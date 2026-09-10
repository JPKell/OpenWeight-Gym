"""weightroom.services.self_restore — WeightRoomGym restores its own database (ADR-0136).

Two halves, in two processes.

:func:`hand_off` runs on the job worker, inside the console. It checks the chosen file is one of
WeightRoomGym's own backups, that this process is ``weightroom.service`` (so something can start it
again), writes a receipt and launches ``systemd-run --user --unit=wr-gym-restore-<job>`` running
``wr-gym db restore-self``. A transient *service* unit lives outside the console's cgroup, so
stopping the console does not stop it.

:func:`perform` runs in that unit. It stops the console, takes a ``pre-restore`` backup of the live
database, restores the chosen file, migrates it to head, writes the job's row and its ``job.run``
audit row into the restored database — naming the pre-restore backup, which keeps every row written
after the chosen backup was taken — and starts the console again. A failure after the stop puts the
live database back and still starts the console.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

from baseaicore import SuiteError

from weightroom.config import data_dir
from weightroom.infrastructure.db.models import Job
from weightroom.services import audit
from weightroom.services.database import (
    Database,
    backup_database,
    backup_directory,
    ensure_ready,
    restore_database,
)
from weightroom.services.jobs import Outcome
from weightroom.services.processes import child_environment, executable_for, run_command

if TYPE_CHECKING:
    from collections.abc import Callable

    from weightroom.config import Settings
    from weightroom.services.jobs import JobContext
    from weightroom.services.processes import SystemdController

__all__ = [
    "CONSOLE_UNIT",
    "RESTORE_UNIT_PREFIX",
    "Receipt",
    "RestoreReport",
    "SelfRestoreRefused",
    "hand_off",
    "own_cgroup",
    "perform",
    "receipts_directory",
    "resolve_backup",
    "runs_under_unit",
]

logger = logging.getLogger(__name__)

CONSOLE_UNIT: Final = "weightroom.service"
RESTORE_UNIT_PREFIX: Final = "wr-gym-restore-"
_LAUNCH_TIMEOUT_SECONDS: Final = 30.0


class SelfRestoreRefused(SuiteError):
    """A restore of WeightRoomGym's own database this console will not start."""

    code: ClassVar[str] = "VALIDATION_ERROR"


def receipts_directory() -> Path:
    """``<data>/restores/``, where a hand-off leaves the helper its receipt."""
    return data_dir() / "restores"


def own_cgroup() -> str:
    """This process's ``/proc/self/cgroup``, or ``""`` where there is none."""
    try:
        return Path("/proc/self/cgroup").read_text(encoding="utf-8")
    except OSError:
        return ""


def runs_under_unit(cgroup_text: str, unit: str = CONSOLE_UNIT) -> bool:
    """Whether a cgroup listing places the process inside ``unit``."""
    return any(line.rstrip().endswith(f"/{unit}") for line in cgroup_text.splitlines())


def resolve_backup(database: Database, file: str) -> Path:
    """The chosen backup, which must be a file inside WeightRoomGym's own backups directory.

    Args:
        database: WeightRoomGym's own database.
        file: An absolute path, or a name relative to the backups directory.

    Returns:
        The resolved path.

    Raises:
        SelfRestoreRefused: The database is PostgreSQL (WeightsDB restores SQLite only and names
            ``pg_restore`` for the rest), or the file is not a backup in that directory.
    """
    if database.engine.dialect.name != "sqlite":
        raise SelfRestoreRefused(
            "WeightRoomGym restores its own database from the console only on SQLite; restore a "
            "PostgreSQL database with pg_restore, with the console stopped.",
            details={"dialect": database.engine.dialect.name},
        )
    directory = backup_directory(database.engine).resolve()
    candidate = Path(file).expanduser()
    resolved = (candidate if candidate.is_absolute() else directory / candidate).resolve()
    if not resolved.is_relative_to(directory) or not resolved.is_file():
        raise SelfRestoreRefused(
            f"{file} is not one of WeightRoomGym's own backups in {directory}.",
            details={"file": file, "directory": str(directory)},
        )
    return resolved


