# Kickoff — E3: Commissioner Phase 2, the ledgers and the mounting, `commissioner 0.1.0`

**Row:** E3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Sonnet 5 · standard**, as scheduled. Note the *standard* — this row is the second
copy of a pattern that is already proven twice, not a design row. If you find yourself designing,
stop and check §2.1 first: the answer is almost certainly already written in `docs/history/C3_HANDOFF.md` §11.
**Repositories:** `/home/jpk/ai/suite/py/Commissioner` (Python **3.13.15**, coverage floor **95 %**),
plus `/home/jpk/ai/suite/docs` for any amendment you propose.
**Ships:** a **first publish** — `commissioner 0.1.0`.
**You prepare the release and stop at the tag.** Tagging, the `pypi` environment approval and the
post-publish install check are the human's ([outstanding-work §4](docs/roadmap/outstanding-work.md)).
No push either: commit on `main` and stop.

**Overnight:** permitted. Batch E is on none of
[model-assignment §2.12](docs/roadmap/model-assignment.md)'s never-overnight lists, and Sonnet rows
run at effort **high** overnight — one step above this row's scheduled *standard*, which is fine.

**This row is M10's last package.** [outstanding-work §5](docs/roadmap/outstanding-work.md) makes
M10 "all four packages at 0.1.0, clean-venv acceptance scripts pass", and E1/E2 delivered CutCtx
and ToolYard on 2026-09-03. Commissioner is the fourth.

---

## ✅ Read this first — the good news, and the one thing that is different

**Unlike E2, `main` is green and there is nothing to fix before you start.** Commissioner is at
`7077cc4`, pushed, with nothing unpushed. I checked the two things that bit E2:

* `.github/workflows/ci.yml:136` runs `python -c "import commissioner"` — **correct**. (ToolYard's
  ran `import cutctx` for three phases because the toolchain was copied and never adapted. This
  one was adapted.)
* `grep -rn spotcheck` over the repository's `.yml`, `.toml`, `.md`, `.py` and `.importlinter`,
  excluding the mirrored `docs/`, finds **nothing**. The B3 rename was thorough.

**What *is* different from every row before it: this one needs a database.** Phase 2 is
`SqlEgressLedger` and `mount_egress_tables`, and the PostgreSQL leg is not optional —
`docs/history/C3_HANDOFF.md` is explicit that a silently skipped dialect is an untested dialect. **Docker 29.7.2
is running on this machine**, so unlike E2's podman blocker you *can* run the Postgres leg here,
and you are expected to:

```bash
docker run -d --name commissioner-pg -e POSTGRES_USER=commissioner \
  -e POSTGRES_PASSWORD=commissioner -e POSTGRES_DB=commissioner_test \
  -p 5432:5432 postgres:16
```

There is **no postgres server and no `psql` on this machine otherwise**, and
`py/Commissioner/.github/workflows/ci.yml` has **no `db-matrix` job** — you add one, copying
LoadLedger's (`py/LoadLedger/.github/workflows/ci.yml` line 72) with three name changes.

---

## The one instruction that matters most

**`docs/history/C3_HANDOFF.md` §11 was written for this row, by the session that built the thing you are
copying.** It is at the workspace root, it names what to copy unchanged, what to rename, two traps
that cost that session time, and one thing its author would do differently. Read it before you read
anything else, and treat it as the design document. This row's risk is not getting the design wrong;
it is re-deriving a design that already exists and arriving somewhere slightly different, which is
how two copies of a pattern start to drift.

Then read **`docs/history/C3_HANDOFF.md` §2** — the five settled shapes, whose heading says outright
*"decisions E3 and J1 must not relitigate"*.

---

## Preconditions

* **`git status --short` must be empty** in `py/Commissioner` and `docs` before you start.
  `git checkout --` anything modified that you did not edit.
* Commissioner is at `7077cc4`, **pushed**, `0` commits ahead of `origin/main`, version
  `0.1.0.dev0`, and its CI is green. Phase 1 (row B3) is complete: `types.py`, `policy.py`,
  `errors.py` and three unit test modules.
* **Its dependencies are published**: `baseaicore 0.4.1` and `setspec` (0.5.x) are both on PyPI.
  `loadledger 0.1.0` is on PyPI too — you do **not** depend on it, you copy from its source tree.
* **The PyPI name `commissioner` is free** — checked 2026-09-03, returns 404. Master architecture
  §1.1 requires availability verified before a first publish; it is verified. Reserving it is an
  operator step and must happen **before** the tag.
