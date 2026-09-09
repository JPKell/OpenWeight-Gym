# Kickoff — W4: WeightRoom Phase 4 — settings forms over the schema verbs, the doctor, tokens

**Row:** W4 (Opus 5 · high) — [`docs/roadmap/weightroom-work.md`](../roadmap/weightroom-work.md).
Runs after W3 and **WS1–WS4** (hard).
**Ships:** `weightroom 0.4.0` prepared: every application's settings editable from the
console through its own schema and validation; the doctor; per-application token pages.
**Component:** `~/ai/suite/WeightRoom`. The four applications must carry `config schema --json`
and `config validate --file` (rows WS1–WS4 done, each prepared as a patch release); pin each as an
editable path install with a `TODO: re-pin on publish` where the release is not on PyPI yet.

## Standing preamble

[`outstanding-work.md` §2](../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../roadmap/weightroom-work.md).

**Read first:** ADR-0127 in full; ADR-0117 (the round-trip and the race this generalises);
ADR-0100 (the runtime registry's meaning); [`spec.md`](../apps/weightroom/spec.md) §7.4, §12, §13;
[`api.md`](../apps/weightroom/api.md) §2 (settings routes), §9 (`/reauth`);
[`development-plan.md`](../apps/weightroom/development-plan.md) Phase 4;
`standards/configuration-standards.md` §4, §7, §8; `MEMORY_SAFETY.md` §6 and `LAN_ACCESS.md`
(the doctor's rubric); the four `WS*_HANDOFF.md` files (each application's document, its quirks);
`history/W3_HANDOFF.md`. Precedent: LoadCoach's provider-admin write path (ADR-0117's
implementation: `tomlkit`, validate, write-beside, `fsync`, rename, `.bak`).

## Decisions already taken — do not reopen

* Forms are generated from the document; **no key is hardcoded**; an undescribed key renders raw
  (ADR-0127 rule 3). The test: add a field to a fixture document and it appears.
* Runtime keys go through the application's `PUT /settings`, never the file (rule 4); other keys
  through `tomlkit` with validate-before-write via `config validate --file`, `.bak`, `base_mtime`
  (rule 3); *pending restart* until the restart happens (rule 5).
* Security keys are editable after `POST /reauth` within the window, and audited as such
  (rule 6) — WeightRoom's own security keys included.
* The doctor **prints** root-owned fixes; it never runs them.

## Gates

**Gate A — the reader and the generator.** `services/settings_forms.py`: read each application's
document (60 s cache), build the form model (sections from the model's nesting; type, bounds,
default, description, current value, `source`, `shadowed`), the security and runtime sets; goldens
over the four documents. Commit.

**Gate B — the write paths.** `services/config_files.py` (round-trip, validate, atomic replace,
`.bak`, the race); runtime keys via the application API; `PUT /apps/{app}/settings` with per-key
outcomes; `POST /reauth` and `REAUTH_REQUIRED`; *pending restart* state and the restart button;
the raw TOML editor under the same rules; WeightRoom's own settings page from its own verb. Every
application's `EXAMPLE_CONFIG_TOML` round-tripped one key at a time, byte-identical elsewhere.
Commit.

**Gate C — doctor and tokens.** `weightroom doctor` and the Doctor page: one finding per rule with
severity, evidence and the printed command — `MEMORY_SAFETY.md` §2.1 and §2.2, an application off
loopback, Ollama on `0.0.0.0` (a notice), versions and revisions in range, TLS expiry, linger, the
polkit rule, disk space under each data root, stray `[server]` blocks from the retired Caddy script;
tokens pages (`token list|create|revoke` per application, the secret shown once). `CHANGELOG.md`;
`0.4.0`. Commit.

## Demonstrate

Plan Phase 4 criteria 1–4 on the reference machine, with `diff config.toml config.toml.bak`
after the security-key write pasted into the handoff.

## What this row must decide, and write down

* How a key whose document name and file spelling differ (LoadCoach's singular `[provider]` vs
  `[providers.<name>]`, ADR-0077) is presented — the WS2 handoff says what the document carries.
* The re-authentication token's transport (a header on the JSON write, or a second cookie) — pick,
  test against the same-origin rules, and record it.

## Finish line

Gate green, coverage held, one commit per gate, `docs/history/W4_HANDOFF.md`, the row marked done.
