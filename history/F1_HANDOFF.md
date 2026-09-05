# F1 — PromptCadence Phase 5: Budget

**Row:** F1 of `docs/roadmap/outstanding-work.md` §1.
**Date:** 2026-09-04.
**Model:** run **single-session at Opus 5 · high**. The row scheduled a split (Opus core / Sonnet
edges); §11 below records why the split was not taken and what that means for
`docs/roadmap/model-assignment.md` §3.5.
**Repositories:** `PromptCadence` (7 commits), `docs` (1 commit).
**Ships:** nothing. `promptcadence` stays off PyPI until G1. No version bump, no tag.
**Interpreter:** `/home/jpk/ai/suite/PromptCadence/.venv/bin/python`, **Python 3.13.15**. There is
no python3.12 on this host; the 3.12 leg is CI's.

---

## 1. Gate results

Every gate ran green before its commit; the numbers below are the final run.

```text
$ source .venv/bin/activate
$ python -V                                   # Python 3.13.15
$ ruff format --check .                       # 101 files already formatted
$ ruff check .                                # no issues
$ mypy src tests                              # Success: no issues found in 98 source files
$ lint-imports                                # Contracts: 5 kept, 0 broken
$ pytest -m "not live and not performance" -q # 875 passed, 2 skipped, 2 deselected
$ pytest -q --cov --cov-report=term-missing   # TOTAL 92%  (floor 85%)
```

Per-module coverage of what this row added: `services/budget.py` 89 %, `services/pricing.py` 94 %,
`services/estimates.py` 93 %, `web/routes/ledger.py` 100 %, `services/loop.py` 85 %.

The two skips are the PostgreSQL-marked migration tests: **there is no PostgreSQL server on this
host**, so migration `0005` is proved on SQLite here and on both dialects in CI. That matters more
than usual this time — see §5's `BigInteger` fix, which is a defect SQLite structurally cannot
catch.

### Commits

| Repo | Commit | Gate |
|---|---|---|
| PromptCadence | `f84ddf2` | A — mount the ledger, migration `0005` |
| PromptCadence | `f6fdf38` | B — declare, debit, pre-flight, exhaustion, the window |
| PromptCadence | `0dc15b1` | C — floor and strict at pre-flight; the renderers |
| PromptCadence | `399803a` | D — the estimator's ladder and its input rule |
| PromptCadence | `bd60bc3` | E — crash reconciliation, idempotent by `source_ref` |
| PromptCadence | `c7fda2d` | F — `GET /ledger`, `/ledger/entries`, `ledger show`, live journey |
| PromptCadence | `ca0f6a7` | F — the mirrored docs (`cmp`-proved byte-identical) |
| PromptCadence | `7a17f2c` | F — the bound-direction fix the demonstration found (§6) |
| docs | `82e75f3` | spec §12 + §7.2, lifecycle §6, the F1 row |

**Nothing is pushed.** The standing instruction of 2026-09-04 is *commit as usual, never run
`git push` in any suite repo*, and it postdates this row's kickoff §12. Both trees are clean and
level with their local `main`; pushing and confirming CI is the operator's.

---

## 2. The LoadLedger surface actually used, and what §0's list got wrong

Used, all from `loadledger 0.1.0` installed as `loadledger[sql]>=0.1,<0.2`:

* `loadledger` — `BudgetCeiling`, `CeilingScope`, `CeilingVerdict`, `Debit`, `LedgerEntry`,
  `PartialPricing`, `CurrencyMismatch`, `UnknownRun`, `utc_day_start`, `utc_day_key`.
* `loadledger.sql` — `SqlLedger`, `mount_ledger_tables`, `DEFAULT_TABLE_PREFIX`, `LedgerTables`.
* Methods: `declare_run`, `debit`, `would_exceed`, `remaining`, `entries`.

§0's list was accurate. Four things it did not say that matter:

1. **`remaining` is used and the row's list omitted it.** It is what a *balance report* needs;
   `would_exceed` answers a different question (what would happen if this step ran) and using it
   for a dashboard would report a position nobody is standing in.
