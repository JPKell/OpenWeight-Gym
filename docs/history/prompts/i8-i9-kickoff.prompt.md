# Kickoff — I8 + I9: the runtime-settings surface, finished

**Rows:** I8 and I9 of [`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md) §1,
run as **one row** (operator's decision, 2026-09-07 interview).
**Ships:** `loadcoach 1.1.2`, then `promptcadence 1.2.0`. Two repositories, two releases, one
subject — the settings surface [ADR-0100](../../adr/0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)
opened. Suggested model: **Sonnet 5 · high** (transcription against a shape already built and
tested, plus two small decisions).

**Order matters and is not negotiable.** Part 1 (LoadCoach) first, Part 2 (PromptCadence) second.
Part 2 bumps PromptCadence's minor, so it needs `v1.1.0` to exist: if `git tag` in
`/home/jpk/ai/suite/PromptCadence` does not list `v1.1.0`, or `pip index versions promptcadence`
does not show `1.1.0`, **do Part 1, write the handoff, and stop** — say exactly that in the
handoff. This is the same version edge that made I4 run before I5.

**Concurrency.** Row I6 may be running in another session against the same workspace. It touches
`py/ModelRack` and `docs/` only. If it is running: **do not run the preamble's
`git checkout -- <path>` cleanup in `docs/`** — you would destroy its uncommitted work — and treat
a gate that goes red while its Ollama probe is loading models as unproven rather than failed
(re-run it when the machine is idle). Touch only the `docs/` files this prompt names.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.**
  `/home/jpk/ai/suite/LoadCoach` for Part 1, `/home/jpk/ai/suite/PromptCadence` for Part 2, each
  with its own `.venv/bin/python`. `pip install -e ".[dev]"` if anything is missing.
* **House method:** docstring-first (behaviour → Google-style docstring, including what the
  function *refuses* → tests → implementation), `from __future__ import annotations` in every
  module, units in every numeric name, keyword-only for anything optional or boolean, injected
  clocks/providers/roots, `@dataclass(frozen=True, slots=True)` for value objects, line length 100,
  `mypy --strict` with no bare `Any` at a public boundary and no `# type: ignore` without a
  trailing reason. Route handlers call one service method and render.
* **Finish line, per repository:** `ruff format --check . && ruff check . && mypy src tests &&
  lint-imports && pytest -m "not live and not performance"` green, plus `pytest --cov` at or above
  the floor (85 % apps). `CHANGELOG.md` updated. One Conventional Commit per gate. **Name the
  interpreter and the exact invocation in the handoff** (M5C-13).
* **Documentation is mirrored.** Edit the workspace copy under `/home/jpk/ai/suite/docs/` first,
  then copy byte-identically into the component's own `docs/`. Verify with `cmp`, never by eye.
* **Do not push, do not tag, do not publish.** Standing instruction of 2026-09-04: commit as usual,
  never run `git push` in any suite repo — not even a dry run.
* **Run `git status --short` at the start and at the end** in every repo you touch.

---

# Part 1 — I8: LoadCoach stops letting a stored row beat the environment

**Ships `loadcoach 1.1.2`** on top of `1.1.1` (`2a7ac58`, tagged, published).

## What this part is

[Configuration standards §7](../../standards/configuration-standards.md) states three rules for
database-backed settings. LoadCoach — which invented the registry the rest of the suite
transcribes — keeps the first and breaks the other two:

1. *Database-backed settings sit between file and environment:*
   `defaults → file → database → env → CLI`. **Broken.**
   `loadcoach.services.settings.read_runtime_settings` takes the stored value whenever a row
   exists, so a `settings` row beats `LOADCOACH_*` in the environment and a `loadcoach serve
   --port`-style flag. LoadCoach's own generated `docs/configuration.md` publishes the chain it
   does not implement.
2. *Anything security-relevant is file/env/CLI only.* **Kept** — `CONFIG_ONLY_SECURITY_KEYS`.
3. *`config show` marks database-sourced values `(database)`.* **Broken.**
   `src/loadcoach/cli/commands/config.py` `show` renders `loaded.sources` and opens no database.

Both were found by row I5 while building the same surface in PromptCadence
([`I5_HANDOFF.md`](../handoffs/I5_HANDOFF.md) §7), and PromptCadence now implements all three. **This part is a
transcription back**, not a second design: read
`PromptCadence/src/promptcadence/services/settings.py` and
`PromptCadence/src/promptcadence/cli/commands/config.py` first, and follow them.

## Reading list

1. [`standards/configuration-standards.md`](../../standards/configuration-standards.md) §7 and §8.
2. [`adr/0100-…`](../../adr/0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md) —
   rule 5 and the first bullet of **Consequences**, which is this part's charter and names the fix.
3. [`apps/loadcoach/api.md`](../../apps/loadcoach/api.md) §9 — the documented contract you are
   amending.
4. PromptCadence, as the source to transcribe: `services/settings.py` (`shadowing_source`,
   `read_runtime_settings`, `runtime_settings_document`), `config.py` `env_var_for`,
   `cli/commands/config.py` `_database_overlay`, `web/routes/settings.py`,
   `web/templates/settings/index.html`, and the tests
   `tests/unit/test_runtime_settings.py` + `tests/unit/test_cli.py`.
5. [`history/handoffs/I5_HANDOFF.md`](../handoffs/I5_HANDOFF.md) §3 (D2) and §7.

## The ground, already checked — do not spend the session rediscovering it

* `src/loadcoach/services/settings.py` — `RUNTIME_SETTINGS` holds **seven** keys, two of them
  booleans: `queue.paused`, `queue.draining`, four `routing.*` floats, and
  `storage.content_retention_hours`. `read_runtime_settings` coerces a stored row and falls back to
  configuration when it cannot (that half is already right and PromptCadence copied it).
* `src/loadcoach/services/worker.py:428` `apply_runtime_settings` applies at the flags cadence
  (one second). Nothing about the cadence changes in this part.
* `src/loadcoach/config.py:1042` — `load_settings(cli_overrides=…)` exists, and **nothing in
  `src/` passes it**: only `tests/unit/test_config.py` does. `serve` sets `LOADCOACH_CONFIG`,
  `LOADCOACH_SERVER__HOST` and `LOADCOACH_SERVER__PORT` as environment variables
  (`cli/commands/system.py:42-46`) and calls `load_settings()` with no arguments — the same shape
  as PromptCadence's `bootstrap`.
* `src/loadcoach/bootstrap.py:45` holds a `LoadedSettings` (with its `sources` map). Whether that
  map reaches the serving process is D2 below; check before deciding.
* `src/loadcoach/cli/commands/config.py` `show` prints
  `f"{path:<40} {rendered!s:<24} ({source})"` and must keep working when the database is absent,
  unmigrated or unreadable — a `config show` that needs a database is a regression.
* `src/loadcoach/web/routes/settings.py` and `web/templates/settings/index.html` render
  `document.definitions[key].configured`; the document has no `stored`, `source` or `shadowed_by`
  today.

## The decisions this part makes

### D1 — do the two control flags follow the same precedence?

`queue.paused` and `queue.draining` are operational controls, not tuning numbers: an operator
pausing dispatch from the console is doing something urgent. If the same rule applies, then
`LOADCOACH_QUEUE__PAUSED=true` in a unit file would make the console's pause button store a row
that does nothing.

**Recommendation: one rule for every key, flags included.** The standard states no exception, a
per-key exception is a second rule nobody would remember, and the failure it prevents is worse than
the one it causes: a paused queue that unpauses itself on restart because the environment said so
is a queue whose state nobody can explain. The mitigation is *visibility* — the shadowed row must
be reported (D3) and the page must say, at the flag, that the environment is holding it. If you
decide otherwise, the exception is an ADR (next free number after 0100; check `docs/adr/`), not a
comment, and it must say what an operator sees when the two disagree.

### D2 — `LoadedSettings.sources`, or `os.environ`?

PromptCadence checks `os.environ` through a shared `env_var_for` helper, because its loader
provably has no CLI layer. LoadCoach's loader **accepts** `cli_overrides` even though nothing
passes it, so the same argument is one refactor away from being wrong.

**Recommendation: plumb `sources` if it costs less than about twenty lines** (bootstrap already
holds `LoadedSettings`; the question is whether the runtime/scheduler can carry the map to
`read_runtime_settings` without changing a documented pure function's signature). If it costs more,
use the `os.environ` check exactly as PromptCadence does, add the shared `env_var_for` helper to
`loadcoach/config.py` so the loader and the check cannot spell a variable differently, **and** add
a test asserting no module under `src/` calls `load_settings` with `cli_overrides` — so the day
someone adds a CLI layer, one named test fails instead of the precedence silently mis-ordering.
Whichever you choose, say in the handoff what the other would have cost.

### D3 — what the document says about a row that does nothing

**Recommendation: PromptCadence's shape, key for key**, so an operator moving between the two
consoles reads one vocabulary: each definition gains `stored` (the row or `null`), `source`
(`"database"` or `"configuration"`) and `shadowed_by` (`"env LOADCOACH_…"` or `null`). The page
prints the same beneath each field. A stored row is **kept**, never deleted, when it turns out to
be shadowed: unsetting the variable makes it effective again, and that is the behaviour to test in
both directions.

## The work, in gate order

**Gate A — precedence in the service.** `read_runtime_settings` ignores a stored row whose key the
environment (or CLI, per D2) pins; `runtime_settings_document` gains D3's three fields. Unit tests:
the environment beats a stored row; the row takes effect again once the variable is unset; an
unreadable row still falls back to configuration; a shadowed row is still *reported*. Include one
test per boolean flag, per D1.

**Gate B — the surfaces.** `GET /settings` carries the new fields; the Settings page prints the
shadow beneath the field it belongs to; `apps/loadcoach/api.md` §9 gains the precedence sentence
and the new body fields, mirrored into `LoadCoach/docs/apps/loadcoach/api.md` and `cmp`-verified.
Tests over HTTP and over the rendered page.

**Gate C — `config show` marks `(database)`.** Transcribe PromptCadence's `_database_overlay`: open
the configured database read-only if there is one, mark each key the table decides `(database)` and
print the stored value; mark a shadowed row beside the variable that beats it. **Never raises for
storage**, and — PromptCadence's own refinement — does not create a missing SQLite file, because an
inspection command must not leave a database behind that `db status` would call unmigrated. Test
both paths.

**Gate D — documentation and the generated reference.** LoadCoach's `services/config_reference.py`
header must state the precedence it now implements and the `(database)` mark. Regenerate
`docs/configuration.md` and let its byte-comparison test pass. If LoadCoach's **Runtime-changeable**
column is a literal rather than driven by `RUNTIME_SETTINGS`, drive it from the registry (ADR-0100
rule 2's reasoning applies to the application that invented the registry too).

**No ADR unless D1 goes the other way.** ADR-0100's Consequences already name this fix; implementing
a published standard needs no new record. Add an **Amended-by**-style note only if the house
convention in `docs/adr/README.md` calls for one.

**Gate E — the release.** `CHANGELOG.md` `[Unreleased]` → `## [1.1.2]` with a fresh empty
`[Unreleased]`; `src/loadcoach/__about__.py` `1.1.1` → `1.1.2`; regenerate any versioned snapshot
the repo commits (`docs/openapi.json` if LoadCoach carries one); full gate plus `pytest --cov`;
commit `chore(release): loadcoach 1.1.2`. **Stop there** — the tag and the publish are the
operator's.

## Part 1 exit conditions

1. Full gate green on a named interpreter, coverage at or above the floor.
2. With `LOADCOACH_STORAGE__CONTENT_RETENTION_HOURS` set, a `PUT /settings` storing a different
   value answers with the environment's value effective, the stored row visible, and
   `shadowed_by` naming the variable. Unsetting the variable makes the stored row effective.
3. `loadcoach config show` marks a database-sourced value `(database)`; with no database it prints
   exactly what 1.1.1 printed, and creates no file.
4. `docs/configuration.md` regenerates and its test passes; `cmp` silent for every mirrored file.
5. `git status --short` clean, work committed, nothing pushed.

---

# Part 2 — I9: `promptcadence settings`, the CLI half

**Ships `promptcadence 1.2.0`** on top of `1.1.0`. **Do not start unless `v1.1.0` is tagged and
`promptcadence 1.1.0` is on PyPI** (see the header).

## What this part is

I5 built the registry, the API and the console page, and deliberately skipped a CLI verb
([`I5_HANDOFF.md`](../handoffs/I5_HANDOFF.md) §7). The operator asked for it at the 2026-09-07 interview: a
setting should be changeable from a script or over ssh without hand-writing `curl`.

`promptcadence config show` already answers the read-side question **without a server**, by opening
the database directly. This verb is the other kind: a **client-mode** command that talks to a
running PromptCadence over HTTP, the way `promptcadence approve` and `deny` do, so it enforces the
same scopes and surfaces the same refusals.

## Reading list

1. [`apps/promptcadence/spec.md`](../../apps/promptcadence/spec.md) §7.2 (the CLI list you are adding
   to) and §7.1 (the endpoints it calls).
2. `PromptCadence/src/promptcadence/cli/commands/approvals.py` — the client-mode precedent:
   `$PROMPTCADENCE_API_TOKEN` or `--token`, the base URL, how a refusal's code and message reach
   the operator, and the exit codes.
3. `PromptCadence/src/promptcadence/services/settings.py` — `RUNTIME_SETTINGS` is the vocabulary;
   the CLI must not restate it.
4. `PromptCadence/docs/quickstart.md` and `operations.md` — where an operator would look for it.

## The decisions this part makes

### D4 — the verb's shape

**Recommendation:** `promptcadence settings list [--json]`, `settings get <key> [--json]`,
`settings set <key> <value> [--token …] [--json]`. `list` and `get` are `read`-scoped calls;
`set` is `admin`. `set` prints the key's effective value **after** the write and says when it
differs from what was sent — a value shadowed by the environment must not read as a success, and
the API already reports `shadowed_by`. A refusal prints the code and the message the API gave
(`FORBIDDEN` naming the key, `VALIDATION_ERROR` listing what may change), never a stack trace.

### D5 — exit codes

**Recommendation:** the repo's existing convention, taken from the neighbouring client-mode
commands rather than invented — read `approvals.py` and match it. Whatever it is, `set` must exit
non-zero on a refusal, and the handoff states the mapping.

## The work, in gate order

**Gate F — the command.** `cli/commands/settings.py`, registered in `cli/main.py`. No business
logic: it calls the API and renders. Tests with `CliRunner` against a `TestClient`-backed
application, covering both refusals, the shadowed-value message, `--json`, and the missing-token
path.

**Gate G — documentation.** Workspace `apps/promptcadence/spec.md` §7.2 gains the verb, mirrored
and `cmp`-verified; `docs/quickstart.md` or `operations.md` gains the one example an operator will
copy; `CHANGELOG.md` `[Unreleased]` → `## [1.2.0]`; `__about__.py` → `1.2.0`; regenerate
`docs/openapi.json` for `info.version` (no path moves — this part adds no endpoint); full gate plus
`pytest --cov`; commit `chore(release): promptcadence 1.2.0`. **Stop there.**

## Part 2 exit conditions

1. Full gate green, coverage at or above 85 %.
2. `promptcadence settings set execution.step_retries 3` against a running server changes the
   value, and `settings get execution.step_retries` reads it back.
3. The same `set` for `server.host` prints `FORBIDDEN` naming the key and exits non-zero; for an
   unknown key, `VALIDATION_ERROR` listing the changeable set.
4. With the key pinned in the environment, `set` reports the stored value as shadowed rather than
   as applied.
5. `cmp` silent for every mirrored document; `docs/openapi.json` differs only in `info.version`.
6. `git status --short` clean in both repositories, work committed, nothing pushed.

---

## The handoff

One document, `docs/history/handoffs/I8_I9_HANDOFF.md`, in the house shape:

1. Gate results with the exact invocations and the interpreter — **per repository**, both named.
2. The gates as commits, per repository.
3. **The five decisions** (D1–D5), each with what the losing option would have claimed.
4. Exit conditions, both lists, answered one by one.
5. **Things this prompt said that turned out not to be true** — line numbers were read on
   2026-09-07 and will have moved; say where the reasoning was wrong, not just the citations.
6. What the operator still has to do: tag `v1.1.2` on LoadCoach and `v1.2.0` on PromptCadence,
   approve each `pypi` environment, publish, push three repositories.
7. Anything found that belongs to another row. In particular: **FreeWeight has a `settings` table
   and the same repository shape** — if it too resolves stored settings against the standard
   wrongly, that is a finding, not a fix in this row.

## Constraints

* **Part 1 before Part 2**, and Part 2 not at all without `v1.1.0` published.
* **No new runtime-changeable keys** in either application. Both registries are as ADR-0100 and
  api.md §9 left them; this row changes *how* stored values resolve and *who can read them*, not
  which keys exist.
* **No second design.** PromptCadence's implementation is the source; a divergence is a defect in
  this row unless the handoff argues it.
* **Never weaken `.importlinter`** in either repository.
* If the work must stop early, stop at a green gate with a commit, and say exactly where you
  stopped and what remains.
