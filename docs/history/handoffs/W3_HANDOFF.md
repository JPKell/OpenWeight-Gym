# W3 Handoff — WeightRoomGym Phase 3: telemetry strip and the shell

**Row:** W3 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Sonnet 5 · high).
**Date:** 2026-09-09. **Kickoff:** [`w3-weightroom-p3-telemetry-shell.prompt.md`](../prompts/w3-weightroom-p3-telemetry-shell.prompt.md).
**Ships:** `wr-gym 0.3.0`, **prepared, not tagged, not pushed, not published.** `mirrorwall 0.3.0`
pinned as an editable path install (prepared, not yet published itself — **TODO: re-pin
`mirrorwall==0.3.0`** once it is; `pyproject.toml`'s dependency range is already `>=0.3,<0.4`).

## 1. What was built, by commit

| Commit | Gate | What |
|---|---|---|
| `c675249` | A | `services/telemetry.py` (the `TelemetryService`, the sampler thread, snapshot→row, the resident cache, the retention/downsample sweep); migration `0002` (`telemetry_samples`); `GET /system/telemetry/stream\|history`, `GET /system/resident`; `/system/status` completed with `ollama` and `telemetry`; tests (fault-injecting reader, downsample/retain, SSE replay, lifecycle) |
| `2de2472` | B | `mirrorwall` re-pinned to `0.3` and installed editable; `_shell.html` (app tabs with status dots, the telemetry strip with the RESIDENT/QUEUE meters, the console page ghosts, the operator chip, the left menu); `render_shell_page`/`app_side_nav`/`app_side_nav_stubs`; every existing page converted to extend it; tests |
| `f1a4e2a` | C | `services/overview.py` (figures from the API or a `COUNT(*)`, the primary table always from the database, the known-revision degrade); `app.html` rebuilt as the real Overview (`card(kind="figure")`, `table(density="dense")`, `log_pane`); `CHANGELOG`; `0.3.0`; tests |
| `4c82c51` | — (found while demonstrating) | `GET /telemetry/history`: a plain inline SVG line (`sparkline_svg`, no chart library) and a small script making the strip's fields clickable — see §2.3 |
| `523a962` | — (post-handoff interview, §2.5) | The four fixture databases at `tests/fixtures/databases/`, ahead of W7 |
| `4afb0db` | — (post-handoff interview, §2.5) | The Overview footer's accurate wording (and the `\| capitalize` bug it surfaced); RESIDENT/QUEUE live-updating |

Full local gate, `WeightRoom` (Python 3.14.4, `.venv`): `ruff format --check .` (114 files),
`ruff check .` clean, `mypy src tests` clean (106 files, strict), `lint-imports` 5 contracts
kept, `pytest -m "not live and not performance"` **614 passed, 1 skipped** (the PostgreSQL
migration test, no server here), coverage **90.10 %** (floor 85 %); `wr-gym config reference
--check` matches.

## 2. What this row was asked to decide, and what it decided

### 2.1 The primary table reads the database in every state, not only when stopped

Spec §7.3's per-application table reads as API-when-up for "the listing" too, and the letter of
that table is not what `services/overview.py` does: the primary table (`models`, `projects`,
`trajectories`, …) is read through a direct, read-only connection to the application's own
database **whether or not the application is running**. Two things pushed that way, both
recorded in the module's own docstring so the decision travels with the code:

1. Spec §10 and the data model's own cross-reference table (§4) already list "database" as a
   legitimate read path for every application generally, not one reserved for the stopped case —
   the narrower API-when-up reading is really about the **figures**, which need a live number a
   static row cannot give (a queue depth, an open circuit breaker), not about a **listing**,
   which a database answers exactly.
2. Decisively: each application's list endpoint (`GET /models`, `GET /projects`, …) has its own
   JSON shape, undocumented at the field level in any `api.md` skimmed for this row, that would
   need reading and pinning **per application** before a row of it could render here. Every
   application already exposes the one shape every row needs — `alembic_version` plus a handful
   of named tables (data model §4) — through the same read-only connection this row already opens
   for the stopped case. Building four list-response parsers is real work with no shortcut, and
   this row's job is the shell and the strip, not a fifth reader per application; **W7's guarded
   database viewer is where a *browsable* table belongs**, and this Overview table is content to
   be a read of the same rows, once.

**Resolved same day, after the operator reviewed this decision:** the footer now names both
halves when they differ (`_compose`, `services/overview.py`) — "Figures from the API; table: the
database at revision 15" — rather than the single word "api" implying the table came from there
too (commit `4afb0db`). Fixing this also surfaced a real bug: `app.html`'s `| capitalize` Jinja
filter lower-cases the rest of the string, so "from the API" had been rendering as "From the api"
since Gate C — found only by actually reading the rendered HTML rather than trusting the test
assertions, which had never checked the exact string. Both fixed together.

### 2.2 RESIDENT and QUEUE — resolved same day

Originally shipped page-load-only: the strip's generic CPU/GPU/RAM/VRAM fields are wired live by
MirrorWall's own `telemetry.js` against the SSE stream's payload, but the two WeightRoomGym-
specific meters this row adds — RESIDENT (VRAM of the primary GPU's resident model) and QUEUE
(LoadCoach's queue depth) — were computed server-side at render only, needing a reload to change.
**Fixed same day** (commit `4afb0db`) rather than left as a gap: `_shell.html` opens a second
`mirrorwallSse` connection to the same stream (`meter()` has no live-update hook of its own for a
two-field, one-consumer addition — design brief §5's "one consumer stays here" case again) and
matches the two meters by their label text, since the macro gives them no other hook.

### 2.3 Clicking a telemetry figure — and no ECharts to open it with

Phase 3 acceptance criterion 1 asks that clicking VRAM open a 24-hour chart. MirrorWall 0.3 did
not vendor ECharts — its seven Phase 3 components (design brief §5) are the tokens, the strip's
meters, the tables, the log pane and the two navs, not a chart container, and `WM_HANDOFF.md` §1
confirms only htmx, its SSE extension and JetBrains Mono were vendored. Building ECharts
vendoring is not this row's job either. Closed the gap with what was available instead: `GET
/telemetry/history` renders a plain, server-built inline SVG polyline
(`services/telemetry.py:sparkline_svg`, no library, ADR-0020 rule 5 — the page is complete
without JavaScript) over the same downsampled rows the JSON endpoint already serves, and a small
script in `_shell.html` makes the strip's `[data-field]` spans clickable and keyboard-operable
without forking MirrorWall's `telemetry_bar.html`. A later row can swap the SVG for ECharts
behind the same URL once MirrorWall vendors it.

### 2.4 Not every spec §7.3 page has a row yet — resolved by operator interview

Each application's left menu names every page spec §7.3 lists; only `Settings`/`Providers`/
`Tokens` (W4) and `Database` (W7) carry a phase, because those are the only ones
`roadmap/weightroom-work.md` schedules between W3 and W10. `Models`, `Runs`, `Routing`, `Queue`,
`Evidence`, `Adapters`, `Reliability`, `Projects`, `Units`, `Workflows`, `Backends`,
`Trajectories`, `Approvals`, `Tiers`, `Tools`, `Ledger`, `Egress` and a dedicated per-application
`Logs` page had **no row** in the roadmap as of this row.

**Operator decision (2026-09-09, post-handoff interview): fold them into W7–W9.** These pages do
not get rows of their own; they land inside the existing catalog (W8), jobs/alerts/prompts (W9)
and database-viewer (W7) rows as each is built, rather than expanding the roadmap with a row per
page or per application. `app_side_nav_stubs`' phase map (`web/rendering.py`) should be widened
at whichever row actually lands each page, not before.

## 2.5 Operator decisions from the post-handoff interview (2026-09-09)

Five more questions were put to the operator once this row's own choices were read back:

1. **The primary table stays database-sourced in every state** (§2.1) — confirmed, no change;
   W7's guarded viewer is still where a browsable, API-capable table belongs.
2. **The telemetry-history chart stays a plain SVG** (§2.3) — confirmed; no MirrorWall row is
   scheduled to vendor ECharts on the strength of this alone.
3. **The four fixture databases were built ahead of W7**, not left for that row to discover
   missing (§4 item 1, below) — done this session, commit `523a962`.
4. **The Overview footer's imprecise wording was fixed now**, not left for W7 (§2.1) — done,
   commit `4afb0db`.
5. **RESIDENT/QUEUE were made to live-update now**, not left as a documented gap (§2.2) — done,
   commit `4afb0db`.

## 3. Other decisions taken in this row

1. **`telemetry_samples.id` is a plain autoincrement integer**, the one table in this schema not
   given a ULID — it doubles as the SSE frame's id, resumed with `Last-Event-ID > id`, a numeric
   comparison a lexicographic ULID does not need and does not help.
2. **The SSE stream replays by polling the store**, exactly FreeWeight's run-event-store pattern
   and this application's own log stream (`web/routes/apps.py`) — no in-memory fan-out, so a
   restarted console loses nothing a reconnecting client had not already seen.
3. **Resident models are cached for five seconds**, not sampled every tick — asking Ollama once a
   second buys nothing visible and costs a process-local HTTP round trip on the sampler's own
   thread every tick. LoadCoach's queue depth is never persisted at all: a second application's
   live number, read fresh for `/system/resident` and folded into the SSE frame's payload only.
4. **The downsampling sweep groups in Python**, not a dialect-specific date-truncation function,
   so the identical sweep runs on SQLite and PostgreSQL (ADR-0006) — keeps the newest row in each
   aging minute, drops the rest, and drops anything past `history_hours` outright.
5. **The database URL for the stopped-state read comes from `<app> config show --json`**
   (`values.storage.database_url` — the actual shape, confirmed by running it against the
   reference machine's FreeWeight and LoadCoach installs; it is **not** the flat shape the
   source's own variable naming suggested at a skim). This is the "CLI" read path data model §4
   already names, not a new one.
6. **`side_nav`'s macro never receives a dead link.** A page this build has not shipped renders
   as inert text (`app_side_nav_stubs`) beside the macro's own `<ul>`, not as an `href=""` inside
   it — the macro's `link` shape has no inert state, and inventing one belongs to MirrorWall, not
   to a page consuming it once.
7. **Every operator-facing page extends `_shell.html` now**, not `mirrorwall/base.html` directly;
   login, the error page and the standalone trust page are the three exceptions (no session, or
   nothing to show tabs for). `render_shell_page` (`web/routes/apps.py`) is the one function that
   supplies the shell's context, so a page rendered without it hits `StrictUndefined` immediately
   — deliberate: a shell page missing its context is a defect, not a page quietly missing a dot.
8. **`APP_STATUS_DOT`** (renamed from `services/health.py`'s private `_APP_STATUS`) is the one
   pill-to-status-dot map, read both by `GET /health`'s component status and by the shell's
   `status_dot` — one vocabulary, not two coincidentally agreeing tables.

## 4. What the kickoff got wrong, or did not know

1. **No fixture databases existed yet at `tests/fixtures/databases/`.** The kickoff's "the
   fixture databases from W0's seeded revisions" assumes W0 or W1 built them; neither did —
   `W1_HANDOFF.md` §2 seeded `known_revisions`' four rows but wrote no `.sqlite3` files, and W7's
   own kickoff (`w7-weightroom-p7-db-viewer-guard.prompt.md`) still describes them as work to do.
   This row's own tests build synthetic SQLite databases at test time with raw `sqlite3` instead
   (the FreeWeight M6 memory note: a gitignored binary fixture is how a CI run goes red for a
   reason nobody in the diff can see). **Built as a same-day follow-up per the operator's
   interview decision** (commit `523a962`): each of the four migrated to its known head through
   the application's own migration runner against a throwaway database, plus one hand-stamped to
   an unknown revision — `tests/fixtures/databases/README.md` records how, and how to regenerate.
2. **No application's `alembic_version` has moved since W1** (`freeweight` `0009`, `loadcoach`
   `0015`, `ideapress` `0010`, `promptcadence` `0011` — checked against each repository's
   `infrastructure/db/migrations/versions/` directly). `known_revisions` needed no new row.
3. **MirrorWall 0.3 did not vendor ECharts**, which the design brief's dependency list (spec §5)
   and Phase 3's own criterion 1 both read as already available — see §2.3.

## 5. Demonstration (Phase 3 acceptance criteria)

1. **The console matches the artboard.** Verified structurally (`tests/integration/test_shell.py`):
   four `app_tab`s with `status_dot`s on every page, the telemetry strip with
   `data-telemetry-url="/api/v1/system/telemetry/stream"`, the RESIDENT/QUEUE meters, a per-
   application `side_nav` with Overview selected. "The strip moving once a second" is
   `TelemetrySampler`'s own behaviour (Gate A's lifecycle tests: start, tick, `latest()` non-null,
   clean stop) streamed unchanged through MirrorWall's `telemetry.js`; not run against a browser
   in this environment. Clicking a figure now opens `/telemetry/history` (§2.3), proven end to
   end (`tests/integration/test_telemetry_routes.py`).
2. **Pulling the GPU sensor.** Proven at the unit level, not on real hardware in this environment
   (no GPU here): `TestSnapshotToRowDegradesHonestly` wraps `sweatmeter`'s own
   `FaultInjectingReader`/`NullGpuReader` around the collector and asserts every GPU-derived
   column is `None` — never `0` — while every host field is unaffected. The wire shape
   (`sample_to_json`) renders an empty `gpus` list in exactly that case, which MirrorWall's
   `telemetry.js` already treats as "no device at this index" rather than a zero reading.
3. **Every application stopped.** Proven end to end with a synthetic per-application database and
   a fake CLI answering `config show --json` (§5's smoke script, folded into
   `tests/unit/test_overview.py` and `tests/integration/test_shell.py`): all four tabs show
   `stopped`, and the Overview renders `From the database at revision 0015.` with the `models`
   table's one row, exactly as the design brief asks.

## 6. Verification a reviewer can repeat

```bash
cd WeightRoom && source .venv/bin/activate
pip install -e ../py/MirrorWall --no-deps   # 0.3.0, prepared not published — see the TODO above
ruff format --check . && ruff check . && mypy src tests && lint-imports
pytest -m "not live and not performance" --cov --cov-report=term-missing
# 616 passed, 1 skipped, coverage 90.21% (after the post-handoff follow-ups, §2.5)
wr-gym config reference --check
```

## 7. What is deferred, unchanged from the kickoff

Settings, the doctor, docs, chat and the database viewer — W4 through W7, per the development
plan's own Phase 3 scope line. §2.4's question is answered (fold into W7–W9, §2.5); nothing is
left open from this row.
