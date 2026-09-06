# ADR-0086 — The consumer's adapter key column is not nullable

**Status:** Accepted (2026-09-06)
**Amends:** [ADR-0085](0085-the-evidence-uniqueness-key-carries-the-adapter.md) decision 2 (the
consumer's key column spelling), and through it
[ADR-0022](0022-capability-evidence-record-contract.md) §3.
**Relates to:** [ADR-0080](0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md)
rule 5 (the same question, decided the same way, inside the same application),
[ADR-0067](0067-reliability-keys-on-the-subject-not-the-base.md) (the shipped precedent this
follows), [ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md) rule 5 (identity is
the artifact hash), [Database Standards](../standards/database-standards.md).
**Source:** Row H5, kickoff §0.1 — found by reading ADR-0085 against LoadCoach's actual write path
before implementing it.

## Context

[ADR-0085](0085-the-evidence-uniqueness-key-carries-the-adapter.md) decision 2 gives the consumer's
uniqueness key an `adapter_artifact_digest` column and says it is **nullable**, with `NULL` meaning
the bare base. That record was written from the producer's side, where FreeWeight's
`replace_for_subject` is a delete-then-insert that matches `IS NULL` explicitly (ADR-0085 rule 4) —
a writer for which nullable is correct and demonstrated.

**LoadCoach does not write that way, and the difference is decisive rather than stylistic.**
`loadcoach.services.evidence` persists each record through `weightsdb.upsert`, which is
`INSERT … ON CONFLICT (index_elements) DO UPDATE` (`weightsdb.types`). A conflict target containing
a `NULL` **never fires**: SQL treats `NULL`s in a unique index as distinct, on SQLite and on
PostgreSQL alike, so `ON CONFLICT` finds nothing to conflict with and the statement inserts.

Spelled nullable, therefore, every re-import of a **bare-base** record inserts a second row rather
than updating the first. There is no error, no rejection and no rejected-record report: the import
counters say `imported` for ever, the row count grows once per import, and
`bound_signals_for_routing` begins scoring one subject several times over. That is a worse defect
than the one row H5 exists to close, and it lands in the same table.

[ADR-0080](0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md) rule 5 already
decided this exact question inside this application, for `reliability_stats` and `residency`, and
decided it the other way: the bare-base row is written with a **sentinel** — the empty string — and
the nullable foreign key sits beside it. `reliability_stats` has shipped that shape since migration
`0012` and the data model documents it beside the key it appears in.

## Decision

**In LoadCoach, `capability_evidence.adapter_artifact_digest` is `NOT NULL`, and the bare base is
the empty string.**

1. **The key column is `String NOT NULL DEFAULT ''`.** The unique constraint is
   `UNIQUE (source_id, canonical_id, adapter_artifact_digest, runtime_profile_hash,
   machine_fingerprint, capability_id, policy_version)`, named explicitly — the naming convention
   would generate an identifier well past PostgreSQL's 63 characters, as it already would for the
   six-column key this replaces.
2. **`''` means "measured on the bare base"**, which is what every row written before this
   migration means, so existing rows backfill to `''` and say exactly what they always said.
3. **A nullable `adapter_id` foreign key into `adapters` sits beside it**, `ON DELETE SET NULL`, and
   is what the binding writes and what queries join on. It is `NULL` both for a bare-base row and
   for a record naming an adapter this operator does not have — the key column carries the identity
   either way, which is why removing an adapter row cannot merge two subjects' histories.
4. **The key column carries the adapter's artifact digest, not its row id**, unlike
   `reliability_stats.adapter_key`. Reliability is computed from local attempts, so an adapter row
   always exists by the time a statistic does; evidence arrives from another machine and may name an
   adapter this operator has never held, so the digest is the only identity available at write time.
   Both columns are the same *idea* — a non-null subject discriminator beside a nullable foreign
   key — spelled with the identity each table can actually obtain.
5. **The producer's spelling is not wrong and does not move.** FreeWeight's `adapter_id` stays
   nullable. A delete-then-insert writer that matches `IS NULL` explicitly and an `ON CONFLICT`
   writer do not have the same constraint, and ADR-0085 rule 4's requirement — that an absent
   adapter is matched as an absent adapter, never left unconstrained — is satisfied by both
   spellings. This record narrows decision 2 to the consumer; it does not reopen the producer's.

## Alternatives considered

**Nullable, as ADR-0085 wrote it.** One fewer wart, and it reads as the natural SQL spelling of "no
adapter". Rejected on the write path, not on taste: `weightsdb.upsert` is the only way this table is
written, its conflict target would contain the nullable column, and a conflict target containing a
`NULL` never fires. Adopting it would require demonstrating that a bare-base record imported twice
produces exactly one row on both dialects, and it cannot be demonstrated, because it does not.

**Nullable, plus a partial unique index for the `NULL` case.** Two indexes — one over the six
non-adapter columns `WHERE adapter_artifact_digest IS NULL`, one over all seven — do constrain
correctly. Rejected because PostgreSQL supports partial indexes as `ON CONFLICT` targets and SQLite
supports them differently enough that the upsert's inference would have to be written per dialect,
which puts a dialect branch on the suite's single evidence write path to avoid one empty string.

**Nullable, plus `COALESCE(adapter_artifact_digest, '')` in the index.** An expression index gets
the constraint right and keeps the column honest. Rejected as the same sentinel, moved somewhere a
reader cannot see it: the value in the index is still `''`, and now the data model, the migration
and the model class no longer agree about what the key is.

**Give up the upsert and write `SELECT`-then-`INSERT`/`UPDATE`.** Nullable becomes safe if the
importer matches `IS NULL` itself, exactly as FreeWeight does. Rejected because the importer already
holds the whole bundle's key set in memory for its duplicate detector, and re-deriving the same
decision a second way — once in Python, once in the database — is how the two drift apart. The
upsert is also what makes a re-import a row-wise operation rather than a transaction-long read.

## Consequences

* One more empty-string sentinel in one more unique key, and it is a deliberate wart of the same
  kind ADR-0080 accepted, documented beside the key in `apps/loadcoach/data-model.md` rather than
  left for a reader to infer from a migration.
* **The two sides of the evidence contract spell the same field differently**, and that is now
  written down rather than discovered. Nothing crosses the wire either way: the key is each
  application's private storage decision, and `capability.evidence` `1.1`'s `adapter` block is
  unchanged by this record.
* A bare-base record re-imported twice produces exactly one row, asserted on SQLite **and** on
  PostgreSQL, which is this record's own acceptance test.
* An evidence row for an absent adapter keeps its identity while `adapter_id` is `NULL`, so it binds
  on a later directory scan with no re-import — ADR-0022 §4's rule for an undiscovered model, now
  true of an undiscovered adapter too.

## Revisit when

`weightsdb.upsert` grows a dialect-aware conflict target that fires on `NULL`s — for instance if
PostgreSQL 15's `NULLS NOT DISTINCT` became expressible through it and SQLite gained an equivalent.
The sentinel exists to serve the writer; if the writer stops needing it, the column can become
nullable in a migration that also drops it from the key's meaning.
