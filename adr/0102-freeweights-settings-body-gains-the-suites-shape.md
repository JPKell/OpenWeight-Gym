# ADR-0102 — FreeWeight's settings body gains the suite's shape, and `items` is deprecated

**Status:** Accepted (2026-09-07)
**Amends:** [FreeWeight API §8](../apps/freeweight/api.md) (`GET`/`PUT /api/v1/settings`, whose
response body gains two fields and deprecates one).
**Relates to:** [ADR-0013](0013-api-versioning.md) (additive-only within a major version, which is
the rule that decided the *how*), [ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)
(the vocabulary being adopted), [ADR-0101](0101-a-runtime-setting-need-not-be-a-configuration-key.md)
(the other shape question the same registry raised), [Configuration standards §7](../standards/configuration-standards.md).
**Source:** Row I8/I9's fourth finding — three applications holding three near-copies of one
registry — and the operator's decision at the 2026-09-07 interview to converge FreeWeight onto the
other two rather than leave the divergence recorded.

## Context

Three applications now serve a runtime-settings surface built on the same idea and no shared code:
a registry of changeable keys, a refusal for everything security-relevant, and configuration
standards §7's precedence with a stored row between file and environment. LoadCoach's was first,
PromptCadence transcribed it (ADR-0100) and corrected its precedence, and row I8 transcribed the
correction back. FreeWeight's was written independently and is the odd one out.

The divergence is in the **wire shape**, not the behaviour:

| | LoadCoach / PromptCadence | FreeWeight |
|---|---|---|
| body | `{settings, definitions, config_only}` | `{items: [...], config_only}` |
| per key | `configured`, `stored`, `source`, `shadowed_by` | `value`, `stored_value`, `source`, `overridden_by_env`, `env_var` |
| `source` values | `"database"` / `"configuration"` | `"env"` / `"database"` / `"file or default"` |
| `kind` | a Python type's name | a string, with a fourth value `"choice"` |
| extras | — | `unit`, `choices` (its page renders both) |

FreeWeight's precedence was already right — it computes `from_env` and reports
`overridden_by_env`, which is exactly what LoadCoach lacked until 1.1.2. What it did not have was
the *vocabulary*, so an operator moving between two of the three consoles meets two spellings of
one fact, and a fourth transcription of this registry would have two models to choose between.

**The obvious repair is forbidden.** Rewriting `GET /api/v1/settings` to return
`{settings, definitions}` is a breaking change to a `v1` response, and ADR-0013 is unambiguous:
within a major version changes are additive only, and a breaking change creates `/api/v2` with
`/api/v1` served and deprecated for at least one minor release. Standing up a second API major in
FreeWeight for one endpoint's field names is disproportionate to what is being fixed.

## Decision

**The body carries both renderings. `settings` and `definitions` are added in the suite's
vocabulary; `items` is unchanged, deprecated, and removed when FreeWeight next has an
`/api/v2`.**

1. **`settings`** maps each runtime-changeable key to the value work started from now on will use.
2. **`definitions`** maps each key to `type`, `description`, `minimum`, `maximum`, `configured`,
   `stored`, `source` (`"database"` or `"configuration"`) and `shadowed_by`
   (`"env FREEWEIGHT_…"` or `null`) — LoadCoach's and PromptCadence's field names, meaning for
   meaning — **plus** `unit`, `choices` and `env_var`, which FreeWeight's page needs and the other
   two have no use for. Extra fields in a definition are additive there too, if either ever grows
   a setting with a unit.
3. **`items` does not change at all.** Not its field names, not its `source` vocabulary, not
   `overridden_by_env`. A deprecated field that quietly changes meaning is worse than one that
   stays put: a consumer reading it keeps reading exactly what it read before.
4. **`configured` requires the loaded settings to survive.** FreeWeight applied stored values over
   its settings object during startup and kept only the result, so "what was configured" was no
   longer answerable. The lifespan now keeps the pristine object beside the applied one — the same
   discipline ADR-0100 required of PromptCadence's composition root — and `configured` and
   `effective` are two different facts again.
5. **`settings` is computed from the row, not read off the applied object.** `items[*].value`
   reports the value folded in when the process started; a row written since then is what the next
   run will use. The new field applies `apply_stored`'s own rule at read time, so it agrees with
   the `source` and `stored` beside it. That disagreement between the two renderings is real, it
   is in `items`' favour of nothing, and it is one of the reasons `items` is the one deprecated.
6. **Removal is at `/api/v2`**, whenever FreeWeight next needs one, and not before. There is no
   scheduled date: a deprecation with a removal *version* and no removal *deadline* is what
   ADR-0013's "at least one minor release" permits, and this field costs one list comprehension to
   keep.

## Alternatives considered

* **Rewrite the v1 body.** What the operator asked for, and the direct reading of "converge".
  Refused: it breaks ADR-0013's additive-only rule for a change with no user-visible benefit, and
  `freeweight 1.0.0` on PyPI serves the old shape to anything already reading it.
* **Stand up `/api/v2` now.** Standards-compliant and clean, and it would let `items` die
  immediately. Refused as disproportionate: a second router, a deprecation window and translation
  logic, so that one endpoint can rename four fields.
* **Converge the other two onto FreeWeight.** Refused, and it is the worse direction:
  `promptcadence 1.1.0` has published `{settings, definitions}` to PyPI, `loadcoach 1.1.2` was
  prepared with it hours before this decision, and api.md §9 documents it. Two breakages instead
  of one, against the shape two applications already share.
* **Align the vocabulary inside `items` only** — rename `stored_value` to `stored` and swap the
  `source` values. Smaller, and still a breaking change to a v1 response: the same rule forbids it,
  with less delivered.
* **Extract the registry into a layer-3 package** and let all three consume it. Refused for now,
  and separately from this record: an abstraction over three registries with three refusal
  policies, two `kind` vocabularies and two response shapes is the kind that ages badly. This ADR
  removes the *shape* half of that objection; if a fourth application wants one, the case is
  better then than it is now.

## Consequences

* FreeWeight serves the same answer twice until its next API major. That is duplication on the
  wire, deliberately, in exchange for not breaking a published contract.
* The two renderings can disagree about the effective value of a key changed since startup
  (rule 5). Both are honest about different instants; the document's own docstring says which is
  which, and only the deprecated one reports the older instant.
* FreeWeight's console still renders `views` — `items`' underlying objects — so the page is
  unchanged by this record. It moves to `definitions` when `items` is removed, not before, so this
  release changes no template.
* A fourth transcription of this registry now has one wire shape to copy rather than two. The
  remaining divergences are internal: a string `kind` with a `"choice"` variant, `unit` and
  `choices`, and FreeWeight's allowlist-based refusal — which is *stronger* than the other two's
  blocklist-plus-registry and is the direction they should eventually move, not this one.
* FreeWeight still raises at startup on a stored row it cannot coerce, where LoadCoach and
  PromptCadence fall back to configuration and keep serving. That robustness difference is real,
  is not addressed here, and is worth its own row.

## Revisit when

FreeWeight needs an `/api/v2` for any reason — that is when `items` goes, and the console moves to
`definitions` with it. Revisit sooner if a fourth application grows a runtime-settings surface, at
which point the shared-package question should be asked again with the shape half already settled.
