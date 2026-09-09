# E4 handoff — PromptCadence Phase 4, tools under ToolYard discipline, and LoadCoach's five harness profiles

**Row:** E4 of `docs/roadmap/outstanding-work.md` §1.
**Date:** 2026-09-04, overnight, unattended.
**Model deviation:** scheduled **Sonnet 5 · high**, run at **Opus 5 · high** — see §12.
**Status:** **complete.** Both parts built, gated and committed in all three repositories. The exit
demonstration was run twice, from two clean scratch directories, and passed both times. Nothing was
pushed, tagged, bumped or published.

---

## 1. Gate results — interpreter and invocation named (M5C-13)

All three run from inside the component directory, in its own virtualenv.

| Repository | Interpreter | Invocation | Result |
|---|---|---|---|
| `docs` | — | `git status --short` | clean |
| `LoadCoach` | **Python 3.14.4** (`.venv/bin/python`) | `ruff format --check . && ruff check . && mypy src tests && lint-imports && python -m pytest -m "not live and not performance" -q` | format 189 files OK · ruff OK · mypy 169 files OK · import-linter 4/4 · **3 failed, 855 passed, 3 skipped, 15 deselected** |
| `PromptCadence` | **Python 3.13.15** (`.venv/bin/python`) | same | format 91 files OK · ruff OK · mypy 88 files OK · import-linter 5/5 · **799 passed, 2 skipped, 2 deselected** |

**LoadCoach's three failures are the three known ones and none of them is mine:**

```text
tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-full]
                                                                                            [1.1-mixed]
                                                                                            [1.1-unsupported]
```

Counted **3 before** the first LoadCoach commit and **3 after** it (855 passed both times — this row
added no LoadCoach test, only moved six pins). Cause unchanged: the venv carries the editable
workspace SetSpec at 0.6.0 prep while LoadCoach pins `setspec>=0.4,<0.5` and CI installs
`setspec==0.4.0`. Adoption is **H4**'s. **Not fixed, not swept, and the pin was not moved.**

Coverage, PromptCadence: **92.6 %** against an 85 % floor. New modules: `domain/tools.py` 100 %,
`services/tools.py` 96 %, `infrastructure/tool_calls.py` 91 %, `cli/commands/tools.py` 84 %,
`services/loop.py` 84 % (was 84 %).

`pytest-randomly` was on for every reported run; `-p no:randomly` was used only while iterating.

---

## 2. Commits

| Repo | SHA | Subject |
|---|---|---|
| `docs` | `da45959` | `docs(loadcoach): the five harness profiles ship in LoadCoach, taking fifteen to twenty` |
| `LoadCoach` | `5c5aa1f` | `feat(profiles): ship PromptCadence's five harness task profiles` |
| `PromptCadence` | `b4ac1a2` | `feat(tools): the loop executes tool calls under ToolYard discipline` |
| `PromptCadence` | `c22ddef` | `test(tools): the §18 security rows, the hostile-model journey, and the profile contract` |
| `docs` | `0e0d28c` | `docs(promptcadence): the tier profiles ship in LoadCoach, and how http_fetch stays off until P6` |

Committed in that order, at each boundary, never `git add -A`. All three trees are clean.
`docs` started at `738eefc`, not the `6494fec` the prompt named — E5's row had been added on
2026-09-04 in between; nothing else differed.

**Mirrors, `cmp`-proved (silent on success, all five verified after the final commit):**

```text
docs/apps/loadcoach/routing.md            == LoadCoach/docs/apps/loadcoach/routing.md
docs/apps/loadcoach/development-plan.md   == LoadCoach/docs/apps/loadcoach/development-plan.md
docs/apps/promptcadence/spec.md           == PromptCadence/docs/apps/promptcadence/spec.md
docs/apps/promptcadence/development-plan.md == PromptCadence/docs/apps/promptcadence/development-plan.md
docs/apps/promptcadence/lifecycle.md      == PromptCadence/docs/apps/promptcadence/lifecycle.md
```

---

## 3. Part 1 — the five harness profiles, in LoadCoach

Transcribed from the row, not re-derived. `task_profiles.toml` goes from fifteen profiles to
twenty; **no `src/loadcoach/**/*.py` was touched.** All five weight sets sum to 1.0 (asserted), and
every capability named is in the SetSpec vocabulary (LoadCoach's own startup validation, which the
suite exercises).

The six "fifteen" pins moved to twenty: two test names
(`test_all_twenty_shipped_profiles_load_and_validate`,
`test_get_task_profiles_returns_all_twenty`), four counts (`test_task_profile_validation.py`,
`test_cli.py` ×2, `test_models_and_task_profiles.py`), `LoadCoach/docs/quickstart.md`, and the two
mirrored `docs/` files. **`tests/simulation/test_scheduling_properties.py:643` was left alone** —
its "fifteen" is about queue points.

