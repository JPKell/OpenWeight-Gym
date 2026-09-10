"""weightroom.services.db_reader — every application's database, opened read-only (spec §7.8).

ADR-0124's mechanics: every connection WeightRoomGym opens to another application's database is
read-only — SQLite through the ``file:…?mode=ro`` URI form ``weightsdb.backup`` itself uses,
PostgreSQL with ``default_transaction_read_only`` set on the connection — and none is pooled, so no
handle outlives the request that opened it. The URL is the application's own effective
``storage.database_url``, printed by ``<app> config show --json`` (ADR-0133 rule 4). The revision is
compared against ``known_revisions`` before anything else is read, and a revision this build does
not know refuses by name (ADR-0123 rule 3).

The engines here are deliberately **not** built by ``weightsdb.create_engine_for``. That factory
configures a database WeightRoomGym owns — it creates the file's directory and sets
``journal_mode=WAL`` and ``secure_delete`` on every connection — and each of those is a write, or
an attempt at one, against a file another application owns. Rows W3 and W4 opened the
applications' databases through it for the Overview table and the doctor's revision rule; both
now open them here.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from datetime import time as clock_time
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final
from urllib.parse import quote

from baseaicore import SuiteError
from sqlalchemy import String, cast, column, create_engine, func, inspect, select, table, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.pool import NullPool
from weightsdb.redaction import redact_url

from weightroom.domain.guard import LockClass, Statement, classify, lock_for, require_read
from weightroom.infrastructure.db.models import KnownRevision
from weightroom.services.processes import child_environment, executable_for, run_command

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import TracebackType

    from sqlalchemy.engine import Connection, Engine

    from weightroom.config import Settings
    from weightroom.services.database import Database
    from weightroom.services.processes import Runner

__all__ = [
    "CONSOLE_ROW_CAP",
    "PAGE_ROWS",
    "STATEMENT_TIMEOUT_SECONDS",
    "AppDatabase",
    "AppDatabaseUnavailable",
    "ColumnInfo",
    "DatabaseUrlCache",
    "QueryResult",
    "ReadFailed",
    "Revision",
    "RowPage",
    "SchemaUnknown",
    "TableInfo",
    "TableUnknown",
    "cell_text",
    "effective_database_url",
    "known_revision",
    "known_revisions",
    "list_tables",
    "open_app_database",
    "open_read_only",
    "read_revision",
    "revision_summary",
    "run_query",
    "table_page",
]

CONSOLE_ROW_CAP: Final = 10_000
"""Spec §7.8 and §15: the console's ``SELECT`` stops here and says it was cut."""

STATEMENT_TIMEOUT_SECONDS: Final = 30.0
"""Spec §7.8, ADR-0124: no statement from the console holds a database longer than this."""

PAGE_ROWS: Final = 100
"""One page of the grid — the page spec §15's 150 ms budget is written against."""

URL_TTL_SECONDS: Final = 60.0
_CONFIG_SHOW_TIMEOUT_SECONDS: Final = 5.0
_PROGRESS_STEPS: Final = 1000


class AppDatabaseUnavailable(SuiteError):
    """The application's database could not be located, or could not be opened read-only."""

    code: ClassVar[str] = "APP_UNREACHABLE"


class SchemaUnknown(SuiteError):
    """ADR-0123 rule 3: the database is at a revision this WeightRoomGym was not written against."""

    code: ClassVar[str] = "SCHEMA_UNKNOWN"


class TableUnknown(SuiteError):
    """The grid was asked for a table the database does not have."""

    code: ClassVar[str] = "NOT_FOUND"


class ReadFailed(SuiteError):
    """A grid parameter or a console statement the database refused, in its own words."""

    code: ClassVar[str] = "VALIDATION_ERROR"


# --- Locating the database ---------------------------------------------------------------------


