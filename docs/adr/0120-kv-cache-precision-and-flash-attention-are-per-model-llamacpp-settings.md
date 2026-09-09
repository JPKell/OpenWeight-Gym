# ADR-0120 — KV-cache precision and flash attention are per-model llama.cpp settings, and Ollama refuses them

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0023](0023-runtime-profile-resolution.md) (the runtime profile and its
resolution chain), [ADR-0017](0017-benchmark-confidence-and-freshness.md) (a differing profile
hash is a differing subject), [ADR-0007](0007-provider-abstraction.md) rule 2 (a provider never
claims what it cannot honour), [ADR-0074](0074-adapter-enabled-serving-is-a-runtime-profile-field.md)
(a launch-time fact belongs in the profile hash; a provider handed a profile it cannot serve
refuses), [ADR-0119](0119-model-servers-run-under-a-host-memory-cap.md) (the memory cap this
sits beside).
**Source:** Operator request, 2026-09-09: "I would like to be able to toggle flash attention and
quantizing the KV cache in both freeweight and loadcoach … per model … in Ollama and llama.cpp …
the run settings to be different with the quantized cache … Q8 and Q4." On learning Ollama cannot
honour either per model: "leave ollama alone, llama.cpp will be the recommended way to run."

## Context

`baseaicore.RuntimeProfile` has carried `kv_cache_precision` and `flash_attention` since Phase 1,
both hashed into `profile_hash`; FreeWeight's `runtime_profiles` table has both columns; ModelRack's
llama.cpp adapter translates them to `--cache-type-k/v` and `--flash-attn` at launch; LoadCoach's
`[runtime]` defaults expose both. What is missing is narrow: FreeWeight's `[runtime]` never let an
operator set them (its docstring says why — Ollama cannot honour them per request), and
LoadCoach's per-model override table has `context_size` only.

Ollama 0.32's request `Options` carry `num_ctx`, `num_gpu`, `use_mmap` and the sampling keys.
Flash attention and KV-cache type are `OLLAMA_FLASH_ATTENTION` and `OLLAMA_KV_CACHE_TYPE`, read
once by the daemon for every model it will ever load. A "per-model" setting on Ollama is
therefore either a lie the run records, or a second daemon per cache mode.

A quantized KV cache halves (`q8_0`) or quarters (`q4_0`) the cache's memory — the single largest
lever on which context a 16 GB card serves — and changes the model's numerics, so a run at `q8_0`
is not comparable to one at `f16`. That is exactly the property the profile hash exists to
separate.

## Decision

**KV-cache precision and flash attention are honoured per model on llama.cpp through the
existing runtime-profile chain; on Ollama they are refused by name; a quantized cache requires
flash attention; and a different precision is a different measurement subject.**

1. **FreeWeight `[runtime]` gains `flash_attention` (bool, unset) and `kv_cache_precision`
   (`"f16" | "q8_0" | "q4_0"`, unset).** They reach `RuntimeProfile` through `to_profile()` like
   `context_size` does, are overridable per run through the same `--runtime` / API `runtime`
   object, and land in `runtime_profiles` columns that already exist. No migration.

2. **LoadCoach's per-model override (`[runtime.models."<canonical id>"]`) gains the same two
   keys**, merged by the existing `_merge` in `domain/routing/subject.py` with the existing
   `_first` precedence: override, then task profile, then per-model, then `[runtime]` default.

3. **`q8_0` and `q4_0` require `flash_attention = true`.** llama.cpp cannot quantize the V cache
   without flash attention and keeps it at f16 silently otherwise, which would record a precision
   that was not served. Both applications refuse the combination at validation, naming both keys.
   The three precisions are the whole vocabulary; anything else is refused with the list.

4. **Either key set for an Ollama provider is refused by name**, at FreeWeight startup and at
   LoadCoach resolve time (a `route explain` rejection with the reason as data). Refused rather
   than ignored: a stored profile saying `q8_0` beside a server running f16 is the fabricated
   subject ADR-0007 rule 2 forbids. ModelRack's Ollama adapter keeps not translating them, as its
   docstring already states.

5. **A different precision or flash-attention state is a different `profile_hash`** and therefore
   a different column in FreeWeight's comparison and a different subject in LoadCoach's routing
   evidence (ADR-0017). Nothing averages across them. Every hash stored before this ADR is
   unchanged: both fields were `None` and `None` is dropped from the canonical JSON (ADR-0074 §2).

6. **Ollama is left at the daemon's f16 default and is not the recommended provider when cache
   precision matters.** The suite runs no second daemon, adds no "declared daemon setting" to be
   hashed as `assumed`, and does not touch `OLLAMA_KV_CACHE_TYPE` on the operator's behalf.

## Consequences

*Positive.* The 16 GB card serves 2–4× the context per model at a precision the run records.
Two models, or one model twice, can be measured at different cache precisions and the results
are kept apart by construction. The change is three config keys, one validation rule and one
override table — every underlying field, column, flag and hash already exists.

*Negative.* Ollama users get nothing here except a clear refusal; the memory cap (ADR-0119) is
their whole protection. `q4_0` on the K cache is known to degrade some models' long-context
recall; the suite does not warn, it measures — `native.long_context` at `q4_0` is the check.

*Neutral.* FreeWeight's `[runtime]` docstring that explained why these keys were absent is
rewritten to explain when they are refused instead.

## Alternatives considered

* **Declared daemon settings, hashed as `assumed`** (the operator writes what the Ollama unit runs
  into the provider registration). Honest, and the pattern context already uses; rejected by the
  operator as not worth carrying for a provider that is no longer the recommended one.
* **One Ollama instance per cache mode** on separate ports. Works, and is how an operator who
  insists can still do it by hand; rejected as suite machinery — it is "pick the instance", not
  "per model".
* **Infer flash attention from the precision** (set it silently when `q8_0` is chosen). Rejected:
  a silently changed second setting is the kind of coupling ADR-0023 keeps out of the profile.

## Revisit when

* Ollama's request `Options` or Modelfile gain `flash_attention` / `kv_cache_type` keys. Then the
  Ollama adapter translates them, rule 4 lifts, and this ADR is superseded.
* llama.cpp adds a precision beyond the three (e.g. `q5_1` for K only): extend the vocabulary
  in one place per application, with the same flash-attention rule.
