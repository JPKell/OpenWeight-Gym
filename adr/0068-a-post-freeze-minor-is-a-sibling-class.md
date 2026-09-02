# ADR-0068 — A post-freeze minor is a sibling class, and a bare name keeps its version

**Status:** Accepted (2026-09-02)
**Amends, additively and reversing nothing:** [ADR-0009](0009-setspec-schema-strategy.md) (adds the
mechanism an additive minor uses *after* its payload's artifacts are committed),
[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (whose consequence list names the
ADR-0032 precedent for the `capability.evidence` `1.1` addition; the outcome it describes is
unchanged, the mechanism is not).
**Relates to:** [ADR-0022](0022-capability-evidence-record-contract.md) (the frozen record whose
minor this is), [ADR-0032](0032-judge-validity-and-user-capability-namespace.md) (the *pre*-freeze
additive precedent this record distinguishes itself from).
**Source:** SetSpec Phase 6 (`setspec 0.5.0`), the first genuine post-freeze minor in the suite.

## Context

[ADR-0009](0009-setspec-schema-strategy.md) fixes what a minor *means* — additive, and a reader
accepts an unknown minor within a supported major — but not how one is built. Until Phase 6 that
gap cost nothing, because every additive change to a payload landed before the payload's schema
and goldens were committed. [ADR-0032](0032-judge-validity-and-user-capability-namespace.md) added
the goal-sourced field group to `capability.evidence` that way: the fields went straight onto
`CapabilityEvidenceFields`, and the change was folded into the Phase 4 promotion before anything
downstream existed to move. That is not a precedent for a payload already published; it is a
precedent for editing a draft.

Phase 6 is the first case where the payload was already frozen, and the in-place edit turns out to
be unsafe for a reason that has nothing to do with the field being added.

**A definition nested by reference moves with the class, not with the schema.**
`EvidenceBundleFields` nests `CapabilityEvidenceFields` by reference. Adding a field to that class
— or merely editing its docstring, since pydantic embeds `__doc__` as the JSON Schema
`description` — regenerates `benchmark.evidence_bundle`'s committed `1.0` document too. The
version bump was for `capability.evidence`; the bundle got no bump, no decision and no review, and
its frozen artifact would have moved anyway. A mechanism where versioning one payload silently
re-versions another is not a versioning mechanism.

**One class cannot generate two versions.** The frozen class *is* what `1.0` means — it is what
regenerates `1.0.json` and what validates the `1.0` goldens. Editing it leaves nothing able to
produce the old document, so "both versions stay available for the lifetime of the major"
(ADR-0009 rule 6) becomes unkeepable in the same stroke.

There is a second question underneath, which the mechanism forces into the open: after `1.1`
exists, what does the *bare* exported name mean? Every producer in the suite imports
`CapabilityEvidenceOut`, not a version-qualified name.

## Decision

**A minor on an already-published payload is a new sibling class. The frozen class is never
edited, and the bare exported name never changes version.**

1. **Sibling, not edit.** The new minor is a field-definition class in the *same* module,
   subclassing the frozen one and adding only optional fields
   (`CapabilityEvidenceV1_1Fields(CapabilityEvidenceFields)`), generating its own writer/reader
   pair. The frozen class is untouched — not its fields, not its docstring, not its validators.
2. **Both versions register side by side** in `SUPPORTED_SCHEMAS` and `PUBLISHED_SCHEMAS`, each
   keeping its own JSON Schema snapshot and its own goldens for the lifetime of the major.
3. **A bare name keeps the version it was frozen at.** `CapabilityEvidenceOut`/`In` mean `1.0`
   permanently. A producer that wants `1.1` imports `CapabilityEvidenceV1_1Out`/`In` explicitly.
   Adopting a minor is therefore a deliberate edit in the consumer, visible in review, never a
   change of meaning delivered by a dependency upgrade.
4. **Byte-identity is proved, not argued.** Where the new field's default is not a value the old
   version could have written (`None` meaning "absent", not "present and null"), the writer
   suppresses the key from the dump rather than emitting `null`, so a document that does not use
   the new field is byte-for-byte what the old version produces — asserted by a golden test over
   the *existing* committed goldens.
5. **Nesting is transitive, and so is the decision.** A payload that nests another's frozen
   definition does not move when that payload gains a minor. Carrying the new minor into the outer
   payload is the *outer* payload's own minor, decided, versioned and scheduled separately —
   `benchmark.evidence_bundle` carrying adapter-bearing evidence is a bundle minor, not a
   side effect of the evidence one.

## Alternatives considered

**Edit the frozen class in place** — what ADR-0032 did, and what ADR-0058's consequence list
assumed. Rejected on the nesting argument above: it moves `benchmark.evidence_bundle`'s frozen
artifact as a side effect, and it destroys the only thing able to generate the old version. The
cost of the rejection is real — two classes where one would do — and it is the smaller cost.

**Let the bare name always mean the latest minor**, with version-qualified aliases for pinning.
Superficially kinder: every consumer gets new fields by upgrading. Rejected because it inverts who
decides. A producer that has been writing `1.0` documents would begin writing `1.1` documents
because a dependency moved, with no edit in its own tree to review and no test that would
necessarily notice — and the reader-side rule that makes minors safe (accept unknown minors) does
not protect a *producer* that never chose to emit one.

**A module per minor** (`setspec.capability.v1_1`), mirroring how majors live in versioned modules.
Rejected: the module axis is the major axis, and diluting it makes "which module am I importing"
stop answering "which major am I on". It also doubles the import surface for a change that is, by
construction, additive and backward-compatible.

**Freeze harder — forbid post-freeze minors entirely**, and require a major for any change to a
published payload. Rejected as the expensive answer to a problem this record solves cheaply: a
major obliges every consumer to migrate, for a field most of them will never read.

## Consequences

* SetSpec grows one class per post-freeze minor, permanently. `setspec.capability.v1` now holds
  both `CapabilityEvidenceFields` and `CapabilityEvidenceV1_1Fields`, and the module's own
  docstring says which is which.
* Adopting a minor is a one-line import change in each consumer that wants it — FreeWeight at LA3,
  for adapter-bearing evidence — and no change at all in consumers that do not.
* A nested payload's minor never propagates for free. Anything that needs adapter evidence to
  travel *inside* an evidence bundle waits for a `benchmark.evidence_bundle` minor and the SetSpec
  release that carries it.
* ADR-0058's consequence — "`CapabilityEvidence` gains optional adapter fields at v1.1 … (the
  ADR-0032 additive precedent)" — is amended here: the fields, the version and the byte-identity
  guarantee are exactly as that record describes; only the mechanism differs.
* The suite gains a rule that reads the same in every repo: if a payload's artifacts are
  committed, its class is frozen.

## Revisit when

A payload accumulates minors faster than the sibling chain stays legible — three or more live
minors of one payload, or a minor that needs to *change* an inherited field rather than add one.
Either signals that the payload has outgrown additive evolution and the honest answer is a new
major in a new module, which is a different decision than this one.
