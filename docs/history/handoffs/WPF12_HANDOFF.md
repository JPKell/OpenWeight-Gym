# WPF12 Handoff — the attempts table names the transport call

**Row:** WPF12 (`roadmap/weightroom-work.md`, wave 4) · **Ran:** 2026-09-12, unattended · **Model:**
Claude Sonnet 5 · **Kickoff:**
`history/prompts/wpf12-weightroom-the-attempts-table-names-the-transport-call.prompt.md` ·
**Ships:** unreleased, no version bump · **Branch:** `row/wpf12-transport-call`
(`~/ai/worktrees/weightroom-wpf12`, from WeightRoom `e225fdd`).

## 1. What shipped

| Commit | Gate | What |
|---|---|---|
| `3636cc2` | A | `transport_call` folded into the attempt cell of both the stage-run page's *Attempts* table and the unit page's *Provenance* table (`attempt N · round R · call C`); one line of copy above each table; `_attempt_row` (`services/ideapress_pages.py`) carries the field for the database-read path; two authored fixture rows (a discarded call and its retry) in `tests/fixtures/ideapress/unit.json` and `task-cancelled.json`; two new tests; `CHANGELOG.md` |
| `d14c17d` | A (fixed in review) | the one line of copy had the discarded/kept direction backwards — fixed same day, caught by orchestrator review before Gate B |
| (this file) | B | the handoff; Gate B's screenshots recorded below, not committed as binary files |

