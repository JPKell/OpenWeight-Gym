"""The shell (row W3, design brief §4): app tabs with dots, the telemetry strip, the left menu.

Every operator-facing page renders inside ``_shell.html``; this file proves the structural
claims the brief's artboard makes, not the pixels MirrorWall's own snapshot tests already cover.
"""

from __future__ import annotations

from pathlib import Path

from tests.support import Console, build_console
from weightroom.services.processes import FakeSystemdController


def _console(tmp_path: Path, **kwargs: object) -> Console:
    return build_console(tmp_path, **kwargs)  # type: ignore[arg-type]


def test_every_page_carries_four_app_tabs_with_status_dots(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    for path in ("/", "/apps", "/ollama", "/logs", "/audit", "/trust"):
        page = console.client.get(path, headers={"Accept": "text/html"}).text
        assert page.count('class="app-tab"') == 4, path
        assert page.count("status-dot") >= 4, path
        for name in ("freeweight", "loadcoach", "ideapress", "promptcadence"):
            assert f"/apps/{name}" in page, (path, name)


def test_an_applications_own_tab_is_current_only_on_its_pages(tmp_path: Path) -> None:
    console = _console(
        tmp_path, systemd=FakeSystemdController(states={"loadcoach.service": "active"})
    )
    console.login()
    on_its_page = console.client.get("/apps/loadcoach", headers={"Accept": "text/html"}).text
    elsewhere = console.client.get("/apps", headers={"Accept": "text/html"}).text
    assert 'aria-current="page"' in on_its_page
    assert 'aria-current="page"' not in elsewhere


def test_the_telemetry_strip_is_on_every_page_with_the_stream_url(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    page = console.client.get("/", headers={"Accept": "text/html"}).text
    assert 'data-telemetry-url="/api/v1/system/telemetry/stream"' in page
    assert "RESIDENT" in page
    assert "QUEUE" in page
    # The two WeightRoomGym-specific meters refresh live off the same stream telemetry.js uses
    # for the generic fields (meter() has no live hook of its own to wire them through).
    assert 'meterValue("RESIDENT")' in page
    assert 'meterValue("QUEUE")' in page


def test_an_applications_side_nav_names_its_built_pages_and_the_unbuilt_ones(
    tmp_path: Path,
) -> None:
    console = _console(tmp_path)
    console.login()
    page = console.client.get("/apps/loadcoach", headers={"Accept": "text/html"}).text
    assert 'aria-label="Sections"' in page  # side_nav's own landmark
    assert "Overview" in page
    # Built at W4, so they are links now, not stubs.
    assert 'href="/apps/loadcoach/settings"' in page
    assert 'href="/apps/loadcoach/tokens"' in page
    # Database is scheduled (W7); a page with no row yet says so honestly; and a page that is
    # deliberately somebody else's says where it lives instead of naming a row (W4).
    assert 'title="coming in phase W7"' in page
    assert "not yet scheduled" in page
    assert "ADR-0117" in page


def test_the_console_pages_are_named_and_inert_until_their_rows_land(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    page = console.client.get("/", headers={"Accept": "text/html"}).text
    for label, phase in (("Chat", "W6"), ("Docs", "W5"), ("Database", "W7"), ("Jobs", "W9")):
        assert f'title="coming in phase {phase}">{label}' in page
    assert "/chat" not in page
    assert "/docs" not in page


def test_every_page_still_carries_the_shell_with_every_application_stopped(
    tmp_path: Path,
) -> None:
    """Plan Phase 3 criterion 3, the shell half: acceptance is 'stopped' with a working start
    button and the console still serving, not silence."""
    executable = tmp_path / "loadcoach"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    console = _console(
        tmp_path,
        systemd=FakeSystemdController(states={"loadcoach.service": "inactive"}),
        extra_toml=f'[apps.loadcoach]\nexecutable = "{executable}"\n',
    )
    console.login()
    for path in ("/", "/apps", "/apps/loadcoach", "/logs", "/audit"):
        response = console.client.get(path, headers={"Accept": "text/html"})
        assert response.status_code == 200, path
        assert response.text.count('class="app-tab"') == 4, path
    page = console.client.get("/apps/loadcoach", headers={"Accept": "text/html"}).text
    assert "stopped" in page
