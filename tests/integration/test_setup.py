"""``wr-gym setup``'s work, driven without a terminal: TLS, the account, the bind, the tokens."""

from __future__ import annotations

import stat
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from weightroom.config import load_settings, secrets_dir
from weightroom.services.auth import operator_count
from weightroom.services.database import Database, ensure_ready
from weightroom.services.processes import (
    CommandResult,
    FakeSystemdController,
    UnitActionFailed,
)
from weightroom.services.setup import (
    SetupAnswers,
    SetupReport,
    enable_linger_step,
    installed_executable,
    issue_token_via_cli,
    run_setup,
    write_config_changes,
)
from weightroom.services.tls import HostIdentity, TlsPaths

IDENTITY = HostIdentity("jordan-main", ("10.77.10.84", "fd00::5"))
NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


@pytest.fixture
def database(tmp_path: Path) -> Database:
    handle = Database.from_url(f"sqlite:///{tmp_path}/setup.sqlite3")
    ensure_ready(handle, auto_migrate=True)
    return handle


def _fake_app(tmp_path: Path, name: str, *, printed: str = "", exit_code: int = 0) -> str:
    secret = printed or "lc_secret_token"
    script = tmp_path / name
    script.write_text(
        "#!/bin/sh\n"
        f'[ "$1 $2 $3" = "token create weightroom" ] || exit 9\n'
        f'echo "note: created"\n'
        f'echo \'{{"token": "{secret}", "name": "weightroom"}}\'\n'
        f"exit {exit_code}\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


def test_setup_from_nothing_creates_tls_account_hosts_bind_and_tokens_by_reference(
    tmp_path: Path, database: Database
) -> None:
    config_path = tmp_path / "config.toml"
    loadcoach = _fake_app(tmp_path, "loadcoach")
    config_path.write_text(f'[apps.loadcoach]\nexecutable = "{loadcoach}"\n# keep me\n')
    settings = load_settings(config_path=config_path).settings
    answers = SetupAnswers(
        username="jordan", password="correct horse battery", bind="lan", lan_address="10.77.10.84"
    )
    report, tls = run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=answers,
        identity=IDENTITY,
        now=NOW,
        controller=FakeSystemdController(),
        start_console=False,
    )
    assert TlsPaths.for_settings(settings).complete() and tls.days_left >= 397
    assert report.tls.startswith("created")
    assert operator_count(database) == 1 and report.account == "created operator 'jordan'"
    assert report.allowed_hosts == ("jordan-main", "jordan-main.local", "10.77.10.84", "fd00::5")
    # ADR-0130: admin, because ADR-0127 rule 4 routes every runtime key through `PUT /settings`,
    # which both LoadCoach and PromptCadence require `admin` for.
    assert report.tokens["loadcoach"].startswith("scope admin →")
    assert report.tokens["promptcadence"] == "not installed; no token"
    secret = secrets_dir() / "loadcoach.token"
    assert secret.read_text() == "lc_secret_token\n"
    assert secret.stat().st_mode & 0o777 == 0o600
    assert secret.parent.stat().st_mode & 0o777 == 0o700

    written = config_path.read_text()
    assert "# keep me" in written  # comments survive the tomlkit round-trip
    assert "lc_secret_token" not in written  # the value never lands in the file
    data = tomllib.loads(written)
    assert data["server"]["host"] == "10.77.10.84"
    assert data["server"]["allowed_hosts"] == list(report.allowed_hosts)
    assert data["apps"]["loadcoach"]["api_key_file"] == str(secret)
    assert config_path.with_suffix(".toml.bak").is_file()
    assert "lc_secret_token" not in str(report.as_params())
    reloaded = load_settings(config_path=config_path).settings
    assert reloaded.server.host == "10.77.10.84"
    assert report.linger.endswith("(existing)") or "enabled" in report.linger
    assert set(report.units) == {
        "freeweight",
        "loadcoach",
        "ideapress",
        "promptcadence",
        "weightroom",
    }


