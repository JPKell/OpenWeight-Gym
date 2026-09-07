# K3 handoff — `project_review`'s prompt gets a budget

**Row:** K3 (Sonnet 5 · high). **Component:** `IdeaPress`, branch `main` (no worktree — J2's row was
the last one split into a worktree; K3 was not). Started from the prepared `ideapress 1.2.0`
(`dcb2a17`) plus K2's two commits, with two further commits (`1f2ad9d` "pytest 9",
`dccfb1c` "docs(readme)") landing mid-session from elsewhere (see §6). Read first:
`docs/history/J2_HANDOFF.md` (all of it, §3 D3 and §8 especially), ADR-0104,
`packages/cutctx/spec.md` §7 + §11, `apps/ideapress/workflows.md` §7, `src/ideapress/domain
/context_assembly.py`, `src/ideapress/services/project_review.py`, `src/ideapress/config.py`.

## 1. Gate results

Interpreter: `IdeaPress/.venv/bin/python` — Python 3.13.15.

```bash
cd /home/jpk/ai/suite/IdeaPress
.venv/bin/python -m ruff format --check .    # 185 files already formatted
.venv/bin/python -m ruff check .             # All checks passed!
.venv/bin/python -m mypy src tests           # Success: no issues found in 180 source files
.venv/bin/lint-imports                       # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                              # 1133 passed, 5 skipped, 30 deselected
.venv/bin/python -m pytest --cov=ideapress --cov-report=term-missing -q
                                              # Required test coverage of 85.0% reached: 88.60%
```

The two `pytest` invocations above were run with `IDEAPRESS_DATA_DIR` pointed at a scratch
directory rather than the default XDG location — see §6 for why: without that override, two test
files unrelated to this row's diff (`tests/security/test_sanitization_sweep.py`,
`tests/integration/test_backend_parity.py`) fail because they call `load_settings()` with no
override and hit the operator's real `~/.local/share/ideapress` database, which a concurrent
process migrated to a revision this checkout's migration history does not contain, mid-session.
Confirmed unrelated to this row's changes: those two files import nothing from
`domain.context_assembly`, `services.project_review` or the `workflow` settings section, and both
pass cleanly in isolation. No network, no GPU, no LoadCoach.

## 2. Commits

`IdeaPress` (branch `main`):

| Commit | What |
|---|---|
| `3c9ce91` | Gate A — golden-capture `render_units()`'s exact current output on a small fixture in `tests/unit/test_context_budget.py`, before any production code changed. |
| `9b965fd` | Gate B+C+D — `domain.context_assembly.assemble_review_context()` and `AssembledReview`; the new `workflow.project_review_context_budget_tokens` setting; `services/project_review.py` rewired onto it (`render_units()` deleted); the golden test updated to prove the new function reproduces the same golden byte for byte on a generous budget, plus new tests for drop order, the `context.compacted` report and the refusal; `docs/configuration.md` regenerated; `tests/unit/test_config_1_0_compatibility.py` taught about the new key (`ADDED_IN_K3`); `CHANGELOG.md`; a one-line decision comment at `review_loop.py`'s revise-round `assemble_context` call (§4, D5). |

`docs` (branch `main`):

| Commit | What |
|---|---|
| `493b0b0` | `apps/ideapress/workflows.md` §7 gains one paragraph naming `assemble_review_context()` as the sibling seam and stating the drop order and why. Mirrored byte for byte into `IdeaPress/docs/apps/ideapress/workflows.md` in commit `9b965fd` above; `cmp`-clean. |

No ADR filed — see §4, D6.

## 3. The untouchable set, and the drop order

**Nothing is pinned.** `project_review`'s documented input, per `workflows.md`'s stage table
(§2, row 15), is "All units" — full stop. There is no per-review unit specification, no
requirement list, no glossary or style constraints the way per-unit `assemble_context()` protects;
`stages.project_review.consistency.v1.json`'s template has exactly one variable, `units`. So
unlike per-unit assembly's `unit_specification`/`requirements`, there is nothing here that plays
the same role, and inventing one (see D1 below) is refused.

