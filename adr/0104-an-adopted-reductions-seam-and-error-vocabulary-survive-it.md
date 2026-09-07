# ADR-0104 — An adopted reduction's seam and error vocabulary survive it

**Status:** Accepted (2026-09-07)
**Amends:** [Workflows §7](../apps/ideapress/workflows.md) (names CutCtx as what performs the
documented reduction order; the order itself is unchanged).
**Relates to:** [CutCtx spec §11](../packages/cutctx/spec.md) (contracts 1–5: view-not-deletion,
the untouchable set, determinism, honest estimates), [ADR-0052](0052-compaction-is-a-view-and-the-package-plans-it-only.md)
(compaction is a view; a package below the applications never calls a model),
[ADR-0016](0016-unavailable-is-not-zero.md) (an estimate is never presented as a count, which is
why `cutctx.CharRatioEstimator` rides under `estimate_tokens` rather than replacing it as a
public name).
**Source:** Row J2 — IdeaPress's `domain/context_assembly.py` adopts `cutctx 0.1.0` for the
first time a shipped package's own consumer-mapping note (spec §7's "Mapping a caller's world
onto these types") became code.

## Context

CutCtx's spec has described IdeaPress's stage-context reduction as an adoption target since before
CutCtx existed — a hand-rolled "research notes → distant unit summaries → adjacent unit
summaries" order, ranked and strictly filled, is exactly a `CompactionPolicy` written in prose. Row
J2 is the adoption, and it forced three decisions that neither CutCtx's spec nor IdeaPress's own
docs had settled, because neither document is about the *seam* between an application and a shared
reduction package — only about each side of it separately.

1. **What survives at the call site.** CutCtx's vocabulary (`Transcript`, `TranscriptTurn`,
   `CompactionPlan`, `BudgetUnsatisfiable`) is generic on purpose — it has two consumers with
   different shapes. IdeaPress's callers (`services/unit_loop.py`, `services/review_loop.py`) know
   `AssembledContext` and `ContextLimitExceeded`, not turns and plans. Exposing CutCtx's types past
   `domain/context_assembly.py` would have made every caller a second consumer of the mapping
   IdeaPress alone owns, and made the row's parity claim — the same public seam, the same two
   error numbers — unverifiable without reading three files instead of one.
2. **How the untouchable set is expressed.** CutCtx offers two knobs that both protect turns:
   `pinned` (a property of the turn) and `protected_recent_turns` (a property of the budget, a tail
   window). Workflows §7's undroppable sections — the unit specification, its requirements, style,
   previous findings — are not a *tail*; they are named sections that may sit anywhere in the
   assembled context. Using `protected_recent_turns` for them would have made the untouchable set
   depend on *where* a caller happened to place a turn rather than on *what it is*, and it would
   have silently protected whatever turns are budget-agnostic, ordered last — the exact ambiguity
   the mapping in CutCtx spec §7 warns a second consumer's mapping must resolve for itself.
3. **What happens to `BudgetUnsatisfiable`.** CutCtx spec §13 hands the package's own error back
   to the caller undecorated. IdeaPress has carried `ContextLimitExceeded` since before CutCtx
   existed, with its own message ("nothing here can be reduced: raise
   `workflow.context_budget_tokens`...") and its own detail keys (`unit_key`, `requirement_count`,
   `undroppable_sections`) that `tests/unit/test_context_budget.py` and the stage runner both
   already depend on. A caller that let `BudgetUnsatisfiable` propagate would have broken every
   consumer of the old error's shape for no behavioural gain — the numbers it carries
   (`untouchable_tokens`, `max_tokens`) are the same numbers, spelled by a different vocabulary.

## Decision

**A shared reduction package is adopted *underneath* the caller's existing public seam, never
alongside it; the untouchable set is expressed as `pinned` rather than as the protected tail; and
the package's own error is translated into the caller's typed error at the boundary, never let
through.**

1. `assemble_context()`'s signature, `AssembledContext`'s fields (`sections`, `dropped`,
   `budget_tokens`) and its `render()`/`section()` are unchanged by the adoption. `cutctx` types
   (`Transcript`, `TranscriptTurn`, `CompactionPlan`, `Action`) appear only inside
   `domain/context_assembly.py`; nothing above it imports `cutctx` (asserted by `lint-imports`'
   layering contract, which forbids a leaked dependency by construction rather than by review).
2. `CompactionBudget.protected_recent_turns` is fixed at `0` for every caller mapping its own
   undroppable set through `pinned`. A tail window is the right primitive for a live conversation's
   "the last few turns are always in context"; it is the wrong primitive for a set of named,
   possibly-scattered sections, and setting it to `0` rather than leaving its default (`4`) is
   required, not incidental — the default would silently pin whatever three sections happen to be
   built last, changing the `BudgetUnsatisfiable` threshold in a way workflows §7 never described.
3. `cutctx.BudgetUnsatisfiable` is caught at the seam and translated into the caller's own typed
   error, using the numbers `BudgetUnsatisfiable.details` already carries
   (`untouchable_tokens` → `required_tokens`, `max_tokens` → `budget_tokens`) plus whatever
   context-specific detail the caller's error contract promises (IdeaPress adds `unit_key`,
   `requirement_count`, `undroppable_sections`, none of which CutCtx could know). CutCtx's own
   error class and message never reach a caller of the adopting module.

## What this refuses

* **A second public vocabulary for one capability.** A caller that imported `cutctx.Transcript`
  directly to build its context would have two ways to describe "what's in the window" —
  `AssembledContext` and `Transcript` — disagreeing the moment either one changed independently.
* **Reusing `protected_recent_turns` as a convenience.** It looks like it does the same job as
  `pinned` when a fixture happens to put its undroppable sections last; workflows §7's own section
  order (`unit specification` before `neighbouring units` before `previous findings`) is exactly
  the case where it would not.
* **Letting a package's error be the caller's error.** `BudgetUnsatisfiable` is honest and
  correctly numbered, and letting it propagate was briefly attractive as the smaller diff. It is
  refused because a caller's error contract is part of that caller's own public API (tested,
  documented, depended on by its own callers), and a shared package's adoption must not silently
  change it.

## Consequences

* Every future adopter of CutCtx (PromptCadence's own transcript compaction, and any future
  IdeaPress `project_review` reduction, ground truth 2 of this row's kickoff) inherits this
  seam-and-translation shape as the reviewed pattern rather than re-deriving it.
* The turn-construction and presentation-ordering code in `domain/context_assembly.py`
  (`_rank_of`, `_priority_key`) is not "dead code left behind" — it changed role from *deciding*
  what survives to *positioning* sections for CutCtx to decide and then *re-presenting* what it
  decided in workflows §7's order. A reviewer expecting D2's "decision code goes" to mean the
  function disappears should read this ADR rather than the kickoff's shorthand.
* A future adopter that finds `pinned` insufficient — an untouchable set that is not a fixed
  property of a turn, but depends on the *budget itself* — has found a real gap this ADR does not
  close, and it belongs in a CutCtx row, not a workaround at any one caller.

## Revisit when

A second IdeaPress reduction (`project_review`, or a future stage) needs an untouchable set that
is not expressible as `pinned` — for instance, a section that is droppable under one workflow
configuration and undroppable under another. That is a real per-caller policy decision CutCtx's
`pinned` cannot express by itself, and it deserves its own record rather than a second exception
bolted onto this one.
