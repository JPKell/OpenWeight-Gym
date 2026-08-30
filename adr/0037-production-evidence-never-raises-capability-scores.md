# ADR-0037 — Production evidence never raises capability scores; upward adaptation is post-1.0 exploration routing

**Status:** Accepted (2026-08-30)
**Extends:** [Routing §5.1/§6/§11](../apps/loadcoach/routing.md), [Spec §21](../apps/loadcoach/spec.md).

## Context

Routing carried two readings of what production evidence does. §5.1's table listed *production
evidence from executed jobs* as a capability-scoring signal ("used as soon as the minimum sample
count is reached") and promised routing "self-improving as production evidence accumulates";
§11 — after the M5 edit — says production evidence **never enters capability scoring**. Under the
code, §11 is the truth: production evidence acts only through the `reliability_factor`, bounded to
`[0.5, 1.0]`, so it can *lower* a candidate that fails in production and can never *raise* one
that succeeds — the opposite of what §5.1 promised a consumer such as IdeaPress. The M5
verification flagged the contradiction as a contract defect (its F7).

The M5 run chose §11's reading for three reasons (its handoff entry M5-1):

1. `model_capabilities` has no `sample_count` column, so a production-sourced capability row could
   never clear `PRODUCTION_MINIMUM_SAMPLES` honestly without a schema change the phase forbade.
2. The same success rate would otherwise act **twice** on one candidate — once as a capability's
   `weight × score` inside `task_fit`, and again as a multiplier on `task_fit` through the
   factor — which is bounded adaptation applied twice over.
3. The factor is the one place where production evidence is *labelled* as production: the
   explanation shows benchmark evidence under `capabilities` with `source: benchmark` and
   production evidence under `factors.reliability_detail` with `source: production`, in one
   document, and a test holds that no capability entry ever says `production`.

## Decision

In 1.0, production evidence **never enters capability scoring**. It acts on a decision only
through the `reliability_factor` (bounded `[0.5, 1.0]`) — downward discipline for a model that
fails in production, never upward reward for one that succeeds — and through the circuit breaker
and regression detection, which are exclusions and alarms, not scores. Capability scores move
only when *measured* evidence moves them: a FreeWeight import, or a manual score.

**Upward adaptation from production success is deliberately deferred to post-1.0 exploration
routing** (spec §21): a scheme that occasionally makes non-greedy choices to gather production
evidence can also feed that evidence back into scoring with the selection bias accounted for.
Feeding it back *without* exploration would entrench whichever model happened to be routed first —
the incumbent gathers samples, the challenger never does.

## Consequences

*Positive.* One truthful contract: §5.1, §6 and §11 now say the same thing, and the explanation's
labelling matches it. A model cannot promote itself by being routed often; a failing model is
still demoted, excluded and alarmed.

*Negative.* A model that performs well in production gains nothing until a benchmark measures it
or an operator scores it manually — routing without FreeWeight is *guarded*, not self-improving.
Documented in §5.1 exactly so.

## Revisit when

Exploration routing (spec §21) is designed. Add `sample_count` to `model_capabilities` in that
migration; scoring's source precedence already carries a `production` slot waiting for it
(M5-1's closing note).
