# WPF9 Handoff — a juror that never answers is named, bounded, and not asked to stop thinking

**Row:** WPF9 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-12, unattended · **Model:** Claude
Opus 5 · **Kickoff:** `history/prompts/wpf9-freeweight-a-juror-that-never-answers.prompt.md` ·
**Ships:** unreleased, no version bump · **Branch:** `main` in both repositories.

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| FreeWeight | `c215e32` | A | `output_truncated` as its own refusal reason, `[judge] max_output_tokens` reaching every juror's request, the calibration report's warning in words, the regenerated config reference |
| FreeWeight | (Gate B) | B | the budget's default reversed to `null`, after Gate B measured 2048 costing a working juror a sample (§4.3) |
| WeightRoom | `e5850cc` | A | ADR-0141 and its index row; `apps/freeweight/api.md` §3a, `spec.md`'s `[judge]` block, FreeWeight's regenerated configuration guide |
| WeightRoom | `5a0a51a` | A | IdeaPress's two guides re-mirrored — pre-existing drift, unrelated to this row (§7) |
| WeightRoom | (this file) | B | the handoff and the row |

Nothing pushed, nothing tagged, no version bumped.

## 2. The four decisions (ADR-0141)

### 1 — The refusal names the cause, as a reason code rather than a recorded `finish_reason`

`JurorVerdict.refused_reason` gains `output_truncated`, decided from the generation's own
`finish_reason`: `FinishReason.LENGTH` with no readable grade is `output_truncated`, anything else
with no readable grade stays `protocol_error`. Rubric and pairwise alike, in one helper
(`_refusal_for`).

The kickoff offered two shapes — a new reason, or `finish_reason` recorded beside `protocol_error`.
The reason code wins on both correctness and size: `refused_reason` is already the field every
reader of this fact consumes (the verdict, the `judge_verdicts` row, `_exclusion_reason`, the
report's `excluded` entries, WPF8's whole chain), so the distinction arrives everywhere at once with
**no column, no migration and no schema change**. `finish_reason` is the *evidence* for the refusal;
the refusal is the fact.

### 2 — The judge call *can* be bounded, and is not by default

`_request` now carries `SamplingParameters(max_output_tokens=…)` from a new `[judge]
max_output_tokens`. **Its default is `null`** — the provider's own limit, which is today's
behaviour unchanged.

**This reverses the decision this row first shipped, and Gate B is why** (§4.3). The setting was
first defaulted to 2 048, on the reasoning that a judge answer is one small JSON object and anything
larger is a juror not answering the rubric. That reasoning is wrong about a real instruct juror: at
2 048, `gemma-4-12b-it` — the model the operator forked `wp6_goal` to *because* it answers directly
— lost a sample it had been grading, and the goal's κ_w fell from 0.3429 to 0.2667. A default that
silently narrows a measurement is worse than a slow refusal, because the measurement is the product.

The figure belongs to the operator, who knows which kind of juror they pinned. Decision 1 names the
refusal either way: the served context bounds the generation even with no budget set, which is
exactly what WPF8 observed.

### 3 — FreeWeight does not ask a reasoning juror not to reason

**And the decisive reason is stronger than the kickoff assumed.** `LlamaCppProvider` declares
`thinking_control = False` and raises `CapabilityUnsupported` for any request that sets `think`
(`providers/llamacpp.py:220`, `:1821`) — and `wp6_goal`'s juror is a `llamacpp/` model. Every
OpenAI-compatible backend is the same (`openai_compatible.py:176`, `:998`). Sending `think` would
turn a juror that returns an unusable answer into a juror that cannot be polled at all. Beyond that,
I6 measured the unreliability where it *can* be sent, and ADR-0099 rule 5 keeps `thinking_control`
out of the SetSpec vocabulary, so no goal can state the need and no jury can check it.

### 4 — Eligibility stays a question of permission, not of competence

`GET /judges` is unchanged and still reports every model eligible, reasoning or not. Eligibility
answers *may this model judge* — self-judging, remote permission, presence in the catalogue — all
knowable before any call. *Can this model answer a rubric inside a budget* is not: there is no
declared signal for "this model reasons", and a name-matching heuristic would refuse jurors that
work and admit ones that do not. The competence question already has an answer, and it is the
calibration report. Decisions 1–3 are what make its answer legible on the first run.

