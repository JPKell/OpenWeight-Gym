"""weightroom.services.app_pages — where an application page's data comes from (spec §7.3).

One rule for every page under an application's tab, written once so no page re-decides it:

* **Running and reachable** — the application's own API. A call that fails renders as its
  refusal, never as the database's figures quietly substituted for what the application itself
  could not answer (the Overview's rule, W3).
* **Stopped, or not answering** — the application's database, read-only and only at a revision
  this console knows (ADR-0123 rule 3); a page with no database source says so.
* **Where the API has no view of the subject** — the database, running or not (spec §7.3's own
  words); the page passes no API reader and says why beside its footer.
* **A version outside the range** — neither: the page degrades by name (spec §19).

The footer names which, in words (spec §7.3: *from the API*, *from the database at revision 0015*).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from datetime import time as clock_time
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from baseaicore import SuiteError
from sqlalchemy import column, inspect, select, table
from sqlalchemy.exc import SQLAlchemyError

from weightroom.services.apps import AppVersionMismatch
from weightroom.services.db_reader import ReadFailed, TableUnknown, statement_deadline

if TYPE_CHECKING:
    from weightroom.services.apps import AppView
    from weightroom.services.db_reader import AppDatabase

__all__ = ["Sourced", "read", "rows_where"]


@dataclass(frozen=True, slots=True)
class Sourced[T]:
    """A page's data and where it came from.

    Attributes:
        source: ``api``, ``database`` or ``none``.
        detail: The footer's sentence.
        data: What the source answered, or ``None`` when nothing did.
        error: Why nothing did, when that was a refusal the page should show by its code.
    """

    source: Literal["api", "database", "none"]
    detail: str
    data: T | None
    error: SuiteError | None = None

    @property
    def live(self) -> bool:
        """Whether the application's API answered — the condition for every API-only action."""
        return self.source == "api"


def read[T](
    view: AppView,
    *,
    api: Callable[[], T] | None,
    database: Callable[[AppDatabase], T] | None,
    open_database: Callable[[], AppDatabase],
) -> Sourced[T]:
    """Read one page's data by spec §7.3's rule.

    Args:
        view: The application as this request sees it.
        api: Reads the data from the running application's API; ``None`` for a subject its API has
            no view of, which the database answers whether or not the application runs.
        database: Reads the same data from an open, known-revision database handle; ``None`` for a
            page whose subject exists only in the running process (a tool registry, a probe).
        open_database: Opens the application's database read-only, refusing an unknown revision
            (``db_reader.open_app_database``, bound by the route).

    Returns:
        The :class:`Sourced` result. Never raises a :class:`~baseaicore.SuiteError`: every
        refusal, unreachable database and unknown revision becomes ``source="none"`` with the
        error attached, so a page renders it rather than an error page.
    """
    if view.pill == "version mismatch":
        mismatch = AppVersionMismatch(
            f"{view.name} {view.version} is outside the range this console speaks to "
            f"({view.supported_range}); its pages are degraded by name rather than guessed at.",
            details={"app": view.name, "version": view.version},
        )
        return Sourced("none", mismatch.message, None, mismatch)
    if api is not None and view.running and view.reachable:
        try:
            return Sourced("api", "From the API", api())
        except SuiteError as exc:
            return Sourced("none", f"The API did not answer this page: {exc.message}", None, exc)
    if database is None:
        return Sourced(
            "none",
            f"{view.name} is not answering, and this page reads only from its running API.",
            None,
        )
    try:
        with open_database() as handle:
            revision = handle.revision.found or "none"
            return Sourced(
                "database", f"From the database at revision {revision}", database(handle)
            )
    except SuiteError as exc:
        return Sourced("none", exc.message, None, exc)


def _json_safe(value: Any) -> Any:  # noqa: ANN401 — whatever the driver returned
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    if isinstance(value, (datetime, date, clock_time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def rows_where(
    handle: AppDatabase,
    table_name: str,
    *,
    equals: Mapping[str, object] | None = None,
    order_by: str | None = None,
    descending: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Rows of one of an application's tables, filtered by equality, as dictionaries.

    The read an application page falls back to (``data-model.md`` §4): untyped columns, so a
    stored value comes back as the driver gives it rather than through a reflected type that may
    not parse another application's format, over the handle's read-only connection and timeout.

    Args:
        handle: The open, revision-checked database.
        table_name: The table.
        equals: ``column → value`` conditions, all of which must hold; a ``None`` or empty value
            is no condition, so an unset page filter reads everything.
        order_by: The column to order by, or ``None`` for the database's order.
        descending: Newest first, when ``order_by`` is a timestamp.
        limit: Rows at most.
        offset: Rows to skip, for a numbered page.

    Returns:
        The rows, each ``{column: value}`` with values JSON-safe.

    Raises:
        TableUnknown: The database has no such table.
        ReadFailed: A named column is not one of the table's, or the database refused or ran past
            the timeout.
    """
    inspector = inspect(handle.engine)
    if table_name not in inspector.get_table_names():
        raise TableUnknown(
            f"{handle.app}'s database has no table {table_name!r}.",
            details={"app": handle.app, "table": table_name},
        )
    names = [str(one["name"]) for one in inspector.get_columns(table_name)]
    conditions = {key: value for key, value in (equals or {}).items() if value not in (None, "")}
    for name in [*conditions, *([order_by] if order_by else [])]:
        if name not in names:
            raise ReadFailed(
                f"{name!r} is not a column of {handle.app}'s {table_name}.",
                details={"app": handle.app, "table": table_name, "column": name},
            )
    source = table(table_name, *(column(name) for name in names))
    statement = select(*source.c)
    for key, value in conditions.items():
        statement = statement.where(source.c[key] == value)
    if order_by:
        key_column = source.c[order_by]
        statement = statement.order_by(key_column.desc() if descending else key_column.asc())
    statement = statement.limit(max(1, limit)).offset(max(0, offset))
    try:
        with (
            handle.engine.connect() as connection,
            statement_deadline(connection, handle.timeout_seconds),
        ):
            return [
                {str(key): _json_safe(value) for key, value in row.items()}
                for row in connection.execute(statement).mappings()
            ]
    except SQLAlchemyError as exc:
        raise ReadFailed(
            f"{handle.app}'s {table_name} could not be read: {exc}",
            details={"app": handle.app, "table": table_name},
        ) from exc
