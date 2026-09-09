"""weightroom.services.database — engine construction, startup migration and status.

Route handlers and CLI command bodies never call :func:`weightsdb.create_engine_for` directly;
they call a function here, so ``wr-gym db status`` and ``GET /api/v1/health`` report the same
database facts by construction. The shape is LoadCoach's ``services/database.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from weightsdb import (
    DatabaseError,
    DatabaseUnavailable,
    MigrationOutcome,
    MigrationRequired,
    MigrationRunner,
    SchemaAhead,
    create_engine_for,
    database_size_bytes,
    integrity_check,
    session_factory,
    session_scope,
    transaction,
)
from weightsdb import backup as weightsdb_backup
from weightsdb import database_health as weightsdb_database_health
from weightsdb import restore as weightsdb_restore
from weightsdb.backup import BackupResult, RestoreResult, sqlite_path

from weightroom.config import data_dir
from weightroom.infrastructure.db.models import (
    AuditLog,
    KnownRevision,
    Operator,
    Setting,
)
from weightroom.infrastructure.db.models import (
    Session as SessionRow,
)

__all__ = [
    "MIGRATIONS_LOCATION",
    "Database",
    "DatabaseStatus",
    "backup_database",
    "build_engine",
    "database_health",
    "ensure_ready",
    "get_status",
    "migration_runner",
    "restore_database",
    "upgrade",
]

MIGRATIONS_LOCATION = str(
    Path(__file__).resolve().parent.parent / "infrastructure" / "db" / "migrations"
)

_APPLICATION_NAME = "weightroom"
_ROW_COUNT_MODELS = (Operator, SessionRow, AuditLog, Setting, KnownRevision)


def build_engine(database_url: str) -> Engine:
    """Build the engine for ``database_url`` through WeightsDB's dialect-aware factory."""
    return create_engine_for(database_url, application_name=_APPLICATION_NAME)


class Database:
    """WeightRoomGym's live connection to its own database: one engine, for as long as it serves.

    Owned by the caller — the web application creates one in its lifespan and disposes it at
    shutdown; a CLI command creates one, runs, and closes it on the way out.
    """

    __slots__ = ("_engine", "_sessions")

    def __init__(self, engine: Engine) -> None:
        """Wrap an existing engine. Prefer :meth:`from_url` unless you built the engine yourself."""
        self._engine = engine
        self._sessions = session_factory(engine)

    @classmethod
    def from_url(cls, database_url: str) -> Database:
        """Build a handle for ``database_url``. Opens no connection until first use."""
        return cls(build_engine(database_url))

    @property
    def engine(self) -> Engine:
        """The underlying engine, for the file-level operations that need one directly."""
        return self._engine

    @property
    def sessions(self) -> sessionmaker[Session]:
        """The session factory bound to this handle's engine."""
        return self._sessions

    @contextmanager
    def write(self) -> Iterator[Session]:
        """One read-write unit of work, committed on success and rolled back on any exception."""
        with session_scope(self._sessions) as session:
            yield session

    @contextmanager
    def read(self) -> Iterator[Session]:
        """One read-only unit of work: a write attempted inside it is refused, not taken."""
        with session_scope(self._sessions) as session, transaction(session, immediate=False):
            yield session

    def close(self) -> None:
        """Dispose the pool. The handle must not be used afterwards."""
        self._engine.dispose()

    def __enter__(self) -> Database:
        """Support ``with Database.from_url(...) as db:`` for one-shot callers like the CLI."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always dispose the pool, whether the body succeeded or raised."""
        self.close()


def migration_runner(engine: Engine, *, backup_retention: int = 5) -> MigrationRunner:
    """Build the :class:`~weightsdb.MigrationRunner` for WeightRoomGym's own history."""
    return MigrationRunner(
        engine, script_location=MIGRATIONS_LOCATION, backup_retention=backup_retention
    )


def _backup_directory(engine: Engine) -> Path:
    if engine.dialect.name == "sqlite":
        return sqlite_path(engine).parent / "backups"
    return data_dir() / "backups"


