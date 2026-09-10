"""weightroom.domain.chat — conversations, the event vocabulary, and the thinking state machine.

Pure: no framework, no clock, no I/O. Everything here is a value or a function over values, so the
behaviour the chat page shows — when thinking opens, when it collapses, what a cost cell says — is
decided in one place and tested over recorded streams rather than over a browser.

**The two backends and no third** (spec §3, §11 contract 6, ADR-0045). A conversation reaches a
model through LoadCoach or PromptCadence; :data:`BACKENDS` is the check constraint's vocabulary
and :func:`require_backend` refuses anything else by name.

**The thinking state machine** (spec §7.6, interview D13, risks T8/I6). A reply is a sequence of
:class:`Chunk` values; :func:`advance` folds one into a :class:`ThinkingState` and says which
persisted event kinds the step produced. The rules, in order of how often they matter:

1. **Thinking opens on the first thinking delta** and streams in its own block.
2. **It collapses on the first text delta that is not whitespace.** Ollama sends lone ``" "``
   content pieces around its thinking (I6), and a model that interleaves them must not flicker the
   block shut and open again, so a whitespace-only text piece is kept as text but moves nothing.
3. **It collapses on ``done`` or on an ``error``** if it is still open — a reply that never starts
   its answer still ends with a collapsed block, never a spinner.
4. **Thinking that arrives after the collapse is appended, collapsed.** The block never reopens.
5. **A model that streams no thinking but reports it at the end** (an older LoadCoach, which drops
   the live deltas and returns ``result.reasoning.summary``) gets a collapsed block filled from
   ``done``. Streamed thinking always wins over the summary; the two are never concatenated.
6. **A provider with no thinking channel shows no block.** ``phase`` stays ``none``.
7. **After ``done`` or ``error`` nothing moves.** A late frame changes nothing and emits nothing.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Any, Final, Literal

__all__ = [
    "ATTACHMENT_MEDIA_TYPES",
    "BACKENDS",
    "CLASSIFICATIONS",
    "DELTA_KINDS",
    "EVENT_KINDS",
    "STRUCTURED_KINDS",
    "BackendUnknown",
    "Chunk",
    "CostCell",
    "ThinkingState",
    "advance",
    "cost_cell",
    "fold",
    "require_backend",
    "sanitise_filename",
    "token_count_text",
]

type Backend = Literal["loadcoach", "promptcadence"]
type Phase = Literal["none", "streaming", "collapsed"]
type ThinkingSource = Literal["none", "stream", "result"]
type ChunkKind = Literal["thinking", "text", "done", "error"]

BACKENDS: Final[tuple[str, ...]] = ("loadcoach", "promptcadence")
"""The only two ways chat reaches a model (spec §11 contract 6). There is no third value."""

CLASSIFICATIONS: Final[tuple[str, ...]] = ("public", "internal", "confidential")
"""PromptCadence's ordered vocabulary (ADR-0046), for a conversation's ``classification``."""

EVENT_KINDS: Final[tuple[str, ...]] = (
    "delta.thinking",
    "delta.text",
    "thinking_done",
    "plan",
    "step",
    "tool_call",
    "egress_decision",
    "approval_pending",
    "halt",
    "done",
)
"""``message_events.kind`` (data model §2). The SSE stream is exactly these, persisted."""

DELTA_KINDS: Final[frozenset[str]] = frozenset({"delta.thinking", "delta.text"})
"""The kinds coalesced into ``messages.text``/``thinking`` on completion and then dropped."""

STRUCTURED_KINDS: Final[frozenset[str]] = frozenset(EVENT_KINDS) - DELTA_KINDS
"""The kinds that stay as rows after completion: they are the record, not the transport."""

ATTACHMENT_MEDIA_TYPES: Final[dict[str, str]] = {
    ".txt": "text/plain",
    ".text": "text/plain",
    ".log": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
"""Text and markdown only (spec §7.6, §14). Anything else is refused by extension and content."""


class BackendUnknown(ValueError):
    """A backend outside :data:`BACKENDS` — the value the check constraint also refuses."""


def require_backend(value: str) -> Backend:
    """Return ``value`` if it is one of the two backends.

    Raises:
        BackendUnknown: It is anything else, including a provider name. Chat has no provider path.
    """
    if value == "loadcoach":
        return "loadcoach"
    if value == "promptcadence":
        return "promptcadence"
    message = f"{value!r} is not a chat backend; chat reaches a model only through {BACKENDS}"
    raise BackendUnknown(message)


@dataclass(frozen=True, slots=True)
class Chunk:
    """One step of a reply, already translated out of a backend's own wire format.

    Attributes:
        kind: ``thinking`` or ``text`` for a delta; ``done`` for the terminal result; ``error``
            for a terminal failure.
        text: The delta's text, or the error's message.
        reasoning: On ``done`` only — the thinking the backend reported at the end (LoadCoach's
            ``result.reasoning.summary``), used when nothing was streamed (module rule 5).
    """

    kind: ChunkKind
    text: str = ""
    reasoning: str | None = None


@dataclass(frozen=True, slots=True)
class ThinkingState:
    """Where one reply stands.

    Attributes:
        phase: ``none`` (no thinking seen), ``streaming`` (the block is open) or ``collapsed``.
        thinking: The thinking text so far.
        text: The answer text so far, whitespace pieces included.
        source: Where ``thinking`` came from — ``stream``, ``result`` or ``none``.
        finished: Whether ``done`` or ``error`` has been seen.
        error: The terminal error's message, when the reply ended in one.
    """

    phase: Phase = "none"
    thinking: str = ""
    text: str = ""
    source: ThinkingSource = "none"
    finished: bool = False
    error: str | None = None

    @property
    def shows_block(self) -> bool:
        """Whether the page renders a thinking block at all (module rule 6)."""
        return self.phase != "none"


def advance(state: ThinkingState, chunk: Chunk) -> tuple[ThinkingState, tuple[str, ...]]:
    """Fold one chunk into the state; return the new state and the event kinds it produced.

    Args:
        state: The reply so far.
        chunk: The next step.

    Returns:
        ``(new_state, kinds)`` where ``kinds`` are :data:`EVENT_KINDS` members, in order —
        ``("thinking_done", "delta.text")`` for the text delta that collapses an open block.
    """
    if state.finished:
        return state, ()
    if chunk.kind == "thinking":
        if not chunk.text:
            return state, ()
        phase: Phase = "streaming" if state.phase == "none" else state.phase
        return (
            replace(state, phase=phase, thinking=state.thinking + chunk.text, source="stream"),
            ("delta.thinking",),
        )
    if chunk.kind == "text":
        if not chunk.text:
            return state, ()
        collapsing = state.phase == "streaming" and chunk.text.strip() != ""
        new_state = replace(
            state,
            text=state.text + chunk.text,
            phase="collapsed" if collapsing else state.phase,
        )
        return new_state, (("thinking_done", "delta.text") if collapsing else ("delta.text",))
    kinds: list[str] = []
    new_state = state
    if state.phase == "streaming":
        new_state = replace(new_state, phase="collapsed")
        kinds.append("thinking_done")
    elif state.phase == "none" and chunk.kind == "done" and chunk.reasoning:
        new_state = replace(new_state, phase="collapsed", thinking=chunk.reasoning, source="result")
        kinds.append("thinking_done")
    if chunk.kind == "error":
        kinds.append("halt")
        return replace(new_state, finished=True, error=chunk.text or "the reply failed"), tuple(
            kinds
        )
    kinds.append("done")
    return replace(new_state, finished=True), tuple(kinds)


def fold(chunks: tuple[Chunk, ...] | list[Chunk]) -> tuple[ThinkingState, tuple[str, ...]]:
    """Run a recorded reply through :func:`advance`: the final state and every kind emitted."""
    state = ThinkingState()
    emitted: list[str] = []
    for chunk in chunks:
        state, kinds = advance(state, chunk)
        emitted.extend(kinds)
    return state, tuple(emitted)


# --- Cost and usage cells ---------------------------------------------------------------------

_TOKEN_CLASSES: Final[tuple[tuple[str, str], ...]] = (
    ("input_tokens", "in"),
    ("output_tokens", "out"),
    ("cache_read_tokens", "cache read"),
    ("cache_write_tokens", "cache write"),
    ("thinking_tokens", "thinking"),
)


def token_count_text(value: Any) -> str:  # noqa: ANN401 — a JSON value from a backend
    """One token count as the page shows it: the number, or ``—`` when it was not reported.

    ``"unsupported"``, ``None`` and anything that is not a whole number are all ``—``; a real
    ``0`` stays ``0`` (ADR-0016 rule 4, ADR-0070). Never totalled.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return "—"
    return f"{value:,}"


