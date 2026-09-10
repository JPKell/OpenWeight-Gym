"""weightroom.domain.guard: each condition failed alone, the never-writable list, the lexer."""

from __future__ import annotations

import re
import sqlite3
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

import pytest

from weightroom.domain.guard import (
    NEVER_WRITABLE,
    ForeignKey,
    GuardAppRunning,
    GuardAuditFailed,
    GuardBackupFailed,
    GuardDryRunFailed,
    GuardError,
    GuardStatementRefused,
    GuardTableLocked,
    GuardTableMismatch,
    application_stopped,
    checklist,
    classify,
    dry_run_id,
    lock_for,
    reach,
    require_read,
    require_writable,
    require_write,
    tokenize,
    typed_mismatch,
)

ROOT = Path(__file__).resolve().parents[2]
ADR_0124 = (
    ROOT
    / "docs"
    / "adr"
    / "0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md"
)
FIXTURES = ROOT / "tests" / "fixtures" / "databases"
APPS = ("freeweight", "loadcoach", "ideapress", "promptcadence")
KNOWN = {"freeweight": "0009", "loadcoach": "0015", "ideapress": "0010", "promptcadence": "0011"}
ENGINE_CATALOG = "Engine catalog"


# --- The never-writable list is ADR-0124's table, as data --------------------------------------


def _adr_table() -> dict[str, dict[str, set[str]]]:
    """The record's own Markdown table: class → application → names."""
    text = ADR_0124.read_text(encoding="utf-8")
    table = text.split("### Tables that are never written from WeightRoomGym", 1)[1]
    parsed: dict[str, dict[str, set[str]]] = {}
    for line in table.splitlines():
        if not line.startswith("| ") or "`" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        parsed[cells[0]] = {
            app: set(re.findall(r"`([a-z_*]+)`", cells[2 + position]))
            for position, app in enumerate(APPS)
        }
    return parsed


def test_the_never_writable_data_is_adr_0124s_table_plus_the_engine_catalog() -> None:
    adr = _adr_table()
    ours = {
        lock.name: {app: set(lock.tables.get(app, ())) for app in APPS}
        for lock in NEVER_WRITABLE
        if lock.name != ENGINE_CATALOG
    }
    assert len(adr) == 8
    assert ours == adr


def _fixture_tables(app: str) -> set[str]:
    path = FIXTURES / f"{app}-{KNOWN[app]}.sqlite3"
    # immutable: a committed file nothing writes; plain mode=ro would leave -shm/-wal beside it.
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {str(row[0]) for row in rows}
    finally:
        connection.close()


@pytest.mark.parametrize("app", APPS)
def test_every_never_writable_name_is_a_table_in_the_fixture_database(app: str) -> None:
    tables = _fixture_tables(app)
    for lock in NEVER_WRITABLE:
        if lock.name == ENGINE_CATALOG:
            continue
        for pattern in lock.tables.get(app, ()):
            assert any(fnmatchcase(table, pattern) for table in tables), (app, pattern)


LOCKED_CASES = sorted(
    {
        (app, name.replace("*", "entries"))
        for lock in NEVER_WRITABLE
        for app, names in lock.tables.items()
        for name in names
    }
)


@pytest.mark.parametrize(("app", "table"), LOCKED_CASES)
def test_a_write_to_every_never_writable_table_is_refused_by_name(app: str, table: str) -> None:
    statement = classify(f"DELETE FROM {table} WHERE id = 'x'")  # noqa: S608 — the lock's own names
    with pytest.raises(GuardTableLocked) as refused:
        require_writable(app, statement)
    assert f"{table} is never writable from WeightRoomGym (ADR-0124)" in refused.value.message
    assert refused.value.details["table"] == table
    assert refused.value.details["condition"] is None


def test_update_routing_decisions_is_refused_by_name_plan_criterion_3() -> None:
    statement = classify("UPDATE routing_decisions SET reason = 'x' WHERE id = '01ROW'")
    with pytest.raises(GuardTableLocked, match="routing_decisions is never writable"):
        require_writable("loadcoach", statement)


