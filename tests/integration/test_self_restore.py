"""ADR-0136: WeightRoomGym restores its own database through a job handed to a transient unit.

The hand-off is exercised with a fake ``systemd-run`` runner and an injected cgroup; the helper's
restore runs for real against SQLite files in ``tmp_path``, over the fake systemd controller.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.integration.test_jobs_queue import T0, database, services_for, settings_for
from weightroom.infrastructure.db.models import AuditLog
from weightroom.services import audit
from weightroom.services.database import Database, backup_database
from weightroom.services.jobs import (
    JobContext,
    JobView,
    OutputBuffer,
    attach_audit,
    claim_next,
    enqueue,
    get_job,
)
from weightroom.services.processes import CommandResult, FakeSystemdController
from weightroom.services.self_restore import (
    Receipt,
    SelfRestoreRefused,
    hand_off,
    perform,
    runs_under_unit,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["database"]

UNIT_CGROUP = "0::/user.slice/user-1000.slice/user@1000.service/app.slice/weightroom.service\n"
TERMINAL_CGROUP = "0::/user.slice/user-1000.slice/session-2.scope\n"


def _running_restore(database: Database, file: Path) -> JobView:
    job = enqueue(database, kind="self_restore", params={"file": str(file)}, now=T0)
    assert claim_next(database, now=T0, lease_seconds=60) is not None
    pending = audit.record(
        database, action="job.run", actor="job", outcome="pending", now=T0, target=job.id
    )
    attach_audit(database, job.id, pending)
    return get_job(database, job.id)


def _receipt(job: JobView, directory: Path) -> Path:
    assert job.started_at is not None
    return Receipt(
        job_id=job.id,
        file=str(job.params["file"]),
        params=job.params,
        attempt=job.attempt,
        queued_at=job.queued_at.isoformat(),
        started_at=job.started_at.isoformat(),
        audit_id=job.audit_id,
    ).write(directory)


def test_the_cgroup_says_whether_the_console_is_its_unit() -> None:
    assert runs_under_unit(UNIT_CGROUP)
    assert not runs_under_unit(TERMINAL_CGROUP)
    assert not runs_under_unit("")


# --- The hand-off ---------------------------------------------------------------------------------


def _context(database: Database, tmp_path: Path, job: JobView, **services: object) -> JobContext:
    return JobContext(
        job=job,
        settings=settings_for(tmp_path),
        database=database,
        services=replace(services_for(), **services),  # type: ignore[arg-type]  # test overrides
        output=OutputBuffer(100_000),
        cancelled=lambda: False,
        now=lambda: T0,
    )


def test_the_hand_off_refuses_a_file_that_is_not_one_of_weightroomgyms_backups(
    tmp_path: Path, database: Database
) -> None:
    stray = tmp_path / "elsewhere.sqlite3"
    stray.write_bytes(b"x")
    job = _running_restore(database, stray)
    outcome = hand_off(_context(database, tmp_path, job, cgroup=lambda: UNIT_CGROUP))
    assert outcome.state == "failed"
    assert "not one of WeightRoomGym's own backups" in (outcome.error or "")


def test_the_hand_off_refuses_a_console_that_is_not_running_as_its_unit(
    tmp_path: Path, database: Database
) -> None:
    backup = backup_database(database, output=None, keep=5).path
    job = _running_restore(database, backup)
    outcome = hand_off(_context(database, tmp_path, job, cgroup=lambda: TERMINAL_CGROUP))
    assert outcome.state == "failed"
    assert "not running as weightroom.service" in (outcome.error or "")
    assert "wr-gym db restore" in (outcome.error or "")


def test_the_hand_off_writes_a_receipt_and_launches_a_transient_unit(
    tmp_path: Path, database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WEIGHTROOM_DATA_DIR", str(tmp_path / "data"))
    backup = backup_database(database, output=None, keep=5).path
    job = _running_restore(database, backup)
    launched: list[list[str]] = []

    def runner(argv: Sequence[str], env: object, timeout: float) -> CommandResult:
        launched.append(list(argv))
        return CommandResult(tuple(argv), 0, "", "")

    outcome = hand_off(
        _context(
            database,
            tmp_path,
            job,
            cgroup=lambda: UNIT_CGROUP,
            which=lambda name: f"/usr/bin/{name}",
            runner=runner,
            config_path=tmp_path / "config.toml",
        )
    )

    assert outcome.state == "handed_off"
    argv = launched[0]
    assert argv[:2] == ["/usr/bin/systemd-run", "--user"]
    assert f"--unit=wr-gym-restore-{job.id.lower()}" in argv
    assert argv[argv.index("--config") + 1] == str(tmp_path / "config.toml")
    receipt_path = Path(argv[argv.index("--receipt") + 1])
    assert receipt_path == tmp_path / "data" / "restores" / f"{job.id}.json"
    assert Receipt.load(receipt_path).file == str(backup.resolve())


# --- The helper -----------------------------------------------------------------------------------


def test_the_helper_restores_carries_the_job_forward_keeps_later_rows_and_starts_the_console(
    tmp_path: Path, database: Database
) -> None:
    settings = settings_for(tmp_path)
    backup = backup_database(database, output=None, keep=5).path
    later = audit.record(database, action="login", actor="operator", outcome="ok", now=T0)
    job = _running_restore(database, backup)
    receipts = tmp_path / "restores"
    path = _receipt(job, receipts)
    database.close()
    host = FakeSystemdController(states={"weightroom.service": "active"})

    report = perform(
        path,
        settings=settings,
        controller=host,
        now=lambda: T0 + timedelta(minutes=1),
        directory=receipts,
    )

    assert report.ok, report.message
    assert report.started
    assert [call[3] for call in host.calls if call[0] == "act"] == ["stop", "start"]
    assert report.pre_restore_backup is not None
    assert report.pre_restore_backup.is_file()
    assert not path.exists()
    with Database.from_url(settings.storage.database_url or "") as restored:
        carried = get_job(restored, job.id)
        assert carried.state == "completed"
        with restored.read() as session:
            row = session.get(AuditLog, carried.audit_id)
            assert row is not None
            assert (row.action, row.outcome, row.security) == ("job.run", "ok", True)
            assert row.backup_path == str(report.pre_restore_backup)
            assert session.get(AuditLog, later) is None  # written after the backup
    with (
        Database.from_url(f"sqlite:///{report.pre_restore_backup}") as kept,
        kept.read() as session,
    ):
        assert session.get(AuditLog, later) is not None


def test_a_failed_restore_leaves_the_live_database_records_the_failure_and_starts_the_console(
    tmp_path: Path, database: Database
) -> None:
    settings = settings_for(tmp_path)
    broken = tmp_path / "backups" / "manual-broken.sqlite3"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_bytes(b"this is not a database")
    kept = audit.record(database, action="login", actor="operator", outcome="ok", now=T0)
    job = _running_restore(database, broken)
    receipts = tmp_path / "restores"
    path = _receipt(job, receipts)
    database.close()
    host = FakeSystemdController(states={"weightroom.service": "active"})

    report = perform(path, settings=settings, controller=host, now=lambda: T0, directory=receipts)

    assert not report.ok
    assert report.started
    assert "the restore failed" in report.message
    with Database.from_url(settings.storage.database_url or "") as live:
        failed = get_job(live, job.id)
        assert failed.state == "failed"
        with live.read() as session:
            assert session.get(AuditLog, kept) is not None
            pending = session.get(AuditLog, failed.audit_id)
            assert pending is not None
            assert pending.outcome == "failed"


def test_a_console_that_will_not_stop_is_not_restored(tmp_path: Path, database: Database) -> None:
    settings = settings_for(tmp_path)
    backup = backup_database(database, output=None, keep=5).path
    job = _running_restore(database, backup)
    receipts = tmp_path / "restores"
    path = _receipt(job, receipts)
    host = FakeSystemdController(
        states={"weightroom.service": "active"},
        refuse={("weightroom.service", "stop"): "Access denied"},
    )
    report = perform(path, settings=settings, controller=host, now=lambda: T0, directory=receipts)
    assert not report.ok
    assert not report.started
    assert "Access denied" in report.message
    assert get_job(database, job.id).state == "failed"


def test_the_helper_refuses_a_receipt_outside_the_receipts_directory(tmp_path: Path) -> None:
    stray = tmp_path / "receipt.json"
    stray.write_text("{}", encoding="utf-8")
    with pytest.raises(SelfRestoreRefused):
        perform(
            stray,
            settings=settings_for(tmp_path),
            controller=FakeSystemdController(),
            directory=tmp_path / "restores",
        )
