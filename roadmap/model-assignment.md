# Model Assignment Guide

**Purpose:** which model to point at which phase, and at what reasoning effort.
**Status:** advisory. Unlike everything else in this set, nothing here is normative — it is a
starting allocation, not a rule. Adjust it from what you actually observe.

---

## 1. What actually makes a phase hard for a model

Difficulty for a human and difficulty for a model are not the same axis. Six factors decide it, and
they explain every allocation below.

| Factor | Pushes toward | Why |
|---|---|---|
| **Feedback-loop quality** | Sonnet when good, Opus when poor | A parser with fixture tests gives a tight write → run → see → fix loop, and a mid-tier model closes it as well as a frontier one. A race that appears once in fifty runs gives no loop at all; the model has to reason it out before writing a line |
| **Cross-file invariant maintenance** | Opus | "`attempt` has exactly one writer" must hold across the claim query, the executor, the recovery path and the simulator. Holding an invariant across files that are never all in view at once is where capability shows |
| **Irreversibility** | Opus | Not because it is harder, but because the cost of error is asymmetric. A golden format, a uniqueness key or a wire shape is cheap now and expensive after data exists |
| **Volume with low subtlety** | Sonnet | Fourteen validators, twenty macros, nine adapter parsers. Sonnet is not merely adequate here, it is *preferable*: cheaper per token, and the work parallelizes across sessions |
| **Adversarial reasoning** | Opus | "What would an attacker do with this path join, this archive entry, this redirect" is a different mode from "make the test pass", and it does not benefit from a feedback loop because the failing case is the one nobody wrote a test for |
| **Mathematical correctness** | **Depends — see below** | Ordinarily Opus. But this documentation set specifies hand-computed expected values for nearly every formula, which converts "derive it correctly" into "match the fixture" — a Sonnet-shaped problem |

### 1.1 The specification quality multiplier

This is the most important thing on the page.

Every phase in every plan names its files, its tests and its acceptance criteria. The final audit
closed the boundaries that were still ambiguous. That removes the factor that usually separates a
frontier model from a mid-tier one on implementation work: **deciding what to build**.

The practical consequence is that Sonnet covers substantially more of this project than it would
cover on a typical codebase — roughly two-thirds of the phases — and the Opus budget concentrates on
the dozen places where the design genuinely cannot be reduced to "follow the spec".

Where you see Opus below, it is almost always one of three things: concurrency, a contract that
outlives a release, or adversarial reasoning.

---

## 2. The allocation

**Claude column:** model plus thinking budget — `max` (ultrathink), `extended` (think hard),
`standard`.
**Codex column:** reasoning effort on the strongest available Codex model. Names move; verify against
your installed version (§4).

### 2.1 BaseAiCore — small, and the most irreversible code in the suite

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | `Unsupported`, `ModelIdentity`, ULID, canonical JSON, hashing | **Opus + extended** | high | ~400 lines, and every one of them is frozen by a golden test that three databases will depend on. Canonical float formatting, ULID monotonicity within a millisecond, and a sentinel that must refuse *every* coercion path are each easy to get 95 % right, which is the failure mode |
| P2 | Descriptor, runtime profile, comparability matrix | Sonnet + extended | medium | The matrix is specified as a table and implemented as a table. Hash stability has goldens |
| P3 | Machine profile and fingerprint | **Opus + extended** | high | Another golden that orphans a machine's entire history if it is wrong. The inclusion/exclusion policy has real judgment in it |
| P4 | Capability IDs, API freeze, publish | Sonnet + standard | medium | Small, mechanical, well-bounded |

