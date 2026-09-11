# WP1 Handoff — application pages I: the page kit, Logs, PromptCadence

**Row:** WP1 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-10, attended, one sitting ·
**Model:** Claude Opus 5 · **Kickoff:** `history/prompts/wp1-weightroom-app-pages-kit-promptcadence.prompt.md`
(arc index `history/prompts/wp-app-pages-arc.prompt.md`)

## 1. What shipped

| Commit | Gate | What |
|---|---|---|
| `12f86a0` | docs | Rows WP1–WP6 pasted into `weightroom-work.md` §1 from the arc index |
| `59ccbfd` | A | The page kit (`services/app_api.py`, `services/app_pages.py`, `render_app_page`, `read_app_page`, `app_view`, `_app_state.html`, `_app_page.html`), the two-section menu, a **Logs** page under every application's tab, each stub naming its WP row |
| `a8a6a2e` | B | PromptCadence's **Trajectories**, one trajectory's **record**, **Approvals**, **Tiers**, **Tools**, **Ledger**, **Egress**; the trajectory stream proxied as log-pane frames; `rows_where`; recorded fixtures under `tests/fixtures/promptcadence/` |
| `39b0a51` | C | **Submit**, **cancel**, **grant**, **deny** (`services/promptcadence_actions.py`), four audit actions, `APP_REFUSED` → 502, the audit-registry exercises |
| `7089cf4` | polish | Found in the screenshots: a stopped application's page now shows one notice and one *Start*, not the Overview's three full-width buttons; identifier links never wrap |

Nothing pushed or tagged; no version bump (`wr-gym` stays `1.0.0`, the work under
`[Unreleased]`). No other repository was touched.

**The gate**, WeightRoom `.venv`, **Python 3.14.4**, at `7089cf4`: `ruff format --check .`,
`ruff check .`, `mypy src tests` (204 files), `lint-imports` (5 contracts kept), `pytest -q` →
**1556 passed, 3 skipped** (1495 before the row). Coverage (`pytest --cov=weightroom`) **90 %**
total; `app_api` 95 %, `app_pages` 91 %, `promptcadence_pages` 96 %, `routes/promptcadence`
98 %, `promptcadence_actions` 81 %. The OpenAPI snapshot and `api.md` are **unchanged**: every
route this row adds is a page or a form post on a `ui_router` (`include_in_schema=False`), and
the snapshot test confirms it.

## 2. Decisions taken

1. **The API has no view of two subjects, so those read the database even while PromptCadence
   runs** (spec §7.3: "where the API has no view — a read of its database"). `GET /approvals`
   lists pending requests, and resolved ones only per trajectory; `GET /egress-decisions` lists
   the **oldest** first with a 200 clamp and no cursor, so its first page is the wrong 200.
   `read_app_page(..., api=None, ...)` expresses it, and both footers say why. A PromptCadence
   API change (`status=all` without a trajectory; `order=desc` or a cursor on egress) would let
   both pages go back to the API. That is a candidate row, not done here.
2. **The console's grant and deny call `app_api` directly** rather than
   `services.chat.decide_approval`. That function is bound to a chat conversation's pending card
   and sends no `budget`, which a `ceiling_raise` requires. The precondition is the same
   `token_can_approve` check (`promptcadence_actions.require_approve_scope`), and the audit rows
   are `security` rows as `chat.approve`'s are.
3. **The audit trail never carries the task text.** `trajectory.submit` names the classification,
   the tools, the tier, the project and whether a budget was set. Budget figures are not in the
   row: `redact_params` masks any key containing `token`, so `budget_tokens` would have read
   `********`.
4. **Tools are always sent**, empty when nothing is ticked (W6's finding: an omitted allowlist is
   every configured tool). When the registry cannot be read, the field becomes free text,
   comma-separated.
5. **The trajectory stream becomes the existing log pane's frames** (`log`, `log.closed` on the
   terminal event or on the proxy's `error` frame) instead of a second pane. *Ponytail:* a
   reconnect replays the stream from its first event, because upstream event ids are not
   forwarded; forward them if a page ever needs to resume mid-stream.
6. **Stubs name their row** (`coming in row WP2`), keyed by application as well as label, since
   FreeWeight's *Models* and LoadCoach's are different rows. `_PAGE_ELSEWHERE` stays until WP2/WP3
   build Provider(s).
7. **The control form carries `next`** and returns to the page it was pressed on, but only to a
   path under the same application's tab (`_back_to`; `//host`, another app and `/apps/loadcoachx`
   are refused and go to the Overview). The approvals forms use the same rule under
   `/apps/promptcadence/` (`_within`).

## 3. The kit, for WP2–WP5

