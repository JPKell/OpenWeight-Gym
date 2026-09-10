"""``GET /health`` and ``GET /system/status``: the shape, the roll-up, the session requirement."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from tests.support import Console, build_console
from weightroom.config import APPLICATIONS
from weightroom.services.health import health_report


@pytest.fixture
def console(tmp_path: Path) -> Console:
    return build_console(tmp_path)


def test_health_needs_a_session_and_names_every_component(console: Console) -> None:
    assert console.client.get("/api/v1/health").status_code == 401
    console.login()
    response = console.client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["application"] == "weightroom"
    names = [component["name"] for component in body["components"]]
    assert names == ["database", "tls", "units", *(f"app:{name}" for name in APPLICATIONS)]
    by_name = {component["name"]: component for component in body["components"]}
    assert by_name["database"]["status"] == "ok"
    assert by_name["tls"]["status"] == "ok" and by_name["tls"]["data"]["days_to_expiry"] >= 397
    assert by_name["units"]["status"] == "not_configured"
    assert all(by_name[f"app:{name}"]["status"] == "unknown" for name in APPLICATIONS)


def test_tls_degrades_the_roll_up_under_thirty_days_but_an_unknown_app_never_does(
    console: Console,
) -> None:
    later = console.now + timedelta(days=398 - 29)
    body = health_report(console.settings, database=console.database, tls=console.tls, now=later)
    assert body["status"] == "degraded"
    assert next(c for c in body["components"] if c["name"] == "tls")["status"] == "degraded"


def test_a_missing_certificate_directory_is_unavailable_from_the_cli_path(
    console: Console,
) -> None:
    report = health_report(console.settings, database=None, tls=None)
    assert report["status"] == "ok"
    for file in Path(console.settings.tls.directory).iterdir():
        file.unlink()
    report = health_report(console.settings, database=None, tls=None)
    assert report["status"] == "unavailable"


def test_system_status_reports_unknown_and_null_never_zero(console: Console) -> None:
    assert console.client.get("/api/v1/system/status").status_code == 401
    console.login()
    body = console.client.get("/api/v1/system/status").json()
    assert set(body["applications"]) == set(APPLICATIONS)
    assert all(app["state"] == "unknown" for app in body["applications"].values())
    for key in ("ollama", "telemetry", "costs_today", "alerts_open", "jobs_running", "doctor_last"):
        assert body[key] is None
    assert body["tls_days_to_expiry"] >= 397
    assert body["bind"] == {"host": "127.0.0.1", "port": 8769}
    console.advance(hours=1)
    assert body["checked_at"] != console.client.get("/api/v1/system/status").json()["checked_at"]
