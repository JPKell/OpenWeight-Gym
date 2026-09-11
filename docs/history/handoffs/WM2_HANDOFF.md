# WM2 Handoff — the four applications adopt MirrorWall 0.3

**Row:** WM2 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-10, unattended after W10, at the
operator's instruction ("start on WM2 without my involvement, without pushing, and with every
tag held") · **Model:** Claude Fable 5.1 · **Kickoff:** `history/prompts/wm2-four-apps-adopt-mirrorwall-0.3.prompt.md`

## 1. What shipped

| Repository | Commit (unpushed, untagged) | What |
|---|---|---|
| `py/MirrorWall` | `be3797e` (on top of the prepared `0.3.1`) | `log_pane_response(...)` and `log_line(...)` — the server half of `log_pane`: the same replay-then-live loop as `sse_response`, each event rendered as one `log` frame carrying the escaped `.log-pane-line` fragment htmx swaps in, `log.closed` after a terminal event. Named in `packages/mirrorwall/spec.md` (mirrored) and the public-surface contract test |
| `FreeWeight` | `7919f3a` | dense run/model/results lists; status dots on `/system`; meters on the telemetry bar; the run page's log pane over `GET /runs/{id}/log` (the run's own `_event_stream`, with a frame renderer); the tab strip under `[console] url`; `runs.js` keeps the badge and progress bar |
| `LoadCoach` | `c036fee` | an application `base.html` over MirrorWall's (14 templates re-pointed); dense job/model lists; dots on `/system`; meters; the job page's log pane over `GET /jobs/{id}/log` (`log_pane_response` over `event_sink.source`, tokens skipped); the tab strip |
| `IdeaPress` | `8bdde0b` | dense project list; dots on `/system`; the workspace's running-stage section is the log pane over `GET /api/v1/projects/{id}/tasks/{task}/log`; the tab strip; **and a fix found on the way** (§3) |
| `PromptCadence` | `aa508ca` | an application `base.html` (10 templates); dense trajectory list; dots on `/system` and per tier on `/tiers`; a running trajectory's page carries the log pane over `GET /api/v1/trajectories/{id}/log`; the tab strip |
| `WeightRoom` (docs) | this commit | `design.md` §6 marked adopted; `packages/mirrorwall/spec.md`; the four `guide/` copies re-synced; this handoff; the row marked done |

