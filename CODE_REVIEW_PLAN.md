# Local AI Suite — Code Review Plan

A reading plan for a programmer who wants to understand the whole codebase: the ten packages under
`py/` and the four applications (FreeWeight, LoadCoach, IdeaPress, PromptCadence). It is ordered
bottom-up along the dependency direction, so nothing is read before the things it imports.

Line counts are source only (`src/`, excluding `__init__.py` and `__about__.py`), as of 2026-09-06:

| Layer | Component | Source lines | Tests (lines) | Sessions |
|---|---|---:|---:|---:|
| 1 | BaseAiCore | 3,600 | 4,100 | 2 |
| 2 | SetSpec | 5,200 | 4,600 | 2 |
| 3 | ModelRack | 14,400 | 17,900 | 5 |
| 3 | SweatMeter | 3,900 | 3,900 | 2 |
| 3 | WeightsDB | 2,100 | 2,400 | 1 |
| 3 | MirrorWall | 1,800 | 2,700 | 1 |
| 3 | LoadLedger | 2,800 | 4,200 | 1 |
| 3 | CutCtx | 2,800 | 4,600 | 1 |
| 3 | ToolYard | 5,600 | 7,500 | 2 |
| 3 | Commissioner | 1,200 | 1,900 | 1 |
| app | FreeWeight | 61,200 | 32,800 | 20 |
| app | LoadCoach | 32,500 | 24,700 | 11 |
| app | IdeaPress | 20,900 | 17,400 | 7 |
| app | PromptCadence | 29,800 | 20,700 | 10 |
| | **Total** | **188,000** | **149,000** | **66** |

A session is roughly 2,500–3,000 source lines plus the tests that exercise them: about three
hours. Sixty-six sessions is the honest figure for reading everything. A **fast track** that skims
the marked files (fake providers, wire codecs, migrations, CLI bodies) is about forty sessions and
is noted per component.

---

## 0. Ground rules

### Set up every repo before reading any

Each component is its own git repository with its own virtualenv. Do this once for all fourteen:

```bash
cd <component>
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff format --check . && ruff check . && mypy src tests && lint-imports
pytest -m "not live and not performance"
```

A green gate before you start means every surprise you find later is in the code, not in your
environment. Note the interpreter version you ran under; local venvs here are a mix of 3.13 and
3.14.

### Read the docs for a component before its code

For every component, in this order:

1. `docs/architecture/master-architecture.md` — once, before session 1, in full. It is 42 KB
   and it is the design.
2. `docs/architecture/dependency-and-boundary-rules.md` — once. It explains every
   `.importlinter` file you will meet.
3. The component's `spec.md` under `docs/packages/<name>/` or `docs/apps/<name>/`.
4. The component's `development-plan.md` — read the *phase list* only. Each phase names what was
   built and what test proves it, which tells you why a module exists.
5. The ADRs the spec cites. The fifteen that shape the most code are listed in section 5.

The workspace `docs/` is the source of truth; each repo's `docs/` is a byte-identical mirror.
Read whichever is nearer.

### How this codebase asks to be read

The suite is written docstring-first: behaviour was written into the docstring before the code.
So **read the docstring as the specification and the body as its proof.** A public function's
docstring says what it refuses; check the body refuses it, and check a test exercises the refusal.

Every file gets the same five questions:

1. What does this module own, and what does its docstring say it refuses to do?
2. Which layer is it in, and does it import only downward? (`web → cli → services → domain`
   inside an application; `apps → packages → SetSpec → BaseAiCore` across the suite.)
3. Where are clocks, providers, filesystem roots and HTTP clients injected? If you cannot find the
   injection point, the module is not testable deterministically and that is a finding.
4. Where is a number without a unit in its name? (`duration_ms`, `vram_used_bytes`, `power_w` are
   correct; `timeout` alone is a defect.)
5. Which test file proves this module? Open it beside the source. If a branch has no test, note
   it.

