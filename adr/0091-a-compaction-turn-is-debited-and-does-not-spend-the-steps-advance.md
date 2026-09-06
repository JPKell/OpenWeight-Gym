# ADR-0091 — A compaction turn is debited, and does not spend the step's advance

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Lifecycle §7](../apps/promptcadence/lifecycle.md) — adds what "is itself
a turn" does *not* imply.
**Relates to:** [ADR-0076](0076-a-step-retry-is-a-repeat-under-the-same-intent.md) §5 (attempts and
turns draw on one envelope), [ADR-0030](0030-model-cost-and-pricing.md) (usage is stored, cost is
derived), [ADR-0090](0090-a-compaction-summary-runs-under-a-superseding-revision.md) (the envelope
the same turn runs under).
**Source:** Row I1, decision D2.

## Context

Lifecycle §7 settles the debit: the summarization call "is itself a turn — debited, recorded,
explainable". It says nothing about the *other* per-step ceiling. `max_turns` is the intent's
advance allowance, and the loop spends it as

```text
turns_used = assistant turns in this step's thread + recorded retry attempts
```

(ADR-0076 §5). If a compaction summary is counted there, a long step can be **ended by its own
housekeeping**: `turns_used` reaches `max_turns`, the loop raises `turn_overrun` /
`STEP_LIMIT_EXCEEDED`, and the turn that spent the last unit is one the caller never asked for and
cannot see coming. Worse, whether it happens depends on transcript size, so the same step with the
same plan halts or completes according to how verbose a tool result happened to be.

## Decision

**The compaction summary is debited against every money and token ceiling, and does not count
against `max_turns`.**

1. **It is debited.** The summary is a real model call with real usage. It is priced and debited
   exactly as any turn is — idempotent by `source_ref`, its own write, its own `budget.debited`
   event — and every active ceiling (the trajectory's, the day's, the project's) sees it. A
   deployment whose compaction spend matters watches it where spend is watched.
2. **It does not advance the step, so it does not spend the advance budget.** `max_turns` counts
   turns that move a step toward its declared finish. Compaction produces no answer to the step's
   question; it makes the next such answer possible. Charging it to `max_turns` makes one ceiling
   do two jobs and lets the cheaper one silently consume the dearer.
3. **The separation is structural, not a filter.** The summary is recorded in **its own thread**,
   whose `step_id` is `compaction:<compaction_id>`, rather than appended to the step's thread. That
   is required for correctness anyway — a summary appended to the thread it summarized would be
   replayed to the model as a conversational turn on the next wire build, double-counting the very
   content it replaced — and it makes rule 2 a property of the shape: the loop counts assistant
   turns *in the step's thread*, and the summary is not in it. There is no flag to read and no
   predicate to keep in sync.
4. **Spend is still bounded.** The thing a runaway compaction would exhaust is the token and money
   ceiling, and rule 1 puts it squarely there. `COMPACTION_FAILED` on an unsatisfiable budget and
   the ordinary budget refusals remain the stops.

## Alternatives considered

**Count it: every model call the step causes spends the step's allowance.** The tidy reading, and
its claim is real — a step that compacts ten times did cause ten extra calls, and something should
bound that. Rejected because `max_turns` is the wrong bound for it: it is per step and integral,
so it cannot express "at most this much housekeeping" without also shortening the work; and it
turns a size-dependent, caller-invisible event into a halt. The ceiling that binds spend already
binds this spend.

**Count it, and raise `max_turns` at compaction time.** Keeps the accounting honest and gives back
what it took. Rejected as a widening minted for a turn already taken — the audit trail would show
an allowance rising whenever it was about to be exceeded, which is an allowance that does not bind.

**Give compaction its own per-step counter.** A third ceiling nobody asked for, configured by
nobody, to bound something the token ceiling already bounds. Refused as speculative until a
deployment shows compaction spend that the token ceiling did not catch.

## Consequences

* A step whose `max_turns` is nearly spent still compacts and still gets its remaining turns. This
  is asserted at the boundary: a step at `max_turns - 1` that compacts completes.
* `compactions` rows and their summary turns are visible in the explanation and the console under
  the step they served, not inside the step's transcript.
* The step's thread and the compaction's thread both belong to the trajectory, so `GET
  /trajectories/{id}/turns`, the ledger and the explanation see the summary turn without anything
  special; only the step's *wire* excludes it.
* An operator reading `max_turns` sees a number that means what it says: how many times the model
  may answer this step.

## Revisit when

Compaction becomes able to run more than once per turn boundary, or a deployment reports
compaction spend that the token ceiling did not bound. The first would make the per-step count
interesting again; the second is the empirical claim rule 4 rests on.
