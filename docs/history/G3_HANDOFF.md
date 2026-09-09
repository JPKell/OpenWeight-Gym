# G3 handoff — PromptCadence's per-step retry policy

**Row:** G3 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-05, daytime, reviewed.
**Model:** Opus 5 · high, as scheduled — no deviation.
**Ships:** nothing. Everything is under `## [Unreleased]`. No bump, no tag, no publish, no push.

---

## 1. Gate results — interpreter and exact invocations (M5C-13)

Interpreter: **Python 3.13.15** at `/home/jpk/ai/suite/PromptCadence/.venv/bin/python`. There is
no `python3.12` on this host.

```bash
cd /home/jpk/ai/suite/PromptCadence
.venv/bin/python -m ruff format --check .        # 138 files already formatted
.venv/bin/python -m ruff check .                 # All checks passed!
.venv/bin/python -m mypy src tests               # Success: no issues found in 134 source files
.venv/bin/lint-imports                           # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                                 # 1038 passed, 2 skipped, 2 deselected
```

Nothing was listening on 8768 at the gate run (`G1_HANDOFF.md` §14.6's trap: four CLI tests read a
live server if one is up). The LoadCoach this row started for §6 was stopped before the gate and
8768 was confirmed free.

Mirrors `cmp`-identical:

```bash
cd /home/jpk/ai/suite
for f in apps/promptcadence/{spec,development-plan,lifecycle}.md; do cmp docs/$f PromptCadence/docs/$f; done
# silent — all three identical
```

## 2. The gates, as commits

| Gate | Repo | Commit | What it made true |
|---|---|---|---|
| — | PromptCadence | `29eed67` | Housekeeping found at the start (§12.1): the docs mirror synced to the `docs/history/` handoff paths, and the agent/editor tooling ignored. |
| A | docs | `cf75d7e` | **ADR-0076**, accepted, with the ADR README index and its note. |
| B | docs / PromptCadence | `d0a1be4` / `7267ef5` | Lifecycle §4.3, §5, §8; spec §12, §13, §17; the development plan's G1 deferral note. The T7 error corrected. |
| C | PromptCadence | `9aa4af4` | Migration `0008`, `plan_steps.attempt`, `EventType.STEP_RETRIED` + `StepRetried`, `[execution] step_retries`. |
| D | PromptCadence | `422f6bd` | The loop, both paths, with the tests. |
| E | PromptCadence | `0f6734f` | Contract 1's third scenario — a retry on both paths, no new allowance. |
| — | docs | (this commit) | The G3 row marked done and its T7 reference corrected. |

Repository heads at the end: docs `main` ahead of `origin/main`, PromptCadence `main` ahead of
`origin/main`, **both trees clean**, nothing pushed and no push attempted.

## 3. The four decisions, with the reason and what the losing option would have claimed

### 3.1 What is retryable — an accident, never a decision

**Drawn structurally, not by a list of exceptions.** The repeat lives at the LoadCoach call site
(`LoopController._call`) and nowhere else. ADR-0073's pre-flights — egress, pricing, availability,
budget — all run *before* `turn.started` and return their own terminal state; every deviation is
compared *after* the response. So an egress denial, an unpriced-egress refusal, a `tier_violation`,
a deviation limit, a denied re-approval, a budget ceiling and an approval timeout are not
"excluded" — they are **out of reach**. That is a stronger property than a rule, because a later
reader cannot add a case to a list that does not exist.

Within what does reach it, the test is *could the identical request plausibly answer differently*:

* **Retryable** — `ALL_CANDIDATES_FAILED`, `PROVIDER_UNAVAILABLE`, `PROVIDER_TIMEOUT`,
  `PROVIDER_PROTOCOL_ERROR`, `INSUFFICIENT_RESOURCES`, `QUEUE_FULL`, `MAX_WAIT_EXCEEDED`,
  `RATE_LIMITED`, `INTERNAL_ERROR`, and the client's own read timeout after the job it may have
  started is cancelled.
* **Not** — `VALIDATION_ERROR`, `VALIDATION_FAILED`, `STRUCTURED_OUTPUT_INVALID`,
  `CONTEXT_LIMIT_EXCEEDED`, `MODEL_NOT_FOUND`, `CAPABILITY_UNSUPPORTED`, `PROVIDER_REJECTED`,
  `UNAUTHORIZED`, `FORBIDDEN`, the job/transition codes, **and any code this build does not know**.
