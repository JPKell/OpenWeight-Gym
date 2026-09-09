# Kickoff — W6: WeightRoomGym Phase 6 — chat: LoadCoach, then PromptCadence, thinking collapse

**Row:** W6 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../roadmap/weightroom-work.md).
Runs after W4.
**Ships:** `wr-gym 0.6.0` prepared: conversations through LoadCoach and PromptCadence,
streamed markdown, collapsible thinking, the routing decision and cost under every reply,
PromptCadence's plan/steps/tools/egress/approvals inline, attachments.
**Component:** `~/ai/suite/WeightRoom`. LoadCoach ≥ 1.3 and PromptCadence ≥ 1.3 on the
reference machine for the live demonstration; recorded fixtures at those versions in the suite.

## Standing preamble

[`outstanding-work.md` §2](../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../roadmap/weightroom-work.md).

**Read first:** [`spec.md`](../apps/weightroom/spec.md) §3 (never a provider), §7.6, §11
contract 6, §14 (chat rows); [`api.md`](../apps/weightroom/api.md) §6; [`data-model.md`](../apps/weightroom/data-model.md)
(`conversations`, `messages`, `message_events`, `attachments`); [`development-plan.md`](../apps/weightroom/development-plan.md)
Phase 6; ADR-0045 (why no provider path); ADR-0049 (`approve` is its own scope); ADR-0016 and
ADR-0069 (cost cells); ADR-0044 (events persisted with the state change); `apps/loadcoach/api.md`
(`POST /generate/stream`, the chunk classes including thinking, `/jobs/{id}/explanation`, usage);
`apps/promptcadence/api.md` §3–§4 (submit, stream events, approve/deny, halts) and
`apps/promptcadence/lifecycle.md` §4–§5; PromptCadence's `tests/security/test_injection_corpus.py`
(reused against chat rendering); `history/I6_HANDOFF.md` (which models stream thinking, and how
Ollama closes the stream); `history/W4_HANDOFF.md`.

## Decisions already taken — do not reopen

* A conversation's `backend` is `loadcoach` or `promptcadence` — a check constraint, no third
  value; `modelrack.generate` is never called (a grep test) and a network-isolation test proves no
  host but the two configured base URLs is contacted (spec §11 contract 6).
* **Thinking streams while the model thinks, in its own block, then collapses** to one line when
  the first text delta arrives (or on `done`); collapsed thinking, decisions and plans expand on
  click; a provider with no thinking channel shows no block (interview D13; risks T8).
* Under each reply: the routing decision (model, candidates, rejections) and the cost by token
  class; money only where priced, `—` where local or unavailable, with the unpriced count.
* PromptCadence approvals are granted inline with the wizard's `approve`-scoped token; a token
  without the scope renders *no approve scope* and never a button that fails.
* Attachments: text and markdown only, size-capped, prepended as context, never executed or
  fetched from. Model text renders through the sanitising markdown pipeline; nothing is raw.
* `message_events` are persisted rows replayable by `Last-Event-ID`; deltas coalesce on
  completion and structured rows stay.

## Gates

**Gate A — the model and the state machine.** `domain/chat.py` (conversation, message, event
kinds, the thinking state machine as a pure function over a chunk sequence); Alembic migration;
tests over recorded streams with, without and interrupted thinking. Commit.

**Gate B — LoadCoach.** `services/chat_loadcoach.py`: the request body, streaming, the decision
from the explanation, usage and cost; the conversation pages with streamed markdown, code copy,
the `<details>` thinking block; attachments. Recorded fixtures; `CHAT_BACKEND_UNAVAILABLE` when
stopped with old conversations still readable. Commit.

**Gate C — PromptCadence.** `services/chat_promptcadence.py`: submit, the stream mapped to
plan/step/tool/egress/approval/halt events, inline cards, approve/deny, halts verbatim; the
injection corpus against the rendered thread; the network-isolation test; `CHANGELOG.md`;
`0.6.0`. Commit.

## Demonstrate

Plan Phase 6 criteria 1–3 on the reference machine from a phone, with a screenshot of the
collapsed and expanded thinking, and `promptcadence trajectory show` output naming the approver.

## What this row must decide, and write down

* How LoadCoach's stream marks thinking for each provider kind on the reference machine
  (`I6_HANDOFF.md` is the evidence), and what the collapse does for a model that emits none.

## Finish line

Gate green, coverage held, one commit per gate, `docs/history/W6_HANDOFF.md`, the row marked done.
Never overnight; reviewed the same day.