Gate every time, Python 3.14.4 at `.venv/bin/python` (this worktree's own venv): `ruff format
--check .`, `ruff check .`, `mypy src tests` (228 source files), `lint-imports` (5 contracts, 0
broken), `pytest -m "not live and not performance"` → **1899 passed, 3 skipped, 10 deselected**.
`git status --short` clean on both commits. Nothing pushed, nothing tagged, no version bumped.

## 2. Decisions this row took

**Both attempts tables, not one.** The collision map named only "the stage-run page's attempts
table" as mine, but Gate B's own text asks for a screenshot of *the unit page* rendering both
calls, and both pages build their attempt rows from the same `_attempt_row` function in
`services/ideapress_pages.py` — leaving one table showing `transport_call` and its sibling not
would itself be the inconsistency this row exists to close. Touching `_attempt_row` once and both
templates is the smaller diff, not a scope violation: no other row owns `ip_unit.html`,
`ip_task.html` or `ideapress_pages.py`, and WPF11's files are untouched
(`services/catalog.py` and the catalog routes/audit — confirmed by `git diff --stat` against this
row's commits, §1).

**The numbering fold, not a new column.** `attempt N · round R` was already this exact table's
own sub-sequence convention (a compound value in one cell, zero-based — `round 0` already appears
literally). Extending it to `attempt N · round R · call C` is "the kit's own style" the kickoff
asked to pick, needs no new column, and needs no grouping/total computation across rows (the
kickoff's alternative, "call 1 of 2", would need a total that no single attempt row carries and
that only exists by counting sibling rows — more code for the same fact).

**The corrections' worked example was inverted; I followed the code instead.** The brief's
corrections section describes authoring "a discarded call (`transport_call: 0, provider_error`)
followed by its retry (`transport_call: 1, completed`)". IdeaPress's own migration
(`0012_attempt_transport_call.py`) and `services/inference.py`/`services/stages.py` say the
opposite, unambiguously: **`0` is the call whose answer the attempt kept; `1` and up are calls
IdeaPress discarded and retried** (`_record_discard` always writes `outcome="provider_error"` at
`transport_call` 1, 2, …, and the kept call is whatever a normal `record_attempt` call passes,
which defaults to `0`). WPF7_HANDOFF §5's own Gate C table confirms it the same way ("`transport_call`
1 and 2" for two discarded calls). I built the fixture and the copy on the real semantics, not the
brief's example, and the orchestrator confirmed this in review (see the review note this row
received on `3636cc2`, which also caught that my *first* draft of the one-line copy had the
direction backwards in its own prose — fixed in `d14c17d`).

**The live evidence being gone changed Gate B's shape, not its target.** With WPF7's two projects
deleted, "against the reference machine's IdeaPress" is no longer possible; the brief's own
correction says to author a fixture and screenshot "your throwaway console serving that fixture."
That reading requires *something* HTTP-shaped in front of the console for a real browser to talk
to — `respx` only patches an in-process `httpx` client, which a real Playwright-driven browser
process cannot reach. I wrote a ~50-line stdlib `http.server` stub
(`stub_ideapress.py`, scratchpad-only, not committed) that serves `GET /api/v1/version`,
`GET /api/v1/projects/{id}`, `GET /api/v1/projects/{id}/units/U-01` and its `/history` straight
from the same fixture files Gate A's tests mock via `respx` — so both gates prove the same
authored data through their own path (in-process for A, over the wire for B) rather than two
fixtures that could drift apart.

## 3. The fixture

`tests/fixtures/ideapress/unit.json` and `task-cancelled.json` each gained one appended pair for
unit `U-01`, stage `revise`, `attempt` 1, `round` 2 — a round number not already used by either
fixture's existing entries, chosen so the new pair reads as a second revision round rather than
colliding with the existing `round` 0/1 data:

* `transport_call: 1`, `outcome: "provider_error"`, `error_code: "EMPTY_GENERATION"` (task fixture
  only — the unit fixture's existing attempts carry no `error_code` key at all, since
  `ip_unit.html`'s Provenance table has no Error column; the new rows follow that fixture's own
  convention rather than inventing one), 538 input / 8192 output tokens spent on the call that was
  thrown away.
* `transport_call: 0`, `outcome: "completed"`, 538 input / 257 output tokens, with a
  `degradations` entry naming `empty_generation_retried … with reasoning suppressed` — the same
  wording WPF7's `_without_reasoning` retry produces, and the same shape as WPF7_HANDOFF §5's live
  `project_review` retry (16 384 tokens/381 s empty, then 257 tokens/6 s).

Both files still round-trip byte-identically through `json.dumps(doc, indent=2,
ensure_ascii=False)` for their untouched entries (checked before writing — `unit.json`'s original
used `ensure_ascii=False`, which is why an earlier round-trip attempt showed a spurious em-dash
diff); the diff is a pure append in both files (`git diff --stat`: `+38`/`+86`, `-0`/`-0`).

## 4. Gate A — the tests

Two new tests, one per page, both against the fixtures above via the existing `respx`-based
harness (no live server, no GPU):

* `test_a_units_provenance_names_the_transport_call_of_a_discarded_retry`
* `test_a_tasks_attempts_name_the_transport_call_of_a_discarded_retry`

Each asserts the one-line copy is present, both `· round 2 · call 1` and `· round 2 · call 0`
render, `provider_error` and (task page only) `EMPTY_GENERATION` appear, and
`empty_generation_retried` names the retry. The full existing suite for both pages
(`test_a_unit_shows_sanitised_content_provenance_history_and_offers_revise`,
`test_a_cancelled_task_is_shown_as_its_state_not_as_an_error`, and the DB-mode
`test_a_stopped_task_reads_its_run_attempts_and_events_from_the_database` against the
`ideapress-0011-journey.sqlite3` fixture, which has no `transport_call` column at all) still pass
unchanged — the DB-mode path's `row.get("transport_call") or 0` degrades a pre-migration-0012
schema to `0` rather than raising or printing `None`.

## 5. Gate B — the live/browser proof

Built, not against the reference machine (its evidence is gone — §2), but against my own
throwaway console (`127.0.0.1:8789`, trust `8790`, own XDG tree under
`XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`XDG_STATE_HOME` in the session scratchpad) serving the fixture
above through the stub at `127.0.0.1:8791`. Recipe:

1. `wr-gym operator create jordan --config <scratchpad>/config.toml --password-stdin` — one
   operator, no wizard, `--start-console` never invoked (that flag touches
   `weightroom.service`, which is on the forbidden-unit list; this row never ran it).
