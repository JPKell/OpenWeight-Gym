"""weightroom.services.promptcadence_pages — the data behind PromptCadence's tab (row WP1).

Each page has two readers: one over PromptCadence's own ``/api/v1`` (through
:mod:`~weightroom.services.app_api`) for while it answers, and one over its database
(``data-model.md`` §4) for while it does not, shaping the rows into the keys the page renders.
Which one runs is :mod:`~weightroom.services.app_pages`' decision, never this module's; what the
rows say is rendered by the templates, escaped.

Two readers use the database even while PromptCadence runs, because its API has no view of the
subject (spec §7.3: "where the API has no view — a read of its database"): **every** approval
request, resolved ones included (``GET /approvals`` lists pending ones, and resolved ones only per
trajectory), and the egress decisions newest first (``GET /egress-decisions`` lists the oldest
first with no cursor, so its first 200 are the wrong 200).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Final
from urllib.parse import quote

from baseaicore import SuiteError
from mirrorwall import Event, format_frame
from setspec import GeneratorInfo

from weightroom.__about__ import __version__
from weightroom.services.app_api import call
from weightroom.services.app_pages import rows_where
from weightroom.services.chat_loadcoach import iter_frames
from weightroom.services.chat_promptcadence import HALT_EVENTS

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings
    from weightroom.services.db_reader import AppDatabase

__all__ = [
    "APP",
    "TRAJECTORY_STATES",
    "VERDICTS",
    "TrajectoryNotRecorded",
    "egress_db",
    "event_log_frames",
    "ledger_api",
    "ledger_db",
    "pending_api",
    "pending_db",
    "requests_db",
    "segment",
    "tiers_api",
    "tools_api",
    "trajectories_api",
    "trajectories_db",
    "trajectory_api",
    "trajectory_db",
]

APP: Final = "promptcadence"
PAGE_ROWS: Final = 50
LIST_CAP: Final = 200
"""PromptCadence clamps every listing to 200 (API standards §6); a database read keeps the cap."""

TRAJECTORY_STATES: Final[tuple[str, ...]] = (
    "queued",
    "planning",
    "awaiting_approval",
    "awaiting_window",
    "executing",
    "completed",
    "rejected",
    "halted",
    "failed",
    "cancelled",
)
"""PromptCadence's ``TrajectoryState`` members, in its declaration order (lifecycle §8.1)."""
VERDICTS: Final[tuple[str, ...]] = ("approved", "denied", "violation")
TERMINAL_EVENTS: Final[frozenset[str]] = HALT_EVENTS | {"trajectory.completed"}
_SUMMARY_CHARS: Final = 300
_GENERATOR = GeneratorInfo(name="weightroom", version=__version__)


class TrajectoryNotRecorded(SuiteError):
    """PromptCadence's database holds no trajectory with that id."""

    code: ClassVar[str] = "NOT_FOUND"


def segment(value: str) -> str:
    """``value`` quoted as one path segment, so an id can never add a segment or a query."""
    return quote(value, safe="")


def _loads(value: Any) -> Any:  # noqa: ANN401 — a stored JSON column, whatever it holds
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _items(body: Any) -> list[dict[str, Any]]:  # noqa: ANN401 — a collection envelope
    items = body.get("items") if isinstance(body, Mapping) else None
    return [dict(one) for one in items or [] if isinstance(one, Mapping)]


# --- Trajectories ---------------------------------------------------------------------------------


def trajectories_api(
    client: httpx.Client, settings: Settings, *, state: str | None, cursor: str | None
) -> dict[str, Any]:
    """``GET /trajectories``: one page, newest first, with PromptCadence's own cursor.

    Raises:
        AppRefused: PromptCadence refused (an unknown ``state`` is its ``VALIDATION_ERROR``).
        AppUnreachable: It did not answer.
    """
    body = call(
        client, settings, APP, "GET", "trajectories",
        params={"state": state, "cursor": cursor, "limit": PAGE_ROWS},
    )  # fmt: skip
    page = body.get("page") if isinstance(body, Mapping) else None
    return {
        "items": _items(body),
        "next_cursor": page.get("next_cursor") if isinstance(page, Mapping) else None,
        "next_page": None,
    }


