# D2 addendum — the `finish_reason` gap closed, and the live journey run

**Row:** D2 of `docs/roadmap/outstanding-work.md` §1, continued. **Model:** Fable 5.1 · xhigh,
attended. **Date:** 2026-09-03. **Supersedes nothing** — read `docs/history/D2_HANDOFF.md` first; this file
records what changed after it, on the operator's decisions below. Nothing pushed, tagged,
published or version-bumped in any repository.

| Repository | Was | Now | Pushed |
|---|---|---|---|
| `/home/jpk/ai/suite/LoadCoach` | `01170a7` | `846348b` (one commit) | no |
| `/home/jpk/ai/suite/PromptCadence` | `321e9d3` | `cb6dbf2` (three commits) | no |
| `/home/jpk/ai/suite/docs` | `9edec2f` | `2acd08a` (two commits: `97f8826` the wire docs, `2acd08a` the E4 tier-defaults row) | no |

---

## 1. The decisions the operator made (interview, this session)

1. **Change LoadCoach and consume it.** Render `output.finish_reason` in the `/generate` response
   and the job document; teach the fake; let a free-text tier complete on a declared `stop`.
2. **Render the validation `checks` in the job document too**, so a turn reconciled after a
   crash can complete on the same facts as one read from the response.
3. **The cancel-path spec/code disagreement stays recorded**, not fixed (D2_HANDOFF §5, §8).
4. **Do not push.** Commit only.
5. **LoadCoach: changelog only, no bump, no tag.** Additive within `/api/v1`.
6. **Run the live journey** against a real LoadCoach started on this machine on the fake
   provider (`provider.kind = fake`) — done, §4.
7. **Requirements locks stay for their own row** (D2_HANDOFF §6.13).
8. **`is_remote` on the wire stays for LC-E1.**

---

## 2. Gate results

**PromptCadence** — `/home/jpk/ai/suite/PromptCadence`, `.venv/bin/python` **3.13.15**, pytest
**9.1.1**:

```bash
.venv/bin/ruff format --check .          # 81 files already formatted
.venv/bin/ruff check .                   # All checks passed!
.venv/bin/mypy src tests                 # Success: no issues found in 78 source files
.venv/bin/lint-imports                   # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                         # 707 passed, 2 skipped, 1 deselected  (ran 5× under
                                         #   random seeds, twice with a LoadCoach listening on 8766)
.venv/bin/python -m pytest -m contract -q          # 18 passed
.venv/bin/python -m pytest --cov --cov-report=term-missing -q   # TOTAL 92%  (floor 85%)
```

The 2 skipped are the PostgreSQL legs; the 1 deselected is the live journey, which **did run
separately and passed** (§4). The kill −9 tests ran in the default suite, on the shipped default
tiers now.

**LoadCoach** — `/home/jpk/ai/suite/LoadCoach`, `.venv/bin/python` **3.14.4**, pytest **9.1.1**:

```bash
.venv/bin/ruff format --check .          # 188 files already formatted
.venv/bin/ruff check .                   # All checks passed!
.venv/bin/mypy src tests                 # Success: no issues found in 168 source files
.venv/bin/lint-imports                   # Contracts: 4 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                         # 830 passed, 3 failed, 3 skipped, 15 deselected
.venv/bin/python -m pytest -q tests/contract/test_openapi_snapshot.py   # passed: docs/openapi.json unchanged
```

**The 3 LoadCoach failures are pre-existing and unrelated.**
`tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-*]`
fails because the `benchmark.evidence_bundle` 1.1 goldens carry an `adapter` field that
`CapabilityEvidenceOut` (`extra="forbid"`) refuses. Verified by `git stash` → same 3 failures on
the clean `01170a7` tree → `git stash pop`. LoadCoach's venv holds an **editable** `py/SetSpec`
(at `53d2c16`, "0.6.0 release prep"; `pip` metadata still says 0.3.0) — the adapter arc changed
the goldens under LoadCoach. That is a LoadCoach-adopts-SetSpec item, not this change; recorded in
§7.

---

## 3. What changed

### LoadCoach `846348b` — `feat(api): render the declared finish_reason and the job document's validation checks`

