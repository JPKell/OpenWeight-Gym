# ADR-0093 — Materialization follows the terminal transition, and a missing revision is not a missing explanation

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Lifecycle §9.1](../apps/promptcadence/lifecycle.md) — "the same
transaction's follow-up work composes the document once" is made precise: a follow-up write, not
the transition's own transaction.
**Relates to:** [ADR-0044](0044-a-state-change-and-its-event-are-one-write.md) (a state change and
its event are one write — which this record does not weaken),
[ADR-0092](0092-the-invalidation-entry-point-ships-before-the-sweep-that-calls-it.md) (the other
way a revision comes into being), [ADR-0030](0030-model-cost-and-pricing.md) (the discipline this
copies: store the facts, derive the view).
**Source:** Row I1, decision D5.

## Context

The composed explanation is materialized once when a trajectory reaches a terminal state. Spec §15
budgets that composition at ≤ 2 s for a 500-turn trajectory, ceiling 10 s. ADR-0044 requires the
state change and its event to be one write. Putting composition inside that write means up to two
seconds — ten at the ceiling — of a write transaction held open on the trajectory's rows, on
SQLite, while every other worker's write waits behind it. The transition is a few hundred bytes of
row change; the composition is a multi-table read of everything the trajectory ever did.

## Decision

**The terminal transition commits alone. Materialization runs immediately afterwards, in its own
write. A revision that never appears is not an error.**

1. **The transition is unchanged.** `trajectory.completed` / `.halted` / `.failed` / `.cancelled`
   and their row updates remain one write, exactly as ADR-0044 requires. Nothing is added to it.
2. **Materialization is the next write.** After the transition commits, the same call composes the
   document from the rows and writes `explanation_revisions` revision 1 plus the artifact under
   its digest. It is idempotent: a revision already present for that trajectory and schema version
   is left alone.
3. **A process that dies in between loses a cache, not a record.** The rows are the source of
   truth. A terminal trajectory with no revision is served by the **live composition path**,
   which every in-flight read already uses, and the missing revision is filled in by
   `promptcadence db rebuild-explanations`. There is no repair state, no "materializing" flag and
   no reader that has to branch on one.
4. **The tests prove it is a cache.** `materialize(rows) == compose_live(rows)` is asserted for
   every fixture trajectory; and mid-suite **every row of `explanation_revisions` is deleted** and
   every explanation read is asserted to answer identically. A cache whose deletion changes an
   answer is not a cache, and this is the assertion that would catch it.
5. **Failure to materialize never fails the trajectory.** A composition error is logged and the
   trajectory stays terminal. Making a completed trajectory fail because its cache could not be
   written would be the cache deciding the record.

## Alternatives considered

**Compose inside the transition's transaction.** The literal reading of §9.1, and it gives the
strongest guarantee: a terminal trajectory always has its revision. Rejected on the lock — up to
ten seconds of held write transaction on the suite's default engine, paid at exactly the moment a
worker is finishing one trajectory and wants to claim the next — and because the guarantee it buys
is one rule 3 shows is not needed. It would also make composition failure a reason for a
successful trajectory not to be marked successful.

**Compose lazily, on the first read of a terminal trajectory.** No transition cost at all, and the
first reader pays 2 s instead of 25 ms. Rejected because it moves an unbounded cost onto an
interactive surface and makes the §15 read budget unmeetable exactly once per trajectory — the
one time somebody is definitely watching.

**Queue materialization as a job.** Correct, and a second scheduler for one job whose failure mode
is "the cache is missing, and the read path already handles that". Refused as machinery bought
with nothing to spend it on.

## Consequences

* The window between the transition and the revision is real and is served correctly. It is also
  the same window `rebuild-explanations` exists to close in bulk.
* `explanation_revisions` is genuinely droppable: `DELETE FROM explanation_revisions` is a
  supported operation whose only visible effect is slower reads until the next rebuild.
* The §15 read budget (≤ 25 ms, any size) applies to the materialized path. A read served live
  because the revision is missing is measured against the composition budget instead, and the
  surface says which path answered.
* Determinism is load-bearing rather than decorative: the equality golden compares bytes, so fixed
  key order, timestamps rendered from stored values, no `set` in a serialized position and no
  dict-iteration dependence are requirements of this record, not style.

## Revisit when

PostgreSQL becomes the primary deployment engine — MVCC removes the lock argument, and composing
inside the transition would then be a free strengthening. Or if a deployment shows a materially
long window where reads are slow enough to matter.
