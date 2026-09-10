"""weightroom.domain.auth: scrypt, constant-time verify, rehash, the expiry decisions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from weightroom.domain.auth import (
    KDF_PARAMS,
    hash_password,
    needs_rehash,
    new_session_id,
    reauth_is_fresh,
    session_expiry,
    session_state,
    verify_password,
)

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


def test_hash_uses_the_adr_parameters_a_fresh_salt_and_verifies() -> None:
    record = hash_password("correct horse battery")
    assert record.kdf_params == {"n": 2**15, "r": 8, "p": 1} == KDF_PARAMS
    assert len(record.password_salt) == 16 and len(record.password_hash) == 32
    assert verify_password("correct horse battery", record)
    assert not verify_password("correct horse batterx", record)
    assert hash_password("correct horse battery").password_salt != record.password_salt


def test_short_passwords_are_refused_at_hash_time_but_still_compared_at_verify_time() -> None:
    with pytest.raises(ValueError, match="8 characters"):
        hash_password("short")
    record = hash_password("long enough")
    assert verify_password("short", record) is False


def test_old_parameters_need_a_rehash() -> None:
    weak = hash_password("long enough", params={"n": 2**14, "r": 8, "p": 1})
    assert needs_rehash(weak) is True
    assert needs_rehash(hash_password("long enough")) is False


def test_session_ids_are_long_random_and_never_repeat() -> None:
    ids = {new_session_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(len(value) >= 40 for value in ids)


def test_expiry_is_the_sooner_of_idle_and_absolute() -> None:
    created = NOW
    assert session_expiry(
        created_at=created, last_seen_at=created, idle_hours=12, max_days=7
    ) == created + timedelta(hours=12)
    late = created + timedelta(days=6, hours=20)
    assert session_expiry(
        created_at=created, last_seen_at=late, idle_hours=12, max_days=7
    ) == created + timedelta(days=7)


def test_state_names_which_rule_ended_the_session() -> None:
    def state(now: datetime, seen: datetime) -> str:
        return session_state(now=now, created_at=NOW, last_seen_at=seen, idle_hours=12, max_days=7)

    assert state(NOW + timedelta(hours=1), NOW) == "active"
    assert state(NOW + timedelta(hours=12), NOW) == "idle_expired"
    assert state(NOW + timedelta(days=7), NOW + timedelta(days=6, hours=23)) == "absolute_expired"


def test_reauth_window() -> None:
    assert reauth_is_fresh(now=NOW, reauth_at=None, window_minutes=5) is False
    assert reauth_is_fresh(now=NOW + timedelta(minutes=4), reauth_at=NOW, window_minutes=5)
    assert not reauth_is_fresh(now=NOW + timedelta(minutes=5), reauth_at=NOW, window_minutes=5)
