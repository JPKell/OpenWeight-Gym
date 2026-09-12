# WPF7 Handoff — IdeaPress honours a cancel across its retry, and fits the window it is served

**Row:** WPF7 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended · **Model:** Claude
Opus 5 · **Kickoff:** `history/prompts/wpf7-ideapress-cancel-and-reasoning-budget.prompt.md`
(wave note `history/prompts/wave1-wpf7-summary.md`) · **Ships:** unreleased, no version bump ·
**Branch:** IdeaPress `row/wpf7-cancel-reasoning-budget`, WeightRoom `main`.

## 1. What shipped

| Repository | Commit | Gate | What |
|---|---|---|---|
| IdeaPress | `e25af5b` | A | A cancel is checked before **every** model call, the transport retry's included, and a discarded call is an attempt row of its own (`transport_call`, migration `0012`) |
| IdeaPress | `091d991` | B | `inference.ollama.served_context_tokens` (default 32768) is sent as `num_ctx`, a stage whose budgets exceed it is refused **before the run**, and `doctor` reports the same check |
| IdeaPress | `f86e88b` | B | `structured_output_tokens` defaults to 16384 and `project_review_context_budget_tokens` to 14336 — the measured reasoning need, and the review context that fits beside it |
| IdeaPress | `305b29e` | C | `inference.ollama.timeout_seconds` defaults to 900, with a `doctor` check that the budget can be generated inside it |
| IdeaPress | `5ec90a6` | C | the configured backend timeout **reaches** the request: `StageLimits.timeout_seconds` was 300 and nothing ever set it, so the setting was dead configuration |
| IdeaPress | `3627928` | C | the retry of an empty generation asks for the answer **without reasoning**, where the backend declares the control |
| IdeaPress | merge | — | `row/wpf7-cancel-reasoning-budget` merged into `main` after Gate C |
| WeightRoom | `42559f4` | A | `apps/ideapress/data-model.md` (the column), `workflows.md` §6.2 (the retry and the cancel), §8 |
| WeightRoom | `e02a45c`, `592433a` | B | `apps/ideapress/spec.md` §15 (the measurements, the served-context rule, the measured reasoning need), `workflows.md` §6.2 (the refusal), the two regenerated guides |
| WeightRoom | `b6e24f8` | A | the recorded IdeaPress attempts in the console's fixtures carry `transport_call` |
| WeightRoom | (this file) | C | `apps/ideapress/spec.md` §15 and `workflows.md` §6.2 on the reasoning-suppressed retry |

Gate every time, and once more on `main` after the merge: Python 3.13.15 at
`/home/jpk/ai/suite/IdeaPress/.venv/bin/python` — `ruff format --check .`, `ruff check .`,
`mypy src tests` (220 files), `lint-imports` (4 contracts),
`pytest -m "not live and not performance"` → **1357 passed, 6 skipped, 31 deselected**; coverage
**90.79 %** against the 85 % floor.

## 2. The decisions this row was asked to make

### Decision 1 — where the cancel check goes, and what a cancel during the first empty generation leaves

**At the one door to a model, immediately before every call** (`InferenceGateway._generate`), not in
the stage bodies. WP6's cancel *was* read by the stage body — and the second call it did not stop
was made inside the gateway's empty-generation retry, one level below anything a body can see. The
runner hands the gateway its own checkpoint (and a provenance sink) at `begin_run`, so the gateway
raises the runner's `StageCancelled` without importing it: the door stays below the runner, and a
door that wrote database rows would be two things.

A cancel during the first empty generation therefore leaves: the run **`cancelled`**, **one** model
call made, and **one** attempt row for that call — `transport_call` 1, outcome `provider_error`,
`error_code` `EMPTY_GENERATION`, with its tokens. No second call.

### Decision 2 — the budget for thinking models

**The output budget was never the binding constraint; the served context was.** The measurement is
what settles it, and it inverts the kickoff's framing.

