# Kickoff — B2: LoadLedger Phase 1

**Row:** B2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Sonnet 5 · high. **Repository:** `/home/jpk/ai/suite/py/LoadLedger` — **it does not exist
yet; creating it is the first task.**
**Runs after:** A2. Independent of B1 and B3 — it may run before, after or beside them.
**Overnight:** permitted, at effort **high**
([model-assignment §2.12](docs/roadmap/model-assignment.md)).

---

## Preconditions

* **`baseaicore` on PyPI is enough at `0.4.0`.** This row uses `Money`, `TokenUsage`,
  `CostEstimate`, `Unsupported` and `SuiteError`, all of which shipped in `0.4.0`. It does **not**
  need `DataClassification` and does not need `0.4.1`. If `0.4.1` is published by the time you run,
  pin the range `>=0.4,<0.5` either way — that is the existing suite pin and `0.4.1` is inside it.
* **The repository is yours to create locally; the remote is not.** Creating the GitHub repository,
  reserving the PyPI name and configuring CI secrets are human steps
  ([outstanding-work §4](docs/roadmap/outstanding-work.md)). Create the local repository, `git init`
  it, commit to `main`, and list the remote setup in your handoff document. Do not create a remote,
  and do not publish.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/LoadLedger`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  LoadLedger section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2,
  then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name; keyword-only for anything optional or
  boolean; **injected clock** (this package cannot be correct without one);
  `@dataclass(frozen=True, slots=True)` for value objects; line length 100; `mypy --strict` with no
  bare `Any` at a public boundary and no `# type: ignore` without a trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, `CHANGELOG.md` started, one Conventional
  Commit per logical group. **Name the interpreter and the exact invocation in the handoff doc**
  (M5C-13).
* **Dependency pinning:** `loadledger` imports `baseaicore` and **nothing else** in Phase 1.
  `sqlalchemy` arrives in Phase 2 as an optional extra (`loadledger[sql]`) — do not add it now, not
  even to `[project.optional-dependencies]` ahead of time. Where a suite dependency is unpublished,
  the standing rule is a local path/editable install carrying a `TODO: re-pin on publish`; that does
  not apply here, because `baseaicore` is published.
* **Documentation is mirrored.** The workspace copies under
  `/home/jpk/ai/suite/docs/packages/loadledger/` are authoritative; copy `spec.md` and
  `development-plan.md` byte-identically into the new repo's own `docs/packages/loadledger/` on
  creation and verify with `cmp` ([outstanding-work §4](docs/roadmap/outstanding-work.md)).
* **You are not authorised to tag or publish.** Phase 1 does not publish in any case — `0.1.0` ships
  at the end of Phase 2 (row C3).

## Setup

```bash
cd /home/jpk/ai/suite/py/LoadLedger      # already exists, with a .gitignore in place
git rev-parse --git-dir >/dev/null 2>&1 || git init -b main
python -m venv .venv && source .venv/bin/activate
# copy the toolchain from a published sibling — py/WeightsDB is the closest in size and shape:
#   pyproject.toml (hatchling, ruff, mypy strict, pytest + pytest-randomly, coverage floor 95)
#   .importlinter  .editorconfig  .pre-commit-config.yaml  .github/workflows/ci.yml
# adapt names, then:
pip install -e ".[dev]" && pre-commit install
```

The directory and its `.gitignore` are already in place — the `.gitignore` is the suite's
canonical one plus the import-linter cache line. **Do not overwrite it** when you copy the rest
of the toolchain from a sibling; copy every other file and leave that one alone.


Copy, do not invent: nine repositories already share this toolchain, and a tenth that differs is a
CI failure nobody expected. The coverage floor for a shared package is **95 %**.

## Reading list

1. [`docs/packages/loadledger/spec.md`](docs/packages/loadledger/spec.md) — §7 is the normative
   public API and you are implementing it as written: `CeilingScope`, `BudgetCeiling`, `Debit`,
   `CeilingVerdict`, `LedgerEntry`, the `Ledger` protocol, `InMemoryLedger`, and the three errors.
   Read §10 (data ownership — none of its own) and §11 (public contracts).
2. [`docs/packages/loadledger/development-plan.md`](docs/packages/loadledger/development-plan.md)
   **Phase 1** — the file layout, the test list and the acceptance criteria. Phase 2 is out of
   scope; read it only to know what you are deferring.
3. [ADR-0030](docs/adr/0030-model-cost-and-pricing.md) — **the decision this package exists to
   obey.** Cost is re-derived, never stored: persist `TokenUsage` plus the `pricing_hash`, never a
   money figure as the record of truth.
4. [ADR-0016](docs/adr/0016-unavailable-is-not-zero.md) — an unavailable measurement is
   `UNSUPPORTED`, never `0` and never `None`. A local model's cost is unsupported, not free.