2. **`debit` is not idempotent and nothing in the package makes it so.** There is no unique
   constraint on `source_ref` — the entries table is keyed on `entry_id` alone. Idempotence by
   `source_ref` is entirely PromptCadence's, implemented as
   `BudgetService.debited_turn_ids(trajectory_id)` read before every debit. This is correct
   division (refusing work is the caller's policy, per the package's own docstrings) but it is
   **not free**, and F2's Commissioner mount will have the same shape of problem if it needs
   at-most-once semantics.
3. **`SqlLedger` accepts a savepoint-joined session** exactly as its docstring promises, and this
   build relies on it: `BudgetService.ledger(session=...)` returns a ledger whose writes land
   inside the caller's transaction, so a debit and its `budget.debited` event commit together
   (ADR-0044 applied to money). Verified working on SQLite under both journal modes the suite runs.
4. **An entry read back carries `debit.cost is None`.** The package documents this; the
   consequence for us is in §4's estimator note.

---

## 3. The mount and the migration — the example F2 should copy

This is the **first** package-table mount in the application, so the shape is deliberate.

**`src/promptcadence/infrastructure/db/models.py`, at the bottom of the module:**

```python
LEDGER_TABLES: Final = mount_ledger_tables(Base.metadata)
```

Three properties, each load-bearing, and Commissioner's `egress_decisions` mount at F2 should
reproduce all three:

* **Unconditional, at module import, in the model package.** Not in a service, not behind a flag,
  not lazily. Autogenerate and `MigrationRunner.check_parity` both read the metadata *as it is when
  they inspect it*; a mount performed later produces a revision that **drops** the package's
  tables. That is the pattern's named failure mode.
* **The package's default prefix, kept.** `ledger_` is contract, not configuration: changing it in
  a host that has migrated is a table rename.
* **Nothing joins to a mounted table.** Reads go through `SqlLedger`. The one exception in this
  build is `tests/`, which selects from `models.LEDGER_TABLES.runs` and `.entries` to assert the
  mount and to simulate a pre-P5 database — a test asserting the shape, never application code
  querying it.

**Migration `0005_ledger_tables.py`** was **autogenerated against the mount, not transcribed** from
LoadLedger's source. `tests/integration/test_migrations.py` proves three things:
`upgrade head` from empty produces exactly the mounted shapes (column set and nullability compared
against `LEDGER_TABLES.all_tables`), `downgrade` to `0004` removes them and nothing else, and
`check_parity` matches on both dialects. Copy that test too; it is what would catch a hand-edited
revision drifting from the mount.

---

## 4. Reconciliation: the design and its idempotence proof

**Ordering.** The debit is written **before** the turn row, in its own transaction:

```text
LoadCoach response  →  [tx1: ledger debit + budget.debited]  →  [tx2: turn row + turn.completed]
```

Chosen after considering the reverse. Debit-last leaves a window in which spend is lost; debit-first
leaves a window in which spend is recorded for a turn that has no row, which is *recoverable* (P4's
existing reconciliation reads the LoadCoach job document and re-records the turn) and never a double
debit, because the debit is guarded by `source_ref`. Losing spend is the failure that cannot be
repaired from the record; recording it early can.

**`LoopController.reconcile_debits(trajectory_id)`** covers the other direction and runs at the head
of every `reconcile()` pass. It reads PromptCadence's own `turns` rows — the turn row is the source
of truth — and debits every assistant turn whose id is not already in `debited_turn_ids`. The row
carries everything the debit and a later re-costing need: four token classes, the tier, the
answering model's canonical id, and `created_at` (which is what the cost is priced *at*, so
re-costing history reproduces the same figure).

`_usage_of(row)` is the one function to read carefully: a `NULL` column is a class LoadCoach never
reported and stays `UNSUPPORTED`; a stored `0` is a class reported as unused. Reading `NULL` as `0`
would make every unreported class look measured and every money figure downstream wrong in the same
direction (ADR-0070).

**The proof.** `tests/integration/test_recovery.py`:

* `test_kill_minus_nine_after_the_response_reconciles_the_completed_job_without_a_second_one` —
  **extended, not added.** This is the existing real `kill -9` test (a child process that SIGKILLs
  itself the instant `generate()` returns, which is exactly the crash window). It now asserts the
  spend lands **exactly once**, keyed by the reconciled turn's own id and not a fresh one, and that
  a second recovery pass writes nothing.
