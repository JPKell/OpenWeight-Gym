# ADR-0090 — A compaction summary runs under a superseding revision of the step's own intent

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Lifecycle §7](../apps/promptcadence/lifecycle.md) — which envelope the
summarization call executes under, not whether it executes.
**Relates to:** [ADR-0047](0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md) (a tier names
exactly one task profile), [ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md) (a supersession is a
minting and is gated), [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md) rule 4 (gates evaluate
against the most permissive permitted tier), [ADR-0091](0091-a-compaction-turn-is-debited-and-does-not-spend-the-steps-advance.md)
(the other half of the same turn).
**Source:** Row I1, decision D1.

## Context

Lifecycle §7 says the compaction summary executes "via LoadCoach (`general.summarize`, on the
trajectory's cheapest admissible *local* tier — a summary of confidential turns must not itself
become egress)", and that the call "is itself a turn — debited, recorded, explainable". Three
built facts pull against that sentence at once:

* A PromptCadence tier is configuration over **one** LoadCoach task profile (ADR-0047).
  `general.summarize` is a shipped LoadCoach profile, but no configured tier names it — the two
  default tiers name `tools.agent.local_fast` and `tools.agent.local_large`. "On tier X with
  profile `general.summarize`" is a combination the tier model cannot express.
* Spec §11 contract 1 says no turn executes without an immutable `ExecutionIntent` to be checked
  against, and `compare`'s `tier_violation` fires when the executed tier is not in
  `intent.permitted_tiers`. A summary run on a summarizing tier inside a step whose intent permits
  another tier **is a deviation** unless something says otherwise first.
* The four pre-flights (egress, pricing, availability, budget — [ADR-0073](0073-egress-is-decided-on-configuration-before-availability.md))
  run before `turn.started`. The summary is a turn, so it has its own.

## Decision

**The compaction summary executes under a superseding revision of the step's own
`ExecutionIntent`, and the step's envelope is restored by a further supersession when the summary
is done.**

1. **The tier stays a tier.** The summarizing tier is an ordinary configured tier — the cheapest
   admissible **local** one among those the trajectory's tier snapshot holds, ordered by
   `context_budget_tokens` then name, and filtered to those whose
   `max_data_classification` admits the step's ceiling. ADR-0047 is untouched: nothing names a
   task profile that no tier declares, and a deployment that wants a dedicated
   `general.summarize` tier configures one and it wins the ordering on its own merits.
2. **The envelope narrows, it never widens.** The superseding revision names the summarizing tier
   as `approved_tier`, **no fallbacks**, and `approved_tools = ∅` — a summary calls no tools. It
   carries the step's `max_classification` unchanged, which is what makes "a summary of
   confidential turns must not itself become egress" a property of the envelope rather than of
   the code path: a remote tier could not be selected in step 1, and a remote answer on this
   revision is the same `tier_violation` it would be on any other.
3. **Restoration is itself a revision.** When the summarization finishes — succeeded, failed, or
   refused — a second supersession restores the step's `approved_tier`, `fallback_tiers` and
   `approved_tools`. The step's own turns therefore never run under the summary's envelope, and
   the record holds both moves rather than one unexplained change.
4. **Both mintings are `policy` mintings.** `MintKind` stays the closed vocabulary it is
   (`policy`, `approver`, `bypass_default`): the compaction policy chose this, no person did, and
   a fourth kind would be a vocabulary widened to describe an authority that already has a name.
   Each supersession emits `intent.minted` in the write that persists it (ADR-0044), and the gates
   re-fire per ADR-0049 rule 3.
5. **The assertion comes first.** No path executes a summary turn under no intent, and no summary
   turn executes outside the envelope of the trajectory it is summarizing. Both are tested
   directly, not inferred from the absence of a deviation.

## Alternatives considered

**(a) Run the summary on the step's own tier and let the tier's profile stand.** Cheapest to
build — no revision, no restoration, no new selection rule. Rejected because it silently discards
the property the sentence exists for: on a trajectory whose step runs remote, the summary of a
confidential transcript becomes egress, and nothing in the record would say that a decision had
been made. It would also charge the summary against a profile chosen for agentic tool use.

**(c) Widen `permitted_tiers` at mint time to include the summarizing tier.** One line. Rejected
because it weakens **every** step's envelope, permanently, for a turn that may never happen: after
it, a step's ordinary turn answered on the summarizing tier is no longer a `tier_violation`, and
the widening is invisible in a diff of one revision against the next. A grant that covers a turn
nobody has yet needed is exactly the standing permission the intent model exists to refuse.

**A separate synthetic step with its own revision-1 intent** (`compaction:<id>`). Genuinely clean,
and rejected for two reasons: it puts a step id in `execution_intents` that no plan declared and
no `plan_steps` row backs, which every reader of the plan surface then has to special-case; and it
detaches the summary from the step whose budget, ceiling and classification actually govern it,
which is the opposite of what the audit trail needs. Superseding keeps the summary inside the
governance record it belongs to.

## Consequences

* Two extra `execution_intents` rows and two `intent.minted` events per compaction that summarizes.
  A trajectory that compacts by masking or dropping alone mints nothing — the revisions exist only
  where a model call does.
* `GET /trajectories/{id}/intents` now shows narrow-then-restore pairs, and the explanation renders
  them with the compaction they belong to. A reader who sees only the narrowing has seen a
  truncated record, which is the same thing they would see for any crash mid-step.
* A trajectory with **no** admissible local tier cannot summarize. That is a `COMPACTION_FAILED`
  naming the missing tier, not a silent fall back to a remote one.
* The step's `max_turns` is untouched by this record; see
  [ADR-0091](0091-a-compaction-turn-is-debited-and-does-not-spend-the-steps-advance.md).

## Revisit when

A tier can name more than one task profile, or LoadCoach gains a way to ask one profile for a
one-off call outside a tier. Either makes rule 1's ordering unnecessary rather than wrong.
