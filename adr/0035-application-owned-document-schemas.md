# ADR-0035 — Application-owned document schemas, and `benchmark.export`

**Status:** Accepted (2026-08-28)
**Amends:** [ADR-0025 §1](0025-envelope-boundaries.md) (what may carry an envelope), [FreeWeight spec §7.3](../apps/freeweight/spec.md), [FreeWeight API §5](../apps/freeweight/api.md).
**Related:** [ADR-0009](0009-setspec-schema-strategy.md) (SetSpec versioning), [ADR-0022](0022-capability-evidence-record-contract.md) (the cross-application contract), [API and Contract Standards §7](../standards/api-and-contract-standards.md).

## Context

[ADR-0025 §1](0025-envelope-boundaries.md) drew a clean line and stated the test in one sentence: a
body is SetSpec-enveloped **iff** its `schema` name appears in `SUPPORTED_SCHEMAS` and the endpoint
documents it as a SetSpec payload. *"There is no third case."*

FreeWeight Phase 10 shipped a third case. `GET /api/v1/results/export` and `freeweight results
export` emit an envelope whose `schema` is `benchmark.export`, which:

* is **not** in `setspec.envelope.SUPPORTED_SCHEMAS` — that mapping holds eight names, and this is
  not one of them;
* is defined in **no** SetSpec module, so nothing validates it but FreeWeight's own reader;
* sits in the **`benchmark.*` namespace**, which SetSpec owns — every one of the six benchmark
  schemas in `SUPPORTED_SCHEMAS` is `benchmark.something`.

The third point is the serious one. An application minting a name in the shared package's namespace
is a collision waiting to happen, and the collision would be silent: the day SetSpec defines its own
`benchmark.export`, every document FreeWeight has ever written becomes a lie about which schema it
follows, and no version number distinguishes them because the *name* is the identity.

### Why the endpoint could not simply use an existing schema

This was not laziness, and the reasons are worth recording because they are the argument for the
decision:

* **`benchmark.run_summary` cannot name its own metrics.** Its `aggregate_metrics` field is a
  sequence of `MetricValueFields`, which declares `value`, `unit`, `aggregation`,
  `higher_is_better`, `sample_count` and `dispersion` — and nothing saying *which metric this is*.
  A document of run summaries alone is a list of numbers a consumer cannot attribute, chart or
  compare. (That upstream gap is worth closing on its own merits and is tracked separately; closing
  it does not remove the need for a container.)
* **No SetSpec schema has a slot for raw samples**, and `include_samples=true` is a documented
  parameter of this endpoint.
* **An export is a *selection*, not a measurement.** `scope=run|model|suite|comparison|all`, with
  `include_samples` and `include_prompts`, plus a `complete` flag. Its shape is FreeWeight's query
  model, not a fact about a model's behaviour.

And it is unambiguously a **document** by ADR-0025's own test — a user downloads it, keeps it, moves
it to another machine and opens it in a year — so it must be enveloped. The rule and the reality
disagree, and the rule is the thing that is wrong.

## Decision

### 1. An application may mint document schemas in its own namespace, and only there

| Namespace | Owner | May be minted by |
|---|---|---|
| `model.*`, `machine.*`, `benchmark.*`, `capability.*` | SetSpec | SetSpec only |
| `freeweight.*` | FreeWeight | FreeWeight only |
| `loadcoach.*` | LoadCoach | LoadCoach only |
| `ideapress.*` | IdeaPress | IdeaPress only |

SetSpec never defines a name in an application namespace. No application defines a name in a shared
one, and no application defines a name in *another* application's.

### 2. ADR-0025 §1's test is amended

> A body is SetSpec-enveloped **iff** its `schema` name appears in `SUPPORTED_SCHEMAS` **or** in the
> producing application's own namespace, and the endpoint documents it as a SetSpec payload.

Everything else about §1 stands unchanged — an ordinary API request or response body is still
versioned by the path and documented by OpenAPI, and an error body is still unwrapped.

### 3. `benchmark.export` becomes `freeweight.export`, at `1.0`

The name moves out of SetSpec's namespace, with **no compatibility path for the old one**. The suite
is pre-1.0, no consumer outside it reads these documents, and results produced during development
are not being retained — so a reader that accepted both names would be carrying a branch for
documents nobody has. After 1.0 the same rename would need one; that is the argument for doing it
now rather than the argument for a compatibility window.