* `test_reconcile_debits_re_derives_a_missing_debit_from_the_turn_row_and_only_once` — **new.**
  Deletes the ledger rows under a completed trajectory (exactly the state a pre-P5 database is in
  after `0005`), reconciles, and asserts one debit re-derived from the turn row; reconciles again
  and asserts `0` written and every entry byte-identical by `as_canonical()`.

**Interaction with P4's lease recovery:** a reconciled trajectory does not resume into a double
debit, because `reconcile()` calls `reconcile_debits` *before* it decides anything, and
`_record_turn`'s own debit is guarded by the same set. The in-flight recovery test's event sequence
gained `budget.debited` between `turn.started` and `turn.completed`, which is the visible shape of
the ordering above.

---

## 5. Config fields added, and the one the kickoff asked for that does not exist

**Added:**

| Field | Where | Why |
|---|---|---|
| `[tiers.<name>] default_step_input_tokens` | `config.Tier` | The estimator's `configured_default` rung. Lifecycle §6 names it; configuration had no field for it. |
| `[tiers.<name>] default_step_output_tokens` | `config.Tier` | Two numbers, not one total: the classes price differently and a fixed ratio would be a magic number between an operator and the cap that binds them. |
| `budget.partial_pricing` per request | `TrajectorySubmission`, `BudgetBody`, column `trajectories.budget_partial_pricing` | ADR-0069's rule is a property of the piece of work. `NULL` means "the configured default", which is not the same as either value pinned. |
| `trajectories.window_parked_from` / `window_next_edge_at` / `window_days_waited` | migration `0005` | `domain.trajectory.WindowWait` field for field. The domain has carried the value object since P2 with nowhere to persist it. |

**Not added: `daily_token_ceiling`.** Kickoff §0 told this session to look for one and to treat its
absence as a real gap. It is not one. Spec §11.5 and lifecycle §6 make the per-day ceiling
**money-only by design** — "local work is unpriced and never counts against it", which is precisely
what lets any amount of work run while only so much is *spent* in a day. A per-day token cap would
stop the local half of an installation at midnight for something nobody budgeted. The universal
brake is the per-trajectory token ceiling. Recorded in spec §12 as a comment so the next reader does
not re-open it.

**Fixed, not added:** `trajectories.budget_money_nanos` and `budget_token_ceiling` were `Integer`.
`Money` is whole nanos, so the shipped `$5.00` default is 5 000 000 000 — past a 4-byte integer's
2 147 483 647. On PostgreSQL every trajectory carrying a money ceiling above **$2.14** would have
failed to insert; SQLite's dynamic typing stores it regardless, so no SQLite-only suite could have
found it. Widened to `BigInteger` in `0005`. **LoadLedger's own rule — every accumulating integer
is a `BigInteger` — should be applied to Commissioner's columns at F2 as a matter of course.**

---

## 6. Decisions this row had to make, which the documents left open

Each is now in `docs/apps/promptcadence/lifecycle.md` §6 or `spec.md` §12. None needed a new ADR:
ADR-0047 §3, ADR-0069 and ADR-0030 decide the substance, and these are their application.

1. **A money ceiling binds a step only when that step's usage is priced.** ADR-0047 §3 says "money
   ceilings bind priced usage"; LoadLedger correctly reports *every* ceiling's verdict and leaves
   the policy to the caller. So `BudgetPosition.binding` skips a money-only ceiling for an unpriced
   step, and for a ceiling binding both, only the token half can refuse one. **Without this a
   shared per-day money cap exhausted by one remote trajectory would halt every local trajectory in
   the installation** — the opposite of what the per-day ceiling is for. A *balance report*
   (`GET /ledger`) makes no such distinction: it says what the ceilings say.
2. **T16 asks the pre-flight's question.** Lifecycle §8.2's guard is "the per-day ceiling now
   **admits the plan or step**", not "is the ceiling exceeded". A day whose headroom is smaller than
   the next step's estimate still refuses. The cheaper question wakes a parked trajectory on every
   day edge only for its pre-flight to park it again — one park per day, forever, with the event
   stream to match. `LoopController._day_refuses` runs the same estimate the pre-flight runs.
3. **A pre-flight estimate is priced against the tier's worst case.** Which model answers is
   LoadCoach's choice and is not known until it has answered, so an estimate cannot name one price
   record. `price_estimate` costs it against every record the tier still claims and takes the
   largest — the only rule that cannot *under*-state a budget, and under-stating is the failure
   that matters. An estimate that could not be totalled sorts as the largest, deliberately.
