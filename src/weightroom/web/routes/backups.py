"""weightroom.web.routes.backups — the Backups page (spec §7.9, api.md §3).

Every application's own `db status`, its own `backups/` directory and the guarded-write backups
WeightRoomGym has taken of it, gathered in one place; the backup/upgrade/restore buttons
themselves stay on each application's own database page (built at W7) — this page does not
duplicate them, only WeightRoomGym's own database, which has no other page to have them on.
"""

from __future__ import annotations

import time
from typing import Annotated, Any

from baseaicore import SuiteError
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from weightroom.config import APPLICATIONS
from weightroom.services.audit import record
from weightroom.services.auth import Principal
from weightroom.services.db_curated import (
    CuratedResult,
    application_backups,
    run_curated,
    run_self_curated,
    self_backups,
)
from weightroom.services.db_guard import list_backups
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator, now_of

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["backups"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)


def _status(state: Any, app: str) -> CuratedResult:  # noqa: ANN401 — FastAPI's untyped app.state
    """``run_curated``'s own status verb, with a not-installed or unreachable application
    reported in the result rather than raised — one missing application must not break the page
    every other row answers on."""
    try:
        return run_curated(state.settings, state.controller, app, "status")
    except SuiteError as exc:
        return CuratedResult(app, "status", (), ok=False, output=None, error=exc.message)


def _overview(request: Request) -> list[dict[str, Any]]:
    state = request.app.state
    rows = []
    for app in APPLICATIONS:
        status = _status(state, app)
        rows.append(
            {
                "app": app,
                "status": status,
                "own_backups": application_backups(
                    state.settings, app, urls=state.database_urls, monotonic=time.monotonic()
                ),
                "guarded_write_backups": list_backups(app),
            }
        )
    rows.append(
        {
            "app": "weightroom",
            "status": run_self_curated(state.database, "status"),
            "own_backups": self_backups(state.database),
            "guarded_write_backups": (),
        }
    )
    return rows


@router.get("/db/status", summary="WeightRoomGym's own db status")
def get_self_status(request: Request, principal: CurrentOperator) -> JSONResponse:
    """``wr-gym db status``, in-process."""
    return JSONResponse(content=run_self_curated(request.app.state.database, "status").as_json())


def _audited_self(request: Request, principal: Principal, verb: str) -> CuratedResult:
    state = request.app.state
    try:
        result = run_self_curated(
            state.database, verb, backup_retention=state.settings.storage.backup_retention
        )
    except SuiteError as exc:
        record(
            state.database,
            action="db.curated",
            actor="operator",
            outcome="refused",
            now=now_of(request),
            operator_id=principal.operator_id,
            app="weightroom",
            target=verb,
            message=exc.message,
            request_id=getattr(request.state, "request_id", None),
        )
        raise
    record(
        state.database,
        action="db.curated",
        actor="operator",
        outcome="ok" if result.ok else "failed",
        now=now_of(request),
        operator_id=principal.operator_id,
        app="weightroom",
        target=result.verb,
        params={"argv": list(result.argv)},
        message=result.error,
        request_id=getattr(request.state, "request_id", None),
    )
    return result


@router.post("/db/backup", summary="WeightRoomGym's own db backup")
def post_self_backup(request: Request, principal: CurrentOperator) -> JSONResponse:
    """``wr-gym db backup``, rotated against ``[storage] backup_retention``."""
    return JSONResponse(content=_audited_self(request, principal, "backup").as_json())


@router.post("/db/upgrade", summary="WeightRoomGym's own db upgrade")
def post_self_upgrade(request: Request, principal: CurrentOperator) -> JSONResponse:
    """``wr-gym db upgrade``, which takes its own backup first."""
    return JSONResponse(content=_audited_self(request, principal, "upgrade").as_json())


# No POST /db/restore: services/db_curated.run_self_curated's own docstring explains why a live
# restore of WeightRoomGym's own database from a request it is itself serving can never succeed —
# there is no route to offer here, only the CLI, with the unit stopped, the way an operator would
# restore any other database WeightRoomGym has no page for.


@router.get("/backups", summary="Every application's backups, curated and guarded-write")
def get_backups(request: Request, principal: CurrentOperator) -> JSONResponse:
    """Each application's own ``db status``, its own ``backups/`` and, where WeightRoomGym has
    taken any, the guarded-write undo copies (``GET /apps/{app}/db/backups``, api.md §3)."""
    return JSONResponse(
        content={
            "apps": [
                {
                    "app": row["app"],
                    "status": row["status"].as_json(),
                    "own_backups": [one.as_json() for one in row["own_backups"]],
                    "guarded_write_backups": [
                        one.as_json() for one in row["guarded_write_backups"]
                    ],
                }
                for row in _overview(request)
            ]
        }
    )


@ui_router.get("/backups", summary="The Backups page", response_class=HTMLResponse)
def backups_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """Every application's status and backups; WeightRoomGym's own status/backup/upgrade
    buttons, since it has no other page to carry them."""
    return render_shell_page(
        request,
        "backups.html",
        page="backups",
        principal=principal,
        rows=_overview(request),
        curated=None,
        curated_error=None,
    )


@ui_router.post("/backups/self", summary="WeightRoomGym's own db verb, from the page")
def self_curated_from_page(
    request: Request, principal: CurrentOperator, verb: Annotated[str, Form()]
) -> HTMLResponse:
    """``status``, ``backup`` or ``upgrade``; ``restore`` answers the refusal in its own words."""
    error: SuiteError | None = None
    result: CuratedResult | None = None
    try:
        result = _audited_self(request, principal, verb)
    except SuiteError as exc:
        error = exc
    return render_shell_page(
        request,
        "backups.html",
        page="backups",
        principal=principal,
        rows=_overview(request),
        curated=result,
        curated_error=error,
    )
