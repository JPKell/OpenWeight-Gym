# WPF11 Handoff — a catalog call slower than the client is not a refusal

**Row:** WPF11 (`roadmap/weightroom-work.md`, wave 4) · **Ran:** 2026-09-12, agentic ·
**Model:** Sonnet 5 · **Kickoff:**
`history/prompts/wpf11-weightroom-catalog-calls-slower-than-the-client.prompt.md` · **Branch:**
`row/wpf11-catalog-pending` at `~/ai/worktrees/weightroom-wpf11`, from WeightRoom `e225fdd`, **not
merged**. **Ships:** unreleased, no version bump.

## 1. What shipped

| Commit | Gate | What |
|---|---|---|
| `eaf451b` | A | `services/catalog.py` — `set_enabled` and the delete path's two Ollama calls
(`/api/tags`, `/api/delete`) raise `app_api.AppTimedOut` on a timeout instead of `CatalogRefused`;
`web/routes/catalog.py` — `catalog.enabled`, `catalog.delete` and `catalog.pull` audit through
`app_api.outcome_of` instead of a bare `"refused"`. Tests: `tests/unit/test_catalog_domain.py`
(6 new), `tests/integration/test_loadcoach_pages.py` (1 new, route-to-audit). `CHANGELOG.md`. |

Gate B is the orchestrator's (below).

**Gate**, at `eaf451b` in the worktree, `~/ai/worktrees/weightroom-wpf11/.venv`, **Python 3.14.4**:
`ruff format --check .` clean (235 files), `ruff check .` clean, `mypy src tests` clean (228 files,
strict), `lint-imports` **5 contracts kept**, `pytest -m "not live and not performance"` **1902
passed, 3 skipped, 10 deselected**. `git status --short` clean.

## 2. What this row settled

### Decision 1 — the same distinction `app_api` has, reused rather than rebuilt

Confirmed in `services/app_api.py` (WPF1): `AppTimedOut` is a subclass of `AppUnreachable`
carrying the same `APP_UNREACHABLE` code, and `outcome_of(exc)` reads it as `"pending"`, anything
else as `"refused"`. Two of `freeweight.py`'s and `loadcoach.py`'s own `set_enabled` call sites
**already** call `outcome_of(exc)` when auditing `catalog.enabled` — WPF1 built that half. What
was missing was the other half: `services/catalog.py` itself raised `CatalogRefused` for every
failure, timeout included, so `outcome_of` on that exception could never see anything but
`"refused"`. This row closes the gap at its root — inside `catalog.py`, once, rather than adding a
special case in each of the three callers (`web/routes/catalog.py`, `web/routes/freeweight.py`,
`web/routes/loadcoach.py`) that already share this code.