def ensure_ready(
    database: Database, *, auto_migrate: bool, backup_retention: int = 5
) -> MigrationOutcome | None:
    """Apply the startup revision check (database standards §5.1).

    Args:
        database: The database handle.
        auto_migrate: ``settings.storage.auto_migrate``.
        backup_retention: ``settings.storage.backup_retention``.

    Returns:
        The :class:`~weightsdb.MigrationOutcome` if a migration ran, else ``None``.

    Raises:
        MigrationRequired: The database is behind head and ``auto_migrate`` is ``False``.
        SchemaAhead: The database's current revision is not one this build's migrations produce.
        DatabaseUnavailable: The database could not be reached at all.
    """
    try:
        runner = migration_runner(database.engine, backup_retention=backup_retention)
        current = runner.current()
        heads = runner.heads()
    except DatabaseError:
        raise
    except Exception as exc:  # noqa: BLE001 — translated into the suite's own error type below
        raise DatabaseUnavailable(
            f"Could not open the database to check its migration state: {exc}"
        ) from exc
    if not heads:  # pragma: no cover — the history ships with this package
        raise DatabaseError(f"No migrations are registered under {MIGRATIONS_LOCATION}.")
    head = heads[0]
    if current == head:
        return None
    if current is not None and current not in runner.known_revisions():
        raise SchemaAhead(
            f"The database is at revision {current!r}, which this build's migrations do not "
            f"produce (known head: {head!r}). It was likely written by a newer version; restore "
            f"the pre-migration backup under {_backup_directory(database.engine)} and install "
            "the version that wrote it.",
            details={"current": current, "head": head},
        )
    if current is not None and not auto_migrate:
        raise MigrationRequired(
            f"The database is at revision {current!r}; head is {head!r}. Run "
            "`wr-gym db upgrade` to migrate.",
            details={"current": current, "head": head, "command": "wr-gym db upgrade"},
        )
    return runner.upgrade(backup=current is not None)


def upgrade(
    database: Database, *, revision: str = "head", backup_retention: int = 5
) -> MigrationOutcome:
    """Run ``wr-gym db upgrade``: migrate to ``revision``, taking a backup first. Idempotent."""
    runner = migration_runner(database.engine, backup_retention=backup_retention)
    return runner.upgrade(revision, backup=runner.current() is not None)


def backup_database(database: Database, *, output: Path | None, keep: int) -> BackupResult:
    """Run ``wr-gym db backup``: a consistent backup, rotating automatic ones against ``keep``."""
    engine = database.engine
    if output is not None:
        return weightsdb_backup(engine, output)
    source = sqlite_path(engine)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = source.parent / "backups" / f"manual-{stamp}{source.suffix}"
    return weightsdb_backup(engine, destination, keep=keep, prefix="manual-")


def restore_database(database: Database, *, source: Path, confirm: bool) -> RestoreResult:
    """Run ``wr-gym db restore``: restore from ``source``, overwriting the current database."""
    return weightsdb_restore(database.engine, source, confirm=confirm)


@dataclass(frozen=True, slots=True)
class DatabaseStatus:
    """The ``wr-gym db status`` snapshot."""

    dialect: str
    current_revision: str | None
    head_revision: str
    is_at_head: bool
    table_row_counts: dict[str, int]
    size_bytes: int
    integrity_ok: bool
    integrity_detail: str


def get_status(database: Database) -> DatabaseStatus:
    """Build the full ``wr-gym db status`` report.

    Raises:
        DatabaseUnavailable: The database could not be reached.
    """
    engine = database.engine
    try:
        runner = migration_runner(engine)
        current = runner.current()
        heads = runner.heads()
        row_counts: dict[str, int] = {}
        if current is not None:
            with database.read() as session:
                for model in _ROW_COUNT_MODELS:
                    count = session.execute(select(func.count()).select_from(model)).scalar_one()
                    row_counts[model.__tablename__] = count
        integrity = integrity_check(engine)
        size_bytes = database_size_bytes(engine)
    except DatabaseError:
        raise
    except Exception as exc:  # noqa: BLE001 — translated into the suite's own error type below
        raise DatabaseUnavailable(f"Could not open the database: {exc}") from exc
    head = heads[0] if heads else ""
    return DatabaseStatus(
        dialect=engine.dialect.name,
        current_revision=current,
        head_revision=head,
        is_at_head=current == head,
        table_row_counts=row_counts,
        size_bytes=size_bytes,
        integrity_ok=integrity.ok,
        integrity_detail=integrity.detail,
    )


def database_health(database: Database) -> tuple[str, str]:
    """The ``database`` health component: ``(status, detail)`` from WeightsDB's own report."""
    report = weightsdb_database_health(database.engine, migration_runner(database.engine))
    if report.status == "ok":
        return "ok", f"{report.dialect} at head"
    return report.status, "; ".join(report.degraded_reasons) or "database unreachable"
