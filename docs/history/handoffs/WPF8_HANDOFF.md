# WPF8 Handoff — the calibration report counts what it judged, and exports what it shows

**Row:** WPF8 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, unattended · **Model:** Claude
Sonnet 5 · **Kickoff:**
`history/prompts/wpf8-freeweight-calibration-report-counts-and-export.prompt.md` (Wave 1) ·
**Branch:** `row/wpf8-calibration-report` in `~/ai/suite/FreeWeight`, off `main`, not merged

## 1. Status

**Gate A is done and committed** (FreeWeight `2cc8942`, WeightRoom `c44cc23`). **Gate B — the live
proof — did not run.** At the point this row would have started it, `nvidia-smi` showed a
judge-sized model (`Qwen3.5-9B` class) loaded via Ollama 65 seconds earlier, 10.2 GiB of the
machine's 16 GiB in use, ~4.6 GiB free — almost certainly another Wave 1 row's live step
(WPF1/WPF3/WPF7 all run live steps this wave), not idle leftover state. ADR-0119 is one live
model load at a time, and the memory-safety incident this arc's ADRs 0119–0122 came from was
exactly this kind of collision. The operator chose to hold off rather than risk it. **This row is
not done** — Gate A's code and tests stand on their own, but the live proof against `wp6_goal`
still needs to run once the GPU is clear, and the handoff finish line (job id, live report/export
agreement) is unmet until then.

## 2. Where the count went (decision 1)

Traced the partition through to the report, per WP6's exact numbers (`anchors 8, holdout 4`,
report said `n_holdout 2`). `run_calibration` judges every holdout sample for every judged
criterion (`services/calibration.py`'s per-sample loop), but a sample whose jury verdict produced
no `median_grade` — a refusal, or an answer no verdict could parse into a grade — was silently
dropped: `jury_grades` never got an entry for it, and `measure_agreement`'s pairing only counts a
sample present in both `jury_grades` and the author's own grades. Nothing recorded *why* the count
was smaller than what the progress events (`calibration.sample_judged`) had already shown live.

Fixed by tracking exclusions where they're already known, rather than reconstructing them after
the fact:

* `run_calibration` now records a reason (`_exclusion_reason`) whenever `median_grade` is `None`
  — a juror's own `refused_reason` (`self_judging`, `protocol_error`, `timeout`) when every
  verdict refused, or `"unparsed_grade"` when the jury answered but no verdict yielded a usable
  grade.
* `measure_agreement` takes the holdout's full sample-id set and that exclusion map, and for each
  criterion computes which of the attempted samples never made it into a counted pair — including
  a case the exclusion map alone can't see: the jury graded it but the *author* never did
  (`"not_graded_by_author"`).
* `CriterionAgreement` gained `n_judged` (how many the jury actually judged for that criterion)
  and `excluded` (each dropped sample, with its reason). `GateVerdict` gained the same `n_judged`
  at the goal level. Both are `n_judged == n_holdout` and `excluded == ()` when nothing was
  dropped — the common case is unchanged.
* Persisted in the existing `disagreement_json` blob (goal-level and per-criterion rows) rather
  than a new column, so **no migration was needed**. `latest_outcome` reads it back with
  `.get(..., <old default>)`, so a report written before this row still loads.
* `api.md` §3a documents `n_judged`/`excluded` beside `n_holdout`.

**A criterion that counted zero pairs is still omitted from `outcome.criteria` entirely** — that
rule (`TestAJudgedGoalThatCouldNotBeGradedIsUncalibrated`) predates this row and stands: "nothing
to report" is still nothing to report, even now that we *could* say why. `n_judged`/`excluded`
only apply to a criterion that produced at least one counted pair, which is the shape WP6 actually
hit (2 counted of 4 judged, not 0 of 4).

## 3. What the export now carries (decision 2)

Checked whether `benchmark.calibration_report` `1.0` already allows a partial criterion:
`setspec.capability.v1.CalibrationFields` declares `kappa_w: float` and `rho: float`, both
required, neither `Optional`. It does not, and `1.0` is frozen — this build doesn't loosen it.

Reproduced WP6's "criteria: []" directly (a jury that answers the same grade for every sample:
`kappa_w` computes fine against a varying author, but a constant series gives Spearman's `rho`
nothing to correlate, so `rho` is `None`). The internal report (`GET .../calibration/report`)
already carries such a criterion in full — `measure_agreement` never required all four figures,
only that the criterion produced at least one pair. `_calibration_report_payload`'s
`if kappa_w is not None and rho is not None` filter is what drops it from the export, and that
filter is correct given the schema: a coefficient the schema requires and this build could not
compute is never fabricated as a number (the same rule that makes an unmeasured criterion's
`kappa_w` `None` rather than `0.0` elsewhere in this module).