Conventions you will see everywhere and should stop noticing by session 5: `from __future__
import annotations` at the top; keyword-only optional and boolean parameters; value objects as
`@dataclass(frozen=True, slots=True)`; pydantic for wire models only; SQLAlchemy models never
leaving the repository layer; `UNSUPPORTED` as a sentinel that raises on arithmetic.

### Keep a review log

One markdown file, one heading per session, three lists under each: *what I now understand*,
*findings* (with `path:line`), *questions for the docs*. A question the docs cannot answer is a
documentation defect, and the suite's rule is that it gets an ADR, not a workaround.

### Do not

* Do not read `.old_projects/`. It is superseded and the inventory records what was taken from it.
* Do not read the five planned-but-empty components' specs as if they had code. As of this date
  all ten packages have code; check `docs/roadmap/outstanding-work.md` if unsure.
* Do not run `git push`, and do not commit while a session is in progress on another tree.

---

## Part A — Packages, bottom-up (19 sessions)

### A1–A2. BaseAiCore — the vocabulary (3,600 lines)

Everything else imports this. It is stdlib-only by rule. Read it completely; nothing here is
skimmable because every name recurs in all thirteen other components.

Session A1 — identity and measurement:

| File | Lines | Watch for |
|---|---:|---|
| `identity.py` | 237 | `provider/name@sha256:digest`, minimal and immutable (ADR-0008) |
| `descriptor.py` | 129 | Why descriptor is separate from identity (ADR-0024) |
| `runtime.py` | 111 | The runtime profile hash: what goes in, what is excluded |
| `adapter.py` | 243 | Adapter identity and the subject it forms with a base model |
| `subject.py` | 325 | The *subject* — the thing evidence is keyed by. Central from H2 onward |
| `measurement.py` | 177 | `UNSUPPORTED`: read every operator it refuses (ADR-0016) |
| `capability.py` | 120 | Capability IDs: the shared vocabulary FreeWeight measures and LoadCoach routes on |
| `classification.py` | 110 | Data classification levels used by egress |

Session A2 — machine, money, plumbing:

| File | Lines | Watch for |
|---|---:|---|
| `machine.py` | 392 | Fingerprint construction; what changes it and what does not |
| `cost.py` | 585 | Cost *types* and `TokenUsage`; cost re-derived, never stored (ADR-0030) |
| `money.py` | 262 | Integer nanos; refuses floats |
| `hashing.py` | 219 | Canonical JSON hashing — used for pricing hashes, prompt hashes, dataset hashes |
| `ids.py` | 256 | ULIDs; where time enters |
| `timeutil.py` | 153 | The injectable clock |
| `errors.py` | 140 | The error hierarchy every package extends |

Run: `py/BaseAiCore/.venv/bin/python demo_baseaicore.py` from the workspace root.
Tests: `tests/unit/` in full — they are short and read as examples.

### A3–A4. SetSpec — the contracts (5,200 lines)

Every payload that crosses an application boundary is a versioned SetSpec model. Read the base
mechanics first, then the payload families.

Session A3 — mechanics: `base.py` (256), `envelope.py` (477), `serialization.py` (330),
`vocabulary.py` (205), `provenance.py` (59), `metrics.py` (184), `errors.py` (68),
`artifacts.py` (364). Questions: how a `MAJOR.MINOR` version is checked on read; what
`DRAFT_SCHEMAS` does at runtime; what the envelope carries that the payload does not.

Session A4 — payloads: `model/v1.py` (389), `machine/v1.py` (131), `capability/v1.py` (503),
`benchmark/v1.py` (595), `goal/v1.py` (390), `governance/v1.py` (139), and `prompts.py` (940).
`prompts.py` implements ADR-0012 (prompts as versioned JSON records); every application's
`prompts/manifest.json` is validated by it. Read `tests/contract/` — the frozen-payload tests are
the actual contract.

Run: `demo_setspec.py`.

### A5–A9. ModelRack — providers (14,400 lines)

