# Outstanding Work — the one schedule

**Added 2026-09-02.** Everything left to build across the [PromptCadence arc](promptcadence-roadmap.md)
(M10–M13) and the [Adapter arc](adapter-roadmap.md) (LA0–LA3), in execution order, one row per
model session. The roadmaps stay authoritative for *rationale*; the
[model-assignment guide](model-assignment.md) (§2.10–2.12) stays authoritative for *model choice*;
this document is the schedule view that answers "what do I run next, on which model".

**How to use a row.** Copy the row into an Opus session and ask it to draft the kickoff prompt for
the working session. The reading column names everything phase-specific; every session's prompt
should additionally include the standing preamble in §2 below. Batch letters group rows that are
adjacent *and* on the same model, so consecutive rows with one letter can be run back-to-back in
one sitting; letters are dependency-ordered, and §3 lists which orderings are load-bearing versus
merely convenient. All paths are relative to `~/ai/suite/docs/`.

## 1. The master table

| # | Phase → ships | Model · effort | Runs after | Work overview — and required reading | Why this model |
|---|---|---|---|---|---|
| **A1** | **Phase 0 + LA0** → ADRs accepted, docs amended | **Opus 5 · xhigh** | — (gates everything) | Write and accept ADRs D-1…D-13 and A-1…A-10 (numbered 0045+); amend master architecture per the checklists; update docs README index, gold-standards §2, traceability matrix, risk register, master-roadmap pointer; retire `harness.md` with a pointer. **Read:** `roadmap/promptcadence-roadmap.md` (§2, §7), `roadmap/adapter-roadmap.md` (§2, §9), `architecture/adapter-identity-and-serving.md`, the ADR index + ADR-0038 as the amendment precedent | Permanent contracts, but every decision is already made and argued in the roadmaps — expansion, not invention. Fable would be 2× to transcribe settled judgment |
| **A2** | BaseAiCore **0.4.1** → PyPI | **Opus 5 · high** | A1 | `DataClassification` (ordered, three levels, D-2) + `AdapterIdentity` and the canonical `+name@sha256:…` suffix (A-1); goldens; fold the deltas into the BaseAiCore spec/plan docs; publish. **Read:** accepted D-2 + A-1 ADRs, `packages/baseaicore/spec.md`, `architecture/adapter-identity-and-serving.md` §§2–3 | §3.3's BaseAiCore rule: wrong here is a data-compatibility break in every repo. Tiny phase — the premium costs almost nothing |
| **B1** | SetSpec **0.5.0** (Phase 6) → PyPI | Sonnet 5 · high | A2 | `governance.egress_decision` 1.0 (D-7/D-10), `model.adapter_manifest` 1.0 + `CapabilityEvidence` v1.1 optional adapter fields (A-1/A-4), JSON Schemas, ≥ 3 goldens each; non-adapter evidence must round-trip byte-identically (I15); fold a Phase 6 section into the SetSpec docs; publish. **Read:** `packages/setspec/spec.md`, `packages/commissioner/spec.md` (payload shape), `roadmap/adapter-roadmap.md` §3 LA0 + §7 I15, accepted D-7/D-10/A-1/A-4 | The SetSpec-P2 precedent: normative field tables → transcription with validation. Goldens get an Opus review pass in the morning |
| **B2** | LoadLedger P1 | Sonnet 5 · high | A2 | Ceilings, debits, verdicts, windows, `InMemoryLedger` — dual token+money ceilings per ADR-0030, the `unpriced_debit_count` that lets PromptCadence raise `UNPRICED_EGRESS_REFUSED` (the code itself is PromptCadence's, never this package's — ADR-0047), UTC-midnight window edges. **Read:** `packages/loadledger/spec.md`, `packages/loadledger/development-plan.md` Phase 1, ADR-0030 | §3.4 exactly: integer arithmetic with hand-computable fixtures; the UTC-midnight trap is named three times in the docs |
| **B3** | Commissioner P1 | Sonnet 5 · high | B1 | Vocabulary binding, `OrderedClassificationPolicy` (fail closed on undeclared ceiling), decision verdicts, payload round-trip against the published `setspec` 0.5.0. **Read:** `packages/commissioner/spec.md`, `packages/commissioner/development-plan.md` Phase 1, accepted D-10 | Enum-parametrized matrix, exhaustive by construction; the fail-closed row is spec'd |
| **B4** | PromptCadence P1 | Sonnet 5 · high | A2 | Repo skeleton, config, database, health endpoint, CLI stub — the standard app shape. **Read:** `apps/promptcadence/spec.md` §§1–8, `apps/promptcadence/development-plan.md` Phase 1; LoadCoach's repo layout as the precedent | Identical in shape to LoadCoach P1; boilerplate against a precise spec |
| **B5** | SetSpec **0.6.0** (Phase 7) → PyPI | Sonnet 5 · standard | B1 | `benchmark.evidence_bundle` **1.1**: the bundle nests `CapabilityEvidenceV1_1Fields` so adapter-bearing evidence can travel *inside* an exported bundle, which `1.0` cannot carry — it nests the frozen `capability.evidence` `1.0` shape by reference and does not move when that payload gains a minor ([ADR-0068](../adr/0068-a-post-freeze-minor-is-a-sibling-class.md) rule 5). Same sibling-class mechanism as B1's `capability.evidence` `1.1`: `EvidenceBundleV1_1Fields` beside an untouched `EvidenceBundleFields`, bare `EvidenceBundleOut`/`In` keep meaning `1.0`, `1.0` goldens byte-unchanged. JSON Schema, ≥ 3 goldens, docs section, publish. **Read:** ADR-0068, `packages/setspec/spec.md` §11 rule 9 + §19, B1's `capability.evidence` `1.1` as the worked example | A second application of a mechanism now written down and demonstrated once — transcription against a precedent in the same repo, which is what `standard` is for |
| **C1** | CutCtx P1 | **Opus 5 · xhigh** | A2 | Transcript model, the `_invariants` module, plan/executor split, `DropOldestPolicy` — property tests whose choice of properties is the deliverable. **Read:** `packages/cutctx/spec.md`, `packages/cutctx/development-plan.md` Phase 1, accepted D-8 | The invariants gate every future policy routes through (first-instance rule); the property choice is the judgment |
| **C2** | ToolYard P1 | **Opus 5 · xhigh** | A2 | Tool specs, registry, executor discipline, structured refusal paths — "model input never raises", fixed refusal order, fuzzed. **Read:** `packages/toolyard/spec.md`, `packages/toolyard/development-plan.md` Phase 1, accepted D-9, ADR-0018, ADR-0026 | The discipline every later tool inherits; the FakeProvider lesson — stricter than its first consumer needs |
| **C3** | LoadLedger P2 → **0.1.0** on PyPI | **Opus 5 · high** | B2 | `loadledger.sql`, `SqlLedger`, `mount_ledger_tables`, kill-mid-debit atomicity on both dialects, the miniature-host Alembic test (I14). **Read:** `packages/loadledger/development-plan.md` Phase 2, accepted D-6, ADR-0006 | First mounting implementation (first-instance rule) + atomicity on money rows — the §3.3 failure shape |
| **C4** | PromptCadence P2 | **Opus 5 · xhigh** | B4 | Domain core: threads, tiers, classification, plans, **`ExecutionIntent`**, deviation matrix, state machine from the T1–T17 tables — with the LA0 optional adapter fields born in. **Read:** `apps/promptcadence/spec.md` §9, `apps/promptcadence/lifecycle.md` §§2–5 + §8, `apps/promptcadence/development-plan.md` Phase 2, accepted D-2/D-3/D-12 | Mostly normative-table transcription — but this phase freezes the shape of the design's load-bearing wall |
| **C5** | **ModelRack: the ADR-0070 usage rule** → next minor | Sonnet 5 · high | A1 (flexible — must land before D3) | Both real adapters read usage to the per-response rule: cache detail present → disjoint classes; absent → cache classes `0`; no usage object → every class `UNSUPPORTED`. `FakeProvider` defaults to `0` with scripted `UNSUPPORTED` still possible; recorded fixtures re-annotated; the three-case conformance test; the Ollama `prompt_eval_count` fixture check. Spec contract 2 is already amended. **Read:** ADR-0070, ADR-0069 §"Not decided here", `packages/modelrack/spec.md` §11 + §18, the two `_read_usage` functions and their fixtures | Two small functions against a stated rule, but in a package three apps call and with a named fabricated-zero failure mode — high, not standard |
| **C6** | **LoadCoach: four token classes on the wire** → next LoadCoach minor | Sonnet 5 · standard | C5 | `cache_write_tokens` + `cache_read_tokens` on the attempts and jobs rows (one migration) and on the job document's `usage`, `"unsupported"` per ADR-0016 rule 4; `apps/loadcoach/data-model.md` and `api.md` amended first; additive within `/api/v1`. **Read:** ADR-0070 decision 7, `apps/loadcoach/data-model.md`, `apps/loadcoach/api.md`, `services/queue.py`'s `JobView` and the worker's usage capture | Additive columns and fields transcribed from an ADR; the migration is the only judgment |
| **D1** | **ToolYard P2** (sandbox) | **Fable 5 · xhigh — daytime, reviewed** | C2 | Containment + tiered isolation (container → bwrap → refuse), TOCTOU and prefix-collision cases; marked tests need the reference machine's bwrap. **Read:** `packages/toolyard/development-plan.md` Phase 2, accepted D-9, ADR-0018 | Adversarial with a silent-failure class — an escape that works is quiet. Never overnight |
| **D2** | **PromptCadence P3** | **Fable 5 · xhigh — daytime, reviewed** | C4 | LoadCoach client, bypass loop, lease/claim, kill −9 recovery, one-write transitions (ADR-0044), events — **plus the fake LoadCoach every later phase trusts** (I10 contract tests against the OpenAPI snapshot). **Read:** `apps/promptcadence/development-plan.md` Phase 3, `apps/promptcadence/lifecycle.md` §8.3 + §10, ADR-0036/0044, `roadmap/promptcadence-roadmap.md` §9 I10 | The LoadCoach-P5-shaped phase: no feedback loop for the interesting failures, and the fake doubles the stakes |
| **D3** | **ModelRack P6** (LA1 start) | **Fable 5 · xhigh — daytime, reviewed** | A1 + C5 (flexible — placed here for model adjacency) | `LlamaCppProvider` process supervision: spawn/health-wait/terminate, kill-tree, pid files, port range, GGUF discovery + hashing, generation + streaming, version-annotated recorded fixtures; usage read to the ADR-0070 rule from the start. **Read:** `roadmap/adapter-roadmap.md` §4.1 P6, `architecture/adapter-identity-and-serving.md` §§4–6, accepted A-5, ADR-0070, `packages/modelrack/spec.md` (Provider protocol) | Concurrency with orphan/leak guarantees, no useful feedback loop, in a package three apps call — the §3.3 class |
| **E1** | CutCtx P2 → **0.1.0** on PyPI | Sonnet 5 · high | C1 (flexible until I1) | `ObservationMaskingPolicy`, `SummarizingPolicy` (planned requests, never executed — D-8), `PolicyChain`; the contiguous-group dict-ordering trap is golden-tested. **Read:** `packages/cutctx/development-plan.md` Phase 2, accepted D-8 | Policies against locked invariants; the one risky spot is named in the plan |
| **E2** | ToolYard P3 → **0.1.0** on PyPI | Sonnet 5 · high | D1 | Built-in tools; `http_fetch` implements ADR-0026 §3 with the vectors byte-shared with LoadCoach's suite. **Read:** `packages/toolyard/development-plan.md` Phase 3, ADR-0026 §3 | Fixture/vector work; Opus reviews the fetch-handler diff |
| **E3** | Commissioner P2 → **0.1.0** on PyPI | Sonnet 5 · standard | B3 + C3 | Append-only ledgers + mounting — copies LoadLedger P2's proven pattern verbatim. **Read:** `packages/commissioner/development-plan.md` Phase 2, LoadLedger P2's implementation as the template | The "rest of the repeated thing" — the pattern is proven twice by now |
| **E4** | PromptCadence P4 | Sonnet 5 · high | D2 + E2 | ToolYard integration, workspace lifecycle, `undeclared_tool` deviation wiring; hostile-model journey tests are specified. **Read:** `apps/promptcadence/development-plan.md` Phase 4, `apps/promptcadence/lifecycle.md` §5 | ToolYard did the hard part. Opus reviews the workspace-lifecycle diff |
| **F1** | PromptCadence P5 | Split: **Opus 5 · high** core, Sonnet 5 · high edges | C3 + C6 + E4 | Budget wiring: LoadLedger mounted, crash-reconciliation of debits idempotent by `source_ref` (the Opus half); estimator with labeled sources, ceilings (per-trajectory, per-day with the `awaiting_window` park, per-project), config, CLI (the Sonnet half). **Read:** `apps/promptcadence/development-plan.md` Phase 5, `apps/promptcadence/lifecycle.md` §6, ADR-0030, accepted D-3 | Reconciliation is money-adjacent crash logic; the rest is plumbing against spec'd maths |
| **F2** | PromptCadence P6 | **Opus 5 · high** | E3 + F1 | Egress evaluation via Commissioner, verification, category-typed deviations, the violation→halt path, re-approval feed. **Read:** `apps/promptcadence/development-plan.md` Phase 6, `apps/promptcadence/lifecycle.md` §5, `packages/commissioner/spec.md`, accepted D-4/D-12 | Fail-closed semantics and the violation path — adversarial-adjacent |
| **F3** | ModelRack P7 | **Opus 5 · xhigh** | D3 (flexible — model adjacency) | Launch-time adapter registration, per-request selection, `adapter_hot_swap`, `AdapterNotFound`, digest-verified compatibility, `pending_restart`, **the cache-correctness conformance test** (prefix under A never reused for B, I17). **Read:** `roadmap/adapter-roadmap.md` §4.1 P7 + §7 I17, accepted A-1/A-5/A-6 | The prefix-reuse property is exactly the intermittent-defect shape; the conformance-test design is the judgment |
| **G1** | **PromptCadence P7** → **0.9.0b0 — M11 beta** | **Fable 5 · xhigh — daytime, reviewed** | F2 | Planner, approval modes (`auto`/`hybrid`/`manual`), intent minting in both paths, DAG ready-set dispatch, **the governance-invariance diff (contract 1, I11)**, plan-schema resilience against real local models. **Read:** `apps/promptcadence/development-plan.md` Phase 7, `apps/promptcadence/lifecycle.md` §4 + §8.4, accepted D-3/D-4/D-5/D-12, `roadmap/promptcadence-roadmap.md` §9 I11 | Design-dense, live-model interaction, and the arc's central proof — a failed pass invalidates the design claim, not just the code |
| **H1** | ModelRack P8 → publish (LA1 done) | Split: **Opus 5 · high** + Sonnet 5 · standard | F3 | Cancellation under supervision + leak tests (20 cycles, no orphan, flat memory) — Opus; conformance suite green across all four providers, docs, publish — Sonnet. LA1 exit needs a GPU session: 20 alternating-adapter generations, zero base loads (I16). **Read:** `roadmap/adapter-roadmap.md` §4.1 P8 + §3 LA1 exit | Leak/cancellation reasoning vs. publication mechanics — a clean split |
| **H2** | **LoadCoach 1.1** (LA2) | **Opus 5 · xhigh** | H1 | Generalized LC-E1 (`[providers.<name>]`, D-11), adapter registry + `adapters scan|list|show`, subject expansion + compatibility/classification filters, `require_adapter_evidence` gate, pins, two-level residency (`base_switch_penalty`, `ignore_residency`), per-subject reliability, explanations/UI. Also carries the unreleased `2c7d740` fix. Exit: the IdeaPress three-stage demo — one base load (I16), classification denial recorded (I19). **Read:** `roadmap/adapter-roadmap.md` §4.2 + §7 I13/I16/I19, accepted D-11/A-4/A-7/A-8/A-9/A-10, `apps/loadcoach/spec.md` | Routing semantics frozen into persisted explanations — the LoadCoach-P3 precedent, extended |
| **H3** | IdeaPress adapter pins → minor release | Sonnet 5 · standard | H2 | Per-stage adapter pins in config passed as the LoadCoach override; provenance columns on every attempt; direct/Ollama mode stays adapter-free. **Read:** `roadmap/adapter-roadmap.md` §4.4, accepted A-7 | Config + override passthrough against a settled contract |
| **H4** | FreeWeight 1.1 (LA3) | Sonnet 5 · high | H2 + B5 | `[adapters] directory`, subject enumeration, `--adapter` flag, the A-2 panel policy (declared + regression + performance), serving-mode A/B, evidence export with v1.1 fields (an import change — `CapabilityEvidenceV1_1Out`/`In`; the bare names still mean `1.0`, ADR-0068 rule 3 — and bundled export needs B5's `benchmark.evidence_bundle` `1.1`), comparison UI grouped by base. Exit I18 needs a GPU session. **Read:** `roadmap/adapter-roadmap.md` §4.3 + §7 I18, accepted A-2/A-3, `apps/freeweight/spec.md` | Measurement plumbing on an existing engine; panel composition is spec'd |
| **I1** | PromptCadence P8 | Split: **Opus 5 · high** + Sonnet 5 · standard | G1 + E1 | Materialization/invalidation of explanation revisions with the `materialize(rows) == compose_live(rows)` golden (D-13) — Opus; CutCtx wiring and the MirrorWall operator UI volume — Sonnet. **Read:** `apps/promptcadence/development-plan.md` Phase 8, `apps/promptcadence/lifecycle.md` §7 + §9.1, accepted D-8/D-13 | Cache-consistency reasoning vs. UI volume — a clean split |
| **I2** | **PromptCadence P9** → **1.0.0 — M12** | Split: **Opus 5 · xhigh** security (consider Fable 5 for the injection corpus), Sonnet 5 · high perf/docs | I1 + H2 | Hardening: the prompt-injection corpus as a release gate, spec §20 criteria, overhead budget (≤ 25 ms/turn), live remote-tier trajectory via LC-E1 (I13) *or* the recorded release-scope decision to ship with remote tiers refusing honestly. **Read:** `apps/promptcadence/development-plan.md` Phase 9, `apps/promptcadence/spec.md` §20, `roadmap/promptcadence-roadmap.md` §9 I13 + §10 | The security half is pure adversarial and never overnight; measurement and docs are not |
| **J1** | IdeaPress 1.1: IP-A1 LoadLedger | Sonnet 5 · high | I2 | Mount the tables, debit per attempt with `pricing_hash`; a per-output ceiling (`PER_RUN`, the unit id) and a per-project ceiling (`PER_TAG`, `project:<id>`, lifetime) from IdeaPress's configuration, resolved per operation (LoadLedger plan Phase 2); per-unit/per-project cost and position in the UI (`—` + reason for unpriced local; "at least" for a floor). Delete the in-app equivalent. **Read:** `roadmap/promptcadence-roadmap.md` §6.1, `packages/loadledger/spec.md` §2 + §21, ADR-0030, ADR-0069 | Third mounting by now; the shape is adopt-delete-prove |
| **J2** | IdeaPress 1.1: IP-A2 Commissioner | Sonnet 5 · standard | I2 | The S4 egress badge reads recorded decisions; denials visible in project history; badge backed by rows, not a flag. **Read:** `roadmap/promptcadence-roadmap.md` §6.2, `packages/commissioner/spec.md` | Reading rows into an existing badge — small and spec'd |
| **J3** | IdeaPress 1.1: IP-A3 CutCtx → **1.1.0** | Sonnet 5 · high | I2 | `project_review` context assembly as a policy chain; in-app reduction code deleted; golden-tested identical output on fixture projects. **Read:** `roadmap/promptcadence-roadmap.md` §6.3, `packages/cutctx/spec.md` | Golden-parity refactor — the safest kind, but worth `high` since it deletes working code |

### 1.1 M9 — Suite 1.0, outside the arcs

One outstanding milestone predates both arcs and appears in neither: **M9, the professional
delivery checklist** ([master-roadmap §7](master-roadmap.md)) over the nine existing components.
It neither gates nor is gated by any row above — it can run any time, in parallel with anything.
Suggested treatment: one **Opus 5 · high** audit session that walks §7 against the repos as they
stand and emits a gap list (many boxes are likely already true and just unchecked), then ordinary
**Sonnet 5 · high** sessions per gap (docs generation, backup/restore and migration-path tests,
compatibility matrix); the declaration itself is a human step. Note for the A1 session: master
roadmap §9's "current state" is frozen at end-of-M7 and should be corrected to the true state
(all nine components tagged and published) in the same pass that adds the M10–M13 pointer row.

## 2. The standing preamble for every kickoff prompt

Every session's prompt, regardless of row, should state:

* The component directory to work in (never the workspace root), its venv, and
  `pip install -e ".[dev]"` if the repo is fresh.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, one Conventional
  Commit per phase. Name the interpreter in the report (M5C-13).
* The house method: docstring-first, `from __future__ import annotations`, units in names,
  keyword-only optionals, injected clocks/providers/roots.
* Read `architecture/master-architecture.md` §§1–3 and the component's gold-standards section
  before the row's reading list.
* New packages pin unpublished suite deps as local path/editable installs with a
  `TODO: re-pin on publish` until the PyPI release lands.
* Overnight rules ([model-assignment §2.12](model-assignment.md)): Sonnet rows run at effort
  **high** overnight; **batches D and G and I2's security half never run overnight** — they are
  won by review and fail silently.

## 3. Which orderings are load-bearing

Hard edges — never reorder across these:

* **A1 before all code** — ADRs before implementation, the standing rule.
* **B1 before B3** — the payload publishes before its consumer pins it (the FreeWeight-P11 lesson).
* **B5 before H4** — a bundle cannot carry adapter evidence until the bundle has a minor that
  nests it; the same rule, one payload out (ADR-0068 rule 5).
* **C5 before D3** — the usage rule (ADR-0070) before the third adapter is written; a retrofit
  is a fixture re-annotation nobody wants.
* **C6 before F1** — all four token classes on LoadCoach's wire before the harness prices them;
  without it a strict money ceiling trips on every remote turn (ADR-0069 §"Not decided here").
* **D1/E2 before E4** — no tool executes in PromptCadence before the discipline is published
  (a security ordering).
* **PromptCadence P1→…→P9 strictly in order**; each package's phases in order.
* **H2 before I2's live-remote verification** — both touch LoadCoach; land LA2, then verify once.
* **J-rows after I2** — adoption targets a released 1.0, never a moving target (ADR-0011).

Everything else is convenience. Genuinely flexible rows, placed for model adjacency: **D3/F3/H1**
(the ModelRack stream can slot anywhere after C5, whenever harness work blocks), **E1** (only
I1 needs it), **B1** (only B3 needs it), **B5** (only H4 needs it), **H3** (any time after H2). One resource rule: LA1/LA2
GPU sessions never share the machine with FreeWeight benchmark runs.

## 4. Not model sessions — the human/ops checklist

* Create the five repos (cutctx, toolyard, loadledger, commissioner, promptcadence) with the
  standard toolchain + CI; reserve the PyPI names; mirror each component's docs byte-identically
  on repo creation.
* Per release: tag, Release-workflow `pypi` environment approval, post-publish install check.
* Review the morning diffs for every overnight batch; review Fable batch output same-day.
* GPU sessions on the reference machine for the LA1 exit (I16 zero-base-loads run), the LA2 exit
  (the three-stage one-base-load demo), and H4's serving-mode A/B — never beside a FreeWeight
  benchmark.
* Re-run the IdeaPress standalone journey and read the output (the M8 leftover) before IdeaPress
  1.1 work begins.
* Optional: extend `suite-flowchart.drawio` with PromptCadence's final shape and the adapter arc.

## 5. Milestone map

| Milestone | Rows | Declared when |
|---|---|---|
| **M9** — Suite 1.0 (pre-arc) | §1.1 — audit + gap sessions, any time | Master-roadmap §7 checklist complete over the nine existing components |
| **M10** — foundations | A1–F2 package rows (A1, A2, B1–B3, C1–C3, C5, C6, D1, E1–E3) | All four packages at 0.1.0, clean-venv acceptance scripts pass |
| **M11** — beta | B4, C4, D2, E4, F1, F2, G1 | The planned-vs-bypassed demo on real LoadCoach; `0.9.0b0` |
| **LA1/LA2/LA3** | D3, F3, H1 / H2, H3 / B5, H4 | Adapter-roadmap §3 exit conditions |
| **M12** — 1.0 | I1, I2 (+ H2 as the LC-E1 dependency) | Spec §20; `promptcadence 1.0.0` published |
| **M13** — adoption | J1–J3 | IdeaPress 1.1; every package has two real consumers |
