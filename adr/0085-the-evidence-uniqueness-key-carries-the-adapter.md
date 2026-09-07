# ADR-0085 — The evidence uniqueness key carries the adapter, on both sides

**Status:** Accepted (2026-09-06)
**Amended by:** [ADR-0086](0086-the-consumers-adapter-key-column-is-not-nullable.md) — decision 2's
`adapter_artifact_digest` is **not nullable** in the consumer, and the bare base is the empty
string. LoadCoach writes this table through `weightsdb.upsert`, an `INSERT … ON CONFLICT` whose
conflict target never fires on a `NULL`, so a nullable key column would silently insert a second
row on every re-import of a bare-base record. The producer's nullable `adapter_id` is unaffected.
**Amends:** [ADR-0022](0022-capability-evidence-record-contract.md) §3 (the producer and consumer
uniqueness keys), additively — both keys gain one column and nothing else changes.
**Relates to:** [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the axis this key
was written before), [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) (why two
subjects' records must never merge),
[ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md) (why the runtime
profile is not the place to carry it),
[ADR-0068](0068-a-post-freeze-minor-is-a-sibling-class.md) (the minor that made the axis
expressible on the wire).
**Source:** Row H4, integration verification I18. Found by running it: a real FreeWeight `1.1`
bundle, exported from three measured subjects on one base, was imported through LoadCoach's own
documented path and **two of its three records were discarded**.

## Context

[ADR-0022](0022-capability-evidence-record-contract.md) §3 fixed the uniqueness key on both sides of
the evidence contract:

* **Producer:** `(model_id, runtime_profile_id, machine_id, capability_id, policy_version)`
* **Consumer:** `(source_id, canonical_id, runtime_profile_hash, machine_fingerprint, capability_id, policy_version)`

Both were written before the measurement subject had an adapter axis. Neither carries one, and the
`canonical_id` in the consumer's key is the **model's** — the base's — because
[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) deliberately kept the adapter in its
own `adapter` block rather than folding it into the model identity, so that a model identity keeps
meaning exactly what it always meant.

The consequence is that a base and every adapter subject on it collapse to **one key** for a given
capability, profile, machine and policy. This is not a theoretical concern; it was measured. The LA3
journey exported a `benchmark.evidence_bundle` `1.1` carrying three records — the bare base and two
adapter subjects, all `reliability`, all on one machine under one profile — and LoadCoach's importer
answered:

```text
records       3
  imported    1
  bound       1
  rejected    2
    [1] DUPLICATE_RECORD: a second record in this bundle carries the same (canonical_id,
        runtime_profile_hash, machine_fingerprint, capability_id, policy_version); two
        measurements are not merged into one row
    [2] DUPLICATE_RECORD: …
```

The importer is behaving **correctly** under the contract it was given. Refusing to merge two
measurements into one row is exactly right; ADR-0022 §3 simply did not know that two of those
records describe different subjects. The rejection is a duplicate-detector doing its job on a key
that has gone stale.

Two things about the failure are worth stating, because both mislead.

**It is not the binding gap.** Row H2's handoff predicted that adapter-bearing evidence would land
`unmatched` until LoadCoach's registry could hold adapter subjects. That prediction was right about
the *registry* and wrong about the *order*: these records never reach binding at all. They are
discarded at the uniqueness check, one step earlier, and no amount of registry work moves that.

**There is an accidental near-miss that must not be mistaken for a fix.** If an adapter subject were
measured under `RuntimeProfile.adapters_registered = True` while its base were measured with the
field unset, the two would have different `runtime_profile_hash` values and would not collide. That
is a coincidence of serving mode, not a property of subjects: two adapter subjects on one base,
measured under the same serving mode, still collide with each other.
[ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md) is explicit that
which adapter ran is the **subject** and whether any were registered is the **profile**; leaning on
the profile hash to separate subjects would conflate exactly the two things that ADR separated, and
would break the moment somebody measured two adapters properly.

## Decision

**Both uniqueness keys gain the adapter, and nothing else changes.**

1. **Producer** (FreeWeight):
   `UNIQUE (model_id, adapter_id, runtime_profile_id, machine_id, capability_id, policy_version)`,
   with `adapter_id` nullable and `NULL` meaning the bare base. Implemented in FreeWeight migration
   `0008`.
2. **Consumer** (LoadCoach):
   `UNIQUE (source_id, canonical_id, adapter_artifact_digest, runtime_profile_hash,
   machine_fingerprint, capability_id, policy_version)`, with `adapter_artifact_digest` nullable and
   `NULL` meaning the bare base. **Not yet implemented** — it is the row that follows H4.
3. **The adapter's artifact digest is the key column, not its name.** A name is a label an operator
   may revise; the digest is the identity
   ([ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md) rule 5). A key spelled
   with the name would merge two adapters' histories the moment one was renamed, and would split one
   adapter's history the moment it was not.
4. **`NULL` is matched as `NULL`, never left unconstrained.** A key comparison that treats an absent
   adapter as "any adapter" re-creates the collision in the delete path instead of the insert path,
   which is worse: it silently removes a base's evidence when an adapter subject is recomputed.
   FreeWeight's `replace_for_subject` matches `IS NULL` explicitly for this reason.
5. **The addition is additive and needs no payload change.** `capability.evidence` `1.1` already
   carries `adapter.artifact_digest`; a `1.0` record has no adapter and keys as `NULL`, which is
   what it has always meant. No producer changes its bytes, and a consumer that has not yet adopted
   the wider key reads `1.1` documents exactly as it does today — badly, but no worse than before.

## Alternatives considered

**Put the subject string in `model.canonical_id`.** The smallest possible change: the producer emits
`…@sha256:…+terse@sha256:…` where the model identity goes, and every existing key separates
correctly with no schema change anywhere. Rejected because it destroys the model identity. That
field is a *canonical model identity* with a digest that must hash the weights it names
([ADR-0024](0024-canonical-id-and-model-references.md)); an adapter subject's base is still
that base, and a consumer that looked up the model would find nothing. It would also make every
adapter subject undiscoverable as the base it runs on, which is the opposite of what grouping
subjects under their base is for.

**Add the adapter to the runtime profile hash.** Tempting because it is already in the key on both
sides and already separates measurements. Rejected by
[ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md), which decided this
exact question in the other direction and for good reasons: an adapter must be *nameable* — pinned,
weighted, displayed, filtered on by `require_adapter_evidence` — and a hash names nothing. It would
also make `adapters_registered` and the adapter's identity indistinguishable in the one field, so a
serving-mode A/B and an adapter comparison would be the same measurement.

**Let the consumer de-duplicate by last-write-wins instead of rejecting.** No schema change, no
rejection, and every record is "imported". Rejected as the worst option available: it is the silent
version of the current failure. Three subjects' measurements would become one row whose contents
depend on bundle ordering, and the surviving score would be attributed to whichever subject happened
to be serialized last. ADR-0022 §3's own refusal to merge two measurements into one row exists
precisely to prevent this, and the fix is to tell it which rows are two measurements — not to stop
it caring.

**Have the producer emit one bundle per subject.** Sidesteps the key entirely: no bundle ever
contains two records that collide. Rejected on the consumer's contract rather than the producer's
convenience. `complete` is what lets a consumer infer removal (ADR-0022 §5), and it is a property of
a whole export; a per-subject bundle can only ever be complete for that subject, so a consumer could
never tell a retired subject from one that simply was not in this file. It also multiplies
`?since=` cursors by the number of subjects.

## Consequences

* **I18 is blocked until the consumer's half lands**, and it is blocked on this rather than on the
  registry. The producer's half is done and demonstrated: a `1.1` bundle carrying three subjects'
  records exports, validates against the published schema, and crosses as a file. Its bare-base
  record imports and binds correctly today, which is the part of the two-application claim that can
  be shown now.
* **The consumer's row is now two changes, not one**: this key, and the adapter axis on
  `capability_evidence` that lets a surviving record bind to an adapter subject. The key comes
  first — until it moves, the records to bind never arrive.
* **A consumer that adopts the wider key gains nothing until it also adopts the axis.** The records
  stop being rejected and start being retained as `unmatched`, which is the state H2's handoff
  described. That is progress, not completion, and it should not be mistaken for the feature
  working.
* Existing rows are unaffected on both sides: every one has no adapter, keys as `NULL`, and means
  what it always meant.
* The producer's side is already live. FreeWeight's `0008` shipped the wider key, so a base and its
  adapter subjects have never collided in a FreeWeight database — which is why the defect surfaced
  at the consumer and not before.

## Revisit when (added 2026-09-07)

* **The execution subject gains a third axis**, as it gained the adapter one in
  [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md). The failure this record fixes —
  several subjects collapsing to one key, so an import keeps the first and rejects the rest as
  duplicates — returns unchanged, and the fix is the same shape. Any proposal to extend the subject
  should carry the key change with it rather than discover it at an integration verification.
* **A producer needs to retire a subject's records.** The alternatives rejected per-subject files
  partly because a consumer could not tell a retired subject from one simply absent from this
  bundle. A real retirement requirement reopens that, and it is a bundle-shape question rather than
  a key question.
* **The key is needed on a wire rather than only in two schemas.** Today it exists in FreeWeight's
  table and LoadCoach's, spelled differently on purpose
  ([ADR-0086](0086-the-consumers-adapter-key-column-is-not-nullable.md)); the day a payload carries
  the key itself, the two spellings have to become one and that is a SetSpec decision.
