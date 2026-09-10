"""weightroom.services.apps — what the console knows about each of the four applications.

Three sources, in this order, and the page says which one answered (spec §7.3):

1. **The unit** — ``systemctl --user show``, which says running or not without asking anything
   of the application. This is also what ADR-0124's guard condition 1 will read at W7.
2. **The application's own API** — ``GET /api/v1/version`` for the negotiated version, and
   ``GET /api/v1/health`` proxied verbatim for its own view of itself.
3. **Its configuration** — the executable and base URL WeightRoomGym was told about.

The version check is cached for :data:`~weightroom.domain.apps.RECHECK_SECONDS` per application
(spec §19). Not because the call is expensive — it is a loopback GET — but because *every* page
of an application's tab would otherwise re-ask, and an application that is down would then cost
one connection refusal per page element rather than one per five minutes.

An application that is not installed is **not installed**, never *stopped* (ADR-0125 rule 1):
a missing executable and a stopped process are different facts and lead to different buttons.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import httpx
from baseaicore import SuiteError

from weightroom.config import APPLICATIONS, Settings
from weightroom.domain.apps import RECHECK_SECONDS, SUPPORTED_VERSIONS, version_verdict
from weightroom.domain.units import unit_name
from weightroom.services.processes import (
    SystemdController,
    UnitStatus,
    UnitUnsupported,
    executable_for,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = [
    "AppUnknown",
    "AppView",
    "VersionCache",
    "VersionProbe",
    "app_health",
    "bearer_token",
    "inventory",
    "require_app",
    "unit_statuses",
    "view_for",
]

logger = logging.getLogger(__name__)

_PROBE_TIMEOUT_SECONDS = 3.0

type AppState = Literal[
    "active", "activating", "deactivating", "inactive", "failed", "absent", "unsupported"
]


class AppUnknown(SuiteError):
    """``{app}`` is not one of the four."""

    code: ClassVar[str] = "APP_UNKNOWN"


class AppNotInstalled(SuiteError):
    """The application has no executable, so it has no unit and cannot be started."""

    code: ClassVar[str] = "APP_NOT_INSTALLED"


class AppUnreachable(SuiteError):
    """The application's own API did not answer."""

    code: ClassVar[str] = "APP_UNREACHABLE"


class AppVersionMismatch(SuiteError):
    """The application's version is outside the range this console speaks to (spec §19)."""

    code: ClassVar[str] = "APP_VERSION_MISMATCH"


def require_app(app: str) -> str:
    """Return ``app`` if it is one of the four, else refuse by name.

    Raises:
        AppUnknown: It is not.
    """
    if app not in APPLICATIONS:
        raise AppUnknown(
            f"{app!r} is not one of the four applications.",
            details={"app": app, "known": list(APPLICATIONS)},
        )
    return app


def bearer_token(settings: Settings, app: str) -> str | None:
    """The token the wizard issued for ``app``, read from ``api_key_file`` (ADR-0126 rule 8).

    The **file** is configured, never the value, so the token is never in the configuration, in
    an audit row, or in this process's memory for longer than the request that used it.

    Args:
        settings: The validated settings.
        app: The application.

    Returns:
        The token, or ``None`` when none is configured or the file is unreadable.
    """
    configured = getattr(settings.apps, app).api_key_file
    if not configured:
        return None
    try:
        return Path(configured).read_text(encoding="utf-8").strip() or None
    except OSError as exc:
        logger.warning("apps.token_unreadable", extra={"app": app, "detail": str(exc)})
        return None


@dataclass(frozen=True, slots=True)
class VersionProbe:
    """What ``GET /api/v1/version`` said, and when.

    Attributes:
        version: The application version, or ``None`` when it did not answer.
        api_version: Its API major (``v1``), or ``None``.
        checked_at: The monotonic instant of the probe, for the five-minute recheck.
        error: Why it did not answer, in the client's own words.
    """

    version: str | None
    api_version: str | None
    checked_at: float
    error: str | None = None