On the reference machine Ollama serves **8192** tokens (`OLLAMA_CONTEXT_LENGTH` in
`ollama.service`, the operator's memory cap, ADR-0119 decision 1). A prompt, the model's reasoning
and its answer all come out of that one window, so `num_predict` can never reach
`structured_output_tokens = 8192`: the prompt has already spent part of it. IdeaPress's own failure
message — *"Raise the stage's output budget"* — asked for the one thing that could not help, and
WP6 passed that advice to the operator in good faith (§7 item 4 of `WP6_HANDOFF.md`).

Measured today on `qwen3.5:9b-q8_0`, the operator's binding for every stage, against the real
prompts of WP6's own project (`01M28ZYHH7GS9RGX5GR0JVEG3F`, read-only):

| Stage | Prompt (tokens) | Reasoning before the first word | Answer | Served | Outcome |
|---|---|---|---|---|---|
| `critique`, U-01 | 2 289 | ≈ 1 700 (6 668 chars) | 237 chars | 8 192 | answered in 49 s |
| `critique`, U-03 | 4 723 | ≈ 4 300 (17 238 chars) | 334 chars | 8 192 | answered in 100 s, the window shifted |
| `audit_fast`, U-03 | 5 581 | ≈ 4 300 (17 315 chars) | 287 chars | 8 192 | answered in 120 s |
| `revise`, U-01 | 538 | ≈ 5 300 (21 427 chars) | 1 011 chars | 8 192 | answered in 130 s |
| `revise`, U-01 | 538 | ≈ 7 000 (28 163 chars) | 788 chars | 16 384 | answered in 168 s |
| `project_review`, 5 units | **12 777** | — | — | 8 192 | **no text at all**, `length`, 174 s |
| `project_review`, 5 units | 12 777 | ≈ 11 800 (47 316 chars) | 1 757 chars | 16 384 | answered in 300 s |

So reasoning costs this model between 1 700 and 11 800 tokens on IdeaPress's structured prompts, and
`project_review`'s assembled context alone (12 777 tokens, under its 24 000-token budget) does not
fit an 8 192-token window at all — Ollama truncated the prompt, and the model spent what was left
reasoning.

**The choice: IdeaPress states the window it needs, asks for exactly that, and checks its budgets
against it.** `inference.ollama.served_context_tokens` (default **32768**) is sent as `num_ctx` on
every request — one value for every stage, because Ollama reloads a model when a request asks for a
different context length, and a reload per stage is the 9.5 GB cost ADR-0038 exists to avoid. `0`
keeps the server's own default and turns the check off, because IdeaPress cannot read
`OLLAMA_CONTEXT_LENGTH` from another process and a check with no figure would be a guess.

Not a larger output budget, and not a per-stage one: with the window stated, one output figure and
one context figure per stage class are enough, and a second knob per stage would be a second way to
be told the same refusal. `structured_output_tokens` stays at 8192 and stays runtime-changeable
exactly as ADR-0100 left it; `served_context_tokens` is **configuration-only**, because changing the
served window mid-process means a model reload, not a value a stage re-reads.

**`project_review_context_budget_tokens` drops from 24000 to 20480**, so the shipped set is
self-consistent: 20480 + 8192 + 512 of prompt overhead = 29 184 ≤ 32 768. A file that sets the key
keeps its value. Memory measured before choosing the default: the 9.7B Q8_0 model resident at
`num_ctx` 32 768 holds **11 620 MiB of 16 311 MiB** on the reference card (24 576 → 11 469 MiB,
16 384 → 10 977 MiB, 8 192 → 9 218 MiB), and ADR-0119's cgroup cap (`MemoryMax=24G`,
`MemorySwapMax=0`) is what keeps a large window from becoming a host thrash.

**Thinking control is used in exactly one place: the retry.** A budget large enough for most
prompts is not large enough for a reasoning loop, and Gate C proved it twice — `project_review`
produced no text in 16 384 tokens, twice, 375 seconds a call, on a 32 768-token window. The model was
not short of room; it was not stopping. A second *identical* request cannot help, so the retry now
asks for the answer with the model's reasoning suppressed where the backend declares the control
(`BackendCapabilities.thinking_control`, `StageLimits.think`; Ollama declares it, and ModelRack
refuses the field on providers that cannot carry it rather than ignoring it). Live: the retry answered
in 257 tokens and 6 seconds, and the attempt carries
`empty_generation_retried: … with reasoning suppressed` so no reader mistakes it for a reasoned answer.

**Thinking control as a general setting was measured and rejected.** `qwen3.5:9b-q8_0` *does* honour Ollama's
`think: false` — probed directly, 2 output tokens and no reasoning at all — and ModelRack already
carries `SamplingParameters.think`, so adopting it would have been small. It is not adopted because
I6 found the control unreliable across models (8 of 10 honoured it; `deepseek-coder-v2` crashed
Ollama) and I3 measured *worse* answers with reasoning off, which is the wrong trade for the stages
that audit and critique someone's work. The served-context fix is model-independent and needs no
per-model table.