Verified against a running LoadCoach at `5c5aa1f` on the fake provider:

```text
GET /api/v1/task-profiles -> profiles: 20
  tools.agent                  8192   allow_remote_providers=False
  tools.agent.local_fast      16384   False
  tools.agent.local_large     32768   False
  tools.agent.remote_cheap   128000   True
  tools.agent.remote_frontier 200000  True
  tools.plan                  16384   False
```

---

## 4. Part 2 — what was built

* **`toolyard>=0.1,<0.2`** added to `pyproject.toml`'s runtime dependencies, replacing the Phase-1
  comment. Resolve verified, not assumed: `pip install -e ".[dev]"` pulled `toolyard 0.1.0` plus
  `jsonschema 4.26.0` and its transitives with no conflict against the existing pins.
  PromptCadence has **no `requirements/` lock** (that is still its own row, per `docs/history/D2_HANDOFF.2.md`
  §7), so nothing needed recompiling.
* **`services/tools.py`** — `ToolPlant` (process-lifetime), `TrajectoryTools` (per trajectory),
  `ArtifactStore`, `tools_health_component`.
* **`domain/tools.py`** — `ToolOutcome`, `ToolCallStarted`, `ToolCallCompleted`. Free of
  `toolyard`, because that package depends on `httpx` and `.importlinter`'s domain-purity contract
  forbids `httpx` under `promptcadence.domain`. A test asserts `ToolOutcome`'s value set equals
  ToolYard's `ToolStatus`, so the restatement cannot drift into a mistranslation.
* **`infrastructure/tool_calls.py`** — `CollectingToolCallStore`, `ToolCallLinks`, `tool_call_row`.
* **`infrastructure/loadcoach.py`** — `RequestedToolCall` and `assemble_tool_calls` (§6, finding 1).
* **Migration `0004`** — `tool_call_records` and `turns.tool_call_id`. `check_parity` green on
  both dialects; the db-matrix job's postgres tests are skipped locally and unchanged.
* **Surfaces** — `GET /tools`, `GET /tools/{name}`, `promptcadence tools list|show`, and a third
  health component `tools` on both `health` and `doctor`.
* **The loop** — the Phase-3 placeholder at `services/loop.py:945` is gone, replaced by the round
  trip; `_round_trips` bounds it by `execution.max_turns_per_step`.

**What was *not* built, deliberately:** `promptcadence tiers check`. It is **Phase 7's** in the
development plan ("Task-profile checks in `doctor` and `promptcadence tiers check`"), it is not on
this row's work list, and building it here would have been P7 work in a P4 commit. §5 below shows
what an operator sees instead.

---

## 5. Exit demonstration — run twice, from two clean scratch directories

Scratch only; nothing under the repositories, nothing in `/tmp` directly, nothing at the workspace
root. Both servers stopped afterwards; `ss -ltnp` confirms nothing listens on 8766 or 8768.

### Run 1 — LoadCoach at E4's own commit (`5c5aa1f`), fake provider, **no `PROMPTCADENCE_TIERS__*`**

```text
$ env | grep -c PROMPTCADENCE_TIERS
0

$ PROMPTCADENCE_LOADCOACH__BASE_URL=http://127.0.0.1:8766 .venv/bin/python -m pytest -m live -q
2 passed, 801 deselected

$ .venv/bin/promptcadence run "Reply with the single word: ready." --bypass-planning --follow
trajectory   01M1NPSF51H5FCWEHJT6JKFWJE
[1] trajectory.created
[2] trajectory.claimed
[3] intent.minted
[4] turn.started
[5] turn.completed — complete
[6] trajectory.completed
state        completed
cause        the provider declared finish_reason=stop
exit 0
```

### Run 2 — fresh LoadCoach data dir **and** fresh PromptCadence data dir, same commands

```text
2 passed, 801 deselected
state        completed          exit 0
$ .venv/bin/promptcadence trajectory list
(server)
01M1NQJAPZQD7SQ2WZ7S8CJGS9  completed          Reply with the single word: ready.   # exactly one
```

**The row's exit condition is met: the shipped defaults work with no tier overrides.**

### What an operator sees

