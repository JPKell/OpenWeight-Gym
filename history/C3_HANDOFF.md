# C3 — LoadLedger Phase 2 · Handoff

**Row:** C3 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-02 (build finished
2026-09-03 05:54Z; amendments applied 2026-09-03). **Repository:**
`/home/jpk/ai/suite/py/LoadLedger` — eight commits on `main` on top of `4c65097`, tree clean,
**nothing tagged, nothing published**. The first six were pushed by the operator during the
session (`origin/main` is at `f5f2a1d`); **the last two are not pushed, and one of them is a CI
fix — see §12**.
**Scope delivered:** development plan Phase 2 in full — `loadledger.sql`, `SqlLedger`, the `[sql]`
extra, the miniature host, the atomicity and concurrency proofs, the quickstart, the upgrade-note
template, the CI `db-matrix` job, and the version/changelog preparation for `0.1.0`.

> **Amendments accepted and applied, 2026-09-03.** The six spec amendments proposed below (§2a,
> §2b, §2d, §2e ×2, §6) were accepted by the architect and written into
> `docs/packages/loadledger/spec.md` — §7, §10, §11 contract 1, §13 and §15 — and mirrored
> byte-identically into `py/LoadLedger/docs/`. Roadmap row B2's scope column was corrected in the same
> pass (§10 item 7). The "amendment proposed" wording is kept below as the record of what was
> proposed and why; **the spec is now the authority**, and §10 items 6 and 7 are closed. The
> performance test now asserts the amended §15 budgets (≤ 100 ms query, ≤ 250 ms materialized)
> rather than a provisional figure.

**PyPI name, re-checked at the start of this session (2026-09-02):**
`https://pypi.org/pypi/loadledger/json` → **404**. The name is free and still **unreserved** —
nothing holds it until the first publish. The fallback was not needed and nothing was renamed.

---

## 1. Gate results

Interpreter: **CPython 3.13.15**, `/usr/bin/python3.13`, in `py/LoadLedger/.venv`. This machine has
3.13 and 3.14 and **no 3.12**, so every CI single-version job (`format`, `lint`, `types`,
`boundaries`, `coverage`, `contracts`, `security`, `build`, `install-check`, and the new
`db-matrix`) runs on an interpreter nothing here could exercise. Dependencies installed with
`pip install -e ".[dev]"`; `baseaicore` resolved to **0.4.1**, inside the unchanged `>=0.4,<0.5`
pin. Run from `/home/jpk/ai/suite/py/LoadLedger`:

| Command | Result |
|---|---|
| `.venv/bin/ruff format --check .` | **pass** — 35 files already formatted |
| `.venv/bin/ruff check .` | **pass** — All checks passed |
| `.venv/bin/mypy src tests` | **pass** — no issues in 24 source files |
| `.venv/bin/lint-imports` | **pass** — 3 contracts kept, 0 broken (19 files, 46 dependencies) |
| `.venv/bin/python -m pytest -m "not live and not performance"` | **pass** — 169 passed, 22 skipped, 5 deselected |

Coverage:

```
.venv/bin/python -m pytest -m "not live and not performance" --cov --cov-report=term-missing
→ TOTAL  513 stmts  0 miss  132 branch  0 partial  100%
  src/loadledger/sql.py   192 stmts  0 miss  36 branch  0 partial  100%
  Required test coverage of 95.0% reached. Total coverage: 100.00%
```

Also run and green:

* `pytest -m contract` → **3 passed, 1 skipped** (the skip is the PostgreSQL leg of the new
  round-trip contract test). The `contracts` CI job therefore passes because contract-marked tests
  exist, not because pytest collected nothing — B2_HANDOFF §5 item 8's trap is still avoided.
* `pytest -m performance` → **5 passed** in 44 s. Figures in §6 below.
* The **CI install path**, reproduced in a throwaway 3.13 venv:
  `pip install --require-hashes -r requirements/ci.lock` → `pip install . --no-deps` →
  `pytest … --cov` → 169 passed, **100 %**.
* The **3.14 early-warning job**, reproduced on CPython 3.14.4 in a throwaway venv:
  `pip install -e ".[dev]"` → 169 passed, 22 skipped.
* The **release build chain**: `pip install --require-hashes -r requirements/release.lock` →
  `python -m build --no-isolation` → `twine check dist/*` → `loadledger-0.1.0.tar.gz` and
  `loadledger-0.1.0-py3-none-any.whl` both **PASSED**. The wheel contains exactly
  `__about__ __init__ core errors memory sql types` plus `py.typed`; the sdist contains
  `docs/quickstart.py`, so `python docs/quickstart.py` works from a source checkout. `dist/` was
  removed afterwards.
* `pytest --doctest-modules src/loadledger/__init__.py` → 1 passed (the module docstring's worked
  example still runs after the docstring was rewritten).

Tests run under `pytest-randomly` in randomized order throughout. `pytest` `addopts` gained `-ra`,
so every skipped PostgreSQL leg names itself and its URL in the summary — a skip can no longer be
mistaken for a pass by reading the last line.

**Not verified locally:** the `security` job (`pip-audit`, gitleaks); anything on 3.12; and every
PostgreSQL leg — `pg_isready` is not installed and no server is reachable. 22 of the 191 collected
tests are PostgreSQL legs and they all skip here. `pre-commit` is still not on this machine's PATH.

### 1.1 Acceptance criteria

Spec §20 sets four; the plan assigns **2 and 3** to this phase, with 1 met against the miniature
host and re-verified at PromptCadence P5.

