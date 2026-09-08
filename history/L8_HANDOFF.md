# L8 handoff — M9 residue, the tests

**Row:** L8 (Sonnet 5 · high), `docs/roadmap/outstanding-work.md` §1: "M9 residue, the tests"
(`M9_REAUDIT.md` items Q1/G16, O1, O6).
**Components:** `py/SetSpec`, `py/ModelRack`, `py/SweatMeter`, `py/WeightsDB`, `py/MirrorWall`,
`py/LoadLedger`, `py/Commissioner`, `FreeWeight`, `LoadCoach`, `IdeaPress`, `PromptCadence` (all
`main`), `docs` (`main`). All fifteen repositories were clean and pushed at the start; nothing was
pushed, tagged or published by this row — standing instruction.

---

## 1. Item 1 — G16 dependency-budget tests (eleven repositories)

Added `tests/unit/test_packaging.py` to every repository gold-standards.md §1.1 named as owing one:
SetSpec, ModelRack, SweatMeter, WeightsDB, MirrorWall, LoadLedger, Commissioner, FreeWeight,
LoadCoach, IdeaPress, PromptCadence. Each parses `[project.dependencies]` with `tomllib`, strips
extras/markers/specifiers to the bare name, excludes the ten suite packages (unbudgeted per §1.1),
and asserts the remainder equals the enumerated set §1.1 records for that component.

