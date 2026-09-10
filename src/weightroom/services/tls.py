"""weightroom.services.tls — the certificate authority on disk (ADR-0126 rules 2, 3, 9).

The ``cryptography`` calls, the four files under ``<config>/tls/`` (directory ``0700``, keys
``0600``), and the four verbs: ``init`` (root and leaf), ``renew`` (a new leaf under the same
root, no re-trust), ``rotate`` (a new root and leaf; every session revoked), ``show``. The
decisions — names, lifetimes, whether to renew — are :mod:`weightroom.domain.tls`.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import shutil
import socket
import subprocess  # noqa: S404 — explicit argv to `ip`, never a shell
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from baseaicore import SuiteError
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from weightroom.config import TlsMissingError, tls_dir
from weightroom.domain.tls import (
    CA_COMMON_NAME_PREFIX,
    CertificateNames,
    RenewalDecision,
    certificate_names,
    renewal_decision,
)
from weightroom.services.processes import child_environment

if TYPE_CHECKING:
    from collections.abc import Callable

    from weightroom.config import Settings

__all__ = [
    "HostIdentity",
    "TlsAlreadyInitialised",
    "TlsPaths",
    "TlsStatus",
    "ensure_tls",
    "fingerprint_sha256",
    "host_identity",
    "init_tls",
    "renew_leaf",
    "rotate_tls",
    "tls_status",
    "trust_steps",
]

logger = logging.getLogger(__name__)

_FILES = ("ca.key", "ca.crt", "server.key", "server.crt")


class TlsAlreadyInitialised(SuiteError):
    """``tls init`` found a complete directory; ``renew`` or ``rotate`` is the verb wanted."""

    code: ClassVar[str] = "TLS_ALREADY_INITIALISED"


@dataclass(frozen=True, slots=True)
class TlsPaths:
    """The four files (ADR-0126 rule 2)."""

    directory: Path

    @property
    def ca_key(self) -> Path:
        """The root's private key, ``0600``."""
        return self.directory / "ca.key"

    @property
    def ca_crt(self) -> Path:
        """The root certificate — public; what a device trusts."""
        return self.directory / "ca.crt"

    @property
    def server_key(self) -> Path:
        """The leaf's private key, ``0600``."""
        return self.directory / "server.key"

    @property
    def server_crt(self) -> Path:
        """The leaf certificate uvicorn serves."""
        return self.directory / "server.crt"

    @classmethod
    def for_settings(cls, settings: Settings) -> TlsPaths:
        """The paths ``[tls] directory`` (or its default) names."""
        return cls(tls_dir(settings))

    def present(self) -> tuple[str, ...]:
        """Which of the four files exist."""
        return tuple(name for name in _FILES if (self.directory / name).is_file())

    def complete(self) -> bool:
        """Whether all four files exist."""
        return len(self.present()) == len(_FILES)


@dataclass(frozen=True, slots=True)
class HostIdentity:
    """The host's bare name and its non-loopback addresses, as the SANs are built from them."""

    hostname: str
    addresses: tuple[str, ...]


def _addresses_from_ip_json(output: str) -> tuple[str, ...]:
    """Parse ``ip -json address``: global-scope, non-loopback, non-link-local addresses."""
    found: list[str] = []
    for interface in json.loads(output):
        for info in interface.get("addr_info", ()):
            raw = info.get("local")
            if not raw or info.get("scope") not in ("global", "universe"):
                continue
            parsed = ipaddress.ip_address(raw)
            if parsed.is_loopback or parsed.is_link_local or parsed.is_multicast:
                continue
            if str(parsed) not in found:
                found.append(str(parsed))
    return tuple(found)


