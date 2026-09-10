"""services/db_curated.py's row-W8 additions: WeightRoomGym's own curated verbs, and reading an
application's own ``backups/`` directory (never the guarded-write one, ``services/db_guard.py``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support import fake_application, fixture_database
from weightroom.config import load_settings
from weightroom.services.database import Database, ensure_ready
from weightroom.services.db_curated import (
    CuratedRefused,
    application_backups,
    run_self_curated,
    self_backups,
)
from weightroom.services.db_reader import DatabaseUrlCache


def _own(tmp_path: Path) -> Database:
    database = Database.from_url(f"sqlite:///{tmp_path / 'weightroom.sqlite3'}")
    ensure_ready(database, auto_migrate=True)
    return database


def test_self_status_reports_the_real_database(tmp_path: Path) -> None:
    database = _own(tmp_path)
    result = run_self_curated(database, "status")
    assert result.ok is True
    assert result.app == "weightroom"
    assert result.output["dialect"] == "sqlite"
    assert result.output["is_at_head"] is True


def test_self_backup_writes_a_file_and_reports_it(tmp_path: Path) -> None:
    database = _own(tmp_path)
    result = run_self_curated(database, "backup")
    assert result.ok is True
    assert Path(result.output["path"]).is_file()


def test_self_upgrade_at_head_is_a_no_op_and_still_ok(tmp_path: Path) -> None:
    database = _own(tmp_path)
    result = run_self_curated(database, "upgrade")
    assert result.ok is True
    assert result.output["from_revision"] == result.output["to_revision"]


def test_self_restore_is_always_refused(tmp_path: Path) -> None:
    database = _own(tmp_path)
    with pytest.raises(CuratedRefused, match="cannot restore its own database"):
        run_self_curated(database, "restore")


def test_self_unknown_verb_is_refused(tmp_path: Path) -> None:
    database = _own(tmp_path)
    with pytest.raises(CuratedRefused, match="offers no db"):
        run_self_curated(database, "vacuum")


def test_self_backups_lists_what_self_backup_just_wrote(tmp_path: Path) -> None:
    database = _own(tmp_path)
    assert self_backups(database) == ()
    result = run_self_curated(database, "backup")
    found = self_backups(database)
    assert [one.path.name for one in found] == [Path(result.output["path"]).name]


def test_application_backups_lists_the_apps_own_directory_not_the_guarded_write_one(
    tmp_path: Path,
) -> None:
    db_path = fixture_database(tmp_path, "loadcoach-0015")
    executable, _config, _document = fake_application(
        tmp_path, "loadcoach", database_url=f"sqlite:///{db_path}"
    )
    console = tmp_path / "console.toml"
    console.write_text(f'[apps.loadcoach]\nexecutable = "{executable}"\n', encoding="utf-8")
    settings = load_settings(config_path=console).settings

    assert application_backups(settings, "loadcoach", urls=DatabaseUrlCache(), monotonic=0.0) == ()

    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir()
    (backups_dir / "manual-20260910T000000Z.sqlite3").write_bytes(b"x")
    (backups_dir / "notes.txt").write_bytes(b"ignored")

    found = application_backups(settings, "loadcoach", urls=DatabaseUrlCache(), monotonic=0.0)
    assert [one.path.name for one in found] == ["manual-20260910T000000Z.sqlite3"]


def test_application_backups_answers_nothing_for_an_uninstalled_application(
    tmp_path: Path,
) -> None:
    console = tmp_path / "console.toml"
    console.write_text(
        '[apps.freeweight]\nexecutable = "/nonexistent/freeweight-binary"\n', encoding="utf-8"
    )
    settings = load_settings(config_path=console).settings
    assert application_backups(settings, "freeweight", urls=DatabaseUrlCache(), monotonic=0.0) == ()
