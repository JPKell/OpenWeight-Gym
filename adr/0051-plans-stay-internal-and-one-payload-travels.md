# ADR-0051 — A plan never leaves PromptCadence; the egress decision is the one shape that travels

**Status:** Accepted (2026-09-02)
**Amends, additively:** [ADR-0035](0035-application-owned-document-schemas.md) §1's namespace table
— adds `promptcadence.*` as a fourth application namespace, and `governance.*` as a SetSpec-owned
root. Reverses nothing.
**Extends:** [ADR-0025](0025-envelope-boundaries.md) (the membership test),
[ADR-0009](0009-setspec-schema-strategy.md) (per-payload versioning),
[PromptCadence Spec §9](../apps/promptcadence/spec.md).
**Relates to:** [ADR-0011](0011-shared-package-boundaries.md) (nothing shared with fewer than two
real consumers — applied here to a schema), [ADR-0054](0054-commissioner-records-egress-it-does-not-enforce-it.md)
(the package that produces the payload).
**Source:** [PromptCadence roadmap §2, D-7](../roadmap/promptcadence-roadmap.md).

## Context

PromptCadence produces three kinds of structured record, and the temptation is to treat them
alike: the **plan** (steps, dependencies, declared tools and tiers), the **trajectory explanation**
(the full reconstructable account of a run), and the **egress decision** (may this classification
go to this target, and what was decided). Each needs a home, and the suite has exactly three homes
with a test for choosing between them.

[ADR-0025](0025-envelope-boundaries.md) supplies the test: a transferable *document* — something a
user downloads, keeps, moves to another machine and opens in a year — carries a SetSpec envelope;
an HTTP API's own request and response bodies are versioned by their path and carry none.
[ADR-0035](0035-application-owned-document-schemas.md) supplies the third home, because the audit
found a document SetSpec had no shape for and no business describing: an application may mint
document schemas in its own namespace, and only there.

What makes this a decision rather than a lookup is the pull toward publishing everything. A plan
looks like a contract — it has a schema, it is validated, it appears in an audit record — and
publishing it costs nothing today. But a published schema is a frozen shape maintained for its
readers, and PromptCadence's plan shape is the thing most likely to change: P7 is where planning is
actually learned, and the arc's top risk is that local models draft plans the design has to adapt
to.

## Decision

**Three records, three answers, and the deciding question is always "who reads this?"**

### 1. Plans are PromptCadence-internal — no envelope, no published schema

The plan is validated against PromptCadence's own schema, persisted verbatim alongside its
validated form, and rendered in the UI and the explanation. No other application reads a plan in
v1, so no schema is published and nothing about the plan's shape is frozen. Its schema version is
recorded on every trajectory so old rows stay interpretable.

### 2. The explanation is an application-owned document

`promptcadence.trajectory_explanation`, version `1.0`, in the `promptcadence.*` namespace under
[ADR-0035](0035-application-owned-document-schemas.md). It passes ADR-0025's document test — it is
exported, kept and read later — so it carries an envelope; and it fails every test for a SetSpec
schema, because it is one application's composition of its own seven tables, not a fact about a
model, a machine or a benchmark. This record adds `promptcadence.*` to ADR-0035's namespace table
as the fourth application namespace.

### 3. Events ride the existing envelope

PromptCadence's events use SetSpec's `event.envelope` unchanged. No new event schema, no new
frame shape: SSE replay, `Last-Event-ID` and the observability standards all work because the shape
is the one every other application already emits.

### 4. Exactly one new SetSpec payload: `governance.egress_decision` 1.0

It enters SetSpec because it has a **named second reader**: IdeaPress's S4 egress badge reads
recorded decisions at M13, and a `setspec`-only script must be able to validate and read a decision
PromptCadence exported, with Commissioner not installed. That is
[ADR-0011](0011-shared-package-boundaries.md)'s two-consumer rule applied to a schema rather than to
a package, and it is the only shape in this arc that meets it. It arrives under a new SetSpec-owned
root, `governance.*`, added to ADR-0035's table by this record; the capability vocabulary and every
frozen v1 payload are untouched.

## Alternatives considered

**Publish the plan as a SetSpec payload too.** It is the most contract-shaped of the three, and
publishing it would let an external tool submit or inspect plans. Rejected on ADR-0011's rule
applied to schemas: a published schema with one producer and no reader is a frozen shape maintained
for nobody, and this particular shape is the one the arc is least sure of. Freezing the plan at
Phase 0 would mean either breaking a published contract at P7 or contorting the design to preserve
a shape nobody consumes. Internal now, published at the trigger below, is strictly cheaper.

**Put the trajectory explanation in SetSpec.** It is exported and archival, which is what SetSpec
payloads are. Rejected for exactly ADR-0035's reasoning about `freeweight.export`: the document's
shape is an application's *query model* — scope, selection, seven tables composed in one
application's order — not a measurement anyone else can interpret. SetSpec describing it would make
SetSpec depend on PromptCadence's internal structure.

**Put the egress decision in the application namespace** (`promptcadence.egress_decision`) and let
IdeaPress read PromptCadence's document. One fewer shared schema, and the arc's smallest SetSpec
change would become no change at all. Genuinely arguable — it is the option that keeps SetSpec
frozen hardest. Rejected because it would make one application's namespace a dependency of another
application, which inverts ADR-0035's containment: those namespaces exist so an application can
mint a shape *without* anyone else being obliged to it. And the fact itself is not a PromptCadence
fact — "data of this classification went to that target under this policy" is true of IdeaPress's
stages and of any future component that sends anything anywhere.

**Let Commissioner own the decision as a bare Python type with no payload**, the skeleton's other
option. Rejected as a split done incorrectly: the *shape* is the cross-application contract and the
*evaluation plus ledger* is the small shared implementation, and they belong in different places —
which is what [ADR-0054](0054-commissioner-records-egress-it-does-not-enforce-it.md) records. A type
with no published schema cannot be read by a `setspec`-only consumer, which is the acceptance
criterion.

**Mint a PromptCadence event envelope**, since its event vocabulary is large and specific.
Rejected: the envelope is transport, the vocabulary is content, and a second envelope would
fragment replay and the observability standards for no gain.

## Consequences

* SetSpec ships `0.5.0` with one new root, one new payload, JSON Schema and at least three goldens.
  Frozen v1 payloads and the capability vocabulary do not move — the additive claim is verified by
  the LA0 exit condition, which requires today's evidence records to round-trip byte-identically.
* PromptCadence owns two versioned shapes: an internal plan schema (recorded per trajectory) and a
  published document (`promptcadence.trajectory_explanation` 1.0, golden-tested). Only the second
  constrains anyone else.
* IdeaPress's M13 badge work needs no PromptCadence dependency of any kind — it reads
  `governance.egress_decision` payloads through `setspec`, exactly as it reads evidence bundles
  today.
* The ADR-0035 namespace table now has four application rows and five SetSpec-owned roots. A fifth
  application, or a second governance shape, follows the same route.
* **A cost:** an external tool that wants to submit a plan to PromptCadence has no published shape
  to build against in v1, and must use the HTTP API's own request body (versioned by path,
  contracted by the OpenAPI snapshot). That is the correct home for it under ADR-0025, and it is
  worth saying out loud that "no published plan schema" is not the same as "no API".

## Revisit when

Another application needs to read a PromptCadence plan **directly** — not the explanation
containing it, but the plan as an interchange object it validates and acts on. That is the second
consumer that turns the plan into a contract, and it arrives with a SetSpec payload, a version and
goldens, decided in its own record.