def host_identity(*, hostname: str | None = None) -> HostIdentity:
    """Discover the host's name and addresses for the SANs (ADR-0126 rule 2).

    Addresses come from ``ip -json address`` (explicit argv, no shell); without ``ip`` on
    ``PATH`` the fallback is whatever the hostname resolves to, minus loopback. Link-local and
    multicast addresses are never included — no phone reaches the console by them.

    Args:
        hostname: An override, for tests; ``socket.gethostname()`` otherwise.

    Returns:
        The identity, with addresses in the order the kernel lists them.
    """
    name = (hostname or socket.gethostname()).split(".")[0].lower()
    ip_binary = shutil.which("ip")
    if ip_binary is not None:
        try:
            completed = subprocess.run(  # noqa: S603 — argv is fixed, from shutil.which
                [ip_binary, "-json", "address"],
                capture_output=True,
                text=True,
                timeout=5,
                # Gold standard G12: a child sees the allowlist, never this process's
                # environment. `ip` needs nothing from it (row W2).
                env=child_environment(),
                check=True,
            )
            return HostIdentity(name, _addresses_from_ip_json(completed.stdout))
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            logger.warning("tls.ip_unavailable", extra={"detail": str(exc)})
    found: list[str] = []
    try:
        for *_rest, sockaddr in socket.getaddrinfo(name, None):
            parsed = ipaddress.ip_address(str(sockaddr[0]))
            if not (parsed.is_loopback or parsed.is_link_local) and str(parsed) not in found:
                found.append(str(parsed))
    except socket.gaierror:
        pass
    return HostIdentity(name, tuple(found))


