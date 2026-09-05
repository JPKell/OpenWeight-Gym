# Kickoff — G1: PromptCadence Phase 7 — Planner, approval modes, DAG dispatch, and the governance-invariance proof

**Row:** G1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Fable 5 · xhigh**, as scheduled ([model-assignment §2.10](docs/roadmap/model-assignment.md)).
Design-dense, with a live-model interaction and the arc's central proof.
**Repositories:** `/home/jpk/ai/suite/PromptCadence`, then `/home/jpk/ai/suite/docs`.
**Ships:** **`promptcadence 0.9.0b0` — the M11 beta, and the package's first PyPI release.**
The version bump and the changelog release section are yours; **the tag, the push and the `pypi`
environment approval are the operator's** (§12).
**Overnight:** **no.** [§2.12](docs/roadmap/model-assignment.md) puts batch G on the never-overnight
list — this row is won by review and its failures are quiet. Daytime, reviewed same day.
**Runs after:** F2 (Phase 6, done) and F4 (LoadLedger P3, done — the soft edge is satisfied).
**Not in this session:** the composed `promptcadence.trajectory_explanation` document, the operator
UI, compaction (all **P8**, and see §0.4); hardening and the injection corpus (**P9**).

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **PromptCadence `main` is at `de8d918`**, clean and level with `origin`. **docs `main` is at
  `7a4bddd`**, clean and level. LoadCoach (`dfbf2d8`), Commissioner (`72b789b`) and ModelRack
  (`5f8cd5d`) are clean, level, and none of them is yours this row. **Confirm** `git status -sb` in
  every repo you touch at the start and at the end (CLAUDE.md, working-tree integrity).
* **Resolved dependencies in the venv:** `setspec 0.5.0`, `commissioner 0.1.0`, `loadledger 0.2.0`,
  `toolyard 0.1.0`, `baseaicore 0.4.1`, `mirrorwall 0.2.2`. Python **3.13.15**; there is **no
  python3.12** on this host. Name the interpreter and every exact invocation (M5C-13).
* **`setspec` resolves to 0.5.x by design, not by regression.** `commissioner 0.1.0` pins
  `setspec>=0.5,<0.6` and caps the resolution even though PromptCadence's own range admits 0.6.
  H4 widens Commissioner and publishes `0.1.1`. [outstanding-work §3](docs/roadmap/outstanding-work.md)
  wrote that note specifically so this row would not read it as a defect. **Do not widen anything.**
* **`promptcadence` is unclaimed on PyPI** (`GET /pypi/promptcadence/json` → 404 today). The first
  publish claims the name. `__about__.py` still says `0.1.0`; `.github/workflows/release.yml` exists.
* **`tools.plan` is a real, shipped LoadCoach profile** — E4 added the five harness profiles and a
  running LoadCoach reports `tools.plan  16384  allow_remote_providers=False`
  (`docs/history/E4_HANDOFF.md` §3). You are not inventing the planning profile; you are calling it.
* **Ollama is installed and running** on this machine with at least one model pulled. **No LoadCoach
  is listening on 8766** as this was written — the demonstration in §10 needs you to start one.
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and the release
  approval to the operator. Do not run a push dry-run either.

## 0.1 Most of this phase's *domain* already exists. Read it before you write a line of it

P2 built the hard, pure half of Phase 7 and it is tested. The row's real content is services, the
loop, the surfaces, and the proof. If you find yourself designing a plan schema or an approval
verdict, stop and go read these:

| Already built | Where |
|---|---|
| `PLAN_SCHEMA`, `plan.schema.json` and their byte-identity golden, `validate_plan_document`, `PlanIssue`/`PlanIssueReason`, `Plan`/`PlanStep` with the verbatim-source digest, all five §4.1 rules | `src/promptcadence/domain/plan.py` |
| `ApprovalPolicy` with its **derived** `version` (config digest × `APPROVAL_RULESET_DIGEST`) and the fixed corpus that pins it | `domain/policy.py:303`, `tests/unit/test_domain_policy.py:545` |
| `evaluate_gates`, `requires_human_approval`, `evaluate_step`, `evaluate_plan`, `GateVerdict`, `StepVerdict`, `PlanVerdict`, `VerdictReason` | `domain/policy.py:516`–`:860` |
| `PlanApproved`, `PlanRejected`, `ApprovalRequested`, `ApprovalGranted`, `ApprovalDenied` events | `domain/policy.py:856`–`:1011` |
| `mint_for_step`, `mint_bypass_default`, `supersede`, `MintKind`/`MintedBy`, `GOVERNED_INTENT_FIELDS`, `RECORD_INTENT_FIELDS`, and `_mint` — the single construction point that evaluates the gates and resolves the egress class | `domain/intent.py` (`_mint` at `:668`) |
| T2–T10 transition helpers: `claim_for_planning`, `approve_plan`, `request_approval` (T5 **and** T10), `reject_plan`, `grant_approval`, `deny_or_time_out_approval` | `domain/trajectory.py:496`–`:693` |
| The tables: `plans`, `plan_steps`, `plan_approvals`, `approval_requests`, `execution_intents` | `infrastructure/db/models.py:335`–`:471`, migration `0002` |
| `[planning]`, `[approval]`, `[execution]` settings, including `request_timeout_hours` and both hybrid gates | `config.py:194`–`:262` |

`compare()` and the whole deviation matrix are P2/P4/P6 work and **do not move**
(`docs/history/F2_HANDOFF.md` §11): G1 changes *who mints the intent*, not what a turn is checked against.

## 0.2 What is actually missing — including one thing that is missing quietly

1. **The planner.** No `services/planner.py`, no prompt record, no `prompts/` package at all
   (`find src -name '*.json'` returns only `domain/plan.schema.json`).
2. **Approval as a service.** Nothing writes `plans`, `plan_steps`, `plan_approvals` or
   `approval_requests`; nothing reads a pending request; no timeout clock runs.
3. **The planned loop.** `services/loop.py` is the bypass path only. There is no ready-set, no
   per-step intent, no step dispatch.
4. **The surfaces.** `POST /trajectories/{id}/approve|deny`, `GET /approvals`,
   `promptcadence approvals list|approve|deny`, and `promptcadence tiers check` — E4 left the last
   one to this row deliberately (`docs/history/E4_HANDOFF.md` §4). `web/routes/system.py:109` hard-codes
   `"pending_approvals": []` with a comment naming Phase 7.
5. **Quietly missing — and the one a green suite will not tell you about: the bypass path
   evaluates its approval gates and then ignores the answer.** `mint_bypass_default` funnels
   through `_mint`, which calls `evaluate_gates` and stores the verdict on the intent, and
   `requires_human_approval` already documents that *"gates fire on the bypass path too
   (ADR-0048): the mode is a property of what the intent permits, not of how the work was
   planned"*. But `services/loop.py` touches `intent.gate` in exactly two places — `:2271` and
   `:2300`, both of them **recording** it. Under `approval.mode = "manual"` a bypassed trajectory
   executes today without any human ever being asked. Lifecycle §4.2 says it must not:
   *"In bypass mode the same gates fire too — at the minting of the default intent and at every
   re-mint a drift triggers … bypass removes planning, never approval of gated egress."*
   **Fixing this is part of Gate B, and it is a governance hole, not a feature request.**

## 0.3 The decision §0.2(5) forces you to take, and to record

The state machine is closed — [lifecycle §8.2](docs/apps/promptcadence/lifecycle.md): *"No
transition exists that this table does not list."* The rows you need already exist: bypass claims
`queued → executing` (**T3**, minting the default intent), and `request_approval()` serves **T10**
from `executing` for "a gated step becomes ready". So a gated bypass trajectory is T3 then
immediately T10, and nothing needs amending.

What is **not** written down is what the grant produces. Two candidate readings, and you must pick
one, implement it, and say which in the handoff:

* the T3 intent stands and the grant simply releases the park — but then the executed intent's
  `approval_request_id` is `None` and `minted_by` says `bypass_default`, and lifecycle §4.3's
  *"the human grant, when one gated it"* is not in the record; or
* the grant **supersedes** it — revision 2, `minted_by = approver` with the token identity,
  `approval_request_id` set, revision 1 retained as the gated envelope nobody executed under.