**Drop order: units are dropped from the *end* of reading order first.** The earliest unit in
`services.units.committed_units()`'s reading order (ordinal ascending) is the most valuable and is
kept longest; the latest unit is the least valuable and goes first. Reasoning: a cross-unit review
is checking later material for drift *away from* something, and the earliest units are where the
project's terms, facts and structure are first established. Keeping that end intact for as long as
the budget allows gives the reviewer an actual anchor to compare against; dropping from the front
instead would leave it comparing later units to each other with nothing establishing what
"consistent" means in this project. Implemented by building the CutCtx transcript in *reversed*
reading order (§7's `DropOldestPolicy` drops the transcript's oldest turns first, so the
reading-order tail is built first/oldest and the head last/newest) — the same construction J2's
`assemble_context()` uses for `REDUCTION_ORDER`, adapted to a single flat category instead of three
ranked ones.

## 4. The decisions, and the losing options

**D1 — the row's suggested pins don't apply; the untouchable set is empty.** The row text reads
"the project brief and requirements are the obvious pins", by analogy with per-unit assembly's
`unit_specification`/`requirements`. Checked against the actual code and found not to hold: (a)
`project_review_body` never reads `Project.brief_text` or any project-level requirement list —
confirmed by grep, nothing in the function touches either; (b) the prompt template carries no slot
for them; (c) workflows §2's own stage table names the documented input as "All units", nothing
more. The **losing option** — add the brief and a compiled requirements summary as new pinned
sections, giving the reviewer grounding it never had — was rejected because it directly conflicts
with the row's own explicit, unconditional requirement: "the stage must keep producing the same
prompt byte-for-byte when nothing is dropped." Any newly-added pinned content changes the prompt
even at a generous budget, for every budget, which is exactly what that sentence forbids. Filed as
what the row got wrong (§8) rather than argued past — the parenthetical is a suggestion from
someone who evidently read `docs/history/J2_HANDOFF.md` §8 carefully (the git-blame-precise
citation) but extrapolated from per-unit assembly's shape without checking stage 15's own
documented input.

**D2 — drop order, see §3.** The **losing option** — drop from the front of reading order first —
was considered and rejected: it discards the foundational material (the terms and facts the
project establishes first) that a drift check needs as its reference, leaving a review of only the
later, least-anchored material.

