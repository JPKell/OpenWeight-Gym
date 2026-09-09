# Kickoff — F1: PromptCadence Phase 5 — Budget

**Row:** F1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** the row schedules a **split — Opus 5 · high for the core, Sonnet 5 · high for the edges**.
§0.3 below says where the seam actually falls. If you are running this single-session, run the whole
row at **Opus 5 · high**: the reconciliation is money-adjacent crash logic and §3.3 of
[model-assignment](docs/roadmap/model-assignment.md) does not economize on it.
**Repositories:** `/home/jpk/ai/suite/PromptCadence`, then `/home/jpk/ai/suite/docs`.
**Ships:** nothing to PyPI. `promptcadence` is not on PyPI at all and stays that way until **G1**
(0.9.0b0, the M11 beta). Changelog under `## [Unreleased]`, no version bump, no tag.
**Overnight:** permitted, but see §0.4 — this row has a genuine "stop and ask" shape at one point.
**Runs after:** C3 (LoadLedger Phase 2), C6 (LoadCoach's four token classes) and E4 (P4). **E6
should land first** — its fake-provider fix is what keeps this row's journeys from depending on a
free GPU.
**Not in this session:** egress, verification, deviations (**F2**); planning, approval modes,
approval-gated ceiling raises (**G1**); compaction (**P8**).

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Do not re-derive these; do **confirm** the ones marked.

* **PromptCadence `main` is at `5247a83`**, clean, level with `origin/main`, **CI green** at that
  commit. Version `0.1.0`; P1–P4 built. **Confirm** with `git status -sb` at the start and end.
* **`loadledger 0.1.0` is on PyPI** — the prerequisite is met, and it is a normal pin, not a path
  install. Its only runtime dependency is `baseaicore>=0.4,<0.5`; SQLAlchemy arrives through its
  **`[sql]` extra**, which is deliberate (ADR-0050 decision 4: a consumer that only wants to add up
  tokens must not acquire an ORM to do it). **You need `loadledger[sql]`**, since you are mounting
  tables. Say so in the pin comment.
* **LoadLedger's public surface**, verified from the installed 0.1.0 source:
  * `loadledger` — `Ledger` (the protocol), `InMemoryLedger`, `Debit`, `LedgerEntry`,
    `BudgetCeiling`, `CeilingScope`, `CeilingVerdict`, `BalanceBook`, `PartialPricing`,
    `UnknownRun`, `InvalidCeiling`, `CurrencyMismatch`, `UnsupportedDialect`, `utc_day_key`,
    `utc_day_start`.
  * `loadledger.sql` — `SqlLedger`, `LedgerTables`, `mount_ledger_tables`, and
    `DEFAULT_TABLE_PREFIX = "ledger_"`. **The prefix is part of the mounted contract** — changing it
    in a host that has already migrated is a table rename, not a configuration change (ADR-0050).
  * The four methods you will use: `declare_run(run_id)`, `debit(Debit) -> LedgerEntry`,
    `would_exceed(...)`, `entries(...)`. Read their real signatures from
    `py/LoadLedger/src/loadledger/core.py:604–670` — do not infer them from this list.
* **PromptCadence already has most of this row's *vocabulary*, built at B4/C4.** This row is
  less greenfield than the row text implies — **confirm each of these before planning**:
  * `config.py` already ships `BudgetSettings` with `default_money_ceiling`,
    `default_token_ceiling`, `daily_money_ceiling`, `estimate_min_samples` (default 20),
    `partial_pricing` (`"floor"`/`"strict"`), `on_exhausted` (`approval`/`halt`),
    `on_daily_exhausted` (`window`/`approval`/`halt`), `window_wait_max_days` (default 3), and
    `projects: dict[str, ProjectBudget]`. `_validate_project_budgets` already refuses a project
    entry that binds neither ceiling.
  * `domain/trajectory.py` already has `TrajectoryState.AWAITING_WINDOW`, the parkable-state rule
    (only `planning` and `executing`) and a persisted `WindowPark` clock.
  * **So Phase 5 mostly wires behaviour to vocabulary that exists.** Where a field is present but
    unused, the work is to make it bind — not to redesign it. Where you find a field the plan needs
    and config does *not* have (check for a per-day **token** ceiling specifically), that is a real
    gap: add it in the established style and say so in the handoff.
* **Alembic history is at `0004_tool_call_records.py`**; yours is `0005_*`. The ADR-0050 mounting
  pattern is documented at `src/promptcadence/infrastructure/db/models.py:41` but **no package's
  tables are mounted yet** — LoadLedger is the **first**. That makes this the first-instance case in
  [model-assignment §3.1](docs/roadmap/model-assignment.md): get the mount + migration shape right,
  because Commissioner's mount at F2 and CutCtx's later will copy it.
* **`setspec` is not involved in this row.** PromptCadence still pins `setspec>=0.4,<0.5` pending
  E5's sweep, and nothing in Phase 5 imports `setspec`. **Do not move that pin here** — E5 owns it,
  F2 needs it. If E5's sweep has landed by the time you run, leave whatever it set alone.
* **Interpreter:** PromptCadence's venv is **Python 3.13.15**. There is **no python3.12** on this
  host. Name the interpreter and every exact invocation in the report (M5C-13).
* **Push auth is configured** (2026-09-04): `credential."https://github.com".helper =
  !/usr/bin/gh auth git-credential` in `~/.gitconfig`. **Probe with
  `GIT_TERMINAL_PROMPT=0 git push --dry-run origin main`, never `git ls-remote origin`** — these
  repos are public and `ls-remote` succeeds anonymously on a repo you cannot push to.

## 0.1 What ADR-0069 and ADR-0070 actually decided — the two you will get wrong if you skim

* **ADR-0069 — a partial price is a floor, and a money ceiling chooses how it binds.** A priced
  response the provider did not fully report accumulates the priced components as a **floor**.
  Under `partial_pricing = "floor"` (the default) "exceeded" is certain and "under budget" is not,
  so the brake can fire late by the unreported portion, and every verdict over that window carries
  the counts that make it a floor. Under `"strict"` a response that could not be fully priced
  **exceeds** the money ceiling — at pre-flight too — so the cap is never crossed. Either way the
  API, CLI and UI render a floor as **"at least"**, never as a bare figure.
* **ADR-0070 — an absent token class is zero only where the protocol cannot bill it.** The debit
  rebuilds `TokenUsage` from **all four** classes on LoadCoach's job document (row C6 put them on
  the wire). A class the protocol cannot bill is `0`; a class that is simply missing is not silently
  zeroed. Get this wrong and every money figure downstream is wrong.