| Where | What |
|---|---|
| `services/execution.py` | `ExecutionOutcome.finish_reason: str \| None = None`, set from `result.finish_reason.value` in `execute()`; `as_json()` renders `output.finish_reason`. Also carried by the `job.completed` event and the streaming `result` event, which render `as_json()`. |
| `services/worker.py` | The queue worker's `_complete` sets the same field, so the async path and the sync path agree. |
| `services/queue.py` | `job_document()` renders `output.finish_reason` from the **last attempt row** and `validation` as `{performed, passed, attempts, checks}` from that attempt's stored `validations` rows (ordered by id), the shape `ExecutionOutcome.as_json` has always had. Covers `GET /jobs/{id}`, every `GET /jobs` item (the route builds items with `job_document`), and a replayed `idempotency_key`. |
| `tests/integration/test_generate.py` | Asserts `stop` on the sync body; new test scripts `FinishReason.LENGTH` and asserts `length` is rendered, not inferred. |
| `tests/integration/test_jobs_api.py` | New test: `POST /jobs` with a `length` finish → the job document, the list item, the sync response and its replay all carry `finish_reason=length` and `checks=[{kind: length, passed: true, detail: {}}]`. |
| `docs/apps/loadcoach/api.md` (mirror of workspace `docs/`) | §4 example gains `"finish_reason": "stop"` and `"checks": []`; a note defines the field's values and `validation.checks`; §5's `GET /jobs/{id}` row names both. |
| `CHANGELOG.md` | Under `[Unreleased] / Added`. No version change. |

`docs/openapi.json` is byte-identical: responses are open objects in the schema.

### PromptCadence `f3a3e44` — `feat(loadcoach): consume the declared finish_reason LoadCoach 846348b renders`