The largest package. Read the abstraction, then one real provider in depth, then the others by
difference.

Session A5 — the abstraction: `types.py` (673), `provider.py` (531), `streaming.py` (264),
`events.py` (299), `errors.py` (308), `cache.py` (309), `residency.py` (215), `adapters.py`
(252), `testing.py` (57). Questions: what a `GenerationRequest` carries, and where the adapter
pin travels (the H6 memory note records FreeWeight once failed to send it); how residency is
represented; which errors are retryable and who decides.

Session A6 — the fake provider: `providers/fake.py` (1,222), `_fake_generation.py` (423),
`_fake_script.py` (782), `_fake_errors.py` (173). *Fast track: skim.* Every application's
test suite runs against this; knowing what it can script tells you what the application tests
actually prove.

Session A7 — Ollama: `providers/_http.py` (341), `providers/ollama.py` (1,460),
`_ollama_wire.py` (516). Read fully; it is the default provider. Trace one generate call from
request to `TokenUsage`, including how streaming tokens become events.

Session A8 — llama.cpp: `providers/llamacpp.py` (2,478), `_llamacpp_process.py` (980),
`_llamacpp_wire.py` (992), `_gguf.py` (420). The process manager is the interesting part: how a
server is spawned, health-checked, given adapters, and torn down; ADR-0071's JSON digest file.
*Fast track: read `llamacpp.py` and `_llamacpp_process.py`, skim the wire module.*

Session A9 — OpenAI-compatible and the tests: `openai_compatible.py` (1,258), `_openai_wire.py`
(254), then `tests/contract/` (the provider contract every provider must pass) and one file from
`tests/live/` to see what a live test asserts that a contract test cannot.

Run: `demo_modelrack.py`.

### A10–A11. SweatMeter — telemetry (3,900 lines)

Session A10: `types.py` (155), `safe.py` (66), `readers/protocols.py` (66), `platform.py`
(240), `sampler.py` (256), `window.py` (392), `collector.py` (530). Question: how an unreadable
sensor becomes `UNSUPPORTED` rather than zero at every layer.

Session A11: `readers/linux.py` (526), `readers/nvml.py` (591), `readers/nvidia.py` (582);
`darwin.py` and `windows.py` are stubs (57 each) — read them to see what "unsupported platform"
looks like. `testing.py` (279) is the fake reader the applications use.

Run: `demo_sweatmeter.py`.

### A12. WeightsDB and MirrorWall (3,900 lines, one session)

WeightsDB: `engine.py` (235), `session.py` (115), `migrations.py` (328), `health.py` (318),
`backup.py` (610), `types.py` (187), `redaction.py` (26), `testing.py` (131). Questions: which
SQLite pragmas are set and why; how the migration runner handles SQLite foreign keys (the H2
memory note: migrations run with FKs off); what backup guarantees.

MirrorWall: `middleware.py` (305), `responses.py` (197), `sse.py` (474), `static.py` (193),
`templating.py` (100), `filters.py` (289), `health.py` (125). Questions: the request-id and
error-envelope contract every app's web layer inherits; why SSE and never WebSockets (ADR-0004).
Read `tests/test_no_application_vocabulary.py` — it enforces that this package knows no
application's words.

### A13. LoadLedger — budgets (2,800 lines)

`types.py` (521), `core.py` (797), `memory.py` (303), `sql.py` (1,054), `errors.py` (86).
Two implementations of one protocol: read `memory.py` first as the readable version, then `sql.py`
as the durable one and diff their behaviour. Questions: reserve versus debit versus release;
floor and strict modes (ADR-0069); absent cost class is zero (ADR-0070); window semantics;
how a ledger is mounted inside an application's own database.

### A14. CutCtx — compaction (2,800 lines)

`types.py` (734), `_invariants.py` (529), `estimator.py` (78), `executor.py` (238),
`policies/drop_oldest.py` (98), `masking.py` (242), `summarizing.py` (302), `chain.py` (401).
The package is pure: policies *plan*, applications *execute*. Read `_invariants.py` before the
policies — it states what a plan may never do. Then read `tests/property/` — this is one of two
packages with property-based tests, and the strategies file tells you the input space.

