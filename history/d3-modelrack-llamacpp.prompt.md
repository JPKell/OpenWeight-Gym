# Kickoff — D3: ModelRack Phase 6, `LlamaCppProvider` and process supervision

**Row:** D3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1, and the
start of **LA1** in the [adapter arc](docs/roadmap/adapter-roadmap.md).
**Model:** **Fable 5 · xhigh**, as scheduled.
**Repository:** `/home/jpk/ai/suite/py/ModelRack` — clean at `94bf5ce`, **3 commits unpushed**
(row C5). Python **3.13.15**, coverage floor **95 %**.
**Runs after:** A1 and C5, both **done**. `C5 before D3` is a hard edge
([§3](docs/roadmap/outstanding-work.md)): the usage rule lands before the third adapter is written,
because a retrofit is a fixture re-annotation nobody wants.
**Ships:** nothing. This rides `modelrack 0.7.0`, published at row **H1** after P7–P8. Do not bump
the version, do not tag, do not publish, **do not push**.

> ## ⛔ Never overnight
>
> [model-assignment §2.12](docs/roadmap/model-assignment.md) names batch D explicitly: *"never
> schedule a Fable/security row overnight — those phases are won by review, and their failures are
> silent."* [outstanding-work §4](docs/roadmap/outstanding-work.md) requires the diff to be reviewed
> **same-day**. Run this attended, in daylight.

**Why xhigh.** The schedule's own words: *"concurrency with orphan/leak guarantees, no useful
feedback loop, in a package three apps call — the §3.3 class."* An orphaned `llama-server` holding
16 GB of VRAM does not fail a test; it fails the *next* session, on a machine nobody is watching.
And ModelRack is called by FreeWeight, LoadCoach and IdeaPress, so a defect here has three blast
radii.

**This row is independent of D1 and D2**, and it is the **flexible** one:
[§3](docs/roadmap/outstanding-work.md) marks D3/F3/H1 as *"the ModelRack stream can slot anywhere
after C5, whenever harness work blocks."* If a day is short, this is the row to move.

**One resource rule** ([§3](docs/roadmap/outstanding-work.md)): LA1/LA2 GPU sessions never share the
machine with a FreeWeight benchmark run. Check before any GPU work.

---

## Preconditions

* **C5 built the seam you bind to, and wrote you the brief.** `docs/history/C5_HANDOFF.md` **§5 — "the
  conformance seam, written for D3"** — is the document to read first. You add `LlamaCppProvider`
  to ADR-0070's three usage cases by writing **one `usage_shapes` fixture**, declaring which
  recorded response produces which shape, and changing **none** of the behaviours. That is the whole
  reason C5 ran before D3.
* **`llama-server` is not installed on this machine** — see the next section. This is a design
  constraint, not just an inconvenience.
* **The `Provider` protocol does not change.**
  [ADR-0062](docs/adr/0062-llamacpp-serves-adapters-through-a-supervised-process.md) decision 1 is
  explicit that `load`/`unload`/`list_resident` already have exactly the right shape, and *"that is
  the evidence the seam was drawn in the right place."* A protocol change is a **major** bump
  (spec §19) and this is a minor. No new dependency either.
* **`git status --short` must be empty before you start.**
* **You are not authorised to push, tag or publish.** Commit on `main` and stop.

## The machine, verified 2026-09-03

```text
llama-server / llama-cli / any llama.cpp build   ABSENT
/home/jpk/ai/models/llm/*.gguf                   5 files, 5.6–9.7 GB each (~40 GB total)
GPU                                              NVIDIA GeForce RTX 5060 Ti, 16 GB
```

**No `llama-server`.** Three consequences, and the second is the one that shapes the row:

1. The default suite must pass without it — the same rule ModelRack already holds for Ollama
   (spec §20 criterion 3). Every P6 test runs against recorded fixtures and a fake process.
2. **Design the spawn seam injectable from the first commit.** Process supervision that can only be
   exercised by launching a real binary is untestable here *and* in CI — and **P8's leak tests (20
   load/unload cycles, no orphan, flat memory) inherit the same constraint.** Inject the launcher
   the way this package already injects `httpx.Client`, clocks and telemetry readers. Retrofitting
   this at P8 is the expensive version of the same work.
3. A live journey against a real `llama-server` is **`live`-marked and cannot run here.** It is an
   operator step and it sits on LA1's critical path — the LA1 exit demo needs one base, three
   registered adapters and 20 generations with **zero base loads**, asserted from the process table
   and load timings. Say so in the handoff.

