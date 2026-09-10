"""``/apps`` and the journal routes (api.md §2), over a fake host and a stub journal reader."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from mirrorwall import Event, Subscription

from tests.support import JSON_HEADERS, Console, build_console
from weightroom.services.journal import JournalLine, JournalPage, JournalReader
from weightroom.services.processes import FakeSystemdController

LOADCOACH_URL = "http://127.0.0.1:8766"


class StubJournal(JournalReader):
    """A journal reader with a scripted history and a subscription the test fills in."""

    def __init__(self, *, events: Sequence[Event] = (), maxlen: int = 256) -> None:
        super().__init__(which=lambda _name: None)
        self.events = list(events)
        self.maxlen = maxlen
        self.asked: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    def available(self) -> bool:
        return True

    def history(self, units: Sequence[str], **kwargs: Any) -> JournalPage:
        self.asked.append((tuple(units), kwargs))
        from datetime import UTC, datetime

        line = JournalLine(
            cursor="s=1;i=1",
            at=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
            priority=6,
            unit=units[0],
            message="started",
        )
        return JournalPage(lines=(line,), next_cursor=None)

    @contextmanager
    def follow(self, units: Sequence[str], **kwargs: Any) -> Iterator[Subscription]:
        self.asked.append((tuple(units), kwargs))
        subscription = Subscription(maxlen=self.maxlen)
        for event in self.events:
            subscription.publish(event)
        subscription.publish(
            Event(sequence=len(self.events) + 1, type="log.closed", payload={"reason": "test"})
        )
        try:
            yield subscription
        finally:
            subscription.close()


def _console(tmp_path: Path, **kwargs: Any) -> Console:
    executable = tmp_path / "loadcoach"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    return build_console(
        tmp_path,
        extra_toml=(
            f'[apps.loadcoach]\nexecutable = "{executable}"\nbase_url = "{LOADCOACH_URL}"\n'
        ),
        **kwargs,
    )


@pytest.fixture
def running(tmp_path: Path) -> Console:
    return _console(tmp_path, systemd=FakeSystemdController(states={"loadcoach.service": "active"}))


@pytest.fixture
def stopped(tmp_path: Path) -> Console:
    return _console(
        tmp_path, systemd=FakeSystemdController(states={"loadcoach.service": "inactive"})
    )


def _version(version: str = "1.3.1") -> respx.Route:
    return respx.get(f"{LOADCOACH_URL}/api/v1/version").mock(
        return_value=httpx.Response(
            200, json={"application": "loadcoach", "version": version, "api_version": "v1"}
        )
    )


@respx.mock
def test_apps_lists_four_with_install_unit_and_version(running: Console) -> None:
    _version()
    running.login()
    body = running.client.get("/api/v1/apps").json()
    assert [entry["name"] for entry in body["apps"]] == [
        "freeweight",
        "loadcoach",
        "ideapress",
        "promptcadence",
    ]
    loadcoach = next(entry for entry in body["apps"] if entry["name"] == "loadcoach")
    assert loadcoach["installed"] is True
    assert loadcoach["unit"] == "loadcoach.service"
    assert loadcoach["unit_state"] == "active"
    assert loadcoach["state"] == "ok"
    assert loadcoach["version"] == "1.3.1"
    assert loadcoach["version_verdict"] == "ok"
    assert loadcoach["supported_versions"] == ">=1.0,<2.0"


@respx.mock
def test_an_application_that_is_not_installed_says_so_rather_than_stopped(
    running: Console,
) -> None:
    running.login()
    body = running.client.get("/api/v1/apps/freeweight").json()
    assert body["installed"] is False
    assert body["state"] == "not installed"
    assert body["unit_state"] == "absent"
    assert body["uptime_seconds"] is None


@respx.mock
def test_a_stopped_application_is_never_probed(stopped: Console) -> None:
    route = _version()
    stopped.login()
    body = stopped.client.get("/api/v1/apps/loadcoach").json()
    assert body["state"] == "stopped"
    assert body["version"] is None
    assert not route.called, "a stopped application's API must not be dialled"


@respx.mock
def test_a_version_outside_the_range_is_a_mismatch_by_name(running: Console) -> None:
    _version("2.4.0")
    running.login()
    body = running.client.get("/api/v1/apps/loadcoach").json()
    assert body["version_verdict"] == "too_new"
    assert body["state"] == "version mismatch"
    page = running.client.get("/apps/loadcoach", headers={"Accept": "text/html"})
    assert "APP_VERSION_MISMATCH" in page.text
    assert "&gt;=1.0,&lt;2.0" in page.text or ">=1.0,<2.0" in page.text


@respx.mock
def test_the_version_is_cached_for_five_minutes_and_reprobed_after_a_control_action(
    running: Console,
) -> None:
    route = _version()
    running.login()
    for _ in range(3):
        running.client.get("/api/v1/apps/loadcoach")
    assert route.call_count == 1
    running.client.post("/api/v1/apps/loadcoach/restart", headers=JSON_HEADERS)
    running.client.get("/api/v1/apps/loadcoach")
    assert route.call_count == 2


@respx.mock
def test_an_unknown_application_is_404_by_name(running: Console) -> None:
    running.login()
    response = running.client.get("/api/v1/apps/ollama")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "APP_UNKNOWN"


@respx.mock
def test_health_is_the_applications_own_body_with_its_source(running: Console) -> None:
    _version()
    respx.get(f"{LOADCOACH_URL}/api/v1/health").mock(
        return_value=httpx.Response(200, json={"status": "ok", "components": [{"name": "db"}]})
    )
    running.login()
    body = running.client.get("/api/v1/apps/loadcoach/health").json()
    assert body == {"source": "api", "status": "ok", "components": [{"name": "db"}]}


@respx.mock
def test_health_of_a_stopped_application_comes_from_the_unit(stopped: Console) -> None:
    stopped.login()
    body = stopped.client.get("/api/v1/apps/loadcoach/health").json()
    assert body == {
        "source": "unit",
        "state": "stopped",
        "app": "loadcoach",
        "unit_state": "inactive",
    }


@respx.mock
def test_health_of_a_running_application_that_does_not_answer_is_unreachable(
    running: Console,
) -> None:
    _version()
    respx.get(f"{LOADCOACH_URL}/api/v1/health").mock(side_effect=httpx.ConnectError("refused"))
    running.login()
    response = running.client.get("/api/v1/apps/loadcoach/health")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "APP_UNREACHABLE"


@respx.mock
def test_start_is_202_with_the_audit_id_and_the_new_state(stopped: Console) -> None:
    _version()
    stopped.login()
    response = stopped.client.post("/api/v1/apps/loadcoach/start", headers=JSON_HEADERS)
    assert response.status_code == 202
    body = response.json()
    assert body["unit"] == "loadcoach.service"
    assert body["unit_state"] == "active"
    assert stopped.host is not None
    assert ("act", "user", "loadcoach.service", "start") in stopped.host.calls
    row = stopped.client.get(f"/api/v1/audit/{body['audit_id']}").json()
    assert row["action"] == "unit.start"
    assert row["target"] == "loadcoach.service"
    assert row["outcome"] == "ok"
    assert row["operator"] == "jordan"


@respx.mock
def test_a_verb_systemd_refuses_is_502_and_still_writes_the_row(tmp_path: Path) -> None:
    console = _console(
        tmp_path,
        systemd=FakeSystemdController(
            states={"loadcoach.service": "inactive"},
            refuse={("loadcoach.service", "start"): "Failed to start: Unit not found."},
        ),
    )
    console.login()
    response = console.client.post("/api/v1/apps/loadcoach/start", headers=JSON_HEADERS)
    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == "UNIT_ACTION_FAILED"
    assert "Unit not found" in error["message"]
    rows = console.client.get("/api/v1/audit?action=unit.start").json()["items"]
    assert len(rows) == 1
    assert rows[0]["outcome"] == "failed"


@respx.mock
def test_starting_an_application_that_is_not_installed_is_refused_by_name(
    running: Console,
) -> None:
    running.login()
    response = running.client.post("/api/v1/apps/freeweight/start", headers=JSON_HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "APP_NOT_INSTALLED"


@respx.mock
def test_a_host_without_systemd_reports_unsupported_and_the_page_still_renders(
    tmp_path: Path,
) -> None:
    console = _console(tmp_path, systemd=FakeSystemdController(supported=False))
    console.login()
    body = console.client.get("/api/v1/apps/loadcoach").json()
    assert body["unit_state"] == "unsupported"
    assert body["state"] == "unsupported"
    page = console.client.get("/apps/loadcoach", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "unsupported on this host" in page.text
    response = console.client.post("/api/v1/apps/loadcoach/start", headers=JSON_HEADERS)
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "UNIT_UNSUPPORTED"


@respx.mock
def test_the_page_control_form_acts_and_redirects_back(stopped: Console) -> None:
    _version()
    stopped.login()
    response = stopped.post_form("/apps/loadcoach/control", {"verb": "start"})
    assert response.status_code == 303
    assert response.headers["location"] == "/apps/loadcoach"
    assert stopped.host is not None
    assert ("act", "user", "loadcoach.service", "start") in stopped.host.calls


@respx.mock
def test_the_page_control_form_refuses_a_verb_outside_the_three(stopped: Console) -> None:
    stopped.login()
    response = stopped.post_form("/apps/loadcoach/control", {"verb": "isolate"})
    assert response.status_code == 400
    assert stopped.host is not None
    assert not [call for call in stopped.host.calls if call[0] == "act"]


def test_logs_history_is_the_page_shape(tmp_path: Path) -> None:
    journal = StubJournal()
    console = _console(tmp_path, journal=journal)
    console.login()
    body = console.client.get("/api/v1/apps/loadcoach/logs?level=warning&q=boom&limit=7").json()
    assert body["app"] == "loadcoach"
    assert body["lines"][0]["message"] == "started"
    assert body["has_more"] is False
    units, kwargs = journal.asked[0]
    assert units == ("loadcoach.service",)
    assert kwargs["level"] == "warning" and kwargs["query"] == "boom" and kwargs["limit"] == 7


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


def test_the_live_stream_is_enveloped_sse_frames(tmp_path: Path) -> None:
    events = [
        Event(
            sequence=n,
            type="log",
            payload={"message": f"line {n}", "app": "loadcoach", "level": "info"},
        )
        for n in range(1, 4)
    ]
    console = _console(tmp_path, journal=StubJournal(events=events))
    console.login()
    with console.client.stream("GET", "/api/v1/apps/loadcoach/logs/stream") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache, no-store"
        text = "".join(response.iter_text())
    frames = _frames(text)
    assert [name for name, _ in frames] == ["log", "log", "log", "log.closed"]
    assert [body["payload"]["message"] for name, body in frames if name == "log"] == [
        "line 1",
        "line 2",
        "line 3",
    ]
    # ADR-0025 §3: every non-token frame is enveloped and names its producer.
    assert frames[0][1]["generator"]["name"] == "weightroom"
    assert "id: 1\n" in text


def test_a_slow_consumer_is_told_how_many_lines_it_lost(tmp_path: Path) -> None:
    events = [
        Event(sequence=n, type="log", payload={"message": f"line {n}", "app": "loadcoach"})
        for n in range(1, 11)
    ]
    console = _console(tmp_path, journal=StubJournal(events=events, maxlen=4))
    console.login()
    with console.client.stream("GET", "/api/v1/apps/loadcoach/logs/stream") as response:
        text = "".join(response.iter_text())
    frames = _frames(text)
    dropped = [body["payload"] for name, body in frames if name == "log.dropped"]
    assert dropped, "the stream must say it fell behind, not serve a log with holes"
    assert dropped[0]["total"] == 7  # ten lines plus the closing event, into a queue of four


def test_the_unified_stream_covers_every_unit_including_weightrooms_own(tmp_path: Path) -> None:
    journal = StubJournal()
    console = _console(tmp_path, journal=journal)
    console.login()
    with console.client.stream("GET", "/api/v1/logs/stream") as response:
        "".join(response.iter_text())
    units, _kwargs = journal.asked[0]
    assert units == (
        "freeweight.service",
        "loadcoach.service",
        "ideapress.service",
        "promptcadence.service",
        "weightroom.service",
    )


def test_the_unified_stream_takes_a_subset_and_refuses_an_unknown_name(tmp_path: Path) -> None:
    journal = StubJournal()
    console = _console(tmp_path, journal=journal)
    console.login()
    with console.client.stream("GET", "/api/v1/logs/stream?apps=loadcoach,freeweight") as response:
        "".join(response.iter_text())
    assert journal.asked[0][0] == ("loadcoach.service", "freeweight.service")
    response = console.client.get("/api/v1/logs/stream?apps=nonsense")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "APP_UNKNOWN"


def test_a_host_without_journalctl_ends_the_stream_with_the_reason(tmp_path: Path) -> None:
    console = _console(tmp_path)  # the default reader has no journalctl
    console.login()
    with console.client.stream("GET", "/api/v1/apps/loadcoach/logs/stream") as response:
        text = "".join(response.iter_text())
    frames = _frames(text)
    assert frames[0][0] == "error"
    assert frames[0][1]["payload"]["code"] == "UNIT_UNSUPPORTED"


def test_every_apps_route_needs_a_session(tmp_path: Path) -> None:
    console = _console(tmp_path, host="10.77.10.84")
    for path in (
        "/api/v1/apps",
        "/api/v1/apps/loadcoach",
        "/api/v1/apps/loadcoach/health",
        "/api/v1/apps/loadcoach/logs",
        "/api/v1/apps/loadcoach/logs/stream",
        "/api/v1/logs/stream",
    ):
        response = console.client.get(path, headers={"Host": "jordan-main.local"})
        assert response.status_code == 401, path


@respx.mock
def test_every_page_renders_with_an_application_running(running: Console) -> None:
    _version()
    running.login()
    for path in ("/", "/apps", "/apps/loadcoach", "/logs"):
        response = running.client.get(path, headers={"Accept": "text/html"})
        assert response.status_code == 200, path
        assert "loadcoach" in response.text, path
    apps_page = running.client.get("/apps", headers={"Accept": "text/html"}).text
    assert "status-success" in apps_page  # the pill is green while it is up
    assert 'value="stop"' in apps_page


@respx.mock
def test_every_page_still_renders_with_every_application_stopped(stopped: Console) -> None:
    """Plan Phase 2 criterion 2: stopping one leaves every page rendering."""
    stopped.login()
    for path in ("/", "/apps", "/apps/loadcoach", "/logs", "/audit"):
        response = stopped.client.get(path, headers={"Accept": "text/html"})
        assert response.status_code == 200, path
    page = stopped.client.get("/apps/loadcoach", headers={"Accept": "text/html"}).text
    assert "stopped" in page
    assert 'value="start"' in page
    # The Overview page's log tail (row W3) is MirrorWall 0.3's log_pane macro, not the
    # pre-0.3 `_log_pane.html` module the unified /logs page below still uses.
    assert 'sse-connect="/api/v1/apps/loadcoach/logs/stream"' in page


def test_the_unified_page_names_every_unit_and_streams_from_one_place(tmp_path: Path) -> None:
    console = _console(tmp_path, journal=StubJournal())
    console.login()
    page = console.client.get("/logs", headers={"Accept": "text/html"}).text
    assert 'data-log-stream="/api/v1/logs/stream"' in page
    for name in ("freeweight", "loadcoach", "ideapress", "promptcadence", "weightroom"):
        assert name in page


def test_the_audit_page_filters_by_application_action_and_date(tmp_path: Path) -> None:
    console = _console(
        tmp_path, systemd=FakeSystemdController(states={"loadcoach.service": "active"})
    )
    console.login()
    console.client.post("/api/v1/apps/loadcoach/restart", headers=JSON_HEADERS)

    page = console.client.get("/audit?action=unit.restart", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "unit.restart" in page.text
    assert 'value="unit.restart" selected' in page.text
    assert "login" not in page.text.split("<tbody")[-1]

    empty = console.client.get("/audit?app=ideapress", headers={"Accept": "text/html"})
    assert "No rows match these filters" in empty.text
    assert "Clear the filters" in empty.text


def test_the_audit_page_ignores_an_unparseable_date_rather_than_refusing(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    page = console.client.get("/audit?since=yesterday", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "is not a date or timestamp" in page.text
    assert "login" in page.text


def test_the_audit_page_since_filter_selects_by_instant(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    past = console.client.get("/audit?since=2026-09-08", headers={"Accept": "text/html"})
    assert "login" in past.text
    future = console.client.get("/audit?since=2026-09-10", headers={"Accept": "text/html"})
    assert "No rows match these filters" in future.text


@respx.mock
def test_activating_reads_as_starting_not_stopped(tmp_path: Path) -> None:
    """Found live at row W2: LoadCoach sat in `activating` for seconds and the pill said stopped."""
    console = _console(
        tmp_path, systemd=FakeSystemdController(states={"loadcoach.service": "activating"})
    )
    console.login()
    body = console.client.get("/api/v1/apps/loadcoach").json()
    assert body["unit_state"] == "activating"
    assert body["state"] == "starting"
    page = console.client.get("/apps", headers={"Accept": "text/html"}).text
    assert "status-warning" in page


@respx.mock
def test_deactivating_reads_as_stopping(tmp_path: Path) -> None:
    console = _console(
        tmp_path, systemd=FakeSystemdController(states={"loadcoach.service": "deactivating"})
    )
    console.login()
    assert console.client.get("/api/v1/apps/loadcoach").json()["state"] == "stopping"


@respx.mock
def test_the_nested_version_shape_negotiates(running: Console) -> None:
    respx.get(f"{LOADCOACH_URL}/api/v1/version").mock(
        return_value=httpx.Response(
            200,
            json={
                "application": {"name": "loadcoach", "version": "1.3.1", "git_commit": None},
                "api": {"current": "v1", "supported": ["v1"], "deprecated": []},
            },
        )
    )
    running.login()
    body = running.client.get("/api/v1/apps/loadcoach").json()
    assert body["version"] == "1.3.1"
    assert body["api_version"] == "v1"
    assert body["version_verdict"] == "ok"
    assert body["state"] == "ok"


@respx.mock
def test_a_failed_probe_is_not_cached_so_a_starting_application_is_seen_when_it_comes_up(
    running: Console,
) -> None:
    """Found live at row W2: caching the refusal showed *starting* long after it had started."""
    route = respx.get(f"{LOADCOACH_URL}/api/v1/version").mock(
        side_effect=[
            httpx.ConnectError("still binding"),
            httpx.Response(200, json={"application": "loadcoach", "version": "1.3.1"}),
        ]
    )
    running.login()
    assert running.client.get("/api/v1/apps/loadcoach").json()["state"] == "starting"
    assert running.client.get("/api/v1/apps/loadcoach").json()["version"] == "1.3.1"
    assert route.call_count == 2
    # The success *is* cached.
    running.client.get("/api/v1/apps/loadcoach")
    assert route.call_count == 2