### A15–A16. ToolYard — sandboxed execution (5,600 lines)

Session A15: `types.py` (799), `validation.py` (389), `registry.py` (165), `store.py` (68),
`_safe.py` (236), `errors.py` (122), `containment.py` (464). The isolation ladder is in
`containment.py`: container, bwrap, unavailable — and unavailable *refuses*.

Session A16: `sandbox.py` (1,114), `executor.py` (710), `tools/files.py` (548),
`tools/command.py` (230), `tools/fetch.py` (563). The bwrap invocation and the prlimit-inside-bwrap
detail are the security-critical lines; read `tests/integration/` and `tests/property/` beside
them. Check what `fetch.py` refuses (private ranges, redirects, size).

### A17. Commissioner — egress policy (1,200 lines)

`types.py` (295), `policy.py` (119), `ledger.py` (155), `sql.py` (486), `errors.py` (64).
Small and complete: a classification, a destination, a policy, a decision, a durable ledger row.
Compare its SQL mounting with LoadLedger's; they follow the same pattern.

**Part A checkpoint.** You can name, for each package, the one type an application imports most,
and you can explain why no package imports another package on the same layer.

---

## Part B — Applications (48 sessions)

Every application has the same skeleton. Read each in this order, and the order stops being
work after the first application:

```text
config.py                 the settings model; every FOO_* env var, every default
bootstrap.py              composition root: what is constructed, what is injected
domain/                   pure logic, no frameworks — the part worth reading slowly
infrastructure/db/        SQLAlchemy models, then migrations in numeric order, then repositories
infrastructure/*          provider factories, HTTP clients to sibling apps
services/                 one class per concern; route handlers and CLI call exactly one method
web/app.py, auth, csrf    then routes/, one file per page
cli/main.py               then commands/, one file per group
prompts/manifest.json     the versioned prompt records the services load
web/templates/            only where a route's behaviour is unclear without it
tests/                    unit beside each module; then contract, security, e2e
```

Two things to trace explicitly in every application, because they are where the suite's rules
bite: (1) how a request reaches a model — from route to service to provider — and where the
`GenerationRequest` is built; and (2) how a row reaches a page — from repository to service to
template — and where the SQLAlchemy model stops and a value object starts.

### B1–B20. FreeWeight (61,200 lines)

The largest and oldest application. Its domain layer is the most valuable reading in the suite.

**B1 — Frame.** `config.py` (1,375), `bootstrap.py` (114), `observability/logging.py` (144),
`infrastructure/providers/factory.py` (175), `services/machine.py` (116), `services/health.py`
(432). Then `web/app.py` (255), `web/middleware.py`, `web/csrf.py`, `web/errors.py`,
`web/rendering.py` — the shell every page hangs on.

**B2 — Domain: measurement.** `domain/benchmark.py` (415), `domain/metrics.py` (500),
`domain/scoring.py` (129), `domain/statistics.py` (566), `domain/confidence.py` (629),
`domain/aggregation.py` (504). Confidence is ADR-0017; read the ADR first.

**B3 — Domain: comparison and provenance.** `domain/comparison.py` (455),
`domain/provenance.py` (391), `domain/run_state.py` (262), `domain/subjects.py` (236),
`domain/capability_mapping.py` (364). Question: which provenance fields invalidate a comparison.

**B4 — Domain: judging.** `domain/judging.py` (662), `domain/jury.py` (210),
`domain/panels.py` (315), `domain/agreement.py` (481), `domain/calibration.py` (392). This is
where "a model is never a test oracle" is made operational: judges are calibrated against human
grading and excluded on disagreement.

**B5 — Domain: goals.** `domain/goals/pack.py` (650), `criteria.py` (362), `composite.py` (162),
`lint.py` (490), `hashing.py` (113). ADR-0031 is the design.

