# ADR-0071 — ModelRack persists artifact digests in a JSON file the application names

**Status:** Accepted (2026-09-03)
**Amends, additively:** ModelRack spec §3 ("no persistence … beyond a documented in-memory
metadata cache"), §10 ("none persistent") and §12 ("reads no file"), each of which gains one named
exception. [ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) decision 6
(the suite takes over model file management and hashing) is applied, not changed.
**Relates to:** [ADR-0008](0008-canonical-model-identity.md) and
[ADR-0024](0024-canonical-id-and-model-references.md) (what a digest is and why it must be the
content hash), [ADR-0016](0016-unavailable-is-not-zero.md) (a stale digest would be a fabricated
identity, which is why invalidation is by content stamp rather than by time),
[Master Architecture §1.2](../architecture/master-architecture.md) (every path is the
application's).
**Source:** ModelRack Phase 6 (row D3) handoff §4, and the operator's decision on it.

## Context

`LlamaCppProvider` identifies a served model by the sha256 of the whole GGUF file
([Adapter Identity §2](../architecture/adapter-identity-and-serving.md): "identity is the hash,
the path is a locator"). That is the identity-confidence gain ADR-0062 names over Ollama's tags,
and it costs what it costs: on the reference machine a 5.6 GB file hashes in 6.4 s and the model
directory — five files, 39 GB — in about 45 s. The header a descriptor is built from is cheap
(hundreds of milliseconds) and is cached under the spec's existing in-memory TTL rule.

Phase 6 as first built kept the digests in memory too, keyed by path and file stamp (size,
mtime, inode, device) so that a changed file simply missed. That respected spec §3 and §10 to the
letter, and it meant every process paid the 45 s on its first discovery: acceptable for a
long-running LoadCoach, and paid on every run by a command-line FreeWeight, until each
application wrote its own persistent store against the `DigestStore` seam the adapter exposes.

Nothing about a content digest changes between processes. It is invalidated by the file's bytes
changing, which the stamp already captures, and by nothing else. Holding a fact that stable in
memory only, and recomputing it at 0.9 GB/s per process start, buys spec purity and nothing else.

## Decision

**`LlamaCppProvider` persists computed artifact digests in one JSON file inside the `state_dir`
the constructing application supplies, by default, and exposes a way to clear it.**

1. **The file is `<state_dir>/digests.json`**, written by `JsonFileDigestStore`, which becomes
   the adapter's default `DigestStore`. `state_dir` is already the application-named directory
   ADR-0062 assigns for pid files and captured stderr; the digest file lives beside them and is
   owned the same way — by the application's data root, never by a path this package chooses.
   `InMemoryDigestStore` remains available for callers that want no persistence, and any
   `DigestStore` implementation may still be injected.
2. **Entries are keyed by path and stamp** — the same key the in-memory store used — and each
   records the path, the digest and when it was computed. A file whose bytes changed has a
   different stamp and therefore misses; nothing is ever *invalidated by time*. `refresh=True` on
   any discovery method re-hashes regardless of what the file holds.
3. **Writes are atomic and merging.** A write reads the current file, merges the new entry,
   drops entries whose path no longer exists, and replaces the file through a temporary sibling
   and `os.replace`. Two processes writing the same file cannot corrupt it; the worst outcome of a
   race is one lost entry, whose cost is one re-hash.
4. **An unreadable or unversioned file is treated as empty**, logged at DEBUG, and overwritten
   on the next write. It is a cache; nothing may fail because of it.
5. **It is clearable**: `LlamaCppProvider.clear_digest_cache()` empties the store and removes the
   file; deleting the file by hand is equally safe. The next discovery hashes again.
6. **It is never shared between applications.** Each application names its own `state_dir`
   ([Dependency and Boundary Rules](../architecture/dependency-and-boundary-rules.md): reading
   another application's cache files is forbidden), so LoadCoach and FreeWeight each hash a
   directory once, not once per process and not once between them. Two applications pointed at
   one `state_dir` would share pid files as well as digests, which ADR-0062 already rules out.
7. **The format is versioned** (`{"version": 1, "entries": {…}}`). A future version reads older
   files or treats them as empty; it never migrates them, because a cache has no history to keep.

## Alternatives considered

**Keep digests in memory; applications persist them.** The Phase 6 build as first delivered.
Rejected by the operator: it makes a fact that never changes cost 45 s per process until two
applications each write the same small store, for no gain but the letter of a spec line written
before this package served files at all. The seam stays, so an application that wants a different
store still injects one.

**A sidecar file next to each model** (`<model>.gguf.sha256`). Rejected: it writes into the model
directory, which the operator owns and this package only reads; a read-only or shared model
directory would break discovery; and a sidecar is exactly the kind of file a rename or a copy
leaves behind pointing at the wrong bytes.

**Trust a digest carried in GGUF metadata.** Rejected: no such field is standard, and a
self-reported digest is a name, not a measurement — the tag problem ADR-0062 exists to escape.

**A cheaper digest (header hash, or size and mtime).** Rejected before this ADR and rejected
here: it would be a different identity from the one the contract names, and a header hash cannot
distinguish two quantizations of one model with the same metadata.

## Consequences

* ModelRack gains one file format it owns, small and versioned, and one more thing an operator
  may delete. The spec's non-goal is narrowed by one named exception rather than dropped: no
  database, no cache of anything but digests, nothing that survives outside `state_dir`.
* The first discovery on a fresh `state_dir` still costs the full hash of the directory; every
  discovery after it, in any process, costs a `stat` per file. Adding a model costs one hash of
  that model.
* An operator who edits `digests.json` can make the adapter report a wrong identity for a file
  until `refresh=True` or `clear_digest_cache()`. That is the trust boundary of any cache in an
  application's own data root, and the entry's stamp still refuses a file whose bytes changed.
* The known gap of stamp-based invalidation is unchanged: a rewrite that preserves size and
  restores the modification time on the same inode would hit. That is deliberate tampering, not
  an ordinary re-download or replace, and `refresh=True` exists for it.
* The `DigestStore` seam and the in-memory implementation survive, so the choice is reversible
  per application by one constructor argument.

## Revisit when

* A model directory is shared read-only between machines, or between applications, and the
  per-application file stops being where a digest naturally lives — then a sidecar or a
  registry-provided digest deserves a second look.
* GGUF gains a standard content-digest field that llama.cpp verifies on load; a verified
  self-report would make the hash a check rather than a computation.
* The stamp's known gap is exercised in practice: then the key gains a cheap sample of the
  content (first and last blocks) beside the stat fields.
