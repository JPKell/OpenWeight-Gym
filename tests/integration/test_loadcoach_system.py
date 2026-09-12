"""Row WPF5 Gate B: LoadCoach's System page — judged needed at WP6 (§3): health components and
workers appeared nowhere in the console (WP6_HANDOFF.md §3).

The recordings under ``tests/fixtures/loadcoach`` (``health.json``, ``system-status.json``) are a
LoadCoach built from this row's own worktree, run against ``FakeProvider`` (no GPU), with no token
configured — the same open-loopback reading WP2 already relies on. Dispatch, residency and circuit
breakers already have a home on Queue and Reliability (WP2); this page adds only what neither did.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import httpx
import respx

from tests.integration.test_loadcoach_pages import (
    API,
    BASE,
    fixture,
    loadcoach_console,
    mock_api,
    page,
)
from tests.security.test_chat_isolation import HOSTILE, _assert_inert
from weightroom.web.rendering import app_side_nav_stubs


def gate_api(router: Any, **bodies: Any) -> dict[str, Any]:  # noqa: ANN401 — a respx router
    """Gate A's recorded reads, and the System recordings beside them."""
    recorded = {"health": fixture("health"), "system/status": fixture("system-status")}
    recorded.update(bodies)
    return mock_api(router, bodies=recorded)


def test_every_loadcoach_page_is_built_and_none_is_a_stub() -> None:
    assert app_side_nav_stubs("loadcoach") == ()


def test_the_system_page_reads_version_and_health_components(tmp_path: Path) -> None:
    console, _database = loadcoach_console(tmp_path, state="active")
    health = fixture("health")
    with respx.mock(assert_all_called=False) as router:
        gate_api(router)
        text = page(console, f"{BASE}/system")
    assert '<a href="/apps/loadcoach/system" aria-current="page">System</a>' in text
    assert health["version"] in text
    for component in ("database", "provider", "queue", "evidence", "reliability"):
        assert f">{component}<" in text, component
    assert 'href="/apps/loadcoach/queue"' in text
    assert 'href="/apps/loadcoach/reliability"' in text
    assert "From the API" in text


def test_a_stopped_systems_page_reads_only_from_the_api(tmp_path: Path) -> None:
    console, _database = loadcoach_console(tmp_path, state="inactive")
    assert "reads only from its running API" in page(console, f"{BASE}/system")


def test_a_health_refusal_renders_beside_the_status_half(tmp_path: Path) -> None:
    """WPC1's precedent (§2 item 7): a 503 from ``/health`` refuses only that half of the page."""
    console, _database = loadcoach_console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        gate_api(router)
        router.get(f"{API}/health").mock(
            return_value=httpx.Response(503, json={"status": "unavailable"})
        )
        text = page(console, f"{BASE}/system")
    assert "HTTP_503" in text
    assert "From the API" in text


def test_the_injection_corpus_renders_inert_on_the_system_page(tmp_path: Path) -> None:
    console, _database = loadcoach_console(tmp_path, state="active")
    health = copy.deepcopy(fixture("health"))
    health["components"][0]["detail"] = HOSTILE
    with respx.mock(assert_all_called=False) as router:
        gate_api(router, health=health)
        text = page(console, f"{BASE}/system")
    _assert_inert(text)
