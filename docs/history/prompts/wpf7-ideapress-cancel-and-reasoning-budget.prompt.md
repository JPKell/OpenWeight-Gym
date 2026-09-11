# Kickoff — WPF7: IdeaPress honours a cancel across its retry, and finishes a project on its own bindings

**Row:** WPF7 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md), finding 8). Runs after WP6. It is
independent of the other WPF rows.
**Ships:** unreleased, no version bump.
- **IdeaPress:** a cancel requested during a model call ends the run **cancelled** at the next
  model-call boundary, the retry of an empty generation included, and every model call a run makes
  is recorded as an attempt. A project on IdeaPress's configured bindings plans, drafts, reviews and
  exports without a stage exhausting its output budget, or the operator is told before the run
  which binding cannot fit.

**Component:** `~/ai/suite/IdeaPress`, plus the console's fixtures if an IdeaPress answer changes.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WP6_HANDOFF.md` finding 8 and check 2's IdeaPress table; `M7_HANDOFF.md` M7-16 and
M7-19 (the empty-generation retry and the raised token budgets); `WP5_HANDOFF.md` §2 items 1–3 and
§5 step 3 (a cancel that did land); `WI1_HANDOFF.md` (runtime settings); `I6_HANDOFF.md` and
`I3_HANDOFF.md` (thinking control on Ollama); `apps/ideapress/workflows.md`; ADR-0038; ADR-0099.

**Code to read first:** IdeaPress's `services/inference.py` (the empty-generation retry, near the
*produced no text at all* message), the stage bodies and the review loop (where
`cancel_requested` is read), and the code that writes `attempts` rows; `config.py`
(`workflow.structured_output_tokens`, `[models.stages]`).

## What WP6 saw on the reference machine (2026-09-11)

1. **A cancel that did not land.** A `project_review` run was started from the console at 14:03:14
   PDT (audit `01M294G788QHTP8SR78R0KYFPB`, task `01M294G77WCS4NANGVCV9BJWSF`). **Cancel** was pressed
   at 14:03:17. The console's audit row is `01M294GAAYYE91ECHK56EASENP`, and IdeaPress's answer was
   *Cancellation requested. IdeaPress honours it at the next model-call boundary*. Ollama served
   two calls: 14:03:15–14:06:09 (2 m 54 s, in flight when the cancel arrived) and **14:06:10–14:08:57
   (2 m 47 s, started after it)**. The run ended **`failed`**, `CONTEXT_LIMIT_EXCEEDED`: *The model
   produced no text at all in 8192 output tokens, twice, for the 'project_review' stage.* Its events
   are `stage.started` and `stage.failed` only, and **0 attempts** are recorded.
2. **The configured bindings cannot finish a project.** Every stage is bound to
   `ollama/qwen3.5:9b-q8_0`, which thinks before it answers. On project
   `01M28ZYHH7GS9RGX5GR0JVEG3F` (5 units):
   * the draft run paused U-03, because the critique produced no text in 8 192 tokens, twice;
   * a revision paused U-01, because the reviser produced no text in 8 392 tokens, twice;
   * `project_review` failed as in item 1;
   * the export was refused until both units were resumed. U-03 was resumed with a per-run
     `model_hint` of `ollama/gemma4:12b-it-q8_0`, and committed in 133 s.

   `workflow.structured_output_tokens` (8 192) is config-only.
3. What worked: every refusal and pause said, in IdeaPress's words, what was exhausted and what to
   raise, and the console rendered it as IdeaPress wrote it.

## Decisions already taken — do not reopen

* **A model never decides control flow** (CLAUDE.md). A cancel is checked by Python at every model-call
  boundary, and a retry is a model call.
* **A run records what it spent.** An empty generation is an attempt, with its tokens, whatever the
  stage's outcome.
* **No silent budget raise.** Whatever changes, the operator can see which stage and binding it
  applies to (spec §12, `config show`).

## Decisions for this row — make each, and record it in the handoff

1. **The retry and the cancel.** Where the check goes, and what a cancel during the first empty
   generation leaves behind: `cancelled`, with no second call.
2. **The budget for thinking models.** Measure `qwen3.5:9b-q8_0`'s thinking tokens on the critique,
   revise and project-review prompts on the reference machine. Then choose: a larger default, a
   per-stage budget, runtime-changeable or not, or a thinking control where Ollama honours it (I6
   found it unreliable on some models). Say why.
3. **Whether IdeaPress should refuse before the run** a binding whose last measured thinking exceeds
   the budget, rather than pausing units mid-run.

## Gates

**Gate A — the cancel.** Tests first, against a scripted backend that returns an empty generation
and then text: a cancel between the two ends the run `cancelled` with one call made, and every call
is an attempt row. Implement. Run the gate, naming the interpreter. Commit.

**Gate B — the budget.** Measure, decide, implement, and document it in `workflows.md` or the
configuration reference. Commit.

**Gate C — the live proof.** On the reference machine, from the console: a new project planned,
drafted, reviewed and exported on IdeaPress's configured bindings with no pause and no per-run model
hint, and a `project_review` cancelled during its first call that ends `cancelled`. One live model
load at a time. Commit the handoff.

## Finish line

- The gate green, with the interpreter named, and coverage held; `git status --short` clean.
- `docs/history/handoffs/WPF7_HANDOFF.md`: the measured thinking tokens, the budget decision, the
  cancel fix, the live ids, and what this kickoff got wrong.
- The row marked done. Nothing pushed.
