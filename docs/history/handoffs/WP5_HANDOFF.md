# WP5 Handoff — application pages V: IdeaPress

**Row:** WP5 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-10/11, attended, beside WP3 ·
**Model:** Claude Opus 5 · **Kickoff:** `history/prompts/wp5-weightroom-ideapress-pages.prompt.md`
(arc index `history/prompts/wp-app-pages-arc.prompt.md`) · **Branch:** `row/wp5-ideapress-pages` at
`~/ai/worktrees/weightroom-wp5`, **not merged** (§7).

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| IdeaPress | `7ad4ca6` | A (operator decision, §2 item 1) | **Revise runs a revision; a stage run's overrides apply.** Revise is its own stage body (`committed`/`paused` → `revising`, the instructions carried to the reviser as a finding in a round that counts against the limit, then the draft path's review and commit, shared as `_review_and_commit`); `overrides.model_hint`, `max_revision_rounds` and `instructions` apply to their run alone, and a key the stage does not read is `400 VALIDATION_ERROR` naming `overrides.<key>` |
| IdeaPress | `11df015` | A | `GET /projects/{id}` carries `plan`, `units`, `stages`, `running_task_id`; `GET /projects` pages by `cursor` |
| IdeaPress | `5bf4fe6` | A | `GET /projects/{id}/plan`, `POST /projects/{id}/plan/edits` |
| IdeaPress | `70c7537` | A | `GET /projects/{id}/research`, each tool call with its `invocation_id` and egress decision |
| IdeaPress | `1475a83` | A | `GET /projects/{id}/workspace?unit=&compare=` |
| IdeaPress | `0be94ba` | A | `GET …/units/{key}/history`: each version with the run that produced it |
| IdeaPress | `9440b25` | A | `DELETE /projects/{id}?confirm=true&archive=true` archives first; `GET /export/formats` gains `description` |
| IdeaPress | `8a39727` | A | `GET /projects/{id}/units`: `coverage` and `last_validation` |
| WeightRoom | `ef1cb4e`, `37d0da1` | A | `apps/ideapress/api.md` §2–§4, edited on the branch first and mirrored byte-identical into IdeaPress with each commit above |
| WeightRoom | `18f4e3b` | B | **Projects** (list, create, one project, edit, delete with IdeaPress's preview and archive-first), **Workflows**, **Backends** (with the round-trip test); `services/ideapress_pages.py`, `services/ideapress_actions.py`, `web/routes/ideapress.py`; fixtures recorded from IdeaPress's own application (§3 item 9) |
| WeightRoom | `cf2da17` | C | **Plan** (with its edits and **research**), **stage runs** (run form, the run's page, the proxied task stream, cancel), **Units** and **one unit** (revise, resume), **Workspace**, **Export** (write, download); `app_api.text`; `app_side_nav_stubs("ideapress") == ()` |
| WeightRoom | `d44363d` | demonstration | The audit rows for revise and resume name the unit `unit`; `unit_key` was masked by the redaction (§5) |
| WeightRoom | this commit | docs | This handoff; the row marked done |

Nothing pushed or tagged; no version bump (IdeaPress stays `1.5.0`, `wr-gym` `1.0.0`; both under
`[Unreleased]`).

**Gates:**

* **IdeaPress** at `8a39727`, `.venv` **Python 3.13.15**: `ruff format --check .`, `ruff check .`,
  `mypy src tests` (216 files), `lint-imports` (4 kept), `pytest -m "not live and not performance"`
  → **1335 passed, 6 skipped**; with `--cov=ideapress` at `9440b25` **91 %** (1334 passed). The OpenAPI
  snapshot was regenerated inside a scratch XDG tree at each commit that moved it; `api.md` mirrors are
  `cmp`-identical.
* **WeightRoom** at `cf2da17`, and again at `d44363d` (worktree, `~/ai/suite/WeightRoom/.venv` with
  `PYTHONPATH=$PWD/src`), **Python 3.14.4**: the same five commands → **1706 passed, 3 skipped**,
  coverage **90 %** (at `cf2da17`), held
  (`ideapress_pages` 91 %, `ideapress_actions` 94 %, `routes/ideapress` 91 %, `app_api` 90 %). The
  console's OpenAPI snapshot and `api.md` are **unchanged**: every route this row adds is a page or a
  form post on a `ui_router`.

## 2. Decisions taken

1. **Revise and overrides were broken in IdeaPress, and fixed here** (operator, 2026-09-10, asked at
   the inventory). `POST …/units/{key}/revise` started a *draft* run, whose first move
   (`committed → drafting`) is no arrow in data model §3, so every revision of a committed unit ended
   `stage.failed`; its `instructions`, and every key of a stage run's `overrides`, were written to
   `stage_runs.options_json` and read by nothing. No test ran revise end to end. The operator chose to
   fix revise and to *apply* the overrides rather than hide them.
2. **How a revision behaves** (`unit_loop.revise_unit`): the author's instructions reach
   `stages.revise.improve` as one `AuditFinding` (`category: author_instruction`) — the prompt record is
   unchanged, so no prompt hash moves. That round counts against `max_revision_rounds`
   (`run_review_loop(first_round=1)`). A proposal that raises validation failures above the committed
   text (the review loop's own `rejects_regression`) **pauses the unit with its version kept** — the
   version stays `current_version_id`, and the pause reason names it; `paused → revising` is the "resume
   with instructions" arrow. A review that hands back exactly the committed text returns the unit to
   `committed` with **no second version** (`unit.unchanged`). A unit with nothing to revise is
   `unit.skipped`, not a failed stage.
3. **Overrides, per stage** (`stage_bodies.OVERRIDES_READ`): `draft` reads `max_revision_rounds` and
   `model_hint`; `revise` those and `instructions`; `project_review` `model_hint`; `research` none.
   `model_hint` is held on the gateway beside `_run_id` (the ADR-0038 one-run-at-a-time rationale that
   docstring already gives) and applies to every call of the run; `max_revision_rounds` is coerced by
   the setting's own field (`settings._coerce`), so its bounds are `config.toml`'s. `null` is no
   override. Refusing an unread key changes an answer — it was silently recorded — which is the point.
4. **The routes the kickoff named as UI-only, and what the inventory found.** `POST …/research` and
   `POST …/units/{key}/resume` needed no new route: they are `POST …/stages/research/run` and
   `POST …/stages/draft/run {"units": [key], "resume": true}` — exactly the calls IdeaPress's own forms
   make. `GET /export/formats` was already on the API. What the API lacked was what those pages
   *read*: the plan, the research record with egress decisions, the workspace view, the per-version
   history, the project's stage history and running task, the unit list's coverage and last validation,
   and archive-before-delete — each added in IdeaPress as its own commit (§1).
5. **Archive before delete** writes `<slug>-<UTC stamp>.ideapress.zip` into `archives/` **beside** the
   project directory, never inside a project's own (a delete removes that directory). An archive that
   cannot be written is `500 EXPORT_FAILED` and nothing is deleted. The console's typed confirmation is
   compared with the title IdeaPress answers, never a hidden field; the preview is a `pending` row.
6. **The project list's cursor** is base64 of an offset — API standards §6's own example.
   *Ponytail:* a project updated between two page reads can cross a page edge; key it on
   `(updated_at, id)` if the list is ever paged under concurrent edits. A forged cursor is refused by
   name, as WPC1 decided.
7. **A stopped IdeaPress never gets a second reading of its computed views.** Coverage summaries, last
   validation, a check's wording and whether it is mechanical, and a unit's validation, findings and
   critiques are IdeaPress's assembly of several tables; the database readers show `—` or say the page
   reads them only from the running API. Projects, units, content, versions, stage runs with their
   events, requirements, research notes and tool calls (joined to `egress_decisions` by `source_ref`)
   are read. Workflows, backends, the workspace and export read only the API.
8. **The task stream** becomes the existing log pane's frames (`task_log_frames`): IdeaPress's own
   `message` per event; `unit.paused`, `unit.reset`, `revision.rejected`, `research.egress_denied` and
   `stage.failed` are **warning** lines naming the state (a cancellation arrives as `stage.failed` with
   `state: cancelled`) — never the proxy's own `error`. A bare `token` frame is a line of its text, which
   the pane sets with `textContent`. *Ponytail:* a reconnect replays from the first event, as WP1's.
9. **Text an author or a model wrote** reaches the page escaped; a unit's content renders through
   W6's `chat.render_reply` (escaped markdown, no images, http(s) links only). An export download is
   served `Content-Disposition: attachment`, so an HTML export never runs in the console's origin.
   Audit rows carry no title, brief, author material, instructions or unit text — only shapes
   (`has_brief`, `has_instructions`, the override *keys*).
10. **What the pages offer on a unit** follows IdeaPress's arrows: *Revise* on a `committed` unit or a
    `paused` one with a version; *Resume* on `paused`, and on `drafting`/`validating`/`auditing`/`revising`
    when no run is in flight (a stranded unit — IdeaPress resets it to `paused` first, row WI1); a
    `planned` unit points to the project's run form; nothing while a run is in flight. IdeaPress still
    refuses anything else, and the page renders its refusal.
11. **The run form's stages** are `draft`, `project_review`, `research` (`ideapress_pages.RUN_STAGES`),
    the ones IdeaPress's workspace and CLI start; the plan and a revision have their own forms, and
    IdeaPress refuses a stage it has no body for by name. The effective `models.stages.*` and
    `workflow.*` values beside the form come from `GET /settings`, with each key's `applies`.
12. **Fixtures** (`tests/fixtures/ideapress/`, `tests/fixtures/databases/ideapress-0011-journey.sqlite3`)
    were recorded from **IdeaPress's own application over its scripted backend** in a scratch XDG tree
    (the recorder is in the session scratchpad, `record_ideapress_fixtures.py`): no model loaded, so the
    one-load rule with WP3 was not touched, and the stream holding `unit.paused` and `stage.failed` is
    deterministic. One exception: its `POST /backends/test` used IdeaPress's configured `ollama` mode and
    so read the reference machine's Ollama health and model list (`backend-test.json`); nothing was
    generated.

## 3. The kit, after WP5 (for WP4 and WP6)

* `app_api.text(client, settings, app, path, params=…)` → `(media type, text)` for a non-JSON body.
* `tests/support.py`: `IDEAPRESS_URL`, `ideapress_fixture`, `mock_ideapress(router, bodies=…,
  base_url=…)`, `ideapress_console(tmp_path, state=…)`. The audit console points IdeaPress at a closed
  port (`127.0.0.1:9`) for the guard's tests, so an exercise must mock the console's configured
  `base_url`, not the default (`_ip_form`).
* Template literal text is not escaped by Jinja — only variables are — so a test asserting on a
  template's own apostrophe expects `'`, not `&#39;`.

## 4. Parity with IdeaPress's own UI

| IdeaPress UI (`web/routes`, `web/templates`) | Console | Test |
|---|---|---|
| `GET /` project list (+ show archived) | `…/projects` (status, content type, archived, cursor) | `test_the_running_projects_page_…`, `test_the_list_sends_its_filters_…`, `test_a_stopped_projects_page_…` |
| `POST /projects` (title, brief, content type) | the create form, + workflow and author material | `test_create_sends_ideapress_body_…`, `test_author_material_that_is_not_an_object_…`, `test_an_ideapress_refusal_…` |
| `GET /projects/{id}` | `…/projects/{id}`: fields, brief, author material, plan figures, units, stage history, run forms | `test_one_running_project_…`, `test_one_stopped_project_…`, `test_the_run_form_shows_the_values_…` |
| — (API/CLI only) `PUT`, `DELETE /projects/{id}` | Edit; Delete with preview, typed title, archive-first | `test_edit_puts_the_form_…`, `test_delete_previews_first_…` |
| `GET /projects/{id}/plan`, `POST …/plan/edit` | `…/plan`: requirements with sources, unit plan, the five edits, the gate's refusal | `test_the_running_plan_…`, `test_a_stopped_plan_…`, `test_a_plan_edit_sends_…`, `test_the_plan_gate_refusal_…` |
| `POST …/research` (workspace) and research on the unit page | Run research on the plan and workspace; every call with its egress decision | `test_running_the_plan_and_research_…`, plan tests |
| — (API only) `POST …/stages/{stage}/run`, `…/tasks/{id}`, `…/cancel` | the run form; `…/tasks/{id}`; Cancel | `test_a_stage_run_sends_…`, `test_an_override_ideapress_refuses_…`, `test_a_running_task_…`, `test_a_cancelled_task_…`, `test_cancel_posts_…` |
| `…/tasks/{id}/log` (the workspace's live pane) | `…/tasks/{id}/events` over `/stream` | `test_the_task_stream_becomes_log_lines_…` |
| `GET /projects/{id}/units/{key}` | `…/units/{key}`: content (sanitised), coverage, validation, findings, critiques, provenance, history | `test_a_unit_shows_sanitised_content_…`, `test_a_stopped_unit_…` |
| — (API/CLI only) `POST …/revise`; `POST …/units/{key}/resume` (workspace) | Revise with instructions; Resume (stranded included) | `test_revise_sends_the_instructions_…`, `test_a_revision_ideapress_refuses_…`, `test_a_stranded_unit_offers_only_resume_…` |
| — | **Units** menu page: a project's units with coverage and last validation | `test_units_lists_a_projects_units_…` |
| `GET /projects/{id}/workspace` (navigator, pause guidance, coverage, content, findings, versions and diff, provenance, backend egress, cost, research) | `…/workspace` over `GET …/workspace` | `test_the_workspace_shows_…`, `test_a_stopped_workspace_…` |
| `GET /projects/{id}/export`, `POST …/export`, the raw `GET /api/v1/…/export` links | `…/export`: formats in IdeaPress's words, what is included, write, download as attachment | `test_export_writes_…`, `test_an_export_downloads_…`, `test_an_export_ideapress_refuses_…` |
| `GET /backends` | `…/backends`, + the round-trip **Test** (API only) | `test_backends_show_egress_…` |
| — (API only) `GET /workflows` | `…/workflows`, `…/workflows/{id}` with bindings and limits | `test_workflows_show_stage_order_…` |
| `GET /system` | **no console page** (IdeaPress's menu in spec §7.3 has none; the Overview and doctor cover health) | — |

The injection corpus renders inert in a brief and author material, in unit content and its pause
reason, and in the workspace (`test_the_injection_corpus_renders_inert_…`, now in the spec §14
registry). **Not at parity:** the workspace's inline `workspace.js` status line (the console's pane
replaces it) and IdeaPress's `diff.js` "hide unchanged lines" toggle.

## 5. Demonstration on the reference machine

`ideapress.service` was restarted at 00:17:22 PDT to serve the eight IdeaPress commits (its database
held no project). A **throwaway** console ran the worktree's code on `https://127.0.0.1:8789`
(open loopback, its own XDG tree in the session scratchpad, `[apps.ideapress] executable` set so the
stopped pages find the database), driven by Playwright over the system Chrome
(`wp5-demo/demo.py`). The operator's `weightroom.service` was not touched. **WP5 took the machine's
one live model load first**, at the operator's word (2026-09-11); every model call ran on
`ollama/qwen3.5:9b-q8_0`, IdeaPress's own bindings.

1. **Created and planned from a phone — emulated.** A Pixel 7 profile (viewport and touch) created
   *WP5 demo: drafting on your own machine* (`01M27NB0G65YFXBE5YD6FNYBB3`) with a brief and author
   material, then pressed *Run the plan*: task `01M27NB0W4GSCTTTSG7D26JDRZ`, 00:19:01 → **completed**
   00:23:21, 3 blocking requirements and units U-01, U-02. The plan page rendered on the phone with
   each requirement's quote and the five edit forms. **Not a real device** — the operator chose
   emulation.
2. **Draft run, streaming.** From the run form (`max_revision_rounds` 0 for the run): task
   `01M27NK0BTBBZBVYWTVKZMSE3H`; the log pane showed `stage.started`, `unit.started`,
   `attempt.started` live, then validation, audit, critique, `review.stopped` (*round_limit — 0 of 0
   rounds used*, the override applied) and `unit.committed` for U-01 at 00:27:31.
3. **Cancelled mid-run, then resumed.** *Cancel run* at 00:27:33, while U-02's draft attempt was with
   the model; the page said it lands at the next model-call boundary. It landed at 00:28:51:
   **`cancelled`**, 1 committed of 2, the pane's last line a warning — *stage.failed · the stage ended
   cancelled: cancelled* — and no error box. U-02 was left **`drafting`** (the in-flight unit of a
   cancelled run); its page offered only *Resume* (*no run owns this unit*). Resume: task
   `01M27NX6QNH0MEK05NW3E7PSCC` → **completed** 00:35:42, U-02 committed.
4. **Revised with an instruction; history read.** U-01, *Add one sentence saying that no account is
   needed.*: task `01M27P9NSRZ4WB4PF1Y3NAWJ2W` → **completed** 00:38:40. Version 2's content carries
   *No account is needed.*; the history shows version 2 produced by `revise, audit_fast, critique` and
   version 1 by `draft, audit_fast, critique` — the revise fix of `7ad4ca6`, live.
5. **Backend test.** `ollama`: **ok**, 28.88 ms, Ollama 0.32.13, 11 models listed, not remote.
6. **Export as markdown.** IdeaPress wrote
   `~/.local/share/ideapress/projects/wp5-demo-drafting-on-your-own-machine/wp5-demo-drafting-on-your-own-machine.md`,
   4 623 bytes, `sha256:a4467908…f2e637`, 2 units.
7. **IdeaPress stopped, every page reloaded.** Eleven pages answered **200** running and **200**
   stopped: Projects, the project, Plan, Units, the unit and the run read *from the database at
   revision 0011*; Workspace, Export, Workflows (both) and Backends said they read only the running
   API, each with *Start*. `ideapress.service` was started again, `active`.

The throwaway console's audit log holds one row per action: `ideapress.project_create`,
`plan_run`, `stage_run` (`overrides: ["max_revision_rounds"]`), `stage_cancel`, `unit_resume`,
`unit_revise` (`has_instructions: true`), `backend_test`, `export_write`. **One defect found and
fixed:** the resume and revise rows read `unit_key: ********` — the audit redaction masks any
parameter whose name holds *key* — so the parameter is `unit` now (`d44363d`, with its tests).

Screenshots of every step and every page, running and stopped, both themes (`wp5-demo/shots/`, 72
PNGs) are in the session scratchpad.

**Seen, not this row's:** the throwaway console raised *memory cap fired · ollama.service* at the first
load (Ollama logged *disabling mmap for llama-server load due to host memory pressure*, 00:19:03);
the stopped notice names the application in lower case (*ideapress is not answering*, WP2 §7 item 5);
the log pane closes with *— the journal reader ended —*, its Logs-page wording.

## 6. What the kickoff got wrong

* **"Known UI-only routes: … `POST …/research`, `POST …/units/{unit_key}/resume`, `GET /export/formats`"**:
  the first two are stage runs the API already took; the third was on the API (§2 item 4). What was
  missing was every *read* those pages make.
* **"Revise with instructions, within IdeaPress's bounds"** and **"`POST …/run` with IdeaPress's
  body"**: revise could not work and overrides were never applied (§2 items 1–3).
* **"List with … a cursor"**, **"the detail page shows the plan summary, unit states and stage
  history"**, **"units … with requirement coverage and last validation"**, **"history of every version
  with attempts, validations, audits and critique verdicts"**, **"offers archive-to-export first"**:
  api.md promised each; the API served none (§1).
* **"`app_side_nav_stubs("ideapress")` leaves only `Tokens`"**: IdeaPress's menu has no *Tokens* entry,
  so nothing is left: `()`.
* **"Enveloped frames plus bare `token` frames"**: IdeaPress emits no `token` event today; its event
  source only knows how to format one. The proxy handles the shape, tested with a frame built as
  IdeaPress would build it (§2 item 8).
* **"A recorded IdeaPress task stream"**: recorded from IdeaPress's own application over its scripted
  backend rather than a live model (§2 item 12); the live stream is §5.
* **"`EXERCISES`, the §14 registry, the OpenAPI snapshot and `api.md` updated"**: the console's snapshot
  and `api.md` have nothing to change (UI routes only), as at WP1 and WP2.

## 7. For the operator

1. **Merge — `main` already merged into this branch; the branch is ready for you to merge.** WP3
   reached `main` first (`a4281ec`), so under `weightroom-work.md` §3 this row merged `main` into
   `row/wp5-ideapress-pages` as `a7d29e3`. Five files conflicted and each keeps both rows:
   `domain/audit.py` (`ACTIONS`), `web/app.py` (both routers), `web/rendering.py` (`_PAGE_HREF`;
   `_PAGE_PHASE` now holds only FreeWeight's *Goals* → WP4), `CHANGELOG.md` (both `[Unreleased]`
   entries) and `tests/security/test_audit_routes.py` (main's file with WP5's `_ip_form` and its two
   `EXERCISES` blocks added before `_state_changing_routes`). `tests/support.py`,
   `tests/security/test_checklist.py` and `roadmap/weightroom-work.md` (both rows' marks) merged
   without conflict. Neither row changed the console's OpenAPI snapshot or `api.md`, so nothing was
   regenerated; the snapshot test passes. **The gate after the merge**, Python 3.14.4: format, lint,
   mypy (222 files), `lint-imports` (5 kept), `pytest` → **1781 passed, 3 skipped**.
2. **Restart `weightroom.service` after the merge** to serve these pages.
3. **Left on the reference machine:** IdeaPress project `01M27NB0G65YFXBE5YD6FNYBB3` (*WP5 demo:
   drafting on your own machine*, U-01 at version 2, U-02 at version 1), its five stage runs, their
   ledger and egress rows, and the markdown export in its project directory; `ideapress.service`
   restarted once (00:17:22 PDT) and stopped and started once (00:38:44–46), `active`;
   `qwen3.5:9b-q8_0` resident in Ollama until its keep-alive expires — **WP3's live load is clear once
   it has**. The throwaway console is stopped; its tree, audit log and screenshots stay in the session
   scratchpad. The *memory cap fired* alert was raised on the throwaway console only.
4. **Candidate follow-ups, not scheduled:** a total-order cursor for `GET /projects` (§2 item 6);
   IdeaPress's `GET /system/status` still answers `active_stage_runs: []` always (the project detail's
   `running_task_id` is the truthful place); applying `model_hint` per stage rather than per run.

## 8. What runs next

WP4 once WP3 is merged (§3 of the work file); WP6 once WP4 and WP5 are both merged.
