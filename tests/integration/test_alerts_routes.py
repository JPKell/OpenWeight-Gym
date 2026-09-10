"""The banner on every page, the Alerts pages and API, and acknowledging (api.md §7, ADR-0137)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from tests.support import JSON_HEADERS, Console, build_console
from weightroom.domain.alerts import Firing, Reading
from weightroom.infrastructure.db.models import AuditLog
from weightroom.services.alerts import active_alerts, apply

if TYPE_CHECKING:
    from pathlib import Path

HTML = {"Accept": "text/html"}
KILL = (
    "oom-kill:constraint=CONSTRAINT_MEMCG,oom_memcg=/system.slice/ollama.service,"
    "task_memcg=/system.slice/ollama.service,task=ollama,pid=4242"
)


def _console(tmp_path: Path) -> Console:
    console = build_console(tmp_path)
    console.login()
    return console


def _memory_cap(console: Console) -> str:
    firing = Firing("ollama.service", {"line": KILL, "cursor": "c1"})
    apply(console.database, Reading("memory_cap", (firing,)), now=console.now)
    return active_alerts(console.database)[0].id


def _ack_rows(console: Console) -> list[str]:
    with console.database.read() as session:
        rows = session.execute(select(AuditLog).where(AuditLog.action == "alert.ack")).scalars()
        return [row.outcome for row in rows]


def test_the_banner_shows_on_every_page_until_the_alert_is_acknowledged(tmp_path: Path) -> None:
    console = _console(tmp_path)
    assert "memory cap fired" not in console.client.get("/", headers=HTML).text
    alert_id = _memory_cap(console)

    page = console.client.get("/jobs", headers=HTML).text
    assert "memory cap fired · ollama.service" in page
    assert KILL in page
    assert 'hx-get="/alerts/banner"' in page
    assert "⚠ 1" in page
    fragment = console.client.get(
        "/alerts/banner", headers={**HTML, "HX-Current-URL": "https://localhost/jobs"}
    ).text
    assert "memory cap fired · ollama.service" in fragment
    assert 'name="next" value="/jobs"' in fragment
    listed = console.client.get("/api/v1/alerts").json()
    assert listed["banner"]["count"] == 1
    assert listed["alerts"][0]["summary"] == KILL

    console.advance(seconds=20)
    acknowledged = console.post_form(f"/alerts/{alert_id}/acknowledge", {"next": "/jobs"})

    assert acknowledged.status_code == 303
    assert acknowledged.headers["location"] == "/jobs"
    assert "memory cap fired · ollama.service" not in console.client.get("/", headers=HTML).text
    events = console.client.get("/api/v1/alerts/history").json()["items"]
    assert [row["event"] for row in events] == ["acknowledged", "opened"]
    assert _ack_rows(console) == ["ok"]
    alerts_page = console.client.get("/alerts", headers=HTML)
    assert alerts_page.status_code == 200
    assert "acknowledged by jordan" in alerts_page.text
    assert console.client.get("/alerts/history", headers=HTML).status_code == 200


def test_acknowledging_through_the_api_and_an_unknown_alert(tmp_path: Path) -> None:
    console = _console(tmp_path)
    alert_id = _memory_cap(console)
    acknowledged = console.client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge", headers=JSON_HEADERS
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged_by"] == "jordan"
    missing = console.client.post(
        "/api/v1/alerts/01NOSUCHALERT0000000000000/acknowledge", headers=JSON_HEADERS
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert _ack_rows(console) == ["ok", "refused"]


def test_acknowledging_never_redirects_off_the_site(tmp_path: Path) -> None:
    console = _console(tmp_path)
    alert_id = _memory_cap(console)
    response = console.post_form(f"/alerts/{alert_id}/acknowledge", {"next": "//evil.example/"})
    assert response.headers["location"] == "/alerts"