**Five real GGUF files are on disk**, so discovery, header parsing and hashing can be exercised
against real artifacts rather than synthesized ones. **The trap:**
[`adapter-identity-and-serving.md` §2](docs/architecture/adapter-identity-and-serving.md) defines
`artifact_digest` as the sha256 of the **served GGUF artifact** — content-addressed, so a rename
changes nothing, and *"identity is the hash, the path is a locator."* That is a full-content hash of
every file. Hashing ~40 GB on every discovery call is minutes of I/O per call. **Decide deliberately
how a digest is cached and invalidated** — `src/modelrack/cache.py` already has a TTL and an
explicit `refresh=True` path, and that is the precedent. **Do not** quietly substitute a
header-only or size+mtime digest for the content digest the identity contract names; if you think
the contract is wrong, that is a finding for the handoff, not a change to make in passing.

The venv is ordinary: only `modelrack` itself is editable, `baseaicore 0.4.0` comes from PyPI.
`pip install -e ".[dev]"` is safe here. **Note that this venv is also what FreeWeight and LoadCoach
resolve `modelrack` through** — both have it installed editable against this working tree — so a
change here is live in their suites immediately (recorded in `docs/history/C5_HANDOFF.md` §7).

## Setup

```bash
cd /home/jpk/ai/suite/py/ModelRack
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be empty before you start
```

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository.
* **Read before writing**, in this order:
  [`architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, then the
  ModelRack section of [`standards/gold-standards.md`](docs/standards/gold-standards.md) §2
  (lines 74–84), then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations`; units in every numeric name (`duration_ms`, `vram_used_bytes`); keyword-only for
  anything optional; injected clocks, launchers and HTTP clients; `mypy --strict`; line length 100.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **95 %**, `CHANGELOG.md` updated
  under `## [Unreleased]`, one Conventional Commit per logical group. **Name the interpreter and the
  exact invocation in the handoff** (M5C-13) — this venv is Python 3.13.15; confirm rather than
  copy. There is no `python3.12` on this machine.
* **Documentation is mirrored.** Anything amended under `/home/jpk/ai/suite/docs/` is edited in the
  workspace copy **first**, then re-copied into `py/ModelRack/docs/` and verified with `cmp`. Do not
  reflow markdown you edit. **This row is expected to amend one document — see below.**

## Reading list

1. [`roadmap/adapter-roadmap.md`](docs/roadmap/adapter-roadmap.md) **§4.1, the P6 bullet** — the
   work and its three named risks: orphaned processes, port management, startup-failure diagnosis.
   Read the P7 and P8 bullets too, so P6 does not foreclose them.
2. [`architecture/adapter-identity-and-serving.md`](docs/architecture/adapter-identity-and-serving.md)
   **§§4–6** — the registry (a directory and a manifest), serving through a process-supervising
   provider, and evidence measured rather than inherited. **§2** for what `artifact_digest` means.
3. [ADR-0062](docs/adr/0062-llamacpp-serves-adapters-through-a-supervised-process.md) (this is A-5)
   — all six decisions. **Decisions 2–5 are P7's, not yours**; read them so this row leaves room.
   Decision 6 names what the suite deliberately takes over, including hashing and process lifecycle.
4. [ADR-0070](docs/adr/0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
   — **decision 4 is yours**: llama.cpp is written to the rule from the start, its docstring stating
   which classes its native API can bill and what it does with each. Decisions 1–3 are the pattern
   the two existing adapters already follow.
5. [`packages/modelrack/spec.md`](docs/packages/modelrack/spec.md) — the `Provider` protocol in §7,
   **§11 contract 2 as amended by C5**, §13's error table, §18's conformance row, and §19 on
   recorded fixtures recording the provider version they came from.
6. **`docs/history/C5_HANDOFF.md` §§2, 5 and 6** — the usage rule as implemented per adapter, **the seam**, and
   how the fixture manifests record a re-annotation rather than a re-capture.
7. The code, in this order: `src/modelrack/providers/ollama.py` (the closest precedent for a
   provider with residency control); `src/modelrack/providers/_ollama_wire.py`'s `read_usage`;
   `tests/contract/test_conformance.py`'s `UsageShapes` / `CacheDetailShape` / `usage_shapes`
   fixtures; `src/modelrack/cache.py`.

## The work

§4.1's P6 bullet is the plan. Four things to decide deliberately and record:

1. **The spawn seam, injected** — see the machine section. This must be right in the first commit
   rather than retrofitted at P8, and it is the difference between a testable row and an untestable
   one.
2. **What a digest costs** — see the machine section. Cache it using `cache.py`'s precedent; do not
   substitute a cheaper digest for the one the identity contract names.
3. **Usage to ADR-0070 from the start.** A class llama.cpp's native API **cannot bill** is `0`; a
   class it **can** express but this response did not carry stays `UNSUPPORTED`; a response with no
   usage object at all is `UNSUPPORTED` throughout. Declare the three shapes through C5's
   `usage_shapes` fixture, and set `cache_detail=None` **only if** the native API genuinely cannot
   report cached input — C5's seam documents that as a *declaration, not an exemption*, and an
   adapter that could report it but declared `None` would exempt itself from the one case that
   catches double-billed cached input.
4. **Recorded fixtures, version-annotated** (spec §19), naming the llama.cpp build they represent.
   Follow the manifest convention C5 re-annotated: say plainly what is a capture and what is a
   representative payload. Since there is no llama.cpp on this machine, these are **representative**
   — say so, the way `openai_compatible/manifest.json` already does.

## A docs gap this row should close

[`packages/modelrack/development-plan.md`](docs/packages/modelrack/development-plan.md) has **five
phases**, and Phase 5's entry ends *"Deferred: llama.cpp and vLLM adapters, embeddings, async API,
tokenization, multi-modal input."* **There is no Phase 6 section.** Unlike D1 and D2, whose plans
live in their components' development plans, this row's plan exists only in `adapter-roadmap.md`
§4.1. Per `CLAUDE.md`, a plan that does not exist where a reader will look for it is a defect in the
docs, to be closed rather than worked around.

**Add a Phase 6 section** in the established shape — Goal, Prerequisites, Work, Files/subsystems,
Tests, Acceptance criteria, Known risks, Likely failure modes, Gold standards, Deferred —
transcribed from §4.1 rather than invented, and amend Phase 5's "Deferred" line so it no longer
defers what the next phase does. Workspace `docs/` first, then mirror into `py/ModelRack/docs/` and
verify with `cmp`. If you disagree that this belongs in this row, say so in the handoff and leave
it — but do not leave it undiscussed.

## Before you finish — closing duties

1. **Write `docs/history/D3_HANDOFF.md` at the workspace root.** Sections: gate results with the interpreter and
   exact commands; the adapter as built, per §4.1's bullet; **the spawn seam, written for P7 and P8
   the way C5 §5 was written for you**; the digest-caching decision and why; the usage shapes
   declared and whether `cache_detail` is `None`; the fixtures added and what each proves; **what
   could not be verified without `llama-server`**, listed as operator steps; the commits; and
   **"Before the next session"** — at minimum: push `main` (this carries C5's three commits too),
   confirm CI green, install llama.cpp before the LA1 exit demo, and the reminder that this rides
   `0.7.0` at H1 rather than publishing now.
   **Never overwrite an existing root file** — the workspace root is not a git repository. If
   `docs/history/D3_HANDOFF.md` exists, write `D3_HANDOFF.2.md` and say why.
2. **Summarise in chat**: what was built, what the gate said with the interpreter named, what you
   decided at each edge, and what is waiting on the operator.
3. **Everything committed on `main`, working tree clean, nothing pushed, nothing tagged.**

## Constraints and stop rules

* **No version bump, no tag, no publish, no push.** This rides `0.7.0` at H1, after P7 and P8.
* **No `Provider` protocol change** (major bump, spec §19) and **no new dependency**.
* **Do not implement P7.** Adapter registration from manifests, per-request `lora` selection,
  `adapter_hot_swap`, `AdapterNotFound`, digest-verified compatibility, `pending_restart`, and the
  cache-correctness conformance test are all P7's. P6 is **process supervision and basic serving**.
  A thing you notice P7 will need is a finding for the handoff.
* **Never leave an orphaned process reachable from any code path.** Kill-tree on timeout, pid files,
  a configured port range — the three risks §4.1 names, each with its mitigation.
* **Never let a startup failure surface as anything but a typed error** carrying the captured
  stderr. "It did not start" with no diagnosis is the failure mode §4.1 names third.
* **The default suite must pass with no llama.cpp installed.** A `live`-marked test is fine; a
  default-suite test that needs a binary is not.
* **Never fabricate a zero.** ADR-0070 licenses `0` only where the protocol cannot bill the class.
  If you find yourself writing `0` for a class the native API *can* express and this response did
  not report, stop.
* **Never weaken `.importlinter`** to make an import work.
* **Working-tree integrity** (`CLAUDE.md`): `git status --short` at the start and end; commit per
  logical group; never `git add -A`.
* **A silent failure is this row's failure mode.** Where a guarantee cannot be proven on this
  machine, say so plainly in the handoff and make it an operator step. Do not let an unrunnable test
  read as a passing one.
* If you must stop early, stop at a green gate with a commit and a clean tree, and record exactly
  where you stopped in `docs/history/D3_HANDOFF.md`.
