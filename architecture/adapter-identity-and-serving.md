# Adapter Identity and Serving — Hot-Swappable LoRA in the Suite

**Status:** Designed 2026-09-01, not implemented. The decisions here are scheduled as ADRs A-1…A-10
in the [adapter roadmap §2](../roadmap/adapter-roadmap.md) and amend
[ADR-0008](../adr/0008-canonical-model-identity.md),
[ADR-0023](../adr/0023-runtime-profile-resolution.md) and
[ADR-0024](../adr/0024-canonical-id-and-model-references.md) without reversing any of them.
**Audience:** every component — this is a cross-cutting identity and serving design, like
[Canonical Model Identity](canonical-model-identity.md), which it extends.

---

## 1. What this is

A LoRA adapter is a small weights delta trained onto a base model. The suite gains the ability to
serve **one warm base model with several adapters, selected per request** — fact-checking, judging
and drafting as three different execution subjects on one resident model, with **zero base
load/unload events between them**. The load-bearing insight:

> **Identity is bookkeeping; residency is serving state.** The execution subject — what evidence,
> routing, provenance and explanations key on — changes per request and costs nothing to change.
> What sits in VRAM is the base, once.

Everything below preserves the suite's existing honesty rules: an adapter changes behaviour the
way a quantization does, so it changes the *subject*; evidence is measured, never inherited; an
unknown is absent, never zero; and every change is additive — a subject without an adapter is
byte-for-byte what it is today.

## 2. Identity: the adapter axis (A-1)

The measurement/execution subject grows one optional axis:

```text
before   (model identity,                    runtime_profile_hash, machine_fingerprint)
after    (model identity, adapter | none,    runtime_profile_hash, machine_fingerprint)
```

