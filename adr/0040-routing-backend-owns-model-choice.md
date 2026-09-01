# ADR-0040 — A routing backend owns model choice and residency

**Status:** Accepted (2026-08-31)
**Extends:** [IdeaPress Spec §12](../apps/ideapress/spec.md),
[IdeaPress Workflows §6](../apps/ideapress/workflows.md).
**Relates to:** [ADR-0038](0038-one-model-at-a-time-per-gpu.md) (one model at a time per GPU),
[ADR-0027](0027-admission-control.md) (LoadCoach admission), risk I2 (coupling through
convenience).

## Context

[ADR-0038](0038-one-model-at-a-time-per-gpu.md) made `InferenceGateway` the single door to a model
and gave it two obligations: resolve the stage's `[models.stages]` binding and pass it down as
`model_hint`, and unload the resident model before a different one loads. Both are correct for a
backend IdeaPress drives directly — Ollama, or an OpenAI-compatible endpoint — because in those
modes IdeaPress *is* the thing that chooses and loads models.

Neither is correct for LoadCoach, and the gateway has no way to tell the difference.

[Spec §12](../apps/ideapress/spec.md) already states the intent — the bindings are "ignored in
loadcoach mode unless overridden" — but nothing implements it, and P7 is the first phase in which
that silence produces behaviour. With the *shipped default* configuration, setting
`inference.mode = "loadcoach"` would:

1. resolve `models.stages.draft = "ollama/gemma4:12b"` like any other mode, and set it as
   `model_hint`;
2. have the adapter send that as `overrides.model` — [Workflows §6.1](../apps/ideapress/workflows.md)
   says `model_hint` is "sent as an override only when the user pinned one", and the adapter cannot
   distinguish a user's pin from a default binding the gateway resolved on its own — pinning every
   request to one model and bypassing LoadCoach's task profiles, its capability evidence, its
   reliability factor and its admission control **entirely**; and
3. call `unload()` for a model IdeaPress does not own and cannot evict, then record a
   `model_switch` degradation describing an eviction that did not happen.

The failure mode is the dangerous shape: **every stage still succeeds.** Nothing raises, nothing is
logged at WARNING, the parity test passes, and the provenance record is truthful about which model
answered. The integration would look like it worked while delivering none of what it exists for —
and (3) would put a fabricated eviction into a provenance record a person is meant to trust, which
is the same offence [ADR-0016](0016-unavailable-is-not-zero.md) exists to forbid.

Requiring the user to empty `[models.stages]` before switching modes is not available either:
[Spec §20 AC2](../apps/ideapress/spec.md) is that switching `inference.mode` needs **no** change
beyond the mode.

## Decision

**A backend that performs its own model selection owns model choice and residency. IdeaPress
supplies the task, not the model.**

1. **The port says which kind it is.** `BackendCapabilities` gains `routes_internally` (default
   `False`). `LoadCoachBackend` reports `True`; every other adapter keeps the default. It is a new
   field rather than a reinterpretation of `model_selection`, which every adapter reports `True` for
   and which means something else — *a model can be named* — and is also true of LoadCoach.

2. **No binding is resolved, and none is required.** When the backend routes internally the gateway
   passes `model_hint` through as it received it. `ModelNotConfigured` cannot arise from a mode
   whose bindings the specification documents as ignored, and a LoadCoach user is never made to
   name eleven Ollama models they do not have.

3. **No residency management.** No `unload`, no `model_switch` degradation. ADR-0038 §1 already
   names LoadCoach the reference implementation of the one-model-at-a-time policy: it has the
   estimator, the live telemetry snapshot, the `waiting_resources` transition and the LRU eviction.
   IdeaPress reaching in from outside would be a second, blind controller of the same card.

4. **An override is opt-in and explicit.** `[inference.loadcoach] honour_stage_bindings`
   (default `false`) is the mechanism spec §12's "unless overridden" names. Set it, and the stage's
   binding is sent as `overrides.model`; leave it, and LoadCoach routes. The default is the one
   that makes the integration worth having.

5. **A pin is a request, not a guarantee.** When a model override was sent and the model that
   answered is a different one, that is recorded on the attempt as a
   `model_override_not_honoured` degradation naming both — never a stage failure. This follows
   [Workflows §6.2](../apps/ideapress/workflows.md) throughout: the honest report of a thing that
   did not go as asked, rather than either pretending it did or refusing to continue.

## Alternatives considered

* **Overload `model_selection`.** Rejected: it currently means "a model can be named", every
  adapter reports `True`, and LoadCoach can be given one too. Changing its meaning would alter
  three adapters' honest self-reports to encode a fourth adapter's routing policy.
* **Send the binding as an override always.** This is the defect, stated as a design.
* **Require `[models.stages]` to be empty in loadcoach mode.** Rejected: it breaks AC2, and it
  makes moving a project between modes a configuration rewrite rather than a one-line change.
* **Have the adapter ignore `model_hint` unconditionally.** Rejected: it removes the user's ability
  to pin a model through LoadCoach at all, which is a capability LoadCoach deliberately exposes
  (`overrides.model`), and it would silently discard an explicit instruction — the same class of
  fault in the opposite direction.

## Consequences

* `BackendCapabilities` gains a field. It is an IdeaPress-internal port
  ([Spec §11](../apps/ideapress/spec.md) contract 1), not a wire contract, so no version changes.
* `InferenceGateway` gains one branch and keeps its single-choke-point property intact; the
  serialising semaphore is unchanged and still applies in every mode.
* Spec §12's "unless overridden" gains the mechanism it names; workflows §6.1 and §6.2 gain
  `honour_stage_bindings` and the `model_override_not_honoured` degradation.
* ADR-0038's residual cross-application risk is unchanged: in LoadCoach mode IdeaPress holds no
  model, so it cannot oversubscribe the card by itself, and LoadCoach's admission control sees the
  live snapshot.
* A future backend that routes internally — a hosted router, a second queue — sets one flag rather
  than discovering this problem again.