```text
$ promptcadence doctor
promptcadence doctor — status: ok
  ✓ database: sqlite, schema at head.
  ✓ loadcoach: loadcoach reports ok
  ✓ tools: 4 registered: read_file, list_dir, write_file, run_command;
      withheld: http_fetch (egress_governance_deferred_to_p6);
      isolation container: podman: not installed; docker at /usr/bin/docker ran the canary
      under the container tier's flags with image 'python:3.12-slim'.

$ promptcadence tools list
  ✓ read_file  [read_only, none]
  ✓ list_dir  [read_only, none]
  ✓ write_file  [mutating, none]
  ✓ run_command  [mutating, none, isolated]
  · http_fetch  withheld: egress_governance_deferred_to_p6

isolation: container (docker)
  podman: not installed; docker at /usr/bin/docker ran the canary under the container tier's
  flags with image 'python:3.12-slim'.

$ promptcadence tiers check
Error: No such command 'tiers'.        # Phase 7's, see §4
```

### The remote tiers reporting `TIER_UNAVAILABLE`

The prompt's §4 asks for this "including the two remote tiers reporting `TIER_UNAVAILABLE`".
**They are not in the shipped active defaults** — B4 decided (`config._default_tiers`, with its
reasoning in the docstring) to ship only the two local tiers active, because a remote tier with an
empty `pricing_file` is refused at startup and would break spec §20 AC1's zero-configuration boot;
the remote pair is documented and commented out in `EXAMPLE_CONFIG_TOML`. So it was demonstrated
the way an operator would reach it — by configuring `remote_cheap` with a pricing file, as the
commented block instructs:

```text
state       halted
error_code  TIER_UNAVAILABLE
cause       tier 'remote_cheap' cannot serve: loadcoach_has_no_remote_provider
```

Note it is caught **earlier** than the row predicted: `TierPolicy.availability` refuses before any
call, so LoadCoach's `NO_ELIGIBLE_MODEL` is never reached. Visible, not silent, either way.

### The Ollama note, and a real environmental finding

**A run against Ollama is the operator's, not mine** (`outstanding-work` §4): the fake provider
declares `finish_reason=stop` for **every** answer, so `length` and `content_filter` on a real model
stay unexercised until the operator does it. It is also the only way a *model* directs a tool call
here — the fake never requests one — so the loop's model-directed path is proven by the integration
suite and the plant's real path by the live test, not by a real model choosing.

**Finding worth knowing before the operator repeats this:** the exit demonstration only runs when
the GPU has roughly **11.5 GB free**. LoadCoach's fake provider declares an 8.5 GB model, and its
`insufficient_vram` hard constraint is real — so with the operator's Ollama holding a 14 GB model
resident, `POST /route` rejects the *only* candidate with `insufficient_vram` and every tier reports
`NO_ELIGIBLE_MODEL`, including plain `tools.agent`. This is **not** a profile problem and not
introduced by this row (verified: plain `tools.agent`, unchanged, is rejected identically), and it
is why one intermediate attempt failed before the two clean runs above. If the demonstration halts
with `NO_ELIGIBLE_MODEL`, check `nvidia-smi` before checking anything else.

---

## 6. Decisions made where a document left an edge, with reasons

1. **`http_fetch` is withheld from the registry, not removed from `[tools] enabled`.** The row made
   this an explicit edge to decide. `enabled` keeps spec §12's shipped list; assembly refuses to
   register the tool and records the cause `egress_governance_deferred_to_p6`, which reaches
   `GET /tools`, `promptcadence tools list` and `doctor`. **Why this way:** an operator who copied
   the documented configuration keeps working, P6 flips one guard instead of editing a shipped list
   an operator may have copied, and the disagreement between "listed" and "registered" is *visible*
   rather than silent. A model asking for it is refused `unknown_tool` — which is true, it is not
   in the registry — and the refusal is a recorded result. **Two independent facts keep it off the
   network:** it is not registered, and every invocation's `max_egress` is `EgressClass.NONE`, which
   would refuse it at the egress check even if it were. Recorded in the plan's Phase 4 "Deferred"
   note and in spec §12.
2. **A name in `[tools] enabled` that ToolYard does not ship is withheld, not a startup refusal.**
   Registration is code (ADR-0053 decision 1), so no configuration could ever supply a handler; a
   server that will not boot tells an operator less than a catalog line naming their typo. Cause
   `not_a_shipped_tool`.
3. **`Disposition.REFUSED_NOT_REAPPROVABLE` continues the trajectory.** Lifecycle §5's prose says a
   tool outside the *trajectory* allowlist has **the call** refused outright and recorded, never
   re-approvable — and says nothing about the trajectory ending. Before tools could execute, a halt
   was the only available reading, and Phase 3 implemented it that way. Phase 4 makes the
   disposition *act*, which is what §2.3 of the row asked for. `SCOPED_REAPPROVAL` still halts; the
   approver is P7's.
