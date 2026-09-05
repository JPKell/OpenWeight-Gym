# Kickoff — C3: LoadLedger Phase 2 (`loadledger 0.1.0`)

**Row:** C3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Opus 5 · high. **Repository:** `/home/jpk/ai/suite/py/LoadLedger` — Phase 1 is built,
green and on `origin/main` at `4c65097`.
**Runs after:** B2, which is **done** — ten commits, CI green on the first push
(`https://github.com/JPKell/LoadLedger/actions/runs/33686302203`), `InMemoryLedger` complete and
golden-tested. Independent of C1/C2 (both built), of B1/B3/B5 (all shipped: `setspec 0.6.0` is
tagged, Commissioner P1 is built) and of C4–C6.
**Ships:** `loadledger 0.1.0` — the arc's **first package release**. You prepare it; you do not
publish it.
**Overnight:** permitted ([model-assignment §2.12](docs/roadmap/model-assignment.md) — only
batches D, G and I2's security half are barred).

**Why this row is Opus at high, and what that means for how you spend the session.** Two reasons,
and both are about what other sessions inherit rather than about SQLAlchemy.

* **This is the suite's first mounting implementation** ([model-assignment
  §3.1](docs/roadmap/model-assignment.md), the first-instance rule). E3 (Commissioner P2) says in
  its own row that it "copies LoadLedger P2's proven pattern verbatim", and J1 mounts it a third
  time inside IdeaPress. The table shapes, the prefix discipline, the `LedgerTables` return type,
  the miniature-host test harness and the upgrade-note template are all being decided once, here,
  for three consumers — one of which will be written by a cheaper model against your code as the
  template.
* **These are money rows, and the failure shape is §3.3's.** Contract 5 says a debit and its
  verdicts commit together. A lost update on a balance row, or an entry written without its
  verdicts, is discovered as a budget that did not bind — months later, in a record nobody can
  reconstruct. There is no useful feedback loop for that class of bug; it is won by reasoning about
  the transaction and by an atomicity test that actually kills a process.

Budget the session accordingly: the shapes in "The work" §1, the concurrency answer in §2, and the
kill-mid-debit design in §4 deserve more of your time than `SqlLedger`'s query methods do.

---

## Preconditions

* **Phase 1 is complete and pushed.** `git log --oneline origin/main -1` must show `4c65097`, and
  `git status --short` must be empty. If the tree is dirty, `git checkout --` anything you did not
  edit (`CLAUDE.md`, working-tree integrity) before you start.
* **`baseaicore` is pinned `>=0.4,<0.5` and stays there.** This row adds no runtime dependency to
  the core: `sqlalchemy` arrives under the **`[sql]` extra** and nothing else changes.
  LoadLedger's non-suite runtime dependency budget is `0`
  ([gold-standards §1](docs/standards/gold-standards.md) — "*(none; `sqlalchemy` under the `sql`
  extra)*").
* **There is no PostgreSQL on this machine.** `pg_isready` is not installed. Every PostgreSQL leg
  must **skip cleanly and visibly** locally and run for real in CI — which means this row also
  **adds the `db-matrix` job** that B2 deliberately did not add (B2_HANDOFF §3). WeightsDB's
  `.github/workflows/ci.yml` lines 72–98 is the template; copy its shape, not its environment
  variable names.
* **You may not import `weightsdb`** — [ADR-0050](docs/adr/0050-a-package-may-ship-tables-never-a-migration-history.md)
  decision 4 forbids it, and `.importlinter` asserts it. That includes `weightsdb.testing`'s
  `temporary_postgres` and `MigrationHarness`, which is exactly the helper you will want. Read them
  for the pattern; write your own, in `tests/`, in about twenty lines.
* **The PyPI name `loadledger` is free but unreserved** — 404 at review on 2026-09-02, and nothing
  holds it until a first publish. Re-check `https://pypi.org/pypi/loadledger/json` at the start of
  the session and record the result. If it has been taken, **stop and say so**: the fallback
  (`aisuite-loadledger`) changes the import name, `pyproject.toml`, `.importlinter`, the coverage
  paths and every document that names the package, and that is not a decision to make at 3 a.m.
  inside a build session.
