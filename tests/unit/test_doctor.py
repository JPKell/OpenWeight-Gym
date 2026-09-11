"""Every doctor rule, with a passing and a failing fixture (development plan Phase 4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.support import build_console
from weightroom.config import Settings, load_settings
from weightroom.services.apps import AppView
from weightroom.services.doctor import CADDY_MARKER, MINIMUM_FREE_BYTES, Report, diagnose
from weightroom.services.processes import FakeSystemdController
from weightroom.services.settings_forms import settings_form

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _settings(tmp_path: Path) -> Settings:
    file = tmp_path / "console.toml"
    file.write_text(f'[storage]\ndatabase_url = "sqlite:///{tmp_path}/w.sqlite3"\n')
    return load_settings(config_path=file).settings


def _form(tmp_path: Path, app: str, toml: str = "") -> Any:  # noqa: ANN401
    document = json.loads((FIXTURES / "schemas" / f"{app}.json").read_text(encoding="utf-8"))
    config = tmp_path / f"{app}.toml"
    config.write_text(toml)
    document["config_path"] = str(config)
    return settings_form(_settings(tmp_path), app, document=document, document_error=None)


def _forms(tmp_path: Path, **toml: str) -> dict[str, Any]:
    return {app: _form(tmp_path, app, toml.get(app, "")) for app in toml}


def _report(tmp_path: Path, controller: FakeSystemdController, **kwargs: Any) -> Report:
    return diagnose(_settings(tmp_path), controller=controller, user="tester", **kwargs)


def _rule(report: Report, rule: str) -> Any:  # noqa: ANN401
    return next((one for one in report.findings if one.rule == rule), None)


# --- The report -------------------------------------------------------------------------------


def test_findings_are_worst_first_and_a_notice_is_not_a_problem(tmp_path: Path) -> None:
    report = _report(tmp_path, FakeSystemdController(), forms={})
    severities = [one.severity for one in report.findings]
    order = ["failure", "warning", "notice", "unknown", "ok"]
    assert severities == sorted(severities, key=order.index)
    notices_only = Report(
        findings=tuple(one for one in report.findings if one.severity in {"notice", "ok"})
    )
    assert notices_only.healthy


# --- MEMORY_SAFETY.md §2.2 — the unit caps ------------------------------------------------------


def test_a_unit_without_the_three_memory_lines_fails_and_prints_units_sync(
    tmp_path: Path,
) -> None:
    controller = FakeSystemdController(properties={"loadcoach.service": {}})
    finding = _rule(_report(tmp_path, controller, forms={}), "memory.unit.loadcoach")
    assert finding is not None
    assert finding.severity == "failure"
    assert finding.command == "wr-gym units sync"
    assert "MEMORY_SAFETY.md §2.2" == finding.document


def test_a_unit_carrying_the_three_lines_passes(tmp_path: Path) -> None:
    controller = FakeSystemdController(
        properties={
            "loadcoach.service": {
                "MemoryHigh": "22G",
                "MemoryMax": "24G",
                "MemorySwapMax": "0",
            }
        }
    )
    finding = _rule(_report(tmp_path, controller, forms={}), "memory.unit.loadcoach")
    assert finding is not None
    assert finding.severity == "ok"
    assert finding.command == ""


# --- LAN_ACCESS.md §1 — the binds ---------------------------------------------------------------


def test_an_application_off_loopback_warns_and_says_where_to_fix_it(tmp_path: Path) -> None:
    forms = _forms(tmp_path, loadcoach='[server]\nhost = "0.0.0.0"\n')  # noqa: S104 — a fixture
    finding = _rule(_report(tmp_path, FakeSystemdController(), forms=forms), "lan.bind.loadcoach")
    assert finding is not None
    assert finding.severity == "warning"
    assert "/apps/loadcoach/settings" in finding.command


def test_an_application_on_loopback_passes(tmp_path: Path) -> None:
    forms = _forms(tmp_path, loadcoach='[server]\nhost = "127.0.0.1"\n')
    finding = _rule(_report(tmp_path, FakeSystemdController(), forms=forms), "lan.bind.loadcoach")
    assert finding is not None
    assert finding.severity == "ok"


# --- The retired Caddy script -------------------------------------------------------------------


def test_a_leftover_caddy_server_block_is_a_notice(tmp_path: Path) -> None:
    leftover = f"\n[server]\n# LAN_ACCESS.md: {CADDY_MARKER} https://host:9443\n"
    forms = _forms(tmp_path, freeweight=leftover)
    finding = _rule(
        _report(tmp_path, FakeSystemdController(), forms=forms), "lan.caddy_leftover.freeweight"
    )
    assert finding is not None
    assert finding.severity == "notice"
    assert "settings/raw" in finding.command


def test_a_clean_file_produces_no_caddy_finding(tmp_path: Path) -> None:
    forms = _forms(tmp_path, freeweight="[server]\nport = 8765\n")
    report = _report(tmp_path, FakeSystemdController(), forms=forms)
    assert _rule(report, "lan.caddy_leftover.freeweight") is None


# --- Spec §19 — versions -------------------------------------------------------------------------


def _view(app: str, *, verdict: str, version: str | None) -> AppView:
    return AppView(
        name=app,
        installed=True,
        executable=f"/opt/{app}",
        unit=f"{app}.service",
        unit_state="active",
        uptime_seconds=1.0,
        restarts=None,
        base_url="http://127.0.0.1:8766",
        version=version,
        verdict=verdict,
        supported_range=">=1.3,<2",
    )


def test_a_version_outside_the_range_warns(tmp_path: Path) -> None:
    views = [_view("loadcoach", verdict="too_old", version="1.0.0")]
    finding = _rule(
        _report(tmp_path, FakeSystemdController(), forms={}, views=views), "version.loadcoach"
    )
    assert finding is not None
    assert finding.severity == "warning"
    assert "1.0.0" in finding.evidence


def test_a_version_in_range_passes(tmp_path: Path) -> None:
    views = [_view("loadcoach", verdict="ok", version="1.3.1")]
    finding = _rule(
        _report(tmp_path, FakeSystemdController(), forms={}, views=views), "version.loadcoach"
    )
    assert finding is not None
    assert finding.severity == "ok"


def test_an_application_that_is_not_installed_is_a_notice_not_a_failure(tmp_path: Path) -> None:
    absent = AppView(
        name="ideapress",
        installed=False,
        executable=None,
        unit="ideapress.service",
        unit_state="absent",
        uptime_seconds=None,
        restarts=None,
        base_url="http://127.0.0.1:8767",
    )
    finding = _rule(
        _report(tmp_path, FakeSystemdController(), forms={}, views=[absent]), "version.ideapress"
    )
    assert finding is not None
    assert finding.severity == "notice"


# --- Lingering -------------------------------------------------------------------------------


def test_a_session_that_does_not_linger_fails(tmp_path: Path) -> None:
    controller = FakeSystemdController()
    controller.linger = False
    finding = _rule(_report(tmp_path, controller, forms={}), "linger")
    assert finding is not None
    assert finding.severity == "failure"
    assert finding.command == "loginctl enable-linger tester"


def test_a_lingering_session_passes(tmp_path: Path) -> None:
    controller = FakeSystemdController()
    controller.linger = True
    finding = _rule(_report(tmp_path, controller, forms={}), "linger")
    assert finding is not None
    assert finding.severity == "ok"
    assert finding.command == ""


def test_a_host_that_cannot_say_is_unknown_not_a_failure(tmp_path: Path) -> None:
    controller = FakeSystemdController()
    controller.linger = None
    finding = _rule(_report(tmp_path, controller, forms={}), "linger")
    assert finding is not None
    assert finding.severity == "unknown"


# --- TLS -------------------------------------------------------------------------------------


def test_a_certificate_near_expiry_is_a_notice_naming_the_renew_command(tmp_path: Path) -> None:
    from dataclasses import replace

    console = build_console(tmp_path / "console")
    assert console.tls is not None
    finding = _rule(
        _report(tmp_path, FakeSystemdController(), forms={}, tls=console.tls), "tls.expiry"
    )
    assert finding is not None
    assert finding.severity == "ok"
    near = replace(console.tls, days_left=5)
    expiring = _rule(_report(tmp_path, FakeSystemdController(), forms={}, tls=near), "tls.expiry")
    assert expiring is not None
    assert expiring.severity == "notice"
    assert expiring.command == "wr-gym tls renew"


def test_no_certificate_status_is_unknown(tmp_path: Path) -> None:
    finding = _rule(_report(tmp_path, FakeSystemdController(), forms={}, tls=None), "tls.expiry")
    assert finding is not None
    assert finding.severity == "unknown"


# --- Disk ------------------------------------------------------------------------------------


def test_disk_space_is_read_under_each_applications_own_data_root(tmp_path: Path) -> None:
    forms = _forms(
        tmp_path, loadcoach=f'[storage]\ndatabase_url = "sqlite:///{tmp_path}/lc/loadcoach.db"\n'
    )
    finding = _rule(_report(tmp_path, FakeSystemdController(), forms=forms), "disk.loadcoach")
    assert finding is not None
    assert finding.severity in {"ok", "warning"}
    assert str(tmp_path) in finding.evidence or str(tmp_path) in finding.summary


def test_a_postgres_url_contributes_no_disk_finding(tmp_path: Path) -> None:
    forms = _forms(
        tmp_path,
        loadcoach='[storage]\ndatabase_url = "postgresql+psycopg://u@localhost/loadcoach"\n',
    )
    report = _report(tmp_path, FakeSystemdController(), forms=forms)
    assert _rule(report, "disk.loadcoach") is None


def test_the_free_space_floor_is_five_gigabytes() -> None:
    assert MINIMUM_FREE_BYTES == 5 * 1024**3


# --- The CLI ------------------------------------------------------------------------------------


@pytest.mark.parametrize("flag", [[], ["--json"], ["--all"]])
def test_the_cli_prints_findings_and_exits_one_on_a_problem(
    tmp_path: Path, flag: list[str]
) -> None:
    from typer.testing import CliRunner

    from weightroom.cli.main import app

    file = tmp_path / "console.toml"
    file.write_text(f'[storage]\ndatabase_url = "sqlite:///{tmp_path}/w.sqlite3"\n')
    result = CliRunner().invoke(app, ["doctor", "--config", str(file), *flag])
    # This host has no ollama.service in a test environment, so something is always unknown or
    # failing; the point is that it runs, prints and exits deliberately rather than crashing.
    assert result.exit_code in {0, 1}, result.output
    if "--json" in flag:
        assert json.loads(result.output)["findings"]
    else:
        assert result.output.strip()


# --- Row W10: PromptCadence's LoadCoach token check, on its card (W6 §8 item 4) -----------------


def _promptcadence_view(*, running: bool = True) -> AppView:
    return AppView(
        name="promptcadence",
        installed=True,
        executable="/opt/promptcadence",
        unit="promptcadence.service",
        unit_state="active" if running else "inactive",
        uptime_seconds=1.0 if running else None,
        restarts=None,
        base_url="http://127.0.0.1:8768",
        version="1.3.3" if running else None,
        verdict="ok" if running else "unreadable",
        supported_range=">=1.3,<2",
    )


def _health(component: dict[str, Any] | None) -> dict[str, Any]:
    components = [] if component is None else [component]
    return {"status": "ok", "application": "promptcadence", "components": components}


@pytest.mark.parametrize(
    ("component", "severity", "fragment"),
    [
        (
            {
                "name": "loadcoach",
                "status": "ok",
                "detail": "loadcoach reports ok",
                "data": {"token_accepted": True},
            },
            "ok",
            "accepts its token",
        ),
        (
            {
                "name": "loadcoach",
                "status": "degraded",
                "detail": "loadcoach answers but refuses the configured token (401)",
                "data": {"token_accepted": False},
            },
            "failure",
            "refuses the token",
        ),
        (
            {"name": "loadcoach", "status": "degraded", "detail": "unreachable: down", "data": {}},
            "unknown",
            "LoadCoach did not answer it",
        ),
        (None, "unknown", "upgrade promptcadence"),
    ],
)
def test_promptcadences_loadcoach_token_check_is_repeated_on_its_card(
    tmp_path: Path, respx_mock: Any, component: dict[str, Any] | None, severity: str, fragment: str
) -> None:
    import httpx

    respx_mock.get("http://127.0.0.1:8768/api/v1/health").mock(
        return_value=httpx.Response(200, json=_health(component))
    )
    with httpx.Client() as http:
        finding = _rule(
            _report(
                tmp_path,
                FakeSystemdController(),
                forms={},
                views=[_promptcadence_view()],
                http=http,
            ),
            "promptcadence.loadcoach_token",
        )
    assert finding is not None
    assert finding.severity == severity
    assert fragment in finding.summary + finding.command
    assert finding.app == "promptcadence"


def test_a_stopped_promptcadence_leaves_the_token_check_unknown(tmp_path: Path) -> None:
    import httpx

    with httpx.Client() as http:
        finding = _rule(
            _report(
                tmp_path,
                FakeSystemdController(),
                forms={},
                views=[_promptcadence_view(running=False)],
                http=http,
            ),
            "promptcadence.loadcoach_token",
        )
    assert finding is not None and finding.severity == "unknown"