### 2.2 SetSpec — one hard phase, then volume

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | Envelope, versioning, canonical serialization, strict/preserving model pair | **Opus + max** | xhigh | Pydantic `extra="allow"` round-trip fidelity is genuinely subtle, and this phase decides it for every payload that follows. Byte-identical output across the CI matrix is the kind of property that fails on one Python version only |
| P2 | Benchmark, capability, machine, model payloads | Sonnet + standard | medium | Volume. The field sets are now normative tables (ADR-0022); this is transcription with validation |
| P3 | Event and error envelopes | Sonnet + standard | medium | Small, and the shapes are fixed by ADR-0025 |
| P4 | Freeze, JSON Schema generation, goldens | Sonnet + extended | medium | Mechanical, but the goldens are contracts — worth extended thinking on what a "fully populated" and an "`unsupported`-heavy" example should contain |
| **P3A** | **Capability vocabulary 1.1, `goal_pack` + `calibration_report` payloads** | **Opus + max** | xhigh | Added by ADR-0031/0032, ships inside 0.3.0 alongside P4. Five interlocking coherence rules across two payload types — `uncalibrated` refused outright, a validity discount refused without the calibration it came from, a verdict refused if it contradicts its own `kappa_w` against the threshold — each closing a way a subjective score could acquire authority it has not earned. The reserved-root refusal must also survive the forward-compatibility exception correctly, which is a one-line rule with a large blast radius if inverted |
| P5 | `setspec.prompts` extraction | Sonnet + extended | high | A move-and-generalize with one hard constraint: FreeWeight's existing pack must hash identically. That constraint is testable, which makes it Sonnet-shaped |

### 2.3 ModelRack — the fake matters more than the real one

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | Types and the `Provider` protocol | Sonnet + extended | high | Small, but it is the shape three applications code against. Worth an Opus review pass even if Sonnet writes it |
| P2 | `FakeProvider` | **Opus + extended** | high | Every default test suite in the suite runs against this. A fake that is more forgiving than Ollama hides real bugs in three applications for months. The judgment is *which nasty cases to script* — and that is exactly what a model with weaker adversarial instincts under-does |
| P3 | Ollama adapter | Sonnet + extended | high | Fixture-driven, tight loop. Two parts deserve care: unicode split across NDJSON chunk boundaries, and keeping backend/client timings separate |
| P4 | OpenAI-compatible adapter | Sonnet + standard | medium | Pattern-following after P3. The honest-capability-declaration discipline is spec'd |
| P5 | Residency, cancellation hardening, cache | **Opus + extended** | high | "Cancel mid-stream, close the connection, leak no socket, preserve partial text" is four properties that interact, verified by a connection-count assertion that will be flaky if the design is wrong rather than the test |

### 2.4 SweatMeter — the most Sonnet-friendly package in the suite

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | `/proc` and `/sys` parsers | Sonnet + standard | medium | Textbook fixture-driven parsing. Every failure mode is a captured file. Delta computation on first call is the only trap and the plan names it |
| P2 | `nvidia-smi` reader | Sonnet + standard | medium | Same shape. Name-based CSV parsing, `[N/A]` handling — all fixture-testable |
| P3 | Collector, machine profile, sampler | Sonnet + extended | high | Thread lifecycle, clean shutdown, no leak across 100 start/stop cycles. Moderate concurrency, but bounded and stress-tested |
| P4 | Derived metrics, energy integration | Sonnet + extended | medium | Integration over irregular timestamps is real maths — but the plan supplies a hand-computed expected value, which converts it |

### 2.5 WeightsDB — failure paths are the whole job

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | Engine, session, types, redaction | Sonnet + extended | high | Two traps, both named: pragmas lost after a pool reconnect, and rollback on `KeyboardInterrupt` |
| P2 | Migration runner, backup, restore | **Opus + extended** | high | The value of this package is entirely in what happens when a migration fails at 40 %. Restore-before-swap, byte-identical originals, disk-full mid-backup, and now a dialect-asymmetric guarantee to implement honestly rather than paper over |
| P3 | Health, publication, adoption checklist | Sonnet + standard | medium | Reporting and packaging |

### 2.6 MirrorWall — one genuinely hard phase inside a lot of surface

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | Tokens, layout, component macros | Sonnet + standard | medium | High volume, low subtlety. Accessibility and contrast are checkable properties. Consider Opus for the *first* three macros to set the pattern, then Sonnet for the remaining twenty |
| P2 | Envelopes, request IDs, **SSE**, static | **Opus + max** | xhigh | Its own plan calls the replay/live handoff "the subtlest code in the package", and the audit added a threadpool-dispatch requirement on top. Gap-free replay with no duplicate across the handoff, under injected races, with bounded queues — this is the second-hardest thing in the suite |
| P3 | JS modules, accessibility, publication | Sonnet + standard | medium | Vanilla ES modules against a DOM harness. Bounded by a size budget |

