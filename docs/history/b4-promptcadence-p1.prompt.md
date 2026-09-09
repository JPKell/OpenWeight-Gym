# Kickoff — B4: PromptCadence Phase 1

**Row:** B4 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Sonnet 5 · high. **Repository:** `/home/jpk/ai/suite/PromptCadence` — **it does not exist
yet; creating it is the first task.** It is an application, so it lives at the workspace root beside
FreeWeight, LoadCoach and IdeaPress, not under `py/`.
**Runs after:** A2. Independent of B1, B2 and B3.
**Overnight:** permitted, at effort **high**
([model-assignment §2.12](docs/roadmap/model-assignment.md)).
**Order:** PromptCadence phases run **strictly P1 → P9, never reordered**
([outstanding-work §3](docs/roadmap/outstanding-work.md)). This is P1.

---

## Preconditions

```bash
pip index versions baseaicore     # must list 0.4.1
```

`DataClassification` ships in `0.4.1` and this phase's startup validation rejects unknown
classification values, so the type must be the published one. The Phase 1 prerequisites in the
development plan name it explicitly. If it is not published, **stop and say so** — do not vendor
the enum and do not pin a local path.

**The repository is yours to create locally; the remote is not.** The GitHub repository, the PyPI
name reservation and CI secrets are human steps
([outstanding-work §4](docs/roadmap/outstanding-work.md)). Create the local repository, commit to
`main`, and list the remote setup in your handoff document.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/PromptCadence`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3 —
  and §4, the application internal architecture, which this phase implements literally — then the
  PromptCadence section of
  [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2, then the reading list.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name; keyword-only for anything optional or
  boolean; injected clocks, HTTP clients and filesystem roots at every boundary;
  `@dataclass(frozen=True, slots=True)` for value objects; wire models are pydantic; SQLAlchemy
  models never leave the repository layer; line length 100; `mypy --strict` with no bare `Any` at a
  public boundary and no `# type: ignore` without a trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, `CHANGELOG.md` started, one Conventional
  Commit per logical group. **Name the interpreter and the exact invocation in the handoff doc**
  (M5C-13). Coverage floor for an application is **85 %**.
* **Dependency pinning:** `promptcadence` depends on `baseaicore`, `setspec`, `weightsdb` and
  `mirrorwall` — all published — plus fastapi/typer/sqlalchemy/alembic/httpx/jinja2 as the other
  applications do. The four new packages (`cutctx`, `toolyard`, `loadledger`, `spotcheck`) are
  **not** dependencies of this phase; add them when the phase that uses them arrives, and where one
  is still unpublished at that point, pin it as a local editable install with a
  `TODO: re-pin on publish`.
* **Documentation is mirrored.** The workspace copies under
  `/home/jpk/ai/suite/docs/apps/promptcadence/` are authoritative; copy `spec.md`,
  `lifecycle.md` and `development-plan.md` byte-identically into the new repo on creation and
  verify with `cmp`.
* **You are not authorised to tag or publish.** Nothing ships here — the first release is
  `0.9.0b0` at row G1.

## Setup

```bash
cd /home/jpk/ai/suite/PromptCadence      # already exists, with a .gitignore in place
git rev-parse --git-dir >/dev/null 2>&1 || git init -b main
python -m venv .venv && source .venv/bin/activate
# LoadCoach is the precedent for every file here — copy its toolchain and adapt names:
#   pyproject.toml  .importlinter  .editorconfig  .pre-commit-config.yaml
#   .github/workflows/ci.yml  alembic.ini + migrations/
pip install -e ".[dev]" && pre-commit install
```

The directory and its `.gitignore` are already in place — the `.gitignore` is the suite's
canonical one plus the import-linter cache line. **Do not overwrite it** when you copy the rest
of the toolchain from a sibling; copy every other file and leave that one alone.


**LoadCoach P1 is this phase's precedent in shape, file for file** — the row says so and the
development plan says the phase is "deliberately identical in shape". Read `LoadCoach/src/loadcoach`
before writing, and diverge only where the spec does.

## Reading list

1. [`docs/apps/promptcadence/spec.md`](docs/apps/promptcadence/spec.md) **§§1–8** — purpose, scope,
   non-goals, responsibilities, dependencies, consumers, public APIs, inputs. Then **§12
   (configuration)**, which is what you implement, and **§13 (error behaviour)** for the startup
   refusals.
2. [`docs/apps/promptcadence/development-plan.md`](docs/apps/promptcadence/development-plan.md)
   **Phase 1** — the work list, the tests and the two acceptance criteria. Everything that executes
   is deferred; read Phase 2 only to know what you are *not* building.
