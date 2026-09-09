# ADR-0127 — Every application publishes its settings schema, and WeightRoom generates the settings form from it

**Status:** Accepted (2026-09-09)
**Amends:** each application's `config` CLI group ([FreeWeight spec §7.2](../apps/freeweight/spec.md),
[LoadCoach spec §7.2](../apps/loadcoach/spec.md), [IdeaPress spec §7.2](../apps/ideapress/spec.md),
[PromptCadence spec §7.2](../apps/promptcadence/spec.md)) with two verbs, `config schema` and
`config validate --file`.
**Relates to:** [ADR-0117](0117-provider-registrations-are-edited-in-place-in-the-config-file.md)
(the in-place, comment-preserving, validate-before-write edit this record applies to the whole
file from outside the application), [ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)
(the runtime-changeable registry each application already keeps and this record publishes),
[Configuration Standards §4, §7, §8](../standards/configuration-standards.md) (schema and
validation; runtime-changeable precedence; the generated configuration reference this record
reuses the source of), [ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
rule 2 (config edits are in the exception).
**Source:** the operator interview of 2026-09-09, decision D9.

## Context

Each application's configuration is a pydantic `Settings` model behind a layered loader —
`defaults → file → database → env → CLI` — with a `config show` that names every leaf's source, a
`config validate`, a generated `docs/configuration.md` produced **from the model** and
diff-checked in CI ([Configuration Standards §8](../standards/configuration-standards.md)), and a
registry of runtime-changeable keys with bounds that `PUT /settings`, the settings page, the CLI
and the reference all read ([ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)).
Everything a settings form needs already exists in each application, and none of it is reachable
from outside the application's process.

WeightRoom wants to render a settings form for each application, write the file in place with
comments kept, use the application's own validation, and change runtime-changeable keys without a
restart. Hard-coding the four key sets into WeightRoom would be a fifth copy of each application's
configuration surface, wrong the week after any of them adds a key — the precise drift the
generated reference was built to prevent.

## Decision

**Each application publishes its settings schema as a versioned JSON document from its own CLI,
and validates a candidate file on request. WeightRoom generates its settings forms from that
document and hardcodes no key.**

1. **`<app> config schema --json`** prints one document, `schema_version = "1.0"`, from the
   same objects the application already keeps:

   ```json
   {
     "schema_version": "1.0",
     "application": "loadcoach",
     "version": "1.3.0",
     "env_prefix": "LOADCOACH_",
     "config_path": "/home/op/.config/loadcoach/config.toml",
     "json_schema": { "...": "Settings.model_json_schema()" },
     "runtime_changeable": [
       {"key": "routing.min_confidence", "kind": "float", "minimum": 0.0, "maximum": 1.0,
        "description": "..."}
     ],
     "security_keys": ["server.host", "server.port", "providers.allow_remote", "..."],
     "config_only": ["storage.retain_content", "..."],
     "sources": {"server.port": "file", "routing.min_confidence": "database (shadowed by env)"}
   }
   ```

   `json_schema` is pydantic's output for `Settings`, descriptions included — the same source
   `docs/configuration.md` is generated from. `runtime_changeable` is the registry, verbatim.
   `security_keys` is the set `PUT /settings` refuses as `403 FORBIDDEN` by name. `config_only`
   is every other non-runtime key. `sources` is `config show`'s per-leaf layer, so a value pinned
   by the environment is reported as such and WeightRoom can mark the field *shadowed* rather
   than let an edit that will not take effect look like it did. An unknown key path in the
   application's own file is reported under `problems`, never dropped.

2. **`<app> config validate --file <path>`** loads an arbitrary candidate file through the
   application's own `load_settings` — the same parse, the same validation, the same security
   refusals — and exits 0 or non-zero with the message validation produced. Without `--file` the
   verb keeps its present meaning. This is [ADR-0117](0117-provider-registrations-are-edited-in-place-in-the-config-file.md)
   rule 4's check, made callable by another process.

3. **WeightRoom renders the form from the document and edits the file in place.** Field type,
   bounds, description, default and current value come from `json_schema` and `sources`; sections
   follow the model's nesting. A key the document does not describe is shown raw, as TOML, never
   invented. A write is `tomlkit`'s round-trip (comments, order and formatting of every untouched
   line preserved), validated through rule 2 before it lands, written beside, `fsync`ed, renamed
   over the original with the previous file kept as `config.toml.bak`, and refused whole if the
   file changed on disk since the form was read (the ADR-0117 rule 7 race, closed the same way).
   Every write is an `audit_log` row naming the keys that changed.

