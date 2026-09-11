"""weightroom.web.routes.promptcadence — PromptCadence's pages under its tab (row WP1).

Trajectories, Approvals, Tiers, Tools, Ledger and Egress, at parity with PromptCadence's own console
(its ``web/routes/console.py``), which a browser on the LAN cannot reach: PromptCadence binds
loopback (ADR-0126). Every page reads by spec §7.3's rule (``services/app_pages``) through the
readers in ``services/promptcadence_pages`` and renders through ``render_app_page``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from weightroom.services import promptcadence_pages as pc
from weightroom.services.app_api import stream as app_stream
from weightroom.web.routes.apps import app_view, read_app_page, render_app_page
from weightroom.web.session import CurrentOperator

__all__ = ["ui_router"]

ui_router = APIRouter(tags=["ui"], include_in_schema=False)

APP = pc.APP
BASE = "/apps/promptcadence"


def _href(path: str, **query: Any) -> str:
    """``path`` with the query parameters that carry a value, so a pager keeps the filters."""
    from urllib.parse import urlencode

    kept = {key: value for key, value in query.items() if value not in (None, "")}
    return f"{path}?{urlencode(kept)}" if kept else path


@ui_router.get(f"{BASE}/trajectories", summary="Trajectories", response_class=HTMLResponse)
def trajectories_page(
    request: Request,
    principal: CurrentOperator,
    state: str | None = None,
    cursor: str | None = None,
    page: int = 1,
) -> HTMLResponse:
    """Every trajectory, newest first, filterable by state."""
    view = app_view(request, APP)
    client, settings = request.app.state.http, request.app.state.settings
    wanted = state or None
    sourced = read_app_page(
        request,
        view,
        api=lambda: pc.trajectories_api(client, settings, state=wanted, cursor=cursor or None),
        database=lambda handle: pc.trajectories_db(handle, state=wanted, page=page),
    )
    data = sourced.data or {}
    next_href = None
    if data.get("next_cursor"):
        next_href = _href(f"{BASE}/trajectories", state=wanted, cursor=data["next_cursor"])
    elif data.get("next_page"):
        next_href = _href(f"{BASE}/trajectories", state=wanted, page=data["next_page"])
    return render_app_page(
        request,
        principal,
        APP,
        "pc_trajectories.html",
        selected="Trajectories",
        view=view,
        sourced=sourced,
        state=wanted or "",
        states=pc.TRAJECTORY_STATES,
        next_href=next_href,
    )


@ui_router.get(
    f"{BASE}/trajectories/{{trajectory_id}}", summary="One trajectory", response_class=HTMLResponse
)
def trajectory_page(
    request: Request, principal: CurrentOperator, trajectory_id: str
) -> HTMLResponse:
    """One trajectory's whole record: request, plan, envelopes, turns, tools, debits, egress."""
    view = app_view(request, APP)
    client, settings = request.app.state.http, request.app.state.settings
    sourced = read_app_page(
        request,
        view,
        api=lambda: pc.trajectory_api(client, settings, trajectory_id),
        database=lambda handle: pc.trajectory_db(handle, trajectory_id),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "pc_trajectory.html",
        selected="Trajectories",
        view=view,
        sourced=sourced,
        trajectory_id=trajectory_id,
        events_url=f"{BASE}/trajectories/{pc.segment(trajectory_id)}/events",
    )


@ui_router.get(f"{BASE}/trajectories/{{trajectory_id}}/events", summary="A trajectory, live")
def trajectory_events(
    request: Request, principal: CurrentOperator, trajectory_id: str
) -> StreamingResponse:
    """PromptCadence's trajectory stream, proxied as the console's log-pane frames."""
    chunks = app_stream(
        request.app.state.http,
        request.app.state.settings,
        APP,
        f"trajectories/{pc.segment(trajectory_id)}/stream",
        last_event_id=request.headers.get("last-event-id"),
    )
    return StreamingResponse(
        pc.event_log_frames(chunks),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )


@ui_router.get(f"{BASE}/approvals", summary="Approvals", response_class=HTMLResponse)
def approvals_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """What is waiting for a person, and every request ever raised."""
    from weightroom.services.chat_promptcadence import token_can_approve

    view = app_view(request, APP)
    client, settings = request.app.state.http, request.app.state.settings
    pending = read_app_page(
        request, view, api=lambda: pc.pending_api(client, settings), database=pc.pending_db
    )
    history = read_app_page(request, view, api=None, database=pc.requests_db)
    return render_app_page(
        request,
        principal,
        APP,
        "pc_approvals.html",
        selected="Approvals",
        view=view,
        pending=pending,
        history=history,
        can_approve=token_can_approve(settings) if pending.live else None,
    )


@ui_router.get(f"{BASE}/tiers", summary="Tiers", response_class=HTMLResponse)
def tiers_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """Every configured tier, its ceiling, and whether it can serve right now."""
    view = app_view(request, APP)
    client, settings = request.app.state.http, request.app.state.settings
    sourced = read_app_page(
        request, view, api=lambda: pc.tiers_api(client, settings), database=None
    )
    return render_app_page(
        request, principal, APP, "pc_tiers.html", selected="Tiers", view=view, sourced=sourced
    )


@ui_router.get(f"{BASE}/tools", summary="Tools", response_class=HTMLResponse)
def tools_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The tool registry, withheld tools with their cause, and the isolation rung."""
    view = app_view(request, APP)
    client, settings = request.app.state.http, request.app.state.settings
    sourced = read_app_page(
        request, view, api=lambda: pc.tools_api(client, settings), database=None
    )
    return render_app_page(
        request, principal, APP, "pc_tools.html", selected="Tools", view=view, sourced=sourced
    )


@ui_router.get(f"{BASE}/ledger", summary="Ledger", response_class=HTMLResponse)
def ledger_page(
    request: Request,
    principal: CurrentOperator,
    trajectory_id: str | None = None,
    tag: str | None = None,
) -> HTMLResponse:
    """Today's position against every ceiling, and the recorded debits behind it."""
    view = app_view(request, APP)
    client, settings = request.app.state.http, request.app.state.settings
    wanted, tagged = trajectory_id or None, tag or None
    sourced = read_app_page(
        request,
        view,
        api=lambda: pc.ledger_api(client, settings, trajectory_id=wanted, tag=tagged),
        database=lambda handle: pc.ledger_db(handle, trajectory_id=wanted),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "pc_ledger.html",
        selected="Ledger",
        view=view,
        sourced=sourced,
        trajectory_id=wanted or "",
        tag=tagged or "",
    )


@ui_router.get(f"{BASE}/egress", summary="Egress decisions", response_class=HTMLResponse)
def egress_page(
    request: Request,
    principal: CurrentOperator,
    verdict: str | None = None,
    trajectory_id: str | None = None,
) -> HTMLResponse:
    """Every decision about whether data could leave, newest first, approvals and refusals alike."""
    view = app_view(request, APP)
    wanted_verdict, wanted_trajectory = verdict or None, trajectory_id or None
    sourced = read_app_page(
        request,
        view,
        api=None,
        database=lambda handle: pc.egress_db(
            handle, verdict=wanted_verdict, trajectory_id=wanted_trajectory
        ),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "pc_egress.html",
        selected="Egress",
        view=view,
        sourced=sourced,
        verdict=wanted_verdict or "",
        verdicts=pc.VERDICTS,
        trajectory_id=wanted_trajectory or "",
    )
