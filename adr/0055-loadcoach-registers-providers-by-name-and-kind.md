# ADR-0055 — LoadCoach registers providers by name and kind, into one tagged registry

**Status:** Accepted (2026-09-02)
**Extends:** [LoadCoach Spec §12](../apps/loadcoach/spec.md) (configuration),
[LoadCoach Routing §5](../apps/loadcoach/routing.md) (candidate pool and constraints),
[Master Architecture §7](../architecture/master-architecture.md).
**Relates to:** [ADR-0007](0007-provider-abstraction.md) (the `Provider` protocol this rests on),
[ADR-0008](0008-canonical-model-identity.md) (kind, not address, is part of identity),
[ADR-0040](0040-routing-backend-owns-model-choice.md) (the router owns model choice),
[ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) (the second local
runtime this exists to admit), [ADR-0013](0013-api-versioning.md) (additive within `/api/v1`).
**Source:** [PromptCadence roadmap §2, D-11](../roadmap/promptcadence-roadmap.md) (LC-E1,
generalized 2026-09-01); [Adapter roadmap §4.2](../roadmap/adapter-roadmap.md).

## Context

LoadCoach 1.0 configures exactly **one** provider: a `[provider]` block with a kind and a base
URL. Every model it knows about comes from that one place, which was right when Ollama was the only
runtime and remote endpoints were a future.

Two independent needs now arrive at the same wall. PromptCadence's remote tiers are defined as
LoadCoach task profiles that route to a remote endpoint — and there is no way to register one
beside the local provider, so every remote tier is unservable. And the adapter arc needs a second
**local** runtime: llama.cpp, for hot-swappable LoRA serving, standing beside Ollama rather than
replacing it, because Ollama remains the zero-ops choice for adapter-free work.

The original LC-E1 was scoped as *remote-provider registration*, and that scoping is the thing this
record corrects. Written remote-first, the configuration would have grown a `[remote_provider]`
block and a set of remote-specific behaviours, and three weeks later the adapter arc would have
needed a second local one — un-designing the flag rather than using it. The generalization is not a
feature addition; it is the recognition that "how many providers" and "is it remote" are two
different questions that the single-provider design had conflated.

Everything downstream already speaks the right language. Routing's `allow_remote` constraint, the
cost adjustment factor and the egress badge all exist and all mean what they say; what is missing is
only a way for more than one provider's models to reach them.

## Decision

**LoadCoach gains additive, provider-kind-agnostic registration: named provider blocks, one model
registry, every model tagged by its provider and its egress class.**

1. **`[providers.<name>]` blocks.** Each names a provider `kind` (`ollama`, `llamacpp`,
   `openai_compatible`), its connection settings, and a `remote` flag. Names are operator-chosen and
   are what explanations, the models UI and the doctor refer to.
2. **Backwards compatible.** The existing single `[provider]` block remains valid and is read as one
   registration. A LoadCoach 1.0 configuration keeps working untouched; this is LoadCoach **1.1**,
   additive within `/api/v1`, with no breaking change to any request, response or stored row.
3. **One registry, tagged — not one registry per provider.** Discovery from every registered
   provider enters the same model registry, and each model carries its provider name, its provider
   kind and its egress class. Filtering, scoring, ranking, residency and reliability are unchanged
   code operating on a larger pool. This is what lets adapter subjects sit beside bare subjects in
   one candidate list ([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)).
4. **`remote` is a property of the registration, not of the kind.** An OpenAI-compatible endpoint on
   loopback is local; the same kind pointed at a hosted API is remote. The flag is what feeds
   `allow_remote`, the cost factor and the egress badge, and it is declared rather than inferred
   from a URL.
5. **Two providers serving the same weights are two subjects, correctly.** `provider_kind` is part
   of model identity ([ADR-0008](0008-canonical-model-identity.md): kind rather than address,
   because templating, sampling defaults and KV handling differ), so a model served by both Ollama
   and llama.cpp appears twice, with separate evidence. That is not duplication to be deduplicated —
   it is the honest consequence of measurements not being interchangeable.