| Where | What |
|---|---|
| `tests/fakes/loadcoach_app.py` | `ScriptedGeneration.finish_reason` (default `DERIVED_FINISH`: `tool_calls` when the script requested tool calls, else `stop` — as ModelRack's own `FakeGeneration` derives it; any string verbatim; `None` = the older wire). `/generate` renders `output.finish_reason`; the job document renders it and `validation.{performed, passed, attempts, checks}`. Module docstring §"looser" bullet replaced. |
| `domain/turns.py` | The absence cause now names the LoadCoach commit and `docs/history/D2_HANDOFF.2.md`. Decision matrix and golden unchanged. |
| `infrastructure/loadcoach.py`, `services/loop.py` | Docstring/comment truth only; no behaviour change. The parser already read `output.finish_reason`; `checks_reported` still distinguishes an older LoadCoach's job document. |
| `tests/integration/test_bypass_loop.py` | `…completes_on_a_declared_stop` (was the halt test); new `…no_declared_finish_halts…` (scripts `None`) and `…truncated_answer_halts_never_flows_onward` (scripts `length`, asserts the `turn.completed` event carries `finish_reason=length`, `decision=halt`). Budget-overrun-under-default-scope now ends `COMPLETED` with the deviation recorded — the drift never decided; the finish does. |
| `tests/integration/test_recovery.py` | Runs on the shipped default tiers (text profiles). Kill-after-response now asserts **`COMPLETED`**: the reconciled turn carries `finish_reason=stop` from the job document, one job, one turn, `trajectory.recovered(reconciled_completed_job:<id>)` then `trajectory.completed`. |
| `tests/e2e/test_bypass_journey.py` | Default tiers; the journey's cause is `the provider declared finish_reason=stop`; two halt tests over HTTP (absent, `length`); the CLI halt case scripts `length` and asserts exit 5 with the cause. |
| `tests/unit/test_fake_loadcoach.py`, `tests/unit/test_loadcoach_client.py` | Rendered in both documents; `checks_reported` is `True` on a replay; the older-wire parse still returns `None`. |
| `tests/live/test_loadcoach_journey.py`, `tests/contract/test_loadcoach_contract.py` | Docstrings: what passes against which LoadCoach; why the snapshot digest did not move. |

### PromptCadence `6f8aece` — `docs: the finish_reason gap is closed by LoadCoach 846348b; mirrored amendments`

`README.md`, `CHANGELOG.md`, and the mirrors of spec §11 contract 6 and the development plan's
Phase 3 "As built" (byte-identical to workspace `docs/`, verified with `cmp`).

### PromptCadence `cb6dbf2` — `test: keep LoadCoach and tier settings for live tests; pin unreachable-LoadCoach tests to a closed port`

Two test-suite defects the live run exposed (§4). No production code.

### docs `97f8826`

`apps/loadcoach/api.md`, `apps/promptcadence/spec.md`, `apps/promptcadence/development-plan.md`.

---

## 4. The live journey — run, and what it exposed

A real LoadCoach (`846348b`) on the fake provider, a real PromptCadence, real sockets:

```bash
# LoadCoach, from /home/jpk/ai/suite/LoadCoach (Python 3.14.4)
LOADCOACH_PROVIDER__KIND=fake LOADCOACH_DATA_DIR=<scratch>/loadcoach-live \
LOADCOACH_STORAGE__DATABASE_URL=sqlite:///<scratch>/loadcoach-live/loadcoach.sqlite3 \
  .venv/bin/loadcoach serve --port 8766
# → /models lists fake/fake-model:8b-q8_0@sha256:fa4e…, provider_kind "fake" (a ProviderKind
#   member, so the provider surface has one kind and every answer resolves LOCAL)

# The wire itself, curl'd (recorded verbatim in the session):
#   POST /generate  → status completed | output.finish_reason = stop |
#                     validation = {performed: true, passed: true, attempts: 1,
#                                   checks: [{kind: length, passed: true, detail: {}}]}
#   GET /jobs/{id}  → the same two fields, the same values
#   GET /jobs?source=promptcadence → items carry output.finish_reason

# The marked live test, from /home/jpk/ai/suite/PromptCadence (Python 3.13.15)
PROMPTCADENCE_LOADCOACH__BASE_URL=http://127.0.0.1:8766 \
PROMPTCADENCE_TIERS__LOCAL_FAST__TASK_PROFILE=tools.agent \
PROMPTCADENCE_TIERS__LOCAL_LARGE__TASK_PROFILE=tools.agent \
  .venv/bin/python -m pytest -m live -q          # 1 passed

# Acceptance criterion 1 as the plan spells it (same env, plus a scratch data dir/database):
.venv/bin/promptcadence serve &                   # health: database ok, loadcoach ok
.venv/bin/promptcadence run "Reply with the single word: ready." --bypass-planning --follow
#   [1] trajectory.created … [4] turn.started  [5] turn.completed — complete
#   [6] trajectory.completed
#   state  completed   cause  the provider declared finish_reason=stop   exit 0
.venv/bin/promptcadence trajectory list           # (server) 01M1MKZ0…  completed
```

Both servers were stopped afterwards; nothing listens on 8766/8768 now. Scratch data lives only
under this session's scratchpad.

**What the run exposed — fixed in `cb6dbf2`.**

1. **The live test could never see the operator's configuration.** `tests/conftest.py`'s
   autouse `isolated_environment` cleared *every* `PROMPTCADENCE_*` variable, `live`-marked tests
   included; the base URL only "worked" because the default is 8766. Live tests now keep
   `PROMPTCADENCE_LOADCOACH__*` and `PROMPTCADENCE_TIERS__*` and are isolated in every other
   respect. Without this, the first assertion failed on the shipped tier names.
2. **The shipped default tiers name profiles LoadCoach does not ship.** PromptCadence's defaults
   are `tools.agent.local_fast` / `tools.agent.local_large`; LoadCoach ships one `tools.agent`
   profile (its `config/task_profiles.toml` has fifteen ids and none of the suffixed ones). The
   live run configures both tiers to `tools.agent` by environment. This is B4's tier-defaults
   judgment call (`docs/history/B4_HANDOFF.md` §3), now with evidence; **recorded, not chased** (§7).
3. **Three tests assumed nothing listens on 8766.** With a LoadCoach running, the two
   `test_server_boot.py` degraded-health tests and `test_cli.py`'s
   `test_health_reports_loadcoach_degraded_when_unreachable` turned green-by-luck into red. They
   now point at `http://127.0.0.1:9`, as `test_recovery.py` already did. The suite passed twice
   with the LoadCoach listening after the fix.

---

## 5. For E4 and F1 — what the fake now models (delta to D2_HANDOFF §5)

* **`output.finish_reason`** in both documents. `ScriptedGeneration(finish_reason=…)`:
  `DERIVED_FINISH` (default) → `tool_calls` if the script has `tool_calls`, else `stop`; any
  string is rendered verbatim (`"length"`, `"content_filter"`, `"unknown"`, …); `None` renders
  `null`, the wire of LoadCoach ≤ `01170a7`. The attempt entries still carry no reason — LoadCoach's
  `AttemptRecord.as_json` does not render it.
* **The job document's `validation`** is `{performed, passed, attempts, checks}`, copied from
  the generation; a job that never produced a result has `performed: false, passed: null,
  attempts: 0, checks: []` and `finish_reason: null`. Consequence for the loop: a reconciled
  completed job completes on a declared `stop`; the "carries no validation checks" note in
  `_record_turn` now fires only against an older LoadCoach, and no default test reaches it.
* **The default tiers are usable against the fake** without the schema workaround: register
  `text_profile("tools.agent.local_fast")` and `text_profile("tools.agent.local_large")`, as the
  e2e and recovery suites now do. `schema_profile("structured.answer")` remains the way to test
  contract 6's second clause (`schema_harness` in `test_bypass_loop.py`).
* The strictnesses (X-Client-Name, idempotency_key, no default profiles) are unchanged.

---

## 6. Decisions I made at edges, this session

1. **The job document's `finish_reason` is the last attempt's**, and its `checks` are the last
   attempt's rows, ordered by id (ULIDs, insertion-ordered). For a completed job the last
   attempt is the one that answered; for a failed one it is the last thing tried. `performed` is
   `validation_passed is not None`, which is how `ValidationOutcome` defines it.
2. **The fake derives `tool_calls` from a scripted tool call** rather than defaulting to `stop`,
   because a provider that requests tools declares `tool_calls`, and a default of `stop` made a
   tool-requesting turn read as complete in two loop tests — exactly the kind of quiet success
   the row forbids. `DERIVED_FINISH` is a sentinel, never rendered.
3. **A budget overrun under the default scope now ends `COMPLETED`** with the deviation row and
   event — the disposition is `continue_recorded` and the turn's own verdict (a declared `stop`)
   decides. The test was rewritten to say so; the `any_deviation` test still halts.
4. **Live tests keep only `PROMPTCADENCE_LOADCOACH__*` and `PROMPTCADENCE_TIERS__*`** from the
   real environment, not the whole prefix: the data directory stays isolated so a live run never
   writes into an operator's real database by accident.
5. **The absence cause still ends "see D2_HANDOFF.2.md"** (the unit test asserts `D2_HANDOFF`
   in it); the string on the row now names the LoadCoach commit that renders the field.
6. **LoadCoach's `api.md` example** was amended together with the code (D2_HANDOFF deliberately
   did not touch it while the field was unserved).

