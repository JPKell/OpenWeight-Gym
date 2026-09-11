# Kickoff — WP4: application pages IV — FreeWeight goals, calibration and grading

**Row:** WP4 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after WP3. Part of the WP arc ([`wp-app-pages-arc.prompt.md`](wp-app-pages-arc.prompt.md)).
**Ships:** unreleased. FreeWeight's Goals page at full parity: authoring, starters, import/export,
judges, calibration, grading and the report.
**Component:** `~/ai/suite/WeightRoom`. `~/ai/suite/FreeWeight` for any missing API route.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** the arc index §2; `history/handoffs/WP3_HANDOFF.md` (the run-stream proxy this
row's calibration run reuses); `apps/freeweight/api.md` **§3a in full** and its notes;
`apps/freeweight/spec.md` (goals, rungs, calibration, jury); ADR-0032 and every ADR it links;
`standards/database-standards.md` §8 (previewed destructive operations).
**Parity target:** FreeWeight's own `web/templates/{goals,grading}` and the routes behind them —
the `/goals/new/{draft_id}/{criteria,rules,tasks,save}` wizard, `/goals/starters/{key}/customise`,
`/goals/{slug}/grade`, `/runs/{run_id}/grade`, `/results/goals/{slug}`. Inventory them first and
note which have no `/api/v1` equivalent.

## Decisions already taken — do not reopen

* Everything in the arc index §2.
* **A goal draft belongs to FreeWeight** (spec §10, data ownership). If FreeWeight's wizard keeps
  drafts server-side, expose them over FreeWeight's API in a FreeWeight commit, and the console
  drives them. WeightRoomGym's database never holds a second draft store. A draft a person has
  spent time on survives a reload and a console restart.
* **Create** accepts both a pack body and the wizard. Lint findings are returned and shown, and
  never block. **Fork** and **customise** start from a starter, and a fork stays `unforked` until
  it is edited.
* **Edit** is `PUT /goals/{slug}`. When `goal_hash` moves, the page shows the old hash, the new
  hash and the count of runs the change separates, and asks for confirmation before the change
  commits. **Delete** shows FreeWeight's preview (runs orphaned, grades destroyed) and confirms by
  typed slug. Both are audited.
* **Suggest-rules** proposals are **never applied automatically**. Each proposal is accepted into
  the draft by the operator, one at a time.
* **Import** passes FreeWeight's size cap, containment check and hash check. A colliding slug
  renders FreeWeight's refusal with the existing `goal_hash`. **Export** offers both forms and
  names which one round-trips (the bundle `freeweight goals export` writes) and which does not
  (`benchmark.goal_pack`).
* **Judges.** Eligible jurors with their `native.judge` bias results and eligibility reasons, and
  `POST /judges/validate` as a dry run of a jury (self-judging, remote permission,
  structured-output capability).
* **Calibration.** Samples by partition with grade progress. Add samples by generation over a
  model spread, pasted text, or promotion of prior run samples. The holdout run streams live
  through WP3's run-event proxy.
* **Grading** reproduces what FreeWeight's grading page hides from the grader. Check it and
  record it; at minimum, no jury score before a human grade. It is keyboard-operable, submits per
  `(sample, criterion)` idempotently, saves partial progress, and resumes where the grader
  stopped. Sample text is escaped. Run-sample grading (`/runs/{id}/grade`) is included.
* **The report** shows `kappa_w`, `rho`, `mae`, `bias`, `n_anchor`, `n_holdout`, inter-juror
  alpha per criterion and weighted, the gate verdict, `judge_validity_factor`, and the
  worst-diverging holdout samples with both rationales. A figure FreeWeight cannot compute
  renders `—` with its reason, never `0`.

## Gates

**Gate A — goals.** Any FreeWeight API commits first, in FreeWeight: drafts, grading routes, and
whatever else the inventory found, with FreeWeight's gate green. Then list, detail, create (pack
and wizard), fork/customise, edit with the separating-change confirmation, delete with preview,
validate, suggest-rules, import/export. Commit.

**Gate B — calibration and grading.** Samples, grading (idempotency and resume tested against a
fake FreeWeight that drops the connection mid-batch), the holdout run live, the report, judges.
`app_side_nav_stubs("freeweight") == ()`. `EXERCISES`, the §14 registry, the OpenAPI snapshot and
`api.md` updated. `CHANGELOG.md` updated. Commit.

## Demonstrate

On the reference machine:

1. Fork a starter and edit a criterion. See the separating-change confirmation name the runs it
   separates.
2. Add calibration samples by generation.
3. Grade half the anchors from a phone, reload, and finish them.
4. Run the holdout live and read the report.
5. Export the bundle, delete the goal through its preview, and import the bundle back to the same
   `goal_hash`.

Take screenshots in both themes.

## Finish line

Gate green in every repository touched, with the interpreter named. Coverage held. One commit per
gate. A handoff at `docs/history/handoffs/WP4_HANDOFF.md` with the parity table, what grading
hides, where drafts live, and what the kickoff got wrong. The row marked done.
