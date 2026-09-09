# I8 + I9 handoff — the runtime-settings surface, finished

**Rows:** I8 and I9 of `docs/roadmap/outstanding-work.md` §1, run as one row.
**Date:** 2026-09-07. **Both parts complete.** `promptcadence 1.1.0` was tagged (`v1.1.0`) and on
PyPI, so the version edge in the kickoff did not bind and Part 2 ran.

**Ships, prepared and neither tagged nor pushed:** `loadcoach 1.1.2` (release commit `1a3e2a7`,
two documentation commits after it — tag `8162f68`), `promptcadence 1.2.0` (`57b1e58`). A
2026-09-07 interview after both parts were green added four further decisions (§6a), which put
three commits on **FreeWeight** as well, riding its unreleased 1.1.0, and two new records:
**ADR-0101** and **ADR-0102**.

---

## 1. Gate results, per repository

### LoadCoach — `/home/jpk/ai/suite/LoadCoach`

Interpreter: `.venv/bin/python` → **Python 3.14.4** (CPython, the repo's own virtualenv).
Console scripts invoked as `.venv/bin/loadcoach`.

```bash
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy src tests
.venv/bin/lint-imports
.venv/bin/python -m pytest -m "not live and not performance" -q
.venv/bin/python -m pytest --cov --cov-report=term-missing -m "not live and not performance" -q
```

| Step | Result |
|---|---|
| `ruff format --check .` | clean |
| `ruff check .` | clean |
| `mypy src tests` | `Success: no issues found in 195 source files` |
| `lint-imports` | `Contracts: 4 kept, 0 broken.` |
| `pytest -m "not live and not performance"` | **1040 passed, 4 skipped, 18 deselected** in 126 s |
| `pytest --cov` | **90.48 %**, floor 85 % — `Required test coverage of 85.0% reached.` |

`pytest-randomly` was left on for every gate run; `-p no:randomly` was used only while iterating on
a single new file.

### PromptCadence — `/home/jpk/ai/suite/PromptCadence`

Interpreter: `.venv/bin/python` → **Python 3.13.15**. Console script `.venv/bin/promptcadence`.

```bash
.venv/bin/promptcadence config reference --check
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy src tests
.venv/bin/lint-imports
.venv/bin/python -m pytest --cov --cov-report=term-missing -m "not live and not performance" -q
```

| Step | Result |
|---|---|
| `config reference --check` | matches the settings model |
| `ruff format --check .` | clean |
| `ruff check .` | clean |
| `mypy src tests` | `Success: no issues found in 178 source files` |
| `lint-imports` | `Contracts: 5 kept, 0 broken.` |
| `pytest --cov` | **1270 passed, 2 skipped, 10 deselected**, **91.66 %** coverage |

**One flake, named rather than hidden.** The first full PromptCadence run reported
`tests/integration/test_runtime_settings_apply.py::test_the_running_worker_applies_a_write_within_one_reap_cadence`
failed — while a LoadCoach coverage run was saturating the machine in parallel. That test polls a
background worker thread against a ten-second wall clock, touches nothing this row changed, and
passed in isolation and in the idle rerun above (1270 passed). Treated as a load-timing flake, not
a regression; it is worth a `ponytail:`-style note in that file if it recurs on CI.

---

## 2. The gates as commits

### LoadCoach (5 commits on `main`, unpushed, `HEAD = 1a3e2a7`)

| Gate | Commit | Subject |
|---|---|---|
| A | `c9abf5d` | `fix(settings): the environment beats a stored row` |
| B | `d2eb8ad` | `feat(settings): the page and the API report a shadowed row` |
| C | `45463c0` | `feat(cli): config show marks database-sourced values` |
| D | `238f567` | `docs(config): the reference states the precedence it now implements` |
| E | `1a3e2a7` | `chore(release): loadcoach 1.1.2` |

### PromptCadence (2 commits on `main`, unpushed, `HEAD = 57b1e58`)

| Gate | Commit | Subject |
|---|---|---|
| F | `e80db43` | `feat(cli): promptcadence settings list\|get\|set` |
| G | `57b1e58` | `chore(release): promptcadence 1.2.0` |

`git status --short` is clean in both repositories. In `docs/`, `apps/loadcoach/api.md` and
`apps/promptcadence/spec.md` are modified by this row and **not committed** — see §6.

---

## 3. The five decisions

### D1 — do the two control flags follow the same precedence? **Yes, and the premise was wrong.**

**Decided: one rule for every key, no exception, no ADR.** But the reasoning in the kickoff does
not survive contact with the code, and the exception it worried about cannot occur.

`queue.paused` and `queue.draining` **are not fields of `loadcoach.config.Settings`**. `QueueSettings`
has no `paused` and no `draining`; `_configured()` reaches them only through
`getattr(section, setting.field, False)` and its `False` default. They are database-only settings
that borrow the registry's shape. So:

* `LOADCOACH_QUEUE__PAUSED=true` in a unit file does **not** make the console's pause button store
  a row that does nothing — it makes `load_settings()` raise
  `ConfigurationError: unknown configuration key 'queue.paused'` and the server refuses to start.
  The failure mode D1 was written to prevent is unreachable.
* Applying the one rule to them therefore costs nothing: `shadowing_source` is consulted for them
  like every other key and always answers `None` against a configuration the loader accepts. Their
  stored row is always the effective value.
* `tests/unit/test_runtime_settings.py::test_the_control_flags_take_the_same_path_and_have_no_configuration_layer`
  asserts both halves — the row is effective and reported as `database`, *and* setting the variable
  is refused by the loader.

**What the losing option would have claimed:** that an operator pausing dispatch from the console
is doing something urgent that a stale environment variable must not override, and that the flags
should take a stored row unconditionally. It would have bought nothing here (no variable can pin
them) at the cost of a second rule in the module and a per-key branch to read at 3am.

**A finding this exposed:** because they are not model fields, `queue.paused` and `queue.draining`
have **no row** in the generated `docs/configuration.md` — the reference's tables walk
`Settings.model_fields`. Gate D added a paragraph naming them and saying why they are absent,
rather than fabricating rows for keys that have no environment variable. A registry key with no
configured counterpart is arguably a shape worth an ADR of its own; it is pre-existing and out of
this row's scope.

### D2 — `LoadedSettings.sources`, or `os.environ`? **`os.environ`, with the guard test.**

**Decided: PromptCadence's `os.environ` check through a shared `env_var_for` helper.**

Plumbing `sources` was costed and rejected. `bootstrap()` holds `LoadedSettings`, but hands
`create_app(loaded.settings)` — **`Settings` only** — and `create_app` is documented as a pure
function of `Settings` "precisely so tests can build an app without touching the filesystem". The
map would have to reach `read_runtime_settings` through `app.state`, the scheduler/worker's
`self.settings`, and `web/routing_support.py`, changing `create_app`'s signature and every test
that builds an app. Well over the twenty-line budget, and it would weaken the one property that
makes `create_app` cheap to test.

So, exactly as PromptCadence does it, plus the two mitigations the kickoff asked for:

* `loadcoach.config.env_var_for(path)` is now the **one** spelling of a key's variable, used by
  `_track_sources` (the loader), `shadowing_source` (the new check) and available to anything else
  that needs it — the loader and the check cannot disagree about a name.
* `tests/unit/test_runtime_settings.py::test_no_source_module_passes_cli_overrides` scans
  `src/loadcoach/**.py` for `cli_overrides` and fails if any module other than `config.py` (where
  the parameter is defined) mentions it. The day someone adds a CLI configuration layer, one named
  test fails instead of the precedence silently mis-ordering.

**What the losing option would have claimed:** that `sources` is the honest answer because it
reports `cli` as well as `env`, and that ADR-0100's Consequences bullet names it explicitly
("`read_runtime_settings` should ignore a stored row whose key `LoadedSettings.sources` reports as
`env …` or `cli`"). It would have cost a signature change to a deliberately pure function and a
plumb through three call sites, to detect a layer that provably does not exist — and it would have
diverged from PromptCadence, which the kickoff names as the source. The ADR's bullet is advisory
about the mechanism; the behaviour it asks for is delivered.

### D3 — what the document says about a row that does nothing. **PromptCadence's shape, key for key.**

Each entry in `definitions` gains `stored` (the row, or `null`), `source` (`"database"` when the
row is what the process runs on, else `"configuration"`) and `shadowed_by` (`"env LOADCOACH_…"`,
else `null`). The Settings page prints the same sentence PromptCadence's does, beneath the field it
belongs to. **A shadowed row is kept, never deleted** — proved in both directions live (§4).

`config show`'s shadow label is one string rather than three fields, because it has one column:
`(env LOADCOACH_STORAGE__CONTENT_RETENTION_HOURS; database row 12 shadowed)` — transcribed from
PromptCadence's `_database_overlay`.

**What the losing option would have claimed:** that a row which cannot take effect should be
deleted on write, so the table never holds a lie. It would make `PUT /settings` destructive in a
way no caller asked for, and unsetting the variable would silently revert to the file instead of
restoring what the operator stored.

### D4 — the verb's shape. **`settings list | get <key> | set <key> <value>`, client mode.**

As recommended. `list` and `get` are `read`-scoped, `set` is `admin`; `--token`, else
`$PROMPTCADENCE_API_TOKEN`; `--json` on all three; `--config` on all three, matching the
neighbouring commands.

Two details worth naming:

* **The registry is never restated in the CLI.** `list` renders whatever the document carries,
  `get` refuses a key the document does not define and lists the ones it does, and `set` sends the
  value for the server to validate. A key added to `services/settings.py` needs no change in
  `cli/commands/settings.py`. When the API refuses an unknown key it sends
  `details.runtime_changeable`; the CLI prints that list rather than one of its own
  (`_echo_changeable_set`).
* **`set` parses its value as JSON** (`3`, `0.8`, `true`), falling back to the raw string so the
  server refuses it by name and type rather than the CLI guessing. `set` then prints the key's
  **effective** value and, when `shadowed_by` is set, a second line naming the variable — a
  shadowed write does not read as a success.

**What the losing option would have claimed:** that `settings set` should also work with the server
stopped, by opening the database the way `config show` does. That would put a second writer on the
`settings` table outside the API's scopes, and it would make the CLI enforce authorization itself
rather than presenting a token. `promptcadence config show` already answers the read-side question
for a stopped install, and the docs say so.

### D5 — exit codes. **The repo's existing mapping, reused rather than restated.**

`_request` delegates every refusal to `promptcadence.cli.commands.trajectories._envelope_error`,
the same function `approve`/`deny` use, and every transport failure to `_fail_unreachable`. So:

| Situation | Code | Exit |
|---|---|---|
| A security-relevant key | `FORBIDDEN` | **1** |
| An unknown key, or a value out of bounds | `VALIDATION_ERROR` | **2** |
| No token on a tokened install | `UNAUTHORIZED` | **1** |
| Configuration itself invalid | (local) | **3** |
| Server unreachable | — | **4** |
| The CLI's own unknown-key refusal in `get` | `VALIDATION_ERROR` | **2** |

`set` exits non-zero on every refusal. Note the API's missing-token code is `UNAUTHORIZED`, not
`UNAUTHENTICATED`.

---

## 4. Exit conditions, answered

### Part 1 (LoadCoach)

1. **Full gate green on a named interpreter, coverage at or above the floor.** Yes —
   Python 3.14.4, 1040 passed, 90.48 % against an 85 % floor. §1 names every invocation.
2. **`PUT /settings` under a pinned environment variable.** Proved **live**, not only in tests,
   against `loadcoach serve` on port 8791 with
   `LOADCOACH_STORAGE__CONTENT_RETENTION_HOURS=72`:
   `PUT {"storage.content_retention_hours": 6}` answered
   `effective 72`, `"stored": 6`, `"source": "configuration"`,
   `"shadowed_by": "env LOADCOACH_STORAGE__CONTENT_RETENTION_HOURS"`. Restarted **without** the
   variable, the same database answered `effective 6`, `source database`, `shadowed_by null`, and
   `/settings` rendered "Stored here, and effective." The row was never deleted.
   Also covered by `tests/e2e/test_settings.py::test_a_row_the_environment_shadows_is_reported_and_not_applied`,
   which exercises both directions in one process.
3. **`config show` marks `(database)`; with no database prints what 1.1.1 printed and creates no
   file.** Proved live on a scratch XDG tree:
   * no database → `storage.content_retention_hours  24  (default)` and
     `ls: cannot access …/lc.sqlite3: No such file or directory` — **no file created**;
   * with a stored row → `storage.content_retention_hours  12  (database)`;
   * with the variable set → `72  (env LOADCOACH_STORAGE__CONTENT_RETENTION_HOURS; database row 12 shadowed)`.
   Four unit tests cover the same paths, including the unmigrated database.
4. **`docs/configuration.md` regenerates and its test passes; `cmp` silent for mirrored files.**
   Regenerated with `.venv/bin/loadcoach config reference --output docs/configuration.md`;
   `tests/unit/test_config_reference.py` (4 tests) passes.
   `cmp docs/apps/loadcoach/api.md ../LoadCoach/docs/apps/loadcoach/api.md` — silent.
5. **`git status --short` clean, work committed, nothing pushed.** Yes. No `git push` was run, not
   even a dry run.

### Part 2 (PromptCadence)

1. **Full gate green, coverage at or above 85 %.** Yes — Python 3.13.15, 1270 passed, 91.66 %.
2. **`settings set execution.step_retries 3` against a running server, read back by `get`.**
   Proved live against `promptcadence serve` on port 8793:
   `execution.step_retries = 3 (database)` from `set`, and the same line from `get`.
3. **`set server.host` prints `FORBIDDEN` naming the key and exits non-zero; an unknown key gives
   `VALIDATION_ERROR` listing the changeable set.** Live:
   `Error: server.host is security-relevant and can only be set in config.toml or the environment
   (spec §14). (FORBIDDEN)` → exit **1**; and for `execution.nonsense`,
   `changeable: compaction.threshold, execution.max_turns_per_step, execution.step_retries,
   planning.corrective_retries, storage.content_retention_hours` then
   `Error: execution.nonsense is not runtime-changeable. (VALIDATION_ERROR)` → exit **2**.
4. **With the key pinned in the environment, `set` reports the stored value as shadowed rather than
   applied.** Live, with `PROMPTCADENCE_EXECUTION__STEP_RETRIES=7`:
   ```
   execution.step_retries = 7 (env PROMPTCADENCE_EXECUTION__STEP_RETRIES (stored 2 shadowed))
   stored 2, but env PROMPTCADENCE_EXECUTION__STEP_RETRIES beats it: the row does nothing until that variable is unset.
   ```
   `settings list` shows the same source string on that row and `(configuration)` on the other four.
5. **`cmp` silent for every mirrored document; `docs/openapi.json` differs only in `info.version`.**
   `cmp apps/promptcadence/spec.md ../PromptCadence/docs/apps/promptcadence/spec.md` — silent.
   `git diff docs/openapi.json` is exactly `-    "version": "1.1.0"` / `+    "version": "1.2.0"`.
   LoadCoach's own `docs/openapi.json` diff is the same one line, `1.1.1` → `1.1.2`.
6. **`git status --short` clean in both repositories, work committed, nothing pushed.** Yes.

---

## 5. Things the kickoff said that turned out not to be true

Line numbers are omitted below where they had moved; the reasoning matters more than the citation.

1. **D1's premise is false, and that is the substantive correction.** "`LOADCOACH_QUEUE__PAUSED=true`
   in a unit file would make the console's pause button store a row that does nothing" — it would
   make the server refuse to start with `unknown configuration key 'queue.paused'`, because
   `QueueSettings` has no such field. The flags are database-only. The decision the kickoff
   recommended is still the right one; the danger it was weighed against does not exist. See §3 D1.
2. **"`RUNTIME_SETTINGS` holds seven keys, two of them booleans"** — true, but the description
   "four `routing.*` floats … and `storage.content_retention_hours`" implies all seven are
   `Settings` fields. Five of them are; the two booleans are not.
3. **"`src/loadcoach/bootstrap.py:45` holds a `LoadedSettings` (with its `sources` map). Whether
   that map reaches the serving process is D2 below."** It is `bootstrap()` (further down the file)
   that holds it, and the answer is **no**: `Application` carries `loaded_settings`, but the ASGI
   app is built by `create_app(loaded.settings)` and nothing downstream ever sees `sources`. The
   line reference had moved; the question was the right one to ask.
4. **"If LoadCoach's Runtime-changeable column is a literal rather than driven by
   `RUNTIME_SETTINGS`, drive it from the registry."** It was already driven from the registry
   (`runtime = "yes" if key in RUNTIME_SETTINGS else "no"`). No change was needed. What *was*
   missing from the reference was the precedence sentence and the note about the two flags with no
   row.
5. **D4's "`VALIDATION_ERROR` listing what may change"** described behaviour the API does not have
   in its *message*: the set is in `details.runtime_changeable`, and `_envelope_error` prints only
   the message. The CLI now prints that detail explicitly (`_echo_changeable_set`); without that
   line the exit code would have been right and the operator would still not have seen the
   vocabulary.
6. **The missing-token error code is `UNAUTHORIZED`, not `UNAUTHENTICATED`.** Minor, but it was
   asserted in a first draft of the test and is worth recording for the next transcription.
7. **`CHANGELOG.md` `[Unreleased]` → `## [1.1.2]`.** LoadCoach's changelog had **no**
   `[Unreleased]` section at all (1.1.1 was the top). One was added, empty, above the new 1.1.2
   entry, so the next row finds the section the house shape expects.

---

## 6. What the operator still has to do

1. **Tag and publish LoadCoach 1.1.2**: `git tag -a v1.1.2` on `1a3e2a7`, push, approve the `pypi`
   environment, publish.
2. **Tag and publish PromptCadence 1.2.0**: `git tag -a v1.2.0` on `57b1e58`, push, approve the
   `pypi` environment, publish.
3. **Push four repositories**: `LoadCoach` (7 commits), `PromptCadence` (2 commits), `FreeWeight`
   (3 commits, riding its unreleased 1.1.0 — nothing to tag or publish here yet), and `docs`.
4. **`roadmap/outstanding-work.md` is left modified and uncommitted in `docs/`, and it is not this
   row's change** — row I6 was running against the same workspace and holds that file. The docs
   commit staged only `apps/loadcoach/api.md`, `apps/promptcadence/spec.md` and this handoff, by
   name. Rows I8 and I9 were therefore **not** marked done in `outstanding-work.md`; that edit
   belongs to whoever lands I6's work.
5. **A note before pushing LoadCoach migrations** (carried forward from H4, unchanged by this row):
   run the suite with `WEIGHTSDB_REQUIRE_POSTGRES=1` first. This row adds no migration.

**Decided at the interview (D6):** `pip index versions loadcoach` reports **only `1.0.0` on
PyPI** — `v1.1.0` and `v1.1.1` are tagged locally and were never published. Publish **1.1.2 only**;
it supersedes both and the two tags stay as repository history.

---

## 6a. The 2026-09-07 interview — four further decisions, and what was built from them

Asked after the row's two parts were green. Each is recorded here rather than as a separate
document because each changed what shipped.

### D6 — the two unpublished LoadCoach tags. **Publish 1.1.2 only.**

`v1.1.0` and `v1.1.1` are tagged locally and absent from PyPI, which carries `loadcoach 1.0.0`
alone. 1.1.2 supersedes both and carries their changes, so PyPI jumps 1.0.0 → 1.1.2 and the two
tags stay as repository history. **What the losing option would have claimed:** that PyPI's history
should match the repository's, which would mean three approvals, three workflow runs, and each
older tag building green against today's lock — for versions no consumer is pinned to, because
none was ever published.

### D7 — FreeWeight's `(database)` gap. **Fixed now, as a third part.**

`freeweight config show` opened no database and so never marked a database-sourced value, breaking
configuration standards §7's third rule in the third application. Transcribed from LoadCoach's fix:
`_database_overlay`, the same never-raises and never-creates-a-file discipline, four tests, and one
sentence in the generated reference's header. Proved live on a scratch tree:
`telemetry.interval_ms  500  (database)`, and with the variable set,
`250  (env FREEWEIGHT_TELEMETRY__INTERVAL_MS; database row 500 shadowed)`, and no file created when
none exists. **FreeWeight's precedence was already correct** — `read_settings` has computed
`from_env` and `overridden_by_env` since it was written — so only the reporting was missing.
Commit `1f37cdc`, on FreeWeight's unreleased 1.1.0.

### D8 — the configuration-less keys. **ADR-0101.**

`queue.paused` and `queue.draining` are runtime-changeable keys that are not configuration keys, a
shape the standards never described (see D1 above for how the row found it). ADR-0101 names it,
states that the one precedence rule still applies unchanged, explains why the generated reference's
tables cannot list them, and gives the test for admitting another: a pause is operational state, a
threshold is configuration. Adding the two to `QueueSettings` for uniformity was refused — it would
create the shadowing hazard they are currently immune to. LoadCoach's api.md §9 and its reference
header now cite the record instead of explaining it twice (`bf27301`, `8162f68`).

### D9 — the three near-copies of one registry. **Converged, and it cost more than the question implied.**

The decision was to converge FreeWeight onto LoadCoach's and PromptCadence's shape. Two findings
came out of doing it, and the second changed the plan:

* **The free half was real and is done.** `FREEWEIGHT_<SECTION>__<FIELD>` was spelled out in three
  places — the loader's source tracking, `RuntimeSetting.env_var` and the reference generator.
  `env_var_for` is now the one spelling all three call, matching the other two applications. The
  generated document is byte-identical (`dae2319`).
* **The rest is a breaking wire change, and ADR-0013 forbids it.** FreeWeight's
  `GET /api/v1/settings` returns `{items: [...]}` with `value`/`stored_value`/`overridden_by_env`
  and a `source` vocabulary of `"env"`/`"database"`/`"file or default"`; the other two return
  `{settings, definitions}` with `configured`/`stored`/`source`/`shadowed_by`. Rewriting a `v1`
  response is not additive, and ADR-0013 requires a `/api/v2` with a deprecation window for that —
  a second API major in FreeWeight to rename four fields.

  So it was done **additively**, which is what ADR-0013 permits: the body now carries both
  renderings. `settings` and `definitions` are added in the suite's vocabulary (plus `unit`,
  `choices` and `env_var`, which FreeWeight's page needs and the other two have no use for);
  `items` is unchanged, deprecated, and removed when FreeWeight next has an `/api/v2`. Recorded as
  **ADR-0102**. Commit `320ec27`.

  Two things fell out of building it, both worth reading:

  1. **`configured` was unanswerable.** FreeWeight folded stored values over its settings object
     during startup and kept only the result, so "what was configured" no longer existed in the
     process — exactly what ADR-0100 refused for PromptCadence. The lifespan now keeps the pristine
     object beside the applied one.
  2. **The two renderings can honestly disagree.** `items[*].value` reports the value folded in
     when the process *started*; `settings` applies the stored row at read time, so it answers
     "what will the next run use". Proved live: after `PUT {"telemetry.interval_ms": 2000}`,
     `settings` reads 2000 and `items[*].value` reads 1000, with `stored: 2000` and
     `source: "database"` beside both. That is a defect in `items`, and it is one of the reasons
     `items` is the half being deprecated rather than the half being kept.

**What the losing options would have claimed.** Converging the other two onto FreeWeight would
break a contract `promptcadence 1.1.0` has already published and that `loadcoach 1.1.2` was
prepared with hours earlier. Extracting a shared layer-3 package would be an abstraction over three
registries with three refusal policies, two `kind` vocabularies and — until this change — two
response shapes; ADR-0102 removes the shape half of that objection and leaves the question open for
a fourth application. Stopping at `env_var_for` was the recommendation and was overruled; the
additive route delivered the convergence without the breakage the recommendation was protecting.

### FreeWeight's gate, for the record

Interpreter `.venv/bin/python` → **Python 3.14.4**. Same six invocations as §1.
`ruff format --check` clean, `ruff check` clean, `mypy src tests` → *no issues found in 299 source
files*, `lint-imports` → *4 kept, 0 broken*, `pytest -m "not live and not performance"` →
**2603 passed, 28 skipped, 30 deselected**, `pytest --cov` → **88.28 %** against an 85 % floor.
Three commits on `main`, unpushed: `1f37cdc`, `dae2319`, `320ec27`. Nothing tagged; FreeWeight's
1.1.0 remains unreleased and these ride it.

---

## 7. Findings that belong to another row

The first three findings this row recorded were **acted on** at the interview and are written up in
§6a: FreeWeight's `(database)` gap (D7, fixed), the configuration-less keys (D8, ADR-0101) and the
three near-copies of one registry (D9, ADR-0102). What remains open:

1. **FreeWeight's OpenAPI snapshot had been stale since the 1.1.0 version bump.** `docs/openapi.json`
   still said `"version": "1.0.0"`, and no test caught it:
   `tests/integration/test_integration_milestones.py` compares **path keys only**, where LoadCoach
   and PromptCadence compare the document byte for byte. This row regenerated it, so the immediate
   drift is closed, but the guard is still weaker than the other two applications' and will let the
   next drift through. A one-line change to that assertion, in whichever row next opens FreeWeight.
2. **FreeWeight raises at startup on a stored row it cannot coerce**, where LoadCoach and
   PromptCadence fall back to configuration and keep serving. `apply_stored` feeds stored values
   through `Settings.model_validate`, so a row written by a version with wider bounds stops this
   one from starting. The other two treat that as "a row this build cannot read" and serve the
   configured value. A real robustness difference, named in ADR-0102's Consequences and not fixed
   there.
3. **FreeWeight's refusal is an allowlist and the other two are blocklist-plus-registry.**
   `RUNTIME_SETTINGS` enumerates what may change, so a security-relevant key nobody remembered to
   forbid is config-only by default. That is the **stronger** direction, and it is FreeWeight that
   has it. If the three ever converge further, they should converge on this, not away from it.
4. **The registry is still three implementations.** ADR-0102 settled the wire shape; the internal
   divergence remains — a string `kind` with a `"choice"` variant against a Python type, `unit` and
   `choices` in one of the three, and three `coerce` implementations. The layer-3-package question
   is deliberately left open, and ADR-0102 says when to ask it again.
5. **`test_the_running_worker_applies_a_write_within_one_reap_cadence` is load-sensitive** (§1). It
   polls a worker thread on a ten-second wall clock and failed once under a parallel test run. If
   CI ever goes red there, it is the clock, not the settings.
