# ADR-0031 — User-defined goal benchmarks and the calibrated-judge instrument

**Status:** Accepted (2026-08-26)
**Amends:** [Benchmark Catalog §1, §6](../apps/freeweight/benchmark-catalog.md) (closes the undelivered `creative_writing` mapping), [Testing Standards §3](../standards/testing-standards.md) (draws the oracle/instrument line explicitly), [Prompt Management Standards §6](../standards/prompt-management-standards.md) (separates *authoring* from *override*).
**Amended by:** [ADR-0032](0032-judge-validity-and-user-capability-namespace.md) — what crosses the application boundary.

## Context

FreeWeight measures capability. Its scoring ladder is deterministic-first and its catalogue is
excellent at things with ground truth: does the code pass, does the JSON validate, was the right tool
called, was the mutation found. For an entire class of real work — *"write in this voice"*, *"sound
like our house style"*, *"summarize without inventing"* — there is no ground truth in the corpus.
The ground truth is in the user's head.

Four facts about the specification as frozen:

1. **There is no user-authored benchmark of any kind.** `benchmark_suites.runner` is
   `native | external`. Every suite ships with the application or is a pinned third-party adapter.
   A user cannot express a measurement goal at all.
2. **The judge machinery points the wrong way.** `native.judge` measures how good a model is *at
   judging*. Nothing *uses* a judge to score a candidate against a rubric.
3. **§6 promises a suite that does not exist.** The capability mapping lists
   `summarization` / `creative_writing` → "Judge-scored suites, with judge trustworthiness linked".
   No such suite appears in §3 or §4. That is a dangling contract, and by this project's own rule a
   missing architectural decision is a defect to close with an ADR before writing code.
4. **Prompt override is a hostile surface, deliberately.** [Prompt Standards §6](../standards/prompt-management-standards.md)
   makes FreeWeight *refuse* to benchmark with an overridden prompt absent `--allow-prompt-override`,
   and records the override in the fingerprint. That is correct — it protects comparability of
   *shipped* benchmarks — but it means the one user-editable surface in the system is designed to
   invalidate results, not to author them. Authoring and overriding are different acts and must not
   share a mechanism.

### The contradiction that has to be resolved, not finessed

[Testing Standards §3](../standards/testing-standards.md) is titled "Never let a model be the
oracle". The scoring ladder's rung 5 is LLM-as-judge. Read naively these cannot both stand, and the
naive reading is why the judged suites were promised but never designed.

The two statements are about different things, and the specification never said so:

* **Oracle** — the thing a *test* asserts against. FreeWeight's own CI must pass with no GPU, no
  Ollama and no network; no model may decide whether FreeWeight's code is correct, and no model may
  decide FreeWeight's control flow. This ban is absolute and this ADR does not touch it.
* **Instrument** — a thing that *takes a measurement*, with a calibration curve and a stated error.
  A thermocouple is not a wrong thermometer because it drifts; it is a usable instrument because its
  drift is characterized. An uncalibrated judge is not an instrument. It is an opinion with a
  decimal point.

The distinction that makes rung 5 legitimate is therefore **calibration against user-supplied ground
truth, with the resulting error reported alongside every number the instrument produces**. Absent
that, a judged score has dispersion but no validity: repeating it five times tells you the judge is
consistent, and tells you nothing about whether the judge's 4 is the user's 4.

## Decision

### 1. A third runner kind: `goal`

`benchmark_suites.runner` becomes `native | external | goal`. A **goal suite** is a user-authored
benchmark, first-class in every respect that matters: it has a manifest, a version, a hash, metric
definitions, a place in the run engine, raw samples that every headline number drills to, and a row
in the comparison UI. It differs from a native suite in exactly two ways — it was authored by the
user rather than shipped, and its judged criteria carry a calibration record.

Goal suites are **not** prompt overrides and do not engage `--allow-prompt-override`. Overriding a
shipped prompt changes a measurement everyone else shares; authoring a goal creates a measurement
that did not previously exist. The first needs a guard rail, the second needs a wizard.

### 2. The scoring stack is composed, not chosen

The ladder in [Benchmark Catalog §1](../apps/freeweight/benchmark-catalog.md) is unchanged and still
binding *per criterion*. A goal declares criteria; each criterion declares the rung it is scored at:

```text
rung 2  rule       forbidden/required phrase, regex, word- and sentence-length distribution,
                   readability band, POV and tense, structural constraints, vocabulary lists,
                   JSON/Markdown shape                                     — deterministic, free
rung 3  reference  similarity or coverage against user-supplied ground truth
                   (entity recall, claim coverage for faithfulness)        — deterministic, free
rung 4  human      the user grades, blinded, in the UI                     — recorded as `human`
rung 5  judge      the irreducible remainder: voice, wit, register, cohesion
```

