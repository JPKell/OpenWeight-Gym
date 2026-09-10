"""weightroom.web.routes.system — version, health, system status (api.md §1).

``GET /version`` is the one route that answers without a session (ADR-0026 §5); ``/health``
and ``/system/status`` need one, because their component detail is operational information.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from weightroom.__about__ import __version__
from weightroom.services.health import health_report, system_status
from weightroom.web.session import CurrentOperator, now_of

__all__ = ["API_VERSION", "SCHEMA_VERSION", "router"]

API_VERSION = "v1"
SCHEMA_VERSION = "1"

router = APIRouter(tags=["system"])


@router.get("/version", summary="Application and API versions")
async def version() -> dict[str, str]:
    """Return the application version, the API major and the settings-schema version."""
    return {
        "application": "weightroom",
        "version": __version__,
        "api_version": API_VERSION,
        "schema_version": SCHEMA_VERSION,
    }


@router.get("/health", summary="Component health")
async def health(request: Request, principal: CurrentOperator) -> JSONResponse:
    """The health report; ``200`` for ok/degraded, ``503`` when the database is unavailable."""
    app = request.app
    report = health_report(
        app.state.settings, database=app.state.database, tls=app.state.tls, now=now_of(request)
    )
    return JSONResponse(
        status_code=503 if report["status"] == "unavailable" else 200, content=report
    )


@router.get("/system/status", summary="The machine view")
async def status(request: Request, principal: CurrentOperator) -> dict[str, object]:
    """Spec §17's machine view; every figure a later phase fills in is ``null`` here."""
    app = request.app
    return system_status(app.state.settings, tls=app.state.tls, now=now_of(request))
