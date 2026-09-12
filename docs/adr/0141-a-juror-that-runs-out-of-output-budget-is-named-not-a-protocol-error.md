# ADR-0141 — A juror that runs out of output budget is named, bounded, and not asked to stop thinking

**Status:** Accepted (2026-09-12)
**Extends:** [ADR-0031](0031-user-defined-goal-benchmarks.md) §4 (a refusal is recorded,
never silently discounted).
**Relates to:** [ADR-0099](0099-a-task-profile-may-ask-for-reduced-thinking.md) rule 5 (`thinking_control`
is not in the SetSpec capability vocabulary and is enforced per provider), [ADR-0023](0023-runtime-profile-resolution.md) §4 (a juror
is served under a stated profile), [ADR-0016](0016-unavailable-is-not-zero.md) (an absent measurement
is not a number).
**Source:** row WPF9, from [WPF8's Gate B](../history/handoffs/WPF8_HANDOFF.md) §9.2.

## Context

WPF8 plumbed an exclusion reason from the jury through to the calibration report: a held-out sample
the jury judged but could not grade is named in `excluded`, with why. Its own Gate B then found that
the "why" was the same word for two unrelated events.

On the reference machine, one rubric call to `wp6_goal`'s pinned juror
`llamacpp/Qwen3.5-9B-UD-Q8_K_XL@sha256:2c4e08e0e72c`, through FreeWeight's own prompt and provider:

```
finish_reason: length
usage: input_tokens=1180, output_tokens=7012
raw answer: (empty)
parsed: (None, None)
```

1 180 + 7 012 = 8 192 — the served window exactly. The juror spent every token it had reasoning and
emitted no answer at all. Three of four samples for `technical_correctness` went that way, each
recorded as `protocol_error`: the same word FreeWeight uses for a juror that *answered* and said
something no grade could be read from. They are different events with different remedies, and the
report could not tell them apart. This is WPF7's IdeaPress finding in FreeWeight's jury.

`JuryService._request` also set no `max_output_tokens`, so nothing but the served context bounded
the call: seven minutes per sample to learn nothing.

## Decision

### 1. A juror cut off at its output limit refuses `output_truncated`, not `protocol_error`

`JurorVerdict.refused_reason` gains one value, decided from the generation's own `finish_reason`:
`FinishReason.LENGTH` with no readable grade is `output_truncated`; anything else with no readable
grade stays `protocol_error`. Rubric and pairwise alike.

The reason code was chosen over recording `finish_reason` beside `protocol_error` because the
refusal reason is already the field every reader of this fact consumes — the verdict, the
`judge_verdicts` row, `_exclusion_reason`, and the report's `excluded` entries — so the distinction
arrives everywhere at once with no new column, no migration and no schema change. `finish_reason`
is the evidence for the refusal, not the refusal.

### 2. The judge call *can* be bounded — `[judge] max_output_tokens` — but is not by default

The setting exists and reaches every juror's request. **Its default is `null`: the provider's own
limit, which on a served model is the context window.** That is the shape FreeWeight has always had,
and this decision keeps it deliberately rather than by omission.

The first draft of this ADR defaulted it to 2 048, on the reasoning that a judge answer is one small
JSON object and anything larger is a juror not answering the rubric. **Row WPF9's Gate B measured
that default and it was wrong**, on the juror it was supposed to be safe for:

| `wp6_goal`, `gemma-4-12b-it-Q4_K_M`, 4 holdout samples | unbounded (WPF8) | 2 048 |
|---|---|---|
| `technical_correctness` | κ_w 0.4, n 4 | κ_w 0.4, n 4 |
| `audience_fit` | κ_w 0.2286, **n 3** | κ_w **0.0**, **n 2** |
| Goal κ_w | 0.3429 | 0.2667 |

A 12 B *instruct* juror — the one the operator forked to precisely because it answers the rubric
directly — hit 2 048 on two of eight calls and lost a sample it had been grading. **A default that
silently narrows a measurement is worse than a slow refusal**, because FreeWeight is the instrument:
the cap's only benefit is that a bad juror fails sooner, and that benefit does not pay for a
coefficient computed over fewer pairs.

So the figure is the operator's, not FreeWeight's: set it to make a reasoning juror fail fast, leave
it unset to let every juror finish. Either way decision 1 names what happened, because the served
context bounds the generation even when nothing else does — `finish_reason: length` is exactly what
the Context above records, with no budget set at all.

It is not a `runtime_profile` field: the profile is how a model is *served* (ADR-0023), the same for
candidate and jury, while this is how one call is asked.

### 3. FreeWeight does not ask a reasoning juror not to reason

No `think`, no reasoning suppression, at any layer of the jury. Three reasons, and the first one
alone settles it for the juror that produced this finding:

* **The provider cannot be asked.** `LlamaCppProvider` declares `thinking_control = False` and
  raises `CapabilityUnsupported` for any request that sets `think` — and `wp6_goal`'s juror is a
  `llamacpp/` model. The same is true of every OpenAI-compatible backend. Sending it would turn a
  juror that returns an unusable answer into a juror that cannot be polled at all.
* **Where it *can* be sent, it is unreliable.** I6 measured Ollama closing the stream on 12 of 13
  attempts for one model and `deepseek-coder-v2` crashing the daemon outright; 8 of 10 models
  honour it. A measuring instrument does not carry a per-model workaround that can take the host
  down.
* **It is not a capability anyone can require.** ADR-0099 rule 5 keeps `thinking_control` out of the
  SetSpec vocabulary, so a goal cannot state the need and a jury cannot check it — there is nothing
  to branch on but the model's name.

So the refusal is made legible instead, which decisions 1 and 2 do — and the calibration report says
it in words: a warning naming the jurors that ran out, that the samples are *unmeasured rather than
disagreed with*, and the two things that change it (raise the budget, or pin a juror that answers
the rubric directly).

### 4. Eligibility stays a question of permission, not of competence

`GET /judges` keeps reporting every model as eligible. Eligibility answers *may this model judge* —
self-judging, remote permission, presence in the catalogue — all of which are knowable before any
call. *Can this model answer a rubric inside a budget* is not: FreeWeight has no declared signal for
"this model reasons" (ADR-0099 again), and a name-matching heuristic would refuse jurors that work
and admit ones that do not.

The competence question already has an answer, and it is the calibration report: that is what the
holdout exists to measure. Decisions 1–3 are what make its answer legible on the first run rather
than on the second.

## Consequences

* A report that previously said `protocol_error` for a truncated juror now says `output_truncated`,
  and carries a warning in words. Reports written before this row keep the word they were written
  with — the exclusion is stored text, and nothing rewrites it.
* **No juror's behaviour changes unless an operator sets the budget.** Every existing calibration
  and goal run reproduces exactly as before, which is what makes WPF8's figures still comparable.
* What a set budget costs is now measured rather than assumed, and it is not small. At 2 048 on
  `wp6_goal`: `Qwen3.5-9B` (reasoning) went from answering 3 of 8 rubric calls to 0 of 8, and the
  run finished in 8 minutes instead of 22 — the same verdict, `uncalibrated` with no coefficient,
  arriving faster and named. `gemma-4-12b-it` (instruct) went from 1 dropped sample to 2, and the
  goal's κ_w from 0.3429 to 0.2667. Speed on a hopeless juror, accuracy on a working one — which is
  why the figure belongs to whoever knows which they have.
* A goal *run*'s `judge_verdicts` rows carry the new reason like any other — the column is a
  free-text `String`. A *calibration* writes no verdict rows: its exclusions and warnings live in
  `calibration_reports.disagreement_json`, which is where WPF8 put them and why this row needed no
  migration either.
* The `benchmark.calibration_report` export is untouched: exclusions are a report-level fact and
  never entered the frozen `1.0` payload.
