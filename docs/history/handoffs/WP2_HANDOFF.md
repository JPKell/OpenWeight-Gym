# WP2 Handoff — application pages II: LoadCoach

**Row:** WP2 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-10/11, attended, one sitting ·
**Model:** Claude Opus 5 · **Kickoff:** `history/prompts/wp2-weightroom-loadcoach-pages.prompt.md`
(arc index `history/prompts/wp-app-pages-arc.prompt.md`)

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| WeightRoom | `88fb45f` | A | The two WP1 defects (figure cards stack in the shell CSS; `_STATUS_FIGURES` reads each application's real `/system/status`, pinned by `tests/fixtures/status/*.json`); LoadCoach's **Models** (scan, enable/disable, warm), **one model**, **Routing** (explain over `POST /route`, decision history, task profiles, one decision, one profile), **Reliability**; the menu keyed per application where FreeWeight shares a label; `AppRefused` carries `app_details` |
| WeightRoom | `16f30b4` | B | **Queue** (the live report as console-rendered htmx SSE regions, pause/resume/drain with a confirmation), **jobs** (list, submit, one job, the event pane, the live reply with the thinking block, cancel, feedback), **Evidence** (by match state, summary, sources, import by upload or FreeWeight pull); `app_api.lines` shared with `promptcadence_pages` |
| LoadCoach | `8825b51` | C | `GET /api/v1/adapters` — api.md edited in `WeightRoom/docs` first and mirrored byte-identical, OpenAPI snapshot regenerated (inside a scratch XDG tree), CHANGELOG |
| WeightRoom | `1cffe1c` | C | **Providers** (save/remove through LoadCoach's `PUT`/`DELETE`, re-authentication, a removal previewed), **Adapters**; `app_side_nav_stubs("loadcoach") == ()`; `_PAGE_ELSEWHERE` keeps only FreeWeight's `Provider` |
| WeightRoom | this commit | docs | This handoff; the row marked done |

Nothing pushed or tagged; no version bump (`wr-gym` stays `1.0.0`, `loadcoach` `1.5.0`; both under
`[Unreleased]`).

**Gates**, both on **Python 3.14.4**, each repository's own `.venv`:

* **WeightRoom** at `1cffe1c`: `ruff format --check .`, `ruff check .`, `mypy src tests` (211 files),
  `lint-imports` (5 kept), `pytest --cov=weightroom` → **1633 passed, 3 skipped** (1556 before the
  row), coverage **90 %** total, held; `routes/loadcoach` 93 %, `loadcoach_pages` 89 %,
  `loadcoach_actions` 83 %, `overview` 94 %. The console's OpenAPI snapshot and `api.md` are
  **unchanged**: every route this row adds is a page or a form post on a `ui_router`.
* **LoadCoach** at `8825b51`: the same five commands with `-m "not live and not performance"` →
  **1110 passed, 5 skipped**.

## 2. Decisions taken

1. **The queue's confirmation says what actually stops** — queued dispatch only. LoadCoach's pause
   and drain flags gate the worker (`services/worker.py`), and `POST /generate` and
   `/generate/stream` never read them. PromptCadence calls `POST /generate`, IdeaPress and the
   console's chat call `/generate/stream`, so none of them waits. The kickoff's sentence and its
   demonstration step 3 assumed otherwise; §5 proves the code's reading live.
2. **An unconfirmed pause, resume or drain writes a `pending` row** and sends nothing (the catalog
   delete's preview precedent, W8). The confirmed post writes the `ok` or `refused` row.
3. **The queue stream is re-rendered here.** LoadCoach's `queue.status` frame carries its own HTML
   beside the report. The console renders `_lc_queue_live.html` from the report and sends that as
   htmx's `sse-swap` data (ADR-0128), with a heartbeat passed through so a closed tab ends the
   proxy. LoadCoach's markup never reaches the DOM (arc index §2 item 4).
4. **The job page uses two connections to one stream**: the log pane (`…/events`, state events as
   lines) and the reply region (`…/reply`, the stream unchanged, `thinking` into the chat's
   thinking block and `token` as text). *Ponytail:* one converted stream would need a pane that
   exposes its `EventSource`; add that if a page ever needs a single connection.
5. **The Submit form mints the idempotency key when the page renders**, so a double click returns
   the first job instead of queueing a second one.
6. **`GET /evidence` records carry no `match_state`** (the payload is the producer's own
   `capability.evidence`). The page reads once per state and labels each record. Staleness shows in
   the summary counts, not per record, while LoadCoach answers.
7. **Adapters: the directory is the truth** (ADR-0061 already decides this, so no new ADR).
   `GET /adapters` starts from `adapter_overview` and joins the `adapters` table only for the row id
   that residency and routing candidates name. Rows the directory no longer describes are listed
   with `in_directory: false`. With no directory it answers `enabled: false` and a note, not an
   error.
8. **Which registration keys re-authenticate** is the console's own set,
   `loadcoach_actions.SECURITY_FIELDS = {kind, base_url, remote}`, plus any new registration and
   any removal. LoadCoach's `config schema --json` names `provider.kind`, `provider.base_url` and
   `providers.allow_remote` but no `providers.<name>.*` key, because a table's name is the
   operator's. The rule is written beside the constant.
9. **Enable/disable reuses `catalog.set_enabled` and its audit action `catalog.enabled`**, as the
   kickoff asked. Its refusal code is the catalog's `CATALOG_REFUSED`, with LoadCoach's message
   inside, not LoadCoach's own code. That is the one refusal on these pages not in the
   application's code.
10. **Menu keys may be `(app, label)`** (`rendering._page_href`). FreeWeight's Models, Evidence and
    Adapters stay WP3's stubs while LoadCoach's are links. `Providers` is keyed by label, because
    only LoadCoach names it.
11. **The task-profile route's parameter is `{task}`**, not `{profile_id}`. The §14 checklist reads
    any parameter containing `file` as a filesystem path.

## 3. The kit, after WP2 (for WPC1, WP3–WP5)

* `app_api.refusal` → `details["app_details"]`: the application's own error `details` (a
  `NO_ELIGIBLE_MODEL` carries its candidates there).
* `app_api.lines(chunks)`: stream text as whole lines, for a page that parses frames itself.
* `routes.apps.back_to(app, next)`: renamed from `_back_to`, the no-open-redirect rule for a
  form's `next`.
* `_shell.html` kit classes: `.kit-inline` (a button beside a heading), `.kit-actions` (a row's small
  forms), `.kit-form` (a collapsible form as a grid, `.kit-wide` spans it), `.kit-check`,
  `.kit-details`, `.kit-output`/`.kit-live` (pre-wrapped model text).
* The confirm-first pattern: post once, render the sentence with a hidden `confirmed=yes`, audit
  `pending`.
* The re-auth pattern for a form: a `password` field, `reauthenticated(request, principal,
  password)`, then `require_fresh_reauth` only when a security key moved. An **open loopback**
  principal is exempt, so a demonstration of re-auth needs an operator account on the console.
* A JSON write from Playwright's request context needs `Origin` **and** `Sec-Fetch-Site:
  same-origin` (the same-origin middleware).

## 4. Parity with LoadCoach's own UI

| LoadCoach UI (`web/routes`, `web/templates`) | Console | Test |
|---|---|---|
| `GET /` dashboard | Overview (W3; figures fixed here) | `unit/test_overview_status_bodies.py` |
| `GET /models`, `POST /models/discover`, `POST /models/{ref}/enabled`, `POST /models/{ref}/warm` | `…/models` with Scan, Enable/Disable, Warm → the job | `test_the_models_page_…`, `test_scan_…`, `test_disable_…`, `test_warm_opens_the_job_…` |
| — (API only) `GET /models/{ref}` | `…/models/{ref}` | `test_one_model_…` |
| `GET /routing`, `GET /routing/{id}` (with the narrative) | `…/routing` (history), `…/routing/decisions/{id}` (candidates, capabilities, rejections by code, the raw document) | `test_routing_lists_…` |
| — (API only) `POST /route` | the explain form on `…/routing` | `test_explain_…`, `test_an_adapter_pin_refused_…`, `test_no_eligible_model_…` |
| `GET /task-profiles` | on `…/routing`, and `…/routing/task-profiles/{task}` | `test_routing_lists_…` |
| `GET /queue` with its live region, `POST /queue/pause|resume|drain` | `…/queue`, live over `…/queue/stream`, confirmed controls | `test_pause_asks_first_…`, `test_resume_and_drain_…`, `test_the_queue_stream_…` |
| `GET /jobs` (filters, cursor) | the Jobs section of `…/queue` | `test_the_queue_page_…`, `test_a_stopped_queue_…` |
| `GET /jobs/{id}`, `/jobs/{id}/log` | `…/queue/jobs/{id}`, `…/events` (pane), `…/reply` (thinking and tokens) | `test_a_job_page_…`, `test_a_jobs_stream_…`, `test_the_reply_stream_…` |
| — (API only) `POST /jobs`, cancel, feedback | Submit form, Cancel, Give feedback | `test_submit_…`, `test_cancel_and_feedback_…` |
| `GET /evidence` (Benchmarks: coverage, records, sources) | `…/evidence` (summary, records by match state, sources) | `test_evidence_reads_…` |
| — (API/CLI only) `POST /evidence/import` | Import: an uploaded bundle, or the FreeWeight pull | `test_import_uploads_…`, `test_the_pull_sends_…` |
| `GET /reliability?task&model` | `…/reliability` | `test_reliability_shows_…` |
| `GET /providers`, `POST /providers` | `…/providers` with re-auth and the removal preview | `test_loadcoach_providers_adapters.py` |
| — (CLI only) `loadcoach adapters list` | `…/adapters` over the new `GET /adapters` | the same file; LoadCoach `test_adapters_api.py` |
| `GET /settings` | Settings (W4) | existing |
| `GET /system` (health components, recovery) | **no console page** | — |
| `/access` (the token-cookie page) | not applicable: the console holds the token | — |

**Not at parity:** LoadCoach's *coverage per capability* table on its Benchmarks page (the API
serves no coverage view; the records and summary are shown instead), and its routing *narrative*
("why this model", computed by `domain/routing/narrative.py`). The console renders the stored
explanation's numbers rather than re-implementing that narrative. LoadCoach's **System** page, like
PromptCadence's before WPC1, has no menu entry in spec §7.3; WP6 should judge both.

## 5. Demonstration on the reference machine

A **throwaway** console (`https://127.0.0.1:8779`, its own XDG tree in the session scratchpad, an
operator account `demo` so re-authentication applies, the operator's LoadCoach and PromptCadence
token files read in place), driven with Playwright and the system Chrome. The operator's
`weightroom.service` was not touched. `loadcoach.service` was restarted once, after `8825b51`, to
serve `GET /adapters`.

1. **Scan, then warm.** *Scanned: 0 added, 11 updated, 0 unavailable, 11 in the registry.* Warm on
   `ollama/smollm2:135m` opened job `01M27EHB6RQW36ZD8C7YF4JA21`: admitted → completed in 1.8 s,
   output *Ready.*, the event pane showing `job.queued` → `job.completed`. It is listed on the Queue
   page, and the model is resident on GPU 0.
2. **Explain with an adapter override** (`general.chat`, adapter `fact-check`):
   `ADAPTER_NOT_FOUND` — *no adapter named 'fact-check' is registered on any provider … adapters
   available here: none* — rendered with *Adapters LoadCoach holds: none.* Without the override: 10
   rejections rendered by code (`insufficient_vram` among them).
3. **Pause.** The confirmation said what stops. Paused, a job submitted from the page
   (`01M27EMD3CGVP1BPDBMVP6Z5RB`, created 05:21:48Z) stayed `queued`. A chat message from the
   console, sent while still paused, was answered at once: its synchronous job
   `01M27EMKHQG0RZ7EM3BKHJ65NY` started and completed at 05:21:55Z (60 ms), conversation
   `01M27EMKGZH9W7KF16NGVWNP75`. **So the kickoff's "a chat message waits" is false, as §2 item 1
   read from the code.** Resumed (confirmed): the queued job started at 05:23:57Z and completed.
4. **Evidence imported from FreeWeight** (the console's `http://127.0.0.1:8765`): *7 new, 0 updated,
   7 bound, 0 unmatched, 0 ambiguous, 0 superseded, 0 rejected* — source
   `freeweight:27da645d…`. **This is live routing evidence on the operator's LoadCoach now.**
5. **Providers.** `~/.config/loadcoach/` held **no** `config.toml` before (LoadCoach ran on defaults).
   Saving `timeout_seconds` 300 → 301 without a password made LoadCoach write:
   ```toml
   [providers.ollama]
   kind = "ollama"
   base_url = "http://127.0.0.1:11434"
   timeout_seconds = 301.0
   remote = false
   server_path = "llama-server"
   ```
   `base_url` → `http://localhost:11434` without the password: `REAUTH_REQUIRED`, nothing sent.
   With the password it saved, and the file changed by exactly
   `-base_url = "http://127.0.0.1:11434"` / `+base_url = "http://localhost:11434"`. Both keys were
   then reverted through the page (the password again).
6. **Stopped.** `systemctl --user stop loadcoach.service`, then every page, both themes: each
   answered `200`. Models, one model, Routing, a decision, a task profile, Reliability, the jobs
   list, a job, Evidence and Adapters read *from the database at revision 0015*; the queue report
   and Providers said they read only from the running API; each carried the notice with **Start**.
   Started again, `active`.

Screenshots of every LoadCoach page, the Overview and PromptCadence's Ledger in both themes, running
and stopped, and of every action step, are in the session scratchpad (`wp2-demo/shots/`, 73 PNGs);
they go with the session.

**Not demonstrated live:** an adapter with data on the Adapters page (the reference machine's
LoadCoach has no `[adapters] directory`; the page shows *Adapters are off* and its note), a removal
of a registration (only one exists and LoadCoach refuses to remove the last), and feedback and
cancel on a live job (tests only).

## 6. What the kickoff got wrong

* **"Show that a chat message from WeightRoomGym waits"** while paused, and a confirmation saying
  **"PromptCadence and IdeaPress route through this queue"**: all three generate synchronously, and
  the flags gate only queued dispatch (§2 item 1, §5 step 3).
* **"The explain form … and the classification"**: `POST /route` has no `data_classification`
  (`RouteBody` forbids extra keys); only `/generate` and `/jobs` take one.
* **"Secrets are `api_key_env`/`api_key_file` references only"**: a LoadCoach registration has no
  secret field at all (`WRITABLE_FIELDS`); the page states that none is shown.
* **"A security-relevant key re-authenticates"**: LoadCoach's schema marks no registration key; the
  console's mapping is §2 item 8.
* **Adapters' "pinned/resident state"**: residency records the adapter a resident base last served;
  LoadCoach keeps no separate pin. The page shows resident devices and the routes that pinned or
  refused it.
* **"The decision history comes from the API"**: it does, from `GET /routing-decisions`, which
  LoadCoach serves but its `api.md` §3 does not list. The console uses it; the doc gap is left for
  a LoadCoach docs pass.
* **"`EXERCISES`, the §14 registry, the OpenAPI snapshot and `api.md` updated"**: the first two are;
  the console's snapshot and `api.md` have nothing to change (UI routes only).
* **"Reuse W8's catalog call"** makes enable/disable the one page action whose refusal code is not
  LoadCoach's (§2 item 9).
* **Gate A's "read and act … against the LoadCoach fixture database"**: `loadcoach-0015` holds no
  rows; the stopped tests add theirs.

## 7. For the operator

1. **Restart `weightroom.service`** to serve these pages (it runs this checkout's editable install).
   WPC1 does this at its end.
2. **Left on the reference machine:** 7 imported evidence records in LoadCoach; `smollm2:135m`
   resident; jobs `01M27EHB6RQW36ZD8C7YF4JA21` (warm), `01M27EJMMQ6TCCJJZW336J2BGV`,
   `01M27EMD3CGVP1BPDBMVP6Z5RB` (submitted), `01M27EMKHQG0RZ7EM3BKHJ65NY` (chat) and the routing
   decisions of the explains in LoadCoach's database. `loadcoach.service` was restarted once and
   stopped/started once.
3. **Two things went wrong during the demonstration, both repaired:**
   (a) the first run of step 3 crashed after pausing (the chat call lacked `Sec-Fetch-Site`), which
   left **LoadCoach's queue paused** with job `01M27EJMMQ6TCCJJZW336J2BGV` waiting. It was resumed at
   once through LoadCoach's own `POST /queue/resume` with the console's token; that resume is in
   LoadCoach's log but **has no console audit row**. The job completed.
   (b) After step 5, `~/.config/loadcoach/config.toml` and `config.toml.bak` existed only because the
   demonstration created them. Both were printed, holding only the demonstration's own values, and
   removed, so LoadCoach is back on defaults. **The shell guard meant to check their content before
   removal had a broken regular expression and did not run**, so the removal rested on the printed
   content alone. `GET /providers` after the restart shows `config_digest ""` and the default
   `ollama` registration.
4. **Stopping `loadcoach.service` hit systemd's stop timeout** (`unit failed (timeout)`), which
   raised an *application down* alert on the throwaway console; start was clean. It is worth
   knowing why LoadCoach's shutdown exceeds `TimeoutStopSec` (a row candidate, not investigated).
5. **Polish seen in the screenshots, not this row's:** a refusal renders in WP1's `.notice` box with
   the success-green border; the stopped footer names the application in lower case (*loadcoach is
   not answering*); the Models table's last column needs a horizontal scroll at 1440 px.
6. The throwaway console is still running on `:8779` for WPC1's demonstration.

## 8. What runs next

WPC1 (`history/prompts/wpc1-promptcadence-api-gaps-system-page.prompt.md`) on this kit, then WP3.
