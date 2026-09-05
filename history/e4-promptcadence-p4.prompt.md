# Kickoff — E4: PromptCadence Phase 4, tools under ToolYard discipline, and the five harness profiles LoadCoach ships

**Row:** E4 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1. Read that
row in full before anything else — it is the longest row in the schedule and it has already made
almost every decision this session would otherwise have to make.
**Model:** **Opus 5 · high** — an upgrade from the scheduled *Sonnet 5 · high*. Reason below;
**record the deviation in the handoff** so [model-assignment §3.5](docs/roadmap/model-assignment.md)'s
distribution does not drift silently.
**Repositories, in this order:** `/home/jpk/ai/suite/docs` (the amendments land first), then
`/home/jpk/ai/suite/LoadCoach` (Python **3.14.4**, coverage floor **85 %**), then
`/home/jpk/ai/suite/PromptCadence` (Python **3.13.15**, coverage floor **85 %**). Three repos, one
session.
**Ships:** nothing. LoadCoach's change is configuration and rides `loadcoach 1.1.0` at H2;
PromptCadence rides `0.9.0b0` at M11. **No version bump, no tag, no publish, no push.**
**Overnight:** permitted. E4 is on none of [§2.12](docs/roadmap/model-assignment.md)'s
never-overnight list (batches D, G, and I2's security half).
**Not in this session: F1 (PromptCadence Phase 5, budget).** See "Stop rules" — the boundary is
hard, and it is the single most important instruction in this document.

---

## Why Opus, and why `high` rather than `xhigh`

The row is scheduled Sonnet because *"ToolYard did the hard part"* — the refusal order, the
containment, the isolation ladder and the five built-in tools are frozen and published, and this
phase wires them into a loop whose deviation taxonomy is already built. That is true. Two things
push it up one tier for **this run**:

1. **[§3.2](docs/roadmap/model-assignment.md)'s mitigation is unavailable.** The row itself says
   *"Opus reviews the workspace-lifecycle diff"*; overnight, §2.12 voids that until morning.
   Running the writing pass at the reviewing tier buys back the pass that cannot happen live.
2. **The ordering is a security ordering.** §3 names *D1/E2 before E4* precisely because this is
   where model-directed tool calls first execute for real. A containment mistake here is quiet.

**Not `xhigh`, because there is nothing here to invent.** Every profile constraint value, every
sandbox construction rule and every contract-test assertion is spelled out — in the E4 row, in
`docs/history/D1_HANDOFF.md` §8/§13 and in `docs/history/D2_HANDOFF.2.md` §4/§7. `xhigh` is what the schedule spends on rows
where the *judgment is the deliverable* (C1's invariants, C2's discipline, C4's `ExecutionIntent`).
This row is integration against decisions already made; spend the effort on the hostile-model
journey and the workspace lifecycle instead.

---

## 0. Machine facts, verified 2026-09-03 before this prompt was written

Do not re-derive these; do check the ones marked **confirm**.

* **`toolyard 0.1.0` is published on PyPI** (so are `cutctx 0.1.0` and `loadledger 0.1.0`).
  E2's two publish blockers were cleared by the operator. ToolYard is a **normal version pin**
  here, not a path install. `commissioner` is *not* on PyPI yet (E3 stopped at the tag) — irrelevant
  to this row, but do not be surprised by it.
* **All seven repositories are clean and level with `origin/main`** — `docs` at `6494fec`,
  LoadCoach at `8ddca7f`, PromptCadence at `cb6dbf2`, ToolYard at `87e53f0`. D1/D2/D3 were pushed.
  **Confirm** with `git status --short` in each of the three you touch, at the start and at the end.
* **LoadCoach's local suite has exactly three pre-existing failures, and they are not yours:**

  ```text
  tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-full]
                                                                                              [1.1-mixed]
                                                                                              [1.1-unsupported]
  ```

  Cause: LoadCoach's venv carries the **editable workspace SetSpec** (at 0.6.0 prep, so the `1.1`
  adapter-bearing goldens exist), while LoadCoach pins `setspec>=0.4,<0.5` and CI installs
  `setspec==0.4.0` from `requirements/ci.lock` — where those goldens do not exist, which is why CI
  is green. Adopting the adapter-bearing evidence record is **H2/H4 work**, recorded in
  `docs/history/D2_HANDOFF.2.md` §7 and `docs/history/E2_HANDOFF.md` §16 row G. **Confirm the count is exactly 3 before your
  first LoadCoach commit and exactly 3 after it**, name them in the handoff, and **do not fix them.**
  A fourth failure is yours.
* **LoadCoach ships fifteen task profiles today**; `tools.agent` is at
  `src/loadcoach/config/task_profiles.toml:393`. After this row it ships twenty.
* **PromptCadence already has the shapes you are wiring.** `ToolsSettings` exists
  (`src/promptcadence/config.py:283`) with `enabled`, `workspace_root`, `read_roots`,
  `fetch_allowed_hosts`, `redact_args`. `domain/deviation.py` already carries
  `DeviationCategory.UNDECLARED_TOOL`, its `approved_tools` intent-field mapping, its severity and
  its disposition table, and `_undeclared_tools()` already splits inside/outside the trajectory
  allowlist. `services/loop.py:945` holds the Phase 3 placeholder — *"tool calls are not executed
  before Phase 4, and a requested tool that cannot run is not a completed turn"*. **P4 wires these;
  it does not redesign them.**
* **The fake LoadCoach is an empty registry by decision** and stays one. `text_profile()` and
  `schema_profile()` are at `tests/fakes/loadcoach_app.py:367` and `:393`.

---

## 1. Setup

```bash
cd /home/jpk/ai/suite/LoadCoach      && source .venv/bin/activate && pip install -e ".[dev]"
cd /home/jpk/ai/suite/PromptCadence  && source .venv/bin/activate && pip install -e ".[dev]"
```

Name both interpreters and the exact invocations in the report (M5C-13). Use the session scratchpad
for every scratch database, data directory and log — **never** the repositories, never `/tmp`
directly, never the workspace root.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory, never the workspace root. Nothing at the root is versioned.
* The finish line, per repository:
  `ruff format --check . && ruff check . && mypy src tests && lint-imports && pytest -m "not live and not performance"`
  green, `CHANGELOG.md` updated under `## [Unreleased]`, **one Conventional Commit per coherent
  unit of work**. `pytest-randomly` is on; a seed-only failure is a real bug.
* House method: docstring-first (behaviour → Google-style docstring including what the function
  *refuses* → tests → implementation), `from __future__ import annotations`, units in names,
  keyword-only optionals, injected clocks/providers/roots, `mypy --strict`, line length 100.
* Read `docs/architecture/master-architecture.md` §§1–3 and PromptCadence's gold-standards section
  before the reading list below.
* **Never `git add -A`.** Stage named paths. Commit at every boundary, not at the end.

## 3. Reading list, in this order

1. The **E4 row** of `docs/roadmap/outstanding-work.md` §1, entire — it is the specification for
   Part 1 and half of Part 2.
2. `docs/apps/promptcadence/development-plan.md` **Phase 4** (work, tests, acceptance, the decided
   workspace-retention risk).
3. `docs/apps/promptcadence/lifecycle.md` **§5** (deviation handling) and `spec.md` **§12**
   (configuration), **§14** (security), **§18** (test strategy).
4. `docs/adr/0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md` §§1–2, and
   `docs/adr/0053-a-refused-tool-call-is-a-result-not-an-exception.md`.
5. `docs/apps/loadcoach/routing.md` §§2–4 — the profile grammar and the hard constraints. A profile
   that violates the grammar is a LoadCoach startup refusal, and you will not see it until the exit
   demonstration.
6. `docs/history/D2_HANDOFF.2.md` §4 (the live journey and what it exposed), §5 (what the fake models now), §7
   (open items — the first is this row).
7. `docs/history/D1_HANDOFF.md` §7, §8 and §13, and `docs/history/E2_HANDOFF.md` §8 — **what this row must not relitigate.**
8. `py/ToolYard/src/toolyard/__init__.py`'s module docstring, then `containment.py`, `sandbox.py`
   and `tools/` signatures. The published API is the contract; read it rather than guessing it.

---

# Part 1 — the five harness profiles, in LoadCoach

**This is the first commit of the row.** PromptCadence's shipped tier defaults name
`tools.agent.local_fast` and `tools.agent.local_large`; LoadCoach ships one `tools.agent`. That gap
is why D2's live journey could only run with `PROMPTCADENCE_TIERS__*` overrides. It closes here, as
**configuration — no LoadCoach code changes.**

**Order: workspace `docs/` first, then the mirror, then LoadCoach's code and tests.** The mirrored
copies under `LoadCoach/docs/apps/loadcoach/` must stay byte-identical; prove it with `cmp` and say
so in the handoff.

### 1.1 The five profiles, as decided

All five are namespaced specializations of `tools.agent` in
`LoadCoach/src/loadcoach/config/task_profiles.toml`. Values are **decided** — transcribe them, do
not re-derive or "improve" them.

| Profile | Weights | Constraints | Execution |
|---|---|---|---|
| `tools.agent.local_fast` | `tools.agent`'s, unchanged | `min_context_tokens = 16384`, `requires_capabilities = ["tool_use"]`, `max_latency_p95_seconds = 60`, `min_capability_scores = { tool_use = 0.3 }`, `allow_remote_providers = false` | `tools.agent`'s, unchanged |
| `tools.agent.local_large` | `agentic 0.30, tool_use 0.25, reasoning 0.30, reliability 0.15` | `min_context_tokens = 32768`, `requires_capabilities = ["tool_use"]`, `max_latency_p95_seconds = 300`, `min_capability_scores = { tool_use = 0.4, reasoning = 0.4 }`, `allow_remote_providers = false` | `max_output_tokens = 8192` |
| `tools.agent.remote_cheap` | `tools.agent`'s | `min_context_tokens = 128000`, `max_latency_p95_seconds = 120`, `min_capability_scores = { tool_use = 0.4 }`, `allow_remote_providers = true` | `max_output_tokens = 4096` |
| `tools.agent.remote_frontier` | `tools.agent`'s | `min_context_tokens = 200000`, `max_latency_p95_seconds = 300`, `min_capability_scores = { tool_use = 0.5, reasoning = 0.5 }`, `allow_remote_providers = true` | `max_output_tokens = 8192` |
| `tools.plan` | `reasoning 0.4, structured_output 0.3, instruction_following 0.2, reliability 0.1` | `min_context_tokens = 16384`, `requires_capabilities = ["structured_output"]`, `max_latency_p95_seconds = 180`, `min_capability_scores = { structured_output = 0.4 }`, `allow_remote_providers = false` | `temperature = 0.1`, `max_output_tokens = 4096`, `response_format = "json"`, `max_attempts = 3`, `fallback_depth = 1`; validation `require_valid_json = true`, `max_output_chars = 50000`, **no schema** |

Three things to hold on to while transcribing:

* **Each local profile's `min_context_tokens` equals its tier's `context_budget_tokens`** (16384 /
  32768), and each remote profile's equals its tier budget (128000 / 200000). LoadCoach cannot
  express model size, so *the latency ceiling, the minimum context and the minimum scores are the
  whole distinction between fast and large.* That is the decision, not an approximation of one.
* **The two remote profiles ship now and route to `NO_ELIGIBLE_MODEL`** until LC-E1 registers a
  remote provider — PromptCadence reports that as `TIER_UNAVAILABLE` and `tiers check` shows it.
  Visible, not silent. **Whether a remote profile must *require* a remote provider is LC-E1's
  question (D-11), not this row's** — do not answer it here.
* **`tools.plan` deliberately has no schema.** The plan document's shape stays PromptCadence-internal
  (D-7) and G1 validates it. G1 may reopen this; you may not.

### 1.2 The pins that move from fifteen to twenty

```text
LoadCoach/tests/unit/test_task_profile_validation.py:107  test_all_fifteen_shipped_profiles_load_and_validate  (name + the len == 15 at :111)
LoadCoach/tests/unit/test_cli.py:222, :238                len(profiles) == 15  (two asserts)
LoadCoach/tests/e2e/test_models_and_task_profiles.py:22   test_get_task_profiles_returns_all_fifteen (name + len at :26)
LoadCoach/docs/quickstart.md:15                           "the fifteen shipped task profiles"   (LoadCoach's own operator doc, not a mirror)
docs/apps/loadcoach/routing.md:73                         the profile list, ending "— fifteen."   (mirrored)
docs/apps/loadcoach/development-plan.md:86                Phase 2 AC1, "All **fifteen** shipped task profiles" (mirrored)
```

**`LoadCoach/tests/simulation/test_scheduling_properties.py:643` also says "fifteen" and is about
queue points, not profiles. Leave it alone.** Search results are not a work list.

### 1.3 Part 1's finish line

LoadCoach's full gate green **except the three known evidence failures**; `CHANGELOG.md` under
`## [Unreleased]`, no bump; `cmp` proof for both mirrored files; one commit in `docs`, one in
`LoadCoach`.

---

# Part 2 — PromptCadence Phase 4

**Goal, from the plan:** the loop executes tool calls under full ToolYard discipline. **Acceptance
criterion 1:** a hostile scripted model — requesting unlisted tools, escaping paths, producing huge
outputs — completes or halts cleanly with every call recorded, and **no exception ever crosses the
loop.**

### 2.1 The dependency

Add `toolyard>=0.1,<0.2` to `pyproject.toml`'s runtime dependencies, replacing the Phase-1 comment
that says the tool packages arrive with the phase that consumes them. It is on PyPI; this is a
normal pin, not a path install. ToolYard's own dependencies (`baseaicore>=0.4.1,<0.5`,
`jsonschema`, `httpx`) are already compatible with PromptCadence's environment — verify the resolve
rather than assuming it.

