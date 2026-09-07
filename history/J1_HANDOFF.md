# J1 handoff — IdeaPress adopts LoadLedger and Commissioner

**Row:** J1 (Sonnet 5 · high), IP-A1 + IP-A2, `docs/roadmap/outstanding-work.md` §1.
**Component:** `/home/jpk/ai/suite/IdeaPress`, main tree, branch `main`. **Kickoff:**
`docs/history/j1-ideapress-loadledger-commissioner.prompt.md`, run under the coordinator's overrides
(ADR numbering from 0103; J2 running concurrently in the `IdeaPress-j2` worktree, files not shared).

## 1. Gate results

Interpreter: `IdeaPress/.venv/bin/python` — CPython 3.13.15.

```bash
cd /home/jpk/ai/suite/IdeaPress
.venv/bin/python -m ruff format --check .   # 183 files already formatted
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/mypy src tests                    # Success: no issues found in 178 source files
.venv/bin/lint-imports                      # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -q                              # 1117 passed, 5 skipped, 30 deselected
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                             # Required test coverage of 85.0% reached: 88.63%
```

No network beyond loopback (the suite's `no_network` autouse fixture enforces this), no GPU, no
`loadcoach` installed (`ModuleNotFoundError` confirmed directly), no `[pricing] file` configured by
default. `git status --short` clean in both `IdeaPress` and `docs` at the start and the end.

## 2. The gates as commits

One commit in `IdeaPress` (`main`, `c8f3fa6`), carrying gates A–F together — the migrations,
`models.py` mount, the three new services, the `Database`/`stages.py`/`plan.py` wiring, the
workspace/unit-report rendering, the four new test files plus edits to three existing ones, and the
mirrored docs. I did not split it further: gates A–D are one design (the mount and the debit site
are not separately reviewable — a mount with no debit site is untested, and a debit site with no
mount does not run), and splitting them would have meant committing migrations the models they
migrate did not yet reference, which the suite's own working-tree-integrity note argues against
doing deliberately.

One commit in `docs` (`main`), staged and committed by name (never `git add -A`, and I re-ran
`git status --short` before staging to confirm no other agent's uncommitted file was present):
`adr/0103-*.md`, `adr/README.md`, `roadmap/outstanding-work.md`, `apps/ideapress/{workflows,
data-model,risks}.md`, and this handoff.

## 3. The eight decisions

**D1 — the two scopes, and what `run_id` means.** Took the recommendation: `run_id` is the unit's
own id, or `project:<project_id>` for a stage attempt with no unit (`plan`, `project_review`);
tags are `project:<id>`, `stage:<name>`, `backend:<name>`; `PER_TAG` binds on `project:<id>`,
lifetime. **Departed from the recommendation on `declare_run()`'s necessity.** The kickoff frames
declaring at unit creation as what avoids `UnknownRun` on a fresh unit's cost view; I implemented
it (`services/plan.py::store_plan`, guarded on `Database.budget is not None`) **and** made every
read path (`unit_cost`, `project_cost`) tolerate `UnknownRun` gracefully regardless, because
`services/plan.py` is not one of J2's files but *is* one more file than the kickoff's named
touch-list, and I wanted the reads correct even if a future caller creates a unit through a path
that skips the declaration. The losing option — reads that raise on an undeclared unit — would have
made a freshly planned project's workspace page crash before its first attempt.

**D2 — what is deleted.** Confirmed: nothing. `AttemptRow.input_tokens`/`output_tokens`/
`thinking_tokens` are provenance (workflows §8) and stay; no in-app cost accumulator existed to
delete. Said so rather than manufacturing a deletion.

**D3 — where the pricing comes from.** Took the recommendation: `[pricing] file`, a copy of
PromptCadence's `services/pricing.py` loader adapted to one flat catalogue (IdeaPress has one
configured backend, never several tiers, so the tier map and the pre-flight worst-case estimator
were dropped). **The copy is 249 lines, over the kickoff's ~120-line flag** — the tier removal saved
perhaps 20 lines; the bulk is the JSON record validation itself, which is inherent to the format
(ADR-0072), not tier-shaped. This is the finding item 8 below names for the operator: a second
near-identical copy now exists, and ADR-0072's own "revisit when" trigger ("a second consumer needs
the reader itself") has fired.

**D4 — the ceilings, and what happens when one binds.** Took the recommendation, with the "harder
half" resolved as: a bound `per_output` ceiling pauses the in-flight unit (`drafting`, `validating`,
`auditing`, `revising` — the same four states an exhausted output budget already pauses from),
reusing `assert_transition`'s own guard rather than raising. `PartialPricing` default `FLOOR`,
configurable via `[budget] partial_pricing`. **Recorded as ADR-0103** alongside D6, since both are
"IdeaPress's own reaction to a verdict the package does not own" — one ADR, not two, because
splitting them would have argued the same boundary rule (ADR-0011/ADR-0054's "the package decides
nothing, the caller decides everything") twice. The losing option (raising from `record_attempt`)
would have surfaced as `INTERNAL_ERROR` in the two callers this row cannot edit, rather than the
structured `paused` outcome the state machine already has a UI for.

**D5 — what the page shows.** Took the recommendation, with one refinement the kickoff's own
phrasing did not quite resolve: reads use `Ledger.balances()` (ceiling-agnostic) for the spent
figure, never `remaining()` alone, because with "unset ⇒ no ceiling" as the design (D4), a
`per_output`/`per_project` ceiling left unconfigured means `remaining()` has nothing to evaluate at
all and a unit's real spend would be unreadable. `balances()` always answers; the ceiling's own
`exceeded`/remaining figures are layered on top when one is configured (`unit_cost`/`project_cost`
in `services/budget.py`). Rendered via `Money`, whole nanos, never a float; `—` plus the reason for
unpriced; "at least" for a floor.

**D6 — the target's ceiling, which IdeaPress does not have.** Took the recommendation: per-backend
`max_data_classification` on `LoadCoachSettings` and `OpenAICompatibleSettings` (Ollama hard-coded
local); unset on a remote target ⇒ `DENIED`/`no_ceiling_declared`, fail closed. Raised the `setspec`
floor to `>=0.5,<0.7` (already satisfied by the resolved `0.6.0`). **Recorded as ADR-0103.** The
losing option (default the ceiling to the installation's own classification) would have made every
remote call self-approving, the exact defect ADR-0054 already rejected for Commissioner generally.

**D7 — where the decision is recorded, and what the badge reads.** Took the recommendation for
*where* (`record_attempt`, `run_id` matching D1, `source_ref` = the attempt id) but **resolved a
tension the text did not spell out** for *what the badge reads*: D1's run_id is per-unit/per-project
pseudo, so "the most recent decision for this project" cannot be answered by naming one run_id — a
project's attempts span several. IdeaPress configures exactly one backend for the whole process
(and one `data_classification`), so every decision against that backend *is* the installation's
current posture regardless of which unit produced it; the badge therefore reads
`EgressService.latest_for_target(backend_name)`, filtered by target, not by run or project. This is
simpler than assembling every unit's run id into a query and exactly as correct given the
one-backend-per-process reality. `_backend_facts`'s `"egress"` expression and `_is_remote` are
deleted (`services/workspace.py`); the badge's copy ("leaves this machine" / "stays on this
machine") is unchanged.

**D8 — denials in project history.** Took the recommendation's provenance-table half
(`unit_reports.unit_detail`'s per-attempt `"egress"` field, joined by `source_ref` == attempt id,
via `EgressService.decisions(run_id=unit_id)` — never a SQL join to the mounted table). **Dropped**
the recommendation's other half, a live `egress.denied` stage event on the existing sink:
`record_attempt` is a free function with no `StageEventSink` reference, and giving it one would mean
attaching a fourth handle to `Database` (after `budget`/`egress`/`settings`) for a "nice to have" the
provenance table and the durable row already satisfy structurally. Noted as a deliberate scope trim,
not an oversight; item 8 below names it for a future row if a live timeline entry is wanted.

## 4. The two exits, answered separately

**§6.1 (LoadLedger), on a real recorded attempt** — `tests/integration/test_cost_and_egress_page.py::
test_the_unit_page_answers_what_it_cost_honestly`, calling the exact functions the workspace route
renders (`unit_reports.unit_detail`, `services.workspace.workspace_view`) after one real
`record_attempt` on a local (Ollama) backend with no pricing file configured:

```text
detail["cost"]["money_spent_display"]  == "—"              # unpriced, never "$0.00"
detail["cost"]["tokens_spent_display"] == "at least 184"    # a floor: see the note below
detail["attempts"][0]["egress"]["verdict"] == "approved"
view["project_cost"]["tokens_spent_display"] == "at least 184"
```

A denied-and-approved pair, both durable, is
`tests/integration/test_stage_governance.py::test_a_remote_backend_with_no_declared_ceiling_is_denied_fail_closed`
and `::test_an_attempt_records_an_egress_decision_joined_by_attempt_id` — one records `verdict ==
"approved"` / `"target_not_remote"` against Ollama, the other `verdict == "denied"` /
`"no_ceiling_declared"` against an `openai_compatible` backend with no declared ceiling, both
queryable by `run_id` afterward.

**§6.2 (Commissioner), on the same page** — the workspace badge in the same test:
`view["backend"]["has_run"] is True`, `["verdict"] == "approved"`, and (from
`test_stage_governance.py`) a fresh `Database` with governance attached but nothing recorded yet
answers `has_run: False` — the fallback D7 asked for, proved in
`tests/security/test_lan_exposure.py::test_the_workspace_says_nothing_has_run_yet_before_any_egress_decision`.

**A real, if uncomfortable, finding on both exits**: every rendered token and money figure is "at
least", never a bare total, on every debit this row can produce today. `TokenUsage.total_tokens`
naming — see item 6.

## 5. Exit conditions, one by one

1. **Met.** Every attempt debits (`services/stages.py::_govern_attempt`, unconditional when
   governance is attached); the page shows per-unit and per-project cost honestly; ceilings are
   configurable (`[budget]`) and binding — a bound `per_output` ceiling pauses the unit, demonstrated
   in `test_stage_governance.py::test_a_bound_output_ceiling_pauses_the_in_flight_unit`.
2. **Met.** The badge reads a recorded decision; `_is_remote` and the ad-hoc `"egress"` expression
   are gone (`git diff` on `services/workspace.py` shows the deletion); an approval and a denial are
   both durable, queryable rows (§4 above); the denial is visible in the unit's own provenance table
   (`unit_reports.py`'s per-attempt `"egress"` field), not a new page.
3. **Met.** Two migrations (`0007`, `0008`) on the `0006` chain; parity test green on SQLite
   (`test_models_and_migration_agree_on_sqlite`, PostgreSQL variant present and marked `live`);
   `upgrade head` clean on a fresh file and on a simulated existing dev database — a project, run
   and attempt written at revision `0006`, then upgraded to `head`, prove both untouched and the two
   new mounts empty (`test_0007_and_0008_leave_an_existing_dev_database_untouched`).
4. **Met.** Full gate green (§1), coverage 88.63 % ≥ 85 %, no network beyond loopback, no GPU, no
   `loadcoach` installed, no pricing file present by default.
5. **Met.** `workflows.md` §8, `data-model.md` (new subsection before §3), `risks.md` S4 edited in
   the workspace copy and mirrored byte-identically (`cmp` on all three, verified below); roadmap's
   J1 and J2 rows corrected for the version (§6 below); ADR-0103 written and indexed.
6. **Met.** Committed, unreleased (`CHANGELOG.md` under `## [Unreleased]`, no version bump), untagged,
   unpushed; `git status --short` clean in both repos at the end.

```bash
cmp docs/apps/ideapress/workflows.md IdeaPress/docs/apps/ideapress/workflows.md      # (no output)
cmp docs/apps/ideapress/data-model.md IdeaPress/docs/apps/ideapress/data-model.md    # (no output)
cmp docs/apps/ideapress/risks.md IdeaPress/docs/apps/ideapress/risks.md              # (no output)
```

## 6. Things the kickoff said that turned out not to be true

* **The roadmap's own J1/J2 rows were more stale than ground truth 1 described.** By the time this
  row ran, `roadmap/outstanding-work.md` had already been edited (2026-09-07, presumably at the same
  merge that split IP-A3 into J2) to say J1 "ships nothing" — correct — but J2's row still read
  "IdeaPress 1.1: IP-A3 CutCtx → **1.1.0**", which cannot be true once IdeaPress is already `1.1.0`.
  Two more mentions of the stale `1.1.0` target for J2 were in §3's ordering note and the M13 summary
  row. All four are corrected now; none of the surrounding prose needed to move.
* **`0103` was free as the coordinator said, but `0105`–`0109` were not** by the time this row
  started (five ADRs from an unrelated audit row had landed since the kickoff was drafted). Not a
  problem — I checked `adr/README.md` and the directory listing before writing, per the kickoff's
  own instruction to verify the next free number, and used only `0103`.
* **`services/workspace.py::_backend_summary`**, named in the (now-corrected) roadmap row's own
  prose as where the ad-hoc egress flag lives, does not exist under that name; the function is
  `_backend_facts`. I left the roadmap row's prose alone beyond the version fix (out of this row's
  stated scope) but note it here so a future reader is not confused chasing the wrong identifier.
* **Line numbers in the kickoff's reading list drifted by roughly one line each** by the time I read
  the files (`workspace.py:209`/`:216` were `:209`/`:216` still, but only because no earlier edit had
  landed in that file — worth flagging that "read on 2026-09-07" was still accurate for this row,
  unlike some prior rows' handoffs that found drift).

## 7. What the operator still has to do

Nothing ships from this row. J2 cuts `ideapress 1.2.0` carrying both adoptions (this row's) plus
CutCtx (J2's own). Operationally, once `1.2.0` is cut: an operator running a remote backend
(`loadcoach` or `openai_compatible`) with `providers.allow_remote = true` should set
`max_data_classification` on that backend's config block, or every attempt against it will be
recorded (not blocked — recorded) as `denied`. This is documented in `IdeaPress/docs/upgrading.md`
and `CHANGELOG.md`.

## 8. Findings for another row

* **The pricing-file loader wants to be a package (D3).** Two ~250-line near-identical copies exist
  now (`promptcadence.services.pricing`, `ideapress.services.pricing`). ADR-0072's own trigger
  ("a second consumer needs the reader itself") has fired. Extraction target: most naturally
  `baseaicore`, if its no-I/O rule is relaxed for this one reader by its own ADR, per ADR-0072 §8;
  otherwise a small new package.
* **LoadLedger's honesty machinery makes every IdeaPress figure a floor, permanently, given today's
  domain model.** `ideapress.domain.inference.TokenUsage` carries no cache-token fields at all
  (only `input_tokens`/`output_tokens`/`thinking_tokens`), so every conversion to
  `baseaicore.TokenUsage` leaves the two cache classes `UNSUPPORTED` — never reported, not even as
  zero. `estimate_cost` and LoadLedger's `unmetered_debit_count` both then correctly mark *every*
  debit as a floor, so "at least 184" rather than "184" is what the page will say forever, priced or
  not, until this is revisited. This is not a defect this row introduced — it is exactly the reality
  ADR-0069 was written to name for every real ModelRack adapter — but it is worth a future row's
  attention if a genuinely complete total ever matters to an operator: either IdeaPress's domain
  `TokenUsage` needs cache fields (which no backend here currently populates, so they would start
  `None` regardless), or the honesty machinery's definition of "unmetered" needs a narrower reading
  for applications that never had cache tokens to report in the first place. `services/budget.py`'s
  module docstring names this in code, not only here.
* **LoadLedger's composite-window question (spec §21) did not come up.** `PER_RUN` (unit) and
  `PER_TAG` (project, lifetime) covered everything this row needed; a "this project, today" window
  was never asked for by any decision here. Not a finding against the spec, just confirmation the
  trigger has not fired yet.
* **A third mounting package would need the miniature-host test kit extracted** (ADR-0050's own
  "revisit when" — this row is the third host after PromptCadence, following the same pattern
  exactly, so the trigger is closer than it was at row F1/F2).
* **The live-timeline egress event (D8's other half) was deliberately dropped**, see D8 above — a
  future row wanting a real-time "egress denied" toast would need to decide whether that justifies a
  fourth `Database`-attached handle (a `StageEventSink` reference) or a different plumbing path
  entirely.