def effective_database_url(
    settings: Settings, app: str, *, runner: Runner = run_command
) -> tuple[str | None, str | None]:
    """The application's own effective ``storage.database_url``, from ``<app> config show --json``.

    The schema document says where a key came from, not the default the application resolves when
    it loads, so ``config show`` is where the resolved value is (ADR-0133 rule 4). Moved here from
    ``services/overview.py`` (row W3) now that three modules read it.

    Args:
        settings: The validated settings, for the executable.
        app: One of the four.
        runner: The process-launch boundary, injected.

    Returns:
        ``(url, None)``, or ``(None, reason)``. Never raises: a database that cannot be located is a
        state a page renders.
    """
    executable = executable_for(settings, app)
    if executable is None:
        return None, "not installed"
    result = runner(
        [executable, "config", "show", "--json"], child_environment(), _CONFIG_SHOW_TIMEOUT_SECONDS
    )
    if not result.ok:
        return None, result.failure_text
    try:
        body = json.loads(result.stdout)
        # `values` since ADR-0131 (IdeaPress 1.5.0 renamed its `settings`). The old name is read
        # too, for one console major: the console and the applications upgrade on different
        # days (ADR-0129 rule 3). Found on the reference machine at row W4.
        block = body.get("values") if "values" in body else body["settings"]
        url = block["storage"]["database_url"]
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return None, "config show --json did not answer the expected shape"
    return (str(url) if url else None), (None if url else "no database configured")


