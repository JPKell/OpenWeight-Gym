# ADR-0062 — llama.cpp serves adapters, through a process the suite supervises

**Status:** Accepted (2026-09-02)
**Extends:** [ADR-0007](0007-provider-abstraction.md) (the `Provider` protocol and provider
capabilities), [Master Architecture §10](../architecture/master-architecture.md) (extension points),
[Adapter Identity and Serving §5](../architecture/adapter-identity-and-serving.md).
**Relates to:** [ADR-0038](0038-one-model-at-a-time-per-gpu.md) (residency and unload-before-switch),
[ADR-0055](0055-loadcoach-registers-providers-by-name-and-kind.md) (how it is registered beside
Ollama), [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the identity it must
verify), [ADR-0063](0063-one-adapter-at-a-time.md) (what a request may select).
**Source:** [Adapter roadmap §2, A-5](../roadmap/adapter-roadmap.md).

## Context

The arc's whole value is one warm base with several adapters selected per request and **zero base
loads between them**. Ollama, the suite's incumbent provider, has no per-request adapter mechanism
at all: an adapter reaches Ollama only by being baked into a Modelfile as a new model, which makes
every adapter switch a full base load. That is precisely the cost this arc exists to remove.

llama.cpp's server does have the mechanism — adapters registered at launch, selected per request by
a `lora` field, with no reload on switch. Taking it means taking what comes with it: the suite
spawns and supervises a process instead of talking to a daemon somebody else manages, and it
inherits model file management, GPU-offload configuration, chat templates and port allocation.

Some of that inheritance is a gain rather than a cost. Ollama identifies models by tag, which the
suite records as `name_only` confidence because a tag can be repointed. Self-managed GGUF files are
hashed, so identity becomes digest-bound — an identity-confidence *upgrade*, not a compromise.

The rest is genuinely new risk for a package three applications depend on: orphaned processes,
ports, crashed servers, and a prompt cache that must never reuse a prefix computed under one adapter
for a request running under another.

## Decision

**A new ModelRack provider, `LlamaCppProvider`, serves adapters by supervising one `llama-server`
process per base. Ollama stays, unchanged, for zero-ops adapter-free serving.**

1. **One base per process, through the existing seam.** `Provider.load(identity, profile)` *spawns*
   `llama-server` with the base GGUF, the profile's flags (`n_gpu_layers`, cache types, flash
   attention, template override where a GGUF's embedded template is broken) and every compatible
   manifest adapter pre-registered via `--lora`, with `--lora-init-without-apply` so nothing is
   active until requested. `unload()` terminates the process; `list_resident()` reads the process
   table. **The `Provider` protocol does not change** — it already has exactly these methods, and
   that is the evidence the seam was drawn in the right place.
2. **Hot-swap is per request.** The `lora` request field selects among registered adapters.
   Selecting costs no reload; the base never moves.
3. **A new adapter file requires a restart, and takes it politely.** Registration happens at launch,
   so a newly scanned adapter is marked `pending_restart` and folds in at the next natural idle or
   unload — **never mid-work**. One restart per newly trained adapter is the honest floor, and it is
   surfaced to the caller rather than hidden.
