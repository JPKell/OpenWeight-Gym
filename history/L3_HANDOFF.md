# L3 handoff — the operations promises get their tests

**Row:** L3 (Sonnet 5 · high), `docs/roadmap/outstanding-work.md` §1: "Operations promises get
their tests" (M9 Group 3).
**Components:** `FreeWeight`, `LoadCoach`, `IdeaPress`, `PromptCadence` (all `main`), `docs`
(`main`). Row L5 was running concurrently in the same four application repos on docs files; none
of the files it names (`docs/upgrading.md`, `CONTRIBUTING.md`, README compatibility tables,
`release.yml`, `tests/unit/test_*help*`, `tests/unit/test_troubleshooting_covers_doctor.py`,
`tests/security/test_checklist.py`) were touched here.

## 1. Gate results

Interpreter: each repo's own `.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/FreeWeight        # CPython 3.14
.venv/bin/python -m ruff format --check .   # 330 files already formatted
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/python -m mypy src tests          # Success: no issues found in 301 source files
.venv/bin/lint-imports                      # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov --cov-report=term-missing -q
                                             # 2611 passed, 29 skipped, 30 deselected
                                             # Required test coverage of 85.0% reached: 89.10%

cd /home/jpk/ai/suite/LoadCoach         # CPython 3.14
.venv/bin/python -m ruff format .           # 220 files left unchanged
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/python -m mypy src tests          # Success: no issues found in 200 source files
.venv/bin/lint-imports                      # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov --cov-report=term-missing -q
                                             # 1048 passed, 5 skipped, 18 deselected
                                             # Required test coverage of 85.0% reached: 90.68%

cd /home/jpk/ai/suite/IdeaPress         # CPython 3.13.15
.venv/bin/python -m ruff format .           # 1 file reformatted, 191 left unchanged
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/python -m mypy src tests          # Success: no issues found in 187 source files
.venv/bin/lint-imports                      # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov --cov-report=term-missing -q
                                             # 1156 passed, 6 skipped, 30 deselected
                                             # Required test coverage of 85.0% reached: 88.65%

cd /home/jpk/ai/suite/PromptCadence     # CPython 3.13.15
.venv/bin/python -m ruff format .           # 1 file reformatted, 186 left unchanged
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/python -m mypy src tests          # Success: no issues found in 182 source files
.venv/bin/lint-imports                      # Contracts: 5 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov --cov-report=term-missing -q
                                             # 1287 passed, 3 skipped, 10 deselected
                                             # Required test coverage of 85.0% reached: 91.60%
