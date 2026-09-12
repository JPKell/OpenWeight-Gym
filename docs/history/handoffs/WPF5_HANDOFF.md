# WPF5 Handoff — FreeWeight's Dashboard and System, LoadCoach's System

**Row:** WPF5 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11/12, unattended · **Model:**
Claude Sonnet 5 · high · **Kickoff:**
`history/prompts/wpf5-weightroom-dashboard-and-system-pages.prompt.md` (wave coordination:
`history/prompts/wave2-wpf5-summary.md`)

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| FreeWeight | `028493f` | A | `GET /api/v1/dashboard` — summary cards and the model × suite comparison heatmap, with FreeWeight's own `separated` marking; `services/results.py::dashboard_summary_json`; tests first (`tests/e2e/test_dashboard.py::TestTheApiRoute`); OpenAPI snapshot regenerated |
| WeightRoom | `05af109` | A | `apps/freeweight/api.md` §5a (the new route) edited before the code, mirrored byte-identically into FreeWeight's own `docs/`; spec §7.3 amended for the three pages judged needed and the two judged not needed |
| WeightRoom | `94553e6` | B | FreeWeight's **Dashboard** and **System** pages, LoadCoach's **System** page; `_APP_PAGES`/`_PAGE_HREF` updated; `services/freeweight_pages.py::dashboard_api,system_api`, `services/loadcoach_pages.py::system_api`; fixtures recorded from each application built in this row's own worktree; two new integration test files, tested running, stopped and against the injection corpus |
| WeightRoom | this commit | C | This handoff; the live proof of §4; the row marked done |

Nothing pushed or tagged; no version bump in either repository (both under `[Unreleased]`).

**Gates, interpreter named:**

* **FreeWeight** at `028493f`, `.venv` **Python 3.14.4** (`mirrorwall` and `setspec` installed
  editable from `py/MirrorWall` and `py/SetSpec` — PyPI's `mirrorwall 0.3.0` and `setspec 0.6.0`
  lag the local `0.3.1`/`0.6.0+` sources this branch needs; not this row's problem, noted so the
  next session does not re-diagnose it): `ruff format --check .`, `ruff check .`, `mypy src tests`
  (324 files), `lint-imports` (4 kept), `pytest -m "not live and not performance"` →
  **2735 passed, 30 skipped**; `--cov=freeweight` **90%** total (`services/results.py` 93%,
  `web/routes/dashboard.py` 91%), held against the 85% floor.
* **WeightRoomGym** at `94553e6`, `.venv` **Python 3.14.4** (same two editable installs):
  the same gate → **1880 passed, 3 skipped**, `lint-imports` 5 contracts kept,
  `pytest tests/security -q` **658 passed** (the audit-route registry and the redaction sweep
  are both unaffected: every new route is a `GET`, so neither the state-changing-route exercise
  list nor a security row applies), `--cov=weightroom` **90%** total (`services/freeweight_pages.py`
  93%, `services/loadcoach_pages.py` 90%, `web/routes/freeweight.py` 95%,
  `web/routes/loadcoach.py` 93%), held against the 85% floor.

## 2. Decisions taken

1. **The API addition is scoped to the summary and the heatmap, not the whole Dashboard.**
   FreeWeight's own Dashboard also renders two scatter charts (quality vs. speed, quality vs.
   VRAM) and seven metric panels (token economy, context, audit, tools, judge bias, goals,
   energy). The kickoff's own decision list says the route answers "the summary and the heatmap
   cells" — nothing outside FreeWeight's own page reads the panels or the scatter data, and
   building an API surface for seven more panels nobody asked for would be exactly the
   speculative surface the workspace's conventions warn against. `dashboard_summary_json` in
   `freeweight/services/results.py` serializes only `Dashboard.cards` and `Dashboard.heatmap`.
2. **`cells` is a sparse list, not a grid.** JSON has no tuple keys, and most `(model, suite)`
   pairs are unmeasured; each cell carries its own `model` and `suite`. An unsupported cell's
   `value` is the string `"unsupported"`, matching `GET /results`' existing convention for the
   same fact (ADR-0016).
3. **`since` reuses `web/query.py::parse_instant`**, which raises `ValidationError` (a
   `SuiteError`) rather than the HTML route's own bare `ValueError` catch — the API route lets
   FreeWeight's global exception handler build the envelope, exactly as `GET /results` does. The
   HTML page's own `/dashboard` route is unchanged; only the new `/api/v1/dashboard` was touched.
