# F4 — LoadLedger Phase 3: a balance read that names no run

**Row:** F4 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-04.
**Interpreter:** Python **3.13.15** in `py/LoadLedger/.venv` (`.venv/bin/python -V`). No python3.12
on this host; CI covers 3.12/3.13 with 3.14 as early warning.

**State: the row is complete.** `loadledger 0.2.0` is published, PromptCadence consumes it, and
`--scope tier` reports spend. The session paused at Gate B's hard stop (§6 B5) until the operator
pushed the tag and approved the `pypi` environment, then ran Gate C against the published wheel.

| Gate | What it was | Result |
|---|---|---|
| Pre-flight (§0.1) | F3 finished, `docs` clean | `docs/history/F3_HANDOFF.md` present; `docs` clean and ahead 4 (F3's `5946e3e`, `23e372c`, `9196580`, `986ab25`); LoadLedger at `c621ea2`, PromptCadence at `2bfc692`, both clean and level — all as §0 stated |
| A | LoadLedger Phase 3 | **Done.** `docs` `478973b`, LoadLedger `9e1d15a` |
| B | Prepare the release | **Done.** LoadLedger `e579f15`. Locks unchanged and proven so; wheel built and install-checked locally before the tag |
| — | The publish | **Operator's.** Tag `v0.2.0` → `e579f15`; run 33930614246 green in 1m1s; both files `200 OK` to `upload.pypi.org`. `loadledger 0.2.0` live |
| C | PromptCadence | **Done.** `95b7719` + `de8d918`, `docs` `7a4bddd` |

---

## 1. Commits

**This session pushed, tagged and published nothing** (§0.3). The operator pushed and tagged
LoadLedger mid-session, which is the first half of Gate B's push order; the second half —
PromptCadence — is still theirs to run.

**Only `py/LoadLedger` was pushed** — its two commits and the `v0.2.0` tag, by the operator
mid-session, which is what put `loadledger 0.2.0` on PyPI. **`docs` and `PromptCadence` are both
unpushed**, verified rather than assumed: `git ls-remote origin main` in `docs` returns `2eaa73b`
and `git branch -r --contains 478973b` is empty. `docs` is ahead 7 — F3's four commits and F4's
three — so pushing it publishes F3's work too, which is expected and is what F3's handoff says.

| Repository | Branch | SHA | Commit | Pushed |
|---|---|---|---|---|
| `~/ai/suite/py/LoadLedger` | `main` | `9e1d15a` | `feat(balances): a balance read that names no run, and a run-free position` | yes |
| `~/ai/suite/py/LoadLedger` | `main` | `e579f15` | `chore(release): prepare loadledger 0.2.0` — tagged `v0.2.0` | yes |
| `~/ai/suite/docs` | `main` | `478973b` | `docs(loadledger): a balance read that names no run, and a run-free position` | **no** |
| `~/ai/suite/docs` | `main` | `bb07ea4` | `docs(roadmap): F4 through Gate B …` | **no** |
| `~/ai/suite/PromptCadence` | `main` | `95b7719` | `build(deps): require loadledger[sql]>=0.2,<0.3` | **no** |
| `~/ai/suite/PromptCadence` | `main` | `de8d918` | `feat(ledger): a tier reports what it spent, and no surface names a reference run` | **no** |
| `~/ai/suite/docs` | `main` | `7a4bddd` | `docs(roadmap): F4 done …` + the lifecycle §6 amendment | **no** |

`git status --short` is empty in all three. `py/ModelRack` was not touched (its five unpushed
commits are F3's).

**What is left for the operator:**

```bash
cd /home/jpk/ai/suite/docs         && git push origin main    # 7 commits: F3's four, F4's three
cd /home/jpk/ai/suite/PromptCadence && git push origin main   # 2 commits
```

PromptCadence's CI installs `-e ".[dev]"` against PyPI and `loadledger 0.2.0` is published, so the
`>=0.2,<0.3` pin resolves and CI should be green on the first push. **No tag and no publish for
PromptCadence** — it is unreleased, and this row bumped no version.

## 2. The §0.2 decision: **route (a)**, and why

**Route (a): `balances()` *plus* a run-free ceiling read.** Two public methods shipped:

```python
def balances(self, *, scope: CeilingScope, window_key: str) -> WindowBalance: ...
def position(self) -> tuple[CeilingVerdict, ...]: ...
```

The reasoning is the one §0.2 sets out, and it survived contact with the code. `balances()` fixes
`--scope tier` completely and fixes nothing else: `--scope day` and `--scope project` need
**headroom against a configured ceiling** — the cap less a spend that may be a floor, with
`exceeded` decided under `FLOOR` or `STRICT` — and deriving that in PromptCadence from a raw
balance would put the floor rule and the strict rule in a consumer. Route (b) would have shipped a
row whose own text promised to retire `most_recent_id()` and did not.

`position()` is mechanically `BalanceBook.verdicts` without its `run_id` and
`SqlLedger._windows_read` without the `PER_RUN` key: the same engine, the same honesty counts, no
new storage, no second arithmetic path.

**Route (a) is also a net deletion in PromptCadence**, which is worth knowing before Gate C runs.
`_report(reference_run, ceilings)` loses its `reference_run` and its `UnknownRun` fallback and
becomes a call to `position()`: on an empty ledger that already returns what the fallback
fabricated, with the difference that it is *true* rather than reached through an exception.
`ledger_view`'s `reference_run` parameter disappears, both call sites drop `most_recent_id()`, and
`TrajectoryService.most_recent_id()` then has **no caller left** and should go with its tests
(§7 C4).

**`_empty(ceiling)` and `_scope_label_of(ceiling)` do *not* become dead**, and an earlier draft of
this handoff said they would — checked and wrong. `_report` is only two of four call sites;
`position(view)` and `preflight(view, …)` also fall back to `_empty` when `remaining` /
`would_exceed` raise `UnknownRun` for a trajectory row written before Phase 5 existed. Those are
genuinely per-run reads, `position()` cannot serve them, and the fallback stays.

### The one behaviour §0.2 told this row to pick: a `PER_RUN` ceiling passed to a run-free read

**Decided: refuse it with `InvalidCeiling`.** Documented in spec §13, tested on both
implementations.

Omitting it from the result was the alternative and is worse. Every verdict-returning method in
this package documents that it returns "one verdict per configured ceiling, in configuration
order, so a caller can pair verdicts with the configuration that produced them positionally" —
PromptCadence's `_report` relies on exactly that, with `zip(..., strict=True)`. Silently returning
a shorter tuple breaks a documented invariant at a distance. Refusing states the real situation: a
per-run cap has no window without a run, and the caller should ask through `remaining(run_id)`.
The cost is nil in practice — a caller that holds one ledger for every ceiling it knows about
builds a second over the ledger-wide subset, which is free, because `SqlLedger` caches nothing
between calls and PromptCadence already builds its ledger per operation.

## 3. `window_keys(scope)`: **not shipped**

Cheap on both backends, and not needed. PromptCadence knows its tier names from `[tiers.<name>]`
configuration and never asks the ledger which tags exist. An unused public method in a 0.x package
is surface that has to be kept and versioned. Recorded in `CHANGELOG.md` and in the development
plan, so the next row does not re-open it as an oversight. See §9(c) for whether J1 changes that.

## 4. `WindowBalance` — the return type, and the one place it departs from the plan

```python
@dataclass(frozen=True, slots=True)
class WindowBalance:
    scope: CeilingScope
    window_key: str
    tokens_spent: int = 0
    money_spent: tuple[Money, ...] = ()      # one per currency, ascending by code
    unpriced_debit_count: int = 0
    untotalled_debit_count: int = 0
    unmetered_debit_count: int = 0
    def as_canonical(self) -> dict[str, Any]: ...
```

A frozen, slotted value object rather than a `CeilingVerdict` with `ceiling=None`, per A1: a
verdict exists to say whether a bound was crossed, and nothing here has a bound. It carries all
three honesty counts because a balance without them is a floor presenting itself as a total (spec
contract 2). `as_canonical()` because every other value object in `types.py` has one.

**Money is a tuple, not a single figure and not `None`.** The development plan's Tests section said
"an unknown `window_key` reports zero tokens and `money=None`", which was written before the
per-currency shape was settled and cannot be right: a window's money is per currency and the
currency set is open, so one figure would be a conversion (ADR-0030 rule 3). An **empty tuple** is
the "nothing has been priced here" answer, and a currency absent from the tuple has had nothing
priced in it, which is not zero (ADR-0016). The plan has been amended to say so (`478973b`).

## 5. Contracts this read inherits, and how each is proven

* **Side-effect free, structurally.** `SqlLedger.balances`/`position` open `_reading()`, which
  rolls back and never commits. `test_an_unknown_window_reports_nothing_spent_and_creates_no_row`
  takes a full `snapshot()` of all four tables, asks about a window nothing has landed in, calls
  `position()` twenty times, and asserts the snapshot is byte-identical. **A missing row is read as
  an empty balance, never inserted as a zero** — the easy contract to break here.
* **An unknown `window_key` is zero tokens, no money, no error.** `UnknownRun` cannot apply: this
  read names no run. Recorded as a §13 row.
* **A blank `window_key` is a `ValueError`**, on `declare_run`'s precedent — a blank key names a
  window nothing can land in, so an empty balance would look exactly like a real one.
* **`PER_DAY` keys are whatever `utc_day_key` spells.** A caller passing `"2026-9-2"` gets the
  empty window it names, documented rather than corrected; `utc_day_key` is exported so nobody has
  to guess. Tested both ways, including across a UTC midnight.
* **The two reads cannot disagree.** The three counts a `balances()` read returns are asserted
  equal to what a `CeilingVerdict` over the same window reports, on `InMemoryLedger`
  (`tests/unit/test_balances.py`) and on `SqlLedger` (`tests/integration/test_sql_ledger.py`), with
  a window contrived so all three counts are non-zero and distinct — `(3, 2, 1)` — so a mismatch
  cannot hide behind a zero.

## 6. Gate results — exact invocations

All from `/home/jpk/ai/suite/py/LoadLedger`, interpreter `.venv/bin/python` = **Python 3.13.15**.

```
.venv/bin/ruff format --check .                       36 files already formatted
.venv/bin/ruff check .                                All checks passed!
.venv/bin/mypy src tests                              Success: no issues found in 25 source files
.venv/bin/lint-imports                                Contracts: 3 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                                      192 passed, 31 skipped, 6 deselected in 2.00s
.venv/bin/python -m pytest ... --cov --cov-report=term-missing
                                                      TOTAL 564 stmts, 0 miss — 100.00%
                                                      (floor is 95 % for a shared package)
```

**PromptCadence**, from `/home/jpk/ai/suite/PromptCadence`, interpreter `.venv/bin/python` =
**Python 3.13.15**:

```
.venv/bin/ruff format --check .                       107 files already formatted
.venv/bin/ruff check .                                All checks passed!
.venv/bin/mypy src tests                              Success: no issues found in 104 source files
.venv/bin/lint-imports                                Contracts: 5 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                                      912 passed, 2 skipped, 2 deselected in 15.98s
                                                      (was 907 before this row's five new tests)
.venv/bin/python -m pytest ... --cov                  TOTAL 92.25% (floor 85 % for an application)
.venv/bin/pip check                                   No broken requirements found.
```

The 31 skips in LoadLedger are the PostgreSQL legs: no server on this host, and each skip names the URL it looked
for. CI's `db-matrix` job sets `LOADLEDGER_REQUIRE_POSTGRES=1`, which turns those skips into
failures — **so the both-dialects half of A4 is asserted here and enforced there, not here.** Every
new integration test runs on the `engine` fixture and therefore on both legs.

Performance (`-m performance`, excluded from the gate, 4 passed in 58.61 s):

| Measure | Spec §15 target | Measured |
|---|---|---|
| `balances` for one window, 10 000 entries behind it | ≤ 2 ms | **0.19 ms** |
| `position` over two ledger-wide ceilings | ≤ 2 ms | **0.26 ms** |

Neither moves with the size of the history — both are primary-key lookups over `{prefix}balances`
and `{prefix}balance_money`, and neither touches `{prefix}entries`. That is the point of the row:
the thing it replaces (`len(self.entries(tag=...))` per tier) materializes the whole history.

## 7. Docs, and the `cmp` that proved the mirrors

Edited in `~/ai/suite/docs` first, then copied into `py/LoadLedger/docs/` and proven:

```bash
cmp packages/loadledger/spec.md \
    /home/jpk/ai/suite/py/LoadLedger/docs/packages/loadledger/spec.md
cmp packages/loadledger/development-plan.md \
    /home/jpk/ai/suite/py/LoadLedger/docs/packages/loadledger/development-plan.md
# both silent — byte-identical
```

* **spec §7** — `WindowBalance` and the two protocol methods, with the refusals in the comments.
* **spec §11 contract 6** — was "`would_exceed` has no side effects"; now covers all three read
  paths and states the row-count proof.
* **spec §13** — three new rows: an unknown window is not an error; a blank key is a `ValueError`;
  a `PER_RUN` ceiling passed to `position()` is an `InvalidCeiling`.
* **spec §15** — the two budgets above, and why neither moves with the history.
* **development-plan Phase 3** — `position()` added to Work with the reason `balances()` alone does
  not close F1's finding; `window_keys` recorded as deliberately not shipped; the `money=None` test
  bullet corrected to the per-currency tuple (§4).

**No table, column or index changed, no Alembic revision, and nothing is owed to
`py/LoadLedger/docs/mounted-table-upgrades.md`** — spec §19's recipe is owed only when a mounted
column changes.

## 8. Gate B — what the operator runs, and what was checked first

**Locks: neither needs recompiling, and this was checked rather than assumed.**
`git diff v0.1.0 --stat -- pyproject.toml requirements/` is **empty** — `dependencies`
(`baseaicore>=0.4,<0.5`) and the `sql` extra (`sqlalchemy>=2,<3`) are untouched since 0.1.0, and
this row adds no dependency. Deliberately not recompiled: E5's lesson (4) is that the `pip-compile`
invocation recorded in those lock headers no longer reproduces them (`--no-index` is now
`--no-emit-index-url`), so a needless recompile is a detour with a diff.

**The wheel was built and install-checked locally**, from the working tree at `e579f15` — the same
artifact `release.yml` will build, so a packaging break would have surfaced before the tag rather
than inside the release workflow:

```
python -m build           →  loadledger-0.2.0-py3-none-any.whl, loadledger-0.2.0.tar.gz
pip install <wheel>       →  baseaicore==0.4.1, loadledger==0.2.0 and nothing else
                             `import sqlalchemy` fails; `from loadledger.sql import SqlLedger`
                             raises ModuleNotFoundError — ADR-0050 decision 4 holds
pip install "<wheel>[sql]"→  + SQLAlchemy 2.0.52 (greenlet, typing_extensions); a mounted
                             SqlLedger debits and answers balances()/position()
```

**Then, in this order, by the operator — nothing below was run by this session. All of it has now
happened:** tag `v0.2.0` points at `e579f15`, release run 33930614246 went green in 1m1s, and
twine reported `200 OK` from `upload.pypi.org` for both the wheel and the sdist.

```bash
cd /home/jpk/ai/suite/docs && git push origin main          # 5 commits, F3's four and this row's one

cd /home/jpk/ai/suite/py/LoadLedger
git push origin main
git tag -a v0.2.0 -m "loadledger 0.2.0 — a balance read that names no run"
git push origin v0.2.0
# release.yml builds from requirements/release.lock, runs the gate against the built wheel, and
# waits on the `pypi` environment approval — which is yours, in the GitHub UI.
```

No TestPyPI dry run: packaging and release standards §6 asks for one before a package's *first*
release, and `loadledger` published 0.1.0, so trusted publishing is already configured.

**B4, the per-release install check (outstanding-work §4) — run, and green:**

```
pip download loadledger==0.2.0 --no-deps --no-cache-dir   loadledger-0.2.0-py3-none-any.whl
pip install "loadledger[sql]==0.2.0"  (fresh venv)        baseaicore 0.4.1, SQLAlchemy 2.0.52,
                                                          greenlet, typing_extensions
                                                          → balances/position present on both
```

**One thing worth recording for the next release:** for several minutes after twine's `200 OK`,
both `pip index versions` **and** PyPI's own JSON API still reported `0.1.0` as the only release.
The publish had succeeded; the index was stale. A session that treats "PyPI does not list it yet"
as "the publish failed" will go looking for a problem that is not there — **read the release run's
log for twine's response before concluding anything from the index.**

## 9. Gate C — what was built

**C1 the pin.** `loadledger[sql]>=0.1,<0.2` → `>=0.2,<0.3`, with the `[sql]` comment kept and a
paragraph added for why the floor moved. **The installed version was verified, not assumed**
(E5's lesson 2): `pip install -U "loadledger[sql]>=0.2,<0.3" && pip show loadledger` → `0.2.0`.
The first reinstall printed a resolver conflict against the *editable* metadata built before the
edit; `pip install -e ".[dev]"` refreshed it and `pip check` then reported **no broken
requirements**. Worth knowing: the conflict line is what a stale editable install looks like, not
a real conflict.

**C2 the service.** `_tier_debit_counts()` → `_tier_balances()`, returning
`Mapping[str, WindowBalance]`. It builds **one** ledger and calls
`balances(scope=PER_TAG, window_key=tier_tag(name))` per configured tier — a primary-key lookup
each, against the `len(self.entries(tag=...))` per tier it replaced, which materialized the whole
history once per tier. `LedgerView.tier_debit_counts` → `tier_balances`, and its docstring, which
existed to explain why a count was all that could honestly be reported, now explains what changed.

**C2b `_report`.** Lost `reference_run`; calls `Ledger.position()`; the `UnknownRun` fallback is
gone. `ledger_view(*, reference_run, trajectory)` → `ledger_view(*, trajectory)` — the trajectory
half is the only part of the view that is about one run, and now the only part that names one.
`LedgerView.day` is no longer `| None`: that optionality was already unreachable (`_report` always
returned a headroom either way), and `position()` removes the reason it was ever written.

**C3 the wire.** `_balance_json(balance)`, the counterpart of `_headroom_json`, emitting
`tokens_spent`, `tokens_spent_display`, `money_spent` (a list), `money_spent_display`,
`money_is_floor`, `tokens_are_floor` and the three counts. It deliberately carries **no**
`money_remaining`, `tokens_remaining`, `exceeded` or `binds` — a tier has no cap to have room in
or to cross, and emitting either would mean inventing one. Asserted absent by test.

**C4 the reference run.** `most_recent_id()` removed from `web/routes/ledger.py` and
`cli/commands/ledger.py`, then **the method itself deleted** from `services/trajectories.py` — it
had no caller left, and no test referenced it.

**C5 the CLI text.** *"no tier ceiling is configured, so a tier has a history and not a balance"* →
*"no tier ceiling is configured, so these are balances and not headroom — nothing here can be
exceeded"*. A new `_spend_line` renders a tier: it says "spent", never "left", and can never print
`EXCEEDED`.

**C6 tests.** `tests/e2e/test_ledger_surfaces.py:182`'s `"1 debit(s) recorded"` became assertions
about a rendered spend (and that `"debit(s) recorded"`, `"left"` and `"EXCEEDED"` are *absent*).
Three tests added there — an unpriced tier renders `—` with a token floor and carries none of a
ceiling's fields; the CLI and the API print the same tier figures; the position answers an empty
ledger with no run named and no fabricated zero — and one in
`tests/integration/test_budget.py`, over the existing `_partial` harness, for the case the fake
LoadCoach cannot produce: **a tier whose estimate did not total renders "at least 0.004 USD"**,
with `untotalled_debit_count == 1`, and explicitly not "at most".

**C7 docs.** `apps/promptcadence/lifecycle.md` §6's sentence at ~line 285, mirrored and
`cmp`-proven. **Spec §7.2 and §17 needed no change and were left alone** — §7.2's line is the CLI
signature (`--scope day|project|tier|trajectory`) with no wording about counts, and §17's per-tier
bullet is *availability*, not spend. C7 named both as candidates; neither was.

**C8.** Two Conventional Commits, `CHANGELOG.md` under `## [Unreleased]`, **no version bump, no
tag, no publish**.

## 10. What this row's text said that turned out not to be true

1. **"rendered through the existing `render_money`/`render_remaining_money`"** (the row text in
   `outstanding-work.md`, and §0.3 of the kickoff flags it). A tier has no ceiling, therefore no
   remaining, therefore nothing for `render_remaining_money` to render. The tier half renders
   through `render_money` / `render_tokens` — the *spent* pair, which qualify a floor with "at
   least". `render_remaining_*` qualify with "at most", because a cap less a floor is an **upper**
   bound; using them on a spend would qualify in the wrong direction, which is the whole reason
   there are four functions.
2. **"an unknown `window_key` reports zero tokens and `money=None`"** (development plan, Tests).
   Money on a window is per currency and the currency set is open; a single `None` cannot express
   "nothing priced in any of them" without also implying there is only one of them. It is an empty
   tuple. Plan amended (§4).
3. **"`balances()` … removes both workarounds"** (`docs/history/F1_HANDOFF.md` §7, and the row text's "drop
   `most_recent_id()`"). It removes one. The `--scope day` and `--scope project` workaround needs a
   ceiling evaluated without a run, which is `position()`. §0.2 of the kickoff had already caught
   this — it is recorded here because the *row* and the *earlier handoff* still say otherwise, and
   a future reader will meet those first.
4. **"the row's second commit is in PromptCadence"** — implied by "same row, second commit". It
   cannot be, in the same session, unless the operator publishes mid-session. The B1-before-B3
   ordering makes Gate C a separate sitting by construction.

## 11. What G1 must not relitigate

* **There is no tier ceiling and none was added** — not as a default, not as a fixture. Lifecycle §6
  configures none deliberately. A tier has a **balance**; it has no headroom, and nothing about it
  can be `exceeded`. The dashboard shows spend.
* **The `PER_RUN`-refusal in `position()`** is decided (§2). A dashboard builds its ledger over the
  ledger-wide ceilings; it does not pass a trajectory cap to a ledger-wide read.
* **`window_keys(scope)` is deliberately absent** (§3). If G1's dashboard wants "which tags have
  spent anything" over tags it did not configure, that is a new row against LoadLedger, not a
  patch — and it is a `SELECT DISTINCT` on an already-indexed key, so it is cheap when it is asked
  for.
* **Money is per currency, everywhere, and never summed across currencies** (ADR-0030 rule 3). A
  dashboard column that totals two currencies is a conversion.

## 12. §3's soft edge

**F4-before-G1 is satisfied.** `promptcadence ledger show --scope tier` and `GET /api/v1/ledger`'s
`tiers` array both report spend, so the column G1 was warned about — `"1 debit(s) recorded"` — no
longer exists anywhere. G1 can build the M11 beta dashboard's per-tier column directly against
`tiers[].tokens_spent` / `money_spent` and the rendered strings beside them, and does not need to
re-derive any of this.

The exit-condition-1 output, verbatim, from the real CLI against a real completed trajectory on the
fake LoadCoach:

```
UTC day 2026-09-04  (as of 2026-09-04T23:53:23.564Z)
local_fast               money                      — spent   tokens   at least 916 spent
local_large              money                      — spent   tokens              0 spent
no tier ceiling is configured, so these are balances and not headroom — nothing here can be exceeded
```

and the matching `GET /api/v1/ledger` `tiers` entry:

```json
{
  "tier": "local_fast",
  "tokens_spent": 916,
  "tokens_spent_display": "at least 916",
  "money_spent": [],
  "money_spent_display": "—",
  "money_is_floor": true,
  "tokens_are_floor": true,
  "unpriced_debit_count": 1,
  "untotalled_debit_count": 0,
  "unmetered_debit_count": 1
}
```

Both tiers ran locally and priced nothing, so money is an em dash and never `$0.00`; the fake
reports no cache classes, so the token figure is a floor and says "at least". `local_large` ran
nothing at all: zero tokens, still no money, and **not** a floor — a window nothing landed in is
honestly zero, where an *unreported class* is excluded rather than counted as zero. That
distinction is the one ADR-0016 exists for, and it is visible in one screen of output.

**Exit condition 3, checked by grep as the row asks:** `grep -n "sum(\|len(self.entries\|for .* in
.*entries()" src/promptcadence/services/budget.py` returns exactly one line, and it is inside
`_tier_balances`'s docstring describing the read it replaced. `self.entries()` survives in two
places, neither of them arithmetic: `entry_views` (the debit history list) and `debited_turn_ids`
(reconciliation's idempotence).

## 13. Read-only findings (§11 of the kickoff)

**(a) The published wheel** — checked, and sound in both shapes. From PyPI:
`loadledger[sql]==0.2.0` resolves to `baseaicore 0.4.1` + `SQLAlchemy 2.0.52` (with `greenlet` and
`typing_extensions`) and mounts, debits and answers `balances()`/`position()`. The **pure** core
installs with `baseaicore` and nothing else — `import sqlalchemy` fails and
`from loadledger.sql import SqlLedger` raises `ModuleNotFoundError`, which is ADR-0050 decision 4
holding at the package boundary rather than only in `.importlinter`.

**(b) Spec §21's "composite windows" extension, after this row.** Cheaper on one side, and it
gains exactly one new obligation. `balances(*, scope, window_key)` takes the scope and the key
separately and holds no assumption about how a key is spelled, so a composite scope (`PER_RUN` ×
tag, `PER_DAY` × tag) needs **no signature change and no new storage** — the persisted key is
already `(scope, window_key)`. The new obligation is `position()`'s refusal: it is written as "is
this ceiling `PER_RUN`", and a composite `per_run_tag` scope would also need a run. That predicate
becomes "does this scope need a run", and the extension must move it rather than add a second
check. One line, but it is the line that would be missed.

**(c) Would IdeaPress's J1 adoption want `window_keys(scope)`?** On the evidence, no. Spec §21 says
J1 sets a per-output and a per-project ceiling **from IdeaPress's configuration**, so it knows its
tags the same way PromptCadence knows its tier names — `window_keys` answers a question a
configured consumer never asks. It would be wanted only by a *discovery* view: "which units cost
the most", over run ids nobody configured, which is `window_keys(CeilingScope.PER_RUN)` and then a
`balances()` per key. If J1's plan grows such a view, it should add the method in that row rather
than J1 discovering it missing — the method is a `SELECT DISTINCT window_key` on the primary key's
leading column and a dict scan in memory, so it costs a phase nothing to add when it is actually
consumed.
