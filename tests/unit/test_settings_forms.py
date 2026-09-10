"""ADR-0127 rule 3: the form is generated from the document and hardcodes no key."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.support import build_console
from weightroom.config import APPLICATIONS, Settings, load_settings
from weightroom.services.apps import AppView
from weightroom.services.processes import CommandResult
from weightroom.services.settings_forms import (
    REDACTED,
    SchemaCache,
    is_secret_key,
    read_schema_document,
    settings_form,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "schemas"
GOLDENS = FIXTURES / "goldens"


def _document(app: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((FIXTURES / f"{app}.json").read_text(encoding="utf-8"))
    return loaded


def _settings(tmp_path: Path) -> Settings:
    file = tmp_path / "console.toml"
    file.write_text(f'[storage]\ndatabase_url = "sqlite:///{tmp_path}/w.sqlite3"\n')
    return load_settings(config_path=file).settings


def _view(app: str, *, running: bool = False, uptime: float | None = None) -> AppView:
    return AppView(
        name=app,
        installed=True,
        executable=f"/opt/{app}",
        unit=f"{app}.service",
        unit_state="active" if running else "inactive",
        uptime_seconds=uptime,
        restarts=None,
        base_url="http://127.0.0.1:8765",
        version="1.0.0" if running else None,
    )


def _form(app: str, tmp_path: Path, *, toml: str = "", **kwargs: Any) -> Any:  # noqa: ANN401
    document = _document(app)
    config = tmp_path / f"{app}.toml"
    config.write_text(toml)
    document["config_path"] = str(config)
    return settings_form(_settings(tmp_path), app, document=document, document_error=None, **kwargs)


# --- The goldens -------------------------------------------------------------------------


def _golden_text(form: Any) -> str:  # noqa: ANN401
    lines = []
    for section in form.sections:
        lines.append(f"[{section.name}]")
        for one in section.fields:
            marks = "".join(
                (
                    "L" if one.runtime else "-",
                    "S" if one.security else "-",
                    "X" if one.secret else "-",
                )
            )
            bounds = f" {one.bounds_text}" if one.bounds_text else ""
            choices = f" {{{','.join(one.choices)}}}" if one.choices else ""
            lines.append(f"  {marks} {one.key}: {one.kind}{bounds}{choices}")
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("app", APPLICATIONS)
def test_the_form_generated_from_each_document_matches_its_golden(app: str, tmp_path: Path) -> None:
    assert _golden_text(_form(app, tmp_path)) == (GOLDENS / f"{app}.txt").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("app", APPLICATIONS)
def test_every_runtime_and_security_key_the_document_names_is_a_field(
    app: str, tmp_path: Path
) -> None:
    form = _form(app, tmp_path)
    keys = {one.key for one in form.fields()}
    document = _document(app)
    stated_runtime = {entry["key"] for entry in document["runtime_changeable"]}
    stated_security = set(document["security_keys"])
    named = stated_runtime | stated_security | set(document["config_only"])
    # Every key the application names is on the page — the keyed-table leaves included
    # (LoadCoach's database-only `queue.paused`, IdeaPress's `models.stages.<stage>`,
    # PromptCadence's `[tiers.<name>]`), which no walk of `json_schema` alone would find.
    assert named <= keys, sorted(named - keys)
    for key in named:
        one = form.field_for(key)
        assert one is not None
        assert one.runtime == (key in stated_runtime)
        assert one.security == (key in stated_security)


# --- Rule 3: nothing is hardcoded ---------------------------------------------------------


def test_a_field_added_to_a_fixture_document_appears_with_no_code_change(tmp_path: Path) -> None:
    """Development plan Phase 4 criterion 3, and spec §20 #5."""
    document = _document("loadcoach")
    # Exactly what an application that grows a key emits: the field in its own `json_schema`,
    # and the key in whichever of the three sets it belongs to (here, config-only).
    document["json_schema"]["$defs"]["ServerSettings"]["properties"]["invented_number"] = {
        "type": "integer",
        "default": 7,
        "minimum": 1,
        "maximum": 9,
        "description": "A key no version of this console has heard of.",
    }
    document["config_only"].append("server.invented_number")
    config = tmp_path / "loadcoach.toml"
    config.write_text("")
    document["config_path"] = str(config)
    form = settings_form(_settings(tmp_path), "loadcoach", document=document, document_error=None)
    invented = form.field_for("server.invented_number")
    assert invented is not None
    assert (invented.kind, invented.default, invented.bounds_text) == ("integer", 7, "1 … 9")
    assert invented.description == "A key no version of this console has heard of."


