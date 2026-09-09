# ADR-0096 — Replayed tool-call arguments are capped at the record's bound

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Spec §14](../apps/promptcadence/spec.md) — the trust-boundary bullet
gains the cap on what a replay carries back to the model.
**Relates to:** [ADR-0053](0053-a-refused-tool-call-is-a-result-not-an-exception.md) (ToolYard's
record and its `args_json` bound), [ADR-0075](0075-a-request-carrying-tools-requires-tool-use-of-every-candidate.md)
(the native replay G2 introduced).
**Source:** Row I2, decision 2 — G2 §10's moved hazard.

## Context

G1 §8 flagged that `_render_tool_calls` echoed model-chosen tool arguments back into the next
turn's transcript uncapped. G2 deleted that rendering and replayed `tool_calls` natively on
LoadCoach's wire — and moved the hazard rather than removing it: `tool_calls[].arguments` is still
uncapped model output going back onto the wire, now as structured JSON. Nothing in PromptCadence,
LoadCoach or ModelRack bounds it.

Two bounds already exist beside it. `_recorded_name` caps a tool name at ToolYard's
`MAX_RECORDED_NAME_CHARS` on every event. ToolYard's executor caps the **record**: when the
canonical JSON of a call's arguments exceeds `max_args_json_bytes` (16 384 by default),
`tool_call_records.args_json` holds a small object naming the size and the digest —
`{"__toolyard_args_omitted__": "oversize", "bytes": N, "sha256": …}` — rather than a fragment
cut mid-string, and `args_sha256` identifies the original in every case. The call itself still
executes with its full arguments: a `write_file` of a 20 KiB document is legitimate work, and
ToolYard bounds arguments for execution by node count and depth, not by bytes.

## Decision

**A replayed call whose canonical arguments exceed ToolYard's record bound is replayed with the
record's own size-and-digest object in place of the arguments. One bound, one shape, and the
record and the wire agree by construction.**

1. **The bound is ToolYard's `DEFAULT_MAX_ARGS_JSON_BYTES`**, imported, never restated. The
   figure the record was capped at is the figure the replay is capped at, so `args_json` being the
   omitted-object *is* the statement that the replay carried it. No new column, no new event.
2. **Where:** in the loop's transcript build (`_transcript`), the one place the persisted
   `tool_calls_json` becomes wire messages. The rows are untouched — `tool_calls_json` keeps what
   the model asked for, in full, until the retention sweep — so a step resumed after a park still
   executes the calls the model actually made.
3. **What is replaced:** the `arguments` value only. The call's id and name are kept so the
   `TOOL` turn answering it still matches an earlier assistant call (LoadCoach's fourth transcript
   rule). The `TOOL` turn's content is unchanged — it was already capped at `max_result_chars`.
4. **The call is not refused and the turn is not failed.** The call ran, its result was recorded,
   and refusing the *next* turn for the size of a previous call's arguments would end a
   trajectory for work already done. The model sees that its earlier arguments were oversize and
   omitted, which is a true statement about the wire.
5. **The cap is measured on canonical JSON of the parsed object, or on the raw text when the
   arguments never parsed** — the same text `args_sha256` digests, so the digest in the stub is
   the digest on the row.

## What this refuses

* Truncating the JSON text at a byte count. A fragment cut mid-string is not JSON, LoadCoach
  would refuse the request, and a record pointing at it would describe nothing.
* A second, PromptCadence-owned bound with its own figure. Two bounds on one value drift.
* Silent omission. The stub names its size and digest; a reader can tell the arguments were
  omitted and can identify them against the record.
* Capping before execution. That would make a 16 KiB document unwritable for the sake of a replay
  hazard that the replay can bound on its own.

## Alternatives considered

**Refuse the turn when an oversize argument would be replayed.** Simplest to state, and it fails a
trajectory for a call that already succeeded — after a park, after a crash, at the next turn
boundary, for a reason the model cannot fix. Rejected.

**Cap arguments at execution, refusing oversize calls `args_invalid`.** Removes the hazard at the
source. Rejected because the bound would be on legitimate work: `write_file` content and
`run_command` argv are arguments, and ToolYard already bounds those by structure and by its own
argv limits. The hazard is *what goes back to the model*, not what runs.

**Store the truncation on the row.** A new column or event saying "replayed truncated". Rejected
as a second place for a fact the record already states: the omitted-object in `args_json` is the
record's own word for it, at the same bound.

## Consequences

* One conditional in `_transcript` and one imported constant; a test that an oversize argument
  never rides back onto the wire uncapped, and one that the stub's digest is the row's digest.
* A model that produces oversize arguments *and* needs them replayed to continue will see the stub
  and may ask again. That is the correct outcome: the alternative is an unbounded wire.
* LoadCoach and ModelRack still carry no bound of their own. This record bounds what PromptCadence
  sends; it does not claim to bound what another caller sends.

## Revisit when

ToolYard's record bound moves, or LoadCoach gains a wire-level bound on `tool_calls[].arguments`.
In the second case this cap becomes redundant and should be deleted, not kept as belt and braces.