* **Neither** — `NO_ELIGIBLE_MODEL` and `TASK_PROFILE_NOT_FOUND` keep their own mechanism
  (fall to the next permitted tier, then `tier_escalation`). Untouched by this row.

**What the losing option would have claimed.** A list-of-exceptions design would have made the
record say a governance refusal *was considered for a repeat and declined*, which invites the "just
this one case" amendment. The structural placement makes the record say it was never a candidate.

**What G2 changed, and it moved the other way from what the row expected.** The kickoff supposed
G2's cleaner failure semantics might move an error out of "timeout" and into a retryable named
code. It did the opposite: `G2_HANDOFF.md` §3.3 made a construction-time refusal fail the job with
`VALIDATION_ERROR` and its attempts written, rather than hanging. Cleanly refused is still refused,
so `VALIDATION_ERROR` is explicitly **not** repeated, and there is a test for it.

**An unreachable LoadCoach is deliberately excluded** even though it is an accident by the test
above. Spec §13 says T13 (`failed`) until a `waiting` state is specified, and this row adds no
backoff; repeating instantly against a service that is down spends the budget in milliseconds.

### 3.2 How many times — `[execution] step_retries`, default `1`, per step

Configuration, `ge=0`, where `0` is one attempt and no repeat — the `[planning] corrective_retries`
reading exactly (`G1_HANDOFF.md` §4). Both are pinned by a test, including the shipped example.

**Default 1, because there is no backoff.** The second immediate repeat mostly re-meets the
condition the first met; one catches the genuinely single-attempt failure — a flaky candidate, a
one-off protocol error, a queue that had just filled. Raising it is one key.

**Per step.** What the losing option would have claimed: with a per-trajectory budget, a step's
halt would say *"this attempt failed and there was no budget left"* when the budget was spent by a
different step hours earlier. The explanation would have to reach across steps to say why this one
got no second chance, and a step's retryability would depend on what ran before it.

### 3.3 Order — a repeat before an escalation

A repeat says *"an attempt failed; here is another under the same envelope."* An escalation says
*"the approved tiers cannot serve this step"*, and its grant widens what a human bounded
(ADR-0049).

**What the losing option would have made the record claim:** with escalation first, a human would
be asked to approve a wider tier — possibly a remote one, possibly egress — on the evidence of one
transient failure nobody had tried twice. The approval request would assert the stronger claim on
the weaker evidence, and the record would keep that assertion permanently.

**Consequence in the code:** a retryable failure **stops the tier ladder** rather than falling to
the next permitted tier. Falling through would be an escalation's move made without an escalation's
record — the step would run on a tier it reached because something flaked, and the turn row would
say only that the tier served. Asserted by
`test_a_repeat_stops_the_tier_ladder_rather_than_falling_through_it`.

### 3.4 The record — (a), a counter plus the events

`plan_steps.attempt` counts; `step.retried` events are the history.

**The deciding argument is contract 1, not storage.** `plan_steps` rows exist only on the planned
path — the bypass loop's synthetic `loop` step has none. A history in the counter would give one
mode attempts and the other nothing, and the diff would show it; with the events carrying it, the
two modes' attempt records are identical and **no allowance was added** to G1's closed list.

* **Not (b), derivation.** A failed attempt writes no turn row at all — only `turn.started` — so
  there is nothing to derive from but an absence, and *composing from emptiness* is exactly the
  hazard `G1_HANDOFF.md` §8 names for `materialize(rows) == compose_live(rows)`.
* **Not (c), a `step_attempts` table.** It would hold what the event already holds, in a table only
  the explanation reads, and would then need keeping consistent with the event it duplicates.

The event body is a golden (`tests/unit/test_dispatch.py`):

```python
{"trajectory_id", "step_id", "thread_id", "intent_id", "intent_revision",
 "attempt", "failed_turn_id", "failed_tier", "cause", "error_code"}
```

`cause` and `error_code` are LoadCoach's own, never model output, so `domain/events.py`'s rule
holds and the per-body content test passes unchanged.

## 4. The demonstrations, verbatim

Both scripted against the fake LoadCoach and therefore deterministic. Script:
`scratchpad/demo_retry.py` (not committed — scratch, per the kickoff).

### 4.1 Fails twice, completes on the third attempt (`step_retries = 2`)