* **You are not authorised to push, tag or publish.** Prepare the release — the version bump, the
  `## [0.1.0]` changelog section, the quickstart — and stop. The tag, the `pypi` environment
  approval and the post-publish install check are operator steps, listed in your handoff.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/LoadLedger` (and in
  `/home/jpk/ai/suite/docs` for the authoritative copy of the two mirrored documents).
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3
  (and §5.3, the storage model, which ADR-0050 extends), the LoadLedger section of
  [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2 (lines 207–222 — six
  bullets; the last three are this phase's and each is a test you owe), then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name; keyword-only for anything optional or
  boolean; line length 100; `mypy --strict` with no bare `Any` at a public boundary and no
  `# type: ignore` without a trailing reason.
* **Injection, not acquisition.** The session factory, the clock and the ceilings all arrive as
  constructor arguments. The package opens no connection, reads no URL, reads no environment
  variable and no file, and holds no engine (ADR-0050 decision 3; spec §12).
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **95 %**, `CHANGELOG.md` updated,
  one Conventional Commit per logical group. **Name the interpreter and the exact invocation in the
  handoff doc** (M5C-13). B2 ran `py/LoadLedger/.venv/bin/python`, Python 3.13.15 — confirm rather
  than copy that; there is no `python3.12` on this machine.
* **Documentation is mirrored.** Edit the workspace copy under
  `/home/jpk/ai/suite/docs/packages/loadledger/` first, then copy byte-identically into the repo's
  `docs/packages/loadledger/`. Verify with `cmp`, never by eye
  ([outstanding-work §4](docs/roadmap/outstanding-work.md)).
* **Lockfiles:** adding `sqlalchemy`, `alembic` and a PostgreSQL driver to `[dev]` means
  recompiling `requirements/ci.lock` with **pip-tools 7.6.1** (the sibling header convention). Read
  `docs/history/C1_HANDOFF.md` §7 first — it records a pip-tools trap (`--no-index` written into the header)
  that will otherwise cost you twenty minutes. `requirements/release.lock` should not need to move.

## Setup

```bash
cd /home/jpk/ai/suite/py/LoadLedger
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be empty before you start
```

## Reading list

1. [`docs/packages/loadledger/spec.md`](docs/packages/loadledger/spec.md) — **§7** is the normative
   surface and now includes `declare_run`, `PartialPricing` and the three honesty counts (ADR-0069,
   docs commits `a87dcea`/`1bd4c03`/`dd60b6e`). §11 contract **5** is this phase's headline; §13 is
   the error table; §15 the performance targets and the "incremental, not recomputed" rule; §18 the
   test strategy; §19 the versioning promise about mounted table shapes; §20 the acceptance
   criteria — **2 and 3 are yours**, 1 is met against the miniature host and re-verified at F1.
2. [`docs/packages/loadledger/development-plan.md`](docs/packages/loadledger/development-plan.md)
   **Phase 2** — the work list, the file layout, the five tests, the two acceptance criteria, the
   named risk ("the mountable pattern meeting a host Alembic setup it has not seen") and the two
   likely failure modes (dialect-specific types from autogenerate; index names colliding without
   the prefix). Both failure modes are things you can defend against structurally rather than
   notice later.
3. [ADR-0050](docs/adr/0050-a-package-may-ship-tables-never-a-migration-history.md) (**D-6**) — the
   decision this phase exists to obey, all seven numbered points. Decision 6 is your test plan in
   one sentence. Read *Alternatives considered* in full: "give the package its own database" is
   what you will be tempted toward the first time the host's Alembic environment fights you.
4. [ADR-0006](docs/adr/0006-sqlite-and-postgresql-roles.md) and
   [ADR-0005](docs/adr/0005-database-strategy.md) — two dialects, both first-class, SQLAlchemy 2.0
   + Alembic and nothing else.
