"""Row WP1's page kit over the smallest page: one application's Logs, and the menu around it."""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from tests.integration.test_apps_routes import LOADCOACH_URL, StubJournal
from tests.support import Console, build_console
from weightroom.services.apps import AppState
from weightroom.services.processes import FakeSystemdController

HTML = {"Accept": "text/html"}


def _console(tmp_path: Path, *, state: AppState) -> Console:
    executable = tmp_path / "loadcoach"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    console = build_console(
        tmp_path,
        extra_toml=f'[apps.loadcoach]\nexecutable = "{executable}"\nbase_url = "{LOADCOACH_URL}"\n',
        systemd=FakeSystemdController(states={"loadcoach.service": state}),
        journal=StubJournal(),
    )
    console.login()
    return console


def test_the_logs_page_is_history_above_the_live_pane_and_current_in_the_menu(
    tmp_path: Path,
) -> None:
    console = _console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{LOADCOACH_URL}/api/v1/version").mock(
            return_value=httpx.Response(
                200,
                json={
                    "application": {"name": "loadcoach", "version": "1.5.0"},
                    "api": {"current": "v1"},
                },
            )
        )
        page = console.client.get("/apps/loadcoach/logs?level=err&q=started", headers=HTML)
    assert page.status_code == 200
    text = page.text
    assert "Journal history, newest first" in text
    assert "started" in text
    assert 'data-log-stream="/api/v1/apps/loadcoach/logs/stream"' in text
    assert '<a href="/apps/loadcoach/logs" aria-current="page">Logs</a>' in text
    # The application's own pages, the rule, then the administrative pages (design brief §4).
    nav = text.split('aria-label="Sections"', 1)[1].split("</nav>", 1)[0]
    assert "<hr>" in nav
    assert nav.index("Overview") < nav.index("<hr>") < nav.index("Settings")
    # A running application's page carries no control form; the Overview does.
    assert 'action="/apps/loadcoach/control"' not in text
    assert 'title="coming in row' not in text  # every LoadCoach page is built (row WP2)
    assert 'href="/apps/loadcoach/adapters"' in text


def test_a_stopped_applications_page_carries_a_start_that_returns_to_it(tmp_path: Path) -> None:
    console = _console(tmp_path, state="inactive")
    text = console.client.get("/apps/loadcoach/logs", headers=HTML).text
    assert 'action="/apps/loadcoach/control"' in text
    assert 'name="next" value="/apps/loadcoach/logs"' in text
    back = console.post_form(
        "/apps/loadcoach/control", {"verb": "start", "next": "/apps/loadcoach/logs"}
    )
    assert back.status_code == 303
    assert back.headers["location"] == "/apps/loadcoach/logs"


def test_the_control_forms_next_cannot_leave_the_applications_tab(tmp_path: Path) -> None:
    console = _console(tmp_path, state="inactive")
    for hostile in (
        "//evil.example.net/x",
        "/apps/ideapress",
        "https://evil.example.net",
        "/apps/loadcoachx",
    ):
        answer = console.post_form("/apps/loadcoach/control", {"verb": "start", "next": hostile})
        assert answer.headers["location"] == "/apps/loadcoach", hostile
