# Architecture Decision Records

Every significant architectural decision in the suite is recorded here. An ADR is written **before**
the decision is implemented, and it is not edited to hide a change of mind — it is superseded by a
new ADR that references it.

## Format

Every ADR contains, in this order:

```text
Status          Proposed | Accepted | Superseded by ADR-XXXX | Deprecated
Context         The forces, constraints and evidence
Decision        What we will do, stated unambiguously
Alternatives considered   What else was evaluated, and why it lost
Consequences    What this costs, what it enables, what it forecloses
Revisit when    The concrete trigger that would reopen the decision
```

A decision without a "revisit when" trigger is a decision nobody can safely revisit.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-application-and-package-separation.md) | Application and package separation | Accepted |
| [0002](0002-web-framework.md) | Web framework: FastAPI | Accepted |
| [0003](0003-sync-vs-async-strategy.md) | Sync core, async edge | Accepted |
| [0004](0004-sse-vs-websockets.md) | Server-Sent Events for streaming | Accepted |
| [0005](0005-database-strategy.md) | SQLAlchemy 2.0 + Alembic | Accepted |
| [0006](0006-sqlite-and-postgresql-roles.md) | SQLite default, PostgreSQL supported | Accepted |
| [0007](0007-provider-abstraction.md) | Provider abstraction and Ollama first | Accepted |
| [0008](0008-canonical-model-identity.md) | Canonical model identity | Accepted |
| [0009](0009-setspec-schema-strategy.md) | SetSpec schema and versioning strategy | Accepted |
| [0010](0010-queue-implementation.md) | Database-backed queue, no broker | Accepted |
| [0011](0011-shared-package-boundaries.md) | Shared package boundaries and extraction timing | Accepted |
| [0012](0012-prompt-storage-format.md) | Prompts as versioned JSON records | Accepted |
| [0013](0013-api-versioning.md) | API versioning | Accepted |
| [0014](0014-authentication-strategy.md) | Authentication strategy | Accepted |
| [0015](0015-repository-and-distribution-model.md) | Repository and distribution model | Accepted |
| [0016](0016-unavailable-is-not-zero.md) | Unavailable is not zero | Accepted |
| [0017](0017-benchmark-confidence-and-freshness.md) | Benchmark confidence and freshness | Accepted |
| [0018](0018-external-benchmark-isolation.md) | External benchmark isolation and sandboxing | Accepted |
| [0019](0019-python-baseline-and-config-format.md) | Python baseline and configuration format | Accepted |
| [0020](0020-ui-rendering-strategy.md) | UI rendering strategy | Accepted |
| [0021](0021-telemetry-collection-strategy.md) | Telemetry collection strategy | Accepted |
| [0022](0022-capability-evidence-record-contract.md) | Capability evidence record contract | Accepted |
| [0023](0023-runtime-profile-resolution.md) | Runtime profile resolution and served context | Accepted |
| [0024](0024-canonical-id-and-model-references.md) | Canonical ID format and model references in URLs | Accepted |
| [0025](0025-envelope-boundaries.md) | Envelope boundaries: what carries a SetSpec envelope | Accepted |
| [0026](0026-local-http-hardening.md) | Local HTTP hardening: Host validation, CSRF and outbound fetch | Accepted |
| [0027](0027-multi-gpu-semantics.md) | Multi-GPU semantics | Accepted |
| [0028](0028-prompt-pack-granularity.md) | Prompt attribution granularity and shared prompt tooling | Accepted |
| [0029](0029-queue-mechanics.md) | Queue mechanics: ageing, attempts, admission states and leases | Accepted |
| [0030](0030-model-cost-and-pricing.md) | Model cost: prices are dated observations, not model properties | Accepted |
| [0031](0031-user-defined-goal-benchmarks.md) | User-defined goal benchmarks and the calibrated-judge instrument | Accepted |
| [0032](0032-judge-validity-and-user-capability-namespace.md) | Judge validity in confidence, and the `user.*` capability namespace | Accepted |
| [0033](0033-benchmark-interaction-protocol.md) | Benchmark interactions, the two scorer protocols, and enforced capability requirements | Accepted |
| [0034](0034-run-level-derived-metrics.md) | Run-level derived metrics: the second benchmark seam | Accepted |
| [0035](0035-application-owned-document-schemas.md) | Application-owned document schemas, and `benchmark.export` | Accepted |
| [0036](0036-queue-recovery-transitions.md) | Queue state machine: recovery edges for every lease-holding state | Accepted |
| [0037](0037-production-evidence-never-raises-capability-scores.md) | Production evidence never raises capability scores; upward adaptation is post-1.0 exploration routing | Accepted |
| [0038](0038-one-model-at-a-time-per-gpu.md) | One model at a time per GPU: fit with room for context, or wait | Accepted |
| [0039](0039-audit-gated-blocking-requirements.md) | A model's silence must not settle a blocking gate | Accepted |
| [0040](0040-routing-backend-owns-model-choice.md) | A routing backend owns model choice and residency | Accepted |
| [0041](0041-caller-schemas-do-not-travel-through-a-router.md) | A caller's output schema does not travel through a router; the caller still owns it | Accepted |
| [0042](0042-a-check-may-not-restate-its-requirement.md) | A deterministic check may not be a restatement of its requirement | Accepted |
| [0043](0043-grounding-is-verified-not-assumed.md) | Grounding is verified, not assumed | Accepted |
| [0044](0044-a-state-change-and-its-event-are-one-write.md) | A state change and the event announcing it are one write | Accepted |
| [0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) | PromptCadence is a fourth application, and it reaches a model only through LoadCoach | Accepted |
| [0046](0046-data-classification-is-ordered-and-defaults-closed.md) | Data classification is ordered, caller-declared, and defaults to the most restrictive | Accepted |
| [0047](0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md) | A tier is configuration over a task profile, and a model's guess never sizes its own budget | Accepted |
| [0048](0048-the-bypass-removes-planning-never-governance.md) | The bypass removes planning; it never removes governance | Accepted |
| [0049](0049-approval-is-a-mode-with-its-own-scope.md) | Approval is a mode with its own scope, and silence never grants it | Accepted |
| [0050](0050-a-package-may-ship-tables-never-a-migration-history.md) | A shared package may ship tables; it may never own a migration history | Accepted |
| [0051](0051-plans-stay-internal-and-one-payload-travels.md) | A plan never leaves PromptCadence; the egress decision is the one shape that travels | Accepted |
| [0052](0052-compaction-is-a-view-and-the-package-plans-it-only.md) | Compaction is a view, and the package that plans a summary never calls a model | Accepted |
| [0053](0053-a-refused-tool-call-is-a-result-not-an-exception.md) | Tools are registered in code, refused in order, and a refusal is a result | Accepted |
| [0054](0054-commissioner-records-egress-it-does-not-enforce-it.md) | Commissioner renders and records an egress verdict; enforcing it is the caller's | Accepted |
| [0055](0055-loadcoach-registers-providers-by-name-and-kind.md) | LoadCoach registers providers by name and kind, into one tagged registry | Accepted |
| [0056](0056-every-turn-executes-under-one-execution-intent.md) | Every turn executes under exactly one immutable ExecutionIntent | Accepted |
| [0057](0057-the-explanation-is-materialized-and-the-rows-stay-authoritative.md) | The trajectory explanation is materialized; the rows stay the source of truth | Accepted |
| [0058](0058-the-execution-subject-gains-an-adapter-axis.md) | The execution subject gains an adapter axis, and an absent adapter changes nothing | Accepted |
| [0059](0059-adapter-evidence-is-measured-never-inherited.md) | Adapter evidence is measured, never inherited from its base | Accepted |
| [0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md) | Adapter selection lives in the subject; adapter serving mode lives in the runtime profile | Accepted |
| [0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md) | The adapter registry is an operator's directory and a reviewed manifest, not a service | Accepted |
| [0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) | llama.cpp serves adapters, through a process the suite supervises | Accepted |
| [0063](0063-one-adapter-at-a-time.md) | One adapter at a time, at a fixed scale | Accepted |
| [0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) | Adapters are selected through the capability vocabulary; there is no tag channel | Accepted |
| [0065](0065-an-adapter-is-classified-and-local-only.md) | An adapter is a distillate of its training data, and it does not leave the machine | Accepted |
| [0066](0066-residency-is-two-level.md) | Residency is two-level: the base is the expensive switch, the adapter is free | Accepted |
| [0067](0067-reliability-keys-on-the-subject-not-the-base.md) | Reliability and the breaker key on the subject, never on the base | Accepted |
| [0068](0068-a-post-freeze-minor-is-a-sibling-class.md) | A post-freeze minor is a sibling class, and a bare name keeps its version | Accepted |
| [0069](0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md) | A partial price accumulates as a floor, and a money ceiling chooses whether an unknown counts against it | Accepted |
| [0070](0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md) | An absent token class is zero only where the protocol cannot bill it | Accepted |
| [0071](0071-modelrack-persists-artifact-digests-in-a-json-file-the-application-names.md) | ModelRack persists artifact digests in a JSON file the application names | Accepted |
| [0072](0072-the-model-pricing-record-file.md) | The ModelPricing record file | Accepted |
| [0073](0073-egress-is-decided-on-configuration-before-availability.md) | Egress is decided on a tier's configuration, before its availability | Accepted |
| [0074](0074-adapter-enabled-serving-is-a-runtime-profile-field.md) | Adapter-enabled serving is a `RuntimeProfile` field, not a `provider_options` convention | Accepted |
| [0075](0075-a-request-carrying-tools-requires-tool-use-of-every-candidate.md) | A request carrying tools requires `tool_use` of every candidate | Accepted |