def test_setup_keeps_an_existing_ca_and_account_and_can_choose_every_interface(
    tmp_path: Path, database: Database
) -> None:
    config_path = tmp_path / "config.toml"
    settings = load_settings(config_path=config_path).settings
    first = SetupAnswers(username="jordan", password="correct horse battery", bind="loopback")
    run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=first,
        identity=IDENTITY,
        now=NOW,
        controller=FakeSystemdController(),
        start_console=False,
    )
    fingerprint = TlsPaths.for_settings(settings).ca_crt.read_bytes()
    second = SetupAnswers(username="ignored", password=None, bind="all")
    report, _tls = run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=second,
        identity=IDENTITY,
        now=NOW,
        controller=FakeSystemdController(),
        start_console=False,
    )
    assert report.tls.startswith("kept") and report.account == "kept the existing operator account"
    assert TlsPaths.for_settings(settings).ca_crt.read_bytes() == fingerprint
    data = tomllib.loads(config_path.read_text())
    assert data["server"]["host"] == "0.0.0.0" and data["server"]["allow_lan_exposure"] is True  # noqa: S104


def test_setup_refuses_a_lan_bind_without_an_address_and_a_missing_password(
    tmp_path: Path, database: Database
) -> None:
    config_path = tmp_path / "config.toml"
    settings = load_settings(config_path=config_path).settings
    with pytest.raises(ValueError, match="password"):
        run_setup(
            settings,
            config_path=config_path,
            database=database,
            answers=SetupAnswers(username="j", password=None, bind="loopback"),
            identity=IDENTITY,
            now=NOW,
            controller=FakeSystemdController(),
            start_console=False,
        )
    with pytest.raises(ValueError, match="address"):
        run_setup(
            settings,
            config_path=config_path,
            database=database,
            answers=SetupAnswers(username="j", password="correct horse battery", bind="lan"),
            identity=IDENTITY,
            now=NOW,
            controller=FakeSystemdController(),
            start_console=False,
        )


def test_a_failing_token_command_is_reported_not_fatal(tmp_path: Path, database: Database) -> None:
    config_path = tmp_path / "config.toml"
    broken = _fake_app(tmp_path, "promptcadence", exit_code=3)
    config_path.write_text(f'[apps.promptcadence]\nexecutable = "{broken}"\n')
    settings = load_settings(config_path=config_path).settings
    report, _tls = run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=SetupAnswers(username="j", password="correct horse battery", bind="loopback"),
        identity=IDENTITY,
        now=NOW,
        controller=FakeSystemdController(),
        start_console=False,
    )
    assert report.tokens["promptcadence"].startswith("failed:")
    assert not (secrets_dir() / "promptcadence.token").exists()


def test_issue_token_via_cli_parses_the_json_line_and_refuses_the_rest(tmp_path: Path) -> None:
    good = _fake_app(tmp_path, "loadcoach", printed="lc_abc")
    assert issue_token_via_cli(good, "write") == "lc_abc"
    silent = tmp_path / "silent"
    silent.write_text("#!/bin/sh\necho nothing\n")
    silent.chmod(silent.stat().st_mode | stat.S_IXUSR)
    with pytest.raises(RuntimeError, match="no token"):
        issue_token_via_cli(str(silent), "write")
    with pytest.raises(RuntimeError, match="failed to run"):
        issue_token_via_cli(str(tmp_path / "absent"), "write")


def test_installed_executable_prefers_the_configured_path(tmp_path: Path) -> None:
    config_path = tmp_path / "c.toml"
    config_path.write_text(f'[apps.loadcoach]\nexecutable = "{tmp_path}/nope"\n')
    settings = load_settings(config_path=config_path).settings
    assert installed_executable(settings, "loadcoach") is None
    found = installed_executable(settings, "ideapress")
    assert found is None or found.endswith("ideapress")


def test_write_config_changes_creates_nested_tables_and_keeps_the_previous_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.toml"
    write_config_changes(path, {"server.port": 9000})
    assert tomllib.loads(path.read_text())["server"]["port"] == 9000
    assert "# WeightRoomGym configuration" in path.read_text()
    write_config_changes(path, {"apps.loadcoach.api_key_file": "/x", "server.port": 9001})
    data = tomllib.loads(path.read_text())
    assert data["apps"]["loadcoach"]["api_key_file"] == "/x" and data["server"]["port"] == 9001
    assert tomllib.loads(path.with_suffix(".toml.bak").read_text())["server"]["port"] == 9000