4. **The pricing-file format.** PromptCadence is the suite's first consumer of
   `baseaicore.ModelPricing`; nothing anywhere defined a file for it. JSON with a `records` array
   (ADR-0019), rates as **decimal strings** (a JSON number is a float, and a price that arrived as
   a float has already lost the value the integer arithmetic protects), an omitted rate meaning
   "not stated" rather than free. A record stating an `artifact_digest` matches only those weights;
   one stating none matches the model under any digest, so a retag stays priced. Documented in
   spec §12 and asserted in `tests/unit/test_pricing.py`.
5. **Render direction.** Found by *running* the CLI, not by reading it: `ledger show` printed
   "at least 20 USD left". The cap less a spend that is a floor is an **upper** bound on what
   remains, so `render_remaining_money`/`render_remaining_tokens` say "at most" and
   `render_money`/`render_tokens` keep "at least" for a spend. Getting this backwards reassures in
   exactly the case where less headroom may remain than the number says.
6. **A refused pre-flight's cause is about the pre-flight.** Also found by running it: the cause
   read "the tokens cap is spent" on a trajectory that had spent nothing — a ceiling too small to
   admit its first step. Every figure in that verdict is `would_exceed`'s *prospective* one,
   including its debit counts, so the cause now says "the tokens cap cannot admit it — counting
   this step the cap is over by 1 120".

---

## 7. The §0.4 finding: one LoadLedger row

**LoadLedger reports a balance only *through a ceiling* and *for a named run*.** There is no
`balances(scope, window_key)` read. Two consequences, neither worked around:

* **A scope with no ceiling has no balance to show.** Spec §7.2's `ledger show --scope tier` asks
  for per-tier spend, and lifecycle §6 says no tier ceiling is configured. The two ways to answer
  are summing `entries()` in the application — ledger arithmetic exactly where ADR-0050 forbids it
  — or inventing an unreachable ceiling to read a number through, which puts a magic figure in the
  record. **So `--scope tier` reports debit *counts* and says why**, and spec §12/lifecycle §6 now
  record that a tier has a history and not a balance.
* **`GET /ledger` must name an arbitrary known run as its reference.** `TrajectoryService.
  most_recent_id()` supplies it. This is *sound* — a `per_day` or `per_tag` verdict's window is
  ledger-wide, so the answer is identical whichever known run is named — but it is a signature
  working around a missing read, and it degrades to "the configured caps with nothing spent" on an
  empty ledger.

**Proposed LoadLedger row:** a `balances(*, scope, window_key)` (or `position(ceilings, *, at)`)
read that takes no `run_id` and returns the accumulated balance and the three honesty counts for a
window. It needs no new storage — `{prefix}balances` and `{prefix}balance_money` are already keyed
`(scope, window_key)` — and it removes both workarounds. Nothing was re-implemented inside
PromptCadence, so the row is optional rather than blocking.

---

## 8. Things this row's prompt said that turned out not to be true

1. **"check for a per-day token ceiling specifically … that is a real gap: add it"** — it is not.
   See §5.
2. **A remote tier cannot run in this build.** `TierPolicy.availability` returns
   `loadcoach_has_no_remote_provider` for every remote tier until LC-E1, and
   `LoopController._tier_policy` hardcodes `loadcoach_has_remote_provider=False`. So **no test can
   reach a money ceiling through the loop by the intended route.** The money, floor/strict and
   window tests price the *local* tier through a hand-built `PricingCatalog` — one visible fiction,
   named and justified in `_priced_catalog`'s docstring, with
   `test_from_settings_never_prices_a_local_tier` holding the shipped rule (ADR-0016: a local
   model's cost is `UNSUPPORTED`, and `PricingCatalog.from_settings` refuses to price a local tier
   whatever it names). **When LC-E1 lands, those tests should move onto a real remote tier.**
3. **"the reconciliation is the Opus half; the rest is plumbing"** — see §11.
4. §0 said "no package's tables are mounted yet — LoadLedger is the **first**". Correct, and it is
   also the first time `ModelPricing` is consumed anywhere in the suite (§6.4).

---