**B6 — Domain: scorers.** `domain/scorers/exact.py` (191), `schema.py` (421), `tools.py` (571),
`rule.py` (460), `judge.py` (418), `judged.py` (340), `audit.py` (404), `critique.py` (295),
`agent.py` (174). Then all ten `scorers/rules/*.py` (~1,800 lines together) — each is one
deterministic check; read them quickly and note which ones a goal can compose.

**B7 — Benchmarks: loading and interaction.** `benchmarks/loading.py` (260),
`benchmarks/interaction.py` (370), `benchmarks/fixtures/tools.py` (700),
`benchmarks/corpora/__init__.py` (73). How a suite is discovered, versioned and hashed.

**B8 — Benchmarks: the native suites, part 1.** `performance/` (502), `energy/` (460 + 345),
`memory_kv/` (599 + 438), `reliability/` (425 + 237), `token_economy/` (341).

**B9 — Benchmarks: part 2.** `echo/` (227), `structured_output/` (100), `tool_use/` (123),
`tool_recovery/` (85), `instruction_following/` (108), `long_context/` (335 + 181 + 88),
`judge/` (262 + 237), `audit/` (171), `critique/` (135), `agent/` (84), `goal/runner.py` (639).

**B10 — Database.** `infrastructure/db/models.py` (291), `models_runs.py` (611),
`models_goals.py` (393), `models_evidence.py` (156), then migrations `0001`–`0008` in order
(*fast track: read `0001` and the latest, skim the rest*). Then repositories: `runs.py` (921),
`models.py` (375), `calibration.py` (237), `goals.py` (222), `evidence.py` (152), and the four
small ones.

**B11–B12 — The run engine.** `services/runs.py` (4,358) across two sessions, with
`services/scheduler.py` (326), `services/events.py` (354), `services/telemetry.py` (209) and
`services/telemetry_recording.py` (641). This is the heart: a run's state machine, its leases,
cancellation, telemetry windows, and where the `GenerationRequest` is built. Read
`tests/unit/` for runs and `tests/e2e/` beside it.

**B13 — Results, comparison, export.** `services/results.py` (1,355), `services/comparison.py`
(824), `services/export.py` (1,404).

**B14 — Evidence.** `services/evidence.py` (2,288). One record per subject, runtime profile,
machine and capability; the export bundle LoadCoach reads. Read `docs/packages/setspec/schemas.md`
beside it.

**B15 — Goals and calibration services.** `services/goals.py` (1,086), `services/calibration.py`
(1,621), `services/jury.py` (599), `services/wizard.py` (1,178).

**B16 — Models, adapters, settings, admin.** `services/models.py` (621), `services/adapters.py`
(452), `infrastructure/adapters/directory.py` (365), `services/inventory.py` (165),
`services/settings.py` (480), `services/database.py` (430), `services/database_admin.py` (814),
`services/prompts.py` (72).

**B17 — External adapters.** `external/framework.py` (262), `environment.py` (256),
`sandbox.py` (395), `invocation.py` (199), `datasets.py` (319), `manifest.py` (93),
`services/external.py` (132), then the eleven files under `external/adapters/` (~1,300 lines). *Fast track:
read `framework.py`, `sandbox.py` and one adapter.*

**B18 — Web routes.** All nineteen files under `web/routes/` (~5,100 lines). Each handler should
call one service method and render; note any that do more. `runs.py` (791) and `wizard.py` (598)
are the ones to read closely.

**B19 — CLI.** `cli/main.py` (92) and the thirteen `cli/commands/*.py` (~4,400 lines). *Fast
track: read `main.py`, `runs.py` (819) and `goals.py` (970); skim the rest.*

**B20 — Tests as a whole.** `tests/contract/`, `tests/security/`, `tests/accessibility/`,
`tests/e2e/`. Read the conftest fixtures: they show how the whole application is stood up on a
fake provider and a temporary database, which is the pattern every other application copies.