## Writing a new ADR

1. Copy the format above; number it sequentially.
2. Record real alternatives with real reasons — an ADR whose alternatives are strawmen is worthless.
3. Link it from this index and from the documents it governs.
4. Never delete an ADR. Supersede it.

## Amendments

ADRs 0022–0029 were added by the [final architecture audit](../reviews/final_architecture_audit.md)
on 2026-08-21, before implementation began. Where one of them narrows or corrects an earlier
decision, the earlier ADR carries an **Amended by** note at its head and the amending ADR states what
it changes. No earlier decision was reversed; each was found to be under-specified at a boundary
rather than wrong.

ADR-0033 was added on 2026-08-27, during FreeWeight Phase 7, to record a decision the phase forced
and the documentation did not contain: how a benchmark drives more than one provider call per
sample. It is the one ADR here written *after* the code rather than before it, which is a departure
from this directory's own rule; the code it describes was written first and the debt recorded, and
this ADR is that debt paid before Phases 8B and 13 build on the same seam.

ADRs 0031–0032 were added on 2026-08-26 to close the undelivered judge-scored capability
mapping in FreeWeight's benchmark catalogue (§6) and to state the oracle/instrument distinction the
testing standards implied but never wrote down. They amend ADR-0012, ADR-0017 and ADR-0022 and add
one root to the SetSpec capability vocabulary; they reverse nothing.