1. **A $5.00 + 2 M-token trajectory ceiling binds, and pre-flight refuses the crossing step.** Met
   against the miniature host and, more legibly, in `docs/quickstart.py`: after 1 225 000 tokens
   the pre-flight for a further 1.5 M-token step reports `per_run exceeded=True` while `per_day`
   (money-only, $25.00) reports `False`. Re-verified inside PromptCadence at P5.
2. **`pip install loadledger[sql]` resolves standalone.** Checked in two clean throwaway venvs
   against the local project:

   ```
   $ pip install <repo>          → baseaicore==0.4.1, loadledger==0.1.0.dev0   (2 packages)
     python -c "import loadledger"          → core import OK
     python -c "import loadledger.sql"      → ModuleNotFoundError: No module named 'sqlalchemy'
   $ pip install "<repo>[sql]"   → baseaicore, greenlet, loadledger, SQLAlchemy==2.0.52,
                                    typing_extensions
     from loadledger.sql import mount_ledger_tables → ledger_entries, ledger_balances,
                                    ledger_balance_money, ledger_runs
   ```

   The core really does resolve to `baseaicore` and nothing else, and the failure a caller gets
   without the extra is the clear one.
3. **Re-costing history changes no stored row.** `test_re_costing_history_changes_no_stored_row`
   debits five entries under a ten-times-too-expensive price list, re-costs each from
   `entry.debit.usage` and `entry.pricing_hash` alone, gets the corrected total, and asserts a
   **row-level** snapshot of all four tables is byte-for-byte identical before and after.
4. `mypy --strict`, `ruff`, `lint-imports` clean; coverage 100 % against a 95 % floor.

### 1.2 The quickstart, as it actually ran

`docs/quickstart.py`, run in the clean `[sql]`-only venv (`sqlalchemy`, `baseaicore`, `loadledger`
and nothing else):

```
mounted: ledger_entries, ledger_balances, ledger_balance_money, ledger_runs

after one local step (no price list applies):
  per_run  spent —                      tokens 912,000   exceeded=False
  per_day  spent —                      tokens 912,000   exceeded=False

remote estimate total: UNSUPPORTED  (input 0.6 USD, output 0.12 USD)

after one partly-priced remote step:
  per_run  spent at least 0.72 USD      tokens 1,120,000 exceeded=False
  per_day  spent at least 0.72 USD      tokens 1,120,000 exceeded=False

after a fully-priced remote step:
  per_run  spent at least 1.095 USD     tokens 1,225,000 exceeded=False
  per_day  spent at least 1.095 USD     tokens 1,225,000 exceeded=False

pre-flight for a 1.5M-token step — would_exceed writes nothing:
  per_run  exceeded=True
  per_day  exceeded=False

history (usage and pricing hash are the stored facts; the money is re-derived):
  turn-1  unpriced=True  pricing_hash=—
  turn-2  unpriced=True  pricing_hash=85b1ec5958b1
  turn-3  unpriced=False pricing_hash=85b1ec5958b1
```

`tests/integration/test_quickstart.py` runs the same script in a temporary directory on every test
run, so the published output cannot rot silently.

---

## 2. The five settled shapes — decisions E3 and J1 must not relitigate

Spec §7 names `mount_ledger_tables` and `LedgerTables` and nothing else about their shapes. These
five are now decided; each ends with the amendment proposed for the authoritative spec. **No spec
file was edited** — proposing is this row's job, accepting is the architect's.

### (a) `LedgerTables` is a frozen dataclass of `Table`s, and a host mostly ignores it

```python
@dataclass(frozen=True, slots=True)
class LedgerTables:
    prefix: str
    entries: Table
    balances: Table
    balance_money: Table
    runs: Table

    @property
    def metadata(self) -> MetaData: ...      # the metadata the host passed in
    @property
    def all_tables(self) -> tuple[Table, ...]: ...   # (entries, balances, balance_money, runs)
```

The honest answer to "what does a host do with it" is **hold it, or drop it on the floor**: the
tables are already in the metadata the host passed, which is what autogenerate reads, so a host
that discards the return value has lost nothing. It is returned so a host can name the tables in a
`create_all(tables=...)`, assert on the shapes in its own tests, or check the prefix it got — and
so `SqlLedger` has one place to look them up.

`metadata` is reachable because it already is (`tables.entries.metadata` is the same object);
hiding it would be theatre. **A host that reaches in for a `Table` in order to join it to one of
its own entities is doing what ADR-0050 decision 2 forbids** — there is no foreign key out of the
mounted set, `run_id`/`source_ref` are opaque, and a join freezes a shape the package is free to
change under an upgrade note. That sentence is in the class docstring.

> **Amendment proposed, spec §7:** give `LedgerTables` its field list, as above, in the
> `loadledger.sql` block. Commissioner's `EgressTables` should be the same *kind* of object with
> the same two properties, so E3 copies the shape and renames the fields.

### (b) Four tables, not three — and the fourth is a correctness requirement, not a convenience

| Table | Key | Holds |
|---|---|---|
| `{p}entries` | `entry_id` (ULID) | `run_id`, `source_ref`, `occurred_at`, `unpriced`, `pricing_hash`, `debit_json`, `verdicts_json` |
| `{p}balances` | `(scope, window_key)` | `tokens_spent` + the three honesty counts |
| `{p}balance_money` | `(scope, window_key, currency)` | `nanos_spent` |
| `{p}runs` | `run_id` | `declared_at` |

The kickoff expected three. The fourth exists because **money is per currency and the currency set
is open**, so a balance's money is a mapping. A mapping in a JSON column on the balance row cannot
be advanced by the single atomic `UPDATE … SET n = n + :delta` that §3's concurrency answer rests
on — you would be back to read-modify-write for money and only money, which is the half that
matters. Splitting it costs one table and one extra statement per priced debit, and buys the whole
concurrency story.

