# ADR-0089 — The fixed regression rows bound their own output

**Status:** Accepted (2026-09-06)
**Extends:** [Benchmark Catalogue §8.2](../apps/freeweight/benchmark-catalog.md) (the regression
panel is fixed and versioned with the catalogue), [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md)
(the panel is declared + regression + performance).
**Relates to:** [ADR-0016](0016-unavailable-is-not-zero.md) (a truncated answer is a real
observation, not a missing one), [FreeWeight risks](../apps/freeweight/risks.md) T11 and its fourth
revisit trigger ("cost, honestly measured").
**Source:** Row H6, measured on the reference machine against a deliberately damaged LoRA.

## Context

The A-2 regression panel exists to catch an adapter that learned a voice and stopped taking
direction. Row H6 built one on purpose and measured it, and found that **the case the panel exists
to catch is also the case where the panel is most expensive** — for the same underlying reason.

An adapter that has lost instruction-following has usually lost the instruction *to stop*. The
damaged LoRA emits no stop token at all: uncapped, every case generates until the served context is
exhausted. Measured on this machine, `native.instruction_following` (11 cases) plus
`native.structured_output` (3 cases):

| Subject | `instruction_following` (11 cases) | `structured_output` (3 cases, two turns each) |
|---|---|---|
| bare base | 37 | 79 |
| `+terse` | 26 | 79 |
| `+pirate` | 35 | 79 |
| `+verbose` — *trained to answer at length* | 61 | 79 |
| **`+damaged`** | **hit every cap offered, `finish_reason = length`** | **the same** |

Maximum output tokens per sample; every healthy figure carries `finish_reason = "stop"`, every
damaged one `"length"`. The medians are 17 and ~31. `native.structured_output` is a two-turn
interaction — an attempt and one corrective retry — so its 79 is roughly 40 per turn.

The panel took **72 s** at `max_output_tokens = 512` and would have taken roughly **forty minutes**
uncapped. That is the whole panel spent on one subject, and it is the subject an operator most needs
an answer about. A regression check nobody runs because it might take forty minutes is not a
regression check.

The healthy figures are the other half of the finding. **No healthy subject on either fixed row came
within an order of magnitude of a cap**: the longest answer any of them produced was 79 tokens per
sample, and on `instruction_following` the worst was 61 — from the adapter explicitly trained to be
verbose. The fixed rows' cases are short by construction —
"answer in exactly three words", "reply with JSON matching this schema" — and that is a property of
the suites, which are fixed and versioned here.

Today the only cap is `FWTEST_A2_MAX_OUTPUT_TOKENS`, an environment variable read by one live test.
The product has none.

## Decision

**The two fixed regression rows run under a fixed output cap of 512 tokens, which is part of the
panel's definition and versioned with this catalogue. Nothing else in the panel is capped.**

1. **512 tokens per turn, on `native.instruction_following` and `native.structured_output` only.**
   Six times the longest answer any healthy subject has produced on either row, and roughly twenty
   times the median. It is chosen to be unreachable by a model that is behaving, and it is recorded
   here with the measurements that make that claim checkable rather than asserted.
2. **A truncated sample is a finding, not a defect in the measurement.** A sample that ends at the
   cap records `finish_reason = "length"` and is scored as what it is — an answer that did not
   comply. On a suite whose subject *is* whether the model does what it was told, failing to stop is
   a failure to follow instructions, and scoring it as one is the honest reading, not a distortion
   introduced by the cap. [ADR-0016](0016-unavailable-is-not-zero.md) is untouched: this is a real
   observation of a real response, not an absence dressed as a zero.
3. **Not configurable, for §8.2's reason.** Two adapters' regression numbers must be comparable
   across installations. A per-deployment cap makes "the regression panel" stop meaning one thing,
   exactly as a per-deployment suite list would. Changing the number is a change to this catalogue,
   versioned with it and visible in review.
4. **The rest of the panel keeps its suites' own budgets.** The declared part runs the suites a
   manifest's capabilities map to, the performance part runs the performance suite, and row 3
   resolves per base to whatever that base is strongest at. Those are ordinary benchmarks whose
   output needs are set by their own definitions — `native.long_context` and a goal suite that
   drafts prose both legitimately need far more than 512 tokens, and capping them at a number chosen
   for a three-word-answer suite would break real measurements to save time on a synthetic one.
5. **The live test's environment variable stays**, now only to *widen* or remove the cap when
   somebody wants to measure the uncapped cost again. It no longer supplies the cap.

## Alternatives considered

**Leave it uncapped and let operators discover the cost.** The status quo, and the option row H6
could have taken by simply recording the number in the risk register. Rejected because the cost is
not evenly distributed: it falls entirely on damaged adapters, so the panel is cheap exactly when it
finds nothing and expensive exactly when it finds something. An operator who runs it once against a
broken LoRA, waits forty minutes, and stops running it has been taught the wrong lesson by the
tool.

**A configuration knob** (`[execution] regression_panel_max_output_tokens`). Cheaper to write and
genuinely tempting, because operators have different machines and different patience. Rejected on
§8.2's own argument: the regression panel is the one part of the panel that is *fixed* so that two
adapters' numbers can be compared, and a cap changes scores — a subject measured at 512 and a
subject measured at 4096 have not been measured the same way. A knob here would quietly reintroduce
the incomparability the fixed panel exists to prevent.

**Cap the whole panel at one number.** Simpler to explain and simpler to implement. Rejected by rule
4's cases: the declared part and row 3 run real capability suites, and a cap chosen for short-answer
suites would truncate a long-context or drafting benchmark and record the truncation as a capability
loss. That is a fabricated regression, which is worse than a slow panel.

**Detect the runaway instead of capping it** — stop a subject after N consecutive `length` finishes
and mark the panel degraded. Attractive, because it costs a healthy adapter nothing at all and names
the pathology directly. Rejected as more mechanism than the problem needs: the cap already produces
that signal (every sample ends `length` and the score collapses), and an early-exit rule would make
a subject's score depend on the *order* its cases ran in. Worth revisiting if 512 ever turns out to
be too generous to bound the cost.

## Consequences

* The panel's worst case is bounded and roughly predictable. `native.structured_output` is a
  two-turn interaction — an attempt and one corrective retry — and the cap applies per turn, so the
  fixed rows cannot exceed `11 × 512 + 3 × 2 × 512 = 8 704` output tokens per subject, whatever the
  adapter does.
* A damaged adapter's numbers are now produced in about a minute, so the panel is runnable in the
  situation it was built for.
* The fixed rows' scores are, in principle, comparable only within one version of this catalogue —
  which was already true, and is now true for one more reason. Panels composed before this decision
  used the provider's default cap; the runs affected are those where a subject actually reached it,
  which is to say the damaged ones.
* `native.instruction_following`'s notion of compliance now includes stopping, in the specific sense
  that a non-stopping answer scores as non-compliant. That is a sharpening of what the suite already
  measured, and it is stated here because it is the kind of thing that should not be discovered from
  a score.

## Revisit when

A fixed regression row gains a case whose legitimate answer approaches 512 tokens — at which point
the cap and the case are in conflict and one of them is wrong, and this record should be reopened
before the case is added. Or if 512 proves too generous to bound the cost on a slower machine, in
which case the early-exit alternative above is the next thing to weigh rather than a smaller number.
