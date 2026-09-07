# ADR-0081 — An adapter subject inherits no evidence from its base

**Status:** Accepted (2026-09-05)
**Extends:** [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the execution subject
gains an adapter axis), [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)
(adapters are selected through the capability vocabulary).
**Relates to:** [ADR-0022](0022-capability-evidence-record-contract.md) (evidence binding and match
states), [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) (evidence is measured against
the subject), [ADR-0067](0067-reliability-keys-on-the-subject-not-the-base.md) (reliability keys on
the subject), [LoadCoach Routing §5](../apps/loadcoach/routing.md).
**Source:** Row H2, gate D — a decision the gate had to take and no record covered.

## Context

[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) §4 settled one direction of this
question and left the other open. Importing an adapter-bearing evidence record and binding it to the
**base's** registry row would raise the score of weights nobody measured, so `bind_identity` retains
such a record `unmatched` — LoadCoach 1.1 implements exactly that.

Gate D then hit the mirror image. A subject is `(base, adapter)`, and the base already carries
capability signals: declared provider flags, manual scores from configuration, imported benchmark
evidence, production statistics. When routing expands the candidate list to adapter subjects, it has
to decide what each new subject knows about itself. Doing nothing is not neutral: the subject is
built from the base's `ModelFacts`, so the base's signals arrive with it unless they are removed.

The two answers are not close in consequence. Inheriting the base's benchmark evidence makes an
unmeasured adapter score exactly as well as measured weights it has never been compared against —
and it does so *invisibly*, because the explanation would name a `benchmark` source for a subject no
benchmark ever ran on.

## Decision

**An adapter subject carries only the capability signals its own manifest declares. It inherits
nothing from the base it runs on — not benchmark evidence, not manual scores, not production
statistics, not declared provider flags.**

1. **Its signals are the manifest's `declared_capabilities`**, validated vocabulary terms
   ([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) rule 1), carried at
   the same score and confidence any declared capability gets. A declaration is a statement, never a
   measurement, and scoring already maps it to a neutral prior rather than to an ability.
2. **A base's benchmark evidence describes bare weights.** It is the same argument
   [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) §4 makes about the import path,
   applied in the other direction: a measurement taken without the adapter says nothing about the
   subject that applies one, and attributing it would be a fabricated measurement in everything but
   name.
3. **Production statistics are already excluded by
   [ADR-0067](0067-reliability-keys-on-the-subject-not-the-base.md)** — reliability keys on the
   subject — and this record makes the same rule true of the capability half, so a reader does not
   have to hold two different inheritance rules in mind for one subject.
4. **The consequence is stated rather than discovered.** With `require_adapter_evidence` on (the
   shipped default, [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)
   rule 3), an adapter subject is rejected `adapter_unmeasured` before scoring reaches it. With the
   gate **off**, it scores on declared terms and priors alone, so it will usually rank *below* a
   base carrying real evidence. That is not a defect: until FreeWeight measures adapters (LA3),
   **a pin is how an adapter is used**, and a pin bypasses scoring by design.

## Alternatives considered

**Inherit the base's evidence, discounted by a factor.** Cheap, and it puts an adapter subject in
the same score range as its base so ranking stays intuitive. Rejected: the discount would be a
number chosen to feel right, applied to a measurement it did not come from, and the explanation
would then present a `benchmark` source for a subject that was never benchmarked. It is the
fabricated-measurement failure the whole evidence design is written against
([ADR-0016](0016-unavailable-is-not-zero.md)'s instinct, applied to attribution).

**Inherit only the *declared* provider flags** — tool use, structured output, vision — on the
grounds that they describe the serving stack rather than the weights. Genuinely arguable, and it
would let an adapter subject satisfy `requires_capabilities` the way its base does. Rejected as
unnecessary rather than as wrong: those flags are read from `ProviderFacts` in the hard-constraint
filter, which every subject on that provider shares, so the capability constraint already behaves
correctly without giving the subject signals it did not earn. Duplicating them as *signals* would
put the same fact in two places with two meanings.

**Let the manifest declare a "same as base" inheritance.** Rejected: it is a per-artifact switch
that turns unmeasured weights into measured ones, which is the one thing the reviewed-manifest
design exists to make impossible.

## Consequences

* An adapter subject's explanation shows `declared` sources and priors, never `benchmark`, until
  FreeWeight measures adapter subjects. The models view says the same in the `evidence_source`
  column, so the state is visible before a routing decision surprises anybody.
* `require_adapter_evidence` is doing real work rather than guarding a case that cannot arise: with
  no inherited evidence, every adapter subject genuinely is unmeasured today.
* Turning the gate off does **not** make adapters win — it makes them eligible and usually
  unselected. An operator who wants a specific adapter pins it, which is the intended path and the
  one the live LA2 journey demonstrates.
* When LA3 lands, adapter evidence arrives keyed on the subject and enters through the same signal
  path as any other measurement. Nothing here has to be undone: the subject starts empty and fills
  with its own numbers.

## Revisit when

FreeWeight measures adapter subjects and a deployment finds that a base's evidence would have been a
*better* prior for an unmeasured adapter than the parameter-band prior it gets — measurably better,
on its own numbers, not by intuition. At that point the question is which prior a subject with no
evidence should fall back on, which is a scoring-prior decision
([routing §5.1](../apps/loadcoach/routing.md)) rather than an inheritance decision, and it should be
taken there.
