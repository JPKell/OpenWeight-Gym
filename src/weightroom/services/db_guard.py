"""weightroom.services.db_guard — ADR-0124's guarded write, wired (spec §7.8).

``domain/guard.py`` decides; this module observes and acts. A raw write into another
application's database runs in ADR-0133's order, and every step is a fact the service checked
rather than one the operator asserted:

1. the statement is one DML statement, and neither it nor a foreign-key action it fires writes a
   never-writable table — the foreign keys are reflected from the database, read-only;
2. every table the statement names was typed (condition 4);
3. the unit is not running and nothing answers on the application's port (condition 1);
4. the dry run is repeated, rolled back, and matches the digest the operator was shown
   (condition 3);
5. a backup is taken through ``weightsdb.backup`` into WeightRoomGym's own data root
   (condition 2);
6. the ``pending`` audit row is written, carrying the backup path (condition 5);
7. the statement runs on its own short-lived connection — rolled back if its counts differ from
   the dry run's — and the row is completed.

A refusal before step 6 is one ``refused`` row; a failure after it completes the pending row as
``failed``. A process that dies between steps 6 and 7 leaves the row ``pending``, which is the
reason it is written first.

**The write connection is ``weightsdb.create_engine_for``'s, deliberately** — unlike every read
(``services/db_reader.py``). It gives the statement the connection the owning application itself
uses: ``BEGIN IMMEDIATE`` and ``foreign_keys=ON`` on SQLite, so the cascades the reach predicted
are the cascades that happen, and ``statement_timeout`` on PostgreSQL. It is opened for the dry run
or for the one statement, and disposed straight after.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import urlsplit

from baseaicore import SuiteError
from sqlalchemy import create_engine, func, inspect, select, table
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.pool import NullPool
from weightsdb import DatabaseError, create_engine_for
from weightsdb import backup as weightsdb_backup

from weightroom.config import data_dir
from weightroom.domain.guard import (
    Condition,
    ForeignKey,
    GuardAppRunning,
    GuardAuditFailed,
    GuardBackupFailed,
    GuardDryRunFailed,
    GuardTableMismatch,
    Reach,
    Statement,
    application_stopped,
    checklist,
    classify,
    reach,
    require_writable,
    require_write,
    typed_mismatch,
)
from weightroom.domain.guard import dry_run_id as bind_dry_run
from weightroom.domain.units import unit_name
from weightroom.services.apps import unit_statuses
from weightroom.services.audit import complete, record
from weightroom.services.db_reader import open_app_database, statement_deadline

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from sqlalchemy.engine import Connection

    from weightroom.config import Settings
    from weightroom.services.database import Database
    from weightroom.services.db_reader import DatabaseUrlCache
    from weightroom.services.processes import SystemdController

__all__ = [
    "GUARD_TIMEOUT_SECONDS",
    "BackupFile",
    "Counts",
    "DryRun",
    "Observation",
    "WriteResult",
    "backups_directory",
    "dry_run",
    "execute_statement",
    "guarded_write",
    "list_backups",
    "observe",
]

GUARD_TIMEOUT_SECONDS: Final = 30.0
"""ADR-0124: the statement's timeout — ``busy_timeout`` and a deadline on SQLite,
``statement_timeout`` and ``lock_timeout`` on PostgreSQL."""

_PORT_TIMEOUT_SECONDS: Final = 0.5
_BACKUP_MARKER: Final = "-guarded-write"

type Connector = Callable[[tuple[str, int], float], None]


def _connect(address: tuple[str, int], timeout: float) -> None:
    socket.create_connection(address, timeout=timeout).close()


def _cause(exc: BaseException) -> str:
    if isinstance(exc, DBAPIError) and exc.orig is not None:
        return str(exc.orig)
    return getattr(exc, "message", None) or str(exc)


# --- Condition 1 ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Observation:
    """Condition 1's two facts (ADR-0133 rule 3).

    Attributes:
        unit_state: The unit's state; ``unsupported`` on a host with no systemd.
        port_open: Whether a connection to the application's port was accepted; ``None`` when its
            base URL names nothing to try.
        address: The ``host:port`` tried.
    """

    unit_state: str
    port_open: bool | None
    address: str

    @property
    def stopped(self) -> bool:
        """Whether both facts say the application is not running."""
        return application_stopped(unit_state=self.unit_state, port_open=self.port_open)

    @property
    def evidence(self) -> str:
        """The two facts in words."""
        port = "unknown" if self.port_open is None else "open" if self.port_open else "closed"
        return f"unit {self.unit_state}, port {self.address} {port}"


def observe(
    settings: Settings,
    controller: SystemdController,
    app: str,
    *,
    connect: Connector | None = None,
) -> Observation:
    """Ask systemd for the unit and try the application's port.

    Args:
        settings: The validated settings, for the application's ``base_url``.
        controller: The systemd boundary.
        app: One of the four.
        connect: Opens and closes a TCP connection or raises ``OSError``; injected in tests.

    Returns:
        The :class:`Observation`. Never raises: a host without systemd is ``unsupported``, and a
        port that cannot be tried is ``None``, which condition 1 does not accept as stopped.
    """
    statuses = unit_statuses(controller, [app])
    status = None if statuses is None else statuses.get(unit_name(app))
    unit_state = "unsupported" if statuses is None else status.state if status else "absent"
    parts = urlsplit(getattr(settings.apps, app).base_url)
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        return Observation(unit_state, None, parts.netloc or "?")
    if not parts.hostname:
        return Observation(unit_state, None, parts.netloc or "?")
    address = f"{parts.hostname}:{port}"
    try:
        (connect or _connect)((parts.hostname, port), _PORT_TIMEOUT_SECONDS)
    except OSError:
        return Observation(unit_state, False, address)
    return Observation(unit_state, True, address)


# --- The statement on its own connection ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Counts:
    """What a statement did, as the database reported it.

    Attributes:
        rows: The rows the statement itself reported.
        changes: Each reached table's change in row count, ``None`` where it is not counted — a
            ``SET NULL`` changes values, not rows.
    """

    rows: int
    changes: dict[str, int | None]


class _CountsDiffer(Exception):  # noqa: N818 — a private signal, not an error the caller names
    def __init__(self, counts: Counts) -> None:
        super().__init__("counts differ from the dry run")
        self.counts = counts


def _count(connection: Connection, name: str) -> int:
    return int(connection.execute(select(func.count()).select_from(table(name))).scalar_one())


def execute_statement(
    url: str,
    statement: Statement,
    reached: Sequence[Reach],
    *,
    commit: bool,
    expected: Counts | None = None,
) -> Counts:
    """Run the statement on its own connection: rolled back for a dry run, committed for the write.

    Args:
        url: The application's own URL.
        statement: The classified statement.
        reached: What its foreign keys reach; each cascaded delete is counted before and after.
        commit: Commit when the counts hold; otherwise always roll back.
        expected: The dry run's counts. When given and different, the transaction is rolled back.

    Returns:
        The :class:`Counts`.

    Raises:
        SQLAlchemyError: The database refused the statement.
        DatabaseError: WeightsDB's own refusals — a lock held past the busy timeout.
        _CountsDiffer: ``expected`` was given and the counts differ (rolled back).
    """
    engine = create_engine_for(
        url,
        statement_timeout_ms=int(GUARD_TIMEOUT_SECONDS * 1000),
        sqlite_busy_timeout_ms=int(GUARD_TIMEOUT_SECONDS * 1000),
        application_name="weightroom-guard",
    )
    counted = [one.table for one in reached if one.action == "ON DELETE CASCADE"]
    try:
        with engine.connect() as connection, statement_deadline(connection, GUARD_TIMEOUT_SECONDS):
            transaction = connection.begin()
            try:
                before = {name: _count(connection, name) for name in counted}
                result = connection.exec_driver_sql(
                    statement.text, execution_options={"no_parameters": True}
                )
                rows = int(result.rowcount)
                changes: dict[str, int | None] = {
                    one.table: _count(connection, one.table) - before[one.table]
                    if one.table in before
                    else None
                    for one in reached
                }
                counts = Counts(rows=rows, changes=changes)
                if expected is not None and counts != expected:
                    raise _CountsDiffer(counts)
                if commit:
                    transaction.commit()
                else:
                    transaction.rollback()
            except BaseException:
                if transaction.is_active:
                    transaction.rollback()
                raise
        return counts
    finally:
        engine.dispose()


# --- The dry run -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Inspected:
    statement: Statement
    tables: tuple[str, ...]
    reached: tuple[Reach, ...]
    url: str
    shown_url: str


def _inspect(
    settings: Settings,
    database: Database,
    app: str,
    sql: str,
    *,
    urls: DatabaseUrlCache,
    monotonic: float,
) -> _Inspected:
    """The statement, the tables it names that exist, what it reaches, and the lock over both."""
    statement = require_write(classify(sql))
    with open_app_database(settings, database, app, urls=urls, now=monotonic) as handle:
        inspector = inspect(handle.engine)
        names = inspector.get_table_names()
        keys = tuple(
            ForeignKey(
                child=name,
                parent=str(key["referred_table"]),
                on_delete=str((key.get("options") or {}).get("ondelete") or "").upper(),
                on_update=str((key.get("options") or {}).get("onupdate") or "").upper(),
            )
            for name in names
            for key in inspector.get_foreign_keys(name)
        )
        url, shown_url = handle.url, handle.revision.database_url
    folded = {name.lower() for name in names}
    tables = tuple(one for one in statement.tables if one.lower() in folded)
    reached = reach(statement.written, statement.events, keys)
    require_writable(app, statement, reached)
    return _Inspected(statement, tables, reached, url, shown_url)


def _run_dry(inspected: _Inspected) -> Counts:
    try:
        counts = execute_statement(
            inspected.url, inspected.statement, inspected.reached, commit=False
        )
    except (SQLAlchemyError, DatabaseError) as exc:
        raise GuardDryRunFailed(
            f"The dry run failed, so nothing will be written: {_cause(exc)}",
            details={"error": _cause(exc)},
        ) from exc
    if counts.rows < 0:
        raise GuardDryRunFailed(
            "The database reported no row count for the dry run, and the guard shows one or "
            "writes nothing.",
            details={"error": "no row count"},
        )
    return counts


@dataclass(frozen=True, slots=True)
class DryRun:
    """A rolled-back dry run, or why none ran (api.md §3 ``POST …/db/write/dry-run``).

    Attributes:
        app: The application.
        statement: The statement, classified.
        tables: The tables it names that exist — what the operator types.
        reached: What its foreign keys reach.
        observation: Condition 1's facts.
        counts: The dry run's counts, or ``None`` while the application runs: no statement touches
            a running application's database, not even rolled back.
        database_url: The URL, credentials redacted.
    """

    app: str
    statement: Statement
    tables: tuple[str, ...]
    reached: tuple[Reach, ...]
    observation: Observation
    counts: Counts | None
    database_url: str

    @property
    def dry_run_id(self) -> str | None:
        """The digest a write must present (ADR-0133 rule 5); ``None`` when nothing ran."""
        if self.counts is None:
            return None
        return bind_dry_run(
            app=self.app,
            statement=self.statement.text,
            count=self.counts.rows,
            reached=self.counts.changes,
        )

    def conditions(
        self,
        *,
        typed: Sequence[str] | None = None,
        backup_path: str | None = None,
        audit_id: str | None = None,
    ) -> tuple[Condition, ...]:
        """The checklist over what this dry run observed, plus what the caller adds."""
        return checklist(
            unit_state=self.observation.unit_state,
            port_open=self.observation.port_open,
            backup_path=backup_path,
            dry_run_count=None if self.counts is None else self.counts.rows,
            tables=self.tables,
            typed=typed,
            audit_id=audit_id,
        )

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        changes = {} if self.counts is None else self.counts.changes
        return {
            "app": self.app,
            "sql": self.statement.text,
            "verb": self.statement.verb,
            "tables": list(self.tables),
            "tables_written": list(self.statement.written),
            "reached": [
                {**one.as_json(), "change": changes.get(one.table)} for one in self.reached
            ],
            "row_count": None if self.counts is None else self.counts.rows,
            "dry_run_id": self.dry_run_id,
            "unit_state": self.observation.unit_state,
            "port_open": self.observation.port_open,
            "address": self.observation.address,
            "database_url": self.database_url,
            "checklist": [one.as_json() for one in self.conditions()],
        }


def dry_run(
    settings: Settings,
    database: Database,
    controller: SystemdController,
    app: str,
    sql: str,
    *,
    urls: DatabaseUrlCache,
    monotonic: float,
    connect: Connector | None = None,
) -> DryRun:
    """Classify, lock-check and — once the application is stopped — dry-run one statement.

    Args:
        settings: The validated settings.
        database: WeightRoomGym's own database.
        controller: The systemd boundary.
        app: One of the four.
        sql: The statement as typed.
        urls: The URL cache.
        monotonic: A monotonic clock reading, for the cache.
        connect: The port probe, injected in tests.

    Returns:
        The :class:`DryRun`; its counts are ``None`` while the application runs.

    Raises:
        GuardStatementRefused: Not one DML statement.
        GuardTableLocked: It writes, or reaches, a never-writable table.
        SchemaUnknown: The database is at a revision this console does not know.
        AppDatabaseUnavailable: The database cannot be located or opened.
        GuardDryRunFailed: The rolled-back statement errored or reported no count.
    """
    inspected = _inspect(settings, database, app, sql, urls=urls, monotonic=monotonic)
    observation = observe(settings, controller, app, connect=connect)
    counts = _run_dry(inspected) if observation.stopped else None
    return DryRun(
        app=app,
        statement=inspected.statement,
        tables=inspected.tables,
        reached=inspected.reached,
        observation=observation,
        counts=counts,
        database_url=inspected.shown_url,
    )


# --- The write -------------------------------------------------------------------------------


def backups_directory(app: str, *, root: Path | None = None) -> Path:
    """``<data>/backups/<app>/``, where a guarded write's backup goes (ADR-0124 condition 2)."""
    return (root if root is not None else data_dir() / "backups") / app


