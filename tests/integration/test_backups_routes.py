"""web/routes/backups.py: /api/v1/backups, WeightRoomGym's own db verbs, and the Backups page.

An application not installed in the console's own config degrades to one row's failure, never
the whole page (found writing this row's own audit exercise — see routes/backups.py's ``_status``).
"""

from __future__ import annotations

from pathlib import Path

from tests.support import Console, build_console, fake_application, fixture_database


def _console_with_loadcoach(tmp_path: Path) -> Console:
    database = fixture_database(tmp_path, "loadcoach-0015")
    executable, _config, _document = fake_application(
        tmp_path, "loadcoach", database_url=f"sqlite:///{database}"
    )
    return build_console(
        tmp_path / "console", extra_toml=f'[apps.loadcoach]\nexecutable = "{executable}"\n'
    )


def test_get_backups_lists_every_application_and_weightroom_itself(tmp_path: Path) -> None:
    console = _console_with_loadcoach(tmp_path)
    console.login()
    response = console.client.get("/api/v1/backups")
    assert response.status_code == 200
    apps = {row["app"] for row in response.json()["apps"]}
    assert apps == {"freeweight", "loadcoach", "ideapress", "promptcadence", "weightroom"}


def test_an_uninstalled_application_degrades_to_one_row_not_the_whole_page(
    tmp_path: Path,
) -> None:
    console = _console_with_loadcoach(tmp_path)
    console.login()
    response = console.client.get("/api/v1/backups")
    assert response.status_code == 200
    by_app = {row["app"]: row for row in response.json()["apps"]}
    assert by_app["freeweight"]["status"]["ok"] is False
    assert "not installed" in by_app["freeweight"]["status"]["error"]
    assert by_app["weightroom"]["status"]["ok"] is True


def test_self_status_reports_the_real_database(tmp_path: Path) -> None:
    console = _console_with_loadcoach(tmp_path)
    console.login()
    response = console.client.get("/api/v1/db/status")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["output"]["dialect"] == "sqlite"


def test_self_backup_writes_a_file_and_audits_once(tmp_path: Path) -> None:
    console = _console_with_loadcoach(tmp_path)
    console.login()
    response = console.client.post("/api/v1/db/backup")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert Path(response.json()["output"]["path"]).is_file()


def test_there_is_no_self_restore_route(tmp_path: Path) -> None:
    console = _console_with_loadcoach(tmp_path)
    console.login()
    assert console.client.post("/api/v1/db/restore").status_code == 404


def test_the_backups_page_renders_with_one_application_missing(tmp_path: Path) -> None:
    console = _console_with_loadcoach(tmp_path)
    console.login()
    response = console.client.get("/backups", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "Backups and migrations" in response.text
    assert "not installed" in response.text