`freeweight goals validate` **flags any rung-5 criterion a rung-2 rule could check** and names the
rule. This is a lint, not a refusal — the user may overrule it with a recorded reason — because the
system cannot know that "avoid corporate hedging" is fully covered by a phrase list, and a false
refusal is worse than a warning. Every goal result reports what fraction of its weight was scored
deterministically; a goal whose weight is 60 % rules is affected by judge variance across 40 % of
its score, and the UI says so.

### 3. Calibration is the price of a judged criterion

A goal with any rung-5 criterion is unusable until calibrated.

* The user grades **N calibration samples** (default target 12, minimum 8) per goal, on each judged
  criterion's ordinal scale.
* The set is split by a seeded, recorded partition: **anchors** (default 60 %) are embedded in the
  judge prompt as few-shot exemplars; **holdout** (default 40 %) is *never shown to the judge*.
* The judge — the same jury configuration, prompts and sampling parameters the goal will run with —
  scores the holdout. Agreement with the user is computed per judged criterion:

```text
kappa_w   quadratic-weighted Cohen's kappa      the headline; ordinal-aware, chance-corrected
rho       Spearman rank correlation             does the judge rank as the user ranks
mae       mean absolute error, in scale points  how far off, in units the user understands
bias      mean signed error                     does the judge run generous or harsh
```

* `kappa_w` is the gate. Weighted across judged criteria by criterion weight, it must reach
  `calibration.min_agreement` (default **0.40**) for the goal to emit capability evidence. Below it,
  runs still execute and every sample is inspectable, but the result is badged **UNCALIBRATED** and
  contributes no evidence ([ADR-0032](0032-judge-validity-and-user-capability-namespace.md)).
* The UI names the criteria the judge disagreed with the user on most, with the specific samples,
  so the user can rewrite the criterion. **The application never rewrites the criterion itself.** A
  model that reworded the user's taste until it became measurable would be optimizing the target
  into the instrument, and the resulting number would measure nothing.
* Calibration is re-run and recorded whenever the jury, the judge prompts, the sampling parameters
  or the criteria change. A calibration record has a `measured_at` and ages exactly as evidence does.

### 4. The judge is a jury, local by default

* Default: **2–3 distinct local models** score each case independently, blinded to the candidate
  model's identity, with case order and criterion order randomized and repeated trials.
* **Inter-judge agreement is a headline metric**, not a footnote. Disagreement between judges enters
  `consistency_factor`; disagreement with the user enters the validity factor.
* A juror is ineligible to judge output it produced. Self-judging is refused, not discounted, and the
  refusal is recorded — `native.judge` already measures self-preference, and there is no reason to
  admit a bias the catalogue elsewhere treats as a defect.
* Every judged score links to the juror's own `native.judge` results, as §3.11 already requires, so
  "how trustworthy is this instrument" is answerable in one interaction.
* A **remote frontier judge is permitted, opt-in only**. It requires `providers.allow_remote = true`
  *and* per-goal `judge.allow_remote = true`, is recorded in the fingerprint, and **separates**
  results from locally-judged ones rather than merging with them. The default install measures
  offline. A better instrument is worth having; a silently different instrument is not.

### 5. The user supplies the tasks; the application ships starters

The prompts the candidate model answers are the user's own. A voice measured on someone else's
prompts measures the wrong thing.

FreeWeight ships four **starter goal packs** — creative writing style and tone, persona and brand
voice, summarization faithfulness, technical explanation quality — complete with tasks, criteria,
proposed rules and worked calibration sets. They exist to be forked, to make the feature
demonstrable on a fresh install, and to teach the shape of a good rubric by example. They are
starters, never defaults: a goal that has not been edited is badged as unforked in the UI.

### 6. A goal is a portable, versioned artifact

A **goal pack** — criteria, rules, tasks, judge configuration, calibration samples and the user's
grades — exports as one hash-pinned bundle and imports on another machine. `goal_hash` covers the
measurement-defining content and behaves exactly as a benchmark version: results from different
`goal_hash` values are **separated, never averaged**. The user's grades travel with the pack, because
without them an importer has an uncalibrated rubric; the importer is told whose grades they are and
may re-calibrate against their own.

Goal packs live under `$XDG_CONFIG_HOME/freeweight/goals/<slug>/`, are JSON per
[ADR-0019](0019-python-baseline-and-config-format.md), and their prompt records obey
[ADR-0012](0012-prompt-storage-format.md) in full — they are prompts, and prompts are versioned data.