2. `wr-gym serve --config <scratchpad>/config.toml` — the real CLI, real TLS (self-signed,
   auto-bootstrapped), real SQLite, in the background, verified listening on 8789/8790 by
   `ss -ltnp` and by `/proc/<pid>/cmdline` before anything was killed.
3. Playwright (`sync_playwright`, installed in a throwaway venv, not this repo's `.venv`) +
   `channel="chrome"` (system `google-chrome`, already on `PATH`), `ignore_https_errors=True`
   standing in for a trust step with no operator to hand it to. Logged in as `jordan`, then
   `GET /apps/ideapress/projects/01M27K4PP8AY6CN0BGB04B99JR/units/U-01` at 1440×900 and 412×915,
   `prefers-color-scheme` light and dark (WPF5_HANDOFF §9's recipe).

| Size | Theme | `scrollWidth` == `clientWidth` | `call 1` / `call 0` / `provider_error` present |
|---|---|---|---|
| 1440 | light | 1440/1440 | yes / yes / yes |
| 1440 | dark | 1440/1440 | yes / yes / yes |
| 412 | light | 412/412 | yes / yes / yes |
| 412 | dark | 412/412 | yes / yes / yes |

All four full-page screenshots were read by eye: the Provenance table's last two rows read
`revise · 1 · round 2 · call 1` (red `provider_error` badge) and `revise · 1 · round 2 · call 0`
(green `completed` badge, degradation note naming the reasoning-suppressed retry); the one-line
copy renders above the table in both corrected wording and directions; the table reflows to
stacked cells at 412 px with no horizontal scroll in either theme. Screenshots are session
artifacts only (`<scratchpad>/wpf12/shots/unit_{1440,412}_{light,dark}.png`), not committed —
this repository has no binary-screenshot convention and the brief did not ask for one.

Both processes were stopped by PID after verifying each PID's `/proc/<pid>/cmdline` named my own
config path/script (not by port-guessing or `pkill -f`); `ss -ltnp` confirmed 8789/8790/8791 clear
afterward. Nothing was started under `systemctl --user`, no shared unit was touched, and the GPU
was never involved — the stub server and the fixture data are entirely static.

I did not additionally screenshot the stage-run page (`ip_task.html`): Gate B's text names only
"a unit page," the same fixture pair also proves the stage-run page's identical treatment through
Gate A's `respx`-mocked test, and the two pages share one template pattern and one row-building
function — a second live screenshot would prove the same code path again, not a different one. If
the orchestrator wants it anyway: adding `GET /api/v1/projects/{id}/tasks/{task_id}` to `ROUTES`
in `stub_ideapress.py` (kept in scratchpad, not committed) is a two-line change, and the same
`shoot.py` pattern reaches `/apps/ideapress/projects/{id}/tasks/{task_id}` unmodified.

## 6. What the kickoff and its corrections got wrong

1. **The corrections' worked numbers were backwards** (§2): the intended example had `0` as the
   discarded call and `1` as the retry it kept; IdeaPress's migration and the two services that
   write these rows say the reverse. Followed the code, not the example.
2. **My own first draft of the one-line copy repeated that same inversion in prose** — "a
   `provider_error` there is that retry" read as naming the retry, not the discarded call — caught
   by the orchestrator's review of `3636cc2` before this row reached Gate B, fixed in `d14c17d`.
   Worth flagging because it means a plain-English gloss of a zero-vs-nonzero convention is easy to
   get backwards even after reading the source twice; the final wording says the direction
   explicitly both ways ("the call it threw away … the retry whose answer it kept") rather than
   relying on one adjective.

## 7. Left for review before merge

* The scope decision in §2 (both templates, not the one the collision map named) is the one thing
  in this row I'd most want a second opinion on before merge — it reads as the coherent choice to
  me, but "own the stage-run page's attempts table" was written on purpose and I did not ask before
  extending it.
* Gate B's stub-server approach (§5) is a new pattern for this repository's throwaway-console
  rows, which have so far pointed at real running applications (WPF5) rather than a hand-written
  fixture server. It is not committed anywhere, so it costs nothing to reject, but future rows
  hitting the same "the live evidence is gone" problem may want to reuse or generalise it rather
  than reinvent it.