* And the standing rule both rest on (**ADR-0030**): **store `TokenUsage` + `pricing_hash`, never a
  money figure as the primary fact.** Cost is re-derived. A schema that persists a computed amount
  as the source of truth fails review no matter how many tests pass.
* **ADR-0016:** a local model's cost is `UNSUPPORTED`, never `$0.00`. Unpriced local usage renders
  `—`, never `$0.00`, in API and CLI. That is acceptance criterion 1 for this phase.

## 0.2 `declare_run` — the ordering detail that makes the difference between working and not

The development plan is explicit and it is easy to get backwards: **`declare_run` fires at
trajectory creation, before plan approval, so that no pre-flight check ever meets `UnknownRun`.**

Wire it at the point a trajectory row is first persisted, not at the point the first turn runs. Then
write the test that proves it: a trajectory whose very first action is a `would_exceed` pre-flight
must not raise `UnknownRun`. That test is cheap and it is the one that catches a later refactor
moving the declaration.

## 0.3 Where the Opus/Sonnet seam actually falls

The row says "reconciliation is the Opus half; the rest is plumbing against spec'd maths". Refined
against what is actually in the tree:

**Opus (judgment, do not delegate):**
* Crash reconciliation idempotent by `source_ref` — §6 Gate C. The turn row is the source of truth;
  recovery re-derives the debit from it. Spend is never lost and never double-debited.
