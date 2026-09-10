"""Spec §11 contract 2: every state-changing route writes exactly one ``audit_log`` row.

The test enumerates the app's routes rather than listing them: a new ``POST``/``PUT``/``PATCH``/
``DELETE`` route fails this suite until it has an entry in :data:`EXERCISES`, and every entry is
run and must add exactly one row. Later rows inherit both halves.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select

from tests.support import JSON_HEADERS, PASSWORD, USERNAME, Console, api_routes, build_console
from weightroom.infrastructure.db.models import AuditLog
from weightroom.services.processes import FakeSystemdController

STATE_CHANGING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

Exercise = Callable[[Console], Any]


def _form_login(console: Console) -> Any:  # noqa: ANN401
    console.client.cookies.clear()
    return console.login()


def _form_logout(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/logout", {})


def _json_login(console: Console) -> Any:  # noqa: ANN401
    console.client.cookies.clear()
    return console.client.post(
        "/api/v1/login", json={"username": USERNAME, "password": PASSWORD}, headers=JSON_HEADERS
    )


def _json_logout(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/logout", headers=JSON_HEADERS)


def _json_reauth(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/reauth", json={"password": PASSWORD}, headers=JSON_HEADERS)


def _unit(verb: str) -> Exercise:
    """One successful control call against the fake host the console was built over."""

    def exercise(console: Console) -> Any:  # noqa: ANN401
        return console.client.post(f"/api/v1/apps/loadcoach/{verb}", headers=JSON_HEADERS)

    return exercise


def _control_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/loadcoach/control", {"verb": "restart"})


def _ollama_restart(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/ollama/restart", headers=JSON_HEADERS)


def _ollama_restart_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/ollama/restart", {})


EXERCISES: dict[tuple[str, str], Exercise] = {
    ("POST", "/login"): _form_login,
    ("POST", "/logout"): _form_logout,
    ("POST", "/api/v1/login"): _json_login,
    ("POST", "/api/v1/logout"): _json_logout,
    ("POST", "/api/v1/reauth"): _json_reauth,
    ("POST", "/api/v1/apps/{app}/start"): _unit("start"),
    ("POST", "/api/v1/apps/{app}/stop"): _unit("stop"),
    ("POST", "/api/v1/apps/{app}/restart"): _unit("restart"),
    ("POST", "/apps/{app}/control"): _control_form,
    ("POST", "/api/v1/ollama/restart"): _ollama_restart,
    ("POST", "/ollama/restart"): _ollama_restart_form,
}
"""One representative, successful call per state-changing route. Add a line per new route."""


def _state_changing_routes(console: Console) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path, route in api_routes(console.client.app):
        for method in (route.methods or set()) & STATE_CHANGING:
            found.add((method, path))
    return found


def _rows(console: Console) -> int:
    with console.database.read() as session:
        return int(session.execute(select(func.count()).select_from(AuditLog)).scalar_one())


@pytest.fixture
def console(tmp_path: Path) -> Console:
    # A fake host where loadcoach is installed and its unit exists, so the control routes have
    # something to act on and each writes exactly one row.
    executable = tmp_path / "loadcoach"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    return build_console(
        tmp_path,
        extra_toml=f'[apps.loadcoach]\nexecutable = "{executable}"\n',
        systemd=FakeSystemdController(states={"loadcoach.service": "active"}),
    )


def test_every_state_changing_route_has_an_exercise(console: Console) -> None:
    routes = _state_changing_routes(console)
    assert routes == set(EXERCISES), (
        f"routes without an audit exercise: {sorted(routes - set(EXERCISES))}; "
        f"exercises for absent routes: {sorted(set(EXERCISES) - routes)}"
    )


@pytest.mark.parametrize(("method", "path"), sorted(EXERCISES))
def test_each_state_changing_route_writes_exactly_one_audit_row(
    console: Console, method: str, path: str
) -> None:
    console.login()  # a session for the routes that need one; its own row is counted first
    before = _rows(console)
    response = EXERCISES[(method, path)](console)
    assert response.status_code < 400, (method, path, response.text)
    assert _rows(console) == before + 1, (method, path)
