# Kickoff — F4: LoadLedger Phase 3 — a balance read that names no run → publish 0.2.0

**Row:** F4 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Sonnet 5 · high**, as scheduled. Additive, against a spec that already describes the
storage; the shape is decided and the arithmetic already exists.
**Repositories, in this order:** `/home/jpk/ai/suite/docs` (the spec amendment first), then
`/home/jpk/ai/suite/py/LoadLedger`, then `/home/jpk/ai/suite/PromptCadence`, then `docs` again to
close the row.
**Ships:** `loadledger` **0.2.0** to PyPI. **You prepare the release; you do not push and you do not
tag** — see §0.3. PromptCadence takes a dependency edit and a surface change only: changelog under
`## [Unreleased]`, **no version bump, no tag, no publish**.
**Overnight:** permitted (Sonnet rows run at effort **high** overnight; batches D and G and I2's
security half are the exclusions, and this is neither). But Gate C cannot start until an operator
has published 0.2.0, so an overnight run may legitimately end at Gate B with the PromptCadence half
unstarted. **That is a complete session, not a failed one.**
**Runs after:** F1 (done, 2026-09-04). Flexible in the schedule; §3's soft edge puts it before G1,
because G1 ships the M11 beta dashboard and a column reading "1 debit(s) recorded" is a column
somebody has to explain.
**Not in this session:** a **tier ceiling** — lifecycle §6 is deliberate that none is configured and
this row adds a *view*, not a cap; G1's planner and dashboard; IdeaPress's LoadLedger adoption
(row J1); any change to the four mounted tables.

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Do not re-derive these; do **confirm** the ones marked.

* **`py/LoadLedger` `main` is at `c621ea2`**, clean, level with `origin/main`. Version **0.1.0**,
  tagged `v0.1.0`, and **`loadledger 0.1.0` is the only release on PyPI** (checked today).
  **Confirm** with `git status -sb` at the start and the end.
* **`PromptCadence` `main` is at `2bfc692`**, clean, level with `origin/main`. **Confirm.**
* **This row has a development plan — unlike F3.** `docs/packages/loadledger/development-plan.md`
  already carries **"Phase 3 — A balance read that names no run — publish 0.2.0"** with Goal, Work,
  Why this exists, Tests, Acceptance criteria, Not in this phase and Gold standards, and it is
  already mirrored into the component repo (`c621ea2`, `cmp`-identical — verified). **Read it. It is
  the contract for this row**, and the row text in `outstanding-work.md` is its summary, not a
  second source.
