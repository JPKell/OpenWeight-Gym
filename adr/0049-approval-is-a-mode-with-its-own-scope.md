# ADR-0049 — Approval is a mode with its own scope, and silence never grants it

**Status:** Accepted (2026-09-02)
**Extends:** [PromptCadence Lifecycle §4.2](../apps/promptcadence/lifecycle.md),
[PromptCadence Spec §12 and §14](../apps/promptcadence/spec.md).
**Relates to:** [ADR-0039](0039-audit-gated-blocking-requirements.md) (a model's silence must not
settle a blocking gate — this is the human form of the same rule),
[ADR-0014](0014-authentication-strategy.md) (tokens and scopes),
[ADR-0056](0056-every-turn-executes-under-one-execution-intent.md) (what an approval produces),
[ADR-0048](0048-the-bypass-removes-planning-never-governance.md) (gates fire in bypass mode too).
**Source:** [PromptCadence roadmap §2, D-5](../roadmap/promptcadence-roadmap.md).

## Context

Some of what a trajectory proposes deserves a person's attention and most of it does not. Reading
files in a workspace is routine; sending internal notes to a paid remote endpoint at a dollar a
step is not. A harness that asks about everything trains its operator to click through, which is
worse than not asking — the gate that fires constantly is the gate nobody reads. A harness that
asks about nothing has no human in the loop at all.

Two further things had to be settled. **Who may approve:** PromptCadence's tokens already carry
scopes, and the natural shortcut is to let whoever may submit work also approve it — which makes
the approval a formality performed by the requester, in the component whose most sensitive act is
sending someone's data off the machine. And **what happens when nobody answers:** a pending
approval is a trajectory holding budget and a question, and the two easy answers are both wrong in
opposite directions.

The suite has already decided the shape of the second question for models.
[ADR-0039](0039-audit-gated-blocking-requirements.md) established that a gate is satisfied only by
an explicit, labelled affirmative, and that silence degrades toward "cannot judge" and pauses. The
human case is the same rule with a person on the other side of it.

## Decision

**Approval is a configured mode with a dedicated token scope. Only an explicit grant approves, and
its output is the minting of an `ExecutionIntent`.**

1. **Three modes**, `approval.mode`:
   * `auto` — the policy verdict is applied directly. Deterministic, versioned
     (`approval_policy_version` on every trajectory), no human in the path.
   * `hybrid` — auto-approve except steps matching the configured gates: egress at or above
     `gate_egress_at`, or an estimated step cost above `gate_step_cost`. A gated step pauses the
     trajectory when that step becomes ready, so ungated earlier work may already have run.
   * `manual` — every plan is held in `awaiting_approval` for a person.
2. **`approve` is its own scope**, distinct from `write`. The identity that submits work cannot
   approve its own egress. Startup refuses `mode = "manual"` with no `approve`-scoped token
   defined — a mode that nobody can satisfy is a configuration error, not a runtime surprise.
3. **Hybrid gates fire per turn in bypass mode.** Bypass removes planning, not approval of gated
   egress ([ADR-0048](0048-the-bypass-removes-planning-never-governance.md)); the gates are
   properties of what a turn is about to do, not of how the work was planned.
4. **A pending approval expires and halts.** After `approval.request_timeout_hours` (default 24)
   the trajectory halts with the timeout recorded as its cause. A timeout is never a grant, and
   never an indefinite wait.
5. **Approval's output is minting**, not a verdict on a document: an approved plan yields one
   immutable `ExecutionIntent` per step, and a scoped re-approval mints a superseding revision
   ([ADR-0056](0056-every-turn-executes-under-one-execution-intent.md)). The three modes differ
   only in who authorizes the minting, which is why they share every downstream record.
6. **Resolution is idempotent per approval request**, and a trajectory parks on exactly one pending
   request at a time.

## Alternatives considered

**A boolean — `require_approval`.** Half the configuration surface and trivially explicable.
Rejected: it forces the choice between approving everything and approving nothing, which is exactly
the choice the middle mode exists to avoid. The value of a gate is that it fires rarely enough to
be read, and only a gated mode can deliver that.

**Let the `write` scope approve.** One fewer scope, one fewer token to issue, and on a single-user
loopback deployment the distinction looks like ceremony. Rejected because it is the one separation
that matters here: the request to send data off the machine and the authorization to send it should
not be the same credential, and the cost of keeping them apart is one enum member. On a
single-operator machine the operator issues themselves both scopes and notices nothing; in the
deployment where it matters, the property exists without a migration.

**Auto-approve on timeout** — "the operator was away, and the work matters". Rejected by name: this
is [ADR-0039](0039-audit-gated-blocking-requirements.md)'s defect with a human in the model's seat.
Absence would settle a blocking gate, and it would do so in the permissive direction, on exactly
the steps that were gated because they were expensive or leaving the machine.

**Wait indefinitely instead of expiring.** Genuinely arguable, and it has a real cost on the other
side: an expired approval loses the trajectory's work, and the user has to resubmit. Rejected
because an unbounded pending approval is an operational leak — budget reserved, a question nobody
is being reminded of, and a trajectory that no health check will ever flag as stuck. Halting with
the timeout on the row is at least observable and at least honest; the mitigation is that
`request_timeout_hours` is configurable and pending approvals with their ages appear in
`GET /system/status`.

**Per-step human approval always, with no `auto` mode.** Maximum control. Rejected: an operator
approving twenty routine steps stops reading by the fourth, so the gate's protection decays to
nothing while its cost stays. `auto` is the honest default for a single-operator machine, and the
policy it applies is deterministic and versioned so it can be audited after the fact.

**Route approvals to people** — assignees, queues, per-operator inboxes. Deferred rather than
rejected on the merits: there is one operator today, and the machinery would be speculative. It is
this record's revisit trigger.

## Consequences

* PromptCadence gains an `approval_requests` table with a persisted timeout clock (a value, not
  process state, so it survives restart), a fourth token scope, and one startup refusal.
* All three modes produce the same downstream records, because all three end in a minted intent.
  The mode is visible in `minted_by` — `"policy"`, an approver's token identity, or
  `"bypass_default"` — so the record says who authorized every turn.
* A hybrid gate can pause a trajectory *mid-flight*, after earlier steps have already run and
  spent. The record shows exactly where it paused and what it had already done, and the ledger
  balance at that point is part of the approval request.
* `manual` mode on an unattended machine will time out and halt. That is the specified behaviour
  and the reason the default is `auto`.
* Because gates are evaluated at minting against the most permissive tier an intent permits
  ([ADR-0056](0056-every-turn-executes-under-one-execution-intent.md) rule 4), a step with a remote
  fallback is gated as though it were remote. Operators will see gates fire on steps that "were
  going to run locally anyway"; that is the rule working.

## Revisit when

Multi-operator workflows need approvals **routed to people** — assignment, delegation, escalation
after a period, or a second approver for high-value egress. That is a workflow model rather than a
mode, and it should arrive with its own record rather than by growing `approval.mode` a fourth
member.