5. [ADR-0050](docs/adr/0050-a-package-may-ship-tables-never-a-migration-history.md) (D-6) — for
   context on where Phase 2 goes, so Phase 1's types do not foreclose it. **Ship no SQL.**
6. [ADR-0047](docs/adr/0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md)
   §"Two ceilings" — the rule this package implements the arithmetic half of. Note the boundary
   carefully: **LoadLedger surfaces `unpriced`; the refusal is the application's.**
   `UNPRICED_EGRESS_REFUSED` is PromptCadence's error code, not LoadLedger's, and this package
   must not raise it.
7. `py/WeightsDB` or `py/MirrorWall` — read one as the repository-shape precedent.

## The work

Phase 1 is the arithmetic and the honesty rules: pure, deterministic, no I/O, no SQL.

### 1. `types.py`

`CeilingScope` (`PER_RUN`, `PER_DAY`, `PER_TAG`), `BudgetCeiling` (validation: at least one of
money/tokens; `tag` required for `PER_TAG` and refused otherwise), `Debit`, `CeilingVerdict`,
`LedgerEntry` — exactly the shapes in spec §7.

### 2. `core.py`

Scope-window resolution, incremental balance maintenance, verdict evaluation with most-restrictive
semantics, and `unpriced` propagation into money verdicts. Three traps, each named in the docs and
each worth a test of its own:

* **UTC-midnight window edges.** "Per-day" means a UTC day. The spec, the field docs and the
  development plan say so three times over precisely because it is the thing an operator guesses
  wrong. Test the boundary with an injected clock, from both sides.
* **Integer arithmetic only.** `Money` is nanos; token counts are integers. A float sneaking into a
  division for a "percentage used" convenience is the named failure mode — if you want that
  convenience, compute it in integers or do not ship it.
* **Balances are maintained, not recomputed.** Summing the entry history on every `debit()` is
  correct and quadratic; the plan calls it out as the likely failure mode.

`would_exceed` is **side-effect-free** — assert it with a state hash taken before and after.

### 3. `memory.py` and `errors.py`

`InMemoryLedger` is a first-class supported implementation and the deterministic double every later
phase tests against, not a stub. `errors.py` per spec §7: `LedgerError`, `CurrencyMismatch`
(a USD ceiling and a EUR debit is **refused, never converted**), `InvalidCeiling`, `UnknownRun`,
all subclassing `baseaicore.SuiteError` with the documented codes.

### 4. Tests

The plan's list is the floor: integer exactness at large sums, per-currency separation, unpriced
debits (tokens accumulate, money untouched, the unpriced count surfaced on money verdicts), every
scope, several ceilings active at once with most-restrictive binding, the UTC boundary, the
side-effect-free assertion, and golden verdict serializations. Then acceptance criterion 2, which is
the one that proves ADR-0030 is honoured: **entries re-priced under a corrected `ModelPricing`
reproduce totals with no stored row changed.**

### 5. Documentation and repository furniture

`README.md` (status line: Phase 1, unreleased), `CHANGELOG.md` with an `## [Unreleased]` section,
`LICENSE` and `SECURITY.md` copied from a sibling, and the two mirrored documents under
`docs/packages/loadledger/` verified with `cmp`. No `docs/api.md` generator unless a sibling's
script drops in unchanged.

### 6. Gate and commit

The full gate green with the interpreter named. Commits on `main` in the new repository. No tag,
no publish, no remote.

## Before you finish — three closing duties

1. **Write `docs/history/B2_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands; the public surface as built, against spec §7 (note any place you deviated and
   why); the repository's toolchain provenance (which sibling you copied); the commits made; and
   **"Before the next session"** — every change that must happen before C3 (LoadLedger P2) or any
   other row proceeds. At minimum: create the GitHub remote, reserve the PyPI name `loadledger`,
   push `main`, and confirm CI green on the first push. Add anything you found: a spec passage that
   was wrong or underdetermined, a shape you had to settle, a trap the plan did not name.
   **Never overwrite an existing root file** — the workspace root is not a git repository. If
   `docs/history/B2_HANDOFF.md` exists, write `B2_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what was built, what the gate said, what is waiting on the
   human, and anything in "Before the next session". A few sentences.
3. **Prepare the commits.** Everything committed on `main`, working tree clean, no remote
   configured, nothing tagged. Say exactly what is waiting for the human.

## Constraints and stop rules

* **No SQL, no engine, no session, no Alembic.** That is Phase 2 (row C3), and it is deliberately a
  stronger model's row because it is the first mounting implementation. Phase 1 shipping a table
  would spend that phase's whole point.
* **No I/O of any kind** — no filesystem, no network, no environment reads, no logging side
  effects. The package's value is that it is pure and deterministic.
* **Never weaken `.importlinter`** to make an import work.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` at the start and end of the
  session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/B2_HANDOFF.md`.