* **The storage already exists and this row adds none.** `mount_ledger_tables` mounts four tables;
  `{prefix}balances` is keyed `(scope, window_key)` and `{prefix}balance_money`
  `(scope, window_key, currency)` — exactly the query this row exposes. PromptCadence's migration
  `0005_ledger_tables.py` already created them. **No column changes, no new Alembic revision, and no
  entry in `py/LoadLedger/docs/mounted-table-upgrades.md`** (a repo-local doc with no workspace
  copy — spec §19's upgrade recipe is owed only when a mounted column changes, and none does).
  If you find yourself writing a migration, you have left the row.
* **What you are replacing, in PromptCadence:** `BudgetService._tier_debit_counts()` is
  `{name: len(self.entries(tag=tier_tag(name))) for name in self._settings.tiers}` — it reads every
  entry per tier to produce a count. `LedgerView.tier_debit_counts` carries it; `LedgerView.as_json`
  emits `"tiers": [{"tier": …, "debit_count": …}]`; the CLI prints
  `"{tier} {n} debit(s) recorded"` plus the line *"no tier ceiling is configured, so a tier has a
  history and not a balance"*; and `tests/e2e/test_ledger_surfaces.py:182` asserts
  `"1 debit(s) recorded"`. All five move together.
* **The reference-run workaround lives in exactly two places:**
  `web/routes/ledger.py:61` and `cli/commands/ledger.py:93`, both calling
  `TrajectoryService.most_recent_id()` (`services/trajectories.py:285`). See §0.2 before you touch
  them.
* **Renderers that already exist** in `services/budget.py`: `render_money` / `render_tokens` for a
  figure that was **spent** ("at least 0.004 USD"), and `render_remaining_money` /
  `render_remaining_tokens` for a figure that is **left** ("at most …"). The row text says the tier
  half renders through `render_money`/`render_remaining_money`; that is imprecise and §7 corrects
  it — a tier has no ceiling, so it has spend and no remaining. **Never render a spend with a
  `render_remaining_*` function**: the qualifier direction is the whole reason there are four.
* **PromptCadence pins `loadledger[sql]>=0.1,<0.2`** with a comment explaining the `[sql]` extra.
  **It has no `requirements/` locks** (unpublished app), and its CI runs `pip install -e ".[dev]"`
  against PyPI — so the moment that pin says `>=0.2`, CI is red until 0.2.0 is published. This is
  the B1-before-B3 rule and §7 is built around it.
* **Interpreters:** both venvs are **Python 3.13.15**. There is **no python3.12** on this host; CI
  covers 3.12/3.13 with 3.14 as early warning. Name the interpreter and every exact invocation in
  the report (M5C-13).
* **Coverage floor is 95 %** for a shared package (LoadLedger), 85 % for an application.

## 0.1 F3 is running in ModelRack — check before you start, and stay out of its way

F3 (ModelRack Phase 7) is executing in a separate session. It touches **`py/ModelRack`** and
**the `docs` repo** (its Gate 0 writes the ModelRack Phase 7 plan section; its Gate F closes the
row). F4 also commits to `docs`. So, before anything else:

1. **`docs/history/F3_HANDOFF.md` must exist at the workspace root.** If it does not, F3 has not finished —
   stop and say so rather than working alongside it in `docs`.
2. **`git -C /home/jpk/ai/suite/docs status --short` must be empty.** If the docs tree carries
   modifications you did not make, **stop and report them**; do not `git checkout --` anything.
   (Working-tree integrity, CLAUDE.md: a tracked file was destroyed this way on 2026-09-02.)
3. **Expect `docs` `main` to be ahead of `origin/main`** with F3's commits — the operator pushes,
   not the sessions. Commit on top. Never reset, rebase or revert.

Nothing in F4 depends on F3's *content*. Read `docs/history/F3_HANDOFF.md` only far enough to know which docs
commits are F3's, so your own row-closing edit to `outstanding-work.md` does not clobber F3's.
**Do not touch `py/ModelRack` at all.**

## 0.2 The decision this row must take, and record — the reference run

The row says the PromptCadence half must "drop `TrajectoryService.most_recent_id()`'s use as a
ledger reference". Read that carefully against what `balances()` actually returns, because
**`balances()` alone does not get you there**, and discovering that halfway through is how a
session ends up doing ledger arithmetic in an application.

* `--scope tier` needs **spend**. `balances(scope=PER_TAG, window_key="tier:local_fast")` answers it
  exactly, with no ceiling and no run. Fixed, completely.
* `--scope day` and `--scope project` need **headroom against a configured ceiling** — the cap less
  a spend that may be a floor, with `exceeded` decided under `FLOOR` or `STRICT` semantics. That is
  `BalanceBook._verdict_for`'s job. Deriving it in PromptCadence from a raw balance would put the
  floor rule and the strict rule in a consumer, which is precisely what ADR-0050's mount exists to
  prevent and what F1 refused to do.

So there are two honest routes. **Take one, and record which and why in the spec, the changelog and
the handoff:**

**(a) `balances()` plus a run-free ceiling read — recommended.** The shape F1 proposed as the
alternative: `position(...)` / `verdicts(...)` taking the configured ceilings and an instant and no
`run_id`, evaluating every ceiling whose scope is not `PER_RUN`. Mechanically it is
`BalanceBook.verdicts` minus its `run_id` argument and `SqlLedger._windows_read` minus the
`PER_RUN` key — the same engine, the same honesty counts, no new storage. It is what actually
delivers the row's stated outcome, and it makes the empty-ledger answer *honest* ("nothing has been
spent") instead of the current fallback that looks identical but is reached through `UnknownRun`.
Cost: a second public method, plus a decided-and-tested behaviour for a `PER_RUN` ceiling passed to
a run-free read (refuse it with `InvalidCeiling`, or omit it from the result — pick, document,
test).

**(b) `balances()` only.** Ship the plan's method, fix `--scope tier`, and leave the reference run
in place for the ceiling-bearing scopes. Legitimate, smaller, and honest — but then **amend the row
text in `outstanding-work.md`** to say the reference run survives and why, rather than leaving a
schedule that claims something the code does not do.

**The constraint on both, and it is absolute:** no headroom arithmetic, no floor rule and no
`exceeded` decision moves into PromptCadence. If the ledger cannot answer a question, the view says
what it can honestly say — that is what F1 did, and it is why this row exists rather than a patch.

## 0.3 You do not push, tag, or publish

Standing rule for this workspace as of 2026-09-04, and it overrides any "push and confirm CI green"
wording you find in the row, in the development plan, or in an older kickoff prompt:

* **Never run `git push`**, including `--dry-run`, and never create or push a tag.
* Commit normally, confirm `git status -sb` is clean, and **report the commits as ready to push**,
  naming each repository, branch and SHA.
* CI status and the PyPI publish can only be checked **after** the operator pushes. Say so in the
  handoff instead of checking.

Gate B below prepares the release and hands the operator the exact commands. Gate C is only
runnable once they have run them and the wheel is on PyPI.

## 1. Setup

```bash
cd /home/jpk/ai/suite/py/LoadLedger && source .venv/bin/activate
python -V                      # expect 3.13.15
pip install -e ".[dev]"        # if anything is missing
git status --short             # must be empty
```

Same shape for `/home/jpk/ai/suite/PromptCadence` when you reach Gate C. Work from inside a
component directory, never the workspace root — nothing there is versioned.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* **The finish line, in each repository you touch:**
  `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional Commit
  per phase**. Name the interpreter and the exact invocation in the report.
* **The house method:** docstring-first — define the behaviour, write the Google-style docstring
  (Args/Returns/Raises, *including what it refuses*), write the tests against it, then implement.
  `from __future__ import annotations` everywhere. Units in names. Keyword-only optionals; no
  positional booleans. Value objects `@dataclass(frozen=True, slots=True)`. Injected clocks.
* **Read `architecture/master-architecture.md` §§1–3 and gold-standards §2's LoadLedger section**
  (integer-exact, no float, no recomputation from history, unpriced is never zero) before the row's
  reading list.
* **Never `git add -A`.** Stage named paths. Commit at every boundary, not at the end.
* **Docs first, mirrors after, `cmp`-proven.** Edit `~/ai/suite/docs/...`, then copy into the
  component's `docs/` tree and prove byte-identity with `cmp`. Ruff skips `docs/` in every repo
  precisely so a mirror cannot drift by reformatting.

## 3. Reading list, in this order

1. `docs/architecture/master-architecture.md` §§1–3.
2. **`docs/packages/loadledger/development-plan.md` Phase 3** — the contract for this row.
3. `docs/packages/loadledger/spec.md` §7 (the `Ledger` protocol block you are amending), §10 (the
   four tables and why money is a table of its own), §11 contracts 2 and 6, §19, §21.
4. `py/LoadLedger/src/loadledger/core.py` — `BalanceBook`, `_ScopeBalance`, `verdicts`,
   `_verdict_for` (the three honesty counts come from there), `windows_touched`, `window_for`,
   `seed`.
5. `py/LoadLedger/src/loadledger/sql.py` — `_windows_read`, `_seed_from_rows`, `_matches_any`,
   `_reading` (the rollback-only session that keeps a read side-effect-free).
6. `ADR-0050` (the mount, and decision 4 — why `sqlalchemy` sits behind an extra), `ADR-0069` (a
   partial price is a floor), `ADR-0030` rules 1 and 3, `ADR-0016`.
7. **`docs/history/F1_HANDOFF.md` §7** — the finding this row closes, in the words of the session that met it.
8. For Gate C: `docs/apps/promptcadence/lifecycle.md` §6, `docs/apps/promptcadence/spec.md` §7.2 and
   §17, and `PromptCadence/src/promptcadence/services/budget.py` (`LedgerView`, `ledger_view`,
   `_report`, `_tier_debit_counts`, the four renderers).

## 4. The shape of the work

Four gates, strictly in order. **Gate C cannot start until `loadledger 0.2.0` is installable from
PyPI** — not "tagged", not "workflow running". Published, and install-checked.

## 5. Gate A — LoadLedger Phase 3

**A1. Decide the return type before you write anything.** The plan leaves it open ("a small value
object or a `CeilingVerdict`-shaped one with no ceiling on it"). Decide, and write the docstring
first. Guidance, not instruction:

* A frozen, slotted value object is the better default — a `CeilingVerdict` with `ceiling=None` and
  two of its fields permanently meaningless invites a caller to ask a verdict-shaped thing whether
  it was exceeded, when nothing here has a bound to be exceeded against.
* It must carry **`tokens_spent`**, the **money per currency**, and **all three honesty counts**
  (`unpriced_debit_count`, `untotalled_debit_count`, `unmetered_debit_count`). A balance without
  them is a floor presenting itself as a total — the one thing spec contract 2 forbids.
* **Money is per currency and is never summed across currencies** (ADR-0030 rule 3). A currency
  absent from the mapping has had nothing priced in it, which reads differently from zero
  (ADR-0016) — so absent, never a zero entry.
* Name it so it does not collide with the private `_ScopeBalance` in `core.py`, and export it from
  `loadledger/__init__.py`'s `__all__` alongside the rest.

**A2. Implement through the one `BalanceBook`.** Both `InMemoryLedger` and `SqlLedger` evaluate
through it, as every other method does, so the deterministic double keeps answering exactly what
production answers. `SqlLedger` seeds the single window it was asked for and reads it back; do not
add a second arithmetic path.

**A3. The contracts this read inherits.**

* **Side-effect free, structurally** (contract 6's shape): the session it opens is rolled back, and
  **a window with no row is not created**. Prove it — call `balances()` for a window nothing has
  landed in, then assert the row count in `{prefix}balances` is unchanged. This is the easy contract
  to break and the reason a missing row is read as an empty balance rather than inserted as a zero.
* **An unknown `window_key` is zero tokens, no money, no error.** `UnknownRun` cannot apply here —
  this read names no run — and "nothing spent" is a true answer, not an exception.
* **`PER_DAY` keys go through `utc_day_key`**, and a caller passing a raw date string that is not a
  UTC day key gets whatever that window holds, which is nothing. Say so in the docstring.

**A4. Tests — the plan's four, and both dialects.** A window with no ceiling still reports its
balance, on both implementations; the three counts **match what a `CeilingVerdict` over the same
window reports**, so the two reads cannot disagree; an unknown key reports zero tokens and no money;
a `per_day` key resolved through `utc_day_key` matches where a debit at that instant landed. Add a
mixed-currency window. `pytest-randomly` is on — a seed-specific failure is a real bug.

**A5. `window_keys(scope)` — include it only if you consume it.** It is cheap on both backends (a
`SELECT DISTINCT` and a dict scan), but PromptCadence does not need it: it knows its tier names from
`[tiers.<name>]` configuration. An unused public method in a 0.x package is surface you then have to
keep and version. **Default to leaving it out**; add it only if your Gate C half actually calls it,
and say which way you went in the changelog.

**A6. Performance.** The point of this read is that it does not touch `entries()`. Check spec §15's
budgets and add an assertion to `tests/performance/` if the existing files have the shape for it —
`-m performance` stays out of the default gate.

**A7. Docs, then mirror.** Amend `docs/packages/loadledger/spec.md` §7's protocol block with the new
method(s) and the value object, and §11 if you took route (a) in §0.2. Mirror into
`py/LoadLedger/docs/packages/loadledger/spec.md` and `cmp`-prove it. The spec amendment is a `docs`
repo commit; the mirror rides the LoadLedger commit, as `c621ea2` did.

**A8. Gate green, then commit.** One Conventional Commit for the feature
(`feat(balances): …`). Report the interpreter and the exact invocation.

## 6. Gate B — prepare the release, and stop

**B1.** Bump `src/loadledger/__about__.py` to `0.2.0`. Add a `## [0.2.0] — <date>` section to
`CHANGELOG.md` naming: the new read and its value object, the §0.2 decision you took, whether
`window_keys` shipped, and explicitly **"no table, column or index changed; hosts need no
migration"** — that sentence is what stops a host application going looking for one.

**B2.** Locks. This repository has two: CI installs `--require-hashes -r requirements/ci.lock`
and then `pip install . --no-deps`, and `release.yml` builds from `requirements/release.lock`.
Neither needs recompiling for this release **provided `dependencies` and the `sql` extra are
unchanged** — which they are, since this row adds no dependency. Confirm that rather than assuming
it, and say so in the handoff; E5's lesson (4) is that the `pip-compile` invocation recorded in
those lock headers no longer reproduces them (`--no-index` is now `--no-emit-index-url`), so a
needless recompile costs a detour.

**B3.** Commit (`chore(release): prepare loadledger 0.2.0`), confirm `git status -sb` clean, and
**stop.** Hand the operator these, verbatim, in the handoff — you do not run them:

```bash
cd /home/jpk/ai/suite/py/LoadLedger
git push origin main
git tag -a v0.2.0 -m "loadledger 0.2.0 — a balance read that names no run"
git push origin v0.2.0
# release.yml then builds from requirements/release.lock, runs the gate against the built wheel,
# and waits on the `pypi` environment approval — which is yours, in the GitHub UI.
```

No TestPyPI dry run is required: packaging and release standards §6 asks for one before a package's
*first* release, and `loadledger` published 0.1.0 already, so trusted publishing is configured.

**B4.** After they approve, the install check (outstanding-work §4's per-release step) is
`pip download loadledger==0.2.0 --no-deps -d /tmp/…` in a clean environment, and
`pip install "loadledger[sql]==0.2.0"` resolving `sqlalchemy`.

**B5. Hard stop.** If the push or the `pypi` approval has not happened in this session, **end
here**. Write the handoff, say exactly where it stopped, and make it resumable from B3. Do **not**
start Gate C against an unpublished wheel, and in particular **do not move PromptCadence's pin to a
version that does not exist on PyPI** — that is a red CI run the operator has to come back and
explain.

## 7. Gate C — PromptCadence, once 0.2.0 is on PyPI

One repository, its own commits, no version bump and no tag.

**C1. The pin.** `loadledger[sql]>=0.1,<0.2` → `>=0.2,<0.3`, keeping the existing comment about why
the `[sql]` extra and not the bare package, and adding one line for why the floor moved (the
run-free balance read; a floor below the surface this application calls is drift that stays
invisible until someone installs the wrong thing — E5's lesson (1)). Then **verify the installed
version rather than assuming the reinstall moved it** — E5's lesson (2): a widened pin does not move
an existing venv, and looks exactly like success when it does not.

```bash
source .venv/bin/activate
pip install -U "loadledger[sql]>=0.2,<0.3" && pip show loadledger   # must print 0.2.0
```

**C2. The service.** `_tier_debit_counts()` becomes a real spend read, calling
`balances(scope=PER_TAG, window_key=tier_tag(name))` once per configured tier. `LedgerView`'s field
and its docstring change with it — the current text explains why a count is all that can honestly be
reported, and that reason is now gone. **No arithmetic is added to `budget.py`**: it asks, renders
and returns.

**C3. The wire.** `"tiers"` carries spend, not a count: the tokens, the per-currency money, the
three counts, and the rendered strings beside the numbers exactly as `_headroom_json` does — the
numbers for a caller that computes, the strings for a caller that displays, so no surface invents
its own way to show a floor. Two specifics:

* Use **`render_money` / `render_tokens`** — the *spent* renderers, which qualify with "at least".
  A tier has no ceiling and therefore no remaining, so `render_remaining_*` has nothing to render
  and would qualify in the wrong direction.
* **Money is a list, not a figure.** A window's money is per currency and the currency set is open;
  emitting one total would be conversion, which ADR-0030 rule 3 forbids. Emit an array of
  `{currency, nanos, display}` even where today's configuration only ever produces one entry, and
  have the CLI print one line per currency. `NOT_PRICED` (`—`) for a tier that has spent nothing
  priced — never `$0.00`.

**C4. The reference run.** Per your §0.2 decision. If you took (a), remove the `most_recent_id()`
call from `web/routes/ledger.py` and `cli/commands/ledger.py`, then check whether
`TrajectoryService.most_recent_id()` has any caller left — if not, delete it and its tests rather
than leaving a method whose docstring describes a workaround that no longer exists.

**C5. The CLI text.** The line *"no tier ceiling is configured, so a tier has a history and not a
balance"* is now false. Replace it with what is still true and worth saying: no tier ceiling is
configured, so these are balances and not headroom — nothing here can be exceeded.

**C6. Tests.** `tests/e2e/test_ledger_surfaces.py` asserts `"1 debit(s) recorded"`; that assertion
becomes one about a rendered spend. Add: a tier whose only debit was unpriced renders `—` and not a
zero; a tier with an untotalled estimate renders "at least"; the API and the CLI print the same
figure for the same tier (the existing `projects` test is the pattern).

**C7. Docs, then mirror.** In `~/ai/suite/docs`: `apps/promptcadence/lifecycle.md` §6 (the sentence
at ~line 286, "a tier has a *history* and not a balance — the ledger views report its debit
count…"), `apps/promptcadence/spec.md` §7.2's `ledger show` line if its wording implies a count, and
§17's `system/status` bullet if the per-tier figure appears there. Mirror into
`PromptCadence/docs/...` and `cmp`-prove.

**C8. Gate green, `CHANGELOG.md` under `## [Unreleased]`, one or two Conventional Commits** (the
dependency edit and the surface change may be separate; the docs mirror rides the code commit).
**Say in the handoff that PromptCadence CI is red until `loadledger 0.2.0` is on PyPI**, and that
the operator's push order is **LoadLedger's tag first, PromptCadence second.**

## 8. Exit conditions — all of these, demonstrably

1. `promptcadence ledger show --scope tier` prints, per tier, tokens and money **spent**, floors
   qualified "at least", unpriced tiers as `—`, with **no ceiling configured and none invented**.
   Paste the actual output into the handoff — the plan's acceptance criterion 1 is this line.
2. `GET /api/v1/ledger`'s `tiers` array carries the spend, the three honesty counts and the rendered
   strings; the CLI and the API agree, proven by a test.
3. **No ledger arithmetic in PromptCadence.** A reviewer can grep `services/budget.py` and find no
   summation over entries or balances — every figure it renders came from LoadLedger already
   computed.
4. The three honesty counts a `balances()` read returns equal what a `CeilingVerdict` over the same
   window reports, on both implementations and both dialects.
5. Full gate green in `py/LoadLedger` and in `PromptCadence`, each with its interpreter and exact
   invocation named; LoadLedger coverage ≥ 95 %.
6. Every doc touched is `cmp`-identical to its mirror, and the command that proved it is in the
   report.
7. `loadledger 0.2.0` is installable from PyPI — **operator step**, recorded as done or as pending.

## 9. Closing duties

1. **`docs/history/F4_HANDOFF.md` at the workspace root**, in the shape of `docs/history/F1_HANDOFF.md`: what was built; the
   §0.2 decision and why; whether `window_keys` shipped; **what this row's text said that turned out
   not to be true** (start with `render_remaining_money` for a tier spend, which §0.3 of the row
   text gets wrong, and add whatever else you find); the exact commands and outputs behind each exit
   condition; and what G1 must not relitigate.
2. **Amend the F4 row in `docs/roadmap/outstanding-work.md`** to `**Done <date>**` with the handoff
   name and every commit SHA, in the shape F1, F2 and E5 use. If you took route (b), correct the
   row's "drop `most_recent_id()`" claim in the same edit.
3. **§3's soft edge:** mark whether F4-before-G1 is now satisfied, so G1's session does not have to
   re-derive it.
4. `git status --short` in every repository you touched — clean — and report each branch and SHA as
   **ready to push**, with the push order from C8.

## 10. Stop rules

* **Never push, tag, or approve the `pypi` environment.** §0.3.
* **Never weaken `.importlinter`** in either repo to make an import work.
* **No ledger arithmetic in PromptCadence** — no summing `entries()`, no cap-minus-spend, no floor
  rule, no `exceeded` decision. If you cannot get a number honestly, the view says less.
* **No tier ceiling.** Not as a default, not as a test fixture standing in for one, not "just to see
  the headroom render". Lifecycle §6 configures none deliberately.
* **No table, column, index or migration change**, in either repo.
* **Do not touch `py/ModelRack`**, and stop if the `docs` tree carries changes you did not make
  (§0.1).
* **Do not move PromptCadence's pin before the wheel exists** (§6 B5).
* If the row's scope starts growing — a second consumer, IdeaPress's adoption, a dashboard —
  **stop and write it into the handoff as the next row's work.**

## 11. If you finish with capacity left

Do **not** start G1, H1 or J1. In priority order, read-only:
(a) confirm from the published wheel that `loadledger[sql]==0.2.0` resolves cleanly in a fresh venv
with `baseaicore` and `sqlalchemy` only, and that the pure core still installs with neither;
(b) re-read `docs/packages/loadledger/spec.md` §21 and note whether this row's read changes what the
"composite windows" future extension would cost;
(c) check whether IdeaPress's planned adoption (row J1) would want `window_keys(scope)` after all,
and record the finding — one paragraph in the handoff, no code.
