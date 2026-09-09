# ADR-0107 — The second LoadCoach consumer arrived; the client package is still declined

**Status:** Accepted (2026-09-07)
**Amends:** [ADR-0011](0011-shared-package-boundaries.md) — its `LoadCoachClient` rejection, its
sizing of IdeaPress's adapter, and its first "revisit when" trigger, which has fired and is
replaced here.
**Relates to:** [ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) (the
decision that created the second consumer), [ADR-0028](0028-prompt-pack-granularity.md) (the same
second-consumer trigger, for prompt tooling, which *did* fire into an extraction),
[ADR-0108](0108-the-snapshot-contracts-the-surface-and-goldens-contract-the-bodies.md) (what the
two consumers' contract tests actually rest on, and the condition that would change this answer),
[LoadCoach spec §21](../apps/loadcoach/spec.md) and the
[risk register](../architecture/risk-register.md), both of which still name the unfired trigger.
**Source:** The 2026-09-07 ADR gap review, finding 3.1 — a fired trigger whose ADR still reads as
if nothing happened.

## Context

ADR-0011 declined `LoadCoachClient` as a seventh shared package and named the condition that would
reopen it: "**A second consumer of the LoadCoach HTTP API appears outside IdeaPress** → create
`LoadCoachClient`, extracted from IdeaPress's adapter and from the OpenAPI document."

[ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) created that consumer
deliberately: PromptCadence reaches a model *only* through LoadCoach. The trigger has therefore
fired, and it fired ten months of code ago. The tree today:

| | IdeaPress | PromptCadence |
|---|---|---|
| module | `infrastructure/backends/loadcoach.py` | `infrastructure/loadcoach.py` |
| size | **1 422 lines** | **1 291 lines** |
| shape | an implementation of IdeaPress's own `InferencePort` — `StageRequest` in, `StageResult` and `StageEvent` out | a LoadCoach-shaped client — `GenerateRequest` in, `GenerationResponse` out, eleven public methods |
| vendored | `tests/contract/loadcoach_openapi_v1.json` | `tests/contract/loadcoach_openapi.json` |

ADR-0011's own rejection reasoning is false in both of its premises. Line 44 describes "a thin
`LoadCoachBackend` adapter (~200 lines)" — off by a factor of seven. The alternatives section
rejects "a package whose only job is to wrap eight HTTP calls" — PromptCadence's client exposes
eleven (`version`, `system_status`, `models`, `task_profiles`, `task_profile`, `route`, `generate`,
`list_jobs`, `job`, `cancel_job`, `find_job`) plus a strict parser, a token-count reader and an
error map. Both applications additionally vendor a ~62 KB copy of LoadCoach's OpenAPI document into
`tests/contract/`, and **the two copies have already drifted from each other** — they are pinned to
different LoadCoach versions.

So the question is live and the record is out of date. What the record cannot do is stay silent:
`docs/README.md` still summarises ADR-0011 as "`LoadCoachClient` deferred", and a reader comparing
that line to the tree finds two clients and no explanation.

**What the two modules actually contain.** This is the part the trigger could not have anticipated.
Neither is a thin wrapper, and the thickness is in different places:

* IdeaPress's is mostly **not about LoadCoach**. `task_for` maps a stage to a task profile;
  `_body_for` decides whether an adapter pin travels and refuses an older wire that cannot carry
  one; `_refuse_an_unhonoured_adapter_pin` and `_pin_degradation` implement
  [ADR-0040](0040-routing-backend-owns-model-choice.md) rule 5 and
  [ADR-0083](0083-an-adapter-pin-is-configured-on-by-being-configured.md); `_reported_degradations`
  and `_routing_degradations` translate a routing answer into IdeaPress's own degradation
  vocabulary; `_to_result` builds a `StageResult`. Extract the HTTP and what remains is still
  most of the file.
* PromptCadence's is mostly **about being strict**. `parse_generation` refuses a body that does not
  say what it claims rather than filling in defaults; `token_count_from_wire` reads a count that
  may be a number, a `null` or the string `"unsupported"` (see
  [ADR-0105](0105-a-shipped-usage-object-keeps-null-until-api-v2.md)); `LOADCOACH_CODE_MAP` and
  `map_error` turn LoadCoach's error vocabulary into PromptCadence's `ErrorCode`; and every call
  site above it binds a `TurnProvenance` that must name the model, the tier and the intent revision
  a turn actually ran under.

The overlap is real but shallow: the request body, the response envelope, the error shape, the
version check, and the SSE frame decoding. Perhaps three hundred lines, spread across two files
whose other twenty-three hundred lines answer different questions.

## Decision

**No shared `LoadCoachClient` package is created now. The trigger fired, was evaluated, and the
answer is recorded here rather than left as a contradiction between ADR-0011 and the tree.**

1. **The two clients stay where they are.** Each is its application's own boundary code, owned by
   the application that reads it, versioned with it.
2. **ADR-0011's rejection reasoning is retired, not reused.** "One consumer" and "eight HTTP calls"
   were true when written and are not now. What survives is ADR-0011's rule 4 — nothing is
   extracted with fewer than two real consumers — and the reason this record is not the extraction:
   two consumers exist, and *neither is thin*, which is a different objection from the original
   one and is the one that decides today.
3. **The reason is divergence plus cost, stated plainly.** The two modules diverge in what they
   bind — stage bindings, adapter pins and a degradation vocabulary on one side; turn provenance, a
   strict parser and an error map on the other — so a package could carry only the shallow overlap.
   And the cost of a package is not its code: it is a **third API surface to version**, released to
   PyPI, pinned by two applications, that must move whenever LoadCoach's `/api/v1` grows a field.
   Two applications already track that surface directly, each at its own pace; a package makes them
   track it through an intermediary that can lag both.
4. **The extraction stays a candidate, with a new trigger** (below), so the next reader inherits a
   decision instead of a discrepancy.
5. **`docs/README.md`'s one-line summary is corrected** to say the trigger fired and extraction was
   declined, because a reader who never opens ADR-0011 should not be told the question is still
   waiting to be asked.

## Alternatives considered

* **Extract `LoadCoachClient` now**, as ADR-0011's trigger literally instructs. The strongest
  argument for it is duplication that has already caused harm once: two vendored OpenAPI copies
  that have drifted, and two independent readings of the same response bodies — which is exactly
  the prior projects' three-Ollama-clients failure that ADR-0011 exists to prevent. Rejected on
  what the package could actually hold: about three hundred lines of overlap out of 2 713, and both
  callers would keep almost everything they have. A shared package that removes 11 % of two files
  while adding a release cadence, a version pin and a compatibility matrix is not a saving.
* **Extract only the wire types** — request body, response envelope, error envelope, SSE frame —
  and leave the clients. Genuinely tempting, and it is the half that is actually identical.
  Rejected because that package already exists: those shapes are LoadCoach's `/api/v1` contract,
  and the artifact that carries them is the OpenAPI document plus the captured goldens
  ([ADR-0108](0108-the-snapshot-contracts-the-surface-and-goldens-contract-the-bodies.md)). A
  Python package restating them would be a fourth place for the same shapes to be written down and
  the only one with a version number of its own.
* **Have PromptCadence depend on IdeaPress's adapter.** Refused outright — applications never
  import applications ([ADR-0001](0001-application-and-package-separation.md)), not even under
  `TYPE_CHECKING`. Recorded only because "the code already exists over there" is the reasoning that
  produces that violation.
* **Have LoadCoach publish a generated client** from its own OpenAPI document. Attractive, and it
  is what the final architecture audit imagined when it wrote "no `LoadCoachClient` is required".
  Rejected today for the reason ADR-0108 records: 32 of 49 JSON responses in LoadCoach's committed
  document describe no body at all, so a generated client would type every response as an untyped
  object and neither consumer could use it. This is the condition that would most plausibly change
  the answer, and it is named in the trigger below.
* **Deduplicate only the vendored snapshot** — one copy, shared. Rejected: it is a test fixture,
  the two applications pin different LoadCoach versions on purpose, and a shared fixture would
  force them to upgrade together, which is the coupling the standalone guarantee forbids.

## Consequences

* Two clients continue to exist, and a LoadCoach `/api/v1` addition is read twice, by two teams of
  one. That is accepted; the mitigation is that each side's contract tests run against captured
  goldens from a real LoadCoach, so a misreading fails in the consumer that made it.
* The two vendored OpenAPI copies stay independent and will keep drifting from each other. That is
  correct rather than a defect — each pins the LoadCoach version its owner tests against — but it
  means neither file is evidence about the other application.
* ADR-0011's table, its rules 1–4 and its other two triggers are unaffected. Only the
  `LoadCoachClient` paragraph and the first trigger are superseded.
* If the extraction is ever done, it starts from PromptCadence's client rather than IdeaPress's —
  the reverse of ADR-0011's instruction — because PromptCadence's is the one shaped like LoadCoach
  rather than like its own caller. That is a finding, and it is why the original trigger's
  "extracted from IdeaPress's adapter" wording does not survive into the new one.
* A third application, if one comes, inherits a decision it can read rather than a trigger it has
  to interpret.

## Revisit when

Either of these, whichever comes first:

* **A third consumer of LoadCoach's HTTP API appears.** Three independent readings of one contract
  is the prior projects' failure at full size, and the overlap argument that decides this record
  changes sign: three hundred lines shared three ways, against a divergence that no longer looks
  like an exception.
* **LoadCoach's OpenAPI document carries typed response bodies.** At that point a *generated*
  client is available for nothing, both consumers can adopt it under their own types, and the
  package this record declines stops being a hand-written third surface and becomes a build
  artifact. See [ADR-0108](0108-the-snapshot-contracts-the-surface-and-goldens-contract-the-bodies.md).
