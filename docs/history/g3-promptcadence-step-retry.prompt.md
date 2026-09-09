# Kickoff — G3: PromptCadence's per-step retry policy — one ADR, then the record shape it forces

**Row:** G3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · high**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
Lifecycle semantics that become persisted record shape — small in code, permanent in what an
explanation says.
**Repositories:** `/home/jpk/ai/suite/docs` (the ADR and the amendments, **first**), then
`/home/jpk/ai/suite/PromptCadence`.
**Ships:** **nothing.** `0.9.0b0` is cut; this goes under `## [Unreleased]`. **No bump, no tag, no
publish.**
**Overnight:** **no.** [§2.12](docs/roadmap/model-assignment.md) puts batch G on the never-overnight
list. Daytime, reviewed same day.
**Runs after:** G1 (done 2026-09-04) and **G2** (the tool wire — it lands in the same
`services/loop.py`; do not start this row with G2 uncommitted).
**Runs before:** **I1** — a hard edge (outstanding-work §3). P8's
`materialize(rows) == compose_live(rows)` golden must see step attempts **in the shape the record
will keep**, so the shape has to be right before the explanation composes it.
**Not in this session:** the explanation document, the operator UI, compaction (all **P8/I1**); the
tool wire (**G2**); hardening and the injection corpus (**P9**).

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **PromptCadence `main` was at `952af18`** and **docs `main` at `3d7d11f`**, both clean and level,
  before G2. **This row starts from whatever G2 left** — **confirm** `git status -sb` and the head
  commit in both repos at the start and at the end (CLAUDE.md, working-tree integrity).
* **`0.9.0b0` (`c9ed99a`) is cut but may not yet be tagged or published** — that is the operator's,
  and nothing in this row touches it. Its changelog's *Known limitations* names **the unbuilt step
  retry**: this row is what removes that line at the next release, not this one.
* **The highest ADR today is `0074`** (`docs/adr/`). **Confirm the next free number** before you
  write — G2 may have taken `0075`.
* **Migration head is `0007_planning_and_approval`**
  (`src/promptcadence/infrastructure/db/migrations/versions/`). Yours will be `0008`; confirm G2
  did not add one.
* **What exists, and is the precedent to follow, not to re-invent:**
  * `[execution] max_turns_per_step = 8` (`config.py:264`) and `[planning] corrective_retries = 2`
    (`config.py:212`, defaults rendered in the shipped config at `:768`/`:783`) — G1 made the
    corrective budget **configuration, not a constant**, and said so in its handoff §4. That is the
    precedent the row names.
  * Tier escalation on a service failure: `_escalate` (`services/loop.py:1651`),
    `next_escalation`, the permitted-tier list, and the `tier_escalation` deviation whose
    disposition the policy decides (`loop.py:1464`, spec §13). **This is the only retry the loop
    has today.**
  * The halt path: `halt` with `cause=exc.message, error_code=ErrorCode(exc.code)`
    (`loop.py:1479`, `:1509`, `:1604`).
  * `plan_steps` (`infrastructure/db/models.py:390`) with `status` (`pending` / `running` /
    `committed`), `started_at`, `completed_at`, and the unique `(plan_id, step_id)`.
  * `EventType` (`domain/events.py:49`, `:59`) — `step.started` and `step.completed` — and
    `domain/dispatch.py:88`/`:118`, the event payloads written **in the same write** as the state
    change (ADR-0044).
  * One thread per step (`infrastructure/threads.py:175`), opened at the step's first dispatch.
* **The row's own text has one thing wrong, and you should not propagate it.** It says a failed
  step halts the trajectory at **T7**. T7 is `planning → failed`, *"plan draft failed after the
  corrective budget"* (`lifecycle.md:436`). A step failure during execution is **T12**
  (`executing → halted`, cause recorded) or **T13** (`executing → failed`, unrecoverable) —
  `lifecycle.md:441`–`:442`, and G1's live halt at `docs/history/G1_HANDOFF.md` §10.4 came out `halted` with
  `LOADCOACH_ERROR`. **Confirm which of T12/T13 the LoadCoach-error path takes today** before the
  ADR names a transition, and correct the row when you update it.
