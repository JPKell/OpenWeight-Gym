# WS3 Handoff — IdeaPress 1.4.1: `config schema --json` and `config validate --file`

**Row:** WS3 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Sonnet 5 · high).
**Date:** 2026-09-09. **Kickoff:** [`ws3-ideapress-config-schema.prompt.md`](../prompts/ws3-ideapress-config-schema.prompt.md).
**Ships:** `ideapress 1.4.1` prepared (not published, not tagged, not pushed): two new `config`
verbs, a golden test of the schema document, `CHANGELOG.md`, the spec §7.2 mirror.

Read [WS1's handoff](WS1_HANDOFF.md) first — it set the exact document shape ("As WS1" in the
kickoff), and this row follows it, including the parts its own kickoff text didn't spell out
verbatim (the fixed five-field `runtime_changeable` shape, and tolerating only an unknown key).

## 1. What was built

* **The document** (ADR-0127 rule 1) is built by
  `ideapress.services.config_schema.build_schema_document()`: `schema_version` (`"1.0"`),
  `application`, `version` (from `__about__`), `env_prefix`, `config_path`, `json_schema`
  (`Settings.model_json_schema()`, untouched), `runtime_changeable`, `security_keys`,
  `config_only`, `sources` and `problems`.
* **IdeaPress's runtime registry moved out of the web layer.** It used to live as
  `RUNTIME_KEYS`/`CONFIG_ONLY_KEYS`/`_is_runtime_key` inside `ideapress.web.routes.settings` (the
  only place api.md §6's line was drawn in code). `config schema` needed the same line, and `cli`
  may not import `web` (`.importlinter`'s `web-cli-independence` contract), so the registry moved
  to a new module, **`ideapress.services.settings_registry`** (`RUNTIME_KEYS`, `CONFIG_ONLY_KEYS`,
  `is_runtime_key`), and the web route now imports it instead of owning a copy —
  `test_settings_registry.py::test_the_web_route_imports_the_registry_rather_than_owning_a_copy`
  asserts object identity, not just equal values.
* **`runtime_changeable` entries have exactly five fields**: `key`, `kind`, `minimum`, `maximum`,
  `description` — matching WS1's precedent (the ADR's own JSON example already showed this shape).
  `minimum`/`maximum` are **always present**, `None` when the field has no such bound — never
  omitted, so every entry across all four applications has the same key set. Both are read
  straight off the field's own resolved fragment of `json_schema` (`_resolve_in_json_schema` walks
  `$ref`/`$defs`), not re-derived from pydantic `FieldInfo` a second way. A choice field's
  permitted values (`inference.mode`, `logging.level`) are **not** repeated in `runtime_changeable`
  — they're in `json_schema`'s own `enum` for that field, same object either way.
* **The eleven `models.stages.<stage>` bindings are runtime-changeable too**, generated from
  `ideapress.domain.stages.MODEL_STAGES` rather than hand-listed — 8 registry keys + 11 stage
  bindings = 19 `runtime_changeable` entries on a default install.
* **`config_only` is the third bucket**: every leaf `ideapress.config_reference.sections()` walks
  (the same walk `docs/configuration.md` is generated from) that is in neither of the other two —
  40 keys on a default install. `test_config_only_covers_every_other_leaf_exactly_once` asserts
  the three buckets partition the full leaf set with no overlap and nothing missing.
* **`ideapress.config.load_settings_tolerant()`** is new, beside `load_settings` (which is
  unchanged — nothing about its behavior or signature moved). It re-parses the file and env layers
  itself rather than calling `load_settings`, then loops: on a pydantic `ValidationError` where
  *every* error is `extra_forbidden` (an unknown key or whole unknown section), it deletes each
  offending path from the merged dict, records `"unknown configuration key '<dotted>'"` (with the
  same typo suggestion `load_settings` gives) in `problems`, and retries. Any *other* kind of
  problem — a bad type, an out-of-range value, `[models.stages]` disagreeing with workflows §2, an
  unsafe bind or egress combination — raises exactly as `load_settings` does; only the unknown-key
  case is tolerated. This is deliberately narrower than a broad "catch anything" first draft: a
  `config schema` run against a config with an unsafe bind now refuses with `INSECURE_BINDING`
  exactly the way `config validate`/`config show` do, rather than silently describing the schema of
  a configuration it would otherwise refuse to serve.
