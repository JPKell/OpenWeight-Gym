"""The thinking state machine and the cost cell, over recorded and hand-written chunk sequences."""

from __future__ import annotations

import pytest

from weightroom.domain.chat import (
    BACKENDS,
    DELTA_KINDS,
    EVENT_KINDS,
    STRUCTURED_KINDS,
    BackendUnknown,
    Chunk,
    ThinkingState,
    advance,
    cost_cell,
    fold,
    require_backend,
    sanitise_filename,
    token_count_text,
)

# --- Backends -----------------------------------------------------------------------------------


def test_there_are_exactly_two_backends_and_no_provider_path() -> None:
    assert BACKENDS == ("loadcoach", "promptcadence")
    assert require_backend("loadcoach") == "loadcoach"
    assert require_backend("promptcadence") == "promptcadence"
    for provider in ("ollama", "llamacpp", "openai_compatible", "modelrack", ""):
        with pytest.raises(BackendUnknown, match="not a chat backend"):
            require_backend(provider)


def test_the_event_vocabulary_partitions_into_deltas_and_structured_rows() -> None:
    assert DELTA_KINDS | STRUCTURED_KINDS == frozenset(EVENT_KINDS)
    assert not DELTA_KINDS & STRUCTURED_KINDS


# --- The thinking state machine: with thinking ------------------------------------------------


def test_thinking_streams_then_collapses_when_the_answer_starts() -> None:
    chunks = [
        Chunk("thinking", "The user wants "),
        Chunk("thinking", "two sentences."),
        Chunk("text", "The sky"),
        Chunk("text", " is blue."),
        Chunk("done"),
    ]
    state, kinds = fold(chunks)
    assert kinds == (
        "delta.thinking",
        "delta.thinking",
        "thinking_done",
        "delta.text",
        "delta.text",
        "done",
    )
    assert (state.phase, state.source, state.finished) == ("collapsed", "stream", True)
    assert state.thinking == "The user wants two sentences."
    assert state.text == "The sky is blue."


def test_the_block_is_open_while_only_thinking_has_arrived() -> None:
    state, _ = fold([Chunk("thinking", "hmm")])
    assert state.phase == "streaming"
    assert state.shows_block
    assert not state.finished


def test_a_whitespace_text_piece_does_not_collapse_the_block() -> None:
    """Ollama sends lone ``" "`` content pieces around thinking (I6_HANDOFF.md D3)."""
    state, kinds = fold([Chunk("thinking", "a"), Chunk("text", " "), Chunk("thinking", "b")])
    assert state.phase == "streaming"
    assert state.thinking == "ab"
    assert kinds == ("delta.thinking", "delta.text", "delta.thinking")


def test_thinking_after_the_collapse_is_appended_and_never_reopens() -> None:
    state, kinds = fold(
        [Chunk("thinking", "a"), Chunk("text", "Answer"), Chunk("thinking", " late")]
    )
    assert state.phase == "collapsed"
    assert state.thinking == "a late"
    assert kinds[-1] == "delta.thinking"
    assert kinds.count("thinking_done") == 1


def test_done_collapses_a_block_that_never_reached_an_answer() -> None:
    state, kinds = fold([Chunk("thinking", "only thinking"), Chunk("done")])
    assert kinds == ("delta.thinking", "thinking_done", "done")
    assert state.phase == "collapsed"
    assert state.text == ""


# --- Without thinking ------------------------------------------------------------------------


def test_a_provider_with_no_thinking_channel_shows_no_block() -> None:
    state, kinds = fold([Chunk("text", "Hello"), Chunk("text", " there"), Chunk("done")])
    assert kinds == ("delta.text", "delta.text", "done")
    assert state.phase == "none"
    assert not state.shows_block
    assert state.source == "none"