4. **Correctness obligations, as named conformance tests**, not as intentions:
   * a KV/prompt-cache prefix computed under adapter A is **never** reused for adapter B — the cache
     key includes the adapter selection, or the cache is dropped on switch;
   * requests with different adapter configurations are not batched together (recorded; irrelevant
     at this suite's single-user concurrency, and stated so it stays true if that changes);
   * an unregistered adapter in a request is a typed `AdapterNotFound` — **never a silent bare-base
     generation**.
5. **Capability honesty.** `ProviderCapabilities` gains `adapter_hot_swap`: llama.cpp declares
   `True`, Ollama and OpenAI-compatible declare `False`, and a request carrying an adapter to a
   provider that declares `False` is `CapabilityUnsupported`. The flag is load-bearing, exactly like
   `context_configurable` — callers branch on it rather than on a provider's name.
6. **What the suite takes over, deliberately:** model file management and hashing (an
   identity-confidence gain — digest-bound rather than tag-based), GPU-offload configuration (profile
   fields, conservative defaults, `doctor` checks), chat-template overrides, and process lifecycle
   including kill-tree on timeout, pid files and a configured port range.

## Alternatives considered

**vLLM.** The strongest technical alternative and not a straw man: it has first-class multi-LoRA
serving, mature per-request adapter selection, and far better throughput under concurrent load.
Rejected because every one of those advantages is a *concurrency* advantage, and this deployment is
one user on one GPU — there is no payoff to collect. Against that it brings a heavyweight Python
serving runtime with tight CUDA coupling into a package that must install cleanly for three
applications on machines that may have no GPU at all. The `Provider` seam keeps the door open, and
the trigger for opening it is a concurrency profile this suite does not have.

**Wait for Ollama to add per-request adapters.** Zero new code, and it keeps one provider.
Rejected: it is a bet on someone else's roadmap for the arc's central capability, with no fallback
if the answer is no or late. Ollama remains registered and remains the default for adapter-free
work, which is the part of it that is genuinely better.

**Bake each `(base, adapter)` pair as its own Ollama model.** This works *today*, with no new
provider, no process supervision and no ports — a real, shippable option. Rejected on all three
counts that matter: every adapter switch becomes a full base load/unload, which is the exact cost
the arc exists to eliminate; each baked model duplicates the base's weights on disk, so four
adapters cost four copies of a 9 GB model; and identity reverts to a tag, losing the content
addressing [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) depends on. It is the
version of this feature that looks like it works and provides none of its value.

**Run `llama-server` as an externally managed service** (systemd, or the operator's own script) and
talk to it over HTTP like any endpoint. Genuinely attractive: no orphans, no kill-tree, no port
allocation, no startup-failure diagnosis — all of the risk section disappears. Rejected because the
suite would lose `unload()`. Residency management and
[ADR-0038](0038-one-model-at-a-time-per-gpu.md)'s unload-before-switch rule depend on the suite
being able to free the GPU, and a base switch would become an operator action. A provider that
cannot unload cannot participate in the one-model-per-GPU policy, which on a single-card machine is
not optional.

**Fall back to bare-base generation when a requested adapter is unregistered.** Superficially
forgiving. Rejected: it answers with the wrong subject and says nothing, which is the failure mode
every identity rule in this arc exists to prevent. `AdapterNotFound` is typed and loud.

## Consequences

* ModelRack gains process supervision — genuinely new territory for the package, and the reason its
  LA1 phases carry leak tests (20 load/unload cycles, no orphan, flat memory), kill-tree on timeout,
  pid files, a configured port range, and stderr captured into the typed startup error.
* Recorded fixtures for the llama.cpp server are **version-annotated**, exactly as Ollama's are, and
  the tested server version is pinned in the documentation. The conformance suite runs for all four
  providers with capability-gated skips made explicit.
* Adapter-capable serving becomes available only where `adapter_hot_swap` is `True`, and every
  consumer branches on the flag. A deployment with only Ollama registered behaves exactly as it does
  today.
* `pending_restart` is a state operators will meet: a freshly scanned adapter is not usable until the
  base restarts. It is surfaced in `adapters list` and by `doctor`, with the reason, rather than
  producing an adapter that mysteriously cannot be selected.
* The suite now owns GGUF files, their hashes and their serving flags for llama.cpp bases. That is
  more configuration surface than Ollama required, and it buys digest-bound identity —
  `identity_confidence = digest` where Ollama gives `name_only`.

## Revisit when

* **llama.cpp gains runtime adapter registration** — the `pending_restart` machinery is then dead
  weight and should be deleted rather than kept "just in case". It would also dissolve the premise of
  [ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md), whose serving-mode
  fact exists because registration is a launch-time property.
* **The llama.cpp server API breaks compatibility** — the version-annotated fixtures are what make
  that a visible test failure rather than a silent behaviour change, and the response is the same one
  the Ollama adapter takes: pin, record, adapt in one place.