def test_a_mounted_family_is_locked_only_where_it_is_mounted() -> None:
    assert lock_for("promptcadence", "ledger_entries") is not None
    assert lock_for("ideapress", "LEDGER_RUNS") is not None
    assert lock_for("loadcoach", "ledger_entries") is None
    assert lock_for("freeweight", "samples") is None
    require_writable("freeweight", classify("DELETE FROM samples WHERE id = 'x'"))


# --- What a write reaches ----------------------------------------------------------------------

FREEWEIGHT_KEYS = (
    ForeignKey("run_events", "runs", on_delete="CASCADE"),
    ForeignKey("run_tests", "runs", on_delete="CASCADE"),
    ForeignKey("samples", "run_tests", on_delete="CASCADE"),
    ForeignKey("metric_values", "samples", on_delete="CASCADE"),
    ForeignKey("calibration_samples", "samples", on_delete="SET NULL"),
    ForeignKey("runs", "models", on_delete="RESTRICT"),
)


def test_deleting_samples_reaches_their_children_and_no_locked_table() -> None:
    statement = classify("DELETE FROM samples WHERE run_test_id = 'x'")
    reached = reach(statement.written, statement.events, FREEWEIGHT_KEYS)
    assert {one.table: one.action for one in reached} == {
        "metric_values": "ON DELETE CASCADE",
        "calibration_samples": "ON DELETE SET NULL",
    }
    require_writable("freeweight", statement, reached)


def test_deleting_runs_removes_their_run_events_with_them_and_is_not_refused() -> None:
    # ADR-0134 rule 1: the events go with the run they describe; no stream is left to replay.
    statement = classify("DELETE FROM runs WHERE id = 'x'")
    reached = reach(statement.written, statement.events, FREEWEIGHT_KEYS)
    assert [one.table for one in reached][:2] == ["run_events", "run_tests"]
    assert reached[-1].path == ("runs", "run_tests", "samples", "calibration_samples")
    assert reached[0].as_json() == {
        "table": "run_events",
        "path": ["runs", "run_events"],
        "action": "ON DELETE CASCADE",
    }
    require_writable("freeweight", statement, reached)


def test_a_cascade_that_edits_an_event_log_is_refused_with_the_path() -> None:
    keys = (*FREEWEIGHT_KEYS, ForeignKey("run_events", "samples", on_delete="SET NULL"))
    statement = classify("DELETE FROM samples WHERE id = 'x'")
    with pytest.raises(GuardTableLocked) as refused:
        require_writable("freeweight", statement, reach(statement.written, statement.events, keys))
    assert refused.value.details["via"] == ["samples", "run_events"]
    assert refused.value.details["action"] == "ON DELETE SET NULL"
    assert "samples → run_events" in refused.value.message
    update = classify("UPDATE runs SET id = 'y' WHERE id = 'x'")
    cascading = (ForeignKey("run_events", "runs", on_delete="CASCADE", on_update="CASCADE"),)
    with pytest.raises(GuardTableLocked, match="ON UPDATE CASCADE"):
        require_writable("freeweight", update, reach(update.written, update.events, cascading))


def test_an_edit_is_never_hidden_behind_a_delete_of_the_same_event_log() -> None:
    keys = (*FREEWEIGHT_KEYS, ForeignKey("run_events", "samples", on_delete="SET NULL"))
    statement = classify("DELETE FROM runs WHERE id = 'x'")
    reached = reach(statement.written, statement.events, keys)
    events = next(one for one in reached if one.table == "run_events")
    assert (events.path, events.action) == (
        ("runs", "run_tests", "samples", "run_events"),
        "ON DELETE SET NULL",
    )
    with pytest.raises(GuardTableLocked, match="run_events"):
        require_writable("freeweight", statement, reached)


