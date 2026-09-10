# J2 handoff — IdeaPress's context assembly becomes a CutCtx policy chain

**Row:** J2 (Sonnet 5 · high). **Component:** `IdeaPress-j2` worktree, branch `j2-cutctx`, checked
out from `main` at `1ef7663`. **Kickoff:** `docs/history/prompts/j2-ideapress-cutctx.prompt.md`. Run under
the coordinator overrides for the parallel J1/J2 split (worktree isolation, Gate E skipped, ADR
number reassigned to 0104, `roadmap/outstanding-work.md` left to the coordinator).

## 1. Gate results

Interpreter: `IdeaPress-j2/.venv/bin/python` — Python 3.13.15.

```bash
cd /home/jpk/ai/suite/IdeaPress-j2
.venv/bin/python -m ruff format --check .        # 175 files already formatted
.venv/bin/python -m ruff check .                 # All checks passed!
.venv/bin/python -m mypy src tests               # Success: no issues found in 170 source files
.venv/bin/lint-imports                           # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -q                    # 1071 passed, 5 skipped, 30 deselected
.venv/bin/python -m pytest -q --cov=ideapress --cov-report=term-missing
                                                  # Required test coverage of 85.0% reached: 88.15%
```

All green, no network, no GPU, no LoadCoach installed (`FakeBackend`/in-process only throughout).
`git status --short` clean in both `IdeaPress-j2` and `docs` at the end of the session.

## 2. The gates as commits

`IdeaPress-j2` (branch `j2-cutctx`):

| Commit | Gate | What |
|---|---|---|
| `0776f1e` | A | Six golden fixtures (`tests/unit/test_context_assembly_golden.py`) captured against the **unmodified** `assemble_context`, plus a `pyproject.toml` per-file `E501` exemption for the fixture's literal `render()` bytes. |
| `5771b28` | B+C+D (domain/services) | Rewrite of `domain/context_assembly.py` onto `cutctx.DropOldestPolicy`; `pyproject.toml` gains `cutctx>=0.1,<0.2`; `services/unit_loop.py` and `services/review_loop.py` emit `context.compacted`; two new report-shape tests and an estimator-agreement test in `test_context_budget.py`; `CHANGELOG.md` under `[Unreleased]`. |
| `40904c4` | D (docs, component copy) | `workflows.md` §7 gains one sentence naming CutCtx; mirrored from the workspace copy; fixes the CHANGELOG's handoff reference to the house's backtick-path convention. |

`docs` (branch `main`, on top of concurrent J1/docs-review commits — `c96573c`, `ac03995`):

| Commit | What |
|---|---|
| `6e7268a` | `adr/0104-an-adopted-reductions-seam-and-error-vocabulary-survive-it.md`, its `adr/README.md` index row and narrative paragraph, and `apps/ideapress/workflows.md` §7 (source of the mirrored copy above). |

I deliberately landed Gates B, C and D's domain/service code as **one** commit rather than three.
The kickoff separates "the mapping" (B) from "the deletion" (C) from "the report" (D), but B and C
are one function body — there is no intermediate state where the new turn-construction code exists
*and* the old strict-fill loop still decides anything, without carrying two competing decision
paths in one function at once, which is the over-engineering this row's own "parity over elegance"
constraint argues against. D4's report field is additive to the same rewrite and shares its
tests, so it rode along. Gate A stands alone because it is the one commit whose entire point is to
predate the rewrite.

## 3. The six decisions

**D1 — the seam that survives.** Took the recommendation: `assemble_context()`'s signature and
`AssembledContext`'s `sections`/`dropped`/`budget_tokens`/`render()`/`section()` are byte-for-byte
unchanged (a `report` field is *added*, not a change to an existing one). The losing option
(exposing `cutctx` types to `services/`) would have made `unit_loop.py` and `review_loop.py` a
second consumer of the mapping, needed no edit under D1, and did receive none — the diff to those
two files is only the four-line `context.report` emission block, D4's addition.

**D2 — what "the in-app reduction code is deleted" means.** Took the recommendation with one
qualification the kickoff's own wording invites a misreading of. `_rank_of` was **not** deleted —
it changed role. Before: it fed the strict-fill loop's *decision* (`_rank_of(name), rank`,
descending, "everything after the first miss is dropped"). After: it is a pure formatting key,
used twice — once to build the turn order `DropOldestPolicy` reads as "oldest first" (least
valuable, built as the oldest turn), and once to re-sort whatever CutCtx kept back into workflows
§7's presentation order. The *decision* — which sections survive — is made entirely by
`DropOldestPolicy.decide()`; nothing in `context_assembly.py` re-derives it. ADR-0104 records this
distinction explicitly because "the decision code — `_rank_of` ... — goes" (kickoff, D2) reads as
"the function goes", which is not what happened and would not have been possible without either
losing byte-parity or re-implementing CutCtx's fill logic a second time to compute presentation
order. The losing option — literally deleting `_rank_of` — would have left no way to reconstruct
`AssembledContext.sections` in the documented order or `AssembledContext.dropped` in the documented
order, since CutCtx's plan only says *which* turns survive, never in what order a caller should
display them. `estimate_tokens` became a thin alias over `cutctx.CharRatioEstimator` (not deleted:
it is `__all__` and is the default value of `assemble_context`'s `estimator` parameter, which must
exist as a real callable at import time). `REDUCTION_ORDER` is untouched.

