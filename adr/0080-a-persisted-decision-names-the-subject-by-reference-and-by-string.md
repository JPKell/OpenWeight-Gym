# ADR-0080 — A persisted decision names the subject by reference and by string

**Status:** Accepted (2026-09-05)
**Extends:** [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the subject's adapter
axis and its canonical suffix), [LoadCoach Data Model](../apps/loadcoach/data-model.md).
**Relates to:** [ADR-0024](0024-canonical-id-and-model-references.md) (the canonical
string is display and lookup, never parsed back),
[ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md) (identity is the hash, the
path is a locator), [ADR-0067](0067-reliability-keys-on-the-subject-not-the-base.md) (reliability
keys on the subject), [Database Standards](../standards/database-standards.md).
**Source:** Row H2, decision 4 of its kickoff §0.2.

## Context

[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) gives the execution subject an
adapter axis and gives the canonical string an optional `+name@sha256:…` suffix. It is explicit that
the string stays a display and lookup key and is never parsed back into its parts
([ADR-0024](0024-canonical-id-and-model-references.md) §4).

LoadCoach must now persist that subject in several places: the routing candidate rows that make up
an explanation, the attempt rows that record what answered, the residency rows that decide what a
switch costs, and the reliability rows that
[ADR-0067](0067-reliability-keys-on-the-subject-not-the-base.md) re-keys onto the subject. Today
every one of them keys on `model_id`, a foreign key into `models`.

Three ways to store the adapter half suggest themselves, and they fail differently. A **string
only** — the suffixed canonical ID on the row — makes every query a `LIKE`, makes the reliability
unique key a string comparison, and puts the parsing that
[ADR-0024](0024-canonical-id-and-model-references.md) forbids back on the read path the
moment anyone needs the adapter's name. A **reference only** — a nullable `adapter_id` foreign key —
is correct and queryable, but a decision record then depends on a row in a table whose contents
follow an operator's directory: rescan after a rename, and the explanation for a decision made last
month renders a name that no longer means what it did, or no name at all. **Both** costs a column.

The stakes are not aesthetic. A routing explanation is the record of a decision, kept for ever by
default, and the LoadCoach-P3 precedent is that it stays readable after the code and the
configuration have changed.

## Decision

**A row that records a decision carries the adapter as a real foreign key *and* as the canonical
subject string written at decision time. The key is what the system queries; the string is what a
person reads.**

1. **`adapter_id`, a nullable foreign key into `adapters`**, on every row that names a subject:
   routing candidates, job attempts, jobs, residency and reliability statistics. `NULL` means the
   bare base, which is every row written before this arc and every decision that used no adapter.
2. **`subject_canonical_id`, the string from
   [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) §3**, written at the moment the
   decision was made and never recomputed. With no adapter it is byte-for-byte today's
   `canonical_id`, which is the additive proof.
3. **It is written, never parsed.** Nothing reads the suffix back out. Every question about which
   adapter answered is asked of `adapter_id`, and the string exists so an explanation, an export or
   a support conversation can quote what the system believed at the time.
4. **The `adapters` table keys on the artifact hash**
   ([ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md) rule 5), so a rename
   keeps the foreign key valid and keeps the evidence attached, and a content change is a different
   row and a different subject. A decision record is therefore never orphaned by an operator tidying
   a directory.
5. **The unique keys move to the subject, and `NULL` is part of them.**
   `reliability_stats` becomes `UNIQUE (model_id, adapter_id, task_profile_id, window)` and
   `residency` becomes `UNIQUE (model_id, adapter_id, gpu_index, loaded_at)`. Because SQL treats
   `NULL`s as distinct in a unique index, the bare-base row is written with a **sentinel**, not with
   `NULL`: the migration and the repository use the empty string for "no adapter" in these two keys
   and the foreign key column stays `NULL` beside it. Stating this here is the point — it is the
   detail that turns "key on the subject" into either a working constraint or a table that silently
   accepts duplicates.
6. **Existing rows migrate to base subjects.** Every row that exists when the migration runs
   describes a bare base: `adapter_id` stays `NULL`, `subject_canonical_id` is backfilled from the
   model's `canonical_id`, and the migration's docstring says so, because a reader in a year needs
   to know the rows were not measured under an adapter that has since been forgotten.

## Alternatives considered

**The canonical string alone.** One column, no join, and it is what an explanation renders. Rejected
on the read path: reliability, residency and candidate lookups all key on the subject, so the string
becomes an index key and a `LIKE` target, and the first time anything needs the adapter's name it
parses the suffix — which is exactly what
[ADR-0024](0024-canonical-id-and-model-references.md) §4 forbids, and forbids because the
string is lossy.

**The foreign key alone**, rendering the string on read. Correct, normalized, and the smaller
schema. Rejected because the rendering depends on `adapters` still holding that row with that name.
An adapter deleted from the directory, or renamed and rescanned, changes what an old explanation
says about a decision that did not change. A decision record must not be editable by later
configuration.

**A composite subject table** — one row per `(model, adapter)` pair, with everything keying on its
id. Cleaner in the abstract and it would make the unique keys trivial. Rejected as a table whose
only content is the pairing of two keys already present, bought at the price of a join on every
routing read and a lifecycle question (when is a pair created, when retired) that nothing needs
answered.

**Store the adapter's digest on the row instead of a foreign key.** Content-addressed, immune to
directory changes, no join. Rejected: it duplicates the identity that `adapters` exists to hold, and
it gives up referential integrity for a property the hash-keyed table already provides.

## Consequences

* Five tables gain two columns, and two unique keys change shape — a migration whose docstring
  states the rule for existing rows.
* An explanation renders the subject exactly as it was recorded, whatever has happened to the
  adapter directory since, and answers "which adapter" from a key rather than from a string.
* The empty-string sentinel in two unique keys is a wart, and it is a deliberate one: the
  alternative is a unique constraint that does not constrain. It is documented in the data model
  beside the keys it appears in, not left for a reader to infer from a migration.
* Every export path that shows a subject shows the recorded string, so LoadCoach, an evidence
  bundle and a support transcript all quote the same characters.

## Revisit when

A third axis joins the subject. Two axes fit comfortably in a key and a string; a third would make
the composite-subject table this record declined the cheaper shape, and the question should be
reopened then rather than answered by adding a fourth column.