### 2.2 Registry, sandbox and workspaces — the part D1 already decided

* Registry assembled from `[tools] enabled`; **per-trajectory allowlist ⊆ config allowlist**, and
  the request's allowlist is the caller's, which is what splits an `undeclared_tool` deviation into
  drift versus violation (`domain/deviation.py` already knows this).
* **Build one `TieredSandbox` per executor and hand that same instance to `run_command_tool`**
  (ToolYard spec §7 as amended at D1). Not one per call, not a second one for the tool.
* **The container image is a constructor argument that must be present locally** (`--pull=never`),
  so configuration names it and `promptcadence doctor` renders `TierReport.reason`. An operator must
  be able to see *which rung the ladder landed on and why* without reading logs.
* **`SandboxPaths` refuses relative or overlapping roots at construction**, so the workspace
  lifecycle builds **absolute, disjoint** roots — per trajectory, under `workspace_root`
  (default `<data>/workspaces`), plus the configured read-only roots.
* `run_command_tool` gets an **explicit `PATH` allowlist** such as
  `{"PATH": "/usr/local/bin:/usr/bin:/bin"}` — under bwrap `--clearenv` leaves none, and
  `os.environ` is never the answer. **Env is caller-owned, never model-supplied.** Never pass
  `network=True` (refused in v1). Render both `SubprocessResult.output_truncated` and the exit code.
  Respect `MIN_PROCESS_COUNT` — bwrap's count includes `bwrap` and `prlimit`, so a low
  `ResourceLimits.process_count` refuses everything.