4. **FreeWeight's System page needs no new route.** `GET /health` already carries `version`,
   overall `status` and the ten components (`services/freeweight_pages.py::system_api` is one
   line). A `503` (a component `unavailable`) is read by the console's client as a refusal, so
   that state renders as the page's refusal rather than a component table with nothing in it —
   FreeWeight's own System page has no lesser-content fallback for that case either.
5. **LoadCoach's System page needs no new route either.** `GET /health` and the already-existing
   `GET /system/status` (built at WP2 for Queue) together carry everything except two fields
   LoadCoach's own page shows from in-process state: **workers** (`len(runtime.workers)`, a
   thread count with no wire form) and the **machine fingerprint** (computed in-process, never
   served). Both render as text naming that they are not served, exactly as WPC1 did for
   PromptCadence's bind host and port (`WPC1_HANDOFF.md` §2 item 8) — a candidate additive field,
   not added here. Dispatch latency, starving, active jobs, dispatch state, residency and circuit
   breakers already have a home on Queue and Reliability (WP2); this page links there rather than
   repeating them, matching PromptCadence's System page linking to Ledger and Approvals.
6. **Menu placement.** *Dashboard* sits among FreeWeight's own pages, right after *Results* — the
   cross-model complement to a per-model query, which is also where the kickoff's own framing put
   it ("Results is a metric query and Compare works per subject"). *System* sits in the
   administrative section (`_ADMIN_PAGES`, already carrying PromptCadence's `System` from WPC1),
   immediately before *Settings*, for both FreeWeight and LoadCoach.
7. **Fixtures were recorded from each application built in this row's own worktree**, run against
   `modelrack.testing.FakeProvider` — no GPU, no Ollama, no network — because the reference
   machine's FreeWeight predates `GET /api/v1/dashboard` (this row adds it) and LoadCoach's own
   System page has none of this row's new console traffic to record from. The technique is
   `tests/e2e/test_dashboard.py`'s own: a real `TestClient` over `create_app`, one
   `native.echo` run for FreeWeight, an idle boot for LoadCoach. FreeWeight's fixture carries a
   real `1.0` `harness_roundtrip_success` and one genuinely `unsupported` metric (GPU telemetry,
   absent under `FakeProvider`); LoadCoach's carries its real five components and an idle queue.
8. **No `EXERCISES` entry, no audit row, no OpenAPI snapshot change on WeightRoomGym's side.**
   All three new routes are `GET`s: spec §11 contract 2 (one audit row per state-changing action)
   does not apply, and `tests/security/test_audit_routes.py::test_every_state_changing_route_has_an_exercise`
   passed unmodified. WeightRoomGym's own OpenAPI snapshot is unaffected because every UI route
   is `include_in_schema=False` — the same finding WPC1 recorded for PromptCadence's System page.

## 3. Parity with each application's own page

| FreeWeight `GET /dashboard` (`web/templates/dashboard/index.html`) | Console `…/dashboard` |
|---|---|
| Filter bar: suite, model, machine, since | the same four, `GET`, same names |
| Summary cards: completed runs, models measured (× suites), samples stored, unsupported measurements, machines, latest run | the same six figures, from `GET /api/v1/dashboard`'s `cards` |
| Comparison heatmap, one headline metric per suite, *separated* warning | the same, from `heatmap`; an empty cell is `—`, never blank-as-zero |
| Two scatter charts (quality vs. speed, quality vs. VRAM) | **absent** — no route serves them (§2 item 1) |
| Seven metric panels (token economy, context, audit, tools, judge bias, goals, energy) | **absent** — no route serves them (§2 item 1) |
| Stopped: renders from the database | **absent** — reads only the running API, with the Overview's Start form, matching Results/Compare/Evidence/Provider (WP3_HANDOFF.md §2 item 5) |

| FreeWeight `GET /system` (`web/templates/system/index.html`) | Console `…/system` |
|---|---|
| Application, version, health | the same, from `GET /health` |
| Ten health components with status and detail | the same ten, same table shape |
| Documentation links | **absent** — the console has its own Docs viewer (spec §7.5); not this page's job |

| LoadCoach `GET /system` (`web/templates/system/index.html`) | Console `…/system` |
|---|---|
| Version, health, five health components | the same, from `GET /health` |
| Machine fingerprint | **absent** — not served by the API (§2 item 5); the page says so |
| Workers (`len(runtime.workers)` of `max_concurrent_jobs`, in flight) | **absent** — not served by the API (§2 item 5); the page says so and points at Settings |
| Dispatch latency, starving, active jobs, dispatch state | **linked**, not repeated — already on Queue (WP2) |
| Telemetry, resident models, circuit breakers | **linked**, not repeated — Telemetry is the console's strip (spec §7.7); residency and breakers are already on Reliability (WP2) |

## 4. Gate C — the live proof

**No browser, no screenshots, no systemd unit** — see §5 for what that leaves for the operator.
What *was* proven live: WeightRoomGym's console, talking real HTTP (no `respx`, no mock) to a
real FreeWeight and a real LoadCoach, each `<app> serve` under `modelrack.testing.FakeProvider`
on a throwaway port (`18765`, `18766`) in the session scratchpad, migrated fresh, with one
`native.echo` run completed on FreeWeight.

```
/apps/freeweight/dashboard 200 True   (the fixture's page_source says "From the API")
/apps/freeweight/system    200 True
/apps/loadcoach/system     200 True
dashboard shows the live model: True   (fake/fake-model:8b-q8_0@sha256:fa4efa4efa4e)
freeweight system shows all ten components: ok
loadcoach system shows all five components: ok
LIVE PROOF PASSED
```

This exercises the real wire path `respx`-mocked tests cannot: real query-string serialization,
a real JSON body FreeWeight and LoadCoach actually produced, and a real round trip through
`app_api.call`. Both throwaway servers were started as plain background processes (not systemd
units — see §5), verified running by PID, and killed by that same PID after the proof; nothing
was left behind. FreeWeight's own `/dashboard` and `/system` and LoadCoach's own `/system` were
also fetched directly (`curl`) from the same two servers, confirming the content this row's pages
claim parity with is what those pages actually render, not a recorded fixture nobody re-checked.

## 5. What the operator's attended session still needs to do

The kickoff's Gate C asks for both themes and phone width, screenshots, **and** running vs.
stopped — the last of which needs a real `systemctl --user` unit for FreeWeight and LoadCoach (or
the reference machine's own units), which this row's hard constraints put out of reach: no
`systemctl --user` action on `freeweight.service` or `loadcoach.service` without asking, and the
GPU stays the operator's for the session. §4's live proof establishes the *data* is correct end to
end; it does not establish the *rendering* in dark mode or at 412px, because that needs a browser
this environment does not have installed (`playwright` is not on `PATH` or in any repo's `.venv`;
`google-chrome` is, but driving it without Playwright's automation is not worth building here).

**To finish Gate C exactly as written:**
1. `pip install playwright && playwright install chromium` in a throwaway virtualenv (or reuse
   the one WP3/WPC1's sessions used, if it still exists in a prior session's scratchpad).
2. Start FreeWeight and LoadCoach as this row's proof did (§4's two `serve` invocations,
   throwaway config, `FREEWEIGHT_PROVIDER__KIND=fake`/`LOADCOACH_PROVIDER__KIND=fake`), or point
   at the reference machine's real units if the operator prefers real data.
3. A throwaway WeightRoomGym console on port **8799**, own XDG tree (as this row's worktree
   convention states), `[apps.freeweight] base_url`/`[apps.loadcoach] base_url` pointed at
   step 2's ports.
4. Playwright + system Chrome, both themes (`prefers-color-scheme` or the console's own toggle)
   and phone width (412px), screenshot `/apps/freeweight/dashboard`, `/apps/freeweight/system`,
   `/apps/loadcoach/system` beside `http://127.0.0.1:18765/dashboard`,
   `http://127.0.0.1:18765/system`, `http://127.0.0.1:18766/system`.
5. Stop one application (a real unit, or restart the throwaway `serve` process's absence) and
   confirm the console's page still renders with the Overview's *Start* form and the
   "reads only from its running API" footer — already proven by
   `tests/integration/test_freeweight_dashboard_system.py::test_a_stopped_dashboard_reads_only_from_the_api`
   and its System-page and LoadCoach counterparts against a mocked stopped unit; a live rerun is
   the remaining visual confirmation.

## 6. What the kickoff got wrong

* Nothing substantive. The one imprecision: the kickoff's "What WP6 found" section describes
  FreeWeight's Dashboard as showing "a model × suite heatmap of one headline metric from each
  latest completed run" without mentioning the two scatter charts or the seven metric panels that
  page also renders — WP6's own finding table (§3) is accurate about scope ("the summary and the
  heatmap cells"), but a reader of the kickoff's narrative alone could reasonably expect the panels
  too. §2 item 1 above states the scoping decision and the reason explicitly, so this does not
  need to be relitigated at WP6's next-door row.
* The kickoff's suggested read order names `apps/freeweight/api.md` §1 and `apps/loadcoach/api.md`
  §1 as "Code to read first" for the two applications' System routes; the routes actually needed
  were `web/routes/system.py` (both applications) and, for LoadCoach, `web/routes/queue.py`
  (`GET /system/status` is defined there, not in `system.py`) — a detail the kickoff's own
  "Code to read first" list gets right by naming the files, just not by which module owns which
  route.

## 7. For the operator

1. Nothing was left running: both throwaway `freeweight serve`/`loadcoach serve` processes from
   §4 were killed by PID after the proof, and their databases live only in the session scratchpad.
2. No `systemctl --user` action was taken on any shared unit, and no GPU was touched.
3. `git status --short` is clean in both worktrees at the end of this row (checked below).
4. The visual half of Gate C (§5) is the next thing to do on this row before merge, if the
   operator wants it done before the two other wave-2 rows land; nothing in it blocks the code.

## 8. What runs next

Per the wave note, this row **merges last** in both FreeWeight and WeightRoomGym, after WPF2
(and WPF4 for WeightRoomGym). The operator rebases `row/wpf5-dashboard-system` onto each repo's
merged `main`, regenerates the OpenAPI snapshot and `api.md` from a scratch XDG tree rather than
hand-merging (same rule WP3/WP5 used), and resolves `rendering.py`/`weightroom-work.md` by hand —
this row is the only one touching `rendering.py` and the §14 registry this wave, so the conflict,
if any, is textual proximity in `weightroom-work.md`'s row list, not a logic conflict.

## 9. The browser half of Gate C, run 2026-09-12 (operator interview)

Playwright against the system Chrome (`channel="chrome"`, headless), a throwaway console on
`127.0.0.1:8779` with its own XDG tree and no operator, its `[apps.*]` pointed at the reference
machine's **own** FreeWeight, LoadCoach, IdeaPress and PromptCadence (real data, reads only; no
unit touched, GPU idle after WPF9). `/apps/freeweight/dashboard`, `/apps/freeweight/system`,
`/apps/loadcoach/system` and, for WPF2's adapter field, `/apps/freeweight/runs` — each in
`prefers-color-scheme` light and dark, at 1440×900 and 412×915, full-page screenshots read by eye
plus a probe of `document.documentElement.scrollWidth` against `clientWidth` and of every element
wider than its box without `overflow-x: auto`.

| Page | 1440 light/dark | 412 light/dark |
|---|---|---|
| FreeWeight Dashboard | renders; the *Latest run* card's value ran past its right edge | **`scrollWidth` 442 on a 412 viewport** — the page scrolled sideways; culprit `UL.card-grid` |
| FreeWeight System | ok | ok (`412/412`; the components table scrolls inside its own wrapper) |
| LoadCoach System | ok | ok |
| FreeWeight Runs (adapter field) | ok, field present under `llamacpp` | ok, form stacks |

**The one defect** was this row's own: `fw_dashboard.html` passed the full RFC 3339
`latest_run_at` (`2026-09-12T05:23:57.516Z`, 24 characters) as a `kind="figure"` card value —
mono, `--mw-font-size-figure`, no wrap — which no card width on any viewport fits. Fixed the same
day: the date is the figure and the clock is the note (*Completed at 05:23:57 UTC.*), with a test
that the full stamp no longer appears in the page. After the fix every page probes
`scrollWidth == clientWidth` at both widths in both themes. The general hardening — a
`overflow-wrap: anywhere` on MirrorWall's `.card-value` — is a package change and was left alone;
every other `card-grid` page renders numbers or short words there.

**Not run:** §5 step 5, the stopped-application rendering, because it needs a shared unit stopped;
the three `test_a_stopped_*` tests stay its proof.
