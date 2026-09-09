# E3 — Commissioner Phase 2: the ledger, the mounted table, `commissioner 0.1.0`

**Row:** E3 of `docs/roadmap/outstanding-work.md` §1. **Repository:** `py/Commissioner`, Python
**3.13.15** (`.venv`), coverage floor 95%. **Ships:** release preparation for a **first publish**,
`commissioner 0.1.0` — prepared and stopped at the tag, exactly as instructed. No push, no tag, no
publish.

**Read this first if you're the next session:** §1 (gate results), §7 (decisions at edges — the
most load-bearing section), §9 (before the next session / operator steps), and the note to **J1**
in §10.

---

## 1. Gate results — the interpreter and the exact invocation, named

All commands below ran inside `py/Commissioner/.venv` (`python3.13` → `/usr/bin/python3.13`,
reporting **Python 3.13.15**), and were then re-verified against a throwaway venv built purely from
`requirements/ci.lock` plus `pip install . --no-deps` — the same install shape CI uses — so what is
reported here is what CI will see, not what an editable install happens to make pass.

```
$ ruff format --check .          # 32 files already formatted
$ ruff check .                   # All checks passed!
$ mypy src tests                 # Success: no issues found in 19 source files
$ lint-imports                   # Contracts: 3 kept, 0 broken
$ pytest -q                                     # no server:      115 passed, 12 skipped, 2 deselected
$ COMMISSIONER_REQUIRE_POSTGRES=1 pytest -q     # server required: 127 passed,  0 skipped, 2 deselected
$ COMMISSIONER_REQUIRE_POSTGRES=1 pytest -q --cov --cov-report=term-missing
    TOTAL   240 stmts   0 miss   46 branch   0 partial   100% cover
    Required test coverage of 95.0% reached. Total coverage: 100.00%   (127 passed, 2 deselected)
```

The two `pytest -q` runs above were made **with the PostgreSQL container stopped and then started**
between them, specifically to make the 12-skip → 0-skip difference an observed fact rather than an
inference — 115 + 12 = 127, exactly the count `COMMISSIONER_REQUIRE_POSTGRES=1` reports with the
server up, which is the arithmetic that says the same tests ran, not a different set. The 2
deselected in every run are the `performance`-marked tests, excluded by `addopts`'s `-m "not live
and not performance"` regardless of the database. `mypy`/`ruff` were additionally run over
`acceptance/` as a third input: `mypy src tests acceptance` → `Success: no issues found in 24
source files`, matching E1/E2's own extra check.

**The PostgreSQL leg actually ran.** Docker 29.7.2 started a real `postgres:16` container
(`commissioner-pg`, credentials `commissioner`/`commissioner`/`commissioner_test` — matching what
`ci.yml`'s new `db-matrix` job now starts), and both dialects went green with **zero skips**. The
container was stopped and removed (`docker rm -f commissioner-pg`) before finishing, per the
closing duties.

**The `--cov` trap C3_HANDOFF.md §12 warns about does not bite here.** Every subprocess this
package's tests spawn (`egress_subprocess.py`'s `hammer` mode) inherits the repository's working
directory rather than a `cwd=`-redirected temp directory, so `pytest-cov`'s branch configuration is
found by every child and the combine step never sees a statement/branch mismatch. Verified by
running the exact `tests`-job and `coverage`-job commands (`--cov --cov-report=xml` and `--cov
--cov-report=term-missing --cov-fail-under=95`) against the clean CI-shaped venv, not just the dev
one.

**The release chain builds standalone.** Against `requirements/release.lock`:
`python -m build --no-isolation` → `commissioner-0.1.0.dev0-py3-none-any.whl`/`.tar.gz` (built
before the version bump; the release-prep commit bumps to `0.1.0` after this was verified — the
build shape does not change with the version string), `twine check dist/*` → both `PASSED`. Then,
in a fresh venv: the wheel installs and `import commissioner` succeeds with **no `sqlalchemy`
installed**; `import commissioner.sql` fails with `ModuleNotFoundError: No module named
'sqlalchemy'` until `commissioner[sql]` is installed from the same wheel, at which point
`import commissioner.sql` succeeds — spec §20 acceptance criterion 2's "`pip install
commissioner[sql]` resolves standalone" is verified, not assumed. `pip-audit --require-hashes` is
clean against both `ci.lock` and `release.lock`.

**`.importlinter` verified to bite, not just to pass.** A temporary `import sqlalchemy` +
`import alembic` appended to `commissioner/policy.py` broke
`only-the-sql-module-imports-sqlalchemy` on both imports (`commissioner.policy -> sqlalchemy`,
`commissioner.policy -> alembic`); the file was restored from git and the contract went back to
kept. `git diff` confirms `policy.py` is byte-identical to before the experiment.

---

## 2. What was built, against spec §7

```python
# commissioner.ledger — no sqlalchemy import; part of the pure core
class EgressLedger(Protocol):
    def record(self, decision: EgressDecision) -> None: ...
    def decisions(self, *, run_id=None, verdict=None, target=None, since=None) -> Sequence[EgressDecision]: ...

