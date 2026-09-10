# ADR-0132 — LoadCoach streams thinking deltas as their own frame

**Status:** Accepted (2026-09-10)
**Amends:** [LoadCoach API](../apps/loadcoach/api.md) §4 (`POST /generate/stream` gains a
`thinking` frame) and §5 (`GET /jobs/{id}/stream` carries it too).
**Relates to:** [ADR-0025](0025-envelope-boundaries.md) §3 (the bare `token` exception, which this
record deliberately does **not** extend), [ADR-0099](0099-a-task-profile-may-ask-for-reduced-thinking.md)
(the thinking control), [ADR-0016](0016-unavailable-is-not-zero.md) (a provider with no thinking
channel sends none — never an empty frame), WeightRoomGym [spec](../apps/weightroom/spec.md) §7.6.
**Found:** row W6, capturing `POST /generate/stream` on the reference machine.
**Source:** operator decision of 2026-09-10, during W6.

## Context

WeightRoomGym's chat (spec §7.6, interview D13) shows a model's thinking **while the model
thinks**, in its own block, then collapses it when the answer starts. The spec assumed a
`thinking`-class chunk on LoadCoach's stream. There was none.

Captured on the reference machine at row W6 — `general.chat`, routed to `ollama/gpt-oss:20b`, a
model that thinks:

```text
1 × event: routing      60 × event: token      1 × event: result
result.reasoning = {"available": true, "source": "provider",
                    "summary": "The user wants a two-sentence answer: …"}
```

Every `token` frame was answer text. The thinking existed — it arrived whole, in the terminal
`result`, after the answer.

The deltas were not missing upstream. ModelRack's `OllamaProvider.stream()` yields a
`ThinkingDelta` for each `message.thinking` piece, and `LlamaCppProvider.stream()` does the same
for `reasoning_content`. LoadCoach's executor received them (`services/execution.py`), added them
to the result, and forwarded nothing: both publishers — the direct stream in
`web/routes/generate.py` and the worker in `services/worker.py` — passed on `token` chunks only.
`StreamChunk`'s own docstring already listed `"thinking"` as a kind; it was never emitted.

## Decision

1. **Each `ThinkingDelta` is forwarded live as `event: thinking`**, payload `{"delta", "index"}`,
   from both `POST /generate/stream` and `GET /jobs/{id}/stream`. An empty delta is not sent.
2. **`index` counts thinking frames only**, from `0` within an attempt. `token` frames keep their
   own counter, so an existing caller reassembling the answer by `token` index sees exactly the
   indices it saw before.
3. **The frame carries the event envelope.** ADR-0025 §3 made `token` bare because a five-field
   envelope per token is the suite's hottest path, and MirrorWall enforces that exception against
   `TOKEN_EVENT` alone, by construction, so that it cannot widen by accident. Thinking frames are
   as frequent as tokens, but making them bare would need a MirrorWall release and an amendment to
   ADR-0025 for roughly a hundred bytes per frame on a loopback connection. They are enveloped;
   the overhead is recorded here as accepted rather than measured away.
4. **Live only, like `token`.** Thinking frames are fanned out and not persisted; a reconnect with
   `Last-Event-ID` replays persisted events, and the thinking a reconnecting caller missed is in
   `result.reasoning.summary`, which is unchanged.
5. **Per provider kind, on the reference machine:** Ollama and llama.cpp stream thinking;
   `openai_compatible` reports it as unsupported and sends **no** thinking frames — never an empty
   one (ADR-0016).
6. **Additive inside `/api/v1`, released as a minor: LoadCoach 1.5.0.** API and Contract Standards
   require clients to ignore an unknown event, so no existing consumer changes.

## Consequences

*Positive.* A caller can show reasoning as it happens. WeightRoomGym's chat does, and collapses it
on the first non-whitespace text delta or on the terminal frame (its `domain/chat.py`).

*Negative.* A thinking model's stream grows by one enveloped frame per reasoning delta. On the
reference machine that is a few hundred frames for a long answer.

*Neutral.* A consumer written against LoadCoach ≤ 1.4 keeps working and keeps getting thinking only
from `result`. WeightRoomGym reads both: live frames when they arrive, `result.reasoning` when
they do not.

## Alternatives considered

* **Bare `thinking` frames, like `token`.** Rejected in rule 3: a MirrorWall release and an
  ADR-0025 amendment for a saving nobody has measured to matter.
* **Thinking only from `result`, no LoadCoach change.** Offered to the operator and declined:
  nothing would stream while the model thinks, which is the behaviour the chat decided on.
* **Carry thinking inside `token` frames with a `channel` field.** Rejected: it changes the meaning
  of an existing frame, and every current consumer would start reassembling reasoning into answers.

## Revisit when

* **A streaming performance budget shows the envelope matters** (LoadCoach's F12-style gap
  measurement over a thinking model). Then make the frame bare, with MirrorWall and ADR-0025
  amended together.
* **A provider streams thinking as summaries rather than deltas.** Rule 1's payload may need a
  `kind`.