@dataclass(frozen=True, slots=True)
class Receipt:
    """What the hand-off tells the helper: the job, its row's fields, and the file."""

    job_id: str
    file: str
    params: dict[str, Any]
    attempt: int
    queued_at: str
    started_at: str | None
    audit_id: str | None
    handed_off_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def write(self, directory: Path) -> Path:
        """Write the receipt as ``<job>.json``, owner-only, and return its path."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.job_id}.json"
        path.touch(mode=0o600, exist_ok=True)
        path.write_text(json.dumps(asdict(self), sort_keys=True), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> Receipt:
        """Read one.

        Raises:
            SelfRestoreRefused: Not a receipt.
        """
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
            return cls(**body)
        except (OSError, ValueError, TypeError) as exc:
            raise SelfRestoreRefused(
                f"{path} is not a restore receipt: {exc}", details={"receipt": str(path)}
            ) from exc


def hand_off(context: JobContext) -> Outcome:
    """The worker's half: verify, write the receipt, launch the transient unit (ADR-0136 rule 2).

    Returns:
        ``handed_off`` once ``systemd-run`` accepted the unit — the job stays running, and the
        helper records its end. ``failed``, having stopped nothing, when the file is refused, when
        the console is not ``weightroom.service`` (rule 5), or when the unit could not be started.
    """
    which = context.services.which or shutil.which
    try:
        source = resolve_backup(context.database, str(context.job.params.get("file", "")))
    except SelfRestoreRefused as exc:
        return Outcome("failed", exc.message)
    if not runs_under_unit((context.services.cgroup or own_cgroup)()):
        return Outcome(
            "failed",
            "WeightRoomGym is not running as weightroom.service, so nothing could start it again "
            "after a restore (ADR-0136 rule 5). Stop the console, run `wr-gym db restore "
            f"{source} --confirm`, and start it again.",
        )
    systemd_run = which("systemd-run")
    executable = executable_for(context.settings, "weightroom", which=which)
    if systemd_run is None or executable is None:
        return Outcome(
            "failed",
            "systemd-run or wr-gym is not on PATH, so the restore cannot be handed to a unit of "
            "its own; nothing was stopped.",
        )
    job = context.job
    receipt = Receipt(
        job_id=job.id,
        file=str(source),
        params=job.params,
        attempt=job.attempt,
        queued_at=job.queued_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        audit_id=job.audit_id,
    )
    path = receipt.write(receipts_directory())
    unit = f"{RESTORE_UNIT_PREFIX}{job.id.lower()}"
    argv = [systemd_run, "--user", f"--unit={unit}", "--collect", "--quiet", executable]
    argv += ["db", "restore-self", "--receipt", str(path)]
    if context.services.config_path is not None:
        argv += ["--config", str(context.services.config_path)]
    context.output.line("$ " + " ".join(argv))
    result = (context.services.runner or run_command)(
        argv, child_environment(), _LAUNCH_TIMEOUT_SECONDS
    )
    if not result.ok:
        path.unlink(missing_ok=True)
        return Outcome("failed", f"systemd-run did not start the restore: {result.failure_text}")
    context.output.line(
        f"handed to {unit}: the console stops, restores {source.name} and starts again. "
        f"`journalctl --user -u {unit}` shows the helper's own output."
    )
    return Outcome("handed_off")


@dataclass(frozen=True, slots=True)
class RestoreReport:
    """What :func:`perform` did."""

    ok: bool
    job_id: str
    source: str
    pre_restore_backup: Path | None
    started: bool
    message: str


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _carry_forward(
    database: Database, receipt: Receipt, *, now: datetime, pre_restore: Path, message: str
) -> None:
    """Write the job's row and its ``job.run`` row into the restored database (ADR-0136 rule 3)."""
    audit_id = audit.record(
        database,
        action="job.run",
        actor="job",
        outcome="ok",
        now=now,
        app="weightroom",
        target=receipt.job_id,
        params={"kind": "self_restore", "file": receipt.file, "attempt": receipt.attempt},
        message=message,
        security=True,
        backup_path=str(pre_restore),
    )
    with database.write() as session:
        row = session.get(Job, receipt.job_id)
        if row is None:
            row = Job(
                id=receipt.job_id,
                kind="self_restore",
                params=receipt.params,
                attempt=receipt.attempt,
                queued_at=_parse(receipt.queued_at) or now,
            )
            session.add(row)
        row.state = "completed"
        row.started_at = _parse(receipt.started_at)
        row.finished_at = now
        row.lease_expires_at = None
        row.output = message
        row.error = None
        row.audit_id = audit_id


