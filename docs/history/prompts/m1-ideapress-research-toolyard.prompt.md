# Kickoff — M1: IdeaPress's `research` stage runs its tools under ToolYard

**Row:** M1 (Opus 5 · high) of [`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md)
§1 — ToolYard's second consumer, the date the 2026-09-07 interview attached to keeping ToolYard a
package.
**Ships:** `ideapress 1.4.0`, prepared (release commit, untagged, unpushed) on top of `1.3.3`, also
carrying row M3's removal (already committed under `[Unreleased]` when you start).
**Component:** `/home/jpk/ai/suite/IdeaPress` plus the `docs` repository. ToolYard is consumed at
its published `0.1.1`; if you find ToolYard itself needs a change, record it as a finding for a
ToolYard row and work around it in IdeaPress — do not edit `py/ToolYard` tonight.

**Overnight, unattended.** The row's schedule column says "never overnight"; the operator
overrode that on 2026-09-07 ("execute rows M1–M3 overnight without my input, I trust your
judgement"), and that deviation is recorded in `roadmap/model-assignment.md` §3.5 by the
coordinator. So: the conservative option at every judgement call — narrower allowlist, more
refusals, smaller surface — every judgement in the handoff's decisions section, and never stop to
ask. If a decision cannot be taken conservatively, stop at a green gate and write it down.

---

## Standing preamble

* **Work from inside the component directory.** `IdeaPress/.venv/bin/python`;
  `pip install -e ".[dev]"` after adding the dependency.
* **Read before writing**, in this order: [`architecture/master-architecture.md`](../../architecture/master-architecture.md)
  §§1–3, the IdeaPress section of [`standards/gold-standards.md`](../../standards/gold-standards.md),
  then the reading list below — **all of it, before the first edit**.
* **House method:** docstring-first (behaviour → Google docstring including what the function
  *refuses* → tests → implementation), `from __future__ import annotations`, units in every numeric
  name, keyword-only optionals and booleans, injected clocks/HTTP clients/roots, frozen slotted
  dataclasses, line length 100, `mypy --strict`, no bare `Any` at a public boundary, no
  `# type: ignore` without a reason. Route handlers and CLI bodies call one service method.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green; `pytest --cov` ≥ 85 %. One Conventional Commit
  per gate. **Name the interpreter and the invocation in the handoff.**
* **Documentation is mirrored.** Edit `/home/jpk/ai/suite/WeightRoom/docs/` first, then copy byte-identically
  into `IdeaPress/docs/apps/ideapress/` (`spec.md`, `development-plan.md`, `workflows.md` and the
  other `apps/ideapress/*` files are mirrors); verify with `cmp`. **`IdeaPress/docs/README.md` is a
  repo-local index — never overwrite it.** The `docs` repository is shared with row M2 tonight:
  commit only the files you edited, by name; never `git add -A`.
* **Do not push, do not tag, do not publish.** Standing instruction of 2026-09-04.
* **`git status --short` at start and end** in every repository you touch; `git checkout --`
  anything modified that you did not edit.

## What this row is

IdeaPress's `research` stage has been specified since M6 (`apps/ideapress/workflows.md` §2, row 2:
"Brief, sources → source notes with citations; every note cites an available source; Optional")
and never built: workflows.md line ~70 says "no research backend ships at 1.0 … the ADR that adds a
research backend decides its binding then." **This row is that ADR and that backend**, built on
ToolYard rather than on a hand-rolled fetch:

* `http_fetch` and `read_file` from ToolYard (`toolyard.http_fetch_tool`, `toolyard.read_file_tool`)
  registered with a `ToolExecutor` whose validate → authorize → execute → record order ToolYard
  owns (`packages/toolyard/spec.md` §7, §11; ADR-0053, ADR-0056).
* One `TieredSandbox` per stage runner (`read_file` reads from the project's own workspace root
  only — the conservative bind set).
* A `ToolCallStore` implementation on **IdeaPress's own tables**: mount, never join. Read ADR-0050
  for the shape and PromptCadence's `infrastructure/tool_calls.py` (`CollectingToolCallStore`, flush
  onto the owning row) as the precedent. Migration `0010` — check
  `src/ideapress/infrastructure/db/migrations/versions/` for the next number first. Migrations
  run with SQLite foreign keys off (row H2's finding) — copy an existing migration's shape.
* The stage's tool **allowlist comes from configuration** (a new `[research]` block, or the nearest
  existing home — read `config.py` §-by-§ before adding one): allowed tools (default: both),
  allowed hosts (default: **empty — no host, so a fresh install fetches nothing until the operator
  names a host**; the conservative default), byte and time budgets with units in the names.