### Decision 3 — refusing before the run

**Yes, and on the arithmetic rather than on a remembered measurement.** A stage is refused when its
assembled-context budget + its output budget + 512 tokens of prompt overhead exceed the served
window — checked in `start_plan` and `start_stage`, before any run row is written, and reported by
`doctor` as `served context` from the same function, so the operator cannot be told two different
things. "A binding whose *last measured thinking* exceeds the budget" was the kickoff's shape and it
was rejected: a per-binding measurement is a moving number that ages, while the budgets are
configuration and are knowable in advance for every stage, bound model or not.

The refusal names all four numbers and both remedies — lower a budget, or serve a larger window —
because which one is right is the operator's memory decision (ADR-0119 decision 3), not IdeaPress's.

## 3. How it works now, in the code

**The cancel.** `StageRunner._run` calls `gateway.begin_run(run_id, model_hint=…,
checkpoint=lambda: self.checkpoint(task), record_discarded=self._discarded_call_recorder(task))`.
Inside the gateway, `_generate(request, backend=None)` is the only place a backend's `generate` is
called — `run`, `_fall_back` and `_retry_empty_truncation` all route through it — and it calls the
checkpoint first. `tests/unit/test_import_boundaries.py::test_only_the_gateway_calls_a_backend_to_generate`
still holds: nothing outside `services/inference.py` reaches a backend.

**The attempt rows.** `record_attempt` gained `transport_call: int = 0`, and the column joins
`uq_attempts_run_unit_stage_attempt_round` (migration `0012`, reversible — verified by downgrading
to `0011` and upgrading again, the constraint intact in both directions). `0` is the call whose
answer the attempt kept, which is what all nine existing call sites pass and what every pre-existing
row is. The gateway records `1` for a discarded empty generation and `2` for a retry that was also
empty, each with the call's tokens, so the budget debit and the egress decision that ride on
`record_attempt` (row J1) now happen for calls a run paid for and threw away.
`GET /projects/{id}/tasks/{task_id}` and the unit provenance report carry `transport_call`.

**The fit check.** `services/context_fit.py` holds the arithmetic: `needed_context_tokens` =
assembled-context budget + output budget + `PROMPT_OVERHEAD_TOKENS` (512), where the output budget
is `structured_output_tokens` for a structured stage and `output_budget_tokens(target_words, …)` for
`draft`, `repair` and `revise`. `context_shortfall` returns the sentence or `None`;
`served_context_tokens` returns 0 for any backend but `ollama`, because in `loadcoach` and
`openai_compatible` mode the window belongs to the service on the other side (ADR-0040).
`start_plan` checks `requirements` and `outline`; `start_stage` checks the stage it is starting,
passing the longest `target_words` among the units it will write. `doctor`'s `served context` finding
reads the same function over every model-using stage.

## 4. Tests

| Test | What it holds |
|---|---|
| `tests/integration/test_cancel_across_the_retry.py` (4) | a cancel between the two calls of a retry ends the run `cancelled` with **one** call made and one attempt row; a discarded call is a row beside the answer that was kept, with the same attempt number; two empty generations leave rows `1` and `2` with their error codes; a stage whose budgets cannot fit is refused before any run row is written |
| `tests/unit/test_served_context_fit.py` (8) | the shipped defaults fit the window they ask for; a stage that cannot fit is named with every number; the needed figure is context + output + prompt; a text stage grows with `target_words`; an unstated window and a non-`ollama` backend are not checked; the setting reaches Ollama as `num_ctx`, and `0` asks for nothing |
| `tests/unit/test_doctor.py` (+3) | `served context` fails naming the stage, passes on the defaults, and warns — rather than passing — when the window is not stated |
| `tests/unit/test_config_1_0_compatibility.py` | the new key is listed as WPF7's and moves no 1.0 value |

## 5. Gate C — the live proof

All of it on the reference machine, from the operator's own console at `https://10.77.10.84:8769`
(`wr-gym 1.0.0`), against IdeaPress `1.5.0` serving this branch under `ideapress.service`, every stage
on IdeaPress's configured binding `ollama/qwen3.5:9b-q8_0` and **no per-run model hint anywhere**.
One live model load throughout. Project `01M29HZ6CSKCJH81FR8DTSRHQG`, 2026-09-11.

