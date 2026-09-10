"""weightroom.services.auth — the operator account and the session table (ADR-0126 rule 4).

One account; scrypt from :mod:`weightroom.domain.auth`; a server-side session row per login,
its id regenerated every time (no fixation); idle and absolute expiry decided by the domain;
``operator password`` and ``tls rotate`` revoke every session. Every function takes ``now``
so a test can move the clock rather than wait.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Literal

from baseaicore import SuiteError, new_id
from sqlalchemy import delete, func, select

from weightroom.domain.auth import (
    PasswordRecord,
    hash_password,
    needs_rehash,
    new_session_id,
    reauth_is_fresh,
    session_expiry,
    session_state,
    verify_password,
)
from weightroom.infrastructure.db.models import Operator, Session

if TYPE_CHECKING:
    from weightroom.config import AuthSettings
    from weightroom.services.database import Database

__all__ = [
    "OperatorExists",
    "OperatorNotFound",
    "Principal",
    "ReauthRequired",
    "Unauthorized",
    "authenticate",
    "change_password",
    "close_session",
    "create_operator",
    "open_session",
    "operator_count",
    "reauthenticate",
    "require_fresh_reauth",
    "resolve_session",
    "revoke_all_sessions",
    "sweep_expired_sessions",
]


class Unauthorized(SuiteError):
    """A session-authenticated route was called with no live session."""

    code: ClassVar[str] = "UNAUTHORIZED"


class ReauthRequired(SuiteError):
    """A security action was attempted outside the re-authentication window (ADR-0127 rule 6)."""

    code: ClassVar[str] = "REAUTH_REQUIRED"


class OperatorExists(SuiteError):
    """``operator create`` when the one account already exists (ADR-0126 rule 7)."""

    code: ClassVar[str] = "VALIDATION_ERROR"


class OperatorNotFound(SuiteError):
    """``operator password`` for a username that does not exist."""

    code: ClassVar[str] = "NOT_FOUND"


@dataclass(frozen=True, slots=True)
class Principal:
    """Who is calling: the operator behind a session, or the open loopback install."""

    username: str
    source: Literal["session", "loopback"]
    operator_id: str | None = None
    session_id: str | None = None
    reauth_at: datetime | None = None


def operator_count(database: Database) -> int:
    """How many operator rows exist (one, or none before ``setup``)."""
    with database.read() as session:
        return int(session.execute(select(func.count()).select_from(Operator)).scalar_one())


def create_operator(database: Database, *, username: str, password: str, now: datetime) -> str:
    """Create the operator account.

    Args:
        database: The database handle.
        username: Non-empty, stripped.
        password: At least the domain's floor.
        now: The creation instant.

    Returns:
        The operator's id.

    Raises:
        OperatorExists: An account already exists (one in 1.0).
        ValueError: The username is empty or the password is below the floor.
    """
    name = username.strip()
    if not name:
        message = "a username is required"
        raise ValueError(message)
    record = hash_password(password)
    if operator_count(database):
        raise OperatorExists(
            "An operator account already exists; 1.0 has one (ADR-0126 rule 7). Use "
            "`wr-gym operator password` to reset its password.",
            details={},
        )
    operator_id = new_id()
    with database.write() as session:
        session.add(
            Operator(
                id=operator_id,
                username=name,
                password_hash=record.password_hash,
                password_salt=record.password_salt,
                kdf_params=record.kdf_params,
                created_at=now,
                password_changed_at=now,
            )
        )
    return operator_id


def change_password(database: Database, *, username: str, password: str, now: datetime) -> int:
    """Reset the password from a shell and revoke every session (ADR-0126 rule 4).

    Returns:
        The number of sessions revoked.

    Raises:
        OperatorNotFound: No such username.
        ValueError: The password is below the floor.
    """
    record = hash_password(password)
    with database.write() as session:
        operator = session.execute(
            select(Operator).where(Operator.username == username.strip())
        ).scalar_one_or_none()
        if operator is None:
            raise OperatorNotFound(f"No operator {username!r}.", details={"username": username})
        operator.password_hash = record.password_hash
        operator.password_salt = record.password_salt
        operator.kdf_params = record.kdf_params
        operator.password_changed_at = now
    return revoke_all_sessions(database)


def _record_of(operator: Operator) -> PasswordRecord:
    params = operator.kdf_params
    assert isinstance(params, dict)  # noqa: S101 — PortableJSON round-trips the dict we wrote
    return PasswordRecord(
        password_hash=bytes(operator.password_hash),
        password_salt=bytes(operator.password_salt),
        kdf_params={str(k): int(v) for k, v in params.items()},
    )


def authenticate(database: Database, *, username: str, password: str, now: datetime) -> str | None:
    """Check a username and password; return the operator id, or ``None``.

    Constant-time on the hash. A record hashed under older parameters is re-hashed on success
    (data model §2). An unknown username still costs one scrypt, so its timing says nothing.
    """
    with database.write() as session:
        operator = session.execute(
            select(Operator).where(Operator.username == username.strip())
        ).scalar_one_or_none()
        if operator is None:
            hash_password("x" * 8, salt=b"\0" * 16)  # burn the same time as a real check
            return None
        record = _record_of(operator)
        if not verify_password(password, record):
            return None
        if needs_rehash(record):
            fresh = hash_password(password)
            operator.password_hash = fresh.password_hash
            operator.password_salt = fresh.password_salt
            operator.kdf_params = fresh.kdf_params
            operator.password_changed_at = now
        return operator.id


def open_session(
    database: Database, *, operator_id: str, address: str, now: datetime, auth: AuthSettings
) -> str:
    """Issue a fresh session for ``operator_id`` and sweep expired rows on the way.

    Returns:
        The new session id — the cookie value. Never reused: a login always mints one.
    """
    sweep_expired_sessions(database, now=now)
    session_id = new_session_id()
    with database.write() as session:
        session.add(
            Session(
                id=session_id,
                operator_id=operator_id,
                created_at=now,
                last_seen_at=now,
                expires_at=session_expiry(
                    created_at=now,
                    last_seen_at=now,
                    idle_hours=auth.session_idle_hours,
                    max_days=auth.session_max_days,
                ),
                address=address,
            )
        )
    return session_id


_TOUCH_INTERVAL_SECONDS = 60


def resolve_session(
    database: Database, *, session_id: str, now: datetime, auth: AuthSettings
) -> Principal | None:
    """The principal behind a cookie value, or ``None`` when it is unknown or expired.

    An expired row is deleted here. A live one has ``last_seen_at`` moved forward — at most
    once a minute, so a page of islands does not write a row per request.
    """
    with database.write() as session:
        row = session.get(Session, session_id)
        if row is None:
            return None
        state = session_state(
            now=now,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            idle_hours=auth.session_idle_hours,
            max_days=auth.session_max_days,
        )
        if state != "active":
            session.delete(row)
            return None
        if (now - row.last_seen_at).total_seconds() >= _TOUCH_INTERVAL_SECONDS:
            row.last_seen_at = now
            row.expires_at = session_expiry(
                created_at=row.created_at,
                last_seen_at=now,
                idle_hours=auth.session_idle_hours,
                max_days=auth.session_max_days,
            )
        operator = session.get(Operator, row.operator_id)
        username = operator.username if operator is not None else "?"
        return Principal(
            username=username,
            source="session",
            operator_id=row.operator_id,
            session_id=row.id,
            reauth_at=row.reauth_at,
        )


def close_session(database: Database, *, session_id: str) -> bool:
    """Delete one session row (logout). Returns whether it existed."""
    with database.write() as session:
        result = session.execute(delete(Session).where(Session.id == session_id))
        return int(getattr(result, "rowcount", 0)) > 0


def revoke_all_sessions(database: Database) -> int:
    """Delete every session row; returns the count (``operator password``, ``tls rotate``)."""
    with database.write() as session:
        return int(getattr(session.execute(delete(Session)), "rowcount", 0))


def sweep_expired_sessions(database: Database, *, now: datetime) -> int:
    """Delete rows past ``expires_at`` (data model §3); returns the count."""
    with database.write() as session:
        result = session.execute(delete(Session).where(Session.expires_at <= now))
        return int(getattr(result, "rowcount", 0))


def reauthenticate(
    database: Database, *, principal: Principal, password: str, now: datetime
) -> bool:
    """``POST /reauth``: check the password again and stamp the session (ADR-0127 rule 6).

    Returns:
        Whether the password was right; the session's ``reauth_at`` is set only then.
    """
    if principal.session_id is None or principal.operator_id is None:
        return False
    if authenticate(database, username=principal.username, password=password, now=now) is None:
        return False
    with database.write() as session:
        row = session.get(Session, principal.session_id)
        if row is not None:
            row.reauth_at = now
    return True


def require_fresh_reauth(principal: Principal, *, now: datetime, auth: AuthSettings) -> None:
    """Refuse a security action outside the window; the open loopback install is exempt.

    Raises:
        ReauthRequired: The session has not re-authenticated within ``reauth_window_minutes``.
    """
    if principal.source == "loopback":
        return
    if not reauth_is_fresh(
        now=now, reauth_at=principal.reauth_at, window_minutes=auth.reauth_window_minutes
    ):
        raise ReauthRequired(
            f"This action needs the password again (POST /reauth) within the last "
            f"{auth.reauth_window_minutes} minutes.",
            details={"window_minutes": auth.reauth_window_minutes},
        )
