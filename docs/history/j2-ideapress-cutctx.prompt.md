# Kickoff — J2: IdeaPress's context assembly becomes a CutCtx policy chain

**Row:** J2 (Sonnet 5 · high) of [`docs/roadmap/outstanding-work.md`](../roadmap/outstanding-work.md)
§1 — the third of M13's adoption phases (IP-A3), scheduled as J3 before the 2026-09-07 merge.
**Component:** `/home/jpk/ai/suite/IdeaPress` — `src/ideapress/domain/context_assembly.py`,
its two callers, and `docs/`.
**Adopts:** `cutctx 0.1.0`, published on PyPI (2026-09-03, `4ade547`).
**Ships:** an IdeaPress minor. **Not `1.1.0` — see the first ground-truth correction below.**

**The row's whole claim is parity.** It deletes working, tested, shipped reduction code and puts a
shared package underneath the same public seam. Nothing a user sees may move: the same sections, in
the same order, dropped in the same order, with the same error carrying the same two numbers. The
new capability this adoption buys is *one shared, golden-tested reduction* — not a better one.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.**
  `/home/jpk/ai/suite/IdeaPress`, its own `.venv/bin/python`. `pip install -e ".[dev]"` if
  anything is missing.
* **House method:** docstring-first, `from __future__ import annotations`, units in every numeric
  name, keyword-only for anything optional or boolean, injected estimators and clocks, line length
  100, `mypy --strict`, no `# type: ignore` without a trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, plus `pytest --cov` at or above the **85 %**
  floor (application). **Name the interpreter and the exact invocation in the handoff** (M5C-13).
* **Documentation is mirrored.** Edit the workspace copy under `/home/jpk/ai/suite/docs/` first,
  then copy byte-identically into `IdeaPress/docs/apps/ideapress/`, and verify with `cmp`.
* **Do not push, do not tag, do not publish.** Standing instruction of 2026-09-04.
* **Run `git status --short` at the start and at the end** in every repository you touch.

---

## Ground truth, already checked on 2026-09-07 — do not spend the session rediscovering it

1. **IdeaPress is already at `1.1.0`, tagged and published.** `30ba52f`
   (`chore(release): ideapress 1.1.0`, 2026-09-05) shipped the H3 adapter-pin work; `v1.1.0` is a
   tag and PyPI serves `ideapress 1.1.0`. The roadmap row's "IP-A3 CutCtx → **1.1.0**" is stale
   prose from before H3. **This row cuts `1.2.0`**, and it corrects the J1 and J2 rows in
   `outstanding-work.md` to say so. `main` is one commit past the release (`1ef7663`, a live test),
   working tree clean.
2. **`project_review` performs no reduction at all.** [`services/project_review.py:37`](../../IdeaPress/src/ideapress/services/project_review.py)
   `render_units()` concatenates *every* committed unit, unbudgeted, straight into the prompt at
   `:77`. The roadmap's "`project_review` context assembly as a policy chain" therefore describes
   code that does not exist. The reduction the row deletes is `domain/context_assembly.py`
   (348 lines), and its only callers are `services/unit_loop.py:171` (draft/repair) and
   `services/review_loop.py:445` (revision). This is decision **D3**.
3. **The first tier of the documented reduction order is dead in production.** `assemble_context`
   accepts `research_notes`, and **neither caller passes it** — so `REDUCTION_ORDER[0]` is
   exercised by `tests/unit/test_context_budget.py` and by nothing else. Do not "fix" this here;
   record it.
4. **No pin moves.** `cutctx 0.1.0` requires `baseaicore>=0.4.1,<0.5`, which is already
   IdeaPress's floor. The adoption adds one line to `dependencies` and nothing else;
   `.importlinter` needs no new contract (`cutctx` is a layer-3 package, and `ideapress.domain`
   may import it — the domain-purity contract forbids frameworks, not suite packages). IdeaPress
   has **no `ci.lock`**; do not invent one.
5. **The estimators already agree.** IdeaPress's `estimate_tokens` is `-(-len(text) // 4)`;
   `cutctx.CharRatioEstimator(4.0)` is `math.ceil(len(text) / 4.0)` with `0` for empty text. For
   integer lengths these are the same function. Parity does not depend on changing either — but
   assert it, because the whole golden claim rests on it.
6. **`cutctx 0.1.0`'s public surface** is `Transcript`, `TranscriptTurn`, `CompactionBudget`,
   `CompactionPolicy`, `PolicyChain`, `ObservationMaskingPolicy`, `SummarizingPolicy`,
   `DropOldestPolicy`, `default_chain`, `CompactionPlan`, `CompactionExecutor`,
   `CompactedTranscript`, `CompactionReport`, `CharRatioEstimator`, and the four errors.
