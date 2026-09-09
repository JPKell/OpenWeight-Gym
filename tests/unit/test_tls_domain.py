"""weightroom.domain.tls: SANs and the renewal decision (ADR-0126 rule 2), pure."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from weightroom.domain.tls import RenewalDecision, certificate_names, renewal_decision

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


def test_names_carry_hostname_local_localhost_and_every_address_plus_loopback() -> None:
    names = certificate_names("Jordan-Main", ("10.77.10.84", "fd00::1", "10.77.10.84"))
    assert names.common_name == "jordan-main"
    assert names.dns_names == ("jordan-main", "jordan-main.local", "localhost")
    assert names.ip_addresses == ("10.77.10.84", "fd00::1", "127.0.0.1", "::1")
    assert names.all_names == {
        "jordan-main",
        "jordan-main.local",
        "localhost",
        "10.77.10.84",
        "fd00::1",
        "127.0.0.1",
        "::1",
    }


def test_names_refuse_an_empty_hostname_and_a_non_address() -> None:
    with pytest.raises(ValueError, match="hostname"):
        certificate_names("  ", ())
    with pytest.raises(ValueError, match="not-an-ip"):
        certificate_names("h", ("not-an-ip",))


def _decision(
    days: int, *, current: frozenset[str] | None = None, wanted: frozenset[str] | None = None
) -> RenewalDecision:
    names = frozenset({"h", "h.local", "localhost", "127.0.0.1", "::1"})
    return renewal_decision(
        now=NOW,
        not_after=NOW + timedelta(days=days),
        renew_before_days=30,
        current_names=current if current is not None else names,
        wanted_names=wanted if wanted is not None else names,
    )


def test_renews_at_29_days_and_not_at_31() -> None:
    assert _decision(29).renew is True
    assert _decision(29).days_left == 29
    assert _decision(31).renew is False
    assert _decision(31).days_left == 31
    assert _decision(30).renew is False  # exactly the threshold: not fewer than 30


def test_an_expired_leaf_renews_with_a_negative_count() -> None:
    decision = _decision(-3)
    assert decision.renew is True
    assert decision.days_left < 0


def test_a_changed_address_set_renews_even_with_a_year_left() -> None:
    base = frozenset({"h", "h.local", "localhost", "127.0.0.1", "::1"})
    decision = _decision(360, current=base, wanted=base | {"10.0.0.9"})
    assert decision.renew is True
    assert "10.0.0.9" in decision.reason
    assert _decision(360, current=base | {"10.0.0.9"}, wanted=base).renew is True
