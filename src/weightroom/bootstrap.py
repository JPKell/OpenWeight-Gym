"""weightroom.bootstrap — the composition root: settings, logging, the two ASGI apps, wired once.

Outside the ``web``/``cli``/``services``/``domain`` ordering ``.importlinter`` enforces, so it
can import both configuration and the web layer. ``weightroom.cli`` never imports it: the
``serve`` command hands uvicorn the dotted strings ``…:create_app_from_environment`` and
``…:create_trust_app_from_environment`` and lets uvicorn import them —
a string literal is invisible to import-linter, so the two surfaces stay decoupled at source
level while running in one process (the LoadCoach precedent).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI
from starlette.applications import Starlette

from weightroom.config import LoadedSettings, load_settings
from weightroom.observability.logging import configure_logging
from weightroom.services.runtime import PreparedRuntime, prepare
from weightroom.services.tls import HostIdentity
from weightroom.web.app import create_app
from weightroom.web.trust_app import create_trust_app

__all__ = [
    "Application",
    "bootstrap",
    "create_app_from_environment",
    "create_trust_app_from_environment",
]


@dataclass(frozen=True, slots=True)
class Application:
    """A fully wired console: the runtime it was prepared from and its two ASGI apps."""

    runtime: PreparedRuntime
    app: FastAPI
    trust_app: Starlette

    @property
    def loaded_settings(self) -> LoadedSettings:
        """The settings the console was built from."""
        return self.runtime.loaded


def bootstrap(*, now: datetime | None = None, identity: HostIdentity | None = None) -> Application:
    """Load configuration, configure logging, prepare the runtime, build both apps.

    Reads configuration through the standard precedence chain with no CLI layer of its own — a
    caller with CLI overrides applies them as environment variables first, which is what
    ``wr-gym serve`` does.

    Raises:
        ConfigurationError: Configuration is invalid, or an unsafe bind combination is
            configured (:class:`~weightroom.config.InsecureBindingError`,
            :class:`~weightroom.config.TlsMissingError`).
        DatabaseError: The database cannot be readied (see ``services.runtime.prepare``).
    """
    loaded = load_settings()
    configure_logging(
        level=loaded.settings.logging.level, log_format=loaded.settings.logging.format
    )
    runtime = prepare(loaded, now=now, identity=identity)
    return Application(
        runtime=runtime,
        app=create_app(
            loaded.settings,
            tls=runtime.tls,
            identity=runtime.identity,
            config_path=loaded.config_path,
        ),
        trust_app=create_trust_app(loaded.settings, tls=runtime.tls, identity=runtime.identity),
    )


def create_app_from_environment() -> FastAPI:
    """Zero-argument ASGI factory for the HTTPS console: the target uvicorn imports by name."""
    return bootstrap().app


def create_trust_app_from_environment() -> Starlette:
    """Zero-argument ASGI factory for the plain-HTTP trust listener (ADR-0126 rule 3)."""
    return bootstrap().trust_app