class InMemoryEgressLedger:
    def __init__(self) -> None: ...          # nothing to configure — see §7 below
    def record(self, decision: EgressDecision) -> None: ...
    def decisions(self, **filters) -> Sequence[EgressDecision]: ...

# commissioner.sql — the only module in this package that imports sqlalchemy
DEFAULT_TABLE_PREFIX = "egress_"

@dataclass(frozen=True, slots=True)
class EgressTables:
    prefix: str
    decisions: Table
    @property
    def metadata(self) -> MetaData: ...
    @property
    def all_tables(self) -> tuple[Table, ...]: ...      # (self.decisions,)

def mount_egress_tables(metadata: MetaData, *, prefix: str = "egress_") -> EgressTables: ...

class SqlEgressLedger:
    def __init__(self, session_factory: Callable[[], Session], *, table_prefix: str = "egress_") -> None: ...
    @property
    def tables(self) -> EgressTables: ...
    def record(self, decision: EgressDecision) -> None: ...        # StoreFailure, UnsupportedDialect
    def decisions(self, **filters) -> Sequence[EgressDecision]: ...

# commissioner.errors — one addition
class UnsupportedDialect(CommissionerError):   # code EGRESS_UNSUPPORTED_DIALECT
```

Built exactly to spec §7's signature line (`SqlEgressLedger(session_factory, *,
table_prefix="egress_")`, `mount_egress_tables(metadata, *, prefix="egress_") -> EgressTables`).
Everything past that signature — the table's shape, `EgressTables`'s own shape, the new error — is
this row's to decide, same as C3's row was for LoadLedger; §7 below records what was decided and
proposes the amendments that follow C1/C2/D1/E1/E2's precedent for a new public name.

### The single table

```
{p}decisions
  decision_id   VARCHAR   PRIMARY KEY
  run_id        VARCHAR   NOT NULL
  verdict       VARCHAR   NOT NULL   -- Verdict(...).value as text, never sa.Enum
  target_name   VARCHAR   NOT NULL
  decided_at    TIMESTAMP WITH TIME ZONE   NOT NULL
  decision_json TEXT      NOT NULL   -- canonical_dumps(decision.to_payload())

  ix_{p}decisions_run (run_id, decided_at)
  ix_{p}decisions_decided_at (decided_at)
