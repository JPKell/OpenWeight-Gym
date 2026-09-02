# ADR-0058 — The execution subject gains an adapter axis, and an absent adapter changes nothing

**Status:** Accepted (2026-09-02)
**Amends, additively and reversing nothing:** [ADR-0008](0008-canonical-model-identity.md)
(minimal immutable identity), [ADR-0023](0023-runtime-profile-resolution.md) (the execution
subject and its profile hash), [ADR-0024](0024-canonical-id-and-model-references.md) (the
canonical string format and model references in URLs).
**Extends:** [Adapter Identity and Serving §2](../architecture/adapter-identity-and-serving.md),
[Canonical Model Identity §5](../architecture/canonical-model-identity.md) (comparability).
**Relates to:** [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) (what the axis
makes necessary), [ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md) (what
the axis is *not*).
**Source:** [Adapter roadmap §2, A-1](../roadmap/adapter-roadmap.md).

## Context

A LoRA adapter is a small weights delta applied to a base model at serving time. The suite is
about to serve one warm base with several adapters selected per request
([ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md)), which means the same
`ModelIdentity` will produce measurably different behaviour from one request to the next.

Every honesty rule in the suite keys on the measurement subject: evidence applies to a subject,
comparability is decided between subjects, routing scores subjects, provenance names one. So the
question is not whether an adapter is worth recording — it is *which axis it is*, and the answer
is constrained from three directions at once.

**It cannot be the artifact digest.** ADR-0008 already rejected quantization as an identity field,
and rightly: two quantizations of one model are two different weight files, so the digest already
separates them. An adapter is the case that argument does not cover. The base artifact is
byte-identical whether or not an adapter is applied; the digest does not move, and so it cannot do
the separating. That is precisely why a new axis is needed rather than a reuse of the old one.

**It cannot be the runtime profile hash.** The profile hash separates serving configurations, and
it will indeed carry *whether the server was launched with adapters registered*
([ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md)). But it is an opaque
hash. Nobody can ask a hash "how good is the fact-check adapter?", pin one by name, or show a user
which of three adapters a turn ran under. Separation without attribution is only half of what
evidence needs.

**It cannot be part of `ModelIdentity`.** Folding the adapter into the identity — a synthetic
`provider_model_name` of `qwen3.5-9b-q8+factcheck`, say — makes "same base" un-computable. The
router must be able to ask whether a candidate runs on the process that is already resident, which
is exactly what [ADR-0066](0066-residency-is-two-level.md)'s two-level residency needs, and it
would also mint a provider model name the provider never reported.

And whatever is decided must be **additive to the point of invisibility**: three databases, every
published evidence bundle and every golden in the suite contain subjects with no adapter, and none
of them may change.

## Decision

**The execution and measurement subject gains one optional, content-addressed adapter axis.**

```text
before   (model identity,                 runtime_profile_hash, machine_fingerprint)
after    (model identity, adapter | none, runtime_profile_hash, machine_fingerprint)
```

### 1. `AdapterIdentity` — content-addressed on the served artifact

A BaseAiCore value object, `@dataclass(frozen=True, slots=True)` like its neighbours:

* `name` — the manifest's human label (`^[a-z][a-z0-9_-]{1,63}$`); the pin and display name.
* `artifact_digest` — the sha256 of **the served GGUF artifact**, normalized by the existing
  `normalize_digest` (ADR-0024 §2). This is the identity. Renaming the file changes nothing;
  changing its content makes a new subject.
* `source_digest` — optional sha256 of the training checkpoint, for lineage only. It never
  participates in identity, because re-converting one checkpoint can yield a different served
  artifact, and the artifact is what produced the behaviour.

### 2. `ModelIdentity` is untouched; the subject carries the adapter

`MeasurementSubject` gains `adapter: AdapterIdentity | None = None`. `ModelIdentity` keeps its
three fields, its equality, its hash and its `canonical_id` exactly as ADR-0008 and ADR-0024 fixed
them — "which weights does this provider serve under this name" stays a question the base answers
alone.

### 3. The canonical string gains an optional suffix, on the subject

```text
llamacpp/qwen3.5-9b-q8@sha256:1f3a9c4e2b70                                  # no adapter — today's string
llamacpp/qwen3.5-9b-q8@sha256:1f3a9c4e2b70+factcheck@sha256:9e2b41d07c55    # with one
```

The suffix is `+{adapter.name}@{digest_short}`, where `digest_short` is ADR-0024 §1's rule
unchanged — `sha256:` followed by 12 hex characters. **With no adapter the string is byte-for-byte
what it is today**, which is the additive proof and is golden-tested as such. It remains a display
and lookup key, still lossy, still never parsed back into its parts (ADR-0024 §4).

**In URLs:** ADR-0024 §3 is unchanged — a canonical string is never a URL path segment. Where it
appears as a query-parameter value, `+` is percent-encoded as `%2B`, because a bare `+` in a query
string decodes to a space under form encoding and would silently resolve to a different subject
(or to none) rather than failing.

### 4. Comparability, restated