```text
=== fails twice, completes on the third attempt (step_retries = 2) ===
[ 1] trajectory.created
[ 2] trajectory.claimed
[ 3] plan.drafted
[ 4] plan.approved
[ 5] intent.minted
[ 6] step.started
[ 7] turn.started — tier local_fast, intent revision 1
[ 8] step.retried — attempt 2 after local_fast (LOADCOACH_ERROR): LoadCoach refused /api/v1/generate with ALL_CANDIDATES_FAILED: scripted failure
[ 9] turn.started — tier local_fast, intent revision 1
[10] step.retried — attempt 3 after local_fast (LOADCOACH_ERROR): LoadCoach refused /api/v1/generate with PROVIDER_TIMEOUT: the provider did not answer in time
[11] turn.started — tier local_fast, intent revision 1
[12] budget.debited
[13] turn.completed
[14] step.completed
[15] trajectory.completed

state        completed
error_code   None
cause        the provider declared finish_reason=stop
plan_steps   [{"step_id": "s1", "status": "committed", "attempt": 3}]
```

Every `turn.started` names **intent revision 1**: nothing was minted and nothing widened. One
`budget.debited`, for the turn that answered.

### 4.2 Spends the budget and halts (`step_retries = 1`)

```text
=== spends the budget and halts (step_retries = 1) ===
[ 1] trajectory.created
[ 2] trajectory.claimed
[ 3] plan.drafted
[ 4] plan.approved
[ 5] intent.minted
[ 6] step.started
[ 7] turn.started — tier local_fast, intent revision 1
[ 8] step.retried — attempt 2 after local_fast (LOADCOACH_ERROR): LoadCoach refused /api/v1/generate with ALL_CANDIDATES_FAILED: scripted failure
[ 9] turn.started — tier local_fast, intent revision 1
[10] trajectory.halted

state        halted
error_code   LOADCOACH_ERROR
cause        step s1: 2 attempts failed under intent 01M1RAQAV7FVCEYSH4HE0KNESW revision 1 and the retry budget (step_retries = 1) is spent — attempt 1 (local_fast): LoadCoach refused /api/v1/generate with ALL_CANDIDATES_FAILED: scripted failure; attempt 2 (local_fast): LoadCoach refused /api/v1/generate with PROVIDER_TIMEOUT: the provider did not answer in time
plan_steps   [{"step_id": "s1", "status": "running", "attempt": 2}]
```

The halt names the last cause **and every attempt with its tier**, which is the row's point. Note
`plan_steps.status` stays `running` — a halt ends the trajectory and leaves the step as it was,
which is `0007`'s existing rule, not a new one.

## 5. The live run (gate E item 3)

LoadCoach was **not** left running by G2, so this row started it: `loadcoach 1.0.0` on 8766 over
the real Ollama, and stopped it again before the gate. Script: `scratchpad/live_retry.py`.

A real `ALL_CANDIDATES_FAILED` is no longer easy to provoke — G2's tool wire removed the path G1
hit — so the live evidence is a **real client read timeout**, which is in the same retryable class
and is deterministic at a 0.5 s timeout.

```text
=== live: a clean run on the real stack (no repeat) ===
[ 1] trajectory.created … [ 9] trajectory.completed
state        completed
answer       'ready'

=== live: a real client timeout, repeated, then the budget spent ===
[ 1] trajectory.created
[ 2] trajectory.claimed
[ 3] intent.minted
[ 4] step.started
[ 5] turn.started — tier local_fast, intent revision 1
[ 6] step.retried — attempt 2 after local_fast: LoadCoach did not answer /api/v1/generate within the configured timeout (LoadCoach job 01M1RATSCCP6EQA1BBCGVH3JEH was cancelled)
[ 7] turn.started — tier local_fast, intent revision 1
[ 8] trajectory.halted

state        halted
error_code   LOADCOACH_ERROR
cause        step loop: 2 attempts failed under intent 01M1RATS9ZTQE3G24NE2Z9N1KR revision 1 and the retry budget (step_retries = 1) is spent — attempt 1 (local_fast): LoadCoach did not answer /api/v1/generate within the configured timeout (LoadCoach job 01M1RATSCCP6EQA1BBCGVH3JEH was cancelled); attempt 2 (local_fast): LoadCoach did not answer /api/v1/generate within the configured timeout (LoadCoach job 01M1RATSYRKB21JA2H2KF247P1 was cancelled)
```