---

## 7. Open items, recorded and not chased

* **B4's tier defaults name profiles LoadCoach does not ship** (§4.2). **Decided by interview
  later on 2026-09-03 and scheduled at E4** (`docs/roadmap/outstanding-work.md` §1, the E4 row,
  docs commit after `97f8826`): the five harness profiles ship in LoadCoach's
  `task_profiles.toml` as E4's first commit, with the constraint values on the row; PromptCadence
  vendors and pins that file with a contract test; the fake stays an empty registry with a
  `shipped_profiles()` helper; the exit demonstration runs the live journey with no tier
  overrides. Until E4 lands, the live test's first assertion names the missing profiles.
* **LoadCoach's evidence-bundle 1.1 goldens fail against its store** (§2) — 3 failures on the
  clean tree, from the editable `py/SetSpec` at 0.6.0 prep. LoadCoach has not adopted the
  adapter-bearing evidence record. Not this row's.
* `GENERATION_CANCELLED` on `/generate`: spec says 200 with a cancelled job, code raises
  (D2_HANDOFF §5) — left as is, by decision.
* `is_remote` on the wire — LC-E1, by decision. Egress stays resolved by identity from `/models`.
* `requirements/` locks and the `security` job — own row, by decision.
* The `promptcadence` PyPI name is unreserved. The running application's `/health` reports
  application version `0.1.0`; D2_HANDOFF says this work rides `0.9.0b0` at M11 — the version
  string was not touched here, only observed.
* The ADR-0044 crash-between test and the kill −9 tests are unchanged and still pass.

---

## 8. Before the next session

1. **Push `main`** from all three: `LoadCoach` (one commit on `01170a7`), `PromptCadence` (three
   on `321e9d3`, nine on `752966f` in total), `docs` (one on `9edec2f`). LoadCoach's push carries
   a wire change; its CI will show the same 3 pre-existing evidence-golden failures if its
   runner also installs the workspace SetSpec — check what its lock pins before reading red as
   this change.
2. **Confirm CI** as D2_HANDOFF §9.2 says (contracts job, db-matrix on migration 0003, the kill
   tests binding a loopback port), plus LoadCoach's.
3. **Decide the tier defaults** (§7, first item) before E4 writes fixtures against them.
4. **A live run against a real provider** (Ollama) is still worth one operator pass: the fake
   provider declares `stop` for every answer, so `length`/`content_filter` on a real model have
   only been exercised through the fake LoadCoach and LoadCoach's own scripted provider.
5. Remember: no bump, no tag, nothing published — all three repositories.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