6. **Owned by the LoadCoach repository**, shipped as LoadCoach 1.1. It is the only code change to a
   shipped application in the PromptCadence arc, and the adapter arc's LA2 builds on it.
7. **Until it lands, remote tiers refuse honestly.** PromptCadence reports `TIER_UNAVAILABLE` with
   the reason `loadcoach_has_no_remote_provider` — specified behaviour with a documented reason, not
   a gap.

## Alternatives considered

**Keep one provider per LoadCoach and run two instances.** Zero code change, real process
isolation, and it ships today. Genuinely tempting for the remote case in particular. Rejected: two
instances means two queues and **two independent admission controllers contending for one GPU**,
which is precisely the residual cross-application risk
[ADR-0038](0038-one-model-at-a-time-per-gpu.md) names and does not solve. It also pushes the choice
of instance onto the caller, and choosing which instance to call is routing — performed by the
component that [ADR-0040](0040-routing-backend-owns-model-choice.md) says must not perform it.

**Ship LC-E1 as originally scoped: remote-provider registration only.** This was the plan, and it is
smaller. Rejected on the evidence of what happened next: within three weeks a second *local* runtime
became a requirement, and a remote-specific configuration key would have had to be widened or
duplicated. The generalization costs one flag and removes a distinction that was never the real one.

**Bind a provider per task profile.** Superficially neat: `tools.agent.remote_cheap` names the
remote provider, and tier configuration becomes provider configuration. Rejected: it pins the
provider — and therefore narrows model choice — by configuration, which is ADR-0040's defect
arriving through a different door, and it makes a mixed candidate pool impossible, so a profile
could never compare a local and a remote model on their merits.

**Separate registries per provider, merged at scoring time.** Rejected: it duplicates constraint
evaluation, residency accounting and reliability tracking across registries, and the two copies
drift. One pool with tags is strictly less code and is what the existing filter/score/rank already
expects.

**A provider plugin system** — providers discovered from entry points or declared in configuration
by import path. Rejected for [ADR-0053](0053-a-refused-tool-call-is-a-result-not-an-exception.md)'s
reason applied to providers: a provider is a ModelRack adapter, which is reviewed code with a
conformance suite, not a configuration value. Registration names a *kind* the suite ships, and
adding a kind is a ModelRack release.

## Consequences

* LoadCoach 1.1 gains named provider registration, per-model provider and egress tags, and a
  `doctor` that names every configured provider and reports each one's reachability separately.
  Nothing downstream of the registry changes meaning.
* PromptCadence's remote tiers become servable, and the adapter arc gains its second local runtime —
  from one change, which is the argument for generalizing it.
* Model lists get longer and can contain apparent duplicates (the same weights under two providers).
  The models UI groups by identity and shows the provider, and the explanation always names which
  one was selected; the alternative — hiding the duplication — would merge two measurement subjects
  that are not comparable.
* An operator can now misconfigure `remote = false` on a hosted endpoint and defeat the egress
  machinery. That is a genuine new footgun: the flag is a declaration and nothing verifies it from
  the URL. The compensating control is PromptCadence's verification contract — the executing
  provider on every response is checked against the tier that requested it, and a mismatch is a
  recorded `VIOLATION` and a halt ([ADR-0054](0054-spotcheck-records-egress-it-does-not-enforce-it.md)).
* This is the arc's only change to a released 1.0 application, and it is scheduled where a mixed
  pool can be verified once (LA2), rather than twice from two arcs.

## Revisit when

A provider appears that the ModelRack `Provider` protocol cannot express — one whose lifecycle,
selection surface or streaming shape does not fit `load`/`unload`/`generate`/`stream`/`list_resident`.
Registration is only as general as the protocol behind it, and that would be a decision about the
protocol, not about configuration.