## 9. What F2 inherits and must not relitigate

* **The mount shape** (§3). Copy it for `egress_decisions`, including the upgrade-from-empty test
  and the `BigInteger` rule for any accumulating column.
* **The debit-before-turn-row ordering and `reconcile_debits`** (§4). An egress decision recorded
  alongside a turn faces the same two crash windows and the same choice; the reasoning is in §4.
* **`render_money` / `render_remaining_money` / `render_tokens` / `render_remaining_tokens`** are
  the only places a figure becomes text. A new surface calls them; it does not format money.
* **Money ceilings bind priced usage** (§6.1). An egress verdict that wants to consult a budget
  consults `BudgetPosition`, which already knows this.
* **`setspec` is still pinned `>=0.4,<0.5`.** Untouched, as instructed. Nothing in P5 imports
  `setspec`.
* **Where an egress verdict attaches.** `LoopController._turn` now reads:
  pre-flight → `turn.started` → `generate` → `_record_turn`(debit, then the turn row). An egress
  decision is evaluated **before `generate`**, beside the pre-flight, because both answer "may this
  call happen" and both must refuse before anything leaves. `_preflight` returns
  `TrajectoryState | None` and is the model for that: `None` means proceed. Nothing in the budget
  path needs an egress verdict, so the coupling is one-directional and F2 owns it entirely.

---

## 10. Exit conditions

| # | Condition | Where |
|---|---|---|
| 1 | §20 #6: crossing a ceiling mid-trajectory halts (or pauses), ledger showing every debit and the balance that crossed | `test_crossing_the_token_ceiling_mid_trajectory_halts_with_every_debit_on_the_ledger`, `test_exhaustion_under_the_approval_policy_parks_on_one_pending_request`; demonstrated live in §12 |
| 2 | §20 #1: unpriced local usage shows `—`, never `$0.00`, in API and CLI | `test_unpriced_local_usage_renders_an_em_dash_and_never_a_zero`, `test_an_unpriced_position_renders_an_em_dash_and_never_a_zero` |
| 3 | A token ceiling binds a local tier where a money ceiling cannot | `test_a_token_ceiling_binds_a_local_tier_where_a_money_ceiling_cannot` |
| 4 | `floor` shows "at least" and continues; `strict` refuses at pre-flight | `test_under_floor_…_reads_at_least`, `test_under_strict_the_next_step_is_refused_at_preflight_not_detected_afterwards` (asserts LoadCoach was never asked a second time) |
| 5 | Parked resumes on the day edge, stays parked when the new day is spent, halts after `window_wait_max_days` — all on an injected clock | three tests in `tests/integration/test_budget.py`, all on `Clock` |
| 6 | Kill −9 between response and debit reconciles exactly once, proved by running recovery twice | §4 |
| 7 | The estimator picks historical at ≥ 20 samples and the default below, source recorded either way | `test_the_source_flips_exactly_at_the_sample_threshold`, parametrised on 19 and 20 |
| 8 | `alembic upgrade head` from empty produces the mounted schema; `downgrade` is clean | `test_upgrade_from_empty_creates_exactly_the_mounted_ledger_schema`, `test_downgrade_removes_the_mounted_ledger_tables` |
| 9 | Full gate green; the suite passes with no LoadCoach, no GPU and no network | §1; and `pytest -m live` passed against a **fake-provider** LoadCoach (§12) |
| 10 | Clean, pushed, CI green; docs clean; mirrors `cmp`-identical | Clean and `cmp`-identical. **Not pushed** — §1. |

---

## 11. Model deviation — resolved by decision, 2026-09-04

> **Closed after this handoff was written.** The operator's answer was *"for all the splits between
> models, just use the stronger model"*. Splits are abolished suite-wide: `model-assignment.md`
> §3.5 is now the rule and records this row as its evidence, §3.6 restates the distribution with
> the split phases folded into the stronger model, and the seven rows that named two models now
> name one (F1, H1, I1, I2 in `outstanding-work.md`; FreeWeight P10A/P13/P14, PromptCadence
> P5/P8/P9 and ModelRack P8 in `model-assignment.md` §2). What follows is the evidence as observed.

**Scheduled:** split — Opus 5 · high for the reconciliation core, Sonnet 5 · high for the edges
(estimator, config plumbing, surfaces, project label).
**Run:** the whole row on **Opus 5 · high**, single session, as the kickoff permitted.