def test_the_wizard_enables_lingering_before_it_writes_a_unit(
    tmp_path: Path, database: Database
) -> None:
    """ADR-0125 rule 2: a unit written under a session that does not linger dies at logout."""
    config_path = tmp_path / "config.toml"
    settings = load_settings(config_path=config_path).settings
    host = FakeSystemdController(linger=False)
    report, _tls = run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=SetupAnswers(username="j", password="correct horse battery", bind="loopback"),
        identity=IDENTITY,
        now=NOW,
        controller=host,
        start_console=False,
    )
    assert report.linger == "enabled for " + (host.calls[0][1] if host.calls else "")
    assert host.calls[0][0] == "enable-linger"
    assert host.linger is True


def test_the_wizard_refuses_to_continue_when_lingering_cannot_be_enabled() -> None:
    class Refusing(FakeSystemdController):
        def enable_linger(self, user: str) -> CommandResult:
            return CommandResult(
                ("loginctl", "enable-linger", user),
                returncode=1,
                stdout="",
                stderr="Failed to enable linger: Access denied",
            )

    report = SetupReport()
    with pytest.raises(UnitActionFailed) as caught:
        enable_linger_step(Refusing(linger=False), user="op", report=report)
    assert caught.value.code == "UNIT_ACTION_FAILED"
    assert caught.value.details["command"] == "loginctl enable-linger op"
    assert "Access denied" in caught.value.message
    assert report.linger.startswith("failed:")


def test_lingering_already_on_is_left_alone() -> None:
    host = FakeSystemdController(linger=True)
    report = SetupReport()
    enable_linger_step(host, user="op", report=report)
    assert report.linger == "already enabled for op"
    assert host.calls == []


def test_the_wizard_writes_the_units_and_says_which_applications_have_none(
    tmp_path: Path, database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.toml"
    loadcoach = _fake_app(tmp_path, "loadcoach")
    config_path.write_text(f'[apps.loadcoach]\nexecutable = "{loadcoach}"\n')
    settings = load_settings(config_path=config_path).settings
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    report, _tls = run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=SetupAnswers(username="j", password="correct horse battery", bind="loopback"),
        identity=IDENTITY,
        now=NOW,
        controller=FakeSystemdController(),
        start_console=False,
    )
    assert report.units["loadcoach"] == "written"
    assert report.units["freeweight"] == "not_installed"
    unit = tmp_path / "xdg" / "systemd" / "user" / "loadcoach.service"
    assert unit.is_file()
    assert "MemoryMax=24G" in unit.read_text(encoding="utf-8")
    assert "--no-start-console" in report.console


def test_the_console_unit_is_enabled_and_started_by_default(
    tmp_path: Path, database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-0125 rule 6: the console outlives the login that installed it."""
    config_path = tmp_path / "config.toml"
    settings = load_settings(config_path=config_path).settings
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    host = FakeSystemdController()
    report, _tls = run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=SetupAnswers(username="j", password="correct horse battery", bind="loopback"),
        identity=IDENTITY,
        now=NOW,
        controller=host,
    )
    assert report.console == "enabled and started as weightroom.service"
    assert ("act", "user", "weightroom.service", "enable") in host.calls
    assert ("act", "user", "weightroom.service", "start") in host.calls


def test_a_host_without_systemd_finishes_the_wizard_and_says_so_by_name(
    tmp_path: Path, database: Database
) -> None:
    """ADR-0125 rule 7: the rest of the console works."""
    config_path = tmp_path / "config.toml"
    settings = load_settings(config_path=config_path).settings
    report, tls = run_setup(
        settings,
        config_path=config_path,
        database=database,
        answers=SetupAnswers(username="j", password="correct horse battery", bind="loopback"),
        identity=IDENTITY,
        now=NOW,
        controller=FakeSystemdController(supported=False),
    )
    assert tls.days_left >= 397
    assert operator_count(database) == 1
    assert "unsupported on this host" in report.units["all"]
    assert "unsupported on this host" in report.console
