"""The systemd boundary against a fake ``systemctl`` on ``PATH`` (ADR-0125 rule 3).

The fake is a real executable that records the argv and the environment it was given and prints
canned ``systemctl show`` output. That is the half a Python fake cannot prove: that the argv is
a list and never a shell line, that ``--user`` and ``--no-ask-password`` are there, and that the
child's environment is the allowlist and nothing else (gold standard G12).
"""

from __future__ import annotations

import json
import os
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from weightroom.config import Settings, load_settings
from weightroom.services.processes import (
    ENV_ALLOWLIST,
    FakeSystemdController,
    Scope,
    SubprocessSystemdController,
    UnitActionFailed,
    UnitStatus,
    UnitUnsupported,
    act_and_settle,
    executable_for,
    plan_units,
    sync_units,
)

FAKE = """#!{python}
import json, os, sys
record = {{"argv": sys.argv, "env": dict(os.environ)}}
with open({log!r}, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(record) + "\\n")
verb = sys.argv[1] if len(sys.argv) > 1 else ""
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if args and args[0] == "show":
    for unit in args[1:]:
        state = {states!r}.get(unit, "absent")
        print("Id=" + unit)
        print("LoadState=" + ("not-found" if state == "absent" else "loaded"))
        print("ActiveState=" + ("inactive" if state == "absent" else state))
        print("SubState=" + ("running" if state == "active" else "dead"))
        print("Result=success")
        print("MainPID=" + ("4242" if state == "active" else "0"))
        print("NRestarts=0")
        print("ActiveEnterTimestampMonotonic=" + ("1000000" if state == "active" else "0"))
        print()
    sys.exit(0)
if {fail!r}:
    sys.stderr.write({fail!r})
    sys.exit(1)
sys.exit(0)
"""


@pytest.fixture
def host(tmp_path: Path) -> Path:
    """A directory that will hold the fake ``systemctl``; the tests fill it in."""
    (tmp_path / "bin").mkdir()
    return tmp_path