**Why, and it is a finding rather than a preference.** Three of the four "Sonnet, transcription
against a working example" items turned out to depend on decisions the Opus half had not yet made,
and could not have been transcribed:

* The **estimator** could not be written against `entries()` until it was settled that an entry
  carries no money (ADR-0030 rule 1) and the historical estimate is therefore a *usage* estimate
  priced through the tier — plus the worst-case rule (§6.3) for an estimate with no model identity.
* The **surfaces** could not be written until the §0.4 gap was found: `--scope tier` has no balance
  to render, and `GET /ledger` needs a reference run. Both are shaped by a package limitation, not
  by a template.
* `partial_pricing` **as config plumbing** was accurate, but its *pre-flight* half is not, and the
  two are one field.

The one item that was genuinely transcription — the `project` label refusal — was **already built
at B4** and needed only `declare_run` wired beside it.

**Recommendation, and what was decided:** this row's split assumed the edges follow the core. They
interleave. The recommendation was to draw a future seam at a *test* boundary — one model commits
the behaviour, another writes the surfaces against it afterwards — rather than at a component
boundary inside one gate. The operator went further and removed the category: a phase gets one
model, the stronger of any pair, and work that genuinely has two halves with a seam between them is
written as two rows rather than as one row with two models.

---

## 12. The demonstration

LoadCoach 1.0.0 started on `provider.kind = fake` (E6's fix is what makes this need no VRAM), a
scratch data directory, no GPU, no Ollama, no network:

```text
$ pytest -m live -q            # 2 passed, 877 deselected
```

The live journey now asserts the debits and the running balance a real run leaves behind. Then,
through the served application and the CLI:

```text
$ promptcadence run "Reply with the single word: ready." --bypass-planning --follow
[5] budget.debited
[6] turn.completed — complete
[7] trajectory.completed

$ promptcadence ledger show
UTC day 2026-09-04  (as of 2026-09-04T20:12:00.187Z)
day                      money         at most 20 USD left   tokens              — left

$ promptcadence ledger show --scope tier
local_fast               1 debit(s) recorded
local_large              0 debit(s) recorded
no tier ceiling is configured, so a tier has a history and not a balance
```

`— left` on the day's token column is a ceiling that binds no tokens, not a zero. And the exhaustion
branch of §20 #6, on a 4 000-token ceiling the shipped 5 120-token default estimate cannot fit:

```text
state   awaiting_approval
cause   the trajectory budget refuses the next step on tier local_fast: the tokens cap cannot
        admit it — counting this step the cap is over by 1120; the money in this window is a floor
        over 1 debit(s) that could not be fully priced — this step included — so what is left is
        at most 5 USD; the estimate was 5120 tokens (source configured_default, 0 samples)
```

Both demo servers were stopped afterwards; the scratch databases live in the session scratchpad and
nothing was written to the repository or the workspace root except this file.


---

## 13. Decisions taken after this row, 2026-09-04

Three questions were put to the operator at the end of the session. All three are implemented; the
trees named in §1 have one further commit each.

1. **The pricing-file format is now suite-wide.** `docs/adr/0072-the-model-pricing-record-file.md`
   (Accepted) fixes the format, the "not stated is not free" rule, the digest-matching asymmetry
   and the resolution order, extending ADR-0030. PromptCadence's spec §12 now references it instead
   of restating it. The argument is the `pricing_hash`: it is only a join if every application
   hashes the same object.
2. **The §7 LoadLedger gap is scheduled.** New row **F4** — LoadLedger P3 → 0.2.0, Sonnet 5 · high,
   runs after F1 — adds `balances(*, scope, window_key)` with no `run_id` and no ceiling, plus the
   PromptCadence follow-up that drops the reference-run workaround and makes `--scope tier` report
   spend. LoadLedger's own development plan gains Phase 3. A **soft** ordering edge F4 → G1 was
   added to `outstanding-work.md` §3.
3. **Splits are abolished.** See §11 above.

**Commits:** docs `c18920a`, PromptCadence `aa255c6`, LoadLedger `c621ea2`. All three trees clean,
every mirror `cmp`-identical, PromptCadence's full gate re-run green (875 passed). **Still nothing
pushed.**