| Step | Task | Outcome |
|---|---|---|
| Create + plan | `01M29HZ6GT9AEZZRQXBYV7EVF7` | **completed** in 3 m 31 s; 2 units, 6 blocking requirements |
| Draft (first attempt) | `01M29J5MJQ6YXNB4410G1AWVWG` | **failed** `PROVIDER_TIMEOUT` — the fix that came out of it is §2's timeout pair |
| Draft (resumed) | `01M29MAAY2TYHQ1WVRPM68N3SC` | **completed** in 11 m 16 s; **both units committed**, no pause, no discarded call |
| `project_review` (first attempt) | `01M29MYZ60F2206QZCMKFBMDN6` | **failed** `CONTEXT_LIMIT_EXCEEDED`: no text in 16 384 tokens, **twice**, 375 s a call — and **both calls recorded**, `transport_call` 1 and 2 |
| `project_review` (with the reasoning-suppressed retry) | `01M29P130SB7E7GA9SWE4J0BM7` | **completed**: first call 16 384 tokens / 381 s empty and recorded; retry with `think: false` answered in **257 tokens / 6 s** |
| Export + download | — | markdown written, downloaded through the console: `200`, `text/markdown`, `attachment; filename="01M29HZ6CSKCJH81FR8DTSRHQG.md"`, **8 025 bytes** |
| Cancel during a multi-call stage | `01M29PF5RN7Y060JP7B4CC19K8` (`revise` U-01) | pressed 40 s into the call → **`cancelled`** at the next model-call boundary, `cancelled_at` set, and the call it had already made recorded (2 983 tokens, 67 s) |
| Cancel during `project_review`'s first call | `01M29QEVMJGGADQFD6PW4X0SA7` | pressed **1 s** after the run started, with the first call already in flight → that call recorded (`transport_call` 1, 16 384 tokens, 375 s), then **`cancelled`** at the retry boundary with **no second call** |

**That last row is WP6 finding 8, run again on the fix.** WP6: a second 2 m 47 s call after the
cancel, the run `failed`, **0 attempts**. Now: no second call, the run `cancelled`, one attempt
recorded with what it spent.

Seen live along the way, and the reason two more commits exist:

* **A draft's first call after a cold load spent all 8 792 of its output tokens thinking** and
  returned nothing (`transport_call` 1, `EMPTY_GENERATION`, 200 s, prompt `stages.draft.write`,
  unit U-01). Its retry produced the draft. Before this row those 8 792 tokens were recorded nowhere.
* **Ollama served what IdeaPress asked for**: `/api/ps` reported `context_length: 16384` during the
  measurements and **`32768`** for every Gate C stage, against the machine's `OLLAMA_CONTEXT_LENGTH`
  of 8 192.
