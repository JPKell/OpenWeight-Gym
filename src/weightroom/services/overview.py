"""weightroom.services.overview — each application's Overview page (spec §7.3, design brief §4).

The artboard's shape is one shape for all four applications: the pill (already ``AppView``'s),
four figures, a primary table, a live log tail. What differs is *where the figures and the table
come from*, and spec §7.3 draws the same line for every application: the API when it is running
and reachable, the database when it is not, ``—`` when neither answers.

**The primary table always reads the application's own database directly**, running or not —
the one deliberate narrowing this row makes against the letter of §7.3's per-application source
column (which reads as API-when-up for "the listing" too). Two things pushed that way. First,
spec §10 and the data model's own cross-reference table (§4) already list "database" as a
legitimate read path for every application, not one reserved for the stopped case — the
narrower reading in §7.3 is about the *figures*, which do need a live number a static row
cannot give (a queue depth, an open circuit breaker), not about a *listing*, which a database
already answers exactly. Second, and decisively: each application's list endpoint has its own
JSON shape that would need reading and pinning per application before this page could render a
row of it, while every application already exposes the one shape every row here needs —
``alembic_version`` and a handful of named tables (data model §4) — through the read-only
connection this module already opens for the stopped case. Building the per-application list
parsers is real work with no shortcut, and this row's job is the shell and the strip, not a
fifth database reader per application; W7's guarded database viewer is where a *browsable* table
belongs, and this Overview table is content to be a read of the same rows, once.

Figures differ: they are read from ``GET /api/v1/system/status`` (one call, already built by
every application) when the application answers, and from ``COUNT(*)`` over the same named
tables the primary table reads when it does not.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import MetaData, Table, func, select, text

from weightroom.services.apps import bearer_token
from weightroom.services.database import Database
from weightroom.services.processes import child_environment, executable_for, run_command

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings
    from weightroom.services.apps import AppView

__all__ = ["Figure", "Overview", "OverviewTable", "overview_for"]

logger = logging.getLogger(__name__)

_CONFIG_SHOW_TIMEOUT_SECONDS: Final = 5.0
_STATUS_TIMEOUT_SECONDS: Final = 3.0
_TABLE_ROW_LIMIT: Final = 10
_TABLE_COLUMN_LIMIT: Final = 6

_PRIMARY_TABLE: Final[dict[str, str]] = {
    "freeweight": "models",
    "loadcoach": "models",
    "ideapress": "projects",
    "promptcadence": "trajectories",
}

_FIGURE_TABLES: Final[dict[str, tuple[str, ...]]] = {
    "freeweight": ("models", "runs", "capability_evidence"),
    "loadcoach": ("models", "jobs", "routing_decisions"),
    "ideapress": ("projects", "units", "stage_runs"),
    "promptcadence": ("trajectories", "approval_requests", "turns"),
}
"""The tables each application's stopped-state figures fall back to counting (data model §4)."""

_STATUS_FIGURES: Final[dict[str, tuple[tuple[str, tuple[str, ...]], ...]]] = {
    # label -> a dotted path into GET /system/status's own body (api.md §1, each application's own).
    "freeweight": (
        ("Active run", ("active_run",)),
        ("Queue depth", ("queue_depth",)),
        ("Disk headroom", ("disk_headroom_bytes",)),
    ),
    "loadcoach": (
        ("Active", ("active",)),
        ("Oldest queued", ("oldest_queued_age_seconds",)),
        ("Starving", ("starving",)),
    ),
    "ideapress": (
        ("Active stage runs", ("active_stage_runs",)),
        ("Backend", ("backend_mode",)),
        ("Pin", ("pin",)),
    ),
    "promptcadence": (
        ("Executing", ("executing",)),
        ("Planning", ("planning",)),
        ("Pending approvals", ("pending_approvals",)),
    ),
}
"""Best-effort field names read off each application's own status body; an absent key is a
figure this build does not know how to read, not a zero (ADR-0016) — it renders ``—``."""


