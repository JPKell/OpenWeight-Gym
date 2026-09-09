# ADR-0036 — Queue state machine: recovery edges for every lease-holding state

**Status:** Accepted (2026-08-29)
**Extends:** [ADR-0029](0029-queue-mechanics.md), [Queue and Scheduling §2](../apps/loadcoach/queue-and-scheduling.md).

## Context

ADR-0029 §3 made `admitted` an explicit state between claim and execution and declared the
transition table in Queue §2 "normative and complete". Building Phase 5 against that table found
three places where a job can legally arrive in a state it cannot legally leave:

1. **Recovery from `admitted`, `validating` and `retrying` has no edge.** Queue §10 step 2 and the
   table's lease-expiry edges name only `leased` and `executing` (→ `queued` for idempotent work,
   → `failed` with `worker_lost` otherwise). Yet `admitted` (claimed, resources reserved, provider
   not yet called), `validating` (response received, checks running) and `retrying` (the backoff
   between two attempts) all hold a lease, all persist — every transition is persisted — and a
   process can die in any of them. Queue §12 requires "restart recovery from every non-terminal
   state, including `admitted`". With the table as written, recovery from `admitted` would have to
   pass through `executing` as a bookkeeping step, which records a provider call that never
   happened.
2. **A cancel that arrives during `retrying` has no path.** `admitted`, `executing` and
   `validating` each have a `→ cancelling` edge; `retrying` does not, so a cancel during a
   multi-second backoff could only take effect after the job re-entered `admitted`.
3. **Admission can fail permanently.** Routing at admission may find no eligible model for a
   reason that no amount of waiting fixes — a capability the provider lacks, a context no model
   serves. The table's only `leased → failed` edge is labelled "lease expired (non-idempotent
   work)". Deferring to `waiting_resources` would be a lie (nothing will free), and the job must
   reach `failed`.

## Decision

### 1. Lease expiry and recovery apply uniformly to every lease-holding state

The set of states that hold a lease is `{leased, admitted, executing, validating, retrying}` (and
`cancelling`, handled separately below). Lease expiry — detected by the reaper while the process is
alive, or by startup recovery — moves a job from **any** of them to `queued` (idempotent work) or
`failed` with `worker_lost` (non-idempotent work). This adds five edges:

```text
admitted   --> queued | failed : lease expired / recovery, by idempotency
validating --> queued          : lease expired / recovery (validating --> failed already existed)
retrying   --> queued | failed : lease expired / recovery, by idempotency
```

The edges the table already had (`leased → …`, `executing → …`, `validating → failed`) are
unchanged; the rule is now one rule rather than a set of special cases. `jobs.attempt` is untouched by any of these transitions
(ADR-0029 §2), so a re-claim after recovery continues the attempt sequence.

### 2. `retrying → cancelling` is legal

A cancel request during backoff takes effect immediately rather than after the next admission.
`retrying → cancelling → cancelled` is the path; `cancel_requested` is set transactionally exactly
as for every other in-flight state.

### 3. `leased → failed` also carries the reason `NO_ELIGIBLE_MODEL`

The edge already exists. When admission's routing pass rejects every candidate and **none** of the
rejections is resource-shaped (`insufficient_vram`, or an unknown estimate), the job fails from
`leased` with `state_reason = NO_ELIGIBLE_MODEL` and the decision's rejections in its terminal event.
When at least one rejection is resource-shaped, the job defers to `waiting_resources` as Queue §5
requires: something may free.

### 4. Unchanged

`cancelling → cancelled` remains the recovery for a job caught mid-cancel; `waiting_resources` is
re-evaluated on recovery and either returns to `queued` or stays; `queued` stays. The table in
Queue §2 is updated to show the edges above and remains normative: every legal transition is
exercised by a test and every unlisted pair is asserted as rejected.

## Alternatives considered

**Route recovery through `executing`.** `admitted → executing → queued` reuses existing edges.
Rejected: it persists a `job.executing` event and a state the job never occupied, and the job
history is the thing a person reads to find out what happened.

**Collapse `validating` and `retrying` into `executing`.** Fewer states to recover. Rejected: the
states are what make the transition history say *where* an attempt stood — "the response was
received and failed validation" and "the provider never answered" are different diagnoses.

**Make admission failure a deferral.** `leased → waiting_resources` for every routing failure, with
`max_wait_seconds` as the eventual terminal. Rejected: an hour in `waiting_resources` for a job that
no resource change can ever admit is the "waits forever" behaviour spec §13 promises against.

## Consequences

*Positive.* Every state a job can be found in after a crash has exactly one recovery edge, and the
rule is a single sentence. Cancellation reaches a job in backoff. Permanent admission failure is
reported as what it is.

*Negative.* Thirty legal edges instead of twenty-four. The state-machine test enumerates every
pair, so the cost is a longer table in one test.

## Revisit when

ADR-0010's own trigger fires — workers on other machines — at which point "the process died" stops
being the only meaning of an expired lease and recovery becomes a protocol.