`{p}runs` is separate rather than folded into a zero `PER_RUN` balance row, even though that would
have worked: it is what the development plan's work list asks for ("a run record beside the
entries"), and conflating "this run exists" with "this window has a balance row" would make a
future retention policy that prunes balances silently delete runs.

Two indexes, both prefixed: `ix_{p}entries_run (run_id, entry_id)` and
`ix_{p}entries_occurred_at`. Every primary key is named explicitly (`pk_{p}entries`, …) —
`test_two_prefixes_mount_into_one_metadata_without_colliding` mounts `ledger_` and `trial_` into
**one** `MetaData` and asserts every table, index and constraint name is unique and carries its own
prefix once `pk_`/`ix_` is stripped. On PostgreSQL index names are unique per schema, so an
unprefixed index would have failed at `upgrade` time in a host's production database rather than
here.

`entries()` orders by `entry_id`. ULIDs are lexicographically ordered by the instant they were
minted, which is the instant the ledger recorded the entry, so this is insertion order for one
writer and a stable total order for any number of them — and it needs no sequence, which SQLite and
PostgreSQL spell differently.

> **Amendment proposed, spec §10:** name the four tables and their keys, since "PromptCadence's
> `ledger_entries`" is the only table §10 currently names and hosts will be reading this list when
> they size their database.

### (c) Every accumulating column is `BigInteger` — the trap, stated where the next person will look

`Money` is a whole number of **nanos**, so 1 USD is 1 000 000 000 and **$2.15 is 2 150 000 000,
already past a 4-byte integer's 2 147 483 647.** `sa.Integer` is 4 bytes on PostgreSQL, where a
few dollars of spend would raise `DataError`; SQLite's dynamic typing stores the value regardless,
so a SQLite-only suite would never see it and the first symptom would be in production on the other
dialect. Token counts get the same width: a `PER_TAG` balance never resets and passes 2³¹ tokens
without difficulty. The three honesty counts too, for the same reason.

Two tests hold it: `test_every_accumulating_column_is_eight_bytes_wide` asserts the *type* of all
five accumulating columns and would fail if a sixth were added at the wrong width; and
`test_money_and_tokens_past_a_four_byte_integer_round_trip` runs a $3.00 debit (3 000 000 000
nanos) and a 2 200 000 000-token debit **through both dialect legs** and reads the stored figures
back. The reasoning is in `mount_ledger_tables`'s docstring, in the paragraph a person adding a
column will read.

### (d) Verdicts are canonical JSON in a `TEXT` column — not child rows, and not `sa.JSON`

**Not child rows.** A verdict carries the whole `BudgetCeiling` that produced it, and a verdict read
back after that ceiling was removed from configuration must still describe the cap that actually
fired. Child rows would have made contract 5's atomicity a real multi-table transaction, which it
is anyway (the balances make it so), and would have needed ~13 mostly-nullable columns and a second
serialization of objects that already have `as_canonical()`. `test_a_verdict_still_describes_its_
ceiling_after_that_ceiling_is_removed` deletes the ceiling from the ledger's configuration entirely
and reads the verdict back intact.

**Not `sa.JSON`, which is what the kickoff anticipated.** Three reasons, in order of weight:

1. **Byte-stability is a contract here.** `canonical_json(...)` in a `TEXT` column means the stored
   bytes *are* the bytes spec contract 4 golden-tests, which makes "re-costing changed no stored
   row" a byte comparison rather than an interpretation. `sa.JSON` would store whatever the
   driver's `json.dumps` produced.
2. **PostgreSQL's `json` type has no equality operator.** `SELECT DISTINCT` or `WHERE col = :x` on
   such a column fails there and succeeds on SQLite — a dialect divergence introduced by the
   storage type itself, in a package whose whole claim is portability.
3. It is the plainest possible column, which is what ADR-0050 decision 2 asks for.

**The cost, stated plainly:** no server-side JSON operators and no index into a record's fields, on
either dialect. A host that needs to query inside a verdict adds its own column, index or view in
its own migration. The same choice is why `entries(tag=...)` filters **in Python** over the rows
`run_id` and `since` already narrowed: tags live inside the canonical debit record and the mounted
set carries no tag index. A per-tag *balance* needs no scan (that is what `PER_TAG` windows are
for); a per-tag *history* is a secondary path. An `{p}entry_tags` child table is the documented
extension if a consumer needs it.

`Debit.as_canonical` / `CeilingVerdict.as_canonical` are used as-is; no second serialization was
invented, and the existing goldens still hold.

**One consequence, and it is the only observable difference between `SqlLedger` and
`InMemoryLedger`:** an entry read back through `entries()` has **`debit.cost is None`**, whatever it
was when recorded. `Debit.as_canonical` omits the cost deliberately (ADR-0030 rule 1 — the stored
facts are the `TokenUsage` and the `pricing_hash`, and a test asserts no `"nanos"` appears in a
serialized debit), so storing the estimate would mean a second, contradictory serialization of the
same object. Nothing about what the ledger *decided* is lost: every verdict is stored whole, with
the money it was decided on. The entry `debit()` returns still carries the estimate the caller
passed. This is in the `entries()` docstring, the module docstring, the README and the quickstart.

> **Amendment proposed, spec §7 and §11 contract 1:** state that a durable ledger does not persist
> the `CostEstimate` and that `entries()` returns `debit.cost is None`, with `unpriced` and
> `pricing_hash` carrying the pricing facts. This is the one place a consumer swapping
> `InMemoryLedger` for `SqlLedger` sees a difference, and it should be in the spec rather than only
> in a docstring.

