"""weightroom.services.chat_loadcoach — one reply through LoadCoach's ``POST /generate/stream``.

LoadCoach is one of the two ways chat reaches a model (spec §3, §11 contract 6); nothing here
knows a provider, and ``modelrack.generate`` is never called anywhere in this repository (a grep
test holds that). This module speaks LoadCoach's wire and nothing else: it builds the request
body, reads the SSE stream, and translates each frame into the pure
:class:`~weightroom.domain.chat.Chunk` the thinking state machine folds. Persistence is
:mod:`weightroom.services.chat`'s.

**How LoadCoach marks thinking** (the question row W6 had to answer, from the reference machine):

* **LoadCoach ≥ 1.5.0** streams each reasoning delta live as ``event: thinking`` inside the event
  envelope (ADR-0132, ``docs/adr/0132-loadcoach-streams-thinking-deltas-as-their-own-frame.md``).
  Captured on ``gpt-oss:20b``: 42 thinking frames, then 22 ``token`` frames, two of them a lone
  space. Ollama and llama.cpp providers stream it; ``openai_compatible`` sends none.
* **LoadCoach ≤ 1.4** sends no thinking frame at all; the reasoning arrives whole in
  ``result.reasoning.summary``. Captured on the same model under 1.3.1. The state machine turns it
  into a collapsed block on ``done``, so a console upgraded before LoadCoach still shows it.

Frame shapes: every frame carries the SetSpec event envelope and its body is ``payload``, except
``token``, which is bare ``{"delta", "index"}`` (ADR-0025 §3). ``tool_call`` frames are ignored —
chat sends no tools.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

import httpx

from weightroom.domain.chat import Chunk

__all__ = [
    "STREAM_TIMEOUT",
    "BackendRefused",
    "Frame",
    "build_request",
    "context_block",
    "fetch_routing",
    "iter_frames",
    "routing_summary",
    "stream_reply",
]

STREAM_TIMEOUT: Final = httpx.Timeout(connect=5.0, read=300.0, write=30.0, pool=5.0)
"""A long read timeout: a thinking model can be silent between frames while it loads."""


class BackendRefused(Exception):  # noqa: N818 — a refusal, reported verbatim, not a bug
    """LoadCoach answered the request with an error status; ``message`` is its own words."""

    def __init__(self, message: str) -> None:
        """Keep the backend's message as the exception's."""
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class Frame:
    """One SSE frame: its ``event:`` name and its parsed ``data:``."""

    event: str
    data: Any


def iter_frames(lines: Iterable[str]) -> Iterator[Frame]:
    """Split an SSE line stream into frames; a frame whose data is not JSON is dropped.

    Comment lines (heartbeats) and ``id:`` lines are skipped; multi-line ``data:`` is joined with
    newlines, as the SSE specification says.
    """
    event: str | None = None
    data_lines: list[str] = []
    for line in [*lines, ""]:
        if line == "":
            if event is not None and data_lines:
                try:
                    yield Frame(event, json.loads("\n".join(data_lines)))
                except ValueError:
                    pass  # a frame this console cannot parse is dropped, never guessed at
            event, data_lines = None, []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "event":
            event = value
        elif field == "data":
            data_lines.append(value)


def _payload(frame: Frame) -> Mapping[str, Any] | None:
    if frame.event == "token":
        return frame.data if isinstance(frame.data, Mapping) else None
    body = frame.data.get("payload") if isinstance(frame.data, Mapping) else None
    return body if isinstance(body, Mapping) else None


def context_block(attachments: Sequence[tuple[str, str]]) -> str:
    """The attachments, as text the model reads before the operator's message (spec §7.6).

    Each file sits in a tilde fence longer than any run of tildes inside it, so a file cannot close
    its own fence and continue as if it were the operator speaking.
    """
    parts = []
    for filename, text in attachments:
        longest = max((len(run) for run in text.split("\n") if set(run) <= {"~"}), default=0)
        fence = "~" * max(4, longest + 1)
        parts.append(f"Attached file `{filename}`:\n\n{fence}\n{text}\n{fence}\n")
    return "\n".join(parts)


def build_request(
    *,
    task: str,
    model_override: str | None,
    history: Sequence[tuple[str, str]],
    idempotency_key: str,
) -> dict[str, Any]:
    """The ``POST /generate/stream`` body for one reply.

    Args:
        task: The conversation's task profile.
        model_override: A canonical model id to pin, or ``None`` to let LoadCoach route.
        history: ``(role, content)`` pairs, oldest first, ending with the operator's new message
            with any attachment context already prepended.
        idempotency_key: The assistant message's id, so a retried request replays rather than
            re-executes (LoadCoach api.md §4).

    Returns:
        The body. ``messages`` is used rather than ``prompt`` so the whole conversation is sent.
    """
    body: dict[str, Any] = {
        "task": task,
        "messages": [
            {"role": role, "content": content, "tool_call_id": None, "tool_calls": None}
            for role, content in history
        ],
        "idempotency_key": idempotency_key,
    }
    if model_override:
        body["overrides"] = {"model": model_override}
    return body


def routing_summary(explanation: Mapping[str, Any]) -> dict[str, Any]:
    """What the line under a reply shows, from LoadCoach's routing explanation (routing §8).

    Returns:
        ``model``, ``provider_name``, ``candidates`` and ``rejected`` counts, ``rejections`` by
        reason, ``flags``, ``task_profile`` and ``decision_id`` — counts and names only, so the
        stored row stays small while the full explanation stays in LoadCoach.
    """
    selected = explanation.get("selected") or {}
    rejected = explanation.get("rejected") or []
    reasons: dict[str, int] = {}
    for row in rejected:
        reason = str((row or {}).get("reason") or "unknown")
        reasons[reason] = reasons.get(reason, 0) + 1
    profile = explanation.get("task_profile") or {}
    return {
        "decision_id": explanation.get("decision_id"),
        "model": selected.get("canonical_id"),
        "provider_name": selected.get("provider_name"),
        "candidates": len(explanation.get("candidates") or []),
        "rejected": len(rejected),
        "rejections": dict(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))),
        "flags": [str(flag) for flag in explanation.get("flags") or []],
        "task_profile": profile.get("id") if isinstance(profile, Mapping) else None,
    }


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _error_text(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"LoadCoach refused with {response.status_code}."
    error = body.get("error") if isinstance(body, Mapping) else None
    if isinstance(error, Mapping) and error.get("message"):
        code = f" ({error['code']})" if error.get("code") else ""
        return f"LoadCoach refused: {error['message']}{code}"
    return f"LoadCoach refused with {response.status_code}."


def stream_reply(
    client: httpx.Client, *, base_url: str, token: str | None, body: Mapping[str, Any]
) -> Iterator[tuple[str, Any]]:
    """Run one reply and yield what it produced, in order.

    Yields:
        ``("routing", summary)`` once; ``("chunk", Chunk)`` per thinking or text delta and for a
        terminal error; ``("result", payload)`` for the terminal result. A stream that ends with
        neither ``result`` nor ``error`` yields a terminal error chunk naming that.

    Raises:
        BackendRefused: LoadCoach answered with an error status before streaming.
        httpx.HTTPError: The connection failed; the caller records it as the reply's halt.
    """
    url = f"{base_url.rstrip('/')}/api/v1/generate/stream"
    with client.stream(
        "POST", url, json=dict(body), headers=_headers(token), timeout=STREAM_TIMEOUT
    ) as response:
        if response.status_code >= 400:  # noqa: PLR2004 — the HTTP error boundary
            response.read()
            raise BackendRefused(_error_text(response))
        for frame in iter_frames(response.iter_lines()):
            payload = _payload(frame)
            if payload is None:
                continue
            if frame.event == "routing":
                yield "routing", routing_summary(payload)
            elif frame.event == "thinking":
                yield "chunk", Chunk("thinking", str(payload.get("delta") or ""))
            elif frame.event == "token":
                yield "chunk", Chunk("text", str(payload.get("delta") or ""))
            elif frame.event == "result":
                yield "result", dict(payload)
                return
            elif frame.event == "error":
                message = payload.get("message") or payload.get("code") or "LoadCoach failed."
                yield "chunk", Chunk("error", f"LoadCoach: {message}")
                return
    yield "chunk", Chunk("error", "LoadCoach's stream ended without a result or an error frame.")


def fetch_routing(
    client: httpx.Client, *, base_url: str, token: str | None, explanation_url: str
) -> dict[str, Any] | None:
    """The routing summary from ``/jobs/{id}/explanation`` when the stream carried no routing frame.

    Returns:
        The summary, or ``None`` when LoadCoach did not answer — the reply is still recorded.
    """
    if not explanation_url.startswith("/api/v1/jobs/"):
        return None  # only LoadCoach's own relative route; never a URL taken from elsewhere
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = client.get(
            f"{base_url.rstrip('/')}{explanation_url}", headers=headers, timeout=10.0
        )
        body = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if response.status_code >= 400 or not isinstance(body, Mapping):  # noqa: PLR2004
        return None
    explanation = body.get("payload", body)
    return routing_summary(explanation) if isinstance(explanation, Mapping) else None
