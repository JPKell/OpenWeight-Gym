# ADR-0041 — A caller's output schema does not travel through a router; the caller still owns it

**Status:** Accepted (2026-08-31)
**Extends:** [IdeaPress Workflows §6.2](../apps/ideapress/workflows.md),
[IdeaPress Spec §11](../apps/ideapress/spec.md) (contract 5).
**Relates to:** [ADR-0039](0039-audit-gated-blocking-requirements.md) (attestation, never silence),
[ADR-0035](0035-application-owned-document-schemas.md) (an application owns its own document
shapes), [ADR-0040](0040-routing-backend-owns-model-choice.md), risk I2.

## Context

IdeaPress's structured stages ask for a shape. `ResponseFormat(kind="json_schema", schema=…)`
carries the JSON Schema the stage needs, and the standalone adapters hand it to the provider.

**LoadCoach has no field for it.** `GenerateBody.response_format` is a bare string —
`text | json | json_schema` — and the schema applied is the *task profile's*
`execution.json_schema_ref`, resolved server-side
([LoadCoach api.md §4](../apps/loadcoach/api.md)). `services/execution.py::_response_format` makes
the consequence exact:

```python
if kind == "json_schema" and schema is not None:   # `schema` is the profile's, never the caller's
    return ResponseFormat(kind=JSON_SCHEMA, schema=dict(schema))
if kind == "json":
    return ResponseFormat(kind=JSON)
return None
```

So a caller asking for `json_schema` gets **the profile's schema, or nothing at all** — and for the
three profiles [Workflows §6](../apps/ideapress/workflows.md)'s task map routes structured stages
through, "the profile's schema" is actively wrong:

| Stage | Profile | The profile enforces | Against IdeaPress's schema |
|---|---|---|---|
| `audit_fast`, `audit_deep` | `content.review` | `content_review_findings.json`: requires `findings` + `summary`; finding items require `requirement`/`status`/`explanation`; `status` ∈ `met`/`partially_met`/`not_met`; `additionalProperties: false` | Requires `findings` + `requirements_assessment`; finding items require `category`/`severity`/`problem_text`; verdicts ∈ `met`/`not_met`/**`cannot_judge`** |
| `requirements` | `structured.extract` | `{data, confidence}` | A `requirements` array of compiled requirements with checks |
| `fact_check` | `content.fact_check` | `fact_check_findings.json` | IdeaPress's claim-verdict shape |

The `content.review` row is not a mismatch to paper over. Its `additionalProperties: false` makes
`requirements_assessment` **structurally impossible**, and its `status` enum has no
`cannot_judge` — so [ADR-0039](0039-audit-gated-blocking-requirements.md)'s attestation mechanism,
accepted three weeks ago and the thing standing between the commit gate and a model's silence,
cannot be expressed at all through this path. A model schema-forced into that shape returns no
attestation for any requirement, every check-less blocking requirement stays unsatisfied, and every
unit pauses. The failure is at least loud. The quieter one is `structured.extract` returning
`{"data": {...}}` where the compiler expected `{"requirements": [...]}`.

Neither side is at fault. LoadCoach's profile schemas are **correct for LoadCoach** — they are what
lets it validate, retry correctively and score a model's structured-output reliability across
callers it knows nothing about. They are simply not IdeaPress's contract, and there is no field in
which IdeaPress's contract could be sent.

## Decision

**Through a routing backend, IdeaPress asks for JSON and enforces its own shape itself.**

1. **Never `json_schema`.** The adapter maps `ResponseFormat(kind="json_schema" | "json")` onto
   LoadCoach's `response_format = "json"`, which `_response_format` honours unconditionally,
   independently of what the profile declares. Valid JSON is guaranteed; the *shape* is not, and
   nothing claims it is.

2. **The degradation is recorded, per attempt.** `structured_output_unavailable: LoadCoach applies
   the task profile's schema, not the caller's; the answer was parsed and validated by IdeaPress`.
   This is [Workflows §6.2](../apps/ideapress/workflows.md)'s existing rule — *request text plus a
   parsing step, record the degradation, never pretend a schema was enforced* — applied to a
   backend that enforces **a** schema rather than none. A backend enforcing the wrong schema is
   further from the truth than one enforcing none, so it gets the same treatment, not a softer one.

3. **`LoadCoachBackend.capabilities()` reports `structured_output=False`, `json_mode=True`.** That
   is the honest answer to "can this backend enforce the shape I asked for?", and it routes the
   stage runner through the parsing path that already exists rather than a new one.

4. **IdeaPress's validation is unchanged and remains the authority.** `parse_findings`, the
   requirement compiler's validation and the deterministic validators run identically in every
   mode. This is what keeps [Spec §20 AC2](../apps/ideapress/spec.md) true: the parity test asserts
   identical structure across four adapters precisely because the shape is enforced above the port,
   not below it.

## Alternatives considered

* **Send `json_schema` and let the profile's schema apply.** Rejected: it silently breaks ADR-0039
  and the requirement compiler, and it makes an application's output contract depend on another
  application's configuration file.
* **Add a per-request schema field to LoadCoach's API.** The right long-term answer and a real
  option — LoadCoach's v1 is additive, so a `json_schema` document field could be added compatibly.
  Rejected *for M8*: it changes a published 1.0 application's public contract and its
  structured-output validation and corrective-retry paths, to remove a degradation that is already
  recorded honestly. Recorded as a post-1.0 candidate, not smuggled into a hardening phase.
* **Ship IdeaPress-shaped profiles into LoadCoach's config.** Rejected: it makes IdeaPress's
  correctness depend on the operator having edited another application's `task_profiles.toml`, and
  the standalone guarantee ([Gold Standards §2](../standards/gold-standards.md)) means that file
  may not exist at all.
* **Give up the audits in LoadCoach mode.** Rejected: parity across backends is AC2.

## Consequences

* One measurable behaviour difference between modes, named on every affected attempt rather than
  discovered: in LoadCoach mode the model is asked for valid JSON and IdeaPress checks the shape;
  in standalone mode the provider is asked to enforce the shape as well. Output is equivalent
  because IdeaPress validated it either way.
* ADR-0039's attestation works identically through LoadCoach, because the schema that reaches the
  model is IdeaPress's prompt-level instruction and IdeaPress's parser, neither of which LoadCoach
  touches — which is the same property [Spec §11](../apps/ideapress/spec.md) contract 5 rests on
  for `prompt_sha256`.
* A profile-schema change on LoadCoach's side cannot break an IdeaPress stage, in either
  direction. The cross-application coupling this closes is the same one the `code.review` →
  `content.review` correction closed for routing.
* If LoadCoach later accepts a caller-supplied schema, this record is superseded rather than
  edited, and the degradation disappears on its own.