### B21–B31. LoadCoach (32,500 lines)

**B21 — Frame.** `config.py` (1,198), `bootstrap.py` (166), `infrastructure/providers/factory.py`
(337), `services/health.py` (379), `services/doctor.py` (629), `web/app.py` (446),
`web/auth.py` (189), `web/rate_limit.py` (282), `web/limits.py` (149), `web/csrf.py` (55).
LoadCoach is the application designed to be exposed on a LAN, so its web shell is the most
hardened; read `docs/security.md` first.

**B22 — Domain: registry and profiles.** `domain/registry.py` (198), `domain/task_profile.py`
(231), `domain/validation.py` (399), `domain/authorization.py` (105), `domain/priority.py`
(158). Then `services/task_profiles.py` (174) and the shipped `config/task_profiles.toml`.

**B23 — Domain: routing.** `domain/routing/subject.py` (453), `constraints.py` (834),
`scoring.py` (613), `context_budget.py` (188), `ranking.py` (118), `explanation.py` (310),
`narrative.py` (360). Read `docs/routing.md` first, then trace one decision through all seven
files. Determinism: find where every source of nondeterminism is pinned.

**B24 — Domain: evidence, reliability, breaker.** `domain/evidence_policy.py` (957),
`domain/reliability.py` (812), `domain/circuit_breaker.py` (357), `domain/retry_policy.py`
(192). Freshness and confidence weighting; the bounded reliability statistics; the re-probe.

**B25 — Domain: queue.** `domain/admission.py` (230), `domain/queue_state.py` (214). Then
`docs/apps/loadcoach/queue-and-scheduling.md` — the starvation bound is proved there and the
test in `tests/simulation/` checks it.

**B26 — Database.** `infrastructure/db/models.py` (852), migrations `0001`–`0014` in order
(*fast track: `0001`, `0009`, `0011`, `0014`*). LoadCoach has the most migrations; they record
how subjects and adapters entered the schema (LA2).

**B27 — Services: routing and evidence.** `services/routing.py` (1,115),
`services/evidence.py` (1,694), `infrastructure/freeweight_client.py` (470). The import path from
FreeWeight: allow-listed hosts (ADR-0026), bundle validation through SetSpec, and nothing else.

**B28 — Services: execution.** `services/execution.py` (2,112), `services/models.py` (625),
`services/residency.py` (404), `services/adapters.py` (369), `infrastructure/adapters/directory.py`
(446). Where the `GenerationRequest` is built; where tool definitions ride on the wire (G2); where
validation and corrective retry happen; the finish-reason contract PromptCadence depends on.

**B29 — Services: queue and worker.** `services/queue.py` (1,598), `services/worker.py` (2,020),
`services/recovery.py` (165), `services/job_events.py` (287), `services/queue_stream.py` (151).
Leases, ageing, cancellation within a chunk, recovery after a kill. Read `tests/simulation/` and
`tests/e2e/` for the recovery proof.

**B30 — Services: the rest.** `services/reliability.py` (567), `services/feedback.py` (245),
`services/tokens.py` (164), `services/settings.py` (271), `services/retention.py` (130),
`services/dashboard.py` (191), `services/status.py` (125), `services/telemetry_stream.py` (170),
`services/database.py` (359), `services/config_reference.py` (164), `services/machine.py`,
`services/prompts.py`.

**B31 — Web, CLI, tests.** Twelve `web/routes/*.py` (~2,500 lines; `generate.py` (558) and
`jobs.py` (412) closely), `web/routing_support.py` (87), the thirteen `cli/commands/*.py`
(~2,900 lines; *fast track: `job.py`, `route.py`, `evidence.py`*). Then `tests/security/` in full —
it walks the Security Standards item by item — and `tests/performance/` to see the spec §15
budgets as assertions.

### B32–B38. IdeaPress (20,900 lines)

