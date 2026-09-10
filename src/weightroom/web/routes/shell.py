"""weightroom.web.routes.shell — the placeholder shell behind the login (Phase 1).

The real shell — the four tabs with status dots, the telemetry strip, the left menus — is
Phase 3 over MirrorWall 0.3 (design brief §3). Until then this page says what is here and what
is not.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from weightroom.config import APPLICATIONS
from weightroom.web.csrf import render_form_page
from weightroom.web.session import CurrentOperator

__all__ = ["ui_router"]

ui_router = APIRouter(tags=["ui"], include_in_schema=False)


@ui_router.get("/", summary="The shell", response_class=HTMLResponse)
def shell(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The shell: who is logged in, the certificate's days left, and the four tabs as stubs."""
    tls = request.app.state.tls
    return render_form_page(
        request,
        "shell.html",
        page="shell",
        principal=principal,
        applications=APPLICATIONS,
        tls_days_left=None if tls is None else tls.days_left,
        bind_host=request.app.state.settings.server.host,
    )
