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
    # W2: systemd is reachable (the console's fake host), and no application is installed in
    # this fixture, so each is `unknown` — not installed is not the same fact as stopped.
    assert by_name["units"]["status"] == "ok"
    assert "0 of 4 units written" in by_name["units"]["detail"]
    assert all(by_name[f"app:{name}"]["status"] == "unknown" for name in APPLICATIONS)
    assert all(by_name[f"app:{name}"]["detail"] == "not installed" for name in APPLICATIONS)


def test_a_host_without_systemd_reports_units_not_configured(tmp_path: Path) -> None:
    """ADR-0125 rule 7: the roll-up stays ``ok`` and the console keeps serving."""
    from weightroom.services.processes import FakeSystemdController

    console = build_console(tmp_path, systemd=FakeSystemdController(supported=False))
    console.login()
    body = console.client.get("/api/v1/health").json()
    by_name = {component["name"]: component for component in body["components"]}
    assert body["status"] == "ok"
    assert by_name["units"]["status"] == "not_configured"
    assert "no systemctl" in by_name["units"]["detail"]


def test_a_stopped_application_never_drops_the_roll_up(tmp_path: Path) -> None:
    from weightroom.services.processes import FakeSystemdController

    executable = tmp_path / "loadcoach"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    console = build_console(
        tmp_path,
        extra_toml=f'[apps.loadcoach]\nexecutable = "{executable}"\n',
        systemd=FakeSystemdController(states={"loadcoach.service": "inactive"}),
    )
    console.login()
    body = console.client.get("/api/v1/health").json()
    by_name = {component["name"]: component for component in body["components"]}
    assert body["status"] == "ok"
    assert by_name["app:loadcoach"]["status"] == "stopped"
    assert by_name["app:loadcoach"]["data"]["unit_state"] == "inactive"


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
    assert all(app["state"] == "not installed" for app in body["applications"].values())
    assert all(app["version"] is None for app in body["applications"].values())
    for key in ("costs_today", "alerts_open", "jobs_running", "doctor_last"):
        assert body[key] is None
    # No sampler tick lands within a synchronous test request, so the live snapshot is still
    # unavailable — the same "unavailable, never zero" claim this test makes about every other
    # not-yet-filled figure (ADR-0016).
    assert body["telemetry"] is None
    # Ollama and the applications are read the same way (W2): the console's own read never
    # raises for an unreachable unit, and the fixture's fake systemd answers "unknown" honestly
    # rather than a guessed state.
    assert body["ollama"]["unit"] == "ollama.service"
    assert body["ollama"]["residency"] == []
    assert body["tls_days_to_expiry"] >= 397
    assert body["bind"] == {"host": "127.0.0.1", "port": 8769}
    console.advance(hours=1)
    assert body["checked_at"] != console.client.get("/api/v1/system/status").json()["checked_at"]