4. **The application applies the model-facing cap, not ToolYard.** The executor's
   `max_content_bytes` is set to `ARTIFACT_CEILING_BYTES` (4 MiB) — above every shipped tool's own
   cap — so `ToolResult.content` **is** the whole cleaned output and its digest is ToolYard's
   `result_sha256`. PromptCadence then caps what the model sees at `[tools] max_result_chars` and
   files the whole output under that digest. **Without this the artifact could not exist**: ToolYard
   hands back a capped `content` and a digest of the *full* output, so an application that spilled
   what it was given would file a prefix under the whole output's hash. `ToolPlant.spill` writes
   **nothing** when the two digests disagree, and a test drives that path.
5. **`assemble_tool_calls` exists because LoadCoach forwards streaming fragments.**
   `output.tool_calls` is one entry per `ToolCallDelta` — `{call_index, id, name,
   arguments_fragment}` — so one call can be three entries. Phase 3's `TurnFacts.requested_tools`
   read a name off each entry and would have counted such a call three times. Fragments are now
   grouped (by `id`, else `call_index`, else position) and parsed once. **It refuses nothing**: a
   missing name, unparseable arguments, a non-object JSON body and a non-string fragment all have a
   defined value, because a parser that raised on model output would let the model choose when a
   turn ends.
6. **Startup refuses a relative tool root, and a read root overlapping the workspace root.**
   `SandboxPaths` makes the same check per trajectory; making it over the *parent* at plant
   construction moves it to startup and covers every trajectory at once. Added to spec §12's
   refusal list.
7. **One sandbox and one registry per *process*, not per executor.** The row says "one
   `TieredSandbox` per executor and hand that same instance to `run_command_tool`". The invariant
   that matters — and the one D1 finding 1 states — is *same instance*, so the executor's tier check
   and the handler's rung are one answer. Building one per trajectory would additionally pay for a
   real canary launch per trajectory. So the plant holds one sandbox and one registry, every
   executor is built over them, and what narrows per trajectory is the **allowlist** — which is
   exactly ToolYard's design ("registered does not mean callable") and ADR-0053 decision 1's
   "registered in code at startup".
8. **The workspace sweep has no production caller yet, and that is deliberate.**
   `ToolPlant.sweep_workspace` implements the plan's decided policy (workspaces follow content
   retention, swept with transcript text, hashes kept) and is unit-tested. Its caller is the
   retention sweep, which does not exist — `StorageSettings.retain_content` is still config-only and
   says "the retention sweep arrives later". Sweeping at the terminal transition instead would be
   **wrong**: retention counts *from* the finish, and deleting the workspace there destroys the
   files an operator reads while diagnosing the run that produced them. See §9.
9. **`GET /tools/{name}` returns 422, not 404**, for a name configuration does not hold. Spec §13
   assigns one status to `TOOL_NOT_FOUND` and the submit path needs it at 422; giving one code two
   statuses would make the machine-readable half ambiguous. Noted in the route's docstring.
10. **`[tools]` gained four keys**: `container_image` (required — the rung is probed with
    `--pull=never`, so configuration has to name it; D1 finding 8), `artifact_root`,
    `max_result_chars`, `timeout_seconds`. The row's "`config.py`'s defaults are untouched" refers to
    the **tier** defaults, which were not touched. All four are documented in `EXAMPLE_CONFIG_TOML`
    and in spec §12.

---

## 7. What the next row must not relitigate

* **Everything in `docs/history/D1_HANDOFF.md` §7 and `docs/history/E2_HANDOFF.md` §8 still stands, and this row changed
  none of it.** No rung below refusal, the probe's real canary, `env=None` is the empty allowlist,
  `requires_isolation` is load-bearing, one `Popen`, the `/etc` tuple, the refusal order, a handler
  refuses by returning `ToolRefusal`, no handler resolves a path, `Reason` is closed, the five
  built-ins' wire definitions are golden-locked. **ToolYard was not touched.**
* **A refusal is a result.** `REFUSED_NOT_REAPPROVABLE` continues; only `HALT` and
  `SCOPED_REAPPROVAL` stop a trajectory in this phase (`_STOPPING_DISPOSITIONS`). Turning a refusal
  back into a halt hands a model a stop condition.
* **`http_fetch` stays withheld until P6**, and P6's change is to register it with a resolver and an
  egress ceiling — not to edit `[tools] enabled`.
* **The digest agreement is load-bearing.** `ARTIFACT_CEILING_BYTES` must stay above every shipped
  tool's own cap, or `spill` starts declining silently and artifacts stop being written. A test
  asserts the inequality.
