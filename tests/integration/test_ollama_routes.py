"""The Ollama pane and its one button (api.md §5, ADR-0125 rules 4–5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import respx

from tests.support import JSON_HEADERS, Console, build_console
from weightroom.services.ollama import POLKIT_RULE_PATH
from weightroom.services.processes import FakeSystemdController

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ollama"
OLLAMA_URL = "http://127.0.0.1:11434"

# What `systemctl restart ollama.service` says on a host with no polkit grant. Measured on the
# reference machine at row W2, with `--no-ask-password`.
REFUSAL = (
    "Failed to restart ollama.service: Access denied as the requested operation requires "
    "interactive authentication. However, interactive authentication has not been enabled by "
    "the calling program."
)


def _fixture(name: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value
    return fields


def _console(tmp_path: Path, *, fixture: str = "safe-applied.txt", **kwargs: Any) -> Console:
    host = FakeSystemdController(
        states={"ollama.service": "active"},
        properties={"ollama.service": _fixture(fixture)},
        **kwargs,
    )
    return build_console(tmp_path, systemd=host)


@respx.mock
def test_the_pane_is_green_once_the_script_has_been_applied(tmp_path: Path) -> None:
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(tmp_path)
    console.login()
    body = console.client.get("/api/v1/ollama").json()
    assert body["safe"] is True
    assert body["passing"] == body["total"] == 7
    assert [finding["outcome"] for finding in body["findings"]] == ["pass"] * 7
    page = console.client.get("/ollama", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "apply_memory_safety.sh" not in page.text


@respx.mock
def test_the_pane_is_red_on_the_reference_machines_pre_fix_unit_and_prints_the_script(
    tmp_path: Path,
) -> None:
    """Plan Phase 2 criterion 3, against the configuration that caused the 2026-09-09 reset."""
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(tmp_path, fixture="unsafe-112000-no-cap.txt")
    console.login()
    body = console.client.get("/api/v1/ollama").json()
    assert body["safe"] is False
    assert body["passing"] == 0
    assert body["apply_script"] == "docs/scripts/apply_memory_safety.sh"
    page = console.client.get("/ollama", headers={"Accept": "text/html"}).text
    assert "docs/scripts/apply_memory_safety.sh" in page
    assert "112000" in page
    assert "no cap" in page


@respx.mock
def test_the_unit_is_read_from_the_system_scope_never_the_user_one(tmp_path: Path) -> None:
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(tmp_path)
    console.login()
    console.client.get("/api/v1/ollama")
    assert console.host is not None
    assert ("properties", "system", "ollama.service") in console.host.calls


@respx.mock
def test_residency_comes_through_modelrack_and_an_absent_figure_is_null_never_zero(
    tmp_path: Path,
) -> None:
    """ADR-0016 and ADR-0123 rule 5: one Ollama client in the suite, and `—` is not `0`."""
    respx.get(f"{OLLAMA_URL}/api/ps").mock(
        return_value=httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "gemma4:12b-it-q8_0",
                        "size_vram": 12_000_000_000,
                        "size": 12_500_000_000,
                    }
                ]
            },
        )
    )
    console = _console(tmp_path)
    console.login()
    body = console.client.get("/api/v1/ollama/ps").json()
    assert body["error"] is None
    assert body["resident"][0]["name"] == "gemma4:12b-it-q8_0"
    assert body["resident"][0]["vram_bytes"] == 12_000_000_000
    # Ollama's /api/ps says nothing about the served context in this payload.
    assert body["resident"][0]["context_length"] is None


@respx.mock
def test_a_daemon_that_does_not_answer_is_a_state_not_an_error(tmp_path: Path) -> None:
    respx.get(f"{OLLAMA_URL}/api/ps").mock(side_effect=httpx.ConnectError("refused"))
    console = _console(tmp_path)
    console.login()
    body = console.client.get("/api/v1/ollama").json()
    assert body["residency"] == []
    assert body["residency_error"]
    assert console.client.get("/ollama", headers={"Accept": "text/html"}).status_code == 200


@respx.mock
def test_the_journal_is_reported_unreadable_by_name_when_it_is(tmp_path: Path) -> None:
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(tmp_path)  # the console's default reader has no journalctl
    console.login()
    body = console.client.get("/api/v1/ollama").json()
    assert body["journal_readable"] is False
    assert "journal not readable" in body["journal_detail"]
    page = console.client.get("/ollama", headers={"Accept": "text/html"}).text
    assert "Journal not readable" in page
    assert "systemd-journal" in page


@respx.mock
def test_the_grant_is_unknown_until_something_has_been_tried(tmp_path: Path) -> None:
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(tmp_path)
    console.login()
    assert console.client.get("/api/v1/ollama").json()["restart_permitted"] == "unknown"
    page = console.client.get("/ollama", headers={"Accept": "text/html"}).text
    assert "not yet known" in page


@respx.mock
def test_a_permitted_restart_succeeds_audits_and_the_grant_becomes_known(tmp_path: Path) -> None:
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(tmp_path)
    console.login()
    response = console.client.post("/api/v1/ollama/restart", headers=JSON_HEADERS)
    assert response.status_code == 202
    assert console.host is not None
    assert ("act", "system", "ollama.service", "restart") in console.host.calls
    row = console.client.get(f"/api/v1/audit/{response.json()['audit_id']}").json()
    assert row["action"] == "ollama.restart"
    assert row["app"] == "ollama"
    assert row["outcome"] == "ok"
    assert console.client.get("/api/v1/ollama").json()["restart_permitted"] == "permitted"


@respx.mock
def test_a_refused_restart_carries_the_rule_the_install_command_and_a_refused_row(
    tmp_path: Path,
) -> None:
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(tmp_path, refuse={("ollama.service", "restart"): REFUSAL})
    console.login()
    response = console.client.post("/api/v1/ollama/restart", headers=JSON_HEADERS)
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "OLLAMA_RESTART_NOT_PERMITTED"
    details = error["details"]
    assert details["command"] == "systemctl restart ollama.service"
    assert details["rule_path"] == POLKIT_RULE_PATH
    assert 'action.lookup("unit") == "ollama.service"' in details["rule"]
    assert "install -m 0644" in details["install"]
    rows = console.client.get("/api/v1/audit?action=ollama.restart").json()["items"]
    assert len(rows) == 1
    assert rows[0]["outcome"] == "refused"
    # The refused row is the probe: the pane now says so rather than offering a button that fails.
    assert console.client.get("/api/v1/ollama").json()["restart_permitted"] == "not_permitted"
    page = console.client.get("/ollama", headers={"Accept": "text/html"}).text
    assert "not permitted" in page


@respx.mock
def test_a_daemon_that_will_not_restart_is_not_reported_as_a_missing_grant(tmp_path: Path) -> None:
    """*You may not* and *it would not come back* are different facts and different fixes."""
    respx.get(f"{OLLAMA_URL}/api/ps").mock(return_value=httpx.Response(200, json={"models": []}))
    console = _console(
        tmp_path,
        refuse={("ollama.service", "restart"): "Job for ollama.service failed: exit-code 203"},
    )
    console.login()
    response = console.client.post("/api/v1/ollama/restart", headers=JSON_HEADERS)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UNIT_ACTION_FAILED"
    rows = console.client.get("/api/v1/audit?action=ollama.restart").json()["items"]
    assert rows[0]["outcome"] == "failed"
    assert console.client.get("/api/v1/ollama").json()["restart_permitted"] == "unknown"


def test_a_host_without_systemd_reports_the_pane_unsupported_and_keeps_rendering(
    tmp_path: Path,
) -> None:
    console = build_console(tmp_path, systemd=FakeSystemdController(supported=False))
    console.login()
    body = console.client.get("/api/v1/ollama").json()
    assert body["state"] == "unsupported"
    assert [finding["outcome"] for finding in body["findings"]] == ["unknown"] * 7
    page = console.client.get("/ollama", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "Unsupported on this host" in page.text


def test_the_pane_and_its_routes_need_a_session(tmp_path: Path) -> None:
    console = build_console(tmp_path, host="10.77.10.84")
    for path in ("/api/v1/ollama", "/api/v1/ollama/ps", "/ollama"):
        response = console.client.get(path, headers={"Host": "jordan-main.local"})
        assert response.status_code in (401, 303), path


@respx.mock
def test_the_polkit_rule_grants_a_unit_and_a_verb_never_a_command(tmp_path: Path) -> None:
    from weightroom.services.ollama import polkit_rule_text

    rule = polkit_rule_text("jordan")
    assert 'action.id == "org.freedesktop.systemd1.manage-units"' in rule
    assert 'action.lookup("verb") == "restart"' in rule
    assert 'subject.user == "jordan"' in rule
    # A sudoers line would grant the binary; this grants a unit and a verb. The word only
    # appears in the file's own explanatory comment, never in what polkit evaluates.
    body = "\n".join(line for line in rule.splitlines() if not line.startswith("//"))
    assert "systemctl" not in body
