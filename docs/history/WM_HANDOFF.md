# WM Handoff — MirrorWall 0.3: the WeightRoomGym design brief's tokens and generic components

**Row:** WM of [`roadmap/weightroom-work.md`](../roadmap/weightroom-work.md) (Sonnet 5 · high).
**Date:** 2026-09-09. **Kickoff:** [`wm-mirrorwall-0.3.prompt.md`](wm-mirrorwall-0.3.prompt.md).
**Ships:** `mirrorwall 0.3.0`, **prepared, not published** — the design brief's token deltas and
seven generic components, additive; every existing consumer renders byte-identically until it
opts in.

## 1. What was built, by commit

| Repository | Commit | What |
|---|---|---|
| `py/MirrorWall` | `0f34758` | Gates A+B: tokens (`--mw-font-size-*`, `--mw-sidebar-w`, `--mw-label-tracking`, `--mw-meter-h`, `--mw-row-h-comfortable`, the four `--mw-status-*` pairs, both themes), JetBrains Mono vendored (two `@font-face` rules, SIL OFL 1.1), htmx 2.0.10 + htmx-ext-sse 2.2.2 vendored (0BSD, 19 075 B gzipped combined); the seven macros (`status_dot`, `app_tab`, `meter`, `card(kind="figure")`, `table(density=…, column.mono)`, `log_pane` + `log_pane.js`, `side_nav`); `base.html`'s opt-in `mirrorwall.htmx` gate and `hx-headers` CSRF token; snapshot tests for every new macro in both themes, a Node DOM-harness suite for `log_pane.js`, the vendor exemption in the vocabulary scan |
| `py/MirrorWall` | (this row, uncommitted at write time) | Gate C: `__about__` → `0.3.0`, `CHANGELOG.md` (`[0.3.0]` section folding the prior `[Unreleased]` bullets in), `README.md` status line, `docs/packages/mirrorwall/{spec,development-plan}.md` Phase 4 section (mirrored byte-identically from `WeightRoom/docs/`), `tests/snapshot/test_weightroom_shell_demo.py` — the row's demonstration, composing the shell skeleton from 0.3 macros alone |
| `WeightRoomGym` (`WeightRoom/docs/`) | (this row) | `packages/mirrorwall/{spec,development-plan}.md` edited first (Phase 4 section, Status line, Decision records, Components row, §21 future-extensions bullet removed since density is now shipped); `roadmap/weightroom-work.md` row marked done; this handoff |

Nothing pushed, tagged or published, per standing instruction.

## 2. Gates, as actually run

* **Gate A (tokens).** All new/changed tokens verified against `tests/unit/test_tokens.py`
  (contrast, `tokens.json` agreement, no colour outside a media query, no hard-coded colour outside
  `tokens.css`) — 55/55 passing including the four new status pairs.
* **Gate B (components).** 44 snapshot assertions across every new macro plus every macro whose
  signature changed, each with an explicit "renders unchanged when the new parameter is omitted"
  test; 5 Node-harness tests for `log_pane.js`.
* **Gate C (release-prepared).** `CHANGELOG.md`, `__about__` `0.3.0`, docs mirrored and `cmp`-proven
  identical, roadmap row marked done.
* **Demonstrate.** `tests/snapshot/test_weightroom_shell_demo.py` composes the artboard's shell —
  four `app_tab`s with dots (one selected), a `telemetry_bar` with two extra `meter`s (one with no
  `percent`, proving the ADR-0016 no-bar-without-a-number rule), a `side_nav` with a footer, four
  `figure_card`s, a dense `table` with a mono column, and a `log_pane` wired to an SSE region — in
  both themes, from public macros alone.

Full local gate, `py/MirrorWall` (Python 3.14.4, `.venv`): `ruff format --check .`, `ruff check .`,
`mypy src tests`, `lint-imports` (2 contracts kept), `pytest --cov` → **373 passed, 3 deselected**
(2 markers + the readme-version check counted once), **coverage 98.02 %** (floor 95 %).

## 3. The four applications, proven against this tree

Per the kickoff's Gate A instruction ("run each from its own repository against an editable
MirrorWall; report the invocations") and the Demonstrate section's "`pytest` in each of the four
application repositories green against the new MirrorWall with no template change":