The second is what §4.3's immutability rules describe (*"nothing is edited"*, *"the audit trail
holds every envelope a turn ever ran under"*) and `supersede()` already exists for it. Take it
unless you find a reason not to, and either way: **no turn may execute under an intent whose gate
fired and whose grant is not in the record.** That is the assertion to write first.

## 0.4 What "spec §20 #2 passes" means at this row, and what it does not

Phase 7's acceptance criterion 1 lists **§20 #2, #3, #7, #8**. Criterion #2 ends with *"a result
plus a retrievable explanation naming every model, tier, tool call, debit and egress verdict"* —
and Phase 8's acceptance criterion 1 is *"**Spec §20 #2's explanation clause** holds against the
golden"*. The clause is split across the two phases on purpose.

**At G1**: the record must be *retrievable through the surfaces that exist* — `GET /trajectories/{id}`,
`/turns`, `/egress-decisions`, `/ledger`, the SSE event stream, plus the new plan and approval
surfaces. **Do not build** `ExplanationBuilder`, the `promptcadence.trajectory_explanation` schema,
`GET /trajectories/{id}/explanation` or `promptcadence trajectory explain`. Shipping an early
document schema commits ADR-0035 namespace surface that P8 then has to break. Say plainly in the
handoff which half of #2 you demonstrated.

## 0.5 The corrective budget has no configuration key

Lifecycle §4.1 says the planner has a *"bounded corrective retry (default 2)"*. Spec §12's
`[planning]` block has no key for it and `PlanningSettings` has no field. Add
`corrective_retries = 2` to `[planning]` — settings model, the shipped TOML reference in
`config.py`, and spec §12 in the same commit — or hard-code the bound and argue why. A bound that
lives only in code is the bound that gets changed in code. Whichever you choose, it is an additive
config edit, not an ADR: **do not open one for it.**

---

## 1. Setup

```bash
cd /home/jpk/ai/suite/PromptCadence && source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show setspec commissioner loadledger toolyard | grep -E "^(Name|Version)"
git -C /home/jpk/ai/suite/PromptCadence status -sb
git -C /home/jpk/ai/suite/docs status -sb
```

Every scratch database, config file, workspace and log goes in the session scratchpad — **never**
the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory. Nothing at the workspace root is versioned; do not overwrite a
  root file you did not create.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional
  Commit per gate**, committed at each gate boundary.
* `pytest-randomly` is on; a seed-only failure is a real bug, not a flake.
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names, keyword-only optionals and booleans, frozen slotted value objects, pydantic wire
  models, SQLAlchemy models never leaving the repository layer, `mypy --strict`, line length 100.
* `web → cli → services → domain`; `domain` imports no framework and no `httpx`. Handlers call one
  service method and render. Never weaken `.importlinter` to make an import work.
* Async at the HTTP edge only (ADR-0003); SSE, never WebSockets (ADR-0004).
* A state change and its event are **one write** (ADR-0044) — this row adds eight event types.
* **Never `git add -A`.** Stage named paths. Any workspace `docs/` edit is mirrored into
  `PromptCadence/docs/` byte-identically and **`cmp`-proved**.

## 3. Reading list, in this order

1. `docs/apps/promptcadence/development-plan.md` **Phase 7** — the work list, the test list, the
   two acceptance criteria, the named risk and its levers. It is this row's specification.
2. `docs/apps/promptcadence/lifecycle.md` **§4 in full** (§4.1 the plan and its five rules, §4.2
   approval and the three modes, §4.3 the `ExecutionIntent` field list and its four load-bearing
   rules) and **§8.4** (DAG dispatch, the disjoint-surface rule), plus **§8.1–8.3** for the states,
   T1–T17 and the `planning` recovery edge.
3. `docs/apps/promptcadence/spec.md` **§11 contract 1** (the invariance claim you are proving),
   **§7.1/§7.2** (the exact route and command spellings), **§12** `[planning]`/`[approval]`/
   `[execution]`, **§13** (`PLAN_INVALID`, `PLAN_DRAFT_FAILED`, `NO_ELIGIBLE_MODEL` → fallback →
   `tier_escalation`), **§17** (the event list and `GET /system/status`), **§20 #2, #3, #7, #8**.
