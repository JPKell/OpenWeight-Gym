"""The settings write paths, over a real executable that answers ADR-0127's two verbs.

Nothing here mocks a subprocess: :func:`tests.support.fake_application` writes a shell script
that prints one of the four committed schema documents and refuses a marked candidate file, so
the argv, the exit code and the application's own refusal text are all exercised.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

from tests.support import (
    JSON_HEADERS,
    PASSWORD,
    REFUSAL_MARKER,
    Console,
    build_console,
    fake_application,
)
from weightroom.services.processes import FakeSystemdController, UnitState

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXAMPLES = FIXTURES / "config" / "examples"
SCHEMAS = FIXTURES / "schemas"


def _state(running: bool) -> UnitState:  # noqa: FBT001 — a test helper, not a public boundary
    return "active" if running else "inactive"


def _console(
    tmp_path: Path,
    app: str = "loadcoach",
    *,
    config_toml: str = "",
    running: bool = False,
    document: dict[str, Any] | None = None,
    schema_exit: int = 0,
) -> tuple[Console, Path]:
    executable, config_path, _document = fake_application(
        tmp_path, app, config_toml=config_toml, document=document, schema_exit=schema_exit
    )
    console = build_console(
        tmp_path / "console",
        extra_toml=f'[apps.{app}]\nexecutable = "{executable}"\n',
        systemd=FakeSystemdController(states={f"{app}.service": _state(running)}),
    )
    return console, config_path


def _put(console: Console, app: str, changes: dict[str, Any], **extra: Any) -> Any:  # noqa: ANN401
    return console.client.put(
        f"/api/v1/apps/{app}/settings",
        json={"changes": changes, **extra},
        headers=JSON_HEADERS,
    )


def _base_mtime(console: Console, app: str) -> int | None:
    body = console.client.get(f"/api/v1/apps/{app}/settings", headers=JSON_HEADERS).json()
    mtime: int | None = body["base_mtime"]
    return mtime


# --- Reading -------------------------------------------------------------------------------


def test_the_schema_route_answers_the_applications_own_document(tmp_path: Path) -> None:
    console, _config = _console(tmp_path)
    console.login()
    body = console.client.get("/api/v1/apps/loadcoach/settings/schema").json()
    assert body["application"] == "loadcoach"
    assert body["schema_version"] == "1.0"


def test_an_application_that_cannot_describe_itself_answers_the_reason(tmp_path: Path) -> None:
    console, _config = _console(tmp_path, schema_exit=2)
    console.login()
    response = console.client.get("/api/v1/apps/loadcoach/settings/schema")
    assert response.status_code == 409
    assert "config schema --json` failed" in response.json()["reason"]


def test_the_settings_route_names_every_keys_source_and_sets(tmp_path: Path) -> None:
    console, _config = _console(tmp_path, config_toml="[server]\nport = 9001\n")
    console.login()
    body = console.client.get("/api/v1/apps/loadcoach/settings", headers=JSON_HEADERS).json()
    fields = {one["key"]: one for section in body["sections"] for one in section["fields"]}
    assert fields["server.port"]["value"] == 9001
    assert "queue.paused" in body["runtime_changeable"]
    assert "server.host" in body["security_keys"]


def test_the_config_route_carries_the_text_and_the_base_mtime(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="# mine\n[server]\nport = 8766\n")
    console.login()
    body = console.client.get("/api/v1/apps/loadcoach/config", headers=JSON_HEADERS).json()
    assert body["text"] == "# mine\n[server]\nport = 8766\n"
    assert body["base_mtime"] == config.stat().st_mtime_ns


# --- Writing to the file --------------------------------------------------------------------


def test_a_file_key_is_written_and_the_comment_above_it_survives(tmp_path: Path) -> None:
    original = '# the port the operator chose\n[server]\nport = 8766\nhost = "127.0.0.1"\n'
    console, config = _console(tmp_path, config_toml=original)
    console.login()
    console.client.post("/api/v1/reauth", json={"password": PASSWORD}, headers=JSON_HEADERS)
    body = _put(
        console, "loadcoach", {"server.port": 9100}, base_mtime=_base_mtime(console, "loadcoach")
    ).json()
    assert body["outcomes"]["server.port"]["outcome"] == "written"
    text = config.read_text()
    assert "# the port the operator chose" in text
    assert "port = 9100" in text
    assert 'host = "127.0.0.1"' in text
    assert config.with_name("config.toml.bak").read_text() == original


def test_the_previous_file_is_kept_as_bak(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[execution]\nmax_attempts = 3\n")
    console.login()
    body = _put(
        console,
        "loadcoach",
        {"execution.max_attempts": 5},
        base_mtime=_base_mtime(console, "loadcoach"),
    ).json()
    assert body["backup"] == str(config.with_name("config.toml.bak"))
    assert tomllib.loads(config.read_text())["execution"]["max_attempts"] == 5


def test_a_stale_base_mtime_is_refused_whole(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[execution]\nmax_attempts = 3\n")
    console.login()
    response = _put(console, "loadcoach", {"execution.max_attempts": 5}, base_mtime=1)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFIG_CHANGED_ON_DISK"
    assert tomllib.loads(config.read_text())["execution"]["max_attempts"] == 3


def test_the_applications_own_refusal_is_surfaced_verbatim_and_nothing_lands(
    tmp_path: Path,
) -> None:
    # A key the fake application's validator refuses by name, in its own words. Prepared before
    # the console reads anything, since the document is cached for 60 s (api.md §2).
    document = json.loads(
        (
            Path(__file__).resolve().parents[1] / "fixtures" / "schemas" / "loadcoach.json"
        ).read_text()
    )
    document["json_schema"]["$defs"]["ExecutionSettings"]["properties"]["refuse_me"] = {
        "type": "boolean",
        "default": False,
    }
    document["config_only"].append("execution.refuse_me")
    console, config = _console(
        tmp_path, config_toml="[execution]\nmax_attempts = 3\n", document=document
    )
    console.login()
    response = _put(
        console,
        "loadcoach",
        {"execution.refuse_me": True},
        base_mtime=_base_mtime(console, "loadcoach"),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONFIG_VALIDATION_FAILED"
    assert "refuse_me is not a configuration key" in response.json()["error"]["message"]
    assert config.read_text() == "[execution]\nmax_attempts = 3\n"
    assert not config.with_name("config.toml.bak").exists()


def test_an_unknown_key_is_refused_by_name_and_the_rest_still_lands(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[execution]\nmax_attempts = 3\n")
    console.login()
    body = _put(
        console,
        "loadcoach",
        {"execution.max_attempts": 4, "nowhere.at_all": 1},
        base_mtime=_base_mtime(console, "loadcoach"),
    ).json()
    assert body["outcomes"]["nowhere.at_all"]["code"] == "SETTING_UNKNOWN"
    assert body["outcomes"]["execution.max_attempts"]["outcome"] == "written"
    assert tomllib.loads(config.read_text())["execution"]["max_attempts"] == 4


def test_a_value_that_did_not_change_is_reported_unchanged_and_not_written(
    tmp_path: Path,
) -> None:
    console, config = _console(tmp_path, config_toml="[execution]\nmax_attempts = 3\n")
    console.login()
    before = config.stat().st_mtime_ns
    body = _put(
        console,
        "loadcoach",
        {"execution.max_attempts": 3},
        base_mtime=_base_mtime(console, "loadcoach"),
    ).json()
    assert body["outcomes"]["execution.max_attempts"]["outcome"] == "unchanged"
    assert config.stat().st_mtime_ns == before


# --- Security keys and re-authentication ------------------------------------------------------


def test_a_security_key_without_a_fresh_reauth_is_refused(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml='[server]\nhost = "127.0.0.1"\n')
    console.login()
    response = _put(
        console,
        "loadcoach",
        {"server.host": "0.0.0.0"},  # noqa: S104 — the value under test, never a bind here
        base_mtime=_base_mtime(console, "loadcoach"),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REAUTH_REQUIRED"
    assert 'host = "127.0.0.1"' in config.read_text()


def test_a_security_key_lands_inside_the_window_and_the_audit_row_says_security_key(
    tmp_path: Path,
) -> None:
    console, config = _console(tmp_path, config_toml='[server]\nhost = "127.0.0.1"\n')
    console.login()
    console.client.post("/api/v1/reauth", json={"password": PASSWORD}, headers=JSON_HEADERS)
    body = _put(
        console,
        "loadcoach",
        {"server.host": "10.77.10.84"},
        base_mtime=_base_mtime(console, "loadcoach"),
    ).json()
    assert body["outcomes"]["server.host"]["outcome"] == "written"
    row = console.client.get(f"/api/v1/audit/{body['audit_id']}", headers=JSON_HEADERS).json()
    assert row["action"] == "settings.write"
    assert row["security"] is True
    assert 'host = "10.77.10.84"' in config.read_text()


def test_the_window_expires(tmp_path: Path) -> None:
    console, _config = _console(tmp_path, config_toml='[server]\nhost = "127.0.0.1"\n')
    console.login()
    console.client.post("/api/v1/reauth", json={"password": PASSWORD}, headers=JSON_HEADERS)
    console.advance(minutes=6)
    response = _put(
        console,
        "loadcoach",
        {"server.host": "10.77.10.84"},
        base_mtime=_base_mtime(console, "loadcoach"),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REAUTH_REQUIRED"


# --- Runtime keys ----------------------------------------------------------------------------


def test_a_runtime_key_on_a_stopped_application_is_refused_and_offers_the_file(
    tmp_path: Path,
) -> None:
    console, config = _console(tmp_path, running=False)
    console.login()
    body = _put(
        console, "loadcoach", {"queue.paused": True}, base_mtime=_base_mtime(console, "loadcoach")
    ).json()
    outcome = body["outcomes"]["queue.paused"]
    assert outcome["outcome"] == "refused"
    assert outcome["code"] == "APP_STOPPED"
    assert str(config) in outcome["message"]


def test_a_runtime_key_can_be_forced_to_the_file(tmp_path: Path) -> None:
    console, config = _console(tmp_path, running=False)
    console.login()
    body = _put(
        console,
        "loadcoach",
        {"queue.paused": True},
        base_mtime=_base_mtime(console, "loadcoach"),
        to_file=["queue.paused"],
    ).json()
    assert body["outcomes"]["queue.paused"]["outcome"] == "written"
    assert tomllib.loads(config.read_text())["queue"]["paused"] is True


def test_a_runtime_key_on_a_running_application_goes_to_its_api_not_the_file(
    tmp_path: Path, respx_mock: Any
) -> None:
    import httpx

    console, config = _console(tmp_path, running=True)
    console.login()
    respx_mock.get("http://127.0.0.1:8766/api/v1/version").mock(
        return_value=httpx.Response(200, json={"application": "loadcoach", "version": "1.3.1"})
    )
    respx_mock.get("http://127.0.0.1:8766/api/v1/settings").mock(
        return_value=httpx.Response(200, json={"settings": {"queue.paused": False}})
    )
    route = respx_mock.put("http://127.0.0.1:8766/api/v1/settings").mock(
        return_value=httpx.Response(200, json={"settings": {"queue.paused": True}})
    )
    body = _put(
        console, "loadcoach", {"queue.paused": True}, base_mtime=_base_mtime(console, "loadcoach")
    ).json()
    assert body["outcomes"]["queue.paused"]["outcome"] == "applied"
    assert route.called
    assert json.loads(route.calls.last.request.content) == {"queue.paused": True}
    assert config.read_text() == ""  # the file is never touched for a runtime key (rule 4)


def test_the_applications_refusal_of_a_runtime_key_is_carried_through(
    tmp_path: Path, respx_mock: Any
) -> None:
    import httpx

    console, _config = _console(tmp_path, running=True)
    console.login()
    respx_mock.get("http://127.0.0.1:8766/api/v1/version").mock(
        return_value=httpx.Response(200, json={"application": "loadcoach", "version": "1.3.1"})
    )
    respx_mock.get("http://127.0.0.1:8766/api/v1/settings").mock(
        return_value=httpx.Response(200, json={"settings": {}})
    )
    respx_mock.put("http://127.0.0.1:8766/api/v1/settings").mock(
        return_value=httpx.Response(
            400,
            json={"error": {"code": "VALIDATION_ERROR", "message": "queue.paused must be a bool"}},
        )
    )
    body = _put(
        console, "loadcoach", {"queue.paused": True}, base_mtime=_base_mtime(console, "loadcoach")
    ).json()
    assert body["outcomes"]["queue.paused"]["outcome"] == "refused"
    assert "queue.paused must be a bool" in body["outcomes"]["queue.paused"]["message"]


# --- Every application's EXAMPLE_CONFIG_TOML, one key at a time -------------------------------


@pytest.mark.parametrize(
    ("app", "key", "value"),
    [
        ("freeweight", "benchmarks.long_context_max_tokens", 16000),
        ("loadcoach", "execution.max_attempts", 7),
        ("ideapress", "execution.max_concurrent_stages", 2),
        ("promptcadence", "execution.max_steps", 11),
    ],
)
def test_each_applications_example_config_round_trips_one_key_byte_identically(
    tmp_path: Path, app: str, key: str, value: Any
) -> None:
    """Development plan Phase 4: comments, order and every untouched line survive."""
    from weightroom.services.config_files import apply_changes

    original = (EXAMPLES / f"{app}.toml").read_text(encoding="utf-8")
    written = apply_changes(original, {key: value})
    section, leaf = key.split(".")
    assert tomllib.loads(written)[section][leaf] == value
    before = [line for line in original.splitlines() if not line.strip().startswith(f"{leaf} ")]
    after = [line for line in written.splitlines() if not line.strip().startswith(f"{leaf} ")]
    assert before == after


@pytest.mark.parametrize("app", ["freeweight", "loadcoach", "ideapress", "promptcadence"])
def test_a_key_the_example_config_never_mentions_is_appended_without_disturbing_it(
    tmp_path: Path, app: str
) -> None:
    from weightroom.services.config_files import apply_changes

    original = (EXAMPLES / f"{app}.toml").read_text(encoding="utf-8")
    written = apply_changes(original, {"logging.level": "DEBUG"})
    assert tomllib.loads(written)["logging"]["level"] == "DEBUG"
    assert written.startswith(original.split("\n[logging]")[0])


# --- The pages --------------------------------------------------------------------------------


def test_the_settings_page_renders_every_section_and_the_raw_editor(tmp_path: Path) -> None:
    console, _config = _console(tmp_path)
    console.login()
    page = console.client.get("/apps/loadcoach/settings", headers={"Accept": "text/html"}).text
    assert 'name="field:server.port"' in page
    assert 'name="field:queue.paused"' in page
    assert "config schema --json" in page
    assert 'name="text"' not in page  # the raw editor is its own page (secrets)
    editor = console.client.get(
        "/apps/loadcoach/settings/raw", headers={"Accept": "text/html"}
    ).text
    assert 'name="text"' in editor


def test_a_secret_is_never_rendered_on_the_page(tmp_path: Path) -> None:
    console, _config = _console(
        tmp_path, app="freeweight", config_toml='[auth]\ntokens = ["hunter2"]\n'
    )
    console.login()
    page = console.client.get("/apps/freeweight/settings", headers={"Accept": "text/html"}).text
    assert "hunter2" not in page
    assert "********" in page
    # The raw editor is the file, secrets included — which is why it is its own page.
    editor = console.client.get(
        "/apps/freeweight/settings/raw", headers={"Accept": "text/html"}
    ).text
    assert "hunter2" in editor


def test_the_page_saves_a_key_and_says_what_it_did(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[execution]\nmax_attempts = 3\n")
    console.login()
    base = _base_mtime(console, "loadcoach")
    response = console.post_form(
        "/apps/loadcoach/settings",
        {"field:execution.max_attempts": "9", "base_mtime": str(base)},
    )
    assert response.status_code == 200
    assert "1 written to the file" in response.text
    assert tomllib.loads(config.read_text())["execution"]["max_attempts"] == 9


def test_the_page_takes_the_password_and_writes_a_security_key_in_one_post(
    tmp_path: Path,
) -> None:
    """Plan Phase 4 criterion 2, without the restart half (a fake host has no process)."""
    console, config = _console(tmp_path, config_toml='[server]\nhost = "127.0.0.1"\n')
    console.login()
    base = _base_mtime(console, "loadcoach")
    response = console.post_form(
        "/apps/loadcoach/settings",
        {
            "field:server.host": "10.77.10.84",
            "base_mtime": str(base),
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200
    assert 'host = "10.77.10.84"' in config.read_text()


def test_a_wrong_password_writes_nothing(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml='[server]\nhost = "127.0.0.1"\n')
    console.login()
    base = _base_mtime(console, "loadcoach")
    response = console.post_form(
        "/apps/loadcoach/settings",
        {"field:server.host": "10.77.10.84", "base_mtime": str(base), "password": "wrong"},
    )
    assert "not the operator" in response.text  # Jinja escapes the apostrophe
    assert 'host = "127.0.0.1"' in config.read_text()


def test_the_raw_editor_refuses_broken_toml_before_launching_anything(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[server]\nport = 8766\n")
    console.login()
    base = _base_mtime(console, "loadcoach")
    response = console.post_form(
        "/apps/loadcoach/settings/raw",
        {"text": "[server\n", "base_mtime": str(base), "password": PASSWORD},
    )
    assert "Not valid TOML" in response.text
    assert config.read_text() == "[server]\nport = 8766\n"


def test_the_raw_editor_writes_the_whole_file_under_the_same_rules(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[server]\nport = 8766\n")
    console.login()
    base = _base_mtime(console, "loadcoach")
    response = console.post_form(
        "/apps/loadcoach/settings/raw",
        {
            "text": "# rewritten\n[server]\nport = 8767\n",
            "base_mtime": str(base),
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200
    assert config.read_text() == "# rewritten\n[server]\nport = 8767\n"


def test_the_raw_editor_is_refused_by_the_applications_own_validation(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[server]\nport = 8766\n")
    console.login()
    base = _base_mtime(console, "loadcoach")
    response = console.post_form(
        "/apps/loadcoach/settings/raw",
        {"text": f"{REFUSAL_MARKER}\n", "base_mtime": str(base), "password": PASSWORD},
    )
    assert "refuse_me is not a configuration key" in response.text
    assert config.read_text() == "[server]\nport = 8766\n"


def test_validate_answers_the_applications_verdict_and_writes_nothing(tmp_path: Path) -> None:
    console, config = _console(tmp_path, config_toml="[server]\nport = 8766\n")
    console.login()
    good = console.client.post(
        "/api/v1/apps/loadcoach/settings/validate",
        json={"text": "[server]\nport = 1\n"},
        headers=JSON_HEADERS,
    ).json()
    assert good["valid"] is True
    bad = console.client.post(
        "/api/v1/apps/loadcoach/settings/validate",
        json={"text": f"{REFUSAL_MARKER}\n"},
        headers=JSON_HEADERS,
    ).json()
    assert bad["valid"] is False
    assert "refuse_me" in bad["message"]
    assert config.read_text() == "[server]\nport = 8766\n"


# --- WeightRoomGym's own page -----------------------------------------------------------------


def test_the_console_generates_its_own_settings_page_from_its_own_verb(tmp_path: Path) -> None:
    console = build_console(tmp_path)
    console.login()
    page = console.client.get("/settings", headers={"Accept": "text/html"}).text
    assert "wr-gym config schema --json" in page
    assert 'name="field:telemetry.interval_ms"' in page
    assert 'name="field:server.host"' in page


def test_the_consoles_own_runtime_key_is_applied_live(tmp_path: Path) -> None:
    console = build_console(tmp_path)
    console.login()
    response = console.post_form(
        "/settings", {"field:telemetry.interval_ms": "2500", "base_mtime": ""}
    )
    assert response.status_code == 200
    body = console.client.get("/api/v1/settings", headers=JSON_HEADERS).json()
    assert body["settings"]["telemetry.interval_ms"] == 2500


def test_the_consoles_own_security_key_needs_the_password_too(tmp_path: Path) -> None:
    console = build_console(tmp_path)
    console.login()
    response = console.client.put(
        "/api/v1/apps/weightroom/settings",
        json={"changes": {"server.port": 8790}},
        headers=JSON_HEADERS,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REAUTH_REQUIRED"
