# Kickoff — I5: PromptCadence 1.1, runtime settings

**Row:** I5 (Opus 5 · high) of [`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md) §1.
**Ships:** `promptcadence 1.1.0`, on top of `1.0.1`.
**Component:** `/home/jpk/ai/suite/PromptCadence` — one repository, one release. No other component
is edited by this row.

**The dependency is satisfied.** The version edge in §3 ("I4 before I5") required `1.0.1` to exist
before this row bumps the minor. It does: `v1.0.1` is tagged, `main` is clean and level with
`origin/main` (`9514d53`), and `promptcadence 1.0.1` is on PyPI. The `docs` repository is clean and
pushed. Nothing in the I4 publish sequence is still open.

**Overnight:** Opus rows may run unattended
([model-assignment §2.12](../../roadmap/model-assignment.md)); I5 is not on the never-overnight list.
But the decision at the centre of this row — *which keys a UI may change while the server runs* —
is a security decision, and the failure mode is a quiet over-permissive registry rather than a red
gate. If you run unattended, take the conservative option every time (fewer keys, more refusals)
and record every judgement call in the handoff's decisions section rather than stopping to ask.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.**
  `/home/jpk/ai/suite/PromptCadence`, its own venv (`.venv/bin/python`, Python 3.13.15 as of
  2026-09-06). `pip install -e ".[dev]"` if anything is missing.
* **Read before writing**, in this order:
  [`architecture/master-architecture.md`](../../architecture/master-architecture.md) §§1–3, the
  PromptCadence section of [`standards/gold-standards.md`](../../standards/gold-standards.md) §2, then
  the reading list below.
* **House method:** docstring-first (behaviour → Google-style docstring, including what the function
  *refuses* → tests → implementation), `from __future__ import annotations` in every module, units
  in every numeric name, keyword-only for anything optional or boolean, injected
  clocks/providers/roots, `@dataclass(frozen=True, slots=True)` for value objects, line length 100,
  `mypy --strict` with no bare `Any` at a public boundary and no `# type: ignore` without a trailing
  reason. Route handlers call one service method and render — no business logic in `web/`.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, plus `pytest --cov` at or above the 85 % floor.
  `CHANGELOG.md` updated. One Conventional Commit per gate. **Name the interpreter and the exact
  invocation in the handoff** (M5C-13).
* **Documentation is mirrored.** Edit the workspace copy under `/home/jpk/ai/suite/WeightRoom/docs/` first,
  then copy byte-identically into `PromptCadence/docs/apps/promptcadence/`. Verify with `cmp`, never
  by eye. `spec.md`, `lifecycle.md` and `development-plan.md` are the mirrored files; everything
  else under `PromptCadence/docs/` (`configuration.md`, `security.md`, `troubleshooting.md`,
  `upgrading.md`, `operations.md`, `quickstart.md`, `openapi.json`) is repo-local.
* **Do not push, do not tag, do not publish.** Standing instruction of 2026-09-04: commit as usual,
  never run `git push` in any suite repo — not even a dry run. Tagging and the release workflow's
  `pypi` environment are the operator's, per run.
* **Run `git status --short` at the start and at the end** of the session in every repo you touch,
  and `git checkout --` anything modified that you did not edit.

---

## What this row is

Spec §7.1 lists `GET /settings` and `PUT /settings`. Neither is built, nothing defines which keys
are runtime-changeable, and `docs/troubleshooting.md` records the gap honestly rather than stubbing
it (I2 §5). The operator chose to **schedule** the row rather than strike the endpoints from the
spec (I2 interview, 2026-09-06). This row builds them — or, if the decision goes the other way for
a given key, records in the spec that PromptCadence deliberately has none of that kind.

The shape is LoadCoach's, transcribed, not a second design: a **registry** of runtime-changeable
keys shared by the API, the console page and the process that applies them, with the
security-relevant keys refused **by name**.

**The persistence already exists.** The `settings` table is Phase 1's
(`src/promptcadence/infrastructure/db/models.py:331`, created in migration `0001_initial_schema`
— see its line 141) and is unused. **This row adds no migration.** If you find yourself writing
one, stop and re-read: you have invented a key that needs a column, which is not this row.

The work is the registry, the loader question, and the surfaces.

## Reading list

1. [`apps/promptcadence/spec.md`](../../apps/promptcadence/spec.md) §7.1 (the endpoint list),
   §10 (data ownership), §12 (the whole configuration block — you are deciding which of these keys
   move at runtime) and §14 (scopes: "`admin` (settings, tokens)").
2. [`standards/configuration-standards.md`](../../standards/configuration-standards.md) §7 (the one
   precedence deviation, and the "never editable from the UI" rule) and §8 (the generated
   reference).
3. LoadCoach, as the precedent to transcribe: `src/loadcoach/services/settings.py` (the whole
   file — `RuntimeSetting`, `RUNTIME_SETTINGS`, `CONFIG_ONLY_SECURITY_KEYS`,
   `read_runtime_settings`, `write_runtime_settings`, `runtime_settings_document`),
   `src/loadcoach/web/routes/settings.py` (API pair + page + form post),
   `src/loadcoach/services/worker.py:428` (`apply_runtime_settings`, applied at the flags cadence),
   and [`apps/loadcoach/api.md`](../../apps/loadcoach/api.md) §9.
4. [`history/handoffs/I2_HANDOFF.md`](../handoffs/I2_HANDOFF.md) §5 (why the endpoints are unbuilt) and
   [`history/handoffs/I4_HANDOFF.md`](../handoffs/I4_HANDOFF.md) §6 (what I5 inherits: nothing but the version edge).
5. [`adr/0094-the-console-authenticates-as-the-api-does.md`](../../adr/0094-the-console-authenticates-as-the-api-does.md)
   — the console's auth and CSRF contract, which anticipated this page.

## The ground, already checked — do not spend the session rediscovering it

* `src/promptcadence/config.py` — `load_settings()` (line 769) merges **file → env → CLI** only and
  returns `LoadedSettings` with a `sources` map built by `_track_sources()` (line 745), one entry
  per leaf field, valued `default` / `file` / `env PROMPTCADENCE_…` / `cli`. There is no database
  layer anywhere in the loader, and the loader cannot have one at import time — the database URL is
  itself a setting.
* `src/promptcadence/services/config_reference.py` — the **Runtime-changeable** column is the
  literal string `no`, hard-coded at line 161, and the header prose says so at line 43.
  `tests/unit/test_config_reference.py` compares `docs/configuration.md` byte-for-byte against the
  render, so both move together. Regenerate with
  `promptcadence config reference --output docs/configuration.md`.
* `tests/contract/test_openapi_snapshot.py:60` asserts `"/api/v1/settings" not in paths` with the
  reason "unbuilt in 1.0 — a spec §7.1 promise, recorded", and the documented-endpoint list above it
  omits both. Both halves move, and `docs/openapi.json` is regenerated by that module's `write()`.
* `docs/troubleshooting.md` lines 66–70, the section "Spec §7.1 endpoints this build does not
  serve", is deleted by this row rather than reworded.
* `docs/security.md:53` — "`admin` | everything above; settings and tokens **when a runtime-settings
  API exists**". The conditional goes.
* `src/promptcadence/cli/commands/config.py` `show` (line 37) prints
  `f"{path:<48} {rendered!s:<24} ({source})"` from `loaded.sources`. It opens no database today, and
  must still work when the database is absent, unmigrated or unreadable — a `config show` that
  fails because the database is missing is a regression, not a feature.
* `src/promptcadence/services/worker.py` — `_thread_main` (line 339) has a reap cadence at
  `next_reap` (lines 342–357), which is this application's analogue of LoadCoach's flags cadence.
  `sweep_retention` (line 298) reads `self.settings.storage.content_retention_hours` directly at
  line 307; if that key becomes runtime-changeable, this read must go through the effective value or
  the stored row is a lie the UI tells.
* Console plumbing exists: nav list at `src/promptcadence/web/rendering.py:45`, one
  `templates/<page>/index.html` per page, `web/csrf.py:38` `render_form_page` (already a
  transcription of LoadCoach's), `web/auth.py:139` `require_scope`, routers registered in
  `web/app.py:276-283` (`/api/v1` for API routers, bare for `ui_router`).
* PromptCadence has **no** pause/drain concept — `queue.paused` / `queue.draining` have no
  counterpart here. Do not invent one; see the constraints.

## The decisions this row makes

Three, and they are the row. Everything else is transcription.

### D1 — the runtime-changeable set

**Rule from the standard (§7):** anything security-relevant — bind address, exposure flag, auth
tokens, remote-provider allowance, database URL, data root — is file/env/CLI only and never
editable from the UI. For this application, read that list through spec §14: exposure, egress,
credentials, **containment** and retention.

**Recommended set** (start here; add only with an argument in the handoff):

| Key | Why it can move |
|---|---|
| `storage.content_retention_hours` | LoadCoach's precedent, and the sweep already re-reads at the reap cadence. |
| `compaction.threshold` | A tuning number, bounded 0–1, read per turn; no security surface. |
| `execution.step_retries` | A tuning number under an existing envelope (ADR-0076). |
| `execution.max_turns_per_step` | Same envelope, same argument, bounded by a maximum. |
| `planning.corrective_retries` | A tuning number; the plan validator's behaviour is unchanged. |

**Recommended config-only, refused by name with `403 FORBIDDEN`:** everything under `server`;
`storage.database_url`; `storage.retain_content`; `loadcoach.base_url`, `api_key_env`,
`api_key_file`; `planning.enabled` and `planning.allow_request_override` (the bypass switch);
`approval.mode`, `gate_egress_at`, `gate_step_cost` (the human-in-the-loop gates *are* the egress
control); everything under `tools` (containment roots, the fetch allowlist and its classification
ceiling, the container image, the registry); every `tiers.<name>` field (`remote`,
`max_data_classification`, `pricing_file`); `policy.default_tier` and `escalation_order`;
`logging.include_content`.

**The budget ceilings are the interesting case, and the recommendation is config-only.** A UI that
can raise `budget.daily_money_ceiling` creates a second way to raise spend — one with no
`approval_requests` row behind it — beside the `ceiling_raise` approval the application already
has, whose whole point is that a raise is recorded with an approver. Two paths to the same money,
one of them unrecorded, is not a convenience. If you decide otherwise, that reasoning is what you
have to beat, in the handoff and in an ADR.

Whatever the set, it is **a registry in one module**, keyed by dotted path, with type and bounds per
key, exactly as LoadCoach's is — so the API, the page, the CLI and the generated reference cannot
disagree.

### D2 — precedence: does a stored row beat an environment variable?

Configuration standards §7 says database-backed settings sit **between file and env**:
`defaults → file → database → env → CLI`. LoadCoach's implementation does **not** do this — its
`read_runtime_settings` takes the stored value whenever a row exists, so a database row beats an
env var and a CLI flag.

`LoadedSettings.sources` already names the layer behind every leaf, so honouring the standard is a
few lines: ignore the stored row when that key's source is `env …` or `cli`, and say so in the
document `GET /settings` returns. **Recommendation: follow the standard**, because an operator who
pinned a value on the command line and finds a web form quietly overriding it has been lied to by
the precedence chain the reference document publishes.

Two consequences to carry through if you take the recommendation: the `GET` body should say, per
key, whether a stored value is *effective* or *shadowed by env/CLI* — a stored row that does nothing
must be visible as such, not silently discarded; and the divergence from LoadCoach is a suite-level
finding for the handoff, **not** a change to LoadCoach in this row. If instead you follow LoadCoach,
that contradicts a published standard and needs an ADR (next free number is **0100**) amending
configuration standards §7, not a comment.

### D3 — scopes, where spec §14 and the precedent disagree

Spec §14 lists `admin` as covering "settings, tokens". LoadCoach makes `GET /settings` **`read`**-
scoped and only `PUT` `admin`-scoped, which is what lets a read-only operator see the effective
configuration without being able to change it. **Recommendation: follow LoadCoach** — `GET` is
`read`, `PUT` is `admin`, the page renders for `read` and its POST refuses anything below `admin`
(ADR-0094's rule: the page enforces what the API enforces, and a `read` principal is not shown the
save button) — and **amend spec §14 to say "settings changes, tokens"** so the document states the
distinction rather than being read as forbidding the read.

---

## The work, in gate order

Each gate ends in a green gate run and its own Conventional Commit.

**Gate A — the registry.** `src/promptcadence/services/settings.py`: the `RuntimeSetting` value
object (key, kind, description, bounds, `coerce`), `RUNTIME_SETTINGS`, `CONFIG_ONLY_SECURITY_KEYS`,
`read_runtime_settings`, `write_runtime_settings`, `runtime_settings_document`, plus whatever
repository access the `settings` table needs (check for an existing repository under
`infrastructure/db/repositories/` before writing one). Unit tests: every key coerces and refuses at
its bounds; a security-relevant key is `FORBIDDEN` **naming the key**; an unknown key is
`VALIDATION_ERROR` naming it and listing the set; a stored row this build cannot read falls back to
configuration rather than raising; and D2's precedence, both directions.

**Gate B — something reads them.** Wire the effective values into the running process at the reap
cadence in `worker.py`, LoadCoach's `apply_runtime_settings` in shape. At minimum every key in the
set that the worker or the loop reads today must come from the effective value. A key nothing
re-reads is not runtime-changeable, whatever the registry says — if a key in your set cannot be
applied without a restart, it is not in the set. Test that a `write_runtime_settings` from outside
the worker changes behaviour within one cadence, with an injected clock.

**Gate C — the API.** `web/routes/settings.py`: `GET /settings` (D3's scope) and
`PUT /settings` (`admin`), registered in `web/app.py` under `/api/v1`. Error codes as above.
Regenerate `docs/openapi.json` via `tests/contract/test_openapi_snapshot.py`'s `write()`; move
`/api/v1/settings` from the negative assertion at line 60 into the documented-endpoint list.

**Gate D — the console.** A Settings page and its nav entry, the form rendered through
`render_form_page` with MirrorWall's double-submit token, booleans as present/absent and numbers as
text, redirecting to `…?saved=1`. Config-only keys are **listed on the page as config-only**, not
omitted — the page's job is to say what cannot be changed here as much as what can. Scope
behaviour per ADR-0094, tested both ways.

**Gate E — `config show` marks `(database)`.** The CLI opens the database if it can and marks each
effective database-sourced value `(database)`; if the database is missing or unmigrated, it prints
exactly what it prints today. Test both paths. **Skip a `promptcadence settings` CLI verb** — the
API and the console cover the surface; add one when an operator asks for it, and say so in the
handoff.

**Gate F — documentation.** In this order:
1. Workspace `docs/apps/promptcadence/spec.md`: §7.1 gains a bullet describing the pair (what `GET`
   returns, what `PUT` refuses and with which code, the scopes); §12's prose says which keys move at
   runtime and by which precedence, per configuration standards §8 — §12 is a TOML block plus
   prose, so this is prose, **not** a new column; §14's scope line per D3.
2. `cmp` the mirror into `PromptCadence/docs/apps/promptcadence/spec.md`.
3. `config_reference.py`: the column is driven by the registry, not the literal `no`, and the header
   paragraph at line 43 is rewritten to say what is runtime-changeable and how the database layer
   sits in the precedence chain. Regenerate `docs/configuration.md`.
4. Repo-local docs: delete the troubleshooting section (lines 66–70); fix `docs/security.md:53`;
   add the `1.1.0` line to `docs/upgrading.md` — **no migration, no schema change, no stored value
   changed**, and say that explicitly, since the table's contract is which revisions a version
   introduces.
5. `docs/apps/promptcadence/development-plan.md` gains a section for this release with
   *demonstrable* acceptance criteria (what to run, what a person should see), and is mirrored.

**Gate G — the release.** `CHANGELOG.md` `[Unreleased]` → `## [1.1.0]` with a fresh empty
`[Unreleased]` above; `src/promptcadence/__about__.py` `1.0.1` → `1.1.0` (version is `dynamic` via
hatch, so `pyproject.toml` does not carry it); regenerate `docs/openapi.json` for the `info.version`
line; full gate plus `pytest --cov`; commit `chore(release): promptcadence 1.1.0`. **Stop there.**

## Exit conditions

1. The full gate is green on a named interpreter, coverage at or above 85 %.
2. `PUT /settings` with a security-relevant key answers `403 FORBIDDEN` naming the key; with an
   unknown key, `400 VALIDATION_ERROR` naming it and listing the runtime-changeable set; with a
   valid key from a non-`admin` principal, `403`.
3. A change written through `PUT /settings` is observably applied by the running worker within one
   reap cadence, proven by a test with an injected clock rather than by inspection.
4. `promptcadence config show` marks a database-sourced value `(database)`, and prints its normal
   output when the database is absent.
5. `docs/configuration.md` regenerates with the Runtime-changeable column reading `yes` exactly for
   the registry's keys, and `tests/unit/test_config_reference.py` passes.
6. `docs/openapi.json` contains `/api/v1/settings`, the contract test's negative assertion is gone,
   and no other path moved.
7. `cmp` is silent for every mirrored document.
8. `git status --short` is clean in both repositories, with the work committed and nothing pushed.

## The handoff

Write `docs/history/handoffs/I5_HANDOFF.md`, in the house shape:

1. Gate results with the exact invocations and the interpreter.
2. The gates as commits.
3. **The three decisions**, each with what the losing option would have claimed — D1's set is the
   one a reviewer will read first, so justify each *inclusion*, not just the exclusions.
4. Exit conditions, answered one by one.
5. **Things this prompt said that turned out not to be true** — line numbers here were read on
   2026-09-06 and will have moved; more importantly, say where the reasoning was wrong, not just
   the citations.
6. What the operator still has to do: tag `v1.1.0`, approve the `pypi` environment, publish, push
   both repositories.
7. Anything found that belongs to another row — in particular LoadCoach's precedence divergence
   (D2), which is a finding, not a fix.

## Constraints

* **No migration.** The table exists.
* **No new configuration keys.** This row decides which *existing* keys move at runtime. A pause
  switch, a drain flag or a new tuning knob is a different row, however tempting the symmetry with
  LoadCoach's `queue.paused` looks.
* **One registry.** If the API, the page, the CLI and the reference generator can disagree about
  which keys are runtime-changeable, the row is not done.
* **Never weaken `.importlinter`** to make an import work.
* **ADRs are superseded, never edited.** If D2 or D1 lands against a published standard, write ADR
  **0100** (check `docs/adr/` for the next free number first) rather than a comment.
* If the work must stop early, stop at a green gate with a commit, and say exactly where you stopped
  and what remains.