def test_a_key_the_document_does_not_describe_is_listed_raw_not_dropped(tmp_path: Path) -> None:
    form = _form(
        "ideapress", tmp_path, toml="[something]\nnobody_knows = 1\n[server]\nport = 8767\n"
    )
    assert "something.nobody_knows" in form.undescribed
    assert "server.port" not in form.undescribed


# --- Values, sources, shadowing -----------------------------------------------------------


def test_the_file_value_wins_over_the_default(tmp_path: Path) -> None:
    form = _form("promptcadence", tmp_path, toml="[server]\nport = 9999\n")
    port = form.field_for("server.port")
    assert port is not None
    assert (port.value, port.in_file, port.live) == (9999, True, False)


def test_a_running_applications_runtime_value_wins_over_the_file(tmp_path: Path) -> None:
    form = _form(
        "promptcadence",
        tmp_path,
        toml="[storage]\ncontent_retention_hours = 12\n",
        live={"storage.content_retention_hours": 48},
        view=_view("promptcadence", running=True),
    )
    live = form.field_for("storage.content_retention_hours")
    assert live is not None
    assert (live.value, live.live, live.runtime) == (48, True, True)


def test_an_environment_pinned_key_is_marked_shadowed(tmp_path: Path) -> None:
    document = _document("freeweight")
    document["sources"]["server.port"] = "env FREEWEIGHT_SERVER__PORT"
    config = tmp_path / "freeweight.toml"
    config.write_text("[server]\nport = 8765\n")
    document["config_path"] = str(config)
    form = settings_form(_settings(tmp_path), "freeweight", document=document, document_error=None)
    port = form.field_for("server.port")
    assert port is not None
    assert port.shadowed
    assert form.field_for("server.host") is not None
    assert not form.field_for("server.host").shadowed  # type: ignore[union-attr]


def test_a_database_row_the_environment_shadows_is_marked_shadowed(tmp_path: Path) -> None:
    document = _document("loadcoach")
    key = document["runtime_changeable"][0]["key"]
    document["sources"][key] = "env LOADCOACH_X; database row 5 shadowed"
    config = tmp_path / "loadcoach.toml"
    config.write_text("")
    document["config_path"] = str(config)
    form = settings_form(_settings(tmp_path), "loadcoach", document=document, document_error=None)
    assert form.field_for(key).shadowed  # type: ignore[union-attr]


# --- Secrets -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "secret"),
    [
        ("auth.tokens", True),
        ("auth.token", True),
        ("server.api_key", True),
        ("chat.password", True),
        ("apps.freeweight.api_key_file", False),
        ("evidence.freeweight_api_key_env", False),
        ("storage.artifact_dir", False),
        ("server.allowed_hosts", False),
    ],
)
def test_only_a_field_that_holds_a_credential_is_secret(key: str, secret: bool) -> None:
    assert is_secret_key(key) is secret


def test_a_configured_secret_is_never_rendered(tmp_path: Path) -> None:
    form = _form("freeweight", tmp_path, toml='[auth]\ntokens = ["hunter2"]\n')
    tokens = form.field_for("auth.tokens")
    assert tokens is not None
    assert tokens.value == REDACTED
    assert "hunter2" not in json.dumps(form.as_json())


# --- Pending restart --------------------------------------------------------------------


def test_a_file_changed_after_the_unit_started_is_pending_restart(tmp_path: Path) -> None:
    config = tmp_path / "loadcoach.toml"
    config.write_text("")
    document = _document("loadcoach")
    document["config_path"] = str(config)
    changed_at = config.stat().st_mtime
    settings = _settings(tmp_path)
    running_since_before = settings_form(
        settings,
        "loadcoach",
        document=document,
        document_error=None,
        view=_view("loadcoach", running=True, uptime=600.0),
        now=changed_at + 60.0,
    )
    assert running_since_before.pending_restart
    running_since_after = settings_form(
        settings,
        "loadcoach",
        document=document,
        document_error=None,
        view=_view("loadcoach", running=True, uptime=10.0),
        now=changed_at + 60.0,
    )
    assert not running_since_after.pending_restart


