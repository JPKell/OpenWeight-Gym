"""weightroom.services.overview — figures and the primary table, API or database, never a fake 0.

No committed binary fixture: every synthetic database here is built at test time with raw
``sqlite3`` (the FreeWeight M6 lesson recorded in memory — a gitignored binary fixture is how a
CI run goes red for a reason nobody in the diff can see).
"""

from __future__ import annotations

import sqlite3
import textwrap
from pathlib import Path

import httpx
import respx

from weightroom.config import load_settings
from weightroom.services.apps import AppView
from weightroom.services.database import Database, ensure_ready
from weightroom.services.overview import overview_for

APP = "loadcoach"
BASE_URL = "http://127.0.0.1:8766"


def _fake_cli(tmp_path: Path, *, database_url: str) -> Path:
    """A one-file ``loadcoach`` stand-in that answers ``config show --json`` and nothing else."""
    script = tmp_path / "loadcoach"
    script.write_text(
        textwrap.dedent(f"""\
            #!/bin/sh
            if [ "$1 $2 $3" = "config show --json" ]; then
              echo '{{"values": {{"storage": {{"database_url": "{database_url}"}}}}}}'
              exit 0
            fi
            exit 1
            """)
    )
    script.chmod(0o755)
    return script


def _synthetic_db(tmp_path: Path, *, revision: str, model_rows: int = 2) -> str:
    path = tmp_path / "loadcoach.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    connection.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
    connection.execute("CREATE TABLE models (id INTEGER PRIMARY KEY, canonical_id TEXT)")
    connection.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE routing_decisions (id INTEGER PRIMARY KEY)")
    for i in range(model_rows):
        connection.execute("INSERT INTO models (canonical_id) VALUES (?)", (f"model-{i}",))
    connection.commit()
    connection.close()
    return f"sqlite:///{path}"


def _console_database(tmp_path: Path) -> Database:
    """A fresh WeightRoomGym database, migrated to head — migration 0001 already seeds
    ``loadcoach``'s known revision as ``0015`` (row W1), which every test below reuses rather
    than re-inserting it (a second row for the same ``(app, revision)`` violates the primary key).
    """
    database = Database.from_url(f"sqlite:///{tmp_path / 'weightroom.sqlite3'}")
    ensure_ready(database, auto_migrate=True)
    return database


def _view(*, installed: bool, running: bool, reachable: bool, executable: str | None) -> AppView:
    return AppView(
        name=APP,
        installed=installed,
        executable=executable,
        unit="loadcoach.service",
        unit_state="active" if running else "inactive",
        uptime_seconds=120.0 if running else None,
        restarts=0,
        base_url=BASE_URL,
        version="1.3.1" if reachable else None,
        api_version="v1" if reachable else None,
        verdict="ok" if reachable else "unreadable",
    )


def _settings(tmp_path: Path, *, executable: Path | None):  # type: ignore[no-untyped-def]
    text = ""
    if executable is not None:
        text = f'[apps.loadcoach]\nexecutable = "{executable}"\nbase_url = "{BASE_URL}"\n'
    config = tmp_path / "console.toml"
    config.write_text(text)
    return load_settings(config_path=config).settings


@respx.mock
def test_running_and_reachable_reads_figures_from_the_api_and_the_table_from_the_database(
    tmp_path: Path,
) -> None:
    respx.get(f"{BASE_URL}/api/v1/system/status").mock(
        return_value=httpx.Response(
            200, json={"active": 3, "oldest_queued_age_seconds": 12.5, "starving": False}
        )
    )
    database_url = _synthetic_db(tmp_path, revision="0015")
    executable = _fake_cli(tmp_path, database_url=database_url)
    settings = _settings(tmp_path, executable=executable)
    console_db = _console_database(tmp_path)
    view = _view(installed=True, running=True, reachable=True, executable=str(executable))

    overview = overview_for(
        APP, view, settings=settings, database=console_db, client=httpx.Client()
    )

    assert overview.source == "api"
    figures = {f.label: f.value for f in overview.figures}
    assert figures["Active"] == "3"
    assert figures["Starving"] == "False"
    assert overview.table.caption == "models"
    assert len(overview.table.rows) == 2


def test_stopped_reads_both_figures_and_the_table_from_the_database_at_a_known_revision(
    tmp_path: Path,
) -> None:
    database_url = _synthetic_db(tmp_path, revision="0015", model_rows=1)
    executable = _fake_cli(tmp_path, database_url=database_url)
    settings = _settings(tmp_path, executable=executable)
    console_db = _console_database(tmp_path)
    view = _view(installed=True, running=False, reachable=False, executable=str(executable))

    overview = overview_for(
        APP, view, settings=settings, database=console_db, client=httpx.Client()
    )

    assert overview.source == "database"
    assert "revision 0015" in overview.source_detail
    figures = {f.label: f.value for f in overview.figures}
    assert figures["Models"] == "1"
    assert figures["Jobs"] == "0"
    assert overview.table.rows


def test_an_unknown_revision_degrades_the_table_by_name_never_zero(tmp_path: Path) -> None:
    database_url = _synthetic_db(tmp_path, revision="9999")
    executable = _fake_cli(tmp_path, database_url=database_url)
    settings = _settings(tmp_path, executable=executable)
    console_db = _console_database(tmp_path)  # 9999 is not in the known set
    view = _view(installed=True, running=False, reachable=False, executable=str(executable))

    overview = overview_for(
        APP, view, settings=settings, database=console_db, client=httpx.Client()
    )

    assert overview.source == "none"
    assert "9999" in overview.source_detail
    assert "9999" in (overview.table.empty_message or "")
    assert all(figure.value == "—" for figure in overview.figures)


def test_neither_api_nor_database_renders_every_figure_as_a_dash(tmp_path: Path) -> None:
    settings = _settings(tmp_path, executable=None)  # not installed
    console_db = _console_database(tmp_path)
    view = _view(installed=False, running=False, reachable=False, executable=None)

    overview = overview_for(
        APP, view, settings=settings, database=console_db, client=httpx.Client()
    )

    assert overview.source == "none"
    assert all(figure.value == "—" for figure in overview.figures)
    assert overview.table.rows == ()
    assert overview.table.empty_message is not None


@respx.mock
def test_a_status_call_that_fails_while_running_still_renders_dashes_not_a_crash(
    tmp_path: Path,
) -> None:
    respx.get(f"{BASE_URL}/api/v1/system/status").mock(side_effect=httpx.ConnectError("refused"))
    database_url = _synthetic_db(tmp_path, revision="0015")
    executable = _fake_cli(tmp_path, database_url=database_url)
    settings = _settings(tmp_path, executable=executable)
    console_db = _console_database(tmp_path)
    view = _view(installed=True, running=True, reachable=True, executable=str(executable))

    overview = overview_for(
        APP, view, settings=settings, database=console_db, client=httpx.Client()
    )

    assert all(figure.value == "—" for figure in overview.figures)
