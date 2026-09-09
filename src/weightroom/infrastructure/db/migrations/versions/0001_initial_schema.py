"""initial schema: operators, sessions, audit_log, settings, known_revisions

Revision ID: 0001
Revises:
Create Date: 2026-09-09 00:00:00.000000

``known_revisions`` is seeded with the head of each application's migration history as read
from the four repositories on 2026-09-09 (row W1; recorded in ``docs/history/W1_HANDOFF.md``).
A later WeightRoomGym release that learns a newer revision adds a row in its own migration.
"""

from __future__ import annotations

import sqlalchemy as sa
import weightsdb
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

KNOWN_REVISIONS: tuple[tuple[str, str], ...] = (
    ("freeweight", "0009"),
    ("loadcoach", "0015"),
    ("ideapress", "0010"),
    ("promptcadence", "0011"),
)
WEIGHTROOM_VERSION = "0.1.0"


def upgrade() -> None:
    op.create_table(
        "operators",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.LargeBinary(), nullable=False),
        sa.Column("password_salt", sa.LargeBinary(), nullable=False),
        sa.Column("kdf_params", weightsdb.PortableJSON(), nullable=False),
        sa.Column("created_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("password_changed_at", weightsdb.UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operators")),
        sa.UniqueConstraint("username", name=op.f("uq_operators_username")),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("operator_id", sa.String(length=26), nullable=False),
        sa.Column("created_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("last_seen_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("expires_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("reauth_at", weightsdb.UtcDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["operators.id"],
            name=op.f("fk_sessions_operator_id_operators"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("operator_id", sa.String(length=26), nullable=True),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("app", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=True),
        sa.Column("params", weightsdb.PortableJSON(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("backup_path", sa.String(), nullable=True),
        sa.Column("dry_run_count", sa.Integer(), nullable=True),
        sa.Column("actual_count", sa.Integer(), nullable=True),
        sa.Column("statement", sa.String(), nullable=True),
        sa.Column("security", sa.Boolean(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["operator_id"], ["operators.id"], name=op.f("fk_audit_log_operator_id_operators")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index("ix_audit_log_at", "audit_log", ["at"])
    op.create_index("ix_audit_log_app_at", "audit_log", ["app", "at"])
    op.create_index("ix_audit_log_action_at", "audit_log", ["action", "at"])
    op.create_table(
        "settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value_json", weightsdb.PortableJSON(), nullable=True),
        sa.Column("updated_at", weightsdb.UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_settings")),
    )
    known = op.create_table(
        "known_revisions",
        sa.Column("app", sa.String(), nullable=False),
        sa.Column("revision", sa.String(), nullable=False),
        sa.Column("weightroom_version", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("app", "revision", name=op.f("pk_known_revisions")),
    )
    op.bulk_insert(
        known,
        [
            {
                "app": app,
                "revision": rev,
                "weightroom_version": WEIGHTROOM_VERSION,
                "notes": "head on 2026-09-09 (row W1)",
            }
            for app, rev in KNOWN_REVISIONS
        ],
    )


def downgrade() -> None:
    op.drop_table("known_revisions")
    op.drop_table("settings")
    op.drop_index("ix_audit_log_action_at", table_name="audit_log")
    op.drop_index("ix_audit_log_app_at", table_name="audit_log")
    op.drop_index("ix_audit_log_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("operators")