def _fail_job(database: Database, receipt: Receipt, *, now: datetime, message: str) -> None:
    """Record the job failed in whichever database is live: the original, or the one put back."""
    with database.write() as session:
        row = session.get(Job, receipt.job_id)
        pending = row.audit_id if row is not None else None
        if row is not None and row.state == "running":
            row.state, row.finished_at, row.lease_expires_at = "failed", now, None
            row.error = message
    if pending is None:
        return
    try:
        audit.complete(database, pending, outcome="failed", message=message)
    except ValueError:
        logger.info("self_restore.audit_already_complete", extra={"audit_id": pending})


def perform(
    receipt_path: Path,
    *,
    settings: Settings,
    controller: SystemdController,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    directory: Path | None = None,
) -> RestoreReport:
    """The helper's half: stop, back up, restore, migrate, carry forward, start (ADR-0136 rule 3).

    Args:
        receipt_path: The receipt :func:`hand_off` wrote.
        settings: WeightRoomGym's settings — the same configuration file the console runs on.
        controller: The systemd boundary.
        now: The clock.
        directory: Where receipts live; :func:`receipts_directory` by default.

    Returns:
        The report. The console is started again whatever happened after it was stopped.

    Raises:
        SelfRestoreRefused: The receipt is not inside the receipts directory, or is not one.
    """
    root = (directory if directory is not None else receipts_directory()).resolve()
    path = receipt_path.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise SelfRestoreRefused(
            f"{receipt_path} is not a receipt in {root}.", details={"receipt": str(receipt_path)}
        )
    receipt = Receipt.load(path)
    url = settings.storage.database_url or ""
    stop = controller.act(CONSOLE_UNIT, "stop")
    if not stop.ok:
        message = f"the console could not be stopped, so nothing was restored: {stop.failure_text}"
        with Database.from_url(url) as database:
            _fail_job(database, receipt, now=now(), message=message)
        path.unlink(missing_ok=True)
        return RestoreReport(
            False, receipt.job_id, receipt.file, None, started=False, message=message
        )
    pre_restore: Path | None = None
    ok = False
    try:
        with Database.from_url(url) as database:
            swapped = False
            try:
                target = (
                    backup_directory(database.engine)
                    / f"pre-restore-{receipt.job_id.lower()}.sqlite3"
                )
                pre_restore = backup_database(database, output=target, keep=0).path
                restore_database(database, source=Path(receipt.file), confirm=True)
                swapped = True
                ensure_ready(
                    database,
                    auto_migrate=True,
                    backup_retention=settings.storage.backup_retention,
                )
                message = (
                    f"restored {receipt.file}; the database it replaced, with every row written "
                    f"since that backup, is {pre_restore}"
                )
                _carry_forward(
                    database, receipt, now=now(), pre_restore=pre_restore, message=message
                )
                ok = True
            except Exception as exc:  # noqa: BLE001 — every failure puts the live database back
                logger.exception("self_restore.failed", extra={"job_id": receipt.job_id})
                message = f"the restore failed ({type(exc).__name__}: {exc})"
                if swapped and pre_restore is not None:
                    try:
                        restore_database(database, source=pre_restore, confirm=True)
                        message += f"; the database was put back from {pre_restore}"
                    except Exception as back:  # noqa: BLE001 — reported, and the unit still starts
                        message += f"; putting it back from {pre_restore} failed too ({back})"
                try:
                    _fail_job(database, receipt, now=now(), message=message)
                except Exception:  # noqa: BLE001 — the report and the journal still say it
                    logger.exception("self_restore.fail_record_failed")
    finally:
        started = controller.act(CONSOLE_UNIT, "start").ok
        path.unlink(missing_ok=True)
    return RestoreReport(ok, receipt.job_id, receipt.file, pre_restore, started, message)
