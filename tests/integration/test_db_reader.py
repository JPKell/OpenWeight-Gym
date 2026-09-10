"""services/db_reader over copies of the committed fixture databases, and over PostgreSQL.

The SQLite half reads each application's real schema at the revision ``known_revisions`` seeds;
the PostgreSQL half (``-m integration``, the db-matrix job) builds a small schema of the same shape
on a real server, because an application's migration history is not WeightRoomGym's to run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import DBAPIError, OperationalError
from weightsdb.testing import temporary_postgres

from tests.support import fake_application, fill_rows, fixture_database
from weightroom.config import Settings, load_settings
from weightroom.domain.guard import GuardStatementRefused
from weightroom.services.database import Database, ensure_ready
from weightroom.services.db_reader import (
    AppDatabase,
    AppDatabaseUnavailable,
    DatabaseUrlCache,
    ReadFailed,
    SchemaUnknown,
    TableUnknown,
    cell_text,
    effective_database_url,
    list_tables,
    open_app_database,
    revision_summary,
    run_query,
    table_page,
)
from weightroom.services.processes import CommandResult, Runner

KNOWN = {"freeweight": "0009", "loadcoach": "0015", "ideapress": "0010", "promptcadence": "0011"}
WRITABLE = {
    "freeweight": "samples",
    "loadcoach": "feedback",
    "ideapress": "units",
    "promptcadence": "compactions",
}


def _own(tmp_path: Path) -> Database:
    database = Database.from_url(f"sqlite:///{tmp_path / 'weightroom.sqlite3'}")
    ensure_ready(database, auto_migrate=True)
    return database


def _settings(tmp_path: Path, app: str, database_url: str | None) -> Settings:
    executable, _config, _document = fake_application(tmp_path, app, database_url=database_url)
    file = tmp_path / "console.toml"
    file.write_text(f'[apps.{app}]\nexecutable = "{executable}"\n', encoding="utf-8")
    return load_settings(config_path=file).settings


def _open(tmp_path: Path, app: str, url: str | None, **options: Any) -> AppDatabase:  # noqa: ANN401
    return open_app_database(
        _settings(tmp_path, app, url),
        _own(tmp_path),
        app,
        urls=DatabaseUrlCache(),
        now=0.0,
        **options,
    )


def _samples(path: Path, count: int) -> None:
    fill_rows(
        path,
        "samples",
        [
            {
                "id": f"01SAMPLE{index:018d}",
                "ordinal": index,
                "status": "failed" if index % 10 == 0 else "completed",
            }
            for index in range(count)
        ],
    )


@pytest.mark.parametrize("app", sorted(KNOWN))
def test_each_fixture_opens_read_only_at_its_known_revision_with_its_locks(
    tmp_path: Path, app: str
) -> None:
    path = fixture_database(tmp_path, f"{app}-{KNOWN[app]}")
    with _open(tmp_path, app, f"sqlite:///{path}") as handle:
        assert (handle.revision.found, handle.revision.is_known) == (KNOWN[app], True)
        assert handle.revision.dialect == "sqlite"
        tables = {one.name: one for one in list_tables(handle)}
    assert tables["alembic_version"].rows == 1
    assert not tables["alembic_version"].writable
    assert "never writable from WeightRoomGym (ADR-0124)" in str(tables["api_tokens"].reason)
    assert all(one.rows is not None for one in tables.values())
    writable = tables[WRITABLE[app]].as_json()
    assert (writable["writable"], writable["reason"], writable["lock_class"]) == (True, None, None)


def test_the_reader_connection_refuses_a_write_the_lexer_never_saw(tmp_path: Path) -> None:
    path = fixture_database(tmp_path, "freeweight-0009")
    with _open(tmp_path, "freeweight", f"sqlite:///{path}") as handle:
        with (
            handle.engine.connect() as connection,
            pytest.raises(OperationalError, match="readonly"),
        ):
            connection.exec_driver_sql("DELETE FROM samples")


def test_an_unknown_revision_refuses_by_name_and_still_reports_itself(tmp_path: Path) -> None:
    path = fixture_database(tmp_path, "loadcoach-unknown-9999")
    with pytest.raises(SchemaUnknown) as refused:
        _open(tmp_path, "loadcoach", f"sqlite:///{path}")
    assert refused.value.details == {"app": "loadcoach", "found": "9999", "known": ["0015"]}
    assert "revision 9999 is not known to WeightRoomGym" in refused.value.message
    with _open(tmp_path, "loadcoach", f"sqlite:///{path}", require_known=False) as handle:
        assert handle.revision.as_json()["known"] is False
        assert handle.revision.as_json()["known_revisions"] == ["0015"]


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        (None, "did not answer the expected shape"),
        ("sqlite:///{tmp}/absent.sqlite3", "would not open read-only"),
        ("sqlite:///:memory:", "in-memory"),
        ("mysql://user@host/db", "neither SQLite nor PostgreSQL"),
    ],
)
def test_a_database_that_cannot_be_located_or_opened_says_why(
    tmp_path: Path, url: str | None, reason: str
) -> None:
    resolved = None if url is None else url.replace("{tmp}", str(tmp_path))
    with pytest.raises(AppDatabaseUnavailable, match=reason):
        _open(tmp_path, "freeweight", resolved)
    settings = _settings(tmp_path, "freeweight", resolved)
    revision, why = revision_summary(
        settings, _own(tmp_path), "freeweight", urls=DatabaseUrlCache(), now=0.0
    )
    assert revision is None and reason in str(why)


def test_the_effective_url_reads_both_config_show_shapes_and_says_why_it_cannot(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, "ideapress", None)

    def answering(stdout: str, returncode: int = 0) -> Runner:
        return lambda argv, env, timeout: CommandResult(
            tuple(argv), returncode=returncode, stdout=stdout, stderr="boom"
        )

    new = '{"values": {"storage": {"database_url": "sqlite:////x.sqlite3"}}}'
    old = '{"settings": {"storage": {"database_url": "sqlite:////y.sqlite3"}}}'
    unset = '{"values": {"storage": {"database_url": null}}}'
    assert effective_database_url(settings, "ideapress", runner=answering(new)) == (
        "sqlite:////x.sqlite3",
        None,
    )
    assert effective_database_url(settings, "ideapress", runner=answering(old))[0] == (
        "sqlite:////y.sqlite3"
    )
    assert effective_database_url(settings, "ideapress", runner=answering(unset)) == (
        None,
        "no database configured",
    )
    assert "boom" in str(effective_database_url(settings, "ideapress", runner=answering("", 2))[1])


def test_the_url_is_asked_once_a_minute_and_a_failure_is_cached_too() -> None:
    calls: list[int] = []

    def read() -> tuple[str | None, str | None]:
        calls.append(1)
        return None, "not installed"

    cache = DatabaseUrlCache(ttl_seconds=60.0)
    assert cache.get("freeweight", now=0.0, read=read) == (None, "not installed")
    cache.get("freeweight", now=59.0, read=read)
    assert len(calls) == 1
    cache.get("freeweight", now=60.0, read=read)
    cache.get("freeweight", now=61.0, read=read, refresh=True)
    assert len(calls) == 3


def test_a_page_of_rows_is_sorted_filtered_and_typed(tmp_path: Path) -> None:
    path = fixture_database(tmp_path, "freeweight-0009")
    _samples(path, 250)
    with _open(tmp_path, "freeweight", f"sqlite:///{path}") as handle:
        first = table_page(handle, "samples")
        third = table_page(handle, "samples", page=3)
        by_ordinal = table_page(handle, "samples", sort="ordinal", descending=True, page_rows=5)
        errors = table_page(handle, "samples", column_name="status", contains="fail")
        literal = table_page(handle, "samples", column_name="status", contains="%")
        reversed_key = table_page(handle, "samples", descending=True, page=0)
    assert (len(first.rows), first.total, first.pages) == (100, 250, 3)
    assert len(third.rows) == 50
    names = [one.name for one in first.columns]
    assert first.rows[0][names.index("id")] == "01SAMPLE000000000000000000"
    assert reversed_key.page == 1
    assert reversed_key.rows[0][names.index("id")] == "01SAMPLE000000000000000249"
    assert [row[names.index("ordinal")] for row in by_ordinal.rows] == [249, 248, 247, 246, 245]
    assert errors.total == 25
    assert literal.total == 0  # a % typed into the filter is text, not a pattern
    columns = {one.name: one for one in first.columns}
    assert columns["id"].primary_key and columns["id"].type == "VARCHAR(26)"
    assert columns["ordinal"].numeric and not columns["status"].numeric
    assert first.table.writable
    body = first.as_json()
    assert (body["pages"], body["filter"], body["columns"][0]["name"]) == (3, None, "id")


def test_the_grid_refuses_an_unknown_table_or_column(tmp_path: Path) -> None:
    path = fixture_database(tmp_path, "freeweight-0009")
    with _open(tmp_path, "freeweight", f"sqlite:///{path}") as handle:
        with pytest.raises(TableUnknown):
            table_page(handle, "nope")
        with pytest.raises(ReadFailed, match="'nope' is not a column of samples"):
            table_page(handle, "samples", sort="nope")
        with pytest.raises(ReadFailed, match="column takes one of"):
            table_page(handle, "samples", column_name="nope", contains="x")


def test_the_console_runs_one_select_capped_and_refuses_everything_else(tmp_path: Path) -> None:
    path = fixture_database(tmp_path, "freeweight-0009")
    _samples(path, 250)
    with _open(tmp_path, "freeweight", f"sqlite:///{path}") as handle:
        counted = run_query(handle, "SELECT count(*) AS n FROM samples;")
        capped = run_query(handle, "SELECT id FROM samples ORDER BY id", row_cap=10)
        blob = run_query(handle, "SELECT X'0102' AS b, NULL AS n")
        for sql in ("DELETE FROM samples", "PRAGMA writable_schema = 1", "SELECT 1; SELECT 2"):
            with pytest.raises(GuardStatementRefused):
                run_query(handle, sql)
        with pytest.raises(ReadFailed, match="refused the statement: no such column"):
            run_query(handle, "SELECT nope FROM samples")
    assert (counted.rows, counted.columns, counted.truncated) == (((250,),), ("n",), False)
    assert (len(capped.rows), capped.truncated) == (10, True)
    assert blob.rows == (("<2 bytes>", None),)
    body = counted.as_json()
    assert (body["tables"], body["row_cap"], body["row_count"]) == (["samples"], 10_000, 1)


def test_a_statement_past_the_timeout_is_interrupted(tmp_path: Path) -> None:
    path = fixture_database(tmp_path, "freeweight-0009")
    endless = (
        "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT count(*) FROM c"
    )
    with _open(tmp_path, "freeweight", f"sqlite:///{path}", timeout_seconds=0.05) as handle:
        with pytest.raises(ReadFailed, match="ran past 0.05 s"):
            run_query(handle, endless)


def test_a_cell_is_shown_as_null_json_or_cut_text() -> None:
    assert cell_text(None) == "NULL"
    assert cell_text({"a": [1, "é"]}) == '{"a": [1, "é"]}'
    assert cell_text("x" * 200, limit=10) == "x" * 9 + "…"
    assert cell_text(0) == "0"


@pytest.mark.integration
def test_postgresql_is_read_only_paged_filtered_and_timed_out(tmp_path: Path) -> None:
    with temporary_postgres() as engine:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
            )
            connection.exec_driver_sql("INSERT INTO alembic_version VALUES ('0015')")
            connection.exec_driver_sql(
                "CREATE TABLE feedback (id VARCHAR(26) PRIMARY KEY, rating INTEGER, note TEXT, "
                "created_at TIMESTAMPTZ DEFAULT now(), body JSONB)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE routing_decisions (id VARCHAR(26) PRIMARY KEY)"
            )
            connection.exec_driver_sql(
                "INSERT INTO feedback (id, rating, note, body) SELECT lpad(g::text, 26, '0'), "
                "mod(g, 5), 'note ' || g, jsonb_build_object('g', g) "
                "FROM generate_series(1, 150) AS g"
            )
        url = engine.url.render_as_string(hide_password=False)
        with _open(tmp_path, "loadcoach", url, timeout_seconds=0.5) as handle:
            assert (handle.revision.dialect, handle.revision.is_known) == ("postgresql", True)
            assert ":***@" in handle.revision.database_url  # the credential never leaves
            tables = {one.name: one for one in list_tables(handle)}
            page = table_page(handle, "feedback", page=2, sort="rating", descending=True)
            filtered = table_page(handle, "feedback", column_name="note", contains="note 14")
            counted = run_query(handle, "SELECT count(*) FROM feedback WHERE note LIKE 'note 1%'")
            typed = run_query(handle, "SELECT created_at, body FROM feedback ORDER BY id LIMIT 1")
            with handle.engine.connect() as connection:
                with pytest.raises(DBAPIError, match="read-only transaction"):
                    connection.exec_driver_sql("DELETE FROM feedback")
            with pytest.raises(ReadFailed, match="ran past 0.5 s"):
                run_query(handle, "SELECT pg_sleep(2)")
    assert (tables["feedback"].rows, tables["feedback"].writable) == (150, True)
    assert not tables["routing_decisions"].writable
    assert (len(page.rows), page.total, page.pages) == (50, 150, 2)
    assert filtered.total == 11  # note 14 and note 140 … 149
    assert counted.rows == ((62,),)  # note 1, 10–19 and 100–150: a literal % reached the server
    assert isinstance(typed.rows[0][0], str) and typed.rows[0][1] == {"g": 1}