### (e) Instants are `DateTime(timezone=True)`, normalized to UTC at the boundary

Measured, not assumed: SQLite **silently strips `tzinfo`** and stores the wall clock of whatever
offset it was handed, returning a naive value. An instant bound as `23:30-05:00` would come back as
`23:30` — the wrong UTC day, which is precisely the thing contract 7 exists to protect.

So `SqlLedger` converts to UTC before every bind (`_as_utc`) and attaches UTC on every read
(`_from_utc`), and the column stays the plain generic type. **A custom `TypeDecorator` was
considered and rejected**: Alembic renders one into a host's generated revision as
`loadledger.sql.UtcDateTime()`, adding an import of this package to the host's migration history —
a revision that then breaks when the package changes. Normalizing at the boundary keeps the
generated revision to `sa.DateTime(timezone=True)` and, as a bonus, keeps the stored SQLite string
sorting correctly, which is what the `since` filter and the `occurred_at` index rely on.

`test_a_debit_lands_in_the_utc_day_it_happened_in_across_a_midnight` writes debits at 23:59:59 and
00:00:00, asserts the two `PER_DAY` balance rows are keyed `2026-09-02` and `2026-09-03`, and reads
the instants back timezone-aware and equal — on both dialects.

### Two smaller shapes, decided the same way

* **`mount_ledger_tables` refuses a prefix that is not an identifier prefix** (`ValueError`),
  empty included. An empty prefix would mount a table called `entries` into an application's
  schema, which is a collision waiting for a second package. Mounting the same prefix twice into
  one metadata raises SQLAlchemy's own `InvalidRequestError`, which is left unwrapped and
  documented — it is the symptom of a model module imported under two names.
* **`UnsupportedDialect` (`LEDGER_UNSUPPORTED_DIALECT`)** is a new `LedgerError`. ADR-0006 admits
  SQLite and PostgreSQL and nothing else, so a third dialect is refused at the first statement
  rather than discovered as a syntax error inside a money transaction. `baseaicore.ConfigurationError`
  was the alternative; a `LedgerError` subclass keeps `except LedgerError` catching every refusal
  this package makes.

  > **Amendment proposed, spec §7's error list and §13's table:** add
  > `UnsupportedDialect  LEDGER_UNSUPPORTED_DIALECT  # a session bound to anything but SQLite or
  > PostgreSQL`, and a §13 row for the prefix `ValueError`.

---

## 3. The concurrency answer

**Two processes debiting the same window add; neither overwrites. No balance is ever read into
Python, added to, and written back.**

Each touched balance is advanced by one statement:

```sql
INSERT INTO ledger_balances (scope, window_key, tokens_spent, …)
VALUES (…)
ON CONFLICT (scope, window_key) DO UPDATE
   SET tokens_spent = ledger_balances.tokens_spent + excluded.tokens_spent, …
```

Both supported dialects execute this atomically, creating the row if it is new and incrementing it
under the row lock if it is not. SQLAlchemy namespaces the construct per dialect, so `_insert_for`
picks `sqlalchemy.dialects.sqlite.insert` or `…postgresql.insert` and refuses anything else. That
is the **only** dialect branch in the package, it is two lines, and it is complete rather than a
slippery slope because ADR-0006 admits exactly two dialects. The alternatives — `UPDATE` then
`INSERT` on zero rows affected, or `INSERT` and catch the integrity error — each reintroduce a race
on a *new* window and need a `SAVEPOINT` to recover on PostgreSQL, which pysqlite handles badly.

**Statement order is part of the correctness argument, not incidental.** `debit()` issues every
write first — the run row, then every balance in **sorted key order** — and only then reads the
balances back to compute verdicts.

* On **PostgreSQL** at `READ COMMITTED` the upsert takes the row lock, a concurrent writer blocks
  until this transaction commits, and the read-back sees this transaction's own values.
