# I3 — LoadCoach 1.1.1: `provider_name` and `is_remote` in `GET /models`, and a profile that can ask for reduced thinking

**Row:** I3 of `roadmap/outstanding-work.md` §1. **Model:** scheduled Sonnet 5 · high; ran on
**Claude Opus 5** (model-assignment §3.5 — recorded, not a split), whole, in one session with the
operator present for the closing interview. **Date:** 2026-09-06.
**Interpreter:** Python 3.14.4 at `LoadCoach/.venv/bin/python` for every gate; Python 3.13.15 at
`/usr/bin/python3.13` for the lock recompile, the install-from-lock gate run and the wheel check.
**Ships:** `loadcoach 1.1.1` **prepared** — bumped, changelogged, release-committed — and **not**
tagged, pushed or published. Those are the operator's (§10).

**Repositories touched:** `docs` (two commits) and `LoadCoach` (four — gate A's mirror rode with gate B). Both were clean at the start
— `LoadCoach` at `93063bd`, level with `origin`; `docs` clean but for this row's untracked kickoff
prompt — and both are clean at the end with the new work committed and unpushed. No `git push`, no
push dry-run, no tag. Nothing was modified that this session did not edit.

---

## 1. Gate results, with the exact invocations

Every gate ran the full pre-PR gate before its commit. The final run, from `/home/jpk/ai/suite/LoadCoach`:

```bash
.venv/bin/ruff format --check .          # 214 files already formatted
.venv/bin/ruff check .                   # All checks passed!
.venv/bin/python -m mypy src tests       # Success: no issues found in 194 source files
.venv/bin/lint-imports                   # Contracts: 4 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                         # 1021 passed, 4 skipped, 18 deselected
.venv/bin/python -m pytest --cov --cov-report=term-missing -m "not live and not performance" -q
                                         # Total coverage: 90.41% (floor 85 %)
```

The suite grew from 1017 to 1021 tests.

**The install-from-lock run** (gate D), on a clean `python3.13 -m venv`:

```bash
/usr/bin/python3.13 -m venv <scratch>/lockcheck
<scratch>/lockcheck/bin/pip install --require-hashes -r requirements/ci.lock
<scratch>/lockcheck/bin/pip install . --no-deps
<scratch>/lockcheck/bin/python -m pytest -m "not live and not performance" -q
                                         # 1021 passed, 4 skipped — modelrack 0.7.1, Python 3.13.15
```

**The wheel** (gate E), built with `.venv/bin/python -m build` and installed into a second clean
3.13 venv: `import loadcoach` ok, `loadcoach --version` → `loadcoach 1.1.1 (api v1)`, and
`tests/e2e/test_server_boot.py` 10 passed against the installed distribution.

## 2. The gates as commits

| Gate | Commit | What it made true |
|---|---|---|
| A | docs `e8ef0ee` | ADR-0099 accepted and indexed; api.md §2 and §4, routing.md §2 and §4 amended |
| B | `8a57472` | `GET /models` and `loadcoach models list --json` render `provider_name` and `is_remote`; the mirror; the snapshot regenerated and unmoved |
| C | `13a0286` | `TaskProfileExecution.think`, `sampling.think` over it, `thinking_control` required at routing, the byte-identical golden |
| D | `cb1cfac` | The measurement, the five profiles' decision and the `tools.plan` comment; `ci.lock` → `modelrack 0.7.1` |
| E | `2a7ac58` | `1.1.1`: the bump, the changelog header, `docs/openapi.json`'s one moved line |

## 3. The four decisions (kickoff §0.2), with the reason and what the losing option would have claimed

All four are in **ADR-0099**, `docs/adr/0099-a-task-profile-may-ask-for-reduced-thinking.md`, the
highest number free when the directory was checked (0098 was the top, as the prompt said).

### 1 — The field's name and type

**Taken:** `TaskProfileExecution.think: bool | None = None`, ModelRack's name and its three states.
Unset builds a request byte-identical to 1.1.0's; `false` asks for reasoning suppressed; `true`
asks for it.

**What the losing option would have claimed.** A string enum (`reasoning = "off" | "on" |
"default"`) would have been a second vocabulary for a fact ModelRack already names, and the record
would have had to assert that two spellings mean one thing — a claim every future reader has to
re-verify at the boundary. The house rule is *same concept, same name across the suite*, and there
was no argument for breaking it here beyond the enum reading marginally better in TOML.

### 2 — Whether the request may override it

**Taken:** yes. `sampling.think` overrides the profile exactly as `sampling.temperature` and
`sampling.max_output_tokens` do, documented in api.md §4 beside them, and a value that is neither a
boolean nor `null` is a `VALIDATION_ERROR` naming the field.

The reason is the measurement itself: gate D varied the control **through `sampling.think`** and
never edited a shipped profile to do it, which is precisely the experiment a caller like
PromptCadence will want to run. Refusing the override would have meant a caller may set the budget
but not the control that decides what the budget is spent on, and there is no principle that
separates those two.

The validator is the one place this row was deliberately *not* lazy: `sampling` is
`dict[str, Any]` and nothing in it is validated today, so a caller writing `think: "false"` would
have sent a truthy string to a provider. It is refused for the new key only; widening the check to
`temperature` and `max_output_tokens` would change a 1.0 contract and is not this row's.

### 3 — What happens when the provider cannot carry it

**Taken:** filter at routing. A set `think` — from the profile or the request — requires
`thinking_control` of every candidate; the rejection is `capability_unsupported` with
`details.capability = "thinking_control"`, `details.provider_kind` and `details.required_by`
(`"task_profile"` or `"request"`). It is ADR-0075's mechanism and its rejection reason, evaluated
in the same loop, right after the `requires_capabilities` check.

**The vocabulary gap the prompt warned about is real, and it changed the shape of the fix.**
`requires_capabilities` is validated against the SetSpec capability vocabulary
(`setspec.is_known_capability`, version 1.1) and routing.md §2 states the rule: *a profile may not
reference a capability outside the SetSpec vocabulary*. `thinking_control` is **not** in that
vocabulary — checked, not assumed — and `thinking` (the neighbouring *model* flag) means something
else. So the requirement travels as its own `ConstraintInputs` field,
`requires_thinking_control: str | None`, whose value **is** the `required_by` label, and
`ProviderFacts` gains `supports_thinking_control` beside its four siblings. Reusing
`requires_capabilities` would have put a non-vocabulary string into the one field the validator
polices, and an operator writing `requires_capabilities = ["thinking_control"]` would still be
refused at import while LoadCoach itself injected exactly that — a rule that applies to the user
and not to the program.

**What the losing options would have claimed.** *Send and map the refusal* — the provider raises
`CapabilityUnsupported` and it becomes a permanent attempt failure with an error code. Honest, and
it fails a job after a model has been chosen for a fact routing knew before it chose; on a
llama.cpp-only deployment every job under such a profile would fail, having consumed a routing
decision to get there. *Drop silently* — the request goes out without the key, and the record then
says the profile asked for something the wire never carried. G2 §5's *configuration that lies*, in
the direction that is hardest to notice.

### 4 — The profile version bump

**Taken:** the rule, not a blanket bump. A profile's `version` moves when its **values** change,
not when its comments do (`5af6b12`'s precedent, which rewrote `tools.plan`'s comment with G2's
numbers and kept `1.0.0`). The measurement then decided that no shipped profile gains a `think`
value (§5), so **no version moves** and every one of the five stays at `1.0.0`.

Had the measurement gone the other way, the five would have shipped at `1.1.0` so that a
`routing_decisions` row written before this release still names the definition it ran under. The
rule is recorded in ADR-0099 rule 6 either way, because the next row to change a shipped profile's
values needs it and nothing had established it before.

## 4. The measurement (gate D)

Six runs per cell, four cells, 24 generations, run once and whole. **Through a real LoadCoach**, not
straight through Ollama as G2 did, because this row's lever is the profile-to-wire thread rather
than a sampling value: `loadcoach serve` on a scratch `LOADCOACH_DATA_DIR` against Ollama `0.32.13`
with `overrides.model` pinning `ollama/gpt-oss:20b@sha256:17052f91a42e`. Every one of the 24
attempt records names that model; nothing else was routed.

The `tools.plan` prompt is PromptCadence's `planner.draft` `1.1.0` record, read from
`PromptCadence/src/promptcadence/prompts/planner/draft.v1.json` and rendered by a scratchpad
script rather than by importing PromptCadence: the 287-character system turn verbatim (identical to
G2's), and the template filled with G2's shape — the G1 task, `internal`, five tools rendered as
name plus first sentence, three tiers, `max_steps = 20`. **The user turn came out 1 942 characters,
not G2's 1 826**, because the tool briefs and tier lines are reconstructed from ToolYard's and
PromptCadence's sources rather than captured from a live render. Every cell used the same string,
so the comparison holds; the absolute number is not G2's.

The `tools.agent.local_fast` turn is api.md §4's shape: two tool definitions, a user turn, an
assistant turn carrying one `list_dir` call, and the matching `tool` result.

| Profile | `think` | Delivered | Attempt 1 hit the 4 096 budget | Median wall |
|---|---|---|---|---|
| `tools.plan` | unset | **3 / 6** | 2 / 6 | 12.9 s |
| `tools.plan` | `false` | **0 / 6** | 1 / 6 | 1.3 s |
| `tools.agent.local_fast` | unset | **6 / 6** | 0 / 6 | 0.9 s |
| `tools.agent.local_fast` | `false` | **6 / 6** | 0 / 6 | 1.0 s |

**"Delivered" is the honest column, and §0.3's `text == ""` is not.** Through LoadCoach a job is up
to three provider calls, and the structured-output corrective retry absorbs an empty draft — so no
`tools.plan` job returned an empty string at all. What three of the six unset runs returned was
`{}`: valid JSON, an empty plan, produced by the corrective after attempt 1 came back with nothing
usable (twice at exactly 4 096 output tokens with `finish_reason=length`, once a stray
`finish_reason=tool_calls`). The other three returned a real plan document. So *delivered* means a
plan; the corrective's `{}` is counted as a non-delivery, and the raw per-attempt rows are the
evidence.

**`think = false` made `tools.plan` strictly worse, and the reason is not the budget.** Four of the
six runs died in 1.3 s with `ProviderProtocolError: The stream from http://127.0.0.1:11434 ended
without a terminal chunk`, and the other two exhausted all three attempts on invalid JSON. Probing
Ollama directly explains it: **gpt-oss:20b accepts `think: false` and does not honour it.** A
non-streaming call with `think: false` still came back with a populated `thinking` field, and a
streaming call with `think: false` and `format: json` emitted the model's reasoning as **`content`**
("The user says: …") instead of on the thinking channel — which then fails `require_valid_json`.
The control reaches the model; the model ignores it and relocates its reasoning into the answer.

On `tools.agent.local_fast` the control changed nothing measurable: 6 of 6 turns produced the
`list_dir` call in both cells, 55–67 output tokens, ~1 s. **I2 §10 run 1's pathology did not
reproduce** — that turn was late in a real trajectory with a full transcript, and a two-tool turn
with one tool result does not reach it. One data point that this row's prompt treated as the shape
to measure; it is not reproducible from a cold agent turn.

`thinking_tokens` reads `unsupported` on every run: Ollama does not report them and LoadCoach
records the `UNSUPPORTED` sentinel rather than a zero (ADR-0016), so the "thinking_tokens per run"
column §0.3 asked for cannot be filled on this provider. `output_tokens` carries the fact instead.

Raw samples: the scratchpad's `measure.json` and the scratch database's `job_attempts`. Nothing
from the harness is committed except the table.

## 5. What the five profiles ship with

**The field unset, on all five** — §0.4's third branch, and a legitimate close of the row: the lever
is reachable from configuration, which is what was missing. `tools.plan`'s comment now carries the
four cells, what `think = false` did to it and why, so the next person to reach for the lever reads
the result before pulling it. No profile outside the five was touched, and `tools.agent` (the
parent) is unchanged.

## 6. Exit conditions (kickoff §10)

| # | Condition | Result |
|---|---|---|
| 1 | `/models` shows a remote registration, and the shipped block's defaults | **Both shown.** On a scratch install whose only registration is `[providers.hosted]` with `remote = true`: `{"canonical_id": "ollama/gpt-oss:20b@sha256:17052f91a42e", "provider_name": "hosted", "is_remote": true}`. On one with the shipped single `[provider]` block: `"provider_name": "ollama", "is_remote": false` — **not** `""` (§8). The `""`/`false` pre-registration row is asserted by `tests/integration/test_multi_provider.py` |
| 2 | A `think = false` profile puts top-level `"think": false` on the Ollama wire | **Shown once**, through a recording pass-through in front of Ollama: `{"model": "gpt-oss:20b", "stream": true, "keep_alive": "5m", "options": {"temperature": 0.1, "num_predict": 4096, "num_ctx": 16384}, "format": "json", "think": false}` |
| 3 | `think` unset produces 1.1.0's `SamplingParameters` | **Golden**, `tests/integration/test_generate.py::test_a_profile_with_no_think_builds_the_request_1_1_0_built` — asserted on the request ModelRack actually received |
| 4 | The routing consequence is visible in an explanation | **Yes**, `test_a_provider_that_cannot_carry_think_is_a_named_routing_rejection`: `NO_ELIGIBLE_MODEL` whose candidates carry `capability_unsupported`, `capability = "thinking_control"`, `required_by = "task_profile"`, and the provider was never called |
| 5 | The four-cell table in the handoff and the `tools.plan` comment | §4 above and `config/task_profiles.toml` |
| 6 | The five profiles carry what §0.4 decided, with the version decision applied | `think` unset on all five; all five stay at `1.0.0` (§3 decision 4) |
| 7 | Snapshot regenerated, mirrors `cmp`-identical, ADR indexed | Snapshot moved by **one line** (§8); seven mirrors `cmp`-identical; ADR-0099 in `adr/README.md`'s table and its dated paragraph |
| 8 | `loadcoach 1.1.1` prepared | `2a7ac58`, unpushed, untagged |
| 9 | Full gate green, interpreter and invocations named | §1 |

## 7. Gold standards and the house method

Docstring-first on every new public surface, including what each refuses: `TaskProfileExecution.think`
names its three states and the routing consequence, `sampling_for` names the byte-identical
promise, `_model_to_json` names what `""` and `False` mean and what is never inferred from them,
and `GenerateBody._think_is_a_switch` names what it raises and why refusing beats passing down.
`from __future__ import annotations` everywhere; no `Any` at a public boundary; no new
`# type: ignore`. No `.importlinter` contract, coverage floor or gate was weakened; nothing was
marked skip. `pytest-randomly` stayed on for every full run — `-p no:randomly` was used only to
isolate single files while iterating.

## 8. Things this prompt said that turned out not to be true

* **"On a fresh database with the shipped single `[provider]` block, `""` and `false`."** The
  singular `[provider]` block **is** a registration, named after its kind (ADR-0077), so discovery
  records `provider_name = "ollama"`. `""` is what migration `0008` left on a row discovered
  *before* registrations had names, and that is the only way to see it on a live install. The e2e
  test asserts `"fake"` for the fake block and the integration test constructs the `""` row.
* **"`docs/openapi.json` will almost certainly not change."** It did not change for the render —
  regenerated after gate B, byte-identical, exactly as predicted, because `GET /models` returns an
  untyped mapping. It changed at gate E for `info.version`, `1.1.0` → `1.1.1`, one line, and the
  contract test caught it. No response model was added.
* **"`requirements/ci.lock` … recompile to 0.7.1."** Doing it needs `--upgrade-package modelrack`:
  `pip-compile` honours the existing output file's pins, so a plain recompile leaves `0.7.0` in
  place and reports success. The committed lock had also been resolved on **Python 3.14** despite
  `requirements/README.md` saying 3.13; this row's recompile puts it back on 3.13, which is the
  second line of the diff.
* **"I2 §10 run 1 … the shape you are measuring."** It is not reproducible from a cold
  `tools.agent.local_fast` turn (§4). The pathology needs the transcript depth of a real
  trajectory, so the agent half of the measurement measures a healthy turn in both cells.
* **"§0.3: empty means `text == ""`."** Through LoadCoach that is unmeasurable on `tools.plan`,
  because the corrective retry absorbs the empty draft and answers `{}` (§4). The table reports
  *delivered* and the per-attempt facts instead.
* **"`thinking_tokens` per run."** `unsupported` on Ollama, every run.
* **The prompt's own §0.3 latency expectation ("~58 s median at 4 096, budget an hour").** The
  whole 24-generation pass took under five minutes: the median unset `tools.plan` job was 12.9 s.
  G2's 58 s was measured with a cold model and a different harness.

## 9. What J1 inherits

* **PromptCadence's two hash-pinned LoadCoach snapshots now differ from the shipped files.**
  `tests/contract/loadcoach_openapi.json` (`info.version`, and nothing else) and
  `tests/contract/loadcoach_task_profiles.toml` (the `tools.plan` comment). Refreshing them is a
  PromptCadence change — 1.0.1 or a J row — and was deliberately not made here.
* **The remote-provider fact now reads from a real LoadCoach.** ADR-0098 rule 1's read of
  `/models` finds `is_remote` and `provider_name` on 1.1.1, with no PromptCadence change behind
  it. A J row that registers a remote provider will see `has_remote_provider` become true at the
  next trajectory, and the two recorded refusal reasons stop being the only outcome.
* **`sampling.think` is available to PromptCadence** without a LoadCoach profile edit, which is how
  a tier can be measured against a model that *does* honour the control.
* **A finding that is ModelRack's or Ollama's, not this row's:** four of six streamed
  `think: false` requests to `gpt-oss:20b` ended with
  `ProviderProtocolError: The stream from … ended without a terminal chunk` after 1.3 s, while a
  hand-made stream of the same shape completed normally with `done: true`. Intermittent, and not
  investigated here — the row's stop rules put ModelRack out of scope.

## 10. Left for the operator

1. **The push list:** `docs` (two commits, `e8ef0ee` and `2385d20`) and `LoadCoach` (four commits,
   `8a57472` through `2a7ac58`). Nothing is pushed; no push dry-run was run.
2. **The tag and the publish are yours.** `loadcoach 1.1.1` is release-committed and untagged.
3. **The 1.1.0-versus-1.1.1 sequencing question was not answered at kickoff**, so the default in
   the prompt was taken: 1.1.1 is prepared as its own release commit on top of the 1.1.0 one.
   `git tag` still lists only `v1.0.0`, and PyPI still holds `loadcoach 1.0.0`. Whether `v1.1.0` is
   tagged first or 1.1.1 becomes the first published 1.1.x is still open, and changes nothing that
   was built.
4. **Model deviation:** scheduled Sonnet 5 · high, ran on Opus 5 (model-assignment §3.5).
5. **One incident, recorded because the tree-integrity rule exists.** A `pkill` killed its own
   shell before a heredoc had written a scratch `config.toml`, so a `loadcoach serve` started with
   `--config <a path that did not exist>`, fell back to the defaults, and briefly bound `:8766`
   against **the operator's own data directory** (`~/.local/share/loadcoach/loadcoach.sqlite3`). It
   served two read requests and was killed. The database's mtime is unchanged (2026-09-06 15:46,
   hours before this session), its `alembic_version` is still `0014`, and no migration or discovery
   ran against it — the `db upgrade` and `models refresh` of that sequence had already run against
   the scratch directory. Nothing to repair; recorded so the next reader does not have to
   re-derive it.

## 11. §13's read-only items, answered

* **(a) `loadcoach models list` (the table form) showing the registration and the egress class.**
  Worth doing and not done here. The table is one line per model at fixed widths — a 60-column
  canonical ID, a 30-column status, then the capabilities — and the registration name is short
  (`ollama`, `hosted`) while the egress class is one word. The honest cost is one more column and
  the capability list losing width on an 80-column terminal; the alternative is a marker on the
  status column, which hides the registration's name. `--json` already carries both from this row.
* **(b) Whether LoadCoach's `tool_calls` events carry a digest I2 §5's argument applies to.**
  **No.** There is no `sha256` or digest of tool-call arguments anywhere in LoadCoach: the wire
  fields are `id`, `name` and `arguments`/`arguments_fragment`, the events carry the same, and
  nothing hashes them. I2 §5's mismatch is PromptCadence's alone and has no LoadCoach analogue.
* **(c) Whether `tools.agent` (the parent) should inherit `think` at 1.2.** A note, not a change:
  it should not inherit it *by default*, because the five children are what PromptCadence routes
  through and the parent is what an operator reaches for directly. If a later measurement finds a
  model that honours the control, the value belongs on the children that measured it, not on a
  parent that would silently impose it on every unrelated caller of `tools.agent`.