* **The tool-call assembler must not raise.** Every model-shaped input has a value.
* **The fake LoadCoach stays an empty registry.** `shipped_profiles()` reads the vendored TOML;
  `text_profile`/`schema_profile` remain for hand-shaped cases. Do not give the fake defaults.
* **The vendored profile snapshot's digest is `33c3dff7…` at LoadCoach `5c5aa1f`.** Changing
  LoadCoach's `task_profiles.toml` means re-copying the file and moving both
  `SNAPSHOT_SHA256` and `SNAPSHOT_SOURCE` in the same change; the failing test says so.
* **`promptcadence tiers check` is Phase 7's**, with the task-profile checks in `doctor`.
* **No cost column on `tool_call_records`.** That is F1's, derived from usage and a pricing hash.

---

## 8. Operator steps for the morning

1. **Push, in this order** (nothing is pushed):
   ```bash
   cd /home/jpk/ai/suite/docs         && git push        # da45959, 0e0d28c
   cd /home/jpk/ai/suite/LoadCoach    && git push        # 5c5aa1f
   cd /home/jpk/ai/suite/PromptCadence && git push       # b4ac1a2, c22ddef
   ```
   Push order matters only for readability — no CI job crosses repositories. `git push` needs the
   VSCode askpass IPC environment (`FreeWeight M6 and push auth` memory).
   Confirm CI green on all three. **LoadCoach's CI installs `setspec==0.4.0` from
   `requirements/ci.lock`, where the three failing goldens do not exist, so CI should be green
   there despite the local reds.**
2. **The Ollama run** (§5). Start Ollama, point LoadCoach at it, and run the journey with a real
   model — that is the only thing that exercises `length` and `content_filter`, and the only way a
   *model* chooses to call a tool here. Give the GPU ~11.5 GB of headroom or LoadCoach will reject
   the candidate on VRAM before any of this is reached.
3. **Podman is still unverified** (`docs/history/D1_HANDOFF.md` §13 row J). This host has docker and no podman;
   the container rung was exercised through docker in `doctor` and `tools list`.
4. **Review the workspace-lifecycle diff** — `§3.2`'s mitigation that overnight voided. The hunks
   worth an eye are `ToolPlant.__init__`/`for_trajectory`/`sweep_workspace`/`spill`
   (`services/tools.py`) and `LoopController._run_tool_calls`/`_run_one_tool_call`
   (`services/loop.py`).

---

## 9. Open items, recorded and not chased

* **The workspace sweep has no caller** (§6.8). P8's retention sweep should call
  `ToolPlant.sweep_workspace(trajectory_id)` for every trajectory whose content it scrubs. Until
  then a workspace persists after a run — the plan's named risk, decided this way rather than
  eliminated.
* **Tool-output text is not retention-scrubbed either**, for the same reason: `TOOL` turns are
  ordinary turns with `content_text` and `content_hash`, so whatever sweeps turn content sweeps
  them. Nothing extra is needed at P8 beyond the workspace call above.
* **`tool_call_records.result_summary` and `args_json` have no scrub path yet** — same P8 item.
* **A tool name in `[tools] enabled` that is withheld is still accepted in a submission's
  allowlist**, because `TrajectoryService.submit` validates against `[tools] enabled` and not
  against the registry. The call is then refused `unknown_tool` and recorded. Left as is: the
  submit-time check is about the *caller's* declared allowlist, and `GET /tools` is where the
  registry's truth lives.
* **`promptcadence doctor` creates its database file** if one does not exist (pre-existing
  `Database.from_url` behaviour, not introduced here). One stray `~/.local/share/promptcadence/`
  created during this session by a bare `doctor` run was removed.
* **PromptCadence has no `requirements/` lock and no `security` job** — still its own row
  (`docs/history/D2_HANDOFF.2.md` §7).
* **`setspec>=0.4,<0.5`** is untouched here; the pin sweep is **E5** and LoadCoach's rides **H4**.

---

## 10. F1 readiness — notes, not code

Read-only reconnaissance, per §7 of the kickoff. **No `loadledger` dependency was added and no
ledger code was written.**

* **LoadLedger's public surface** (`py/LoadLedger/src/loadledger/__init__.py`, `0.1.0` on PyPI):
  `Ledger` (the protocol), `InMemoryLedger`, `BalanceBook`, `BudgetCeiling`, `CeilingScope`,
  `CeilingVerdict`, `Debit`, `LedgerEntry`, `PartialPricing`, `utc_day_key`, `utc_day_start`, and
  the errors `CurrencyMismatch`, `InvalidCeiling`, `UnknownRun`, `UnsupportedDialect`.
  `SqlLedger` and `mount_ledger_tables` live in `loadledger.sql` (`sql.py:292` and `sql.py:154`).
