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
| [0039](0039-audit-gated-blocking-requirements.md) | A model's silence must not settle a blocking gate | Proposed |

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

ADR-0039 was proposed on 2026-08-31, out of the M7 verification of IdeaPress (finding M7-20): a
blocking requirement with no deterministic check is currently satisfied by the audit's *silence*,
which lets the model's default behaviour settle exactly the qualitative gates nothing mechanical
backstops. It lays out three options with a recommendation — affirmative, labelled, per-requirement
attestation — and stays **Proposed** until a human accepts one; the commit gate's behaviour does
not change on the strength of this record alone.

ADR-0038 was added on 2026-08-31, during IdeaPress's M7 build, to close a gap Master Architecture
§5.2 left open: its inference-concurrency bullet gave a policy for FreeWeight and LoadCoach and
named IdeaPress nowhere, while IdeaPress's own default configuration binds two models to a card
that holds one. It states the machine-wide rule — two models contending for one GPU must both fit,
with room for their context, or the later one waits — names LoadCoach's admission as the compliant
reference implementation, gives IdeaPress the narrower serialise-and-unload obligation that needs
no queue, and records the estimator question (duplicate `estimate_vram` or extract it to
`modelrack`) with a recommendation rather than performing an extraction that touches a published
package and two 1.0 applications.
