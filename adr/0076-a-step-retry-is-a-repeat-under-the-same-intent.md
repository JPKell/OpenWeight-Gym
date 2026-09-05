# ADR-0076 — A step retry is a repeat under the same intent

**Status:** Accepted (2026-09-05)
**Relates to:** [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md) (one immutable intent per turn —
the rule that makes a retry a new turn rather than a new envelope),
[ADR-0044](0044-a-state-change-and-its-event-are-one-write.md) (a state change and its event are
one write), [ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md) (approval is a mode with its
own scope, and silence never grants it — why an escalation is a re-approval and a repeat is not),
[ADR-0073](0073-egress-is-decided-on-configuration-before-availability.md) (the pre-flight order a
retried turn keeps), [ADR-0075](0075-a-request-carrying-tools-requires-tool-use-of-every-candidate.md)
(a construction-time refusal is `VALIDATION_ERROR`, which this record classes as deterministic).
**Source:** row G3 of [`docs/roadmap/outstanding-work.md`](../roadmap/outstanding-work.md), deferred
at G1 (`docs/history/G1_HANDOFF.md` §9) and scheduled by operator decision on 2026-09-04.

## Context

Until this record, a step that could not complete ended the trajectory. A LoadCoach failure at the
`/generate` call site halts at **T12** (`executing → halted`) with `LOADCOACH_ERROR` and LoadCoach's
own code preserved in the cause — G1's live run halted exactly that way when Ollama rejected a
tool call and LoadCoach answered `ALL_CANDIDATES_FAILED` (`docs/history/G1_HANDOFF.md` §10.4). (The
roadmap row said T7. T7 is `planning → failed`, the plan draft's corrective budget; a step failure
during execution is T12, or T13 when LoadCoach is unreachable.)

The only second chance anywhere in the loop is **tier escalation**: when no tier the intent
permits can serve — `NO_ELIGIBLE_MODEL`, `TASK_PROFILE_NOT_FOUND` — the turn raises a
`tier_escalation` drift whose disposition may request a scoped re-approval carrying the next tier
in the escalation order. That is not a repeat. It is an ask for a **wider envelope**, and its grant
mints a superseding intent revision.

So there are two different things a failure can deserve, and the loop had only one of them. What
was missing is the cheaper one: *try that again, under exactly the envelope already approved*.

The code for it is small. What is not small is that every attempt becomes a row an explanation
reads back months later, and P8's golden asserts that a materialized explanation and a
live-composed one are the same document. The record's shape has to be right before the explanation
composes it, which is why this is one accepted record and not four config keys.

## Decision

### 1. What is retryable: an accident, never a decision

