# Kickoff — J1: IdeaPress mounts LoadLedger and Commissioner

**Row:** J1 (Sonnet 5 · high) of [`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md)
§1 — M13's adoption phases IP-A1 **and** IP-A2, merged into one row on 2026-09-07.
**Component:** `/home/jpk/ai/suite/IdeaPress` — `services/`, `infrastructure/db/`, `config.py`,
`web/templates/workspace/index.html`, and `docs/`.
**Adopts:** `loadledger 0.2.0` and `commissioner 0.1.1`, both published on PyPI.
**Ships:** nothing on its own. **Cut no release here** — see ground truth 1 and D7.

**Two adoptions, proved separately, in order: LoadLedger first, then Commissioner.** They share one
page, one migration chain, one `pyproject` move and one gate, which is why they are one row; they
do not share an exit condition. Roadmap §6.1 and §6.2 are unchanged and are answered one at a time.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.**
  `/home/jpk/ai/suite/IdeaPress`, its own `.venv/bin/python` (CPython 3.13.15). `pip install -e
  ".[dev]"` if anything is missing.
* **House method:** docstring-first, `from __future__ import annotations`, units in every numeric
  name (`*_tokens`, `*_nanos`, `*_ms`), keyword-only for anything optional or boolean, injected
  clocks and session factories, line length 100, `mypy --strict`, no `# type: ignore` without a
  trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, plus `pytest --cov` at or above the **85 %**
  floor (application). **Name the interpreter and the exact invocation in the handoff** (M5C-13).
* **Documentation is mirrored.** Edit the workspace copy under `/home/jpk/ai/suite/WeightRoom/docs/` first,
  then copy byte-identically into `IdeaPress/docs/apps/ideapress/`, and verify with `cmp`.
* **Do not push, do not tag, do not publish.** Standing instruction of 2026-09-04.
* **Run `git status --short` at the start and at the end** in every repository you touch.

---

## Ground truth, already checked on 2026-09-07 — do not spend the session rediscovering it

1. **IdeaPress is already at `1.1.0`, tagged and published** (`30ba52f`, 2026-09-05, the H3
   adapter-pin work; `v1.1.0` on PyPI). The roadmap's "IdeaPress 1.1" prose for M13 predates that
   release. This row therefore **prepares no release**: J2 follows it and cuts `1.2.0` carrying
   both rows' work. Correct the J1 and J2 rows in `outstanding-work.md` to say so. `main` is one
   commit past the release (`1ef7663`), tree clean.
2. **PromptCadence has already done this mount, twice, and its code is the pattern to copy.**
   `PromptCadence/src/promptcadence/infrastructure/db/models.py:737` (`LEDGER_TABLES`) and `:758`
   (`EGRESS_TABLES`) — both unconditional, at module import, with the docstring explaining *why*
   a conditional mount makes autogenerate emit a `DROP`. Migrations `0005_ledger_tables.py` and
   `0006_egress_decisions.py`. Services: `services/budget.py` (979 lines), `services/egress.py`
   (373), `services/pricing.py` (368). **Read those three before writing anything.** IdeaPress's
   versions are smaller — no tiers, no approvals, no trajectories — but the shape is settled.
3. **IdeaPress has no money anywhere today.** `AttemptRow` stores `input_tokens`,
   `output_tokens`, `thinking_tokens` and timings (`models.py:301`), and `unit_reports.py:157` and
   `stage_reports.py:83` render the token counts. There is **no cost code, no pricing, no
   accumulation** — so "delete the in-app equivalent" (roadmap §6.1) has **almost nothing to
   delete**. Say so plainly rather than inventing a deletion. This is decision **D2**.
4. **The egress flag is exactly one expression**, at
   [`services/workspace.py:209`](../../IdeaPress/src/ideapress/services/workspace.py):
   `"egress": runtime.settings.inference.mode != "ollama" and _is_remote(runtime)`, with
   `_is_remote` reading the configured base URL's host at `:216`. It renders at
   `web/templates/workspace/index.html:28` as "leaves this machine" / "stays on this machine".
   That flag, and `_is_remote`, are what IP-A2 replaces with a query over recorded rows.
5. **The classification and the opt-in already exist.** `inference.data_classification`
   (`config.py:248`, default `"public"`, validated against `baseaicore.DataClassification`) and
   `providers.allow_remote` (`config.py:504`, default `False`, enforced at `:739`). Commissioner
   needs a **ceiling per target**, which IdeaPress does not have — that is decision **D4**.
6. **Migration chain head is `0006_attempt_adapter_subject`.** Two new revisions land on it. The
   suite's SQLite migrations run with foreign keys off (H2/I1 finding) — follow the existing
   `env.py`; do not re-derive it.
7. **No pin moves, and no `ci.lock`.** `loadledger` needs `baseaicore>=0.4,<0.5`; `commissioner`
   needs `baseaicore>=0.4.1,<0.5` and `setspec>=0.5,<0.7`. IdeaPress pins `baseaicore>=0.4.1,<0.5`
   and `setspec>=0.4,<0.7`, and its venv resolves `baseaicore 0.4.1` / `setspec 0.6.0` — satisfied.
   Both packages need their `[sql]` extra: `loadledger[sql]>=0.2,<0.3`,
   `commissioner[sql]>=0.1.1,<0.2`. IdeaPress has **no `ci.lock`**; do not invent one. See D6 on
   the `setspec` floor.
8. **Next free ADR number is `0101`** — unless J2 ran first and took it; check before writing.
9. **J2 shares no file with this row** and may be running in another session (it touches
   `domain/context_assembly.py`, `services/project_review.py`, `services/unit_loop.py`,
   `services/review_loop.py`). If it is: do not run a blanket `git checkout --` in `docs/`, and
   expect to meet its commits in `pyproject.toml` and `CHANGELOG.md` — those two are the only
   files you both touch.

## Reading list

1. [`roadmap/promptcadence-roadmap.md`](../../roadmap/promptcadence-roadmap.md) §6.1 + §6.2 — the two
   exit conditions, verbatim.
2. [`packages/loadledger/spec.md`](../../packages/loadledger/spec.md) **§2** (the three scopes and
   what a window spans), **§7** (`Debit`, `CeilingVerdict`, `WindowBalance`, `balances()`,
   `position()`, `declare_run()`) and **§21** (the IdeaPress adoption's own note).
3. [`packages/commissioner/spec.md`](../../packages/commissioner/spec.md) §7 (`EgressTarget`,
   `EgressRequest`, `OrderedClassificationPolicy`, `SqlEgressLedger`), §10 (the one table) and
   §11 (contracts 1, 2 and 6).
4. [ADR-0030](../../adr/0030-model-cost-and-pricing.md) (cost is re-derived, never stored),
   [ADR-0069](../../adr/0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md)
   (floor vs strict), [ADR-0050](../../adr/0050-a-package-may-ship-tables-never-a-migration-history.md)
   (mount, never join), [ADR-0054](../../adr/0054-commissioner-records-egress-it-does-not-enforce-it.md)
   (record, do not enforce — and its bullet naming this row),
   [ADR-0072](../../adr/0072-the-model-pricing-record-file.md) (the pricing file format),
   [ADR-0073](../../adr/0073-egress-is-decided-on-configuration-before-availability.md) (decide on
   configuration, before availability).
5. `IdeaPress/src/ideapress/services/stages.py:115` `record_attempt()` — the one funnel every
   stage attempt passes through, and therefore the debit site.
6. [`apps/ideapress/risks.md`](../../apps/ideapress/risks.md) risk S4, and
   [`apps/ideapress/data-model.md`](../../apps/ideapress/data-model.md) — the two documents this row
   edits besides `workflows.md`.

## Part 1 — LoadLedger (IP-A1)

**Exit (§6.1):** a project page answers "what did this cost?" honestly, and ADR-0030's context
sentence is shipped behaviour.

**The debit site is `record_attempt()`**, which every stage already routes through with a
`StageResult` carrying usage. One debit per attempt, `source_ref` = the attempt id, `run_id` =
decision D1, tags = decision D1.

**Honesty is the whole feature.** Ollama runs are unpriced: `Debit.cost=None`, `unpriced=True`, no
money balance touched, and the UI renders `—` **with the reason**, never `0`. A partially priced
estimate makes the money figure a floor, rendered "at least" (ADR-0069, `CeilingVerdict`'s three
counts). A `0` on that page would be the exact defect ADR-0016 exists to prevent.

### D1 — the two scopes, and what `run_id` means

LoadLedger's `run_id` is the caller's run identity, and IdeaPress has three candidates: the stage
run, the unit, the project. The row wants **per-unit** and **per-project** figures.
**Recommendation:** `run_id = the unit id` (so `PER_RUN` is the per-output ceiling the row names),
and `tags = ("project:<project_id>", "stage:<stage>", "backend:<name>")` with a `PER_TAG` ceiling
on `project:<id>` — which never resets, which is what "lifetime project cost" means. A stage
attempt with no unit (`plan`, `project_review`) has no unit id: **decide what it debits** — the
recommendation is `run_id = f"project:{project_id}"` for those, so nothing is silently undebited,
and say it in the handoff. `declare_run()` at unit creation, so a per-unit view before the first
attempt reads a real empty window rather than `UnknownRun`.

### D2 — what is deleted

Ground truth 3: there is no in-app cost accumulator to delete. **Recommendation:** state that in
the handoff and in the row, delete nothing, and do not manufacture a deletion by routing the
existing per-attempt token counts through the ledger *instead of* the `attempts` columns — those
columns are provenance (workflows §8) and the ledger is an accumulation; both are correct and they
are not duplicates. If you find a real accumulator I missed, delete it and name it.

### D3 — where the pricing comes from

ADR-0030 gives acquisition to applications, and PromptCadence's `services/pricing.py` +
ADR-0072 already define the file format. **Recommendation:** a `[pricing] file = "…"` key
(optional; absent ⇒ everything is unpriced and says so), loaded at startup, parsed by **a copy of
PromptCadence's loader adapted to IdeaPress's config**, not by importing PromptCadence — an
application never imports another application, not even for a loader. If the copy is more than
~120 lines, argue in the handoff whether the loader belongs in a package (that is a *finding*, not
work for this row). Local Ollama runs need no pricing file and must work with none present.

### D4 — the ceilings, and what happens when one binds

`PER_RUN` (per output) and `PER_TAG` (`project:<id>`, lifetime) from configuration — new keys under
`[workflow]` or a new `[budget]` section; pick one and say why. **The harder half:** LoadLedger
decides nothing (spec §3), so IdeaPress must. **Recommendation:** a bound ceiling **pauses the
unit** with a reason, reusing the existing pause path (`pause_guidance`,
`services/workspace.py:37`, which already has a documented remedy shape) rather than raising —
IdeaPress's pause/resume is its established way to stop work a person can unblock. `PartialPricing`
default **FLOOR** (ADR-0069's default), configurable. Ceilings unset ⇒ no ceiling, and the ledger
still accumulates and still renders.

### D5 — what the page shows

**Recommendation:** per-unit cost on the focused unit (from `remaining()`/`entries()` for that
run), and per-project cost + position in the badge row (`balances(scope=PER_TAG,
window_key="project:<id>")`, which reads through no ceiling and answers on a ledger with none).
Render money from `Money` in whole nanos — never a float — `—` plus the reason for unpriced, "at
least" whenever any of the three honesty counts is non-zero.

## Part 2 — Commissioner (IP-A2)

**Exit (§6.2):** the badge is backed by rows, not by an ad-hoc flag; denials visible in project
history.

**Evaluate on configuration, before availability** (ADR-0073): the decision is made when a stage is
about to run, from `inference.mode` + the configured base URL + `inference.data_classification`,
recorded through `SqlEgressLedger`, and *then* acted on. Commissioner does not enforce (ADR-0054):
the refusal stays `config.py:739`'s `providers.allow_remote` check plus whatever this row adds.

### D6 — the target's ceiling, which IdeaPress does not have

`EgressTarget.max_data_classification` is **required when remote**, and a remote target with no
declared ceiling is **denied** (spec §11 contract 2, fail closed). IdeaPress today has one global
`data_classification` and a boolean `allow_remote`. **Recommendation:** a per-backend
`max_data_classification` key on `LoadCoachSettings` and `OpenAICompatibleSettings` (Ollama is
local; `EgressTarget(remote=False)` and the policy answers `target_not_remote`), unset ⇒ denied
with `no_ceiling_declared` — which is a **behaviour change for an existing remote configuration**,
and must be called out in `CHANGELOG.md` and `upgrading.md`. The losing option — defaulting the
ceiling to the installation's own classification — makes every remote call self-approving and
guts the record. **Also decide the `setspec` floor**: `>=0.4` admits a resolution commissioner
forbids; the honest fix is raising IdeaPress's floor to `>=0.5,<0.7`. Recommendation: raise it.

### D7 — where the decision is recorded, and what the badge reads

**Recommendation:** record in the stage runner, once per stage attempt, `run_id` matching D1's
choice and `source_ref` = the attempt id, so a decision joins to an attempt by reference (never by
a SQL join to the mounted table — ADR-0050 decision 2). The badge then reads the **most recent
decision for this project** and renders its verdict and reason; with no decision yet — a fresh
project — it falls back to *stating that nothing has run yet*, not to the old flag. Deleting
`_backend_facts`'s `"egress"` expression and `_is_remote` is the deliverable; keep the badge's
copy ("leaves this machine") intact so the page reads the same.

### D8 — denials in project history

There is no project-history page: `web/routes/units.py:52` serves a *unit* history, and stage
events go through `services/events.py`. **Recommendation:** emit a stage event
(`egress.denied` / `egress.decided`) on the existing sink, which is what the workspace timeline and
the events API already read, and render denials in the unit's provenance table beside the attempt.
Do not build a new page.

## The work, in gate order

**Gate A — the mount.** `pyproject.toml` gains both `[sql]` extras. `models.py` gains
`LEDGER_TABLES` and `EGRESS_TABLES`, unconditional, at module import, with PromptCadence's warning
transcribed. Two migrations on `0006`: `0007_ledger_tables`, `0008_egress_decisions`. Migration
parity test green; `alembic upgrade head` on a fresh SQLite file and on the existing dev database.

**Gate B — LoadLedger debits.** D1–D3: a `services/budget.py` (small), pricing loading, the debit
in `record_attempt()`. No UI yet. Tests: an unpriced local attempt accumulates tokens and touches
no money; a priced one derives money and stores `pricing_hash`; a partial estimate produces a
floor with the counts set.

**Gate C — LoadLedger ceilings and the page.** D4, D5. **§6.1's exit is proved here** — a project
page answering "what did this cost?" on a real run, and a screenshot or the rendered HTML in the
handoff.

**Gate D — Commissioner.** D6–D8: the ceiling keys, the evaluation site, the ledger write, the
badge reading rows, `_is_remote` and the ad-hoc flag deleted, denials on the timeline. **§6.2's
exit is proved here**, separately: a denied decision visible as a row and on the page.

**Gate E — docs and ADRs.** `workflows.md` (the debit and the decision in the stage sequence),
`data-model.md` (the five mounted tables, named as package-owned), `risks.md` S4 (the badge is now
a record), `configuration.md` + `upgrading.md` (the new keys, and D6's fail-closed change), the
ADR(s) from D4/D6 if the recommendations are taken. Mirror and `cmp`.

**Gate F — the gate, and stop.** Full gate plus `pytest --cov` ≥ 85 %. `CHANGELOG.md` under
`## [Unreleased]` — **no version bump, no tag, no push** (ground truth 1).

## Stop rules

* **No join from an IdeaPress entity to a mounted table** (ADR-0050 decision 2). Reads go through
  `SqlLedger` / `SqlEgressLedger`. If a view needs a join to be fast, that is a finding for the
  package, not a query you write.
* **Never a fabricated zero.** Unpriced is `—` with a reason; a floor says "at least".
* **Commissioner does not enforce** (ADR-0054). If you find yourself writing "and then refuse the
  call" inside the evaluation, the refusal belongs in IdeaPress's own code, beside
  `allow_remote`'s.
* If a mount cannot be made unconditional because a package is an optional extra, **stop and say
  so** — a conditional mount makes autogenerate emit a `DROP`, which is data loss, and the answer
  is a hard dependency, not a clever mount.
* Do not touch `domain/context_assembly.py`, `services/project_review.py`, `services/unit_loop.py`
  or `services/review_loop.py` — J2's files.
* Do not build a project-history page, a per-stage classification, or a price-catalogue package.

## Exit conditions

1. **§6.1, proved on its own:** every stage attempt debits; a project page shows per-unit and
   per-project cost honestly (`—` + reason for unpriced local, "at least" for a floor); ceilings
   configurable and binding, with the bound behaviour of D4 demonstrated.
2. **§6.2, proved on its own:** the badge renders from a recorded decision; `_is_remote` and the
   ad-hoc `"egress"` expression are gone; an approval and a denial are both durable rows, and the
   denial is visible where D8 put it.
3. Two migrations on the `0006` chain, parity test green, `upgrade head` clean on a fresh database
   and on an existing one.
4. Default gate green on a named interpreter, coverage ≥ 85 %, **with no network, no GPU, no
   LoadCoach installed and no pricing file present**.
5. Docs current, mirrored, `cmp`-clean; the roadmap's J1/J2 rows corrected for the version.
6. Committed, **unreleased**, untagged, unpushed; `git status --short` clean everywhere.

## The handoff

`docs/history/handoffs/J1_HANDOFF.md`, in the house shape:

1. Gate results with the exact invocations and the interpreter.
2. The gates as commits.
3. **The eight decisions** (D1–D8), each with what the losing option would have claimed. D1 and D6
   are the two a reviewer reads first.
4. **The two exits, answered separately**, with the evidence for each — rendered page for §6.1, the
   approved and denied rows for §6.2.
5. Exit conditions, answered one by one.
6. Things this prompt said that turned out not to be true (line numbers were read on 2026-09-07).
7. What the operator still has to do — nothing here ships; J2 cuts `1.2.0`.
8. Anything found that belongs to another row: in particular whether the pricing loader wants to be
   a package (D3), whether LoadLedger needs a composite window for "this project, this day"
   (spec §21), and anything the two mounts made awkward that a third consumer would hit too.

## Constraints

* **IdeaPress and `docs/` only.** LoadLedger and Commissioner are adopted as published, not edited.
* **IdeaPress imports no other application** — PromptCadence's code is read and transcribed, never
  imported. Never weaken `.importlinter`.
* **Cost is re-derived, never stored** (ADR-0030): persist `TokenUsage` + `pricing_hash`, never a
  money column of your own.
* **A model is never a test oracle**, and nothing in this row calls one.
* If the work must stop early, stop at a green gate with a commit — **after Part 1 if you must**,
  since the two halves are separately provable — and say exactly where you stopped.
