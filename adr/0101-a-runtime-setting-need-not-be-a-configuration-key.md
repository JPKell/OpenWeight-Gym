# ADR-0101 — A runtime setting need not be a configuration key, and the ones that are not say so

**Status:** Accepted (2026-09-07)
**Amends:** [Configuration standards §7](../standards/configuration-standards.md) (which describes
database-backed settings only as configuration keys that a UI may also change) and
[§8](../standards/configuration-standards.md) (the generated reference, whose tables are walked
from the settings model).
**Relates to:** [ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)
(the registry pattern, and rule 5's precedence),
[LoadCoach api.md §9](../apps/loadcoach/api.md) (the registry this record describes),
[ADR-0010](0010-queue-implementation.md) (the database-backed queue whose pause and drain these
two keys are).
**Source:** Row I8, while fixing LoadCoach's precedence. The kickoff's decision D1 asked whether
`queue.paused` and `queue.draining` should be exempt from the environment-beats-a-row rule; the
answer turned out to depend on a fact neither the standards nor api.md records.

## Context

Configuration standards §7 describes runtime-changeable settings as configuration keys with an
extra layer: `defaults → file → database → env → CLI`. Every sentence of it — the precedence
chain, the "never editable from the UI" rule, the `(database)` mark on `config show` — assumes the
key exists in the settings model, has an environment variable, and appears in the generated
`docs/configuration.md` (§8).

**Two of LoadCoach's seven runtime-changeable keys do not.** `queue.paused` and `queue.draining`
are members of `loadcoach.services.settings.RUNTIME_SETTINGS`, are served by `GET /settings`, are
rendered on the Settings page, and are re-read by the scheduler every second — but `QueueSettings`
has no `paused` and no `draining` field. They exist **only** in the `settings` table. The
consequences were all live and none was written down:

* `_configured()` reaches them through `getattr(section, field, False)` and its default, so their
  "configured value" is a fallback rather than a configured anything.
* `LOADCOACH_QUEUE__PAUSED=true` is not a lower-precedence layer that a stored row beats. It is an
  **unknown configuration key**: `load_settings()` raises `ConfigurationError` and the server
  refuses to start.
* They have no row in `docs/configuration.md`, because the reference walks
  `Settings.model_fields`. An operator reading the generated reference cannot discover them there
  at all; they appear only in api.md §9 and on the page.

Row I8 asked whether these two should be exempt from §7's precedence — the worry being that
`LOADCOACH_QUEUE__PAUSED=true` in a unit file would make the console's pause button store a row
that silently did nothing. It cannot: that variable stops the server instead. The question was
answerable only by reading the settings model, which is exactly the sign of a shape the standards
do not name.

The alternative — adding `paused` and `draining` to `QueueSettings` so every registry key is a
configuration key — was considered and refused. It would make `LOADCOACH_QUEUE__PAUSED` valid for
the first time, and with it the failure D1 feared: an operator pauses dispatch from the console,
the row is shadowed by a variable in a unit file, and the queue keeps running with no explanation
on the page unless the operator reads the shadow line. Making a shape uniform by creating the
hazard it was uniform against is not a repair. A pause is also **operational state**, not
configuration: it is what an operator did to this installation a minute ago, not how this
installation is set up.

## Decision

**A runtime-changeable setting may exist without a configuration counterpart. Where it does, that
is a property of the registry entry, stated in the registry and surfaced everywhere the key is,
and the one precedence rule still applies to it unchanged.**

1. **The registry is the authority on which keys exist, not the settings model.** A registry entry
   whose `key` names no field of `Settings` is legal and means: this value lives only in the
   `settings` table. Nothing else about it differs.

2. **One precedence rule, no per-key exception** (ADR-0100 rule 5, and configuration standards §7).
   `shadowing_source` is consulted for a configuration-less key like any other and always answers
   `None`, because no variable can name it without the loader refusing to start. The rule costs
   nothing here and a second rule would cost a branch nobody would remember.

3. **The generated reference says they exist and why they are absent from its tables.** §8's tables
   are walked from the model and stay that way — inventing rows for keys with no environment
   variable and no default would publish a variable that cannot be set. Instead the reference's
   header names the configuration-less keys and states that no `LOADCOACH_QUEUE__PAUSED` exists
   and that a variable of that name is refused as an unknown key.

4. **`config show` does not mark them.** It renders the settings model; a key that is not in the
   model has no line to mark. `GET /settings` and the Settings page are where these keys are
   inspected, and both report `stored`, `source` and `shadowed_by` for them exactly as for the
   rest.

5. **A configuration-less key is operational state, and that is the test for admitting one.**
   `queue.paused` and `queue.draining` are what an operator did to this installation, not how it
   is set up. A *tuning number* — a threshold, a retry count, a retention window — belongs in the
   settings model and gets a file layer and a variable, because an operator provisioning a machine
   should be able to set it before the first start. If a proposed runtime key would sensibly
   appear in `config.toml`, it goes in the model; if setting it in a file would be meaningless,
   it may live in the table alone.

## Alternatives considered

* **Add the two keys to `QueueSettings`.** Uniform, and it makes the reference tables complete. It
  also creates the shadowing hazard described above, and it invites an operator to bake a pause
  into a unit file, which is a queue whose state nobody can explain. Refused.
* **Exempt the flags from §7's precedence instead** (row I8's D1, the losing branch). A per-key
  exception to a published standard, written to prevent a failure that cannot occur. Refused.
* **Say nothing and let the code speak.** The reference's silence is what made D1 unanswerable
  without reading the model; the next transcription of this registry — there have been three —
  would rediscover it. Refused.
* **Forbid the shape: every runtime key must be a configuration key.** Clean, and it is what the
  standards implicitly assumed. It would require the two flags to move out of the registry into
  their own control surface with their own state machine, which ADR-0100 already refused to invent
  for PromptCadence. Refused as more machinery than the fact deserves.

## Consequences

* The registry gains an implicit second class of entry. A reader of `RUNTIME_SETTINGS` must
  check the settings model to know which class an entry is in, unless the entry says so. The
  cheapest form of "says so" is prose in the reference header, which is what this release ships;
  a `RuntimeSetting` field carrying the fact would be better and is the natural first change if a
  third such key appears.
* `_configured()`'s `getattr(..., False)` default is now load-bearing rather than defensive, and it
  hard-codes `False` as the configured value of every configuration-less boolean. That is correct
  for a pause and a drain — an installation starts running — and would be wrong for a key whose
  off state is not the neutral one.
* PromptCadence and FreeWeight have no configuration-less keys, so this record describes LoadCoach
  alone today. It is written at suite level because the registry pattern is transcribed between
  the three applications and the next transcription should carry the rule rather than rediscover
  the exception.
* `docs/configuration.md` is no longer a complete list of what a running LoadCoach will answer for
  — it is a complete list of what may be **configured**. `GET /settings` is the complete list of
  what may be changed at runtime. Two documents, two questions, and the reference now says which
  is which.

## Revisit when

A third configuration-less key is proposed, or one is proposed in an application other than
LoadCoach. At that point the fact belongs in `RuntimeSetting` as a field the registry declares and
the reference renders, rather than in prose one generator's header happens to carry. Also revisit
if a configuration-less key is ever wanted whose neutral state is not the type's zero value — the
`getattr` default would have to become an explicit declaration first.
