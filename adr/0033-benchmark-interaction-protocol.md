# ADR-0033 — Benchmark interactions: multi-turn execution and the two scorer protocols

**Status:** Accepted (2026-08-27)
**Amended by:** [ADR-0034](0034-run-level-derived-metrics.md) — adds the *aggregation* seam beside this one, under the same "a benchmark touches no provider, database or clock" constraint.
**Amends:** [FreeWeight spec §7](../apps/freeweight/spec.md), [Benchmark Catalog §5](../apps/freeweight/benchmark-catalog.md).
**Related:** [ADR-0003](0003-sync-vs-async-strategy.md) (synchronous below the edge), [ADR-0016](0016-unavailable-is-not-zero.md), [ADR-0018](0018-external-benchmark-isolation.md) (the other way a benchmark reaches outside itself), [Security Standards §6](../standards/security-standards.md).

## Context

Through FreeWeight Phase 6 every benchmark was one shape: **one prompt, one provider call, one
scored response.** The run engine built a request from a case, called `generate` or `stream`, handed
`result.text` to the test's scorer and stored one sample. `native.echo`, `native.performance` and
`native.token_economy` all fit, and nothing in the architecture said they had to.

Phase 7 delivers five suites, and three of them do not fit:

* **`native.tool_use`, `native.tool_recovery`, `native.agent`** are loops. The model asks for a tool,
  the harness runs it, the result goes back as a `tool` turn, and the model is asked again. What is
  measured — tool selection, argument correctness, wrong turns, calls per success, recovery from an
  injected failure ([Benchmark Catalog §3.6–3.8](../apps/freeweight/benchmark-catalog.md)) — is a
  property of the *trajectory*. None of it is visible in the model's final sentence.
* **`native.structured_output`** is a call plus, at most, one corrective retry, because §3.5 measures
  "recovery rate after one corrective retry" as a figure distinct from first-attempt conformance.

This forces two decisions the documentation did not contain, and both of them are load-bearing well
beyond Phase 7. Phase 8B's jury calls a judge model several times per sample; Phase 13's external
adapters drive a subprocess whose transcript is the result. Deciding this ad hoc, inside the run
engine, three times, is how the run engine becomes the thing nobody can change.

There is also a **containment** dimension. A loop that feeds tool output back into a prompt is the
one place in this application where model-generated content comes closest to steering execution.
[Testing Standards §3](../standards/testing-standards.md) and the suite's own gold standards are
categorical: a model never decides control flow. Whatever shape this takes has to make that
structurally true rather than carefully observed.

## Decision

### 1. A benchmark test may declare an *interaction*; the run engine executes it

The seam is one function type and one result type.

```python
class TurnCaller(Protocol):
    """Supplied by the run engine: here is a conversation, give me the next assistant turn."""
    def __call__(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ToolDefinition] = (),
        response_format: ResponseFormat | None = None,
    ) -> GenerationResult: ...


class Interaction(Protocol):
    """Declared by a benchmark test. A test declaring one is executed through it."""
    def run(self, caller: TurnCaller, case: BenchmarkCase) -> InteractionOutcome: ...
```

`InteractionOutcome` carries every `GenerationResult` obtained, the text to be scored, an optional
tool transcript, extra evidence for `samples.result_json`, and an error code and text.

**The division of labour is the point.**

| The run engine owns | A benchmark owns |
|---|---|
| When a call happens, and the sampling parameters, seed and timeout it happens under — the run's *frozen* execution config, identically on every turn | What to say next |
| Counting what every turn cost, and storing one sample for the whole interaction | Which tools to offer, and what to do with their results |
| Cancellation checks, error containment, event publication | When it has an answer |

A benchmark never touches the provider, the database or the clock, so an interaction is unit-testable
with a two-line fake caller and cannot make a run irreproducible by varying a sampling parameter
mid-trajectory.

### 2. Interactions are bounded, and exhausting the bound is a *measurement*

Every interaction has a step budget. Running out of it is neither an error nor a hang: the sample is
stored, scored as a failure to complete, and carries `hit_step_limit`. A model that loops forever is
a fact about that model, and this is where it is recorded.

