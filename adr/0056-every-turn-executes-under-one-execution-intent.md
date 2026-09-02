# ADR-0056 — Every turn executes under exactly one immutable ExecutionIntent

**Status:** Accepted (2026-09-02)
**Extends:** [PromptCadence Lifecycle §4.3 and §5](../apps/promptcadence/lifecycle.md),
[PromptCadence Spec §11](../apps/promptcadence/spec.md) (contract 1).
**Relates to:** [ADR-0048](0048-the-bypass-removes-planning-never-governance.md) (the invariance
this makes structural), [ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md) (who mints),
[ADR-0044](0044-a-state-change-and-its-event-are-one-write.md) (minting commits with its event),
[ADR-0057](0057-the-explanation-is-materialized-and-the-rows-stay-authoritative.md) (every revision is in
the record).
**Source:** [PromptCadence roadmap §2, D-12](../roadmap/promptcadence-roadmap.md).

## Context

PromptCadence's central promise is that a bypassed trajectory is governed exactly as a planned one
is ([ADR-0048](0048-the-bypass-removes-planning-never-governance.md)). Its central mechanism is a
per-turn comparison: after every turn, what actually happened is checked against what was allowed.

The expansion pass wrote that comparison with **two sources**. On the planned path the allowed
thing was the approved plan step; on the bypass path it was the tier policy's defaults. Two
sources means the comparison branches on which path a trajectory took — and a comparison that
branches on the mode cannot be the evidence that the modes are governed alike. It is the claim
restated, not proved.

The plan/policy split is wrong on a second count: the granularity does not match. A plan step
*declares* — tools, tier, classification — and approval renders a verdict on the document. But
execution and deviation happen per **turn**, several turns to a step, and a verdict on a document
is not something a turn can be checked against. Nor does a redline live anywhere natural: when the
approver substitutes `local_large` for `remote_cheap`, the plan must keep the original (it is what
the model proposed) while execution must be held to the substitution. Two facts, one row.

Then there is the deviation taxonomy. Written against a plan, deviations were an open list of
things that might go wrong, and an open list has no completeness argument: policy maps a category
to a disposition, and a category nobody enumerated has no defined disposition at all.

## Decision

**Approval's output is not a verdict on a document — it is the minting of one immutable
`ExecutionIntent`. Every turn executes under exactly one intent and is checked against exactly
that intent.**

### 1. The envelope

```text
ExecutionIntent
  intent_id · trajectory_id · step_id        # step_id is the synthetic "loop" in bypass mode
  revision · supersedes                      # re-approval mints revision n+1; nothing is edited
  approved_tier + fallback_tiers             # ordered; may be empty
  approved_tools                             # frozen subset of the trajectory allowlist
  max_classification                         # <= the trajectory's declaration
  token_budget · money_budget                # the step's slice, with the estimate's source
  max_turns                                  # tool round trips this intent covers
  minted_by                                  # "policy" | approver token identity | "bypass_default"
  minted_at · approval_request_id            # the human grant, when one gated it
```

### 2. Universal — there is no path without one

