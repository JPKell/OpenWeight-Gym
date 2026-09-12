# Kickoff — WPF9: a juror that never answers is named, not silently dropped

**Row:** WPF9 (Opus 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WPF8's Gate B ([`WPF8_HANDOFF.md`](../handoffs/WPF8_HANDOFF.md) §9.2). Runs after WPF8.
**Ships:** unreleased, no version bump.

**Component:** `~/ai/suite/FreeWeight` (and `WeightRoom/docs/apps/freeweight/api.md`, the canonical
copy, if the refusal's shape changes).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WPF8_HANDOFF.md` §9 (all of it — §9.2 is the finding, §9.3 is the fork that worked
around it); `WPF7_HANDOFF.md` §2, the same shape in IdeaPress; `I6_HANDOFF.md`, what `think=false`
does and does not do across models; ADR-0031 (the jury), ADR-0099 (thinking control is not a SetSpec
capability).

**Code to read first:** `services/jury.py` — `JuryService._request`, `_poll_rubric`'s refusal path,
`REFUSED_PROTOCOL`, `_parse_grade`; `services/calibration.py`'s `_exclusion_reason` (WPF8's own
work, which already carries a reason through to the report).

## What Gate B measured on the reference machine (2026-09-12)

One rubric call to `wp6_goal`'s own juror, `llamacpp/Qwen3.5-9B-UD-Q8_K_XL@sha256:2c4e08e0e72c`,
through FreeWeight's own prompt and provider:

```
finish_reason: length
usage: input_tokens=1180, output_tokens=7012
raw answer: (empty)
parsed: (None, None)
```

Every such sample becomes `protocol_error`, and the report says only that. Three of four samples for
`technical_correctness` went that way. The instruct juror the operator forked to answered all four
in 90 seconds each.

## What this row has to settle

1. **The refusal must name the cause.** A verdict that came back `finish_reason: length` with no
   parsable grade is *not* the same event as a juror that answered something unusable, and the
   report cannot currently tell them apart. Decide the vocabulary (a new `refused_reason`, or the
   `finish_reason` recorded beside `protocol_error`) and carry it into the report's `excluded`
   entries, which WPF8 already plumbed end to end.
2. **Whether FreeWeight bounds the judge's output at all.** `_request` sets no `max_output_tokens`.
   Decide whether a judge call gets an explicit budget, and what happens when the budget is spent.
3. **Whether FreeWeight asks a reasoning juror not to reason.** I6 measured that `think=false` is
   honoured by most models and crashes some; ADR-0099 says it is not a SetSpec capability. If the
   answer is "no", say so in the ADR and make the refusal legible instead — a juror that cannot
   answer inside its budget is a juror the goal should not have pinned, and the report should say
   that in words.
4. **Whether the eligibility check should refuse such a juror up front** (`GET /judges` reports
   every model as eligible today, reasoning or not).

## Gates

**Gate A.** Tests first, against the decisions above. Implement. Run the gate, naming the
interpreter. Commit. An ADR if any of items 2–4 is a decision the docs do not already carry.

**Gate B — the live proof.** On the reference machine, with a goal pinned to a reasoning juror
(`wp6_goal`'s pack before the WPF8 fork is in that row's scratchpad backup, or pin one in a scratch
goal): the calibration completes, and the report names *why* each sample was dropped in words an
operator can act on. Check `nvidia-smi` and ADR-0119 before starting.

## Finish line

- The gate green, interpreter named, coverage held; `git status --short` clean.
- `docs/history/handoffs/WPF9_HANDOFF.md`: the decisions, the live numbers, what this kickoff got
  wrong.
- The row marked done. Nothing pushed.
