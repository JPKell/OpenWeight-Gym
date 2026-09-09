"""Every startup refusal, with its message (development plan Phase 1 tests)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from weightroom.config import InsecureBindingError, TlsMissingError, load_settings
from weightroom.services.database import Database
from weightroom.services.runtime import has_operator, prepare
from weightroom.services.tls import HostIdentity, TlsPaths, init_tls

IDENTITY = HostIdentity("jordan-main", ("10.77.10.84",))
NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


def _lan(tmp_path: Path) -> Path:
    file = tmp_path / "lan.toml"
    file.write_text('[server]\nhost = "10.77.10.84"\nallowed_hosts = ["jordan-main.local"]\n')
    return file


def test_loopback_with_nothing_configured_prepares_and_initialises_tls(tmp_path: Path) -> None:
    loaded = load_settings(config_path=tmp_path / "absent.toml")
    runtime = prepare(loaded, now=NOW, identity=IDENTITY)
    assert runtime.has_operator is False
    assert TlsPaths.for_settings(loaded.settings).complete()
    assert runtime.tls.days_left >= 397
    assert prepare(loaded, now=NOW, identity=IDENTITY).tls.leaf_fingerprint_sha256 == (
        runtime.tls.leaf_fingerprint_sha256
    )


def test_lan_bind_without_tls_is_insecure_binding_naming_setup(tmp_path: Path) -> None:
    loaded = load_settings(config_path=_lan(tmp_path))
    with pytest.raises(InsecureBindingError, match="certificate authority") as info:
        prepare(loaded, now=NOW, identity=IDENTITY)
    assert info.value.code == "INSECURE_BINDING"
    assert not TlsPaths.for_settings(loaded.settings).present()


def test_lan_bind_without_an_account_is_insecure_binding(tmp_path: Path) -> None:
    loaded = load_settings(config_path=_lan(tmp_path))
    init_tls(loaded.settings, identity=IDENTITY, now=NOW)
    with pytest.raises(InsecureBindingError, match="operator account"):
        prepare(loaded, now=NOW, identity=IDENTITY)


def test_a_broken_tls_directory_is_tls_missing_on_any_bind(tmp_path: Path) -> None:
    loaded = load_settings(config_path=tmp_path / "absent.toml")
    init_tls(loaded.settings, identity=IDENTITY, now=NOW)
    TlsPaths.for_settings(loaded.settings).ca_crt.unlink()
    with pytest.raises(TlsMissingError) as info:
        prepare(loaded, now=NOW, identity=IDENTITY)
    assert info.value.code == "TLS_MISSING"


def test_has_operator_reads_the_table(tmp_path: Path) -> None:
    loaded = load_settings(config_path=tmp_path / "absent.toml")
    prepare(loaded, now=NOW, identity=IDENTITY)
    with Database.from_url(loaded.settings.storage.database_url or "") as database:
        assert has_operator(database) is False
