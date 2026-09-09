# ADR-0117 — Provider registrations are edited in place in the config file

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0055](0055-loadcoach-registers-providers-by-name-and-kind.md)
(the named registration this edits), [ADR-0077](0077-a-named-provider-block-and-the-singular-block-are-one-registry.md)
(the singular `[provider]` form, which this must edit as faithfully as the plural one),
[ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md) (the runtime-changeable registry this
does *not* extend), [ADR-0114](0114-the-dependency-budget-is-the-enumerated-set-a-component-declares.md)
(the enumerated set `tomlkit` is added to here), [standards/configuration.md](../standards/configuration.md)
§7 (the precedence chain a stored value would have sat in).
**Source:** Operator request, 2026-09-09: configure the provider for each application from the web
admin.

## Context

A provider registration is `[providers.<name>]` in the application's `config.toml`, parsed into
`ProviderRegistrationSettings` and turned into a live provider exactly once, by
`build_registrations` at startup. Nothing rebuilds it while the server runs, and nothing writes it:
`PUT /settings` refuses every key outside the runtime-changeable registry, and FreeWeight's settings
page states the reason plainly — a security boundary a browser session can move is not a boundary.
Migration 0008 recorded the other half of the same position: a registration is configuration, not
data, which is why a discovered model records the *name* it was served by instead of a foreign key
into a table.

The operator wants to add, edit and remove registrations from the web admin, and has said which
property matters most: the file stays the source of truth, and its comments survive. That rules out
both of the obvious designs.

A **database overlay** — registrations stored as a structured settings row, merged over the file at
`file → database → env` — reuses the machinery ADR-0100 already built and needs no new dependency.
It is rejected because it makes the file a half-truth: the operator opens `config.toml`, reads a
registration, and the running system is serving a different one, with nothing in the file saying so.
Configuration standards §7 tolerates that for a scalar an operator can see reported as *shadowed* on
the settings page. A provider — the thing that decides where a prompt goes and whether it leaves the
machine — is not a scalar anyone should have to cross-reference a second surface to read.

A **plain rewrite** — parse with `tomllib`, re-serialise the whole document — loses every comment
and all formatting in a file that is written by hand and read by hand. An operator who edits a
provider in the browser and loses the paragraph explaining why the remote one exists has been
punished for using the feature.

## Decision

**`config.toml` remains the single source of truth for provider registrations, and the web admin
edits it in place.**

1. **Comment- and format-preserving round-trip.** The file is read and written with `tomlkit`, which
   keeps comments, key order, spacing and string style for every part of the document the edit does
   not touch. `tomlkit` joins LoadCoach's and FreeWeight's declared dependency sets under ADR-0114
   §3, and `gold-standards` §1.1 lists it for those two components and no others.

2. **Only the provider subtree is writable.** An edit may create, change or delete a
   `[providers.<name>]` table, or the singular `[provider]` block (ADR-0077) in an application that
   uses that form. Every other key in the file — the bind address, the exposure flag, auth tokens,
   the database URL, the data roots — is untouched by construction, and naming one is `403
   FORBIDDEN` naming the key, exactly as `PUT /settings` already answers.

3. **`providers.allow_remote` stays config-only.** It is the egress boundary, not a registration, so
   it keeps the answer FreeWeight's settings page gives today. A registration declaring `remote =
   true` may be added from the browser and is then *inert*: routing refuses it until a human edits
   the file to allow remote providers at all. The boundary a browser session cannot move is the one
   that decides whether work leaves the machine, not the one that names the machines.

4. **A write is validated before it lands.** The candidate document is loaded through the
   application's own `load_settings` — the same parse, the same validation, the same security
   checks — and a document that fails is refused with the message that validation produced, leaving
   the file untouched. A write that passes is an atomic replace (write beside, `fsync`, rename) with
   the previous file kept as `config.toml.bak`.

5. **The running server re-registers, and does not restart.** After a successful write the
   application rebuilds its registrations from the reloaded settings and rebinds them, so the change
   is live on the next request. Nothing else in `Settings` is re-read: a value the process captured
   at startup keeps whatever it captured, and the page says so.

6. **An environment variable still wins, and is reported.** `LOADCOACH_PROVIDERS__*` sits above the
   file in the precedence chain, so a file edit under a set variable is written, kept, and marked
   *shadowed* on the page — the treatment configuration standards §7 already prescribes for a stored
   value, applied to a written one.

7. **Admin scope, CSRF, audited.** The route is `admin`, the form is CSRF-checked, and every write
   records who made it and what changed, because the file is now editable by a session rather than
   only by a shell.

## Consequences

* Two applications gain one dependency (`tomlkit`) and one write path into a file they previously
  only read. The blast radius of a bug in that path is the provider subtree of one file, with a
  `.bak` beside it.
* Migration 0008's rationale is unchanged and stays true: a registration is still configuration, and
  a model still records the name that served it rather than a key into a table. What changes is who
  may write the configuration, not what kind of thing it is.
* A registration edited in the browser and a registration edited in `$EDITOR` are the same edit to
  the same file. There is no second surface to reconcile, no import, and no drift.
* The file can now be rewritten while a human has it open in an editor. That race exists for any
  file two writers share; the `.bak` and the validation-before-write are the mitigation, and the
  page tells the operator when the file changed under it by refusing a write whose base document is
  no longer what was read.
