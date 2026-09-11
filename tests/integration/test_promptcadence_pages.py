"""Row WP1 Gate B: PromptCadence's six pages — against its recorded API, and against its database.

The recordings under ``tests/fixtures/promptcadence`` are the reference machine's own PromptCadence
1.3.3 answering on 2026-09-10 for one trajectory ("State in one sentence what 2+2 is."); the stopped
half reads a copy of the committed ``promptcadence-0011`` fixture database with rows added per test.
"""

from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path
from typing import Any

import httpx
import respx

from tests.security.test_chat_isolation import HOSTILE, _assert_inert
from tests.support import (
    CHAT_FIXTURES,
    PROMPTCADENCE_URL,
    RECORDED_TRAJECTORY,
    Console,
    build_console,
    fake_application,
    fill_rows,
    fixture_database,
)
from weightroom.services.apps import AppState
from weightroom.services.processes import FakeSystemdController
from weightroom.web.rendering import app_side_nav_stubs

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "promptcadence"
HTML = {"Accept": "text/html"}
TRAJECTORY = "01M273A83QK9QYQWVD07X8QHA4"
STOPPED = "01STOPPEDTRAJECTORY000001"
BASE = "/apps/promptcadence"


def _fixture(name: str) -> Any:  # noqa: ANN401 — a recorded JSON document
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _console(
    tmp_path: Path, *, state: AppState, revision: str | None = None
) -> tuple[Console, Path]:
    database = fixture_database(tmp_path, "promptcadence-0011")
    if revision is not None:
        connection = sqlite3.connect(database)
        connection.execute("UPDATE alembic_version SET version_num = ?", (revision,))
        connection.commit()
        connection.close()
    executable, _config, _document = fake_application(
        tmp_path, "promptcadence", database_url=f"sqlite:///{database}"
    )
    console = build_console(
        tmp_path / "console",
        extra_toml=(
            f'[apps.promptcadence]\nexecutable = "{executable}"\nbase_url = "{PROMPTCADENCE_URL}"\n'
        ),
        systemd=FakeSystemdController(states={"promptcadence.service": state}),
    )
    console.login()
    return console, database


def _mock_api(router: Any, *, version: str = "1.3.3", **bodies: Any) -> dict[str, Any]:  # noqa: ANN401
    router.get(f"{PROMPTCADENCE_URL}/api/v1/version").mock(
        return_value=httpx.Response(
            200, json={"application": "promptcadence", "version": version, "api_version": "v1"}
        )
    )
    recorded: dict[str, Any] = {
        "trajectories": _fixture("trajectories"),
        f"trajectories/{TRAJECTORY}/explanation": _fixture("explanation"),
        "approvals": _fixture("approvals"),
        "tiers": _fixture("tiers"),
        "tools": _fixture("tools"),
        "ledger": _fixture("ledger"),
        "ledger/entries": _fixture("ledger-entries"),
    }
    recorded.update({key.replace("__", "/"): value for key, value in bodies.items()})
    return {
        path: router.get(f"{PROMPTCADENCE_URL}/api/v1/{path}").mock(
            return_value=httpx.Response(200, json=body)
        )
        for path, body in recorded.items()
    }


def _page(console: Console, path: str) -> str:
    response = console.client.get(path, headers=HTML)
    assert response.status_code == 200, response.text
    return str(response.text)


def test_every_promptcadence_page_is_built_and_none_is_a_stub() -> None:
    assert app_side_nav_stubs("promptcadence") == ()


def test_running_pages_read_promptcadences_api(tmp_path: Path) -> None:
    console, _database = _console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        _mock_api(router)
        listing = _page(console, f"{BASE}/trajectories")
        detail = _page(console, f"{BASE}/trajectories/{TRAJECTORY}")
        approvals = _page(console, f"{BASE}/approvals")
        tiers = _page(console, f"{BASE}/tiers")
        tools = _page(console, f"{BASE}/tools")
        ledger = _page(console, f"{BASE}/ledger")
    assert "State in one sentence what 2+2 is." in listing
    assert f'href="{BASE}/trajectories/{TRAJECTORY}"' in listing
    assert (
        '<a href="/apps/promptcadence/trajectories" aria-current="page">Trajectories</a>' in listing
    )
    assert "From the API" in listing
    assert "Drafting attempts" in detail
    assert "target_not_remote" in detail  # the egress decision the explanation holds
    assert "Every persisted event, in sequence order" in detail
    assert "data-log-stream" not in detail  # a completed trajectory has no live pane
    assert "Nothing is waiting for a person." in approvals
    assert "From the database at revision 0011" in approvals  # the history's own source
    assert "tools.agent.local_fast" in tiers
    assert "docker" in tools
    assert "read_file" in tools
    assert "at most 20 USD" in ledger
    assert "tier:local_fast" in ledger


def test_egress_is_read_newest_first_from_the_database_even_while_running(tmp_path: Path) -> None:
    console, database = _console(tmp_path, state="active")
    fill_rows(
        database,
        "egress_decisions",
        [
            {
                "decision_id": f"01EGRESS00000000000000000{index}",
                "run_id": TRAJECTORY,
                "verdict": verdict,
                "target_name": "local_fast",
                "decided_at": f"2026-09-10T0{index}:00:00Z",
                "decision_json": json.dumps({"reason": reason, "policy_name": "Ordered"}),
            }
            for index, (verdict, reason) in enumerate(
                [("approved", "older_reason"), ("denied", "newer_reason")]
            )
        ],
    )
    with respx.mock(assert_all_called=False) as router:
        _mock_api(router)
        page = _page(console, f"{BASE}/egress")
        denied = _page(console, f"{BASE}/egress?verdict=denied")
    assert page.index("newer_reason") < page.index("older_reason")
    assert "From the database at revision 0011" in page
    assert "newer_reason" in denied
    assert "older_reason" not in denied


