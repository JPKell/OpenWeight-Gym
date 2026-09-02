# ADR-0067 — Reliability and the breaker key on the subject, never on the base

**Status:** Accepted (2026-09-02)
**Extends:** [LoadCoach Routing §11](../apps/loadcoach/routing.md) (production evidence and
reliability), [Adapter Identity and Serving §10](../architecture/adapter-identity-and-serving.md).
**Relates to:** [ADR-0037](0037-production-evidence-never-raises-capability-scores.md) (what
production evidence may and may not do), [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md)
(the subject being keyed on), [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md)
(the same refusal to attribute one subject's numbers to another).
**Source:** [Adapter roadmap §2, A-10](../roadmap/adapter-roadmap.md).

## Context

LoadCoach tracks reliability from production outcomes and breaks a circuit when a model fails
repeatedly. With adapters, the question is what "a model" means for that purpose: the base process,
or the `(base, adapter)` subject running on it.

Pooling on the base is attractive for one strong reason — **samples**. Reliability wants volume, and
splitting one base's traffic across four adapters splits its evidence four ways, so a breaker keyed
per subject reacts more slowly and a low-traffic adapter may never accumulate a meaningful rate at
all. Pooling also handles the case where the base genuinely is the problem: a corrupted GGUF or a
broken chat template fails every adapter, and one pooled counter would notice immediately.

Against that, the observed failure modes of adapters are mostly *adapter-specific*: a LoRA that
produces unparseable structured output, an adapter whose template expectations differ, a bad
conversion. Under pooling, one such adapter would drive the base's counter and break the base — and
with it every sibling adapter and the bare base itself. A five-megabyte delta would take a
nine-gigabyte model out of routing.

## Decision

**Reliability statistics and the circuit breaker key on the execution subject.**

1. **A failing `(base, adapterA)` is deprioritized and eventually broken *as that subject*.** It
   never breaks the bare base, and it never breaks a sibling adapter.
2. **Process- and transport-level failures are availability, not reliability.** A `llama-server`
   that will not start, a dead port, a connection refused — these are provider health facts, and
   they take every subject on that provider out of the candidate pool through the existing
   `model_unavailable` hard constraint ([LoadCoach Routing §4](../apps/loadcoach/routing.md)): a
   statement about reachability, never about a subject's quality, and distinct from the
   load-driven `availability_factor` of Routing §6, which they do not touch. Keeping the two
   separate is what stops a crashed process from looking like four failing adapters.
3. **Cross-adapter attribution is not inferred in v1.** "Is the base failing?" is deliberately left
   to a human, reading the per-subject rows the explanation already shows. The suite does not guess
   at it, and it does not pretend to.
4. **The cost is named, not hidden.** Per-subject sample counts fragment; the 20-sample minimum
   applies per subject; low-traffic adapter subjects will carry `low_evidence` flags for a long time.
   That is reported honestly rather than papered over by borrowing a neighbour's numbers.

## Alternatives considered

**Key reliability on the base and pool across its adapters.** The strongest alternative, and the one
that solves the real problem: four times the samples, a breaker that reacts in useful time, and
immediate detection when the base itself is broken. Rejected on the direction the attribution flows.
The dominant failure modes are adapter-specific, so pooling routinely charges a base with a single
adapter's defect — and the consequence is severe and wide: the bare base and every sibling adapter
leave the candidate pool because of one bad conversion. Given a choice between a breaker that reacts
slowly to a real base failure and one that reacts quickly to the wrong subject, the slow honest one
is the right default; base failures also surface through availability (rule 2), which is the faster
signal for exactly the case pooling was meant to catch.

**A hierarchical estimator: subject-level rates shrunk toward the base's pooled rate when samples are
few.** The statistically sophisticated answer, and it genuinely dissolves the trade-off — sparse
subjects borrow strength, dense ones do not. Rejected for v1 because choosing a shrinkage rule needs
data nobody has yet: how correlated adapter failures actually are on one base is the empirical
question, and picking a coefficient in advance means silently propagating one adapter's failures onto
its siblings at a rate chosen by guess. Worse, the resulting number would be neither measured nor
attributable — a reader could not tell how much of a subject's rate came from its own traffic. It is
the right thing to build once there are rows to fit it against, which is precisely this record's
revisit trigger.

**Automatic base-failure attribution** — infer "the base is broken" when every adapter on it degrades
together. Rejected for v1: it is an inference over sparse, correlated samples, and a human reading
four per-subject rows does it better and with context the router does not have. It is listed among
the architecture's deliberate v1 exclusions rather than left as an oversight.

**Key on the base for availability *and* quality, and expose per-subject rows for display only.**
Half-measures in the wrong half: routing would still act on the pooled number, so the display would
show the operator a truth the router was ignoring.

## Consequences

* LoadCoach 1.1 tracks reliability per subject, which means more counters, more rows, and slower
  accumulation per counter. `low_evidence` on reliability becomes common on adapter subjects, and the
  explanation says so rather than presenting a rate computed from three samples as a rate.
* A bad adapter degrades and breaks alone. The base and its siblings keep routing, which is the
  property that makes it safe to add an adapter to a working deployment at all.
* Diagnosing "is the base failing?" is an operator task, supported by the explanation's per-subject
  rows and by `doctor`'s provider reporting. The suite claims no more than that.
* Availability and reliability stay separate concepts in the routing explanation, and the adapter
  work does not blur them — a distinction that already existed and that this record makes
  load-bearing.
* The breaker's per-subject keying interacts with residency
  ([ADR-0066](0066-residency-is-two-level.md)): a broken adapter subject does not evict its base, so
  the warm base keeps serving its siblings while one subject sits out.

## Revisit when

Fragmented samples make per-subject reliability **useless in practice** — adapter subjects that never
reach a meaningful sample count, or a breaker that never fires on a subject that plainly deserves it.
The response is to revisit the **pooling rules explicitly**, with the accumulated per-subject rows as
the evidence for how correlated adapter failures really are, rather than to adopt base-level pooling
as a default nobody measured.
