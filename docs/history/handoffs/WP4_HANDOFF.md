# WP4 Handoff — application pages IV: FreeWeight goals, calibration and grading

**Row:** WP4 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended · **Model:** Claude Opus 5 ·
**Kickoff:** `history/prompts/wp4-weightroom-freeweight-goals.prompt.md` (arc index
`history/prompts/wp-app-pages-arc.prompt.md`) · **Branch:** `main` in `~/ai/suite/WeightRoom` — WP3 and WP5
were both merged, so no parallel-row rules applied

## 1. What shipped

Unreleased, no version bump (the operator holds versions until the W arc ends). Nothing pushed.

**FreeWeight**
* `4090275` — goal authoring, grading and calibration over `/api/v1` (Gate A): the wizard's drafts,
  `pack` and calibration fields on a goal, the bundle, suggest-rules `items`, the blinded calibration
  and run grading views, run grades, server-side promotion by `source_sample_id`, `native.judge`
  figures on `GET /judges`, evidence `explanations`, `goals calibrate --progress`. Fixed: `PUT`
  deleted a pack's other files; a calibration grade could name another goal's sample; the grading
  page's progress counted criteria it did not offer.
* `5a893d1` — the registry is rebuilt after every goal write (API and HTML routes) and by the
  scheduler before each run; an edited fork loses `unforked`.
* `036c48f` — `DELETE /goals/{slug}`'s preview counts the runs of every hash the goal has had.

**WeightRoomGym**
* `884b6de` — `apps/freeweight/api.md` and `spec.md` for the new routes, mirrored into FreeWeight.
* `d9603e2` (Gate A) — the Goals page: list, drafts, starters, create, import, one goal, edit dry-run
  first, delete from the preview, both exports; Evidence shows staleness and confidence factors; the
  kit polish of `WP3_HANDOFF.md` §6 item 5.
* `384eccf` (Gate B) — calibration counts, promotion and generation, the `freeweight_goal_calibrate`
  job, blinded one-sample grading for calibration sets and goal runs, the agreement report, judges.
  `app_side_nav_stubs("freeweight") == ()`.
* The Gate D commit — this handoff, the row marked done, and two fixes the phone demonstration
  found: a `fieldset` widened the grading form past a phone's width, and a `—` gave its reason only
  as a tooltip.