class DatabaseUrlCache:
    """Each application's ``config show`` answer, re-asked every :data:`URL_TTL_SECONDS`.

    ``config show`` is a process launch — about 0.4 s per application on the reference machine —
    and a URL changes only when a configuration file does. Thread-safe, and a failed answer is
    cached too, as :class:`~weightroom.services.settings_forms.SchemaCache` does, so an application
    that is not installed costs one launch a minute rather than one per request.
    """

    __slots__ = ("_entries", "_lock", "_ttl")

    def __init__(self, *, ttl_seconds: float = URL_TTL_SECONDS) -> None:
        """Build an empty cache."""
        self._entries: dict[str, tuple[float, str | None, str | None]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(
        self,
        app: str,
        *,
        now: float,
        read: Callable[[], tuple[str | None, str | None]],
        refresh: bool = False,
    ) -> tuple[str | None, str | None]:
        """The cached ``(url, reason)`` pair, re-read when stale or when ``refresh`` is set."""
        with self._lock:
            held = self._entries.get(app)
            if held is not None and not refresh and (now - held[0]) < self._ttl:
                return held[1], held[2]
        url, reason = read()
        with self._lock:
            self._entries[app] = (now, url, reason)
        return url, reason


def open_read_only(url: str, *, timeout_seconds: float = STATEMENT_TIMEOUT_SECONDS) -> Engine:
    """An unpooled engine whose every connection is read-only.

    Args:
        url: The application's own ``sqlite:///`` or ``postgresql(+driver)://`` URL.
        timeout_seconds: SQLite's busy timeout; PostgreSQL's ``statement_timeout`` and
            ``lock_timeout``. SQLite has no statement timeout of its own, so the grid and the
            console add a per-statement deadline (:func:`run_query`).

    Returns:
        The engine. Nothing is opened until it is first used.

    Raises:
        AppDatabaseUnavailable: The URL is neither SQLite nor PostgreSQL, or names an in-memory
            SQLite database, which another process cannot share.
    """
    parsed = make_url(url)
    backend = parsed.get_backend_name()
    if backend == "sqlite":
        database = parsed.database or ""
        if not database or database == ":memory:":
            raise AppDatabaseUnavailable(
                "An in-memory SQLite database belongs to the process that opened it.",
                details={"database_url": redact_url(url)},
            )
        uri = f"file:{quote(str(Path(database).expanduser()))}?mode=ro"

        def connect() -> sqlite3.Connection:
            return sqlite3.connect(uri, uri=True, timeout=timeout_seconds)

        return create_engine("sqlite://", creator=connect, poolclass=NullPool)
    if backend == "postgresql":
        milliseconds = max(1, int(timeout_seconds * 1000))
        options = (
            f"-c default_transaction_read_only=on -c statement_timeout={milliseconds} "
            f"-c lock_timeout={milliseconds}"
        )
        return create_engine(
            parsed,
            poolclass=NullPool,
            connect_args={"options": options, "application_name": "weightroom-reader"},
        )
    raise AppDatabaseUnavailable(
        f"{redact_url(url)} is neither SQLite nor PostgreSQL (database standards §2).",
        details={"dialect": backend},
    )


@contextmanager
def _deadline(connection: Connection, seconds: float) -> Iterator[None]:
    """Interrupt a SQLite statement that runs past ``seconds``; PostgreSQL enforces its own."""
    raw = connection.connection.driver_connection
    if not isinstance(raw, sqlite3.Connection):
        yield
        return
    limit = time.monotonic() + seconds
    raw.set_progress_handler(lambda: int(time.monotonic() > limit), _PROGRESS_STEPS)
    try:
        yield
    finally:
        raw.set_progress_handler(None, 0)


def read_revision(engine: Engine) -> str | None:
    """The database's ``alembic_version``, or ``None`` when it has none it will say."""
    try:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT version_num FROM alembic_version")).first()
    except Exception:  # noqa: BLE001 — no alembic_version table is "not known", not a crash
        return None
    return str(row[0]) if row else None


def known_revisions(database: Database, app: str) -> tuple[str, ...]:
    """Every revision of ``app``'s schema this WeightRoomGym was written against."""
    with database.read() as session:
        rows = session.execute(select(KnownRevision.revision).where(KnownRevision.app == app))
        return tuple(sorted(str(one) for one in rows.scalars()))


def known_revision(database: Database, app: str, revision: str | None) -> bool:
    """Whether ``revision`` is one of :func:`known_revisions`."""
    return revision is not None and revision in known_revisions(database, app)


# --- One application's database, for one request ----------------------------------------------


@dataclass(frozen=True, slots=True)
class Revision:
    """The revision check (ADR-0123 rule 3, api.md §3 ``GET …/db/revision``).

    Attributes:
        app: The application.
        found: Its ``alembic_version``, or ``None`` when it has none.
        known: The revisions this build knows for it.
        dialect: ``sqlite`` or ``postgresql``.
        database_url: The URL, credentials redacted.
    """

    app: str
    found: str | None
    known: tuple[str, ...]
    dialect: str
    database_url: str

    @property
    def is_known(self) -> bool:
        """Whether the database's revision is one this build was written against."""
        return self.found is not None and self.found in self.known

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        return {
            "app": self.app,
            "alembic_version": self.found,
            "known": self.is_known,
            "known_revisions": list(self.known),
            "dialect": self.dialect,
            "database_url": self.database_url,
        }


class AppDatabase:
    """One application's database, opened read-only for one request; close it when done."""

    __slots__ = ("app", "engine", "revision", "timeout_seconds", "url")

    def __init__(
        self, app: str, url: str, engine: Engine, revision: Revision, *, timeout_seconds: float
    ) -> None:
        """Wrap an engine from :func:`open_read_only`; :func:`open_app_database` builds these."""
        self.app = app
        self.url = url
        self.engine = engine
        self.revision = revision
        self.timeout_seconds = timeout_seconds

    def close(self) -> None:
        """Dispose the engine; no connection outlives this."""
        self.engine.dispose()

    def __enter__(self) -> AppDatabase:
        """Use as ``with open_app_database(...) as handle:``."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always close."""
        self.close()


def _cause(exc: SQLAlchemyError) -> str:
    return str(exc.orig) if isinstance(exc, DBAPIError) and exc.orig is not None else str(exc)


def open_app_database(
    settings: Settings,
    database: Database,
    app: str,
    *,
    urls: DatabaseUrlCache,
    now: float,
    require_known: bool = True,
    timeout_seconds: float = STATEMENT_TIMEOUT_SECONDS,
    runner: Runner = run_command,
) -> AppDatabase:
    """Locate, open read-only and revision-check one application's database.

    Args:
        settings: The validated settings.
        database: WeightRoomGym's own database, for ``known_revisions``.
        app: One of the four.
        urls: The URL cache.
        now: A monotonic clock reading, for the cache.
        require_known: Refuse an unknown revision (every page but the revision's own).
        timeout_seconds: The statement timeout (:func:`open_read_only`).
        runner: The process-launch boundary, for ``config show``.

    Returns:
        The open handle.

    Raises:
        AppDatabaseUnavailable: No URL, or the database would not open read-only.
        SchemaUnknown: ``require_known`` and the revision is not one this build knows; ``details``
            name the revision found and the revisions known.
    """
    url, reason = urls.get(
        app, now=now, read=lambda: effective_database_url(settings, app, runner=runner)
    )
    if url is None:
        raise AppDatabaseUnavailable(
            f"{app}'s database could not be located: {reason}.",
            details={"app": app, "reason": reason},
        )
    engine = open_read_only(url, timeout_seconds=timeout_seconds)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        engine.dispose()
        raise AppDatabaseUnavailable(
            f"{app}'s database at {redact_url(url)} would not open read-only: {_cause(exc)}",
            details={"app": app, "database_url": redact_url(url)},
        ) from exc
    revision = Revision(
        app=app,
        found=read_revision(engine),
        known=known_revisions(database, app),
        dialect=engine.dialect.name,
        database_url=redact_url(url),
    )
    if require_known and not revision.is_known:
        engine.dispose()
        from weightroom.__about__ import __version__

        raise SchemaUnknown(
            f"{app}'s schema at revision {revision.found or 'none'} is not known to WeightRoomGym "
            f"{__version__} (known: {', '.join(revision.known) or 'none'}); its database pages are "
            "degraded by name (ADR-0123 rule 3).",
            details={"app": app, "found": revision.found, "known": list(revision.known)},
        )
    return AppDatabase(app, url, engine, revision, timeout_seconds=timeout_seconds)


def revision_summary(
    settings: Settings,
    database: Database,
    app: str,
    *,
    urls: DatabaseUrlCache,
    now: float,
    runner: Runner = run_command,
) -> tuple[Revision | None, str | None]:
    """The revision check without the refusal, for ``GET /apps`` and the machine view.

    Returns:
        ``(revision, None)``, or ``(None, reason)`` when the database cannot be read at all.
    """
    try:
        with open_app_database(
            settings, database, app, urls=urls, now=now, require_known=False, runner=runner
        ) as handle:
            return handle.revision, None
    except AppDatabaseUnavailable as exc:
        return None, exc.message


# --- Tables, rows and the console --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TableInfo:
    """One table of the list (api.md §3 ``GET …/db/tables``).

    Attributes:
        name: The table.
        rows: Its row count, or ``None`` when it could not be counted — never ``0`` (ADR-0016).
        lock: The class that makes it never writable, or ``None`` when a guarded write may touch it.
    """

    name: str
    rows: int | None
    lock: LockClass | None

    @property
    def writable(self) -> bool:
        """Whether a raw write may touch it at all — under the five conditions, never without."""
        return self.lock is None

    @property
    def reason(self) -> str | None:
        """Why it is locked, naming the record."""
        if self.lock is None:
            return None
        return (
            f"never writable from WeightRoomGym (ADR-0124) — {self.lock.name}: {self.lock.reason}"
        )

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        return {
            "name": self.name,
            "rows": self.rows,
            "writable": self.writable,
            "reason": self.reason,
            "lock_class": None if self.lock is None else self.lock.name,
        }


def list_tables(handle: AppDatabase) -> tuple[TableInfo, ...]:
    """Every table with its row count and its lock, by name."""
    names = sorted(inspect(handle.engine).get_table_names())
    found: list[TableInfo] = []
    with handle.engine.connect() as connection, _deadline(connection, handle.timeout_seconds):
        for name in names:
            try:
                count: int | None = int(
                    connection.execute(select(func.count()).select_from(table(name))).scalar_one()
                )
            except SQLAlchemyError:
                connection.rollback()  # PostgreSQL refuses every later statement in a failed one
                count = None
            found.append(TableInfo(name=name, rows=count, lock=lock_for(handle.app, name)))
    return tuple(found)


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    """One column of the grid, typed as the database declares it.

    Attributes:
        name: The column.
        type: Its declared type, ``VARCHAR(26)``, ``INTEGER``, ``JSON``.
        nullable: Whether it admits a null.
        primary_key: Whether it is part of the primary key.
    """

    name: str
    type: str
    nullable: bool
    primary_key: bool

    @property
    def numeric(self) -> bool:
        """Whether the grid right-aligns it."""
        declared = self.type.upper()
        return any(word in declared for word in ("INT", "FLOAT", "REAL", "NUMERIC", "DECIMAL"))

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
        }