```

One table, not four, because there is nothing to aggregate — see §7(a). Every accumulating-column
trap C3_HANDOFF.md §2(c) documents for LoadLedger (`BigInteger` for anything that sums) is inapplicable
here: nothing in this table sums, so there is no accumulating column and the trap is structurally
absent rather than avoided by discipline.

---

## 3. Decisions made where the design document left an edge, and why

`docs/history/C3_HANDOFF.md` §2 and §11 settled the shapes to copy; this section is what remained to decide for
a package whose ledger is append-only rather than accumulating. **Where a choice below reads as an
improvement over LoadLedger's own shape, it is flagged as such — the point C3 §11 makes about a
future extraction row, and about LoadLedger itself adopting it at its next release.**

### (a) One table, decided from the concurrency mechanism first — C3's own advice, followed

C3 §11's parting advice: *"decide the table set after deciding the concurrency mechanism, not
before."* Applied here: Commissioner's `record()` has no shared aggregate at all — no balance, no
running total, no window a second writer's row could collide with. Every decision is independent,
keyed by its own `decision_id`. Once that was clear, the table set followed immediately: one table,
one `INSERT`, no upsert, no `ON CONFLICT`. There was no LoadLedger-style "an hour of reordering"
here, because the concurrency answer for an audit ledger is simpler than for a budget ledger by
construction, not by a shortcut.

One consequence worth stating for J1's benefit: **`_insert_for`'s dialect-specific `insert()`
selection was not copied**, because nothing here needs `ON CONFLICT` and a plain `sa.insert()` is
identical across dialects. What *was* copied, on C3's explicit instruction, is the refusal itself —
`_require_supported_dialect(session)` raises `UnsupportedDialect` for anything but SQLite or
PostgreSQL, checked once at the top of `record()`, even though the SQL Commissioner emits would
probably run unmodified on a third dialect SQLAlchemy supports. ADR-0006 admits exactly two, and a
package that worked by accident on a third would be half-supporting it.

### (b) No `declare_run`, no `UnknownRun` — there is no "run" concept to pre-register

LoadLedger's `Ledger` protocol has `declare_run`/`UnknownRun` because a budget balance must
distinguish "this run has spent nothing" from "this run id is a typo." Commissioner's
`decisions(run_id=...)` is a plain filter with no such ambiguity: a run nobody ever recorded a
decision for returns an empty sequence, which is the correct answer, not an error. Nothing in spec
§7 or §13 asks for a run-registration method, and adding one would be inventing API surface the
spec does not name. **Not copied**, and this is a simplification rather than a gap.

### (c) `record()` takes an already-decided `EgressDecision`; this ledger mints nothing

The most consequential difference from LoadLedger's `SqlLedger`, which draws its own `entry_id` via
an internal `UlidGenerator` and therefore needs a `clock` at construction. Commissioner's
`OrderedClassificationPolicy` already draws `decision_id` and `decided_at` before a decision ever
reaches the ledger (spec §7's `EgressLedger.record(decision: EgressDecision) -> None` — the ledger
is a pure persist-and-query surface). `SqlEgressLedger.__init__` therefore takes only
`session_factory` and `table_prefix`; there is no `clock` parameter to inject, and
`InMemoryEgressLedger()` takes no arguments at all. This is exactly spec §7's stated signature —
nothing was added past it.

**Consequence for ordering:** LoadLedger orders `entries()` by `entry_id` because the ledger mints
that id itself, at write time, so it is a true insertion-order key. Commissioner's `decision_id` is
minted by the *policy*, before the ledger ever sees the decision — nothing here can assume it
reflects recording order (a caller could, in principle, record decisions out of the order they were
decided, e.g. replaying an export). Both `InMemoryEgressLedger.decisions()` and
`SqlEgressLedger.decisions()` therefore order by **`(decided_at, decision_id)`** explicitly, rather
than by insertion order — asserted directly in
`tests/unit/test_ledger_memory.py::TestOrdering::test_decisions_come_back_ordered_by_decided_at_regardless_of_record_order`,
which records two decisions in reverse chronological order and asserts they come back in order.
This is a **deliberate, tested divergence from LoadLedger's ordering rule**, made necessary by the
different division of labour between policy and ledger, not an oversight.

> **Amendment proposed, spec §7:** state `EgressLedger.decisions()`'s ordering explicitly —
> `(decided_at, decision_id)`, ascending — since the protocol currently promises no order at all,
> and both implementations now agree on one that is worth a caller being able to rely on.

### (d) `decision_json` holds the decision's own SetSpec payload, not a second serialization

C3 §2(d) rejects `sa.JSON` for LoadLedger's `debit_json`/`verdicts_json` for three reasons (byte
stability, PostgreSQL's `json` type has no equality operator, plainest possible column) and copies
those reasons here verbatim — they apply exactly to a decision ledger. What is **new** for
Commissioner: LoadLedger had to invent `as_canonical()` on each of its value objects because it has
no SetSpec payload of its own. Commissioner already has a fully golden-tested
`to_payload()`/`from_payload()` round trip (spec §11 contract 4, B3's own row). Rather than inventing
a second canonical form, `sql.py` stores `canonical_dumps(decision.to_payload())` and reconstructs
with `EgressDecision.from_payload(GovernanceEgressDecisionIn.model_validate(json.loads(...)))` —
the identical mechanism a caller reading an *exported* decision uses. **This is a genuine
improvement over LoadLedger's shape**, worth flagging for LoadLedger's own next release if it ever
gains a cross-application payload of its own: one round trip serves both storage and export,
instead of two independent serializations of the same facts that could in principle drift apart.

One consequence follows directly: **there is no observable difference between
`InMemoryEgressLedger` and `SqlEgressLedger`** the way LoadLedger's `SqlLedger.entries()` drops
`debit.cost`. A decision read back through `SqlEgressLedger.decisions()` is field-for-field
identical to what `record()` was given — asserted in
`test_a_decision_survives_a_restart_and_reads_back_byte_identically`, which compares with `==`, not
just a canonical-JSON diff.

### (e) The projected columns are pure index/filter surface, never a reconstruction source

`run_id`, `verdict`, `target_name` and `decided_at` are columns purely so they can be indexed and
filtered; every field a caller reads comes from `decision_json` alone. This is a stronger form of
the same idea LoadLedger applies inconsistently — `_entry_from_row` reads some fields from columns
and others from JSON, and a test asserts the two never disagree. Here there is only one direction to
disagree in (a column could drift from the JSON it was projected from, never the reverse), and
`test_the_indexed_columns_agree_with_the_canonical_record` asserts exactly that on every recorded
row, over the full script.

> **Amendment proposed, spec §10:** name the one table and its columns, since "PromptCadence's
> `ledger_entries`" is the only concrete example LoadLedger's own §10 entry names, and a host sizing
> its database will want Commissioner's shape stated the same way.

### (f) `StoreFailure` is real, not a placeholder — the one new failure mode this phase adds

Phase 1 declared `StoreFailure` in `errors.py` but nothing constructed one (Phase 1 has no store).
This phase makes it real: any `sqlalchemy.exc.SQLAlchemyError` raised during the `INSERT` — in
practice, almost always a duplicate `decision_id` violating the primary key — is caught and
re-raised as `StoreFailure`, never silently absorbed. This is deliberately **not** an
`ON CONFLICT DO NOTHING`: two decisions cannot legitimately share an identity, so a collision is a
caller bug that must surface loudly, not a retry to swallow — the same reasoning spec §14's
"append-only by convention... no update or delete" rests on, applied to the one place a quiet
"insert or ignore" could have crept in as a convenience.
`test_a_duplicate_decision_id_raises_store_failure_and_writes_nothing` proves both halves: the
error, and that the snapshot before and after is identical.

> **Amendment proposed, spec §7's error list and §13's table:** add
> `UnsupportedDialect  EGRESS_UNSUPPORTED_DIALECT  # a session bound to anything but SQLite or
> PostgreSQL`, mirroring `LEDGER_UNSUPPORTED_DIALECT`'s entry in LoadLedger's own spec. `StoreFailure`
> is already listed; §13 should additionally say what actually triggers it (a duplicate
> `decision_id`, in practice), since "store write failure" alone reads as a hardware fault rather
> than the caller-bug case this phase's tests actually exercise.

### (g) No SIGKILL fault-injection harness — there is no transaction boundary to prove atomic

`docs/history/C3_HANDOFF.md` §11 says to copy the whole of `tests/integration/`, `ledger_subprocess.py` included.
**This was not copied whole, and the omission is deliberate, not an oversight to flag as a gap.**
LoadLedger's atomicity proof exists because `debit()` writes to *three* tables (`runs`, `balances`,
`balance_money`) plus `entries` in one transaction, and the property under test is that a crash
between those statements leaves nothing partial — proven by killing the process mid-transaction and
by a `TwoTransactionLedger` subclass that moves the boundary and is shown to leak. `record()` here
issues **exactly one `INSERT` into one table.** There is no second statement for a crash to land
*between*, so there is no atomicity boundary for a fault-injection harness to prove, and a
`TwoTransactionLedger`-shaped broken subclass could not be written — there is only one transaction
to move. `tests/integration/egress_subprocess.py`'s module docstring states this reasoning in the
same place the next person will look for the missing `fault` mode.

What *is* still proven with real subprocesses: `test_concurrency.py` runs three processes recording
40 decisions apiece into one run at once (WAL, real file, none started before all are launched) and
asserts the row count, the distinct-id count and the per-run count all equal 120 — the claim an
append-only ledger with no shared aggregate actually has, stated narrower than LoadLedger's because
the underlying risk is narrower.

### (h) Filters are pushed fully into SQL — no Python-side narrowing at all

LoadLedger's `entries(tag=...)` filters in Python because tags live only inside the JSON debit
record with no index. Every one of Commissioner's four filter fields — `run_id`, `verdict`,
`target`, `since` — is a real, indexed-or-plain column, so `decisions()` builds one `WHERE` with
every given filter and lets the database do all of the narrowing.
`test_decisions_filters_narrow_the_same_way_the_in_memory_ledger_narrows` proves the two
implementations agree on every combination tried, including a target that matches nothing.

---

## 4. Performance — spec §15, measured

| Measure | Target | Measured | |
|---|---|---|---|
| `record` (`SqlEgressLedger`, SQLite) | ≤ 5 ms | **~0.27 ms** | pass, by a wide margin |
| `decisions` over 100 000 rows, filtered to one run's 100 | ≤ 200 ms | **~1.9 ms** | pass |

Both comfortably inside budget — no amendment needed here, unlike C3's one honestly-reported miss.
The filtered-query figure is the meaningful one to watch for regression: it is a single indexed
`SELECT` (`ix_egress_decisions_run`) plus reconstructing 100 rows through
`GovernanceEgressDecisionIn.model_validate` + `EgressDecision.from_payload` — no N+1, no balance
recomputation, because there is no balance. `record`'s flatness across history length is
**structural**, not merely measured: each write is one independent `INSERT` regardless of how many
rows already exist, so there is no "first slice vs. last slice" comparison to make the way
LoadLedger's `debit` needed one — there is nothing here that *could* slow down as history grows.
`tests/performance/test_sql_scaling.py`'s own docstring states this reasoning.

---

## 5. `.importlinter`, the `[sql]` extra, and the lockfiles

* `no-sql-in-phase-1` → `only-the-sql-module-imports-sqlalchemy`, identical in shape to C3 §7's
  contract for LoadLedger: same forbidden modules (`sqlalchemy`, `alembic`), one ignored import
  (`commissioner.sql -> sqlalchemy`), no exemption anywhere for `alembic` — the host owns every
  migration. Verified to bite (§1 above).
* `[project.optional-dependencies].sql = ["sqlalchemy>=2,<3"]`, added in the same commit that first
  imports SQLAlchemy (`sql.py`), per the standing instruction. `dev` gained `alembic>=1.13,<2` and
  `psycopg[binary]>=3.2,<4` for the miniature-host tests and the PostgreSQL leg.
* `requirements/ci.lock` regenerated with **pip-tools 7.6.1** (`--strip-extras --extra dev
  --generate-hashes`). `requirements/release.lock` was regenerated too (same command) and is
  **unchanged** — confirmed with `diff`, not assumed — and stays byte-identical below its header to
  CutCtx's, LoadLedger's, WeightsDB's, MirrorWall's and ToolYard's (`diff <(tail -n +2 …)` against
  all five, zero output). ModelRack's remains the known, separate, two-pins-behind exception E2
  already recorded.
* `pip-audit --require-hashes` clean against both locks.

---

## 6. The acceptance scripts — both run for real, in two real clean venvs

`acceptance/record_and_export.py` (spec §20 criterion 1 — PromptCadence's own acceptance criterion
4, run through Commissioner alone since PromptCadence has no code yet) and
`acceptance/read_verdict.py` (criterion 2 — "the payload is the contract").

```
$ python -m venv /tmp/commissioner-acceptance-writer
$ /tmp/…/pip install ".[sql]"
$ /tmp/…/python acceptance/record_and_export.py /tmp/out/exported_decision.json
ok    a confidential request to a remote tier is denied
ok    and it names the ceiling as the reason
ok    the same confidential data reaches the local tier
ok    the denial is queryable by verdict alone
ok    and it is the confidential-to-remote decision, not some other row
ok    the approval is recorded beside it, symmetrically
ok    no confidential decision in this run was ever approved for a remote target
ok    the denial was exported to /tmp/out/exported_decision.json
All acceptance checks passed.                              # exit 0

