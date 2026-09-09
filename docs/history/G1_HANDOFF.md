# G1 handoff — PromptCadence Phase 7: planner, approval modes, DAG dispatch, and the governance-invariance proof

**Row:** G1 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-04 (finished 2026-09-05 UTC).
**Model:** Claude Fable 5.1 (the row was scheduled for Fable 5 · xhigh — §16).
**Repositories:** PromptCadence `de8d918` → `c9ed99a` (eight gate commits + the release commit, not pushed); docs `7a4bddd` → `e00383e` (three commits, not pushed). LoadCoach, ModelRack and Commissioner were read and never edited.
**Version:** **`0.9.0b0`**, withheld at the build (§11) and cut by operator decision at the interview (§17): PromptCadence `c9ed99a`, changelog section dated 2026-09-04 with a *Known limitations* block. The tag, the push and the single `pypi` approval are the operator's (§12).

## 1. Gate results — interpreter and exact invocations (M5C-13)

Interpreter: `/home/jpk/ai/suite/PromptCadence/.venv/bin/python`, **Python 3.13.15** (there is no python3.12 on this host). Resolved: setspec 0.5.0, commissioner 0.1.0, loadledger 0.2.0, toolyard 0.1.0, baseaicore 0.4.1, mirrorwall 0.2.2 — nothing widened.

Run from `/home/jpk/ai/suite/PromptCadence`, **with no LoadCoach listening on 8766 and no PromptCadence on 8768** (see §14 item 6 for why that matters):

```text
$ .venv/bin/ruff format --check .        → 123 files already formatted
$ .venv/bin/ruff check .                 → All checks passed!
$ .venv/bin/mypy src tests               → Success: no issues found in 132 source files
$ .venv/bin/lint-imports                 → Contracts: 5 kept, 0 broken.
$ .venv/bin/python -m pytest -m "not live and not performance" -q
                                         → 1011 passed, 2 skipped, 2 deselected  (random order: pytest-randomly on)
$ PROMPTCADENCE_LOADCOACH__BASE_URL=http://127.0.0.1:8766 .venv/bin/python -m pytest -m live -q -rs
                                         → 2 passed, 1010 deselected   (real LoadCoach on Ollama)
```