* **Python 3.13.15; there is no python3.12 on this host.** Name the interpreter and every exact
  invocation (M5C-13). **Stop any demo PromptCadence on 8768 before running the gate** — four CLI
  tests read a live server if one is up (`docs/history/G1_HANDOFF.md` §14.6).
* **Never `git push`.** Commit at every gate boundary; leave pushing to the operator. Do not run a
  push dry-run either.

## 0.1 What this row actually is

Today: a step that fails halts the whole trajectory, and the only second chance anywhere in the
loop is the tier escalation that fires when no permitted tier could serve. There is no notion of
*try that step again*. G1 deferred it deliberately and the operator scheduled it on 2026-09-04.

The code is small. The permanence is not: **every retry becomes a row that an explanation will read
back months later**, and I1's golden asserts that a materialized explanation and a live-composed one
are the same document. Get the shape wrong here and I1 either inherits it or breaks. So the order is
**decide → document → shape the record → then the loop**, and the ADR is not a formality.

## 0.2 The three decisions the ADR must take — together, in one ADR

The row names them. They interact, which is why they are one ADR and not three.

1. **What is retryable.** Retryable: a LoadCoach service failure — `ALL_CANDIDATES_FAILED`,
   `TIER_UNAVAILABLE`, timeouts. **Never** retryable: a governance refusal, an egress denial, a
   deviation halt. The line is not arbitrary — a governance outcome is a *decision* and retrying a
   decision is laundering it; a service failure is an *accident*. State the principle in those
   terms, then enumerate against PromptCadence's actual `ErrorCode` values and LoadCoach's error
   vocabulary (`apps/loadcoach/api.md` §10), so the ADR is checkable rather than gestural. Note
   what G2 changed here if it changed anything: after G2 a corrective that ModelRack refuses fails
   the job cleanly rather than hanging, which may move an error out of "timeout" and into a named
   code.
2. **How many times.** `[execution] step_retries`, default small, **configuration and not a
   constant** — the `corrective_retries` precedent exactly (G1 §4). Decide the default and defend
   it in one sentence. Decide, too, whether the budget is per step or per trajectory
   (recommendation: **per step**, because that is what the record can explain — but say so).
3. **Whether a retry runs before or after tier escalation.** This is the decision with the longest
   shadow. A retry on the same tier is a **repeat**; an escalation is a **scoped re-approval**.
   The order changes what the record says happened, and therefore what an explanation says. Take
   it explicitly and give the reason, including what the losing order would have made the record
   claim.

And the invariants the ADR must restate, because they constrain all three:

* A retry is a **new turn under the same intent revision**. Nothing widens (ADR-0056). It is on the
  step's thread, counted against `max_turns_per_step`, and **debited as any turn** — a retry costs
  money and the ledger says so.
* It is recorded as `plan_steps.attempt` plus a **`step.retried` event in the write that starts it**
  (ADR-0044). Not after; not in a separate write.
* **The halt after the last attempt names the last cause and every attempt.** A halt that says only
  "attempt 3 failed" is the failure mode this row exists to prevent.
* **Both paths.** The bypassed loop's synthetic step retries the same way, or contract 1 fails —
  and the governance-invariance diff must stay green **with no new allowance** (spec §11 contract 1,
  `tests/contract/test_governance_invariance.py`, allowance list closed at `docs/history/G1_HANDOFF.md` §5).

## 0.3 The record-shape question the row states but does not settle

`plan_steps.attempt` is one column on a row that is unique per `(plan_id, step_id)`. That gives you
**a counter**, not a history. An explanation that must name *every attempt* needs each attempt's
cause, tier and time — and the counter alone cannot produce them.

Decide, in the ADR, which of these the record is:

* **(a) A counter plus the events.** `plan_steps.attempt` increments; each `step.retried` event
  carries the cause, the tier and the attempt number; the explanation reads the events. Cheapest,
  no new table, and it makes the events load-bearing for the explanation — which they may already
  be.
* **(b) A counter plus derivation from existing rows.** The turns on the step's thread already carry
  tier, intent revision and outcome; attempts are derivable. Cheapest of all, and the most fragile:
  derivation rules are exactly what `materialize(rows) == compose_live(rows)` breaks on.
* **(c) A `step_attempts` table.** Explicit, queryable, one row per attempt with its cause. Most
  storage, least ambiguity, and one more table for I1 to compose.