@dataclass(frozen=True, slots=True)
class Figure:
    """One of the Overview's four cards."""

    label: str
    value: str
    note: str | None = None


@dataclass(frozen=True, slots=True)
class OverviewTable:
    """The primary table: a caption, its columns, and up to :data:`_TABLE_ROW_LIMIT` rows."""

    caption: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    empty_message: str | None = None

    def columns_for_table_macro(self) -> tuple[dict[str, str], ...]:
        """``columns`` in the shape MirrorWall's ``table()`` macro takes (spec §4)."""
        return tuple({"label": name} for name in self.columns)


@dataclass(frozen=True, slots=True)
class Overview:
    """Everything the Overview page renders beyond the pill, which is already ``AppView``'s."""

    source: str
    """``"api"``, ``"database"`` or ``"none"`` — the footer names it (spec §7.3)."""
    source_detail: str
    figures: tuple[Figure, ...]
    table: OverviewTable


def _dash_figures(app: str) -> tuple[Figure, ...]:
    return tuple(Figure(label=label, value="—") for label, _path in _STATUS_FIGURES.get(app, ()))


def _empty_table(app: str, *, message: str) -> OverviewTable:
    return OverviewTable(
        caption=_PRIMARY_TABLE.get(app, app), columns=(), rows=(), empty_message=message
    )


