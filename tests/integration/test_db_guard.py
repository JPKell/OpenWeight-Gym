"""services/db_guard: ADR-0124's five conditions wired, each failed alone, over a copy of
FreeWeight's fixture database — and the PostgreSQL leg of the same write.

Every refusal is also checked for what it did **not** do: the application's rows are unchanged, and
the audit trail holds exactly the row the refusal should leave.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import select, text
from weightsdb.backup import BackupResult
from weightsdb.testing import temporary_postgres

from tests.support import fake_application, fill_rows, fixture_database
from weightroom.config import Settings, load_settings
from weightroom.domain.guard import (
    GuardAppRunning,
    GuardAuditFailed,
    GuardBackupFailed,
    GuardDryRunFailed,
    GuardError,
    GuardStatementRefused,
    GuardTableLocked,
    GuardTableMismatch,
)
from weightroom.infrastructure.db.models import AuditLog
from weightroom.services import db_guard
from weightroom.services.audit import record as record_row
from weightroom.services.auth import ReauthRequired
from weightroom.services.database import Database, ensure_ready
from weightroom.services.db_reader import DatabaseUrlCache
from weightroom.services.processes import FakeSystemdController, UnitState

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
SQL = "DELETE FROM samples WHERE run_test_id = 'RT1'"


def _closed(address: tuple[str, int], timeout: float) -> None:
    raise ConnectionRefusedError(address)


def _answering(address: tuple[str, int], timeout: float) -> None:
    return None


def _code(row: AuditLog) -> Any:  # noqa: ANN401 — a JSON value
    return cast("dict[str, Any]", row.params)["code"]


def _sample(index: int, run_test: str) -> dict[str, Any]:
    return {
        "id": f"01SAMPLE{index:018d}",
        "run_test_id": run_test,
        "ordinal": index,
        "status": "completed",
    }


@dataclass
class Rig:
    """A FreeWeight database copy with five samples (three in RT1) and two metric values."""

    settings: Settings
    database: Database
    controller: FakeSystemdController
    path: Path
    backups: Path

    def dry(self, sql: str = SQL, *, connect: Any = _closed) -> db_guard.DryRun:  # noqa: ANN401
        return db_guard.dry_run(
            self.settings,
            self.database,
            self.controller,
            "freeweight",
            sql,
            urls=DatabaseUrlCache(),
            monotonic=0.0,
            connect=connect,
        )

    def write(
        self,
        sql: str = SQL,
        *,
        typed: tuple[str, ...] = ("samples",),
        dry_run_id: str | None = None,
        connect: Any = _closed,  # noqa: ANN401
        authorise: Any = None,  # noqa: ANN401
    ) -> db_guard.WriteResult:
        identifier = dry_run_id if dry_run_id is not None else str(self.dry(sql).dry_run_id)
        return db_guard.guarded_write(
            self.settings,
            self.database,
            self.controller,
            "freeweight",
            sql,
            tables_typed=typed,
            dry_run_id=identifier,
            operator_id=None,
            urls=DatabaseUrlCache(),
            now=NOW,
            monotonic=0.0,
            authorise=authorise,
            backups_root=self.backups,
            connect=connect,
        )

    def count(self, table: str = "samples", path: Path | None = None) -> int:
        # A backup is a finished file, read immutable so the read leaves no -shm beside it.
        mode = "ro" if path is None else "ro&immutable=1"
        connection = sqlite3.connect(f"file:{path or self.path}?mode={mode}", uri=True)
        try:
            return int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])  # noqa: S608
        finally:
            connection.close()

    def rows(self) -> list[AuditLog]:
        with self.database.read() as session:
            statement = select(AuditLog).where(AuditLog.action == "db.guarded_write")
            return list(session.scalars(statement.order_by(AuditLog.id)))


def _rig(tmp_path: Path, *, state: UnitState = "inactive") -> Rig:
    path = fixture_database(tmp_path, "freeweight-0009")
    fill_rows(
        path, "samples", [_sample(index, "RT1" if index < 3 else "RT2") for index in range(5)]
    )
    fill_rows(
        path,
        "metric_values",
        [
            {"id": f"01METRIC{index:018d}", "sample_id": f"01SAMPLE{index:018d}"}
            for index in range(2)
        ],
    )
    executable, _config, _document = fake_application(
        tmp_path, "freeweight", database_url=f"sqlite:///{path}"
    )
    file = tmp_path / "console.toml"
    file.write_text(
        f'[apps.freeweight]\nexecutable = "{executable}"\nbase_url = "http://127.0.0.1:9"\n',
        encoding="utf-8",
    )
    database = Database.from_url(f"sqlite:///{tmp_path / 'weightroom.sqlite3'}")
    ensure_ready(database, auto_migrate=True)
    return Rig(
        settings=load_settings(config_path=file).settings,
        database=database,
        controller=FakeSystemdController(states={"freeweight.service": state}),
        path=path,
        backups=tmp_path / "backups",
    )


def test_a_write_that_passes_all_five_conditions_lands_with_its_backup_and_its_row(
    tmp_path: Path,
) -> None:
    rig = _rig(tmp_path)
    dry = rig.dry()
    assert dry.counts is not None
    assert (dry.counts.rows, dry.tables, dry.counts.changes["metric_values"]) == (
        3,
        ("samples",),
        -2,
    )
    assert [one.verdict for one in dry.conditions()] == [
        "pass",
        "pending",
        "pass",
        "pending",
        "pending",
    ]
    result = rig.write(dry_run_id=str(dry.dry_run_id))
    assert (result.counts.rows, rig.count(), rig.count("metric_values")) == (3, 2, 0)
    assert (
        result.backup_path
        == rig.backups / "freeweight" / "20260910T120000000000Z-guarded-write.sqlite3"
    )
    assert result.backup_path.stat().st_mode & 0o777 == 0o600
    assert rig.count(path=result.backup_path) == 5  # the backup is the database before the write
    (row,) = rig.rows()
    assert (row.outcome, row.backup_path, row.dry_run_count, row.actual_count) == (
        "ok",
        str(result.backup_path),
        3,
        3,
    )
    assert (row.statement, row.security, row.target) == (SQL, True, "samples")
    assert [one["verdict"] for one in result.as_json()["checklist"]] == ["pass"] * 5
    assert db_guard.list_backups("freeweight", root=rig.backups)[0].path == result.backup_path


CONDITION_ERRORS: dict[int, type[GuardError]] = {
    1: GuardAppRunning,
    2: GuardBackupFailed,
    3: GuardDryRunFailed,
    4: GuardTableMismatch,
    5: GuardAuditFailed,
}


@pytest.mark.parametrize("condition", sorted(CONDITION_ERRORS))
def test_each_condition_failed_alone_refuses_with_its_code_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, condition: int
) -> None:
    rig = _rig(tmp_path)
    options: dict[str, Any] = {"dry_run_id": str(rig.dry().dry_run_id)}
    if condition == 1:
        options["connect"] = _answering  # the unit is inactive; something answers on the port
    elif condition == 2:
        rig.backups.mkdir()
        (rig.backups / "freeweight").write_text("a file where the directory should be")
    elif condition == 3:
        options["dry_run_id"] = "0" * 32
    elif condition == 4:
        options["typed"] = ("Samples",)
    else:

        def refusing_pending(*args: Any, **fields: Any) -> str:  # noqa: ANN401
            if fields.get("outcome") == "pending":
                raise RuntimeError("database is locked")
            return record_row(*args, **fields)

        monkeypatch.setattr(db_guard, "record", refusing_pending)
    with pytest.raises(CONDITION_ERRORS[condition]) as refused:
        rig.write(**options)
    assert refused.value.details["condition"] == condition
    assert (rig.count(), rig.count("metric_values")) == (5, 2)
    expected = {2: ["failed"], 5: []}.get(condition, ["refused"])
    assert [row.outcome for row in rig.rows()] == expected


def test_an_active_unit_refuses_even_with_nothing_on_the_port(tmp_path: Path) -> None:
    rig = _rig(tmp_path)
    identifier = str(rig.dry().dry_run_id)
    rig.controller.states["freeweight.service"] = "active"
    with pytest.raises(GuardAppRunning, match="unit active"):
        rig.write(dry_run_id=identifier)
    assert rig.count() == 5


def test_a_crash_between_the_pending_row_and_the_statement_leaves_the_pending_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = _rig(tmp_path)
    identifier = str(rig.dry().dry_run_id)

    class Crash(BaseException):
        """The process dying — not an exception the guard's handlers catch."""

    real = db_guard.execute_statement

    def crashing(*args: Any, commit: bool, **options: Any) -> db_guard.Counts:  # noqa: ANN401
        if commit:
            raise Crash
        return real(*args, commit=commit, **options)

    monkeypatch.setattr(db_guard, "execute_statement", crashing)
    with pytest.raises(Crash):
        rig.write(dry_run_id=identifier)
    (row,) = rig.rows()
    assert (row.outcome, row.actual_count, row.dry_run_count) == ("pending", None, 3)
    assert row.backup_path is not None and Path(row.backup_path).is_file()
    assert rig.count() == 5