* **`AdapterIdentity`** (BaseAiCore, additive): `name` (the manifest's human label),
  `artifact_digest` (sha256 of the **served GGUF artifact** — content-addressed, so renaming the
  file changes nothing), and optional `source_digest` (sha256 of the training checkpoint, for
  lineage — re-converting a checkpoint may produce a new artifact digest, and the artifact served
  is the identity).
* **Canonical string form** (amends ADR-0024, additively): the existing canonical id gains an
  optional suffix — `llamacpp/qwen3.5-9b-q8@sha256:1f3a9c4e2b70+factcheck@sha256:9e2b41d07c55`.
  Absent suffix = bare subject, unchanged from today. A canonical string is never a URL path
  segment (ADR-0024 §3); where it appears as a query-parameter value the `+` is percent-encoded as
  `%2B`, because a bare `+` decodes to a space under form encoding.
* **Comparability rule, restated:** evidence measured on `(base, adapterA)` applies to
  `(base, adapterA)` and to nothing else — not to the bare base, not to `(base, adapterB)`.
* **Base compatibility is verified by digest, fail closed.** A PEFT `adapter_config.json` names
  its base by *name*; a name-only match is accepted only with visibly reduced identity confidence
  (the ADR-0024 `name_only` machinery, reused), and applying an adapter whose declared base digest
  does not match the served base is a refusal, never an attempt.

## 3. The split: selection vs serving mode (A-3)

Two different facts live in two different places, and confusing them corrupts evidence:

| Fact | Where it lives | Why |
|---|---|---|
| **Adapter selection** — which adapter this request runs under | The execution subject (§2) | It changes the weights' behaviour; it is the thing being measured |
| **Adapter serving mode** — the server was launched with adapters registered | The `runtime_profile_hash` | A base measured on an adapter-enabled server is a different measurement than on a clean server; the profile hash is what keeps them separate ([ADR-0023](../adr/0023-runtime-profile-resolution.md)) |

Consequences: FreeWeight can A/B `base @ clean-profile` vs `base @ adapters-registered-profile` as
two ordinary subjects and answer the overhead question **empirically on the deployment's own
hardware** — expected to be memory-only for registered-but-inactive adapters and low single-digit
percent decode cost for an active adapter (rank-proportional), but the suite measures rather than
believes. Adapter-enabled serving is the **configuration default** for llama.cpp tiers, overridable
per runtime profile — config, not code.

## 4. The registry: a directory and a manifest (A-4)

There is no registry service. The registry **is** an operator-owned directory of adapter artifacts
plus one manifest per adapter, and the manifest schema is a SetSpec payload —
`model.adapter_manifest` v1.0 — because at least two applications read it independently:

```text
model.adapter_manifest v1.0
  name                     # ^[a-z][a-z0-9_-]{1,63}$ — the pin/display name
  artifact_file            # relative path to the served GGUF
  artifact_sha256          # the identity (§2)
  source_sha256            # optional: the training checkpoint, for lineage
  base                     # provider_model_name + artifact_digest (digest may be absent →
                           #   name_only confidence, flagged everywhere it surfaces)
  declared_capabilities[]  # namespaced specializations from the SetSpec vocabulary
                           #   (coding.python, content.fact_check, user.house_voice, …);
                           #   validated; a bare reserved root is refused
  data_classification      # public | internal | confidential — required, no default (§9)
  format = "gguf"          # v1 accepts only what llama.cpp serves
  created_at · notes
```

* Each consuming application names the directory in its own configuration
  (`[adapters] directory = ""`, empty = feature off — the whole design is opt-in). **FreeWeight**
  reads it to enumerate benchmark subjects; **LoadCoach** reads it to build its routing-facing
  adapter rows; **ModelRack** receives manifests from the constructing application and validates +
  mounts. PromptCadence and IdeaPress never read the directory — they see adapters only through
  LoadCoach, which is the point.
* `loadcoach adapters scan` drafts a manifest from a dropped adapter (hashing the artifact,
  reading `adapter_config.json`, flagging an unverifiable base as `name_only`); the operator
  reviews and keeps it. Nothing trusts an unreviewed draft.
* **Rename-safety:** identity is the hash, the path is a locator. A renamed file with a stale
  manifest makes that adapter *unavailable* (fail closed, named by `doctor`) until a rescan —
  never a silent misattribution, and never a lost benchmark.
* Training happens outside the suite in v1; the directory is the hand-off point.

## 5. Serving: llama.cpp through a process-supervising provider (A-5)

Ollama has no per-request adapter mechanism, so the adapter-serving runtime is **llama.cpp's
server**, behind a new ModelRack adapter, `LlamaCppProvider`. Ollama remains the zero-ops
provider for adapter-free use; both register with LoadCoach under the generalized LC-E1.

* **One base per process.** `Provider.load(identity, profile)` maps to *spawning* `llama-server`
  with the base GGUF, the profile's flags (`n_gpu_layers`, cache types, flash attention, template
  override where a GGUF's embedded template is broken) and **every compatible manifest adapter
  pre-registered** via `--lora`, with `--lora-init-without-apply` so nothing is active until
  requested. `unload()` terminates the process; `list_resident()` reads the process table. The
  existing `Provider` protocol already has exactly these methods — the seam holds.
* **Hot-swap is per request:** the `lora: [{id, scale}]` request field selects among registered
  adapters. Selecting costs no reload; the base never moves.
* **A new adapter file requires a restart** — registration happens at launch. The registry marks
  a newly scanned adapter `pending_restart` and the provider folds it in at the next natural
  idle/unload, never mid-work. One restart per newly trained adapter is the honest floor.
* **Correctness obligations, named as conformance tests:** a KV/prompt-cache prefix computed
  under adapter A is never reused for adapter B (the cache key includes the adapter selection, or
  the cache is dropped on switch); requests with different adapter configs are not batched
  together (recorded; irrelevant at the suite's single-user concurrency); an unregistered adapter
  in a request is a typed `AdapterNotFound`, never a silent bare-base generation.
* **Capability honesty:** `ProviderCapabilities` gains `adapter_hot_swap`; llama.cpp declares
  `True`, Ollama and OpenAI-compatible declare `False`, and a request carrying an adapter to a
  provider that declares `False` is `CapabilityUnsupported` — the flag is load-bearing, like
  `context_configurable`.
* **What the suite takes over from Ollama** (accepted deliberately — self-managed files are
  visible and backupable): model file management and hashing (an identity-confidence *gain*),
  GPU-offload configuration (profile fields, conservative defaults, `doctor` checks), chat-template
  overrides, and process lifecycle. PEFT/safetensors adapters are converted to GGUF once, on drop,
  as part of the scan workflow.

## 6. Evidence: measured, never inherited (A-2)

A LoRA routinely *damages* capabilities it was not trained for; inheriting the base's evidence
would be a fabricated number — [ADR-0016](../adr/0016-unavailable-is-not-zero.md)'s bug class —
and [ADR-0037](../adr/0037-production-evidence-never-raises-capability-scores.md) already closes
the production-data shortcut. Therefore:

* A new adapter subject has **no evidence**. Every adapter is benchmarked before use — enforced
  by routing arithmetic, not policy (§7).
* FreeWeight's panel per adapter subject: the suites mapping to the manifest's
  `declared_capabilities` (the claim under test) **plus a fixed regression panel**
  (`instruction_following`, `structured_output`, and the base's strongest capability) to catch
  forgetting, **plus** the performance suite — tokens/sec with the adapter active is this
  subject's own number.
* The serving-mode A/B (§3) is measured once per base + profile, not per adapter.
* `CapabilityEvidence` gains optional adapter fields (SetSpec v1.1, the ADR-0032 additive
  precedent); records without them are exactly today's records.

## 7. Selection: the capability vocabulary, not tags (A-7)

There is no free-form tag channel — a second, unversioned vocabulary with no evidence linkage is
banned here for the same reason it is banned everywhere else. Instead, selection rides machinery
that already exists:

* Adapters **declare and are measured on namespaced capability specializations**
  (`coding.python`, `content.fact_check`) — permitted by the vocabulary's existing rules — and
  personal dimensions use the `user.*` namespace built for exactly this
  ([ADR-0031](../adr/0031-user-defined-goal-benchmarks.md)/[0032](../adr/0032-judge-validity-and-user-capability-namespace.md):
  a house-voice LoRA scored by a calibrated house-voice goal is the intended pairing).
* **Routed selection:** adapter subjects enter LoadCoach's candidate pool beside bare subjects
  and are scored by the ordinary filter → score → rank on their own evidence. A task profile that
  weights `content.fact_check` will rank the fact-check adapter above the bare base *because the
  measurements say so* — no new mechanism.
* **The gate:** a new hard constraint, `require_adapter_evidence` (default on): an adapter
  subject with no measured evidence for the profile's top-weighted capability is filtered with a
  named rejection. "No benchmark, no use" is thereby arithmetic plus one explicit constraint.
* **Pinned selection:** a caller may name an adapter (IdeaPress per-stage pins; a PromptCadence
  trajectory option) with the existing `model`-override semantics — bypasses scoring, **hard
  constraints still apply** (compatibility, classification, the evidence gate), recorded as an
  override in the explanation.
* LoadCoach still never reads content ([ADR-0040](../adr/0040-routing-backend-owns-model-choice.md)):
  intent arrives as a task profile, and the callers always know their intent — an IdeaPress stage,
  a PromptCadence plan step's `purpose` → task-profile mapping carried in its `ExecutionIntent`.
  The adapter choice within the profile is LoadCoach's, so PromptCadence's deviation taxonomy is
  untouched: no new intent field, no new category.

## 8. Residency and scheduling (A-9)

Residency becomes two-level: **(resident base process, registered adapter set)**. LoadCoach's
scoring reflects the real cost surface:

* A candidate on the **resident base with any registered adapter** is resident — the
  `prefer_resident_bonus` applies; switching adapters is free.
* A candidate requiring a **different base** carries a configurable `base_switch_penalty`
  (a process restart is the expensive event, and with a few bases and many adapters the router
  should camp on a base).
* The **mission-critical lever**: a per-request `ignore_residency` override zeroes the
  residency/switch terms for that call, recorded in the explanation like every override —
  "use the absolute best and pay the swap" is one flag, and traceable.
* [ADR-0038](../adr/0038-one-model-at-a-time-per-gpu.md) restated: the *base* is the unit that
  must fit; registered adapters count toward its footprint. IdeaPress's serialize-and-unload rule
  is taught the same distinction so per-stage adapter changes on one base never thrash.

## 9. Governance: an adapter is a distillate of its training data (A-8)

* Every manifest carries a `data_classification`. An adapter trained on confidential material is
  itself confidential.
* **Adapters are local-only artifacts in v1** — never uploaded to a remote endpoint; a would-be
  adapter egress is a recorded SpotCheck denial. Since adapters exist only behind local
  providers, the classification lattice is satisfied by construction at serving time, and the
  adapter's classification is still recorded on every turn/attempt that used it — for audit, and
  so the invariant is checkable rather than assumed.
* The effective classification of work is `max(caller's declaration, adapter's classification)` —
  recorded wherever classification is recorded.

## 10. Reliability attribution (A-10)

Reliability statistics and the circuit breaker key on the **subject**, not the base: a failing
`(base, adapterA)` is deprioritized and eventually broken *as that subject*; it never breaks the
bare base or its sibling adapters. The honest costs are named: per-subject sample counts fragment
(the 20-sample minimum is per subject), and cross-adapter attribution ("is the base failing?") is
deliberately not inferred in v1 — a human reads the per-subject rows the explanation already
shows.

## 11. Deliberately excluded from v1

* **Multi-adapter composition** (several LoRAs with scales on one request) — the identity becomes
  a weighted set and the evidence space squares; no current consumer needs it. One adapter at a
  time, at a fixed scale of 1.0 (A-6).
* **Remote adapter serving** — see §9.
* **In-suite training** — adapters arrive by directory drop; a training component is a future arc.
* **Automatic base-failure attribution across adapters** — see §10.
* **vLLM** — concurrency-oriented serving with no payoff on single-user hardware; the
  `Provider` seam keeps the door open.

## 12. Component impact, one line each

| Component | Change | Nature |
|---|---|---|
| BaseAiCore | `AdapterIdentity` + subject/canonical-form extension | Additive (0.4.x pre-M9-1.0, else 1.1.0) |
| SetSpec | `model.adapter_manifest` 1.0; `CapabilityEvidence` optional adapter fields (v1.1) | Additive minor |
| ModelRack | `LlamaCppProvider` (process supervision, adapter registration/selection), `adapter_hot_swap` flag, `AdapterNotFound`, conformance additions | Additive minor |
| SweatMeter · WeightsDB · MirrorWall · CutCtx · ToolYard · LoadLedger · SpotCheck | Nothing | — |
| LoadCoach | Generalized LC-E1; adapter registry rows + scan CLI; subject expansion, gate, pins; two-level residency; per-subject reliability | LoadCoach 1.1 |
| FreeWeight | Adapter subject enumeration; panels + regression panel; serving-mode A/B; evidence fields | FreeWeight 1.1 |
| IdeaPress | Per-stage adapter pins via the LoadCoach backend (direct/Ollama mode stays adapter-free); provenance columns | Minor |
| PromptCadence | Born adapter-aware (optional fields in turns, explanation, fake LoadCoach — joint Phase 0); routed adapters within tiers when evidence exists | Schema-level at birth |
