# G2 — LoadCoach's tool wire: `/generate` carries tool definitions and `tool_calls`, and the corrective retry survives an empty answer

**Row:** G2 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-04/05.
**Model:** Opus 5 · high, as scheduled. Whole, daytime, no split. No deviation.
**Ships:** nothing. LoadCoach and PromptCadence both gain `## [Unreleased]` sections. No bump, no
tag, no publish, and **nothing was pushed** — three repos are ahead of `origin` and that is the
operator's to resolve.
**Exit conditions:** all eight met. The demonstration (§6.4) completed on real LoadCoach + Ollama
with gpt-oss:20b and the shipped defaults: six declared sandboxed tool calls across the planned and
bypassed pair, every one `ok`, zero deviations.

---

## 1. Gate results — interpreter and exact invocations (M5C-13)

Two repositories, two virtualenvs, two interpreters. Both named because they differ.

**LoadCoach** — `/home/jpk/ai/suite/LoadCoach/.venv`, **CPython 3.14.4**, `modelrack 0.5.0`,
`setspec 0.4.0`:

```bash
.venv/bin/python -m ruff format --check .     # 194 files already formatted
.venv/bin/python -m ruff check .              # All checks passed!
.venv/bin/python -m mypy src tests            # Success: no issues found in 174 source files
.venv/bin/lint-imports                        # Contracts: 4 kept, 0 broken.
.venv/bin/python -m pytest -q -m "not live and not performance"
                                              # 886 passed, 3 skipped, 15 deselected
```

**PromptCadence** — `/home/jpk/ai/suite/PromptCadence/.venv`, **CPython 3.13.15**:

```bash
.venv/bin/python -m ruff format --check .     # 136 files already formatted
.venv/bin/python -m ruff check .              # All checks passed!
.venv/bin/python -m mypy src tests            # Success: no issues found in 132 source files
.venv/bin/lint-imports                        # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -q -m "not live and not performance"
                                              # 1015 passed, 2 skipped, 2 deselected
```

**A note on the LoadCoach venv, because it changed.** `mypy src tests` failed on arrival with three
errors in `tests/simulation/simulator.py` — `SimulatedProvider` missing `list_adapters` and
`register_adapters`. The cause was environmental, not the row's: `modelrack` was installed
**editable against `/home/jpk/ai/suite/py/ModelRack/src`**, whose working tree is at `0.6.0` and
whose `Provider` protocol has grown since, while LoadCoach's pin is `modelrack>=0.5,<0.6`. The venv
was therefore reinstalled from PyPI at the pin (`pip install "modelrack==0.5.0"`), which is what CI
installs, and the errors went with it. Nothing in this row needs a ModelRack newer than `0.5.0`:
`ToolDefinition`, `ToolCall` and `GenerationRequest.tools` are all in the `v0.5.0` tag. **If the
operator wants the editable cross-repo install back, that is one command, and it will re-break
`mypy` until LoadCoach's pin moves — which is an H1 question, not this row's.**

## 2. The six gates, as commits

| Gate | Repo | Commit | What it made true |
|---|---|---|---|
| A | docs | `3d824b4` | api.md §4/§10/§12, data-model.md, routing.md §4, spec.md §13/§14, **ADR-0075** accepted and indexed |
| A | LoadCoach | `dd2112a` | The byte-identical mirror, `cmp`-proved |
| B | LoadCoach | `ec71ce9` | `tools` inbound, the routing rule, the compatibility golden |
| C | LoadCoach | `8815dae` | `tool_calls` inbound, the four refusals, native replay |
| D | LoadCoach | `f5f3b81` | The corrective never replays an empty answer; a refused request writes its attempts |
| E | LoadCoach | `5af6b12` | `tools.plan` measured and left alone; the thinking-control finding |
| F | PromptCadence | `f85c236` | The fake and the contract, with the real refusals |
| F | PromptCadence | `bce7edc` | The client sends the allowlist, the `[tool_calls]` rendering is deleted, and the assembler is fixed |
| — | docs | `fe95179` | The G2 row marked Done, and this handoff under `docs/history/` |

