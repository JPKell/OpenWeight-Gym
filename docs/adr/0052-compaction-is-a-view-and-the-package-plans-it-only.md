# ADR-0052 — Compaction is a view, and the package that plans a summary never calls a model

**Status:** Accepted (2026-09-02)
**Extends:** [CutCtx Spec §3 and §11](../packages/cutctx/spec.md),
[PromptCadence Lifecycle §7](../apps/promptcadence/lifecycle.md).
**Relates to:** [ADR-0007](0007-provider-abstraction.md) (ModelRack is the suite's only provider
client), [ADR-0023](0023-runtime-profile-resolution.md) (silent truncation is never acceptable),
[ADR-0016](0016-unavailable-is-not-zero.md) (an estimate is labelled as one),
[ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) (no second inference path),
[ADR-0012](0012-prompt-storage-format.md) (the summary prompt is a versioned record, not a
literal).
**Source:** [PromptCadence roadmap §2, D-8](../roadmap/promptcadence-roadmap.md).

## Context

Two components in the suite have the same problem: a body of text has outgrown the window it must
fit. PromptCadence's agent transcripts grow turn by turn; IdeaPress's `project_review` stage
reasons over every committed unit of a project and already documents a hand-rolled reduction order
in prose ("research notes → distant unit summaries → adjacent unit…"). That prose *is* a compaction
policy, written twice, in two applications, in English.

Extracting it is straightforward until summarization appears. Masking a tool result and dropping an
old turn are pure functions over values. Summarizing is not: it needs a model, which means a
provider client, a budget, a tier, an egress verdict and a prompt record. A package that summarizes
is a package that infers, and CutCtx sits below the applications — where a path to a model would be
a second inference path that no ledger debits and no egress decision governs. It is
[ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md)'s objection at the package
layer.

The second question is what compaction *does* to the record. The cheap implementation drops turns
from the store, which frees space and is irreversible. But PromptCadence's explanation contract
requires every turn to remain reconstructable, and a materialized explanation whose rows have been
edited by a compaction cannot satisfy `materialize(rows) == compose_live(rows)`
([ADR-0057](0057-the-explanation-is-materialized-and-the-rows-stay-authoritative.md)).

## Decision

**A compaction plan is a view. CutCtx is pure: it plans summarization and never performs it.**

1. **A plan never mutates and never deletes.** `CompactionExecutor.apply` returns a new
   `CompactedTranscript`; the input transcript is unchanged, and what the caller retains is the
   caller's data-ownership decision (PromptCadence retains everything; the store keeps every
   original turn, and what changes is only the snapshot sent to the model).
2. **CutCtx performs no I/O of any kind** — no database, no filesystem, no network, no environment,
   no logging. It imports `baseaicore` and nothing else, and an import-graph test asserts it. There
   is no HTTP client and no provider import, so the "second path to a model" is absent by
   construction rather than by policy.
3. **Summarization crosses the boundary as a request object.** `SummarizingPolicy` emits a
   `SummarizationRequest(group_id, turn_ids, target_tokens, prompt_id)` inside the plan. The
   application fulfils it through **its own governed inference path** — PromptCadence via LoadCoach,
   IdeaPress via its inference port — and passes the summaries back to `apply()`. A plan whose
   request has no supplied summary raises `SummaryMissing` naming the group; it never silently skips
   the reduction.
4. **The prompt is named, never carried.** `prompt_id` refers to a versioned record in the
   application's own prompt pack ([ADR-0012](0012-prompt-storage-format.md)); CutCtx contains no
   prompt text.
5. **A summary of confidential turns runs on a local tier only.** The summarization call is itself
   governed work: it is a turn, it is debited, it is recorded, and it carries the trajectory's
   classification. A summary of confidential material is confidential material, so PromptCadence
   executes it on the cheapest admissible **local** tier — compaction must not become the route by
   which restricted content leaves the machine.