def test_counts_that_change_under_the_statement_roll_it_back_and_fail_the_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = _rig(tmp_path)
    identifier = str(rig.dry().dry_run_id)
    real = db_guard.execute_statement

    def growing(*args: Any, commit: bool, **options: Any) -> db_guard.Counts:  # noqa: ANN401
        if commit:  # another writer adds a matching row after the backup, before the statement
            fill_rows(rig.path, "samples", [_sample(99, "RT1")])
        return real(*args, commit=commit, **options)

    monkeypatch.setattr(db_guard, "execute_statement", growing)
    with pytest.raises(GuardDryRunFailed, match="Rolled back: the statement reported 4 rows"):
        rig.write(dry_run_id=identifier)
    (row,) = rig.rows()
    assert (row.outcome, row.actual_count) == ("failed", 4)
    assert rig.count() == 6  # the statement was rolled back; only the other writer's row landed


def test_a_locked_table_named_is_refused_and_a_run_takes_its_event_log_with_it(
    tmp_path: Path,
) -> None:
    rig = _rig(tmp_path)
    dry = rig.dry("DELETE FROM runs WHERE id = 'x'")  # ADR-0134 rule 1, on the real schema
    events = next(one for one in dry.reached if one.table == "run_events")
    assert (events.path, events.action) == (("runs", "run_events"), "ON DELETE CASCADE")
    with pytest.raises(GuardTableLocked, match="models is never writable"):
        rig.dry("UPDATE models SET name = 'x'")
    with pytest.raises(GuardTableLocked, match="run_events is never writable"):
        rig.write("DELETE FROM run_events WHERE id = 'x'", typed=("run_events",), dry_run_id="x")
    assert [(row.outcome, _code(row)) for row in rig.rows()] == [("refused", "GUARD_TABLE_LOCKED")]