The planned path mints one intent per approved step. The bypass path mints one default intent from
`TierPolicy` before its first turn (`policy.default_tier`, the trajectory allowlist, the
trajectory's own classification and budget, `execution.max_steps` as `max_turns`), recorded as
`minted_by = "bypass_default"`. Governance invariance is therefore **structural**: not a rule
implementers must remember, but the absence of a code path that could break it. Contract 1's diff
test then compares two record sets that differ only in the plan and approval rows, because every
other row was produced by the same machinery.

### 3. Immutable, revisioned, never edited

* A **redline is resolved at minting**: the intent carries the substituted tier, the plan retains
  what the model proposed. Both facts survive, in the places they belong.
* A **scoped re-approval supersedes**: revision *n+1* with `supersedes` pointing at *n*, and *n*
  retained. The audit trail holds every envelope any turn ever ran under, so "under whose grant
  did turn 7 run?" is answerable after the fact, which an edited row cannot do.
* **Every turn persists `(intent_id, revision)`.** The explanation shows which envelope each turn
  ran under and why a new revision appeared.
* Minting emits `intent.minted` **in the same write** as the transition that caused it
  ([ADR-0044](0044-a-state-change-and-its-event-are-one-write.md)).

### 4. Gates are evaluated against the most permissive tier in the set

An intent may carry fallback tiers. Approval gates — the hybrid egress gate, the per-step cost
gate — are evaluated **at minting, against the most permissive tier the intent permits**, not
against its first choice. Without this rule a pre-approved fallback is a smuggling route: a step
approved for `local_fast` with `remote_frontier` in its fallbacks would pass an egress gate that
only looked at the primary, and then escalate past it silently.

### 5. The taxonomy is closed by construction

`DeviationHandler` is a pure function `compare(turn_facts, intent) -> deviations` — one source, no
branching on mode. There is **exactly one deviation category per intent field it can contradict**,
plus one for a promise contradicted after the fact (`tier_violation`, when the response's
execution subject is outside the intent entirely). Creating a new category therefore requires
adding a field to the intent, which is a new governance dimension and a new ADR — see *Revisit
when*. Severity is not configurable: a contradicted promise is a `violation` and halts; an
uncovered want is a `drift` and follows `reapproval_scope`.

## Alternatives considered

**Compare against the plan step, with the bypass path comparing against policy defaults.** The
status quo of the expansion pass, and it needs no new table. Rejected because it makes the
comparison branch on the very distinction the design exists to erase: contract 1 would be proved
by a test over code that already knows which mode it is in. The two-source version also has
nowhere to put a redline that both preserves the proposal and binds the execution.

**Synthesize a pseudo-plan for bypassed trajectories**, so there is one source without a new
object. Genuinely close, and it was the cheaper fix. Rejected because the record would then
contain a plan for a trajectory that was never planned, and contract 1's diff test would have to
*exclude* those synthetic rows — weakening exactly the proof it exists to give. An intent minted
`bypass_default` says what actually happened; a synthetic plan says something that did not.

**Let the intent be mutable — edit it on re-approval.** One row per step, simpler queries, no
revision chain. Rejected: turns that already ran would retroactively appear to have run under an
envelope that did not exist when they ran, and an approver's grant would be silently rewritten by
a later one. In a record whose purpose is to answer "who allowed this, and when", an in-place edit
is a lie with good ergonomics.

**Mint an intent per turn rather than per step.** Finer granularity, and it removes `max_turns`
entirely. Rejected on the human cost: in hybrid mode a per-turn intent is an approval prompt per
tool round trip, which turns the gate into noise operators will disable. `max_turns` is the
deliberate bound — one grant covers a bounded number of turns, and exceeding it is itself a
deviation (`turn_overrun`) rather than a silent continuation.

**Keep an open deviation taxonomy** with free-form reasons, so unforeseen deviations can still be
recorded. Rejected: an open taxonomy has no completeness argument, and policy must map every
category to a disposition — so an unmapped category has no defined behaviour at exactly the moment
something unforeseen is happening. Closure is bought honestly here: the price is that a genuinely
new kind of deviation cannot be recorded until the intent gains a field, and that price is the
revisit trigger rather than a loophole.

## Consequences

* PromptCadence owns an `execution_intents` table that is append-only in practice: one row per
  revision, none ever updated. A long trajectory with several re-approvals keeps every envelope,
  and the explanation renders the chain.
* The deviation matrix in [Lifecycle §5](../apps/promptcadence/lifecycle.md) is now derivable from
  the intent's field list, and the unit tests walk the full category × severity × scope matrix
  because the matrix is finite by construction.
* Approval in all three modes, the bypass default, and scoped re-approval become one operation
  with one output. `PlanApprover` is deterministic given tier policy, ledger headroom and egress
  policy, and its output is data — which is what makes the whole approval path golden-testable.
* **A cost:** one more object between plan and execution, and every reader of the record must
  understand three things (what was proposed, what was approved, what ran) rather than two. The
  explanation is expected to carry that weight, and P8's UI work is where it is proved readable.
* Rule 4 makes fallbacks slightly harder to get approved than a naive implementation would — a
  step with a remote fallback is gated as though it were remote. That is the intended trade: a
  fallback that never fires still had to be permitted.

## Revisit when

An intent needs a field that no plan and no policy supplies. That is a new governance dimension —
a thing the suite has started to govern that it did not govern before — and it arrives with its
own deviation category, its own disposition rules and its own ADR. It is never a schema tweak,
because the taxonomy's closure is a function of the field list.