5. [ADR-0044](docs/adr/0044-a-state-change-and-its-event-are-one-write.md) — contract 5 is this
   ADR applied to money. The shape of the proof (a crash-between test, not a review) is the same.
6. [ADR-0030](docs/adr/0030-model-cost-and-pricing.md) rule 1 — store usage and the `pricing_hash`,
   derive cost. The re-costing test (acceptance criterion 3) is the assertion that no stored row
   changes when history is re-costed under a corrected price list; against `SqlLedger` that means
   proving it at the *row* level, not just the total.
7. **`docs/history/B2_HANDOFF.md` §§2.1–2.3 and §5** — the surface as built, the five departures (four of which
   are now in §7), and **§2.2's settled semantics**, which are decisions you implement and do not
   relitigate: `PER_DAY` is one UTC day across every run, `PER_TAG` never resets, `exceeded` is
   strictly greater, `debit()` resolves `PER_DAY` against the debit's own `occurred_at` while
   `remaining()`/`would_exceed()` use the clock, `money_spent is None` until something is priced
   (with `money_remaining` the whole cap in that state), `entries(since=…)` is inclusive and naive
   datetimes are refused. §5 items 1–4 are the operator steps you inherit; items 5 and 6 are
   **resolved and are your work**.
8. `src/loadledger/core.py` — `BalanceBook`, `_ScopeBalance`, `_ScopeKey`, `_keys_touched` and
   `_key_for`. Note what `_keys_touched` already does: it records into every window a debit falls
   into **regardless of the configured ceilings**, which is precisely the property Phase 2's plan
   relies on ("a ceiling added later binds on the full history"). `src/loadledger/memory.py` is the
   behavioural reference: `SqlLedger` must be observably the same ledger with a different store.
9. `py/WeightsDB` — `src/weightsdb/testing.py` and `.github/workflows/ci.yml` lines 72–98, as
   **patterns to copy by hand**, never as imports. Also its `docs/quickstart.md` and
   `docs/adoption-checklist.md` as the shape of what this row owes.

## The work

Phase 2 is the mountable models, the durable implementation, and the evidence that a real host
application survives both.

### 1. `sql.py` — the mount function, and five shapes the spec leaves you to settle

`mount_ledger_tables(metadata, *, prefix="ledger_") -> LedgerTables`. Settle each of the following
deliberately, document the reasoning in the docstring, and record it in the handoff under a heading
the E3 and J1 sessions will find. Where your answer contradicts the spec as written, **say so and
propose the amendment** — an underdetermined spec passage is a defect to close, not to work around
silently (`CLAUDE.md`).

* **(a) What `LedgerTables` is.** §7 names the return type and nothing else. Commissioner's
  `mount_egress_tables` returns the same *kind* of object, so this is a two-package decision: a
  frozen dataclass of `Table` objects with named attributes is the obvious answer, but say what the
  attribute names are, whether the `MetaData` is reachable from it, and what a host does with it
  (the honest answer is "passes it nowhere and just holds it" — an application that needs the
  `Table` for a join is doing something ADR-0050 decision 2 forbids).
* **(b) The table set.** Entries, plus a **run record** so a run declared with nothing debited
  survives a restart (`declare_run`, spec §7/§13; the Phase 2 work list now names it), plus
  whatever persists balances. Three tables is the expected answer; if you can honestly do it in
  two, say why. Every table, index and constraint carries the prefix — the plan names
  "index names colliding without the prefix" as a likely failure mode, and the test for it is two
  mounts with two prefixes into **one** `MetaData`, which must not raise.