def test_a_cascade_into_queue_state_or_a_decision_record_is_still_refused() -> None:
    ideapress = (
        ForeignKey("stage_runs", "projects", on_delete="CASCADE"),
        ForeignKey("stage_events", "stage_runs", on_delete="CASCADE"),
    )
    projects = classify("DELETE FROM projects WHERE id = 'x'")
    with pytest.raises(GuardTableLocked) as refused:
        require_writable("ideapress", projects, reach(projects.written, projects.events, ideapress))
    assert refused.value.details["class"] == "Queue and lease state"
    plans = classify("DELETE FROM plans WHERE id = 'x'")
    approvals = (ForeignKey("plan_approvals", "plans", on_delete="CASCADE"),)
    with pytest.raises(GuardTableLocked, match="plan_approvals"):
        require_writable("promptcadence", plans, reach(plans.written, plans.events, approvals))


def test_an_update_follows_only_update_actions_and_an_insert_reaches_nothing() -> None:
    keys = (*FREEWEIGHT_KEYS, ForeignKey("tags", "samples", on_update="CASCADE"))
    update = classify("UPDATE samples SET score = 1")
    assert [one.table for one in reach(update.written, update.events, keys)] == ["tags"]
    insert = classify("INSERT INTO runs (id) VALUES ('x')")
    assert reach(insert.written, insert.events, keys) == ()


def test_a_set_null_is_followed_onward_as_an_update_and_a_cycle_terminates() -> None:
    keys = (
        ForeignKey("b", "a", on_delete="SET NULL"),
        ForeignKey("c", "b", on_update="CASCADE"),
        ForeignKey("a", "c", on_update="CASCADE", on_delete="CASCADE"),
    )
    statement = classify("DELETE FROM a")
    assert [one.table for one in reach(statement.written, statement.events, keys)] == ["b", "c"]


# --- The lexer and the statement ---------------------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT ';' FROM samples",
        'SELECT "a;b" FROM samples',
        "SELECT `a;b`, [c;d] FROM samples",
        "SELECT 1 FROM samples -- ; trailing comment",
        "SELECT /* ; */ 1 FROM samples",
        "SELECT $$;$$, $tag$ ; $tag$ FROM samples",
        "SELECT E'it\\';s' FROM samples",
        "SELECT 'it''s;' FROM samples;",
    ],
)
def test_a_semicolon_inside_a_string_identifier_or_comment_is_one_statement(sql: str) -> None:
    assert classify(sql).tables == ("samples",)


@pytest.mark.parametrize(
    ("sql", "reason"),
    [
        ("SELECT 1; SELECT 2", "multiple_statements"),
        ("DELETE FROM samples; DELETE FROM runs", "multiple_statements"),
        ("SELECT 'abc", "an unterminated '…'"),
        ('SELECT "abc', 'an unterminated "…"'),
        ("SELECT 1 /* open", "an unterminated /* comment"),
        ("SELECT /* a /* b */ c */ 1", "a nested /* comment, which SQLite and PostgreSQL end"),
        ("SELECT $$x", "an unterminated dollar-quoted string"),
        ("SELECT [x", "an unterminated [identifier]"),
    ],
)
def test_what_cannot_be_read_exactly_is_refused(sql: str, reason: str) -> None:
    with pytest.raises(GuardStatementRefused) as refused:
        classify(sql)
    assert str(refused.value.details["reason"]).startswith(reason)


@pytest.mark.parametrize(
    ("sql", "keyword"),
    [
        ("CREATE TABLE t (a)", "CREATE"),
        ("ALTER TABLE samples ADD COLUMN x", "ALTER"),
        ("DROP TABLE samples", "DROP"),
        ("PRAGMA foreign_keys = OFF", "PRAGMA"),
        ("vacuum", "VACUUM"),
        ("ATTACH DATABASE 'x.db' AS other", "ATTACH"),
        ("BEGIN", "BEGIN"),
        ("TRUNCATE samples", "TRUNCATE"),
        ("VALUES (1)", "VALUES"),
        ("EXPLAIN DELETE FROM samples", "EXPLAIN"),
    ],
)
def test_ddl_pragma_vacuum_and_everything_but_select_and_dml_are_refused_by_name(
    sql: str, keyword: str
) -> None:
    with pytest.raises(GuardStatementRefused) as refused:
        classify(sql)
    assert refused.value.details["keyword"] == keyword
    assert refused.value.message.startswith(f"{keyword} is refused by name")