**The finding worth carrying forward.** Both cancelled jobs came back from LoadCoach as
`{"status": "completed", "cancel_requested": true}`: the model answered in well under a second, so
the cancel arrived after the work was done. A client-timeout repeat therefore costs **real provider
work that the ledger never sees** — no turn row, no debit — and the repeat doubles it. This is not
new with this row (G1 already abandoned the job and halted, with the same invisible spend), but the
retry multiplies it, and a `waiting`-state design with backoff should reckon with it. It is also an
argument for keeping the default at `1`.

## 6. `turn_overrun` and a retry are distinguishable in the record

Yes, on three independent facts:

| | A spent retry budget | `turn_overrun` |
|---|---|---|
| Error code | the last attempt's (`LOADCOACH_ERROR`, `TIER_UNAVAILABLE`, …) | `STEP_LIMIT_EXCEEDED` |
| Halt text | `N attempts failed … step_retries = M — attempt 1 (tier): …` | `the intent's max_turns (N) is spent with no declared finish` |
| Events | one `step.retried` per repeat | a `deviation.detected` of category `turn_overrun` |

`test_attempts_and_turns_draw_on_one_envelope_so_max_turns_still_binds` asserts the pair directly:
with `step_retries = 5` and `max_turns_per_step = 2`, two repeats are recorded and the third
iteration halts as `STEP_LIMIT_EXCEEDED`, not as a spent budget. **`turn_overrun` itself still has
no loop-level test** (`G1_HANDOFF.md` §15c) — that is unchanged, and §9 below says what the cheapest
one would be.

## 7. The I1 note — how the explanation reads a retry back

**Where the attempts are.** Between the step's `step.started` and its `step.completed` (or the
trajectory's `trajectory.halted`), in `events`, ordered by `sequence`. One `step.retried` per
repeat, each naming the attempt number it *starts*, the turn that was announced and never answered,
that turn's tier, and the cause. `plan_steps.attempt` is the summary and, on the planned path only.

**The order to read them in.**

1. `step.started` — the thread, the intent and its revision.
2. Interleaved `turn.started` / `step.retried`, by `sequence`. Attempt *n*'s turn is the
   `turn.started` immediately before the `step.retried` naming attempt *n+1*; equivalently, the
   `step.retried`'s `failed_turn_id` **is** that `turn.started`'s `turn_id`, which is the join to
   prefer — it does not depend on adjacency.
3. `step.completed`, or `trajectory.halted` whose `cause` already lists every attempt.

**Whether `materialize(rows) == compose_live(rows)` gains a hazard here.** One, and it is small:

* **A failed attempt has a `turn.started` event and no `turns` row.** An explanation that composes
  a step's turns by walking `turns` will silently skip the failed attempts; one that walks
  `turn.started` events will show turns that have no content, no usage and no debit. **Compose the
  attempt list from `step.retried`, and the turn list from `turns`** — do not try to make one
  source serve both. This is `G1_HANDOFF.md` §8's *compose from an explicit flag, never from
  emptiness*, in its exact shape: the absence of a turn row is not the record of a failed attempt;
  the `step.retried` event is.
* No new **content** hazard: `cause` is LoadCoach's error text, not model output, so the retention
  scrub does not touch it and materialized and live composition see the same string forever.
* No new **ordering** hazard: attempts are ordered by event `sequence`, which is unique per
  trajectory under the trajectory-row CAS, so the millisecond-clock tie problem `G1_HANDOFF.md` §8
  names for `threads` does not arise for these.
* No new table for I1 to compose, by design (§3.4).

## 8. Exit conditions (kickoff §10)

| # | Condition | Result |
|---|---|---|
| 1 | One ADR taking all three decisions and the record shape, with refusals stated | ADR-0076, accepted, §"What this record refuses" |
| 2 | Lifecycle §4.3/§5/§8 and spec §13 amended before the code; T7 corrected | Gate B, before gates C–E; T7 corrected in lifecycle §8.2 and in the roadmap row |
| 3 | Retryable repeated to the budget; governance refusal / egress denial / deviation halt never repeated, each with its own test | `test_step_retry.py` (four deterministic refusals parametrized, the deviation halt) and `test_egress.py::test_an_egress_denial_is_never_repeated` |
| 4 | New turn, same intent revision, on the step's thread, counted against `max_turns_per_step`, debited | Asserted in `test_a_step_that_fails_twice_completes_on_its_third_attempt` and the max_turns test |
| 5 | `plan_steps.attempt` + `step.retried` in the write that starts the attempt | `_record_retry`, one `self._sink.write()` block; migration `0008` |
| 6 | The halt names the last cause and every attempt, asserted on its text | `test_the_budget_is_spent_and_the_halt_names_the_last_cause_and_every_attempt` |
| 7 | The bypassed path retries identically; contract 1 green with no new allowance | `test_the_bypassed_loop_repeats_through_the_same_code_path`; contract 1's third scenario, allowance list untouched |
| 8 | Full gate green, interpreter and invocations named; mirrors `cmp`-identical | §1 |

