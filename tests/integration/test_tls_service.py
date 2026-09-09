"""weightroom.services.tls on a real directory: files, modes, verification, the four verbs."""

from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes

from weightroom.config import TlsMissingError, load_settings, tls_dir
from weightroom.services.tls import (
    HostIdentity,
    TlsAlreadyInitialised,
    TlsPaths,
    _addresses_from_ip_json,
    ensure_tls,
    host_identity,
    init_tls,
    renew_leaf,
    rotate_tls,
    tls_status,
    trust_steps,
)

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
IDENTITY = HostIdentity("jordan-main", ("10.77.10.84",))


@pytest.fixture
def settings(tmp_path: Path):  # type: ignore[no-untyped-def]  # a fixture returning Settings
    return load_settings(config_path=tmp_path / "absent.toml").settings


def test_init_writes_four_files_with_the_documented_modes_and_lifetimes(settings) -> None:  # type: ignore[no-untyped-def]
    status = init_tls(settings, identity=IDENTITY, now=NOW)
    paths = TlsPaths.for_settings(settings)
    assert paths.directory == tls_dir(settings)
    assert paths.complete()
    assert paths.directory.stat().st_mode & 0o777 == 0o700
    assert paths.ca_key.stat().st_mode & 0o777 == 0o600
    assert paths.server_key.stat().st_mode & 0o777 == 0o600
    assert status.ca_subject == "CN=WeightRoomGym CA jordan-main"
    assert status.leaf_subject == "CN=jordan-main"
    assert status.days_left == 398 - 1 or status.days_left == 398
    assert status.leaf_names == {
        "jordan-main",
        "jordan-main.local",
        "localhost",
        "10.77.10.84",
        "127.0.0.1",
        "::1",
    }
    ca = x509.load_pem_x509_certificate(paths.ca_crt.read_bytes())
    assert ca.not_valid_after_utc - NOW >= timedelta(days=3650)
    constraints = ca.extensions.get_extension_for_class(x509.BasicConstraints)
    assert constraints.critical and constraints.value.ca and constraints.value.path_length == 0
    usage = ca.extensions.get_extension_for_class(x509.KeyUsage).value
    assert usage.key_cert_sign and not usage.digital_signature
    leaf = x509.load_pem_x509_certificate(paths.server_crt.read_bytes())
    assert leaf.signature_hash_algorithm is not None
    assert isinstance(leaf.signature_hash_algorithm, hashes.SHA256)
    assert leaf.not_valid_after_utc == NOW + timedelta(days=398)
    assert len(status.ca_fingerprint_sha256) == 95 and status.ca_fingerprint_sha256.count(":") == 31


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not on PATH")
def test_the_leaf_verifies_against_the_root_with_openssl(settings) -> None:  # type: ignore[no-untyped-def]
    init_tls(settings, identity=IDENTITY, now=datetime.now(UTC))
    paths = TlsPaths.for_settings(settings)
    completed = subprocess.run(  # noqa: S603 — fixed argv, a test
        [
            str(shutil.which("openssl")),
            "verify",
            "-CAfile",
            str(paths.ca_crt),
            str(paths.server_crt),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().endswith("OK")
    fingerprint = subprocess.run(  # noqa: S603
        [
            str(shutil.which("openssl")),
            "x509",
            "-in",
            str(paths.ca_crt),
            "-noout",
            "-fingerprint",
            "-sha256",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    status = tls_status(paths, now=datetime.now(UTC))
    assert status.ca_fingerprint_sha256 in fingerprint


def test_init_refuses_a_second_time_and_rotate_replaces_the_root(settings) -> None:  # type: ignore[no-untyped-def]
    first = init_tls(settings, identity=IDENTITY, now=NOW)
    with pytest.raises(TlsAlreadyInitialised):
        init_tls(settings, identity=IDENTITY, now=NOW)
    revoked: list[int] = []

    def revoke() -> int:
        revoked.append(1)
        return 3

    rotated = rotate_tls(settings, identity=IDENTITY, now=NOW, revoke_sessions=revoke)
    assert rotated.ca_fingerprint_sha256 != first.ca_fingerprint_sha256
    assert revoked == [1]


def test_renew_keeps_the_root_and_changes_the_leaf(settings) -> None:  # type: ignore[no-untyped-def]
    first = init_tls(settings, identity=IDENTITY, now=NOW)
    renewed = renew_leaf(settings, identity=HostIdentity("jordan-main", ("10.0.0.2",)), now=NOW)
    assert renewed.ca_fingerprint_sha256 == first.ca_fingerprint_sha256
    assert renewed.leaf_fingerprint_sha256 != first.leaf_fingerprint_sha256
    assert "10.0.0.2" in renewed.leaf_names and "10.77.10.84" not in renewed.leaf_names


def test_renew_without_a_root_is_tls_missing(settings) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(TlsMissingError):
        renew_leaf(settings, identity=IDENTITY, now=NOW)


def test_status_refuses_an_incomplete_or_inconsistent_directory(settings) -> None:  # type: ignore[no-untyped-def]
    init_tls(settings, identity=IDENTITY, now=NOW)
    paths = TlsPaths.for_settings(settings)
    paths.server_crt.unlink()
    with pytest.raises(TlsMissingError, match="complete"):
        tls_status(paths, now=NOW)
    paths.server_crt.write_text("not a certificate")
    with pytest.raises(TlsMissingError, match="unreadable"):
        tls_status(paths, now=NOW)


def test_ensure_tls_initialises_on_loopback_renews_when_due_and_refuses_off_loopback(  # type: ignore[no-untyped-def]
    settings,
) -> None:
    with pytest.raises(TlsMissingError, match="setup"):
        ensure_tls(settings, identity=IDENTITY, now=NOW, initialise=False)
    first = ensure_tls(settings, identity=IDENTITY, now=NOW, initialise=True)
    same = ensure_tls(settings, identity=IDENTITY, now=NOW + timedelta(days=1), initialise=True)
    assert same.leaf_fingerprint_sha256 == first.leaf_fingerprint_sha256
    due = ensure_tls(settings, identity=IDENTITY, now=NOW + timedelta(days=370), initialise=True)
    assert due.leaf_fingerprint_sha256 != first.leaf_fingerprint_sha256
    assert due.days_left == 398
    moved = ensure_tls(
        settings,
        identity=HostIdentity("jordan-main", ("10.9.9.9",)),
        now=NOW + timedelta(days=370),
        initialise=True,
    )
    assert "10.9.9.9" in moved.leaf_names


def test_addresses_from_ip_json_keep_global_scope_only() -> None:
    output = """[
      {"ifname": "lo", "addr_info": [{"family": "inet", "local": "127.0.0.1", "scope": "host"}]},
      {"ifname": "eno1", "addr_info": [
        {"family": "inet", "local": "10.77.10.84", "scope": "global"},
        {"family": "inet6", "local": "fe80::1", "scope": "link"},
        {"family": "inet6", "local": "fd00::5", "scope": "global"},
        {"family": "inet", "local": "10.77.10.84", "scope": "global"}
      ]}
    ]"""
    assert _addresses_from_ip_json(output) == ("10.77.10.84", "fd00::5")


def test_host_identity_lowercases_and_strips_the_domain() -> None:
    identity = host_identity(hostname="Jordan-Main.lan")
    assert identity.hostname == "jordan-main"
    for address in identity.addresses:
        assert not address.startswith("127.") and address != "::1"


def test_trust_steps_name_every_platform_and_the_android_store() -> None:
    platforms = [platform for platform, _ in trust_steps("h")]
    assert len(platforms) == 5
    text = "\n".join(text for _, text in trust_steps("h"))
    assert "CA certificate" in text and "Certificate Trust Settings" in text