* **(c) Integer width — the money trap, and the one that is genuinely dangerous.**
  `Money` is `(currency, nanos: int)` and 1 USD is 1 000 000 000 nanos, so **$2.15 overflows a
  4-byte integer**. `sa.Integer` is 4 bytes on PostgreSQL; SQLite's dynamic typing accepts the
  value regardless. A SQLite-only test suite will never see this, and the first symptom in
  production is a `DataError` on PostgreSQL at a trivial spend — or, worse, on a database that
  silently wrapped. Use `BigInteger` for nanos and for every accumulated token count (a lifetime
  `PER_TAG` token balance passes 2^31 without difficulty), and write the test that proves a
  large-nanos debit round-trips on **both** dialects. Say in the docstring why the width is what it
  is, because the next person to add a column will otherwise copy the wrong one.
* **(d) Where the verdicts live.** `LedgerEntry.verdicts` is a tuple of `CeilingVerdict`, each
  carrying the `BudgetCeiling` that produced it. Decide: a JSON column on the entry row, or child
  rows. Two consequences to reason about before choosing — contract 5's atomicity is trivial in one
  and a real transaction in the other; and a verdict read back **after a ceiling was removed from
  configuration** must still describe the ceiling that produced it, so a persisted verdict cannot
  be a reference into the current configuration. Use `Debit.as_canonical` / `CeilingVerdict.as_canonical`
  (B2's mechanism, handoff §2.1 item 4) rather than inventing a second serialization; the goldens
  already depend on it. If you choose JSON, remember plain types only — `sa.JSON`, never
  WeightsDB's `PortableJSON` — and say what that costs on each dialect.
* **(e) Datetimes and the naive-refusal rule.** WeightsDB's `UtcDateTime` is not available to you.
  Decide the storage convention (tz-aware UTC in, tz-aware UTC out, on both dialects — SQLite will
  hand you back a naive value if you let it), enforce it at the boundary the way `memory.py` does,
  and test the round-trip across a UTC midnight so contract 7 holds through the store as well as
  through the arithmetic.

Plain-typed columns only, no ORM base with domain meaning, no relationship to any application
entity, no foreign key out of the mounted set, and `run_id`/`source_ref` stay opaque strings
(ADR-0050 decision 2). Nothing in this module creates a table on import: no `create_all` in library
code, ever — tests may call it, the package may not.

### 2. `SqlLedger` — and the concurrency question the spec does not answer

Constructor exactly as §7 types it:
`SqlLedger(session_factory, ceilings, *, clock, table_prefix="ledger_")`. Stateless and cheap to
construct — an application resolves its ceiling set **per operation** (the configured defaults,
this run's own budget, this project's cap) and builds a view with it, which is only sound because
the persisted balance key is `(scope, window_key)` and knows nothing about ceilings.

`debit()` is one transaction: `CurrencyMismatch` checked before anything is written, the entry
inserted, every touched balance updated, the verdicts computed and committed with it. `declare_run`
is idempotent and refuses a blank id. `would_exceed()` has **no side effects** at any frequency
(contract 6) — including no lazy row creation, which is the easy way to break it.

**The question to answer explicitly: two processes debiting the same window.** A read-modify-write
on a balance row is the textbook lost update, and the thing lost is money. `InMemoryLedger` takes a
lock per method; a SQL ledger's transaction is supposed to be the serialization (`core.py`'s
`BalanceBook` docstring says exactly that), but "in a transaction" is not by itself enough at
SQLite's default isolation or PostgreSQL's `READ COMMITTED`. Decide the mechanism — `SELECT … FOR
UPDATE` on PostgreSQL, `BEGIN IMMEDIATE` or an atomic `UPDATE … SET x = x + :n` on SQLite, or a
formulation that is correct on both without dialect branching — write down why it is correct, and
**test it with two concurrent writers**, not by inspection. If you conclude that the honest answer
for `0.1.0` is "single-writer, documented", then say so in the docstring and in `README.md` in
those words, and name what PromptCadence P5 must do about it. What you may not do is leave it
unstated.

Performance (spec §15, behind the `performance` marker): `debit` with three active ceilings
≤ 5 ms on SQLite, `would_exceed` ≤ 2 ms, `entries` over a 10 000-entry run ≤ 100 ms. The last one
is also the proof of the "incremental, not recomputed" rule — if `debit` gets slower as history
grows, a balance is being recomputed somewhere.