* On **SQLite** the ordering matters more: pysqlite begins the transaction at the first DML
  statement, so a `SELECT` issued *before* any write would run outside the transaction and could
  read a value another writer was about to change. Writing first opens the write transaction
  immediately; a concurrent writer waits on it (pysqlite's `timeout`, five seconds by default).
* Sorted key order gives every process the same lock order, so two debits touching two windows in
  common cannot deadlock.

**What is not claimed: serializable isolation.** Two debits committing concurrently may each report
a verdict that omits the other's spend, so a ceiling can be crossed by at most the concurrent
in-flight debits before the next one sees it — the same "fires late" property a floor already has
(ADR-0069), for a different reason. Both totals are recorded exactly and the next verdict is
correct. **A caller that must not cross a cap under concurrency serializes its own approvals** —
which is what PromptCadence's plan gate already does, so **PromptCadence P5 has nothing to build
here**; it must simply not assume `would_exceed` is a lock. This is in the `SqlLedger` class
docstring and in `README.md`, in those words.

On SQLite the host owns the engine and two settings are its own: a `busy_timeout` long enough for
its write concurrency (the five-second default is usually enough) and a journal mode. Both are
documented in the quickstart.

**Tested, not asserted.** `tests/integration/test_concurrency.py`:

1. `test_a_read_modify_write_on_a_balance_row_loses_a_debit` — the defect, staged deterministically
   on both dialects: two sessions read the same balance, both write it back, and one of two debits
   of 11 tokens vanishes (100 → 111, not 122). It is a fact in the repository, not a paragraph.
2. `test_the_statements_a_debit_issues_are_increments_and_they_come_before_the_reads` — reads the
   SQL off the wire through an engine listener and asserts every balance statement is
   `x = (table.x + excluded.x)` and that **no `SELECT` on a balance precedes the transaction's
   first write**. Both halves of the argument above, asserted against the emitted SQL.
3. `test_two_processes_debiting_one_window_lose_nothing` — two real subprocesses, 40 debits each,
   both started before either is waited on, WAL. The `PER_RUN` and `PER_DAY` balances, the entry
   count and the unpriced count all come out at exactly 80.

---

## 4. Atomicity: how the kill is made deterministic, and how it was proven to bite

**The library has no test seam.** `SqlLedger.debit()` takes no `_after_insert` hook, no debug flag
and no test-only branch — a hook in a production signature is a hook a future caller can reach, and
the contract would then be guarded by a promise not to use it. The fault is injected through the
seam ADR-0050 decision 3 **already** provides: the host owns the engine and the session factory, so
`tests/integration/ledger_subprocess.py` installs a SQLAlchemy event listener on *its own* engine.
The library is unmodified and unaware.

Two fault points, because they fail differently:

* **`entry_insert`** — a `before_cursor_execute` listener that `os.kill(os.getpid(), SIGKILL)`s
  when it sees `INSERT INTO ledger_entries`. Every balance has been advanced; the entry that
  explains them has not been written. A two-transaction implementation has already committed the
  balances by this moment.
* **`before_commit`** — a `Session`-level `before_commit` listener. Everything written, nothing
  committed. The classic.

Both run under **both SQLite journal modes**, because what a killed process leaves on disk depends
on which is in force: the default rollback journal (`delete`) is replayed by the next connection,
WAL is recovered from the log. Four parametrized cases. The parent takes a row-level snapshot of
all four tables, runs the child, asserts the child died by `-SIGKILL` (so the fault point was
actually reached — a child that exited 0 or 1 fails the test), then **reopens the file the killed
process left behind** and asserts the snapshot is unchanged, that no `traj-killed` run row exists,
and that no balance advanced.

**Proven to bite.** `TwoTransactionLedger` in the same module is `SqlLedger` subclassed with
**only the transaction boundary moved** — balances and run row committed in transaction one, the
entry inserted in transaction two — so it is a fair test of what the assertion detects rather than
a strawman. Run through the identical harness at the identical fault point, it leaves a ledger whose
balances say a debit happened and whose entries do not, and
`test_the_same_check_catches_an_implementation_that_uses_two_transactions` asserts exactly that
divergence, on both journal modes. Written first against the broken variant, as C1 did for its
invariants guard.

A fifth test, `test_a_debit_that_raises_mid_flight_rolls_the_whole_thing_back`, runs the same
contract **on both dialects** without a signal — an exception raised between the balances and the
entry unwinds all of it. That is the failure that actually happens in production (a disk error, a
dropped connection, a constraint) rather than the one that is easiest to stage, and it is what
covers PostgreSQL, where the killed-process form is the server's contract rather than this
package's.

Structurally, `would_exceed`/`remaining`/`entries` run inside `_reading()`, which **rolls the
session back** on the way out and never commits. Contract 6 is therefore mechanical: even a future
edit that wrote a row on a read path could not persist one. `test_would_exceed_writes_nothing_at_any_frequency`
takes a full row snapshot, makes 300 read calls including one naming a tag the ledger has never
seen, and asserts the snapshot is unchanged.

---

## 5. The miniature host — what it covers, and what it deliberately does not

`tests/integration/hostapp/` is a **real Alembic project**: its own `MetaData`, its own
`host_notes` table (so the host is not merely the mounted set), its own `migrations/env.py` and
`versions/`. `models.py` mounts at module import, in the module `env.py` imports, which is what a
host must do. `env.py` is an ordinary one — nothing in it knows that some of `target_metadata`'s
tables came from a package, because an `env.py` with a special case would quietly withdraw
ADR-0050's claim.

Covered (`tests/integration/test_hostapp.py`, every test on both dialect legs):

* **Mount → autogenerate → upgrade → debit → query**, with the host's own table working beside the
  mounted ones in the same database and the same single history.
* **The generated revision is checked, not just the metadata.** It must name all five tables, must
  contain no `postgresql.`/`sqlite.`/`mysql.` type reference, must use only
  `String|Text|BigInteger|Boolean|DateTime|VARCHAR|TEXT|BIGINT|BOOLEAN|DATETIME|TIMESTAMP`, and
  must spell both prefixed index names. This is the plan's "autogenerate emitting dialect-specific
  types" failure mode, defended structurally.
* **The revision is then rendered as DDL for the *other* dialect** through Alembic's offline mode,
  which needs no server — so the cross-dialect half of the portability claim runs on this machine.
  The SQLite-generated revision produces valid PostgreSQL: `BIGINT`,
  `TIMESTAMP WITH TIME ZONE`, `BOOLEAN`, `CONSTRAINT pk_ledger_balances PRIMARY KEY (scope,
  window_key)`, both prefixed indexes.
* **Two migrated hosts, two databases, no cross-talk** — same run id, same UTC day, same package
  version; a debit in one is invisible in the other. (`test_mounting.py` has the same assertion at
  the `SqlLedger` level with two prefixes as well as two files.)
* **The import-order hazard is proven real, not described.** Autogenerating against a metadata that
  has *not* mounted makes Alembic write `op.drop_table` for all four ledger tables. That is
  ADR-0050's named failure mode, and it is now a passing test rather than a warning in a docstring.

Deliberately **not** covered:

* **No downgrade path is exercised.** Autogenerate writes one, and it is not run.
* **No multi-revision history.** The host generates one initial revision; a host upgrading *across*
  a package shape change is what `docs/mounted-table-upgrades.md` is for, and its recipe is not
  executed by a test — there is no shape change yet to execute.
* **No `render_as_batch` host.** `env.py` does not enable Alembic's batch mode, so nothing here
  proves the recipe's `op.batch_alter_table` works inside *this* host. It is the standard idiom and
  the upgrade note tells hosts to use it; a first real shape change should add that test.
* **No concurrent-host test.** Two hosts sharing one database is what ADR-0050 forbids, so there is
  nothing to test.

---

## 6. Performance — one budget is missed, and the miss is real

Spec §15, measured on CPython 3.13, SQLite on a real file, three active ceilings:

| Measure | Target | Measured | |
|---|---|---|---|
| `debit` with 3 ceilings | ≤ 5 ms | **~1.5 ms** | pass |
| `debit`, first 500 vs last 500 of 10 000 | flat | 1.58 → 1.47 ms | balances are maintained, not recomputed |
| `would_exceed` | ≤ 2 ms | **~0.4 ms** | pass |
| `entries` over a 10 000-entry run — the query | ≤ 100 ms | **~17 ms** | pass |
| `entries` over a 10 000-entry run — fully materialized | ≤ 100 ms | **~155 ms** | **miss** |

The miss is not a slow machine. Materializing ten thousand entries parses two JSON records each and
constructs roughly thirty-five validated value objects — a `Debit`, a `TokenUsage`, three
`CeilingVerdict`s, their `BudgetCeiling`s and their `Money`. The query is well inside budget;
turning rows into the package's own types is what exceeds it, and no indexing changes that.
Memoizing the rehydrated ceilings (`_ceiling_from_fields`, an `lru_cache` on the primitive fields —
safe because a ceiling is a frozen value object) took it from ~200 ms to ~155 ms, and there is no
comparable win left short of changing what `entries()` returns.

`SqlLedger` did not exist when §15 was written; the figure was set against `InMemoryLedger`, which
meets it.

> **Amendment proposed, spec §15:** split the row —
> `entries` for a 10 000-entry run (`SqlLedger`, SQLite), **query** ≤ 100 ms;
> **fully materialized** ≤ 250 ms. Keep ≤ 100 ms for `InMemoryLedger`.

**Accepted 2026-09-03 and now in §15.** The performance test asserts both amended budgets — the
query at ≤ 100 ms and full materialization at ≤ 250 ms — and the reasoning is in that module's
docstring so neither number reads as arbitrary. Measuring the halves separately keeps the query's
budget meaningful: a regression *there* means an N+1 query or a balance recomputed from history,
and lands in seconds rather than in a fifty-millisecond overshoot.

---

## 7. `.importlinter`, and the `spotcheck` → `commissioner` fix

`no-sql-in-phase-1` was **replaced**, not deleted, by
`only-the-sql-module-imports-sqlalchemy`:

```ini
[importlinter:contract:only-the-sql-module-imports-sqlalchemy]
name = Only loadledger.sql may import SQLAlchemy, and nothing may import Alembic
type = forbidden
source_modules = loadledger
forbidden_modules =
    sqlalchemy
    alembic
ignore_imports =
    loadledger.sql -> sqlalchemy
```

Same forbidden modules, one ignored import, and **no exemption at all for `alembic`** — the host
owns every migration (ADR-0050 decision 5), so nothing in this package imports it, `loadledger.sql`
included; it is a `[dev]` dependency for the miniature host only. Note that with
`include_external_packages = True`, import-linter collapses every external import to the top-level
package, so `loadledger.sql -> sqlalchemy.**` matches nothing and was removed — one line, not two.

**Verified to bite:** a temporary `import sqlalchemy` + `import alembic` appended to `core.py`
broke the contract on both (`loadledger.core -> sqlalchemy`, `loadledger.core -> alembic`); the
file was restored from a copy and the contract went back to kept. A weakened contract and a deleted
one look identical in a diff, which is why this paragraph exists.

`no-sibling-packages` listed **`spotcheck`**, the package's name before `py/Commissioner`'s rename
in `7077cc4`. `commissioner` is added and `spotcheck` **kept**: a forbidden module that no longer
exists forbids nothing, silently, so dropping the old spelling would quietly stop guarding against
an import written before the rename. The reason is a comment above the contract — note that
configparser folds indented `#` lines into the *value* of a multi-line option, so a comment inside
the module list becomes a bogus forbidden module name. It has to go above the section header.

---

## 8. CI, and what could not be run locally

`.github/workflows/ci.yml` gains **`db-matrix`**, WeightsDB's job shape with this package's names:
`postgres:16` service with `loadledger`/`loadledger`/`loadledger_test` matching
`DEFAULT_POSTGRES_URL` in `tests/conftest.py`, `pg_isready` health check, `pytest … tests/integration`
on 3.12 from `ci.lock`, with:

```yaml
LOADLEDGER_REQUIRE_POSTGRES: "1"
LOADLEDGER_POSTGRES_URL: postgresql+psycopg://loadledger:loadledger@localhost:5432/loadledger_test
```

`LOADLEDGER_REQUIRE_POSTGRES=1` is the load-bearing line: without it the PostgreSQL legs would skip
in CI exactly as they do here and the job would go green having tested SQLite twice.
`test_a_missing_postgresql_server_fails_rather_than_skips_when_ci_demands_it` asserts the switch —
`Skipped` without it, `Failed` with it, both against an unreachable URL.

**Nothing PostgreSQL ran on this machine.** `pg_isready` is not installed and no server is
reachable; 22 of the 191 collected tests are PostgreSQL legs and every one of them skipped, each
printing `POSTGRESQL LEG SKIPPED — no server at postgresql+psycopg://…` in the `-ra` summary. The
first push is the first time the following run for real: every dialect leg of `test_sql_ledger`,
`test_mounting`, `test_hostapp` (including autogenerate and upgrade against PostgreSQL) and
`test_atomicity`'s exception-rollback case. The killed-process atomicity tests are SQLite-only by
design — they need a database file this process can reopen afterwards, and the PostgreSQL
equivalent is the server rolling back an aborted backend, which is the server's contract.

`requirements/ci.lock` was recompiled with **pip-tools 7.6.1 on Python 3.13** and gains
`alembic 1.19.1`, `sqlalchemy 2.0.52`, `psycopg 3.3.5` + `psycopg-binary`, `mako`, `markupsafe`,
`greenlet`. The header is the sibling convention, `--no-index` and all (C1_HANDOFF §7's trap: that
flag is *recorded* by 7.6.1, not passed — passing it fails to resolve). It installs cleanly under
`--require-hashes`. `requirements/release.lock` recompiles byte-identically and is unchanged.

---

## 9. Commits

All on `main` in `py/LoadLedger`, on top of `4c65097`, oldest first. `git add -A` was never used;
`git status --short` was empty at the start and is empty now.

```
3fbf15c  refactor: expose the BalanceBook seams a durable ledger evaluates through
0a6e011  feat: add mountable ledger tables and SqlLedger (ADR-0050)
ac746ff  build: add the sql extra, the db-matrix job, and the import contract that replaces phase 1
77eca67  test: prove mounting, atomicity, concurrency and a real host's migration story
3cc3d00  docs: add the runnable quickstart and the mounted-table upgrade template
f5f2a1d  chore(release): prepare loadledger 0.1.0
```

`origin/main` was at `4c65097` when the build finished and is now at `f5f2a1d` — the operator
pushed the six build commits during the session. Two further commits followed when the spec
amendments were accepted:

```
37c684d  docs: mirror the LoadLedger spec with C3's shapes and the split §15 budget
68c3277  test: assert §15's accepted budgets, and stop the quickstart child breaking coverage
```

Both are **unpushed**, and the docs repository has one matching commit, `a954a72`, also unpushed.

The two mirrored documents were **not touched** and were re-verified byte-identical with `cmp`
against `/home/jpk/ai/suite/docs/packages/loadledger/`.

One working-tree note, recorded because `CLAUDE.md` asks for it: a `cp` in this session ran with
the workspace root as its working directory instead of `py/LoadLedger`, and left an untracked
`quickstart.py` in the **docs** repository. It was identified (an unformatted copy of this
session's own script), removed, and `git status --short` in `/home/jpk/ai/suite/docs` is empty at
`b8fd567`. Nothing tracked in that repository was touched. `docs/quickstart.md`,
`docs/quickstart.py` and `docs/mounted-table-upgrades.md` are repo-local, like WeightsDB's, and are
not mirrored. `docs/adoption-checklist.md` stays deferred to PromptCadence P5.

---

## 10. Before the next session

1. **Push `main` — two commits, `37c684d` and `68c3277` — and the docs repository's `a954a72`.**
   The six build commits are already on `origin/main` at `f5f2a1d`, where three CI job legs are
   red. **`68c3277` is the fix for that and the push is not optional: see §12.** Re-run CI after
   pushing and expect `tests` (3.12 and 3.13) and `coverage` to go green; `db-matrix` is still
   having its first ever run and is the one to read carefully.
2. **Confirm CI green, including the new `db-matrix` job.** This is the first run of every
   PostgreSQL leg, so treat a `db-matrix` failure as information rather than as flakiness. The
   likeliest genuine finds are the `TIMESTAMP WITH TIME ZONE` round trip and Alembic autogenerate
   against a live PostgreSQL schema.
3. **Reserve the PyPI name.** Re-checked 2026-09-02: `loadledger` is **404, free, unreserved**.
   Nothing holds it until the first publish, so do the TestPyPI dry run before anyone else takes
   it.
4. **Configure the PyPI trusted publisher and the `pypi` GitHub environment**, then run
   `Release → Run workflow` once against **TestPyPI**. `release.yml` expects both, and this is the
   package's first real release.
5. **Tag `v0.1.0` and publish**, then the post-publish check in a clean venv:
   `pip install loadledger` (must resolve to `baseaicore` alone) and
   `pip install "loadledger[sql]"` (must add SQLAlchemy and no more), then
   `python -c "from loadledger.sql import mount_ledger_tables"`.
6. ~~Put the six proposed spec amendments to the architect.~~ **Done, 2026-09-03** — all six
   accepted and written into `docs/packages/loadledger/spec.md` §7, §10, §11 contract 1, §13 and
   §15, mirrored byte-identically into `py/LoadLedger/docs/`. E3 and J1 should read the spec, not
   this handoff, for the normative shapes. The docs repository has its own commit; push both.
7. ~~Amend roadmap row B2's scope column.~~ **Done, 2026-09-03** — the row now reads "the
   `unpriced_debit_count` that lets PromptCadence raise `UNPRICED_EGRESS_REFUSED` (the code itself
   is PromptCadence's, never this package's — ADR-0047)", closing B2_HANDOFF §5 item 11.

Nothing here blocks E3 or J1; both can start against the code as committed.

---

## 11. To E3 (Commissioner P2), which copies this pattern verbatim

**Copy, unchanged in shape:**

* `mount_ledger_tables`'s whole structure — the prefix validation, the explicitly named
  `pk_`/`ix_` constraints, and the docstring section explaining *why* each type is what it is. The
  index-name test (two prefixes, one `MetaData`) transfers with a rename.
* `LedgerTables` → `EgressTables`: frozen, slotted, `prefix` + named `Table` fields + `metadata`
  and `all_tables` properties, and the same "a host that joins these is doing what decision 2
  forbids" paragraph.
* `_insert_for`, `_upsert_sum` and `_note_run` — the dialect pair, the increment upsert and the
  `on_conflict_do_nothing`. Commissioner's ledger is append-only, so it may need only the insert
  half; keep the `UnsupportedDialect` refusal either way.
* `_writing()` / `_reading()`. `_reading()` rolling back rather than committing is what makes
  "this path has no side effects" mechanical instead of a promise, and Commissioner's read paths
  want it more than this one does.
* `_as_utc` / `_from_utc` and the reasoning behind them. **Do not** write a `UtcDateTime`
  `TypeDecorator`; see §2(e).
* `canonical_json` in a `TEXT` column, for the same three reasons — Commissioner's decision records
  are exactly the byte-stable historical statements that argument is about.
* The whole of `tests/integration/`: the `postgres_url` harness (twenty lines, no `weightsdb`
  import), the `database_url`/`engine` fixture pair, the miniature host, and
  `ledger_subprocess.py`'s engine-listener fault injection with a deliberately broken subclass to
  prove the assertion bites. The CI `db-matrix` job transfers with three name changes.

**Rename:** `ledger_` → `egress_` throughout; `LOADLEDGER_POSTGRES_URL` /
`LOADLEDGER_REQUIRE_POSTGRES` → `COMMISSIONER_*`; the conftest's `DEFAULT_POSTGRES_URL`
credentials and the CI service's `POSTGRES_USER`/`POSTGRES_DB`.

**Two things to know before you start:**

* **Put the database harness in the single top-level `tests/conftest.py`.** With no `__init__.py`
  under `tests/`, a second file named `conftest.py` puts two different modules on `sys.path` under
  the name `conftest`, and `from conftest import MIDDAY` then resolves to whichever pytest inserted
  last. This cost time here; it needn't cost it twice.
* **ADR-0050's "revisit when" clause says a third mountable package should extract the
  miniature-host test kit** rather than write the Alembic harness a third time. E3 is the *second*,
  so copying by hand is right. **J1 is the third** — when IdeaPress mounts, that is the moment to
  extract, and the natural home is a `testing` sub-package in whichever of the two packages the
  host already depends on, or a shared test-only module in the workspace. Flag it in the J1
  kickoff.

**The one thing I would do differently a second time:** decide the table set *after* deciding the
concurrency mechanism, not before. The fourth table (`balance_money`) exists purely because the
atomic-increment upsert cannot operate on a JSON mapping, and that only became obvious once the
upsert was written. For Commissioner, work out how a row is written under concurrency first, and
let the shape follow — an hour of reordering here was the cost of doing it the other way round.

---

## 12. Found after the push: three CI job legs are red on `f5f2a1d`

Applying the accepted amendments surfaced a defect introduced by this session's own
`tests/integration/test_quickstart.py`, which is in the pushed head. **Every CI job that passes
`--cov` fails on `f5f2a1d`** — that is `tests` on both 3.12 and 3.13 (`ci.yml` line 58,
`--cov --cov-report=xml`) and `coverage` (line 112, `--cov --cov-fail-under=95`). Confirmed by the
operator against the 3.12 leg. It fails with an error that points nowhere near the cause, *after*
reporting every test as passed:

```
INTERNALERROR> coverage.exceptions.DataError:
  Can't combine statement coverage data with branch data
```

```
================ 169 passed, 22 skipped, 5 deselected in 9.13s =================
Error: Process completed with exit code 3.
```

The test runs the published quickstart in a child process with `cwd` set to a temporary directory —
deliberately, because that is where the script writes its database. The child therefore cannot find
`pyproject.toml`, so pytest-cov measures it **without** `branch = true`, and the resulting
`.coverage.*` file refuses to combine with the branch data every other process wrote. The tests all
pass; only the combine step dies, which is why the local `pytest` gate stayed green throughout the
build and only the `--cov` run caught it.

**Fixed in `68c3277`** by stripping `COV_CORE*`/`COVERAGE*` from the child's environment — the
child's coverage was never wanted, since what is under test is that the published script runs, not
which of its lines did. The reason is in the helper's docstring so nobody re-adds it.

Verified by reproducing **both** failing commands against the installed distribution
(`pip install --require-hashes -r requirements/ci.lock` → `pip install . --no-deps`), on 3.13,
since this machine has no 3.12:

* `pytest -m "not live and not performance" --cov --cov-report=xml` → exit **0**, 169 passed,
  22 skipped — the `tests` job's command, verbatim.
* `pytest -m "not live and not performance" --cov --cov-report=term-missing --cov-fail-under=95`
  → 169 passed, **100 %** — the `coverage` job's command, verbatim.

Two things worth carrying forward:

* **A green `pytest` and a green `pytest --cov` are not the same gate** when a test spawns a child
  process. The standing gate in this suite's kickoffs runs `pytest` without `--cov`; the coverage
  floor is checked separately, and in CI by a separate job. Any row whose tests spawn subprocesses
  should run the `--cov` form locally before it calls itself done — E3's will, since it copies this
  harness.
* Every other child in the suite (`ledger_subprocess.py`'s fault and hammer runs) inherits the
  repository's working directory and is unaffected. It is specifically the `cwd=` argument that
  breaks the configuration lookup.
