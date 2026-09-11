# WPC1 Handoff — PromptCadence's API gaps, its System page, a grant proven live

**Row:** WPC1 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended, straight after WP2 ·
**Model:** Claude Opus 5 · **Kickoff:** `history/prompts/wpc1-promptcadence-api-gaps-system-page.prompt.md`

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| PromptCadence | `ae2d5fd` | A | `GET /approvals?status=all` without `trajectory_id` lists every request newest first, paged; `GET /egress-decisions` gains `sort` and `cursor`; `services/cursors.py`; tests written first; OpenAPI snapshot regenerated in a scratch XDG tree; CHANGELOG; `api.md` mirrored byte-identical |
| WeightRoom | `162bf27` | A | `apps/promptcadence/api.md` §4 and §6, edited before the code |
| WeightRoom | `fb30c46` | B | The Approvals history and Egress read the API while PromptCadence answers; PromptCadence's **System** page; fixtures re-recorded from the restarted PromptCadence |
| WeightRoom | this commit | C | This handoff; the row marked done |

Nothing pushed or tagged; no version bump in either repository (both under `[Unreleased]`).

**Gates:**

* **PromptCadence** at `ae2d5fd`, `.venv` **Python 3.13.15**: `ruff format --check .`, `ruff check .`,
  `mypy src tests` (195 files), `lint-imports` (5 kept), `pytest -m "not live and not performance"`
  → **1332 passed, 3 skipped**; with `--cov=promptcadence` **92 %** total (`routes/egress` 100 %,
  `routes/approvals` 93 %, `services/egress` 96 %, `services/cursors` 88 %). The coverage before the
  row was not measured; 92 % is above the 85 % floor.
* **WeightRoom** at `fb30c46`, `.venv` **Python 3.14.4**: the same gate → **1638 passed, 3 skipped**,
  coverage **90 %**, held (`promptcadence_pages` 97 %, `routes/promptcadence` 98 %). The console's
  OpenAPI snapshot and `api.md` are unchanged: the System page is a UI route.

## 2. Decisions taken

1. **The parameter names.** Every request is the existing `status=all`, with no `trajectory_id`,
   paged by **`limit`** and **`cursor`** — the names `GET /trajectories` already uses (API standards
   §6). Egress newest first is **`sort=-decided_at`**, the standard's own spelling (`?sort=-field`),
   not an `order=desc` PromptCadence has nowhere else; `sort=decided_at` states the default, and any
   other value is `400 VALIDATION_ERROR` naming `sort`. Its **`cursor`** works in either order.
2. **The order is total.** Approvals page by `(created_at, request_id)` and egress by
   `(decided_at, decision_id)`, so rows written in the same millisecond neither repeat nor vanish at a
   page edge. `GET /trajectories` compares `created_at` alone; it was not changed.
3. **A forged cursor is refused by name** (`VALIDATION_ERROR`, `field: cursor`). `GET /trajectories`
   silently reads a bad cursor as "the first page", which hands a paging loop the first page
   forever; the new listings do not repeat that.
4. **Only `status=all` without a trajectory changes.** `status=granted` (or `denied`, `expired`)
   without a trajectory still answers from the pending list, which is empty — as it always did.
   Extending it would change an existing answer, which the kickoff forbade; it is noted here.
5. **Egress pages in memory.** *Ponytail:* `EgressService.page` reads every matching decision
   through Commissioner's ledger and pages in Python, as the endpoint already read everything
   before slicing. The ceiling is the size of the egress table; push the order and the cursor into
   `commissioner.sql.SqlEgressLedger` when it grows.
6. **`page.has_more` on the egress default is now exact.** It used to be "the page was full". The
   items for a caller sending neither new parameter are byte-for-byte the same, and live chat's
   per-trajectory read is unaffected; a caller that looped on `has_more` alone now stops one page
   sooner.
7. **The System page sits in the administrative section** (`_ADMIN_PAGES`), after Egress's rule and
   before Settings, as the kickoff says. `/health` answers `503` when a component is unavailable, and
   the console's client reads any status of 400 or above as a refusal, so that case renders the
   refusal (`HTTP_503`) above the components while the status half still renders.
8. **Authentication is not on PromptCadence's API.** Its own System page reads `server.host` and
   `server.port` from configuration, and neither `/health` nor `/system/status` serves them, so the
   page links the Tokens page and says so. That is a candidate additive field, not added here.

## 3. Parity with PromptCadence's own System page

| PromptCadence `GET /system` (`templates/system/index.html`) | Console `…/system` |
|---|---|
| Components with their status and detail | the same, from `GET /health`, with the overall status and version |
| The last recovery pass (touched, resumed, finished, halted, failed, deferred) | the same, from `GET /system/status` |
| Bind host and port | **absent**: the API does not serve them (§2 item 8) |
| LoadCoach base URL, concurrency | the same |
| How the console authenticates (ADR-0094 prose) | a sentence and the Tokens link |
| — | active trajectories, pending approvals with their age, today's position (the kickoff's additions from `/system/status`) |

