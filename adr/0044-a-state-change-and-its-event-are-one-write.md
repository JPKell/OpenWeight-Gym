# ADR-0044 — A state change and the event announcing it are one write

**Status:** Accepted (2026-09-01).
**Extends:** [ADR-0004](0004-sse-vs-websockets.md) (SSE for all streaming),
[Master architecture §7](../architecture/master-architecture.md).
**Relates to:** [ADR-0039](0039-audit-gated-blocking-requirements.md) (a run must attest to what it
did, never fall silent), [ADR-0036](0036-queue-recovery-transitions.md), risk T7.

## Context

Both applications that run long work keep the same two records: a **row holding the current state**
of a run or job, and an **append-only event log** describing how it got there. Every consumer in
the suite reads both — the SSE endpoint streams events and closes on a terminal one; the CLI
prints events and stops when the run reports itself finished; a resumed browser replays from
`Last-Event-ID` and then follows the live stream.

Two records, two readers, and no stated rule about the order in which they are written. IdeaPress
did the obvious thing:

```python
with self._database.write() as session:      # transaction 1: the run is now failed
    run.state = state
self._sink.emit(..., event_type="stage.failed")   # transaction 2: and here is why
```

which opens a window in which the run is readable as finished and the event saying so does not
exist yet. M8 CI found it: `test_an_invented_verdict_is_refused_rather_than_read_as_acceptable`
asserted that a refused stage emits `stage.failed`, and on a slower runner it did not. The event
was written; the assertion simply read the log inside the window.

The test was the cheap symptom. The expensive one was in the product: `ideapress plan build` drains
the event log, *then* asks whether the run has finished, then stops. A run whose state commits
first therefore ends with its terminal line never printed — the user watches a stage stop, with no
line saying whether it succeeded or failed. A run that ends without saying it ended is precisely
the silence ADR-0039 exists to forbid, arriving through the transport rather than through a model.

Swapping the order is not a fix, it is a change of victim. Emitting first would let an SSE client
receive `stage.completed`, ask the API about the run, and be told it is still executing.

LoadCoach already had the answer and had written down why. Its `JobEventSink.write` yields one
session and one event writer, so a transition and the event describing it commit together, and
staged events publish only after that commit — *"a subscriber can never see an event whose row was
rolled back."* What was missing was the rule as a rule, applying to both applications, rather than
one component's good habit.

## Decision

**A state change and the event that announces it are written in one transaction.** Neither is
observable without the other.

1. A writer that changes a state readers use to decide an event has happened must commit that
   change **in the same transaction as the event**. In IdeaPress this is `StageEventSink.emit`'s
   `alongside` parameter; in LoadCoach it is `JobEventSink.write`. A caller that opens its own
   transaction first is wrong even when it looks equivalent.
2. **Publish after commit, never inside the transaction.** The store stays the source of truth and
   the broker stays a latency optimisation (already stated for events alone; it now covers the
   pair).
3. A poller that reads both **asks for the state first and reads the log second**. The atomicity in
   (1) makes that order correct and the reverse order lossy: a log read taken before the finish
   check can miss the terminal event by a hair, and the loop then exits without looking again.
   Draining once more after the run reports itself finished is the same rule stated as code.

Ordinary progress events — `attempt.started`, `audit.completed`, a token frame — are unaffected.
This is about the events that *report* a state a reader can independently observe, of which the
terminal ones are the only ones that end a stream.

## Consequences

* IdeaPress's `StageRunner._finish` writes the run's terminal state and its terminal event in one
  transaction, and its CLI poller checks before it drains. Two regression tests hold the window
  open deliberately — one for each observer — so neither order can be reintroduced.
* LoadCoach needs no change; this ADR records the rule it already follows, and its
  `JobEventSink.write` is the reference implementation.
* The rule is testable without a race: widen the window artificially and assert the invariant,
  rather than waiting for a slow CI runner to find it. A test that can only fail under load is a
  test that will be re-run until it passes.
* No wire contract changes. This is an ordering rule about writes inside an application; no SetSpec
  payload, no HTTP response and no event shape is affected.

## Alternatives considered

**Emit the event first, then write the state.** Rejected: it moves the window rather than closing
it, and hands the worse half to the SSE client, who is told a run ended and then finds it running.

**Have readers tolerate the window** — poll again after seeing a terminal state, and treat a
missing terminal event as "not yet". Rejected: it pushes a storage-layer defect onto every consumer
present and future, and gets it wrong by default. The CLI, the SSE endpoint and the tests each
implemented the naive order independently, which is the evidence that the naive order is the one
people write.

**Leave it to tests to catch.** Rejected: the failure is timing-dependent, so tests catch it as
flakes, and a flake's usual treatment is a re-run.
