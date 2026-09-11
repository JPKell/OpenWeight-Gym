"""The database fallback reader and the trajectory stream's conversion to log-pane frames."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from mirrorwall import Event, format_frame
from setspec import GeneratorInfo

from weightroom.services.app_pages import rows_where
from weightroom.services.db_reader import (
    AppDatabase,
    ReadFailed,
    Revision,
    TableUnknown,
    open_read_only,
)
from weightroom.services.promptcadence_pages import event_log_frames


@pytest.fixture
def handle(tmp_path: Path) -> AppDatabase:
    path = tmp_path / "pc.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE decisions (id TEXT PRIMARY KEY, verdict TEXT, decided_at TEXT)"
    )
    connection.executemany(
        "INSERT INTO decisions VALUES (?, ?, ?)",
        [
            ("a", "approved", "2026-09-10T01"),
            ("b", "denied", "2026-09-10T02"),
            ("c", "approved", "2026-09-10T03"),
        ],
    )
    connection.commit()
    connection.close()
    url = f"sqlite:///{path}"
    revision = Revision(
        app="promptcadence", found="0011", known=("0011",), dialect="sqlite", database_url=url
    )
    return AppDatabase("promptcadence", url, open_read_only(url), revision, timeout_seconds=5.0)


def test_rows_filter_by_equality_skip_unset_filters_and_order_newest_first(
    handle: AppDatabase,
) -> None:
    rows = rows_where(
        handle, "decisions", equals={"verdict": "approved", "id": None}, order_by="decided_at"
    )
    assert [row["id"] for row in rows] == ["c", "a"]
    oldest = rows_where(
        handle, "decisions", order_by="decided_at", descending=False, limit=1, offset=1
    )
    assert [row["id"] for row in oldest] == ["b"]


def test_an_unknown_table_or_column_is_refused_by_name(handle: AppDatabase) -> None:
    with pytest.raises(TableUnknown):
        rows_where(handle, "nope")
    with pytest.raises(ReadFailed, match="'status' is not a column"):
        rows_where(handle, "decisions", equals={"status": "x"})
    with pytest.raises(ReadFailed):
        rows_where(handle, "decisions", order_by="decided_at; DROP TABLE decisions")


def _frame(event: str, data: dict[str, object]) -> str:
    envelope = {"payload": {"type": event, "data": data, "timestamp": "2026-09-10T00:00:00Z"}}
    return f"event: {event}\ndata: {json.dumps(envelope)}\n\n"


def _events(text: str) -> list[tuple[str, dict[str, object]]]:
    found = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        found.append((fields["event"], json.loads(fields["data"])["payload"]))
    return found


def test_frames_split_across_chunks_become_whole_log_lines() -> None:
    whole = _frame("step.started", {"step_id": "s1", "trajectory_id": "t"})
    chunks = [whole[:17], whole[17:40], whole[40:]]
    events = _events("".join(event_log_frames(chunks)))
    assert events[0][0] == "log"
    assert events[0][1]["app"] == "step.started"
    assert events[0][1]["message"] == "step_id=s1"
    assert events[-1][0] == "log.closed"


def test_a_halt_is_an_error_line_and_ends_the_stream_there() -> None:
    text = "".join(
        event_log_frames(
            [
                _frame("trajectory.halted", {"cause": "denied"}),
                _frame("step.started", {"step_id": "late"}),
            ]
        )
    )
    events = _events(text)
    assert [kind for kind, _payload in events] == ["log", "log.closed"]
    assert events[0][1]["level"] == "err"
    assert "late" not in text


def test_the_consoles_own_error_frame_becomes_a_line_and_a_close() -> None:
    generator = GeneratorInfo(name="weightroom", version="test")
    error = format_frame(
        Event(sequence=0, type="error", payload={"code": "TRAJECTORY_NOT_FOUND", "message": "no"}),
        generator=generator,
    )
    events = _events("".join(event_log_frames([error])))
    assert events[0][1]["message"] == "TRAJECTORY_NOT_FOUND: no"
    assert events[-1][0] == "log.closed"