The suite passes with no LoadCoach, no GPU and no network (§20 #10). The two skips are the PostgreSQL parity tests, as before.

## 2. The six gates, as commits

| Gate | Commit | What it made true |
|---|---|---|
| A | `8e3b2d7` | The planner drafts under `tools.plan`, validates here, retries within `[planning] corrective_retries`; every attempt a `plans` row; T2/T4/T5/T6/T7; one thread per step; `step.started`/`step.completed` on both paths; intents re-minted from the record; the `planning` recovery edge redrafts; migration 0007 |
| B | `8fc75d6` | Three modes on both paths; **the bypass gate wired** (§0.2(5)); the grant **supersedes** (§0.3); scoped re-approval, tier escalation, ceiling raise as real T10 requests; expiry by persisted clock; tokens and the `approve` scope |
| C | `95a9a3d` | Ready-set DAG dispatch under the disjoint-surface rule; the DAG recorded when serial; multi-step reconciliation |
| D | `9d7705e` | The contract-1 diff with its named allowance list, and the structural proof |
| E | `1152147` | `approve`/`deny`/`approvals list`, `tiers list\|show\|check`, `token create\|list\|revoke`, `/plan`, `/intents`, a real `/system/status`, the `tiers` health component; the docs |
| F | `e67b5f0`, `bfd96bc`, `289a38e`, `c9ed99a` | Three fixes the real stack forced (§9); the version withheld at the build (§11) and cut at the interview (§17) |

Docs: `463ea9c` (§12 `corrective_retries`, §8.3 amendment) and `18bcd73` (the Phase 7 deltas). `spec.md`, `lifecycle.md`, `development-plan.md` are `cmp`-identical between `docs/apps/promptcadence/` and `PromptCadence/docs/apps/promptcadence/`.

## 3. The §0.3 decision — the grant supersedes

Taken as the kickoff recommended. A gated bypass trajectory is T3 then T10 **in one write** (`trajectory.claimed` + `intent.minted` + `approval.requested`, the row ending `awaiting_approval` with no lease). The grant mints **revision 2** by `supersede()` — `minted_by = approver:<token id>`, `approval_request_id` set, no field widened — and revision 1 is retained as the gated envelope nobody executed under. The executed turns carry `(intent_id, 2)`. The assertion written first, and asserted over every Gate B scenario: *no turn executes under an intent whose gate fired and whose grant is not in the record* (`tests/integration/test_approvals.py::_assert_no_turn_ran_under_an_ungranted_gate`). Lifecycle §4.2 now says this.

## 4. The §0.5 decision — `corrective_retries = 2` is configuration

`[planning] corrective_retries` (default 2, `ge=0`; 0 is one attempt and no retry) on `PlanningSettings`, in the shipped TOML reference and in spec §12, one commit. No ADR. The budget is `1 + corrective_retries` attempts; every issue of a refused draft is fed back at once (`planner.corrective`), and — after the real stack (§9) — a LoadCoach *validation* failure on a drafting call counts as an empty attempt within the same budget, as spec §13's planner row already says.

## 5. Contract 1 — the permitted-difference set, and how it fails

`tests/contract/test_governance_invariance.py`. One scripted task, run planned and `bypass_planning` into two fresh databases; every table's rows reduced to shapes (ULIDs, decision ids, timestamps and digests masked, JSON text columns parsed and masked inside) and diffed. Two scenarios: a one-turn journey, and a journey that raises the same `undeclared_tool` deviation on both paths (a tool outside the trajectory allowlist, refused and recorded).

Permitted, each with its document:

1. `plans`, `plan_steps`, `plan_approvals` — rows only on the planned path (contract 1's own wording).
2. `events` of type `plan.drafted` and `plan.approved` — only on the planned path; `trajectory.claimed.data.state` is `planning` on one and `executing` on the other (T2 vs T3).
3. `turns` — exactly one extra `user` turn on the planned path, identified by `prompt_id = step.execute` (spec §9); every turn count it shifts (`sequence` on turn rows and on `turn.*` events, `turn_count` on `step.completed` and `trajectory.completed`) must be **exactly bypassed + 1** — a relation, not a mask.
4. `execution_intents` and `intent.minted` — `minted_by` (`policy` vs `bypass_default`), `step_id` (`s1` vs `loop`), and the **slice** fields `token_budget`, `money_budget(_currency/_nanos)`, `max_turns`: the bypass default's slice *is* the trajectory's ceiling and `execution.max_steps` (ADR-0056 §2); a planned step's is estimate × 2 and `max_turns_per_step` (lifecycle §4.3, §5). Every governed field — `approved_tier`, `fallback_tiers`, `permitted_egress_class`, `approved_tools`, `max_classification`, `budget_source`, the gate — must match.
5. `threads.step_id` and every `step_id` in an event body.
6. `trajectories.bypass_planning` and the same flag on `trajectory.created` — the request itself.

Everything else — the ledger's entries, balances and per-ceiling verdicts, every egress decision, every deviation row and event, every tool-call record, the turn rows' provenance and usage, the terminal transition and its cause — is identical, and is. The failure message names the table, the row index and the field: `execution_intents[0].money_budget_nanos moved: planned=None bypassed=5000000000` is what item 4 looked like before it was named.

**One item was added to the list while writing it, and it is the one worth a reviewer's eye:** the slice fields (item 4). The kickoff's wording was "identical except for the plan rows"; F2 §11's was about the deviation matrix rows (which do not move). The slice differing is by construction in ADR-0056 §2 — it is not a governance write that became conditional — and it is declared, not masked: the governed fields beside it are compared by value.

**The structural half:** an AST walk asserts `LoadCoachClient.generate` is reached from exactly two sites — `LoopController._call`, whose signature takes a `_StepRun` (an intent and its thread), and `Planner.draft`, which produces no turn — plus the existing `TurnProvenance` InitVar guard.

## 6. What was built beyond the kickoff's list, and why

* **`turns.tool_calls_json`** — the calls an assistant turn requested, persisted verbatim. Without it a step parked for a scoped re-approval between the turn and its calls (spec §20 #8's exact scenario) would resume with the calls lost. The step loop now runs pending calls on its next iteration, so a crash there is recoverable by construction too.
* **`deviations.turn_id` loses its foreign key** — a `tier_escalation` names a turn that was announced (`turn.started`) and never answered.
* **`GET /trajectories/{id}/plan` and `/intents`** — the "new plan and approval surfaces" §0.4 asks for, so the record is retrievable through the surfaces that exist. Additive routes; spec §7.1 amended. Not the explanation document.
* **`loadcoach_has_remote_provider` as an injection seam** (governance, approvals, loop; default `False`). D2 named it a runtime fact from LoadCoach; nothing supplied it. The planned path's hybrid egress gate cannot fire in a real deployment before LC-E1 (a remote step is rejected as unavailable at approval), so the gate tests inject `True` and say so.
* **`services/tokens.py`, `web/auth.py`, `promptcadence token …`** — the `approve` scope had nothing to hang on: PromptCadence had no authentication layer. Loopback with no tokens is open and names itself (`approver:loopback`), the LoadCoach precedent.
* **The deviation limit** (lifecycle §5's "more than 3 on one step halts") and **`PROMPTCADENCE_API_TOKEN`** as a reserved environment name.

## 7. Exit conditions (kickoff §11)

| # | Condition | Result |
|---|---|---|
| 1 | §20 #2 minus the explanation clause | **Passed on the real stack** for a tool-free task (§10.3); **the sandboxed-tool clause did not** (§10.4–10.5) |
| 2 | §20 #3 by the contract-1 diff | Passed (`test_governance_invariance.py`, both scenarios) |
| 3 | §20 #7 hybrid pause, listed, deny halts | Passed on the fake with the remote-provider seam (`test_hybrid_runs_the_ungated_step_first…`) |
| 4 | §20 #8 scoped re-approval, both revisions retained | Passed (`test_a_scoped_reapproval_mints_a_superseding_revision_for_that_step_only`) |
| 5 | `manual` holds a bypassed trajectory | Passed (`test_manual_holds_a_bypassed_trajectory…`) |
| 6 | A gated fallback cannot smuggle egress | Passed (`tests/unit/test_gate_smuggling.py`) |
| 7 | The seven planned journeys | auto ✓, hybrid pausing ✓, manual deny ✓, timeout ✓, redlined ✓, scoped re-approval ✓, parallel pair: the rule is walked as a matrix and two local steps stay serial under a raised cap ✓; a *remote* step cannot execute before LC-E1 |
| 8 | `tiers check`, `doctor`, `/system/status` | Passed on the real LoadCoach (§10.1) |
| 9 | No `before Phase 7` survives | Passed; a test greps for it |
| 10 | Full gate, no LoadCoach/GPU/network | Passed (§1) |
| 11 | Live run captured; version iff passed | Captured (§10); withheld at the build (§11), cut at the interview (§17) |
| 12 | Trees clean, docs `cmp`-identical | Passed |

## 8. What P8 and I2 inherit

**P8 (I1).** The rows the explanation composes all exist now: `trajectories`, `plans` (every attempt, `valid`/`issues_json`, the planning call's subject and token classes, `prompt_*`), `plan_steps` (with `status`), `plan_approvals` (the full verdict), `approval_requests` (`kind`, `detail_json`, `resolution_reason`), `execution_intents` (every revision), `threads` (per step), `turns` (`prompt_*`, `tool_calls_json`), `tool_call_records`, `ledger_entries`, `egress_decisions`, `deviations`, `events`. `/plan` and `/intents` render them as-is and commit to no schema. Hazards for `materialize(rows) == compose_live(rows)` specifically in the plan/approval rows: `tool_calls_json` and `plans.raw_document` are **model output** and must follow the retention scrub exactly as transcript text does; `threads` for a trajectory order by `created_at` then `id` (ties are real under the millisecond clock); an invalid attempt has `validated_json = {}` and `issues_json` set — compose from `valid`, not from emptiness. The compaction trigger inherits `threads.step_id`: compaction is per step thread.

**I2 (the injection corpus).** The plan document is the first model output that steers dispatch. Its declarations are validated (tools, tiers, classification, DAG) but its **descriptions are free text (≤ 2000 chars) quoted verbatim into the executing model's context** by `step.execute`; a description carrying instructions is the obvious vector. Second vector: `_render_tool_calls` echoes model-chosen tool names and arguments into the next turn's transcript, **uncapped** — `_recorded_name` caps names on events, nothing caps the replay text; cap it. Third: `depends_on` and `step_id` are validated against the plan only; `max_plan_steps` bounds the count and LoadCoach's `max_output_chars` (50 000) the document.

## 9. What the real stack found (gate F), and what was done about each

Verbatim transcripts are in §10. In order of discovery:

1. **gpt-oss:20b under `tools.plan` returns an empty document about half the time.** Sampled four times with the identical call: two answers in 5–9 s, two empty after ~45 s. Shown the 1.0.0 prompt (4.4k characters: the full JSON Schema block and five full tool descriptions) it was empty on **every** try. `planner.draft` 1.1.0 (`bfd96bc`) drops the schema block and renders a tool as one sentence; PLAN_SCHEMA and the five rules are untouched. LoadCoach's attempt rows for the empty tries are **not persisted** (item 2), so their `finish_reason` is unrecoverable; the shape seen directly through Ollama with qwen3.5:9b was `done_reason=length`, content empty, 4096 tokens of thinking. **This is the `native.plan` finding**: a reasoning model under JSON mode spends `max_output_tokens` thinking. Levers not pulled here because they are LoadCoach's: `tools.plan`'s `max_output_tokens`, and thinking control.
2. **LoadCoach's own corrective retry crashes on an empty first answer and leaves the job `executing`.** `services/execution.py::corrective_turns` appends `Message(ASSISTANT, content=previous_text)` unconditionally; ModelRack's `Message` refuses an assistant turn with neither content nor tool calls; `/generate` surfaces `VALIDATION_ERROR`, the job stays `executing` until a watchdog or a cancel, and its attempts are never written. PromptCadence's response (`e67b5f0`, `289a38e`): never replay an empty answer in *its* corrective; treat a LoadCoach validation failure on a drafting call as an empty attempt within `corrective_retries` (spec §13's planner row); cancel the job LoadCoach left running. **LoadCoach defect, reported here, not fixed here.**
3. **LoadCoach's wire cannot carry tools.** `GenerateBody` has no `tools`; `MessageBody` has no `tool_calls`. So (a) a model is never told which tools exist — gpt-oss invents names from its own built-in vocabulary (`repo_browser.list_dir`, `container.exec`, `assistant<|channel|>commentary`) and sends arguments as strings, every one refused and recorded by ToolYard; (b) an assistant turn that answered with tool calls alone cannot be replayed — ModelRack refuses it empty — so `289a38e` replays it as text naming the calls; and (c) Ollama's own tool-call parsing then rejects gpt-oss's next answer (`ProviderRejected: error parsing tool call`) and LoadCoach halts with `ALL_CANDIDATES_FAILED`. **Model-directed tool use is unreachable on the real stack until LoadCoach's `/generate` carries tool definitions and `tool_calls`.** E4 said the operator's Ollama run was the only place a model would choose a tool; it turns out it cannot. This is LC-E1-adjacent and, in my view, the first item for M12.
4. **A model over-plans.** For "Reply with the single word: ready." the planner declared a `write_file` step. The tool-free task ("What is 2 + 2?") planned, was approved and completed. A prompt instruction against over-planning is one model's tuning and was not attempted.
5. **The record around all of it is right.** Every refused call is a `tool_call_records` row and a `TOOL` turn; every hallucinated tool is an `undeclared_tool` deviation, refused and never re-approvable; every turn has its egress decision and its debit; every halt names LoadCoach's code. That is contract 1 holding on the real stack, which is the row's point.

## 10. The live demonstration, verbatim

LoadCoach `1.0.0` served from a scratch data directory on 8766 against Ollama 0.32.13 (15 models); PromptCadence served on 8768 from a scratch data directory with the **shipped defaults and no `PROMPTCADENCE_TIERS__*` overrides**. LoadCoach routed `tools.plan` and `tools.agent.local_fast` to `ollama/gpt-oss:20b`, `tools.agent.local_large` to `ollama/ornith:9b`, all flagged `low_evidence`.

### 10.1 `tiers check` and `doctor`

```text
$ promptcadence tiers check
loadcoach http://127.0.0.1:8766: 3 profile(s) resolve in LoadCoach, tools.plan included
  ✓ local_fast       tools.agent.local_fast         version 1.0.0
  ✓ local_large      tools.agent.local_large        version 1.0.0
  ✓ (planner)        tools.plan                     version 1.0.0
exit=0

$ promptcadence doctor
promptcadence doctor — status: ok
  ✓ database: sqlite, schema at head.
  ✓ loadcoach: loadcoach reports ok
  ✓ tiers: 3 profile(s) resolve in LoadCoach, tools.plan included
  ✓ tools: 5 registered: read_file, list_dir, write_file, run_command, http_fetch; isolation container: podman: not installed; docker at /usr/bin/docker ran the canary under the container tier's flags with image 'python:3.12-slim'.
exit=0
```

### 10.2 The pair on a tool-free task — planned completes, bypassed completes

```text
$ promptcadence run "What is 2 + 2? Answer with just the number." --follow
trajectory   01M1QQCJCS0K12X8DF5267C34V
[1] trajectory.created
[2] trajectory.claimed
[3] plan.drafted — attempt 1, valid, 1 step(s)
[4] plan.approved
[5] intent.minted — step s1 (policy, revision 1)
[6] step.started — step s1
[7] turn.started
[8] budget.debited
[9] turn.completed — complete
[10] step.completed — step s1
[11] trajectory.completed
trajectory   01M1QQCJCS0K12X8DF5267C34V
state        completed
class        confidential
bypass       False
cause        the provider declared finish_reason=stop
exit=0
plan attempts: [(1, True, '1.1.0', 887, 50, 4109.0)]
raw: {"steps":[{"step_id":"s1","description":"Compute 2 + 2 and output the result.","depends_on":[],"tools":[],"tier":"local_fast","data_classification":"confidential","expected_turns":1}]}
steps: [('s1', [], 'local_fast', 'committed')]
turn 1 s1 user tier local_fast rev 1 model  finish None usage None prompt None
     'What is 2 + 2? Answer with just the number.'
turn 2 s1 user tier local_fast rev 1 model  finish None usage None prompt step.execute
     "You are executing step s1 of an approved plan for the task above.\n\nSTEP\nCompute 2 + 2 and output the result.\n\nUse only these tools: none. When the step is complete, answer with the step's result and stop."
turn 3 s1 assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish stop usage {'input_tokens': 131, 'output_tokens': 90, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     '4'
2026-09-05T02:47:02.459Z   approved  confidential -> local_fast         (local ) target_not_remote

1 decision(s).
UTC day 2026-09-05  (as of 2026-09-05T02:47:04.222Z)
trajectory 01M1QQCJCS0K12X8DF5267C34V money          at most 5 USD left   tokens        1999779 left
```

```text
$ promptcadence run "Reply with the single word: ready." --follow
trajectory   01M1QQ96A6F8KSE0HF47SKATAG
[1] trajectory.created
[2] trajectory.claimed
[3] plan.drafted — attempt 1, valid, 1 step(s)
[4] plan.approved
[5] intent.minted — step s1 (policy, revision 1)
[6] step.started — step s1
[7] turn.started
[8] budget.debited
[9] turn.completed — continue
[10] tool.call.started
[11] tool.call.completed
[12] tool.call.started
[13] tool.call.completed
[14] turn.started
[15] budget.debited
[16] turn.completed — continue
[17] deviation.detected
[18] tool.call.started
[19] tool.call.completed
[20] tool.call.started
[21] tool.call.completed
[22] turn.started
[23] budget.debited
[24] turn.completed — continue
[25] deviation.detected
[26] tool.call.started
[27] tool.call.completed
[28] tool.call.started
[29] tool.call.completed
[30] turn.started
[31] trajectory.halted — LoadCoach refused /api/v1/generate with ALL_CANDIDATES_FAILED: Every candidate was tried and every attempt failed.
trajectory   01M1QQ96A6F8KSE0HF47SKATAG
state        halted
class        confidential
bypass       False
cause        LoadCoach refused /api/v1/generate with ALL_CANDIDATES_FAILED: Every candidate was tried and every attempt failed.
error_code   LOADCOACH_ERROR
exit=5

$ promptcadence run "Reply with the single word: ready." --bypass-planning --follow
trajectory   01M1QQAY1ZKAF8ECP76JAA342C
[1] trajectory.created
[2] trajectory.claimed
[3] intent.minted — step loop (bypass_default, revision 1)
[4] step.started — step loop
[5] turn.started
[6] budget.debited
[7] turn.completed — complete
[8] step.completed — step loop
[9] trajectory.completed
trajectory   01M1QQAY1ZKAF8ECP76JAA342C
state        completed
class        confidential
bypass       True
cause        the provider declared finish_reason=stop
exit=0
== 01M1QQ96A6F8KSE0HF47SKATAG
turn 1 s1 user tier local_fast rev 1 model  finish None usage None prompt None
     'Reply with the single word: ready.'
turn 2 s1 user tier local_fast rev 1 model  finish None usage None prompt step.execute
     "You are executing step s1 of an approved plan for the task above.\n\nSTEP\nWrite the word 'ready' to a file named output.txt\n\nUse only these tools: write_file. When the step is complete, answer with the "
turn 3 s1 assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish tool_calls usage {'input_tokens': 128, 'output_tokens': 86, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     ''
turn 4 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool 'write_file' — args_invalid: $: expected an object of arguments, received str"
turn 5 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool '' — unknown_tool: no tool of that name is registered"
turn 6 s1 assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish tool_calls usage {'input_tokens': 207, 'output_tokens': 83, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     ''
turn 7 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool 'assistant<|channel|>commentary' — unknown_tool: no tool of that name is registered"
turn 8 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool '' — unknown_tool: no tool of that name is registered"
turn 9 s1 assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish tool_calls usage {'input_tokens': 297, 'output_tokens': 132, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     ''
turn 10 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool 'assistant<|channel|>commentary' — unknown_tool: no tool of that name is registered"
turn 11 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool '' — unknown_tool: no tool of that name is registered"
intent s1 rev 1 policy local_fast ['write_file'] budget 10240 max_turns 8 gate {'egress_gated': False, 'cost_gated': False, 'gating_tier': 'local_fast', 'egress_classification': None}
plan: [(1, True, '1.1.0', 1222, 55, 7859.0)] [('s1', ['write_file'], 'running')]
== 01M1QQAY1ZKAF8ECP76JAA342C
turn 1 loop user tier local_fast rev 1 model  finish None usage None prompt None
     'Reply with the single word: ready.'
turn 2 loop assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish stop usage {'input_tokens': 75, 'output_tokens': 31, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     'ready'
intent loop rev 1 bypass_default local_fast ['http_fetch', 'list_dir', 'read_file', 'run_command', 'write_file'] budget 2000000 max_turns 20 gate {'egress_gated': False, 'cost_gated': False, 'gating_tier': 'local_fast', 'egress_classification': None}
plan: None None
status: pending [] active [] ledger.day at most 20 USD tiers [('local_fast', '3094', '—'), ('local_large', '0', '—')]
```

### 10.3 A confidential trajectory cannot reach a remote tier (second instance, `remote_cheap` configured with a pricing file)

```text
$ promptcadence run "Summarize the files in ./notes" --classification confidential --tier remote_cheap --bypass-planning --follow
trajectory   01M1QNQKM5EWD924R9ZTE8ZZCY
[1] trajectory.created
[2] trajectory.claimed
[3] intent.minted — step loop (bypass_default, revision 1)
[4] step.started — step loop
[5] trajectory.halted — egress to tier remote_cheap was denied for a confidential trajectory: classification_exceeds_ceiling (decision 01M1QNQKNGDW2PNY5SZF5H1T2X, policy OrderedClassificationPolicy 1.0)
trajectory   01M1QNQKM5EWD924R9ZTE8ZZCY
state        halted
class        confidential
bypass       True
tier         remote_cheap
cause        egress to tier remote_cheap was denied for a confidential trajectory: classification_exceeds_ceiling (decision 01M1QNQKNGDW2PNY5SZF5H1T2X, policy OrderedClassificationPolicy 1.0)
error_code   EGRESS_DENIED
exit=5

$ promptcadence egress list --denied-only
2026-09-05T02:18:02.800Z   denied    confidential -> remote_cheap       (remote) classification_exceeds_ceiling

1 decision(s).

$ promptcadence tiers check
loadcoach http://127.0.0.1:8766: 4 profile(s) resolve in LoadCoach, tools.plan included
  ✓ local_fast       tools.agent.local_fast         version 1.0.0
  ✓ local_large      tools.agent.local_large        version 1.0.0
  ✓ remote_cheap     tools.agent.remote_cheap       version 1.0.0
  ✓ (planner)        tools.plan                     version 1.0.0
```

### 10.4 `summarize the files in ./notes`, planned — the corrective budget working, then the tool wire

```text
$ promptcadence run "Summarize the files in ./notes" --follow
trajectory   01M1QQ4GSYQXQCAAHKRSSSDPDN
[1] trajectory.created
[2] trajectory.claimed
[3] plan.drafted — attempt 1, invalid, 0 step(s)
[4] plan.drafted — attempt 2, valid, 4 step(s)
[5] plan.approved
[6] intent.minted — step s1 (policy, revision 1)
[7] intent.minted — step s2 (policy, revision 1)
[8] intent.minted — step s3 (policy, revision 1)
[9] intent.minted — step s4 (policy, revision 1)
[10] step.started — step s1
[11] turn.started
[12] budget.debited
[13] turn.completed — continue
[14] deviation.detected
[15] tool.call.started
[16] tool.call.completed
[17] tool.call.started
[18] tool.call.completed
[19] turn.started
[20] budget.debited
[21] turn.completed — complete
[22] step.completed — step s1
[23] step.started — step s2
[24] turn.started
[25] budget.debited
[26] turn.completed — continue
[27] tool.call.started
[28] tool.call.completed
[29] tool.call.started
[30] tool.call.completed
[31] turn.started
[32] trajectory.halted — LoadCoach refused /api/v1/generate with ALL_CANDIDATES_FAILED: Every candidate was tried and every attempt failed.
trajectory   01M1QQ4GSYQXQCAAHKRSSSDPDN
state        halted
class        confidential
bypass       False
cause        LoadCoach refused /api/v1/generate with ALL_CANDIDATES_FAILED: Every candidate was tried and every attempt failed.
error_code   LOADCOACH_ERROR
exit=5
attempt 1 valid False model None usage {'input_tokens': 'unsupported', 'output_tokens': 'unsupported', 'cache_write_tokens': 'unsupported', 'cache_read_tokens': 'unsupported'} ms None prompt planner.draft 1.1.0
  raw: 
  issues: [('not_json', 'the drafting call produced no usable document: LoadCoach reported VALIDATION_ERROR (LoadCoach refused /api/v1/generate with VALIDATION_ERROR')]
attempt 2 valid True model ollama/gpt-oss:20b@sha256:17052f91a42e usage {'input_tokens': 1992, 'output_tokens': 196, 'cache_write_tokens': 0, 'cache_read_tokens': 0} ms 16436.0 prompt planner.corrective 1.0.0
  raw: {"steps":[{"step_id":"s1","description":"List the files in the ./notes directory.","depends_on":[],"tools":["list_dir"],"tier":"local_fast","data_classification":"confidential","expected_turns":1},{"step_id":"s2","description":"Read the contents of all files in ./notes by concatenating them.","depends_on":["s1"],"tools":["run_command"],"tier":"local_fast","data_classification":"confidential","expected_turns":1},{"step_id":"s3","description":"Summarize the combined contents of the notes.","depends_on":["s2"],"tools":[],"tier":"local_fast","data_classification":"confidential","expected_turns":1},{"step_id":"s4","description":"Write the summary to summary.txt.","depends_on":["s3"],"tools":["wri
  issues: []
steps: [('s1', 'local_fast', ['list_dir'], [], 'committed'), ('s2', 'local_fast', ['run_command'], ['s1'], 'running'), ('s3', 'local_fast', [], ['s2'], 'pending'), ('s4', 'local_fast', ['write_file'], ['s3'], 'pending')]
approval: approved sha256:e6a4d66edaa1835db [('s1', 'approved', 'auto_approved', False), ('s2', 'approved', 'auto_approved', False), ('s3', 'approved', 'auto_approved', False), ('s4', 'approved', 'auto_approved', False)]
intent s1 rev 1 policy local_fast ['list_dir'] budget 10240 configured_default max_turns 8 gate {'egress_gated': False, 'cost_gated': False, 'gating_tier': 'local_fast', 'egress_classification': None}
intent s2 rev 1 policy local_fast ['run_command'] budget 10240 configured_default max_turns 8 gate {'egress_gated': False, 'cost_gated': False, 'gating_tier': 'local_fast', 'egress_classification': None}
intent s3 rev 1 policy local_fast [] budget 10240 configured_default max_turns 8 gate {'egress_gated': False, 'cost_gated': False, 'gating_tier': 'local_fast', 'egress_classification': None}
intent s4 rev 1 policy local_fast ['write_file'] budget 10240 configured_default max_turns 8 gate {'egress_gated': False, 'cost_gated': False, 'gating_tier': 'local_fast', 'egress_classification': None}
turn 1 s1 user tier local_fast rev 1 model  finish None usage None prompt None
     'Summarize the files in ./notes'
turn 2 s1 user tier local_fast rev 1 model  finish None usage None prompt step.execute
     "You are executing step s1 of an approved plan for the task above.\n\nSTEP\nList the files in the ./notes directory.\n\nUse only these tools: list_dir. When the step is complete, answer with the step's result and stop."
turn 3 s1 assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish tool_calls usage {'input_tokens': 125, 'output_tokens': 41, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     ''
turn 4 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool 'repo_browser.list_dir' — unknown_tool: no tool of that name is registered"
turn 5 s1 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool '' — unknown_tool: no tool of that name is registered"
turn 6 s1 assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish stop usage {'input_tokens': 197, 'output_tokens': 333, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     'I’m sorry, but I don’t have a tool available to list the contents of the `./notes` directory.'
turn 1 s2 user tier local_fast rev 1 model  finish None usage None prompt None
     'Summarize the files in ./notes'
turn 2 s2 user tier local_fast rev 1 model  finish None usage None prompt step.execute
     "You are executing step s2 of an approved plan for the task above.\n\nSTEP\nRead the contents of all files in ./notes by concatenating them.\n\nRESULTS OF EARLIER STEPS\n- s1: I’m sorry, but I don’t have a tool available to list the contents of the `./notes` directory.\n\nUse only these tools: run_command. When the step is complete, answer with the step's result and stop."
turn 3 s2 assistant tier local_fast rev 1 model ollama/gpt-oss:20b@sha256:17 finish tool_calls usage {'input_tokens': 167, 'output_tokens': 131, 'cache_write_tokens': 0, 'cache_read_tokens': 0} prompt None
     ''
turn 4 s2 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool 'run_command' — args_invalid: $: expected an object of arguments, received str"
turn 5 s2 tool tier local_fast rev 1 model  finish None usage None prompt None
     "Tool '' — unknown_tool: no tool of that name is registered"
2026-09-05T02:43:35.437Z   approved  confidential -> local_fast         (local ) target_not_remote
2026-09-05T02:43:36.270Z   approved  confidential -> local_fast         (local ) target_not_remote
2026-09-05T02:43:40.166Z   approved  confidential -> local_fast         (local ) target_not_remote
2026-09-05T02:43:42.039Z   approved  confidential -> local_fast         (local ) target_not_remote

4 decision(s).
UTC day 2026-09-05  (as of 2026-09-05T02:44:27.019Z)
trajectory 01M1QQ4GSYQXQCAAHKRSSSDPDN money          at most 5 USD left   tokens        1999006 left
```

LoadCoach's attempt behind the final halt: `ProviderRejected: error parsing tool call: raw='We need to call run_command with JSON object. Let's do: … ```json {"name": "run_command", "arguments": {"cmd": ["bash", "-lc", "ls -R ./notes"]}} ```'`.

### 10.5 `summarize the files in ./notes`, bypassed — completes, and the model says why it cannot

```text
$ promptcadence run "Summarize the files in ./notes" --bypass-planning --follow
trajectory   01M1QNQ61KKN2EEWR9D26DM16M
[1] trajectory.created
[2] trajectory.claimed
[3] intent.minted — step loop (bypass_default, revision 1)
[4] step.started — step loop
[5] turn.started
[6] budget.debited
[7] turn.completed — complete
[8] step.completed — step loop
[9] trajectory.completed
trajectory   01M1QNQ61KKN2EEWR9D26DM16M
state        completed
class        confidential
bypass       True
cause        the provider declared finish_reason=stop
exit=0
```

The assistant's answer, from `/turns`: *"I don't have direct access to your filesystem, so I can't read the contents of `./notes` myself…"* — 75 input, 311 output tokens on `local_fast`, unpriced, `finish_reason=stop`.

### 10.6 Status and ledger after the runs

```text
$ promptcadence ledger show --scope tier
UTC day 2026-09-05
local_fast               money                      — spent   tokens           3094 spent
local_large              money                      — spent   tokens              0 spent
no tier ceiling is configured, so these are balances and not headroom — nothing here can be exceeded

GET /system/status → pending_approvals [], active [], ledger.day "at most 20 USD",
                     tiers [("local_fast", "3094", "—"), ("local_large", "0", "—")]
```

`length` and `content_filter` were **not** observed: every completed real turn declared `stop` or `tool_calls`.

## 11. Why the version was withheld at the build

Kickoff §10: bump *only after the demonstration passes*; §11 #11: `0.9.0b0` **iff** it passed. M11's exit condition as written in roadmap §3 — one planned and one bypassed trajectory, tools + budget + egress active in both, records identical in shape minus plan rows, a confidential trajectory provably unable to reach a remote tier — **held** (§10.2, §10.3, §5). Spec §20 #2's phrase *"executes on a local tier with sandboxed tools"* did **not**: no model-directed sandboxed tool call succeeded on the real stack, and it cannot until LoadCoach's wire carries tools (§9.3). Whether a beta ships with that recorded as an M12 item was the operator's call, put to them at the interview and taken (§17): **cut**, with the changelog's *Known limitations* naming the sandboxed-tool clause, the unbuilt step retry and the open podman condition. The release commit is `c9ed99a`; it also carries the gate E changelog lines, which `1152147` had shipped without.

## 12. The release is the operator's

1. Review the eight commits (`git log de8d918..HEAD`), one per gate, each message saying what it made true.
2. The bump is done (`c9ed99a`, dated 2026-09-04). Nothing else changes in the tree before the tag.
3. Push PromptCadence `main` (now including `952af18`, the release plumbing: `environment: pypi`, the manual TestPyPI dry run, the hashed `requirements/release.lock` build chain — none of which `release.yml` had) and docs `main`. Then, because this is the package's first release (standard §6): add pending trusted publishers on PyPI (environment `pypi`) and TestPyPI (no environment) for `JPKell/PromptCadence`, workflow `release.yml`; create the GitHub `pypi` environment with a required reviewer; run the TestPyPI dry run from Actions → Release → *Run workflow* and confirm 0.9.0b0 on test.pypi.org; **then** tag `v0.9.0b0` and push the tag; approve the `pypi` environment **once** — a single tag push fires two Release runs; approve one and cancel the other (outstanding-work §4). The first publish claims the unreserved name.
4. Post-publish: `pip install promptcadence==0.9.0b0` in a clean venv, `promptcadence doctor`.
5. **M11's other exit condition is unmet and not this row's:** `pytest -m isolation -rs` green on a real podman host. This host has docker only; a skip is visible and is not a pass.
6. For the next row against LoadCoach: §9.2 and §9.3.

## 13. What P8 and the next rows must not relitigate

* The bypass gate's grant **supersedes** (§3). Releasing the park without a revision would leave `minted_by = bypass_default` on an executed intent whose gate fired.
* The planner's spend is on the `plans` row, **not** the ledger. It is not a turn and runs under no intent; contract 1 says debits occur under an intent on every turn. Lifecycle §4.1 records it. If the token ceiling must see it, that is a decision, not a patch.
* The contract-1 allowance list (§5) is closed. A new difference is a finding.
* `observed_classification` for a turn is the intent's ceiling until an operator-flagged path exists to raise it. A planned step declared below the trajectory would otherwise raise `classification_exceeded` on every turn for handling the task text.
* The remote-provider fact is a seam with the safe default. LC-E1 supplies it; nothing here infers it from a provider kind (contract 4).

## 14. Things this prompt said that turned out not to be true

1. **"`tools.plan` is a real, shipped LoadCoach profile — you are not inventing the planning profile; you are calling it."** True, and insufficient: calling it with a 4.4k-character prompt made the shipped model return nothing every time (§9.1). The profile's constraints are a lever the row could not pull.
2. **§0.2(5) said the bypass gate was the one thing missing quietly.** There was a second: `TrajectoryService.turns()` and every reader assumed one thread per trajectory. The planned path needs one per step, and the bypass loop's thread now opens at the step's first dispatch rather than at the claim so both paths have one shape.
3. **"Grants … require the `approve` scope."** There was no authentication in PromptCadence at all — no token CLI, no principal, no scope check on any route. §6 built the minimum; the loopback-open rule is LoadCoach's precedent, not a G1 invention.
4. **§7's "a parallel local+remote DAG pair under the concurrency rule (fake)."** A remote step cannot execute before LC-E1 — approval rejects it as unavailable — so the pair is proven at the rule (a matrix) and at the loop for two local steps under a raised cap; no remote turn ran.
5. **F2 §11's "only `intent_id` and the `minted_by` kind may move."** For the deviation matrix rows, true and asserted. For the intent row itself the slice fields move by construction (§5 item 4).
6. **§10 said the real model would exercise `length` and `content_filter`.** It did not; it exercised `tool_calls` with invented names, which the fake cannot produce either (§9.3). Also: running the gate while a demo PromptCadence listens on 8768 makes four CLI "either"-mode tests read the live server; stop it first.
7. **"The recovery cancels the job, then resumes."** In that order the stalled worker can win a race and end the trajectory itself in the instant before the takeover fences it; the random-order suite found it. Both edges now take the lease first (`8e3b2d7`).
8. **§8 implied `execution_intents.money_budget` matches across modes.** It cannot: the bypass default carries the trajectory's `$5.00`; a local planned step's estimate prices nothing, so its slice is `None` (ADR-0016). Named in the allowance list.

## 15. Read-only notes (kickoff §14)

* **(a) I1 readiness** — §8. One more hazard: `approval_requests` for a bypass gate carry `step_ids = ["loop"]`; the explanation should not look the step up in `plan_steps`.
* **(b) P9 corpus** — §8, second paragraph. Add: a plan whose descriptions embed `[tool_calls]` text, since that prefix is what the replay uses.
* **(c) Lifecycle §5 categories without a loop-level test:** `turn_overrun` (domain-tested only; no loop journey reaches `max_turns` without a declared finish) and `classification_exceeded` (cannot fire — no operator-flagged path exists to raise a turn's observed classification). `tier_violation`, `tier_escalation`, `undeclared_tool` (both sides of the allowlist) and `budget_overrun` (both scopes) have loop tests.

## 16. Model deviation (model-assignment §3.5)

The row was scheduled for **Fable 5 · xhigh** and ran on **Claude Fable 5.1**, whole, daytime, with the operator present for the interview that follows this handoff. No split.

## 17. The interview (2026-09-04) — ten decisions and where each landed

| # | Decision put | Answer | Where it landed |
|---|---|---|---|
| 1 | Cut `0.9.0b0` now, or after LoadCoach carries tools | **Cut** | `c9ed99a`; changelog *Known limitations*; roadmap M11 row |
| 2 | The bypass gate's grant supersedes the intent | Confirmed | As built (§3); roadmap G1 row "not to relitigate" |
| 3 | Planner spend on the `plans` row, not the ledger | Keep as built | §13; G1 row |
| 4 | Loopback with no tokens is open, recorded `approver:loopback` | Keep as built | §6; changelog gate E |
| 5 | `loadcoach_has_remote_provider` seam, default `False` | Confirmed | §13; G1 row item (4) |
| 6 | The LoadCoach wire gaps become a row | **Yes — G2 drafted** | roadmap `e00383e`: G2, Opus 5 · high, after G1, before I2; exit = a declared sandboxed call on the real stack and the `[tool_calls]` rendering gone |
| 7 | `planner.draft` 1.1.0 drops the schema block | Confirmed | `bfd96bc`; changelog gate F |
| 8 | The contract-1 allowance list includes the intent slice fields | Confirmed | §5 item 4; the list is closed |
| 9 | Per-step retry policy | **Schedule now — G3 drafted** | roadmap `e00383e`: G3, Opus 5 · high, after G1, before I1; one ADR (retry vs escalation order), `[execution] step_retries`, `step.retried`, no new contract-1 allowance |
| 10 | `corrective_retries` is configuration | Confirmed | §4 |

Also recorded in the roadmap: §3 gains *G2 before I2's sandboxed-tool verification* and *G3 before I1*; §4 carries the G1 push, tag and single `pypi` approval and marks the E4 Ollama run done with `length`/`content_filter` still unexercised; §5's M12 row lists G2 and G3.

