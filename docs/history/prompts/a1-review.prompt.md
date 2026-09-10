# Morning review — Batch A1's 23 ADRs

**Model:** Fable 5 · xhigh. **When:** after the overnight batch-A run, before any Batch B/C phase
starts. **Shape:** a triage pass, not a rewrite. Input-heavy, output-light — read everything,
report a short ranked list.

## Why this pass exists

Twenty-three ADRs (0045–0067) were written unattended in one session from the decision tables in
`docs/roadmap/promptcadence-roadmap.md` §2 and `docs/roadmap/adapter-roadmap.md` §2. They are
permanent contracts that gate roughly twenty-six downstream phases, and **nothing tests them**.
The expected failure mode is not a wrong decision — the decisions were settled before the session
started — but a degraded *record*: alternatives that flattened into formalities as the session
wore on, a Decision that drifted a shade from its roadmap row, two ADRs that contradict each other
at their seam. Every one of those survives a green gate and shows up months later as "why did we
reject vLLM?" with no usable answer.

This is the review that failure mode is caught by. It is [model-assignment
§3.2](docs/roadmap/model-assignment.md)'s "implement cheap, review expensive" applied literally.

## Read

1. `A1_REPORT.md` at the workspace root — the session's own account. It carries three things that
   direct this pass: a per-ADR `confidence` column (`solid` / `thin`), **where its context was
   compacted**, and which ADRs it strengthened on its own self-checks. Start with every `thin` row
   and everything written after the seam; those are the highest-risk group. Then sample the
   `solid` ones — the session graded its own work, and an inflated `solid` is exactly the finding
   this pass exists to catch, so do not treat that column as a filter you can trust completely.
2. All of `docs/adr/0045-*.md` … `docs/adr/0067-*.md`.
3. The two source decision tables: `docs/roadmap/promptcadence-roadmap.md` §2 (D-1…D-13) and
   `docs/roadmap/adapter-roadmap.md` §2 (A-1…A-10). These are the ground truth each ADR expands.
4. `docs/adr/README.md` — the Format section, and the index rows added for 0045–0067.
5. `git log` and the diff on `docs/architecture/master-architecture.md`.

## The four checks

1. **Decision drift.** For each ADR, does its *Decision* section say what its roadmap row says —
   no more, no less? An ADR that quietly widens or narrows its scope is the most expensive defect
   here, because downstream phases implement the ADR, not the roadmap.
2. **Contradiction between ADRs.** Particularly at the seams the design leans on: D-4 (bypass
   removes planning, never governance) against D-12 (every turn runs under an ExecutionIntent);
   D-6's mountable-persistence rule against D-10's SpotCheck scope; A-1's identity axis against
   A-3's selection-versus-serving-mode split; A-7 (capability vocabulary) against A-2 (evidence
   measured, never inherited).
3. **Formality alternatives.** Could a reader who disagrees with the decision tell, from the
   Alternatives section alone, that the losing option was genuinely weighed? Name the ADRs where
   the answer is no. The roadmaps name most of the real alternatives — vLLM for A-5, free-form tags
   for A-7, a manifest service for A-4, ThreadRack-as-a-package for D-1, a money-only ceiling for
   the budget decisions — so a formality here is usually a *retrievable* one.
4. **Format and amendment correctness.** Every ADR has all six sections in order and a concrete
   *Revisit when*. The amendment headers are right: A-1 amends ADR-0008/0023/0024 **additively,
   reversing none**; A-2 extends the ADR-0016/0037/0043 family; D-9 reuses ADR-0018's tier ladder
   and ADR-0026's fetch rules. And the `master-architecture.md` edits actually match what the ADRs
   claim to have amended — a claimed amendment that never landed is a silent defect.

## Report

Short and ranked. For each finding: the ADR, which check it failed, one sentence on the defect, and
the specific fix. Group as **must fix before Batch B** / **strengthen when convenient** / **fine**.

**"All 23 are sound" is a valid and welcome outcome.** Do not manufacture findings to justify the
pass; a short report is the good result.

## Two things to know before you recommend anything

* **Strengthening prose does not require superseding.** The house rule is that an ADR is never
  edited *to hide a change of mind*. Sharpening an Alternatives section while the Decision stays
  identical is not a change of mind, and these were accepted hours ago with nothing yet depending
  on them. So a weak-but-correct ADR is a cheap edit, not a new record. An ADR whose **Decision** is
  wrong is the opposite — that is a real supersede, and it should block the phases that depend on it.
* **D-2 (ADR-0046) and A-1 (ADR-0058) are load-bearing right now.** Part A2 implemented them the
  same night, into `baseaicore` 0.4.1, which is prepared but — if the overnight instructions were
  followed — **not yet tagged**. If either is wrong, say so first and loudly: it is still free to
  fix, and it stops being free the moment that tag is pushed.

**Report; do not edit.** The decisions are the architect's. Once the findings are approved, apply
them in a separate pass.
