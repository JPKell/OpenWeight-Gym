# ADR-0057 — The trajectory explanation is materialized; the rows stay the source of truth

**Status:** Accepted (2026-09-02)
**Extends:** [PromptCadence Lifecycle §9.1](../apps/promptcadence/lifecycle.md),
[PromptCadence Spec §11](../apps/promptcadence/spec.md) (contract 2) and
[§15](../apps/promptcadence/spec.md) (the retrieval budgets).
**Relates to:** [ADR-0030](0030-model-cost-and-pricing.md) (store the facts, derive the figure —
the discipline this copies), [ADR-0051](0051-plans-stay-internal-and-one-payload-travels.md) (the
document being materialized), [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md)
(every intent revision is part of the record), [ADR-0044](0044-a-state-change-and-its-event-are-one-write.md).
**Source:** [PromptCadence roadmap §2, D-13](../roadmap/promptcadence-roadmap.md).

## Context

PromptCadence's second public contract is that every trajectory yields a complete, retrievable
account: the plan and its verdicts, every intent revision, every turn with its provenance and
LoadCoach explanation reference, every tool call, ledger entry, egress decision, deviation,
approval and compaction, in order. Retention is **forever by default** — the records and hashes
outlive the transcript text, deliberately, so a trajectory stays explicable after its content is
swept.

Composing that document is a seven-table reconstruction whose cost grows with turn count and
deviation count. On a long-lived deployment "explain trajectory X" becomes the dominant read, and it
is re-paid in full on every one of them, for records that stopped changing months earlier. The
budget in spec §15 is ≤ 25 ms for a terminal trajectory of *any* size, which a live composition of a
500-turn trajectory will not meet.

The obvious fix is a cache, and the obvious cache is the trap. A composed document persisted beside
its rows drifts the moment anything changes a row — and things do change rows here: the retention
sweep scrubs content, a corrected price record re-costs ledger entries, a document-schema minor bump
changes the shape. A cache that quietly diverges from its source in a record whose purpose is audit
is worse than no cache, because it is confidently wrong in the place people trust most.

## Decision

**The composed explanation is materialized as revisioned snapshots at terminal transitions. The
rows remain the sole source of truth, and the materialization is a derived cache that can be dropped
and rebuilt at any time.**

1. **Materialize at terminal transitions only.** When a trajectory reaches `completed`, `halted`,
   `failed`, `rejected` or `cancelled`, the document is composed once and persisted as
   `explanation_revisions` revision 1 — the body in the artifact directory with its hash on the row,
   per the suite's large-payload rule. A terminal trajectory is immutable, so the snapshot is
   write-once and every later read is one row plus one artifact fetch, independent of turn count.
2. **In-flight trajectories compose live.** An active trajectory is short relative to the archive,
   and a snapshot of a moving record would be stale before it returned.
3. **The rows are authoritative; the revision is derived.** This is
   [ADR-0030](0030-model-cost-and-pricing.md)'s discipline — store `TokenUsage` and the
   `pricing_hash`, derive the money — applied to a document instead of a figure.
4. **Every row-changing operation bumps the revision, and records why.** The retention sweep
   (content scrubbed → revision *n+1* with "content removed by retention" stubs), a ledger re-costing
   under a corrected price record, a document-schema minor bump on upgrade. A revision is never
   edited; superseded revisions keep their artifacts until an operator prunes them.
5. **`materialize(rows) == compose_live(rows)` is a tested equality**, golden-tested for every
   fixture trajectory including post-scrub and post-re-costing revisions. `promptcadence db
   rebuild-explanations` exists so the cache can be discarded and rebuilt on demand — the operational
   form of the same claim.

## Alternatives considered

**Compose live, always.** No cache, no revisions, no invalidation, no equality test — and it is
correct by construction, which is a serious argument in a governance record. Rejected on the
measured shape of the workload rather than on principle: retention is forever, the archive grows
without bound, and the dominant query would re-derive an unchanging document from seven tables on
every read. The §15 budget of ≤ 25 ms "for a terminal trajectory of any size" is precisely the
promise that a live composition cannot keep, and it is a promise worth keeping because an
explanation nobody waits for is an explanation people actually read.

**Materialize incrementally, per turn**, appending a segment as each turn commits. Better latency
distribution — no 2-second pause at the end of a 500-turn trajectory — and no large synchronous
composition anywhere. Rejected for now on complexity: every deviation, re-approval and re-costing
would have to invalidate a segment range rather than a document, and the equality test becomes a
test over an assembly algorithm rather than over one function. It is deliberately kept as this
record's revisit trigger, because it is the right answer if the terminal pause ever becomes
user-visible.

**Treat the snapshot as the source of truth and let the rows be prunable** — the natural next step
once a document exists, and it would let retention delete rows outright. Rejected outright: the
snapshot would become an un-auditable artifact whose derivation nobody can re-check, and the first
schema change would strand every old one. The equality test is only meaningful while the rows can
still produce the document.

**Cache without revisions** — one materialization per trajectory, overwritten when rows change.
Rejected: an overwritten explanation destroys the answer to "what did this record say before the
retention sweep?", which is exactly the question an audit asks after a dispute. Revisions cost rows
and artifacts; they buy a record that cannot be quietly rewritten.

**Materialize on first read instead of at the terminal transition** (lazy). Slightly less work for
trajectories nobody explains. Rejected: it puts an unbounded composition on a user-facing read,
which is the latency this record exists to remove, and it makes the first reader pay for everyone
else. Terminal transitions are already the moment the trajectory stops changing, and they already
carry a write.

## Consequences

* PromptCadence owns an `explanation_revisions` table plus artifacts, and a maintenance command
  that rebuilds them. Storage grows with revisions, and pruning superseded revisions is an
  operator's explicit action rather than an automatic one.
* Reading a terminal trajectory's explanation is a row and a file, meeting the §15 budget for any
  size. Reading an in-flight one costs what it costs and is bounded by the trajectory's own length.
* The retention sweep, the re-costing path and the upgrade path each acquire an obligation: bump the
  revision and record the reason. A change that edits rows without bumping is a defect the equality
  golden is designed to catch.
* Materialization happens as the terminal transition's follow-up work, not inside the transition's
  own transaction — the state change and its event commit together
  ([ADR-0044](0044-a-state-change-and-its-event-are-one-write.md)) and the document is composed
  after, so a slow composition can never delay or fail a state change.
* **A cost stated plainly:** a 500-turn trajectory pays up to ~2 s of composition at the moment it
  finishes. That is budgeted in §15 and measured in P9, and it is the number to watch — see below.

## Revisit when

Materialization cost at terminal transitions becomes **user-visible latency** — a trajectory whose
completion visibly stalls while its document is composed. The move at that point is the incremental
per-turn segmentation rejected above, with its invalidation rules and an equality test over the
assembly, not a smaller document or a lazier cache.