### 3. The miniature host — `tests/integration/hostapp/`

A **real Alembic project** in this repository's tests: its own `MetaData`, its own `env.py`, its own
`versions/` directory, one table of its own so the host is not merely the mounted set. It mounts,
autogenerates, upgrades, debits, queries. This is ADR-0050 decision 6, and it is the only evidence
that the pattern survives contact with a host's migration story.

Two things the plan names, both worth designing rather than discovering:

* **Autogenerate emitting dialect-specific types.** The point of the test is that the *generated
  revision* is portable, so run the generated revision on the other dialect too, or assert on what
  autogenerate produced. A test that only checks "autogenerate saw the tables" misses the failure.
* **Two miniature hosts, two databases, one package version — no cross-talk.** Different prefixes,
  different files; assert that a debit in one is invisible in the other. This is the concrete form
  of "two applications mounting these tables have two tables in two databases — never one".

PostgreSQL legs skip locally with a visible reason and run in CI's new `db-matrix` job. Write the
skip so it is impossible to mistake a skip for a pass in the summary line.

### 4. Atomicity — kill mid-debit, and how you make that deterministic

Contract 5's proof: kill the process mid-debit and assert that the entry and its verdicts are
**both present or both absent** — no entry without verdicts, no balance advanced without an entry.
On SQLite (a real file database, so the journal mode matters and you should state which one you
tested and why) and on PostgreSQL in CI.

The design problem is getting the kill to land in the window that matters. A `SIGKILL` at a random
moment usually lands somewhere harmless and the test proves nothing. The workable shapes are a
subprocess that performs a debit with an **injected fault point** — a callable the test supplies
that raises or `os.kill(os.getpid(), SIGKILL)`s itself between the insert and the commit — or a
session hook that does the same. Pick one, and be honest in the docstring about what is production
code and what exists only for the test: a `debit()` that takes a `_after_insert` hook in its
production signature is a seam a future caller can reach, and the fix is to make the seam
test-visible without being publicly callable. Whatever you choose, the test must **fail** if the
implementation splits the write into two transactions — write it against a deliberately broken
variant first to prove it bites, the way C1 proved its invariants guard.

### 5. Packaging, extras and the import contract

* `pyproject.toml`: add `sql = ["sqlalchemy>=2,<3"]`; add `sqlalchemy`, `alembic` and a PostgreSQL
  driver to `[dev]` only. The core install must still resolve with nothing but `baseaicore`, and
  `pip install loadledger[sql]` must resolve standalone (acceptance criterion 2). Prove both in a
  clean throwaway venv and paste the output into the handoff.
* `.importlinter`: **replace** `no-sql-in-phase-1` — do not delete it. The replacement forbids
  `sqlalchemy` and `alembic` everywhere except `loadledger.sql`; a deleted contract and a weakened
  one look identical in a diff, and this one is the mechanical statement of ADR-0050 decision 4.
  While you are in the file: the `no-sibling-packages` contract still lists **`spotcheck`**, the
  package's old name. It is `commissioner` now (`py/Commissioner`, renamed in `7077cc4`) — fix the
  name and keep both spellings if you like, since a stale forbidden module silently forbids nothing.
* Version: `src/loadledger/__about__.py` `0.1.0.dev0` → `0.1.0`. `CHANGELOG.md` gains a real
  `## [0.1.0]` section, not `[Unreleased]`.
* `.github/workflows/ci.yml`: add the `db-matrix` job. Note B2_HANDOFF §5 item 8 — CI's `contracts`
  job runs `pytest -m contract` and pytest exits 5 when nothing is collected, so if this repository
  still has no `contract`-marked test, check whether that job is currently passing for the reason
  you think it is.

### 6. Documentation

* `README.md`: the mount-into-your-own-metadata shape is the thing a new caller gets wrong, so it
  belongs above the fold — "this package ships tables, not a database".
