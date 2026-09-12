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

### 2. A judge call is bounded: `[judge] max_output_tokens`, default 2048

A judge answer is one small JSON object — a grade and a one-sentence reason. 2 048 tokens is an
order of magnitude more than that needs, and a juror that cannot produce it inside that budget is
not answering the rubric. Unbounded, such a juror spends the whole served window instead, which is
what the measurement above is.

The budget does not rescue a reasoning juror and is not meant to: it makes the same refusal arrive
in about a minute rather than seven, under a name that says what happened. `null` restores the
provider's own limit, and a raised value is how an operator keeps a juror that genuinely needs room.

The knob exists because the right figure is a property of the juror, not of FreeWeight. It is not a
`runtime_profile` field: the profile is how a model is *served* (ADR-0023), the same for candidate
and jury, while this is how one call is asked.

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
* Every juror is now polled under a 2 048-token ceiling by default, including jurors that answered
  fine before. A juror whose legitimate answer exceeds 2 048 tokens — none observed; the instruct
  juror this arc measured answers in a few hundred characters — would newly refuse
  `output_truncated`, which the report names, and the remedy is the setting.
* `judge_verdicts` rows carry the new reason like any other; the column is a free-text `String`.
* The `benchmark.calibration_report` export is untouched: exclusions are a report-level fact and
  never entered the frozen `1.0` payload.
