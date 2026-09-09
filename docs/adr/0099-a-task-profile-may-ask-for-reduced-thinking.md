# ADR-0099 — A task profile may ask for reduced thinking, and routing enforces that it can be asked

**Status:** Accepted (2026-09-06)
**Amends:** [LoadCoach api.md §2](../apps/loadcoach/api.md) (every `GET /models` entry carries
`provider_name` and `is_remote`) and [§4](../apps/loadcoach/api.md) (`sampling.think`);
[LoadCoach routing.md §2](../apps/loadcoach/routing.md) (the execution block's `think`) and §5
(the `capability_unsupported` row).
**Relates to:** [ADR-0075](0075-a-request-carrying-tools-requires-tool-use-of-every-candidate.md)
(the request-imposed hard constraint this one copies), [ADR-0055](0055-loadcoach-registers-providers-by-name-and-kind.md)
rule 4 (`remote` is declared, never inferred), [ADR-0098](0098-promptcadence-1-0-ships-with-remote-tiers-refusing-honestly.md)
rule 1 and its Correction (the reader this render exists for),
[ADR-0007](0007-provider-abstraction.md) rule 2 (a declared capability is reachable).
**Source:** Row I3 — the two halves of one patch release: I2 §5's correction (the render) and
G2 §5's finding, seen again at I2 §10 run 1 (the lever).

## Context

Two findings, one release.

**(a)** LoadCoach 1.1 records `provider_name` and `is_remote` on every model row (migration `0008`)
and renders both on the `model` block of every `/generate` response. `GET /models` renders neither.
ADR-0098 rule 1 reads exactly that listing, so on a real 1.1.0 the remote-provider fact reads
`False`, a remote registration is invisible until its first turn, and every PromptCadence remote
tier stays `loadcoach_has_no_remote_provider` — the honest refusal, and wrong by omission.

**(b)** gpt-oss:20b under `response_format = "json"` spends its whole output budget reasoning and
returns nothing: 1 in 6 at 4 096 tokens and 3 in 6 at 8 192 on `tools.plan` (G2 gate E), and once
on `tools.agent.local_fast` at 4 096 with all 4 096 tokens reasoning and no text (I2 §10 run 1).
G2 proved the output budget is not the lever — doubling it tripled the latency and doubled the
failure rate — and named the lever: a thinking control. H1 built it in ModelRack
(`SamplingParameters.think`, tri-state; Ollama sends its own top-level `think`, llama.cpp and
OpenAI-compatible raise `CapabilityUnsupported` naming `thinking_control`). G2 refused to add a
profile field for a control that could not be sent — *configuration that lies*. It can be sent now.

## Decision

**Every `GET /models` entry carries `provider_name` and `is_remote`, and a task profile's
`execution` block may carry `think`, which routing enforces before a model is chosen.**

1. **The listing renders both fields, under the names the generate response already uses.**
   `provider_name` and `is_remote` at the top level of each entry, `""` and `false` reading as
   *not recorded* for a row discovered before registrations had names. `loadcoach models list
   --json` carries them too, so the CLI and the API say the same thing about a model. No response
   model is added to `GET /models`: the endpoint returns an untyped mapping, `docs/openapi.json`
   describes no entry field at all, and typing it now to make a snapshot move would change a 1.0
   contract's schema for fields the JSON already carries.

2. **The field is `TaskProfileExecution.think: bool | None = None`** — ModelRack's name, ModelRack's
   three states. Unset or `null` builds a `SamplingParameters` byte-identical to 1.1.0's; `false`
   asks for reasoning suppressed; `true` asks for it.

3. **`sampling.think` on `POST /generate` overrides the profile**, exactly as `sampling.temperature`
   and `sampling.max_output_tokens` do, and is refused with a `VALIDATION_ERROR` when it is neither
   a boolean nor `null`. A caller that may override the budget may override the control that
   decides what the budget is spent on; PromptCadence can then measure a tier without a profile
   edit.

4. **A `think` that is set requires `thinking_control` of every candidate, at routing.** The
   rejection is `capability_unsupported` with `details.capability = "thinking_control"`,
   `details.provider_kind` and `details.required_by` — `"request"` when `sampling.think` set it,
   `"task_profile"` when the profile did. It is ADR-0075's mechanism, one rejection reason,
   evaluated in the same loop.

5. **`thinking_control` does not enter `requires_capabilities`.** That field is validated against
   the SetSpec capability vocabulary (`is_known_capability`; routing.md §2: *a profile may not
   reference a capability outside the SetSpec vocabulary*), and `thinking_control` is not in it —
   it is a **provider** flag on `ProviderCapabilities`, while the vocabulary's neighbouring
   *model* flag is `thinking`. So the requirement travels as its own input to the constraint
   evaluator, `ProviderFacts` gains `supports_thinking_control` beside its four siblings, and the
   two vocabularies stay separate. An operator writing `requires_capabilities =
   ["thinking_control"]` is still refused at import, as they were yesterday.

6. **A profile's `version` bumps when its *values* change, not when its comments do.** The
   precedent is `5af6b12`, which rewrote `tools.plan`'s comment with G2's numbers and kept
   `1.0.0`. A shipped profile that gains a `think` value ships at `1.1.0`, so a `routing_decisions`
   row written before this release still names the definition it ran under; a profile whose only
   edit is the measured comment keeps its version.

7. **What the five harness profiles ship with is the measurement's call, not this record's.** The
   field exists and is reachable from configuration either way; the row's handoff and the
   `tools.plan` comment carry the four-cell table that decided it.

## What this refuses

* **Sending a control the wire cannot carry, or dropping one the profile set.** G2 §5's rule in
  both directions: never a request that quietly differs from its profile. The alternative —
  letting the request go out and mapping `CapabilityUnsupported` to a permanent attempt failure —
  is honest and useless: a profile with `think = false` on a llama.cpp-only deployment would fail
  every job after a model had already been chosen, which is exactly the shape ADR-0075 exists to
  prevent.
* **Dropping the key silently when the provider cannot carry it.** Configuration that lies.
* **A second vocabulary for a three-state fact.** A string enum
  (`reasoning = "off" | "on" | "default"`) would name in LoadCoach what ModelRack already names,
  and the house rule is *same concept, same name across the suite*. A record written under it
  would have had to claim the two spellings meant the same thing, and every future reader would
  have had to check.
* **Inferring the remote fact from a provider kind.** ADR-0055 rule 4; `openai_compatible` is both
  local and remote.

## Consequences

* PromptCadence's `ProviderSurface` reads a true `is_remote` from a real LoadCoach the day this
  ships, with no PromptCadence change — ADR-0098's Correction said so and this is it.
* PromptCadence's two hash-pinned LoadCoach snapshots (`tests/contract/loadcoach_openapi.json`,
  `tests/contract/loadcoach_task_profiles.toml`) stop matching the shipped files the moment a
  profile changes. Refreshing them is a PromptCadence change, in its own row; nothing in this one.
* `ProviderFacts` gains a fifth support flag, and every construction site that states a provider's
  shape in one line keeps working — the default is `False`, which is what a provider that has not
  declared the capability means.
* A deployment whose only registration is llama.cpp cannot set `think` on any profile without
  every candidate being rejected with a named reason. That is the intended, visible outcome.

## Revisit when

A provider gains a *degree* of thinking control rather than a switch (a token budget, an effort
level). Three states stop being enough then, and the replacement is a new record — not a widened
boolean.