4. **Runtime-changeable keys go through the application, not the file.** A key in
   `runtime_changeable` is written with `PUT /api/v1/settings` on the running application and
   takes effect on the application's own schedule (its next lease reap, its scheduler's next
   second); the file is not touched for it, so the file keeps saying what the operator configured
   and the application keeps saying what it is running ([Configuration Standards §7](../standards/configuration-standards.md)).
   A stopped application has no runtime path, and the form says so and offers the file.

5. **Every other key needs a restart, and the form offers it.** After a successful file write the
   page shows *restart <app> to apply* with the [ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
   button; a write that is not followed by a restart is shown as *pending restart* until one
   happens, so a configured-but-not-running value is never mistaken for an applied one.

6. **Security keys are editable, re-authenticated and audited.** ADR-0117 rule 3 kept the egress
   boundary config-only *for a browser session on the application*; WeightRoom's session is the
   operator's, with a shell's reach ([ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
   rule 2). A change to any key in `security_keys` — the bind, the exposure flag, `allow_remote`,
   the database URL, the data roots, content retention — requires the operator's password again
   (a five-minute re-authentication window, sudo-style), names the key on the confirmation, and is
   an audit row that says *security key*. The boundary a browser session cannot move on the
   application is one a re-authenticated operator can move here, and every such move is written
   down.

7. **The four rows that add the verbs are WS1–WS4** in
   [`roadmap/weightroom-work.md`](../roadmap/weightroom-work.md), one per application, each with a
   golden test of the document and a contract test that WeightRoom's form generator renders it.
   The document is a SetSpec-shaped payload in spirit — versioned, additive minors — but it is
   application-local and not a `setspec` schema: only WeightRoom reads it, and a fifth consumer is
   the trigger for promotion.

## Consequences

*Positive.* WeightRoom's settings forms cannot drift from the applications, because there is
nothing in WeightRoom to drift: a key added to an application appears in the form on the next
schema read. The applications' own validation runs on every write, so a file WeightRoom writes
is a file the application would have accepted from `$EDITOR`.

*Negative.* Four applications gain two CLI verbs and a document to keep stable. The document is
built from objects that already exist and already have tests, so the cost is the verb and its
golden, per application.

*Negative.* `config show`'s per-leaf `sources` becomes a machine-read contract rather than a
human display; a format change there is now a minor bump of the document.

*Neutral.* PromptCadence's precedence fix ([ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)
decision 5) and LoadCoach's (row I8) mean both report a shadowed row the same way; the document
carries what each application says, and WeightRoom shows it without reconciling.

## Alternatives considered

* **Hardcode the four key sets in WeightRoom**, from the specs. Rejected: a fifth copy that the
  generated reference exists to prevent.
* **Read each application's `docs/configuration.md`** and parse the table. Rejected: a document
  for people, generated from the model; ask the model.
* **Import each application's `Settings` class.** The most direct source, and forbidden:
  ADR-0123 rule 3, and the reason it gives — an import binds to the version.
* **Refuse security keys from WeightRoom as the applications do.** Rejected by rule 6's
  reasoning: the operator would edit the file in a shell instead, unaudited, which is worse.

## Revisit when

* **A fifth consumer of the schema document appears** (a configuration linter, a second console).
  Promote the document to a `setspec` payload with goldens.
* **An application's `Settings` stops being pydantic.** Rule 1's `json_schema` needs a new source.