**Gates** (Python 3.14.4, each repository's `.venv/bin/*`; `ruff format --check`, `ruff check`,
`mypy src tests`, `lint-imports`, FreeWeight's OpenAPI snapshot check, `pytest` with coverage), run
after the last change in each repository:
* **FreeWeight** — 2725 passed, 30 skipped; coverage 89.50 % (floor 85 %).
* **WeightRoomGym** — 1844 passed, 3 skipped; coverage 90.28 % (floor 85 %).

## 2. Decisions taken

1. **The holdout run is a capped job, not a run-event stream** (operator, 2026-09-11, asked with the
   trade-offs). FreeWeight's `POST /goals/{slug}/calibration/run` is synchronous: it holds the request
   while the jury grades the holdout and answers the report. It creates no run and streams nothing,
   although api.md said "returns a run id; progress streams over the run event SSE". Three shapes
   were put to the operator: a console job over the CLI, an async API in FreeWeight, or the
   synchronous call with no stream. The job was chosen, for three reasons:
   * it is the least FreeWeight code: a `progress` callback and `goals calibrate --progress`;
   * it runs under the same memory cap as a suite run;
   * the console's single job worker serialises it with every FreeWeight run the console starts.

   The kind is `freeweight_goal_calibrate`. It runs in a `wr-gym-fwrun-` scope, so W10's memory-cap
   alert recognises a kill inside it. api.md now says what really happens.
2. **Generation over a model spread is composed** (operator, 2026-09-11). No part of FreeWeight
   generated calibration samples: not the API, not the CLI (`grade.html` names a
   `goals calibrate --generate` that never existed), not a service. The calibration page runs the goal
   on one model at a time through WP3's capped Start, then promotes each completed run's samples.
   FreeWeight gained **server-side promotion**. An entry naming `source_sample_id` gets FreeWeight's
   own stored text and the run's model. It is refused unless the sample is a completed sample of a run
   of that goal, and a `content` that differs is refused. Before this, the API accepted any
   `source_sample_id` with any text, so a promoted sample's provenance could be forged.
3. **Drafts live in FreeWeight's `wizard_drafts` table**, as they already did. They are exposed as
   `/api/v1/goals/drafts…` over the same service calls the wizard pages make (spec §10). The console
   stores no draft. A draft survives a reload and a console restart because it is FreeWeight's row. It
   expires after 30 days untouched, and every step renews it. `GET /goals/drafts` is new: FreeWeight's
   own UI reached a draft only by its URL.
4. **What FreeWeight's grading page hides**, checked in its templates and services, and what the
   console does about each:
   * **The model that wrote a sample.** It is never fetched, on either grading screen.
   * **The generation order.** The calibration order is a per-goal `sha256(slug:id)` shuffle; the
     run order is seeded by `grading:<run_id>`.
   * **A sample's origin and partition.** They are not read.
   * **Every jury grade and rationale.** They appear only on the report.

   The console reads FreeWeight's own blinded views: `GET /goals/{slug}/calibration/grading` (the
   pages' code moved into `services/calibration.blinded_samples`) and `GET /runs/{id}/grading`. So
   the blinding is a property of what FreeWeight serves, not of a template. Two console pages add to
   it. The calibration page shows the set **only as counts** by partition and origin, because a row
   pairing a sample with its origin would unblind grading. The grading page shows **no jury figure**.
5. **One sample at a time, per `(sample, criterion)`.** FreeWeight's page is one long page of forms,
   one per pair. The console shows one sample with a select per criterion, each option carrying its
   descriptor, and a note. A save posts that sample's graded pairs as one batch. FreeWeight upserts
   each pair, so a resend replaces rather than duplicates. The page opens at the first unfinished
   sample, and after a save it moves to the next one. When FreeWeight does not answer mid-save, the
   audit row is `failed`, the page re-reads what FreeWeight holds, and the operator sends again
   (tested against a fake FreeWeight that lands one grade and then drops the connection).
6. **Editing is `goal.json` and the task records, dry-run first.** `GET /goals/{slug}` now carries
   `pack`, the documents as on disk. FreeWeight's own UI has no edit page (`goals edit` opens
   `$EDITOR`). Every save is `PUT …?dry_run=true` first:
   * an edit that keeps `goal_hash` saves at once;
   * one that moves it shows the old hash, the new hash, the separated runs and the changed fields,
     and commits only when the confirmation carries the same two hashes;
   * if the goal changed after the preview, the new preview is shown instead.
7. **Suggest-rules on an existing goal** shows FreeWeight's proposals with their parameters
   (`items`, new) and applies none. Accepting one there means editing `goal.json`. In a draft, each
   proposal has its own *Accept* form, one at a time, the parameters as edited.
8. **Stopped FreeWeight.** The goal list, one goal (criteria, tasks, lint, stored report), the
   calibration counts and the report read FreeWeight's database at `0010`. Drafts, starters,
   validate, suggest, grading, judges and exports read only its API. The goal-level report band is
   FreeWeight's reading of the coefficient and is not stored, so it renders `—` with that reason.
9. **Kit polish (WP3 §6 item 5).** A refusal renders as `.error-state`. A page the API refused says
   *From the API, which refused this page*. The stopped footer names the application by its label.
   `form.kit-form` lays out as a grid (Results' and Evidence's export forms).
10. **Evidence explanations** are a sibling `explanations` list beside the SetSpec envelopes, one per
    item in order. An envelope is the document LoadCoach imports, and staleness is a reading of it
    at one instant.

## 3. Parity with FreeWeight's own UI

Every page FreeWeight serves for goals and grading, the `/api/v1` route that existed for it when
the row started, and where the console now has it. "Added" means FreeWeight `4090275` put it on the
API in Gate A. Console paths are under `/apps/freeweight`.

