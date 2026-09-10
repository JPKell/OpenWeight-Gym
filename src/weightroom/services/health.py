"""weightroom.services.health — the one health report the API and the CLI share (spec §17).

Components: ``database``, ``tls`` (days to expiry, degraded under ``renew_before_days``),
``units`` (whether systemd is reachable at all) and one ``app:<name>`` per application. Overall
status is the worst of the components WeightRoomGym itself needs — the database and the
certificate; a stopped or unknown application never drops it below ``ok`` (api.md §1), because a
console whose own health goes red when the operator deliberately stops an application is a
console whose health nobody reads.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from baseaicore.timeutil import to_rfc3339

from weightroom.__about__ import __version__
from weightroom.config import APPLICATIONS, Settings
from weightroom.services.apps import AppView
from weightroom.services.database import Database, database_health
from weightroom.services.tls import TlsPaths, TlsStatus, tls_status

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["health_report", "system_status"]

_SEVERITY = {"not_configured": 0, "ok": 1, "degraded": 2, "unavailable": 3}

_APP_STATUS: dict[str, str] = {
    "ok": "ok",
    "starting": "degraded",
    "stopped": "stopped",
    "failed": "degraded",
    "version mismatch": "degraded",
    "not installed": "unknown",
    "unsupported": "unknown",
}
"""A pill to the health vocabulary spec §17 uses (``ok``/``degraded``/``stopped``/``unknown``)."""


def _app_component(view: AppView) -> dict[str, Any]:
    detail = view.pill if view.error is None else f"{view.pill} ({view.error})"
    return _component(
        f"app:{view.name}",
        _APP_STATUS.get(view.pill, "unknown"),
        detail,
        unit=view.unit,
        unit_state=view.unit_state,
        version=view.version,
        version_verdict=view.verdict,
        uptime_seconds=view.uptime_seconds,
    )


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
    views: Sequence[AppView] | None = None,
) -> dict[str, Any]:
    """The ``GET /health`` body and ``wr-gym health``'s report.

    Args:
        settings: The validated settings.
        database: The serving handle; ``None`` opens one for this check alone (the CLI).
        tls: The runtime's certificate status; ``None`` reads the directory (the CLI).
        now: The clock.
        views: The applications as W2's inventory sees them; ``None`` (a caller with no systemd
            boundary to hand) leaves each ``unknown`` rather than guessing.

    Returns:
        ``status``, ``application``, ``version``, ``checked_at`` and ``components`` in a stable
        order: ``database``, ``tls``, ``units``, then ``app:<name>`` for each application.
    """
    instant = now or datetime.now(UTC)
    if views is None:
        units = _component("units", "not_configured", "no systemd boundary was supplied")
        app_components = [
            _component(f"app:{name}", "unknown", "not read on this call") for name in APPLICATIONS
        ]
    elif all(view.unit_state == "unsupported" for view in views):
        units = _component("units", "not_configured", "unsupported on this host: no systemctl")
        app_components = [_app_component(view) for view in views]
    else:
        written = sum(1 for view in views if view.unit_state != "absent")
        units = _component(
            "units", "ok", f"systemd reachable; {written} of {len(views)} units written"
        )
        app_components = [_app_component(view) for view in views]
    components = [
        _database_component(settings, database),
        _tls_component(settings, tls, now=instant),
        units,
        *app_components,
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
    settings: Settings,
    *,
    tls: TlsStatus | None,
    now: datetime | None = None,
    views: Sequence[AppView] | None = None,
    ollama: dict[str, Any] | None = None,
    telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The ``GET /system/status`` machine view (spec §17), with ``null`` for what is not known.

    Every figure a later phase fills in is ``None`` here — never ``0`` (ADR-0016).
    """
    instant = now or datetime.now(UTC)
    by_name = {view.name: view for view in views or ()}
    return {
        "checked_at": to_rfc3339(instant),
        "applications": {
            name: (
                {
                    "state": by_name[name].pill,
                    "unit_state": by_name[name].unit_state,
                    "version": by_name[name].version,
                    "api_version": by_name[name].api_version,
                    "uptime_seconds": by_name[name].uptime_seconds,
                    "db_revision": None,
                    "known": None,
                }
                if name in by_name
                else {
                    "state": "unknown",
                    "unit_state": None,
                    "version": None,
                    "api_version": None,
                    "uptime_seconds": None,
                    "db_revision": None,
                    "known": None,
                }
            )
            for name in APPLICATIONS
        },
        "ollama": ollama,
        "telemetry": telemetry,
        "costs_today": None,
        "alerts_open": None,
        "jobs_running": None,
        "doctor_last": None,
        "tls_days_to_expiry": None if tls is None else (tls.leaf_not_after - instant).days,
        "bind": {"host": settings.server.host, "port": settings.server.port},
    }