* **Where the mount attaches.** `mount_ledger_tables(metadata, *, prefix=…)` must be called
  **eagerly, at module import, in the host's model package** — its docstring names a host that
  mounts lazily as the pattern's failure mode, because autogenerate then emits a migration that
  *drops* the package's tables. The place is
  `src/promptcadence/infrastructure/db/models.py`, whose module docstring already says so in
  prose: *"`ledger_entries` (LoadLedger) and `egress_decisions` (Commissioner) are **not** created
  here. They arrive *mounted* into this same metadata and Alembic history at Phase 5/6 (ADR-0050)
  … which is why the mount calls belong right here."* `Base.metadata` is what
  `MigrationRunner.check_parity` compares against and what the Alembic `env.py` names, so mounting
  there puts four tables into the same history as migration `0005` would create.
* **What F1 debits from.** `Debit` carries `run_id` and `source_ref`, both opaque strings
  (`types.py:227` — *"the turn, tool invocation or stage attempt this spend came from"*), and
  `SqlLedger.declare_run(run_id)` opens a run. So:
  * `run_id` → the **trajectory id**.
  * `source_ref` for a model turn → the **turn id** (`turns.id`), which is also the LoadCoach
    `idempotency_key`, which is what makes crash reconciliation idempotent by `source_ref`.
  * `source_ref` for a tool call → this row's **`tool_call_records.invocation_id`**, which is
    unique by constraint, is minted by the application and never by a model, and is already the
    `TOOL` turn's `tool_call_id`. It is the natural key and it is why the unique constraint exists.
  * The token counts a debit needs are already on `turns` in all four classes, with unreported
    classes stored as `NULL` rather than `0` (`_counted`, ADR-0016/ADR-0069) — so a floor stays
    distinguishable from a complete total, which is what `PartialPricing` and
    `budget.partial_pricing` turn on.
* **Tool calls have no cost of their own.** A tool call spends no tokens; what it costs is the
  *next* turn's larger input. So F1's debit for a tool call is either zero-valued-with-a-source or
  absent entirely — a decision for that row, not this one. The record deliberately has no cost
  column (§7).

---

## 11. Files added and changed

**`docs`** (2 commits): `apps/loadcoach/routing.md`, `apps/loadcoach/development-plan.md`,
`apps/promptcadence/spec.md`, `apps/promptcadence/development-plan.md`.

**`LoadCoach`** (1 commit): `src/loadcoach/config/task_profiles.toml`, `CHANGELOG.md`,
`docs/quickstart.md`, the two mirrors, and the four test files holding the moved pins.

**`PromptCadence`** (2 commits) — new:
`src/promptcadence/domain/tools.py`, `src/promptcadence/services/tools.py`,
`src/promptcadence/infrastructure/tool_calls.py`, `src/promptcadence/cli/commands/tools.py`,
`src/promptcadence/infrastructure/db/migrations/versions/0004_tool_call_records.py`,
`tests/contract/loadcoach_task_profiles.toml`, `tests/contract/test_loadcoach_task_profiles.py`,
`tests/integration/test_tool_execution.py`, `tests/unit/test_tool_plant.py`,
`tests/unit/test_tool_surfaces.py`, `tests/unit/test_tool_call_store.py`.
Changed: `pyproject.toml`, `config.py`, `services/loop.py`, `services/runtime.py`,
`services/worker.py`, `services/diagnostics.py`, `infrastructure/loadcoach.py`,
`infrastructure/threads.py`, `infrastructure/db/models.py`, `web/routes/system.py`,
`cli/main.py`, `CHANGELOG.md`, three mirrors, `tests/fakes/loadcoach_app.py`, and five existing
test files.

---

## 12. Model deviation, recorded for `model-assignment.md` §3.5

**Scheduled: Sonnet 5 · high. Run at: Opus 5 · high.** The kickoff document specified the upgrade
and its reasons, and they held:

1. **§3.2's mitigation was unavailable.** The row says *"Opus reviews the workspace-lifecycle
   diff"*; §2.12 voids that overnight. Running the writing pass at the reviewing tier buys back the
   pass that could not happen live — and the review is still owed (§8.4).
2. **The ordering is a security ordering.** §3 puts D1/E2 before E4 because this is where
   model-directed tool calls first execute for real, and a containment mistake here is quiet.