def _install_fake(
    host: Path, *, name: str = "systemctl", states: dict[str, str] | None = None, fail: str = ""
) -> Path:
    log = host / f"{name}.log"
    script = host / "bin" / name
    script.write_text(
        FAKE.format(python=sys.executable, log=str(log), states=states or {}, fail=fail),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return log


def _calls(log: Path) -> list[dict[str, Any]]:
    """Every invocation the fake recorded: its argv and the environment it was handed."""
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def _controller(host: Path) -> SubprocessSystemdController:
    binaries = {
        path.name: str(path) for path in (host / "bin").iterdir() if os.access(path, os.X_OK)
    }
    return SubprocessSystemdController(which=binaries.get)


def _settings(tmp_path: Path, host: Path) -> Settings:
    for app in ("freeweight", "loadcoach", "ideapress", "promptcadence"):
        binary = host / "bin" / app
        binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        binary.chmod(0o755)
    file = tmp_path / "console.toml"
    file.write_text(
        "\n".join(
            f'[apps.{app}]\nexecutable = "{host / "bin" / app}"'
            for app in ("freeweight", "loadcoach", "ideapress", "promptcadence")
        )
        + f'\n[storage]\ndatabase_url = "sqlite:///{tmp_path}/weightroom.sqlite3"\n',
        encoding="utf-8",
    )
    return load_settings(config_path=file).settings


def test_each_verb_is_an_explicit_argv_with_user_and_no_ask_password(host: Path) -> None:
    log = _install_fake(host)
    controller = _controller(host)
    for verb in ("start", "stop", "restart"):
        assert controller.act("loadcoach.service", verb).ok
    argvs = [call["argv"] for call in _calls(log)]
    assert [argv[1:] for argv in argvs] == [
        ["--user", "--no-ask-password", verb, "loadcoach.service"]
        for verb in ("start", "stop", "restart")
    ]
    for argv in argvs:
        assert all(isinstance(part, str) for part in argv)
        assert not any(";" in part or "&&" in part or "|" in part for part in argv)


# --- a verb that outlives the console's limit (row WPF4) ------------------------------------------

UNIT = "loadcoach.service"


def test_a_call_that_answers_in_time_is_not_re_read() -> None:
    """The common path costs nothing extra: one ``act`` and no ``show``."""
    fake = FakeSystemdController(states={UNIT: "active"})
    report = act_and_settle(fake, UNIT, "stop")
    assert report.outcome == "ok"
    assert report.note is None
    assert report.settled is None
    assert [call for call in fake.calls if call[0] == "show"] == []


def test_a_verb_that_outlived_the_limit_is_judged_by_the_state_the_unit_reached() -> None:
    """Row WP6's restart: ``systemctl`` was killed at 30 s and the unit came back anyway."""
    fake = FakeSystemdController(states={UNIT: "inactive"}, slow={(UNIT, "restart"): "active"})
    report = act_and_settle(fake, UNIT, "restart")
    assert report.result.timed_out
    assert report.reached
    assert report.outcome == "ok"
    assert report.note is not None
    assert "did not answer within 30s" in report.note
    assert f"{UNIT} is active" in report.note


def test_a_unit_still_deactivating_after_the_limit_is_pending_not_failed() -> None:
    """systemd is still working on it, so the trail says so rather than inventing a failure."""
    fake = FakeSystemdController(states={UNIT: "active"}, slow={(UNIT, "stop"): "deactivating"})
    report = act_and_settle(fake, UNIT, "stop")
    assert report.outcome == "pending"
    assert report.reached is False
    assert report.note is not None
    assert "is deactivating" in report.note


def test_a_unit_that_failed_after_the_limit_is_a_failure_in_systemds_own_words() -> None:
    """The one case that is a failure: the unit's own ``Result`` says why."""
    fake = FakeSystemdController(states={UNIT: "active"}, slow={(UNIT, "stop"): "failed"})
    report = act_and_settle(fake, UNIT, "stop")
    assert report.outcome == "failed"
    assert report.note is not None
    assert "is failed (timeout)" in report.note


def test_a_verb_with_no_state_to_reach_keeps_its_timeout_as_a_failure() -> None:
    """``enable`` writes a symlink; there is no state a re-read could judge it by."""
    fake = FakeSystemdController(states={UNIT: "active"}, slow={(UNIT, "enable"): "active"})
    report = act_and_settle(fake, UNIT, "enable")
    assert report.outcome == "failed"
    assert report.settled is None
    assert [call for call in fake.calls if call[0] == "show"] == []


def test_a_re_read_that_fails_leaves_the_timeout_as_the_whole_answer() -> None:
    """Two failures are not more information than one, so the bare result stands."""

    class Mute(FakeSystemdController):
        def show(self, units: Sequence[str], *, scope: Scope = "user") -> dict[str, UnitStatus]:
            raise UnitActionFailed("systemctl show failed: bus went away")

    fake = Mute(states={UNIT: "active"}, slow={(UNIT, "stop"): "inactive"})
    report = act_and_settle(fake, UNIT, "stop")
    assert report.outcome == "failed"
    assert report.note == "systemctl did not answer within 30s"


def test_a_system_scope_call_omits_user_but_keeps_no_ask_password(host: Path) -> None:
    log = _install_fake(host)
    _controller(host).act("ollama.service", "restart", scope="system")
    assert _calls(log)[0]["argv"][1:] == ["--no-ask-password", "restart", "ollama.service"]


def test_an_unknown_verb_is_a_caller_bug_not_a_subprocess(host: Path) -> None:
    log = _install_fake(host)
    with pytest.raises(ValueError, match="is not a unit verb"):
        _controller(host).act("loadcoach.service", "isolate")
    assert _calls(log) == []


def test_the_child_environment_is_the_allowlist_and_carries_no_secret(
    host: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOADCOACH_API_KEY", "sk-must-not-leak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "also-must-not-leak")
    log = _install_fake(host)
    _controller(host).act("loadcoach.service", "start")
    env = _calls(log)[0]["env"]
    assert set(env) <= {*ENV_ALLOWLIST, "LC_ALL", "PYTHONUNBUFFERED"}
    assert "must-not-leak" not in json.dumps(env)
    assert env["LC_ALL"] == "C"
    assert env["PYTHONUNBUFFERED"] == "1"  # W9 §5 item 5h: a child's lines arrive as written


def test_show_asks_for_every_property_in_one_call_and_parses_the_records(host: Path) -> None:
    log = _install_fake(host, states={"loadcoach.service": "active"})
    states = _controller(host).show(["loadcoach.service", "freeweight.service"])
    argv = _calls(log)[0]["argv"]
    assert argv.count("show") == 1
    assert "--property=ActiveEnterTimestampMonotonic" in argv
    assert states["loadcoach.service"].state == "active"
    assert states["loadcoach.service"].main_pid == 4242
    assert states["loadcoach.service"].uptime_seconds is not None
    assert states["freeweight.service"].state == "absent"
    assert states["freeweight.service"].uptime_seconds is None


def test_a_unit_that_is_not_active_reports_no_uptime_rather_than_zero(host: Path) -> None:
    _install_fake(host, states={"loadcoach.service": "inactive"})
    status = _controller(host).show(["loadcoach.service"])["loadcoach.service"]
    assert status.state == "inactive"
    assert status.uptime_seconds is None


def test_systemds_own_failure_text_reaches_the_caller(host: Path) -> None:
    _install_fake(host, fail="Failed to start loadcoach.service: Unit not found.")
    result = _controller(host).act("loadcoach.service", "start")
    assert not result.ok
    assert "Unit not found" in result.failure_text


def test_without_systemctl_the_host_is_unsupported_by_name(host: Path) -> None:
    controller = SubprocessSystemdController(which=lambda _name: None)
    assert not controller.available()
    with pytest.raises(UnitUnsupported) as caught:
        controller.show(["loadcoach.service"])
    assert caught.value.code == "UNIT_UNSUPPORTED"
    assert "no systemctl" in caught.value.message


def test_linger_is_read_from_loginctl_and_enabled_through_it(host: Path) -> None:
    systemctl_log = _install_fake(host)
    loginctl = host / "bin" / "loginctl"
    loginctl.write_text(
        f"#!{sys.executable}\nimport sys\nprint('no' if 'show-user' in sys.argv else '')\n",
        encoding="utf-8",
    )
    loginctl.chmod(0o755)
    controller = _controller(host)
    assert controller.linger_enabled("op") is False
    assert controller.enable_linger("op").ok
    assert _calls(systemctl_log) == []


def test_sync_writes_five_units_reloads_once_and_is_idempotent(tmp_path: Path, host: Path) -> None:
    log = _install_fake(host)
    settings = _settings(tmp_path, host)
    units = tmp_path / "systemd"
    first = sync_units(
        settings, controller=_controller(host), which=lambda _n: None, directory=units
    )
    # weightroom is not installed in this fixture: four units, and `weightroom` says so by name.
    assert sorted(first.written) == [
        "freeweight.service",
        "ideapress.service",
        "loadcoach.service",
        "promptcadence.service",
    ]
    assert first.reloaded
    assert {plan.app: plan.outcome for plan in first.plans}["weightroom"] == "not_installed"
    assert not (units / "weightroom.service").exists()

    reloads = [call for call in _calls(log) if "daemon-reload" in call["argv"]]
    assert len(reloads) == 1

    second = sync_units(
        settings, controller=_controller(host), which=lambda _n: None, directory=units
    )
    assert second.written == ()
    assert not second.reloaded
    assert all(plan.outcome != "written" for plan in second.plans if plan.rendered)


def test_sync_overwrites_a_hand_edit_and_reports_the_diff(tmp_path: Path, host: Path) -> None:
    _install_fake(host)
    settings = _settings(tmp_path, host)
    units = tmp_path / "systemd"
    sync_units(settings, controller=_controller(host), which=lambda _n: None, directory=units)
    edited = units / "loadcoach.service"
    edited.write_text(
        edited.read_text(encoding="utf-8").replace("MemoryMax=24G", "MemoryMax=99G"),
        encoding="utf-8",
    )
    plans = {
        plan.app: plan for plan in plan_units(settings, which=lambda _n: None, directory=units)
    }
    assert plans["loadcoach"].outcome == "written"
    assert "-MemoryMax=99G" in plans["loadcoach"].diff
    report = sync_units(
        settings, controller=_controller(host), which=lambda _n: None, directory=units
    )
    assert report.written == ("loadcoach.service",)
    assert "MemoryMax=24G" in edited.read_text(encoding="utf-8")


def test_a_dry_run_writes_nothing_and_reloads_nothing(tmp_path: Path, host: Path) -> None:
    log = _install_fake(host)
    settings = _settings(tmp_path, host)
    units = tmp_path / "systemd"
    report = sync_units(
        settings,
        controller=_controller(host),
        which=lambda _n: None,
        directory=units,
        dry_run=True,
    )
    assert report.written
    assert not report.reloaded
    assert not units.exists()
    assert not [call for call in _calls(log) if "daemon-reload" in call["argv"]]


def test_sync_on_a_host_without_systemd_is_unsupported_by_name(tmp_path: Path, host: Path) -> None:
    settings = _settings(tmp_path, host)
    controller = SubprocessSystemdController(which=lambda _name: None)
    with pytest.raises(UnitUnsupported) as caught:
        sync_units(settings, controller=controller, directory=tmp_path / "systemd")
    assert caught.value.code == "UNIT_UNSUPPORTED"


def test_a_reload_that_fails_leaves_the_files_written_and_says_so(
    tmp_path: Path, host: Path
) -> None:
    _install_fake(host, fail="Failed to reload daemon: Connection reset by peer")
    settings = _settings(tmp_path, host)
    units = tmp_path / "systemd"
    with pytest.raises(UnitActionFailed) as caught:
        sync_units(settings, controller=_controller(host), which=lambda _n: None, directory=units)
    assert "would not reload" in caught.value.message
    assert (units / "loadcoach.service").is_file()


def test_an_application_that_is_not_installed_has_no_unit(tmp_path: Path, host: Path) -> None:
    settings = _settings(tmp_path, host)
    (host / "bin" / "ideapress").unlink()
    assert executable_for(settings, "ideapress", which=lambda _n: None) is None
    plans = {
        plan.app: plan for plan in plan_units(settings, which=lambda _n: None, directory=tmp_path)
    }
    assert plans["ideapress"].outcome == "not_installed"
    assert plans["ideapress"].rendered is None


def test_which_is_the_fallback_when_no_executable_is_configured(tmp_path: Path, host: Path) -> None:
    file = tmp_path / "bare.toml"
    file.write_text(
        f'[storage]\ndatabase_url = "sqlite:///{tmp_path}/x.sqlite3"\n', encoding="utf-8"
    )
    settings = load_settings(config_path=file).settings
    found = executable_for(settings, "loadcoach", which=lambda name: f"/opt/{name}")
    assert found == "/opt/loadcoach"