$ python -m venv /tmp/commissioner-acceptance-reader
$ /tmp/…/pip install setspec                                # commissioner NOT installed
$ /tmp/…/pip show commissioner
WARNING: Package(s) not found: commissioner                 # confirmed absent, not assumed
$ /tmp/…/python acceptance/read_verdict.py /tmp/out/exported_decision.json
ok    the file validates as a governance.egress_decision payload
ok    it describes a denial — the refusal record.py exported
ok    and it names the ceiling as the reason
verdict:     denied
reason:      classification_exceeds_ceiling
...
All acceptance checks passed — read with setspec alone, Commissioner not installed.   # exit 0
```

Both scripts were also proven to **fail loudly**: feeding `read_verdict.py` a non-payload JSON file
exits 1 with a pydantic validation error, not a silent pass. Every claim is a `_check(claim,
condition)` call that calls `sys.exit` on failure, matching CutCtx's and ToolYard's own acceptance
scripts exactly — no claim is a `print` with nothing enforcing it.

---

## 7. Documentation touched, and what was deliberately not touched

* **The amendments were applied**, after the post-build interview in §12 — see that section.
  `docs/packages/commissioner/spec.md` §7, §10, §13, §14 and §15 are edited in the workspace docs
  repo (commit `6494fec`) and mirrored byte-identically into `py/Commissioner/docs/` (`72b789b`),
  `cmp`-verified. `development-plan.md` is **untouched** in both copies and still `cmp`-identical:
  it is the record of what was intended, and Phase 2's text does not contradict what was built.
  (This section originally read "no spec file was edited", following C3's propose-only precedent;
  the operator chose the C1/C2/D1/E1/E2 pattern instead, which is what the kickoff preamble
  actually asked for.)
* `README.md`, `CHANGELOG.md`: updated in `py/Commissioner` only (`docs/README.md` inside that repo
  is the mirrored copy of the workspace `docs/README.md` and was not touched, correctly — nothing
  about Commissioner's top-level index entry changed).
* **A pre-existing Phase 1 bug, found and fixed while verifying the README's own quickstart runs**:
  `OrderedClassificationPolicy(clock=lambda: datetime.now(UTC))` in the original quickstart made
  `assert type(decision).from_payload(payload) == decision` fail on almost every real run, because
  `to_payload()` truncates `decided_at` to millisecond precision (`TimestampField`) and
  `datetime.now()` essentially never lands exactly on one. Nobody had run the snippet as written —
  B3's own tests all use `ManualClock`. Fixed by using the same fixed instant every other example in
  this package already uses. Worth a note for whoever next touches a Phase 1 doc: **run the
  snippets you find, don't just read them.**

---

## 8. Commits

All on `main` in `py/Commissioner`, on top of `7077cc4`, oldest first, `git add -A` never used:

```
c1be36f  feat(commissioner): add mountable egress table and SqlEgressLedger (ADR-0050)
5284add  build(commissioner): add the sql extra, the db-matrix job, and the import contract that replaces phase 1
671e1d3  test(commissioner): prove mounting, the append-only surface, and a real host's migration story
52f2586  docs(commissioner): changelog, README and the runnable acceptance scripts
89409e7  chore(release): prepare commissioner 0.1.0
```

**These five were pushed by the operator during the session**, and `origin/main` is now at
`89409e7`. Two further commits followed from the post-build interview (§12) and are **unpushed**:

```
72b789b  docs(commissioner): mirror the E3 spec amendments        (py/Commissioner)
6494fec  docs(commissioner): E3 amendments to spec §7,§10,§13,§14,§15   (docs repository)
```

A third, `487f40c` in **`py/BaseAiCore`**, came out of the snippet sweep and is unrelated to this
release. All three working trees are clean. Still no tag and no publish — that part of the
instruction stands.

### CI is green, and the new job actually ran

Run `33843625429` on `89409e7`: **all 13 jobs passed**, including the one this row added and could
not verify locally —

```
✓ tests (PostgreSQL) in 36s
    COMMISSIONER_REQUIRE_POSTGRES: 1
    collected 43 items
    43 passed in 2.43s          # zero skipped
