# Kickoff — WS3: IdeaPress 1.4.1 — `config schema --json` and `config validate --file`

**Row:** WS3 (Sonnet 5 · high; overnight allowed) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W0; independent of W1–W3 and of the other three WS rows; **before W4**.
**Ships:** `ideapress 1.4.1` prepared (not published): two verbs on the existing `config` group, a
golden of the schema document, CHANGELOG, the mirror.
**Component:** `~/ai/suite/IdeaPress` (its `.venv`); then one docs commit in `~/ai/suite/WeightRoom`
(`apps/ideapress/spec.md` §7.2 gains the two verbs — edit the canonical copy first, then
`cmp`-prove the mirror in `IdeaPress/docs/`; the row marked done).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** ADR-0127 in full (rule 1 is the document, rule 2 the validation verb);
`apps/ideapress/spec.md` §7.2 and §12; `standards/configuration-standards.md` §4, §7, §8;
`standards/cli-standards.md` §3 (`--json` output), §9; IdeaPress's `config.py` (the `Settings`
model, `load_settings`, `LoadedSettings.sources`), its `services/settings.py` or equivalent (the
runtime registry and the security-key set), its `cli/commands/config.py` and the existing
`config show`/`validate` tests; `scripts/generate_config_reference.py` where present — the
document is built from the **same** objects the reference is.

## Decisions already taken — do not reopen

* The document is exactly ADR-0127 rule 1's shape, `schema_version = "1.0"`: `application`,
  `version`, `env_prefix`, `config_path`, `json_schema` (pydantic's `model_json_schema()` of
  `Settings`, descriptions included), `runtime_changeable` (the registry verbatim, with bounds),
  `security_keys` (the set `PUT /settings` refuses as `403` by name), `config_only` (every other
  non-runtime leaf), `sources` (`config show`'s per-leaf layer, with `shadowed by env` where a
  stored row cannot take effect), and `problems` for an unknown key in the file.
* `config validate --file <path>` runs `load_settings` on that file — same parse, same
  validation, same security refusals — and exits 0 or non-zero with validation's own message;
  without `--file` the verb keeps its present meaning (rule 2).
* No new dependency; nothing else in the application changes; the document is application-local
  (not a `setspec` schema — rule 7).
* **IdeaPress's runtime-changeable registry** is described by `apps/ideapress/api.md` §6 rather than by a `services/settings.py` — find where it lives in the code, name the module in the handoff, and emit the same document shape as the other three. If there is no registry (every key config-only), `runtime_changeable` is `[]` and the document says so; do not invent one.

## Gates

**Gate A — the document.** A service function that builds it from the existing objects (no
duplicated key lists); `config schema --json` printing canonical JSON (sorted keys, Gold
Standards G8); a golden test that compares the document to a committed file and a test that
every key in `runtime_changeable` and `security_keys` exists in `json_schema`. Commit.

**Gate B — validation.** `config validate --file`; tests: a valid candidate exits 0, an unknown
key names it, an insecure bind refuses with `INSECURE_BINDING`, a missing file is a clean error,
and the application's own `config.toml` is never touched (assert its bytes). Commit.

**Gate C — release-prepared.** `CHANGELOG.md`, `__about__` `1.4.1`, the generated
`docs/configuration.md` regenerated if the verb list appears in it, the spec §7.2 amendment
canonical-first and mirrored, the row marked done. Commit in both repositories.

## Demonstrate

`ideapress config schema --json | python -m json.tool | head -60` on the reference machine against
the operator's real configuration, and `ideapress config validate --file /tmp/candidate.toml` on a
copy with one deliberate error, both pasted into the handoff. **Do not print secrets**: the
document carries key paths and layers, never a token, a password or a URL credential — a test
asserts it over a configuration that sets `api_key_file`-class keys.

## Finish line

Gate green in the application's repository, coverage held, nothing pushed or tagged,
`docs/history/handoffs/WS3_HANDOFF.md` naming the document's exact shape and any quirk W4 must know.