The row's phrasing (`plan_steps.attempt` **plus** a `step.retried` event) points at **(a)**;
recommendation is (a) unless reading I1's needs says otherwise. **Read `docs/history/G1_HANDOFF.md` §8's hazard
list before choosing** — it names, for the plan/approval rows specifically, what
`materialize(rows) == compose_live(rows)` trips on: model output must follow the retention scrub;
threads order by `created_at` then `id` and ties are real under the millisecond clock; compose from
an explicit flag, never from emptiness. Whichever you choose, **the choice is in the ADR with its
reason**, and the I1 note in the handoff says how the explanation reads it.

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb && git -C /home/jpk/ai/suite/docs log --oneline -3
git -C /home/jpk/ai/suite/PromptCadence status -sb && git -C /home/jpk/ai/suite/PromptCadence log --oneline -3
source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show setspec commissioner loadledger toolyard | grep -E "^(Name|Version)"
```

Every scratch database, config file, workspace and log goes in the session scratchpad — **never**
the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory. Nothing at the workspace root is versioned; do not overwrite a
  root file you did not create.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional
  Commit per gate**, committed at each gate boundary.
* `pytest-randomly` is on; a seed-only failure is a real bug, not a flake. G1's recovery race was
  found exactly that way (`docs/history/G1_HANDOFF.md` §14.7).
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names, keyword-only optionals and booleans, frozen slotted value objects, pydantic wire
  models, SQLAlchemy models never leaving the repository layer, `mypy --strict`, line length 100.
* `web → cli → services → domain`; `domain` imports no framework and no `httpx`. Never weaken
  `.importlinter`.
* **A state change and its event are one write** (ADR-0044). This row adds one event type.
* **Never `git add -A`.** Stage named paths. Every workspace `docs/` edit is mirrored into
  `PromptCadence/docs/` byte-identically and **`cmp`-proved**.

## 3. Reading list, in this order

1. `docs/apps/promptcadence/lifecycle.md` **§4.3** (the `ExecutionIntent` and its four load-bearing
   rules — a retry lives entirely inside one), **§5** (the deviation categories, and where
   `tier_escalation` sits), **§8** (the states and T1–T17; the transition table at `:436`–`:442` is
   where §0's T7 correction comes from).
2. `docs/apps/promptcadence/spec.md` **§13** (error behaviour — `NO_ELIGIBLE_MODEL` → fallback →
   `tier_escalation`, the existing shape a retry has to sit beside), **§11 contract 1**, **§12**
   `[execution]`, **§17** (the event list — your new event joins it).
3. **`docs/history/G1_HANDOFF.md`**: **§9** (what the real stack found — the failures a retry would actually have
   met), **§10.4** (a real halt, verbatim: the trajectory this row would have retried), **§10.2**
   (what a clean run looks like), **§5** (the contract-1 allowance list, closed), **§13** (what must
   not be relitigated), **§8** (what I1 inherits — the §0.3 decision answers to this).
4. **ADR-0056** (= D-12, one immutable intent per turn — the rule that makes a retry a new turn
   rather than a new intent), **ADR-0044** (state change and event in one write), **ADR-0047**
   (= D-3, a tier is configuration and a model never sizes its own budget), **ADR-0049** (= D-5,
   approval is a mode with its own scope, and silence never grants it — the reason an escalation is
   a scoped re-approval and a retry is not), **ADR-0073** (the pre-flight order egress → pricing →
   availability → budget, which a retried turn keeps).
5. `docs/roadmap/promptcadence-roadmap.md` §9 and §3's **M12** exit condition — this row is one of
   its named items.
6. The code, before you design against it: `services/loop.py` around `_escalate` (`:1651`), the
   step dispatch and its halt sites (`:1259`, `:1400`–`:1509`), `config.py:194`–`:264`,
   `domain/events.py`, `domain/dispatch.py`, `infrastructure/db/models.py:390`.

---

## 4. The shape of the work — five gates

A → the ADR. B → the documents. C → the record shape. D → the loop, both paths. E → the proof and
the demonstration.

**A and B come before any code.** That is the standing rule (outstanding-work §3: *A1 before all
code — ADRs before implementation*), and it is load-bearing here specifically: the §0.3 choice
decides a migration, and a migration written before the decision is a migration you will rewrite.

## 5. Gate A — one ADR

At the next free number, **accepted**, in `docs/adr/`, mirrored into `PromptCadence/docs/`,
`cmp`-proved. It takes §0.2's three decisions and §0.3's record shape, restates the invariants it is
constrained by, and — house form — says what it **refuses**: a governance refusal is never retried,
a retry never widens an intent, silence is never a grant. Reference it from `lifecycle.md` and
`spec.md` in gate B. ADRs are superseded, never edited.

**Commit:** `docs(adr): NNNN — a step retry is a repeat under the same intent`.

## 6. Gate B — lifecycle and spec, amended

Workspace `docs/` first, then the byte-identical mirror.

* `lifecycle.md` **§4.3** (a retry is a new turn under the same intent revision — say it where the
  intent's rules are stated, not in a footnote), **§5** (where a retry sits relative to
  `tier_escalation`, per §0.2(3)), **§8** (the transition, and the T7 correction from §0 — say
  plainly which transition a step failure takes, since the roadmap row got it wrong).
* `spec.md` **§13** (the retry in the error-behaviour ladder), **§12** (`[execution] step_retries`),
  **§17** (the `step.retried` event).
* `docs/apps/promptcadence/development-plan.md` if the phase text now misstates the loop.
* Correct the **G3 row** in `docs/roadmap/outstanding-work.md`'s T7 reference when you mark it done
  (gate E), not now.

**Commit:** `docs(promptcadence): the per-step retry in the lifecycle, the spec and the error ladder`.

## 7. Gate C — the record shape

* Migration `0008`: `plan_steps.attempt` (and a `step_attempts` table only if the ADR chose (c)).
  Nullable-or-defaulted so existing rows are valid; SQLite **and** PostgreSQL (ADR-0006) — the
  batch-alter idiom `0007` uses.
* `EventType.STEP_RETRIED = "step.retried"` in `domain/events.py`, with its payload in
  `domain/dispatch.py` beside `step.started`/`step.completed`, carrying the attempt number, the
  cause and the tier. It is written **in the same write that starts the retry** (ADR-0044).
* `[execution] step_retries` in `config.py`, defaulted, rendered into the shipped config's comments
  the way `corrective_retries` is at `:768`.
* Tests: the migration round-trips on both backends; the event's payload is asserted by golden; the
  setting's default is pinned.

**Commit:** `feat(record): a step's attempts, and the step.retried event`.