* **You are not authorised to push, tag or publish.** Prepare the release, stop at the tag, and say
  plainly in the handoff what is waiting.

## Setup

```bash
cd /home/jpk/ai/suite/py/Commissioner
source .venv/bin/activate
pip install -e ".[dev]"
git status --short                # must be empty before you start
python --version                  # confirm 3.13.15 rather than copying it from here
```

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository, and nothing at its root is versioned. Every multi-step shell command
  starts with an absolute `cd` (D1 §14 explains what happened the one time that was skipped).
* **Read before writing**, in this order:
  [`architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, then
  Commissioner's section of [`standards/gold-standards.md`](docs/standards/gold-standards.md) §2,
  then the row's reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations`; units in every numeric name; keyword-only for anything optional; injected clocks and
  session factories; `mypy --strict`; line length 100.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **95 %**, `CHANGELOG.md` updated,
  one Conventional Commit per logical group. **Name the interpreter and the exact invocation in the
  handoff** (M5C-13).
* **Documentation is mirrored.** Anything amended under `/home/jpk/ai/suite/docs/` is edited in the
  workspace copy **first**, then re-copied into `py/Commissioner/docs/` and proven with `cmp`. Do
  not reflow markdown you edit.
* **A new public name is a spec amendment, proposed, not a quiet deviation.** C1, C2, D1, E1 and E2
  all did this and every amendment was accepted — follow that precedent, docs first, in the same
  commit.

---

## 2.1 Reading list

1. **`docs/history/C3_HANDOFF.md` §11 and §2** — above. The design document for this row.
2. [`packages/commissioner/development-plan.md`](docs/packages/commissioner/development-plan.md)
   **Phase 2** — the work, the tests, the acceptance criteria, and the two named failure modes:
   *"a query path added for a UI that quietly becomes an update path"* and *"dialect-specific enum
   storage."* Both are testable here and both are load-bearing.
3. [`packages/commissioner/spec.md`](docs/packages/commissioner/spec.md) — **§7** (`EgressLedger`,
   `InMemoryEgressLedger`, `SqlEgressLedger(session_factory, *, table_prefix="egress_")`,
   `mount_egress_tables(metadata, *, prefix="egress_") -> EgressTables`), **§10** (data ownership),
   **§13**, **§18** and **§20** — criteria 1 and 2 are this row's exit.
4. [ADR-0050](docs/adr/0050-mountable-tables-and-host-owned-migrations.md) — the mounting rule, and
   its "revisit when" clause, which matters here: **E3 is the second mountable package, so copying
   by hand is right; J1 is the third and is the extraction point.** Say so in the handoff.
5. [ADR-0006](docs/adr/0006-sqlite-by-default-postgresql-supported.md) — SQLite by default,
   PostgreSQL supported, nothing else. Both dialects, both green.
6. **`docs/history/B3_HANDOFF.md` §3** (the public surface as built) and **§9** (the SpotCheck → Commissioner
   rename) — what Phase 1 left you.
7. The code you are copying, in this order: `py/LoadLedger/src/loadledger/sql.py`, then
   `memory.py`, then `py/LoadLedger/tests/integration/` entire, then
   `py/LoadLedger/tests/conftest.py`'s database harness.

## 2.2 `ledger.py` and `sql.py`

Copy the shape; do not redesign it. `docs/history/C3_HANDOFF.md` §11's "copy, unchanged in shape" list is the
specification: `mount_egress_tables`'s prefix validation and explicitly named `pk_`/`ix_`
constraints, `EgressTables` as a frozen slotted dataclass, `_insert_for`, `_writing()`/`_reading()`,
`_as_utc`/`_from_utc`, and `canonical_json` in a `TEXT` column.

**Three things are Commissioner's and not LoadLedger's:**

* **The ledger is append-only, and that is a surface property rather than a convention.** The
  development plan's test list says *"API-surface test: no mutation path exists"*, and its named
  failure mode is a query path that quietly becomes an update path. Assert it structurally — the
  way ToolYard's `test_boundaries.py` asserts "one `Popen`" — not by reviewing the module.
  `_reading()` rolling back rather than committing is what makes "this path has no side effects"
  mechanical; C3 §11 notes Commissioner wants it *more* than LoadLedger does.
* **You may need only the insert half** of the dialect pair. LoadLedger's `_upsert_sum` and
  `_note_run` exist for accumulating money rows; an append-only decision ledger has nothing to
  accumulate. **Keep the `UnsupportedDialect` refusal either way** — a third dialect must be refused
  rather than half-supported.
* **`Verdict` is an enum going into a column**, and the plan names *dialect-specific enum storage*
  as a failure mode. Store the `.value` as text and convert at the boundary; do not use
  `sa.Enum`, which creates a native type on PostgreSQL and a check constraint on SQLite, so the
  same code produces two schemas. A test that reads a row written by the other dialect's shape is
  the one that catches it.

**C3's own advice, and take it:** *"decide the table set after deciding the concurrency mechanism,
not before."* Work out how a decision row is written under concurrent writers first, and let the
shape follow. LoadLedger's fourth table exists only because an atomic increment cannot operate on a
JSON mapping — an hour of reordering was the cost of doing it the other way round.

## 2.3 The tests, and the trap that is not in the plan

Copy `tests/integration/` whole: the `postgres_url` harness (twenty lines, **no `weightsdb`
import**), the `database_url`/`engine` fixture pair, the miniature host, and
`ledger_subprocess.py`'s engine-listener fault injection with its deliberately broken subclass that
proves the assertion bites.

**Rename throughout:** `ledger_` → `egress_`; `LOADLEDGER_POSTGRES_URL` /
`LOADLEDGER_REQUIRE_POSTGRES` → `COMMISSIONER_*`; the conftest's `DEFAULT_POSTGRES_URL` credentials
and the CI service's `POSTGRES_USER`/`POSTGRES_DB`.

**Two traps, both already paid for once:**

* **Put the database harness in the single top-level `tests/conftest.py`.** With no `__init__.py`
  under `tests/`, a second `conftest.py` puts two modules on `sys.path` under the same name and
  `from conftest import …` resolves to whichever pytest inserted last. This cost C3 time; it need
  not cost it twice.
* **A green `pytest` and a green `pytest --cov` are not the same gate when a test spawns a child
  process.** C3 shipped a red `main` because of exactly this: a child run with `cwd=` set to a
  temporary directory cannot find `pyproject.toml`, so pytest-cov measures it *without*
  `branch = true` and the combine step dies with `Can't combine statement coverage data with branch
  data` — **after** reporting every test as passed. The standing gate runs `pytest` without
  `--cov`, so it stayed green throughout. **This row copies that harness, so run the `--cov` form
  locally before you call yourself done**, and strip `COV_CORE*`/`COVERAGE*` from any child's
  environment the way `68c3277` does.

Performance: the plan wants filters (run, verdict, target, since) over **100 000 rows** within
budget. Note that C3's §6 records one missed budget honestly rather than tuning until it passed —
if one of yours misses, say so and say by how much.

## 2.4 The `[sql]` extra, the locks, and CI

* **Declare the `[sql]` extra in the same commit that first imports SQLAlchemy.** `pyproject.toml`
  currently says, in a comment, that there is no `sql` extra yet because declaring it ahead of the
  module *"would advertise an import that does not exist"*. That comment is now out of date and the
  commit that lands `sql.py` is the one that fixes it. Match LoadLedger's pin.
* **Regenerate both locks** with the recorded commands in `requirements/README.md` and commit them.
  They were generated with **pip-tools 7.6.1**. `release.lock` must stay byte-identical below its
  header to CutCtx's, LoadLedger's, WeightsDB's, MirrorWall's and **ToolYard's** — verify it rather
  than assuming it. (E2 checked this on 2026-09-03: those five agree; **ModelRack's is two pins
  behind** and is a known, separate item.)
* **Add the `db-matrix` job** to `.github/workflows/ci.yml`, copied from LoadLedger's line 72 with
  the three name changes. It sets `COMMISSIONER_REQUIRE_POSTGRES=1`, which turns the local skip into
  a failure — that is the point of it.
* **`.importlinter`**: SQLAlchemy becomes permitted in `commissioner.sql` and nowhere else, exactly
  as LoadLedger constrains it. Check whether the exemption is already written (C2 and D1 wrote
  ToolYard's two phases early); if it is, you add a module and change no boundary rule. **Never
  weaken or delete a contract to make an import work.**

## 2.5 Exit, and the release preparation

Spec §20 criteria 1 and 2 are the exit, and **criterion 2 needs a committed, runnable script**:
*a `setspec`-only script reads a decision exported by PromptCadence and prints its verdict — no
Commissioner installed.* That is the payload-is-the-contract claim, and it is only proven by a
script that runs in a virtualenv holding `setspec` and **not** `commissioner`.

Follow E1's and E2's precedent, which the operator has now seen twice: an `acceptance/` directory,
a script that **exits non-zero when a claim fails** rather than printing and returning 0, and a
recorded clean-venv run. M10's exit condition is *"clean-venv acceptance scripts pass"*, and a
script that only printed things would pass while being wrong. Note that this criterion needs **two**
venvs — one with `commissioner[sql]` to produce and export the decision, one with `setspec` alone to
read it.

Then the release-prep commit, and stop: `src/commissioner/__about__.py` `0.1.0.dev0` → `0.1.0`,
`CHANGELOG.md`'s `## [Unreleased]` becomes `## [0.1.0] — <date>` with a fresh empty `Unreleased`
above it, in a commit shaped like MirrorWall's and E1/E2's precedent —
`chore(release): prepare commissioner 0.1.0`. **No tag. No push. No publish.**

---

## Closing duties

1. **`docs/history/E3_HANDOFF.md`** at the workspace root. **Never overwrite an existing root file** — the
   workspace root is not a git repository; if one exists, write `E3_HANDOFF.2.md` and say why. It
   carries: gate results with the interpreter and the exact invocation, **including the `--cov`
   form and the PostgreSQL leg with `COMMISSIONER_REQUIRE_POSTGRES=1`**; what was built against
   spec §7; every decision made where a document left an edge, and every amendment proposed with its
   `cmp` proof; **where your copy of LoadLedger's pattern deliberately differs, and why** (that list
   is the most valuable thing this row produces — it is what a future extraction row reads); what
   the next row must not relitigate; the commits; and **"Before the next session — operator
   steps."**
2. **`docs/history/E3_HANDOFF.md` additionally carries** a note for **J1**: ADR-0050's revisit clause makes the
   *third* mountable package the moment to extract the miniature-host test kit rather than write the
   Alembic harness a third time. E3 is the second. Name the natural home — a `testing` sub-package
   in whichever package the host already depends on, or a shared test-only module in the workspace
   — and say which of your files would move.
3. **One summary in chat**: what changed, what each gate said with the interpreter named, whether
   the PostgreSQL leg actually ran or skipped, every decision taken at an edge, and everything
   waiting on the operator — reserve the PyPI name, push, confirm CI green (**the new `db-matrix`
   job is the one to watch**), review, tag, approve the `pypi` environment, run the post-publish
   install check. **`E1_E2_RELEASE_RUNBOOK.md` at the workspace root has the full release sequence**
   and two things worth reusing: the `gh auth setup-git` fix for the https/ssh push friction, and
   the fact that **Packaging and Release Standards §6 requires a TestPyPI dry run before a
   package's first real release** — which this is, and which is a `workflow_dispatch` that will not
   happen on its own.
4. **Everything committed on `main`, working tree clean, nothing pushed, tagged or published.**
5. **Stop the postgres container** when you are done: `docker rm -f commissioner-pg`.

## Constraints and stop rules

* **No push, no tag, no publish.** Prepare and stop.
* **Never `git add -A`.** `git status --short` at the start and end, and commit per logical group
  (working-tree integrity, `CLAUDE.md`).
* **Never weaken or delete an `.importlinter` contract.** A "temporary" widening to make an import
  work is the one edit that is never temporary.
* **Do not relitigate what `docs/history/C3_HANDOFF.md` §2 and §11 settled**, or what `docs/history/B3_HANDOFF.md` §3 built.
  A thing you would have designed differently is a **finding for the handoff**, not a redesign in a
  publishing row — and if it is a genuine improvement, say so plainly, because LoadLedger can adopt
  it at its next release.
* **The ledger is append-only and that is asserted, not intended.** No update path, no delete path,
  no "just for the UI" mutation.
* **Both dialects, both green, and a skipped PostgreSQL leg is not a pass.** Docker is available
  here; there is no excuse for reporting a skip. If the container will not start, say so plainly and
  make it an operator step rather than letting a skip read as a pass.
* **Do not implement a later phase.** No IdeaPress badge adoption, no aggregation helpers, no
  additional policy dimensions (spec §21) — those arrive as new `EgressPolicy` implementations
  without a schema change, which is the point of the record shape carrying policy name and version.
* **Where a guarantee cannot be proven on this machine, say so plainly** and make it an operator
  step. Do not let an unrunnable check read as a passing one.
* **If you must stop early, stop at a green gate with a commit and a clean tree**, and record
  exactly where you stopped.