```bash
cd <app> && .venv/bin/pip install -e ../py/MirrorWall --no-deps
.venv/bin/python -m pytest -m "not live and not performance" -q
cd <app> && .venv/bin/pip install "mirrorwall==0.2.2" --no-deps   # restored after
```

| Application | Result | Notes |
|---|---|---|
| LoadCoach | **1100 passed, 5 skipped** | Already had an editable MirrorWall install from prior session work; ran as-is |
| FreeWeight | **2667 passed, 29 skipped** | Clean |
| IdeaPress | **3 failed** (`tests/unit/test_config_schema.py`), 1239 passed, 6 skipped | The three failures are WS3's own config-schema golden, no `mirrorwall` import anywhere in that file — unrelated to this row, left for WS3 |
| PromptCadence | **4 failed** (`tests/unit/test_egress_surfaces.py`), 1307 passed, 3 skipped | Same shape: Commissioner egress-surface tests, no `mirrorwall` import — unrelated |

Zero template-related failures across 5313 combined passing tests. All four repositories' pinned
`mirrorwall>=0.2.2,<0.3` restored afterward — this row does not widen any application's pin; that
is each application's own adoption row (WM2 and the per-application rows after it).

## 4. Decisions made closing gaps the kickoff prompt left open

* **`--mw-row-h` keeps its 0.2.2 value; dense is opt-in per table, not per page.** The design
  brief's token-delta table reads as if the *global default* moves to 32px with a new
  `--mw-row-h-comfortable` as the opt-out — that would break byte-identical rendering for every
  existing table the moment an application upgrades. Implemented instead: `--mw-row-h` unchanged,
  `--mw-row-h-comfortable` a same-valued alias a page can name explicitly, and
  `table[data-density="dense"]` (`tables.css`) the only thing that moves the value, scoped to the
  table that asks for it. This is the reading that satisfies both the brief's *intent* (a dense
  table exists) and spec §11 contract 7 (an upgrade never requires a page to change).
* **`status_dot`'s `status` parameter defaults to `"unknown"`**, not required — the vocabulary
  already defines "unknown" as its own fallback state, and a required parameter with no sensible
  default was the one macro the vocabulary-scan's generic-parameter test caught.
* **`side_nav`'s per-section pages are keyed `links`, not `items`** — a plain dict's `.items`
  resolves to the built-in method before Jinja's key-lookup fallback runs, so a template written
  against `section.items` would silently iterate `dict.items` the first time a real dict (rather
  than a lucky namespace object) was passed. Documented in the macro's own comment.
* **`static/vendor/` is exempted from the application-vocabulary scan.** htmx's own minified
  source contains the word "queue" (its internal event queue) — legitimate upstream naming, not a
  leak of this package's naming discipline. Every other vendoring rule (digest, licence) still
  applies to vendored files; only the vocabulary scan is scoped away from `vendor/`.
* **JetBrains Mono vendored as two static weights (400, 700)**, not a variable font — a data font
  needs no range of weights, and the two static `@font-face` rules match the pattern the fonts test
  already expects (a licensed file beside a `LICENSE`).
* **The "Demonstrate" shell skeleton is a test, not a `gallery.py` implementation.** Phase 3's
  component gallery is still an unimplemented stub (deferred, unrelated to this row); building it
  out was not asked for and would have been scope creep. The demonstration lives as
  `tests/snapshot/test_weightroom_shell_demo.py` instead — composed from public macros only,
  asserting the specific structural claims the brief's artboard makes.

## 5. What the interview/kickoff left for later, unchanged

* Removing the pre-htmx swap/SSE JS modules — ADR-0128 rule 7, ships at WM2 or later, not before
  every application has adopted htmx.
* The four applications' own adoption of the new tokens and components (density, status dots,
  meters, the log pane, the tab strip) — rows after this arc, per design brief §6.
* `gallery.py`'s Phase 3 implementation — still a stub, orthogonal to this row.

## 6. Verification a reviewer can repeat

```bash
cd py/MirrorWall && source .venv/bin/activate
ruff format --check . && ruff check . && mypy src tests && lint-imports
pytest --cov --cov-report=term-missing   # 373 passed, coverage 98.02%
diff docs/packages/mirrorwall/spec.md ../../WeightRoom/docs/packages/mirrorwall/spec.md
diff docs/packages/mirrorwall/development-plan.md ../../WeightRoom/docs/packages/mirrorwall/development-plan.md
```
