"""weightroom.web.routes.audit — the trail (api.md §7) and its page."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from mirrorwall import clamp_limit, paginated_response

from weightroom.services.audit import get_audit, list_audit
from weightroom.web.csrf import render_form_page
from weightroom.web.session import CurrentOperator

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["audit"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)


@router.get("/audit", summary="The audit trail")
def audit_list(
    request: Request,
    principal: CurrentOperator,
    app: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    limit: int | None = None,
    cursor: str | None = None,
) -> JSONResponse:
    """A page of rows, newest first, filtered by ``app``, ``action`` and ``since``."""
    effective = clamp_limit(limit)
    rows, has_more = list_audit(
        request.app.state.database,
        limit=effective,
        app=app,
        action=action,
        since=since,
        before_id=cursor,
    )
    return paginated_response(
        [row.as_json() for row in rows],
        limit=effective,
        next_cursor=rows[-1].id if has_more and rows else None,
        has_more=has_more,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/audit/{audit_id}", summary="One audit row")
def audit_detail(request: Request, principal: CurrentOperator, audit_id: str) -> JSONResponse:
    """One row by id; ``404 AUDIT_NOT_FOUND`` otherwise."""
    return JSONResponse(content=get_audit(request.app.state.database, audit_id).as_json())


@ui_router.get("/audit", summary="The audit page", response_class=HTMLResponse)
def audit_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The newest fifty rows, with the filters the API takes."""
    rows, has_more = list_audit(request.app.state.database, limit=50)
    return render_form_page(
        request, "audit.html", page="audit", rows=rows, has_more=has_more, principal=principal
    )
