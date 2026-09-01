# ADR-0043 — Grounding is verified, not assumed

**Status:** Accepted (2026-09-01).
**Extends:** [IdeaPress Workflows §2](../apps/ideapress/workflows.md),
[IdeaPress Spec §11](../apps/ideapress/spec.md).
**Relates to:** [ADR-0039](0039-audit-gated-blocking-requirements.md),
[ADR-0042](0042-a-check-may-not-restate-its-requirement.md), risk T1, risk C2.

## Context

M8's demonstration ran an independent brief with **no source documents attached**. The brief asked
that claims be grounded in evidence a council would accept. The model complied by inventing it:

* "averaging 150 daily footfall, 40 weekly workshop attendees, and 200 monthly digital resource
  check-outs";
* "a comprehensive 2023 local service mapping audit";
* "neighboring sites that operate at 85% capacity".

None of it exists. There was nothing for it to come from. Every gate passed:

```
validation.completed : 23 checks passed
audit.completed      : audit_fast: no findings (score 1.00)
critique.completed   : leave_it_alone
coverage.completed   : 2/2 requirements satisfied
unit.committed       : version 1 committed
```

Two distinct failures are stacked here.

**The first is that a requirement demanding evidence was accepted against a project with no
evidence.** Nothing in the compile, the plan, or the gate observed that R-006 asked for grounding
and the project had no sources. The requirement was compiled, assigned to five units, and reported
satisfied — a claim the system had no means to evaluate and never said so.

**The second is that nothing verified the claims.** `fact_check` exists in the stage vocabulary
(workflows §2) and is **not part of the draft loop**, so it never ran. Even had it run, with no
sources it could have verified nothing.

The product's claim is that Python owns control flow and the gates catch what a model gets wrong.
Here the gates reported full coverage of a grounding requirement while the content was fabricated.
A 1.0 whose headline is gated, provenance-tracked output cannot ship in that state.

## Decision

Grounding is treated as a property the system must be able to *check*, not one it may assume. Two
mechanisms, deliberately layered — the deterministic one refuses early and cheaply, the model one
covers what it cannot see.

### 1. A grounding requirement with no source is refused at plan time

A compiled requirement is **grounding-demanding** when its text asks for evidence — the compiler
marks it, and the marking is a field on the requirement, not a regex over prose at gate time.

When a project has **no sources attached** and the compilation produces a grounding-demanding
blocking requirement, `plan build` **refuses**, names the requirement, and states the remedy:

```
R-006 asks for claims to be grounded in evidence, and this project has no sources attached.
Attach a source (`ideapress project source add`) or rewrite the brief so the requirement is not
about evidence.
```

This is a `CONFIGURATION`-shaped refusal in the family the codebase already uses — `INSECURE_BINDING`,
`max_concurrent_stages`, an unbound stage — where a value that would produce a system behaving
differently from how the operator believes is refused up front rather than worked around.

It is deterministic, costs no model call, and closes the case observed. It does **not** detect
fabrication where sources *do* exist.

### 2. `fact_check` runs inside the draft loop, against the attached sources

`fact_check` moves from a stage that exists in the vocabulary to a stage the unit loop runs, after
`audit` and before `commit`, for any unit carrying a grounding-demanding requirement:

* it is given the unit's text and the project's sources, and asked which claims are **not
  supported** by them;
* an unsupported claim is an audit finding of severity `major`, carried into the same review loop
  as any other finding, so the existing revise/re-audit machinery handles it with no new control
  flow;
* it is **never** a test oracle for anything else, and it cannot pass a requirement — it can only
  add findings. A model still does not decide the gate (risk T1).

Where a project has sources, this catches claims the sources do not support. Where it does not,
mechanism 1 has already refused.

### 3. Coverage distinguishes what it could not check

`satisfied` and `satisfied against no source` are different states and are reported differently, in
the coverage table and in every export. A requirement satisfied by an audit that had nothing to
check against says so.

## Consequences

* **`fact_check` is in the 1.0 release.** It adds one model call per unit carrying a
  grounding-demanding requirement. That is a real cost in wall-clock time on a single GPU, and it
  is accepted deliberately: a slower system that checks is worth more than a fast one that does
  not.
* A brief that asks for evidence and attaches none now **fails to plan**. This is a behaviour
  change for existing projects and is the point of the ADR. The refusal names the remedy.
* **There is no suite-level consequence** — corrected during implementation. An earlier draft of
  this ADR said `SetSpec` payloads carrying requirement coverage would gain the distinction. **No
  such payload exists**: requirement coverage never crosses an application boundary, because
  IdeaPress's export format is an application-owned document schema (ADR-0035) and SetSpec carries
  no coverage model. The three states live in `RequirementCoverage` and in IdeaPress's own three
  exporters, and nothing outside IdeaPress reads them. The claim is left here struck rather than
  deleted, because an ADR that quietly loses a consequence is worse than one that records being
  wrong about it.
* ADR-0039's attestation obligation is unchanged, but its scope grows — more requirements are
  audit-gated after ADR-0042, and this ADR adds a second model-run stage. The P7-B measurement
  should be re-run once both land.

## Alternatives considered

**Refusal only (mechanism 1), no `fact_check`.** Cheapest, and closes the observed case. Rejected
as insufficient: it says nothing about a project that *has* sources and cites them wrongly, which
is the more common real failure and the one a user would least expect the system to miss.

**`fact_check` only, no refusal.** Rejected: with no sources, `fact_check` has nothing to check
against and would either pass everything or fail everything. A deterministic refusal is strictly
better than a model call that cannot succeed.

**Report rather than refuse** — let the plan proceed with a warning. Rejected: the M8 evidence is
that a warning in a log is not read, and the artefact that *is* read reported full satisfaction.
The system must not offer a green report it cannot justify.
