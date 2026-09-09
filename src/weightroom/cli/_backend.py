"""weightroom.cli._backend — how a CLI command resolves configuration and opens its database.

Every local-mode command resolves configuration and opens one database handle for the life of
the command before its own work. Both are here once, and both exit ``3`` on a configuration
error (CLI standards §4). The service layer is imported inside the functions, never at module
level, so ``--help`` stays cheap (CLI standards §12).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from weightroom.config import LoadedSettings, Settings
    from weightroom.services.database import Database

__all__ = ["fail", "load_settings_or_exit", "open_database", "open_loaded_database"]


def fail(exc: Exception, *, exit_code: int = 4) -> typer.Exit:
    """Print the standard CLI error line and return the exit signal (CLI standards §4)."""
    code = getattr(exc, "code", "ERROR")
    message = getattr(exc, "message", str(exc))
    typer.echo(f"Error: {message} ({code})", err=True)
    return typer.Exit(exit_code)


def load_settings_or_exit(config: str | None) -> LoadedSettings:
    """Resolve configuration, or exit ``3`` with the refusal on stderr."""
    from weightroom.config import ConfigurationError, load_settings

    try:
        return load_settings(config_path=config)
    except ConfigurationError as exc:
        raise fail(exc, exit_code=3) from exc


@contextmanager
def open_loaded_database(loaded: LoadedSettings) -> Iterator[Database]:
    """Open one database handle for already-resolved configuration, closed on the way out."""
    from weightroom.services.database import Database

    url = loaded.settings.storage.database_url
    if url is None:  # pragma: no cover — StorageSettings always fills this in
        typer.echo("Error: no database_url configured (CONFIGURATION_ERROR)", err=True)
        raise typer.Exit(3)
    with Database.from_url(url) as database:
        yield database


@contextmanager
def open_database(config: str | None) -> Iterator[tuple[Database, Settings]]:
    """Resolve configuration and open one database handle for this command, or exit ``3``."""
    loaded = load_settings_or_exit(config)
    with open_loaded_database(loaded) as database:
        yield database, loaded.settings


@contextmanager
def open_ready_database(config: str | None) -> Iterator[tuple[Database, Settings]]:
    """As :func:`open_database`, with the startup revision check applied (migrate if allowed)."""
    from weightsdb import DatabaseError

    from weightroom.services.database import ensure_ready

    with open_database(config) as (database, settings):
        try:
            ensure_ready(
                database,
                auto_migrate=settings.storage.auto_migrate,
                backup_retention=settings.storage.backup_retention,
            )
        except DatabaseError as exc:
            raise fail(exc) from exc
        yield database, settings
