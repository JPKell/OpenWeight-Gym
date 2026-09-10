"""weightroom.web.routes.databases — every application's database, read-only (api.md §3).

The read half of row W7 (spec §7.8): the revision against ``known_revisions``, the tables with
their row counts and locks, a page of rows, and the SQL console. Every route opens the
application's database read-only for the length of the request and closes it
(``services/db_reader.py``). An unknown revision is ``409 SCHEMA_UNKNOWN`` in JSON and a page that
says so by name in HTML (ADR-0123 rule 3). The console is a ``POST`` and leaves one ``db.query``
audit row whatever happens to the statement (spec §11 contract 2).
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Final
from urllib.parse import quote, urlencode

from baseaicore import SuiteError
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from weightroom.config import APPLICATIONS
from weightroom.domain.guard import GuardStatementRefused, lock_for
from weightroom.services.apps import require_app
from weightroom.services.audit import record
from weightroom.services.db_reader import (
    CONSOLE_ROW_CAP,
    AppDatabase,
    AppDatabaseUnavailable,
    QueryResult,
    ReadFailed,
    SchemaUnknown,
    list_tables,
    open_app_database,
    revision_summary,
    run_query,
    table_page,
)
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator, now_of

__all__ = ["open_for", "router", "ui_router"]

router = APIRouter(tags=["databases"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)

_SQL_MAX_CHARS: Final = 100_000


class QueryBody(BaseModel):
    """``POST /apps/{app}/db/query``'s body."""

    model_config = ConfigDict(extra="forbid")

    sql: str = Field(max_length=_SQL_MAX_CHARS)


def open_for(request: Request, app: str, *, require_known: bool = True) -> AppDatabase:
    """The application's database, read-only, for this request; the caller closes it."""
    state = request.app.state
    return open_app_database(
        state.settings,
        state.database,
        app,
        urls=state.database_urls,
        now=time.monotonic(),
        require_known=require_known,
    )


def _record_query(
    request: Request,
    principal: Any,  # noqa: ANN401 — a Principal
    app: str,
    sql: str,
    *,
    outcome: str,
    result: QueryResult | None = None,
    message: str | None = None,
) -> None:
    record(
        request.app.state.database,
        action="db.query",
        actor="operator",
        outcome=outcome,
        now=now_of(request),
        operator_id=principal.operator_id,
        app=app,
        target=", ".join(result.statement.tables) or None if result is not None else None,
        params={} if result is None else {"rows": len(result.rows), "truncated": result.truncated},
        message=message,
        statement=sql,
        request_id=getattr(request.state, "request_id", None),
    )


def _audited_query(
    request: Request,
    principal: Any,  # noqa: ANN401 — a Principal
    app: str,
    sql: str,
) -> QueryResult:
    """Run one console statement and leave exactly one ``db.query`` row, refused or not."""
    try:
        with open_for(request, app) as handle:
            result = run_query(handle, sql)
    except Exception as exc:
        refused = isinstance(exc, (GuardStatementRefused, SchemaUnknown))
        _record_query(
            request,
            principal,
            app,
            sql,
            outcome="refused" if refused else "failed",
            message=getattr(exc, "message", str(exc)),
        )
        raise
    _record_query(request, principal, app, sql, outcome="ok", result=result)
    return result


# --- JSON ------------------------------------------------------------------------------------


@router.get("/apps/{app}/db/revision", summary="The schema revision against known_revisions")
def get_revision(request: Request, principal: CurrentOperator, app: str) -> JSONResponse:
    """``alembic_version``, whether this console knows it, and the revisions it does."""
    with open_for(request, require_app(app), require_known=False) as handle:
        return JSONResponse(content=handle.revision.as_json())


@router.get("/apps/{app}/db/tables", summary="Tables, row counts and locks")
def get_tables(request: Request, principal: CurrentOperator, app: str) -> JSONResponse:
    """Every table with its count, ``writable`` and, when locked, ``reason``."""
    with open_for(request, require_app(app)) as handle:
        tables = list_tables(handle)
        return JSONResponse(
            content={
                "revision": handle.revision.as_json(),
                "tables": [one.as_json() for one in tables],
            }
        )


@router.get("/apps/{app}/db/tables/{table}", summary="A page of rows, columns typed")
def get_rows(
    request: Request,
    principal: CurrentOperator,
    app: str,
    table: str,
    page: int = 1,
    sort: str | None = None,
    desc: bool = False,
    column: str | None = None,
    filter_text: Annotated[str | None, Query(alias="filter")] = None,
) -> JSONResponse:
    """One page of ``table``, sorted by ``sort`` (the primary key otherwise), filtered by
    ``column`` containing ``filter``."""
    with open_for(request, require_app(app)) as handle:
        grid = table_page(
            handle,
            table,
            page=page,
            sort=sort or None,
            descending=desc,
            column_name=column or None,
            contains=filter_text or None,
        )
        return JSONResponse(content=grid.as_json())