* **Commissioner decides egress before the fetch** (ADR-0073): IdeaPress already records
  `egress_decisions` (migration `0008`, `services/egress.py`, row J1 / ADR-0103) — route the
  research fetch through that same service so a denied host is a recorded decision *and* a
  `ToolResult` refusal on the unit's provenance, never an exception the stage swallows.
* **Every refusal is a `ToolResult`** on the unit's provenance table — visible in the unit view.
* **Research notes flow into `assemble_context`** — which deliberately reopens J2's dead
  `research_notes` path (`docs/history/handoffs/J2_HANDOFF.md` ~line 188 and row K3's comment in
  `services/review_loop.py:445`). J2 kept the reduction order (`research_notes` drop first) and
  the budget tests; now they have real input.
* The stage is **still Optional** (workflows.md row 2): a project with no URL in its brief and no
  configured host skips the stage exactly as today, and every 1.3 project and configuration loads
  unchanged.

## Reading list

1. `apps/ideapress/workflows.md` §2 (stages), the context-assembly section (~line 275–290:
   "relevant research notes … budgeted, ranked by explicit reference"; reduction order).
2. `apps/ideapress/spec.md` — the stage list, §21 future extensions (research backends), data
   ownership, and the M3-edited telemetry text (do not reopen it).
3. `apps/ideapress/development-plan.md` — find where `research` is deferred and add the phase.
4. `packages/toolyard/spec.md` §§7, 11, 13, 14 (the executor, the contracts, error behaviour,
   security) and `py/ToolYard/src/toolyard/` (`executor.py`, `store.py`, `sandbox.py`,
   `tools/fetch.py`, `tools/files.py`).
5. PromptCadence `services/tools.py` — the precedent consumer: `ToolPlant`, how one sandbox is
   built, how `http_fetch_tool` gets its resolver and Commissioner check, how the store is passed.
   Transcribe the *shape*; IdeaPress's stage runner is not an agent loop, so there is no plan
   step and no per-turn tool selection — the stage decides the calls from the brief's URLs.
6. `docs/history/handoffs/E4_HANDOFF.md` (PromptCadence Phase 4, the first consumer — what ToolYard's API
   turned out to cost), `docs/history/handoffs/D1_HANDOFF.md` (the sandbox's real behaviour: prlimit inside
   bwrap, bwrap forced via an injected `which`, podman never exercised — ADR-0111 drops it).
