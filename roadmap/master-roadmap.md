# Master Development Roadmap

**From:** empty repositories (architecture frozen 2026-08-21).
**To:** three professionally deliverable applications and six published packages.
**Corrected 2026-08-21** by the [final architecture audit](../reviews/final_architecture_audit.md):
the prompt library moves from FreeWeight P7 into P6 (the fingerprint needs it), `setspec.prompts` is
extracted at LoadCoach P4 alongside MirrorWall, and LoadCoach P3 gains the VRAM estimator its
constraint filter requires.
**Sequencing principle:** dependency order and rework risk, not calendar dates. No phase is dated,
because a single-maintainer project's calendar is a fiction; every phase instead has prerequisites,
acceptance criteria and an exit condition.
**Amended 2026-08-26** by [ADR-0031](../adr/0031-user-defined-goal-benchmarks.md) and
[ADR-0032](../adr/0032-judge-validity-and-user-capability-namespace.md): FreeWeight gains three
phases (P8A, P8B, P10A — user-defined goal benchmarks) between its existing P8 and P11, and SetSpec
gains Phase 3A (capability vocabulary 1.1, the goal payload schemas), landing inside the existing
`setspec 0.3` release rather than as a new one. M2 and M3's content and exit conditions below are
updated accordingly; no milestone number, package range or cross-application dependency edge moved.

---

## 1. Milestones