ADRs 0034–0035 were added on 2026-08-28, after FreeWeight Phase 10A, to close two decisions the
phases forced and recorded as debts rather than took quietly. ADR-0034 states the aggregation
seam that lets three suites compute run-level figures no scorer can see, and draws the boundary
that a derived metric is a function of one run. ADR-0035 gives applications a namespace of their
own for documents SetSpec does not describe, and amends ADR-0025 §1's "there is no third case"
to admit the case that turned up. Both are ADRs written after the code they describe, for the
same reason ADR-0033 was: the debt was recorded at the time and is paid here before the next
phase builds on either seam.

ADR-0039 was proposed and accepted on 2026-08-31, out of the M7 verification of IdeaPress
(finding M7-20): a blocking requirement with no deterministic check was satisfied by the audit's
*silence*, which let the model's default behaviour settle exactly the qualitative gates nothing
mechanical backstops. The accepted option (b) replaces silence with explicit, labelled,
per-requirement attestation — only a literal `met` satisfies, everything else (including an
invented verdict) degrades toward `cannot_judge` and pauses — with
`workflow.allow_audit_gated_requirements = false` as the wholly-mechanical opt-out.

ADR-0038 was added on 2026-08-31, during IdeaPress's M7 build, to close a gap Master Architecture
§5.2 left open: its inference-concurrency bullet gave a policy for FreeWeight and LoadCoach and
named IdeaPress nowhere, while IdeaPress's own default configuration binds two models to a card
that holds one. It states the machine-wide rule — two models contending for one GPU must both fit,
with room for their context, or the later one waits — names LoadCoach's admission as the compliant
reference implementation, gives IdeaPress the narrower serialise-and-unload obligation that needs
no queue, and records the estimator question (duplicate `estimate_vram` or extract it to
`modelrack`) with a recommendation rather than performing an extraction that touches a published
package and two 1.0 applications.

