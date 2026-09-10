"""weightroom.config: precedence field by field, the refusal set, the key sets (spec §12)."""

from __future__ import annotations

from pathlib import Path

import pytest
from baseaicore import ConfigurationError

from weightroom.config import (
    APPLICATIONS,
    InsecureBindingError,
    Settings,
    config_dir,
    data_dir,
    env_var_for,
    leaf_keys,
    load_settings,
    load_settings_tolerant,
    resolve_config_path,
    secrets_dir,
    security_keys,
    tls_dir,
)


def test_zero_configuration_defaults_are_the_documented_ones(tmp_path: Path) -> None:
    loaded = load_settings(config_path=tmp_path / "absent.toml")
    s = loaded.settings
    assert loaded.config_file_used is False
    assert (s.server.host, s.server.port, s.server.trust_port) == ("127.0.0.1", 8769, 8770)
    assert s.server.failed_login_per_minute == 5
    assert s.server.max_body_bytes == 64 * 1024 * 1024
    assert (s.tls.leaf_days, s.tls.ca_years, s.tls.renew_before_days) == (398, 10, 30)
    assert (s.auth.session_idle_hours, s.auth.session_max_days, s.auth.reauth_window_minutes) == (
        12,
        7,
        5,
    )
    assert s.storage.database_url == f"sqlite:///{data_dir()}/weightroom.sqlite3"
    assert s.storage.auto_migrate is True
    assert s.apps.loadcoach.base_url == "http://127.0.0.1:8766"
    assert s.apps.promptcadence.base_url == "http://127.0.0.1:8768"
    assert (s.host.memory_high, s.host.memory_max) == ("22G", "24G")
    assert s.telemetry.interval_ms == 1000 and s.telemetry.history_hours == 72
    assert s.chat.default_classification == "confidential"
    assert s.alerts.gpu_temperature_c == 85
    assert s.logging.include_content is False
    assert tls_dir(s) == config_dir() / "tls"
    assert secrets_dir() == config_dir() / "secrets"
    assert str(config_dir()).endswith("wr-gym")


