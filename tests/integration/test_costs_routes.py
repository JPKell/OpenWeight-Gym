"""web/routes/costs.py: /api/v1/costs, /api/v1/costs/{app} and the Costs page.

A read-only surface (module docstring) — no exercise is owed to
``tests/security/test_audit_routes.py``.
"""

from __future__ import annotations

from pathlib import Path

from tests.support import Console, build_console, fake_application, fixture_database


def _console_with_ideapress(tmp_path: Path) -> Console:
    database = fixture_database(tmp_path, "ideapress-0010")
    executable, _config, _document = fake_application(
        tmp_path, "ideapress", database_url=f"sqlite:///{database}"
    )
    return build_console(
        tmp_path / "console", extra_toml=f'[apps.ideapress]\nexecutable = "{executable}"\n'
    )


def test_get_costs_lists_both_ledger_applications(tmp_path: Path) -> None:
    console = _console_with_ideapress(tmp_path)
    console.login()
    response = console.client.get("/api/v1/costs")
    assert response.status_code == 200
    body = response.json()
    apps = {row["app"] for row in body["apps"]}
    assert apps == {"promptcadence", "ideapress"}


def test_get_one_apps_costs(tmp_path: Path) -> None:
    console = _console_with_ideapress(tmp_path)
    console.login()
    response = console.client.get("/api/v1/costs/ideapress")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "ideapress"
    assert body["today"]["tokens_spent"] == 0
    assert body["verdicts"] == []


def test_an_app_with_no_ledger_is_app_unknown(tmp_path: Path) -> None:
    console = _console_with_ideapress(tmp_path)
    console.login()
    response = console.client.get("/api/v1/costs/freeweight")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "APP_UNKNOWN"


def test_the_costs_page_renders(tmp_path: Path) -> None:
    console = _console_with_ideapress(tmp_path)
    console.login()
    response = console.client.get("/costs", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "Costs" in response.text
    assert "ideapress" in response.text.lower()