| FreeWeight page or form | API before WP4 | Console |
| --- | --- | --- |
| `GET /goals` | `GET /goals` (no κw, n holdout or calibration age) | `/goals`: list, drafts, starters, create, import. `kappa_w`, `n_holdout`, `calibrated_at` and `calibration_stale` added |
| `GET /goals/starters` | `GET /goals/starters` | `/goals`, in reading order |
| `POST /goals/starters/{key}/fork` | `POST /goals/starters/{key}/fork` | `POST /goals/starters/{starter}/fork` |
| `POST /goals/starters/{key}/customise` | none | `POST /goals/starters/{starter}/customise`, over `POST /goals/drafts {"starter": key}` (added) |
| `GET`/`POST /goals/new` | none | `POST /goals/drafts` (added `GET`/`POST /goals/drafts`) |
| `/goals/new/{draft_id}/criteria` | none | `/goals/drafts/{id}` and `POST …/criteria` (added) |
| `/goals/new/{draft_id}/rules` | none | `POST …/rules`, each proposal accepted alone (added, with `items`) |
| `/goals/new/{draft_id}/tasks` | none | `POST …/tasks` (added) |
| `/goals/new/{draft_id}/save` | none | `POST …/save` (added); abandon is `DELETE /goals/drafts/{id}` (added) |
| no edit page (`goals edit` opens `$EDITOR`) | `PUT /goals/{slug}` took no pack from `GET` | `/goals/{slug}/edit`, dry run first. `pack` added to `GET /goals/{slug}`; `PUT` now keeps a pack's other files |
| no delete page (`goals delete` CLI) | `DELETE /goals/{slug}?dry_run` | `POST /goals/{slug}/delete`, preview then typed slug |
| no import page (`goals import` CLI) | `POST /goals/import` | `POST /goals/import`, file or paste |
| no bundle download (`goals export` CLI) | none | `/goals/{slug}/bundle` (added `GET /goals/{slug}/bundle`); `/goals/{slug}/export` for `benchmark.goal_pack` |
| `goals validate`, `goals suggest-rules` CLI | both routes, suggest without parameters | `/goals/{slug}`: validate and proposals with `items` (added) |
| `GET`/`POST /goals/{slug}/grade` | `POST /goals/{slug}/calibration/grades` only | `/goals/{slug}/grade` over `GET /goals/{slug}/calibration/grading` (added, blinded) |
| `GET /goals/{slug}/report` | `GET /goals/{slug}/calibration/report` | `/goals/{slug}/report` and `/report/export` |
| `goals calibrate` CLI | `POST /goals/{slug}/calibration/run`, synchronous | `/goals/{slug}/calibration` and the `freeweight_goal_calibrate` job page (`goals calibrate --progress` added) |
| calibration samples: pasted only | `POST /goals/{slug}/calibration/samples`, any text trusted | `/goals/{slug}/calibration`: paste, promote by `source_sample_id` (FreeWeight now reads the stored text), generate by running the goal |
| `GET`/`POST /runs/{run_id}/grade` | none | `/runs/{run_id}/grade` over `GET /runs/{id}/grading` and `POST /runs/{id}/grades` (added) |
| `GET /results/goals/{slug}` | `GET /results?suite=goal.{slug}` | `/goals/{slug}`, the goal's results |
| `judges` CLI | `GET /judges` (no `native.judge` figures), `POST /judges/validate` | `/judges`: refusals, figures (added), dry run |

## 4. What the kickoff got wrong

1. **"The holdout run streams live through WP3's run-event proxy."** It cannot. FreeWeight's
   `POST /goals/{slug}/calibration/run` is synchronous and creates no run, so there is no run event
   stream to proxy. api.md said otherwise and was corrected. See §2 item 1.
2. **"Add samples by generation over a model spread"** assumed FreeWeight can generate calibration
   samples. Nothing in FreeWeight did. `grade.html` even names `goals calibrate --generate`, which
   never existed. See §2 item 2.
3. **The Parity target lists `/goals/{slug}/grade` and `/runs/{run_id}/grade` as if they had API
   equivalents.** Neither had a blinded read on the API; both were added.
4. **"A fork stays `unforked` until it is edited"** was stated as FreeWeight's behaviour. FreeWeight
   never cleared the field: an edited fork kept the badge and its `UNFORKED_STARTER` lint. Fixed in
   FreeWeight `5a893d1`, found by the demonstration.
5. **Edit, fork, import and create were taken to make a goal runnable.** FreeWeight built its
   benchmark registry once at startup, so a goal written while it ran failed its first run with
   `BENCHMARK_NOT_FOUND`, and an edited goal would have run under its old rubric. Fixed in
   FreeWeight `5a893d1`, found by the demonstration.
6. **"Grade half the anchors."** Grading covers the whole calibration set, anchors and holdout, and
   FreeWeight's blinded view does not say which partition a sample is in. The demonstration graded
   half of the set.

## 5. Demonstration on the reference machine

