# WP3 Handoff — application pages III: FreeWeight measurement

**Row:** WP3 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended, beside WP5 under the
parallel-row rules (§3) · **Model:** Claude Opus 5 · **Kickoff:**
`history/prompts/wp3-weightroom-freeweight-pages.prompt.md` (arc index
`history/prompts/wp-app-pages-arc.prompt.md`) · **Branch:** `row/wp3-freeweight-pages` at
`~/ai/worktrees/weightroom-wp3`, not merged

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| WeightRoom | `038fc42` | C (first) | `apps/freeweight/api.md`: the models list's `has_results`/`sort`, `POST /models/{ref}/enabled` as JSON, a new §2a Adapters, runs filters and cursor, the samples cursor, `GET /runs/{id}/telemetry`, `GET /samples/{id}`, the results `adapter` filter. Edited here first, then mirrored byte-identical |
| FreeWeight | `989e5a7` | C (first) | The read surface the pages need: `list_runs` filters and a `(created_at, id)` cursor, the samples cursor, `RunSummary` machine/profile/adapter, `GET /runs/{id}/telemetry`, `GET /samples/{id}`, `GET /adapters` (`services/adapters.adapter_catalog`), the JSON `POST /models/{ref}/enabled`, the models `has_results`/`sort` and the fixed `family` filter, `ResultsQuery.adapter`. OpenAPI snapshot regenerated in a scratch XDG tree; CHANGELOG |
| WeightRoom | `0401de1` | A | **Models** (list, Refresh from provider, Enable/Disable through W8's catalog, one model with its descriptor history, evidence and paginated results), **Runs** (filters, cursor, Start as the capped `freeweight_suite_run` job, *Starting* page that follows the run, one run with tests, metrics, degradations, telemetry charts, fingerprint document and the live event pane, Cancel, Repeat with force and label), test samples and the case inspector. `app_api.download`; the job kind takes `label` |
| WeightRoom | `ca13a87` | B | **Results** (the metric query, Compare, Export streamed), **Evidence** (records, `user.*` fields, the bundle download), **Machines** (list and detail, linked from runs, run, model and results) |
| WeightRoom | `8cc25ca` | C | **Adapters** (list and one adapter beside its bare base), **Provider** (`GET`/`PUT /provider` with re-auth), FreeWeight's own figures on the Database page, `_PAGE_ELSEWHERE` deleted, the `link` macro, stubs reduced to Goals |
| WeightRoom | `579f2ab` | demo fix | A job's output reaches its row while the child is quiet (§2 item 3); a running run's page reloads when its stream ends |
| WeightRoom | this commit | docs | This handoff; the row marked done |

Nothing pushed or tagged; no version bump (`wr-gym` stays `1.0.0`, `freeweight` `1.2.1`; both
under `[Unreleased]`).

**Gates**, both on **Python 3.14.4**:

* **WeightRoom** at `579f2ab`, `~/ai/suite/WeightRoom/.venv` with `PYTHONPATH=$PWD/src` in the
  worktree: `ruff format --check .` (223 files), `ruff check .`, `mypy src tests` (217 files),
  `lint-imports` (5 kept, 0 broken), `pytest --cov=weightroom` → **1713 passed, 3 skipped**
  (1638 before the row), coverage **90 %** total, held; `routes/freeweight` 94 %,
  `freeweight_pages` 92 %, `freeweight_actions` 93 %, `services/jobs` 89 %. Per gate: A 1674,
  B 1690, C 1711.
* **FreeWeight** at `989e5a7`, its own `.venv`: the same five commands with
  `-m "not live and not performance"`, in random order → **2704 passed, 30 skipped**, coverage
  **89.26 %** (floor 85), mypy 324 files, 4 contracts kept.

The console's own OpenAPI snapshot and `api.md` are **unchanged**: every route this row adds is a
page, a download or a form post on a `ui_router`. `EXERCISES` gained the six FreeWeight form posts;
`SPEC_14_ROWS` gained the provider re-auth tests and the three inert-text tests.

## 2. Decisions taken

1. **Enable/disable needed a FreeWeight API route.** W8's catalog posts JSON to
   `POST /api/v1/models/{ref}/enabled`. FreeWeight served that path only as an HTML form route, so
   **the catalog's FreeWeight switch had never worked** (404 live). The kickoff says "a form field,
   not a JSON body". A form post cannot reach `/api/v1`: MirrorWall's `CsrfMiddleware` exempts only
   JSON bodies. So `989e5a7` adds the JSON route `{"enabled": bool}` → `{"canonical_id","enabled"}`,
   and the console reuses `catalog.set_enabled` and its audit action `catalog.enabled`.
2. **Repeat stays an API call, because it runs capped.** On the reference machine,
   `systemctl --user show freeweight.service` reports `MemoryHigh=22G`, `MemoryMax=24G` and
   `MemorySwapMax=0`. `POST /runs/{id}/repeat` enqueues the repeat on FreeWeight's in-process
   `RunScheduler` inside `freeweight serve`, so it executes in that unit's cgroup. An Ollama model
   load happens in `ollama.service`, which carries the same caps. A `llama-server` that FreeWeight
   starts for a `llamacpp` provider is its child, so it is inside the same cgroup. **Answer: yes,
   it runs capped. It is not sent through the job kind.** Start *is* the job, as decided: a run
   started by `freeweight run start` runs in the CLI process, which the job wraps in
   `systemd-run --user --scope -p MemoryHigh=22G -p MemoryMax=24G -p MemorySwapMax=0` (shown in the
   job output live, §5 step 1).
3. **A started run is followed from the job's output.** `POST …/runs` enqueues the job and redirects
   to `…/runs/starting/{job_id}`. htmx polls that page every 2 s. Once `run_id_in(job.output)` finds
   the id, the route answers `HX-Redirect` (or `303` without htmx) to the run. The demonstration
   found that the id reached the row only at the run's end. `OutputBuffer` flushed only when a new
   line arrived, and `freeweight run start --json` prints the id and then stays silent. Fixed at the
   root in `services/jobs.py` (`flush_due` between polls, `579f2ab`), with a test using a real child.
   It also fixes the Jobs page's live output for every quiet child.
4. **The event stream keeps FreeWeight's sequence.** FreeWeight's frames carry `payload.sequence`.
   The console re-emits them as log-pane frames with that sequence as the SSE `id`, and it passes
   `Last-Event-ID` through, so a dropped stream resumes where it stopped. A terminal event
   (`run.completed|failed|cancelled|interrupted`) ends the pane. FreeWeight's own page keeps its
   badge current with `runs.js`. The console's page reloads once when a non-terminal run's stream
   ends (`579f2ab`).
5. **Sources while FreeWeight is stopped** (spec §7.3). Models, one model, runs, one run (with its
   stored events instead of the pane), samples, the case inspector, machines, one machine, adapters
   and one adapter read FreeWeight's database at revision `0010`. Results, Compare, Evidence and
   Provider say they "read only from its running API". Those pages are FreeWeight's own
   computations: the comparability grouping, `status=any` aggregation, and evidence staleness.
   Re-implementing them from rows would be a second copy that can disagree. The runs list in
   database mode ignores `since`/`until`.
6. **A stopped FreeWeight is never called for a download.** `_unanswered` refuses Export and the
   evidence bundle with `APP_UNREACHABLE` before any request. A Gate B test without it reached the
   operator's live FreeWeight on `:8765` (a read-only CSV; nothing written). The test now runs
   under respx.
7. **`runtime_hash` on the console, `runtime_profile` on FreeWeight.** The §14 checklist refuses any
   route parameter containing `file`, and `runtime_profile` contains it. The console maps the name
   back in `_console_names`.
8. **Adapters.** FreeWeight had no adapters endpoint, so `989e5a7` adds `GET /adapters`. It returns
   the directory as FreeWeight reads it (`enabled`, `directory`, `note`, `invalid`, `drafts`,
   `unmanifested`) and every adapter by digest, with `in_directory`, `run_count`, `last_run_at` and
   its subjects (`base`, `subject`, `measured`, `base_measured`). One adapter's page sets the
   adapter's results beside the bare base's and gives each delta, and lists its runs and results
   (`?adapter=`, `status=any`). **No canary verdict is stored anywhere.** The base-only canary is a
   live test (`test_the_panel_still_separates_a_known_damaged_adapter`, H6). The page names that
   test and shows the deltas it would judge. It does not show a pass/fail FreeWeight never
   recorded.
9. **Provider re-auth.** `freeweight_actions.SECURITY_FIELDS = {kind, base_url}`, the console's own
   set. FreeWeight's schema marks none, as with LoadCoach in WP2. The `PUT` carries `base_digest`,
   so a file changed underneath is FreeWeight's refusal, rendered as itself.
10. **Machines have no menu entry.** They are reached from Results' header, every run and model
    page, and a fingerprint link (`…/machines?fingerprint=`). Spec §7.3 is unchanged.
11. **The Database page's gap was FreeWeight's own statistics only.** Backup, vacuum, upgrade,
    restore and FreeWeight's previewed results deletion were already there (W7, ADR-0134). This row
    adds FreeWeight's `GET /database/stats` section (backups, artifacts, integrity) while it answers.
    A stopped FreeWeight is not called.
12. **Markup in a table cell goes through the `link` macro.** `'<a…' ~ (x | e) ~ '</a>' | safe` escapes
    the whole string, so the adapters link rendered as text. Elsewhere, a fingerprint and a run id
    sat unescaped inside `| safe`. `_fw.html`'s `link(href, text, class_, title)` replaces every
    such concatenation, pinned by `test_an_adapters_name_and_a_machines_fingerprint_render_inert`.
13. **Evidence shows what the API serves.** `GET /evidence` carries the `user.*` fields (`goal_hash`,
    `judge_set`, `calibration`, `judge_validity_factor`). It does not carry the staleness state or
    the six confidence factors FreeWeight's own evidence page computes. The page says so rather than
    recomputing them.

## 3. Parity with FreeWeight's own UI

| FreeWeight UI (`web/routes`, `web/templates`) | Console (`/apps/freeweight/…`) | Test |
|---|---|---|
| `GET /models`, `POST /models/discover`, `POST /models/{ref}/enabled` | `models` with Refresh from provider (counts), Enable/Disable | `test_the_models_page_…`, `test_refresh_shows_freeweights_counts_…`, `test_disable_is_the_catalogs_call_…` |
| `GET /models/{ref}` | `models/{ref}`: identity, descriptor history, evidence, results by suite and runtime profile with a cursor | `test_one_model_shows_its_descriptor_evidence_and_results_…` |
| `GET /runs`, `POST /runs` | `runs` with status/model/suite/machine/label/date filters and cursor; Start → the job → `runs/starting/{job}` | `test_the_runs_page_…`, `test_the_runs_pager_…`, `test_start_enqueues_the_capped_suite_run_job_…`, `test_a_start_the_queue_refuses_…` |
| `GET /runs/{id}`, `/runs/{id}/log`, `POST /runs/{id}/cancel`, repeat (API) | `runs/{id}` (tests, metrics, degradations, telemetry, fingerprint document, live pane), `…/events`, Cancel, Repeat | `test_one_run_shows_…`, `test_a_running_run_reloads_…`, `test_the_event_stream_keeps_freeweights_sequence_…`, `test_a_refused_event_stream_…`, `test_cancelling_…` ×2, `test_repeat_sends_force_and_label_…`, `test_a_refused_repeat_names_every_blocker_…` |
| `GET /runs/{id}/tests/{test}` | `runs/{id}/tests/{test}` (cursor) | `test_a_tests_samples_page_by_freeweights_cursor` |
| `GET /results/samples/{id}` | `samples/{id}` | `test_the_case_inspector_renders_model_and_juror_text_inert` |
| `GET /results` | `results` with every filter and the cursor | `test_results_read_freeweights_metric_query_…` |
| `GET /compare` | `results/compare`: verdicts, reasons, separating fields; a refusal with the offending runs | `test_compare_renders_each_verdict_…`, `test_a_refused_comparison_states_its_reason_…`, `test_compare_with_no_subjects_asks_…`, `test_labels_on_a_comparison_render_inert` |
| export (API and CLI) | `results/export`, streamed with FreeWeight's headers; the 500-run refusal as itself | `test_the_export_streams_through_…`, `test_the_export_leaves_unticked_options_…`, `test_the_500_run_refusal_renders_as_itself_…` |
| `GET /evidence`, the bundle (API) | `evidence`, `evidence/export` | `test_evidence_shows_each_record_and_a_user_records_…`, `test_the_evidence_bundle_downloads_…` |
| `GET /machines` | `machines`, `machines/{id}` with its runs | `test_machines_list_and_one_machine_…` |
| — (CLI only) adapters | `adapters`, `adapters/{name or digest}` over the new `GET /adapters` | `test_adapters_list_…`, `test_adapters_off_says_which_key_…`, `test_one_adapter_sets_its_scores_beside_the_bare_bases_…`, `test_an_adapter_by_its_digest_…`; FreeWeight `test_adapter_catalog.py` |
| `GET`/`POST /provider` | `provider` with re-auth | `test_the_provider_page_…` and seven more in `test_freeweight_adapters_provider.py` |
| `GET /database` (stats, preview/delete, backup, vacuum) | Database (W7) plus FreeWeight's own statistics | `test_the_database_page_adds_freeweights_backups_…`, `test_a_stopped_freeweights_database_page_…` |
| `GET /settings` | Settings (W4) | existing |
| stopped, every page above | database at `0010`, or "reads only from its running API", with Start | `test_stopped_pages_read_the_database_…`, `test_stopped_results_evidence_and_compare_…`, `test_a_stopped_freeweights_adapters_…`, `test_a_stopped_freeweights_provider_page_…` |
| `GET /dashboard` (charts by suite, model, machine, since) | **no console page**; the Overview (W3) carries FreeWeight's status figures only | — |
| `GET /sources` (external benchmarks credited with licences) | **no console page** | — |
| `GET /system` (health, telemetry stream) | **no console page**; the console header's meters cover the host | — |
| `goals`, `grading`, `GET /results/goals/{slug}` | WP4 (the one remaining stub) | `test_no_freeweight_page_is_a_stub_but_goals` |

**Not at parity:** FreeWeight's Dashboard, Sources and System pages have no home in spec §7.3.
LoadCoach's and PromptCadence's System pages were in the same position (WP2 §4). WP6 should judge
all of them. Evidence's staleness and confidence factors are not on the API (§2 item 13). While
FreeWeight is stopped, Results, Compare, Evidence and Provider do not read its database (§2
item 5).

## 4. What the kickoff got wrong

* **"Enable/disable reuses W8's catalog call (a form field, not a JSON body, on FreeWeight)."**
  W8's call is JSON, it had no FreeWeight route to reach (404), and a form field cannot cross
  `/api/v1`'s CSRF check. The fix is a JSON API route (§2 item 1).
* **"The page then follows the run FreeWeight reports"** could not work for any run longer than the
  output flush. The job buffer held the run id until the child printed again or exited (§2 item 3).
* **"FreeWeight serves no adapters endpoint. Adapters are in `runtime_profiles`
  (`adapters_registered`) … whether the base-only canary passed."** The first half is right, and the
  route was added. There is no stored canary result to show (§2 item 8).
* **"`EXERCISES`, the §14 registry, the OpenAPI snapshot and `api.md` updated."** The first two are.
  The console's snapshot and `api.md` have nothing to change. FreeWeight's `api.md` and snapshot
  changed instead.
* **The parity target lists `sources`, `system` and `dashboard`** without a place for them in the
  console's menu (§3).
* **"Evidence … `user.*` records with … `judge_validity_factor`"** is right, but FreeWeight's own
  Evidence page shows staleness and confidence factors the API does not serve.
* **"Demonstrate 5. Open an adapter's page and its results."** The reference machine's FreeWeight
  has no `[adapters] directory`, so only *Adapters are off* can be shown live (§5).
* **"Compare two models."** Compare takes runs, or model references with a suite (each model's
  latest completed run). The demonstration used one run per model.
* **Unstated:** FreeWeight's models list `family` filter matched nothing. It was fixed in `989e5a7`.

## 5. Demonstration on the reference machine

A **throwaway** console (`https://127.0.0.1:8779`, its own XDG tree in the session scratchpad,
open loopback, the operator's LoadCoach and PromptCadence token files read in place), driven with
Playwright and the system Chrome. The operator's `weightroom.service` was not touched. The
operator chose to run the live suite run before WP5's live stage run. Ollama had no model loaded
and no `llama-server` was running beforehand.

1. **Scan, then start a run and follow it live.** *Refreshed from the provider: 0 added, 0 updated,
   11 unchanged, 11 in all.* Start `native.echo` on `ollama/smollm2:135m@sha256:9077fe9d2ae1`,
   label *wp3 demonstration*:
   * **First attempt:** job `01M27MF9CKYCTEF8BEFPXMY54A`, run `01M27MFA104BJEXPGW6SP4Z8VD`,
     completed in 15 s. The job output shows the scope
     `wr-gym-fwrun-01M27MF9… -p MemoryHigh=22G -p MemoryMax=24G -p MemorySwapMax=0`. The Starting
     page moved to the run only at 07:04:08.8, after the run had finished, which exposed §2 item 3.
     A second fault was the demonstration script's own: `time.sleep` with `page.url` never sees a
     navigation in Playwright's sync API.
   * **After the fix** (console restarted): job `01M27MSK2QQA3YEF0SG8AWVAHQ`, run
     `01M27MSKR6EPKF8Y4KP81Q7D7Q`, followed **2.0 s** after the start while it was still
     *preparing*. The pane streamed 22 events live (`run.started`, 15 `sample.completed`,
     `test.*`, `run.completed`) and ended. The header still said *preparing* until a manual reload,
     so the reload hook was added.
   * **Final run:** run `01M27N0XGKH7YG3MPZYCP37QNQ`, followed after 2.0 s. At `run.completed` the
     page reloaded by itself to *completed*, with two tests, ten metrics and six telemetry charts.
     Ollama still had `smollm2:135m` resident from the previous run, the same model, and nothing
     else was loaded.
2. **A sample:** `samples/01M26MTM5XS87ZJPG7PE51BQVH`, case `prompt-128` of
   `performance.prompt_processing`: prompt `benchmarks.performance.probe` 1.0.0 by hash, response
   not stored (its hash shown), rule score 1, 146 in / 73 out tokens, 170.4 ms.
3. **Compare:** `01M26MTEM1…` (`smollm2:135m`) and `01M22D3SAJ…` (`gemma3:latest`) under
   `native.performance`: *unrelated*, verdict *indeterminate*, "Different identities and no shared
   model family", provenance differing on 9 fields, every metric in its own group. **Refused:**
   `01M26MTEM1…` with `01M22J6XV0…` gave `COMPARISON_REFUSED`, *Every subject must be a run of
   'native.performance'; 1 of 2 are not.*, with the offending run and its suite
   `native.memory_kv` in a table.
4. **Export a run as CSV:** `200`, `text/csv; charset=utf-8`,
   `attachment; filename="freeweight-run.csv"`, 12 807 bytes, header
   `run_id,label,model_canonical_id,suite_key,…,coefficient_of_variation`.
5. **Adapters:** *Adapters are off. adapters are not configured: set [adapters] directory …* and
   *No adapter in the directory, and none measured under.* One adapter's page with data is shown
   only by tests.
6. **Stopped:** `systemctl --user stop freeweight.service`, then every page in both themes. Each
   answered `200`. The sources were as in §2 item 5, the database page rendered without FreeWeight's
   section, and each page carried the notice with **Start**. Started again: `active`, `/version`
   1.2.1.

Screenshots of every FreeWeight page running and stopped, in light and dark (60), and of the
action steps, are in the session scratchpad (`wp3-demo/shots/`). They go with the session.

**Not demonstrated live:** cancel and repeat (a 15 s run leaves no time to cancel, and repeat would
be a fourth live run; tests only), Enable/Disable, a Provider save with re-auth (open loopback is
exempt, WP2 §3), an adapter with data, and the 500-run export refusal (tests only).

## 6. For the operator

1. **Restart `weightroom.service` only after the merge** (§3 rule). `freeweight.service` already
   serves `989e5a7`: it answered `GET /adapters` throughout.
2. **Merge.** Whichever of WP3 and WP5 finishes second merges `main` in. It keeps both rows' entries
   in `rendering.py`, the §14 registry, `CHANGELOG.md` and the roadmap, and regenerates the OpenAPI
   snapshot and `api.md` in a scratch XDG tree. WP3 touched `rendering.py` (`_PAGE_HREF`,
   `_PAGE_PHASE`, `_PAGE_ELSEWHERE` deleted), `test_audit_routes.py`, `test_checklist.py`,
   `routes/databases.py`, `database.html`, `routes/jobs.py` (`_enqueue` → `enqueue_job`),
   `services/jobs.py` and `services/job_kinds.py` (`_run_id` → `run_id_in`).
3. **Left on the reference machine:** three `native.echo` runs labelled *wp3 demonstration* in
   FreeWeight's database (`01M27MFA…`, `01M27MSK…`, `01M27N0X…`); `smollm2:135m` resident in Ollama
   until its keep-alive ends; `freeweight.service` stopped and started once. The jobs are in the
   throwaway console's database only, which is stopped at the end of this session.
4. **Not this row's, seen in passing:** two failed transient scopes in the user manager,
   `run-p119078-i133784.scope` and `run-p119326-i137042.scope`
   (`llama-server --model …/bge-m3-q4_k_m.gguf --port 8180`). **Investigated read-only after the
   row:**
   * **Not WP5's and not IdeaPress's.** Both scopes started on **2026-09-09 at 12:22:38 and
     12:22:54 PDT**, the day of the memory incident, and two days before WP5.
   * **Killed on start.** Each was a `systemd-run --user --scope` with `MemoryMax=64M` and
     `MemoryHigh=infinity`. So it was not the suite's cap wrapper, which sets `MemoryHigh`. The
     kernel OOM killer stopped each the moment it started (`Failed with result 'oom-kill'`). 64 M is
     the kill-proof cap from `MEMORY_SAFETY.md` §2.3, far below a 0.4 GB model.
   * **Launcher not found.** The binary is `~/.local/bin/llama-server`, a link to
     `~/ai/tools/llama.cpp/build/bin/llama-server`. The model file was downloaded at 00:05 that day.
     No suite document, no Claude transcript kept for this workspace and no `~/.openclaw` or
     `~/.config` file names that command line, so it was typed by hand or started by a tool outside
     the suite.
   * **Harmless.** Nothing is running and the units hold no cgroup. They are records only, and
     `systemctl --user reset-failed` clears them.
5. **Polish seen in the screenshots, not changed here (WP1's kit):** a refusal still renders in the
   success-green `.notice` box. A refused comparison's footer says *The API did not answer this
   page: freeweight refused …*, although the API answered with a refusal. The stopped footer names
   the application in lower case. The Results page's Export form stacks every field full width.
6. FreeWeight `989e5a7` is unpushed. Its CHANGELOG carries the entries under `[Unreleased]`.

## 7. The operator's decisions (interviewed 2026-09-11, after the row)

1. **Merge now.** WP3 finished first, so it was merged into `main` at `c1c9ba6` (`--no-ff`) and
   `weightroom.service` was restarted. WP5 merges `main` in under §3's rules.
2. **Keep the three demonstration runs** in FreeWeight's database. They are genuine measurements.
3. **Pages with no console home go to WP6**: FreeWeight's Dashboard, Sources and System, and
   LoadCoach's System. They are written into WP6's kickoff.
4. **Adapters are turned on in a later row.** WP6's parity run sets FreeWeight's
   `[adapters] directory` to `~/ai/models/adapters/llm`, measures one adapter beside its base and
   reads its page.
5. **Evidence staleness and confidence factors go on FreeWeight's API.** This is placed in WP4's
   Gate A, not WP6, because WP6 ships no code.
6. **Stopped reads stay API-only** for Results, Compare, Evidence and Provider (§2 item 5).
7. **WP4 fixes the kit polish of §6 item 5** as it builds the goal pages. This is written into
   WP4's kickoff.
8. **The failed scopes of §6 item 4 were investigated** (read-only). See that item.

## 8. What runs next

WP4 (FreeWeight Goals) from `main` once WP3 is merged. Its calibration run reuses this row's run
event proxy (`routes/freeweight.run_events`, `freeweight_pages.run_log_frames`) and the
start-as-job follow (§2 item 3).