@dataclass(frozen=True, slots=True)
class RowPage:
    """A page of the grid (api.md §3 ``GET …/db/tables/{t}``).

    Attributes:
        table: The table, with its lock.
        columns: Its columns, typed.
        rows: The page's rows, JSON-safe.
        page: The page number, from 1.
        page_rows: Rows per page.
        total: Rows matching the filter, or ``None`` if they could not be counted.
        sort: The column sorted on, or ``None`` for the primary key.
        descending: Whether the sort is reversed.
        column: The filtered column, or ``None``.
        contains: The text it must contain, or ``None``.
    """

    table: TableInfo
    columns: tuple[ColumnInfo, ...]
    rows: tuple[tuple[Any, ...], ...]
    page: int
    page_rows: int
    total: int | None
    sort: str | None
    descending: bool
    column: str | None
    contains: str | None

    @property
    def pages(self) -> int | None:
        """How many pages the filtered rows make; ``None`` when uncounted."""
        return None if self.total is None else max(1, math.ceil(self.total / self.page_rows))

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        return {
            "table": self.table.as_json(),
            "columns": [one.as_json() for one in self.columns],
            "rows": [list(row) for row in self.rows],
            "page": self.page,
            "page_rows": self.page_rows,
            "pages": self.pages,
            "total": self.total,
            "sort": self.sort,
            "descending": self.descending,
            "column": self.column,
            "filter": self.contains,
        }


