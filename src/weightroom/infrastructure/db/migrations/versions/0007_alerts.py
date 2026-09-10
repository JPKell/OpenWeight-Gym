"""alerts

The alert episodes and their history (data model §2, spec §7.10, ADR-0137, row W9): ``alerts``, with
a partial unique index holding "at most one active alert per ``(source, subject)``" in the
database itself, and ``alert_history``.

Additive only. ``downgrade`` drops both, which loses the history the data model keeps for ever — a
downgrade is a restore, not a routine operation.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-10 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import weightsdb
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ACTIVE = sa.text("closed_at IS NULL")


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("opened_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("last_seen_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("acknowledged_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.String(), nullable=True),
        sa.Column("cleared_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("closed_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("detail", weightsdb.PortableJSON(), nullable=False),
        sa.CheckConstraint(
            "source IN ('app_down', 'memory_cap', 'gpu_thermal', 'budget_ceiling', 'breaker_open')",
            name=op.f("ck_alerts_source"),
        ),
        sa.CheckConstraint("severity IN ('warning', 'critical')", name=op.f("ck_alerts_severity")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(
        "uq_alerts_source_subject_active",
        "alerts",
        ["source", "subject"],
        unique=True,
        sqlite_where=_ACTIVE,
        postgresql_where=_ACTIVE,
    )
    op.create_index("ix_alerts_opened_at", "alerts", ["opened_at"])
    op.create_table(
        "alert_history",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("alert_id", sa.String(length=26), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("detail", weightsdb.PortableJSON(), nullable=False),
        sa.CheckConstraint(
            "event IN ('opened', 'seen', 'acknowledged', 'cleared')",
            name=op.f("ck_alert_history_event"),
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"], ["alerts.id"], name=op.f("fk_alert_history_alert_id_alerts")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_history")),
    )
    op.create_index("ix_alert_history_alert_id_at", "alert_history", ["alert_id", "at"])
    op.create_index("ix_alert_history_at", "alert_history", ["at"])


def downgrade() -> None:
    op.drop_index("ix_alert_history_at", table_name="alert_history")
    op.drop_index("ix_alert_history_alert_id_at", table_name="alert_history")
    op.drop_table("alert_history")
    op.drop_index("ix_alerts_opened_at", table_name="alerts")
    op.drop_index("uq_alerts_source_subject_active", table_name="alerts")
    op.drop_table("alerts")
