# WI1 Handoff — IdeaPress: runtime settings in the suite's shape and applied; a unit a failed stage strands

**Row:** WI1 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Opus 5 · high).
**Date:** 2026-09-10. **Kickoff:**
[`wi1-ideapress-runtime-settings-and-stuck-unit.prompt.md`](../prompts/wi1-ideapress-runtime-settings-and-stuck-unit.prompt.md).
**Ships:** IdeaPress changes under `CHANGELOG.md`'s `[Unreleased]`; **no version bump**
(`__about__.py` stays `1.5.0`), nothing tagged, pushed or published. Built on `main` in
`~/ai/suite/IdeaPress`, plus one test commit and this docs commit in `~/ai/suite/WeightRoom`.

## 1. What was built, by commit

| Repository | Commit | Gate | What |
|---|---|---|---|
| IdeaPress | `1b5c51a` | A | `services/settings.py` — the suite's document (`settings`, `definitions` with `type`, `description`, `minimum`, `maximum`, `configured`, `stored`, `source`, `shadowed_by`, and `config_only`), resolved over the configured settings; `PUT /settings` takes a flat object and answers the document; a value is validated by its own pydantic field before it is stored. A configuration-only key is now **`403 FORBIDDEN`** naming it (it answered `422` although api.md §6 said 403). `config_schema.runtime_changeable_entries()` shared for type and bounds; `settings_registry.ALL_RUNTIME_KEYS`. OpenAPI snapshot regenerated |
| IdeaPress | `2871648` | B | Stored rows applied with ADR-0100 rule 5's precedence: `Runtime` keeps `configured` pristine and hands its handles a deep copy, which `Runtime.refresh_settings()` brings up to date at `start_plan` and `start_stage`. `null` in `PUT` removes a key's row. Every definition carries `applies: "next_stage"`. `inference.mode` and `logging.level` left the runtime-changeable set (§2 item 2); the schema golden follows |
| IdeaPress | `74462c8` | C | `draft_body` runs M7's `reset_orphaned_units` on **every** run, not only `--resume`, so a unit a failed run left in `drafting` is reset to `paused` (with `unit.reset`) and re-entered |
| IdeaPress | `74f064d` | D | `docs/apps/ideapress/api.md` mirrored byte-identical from `WeightRoom/docs` |
| IdeaPress | `f104b51` | D (found by the demonstration, §4.1) | `_track_sources` descends into nested sections (`models.stages.draft`, `inference.ollama.base_url`); `config schema --json` and `config show` overlay `database` — or `env …; database row … shadowed` — from the `settings` table, never creating a database that does not exist; `config show` prints the stored value it marks (configuration standards §7) |
| WeightRoom | `013c3b3` | D | `tests/fixtures/schemas/ideapress.json` and the IdeaPress form golden: the two keys move from runtime to config-only. No console test mocked IdeaPress's old `GET`/`PUT` shape — the console's settings tests mock LoadCoach only |
| WeightRoom | this commit | D | `apps/ideapress/api.md` §6 rewritten (canonical), this handoff, the row marked done |

**The gate, IdeaPress**, Python **3.13.15** (`~/ai/suite/IdeaPress/.venv/bin/…`): `ruff format
--check` and `ruff check` clean, `mypy src tests` clean (210 files), `lint-imports` 4 kept,
`pytest -m "not live and not performance"` **1290 passed, 6 skipped, 30 deselected** on `f104b51`
(baseline before the row: 1260 passed) — the final run with `XDG_DATA_HOME`, `XDG_CONFIG_HOME`,
`XDG_STATE_HOME` and `IDEAPRESS_DATA_DIR` pointed at scratch for the **whole process**, because a
plain run on this machine writes test projects into the operator's real IdeaPress database and now
errors on it (§5 item 4g). **WeightRoom**, Python **3.14.4** (`.venv/bin/…`, the venv
*not* activated — see §5 item 4d): ruff clean, mypy clean (187 files), `lint-imports` 5 kept,
`pytest` **1462 passed, 3 skipped** on `013c3b3`. `docs/scripts/sync_component_docs.py --check`
exits 0.

## 2. What the kickoff and the docs did not settle, and where this row put it