def _write_private(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` with mode ``0600``, atomically."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        Path(temporary).chmod(0o600)
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _write_public(path: Path, data: bytes) -> None:
    _write_private(path, data)
    path.chmod(0o644)


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _issue_ca(
    hostname: str, *, now: datetime, years: int
) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = _name(f"{CA_COMMON_NAME_PREFIX} {hostname}")
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365 * years + years // 4))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return key, certificate


def _issue_leaf(
    ca_key: ec.EllipticCurvePrivateKey,
    ca_certificate: x509.Certificate,
    names: CertificateNames,
    *,
    now: datetime,
    days: int,
) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = ec.generate_private_key(ec.SECP256R1())
    sans: list[x509.GeneralName] = [x509.DNSName(name) for name in names.dns_names]
    sans.extend(x509.IPAddress(ipaddress.ip_address(ip)) for ip in names.ip_addresses)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(_name(names.common_name))
        .issuer_name(ca_certificate.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName(sans), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return key, certificate


def _pem_key(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _load_ca(paths: TlsPaths) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = serialization.load_pem_private_key(paths.ca_key.read_bytes(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise TlsMissingError(
            f"{paths.ca_key} is not an EC private key; `wr-gym tls rotate` reissues the root.",
            details={"file": str(paths.ca_key)},
        )
    return key, x509.load_pem_x509_certificate(paths.ca_crt.read_bytes())


def fingerprint_sha256(certificate: x509.Certificate) -> str:
    """The SHA-256 fingerprint in the colon form every OS's certificate viewer prints."""
    digest = certificate.fingerprint(hashes.SHA256()).hex().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def _san_names(certificate: x509.Certificate) -> frozenset[str]:
    try:
        extension = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    except x509.ExtensionNotFound:
        return frozenset()
    value = extension.value
    return frozenset(value.get_values_for_type(x509.DNSName)) | frozenset(
        str(ip) for ip in value.get_values_for_type(x509.IPAddress)
    )


@dataclass(frozen=True, slots=True)
class TlsStatus:
    """What ``tls show`` prints and ``/health`` reports."""

    paths: TlsPaths
    ca_subject: str
    ca_fingerprint_sha256: str
    ca_not_after: datetime
    leaf_subject: str
    leaf_fingerprint_sha256: str
    leaf_not_before: datetime
    leaf_not_after: datetime
    leaf_names: frozenset[str]
    days_left: int

    def as_json(self) -> dict[str, object]:
        """A JSON-ready view, paths as strings, instants as RFC 3339."""
        return {
            "directory": str(self.paths.directory),
            "ca": {
                "subject": self.ca_subject,
                "fingerprint_sha256": self.ca_fingerprint_sha256,
                "not_after": self.ca_not_after.isoformat(),
                "file": str(self.paths.ca_crt),
            },
            "leaf": {
                "subject": self.leaf_subject,
                "fingerprint_sha256": self.leaf_fingerprint_sha256,
                "not_before": self.leaf_not_before.isoformat(),
                "not_after": self.leaf_not_after.isoformat(),
                "names": sorted(self.leaf_names),
                "file": str(self.paths.server_crt),
                "days_left": self.days_left,
            },
        }


def tls_status(paths: TlsPaths, *, now: datetime) -> TlsStatus:
    """Read the directory and describe it.

    Raises:
        TlsMissingError: A file is missing or unreadable, or the leaf was not signed by the root.
    """
    if not paths.complete():
        raise TlsMissingError(
            f"{paths.directory} does not hold a complete CA (found {list(paths.present())}); "
            "run `wr-gym tls init`, or `wr-gym tls rotate` to replace a damaged one.",
            details={"directory": str(paths.directory), "present": list(paths.present())},
        )
    try:
        ca = x509.load_pem_x509_certificate(paths.ca_crt.read_bytes())
        leaf = x509.load_pem_x509_certificate(paths.server_crt.read_bytes())
        leaf.verify_directly_issued_by(ca)
    except (ValueError, TypeError, OSError) as exc:
        raise TlsMissingError(
            f"{paths.directory} is unreadable or inconsistent ({exc}); `wr-gym tls rotate` "
            "replaces it.",
            details={"directory": str(paths.directory)},
        ) from exc
    days_left = (leaf.not_valid_after_utc - now).days
    return TlsStatus(
        paths=paths,
        ca_subject=ca.subject.rfc4514_string(),
        ca_fingerprint_sha256=fingerprint_sha256(ca),
        ca_not_after=ca.not_valid_after_utc,
        leaf_subject=leaf.subject.rfc4514_string(),
        leaf_fingerprint_sha256=fingerprint_sha256(leaf),
        leaf_not_before=leaf.not_valid_before_utc,
        leaf_not_after=leaf.not_valid_after_utc,
        leaf_names=_san_names(leaf),
        days_left=days_left,
    )


def _issue_and_write_leaf(
    paths: TlsPaths, identity: HostIdentity, *, now: datetime, leaf_days: int
) -> None:
    ca_key, ca_certificate = _load_ca(paths)
    names = certificate_names(identity.hostname, identity.addresses)
    key, certificate = _issue_leaf(ca_key, ca_certificate, names, now=now, days=leaf_days)
    _write_private(paths.server_key, _pem_key(key))
    _write_public(paths.server_crt, certificate.public_bytes(serialization.Encoding.PEM))


def init_tls(
    settings: Settings, *, identity: HostIdentity, now: datetime, force: bool = False
) -> TlsStatus:
    """``wr-gym tls init``: a new root and a new leaf.

    Args:
        settings: For the directory and the lifetimes.
        identity: The host's name and addresses (SANs).
        now: The issue instant.
        force: Replace an existing directory (what ``rotate`` passes).

    Raises:
        TlsAlreadyInitialised: The directory is already complete and ``force`` is false.
    """
    paths = TlsPaths.for_settings(settings)
    if paths.present() and not force:
        raise TlsAlreadyInitialised(
            f"{paths.directory} already holds {list(paths.present())}; use `wr-gym tls renew` "
            "for a new leaf or `wr-gym tls rotate` for a new root.",
            details={"directory": str(paths.directory)},
        )
    paths.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    paths.directory.chmod(0o700)
    ca_key, ca_certificate = _issue_ca(identity.hostname, now=now, years=settings.tls.ca_years)
    _write_private(paths.ca_key, _pem_key(ca_key))
    _write_public(paths.ca_crt, ca_certificate.public_bytes(serialization.Encoding.PEM))
    _issue_and_write_leaf(paths, identity, now=now, leaf_days=settings.tls.leaf_days)
    logger.info("tls.initialised", extra={"directory": str(paths.directory)})
    return tls_status(paths, now=now)


def renew_leaf(settings: Settings, *, identity: HostIdentity, now: datetime) -> TlsStatus:
    """``wr-gym tls renew``: a new leaf under the same root; no device needs re-trusting.

    Raises:
        TlsMissingError: The root is missing or unreadable.
    """
    paths = TlsPaths.for_settings(settings)
    if not (paths.ca_key.is_file() and paths.ca_crt.is_file()):
        raise TlsMissingError(
            f"{paths.directory} has no root to sign with; run `wr-gym tls init`.",
            details={"directory": str(paths.directory)},
        )
    _issue_and_write_leaf(paths, identity, now=now, leaf_days=settings.tls.leaf_days)
    logger.info("tls.renewed", extra={"directory": str(paths.directory)})
    return tls_status(paths, now=now)


def rotate_tls(
    settings: Settings,
    *,
    identity: HostIdentity,
    now: datetime,
    revoke_sessions: Callable[[], int] | None = None,
) -> TlsStatus:
    """``wr-gym tls rotate``: a new root and leaf, every session revoked (ADR-0126 rule 9).

    Args:
        settings: For the directory and the lifetimes.
        identity: The host's name and addresses.
        now: The issue instant.
        revoke_sessions: Deletes every session row and returns the count; the caller supplies
            it because this module opens no database. ``None`` when there is none to revoke.
    """
    status = init_tls(settings, identity=identity, now=now, force=True)
    revoked = revoke_sessions() if revoke_sessions is not None else 0
    logger.info("tls.rotated", extra={"sessions_revoked": revoked})
    return status


def ensure_tls(
    settings: Settings, *, identity: HostIdentity, now: datetime, initialise: bool
) -> TlsStatus:
    """What ``serve`` does at startup: initialise if allowed, renew if due, refuse if broken.

    Args:
        settings: The loaded settings.
        identity: The host's names and addresses today.
        now: The current instant.
        initialise: Whether an *absent* directory may be created here — true on loopback (a
            zero-configuration start), false off it (ADR-0126 rule 6 wants ``setup`` first).

    Returns:
        The status after any renewal.

    Raises:
        TlsMissingError: The directory is absent and ``initialise`` is false, or incomplete.
    """
    paths = TlsPaths.for_settings(settings)
    if not paths.present():
        if not initialise:
            raise TlsMissingError(
                f"{paths.directory} does not exist; run `wr-gym setup` (or `wr-gym tls init`) "
                "before binding off loopback.",
                details={"directory": str(paths.directory)},
            )
        return init_tls(settings, identity=identity, now=now)
    status = tls_status(paths, now=now)
    wanted = certificate_names(identity.hostname, identity.addresses).all_names
    decision: RenewalDecision = renewal_decision(
        now=now,
        not_after=status.leaf_not_after,
        renew_before_days=settings.tls.renew_before_days,
        current_names=status.leaf_names,
        wanted_names=wanted,
    )
    if decision.renew:
        logger.info("tls.renewing", extra={"reason": decision.reason})
        return renew_leaf(settings, identity=identity, now=now)
    return status


def trust_steps(hostname: str) -> tuple[tuple[str, str], ...]:
    """The per-OS steps ``wr-gym trust`` prints and both trust pages show (LAN_ACCESS.md §3).

    Returns:
        ``(platform, steps)`` pairs, plain text.
    """
    store = f"weightroom-{hostname}"
    return (
        (
            "Linux (Debian/Ubuntu: system store, curl, Chrome)",
            f"sudo cp root.crt /usr/local/share/ca-certificates/{store}.crt\n"
            "sudo update-ca-certificates\n"
            "Firefox keeps its own store: Settings → Privacy & Security → Certificates → "
            "View Certificates → Authorities → Import…, tick 'Trust this CA to identify websites'.",
        ),
        (
            "macOS",
            "sudo security add-trusted-cert -d -r trustRoot -k "
            "/Library/Keychains/System.keychain root.crt\n"
            "(or double-click root.crt → Keychain Access → System → Trust → Always Trust)",
        ),
        (
            "Windows (administrator prompt)",
            "certutil -addstore -f Root root.crt",
        ),
        (
            "iOS / iPadOS",
            "1. Open the /root.crt link in Safari and allow the profile download.\n"
            "2. Settings → General → VPN & Device Management → install the profile.\n"
            "3. Settings → General → About → Certificate Trust Settings → enable full trust "
            "for the WeightRoomGym root. Without step 3 the profile is installed but not trusted.",
        ),
        (
            "Android",
            "Settings → Security & privacy → More security & privacy → Encryption & credentials "
            "→ Install a certificate → CA certificate → Install anyway → pick root.crt. "
            "The store is 'CA certificate', not 'VPN & app user certificate'.",
        ),
    )


def now_utc() -> datetime:
    """The clock the CLI injects; tests pass their own."""
    return datetime.now(UTC)