**D3 — `project_review` is out of scope.** Took the recommendation. Confirmed ground truth 2
still holds: `services/project_review.py:37`'s `render_units()` concatenates every committed unit
unbudgeted at `:77`; there is no reduction there to convert. Filed as a follow-up below (§8).

**D4 — the `CompactionReport` is emitted.** Took the recommendation, with the "if the sink is not
reachable from `domain/`" branch: `assemble_context` stays pure and returns the report on
`AssembledContext.report` (`None` when nothing was dropped, set exactly once per assembly that
dropped something), and the two callers emit it as `"context.compacted"` on the existing
`emit(event_type, message, data)` closure already threaded through both loops. Tested at the
domain layer (`test_no_report_when_nothing_is_dropped`,
`test_a_dropped_assembly_carries_the_context_compacted_report`); **not** tested end-to-end through
a running stage (see §8 — the revise-loop call site can in practice never produce a report, which
is itself a finding).

**D5 — the version.** Left the version alone per the coordinator's Gate-E override: `CHANGELOG.md`
stays under `## [Unreleased]`, `__about__.py` untouched at `1.1.0`. The coordinator cuts `1.2.0`
(or, if J1 lands first, `1.3.0`) after merging both branches.

**D6 — the ADR.** Wrote one: `ADR-0104`. Checked `packages/cutctx/spec.md` §11 first, per the
kickoff's instruction to skip it if everything were already stated there — it is not: §11's five
contracts describe CutCtx's own guarantees (view-not-deletion, the untouchable set, tool-exchange
integrity, determinism, honest estimates), none of which say what an *adopting application* must do
at the seam. The three things this row had to decide that neither document settled — cutctx types
never reach a caller's callers, `protected_recent_turns` fixed at `0` with `pinned` carrying the
whole untouchable set, and `BudgetUnsatisfiable` translated rather than let through — are the ADR's
three decision points.

## 4. The parity evidence

Six golden fixtures, captured pre-CutCtx at `0776f1e` and asserted unedited after the rewrite at
`5771b28`. All six pass against the new implementation without a single golden value changed:

| Fixture | Budget | `dropped` |
|---|---|---|
| `generous` | 100 000 | `()` |
| `drops_research_notes_only` | 284 | `('research_notes', 'research_notes')` |
| `drops_distant_and_research` | 224 | `('research_notes', 'research_notes', 'distant_units')` |
| `drops_one_adjacent_and_more` | 184 | `('research_notes', 'research_notes', 'distant_units', 'adjacent_units')` |
| `strict_not_greedy_large_then_small` | 184 | `('research_notes', 'research_notes')` |
| `overflow_raises` | 50 | *raises* `ContextLimitExceeded`, `required_tokens=84`, `budget_tokens=50` |