7. **Next free ADR number is `0101`** (`0100` is PromptCadence's runtime settings).
8. **J1 has not run.** No `docs/history/J1_HANDOFF.md` exists. §3's "J1 before J2" is a
   *version-numbering* edge, not a code edge — the two rows share no file. See D5.

## Reading list

1. [`roadmap/promptcadence-roadmap.md`](../roadmap/promptcadence-roadmap.md) §6.3 — the exit
   condition in its own words.
2. [`packages/cutctx/spec.md`](../packages/cutctx/spec.md) §7 (the API), **§11 contracts 1–5**
   (view-not-deletion, untouchable set, determinism, honest estimates) and §13 (the error table).
3. `IdeaPress/src/ideapress/domain/context_assembly.py` — all 348 lines, including the two long
   comments at `:239` and `:245` that state the *strict, non-greedy* rule. That rule is the parity
   risk.
4. `IdeaPress/tests/unit/test_context_budget.py` (274 lines) — the behaviour that must survive,
   test by test.
5. [`apps/ideapress/workflows.md`](../apps/ideapress/workflows.md) **§7** — the document the
   reduction order is read against, and the one this row edits.

## The shape mismatch, which is the actual work

CutCtx compacts a **transcript of turns**; IdeaPress assembles **labelled sections with a
droppability and a rank**. The adoption is a mapping, and every parity risk lives in it:

| IdeaPress | CutCtx |
|---|---|
| `droppability="always"` (unit spec, requirements, style, previous findings) | `TranscriptTurn.pinned=True` |
| `ContextSection` (`name`, `heading`, `body`, `rank`) | `TranscriptTurn` with `content=section.render()`, `metadata` carrying `name`/`heading` |
| Reduction order + `rank`, most valuable **last** to be dropped | turn **order**: least valuable first, so "oldest" means "cheapest" |
| `budget_tokens` | `CompactionBudget(max_tokens=…, protected_recent_turns=0)` |
| strict, non-greedy fill | `DropOldestPolicy` |
| `ContextLimitExceeded(required_tokens, budget_tokens, …)` | `BudgetUnsatisfiable` |
| `AssembledContext.dropped` | `CompactionPlan.actions` where `action is Action.DROP` |

Two things to check rather than assume:

* **`protected_recent_turns` defaults to `4`.** Left at its default it pins the last four sections
  — the *most* valuable ones under this mapping, which sounds harmless and is not: it changes the
  `BudgetUnsatisfiable` threshold. Set it to `0` and let `pinned` carry the whole untouchable set.
* **`DropOldestPolicy` stops as soon as the budget fits.** IdeaPress stops filling at the first
  section that does not fit and drops everything less valuable after it. Argue in the handoff
  whether these coincide (they appear to: both leave the maximal most-valuable suffix whose
  cumulative size fits) and **prove it with a golden that contains a large section followed by a
  small one** — that is the case where a greedy fill would differ.

## The decisions this row makes

### D1 — the seam that survives

**Recommendation:** keep `assemble_context()` and `AssembledContext` exactly as they are —
signature, return type, `render()`, `section()`, `dropped` — and replace only the body. Both
callers, the prompt rendering and most of the test file then need no edit, and the golden claim
becomes trivially checkable. The losing option is exposing `cutctx` types to `services/`, which
buys nothing and edits four files instead of one.

### D2 — what "the in-app reduction code is deleted" means, exactly

**Recommendation:** what goes is the *decision* code — `_rank_of`, the strict-fill loop, the
sort — replaced by turn construction plus `DropOldestPolicy`. What stays is the *rendering* code
(`_render_unit`, `_render_requirements`, `_render_style`, `ContextSection.render`), which is
IdeaPress's prompt shape and no business of a shared package. `estimate_tokens` becomes a thin
alias over `CharRatioEstimator` or is deleted in favour of it — say which and why; it is public
(`__all__`) and imported by tests. **`REDUCTION_ORDER` stays**: it is the documented order and now
also the turn-ordering key.

### D3 — whether `project_review` is in scope

Ground truth 2 says there is nothing there to convert. Three options, pick one and argue it:

* **Recommendation: out of scope, and say so in the handoff and in the row.** J2 converts the
  assembly that exists. An unbudgeted whole-document prompt is a *different* change — new
  behaviour, a new failure mode for large projects, a settings key — and it is not a
  golden-parity refactor.
* Budget it here through the same chain (honest, but it doubles the row and cannot be
  golden-tested against a prior behaviour, because there is no prior behaviour).
* Budget it in a follow-up row you file. **If you pick the recommendation, file this**: it is a
  real ceiling — a project with enough committed units will exceed the served context and the
  stage will fail at the provider rather than with IdeaPress's numbers.

### D4 — whether the `CompactionReport` is emitted

CutCtx §11.7 says the report is exactly the body of the suite's `context.compacted` event.
IdeaPress emits nothing today when it drops a section. **Recommendation: emit it**, once per
assembly that dropped anything, on the existing event sink — it is the visible half of the
adoption and it costs a few lines. If the sink is not reachable from `domain/` without breaking
layering (it is not — `assemble_context` is pure), return the report on `AssembledContext` and let
the two callers emit. Do not push an event out of `domain/`.

### D5 — the version, given J1 has not run

`1.2.0` either way. **Recommendation: cut it here and note in the handoff that if J1 lands after
this row it cuts `1.3.0`**, and that M13's exit ("IdeaPress 1.1" in the roadmap's prose) is now
satisfied by a 1.x line rather than by that exact number — a documentation correction, not a
scheduling problem. Do not hold the release waiting for J1; §3 already calls the edge soft.

