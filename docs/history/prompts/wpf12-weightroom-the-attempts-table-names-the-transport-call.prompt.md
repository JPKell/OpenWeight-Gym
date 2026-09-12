# Kickoff — WPF12: the attempts table names the transport call

**Row:** WPF12 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Left by WPF7 ([`WPF7_HANDOFF.md`](../handoffs/WPF7_HANDOFF.md) §7 item 6). Runs after WPF7.
**Ships:** unreleased, no version bump.

**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WPF7_HANDOFF.md` §2 decision 1 and §3 (a discarded call is an attempt row with
`transport_call`, migration 0012, its tokens and its debit), §7 item 6; `WP5_HANDOFF.md` (the
IdeaPress pages and where their fixtures were recorded from); `WP1_HANDOFF.md` §3 (the page kit);
`apps/ideapress/api.md` — the attempt payload.

**Code to read first:** the IdeaPress unit/attempts template and its route in `web/`; the recorded
fixtures under `tests/fixtures/ideapress/` — WPF7 already re-recorded them with `transport_call`
(`b6e24f8`).

## What this row has to settle

1. **Two rows of one attempt are told apart by what they are, not by their outcome.** Show
   `transport_call` in the attempts table, in the kit's own style (a numbered call within the
   attempt, or a *call 1 of 2* form — pick what the design brief already has for a sub-sequence).
2. **A discarded call reads as discarded.** The first row of a retried attempt carries
   `provider_error` and the tokens it spent; the page should not make it look like a second
   failed attempt. One line of copy, not a new component.
3. **Nothing else.** The export's `ExportAttempt` does not carry the field (WPF7 §8, a version
   question) and this row does not touch it.

## Gates

**Gate A.** Tests first against the recorded fixture: the two calls of one attempt render with
their call numbers. Implement. Gate green, interpreter named; the per-page JavaScript budget
(ADR-0139) untouched. Commit.

**Gate B.** Against the reference machine's IdeaPress, a unit page whose attempt was retried
(WPF7's Gate C left the evidence in the operator's database) renders both calls, screenshot at
1440 and 412 px in both themes — the browser recipe is in `WPF5_HANDOFF.md` §9.

## Finish line

- The gate green; `git status --short` clean.
- `docs/history/handoffs/WPF12_HANDOFF.md`, the row marked done. Nothing pushed.