def test_while_the_application_runs_the_dry_run_touches_nothing_and_says_why(
    tmp_path: Path,
) -> None:
    rig = _rig(tmp_path, state="active")
    dry = rig.dry()
    body = dry.as_json()
    assert (dry.counts, dry.dry_run_id, body["row_count"], body["unit_state"]) == (
        None,
        None,
        None,
        "active",
    )
    assert [one["verdict"] for one in body["checklist"]] == ["fail"] + ["pending"] * 4
    assert body["reached"][0]["change"] is None


def test_a_refused_statement_a_failing_dry_run_and_a_refused_session_are_each_audited(
    tmp_path: Path,
) -> None:
    rig = _rig(tmp_path)
    with pytest.raises(GuardStatementRefused, match="VACUUM is refused by name"):
        rig.write("VACUUM", typed=(), dry_run_id="x")
    with pytest.raises(GuardDryRunFailed, match="no such column: nope"):
        rig.dry("DELETE FROM samples WHERE nope = 1")

    def refuse() -> None:
        raise ReauthRequired("This action needs the password again.", details={})

    with pytest.raises(ReauthRequired):
        rig.write(authorise=refuse, dry_run_id="x")
    assert [(row.outcome, _code(row)) for row in rig.rows()] == [
        ("refused", "GUARD_STATEMENT_REFUSED"),
        ("refused", "REAUTH_REQUIRED"),
    ]
    assert rig.count() == 5


