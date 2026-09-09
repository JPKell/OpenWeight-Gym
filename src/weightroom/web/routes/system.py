"""weightroom.web.routes.system — version, health, system status (api.md §1).

``GET /version`` is the one route that answers without a session (ADR-0026 §5).
"""

from __future__ import annotations

from fastapi import APIRouter

from weightroom.__about__ import __version__

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