def test_stopped_pages_read_the_database_with_a_start_beside_them(tmp_path: Path) -> None:
    console, database = _console(tmp_path, state="inactive")
    fill_rows(
        database,
        "trajectories",
        [
            {
                "id": STOPPED,
                "task": "a task recorded before the stop",
                "status": "completed",
                "data_classification": "internal",
                "created_at": "2026-09-10T00:00:00Z",
            }
        ],
    )
    fill_rows(
        database,
        "turns",
        [
            {
                "id": "01TURN0000000000000000001",
                "thread_id": "01THREAD",
                "trajectory_id": STOPPED,
                "sequence": 1,
                "role": "assistant",
                "content_text": "the answer read from the database",
                "created_at": "2026-09-10T00:00:01Z",
            }
        ],
    )
    fill_rows(
        database,
        "approval_requests",
        [
            {
                "id": "01REQUEST0000000000000009",
                "trajectory_id": STOPPED,
                "status": "pending",
                "kind": "plan",
                "reason": "the plan needs a person",
                "created_at": "2026-09-10T00:00:02Z",
            }
        ],
    )
    fill_rows(
        database,
        "ledger_entries",
        [
            {
                "entry_id": "01ENTRY",
                "run_id": STOPPED,
                "source_ref": "01TURN0000000000000000001",
                "occurred_at": "2026-09-10T00:00:03Z",
                "unpriced": 1,
                "debit_json": json.dumps({"usage": {"input": 5}, "tags": ["tier:recorded"]}),
            }
        ],
    )
    listing = _page(console, f"{BASE}/trajectories")
    assert "a task recorded before the stop" in listing
    assert "From the database at revision 0011" in listing
    assert 'name="next" value="/apps/promptcadence/trajectories"' in listing
    detail = _page(console, f"{BASE}/trajectories/{STOPPED}")
    assert "the answer read from the database" in detail
    assert "PromptCadence is not answering" in detail
    assert "the plan needs a person" in _page(console, f"{BASE}/approvals")
    ledger = _page(console, f"{BASE}/ledger")
    assert "tier:recorded" in ledger
    assert 'href="/costs"' in ledger
    for path in ("tiers", "tools"):
        assert "reads only from its running API" in _page(console, f"{BASE}/{path}")


def test_an_unknown_revision_degrades_each_database_page_by_name(tmp_path: Path) -> None:
    console, _database = _console(tmp_path, state="inactive", revision="9999")
    for path in ("trajectories", "approvals", "ledger", "egress"):
        page = _page(console, f"{BASE}/{path}")
        assert "SCHEMA_UNKNOWN" in page, path
        assert "9999" in page, path


def test_a_version_outside_the_range_reads_neither_source(tmp_path: Path) -> None:
    console, _database = _console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        routes = _mock_api(router, version="9.0.0")
        page = _page(console, f"{BASE}/trajectories")
    assert "APP_VERSION_MISMATCH" in page
    assert not routes["trajectories"].called


def test_a_live_trajectory_streams_as_log_frames_that_close_on_the_terminal_event(
    tmp_path: Path,
) -> None:
    console, _database = _console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        _mock_api(router)
        router.get(f"{PROMPTCADENCE_URL}/api/v1/trajectories/{RECORDED_TRAJECTORY}/stream").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=(CHAT_FIXTURES / "promptcadence-1.3.3-completed.sse").read_bytes(),
            )
        )
        response = console.client.get(f"{BASE}/trajectories/{RECORDED_TRAJECTORY}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert "event: log\n" in text
    assert "plan.drafted" in text
    assert text.index("trajectory.completed") < text.index("event: log.closed")


def test_the_injection_corpus_renders_inert_on_every_page_that_shows_model_or_operator_text(
    tmp_path: Path,
) -> None:
    explanation = copy.deepcopy(_fixture("explanation"))
    explanation["trajectory"]["task"] = HOSTILE
    explanation["trajectory"]["cause"] = HOSTILE
    explanation["threads"][0]["turns"][0]["content"]["text"] = HOSTILE
    hostile_list = {
        "items": [
            {"trajectory_id": TRAJECTORY, "task": HOSTILE, "state": "halted", "cause": HOSTILE}
        ],
        "page": {"next_cursor": None},
    }
    hostile_approvals = {
        "items": [
            {
                "request_id": "01REQUEST",
                "trajectory_id": TRAJECTORY,
                "kind": "reapproval",
                "reason": HOSTILE,
                "detail": {"why": HOSTILE},
            }
        ]
    }
    console, _database = _console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        _mock_api(
            router,
            trajectories=hostile_list,
            approvals=hostile_approvals,
            **{f"trajectories__{TRAJECTORY}__explanation": explanation},
        )
        listing = _page(console, f"{BASE}/trajectories")
        detail = _page(console, f"{BASE}/trajectories/{TRAJECTORY}")
        approvals = _page(console, f"{BASE}/approvals")
    _assert_inert(detail)
    for page in (listing, approvals):
        assert "<script>alert(1)</script>" not in page
        assert 'href="javascript:' not in page
        assert 'src="http://evil.example.net' not in page
