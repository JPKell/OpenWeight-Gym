# ADR-0059 — Adapter evidence is measured, never inherited from its base

**Status:** Accepted (2026-09-02)
**Extends:** [ADR-0016](0016-unavailable-is-not-zero.md) (an unknown is never a convenient number),
[ADR-0017](0017-benchmark-confidence-and-freshness.md) (confidence and freshness),
[ADR-0022](0022-capability-evidence-record-contract.md) (the evidence record),
[ADR-0037](0037-production-evidence-never-raises-capability-scores.md) (the other shortcut, already
closed), [ADR-0043](0043-grounding-is-verified-not-assumed.md) (a property nothing measured is not
one the record may assert — here, that a subject's evidence is its own),
[Adapter Identity and Serving §6](../architecture/adapter-identity-and-serving.md).
**Relates to:** [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the subject this
attaches to), [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) (the gate
that enforces it arithmetically), [ADR-0067](0067-reliability-keys-on-the-subject-not-the-base.md).
**Source:** [Adapter roadmap §2, A-2](../roadmap/adapter-roadmap.md).

## Context

An adapter subject arrives with no measurements and an obvious way to fill the gap: it is *mostly*
the base, so let it inherit the base's capability evidence and override only where its own
measurements exist. That would make an adapter usable the moment it lands, which is the whole
appeal.

It is also false in a specific, well-documented way. A LoRA trained for one thing routinely
degrades others — catastrophic forgetting is the norm rather than an edge case, and its severity is
not predictable from the training objective. So an inherited score is not an approximation with an
error bar; it is a number about different weights, published under this subject's name, and biased
in the flattering direction: the base's strengths become the adapter's claims, while the damage the
adapter did is precisely what nobody measured.

The suite has closed two doors of exactly this shape already.
[ADR-0016](0016-unavailable-is-not-zero.md) refuses to let an unavailable measurement become a
number, and [ADR-0037](0037-production-evidence-never-raises-capability-scores.md) refuses to let
observed production outcomes raise a capability score, because production data is not a controlled
measurement. Inheritance is the third door: an unmeasured subject acquiring a measured subject's
credibility.

The countervailing cost is real and must be named. Benchmarking is GPU time nobody has spare, and
requiring it per adapter multiplies the measurement burden by however many adapters a base carries.
A rule that makes adapters expensive to adopt is a rule people route around.

## Decision

**A new adapter subject has no evidence. Every adapter is benchmarked before it is routed to, and
the panel is fixed, small and targeted.**

1. **No inheritance, in any form** — not full, not partial, not discounted. An adapter subject's
   capability evidence is the evidence measured on that subject, and where none exists the answer
   is *absent*, rendered as `—`, never a number.
2. **The panel, per adapter subject**, is three parts and no more:
   * the suites mapping to the manifest's `declared_capabilities` — **the claim under test**;
   * a **fixed regression panel** — `instruction_following`, `structured_output`, and the base's
     strongest measured capability — which is what catches forgetting, and is the part nobody would
     think to run;
   * the **performance suite** — tokens/sec with the adapter active is this subject's own number,
     not the base's.
3. **The serving-mode A/B is measured once per base + runtime profile**, not per adapter. Whether a
   server launched with adapters registered is slower than a clean one is a property of the base and
   its profile ([ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md)), so
   measuring it per adapter would multiply cost and attribute the result to the wrong thing.
4. **The rule is enforced by arithmetic, not by policy.** `require_adapter_evidence` (default on)
   filters an adapter subject with no measured evidence for the profile's top-weighted capability,
   with a named rejection ([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)).
   "No benchmark, no use" is a constraint in the router, not an instruction in a document.
5. **The record carries the adapter.** `CapabilityEvidence` gains optional adapter fields at SetSpec
   v1.1 — the ADR-0032 additive precedent — and a record written without them is byte-for-byte
   today's record.

## Alternatives considered

**Inherit the base's evidence, overridden where the adapter has been measured.** The pragmatic
option, and the one every deployment will reach for: adapters become usable on arrival, and only
the capabilities actually retrained appear to change. Rejected because it gets the *direction* of
the error wrong. Inheritance publishes the base's strengths as the adapter's claims while leaving
the adapter's damage unmeasured, so the fabricated numbers are exactly the ones that win routing.
[ADR-0016](0016-unavailable-is-not-zero.md) calls this the most damaging bug class in a measurement
system, and this is it with a plausible cover story.

**Inherit with a confidence penalty** — carry the base's score at a discount rather than at face
value. The tempting middle, and it has a precedent shape: it is the same move
[ADR-0023](0023-runtime-profile-resolution.md) considered and rejected for runtime-profile
mismatch. Rejected for the same reason, sharpened by the physics: forgetting is not proportional to
anything observable before measurement, so no discount factor is derivable from anything. A
principled-looking number with no principle behind it is worse than an absence, because it survives
review.

**Let production evidence fill the gap** — route to the adapter and learn from outcomes. Rejected by
[ADR-0037](0037-production-evidence-never-raises-capability-scores.md), which already decided that
production evidence never raises a capability score. It can lower confidence and inform reliability;
it cannot manufacture a capability measurement, and an adapter with no benchmark would never get the
production exposure to try.

**Benchmark only the declared capabilities and skip the regression panel.** The cheapest rule that
still measures something, and it tests exactly the claim the manifest makes. Rejected: the claim is
half the question. What the adapter *broke* is the other half, it is invisible to a panel built from
the manifest, and it is the failure a user meets in production — a fact-check adapter that stopped
following instructions looks fine on every fact-check suite. The regression panel is three suites,
chosen to be the cheapest thing that could detect the damage.

**Run the base's full panel against every adapter.** Rigorous, and it would make adapter and base
directly comparable everywhere. Rejected on cost: a full panel is hours of GPU time on a machine
with one card, per adapter, and a rule nobody can afford is a rule that gets disabled. The three-part
panel is the deliberate compromise, and its composition is what the revisit trigger reopens.

**Measure the serving-mode overhead per adapter.** Rejected: it is a property of the base and its
profile, and per-adapter measurement would multiply the cost while attributing the answer to the
wrong subject.

## Consequences

* An adapter is unusable until it is benchmarked — through routed selection and through a pin
  alike, since the gate is a hard constraint and a pin bypasses only scoring. That is the intended
  friction; the gate's recorded off switch
  ([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) rule 3) is the one
  way around it, and it is not silent.
* FreeWeight 1.1 gains adapter subject enumeration and the A-2 panel policy; the benchmarking cost
  per adapter is three suite groups rather than a full catalogue, which is what makes the rule
  affordable enough to keep.
* A manifest that overclaims is caught by its own evidence: declaring `content.fact_check` means
  being measured on it, so the declaration is a claim under test rather than a label
  ([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)).
* Evidence fragments per subject, and the 20-sample minimum applies per subject. `low_evidence`
  flags will be common early in a deployment's life, which is honest and is the point of the flag.
* Nothing about existing evidence changes. A base measured before adapters existed keeps its
  records unchanged, and no record acquires an adapter field it did not have.

## Revisit when

**Never for inheritance** — that is the decision, and no measurement of forgetting would make an
unmeasured number true. What may change is the **panel's composition**: once real forgetting data
exists across several adapters, the fixed regression panel may prove too small (missing a common
damage mode) or unnecessarily large (a suite that never moves). Changing which suites make up the
panel is a tuning decision with its own record; changing whether a panel is required is not.