class VersionCache:
    """One negotiated version per application, re-probed every five minutes (spec §19).

    Thread-safe: FastAPI runs this application's synchronous routes in a threadpool, so two
    requests for two pages of the same tab can arrive at once.
    """

    __slots__ = ("_entries", "_lock", "_recheck_seconds")

    def __init__(self, *, recheck_seconds: float = RECHECK_SECONDS) -> None:
        """Build an empty cache."""
        self._entries: dict[str, VersionProbe] = {}
        self._lock = threading.Lock()
        self._recheck_seconds = recheck_seconds

    def get(
        self, app: str, *, now: float, probe: Callable[[], VersionProbe], refresh: bool = False
    ) -> VersionProbe:
        """The cached probe, re-running ``probe`` when it is older than the recheck window.

        Args:
            app: The application.
            now: A monotonic clock reading, injected.
            probe: How to ask; called only when the cache is cold or stale.
            refresh: Ignore the cache and ask now — what a start/stop does, so the page that
                follows the action does not show the state from before it.

        Returns:
            The probe.
        """
        with self._lock:
            held = self._entries.get(app)
            fresh = (
                held is not None and not refresh and (now - held.checked_at) < self._recheck_seconds
            )
            if fresh and held is not None:
                return held
        answer = probe()
        with self._lock:
            self._entries[app] = answer
        return answer

    def forget(self, app: str) -> None:
        """Drop ``app``'s entry, so the next read probes."""
        with self._lock:
            self._entries.pop(app, None)


@dataclass(frozen=True, slots=True)
class AppView:
    """One application as ``GET /apps`` reports it (api.md §2).

    Attributes:
        name: The application.
        installed: Whether an executable was resolved.
        executable: That executable, or ``None``.
        unit: ``loadcoach.service``.
        unit_state: The unit's state, or ``unsupported`` on a host without systemd.
        uptime_seconds: How long it has been active, ``None`` when it is not — never ``0``.
        restarts: ``NRestarts``, or ``None``.
        base_url: The application's own API.
        version: What it reported, or ``None``.
        api_version: Its API major, or ``None``.
        verdict: ``ok`` / ``too_old`` / ``too_new`` / ``unreadable`` (spec §19).
        supported_range: The range this console speaks to, for the mismatch message.
        error: Why the API did not answer, when it did not.
    """

    name: str
    installed: bool
    executable: str | None
    unit: str
    unit_state: AppState
    uptime_seconds: float | None
    restarts: int | None
    base_url: str
    version: str | None = None
    api_version: str | None = None
    verdict: str = "unreadable"
    supported_range: str = ""
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def running(self) -> bool:
        """Whether the unit is up."""
        return self.unit_state == "active"

    @property
    def reachable(self) -> bool:
        """Whether the application's own API answered."""
        return self.version is not None

    @property
    def pill(self) -> str:
        """The one word the tab's status pill shows."""
        if self.unit_state == "unsupported":
            return "unsupported"
        if not self.installed:
            return "not installed"
        if self.unit_state == "failed":
            return "failed"
        if not self.running:
            return "stopped"
        if self.verdict not in {"ok", "unreadable"}:
            return "version mismatch"
        return "ok" if self.reachable else "starting"

    def as_json(self) -> dict[str, Any]:
        """The api.md §2 shape."""
        return {
            "name": self.name,
            "installed": self.installed,
            "executable": self.executable,
            "unit": self.unit,
            "unit_state": self.unit_state,
            "state": self.pill,
            "uptime_seconds": self.uptime_seconds,
            "restarts": self.restarts,
            "base_url": self.base_url,
            "version": self.version,
            "api_version": self.api_version,
            "version_verdict": self.verdict,
            "supported_versions": self.supported_range,
            "error": self.error,
            # W7 fills these; they are `null` rather than absent so the shape does not change.
            "db_revision": None,
            "known": None,
        }


