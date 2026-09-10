# WS4 Handoff — PromptCadence 1.3.3: `config schema --json` and `config validate --file`

**Row:** WS4 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Sonnet 5 · high).
**Date:** 2026-09-09. **Kickoff:** [`ws4-promptcadence-config-schema.prompt.md`](../prompts/ws4-promptcadence-config-schema.prompt.md).
**Ships:** `promptcadence 1.3.3` prepared (not published, not tagged, not pushed): two new `config`
verbs, a golden test of the schema document, `CHANGELOG.md`, the spec §7.2 mirror.

## 1. What was built

* **The document** (ADR-0127 rule 1) is built by
  `promptcadence.services.config_schema.build_schema_document()` (new module): `schema_version`
  (`"1.0"`), `application`, `version` (from `__about__`), `env_prefix`, `config_path`, `json_schema`
  (`Settings.model_json_schema()`, untouched), `runtime_changeable` (`RUNTIME_SETTINGS`, mapped to
  `key`/`kind`/`minimum`/`maximum`/`description` — the same five-field shape WS1/WS2 used),
  `security_keys` (`services.settings.config_only_keys()`, PromptCadence's existing name for the
  set `PUT /settings` refuses — ADR-0100's five runtime keys plus whole sections
  `[server]`/`[loadcoach]`/`[approval]`/`[budget]`/`[tools]`/`[tiers]`/`[policy]` expanded to every
  leaf, not the section names, so a form can mark each field), `config_only` (the new
  `all_configured_keys()` minus the two sets above), `sources` (`config show`'s own per-leaf layer,
  database overlay included — `shadowed_by` exactly as `GET /settings` reports it), and `problems`.
* **`promptcadence.config.load_settings_tolerant()`** is new: like `load_settings`, but an unknown
  key in the file is pruned and reported in `problems` (as `{"key": ..., "reason": "unknown
  configuration key"}`) instead of raising. Any *other* refusal — bad TOML, a wrong type, an
  insecure bind, a misconfigured tier or project budget — still raises exactly as `load_settings`
  does; a test proves an unknown key alongside a genuine type error still raises (the pruning pass
  only ever removes `extra_forbidden` errors, nothing else). `load_settings` itself is
  behavior-unchanged — split into `_read_toml_file`/`_validate_and_load` helpers so the tolerant
  variant reuses the same merge/validate/security-checks pipeline instead of a second copy.
* **`promptcadence.services.settings.all_configured_keys()`** is new, sharing a `_walk_leaf_keys()`
  helper with the existing `config_only_keys()` (which used to inline the same walk) — one walk,
  two filters, so the schema document and the config-only list can never name a keyed-table leaf
  (`[tiers.<name>]`, `[budget.projects.<name>]`) differently.
* **`promptcadence.services.settings.database_source_overlay()`** is the CLI's former private
  `_database_overlay()` (from `config show`), moved and made public so `config schema` reuses the
  identical read-only database-read logic rather than a second copy. `config show`'s own behavior
  and output are unchanged — it now imports the function it used to define.
* **`promptcadence config schema [--json]`** prints the document: `--json` prints
  `baseaicore.canonical_json(document)` (Gold Standards G8: sorted keys, one line, stable floats);
  without it, `json.dumps(document, indent=2, sort_keys=True)` — still valid JSON, just
  human-readable, since there is no sensible tabular rendering of a JSON Schema.
* **`promptcadence config validate --file <path>`** is a new option on the existing `validate`
  command. Without `--file` the verb is exactly what it was (`--config` still falls back to
  defaults when the resolved file is missing — spec §20 AC1). With `--file`, the CLI checks
  `Path(file).is_file()` itself first — a missing candidate is a clean `Exit(3)` naming the path,
  not a silent fall-through to defaults the way a missing `--config` is — then calls
  `load_settings(config_path=file)`, the same parse/validation/security pipeline as everything
  else. `--file` never reads or writes the application's own `config.toml`; a test asserts its
  bytes are untouched across a `--file` run against an unrelated candidate.

## 2. Tests

* `src/promptcadence/config.py`: `load_settings` refactored into `_read_toml_file` +
  `_validate_and_load` (behavior-preserving — all 30 existing `test_config.py` cases pass
  unchanged) plus the new `load_settings_tolerant` and `_delete_error_path`.
* `tests/unit/test_config_schema.py` (new) — the golden
  (`tests/golden/config_schema.json`, `config_path` masked since it names the test's per-run tmp
  XDG root); every `RUNTIME_SETTINGS`/`security_keys` key resolves inside `json_schema` (a
  generic `$ref`/`additionalProperties` walker, handling both plain `section.field` and
  keyed-table `section.<name>.field` paths); the three key sets (`runtime_changeable`,
  `security_keys`, `config_only`) partition `all_configured_keys()` with no overlap and no gap;
  `config_only_keys()` and the document's `security_keys` agree; an unknown file key is reported
  under `problems` and the rest of the document still builds; an unknown key alongside a genuine
  type error still raises; a database-sourced runtime value is reported as `"database"` in
  `sources`; a configured `loadcoach.api_key_env` value never appears in the serialized document.
* `tests/unit/test_cli.py` — `config schema` (exits 0, prints valid JSON, `--json` is
  self-consistently canonical, exits 3 on a genuine refusal — `INSECURE_BINDING` — same as
  `validate`, an unknown file key surfaces as a `problems` entry with the rest of the file still
  loaded) and `config validate --file` (valid candidate, unknown key named, `INSECURE_BINDING`
  refused, missing file is a clean error distinct from `--config`'s fallback, the application's own
  `config.toml` bytes are untouched).