def _dig(body: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = body
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _figures_from_status(app: str, body: dict[str, Any]) -> tuple[Figure, ...]:
    figures = []
    for label, path in _STATUS_FIGURES.get(app, ()):
        value = _dig(body, path)
        figures.append(Figure(label=label, value="—" if value is None else str(value)))
    return tuple(figures)


def _fetch_status(
    settings: Settings, app: str, view: AppView, *, client: httpx.Client
) -> dict[str, Any] | None:
    headers = {}
    token = bearer_token(settings, app)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = client.get(
            f"{view.base_url.rstrip('/')}/api/v1/system/status",
            headers=headers,
            timeout=_STATUS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except Exception:  # noqa: BLE001 — a status call that fails degrades to "—", not an error page
        logger.info("overview.status_unreachable", extra={"app": app})
        return None
    return body if isinstance(body, dict) else None


def _database_url(settings: Settings, app: str) -> tuple[str | None, str | None]:
    """``<app> config show --json``'s ``values.storage.database_url`` (data model §4's "CLI" path).

    Returns:
        ``(url, None)`` on success, ``(None, reason)`` otherwise — never raises: a stopped
        application with no readable configuration is a state this page renders, not an error.
    """
    executable = executable_for(settings, app)
    if executable is None:
        return None, "not installed"
    result = run_command(
        [executable, "config", "show", "--json"], child_environment(), _CONFIG_SHOW_TIMEOUT_SECONDS
    )
    if not result.ok:
        return None, result.failure_text
    try:
        body = json.loads(result.stdout)
        url = body["values"]["storage"]["database_url"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, "config show --json did not answer the expected shape"
    return (str(url) if url else None), (None if url else "no database configured")


def _reflect(engine: Any, name: str) -> Table | None:  # noqa: ANN401 — a SQLAlchemy Engine
    try:
        return Table(name, MetaData(), autoload_with=engine)
    except Exception:  # noqa: BLE001 — an unknown or unreadable table renders "—", not a crash
        return None


def _read_revision(engine: Any) -> str | None:  # noqa: ANN401 — a SQLAlchemy Engine
    try:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT version_num FROM alembic_version")).first()
    except Exception:  # noqa: BLE001 — no alembic_version table is "not known", not a crash
        return None
    return str(row[0]) if row else None


def _known_revision(database: Database, app: str, revision: str | None) -> bool:
    if revision is None:
        return False
    from weightroom.infrastructure.db.models import KnownRevision

    with database.read() as session:
        return session.get(KnownRevision, {"app": app, "revision": revision}) is not None


def _figures_from_database(engine: Any, app: str) -> tuple[Figure, ...]:  # noqa: ANN401
    figures = []
    for name in _FIGURE_TABLES.get(app, ()):
        table = _reflect(engine, name)
        count: int | None = None
        if table is not None:
            try:
                with engine.connect() as connection:
                    count = connection.execute(select(func.count()).select_from(table)).scalar_one()
            except Exception:  # noqa: BLE001 — a table this build cannot read renders "—"
                count = None
        figures.append(
            Figure(label=name.replace("_", " ").title(), value="—" if count is None else str(count))
        )
    return tuple(figures)


def _table_from_database(engine: Any, app: str) -> OverviewTable:  # noqa: ANN401
    name = _PRIMARY_TABLE.get(app, app)
    table = _reflect(engine, name)
    if table is None:
        return _empty_table(app, message=f"{name} is not a table this build knows how to read.")
    order_columns = list(table.primary_key.columns)
    statement = select(table)
    if order_columns:
        statement = statement.order_by(order_columns[0].desc())
    statement = statement.limit(_TABLE_ROW_LIMIT)
    columns = tuple(column.name for column in table.columns)[:_TABLE_COLUMN_LIMIT]
    try:
        with engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
    except Exception:  # noqa: BLE001 — an unreadable table renders as empty, not a crash
        return _empty_table(app, message=f"{name} could not be read.")
    return OverviewTable(
        caption=name,
        columns=columns,
        rows=tuple(tuple("—" if row[c] is None else str(row[c]) for c in columns) for row in rows),
        empty_message=None if rows else f"No rows in {name} yet.",
    )


def overview_for(
    app: str,
    view: AppView,
    *,
    settings: Settings,
    database: Database,
    client: httpx.Client,
) -> Overview:
    """Build one application's Overview: figures, the primary table, and where they came from.

    Args:
        app: One of the four applications.
        view: Its current :class:`~weightroom.services.apps.AppView`.
        settings: The validated settings.
        database: WeightRoomGym's own database, for the :data:`known_revisions <KnownRevision>`
            check (ADR-0123 rule 3).
        client: The pooled HTTP client for the application's own ``/system/status``.

    Returns:
        The Overview. Never raises: every failure path renders ``—`` or an empty table instead.
    """
    figures: tuple[Figure, ...]
    if view.running and view.reachable:
        body = _fetch_status(settings, app, view, client=client)
        figures = _dash_figures(app) if body is None else _figures_from_status(app, body)
    else:
        figures = ()  # filled from the database below, or left dashed if that fails too

    database_url, database_error = _database_url(settings, app)
    if database_url is None:
        table = _empty_table(app, message=f"No database reachable: {database_error}.")
        if not figures:
            figures = _dash_figures(app)
        source = "api" if (view.running and view.reachable) else "none"
        detail = "from the API" if source == "api" else f"unavailable: {database_error}"
        return Overview(source=source, source_detail=detail, figures=figures, table=table)

    other = Database.from_url(database_url)
    try:
        revision = _read_revision(other.engine)
        if revision is not None and not _known_revision(database, app, revision):
            table = _empty_table(
                app,
                message=(
                    f"Schema at revision {revision} is not known to WeightRoomGym — its "
                    "database-sourced pages degrade by name; API-sourced figures are unaffected."
                ),
            )
            if not figures:
                figures = _dash_figures(app)
            source = "api" if (view.running and view.reachable) else "none"
            detail = (
                "from the API" if source == "api" else f"schema at revision {revision} is not known"
            )
            return Overview(source=source, source_detail=detail, figures=figures, table=table)
        table = _table_from_database(other.engine, app)
        if not figures:
            figures = _figures_from_database(other.engine, app)
            source, detail = "database", f"from the database at revision {revision}"
        else:
            source, detail = "api", "from the API"
    finally:
        other.close()
    return Overview(source=source, source_detail=detail, figures=figures, table=table)
