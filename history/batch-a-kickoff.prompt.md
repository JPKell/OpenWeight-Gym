# Kickoff — Batch A: Phase 0 / LA0 contracts, then BaseAiCore 0.4.1

**Rows:** A1 (Opus 5 · xhigh) and A2 (Opus 5 · high) of
[`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Shape:** two parts with a hard stop between them. A1 is documentation-only in the `docs`
repository; A2 is code in `py/BaseAiCore` and depends on A1's ADRs being accepted. Run straight
through in one sitting, or cut the session at the checkpoint — but **do not begin A2 before A1's
report has been read by a human**, because A2 implements what A1 decides.
**Overnight:** both rows are Opus and may run unattended
([model-assignment §2.12](docs/roadmap/model-assignment.md)). Neither is on the never-overnight
list.

---

## Standing preamble (applies to both parts)

* **Work from inside a component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace; each component is an independent git repository. Part A1 works in
  `/home/jpk/ai/suite/docs`; part A2 works in `/home/jpk/ai/suite/py/BaseAiCore`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  component's section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2,
  then the part's own reading list below.
* **House method:** docstring-first (define behaviour → Google-style docstring including what the
  function *refuses* → tests → implementation), `from __future__ import annotations` in every
  module, units in every numeric name, keyword-only for anything optional or boolean, injected
  clocks/providers/roots, `@dataclass(frozen=True, slots=True)` for value objects, line length 100,
  `mypy --strict` with no bare `Any` at a public boundary and no `# type: ignore` without a trailing
  reason.
* **Finish line for any code part:** `ruff format --check . && ruff check . && mypy src tests &&
  lint-imports && pytest -m "not live and not performance"` all green, `CHANGELOG.md` updated,
  one Conventional Commit per phase. **Name the interpreter and the exact invocation in the report**
  (M5C-13) — for example `py/BaseAiCore/.venv/bin/python`, Python 3.13.15.
* **Dependency pinning:** the outstanding-work preamble's rule about pinning unpublished suite deps
  as local editable installs **does not apply to either part**. `baseaicore` imports the standard
  library only; adding any dependency to it would be an architecture violation, not a pinning
  question.
* **Documentation is mirrored.** Edit the workspace copy under `/home/jpk/ai/suite/docs/` first,
  then copy byte-identically into the component repo's own `docs/`. Verify with `cmp`, never by eye.
* **You are not authorised to tag or publish.** Tagging and the release workflow's `pypi`
  environment approval are the human's, per run. Prepare the release and say so; do not create the
  tag.

---

# Part A1 — Phase 0 / LA0: write the contracts

## What this is

Two post-1.0 arcs were designed on 2026-09-01/02 and their decisions are fully argued in the
roadmaps: the **PromptCadence arc** (a plan-approved, tier-routed agent harness over LoadCoach plus
four new shared packages) and the **Adapter arc** (hot-swappable LoRA serving on a warm base via
llama.cpp). The suite's standing rule is that a missing architectural decision is a defect in the
documentation, closed with an ADR **before** any code is written. This phase writes those ADRs and
amends the frozen architecture documents to match. **No code is written in this part, and no
repositories are created.**

**Every decision here is already made.** The D-ids and A-ids below are stated unambiguously in the
roadmaps, with their alternatives and revisit triggers. Your job is expansion into the house ADR
form, not re-litigation. If, while writing, you find a decision that is genuinely underdetermined —
a case the roadmaps do not cover — **do not invent a resolution silently**: write it into the
report's "gaps found" section, and if it must be decided to make the ADR coherent, say so
explicitly and mark that ADR `Proposed` rather than `Accepted`.

## Reading list

1. [`docs/roadmap/promptcadence-roadmap.md`](docs/roadmap/promptcadence-roadmap.md) — §2 (the
   D-1…D-13 decision table) and §7 (the Phase 0 documentation checklist). Read §1 and §5 for
   context.
2. [`docs/roadmap/adapter-roadmap.md`](docs/roadmap/adapter-roadmap.md) — §2 (the A-1…A-10 decision
   table) and §9 (the LA0 documentation checklist). Read §1 and §5 for context.
3. [`docs/architecture/adapter-identity-and-serving.md`](docs/architecture/adapter-identity-and-serving.md)
   — the full cross-cutting design the A-ids come from.
4. [`docs/adr/README.md`](docs/adr/README.md) — the **Format** section is normative: Status,
   Context, Decision, Alternatives considered, Consequences, Revisit when, in that order. "A
   decision without a *revisit when* trigger is a decision nobody can safely revisit."
5. [`docs/adr/0038-one-model-at-a-time-per-gpu.md`](docs/adr/0038-one-model-at-a-time-per-gpu.md) —
   **the amendment precedent.** The master architecture is frozen; it is amended *through* ADRs
   that declare what they extend in a header block. Copy that mechanism.
6. The specs the ADRs govern, as needed:
   [`docs/apps/promptcadence/spec.md`](docs/apps/promptcadence/spec.md) and
   [`lifecycle.md`](docs/apps/promptcadence/lifecycle.md), and
   [`docs/packages/{cutctx,toolyard,loadledger,spotcheck}/spec.md`](docs/packages/).

## The work

### 1. Write 23 ADRs, numbered deterministically

The last accepted ADR is 0044. Use exactly this mapping so that part A2 and every later phase can
reference numbers that already exist:

| Roadmap id | ADR | Roadmap id | ADR |
|---|---|---|---|
| D-1 | 0045 | D-13 | 0057 |
| D-2 | 0046 | A-1 | 0058 |
| D-3 | 0047 | A-2 | 0059 |
| D-4 | 0048 | A-3 | 0060 |
| D-5 | 0049 | A-4 | 0061 |
| D-6 | 0050 | A-5 | 0062 |
| D-7 | 0051 | A-6 | 0063 |
| D-8 | 0052 | A-7 | 0064 |
| D-9 | 0053 | A-8 | 0065 |
| D-10 | 0054 | A-9 | 0066 |
| D-11 | 0055 | A-10 | 0067 |
| D-12 | 0056 | | |

**Write them in this order** (the numbering above is fixed regardless of authorship order, so
order of writing costs nothing): first the six load-bearing records, while your context is
freshest and closest to the source — **0046 (D-2), 0058 (A-1), 0056 (D-12), 0050 (D-6),
0053 (D-9), 0064 (A-7)** — then everything else in numeric order. Those six are the ones later
phases lean on hardest: two of them are what part A2 implements, D-12 is the design's load-bearing
wall, D-6 is a pattern two packages copy, D-9 is a security ordering, and A-7 is the decision that
overturned a proposal on the merits and therefore has the most argument to lose.

**Before writing each ADR, re-open its row in the roadmap decision table and read it again.** Not
once at the start for all 23 — immediately before each one. This is the single most effective guard
against the failure mode described at the end of this prompt: by ADR fifteen, the nearest thing in
your context is fourteen ADRs you wrote yourself, and pattern-matching to those instead of to the
source is how the arguments flatten. Extract the alternative and the revisit trigger from the
roadmap row *before* composing any prose.

Requirements for each:

* **Filename** `NNNN-kebab-title.md`; **title** a declarative sentence stating the decision, in the
  house voice — compare "A state change and the event announcing it are one write", "Caller schemas
  do not travel through a router". Not a topic label.
* **Status:** `Accepted (2026-09-02)` unless you are flagging a genuine gap (see above).
* **Alternatives considered must be real.** The roadmaps name most of them (vLLM for A-5, free-form
  tags for A-7, a manifest service for A-4, ThreadRack as a package for D-1, a money-only ceiling
  for the budget decisions). Where a roadmap names an alternative and why it lost, carry the
  argument across; do not weaken it into a formality.
* **Revisit when:** the roadmap tables already supply one per decision. Use it.
* **Amendment headers** where a decision extends an existing record: A-1 amends
  [ADR-0008](docs/adr/0008-canonical-model-identity.md),
  [ADR-0023](docs/adr/0023-runtime-profile-resolution.md) and
  [ADR-0024](docs/adr/0024-canonical-id-and-model-references.md) **additively, reversing none**;
  A-2 extends the ADR-0016/0037/0043 family; D-9 reuses ADR-0018's tier ladder and ADR-0026's fetch
  rules; D-6's mounting pattern relates to ADR-0006; D-7 uses ADR-0035's namespace; A-9/A-10 touch
  ADR-0038's residency reasoning; the PromptCadence adapter position rests on ADR-0040.
* **Naming:** the compaction package is **CutCtx** (import name `cutctx`) — it was renamed from
  "ContextPress" on 2026-09-02. No ADR may contain the old name.

### 2. Amend the master architecture

Both checklists, applied to
[`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) via the
ADR-0038 mechanism:

From **promptcadence-roadmap §7**: §1.1 component table (+ PromptCadence, port 8768; + the four
packages), §1.5 task-profiles note, §2 dependency graph and rules (new packages under rule 3; the
SpotCheck→SetSpec edge), §3 ownership rows, §8 deployment note for PromptCadence, §11 forbidden
list (+ "a package owning an application's migration history", + "direct provider access from
PromptCadence").

From **adapter-roadmap §9**: §1.3 domain terms (+ adapter identity, + adapter manifest), §10
extension points (+ a `LlamaCppProvider` row), §11 forbidden list (+ "an adapter applied without
digest-verified base compatibility", + "adapter evidence inherited from a base").

### 3. The remaining documentation updates

* [`docs/adr/README.md`](docs/adr/README.md) — 23 new index rows, 0045–0067, in the existing table
  format.
* [`docs/README.md`](docs/README.md) — component rows for PromptCadence and the four packages, and
  the reading order; link
  [`architecture/adapter-identity-and-serving.md`](docs/architecture/adapter-identity-and-serving.md)
  from the architecture index.
* [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2 — sections for
  PromptCadence and for each of CutCtx, ToolYard, LoadLedger, SpotCheck.
* [`docs/architecture/traceability-matrix.md`](docs/architecture/traceability-matrix.md) and
  [`docs/architecture/risk-register.md`](docs/architecture/risk-register.md) — the arcs'
  requirements and the top risks named in promptcadence-roadmap §10 and adapter-roadmap §8.
* [`docs/roadmap/master-roadmap.md`](docs/roadmap/master-roadmap.md) §1/§9 — a pointer row
  delegating M10–M13 to the arc roadmaps **and a correction**: §9's "current state" is frozen at
  end-of-M7 and is now wrong. All nine components are tagged and published (FreeWeight, LoadCoach,
  IdeaPress at 1.0.0; modelrack 0.6.0; weightsdb and mirrorwall 0.2.1; baseaicore 0.4.0; setspec
  0.4.0; sweatmeter 0.4.0). Correct it to the true state; leave the M9 delivery checklist in §7
  intact — it is still outstanding work.
* [`harness.md`](harness.md) (workspace root) — retire it with a pointer to
  `docs/apps/promptcadence/` and the roadmap. It is the superseded skeleton this arc expanded;
  keeping two versions of the design invites drift.

### 4. Commit

In the `docs` repository, Conventional Commits, grouped logically (for example: one commit for the
D-series ADRs, one for the A-series, one for the architecture amendments, one for the index and
standards updates). Note that `docs/roadmap/model-assignment.md`,
`docs/roadmap/outstanding-work.md` and the CutCtx rename may already be uncommitted in the working
tree — check `git status` first and commit them separately with their own message rather than
sweeping them into an ADR commit.

## A1 report, then continue

Write the A1 report into `A1_REPORT.md` at the workspace root **and** summarise it in your reply:

1. A table of ADR number → title → status, with **two extra columns**: `confidence`
   (`solid` / `thin`) and `note`. Mark an ADR `thin` when you could not find a genuinely
   arguable losing alternative, when the roadmap row underdetermined something you had to settle,
   or when you wrote it after a compaction and could not fully reconstruct the source argument.
   Flag anything left `Proposed` and why.
2. Every file amended, with a one-line summary of the amendment.
3. **Gaps found** — any decision the roadmaps did not determine, any contradiction between two
   documents, anything you had to leave open. This section being empty is a valid outcome; padding
   it is not.
4. **The compaction seam** — if your context was compacted, which ADR you were writing when it
   happened, and how many ADRs were written after it.
5. Any ADR you strengthened on the every-fifth self-check, and what was weak about it.
6. The commits made.

**This report is read by a review pass in the morning** (Fable 5, `docs/history/a1-review.prompt.md`) that
triages all 23 ADRs against the roadmap decision tables. It cannot re-derive what only you know:
where the seam fell, which rows fought you, which alternatives you could not make arguable. An
honest `thin` costs you nothing and saves that pass an hour of hunting — **an inflated `solid` is
the one thing here that actually does damage**, because it steers attention away from the record
that needed it. Marking a row `thin` is not a licence to write it thin: write every ADR as well as
you can, then report accurately on how it went.

**Then continue directly into A2.** This batch runs unattended overnight, so the human acceptance
of the ADRs happens in the morning, over the committed diff, not between the two parts. Two
consequences you must respect:

* If A1 produced a `Proposed` ADR for **D-2 or A-1 specifically** — the two A2 implements — then
  **stop before A2** and say so. Those two must be settled for A2 to mean anything. A `Proposed`
  ADR anywhere else does not block A2.
* Treat the ADRs you wrote as accepted for A2's purposes, and note in the A2 report that the
  implementation rests on decisions not yet human-reviewed.

---

# Part A2 — BaseAiCore 0.4.1

## What this is

The smallest possible additive release of the suite's domain foundation: one new enum and one new
value object, both frozen by golden tests that three databases will depend on. `baseaicore` is the
root of the dependency graph and imports the standard library only. Every existing consumer pins
`>=0.4,<0.5`, so **0.4.1 must land inside that range**: additive only, no signature changes, no
golden edited to match new behaviour.

The BaseAiCore rule from [model-assignment §3.3](docs/roadmap/model-assignment.md): wrong here is a
data-compatibility break in every repository in the suite. This phase is small precisely so that
care is affordable.

## Setup

```bash
cd /home/jpk/ai/suite/py/BaseAiCore
source .venv/bin/activate          # Python 3.13.15; recreate with python -m venv .venv if absent
pip install -e ".[dev]"
```

## Reading list

1. The **accepted ADR-0046 (D-2)** and **ADR-0058 (A-1)** from part A1 — the contracts you are
   implementing.
2. [`docs/packages/baseaicore/spec.md`](docs/packages/baseaicore/spec.md) — especially the value
   object conventions (`frozen=True, slots=True`, lazily cached hashes) and the golden-test
   discipline: the canonical-ID golden "is the one that must never be 'updated to match'".
3. [`docs/architecture/adapter-identity-and-serving.md`](docs/architecture/adapter-identity-and-serving.md)
   §§2–3 — the adapter axis and the selection-vs-serving-mode split.
4. [`docs/packages/baseaicore/development-plan.md`](docs/packages/baseaicore/development-plan.md) —
   the existing P1–P4 phases, for the shape a new phase section should take.
5. The existing `src/baseaicore/identity.py` and `src/baseaicore/subject.py` — `ModelIdentity`,
   `IdentityConfidence` and `normalize_digest` are what you are extending.

## The work

### 1. `DataClassification` (ADR-0046 / D-2)

An ordered three-level enum — `PUBLIC < INTERNAL < CONFIDENTIAL` — that is caller-declared and
**defaults to the most restrictive level**. The ordering *is* the contract (a later addition of a
level is a new ADR precisely because of it), so ordering comparisons must be part of the public
surface and golden-tested. The lattice operation consumers need is `max(caller, adapter)`; make it
expressible without importing anything.

### 2. `AdapterIdentity` and the canonical suffix (ADR-0058 / A-1)

* `AdapterIdentity(name, artifact_digest, source_digest=None)` — `name` is the manifest's human
  label, `artifact_digest` is the sha256 of the **served GGUF artifact** (content-addressed, so
  renaming the file changes nothing), `source_digest` is optional lineage to the training
  checkpoint. Reuse `normalize_digest`.
* **The canonical string form gains an optional suffix**, amending ADR-0024 additively:
  `llamacpp/qwen3.5-9b-q8@sha256:1f3a9c4e2b70+factcheck@sha256:9e2b41d07c55`. An absent adapter must
  produce a string **byte-for-byte identical to today's**. The `+` is percent-encoded where the
  canonical id appears in a URL path segment.
* **Base compatibility is verified by digest, fail closed.** A name-only match is accepted only with
  visibly reduced identity confidence — reuse the existing `IdentityConfidence`/`name_only`
  machinery rather than inventing a parallel one.
* Comparability, restated in the docstrings: evidence measured on `(base, adapterA)` applies to
  `(base, adapterA)` and to nothing else — not to the bare base, not to `(base, adapterB)`.

### 3. Goldens

The additive proof is the important one: **every existing golden must pass unchanged**, and a new
golden must show a bare (adapter-free) subject serialising byte-identically to the current output.
Then add adapter-bearing forms, the percent-encoded URL form, the ordering of every
`DataClassification` pair, and the refusal cases (mismatched base digest, malformed suffix).
Exports go in `__init__.py` and `__all__`.

### 4. Documentation, in the right order

1. Update the **workspace** copies first:
   `/home/jpk/ai/suite/docs/packages/baseaicore/spec.md` and `development-plan.md` (a new phase
   section for this release, with demonstrable acceptance criteria — the house rule is that every
   phase states what to run and what a person should see).
2. Copy byte-identically into `py/BaseAiCore/docs/packages/baseaicore/` and **verify with `cmp`**.
   Those two files are the only mirrored documents in this repo; `README.md`, `quickstart.md` and
   `api.md` are repo-local.
3. Regenerate the API reference: `python scripts/generate_api_reference.py` (writes `docs/api.md`).
   It is not CI-enforced yet, so it will drift silently if you skip it.

### 5. CHANGELOG and version

`CHANGELOG.md` already has an `## [Unreleased]` section carrying real work done since `v0.4.0` —
the `requirements/*.lock` files, the CI changes that install from them, and a `pytest` security
range bump. **0.4.1 ships those too.** Promote the existing entries into the `0.4.1` section
alongside your own additions rather than releasing your changes over the top of them, and leave a
fresh empty `[Unreleased]` above. Version is `dynamic` via hatch — set it where
`src/baseaicore/__about__.py` holds it.

### 6. Gate and commit

The full gate from the standing preamble, green, with the interpreter named. One Conventional
Commit for the release.

## A2 report

1. Gate results, with the exact command and interpreter (`py/BaseAiCore/.venv/bin/python`, version).
2. The public surface added, and the proof it is additive: existing goldens untouched, bare-subject
   canonical form byte-identical.
3. `cmp` output for both mirrored documents.
4. What remains for the human: **tag `v0.4.1`** and approve the release workflow's `pypi`
   environment; then `pip install baseaicore==0.4.1` in a clean venv as the post-publish check.
   Do not perform these.

---

## Constraints for the whole batch

* **No code in A1. No repository creation in either part** — the five new repos are a human step
  in [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §4.
* **Never weaken `.importlinter`** to make an import work, and never add a dependency to
  `baseaicore`.
* **ADRs are superseded, never edited.** If you disagree with an accepted decision, say so in the
  report; do not quietly write something else.
* If the work must stop early, stop at a green gate with a commit and say exactly where you stopped
  and what remains.

## Running unattended: commit as you go

This batch runs overnight with nobody watching, and it is long enough that your context will
probably be compacted at least once. Durability matters more than tidiness:

* **Commit in groups, as each group finishes** — not once at the end. The order:
  (1) any pre-existing uncommitted work, on its own; (2) the D-series ADRs 0045–0057;
  (3) the A-series ADRs 0058–0067; (4) the master-architecture amendments; (5) the index,
  standards, matrix, risk-register and roadmap updates plus `harness.md`'s retirement;
  (6) `A1_REPORT.md`; then A2's release commit. A session that dies at 4 a.m. must leave committed
  work behind it, never a dirty tree.
* **Keep a running note** in `A1_REPORT.md` as you go — append each ADR to its table the moment you
  write it, rather than reconstructing the table at the end. If your context is compacted, that
  file plus `git log` is how you recover your place. Re-read the numbering table in this prompt
  after any compaction; the mapping is fixed and must not drift.
* **Do not stop the run to ask a question.** Where this prompt gives you latitude, take the
  conservative option, record the choice in the report's gaps section, and keep going. The only
  authorised early stops are: a `Proposed` D-2 or A-1 (above), or an A2 gate you cannot get green —
  in which case commit the green subset, leave the tree clean, and report precisely what fails.
* **Quality warning specific to this batch.** Twenty-three ADRs is a lot of expansion of settled
  judgment, and the failure mode is not crashing — it is blandness: "Alternatives considered"
  sections that degrade into formalities as the session wears on. The later ADRs are the ones at
  risk. If you notice yourself writing an alternative you cannot argue against, go back to the
  roadmap row and find the real one.
* **A compaction is a warning, not a reset.** If your context is compacted mid-run, what survives
  is your own summary of the roadmaps, not the roadmaps. Every ADR written after that point is at
  the highest risk of restating your earlier prose instead of the source argument. So after any
  compaction: re-read this prompt's numbering table, re-open the relevant roadmap decision table
  from disk, and note in `A1_REPORT.md` which ADR you were on when it happened — the morning review
  needs to know where the seam is.
* **Self-check every fifth ADR.** Stop and ask of the one you just wrote: could a reader who
  disagrees with this decision tell, from the Alternatives section alone, that the losing option
  was genuinely considered? If not, fix it before continuing. Record any ADR you strengthened on
  this check in the report.
