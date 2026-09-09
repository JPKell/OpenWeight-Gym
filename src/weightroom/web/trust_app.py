"""weightroom.web.trust_app — the plain-HTTP trust listener (ADR-0126 rule 3).

A second, tiny Starlette application on ``server.trust_port`` serving **exactly two routes**:
``GET /root.crt`` (the root certificate, public by definition) and ``GET /trust`` (the
fingerprint and the per-OS steps). No cookie is ever set, no login exists, and every other
path is ``404`` — a phone cannot fetch the certificate over a TLS session it does not yet
trust, and that is the only reason plain HTTP is served anywhere in the suite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from baseaicore import new_id
from mirrorwall import HostValidationMiddleware, RequestIdMiddleware, error_body
from starlette.applications import Starlette
from starlette.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.routing import Route

from weightroom.web.hosts import resolve_allowed_hosts
from weightroom.web.rendering import render, trust_context

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

    from weightroom.config import Settings
    from weightroom.services.tls import HostIdentity, TlsStatus

__all__ = ["create_trust_app"]


def create_trust_app(settings: Settings, *, tls: TlsStatus, identity: HostIdentity) -> Starlette:
    """Build the trust listener.

    Args:
        settings: For the Host allowlist and the URLs the page prints.
        tls: The certificate to hand out and describe.
        identity: The host's names, for the URLs.

    Returns:
        A Starlette app with two routes and a 404 for everything else, no cookies anywhere.
    """
    context = trust_context(settings, tls=tls, identity=identity)

    async def root_crt(request: Request) -> Response:
        return FileResponse(
            tls.paths.ca_crt,
            media_type="application/x-x509-ca-cert",
            filename="root.crt",
            headers={"Cache-Control": "no-store"},
        )

    async def trust_page(request: Request) -> Response:
        return HTMLResponse(render("trust_standalone.html", **context))

    async def not_found(request: Request, exc: Exception) -> Response:
        request_id = getattr(request.state, "request_id", None) or new_id()
        return JSONResponse(
            status_code=404,
            content=error_body(
                code="NOT_FOUND",
                message="The trust listener serves /root.crt and /trust only (ADR-0126 rule 3).",
                request_id=request_id,
            ),
            headers={"X-Request-ID": request_id, "Cache-Control": "no-store"},
        )

    app = Starlette(
        routes=[
            Route("/root.crt", root_crt, methods=["GET", "HEAD"]),
            Route("/trust", trust_page, methods=["GET", "HEAD"]),
        ],
        exception_handlers={404: not_found, 405: not_found},
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(HostValidationMiddleware, allowed_hosts=resolve_allowed_hosts(settings))
    return app
