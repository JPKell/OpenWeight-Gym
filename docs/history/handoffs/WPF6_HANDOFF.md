# WPF6 Handoff — an application's Overview renders inside its budget

**Row:** WPF6 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended · **Model:**
Claude Opus 5 · high · **Kickoff:**
`history/prompts/wpf6-weightroom-overview-inside-its-budget.prompt.md` (wave coordination:
`history/prompts/wave3-wpf6-summary.md`; wave 3, sole occupant)

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| WeightRoom | `29b98cf` | A | `overview_for` takes the shared `DatabaseUrlCache` and a monotonic reading; `web/routes/apps.py::app_page` passes `app.state.database_urls`; the budget test's LoadCoach sleeps a realistic `config show`; a unit test counts the launches; `CHANGELOG.md` under `[Unreleased] / Fixed` |
| WeightRoom | `e518a0d` | A | `merge: row/wpf6-overview-budget into main` |
| WeightRoom | this commit | B | This handoff; the live proof of §4; the row marked done |

Nothing pushed or tagged; no version bump (`[Unreleased]`, per the standing hold on the W arc).

**Gate, interpreter named:** WeightRoomGym at `29b98cf`, `.venv` **Python 3.14.4** —
`ruff format --check .` (235 files), `ruff check .`, `mypy src tests` (228 files),
`lint-imports` (5 contracts kept), `pytest` → **1897 passed, 3 skipped, 10 deselected**;
`pytest --cov` **90.50 %** total, against the 85 % floor. The performance marker is excluded from
that run by `addopts`, so the Overview budget was run separately:
`pytest tests/performance/test_budgets.py -m performance -k overview` → **6.1 ms (budget 300 ms)**.

## 2. The cause, exactly

`services/overview.py` called `effective_database_url(settings, app)` on every render — a launch of
`<app> config show --json`, which is a Python interpreter start. `web/app.py` builds
`app.state.database_urls`, a `DatabaseUrlCache`, for precisely that call, and every other
database-backed page of the console (`open_app_database`, `revision_summary`, the catalog, the
costs, the backups) already goes through it. The Overview was the one page that did not.

ADR-0133 rule 4 is untouched: the URL is still the application's own, read from its own
`config show`, only now once a minute per application rather than once per render.

## 3. What the tests now prove

1. **`tests/unit/test_overview.py::test_the_database_url_is_launched_once_per_ttl_not_once_per_render`**
   — the unit's fake `loadcoach` appends a line to `show.calls` on every `config show`. Three
   renders sharing one cache inside `URL_TTL_SECONDS` launch **once**; a fourth at `now=61.0`
   launches again, because a configuration file may have changed.
2. **`tests/performance/test_budgets.py::test_application_overview_with_the_application_running`**
   — W10 measured 3.0 ms here because the fake application answers in milliseconds, which faked
   away the very cost that broke the budget. Its LoadCoach now **sleeps 0.5 s** per `config show`
   (`CONFIG_SHOW_SECONDS`, the reference machine's figure) and serves the committed
   `loadcoach-0015` fixture database, so the budget is met only by not launching per render. The
   test also asserts the median is below one launch, naming why.

Both fail on the pre-fix code, checked by reverting the one call in place: the budget test measured
**512.9 ms against the 300 ms budget** and the unit test counted a launch per render.

## 4. The live proof (Gate B)

The reference machine, 2026-09-11, all four applications running, `weightroom.service` restarted
onto the merge (`e518a0d`, MainPID 1318106, 22:53:27 PDT).

**The browser, as WP6 measured it** — Playwright driving the system Google Chrome headless, desktop
1440 × 900, the LAN address `https://10.77.10.84:8769`, 3 loads per page, median:

| Page | First paint, WP6 (before) | First paint, now | First byte, now |
|---|---|---|---|
| `/apps/freeweight` | 508 ms | **188 ms** | 152 ms |
| `/apps/loadcoach` | 544 ms | **236 ms** | 203 ms |
| `/apps/ideapress` | 520 ms | **152 ms** | 129 ms |
| `/apps/promptcadence` | 580 ms | **180 ms** | 136 ms |
| `/apps/promptcadence/trajectories` (control, not an Overview) | 36 ms round trip | 160 ms | 118 ms |
| `/apps/loadcoach/queue` (control, WP6's slowest page inside budget) | 224 ms | 188 ms | 145 ms |

**Every Overview is inside spec §15's 300 ms**, and none is now slower than the controls that were
always inside it. The four were 508–580 ms at WP6.

**The render itself**, timed directly against the operator's own configuration and the four running
applications (`overview_for`, 5 calls, median; the script is in the session scratchpad):

| Application | A fresh cache each render (what the old code did) | The shared cache |
|---|---|---|
| freeweight | 362.3 ms | **4.9 ms** |
| loadcoach | 409.1 ms | **92.5 ms** |
| ideapress | 410.3 ms | **1.7 ms** |
| promptcadence | 476.2 ms | **8.6 ms** |

LoadCoach's 92.5 ms is its own `/system/status` call and its database read, not a launch.

**The "before" half of the browser table is WP6's**, measured the same way on the same machine the
day before. It was not re-measured in this session: doing so would mean putting the pre-fix code
back under the operator's live `weightroom.service`, and the direct timing above already shows the
same half second in the same tree.

## 5. What this kickoff got wrong

* **"a second Overview render within the cache's TTL launches no process"** is the right test, but
  the kickoff put it and the budget test in one gate with "implement" between them. The budget test
  is the one that needed changing *first*: it passed at 3.0 ms before and after the fix until its
  fake was made to cost what the real launch costs. The order that matters is *make the budget test
  able to fail*, then fix.
* **The kickoff's framing, "one cache call, and a test that no longer fakes the cost away"**, is
  accurate: the change is one call site, plus `urls`/`now` on `overview_for`'s signature (matching
  `open_app_database` and `revision_summary`, which already take both) and five test call sites.
* **Gate B needed a console login and the kickoff did not say so.** WP6 had reset the operator
  password and kept it in a scratchpad that is gone. At the operator's instruction (2026-09-11) it
  was reset again — `wr-gym operator password jpk --password-stdin`, **21 sessions revoked** — and
  the value is in this session's scratchpad. **Set your own password again.**
* **The budget test's console fixture is shared by every budget in the file**, so the 0.5 s sleep is
  given to LoadCoach alone. A sleep in all four would tax the table-page and shell budgets for no
  reason; the Overview measured here is LoadCoach's.

## 6. Open, for whoever comes next

* Nothing from this row. The remaining WPF row is **WPF8's Gate B**, the live calibration proof,
  which needs a clear GPU window.
* The console's operator password is the scratchpad value until the operator sets their own.