* **Reading.** `app_view(request, app)` → `read_app_page(request, view, api=<callable>|None,
  database=<callable(handle)>|None)` → `Sourced` (`source`, `detail`, `data`, `error`, `live`).
  API readers call `app_api.call(client, settings, app, method, path, params=…, body=…,
  timeout_seconds=…)`, which raises `AppRefused` (the application's own code in
  `details["app_code"]`) or `AppUnreachable`. Database readers use `app_pages.rows_where(handle,
  table, equals={…}, order_by=…, descending=…, limit=…, offset=…)`; `None` filter values are
  dropped.
* **Rendering.** `render_app_page(request, principal, app, template, selected="<label>",
  view=view, **context)`. The template does `{% include "_app_state.html" %}` and imports
  `page_source`, `refusal`, `rows_table` from `_app_page.html`. A macro that renders a form needs
  `import … with context` (for the CSRF token).
* **Streams.** `app_api.stream(...)` proxies an SSE stream with `Last-Event-ID`; a page either
  passes it through or converts it (as `promptcadence_pages.event_log_frames` does for the pane).
* **The menu.** Add the label to `_PAGE_HREF`, remove its `_PAGE_PHASE` entry; administrative
  labels live in `_ADMIN_PAGES`.
* **Actions.** Add the action to `domain/audit.ACTIONS`; register the route in
  `tests/security/test_audit_routes.py` through an `EXERCISES.update(...)` block. A refused action
  that renders a page must mock LoadCoach too: the page's application tabs probe its version, and
  respx raises on anything unmocked. That is why Gate C's first full run failed under a random
  order.
* **Traps met.** Templates run under `StrictUndefined`, so read optional keys with `.get`, and a
  collection as `data["items"]` (`data.items` is the dict method). `ruff format` rewrites Python
  files, so re-read before editing. Record fixtures from the live application (`curl` with the
  console's token file) and commit only harmless content.

## 4. Parity with PromptCadence's own console

| PromptCadence UI (`web/routes/console.py`) | Console | Test |
|---|---|---|
| `GET /` dashboard | Overview (W3) | `tests/unit/test_overview.py` |
| `GET /trajectories?state&cursor` | `GET /apps/promptcadence/trajectories` | `test_running_pages_read_promptcadences_api`, `test_stopped_pages_read_the_database_with_a_start_beside_them` |
| `GET /trajectories/{id}` (the explanation document) | `GET …/trajectories/{id}`, every section of the document | the same, `test_the_injection_corpus_renders_inert_…` |
| `/trajectories/{id}/log` (live pane) | `GET …/trajectories/{id}/events` over `/stream` | `test_a_live_trajectory_streams_as_log_frames_…` |
| — (API only) `POST /trajectories` | `POST …/trajectories`, the New-trajectory form | `test_the_form_becomes_promptcadences_body_…`, `test_no_tool_ticked_…`, `test_a_refusal_comes_back_…`, `test_a_field_that_cannot_parse_…` |
| — (API only) `POST /trajectories/{id}/cancel` | `POST …/trajectories/{id}/cancel` | `test_cancel_redirects_to_the_record_…` |
| `GET /approvals?resolved` | `GET …/approvals` (pending, and every request) | running and stopped tests |
| `POST /approvals/{id}/grant` | `POST …/approvals/{id}/grant`, on the page and on the record, with a ceiling raise's ceilings (PromptCadence's own inbox cannot send those) | `test_a_grant_without_the_approve_scope_…`, `test_a_ceiling_raise_grant_…` |
| `POST /approvals/{id}/deny` | `POST …/approvals/{id}/deny` | `test_a_denial_sends_its_reason_…` |
| `GET /tiers` | `GET …/tiers` | running test |
| `GET /tools` | `GET …/tools` | running test |
| `GET /ledger?trajectory_id` | `GET …/ledger?trajectory_id&tag` | running and stopped tests |
| `GET /egress?verdict&trajectory_id` | `GET …/egress` | `test_egress_is_read_newest_first_…` |
| `GET /settings`, `POST /settings` | Settings (W4) | existing |
| `GET /system` (health, last recovery pass, how it authenticates) | **no console page** | — |

PromptCadence's **System** page has no menu entry in spec §7.3, and this row did not invent one.
The console's doctor and the Overview's health cover part of it; the last recovery pass is not
shown anywhere in the console. WP6 should judge it.

## 5. Demonstration on the reference machine

