# ADR-0063 — One adapter at a time, at a fixed scale

**Status:** Accepted (2026-09-02)
**Extends:** [Adapter Identity and Serving §11](../architecture/adapter-identity-and-serving.md)
(deliberately excluded from v1).
**Relates to:** [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (identity is one
content-addressed artifact), [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) (every
subject is measured, which is what makes the subject count matter),
[ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) (the request field that
would permit composition).
**Source:** [Adapter roadmap §2, A-6](../roadmap/adapter-roadmap.md).

## Context

llama.cpp's `lora` request field is a **list** of `{id, scale}` entries. Composition — a domain
adapter and a style adapter applied together, each at its own weight — is therefore available for
free, needs no new machinery, and is a thing people genuinely want: "answer like our house voice,
about our domain" is two adapters and one request.

The cost is not in the serving. It is in every rule this arc has just written down.

**Identity.** `AdapterIdentity` is one artifact's digest
([ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md)). A composition is an ordered
weighted set, and naming one forces a choice with no good branch. If scale is part of identity, then
0.70 and 0.71 are different subjects and the subject space is continuous — evidence can never
accumulate against any of them, because no two requests ever share a subject. If scale is *not* part
of identity, then two materially different behaviours share one name and their measurements merge,
which is exactly the fabricated comparability the adapter axis exists to prevent.

**Evidence.** [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) requires every subject
to be measured, with a 20-sample minimum. A base with *n* adapters has *n + 1* subjects. Allow
composition and it has up to *2ⁿ*, before scales. The measurement burden stops being affordable, and
the pressure to inherit evidence — the thing the arc most firmly refuses — comes straight back, this
time with an excuse.

## Decision

**A request selects at most one adapter, applied at a fixed scale. There is no composition and no
scale mixing.**

1. **One adapter per request.** The provider sends at most one `lora` entry. Two adapters on one
   request is a typed refusal, not a merge.
2. **Scale is fixed, and is not a request parameter.** The adapter is applied as it was trained and
   benchmarked. A per-request scale would vary behaviour without varying identity — the same defect
   as composition, in miniature — so the identity design forecloses it: there is nowhere in
   `AdapterIdentity` for a scale to live, and that is deliberate rather than an omission.
3. **The refusal is explicit.** A caller asking for two adapters gets a named error, never a silent
   selection of the first one.

## Alternatives considered

**Support composition now, since the serving layer already does.** The honest case for it is strong:
it costs no new serving code, it is a real user need, and deferring it means a user who wants domain
plus voice must train a combined adapter instead of composing two. Rejected on identity and
evidence, not on effort. The identity of a weighted set has no answer that is both stable and
faithful — scale-sensitive identity makes evidence unaccumulable, scale-insensitive identity makes
different behaviours share a name — and until that is solved, composition would put unmeasurable
subjects into a routing system whose entire claim is that it routes on measurements. The evidence
space squaring is the second, independent reason: `2ⁿ` subjects at 20 samples each is a benchmarking
bill nobody pays, and an unpaid benchmarking bill becomes an argument for inheritance.

**Support composition but exempt composed subjects from the evidence gate** — let them be pinned
only, never routed. This is the narrow version, and it is genuinely tempting because it confines the
damage: a user could compose deliberately without polluting routing. Rejected because the
measurements would still be recorded against a subject whose name does not determine its behaviour,
so the *records* would be wrong even if the routing was not — and a record that cannot be reproduced
from its own identity is not evidence. Fixing that means solving the identity problem first, which
is the revisit trigger.

**Allow a per-request scale on a single adapter**, without composition. Smaller, and it looks like a
tuning knob rather than a design change. Rejected for the same identity reason at one adapter: two
requests at 0.5 and 1.0 would produce one subject and two behaviours, and every measurement taken
under either would be attributed to both.

**Allow composition only where every component adapter has been measured individually.** Rejected:
individual measurements do not predict a composition's behaviour — that is the same inheritance
fallacy [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) rejects, one level up.

## Consequences

* The serving layer's list-shaped `lora` field is used with exactly one entry, and the provider
  enforces it. A future composition feature would be a change in the suite, not in llama.cpp.
* A user who needs two behaviours trains one adapter for them, or picks one. That is a real product
  limitation, stated plainly in the documentation rather than discovered.
* Subject counts stay linear in adapter count, which is what keeps
  [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md)'s per-subject benchmarking
  affordable and therefore keeps it enforced.
* Identity stays one digest, which keeps the canonical suffix, the compatibility check and the
  evidence key simple everywhere they appear.
* Scope creep toward composition is a named risk in the adapter roadmap; this record and §11 of the
  architecture document are the two places that hold the line, and both require a new ADR to move
  it.

## Revisit when

A **concrete consumer need** appears — a named use case, not a general preference — **and the
identity-of-a-weighted-set problem is solved first**. The order matters: the reopening decision must
state how a composition is named such that the same name always means the same behaviour, how its
evidence is measured without inheriting from its components, and what the subject-space growth costs
in benchmark time. A proposal that answers the need without answering those three is this
alternative returning unchanged.