**B32 — Frame and the workflow model.** `config.py` (927), `config_reference.py` (179),
`bootstrap.py` (58), `errors.py` (222), `content_types/registry.py` (137), `domain/stages.py`
(189), `domain/stage_state.py` (123), `domain/plan.py` (150), `domain/project.py` (132). Read
`docs/workflows.md` (the sixteen stages) and `docs/content-types.md` first.

**B33 — Domain: requirements and inference.** `domain/requirements.py` (458),
`domain/context_assembly.py` (348), `domain/inference.py` (400), `domain/revision_policy.py`
(149), `domain/critique.py` (62), `domain/audit.py` (170), `domain/commit.py` (250). Where the
"Python decides, models perform" rule lives: what a model output must satisfy before the loop
advances.

**B34 — Domain: validators and exporters.** `domain/validation.py` (158), the seven
`domain/validators/*.py` (~700 lines), `domain/exporters/model.py` (262), `markdown.py` (130),
`html.py` (189), `json.py` (122).

**B35 — Backends.** `infrastructure/backends/_modelrack.py` (402), `ollama.py` (207),
`openai_compatible.py` (175), `fake.py` (248), and `loadcoach.py` (1,422) — the HTTP client to
LoadCoach, SetSpec payloads only. Compare it with PromptCadence's LoadCoach client later (B42);
they solve the same problem and the differences are instructive. `services/backends.py` (182).

**B36 — Database and services: projects and plans.** `infrastructure/db/models.py` (502),
migrations `0001`–`0006`, `repositories/projects.py` (162); `services/projects.py` (332),
`services/project_archive.py` (554), `services/requirements.py` (452), `services/plan.py` (406),
`services/plan_editing.py` (473), `services/workspace.py` (233).

**B37 — Services: the loops.** `services/stages.py` (496), `services/unit_loop.py` (554),
`services/review_loop.py` (539), `services/review.py` (512), `services/inference.py` (442),
`services/units.py` (385), `services/stage_bodies.py` (194), `services/feedback.py` (196),
`services/diff.py` (276), `services/export.py` (415), plus the small report and registry
modules. The bounded loops are the thing to trace: iteration cap, exit conditions, what a pause
records (the M7 memory note: an empty critique generation once wedged a run; find the fix).

**B38 — Web, CLI, tests.** Nine `web/routes/*.py` (~1,200 lines), eleven `cli/commands/*.py`
(~1,500 lines), then `tests/e2e/` — the exit demo that drafts a full article on the fake backend.

### B39–B48. PromptCadence (29,800 lines)

**B39 — Frame and tiers.** `config.py` (968), `bootstrap.py` (126), `domain/tiers.py` (497),
`services/tiers.py` (251), `services/pricing.py` (368), `services/runtime.py` (218),
`services/diagnostics.py` (101), `web/app.py` (286), `web/auth.py`, `web/rate_limit.py`,
`web/limits.py`. Read `docs/tiers.md` and ADR-0072 (pricing file) first.

**B40 — Domain: the trajectory.** `domain/trajectory.py` (1,073), `domain/turns.py` (211),
`domain/threads.py` (277), `domain/events.py` (83), `domain/errors.py` (232),
`domain/deviation.py` (648). Read `docs/apps/promptcadence/lifecycle.md` beside these; the state
machine and every deviation category are specified there and must match the code.

**B41 — Domain: plan, intent, policy.** `domain/plan.py` (855), `domain/intent.py` (803),
`domain/policy.py` (1,028), `domain/dispatch.py` (184), `domain/tools.py` (166),
`domain/explanation.py` (137), `domain/compaction.py` (117). The `ExecutionIntent` every turn
runs under is the object to understand fully: it is what makes a turn reconstructable.

**B42 — The LoadCoach client.** `infrastructure/loadcoach.py` (1,291),
`services/loadcoach_surface.py` (206), `services/loadcoach_status.py` (76). ADR-0045: models are
reached only here. Check the finish-reason handling — an undeclared finish is never success — and
what happens when `is_remote` is absent (ADR-0098).

