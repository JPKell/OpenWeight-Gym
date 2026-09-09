# WS1 Handoff — FreeWeight 1.2.1: `config schema --json` and `config validate --file`

**Row:** WS1 of [`roadmap/weightroom-work.md`](../roadmap/weightroom-work.md) (Sonnet 5 · high).
**Date:** 2026-09-09. **Kickoff:** [`ws1-freeweight-config-schema.prompt.md`](ws1-freeweight-config-schema.prompt.md).
**Ships:** `freeweight 1.2.1` prepared (not published, not tagged, not pushed): two new `config`
verbs, a golden test of the schema document, `CHANGELOG.md`, the spec §7.2 mirror.

## 1. What was built

Gates A and B landed in one commit (they touch the same three source files, so splitting them
would have been a diff without a seam); Gate C is the release-prepared commit.

* **The document** (ADR-0127 rule 1) is built by
  `freeweight.services.settings.config_schema_document()`, a new function beside the existing
  runtime-settings registry it reuses rather than duplicates:
  `schema_version` (`"1.0"`), `application`, `version` (from `__about__`), `env_prefix`,
  `config_path`, `json_schema` (`Settings.model_json_schema()`, untouched), `runtime_changeable`
  (`RUNTIME_SETTINGS`, mapped to `key`/`kind`/`minimum`/`maximum`/`description` — **not** `unit` or
  `choices`; the kickoff's decisions-already-taken bullet named exactly those five fields as "the
  one shape all four rows emit", so `execution.on_idle_timeout`'s two choices and
  `telemetry.interval_ms`'s `"ms"` unit are in the document's `json_schema` block but not repeated
  in `runtime_changeable` — a form generator reads the constraint from `json_schema` if it wants
  it, same object either way), `security_keys` (`CONFIG_ONLY_KEYS`, sorted — FreeWeight's existing
  name for what the ADR calls `security_keys`, left as-is rather than renamed to avoid
  disturbing every other reader of that constant), `config_only` (every other leaf: `leaf_keys()`
  minus the two sets above), `sources` (`config show`'s own per-leaf layer, database overlay
  included — see below) and `problems`.
* **`freeweight.config.load_settings_tolerant()`** is new: like `load_settings`, but an unknown
  key in the file is stripped and reported in `problems` rather than raising — the tool that
  describes why a configuration file won't load cannot itself refuse to load it. Every *other*
  kind of problem (a bad type, an out-of-range value, an unsafe bind) still raises exactly as
  `load_settings` does; only an unrecognized key path gets the tolerant treatment. `load_settings`
  itself is unchanged in behavior — it was split into `_read_file`/`_validate` helpers so the
  tolerant variant could reuse them instead of re-parsing TOML a second way.
* **`freeweight.config.leaf_keys()`** is new (every `section.field` path `Settings` recognizes) and
  `_known_dotted_keys()` (the existing typo-suggestion helper) now calls it instead of carrying its
  own copy — the "no duplicated key lists" instruction, taken literally.
* **`freeweight.services.settings.database_overlay()`** is the CLI's private
  `_database_overlay()` (from `config show`), moved and made public so `config schema` can call the
  identical database-read logic rather than a second copy. `config show`'s own behavior and output
  are unchanged — it now imports the function it used to define.
* **`freeweight config schema --json`** prints `canonical_json(document)` (Gold Standards G8:
  sorted keys, one line, stable floats) built from the above. Without `--json` it prints a short
  human summary (counts and key names, not the whole JSON Schema).
* **`freeweight config validate --file <path>`** is a new option on the existing `validate`
  command: `load_settings(config_path=file if file is not None else config)`. Without `--file` the
  verb is exactly what it was — nothing about `--config`'s existing behavior changed. `--file` never
  reads or writes the installation's own `config.toml`; a test asserts its bytes are untouched
  across a `--file` run against a different, invalid candidate.

## 2. Tests

* `tests/unit/test_config.py` — `leaf_keys()`, and four `load_settings_tolerant` cases (unknown
  field, unknown section, a genuine validation error still raises, output matches `load_settings`
  byte-for-byte on a clean file).
* `tests/unit/test_config_schema.py` (new) — the golden (`tests/unit/golden/config_schema.json`,
  recorded from a clean, file-less, env-less document with `version` and `config_path` excluded
  from the comparison, since one changes on every release and the other is wherever the test's
  isolated XDG tree lands); every `RUNTIME_SETTINGS` and `CONFIG_ONLY_KEYS` key resolves inside
  `json_schema`; `config_only` excludes both other sets; an unknown key is reported and the rest of
  the document still builds; a genuine validation error still raises; a configured secret
  (`auth.tokens`) never appears in the serialized document; a database-sourced runtime value is
  reported as `"database"` in `sources`.
