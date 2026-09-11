# Kickoff — WPF8: the calibration report counts what it judged, and exports what it shows

**Row:** WPF8 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md), findings 10 and 11), and first seen at
WP4 (`WP4_HANDOFF.md` §5 step 4, left for WP6). Runs after WP6, independent of the other WPF rows.
**Ships:** unreleased, no version bump.
- **FreeWeight:** a calibration report whose held-out count is the number of samples the jury
  actually judged, or which says why a judged sample is not counted; and an exported
  `benchmark.calibration_report` that carries the per-criterion body the report page shows.

**Component:** `~/ai/suite/FreeWeight`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WP6_HANDOFF.md` findings 10 and 11 and check 2's FreeWeight goals row;
`WP4_HANDOFF.md` §2 items 1 and 4, and §5 step 4; ADR-0032 (goals and calibration);
`apps/freeweight/api.md` §3a; `packages/setspec/schemas.md` for `benchmark.calibration_report`.

**Code to read first:** FreeWeight's `services/calibration.py` (the partition, the jury pass, the
report's arithmetic), the report's serialiser for the export, and the tests that cover both.

## What WP6 saw on the reference machine (2026-09-11)

Goal `wp6_goal`, forked from `technical_explanation`, 12 pasted samples, 24 grades recorded, one
juror (`llamacpp/Qwen3.5-9B-UD-Q8_K_XL@sha256:2c4e08e0e72c`).

1. **Judged four, counted two.** The job (`01M297EVXDF0N9SXPW09V2QG3W`, 1 375 s) printed
   `calibration.started` with `anchors 8, holdout 4`, then `calibration.sample_judged` for
   `1 of 4`, `2 of 4`, `3 of 4` and `4 of 4`. The report page and `GET
   /goals/wp6_goal/calibration/report` both say `n_anchor 8 · n_holdout 2`, and each criterion says
   `n_holdout 2`. Nothing on the page or in the payload says why two of the four judged samples are
   not counted. WP4 saw the same shape: four judged, three counted.
2. **The export drops the criteria.** `GET /goals/wp6_goal/report/export` returns
   `wp6_goal.calibration-report.json`, 761 bytes, `schema benchmark.calibration_report 1.0`, whose
   payload carries `"criteria": []` — while the page and the API carry both criteria with their
   `kappa_w`, `rho`, `mae`, `bias`, `n_holdout`, validity, band, lint and worst disagreements. The
   export is what a person keeps, and it is the empty half.

Everything else in that path worked: the fork, the dry-run edit with both hashes, the pasted set, the
grading across a reload with FreeWeight's own upserts, the capped job, the report's bands and lint,
and the bundle and goal-pack exports.

## Decisions already taken — do not reopen

* **A coefficient is never shown without its n** (the report's own words). That rule is why the
  mismatch matters: the n has to be the n the coefficient was computed over.
* **The exported report is a SetSpec payload.** Whatever it carries is `benchmark.calibration_report`
  at its stated version, and a reader validates it. Adding the criteria to the payload is a schema
  question: check whether `1.0` already allows them before changing anything.

## Decisions for this row — make each, and record it in the handoff

1. **Which samples the report counts, and why.** Trace the partition through the jury pass to the
   report. If a judged sample is legitimately excluded — a refusal, an unparsed grade, a tie — the
   report says so, by count and by reason, beside the n.
2. **What the export carries.** Either the criteria belong in the payload at `1.0`, or the export is
   a different document from the page and says so in `api.md`. Decide, and make the goldens agree.
3. Whether `GET .../report/export` should refuse, rather than render the page, when no report exists
   (WP6 saw it answer `text/html` in that state).

## Gates

**Gate A.** Tests first: a calibration whose jury judges every held-out sample reports that number;
an excluded sample is counted and explained; the exported payload matches the report the page
renders. Implement. Run the gate, naming the interpreter. Refresh the OpenAPI snapshot and the
CHANGELOG. Commit.

**Gate B — the live proof.** On the reference machine, with `wp6_goal` (already installed, 12
samples, 24 grades): regrade enough samples to give a criterion variance, run the calibration from
the console's Goals page, and show the report and its export agreeing on both the count and the
criteria. Commit the handoff.

## Finish line

- The gate green, with the interpreter named, and coverage held; `git status --short` clean.
- `docs/history/handoffs/WPF8_HANDOFF.md`: where the count went, what the export now carries, the
  job id of the live proof, and what this kickoff got wrong.
- The row marked done. Nothing pushed.