4. **ADR-0049** (= D-5, approval is a mode with its own scope, and silence never grants it),
   **ADR-0048** (= D-4, the bypass removes planning, never governance), **ADR-0056** (= D-12, one
   immutable intent per turn), **ADR-0047** (= D-3, a tier is configuration and a model never sizes
   its own budget — the planner's `expected_turns` is *advisory*), **ADR-0041** (a caller's schema
   does not travel through a router), **ADR-0051** (a plan never leaves PromptCadence),
   **ADR-0012** (prompts are versioned JSON records), **ADR-0044**, **ADR-0073** (the pre-flight
   order egress → pricing → availability → budget, which the planned path must keep).
5. `roadmap/promptcadence-roadmap.md` **§9 I11** and **§3's M11 exit condition**.
6. Handoffs, for what they left you: **`docs/history/F2_HANDOFF.md` §11** (what G1 inherits, and why the
   deviation matrix golden is the invariance baseline), **`docs/history/F4_HANDOFF.md` §11–12** (what G1 must
   not relitigate about the ledger, and the per-tier column it can now build),
   **`docs/history/D2_HANDOFF.md` §3–4** (the bypass loop, leases, CAS fencing, and the T2→T7 stub you replace),
   **`docs/history/E4_HANDOFF.md` §3–4** (the five task profiles; `tiers check` left to you).
7. Precedent to copy, not re-invent: `IdeaPress/src/ideapress/prompts/` (manifest + versioned
   stage records) and `IdeaPress/src/ideapress/services/plan.py` (schema-validated JSON with a
   deterministic gate after it — the ADR-0041 pattern this row repeats).

---

## 4. The shape of the work — six gates

A → the planner drafts and validates. B → approval decides and mints, in all three modes, on both
paths. C → the loop executes per DAG. D → the proof. E → the surfaces. F → the demonstration and
the version. The order matters: **D compares what A–C produce against what already exists**, so it
cannot be written first, and it must not be written to pass.

## 5. Gate A — the planner

* `services/planner.py`: call LoadCoach under the **`tools.plan`** profile with
  `response_format` JSON, validate with `domain.plan.validate_plan_document` — **PromptCadence's
  own schema, never handed to LoadCoach** (ADR-0041) — and retry correctively within the §0.5
  budget, feeding back *every* issue at once. `plan.py`'s module docstring already explains why it
  reports them together: a two-attempt budget is spent immediately by a validator that reports one
  problem at a time.
* **The planner prompt is a versioned JSON record** (ADR-0012), and so is the structured-output
  corrective (spec §9). Create `src/promptcadence/prompts/` with a manifest, mirroring IdeaPress.
  No prompt text as a Python string literal, anywhere.
* Persist the plan **verbatim alongside its validated form** — `Plan` already refuses to exist if
  its digest does not match its source text; the `plans` row must carry both.
* T2 (`queued → planning`) and, on exhaustion of the corrective budget, **T7** with
  `PLAN_DRAFT_FAILED`. The stub D2 left — *"planning is not available before Phase 7"* — is
  replaced here. Grep the tree for `Phase 7` and `before Phase 7` and make sure no stale
  placeholder string survives in code, tests, `doctor` output, route docstrings or the shipped
  config comments.
* **The `planning` recovery edge becomes real** (lifecycle §8.3): re-claim, cancel any in-flight
  LoadCoach plan job, discard the partial draft and **redraft** — drafting has no side effects to
  reconcile. Its last line, *"Until the planner exists (Phase 7), a `planning` lease found at
  recovery is T7 with the cause rather than a redraft"*, expires with this gate; amend it in docs.
* An empty plan is invalid — *emptiness cannot pass a gate* (the IdeaPress M7 lesson, and it cost a
  whole verification round there).

## 6. Gate B — approval in three modes, and minting as its output

* `PlanApprover` service over P2's pure `evaluate_plan`: persist `plan_approvals` (one verdict per
  step, with the reason), the trajectory-level verdict, and `approval_policy_version` from
  `ApprovalPolicy.version` — **derived, never declared**; do not add a hand-set field.
* **`auto`** → T4, every intent minted in the same write as `plan.approved`. **`manual`** → T5,
  every plan held. **`hybrid`** → auto-approve except gated steps, which pause the trajectory *at
  the point the gated step becomes ready* (T10), so ungated earlier steps may already have run.
  That last clause is a scheduling requirement, not a description — a hybrid trajectory that parks
  before running its ungated steps has implemented the wrong thing.