### 3. Control flow advances on declared provider state, never on model text

A loop continues because the provider reported `finish_reason = TOOL_CALLS` and the result carries
tool calls — never because the model wrote something that reads like a decision. A model that says
"I am finished" while still requesting a tool is still requesting a tool. This is
[Testing Standards §3](../standards/testing-standards.md)'s rule, made structural at the one place it
is most tempting to relax.

### 4. Tokens are summed across an interaction's turns; provider timings are not

A sample's `input_tokens` and `output_tokens` cover the whole interaction — a tool trajectory that
generated four turns cost four turns, and `native.token_economy`'s per-success figures over a tool
suite would otherwise report a fraction of the real cost. Summing is over the turns that *reported* a
count; where none did, the column stays `NULL` — "not reported", not zero ([ADR-0016](0016-unavailable-is-not-zero.md)).

The provider's own `backend_*` durations are **not** summed. A provider reports them per call; a sum
across calls is a figure no provider ever produced, and inventing one is the failure this suite's
timing rules exist to prevent. They are recorded from the final turn alone.

### 5. There are two scorer protocols, and the engine dispatches on the type

`Scorer.score(case, response_text)` cannot express a trajectory. Rather than widen it — which would
touch every existing scorer to serve three suites — a sibling protocol is added:

```python
class TrajectoryScorer(Protocol):
    def score_trajectory(self, case: BenchmarkCase, transcript: ToolTranscript) -> ScoreResult: ...
```

**There is no fallback.** An interaction that produced a transcript is scored by a
`TrajectoryScorer` or not at all; a transcript is never quietly scored on its final sentence, because
a suite measuring tool selection would then silently report an exact-match figure under a
tool-selection metric key. Both protocols return the same `ScoreResult`, so `samples.score_method`,
the `NULL`-score rules and aggregation are unchanged.

### 6. A scorer may report several numbers, and a missing one stays missing

A trajectory scorer measures a dozen things at once. Its `ScoreResult.detail` may therefore carry a
number per metric key, and aggregation prefers that number over the headline score when *any*
completed sample in the group carries one. A sample that measured no value for a key is **excluded**
from that metric with `not_measured_for_this_case` rather than contributing a zero — ordering
accuracy for a case that requires one call, calls-per-success for a case that failed
([ADR-0016](0016-unavailable-is-not-zero.md)).

The group, not the individual sample, decides whether a key is detail-derived. A per-sample fallback
would let a missing key resolve to the headline score, which is a different number wearing this
metric's name.

### 7. Mock tools are contained by construction, and the harness is not the interaction

The tool harness ([Security Standards §6](../standards/security-standards.md), FreeWeight spec §14)
stays separate from the interaction that drives it: the driver knows how to have a conversation, the
toolbox knows what a tool does. A tool runs only when it is on the case's explicit allowlist and its
arguments validate against its own schema; every path is proved contained after symlink resolution;
reads and writes have different roots; and a refusal is a value the model reads, never an exception
that ends the case.

A containment refusal names the requested path and **not** where it resolved to. An error message is
input to the next prompt exactly as a result is, and one carrying an absolute path would tell the
model where the checkout lives.

### 8. Where this lives, and when it moves

The interaction protocol and its drivers are FreeWeight's, under `freeweight.benchmarks`. They are
**not** extracted now: [ADR-0011](0011-shared-package-boundaries.md)'s bar is two real consumers, and
there is one. LoadCoach's execution layer is the plausible second, at which point the extraction
target is `setspec` only if the protocol crosses an application boundary — which today it does not.

The same reasoning applies to the bounded JSON-Schema validator this phase introduced
(`freeweight.domain.scorers.schema`). It decides a fixed keyword set and **refuses** any other
keyword rather than ignoring it, because a validator that silently skipped `oneOf` would report a
conformance rate for a check it never performed. LoadCoach spec §27 wants the same validation with a
corrective retry; that is the second consumer, and the extraction rides along with the
`setspec.prompts` work at LoadCoach P4 ([ADR-0028](0028-prompt-pack-granularity.md)) rather than
adding a phase.