* **`ideapress config schema --json`** prints the document as canonical JSON (`indent=2,
  sort_keys=True`, the same convention `config show --json`/`version --json` already use). Without
  `--json` it prints a short human summary (counts, not the whole JSON Schema); a non-empty
  `problems` list prints in yellow. A `ConfigurationError` that isn't an unknown key (e.g. an
  unsafe bind in the installation's own file) exits 2 with the refusal's message, same as `show`.
* **`ideapress config validate --file <path>`** is a new option on the existing `validate`
  command. With `--file`, the path must exist — a missing candidate is a clean usage error (exit
  2), unlike the application's own configuration, where a missing file just means defaults. The
  candidate is validated through the same `load_settings(config_path=...)` `show`/`validate`
  already use — same parse, same validation, same refusals — and the application's own
  `config.toml` (wherever `IDEAPRESS_CONFIG`/`--config`/the XDG default points) is never opened.
  Without `--file`, `validate` is byte-for-byte what it was.

## 2. Tests

* `tests/unit/test_config.py` — four new `load_settings_tolerant` cases: an unknown field is
  stripped and reported with its suggestion; an unknown whole section is reported by its top-level
  name (the error's `loc` never reaches `foo` inside `[nonsense]` — pydantic never looks inside a
  section it doesn't recognize at all, so the problem is `"unknown configuration key 'nonsense'"`,
  not `'nonsense.foo'` — this tripped the first draft of the test); a genuine validation error
  (`max_concurrent_stages = 2`) and an unsafe bind both still raise; output agrees with
  `load_settings` byte-for-byte on a clean file.
* `tests/unit/test_settings_registry.py` (new) — the web route imports the registry by identity;
  `is_runtime_key` for every registered key, every model stage, a security key, and nonsense.
* `tests/unit/test_config_schema.py` (new, 12 tests) — the golden
  (`tests/unit/goldens/config_schema_1_0.json`, recorded with `XDG_CONFIG_HOME=/golden/config` and
  `IDEAPRESS_DATA_DIR=/golden/data` pinned so `config_path` is deterministic, matching this repo's
  existing `_pinned_paths` convention in `test_config_1_0_compatibility.py`); every
  `runtime_changeable`/`security_keys` key resolves inside `json_schema`; the three buckets
  partition the leaf set exactly; bounds match pydantic's own `ge`/`le`; an unknown key is reported
  and the rest of the document still builds around it, with `sources` for every *other* leaf
  reported correctly (not blanked out); a genuine validation error (`INSECURE_BINDING`) is not
  swallowed; a configured `inference.loadcoach.api_key_env` naming a variable that is genuinely set
  to a secret in the test's own environment never puts that secret's value in the serialized
  document (it can't, structurally — `json_schema` is class-level and holds only defaults,
  `sources`/`problems` name layers and keys, never values — but this proves it directly rather
  than resting on that argument).
* `tests/e2e/test_cli_skeleton.py` — `config validate --file` (valid, unknown key, insecure bind,
  missing candidate, own-`config.toml`-untouched via `IDEAPRESS_CONFIG` + byte comparison) and
  `config schema` (canonical `--json`, human default, a tolerated unknown key surfacing in
  stdout, and the same `INSECURE_BINDING` refusal `validate` gives).

## 3. Quirks W4 needs to know

