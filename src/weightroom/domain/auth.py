"""weightroom.domain.auth — password hashing and the session-expiry decisions (ADR-0126 rule 4).

Pure: ``hashlib.scrypt`` from the standard library, ``secrets`` for ids, ``hmac.compare_digest``
for every comparison, and datetimes in and out. No database, no request, no clock of its own —
:mod:`weightroom.services.auth` supplies those.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final, Literal

__all__ = [
    "KDF_PARAMS",
    "MIN_PASSWORD_LENGTH",
    "PasswordRecord",
    "SessionState",
    "hash_password",
    "needs_rehash",
    "new_session_id",
    "reauth_is_fresh",
    "session_expiry",
    "session_state",
    "verify_password",
]

KDF_PARAMS: Final[dict[str, int]] = {"n": 2**15, "r": 8, "p": 1}
"""ADR-0126 rule 4's scrypt parameters, stored beside every hash so they can rise later."""

MIN_PASSWORD_LENGTH: Final = 8
"""A floor, not a policy: one operator chooses their own password; eight is the sanity check."""

_HASH_LENGTH: Final = 32
_SALT_LENGTH: Final = 16


def _maxmem(params: dict[str, int]) -> int:
    """scrypt's working set is ``128 * n * r`` bytes; OpenSSL's default cap is exactly 32 MiB.

    ``n = 2**15, r = 8`` is 32 MiB, which trips the default cap, so the cap is raised to twice the
    parameters' need — never unbounded, so a hostile stored ``kdf_params`` cannot ask for the
    whole machine.
    """
    return 2 * 128 * int(params["n"]) * int(params["r"]) * max(int(params["p"]), 1)


type SessionState = Literal["active", "idle_expired", "absolute_expired"]


@dataclass(frozen=True, slots=True)
class PasswordRecord:
    """What ``operators`` stores for a password: the hash, its salt and the parameters used."""

    password_hash: bytes
    password_salt: bytes
    kdf_params: dict[str, int]


def hash_password(
    password: str, *, salt: bytes | None = None, params: dict[str, int] | None = None
) -> PasswordRecord:
    """Hash ``password`` with scrypt.

    Args:
        password: The plaintext, at least :data:`MIN_PASSWORD_LENGTH` characters.
        salt: 16 random bytes; generated when ``None``.
        params: ``n``, ``r``, ``p``; :data:`KDF_PARAMS` when ``None``.

    Returns:
        The record to store.

    Raises:
        ValueError: The password is shorter than the floor.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        message = f"a password needs at least {MIN_PASSWORD_LENGTH} characters"
        raise ValueError(message)
    chosen_salt = salt if salt is not None else secrets.token_bytes(_SALT_LENGTH)
    chosen = dict(params or KDF_PARAMS)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=chosen_salt,
        n=chosen["n"],
        r=chosen["r"],
        p=chosen["p"],
        maxmem=_maxmem(chosen),
        dklen=_HASH_LENGTH,
    )
    return PasswordRecord(password_hash=digest, password_salt=chosen_salt, kdf_params=chosen)


def verify_password(password: str, record: PasswordRecord) -> bool:
    """Whether ``password`` matches ``record``, compared in constant time.

    A password below the floor is hashed and compared anyway, so the timing of a refusal does not
    say which rule refused it.
    """
    params = record.kdf_params
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=record.password_salt,
        n=int(params["n"]),
        r=int(params["r"]),
        p=int(params["p"]),
        maxmem=_maxmem(params),
        dklen=len(record.password_hash) or _HASH_LENGTH,
    )
    return hmac.compare_digest(digest, record.password_hash)


def needs_rehash(record: PasswordRecord) -> bool:
    """Whether the stored parameters are below :data:`KDF_PARAMS` (a login re-hashes then)."""
    return any(int(record.kdf_params.get(key, 0)) < value for key, value in KDF_PARAMS.items())


def new_session_id() -> str:
    """32 random bytes, base64url (data model §2): regenerated on every login."""
    return secrets.token_urlsafe(32)


def session_expiry(
    *, created_at: datetime, last_seen_at: datetime, idle_hours: int, max_days: int
) -> datetime:
    """When a session ends: the sooner of idle-from-last-seen and absolute-from-creation."""
    return min(last_seen_at + timedelta(hours=idle_hours), created_at + timedelta(days=max_days))


def session_state(
    *, now: datetime, created_at: datetime, last_seen_at: datetime, idle_hours: int, max_days: int
) -> SessionState:
    """Classify a session at ``now``: active, idle-expired, or past its absolute lifetime."""
    if now >= created_at + timedelta(days=max_days):
        return "absolute_expired"
    if now >= last_seen_at + timedelta(hours=idle_hours):
        return "idle_expired"
    return "active"


def reauth_is_fresh(*, now: datetime, reauth_at: datetime | None, window_minutes: int) -> bool:
    """Whether a ``POST /reauth`` at ``reauth_at`` still authorises a security action at ``now``."""
    if reauth_at is None:
        return False
    return now < reauth_at + timedelta(minutes=window_minutes)