| #      | Milestone                                | Content                                                                            | Exit condition                                                                                                     |
| ------ | ---------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **M1** | Package foundation                       | BaseAiCore 0.4 · SetSpec 0.1–0.2 (draft payloads) · ModelRack 0.5 · SweatMeter 0.3 | A script using only these packages discovers a model, generates text, and prints machine telemetry                 |
| **M2** | FreeWeight beta                          | FreeWeight P1–P10A                                                                 | A real model is benchmarked end to end; results are drillable, comparable and exportable; a subjective goal can be authored, calibrated and scored entirely from the UI ([P10A](../apps/freeweight/development-plan.md#phase-10a--the-goal-authoring-wizard-and-starter-packs--completes-m2-beta)) |
| **M3** | FreeWeight 1.0-rc · **contract freeze**  | FreeWeight P11 (built on P8A/P8B/P10A) · SetSpec 0.3 (schemas frozen incl. capability vocabulary 1.1 and the goal payloads, goldens published) | An evidence bundle is consumed by a `setspec`-only harness with no FreeWeight code or DB access, including a calibrated `user.*` goal record |
| **M4** | LoadCoach beta · **extraction complete** | LoadCoach P1–P6 · WeightsDB 0.2 · MirrorWall 0.2 · SetSpec 0.4 (`setspec.prompts`) | LoadCoach routes, executes, streams and imports FreeWeight evidence; two applications share the extracted packages |
| **M5** | LoadCoach 1.0                            | LoadCoach P7–P9                                                                    | Explainable, durable, secure routing service; published to PyPI                                                    |
| **M6** | FreeWeight 1.0                           | FreeWeight P12–P14                                                                 | FreeWeight on the shared packages, external adapters, hardened; published to PyPI                                  |
| **M7** | IdeaPress beta                           | IdeaPress P1–P6                                                                    | A complete project is produced and exported with **only Ollama** present                                           |
| **M8** | IdeaPress 1.0                            | IdeaPress P7–P9                                                                    | Optional LoadCoach backend; hardened; published to PyPI                                                            |
| **M9** | Suite 1.0                                | Integration verification, cross-repository CI, documentation set, public release   | Every gold standard met; all install paths verified; release notes published                                       |

---

## 2. Dependency graph

```mermaid
graph TD
    BC["BaseAiCore 0.4"] --> SS["SetSpec 0.1–0.2"]
    BC --> MR["ModelRack 0.5"]
    BC --> SM["SweatMeter 0.3"]
    SS --> FW1["FreeWeight P1–P10A<br/>M2 beta"]
    MR --> FW1
    SM --> FW1
    FW1 --> FW2["FreeWeight P11<br/>M3 1.0-rc"]
    FW2 --> SSF["SetSpec 0.3<br/>schemas frozen"]
    SSF --> FW2
    FW2 --> LC1["LoadCoach P1–P6<br/>M4 beta"]
    LC1 --> WDB["WeightsDB 0.2<br/>(extracted at LC-P1)"]
    LC1 --> MW["MirrorWall 0.2<br/>(extracted at LC-P4)"]
    LC1 --> SSP["SetSpec 0.4<br/>setspec.prompts<br/>(extracted at LC-P4)"]
    SSP --> FW3
    SSP --> IP1
    LC1 --> LC2["LoadCoach P7–P9<br/>M5 1.0"]
    WDB --> FW3["FreeWeight P12–P14<br/>M6 1.0"]
    MW --> FW3
    WDB --> IP1["IdeaPress P1–P6<br/>M7 beta"]
    MW --> IP1
    MR --> IP1
    LC2 --> IP2["IdeaPress P7–P9<br/>M8 1.0"]
    IP1 --> IP2
    FW3 --> SUITE["M9 Suite 1.0"]
    LC2 --> SUITE
    IP2 --> SUITE
```

The one non-obvious edge is **FreeWeight P11 → SetSpec 0.3 → FreeWeight P11**: the schemas are frozen
only after FreeWeight has produced real results against the draft models, and FreeWeight's evidence
export then ships against the frozen schemas. Freezing a contract before its producer exists is a
guess; this ordering makes it an observation.

---

## 3. Work streams and what can proceed in parallel

Four streams. Within a stream, phases are strictly ordered; across streams, the table states what may
overlap.

| Stream | Contents |
|---|---|
| **A — Foundation packages** | BaseAiCore, SetSpec, ModelRack, SweatMeter |
| **B — FreeWeight** | FreeWeight P1–P14 (18 phases total: adds P8A, P8B, P10A for user-defined goal benchmarks) |
| **C — LoadCoach + extractions** | LoadCoach P1–P9, WeightsDB, MirrorWall |
| **D — IdeaPress** | IdeaPress P1–P9 |

```mermaid
gantt
    dateFormat X
    axisFormat %s
    title Sequencing by dependency (units are phases, not time)

    section A Foundation
    BaseAiCore P1-P4         :a1, 0, 4
    SetSpec P1-P3            :a2, after a1, 3
    ModelRack P1-P5          :a3, after a1, 5
    SweatMeter P1-P4         :a4, after a1, 4
    SetSpec P4 freeze        :a5, 15, 1

    section B FreeWeight
    FW P1-P2 skeleton+storage :b1, after a1, 2
    FW P3-P4 models+telemetry :b2, after a3, 2
    FW P5-P9 + 8A/8B engine+benchmarks+goals :b3, after b2, 7
    FW P10-P10A UI+goal wizard (M2)         :b4, after b3, 2
    FW P11 evidence (M3)                    :b5, after b4, 1
    FW P12-P14 adopt+ext (M6) :b6, after c2, 3

    section C LoadCoach
    LC P1-P4 + WeightsDB + MirrorWall (M4 pt1) :c1, after b5, 4
    LC P5-P6 queue+evidence (M4)               :c2, after c1, 2
    LC P7-P9 feedback+UI+harden (M5)           :c3, after c2, 3

    section D IdeaPress
    IP P1-P6 standalone (M7)  :d1, after c1, 6
    IP P7-P9 loadcoach (M8)   :d2, after c3, 3

    section Suite
    M9 Suite 1.0              :e1, after b6, 2
```

### 3.1 Explicit parallelism rules

| These may run concurrently | Because |
|---|---|
| ModelRack P1–P5 and SweatMeter P1–P4 | Both depend only on BaseAiCore; no shared surface |
| SetSpec P1–P3 and ModelRack/SweatMeter | SetSpec does not depend on either |
| FreeWeight P1–P2 and ModelRack P3–P5 | FreeWeight's skeleton and storage need no provider |
| FreeWeight P8A and FreeWeight P8 | P8A's only prerequisite is P7; it does not need P8's judge infrastructure. P8B is the join point — it needs both P8 and P8A complete |
| FreeWeight P12–P14 and LoadCoach P7–P9 | Different repositories; FreeWeight P12 needs only the *published* WeightsDB/MirrorWall |
| IdeaPress P1–P6 and LoadCoach P5–P9 | IdeaPress standalone needs no LoadCoach, only the extracted packages |
| IdeaPress P1–P6 and FreeWeight P12–P14 | Entirely independent |
| Documentation and hardening within any application's final phases | Different files, same acceptance gate |

| These may **not** overlap | Because |
|---|---|
| FreeWeight P11 and SetSpec P4 (freeze) | Circular by design; sequence is draft → real results → freeze → export |
| FreeWeight P9 and FreeWeight P8A–P8B | P9 depends only on P6 and P8, not on the goal phases; both branches must finish before P10A, but neither blocks the other |
| LoadCoach P1 and FreeWeight's storage refactor | WeightsDB is extracted *from* FreeWeight; FreeWeight must be stable first |
| MirrorWall extraction and FreeWeight UI changes | The extraction is a move, not a copy; a moving target breaks it |
| IdeaPress P7 and LoadCoach P1–P9 | The LoadCoach backend requires a stable, released LoadCoach API (M5) |
| Any two GPU-bound work streams on the reference machine | One GPU; benchmark measurements are invalid when shared |

### 3.2 The single-maintainer reality

With one person, "parallel" means *unblocked*, not *simultaneous*. The practical ordering that
minimizes context switching is: finish stream A; drive stream B to M3; drive stream C to M4; then
alternate between B (P12–P14) and D (P1–P6) as each hits a natural pause; finish C to M5; finish D;
then M9. The parallelism table above matters mainly for deciding what to pick up when something is
blocked — for example, when a live benchmark run is occupying the GPU for an hour.

---

## 4. Integration milestones

Points where two components must actually work together. Each has a dedicated verification, and none
is considered complete on the basis of a code review.

| # | Integration | At | Verification |
|---|---|---|---|
| **I1** | FreeWeight ↔ ModelRack | FW P3 | Discovery through ModelRack only; no provider HTTP code in FreeWeight (asserted) |
| **I2** | FreeWeight ↔ SweatMeter | FW P4 | Telemetry bar live; machine profile persisted; no-GPU path exercised |
| **I3** | FreeWeight → SetSpec | FW P6, frozen at FW P11 | Exported results validate against schemas and goldens |
| **I4** | FreeWeight → LoadCoach (evidence) | LC P6 | A bundle produced by FreeWeight changes LoadCoach routing, verified with **no shared code and no shared database**; a `user.*` goal capability in the bundle changes nothing unless a task profile names it explicitly ([ADR-0032 §6](../adr/0032-judge-validity-and-user-capability-namespace.md)) |
| **I5** | WeightsDB ↔ two applications | LC P1, FW P12 | Two schemas, two migration histories, one package; FreeWeight's test suite passes unchanged after adoption |
| **I6** | MirrorWall ↔ two applications | LC P4, FW P12 | Both applications' template suites render against the same version in CI |
| **I7** | IdeaPress ↔ LoadCoach | IP P7 | Backend switch changes no workflow code; degradation and version mismatch handled; feedback lands in LoadCoach's reliability stats; every task ID in `LOADCOACH_TASK_MAP` exists in the running LoadCoach's `/task-profiles`; the prompt LoadCoach forwards equals the prompt IdeaPress rendered |
| **I9** | Prompt hashing across components | LC P4, FW P12 | The same prompt record hashes identically under FreeWeight's, LoadCoach's and IdeaPress's installed `setspec`, and FreeWeight's pack hashes unchanged across the adoption |
| **I8** | Full suite | M9 | All three running together on one machine; every optional link exercised on and off |

---

## 5. Stabilization phases

Stabilization is scheduled work, not what happens if there is time left.

| Phase | When | Content | Gate |
|---|---|---|---|
| **S1 — Foundation stabilization** | End of M1 | Package APIs reviewed against their first real consumer; breaking changes made now while everything is `0.x`; golden values locked | Every package installs alone, type-checks from a consumer, ≥ 95 % coverage |
| **S2 — FreeWeight stabilization** | FW P14 (M6) | Performance budgets, security checklist, accessibility audit, upgrade testing from every released version, documentation | All FreeWeight acceptance criteria and gold standards met |
| **S3 — LoadCoach stabilization** | LC P9 (M5) | Auth and LAN-exposure review, scheduling simulation at scale, security checklist, operations documentation | All LoadCoach acceptance criteria and gold standards met |
| **S4 — IdeaPress stabilization** | IP P9 (M8) | Model-output sanitization sweep, archive-import hardening, performance, documentation | All IdeaPress acceptance criteria and gold standards met |
| **S5 — Suite stabilization** | M9 | Cross-repository compatibility matrix, install-path verification, documentation consistency review, dependency audit, release notes, **and the package-1.0 range widening** (every application needs a release whose ranges admit the 1.0 packages — see [Packaging Standards §4](../standards/packaging-and-release-standards.md)) | Every item in §7 checked |

---

## 6. Version trajectory

**Packages**

| Component | M1 | M2 | M3 | M4 | M5 | M6 | M8 | M9 |
|---|---|---|---|---|---|---|---|---|
| BaseAiCore | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.6 | 0.6 | **1.0** |
| SetSpec | 0.2 | 0.2 | **0.3** (frozen) | 0.4 | 0.4 | 0.4 | 0.5 | **1.0** |
| ModelRack | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.7 | 0.7 | **1.0** |
| SweatMeter | 0.3 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | **1.0** |
| WeightsDB | — | — | — | **0.2** | 0.2 | 0.3 | 0.3 | **1.0** |
| MirrorWall | — | — | — | **0.2** | 0.2 | 0.3 | 0.4 | **1.0** |

**Applications**

| Component | M2 | M3 | M4 | M5 | M6 | M8 | M9 |
|---|---|---|---|---|---|---|---|
| FreeWeight | **0.9-beta** | 1.0-rc | 1.0-rc | 1.0-rc | **1.0** | 1.0 | **1.0** |
| LoadCoach | — | — | **0.9-beta** | **1.0** | 1.0 | 1.0 | **1.0** |
| IdeaPress | — | — | — | — | — | **1.0** | **1.0** |

**FreeWeight is `0.9-beta` at M2**, not `0.1.0`. The trajectory used to start it at M3, which left
the version of a feature-complete application undecided and understated ten delivered phases to
anyone reading the version alone. `0.9-beta` says the true thing — every phase through 10A is
built; the contracts are not frozen until M3 — and mirrors LoadCoach's own beta. In PEP 440 that is
`0.9.0b0`; the tag is cut at M2 exit, not before, because the exit condition is a demonstration on a
real model rather than a state of the source.

SetSpec's M4 column is **0.4**, not 0.3: `setspec.prompts` is extracted during LoadCoach P4
([ADR-0028](../adr/0028-prompt-pack-granularity.md)). The schema freeze at M3 is unaffected —
prompt tooling is additive and the frozen payload schemas do not change.

SetSpec's M3 column, `0.3 (frozen)`, also carries capability vocabulary **1.1** and the
`benchmark.goal_pack` / `benchmark.calibration_report` schemas
([ADR-0031](../adr/0031-user-defined-goal-benchmarks.md),
[ADR-0032](../adr/0032-judge-validity-and-user-capability-namespace.md)). These land via
[SetSpec Phase 3A](../packages/setspec/development-plan.md#phase-3a--capability-vocabulary-11-and-the-goal-payloads),
which ships inside the same `0.3.0` release as Phase 4 rather than as a separate one — no version
pin in any consuming `pyproject.toml` changes.
| FreeWeight | — | 1.0-rc | 1.0-rc | 1.0-rc | **1.0** | 1.0.x | 1.1 |
| LoadCoach | — | — | 0.9-beta | **1.0** | 1.0.x | 1.0.x | 1.1 |
| IdeaPress | — | — | — | — | 0.9-beta | **1.0** | 1.0.x |

**Corrected at M5 (2026-08-30), closing the discrepancy the M4 review recorded.** The table had
BaseAiCore at 0.5 and ModelRack at 0.6 from M4, and MirrorWall at 0.3 at M5, with no phase in any
of those packages' plans behind the bumps and no entry in the milestones' Content columns. The
columns now say what the packages are — 0.4, 0.5 and 0.2 — through M5, and the bumps stay at M6,
which is the first milestone whose content touches them. A version bump with no change behind it
is exactly the fiction the FreeWeight note above argues against. SetSpec's M4 column reads 0.4 for
the reason stated below.

Packages reach 1.0 only at M9, when all three applications have exercised them. Applications reach
1.0 when their own acceptance criteria pass — an application at 1.0 depending on a `0.x` package is
deliberate and honest, and the compatible-range pinning in
[Packaging Standards](../standards/packaging-and-release-standards.md) makes it safe.

---

## 7. M9 — Professional delivery checklist

Nothing here is optional; each maps to requirement §37.

**Installation and distribution**
- [ ] `pip install freeweight|loadcoach|ideapress` into a clean venv, each starting with zero configuration
- [ ] `pipx install` verified for all three
- [ ] All six packages installable and importable standalone
- [ ] `python -m <app>` works for all three
- [ ] Optional extras (`[postgres]`) install and function

**Releases**
- [ ] Every component released from a tag by CI with Trusted Publishing; no manual upload has ever occurred
- [ ] Semantic versions, changelogs and release notes for every component
- [ ] Compatibility matrix published per application (tested package ranges)
- [ ] Checksums published for application artifacts

**Documentation**
- [ ] README per repository with purpose, install, quickstart and links
- [ ] Configuration reference per application, generated and CI-diff-checked
- [ ] API documentation per application: OpenAPI snapshot plus a written guide
- [ ] `--help` complete and correct at every CLI level
- [ ] Web UI help/about page per application
- [ ] Troubleshooting guide per application, aligned with `<app> doctor`
- [ ] Security documentation: trust boundaries, exposure, egress, sandboxing
- [ ] Backup and restore procedure per application, tested
- [ ] Upgrade guide from every released version; rollback considerations documented
- [ ] Developer documentation and `CONTRIBUTING.md` per repository
- [ ] This documentation set reviewed for consistency (§8) and published

**Quality**
- [ ] Every gold standard in [Gold Standards](../standards/gold-standards.md) met and measured
- [ ] Coverage floors met in every repository
- [ ] Performance budgets measured on the reference machine and published with the machine described
- [ ] Security checklist complete; `pip-audit` and `gitleaks` clean
- [ ] Accessibility checklist complete for all three UIs
- [ ] Cross-repository compatibility matrix green

**Operations**
- [ ] Migration path tested from every released version with real data
- [ ] Downgrade procedure exercised: upgrade, write data, restore the pre-migration backup, start the
      older version — and a database ahead of the code refuses with `SchemaAhead` naming both revisions
- [ ] Every application's dependency ranges admit the 1.0 packages, verified by a clean-venv resolve
- [ ] Backup/restore tested on both dialects
- [ ] `<app> doctor` diagnoses every documented failure mode
- [ ] Degradation matrix exercised end to end for all three applications

---

## 8. Documentation consistency review (repeated before every milestone)

The review in [§9 of this roadmap](#9-current-state-and-immediate-next-steps) is run at each
milestone, not only at M9. It checks: component names, public contracts, model identity terms,
configuration precedence, API conventions, database ownership, no cross-application DB access, no
package importing an application, each application independently runnable, the optional links, tests
planned before implementation, acceptance criteria present in every phase, and rationale recorded for
every architectural decision. Any drift is fixed in the documentation before the milestone is
declared.

---

## 9. Current state and immediate next steps

**Current state (2026-08-30, end of M5's build work).** The architecture is frozen and `docs/` is
complete; nine repositories exist and seven of them hold working software.

| Component | Version | State |
|---|---|---|
| BaseAiCore | 0.4.0 | Complete through its plan; published |
| SetSpec | 0.4.0 | Schemas frozen at 0.3; `setspec.prompts` at 0.4; published |
| ModelRack | 0.5.0 | Complete; published |
| SweatMeter | 0.4.0 | Complete; published |
| WeightsDB | 0.2.0 | P1–P3 complete; **published** |
| MirrorWall | 0.2.0 | P1–P2 complete; **published** |
| FreeWeight | 1.0.0rc1 | P1–P11 plus P12-early complete |
| LoadCoach | 1.0.0 | P1–P9 complete; M5 verification's fourteen findings closed (handoff M5C-1…15); **CI green on the real runner** (run 33334510805, every job); release **prepared, not tagged** |
| IdeaPress | — | Scaffold only; tooling verified, no phase started |

M5's own content — LoadCoach P7–P9 — is built: production feedback, reliability and regression
detection; the complete operator UI; auth hardening with scopes checked at the route and in the
service, rate limits, queue caps, CSRF, body limits and content retention; every spec §15 budget
measured; Security Standards §14 held item by item; the seven operator documents; and a `doctor`
that names every documented failure mode. The M5 exit condition reads *"Explainable, durable,
secure routing service; published to PyPI"*: the first three adjectives are met with evidence in
the M5 handoff; the fourth clause is a publish, which is a human decision this run did not take.

**The one thing standing between here and M5 is the `loadcoach` tag.** Both extracted packages
are on PyPI; `LoadCoach/requirements/ci.lock` is generated and audited; every CI job installs from
it; the suite passed in a fresh non-root virtualenv installed from the lock; and spec §20 AC1 was
run against a real Ollama from a clean index-only install (M5-25 in the handoff).

The next actions, in order:

1. ~~Let CI go green on the real runner~~ — **done, and it took three findings to get there**:
   the suite only collected under `python -m pytest` (the closeout's F1), a GPU-dependent test
   fixture (M5C-14), and a migration that was a PostgreSQL syntax error nothing local could see
   (M5C-15). Run `33334510805` on `eeef0f4` is green on every job, the first in the
   repository's history.
2. ~~Run the M5 verification~~ — **done** (Fable 5, 2026-08-30, verdict *not ready*, fourteen
   findings) **and acted on** (the closeout run, handoff entries M5C-1…M5C-15, all closed). The
   re-verification prompt is `~/ai/suite/m5-reverification.prompt.md`; it must still be able to
   say *not ready*.
3. **Tag and publish `loadcoach 1.0.0`** (Packaging Standards §6 from step 6), verify
   `pip install loadcoach==1.0.0` in a clean virtualenv, then declare M5. IdeaPress may begin its
   LoadCoach integration phase. The tag remains the one human step (`TAG_APPROVED` was `no` at
   the closeout).
4. **Begin M6 or M7.** FreeWeight P12–P14 (M6: adoption of the shared packages, external adapters,
   hardening) and IdeaPress P1–P6 (M7: a complete project with only Ollama present) are both
   unblocked; §3's work streams say what may overlap. IdeaPress P1 needs nothing from LoadCoach
   until P7.

An implementation agent assigned any phase should read, in this order: the master requirements, the
[Master Architecture](../architecture/master-architecture.md), the relevant component
[specification](../README.md), that phase in the component's development plan, and the standards it
touches. It should not need to invent an architectural decision; if it does, that gap is a defect in
this documentation set and should be closed with an ADR before the code is written. The
[final architecture audit](../reviews/final_architecture_audit.md) is still worth reading before a
first phase: it added ADR-0022 – ADR-0029 and corrected the specifications they touch. The M4 and
M5 handoff sections in `~/ai/suite/M4_HANDOFF.md` are where the decisions the documents left open
were made, and the verification prompts are how each milestone is checked before it is declared.
