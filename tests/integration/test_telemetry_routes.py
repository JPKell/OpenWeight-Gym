"""``/api/v1/system/telemetry/*`` and ``/api/v1/system/resident`` (api.md §1, spec §7.7).

The stream and history routes read straight from the database — ``build_console`` never enters
the lifespan (``tests/support.py``'s own docstring), so these tests persist rows directly rather
than running a live ``TelemetryService``; that sampler's own behaviour is
``tests/unit/test_telemetry.py``'s job.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import anyio

from tests.support import Console, build_console
from weightroom.infrastructure.db.models import TelemetrySample
from weightroom.services.database import Database
from weightroom.web.routes.system import _telemetry_frames

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


def _console(tmp_path: Path) -> Console:
    return build_console(tmp_path)


def _frames(text: str) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        name = ""
        data = ""
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = line.removeprefix("data: ")
        if name and data:
            found.append((name, json.loads(data)))
    return found


@dataclass
class _FakeAppState:
    database: Database


@dataclass
class _FakeApp:
    state: _FakeAppState


class _FakeRequest:
    """Just enough of a ``Request`` for ``_telemetry_frames``: a database and a disconnect clock.

    The route's SSE stream is intentionally unbounded (it is live, not a finite log follow), so
    driving it through ``TestClient.stream()`` would never see its own generator return — that
    pattern works for the log stream tests only because a fake journal closes with ``log.closed``.
    Calling the generator directly, the way FreeWeight's own event-stream tests drive
    ``_event_stream`` (``web/routes/runs.py``), is the deterministic alternative: no thread, no
    portal, no open connection to close.
    """

    def __init__(self, database: Database, *, disconnect_after: int) -> None:
        self.app = _FakeApp(state=_FakeAppState(database=database))
        self._checks = 0
        self._disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > self._disconnect_after


async def _collect(database: Database, after_id: int, disconnect_after: int = 1) -> str:
    request = _FakeRequest(database, disconnect_after=disconnect_after)
    # `_telemetry_frames` only ever runs against a real `Request` in production; this fake
    # supplies exactly the two members it reads (`app.state.database` and `is_disconnected()`).
    frames = [
        frame
        async for frame in _telemetry_frames(request, after_id=after_id)  # type: ignore[arg-type]
    ]
    return "".join(frames)


def test_history_needs_a_known_figure(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()

    response = console.client.get("/api/v1/system/telemetry/history?figure=made_up")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_history_returns_samples_within_the_window(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    with console.database.write() as session:
        session.add(
            TelemetrySample(at=NOW, interval_ms=1000, gpu_index=0, gpu_utilization_percent=61.0)
        )
        session.add(
            TelemetrySample(
                at=NOW - timedelta(hours=48), interval_ms=1000, gpu_utilization_percent=10.0
            )
        )

    body = console.client.get(
        "/api/v1/system/telemetry/history?figure=gpu_utilization_percent&hours=24"
    ).json()
    assert body["figure"] == "gpu_utilization_percent"
    assert len(body["samples"]) == 1
    assert body["samples"][0]["value"] == 61.0


def test_the_stream_replays_persisted_rows_as_enveloped_sse_frames(tmp_path: Path) -> None:
    console = _console(tmp_path)
    with console.database.write() as session:
        session.add(
            TelemetrySample(at=NOW, interval_ms=1000, gpu_index=0, gpu_utilization_percent=61.0)
        )
        session.add(
            TelemetrySample(
                at=NOW + timedelta(seconds=1),
                interval_ms=1000,
                gpu_index=0,
                gpu_utilization_percent=62.0,
            )
        )

    collected = anyio.run(_collect, console.database, 0)
    frames = _frames(collected)
    sampled = [payload for name, payload in frames if name == "telemetry.sampled"]
    assert len(sampled) == 2
    assert sampled[0]["payload"]["gpus"][0]["utilization_percent"] == 61.0
    assert sampled[1]["payload"]["gpus"][0]["utilization_percent"] == 62.0
    # ADR-0025 §3: every non-token frame is enveloped and names its producer.
    assert sampled[0]["generator"]["name"] == "weightroom"
    assert "id: 1\n" in collected


def test_the_stream_resumes_from_last_event_id(tmp_path: Path) -> None:
    console = _console(tmp_path)
    with console.database.write() as session:
        session.add(
            TelemetrySample(at=NOW, interval_ms=1000, gpu_index=0, gpu_utilization_percent=61.0)
        )
        session.add(
            TelemetrySample(
                at=NOW + timedelta(seconds=1),
                interval_ms=1000,
                gpu_index=0,
                gpu_utilization_percent=62.0,
            )
        )

    collected = anyio.run(_collect, console.database, 1)
    frames = _frames(collected)
    sampled = [payload for name, payload in frames if name == "telemetry.sampled"]
    assert len(sampled) == 1
    assert sampled[0]["payload"]["sequence"] == 2


def test_resident_reports_a_source_and_an_error_for_each_unreachable_side(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()

    body = console.client.get("/api/v1/system/resident").json()
    assert body["ollama"]["source"] == "ollama"
    assert body["ollama"]["models"] == []
    assert body["loadcoach"]["source"] == "loadcoach"
    assert body["loadcoach"]["models"] == []
    assert body["loadcoach"]["error"]


def test_the_history_page_renders_an_inline_svg_clicking_the_strip_would_open(
    tmp_path: Path,
) -> None:
    console = _console(tmp_path)
    console.login()
    with console.database.write() as session:
        session.add(
            TelemetrySample(at=NOW, interval_ms=1000, gpu_index=0, gpu_vram_used_bytes=1_000_000)
        )

    page = console.client.get(
        "/telemetry/history?figure=gpu_vram_used_bytes", headers={"Accept": "text/html"}
    ).text
    assert "<svg" in page and "polyline" in page
    assert "1 sample." in page


def test_the_history_page_falls_back_to_a_known_figure_for_a_bad_query(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    response = console.client.get(
        "/telemetry/history?figure=not-a-figure", headers={"Accept": "text/html"}
    )
    assert response.status_code == 200
    assert "gpu_vram_used_bytes" in response.text


def test_telemetry_routes_need_a_session(tmp_path: Path) -> None:
    console = build_console(tmp_path, host="10.77.10.84")
    for path in (
        "/api/v1/system/telemetry/history?figure=cpu_percent",
        "/api/v1/system/telemetry/stream",
        "/api/v1/system/resident",
    ):
        response = console.client.get(path, headers={"Host": "jordan-main.local"})
        assert response.status_code == 401, path