**No second vocabulary was built.** `AppTimedOut` is imported from `app_api` and reused as-is;
`services/app_api.py` itself was not edited (per the row's own collision map) — only read.

Three calls changed:
- `set_enabled` (`POST {app}/api/v1/models/{model_id}/enabled`): `httpx.TimeoutException` →
  `AppTimedOut`; every other `httpx.HTTPError` and a non-success response still raise
  `CatalogRefused`, unchanged.
- `_ollama_tag_exists` (`GET /api/tags`, used by the delete preview): a timeout raises
  `AppTimedOut`; every other failure (Ollama unreachable, a bad body) still degrades to `False`,
  unchanged — a preview is a best-effort read (W8), and only a timeout is the *pending* case.
- `_ollama_delete_tag` (`DELETE /api/delete`, used by the confirmed delete): the same split —
  timeout raises, everything else still degrades to `False` (`ollama_removed=False`).

`web/routes/catalog.py`'s `_enable`, `_delete` and `_start_pull` now audit with
`outcome=outcome_of(exc)` instead of a hardcoded `outcome="refused"`.

### Decision 2 — does `pull` move onto the job queue? **Already moot; flagged for review**

**The kickoff's premise was stale.** `catalog_pull` was moved onto the job queue at **row W9**
(`870cec5`, `docs/history/handoffs/W9_HANDOFF.md` §3: *"`catalog_pull` is a queued job now"*),
before this row ever ran. `web/routes/catalog.py`'s `post_pull`/`pull_from_page` already call
`services.jobs.enqueue(kind="catalog_pull", …)`, not a synchronous call to Ollama; the actual
`/api/pull` streaming happens later, inside `job_kinds.catalog_pull`, executed by the job worker
in its own thread, with `timeout=None` on the stream (deliberately — a pull runs for minutes and
must not be killed by a client-style timeout).

Consequences for Gate A's third example ("a timed-out … pull … audits pending"):
- **The enqueue call itself cannot time out.** `enqueue()` only writes one local row; there is no
  outbound HTTP call at that layer, so there is no `AppTimedOut` case to build there. I updated its
  exception handler to use `outcome_of(exc)` anyway (uniform with the other two routes, and it
  costs nothing), but today `exc` there is never `AppTimedOut` in practice — noted, not disguised,
  in the docstring and in `CHANGELOG.md`.
- **The pull's own progress is a job outcome (`completed`/`cancelled`/`failed`), not the
  `pending`/`refused` audit vocabulary.** `run_pull`'s stream has no timeout by design, so it
  cannot raise `AppTimedOut` either; a pull that dies mid-stream is `failed` on the job row, which
  is a different, already-correct mechanism (W9), out of this row's scope.

**My decision: no change needed, and no ADR.** The decision the kickoff asked this row to make was
already made and implemented at W9, without an ADR at the time. I did not write ADR-0142 — writing
one now, after the fact, for a decision this row did not take, seemed like manufacturing a record
rather than keeping one. **Flagging this for orchestrator review per the row's own instructions**:
if W9's queueing of `catalog_pull` should have had an ADR and did not, that is a gap to fill
retroactively or accept, not something WPF11 should paper over by writing one now as if it were
this row's own call.

### Decision 3 — what the page shows after a `pending`

Unchanged from what W9 already built: the pull's SSE stream (`GET
/catalog/pull/{job_id}/stream`) falls back to the job row once `PullRegistry` has nothing for that
id (`_pull_frames`, `web/routes/catalog.py`), and the model reaches the catalog only once a
`model_refresh` job runs, which `job_kinds.catalog_pull` itself queues on success. The Catalog page
re-reads `_entries()` (a live join) on every render, so a model that finished pulling appears
without a second pull being sent — that mechanic was already correct and this row did not touch
it. Gate B proves it live.

## 3. Tests, and why they sit where they do

- `tests/unit/test_catalog_domain.py`: `set_enabled`, `catalog_delete_preview` and
  `catalog_delete_confirm` each get a "raises `AppTimedOut`, and `outcome_of` reads it `pending`"
  test, plus one proving a genuine Ollama failure (500, not a timeout) still degrades to `False`
  the way it always did — so the two paths (`pending` vs. the W8 best-effort preview) don't get
  confused with each other.
- `tests/integration/test_loadcoach_pages.py`:
  `test_a_slow_enable_is_audited_pending_not_refused` drives the whole route
  (`POST /apps/loadcoach/models/{id}/enabled`) through a respx-mocked timeout and reads the actual
  `catalog.enabled` audit row back over `/api/v1/audit` — this is the one test that would have
  caught a mistake in the route's own wiring (e.g. forgetting to swap `outcome="refused"` for
  `outcome_of(exc)`) that a service-level unit test alone would not.
- No new `PENDING`-style registry was added to `tests/security/test_audit_routes.py` — WPF1 itself
  did not build one either; its own live proof demonstrated the pending case on the reference
  machine rather than through that file's `EXERCISES`/`REFUSALS` dicts, which only assert "one row"
  and "outcome == refused" respectively, not "outcome == pending". I judged matching that existing
  precedent (service-level + one route-level test) proportionate rather than building new harness
  machinery this row was not asked for.

## 4. `services/app_api.py`

**Read, not edited.** `AppTimedOut` and `outcome_of` are imported and reused exactly as WPF1 left
them. I did not need to change either — the fix was entirely inside `services/catalog.py` (raise
the right exception) and `web/routes/catalog.py` (read it with the existing function).

## Gate B, on the reference machine

(orchestrator fills in)

**What to watch**, for the orchestrator's live `smollm2:135m` pull with `ollama.service` up:

- **Click path**: Catalog page → *Pull a model* form → type `smollm2:135m` → submit. (JSON
  equivalent: `POST /api/v1/catalog/pull {"name": "smollm2:135m"}`, 202, `{"job_id": …}`.)
- **Watch the job**: `/jobs/{job_id}` (or `wr-gym jobs show {job_id}`) — state moves
  `queued` → `running` → `completed`; its output lines are Ollama's own progress lines
  (`pulling manifest`, `downloading …`, `success`), the same shape `job_kinds.catalog_pull`
  produces (module docstring, §2 above).
- **Watch the stream**: `GET /catalog/pull/{job_id}/stream` (opened automatically by the Catalog
  page after the form posts) — SSE frames of type `pull` with `status`/`digest`/`total`/`completed`,
  then one `done` frame.
- **Audit ids to watch**: the `catalog.pull` row written at enqueue time (`outcome: "ok"`,
  `params.job_id` = the job id above) — that is the one row this row's own change reaches; it does
  **not** change during the pull, because the pull's progress is the job row, not a second audit
  row. If the orchestrator wants to see this row's fix exercised live rather than just the
  already-working W9 mechanism, the closer proof is a **slow `enable`/`disable`** or a **slow
  delete** against an application that is deliberately made to hang (e.g. a `iptables`/firewall
  rule dropping the packet rather than refusing it, or a `sleep` shim in a fake executable) —
  that is what `set_enabled`/`_ollama_tag_exists`/`_ollama_delete_tag` changed, and it is what the
  `catalog.enabled` / `catalog.delete` audit row should read `"pending"` for. **This was not run
  live in this session** (it may need the GPU or a shared unit's exact hang behaviour, which is the
  orchestrator's call, not mine) — flagging it as the one live check this row's actual change would
  benefit from, distinct from the kickoff's own `smollm2:135m` pull proof, which mostly proves W9's
  already-built mechanism still works.
- **No second pull in Ollama's log**: unaffected by this row; same check the kickoff names.

## 5. What the kickoff got wrong

1. **"Decide whether the console's `pull` stays a request with a client timeout … or moves onto
   the job queue."** It already moved onto the job queue, at row W9, before this row existed. The
   kickoff (and the orchestrator's own correction to it) both read as if this were still an open
   design choice; it was closed and shipped two rows earlier. §2 Decision 2 above has the detail
   and the audit trail (`W9_HANDOFF.md` §3, `job_kinds.py`, `web/routes/catalog.py`).
2. **"A timed-out … pull … audits pending."** Under the current (post-W9) architecture there is no
   synchronous call at the `pull` route layer left to time out — the premise assumed the pre-W9
   design where starting a pull was itself a blocking call. I did not force a `pending` case into
   existence where none can occur; I documented why in the module docstring and here instead.
3. **Gate A's three examples (`set_enabled`, `pull`, `rm`) are not symmetric under the current
   code.** `set_enabled` needed exactly the fix WPF1 anticipated. `rm` needed more: unlike
   `set_enabled`, the Ollama-tag calls in the delete path did not raise `CatalogRefused` on
   failure at all before this row — they silently degraded to `False`/`"not removed"`, so the
   route audited `"ok"` even when Ollama never answered. Fixing the `pending` case there
   necessarily meant introducing the first raise on the timeout path specifically, while leaving
   every other failure exactly as silent as W8 built it (Database Standards §8's read-only
   preview contract; §3 above has the test that pins this down).

## 6. For the orchestrator

1. Gate A is green in the worktree; nothing was pushed, merged, tagged or version-bumped.
2. Decision 2 (§2) is the one flagged for review before merge: I made no change and wrote no ADR,
   on the reasoning that the decision was already made and implemented at W9. If that reasoning is
   wrong — if W9's queueing should retroactively get ADR-0142, or if there is a reason to reopen
   whether `pull` belongs on the queue — that is a call for review, not something I resolved
   unilaterally.
3. `services/app_api.py` was read, not edited.
4. Gate B is unrun here — see the section above for the click path, audit ids and the one
   additional live check (a slow `enable`/delete) this row's actual change would benefit from
   proving, beyond the kickoff's own `smollm2:135m` pull (which mainly proves W9's mechanism, not
   this row's).
5. `docs/roadmap/weightroom-work.md` was not touched, per the row's own instructions.
