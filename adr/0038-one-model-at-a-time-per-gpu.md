# ADR-0038 — One model at a time per GPU: fit with room for context, or wait

**Status:** Accepted (2026-08-31)
**Extends:** [Master Architecture §5.2](../architecture/master-architecture.md),
[IdeaPress Spec §12](../apps/ideapress/spec.md),
[IdeaPress Workflows §6.2](../apps/ideapress/workflows.md).
**Relates to:** [ADR-0023](0023-runtime-profile-resolution.md) (served context, not the
advertised maximum), [ADR-0029](0029-queue-mechanics.md) (LoadCoach admission),
[ADR-0010](0010-queue-implementation.md) (no broker).

## Context

The suite's machine has one GPU. Two of the three applications already have a policy for it, and
[Master Architecture §5.2](../architecture/master-architecture.md)'s *inference concurrency* bullet
states both: FreeWeight allows exactly one GPU-bound benchmark workload at a time (concurrency
benchmarks being the deliberate exception), and LoadCoach allows a configured maximum of concurrent
executions, defaulting to 1 on a single-GPU machine.

**IdeaPress is named nowhere in that bullet.** That silence is the defect this record closes, and
it is not theoretical. IdeaPress's own default configuration binds two models —
`gemma4:12b` (7.6 GB) for `draft` and `qwen3.5:9b-q8_0` (10.7 GB) for every other model-using
stage — to a 16 GB card. The two do not fit together with room for their context. Worse, the
failure is **silent**: Ollama keeps a model resident until its `keep_alive` expires, so a workflow
that alternates bindings can sit at 18 GB of demand on a 16 GB card and degrade to CPU, or OOM,
without any error the application raises or records.

LoadCoach already implements the arithmetic this needs.
`domain/routing/constraints.py::estimate_vram` computes
`size_bytes × loading_overhead_factor + kv_bytes_per_token × served_context +
activation_overhead` — weights **plus room for the context actually served**, never the
descriptor's advertised maximum ([ADR-0023 §4](0023-runtime-profile-resolution.md)).
`device_fits` compares that against live free VRAM per device with a 512 MB `vram_headroom_bytes`
reserve; a resource-shaped rejection sends the job to `waiting_resources`, which releases the
lease; ageing raises effective priority so nothing starves; an idle resident is unloaded LRU to
make room; and an unknown estimate never fits unless the model is already resident. Admission
reads a **live** telemetry snapshot (`services/worker.py::admission_snapshot`), so VRAM another
application is holding is already subtracted.

## Decision

**Two models contending for one GPU must both fit — with room for their context — or the later one
waits. Where a queue exists, it waits by priority.**

This is a machine-wide policy, not a per-application preference. Concretely:

1. **LoadCoach is the reference implementation and already complies.** `estimate_vram` +
   `device_fits` + `waiting_resources` + ageing is exactly this policy with a queue behind it, and
   `max_concurrent_jobs` defaults to 1. Nothing changes there.

2. **IdeaPress serialises and unloads, and grows no queue.** Standalone IdeaPress must never
   acquire one: [Spec §3](../apps/ideapress/spec.md) forbids it routing algorithms, and "queued by
   priority" is meaningless for a single sequential workflow — a queue of one. Its obligation is
   narrower and absolute:
   * **One generation in flight, at one choke point.** Every stage — CLI, web route, stage runner —
     reaches a model through a single function, and that function serialises. There is no second
     door. Configuration: `[execution] max_concurrent_stages = 1`; a value above 1 is **refused at
     startup** with the reason, never silently accepted or clamped.
   * **Unload before switching.** When the next stage's binding names a different model from the
     resident one, the outgoing model is unloaded explicitly before the incoming one loads.
     ModelRack's provider protocol already ships `load`, `unload` and `list_resident`, and its
     Ollama adapter implements `unload` as `keep_alive: 0`. Configuration:
     `[execution] unload_before_model_switch = true`.
   * Serialising plus unload-on-switch means IdeaPress **alone** can never hold two models.

3. **A standalone application participates decentrally, without a broker.** Each application checks
   live free VRAM before it loads and waits — *with the numbers* — rather than loading optimistically.
   No coordinator, no lock service, no shared state: this satisfies
   [ADR-0010](0010-queue-implementation.md)'s no-broker constraint, and it is the only design that
   works when the applications are genuinely independent and any one of them may not be installed.
   For IdeaPress the preflight is **optional**, because `sweatmeter` is an optional extra
   ([Spec §5, §16](../apps/ideapress/spec.md)): with `ideapress[telemetry]` installed the preflight
   runs; without it the serialise-and-unload invariant above still holds on its own. Telemetry must
   not become a hard dependency in order to obtain this property.