ADR-0040 was added on 2026-08-31, during IdeaPress's M8 build, before the LoadCoach adapter was
written. `InferenceGateway` resolves a `[models.stages]` binding for every request and unloads the
resident model before a switch — both correct for a backend IdeaPress drives, neither correct for
one that routes for itself. With the shipped defaults, `inference.mode = "loadcoach"` would have
pinned every request to the bound model and bypassed LoadCoach's profiles, evidence and admission
control while every stage still succeeded. It gives the port a `routes_internally` flag, makes
`[inference.loadcoach] honour_stage_bindings` the explicit opt-in spec §12's "unless overridden"
had never been given, and records an unhonoured pin as a degradation rather than a failure.

ADR-0041 was added on 2026-08-31, alongside ADR-0040 and for the same reason: the LoadCoach
adapter could not be written correctly without deciding it. LoadCoach's `response_format` is a bare
string and the schema applied is the *task profile's*, so a caller asking for `json_schema` gets a
shape it did not write. For `content.review` that shape forbids `requirements_assessment` and has
no `cannot_judge` verdict, which would make ADR-0039's attestation structurally impossible through
LoadCoach while every stage still ran. IdeaPress therefore asks for `json` and enforces its own
shape above the port, records the difference as a degradation on every affected attempt, and
reports `structured_output=False` honestly.

ADRs 0042 and 0043 were added on 2026-09-01, during IdeaPress's M8 build, from reading a real
run's output rather than from a failing test. ADR-0042 records that a `must_contain_any` check
built out of its own requirement's words is satisfied by quoting the requirement — the gate then
behaves exactly as ADR-0039 says it must and commits work its own critique called deficient.
ADR-0043 records that "grounded in the sources" was a requirement nothing verified: the compiler
wrote checks for the vocabulary of grounding, not for the grounding. Both narrow ADR-0039 without
reversing it; the asymmetry it establishes is unchanged, and what changed is which checks are
allowed to exist.

**ADRs 0045–0067 were written on 2026-09-02**, before any code, as the joint Phase 0 / LA0 of two
post-1.0 arcs: the [PromptCadence arc](../roadmap/promptcadence-roadmap.md) (a plan-approved,
tier-routed agent harness over LoadCoach, plus the four shared packages it justifies) and the
[Adapter arc](../roadmap/adapter-roadmap.md) (hot-swappable LoRA serving on a warm base via
llama.cpp). They are the suite's rule working as intended rather than a debt being paid: the
decisions were argued in the roadmaps, and these records exist so that no implementation phase has to
invent one. 0045–0057 expand the PromptCadence arc's D-1…D-13; 0058–0067 expand the Adapter arc's
A-1…A-10.

**ADR-0069 was added on 2026-09-02**, after LoadLedger Phase 1 had been built to its spec's
contract 2 as first written and the review of that build found the contract made money ceilings
unable to bind on any real adapter's output. It reverses that one line, before Phase 2 persists a
row under it, and records the operator's choice between a floor that may fire late and a strict
ceiling that never crosses. [ADR-0070](0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md) followed the same day and closes the question
0069 left open — which layer decides what an absent token class means. It is the adapter, per
response: zero where the protocol cannot bill the class, unavailable where it could and the
response did not say.

**ADR-0071 was added on 2026-09-03**, after ModelRack Phase 6 had been built with its artifact
digests held in memory to the letter of the spec's "no persistence" line, and the operator's
review of that build asked why a content hash that only content can invalidate should cost
forty-five seconds on every process start. It narrows spec §3 by one named exception — a
versioned, clearable `digests.json` beside the pid files ADR-0062 already placed in the
application's `state_dir` — and is the third record here written after the code rather than
before it.

