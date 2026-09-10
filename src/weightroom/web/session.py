"""weightroom.web.session — resolving the caller from the session cookie (ADR-0126 rule 4).

Runs as a route dependency, after every middleware (Host allowlist, rate limiter, CSRF,
same-origin). Where a principal comes from:

1. The ``__Host-weightroom_session`` cookie, resolved against the ``sessions`` table.
2. **Loopback with no account is open** (ADR-0126 rule 6): before ``setup`` has created the
   operator, a loopback bind serves as every application does on loopback, and the principal is
   ``loopback``. The moment an account exists, or the bind is not loopback, a session is required.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import Depends, Request

from weightroom.config import LOOPBACK_HOSTS
from weightroom.services.auth import (
    Principal,
    Unauthorized,
    operator_count,
    reauthenticate,
    resolve_session,
)

if TYPE_CHECKING:
    from fastapi import Response

__all__ = [
    "SESSION_COOKIE_NAME",
    "CurrentOperator",
    "clear_cookie",
    "now_of",
    "reauthenticated",
    "set_cookie",
]

SESSION_COOKIE_NAME: Final = "__Host-weightroom_session"  # noqa: S105 — a cookie *name*
"""``HttpOnly``, ``Secure``, ``SameSite=Strict``, ``Path=/`` (ADR-0126 rule 4)."""


def now_of(request: Request) -> datetime:
    """The request's clock: ``app.state.clock`` when a test set one, else the real one."""
    clock = getattr(request.app.state, "clock", None)
    return clock() if clock is not None else datetime.now(UTC)


def reauthenticated(request: Request, principal: Principal, password: str) -> Principal | None:
    """Open the re-authentication window and return the **restamped** principal, or ``None``.

    The principal this request was resolved with was read before the password arrived, so it
    still carries the old ``reauth_at``; handing it to
    :func:`~weightroom.services.auth.require_fresh_reauth` a moment later would refuse a password
    that had just been accepted. The session row is the store; this is the same row, re-read.
    Moved here from ``web/routes/settings.py`` (row W4) when the guarded write became its second
    caller (row W7).
    """
    now = now_of(request)
    if not reauthenticate(
        request.app.state.database, principal=principal, password=password, now=now
    ):
        return None
    return replace(principal, reauth_at=now)


def set_cookie(response: Response, session_id: str) -> None:
    """Attach the session cookie with the documented flags."""
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )


def clear_cookie(response: Response) -> None:
    """Remove the session cookie."""
    response.delete_cookie(
        SESSION_COOKIE_NAME, path="/", secure=True, httponly=True, samesite="strict"
    )


def _principal(request: Request) -> Principal:
    settings = request.app.state.settings
    database = request.app.state.database
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie:
        principal = resolve_session(
            database, session_id=cookie, now=now_of(request), auth=settings.auth
        )
        if principal is not None:
            request.state.principal = principal
            return principal
    if settings.server.host in LOOPBACK_HOSTS and operator_count(database) == 0:
        principal = Principal(username="loopback", source="loopback")
        request.state.principal = principal
        return principal
    raise Unauthorized("This page needs a login.", details={})


CurrentOperator = Annotated[Principal, Depends(_principal)]
"""Declare as a route parameter to require a live session (or the open loopback install)."""