3. [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §4 — the
   `web` → `cli` → `services` → `domain` layering, and §1.1 for the canonical identifiers:
   import and distribution name `promptcadence`, **port 8768**, env prefix `PROMPTCADENCE_`,
   database `promptcadence.sqlite3`.
4. [ADR-0045](docs/adr/0045-promptcadence-reaches-models-only-through-loadcoach.md) (D-1) —
   **rules 2 and 3 are implemented in this phase**, one as an import contract and one as health
   behaviour.
5. [ADR-0026](docs/adr/0026-local-http-hardening.md) (loopback binding, Host allowlist, the
   auth-vs-binding refusal), [ADR-0006](docs/adr/0006-sqlite-and-postgresql-roles.md) and
   [ADR-0005](docs/adr/0005-database-strategy.md) (SQLAlchemy 2.0 + Alembic through WeightsDB),
   [ADR-0020](docs/adr/0020-ui-rendering-strategy.md) (server-rendered HTML, no SPA).
6. `LoadCoach/` — the repository layout, its `config.py` precedence handling, its `/system/status`
   shape and its `doctor`.

## The work

The goal is one sentence from the plan: **`promptcadence serve` starts, migrates, and reports
health honestly with nothing else running.**

### 1. Repository and import contracts

The standard application layout per master architecture §4, and `.importlinter` contracts written
**now**, not later:

* `web` and `cli` may import `services`; `services` may import `domain` and `infrastructure`;
  `domain` imports no framework (no fastapi, sqlalchemy, typer, httpx, jinja2).
* No application import, in either direction, including under `TYPE_CHECKING`.
* **`modelrack` and `sweatmeter` are forbidden imports.** This is not an accident of what the phase
  needs — it is [ADR-0045](docs/adr/0045-promptcadence-reaches-models-only-through-loadcoach.md)
  rule 2 and master architecture §11 item 19, and `.importlinter` is its mechanical form. A harness
  with direct provider access would own a second, ungoverned egress path. Write the contract in
  Phase 1 so no later phase can add the import casually.

### 2. `config.py` — the full spec §12 surface

Every section: `[server]`, `[storage]`, `[loadcoach]`, `[planning]`, `[approval]`, `[execution]`,
`[budget]`, `[tools]`, `[compaction]` and the four `[tiers.*]` blocks. Precedence is file →
environment → CLI flag, per the configuration standards, and it is tested **field by field**.

**Startup validation refuses rather than warns**, and every refusal has a message a person can act
on ([ADR-0047](docs/adr/0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md) §2,
spec §13):

* a remote tier without `max_data_classification`;
* a remote tier without a pricing source;
* an unknown classification value;
* a tier naming no task profile;
* non-loopback binding without authentication (ADR-0026);
* `approval.mode = "manual"` with no `approve`-scoped token defined — a mode nobody can satisfy is
  a configuration error, not a runtime surprise
  ([ADR-0049](docs/adr/0049-approval-is-a-mode-with-its-own-scope.md) rule 2).

The tier objects are *parsed and validated* here. Nothing resolves, routes or executes — that is
P2 and later.

### 3. Database

WeightsDB wiring, one Alembic history from migration `0001`, and the core tables only:
`trajectories`, `threads`, `turns`, `events`, `api_tokens`, `settings`. Migration up **and** down
on both dialects, plus backup/restore, are the tests.

Two forward-looking notes, so P2 does not have to undo this phase: the turn and trajectory rows
carry the LA0 optional adapter fields when they arrive (adapter-roadmap §4.5 — "born, not
retrofitted"), and `ledger_entries` / `egress_decisions` will be **mounted** into this same
metadata and history at P5/P6
([ADR-0050](docs/adr/0050-a-package-may-ship-tables-never-a-migration-history.md)). Do not create
either mounted table now; do leave the metadata module shaped so mounting at module import is
natural, since the named failure mode of that pattern is a host that mounts too late and
autogenerates a migration dropping the package's tables.

### 4. Web, CLI and health

MirrorWall base — envelopes, request IDs, the SSE helper, and the telemetry widget fed from
LoadCoach's `/system/status` when it is reachable. Then `GET /health`, `/version` and
`/system/status`, and the CLI: `promptcadence serve | health | version | config | db`, plus a
`doctor` skeleton.

**Honest degradation is the acceptance criterion, not a nicety.** With no LoadCoach reachable the
service starts, serves, and reports the `loadcoach` component **degraded** while HTTP stays 200.
PromptCadence requires LoadCoach for *execution*, never for *startup*
([ADR-0045](docs/adr/0045-promptcadence-reaches-models-only-through-loadcoach.md) rule 3) — and
since nothing executes in this phase, degraded-but-alive is the whole observable behaviour.

Route handlers and CLI command bodies contain **no business logic**: each calls one service method
and renders.

### 5. Documentation and repository furniture

`README.md` (status line: Phase 1, unreleased), `CHANGELOG.md` with `## [Unreleased]`, `LICENSE`
and `SECURITY.md` from LoadCoach, and the three mirrored documents under `docs/apps/promptcadence/`
verified with `cmp`.

### 6. Gate and commit

Full gate green with the interpreter named, plus both acceptance criteria demonstrated:
`promptcadence serve` on a clean machine with **zero configuration**, health degraded rather than
dead. Say in the handoff what you ran and what a person would see.

## Before you finish — three closing duties

1. **Write `docs/history/B4_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands; the acceptance-criteria demonstration (the commands, and the health payload as
   returned); the config surface as implemented against spec §12, with every startup refusal and
   its message; the `.importlinter` contracts as written; `cmp` output for the three mirrored
   documents; the commits made; and **"Before the next session"** — every change needed before C4
   (PromptCadence P2) starts. At minimum: create the GitHub remote, reserve the PyPI name
   `promptcadence`, push `main`, CI green on first push. Add anything you found: a spec §12 field
   that was underdetermined, a place the LoadCoach precedent did not transfer, a table shape P2
   will want changed.
   **Never overwrite an existing root file** — the workspace root is not a git repository and has
   no history to recover from. If `docs/history/B4_HANDOFF.md` exists, write `B4_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what was built, what the gate said, what is waiting on the
   human, and anything in "Before the next session".
3. **Prepare the commits.** Everything committed on `main`, tree clean, no remote configured,
   nothing tagged.

## Constraints and stop rules

* **Nothing executes.** No LoadCoach client beyond the status read for the telemetry widget, no
  queue worker, no lease, no planner, no tools, no agent loop. "Deferred: everything that executes"
  is the plan's own line. A P1 that starts executing is a P2 nobody reviewed.
* **Never weaken `.importlinter`** to make an import work — least of all the `modelrack` and
  `sweatmeter` contracts, which are the mechanical form of an architectural decision.
* **No business logic in route handlers or CLI command bodies.**
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` at the start and end of the
  session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/B4_HANDOFF.md`.
