# ADR-0064 — Adapters are selected through the capability vocabulary; there is no tag channel

**Status:** Accepted (2026-09-02)
**Extends:** [Master Architecture §1.4](../architecture/master-architecture.md) (capability
vocabulary and the specialization rule), [LoadCoach Routing §5–§8](../apps/loadcoach/routing.md),
[Adapter Identity and Serving §7](../architecture/adapter-identity-and-serving.md).
**Relates to:** [ADR-0031](0031-user-defined-goal-benchmarks.md) and
[ADR-0032](0032-judge-validity-and-user-capability-namespace.md) (the `user.*` namespace this
reuses), [ADR-0040](0040-routing-backend-owns-model-choice.md) (the router owns model choice),
[ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) (what the gate has to filter on),
[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (what is being selected).
**Source:** [Adapter roadmap §2, A-7](../roadmap/adapter-roadmap.md).

## Context

Once a base can serve several adapters, something has to choose which one a request runs under. The
proposal on the table was the obvious one, and it is what almost every LoRA deployment does: give
each adapter a set of free-form tags at drop time (`factcheck`, `house-voice`, `sql`), let a caller
ask for a tag, and match. It costs nothing, it works the moment an adapter lands in the directory,
and it requires no benchmark at all.

The suite already has a vocabulary for "what is this model good at", and it is not free-form. The
SetSpec capability vocabulary is versioned, its additions are minor and its removals major, it
permits namespaced specializations (`coding.python`, `content.fact_check`) that inherit from a
generic root, and [ADR-0032](0032-judge-validity-and-user-capability-namespace.md) added the
`user.*` root precisely so a person's own dimension — a house voice — can carry measured evidence.
Every term in it links to something FreeWeight measured; that linkage is the whole reason routing
can explain itself.

A tag links to a claim. Nobody measured it, nothing decays it, and no arithmetic can compare two of
them. So the choice is not really "tags or capabilities" — it is whether adapter selection joins
the machinery that makes routing accountable, or runs beside it on assertions.

The arc's honesty claim depends on the answer. "No benchmark, no use" is the thing that stops an
adapter's confident, damaged output from being routed to on the strength of its name — and it is
not implementable over tags, because a tag gives the router nothing to filter on.

## Decision

**Adapter selection rides the existing capability vocabulary. There is no free-form tag channel,
and adding one is a decision this record rejects rather than an omission.**

1. **Adapters declare and are measured on namespaced capability specializations.** A manifest's
   `declared_capabilities[]` are vocabulary terms — `content.fact_check`, `coding.python`,
   `user.house_voice` — validated against the vocabulary, with a bare reserved root refused.
   Personal dimensions use `user.*`, which exists for exactly this pairing: a house-voice LoRA
   scored by a calibrated house-voice goal.
2. **Routed selection is ordinary scoring.** Adapter subjects enter LoadCoach's candidate pool
   beside bare subjects and go through the same filter → score → rank → select. A task profile
   weighting `content.fact_check` ranks the fact-check adapter above the bare base *because the
   measurements say so*. No new selection mechanism exists, and none is needed.
3. **The gate is one hard constraint.** `require_adapter_evidence`, default **on**: an adapter
   subject with no measured evidence for the profile's top-weighted capability is filtered with a
   named rejection (`adapter_unmeasured`), visible in the explanation like every other rejection.
   "No benchmark, no use" is therefore arithmetic plus one constraint, not a policy anyone has to
   remember. Turning it off is an operator's configuration change, recorded on every decision made
   under it, and the resulting selection carries the existing `low_evidence` flag.
4. **Pinned selection uses `model`-override semantics, unchanged.** A caller may name an adapter —
   IdeaPress's per-stage pins, a PromptCadence trajectory option. A pin bypasses *scoring*; it does
   not bypass **hard constraints**: digest compatibility, classification, and the evidence gate all
   still apply, and the pin is recorded as an override in the explanation.
5. **The caller supplies intent, never content.** [ADR-0040](0040-routing-backend-owns-model-choice.md)
   is unchanged: intent arrives as a task profile, and callers always know their intent — an
   IdeaPress stage, a PromptCadence step's `purpose` mapped into its `ExecutionIntent`. The adapter
   choice *within* the profile is LoadCoach's, which is why PromptCadence's deviation taxonomy
   needs no new field and no new category
   ([ADR-0056](0056-every-turn-executes-under-one-execution-intent.md)).

## Alternatives considered

**A free-form tag channel** — the proposal this record overturns, and the strongest alternative
here. Its case is genuine and worth stating at full strength: tags work the instant an adapter is
dropped, with no benchmark, no suite and no waiting; they express intent a capability term cannot
("this one is tuned for our ticket format"); and they are what the ecosystem does, so an operator
arriving from anywhere else expects them. The cost of refusing them is real and is paid by the
first adapter a user trains, for which no matching benchmark suite may exist.

It is rejected because a tag is a second vocabulary with three properties the first one does not
have: it is unversioned, so its meaning drifts silently; it has no evidence linkage, so nothing it
asserts can be checked, decayed or compared; and it has no arithmetic, so selection over tags must
be a parallel code path inside the router that bypasses scoring entirely. That last consequence is
the decisive one. Two selection paths means the explanation has two shapes, `require_adapter_evidence`
can only gate one of them, and the honest answer to "why this adapter?" becomes "because someone
typed that word on both ends" — in the component whose entire product claim is that it can explain
its choice. The friction the refusal creates is answered in the open, by rule 3's off switch and by
rule 4's pins, rather than by a channel that routes around the measurement.

**A separate adapter-selection surface in LoadCoach** — adapter profiles keyed on adapter metadata,
sitting beside task profiles. Rejected for the same reason at one remove: it is the second router
again, with better manners. Every adjustment factor (residency, reliability, cost) would need
teaching twice, and the two would drift.

**Pins only; no routed selection at all.** Genuinely attractive, and it is what the arc's own
motivating demo uses — IdeaPress pinning three adapters across three stages. It needs no evidence,
no gate and no scoring changes, and it would ship at LA2 with LA3 deleted. Rejected as the *only*
mechanism because it returns model choice to the caller, which is exactly what
[ADR-0040](0040-routing-backend-owns-model-choice.md) took away from IdeaPress three weeks ago and
for the same reasons; and because it makes FreeWeight's contribution to this arc inert — evidence
could never change which adapter is used, so LA3's proof (an imported bundle visibly flipping a
profile's selected subject) would have nothing to demonstrate. Pins remain, as an override with the
hard constraints intact, which is what an override should be.

**Infer the adapter from the request's content** — classify the prompt, pick the specialist.
Rejected twice over: LoadCoach never reads content, and a model deciding control flow is banned
suite-wide. The caller knows its own intent, which is cheaper and honest.

**Ship `require_adapter_evidence` defaulting to off**, so adapters are usable on arrival and
operators opt into rigour. Rejected: a default-off gate is a claim nobody keeps, and the failure it
permits — an unmeasured adapter selected because its name matched a weighting — is the specific
failure [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) exists to prevent. The
default is on; the switch is visible; the reason it was thrown is on every decision made under it.

## Consequences

* LoadCoach's routing gains adapter subjects in its candidate pool and three rejection reasons
  (`adapter_incompatible`, `adapter_unmeasured`, `excluded_by_policy` for remote + adapter). It
  gains **no** new selection algorithm — the scoring code is untouched, which is what makes this
  affordable inside a 1.0 application.
* An adapter is unusable through routed selection until it is benchmarked. That is the intended
  cost, and it is what makes the routed path trustworthy; the pinned path and the gate's off switch
  are the two honest ways around it, both recorded per decision.
* Declaring a capability specialization on a manifest is now a claim under test rather than a
  label: FreeWeight benchmarks exactly the declared capabilities plus the regression panel
  ([ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md)), so a manifest that
  overclaims is caught by its own evidence.
* The vocabulary absorbs the load without a version bump: `content.fact_check` and `user.*` are
  already legal under the specialization rule, so no root is added and nothing in SetSpec changes
  for selection's sake.
* Because there is no tag channel, a deployment whose adapters really are organized by kind
  ("ticket format", "legal") has to express that as a specialization under a generic root, or as a
  `user.*` goal with a calibrated benchmark. Where neither fits, the revisit trigger is the
  intended route — not a tag added quietly.

## Revisit when

A selection need appears that the vocabulary's specialization rule genuinely cannot express — one
where no generic root is a plausible parent and no `user.*` goal can be calibrated against it. The
replacement decision must then say how the new channel acquires evidence, how the evidence gate
filters on it, and how one explanation covers both paths; a channel that cannot answer those three
is this alternative returning under a new name.