* **Gates are evaluated at minting against the MOST permissive tier in the intent's set**
  (`_mint` does this already) — *"so a pre-approved fallback cannot smuggle egress past a hybrid
  gate"*. Test it with a `local_*` primary and a `remote_*` fallback: it must gate.
* **Wire the bypass gate** (§0.2(5), §0.3). T3 then T10 when the default intent's gate fires; the
  grant supersedes. `manual` + `--bypass-planning` must park, and a test must assert it does.
* `approval_requests`: exactly one pending per trajectory (ADR-0049 rule 6 — a trajectory parked
  with no request is one nobody can release), the `request_timeout_hours` clock **persisted, not
  process state**, and expiry → T9 `halted` with the timeout recorded. Grants are **idempotent per
  request** (spec §7.1) and require the **`approve` scope**, which is deliberately not `write`.
* **Scoped re-approval** — the P4/P6 halt (*"scoped re-approval is not available before Phase 7"*)
  becomes real: a drift whose disposition is `scoped_reapproval` raises a request for **that step
  only**, and the grant mints revision *n+1* superseding the old, both retained, `supersedes` set.
  `reapproval_scope` (`on_tier_or_classification_change` | `any_deviation`) selects which drifts
  qualify. A tool outside the *trajectory* allowlist stays refused and **never re-approvable** —
  F2 pinned that with a test; it must still pass.

## 7. Gate C — the planned loop and DAG dispatch

* Ready-set dispatch over the plan DAG: a step is ready when every dependency has committed.
  `max_concurrent_steps = 1` by default; above 1, concurrency is granted **only across disjoint
  execution surfaces** — at most one local step in flight *ever* (ADR-0038 makes two a queueing
  fiction), plus up to `max_concurrent_remote_steps` remote ones.
* **Record the DAG even when execution is serial**, so the explanation can later show what could
  have run in parallel (lifecycle §8.4).
* Each step runs under its own intent through the existing `TierRouter` path. The turn body,
  pre-flight order (ADR-0073), debits, egress evaluation, subject verification and `compare()` are
  **unchanged** — reuse them; do not fork a planned variant. If you find yourself copying the turn
  loop, that is the signal the seam is in the wrong place.
* Per-step budget slices come from the estimator F1 built, with their labelled sources — a model's
  `expected_turns` is advisory and **never sizes its own budget** (ADR-0047).
* `NO_ELIGIBLE_MODEL` → the intent's next `fallback_tier`, else a `tier_escalation` deviation
  (scoped re-approval) or halt, per spec §13. This is the row where those cells stop being "halt
  with the cause".
* Kill −9 mid-step must still recover: leases, CAS fencing and `source_ref`-idempotent debits are
  D2/F1 machinery — extend the reconciliation to the multi-step case, do not rebuild it.

## 8. Gate D — contract 1, the governance-invariance diff (I11)

**This is what the row is for.** Everything above is the apparatus.

* One scripted task, run twice against the fake LoadCoach — once planned, once `--bypass-planning`
  — and diff the **record shapes**. They must be identical except for the `plan` and
  `plan_steps`/`plan_approvals` rows. Not "similar", not "equivalent modulo": the test names the
  permitted difference set and fails on anything else appearing in it.
* Per `docs/history/F2_HANDOFF.md` §11, every turn already carries an egress decision in both modes, and
  `deviation_matrix_bypass.json` is the baseline: *"when a planner mints the intent, those rows must
  not move — only `intent_id` and the `minted_by` kind may."* Encode that as the diff's allowance
  list, and make the failure message say which field moved.
* Prove the structural half too: **there is no code path that executes a turn without an intent.**
  A test that walks the dispatch entry points, or an assertion at the single turn entry, is worth
  more than the diff alone — the diff shows two runs agreed, the assertion shows they had to.
