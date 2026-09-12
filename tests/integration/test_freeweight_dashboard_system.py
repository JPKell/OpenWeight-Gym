"""Row WPF5 Gate B: FreeWeight's Dashboard and System pages — judged needed at WP6 (§3).

The recordings under ``tests/fixtures/freeweight`` (``dashboard.json``, ``health.json``) are a
FreeWeight built from this row's own worktree, run against ``FakeProvider`` (no GPU) after one
``native.echo`` run completed — the same technique ``tests/e2e/test_dashboard.py`` uses, since the
reference machine's FreeWeight predates the ``GET /api/v1/dashboard`` route this row adds. Both
pages read the running API only (spec §7.3 amendment, WPF5): FreeWeight's own Dashboard and System
pages are HTML-only computations, so a stopped FreeWeight leaves nothing in its database that would
reproduce them faithfully.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import httpx
import respx

from tests.integration.test_freeweight_pages import (
    BASE,
    fixture,
    freeweight_console,
    mock_api,
    page,
    route_for,
)
from tests.security.test_chat_isolation import HOSTILE, _assert_inert
from weightroom.web.rendering import app_side_nav_stubs

RUN = "01M29YGGP7KTBC7TPARGX29T2D"


def gate_api(router: Any, **bodies: Any) -> dict[str, Any]:  # noqa: ANN401 — a respx router
    """Gate A's recorded reads, and the Dashboard and System recordings beside them."""
    recorded = {"dashboard": fixture("dashboard"), "health": fixture("health")}
    recorded.update(bodies)
    return mock_api(router, bodies=recorded)


def test_every_freeweight_page_is_built_and_none_is_a_stub() -> None:
    assert app_side_nav_stubs("freeweight") == ()


# --- Dashboard --------------------------------------------------------------------------------


def test_the_dashboard_reads_freeweights_summary_and_heatmap(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    dashboard = fixture("dashboard")
    with respx.mock(assert_all_called=False) as router:
        gate_api(router)
        text = page(console, f"{BASE}/dashboard")
    assert '<a href="/apps/freeweight/dashboard" aria-current="page">Dashboard</a>' in text
    assert str(dashboard["cards"]["completed_runs"]) in text
    assert dashboard["heatmap"]["models"][0] in text
    assert dashboard["heatmap"]["suites"][0] in text
    assert f'href="/apps/freeweight/runs/{RUN}"' in text
    assert "From the API" in text


def test_the_dashboards_filters_reach_freeweights_query(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        routes = gate_api(router)
        page(
            console,
            f"{BASE}/dashboard?suite=native.echo&model=m&machine=abc&since=2026-09-01T00:00:00Z",
        )
    params = routes["dashboard"].calls.last.request.url.params
    assert (params["suite"], params["model"], params["machine"]) == ("native.echo", "m", "abc")
    assert params["since"] == "2026-09-01T00:00:00Z"


def test_a_separated_heatmap_carries_the_warning(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    dashboard = copy.deepcopy(fixture("dashboard"))
    dashboard["heatmap"]["separated"] = True
    with respx.mock(assert_all_called=False) as router:
        gate_api(router, dashboard=dashboard)
        text = page(console, f"{BASE}/dashboard")
    assert "Separated" in text


def test_a_refused_dashboard_filter_renders_freeweights_own_refusal(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        gate_api(router)
        route_for(router, "GET", "dashboard").mock(
            return_value=httpx.Response(
                404,
                json={
                    "error": {
                        "code": "MODEL_NOT_FOUND",
                        "message": "No model matches 'nothing'.",
                        "details": {"model": "nothing"},
                    }
                },
            )
        )
        text = page(console, f"{BASE}/dashboard?model=nothing")
    assert "MODEL_NOT_FOUND" in text
    assert "No model matches" in text


def test_a_stopped_dashboard_reads_only_from_the_api(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="inactive")
    assert "reads only from its running API" in page(console, f"{BASE}/dashboard")


def test_the_injection_corpus_renders_inert_on_the_dashboard(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    dashboard = copy.deepcopy(fixture("dashboard"))
    dashboard["heatmap"]["cells"][0]["unavailable_reason"] = HOSTILE
    dashboard["heatmap"]["models"][0] = HOSTILE
    with respx.mock(assert_all_called=False) as router:
        gate_api(router, dashboard=dashboard)
        text = page(console, f"{BASE}/dashboard")
    _assert_inert(text)


# --- System -------------------------------------------------------------------------------------


def test_the_system_page_reads_version_status_and_health_components(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    health = fixture("health")
    with respx.mock(assert_all_called=False) as router:
        gate_api(router)
        text = page(console, f"{BASE}/system")
    assert '<a href="/apps/freeweight/system" aria-current="page">System</a>' in text
    assert health["version"] in text
    for component in (
        "database", "provider", "gpu_telemetry", "machine", "evidence",
        "prompts", "sandbox", "external_benchmarks", "goals", "judges",
    ):  # fmt: skip
        assert f">{component}<" in text, component
    assert "From the API" in text


def test_a_stopped_systems_page_reads_only_from_the_api(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="inactive")
    assert "reads only from its running API" in page(console, f"{BASE}/system")


def test_a_degraded_component_renders_its_own_detail(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    health = copy.deepcopy(fixture("health"))
    health["components"][1]["status"] = "degraded"
    health["components"][1]["detail"] = "provider is slow to answer"
    health["status"] = "degraded"
    with respx.mock(assert_all_called=False) as router:
        gate_api(router, health=health)
        text = page(console, f"{BASE}/system")
    assert "provider is slow to answer" in text


def test_the_injection_corpus_renders_inert_on_the_system_page(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    health = copy.deepcopy(fixture("health"))
    health["components"][0]["detail"] = HOSTILE
    with respx.mock(assert_all_called=False) as router:
        gate_api(router, health=health)
        text = page(console, f"{BASE}/system")
    _assert_inert(text)
