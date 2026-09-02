# ADR-0048 — The bypass removes planning; it never removes governance

**Status:** Accepted (2026-09-02)
**Extends:** [PromptCadence Spec §1 and §11](../apps/promptcadence/spec.md) (contract 1),
[PromptCadence Lifecycle §1](../apps/promptcadence/lifecycle.md).
**Relates to:** [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md) (the mechanism
that makes this structural), [ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md) (gates fire
in bypass mode too), risk A8 (a documented invariant with no mechanism behind it).
**Source:** [PromptCadence roadmap §2, D-4](../roadmap/promptcadence-roadmap.md).

## Context

PromptCadence's planned path costs a whole model call before step one: the planner drafts a
structured plan, PromptCadence validates it, and the approver renders a verdict on every step. On a
one-step task that round trip is the dominant cost and produces a plan with one step in it. Worse,
the arc's top product risk is that local models draft unusable plans — so the planned path can be
both slower *and* worse for simple work, which is exactly the work a harness should feel best at.

Hence the bypass: `planning.enabled = false`, or `bypass_planning` per request. And hence the
danger. "Bypass" is a word that grows: the first thing anyone asks of a fast mode is that it also
skip the ledger write, the egress row and the deviation check, because each of those is overhead
and none of them is what the user came for. Every one of those requests is individually reasonable
and collectively fatal — a governance record that is optional is absent precisely when someone is
in a hurry, which is when it matters most.

The distinction has to be stated once, precisely, and mechanized, or it erodes during
implementation. Risk A8 names this exact failure class: a documented invariant with no mechanism
behind it.

## Decision

**The bypass removes the up-front planning-and-approval round trip. It removes nothing else.**

### Removed by the bypass

* The planner's model call and the plan it produces.
* The policy pass over that plan document, and the `plans` / `plan_steps` / `plan_approvals` rows.

### Not removed, in any mode, ever

* **Tier resolution.** Every turn runs on a resolved tier; the bypass path starts at
  `policy.default_tier`.
* **Data classification.** The trajectory's declaration binds every turn.
* **Budget.** Pre-flight `would_exceed`, per-turn debits, and ceiling evaluation.
* **Egress.** A `SpotCheck` evaluation per turn, recorded whether it approves or denies.
* **Approval gates.** Hybrid gates fire in bypass mode too — at the minting of the default
  intent, and at every re-mint a turn's drift triggers
  ([ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md) rule 3,
  [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md) rule 4). Bypass removes
  planning, never approval of gated egress.
* **The deviation comparison**, against the turn's `ExecutionIntent`.
* **The audit trail** — turns, tool calls, ledger entries, egress decisions, events, the
  explanation.

### It is structural, not procedural

The bypass path mints a default `ExecutionIntent` from `TierPolicy` before its first turn
([ADR-0056](0056-every-turn-executes-under-one-execution-intent.md)), so **there is no code path
that executes a turn without an intent to check it against**. The invariance is a property of the
code's shape rather than a rule implementers must remember.

### It is proved, not asserted

Contract 1 is a **diff test**: the same scripted task run planned and bypassed produces record sets
identical in shape except for the plan and plan-approval rows. It runs in CI, it is a release gate,
and it fails loudly if a governance write ever becomes conditional on the mode.

## Alternatives considered

**A genuinely fast mode that skips per-turn governance too.** The alternative users will actually
ask for, and its case is not silly: for a trivial local task, an egress row, a ledger write and a
deviation comparison per turn are pure overhead, and no comparable harness charges them. Rejected
on the arithmetic and on the consequence. The arithmetic: the expensive thing is the *planning
model call*, measured in seconds; PromptCadence's whole per-turn governance overhead is budgeted at
≤ 25 ms beside a multi-second generation, so skipping it buys approximately nothing. The
consequence: a record that exists only when someone opted into it answers "what left this machine?"
with "the parts we were not in a hurry for", which is not an answer.

**Make governance opt-in per trajectory** rather than always-on. The same alternative inverted, and
it fails the same way — with the added property that the default would eventually be flipped for
convenience by an operator who does not read this record.

**Ship two applications: a governed harness and a fast one.** Honest about the trade-off and it
keeps each codebase simple. Rejected: two loops means two implementations of tool execution,
transcripts and recovery, and the fast one becomes the one people use — the ungoverned path
[ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) refuses at the import level,
returning at the product level.

**Remove the bypass entirely; always plan.** Genuinely arguable, and it makes this whole ADR
unnecessary: one path, nothing to keep invariant, contract 1 deleted. Rejected because it forces a
model call and a policy pass onto work that has one step, and because the arc's own top risk says
local planners are the weak link — mandatory planning would make the product worst exactly where it
should be best. The bypass is the design's honesty about when planning pays for itself.

**Prove invariance by review and documentation** instead of a diff test. Rejected by name: this is
risk A8, the class the final architecture audit found repeatedly — ageing with no sweep, a lease
with no keeper. "The specification says so" is not an implementation.

## Consequences

* Every governance write in PromptCadence is unconditional on the planning mode. A code review that
  finds `if planned:` around a ledger debit, an egress evaluation or a deviation check has found a
  defect, and the diff test should already have failed.
* The bypass is genuinely faster in the only way that matters: it removes a model call, not a
  record. Users get the speed they asked for and the trail they did not ask for.
* Contract 1's diff test constrains implementation order — the bypass loop (P3) exists before the
  planner (P7), so the invariant is established on the simpler path and the planner has to fit it.
* A bypassed trajectory in hybrid mode can still pause for a human, which will surprise someone.
  It is intended: the gate is about egress and cost, and neither is a property of how the work was
  planned.
* PromptCadence's overhead budget (≤ 25 ms/turn) is now load-bearing rather than aspirational — it
  is the number that makes "skip governance for speed" unattractive, so it is measured in P9 and
  regressions fail the nightly performance job.

## Revisit when

**Never, as a weakening.** This record names no trigger that relaxes the rule, and that is
deliberate: every erosion of it arrives as a locally reasonable request, so the answer has to be
decided once rather than case by case. Reopening it is not an amendment — it is a different
product, and it takes a new ADR that supersedes this one, states what the audit trail is now for,
and re-answers PromptCadence's reason to exist. What *may* change without touching this record is
what the planned path adds (templates, richer approval policy) and what the bypass path costs
(overhead measurements), because neither changes the set above.