def test_a_stopped_application_is_not_pending_restart(tmp_path: Path) -> None:
    form = _form("loadcoach", tmp_path, view=_view("loadcoach"))
    assert not form.pending_restart


# --- Reading the document ------------------------------------------------------------------


def _runner(result: CommandResult) -> Any:  # noqa: ANN401
    def run(argv: Any, env: Any, timeout: float) -> CommandResult:  # noqa: ANN401, ARG001
        return result

    return run


def test_a_document_is_read_from_the_applications_own_verb(tmp_path: Path) -> None:
    payload = json.dumps({"json_schema": {"properties": {}}, "application": "loadcoach"})
    document, error = read_schema_document(
        _settings(tmp_path),
        "loadcoach",
        runner=_runner(CommandResult(("x",), 0, payload, "")),
        which=lambda _name: "/opt/loadcoach",
    )
    assert error is None
    assert document is not None
    assert document["application"] == "loadcoach"


@pytest.mark.parametrize(
    ("result", "which", "fragment"),
    [
        (CommandResult(("x",), 0, "", ""), None, "is not installed"),
        (CommandResult(("x",), 2, "", "no such command"), "/opt/x", "failed"),
        (CommandResult(("x",), 0, "not json", ""), "/opt/x", "did not print JSON"),
        (CommandResult(("x",), 0, "{}", ""), "/opt/x", "predates ADR-0127"),
    ],
)
def test_an_application_that_cannot_answer_degrades_with_a_reason(
    tmp_path: Path, result: CommandResult, which: str | None, fragment: str
) -> None:
    document, error = read_schema_document(
        _settings(tmp_path),
        "loadcoach",
        runner=_runner(result),
        which=lambda _name: which,
    )
    assert document is None
    assert error is not None
    assert fragment in error


def test_a_form_over_no_document_is_a_page_not_an_exception(tmp_path: Path) -> None:
    config = tmp_path / "loadcoach.toml"
    config.write_text("[server]\nport = 1\n")
    form = settings_form(
        _settings(tmp_path),
        "loadcoach",
        document=None,
        document_error="loadcoach is not installed",
        config_path=config,
    )
    assert form.sections == ()
    assert form.document_error == "loadcoach is not installed"
    assert form.raw_toml == "[server]\nport = 1\n"
    assert form.undescribed == ("server.port",)


def test_broken_toml_is_a_problem_on_the_page_not_a_crash(tmp_path: Path) -> None:
    form = _form("ideapress", tmp_path, toml="[server\n")
    assert any("not valid TOML" in problem for problem in form.problems)


# --- The cache -----------------------------------------------------------------------------


def test_the_document_is_held_for_the_ttl_and_re_read_after_it() -> None:
    cache = SchemaCache(ttl_seconds=60.0)
    calls = []

    def read() -> tuple[dict[str, Any] | None, str | None]:
        calls.append(1)
        return {"json_schema": {}}, None

    cache.get("loadcoach", now=0.0, read=read)
    cache.get("loadcoach", now=30.0, read=read)
    assert len(calls) == 1
    cache.get("loadcoach", now=61.0, read=read)
    assert len(calls) == 2
    cache.get("loadcoach", now=61.0, read=read, refresh=True)
    assert len(calls) == 3
    cache.forget("loadcoach")
    cache.get("loadcoach", now=61.0, read=read)
    assert len(calls) == 4


# --- WeightRoomGym's own document ------------------------------------------------------------


def test_weightroomgym_generates_its_own_page_from_its_own_verb(tmp_path: Path) -> None:
    console = build_console(tmp_path / "console")
    config = tmp_path / "console" / "console.toml"  # the file build_console wrote
    document, error = read_schema_document(console.settings, "weightroom", config_path=config)
    assert error is None
    assert document is not None
    form = settings_form(
        console.settings, "weightroom", document=document, document_error=None, config_path=config
    )
    assert {section.name for section in form.sections} >= {"server", "tls", "auth", "storage"}
    assert "telemetry.interval_ms" in form.runtime_keys
    assert "server.host" in form.security_keys