7. ADR-0050, ADR-0053, ADR-0056, ADR-0073, ADR-0103, ADR-0111, ADR-0114 (the dependency budget:
   adding `toolyard` to IdeaPress's runtime set is an enumerated-set change — update
   `tests/unit/test_packaging.py` and gold-standards §1.1's set, and say so in the ADR).
8. `docs/history/handoffs/J1_HANDOFF.md`, `J2_HANDOFF.md`, `K3_HANDOFF.md` — how the stage runner, the
   egress service and `assemble_context` actually look now.

## The ground, checked on 2026-09-07 — verify, do not rediscover

* Next free ADR is **0116** (M3 takes 0115 tonight). Write **ADR-0116** for the research backend:
  binding, allowlist default, the "URL in the brief" trigger, and the ADR-0114 set change. If a
  second decision needs its own ADR, **0117**.
* Latest IdeaPress migration is `0009_attempt_cache_token_classes.py`.
* `services/egress.py` and `egress_decisions` exist (J1). `services/stage_registry.py` and
  `services/stages.py` are the stage machinery; `config.py:384` maps `research_synthesis` to a
  model, `research` itself has no model (it uses none — tools only).
* IdeaPress's runtime dependency set (`pyproject.toml`) has no `toolyard`; PromptCadence pins
  `toolyard>=0.1.1,<0.2` — use the same range. Recompile `requirements/ci.lock` with
  `pip-compile <the header's own arguments, minus --no-index> -P toolyard`, pip-tools 7.6.1 on
  `/usr/bin/python3.13`, then prove the lock in a clean venv (`pip install --require-hashes -r
  requirements/ci.lock && pip install . --no-deps`, full gate).
* `docs/openapi.json` is guarded by `tests/contract/test_openapi_snapshot.py`; regenerate with
  `python -c "from tests.contract.test_openapi_snapshot import write; write()"` if a route moves
  (the unit view showing a refusal may not need a new route; a research-notes read endpoint would).
* `README.md`'s version line is guarded by `tests/unit/test_readme_version.py`, and the README's
  compatibility table by `tests/unit/test_readme_compatibility.py` — both move at the release gate.

## The work, in gate order

* **Gate A — docs first.** ADR-0116; `workflows.md` §2 row 2 and the "no research backend ships"
  paragraph; `spec.md` (stage, configuration block, data ownership: the new table, §21);
  `development-plan.md` (the phase, with what to run and what a person sees); gold-standards §1.1
  set. Mirror; `cmp`; commit in `docs` by file name.
* **Gate B — the store and migration.** Migration `0010`, repository, the `ToolCallStore`
  implementation, tests (round trip, refusal recorded, foreign key to the unit/attempt).
* **Gate C — the plant.** The IdeaPress equivalent of `ToolPlant`: one sandbox, one executor,
  registry of the two tools, allowlist from configuration, Commissioner egress through
  `services/egress.py`, resolver injected. Unit tests with a fake resolver and a fake HTTP
  transport — no network in the default suite.
* **Gate D — the stage.** `research` in the stage registry: URL extraction from the brief
  (conservative: only absolute `http(s)://` URLs appearing verbatim), one `http_fetch` per URL
  through the executor, notes assembled with the citation the workflow demands, refusals to
  provenance, then `assemble_context` consuming the notes (reopen the J2 path; K3's comment in
  `review_loop.py` updated). The stage skips cleanly with no URL / no host.
* **Gate E — the surface.** The unit view shows research notes and refusals (server-rendered, no
  new JS). CLI: whatever `ideapress` verb shows a unit's provenance shows the tool calls.
* **Gate F — the demonstration and the release.** Run the exit journey below on a fake HTTP
  transport (an `httpx.MockTransport` or a loopback server on 127.0.0.1 — a loopback host is a
  configured allowlist host for the demo); paste the evidence into the handoff. Then prepare
  **`ideapress 1.4.0`**: `## [1.4.0] - 2026-09-08` in `CHANGELOG.md` (absorbing `[Unreleased]`,
  which holds M3's line), `__about__.py`, README version line and compatibility table, `ci.lock`
  proved, `docs/openapi.json` regenerated. One commit `chore(release): 1.4.0`. **No tag, no
  push.**

## Exit conditions (the row's, verbatim, plus the house ones)

1. A project whose brief names a URL produces notes from it, with the call recorded on the unit's
   provenance table.
2. A disallowed host is refused **as a result**, visible on the unit, with an `egress_decisions`
   row and no exception.
3. A brief with no URL, or an installation with no allowed host, runs the workflow exactly as 1.3
   did — proven by the existing e2e journey still passing unchanged.
4. Full gate green on a named interpreter; coverage ≥ 85 %; lock proved in a clean venv.
5. `cmp` silent for every mirrored file; `git status --short` clean in both repositories; the
   release commit exists, untagged, unpushed.

## The handoff

Write `docs/history/handoffs/M1_HANDOFF.md` (row M1 of outstanding-work, not milestone M1), house shape:
gates as commits with invocations and interpreter; **every decision taken unattended**, each with
what the other option would have claimed; the exit conditions answered one by one with pasted
evidence; **what this prompt said that turned out not to be true**; what the operator still has
to do (tag `v1.4.0`, approve `pypi`, push `docs` and IdeaPress; enable nothing else); findings
that belong to another row — a ToolYard change you needed, anything in Commissioner. Then mark
row M1 done in `roadmap/outstanding-work.md` in row L8's style and commit that file by name.

## Constraints

* **Never weaken `.importlinter`.** `toolyard` joins the allowed set the way `commissioner` did at
  J1; no application import, no sibling package reaching into IdeaPress.
* **No model call in the `research` stage.** It is tools only; `research_synthesis` (stage 3) is
  the model stage and is not this row.
* **No new JS, no WebSocket, no background thread**: the stage runs inside the existing unit loop.
* **Do not edit `py/ToolYard`, `py/Commissioner` or PromptCadence.** Findings go in the handoff.
* **ADRs are superseded, never edited.**
* If the work must stop early, stop at a green gate with a commit and say exactly where; the
  release commit is only cut if every gate is green.