def _trajectory_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """A ``trajectories`` row under the API document's names (its columns differ: ``status``)."""
    return {
        "trajectory_id": row.get("id"),
        "task": row.get("task"),
        "state": row.get("status"),
        "data_classification": row.get("data_classification"),
        "project": row.get("project"),
        "tools": _loads(row.get("tools_json")),
        "bypass_planning": bool(row.get("bypass_planning")),
        "tier": row.get("tier_override"),
        "budget_tokens": row.get("budget_token_ceiling"),
        "cause": row.get("halted_reason"),
        "error_code": row.get("error_code"),
        "created_at": row.get("created_at"),
        "completed_at": row.get("completed_at"),
    }


def trajectories_db(handle: AppDatabase, *, state: str | None, page: int) -> dict[str, Any]:
    """The ``trajectories`` table, newest first, one page by number.

    Raises:
        TableUnknown: The database has no ``trajectories`` table.
        ReadFailed: The database refused or ran past the timeout.
    """
    page = max(1, page)
    rows = rows_where(
        handle, "trajectories", equals={"status": state}, order_by="created_at",
        limit=PAGE_ROWS + 1, offset=(page - 1) * PAGE_ROWS,
    )  # fmt: skip
    return {
        "items": [_trajectory_row(row) for row in rows[:PAGE_ROWS]],
        "next_cursor": None,
        "next_page": page + 1 if len(rows) > PAGE_ROWS else None,
    }


def trajectory_api(client: httpx.Client, settings: Settings, trajectory_id: str) -> dict[str, Any]:
    """``GET /trajectories/{id}/explanation``: the whole record, the bytes PromptCadence renders.

    PromptCadence's own timeline page renders this one document, so every record type it holds is
    a record type this page shows, and the two consoles cannot drift apart.

    Raises:
        AppRefused: ``TRAJECTORY_NOT_FOUND``, or any other refusal.
        AppUnreachable: It did not answer.
    """
    explanation = call(
        client, settings, APP, "GET", f"trajectories/{segment(trajectory_id)}/explanation",
        timeout_seconds=30.0,
    )  # fmt: skip
    return {"explanation": explanation if isinstance(explanation, Mapping) else {}}


def trajectory_db(handle: AppDatabase, trajectory_id: str) -> dict[str, Any]:
    """One trajectory's rows across the tables that record it, oldest first within each.

    Raises:
        TrajectoryNotRecorded: No such trajectory in the database.
        TableUnknown: A table this reader expects is absent.
        ReadFailed: The database refused or ran past the timeout.
    """
    found = rows_where(handle, "trajectories", equals={"id": trajectory_id}, limit=1)
    if not found:
        raise TrajectoryNotRecorded(
            f"PromptCadence's database holds no trajectory {trajectory_id!r}.",
            details={"trajectory_id": trajectory_id},
        )
    mine = {"trajectory_id": trajectory_id}
    run = {"run_id": trajectory_id}
    return {
        "trajectory": _trajectory_row(found[0]),
        "turns": rows_where(
            handle, "turns", equals=mine, order_by="sequence", descending=False, limit=LIST_CAP * 5
        ),
        "tool_calls": rows_where(
            handle, "tool_call_records", equals=mine, order_by="created_at", descending=False,
            limit=LIST_CAP,
        ),
        "approvals": [
            _approval_row(row)
            for row in rows_where(
                handle, "approval_requests", equals=mine, order_by="created_at", descending=False,
                limit=LIST_CAP,
            )
        ],
        "egress": [
            _egress_row(row)
            for row in rows_where(
                handle, "egress_decisions", equals=run, order_by="decided_at", descending=False,
                limit=LIST_CAP,
            )
        ],
        "ledger": [
            _entry_row(row)
            for row in rows_where(
                handle, "ledger_entries", equals=run, order_by="occurred_at", descending=False,
                limit=LIST_CAP,
            )
        ],
        "events": rows_where(
            handle, "events", equals=mine, order_by="sequence", descending=False,
            limit=LIST_CAP * 5,
        ),
    }  # fmt: skip


