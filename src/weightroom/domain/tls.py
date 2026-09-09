"""weightroom.domain.tls — what to issue and when to renew (ADR-0126 rule 2), with no I/O.

The certificate authority's shape is a decision, not a library call: the root's name, the
subject alternative names a leaf must carry for this host, the lifetimes, and the rule that
decides whether ``wr-gym serve`` reissues the leaf at startup. Everything here is a pure
function of its arguments; :mod:`weightroom.services.tls` is where ``cryptography`` and the
filesystem come in.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta

__all__ = [
    "CA_COMMON_NAME_PREFIX",
    "LOOPBACK_SANS",
    "CertificateNames",
    "RenewalDecision",
    "certificate_names",
    "renewal_decision",
]

CA_COMMON_NAME_PREFIX = "WeightRoomGym CA"
"""The root is ``CN=WeightRoomGym CA <hostname>`` (ADR-0126 rule 2)."""

LOOPBACK_SANS: tuple[str, ...] = ("localhost", "127.0.0.1", "::1")
"""Every leaf carries these, so ``https://localhost:8769`` validates on the host itself."""


@dataclass(frozen=True, slots=True)
class CertificateNames:
    """The names a leaf for this host must carry, split by SAN kind.

    Attributes:
        common_name: The leaf's subject CN — the bare hostname.
        dns_names: ``hostname``, ``hostname.local``, ``localhost``; deduplicated, in that order.
        ip_addresses: Every non-loopback address the host holds, then ``127.0.0.1`` and ``::1``.
    """

    common_name: str
    dns_names: tuple[str, ...]
    ip_addresses: tuple[str, ...]

    @property
    def all_names(self) -> frozenset[str]:
        """Every SAN as one set — what the renewal rule compares."""
        return frozenset(self.dns_names) | frozenset(self.ip_addresses)


def certificate_names(hostname: str, addresses: tuple[str, ...]) -> CertificateNames:
    """Decide the SANs for a leaf on ``hostname`` holding ``addresses`` (ADR-0126 rule 2).

    Args:
        hostname: The host's bare name, e.g. ``jordan-main``.
        addresses: The host's non-loopback IPv4/IPv6 addresses at issue time, any order.

    Returns:
        The names, with ``localhost``, ``127.0.0.1`` and ``::1`` always present.

    Raises:
        ValueError: ``hostname`` is empty, or an address does not parse as an IP address.
    """
    name = hostname.strip().lower()
    if not name:
        message = "a certificate needs a hostname"
        raise ValueError(message)
    dns: list[str] = []
    for candidate in (name, f"{name}.local", "localhost"):
        if candidate not in dns:
            dns.append(candidate)
    ips: list[str] = []
    for raw in (*addresses, "127.0.0.1", "::1"):
        parsed = str(ipaddress.ip_address(raw.strip()))
        if parsed not in ips:
            ips.append(parsed)
    return CertificateNames(common_name=name, dns_names=tuple(dns), ip_addresses=tuple(ips))


@dataclass(frozen=True, slots=True)
class RenewalDecision:
    """Whether the leaf should be reissued now, and why (or why not)."""

    renew: bool
    reason: str
    days_left: int


def renewal_decision(
    *,
    now: datetime,
    not_after: datetime,
    renew_before_days: int,
    current_names: frozenset[str],
    wanted_names: frozenset[str],
) -> RenewalDecision:
    """Decide whether ``serve`` renews the leaf at startup (ADR-0126 rule 2).

    Renew when fewer than ``renew_before_days`` remain — 29 days renews, 31 does not — or when
    the host's names and addresses no longer match the SANs the leaf carries. An already-expired
    leaf is the first case with a negative count.

    Args:
        now: The current instant (timezone-aware).
        not_after: The leaf's expiry.
        renew_before_days: ``[tls] renew_before_days``.
        current_names: The SANs the leaf carries.
        wanted_names: The SANs :func:`certificate_names` wants today.

    Returns:
        The decision with the number of whole days left.
    """
    remaining = not_after - now
    days_left = remaining.days if remaining >= timedelta(0) else -((-remaining).days + 1)
    if remaining < timedelta(days=renew_before_days):
        return RenewalDecision(
            renew=True,
            reason=f"{days_left} day(s) left, fewer than {renew_before_days}",
            days_left=days_left,
        )
    if current_names != wanted_names:
        added = sorted(wanted_names - current_names)
        gone = sorted(current_names - wanted_names)
        return RenewalDecision(
            renew=True,
            reason=f"host names changed (added {added}, removed {gone})",
            days_left=days_left,
        )
    return RenewalDecision(renew=False, reason=f"{days_left} day(s) left", days_left=days_left)
