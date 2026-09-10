# Kickoff — WI1: IdeaPress — runtime settings in the suite's shape and applied; a unit a failed stage strands

**Row:** WI1 (Opus 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W9 and **before W10** (operator, 2026-09-10).
**Ships:** IdeaPress changes under `CHANGELOG.md`'s `[Unreleased]` — **no version bump** (every
version holds until the W arc ends), nothing tagged, pushed or published.
**Components:** `~/ai/suite/IdeaPress` (its own `.venv`, Python 3.13), then `~/ai/suite/WeightRoom`
(the canonical `apps/ideapress/api.md`, any console test that mocks IdeaPress's old shape, and one
docs commit).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `history/handoffs/W9_HANDOFF.md` §4.3, §5 items 3–5 and §6; ADR-0100 in full
(rule 5: `defaults → file → database → env → CLI`, and the per-key `stored`, `source`,
`shadowed_by`); ADR-0124 (IdeaPress's `settings` table is never writable from WeightRoomGym — the
application's `PUT /settings` is the audited path); ADR-0127 rule 4;
`standards/configuration-standards.md` §7; `apps/ideapress/api.md` §6. Code: LoadCoach's
`services/settings.py` (`runtime_settings_document` → `settings`, `definitions` with `configured`,
`stored`, `source`, `shadowed_by`, and `config_only`) and `web/routes/settings.py`; PromptCadence's
`web/routes/settings.py` (the same document, ADR-0100); IdeaPress's `web/routes/settings.py`,
`services/settings_registry.py`, `services/unit_loop.py`; WeightRoomGym's
`services/settings_forms.py::live_settings` and `web/routes/settings.py::_runtime_applier`.

## What is wrong

1. **The shape.** IdeaPress's `PUT /settings` takes `{"values": {…}}` (`extra="forbid"`) and its
   `GET` answers `runtime_changeable`, `overrides` and `config_only`. LoadCoach and PromptCadence
   take a flat `{key: value}` body and answer `{settings, definitions, config_only}`, and the
   console sends and reads that. So every IdeaPress runtime key is refused from the console's
   Settings page ("Request body failed validation") and IdeaPress's live values never show.
2. **Rows never applied.** IdeaPress upserts a `settings` row per changed key, and nothing in
   IdeaPress reads that table: a runtime change is recorded and does nothing.
3. **A stranded unit.** `run_unit` sets the unit to `drafting` before its first model call. A stage
   that fails before any attempt — `MODEL_NOT_CONFIGURED` when the bound model is not installed —
   leaves the unit in `drafting`, and running the stage on it again is refused ("Unit U-01 cannot
   move from 'drafting' to 'drafting'"). On the reference machine: project
   `01M26M2QJQD5VK73X476GVB1CJ`, unit U-01.
4. **A leftover row on the reference machine.** W9's demonstration stored
   `models.stages.draft = "ollama/gemma4:12b"`. Inert today; once rows apply, it beats
   `~/.config/ideapress/config.toml`'s `ollama/qwen3.5:9b-q8_0` and every draft fails again.

## Decisions already taken — do not reopen

* **IdeaPress conforms** (operator, 2026-09-10); the console is not taught a per-application shape.
  `GET` and `PUT` answer the same document LoadCoach and PromptCadence answer; `PUT` takes a flat
  object. IdeaPress's refusal rules stay: a configuration-only key is `403` naming it, an unknown
  key is refused, and nothing is written when any key is refused.
* **Stored rows are applied with ADR-0100 rule 5's precedence** — the environment beats a stored
  row, a stored row beats the file — and the document says per key what decides it. *When* a stored
  value takes effect (the next request, the next stage start, a restart) is decided from what the
  code can honour, stated per key in the document and `api.md` §6; no key claims to be live if it
  is not.
* **A stored row can be cleared through `PUT /settings`.** Follow LoadCoach's or PromptCadence's
  convention if either has one; otherwise a `null` value removes the key's row. Document it in
  `api.md` §6. Clear W9's leftover row on the reference machine through that path — never by a raw
  write.
* **A stage that fails before a unit's first attempt leaves the unit runnable.** Choose between
  returning it to the state it started from and letting a re-run take a unit a failed task left in
  `drafting`, by what the state machine already has a precedent for; say which in the handoff.
* No ADR unless the precedence or when-it-applies decision does not fit ADR-0100 — then the ADR
  first, before code. `apps/ideapress/api.md` is edited in `WeightRoom/docs` first and mirrored
  byte-identical into `IdeaPress/docs`.

## Gates

**Gate A — the document and the body.** Failing tests first: a flat `PUT` accepted, the `GET`
document's keys, the refusals unchanged. Then the implementation; IdeaPress's gate green. Commit.

**Gate B — rows applied and clearable.** Tests for file-only, row-over-file, environment-over-row
and a cleared row, and for when each key takes effect. Commit.

**Gate C — the stranded unit.** The failing case first: a draft whose bound model is missing, then
a second run of the same stage on the same unit. The fix. Commit.

**Gate D — the console and the docs.** Any WeightRoomGym test fixture that mocks IdeaPress's old
shape updated, WeightRoomGym's gate green; `api.md` §6 canonical and mirrored;
`history/handoffs/WI1_HANDOFF.md`; the row marked done. Commit in each repository.

## Demonstrate

On the reference machine, with `ideapress.service` restarted after the commits (a unit runs its
repository's editable install — W9_HANDOFF.md §5 item 3), through a throwaway console as W9 ran
one:

1. The console's Settings page for IdeaPress shows live values with their sources; one runtime key
   (e.g. `workflow.max_revision_rounds`) changed from the console, seen applied, and set back.
2. W9's leftover `models.stages.draft` row cleared through `PUT /settings`; the effective binding is
   `config.toml`'s `ollama/qwen3.5:9b-q8_0`, sourced from the file.
3. The draft stage run again on project `01M26M2QJQD5VK73X476GVB1CJ` unit U-01, and it drafts.

## Finish line

Gates green with the interpreter named, one commit per gate, `WI1_HANDOFF.md`, the row marked done.
Nothing pushed or tagged.
