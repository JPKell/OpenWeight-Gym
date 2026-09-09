# ADR-0121 — FreeWeight launches llama-server with `--fit off` and caps the max-fit ladder; LoadCoach keeps `--fit on`

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0119](0119-model-servers-run-under-a-host-memory-cap.md) (the memory cap),
[ADR-0023](0023-runtime-profile-resolution.md) (`provider_options` are hashed profile content),
[ADR-0017](0017-benchmark-confidence-and-freshness.md) (a differing ladder is a differing
measurement), [ADR-0066](0066-residency-is-two-level.md) (silent CPU degradation is the failure to
end), [ADR-0016](0016-unavailable-is-not-zero.md).
**Source:** Operator decision, 2026-09-09, after the `--fit` semantics were laid out
(`MEMORY_SAFETY.md` §5): "`--fit off` for FreeWeight only"; and "yes, add ceiling + ADR" for the
`memory_kv.max_context_fit` ladder.

## Context

`llama-server --fit on`, its default, adjusts **only arguments the caller left unset** so that
weights plus KV cache fit device memory minus a margin. The suite passes `--ctx-size` whenever the
profile sets a context, so `fit` never shrinks a set context; it shrinks `--n-gpu-layers`, which
the suite leaves unset, and the displaced layers go to host RAM. The server starts, the run
proceeds, decode is 5–20× slower, and the layer split — which is not reported by `/props` and not
part of the profile — differs between two machines with the same `profile_hash`.

`native.memory_kv`'s `max_context_fit` test climbs a fixed ladder, `8192 … 131072`, "until
something refuses" (catalog §3.2), and records the first refusal as the maximum context the
machine serves. Against a server that fits instead of refusing, the ladder never ends in a
refusal; it ends in a spill. The ladder's ceiling is a module constant; `native.long_context`'s
ladder, by contrast, is truncated to `benchmarks.long_context_max_tokens` and that ceiling is
hashed into the suite's `dataset_hashes`.

The two applications want different things from a server that does not fit. A benchmark wants
the truth about the launch it recorded; an agent loop wants tokens.

## Decision

1. **`memory_kv.max_context_fit`'s ladder is truncated to `benchmarks.max_fit_context_tokens`**
   (default `131072`, the current top rung; `ge=8192`), exactly as `long_context_max_tokens`
   truncates `native.long_context`: the effective ladder is hashed into `dataset_hashes`, so a
   sweep capped at 32 k and one capped at 131 k are two measurements and never one average. The
   derived metric `max_context_capped_by_configuration` already exists for this reading and now
   has a configuration to read.

2. **FreeWeight launches every `llama-server` with `--fit off`.** The flag travels as
   `provider_options["--fit"] = "off"` on the resolved profile, set from a new `[runtime]` key
   `fit_to_device` (bool, default `false`), so it is hashed like every launch-time fact (ADR-0023,
   ADR-0074 §1). Every `profile_hash` stored before this version is unchanged: those runs launched
   without the key, llama-server's default was `on`, and the key's absence keeps meaning that. A
   profile that does not fit fails at launch with ModelRack's typed error naming the model and the
   argv; the sample is stored as failed at that context, which is the OOM measurement the catalog
   asks for and the refusal the ladder in decision 1 climbs toward.

3. **LoadCoach keeps llama-server's `--fit on`.** For a served request a model that runs slowly
   on a partial offload beats one that does not run; the host is protected by the memory cap
   (ADR-0119), not by refusing to launch. LoadCoach does not record the served layer split — it is
   a runtime fact outside the profile — and does not pretend to. An operator who wants LoadCoach
   to fail rather than spill sets `provider_options = { "--fit" = "off" }` on the profile.

4. **The Ollama path is unchanged by this ADR.** Ollama has no equivalent flag; its protection is
   the daemon cap and `benchmarks.max_fit_context_tokens` set to what the card serves.

## Consequences

*Positive.* A FreeWeight llama.cpp run's launch matches its recorded profile or does not happen.
`max_context_fit` measures what it was written to measure, in seconds per rung rather than a
machine per rung. LoadCoach's behaviour for its consumers does not change.

*Negative.* Two providers, two `fit` behaviours, documented in one place (`MEMORY_SAFETY.md` §5)
because they will otherwise be rediscovered. A FreeWeight operator who wants to measure a model
that only fits with partial offload sets `runtime.gpu_layers` explicitly — `fit` no longer
guesses it for them.

*Neutral.* `fit_to_device = true` is an explicit opt-in back to the llama-server default, hashed
as such; it exists so the setting has a name rather than a hidden constant.

## Alternatives considered

* **`--fit off` everywhere.** The operator's first-listed option; rejected for LoadCoach because
  its consumers (IdeaPress, PromptCadence) would see a model vanish from routing rather than slow
  down, with no evidence recorded either way.
* **Leave `--fit on` in FreeWeight and read the served split.** llama-server does not report the
  split, so it cannot be hashed; the subject would still drift silently.
* **A hidden constant instead of `fit_to_device`.** Rejected: a launch flag that changes the
  measurement is profile content, and profile content has a name in config.

## Revisit when

* `llama-server` reports the served `n_gpu_layers` in `/props`. Then the split can be recorded
  and hashed, and decision 2 could relax to "record what fit did" for FreeWeight as well.