Docs mirroring: `api.md`, `data-model.md`, `routing.md`, `spec.md` copied into
`LoadCoach/docs/apps/loadcoach/` and `cmp`-clean on all four. ADR-0075 lives only in the workspace
`docs/adr/`, which is the mirror's existing scope (LoadCoach's copy has no `adr/` directory and
links out to `../../adr/`).

## 3. The four decisions of §0.2, and why

### 3.1 What a request carrying `tools` does to routing — **ADR-0075**

**A non-empty `tools` imposes `tool_use` as a hard constraint on that request**, unioned with the
task profile's `requires_capabilities`. It filters; it never scores.

Expressed through the machinery that already existed rather than beside it:
`RouteRequest.require_capabilities` is unioned into the merged constraints inside `route()`. A
union can only narrow, so it cannot collide with `_merged_constraints`' refusal to loosen, and no
new rejection path was created.

* **The rejection reason string is the existing `capability_unsupported`**, not a new one. Routing's
  reasons are a caller-visible vocabulary and this is the same fact — *this candidate cannot use
  tools* — seen from a different angle. What a caller could not otherwise tell is **whose**
  requirement it was, so the rejection detail gains
  `required_by: "request" | "task_profile"`. With `general.chat` or `tools.plan`, whose profiles
  require no `tool_use` at all, `"request"` is the only thing that makes the rejection legible.
* **`tools: []` is `tools: null` is absent.** Identical in every respect including routing. A
  caller that computed an empty tool set gets exactly the request it would have sent without the
  field. Asserted.
* **The provider edge is unreachable through `/generate`.** ModelRack raises `CapabilityUnsupported`
  when tools reach a provider that has not declared `tool_calling`; after this rule routing refuses
  first, and a test asserts `NoEligibleModel` arrives while `provider.requests == []`.

### 3.2 How strictly the wire validates a transcript — **strictly, and yes to the fourth rule**

Four rules, each a `VALIDATION_ERROR` carrying `details.fields[0].path`:

| Rule | Whose | Field |
|---|---|---|
| `tool_calls` on a non-assistant turn | ModelRack's, surfaced | `messages[i].tool_calls` |
| a `tool` turn with no `tool_call_id` | ModelRack's, surfaced | `messages[i].tool_call_id` |
| a turn with neither content nor calls | ModelRack's, surfaced | `messages[i].content` |
| a `tool_call_id` naming no earlier call | **LoadCoach's own** | `messages[i].tool_call_id` |

The first three are **surfaced, not duplicated**: `messages_of` builds each `Message`, lets
ModelRack apply its own rules, catches its `ValidationError` and re-raises LoadCoach's with the
`fields` shape a caller already gets from a schema failure. Copying the rules into LoadCoach would
have created two places for them to drift.

The fourth is the recommendation, taken. An unmatched id is a caller bug; left alone, a provider
turns it into a confusing model failure well downstream. It had a real consequence in gate F: a
replayed `TOOL` turn now has to carry the **model's** call id, and PromptCadence's own invocation
ULID stays on the row where it belongs. That is not a cost of the rule — it is the rule finding a
latent defect, since a provider that matches results to calls needs the id the model chose.

**`raw_arguments` is carried, without a second wire field.** `arguments` is `object | string`: an
object is the parsed form, a string is the raw text the model produced when its arguments were not
a JSON object, and it maps to `ToolCall(arguments={}, raw_arguments=…)`. One field, two shapes,
and a malformed call stays diagnosable on replay instead of being smoothed into "the model asked
for nothing". G1 saw exactly the string case.

### 3.3 Which status a construction-time refusal lands in — **`failed`, `VALIDATION_ERROR`, attempts written**

