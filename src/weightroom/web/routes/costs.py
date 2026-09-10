"""weightroom.web.routes.costs — the Costs page (spec §7.9, api.md §5).

Read-only: no route here changes anything, so nothing is audited (spec §11 contract 2 covers
state-changing routes; a balance read is not one — the same reasoning ``GET /audit`` and the
database viewer's reads already rest on).
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from weightroom.services.apps import AppUnknown
from weightroom.services.costs import COST_APPS, AppCosts, costs_for
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator, now_of

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["costs"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)


def _costs(request: Request, app: str) -> AppCosts:
    state = request.app.state
    return costs_for(
        state.settings,
        state.database,
        app,
        urls=state.database_urls,
        now=now_of(request),
        monotonic=time.monotonic(),
    )


@router.get("/costs", summary="LoadLedger balances for PromptCadence and IdeaPress")
def get_costs(request: Request, principal: CurrentOperator) -> JSONResponse:
    """Today's window and each application's app-wide ceiling verdict, where one applies."""
    return JSONResponse(content={"apps": [_costs(request, app).as_json() for app in COST_APPS]})


@router.get("/costs/{app}", summary="One application's LoadLedger balance")
def get_app_costs(request: Request, principal: CurrentOperator, app: str) -> JSONResponse:
    """``app`` must be one that mounts LoadLedger's tables — anything else is ``APP_UNKNOWN``,
    the same as an unrecognised name anywhere else in the API."""
    if app not in COST_APPS:
        raise AppUnknown(f"{app!r} keeps no ledger; costs are {', '.join(COST_APPS)}.")
    return JSONResponse(content=_costs(request, app).as_json())


@ui_router.get("/costs", summary="The Costs page", response_class=HTMLResponse)
def costs_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """Today's balance and ceiling verdict per application, ``—`` where nothing is priced.

    The template renders each application's :meth:`~weightroom.services.costs.AppCosts.as_json`
    rather than the dataclass itself, so money is already the text :func:`~weightroom.services.
    costs.money_text` renders it as — a template has no business formatting a :class:`~baseaicore.
    Money` on its own.
    """
    return render_shell_page(
        request,
        "costs.html",
        page="costs",
        principal=principal,
        apps=[(app, _costs(request, app).as_json()) for app in COST_APPS],
    )