def _summary(data: Mapping[str, Any]) -> str:
    parts = [
        f"{key}={value}"
        for key, value in data.items()
        if key != "trajectory_id" and isinstance(value, (str, int, float, bool)) and value != ""
    ]
    text = " ".join(parts)
    return text if len(text) <= _SUMMARY_CHARS else text[: _SUMMARY_CHARS - 1] + "…"


def _lines(chunks: Iterable[str]) -> Iterator[str]:
    """Stream text chunks as whole lines; a chunk boundary can fall anywhere in a frame."""
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        *complete, buffer = buffer.split("\n")
        for line in complete:
            yield line.removesuffix("\r")
    if buffer:
        yield buffer.removesuffix("\r")


def event_log_frames(chunks: Iterable[str]) -> Iterator[str]:
    """PromptCadence's trajectory stream as the frames the console's log pane reads.

    Each governance event becomes one ``log`` line (the event type where the pane names a unit,
    its scalar fields as the message); a halt is coloured as an error. The stream ends with
    ``log.closed`` on the terminal event, on the console's own ``error`` frame from
    :func:`~weightroom.services.app_api.stream`, or when PromptCadence closes it — the pane closes
    its ``EventSource`` then, rather than reconnecting to a stream that ends the same way each time.

    Args:
        chunks: :func:`~weightroom.services.app_api.stream`'s text.

    Yields:
        SSE frames, ``log`` then one ``log.closed``.
    """
    # ponytail: a reconnect replays the trajectory from its first event (the pane's own ids are
    # not PromptCadence's); forward upstream ids if a pane ever needs to resume mid-stream.
    sequence = 0

    def frame(kind: str, payload: dict[str, Any]) -> str:
        nonlocal sequence
        sequence += 1
        return format_frame(
            Event(sequence=sequence, type=kind, payload=payload), generator=_GENERATOR
        )

    for one in iter_frames(_lines(chunks)):
        envelope = one.data if isinstance(one.data, Mapping) else {}
        body = envelope.get("payload")
        body = body if isinstance(body, Mapping) else {}
        if one.event == "stream.closed":
            break
        if one.event == "error":
            yield frame(
                "log",
                {
                    "at": envelope.get("generated_at"),
                    "app": "error",
                    "level": "err",
                    "message": f"{body.get('code')}: {body.get('message')}",
                },
            )
            break
        data = body.get("data")
        yield frame(
            "log",
            {
                "at": body.get("timestamp") or envelope.get("generated_at"),
                "app": one.event,
                "level": "err" if one.event in HALT_EVENTS else "info",
                "message": _summary(data if isinstance(data, Mapping) else {}),
            },
        )
        if one.event in TERMINAL_EVENTS:
            break
    yield frame("log.closed", {"reason": "the trajectory's stream ended"})


# --- Approvals ------------------------------------------------------------------------------------


def _approval_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "request_id": row.get("id"),
        "trajectory_id": row.get("trajectory_id"),
        "kind": row.get("kind"),
        "status": row.get("status"),
        "reason": row.get("reason"),
        "step_ids": _loads(row.get("step_ids_json")) or [],
        "detail": _loads(row.get("detail_json")),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
        "resolved_at": row.get("resolved_at"),
        "approver_token_id": row.get("approver_token_id"),
        "resolution_reason": row.get("resolution_reason"),
        "age_seconds": None,
    }


def pending_api(client: httpx.Client, settings: Settings) -> list[dict[str, Any]]:
    """``GET /approvals``: every pending request with its age, oldest first.

    Raises:
        AppRefused: PromptCadence refused.
        AppUnreachable: It did not answer.
    """
    return _items(call(client, settings, APP, "GET", "approvals"))


def pending_db(handle: AppDatabase) -> list[dict[str, Any]]:
    """The pending ``approval_requests`` rows, oldest first; no age, which only the API computes."""
    return [
        _approval_row(row)
        for row in rows_where(
            handle, "approval_requests", equals={"status": "pending"}, order_by="created_at",
            descending=False, limit=LIST_CAP,
        )
    ]  # fmt: skip