@dataclass(frozen=True, slots=True)
class BackupFile:
    """One guarded-write backup on disk (api.md §3 ``GET …/db/backups``)."""

    path: Path
    size_bytes: int
    modified_at: datetime

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        return {
            "path": str(self.path),
            "name": self.path.name,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at.isoformat(),
        }


def list_backups(app: str, *, root: Path | None = None) -> tuple[BackupFile, ...]:
    """Every guarded-write backup of ``app``'s database, newest first. Never rotated: each is the
    undo of one raw write."""
    directory = backups_directory(app, root=root)
    if not directory.is_dir():
        return ()
    found = [
        BackupFile(path, path.stat().st_size, datetime.fromtimestamp(path.stat().st_mtime, UTC))
        for path in directory.iterdir()
        # The backup's own file, not the -shm/-wal a read of it leaves beside it.
        if path.is_file() and _BACKUP_MARKER in path.name and path.suffix in (".sqlite3", ".dump")
    ]
    return tuple(sorted(found, key=lambda one: (one.modified_at, one.path.name), reverse=True))


@dataclass(frozen=True, slots=True)
class WriteResult:
    """A write that passed all five conditions and landed.

    Attributes:
        audit_id: The completed audit row.
        backup_path: The backup taken before it.
        counts: What the statement did.
        dry: The repeated dry run it was bound to.
    """

    audit_id: str
    backup_path: Path
    counts: Counts
    dry: DryRun

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        return {
            "audit_id": self.audit_id,
            "backup_path": str(self.backup_path),
            "row_count": self.counts.rows,
            "changes": self.counts.changes,
            "checklist": [
                one.as_json()
                for one in self.dry.conditions(
                    typed=self.dry.tables,
                    backup_path=str(self.backup_path),
                    audit_id=self.audit_id,
                )
            ],
        }