@dataclass(frozen=True, slots=True)
class CostCell:
    """The line under a reply: tokens by class, and money only where it was priced.

    Attributes:
        tokens: ``(label, text)`` per token class, ``—`` where unreported.
        money: ``"$0.0042"``-style text, ``"at least $…"`` when a component was unpriced, or ``—``.
        note: ``local`` for a model that costs nothing to call, ``unpriced`` when a remote call
            carried no price, else ``""``.
        unpriced_count: How many components or debits went unpriced (ADR-0069 rule 2).
    """

    tokens: tuple[tuple[str, str], ...]
    money: str
    note: str
    unpriced_count: int

    @property
    def summary(self) -> str:
        """``in 77 · out 106 · thinking — · — · local``."""
        parts = [f"{label} {text}" for label, text in self.tokens]
        tail = f"{self.money} · {self.note}" if self.note else self.money
        return " · ".join([*parts, tail])


def cost_cell(
    usage: dict[str, Any] | None, cost: dict[str, Any] | None, *, remote: bool
) -> CostCell:
    """Build the cost line from a reply's ``usage`` and ``cost``.

    Args:
        usage: The backend's token classes, as reported; ``None`` when the backend gave none.
        cost: ``{"nanos": int, "currency": str, "unpriced_count": int}`` or ``None``.
        remote: Whether the serving model was a remote provider.

    Returns:
        The cell. Money is shown only when ``cost`` carries an amount; a local model is ``—`` with
        ``local``; a remote call with no price is ``—`` with ``unpriced``; a partial price is
        rendered as a floor, never a bare figure (ADR-0069 rule 2).
    """
    report = usage or {}
    tokens = tuple((label, token_count_text(report.get(key))) for key, label in _TOKEN_CLASSES)
    unpriced = int((cost or {}).get("unpriced_count") or 0)
    nanos = (cost or {}).get("nanos")
    currency = str((cost or {}).get("currency") or "")
    if isinstance(nanos, int) and not isinstance(nanos, bool) and currency:
        figure = _money_text(nanos, currency)
        if unpriced:
            return CostCell(tokens, f"at least {figure}", "", unpriced)
        return CostCell(tokens, figure, "", 0)
    if not remote:
        return CostCell(tokens, "—", "local", unpriced)
    return CostCell(tokens, "—", "unpriced", max(unpriced, 1))


def _money_text(nanos: int, currency: str) -> str:
    amount = nanos / 1_000_000_000
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency.upper())
    body = f"{amount:.4f}".rstrip("0").rstrip(".") if amount else "0"
    return f"{symbol}{body}" if symbol else f"{body} {currency.upper()}"


# --- Attachments ------------------------------------------------------------------------------

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


def sanitise_filename(name: str, *, limit: int = 120) -> str:
    """A display name that cannot be a path: no separators, no controls, no leading dots.

    The stored file never uses it (it lives under a generated ULID, spec §14); this is only what
    the page shows and what the context block names.
    """
    normal = unicodedata.normalize("NFKC", name)
    base = normal.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _UNSAFE_NAME.sub("_", base).strip(" ._") or "attachment"
    return cleaned[:limit]