### 7. The wizard emits a file

The authoring surface is a guided web flow (define goal → draft criteria → the application proposes
mechanizable rules → supply tasks → grade the calibration set inline → see agreement → save) whose
output is the editable, git-trackable goal pack of §6. `freeweight goals init` runs the same
interview in the terminal. The wizard is a teacher, not a container: nothing it produces is
inaccessible to a text editor, and nothing requires it.

## Alternatives considered

**Leave subjective goals out of FreeWeight.** Defensible, and the cheapest option. Rejected on two
grounds: §6 of the catalogue already promises judged capability mapping, so the alternative is not
"don't build it" but "delete the promise"; and the classes of work the suite exists to serve
(IdeaPress is a content application) are substantially subjective. A measurement tool that measures
only what is easy to measure pushes the user's real question somewhere it cannot be answered
honestly at all.

**Absolute rubric scoring with no calibration.** Much cheaper: the user writes a 1–5 scale per
criterion, the judge scores, repeated trials give dispersion. Rejected: dispersion is not validity.
This produces a number with real error bars around an unknown quantity, which is *more* dangerous
than an obviously vague adjective, because it looks like a measurement and will be compared,
tracked and routed on.

**Pairwise against user references only.** Attractive — it reuses `native.judge`'s existing bias
controls directly, needs no absolute scale, and pairwise preference is known to be a more reliable
judge task than absolute rating. Rejected as the *primary* method because it answers "better or
worse than my reference" rather than "how good", cannot be tracked as a level over time, and
degrades badly once the candidate exceeds the reference. **Retained as a supported criterion type**
inside the anchored frame, where the reference set is available.

**Let the model repair a failing rubric automatically.** Rejected in §3 above. It optimizes the
target into the instrument.

**A single strong local judge instead of a jury.** Simpler and cheaper. Rejected: with one judge
there is no inter-judge agreement, so the only visible variance is the judge's self-consistency,
which a biased judge exhibits perfectly. The jury is what makes bias distinguishable from noise.

**Remote frontier judge by default.** The best instrument available, and this was a genuine
temptation. Rejected: it breaks the no-network default, makes a headline number depend on a vendor's
undisclosed model revision, and adds cost to a tool whose premise is measuring local models on your
own hardware. Permitted opt-in, recorded, and separated.

## Consequences

*Positive.* The `creative_writing` promise is honoured with a real mechanism. Rung 5 becomes
legitimate because it is calibrated, and the oracle/instrument line is written down instead of
implied. Deterministic-first is *strengthened*, not weakened: the lint actively pushes weight down
the ladder, and the UI rewards a goal for mechanizing more of itself. A user can measure the thing
they actually care about, and can be told, with a number, when their rubric is not yet measurable.

*Negative.* Real setup cost. Grading 12 samples per goal is genuine work, and some users will not do
it. Mitigated by the starter packs, the inline grading UI, and the minimum of 8 — but not eliminated,
and it should not be: the cost *is* the ground truth.

*Negative.* A new authoring surface is new attack surface and new support burden — user-supplied
Jinja2 templates, user-supplied regex (catastrophic backtracking), user-supplied task text of
arbitrary size. Handled in the spec's security section: goal templates render under the same
`StrictUndefined` sandbox as shipped prompts, rules run under a timeout with a re-linted regex
dialect, and goal packs are size-capped and containment-checked on import.

*Negative.* `kappa_w` on 5 holdout samples is a noisy statistic, and users will read it as precise.
Mitigated by shrinking the validity factor toward zero at small holdout sizes
([ADR-0032](0032-judge-validity-and-user-capability-namespace.md)) and by displaying `n_holdout`
next to every agreement figure, never the coefficient alone.

*Negative.* Goal results are, in the end, a measurement of one person's taste. This is a feature and
a hazard. Contained by the `user.*` namespace and the validity cap in ADR-0032, which keep a
subjective score structurally weaker than a deterministic one wherever the two compete.

*Foreclosed.* Comparing goal results across users without a shared goal pack. Two people's
"good tone" are different measurements, and the `goal_hash` separation makes that explicit rather
than letting the numbers silently merge.

## Revisit when

Real calibration data exists across a few dozen goals and shows either that the 0.40 gate is
routinely unreachable for legitimate rubrics (the gate is wrong), or that goals passing it still
produce scores users disagree with (the method is wrong). Or when a local open-weight judge
demonstrates agreement with users comparable to a frontier model, at which point the remote judge
opt-in loses its justification and should be removed rather than left as a legacy escape hatch.
