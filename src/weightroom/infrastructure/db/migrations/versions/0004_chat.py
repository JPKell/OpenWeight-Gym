"""chat

The four chat tables (data model §2, spec §7.6): ``conversations``, ``messages``,
``message_events``, ``attachments``. ``conversations.backend`` is a check constraint naming the
two backends and no third (spec §11 contract 6); ``message_events.id`` is an autoincrement integer
for the reason ``telemetry_samples.id`` is — it is the SSE frame id, resumed numerically.

Additive only. ``downgrade`` drops all four, which loses conversation history; nothing outside
them references a row in them.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-10 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import weightsdb
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("backend", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("task_profile", sa.String(), nullable=True),
        sa.Column("model_override", sa.String(), nullable=True),
        sa.Column("classification", sa.String(), nullable=True),
        sa.Column("tier", sa.String(), nullable=True),
        sa.Column("tools", weightsdb.PortableJSON(), nullable=True),
        sa.Column("remote_trajectory_id", sa.String(), nullable=True),
        sa.Column("created_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("updated_at", weightsdb.UtcDateTime(), nullable=False),
        sa.CheckConstraint(
            "backend IN ('loadcoach', 'promptcadence')", name=op.f("ck_conversations_backend")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("conversation_id", sa.String(length=26), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("thinking", sa.String(), nullable=True),
        sa.Column("routing", weightsdb.PortableJSON(), nullable=True),
        sa.Column("usage", weightsdb.PortableJSON(), nullable=True),
        sa.Column("cost", weightsdb.PortableJSON(), nullable=True),
        sa.Column("remote_job_id", sa.String(), nullable=True),
        sa.Column("remote_step_id", sa.String(), nullable=True),
        sa.Column("finish_reason", sa.String(), nullable=True),
        sa.Column("created_at", weightsdb.UtcDateTime(), nullable=False),
        sa.Column("completed_at", weightsdb.UtcDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_messages_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
        sa.UniqueConstraint(
            "conversation_id", "sequence", name=op.f("uq_messages_conversation_id_sequence")
        ),
    )
    op.create_table(
        "message_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.String(length=26), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", weightsdb.PortableJSON(), nullable=False),
        sa.Column("at", weightsdb.UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_message_events_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_events")),
        sa.UniqueConstraint(
            "message_id", "sequence", name=op.f("uq_message_events_message_id_sequence")
        ),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("conversation_id", sa.String(length=26), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("stored_path", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", weightsdb.UtcDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_attachments_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
    )


def downgrade() -> None:
    op.drop_table("attachments")
    op.drop_table("message_events")
    op.drop_table("messages")
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
    op.drop_table("conversations")