def requests_db(handle: AppDatabase) -> list[dict[str, Any]]:
    """Every approval request, newest first — resolved ones included, which the API cannot list."""
    return [
        _approval_row(row)
        for row in rows_where(handle, "approval_requests", order_by="created_at", limit=LIST_CAP)
    ]


# --- Tiers, tools ---------------------------------------------------------------------------------


def tiers_api(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``GET /tiers``: the tier snapshot, each tier's availability and why not (ADR-0098)."""
    body = call(client, settings, APP, "GET", "tiers")
    return dict(body) if isinstance(body, Mapping) else {}


def tools_api(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``GET /tools``: the registry, withheld tools with their cause, and the isolation probe."""
    body = call(client, settings, APP, "GET", "tools")
    return dict(body) if isinstance(body, Mapping) else {}


# --- Ledger, egress -------------------------------------------------------------------------------


def ledger_api(
    client: httpx.Client, settings: Settings, *, trajectory_id: str | None, tag: str | None
) -> dict[str, Any]:
    """``GET /ledger`` and ``GET /ledger/entries``: today's position and the debits behind it.

    Raises:
        AppRefused: ``TRAJECTORY_NOT_FOUND`` for an unknown ``trajectory_id``, or another refusal.
        AppUnreachable: It did not answer.
    """
    position = call(client, settings, APP, "GET", "ledger", params={"trajectory_id": trajectory_id})
    entries = call(
        client, settings, APP, "GET", "ledger/entries",
        params={"trajectory_id": trajectory_id, "tag": tag, "limit": LIST_CAP},
    )  # fmt: skip
    return {
        "position": position if isinstance(position, Mapping) else None,
        "entries": _items(entries),
    }


def _entry_row(row: Mapping[str, Any]) -> dict[str, Any]:
    debit = _loads(row.get("debit_json"))
    debit = debit if isinstance(debit, Mapping) else {}
    usage = debit.get("usage")
    tags = debit.get("tags")
    return {
        "entry_id": row.get("entry_id"),
        "trajectory_id": row.get("run_id"),
        "turn_id": row.get("source_ref"),
        "occurred_at": row.get("occurred_at"),
        "unpriced": bool(row.get("unpriced")),
        "pricing_hash": row.get("pricing_hash"),
        "usage": dict(usage) if isinstance(usage, Mapping) else {},
        "tags": list(tags) if isinstance(tags, list) else [],
    }


def ledger_db(handle: AppDatabase, *, trajectory_id: str | None) -> dict[str, Any]:
    """The recorded debits, newest first. No position: that is PromptCadence's arithmetic, live."""
    rows = rows_where(
        handle, "ledger_entries", equals={"run_id": trajectory_id}, order_by="occurred_at",
        limit=LIST_CAP,
    )  # fmt: skip
    return {"position": None, "entries": [_entry_row(row) for row in rows]}


def _egress_row(row: Mapping[str, Any]) -> dict[str, Any]:
    decision = _loads(row.get("decision_json"))
    decision = decision if isinstance(decision, Mapping) else {}
    request = decision.get("request")
    request = request if isinstance(request, Mapping) else {}
    return {
        "decision_id": row.get("decision_id"),
        "verdict": row.get("verdict"),
        "trajectory_id": row.get("run_id"),
        "target": row.get("target_name"),
        "classification": request.get("data_classification"),
        "policy": decision.get("policy_name"),
        "reason": decision.get("reason"),
        "decided_at": row.get("decided_at"),
    }


def egress_db(
    handle: AppDatabase, *, verdict: str | None, trajectory_id: str | None
) -> list[dict[str, Any]]:
    """The ``egress_decisions`` rows, newest first, filtered by verdict and trajectory."""
    rows = rows_where(
        handle, "egress_decisions", equals={"verdict": verdict, "run_id": trajectory_id},
        order_by="decided_at", limit=LIST_CAP,
    )  # fmt: skip
    return [_egress_row(row) for row in rows]
