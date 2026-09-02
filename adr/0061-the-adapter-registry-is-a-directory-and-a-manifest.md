# ADR-0061 — The adapter registry is an operator's directory and a reviewed manifest, not a service

**Status:** Accepted (2026-09-02)
**Extends:** [Adapter Identity and Serving §4](../architecture/adapter-identity-and-serving.md),
[Master Architecture §11](../architecture/master-architecture.md) items 3 and 12.
**Relates to:** [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (identity is the
hash), [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) (what
`declared_capabilities` commits an operator to), [ADR-0065](0065-an-adapter-is-classified-and-local-only.md)
(the manifest's classification field), [ADR-0009](0009-setspec-schema-strategy.md) (payload
versioning), [ADR-0010](0010-queue-implementation.md) (the no-new-infrastructure precedent).
**Source:** [Adapter roadmap §2, A-4](../roadmap/adapter-roadmap.md).

## Context

Adapters have to come from somewhere, and two applications need to know about them independently.
FreeWeight enumerates adapter subjects to benchmark them; LoadCoach builds routing-facing adapter
rows to select among them. Neither may read the other's database, and neither may import the other.

The shape that suggests itself is a registry service — a component that owns the adapter inventory
and answers questions about it. The suite has a standing answer to that suggestion: no new
infrastructure without an ADR demonstrating a concrete, present need (§11.12), the same rule that
kept a broker out of the queue.

There is also the question of what a manifest *asserts*. An adapter's base compatibility, its
classification and its declared capabilities are all safety-relevant: the first decides whether it
may be applied at all, the second decides where its work may go, the third is a claim FreeWeight
will test and LoadCoach will route on. A PEFT `adapter_config.json` supplies only part of this, and
names its base by *name*, which is not a proof.

Finally, files move. A registry keyed on paths breaks when someone tidies a directory; a registry
that ignores paths cannot find anything.

## Decision

**There is no registry service. The registry is an operator-owned directory of adapter artifacts
plus one reviewed manifest per adapter, and the manifest is a SetSpec payload.**

1. **`model.adapter_manifest` 1.0**, a SetSpec payload, because at least two applications read it
   independently — the same two-consumer justification that puts any shape in SetSpec. Its fields:
   `name`, `artifact_file` (a relative path), `artifact_sha256` (the identity), optional
   `source_sha256` (lineage), `base` (provider model name plus artifact digest, the digest optionally
   absent → `name_only` confidence, flagged everywhere it surfaces), `declared_capabilities[]`
   (namespaced vocabulary terms, validated; a bare reserved root refused), `data_classification`,
   `format = "gguf"`, `created_at`, `notes`.
2. **Opt-in, per application.** Each consumer names the directory in its own configuration
   (`[adapters] directory = ""`), and **empty means the feature is off**. A deployment that has never
   heard of adapters is unaffected by every part of this arc.
3. **Who reads what.** FreeWeight reads the directory to enumerate benchmark subjects; LoadCoach
   reads it to build routing rows; **ModelRack never reads the directory** — it receives manifests
   from the application constructing it, and validates and mounts them. PromptCadence and IdeaPress
   never read it at all: they see adapters only through LoadCoach, which is the point of the layering.
4. **`loadcoach adapters scan` drafts; a human keeps.** The scan hashes the artifact, reads
   `adapter_config.json`, and flags an unverifiable base as `name_only`. The operator reviews the
   draft and commits it. **Nothing trusts an unreviewed draft** — a drafted manifest is a proposal,
   not a registration.
5. **Identity is the hash; the path is a locator.** A renamed file with a stale manifest makes that
   adapter **unavailable** — fail closed, named by `doctor`, until a rescan. Never a silent
   misattribution, and never a lost benchmark: the measurements stay attached to the hash, so the
   evidence returns when the file does.
6. **Training is outside the suite in v1.** The directory is the hand-off point; PEFT/safetensors
   adapters are converted to GGUF once, on drop, as part of the scan workflow.

## Alternatives considered

**A registry service** — an HTTP component (or a fourth application) owning the adapter inventory.
It is the shape the problem suggests, and it would centralize validation, give one place to query,
and scale to a fleet. Rejected under §11.12: there is no concrete present need, the two readers sit
on one machine and can each read a directory, and a service adds a process to run, back up, secure
and version for a deployment whose defining property is that it is one workstation. The revisit
trigger below names precisely what would change that.

**A shared database of adapters that both applications read.** Cheaper than a service and it gives
transactional consistency. Rejected outright: it is cross-application database access, which §11.3
forbids without qualification, and it is the "shared DB as a shortcut" the legacy inventory records
as an explicitly rejected concept.

**Auto-generate manifests on scan and trust them.** Removes the review step, which is the only
manual part of adopting an adapter, and the scan already knows almost everything. Rejected on the
two fields a machine cannot honestly fill. **Base compatibility**: `adapter_config.json` names a
base by name, so an auto-manifest would assert a compatibility nobody verified — the exact claim
[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md)'s digest check exists to distrust.
**`declared_capabilities`**: it is a claim under test that determines what FreeWeight benchmarks and
what LoadCoach routes on, and a machine guessing it from a filename would put a fabricated claim
into the evidence pipeline. The scan does the tedious parts; the assertions stay a person's.

**No manifest at all — derive everything from filenames and directory conventions.** The simplest
possible thing, and plenty of tooling does it. Rejected: a naming convention is an unversioned
vocabulary that drifts silently (the same objection as
[ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)'s tag channel), and
there is nowhere in a filename to put a data classification, a base digest or a capability
declaration.

**Put the adapter inventory in each application's own TOML configuration** instead of a shared
payload. Rejected because both applications must agree about the same adapters, and two hand-edited
configurations drift — and the drift is invisible until FreeWeight benchmarks a subject LoadCoach
will not route to, or worse, until they disagree about a classification.

**Identify adapters by path.** Rejected in both directions: a rename would change identity and orphan
its evidence, while a content change under an unchanged path would silently keep it, re-attributing
new weights to old measurements. Content addressing makes the first harmless and the second
impossible.

## Consequences

* SetSpec ships `model.adapter_manifest` 1.0 with JSON Schema and goldens; a `setspec`-only script
  validates a manifest, which is one half of the LA0 exit condition.
* Adopting an adapter is: drop the file, run `loadcoach adapters scan`, review the draft, keep it.
  The review step is the deliberate friction, and it is where the base digest and the capability
  claims get a person's attention.
* The whole feature is off unless a directory is configured, in every consuming application
  independently. There is no partial state where one application knows about adapters and another
  silently does not — each is explicitly on or off, and `doctor` reports which.
* A tidy-up that renames adapter files takes those adapters out of service until a rescan, loudly.
  That is the intended failure: unavailable and named, rather than available and wrong.
* Operators own an inventory in files they can read, diff, back up and put under version control —
  which is the same property the suite chose for prompts (ADR-0012) and for goal packs.

## Revisit when

A **third reader class** appears — something beyond FreeWeight and LoadCoach that needs the adapter
inventory, especially on a machine that is not the one holding the files. Until then a manifest
*service* is still not the answer; the first thing to reconsider at that point is whether the third
reader can read the directory too, and only then whether the inventory needs an owner.