def test_postgres_url_defaults_auto_migrate_off(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text('[storage]\ndatabase_url = "postgresql+psycopg://u:p@h/db"\n')
    assert load_settings(config_path=file).settings.storage.auto_migrate is False


def test_precedence_file_then_env_then_cli_at_every_depth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / "config.toml"
    file.write_text('[server]\nport = 9001\n[apps.loadcoach]\nbase_url = "http://127.0.0.1:1"\n')
    loaded = load_settings(config_path=file)
    assert loaded.settings.server.port == 9001
    assert loaded.sources["server.port"] == "file"
    assert loaded.sources["apps.loadcoach.base_url"] == "file"
    assert loaded.sources["apps.freeweight.base_url"] == "default"

    monkeypatch.setenv("WEIGHTROOM_SERVER__PORT", "9002")
    monkeypatch.setenv("WEIGHTROOM_APPS__LOADCOACH__BASE_URL", "http://127.0.0.1:2")
    loaded = load_settings(config_path=file)
    assert loaded.settings.server.port == 9002
    assert loaded.settings.apps.loadcoach.base_url == "http://127.0.0.1:2"
    assert loaded.sources["server.port"] == "env WEIGHTROOM_SERVER__PORT"
    assert loaded.sources["apps.loadcoach.base_url"] == "env WEIGHTROOM_APPS__LOADCOACH__BASE_URL"

    loaded = load_settings(
        config_path=file,
        cli_overrides={"server": {"port": 9003}, "apps": {"loadcoach": {"base_url": "http://x"}}},
    )
    assert loaded.settings.server.port == 9003
    assert loaded.sources["server.port"] == "cli"
    assert loaded.sources["apps.loadcoach.base_url"] == "cli"


def test_per_leaf_override_leaves_siblings_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / "config.toml"
    file.write_text('[server]\nport = 9100\n[apps.loadcoach]\nexecutable = "/x/loadcoach"\n')
    monkeypatch.setenv("WEIGHTROOM_APPS__LOADCOACH__BASE_URL", "http://127.0.0.1:9")
    loaded = load_settings(config_path=file, cli_overrides={"server": {"trust_port": 9101}})
    assert loaded.settings.server.port == 9100
    assert loaded.settings.server.trust_port == 9101
    assert loaded.settings.apps.loadcoach.executable == "/x/loadcoach"
    assert loaded.settings.apps.loadcoach.base_url == "http://127.0.0.1:9"


def test_log_level_shorthand_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WEIGHTROOM_LOG_LEVEL", "DEBUG")
    assert load_settings(config_path=tmp_path / "x.toml").settings.logging.level == "DEBUG"


def test_env_csv_split_for_allowed_hosts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WEIGHTROOM_SERVER__HOST", "10.0.0.5")
    monkeypatch.setenv("WEIGHTROOM_SERVER__ALLOWED_HOSTS", "a.local, 10.0.0.5")
    loaded = load_settings(config_path=tmp_path / "x.toml")
    assert loaded.settings.server.allowed_hosts == ("a.local", "10.0.0.5")


def test_unknown_key_rejected_with_suggestion_at_depth(tmp_path: Path) -> None:
    file = tmp_path / "config.toml"
    file.write_text('[apps.loadcoach]\nbase_urls = "x"\n')
    with pytest.raises(ConfigurationError, match="apps.loadcoach.base_url"):
        load_settings(config_path=file)


def test_bad_type_names_the_field(tmp_path: Path) -> None:
    file = tmp_path / "config.toml"
    file.write_text('[server]\nport = "eight"\n')
    with pytest.raises(ConfigurationError, match="server.port"):
        load_settings(config_path=file)


def test_invalid_toml_rejected(tmp_path: Path) -> None:
    file = tmp_path / "config.toml"
    file.write_text("this is not [ valid toml")
    with pytest.raises(ConfigurationError, match="not valid TOML"):
        load_settings(config_path=file)


def test_all_interfaces_without_acknowledgement_refused(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text('[server]\nhost = "0.0.0.0"\nallowed_hosts = ["x"]\n')
    with pytest.raises(InsecureBindingError, match="allow_lan_exposure") as info:
        load_settings(config_path=file)
    assert info.value.code == "INSECURE_BINDING"


def test_non_loopback_without_allowed_hosts_refused(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text('[server]\nhost = "10.0.0.5"\n')
    with pytest.raises(InsecureBindingError, match="allowed_hosts"):
        load_settings(config_path=file)


def test_trust_port_must_differ(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text("[server]\ntrust_port = 8769\n")
    with pytest.raises(ConfigurationError, match="trust_port"):
        load_settings(config_path=file)


def test_acknowledged_lan_bind_passes_the_config_level_checks(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text(
        '[server]\nhost = "0.0.0.0"\nallow_lan_exposure = true\nallowed_hosts = ["h.local"]\n'
    )
    assert load_settings(config_path=file).settings.server.allowed_hosts == ("h.local",)


def test_resolve_config_path_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert resolve_config_path("~/x.toml") == Path.home() / "x.toml"
    assert resolve_config_path() == config_dir() / "config.toml"
    (tmp_path / "wr-gym.toml").write_text("")
    assert resolve_config_path() == tmp_path / "wr-gym.toml"
    monkeypatch.setenv("WEIGHTROOM_CONFIG", str(tmp_path / "env.toml"))
    assert resolve_config_path() == tmp_path / "env.toml"


def test_data_dir_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WEIGHTROOM_DATA_DIR", str(tmp_path / "d"))
    assert data_dir() == tmp_path / "d"


def test_leaf_keys_cover_every_application_block_and_no_section() -> None:
    keys = leaf_keys()
    for app in APPLICATIONS:
        assert f"apps.{app}.base_url" in keys
    assert "apps" not in keys and "apps.loadcoach" not in keys
    assert env_var_for("apps.loadcoach.api_key_file") == "WEIGHTROOM_APPS__LOADCOACH__API_KEY_FILE"
    with pytest.raises(ValueError, match="section.field"):
        env_var_for("server")


def test_security_keys_are_exactly_the_five_sections(tmp_path: Path) -> None:
    keys = security_keys()
    assert {key.split(".", 1)[0] for key in keys} == {"server", "tls", "auth", "apps", "host"}
    assert "storage.database_url" not in keys and "logging.include_content" not in keys
    assert "apps.promptcadence.api_key_file" in keys
    assert keys <= set(leaf_keys())


def test_tolerant_load_reports_unknown_keys_at_any_depth(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text(
        '[server]\nport = 9000\nbogus = 1\n[apps.loadcoach]\nnope = "x"\n[mystery]\na = 1\n'
    )
    loaded, problems = load_settings_tolerant(file)
    assert loaded.settings.server.port == 9000
    assert set(problems) == {
        "unknown configuration key 'server.bogus'",
        "unknown configuration key 'apps.loadcoach.nope'",
        "unknown configuration key 'mystery'",
    }


def test_settings_model_forbids_extra_everywhere() -> None:
    with pytest.raises(Exception, match="extra"):
        Settings.model_validate({"tls": {"leaf_days": 1, "x": 2}})


def test_a_partial_apps_table_keeps_the_applications_own_port(tmp_path: Path) -> None:
    """Configuration standards §1: overriding is per leaf, not per section (found at row W2)."""
    file = tmp_path / "config.toml"
    file.write_text('[apps.loadcoach]\nexecutable = "/opt/bin/loadcoach"\n', encoding="utf-8")
    settings = load_settings(config_path=file).settings
    assert settings.apps.loadcoach.executable == "/opt/bin/loadcoach"
    assert settings.apps.loadcoach.base_url == "http://127.0.0.1:8766"
    assert settings.apps.freeweight.base_url == "http://127.0.0.1:8765"


def test_an_explicit_base_url_still_wins(tmp_path: Path) -> None:
    file = tmp_path / "config.toml"
    file.write_text('[apps.ideapress]\nbase_url = "http://127.0.0.1:9999"\n', encoding="utf-8")
    settings = load_settings(config_path=file).settings
    assert settings.apps.ideapress.base_url == "http://127.0.0.1:9999"


def test_the_port_table_matches_the_declared_defaults() -> None:
    from weightroom.config import DEFAULT_APP_PORTS, Settings

    defaults = Settings()
    for name, port in DEFAULT_APP_PORTS.items():
        assert getattr(defaults.apps, name).base_url == f"http://127.0.0.1:{port}"