@router.post("/apps/{app}/db/query", summary="One SELECT on a read-only connection")
def post_query(
    request: Request, principal: CurrentOperator, app: str, body: QueryBody
) -> JSONResponse:
    """30 s, 10 000 rows; anything but one ``SELECT`` is ``GUARD_STATEMENT_REFUSED``."""
    result = _audited_query(request, principal, require_app(app), body.sql)
    return JSONResponse(content=result.as_json())


# --- Pages -----------------------------------------------------------------------------------


def _page(
    request: Request,
    principal: Any,  # noqa: ANN401 — a Principal
    app: str,
    template: str,
    /,
    **context: Any,
) -> HTMLResponse:
    from weightroom.web.rendering import app_side_nav, app_side_nav_stubs

    return render_shell_page(
        request,
        template,
        page="apps",
        principal=principal,
        app=app,
        active_app=app,
        nav_sections=app_side_nav(app, selected="Database"),
        side_nav_stubs=app_side_nav_stubs(app),
        row_cap=CONSOLE_ROW_CAP,
        **context,
    )


def _tables_context(request: Request, app: str) -> dict[str, Any]:
    """The revision and the tables, or why there are none — never an error page."""
    try:
        with open_for(request, app, require_known=False) as handle:
            tables = list_tables(handle) if handle.revision.is_known else ()
            return {"revision": handle.revision, "tables": tables, "unavailable": None}
    except AppDatabaseUnavailable as exc:
        return {"revision": None, "tables": (), "unavailable": exc.message}


@ui_router.get("/database", summary="Every application's database", response_class=HTMLResponse)
def databases_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The four databases: where each is, its revision, and whether this console knows it."""
    state = request.app.state
    databases = []
    for app in APPLICATIONS:
        revision, reason = revision_summary(
            state.settings, state.database, app, urls=state.database_urls, now=time.monotonic()
        )
        databases.append({"app": app, "revision": revision, "reason": reason})
    return render_shell_page(
        request, "databases.html", page="database", principal=principal, databases=databases
    )


@ui_router.get(
    "/apps/{app}/database",
    summary="An application's tables and console",
    response_class=HTMLResponse,
)
def database_page(request: Request, principal: CurrentOperator, app: str) -> HTMLResponse:
    """The tables with counts and locks, and the SQL console."""
    name = require_app(app)
    return _page(
        request,
        principal,
        name,
        "database.html",
        sql="",
        result=None,
        query_error=None,
        **_tables_context(request, name),
    )


@ui_router.post("/apps/{app}/database/query", summary="Run the console from the page")
def query_from_page(
    request: Request,
    principal: CurrentOperator,
    app: str,
    sql: Annotated[str, Form(max_length=_SQL_MAX_CHARS)] = "",
) -> HTMLResponse:
    """The console's form post: the result, or the refusal in its own words, on the same page."""
    name = require_app(app)
    result: QueryResult | None = None
    error: SuiteError | None = None
    try:
        result = _audited_query(request, principal, name, sql)
    except SuiteError as exc:
        error = exc
    return _page(
        request,
        principal,
        name,
        "database.html",
        sql=sql,
        result=result,
        query_error=error,
        **_tables_context(request, name),
    )


def _grid_href(app: str, table: str, **params: Any) -> str:
    kept = {key: value for key, value in params.items() if value not in (None, "", False)}
    query = f"?{urlencode(kept)}" if kept else ""
    return f"/apps/{app}/database/{quote(table, safe='')}{query}"


@ui_router.get(
    "/apps/{app}/database/{table}", summary="A table's rows", response_class=HTMLResponse
)
def table_rows_page(
    request: Request,
    principal: CurrentOperator,
    app: str,
    table: str,
    page: int = 1,
    sort: str | None = None,
    desc: bool = False,
    column: str | None = None,
    filter_text: Annotated[str | None, Query(alias="filter")] = None,
) -> HTMLResponse:
    """A page of rows with the sort and filter form; a lock says so above the grid."""
    name = require_app(app)
    context: dict[str, Any] = {
        "table_name": table,
        "lock": lock_for(name, table),
        "grid": None,
        "grid_error": None,
        "revision": None,
        "unavailable": None,
        "previous_href": None,
        "next_href": None,
        "clear_href": _grid_href(name, table),
    }
    try:
        with open_for(request, name, require_known=False) as handle:
            context["revision"] = handle.revision
            if handle.revision.is_known:
                grid = table_page(
                    handle,
                    table,
                    page=page,
                    sort=sort or None,
                    descending=desc,
                    column_name=column or None,
                    contains=filter_text or None,
                )
                context["grid"] = grid
                shared = {"sort": grid.sort, "desc": grid.descending, "column": grid.column}
                shared["filter"] = grid.contains
                if grid.page > 1:
                    context["previous_href"] = _grid_href(name, table, page=grid.page - 1, **shared)
                if grid.pages is not None and grid.page < grid.pages:
                    context["next_href"] = _grid_href(name, table, page=grid.page + 1, **shared)
    except AppDatabaseUnavailable as exc:
        context["unavailable"] = exc.message
    except ReadFailed as exc:
        context["grid_error"] = exc.message
    return _page(request, principal, name, "database_table.html", **context)
