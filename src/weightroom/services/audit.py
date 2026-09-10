"""weightroom.services.audit — the one writer of ``audit_log`` and the trail's readers.

Spec §11 contract 2: every action the console takes is a row naming the actor, the time, the
target, the redacted parameters and the outcome. Append-only: the one update path is
``pending → ok|failed`` on the row's own id, for the guarded write W7 adds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from baseaicore import SuiteError, new_id
from sqlalchemy import select

from weightroom.domain.audit import ACTIONS, ACTORS, OUTCOMES, redact_params
from weightroom.infrastructure.db.models import AuditLog, Operator

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from weightroom.services.database import Database

__all__ = ["AuditNotFound", "AuditRow", "get_audit", "list_audit", "record", "record_cli"]


class AuditNotFound(SuiteError):
    """``GET /audit/{id}`` for an id that is not in the trail."""

    code: ClassVar[str] = "AUDIT_NOT_FOUND"


@dataclass(frozen=True, slots=True)
class AuditRow:
    """One row of the trail, as the API and the CLI render it."""

    id: str
    at: datetime
    actor: str
    operator: str | None
    app: str | None
    action: str
    target: str | None
    params: Any
    outcome: str
    message: str | None
    security: bool
    request_id: str | None
    backup_path: str | None = None
    dry_run_count: int | None = None
    actual_count: int | None = None

    def as_json(self) -> dict[str, Any]:
        """The api.md §7 shape."""
        return {
            "id": self.id,
            "at": self.at.isoformat(),
            "actor": self.actor,
            "operator": self.operator,
            "app": self.app,
            "action": self.action,
            "target": self.target,
            "params": self.params,
            "outcome": self.outcome,
            "message": self.message,
            "security": self.security,
            "request_id": self.request_id,
            "backup_path": self.backup_path,
            "dry_run_count": self.dry_run_count,
            "actual_count": self.actual_count,
        }


def record(
    database: Database,
    *,
    action: str,
    actor: str,
    outcome: str,
    now: datetime | None = None,
    operator_id: str | None = None,
    app: str | None = None,
    target: str | None = None,
    params: Mapping[str, Any] | None = None,
    message: str | None = None,
    security: bool = False,
    request_id: str | None = None,
) -> str:
    """Append one row and return its id.

    Args:
        database: The database handle.
        action: One of :data:`~weightroom.domain.audit.ACTIONS`.
        actor: One of :data:`~weightroom.domain.audit.ACTORS`.
        outcome: One of :data:`~weightroom.domain.audit.OUTCOMES`.
        now: The instant; the clock when ``None``.
        operator_id: The operator, when the actor is one.
        app: ``freeweight`` … ``weightroom`` ``ollama`` ``host``, or ``None``.
        target: The unit, key list, table, model ref, job id — or ``None``.
        params: The parameters, redacted here before they are written.
        message: The failure or refusal text.
        security: True for a security-key change or a guarded write.
        request_id: The request the action belongs to.

    Returns:
        The new row's ULID.

    Raises:
        ValueError: ``action``, ``actor`` or ``outcome`` is outside its closed set.
    """
    if action not in ACTIONS:
        message_text = f"{action!r} is not an audit action; the vocabulary is closed"
        raise ValueError(message_text)
    if actor not in ACTORS or outcome not in OUTCOMES:
        message_text = f"actor {actor!r} / outcome {outcome!r} outside the closed sets"
        raise ValueError(message_text)
    row_id = new_id()
    with database.write() as session:
        session.add(
            AuditLog(
                id=row_id,
                operator_id=operator_id,
                actor=actor,
                at=now or datetime.now(UTC),
                app=app,
                action=action,
                target=target,
                params=redact_params(dict(params or {})),
                outcome=outcome,
                message=message,
                security=security,
                request_id=request_id,
            )
        )
    return row_id


def record_cli(
    database: Database,
    *,
    action: str,
    outcome: str,
    target: str | None = None,
    params: Mapping[str, Any] | None = None,
    message: str | None = None,
    security: bool = False,
) -> str:
    """:func:`record` for a shell command: actor ``cli``, app ``weightroom``, no request."""
    return record(
        database,
        action=action,
        actor="cli",
        outcome=outcome,
        app="weightroom",
        target=target,
        params=params,
        message=message,
        security=security,
    )


def _to_row(row: AuditLog, username: str | None) -> AuditRow:
    return AuditRow(
        id=row.id,
        at=row.at,
        actor=row.actor,
        operator=username,
        app=row.app,
        action=row.action,
        target=row.target,
        params=row.params,
        outcome=row.outcome,
        message=row.message,
        security=row.security,
        request_id=row.request_id,
        backup_path=row.backup_path,
        dry_run_count=row.dry_run_count,
        actual_count=row.actual_count,
    )


def list_audit(
    database: Database,
    *,
    limit: int,
    app: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    before_id: str | None = None,
) -> tuple[Sequence[AuditRow], bool]:
    """The trail, newest first, by the ``(app, at)`` / ``(action, at)`` indexes.

    Args:
        database: The database handle.
        limit: Page size, already clamped.
        app: Filter by application.
        action: Filter by action.
        since: Rows at or after this instant.
        before_id: Cursor: rows with an id below this one (ULIDs order by time).

    Returns:
        The page and whether more rows follow.
    """
    statement = (
        select(AuditLog, Operator.username)
        .outerjoin(Operator, Operator.id == AuditLog.operator_id)
        .order_by(AuditLog.at.desc(), AuditLog.id.desc())
        .limit(limit + 1)
    )
    if app is not None:
        statement = statement.where(AuditLog.app == app)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if since is not None:
        statement = statement.where(AuditLog.at >= since)
    if before_id is not None:
        statement = statement.where(AuditLog.id < before_id)
    with database.read() as session:
        pairs = session.execute(statement).all()
        rows = [_to_row(entry, username) for entry, username in pairs[:limit]]
    return rows, len(pairs) > limit


def get_audit(database: Database, audit_id: str) -> AuditRow:
    """One row by id.

    Raises:
        AuditNotFound: No such row.
    """
    with database.read() as session:
        pair = session.execute(
            select(AuditLog, Operator.username)
            .outerjoin(Operator, Operator.id == AuditLog.operator_id)
            .where(AuditLog.id == audit_id)
        ).first()
        if pair is None:
            raise AuditNotFound(f"No audit row {audit_id!r}.", details={"id": audit_id})
        return _to_row(pair[0], pair[1])