A **throwaway** console (`https://127.0.0.1:8779`, its own XDG tree in the session scratchpad, open
loopback), driven with Playwright and the system Chrome, against the operator's `freeweight.service`
and Ollama. The operator's `weightroom.service` was not touched. The jury was one juror,
`ollama/qwen3.5:9b-q8_0` (operator's choice, §2).

**Two false starts, both the host's.** The first demonstration (goal `wp4_voice`) ran 09:09–09:48 PDT
and never finished:
* its first generation run failed `BENCHMARK_NOT_FOUND` — the registry bug, §4 item 5;
* its next two runs were left `interrupted` when FreeWeight's scheduler segfaulted in the jury phase
  (09:14 and 09:44), and at 09:48 the whole host froze.

That morning's unattended upgrade had moved the NVIDIA user-space driver to `580.178.04` while the
loaded kernel module stayed `580.173.02`. Between 09:14 and 09:44 the kernel logged segfaults in
unrelated processes and `BUG: Bad page map` in `llama-server`. Nothing of WP4's code was implicated.
The reboot matched the driver, and the demonstration was run again from the start as `wp4_demo`,
because deleting `wp4_voice` was not authorised in that session. **`wp4_voice` is still installed**,
with three runs and no grades. The rerun logged no kernel fault.

1. **Fork and edit.** *Creative non-fiction voice* forked as `wp4_demo` (`sha256:2bda90e8…`,
   `unforked` true). The first edit (a one-juror jury, a `dry_wit` descriptor) showed *This edit
   separates measurements*, both hashes, *0 run(s)*, *What moved: criteria, judge* and the lint, and
   saved on confirmation: `sha256:e9ad7c4b…`, **`unforked` false**. A draft was opened from *House
   style compliance* and abandoned; the judges page and a jury dry run were shown.
2. **Samples by generation.** The goal ran on `smollm2:135m` (run `01M28RJD8GBYEWX87JD581PHM8`,
   20 min, 3 tasks × 3 repetitions, 9 samples judged) and on `ornith:9b` (`01M28SR4ND27G6T1HE7GAVKP58`,
   28 min), each through the capped Runs start and followed live. Promoting both runs added
   **8** samples from 18: FreeWeight skips a sample whose text is already in the set, and repetitions
   at temperature 0 repeat themselves. Four pasted samples made 12, FreeWeight's target. A second
   edit then showed **2 run(s)** separated (`sha256:b5112a39…`).
3. **Grading from a phone** (Pixel 7 viewport). The first attempt could not press *Save and go on*:
   the form was 839 px wide on a 412 px screen and the tap landed on the sample text. Fixed in
   `_shell.html` (`fieldset { min-width: 0 }`, `select { max-width: 100% }`), then: 6 samples graded,
   the page reloaded and reopened at the next unfinished sample, 6 more graded, **24 of 24** grades,
   no grade sent twice. The grades are a scripted heuristic, not a person's taste.
4. **The holdout run live.** Job `01M28VGRS546T0XFQ2DSTWP58F`, 10 min 36 s, in scope
   `wr-gym-fwrun-01M28VGRS546T0XFQ2DSTWP58F` with `MemoryHigh=22G MemoryMax=24G MemorySwapMax=0`.
   The page showed `calibration.started` (8 anchors, 4 holdout, one juror) and then one
   `calibration.sample_judged` line per sample as it landed. **The report:** *Not measurable yet*,
   gate not passed, weighted κw 0.000 over **3** held-out samples (4 were judged; the report does not
   say why one is not counted — left for WP6), 8 anchors, judge validity factor 0.400.
   * `dry_wit`: κw 0.000, MAE 3.00, bias −3.00, and *the jury grades harsher than you by 3.0
     points*.
   * `concrete_over_abstract`: κw, ρ and α are `—`, each with its reason.
   * The three worst `dry_wit` disagreements show both rationales.

   The reasons were tooltips on the first screenshot and are written out since the fix (§1).
5. **Stopped.** With `freeweight.service` stopped, the goal list, one goal, the calibration counts and
   the report rendered from FreeWeight's database at `0010`. The grading page said it reads only
   FreeWeight's running API, with its save disabled. The service was started again.
6. **Round trip.** The bundle downloaded (8 584 bytes). *Delete this goal…* previewed *0 run(s)
   … lose their goal, and 24 of your grades are destroyed*, and the goal was deleted with the slug
   typed. Importing the file restored `sha256:b5112a39…`, **the same `goal_hash`**. The preview's
   *0 runs* was wrong: the goal had two runs, both under its earlier hash. FreeWeight now counts
   every hash's runs (§1).

Screenshots of every step in light and dark (`wp4-demo/shots/`, 54 files) are in the session
scratchpad. The first demonstration's were lost with `/tmp` at the reboot.