def _plain(value: Any) -> Any:  # noqa: ANN401 — whatever the driver returned, made JSON-safe
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    if isinstance(value, (datetime, date, clock_time)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool, dict, list)):
        return value
    return str(value) if isinstance(value, Decimal) else str(value)


def cell_text(value: Any, *, limit: int = 160) -> str:  # noqa: ANN401 — a JSON-safe cell
    """One cell as a page shows it.

    ``NULL`` for a null — a null in a row is a value, not an unavailable reading, so it is neither a
    blank nor ``—``; JSON for a structure; text longer than ``limit`` cut with an ellipsis (the
    JSON route carries it whole).
    """
    if value is None:
        return "NULL"
    shown = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return shown if len(shown) <= limit else shown[: limit - 1] + "…"


def table_page(
    handle: AppDatabase,
    name: str,
    *,
    page: int = 1,
    sort: str | None = None,
    descending: bool = False,
    column_name: str | None = None,
    contains: str | None = None,
    page_rows: int = PAGE_ROWS,
) -> RowPage:
    """One page of a table: sorted, filtered, its columns typed.

    Args:
        handle: The open database.
        name: The table.
        page: From 1; anything lower is page 1.
        sort: A column to order by; the primary key otherwise, so paging is stable.
        descending: Reverse the order.
        column_name: A column to filter on.
        contains: Text the column, cast to text, must contain — matched literally, never a pattern.
        page_rows: Rows per page.

    Returns:
        The :class:`RowPage`.

    Raises:
        TableUnknown: The database has no such table.
        ReadFailed: ``sort`` or ``column_name`` is not one of its columns, or the database refused
            or ran past the timeout.
    """
    inspector = inspect(handle.engine)
    if name not in inspector.get_table_names():
        raise TableUnknown(
            f"{handle.app}'s database has no table {name!r}.",
            details={"app": handle.app, "table": name},
        )
    primary = set(inspector.get_pk_constraint(name).get("constrained_columns") or ())
    columns = tuple(
        ColumnInfo(
            name=str(one["name"]),
            type=str(one["type"]),
            nullable=bool(one.get("nullable", True)),
            primary_key=one["name"] in primary,
        )
        for one in inspector.get_columns(name)
    )
    names = [one.name for one in columns]
    for label, chosen in (("sort", sort), ("column", column_name)):
        if chosen is not None and chosen not in names:
            raise ReadFailed(
                f"{chosen!r} is not a column of {name}; {label} takes one of {', '.join(names)}.",
                details={"table": name, label: chosen},
            )
    page = max(1, page)
    # Untyped column() constructs: the rows come back as the driver gives them, rather than through
    # a reflected type's result processor that may not parse another application's stored format.
    source = table(name, *(column(one) for one in names))
    rows_statement = select(*source.c)
    count_statement = select(func.count()).select_from(source)
    if column_name is not None and contains:
        escaped = contains.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        condition = cast(source.c[column_name], String).like(f"%{escaped}%", escape="\\")
        rows_statement = rows_statement.where(condition)
        count_statement = count_statement.where(condition)
    if sort is not None:
        ordering = [source.c[sort].desc() if descending else source.c[sort].asc()]
    else:
        keys = [source.c[one] for one in names if one in primary] or [source.c[names[0]]]
        ordering = [key.desc() if descending else key.asc() for key in keys]
    rows_statement = (
        rows_statement.order_by(*ordering).limit(page_rows).offset((page - 1) * page_rows)
    )
    try:
        with handle.engine.connect() as connection, _deadline(connection, handle.timeout_seconds):
            total = int(connection.execute(count_statement).scalar_one())
            rows = tuple(
                tuple(_plain(value) for value in row) for row in connection.execute(rows_statement)
            )
    except SQLAlchemyError as exc:
        raise ReadFailed(
            _failure_text(exc, handle.timeout_seconds), details={"app": handle.app, "table": name}
        ) from exc
    return RowPage(
        table=TableInfo(name=name, rows=None, lock=lock_for(handle.app, name)),
        columns=columns,
        rows=rows,
        page=page,
        page_rows=page_rows,
        total=total,
        sort=sort,
        descending=descending,
        column=column_name,
        contains=contains or None,
    )


