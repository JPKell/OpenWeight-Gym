"""freeweight 0010 is a known revision

Row WA1: FreeWeight's migration ``0010`` adds ``runtime_profiles.adapters_registered``
(ADR-0135). The guard refuses a revision ``known_revisions`` does not list before it reads a table
(ADR-0123 rule 3), so this build learns it here — the way migration ``0001`` says a later revision
is learned. ``0009`` stays known: an installation that has not upgraded FreeWeight is still one this
build reads.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-10 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_known_revisions = sa.table(
    "known_revisions",
    sa.column("app", sa.String()),
    sa.column("revision", sa.String()),
    sa.column("weightroom_version", sa.String()),
    sa.column("notes", sa.String()),
)


def upgrade() -> None:
    op.bulk_insert(
        _known_revisions,
        [
            {
                "app": "freeweight",
                "revision": "0010",
                "weightroom_version": "0.7.0",
                "notes": "runtime_profiles.adapters_registered (row WA1, ADR-0135)",
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        _known_revisions.delete().where(
            (_known_revisions.c.app == "freeweight") & (_known_revisions.c.revision == "0010")
        )
    )
