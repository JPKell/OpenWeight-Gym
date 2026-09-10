"""weightroom.services.health — the one health report the API and the CLI share (spec §17).

Components: ``database``, ``tls`` (days to expiry, degraded under ``renew_before_days``),
``units`` (systemd — not configured until W2) and one ``app:<name>`` per application, ``unknown``
until W2 reads the units and the APIs. Overall status is the worst of the components WeightRoomGym
itself needs — the database and the certificate; a stopped or unknown application never drops
it below ``ok`` (api.md §1).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from baseaicore.timeutil import to_rfc3339

from weightroom.__about__ import __version__
from weightroom.config import APPLICATIONS, Settings
from weightroom.services.database import Database, database_health
from weightroom.services.tls import TlsPaths, TlsStatus, tls_status

__all__ = ["health_report", "system_status"]

_SEVERITY = {"not_configured": 0, "ok": 1, "degraded": 2, "unavailable": 3}


def _component(name: str, status: str, detail: str, **data: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "detail": detail, "data": data}


def _tls_component(settings: Settings, tls: TlsStatus | None, *, now: datetime) -> dict[str, Any]:
    try:
        status = tls or tls_status(TlsPaths.for_settings(settings), now=now)
    except Exception as exc:  # noqa: BLE001 — a health check reports, never raises
        return _component("tls", "unavailable", f"no usable certificate: {exc}")
    days = (status.leaf_not_after - now).days
    verdict = "ok" if days >= settings.tls.renew_before_days else "degraded"
    return _component(
        "tls",
        verdict,
        f"leaf expires in {days} days" if days >= 0 else f"leaf expired {-days} days ago",
        days_to_expiry=days,
        fingerprint_sha256=status.ca_fingerprint_sha256,
    )


def _database_component(settings: Settings, database: Database | None) -> dict[str, Any]:
    try:
        if database is not None:
            status, detail = database_health(database)
        else:
            with Database.from_url(settings.storage.database_url or "") as opened:
                status, detail = database_health(opened)
    except Exception as exc:  # noqa: BLE001 — a health check reports, never raises
        return _component("database", "unavailable", str(exc))
    return _component("database", status, detail)


def health_report(
    settings: Settings,
    *,
    database: Database | None,
    tls: TlsStatus | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The ``GET /health`` body and ``wr-gym health``'s report.

    Args:
        settings: The validated settings.
        database: The serving handle; ``None`` opens one for this check alone (the CLI).
        tls: The runtime's certificate status; ``None`` reads the directory (the CLI).
        now: The clock.

    Returns:
        ``status``, ``application``, ``version``, ``checked_at`` and ``components`` in a stable
        order: ``database``, ``tls``, ``units``, then ``app:<name>`` for each application.
    """
    instant = now or datetime.now(UTC)
    components = [
        _database_component(settings, database),
        _tls_component(settings, tls, now=instant),
        _component("units", "not_configured", "process control arrives at W2"),
        *(
            _component(f"app:{name}", "unknown", "reported from W2 (units and the API)")
            for name in APPLICATIONS
        ),
    ]
    required = [component for component in components if component["name"] in ("database", "tls")]
    overall = max((component["status"] for component in required), key=lambda s: _SEVERITY[s])
    return {
        "status": overall,
        "application": "weightroom",
        "version": __version__,
        "checked_at": to_rfc3339(instant),
        "components": components,
    }


def system_status(
    settings: Settings, *, tls: TlsStatus | None, now: datetime | None = None
) -> dict[str, Any]:
    """The ``GET /system/status`` machine view (spec §17), with ``null`` for what W1 cannot know.

    Every figure a later phase fills in is ``None`` here — never ``0`` (ADR-0016).
    """
    instant = now or datetime.now(UTC)
    return {
        "checked_at": to_rfc3339(instant),
        "applications": {
            name: {
                "state": "unknown",
                "version": None,
                "api_version": None,
                "db_revision": None,
                "known": None,
            }
            for name in APPLICATIONS
        },
        "ollama": None,
        "telemetry": None,
        "costs_today": None,
        "alerts_open": None,
        "jobs_running": None,
        "doctor_last": None,
        "tls_days_to_expiry": None if tls is None else (tls.leaf_not_after - instant).days,
        "bind": {"host": settings.server.host, "port": settings.server.port},
    }