### 9. `requires.provider_capabilities` is enforced, and unknown names are unmet

A benchmark test's `requires["provider_capabilities"]` names
`ProviderCapabilities` fields and is checked *before* the test runs. An unmet requirement makes the
test `skipped` with `run_tests.skip_reason = "unsupported_capability"` and `CAPABILITY_UNSUPPORTED`
on the row; the test produces no samples, contributes no score, and the run completes normally
([graceful degradation](../architecture/graceful-degradation.md), FreeWeight spec §13).

A name that is not a `ProviderCapabilities` field is treated as **unmet**, never as satisfied: the
honest reading of "I cannot tell whether this provider can do that" is that the test must not run.
Because a typo would then silently skip a suite, every declared name is validated against the
capability set when the registry is built — which is startup — so a manifest naming
`tool_calls` instead of `tool_calling` fails to launch rather than reporting a skip forever.

## Alternatives considered

**Widen `Scorer.score` to take an optional evidence mapping.** Rejected. Every existing scorer would
change signature to serve three suites, and an optional argument that three implementations require
and four ignore is a protocol that documents nothing. The type-level split is what lets the engine
*refuse* to score a trajectory on its final sentence.

**Serialize the trajectory into `response_text` and keep one protocol.** Rejected, and it was the
tempting one. `samples.response_hash` and `response_text` would then describe a JSON document the
model never produced, breaking the drill-down for the three suites that need it most.

**Put the loop in the run engine, switched on a benchmark's category.** Rejected: it puts benchmark
logic in the engine, makes every new suite shape an engine change, and gives the engine a growing
`match` over categories — the "god module" the coding standards name as an anti-pattern.

**Give the benchmark the provider.** Rejected outright. A benchmark that holds a provider can vary
sampling parameters mid-trajectory, retry silently, or call a different model, and no amount of
review would reliably catch it. The engine keeps the provider precisely so that "the same run,
again" continues to mean something.

**Add `jsonschema` as a dependency instead of a bounded validator.** Rejected for now: it is a
runtime dependency added to serve one phase, and a full implementation would accept keywords the
benchmark schemas do not use and whose failure modes nobody here has thought about. The bound is
enforced by refusal, so the day a case needs more, the build says so.

## Consequences

*Positive.* A new suite shape is a new `Interaction`, not an engine change. The three Phase 7 tool
suites, Phase 8B's jury and Phase 13's adapters share one seam, one cost-accounting rule and one
containment story. A trajectory cannot be scored by the wrong instrument, because the wrong
instrument does not type-check.

*Positive.* Enforcing `requires` closes a two-phase-old gap between a documented behaviour and the
code, and it is what makes "a model without tool support yields a recorded skip, never a low score"
true rather than aspirational.

*Negative.* FreeWeight now has two scorer protocols, and a reader has to know which one a suite uses.
Mitigated by the engine's dispatch being explicit and by both returning the same `ScoreResult`.

*Negative.* Enforcing `requires` changes the behaviour of the Phase 6 suites on a weak provider:
`native.performance` and `native.token_economy` now skip rather than producing `UNSUPPORTED`-heavy
results. This is the behaviour the protocol always documented, and a skip with a reason is more
useful than a run of empty columns — but it is a change, and it will first be visible against a bare
OpenAI-compatible endpoint at Phase 4/13.

*Negative.* Aggregation now has three sources for a metric value rather than two. The order is fixed
and documented, and the group-level decision keeps a missing key from silently resolving to the
score.

## Revisit when

A second application needs to drive a multi-turn benchmark interaction, which makes extraction worth
its cost under [ADR-0011](0011-shared-package-boundaries.md); or an interaction needs to run its
turns concurrently — the catalog's optional concurrency-scaling row, and its "parallel independent
tools" scenario if that ever means genuine concurrency rather than order-independence — which the
synchronous execution path of [ADR-0003](0003-sync-vs-async-strategy.md) cannot express and which
would need its own decision about what a concurrent trajectory's timings even mean.