Evidence measured on `(base, adapterA)` applies to `(base, adapterA)` and to nothing else — not to
the bare base, not to `(base, adapterB)`. A differing adapter axis is a **different subject**, in
exactly the way a differing `runtime_profile_hash` already is (ADR-0023): shown side by side,
never merged.

### 5. Base compatibility is verified by digest, and fails closed

A PEFT `adapter_config.json` names its base by *name*, which is not a proof. Therefore:

* An adapter whose manifest declares a base **digest** is applied only to a served base whose
  digest matches. A mismatch is a refusal, never an attempt — an adapter applied to the wrong base
  produces plausible, wrong output, which is the worst available failure.
* An adapter whose manifest declares a base by **name only** may be used, and carries visibly
  reduced identity confidence through the existing `IdentityConfidence.NAME_ONLY` machinery
  (ADR-0024 §2) rather than a parallel flag. The suite already knows how to display, store and
  discount a name-only identity; an adapter's uncertainty rides the same rail.

### 6. It ships additively

`baseaicore 0.4.1`, inside every existing `>=0.4,<0.5` pin. No signature changes, no golden
edited to match new behaviour, and a new golden asserting the adapter-free subject's serialized
form is unchanged.

## Alternatives considered

**Fold the adapter into `ModelIdentity`** (a synthetic model name, or a fourth identity field).
The most obvious option, and the one that needs the least new machinery: every consumer that
already keys on identity would key on the adapter for free. Rejected because it destroys the
question "is this candidate on the resident base?" — the router would see two unrelated
identities where the machine sees one process with a different LoRA selected, and
[ADR-0066](0066-residency-is-two-level.md)'s cheap-switch/expensive-switch distinction would have
nothing to compute against. It also makes identity a thing the provider cannot confirm, breaking
ADR-0008's rule that identity names what the provider serves.

**Put the adapter in the runtime profile hash.** Defensible, and half-right — the *serving mode*
does go there ([ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md)) — so this
is the alternative that requires the least new surface of all. Rejected because a hash separates
without naming. Three adapters on one base would produce three profile hashes that no UI could
label, no task profile could weight and no caller could pin; "no benchmark, no use"
([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)) would be
unimplementable, because the gate needs to know *which* adapter lacks evidence.

**Treat the adapter as descriptor metadata rather than an identity axis.** The ADR-0008 precedent
for quantization points this way. Rejected on the same reading that makes ADR-0008 right: a
descriptor is mutable, descriptive and never part of what a measurement is attributed to, and an
adapter changes what the weights *do*. A descriptor field would let a fact-check adapter's score
be read as the base's — the fabricated comparability this whole design exists to prevent.

**Identify the adapter by its source checkpoint** (the PEFT safetensors digest) rather than by the
served GGUF. Genuinely arguable: the checkpoint is what a human thinks of as "the adapter", it
survives re-conversion, and lineage is the thing an operator remembers. Rejected because
conversion toolchains vary — the adapter roadmap names re-conversion producing a new artifact
digest as a live risk — so two materially different served artifacts would share one identity and
their measurements would silently merge. `source_digest` keeps the lineage without letting it
carry identity.

**Name-only adapter identity**, the way an Ollama tag names a model. Rejected: replacing the file
behind a name would silently change the subject and re-attribute its history, and the whole point
of content addressing here is that a rename is safe and a content change is a new subject. The
suite already pays this price with Ollama tags and records it as reduced confidence; it does not
need to design a second instance of the problem on purpose.

**Keep the canonical string bare and carry the adapter in a separate column only.** Rejected: the
canonical string is what appears in logs, badges, explanations and evidence subject keys, and a
bare base string beside an adapter column means every one of those surfaces must remember to join
them. The one that forgets attributes an adapter's measurement to the base — silently, and in the
direction that flatters. The suffix makes that mistake unrepresentable in the string itself.

## Consequences

* BaseAiCore ships `0.4.1` with one value object and one optional field. Every existing golden
  passes untouched; a new golden pins the adapter-free canonical form byte-for-byte.
* SetSpec's `CapabilityEvidence` gains optional adapter fields at v1.1 and
  `model.adapter_manifest` 1.0 arrives beside them (the ADR-0032 additive precedent). A record
  written without adapter fields is exactly today's record — asserted by the LA0 exit condition.
* FreeWeight, LoadCoach and PromptCadence all gain a subject that may carry an adapter without any
  of them being obliged to. A deployment with no adapters directory sees no change anywhere.
* The refusal in rule 5 is real work for LA1: `LlamaCppProvider` must hash the base it actually
  launched and compare, and `AdapterNotFound` and the compatibility refusal are typed errors, not
  log lines.
* **A cost, stated plainly:** subjects multiply. A base with four adapters is five subjects, each
  needing its own evidence at its own sample minimums
  ([ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md)), and per-subject reliability
  fragments accordingly ([ADR-0067](0067-reliability-keys-on-the-subject-not-the-base.md)). This
  is the price of not fabricating comparability, and it is paid in benchmark time.

## Revisit when

A provider serves adapters **by reference** — a name, a URL, a server-side registry entry — rather
than from an artifact the suite can hash. Content addressing is the mechanism this record rests
on; a provider that cannot expose the served bytes breaks it, and the replacement decision has to
say what identity means when the suite can no longer verify what it ran.