@pytest.mark.parametrize("sql", ["", "  ;  ", "42", "WITH x AS (SELECT 1)"])
def test_an_empty_or_verbless_statement_is_refused(sql: str) -> None:
    with pytest.raises(GuardStatementRefused):
        classify(sql)


@pytest.mark.parametrize(
    ("sql", "verb", "tables", "written"),
    [
        (
            "DELETE FROM samples WHERE run_test_id IN "
            "(SELECT id FROM run_tests WHERE run_id = '01RUN')",
            "DELETE",
            ("samples", "run_tests"),
            ("samples",),
        ),
        (
            "UPDATE units AS u SET title = 'x' FROM projects p WHERE p.id = u.project_id",
            "UPDATE",
            ("units", "projects"),
            ("units",),
        ),
        (
            "INSERT INTO feedback (job_id, rating) SELECT j.id, 1 FROM jobs j "
            "JOIN job_attempts a ON a.job_id = j.id",
            "INSERT",
            ("feedback", "jobs", "job_attempts"),
            ("feedback",),
        ),
        (
            "WITH doomed AS (SELECT id FROM samples WHERE score IS NULL) "
            "DELETE FROM samples WHERE id IN (SELECT id FROM doomed)",
            "DELETE",
            ("samples",),
            ("samples",),
        ),
        ('delete from "Samples" where 1', "DELETE", ("Samples",), ("Samples",)),
        ("DELETE FROM main.SAMPLES", "DELETE", ("samples",), ("samples",)),
        (
            "SELECT extract(epoch FROM created_at), s.id FROM samples s, run_tests AS rt "
            "WHERE rt.id = s.run_test_id",
            "SELECT",
            ("samples", "run_tests"),
            (),
        ),
        ("SELECT * FROM jobs FOR NO KEY UPDATE", "SELECT", ("jobs",), ()),
        (
            "INSERT INTO feedback (id) VALUES ('x') ON CONFLICT (id) DO UPDATE SET rating = 2",
            "INSERT",
            ("feedback",),
            ("feedback",),
        ),
        (
            "WITH d AS (DELETE FROM routing_decisions RETURNING id) SELECT count(*) FROM d",
            "SELECT",
            ("routing_decisions",),
            ("routing_decisions",),
        ),
        (
            "DELETE FROM samples USING run_tests WHERE run_tests.id = samples.run_test_id",
            "DELETE",
            ("samples", "run_tests"),
            ("samples",),
        ),
        ("INSERT OR REPLACE INTO feedback VALUES ('x')", "INSERT", ("feedback",), ("feedback",)),
        ("REPLACE INTO feedback VALUES (1)", "REPLACE", ("feedback",), ("feedback",)),
        ("UPDATE OR IGNORE ONLY samples SET score = ?1", "UPDATE", ("samples",), ("samples",)),
        (
            "SELECT * FROM json_each('[1]') AS j(value) JOIN samples ON 1 "
            "LEFT JOIN (SELECT id FROM runs) r USING (id)",
            "SELECT",
            ("samples", "runs"),
            (),
        ),
        (
            "MERGE INTO feedback f USING jobs j ON f.job_id = j.id "
            "WHEN MATCHED THEN UPDATE SET rating = 1 WHEN NOT MATCHED THEN DELETE",
            "MERGE",
            ("feedback", "jobs"),
            ("feedback",),
        ),
        (
            "(SELECT id FROM samples WHERE score > $1 AND ordinal < 1.5e3 AND x = :name "
            "AND y = @v AND z::text = 'a')",
            "SELECT",
            ("samples",),
            (),
        ),
    ],
)
def test_the_verb_the_tables_named_and_the_tables_written(
    sql: str, verb: str, tables: tuple[str, ...], written: tuple[str, ...]
) -> None:
    statement = classify(sql)
    assert (statement.verb, statement.tables, statement.written) == (verb, tables, written)