```

Every skip in all four repos is a PostgreSQL leg with no server on this machine (the new
both-dialects tests included) — see §3. `git status --short` was checked at the start and end of
every repo; each ended clean except LoadCoach, which carries row L2/L5's own uncommitted
`pydantic-settings` removal (`pyproject.toml`, `requirements/ci.lock`) — present before this row
started, untouched by it, and deliberately left for whoever owns that row to commit.

## 2. The commits

| Repo | Hash | Commit |
|---|---|---|
| FreeWeight | `7a4474a` | `test(ops): drive the SchemaAhead downgrade drill end to end` |
| FreeWeight | `2224705` | `test(ops): parametrize backup/restore over weightsdb.testing fixtures` |
| FreeWeight | `b904238` | `test(ops): add a released-version migration fixture (1.1.0)` |
| LoadCoach | `99ac5cf` | `test(ops): drive the SchemaAhead downgrade drill end to end` |
| LoadCoach | `0ddff9b` | `test(ops): parametrize backup/restore over weightsdb.testing fixtures` |
| LoadCoach | `73c8be2` | `test(ops): add a released-version migration fixture (1.0.0)` |
| IdeaPress | `38f45c5` | `test(ops): drive the SchemaAhead downgrade drill end to end` |
| IdeaPress | `b893ff1` | `test(ops): add backup/restore coverage from scratch` |
| IdeaPress | `84af6e0` | `test(ops): add a released-version migration fixture (1.3.0)` |
| PromptCadence | `4b77781` | `test(ops): drive the SchemaAhead downgrade drill end to end` |
| PromptCadence | `7e5b98f` | `test(ops): backup/restore on both dialects and a released-version fixture` |

**One deviation from "one commit per item," disclosed:** PromptCadence keeps its migration and
backup/restore tests in one file (`tests/integration/test_migrations.py`), unlike the other three
applications, which split backup/restore into its own file. Items 2 and 3 both land in that one
file there, so they went into one commit rather than two. Nothing else about the two items
changed shape.

Nothing is pushed, nothing is tagged, nothing is published — standing instruction.

## 3. What could only be proved by skip, locally

Every application gained one test parametrized `["sqlite", "postgresql"]`
(`test_backup_round_trips_or_refuses_restore_on_both_dialects`), built directly on
`weightsdb.testing.temporary_sqlite`/`temporary_postgres`. The PostgreSQL leg skips honestly with
`pytest.skip("no PostgreSQL server available...")` when `WEIGHTSDB_POSTGRES_URL` is unreachable —
true on every machine this row ran on — and turns into a hard failure under
`WEIGHTSDB_REQUIRE_POSTGRES=1`, which is exactly the flag the four applications' `db-matrix` CI
jobs (and FreeWeight's differently-named `postgresql-tests` job) already set. Nothing about the
PostgreSQL half of database standards §7 or packaging §6.1 was verified on this machine; all four
`db-matrix` jobs are where that proof actually happens.

## 4. What was found and fixed along the way

Writing "assert the bootstrap raises `SchemaAhead` naming both revisions and the backup directory"
against the real code surfaced two things the audit's own framing did not anticipate, in all four
applications:

* **The backup directory was never named.** FreeWeight's and LoadCoach's `SchemaAhead` raises
  already existed (`current not in runner.known_revisions()`) but carried only `current` and
  `head` in the message and `details` — packaging §6.1's "and the backup directory" half of the
  promise was simply not implemented. Both now compute the same directory `db backup`'s own
  default path would use (`_backup_directory(engine)`, added to each `services/database.py`) and
  name it in both the message and `details["backup_directory"]`.
* **IdeaPress and PromptCadence never detected a schema-ahead database at all.** Their
  `ensure_ready` went straight from `is_at_head()` to `if auto_migrate: runner.upgrade()` with no
  `known_revisions()` check in between. With `auto_migrate` true (the SQLite default), a database
  ahead of head would have hit `runner.upgrade()`, which alembic fails on its own terms — wrapped
  by WeightsDB into `MigrationFailed` after taking and immediately using a real backup, mislabeling
  a schema-ahead situation as a migration failure. With `auto_migrate` false it raised
  `MigrationRequired` instead, telling an operator to upgrade a database that is not behind — the
  opposite of correct. Both now carry the same `known_revisions()` check FreeWeight and LoadCoach
  already had, raising `SchemaAhead` with the backup directory named, before `auto_migrate` is ever
  consulted.

These are production-code fixes, not test-only additions, and they are what the row's own
generated tests are what caught them — none of the four applications' existing suites referenced
`SchemaAhead` by name before this row (matching the audit's own finding), so nothing had ever
driven this path.

**IdeaPress's bootstrap does not raise this at all, by design** — spec §20 AC7 makes an
unreachable or broken database a health condition, never a startup crash, so
`ideapress.services.runtime.Runtime` catches every `DatabaseError` and records `startup_error`
instead of propagating it. IdeaPress's test drives both: `ensure_ready` directly (proving the
refusal itself, the function every other application's bootstrap calls straight through), and
`build_runtime` (proving IdeaPress's own translation of the same refusal into a recorded string
rather than a raised exception) — this is the "or the application's translation of it" case the
row's own kickoff prompt anticipated.

## 5. Fixtures

One `.sqlite3` fixture per application, each built the same way: `/usr/bin/python3.13 -m venv`,
`pip install <app>==<version>`, `<app> db upgrade` against a fresh file, two rows seeded, copied
into `tests/fixtures/databases/`.

| App | Version | How seeded | Fixture head | This build's head |
|---|---|---|---|---|
| FreeWeight | 1.1.0 | Python: `SettingsRepository.set` (no CLI verb writes a setting) | `0008` | `0008` (no-op) |
| LoadCoach | 1.0.0 | Python: `SettingsRepository.set` | `0006` | `0014` (real upgrade) |
| IdeaPress | 1.3.0 | CLI: `ideapress project create` ×2 | `0009` | `0009` (no-op) |
| PromptCadence | 1.2.0 | CLI: `promptcadence token create` ×2 | `0011` | `0011` (no-op) |

Three of the four are currently no-ops (the fixture's version already sits at this build's head) —
that is a fact about how recently each package last shipped a migration, not a defect in the
fixture; each test asserts the upgrade *and* row survival regardless, and starts asserting a real
multi-revision migration the day the next one lands. Only LoadCoach's fixture (`0006` → `0014`)
exercises a real upgrade path today.

**All three of `.gitignore`'s `tests/fixtures/databases/` exceptions were missing before this
row** — LoadCoach, IdeaPress and PromptCadence all blanket-ignore `*.sqlite3` with no carve-out for
committed fixtures (only FreeWeight, which already had the rc1 fixture, had the exception). Without
it, `git add` would have silently accepted the new fixture locally while a fresh CI checkout saw
nothing — precisely the FreeWeight rc1 failure mode the row's kickoff named as a thing to check
for, and precisely what would have happened here without checking.

## 6. What the row and audit got wrong

* **The row's stated released versions were stale for two of four applications.** It named
  `loadcoach 1.1.2` and `promptcadence 1.3.0`; `pip index versions` on the day showed **loadcoach
  1.0.0** (only) and **promptcadence 1.2.0** as the newest PyPI-published releases. FreeWeight
  (1.1.0) and IdeaPress (1.3.0) matched. The row anticipated this ("check `pip index versions`");
  it just hadn't been re-checked since CLAUDE.md's component table was last written, which is
  itself stale in the same two places (also fixable, not done here — out of this row's scope).
* **"Keep fixtures < 200 KB" is no longer achievable for any of the four schemas.** Every fixture
  landed between 288 KB and 516 KB after `db vacuum` reported nothing reclaimable — the floor is
  SQLite's own per-table page overhead across a schema with 10–27 tables, not row count. FreeWeight's
  own `1.0.0rc1` fixture (472 KB, pre-existing) already exceeded the stated cap before this row
  touched anything, so the number was already aspirational rather than enforced.
* **The audit's "smallest change" description undersold item O2.** It reads as "write the test";
  in practice the test could not pass against the code as it stood in three of the four
  applications (§4) until the missing `SchemaAhead` detection and the missing backup-directory
  naming were added. The audit's own evidence section (Group 3) is accurate that "zero tests
  reference it" — it just didn't say that meant the promise itself was two-thirds unimplemented,
  not merely untested.

## 7. What the operator has to do

Nothing blocking. All four repositories are gate-green and committed on `main`, uncommitted only
where row L2/L5 already had files in flight (LoadCoach's `pyproject.toml`/`ci.lock`). Merge and
push at the operator's discretion, same as every other row this cycle.
