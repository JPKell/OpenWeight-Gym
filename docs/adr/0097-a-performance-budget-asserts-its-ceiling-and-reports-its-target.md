# ADR-0097 — A performance budget asserts its ceiling and reports its target

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Spec §15](../apps/promptcadence/spec.md) — the assertion policy under
the table; §18's Performance row.
**Relates to:** [Performance Targets](../architecture/performance-targets.md) (target/ceiling
pairs across the suite), [ADR-0093](0093-materialization-follows-the-terminal-transition.md)
(the two explanation budgets and why the read path is measured separately).
**Source:** Row I2, decision 3. The shape is LoadCoach's `tests/performance/`.

## Context

Spec §15 lists ten budgets, each with a **target** and a **ceiling**. Phase 9 says every one is
"measured on the reference machine and asserted". Three things are unsettled: whether the test
fails at the target or at the ceiling; which statistic over how many iterations; and which rows
are asserted in CI versus measured once on the reference machine and written down. Left
unsettled, the first slow CI runner turns a budget into a flake and the response is to widen it —
the one thing the row's stop rules forbid.

## Decision

**Every §15 row is a test under the `performance` marker. The test fails when the median exceeds
the ceiling. It prints the median, the p95 and the target, and the handoff records the numbers.**

1. **The ceiling is the failing bound.** A ceiling is the figure past which the harness is doing
   something wrong; a target is what a healthy machine achieves. Asserting the target would make a
   loaded CI runner red for nothing; asserting nothing would make the table decoration.
2. **The statistic is the median over 20 measured iterations after 3 warm-ups**, matching
   LoadCoach. The p95 and the maximum are printed beside it, never asserted: a single garbage
   collection is not a regression.
3. **Every row is asserted, none is measured-and-recorded only.** The three scale rows — the
   500-turn materialization, the 200-turn compaction plan and the 100-trajectory recovery — are
   built synthetically in the test from rows, not from a live run; a fixture that takes seconds to
   seed is still a test. The recovery row's ceiling is ten seconds, which bounds the fixture's
   cost.
4. **LoadCoach time and tool time are subtracted, never folded in.** The per-turn overhead row is
   wall time for the turn minus the `timing.total_ms` LoadCoach reported minus the tool calls'
   `duration_ms`; the test asserts the three are recorded separately on the turn and the record
   before it subtracts. The fake LoadCoach's reported time is a scripted constant, so the
   subtraction is exact.
5. **A missed ceiling is a finding, never a knob.** The number goes to the operator in the handoff
   with the row's name; the ceiling in §15 is not edited to make the suite green. If a ceiling is
   wrong, that is a spec amendment with its own reason, made before the test, not after it fails.
6. **The default gate excludes the marker** (`addopts` already does), so the budgets never make
   the ordinary suite slow or flaky. They run on the reference machine before a release and
   nightly.

## What this refuses

* Asserting a target.
* Asserting a maximum or a p95.
* A row measured by hand and written into the handoff with no test behind it.
* Widening a ceiling in the same commit as a failing budget.

## Alternatives considered

**Assert the target, since that is what §15 "expects".** It is what a healthy install achieves,
and asserting it makes every slower machine red. The ceiling is the contract; the target is the
report.

**Measure the three scale rows once and record them.** Cheaper to write, and it leaves the rows
that are most likely to regress with growth — recovery over many trajectories, composition over
many turns — without a test. A synthetic fixture costs a few seconds.

**Assert per-row statistics chosen per row.** More precise and more to argue about. One rule,
applied ten times, is easier to hold.

## Consequences

* `tests/performance/` holds ten assertions over the loop harness, the explanation builder, the
  compaction service, the ledger and the SSE source. Each prints its numbers; the handoff copies
  them.
* The ≤ 25 ms per-turn overhead row is reported **as a number** in the handoff, beside the
  LoadCoach time and the tool time it was separated from, because that row is the one the
  roadmap's risk table watches.
* Nothing changes in the default gate.

## Revisit when

A row's ceiling binds on the reference machine for a structural reason — I1 §7.2 named one
candidate, compaction re-planning from the whole transcript on every turn. That is a decision
about the mechanism, taken as its own record, not a wider ceiling.
