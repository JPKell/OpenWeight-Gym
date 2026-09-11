"""End to end, with the network gone: every page and every read route still answers.

Spec §20 criterion 10 and the last WeightRoomGym gold standard: with no application, no systemd,
no GPU and no network, the console serves the shell, the docs, the doctor and the audit trail.
Here a raw socket cannot open at all — ``socket.connect`` refuses — and every HTML page and every
``GET`` under ``/api/v1`` that needs no id is fetched against a console whose four applications
are installed (a fake executable each) and stopped. Nothing may reach for a peer to render.
"""

from __future__ import annotations

import errno
import socket
from pathlib import Path
from typing import Any

import pytest

from tests.support import JSON_HEADERS, Console, api_routes, build_console, fake_application
from weightroom.config import APPLICATIONS
from weightroom.services.processes import FakeSystemdController

DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs"


@pytest.fixture
def console(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Console:
    def refuse(*args: object, **kwargs: object) -> None:
        # What a host with no network answers: the connect fails, and the console must degrade
        # the pane that asked (Ollama, a peer's API) rather than the page.
        raise OSError(errno.ENETUNREACH, "network is unreachable")

    lines = [f'[docs]\nroot = "{DOCS_ROOT}"\n']
    for app in APPLICATIONS:
        executable, _config, _document = fake_application(tmp_path, app)
        lines.append(f'[apps.{app}]\nexecutable = "{executable}"\n')
    console = build_console(
        tmp_path / "console", extra_toml="".join(lines), systemd=FakeSystemdController()
    )
    console.login()
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    return console


def _html_paths(console: Console) -> list[str]:
    paths: list[str] = []
    for path, route in api_routes(console.client.app):
        if "GET" not in (route.methods or set()) or path.startswith("/api/"):
            continue
        if path.replace("{app}", "").count("{"):
            continue  # a page over one record; the records' own tests cover them
        paths.extend(
            path.replace("{app}", app) for app in (APPLICATIONS if "{app}" in path else ("",))
        )
    return sorted(set(paths))


def _json_paths(console: Console) -> list[str]:
    paths: list[str] = []
    for path, route in api_routes(console.client.app):
        if "GET" not in (route.methods or set()) or not path.startswith("/api/v1"):
            continue
        if path.replace("{app}", "").count("{"):
            continue  # a read over one record; the records' own tests cover them
        if path.endswith("/stream") or "/stream" in path:
            continue  # SSE never ends; the streams have their own tests
        paths.extend(
            path.replace("{app}", app) for app in (APPLICATIONS if "{app}" in path else ("",))
        )
    return sorted(set(paths))


def test_every_page_renders_with_every_application_stopped_and_no_socket(
    console: Console,
) -> None:
    failures: list[tuple[str, int]] = []
    for path in _html_paths(console):
        if path.endswith("/stream") or path in {"/trust/root.crt"}:
            continue
        response = console.client.get(path, headers={"Accept": "text/html"})
        if response.status_code >= 500:
            failures.append((path, response.status_code))
    assert failures == []


def test_every_json_read_answers_with_every_application_stopped_and_no_socket(
    console: Console,
) -> None:
    answered: dict[str, int] = {}
    refused: dict[str, str] = {}
    for path in _json_paths(console):
        response: Any = console.client.get(path, headers=JSON_HEADERS)
        answered[path] = response.status_code
        if response.status_code >= 500:
            # A refusal by name (UNIT_UNSUPPORTED without systemd, the database unreachable) is
            # honest degradation; an internal error is not.
            refused[path] = response.json()["error"]["code"]
    assert all(code != 500 for code in answered.values()), answered
    assert all(refused.values()), refused
    assert answered["/api/v1/health"] == 200
    assert answered["/api/v1/system/status"] == 200
    assert answered["/api/v1/doctor"] == 200