**B43 — Database.** `infrastructure/db/models.py` (774), migrations `0001`–`0011` in order,
`infrastructure/threads.py` (313), `infrastructure/tool_calls.py` (190), `services/records.py`
(161), `services/database.py` (271). This application mounts LoadLedger's and Commissioner's
tables inside its own database; find the mount.

**B44–B45 — The loop.** `services/loop.py` (4,218) across two sessions, with `services/worker.py`
(401), `services/events.py` (289), `services/estimates.py` (179). Trace one trajectory:
submitted, planned, approved, each step dispatched under an intent, tools executed, ledger
debited, egress decided, compaction applied, terminal state reached. Keep the lifecycle document
open.

**B46 — Governance services.** `services/planner.py` (455), `services/approvals.py` (1,199),
`services/policy_assembly.py` (178), `services/governance.py` (109), `services/egress.py` (373),
`services/budget.py` (979), `services/intents.py` (568). The three approval modes; the three
ceilings; the egress decision per turn.

**B47 — Tools, compaction, explanation.** `services/tools.py` (874), `services/compaction.py`
(349), `services/explanation.py` (681), `services/views.py` (241), `services/console.py` (297),
`services/trajectories.py` (513), `services/retention.py` (192), `services/tokens.py` (204).
Compaction is a *view*; the full record is never modified (ADR-0090 and ADR-0091 govern the
summary turn). The explanation is
composed, then materialized; find both.

**B48 — Web, CLI, tests.** Six `web/routes/*.py` (~1,100 lines), ten `cli/commands/*.py`
(~2,200 lines; `trajectories.py` (536) closely), then `tests/security/` (the checklist and the
prompt-injection corpus are release gates), `tests/golden/`, and `tests/e2e/`.

**Part B checkpoint.** For each application you can draw the request path to a model and the
row path to a page; you can name every place it talks to a sibling application and confirm it is
HTTP with a SetSpec payload; and your review log has at least one finding per application that
the docs did not already know about.

---

## 5. ADRs to read before the code they shaped

There are one hundred ADRs in `docs/adr/`. These fifteen change how you read the code:

| ADR | Decision | Read before |
|---|---|---|
| 0003 | Async at the HTTP edge only | any `web/` |
| 0004 | SSE, never WebSockets | MirrorWall `sse.py` |
| 0008, 0024 | Model identity is minimal; descriptor and runtime profile are separate | BaseAiCore A1 |
| 0010, 0029 | Database-backed queue with leases, no broker | LoadCoach B25, B29 |
| 0012 | Prompts are versioned JSON records | SetSpec `prompts.py` |
| 0016 | `Unsupported` is not zero | BaseAiCore `measurement.py` |
| 0017 | Confidence on evidence | FreeWeight B2 |
| 0018 | The isolation ladder ends in refusal | ToolYard A15 |
| 0026 | Evidence import through an allow-list | LoadCoach B27 |
| 0030 | Cost re-derived, never stored | BaseAiCore `cost.py`, LoadLedger |
| 0045 | PromptCadence reaches models only through LoadCoach | PromptCadence B42 |
| 0069, 0070 | Ledger floor/strict; absent class is zero | LoadLedger A13 |
| 0098 | Remote tiers refuse until registered and priced | PromptCadence B39 |

`docs/reviews/final_architecture_audit.md` explains why ADRs 0022–0030 exist; read it after
Part A.

---

## 6. Suggested calendar

* **Weeks 1–2:** Part A. Two sessions a day is sustainable for packages.
* **Weeks 3–6:** FreeWeight. One session a day; its domain layer rewards slowness.
* **Weeks 7–8:** LoadCoach.
* **Week 9:** IdeaPress.
* **Weeks 10–11:** PromptCadence.
* **Week 12:** Re-read your review log, turn confirmed findings into issues in the right
  repository, and turn unanswered questions into ADR proposals.

Fast track: weeks 1–2 unchanged, then one week per application reading only the domain and
services layers in full and everything else by the file lists above marked *skim*.