**The strict-versus-greedy case, in detail.** Two research notes: one referenced (rank 999, the
unit's own title, 198 estimated tokens), one unreferenced (rank 0, 23 estimated tokens). Mandatory
sections cost 84 tokens; budget 184 leaves 100 for the budgeted pair.

* **Old algorithm** (fill from most valuable): tries the referenced note first — 198 > 100, a
  miss — and marks everything after it dropped regardless of size. The unreferenced note (23
  tokens, which alone fits in 100) is dropped anyway. Kept: neither. Dropped: both.
* **A greedy/best-fit alternative** (not shipped anywhere in this row, described only to name the
  risk) would have skipped the 198-token miss and packed the 23-token note into the leftover
  space — keeping one note the strict algorithm drops.
* **`DropOldestPolicy`**, walking oldest-first (built as: unreferenced note oldest, referenced note
  next-oldest, ties resolved to match the original stable sort exactly — see `context_assembly.py`'s
  comment on `kept_in_fill_order`), removes the unreferenced note first (running total still over
  budget: 198 tokens of budgeted content remain against 100), then removes the referenced note too
  (now fits). It never "tries" the unreferenced note in isolation — it only ever asks "does the
  running total fit yet", which structurally cannot produce a best-fit answer. Result: both
  dropped, byte-identical to the old algorithm and to the golden.

This is not a coincidence of the specific numbers chosen; it follows from `DropOldestPolicy`'s
mechanics (drop from the oldest end, one exchange at a time, stop only when the cumulative estimate
fits) being structurally incapable of skipping a too-large item to reach a smaller one further
along — the same non-greedy property the old loop's `# **Strictly ordered, not greedy.**` comment
(deleted, along with the loop it documented) asserted about itself. The reasoning is recorded in
`context_assembly.py`'s new comments so a future reader does not have to re-derive it.

## 5. Exit conditions

1. **`project_review` decided (D3), follow-up filed.** Out of scope; filed in §8.
2. **The stage's context assembly runs through `cutctx`; the decision code is gone.** Yes —
   `DropOldestPolicy.decide()` makes every keep/drop call; `context_assembly.py` no longer sorts
   sections to decide anything, only to position and re-present (D2).
3. **Golden parity: byte-identical `render()`, identical `dropped`, identical error details, on
   every fixture, goldens committed before the change.** Yes — `0776f1e` before, `5771b28` after,
   all six fixtures pass unedited (§4).
4. **Default gate green, coverage ≥ 85%, no network/GPU/LoadCoach.** Yes — 88.15% (§1).
5. **`workflows.md` §7 current, mirrored, `cmp`-clean; roadmap version corrected.** §7 done and
   `cmp`-clean (§2). Roadmap version correction is the coordinator's, per override 4 — not touched
   here.
6. **`1.2.0` prepared, committed, untagged, unpushed; `git status --short` clean everywhere.**
   Version *not* bumped, per the coordinator's Gate-E override (this row's exit condition 6 is
   superseded by that override — the coordinator cuts the release after merging J1 and J2).
   `git status --short` is clean in both `IdeaPress-j2` and `docs`.

## 6. Things the kickoff said that turned out not to be true

* **D2's "what goes is the decision code — `_rank_of` ..." reads as stronger than what actually
  happened.** `_rank_of` survives, repurposed as a presentation-ordering key rather than a decision
  key (§3, D2). This is not a disagreement with the kickoff's intent — the *decision* is genuinely
  gone — but a reader taking "the decision code — `_rank_of`" as "the function `_rank_of` is
  deleted" would be wrong, and I could not find a way to reconstruct byte-identical `sections` and
  `dropped` ordering without a same-shaped helper, so I kept the name and recorded the reinterpretation in ADR-0104 rather than inventing a new name to dodge the appearance of disagreeing.
* Nothing else in the ground truth, the reading list or the shape-mismatch table needed correcting;
  ground truths 1–8 all held exactly as stated when checked against the actual `1ef7663` tree and
  the installed `cutctx 0.1.0`.

## 7. What the operator still has to do

The coordinator merges `j2-cutctx` into `main` (after `J1` lands, per the coordinator's plan) and
cuts `ideapress 1.2.0` (or `1.3.0` if J1 landed first) — version bump, `CHANGELOG.md` heading
change, tag and publish are all outside this row's remit (coordinator overrides 2 and 7).

## 8. Found, belongs to another row

* **`project_review`'s unbudgeted whole-document prompt** (ground truth 2, confirmed unchanged):
  `services/project_review.py:37`'s `render_units()` concatenates every committed unit,
  unbudgeted, into the prompt at `:77`. A project with enough committed units will exceed the
  served context and the stage will fail at the provider rather than with IdeaPress's own numbers.
  Budgeting it through CutCtx is real work — new behaviour, a new failure mode, possibly a new
  settings key — and is not a golden-parity refactor; it needs its own row.
* **The dead `research_notes` path** (ground truth 3, confirmed unchanged): `assemble_context`
  still accepts `research_notes`, and neither `unit_loop.py`'s draft/repair call nor
  `review_loop.py`'s revise call passes it. `REDUCTION_ORDER[0]` is exercised only by
  `tests/unit/test_context_budget.py` and the new golden fixtures, never by a running stage. Left
  as found, per the kickoff's explicit instruction not to "fix" this here.
* **The revise-loop call site can never, in practice, produce a `context.compacted` report.**
  `review_loop.py`'s `assemble_context` call (the revision path) passes only `unit`, `requirements`,
  `budget_tokens` and `previous_findings` — no `neighbouring_units`, no `research_notes` — so it
  builds *zero* budgeted sections and can never have anything to drop. The `if context.report is
  not None: emit(...)` block added there for D4 is therefore currently unreachable in production,
  though it is directly exercised by the domain-level report tests (which call `assemble_context`
  with neighbours/notes regardless of which caller would realistically supply them). This is not a
  bug introduced by this row — the revise call never passed those kwargs before J2 either — but it
  is worth a future row noticing before relying on a revision-time compaction event actually firing.
* **What CutCtx would need to serve `project_review` as a third consumer**: an untouchable set that
  is not a static property of a turn (`pinned`) but depends on the workflow's own configuration —
  ADR-0104's "Revisit when" names this as the trigger for CutCtx's next row, should `project_review`
  ever need a droppable-under-one-config, undroppable-under-another section.