def test_the_foreign_key_events_follow_what_the_statement_does() -> None:
    assert classify("DELETE FROM a").events == {"DELETE"}
    assert classify("UPDATE a SET b = 1").events == {"UPDATE"}
    assert classify("INSERT INTO a VALUES (1)").events == frozenset()
    assert classify("INSERT OR REPLACE INTO a VALUES (1)").events == {"DELETE"}
    assert classify("INSERT INTO a VALUES (1) ON CONFLICT DO UPDATE SET b = 2").events == {"UPDATE"}
    assert classify("MERGE INTO a USING b ON 1 WHEN MATCHED THEN DELETE").events == {
        "DELETE",
        "UPDATE",
    }


def test_the_console_takes_only_a_select_and_the_guard_only_a_write() -> None:
    select = classify("SELECT count(*) FROM samples")
    delete = classify("DELETE FROM samples")
    hidden = classify("WITH d AS (DELETE FROM samples RETURNING id) SELECT * FROM d")
    assert require_read(select) is select
    assert require_write(delete) is delete
    for refused_read in (delete, hidden):
        with pytest.raises(GuardStatementRefused, match="read-only connection"):
            require_read(refused_read)
    for refused_write in (select, hidden):
        with pytest.raises(GuardStatementRefused, match="whose own verb is the write"):
            require_write(refused_write)


def test_tokens_keep_quoted_names_as_written_and_drop_comments() -> None:
    tokens = tokenize('SELECT "Mixed" -- gone\nFROM t')
    assert [(token.kind, token.text) for token in tokens] == [
        ("word", "SELECT"),
        ("identifier", "Mixed"),
        ("word", "FROM"),
        ("word", "t"),
    ]
    assert tokens[1].keyword == ""


# --- The five conditions, each failed alone ----------------------------------------------------

ALL_PASS: dict[str, Any] = {
    "unit_state": "inactive",
    "port_open": False,
    "backup_path": "/data/backups/freeweight/20260910T120000Z-guarded-write.sqlite3",
    "dry_run_count": 412,
    "tables": ("samples", "run_tests"),
    "typed": ("run_tests", " samples "),
    "audit_id": "01AUDIT0000000000000000000",
}

FAILING_ALONE: dict[int, dict[str, Any]] = {
    1: {"unit_state": "active", "port_open": True},
    2: {"backup_path": None, "backup_error": "No space left to write backup"},
    3: {"dry_run_count": None, "dry_run_error": "no such column: run_id"},
    4: {"typed": ("samples",)},
    5: {"audit_id": None, "audit_error": "database is locked"},
}


def test_every_condition_passes_on_the_facts_of_a_good_write() -> None:
    conditions = checklist(**ALL_PASS)
    assert [condition.verdict for condition in conditions] == ["pass"] * 5
    assert conditions[0].evidence == "unit inactive, port closed"
    assert conditions[2].evidence == "412 rows"
    assert conditions[0].as_json()["condition"] == 1


@pytest.mark.parametrize("number", sorted(FAILING_ALONE))
def test_each_condition_fails_alone(number: int) -> None:
    conditions = checklist(**{**ALL_PASS, **FAILING_ALONE[number]})
    verdicts = {condition.number: condition.verdict for condition in conditions}
    assert verdicts == {one: "fail" if one == number else "pass" for one in range(1, 6)}


def test_before_the_write_runs_conditions_2_4_and_5_are_pending_not_passed() -> None:
    conditions = checklist(unit_state="inactive", port_open=False, tables=("samples",))
    assert [condition.verdict for condition in conditions] == [
        "pass",
        "pending",
        "pending",
        "pending",
        "pending",
    ]
    assert conditions[3].evidence == "type samples"


@pytest.mark.parametrize(
    ("unit_state", "port_open", "stopped"),
    [
        ("inactive", False, True),
        ("failed", False, True),
        ("absent", False, True),
        ("unsupported", False, True),
        ("inactive", True, False),  # started by hand in a terminal
        ("inactive", None, False),  # the port could not be tried: no evidence
        ("activating", False, False),
        ("deactivating", False, False),
        ("active", False, False),
    ],
)
def test_stopped_is_the_unit_and_the_port_together(
    unit_state: str, port_open: bool | None, stopped: bool
) -> None:
    assert application_stopped(unit_state=unit_state, port_open=port_open) is stopped