**A governance outcome is a decision, and retrying a decision launders it. A service failure is an
accident, and repeating an accident is honest.** That is the line, and it is drawn structurally
rather than by a list of exceptions: **the retry lives at the LoadCoach call site and nowhere
else.** Egress evaluation, pricing, availability and budget (ADR-0073's order) all run *before*
`turn.started` and return their own terminal state; a deviation is compared *after* the response.
Neither reaches the code that decides to repeat. An egress denial, an unpriced-egress refusal, a
`tier_violation`, a deviation limit, a denied re-approval, a budget exhaustion and an approval
timeout are therefore not "excluded from the retryable set" — they are not in reach of it.

Within the failures that *do* reach it, a LoadCoach error is retryable when repeating the identical
request could plausibly get a different answer, and is not when it could not:

| Retryable — the condition is load, contention or a flaky attempt | Not retryable — the same request gets the same answer |
|---|---|
| `ALL_CANDIDATES_FAILED`, `PROVIDER_UNAVAILABLE`, `PROVIDER_TIMEOUT`, `PROVIDER_PROTOCOL_ERROR` | `VALIDATION_ERROR`, `VALIDATION_FAILED`, `STRUCTURED_OUTPUT_INVALID`, `SCHEMA_VERSION_UNSUPPORTED` |
| `QUEUE_FULL`, `MAX_WAIT_EXCEEDED`, `RATE_LIMITED`, `INSUFFICIENT_RESOURCES` | `MODEL_NOT_FOUND`, `CAPABILITY_UNSUPPORTED`, `PROVIDER_REJECTED` |
| `INTERNAL_ERROR` | `UNAUTHORIZED`, `FORBIDDEN`, `MISDIRECTED_REQUEST` |
| The client's own read timeout (`reason = client_timeout`), after the job it may have started is cancelled | `CONTEXT_LIMIT_EXCEEDED` (a context that does not fit still does not fit; compaction is its answer, not repetition) |
| | `GENERATION_CANCELLED`, `JOB_NOT_FOUND`, `JOB_NOT_CANCELLABLE`, `TRANSITION_REFUSED`, `ILLEGAL_TRANSITION`, `ATTEMPT_REFUSED`, `NOT_FOUND`, `EVIDENCE_*` |
| | Any code this build does not know |

Three of those rows are worth their reason in words.

* **`VALIDATION_ERROR` is a refusal, not an accident.** Since G2 (`G2_HANDOFF.md` §3.3) a request
  LoadCoach cannot construct fails the job with `VALIDATION_ERROR` and its attempts written,
  rather than hanging. The row's kickoff supposed G2 might move an error *into* the retryable set;
  it did the opposite, and correctly: a request whose shape LoadCoach refuses is refused again
  identically, so repeating it spends a turn to learn nothing. **An unknown code is not
  retryable**, for the same reason from the other direction: this build cannot show that repeating
  it could help, and the safe default for an unknown is the one that spends no money.
* **`NO_ELIGIBLE_MODEL` and `TASK_PROFILE_NOT_FOUND` are neither.** They already have a mechanism —
  fall to the intent's next permitted tier, then `tier_escalation` — and they are statements about
  *which tiers can serve*, not about an attempt that went wrong. This record does not touch them.
* **An unreachable LoadCoach is deliberately not retried.** It is an accident by the test above,
  but spec §13 says an unreachable LoadCoach mid-turn is T13 (`failed`) with the cause until a
  `waiting` state is specified, and this record introduces **no delay and no backoff**. Repeating
  immediately against a service that is down is a way to spend a retry budget in three
  milliseconds and learn nothing. A `waiting` state, with backoff, is a separate decision.

### 2. How many times: `[execution] step_retries`, default `1`, per step

The budget is **configuration, not a constant** — `[execution] step_retries`, `ge=0`, where `0`
means one attempt and no repeat, exactly as `[planning] corrective_retries` bounds the planner's
corrective (`G1_HANDOFF.md` §4). A number compiled into the loop is a number an operator with a
flaky provider cannot move.

**The default is `1`.** With no backoff, the second immediate repeat mostly re-meets the condition
the first one met; one repeat catches the genuinely single-attempt failure — the flaky candidate,
the one-off protocol error, the queue that had just filled — and stops there. An operator whose
deployment argues for more raises one key.

**The budget is per step, not per trajectory.** A step's attempts are what the step's record can
explain: they are on its thread, under its intent, and its halt names them. A per-trajectory budget
would let one step's halt say *"this attempt failed and there was no budget left"* when the budget
was spent by a different step hours earlier — an explanation that has to reach across steps to say
why this one got no second chance, and a step whose retryability depends on what ran before it.

### 3. Order: a repeat comes before an escalation

**A retryable failure repeats on the same tier, under the same intent, before any tier escalation
is raised.** Escalation is only reached the way it is reached today: every permitted tier answered
that it cannot serve.

The reason is what each mechanism *claims*. An escalation says **"the approved tiers cannot serve
this step"**, and its grant widens the envelope a human already bounded. A repeat says **"an
attempt failed; here is another under the same envelope."** If an escalation came first, the record
would assert the stronger claim on the evidence for the weaker one: a human would be asked to
approve a wider tier — possibly a remote one, possibly egress — because of a transient failure
nobody had tried twice. Escalation is a scoped re-approval (ADR-0049) and re-approvals are
expensive in the only currency that matters here, which is the operator's attention. Exhaust the
cheap, envelope-preserving answer first.

The order is also why a retryable failure **stops the tier ladder** rather than falling through it.
Falling to the next permitted tier on a transient failure is an escalation's move made without an
escalation's record: the step would execute on a tier it reached because something *flaked*, and
the turn row would say only that this tier served. The repeat re-enters the ladder from the top,
so the intent's tier order is honoured on every attempt.

### 4. The record: a counter, and the events are the history

**`plan_steps.attempt` counts; `step.retried` events are the history.** Option (a) of the row.

Each retry writes, in the same write that starts it (ADR-0044), one `step.retried` event carrying
the attempt number, the failed turn's id, the tier that failed, the cause and the error code — and,
on the planned path, the `plan_steps.attempt` increment in that same write.

* **The events are authoritative because they are the only half both paths have.** `plan_steps`
  rows exist only on the planned path; the bypass loop's synthetic `loop` step has none. An
  explanation that read attempts from the counter would have a history for one mode and nothing for
  the other, and spec §11 contract 1's diff would show the difference — with the events carrying
  it, the two modes' attempt records are identical and no allowance is added.
* **The counter is a denormalization, and is declared as one.** It is on `plan_steps` for the same
  reason `status` is: so the planned path's DAG is queryable without replaying events.
* **Not (b), derivation from the turn rows.** A failed attempt writes no turn row at all — only
  `turn.started` — so there is nothing to derive from but an absence, and *composing from
  emptiness* is precisely the hazard `G1_HANDOFF.md` §8 names for
  `materialize(rows) == compose_live(rows)`.
* **Not (c), a `step_attempts` table.** It would hold what the event already holds, in a table only
  the explanation reads, and would then have to be kept consistent with the event it duplicates.
  The event is already load-bearing for the explanation; one source is better than two agreeing.

### 5. What a retry is, and what it may not become

* **A new turn under the same intent revision.** Nothing widens (ADR-0056): same `intent_id`, same
  `revision`, same approved tiers, tools, classification ceiling and budget slice. A retry that
  minted an intent would be an escalation wearing a repeat's name.
* **On the step's thread**, with a fresh `turn_id`, through the same turn body: the same pre-flight
  order (ADR-0073), the same debit, the same `compare()`. There is no `if retrying:` branch inside
  governance — that is the two-source design ADR-0056 collapsed.
* **Debited as any turn.** A retry costs money and the ledger says so. A failed attempt that
  produced no response debits what it produced, by the same rule as any other turn.
* **Counted against `max_turns_per_step`.** Attempts and turns draw on one envelope, so a step
  cannot spend `max_turns` turns *and* a fresh retry budget on top of it. Whichever bound is
  reached first ends the step, and the two remain distinguishable in the record: reaching
  `max_turns` with no declared finish is a `turn_overrun` deviation and halts with
  `STEP_LIMIT_EXCEEDED`; exhausting the retry budget halts with the last attempt's error code and
  no deviation at all.
* **The halt after the last attempt names the last cause and every attempt** — each attempt's
  number, tier and cause, in the halt's own text. A halt that said only *"attempt 3 failed"* would
  make the record unable to answer the first question anyone asks of it.
* **Both paths, one code path.** The bypass loop's synthetic step retries through the same
  function, not a parallel one.

## What this record refuses

* **A governance refusal is never retried.** Not by configuration, not by an exception "just for
  this case". A denied egress, a denied re-approval, a violation, a deviation limit, a budget
  ceiling and an approval timeout are outcomes; a repeat would launder them, and the retry is
  placed where it cannot reach them.
* **A retry never widens an intent** and never mints one. Same revision or it is not a retry.
* **Silence is never a grant.** An exhausted retry budget halts and says so; it does not fall
  through to a wider tier, and it does not park waiting for a human who was never asked.
* **`step_retries` is not a delay.** No backoff, no sleep, no `waiting` state is introduced here.
* **An unknown LoadCoach code is not retryable.** The default for an unknown is the one that
  spends nothing.

## Consequences

* Spec §13's sentence *"No per-step retry policy is configured in this version — §12 has no key for
  one"* is superseded by this record; its `PROVIDER_UNAVAILABLE` / `PROVIDER_TIMEOUT` row's "retry
  per step policy" cell becomes real, and its `QUEUE_FULL` / `MAX_WAIT_EXCEEDED` "waits" cell
  remains unbuilt — those codes repeat, they do not wait.
* A transient failure now costs up to `1 + step_retries` turns of budget instead of one. That is
  the intended trade and it is bounded twice, by `step_retries` and by `max_turns_per_step`.
* An explanation composing a step reads `step.retried` events between the step's `step.started` and
  its `step.completed` or the trajectory's halt. `plan_steps.attempt` is a summary of them and is
  never the only source.
* `deviations` gains nothing. A retry is not a deviation: nothing about the executed reality
  contradicted the intent — the attempt produced no reality at all.
* A `waiting` state with backoff, and retryability for an unreachable LoadCoach, remain open and
  are a separate decision.