`xhigh` was correctly **not** used: every profile value, sandbox construction rule and contract-test
assertion was already decided on the row or in `docs/history/D1_HANDOFF.md` §8/§13 and `docs/history/D2_HANDOFF.2.md` §4/§7,
and the effort went into the hostile-model journey and the workspace lifecycle as the kickoff
directed.

**One deviation of my own, recorded:** §7's "deepen the §18 security cases" was partly done — the
hostile journey covers a pathological tool name (500 characters, capped to 128 in the record), an
output bomb under the cap, arguments that are not JSON, and an empty tool name. **A symlink swapped
between check and use was not built**: ToolYard resolves before it checks and substitutes the
resolved path into the handler's arguments, so the window that test would target is closed inside
ToolYard and its own suite is where the race belongs — writing it here would have tested ToolYard
from the wrong side, and touching ToolYard is its own row now that `0.1.0` is published.

---

## 13. Stop rules — observed

* **Phase 5 / row F1 was not started.** No `loadledger` dependency, no ledger tables, no mounting,
  no debits, no estimator, no `[budget]` wiring, no `declare_run`. §10 is notes.
* **ToolYard was not touched.** `py/ToolYard` is clean at `87e53f0`; nothing in this row needed a
  change there.
* **LoadCoach's three evidence failures were not fixed and its `setspec` pin was not moved.**
* **`.importlinter` was not weakened** in either repository; both contract sets pass unchanged
  (LoadCoach 4/4, PromptCadence 5/5), and `test_domain_purity.py` still asserts the contracts
  themselves are present and still forbid what they must.
* **The tier defaults were transcribed, not relitigated.**
* **No tool performs network egress.** Two independent facts, §6.1.
* **Never `git add -A`**; named paths only. No workspace-root file was overwritten — `docs/history/E4_HANDOFF.md`
  is new.

---

## 14. Interview, 2026-09-04 — decisions taken with the operator after the build

Ten decisions, put to the operator in three rounds after the row was complete. Seven confirmed what
was built; three changed something, and those three are done and committed.

| # | Question | Decision | Where it landed |
|---|---|---|---|
| A | How `http_fetch` stays off the network until P6 | **Keep it withheld** — listed in `[tools] enabled`, refused at registry assembly with a visible cause | Confirms §6.1; no change |
| B | `promptcadence tiers check` does not exist | **Leave it at P7**, and annotate the E4 row so the forward-looking reference does not mislead F1 | docs `943fbe1` |
| C | `sweep_workspace` has no caller | **Leave it uncalled until P8** — the retention sweep owns the schedule | Confirms §6.8; stays in §9 |
| D | The owed review, and the push | **Review before pushing** — and by `/code-review ultra`, not by me | §8.1 unchanged; see below |
| E | `[tools] max_result_chars` default | **Keep 8192** — ~12 % of `local_fast`'s context budget per result | Confirms §6.4; no change |
| F | The fake provider's VRAM gating | **File it as its own LoadCoach row, before F1** | docs `943fbe1`, new row **E6** |
| G | Spec §12 documents four tiers; two ship active | **Amend spec §12** to say so, with the reason | docs `943fbe1`; mirrored, `cmp`-proved |
| H | Podman still unverified | **Make it a blocking item before M11**, not an advisory ops step | docs `943fbe1`, milestone map + §4 |
| I | `GET /tools/{name}` returning 422 | **Keep 422** — one code, one status; §13's table stays a table | Confirms §6.9; no change |
| J | Testing the VRAM rejection deliberately | **The declared size must be configurable**, not merely smaller | Folded into row **E6** as its second requirement |

### The one that changed shape: E6

The operator's own addition, and it inverted the fix. Asked for the ability *"to test the fake with
a load that rejects on VRAM to see behaviour"* — which means the row is not "shrink the fake
model". Shrinking it alone would make every fake-provider journey reproducible **and remove the
only way anyone has ever seen `insufficient_vram` fire**, since that rejection has never been
reachable on purpose. So E6 carries two requirements: a default that never trips the constraint,
**and** a configurable declared size so an operator can provoke the rejection and read what
LoadCoach reports — `estimated_bytes`, `free_bytes_by_gpu`, `headroom_bytes` and the whole
`estimate` block, which is among the better diagnostics that application produces. The row also
says to prefer a configuration key over exempting the fake provider kind from the constraint: an
exemption would stop the fake modelling the constraint at all, which is the failure the row exists
to prevent.

### The review, per decision D

The operator will run **`/code-review ultra`** on the PromptCadence branch themselves — a
multi-agent cloud review, from a reviewer that did not write the code, which is the real weakness
of both a self-authored review document and a walkthrough I lead. It is user-triggered and billed;
I cannot launch it. **Push is blocked on that review's findings being acted on**, and §8.1's order
is otherwise unchanged.

