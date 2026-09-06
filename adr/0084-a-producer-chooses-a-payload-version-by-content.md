# ADR-0084 — A producer chooses a payload version by content, not by build

**Status:** Accepted (2026-09-05)
**Extends:** [ADR-0068](0068-a-post-freeze-minor-is-a-sibling-class.md) rules 3 and 5 (a bare name
keeps its version; carrying a nested minor is the outer payload's own minor). ADR-0068 settles what
the *contract* looks like once both versions exist. This settles what the *producer* does with two
writable versions in one build.
**Relates to:** [ADR-0009](0009-setspec-schema-strategy.md) (acceptance is by major, so a `1.0`
consumer already accepts a `1.1` document it was not built for),
[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the adapter axis whose arrival
creates the first real instance of this question),
[ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) (why most records will never carry
an adapter),
[ADR-0022](0022-capability-evidence-record-contract.md) §5 (the incremental-import contract a
bundle's bytes participate in).
**Source:** Row H4, decision 3 of its kickoff §0.3 — FreeWeight 1.1, the suite's first producer to
hold two writable versions of the same payload at once.

## Context

[ADR-0068](0068-a-post-freeze-minor-is-a-sibling-class.md) built the sibling-class mechanism so a
frozen payload could gain an optional field without editing the frozen class. It answers every
question about the *contract*: two field-definition classes, two schema snapshots, two golden sets,
a bare name that permanently means the older minor. It deliberately does not answer the question a
producer faces the moment it adopts the new sibling, because at the time no producer had.

FreeWeight 1.1 is that producer. It writes `benchmark.evidence_bundle`, and at LA3 it can write
bundles two ways:

* a bundle of evidence measured on bare bases — exactly what `freeweight 1.0.0` writes today, and
  what the overwhelming majority of exports will be for the lifetime of the major, because almost
  every installation measures no adapters at all;
* a bundle carrying at least one record measured on a `(base, adapter)` subject, which needs the
  `1.1` element type to be expressible.

Both versions are registered, published, schema-snapshotted and golden-tested. Both are writable by
this build. Nothing in the contract says which one a given export should be, and the question is not
academic: the version is a byte in the envelope, and the envelope's bytes are what a consumer's
uniqueness key, its `?since=` cursor and its own goldens are computed against.

Two answers were available, and the difference between them is not stylistic.

**Always write the newest version this build can write.** It is the simpler rule, it is what most
producers do without thinking about it, and there is a real argument for it: one code path, one
golden set, no branch to get wrong, and no possibility of a build that "forgets" it can express
something. Acceptance is by major ([ADR-0009](0009-setspec-schema-strategy.md) rule 9), so no
existing consumer *breaks* — a `1.0` reader negotiating `[1.0]` accepts a `1.1` document.

**Write the version the content actually needs.** A bundle whose records carry no adapter is
written at `1.0`, and is byte-for-byte what the previous release wrote. A bundle carrying any
adapter-bearing record is written at `1.1`.

## Decision

**A producer holding two writable versions of one payload chooses between them by the content of
the document it is about to write, not by the version its build is capable of.** It writes the
lowest version that can express the document, and the choice is proved byte-wise, not argued.

1. **Lowest expressible version wins.** A document that the frozen version can express is written
   at the frozen version. The newer minor appears in the wild only on documents that use what the
   minor added.
2. **The unchanged case is byte-identical to the previous release, and that is a golden.** Not "is
   expected to be", not "should be" — a committed golden produced by the previous release's code,
   asserted against this release's output over the same input. ADR-0068 rule 4 proved byte-identity
   at the *serializer*; this proves it at the *producer*, which is where a consumer meets it.
3. **The decision is made from the data, once, at the point of writing** — from the records in
   hand, not from configuration, not from a flag, and not from whether the adapter feature is
   enabled. An installation with adapters configured that has measured none writes `1.0`, because
   its bundle contains nothing a `1.0` bundle could not carry.
4. **The version a build *can* write is declared separately from the version it *does* write.**
   Where an application publishes its emitted-schema table (FreeWeight's `EMITTED_SCHEMAS`, read by
   `freeweight version` and `GET /api/v1/version`), the entry names the **highest** version the
   build can produce, so a consumer checking compatibility before it fetches sees the ceiling. The
   per-document choice is narrower than the declaration, never wider.
5. **This generalizes.** It is the rule for the next payload minor and the one after, in any
   producer in the suite. A producer adopting a sibling class inherits this decision with it, and
   overturning it for a particular payload needs its own ADR saying why that payload is different.

## Alternatives considered

**Always write the newest version the build can write.** One path, no branch, no chance of a
producer that quietly under-declares. Rejected because it spends the sibling-class mechanism on
nothing. The whole point of ADR-0068 was that a `1.0` consumer should not have to move for a field
it will never see; writing `1.1` on every export makes every consumer move — not to *parse*, since
acceptance is by major, but in every place a version is compared, recorded, pinned, or asserted in a
golden. Consumers do hold those: LoadCoach records `schema_version` on the evidence source and
returns it in the import response, and its contract tests pin bundle goldens. Flipping that string
for every installation in the suite, to describe a field almost none of them use, is a migration
imposed on everyone to save one branch in one producer. It also destroys the strongest regression
test available here — that a no-adapter export is byte-identical to what `1.0.0` wrote — because
under this rule it is byte-identical to nothing.

**Make the version a configuration key.** `[evidence] bundle_schema_version = "1.1"`, or a
`--schema-version` flag. Rejected on the same grounds
[ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) refuses a configurable regression
panel: it converts a fact about a document into a per-deployment opinion. Two installations exporting
the same records would produce differently versioned bundles, the version would stop being evidence
about the content, and every consumer-side bug report would begin by asking what the producer's
config said. It also creates a configuration that can be set *wrong* — `1.0` with adapter-bearing
records is unwritable, and the operator learns this from an export failure.

**Decide from whether the adapter feature is configured.** Cheaper to compute than scanning the
records, and it reads like the same thing. Rejected because it is not the same thing: it is a fact
about the installation rather than about the document, and it is wrong in the common case of an
operator who has configured `[adapters] directory` and not yet measured anything. That installation
would emit `1.1` bundles whose content is indistinguishable from `1.0`, which breaks rule 2's golden
and puts the version out of step with the bytes it describes.

**Emit both versions and let the consumer negotiate.** Content negotiation at the export endpoint,
each version at its own URL or media type. Rejected as a real feature with real cost — two documents
to keep consistent, two caches, two `?since=` cursors — bought for a difference of one optional
field. Acceptance-by-major already gives the consumer what negotiation would.

## Consequences

* FreeWeight's bundle writer takes one branch: scan the records in hand for an adapter, pick the
  version, write. The evidence *record* writer takes the same branch for the same reason, per
  record.
* A `freeweight 1.1.0` installation that has measured no adapters is, byte-for-byte, a
  `freeweight 1.0.0` installation from a consumer's point of view. Exit condition 9 of row H4 is
  that statement, asserted.
* A consumer cannot infer from a `1.0` bundle that the producer is old. It infers only that the
  bundle carries no adapter-bearing evidence, which is the true and useful reading. Producer version
  is already carried by the envelope's `generator`, which is where it belongs.
* A mixed bundle — bare-base and adapter-bearing records together — is `1.1`, and is the normal
  shape of a real LA3 export. SetSpec ships a golden for exactly that case.
* The rule has teeth only while the newer minor stays additive. A minor that *removed* or
  *narrowed* something would make "lowest expressible" ambiguous; ADR-0068 rule 1 forbids that, and
  if it were ever reopened this decision would have to be revisited with it.
