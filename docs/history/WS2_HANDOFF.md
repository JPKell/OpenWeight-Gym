# WS2 Handoff — LoadCoach 1.3.1: `config schema --json` and `config validate --file`

**Row:** WS2 of [`roadmap/weightroom-work.md`](../roadmap/weightroom-work.md) (Sonnet 5 · high).
**Date:** 2026-09-09. **Kickoff:** [`ws2-loadcoach-config-schema.prompt.md`](ws2-loadcoach-config-schema.prompt.md).
**Ships:** `loadcoach 1.3.1` prepared (not published, not tagged, not pushed): two new `config`
verbs, a golden test of the schema document, `CHANGELOG.md`, the spec §7.2 mirror.

## 1. What was built

* **The document** (ADR-0127 rule 1) is built by
  `loadcoach.services.settings.config_schema_document()`: `schema_version` (`"1.0"`),
  `application`, `version` (from `__about__`), `env_prefix`, `config_path`, `json_schema`
  (`Settings.model_json_schema()`, untouched), `runtime_changeable` (`RUNTIME_SETTINGS`, mapped to
  `key`/`kind`/`minimum`/`maximum`/`description` — the same five-field shape as WS1), `security_keys`
  (`CONFIG_ONLY_SECURITY_KEYS`, sorted — LoadCoach's own existing name, left as-is), `config_only`
  (`leaf_keys()` minus the two sets above minus `DERIVED_CONFIG_KEYS`), `provider_form`
  (`"singular"` or `"plural"`, ADR-0077 — see quirk below), `sources` (`config show`'s own
  per-leaf layer, database overlay included) and `problems`.
* **`loadcoach.config.load_settings_tolerant()`** is new: like `load_settings`, but an unknown key
  in the file is stripped and reported in `problems` rather than raising. `load_settings` itself is
  unchanged in behavior — it was split into `_read_file`/`_validate` helpers so the tolerant
  variant reuses them rather than re-parsing TOML a second way. A section that validates its own
  extra keys (`[providers]` and its `[providers.<name>]` registrations, ADR-0077) is passed through
  untouched by the tolerant filter rather than having its registrations misreported as unknown
  fields — LoadCoach is the first of the four applications to need this, since FreeWeight has no
  named-registration registry.
* **`loadcoach.config.leaf_keys()`** and **`DERIVED_CONFIG_KEYS`** are new. `leaf_keys()` reuses
  the existing `_known_dotted_keys()` walk (no duplicated key list). `DERIVED_CONFIG_KEYS`
  (`frozenset({"providers.registrations"})`) moved out of `services/config_reference.py`'s
  private `_DERIVED_KEYS` into `config.py` as the single source, imported back into
  `config_reference.py` under the old name so its existing test keeps passing — `registrations` is
  collected from `[providers.<name>]` subtables, not a key an operator types, and both the
  configuration reference and the schema document needed to agree on excluding it.
* **`loadcoach.services.settings.database_overlay()`** is the CLI's former private
  `_database_overlay()` (from `config show`), moved and made public so `config schema` reuses the
  identical database-read logic. `config show`'s own behavior and output are unchanged.
* **`loadcoach config schema --json`** prints `canonical_json(document)` (sorted keys). Without
  `--json` it prints a short human summary.
* **`loadcoach config validate --file <path>`** is a new option on the existing `validate`
  command: `load_settings(config_path=file if file is not None else config)`, with an explicit
  `Path(file).is_file()` check first so a missing candidate is a clean `CONFIGURATION_ERROR`
  rather than silently validating built-in defaults. Without `--file` the verb is exactly what it
  was. `--file` never reads or writes the installation's own `config.toml` (`resolve_config_path`
  returns the explicit path directly, bypassing `LOADCOACH_CONFIG` and the XDG default).

## 2. Tests

* `tests/unit/test_config_schema.py` (new) — the golden
  (`tests/fixtures/config/config_schema.json`, recorded from a clean, file-less,
  `LOADCOACH_STORAGE__DATABASE_URL`-pinned document with `config_path` **and** `version` excluded
  from the comparison, asserted separately instead; `version` in particular changes on every
  release, a gap the WS1 handoff flagged and this row closed at the outset); every
  `RUNTIME_SETTINGS`/`CONFIG_ONLY_SECURITY_KEYS` key resolves inside `json_schema` (the two P5
  queue control flags — `queue.paused`/`queue.draining` — are the documented exception: no
  `Settings` field exists for them, so they are skipped by name, not silently swallowed);
  `config_only` excludes both other sets and `providers.registrations`; `provider_form` reports
  `"plural"` once a `[providers.<name>]` block is configured; an unknown key is reported in
  `problems` and the rest of the document still builds.