def test_thinking_reported_only_at_the_end_fills_a_collapsed_block() -> None:
    """An older LoadCoach drops the live deltas and returns ``result.reasoning.summary`` —
    the recorded 1.3.1 stream behaves exactly like this (tests/fixtures/chat)."""
    state, kinds = fold(
        [Chunk("text", "The sky is blue."), Chunk("done", reasoning="The user wants two.")]
    )
    assert kinds == ("delta.text", "thinking_done", "done")
    assert (state.phase, state.source) == ("collapsed", "result")
    assert state.thinking == "The user wants two."


def test_streamed_thinking_wins_over_the_end_of_stream_summary() -> None:
    state, _ = fold(
        [
            Chunk("thinking", "streamed"),
            Chunk("text", "A"),
            Chunk("done", reasoning="summary"),
        ]
    )
    assert state.thinking == "streamed"
    assert state.source == "stream"


def test_empty_deltas_move_nothing() -> None:
    state, kinds = advance(ThinkingState(), Chunk("thinking", ""))
    assert (state, kinds) == (ThinkingState(), ())
    state, kinds = advance(ThinkingState(), Chunk("text", ""))
    assert (state, kinds) == (ThinkingState(), ())


# --- Interrupted ---------------------------------------------------------------------------------


def test_an_error_mid_thinking_collapses_the_block_and_halts() -> None:
    state, kinds = fold(
        [
            Chunk("thinking", "working"),
            Chunk(
                "error", "The stream from http://127.0.0.1:11434 ended without a terminal chunk."
            ),
        ]
    )
    assert kinds == ("delta.thinking", "thinking_done", "halt")
    assert state.phase == "collapsed"
    assert state.finished
    assert state.error is not None
    assert "without a terminal chunk" in state.error


def test_an_error_before_anything_halts_with_no_block() -> None:
    state, kinds = fold([Chunk("error", "")])
    assert kinds == ("halt",)
    assert not state.shows_block
    assert state.error == "the reply failed"


def test_nothing_moves_after_the_reply_has_finished() -> None:
    state, _ = fold([Chunk("text", "done."), Chunk("done")])
    for late in (Chunk("text", "more"), Chunk("thinking", "x"), Chunk("done"), Chunk("error", "e")):
        assert advance(state, late) == (state, ())


# --- Cost cells ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "text"),
    [(0, "0"), (1104, "1,104"), ("unsupported", "—"), (None, "—"), (True, "—"), (1.5, "—")],
)
def test_a_token_count_is_a_number_or_a_dash_never_a_coerced_zero(value: object, text: str) -> None:
    assert token_count_text(value) == text


def test_a_local_reply_costs_a_dash_labelled_local() -> None:
    usage = {"input_tokens": 77, "output_tokens": 106, "thinking_tokens": "unsupported"}
    cell = cost_cell(usage, None, remote=False)
    assert cell.money == "—"
    assert cell.note == "local"
    assert dict(cell.tokens)["thinking"] == "—"
    assert cell.summary.endswith("— · local")


def test_a_priced_reply_shows_money() -> None:
    cell = cost_cell({}, {"nanos": 4_200_000, "currency": "USD", "unpriced_count": 0}, remote=True)
    assert cell.money == "$0.0042"
    assert cell.unpriced_count == 0


def test_a_partial_price_is_a_floor_with_its_unpriced_count() -> None:
    cell = cost_cell({}, {"nanos": 4_200_000, "currency": "USD", "unpriced_count": 2}, remote=True)
    assert cell.money == "at least $0.0042"
    assert cell.unpriced_count == 2


def test_a_remote_reply_with_no_price_is_unpriced_not_free() -> None:
    cell = cost_cell({"input_tokens": 10}, None, remote=True)
    assert (cell.money, cell.note, cell.unpriced_count) == ("—", "unpriced", 1)


# --- Attachment names ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("notes.md", "notes.md"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\x\\secret.txt", "secret.txt"),
        (".hidden", "hidden"),
        ("<script>.md", "script_.md"),
        ("", "attachment"),
    ],
)
def test_an_attachment_name_can_never_be_a_path(raw: str, clean: str) -> None:
    assert sanitise_filename(raw) == clean