def guarded_write(
    settings: Settings,
    database: Database,
    controller: SystemdController,
    app: str,
    sql: str,
    *,
    tables_typed: Sequence[str],
    dry_run_id: str,
    operator_id: str | None,
    urls: DatabaseUrlCache,
    now: datetime,
    monotonic: float,
    authorise: Callable[[], None] | None = None,
    request_id: str | None = None,
    backups_root: Path | None = None,
    connect: Connector | None = None,
) -> WriteResult:
    """Run one raw write under ADR-0124's five conditions, in ADR-0133's order.

    Args:
        settings: The validated settings.
        database: WeightRoomGym's own database.
        controller: The systemd boundary.
        app: One of the four.
        sql: The statement as typed.
        tables_typed: What the operator typed, compared exactly.
        dry_run_id: The digest of the dry run the operator confirmed.
        operator_id: Who, for the audit row.
        urls: The URL cache.
        now: The instant, for the audit row and the backup's name.
        monotonic: A monotonic clock reading, for the cache.
        authorise: Raises when the session may not write — the re-authentication check. Its
            refusal is audited like any other.
        request_id: The request, for the audit row.
        backups_root: Where ``<app>/`` backups go; WeightRoomGym's data root otherwise.
        connect: The port probe, injected in tests.

    Returns:
        The :class:`WriteResult`.

    Raises:
        ReauthRequired: ``authorise`` refused.
        GuardStatementRefused: Not one DML statement.
        GuardTableLocked: It writes, or reaches, a never-writable table.
        SchemaUnknown: The database is at a revision this console does not know.
        AppDatabaseUnavailable: The database cannot be located or opened.
        GuardTableMismatch: Condition 4.
        GuardAppRunning: Condition 1.
        GuardDryRunFailed: Condition 3 — the repeated dry run errored or no longer matches, or the
            statement's own counts differed and it was rolled back.
        GuardBackupFailed: Condition 2.
        GuardAuditFailed: Condition 5 — the pending row could not be written.
    """
    started = datetime.now(UTC) if now is None else now

    def refuse(exc: SuiteError, *, tables: Sequence[str] = (), outcome: str = "refused") -> None:
        record(
            database,
            action="db.guarded_write",
            actor="operator",
            outcome=outcome,
            now=started,
            operator_id=operator_id,
            app=app,
            target=", ".join(tables) or None,
            params={
                "code": exc.code,
                "condition": exc.details.get("condition"),
                "tables_typed": list(tables_typed),
            },
            message=exc.message,
            statement=sql,
            security=True,
            request_id=request_id,
        )

    inspected: _Inspected | None = None
    try:
        if authorise is not None:
            authorise()
        inspected = _inspect(settings, database, app, sql, urls=urls, monotonic=monotonic)
        missing, extra = typed_mismatch(inspected.tables, tables_typed)
        if missing or extra:
            raise GuardTableMismatch(
                "Type every table the statement names, exactly: "
                f"{', '.join(inspected.tables)}."
                + (f" Not typed: {', '.join(missing)}." if missing else "")
                + (f" Not in the statement: {', '.join(extra)}." if extra else ""),
                details={
                    "tables_in_statement": list(inspected.tables),
                    "tables_typed": list(tables_typed),
                },
            )
        observation = observe(settings, controller, app, connect=connect)
        if not observation.stopped:
            raise GuardAppRunning(
                f"{app} is not stopped ({observation.evidence}); a raw write runs only with the "
                "application stopped (ADR-0124 condition 1).",
                details={
                    "unit_state": observation.unit_state,
                    "port_open": observation.port_open,
                    "address": observation.address,
                },
            )
        dry = DryRun(
            app,
            inspected.statement,
            inspected.tables,
            inspected.reached,
            observation,
            _run_dry(inspected),
            inspected.shown_url,
        )
        if dry.dry_run_id != dry_run_id:
            raise GuardDryRunFailed(
                "The dry run no longer matches the one you confirmed — the statement, its count or "
                "what it reaches has changed. Run the dry run again and confirm what it shows.",
                details={
                    "dry_run_count": None if dry.counts is None else dry.counts.rows,
                    "tables_in_statement": list(dry.tables),
                },
            )
    except SuiteError as exc:
        refuse(exc, tables=() if inspected is None else inspected.tables)
        raise
    counts = dry.counts
    assert counts is not None  # noqa: S101 — _run_dry returned, so the dry run counted

    suffix = ".dump" if make_url(inspected.url).get_backend_name() == "postgresql" else ".sqlite3"
    stamp = started.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backups_directory(app, root=backups_root) / f"{stamp}{_BACKUP_MARKER}{suffix}"
    source = create_engine(inspected.url, poolclass=NullPool)
    try:
        backup = weightsdb_backup(source, destination)
    except (DatabaseError, OSError) as exc:
        failure = GuardBackupFailed(
            f"The backup failed, so nothing was written: {_cause(exc)}",
            details={"destination": str(destination)},
        )
        refuse(failure, tables=dry.tables, outcome="failed")
        raise failure from exc
    finally:
        source.dispose()

    try:
        audit_id = record(
            database,
            action="db.guarded_write",
            actor="operator",
            outcome="pending",
            now=started,
            operator_id=operator_id,
            app=app,
            target=", ".join(dry.tables),
            params={
                "database_url": dry.database_url,
                "tables_typed": list(tables_typed),
                "reached": counts.changes,
                "dry_run_id": dry_run_id,
            },
            statement=sql,
            backup_path=str(backup.path),
            dry_run_count=counts.rows,
            security=True,
            request_id=request_id,
        )
    except Exception as exc:
        raise GuardAuditFailed(
            f"The audit row could not be written, so the statement did not run: {exc}",
            details={"backup_path": str(backup.path)},
        ) from exc

    try:
        actual = execute_statement(
            inspected.url, inspected.statement, inspected.reached, commit=True, expected=counts
        )
    except _CountsDiffer as exc:
        message = (
            f"Rolled back: the statement reported {exc.counts.rows} rows and "
            f"{exc.counts.changes} where the dry run showed {counts.rows} and {counts.changes}."
        )
        complete(
            database, audit_id, outcome="failed", actual_count=exc.counts.rows, message=message
        )
        raise GuardDryRunFailed(message, details={"audit_id": audit_id}) from exc
    except (SQLAlchemyError, DatabaseError) as exc:
        message = f"The statement failed where its dry run did not: {_cause(exc)}"
        complete(database, audit_id, outcome="failed", message=message)
        raise GuardDryRunFailed(message, details={"audit_id": audit_id}) from exc
    complete(database, audit_id, outcome="ok", actual_count=actual.rows)
    return WriteResult(audit_id=audit_id, backup_path=backup.path, counts=actual, dry=dry)