**D3 — the refusal, because CutCtx's own `BudgetUnsatisfiable` never fires here.** With `pinned`
empty on every turn and `protected_recent_turns=0` (ADR-0104's rule), the untouchable set is
`0` tokens. Verified directly against the installed `cutctx 0.1.0`: `CompactionBudget(max_tokens=0,
protected_recent_turns=0)` against three 16-token turns produces `kept: []`, no exception —
`DropOldestPolicy` drops **everything** rather than refuse, because from CutCtx's own point of view
an empty view that fits the budget is a valid plan (spec §13: `BudgetUnsatisfiable` fires only when
a *pinned* turn overflows). A negative `max_tokens` does not reach that path either — `cutctx`'s
own `CompactionBudget.__post_init__` raises `baseaicore.errors.ValidationError` at construction,
before `DropOldestPolicy.decide()` ever runs (existing behaviour of `assemble_context()` too, left
as found, matching J2's precedent of not fixing what the row does not name).

Since `assemble_review_context` has no undroppable content, letting CutCtx's own decision stand
would mean a too-small budget silently reviews an emptied document — the exact
silent-degradation-with-extra-steps this codebase's philosophy (ADR-0016, workflows §7 "never
silently truncating") refuses everywhere else. The **losing option** — let `DropOldestPolicy`'s
own empty-view answer stand, since it is not technically an error CutCtx itself raises — was
rejected on that basis. Implemented instead: a manual post-`decide()` check (`kept_keys` empty
while `ordered_keys` was not) that raises `ContextLimitExceeded` carrying `required_tokens` (the
single cheapest unit's estimated size) and `budget_tokens`. This is the caller-specific untouchable
floor ADR-0104's "Revisit when" anticipated for a future adopter whose untouchable set is not
expressible as `pinned` — except here it is the *reachability* of the refusal, not the expression
of the pin, that CutCtx's own contract cannot reach for an all-droppable transcript. Tested directly
(`test_review_refuses_when_even_the_cheapest_unit_does_not_fit`, budget=5 against three 16-token
units) rather than left dead — matching J2's own precedent of proving the mechanism with an
artificially tiny budget below what production config would ever allow (`ge=256` on the new field).

**D4 — the settings key.** `workflow.project_review_context_budget_tokens`, default `24_000`,
`ge=256` — same section and shape as `workflow.context_budget_tokens` (J1/J2 precedent), named
with the unit in the name per the row's instruction. Larger default than the per-unit key's `8_000`
because this budget holds potentially many units at once rather than one unit's neighbourhood.

**D5 — the revise loop's missing `neighbouring_units`/`research_notes`: the shape is intentional.**
Checked `src/ideapress/prompts/stages/revise.improve.v1.json`'s own system prompt: "You revise a
section against specific findings written by a reviewer. Address the findings and change as little
else as possible: a rewrite that fixes the fault and loses the writing is not a revision." That is
a deliberately narrow brief, and it is the opposite of what broader cross-unit context invites — a
model shown neighbouring units and research notes has more material to let leak into "why not also
fix this while I'm here." The **losing option** — widen `run_review_loop`'s signature to accept
`neighbours`/`ordinals` (both already in scope at `unit_loop.py`'s `run_unit`, where
`run_review_loop` is called, per its own `neighbours`/`ordinals` parameters) and thread them
through into the revise call, with a test proving the `context.compacted` branch fires — was
considered and rejected: it contradicts the revise prompt's own narrow-fix framing, and the row's
own "do not widen beyond this" instruction reads most naturally as bounding exactly this kind of
scope creep. Recorded as a one-line comment at the call site
(`src/ideapress/services/review_loop.py:445`) rather than an ADR, since it is a narrow,
single-call-site decision, not a seam decision the way ADR-0104's were.

**D6 — no new ADR.** ADR-0104's "Revisit when" names a future adopter whose untouchable set is
"not expressible as `pinned`" as the trigger for a new record. This row's untouchable set *is*
expressible as `pinned` — it is simply empty, which is a valid instance of the same contract, not a
gap in it. What this row adds beyond ADR-0104 (the manual post-decide refusal, D3) is a
consequence of an *empty* pinned set, not a different way of expressing one, so it is recorded here
rather than in a new ADR.

## 5. Parity evidence

`REVIEW_GOLDEN` in `tests/unit/test_context_budget.py`, captured against `render_units()` before any
production code changed (`3c9ce91`):

```text
### U-01 — Opening
First section text about the introduction.

### U-02 — Middle
Second section text about the middle content.

### U-03 — Closing
Third section text about the closing remarks.
```

`test_a_generous_review_budget_reproduces_the_captured_golden` (added in `9b965fd`, alongside the
production change) asserts `assemble_review_context(units=REVIEW_UNITS, titles=REVIEW_TITLES,
budget_tokens=100_000).render() == REVIEW_GOLDEN` — unedited from the pre-change capture — with
`dropped == ()` and `report is None`. `test_review_units_are_dropped_latest_in_reading_order_first`
proves the drop order at two budgets (32 tokens drops `U-03` only; 16 tokens drops `U-03` then
`U-02`, keeping only `U-01`). `test_review_report_only_when_something_is_dropped` mirrors J2's D4
test shape. `test_an_empty_project_review_assembles_to_nothing` covers the zero-units edge case
(not a budget failure — there is simply nothing to assemble; `project_review_body`'s own
precondition already refuses before this function would ever see fewer than two units in
production).

## 6. Working-tree conditions found, not caused by this row

* **Concurrent commits landed on `main` mid-session.** `1f2ad9d` ("chore(deps): pytest 9") at
  11:38:33 and `dccfb1c` ("docs(readme): ...") at 11:54:34, both authored as Jordan Kell, appear
  between this row's two `IdeaPress` commits in `git log`. Both are fully committed, ordinary,
  unrelated to this row's diff (dependency bump, README wording) and merged into this row's history
  without conflict — noted for the record, not a problem this row needed to resolve.
* **An uncommitted `.github/workflows/ci.yml` diff (adding a `diff-cover` job) was present in the
  working tree throughout this session**, before this row's first edit and still present at the
  end. Not created by this row, not staged, not committed (verified: every `git add` in this row
  named files explicitly, per house rule; `.github/workflows/ci.yml` was never one of them).
  Left exactly as found for whoever is mid-edit on it.
* **The operator's real `~/.local/share/ideapress/ideapress.sqlite3` was migrated to revision
  `0009` by something else mid-session** (a fresh `pre-migration-0009-*.sqlite3` backup appeared at
  11:45, mid-session — most likely K4's concurrent work in `IdeaPress-k4`, which this row's
  kickoff named as touching the attempts migration chain, though `IDEAPRESS_DATA_DIR` is not
  worktree-scoped by default so this is inference, not confirmed). This broke
  `tests/security/test_sanitization_sweep.py` and `tests/integration/test_backend_parity.py` for
  anyone running the plain default-location test suite from this point on — both call
  `load_settings()` with no override and so read the real, shared, migrated-ahead database. §1's
  gate re-ran both files with `IDEAPRESS_DATA_DIR` pointed at a scratch directory to get a clean
  read; all 1133 tests pass either way except those two files' 17 cases, and those 17 pass cleanly
  in isolation, confirming the failure is environmental and not this row's diff. Filed as a
  follow-up in §8 — these two files' lack of data-dir isolation is a latent hazard independent of
  K3, worth fixing before the next time two rows run against this repo at once.
* This row did not run `git status --short` before its first edit (an oversight against the
  standing instruction) — the account above is reconstructed from `git log` timestamps and the
  working tree as found partway through, not a clean before/after comparison. `git status --short`
  at the end of this row (both repos) is in §1 and above: only the files this row names are
  staged; `.github/workflows/ci.yml` remains modified and unstaged, exactly as found.

## 7. Exit conditions

1. **`project_review`'s context routed through the same CutCtx chain, with its own untouchable
   set, a settings key, an honest refusal and the `context.compacted` report.** Yes — §3, §4 D3/D4,
   `assemble_review_context()`.
2. **Byte-for-byte parity on a generous budget, golden-tested before the change.** Yes — §5;
   golden captured in `3c9ce91`, reproduced unedited in `9b965fd`.
3. **The revise loop's missing `neighbouring_units`/`research_notes` decided and recorded.** Yes —
   §4 D5: intentional, matches `stages.revise.improve`'s own narrow-fix framing; one-line comment
   at the call site, no widening.
4. **Default gate green, coverage ≥ 85%, no network/GPU/LoadCoach.** Yes — 88.60% (§1), modulo the
   environmental note in §6 (both affected files pass in isolation).
5. **`workflows.md` §7 current, mirrored, `cmp`-clean.** Yes — §2, `cmp`-clean confirmed after both
   commits landed.
6. **Version untouched, `git status --short` clean of anything this row should have staged.** Yes
   for the version (`__about__.py` untouched, `CHANGELOG.md` still under `[Unreleased]`). For
   `git status --short`: clean of this row's own work; the pre-existing `.github/workflows/ci.yml`
   diff (§6) is not this row's to clean up.

## 8. Found, belongs to another row

* **`project_review_body`, and `unit_loop.run_unit`/`review_loop.run_review_loop` before it, have
  never had direct test coverage.** Confirmed with a targeted run:
  `pytest --cov=ideapress.services.project_review` reports **0.00%** — the module is not imported
  by any test in the suite, live or otherwise (no test imports `project_review_body`, and
  `services/stage_registry.py`'s own dispatch to it, lines 50-52, is itself in that file's uncovered
  lines). This predates this row entirely — `render_units()` had the same zero coverage before
  today — and this row's new domain-level tests (`assemble_review_context`) do not close it: they
  prove the budgeting *logic*, not the stage `body()` closure's wiring (the settings lookup, the
  conditional `context.compacted` emit, feeding `context.render()` into `render(...)`). Building an
  integration harness for a currently entirely-untested stage body is a real, separate undertaking
  (a `Runtime`/`StageTask`/`FakeBackend` fixture nothing in this repo currently provides for these
  three functions) and was left out of this row as scope creep beyond "give `render_units()` a
  budget" — flagged here rather than silently expanded into.
* **`tests/security/test_sanitization_sweep.py` and `tests/integration/test_backend_parity.py`
  call `load_settings()` with no `IDEAPRESS_DATA_DIR` override**, reading the operator's real
  `~/.local/share/ideapress` database rather than an isolated fixture. Harmless when only one
  IdeaPress session runs at a time; broke visibly the moment a concurrent session (almost certainly
  K4, per this row's own kickoff) migrated that real database mid-session (§6). Worth pinning a
  scratch data dir in both fixtures before the next time two rows touch this repo concurrently.
* **CutCtx's `BudgetUnsatisfiable` cannot detect "kept nothing" for a caller with an entirely
  droppable, unpinned transcript** (D3) — this row's manual post-`decide()` check
  (`kept_keys` empty) is a caller-side workaround, not something CutCtx itself offers. Any future
  CutCtx adopter shaped like `project_review` (no undroppable content at all) will reinvent the
  same check. Worth a line in CutCtx's own backlog — not built here, since it is a package-level
  design question outside IdeaPress's remit.