**ADR-0072 was added on 2026-09-04**, after PromptCadence Phase 5 became the suite's first
consumer of `baseaicore.ModelPricing` and discovered that nothing anywhere said what a price list
looks like on disk. It is the fourth record here written after the code rather than before it, and
the reason it is an ADR rather than a line in one application's spec is
[ADR-0030](0030-model-cost-and-pricing.md)'s `pricing_hash`: that hash is only a join between a
stored usage and the price it was costed under if every application hashes the same object, and two
components that each invented a file would differ on exactly one question — whether an absent rate
means "not stated" or "free" — and produce the same hash for two different prices.

**ADR-0073 was added on 2026-09-04**, after PromptCadence Phase 6 found that spec §20 criterion 4
was unreachable as the code stood. Every remote tier reports `loadcoach_has_no_remote_provider`
until LC-E1 registers one, so a `confidential` trajectory aimed at one halted on the availability
check before any egress evaluation ran — no request left, but the refusal was not the queryable
`EgressDecision` the criterion demands, and the reason given was about the deployment rather than
about the data. It is the fifth record here written after the code rather than before it. The
reason it is an ADR and not a line in one application's spec is that it records an **ordering**:
criteria 4 and 5 are statements about *when* a refusal happens, a build that reordered the checks
would still pass every unit test of the policy itself, and the observable failure — a recorded
reason that silently changes the day infrastructure changes — appears only in a deployment nobody
has yet.

Three of them **amend earlier records additively, reversing nothing**.
[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) extends ADR-0008, ADR-0023 and
ADR-0024 with an optional adapter axis on the execution subject and an optional suffix on the
canonical string — a subject with no adapter is byte-for-byte what it is today.
[ADR-0051](0051-plans-stay-internal-and-one-payload-travels.md) adds `promptcadence.*` as a fourth
application namespace and `governance.*` as a SetSpec-owned root to ADR-0035's table.
[ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md) opens a narrow door in the
storage model — a package may ship mountable table definitions, and may still never own an engine, a
session, a migration history or the data. Together they amend
[Master Architecture](../architecture/master-architecture.md) §§1.1, 1.3, 1.5, 2, 3, 8, 10, 11 and
12 through the [ADR-0038](0038-one-model-at-a-time-per-gpu.md) mechanism.

ADR-0044 was added on 2026-09-01, during the same build, after CI failed a test a fast machine
could not. It is the second ADR here written after the code rather than before it. The decision it
records — that a state change and the event announcing it commit together — was already
implemented in LoadCoach and already explained in that component's own docstrings; what did not
exist was the rule, stated once, applying to both applications. IdeaPress had written the naive
order in three places independently, which is the argument for writing it down.

**ADR-0074 was added on 2026-09-04**, after ModelRack Phase 7 built adapter serving and found that
[ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md)'s "serving mode lives
in the runtime profile" had no mechanism behind it: `--lora` flags come from the provider's
registration set, `RuntimeProfile` is a separate object the caller passes, and nothing joined them.
So a base on an adapter-registered server and the same base on a clean one hash to the same profile
and would merge. It is the sixth record here written after the code rather than before it, and the
reason it is an ADR rather than a convention is what the alternatives section argues: the cheapest
correct fix — a `provider_options` key — is unvalidated and unspellable-wrong-safely, so a
misspelling would not fail but would mint a second hash meaning nothing, which is the same silent
merge from the other direction. The window in which this is cheap closes the first time a base is
benchmarked on a machine with an adapters directory configured, because evidence recorded without
the field is not separable afterwards.

**ADR-0075 was added on 2026-09-04**, when LoadCoach's `/generate` gained `tools` on its request
body (row G2). G1 had shown the cost of the gap from the model's side: told about no tools, a
model invents names out of its own vocabulary and every call is refused. The record exists because
closing that gap raised a question the wire alone does not answer — what a request carrying tools
does to *routing* when the task profile requires nothing — and the two easy answers, letting the
tools reach a provider that cannot use them and dropping them silently, are both failures a caller
cannot see until after a model was chosen.
