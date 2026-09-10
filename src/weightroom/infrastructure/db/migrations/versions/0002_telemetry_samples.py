"""telemetry_samples

The one Phase 3 table (data model §2): one row per sampler tick, host and primary-GPU fields,
``resident_json`` refreshed at a coarser cadence than the tick itself
(``services/telemetry.py``). ``id`` is a plain autoincrement integer rather than a ULID — the
one table in this schema where that is right, because it doubles as the SSE stream's frame id,
resumed with a numeric ``Last-Event-ID`` comparison rather than a lexicographic one.

Additive only. ``downgrade`` drops the table; that loses telemetry history, and only telemetry
history, which is why it is allowed to be silent rather than raising — no other row depends on it.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-09 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import weightsdb
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "telemetry_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("interval_ms", sa.Integer(), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("cpu_temperature_c", sa.Float(), nullable=True),
        sa.Column("ram_used_bytes", sa.BigInteger(), nullable=True),
        sa.Column("ram_total_bytes", sa.BigInteger(), nullable=True),
        sa.Column("gpu_index", sa.Integer(), nullable=True),
        sa.Column("gpu_utilization_percent", sa.Float(), nullable=True),
        sa.Column("gpu_temperature_c", sa.Float(), nullable=True),
        sa.Column("gpu_power_watts", sa.Float(), nullable=True),
        sa.Column("gpu_vram_used_bytes", sa.BigInteger(), nullable=True),
        sa.Column("gpu_vram_total_bytes", sa.BigInteger(), nullable=True),
        sa.Column("resident_json", weightsdb.PortableJSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_telemetry_samples")),
    )
    op.create_index("ix_telemetry_samples_at", "telemetry_samples", ["at"])


def downgrade() -> None:
    op.drop_index("ix_telemetry_samples_at", table_name="telemetry_samples")
    op.drop_table("telemetry_samples")