```

That is the `db-matrix` job doing exactly what it was built to do in GitHub's own environment: the
PostgreSQL legs ran for real rather than skipping, and the 43-item count matches this tree's local
collection exactly, so CI is running the same set and not a subset. **The largest open risk named
in this handoff is now closed.** (The only annotations are the repository-wide Node 20 deprecation
warnings on `actions/checkout@v4` / `actions/setup-python@v5`, which affect every repo in the suite
and are not this row's to fix.)

---

## 9. Before the next session — operator steps

None of these can be done from here; all are named in
[`E1_E2_RELEASE_RUNBOOK.md`](E1_E2_RELEASE_RUNBOOK.md) in more detail, including the `gh auth
setup-git` fix for push friction and the **TestPyPI dry run required before a first real release**
(Packaging and Release Standards §6 — a `workflow_dispatch` that will not fire on its own):

1. **Reserve the PyPI name `commissioner`.** Checked 2026-09-03 by the kickoff, still 404 as far as
   this session can tell without a publish — reservation is the operator's own step and must happen
   **before** the tag, per master architecture §1.1.
2. ~~Review the amendments in §3.~~ **Done** — all accepted and applied in the post-build
   interview; see §12. Two extra commits exist as a result: `72b789b` in `py/Commissioner` (the
   mirrored spec) and `6494fec` in the **docs repository**, which is now one commit ahead of its
   own origin and needs pushing too. A third, `487f40c`, is in **`py/BaseAiCore`** from the snippet
   sweep — unrelated to this release, docs-only, and safe to push whenever.
3. ~~Push `main`, confirm CI green.~~ **Done during the session** — you pushed the five build
   commits, and run `33843625429` went green on all 13 jobs including `tests (PostgreSQL)`
   (43 passed, 0 skipped). See §8. What remains is to push the **docs mirror** `72b789b` here and
   `6494fec` in the docs repository, and to let CI go green once more on that mirror before
   tagging — it is a docs-only commit, so this is a formality rather than a risk.
4. **Review, then tag `v0.1.0`.**
5. **Approve the `pypi` environment** for the tag-triggered `release.yml` run.
6. **Run the TestPyPI dry run** (`workflow_dispatch`) before the real one, per Packaging and Release
   Standards §6 — this is this package's *first* real release, which is exactly the case that
   standard exists for.
7. **Run the post-publish install check**: `pip install commissioner[sql]` in a clean venv,
   `python -c "import commissioner.sql"`, and run `acceptance/record_and_export.py` /
   `acceptance/read_verdict.py` against it, the way this session did against the built wheel.

---

## 10. To J1 (IdeaPress mounting), the third mountable package

ADR-0050's "revisit when" clause names the **third** mountable package as the moment to extract the
miniature-host test kit rather than write the Alembic harness a third time. **E3 is the second** (as
C3 §11 already told E3); **J1 is the third**, and this is that flag, restated for J1's own kickoff to
find.

**What would move**, unchanged in shape across both existing copies (LoadLedger's and
Commissioner's), so extraction is a pure move, not a rewrite:

* The `postgres_url()` / `database_url` fixture / `engine` fixture trio from `tests/conftest.py`,
  parameterized by an env-var-name prefix (`LOADLEDGER_`/`COMMISSIONER_` today) rather than
  hardcoded.
* `tests/integration/hostapp/migrations/env.py` and `script.py.mako` — genuinely byte-identical
  between the two existing copies today (diff them to confirm before assuming it for a third).
* `test_hostapp.py`'s `host_config`, `a_host_project`, `sole_revision` helpers, and the shape of its
  six tests (mount→autogenerate→upgrade→use, revision names every table with no dialect type,
  cross-dialect DDL rendering, two hosts/two databases, mount-too-late drops the table, missing
  PostgreSQL fails under `..._REQUIRE_POSTGRES=1`) — parameterized over "the mounted table names"
  and "the mount function," which is the one thing that varies per package.

**What does not move**, and stays a per-package file: `hostapp/models.py` (it mounts one specific
package's tables, by construction) and the package-specific env var names / default credentials.

**Where to put it:** neither LoadLedger nor Commissioner is a dependency of the other (siblings,
`.importlinter` forbids it), and neither is a dependency IdeaPress is guaranteed to have — J1's own
kickoff will say which of the two (or both) IdeaPress actually mounts. `baseaicore` has no
test-only surface today, and adding one there for a kit three packages currently duplicate would be
a new precedent worth the architect's sign-off rather than a route this row should presume. **Best
guess, to be confirmed at J1's own kickoff:** a `testing` sub-package in whichever of
`loadledger`/`commissioner` IdeaPress ends up depending on for its own mounted tables, since that
package will already be an IdeaPress dependency and the kit's only real consumer is a package
already in that position (mirroring ADR-0050's own "the natural home is a testing sub-package in
whichever of the two packages the host already depends on" wording).

---

## 11. Constraints honoured

No push, no tag, no publish. `git add -A` never used. No `.importlinter` contract weakened (one was
*replaced*, per C3's own precedent, verified to bite before and after). The ledger is append-only
and it is asserted, not merely intended — §3(h)'s and the surface tests above are the proof. Both
dialects ran for real and both are green; the PostgreSQL leg was not allowed to read as a pass by
skipping. No later phase implemented: no IdeaPress badge adoption, no aggregation helper, no new
policy dimension. Nothing in `docs/history/C3_HANDOFF.md` §2 or `docs/history/B3_HANDOFF.md` §3 was relitigated — every place
this row's design differs from LoadLedger's is in §3 above, with the reason, not a silent
redesign.

---

## 12. Post-build interview — eight decisions, and what each one changed

Taken with the operator after the build was green and committed. Every one was resolved to the
recommended option; four of the eight changed the tree, four confirmed it as built.

| # | Decision | Outcome | Effect |
|---|---|---|---|
| 1 | The four proposed spec amendments | **Apply now** | 5 sections edited + mirrored (below) |
| 2 | §15's ambiguous filter selectivity | **Keep per-run reading, amend §15** | §15 rewritten; no code change |
| 3 | Duplicate `decision_id` → `StoreFailure` | **Keep** | Confirmed as built; now stated in §13 |
| 4 | The omitted SIGKILL atomicity harness | **Keep omitted** | Confirmed; reasoning already documented |
| 5 | `TAG_COMMANDS.sh` | **Append commissioner** | Third block added, with its 3 preconditions |
| 6 | The README-snippet defect class | **Sweep all nine repos** | 15 documents executed; 1 real defect found and fixed |
| 7 | LoadLedger adopting the payload-as-storage pattern | **Note only, no row** | §3(d) stands as the record |
| 8 | J1's extraction home for the test kit | **Leave to J1's kickoff** | §10 stands as the inventory |

### The amendments, as applied

Workspace `docs` commit **`6494fec`**, mirrored byte-identically into `py/Commissioner/docs` as
**`72b789b`** (`cmp`-verified both before and after). Five sections, one more than the four
proposed — **§14 is the extra**, and it is flagged here rather than buried: the sentence "rows are
append-only **by convention**" understated what E3 actually built, since the property is now
asserted by an API-surface test and an AST scan. It was changed to say so. If that reads as scope
the interview did not authorise, revert that hunk alone; the other four stand independently.

* **§7** — `decisions()` now promises `(decided_at, decision_id)` ascending, with the reason
  (`decision_id` is policy-minted, so it is not an insertion-order key the way LoadLedger's
  `entry_id` is), and states that `since` is inclusive and refuses a naive bound.
  `UnsupportedDialect` / `EGRESS_UNSUPPORTED_DIALECT` added to the error tree.
* **§10** — the one mounted table named in LoadLedger §10's own table format: key, columns, both
  index names, plus why it is one table and not four and why `verdict` is text rather than
  `sa.Enum`.
* **§13** — two rows added: a duplicate `decision_id`, and a third dialect.
* **§14** — append-only restated as a structurally asserted surface property (the extra; see above).
* **§15** — the filtered read's selectivity made part of the target, with the reason the broad
  filter is a different question (cost is dominated by `from_payload` reconstruction, not the
  indexed scan), plus a note that `record` has no history-length term at all.

### The nine-repo snippet sweep

Every ` ```python ` block in all fifteen README/quickstart documents across the nine packages was
extracted, concatenated **in document order** (so a block using a name an earlier block bound is
treated as correct documentation, not a broken snippet) and executed against that repo's own venv,
in a temp working directory so nothing could write into a repository. The three applications have
no Python snippets in their READMEs and were not swept.

