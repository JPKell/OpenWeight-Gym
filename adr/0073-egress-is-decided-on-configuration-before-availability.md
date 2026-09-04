# ADR-0073 — Egress is decided on a tier's configuration, before its availability

**Status:** Accepted (2026-09-04)
**Extends, additively:** [ADR-0054](0054-commissioner-records-the-caller-enforces.md) (Commissioner
renders and records a verdict; enforcing it is the caller's). Nothing in ADR-0054 changes; this
record answers the question it left open — *when* the caller asks, relative to everything else it
must ask before a turn runs.
**Relates to:** [ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md) (an
undeclared ceiling is never assumed public), [ADR-0043](0043-grounding-is-verified-not-assumed.md)
(the principle contract 4 applies to egress), [ADR-0048](0048-the-bypass-removes-planning-never-governance.md)
(governance is not conditional on planning mode),
[ADR-0016](0016-unavailable-is-not-zero.md) and [ADR-0030](0030-model-cost-and-pricing.md)
(unpriced egress is refused, not free), [ADR-0047](0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md)
§2–3 (a tier is configuration; a remote tier must name a pricing source).
**Source:** PromptCadence Phase 6 (row F2) handoff §9, and the operator's decision on it.

## Context

[PromptCadence spec §20](../apps/promptcadence/spec.md) criteria 4 and 5 are not statements about
*what* a governed application refuses. They are statements about **when**:

> 4. A trajectory declared `confidential` can never reach a remote tier: the attempt is refused
>    **before any HTTP request leaves**, and the refusal is a queryable `EgressDecision`.
> 5. A remote tier with no pricing record refuses with `UNPRICED_EGRESS_REFUSED` **before any call**.

A refusal that arrives after the request has gone produces an identical halted trajectory, an
identical error code and an identical row. Only the ordering separates the two, which means the
ordering is the guarantee and not an implementation detail — and a guarantee nobody wrote down is
one the next refactor is free to reverse.

Phase 6 found this the hard way. A turn's pre-flights had grown up in the order the phases arrived:
Phase 3 resolved the tier (which checked availability), Phase 5 added the budget pre-flight, and
Phase 6 was to add the egress evaluation. Written in that order, **criterion 4 was literally
unreachable.** `TierPolicy.availability` reports `loadcoach_has_no_remote_provider` for every remote
tier until LC-E1 registers one, so a `confidential` trajectory aimed at a remote tier halted with
`TIER_UNAVAILABLE` before any egress evaluation ran. No request left — the criterion's visible half
held — but the refusal was not an `EgressDecision`, and the reason given was about the deployment
rather than about the data.

The deeper problem is what happens next. The moment LC-E1 registers a remote provider, the
availability check passes, the egress evaluation finally runs, and *the same trajectory is refused
for a different reason and produces a different record*. The governance answer would have changed
because infrastructure changed, while the policy, the configuration and the data all stayed the
same. That is the class of accident these criteria exist to rule out.

Two facts about a tier make the resolution obvious once separated:

* **A tier's egress class is a property of its configuration.** `remote` and
  `max_data_classification` are written in `[tiers.<name>]` and are true of the tier whether or not
  anything can serve it today.
* **A tier's availability is a property of the deployment.** It is a question about what LoadCoach
  has registered right now, and its answer changes without any configuration changing.

Governance decided on the second is governance that varies with the weather.

## Decision

**A turn's pre-flights run in a fixed order — egress, then pricing, then availability, then budget
— and all of them complete before the turn is announced and therefore before any request is built.
The egress decision is rendered against the tier as *configured*, and is never gated on whether
that tier can serve.**

### 1. The order, and why each position is where it is

1. **Egress.** First, because it is the only unconditional one. A trajectory that may not use a
   tier may not use it whatever the price, the availability or the remaining balance. Deciding it
   first is also what makes the recorded reason stable: it cannot depend on which later check
   happened to fire.
2. **Pricing.** Unpriced egress is refused rather than treated as free (ADR-0016, ADR-0030), and a
   ceiling cannot bind what cannot be priced — so this necessarily precedes the budget.
3. **Availability.** The deployment's answer, asked only once policy has already permitted the
   tier.
4. **Budget.** The numbers last. Parking a trajectory for a day edge, or halting it on a ceiling,
   when it should never have been allowed to reach that tier at all, is the wrong answer written
   durably.

### 2. Resolving a tier and checking that it can serve are separate operations

The router exposes them separately: one operation returns the intent's approved tier as configured
(failing only when the tier is not configured at all), and another refuses a tier that cannot serve
now. A combined "resolve" that does both is retained only for callers that render no egress
decision of their own — reconciliation re-reading a turn that already ran.

This split is the mechanism; ADR-0054 is the reason it is safe. Commissioner renders and records
the verdict without knowing anything about tiers, availability or turns, so the *order* of the
caller's questions is entirely the caller's to arrange, and arranging it is not a policy change.

### 3. Every turn is evaluated, including a local one

A local tier is approved with `target_not_remote` and the approval is recorded, rather than the
evaluation being skipped. Governance invariance ([spec §11](../apps/promptcadence/spec.md)
contract 1, ADR-0048) is meant to be *checkable*, and "every turn carries an egress decision" stops
being checkable by counting the moment some turns are exempt. It is also what lets the record answer
"where did this trajectory's data go" rather than only "when was something refused".

### 4. A refusal at any position is a recorded outcome, not an exception

An egress denial ends the turn with a structured refusal carrying the policy's own reason
(`EGRESS_DENIED`), never an exception reaching a caller as `INTERNAL_ERROR`
([spec §13](../apps/promptcadence/spec.md)). The same holds for the pricing refusal
(`UNPRICED_EGRESS_REFUSED`) and the availability one (`TIER_UNAVAILABLE`).

## Consequences

* **Criteria 4 and 5 become properties of the code's shape** rather than of a test that happens to
  check them. A test still asserts against the injected HTTP client that nothing was sent, because
  that is the only witness distinguishing a refusal before the call from one after it — but the
  assertion is now confirming a structural fact instead of standing in for one.
* **The recorded reason is stable across deployments.** A `confidential` trajectory aimed at a
  remote tier is refused with `classification_exceeds_ceiling` today, on a host with no remote
  provider, and with exactly the same reason once LC-E1 registers one. Nothing about the record
  changes when infrastructure does.
* **A remote tier that cannot serve still produces the governance answer first.** An operator who
  misconfigures a `confidential` trajectory onto a remote tier learns that the classification
  forbids it, not that LoadCoach has no remote provider — the second being true, unhelpful, and
  temporary.
* **Adding a pre-flight is now a decision with a stated position**, not an append. A future check —
  a residency rule, a rate limit, a quota — has to say where in this order it belongs and why.
* **The cost is one more evaluation per turn**, including on the local path where the answer is
  always `target_not_remote`, plus one row. That is accepted deliberately: it is the price of the
  invariance being countable, and an egress decision is a small row on a table built for them.
* **This is a rule about ordering, not about policy.** It adds no classification level, no verdict
  and no configuration key. A build that reordered these checks would still pass every unit test of
  the policy itself, which is the argument for recording it here rather than only in a docstring.