def test_condition_one_is_observed_not_asserted() -> None:
    settings = load_settings(config_path=None).settings
    no_systemd = FakeSystemdController(supported=False)
    observed = db_guard.observe(settings, no_systemd, "freeweight", connect=_closed)
    assert (observed.unit_state, observed.port_open, observed.stopped) == (
        "unsupported",
        False,
        True,
    )
    assert observed.address == "127.0.0.1:8765"
    absent = db_guard.observe(settings, FakeSystemdController(), "loadcoach", connect=_answering)
    assert (absent.unit_state, absent.port_open, absent.stopped) == ("absent", True, False)
    assert "port 127.0.0.1:8766 open" in absent.evidence


@pytest.mark.integration
def test_postgresql_dry_run_reach_and_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def dumped(engine: Any, destination: Path, **_options: Any) -> BackupResult:  # noqa: ANN401
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"a pg_dump stand-in: weightsdb's own tests run pg_dump")
        return BackupResult(path=destination, size_bytes=1, created_at=NOW, dialect="postgresql")

    monkeypatch.setattr(db_guard, "weightsdb_backup", dumped)
    with temporary_postgres() as engine:
        with engine.begin() as connection:
            for statement in (
                "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)",
                "INSERT INTO alembic_version VALUES ('0009')",
                "CREATE TABLE runs (id VARCHAR(26) PRIMARY KEY)",
                "CREATE TABLE run_events (id VARCHAR(26) PRIMARY KEY, "
                "run_id VARCHAR(26) REFERENCES runs (id) ON DELETE CASCADE)",
                "CREATE TABLE samples (id VARCHAR(26) PRIMARY KEY, run_test_id VARCHAR(26))",
                "CREATE TABLE metric_values (id VARCHAR(26) PRIMARY KEY, "
                "sample_id VARCHAR(26) REFERENCES samples (id) ON DELETE CASCADE)",
                "INSERT INTO samples SELECT 's' || g, CASE WHEN g < 3 THEN 'RT1' ELSE 'RT2' END "
                "FROM generate_series(0, 4) AS g",
                "INSERT INTO metric_values VALUES ('m0', 's0'), ('m1', 's1')",
            ):
                connection.execute(text(statement))
        url = engine.url.render_as_string(hide_password=False)
        executable, _config, _document = fake_application(tmp_path, "freeweight", database_url=url)
        file = tmp_path / "console.toml"
        file.write_text(
            f'[apps.freeweight]\nexecutable = "{executable}"\nbase_url = "http://127.0.0.1:9"\n',
            encoding="utf-8",
        )
        database = Database.from_url(f"sqlite:///{tmp_path / 'weightroom.sqlite3'}")
        ensure_ready(database, auto_migrate=True)
        rig = Rig(
            settings=load_settings(config_path=file).settings,
            database=database,
            controller=FakeSystemdController(states={"freeweight.service": "inactive"}),
            path=tmp_path / "unused",
            backups=tmp_path / "backups",
        )
        dry = rig.dry()
        runs = rig.dry("DELETE FROM runs")  # the reach reflected on PostgreSQL; ADR-0134 rule 1
        assert [(one.table, one.action) for one in runs.reached] == [
            ("run_events", "ON DELETE CASCADE")
        ]
        result = rig.write(dry_run_id=str(dry.dry_run_id))
        with engine.connect() as connection:
            left = connection.execute(text("SELECT count(*) FROM samples")).scalar_one()
            metrics = connection.execute(text("SELECT count(*) FROM metric_values")).scalar_one()
    assert dry.counts is not None
    assert (dry.counts.rows, dry.counts.changes) == (3, {"metric_values": -2})
    assert (result.counts.rows, left, metrics) == (3, 2, 0)
    assert result.backup_path.suffix == ".dump"
    assert [row.outcome for row in rig.rows()] == ["ok"]