**No code change.** The chosen answer from the kickoff's two options is "the export is a
different, narrower document than the page, and says so" — `api.md` §3a now states explicitly
that a criterion missing either coefficient is on the report and off the export, and why. Locked
in by a new contract test
(`test_a_criterion_with_no_computable_rho_is_reported_but_not_exported`).

## 4. Decision 3 — should the export refuse instead of rendering the page?

It already does. `test_the_export_refuses_in_the_error_envelope_when_no_report_exists`
(`tests/e2e/test_goals_api.py`) hits `GET /api/v1/goals/{slug}/calibration/report/export` on a
freshly created judged goal with no report and gets a `400` in the standard `{"error": {...}}`
envelope, `application/json`. `ExportRefused` is a `ValidationError`/`SuiteError` and is caught by
`register_exception_handlers`'s `SuiteError` handler like every other domain refusal — there is no
code path from this route to an HTML response.

**What the kickoff got wrong:** WP6 most likely observed FreeWeight's separate
`GET /goals/{slug}/report` route (`web/routes/wizard.py:518`, the wizard's own HTML page, which
renders `"No calibration yet"` and is always `200 text/html` regardless of state) rather than the
API export route this decision is about. The two share the word "report" but are otherwise
unrelated routes with unrelated contracts; nothing suggests the API route itself misbehaves.

## 5. Tests (Gate A)

* `tests/integration/test_calibration_flow.py::TestTheReportCountsWhatItJudged` — a fully-judged
  holdout has `n_judged == n_holdout` and `excluded == ()`; a jury that refuses the first two of
  five holdout samples (`_PartiallyRefusingJury`) produces `n_judged == n_holdout + 2`, two
  `excluded` entries reasoned `"protocol_error"`, and the exclusion survives a `latest_outcome`
  round trip.
* `tests/contract/test_export_schemas.py::TestTheCalibrationReportContract::test_a_criterion_with_no_computable_rho_is_reported_but_not_exported`
  — `_ConstantJury` (one juror, always the same grade) produces a real `kappa_w` and a `None`
  `rho`; the internal report keeps the criterion, the export's parsed payload has none.
* `tests/e2e/test_goals_api.py::TestCalibrationEndpoints::test_the_export_refuses_in_the_error_envelope_when_no_report_exists`
  — decision 3, above.

## 6. Gate (Python 3.14.4, `.venv/bin/*`)

`ruff format --check .`, `ruff check .`, `mypy src tests`, `lint-imports` — all green. Full suite:
**2729 passed, 30 skipped, 31 deselected** (`live`/`performance`); coverage **89.51 %** (floor
85 %; `calibration.py` itself at 94 %). OpenAPI snapshot (`scripts/generate_openapi_snapshot.py
--check`) unaffected — every touched route already returns an untyped `dict[str, Any]`, so no
route's declared schema changed. `git status --short` clean in both repositories at every commit.

## 7. Docs

`docs/apps/freeweight/api.md` is WeightRoomGym's canonical copy (`WeightRoom/docs/apps/…`).
Caught this the slow way: edited FreeWeight's copy first out of habit (it's committed together
with the code, in FreeWeight `2cc8942`), then found the mismatch with `cmp` against
WeightRoomGym's canonical copy and fixed the canonical copy to match (WeightRoom `c44cc23`),
verified byte-identical with `scripts/sync_docs.py --check` before committing either. Worth
naming for whoever reads this next: check `cmp` (or `sync_docs.py --check`) before committing a
component's `docs/apps/**` edit, not after.

## 8. What's left

* **Gate B** — the live proof: on the reference machine, with `wp6_goal` (12 samples, 24 grades
  already installed), regrade enough samples to give a criterion real variance, run the
  calibration from the console's Goals page, and confirm the report and its export agree on both
  the count and the criteria now that the fix is in. Needs a GPU window clear of the other Wave 1
  rows' live steps — check `nvidia-smi` and for a live-graded row of the wave in progress before
  starting.
* Merge `row/wpf8-calibration-report` to FreeWeight `main` once Gate B lands (this row is first
  into FreeWeight this arc; nothing to rebase onto).
* Mark the row done in `weightroom-work.md` at that point — it currently reads "Gate A done, Gate
  B pending" rather than done.