1. **When a stored value takes effect: as the next stage starts.** Every remaining
   runtime-changeable key is read by a stage and by nothing else — the workflow limits by the unit
   and review loops, a binding by the gateway on every model call — and every model call reaches
   the gateway through `start_plan` or `start_stage` (`POST …/revise` included). So
   `Runtime.refresh_settings()` runs there, in whichever process starts the stage (the served one or
   the CLI), and nothing applies a value sooner. `PUT` itself touches only the table. One edge,
   written into api.md §6: the settings a process's stages read are shared, so a stage started on
   one project refreshes them under a stage already running on another project in the same
   process, which may then see the change from its next unit or model call.
2. **`inference.mode` and `logging.level` are no longer runtime-changeable.** The backend is built,
   and logging configured, once per process; neither can be honoured at a stage start. The kickoff
   allowed "a restart" as an answer, but a stored row that takes effect only on restart is what
   ADR-0100 refuses ("a UI that reports a change and a loop that ignores it until a restart nobody
   was told to perform"), and its rule 1 is the test: a key nothing re-reads is not
   runtime-changeable. Out of the set, the console writes them to `config.toml` and shows
   *restart*/*pending restart* (ADR-0127 rule 5) — which a database row would have evaded — and
   `ideapress backend use` already writes `inference.mode` to the file. **No ADR:** this applies
   ADR-0100 rather than departing from it. Keeping either key runtime-changeable would need an ADR,
   startup application of rows before the backend is built, and a way for the console to show the
   pending restart.
3. **Clearing a row.** Neither LoadCoach nor PromptCadence has a convention, so `null` removes the
   key's row, as the kickoff's fallback said. `null` for a key with no row changes nothing; the
   configuration-only and unknown-key refusals apply to `null` exactly as to a value, and a mixed
   request still writes nothing.
4. **The stranded unit: a re-run takes a unit a failed task left in `drafting`.** The state machine's
   precedent is M7 finding 1b's `reset_orphaned_units`: an in-flight unit whose owning run is
   demonstrably gone moves to `paused`, which has the `drafting` arrow — it simply ran only under
   `--resume`. Returning the unit to the state it started from has no precedent: from `planned` it
   needs a `drafting → planned` arrow data model §3 does not have. So every draft run now runs the
   reset first. Two consequences: between the failed run and the next one the unit still reads
   `drafting` (visible, and the next run explains itself with `unit.reset`); and the reset's
   liveness refusal now applies to plain runs too — a run with no recorded owner still marked
   `running` blocks a plain draft on that project, as it already blocked `--resume`.
5. **Refusal codes.** Configuration-only is `403 FORBIDDEN` (a code added to the status map
   alongside `CSRF_FAILED`, outside spec §13's fifteen). An unknown key or a refused value stays
   IdeaPress's `422 VALIDATION_FAILED`; LoadCoach and PromptCadence answer those `400
   VALIDATION_ERROR`. Kept, as "the refusals unchanged"; the console shows the envelope's message
   whatever the code.
6. **`applies`** is an additive, IdeaPress-only field in each definition. The console does not read
   it yet (§5 item 4a).
7. **`sources` were wrong on the console** (§4.1): not in the kickoff, but criterion 1 ("live values
   with their sources") could not be shown truthfully without it, so it rides this row as `f104b51`.

## 3. Decisions inside the implementation worth knowing

* **One module**, `services/settings.py`, holds resolution, the write, the document, the database
  source overlay and `apply_runtime_settings`; the key list stays in `settings_registry.py` and the
  per-key type and bounds come from `config_schema.runtime_changeable_entries()` — no key list is
  copied.
* **A value is validated by re-validating its own model** (`type(parent).model_validate({**dump,
  field: value})`), so `PUT` accepts exactly what the file could hold, with pydantic's lax
  coercion (`"3"` → `3`), and stores the coerced value.
* **A row this build cannot read** falls back to configuration and reports `source:
  "configuration"` with the row under `stored` — stricter than LoadCoach, whose document says
  `database` for such a row while serving the configured value.
* **Shadowing** checks `IDEAPRESS_<SECTION>__<FIELD>`, nested for bindings
  (`IDEAPRESS_MODELS__STAGES__DRAFT`); `ideapress serve` sets its flags as environment variables, so
  that covers the CLI layer.
* **`Runtime.settings` is now a copy.** Code that wants what was configured reads
  `Runtime.configured`; the web routes keep using `app.state.settings`, which is that same object.
* **Regenerating the schema golden** (`tests/unit/goldens/config_schema_1_0.json`): with
  `XDG_CONFIG_HOME=/golden/config IDEAPRESS_DATA_DIR=/golden/data`, `json.dumps(document, indent=2,
  sort_keys=True, ensure_ascii=False) + "\n"` — without `ensure_ascii=False` every `—` and `§` in
  the descriptions churns.

## 4. Demonstration on the reference machine

`ideapress.service` restarted after the commits — at 16:31 PDT (Gates A–D) and 16:39 PDT
(`f104b51`) — so the unit ran the new editable install. A throwaway console on `127.0.0.1:8781`
(open loopback; WeightRoom's `.venv`, Python 3.14.4; scratch `XDG_*`; a config naming only
`[apps.ideapress]`), driven by Playwright over system Chrome, stopped afterwards by its
environ-verified pid.

### 4.1 Criterion 1 — live values with their sources; one key changed from the console and set back

* **First pass, before `f104b51`:** the console showed `models.stages.draft` live as
  `ollama/gemma4:12b` (W9's row) labelled **`default`**, although the row decided it and
  `config.toml` set `ollama/qwen3.5:9b-q8_0`. IdeaPress's `config schema` tracked sources only to
  `section.field` and knew nothing of the table. Fixed in `f104b51`; the console restarted.
* **Before:** `workflow.max_revision_rounds` `3` · `default` · *live*; `models.stages.draft`
  `ollama/gemma4:12b` · **`database`** · *live*; `inference.mode` and `logging.level` · `default` ·
  *restart* (file path).
* **Changed to `2` from the console:** notice "1 applied live."; the row reloaded as `2` ·
  `database` · *live*; IdeaPress's own document: `settings` `2`, `configured 3`, `stored 2`,
  `source database`, `shadowed_by null`, `applies next_stage`. Audit row `settings.write ok`
  23:39:37Z, `applied: ["workflow.max_revision_rounds"]`.
* **Set back to `3` from the console:** "1 applied live."; `3` · `database`; IdeaPress `stored 3`,
  `source database`. Audit row 23:39:39Z. The console has no way to *clear* a row, so the set-back
  left a row equal to the configured value (§5 item 4b); it was removed with
  `PUT {"workflow.max_revision_rounds": null}` (HTTP 200, `stored null`, `source configuration`).

### 4.2 Criterion 2 — W9's leftover row cleared through `PUT /settings`

* `PUT /api/v1/settings {"models.stages.draft": null}` → **HTTP 200**; the document: `settings`
  `ollama/qwen3.5:9b-q8_0`, `configured ollama/qwen3.5:9b-q8_0`, `stored null`,
  `source configuration`, `applies next_stage`.
* The `settings` table afterwards: **empty**. `ideapress config schema --json` sources
  `models.stages.draft: file`; `ideapress config show`: `models.stages.draft
  'ollama/qwen3.5:9b-q8_0' [file]`; the console's row: `ollama/qwen3.5:9b-q8_0` · **`file`** · *live*.

### 4.3 Criterion 3 — the draft stage on project `01M26M2QJQD5VK73X476GVB1CJ` unit U-01

* Before: U-01 `drafting` (W9's stranded unit), U-02 `committed`, U-03 `planned`.
* `POST …/stages/draft/run {"units": ["U-01"]}` → **202**, task `01M26V3M7NFDJW9NWB9GZ2MNG9`,
  started 23:40:35Z. Events: `stage.started`; **`unit.reset` "U-01: an earlier run left it in
  'drafting'; reset to paused"**; `unit.started`; `attempt.started` "draft attempt 1 of 3".
* **It drafts.** The run then made, all on `ollama/qwen3.5:9b-q8_0@sha256:441ec31e4d2a…` — the
  file's binding, `prompt_source: pack`: draft attempt 1 (351 in / 7,841 out tokens, 185 s; one
  blocking validation failure), repair attempt 2 (22 checks passed), `audit_fast` (1 critical,
  escalated), `audit_deep` (1 critical), critique `materially_deficient`, revise round 1 — rejected,
  because it raised validation failures from 0 to 1, so the previous version was kept.
* The stage **completed** at 23:52:46Z (12 min 10 s), `units_completed 0`, `units_paused 1`. U-01
  is **`paused`**, not committed: "1 blocking requirement(s) have no deterministic check and no
  audit has attested them met: R-001." That is the content gate doing its job (ADR-0039), and a
  `paused` unit is runnable again — the defect this row fixed (a unit no stage could take) is gone.
  Whether U-01 ever commits is a matter of the brief and the model, not of this row; U-02
  `committed` and U-03 `planned` are unchanged.

## 5. For the operator

1. **Nothing pushed or tagged.** IdeaPress `1b5c51a`, `2871648`, `74462c8`, `74f064d`, `f104b51`;
   WeightRoom `013c3b3` and this docs commit.
2. **No version bump.** IdeaPress stays `1.5.0`; everything is under `[Unreleased]` (Changed:
   the document and body, rows applied, the two keys out; Fixed: 403, the stranded unit, sources).
   `PUT /settings`'s body change is breaking for any caller still sending `{"values": …}` — none in
   the suite; WeightRoomGym already sent the flat shape.
3. **The reference machine.** `ideapress.service` restarted twice (§4); no migration. IdeaPress's
   `settings` table is **empty** — W9's `models.stages.draft` row and the demonstration's own
   `workflow.max_revision_rounds` row both removed through `PUT /settings`. `config.toml`
   untouched. The throwaway console and its scratch state are gone with the session scratchpad.
4. **Found, not fixed:**
   a. **The console says "applied live"** (and its badge "no restart") for IdeaPress's runtime keys,
      which apply at the next stage start. The document now says so per key (`applies`); the
      console could show it when present — W10's Settings pass.
   b. **The console cannot clear a stored row.** Setting a runtime key back to its configured value
      stores a row equal to it, which silently beats a later edit of `config.toml` — W9's leftover
      row again. A *clear* control sending `null` (IdeaPress) is the fix; LoadCoach and
      PromptCadence have no clearing convention at all.
   c. The console's `settings.write` audit rows for a change to `workflow.max_revision_rounds` alone
      recorded `touched_security: true`. Looks wrong; not investigated.
   d. WeightRoom's `tests/unit/test_cli.py::test_units_sync_writes_reports_and_audits` fails when
      WeightRoom's `.venv/bin` is on `PATH` (an activated venv): `wr-gym` is then found, so
      `units sync` also writes `weightroom.service`. It passes with the tools invoked by path. A
      test-isolation defect, present before this row.
   e. `ideapress doctor`'s stage-binding check reads configuration (`diagnostics.py`), not stored
      rows, so a binding changed through `PUT /settings` is not what `doctor` checks.
   f. The shared-settings edge in §2 item 1 (a stage on another project may see a change before its
      own next start). Honest in api.md; a per-run snapshot would remove it.
   g. **IdeaPress's default test run writes into the operator's real IdeaPress data — since
      2026-08-31.** Two module-scoped fixtures, `tests/security/test_sanitization_sweep.py:161` and
      `tests/accessibility/test_ui_checklist.py:92` (and, nightly only,
      `tests/performance/test_budgets.py:168`), call `load_settings()` before the function-scoped
      `isolated_environment` fixture has redirected `XDG_*`/`IDEAPRESS_DATA_DIR`, so they build an
      application over `~/.local/share/ideapress/`. That database now holds **1186 projects, 999 of
      them titled "Local inference"** plus the sweep's `<script>` titles, with a matching directory
      each under `projects/` (created 2026-08-31 → 2026-09-10; this row's own gate runs added some
      of the 40 dated today). At 999 the slug allocator gives up, so a plain gate run now fails
      five tests with "Could not find a free slug for 'Local inference' after 998 attempts". **Not
      cleaned** — deleting rows and directories from your real database is your call, and project
      `01M26M2QJQD5VK73X476GVB1CJ` must survive it. The fix is the fixtures' own isolation
      (a module-scoped `MonkeyPatch` over a `tmp_path_factory` directory), then a cleanup of
      everything titled "Local inference…" with a backup first.

## 6. Open for later rows

* **W10** takes §5 items 4a–4c with its Settings and audit passes if the operator agrees; 4d belongs
  with W10's hardening.
* **§5 item 4g wants a row of its own before anyone next runs IdeaPress's suite on this machine
  unisolated** — the isolation fix in IdeaPress, then the cleanup of the real database.
* **If `inference.mode` or `logging.level` should be changeable from a form without a file edit**,
  that is an ADR first (§2 item 2), not a registry line.
