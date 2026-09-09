"""weightroom.services.runtime — what every serving process checks before it opens a socket.

``wr-gym serve`` and the ASGI factories in :mod:`weightroom.bootstrap` all call
:func:`prepare`, so the startup refusals (ADR-0126 rule 6), the migration check and the
certificate renewal happen once, in one place, whichever entry point started the process. It
lives in ``services`` because the CLI may not import ``web`` (``.importlinter``) and both need it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from weightroom.config import LOOPBACK_HOSTS, InsecureBindingError, LoadedSettings
from weightroom.infrastructure.db.models import Operator
from weightroom.services.database import Database, ensure_ready
from weightroom.services.tls import HostIdentity, TlsPaths, TlsStatus, ensure_tls, host_identity

if TYPE_CHECKING:
    from weightroom.config import Settings

__all__ = ["PreparedRuntime", "has_operator", "prepare"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedRuntime:
    """What :func:`prepare` established: the certificate to serve and whether a login exists."""

    loaded: LoadedSettings
    tls: TlsStatus
    identity: HostIdentity
    has_operator: bool

    @property
    def settings(self) -> Settings:
        """The validated settings."""
        return self.loaded.settings


def has_operator(database: Database) -> bool:
    """Whether the operator account exists (ADR-0126 rule 6's third member)."""
    with database.read() as session:
        count = session.execute(select(func.count()).select_from(Operator)).scalar_one()
    return count > 0


def prepare(
    loaded: LoadedSettings,
    *,
    now: datetime | None = None,
    identity: HostIdentity | None = None,
) -> PreparedRuntime:
    """Ready the database and the certificate, and apply the bind refusals.

    Args:
        loaded: The resolved settings.
        now: The clock, injected for tests.
        identity: The host's names and addresses, injected for tests.

    Returns:
        The prepared runtime.

    Raises:
        InsecureBindingError: A non-loopback bind without a complete ``tls/`` directory or
            without an operator account (ADR-0126 rule 6; the other two rules raised in
            :func:`~weightroom.config.load_settings`).
        TlsMissingError: The directory is present but incomplete or inconsistent, on any bind.
        MigrationRequired, SchemaAhead, DatabaseUnavailable: As :func:`ensure_ready`.
    """
    settings = loaded.settings
    instant = now or datetime.now(UTC)
    who = identity or host_identity()
    loopback = settings.server.host in LOOPBACK_HOSTS
    database_url = settings.storage.database_url
    if database_url is None:  # pragma: no cover — StorageSettings always fills this in
        message = "no database_url configured"
        raise RuntimeError(message)
    with Database.from_url(database_url) as database:
        ensure_ready(
            database,
            auto_migrate=settings.storage.auto_migrate,
            backup_retention=settings.storage.backup_retention,
        )
        account = has_operator(database)
    paths = TlsPaths.for_settings(settings)
    if not loopback and not paths.present():
        raise InsecureBindingError(
            f"server.host is {settings.server.host!r} but {paths.directory} holds no certificate "
            "authority. A non-loopback bind needs TLS: run `wr-gym setup` (or `wr-gym tls init`).",
            details={"field": "tls.directory", "host": settings.server.host},
        )
    if not loopback and not account:
        raise InsecureBindingError(
            f"server.host is {settings.server.host!r} but no operator account exists. A "
            "non-loopback bind needs a login: run `wr-gym setup` (or `wr-gym operator create`).",
            details={"field": "server.host", "host": settings.server.host},
        )
    tls = ensure_tls(settings, identity=who, now=instant, initialise=loopback)
    if not account:
        logger.warning(
            "auth.open_loopback",
            extra={"detail": "no operator account: the console is open on loopback (ADR-0126)"},
        )
    return PreparedRuntime(loaded=loaded, tls=tls, identity=who, has_operator=account)