* **`sources` is one level deep, and `models.stages.<stage>` is not in it.**
  `ideapress.config._track_sources` (pre-existing, unchanged by this row) tracks provenance at
  `section.field`, one level under `Settings` — so `inference.ollama.base_url` has no entry of its
  own; the tracked key is `inference.ollama`, covering the whole nested table as one unit,
  and setting *any* stage in `[models.stages]` makes the tracked key `"models.stages"` = `"file"`
  as a whole, not `"models.stages.draft"` individually. W4's form generator will find `sources`
  entries for the 8 non-stage `runtime_changeable` keys but **not** for the 11
  `models.stages.<stage>` ones — reading `sources.get("models.stages.draft")` gets nothing, even
  when that stage really is file-set. This is not something WS3 introduced or fixed (it's how
  `config show` has always reported `[models.stages]`, and fixing it would change `config show`'s
  own output and golden); W4 will need to either fall back to `"default"` for any
  `models.stages.*` key not literally present in `sources`, or treat the coarser
  `"models.stages"` entry as covering all eleven when present.
* **Only an unknown key is tolerated; every other refusal still refuses.** `config schema` against
  an installation whose own `config.toml` has an unsafe bind, a bad range, or a
  `[models.stages]`/workflows-§2 mismatch exits 2 with that refusal's message — it does not
  degrade to a `problems` entry. `problems` is specifically and only "a key path this build
  doesn't recognize," per ADR-0127 rule 1's own wording ("An unknown key path... is reported under
  problems"); nothing else is.
* **`runtime_changeable`'s `minimum`/`maximum` are always both present** (possibly `null`), never
  conditionally omitted — a first draft of this row made them conditional
  (`exclusiveMinimum`/`exclusiveMaximum` included when present, both entirely absent for an
  unbounded field) before finding WS1's handoff, which fixed the five-field shape as what "all
  four rows emit." None of IdeaPress's bounded runtime settings use exclusive bounds (`ge`/`le`
  throughout), so nothing was lost switching to the fixed shape.
* **The generated `docs/configuration.md` was not touched** — regenerating it produces no diff.
  Its preamble names `config show`/`path`/`init` as examples, not an exhaustive verb list, and
  `schema`/`validate --file` change no field's type, default, range or security note.
* **IdeaPress has no live-secret field at all** (unlike FreeWeight's `auth.tokens`, WS1's only
  live secret): `api_key_env`/`api_key_file` hold a *reference* — an environment variable name or
  a file path — never a token, per configuration standards §6. The "do not print secrets"
  demonstration here proves the reference's genuinely-secret *target value* (an env var actually
  set to a secret string) never appears in the document, which is the strongest version of that
  claim this application can make.
* **`ideapress config schema` takes no `--config`/`--file` flag of its own** — it always describes
  *this installation's* configuration, resolved the normal way (`IDEAPRESS_CONFIG`, then the XDG
  default). To point it at a specific file for testing or diagnosis, set `IDEAPRESS_CONFIG`, the
  same as any other command that reads the resolved default.

## 4. Demonstrate

Both run against this machine's real (absent — no `~/.config/ideapress/config.toml` exists here)
configuration, so every value shown is a default and no secret-bearing key is set to demonstrate
redaction with; that claim rests on `test_the_document_never_carries_a_live_secret_value` instead.

```
$ ideapress config schema --json | python -m json.tool | head -60
{
    "application": "ideapress",
    "config_only": [
        "budget.partial_pricing",
        "budget.per_output_money_ceiling",
        ...
        "workflow.structured_output_tokens"
    ],
    "config_path": "/home/jpk/.config/ideapress/config.toml",
    "env_prefix": "IDEAPRESS_",
    "json_schema": {
        "$defs": {
            "BudgetSettings": {
            ...
```

```
$ printf '[server]\nhostt = "127.0.0.1"\n' > /tmp/candidate.toml
$ ideapress config validate --file /tmp/candidate.toml
Configuration invalid (/tmp/candidate.toml): unknown configuration key 'server.hostt'
(did you mean 'server.host'?)
$ echo $?
2
```

## 5. Finish line

`ruff format --check .`, `ruff check .`, `mypy src tests` (204 files), `lint-imports` (4 contracts
kept) and the full `pytest --cov` (1253 passed, 6 skipped, 89.30% coverage against the 85% app
floor) all green on Python 3.13 (`.venv`). Nothing pushed, tagged, or published. IdeaPress is at
`1.4.1` prepared; WeightRoomGym's W4 row is still blocked on WS2 and WS4.