## 3. Where the words live, and why they are not only in `excluded`

WPF8 plumbed `excluded` end to end, and the kickoff asked for the new vocabulary to be carried into
it. It is. But `excluded` **cannot reach the case this row was about**, and Gate B is the proof:

* `measure_agreement` omits a criterion that produced **zero counted pairs** from
  `outcome.criteria` entirely — WPF8's own rule, locked by
  `TestAJudgedGoalThatCouldNotBeGradedIsUncalibrated`, and correct ("nothing to report is still
  nothing to report").
* When *every* sample truncates, every judged criterion has zero pairs. `criteria` is `[]`, and
  every `excluded` entry goes with it.

So the sentence an operator reads lives on `CalibrationOutcome.warnings`, built in `run_calibration`
from `judge_exclusions` directly — the map that is complete whether or not a criterion survived.
It names the jurors that ran out, says the samples are *unmeasured rather than disagreed with*, and
gives the two remedies.

It reaches every existing reader with **no rendering code at all**: FreeWeight's own report page
(`templates/goals/report.html:142`, "Before you read those numbers"), `freeweight goals report`
(`cli/commands/goals.py:892`), and WeightRoomGym's console report page
(`templates/fw_goal_report.html`, the same block). Verified live in the first of those (§4).

## 4. Gate B, on the reference machine (2026-09-12)

GPU clear before starting: 3 734 MiB of 16 311 used, `ollama ps` empty, no other live row. FreeWeight's
own config serves `[runtime] context_size = 8192` (`MEMORY_SAFETY.md`), which is the window WPF8's
measurement filled.

`wp6_goal`'s pack was re-pinned from WPF8's instruct fork back to the reasoning juror
`llamacpp/Qwen3.5-9B-UD-Q8_K_XL@sha256:2c4e08e0e72c` — `judge.models`, nothing else — and
`goal_hash` moved back to `sha256:3143423b…`, the pre-fork hash WPF8 recorded, which is a small
confirmation that the fork and the unfork are the same edit. The gemma pack was backed up first and
restored afterwards (§6). FreeWeight was restarted onto the new code; the juror loaded at
**11 240 MiB, one `llama-server`, nothing else on the device** (ADR-0119 honoured).

`POST /api/v1/goals/wp6_goal/calibration/run`, `200`, **493.3 s** — 4 holdout samples × 2 judged
criteria × 1 repetition = **8 rubric calls at ≈58 s each** (the journal's request spacing confirms
it: 07:26:18, 07:27:16, 07:28:14, … 07:34:17).

**Every one of the 8 calls truncated.** The report:

```
calibration_state   uncalibrated
weighted_kappa_w    null
n_anchor 8   n_holdout 0   n_judged 4
criteria            []
warnings            [ the sentence below ]
```

> 4 held-out sample(s) were dropped because the jury ran out of output budget before it answered
> (llamacpp/Qwen3.5-9B-UD-Q8_K_XL@sha256:2c4e08e0e72c). That is not a juror that failed your rubric
> — it never reached an answer at all, which is what a model that reasons at length does when
> nothing bounds it. Raise judge.max_output_tokens if you want to keep this juror, or pin the goal
> to one that answers the rubric directly; either way the samples below are unmeasured, not
> disagreed with.

**The row's exit condition is met**: the calibration completed, and the report names why each sample
was dropped in words an operator can act on. Confirmed in three places — the API payload, the stored
row (`calibration_reports.disagreement_json` carries `{"n_judged": 4, "warnings": [...]}`), and
FreeWeight's own rendered report page at `GET /goals/wp6_goal/report`, which shows it under **Before
you read those numbers**.

### 4.3 — What a 2 048 budget cost, which is why it is not the default

Two comparisons, both against WPF8's unbounded runs of the same goal and the same four samples.

**On the reasoning juror it was designed for, the cap is pure gain:**

| `Qwen3.5-9B-UD-Q8_K_XL` | WPF8 (unbounded) | at 2 048 |
|---|---|---|
| Wall clock | ~22 min | **8 min 13 s** |
| Per rubric call | ≈165 s | **≈58 s** |
| Calls that answered | 3 of 8 | 0 of 8 |
| Criteria with a coefficient | 0 | 0 |
| `calibration_state` | `uncalibrated` | `uncalibrated` |
| Why, in the report | `protocol_error` ×5, unexplained | `output_truncated`, named in words |

Same verdict, a third of the time, and now with a cause. So far so good.

**Then the restore run (§6) measured it on the instruct juror, where it is a loss:**

| `gemma-4-12b-it-Q4_K_M` | WPF8 (unbounded) | at 2 048 |
|---|---|---|
| `technical_correctness` | κ_w 0.4, ρ 0.577, n 4 | κ_w 0.4, ρ 0.577, n 4 |
| `audience_fit` | κ_w 0.2286, ρ 0.5, **n 3** | κ_w **0.0**, ρ `None`, **n 2** |
| Goal κ_w | **0.3429** | **0.2667** |
| `excluded` on `audience_fit` | 1 × `protocol_error` | 2 × `output_truncated` |

A 12 B instruct juror hit 2 048 on two of eight rubric calls. **This is the row's most useful
finding and it arrived by accident** — the run existed only to put the operator's goal back, and it
falsified the default on the way. The default became `null`, the ADR's decision 2 was rewritten
around this table, and the operator's goal was then calibrated a third time, unbounded, to restore
WPF8's figures.

The lesson worth carrying: a budget that is "obviously generous" for a *task* is not obviously
generous for a *model*, and the only way to know is to run it against the juror you actually pinned.

## 5. Tests (Gate A)

* `tests/integration/test_jury_assembly.py::TestAJurorThatRanOutOfBudget` — three tests.
  `test_the_configured_output_budget_reaches_the_provider_and_truncation_is_named` scripts an answer
  that *would* parse and polls it at `max_output_tokens=2`; `FakeProvider` truncates it and derives
  `FinishReason.LENGTH`, so one test proves both decisions — the budget reaches the request, and the
  refusal is `output_truncated`. The other two hold the far sides: a juror that ended its turn with
  prose is still `protocol_error`, and `None` leaves the budget to the provider.
* `tests/integration/test_calibration_flow.py::TestAJurorThatNeverAnswered` — the exclusion reason
  reaches `excluded`, the warning is present, names the juror and `judge.max_output_tokens`, and
  survives the `latest_outcome` round trip; and a `protocol_error` run raises no budget warning.
  `_PartiallyRefusingJury` gained a `reason` field rather than a second double.

## 6. What was touched on the operator's machine, and put back

* `~/.config/freeweight/goals/wp6_goal/goal.json` — `judge.models` re-pinned to the reasoning juror
  for Gate B, then **restored** from the backup in the session scratchpad
  (`wpf9/goal.json.gemma.bak`). `goal_hash` is back to `sha256:aae8aaa9…`, the value WPF8 left it
  at. Every sample and grade is untouched throughout (`sync_goals` upserts by slug).
* The calibration ran three times: the reasoning juror at 2 048 (Gate B, §4), the instruct juror at
  2 048 (the restore, which is what falsified the default, §4.3), and the instruct juror unbounded
  (the actual restore, §6a).
* `freeweight.service` restarted four times — to pick up the new code, to free the GPU twice, and to
  pick up the `null` default.
* Nothing else. No database write outside the calibrations the row is about.

### 6a — The restored report, which is also this row's best evidence

Third run, instruct juror, budget unset, **351.2 s**. It reproduces WPF8's figures exactly:

| | WPF8 | WPF9 restore |
|---|---|---|
| `goal_hash` | `sha256:aae8aaa9…` | `sha256:aae8aaa9…` |
| `technical_correctness` | κ_w 0.4, ρ 0.5774, n 4 | κ_w 0.4, ρ 0.5774, n 4 |
| `audience_fit` | κ_w 0.2286, ρ 0.5, n 3 | κ_w 0.2286, ρ 0.5, n 3 |
| Goal κ_w | 0.3429 | 0.3429 |
| `audience_fit` `excluded` | `01M2977TGDE7RYSADQQRA0RJCK` — **`protocol_error`** | `01M2977TGDE7RYSADQQRA0RJCK` — **`output_truncated`** |

Same juror, same sample, same four coefficients — and **the only thing that changed is the name of
the refusal, which is now the true one.** WPF8's `protocol_error` on that sample was a mislabel: the
juror did not answer unusably, it ran out of window and never answered at all. That is decision 1
validated against real data rather than a scripted double, and it is a better proof than the Gate B
run that was designed for it.

The operator's goal is therefore back exactly where WPF8 left it, plus one sentence it did not have:

> 1 held-out sample(s) were dropped because the jury ran out of output budget before it answered
> (llamacpp/gemma-4-12b-it-Q4_K_M@sha256:0a270ec9fe6b) …

**Which means the warning fires on a normal, healthy run**, not only on a pathological one — a
juror that loses one sample in four to the served window is a real and previously invisible fact
about this goal's measurement. The operator may want to act on it; nothing here does it for them.

## 7. What this kickoff, and the roadmap row, got wrong

0. **"Whether FreeWeight bounds the judge's output at all"** was put as a design question and it
   turned out to be an empirical one. The kickoff's framing — *a juror that cannot answer inside its
   budget is a juror the goal should not have pinned* — is true of a reasoning juror and false of an
   instruct one at any budget a person would guess. §4.3 is the measurement; the answer is a knob
   with no default.
1. **"the verdict records neither the `finish_reason` nor the token spend."** Half wrong: every
   `JurorVerdict` has recorded `input_tokens` and `output_tokens` since the jury was built
   (`services/jury.py`, `_reported`), and they reach the `judge_verdicts` row. Only the
   `finish_reason` was missing — and this row decided not to add it, because the reason code carries
   the same fact through plumbing that already exists (§2.1).
2. **"a new `refused_reason`, **or** the `finish_reason` recorded beside `protocol_error`"** framed
   the two as equivalent-cost options. They are not: the second needs a `JurorVerdict` field, a
   `judge_verdicts` column, a migration, and a change to everything that reads the row.
3. **ADR-0099 does not say "thinking control is not a SetSpec capability" as a general rule** — its
   rule 5 says `thinking_control` does not enter `requires_capabilities`, which is a narrower claim.
   The fact that actually settles decision 3 is in ModelRack, not in that ADR: llama.cpp *refuses*
   the control outright.
4. **A `judge_verdicts` row is not where a calibration's refusal lands.** A goal *run* writes those;
   a calibration writes `calibration_reports`. The table is empty on the reference machine.

Two things found while working, neither this row's to fix:

5. **`docs/configuration.md` was already stale on FreeWeight `main`** — CI runs
   `generate_config_reference.py --check` and it was red before this row. Regenerating it is in
   `c215e32` and noted in the changelog's Fixed section. `sync_component_docs.py --check` was
   likewise red for two IdeaPress guides (`5a0a51a`).
6. **A pinned juror changed between two calibration runs needs a FreeWeight restart.** The first
   restore attempt failed in 16 s with eight `goal.juror_unreachable` / `PROVIDER_UNAVAILABLE`
   warnings: the previous juror's supervised `llama-server` was still resident at 11 240 MiB and the
   new one could not be launched beside it on a 16 GiB device. A restart freed it and the same
   request succeeded. Worth a row if an operator is expected to switch jurors without one.

## 8. Gate (Python 3.14.4, `~/ai/suite/FreeWeight/.venv/bin/*`)

`ruff format --check .`, `ruff check .`, `mypy src tests` (324 files), `lint-imports` (4 contracts
kept), `scripts/generate_config_reference.py --check`, `scripts/generate_openapi_snapshot.py
--check` and `scripts/sync_docs.py --check` — all green.
`pytest -m "not live and not performance"`: **2762 passed, 30 skipped, 31 deselected**; coverage
**89.67 %** against the 85 % floor. `git status --short` clean in both repositories at every commit.

**One environmental flake worth naming for the next person.**
`TestIdleDetection::test_a_quiet_machine_proceeds` failed once, during the gate run that overlapped
this row's own live calibration, and passed on a quiet GPU immediately after with no code change.
The test builds `_collector(cpu_percent=1.0)` with `gpus=0`, which constructs
`TelemetryCollector(host=ScriptedHostReader(...))` with **no** `gpu=` argument — so the GPU half is
not scripted and reads the real device. A busy GPU makes a "quiet machine" test fail. It is a real
test defect (a unit test that reads the host), not a flake to retry past, but it is not this row's.

The `tests/unit/golden/config_schema.json` golden gained the new key by hand-insertion in the file's
own formatting (19 added lines) rather than by re-serialising the document, which would have
reordered 598 lines for one field.
