# ADR-0075 — A request carrying tools requires `tool_use` of every candidate

**Status:** Accepted (2026-09-04)
**Relates to:** [ADR-0041](0041-caller-schemas-do-not-travel-through-a-router.md) (a caller's
schema is passed through, never validated — the rule this record inherits for a tool's
`parameters`), [ADR-0007](0007-provider-abstraction.md) (a provider declares what it can
do and is refused what it cannot), [ADR-0016](0016-unavailable-is-not-zero.md) (an absent fact is
not a permissive one).
**Source:** G1's real-stack evidence (`docs/history/handoffs/G1_HANDOFF.md` §9.3) and row G2 of
[`docs/roadmap/outstanding-work.md`](../roadmap/outstanding-work.md).

## Context

LoadCoach's `/generate` now accepts `tools` on the request body ([api.md §4](../apps/loadcoach/api.md)).
Routing already understands `tool_use`: it is in the SetSpec capability vocabulary, five shipped
task profiles require it, and `domain/routing/constraints.py` rejects a candidate whose provider
has not declared it.

What did not exist is a rule for a request whose *body* carries tools while its *task profile*
requires nothing. `general.chat` and `tools.plan` are both such profiles. Without a rule, three
outcomes were possible and only one of them is honest:

1. Route as if the tools were not there, and let the tools reach a provider that cannot use them.
   ModelRack raises `CapabilityUnsupported` at the provider edge — an error that names a
   capability, not a candidate, arriving after routing has already chosen and after the caller has
   been told which model was selected.
2. Route as if the tools were not there, and drop them. The model is never told the tools exist,
   answers as best it can, and the caller cannot tell from the response that its offer was
   discarded. This is the silent failure G1 lived through from the other side: gpt-oss:20b invented
   `repo_browser.list_dir` because nothing told it what existed.
3. Treat the tools as a statement of what the request needs, and filter candidates on it.

## Decision

**A `POST /generate` (or `POST /jobs`) body with a non-empty `tools` imposes `tool_use` as a hard
constraint on that request**, unioned with whatever the task profile's
`requires_capabilities` already names. It is a filter and never a score: no weight moves, no
candidate is preferred for supporting tools, and a request without tools routes exactly as it did
before.

1. **The rejection is `capability_unsupported`**, routing's existing reason — not a new one. Its
   `details` carry `capability: "tool_use"` and `required_by`, which is `"request"` when the body's
   tools imposed it and `"task_profile"` when the profile did. Rejection reasons are a
   caller-visible vocabulary; adding a reason string for the same fact seen from a different angle
   would grow that vocabulary for nothing, while a caller reading `NO_ELIGIBLE_MODEL` still needs
   to know that it was *their own request* that narrowed the field.
2. **When nothing survives, the error is `NO_ELIGIBLE_MODEL`** with every candidate and its reason,
   as it already is for every other hard constraint. A caller that sent tools to a machine whose
   only provider cannot use them is told so before a model is chosen.
3. **`tools: []` is identical to `tools: null` and to the field's absence.** An empty list offers
   nothing, so it constrains nothing. A caller that computed an empty tool set gets exactly the
   request it would have sent without the field — including its routing.
4. **A tool's `parameters` is passed to the provider unmodified and LoadCoach never executes a
   call.** ADR-0041's rule, inherited verbatim from ModelRack's spec §14. LoadCoach is a router;
   a sandbox inside it would be an architecture breach, not a feature.

## Consequences

* The provider-edge `CapabilityUnsupported` becomes unreachable through `/generate`: routing
  refuses first. It stays as ModelRack's own guard for callers that are not LoadCoach, and a test
  asserts the rejection happens at routing rather than at the provider.
* A caller cannot use `tools` to *loosen* anything. The constraint is a union with the profile's,
  and `_merged_constraints`' refusal to loosen is untouched.
* Because the constraint is request-level rather than profile-level, `tools.plan` — which requires
  `structured_output` and not `tool_use` — keeps routing to a model chosen for structured output,
  right up until a caller offers it a tool, at which point both apply.
* A machine with no tool-calling provider serves every tool-free request exactly as before. Only
  requests that ask for tools are narrowed, which is the property that makes this additive within
  `/api/v1`.

## Alternatives considered (added 2026-09-07)

* **Let the tools reach whatever model routing chose.** The status quo before this record, and the
  cheapest. Rejected on G1's evidence from the other side: a model told about tools it cannot call
  invents names out of its own vocabulary, so the failure arrives after a model was chosen, as
  refused calls the caller has to interpret.
* **Drop `tools` silently for a candidate that cannot use them.** Every request still succeeds.
  Rejected: it is the same failure with the evidence removed — the caller offered tools, none were
  offered to the model, and nothing in the response says so.
* **Make `tool_use` a preference rather than a filter** — score candidates that support it higher.
  Rejected: a soft constraint means a caller that sent tools sometimes gets a model that cannot use
  them, non-deterministically, depending on the rest of the score. A capability a request depends on
  is not a tie-break.
* **Require the task profile to declare `tool_use` instead.** Rejected: it makes a caller's request
  depend on another application's configuration file — the coupling ADR-0041 exists to refuse — and
  `tools.plan` is the counter-example, a profile that legitimately requires `structured_output` and
  not `tool_use` right up until a caller offers it a tool.
* **Add a `tools_unsupported` rejection reason.** Rejected: rejection reasons are a caller-visible
  vocabulary, and this is `capability_unsupported` seen from a different angle. `required_by`
  carries the difference in `details`, which is where a distinction that is not a new fact belongs.

## Revisit when (added 2026-09-07)

* **A provider supports tool calling for some of its models and not others.** The constraint is
  evaluated against `ProviderCapabilities`, so a per-model flag would make the filter answer for the
  provider when the question is about the model — and `NO_ELIGIBLE_MODEL` would name the wrong
  candidates.
* **A second tool-related capability is needed** — parallel calls, streamed calls, a tool-choice
  mode. One flag currently stands for "can use tools at all"; the first request that needs more
  than that reopens whether `tool_use` is one capability or a family.
* **A caller wants "use tools if you can" semantics.** That is a different request, not a loosening
  of this one, and it needs its own field rather than a weakening of the constraint — but it is the
  ask most likely to arrive, so the shape should be decided when it does rather than by whoever
  implements it.