4. **The residual risk is cross-application and is named, not solved.** FreeWeight benchmarking
   while IdeaPress drafts can still oversubscribe the card. Closing that needs every application to
   perform the free-VRAM preflight of point 3 — see *Consequences*.

### The estimator: recommendation

Applying point 3 in a second application means either duplicating `estimate_vram` or extracting it.
IdeaPress may not import `loadcoach` (`.importlinter` forbids it, and
[Spec §20 AC8](../apps/ideapress/spec.md) asserts it), so those are the only two options.

**Recommended: extract the estimator to a shared package** — `modelrack`, which already owns
`ResidentModel`, `RuntimeProfile` and the provider protocol the arithmetic reads, and which every
application already depends on. Consequences of each:

| Option | Consequences |
|---|---|
| **Extract to `modelrack`** (recommended) | One implementation, one set of golden values, one place ADR-0023's served-context rule is enforced. Costs: a `modelrack` minor release; LoadCoach's `domain/routing/constraints.py` becomes a thin adapter over it, which touches a 1.0 application's most-tested module; the extraction is a *move*, and a moving target breaks it (the same rule that governed the MirrorWall extraction). |
| **Duplicate in IdeaPress** | No package release, no LoadCoach change, ships immediately. Costs: two copies of a formula whose constants (`LOADING_OVERHEAD_FACTOR`, `ACTIVATION_OVERHEAD_BYTES`, the KV-precision table) will drift, and the drift will be silent — each copy keeps producing *a* number. This is precisely what the package layer exists to prevent, and a second copy makes the eventual extraction strictly harder. |

**This ADR does not perform the extraction.** It touches a published package and two 1.0
applications, and belongs to a phase scoped for it, not to a run building IdeaPress's beta.

## Alternatives considered

* **A machine-wide GPU lock (a file lock, or a broker).** Rejected: ADR-0010 forbids a broker, and
  a lock file shared between independently-installed applications is coordination state nobody
  owns — a stale lock after a crash strands the GPU, and the recovery logic is a distributed
  system in a directory.
* **Route everything through LoadCoach.** This would give one admission controller for the whole
  machine, and it is genuinely the better answer *when LoadCoach is installed*. Rejected as the
  policy because [Spec §3](../apps/ideapress/spec.md) makes "never requires LoadCoach" a product
  guarantee, and Gold Standards §2's first IdeaPress bullet is that a complete workflow runs with
  LoadCoach absent. LoadCoach remains the better path where it exists; it cannot be the only one.
* **Bind every stage to one model.** This makes the switch problem disappear and is a legitimate
  user choice — but spec §12's two-model default exists because prose drafting and structured
  extraction reward different models, and silently collapsing it would be a product decision taken
  by an implementation detail. The default stands; the reload cost is measured and reported so a
  user can decide.
* **Rely on Ollama's own eviction.** Rejected: Ollama evicts on `keep_alive` expiry, not on demand,
  so the overlap window is exactly the window in which both models are resident. The failure is
  silent, which is what makes it dangerous.

## Consequences

* IdeaPress gains `[execution]` with two keys and one startup refusal, one choke-point function
  every entry point uses, and an explicit unload before a model switch. The invariant is proven by
  a `-m live` test that polls `list_resident()` across a real stage switch and asserts it never
  returns more than one entry, and by a default-path test that asserts the unload happened *before*
  the load.
* Alternating `draft` and the structured stages costs an unload and a full reload each way. The
  demonstration batches stages by model so the reloads are few, and reports the measured cost so
  the two-model default can be re-decided on evidence.
* **FreeWeight is the open gap.** It serialises its own work but performs **no free-VRAM preflight
  before loading a model**: `estimate_vram`, `device_fits` and any free-VRAM read appear nowhere in
  its source, and `insufficient_vram` occurs exactly once in the repository — as a documented skip
  reason in `infrastructure/db/models_runs.py`'s docstring that **nothing ever sets**. A benchmark
  therefore loads whatever the run needs regardless of what another application is holding. Closing
  this requires point 3's preflight in FreeWeight's runner, and it depends on the estimator
  decision above.
* The policy is stated in the user's own terms and can be checked by a person: *two models
  contending for one GPU must both fit with room for their context, or the later one waits.*