### D6 — the ADR

**Recommendation: one ADR, `0101`**, on what the suite's applications owe a shared reduction: that
a policy chain replaces in-app packing, that the untouchable set is expressed as pins rather than
as a policy exception, and that `BudgetUnsatisfiable` is translated at the application boundary
into the application's own typed error rather than leaking. Skip it only if every one of those is
already stated in `packages/cutctx/spec.md` §11 — check before you write.

## The work, in gate order

**Gate A — the goldens, before any behaviour moves.** Capture the *current* output as fixtures:
several fixture projects covering a generous budget, a budget that drops research notes only, one
that drops distant units, one that drops adjacent units, the strict-versus-greedy case (a large
section followed by a small one), and the overflow that raises. Record `render()` byte-for-byte,
`dropped`, and the error's `details`. Commit these **against the unchanged implementation** so the
diff proves they were not written to fit the new one.

**Gate B — the mapping.** Turn construction, the budget, the chain, the error translation, behind
the unchanged seam (D1). Goldens from Gate A pass unmodified — if one needs editing, the row has
changed behaviour and must stop and explain.

**Gate C — the deletion.** D2. `pyproject.toml` gains `cutctx>=0.1,<0.2`. Full gate plus coverage.

**Gate D — the report, and the docs.** D4; `workflows.md` §7 gains a sentence naming CutCtx as
what performs the reduction (the *order* stays as documented — do not restate it in package
terms); mirror and `cmp`. The ADR, if D6 says so. `outstanding-work.md`'s J1/J2 rows corrected for
the version (ground truth 1).

**Gate E — the release.** `CHANGELOG.md` `[Unreleased]` → `## [1.2.0]`, full gate plus `pytest
--cov`, commit `chore(release): ideapress 1.2.0`. **Stop there — no tag, no push, no publish.**

## Stop rules

* **A golden that has to be edited is a stop, not a rebase.** If the chain cannot reproduce the
  current output, say precisely which case differs and by what, and stop with the goldens green
  against the old implementation. A silently "improved" reduction is the one outcome this row
  cannot ship.
* If parity needs a new CutCtx policy, **stop**: that is a CutCtx row (`0.2.0`), not an IdeaPress
  one, and it makes the package the second consumer's shape rather than a shared one.
* Do not widen into `project_review` beyond D3's answer, and do not add a settings key.
* Do not touch the adapter, budget or egress surfaces — those are J1's files
  (`services/workspace.py`, `web/templates/workspace/index.html`, `config.py`). If J1 is running in
  another session, you share no file with it; keep it that way.
* Never weaken `.importlinter`.

## Exit conditions

1. `project_review`'s status is decided and stated (D3), with the follow-up filed if the
   recommendation is taken.
2. The stage's context assembly runs through `cutctx`, and the in-app reduction decision code is
   gone from `domain/context_assembly.py`.
3. Golden parity: byte-identical `render()`, identical `dropped`, identical error details, on every
   fixture project — with the goldens committed *before* the change.
4. The default gate is green on a named interpreter, coverage at or above 85 %, with no network,
   no GPU and no LoadCoach installed.
5. `workflows.md` §7 is current, mirrored and `cmp`-clean; the roadmap row's version is corrected.
6. `1.2.0` prepared, committed, untagged and unpushed; `git status --short` clean in every
   repository touched.

## The handoff

`docs/history/J2_HANDOFF.md`, in the house shape:

1. Gate results with the exact invocations and the interpreter.
2. The gates as commits.
3. **The six decisions** (D1–D6), each with what the losing option would have claimed.
4. **The parity evidence**: the golden cases, and the strict-versus-greedy case in particular —
   what the two orderings would each have kept, and which the chain produced.
5. Exit conditions, answered one by one.
6. Things this prompt said that turned out not to be true (line numbers were read on 2026-09-07).
7. What the operator still has to do: tag and publish `ideapress 1.2.0`.
8. Anything found that belongs to another row — in particular `project_review`'s unbudgeted prompt
   (ground truth 2), the dead `research_notes` path (ground truth 3), and anything CutCtx would
   need to serve a third consumer.

## Constraints

* **IdeaPress and `docs/` only.** CutCtx is adopted as published; it is not edited here.
* **Parity over elegance.** If the mapping is ugly but byte-identical, ship the ugly mapping and
  name the ceiling in a `ponytail:`-style comment.
* **A model is never a test oracle**, and no part of this row calls one — the assembly is pure
  Python and stays pure.
* If the work must stop early, stop at a green gate with a commit, and say exactly where you
  stopped and what remains.