def test_typed_names_match_exactly_and_a_name_not_in_the_statement_refuses() -> None:
    assert typed_mismatch(("samples",), ("samples",)) == ((), ())
    assert typed_mismatch(("samples",), ("Samples",)) == (("samples",), ("Samples",))
    assert typed_mismatch(("samples",), ("samples", "runs", "")) == ((), ("runs",))
    evidence = checklist(**{**ALL_PASS, "typed": ("runs",)})[3].evidence
    assert evidence == "not typed: run_tests, samples; not in the statement: runs"


@pytest.mark.parametrize(
    ("error", "code", "condition"),
    [
        (GuardAppRunning, "GUARD_APP_RUNNING", 1),
        (GuardBackupFailed, "GUARD_BACKUP_FAILED", 2),
        (GuardDryRunFailed, "GUARD_DRY_RUN_FAILED", 3),
        (GuardTableMismatch, "GUARD_TABLE_MISMATCH", 4),
        (GuardAuditFailed, "GUARD_AUDIT_FAILED", 5),
        (GuardTableLocked, "GUARD_TABLE_LOCKED", None),
        (GuardStatementRefused, "GUARD_STATEMENT_REFUSED", None),
    ],
)
def test_each_refusal_carries_its_code_and_its_condition_number(
    error: type[GuardError], code: str, condition: int | None
) -> None:
    raised = error("refused", details={"app": "freeweight"})
    assert raised.code == code
    assert raised.details == {"condition": condition, "adr": "ADR-0124", "app": "freeweight"}


def test_the_dry_run_id_binds_the_application_the_text_the_count_and_the_reach() -> None:
    base: dict[str, Any] = {"app": "freeweight", "statement": "DELETE FROM samples", "count": 412}
    first = dry_run_id(**base, reached={"metric_values": 1200, "calibration_samples": None})
    assert first == dry_run_id(**base, reached={"calibration_samples": None, "metric_values": 1200})
    assert len(first) == 32
    assert first != dry_run_id(**{**base, "count": 413}, reached={})
    assert first != dry_run_id(**base, reached={"metric_values": 1201, "calibration_samples": None})
    assert dry_run_id(**base, reached={}) != dry_run_id(**{**base, "app": "loadcoach"}, reached={})


@pytest.mark.parametrize(
    ("sql", "tables", "written"),
    [
        (
            "WITH RECURSIVE a(n) AS NOT MATERIALIZED (SELECT 1), b AS MATERIALIZED "
            "(SELECT n FROM a) DELETE FROM samples WHERE id IN (SELECT n FROM b)",
            ("samples",),
            ("samples",),
        ),
        ("SELECT CAST(x AS timestamp WITH TIME ZONE) FROM samples", ("samples",), ()),
        ("SELECT * FROM ONLY samples", ("samples",), ()),
        ("SELECT 1 FROM ONLY", (), ()),
        ("SELECT 1 FROM 'not a table'", (), ()),
        ("SELECT count(*) FROM (SELECT 1", (), ()),
        ("SELECT 1) FROM samples", ("samples",), ()),
        ("INSERT INTO (SELECT 1)", (), ()),
    ],
)
def test_malformed_and_unusual_shapes_never_trip_the_lexer(
    sql: str, tables: tuple[str, ...], written: tuple[str, ...]
) -> None:
    statement = classify(sql)
    assert (statement.tables, statement.written) == (tables, written)


def test_a_table_reached_twice_is_reported_once_by_its_shortest_path() -> None:
    keys = (
        ForeignKey("b", "a", on_delete="CASCADE"),
        ForeignKey("c", "a", on_delete="CASCADE"),
        ForeignKey("d", "b", on_delete="CASCADE"),
        ForeignKey("d", "c", on_delete="CASCADE"),
    )
    reached = reach(("a",), frozenset({"DELETE"}), keys)
    assert [(one.table, one.path) for one in reached] == [
        ("b", ("a", "b")),
        ("c", ("a", "c")),
        ("d", ("a", "b", "d")),
    ]
