# ADR-0118 — A discovered model can be disabled

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0055](0055-loadcoach-registers-providers-by-name-and-kind.md) (the discovery
pass that writes these rows), [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)
rule 4 (a pin that cannot be honoured is refused by name, never quietly re-routed),
[ADR-0117](0117-provider-registrations-are-edited-in-place-in-the-config-file.md) (the provider
admin this is reached from).
**Source:** Operator request, 2026-09-09: "I would like the ability to disable models so that not
every model that is discovered can be used."

## Context

Discovery writes a registry row for every model a registration reports, and routing considers all of
them. A row carries `available` and `unavailable_reason` — facts the *provider* reported, refreshed
on every pass — and the `model_unavailable` hard constraint rejects a candidate on them. There is no
way for an operator to say "this one is real, reachable and healthy, and I do not want it used":
a model pulled for one experiment, a quantization that measured badly, a base whose licence the
operator will not run work under. The registry has no room for that sentence, and the file has no
room for it either — a denylist of `provider/name@sha256:…` strings in `config.toml` is a list of
digests no human maintains.

## Decision

**A registry row carries an operator's `enabled` flag, and it is the only thing that sets it.**

1. **`models.enabled`, boolean, default true** — LoadCoach migration `0015`, FreeWeight migration
   `0009`. Written only by an operator, through the models page or the CLI. **Discovery never
   writes it:** a pass upserts every other column and leaves this one alone, so a disabled model
   that vanishes from the provider and comes back is still disabled.

2. **`enabled` is not `available`, and neither is derived from the other.** `available = false` is a
   fact about a provider at a moment. `enabled = false` is a decision by a person, with no expiry.
   Both are shown, separately, with their own words; a disabled model that is also unreachable reads
   as both, because collapsing them would lose which one an operator has to act on.

3. **Routing rejects a disabled candidate by name, before availability.** A new hard constraint
   `model_disabled` is evaluated ahead of `model_unavailable`, so an explanation of why a model was
   not chosen says a person excluded it rather than blaming an incidental provider state. It appears
   in the explanation like every other rejection: named, with the reason as data.

4. **An explicit request for a disabled model is refused, never re-routed.** Naming one in a
   request, a pin or a benchmark subject is an error naming the model and the flag — ADR-0064 rule
   4's treatment of a pin that cannot be honoured, applied to the one case where the obstacle is a
   human's decision. Silently substituting another model would be the worst possible reading of an
   operator's exclusion.

5. **Disabling hides nothing and deletes nothing.** The row, its evidence, its reliability history
   and its past decisions all stay. Re-enabling restores exactly what was there; the flag is a gate
   on future use, not a retraction of past measurement.

6. **FreeWeight honours the same flag for the same reason.** A disabled model is not offered as a
   benchmark subject and is skipped by a sweep that would otherwise measure every discovered model.
   The applications each own their own column — no application reads another's database — and mean
   the same thing by it.

## Consequences

* One column, one constraint, one checkbox per application. The registry gains an operator's
  intention it could not previously express, and the decision log gains a rejection reason that
  names a person instead of a machine state.
* An operator can now empty the candidate pool from a browser. That is the point, and routing
  already answers an empty pool with an explanation listing every rejection and its reason, so the
  outcome states its own cause.
* A disabled model still appears in `GET /models`, still shows its evidence, and still costs a row.
  Deleting a model remains something only discovery's absence and retention can do.
