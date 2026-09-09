# ADR-0088 — An excluded measurement falls back to the prior it displaced

**Status:** Accepted (2026-09-06)
**Amends:** [ADR-0023](0023-runtime-profile-resolution.md) §3 (what an excluded
measurement scores, not whether it is excluded), and
[LoadCoach Routing §5](../apps/loadcoach/routing.md)'s scoring precedence.
**Relates to:** [ADR-0017](0017-benchmark-confidence-and-freshness.md) (the hard separations, which
are unchanged), [ADR-0016](0016-unavailable-is-not-zero.md) (an absence is never a zero),
[ADR-0087](0087-the-evidence-gate-admits-only-a-signal-that-scores.md) (the other half of the same
live failure).
**Source:** Row H6, from the H5 interview on 2026-09-06 — the second, independent defect noted while
tightening the gate (`docs/history/H5_HANDOFF.md` §10.1).

## Context

Scoring resolves one capability by precedence: `benchmark`, `production`, `manual`, `declared`, then
the parameter-band prior, then absent. Before any of that it applies three exclusions — unbound
evidence, a foreign machine, a mismatched runtime profile — and a benchmark caught by one of them is
set aside as an `excluded` result carrying its reason and its remedy.

Where that result is *returned* is the defect. It is returned after the precedence loop and **before
the band prior**, so:

| Subject | What is known about it | What it scores |
|---|---|---|
| Measured here, under a profile that does not apply | a real benchmark, elsewhere | `absent` — nothing |
| Never measured anywhere, by anyone | nothing at all | the band prior, `0.40`–`0.60` at confidence `0.3` |

A capability that is absent is excluded from the weighted mean's numerator **and** denominator, so
with a single-capability profile the first subject scores `task_fit = 0.0` and the second scores a
number. **A subject somebody benchmarked ranks below a subject nobody has ever touched, on the
strength of a guess.** That is the same shape as the failure
[ADR-0087](0087-the-evidence-gate-admits-only-a-signal-that-scores.md) closes — a claim beating a
measurement — one layer down, and it is the other half of what let a declaration win at H5.

The ordering was deliberate, and its argument is a good one: a model that *was* measured under
settings that do not apply here is not in the same position as one nobody has measured, and
substituting a guess buries the remedy — the `freeweight run start …` invocation that would produce
matching evidence, which is the one thing a user can act on. That argument is about the
**explanation**. It was implemented as a penalty on the **score**, and those are separable.

## Decision

**An excluded measurement scores the prior it displaced, and keeps its own name, note and remedy in
the explanation.**

1. **The score.** Where a band prior exists and priors are admissible (`require_evidence` off), an
   excluded measurement resolves to that prior's score and confidence — byte-identical to what the
   same subject would have scored had the measurement never existed. Where no prior exists, or
   priors are refused, it stays absent exactly as today. A subject is never *penalised* for having
   been measured.
2. **The name survives the fallback.** The resolved score keeps `source =
   evidence_profile_mismatch` / `evidence_foreign_machine` / `evidence_unbound`, its note, its
   remedy, and the measured profile hash or machine fingerprint it carries. The explanation reads
   the same as it does today; only the number changes. This is the half of the original argument
   that was right, kept.
3. **It is not evidence, and nothing pretends it is.** The resolved score's source is not in the
   measured set, so it contributes **no** measured weight, the `low_evidence` flag is computed
   exactly as before, and [ADR-0087](0087-the-evidence-gate-admits-only-a-signal-that-scores.md)'s
   gate still refuses it. A prior is what it scores; a prior is not what it is called.
4. **The hard separations are untouched.** ADR-0017's and ADR-0023 §3's rule — evidence measured
   under another profile or on another machine does not describe this execution — is exactly as
   strict as it was. This record decides only what stands in its place, and the answer is the same
   thing that stands in for no evidence at all.

## Alternatives considered

**Keep it: an excluded measurement scores nothing.** The status quo, and the code's own stated
reasoning. Rejected because the reasoning defends the *explanation* and was implemented as a penalty
on the *score*, and the two come apart cleanly: rule 2 keeps every word of the remedy while rule 1
removes the penalty. Its remaining defence — that a scoreless candidate makes the user notice — is a
routing decision made worse on purpose to send a message, and the explanation already sends it.

**Rank the excluded measurement above a declared flag** (return it before the precedence loop) — the
strictest reading, and the exact companion of ADR-0087 at the scorer: once a measurement exists and
does not apply, no claim stands in for it either. Rejected because it deepens the very asymmetry
this record exists to remove. It makes *more* subjects score nothing, and it would take a subject
that scores `0.500 declared` today down to `0.0` for the sole reason that somebody once benchmarked
it — which is the defect, argued from the other end.

**Score the excluded measurement itself, at reduced confidence.** Tempting, and rejected for
ADR-0023's own reason: a KV-precision or context change moves metrics by factors, not percentages,
and there is no defensible coefficient. A prior at least admits it is a prior.

## Consequences

* A subject with an excluded measurement and a subject with no measurement now score identically,
  which is the honest statement: nothing is known here about either, and one of them has a remedy
  printed beside it.
* Rankings move for any decision containing a subject whose evidence was excluded — upward, and only
  to where an unmeasured subject already sat. No decision that had a *usable* measurement changes.
* `low_evidence`, `measured_weight` and ADR-0087's gate are all unchanged, because all three read
  the source rather than the score. A decision made entirely on excluded measurements is still
  flagged, still refuses adapters, and still shows every remedy.
* One asymmetry remains and is deliberate: a subject with an excluded measurement and *no* band
  prior (a model whose parameter count was never reported) still scores absent. It is not a
  penalty — the unmeasured sibling scores absent there too.

## Revisit when

Band priors stop being the fallback for an unmeasured subject — if routing ever scores an unmeasured
capability some other way, this record's "the prior it displaced" has to name the new thing instead.
Or if a measured-elsewhere signal acquires a defensible transfer coefficient, at which point rule 1
becomes a floor rather than the answer.
