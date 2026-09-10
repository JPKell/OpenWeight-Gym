"""jobs

The queue (data model §2, spec §7.10, row W9): ``job_schedules`` and ``jobs``. ``jobs`` carries
``cancel_requested_at``, the flag a cancel sets on a job that is already running.

Five schedules are seeded here, **disabled** — one per scheduled kind: a nightly backup of every
database, a nightly retention trim, a weekly model refresh, a nightly FreeWeight suite run with no
model chosen (it cannot be enabled until one is), and a nightly docs index. The data model said the
wizard seeds them; a migration does it once for every installation, including one set up before
this row, which the wizard never revisits.

Additive only. ``downgrade`` drops both tables, which loses the job history; the audit rows the
jobs wrote stay.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-10 00:00:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
import weightsdb
from alembic import op
from baseaicore import new_id

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_SEEDS: tuple[tuple[str, str, dict[str, object]], ...] = (
    (
        "backup",
        "0 3 * * *",
        {"apps": ["freeweight", "loadcoach", "ideapress", "promptcadence", "weightroom"]},
    ),
    (
        "retention_trim",
        "30 3 * * *",
        {"guarded_backup_days": 90, "freeweight_older_than_days": None},
    ),
    ("model_refresh", "0 4 * * 1", {"apps": ["freeweight", "loadcoach"]}),
    (
        "freeweight_suite_run",
        "0 2 * * *",
        {"suite": "native.performance", "allow_prompt_override": False},
    ),
    ("docs_index", "0 5 * * *", {}),
)


def upgrade() -> None:
    schedules = op.create_table(
        "job_schedules",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("params", weightsdb.PortableJSON(), nullable=False),
        sa.Column("cron", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("last_run_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("last_job_id", sa.String(length=26), nullable=True),
        sa.Column("created_at", weightsdb.UtcDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_schedules")),
    )
    op.create_index(
        "ix_job_schedules_enabled_next_run_at", "job_schedules", ["enabled", "next_run_at"]
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("params", weightsdb.PortableJSON(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("schedule_id", sa.String(length=26), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("lease_expires_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("cancel_requested_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("queued_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("started_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("finished_at", weightsdb.UtcDateTime(), nullable=True),
        sa.Column("output", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("audit_id", sa.String(length=26), nullable=True),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name=op.f("ck_jobs_state"),
        ),
        sa.ForeignKeyConstraint(
            ["audit_id"], ["audit_log.id"], name=op.f("fk_jobs_audit_id_audit_log")
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["job_schedules.id"],
            name=op.f("fk_jobs_schedule_id_job_schedules"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_state_lease_expires_at", "jobs", ["state", "lease_expires_at"])
    op.create_index("ix_jobs_kind_queued_at", "jobs", ["kind", "queued_at"])
    now = datetime.now(UTC)
    op.bulk_insert(
        schedules,
        [
            {
                "id": new_id(),
                "kind": kind,
                "params": params,
                "cron": cron,
                "enabled": False,
                "next_run_at": None,
                "last_run_at": None,
                "last_job_id": None,
                "created_at": now,
            }
            for kind, cron, params in _SEEDS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_kind_queued_at", table_name="jobs")
    op.drop_index("ix_jobs_state_lease_expires_at", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_job_schedules_enabled_next_run_at", table_name="job_schedules")
    op.drop_table("job_schedules")