@dataclass(frozen=True, slots=True)
class QueryResult:
    """What the console's one ``SELECT`` returned (api.md §3 ``POST …/db/query``).

    Attributes:
        statement: The statement, classified.
        columns: The result's column names.
        rows: Up to :data:`CONSOLE_ROW_CAP` rows, JSON-safe.
        truncated: Whether more rows existed than were kept.
        duration_ms: Wall time for the statement and the fetch.
    """

    statement: Statement
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    truncated: bool
    duration_ms: float

    def as_json(self) -> dict[str, Any]:
        """The api.md §3 shape."""
        return {
            "sql": self.statement.text,
            "tables": list(self.statement.tables),
            "columns": list(self.columns),
            "rows": [list(row) for row in self.rows],
            "row_count": len(self.rows),
            "truncated": self.truncated,
            "row_cap": CONSOLE_ROW_CAP,
            "duration_ms": round(self.duration_ms, 1),
        }


def _failure_text(exc: SQLAlchemyError, timeout_seconds: float) -> str:
    cause = _cause(exc)
    if "interrupted" in cause or "statement timeout" in cause:
        return f"The statement ran past {timeout_seconds:g} s and was interrupted (spec §7.8)."
    return f"The database refused the statement: {cause}"


def run_query(
    handle: AppDatabase,
    sql: str,
    *,
    row_cap: int = CONSOLE_ROW_CAP,
    clock: Callable[[], float] = time.monotonic,
) -> QueryResult:
    """Run the console's one ``SELECT`` on the read-only connection, capped and timed out.

    Args:
        handle: The open database.
        sql: The statement as typed.
        row_cap: Rows kept before the result says it was cut.
        clock: A monotonic clock, injected.

    Returns:
        The :class:`QueryResult`.

    Raises:
        GuardStatementRefused: It is not exactly one ``SELECT`` (``domain/guard.py``): DML, DDL,
            ``PRAGMA`` and a second statement are refused by name before the database sees them.
        ReadFailed: The database refused it, or it ran past the timeout.
    """
    statement = require_read(classify(sql))
    started = clock()
    try:
        with handle.engine.connect() as connection, _deadline(connection, handle.timeout_seconds):
            # no_parameters: the text goes to the cursor alone. With an empty parameter list
            # psycopg reads every `%` as a placeholder, so `LIKE 'note 1%'` would be refused
            # (found by the PostgreSQL leg).
            result = connection.exec_driver_sql(
                statement.text, execution_options={"no_parameters": True}
            )
            columns = tuple(str(one) for one in result.keys())
            fetched = result.fetchmany(row_cap + 1)
    except SQLAlchemyError as exc:
        raise ReadFailed(
            _failure_text(exc, handle.timeout_seconds), details={"app": handle.app}
        ) from exc
    return QueryResult(
        statement=statement,
        columns=columns,
        rows=tuple(tuple(_plain(value) for value in row) for row in fetched[:row_cap]),
        truncated=len(fetched) > row_cap,
        duration_ms=(clock() - started) * 1000.0,
    )
