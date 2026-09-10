"""weightroom.web.routes.alerts — active alerts, acknowledge, history, the banner (api.md §7).

Acknowledging is the one state-changing action here, and writes one ``alert.ack`` audit row, success
or refusal (spec §11 contract 2). Nothing on these pages sends anything anywhere (spec §3); the
evaluator that raises alerts is ``services/alerts.AlertEvaluator``, on a thread of its own.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urlsplit

from baseaicore import SuiteError
from fastapi import APIRouter, Form, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from mirrorwall import clamp_limit, paginated_response

from weightroom.services.alerts import (
    AlertView,
    acknowledge,
    active_alerts,
    banner,
    history,
    recent_alerts,
)
from weightroom.services.audit import record
from weightroom.services.auth import Principal
from weightroom.web.csrf import render_form_page
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator, now_of

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["alerts"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)


def _acknowledge(request: Request, principal: Principal, alert_id: str) -> AlertView:
    """Acknowledge as this operator, and audit it once."""
    state = request.app.state
    now = now_of(request)
    request_id = getattr(request.state, "request_id", None)
    try:
        view = acknowledge(state.database, alert_id, operator=principal.username, now=now)
    except SuiteError as exc:
        record(
            state.database,
            action="alert.ack",
            actor="operator",
            outcome="refused",
            now=now,
            operator_id=principal.operator_id,
            app="host",
            target=alert_id,
            message=exc.message,
            request_id=request_id,
        )
        raise
    record(
        state.database,
        action="alert.ack",
        actor="operator",
        outcome="ok",
        now=now,
        operator_id=principal.operator_id,
        app="host",
        target=alert_id,
        params={"source": view.source, "subject": view.subject},
        request_id=request_id,
    )
    return view


def _safe_path(target: str) -> str:
    """A same-site path to return to after a form; anything else is the Alerts page."""
    return target if target.startswith("/") and not target.startswith("//") else "/alerts"


@router.get("/alerts", summary="Active alerts, and what the banner shows")
def get_alerts(request: Request, principal: CurrentOperator) -> JSONResponse:
    """Every alert not yet closed, newest first, and the banner's count and newest."""
    database = request.app.state.database
    return JSONResponse(
        content={
            "alerts": [one.as_json() for one in active_alerts(database)],
            "banner": banner(database).as_json(),
        }
    )


@router.post("/alerts/{alert_id}/acknowledge", summary="Acknowledge an alert")
def post_acknowledge(request: Request, principal: CurrentOperator, alert_id: str) -> JSONResponse:
    """A memory-cap alert closes; a condition stays active, off the banner, until it clears."""
    return JSONResponse(content=_acknowledge(request, principal, alert_id).as_json())


@router.get("/alerts/history", summary="What happened to every alert")
def get_history(
    request: Request,
    principal: CurrentOperator,
    limit: int | None = None,
    cursor: str | None = None,
) -> JSONResponse:
    """``opened``, ``seen``, ``acknowledged`` and ``cleared``, newest first; kept for ever."""
    effective = clamp_limit(limit)
    rows, has_more = history(request.app.state.database, limit=effective, before_id=cursor)
    return paginated_response(
        [row.as_json() for row in rows],
        limit=effective,
        next_cursor=rows[-1].id if has_more and rows else None,
        has_more=has_more,
        request_id=getattr(request.state, "request_id", None),
    )


def _page(request: Request, principal: Principal, /, **overrides: Any) -> HTMLResponse:
    from weightroom.services.settings import read_runtime_settings

    state = request.app.state
    database = state.database
    evaluator = getattr(state, "alerts", None)
    interval = read_runtime_settings(database, settings=state.settings)["alerts.interval_seconds"]
    context: dict[str, Any] = {"error": None, **overrides}
    return render_shell_page(
        request,
        "alerts.html",
        page="alerts",
        principal=principal,
        active=active_alerts(database),
        recent=[one for one in recent_alerts(database) if one.closed_at is not None],
        problems=dict(evaluator.problems) if evaluator is not None else {},
        evaluating=evaluator is not None,
        interval_seconds=interval,
        **context,
    )


@ui_router.get("/alerts", summary="The Alerts page", response_class=HTMLResponse)
def alerts_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The active alerts with their evidence, the recently closed ones, and any source the last
    evaluation could not read."""
    return _page(request, principal)


@ui_router.get("/alerts/history", summary="The alert history page", response_class=HTMLResponse)
def history_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The newest two hundred events."""
    rows, has_more = history(request.app.state.database, limit=200)
    return render_shell_page(
        request,
        "alerts_history.html",
        page="alerts",
        principal=principal,
        rows=rows,
        has_more=has_more,
    )


@ui_router.get("/alerts/banner", summary="The banner fragment", response_class=HTMLResponse)
def banner_fragment(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """What every page's banner polls every five seconds."""
    current = urlsplit(request.headers.get("hx-current-url", "")).path
    return render_form_page(
        request,
        "_alert_banner.html",
        alert_banner=banner(request.app.state.database),
        current_path=_safe_path(current),
    )


@ui_router.post("/alerts/{alert_id}/acknowledge", summary="Acknowledge an alert from a page")
def acknowledge_from_page(
    request: Request,
    principal: CurrentOperator,
    alert_id: str,
    next_path: Annotated[str, Form(alias="next")] = "/alerts",
) -> Response:
    """Acknowledge, then back to the page the banner was on."""
    try:
        _acknowledge(request, principal, alert_id)
    except SuiteError as exc:
        return _page(request, principal, error=exc)
    return RedirectResponse(_safe_path(next_path), status_code=status.HTTP_303_SEE_OTHER)
