"""The shell (row W3, design brief §4): app tabs with dots, the telemetry strip, the left menu.

Every operator-facing page renders inside ``_shell.html``; this file proves the structural
claims the brief's artboard makes, not the pixels MirrorWall's own snapshot tests already cover.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.support import Console, build_console
from weightroom.__about__ import __version__
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
    # On an element, not in the stylesheet — the shell's CSS names the same attribute selector.
    current = re.compile(r"<a [^>]*aria-current=\"page\"")
    assert current.search(on_its_page)
    assert not current.search(elsewhere)


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


def test_the_strip_loads_the_modules_that_move_it(tmp_path: Path) -> None:
    """A bar whose values never change is a bar that measures nothing (design brief §4).

    MirrorWall's base template loads neither `sse.js` nor `telemetry.js` — they are opt-in per
    application — so a console that shows the strip and omits them renders four em dashes and
    keeps them forever, which is what W3 shipped.
    """
    console = _console(tmp_path)
    console.login()
    page = console.client.get("/", headers={"Accept": "text/html"}).text
    assert "js/sse.js" in page
    assert "js/telemetry.js" in page
    # One EventSource per tab: RESIDENT and QUEUE read telemetry.js's re-dispatched frame.
    assert 'addEventListener("mw:telemetry"' in page
    assert "mirrorwallSse.connect(" not in page
    # The strip can be hidden, and a hidden strip opens no stream: the toggle names the bar it
    # controls, and the remembered choice is applied in <head>, before first paint, so telemetry.js
    # never finds a rendered bar to connect.
    assert 'class="icon-button telemetry-toggle" aria-controls="mw-telemetry-bar"' in page
    assert ':root[data-telemetry="off"] #mw-telemetry-bar { display: none; }' in page
    assert page.index('localStorage.getItem("weightroom-telemetry")') < page.index("<body")
    # The artboard's inline meters, opted into by name; MirrorWall renders no track without them.
    for group in ("cpu", "ram", "gpu", "vram"):
        assert f'data-meter="{group}"' in page, group


def test_the_console_overview_lists_the_applications_as_a_dense_table(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    page = console.client.get("/", headers={"Accept": "text/html"}).text
    assert 'data-table="console-applications"' in page
    assert 'data-density="dense"' in page
    # Linked by the lowercase route, labelled with the display name.
    for name, label in (
        ("freeweight", "FreeWeight"),
        ("loadcoach", "LoadCoach"),
        ("ideapress", "IdeaPress"),
        ("promptcadence", "PromptCadence"),
    ):
        assert f'<a href="/apps/{name}">{label}</a>' in page, name


def test_the_top_bar_collapses_in_two_steps_and_the_brand_goes_home(tmp_path: Path) -> None:
    """Console pages fold into Menu first, then the applications (operator, 2026-09-10).

    Each group is rendered inline and again inside Menu; the stylesheet shows one copy per width.
    What this proves is the structure the breakpoints rely on — the widths themselves were swept
    in headless Chrome from 1400 px down to 350 px.
    """
    console = _console(tmp_path)
    console.login()
    page = console.client.get("/apps/loadcoach", headers={"Accept": "text/html"}).text
    assert '<h1><a class="brand" href="/">WeightRoom</a></h1>' in page
    assert 'class="version"' not in page  # no version in the header
    assert f"WeightRoom {__version__}" in page[page.index('class="dropdown user-menu"') :]
    assert page.count('class="app-tab"') == 4  # the inline tabs; Menu's copies are plain links
    assert 'class="dropdown-group nav-more-apps"' in page
    assert 'class="dropdown-group nav-more-console"' in page
    assert re.search(r'<a href="/apps/loadcoach" aria-current="page">.*?LoadCoach</a>', page, re.S)
    # One theme control, inside the operator menu, so theme.js has exactly one select to bind.
    assert page.count("data-theme-select") == 1
    assert page.index("data-theme-select") > page.index('class="dropdown user-menu"')
    assert "@media (max-width: 1080px)" in page
    assert "@media (max-width: 860px)" in page


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
    for label, phase in (("Chat", "W6"), ("Database", "W7"), ("Jobs", "W9")):
        assert f'title="coming in phase {phase}">{label}' in page
    assert "/chat" not in page
    # Docs (row W5) is built: a real link, not a stub — tests/integration/test_docs_routes.py
    # proves the page itself; this only guards the top-bar wiring.
    assert '<a href="/docs">Docs</a>' in page
    assert 'title="coming in phase W5"' not in page


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
