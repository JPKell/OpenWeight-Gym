"""weightroom.web.limits — body cap, same-origin on JSON writes, the rate limiter and login brake.

**Oversize body rejected before buffering** (Security Standards §14): a declared
``Content-Length`` over ``[server] max_body_bytes`` is ``413`` before a byte is read; a chunked
body is counted as it streams and cut at the cap.

**A cross-origin JSON write is refused** (ADR-0126 rule 5). ADR-0026's JSON exemption argued
from bearer tokens a browser cannot attach; a cookie it can. So a state-changing request with
``Content-Type: application/json`` needs ``Sec-Fetch-Site: same-origin`` (or ``none`` — a typed
address), and an ``Origin``, when present, whose host is the one the request was sent to. A
JSON write with no ``Sec-Fetch-Site`` at all is refused too: every browser that sends the cookie
sends the header, and a script without the cookie is not what this check is for.

**The rate limiter** is a token bucket per address on ``/api/v1`` (``/api/v1/version`` exempt).
**The login brake** counts every ``POST /login`` and ``POST /reauth`` per address against
``failed_login_per_minute`` (ADR-0126 rule 4) — attempts, not failures, so a guesser cannot
learn which attempts counted. Both answer ``429 RATE_LIMITED`` with ``Retry-After``.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from baseaicore import new_id
from mirrorwall import error_body
from mirrorwall.middleware import split_host
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = [
    "LOGIN_PATHS",
    "BodySizeLimitMiddleware",
    "RateLimitMiddleware",
    "SameOriginMiddleware",
    "TokenBucket",
]

logger = logging.getLogger(__name__)

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_API_PREFIX = "/api/v1"
_EXEMPT_PATHS = frozenset({"/api/v1/version"})
LOGIN_PATHS = frozenset({"/login", "/api/v1/login", "/reauth", "/api/v1/reauth"})
"""The paths the login brake counts."""


async def _reject(
    scope: Scope,
    receive: Receive,
    send: Send,
    *,
    status: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> None:
    request_id = scope.get("state", {}).get("request_id") or new_id()
    response = JSONResponse(
        status_code=status,
        content=error_body(code=code, message=message, request_id=request_id),
        headers={"X-Request-ID": request_id, "Cache-Control": "no-store", **(headers or {})},
    )
    await response(scope, receive, send)


class BodySizeLimitMiddleware:
    """Refuse a body over ``max_bytes`` — by its declared length first, else while it arrives."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        """Wrap ``app``."""
        self.app = app
        self._max = max(int(max_bytes), 1)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """413 before buffering when the body is, or declares itself, too large."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > self._max:
            logger.warning("request.body_too_large", extra={"declared": int(declared)})
            await _reject(
                scope,
                receive,
                send,
                status=413,
                code="PAYLOAD_TOO_LARGE",
                message=f"The request body is {declared} bytes; the limit is {self._max}.",
            )
            return
        chunks: list[bytes] = []
        seen = 0
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            seen += len(body)
            if seen > self._max:
                logger.warning("request.body_too_large", extra={"streamed": seen})
                await _reject(
                    scope,
                    receive,
                    send,
                    status=413,
                    code="PAYLOAD_TOO_LARGE",
                    message=f"The request body exceeded {self._max} bytes.",
                )
                return
            chunks.append(body)
            more = bool(message.get("more_body", False))
        buffered = b"".join(chunks)
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": buffered, "more_body": False}

        await self.app(scope, replay, send)


class SameOriginMiddleware:
    """ADR-0126 rule 5 for JSON writes; ADR-0026 §2's ``Origin`` check for every other write."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ``app``."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """403 ``CSRF_FAILED`` for a cross-site write; everything else passes through."""
        if scope["type"] != "http" or scope["method"] not in _UNSAFE_METHODS:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        host = split_host(headers.get("host", ""))
        origin = headers.get("origin")
        origin_host = (
            (urlsplit(origin).hostname or "").lower() if origin and origin != "null" else ""
        )
        if origin is not None and origin_host != host:
            await self._refuse(scope, receive, send, "the Origin header names another host")
            return
        content_type = headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type == "application/json":
            site = headers.get("sec-fetch-site", "").lower()
            if site not in ("same-origin", "none"):
                await self._refuse(
                    scope, receive, send, "a JSON write needs Sec-Fetch-Site: same-origin"
                )
                return
        await self.app(scope, receive, send)

    async def _refuse(self, scope: Scope, receive: Receive, send: Send, why: str) -> None:
        logger.warning("request.cross_origin_refused", extra={"why": why})
        await _reject(
            scope,
            receive,
            send,
            status=403,
            code="CSRF_FAILED",
            message=f"Cross-site writes are not accepted: {why} (ADR-0126 rule 5).",
        )


@dataclass
class TokenBucket:
    """One address's budget: ``capacity`` at rest, refilled at ``per_second``."""

    capacity: float
    per_second: float
    tokens: float
    updated_at: float

    def take(self, now: float) -> float:
        """Take one request's worth: ``0.0`` when admitted, else seconds until it would be."""
        elapsed = max(now - self.updated_at, 0.0)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.per_second)
        self.updated_at = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return 0.0
        return (1.0 - self.tokens) / self.per_second if self.per_second > 0 else math.inf


class RateLimitMiddleware:
    """The per-address API bucket and the login brake (spec §12, ADR-0126 rule 4)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        per_minute: int,
        burst: int,
        login_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Wrap ``app``. ``0`` disables either limit."""
        self.app = app
        self._per_minute = max(per_minute, 0)
        self._burst = max(burst, 1)
        self._login_per_minute = max(login_per_minute, 0)
        self._clock = clock
        self._buckets: dict[str, TokenBucket] = {}
        self._logins: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def _bucket(self, table: dict[str, TokenBucket], key: str, *, capacity: int) -> TokenBucket:
        bucket = table.get(key)
        if bucket is None:
            bucket = TokenBucket(
                capacity=float(capacity),
                per_second=capacity / 60.0 if table is self._logins else self._per_minute / 60.0,
                tokens=float(capacity),
                updated_at=self._clock(),
            )
            table[key] = bucket
            if len(table) > 10_000:  # a stranger cycling addresses cannot grow this unbounded
                table.pop(next(iter(table)))
        return bucket

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Admit, or answer 429 with ``Retry-After``."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        client = scope.get("client")
        address = client[0] if client else "unknown"
        now = self._clock()
        with self._lock:
            if self._login_per_minute and path in LOGIN_PATHS and scope["method"] == "POST":
                wait = self._bucket(self._logins, address, capacity=self._login_per_minute).take(
                    now
                )
                if wait > 0.0:
                    logger.warning("auth.login_rate_limited", extra={"client": address})
                    await self._reject(scope, receive, send, wait, "too many login attempts")
                    return
            elif self._per_minute and path.startswith(_API_PREFIX) and path not in _EXEMPT_PATHS:
                wait = self._bucket(self._buckets, address, capacity=self._burst).take(now)
                if wait > 0.0:
                    await self._reject(scope, receive, send, wait, "rate limit reached")
                    return
        await self.app(scope, receive, send)

    async def _reject(
        self, scope: Scope, receive: Receive, send: Send, wait: float, reason: str
    ) -> None:
        retry_after = max(1, math.ceil(wait if math.isfinite(wait) else 60.0))
        await _reject(
            scope,
            receive,
            send,
            status=429,
            code="RATE_LIMITED",
            message=f"{reason}; retry after {retry_after} s.",
            headers={"Retry-After": str(retry_after)},
        )
