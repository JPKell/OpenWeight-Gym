# ADR-0047 — A tier is configuration over a task profile, and a model's guess never sizes its own budget

**Status:** Accepted (2026-09-02)
**Extends:** [PromptCadence Spec §12](../apps/promptcadence/spec.md) (configuration),
[PromptCadence Lifecycle §3 and §6](../apps/promptcadence/lifecycle.md).
**Relates to:** [ADR-0040](0040-routing-backend-owns-model-choice.md) (a routing backend owns model
choice), [ADR-0030](0030-model-cost-and-pricing.md) (cost is derived, and a local model's cost is
`UNSUPPORTED`), [ADR-0016](0016-unavailable-is-not-zero.md), [ADR-0023](0023-runtime-profile-resolution.md)
(the served-context labelling idiom this copies), [ADR-0039](0039-audit-gated-blocking-requirements.md)
(a model's own output must not settle a gate).
**Source:** [PromptCadence roadmap §2, D-3](../roadmap/promptcadence-roadmap.md).

## Context

A tier is PromptCadence's unit of governance: `local_fast`, `remote_cheap`, `remote_frontier`. A
step is approved for a tier, an egress verdict is rendered against a tier's ceiling, a budget slice
is drawn against a tier's prices. So a tier has to be a precise object — and the question is
whether it is a *set of models* PromptCadence picks from, or a *name for an intent* it hands to
something that picks.

The suite settled the general form of that question three weeks ago.
[ADR-0040](0040-routing-backend-owns-model-choice.md) took per-stage model pinning away from
IdeaPress because a caller that names models bypasses the routing backend's profiles, evidence and
admission control while every request still succeeds. A harness that names models inside a tier
would repeat that, with a second copy of scoring code that drifts from the first.

The budget side has a sharper problem. The planner drafts a plan by calling a model, and the
obvious way to size each step's budget is to ask that same call for an estimate — the plan already
has a slot-shaped hole where `estimated_cost` would go. That would let a number the model invented
size the ceiling that constrains the model. The suite has met this shape before: a model's silence
settling a blocking gate ([ADR-0039](0039-audit-gated-blocking-requirements.md)), and a check built
out of its own requirement's words ([ADR-0042](0042-a-check-may-not-restate-its-requirement.md)).
It is the same defect — the thing being constrained supplying the constraint.

And money alone cannot do the job. [ADR-0030](0030-model-cost-and-pricing.md) makes a local
model's cost `UNSUPPORTED`, never `$0.00`, so a money ceiling does not bind local execution at all;
a trajectory could run forever on a local tier under a $5 cap and never approach it.

## Decision

**A tier is configuration over exactly one LoadCoach task profile. PromptCadence performs no
routing math. Step estimates are labelled by source, and a model-generated number is never one of
those sources.**

### 1. What a tier is

```text
tier = name                       # operator-chosen
     + task_profile               # exactly one LoadCoach task profile
     + remote (bool)              # the egress class
     + max_data_classification    # required when remote
     + context_budget_tokens      # the compaction trigger's input
     + pricing source             # required when remote
```

*Which model within the tier* stays LoadCoach's filter → score → rank → select, driven by the
profile. The shipped profiles (`tools.plan`, `tools.agent.local_fast`, `…local_large`,
`…remote_cheap`, `…remote_frontier`) are namespaced specializations of `tools.agent` shipped as
**LoadCoach configuration, not code**. Tier suitability therefore improves when FreeWeight's
evidence improves, with no PromptCadence change.

### 2. The taxonomy is not fixed; the invariants are

Tier names and count are operator configuration — four shipped defaults, not a closed set. What is
enforced in code, at startup, with a refusal rather than a warning: a remote tier without
`max_data_classification`; a remote tier without a pricing source; an unknown classification value;
a tier naming no task profile. `promptcadence doctor` and `promptcadence tiers check` additionally
verify that each configured tier's task profile exists in the running LoadCoach.

### 3. Two ceilings, because one cannot bind

* **Token ceilings bind every turn on every tier** — the universal brake, and the only one that
  governs local execution.
* **Money ceilings bind priced usage.** A remote tier must name a pricing source — `ModelPricing`
  records with provenance — and a configuration that omits one is refused at startup (§2 above). A
  remote step whose selected model has no pricing record in that source is refused at approval
  time with `UNPRICED_EGRESS_REFUSED`, before any call. **Unpriced egress is refused, not free** —
  a ceiling cannot bind what cannot be priced, and treating it as free is exactly the fabricated
  zero [ADR-0016](0016-unavailable-is-not-zero.md) forbids.

### 4. Estimates are layered, and their source is recorded

```text
estimate = p80 of observed cost for (tier, task_profile)   when >= estimate_min_samples exist
                                                           -> source "historical"
           configured per-tier default                     otherwise
                                                           -> source "configured_default"
```

The estimate, its source and the sample count behind it appear in the approval record, mirroring
the suite's served-context labelling (ADR-0023): a number is never presented without saying where
it came from. `PlanApprover` approves a plan only if the sum of step estimates fits the remaining
ceilings. **A model-generated cost guess is never an estimator input.**

## Alternatives considered

**Let PromptCadence choose the model inside a tier**, from a configured candidate list. It removes
a network hop from the decision and makes tiers self-contained. Rejected: it is
[ADR-0040](0040-routing-backend-owns-model-choice.md)'s defect with a new caller — a second scorer
that cannot see evidence, reliability, residency or admission state, silently diverging from the
one that can. A model list also goes stale while a task profile gets better on its own.

**Fix the tier taxonomy in code** — four members, an enum, exhaustively tested. Genuinely
attractive: fixed names make the UI, the documentation and the policy language simpler, and a
closed set can be tested completely. Rejected because tier *meaning* is deployment-specific — one
operator's `remote_cheap` is another's forbidden — and because the properties that actually need
guarding (remote implies a ceiling, remote implies pricing) are enforceable without fixing names.
The four defaults ship as configuration so an operator can delete one, which an enum would not
allow. The revisit trigger below is the honest reopening.

**Define a tier as a set of models rather than a task profile.** Rejected for the same reason as
the first alternative, plus one more: a task profile carries hard constraints and capability
weights that evidence updates, and a model set carries nothing that improves.

**A single money ceiling.** The ceiling every user expects — "stop at $5" — and the only one a
hosted harness needs. Rejected because in this suite it does not bind:
[ADR-0030](0030-model-cost-and-pricing.md) makes a local model's cost `UNSUPPORTED`, never `$0.00`,
so a trajectory on a local tier under a $5 cap runs until the disk fills and never approaches it. A
money-only ceiling is a ceiling on the expensive tiers and no ceiling at all on the default one.

**A single token ceiling.** Universal, provider-independent, and it binds local execution. Rejected
because tokens do not bound spend: the same ten thousand tokens cost nothing on `local_fast` and
real money on `remote_frontier`, so a token ceiling tight enough to cap remote spend strands local
work, and one loose enough for local work leaves remote spend uncapped. Two ceilings with two scopes
is the smallest rule that binds everywhere, and ADR-0030's derivation makes the money figure
available whenever a price is.

**Ask the planner for a cost estimate per step.** Cheap, obvious, and the plan is right there.
Rejected: a number the model invented would size the budget that constrains the model. This is
[ADR-0039](0039-audit-gated-blocking-requirements.md)'s and
[ADR-0042](0042-a-check-may-not-restate-its-requirement.md)'s shape exactly — the thing under
constraint supplying its own constraint — and it fails in the flattering direction, because an
optimistic estimate is what gets a plan approved.

**One configured default per tier, with no history at all.** Simpler, no sample threshold, no
estimator version to record. Rejected: a static default is either loose enough never to bind or
tight enough to block real work, and it never improves. The layered form is barely more code and it
gets better with use, which is the same bet the routing evidence makes.

**Use the mean of observed cost rather than the p80.** Unbiased, and easier to explain. Rejected on
the asymmetry: under-estimating halts a trajectory in the middle of work a user is waiting on,
over-estimating costs a little headroom. p80 puts the error on the cheap side deliberately, and the
20-sample minimum matches the suite's existing threshold for treating a statistic as meaningful.

## Consequences

* PromptCadence contains no scoring code, no candidate ranking and no residency arithmetic. Its
  routing surface is a string — the task profile name — and its own tests never need a model.
* Adding a tier is a configuration edit plus a LoadCoach task profile; adding a *kind* of tier
  invariant is a code change. That asymmetry is deliberate.
* Every approval record carries per-step estimates with their sources, so "why was this plan
  approved for $2.40?" is answerable from the record, and a wrong estimate is diagnosable as
  historical-with-n-samples or as a configured default nobody tuned.
* Local tiers can exhaust a token ceiling and never touch a money ceiling; the UI must show `—`
  rather than `$0.00` for their spend, per ADR-0030 and ADR-0016.
* Remote tiers are unusable until an operator supplies pricing — which will read as friction, and
  is the intended reading: a remote call whose cost cannot be computed is a call that cannot be
  budgeted.
* The estimator has a version, recorded on every trajectory, so changing the rule does not silently
  reinterpret old approval records.

## Revisit when

* **Tier count or shape proves per-organization-variable beyond what configuration can express** —
  for example if tiers need composition, inheritance or per-caller overrides. That is a policy
  language, and it needs its own record rather than more TOML.
* **FreeWeight ships a `native.plan` benchmark category**, at which point `tools.plan` acquires
  measured evidence and the planner's own routing stops being a declared-capability guess.