* The **first** package-table mount + its Alembic migration (§0's first-instance rule).
* The `partial_pricing` floor/strict semantics reaching pre-flight, not just post-hoc accounting.
* Resolving three simultaneously-active ceilings (per-trajectory, per-day, per-project) to "the most
  restrictive binds", and what each entry records as its balance-after against **each** active
  ceiling.

**Sonnet (transcription against a working example):**
* The historical estimator over `entries()` with source labels, once the first source-labelled path
  exists.
* `[budget] partial_pricing` and ceiling per-request overrides as config plumbing.
* `GET /ledger`, `GET /ledger/entries`, `promptcadence ledger show` — once one renders a floor as
  "at least", the rest are transcription.
* The `project` label refusal (`PROJECT_UNKNOWN`) and the `project:<name>` tag on every debit.

## 0.4 The one place to stop and ask

If you find that **LoadLedger 0.1.0's shipped API cannot express something Phase 5 requires** — a
ceiling scope that does not exist, a `would_exceed` signature that cannot answer a pre-flight
question the plan asks, an `entries()` filter the estimator needs — **stop and write it up before
working around it.** LoadLedger is a published package with its own spec and its own development
plan (Phase 2 landed at C3); a workaround inside PromptCadence that re-implements ledger logic is
exactly the "a package needed application responsibility" mistake CLAUDE.md names. A gap here is a
LoadLedger row, and it is better found in an hour than papered over in six.

---

## 1. Setup

```bash
source .venv/bin/activate && pip install -e ".[dev]"
```

Use the session scratchpad for every scratch database, config file and log — **never** the
repository, never `/tmp` directly, never the workspace root.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory, never the workspace root. Nothing at the root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated under `## [Unreleased]`,
  **one Conventional Commit per repository** (commit at each gate boundary, not at the end).
* `pytest-randomly` is on; a seed-only failure is a real bug — `-p no:randomly` isolates, never fixes.
* Coverage floor for an application is **85%**; `domain/` is held to the shared-package floor.
* House method: docstring-first (define behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names (`*_tokens`, `*_ms`), keyword-only for optionals and every boolean,
  `@dataclass(frozen=True, slots=True)` value objects, pydantic wire models, SQLAlchemy models never
  leaving the repository layer, `mypy --strict`, line length 100.
* Layering inside the app is `web → cli → services → domain`; `domain` imports no framework. Route
  handlers and CLI bodies call **one** service method and render. `.importlinter` encodes this;
  never weaken it to make an import work.
* Inject the clock. Every window, day-edge and expiry test in this row depends on it.
* **Never `git add -A`.** Stage named paths.
* Any workspace `docs/` edit is mirrored byte-identically into the component repo and **`cmp`-proved**.

## 3. Reading list, in this order

1. `docs/apps/promptcadence/development-plan.md` **Phase 5** — the work list, the test list, the
   acceptance criterion, the known risk and the deferral. It is the specification of this row.
2. `docs/apps/promptcadence/lifecycle.md` **§6** (budget: two ceilings, labelled estimates) — read
   the estimator ladder and the three-simultaneous-ceilings paragraph carefully; then **§8**
   T15–T17 for the `awaiting_window` park, resume and `window_wait_max_days` halt.
3. **ADR-0030** (cost and pricing), **ADR-0069** (floor/strict), **ADR-0070** (absent token class),
   **ADR-0016** (`UNSUPPORTED` is not zero), **ADR-0047** (= D-3: a tier is configuration and a
   model never sizes its own budget), **ADR-0050** (a package may ship tables, never a migration
   history).
4. `docs/packages/loadledger/spec.md` **§7** (scopes, entries, balance-after) and **§15** (the
   accepted budgets), plus `py/LoadLedger/src/loadledger/core.py` for the real signatures.
5. `docs/history/B2_HANDOFF.md` and `docs/history/C3_HANDOFF.md` — LoadLedger Phases 1 and 2 as built, including the
   `declare_run` decision and the window semantics that were confirmed there.
6. `docs/apps/promptcadence/spec.md` §20 criteria **1** and **6**, and §12's `[budget]` surface.
7. `docs/history/E4_HANDOFF.md` — what P4 left, and the shape of the live journey you will extend.

---

## 4. The shape of the work

Five gates, in order, one commit each. The ledger must be mounted and debiting before any ceiling
can bind, and reconciliation is proved last because it needs real debits to reconcile.

## 5. Gate A — mount the ledger

Add `loadledger[sql]>=0.1,<0.2` to `pyproject.toml` with a comment saying why the `[sql]` extra is
needed. Mount `mount_ledger_tables` into PromptCadence's metadata and write migration `0005_*`.

* Keep `DEFAULT_TABLE_PREFIX`. If you have a reason to change it, that reason must be in the
  changelog and the migration comment (§0).
* **This is the first package-table mount in this application.** Write it as the example the next
  two will copy: the mount in one named place, the migration generated against it, and a test that
  proves `alembic upgrade head` from empty produces exactly the mounted schema, and that
  `downgrade` is clean.
* Confirm the boundary: `lint-imports` must stay green, and `loadledger` is a capability package —
  it may not import PromptCadence, and PromptCadence's `domain/` may not import SQLAlchemy.

## 6. Gate B — debit, declare, and the pre-flight

* `declare_run` at trajectory creation, per §0.2, with the no-`UnknownRun` test.
* Debit per turn from LoadCoach's job document, rebuilding `TokenUsage` from **all four** classes
  per ADR-0070. Store `TokenUsage` + `pricing_hash`; never a money amount as the primary fact.
* `would_exceed` pre-flight per turn; `budget.debited` events.
* Exhaustion per ceiling: `on_exhausted` (`approval` | `halt`) for per-trajectory and per-project;
  `on_daily_exhausted` (`window` | `approval` | `halt`) for per-day, with the `awaiting_window` park
  and resume (T15–T17) and `window_wait_max_days`.
* The `project` request label: refused with `PROJECT_UNKNOWN` unless configured, **before anything
  is persisted**; `project:<name>` on every debit beside `tier:<name>`.
* Three ceilings may be active at once and **the most restrictive binds**; every entry records its
  balance-after against each active ceiling.

Tests the plan names explicitly, all with an injected clock: crossing each ceiling mid-trajectory;
a **token** ceiling binding a local tier where money cannot (the ADR-0030 case); the daily UTC
window; a trajectory parked on the per-day ceiling that resumes when the clock crosses UTC midnight
and the ceiling admits it, **stays** parked when another trajectory already spent the new day, and
halts after `window_wait_max_days`; a project ceiling binding across two trajectories that share the
label; an unknown project refused before persistence.

## 7. Gate C — partial pricing, floor and strict (ADR-0069)

`[budget] partial_pricing`, a per-request override like the ceilings, onto **every** money ceiling.

* Under `floor`: the trajectory continues and the balance shows **"at least"** — in the API, in the
  CLI, and wherever a figure is rendered. Never a bare number.
* Under `strict`: the next step is **refused at pre-flight**. Not detected afterwards — refused
  before the call.
* A local step trips neither, and its cost renders `—`, never `$0.00` (acceptance criterion 1).

## 8. Gate D — the estimator

The layered historical estimator over `entries()` (lifecycle §6): historical p80 per
`(tier, profile)` at ≥ `estimate_min_samples` (20) samples, else the configured per-tier default.
**Every estimate records its source label.** A model-generated number is never an input — D-3
/ ADR-0047 is categorical about it, and a test should assert that no path can feed one in.

Test the source selection **at** the sample threshold, both sides.

## 9. Gate E — crash reconciliation (the Opus half; the row's known risk)

Kill −9 between the LoadCoach response and the debit. Recovery reconciles from the persisted turn:
**spend is never lost and never double-debited**, idempotent by `source_ref`.

* The turn row is the source of truth; recovery re-derives the debit from it.
* Prove idempotence directly: run recovery twice and assert the ledger is unchanged the second time.
* Prove the lost case too: crash before the debit, recover, and assert the spend appears exactly once.
* This interacts with P4's lease recovery — check that a reconciled trajectory does not resume into a
  double debit, and say in the handoff which existing recovery test you extended.

## 10. Gate F — surfaces, then docs

* `GET /ledger`, `GET /ledger/entries`, `promptcadence ledger show`. Async at the HTTP edge only
  (ADR-0003); server-rendered HTML with progressive enhancement if a page is in scope (ADR-0020);
  SSE for anything streaming (ADR-0004), never WebSockets.
* Extend the live journey (`tests/live/test_loadcoach_journey.py`) so a real run shows debits and a
  running balance. It must still pass with **no GPU, no Ollama and no network** on the fake provider
  (spec §20 #10) — E6 is what makes that reliable.
* Then, in `/home/jpk/ai/suite/docs`, one commit: mark the **F1 row** done in
  `roadmap/outstanding-work.md` §1 in the house shape (`**Done 2026-09-0X** (`docs/history/F1_HANDOFF.md`;
  commits …)`), and record anything §0 got wrong. Mirror and `cmp`-prove any file PromptCadence
  copies.

---

## 11. Exit conditions — all of these, demonstrably

1. Spec §20 **#6** passes: crossing the money or token ceiling mid-trajectory halts (or pauses for
   approval) with the ledger showing every debit and the running balance that crossed.
2. Spec §20 **#1** acceptance still holds: unpriced local usage shows `—`, never `$0.00`, in API
   and CLI.
3. A token ceiling binds a local tier where a money ceiling cannot.
4. `floor` shows "at least" and continues; `strict` refuses at pre-flight.
5. A parked trajectory resumes on the UTC day edge, stays parked when the new day is already spent,
   and halts after `window_wait_max_days` — all on an injected clock.
6. Kill −9 between response and debit reconciles exactly once, proved by running recovery twice.
7. The estimator picks historical at ≥ 20 samples and the configured default below, with the source
   label recorded either way.
8. `alembic upgrade head` from empty produces the mounted schema; `downgrade` is clean.
9. Full gate green; the suite passes with no LoadCoach, no GPU and no network.
10. PromptCadence clean and pushed, CI green; docs clean; every mirrored file `cmp`-identical.

## 12. Closing duties

1. Full gate, interpreter and exact invocation named (M5C-13).
2. **`docs/history/F1_HANDOFF.md` at the workspace root**, house shape: gate results; the LoadLedger surface you
   actually used and anything §0's list got wrong; the mount + migration shape, called out as the
   example F2's Commissioner mount should copy; the reconciliation design and its idempotence proof;
   any config field you had to add; what F2 inherits and must not relitigate; anything this prompt
   said that turned out not to be true.
3. Push and confirm CI green. Record any **model deviation** from the scheduled split for
   [model-assignment §3.5](docs/roadmap/model-assignment.md), including which half ran on which model.

## 13. Stop rules

* **Do not start F2.** No egress evaluation, no Commissioner, no verification, no deviation
  handling, no `http_fetch`. If a budget path seems to need an egress verdict, that coupling is
  F2's and belongs in the handoff.
* **Do not move PromptCadence's `setspec` pin** — E5 owns it, F2 needs it.
* **Do not implement approval-gated ceiling raises** — explicitly deferred to P7 (G1). Exhaustion
  may *route to* `awaiting_approval`; granting the raise is not this row.
* **Do not persist a money figure as the primary fact** (ADR-0030), and do not coerce an
  `UNSUPPORTED` cost to zero (ADR-0016). Either one fails review with every test passing.
* **Do not re-implement ledger logic inside PromptCadence.** If LoadLedger cannot express it, §0.4.
* **Do not let a model-produced number size a budget** (D-3 / ADR-0047).
* Do not bump the version, tag, or publish. `promptcadence` reaches PyPI at G1.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a boundary.

## 14. If you finish with capacity left

Do **not** start F2 or G1. Read-only, in priority order: (a) an **F2 readiness note** — where an
egress verdict would attach to the turn path you just instrumented, and the `setspec`/Commissioner
pin problem recorded in F2's own kickoff §0.2; (b) confirm and record which of Phase 5's journeys
still depend on a free GPU, if any, after E6; (c) note any LoadLedger API friction you worked
around, as a candidate LoadLedger row.
