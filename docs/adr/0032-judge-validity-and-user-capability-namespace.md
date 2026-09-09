# ADR-0032 — Judge validity in confidence, and the `user.*` capability namespace

**Status:** Accepted (2026-08-26)
**Amends:** [ADR-0017](0017-benchmark-confidence-and-freshness.md) (adds a sixth confidence factor and two hard separations), [ADR-0022](0022-capability-evidence-record-contract.md) (adds fields to the evidence record), [SetSpec capability vocabulary](../packages/setspec/spec.md) (adds one root; minor bump to 1.1).
**Depends on:** [ADR-0031](0031-user-defined-goal-benchmarks.md), which defines what is being exported.

## Context

[ADR-0031](0031-user-defined-goal-benchmarks.md) makes a user-authored, judge-scored goal a
first-class benchmark inside FreeWeight. This ADR decides what, if anything, crosses the application
boundary into `capability.evidence` — the contract LoadCoach routes on.

Three constraints collide.

**The vocabulary is closed at the root.** `setspec.vocabulary.CAPABILITIES` enumerates twenty roots
and validates a candidate's *root*, leaving specializations open-ended: `coding.rust` is valid the
moment `coding` is known. A goal invented on a Tuesday has no root at all. Rejecting it outright
would confine goal results to FreeWeight; minting a root per goal would make the vocabulary
unversionable, since every user's rubric would be a minor bump to a shared contract.

**ADR-0017's confidence formula has no term for validity.** Its five factors describe sample count,
dispersion, age, environment drift and identity strength. Every one of them can be excellent for a
judged score that is measuring the wrong thing: 200 samples, tight variance, measured this morning,
digest identity, on a rubric the judge understands completely differently from the user. The formula
was designed for measurements whose *correctness* was not in question, only their *weight*. A
calibrated instrument has a second, independent error term, and it is usually the larger one.

**A subjective score must never outrank a deterministic one by accident.** If `user.house_voice`
scores 0.91 with confidence 0.88 while EvalPlus pass@1 scores 0.62 with confidence 0.79, a router
that treats them as commensurable is making a taste judgement look like an engineering one.

## Decision

### 1. One new root: `user`

SetSpec's capability vocabulary gains exactly one root — `user` — at
`CAPABILITY_VOCABULARY_VERSION = "1.1"` (an addition; minor per rule 8 of the SetSpec spec).

Goal capabilities are specializations of it: `user.noir_tech_voice`, `user.house_style`,
`user.brief_faithfulness`. These validate under the existing root rule with **no further vocabulary
changes ever** — the open-ended specialization mechanism that already accepts `coding.rust` accepts
every goal any user will ever write. One root, once, and the contract is closed again.

The `user` root is reserved: no shipped benchmark maps onto it, and FreeWeight refuses a goal slug
that would collide with a shipped capability root.

A goal **may additionally declare** that it contributes to a shipped capability
(`contributes_to: "creative_writing"`). When it does, it is emitted **twice**: once as
`user.<slug>` carrying its own identity, and once as a weighted source inside the shipped
capability's evidence. It is never emitted *only* as the shipped capability — that would silently
fold one person's taste into a term other components believe is objective.

### 2. A sixth confidence factor: `judge_validity_factor`

ADR-0017's formula becomes:

```text
confidence = sample_factor × consistency_factor × freshness_factor
           × environment_factor × identity_factor × judge_validity_factor
             clamped to [0.05, 1.0]
```

| Factor | Definition |
|---|---|
| `judge_validity_factor` | `Σ(weight_c × v_c) / Σ(weight_c)` over the criteria contributing to the score, where `v_c = 1.0` for any criterion scored at ladder rung 1–4, and `v_c = max(0, kappa_w,c) × min(1, sqrt(n_holdout / n_holdout_target))` for a rung-5 judged criterion. `n_holdout_target` defaults to 10. Clamped to `[0.05, 1.0]`. |

Three properties this is chosen for:

* **It is 1.0 for every existing measurement.** No deterministic result changes value, and no
  currently-specified behaviour is altered by this ADR. The factor is inert until a goal exists.
* **Mechanizing a criterion raises confidence.** A goal that moves "no corporate hedging" from a
  judged criterion to a phrase-list rule gains validity arithmetically. The formula pays the user
  for climbing the ladder, which is the incentive the ladder has lacked.
* **Small calibration sets are shrunk toward zero, not trusted.** `kappa_w` over 4 holdout samples is
  nearly meaningless; the `sqrt(n_holdout / 10)` term is the same shape as ADR-0017's existing
  `sample_factor`, so it introduces no new statistical vocabulary for a user to learn. Six holdout
  samples at `kappa_w = 0.71` yields `0.71 × 0.77 = 0.55`, not `0.71`.

The parameters (`n_holdout_target`, the gate) are configuration, recorded on the evidence with the
policy version, exactly as ADR-0017's own parameters are.

### 3. The calibration gate is a refusal to export, not a refusal to run

When weighted `kappa_w` across a goal's judged criteria falls below `calibration.min_agreement`
(default 0.40):

* The run **executes and completes**. Every sample, score, judge rationale and disagreement is
  stored and inspectable.
* The result is badged **UNCALIBRATED** in the UI, in the CLI and in `benchmark.result`.
* It emits **no `capability.evidence`** at all. Not discounted evidence — none.
* The UI names the criteria and the specific samples where judge and user diverged most.

This is the one place in the suite where a measurement is withheld rather than degraded, and the
departure from "degrade, never discard" is deliberate. ADR-0017's floor of 0.05 exists so weak
evidence survives as a tiebreak; that logic assumes the measurement is *of the right thing*. An
uncalibrated rubric has not established what it measures, so there is no quantity to attach a low
confidence to. Emitting it at the floor would put a number of unknown meaning into routing, where
the floor would eventually make it decisive against an absent alternative.