## 3. Quirks W4 needs to know

* **`security_keys` expands whole sections to every leaf, per ADR-0100/ADR-0127**, not section
  names: `tiers.local_fast.remote`, `tiers.local_fast.task_profile`, etc. are each named
  individually (and only for tiers actually configured — a keyed table's entries are walked as
  configured, never left as a `<name>` placeholder). A default install therefore lists 56
  `security_keys` and 10 `config_only` keys; both counts move if the operator adds a tier or a
  project.
* **`config_only` is the third bucket, not a synonym for "everything else in the file."** It is
  every leaf that is neither runtime-changeable nor security-relevant — on a default install:
  `compaction.policy_chain`, `compaction.protected_recent_turns`, five `execution.*` bounds,
  `logging.format`, `logging.level`, `planning.max_plan_steps`. Read ADR-0127 rule 1 twice if this
  looks backwards — the security half is the *larger* set here, because PromptCadence's
  config-only-by-section rule (spec §12) reaches almost the whole model.
* **`sources` reuses `config show`'s exact strings, shadowed values included**
  (`"env PROMPTCADENCE_…; database row … shadowed"`), matching the WS1/WS2 precedent rather than
  the ADR's shorter illustrative form (`"database (shadowed by env)"`) — the ADR's example is
  representative, not literal.
* **`config validate --file` and `--config` are genuinely different, not aliases.** `--config`
  keeps "missing file → defaults" (so `promptcadence config validate` alone still answers on a
  fresh install); `--file` requires the candidate to exist, because a form that just wrote a file
  asking "is what I wrote valid" should get a clean error on a typo'd path, not a silent "yes,
  defaults are fine."
* **No provider_form-style quirk here** (LoadCoach's WS2 handoff flagged one for its
  singular/plural `[providers]` shape) — PromptCadence's `[loadcoach]` section has no analogous
  registration table, so the document's shape is the plain five-field case throughout.
* **The generated `docs/configuration.md` was not touched** — neither verb changes any field's
  type, default, range or security note, so `promptcadence config reference --check` stayed green
  with no edit (confirmed by the existing `test_config_reference.py` golden, unchanged and passing).
* **`docs/openapi.json` needed a one-line regen** for the `1.3.2` → `1.3.3` version bump (the
  FastAPI app's `info.version` comes from `__about__`) — a `test_openapi_snapshot.py` failure
  unrelated to this row's own work, same as the WS1/WS2 handoffs' README/openapi notes, fixed here
  rather than left red.

## 4. Demonstrate

Both commands below ran on this machine against its real configuration — no `config.toml` exists
at `~/.config/promptcadence/config.toml`, so this is the zero-configuration default install (spec
§20 AC1), the state `promptcadence serve` actually runs in here today:

```
$ promptcadence config schema --json | python -m json.tool | head -60
{
    "application": "promptcadence",
    "config_only": [
        "compaction.policy_chain",
        "compaction.protected_recent_turns",
        "execution.lease_seconds",
        "execution.max_concurrent_remote_steps",
        "execution.max_concurrent_steps",
        "execution.max_concurrent_trajectories",
        "execution.max_steps",
        "logging.format",
        "logging.level",
        "planning.max_plan_steps"
    ],
    "config_path": "/home/jpk/.config/promptcadence/config.toml",
    "env_prefix": "PROMPTCADENCE_",
    "json_schema": {
        "$defs": {
            "ApprovalSettings": {
                "additionalProperties": false,
                "description": "``[approval]`` — who authorizes the minting of an
                ``ExecutionIntent`` (ADR-0049).",
                "properties": { ... },
                ...
```

```
$ cat > /tmp/candidate.toml <<'EOF'
[server]
host = "127.0.0.1"
port = 8768

[loadcoach]
base_url = "http://127.0.0.1:8766"

[storage]
retain_content = "yes-please"
EOF
$ promptcadence config validate --file /tmp/candidate.toml
Error: Configuration invalid (/tmp/candidate.toml): storage.retain_content: Input should be a
valid boolean, unable to interpret input (CONFIGURATION_ERROR)
$ echo $?
3
```

No secret-bearing key is set on this machine to demonstrate redaction against; that claim rests on
`test_no_secret_shaped_value_reaches_the_document` (a `loadcoach.api_key_env` value set via
environment never reaches the serialized document — no field of the document ever carries a
configured *value*, only key paths, types and layer labels), matching the WS1/WS2 handoffs' note.

## 5. Finish line

`ruff format --check .`, `ruff check .`, `mypy src tests` (Python 3.13.15, `.venv`), `lint-imports`
(5 contracts kept), full `pytest -p no:randomly` — 1310 passed, 3 skipped, 10 deselected, 4
warnings (unrelated deprecation notices).

Four pre-existing failures in `tests/unit/test_egress_surfaces.py` predate this row — reproduced
identically on a clean `git stash` of every change this row made, confirmed unrelated before
starting and left exactly as found (not in ADR-0127's or this row's scope).

Nothing pushed, tagged, or published. PromptCadence is at `1.3.3` prepared; WeightRoomGym's W4 row
is unblocked on WS1, WS2 and this row, still waiting on WS3.