It is not a provider failure (nothing was called) and not a routing failure (no candidate was
rejected), so neither `ALL_CANDIDATES_FAILED` nor `NO_ELIGIBLE_MODEL` is honest. The job becomes
`failed` with `error_code = VALIDATION_ERROR` and `completed_at` set, and — the part that matters —
**every attempt already made is committed** before the error is raised. `_execute_attempts` returns
the refusal alongside its records instead of letting it propagate; `execute` persists and then
re-raises.

No new `job_attempts.outcome` value was needed: a construction refusal is not an attempt, because
no provider was called. What was being lost was the rows for the attempts that *were*.

### 3.4 `tools.plan`'s output budget — **measured, and left at 4096**

See §4. The second half of item 4 — a profile field for reduced thinking — is a **finding, not a
change**: see §5.

## 4. The measurement (gate E)

Six samples per setting against **gpt-oss:20b**, `format=json`, `temperature=0.1`, with
PromptCadence's `planner.draft` 1.1.0 prompt rendered for the G1 task (287-character system,
1826-character user — G1's "1.6k" prompt, as it renders today with five tools and three tiers).
Taken **straight through Ollama** so that nothing but the budget varied; LoadCoach's routing could
not have held the model constant, and the lever under test is a sampling parameter, not a routing
one.

| `max_output_tokens` | empty | rate | median latency | every empty answer |
|---|---|---|---|---|
| **4096 (shipped)** | 1 / 6 | **17 %** | 58 s | `done_reason=length`, `eval_count` 4096, 18 852 thinking chars |
| 8192 | 3 / 6 | **50 %** | 171 s | `done_reason=length`, `eval_count` 8192, 31 266–34 459 thinking chars |

**The decision is to change nothing**, and the numbers are why: doubling the budget tripled the
median latency and doubled the failure rate. The model fills whatever budget it is given with
reasoning and runs out later, at greater cost. The table is recorded in the changelog and in a
comment beside the value in `task_profiles.toml`, so the next person to reach for this lever reads
the result before pulling it.

**This closes G1's open question.** G1 could not say what finish reason sat behind an empty
planning answer, because the refused corrective threw the attempt rows away. It is **`length`**,
with `eval_count` exactly equal to the budget — measured directly here, and now recordable through
LoadCoach as well, because gate D writes those rows.

The raw samples are in the session scratchpad (`measure_A.jsonl`, `measure_B.jsonl`); the
measurement harness is `direct_ollama.py` beside them. Nothing about it belongs in either repo.

## 5. The thinking-control finding (item 4, lever 2) — **ModelRack's, not fixed here**

**ModelRack's Ollama adapter declares `thinking_control = True` and exposes no way to ask for it.**

* `providers/ollama.py:156` declares the flag.
* `SamplingParameters` (`types.py:365`) has no `think` field.
* `OllamaProvider._build_request` never emits Ollama's top-level `think` key, and
  `runtime_profile.provider_options` merges into `options`, where `think` does not live.

So the capability is declared and unreachable — the shape ADR-0007 rule 2 exists to prevent, from
the request side rather than the response side. A `tools.plan` profile field for a control that
cannot be sent would be configuration that lies, so none was added.

**Scheduled by the operator at the interview (2026-09-05): into H1**, ModelRack P8. A
`SamplingParameters.think: bool | None = None` — tri-state, so an unset request is byte-identical
to today's — sent as the top-level `think` key by the Ollama adapter and refused with
`CapabilityUnsupported` by adapters declaring `thinking_control = False` (llama.cpp and
openai-compatible both do). Whether a task profile may then *ask* for it is a later row: a profile
field for a control that cannot be sent would be configuration that lies.

## 6. What the live stack showed

LoadCoach `1.0.0` (this working tree) served on `127.0.0.1:8766` from a scratch data directory
against Ollama 0.32.13, 15 models. PromptCadence `0.9.0b0` on `8768` from a scratch data directory
with the **shipped defaults and no `PROMPTCADENCE_TIERS__*` overrides**.

### 6.1 The four refusals, against the real server

Posted directly to the running LoadCoach, not to the fake:

