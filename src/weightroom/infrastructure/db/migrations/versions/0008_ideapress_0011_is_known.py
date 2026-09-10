"""ideapress 0011 is a known revision

Row W9: IdeaPress's migration ``0011`` adds ``attempts.prompt_source`` — prompt standards §6's
marking on every attempt that rendered an operator override, the overrides this console's prompt
editor writes. The guard refuses a revision ``known_revisions`` does not list before it reads a
table (ADR-0123 rule 3), so this build learns it here, the way migration ``0005`` learned
FreeWeight's ``0010``. ``0010`` stays known: an installation that has not upgraded IdeaPress is
still one this build reads.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-10 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
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
                "app": "ideapress",
                "revision": "0011",
                "weightroom_version": "0.7.0",
                "notes": "attempts.prompt_source (row W9, prompt standards §6)",
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        _known_revisions.delete().where(
            (_known_revisions.c.app == "ideapress") & (_known_revisions.c.revision == "0011")
        )
    )