* `docs/quickstart.md`: **acceptance criterion 2 is a demonstrable script**, not a prose section —
  a standalone script with `loadledger[sql]` + `baseaicore` that mounts into its own SQLite file,
  debits priced and unpriced usage, and prints honest balances (`—`, not `$0`, for the unpriced
  local model; "at least" for a floor). Run it and paste the real output into the handoff.
* The **upgrade-note template** for host applications (Phase 2's work list; spec §19): a column
  change ships as a note plus a migration recipe the host runs from its own revision. Write the
  template now, with one worked example, because the first person to need it will be mid-incident.
* The two mirrored documents verified with `cmp`; `docs/adoption-checklist.md` stays deferred to
  PromptCadence P5 (B2_HANDOFF §5 item 12) unless you find you have written it anyway.

### 7. Gate and commit

The full gate green with the interpreter named. Commits on `main`, one per logical group. No tag,
no publish, no push.

## Before you finish — three closing duties

1. **Write `docs/history/C3_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands, including the clean-venv `pip install loadledger[sql]` check and the quickstart
   script's real output; **the five settled shapes from §1** as decisions E3 and J1 must not
   relitigate, each with the spec amendment you propose where §7 now disagrees; **the concurrency
   answer from §2** in the words a reviewer needs; **how the kill-mid-debit test is made
   deterministic and how it was proven to bite**; what the miniature host covers and what it
   deliberately does not; the `.importlinter` replacement and the `spotcheck`→`commissioner` fix;
   the CI `db-matrix` job and what could not be run locally (no PostgreSQL on this machine); the
   commits made; and **"Before the next session"** — at minimum: push `main`, confirm CI green
   including the new `db-matrix` job, the re-checked PyPI-name result, the trusted-publisher and
   `pypi` environment setup, the TestPyPI dry run, then tag `v0.1.0` and publish, then the
   post-publish install check. Add a short section addressed **to E3** — Commissioner P2 copies
   this pattern verbatim, so tell it what to copy, what to rename, and the one thing you would do
   differently a second time. **Never overwrite an existing root file** — the workspace root is not
   a git repository. If `docs/history/C3_HANDOFF.md` exists, write `C3_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what was built, what the gate said, the shapes you settled, how
   atomicity is proven, and what is waiting on the operator. A few sentences.
3. **Prepare the commits.** Everything committed on `main`, working tree clean, nothing pushed,
   nothing tagged. Say exactly what is waiting for the operator.

## Constraints and stop rules

* **No `weightsdb` import, in `src/` or in `tests/`** — not for the migration harness, not for
  `temporary_postgres`, not for `PortableJSON` or `UtcDateTime`, not under `TYPE_CHECKING`.
  ADR-0050 decision 4 gives the reason; `.importlinter` asserts it; you never weaken
  `.importlinter` to make an import work.
* **The package owns no engine, no session, no URL, no environment variable, no file, and no
  migration history.** It never runs a migration, and auto-migration on import is forbidden
  outright (ADR-0050 decision 5). `create_all` does not appear in `src/`.
* **No new runtime dependency in the core.** `sqlalchemy` lives under `[sql]`; the budget is `0`.
* **`UNPRICED_EGRESS_REFUSED` stays out of this package** (B2_HANDOFF §2.3, ADR-0047). LoadLedger
  surfaces the counts; refusing an unpriced remote step is PromptCadence's policy. `errors.py`'s
  module docstring already says so — leave it saying so.
* **No new semantics.** Everything in B2_HANDOFF §2.2 is settled and now written into the spec.
  `SqlLedger` is `InMemoryLedger` with a different store; where you find yourself deciding a
  behaviour rather than persisting one, you have drifted — stop and check §2.2 first.
* **No pricing, no conversion, no policy, no logging** (spec §3, §17). A mixed-currency debit
  raises; nothing here converts.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` in this repo at the start and
  end of the session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/C3_HANDOFF.md`.