```text
$ curl -s -X POST http://127.0.0.1:8766/api/v1/generate -d '<each body>'
VALIDATION_ERROR [{"path": "messages[0].tool_calls", "problem": "Only an assistant message may carry tool_calls; got role 'user'. …"}]
VALIDATION_ERROR [{"path": "messages[0].tool_call_id", "problem": "A tool message must carry the tool_call_id it answers; got None. …"}]
VALIDATION_ERROR [{"path": "messages[0].content", "problem": "A assistant message must carry content or tool_calls; got neither. …"}]
VALIDATION_ERROR [{"path": "messages[1].tool_call_id", "problem": "no earlier assistant turn requested the call 'c9'; a tool result answers a call the model made."}]
```

The fake returns the same code and the same four `path` values, which is what
`test_the_fake_refuses_every_transcript_the_real_server_refuses` asserts. **That is how the fake was
verified against the real server rather than against itself.**

### 6.2 `tiers check`

```text
$ promptcadence tiers check
loadcoach http://127.0.0.1:8766: 3 profile(s) resolve in LoadCoach, tools.plan included
  ✓ local_fast       tools.agent.local_fast         version 1.0.0
  ✓ local_large      tools.agent.local_large        version 1.0.0
  ✓ (planner)        tools.plan                     version 1.0.0
```

### 6.3 The first planned run — what it proved, and the defect it exposed

`promptcadence run "Summarize the files in ./notes" --follow`, trajectory
`01M1R5XWB1CEWMGRWGY35YWKSM`, with a `./notes` directory of two markdown files in the trajectory's
workspace. It ran to `turn_overrun` (8/8 turns) with a scoped re-approval parked — correct
behaviour for a step that could not make progress, and incidentally the **first loop-level
`turn_overrun`**, which G1 §15 recorded as domain-tested only.

It proved most of the wire. The job body LoadCoach actually received, read back out of its
`jobs.request_json`:

```text
tools: [{"name": "list_dir", "description": "List a directory in the workspace, sorted by name. …",
         "parameters": {"type": "object", "properties": {"path": {"type": "string", …
  user      'Summarize the files in ./notes'                       | calls: null
  user      "You are executing step s1 of an approved plan …"      | calls: null
  assistant ''  | calls: [{"id": "ollama-227744599217020-0", "name": "list_dir", "arguments": ""}]
  tool      "Tool 'list_dir' — args_invalid: …"                    | tool_call_id: ollama-227744599217020-0
  … (seven such pairs)
```

* The definitions travelled, with the registered description and the real JSON Schema.
* **An assistant turn with no content replayed natively** — `content: ''` carrying `tool_calls`,
  with no `[tool_calls]` text anywhere in the transcript.
* The `TOOL` turns carry the **model's** call ids and LoadCoach accepted them, so the fourth
  transcript rule holds against a real trajectory.
* The model, finally told what `list_dir` is, **called `list_dir`** — none of G1's invented
  vocabulary.

Every call was nevertheless refused, and the cause was a defect in PromptCadence's own assembler,
not in the wire: §7. Note the `"arguments": ""` above — that is the defect visible on the wire.

### 6.4 The exit demonstration — **both paths, completed**

Re-run after the §7 fix, with the GPU free. Shipped defaults, no `PROMPTCADENCE_TIERS__*`
overrides, scratch data directories for both applications. Both trajectories routed to
**`ollama/gpt-oss:20b@sha256:17052f91a42e`** — G1's model, so this is like-for-like with G1 §10.4.

**Planned** — `promptcadence run "Summarize the files in ./notes" --follow`:

```text
trajectory   01M1R81X0MJ74EJ861496X9PHG
[1] trajectory.created
[2] trajectory.claimed
[3] plan.drafted — attempt 1, invalid, 0 step(s)
[4] plan.drafted — attempt 2, valid, 1 step(s)
[5] plan.approved
[6] intent.minted — step s1 (policy, revision 1)
[7] step.started — step s1
[8] turn.started
[9] budget.debited
[10] turn.completed — continue
[11] tool.call.started
[12] tool.call.completed
[13] turn.started
[14] budget.debited
[15] turn.completed — continue
[16] tool.call.started
[17] tool.call.completed
[18] turn.started
[19] budget.debited
[20] turn.completed — continue
[21] tool.call.started
[22] tool.call.completed
[23] turn.started
[24] budget.debited
[25] turn.completed — complete
[26] step.completed — step s1
[27] trajectory.completed
trajectory   01M1R81X0MJ74EJ861496X9PHG
state        completed
class        confidential
bypass       False
cause        the provider declared finish_reason=stop
```

`tool_call_records` for that trajectory — **three declared sandboxed calls, every one `ok`**:

```text
run_command | ok | {"argv":["bash","-lc","ls -1 ./notes"]}                       | isolation: container | 257 ms
run_command | ok | {"argv":["bash","-lc","sed -n '1,200p' ./notes/meeting.md"]}  | isolation: container | 117 ms
run_command | ok | {"argv":["bash","-lc","sed -n '1,200p' ./notes/roadmap.md"]}  | isolation: container | 115 ms
```

The turns, showing three native tool-call turns and the answer:

```text
(1, 'user',      'Summarize the files in ./notes')
(2, 'user',      'You are executing step s1 of an approved plan for the task above.…')
(3, 'assistant', ''  finish=tool_calls)
(4, 'tool',      'exit code: 0\nisolation: container\nstdout:\nmeeting.md\nroadmap.md\n\nstderr: (empty)')
(5, 'assistant', ''  finish=tool_calls)
(6, 'tool',      'exit code: 0\nisolation: container\nstdout:\n# Meeting notes\n\nThe planner over-plans…')
(7, 'assistant', ''  finish=tool_calls)
(8, 'tool',      "exit code: 0\nisolation: container\nstdout:\n# Roadmap notes\n\n- G2 closes LoadCoach's…")
(9, 'assistant', '**Summary of files in `./notes`:** …'  finish=stop, 546 in / 126 out)
```

The answer itself, from `/turns`:

> **Summary of files in `./notes`:**
> | `meeting.md` | A brief note … stating that the planner tends to over-plan trivial tasks, and the
> decision was made to "measure before tuning." |
> | `roadmap.md` | … 1) G2 closes LoadCoach's inbound tool wire; 2) G3 adds a per-step retry policy. |

**Bypassed**, for the pair — `--bypass-planning`:

```text
trajectory   01M1R8K73NR7RX8Z8PWXYXYXZ8
[3] intent.minted — step loop (bypass_default, revision 1)
[5] turn.started … [8] tool.call.started … [22] turn.completed — complete
[23] step.completed — step loop
[24] trajectory.completed
state        completed
class        confidential
bypass       True
cause        the provider declared finish_reason=stop
```

Its three calls, on the tools the bypass default allows:

```text
list_dir  | ok
read_file | ok
read_file | ok
```

**Six tool calls across the pair, every one `ok`, and zero deviations.** Eight egress decisions,
all `approved  confidential -> local_fast (local) target_not_remote` — nothing left the host. This
is spec §20 #2's *sandboxed tools* clause, which the M11 beta shipped unmet.

## 7. The defect the real stack found — `assemble_tool_calls` grouped by the wrong key

`turns.tool_calls_json` from the live run:

```json
[{"call_index": 0, "id": "ollama-227744599217020-0", "name": "list_dir", "arguments_fragment": null},
 {"call_index": 0, "id": null, "name": null, "arguments_fragment": "{\"path\": \"./notes\"}"}]
```

ModelRack's Ollama adapter emits one call as two deltas: the first carries the id and the name with
no arguments, the second carries the argument text **with no id**. `assemble_tool_calls` keyed on
`id` when one was present and on `call_index` otherwise, so those two fragments landed in two
groups and one call became two:

```text
('list_dir', 'refused', 'args_invalid', '""')     # named, no arguments
('',         'refused', 'unknown_tool', '{"path":"./notes"}')   # arguments, no name
```

That pair is verbatim in G1 §10.4, where it was read as the model inventing names and sending
arguments as strings. **Part of it was this function.** `call_index` is ModelRack's own answer to
*which call is this a fragment of* (`streaming.py:198`), so it is now the grouping key, with `id`
and then position as fallbacks. Fixed in `bce7edc` with a regression test built from the fragments
above.

**This is the most important thing in this handoff for the next row.** A hostile-model journey
against the fake could never have found it: the fake emits whatever fragments a test scripts, and
every test scripted the tidy shape.

## 8. What H2 inherits

**Settled contract, generalize on top of it, do not re-decide:**

* The request shape: `tools: [{name, description, parameters}]` with `parameters` verbatim, and
  `messages[].tool_calls: [{id, name, arguments}]` with `arguments` as `object | string`.
* The four transcript rules and their `details.fields[{path, problem}]` presentation.
* ADR-0075's routing rule, including `required_by` on the rejection and `tools: []` ≡ absent.
* A construction-time refusal fails the job with its attempts written.
* LoadCoach never executes a call and never validates a `parameters` schema.

**Open, and H2's to choose:**

* **The response side is still fragments and the request side is assembled.** `output.tool_calls`
  renders one entry per `ToolCallDelta` — `call_index`, `id`, `name`, `arguments_fragment` — while
  a request takes one entry per call. api.md §4 documents the asymmetry and the grouping rule, and
  §7 above is what it costs: every caller must implement that grouping, and the first one to do it
  got it wrong. Collapsing `output.tool_calls` to the assembled shape is a **breaking** change to a
  `1.0` field and wants a major or a parallel field; it is the obvious candidate for H2 and it
  would delete a whole class of caller bug.
* **`Message.name` is not on the wire.** ModelRack's `Message` carries it and Ollama echoes it on a
  tool result; LoadCoach's `MessageBody` has no such field. Nothing needed it here.
* **Remote execution (LC-E1).** Nothing in this row assumes locality; the routing rule is a
  capability filter and applies unchanged to a remote provider that declares `tool_calling`.

## 9. What I2 can now do that it could not

* **A hostile-model journey can script a declared call.** The fake carries `tools` and
  `tool_calls` and copies the real refusals, so the corpus can put a declared tool, a declared tool
  with hostile arguments, and an invented tool through the same journey. G1 §14.6 recorded that the
  fake could not produce the shape the real model produces; it can now.
* **`undeclared_tool` is testable against a model that was actually told the truth.** Until now
  every invented name was arguably the wire's fault. It no longer is.
* **The sandboxed-tool clause of spec §20 #2 is met on the real stack** (§6.4), so I2 verifies a
  path that works rather than one that has never run.

## 10. The moved hazard — uncapped arguments (for I2/P9, not fixed here)

`_render_tool_calls` put uncapped model text into the next turn's transcript; G1 §8 flagged it.
Deleting it **moves** the hazard rather than removing it: `tool_calls[].arguments` is still
uncapped model output going back onto the wire, now as structured JSON instead of prose. Nothing
caps it in PromptCadence, LoadCoach or ModelRack. `_recorded_name` still caps names on events, and
the arguments' *digest* is what `tool_call_records.args_sha256` stores, but the replay carries the
whole thing.

For P9 specifically: **tool definitions now travel too**, and a `description` is caller-written
prompt content going into the model's context (api.md §4 and §12 say so). The injection surface is
no longer only the plan document — it is the plan document plus every tool description the caller
supplies. In this suite those descriptions come from ToolYard's registered specs and are not model
text, which is exactly the property the corpus should assert rather than assume.

## 11. Things this prompt said that turned out not to be true