### 4. An application-owned document embeds SetSpec payloads verbatim

Where a shared schema exists for part of the content, the application document **contains** it
rather than re-describing it. `freeweight.export` carries a real `benchmark.run_summary` payload per
run under `summary`, built and validated through `BenchmarkRunSummaryOut` — so the runtime-profile
hash check, the timing-order check and the measurement serializers all run over what FreeWeight
exports, and a hand-built dictionary cannot drift at the next SetSpec minor.

**An application namespace is for the container. It is never a place to re-describe a shared
payload**, and a `freeweight.run_summary` would be a defect under this ADR, not an option.

### 5. An application-owned schema is not a cross-application contract

A consumer needing FreeWeight's data across an application boundary uses `capability.evidence` and
`benchmark.evidence_bundle` ([ADR-0022](0022-capability-evidence-record-contract.md)) — that is what
those exist for, and [API §10](../apps/freeweight/api.md) names them as LoadCoach's integration
point.

If a second application ever genuinely needs to read `freeweight.export`, **that is the trigger to
promote it into SetSpec** — and the promotion mints a *new* name in the shared namespace with its
own version, rather than renaming one in place. A document already written keeps meaning what it
meant.

### 6. The rule is testable, and is tested

A contract test asserts that every `schema` name FreeWeight emits is either in
`SUPPORTED_SCHEMAS` or begins with `freeweight.`. A namespace rule that is only prose is a namespace
rule that gets broken by the next endpoint — this one was.

## Alternatives considered

**Add `benchmark.export` to SetSpec.** The tidy answer, and wrong on ownership. SetSpec would have
to version FreeWeight's query model: `scope`, `include_samples`, `include_prompts` and the
`complete` flag are all FreeWeight's, and adding a scope value to one endpoint would become a
suite-wide schema release that LoadCoach and IdeaPress must both accept. SetSpec's payloads describe
*measurements*; this describes *a selection of them*, which is a different kind of thing.

**Emit `benchmark.run_summary` per run and nothing else.** No new schema, no namespace question —
and a document whose metrics cannot be told apart, plus no home for the samples the endpoint
documents. It fails the round-trip test for a reason that is not FreeWeight's to fix.

**Emit no envelope; make the export a plain API body.** Then it is versioned by `/api/v1` and needs
no schema at all. Rejected because it is precisely the case ADR-0025 drew its boundary *for*: a file
that outlives the request, read by something that never saw the request.

**Keep the name and add it to `SUPPORTED_SCHEMAS` from FreeWeight at import time.** Rejected
outright — a shared registry an application can mutate is not a registry, and the failure mode is
two applications registering the same name with different shapes.

**Keep `benchmark.export` and document the exception.** The cheapest option today. Rejected because
the cost is not paid today: it is paid the first time SetSpec wants the name, and by then documents
exist in users' directories that nothing can disambiguate.

## Consequences

* **Cost.** A rename in FreeWeight's export module, its contract goldens, the CLI help and two
  documents. No compatibility branch, and no reader for documents written under the old name.
* **Enables.** LoadCoach and IdeaPress get a rule instead of a precedent, before either has written
  its first export. This ADR is cheap now precisely because it is being written at 0.x.
* **Forecloses.** Passing `freeweight.export` between applications as a contract. That is
  intentional: the evidence bundle is the contract, and an export that quietly became one would
  couple LoadCoach to FreeWeight's query parameters.
* **Settled since.** `MetricValueFields` now carries `metric_key`, so an embedded
  `benchmark.run_summary` is attributable on its own. That removes one of the three reasons this
  document could not simply be a SetSpec payload; the other two — no slot for raw samples, and a
  shape that follows FreeWeight's query model — stand, which is why the decision does not change.

## Revisit when

* A second application needs to read another's document — the promotion trigger in §5.
* SetSpec gains a container payload with a samples slot and a keyed metrics sequence, at which point
  `freeweight.export` may have nothing left that is FreeWeight's own.
* A user-visible artifact needs to be readable by a tool outside this suite, which would make the
  namespace question a publishing question rather than an internal one.