6. **The invariants hold or the plan refuses.** The system turn, pinned turns and the
   `protected_recent_turns` tail are untouchable; a tool call and its result are masked,
   summarized or dropped **together**; a budget smaller than the untouchable set raises
   `BudgetUnsatisfiable` **with both numbers** rather than being "solved" by violating an invariant;
   an exhausted chain returns a plan that is still over budget, flagged `budget_unmet`, and the
   caller decides — never a silent truncation ([ADR-0023](0023-runtime-profile-resolution.md)'s
   rule, applied to transcripts).
7. **Plans are deterministic and golden-tested.** Same transcript, budget and policy configuration
   ⇒ byte-identical plan, on every platform — because a plan appears in an audit record, and a
   record nobody can reproduce is not evidence.

## Alternatives considered

**Let CutCtx call the model itself**, taking a provider or an HTTP client. One call, no
choreography, and the caller never has to understand a two-phase protocol. Rejected: it puts an
inference path underneath the applications, where no budget debits it, no egress policy evaluates
it and no tier constrains it — and a transcript summarization is not a small call. It would also
require importing ModelRack, which a capability package may not do to a sibling, or embedding a
second HTTP client, which is worse.

**Inject a `Summarizer` protocol that the application implements.** The strongest alternative by
some distance: CutCtx would still import nothing, the application's implementation would still run
through its governed path, and the two-phase dance would disappear behind ordinary dependency
injection. Rejected on determinism and atomicity. A `decide()` that may call out is no longer a
pure function, so "same inputs ⇒ byte-identical plan" — the property that lets a plan be inspected,
budgeted and golden-tested *before* anything is spent — is gone. And a summarizer that fails on the
third of five groups leaves a half-applied compaction with no obvious state to return to, whereas a
plan is either fulfilled and applied or not applied at all. Separating the decision from the
expensive part is what makes the decision auditable.

**Delete turns rather than compute a view.** Frees storage, and it is what a naive implementation
does. Rejected: PromptCadence's explanation contract requires every turn to stay reconstructable,
and a deletion makes `materialize(rows) == compose_live(rows)` unprovable after the fact — the
compaction would silently become the reason a trajectory can no longer be explained. Retention is
handled by the retention sweep, which is a policy with its own record and its own revision bump,
not a side effect of fitting a context window.

**Let the chain truncate silently when it cannot fit the budget.** Rejected by direct analogy:
ADR-0023 refused "trust `max_context` and let the provider truncate" because silent truncation of
input is undetectable from the output. A `budget_unmet` flag hands the caller a decision it can act
on — PromptCadence halts with `COMPACTION_FAILED` — instead of a quietly shortened prompt.

**Count tokens exactly with a tokenizer.** Rejected: it would add a heavyweight dependency to a
package whose whole value is purity, and tie plans to one tokenizer's version. Estimates come from
an injected `TokenEstimator`, the character-ratio default records its ratio on the plan, and an
estimate is never presented as a count.

## Consequences

* CutCtx ships with `baseaicore` as its only dependency and a coverage floor of 95 %. Its test
  suite needs no model, no network and no database — property-based tests over random transcripts
  are affordable precisely because everything is a pure function.
* PromptCadence executes summarization requests itself, which means each one is a turn with a
  ledger debit, an egress decision, a recorded prompt id and a place in the explanation. Compaction
  is visible in the record rather than being an invisible reduction someone notices later.
* The two-phase protocol is real friction for a caller: plan, fulfil requests, apply. It is
  documented as the package's shape, and `SummaryMissing` makes the omitted middle step a loud
  failure rather than a quiet one.
* IdeaPress's `project_review` reduction becomes a policy chain at M13, with golden-tested identical
  output on the fixture projects — the adoption phase is the proof that the abstraction fits two
  consumers rather than one.
* An operator can read a `CompactionReport` and know exactly what the model was shown: which turns
  were masked, which were summarized into what, and the estimate before and after.

## Revisit when

A policy needs model access of its own — an embedding-relevance policy that keeps turns similar to
the current step is the concrete case, and it will arrive once ModelRack has an embeddings API. It
does **not** reopen this record: it arrives as another `CompactionPolicy` emitting a planned
request, in exactly the form `SummarizationRequest` established. What would reopen it is a policy
whose decision genuinely cannot be made without a model call *during* planning — at which point the
purity claim, not the policy, is what needs re-deciding.
