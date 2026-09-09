"""Alembic environment for WeightRoomGym's own migration history.

Always run through :class:`weightsdb.MigrationRunner`, never through the bare ``alembic`` CLI:
``config.attributes["connection"]`` is populated by the runner with an already-open connection
from the application's own dialect-configured engine, so this module never builds an engine from
a URL and never runs in Alembic's offline mode.
"""

from __future__ import annotations

from alembic import context

from weightroom.infrastructure.db.models import Base

config = context.config
target_metadata = Base.metadata


def _set_foreign_keys(connection: object, *, on: bool) -> None:
    """Set SQLite's ``foreign_keys`` pragma on this connection, outside any transaction.

    Through the raw DBAPI cursor deliberately: WeightsDB emits ``BEGIN IMMEDIATE`` from
    SQLAlchemy's ``begin`` event, and ``PRAGMA foreign_keys`` inside a transaction is a documented
    no-op — the silent kind (the LoadCoach precedent, row H2).
    """
    raw = connection.connection  # type: ignore[attr-defined]  # alembic hands a Connection
    cursor = raw.cursor()
    try:
        cursor.execute(f"PRAGMA foreign_keys={'ON' if on else 'OFF'}")
    finally:
        cursor.close()


def run_migrations_online() -> None:
    """Run migrations against the connection the caller placed in ``config.attributes``.

    Foreign keys are off for the duration on SQLite so a batch-mode table rebuild never cascades
    a delete into ``audit_log`` — the one table that must survive everything (data model §2).
    """
    connection = config.attributes["connection"]
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        _set_foreign_keys(connection, on=False)
    version_table = config.attributes.get("version_table", "alembic_version")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=version_table,
        render_as_batch=sqlite,
    )
    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        if sqlite:
            _set_foreign_keys(connection, on=True)


run_migrations_online()
