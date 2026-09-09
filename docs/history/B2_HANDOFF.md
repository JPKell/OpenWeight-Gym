# B2 — LoadLedger Phase 1 · Handoff

**Row:** B2 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-02.
**Repository:** `/home/jpk/ai/suite/py/LoadLedger` — created, ten commits on `main`, tree clean,
nothing tagged. **Pushed by the operator on 2026-09-02 at 14:39 PDT through `0982c8b`**; the one
commit after it (`4c65097`) is local.
**Scope delivered:** development plan Phase 1 in full, plus ADR-0069 (see below). Phase 2
(`loadledger.sql`, `SqlLedger`, the `[sql]` extra, `0.1.0`) is untouched and remains row C3.
**Reviewed 2026-09-02:** every claim below was re-checked against the tree; the gate, the CI
install path and the release build chain were re-run and match. Changed at review: the interpreter
note in §1 (3.12 is not on this machine, and CI's single-version jobs all run on it), the 3.14 job
now reproduced, §1.1 added, the PyPI-name check in §5 item 3, item 7's check result, and item 11.
**Decided 2026-09-02, after the review:** the review found that `estimate_cost` refuses a total
whenever a token class is unreported and that both real ModelRack adapters leave the cache classes
unreported — so under spec contract 2 as first written, no remote debit would ever have reached a
money balance. The operator chose the floor with a strict option, recorded as
[ADR-0069](docs/adr/0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md)
(docs commit `a87dcea`) and implemented here (commits `899e87b`, `364bb5e`). The two questions
that decision left open were then settled the same day:
[ADR-0070](docs/adr/0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
puts the absent-class rule in the adapter, per response, and schedules it as roadmap rows C5 and
C6; and `Ledger.declare_run` entered spec §7 (docs commit `1bd4c03`, mirror commit `0982c8b`
here, ModelRack mirror commit `a0f9328`). Item 6 was then closed as well: the window semantics
are confirmed in spec §2 as built (docs commit `dd60b6e`, mirror commit `4c65097`), together
with the per-project budgets and the per-day window wait they serve in PromptCadence. §1, §2, §4
and §5 below describe the tree after those commits. **No architect question from this row remains
open.**

---

## 1. Gate results

Interpreter: **CPython 3.13.15**, `/usr/bin/python3.13`, in `py/LoadLedger/.venv`. This machine
has 3.13 and 3.14 and **no 3.12**; the lockfiles are compiled on 3.13 like every sibling's, so
3.13 is the interpreter that matches them. Note what that leaves out: CI runs the `tests` matrix
on 3.12 and 3.13, but every single-version job — `format`, `lint`, `types`, `boundaries`,
`coverage`, `contracts`, `security`, `build`, `install-check` — runs on **3.12**, which nothing
here could exercise. Dependencies installed with `pip install -e ".[dev]"`; `baseaicore`
resolved to **0.4.1** from PyPI, inside the declared `>=0.4,<0.5` pin.

Run from `/home/jpk/ai/suite/py/LoadLedger`:

| Command | Result |
|---|---|
| `.venv/bin/ruff format --check .` | **pass** — 20 files already formatted |
| `.venv/bin/ruff check .` | **pass** — All checks passed |
| `.venv/bin/mypy src tests` | **pass** — no issues in 12 source files |
| `.venv/bin/lint-imports` | **pass** — 3 contracts kept, 0 broken (14 files, 33 dependencies) |
| `.venv/bin/python -m pytest -m "not live and not performance"` | **pass** — 120 passed, 2 deselected |

Coverage, the gate the plan actually sets:

```
.venv/bin/python -m pytest -m "not live and not performance" --cov --cov-report=term-missing
→ TOTAL  314 stmts  0 miss  94 branch  0 partial  100%
  Required test coverage of 95.0% reached. Total coverage: 100.00%
```

Also run and green, beyond the standing gate:

* `pytest -m performance` — 2 passed (the non-quadratic-debit assertion and spec §15's
  10 000-entry history query).
* `pytest -m contract` — 2 passed. CI has a `contracts` job; a repository with no
  `contract`-marked test would fail it with pytest's "no tests collected" exit 5, so the golden
  verdict serializations carry that marker.
* The **CI installation path**, reproduced locally in a throwaway 3.13 venv:
  `pip install --require-hashes -r requirements/ci.lock` → `pip install . --no-deps` →
  `pytest … --cov` → 120 passed, 100 %. This is what proves `[tool.coverage.run] source` names the
  importable package and not `src/loadledger` (the trap documented in `requirements/README.md`).
* The **release build chain**: `pip install --require-hashes -r requirements/release.lock` →
  `python -m build --no-isolation` → `twine check dist/*` → both artifacts PASSED. `dist/` was
  removed afterwards.
* The README quickstart, executed: it prints `912000 None 1` exactly as documented — an unpriced
  local model shows nothing spent, not `$0.00`. The strict-ceiling snippet that follows it
  constructs a `BudgetCeiling` whose `partial_pricing` is `strict`.
* `pytest --doctest-modules src/loadledger/__init__.py` — 1 passed; the module docstring's worked
  example is real.
* The **3.14 early-warning job**, reproduced at review in a throwaway venv on CPython 3.14.4:
  `pip install --require-hashes -r requirements/ci.lock` → `pip install . --no-deps` →
  `pytest -m "not live and not performance"` → 120 passed. The 3.13-compiled lock installs under
  `--require-hashes` on 3.14 without complaint.

Tests run under `pytest-randomly` in randomized order throughout (no `-p no:randomly` in any
recorded result above).

**Not verified locally:** the `security` job (`pip-audit`, gitleaks), and anything on 3.12 — see
the interpreter note above. Both were verified by CI on the first push instead: the run on
`0982c8b` (2026-09-02 21:39Z) completed with every job green, 3.12 legs and `security` included.
`pre-commit` is not on this machine's PATH, so `pre-commit install` was not run — nor is a hook
installed in any sibling repository, so this matches the rest of the suite.

### 1.1 Phase 1 acceptance criteria, as demonstrated

The development plan sets two.

1. **`mypy --strict` clean; goldens stable across the CI matrix; coverage ≥ 95 %.** mypy and
   coverage are in the table above. The golden verdict bytes
   (`test_verdicts_serialize_to_their_golden_bytes`, `contract`-marked) are identical on 3.13 and
   3.14 here; "across the CI matrix" also means 3.12, which only the first push can show. The
   goldens were re-derived by hand for ADR-0069's two new canonical fields, `partial_pricing` on
   the ceiling and `untotalled_debit_count` on the verdict.
2. **Re-costing changes no stored row** (spec contract 1, ADR-0030 rule 1).
   `test_history_recosts_under_a_corrected_price_with_no_stored_row_changing` debits a run under a
   wrong `ModelPricing`, re-costs the stored entries under a corrected one from their usage and
   `pricing_hash` alone, gets the corrected total, and asserts every stored entry's canonical bytes
   and every stored `pricing_hash` are unchanged.
   `test_the_pricing_hash_is_stored_and_the_money_is_not_the_record` covers the other half: the
   hash is on the entry and no money figure is in the serialized debit. Both in
   `tests/unit/test_memory_ledger.py`.

The kickoff's own additions are in the same suite: `would_exceed` proven side-effect-free by a
state hash taken before and after a hundred calls
(`test_the_state_hash_is_unchanged_across_many_calls`), and the UTC-midnight boundary from both
sides, including the west-of-UTC case a local reading would get wrong (`tests/unit/test_windows.py`,
fifteen tests).

---

## 2. The public surface as built, against spec §7

`loadledger.__all__`:

```
BalanceBook  BudgetCeiling  CeilingScope  CeilingVerdict  CurrencyMismatch  Debit
InMemoryLedger  InvalidCeiling  Ledger  LedgerEntry  LedgerError  PartialPricing  UnknownRun
__version__  utc_day_key  utc_day_start
```

Field-for-field against §7 as amended by ADR-0069:
`BudgetCeiling(scope, money, tokens, tag, *, partial_pricing)`,
`Debit(run_id, source_ref, usage, cost, tags, occurred_at)`,
`CeilingVerdict(ceiling, exceeded, money_spent, money_remaining, tokens_spent, tokens_remaining,
unpriced_debit_count, untotalled_debit_count, unmetered_debit_count)`,
`LedgerEntry(entry_id, debit, unpriced, pricing_hash, verdicts)`, and the four errors with the
documented codes (`LEDGER_ERROR`, `LEDGER_CURRENCY_MISMATCH`, `LEDGER_CEILING_INVALID`,
`LEDGER_UNKNOWN_RUN`), all subclassing `baseaicore.SuiteError`.

### 2.1 Where the build departs from §7, and why

Five departures at the time of the build. **ADR-0069 amended §7 on 2026-09-02** and absorbed three
of them, and **`declare_run` was accepted into §7 the same day** (docs commit `1bd4c03`) — items
1, 2, 3 and 5 below are now what §7 says. Item 4 remains the one departure without a spec line:
`as_canonical()` is the mechanism behind contract 4, and §7 does not name it.

1. **`CeilingVerdict.unpriced_debit_count: int = 0` — added; now in §7 (ADR-0069).**
   Spec contract 2 requires "the money verdict for a scope containing unpriced remote usage
   carries the unpriced count". §7's field list had nowhere to put it. Without the field, contract
   2 is unimplementable.

2. **`CeilingVerdict.unmetered_debit_count: int = 0` — added; now in §7 (ADR-0069).** *This is
   the one the plan did not name, and it is the trap of the row.*
   `TokenUsage.total_tokens` is `UNSUPPORTED` if **any** of the four classes is unsupported, and
   the four default to `UNSUPPORTED`. A provider that reports input and output tokens — the
   ordinary case, not an edge one — therefore has an `UNSUPPORTED` total. Using `total_tokens` for
   accumulation would make essentially every real ledger's token balance unsupported, disabling
   the ceiling ADR-0047 calls "the universal brake". The build instead sums the classes that were
   reported and counts the debits it could not fully count, exactly mirroring `unpriced` on the
   money side. Silently summing without the count would have been a floor presenting itself as a
   total — the defect contract 2 exists to prevent, in the other half of the verdict.

3. **`Ledger.declare_run(run_id) -> None` — added to the protocol; now in §7.**
   Spec §13 defines a run as existing "once debited **or declared**". §7's protocol offered no way
   to declare one, so `UnknownRun` could only ever be avoided by spending money first. C3 must
   implement it on `SqlLedger` too.

4. **`as_canonical()` on `BudgetCeiling`, `Debit`, `CeilingVerdict`, `LedgerEntry` — added.**
   Contract 4 promises verdicts are "byte-identical in serialized form — golden-tested", and
   `baseaicore.canonical_json` refuses `Money` and needs a mapping form. This follows BaseAiCore's
   own `Money.as_canonical` / `TokenRates.as_canonical` pattern. `Debit.as_canonical` **omits the
   cost deliberately**: usage and `pricing_hash` are the stored facts (ADR-0030 rule 1), and a test
   asserts no `"nanos"` appears anywhere in a serialized debit.

5. **`CeilingScope` is a `StrEnum` where §7 wrote `Enum`.** Every enumeration in the suite
   (`ProviderKind`, `PricingSource`, `MetricKind`, `GpuVendor`) is a `StrEnum`, and a `StrEnum`
   *is* an `Enum`, so nothing written against §7 breaks. §7 now says `StrEnum`, and the new
   `PartialPricing` is one too (ADR-0069).

Added by ADR-0069, and in §7 from the start of their existence: `PartialPricing` (`FLOOR`,
`STRICT`), the keyword-only `BudgetCeiling.partial_pricing`, and
`CeilingVerdict.untotalled_debit_count` — the subset of the unpriced count that carried an
estimate which did not total, and what a strict ceiling fires on. All three are in the canonical
forms.

`BalanceBook`, `utc_day_start` and `utc_day_key` are also exported and are not in §7. They are the
engine and the window arithmetic, factored out so `SqlLedger` reuses one implementation in C3
rather than growing a second. If the architect would rather they stayed private, that is a
one-line change to `__all__` before `0.1.0` publishes — but C3 will want `BalanceBook`.

### 2.2 Semantics the spec left underdetermined, and how they were settled

Every one of these is documented in the relevant docstring. **They are the highest-value thing on
this page to review**, because a later change to any of them is a behaviour change in a money
record.

* **`PER_DAY` and `PER_TAG` are ledger-wide; `PER_RUN` is per run** — confirmed, now in spec §2.
  §2 used to list the three scopes without saying whether a day window is per-run or across runs.
  A daily spend cap that reset per run would cap nothing, so `PER_DAY` accumulates every debit in
  the UTC day across all runs, and `PER_TAG` every debit carrying the tag across all runs and days,
  never resetting — the shape a project budget wants. `remaining(run_id)` still reports all three,
  anchored on that run for the `PER_RUN` one. Finer windows are new scope values, never a
  reinterpretation.
* **`exceeded` is strictly greater than the bound.** Spending exactly the cap is not exceeding it.
* **`debit()` resolves `PER_DAY` against the debit's own `occurred_at`, not "now".** A back-dated
  debit affects yesterday's window and the verdict it gets back describes that window.
  `remaining()` and `would_exceed()` use the clock.
* **`money_spent is None` until something is priced in the window** (§7's own comment, "None when
  nothing priced yet in this scope"). `money_remaining` is the **whole cap** in that state, not
  `None` — nothing priced has been spent, and the `unpriced_debit_count` on the same verdict says
  whether that figure is a floor. A token-only ceiling reports `None` for both. An estimate that
  priced *nothing* (a price list not covering the instant) leaves it `None` too; it creates no zero.
* **A partial price is a floor** (ADR-0069 — decided, no longer underdetermined). An estimate that
  did not total adds the components it did price; `money_spent` is then a floor, `exceeded` is
  certain when `True` and not when `False`, and `untotalled_debit_count` says so. Under
  `PartialPricing.STRICT` an untotalled estimate in the window makes the ceiling exceeded, at
  pre-flight too; a debit with no estimate never trips it.
* **`CurrencyMismatch` fires when any money ceiling *covering* the debit is in another currency**,
  and is checked on the currency the estimate *names* — not on whether it produced a total, since
  an estimate that failed to price today is re-costable into that currency tomorrow. Balances stay
  per-currency internally and are never summed across, so a token-only ledger accumulates USD and
  EUR side by side without refusing either.
* **`entries(since=...)` is inclusive** (`occurred_at >= since`), making the window half-open, so
  two consecutive queries with touching bounds return each entry exactly once. Naive `since` and
  naive `Debit.occurred_at` are refused.
* **`would_exceed` with neither `usage` nor `cost`** has nothing prospective to add and equals
  `remaining` — asserted by a test.
* **`InMemoryLedger` is thread-safe**; one lock per public method, so a debit and its verdicts are
  computed against one consistent state (contract 5's in-memory reading).

### 2.3 Boundary honoured

`UNPRICED_EGRESS_REFUSED` is **not** in this package. LoadLedger surfaces `unpriced_debit_count`
and says what remains; refusing an unpriced remote step is PromptCadence's policy (ADR-0047
§"Two ceilings"). `errors.py`'s module docstring records that explicitly so a future contributor
does not "helpfully" add it.

One wording to know about: the roadmap row itself (`outstanding-work.md` §1, B2) lists
"`UNPRICED_EGRESS_REFUSED` shape" in its scope column. The kickoff and ADR-0047 are explicit that
the code is PromptCadence's and this package must not raise it, and the kickoff was followed.
Read the row's phrase as "the `unpriced_debit_count` that lets PromptCadence raise it" — see §5
item 11.

---

## 3. Toolchain provenance

Copied from **`py/WeightsDB`**, as the kickoff directed. `pyproject.toml`, `.importlinter`,
`.editorconfig`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`,
`.github/workflows/release.yml`, `requirements/release.in`, `LICENSE`, `SECURITY.md`,
`CONTRIBUTING.md`. The pre-existing `.gitignore` was left untouched, as instructed
(`git status --short -- .gitignore` clean throughout).

Adapted, each deliberately:

* **No PostgreSQL `db-matrix` job and no `psycopg` in `[dev]`** — this package touches no database
  in Phase 1 and never owns one (ADR-0050). C3 will need to decide whether Phase 2's miniature
  host warrants restoring that job; the development plan says PostgreSQL in CI, so it probably
  does, and the WeightsDB job is the template.
* **No `respx` in `[dev]`** — no `httpx`, no HTTP anywhere.
* **No `[sql]` extra yet.** Declaring it before `loadledger/sql.py` exists would advertise an
  import that is not there. C3 adds `sql = ["sqlalchemy>=2,<3"]`.
* **`.importlinter` gains a third contract**, `no-sql-in-phase-1`, forbidding `sqlalchemy` and
  `alembic` outright, and lists `promptcadence` among the forbidden applications. **C3 must
  replace that contract** with one that exempts `loadledger.sql` alone — not delete it, and not
  weaken it to a warning.
* **Coverage floor 95 %** in both `pyproject.toml` and the CI `coverage` job. Note for the suite:
  MirrorWall's `coverage` job passes `--cov-fail-under=85` while its own `pyproject.toml` sets 95.
  One of those two is wrong in that repository; LoadLedger follows WeightsDB and uses 95 in both.
* **`release.yml`'s TestPyPI comment** renamed `0.2.0` → `0.1.0`.

Lockfiles compiled with **pip-tools 7.6.1 on Python 3.13**, matching the sibling header
convention. `requirements/release.lock` is **byte-identical to WeightsDB's below the header** —
that equality was checked, and is the evidence the build chain is reproducible rather than merely
pinned. `requirements/ci.lock` installs cleanly under `--require-hashes`.

Version is **`0.1.0.dev0`** (`src/loadledger/__about__.py`). Phase 1 does not publish; C3 bumps it
to `0.1.0` at the end of Phase 2.

---

## 4. Commits

All on `main`, in `py/LoadLedger`, oldest first:

```
678c8be  build: scaffold the LoadLedger repository from the suite toolchain
b2f7513  docs: mirror the authoritative LoadLedger spec and development plan
f464024  feat: add the ledger value objects and the typed refusals
ec2a3f6  feat: add scope windows, incremental balances and InMemoryLedger
aa3b3ee  test: cover the arithmetic, the honesty rules and the goldens
fefa077  docs: add README, CHANGELOG, SECURITY and CONTRIBUTING
899e87b  docs: mirror the LoadLedger spec and plan as amended by ADR-0069
364bb5e  feat: accumulate a partial price as a floor, and let a money ceiling be strict (ADR-0069)
0982c8b  docs: mirror the LoadLedger spec and plan with declare_run in §7
4c65097  docs: mirror the LoadLedger spec and plan with the window semantics confirmed
```

They sit on top of `e66f7f1 first commit` (the `.gitignore`, already on the remote). The last
four were made on 2026-09-02 after the review, on the operator's decisions; the docs repository's
matching commits are `a87dcea` (ADR-0069), `1bd4c03` (ADR-0070, `declare_run`) and `dd60b6e`
(window semantics, project budgets). Working tree clean, no tags. Everything through `0982c8b`
is on `origin/main` (pushed by the operator, 14:39 PDT); `4c65097` is not yet. `git add -A` was
never used.

Both mirrored documents verified byte-identical with `cmp` against
`/home/jpk/ai/suite/docs/packages/loadledger/`.

---

## 5. Before the next session

### Blocking C3 (LoadLedger Phase 2)

1. **Push the last commit.** `main` was pushed by the operator on 2026-09-02 at 14:39 PDT through
   `0982c8b`; `4c65097` (the spec mirror with the window semantics) is still local, as is the docs
   repository's `dd60b6e` that it mirrors. The GitHub remote **already existed and was already
   configured** — `origin` → `https://github.com/JPKell/LoadLedger.git`, with `e66f7f1` on it —
   contrary to the kickoff's precondition, which said the remote was a human step still to come;
   no remote was created by this session. `py/ModelRack`'s docs-only commit `a0f9328` was pushed
   in the same batch.
2. **Resolved.** CI on the first push, `0982c8b`, completed green on 2026-09-02 at 21:39Z
   (`https://github.com/JPKell/LoadLedger/actions/runs/33686302203`): the `security` job
   (`pip-audit` against both locks, plus gitleaks over full history, with the `fetch-depth: 0`
   inherited from WeightsDB), every 3.12 job, both legs of the test matrix, the 3.14 early
   warning, `build` and `install-check`. The commit after it, `4c65097`, is docs-only.
   ModelRack's `a0f9328` was pushed in the same batch and is green too.
3. **Reserve the PyPI name `loadledger`.** Master architecture §1.1 requires distribution-name
   availability to be verified before first publish, with `aisuite-loadledger` as the documented
   fallback. Checked at review on 2026-09-02: `https://pypi.org/pypi/loadledger/json` returns
   404, and so does the fallback (`weightsdb`, as a control, returns 200) — the name is **free but
   not reserved**, and nothing holds it until the first TestPyPI/PyPI publish. Do the reservation
   *before* C3 finishes, not at publish time — the fallback would change the import name,
   `pyproject.toml`, `.importlinter`, the coverage paths and every document that names the
   package.
4. **Configure the PyPI trusted publisher and the `pypi` GitHub environment**, and run the
   `Release → Run workflow` TestPyPI dry run once. `release.yml` expects both, and `0.1.0` will be
   this package's first real release.

### Decisions the architect should confirm before C3 builds on them

5. **Resolved.** `Ledger.declare_run` is in spec §7 (docs commit `1bd4c03`), and the Phase 2 work
   list now names the run record `SqlLedger` needs so a run declared with nothing debited survives
   a restart — a second mounted table, to be covered by the miniature-host migration test. C3
   implements both. PromptCadence declares at trajectory creation, before plan approval.
6. **Resolved.** The window semantics are confirmed as built and written into spec §2 (docs commit
   `dd60b6e`): `PER_DAY` is one UTC day across every run in the ledger, `PER_TAG` is every run and
   every day and never resets, finer windows are new scope values. Phase 2's plan tells C3 that
   `SqlLedger` is stateless, balances persist per window whatever ceilings exist, and the window
   key is a string so composite scopes need no schema change. On top of that PromptCadence gained
   per-project budgets (a `project` request label, `[budget.projects.<name>]`, `PROJECT_UNKNOWN`)
   and a per-day ceiling that parks in the new `awaiting_window` state instead of halting
   (lifecycle §8 T15–T17, `on_daily_exhausted`, `window_wait_max_days`); row J1 now sets a
   per-output and a per-project ceiling in IdeaPress.

### Things found that the plan did not name

7. **One rule refuses a total whenever a token class is unreported, and both real adapters leave
   two classes unreported.** `TokenUsage.total_tokens` and `estimate_cost` share the rule; Ollama
   and OpenAI-compatible leave the cache classes `UNSUPPORTED` by design (ADR-0016). Measured at
   review: input 1 000 and output 500 against a complete price list gives an `UNSUPPORTED` total
   with real `input_cost` and `output_cost`; the same usage with explicit zeros gives 0.0105 USD.
   No component in the suite calls `estimate_cost` yet, which is why nothing had noticed (IdeaPress
   carries its own integer-valued `TokenUsage`; LoadCoach sums no token usage; FreeWeight totals
   input and output separately). The ledger side is now settled by ADR-0069 (floor plus strict).
   **The adapter side is now decided too**, by ADR-0070: the rule is per response and lives in
   the adapter — a class the wire protocol cannot bill is `0`, a class it can express but the
   response omitted stays `UNSUPPORTED`, no usage object means every class `UNSUPPORTED`.
   OpenAI-compatible reconciles `prompt_tokens_details.cached_tokens` when present (today it reads
   none of it, so cached input is over-estimated at the full rate); Ollama reports `0` with a
   fixture check on `prompt_eval_count`; the fake defaults to `0`; llama.cpp (D3) is written to
   the rule from the start. ModelRack spec contract 2 is amended and mirrored (`a0f9328`); the
   code is roadmap row **C5**, which must land before D3. LoadCoach carrying all four classes on
   its rows and job document is row **C6**, before F1; its `api.md` and `data-model.md` still
   describe the shipped 1.0.0 shape and are amended when C6 ships. Until C5 and C6 land, every
   floor from a real adapter omits the cache classes and a `STRICT` ceiling trips on the first
   remote response — by design, and now scheduled.
8. **A `contract`-marked test is mandatory in every repository**, because CI's `contracts` job
   runs `pytest -m contract` and pytest exits 5 — a failure — when nothing is collected. A future
   scaffold copied from a sibling into a repository with no contract tests goes red on first push
   for a reason that looks nothing like the cause.
9. **MirrorWall's coverage job/pyproject mismatch** (85 vs 95), noted in §3. Not this row's to fix.
10. **`pre-commit` is not installed on this machine**, so `pre-commit install` could not be run in
    any repository. No sibling has the hook installed either, so nothing on this machine has
    exercised the suite's pre-commit configuration — only whatever CI reproduces of it.

11. **Roadmap row B2 names "`UNPRICED_EGRESS_REFUSED` shape" in its scope column** (§2.3). The
    kickoff and ADR-0047 say the opposite — the code is PromptCadence's — and the kickoff was
    followed. Worth a one-line amendment to the row so the next reader does not file it as
    undelivered.

### Not blocking

12. `docs/quickstart.md` and `docs/adoption-checklist.md` were **not** written. WeightsDB has both;
    for LoadLedger the quickstart belongs with Phase 2 (the development plan puts "README,
    quickstart (standalone mount into a script's own SQLite file)" in Phase 2's work list), and the
    adoption checklist belongs with PromptCadence P5. The README's quickstart covers Phase 1's
    surface in the meantime. No `docs/api.md` generator was added — no sibling's script dropped in
    unchanged, per the kickoff.