* Console audit rows for the whole run: `ideapress.project_create`, `ideapress.plan_run`,
  `ideapress.stage_run` (five, one `refused` — `project_review` with fewer than two committed units,
  which the console rendered in IdeaPress's words), `ideapress.export_write`.

**One deviation from the kickoff's wording.** A first project, `01M29FZG0CPYQKMFS74E1H07YJ`, paused
both its units — not on a budget, but on ADR-0039's attestation gate: my brief asked for three habits
in two sections, so a blocking requirement no deterministic check could settle was never attested.
The brief was mine and the gate was right, so the proof was re-run on a coherent brief rather than
argued around. Both projects were kept (§7 item 7).

## 6. What this kickoff got wrong

1. **"A project on IdeaPress's configured bindings … without a stage exhausting its output budget."**
   The budget was not the constraint. The served context was, and the output budget was *too small*
   rather than too large — two separate numbers, both wrong, and neither visible in the failure
   message the operator was given. The kickoff (and WP6's note §7 item 4, and IdeaPress's own
   `CONTEXT_LIMIT_EXCEEDED` text) all pointed at `workflow.structured_output_tokens`, which on this
   machine could not be honoured at all: with 8 192 served, no request could ask for 8 192 output.
2. **"Measure `qwen3.5:9b-q8_0`'s thinking tokens … then choose: a larger default, a per-stage
   budget, runtime-changeable or not, or a thinking control."** The list has no entry for the answer
   — *state the served window and fit the budgets to it* — and the four it does list are all about
   the output figure alone. A larger default was needed as well, and is here; a per-stage budget was
   not, because with the window stated one figure per stage class suffices.
3. **"A `project_review` cancelled during its first call that ends `cancelled`."** True as written,
   but only because the first call came back empty and the retry is now a boundary: the cancel landed
   there. A `project_review` whose first call *answers* makes one model call, so a cancel arriving
   mid-call has no later boundary and the run ends `completed` — correct behaviour for "honoured at
   the next model-call boundary", and not what the sentence implies. Worth knowing: the cancel pressed
   **one second** after the run started was already too late to precede the first call, because the
   console → API → context assembly path is well under a second.
4. **"`workflow.structured_output_tokens` (8 192) is config-only"** (WP6's observation, carried into
   this kickoff as context). True, and it stays config-only for the served context while
   `structured_output_tokens` remains runtime-changeable — but neither fact was the reason the stages
   failed, so making the budget runtime-changeable would have fixed nothing.
5. **Ollama's token accounting was assumed sound.** It is not, and this row did not fix it: on a
   structured request Ollama returns the model's reasoning in a separate `thinking` field and reports
   `eval_count` **without** it (critique: 57 output tokens reported beside 6 668 characters of
   reasoning), while on an unstructured one the reasoning is counted (revise: 5 309 tokens for 21 427
   characters). So a thinking model's attempt rows under-report what the structured stages spent, and
   every budget debit under them is a floor rather than a total. A ModelRack question, not an
   IdeaPress one (§7).

## 7. For the operator

1. **Set your own console password.** It was reset at the start of Gate C
   (`wr-gym operator password jpk --password-stdin`, one session revoked) and its value is in this
   session's scratchpad, which goes with the session. Run `wr-gym operator password jpk`.
   That reset also revoked whatever console session another WPF row was holding at 17:22 PDT.
2. **Your IdeaPress database is at revision `0012`.** The restart migrated it, and the automatic
   pre-migration backup is
   `~/.local/share/ideapress/backups/pre-migration-0011-20260912T002126144283Z.sqlite3`.
3. **Two defaults moved, and they change what IdeaPress asks your Ollama for.** Every request now
   carries `num_ctx = 32768` (`inference.ollama.served_context_tokens`) instead of inheriting your
   `OLLAMA_CONTEXT_LENGTH=8192`, and the structured stages ask for up to 16 384 output tokens. On your
   card that is 11.6 GB resident of 16.3 GB, measured; `ollama.service`'s `MemoryMax=24G` and
   `MemorySwapMax=0` still stand, and ADR-0119's reasoning is untouched — **if you want the smaller
   window back, set `served_context_tokens = 8192` in `~/.config/ideapress/config.toml`** and
   IdeaPress will then refuse the stages that cannot fit it, by name, before they run.
4. **`ideapress doctor` gained `served context`**, and its `output budget` check now warns below
   16384 rather than below 8192.
5. **Ollama under-reports what a thinking model spends on the structured stages** (§6 item 5). Every
   `input_tokens`/`output_tokens` figure and every budget debit for `audit_*`, `critique` and
   `project_review` on `qwen3.5:9b-q8_0` is a floor, not a total. Worth a ModelRack row: the
   provider has `GenerationResult.thinking` and `usage.thinking_tokens` and could count what Ollama
   separates.
6. **The console's attempts table does not show `transport_call`.** Two rows of one attempt are told
   apart only by their outcome (`completed` beside `provider_error`). The field is in the API and the
   fixtures; showing it is a WeightRoomGym display question.
7. **Two projects were left on the machine** by Gate C, at your choice of keeping everything:
   `01M29FZG0CPYQKMFS74E1H07YJ` (both units paused on ADR-0039's attestation gate — my brief asked
   for three habits in two sections, so a blocking requirement nothing mechanical could settle was
   never attested) and `01M29HZ6CSKCJH81FR8DTSRHQG` (§5).

## 8. Two things deliberately not done

* **`InferenceGateway.stream` has no checkpoint**, because no stage calls it: nothing outside the
  gateway reaches `stream` at all (token streaming to the UI replays IdeaPress's own event log, not a
  provider stream). A checkpoint there would guard a path with no caller.
* **`export`'s `ExportAttempt` payload does not carry `transport_call`.** The export is a versioned
  SetSpec-shaped document, and adding a field to it is a version question, not a bug fix. A discarded
  call still appears in an export as an attempt with outcome `provider_error`, which is honest if
  terser than the API's answer.