| Result | Documents |
|---|---|
| **PASS** | SetSpec, WeightsDB README, LoadLedger README, Commissioner README, **BaseAiCore README + quickstart (after the fix)** |
| **Real defect, fixed** | BaseAiCore README **and** `docs/quickstart.md` |
| Intentional placeholder fragment | ModelRack quickstart (`request`), SweatMeter README + quickstart (`run_work`/`run_workload`), MirrorWall README (a route body without its `def`), CutCtx README (`executor`), LoadLedger quickstart (`session_factory`), ToolYard README (`executor`), WeightsDB quickstart (`created_at=...`) |
| Needs live infrastructure | ModelRack README (a real provider at `127.0.0.1:8080`) |

**The one real defect** (BaseAiCore `487f40c`): `UNSUPPORTED or 0` raises `TypeError`, exactly as
the comment beside it says — so the block stopped on its first line and the two lines
demonstrating `is_supported()` and `supported_values()` were unreachable to anyone who pasted it.
Now wrapped in a `try`, demonstrating the same refusal and running to completion. Docs-only; a
`### Fixed` entry sits under BaseAiCore's `## [Unreleased]`.

**Worth knowing for next time:** the fragment failures are not defects and should not be "fixed" —
`executor`, `session_factory` and `run_work` are placeholders a reader replaces, and that is
idiomatic. One is mildly hostile though, and is left as-is deliberately: WeightsDB's
`created_at=...` is *valid Python*, so instead of a clean `NameError` naming what is missing, it
fails deep inside SQLAlchemy with `'ellipsis' object has no attribute 'tzinfo'`. If that file is
ever touched for another reason, `some_datetime` would be the kinder placeholder.

The sweep script is at
`/tmp/claude-1000/-home-jpk-ai-suite/e346f12c-a72e-4741-a102-97c9b5cfaf68/scratchpad/sweep.py`
(session-scoped, so it will not survive). It is ~50 lines and worth re-deriving rather than
preserving; the method is the part that matters, and it is described above. Making it a CI check
would be a new row, not this one.