* **Workspace lifecycle follows content retention** — swept with transcript text, hashes kept
  (the plan's decided answer to its own named risk).

### 2.3 The loop

Tool round trips inside a step: `tool_calls` → ToolYard → results appended as **TOOL turns** →
continue until a declared finish, bounded by `execution.max_turns_per_step`. A **refusal is a
result**: it is fed back as a structured TOOL turn and the trajectory continues (ADR-0053). Remove
the Phase-3 placeholder at `services/loop.py:945` — and make sure what replaces it still refuses to
call a requested-tool turn "completed" when the tool could not run.

`undeclared_tool` wiring: the requested tools already reach `TurnFacts.requested_tools` and the
trajectory allowlist already reaches the comparison. Phase 4 makes the disposition *act* — inside
the intent's `approved_tools`, outside it but inside the trajectory allowlist, and outside both.

### 2.4 Persistence, events, artifacts, surfaces

* `SqlToolCallStore` over a `tool_call_records` table — **one new Alembic migration** (`0004_…`),
  one-write transitions per ADR-0044, and the db-matrix must stay green on both dialects.
* `tool.call.*` events on the existing event stream.
* **Oversize tool outputs spill to the artifact directory by hash**, with the record naming the
  hash — never a truncated body pretending to be the whole one.
* `GET /tools` and `promptcadence tools list|show`. Route handlers and CLI bodies call one service
  method and render; no business logic in either.
* `[tools] redact_args` means those tools' arguments are stored **as a hash only**.

### 2.5 The contract test that stops the profiles drifting

Vendor LoadCoach's `task_profiles.toml` as `tests/contract/loadcoach_task_profiles.toml`, recorded
**exactly the way I10 records the OpenAPI snapshot** — copy the idiom from
`tests/contract/test_loadcoach_contract.py` (`SNAPSHOT_SHA256`, `SNAPSHOT_SOURCE`, and the
`test_the_vendored_snapshot_is_the_one_recorded` digest test, whose failure message tells the next
session what to update). Source is **LoadCoach at your own Part 1 commit** — record that SHA.

The contract test asserts:

1. every default tier's `task_profile` exists in the vendored file;
2. both agent profiles require `tool_use`;
3. each profile's `min_context_tokens` equals its tier's `context_budget_tokens`;
4. each profile's `allow_remote_providers` equals its tier's `remote`;
5. `tools.plan` exists, sets `require_valid_json`, and declares **no** schema.

A drift then fails in CI, not at an operator's `tiers check`.

### 2.6 The fake LoadCoach

**It stays an empty registry — stricter than LoadCoach, by decision. Do not give it defaults.** Add
`shipped_profiles()` to `tests/fakes/loadcoach_app.py`, reading the vendored TOML, so tests register
the *real* profile shapes; `text_profile()` and `schema_profile()` remain for hand-shaped cases
(`schema_profile` is still how contract 6's second clause is tested). Move the e2e, recovery and
live-adjacent fixtures onto `shipped_profiles()`.

### 2.7 The document amendments

* `docs/apps/promptcadence/spec.md` §12: the sentence saying the tier profiles are *"documented as
  TOML in PromptCadence's operator guide"* becomes: they **ship in LoadCoach's
  `task_profiles.toml`**.
* `tests/live/test_loadcoach_journey.py`'s docstring: drop the `PROMPTCADENCE_TIERS__*` overrides —
  they are no longer needed, which is the point of the row.
* Mirror every touched `docs/` file into `PromptCadence/docs/`, byte-identical, `cmp`-proved.

### 2.8 Tests

The spec §18 rows that exist at this layer, each as its own test: **unlisted tool; path escape;
symlink escape; refusal fed back as a structured TOOL turn with the trajectory continuing; size
caps.** Then a scripted **multi-tool journey against the fake**, and a **hostile scripted model**
journey for acceptance criterion 1 — it must end `completed` or `halted` with every call recorded,
and the assertion that no exception escaped is part of the test, not an observation. The marked live
journey gains one real `read_file`.

The default suite must still pass with **no LoadCoach, no Ollama, no GPU and no network.**

---

## 4. Exit demonstration — run it, do not describe it

The row's exit condition is that the shipped defaults work with **no tier overrides**. D2's journey
is the template (`docs/history/D2_HANDOFF.2.md` §4); scratch data goes in the scratchpad only, and both servers
get stopped afterwards.

```bash
# LoadCoach at YOUR Part 1 commit, fake provider
cd /home/jpk/ai/suite/LoadCoach
LOADCOACH_PROVIDER__KIND=fake LOADCOACH_DATA_DIR=<scratch>/loadcoach-live \
LOADCOACH_STORAGE__DATABASE_URL=sqlite:///<scratch>/loadcoach-live/loadcoach.sqlite3 \
  .venv/bin/loadcoach serve --port 8766

# PromptCadence — note: NO PROMPTCADENCE_TIERS__* overrides. That is the whole test.
cd /home/jpk/ai/suite/PromptCadence
PROMPTCADENCE_LOADCOACH__BASE_URL=http://127.0.0.1:8766 .venv/bin/python -m pytest -m live -q
.venv/bin/promptcadence run "…" --bypass-planning --follow
```

Both must complete. Also run `promptcadence tiers check` and `promptcadence doctor` and paste what
an operator sees — including the two remote tiers reporting `TIER_UNAVAILABLE`, which is correct.

**A run against Ollama is the operator's, not yours** ([outstanding-work §4](docs/roadmap/outstanding-work.md)):
the fake provider declares `stop` for every answer, so `length` and `content_filter` on a real model
stay unexercised until they do it. Say so in the handoff.

## 5. Closing duties

1. Full gate in **all three** repositories, with the interpreter and the exact invocation named, and
   LoadCoach's three known failures reported as three — not swept, not fixed.
2. `CHANGELOG.md` under `## [Unreleased]` in LoadCoach and PromptCadence. No bumps.
3. `git status --short` clean in all three; every mirror `cmp`-proved.
4. **`docs/history/E4_HANDOFF.md` at the workspace root**, in the house shape: gate results with the interpreter;
   what was built against the plan; **decisions made where a document left an edge, with reasons**;
   the commits; what the next row must not relitigate; operator steps for the morning (push order:
   `docs`, `LoadCoach`, `PromptCadence`; the Ollama run; the F1 readiness note below).
5. Record the **model deviation** (scheduled Sonnet 5 · high, run at Opus 5 · high) and why.

## 6. Stop rules — the boundary is the point

* **Do not start Phase 5 / row F1.** No `loadledger` dependency, no ledger tables, no mounting, no
  debits, no estimator, no `[budget]` wiring, no `declare_run`. If tool-call records look like they
  want a cost column, they do not — that is F1's, and F1 is a separate session on a reviewed P4.
* **Do not touch ToolYard.** `docs/history/E2_HANDOFF.md` §8 lists what is settled: no rung below refusal, the
  probe's real canary, `env=None` is the empty allowlist, `requires_isolation` is load-bearing, one
  `Popen`, the `/etc` tuple, the refusal order, a handler refuses by returning `ToolRefusal` and
  never by raising, no handler resolves a path, `Reason` is closed, the five built-ins' wire
  definitions are golden-locked. If ToolYard genuinely blocks this row, **stop and write it up** —
  a ToolYard change is its own row now that `0.1.0` is published.
* **Do not fix LoadCoach's three evidence failures**, and do not move its `setspec` pin. Both are
  scheduled: the pin sweep is **row E5** (added 2026-09-04; `mirrorwall 0.2.2` is prepared and
  waiting to publish), and LoadCoach's own pin deliberately rides **H4**, with the
  `CapabilityEvidenceV1_1Out` adoption that makes those three tests pass. Moving it here turns a
  local-only red into a CI red in the middle of a config-only commit.
* **Do not weaken `.importlinter`** in either repository to make an import work.
* **Do not relitigate the tier defaults.** They were decided by interview on 2026-09-03 and are
  recorded on the row. Transcribe them.
* **No tool performs network egress in this phase.** The plan's "Deferred" note is explicit:
  `http_fetch` waits for P6, because it requires egress governance to be in place. `[tools] enabled`
  lists it by default, so *how* it stays off — refused at registry assembly with a named cause, or
  excluded from the default until P6 — is an edge this row must decide, implement and **record in
  the handoff with its reason**. What is not open: it must not reach the network, and an operator
  must be able to see why it did not.
* Never `git add -A`; never edit the workspace root's unversioned files by overwrite; never leave
  the tree dirty at a boundary.
* If you are blocked, **stop and write the handoff.** A half-built phase with an honest handoff is a
  good night's work; a half-built phase discovered in the morning is not.

## 7. If you finish with capacity left

Do **not** start F1. In priority order: deepen the §18 security cases (a symlink swapped between
check and use; a tool name that is valid UTF-8 but pathological; an output bomb under the cap);
re-run the exit demonstration a second time from a clean scratch directory to prove it is not
order-dependent; then write an **F1 readiness section** in the handoff — read-only: name
`loadledger`'s public surface (`SqlLedger`, `mount_ledger_tables`), the exact place P5's mount would
attach to PromptCadence's metadata and Alembic history, and which of your new tool-call records F1
will debit from. Notes, not code.
