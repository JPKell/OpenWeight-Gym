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


EXERCISES: dict[tuple[str, str], Exercise] = {
    ("POST", "/login"): _form_login,
    ("POST", "/logout"): _form_logout,
    ("POST", "/api/v1/login"): _json_login,
    ("POST", "/api/v1/logout"): _json_logout,
    ("POST", "/api/v1/reauth"): _json_reauth,
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
    return build_console(tmp_path)


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