* `tests/unit/test_cli.py` — `config validate --file` (valid, unknown key, insecure bind, missing
  file, own-`config.toml`-untouched) and `config schema` (JSON document shape, secret redaction via
  `evidence.freeweight_api_key_env`, drift refusal).
* Full pre-PR gate green: `ruff format --check .`, `ruff check .`, `mypy src tests`, `lint-imports`
  (4 contracts kept), `pytest` — 1100 passed, 5 skipped, 18 deselected, on Python 3.14 (`.venv`).

## 3. Quirks W4 needs to know

* **`provider_form` reflects the *effective* settings, not a literal read of the file on disk.**
  LoadCoach's environment layer supports arbitrary nesting (`LOADCOACH_PROVIDERS__LOCAL__KIND` is a
  legal way to register a provider with no file at all), so `provider_form` is computed from
  `loaded.settings.providers.registrations` after the full precedence chain, not from a raw TOML
  read. In the overwhelming common case (no env-based provider registration) this is
  indistinguishable from "what the file says"; W4's settings form should treat it as "which form is
  live", not "which form is written".
* **`providers.registrations` is excluded from `config_only`** via the new
  `loadcoach.config.DERIVED_CONFIG_KEYS`, shared with the configuration reference. If a future
  section grows its own "collected, not typed" field, add it there once rather than in both
  `config_reference.py` and `services/settings.py` separately.
* **The tolerant loader treats `extra="allow"` sections specially.** `load_settings_tolerant`
  checks each top-level section's `model_config["extra"]` and skips its own unknown-key filtering
  entirely for `[providers]`, deferring to `ProvidersSettings`' own extras-collection and
  extras-validation. A `[providers.local]` with a genuinely bad field (e.g. a typo inside the
  registration table) still raises normally — only the *table name* `local` is exempted from the
  tolerant pass, not its contents.
* **`security_keys` is named `CONFIG_ONLY_SECURITY_KEYS` in LoadCoach's own code** (not
  `CONFIG_ONLY_KEYS` as in FreeWeight) — left unrenamed; the document's field is `security_keys`
  regardless.
* **The generated `docs/configuration.md` was not touched** beyond the `DERIVED_CONFIG_KEYS`
  refactor, which is behavior-preserving — `loadcoach config reference --check` stayed green with
  no edit. `docs/openapi.json` and `README.md`'s status line both needed a one-line regen/edit for
  the `1.3.0` → `1.3.1` bump; both are one-command fixes tied to any version bump, not specific to
  this row.
* **LoadCoach has two `api_key_*`-shaped secrets** (`evidence.freeweight_api_key_env`,
  `evidence.freeweight_api_key_file`), the case the WS1 handoff flagged as untested there. The
  redaction test here exercises the `_env` variant; both are structurally guaranteed secret-free
  regardless, since no field of the document ever carries a configured *value* — only key paths,
  types and layer labels.

## 4. Demonstrate

```
$ loadcoach config schema --json | python -m json.tool | head -60
{
    "application": "loadcoach",
    "config_only": [
        "adapters.directory",
        "evidence.accept_schema_majors",
        ...
    ],
    "env_prefix": "LOADCOACH_",
    "json_schema": {
        "$defs": {
        ...
```

```
$ printf '[server]\nhost = "0.0.0.0"\n' > /tmp/candidate.toml
$ loadcoach config validate --file /tmp/candidate.toml
Error: server.host is '0.0.0.0' (all interfaces) but server.allow_lan_exposure is false. Exposing
the service beyond this machine must be a deliberate act: set server.allow_lan_exposure = true if
that is intended. (INSECURE_BINDING)
$ echo $?
3
```

Both run against this machine's fresh (no-secret-set) configuration, matching WS1's note: the
redaction claim rests on the test suite
(`test_config_schema_never_prints_a_secret`), not a pasted transcript with a real secret in it.

## 5. Finish line

Gate green in `~/ai/suite/LoadCoach` (nothing pushed or tagged); one docs commit in
`~/ai/suite/WeightRoom` (`apps/loadcoach/spec.md` §7.2 amendment, canonical-first, mirror
`cmp`-proven byte-identical; the roadmap row marked done). The WeightRoom docs repository carried
other sessions' uncommitted edits (WM, WS3, WS4) at the time of this row's commit; only this row's
two lines (`apps/loadcoach/spec.md`, the WS2 table row) were staged and committed — the others were
left exactly as found, for their own rows to commit.