### Still true after the interview

None of §7's "must not relitigate" list moved. ToolYard is still untouched, LoadCoach's three
evidence failures are still not fixed, its `setspec` pin is still not moved, and F1 was not
started.

---

## 15. Review, 2026-09-04 — `/code-review ultra`, and what it found

Run by the operator from `/home/jpk/ai/suite/PromptCadence` on `main` (three commits ahead of
`origin/main`). **39 agents, 2 rounds, 9 candidates, 2 confirmed findings.** It hit its 16-minute
wall clock with 4 agents abandoned, so **coverage is marked incomplete** — worth knowing when
reading the result as assurance rather than as a list.

### One real bug, found and fixed

**`ToolPlant.spill` had no size gate.** Two finders flagged it independently; the review's own
triage refuted them, and the refutation was wrong. The body was a status check, a digest check and
a `put` — so **an artifact was written for every successful call**, and `artifact_ref` was
populated on every `tool_call_records` row. Three contracts said otherwise, including `spill`'s own
`Returns` clause: *"nothing is written when the output is small enough to live in the turn"*. That
sentence described behaviour the function never had. `domain/tools.py`'s `artifact_ref` docstring
(*"when it was too large to keep inline"*) and spec §12's `artifact_root` (*"oversize tool
output"*) said the same thing.

Consequence was modest and real: a file per successful call, and the
`artifact_ref`/`output_truncated` pair no longer distinguishing an oversize output from an ordinary
one — which is the whole reason the field exists.

**Fixed.** `spill` now takes `limit` and refuses at or below it, keyed off the same
`[tools] max_result_chars` that `_shown_result` truncates at, so for an `OK` result the two cannot
disagree: an artifact is written **exactly when the model saw a prefix**. The one remaining
asymmetry is intended and now documented — a result *ToolYard* truncated is shown as a prefix and
filed nowhere, so `output_truncated=True` with `artifact_ref=None` reads as "the whole output no
longer exists to be filed".

Three tests pin it, and their absence is what let this through: an output that fits is not filed
(and the artifact root is asserted not to exist), an output one character past the limit is filed,
and the multi-tool journey asserts `{artifact_ref} == {None}` across its three small results.

**The digest-agreement rule itself was correct and holds** — `services/tools.py` still refuses a
body whose own hash does not match `result_sha256`, so a ToolYard-truncated prefix is never filed
under the whole output's digest, in both directions.

### Transaction boundaries — sound, and two properties worth knowing

The review generated candidates here and refuted them, correctly. Three phases: `ToolCallStarted`
plus the owner-CAS in its own write; execution with **no** transaction open; then the `TOOL` turn,
`store.flush` and `ToolCallCompleted` committing together. Turn row, record and completion event
are atomic with each other, which is the property ADR-0044 asks for.

Two implications, recorded rather than fixed:

* **A lost lease on the second write leaves a tool that ran and only a started event.** If
  `_owned_cas` raises `LeaseLost` after the call, the workspace side effects have already happened
  and nothing compensates them. Diagnosable by design — the started event is why it is written
  before the call — but it is not a rollback, and no phase currently promises one.
* **`spill` writes to disk before that commit**, so a rollback can leave an orphan artifact file.
  Harmless: the store is content-addressed and idempotent, so the same body re-filed later is the
  same file, and an unreferenced one wastes only space.

### The two confirmed nits, both fixed

1. **A stale `SqlToolCallStore` reference** in `TrajectoryTools.executor`'s docstring — a dangling
   Sphinx ref sitting on the exact sentence meant to explain collect-versus-write-through. The
   class is `CollectingToolCallStore`. The same stale name was in
   `apps/promptcadence/development-plan.md`'s Phase 4 work list, which is the *plan* — so the plan
   was amended to name the built class **and to say why it is not the one it originally specified**
   (a write-through store would hold a SQLite write lock across a container's whole timeout).
2. **The isolation mapping was hand-built twice**, in `web/routes/system.py` and
   `cli/commands/tools.py`. Now one `isolation_payload()` in `services/tools.py`, used by both, with
   a test asserting the two surfaces report the same key set. The review suggested a `TierReport`
   method; that is ToolYard's frozen dataclass and ToolYard must not be touched, so the shared
   shape lives on this side of the boundary instead.

### Gate after the fixes

`ruff format --check` 91 files · `ruff check` clean · `mypy` 88 files · import-linter 5/5 ·
**802 passed, 2 skipped, 2 deselected** (was 799) · coverage **92.67 %**, `services/tools.py` at
**97 %**.