## 8. Gate D — the loop, on both paths

* The retry sits where the ADR put it relative to escalation. **Do not fork the turn body**: a
  retried turn goes through the same pre-flight order (ADR-0073), the same debit, the same
  `compare()`. A `if retrying:` branch inside governance is the two-source design D-12 collapsed.
* Counted against `max_turns_per_step`. A step that exhausts its turns is `turn_overrun` and that
  is not a retry — keep the two distinguishable in the record, since G1 noted `turn_overrun` has no
  loop-level test today (`docs/history/G1_HANDOFF.md` §15c) and this row is the first thing that could confuse
  it.
* **The bypassed loop's synthetic step retries the same way.** Same code path, not a parallel one.
* The halt after the last attempt names **the last cause and every attempt**. Test the halt's text.
* Tests: a retryable failure retried and then succeeding; retried and then exhausting the budget
  (the halt's cause and its attempt list asserted); a governance refusal **not** retried; an egress
  denial **not** retried; a deviation halt **not** retried; the escalation-vs-retry order asserted
  in the order the ADR chose; the debit landing for every attempt; the intent revision unchanged
  across attempts.

**Commit:** `feat(loop): a failed step retries under the same intent, on both paths`.

## 9. Gate E — the proof

1. **Contract 1 green with no new allowance.** `tests/contract/test_governance_invariance.py`. If
   the diff moves, that is the row's most important finding and it stops the gate — do not widen the
   allowance list to pass (`docs/history/G1_HANDOFF.md` §5: the list is closed, a new difference is a finding).
2. **A demonstration a person can read.** The fake LoadCoach can produce the failures this row
   retries, so the primary demonstration is scripted and deterministic: show the event stream of a
   trajectory whose step fails twice and completes on the third attempt, and one that exhausts its
   budget and halts — with the halt's cause and its attempt list. Put both verbatim in the handoff.
3. **One live run if the stack is up.** Not required by the row, and not worth standing the stack up
   for on its own — but if G2 left LoadCoach + Ollama running, a real `ALL_CANDIDATES_FAILED`
   retried on the real stack is worth the ten minutes and is the strongest evidence in the handoff.
4. Full gate; `docs/` and mirror `cmp`-identical.

**Commit:** `test(loop): the retry's record, on both paths, with contract 1 unchanged`.

## 10. Exit conditions — all of these, demonstrably

1. **One ADR**, accepted, taking all three of §0.2's decisions and §0.3's record shape, with its
   refusals stated.
2. `lifecycle.md` §4.3/§5/§8 and `spec.md` §13 amended **before** the code, and the T7 error
   corrected wherever it appears.
3. A retryable failure is retried up to `[execution] step_retries`; a governance refusal, an egress
   denial and a deviation halt are **never** retried — each asserted by its own test.
4. A retry is a new turn under the **same intent revision**, on the step's thread, counted against
   `max_turns_per_step`, and **debited**.
5. `plan_steps.attempt` and a `step.retried` event, written in the write that starts the attempt.
6. The halt after the last attempt names the last cause **and every attempt**, asserted on its text.
7. The bypassed path retries identically, and **contract 1 is green with no new allowance**.
8. Full gate green, interpreter and exact invocations named; `docs/` and mirror `cmp`-identical.

## 11. Closing duties

1. Full gate; interpreter and exact invocations named (M5C-13).
2. **`G3_HANDOFF.md` at the workspace root**, house shape: the gate results; each of §0.2's three
   decisions and §0.3's record-shape choice, with the reason and what the losing option would have
   made the record claim; the verbatim demonstrations; **an I1 note** saying exactly how the
   explanation reads a retry back and whether `materialize(rows) == compose_live(rows)` has any new
   hazard in these rows; whether `turn_overrun` and a retry are distinguishable in the record;
   **and anything this prompt said that turned out not to be true**.
3. Update the **G3 row** in `docs/roadmap/outstanding-work.md` to Done — date, commits, what held,
   what did not — **and correct its T7 reference** (§0).
4. Note for the operator: the `0.9.0b0` changelog's *Known limitations* names the unbuilt step
   retry; it comes out at the **next** release, not this row.
5. Reviewed, not overnight: one commit per gate, each message saying what it made true.
6. Record any **model deviation** from the scheduled Opus 5 · high
   ([model-assignment §3.5](docs/roadmap/model-assignment.md)).

## 12. Stop rules

* **Do not retry a decision.** A governance refusal, an egress denial and a deviation halt are
  outcomes, not accidents. This is the whole line the ADR draws; a "just this one case" exception
  is the breach.
* **Do not mint a new intent for a retry, and do not widen one** (ADR-0056). Same revision, or the
  record stops meaning what it says.
* **Do not fork the turn body** or branch governance on whether a turn is a retry.
* **Do not widen the contract-1 allowance list** to make the diff pass (`docs/history/G1_HANDOFF.md` §5).
* **Do not make the retry a constant.** It is configuration, per the row and the
  `corrective_retries` precedent.
* **Do not change the escalation's meaning.** A scoped re-approval stays a scoped re-approval
  (ADR-0049); the row orders retry and escalation, it does not merge them.
* **Do not relitigate G1's closed decisions** (`docs/history/G1_HANDOFF.md` §13): the bypass grant supersedes;
  the planner's spend is on the `plans` row, not the ledger; `observed_classification` is the
  intent's ceiling; the remote-provider fact is a seam with a safe default.
* **Do not touch LoadCoach, ModelRack or Commissioner**, and do not widen any `setspec` pin.
* **Do not bump, tag or publish. Do not `git push`.**
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a gate boundary.

## 13. If you finish with capacity left

Read-only, in priority order: (a) the **I1 readiness note** above, extended — which rows the
explanation composes for a retried step and in what order it must read them; (b) whether
`turn_overrun` can now be reached by a loop-level journey (G1 says it is domain-tested only,
`docs/history/G1_HANDOFF.md` §15c) and what the cheapest such journey is; (c) whether anything in §0.2's
retryable set should have been a LoadCoach-side behaviour instead — if G2's cleaner failure
semantics make a class of retry unnecessary, say so, because the smaller policy is the better one.
