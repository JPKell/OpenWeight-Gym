"""weightroom.infrastructure.db.models — the declarative base and the Phase 1 tables.

WeightRoomGym owns this ``MetaData`` exclusively (database standards §1, spec §10): WeightsDB
provides plumbing only, and no package table is ever mounted here. The four applications'
databases are read through their own connection strings and are never modelled in this module —
a table they own has no SQLAlchemy class in WeightRoomGym, by ADR-0123 rule 3.

Phase 1 (migration ``0001``): ``operators``, ``sessions``, ``audit_log``, ``settings``,
``known_revisions`` (data model §2). The naming convention is what keeps Alembic's autogenerate
parity check and SQLite's batch mode agreeing on constraint names.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, LargeBinary, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from weightsdb import PortableJSON, UtcDateTime, ulid_primary_key

__all__ = [
    "AuditLog",
    "Base",
    "KnownRevision",
    "Operator",
    "Session",
    "Setting",
    "utcnow",
]

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """The one declarative base for every WeightRoomGym-owned table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone-aware now, for column defaults."""
    return datetime.now(UTC)


class Operator(Base):
    """The operator account: one row in 1.0 (ADR-0126 rule 7); the shape admits more."""

    __tablename__ = "operators"

    id: Mapped[str] = ulid_primary_key()
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    password_salt: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    kdf_params: Mapped[object] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    password_changed_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=utcnow
    )


class Session(Base):
    """A server-side login session; the cookie carries only ``id`` (ADR-0126 rule 4)."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_expires_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operator_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("operators.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    reauth_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class AuditLog(Base):
    """One action the console took: append-only, redacted, the operator's record (spec §11)."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_at", "at"),
        Index("ix_audit_log_app_at", "app", "at"),
        Index("ix_audit_log_action_at", "action", "at"),
    )

    id: Mapped[str] = ulid_primary_key()
    operator_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("operators.id"), nullable=True
    )
    actor: Mapped[str] = mapped_column(String, nullable=False)
    at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    app: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    target: Mapped[str | None] = mapped_column(String, nullable=True)
    params: Mapped[object] = mapped_column(PortableJSON, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    backup_path: Mapped[str | None] = mapped_column(String, nullable=True)
    dry_run_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    statement: Mapped[str | None] = mapped_column(String, nullable=True)
    security: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Setting(Base):
    """One runtime-changeable configuration value (ADR-0100's shape)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value_json: Mapped[object | None] = mapped_column(PortableJSON)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


class KnownRevision(Base):
    """An application ``alembic_version`` this WeightRoomGym release reads (ADR-0123 rule 3)."""

    __tablename__ = "known_revisions"

    app: Mapped[str] = mapped_column(String, primary_key=True)
    revision: Mapped[str] = mapped_column(String, primary_key=True)
    weightroom_version: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
