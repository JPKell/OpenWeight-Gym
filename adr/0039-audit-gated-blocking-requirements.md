# ADR-0039 — A model's silence must not settle a blocking gate

**Status:** Proposed (2026-08-31) — awaiting sign-off; commit-gate behaviour is unchanged until
this is accepted.
**Extends:** [IdeaPress Workflows §3](../apps/ideapress/workflows.md),
[IdeaPress Spec §11](../apps/ideapress/spec.md).
**Relates to:** [ADR-0016](0016-unavailable-is-not-zero.md) (a value the system cannot measure is
never coerced to one it can), [ADR-0012](0012-prompt-storage-format.md) (the compiler
prompt is a versioned record), risk T1 (a model deciding a gate).

## Context

IdeaPress's commit gate rests on requirement coverage. A requirement with deterministic checks is
settled by Python running them — a model's opinion cannot overturn a check, and that asymmetry is
stated in `evaluate_coverage`'s docstring as the whole of risk T1 in one place. But a requirement
the compiler could not express as a literal check — and the qualitative ones, "must not use a
marketing register", are exactly the ones it cannot — has no check, and for those the gate
consults the audit.

**The defect (M7-20) is *how* it consults the audit.** `services/review_loop.py` builds an
`audit_satisfied` set containing every check-less requirement whose key does not appear in the
round's finding texts. Silence satisfies. A model that says nothing about a requirement — because
it ran out of attention, because the prompt never asked it to speak per-requirement, because it
truncated — thereby *guarantees* it, and `domain/commit.py::evaluate_coverage` lets the commit
proceed with `satisfied_by="audit"`. The model's default behaviour settles precisely the blocking
requirements that have no mechanical backstop. Three aggravations:

* Nothing requires the audit to have *considered* the requirement. The satisfaction test is a
  substring absence over finding text, not an attestation.
* The compiler tends to attach weak checks or none to qualitative requirements, and M7-21 found it
  also emits single-word `must_contain_any` checks that pass against nearly any text — so the
  population of effectively-unchecked blocking requirements is larger than the check-less count.
* The suite's own principle is that "a model is never a test oracle". Silence-as-satisfaction is
  an oracle wearing a blindfold.

M7 marked this blocking before M8 builds anything more on the coverage gate.

## Options

### (a) A blocking requirement must carry a deterministic check, or it is demoted to advisory

The gate becomes wholly mechanical: at plan time, a blocking requirement the compiler leaves
check-less is stored as advisory, flagged, and never gates a commit.

* *For:* the gate is then exactly what it claims to be; no model output can influence a commit.
* *Against:* it silently weakens the author's own material. "Must not use a marketing register"
  is a real *must* the author stated; demoting it to a preference because Python cannot check it
  discards the author's stated intent by a mechanism the author never sees at the moment it
  matters. It also pressures the compiler to invent bad literal checks so requirements keep their
  force — manufacturing exactly the fake guarantees M7-21 flags.

### (b) Audit-satisfaction may gate a commit, but only as an explicit, labelled, affirmative act

Keep the author's *must* blocking, and keep the audit as the only instrument that can reach it —
but replace silence with attestation, and label the result everywhere:

1. **Silence never satisfies.** The audit stages' response schema gains a per-requirement verdict
   (`met` / `not_met` / `cannot_judge`) for each check-less blocking requirement, and only an
   explicit `met` enters `audit_satisfied`. An absent verdict, or `cannot_judge`, leaves the
   requirement unsatisfied and the unit **pauses** with the honest reason — the same first-class
   outcome every other unresolvable condition gets. Nothing is committed to escape the gap.
2. **The label travels.** Everywhere the requirement or its coverage appears — commit event, unit
   page, plan page, `plan show`, `unit show`, and all three exports — it reads as *guaranteed by
   model review, not a deterministic check*.
3. **A lever exists.** `workflow.allow_audit_gated_requirements` (default `true`) lets a user who
   wants a wholly mechanical gate refuse model-gated commits: with it `false`, a check-less
   blocking requirement pauses the unit instead of ever being audit-satisfied.

* *For:* the author's stated musts keep their force; the model performs a bounded, validated task
  (per-requirement verdicts are parseable and refusable) rather than being read by omission; the
  residual trust is explicit, labelled, and switchable off.
* *Against:* a model can still attest wrongly — the guarantee is genuinely weaker than a check,
  which is why the label is mandatory rather than cosmetic. The audit prompt and schema change,
  and the pinned manifest with them.

### (c) Status quo, better labelled

Keep silence-as-satisfaction; make the labelling louder.

* *For:* no behaviour change; nothing pauses that did not pause before.
* *Against:* the defect is the mechanism, not the label. A gate the model's default behaviour
  satisfies is not a gate, and M8 would build on it.

## Recommendation

**(b).** It is the only option that keeps faith with both principles in tension: the author's
material is authoritative (a stated *must* is not quietly demoted), and a model never decides a
gate by default (an affirmative, schema-validated, labelled attestation is a bounded task; silence
is not). Option (a) remains the fallback if per-requirement attestation proves unreliable on the
default models — measure it in M8 against the M7 brief before building further on the gate.

Interim, already shipped and deliberately short of the decision: the labelling of part 2 (commit
event, pages, CLI, exports) and the M7-21 compiler-prompt tightening, neither of which changes
what satisfies the gate.

## Consequences

* Accepting (b) changes `review_loop.py` (attestation set instead of mention-absence),
  the audit prompts and `FINDINGS_SCHEMA` (per-requirement verdicts), `config.py` (the opt-out),
  and the M8 plan (a reliability measurement of attestation on the default models).
* Until acceptance, the coverage gate's behaviour is unchanged; the surfaces say so honestly.
* Whatever is decided, `evaluate_coverage`'s asymmetry stands: where a deterministic check
  exists, the check decides, and no audit verdict can overturn it.