* **A failed pass here invalidates the design claim, not just the code** (the row's "why this
  model"). If the two records genuinely cannot be made to match, that is a finding to write up in
  the handoff and take to the operator — **not** something to fix by widening the allowance list.
  Widening it silently is the one failure mode this gate exists to prevent.

## 9. Gate E — the surfaces

* HTTP: `POST /trajectories/{id}/approve`, `POST /trajectories/{id}/deny` (`approve` scope,
  idempotent per request), `GET /approvals`.
* CLI: `promptcadence approvals list`, `promptcadence approve <id>`, `promptcadence deny <id>
  [--reason …]` — the spellings in spec §7.2, not near-misses.
* `promptcadence tiers check` and the `doctor` task-profile check: every configured tier's profile
  must resolve in the running LoadCoach. E4 left this here; `tools.plan` is now one of the profiles
  that must exist.
* **`GET /system/status` loses its placeholder**: `pending_approvals` with ages, and today's ledger
  position against the daily ceiling and each configured project's ceiling (spec §17). Build the
  per-tier column against `tiers[].tokens_spent` / `money_spent` and the rendered strings beside
  them — `docs/history/F4_HANDOFF.md` §11–12 says exactly what not to re-derive: **a tier has a balance, not
  headroom; nothing about it can be `exceeded`; `—` is not `$0.00`; money is per currency and never
  summed across currencies.**
* Every new event type from spec §17 (`plan.drafted`, `plan.approved`, `plan.rejected`,
  `approval.requested`, `approval.granted`, `approval.denied`, `intent.minted` on the planned path,
  `step.started`, `step.completed`) is persisted in the **same write** as its transition, and
  replayable from `Last-Event-ID`.
* Docs last, in the workspace `docs/` first, then mirrored and `cmp`-proved: the Phase 7 deltas,
  the §8.3 recovery amendment (§5), the §12 config addition (§0.5), and anything §0.3 decided.

## 10. Gate F — the demonstration, then the version

The M11 exit condition is a **demonstration on real LoadCoach + Ollama**, not a green suite:

> one planned and one bypassed trajectory, tools + budget + egress active in both, records identical
> in shape minus plan rows; a confidential trajectory provably cannot reach a remote tier.

* Start a real LoadCoach on 8766 against Ollama (nothing is listening today) and run both
  trajectories through the CLI with `--follow`. Capture the output verbatim into the handoff.
* **Plan-schema resilience against a real local model** is a marked `live` test and it is the risk
  the development plan names: *"local models drafting unusable plans."* The levers, in order, are
  the corrective budget, the `tools.plan` profile's constraints, and — only if needed — a simpler
  fallback plan shape (a single linear step list). **A persistent failure is finding-grade input to
  the future `native.plan` benchmark, not something to paper over**: if a small local model cannot
  produce a valid plan, say so with the transcript, and do not loosen the schema to make it pass.
  Loosening §4.1's rules is a governance change, and three of them are classification and allowlist
  rules.
* This is also the run the ops checklist has been waiting for: with the shipped defaults and **no**
  `PROMPTCADENCE_TIERS__*` overrides, a real model exercises `length` and `content_filter`
  finish reasons that the fake provider (always `stop`) never has.
* **Only after the demonstration passes**: bump `__about__.py` to `0.9.0b0`, close the changelog's
  `## [Unreleased]` into a `## [0.9.0b0]` release section, commit. *"Cut at the demonstration, not
  before."* If the demonstration cannot be run — no Ollama, no model, LoadCoach won't start — **stop
  before the bump**, leave `## [Unreleased]` as it is, and say so in the handoff. A beta tagged on a
  suite that passed with the fake is not the M11 exit condition.

## 11. Exit conditions — all of these, demonstrably

1. Spec §20 **#2** (minus the explanation clause, §0.4): `promptcadence run "…"` plans, is
   auto-approved, executes on a local tier with sandboxed tools, and returns a result.
2. Spec §20 **#3**: the same task with `--bypass-planning` produces a record identical in shape
   minus the plan and approval rows — **by the contract-1 diff test**, not by inspection.
3. Spec §20 **#7**: with `approval.mode = "hybrid"`, a step needing `internal` egress pauses,
   appears in `promptcadence approvals list`, and a `deny` halts with the denial recorded.
4. Spec §20 **#8**: an `undeclared_tool` deviation gets a scoped re-approval that mints a
   superseding revision **for that step only**, with both revisions retained and visible.
5. `manual` mode holds a **bypassed** trajectory (§0.2(5)) — the hole is closed and a test says so.
6. A gated fallback tier cannot smuggle egress past a hybrid gate (§6).
7. Planned journeys: auto-approved; hybrid pausing at the gated step; manual deny; approval
   timeout; redlined substitution; scoped re-approval; a parallel local+remote DAG pair under the
   concurrency rule.
8. `promptcadence tiers check` and `doctor` verify every profile including `tools.plan`;
   `GET /system/status` reports real pending approvals and a real ledger position.
9. No `before Phase 7` / `not available before Phase 7` string survives anywhere in code, tests,
   CLI output or docs.
10. Full gate green, interpreter and exact invocation named; the suite still passes with **no
    LoadCoach, no GPU and no network** (§20 #10).
11. The live demonstration run, captured verbatim; `0.9.0b0` in `__about__.py` and the changelog
    **iff** it passed.
12. Both trees clean and committed (not pushed); `docs/apps/promptcadence/{spec,lifecycle,
    development-plan}.md` `cmp`-identical between the workspace and the repo mirror.

## 12. Closing duties

1. Full gate, interpreter and exact invocations named (M5C-13).
2. **`docs/history/G1_HANDOFF.md` at the workspace root**, house shape: the gate results; the §0.3 decision and
   why; the §0.5 decision and why; the contract-1 diff's permitted-difference set and how it fails;
   what the live plan-schema run actually produced (transcript, not summary), and whether the
   `native.plan` finding needs writing up; what P8 inherits (the explanation clause, the UI, the
   compaction trigger) and what I2 inherits; **and anything this prompt said that turned out not to
   be true** — that section has been the most useful part of the last four handoffs.
3. **The release is the operator's.** State exactly what is left: push PromptCadence and docs,
   tag `v0.9.0b0`, approve the `pypi` environment **once** (a single tag push fires two Release
   runs — approve one, cancel the other, per outstanding-work §4), post-publish install check in a
   clean venv. Also remind them that M11's other exit condition is unmet and not yours:
   **`pytest -m isolation -rs` green on a real podman host** — a skip is visible and is not a pass.
4. This row is **reviewed, not overnight**: leave a diff a reviewer can read — one commit per gate,
   each message saying what it made true.
5. Record any **model deviation** from the scheduled Fable 5 · xhigh for
   [model-assignment §3.5](docs/roadmap/model-assignment.md).

## 13. Stop rules

* **Do not fork the turn loop.** The planned path reuses P3–P6's turn body, pre-flight order,
  debits, egress evaluation and `compare()`. A `if planned:` branch inside governance is the exact
  two-source design D-12 collapsed.
* **Do not make anything about governance conditional on planning mode** (ADR-0048). This is the
  design's load-bearing wall and this is the row that could quietly breach it.
* **Do not widen the contract-1 diff's allowance list to make it pass** (§8). A genuine mismatch is
  a finding for the operator.
* **Do not loosen `PLAN_SCHEMA`'s five rules** to accommodate a weak local model (§10). A simpler
  *plan shape* is a permitted lever; a laundered classification is not.
* **Do not hand the plan schema to LoadCoach** (ADR-0041), and **do not let a plan leave
  PromptCadence** (ADR-0051) — the egress decision is the only shape that travels.
* **Do not let a model decide control flow.** The plan is a proposal Python validates, approves and
  dispatches; `expected_turns` is advisory (ADR-0047).
* **Do not build the explanation document, the operator UI or compaction** (§0.4 — all P8).
* **Do not add a field to `TurnFacts`** or a new deviation category; both are governance dimensions
  needing an ADR (`docs/history/F2_HANDOFF.md`'s stop rule, still in force).
* **Do not widen any `setspec` pin** (§0), and do not touch LoadCoach, Commissioner or ModelRack.
* **Do not `git push`, tag, or publish.** Commit only.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a gate boundary.

## 14. If you finish with capacity left

Read-only, in priority order: (a) an **I1 readiness note** — which record rows the explanation
builder will need to compose and which of them this row made exist, and whether
`materialize(rows) == compose_live(rows)` has any hazard in the plan/approval rows specifically;
(b) a note on what the injection corpus at P9 should target given how the planner consumes model
output — the plan document is untrusted input and this row is the first place it steers dispatch;
(c) which lifecycle §5 deviation categories still have no test, now that scoped re-approval exists.