1. **"docs `main` is at `3d7d11f`."** It was at `93c3922`; two commits had moved the handoff
   history into `docs/history/` and re-pointed every reference to it. The mirrors in LoadCoach and
   PromptCadence carried the matching uncommitted edits when this session started, and they were
   left alone and committed with this row's work where they overlapped a file it touched
   (`LoadCoach/CHANGELOG.md`, `LoadCoach/docs/apps/loadcoach/routing.md`). `LoadCoach/.gitignore`
   and `PromptCadence/.gitignore` are still uncommitted, and `PromptCadence/skills-lock.json` is
   still untracked — **none of the three is this row's, and all three are left for the operator.**
2. **"Python 3.13.15; there is no python3.12 on this host."** True of PromptCadence's venv. **LoadCoach's
   venv is 3.14.4**, and its `mypy` was red on arrival for an unrelated reason (§1).
3. **"Ollama is installed and running with gpt-oss:20b among the pulled models — the model G1
   measured."** True, but conditional on the GPU. With another model resident, `tools.plan` routes
   to `gemma3:latest` and gpt-oss:20b is rejected `insufficient_vram` — routing being right, and
   the reason the gate E measurement went straight to Ollama rather than through LoadCoach, where
   the model could not have been held constant. With the card free, both demonstration
   trajectories routed to gpt-oss:20b, which is what makes §6.4 like-for-like with G1 §10.4. Any
   future demonstration on this machine should record what was resident.
4. **"The round trip — a response's `output.tool_calls` fed straight back in as the next request's
   assistant turn — works without the caller reshaping anything."** It does not, and cannot: the
   response is fragments and the request is assembled (§8). The round-trip test performs exactly
   the documented grouping and nothing else, and api.md §4 now states the asymmetry rather than
   pretending it away.
5. **§0.2(2) framed the internal-consistency check as costing only strictness.** It also forced a
   real change in PromptCadence: a replayed `TOOL` turn must carry the model's call id, not the
   application's invocation ULID. That was a latent defect, not a cost.
6. **The row's item 2 read as "delete the workaround and replay `tool_calls_json`".** Replaying it
   *as persisted* would have reproduced the bug in §7 — the persisted form is fragments, and they
   have to be assembled, correctly, first.
7. **"Ollama's own tool-call parser then rejects the model's next answer" (G1 §9.3(c)).** Not seen
   once in this session's live runs. With the definitions on the wire, gpt-oss:20b emitted
   well-formed tool calls every time; the `ProviderRejected: error parsing tool call` shape did not
   recur.

## 12. Left for the operator

1. **Push three repositories.** `docs` (2 commits ahead), `LoadCoach` (5), `PromptCadence` (2).
   Nothing was pushed and no push was attempted.
2. **No tag, no publish.** LoadCoach's minor is cut at H2; PromptCadence's `0.9.0b0` tag is still
   the operator's and is unaffected by this row.
3. **Three pre-existing working-tree items were left untouched** (§11.1): the two `.gitignore`
   edits and `PromptCadence/skills-lock.json`.
4. **The ModelRack finding in §5 is scheduled into H1** (interview, 2026-09-05).

## 13. The interview (2026-09-05) — four decisions

| # | Decision put | Answer | Where it landed |
|---|---|---|---|
| 1 | LoadCoach's venv: keep `modelrack 0.5.0` from PyPI, or restore the editable cross-repo install | **Keep 0.5.0** | §1; the venv now matches the declared pin and CI, and the gate is green because of it |
| 2 | The unreachable `thinking_control`: a ModelRack row, a finding only, or drop the declaration | **Schedule a row** | Added to the **H1** row (ModelRack P8): `SamplingParameters.think`, the Ollama top-level key, `CapabilityUnsupported` elsewhere; a task-profile field is explicitly a later row |
| 3 | The response/request tool-call asymmetry | **H2 decides, documented as open** | §8; api.md §4 states the asymmetry and the grouping rule, and nothing in a shipped `1.0` field moved here |
| 4 | The moved uncapped-arguments hazard | **Leave to I2/P9** | §10; written up as a moved hazard, with the property the corpus should assert rather than assume |