* `tests/e2e/test_cli_basics.py` — `config validate --file` (valid, unknown key, insecure bind,
  missing file, own-`config.toml`-untouched) and `config schema` (canonical one-line JSON, secret
  redaction, unknown-key problem, and the same `INSECURE_BINDING` refusal `validate` gives).

## 3. Quirks W4 needs to know

* **`runtime_changeable` entries carry only five fields** — `key`, `kind`, `minimum`, `maximum`,
  `description`. A `"choice"` setting's permitted values (`execution.on_idle_timeout`,
  `logging.level`) are **not** repeated there; W4's form generator must read `enum`/`const` off the
  matching field in `json_schema` for a choice widget, and the unit (`telemetry.interval_ms`:
  `"ms"`) similarly comes from the field's schema, not from `runtime_changeable`. This was a
  decision already taken in the kickoff prompt (the exact five-field shape is named), not something
  this row chose.
* **`security_keys` is named `CONFIG_ONLY_KEYS` in FreeWeight's own code.** Left unrenamed —
  `generate_config_reference.py`, `web/routes/settings.py` and the settings service all already
  import it under that name, and the document's field is `security_keys` regardless of what the
  Python constant is called.
* **`config_only` is the third bucket, not a synonym for `CONFIG_ONLY_KEYS`.** It is every leaf
  that is neither runtime-changeable nor security-relevant (`goals.max_pack_bytes`,
  `provider.timeout_seconds`, and 56 others on a default install) — read the ADR's rule 1 bullet
  twice if this looks backwards; it did to the first draft of this row too.
* **`sources` reuses `config show`'s exact strings**, shadowed values included
  (`"env FREEWEIGHT_…; database row … shadowed"`), rather than the shorter illustrative form in the
  ADR's own example (`"database (shadowed by env)"`). The ADR's example is representative, not
  literal; each of the four applications already had its own vocabulary for this before ADR-0127,
  and rule 1 says to reuse "`config show`'s per-leaf layer" — so this row reused it rather than
  inventing a fifth spelling.
* **The generated `docs/configuration.md` was not touched.** Its static preamble names `config
  show`/`path`/`init` as examples, not an exhaustive verb list, and `schema`/`validate --file`
  don't change any field's type, default, range or security note — `scripts/generate_config_reference.py
  --check` is green with no edit.
* **FreeWeight has no `api_key_env`/`api_key_file`-shaped provider secret** (unlike LoadCoach,
  IdeaPress and PromptCadence, which call remote APIs) — the "do not print secrets" demonstration
  test here covers `auth.tokens` instead, FreeWeight's only live secret. WS2–WS4 will need the
  `api_key_*` case as well as their own runtime-registry secrets, if any.

## 4. Demonstrate

```
$ freeweight config schema --json | python -m json.tool | head -60
{
    "application": "freeweight",
    "config_only": [
        "adapters.directory",
        "benchmarks.long_context_max_tokens",
        ...
    ],
    "env_prefix": "FREEWEIGHT_",
    "json_schema": {
        "$defs": {
        ...
```

```
$ printf '[server]\nhostt = "127.0.0.1"\n' > /tmp/candidate.toml
$ freeweight config validate --file /tmp/candidate.toml
Error: Configuration invalid (/tmp/candidate.toml): unknown configuration key 'server.hostt'
(did you mean 'server.host'?) (CONFIGURATION_ERROR)
$ echo $?
3
```

Both run against this machine's real (empty, fresh) configuration — no secret-bearing key is set
here to demonstrate redaction with, so the redaction claim rests on
`test_document_never_carries_a_configured_secret_value` and
`test_config_schema_redacts_a_configured_secret` instead of a pasted transcript.

## 5. Finish line

`ruff format --check .`, `ruff check .`, `mypy src tests`, `lint-imports` (4 contracts kept), full
`pytest` (2667 passed, 29 skipped, 30 deselected, 0 failed) — all green on Python 3.14.4 (`.venv`).

Two pre-existing failures surfaced on the first full run, both predating this row (the version was
already `1.2.0` with no matching release-prep commit): `docs/openapi.json` still named `1.1.2`, and
`README.md`'s status line still said `1.2.0` after this row's own bump to `1.2.1`. Both are
one-command regens tied to the version bump this row makes anyway
(`scripts/generate_openapi_snapshot.py`, and the README line release scripts are supposed to stage
per the version guard), not a change this row's ADR-0127 work required — fixed here rather than
left red, since leaving them would have made "gate green" false for reasons unrelated to what WS1
built.

Nothing pushed, tagged, or published. FreeWeight is at `1.2.1` prepared; WeightRoomGym's W4 row
(`WS1–WS4` gate) is still blocked on WS2–WS4.