def _probe_version(settings: Settings, app: str, *, client: httpx.Client) -> VersionProbe:
    """Ask one application what it is. Never raises: a refusal is an answer."""
    import time

    base_url = getattr(settings.apps, app).base_url
    headers = {}
    token = bearer_token(settings, app)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    now = time.monotonic()
    if not base_url:
        return VersionProbe(None, None, now, error="no base_url configured")
    try:
        response = client.get(
            f"{base_url.rstrip('/')}/api/v1/version",
            headers=headers,
            timeout=_PROBE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return VersionProbe(None, None, now, error=type(exc).__name__ + ": " + str(exc)[:200])
    if not isinstance(body, dict):
        return VersionProbe(None, None, now, error="the version endpoint answered a non-object")
    return VersionProbe(
        version=str(body.get("version")) if body.get("version") else None,
        api_version=str(body.get("api_version")) if body.get("api_version") else None,
        checked_at=now,
    )


def view_for(
    settings: Settings,
    app: str,
    *,
    status: UnitStatus | None,
    cache: VersionCache,
    client: httpx.Client,
    now: float,
    refresh: bool = False,
) -> AppView:
    """Assemble one application's view from the unit, the API and the configuration.

    Args:
        settings: The validated settings.
        app: One of the four.
        status: The unit's state, or ``None`` on a host with no systemd.
        cache: The five-minute version cache.
        client: The HTTP client used for the probe.
        now: A monotonic clock reading.
        refresh: Probe the version now rather than reading the cache.

    Returns:
        The view. Never raises for an application that is down: *stopped* is a state to render,
        not an error.
    """
    executable = executable_for(settings, app)
    unit = unit_name(app)
    unit_state: AppState = "unsupported" if status is None else status.state
    # A stopped application is not an error and carries none: the pill already says *stopped*,
    # and an `error` beside it would put a red sentence next to a state the operator chose.
    probe = (
        VersionProbe(None, None, now)
        if unit_state != "active"
        else cache.get(
            app,
            now=now,
            probe=lambda: _probe_version(settings, app, client=client),
            refresh=refresh,
        )
    )
    supported = SUPPORTED_VERSIONS.get(app)
    return AppView(
        name=app,
        installed=executable is not None,
        executable=executable,
        unit=unit,
        unit_state=unit_state,
        uptime_seconds=None if status is None else status.uptime_seconds,
        restarts=None if status is None else status.restarts,
        base_url=getattr(settings.apps, app).base_url,
        version=probe.version,
        api_version=probe.api_version,
        verdict=version_verdict(app, probe.version) if probe.version else "unreadable",
        supported_range=str(supported) if supported else "",
        error=probe.error,
    )


def unit_statuses(
    controller: SystemdController, apps: Sequence[str]
) -> dict[str, UnitStatus] | None:
    """Every named application's unit state, or ``None`` on a host with no systemd."""
    try:
        return controller.show([unit_name(app) for app in apps])
    except UnitUnsupported:
        return None


def inventory(
    settings: Settings,
    *,
    controller: SystemdController,
    cache: VersionCache,
    client: httpx.Client,
    now: float,
    refresh: str | None = None,
) -> tuple[AppView, ...]:
    """Every application, in configuration order.

    Args:
        settings: The validated settings.
        controller: The systemd boundary.
        cache: The version cache.
        client: The HTTP client.
        now: A monotonic clock reading.
        refresh: One application whose version should be re-probed now — the one just acted on.

    Returns:
        Four views.
    """
    statuses = unit_statuses(controller, APPLICATIONS)
    return tuple(
        view_for(
            settings,
            app,
            status=None if statuses is None else statuses.get(unit_name(app)),
            cache=cache,
            client=client,
            now=now,
            refresh=refresh == app,
        )
        for app in APPLICATIONS
    )


def app_health(
    settings: Settings, app: str, view: AppView, *, client: httpx.Client
) -> dict[str, Any]:
    """The application's own ``/api/v1/health``, proxied verbatim with its source (api.md §2).

    Args:
        settings: The validated settings.
        app: One of the four.
        view: Its view, for the stopped and mismatched cases.
        client: The HTTP client.

    Returns:
        ``{"source": "api", …the application's own body}`` when it answered; otherwise
        ``{"source": "unit", "state": …}`` with the reason. Never the application's shape with
        fields invented for it (spec §11 contract 9).
    """
    if not view.installed:
        return {"source": "config", "state": "not installed", "app": app}
    if not view.running:
        return {"source": "unit", "state": "stopped", "app": app, "unit_state": view.unit_state}
    headers = {}
    token = bearer_token(settings, app)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = client.get(
            f"{view.base_url.rstrip('/')}/api/v1/health",
            headers=headers,
            timeout=_PROBE_TIMEOUT_SECONDS,
        )
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppUnreachable(
            f"{app} is running but its API did not answer: {exc}",
            details={"app": app, "base_url": view.base_url},
        ) from exc
    if not isinstance(body, dict):
        raise AppUnreachable(
            f"{app}'s health endpoint answered a non-object.",
            details={"app": app, "base_url": view.base_url},
        )
    return {"source": "api", **body}