Against a **throwaway** console (loopback `127.0.0.1:8779`, its own XDG tree, open loopback, the
operator's application token files read in place), driven with Playwright and the system Chrome,
both themes. The operator's `weightroom.service` was not touched.

1. **Submitted from the Trajectories page:** "State in one sentence what 3 + 4 is.", `internal`,
   no tools → trajectory `01M277X4949YM571B679X90MZ0`, planned, executed on
   `ollama/deepseek-coder-v2`, **completed** ("The result of the arithmetic expression 3 + 4 is
   7."). The record showed the live pane while it ran, then the whole explanation: one attempt,
   step `s1`, one envelope, three turns, one debit (`unpriced`, `tier:local_fast`), one egress
   decision (`approved`, `target_not_remote`), twelve events including `egress.evaluated`.
2. Ledger and Egress filtered to that trajectory both listed it.
3. **PromptCadence stopped** (`systemctl --user stop promptcadence.service`, twice, about a
   minute each, started again both times and `active` since): every page answered `200`.
   Trajectories, the record, Approvals, Ledger and Egress read *from the database at revision
   0011*; Tiers and Tools said they read only from the running API; the record carried a
   working Start (after the polish: one notice, one button).
4. All four applications' **Logs** pages rendered history and the live pane. PromptCadence's menu
   has no stub left; FreeWeight, LoadCoach and IdeaPress show theirs with their rows named.

Screenshots are in the session scratchpad (`wp1-demo/shots/`, 50 PNGs); they go with the session.

**Not demonstrated live:** a **grant or a denial** (the reference machine's tiers are local and its
policy raised no approval request, as at W10: fixture and test only); the injection corpus
against a live model (test only); a phone (not part of this row).

## 6. What the kickoff got wrong

* "Reuse `chat_promptcadence`'s decide function": that function is conversation-bound and sends no
  budget (§2 item 2).
* "Regenerate the OpenAPI snapshot and `api.md`": nothing to regenerate, since every WP1 route is a
  UI route (§1).
* "The Overview must render byte-for-byte as before": the control form gained the hidden `next`
  field; every Overview test passes unchanged.
* "Grant its approval" in the demonstration: nothing on the reference machine raises one (§5).
* "Running reads the API": true except for the two subjects the API has no view of (§2 item 1).

## 7. For the operator

1. **Restart `weightroom.service` to see the new pages**: it runs this checkout's editable install
   and still serves the code it started with. `systemctl --user restart weightroom.service`.
2. **Two existing defects the screenshots show, not this row's:** (a) the MirrorWall `card(…,
   kind="figure")` renders label, figure and note on one line rather than stacked (design brief
   §5), on the Overview and on this row's Ledger alike; (b) PromptCadence's Overview figures read
   `executing`, `planning` and `pending_approvals` off `/system/status`, which serves
   `active_trajectories` and `pending_approvals` as lists. So *Executing* and *Planning* show `—`
   and *Pending approvals* shows `[]` (W3's `_STATUS_FIGURES`). Both are small; say which row
   takes them.
3. **Candidate PromptCadence API change** (§2 item 1): resolved approvals without a trajectory,
   and egress decisions newest-first with a cursor.
4. **Left on the machine:** trajectory `01M277X4949YM571B679X90MZ0` and its debit in
   PromptCadence; `promptcadence.service` restarted twice; LoadCoach's journal holds the
   throwaway console's reads; the throwaway's own tree is in the session scratchpad.

## 8. What runs next

WP2 (`history/prompts/wp2-weightroom-loadcoach-pages.prompt.md`) on this kit, then WPC1 (§9).

## 9. Operator decisions (2026-09-10, post-handoff interview)

1. **PromptCadence's API gaps (§2 item 1) become a row: WPC1.** It runs after WP2 and before WP3,
   on Opus 5 · high, never overnight. Two additive changes land in PromptCadence's API: every
   approval request listed without a trajectory, and egress decisions newest first with a cursor.
   The console's Approvals history and Egress page then read the API while PromptCadence answers.
   Kickoff: `history/prompts/wpc1-promptcadence-api-gaps-system-page.prompt.md`.
2. **The two existing defects (§7 item 2) go to WP2's Gate A.** The figure-card layout is fixed in
   WeightRoomGym's shell CSS, and MirrorWall `0.3.1` stays as prepared. The Overview's figures are
   re-read against each application's real `/system/status` body.
3. **PromptCadence gains a System page (§4).** Spec §7.3's PromptCadence menu is amended to list
   *System*, and WPC1 builds it at parity with PromptCadence's own page.
4. **A grant and a denial are proven live in WPC1**, by setting a real approval gate up on
   purpose, not left to WP6 or to tests alone.
5. **`weightroom.service` was restarted** at the operator's instruction, right after this
   interview. It answers `1.0.0` on `https://10.77.10.84:8769`, and
   `/apps/promptcadence/trajectories` redirects to the login page, so the WP1 routes are live.