**Versions held** (the operator's decision at the W10 review): every application's work sits
under `[Unreleased]` at its current version; the kickoff's "four patch releases" are the
operator's bump at tag time. `mirrorwall>=0.3.1,<0.4` in all four `pyproject.toml`s; each venv
holds the locally built `mirrorwall-0.3.1` wheel, and each `ci.lock` still pins `0.2.2` until
`0.3.1` publishes — the same standing red as WeightRoomGym's (W10 handoff §2 item 4).

**Gates** (each repository's own venv): MirrorWall 379 passed (Python 3.14.4); FreeWeight 2686
passed, 30 skipped (3.14.4); LoadCoach 1106 passed, 5 skipped (3.14.4); IdeaPress 1295 passed,
6 skipped (3.13.15); PromptCadence 1325 passed, 3 skipped (3.13.15). Format, lint, mypy and
import-linter clean in all five. Each application's JavaScript-per-page budget (ADR-0139,
120 KB total) passes under `-m performance`.

## 2. Decisions

1. **The tab strip's targets come from one key, `[console] url`.** A new `ConsoleSettings`
   section in each application (config-only, not a security key). Set, the masthead gains
   `app_tab("WeightRoomGym", url)` and one tab per application — its own selected and linking
   home, each peer as `<url>/apps/<name>`, reached *through* the console (an application knows
   only its own loopback port). Unset, the block is empty and the page is byte-for-byte what it
   was — the four accessibility suites and every existing page test passed unchanged. **No status
   dots on the strip:** an application does not know a peer's state and invents none (ADR-0016);
   the console's own strip carries them.
2. **The log pane is fed by each application's own event stream, with a renderer per
   application.** MirrorWall's `log_pane_response` reuses the enveloped stream's source and loop;
   the application supplies `render_line`, so the pane shows the event in the application's own
   words (LoadCoach skips `token` frames; PromptCadence appends the cause, reason or step; IdeaPress
   the stage event's message; FreeWeight the timestamp and message). FreeWeight's stream is not a
   MirrorWall `EventSource` (it polls its own store), so its `_event_stream` gained a `frame`/
   `closing` pair instead — same idea, no second loop.
3. **htmx loads only on the page with the pane, and only while it is live** (ADR-0128):
   `mirrorwall={"htmx": True}` on the run and job pages; on IdeaPress's workspace only while a
   stage runs; on PromptCadence's trajectory page only until `completed_at`. Every other page
   carries no htmx and no pane.
4. **Dense is per list table, not per page** (the WM handoff's reading): the index lists an
   operator scans — runs, results, models, jobs, projects, trajectories — take
   `density="dense"`; content tables on detail pages do not.
5. **Status dots map the health vocabulary to the dot's:** `ok`→`ok`, `degraded`→`degraded`,
   `unavailable`→`stopped`, anything else (`not_configured`)→`unknown`, with the health payload's
   own word as the label. PromptCadence's tiers page: available→`ok`, else `degraded` with the
   unavailable reason as the label.
6. **IdeaPress's log route lives on the API router**, `include_in_schema=False`: its accessibility
   suite enumerates every `ui_router` route as a page to render, and an SSE stream is not one.
   LoadCoach's and FreeWeight's live on their HTML routers.
7. **PromptCadence's `[Unreleased]` already held W10's items**; WM2's bullet joins them. IdeaPress's
   compatibility test (`test_config_1_0_compatibility.py`) gained `ADDED_IN_WM2_SECTIONS`, the
   way J1, K3 and M1 recorded theirs.

## 3. Found on the way

* **IdeaPress's own `workspace.css`, `workspace.js` and `diff.js` were never served.** The
  templates rendered them through MirrorWall's `asset_url`, which put them under
  `/static/mirrorwall/` where nothing served them, so the workspace's running-stage section
  never updated live in a browser and its own styling never loaded — since P8 (`efadcb0`).
  Found by the JS-per-page budget test's `assert asset.status_code == 200`. Fixed in `8bdde0b`:
  `mount_static(..., extra_dirs={"/static/ideapress": …})` and an `app_asset_url` filter; a test
  fetches all three over HTTP. In IdeaPress's CHANGELOG under *Fixed*.
* Four README compatibility tables and LoadCoach's README prose pinned `mirrorwall>=0.2.2,<0.3`
  and are checked by tests; all moved to `>=0.3.1,<0.4`.

## 4. Demonstration on the reference machine

The four units were restarted after the commits (they run editable installs). Over loopback:
FreeWeight's `/system` renders 10 status dots, IdeaPress's 3; LoadCoach's and PromptCadence's
pages answer `401` without their tokens (tokens exist, so every page needs one — spec §14), so
their dots are shown by their tests, not by `curl`. FreeWeight's `/runs/<unknown>/log` → `404`;
IdeaPress's `/static/ideapress/js/workspace.js` → `200`. **No application has `[console] url`
set**, so no strip renders on the machine; the tests render it under
`<APP>_CONSOLE__URL=https://jordan-main.local:8769`.

## 5. For the operator

1. **Nothing pushed, tagged or published** (§1). Versions held.
2. **To see the strip on the machine**, set `[console] url = "https://jordan-main.local:8769"` in
   each application's `config.toml` (the console's settings page writes it; restart the unit) —
   your call, not this row's.
3. **Release order** stays W10's: publish `mirrorwall 0.3.1` (now `be3797e`), re-cut every
   `ci.lock` (five repositories), push, tags when you have finished all the work.
4. IdeaPress's asset fix (§3) is a real behaviour change on the machine: the workspace's live
   section works in a browser now.

## 6. What runs next

Nothing is scheduled after WM2 in `roadmap/weightroom-work.md`. The verification of W10 (Gate D,
independent device) and the release sequence are the open items.