## 4. Gate C — the live proof on the reference machine

`promptcadence.service` was restarted once after `ae2d5fd`, and the new listings answered live: the
default egress listing stayed oldest first with a `next_cursor`; `sort=-decided_at` returned
newest first; a forged approvals cursor returned `400`.

**The gate was set up by the least invasive route, with no configuration change.** From the
throwaway console (`https://127.0.0.1:8779`, the WP2 tree, operator account `demo`, the operator's
PromptCadence token file read in place), a trajectory was submitted with `bypass_planning` and a
**per-trajectory token budget of 1**. The default `[budget] on_exhausted = "approval"` makes the
first step's pre-flight raise a `ceiling_raise` request (`services/loop.py::_preflight`). Nothing
was changed, so nothing had to be undone.

| | Trajectory | Request | Decision | Outcome | Console audit row |
|---|---|---|---|---|---|
| Grant | `01M27FQB9QFSMF4K2A8TBFSEAF` ("5 + 6") | `01M27FQBB3MFDSB5261NCGS19A`, `ceiling_raise`, `budget_exceeded`, scope `trajectory` | granted from the Approvals page with a new token ceiling of 50 000 | resumed → **completed** | `01M27FQEK412A8C076NR8TB2GQ` `trajectory.approve`, `security: true`, `raised: true` |
| Deny | `01M27FQM0XZR2WV4CPDVMY6WSX` ("7 + 8") | `01M27FQM1ZB3X49DH0CM34XK5S`, `ceiling_raise` | denied with the reason *WPC1 live proof: denied on purpose from the console.* | **halted**, cause *approval request 01M27FQM1ZB3X49DH0CM34XK5S (ceiling_raise, budget_exceeded) was denied: WPC1 live proof: …* | `01M27FQM87WTTM1J2DM2G22MJ3` `trajectory.deny`, `security: true` |

The submissions are `trajectory.submit` rows `01M27FQB9YWQAYMF52JSZRT008` and
`01M27FQM107DT82MPZX566B4NG` (`budgeted: true`). All four audit rows are in the **throwaway
console's** database (the session scratchpad), not the operator's. PromptCadence records the
approver as token `01M24Y8TKHE7DK5346QV3MMBB4`, the console's.

Screenshots, both themes (`wp2-demo/shots/wpc1-*`, 14 PNGs, session scratchpad): the Approvals
page with the pending raise and its ceiling fields, the record awaiting, the resumed record, the
halted record, the Approvals history now **from the API** (four requests, newest first, the denial
with its reason), Egress, and the System page.

The operator's **`weightroom.service` was restarted** after `fb30c46` (active since 22:41:26 PDT).
It answers `1.0.0` on `https://10.77.10.84:8769`, and `/apps/promptcadence/system` answers `401`
to an unauthenticated request rather than `404`, so the routes of both rows are served.

## 5. What the kickoff got wrong

* **"How PromptCadence authenticates, if its API says so"**: it does not (§2 item 8).
* **"`GET /egress-decisions` gains … a cursor, as an opt-in parameter"**: the cursor is opt-in, but
  `page.next_cursor` and an exact `has_more` now appear on the default answer too (§2 item 6).
* **"Nothing on it raises an approval request by itself … its policy raised none at W10 or WP1"**:
  two `plan` requests, both granted, were already in PromptCadence's database from 2026-09-10 (W6's
  chat); the new listing shows them.
* **"If the only route is a configuration change"**: it was not; a submission's own budget sufficed.
* **"Restart `promptcadence.service`" before re-recording** was needed exactly as written; the
  throwaway console also had to be restarted, because a running `wr-gym serve` keeps the code it
  started with.

## 6. For the operator

1. **Left on the reference machine:** PromptCadence trajectories `01M27FQB9QFSMF4K2A8TBFSEAF`
   (completed, with its debit) and `01M27FQM0XZR2WV4CPDVMY6WSX` (halted), their two approval rows,
   and the LoadCoach jobs their turns ran. `promptcadence.service` and `weightroom.service` were each
   restarted once. The throwaway console is stopped; its tree stays in the session scratchpad.
2. **Candidate follow-ups, not scheduled:** the bind/authentication fields on PromptCadence's
   `/system/status` (§2 item 8); pushing egress paging into Commissioner's ledger (§2 item 5); a
   total order and a refused forged cursor on `GET /trajectories` (§2 items 2–3).

## 7. What runs next

WP3 (`history/prompts/wp3-weightroom-freeweight-pages.prompt.md`), on the kit as WP2 §3 describes
it. When WP3 builds FreeWeight's Provider it deletes `_PAGE_ELSEWHERE`.
