"""weightroom.web.routes.trust — the console's own trust page (session required).

The same fingerprint, steps and download as the trust listener, behind the login: an operator
who is already in can hand the root to a second device without leaving the console.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

from weightroom.services.tls import host_identity
from weightroom.web.rendering import trust_context
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator

__all__ = ["ui_router"]

ui_router = APIRouter(tags=["ui"], include_in_schema=False)


@ui_router.get("/trust", summary="Trust page", response_class=HTMLResponse)
def trust_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The root's fingerprint, its download and the per-OS steps."""
    app = request.app
    identity = getattr(app.state, "identity", None) or host_identity()
    return render_shell_page(
        request,
        "trust.html",
        page="trust",
        principal=principal,
        **trust_context(app.state.settings, tls=app.state.tls, identity=identity),
    )


@ui_router.get("/trust/root.crt", summary="The root certificate")
def root_crt(request: Request, principal: CurrentOperator) -> FileResponse:
    """The public root, as a download."""
    return FileResponse(
        request.app.state.tls.paths.ca_crt,
        media_type="application/x-x509-ca-cert",
        filename="root.crt",
    )