## 9. Read-only notes (kickoff §13)

* **(a) I1 readiness** — §7 above.
* **(b) The cheapest `turn_overrun` journey.** Now trivial and adjacent to this row's tests: set
  `max_turns_per_step = 1` and script a single generation whose `finish_reason` is not a declared
  finish (a tool-call answer, or `length`). The step's first turn records, the loop's next
  iteration sees `turns_used >= max_turns`, and `compare()` raises `turn_overrun` — which today's
  loop halts on as `STEP_LIMIT_EXCEEDED` *before* the deviation, so the journey is really a test of
  which of the two fires first. That ordering question is worth settling in the same session that
  writes the journey, and it is a spec question, not a test question.
* **(c) Should any of the retryable set have been LoadCoach's job instead?** Two candidates, and
  the answer is *not yet* for both. `QUEUE_FULL` and `MAX_WAIT_EXCEEDED` are statements about
  LoadCoach's own queue depth; a caller repeating immediately is the least informed possible
  response, and LoadCoach already has `max_wait_seconds` on a job. If LoadCoach ever admits a
  caller-visible *wait*, those two should leave PromptCadence's retryable set and become a park —
  which is the same `waiting`-state decision §3.1 defers. `RATE_LIMITED` is the same shape with a
  provider's clock behind it. The smaller policy is the better one, and the smaller policy here
  needs a mechanism nobody has built yet; until then repeating is the honest approximation and the
  budget of 1 bounds it.

## 10. Things this prompt said that turned out not to be true

1. **§0's "the highest ADR today is `0074`"** — G2 took `0075`, as §0 anticipated it might. This
   row is `0076`.
2. **§0's T7/T12 question, answered.** The LoadCoach-error path takes **T12** (`executing →
   halted`) with `LOADCOACH_ERROR`; T13 is reserved for the unreachable case
   (`LOADCOACH_UNAVAILABLE`). The roadmap row's T7 was wrong and is corrected.
3. **§0.2(1) expected G2 to move an error *into* the retryable set.** It moved one out: a
   construction-time refusal is now a clean `VALIDATION_ERROR` and is deterministic (§3.1).
4. **§0.2's "debited as any turn — a retry costs money and the ledger says so."** True of a repeat
   that *answers*. A repeat whose attempt failed produces no response and therefore no debit — and
   the live run showed the sting in that (§5): the provider may have done the work anyway.
5. **Gate A's "mirrored into `PromptCadence/docs/`, `cmp`-proved"** for the ADR. No component repo
   mirrors ADRs — the mirrors carry only that component's own `spec.md`, `development-plan.md` and
   `lifecycle.md`, and the existing `../../adr/…` links in them are already relative to the
   workspace `docs/`. Following the repo's precedent rather than the instruction; the three
   mirrored files *are* `cmp`-proved.
6. **§9.3's "if G2 left LoadCoach + Ollama running".** Ollama was up, LoadCoach was not. Starting
   it took about a minute, so the live run happened anyway (§5).

## 11. Left for the operator

1. **Push two repositories.** `docs` and `PromptCadence`, both ahead of `origin/main`. Nothing was
   pushed and no push was attempted.
2. **No tag, no publish.** `0.9.0b0` is untouched. Its changelog's *Known limitations* names the
   unbuilt step retry; **that line comes out at the next release, not this row.**
3. **One pre-existing working-tree item was resolved, not left** (`G2_HANDOFF.md` §12.3): the two
   `.gitignore` edits and the docs-mirror drift are committed as `29eed67`, and `skills-lock.json`
   is now ignored rather than untracked. If any of that was deliberate, revert that one commit.
4. **The invisible-spend observation in §5** is a candidate for the `waiting`-state decision, and
   possibly for LoadCoach: a job that completes after its caller's read timeout is work nobody
   bills.