### 2.7 FreeWeight — eighteen phases, six of them hard

Adds P8A, P8B and P10A (ADR-0031, ADR-0032, user-defined goal benchmarks). FreeWeight's own
development plan carries a step-level breakdown of these three phases and the runtime-juror
selection question, which is a different question from the one this page answers — see its
[Appendix A](../apps/freeweight/development-plan.md#appendix-a--model-assignment).

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | Skeleton, config, CLI, logging | Sonnet + standard | medium | Boilerplate with a precise spec |
| P2 | Storage, migrations, repositories | Sonnet + extended | high | Both dialects from the start; the `name_only` upgrade-in-place rule needs care |
| P3 | Model discovery | Sonnet + standard | medium | Straightforward once ModelRack exists |
| P4 | Telemetry, machine profile, SSE bar | Sonnet + extended | high | Sampler lifecycle under reload is the trap |
| **P5** | **Run engine, state machine, scheduler, event store, recovery** | **Opus + max** | xhigh | The plan says it: "the two subtlest components in the application". A scheduler thread, a state machine, gap-free event sequences, replay/live handoff, and kill-at-five-points recovery — with no useful feedback loop for any of it |
| **P6** | **First real measurements, provenance, fingerprint, prompt library** | **Opus + extended** | high | Timing semantics (`perf_counter_ns` vs wall clock, backend vs client, cold vs warm) are exactly the confusions that produce plausible wrong numbers. Plus fingerprint assembly, which is irreversible |
| P7 | Deterministic quality suites, scorers, mock tools | Sonnet + extended | medium | Volume work with clear pass/fail definitions — **except** the mock-tool containment tests (`../`, absolute paths, symlinks), which want **Opus + extended** for an hour |
| **P8** | **Judged suites: audit, critique, judge, long context** | **Opus + extended** | high | Judge-bias measurement, transitivity violations, self-preference deltas, correction uplift and regression rate. Subtle statistics *and* subtle experiment design — the "flag everything" adversarial test case is the kind of thing you want the model to think of unprompted |
| P8A | Goal packs, rule/reference criteria, `goal_hash` | Sonnet + standard | medium | Thirteen small pure rule functions and CRUD — volume, not subtlety. Opus + extended for the `goal_hash` boundary specifically (what it covers vs excludes has years of comparability riding on it) and the rubric lint |
| **P8B** | **Calibration: `kappa_w`, jury, the anchor/holdout gate** | **Opus + max** | xhigh | The intellectual core of the goal-benchmark feature and arguably the hardest phase in this table. A subtly wrong agreement statistic produces *plausible* numbers and stays wrong for months — no feedback loop catches it, only hand-computed fixtures and synthetic graders with known true agreement do |
| **P9** | **Memory/KV, energy, reliability, comparison** | **Opus + extended** | high | KV theory vs observed slope, fit quality, OOM-as-a-measurement, and comparability verdicts that must refuse to average across a boundary |
| P10 | Dashboard, results, exports, data management | Sonnet + extended | medium | Large surface, low subtlety. The anti-lie test (every figure recomputed from raw samples) is what protects it |
| P10A | Goal wizard, starter packs | Split | — | **Opus + extended** for the wizard flow (Step 2's two questions, the calibration report copy) — the teaching *is* the product, and generic copy wastes the whole feature. Sonnet + standard for templates, forms and the grading UI once the flow is decided |
| **P11** | **Capability evidence and the LoadCoach contract** | **Opus + max** | xhigh | The suite's most load-bearing contract, frozen at this phase, now including the six-factor confidence formula and the goal-evidence gate's "no row at all" rule — which a careful implementer gets wrong precisely *by* being careful and emitting at the floor |
| P12 | Adopt WeightsDB, MirrorWall, `setspec.prompts` | Sonnet + standard | medium | Mostly deletion. The acceptance criterion — the existing test suite passes unchanged — is a perfect guardrail for a cheaper model |
| P13 | External adapters and sandboxing | Split | — | **Opus + extended** for the sandbox tiering and the refusal path (security, and the failure is silent host execution). Sonnet + standard for the nine adapter output parsers, which are fixture work |
| P14 | Hardening and 1.0 | Split | — | **Opus + extended** for the security pass. Sonnet + extended for performance, docs and upgrade testing |

### 2.8 LoadCoach — the highest concentration of hard phases

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | Skeleton, storage, WeightsDB extraction | Sonnet + extended | high | The extraction is a move-and-generalize; the risk is carrying FreeWeight-shaped assumptions across, which a careful reader catches |
| P2 | Registry and task profiles | Sonnet + standard | medium | Configuration validation |
| **P3** | **Routing, scoring, constraints, explanation** | **Opus + max** | xhigh | Pure functions, but: a total ordering that must be deterministic, absent-evidence excluded from numerator *and* denominator, runtime-profile matching, served-context resolution, and an explanation that has to be truthful about all of it. Judgment-dense, and frozen into a persisted format |
| **P4** | **Execution, streaming, validation, MirrorWall extraction** | **Opus + extended** | high | Streaming with cancellation inside one chunk, corrective retries that preserve the original attempt record, and provider/overhead timings kept separate |
| **P5** | **Queue, scheduling, recovery, simulator** | **Opus + max** | xhigh | The hardest single phase in the suite. Atomic claiming under concurrent workers, lease keeper, ageing sweep, admission deferral, circuit breaker, cancellation from every state, kill-9 recovery from five points — plus building the simulator that proves it. No feedback loop for any of the interesting failures |
| **P6** | **Evidence import and evidence-driven routing** | **Opus + extended** | high | Cross-application contract correctness, the `match_state` binding rules in both directions, and version rejection that must not partially parse |
| P7 | Feedback, reliability, regression detection | Sonnet + extended | high | Statistics with stated bounds and minimum sample counts. Worth Opus if you see oscillation |
| P8 | UI completion | Sonnet + standard | medium | Volume. The one-minute-explainability criterion is a design judgment better made by a human looking at the page |
| P9 | Hardening, auth, LAN exposure | **Opus + extended** | high | The application most likely to be exposed. Scope enforcement in the service layer *and* the route, rate limits, `Host` validation, the fetch allowlist |

### 2.9 IdeaPress — mostly Sonnet, with three exceptions

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| P1 | Skeleton, storage, projects | Sonnet + standard | medium | Boilerplate on packages that already exist |
| P2 | Inference port, Ollama backend | Sonnet + extended | high | The port shape matters; the rest is adapter work |
| P3 | Requirements, plan, gates | Sonnet + extended | high | One subtle property — the compiler must not fabricate requirements — and it has a test. Opus if the anti-fabrication test proves hard to satisfy honestly |
| P4 | Draft, validate, repair, commit | Sonnet + extended | medium | Fourteen validators is volume work. Two parts want care: atomic commit, and the context-reduction order that must never drop a requirement |
| P5 | Audit, critique, bounded revision | Sonnet + extended | high | Diminishing-returns detection computed from deterministic finding counts. Bounded, testable |
| P6 | Exports, project review, second backend | Sonnet + extended | medium | Byte-stable export determinism is fiddly (unsorted collections, locale, newlines) but entirely testable |
| P7 | LoadCoach backend | Sonnet + extended | high | Contract work against a schema-driven mock. Well-bounded now that the prompt-passthrough and task-map questions are settled |
| P8 | UI and editing experience | Sonnet + standard | medium | Volume |
| P9 | Hardening | **Opus + extended** | high | This is the application that renders the most model output and imports user archives. Sanitizer gaps that exist in one export format and not another, and archive extraction, are adversarial-reasoning work |

### 2.10 PromptCadence arc — the new packages and the harness

Added 2026-09-02 for the [PromptCadence roadmap](promptcadence-roadmap.md). Model names here are
the Claude 5 generation (Fable 5 > Opus 5 > Sonnet 5); the second value is the Claude Code
**effort** level, which replaced thinking budgets. The older sections' "Opus + max/extended"
rows map to "Opus 5 · xhigh/high". The specification-quality multiplier (§1.1) applies *more*
strongly here than to the original plans: the state machine is normative tables (T1–T14), the
deviation taxonomy is closed per intent field, and the budget maths has named traps — much of
this arc is deliberately Sonnet-shaped.

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| **Phase 0 / LA0** | **ADRs D-1…D-13 + A-1…A-10, doc amendments** | **Opus 5 · xhigh** | xhigh | Permanent contracts, but the decisions are already made and argued in the roadmaps — expansion, not invention. Fable would be paying 2× to transcribe settled judgment |
| BaseAiCore additive (DataClassification, adapter types) | Small, frozen vocabulary + canonical forms | **Opus 5 · high** | high | §3.3's BaseAiCore rule: wrong here is a data-compatibility break across every repo. Tiny phase, so the premium costs little |
| SetSpec Phase 6 (governance payload, evidence v1.1, adapter manifest) | Payload models + goldens | Sonnet 5 · high | medium | The SetSpec-P2 precedent: normative field tables → transcription with validation. Goldens get an Opus review pass |
| CutCtx P1 | Invariants, plan, executor, DropOldest | **Opus 5 · xhigh** | high | The `_invariants` module is the one gate every future policy routes through (first-instance rule), enforced by property tests whose *choice of properties* is the judgment |
| CutCtx P2 | Masking, summarizing, chain — 0.1.0 | Sonnet 5 · high | medium | Policies against locked invariants. The one risky spot: SummarizingPolicy's contiguous-group assembly (dict-ordering nondeterminism) — named in the plan, golden-tested |
| ToolYard P1 | Refusal machinery, registry, records | **Opus 5 · xhigh** | high | "Model input never raises" under fuzzing, and the fixed refusal order every later tool inherits. The FakeProvider lesson: the discipline layer must be stricter than its first consumer needs |
| **ToolYard P2** | **Sandbox: containment + isolation tiers** | **Fable 5 · xhigh** | xhigh | Adversarial reasoning with a silent-failure class (an escape that works is quiet); TOCTOU and prefix-collision cases don't appear in a test loop until someone thinks of them. Needs the reference machine for marked tests — a daytime phase, not overnight |
| ToolYard P3 | Built-in tools, ADR-0026 fetch vectors | Sonnet 5 · high | medium | Fixture/vector work; the vectors are byte-shared with LoadCoach's existing suite. Opus reviews the fetch handler diff |
| LoadLedger P1 | Ceilings, debits, verdicts, windows | Sonnet 5 · high | medium | §3.4 exactly: integer arithmetic with hand-specifiable expected values, and the UTC-midnight trap is named three times in the docs |
| LoadLedger P2 | `loadledger.sql`, atomicity, miniature host | **Opus 5 · high** | high | First mounting implementation (first-instance rule) plus kill-mid-debit atomicity on both dialects — money rows with the §3.3 failure shape |
| SpotCheck P1 | Policy matrix, payload round-trip | Sonnet 5 · high | medium | Enum-parametrized matrix, exhaustive by construction; fail-closed row is spec'd |
| SpotCheck P2 | Ledgers + mounting — 0.1.0 | Sonnet 5 · standard | medium | Copies LoadLedger P2's proven mounting pattern — the "rest of the repeated thing" |
| PromptCadence P1 | Skeleton, config, db, health | Sonnet 5 · high | medium | Identical in shape to LoadCoach P1; boilerplate against a precise spec |
| PromptCadence P2 | Domain: threads, tiers, plans, intents, state machine | **Opus 5 · xhigh** | xhigh | Mostly normative-table transcription — but `ExecutionIntent` is the design's load-bearing wall and this phase freezes its shape |
| **PromptCadence P3** | **LoadCoach client, bypass loop, lease/recovery, the fake LoadCoach** | **Fable 5 · xhigh** | xhigh | The LoadCoach-P5-shaped phase: kill −9 reconciliation, one-write transitions, cancellation — no feedback loop for the interesting failures — *plus* the fake every later phase trusts (the P2-FakeProvider argument, doubled) |
| PromptCadence P4 | ToolYard integration, workspaces | Sonnet 5 · high | high | ToolYard did the hard part; the hostile-model journey tests are specified. Opus reviews the workspace-lifecycle diff |
| PromptCadence P5 | Budget wiring, estimator | Split | high | **Opus 5 · high** for crash-reconciliation of debits (idempotent by `source_ref`); Sonnet 5 for ceilings/config/CLI |
| PromptCadence P6 | Egress, verification, deviations | **Opus 5 · high** | high | Fail-closed verification semantics and the violation path — adversarial-adjacent, and the deviations feed re-approval |
| **PromptCadence P7** | **Planner, approval modes, DAG dispatch, the contract-1 diff** | **Fable 5 · xhigh** | xhigh | Design-dense with a live-model interaction (plan-schema resilience against real local models) and the arc's central proof (governance invariance). A failed pass here invalidates the design claim, not just the code |
| PromptCadence P8 | Compaction, explanation, UI | Split | medium | **Opus 5 · high** for materialization/invalidation (cache-consistency reasoning); Sonnet 5 · standard for the MirrorWall UI volume |
| PromptCadence P9 | Hardening — 1.0 | Split | high | **Opus 5 · xhigh** for the security pass (consider Fable 5 for the prompt-injection corpus — pure adversarial); Sonnet 5 for performance measurement and docs |
| M13 IP-A1 (IdeaPress + LoadLedger) | Mount, debit, cost UI | Sonnet 5 · high | medium | Third mounting implementation by then; adopt-delete-prove against fixtures |
| M13 IP-A2 (IdeaPress + SpotCheck) | S4 badge on rows | Sonnet 5 · standard | medium | Reading recorded decisions into an existing badge |
| M13 IP-A3 (IdeaPress + CutCtx) | `project_review` policy chain | Sonnet 5 · high | medium | Golden-parity refactor that deletes working code — `high` is the floor for deletions |

### 2.11 Adapter arc

| Phase | Work | Claude | Codex | Why |
|---|---|---|---|---|
| **ModelRack P6** | **`LlamaCppProvider` process supervision** | **Fable 5 · xhigh** | xhigh | Spawn/health/terminate with orphan and leak guarantees — concurrency with no useful feedback loop, in a published package three applications call. The §3.3 class |
| ModelRack P7 | Adapter registration/selection, cache correctness | **Opus 5 · xhigh** | high | The prefix-under-A-never-reused-for-B property is exactly the intermittent-defect shape; the conformance test design is the judgment |
| ModelRack P8 | Hardening, publication | Split | medium | Opus 5 for cancellation-under-supervision and leak tests; Sonnet 5 for docs and publish |
| LoadCoach 1.1 | Generalized LC-E1, adapter registry, gate, two-level residency | **Opus 5 · xhigh** | xhigh | Routing semantics frozen into persisted explanations — the LoadCoach-P3 precedent, extended |
| FreeWeight 1.1 | Adapter enumeration, panels, serving-mode A/B | Sonnet 5 · high | medium | Measurement plumbing on an existing engine; panel composition is spec'd |
| IdeaPress pins | Per-stage adapter pins, provenance columns | Sonnet 5 · standard | medium | Config + override passthrough against a settled contract |

### 2.12 Overnight, single-session runs (no agentic loops)

The allocations above assume §5.3's caveat — "every Sonnet row assumes you read the diff". For
unattended overnight runs that assumption is void until morning, so two adjustments: run Sonnet
rows at effort **high** (not standard) since nobody will nudge a stuck session, and never
schedule a Fable/security row overnight — those phases are won by review, and their failures are
silent. The suite's own design is what makes overnight work at all: every default test suite
passes with no GPU, no Ollama and no network, so a session can drive itself to a green gate.
Sequencing is the other constraint: Phase 0 (the ADRs) must land before any code session starts,
per the standing rule.

These matter more than any individual row.

### 3.1 The first-instance rule

Use the stronger model for the **first** of a repeated thing, then the cheaper one for the rest:

* the first scorer, then the other five
* the first external benchmark adapter, then the other eight
* the first component macro, then the other twenty
* the first validator, then the other thirteen
* the first Alembic migration, then every subsequent one

The first one establishes the pattern, the test shape and the error handling. The rest are
transcription against a working example, which is where a mid-tier model is genuinely equal and
meaningfully cheaper.

### 3.2 Implement cheap, review expensive

For the phases marked Sonnet that touch a contract or a concurrency boundary — ModelRack P1,
WeightsDB P1, FreeWeight P2 and P4, LoadCoach P1 and P7 — the best value is Sonnet writing and Opus
reviewing the diff before the phase closes. A review pass costs a fraction of an implementation pass
and catches the class of error that a passing test suite does not.

This is also the right shape for the extraction phases (WeightsDB P1, MirrorWall P1–2,
`setspec.prompts`): the move is mechanical, but "did a FreeWeight-shaped assumption come across with
it?" is a judgment question.

### 3.3 Never economize on these five

Regardless of budget pressure:

| Phase | Because |
|---|---|
| LoadCoach P5 (queue) | The failure is a duplicated or lost job, discovered in production, unreproducible |
| MirrorWall P2 (SSE) | Three applications inherit the defect, and replay bugs are intermittent |
| FreeWeight P5 (run engine) | Same shape, plus it corrupts measurements rather than failing loudly |
| FreeWeight P11 (evidence contract) | Frozen at M3; every later change is a coordinated multi-repository release |
| BaseAiCore P1 and P3 (goldens) | Wrong here means a data-compatibility break across nine repositories |

### 3.4 Where the plans have already done the hard part

Do **not** reach for Opus reflexively on the maths. The plans specify hand-computed expected values
for metric formulas, energy integration, KV theory, confidence factors and statistics. That is the
single biggest cost saver in this table: it converts a class of work that would normally need a
frontier model into fixture-matching. Read the phase's test list before deciding — if the expected
values are given, Sonnet is the right call.

### 3.5 Rough distribution

Of roughly 54 phases (updated 2026-08-26 for the three FreeWeight goal-benchmark phases and
SetSpec's vocabulary phase, ADR-0031/0032): **~16 Opus, ~31 Sonnet, ~7 split**. That ratio is a
consequence of the documentation quality, not of the work being easy. On an ordinary codebase the
same project would invert it. The 2026-09-02 additions (§2.10–2.11, ~26 phases across the
PromptCadence and adapter arcs) hold the ratio — roughly 9 Opus 5, 11 Sonnet 5, 4 Fable 5, 4
split — with Fable 5 confined to the four phases where reasoning-before-writing dominates and a
silent failure survives a green test suite.

---

## 4. Codex notes

The Codex column maps effort tiers rather than model names, because names move faster than this
document will be updated. Verify what your installed Codex offers before relying on the mapping.

| This table says | Means |
|---|---|
| `xhigh` | The strongest Codex reasoning tier available, on the strongest Codex model |
| `high` | High reasoning effort |
| `medium` | Default effort — correct for most of the Sonnet rows |
| `low` | Not recommended anywhere in this project; every phase has real acceptance criteria |

**Where Codex tends to fit this project well**

* The fixture-driven parser phases (SweatMeter P1–P2, ModelRack P3–P4, FreeWeight P13 adapters).
  Long, mechanical, verified by a test command — Codex's execution loop suits this closely.
* The high-volume phases with clear acceptance criteria (FreeWeight P7 and P10, IdeaPress P4 and P8).
* Migration and both-dialects work, where the loop is "run the suite against SQLite and PostgreSQL".

**Where to be more careful with Codex**

* The five phases in §3.3. Not a capability claim — a workflow one: those phases are won by reasoning
  before writing, and an agent optimized for iterating against a test suite has the weaker instinct
  there, because the interesting failures do not appear in the suite.
* The extraction phases, where the question is judgment about what *not* to carry across.
* Anything where the acceptance criterion is prose ("a user can answer 'why did it pick that model?'
  in under a minute").

**Practical split if you are using both**

Codex for the volume and the loop-friendly work; Claude Opus for the design-dense phases and for
review passes. The phases marked *split* in §2.7 are the natural handoff points — the security
portion to Opus, the parsing portion to Codex.

---

## 5. What this table cannot tell you

It is derived from the plans, not from having built any of it. Three things will change it:

1. **Your own observation.** If Sonnet clears FreeWeight P7 without a rough edge, move P8's scorers
   down too. If it struggles on WeightsDB P1's pragma-reconnect test, move P1 up.
2. **Model releases.** The allocation is about relative capability, so a new tier shifts the whole
   table rather than any one row.
3. **How much you review.** Every Sonnet row assumes you read the diff. Without that, several of them
   should be Opus — and the table would be a worse tool, because "use the best model everywhere" is
   not a plan.