**The standard needed no correction.** Every one of the eleven repositories' declared dependencies
already matched §1.1 exactly — including the two "the same as X" rows (IdeaPress = FreeWeight's
nine names; PromptCadence = LoadCoach's eight), where the packages §1.1 treats as unbudgeted
(`loadledger[sql]`, `commissioner[sql]`, `cutctx`, `toolyard`) are suite packages, not part of
either application's non-suite spend. No table edit was needed; ADR-0114 decision 4
(`pydantic-settings` removal) was already reflected everywhere.

Commits: one per repository, `test: add G16 dependency-budget test (row L8 item 1)` — SetSpec
`dd598b1`, ModelRack `874343d`, SweatMeter `0bcd434`, WeightsDB `a62f49a`, MirrorWall `9c0e64f`,
LoadLedger `d82faa9`, Commissioner `2a16a8f`, FreeWeight `2c46c8c`, LoadCoach `91b1f2c`, IdeaPress
`d988ed0`, PromptCadence `fdf0db4`.

---

## 2. Item 2 — O1 earliest-release fixtures

Built the way L3 built the others: `/usr/bin/python3.13 -m venv`, `pip install <app>==<version>`
in a scratch venv with `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`XDG_STATE_HOME` pointed at a throwaway
tree (the real `~/.config/ideapress/config.toml` on this machine has a newer schema than 1.1.0
understands — hit this immediately and isolated around it, never touched it), migrated with the
app's own `db upgrade`, seeded through the app's own CLI where one exists, copied into
`tests/fixtures/databases/`, and added as a sibling test next to the existing fixture's.

| App | Version | Seeded via | Fixture head | This build's head | Migration exercised |
|---|---|---|---|---|---|
| FreeWeight | 1.0.0 | Python: `SettingsRepository.set` (no CLI verb writes a setting) — matches how 1.1.0 was seeded | `0007` | `0008` | **Real** (`0007 -> 0008`, the `runs` cascade rebuild ADR-0082 guards) |
| IdeaPress | 1.1.0 | CLI: `ideapress project create` × 2 | `0006` | `0009` | **Real** (`0006 -> 0009`: ledger tables, egress decisions, attempt cache/token classes) |
| PromptCadence | 1.1.0 | CLI: `promptcadence token create` × 2 | `0011` | `0011` | No-op — 1.1.0's head is this build's head; no migration has landed since. Same shape as the existing 1.2.0 fixture's test; starts asserting a real migration the day `0012` lands |

FreeWeight's and IdeaPress's earliest-release fixtures are the ones that actually exercise a
migration — the existing 1.1.0/1.3.0/1.2.0 fixtures are all documented no-ops (each already sits
at its build's own head), so this closes the gap M9_REAUDIT's O1 named ("only LoadCoach's fixture
exercises a real upgrade path"): FreeWeight and IdeaPress now do too. LoadCoach was excluded from
this item by the row's own kickoff (it already has a 1.0.0 fixture that exercises a real,
multi-revision upgrade).

`.gitignore` in all three repositories already carried the `tests/fixtures/databases/*.sqlite3`
carve-out from L3 — checked, nothing to add.

Commits: FreeWeight `74b07bd`, IdeaPress `5a6bcc7`, PromptCadence `964dd54`.

---

## 3. Item 3 — O6 untested degradation cells

Read `docs/architecture/graceful-degradation.md` §2.1 fresh rather than trusting the row's own
kickoff text, which quoted `M9_REAUDIT.md`'s parenthetical explanations of *where a row was already
proved* as if they named *where to add one* — by the time this row ran, row K1 (same day) had
already closed IdeaPress's and PromptCadence's "incompatible API major version" cells, so what the
kickoff called out as "(IdeaPress)" was actually LoadCoach's cell that remained open, and "database
locked (FreeWeight)" meant FreeWeight already had one — the other three did not. This section says
so per the same principle item 1 used: when a stale description and the live document disagree,
the live document is truth, and the divergence gets recorded rather than silently followed or
silently ignored.

### 3.1 What has a real test now (nine cells, four repositories)

Every one of these injects a failure at a seam the application already owns — never a global
`os.write` patch, never a real full disk:

* **Disk full**, all four applications, each attaching a SQLAlchemy engine-level hook
  (`before_cursor_execute` or a Core-level statement match — none of the three write paths use an
  ORM-tracked attribute set, so a session-level `before_flush` hook would have missed all three)
  that raises `sqlite3.OperationalError("database or disk is full")` at the one write that matters,
  then proves what survives and what does not:
  - FreeWeight `tests/integration/test_disk_full.py` — the third sample write in `native.echo`
    fails; that one *test* (not the run) is marked `failed`; the run still reaches `completed`;
    every other sample, including the next test's, is intact. This is finer-grained than the
    matrix's prior wording ("run aborted") — corrected in the same change (§4 below).
  - LoadCoach `tests/integration/test_disk_full.py` — a `QueueRuntime` built with a fault on the
    one `UPDATE jobs ... state='completed'` write; that job fails and releases its lease; a second
    job enqueued right after completes normally through the same runtime.
  - IdeaPress `tests/integration/test_disk_full.py` — `export_project` has no injectable writer, so
    this scopes a `monkeypatch.setattr(Path, "open", ...)` to only the export's own target path;
    proves `ExportFailed` names the path and the original error, nothing partial is left on disk,
    and clearing the fault lets the same export succeed. The matrix's prior wording ("temp file")
    was simply wrong — there is no temp-file staging anywhere in this codebase — corrected in the
    same change.
  - PromptCadence `tests/integration/test_disk_full.py` — a fault on the one `INSERT INTO turns`
    write; the failing trajectory is left exactly as `claim` left it (no partial turn or event); a
    sibling trajectory that already completed is untouched; clearing the fault lets the same
    trajectory finish. `LoopController.run()` has no generic exception handler around a turn
    boundary, so the failure propagates to the caller exactly as production's worker thread would
    see it — recovery there is the already-proven lease-expiry path (`test_recovery.py`), not a new
    catch this row added.
* **Database locked (SQLite)**, LoadCoach/IdeaPress/PromptCadence (FreeWeight already had
  `integration/test_transactions.py`), each `tests/integration/test_database_locked.py`: a real
  second connection holds a real `BEGIN IMMEDIATE` write transaction (the exact technique
  WeightsDB's own `test_sqlite_busy_timeout_raises_storage_busy` uses), and an ordinary write
  (`enqueue`, `ProjectService.create`, `TrajectoryService.submit`) is proved to surface the typed
  `weightsdb.StorageBusy` (`STORAGE_BUSY`) rather than hanging or crashing, creating nothing.
* **Database migration fails**, IdeaPress/PromptCadence (FreeWeight/LoadCoach already had ones),
  each `tests/integration/test_migration_failure.py`, following LoadCoach's own
  `test_failed_migration_restores_backup_on_sqlite` shape: a deliberately failing revision stacked
  on the real head, `MigrationFailed` raised with `details["restored"] is True`, and a row written
  before the failed upgrade survives untouched.

### 3.2 What was left untested, and why (two rows, documented behaviour that is not built)

Per the row's own instruction and ADR-0042: a documented behaviour with no implementation is left
`untested — behaviour not implemented, see L8 handoff` rather than proved with a test that would
really be asserting the row's own text back at itself.

* **LoadCoach's "incompatible API major version."** The cell reads "Client rejects with both
  versions named," describing LoadCoach as a client of FreeWeight's evidence API. Read
  `LoadCoach/src/loadcoach/infrastructure/freeweight_client.py`: it calls the fixed path
  `EVIDENCE_EXPORT_PATH = "/api/v1/evidence/export"` and never reads or checks any version field
  from the response. There is no code this test could exercise. (IdeaPress's and PromptCadence's
  own cells on this row, both about *their* LoadCoach clients, are unaffected and stay proved —
  row K1 closed those the same day, which is what made the kickoff's "(IdeaPress)" phrasing stale.)
* **IdeaPress's three machine-condition rows** (No GPU present, `nvidia-smi` missing or failing,
  GPU sensor unavailable). `show_telemetry_bar` (`IdeaPress/src/ideapress/web/rendering.py:53`) is
  a hardcoded `False` Jinja global, never overridden anywhere in the codebase or its tests.
  `sweatmeter` is imported exactly once, in `services/diagnostics.py`, only as a presence probe for
  a VRAM-preflight capability flag — never to read a `TelemetrySnapshot`. Spec §16 calls for
  "optional telemetry display" that "degrades per Cross-Platform Standards"; it does not exist yet.
  The three "D" cells in §2 are trivially true (the widget is unconditionally hidden, machine state
  or not), but there is no conditional behaviour for a test to exercise.

Building either is separate work — plausibly its own row, since the LoadCoach gap needs
`FreeWeightClient` to read and check a version field it currently ignores, and the IdeaPress gap
needs the `sweatmeter[telemetry]` wiring M9_REAUDIT's I5 already flagged as never installed by any
job. Neither was attempted here.

`docs/architecture/graceful-degradation.md` §2.1 was updated with all nine new test citations, and
§2 corrected for the two cells whose documented wording did not survive contact with a real test
(FreeWeight's and IdeaPress's disk-full rows) plus the two owed-work gaps (LoadCoach's API-version
cell, IdeaPress's three machine rows, the latter carrying a new footnote ⁴). `docs/architecture/*`
is workspace-only and is not mirrored to any component repo. Commit `docs` `448e4cb`.

Commits: FreeWeight `e199a14`, LoadCoach `93ddc03`, IdeaPress `dafc07f`, PromptCadence `220efbd`,
docs (graceful-degradation.md).

---

## 4. Item 4 — twelve TODO-stub test files

Found with `grep -rL "def test_" --include="test_*.py" <repo>/tests` in each of the four named
repositories — twelve files exactly, though distributed differently than the row's own count
implied (MirrorWall had five, not four; the other totals matched).

**IdeaPress (4 files → 3 deleted, 1 implemented):**
* `tests/unit/test_escalation.py` and `tests/unit/test_diminishing_returns.py` — deleted. Both
  journeys are already proved end to end by `tests/integration/test_review_loop.py`
  (`test_a_low_score_escalates_to_a_deep_audit_exactly_once_per_round`,
  `test_a_critic_that_never_converges_is_stopped_by_the_arithmetic`, P5).
* `tests/unit/test_repair_loop.py` — deleted. Already proved by
  `tests/integration/test_draft_to_commit.py`
  (`test_a_non_compliant_draft_is_repaired`,
  `test_an_unrepairable_unit_pauses_and_commits_nothing`, P4).
* `tests/e2e/test_full_project_journey.py` — implemented. Phase 9's acceptance criterion 3
  ("create -> plan -> draft -> export") had no single test driving the whole path; every other
  e2e file exercises one page or stage of a project some fixture already brought partway there.
  Now drives create, plan, draft (which chains validate/repair/commit internally) and both the
  read and write export paths, over HTTP with a scripted fake backend.

**FreeWeight (1 file, implemented):**
* `tests/e2e/test_full_journeys.py` — Phase 14's acceptance criterion 1 ("pip install -> serve
  -> run a benchmark -> export") was likewise never driven as one path. `install-check` (CI) only
  proves the install and that the server starts. Now drives a zero-configuration health check,
  discover, a benchmark to completion, and an export that names the run just produced.

**MirrorWall (5 files → 1 deleted, 4 implemented):**
* `tests/js/test_telemetry.py` — deleted. Already proved by
  `tests/js/test_sse_client.py::test_the_telemetry_module_renders_an_em_dash_with_a_reason_never_zero`.
* `tests/js/test_table.py` and `tests/js/test_theme.py` — implemented, each running the real
  shipped module in Node against a hand-rolled DOM (no jsdom in the dependency budget), the same
  approach `test_sse_client.py` already established. `test_table.py` proves sorting is gated on
  `data-complete`, a missing value sorts last in both directions, and column visibility persists
  via `localStorage`. `test_theme.py` proves choosing a theme applies/persists/announces it,
  `"system"` clears the override, a stored choice restores on reload, and a private-mode storage
  failure still lets the choice apply to the page in front of the reader.
* `tests/accessibility/test_keyboard_and_aria.py` — implemented: `drawer.js`'s hand-rolled focus
  trap (the one piece of interactive keyboard handling this package writes itself — `dialog.js`
  delegates entirely to the platform's own `<dialog>` element), the skip link's target, and
  `prefers-reduced-motion`.
* `tests/performance/test_render.py` — implemented against spec §15's three relevant budgets:
  template render ≤ 30 ms, table sort of 1000×20 ≤ 150 ms (measured in Node), JS shipped per page
  ≤ 60 KB.

**SetSpec (2 files, left untouched):** `tests/unit/test_errors.py` and `tests/unit/test_events.py`
test `src/setspec/error/v1.py` and `src/setspec/event/v1.py` — both are themselves TODO-stub
*source* files. `envelope.py`'s own docstring says so in the current tree: "Two payload types
remain unregistered even after Phase 6: `event.envelope` and `error.envelope` were planned for
Phase 3, which was never implemented." Writing tests against models that do not exist, or building
the models to give the tests something to assert, are both out of scope for a test-cleanup item —
left as documented, unmodified placeholders.

Commits: MirrorWall `c1aa0d5`, FreeWeight `9b4c7ac`, IdeaPress `fbdc8c6`.

---

## 5. Addendum — a flaky LoadCoach test, fixed mid-row on request

Not part of the original four items; added after the coordinator flagged a real CI failure found
during this row's run: `tests/integration/test_breaker_probe.py::test_a_probe_cancelled_before_it_reports_is_handed_back`
failed once on GitHub's v1.1.5 Release run (`_wait_terminal`'s 10 s deadline exceeded), passing
locally every time.

**Diagnosis.** The generation's `first_chunk_delay_ms=700` is a real `time.sleep` (needed so the
cancel genuinely lands mid-flight, not against a fake clock); ModelRack's fake provider
(`providers/fake.py`) only checks the cancellation token *after* that sleep returns, not during
it. The wait is bounded by one real, uninterruptible 700 ms sleep plus whatever the OS defers it
by under load — not by a worker poll cadence, so there was no cadence value to bound the deadline
by.

**Fix.** Widened `_wait_terminal`'s timeout for this one call from 10 s to 30 s with a `# ponytail:`
comment naming the ceiling, the same move PromptCadence's `9b3ce00` and FreeWeight's `5efec5d`
made the same day for the same class of real-wall-clock CI noise. Ran the file 20/20 green
(~13.2–13.3 s each — consistent with the real sleep, no other jitter), then LoadCoach's full gate.
What the test proves — cancellation eventually lands once the in-flight generation naturally
checks its token, the breaker releases to half-open, and nothing about the model is inferred from
a cancellation — is unchanged.

Commit: LoadCoach `7b68d10`, `test(worker): widen the cancel-probe wait past real-sleep CI noise`.

---

## 6. Gate results

Interpreter: each repo's own `.venv/bin/python`. `ruff format --check .`, `ruff check .`,
`mypy src tests`, `lint-imports`, `pytest -m "not live and not performance"` green in all eleven
repositories touched; `pytest --cov` at or above floor in each of the four applications before
the last commit in that repo.

| Repo | Interpreter | Tests | Coverage |
|---|---|---|---|
| SetSpec | 3.13.15 | 1074 passed, 4 skipped | — (package, no floor gate run beyond suite-wide) |
| ModelRack | 3.13.15 | 1435 passed, 16 skipped, 26 deselected | — |
| SweatMeter | 3.14.4 | 353 passed, 9 deselected | — |
| WeightsDB | 3.14.4 | 131 passed, 10 skipped, 6 deselected | — |
| MirrorWall | 3.14.4 | 331 passed, 3 deselected | 98.33 % (floor 95 %) |
| LoadLedger | 3.13.15 | 221 passed, 31 skipped, 6 deselected | — |
| Commissioner | 3.13.15 | 117 passed, 12 skipped, 2 deselected | — |
| FreeWeight | 3.14.4 | 2620 passed, 29 skipped, 30 deselected | 89.10 % (floor 85 %) |
| LoadCoach | 3.14.4 | 1052 passed, 5 skipped, 18 deselected | 90.64 % (floor 85 %) |
| IdeaPress | 3.13.15 | 1163 passed, 6 skipped, 30 deselected | 88.67 % (floor 85 %) |
| PromptCadence | 3.13.15 | 1293 passed, 3 skipped, 10 deselected | 91.60 % (floor 85 %) |

Every skip is a PostgreSQL leg with no server on this machine. `git status --short` was checked at
the start of the row (clean) and is clean in all fifteen repositories at the end of it (`docs`
included).

---

## 7. What the operator has to do

* Nothing is pushed, tagged or published — standing instruction. Push at will; nothing here bumps
  a version.
* Two owed gaps from item 3 (§3.2 above) are real, scoped work, not documentation debt:
  LoadCoach's `FreeWeightClient` needs to read and check FreeWeight's API version before this row's
  documented behaviour can be tested honestly; IdeaPress's telemetry display needs the
  `sweatmeter[telemetry]` wiring M9_REAUDIT's I5 already named. G20 (§7's gold standard, "every row
  of the degradation matrix has a test") can be turned on for every other row now; these two need
  either the build or a formal scope-out the way ADR-0111 scopes out ToolYard's podman rung.
* The gold-standards §1.1 table needed no correction (item 1) — worth noting only because the row
  asked "if the standard and pyproject disagree, say so"; they did not.