Running the benchmark anyway is what makes the gate useful rather than merely obstructive: the
diagnostic data is exactly what the user needs to fix the rubric, and it costs one GPU-bound run to
obtain.

### 4. Two new hard separations

Added to ADR-0017's list. Evidence is partitioned, never merely discounted, when:

* the **`goal_hash`** differs — a different rubric is a different measurement, exactly as a different
  benchmark version is;
* the **judge set identity** differs — jury membership, judge model digests, judge prompt versions,
  or local-versus-remote. A different instrument is a different measurement.

The **calibration record hash** is provenance rather than a separation input: re-grading the same
rubric refines the instrument's characterization without changing what is being measured, and it
already flows into confidence through `judge_validity_factor`.

### 5. Evidence record additions

`capability.evidence` ([ADR-0022](0022-capability-evidence-record-contract.md)) gains, for
goal-sourced records only:

```text
goal_hash                 the measurement-defining hash of the goal pack
goal_pack_version         semantic version of the pack
score_method_mix          fraction of scored weight by ladder rung: {rule: 0.6, judge: 0.4}
judge_set                 jury members (canonical model IDs), prompt IDs and versions, remote flag
calibration               {kappa_w, rho, mae, bias, n_anchor, n_holdout, graded_by, measured_at}
judge_validity_factor     the computed factor, so a consumer can see it without recomputing
uncalibrated              always false in an emitted record; present so its absence is not ambiguous
```

`vocabulary_version` on such a record is `1.1` or later.

### 6. LoadCoach applies, and opts in

Per ADR-0017's ownership rule, FreeWeight computes and LoadCoach applies. Two additions to the
consumer contract:

* `user.*` capabilities are **opt-in for routing**. LoadCoach does not weight a `user.*` capability
  unless a task profile names it explicitly. A capability that only one person's taste defines must
  not silently acquire influence over routing by existing.
* A routing explanation that used a `user.*` capability **says so, names the goal, and shows its
  calibration agreement** — not just its confidence. "Chose qwen3:14b partly on `user.house_voice`
  0.74, judge agreement kappa 0.71 over 6 held-out samples you graded on 2026-08-14" is a sentence a
  user can audit. "Confidence 0.31" is not.

## Alternatives considered

**Keep goal results FreeWeight-local; never export.** The cleanest boundary, and genuinely
attractive: zero new contract surface, zero risk of taste leaking into automated routing. Rejected
because it makes the feature answer the wrong question. A user who has established that one model
writes in their voice and another does not wants that fact used when work is routed. Refusing to
carry it means they route by hand, and the measurement's only consumer is a chart.

**Map goals onto existing capabilities only.** No vocabulary change at all. Rejected as the primary
mechanism: it destroys the goal's identity at the boundary. `creative_writing` would silently become
a blend of shipped judged suites and one user's rubric, and no consumer could tell which. Retained as
the *optional secondary* emission in §1, where the `user.<slug>` record preserves the identity that
the blend loses.

**A root per goal, minted on demand.** Rejected: it makes a versioned cross-component contract
mutable by end users, and every rubric would be a vocabulary bump that other components must
tolerate. The specialization mechanism already solves this properly.

**Fold validity into `consistency_factor`.** Superficially tidy — one fewer factor. Rejected: they
are different quantities with different remedies. Low consistency means measure more; low validity
means rewrite the rubric or change the instrument. Collapsing them would tell a user to collect more
samples of a number that is measuring the wrong thing.

**Emit uncalibrated evidence at the ADR-0017 floor.** Consistent with "degrade, never discard", and
this was the closer call. Rejected for the reason in §3: the floor is a weight for a known quantity,
and an uncalibrated rubric has not established a quantity.

**Bayesian treatment of judge reliability** (a latent true score with judge-specific error). More
principled, and it would handle small holdout sets natively rather than by shrinkage. Rejected for
the same reason ADR-0017 rejected a posterior: the requirement is that a user can audit the number.
`kappa_w = 0.71 over 6 samples you graded` is auditable. Recorded as a future refinement behind the
same interface.

## Consequences

*Positive.* One root, added once, closes the vocabulary question permanently. Every existing
measurement's confidence is unchanged, because the new factor is 1.0 for everything deterministic.
Subjective evidence is structurally incapable of outranking deterministic evidence at equal score,
and the ladder finally has an arithmetic incentive attached to it. A routing decision influenced by
taste says so in words.

*Negative.* Six multiplied factors compound quickly. A goal at `kappa_w` 0.5 with 8 holdout samples,
40 % judged weight, 20 samples and mild drift lands near 0.2 — usable as a tiebreak and little more.
This is intended, but the UI must explain the factor breakdown rather than presenting a single
number, or users will conclude the feature does not work.

*Negative.* A SetSpec minor bump ripples through the compatibility matrix: every component must
accept `1.1` payloads, and older builds will treat `user.*` as an unknown root. ADR-0009's
forward-compatibility rule already covers this — a newer *minor* is accepted and preserved — so the
practical impact is that an older LoadCoach ignores goal evidence rather than failing on it. That is
the correct degradation.

*Negative.* The gate will frustrate users whose first rubric fails it. Mitigated by running the
benchmark anyway and by the disagreement diagnostics, but the first experience of authoring a hard
rubric may well be "this is not measurable yet", and the wizard's copy must prepare the user for that
before they spend the grading effort, not after.

## Revisit when

Enough goals exist to fit `n_holdout_target` and the gate empirically rather than by argument; or
if `user.*` evidence is observed driving routing decisions users disagree with despite passing the
gate, which would indicate the gate is measuring judge-user agreement on the calibration set without
that generalizing to the task set.
