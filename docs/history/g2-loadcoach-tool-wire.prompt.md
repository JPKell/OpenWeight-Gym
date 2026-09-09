# Kickoff — G2: LoadCoach's tool wire — `/generate` carries tool definitions and `tool_calls`, and the corrective retry survives an empty answer

**Row:** G2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · high**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
A wire contract inside `/api/v1` that H2 then generalizes, plus the corrective's failure semantics.
**Repositories:** `/home/jpk/ai/suite/docs` (first), `/home/jpk/ai/suite/LoadCoach` (the row's
weight), then `/home/jpk/ai/suite/PromptCadence` (the last two commits).
**Ships:** **nothing.** LoadCoach's changelog gains an `## [Unreleased]` section; **no bump, no tag,
no publish** — this rides the next LoadCoach minor (1.1 at H2 if H2 lands first). PromptCadence is
past `0.9.0b0`; its changes go under `## [Unreleased]` too.
**Overnight:** **no.** [§2.12](docs/roadmap/model-assignment.md) puts batch G on the never-overnight
list. Daytime, reviewed same day.
**Runs after:** G1 (done 2026-09-04, `docs/history/G1_HANDOFF.md`). **Runs before:** I2's sandboxed-tool
verification (a hard edge, outstanding-work §3) and **G3**, which edits the same `services/loop.py`
this row's last commit touches.
**Not in this session:** per-step retry policy (**G3** — see §13); LC-E1 / remote execution (**H2**);
the injection corpus (**P9**); anything that bumps or publishes either package.

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **LoadCoach `main` is at `dfbf2d8`**, clean and level with `origin`; `__about__.py` says
  `1.0.0` and `CHANGELOG.md` already carries an `## [Unreleased]` block (E6's fake-provider fix).
  **PromptCadence `main` is at `952af18`**, clean and level — `c9ed99a` cut `0.9.0b0`, which the
  operator has not yet tagged or published. **docs `main` is at `3d7d11f`**, clean and level.
  **Confirm** `git status -sb` in all three at the start and at the end (CLAUDE.md, working-tree
  integrity).
* **Half of this row already exists, on the outbound side.** LoadCoach's *response* has carried
  tool calls since M4: `output.tool_calls` is documented in `api.md` §4, populated from
  `services/execution.py:647`, persisted as `jobs.tool_calls_json` (migration `0003`), scrubbed by
  `services/retention.py:101`, and PromptCadence parses it at
  `infrastructure/loadcoach.py:573`. **The missing half is entirely inbound**: `GenerateBody` has
  no `tools`, `MessageBody` has no `tool_calls`, and `GenerationRequest` is built at
  `services/execution.py:617` without a `tools=` argument. Read the row as *"close the inbound
  half"*, not *"add tool support"*.
* **ModelRack's shapes exist and are the ones to use, unchanged.** `ToolDefinition`
  (`name`, `description`, `parameters` — a JSON Schema passed to the provider **verbatim**,
  `types.py:167`), `ToolCall` (`id`, `name`, `arguments`, `raw_arguments`, `types.py:200`),
  `Message.tool_calls` / `Message.tool_call_id` with the three refusals at `types.py:266`–`:280`,
  and `GenerationRequest.tools` at `types.py:567` — which already raises
  `CapabilityUnsupported` when a provider has not declared `tool_calling`. **ModelRack is not
  yours this row.** If you find yourself editing `py/ModelRack`, stop: the shape you need is
  already there, or the row has grown.
* **PromptCadence already holds the definitions to send.** `services/tools.py:175`
  `ToolCatalogEntry` carries `name`, `description` and `parameters` (from `ToolSpec.args_schema`,
  `:482`) and `as_payload()` renders them. The intent's declared allowlist is what a step may call.
  Nothing new needs designing on that side — it needs mapping onto the wire.
* **The capability vocabulary is already wired both ways.** SetSpec's name is `tool_use`;
  `domain/registry.py:52` maps `ModelCapabilityFlag.TOOLS → "tool_use"`;
  `domain/routing/constraints.py:371` maps the constraint `"tool_use"` to the subject field
  `supports_tool_use` (`domain/routing/subject.py:116`), which is populated from
  `capabilities.tool_calling` at `services/execution.py:1705` and `cli/commands/route.py:104`.
  The five `tools.agent*` profiles already declare `requires_capabilities = ["tool_use"]`
  (`config/task_profiles.toml`). **What does not exist is a request-level rule** — see §0.2(1).
* **`tools.plan` requires `structured_output`, not `tool_use`** (`task_profiles.toml:551`), with
  `max_output_tokens = 4096`, `response_format = "json"`, `max_attempts = 3`,
  `max_output_chars = 50000`. It is not a tool-calling profile and item 4 is not about tools —
  it is about a reasoning model spending its whole output budget thinking under JSON mode.
* **Ollama is installed and running** with gpt-oss:20b among the pulled models — the model G1
  measured. **No LoadCoach is listening on 8766** as this was written; the demonstration needs you
  to start one. **Stop any demo PromptCadence on 8768 before running PromptCadence's gate** —
  G1 found four CLI tests read a live server if one is up (`docs/history/G1_HANDOFF.md` §14.6).
* **Python 3.13.15; there is no python3.12 on this host.** Name the interpreter and every exact
  invocation (M5C-13).
* **Never `git push`.** Commit at every gate boundary; leave pushing and any release to the
  operator. Do not run a push dry-run either.

## 0.1 Why this row exists — read G1's evidence before you design anything

G1 stood the whole harness up on real LoadCoach + Ollama and the M11 beta shipped with spec §20 #2's
*sandboxed tools* clause **unmet**, for a reason outside that row. `docs/history/G1_HANDOFF.md` §9.3 and the
verbatim transcript in §10.4 are the specification for this row's first three items. The failure
chain, in order:

1. A model is **never told which tools exist**. gpt-oss:20b invented `repo_browser.list_dir`,
   `container.exec` and `assistant<|channel|>commentary` out of its own vocabulary and sent
   arguments as a bare string.
2. Every invented call was refused and recorded — `unknown_tool`, `args_invalid`, an
   `undeclared_tool` deviation each. **That part is correct and must stay exactly as it is.**
3. The assistant turn that answered with calls and no text **could not be replayed**: LoadCoach's
   `MessageBody` has no `tool_calls`, and ModelRack refuses an assistant message with neither
   content nor calls. PromptCadence's `289a38e` works around it by replaying the turn as
   `[tool_calls]`-prefixed **text** (`services/loop.py:1615` `_transcript`, `:3099`
   `_render_tool_calls`). That workaround is what this row's last commit deletes.
4. Ollama's own tool-call parser then rejected the model's next answer
   (`ProviderRejected: error parsing tool call`) and LoadCoach halted the job with
   `ALL_CANDIDATES_FAILED`.

Separately (§9.1–9.2): the planning call returned an **empty document** — ~50 % of the time at a
1.6k-character prompt, **100 %** at 4.4k — and LoadCoach's own corrective retry then crashed on it,
leaving the job `executing` with its attempts never written, so the `finish_reason` behind the empty
answers is unrecoverable to this day. Directly through Ollama the shape was `done_reason=length`,
content empty, 4096 tokens of thinking.

## 0.2 The four items, and the decision each one hides

The row lists four items. Each has a decision inside it that is yours to take and to record — in the
handoff, and in an ADR where it outlives the row (CLAUDE.md: a missing architectural decision is a
docs defect, and you close it with an ADR rather than an implementation).

1. **`tools` on `GenerateBody`, passed through routing to the provider.** The decision:
   *what a request carrying `tools` does to routing.* The row is explicit — **a candidate without
   `tool_use` is a routing rejection, never a silent drop.** So a body with a non-empty `tools`
   imposes `tool_use` as a **hard constraint on that request**, on top of whatever the profile
   requires, and a profile that requires nothing (`general.chat`, `tools.plan`) still gets the
   rejection with a reason a caller can read. Weights do not move; this is a filter, not a score.
   Decide and record: whether an empty `tools: []` differs from `tools: null` (recommendation:
   identical, and neither imposes anything), and what the rejection reason string is, since
   routing's rejection reasons are a caller-visible vocabulary.
2. **`tool_calls` on `MessageBody`, and the `tool` role with `tool_call_id`.** The `tool` role and
   `tool_call_id` **already exist** on the wire (`generate.py:76`); what is missing is
   `tool_calls` on an assistant turn, so a transcript with tool turns replays natively. The
   decision: *how strictly the wire validates a transcript's internal consistency.* ModelRack
   already refuses a non-assistant turn carrying `tool_calls`, a `tool` turn with no
   `tool_call_id`, and a message with neither content nor calls (`types.py:266`–`:280`) — those
   refusals must surface as `VALIDATION_ERROR` with a field name, not as a 500. Whether LoadCoach
   *additionally* checks that every `tool_call_id` matches a call in some earlier assistant turn is
   the open question: recommendation **yes**, because an unmatched id is a caller bug that a
   provider will otherwise turn into a confusing model failure — but state the choice either way.
3. **The corrective's failure semantics.** `services/execution.py:710` appends
   `Message(role=Role.ASSISTANT, content=previous_text)` unconditionally, so an empty
   `previous_text` builds a message ModelRack refuses. Two things to fix, and they are separate:
   (a) `corrective_turns` never appends an empty assistant turn — an empty previous answer is
   described in the correction prompt's `previous_output` rather than replayed as a turn; and
   (b) **a corrective whose request ModelRack refuses fails the job with its attempts written**
   instead of leaving it `executing` until a cancel or a watchdog. (b) is the one that matters
   most: the reason G1 cannot tell you the `finish_reason` behind the empty answers is that those
   attempt rows were never persisted. The decision: *which job status a construction-time refusal
   lands in* — it is not a provider failure and not a routing failure. Record the choice against
   `api.md` §10's error vocabulary and `data-model.md`'s attempt outcomes.
4. **`tools.plan`'s output budget, and whether a profile can ask for reduced thinking.**
   Measure before you change anything: sample the current profile against gpt-oss:20b enough times
   to have a number, then again after each lever. The levers are `max_output_tokens` (4096 today,
   with the model spending all of it thinking) and, **if and only if** ModelRack's Ollama provider
   exposes a `think` control, a profile field for it. Check whether it does before you plan around
   it — if it does not, that half of item 4 is a **finding written into the handoff and the row**,
   not a ModelRack change smuggled into this session. A task profile is routing intent
   (`routing.md` §2); a new execution field is a schema change to shipped configuration, so it is
   documented in `apps/loadcoach/spec.md` and the profile file's header comment, and it needs the
   same care as any wire change.

## 0.3 What "additive within `/api/v1`" means, and what it forbids

LoadCoach is `1.0.0` and published. This row adds optional fields to a request body and adds
nothing to a response. Therefore:

* **Every existing caller must be byte-unaffected.** A body with no `tools` and no per-message
  `tool_calls` produces exactly the request it produces today, including the `GenerationRequest`
  it builds. Prove it with a contract golden, not by reading the diff.
* `model_config = ConfigDict(extra="forbid")` stays on both bodies. The new fields are declared,
  not permitted by loosening.
* **No new route, no `/api/v2`, no version negotiation.** H2 generalizes this shape; it does not
  inherit a compatibility flag.
* PromptCadence's fake LoadCoach (`tests/fakes/loadcoach_app.py:161`–`:216`) mirrors the real
  bodies field for field. Its refusals are copied from the real ones so the contract test means
  something — `tests/contract/test_loadcoach_contract.py` is where the two repos' agreement is
  asserted, and it is the file a reviewer will read first.

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb
git -C /home/jpk/ai/suite/LoadCoach status -sb
git -C /home/jpk/ai/suite/PromptCadence status -sb
cd /home/jpk/ai/suite/LoadCoach && source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show modelrack setspec | grep -E "^(Name|Version)"
```

PromptCadence has its own venv; activate it in its own directory when you get to gate F. Every
scratch database, config file, workspace and log goes in the session scratchpad — **never** the
repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory. Nothing at the workspace root is versioned; do not overwrite a
  root file you did not create.
* The finish line, **in each repo you touch**: `ruff format --check . && ruff check . &&
  mypy src tests && lint-imports && pytest -m "not live and not performance"` green,
  `CHANGELOG.md` updated, **one Conventional Commit per gate**, committed at each gate boundary.
* `pytest-randomly` is on; a seed-only failure is a real bug, not a flake.
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names, keyword-only optionals and booleans, frozen slotted value objects, pydantic wire
  models, SQLAlchemy models never leaving the repository layer, `mypy --strict`, line length 100.
* `web → cli → services → domain`; `domain` imports no framework. Handlers call one service method
  and render. Never weaken `.importlinter` to make an import work.
* Async at the HTTP edge only (ADR-0003); SSE, never WebSockets (ADR-0004).
* Coverage floors: 85 % applications. Both repos here are applications.
* **Never `git add -A`.** Stage named paths. Every workspace `docs/` edit is mirrored into
  `LoadCoach/docs/` (and `PromptCadence/docs/`) byte-identically and **`cmp`-proved**.

## 3. Reading list, in this order

1. **`docs/history/G1_HANDOFF.md` §9 and §10.4 in full** — the evidence. §10.4 is the transcript this row makes
   come out differently; read it before you write a line. Then §13 (what must not be relitigated)
   and §8 (the I2 hazards, one of which this row changes the shape of).
2. `docs/apps/loadcoach/api.md` **§4** (the `/generate` body, the response's `output.tool_calls`,
   the "sends the caller's text unmodified" promise this row must not break), **§5** (jobs and
   their statuses), **§10** (the error vocabulary), **§12** (client guidance).
3. `docs/apps/loadcoach/data-model.md` — the `jobs` and `attempts` rows, what is persisted per
   attempt and when. Item 3(b) is a statement about this file.
4. `docs/apps/loadcoach/routing.md` **§2** (a task profile is routing intent, not a prompt) and the
   constraint vocabulary; then `domain/routing/constraints.py` and `subject.py` for how a hard
   constraint rejects with a reason today.
5. ModelRack: `py/ModelRack/src/modelrack/types.py` `ToolDefinition` (`:167`), `ToolCall` (`:200`),
   `Message` (`:240`–`:285`), `GenerationRequest.tools` (`:538`, `:567`) — **and the spec §14 rule
   that ModelRack never executes a tool and never validates its schema.** LoadCoach inherits that
   rule exactly: it is a router, not an executor.
6. `docs/apps/promptcadence/spec.md` **§9** (the tool discipline) and **§20 #2** (the clause this
   row unblocks), `lifecycle.md` **§4.3** (the intent's declared allowlist — the thing that decides
   *which* definitions travel) and **§5** (`undeclared_tool`, which stays exactly as it is).
7. ADRs: **ADR-0041** (a caller's schema does not travel through a router — the reason `tools` is
   passed through verbatim and never validated), **ADR-0051** (a plan never leaves PromptCadence),
   **ADR-0044** (a state change and its event are one write), **ADR-0056** (one immutable intent
   per turn — nothing here widens one).
8. `docs/standards/` on API versioning and additive change, before you touch a published body.

---

## 4. The shape of the work — six gates

A → docs first. B → `tools` inbound, and the routing rule. C → `tool_calls` inbound, and native
replay. D → the corrective's failure semantics. E → `tools.plan`'s levers, measured. F →
PromptCadence: the fake, the client, the deletion of the workaround, and the live demonstration.

A–E are LoadCoach; F is PromptCadence. **Do gate D before gate F** even though it is the least
glamorous: without it, a failure inside the live demonstration leaves you with an `executing` job
and no attempt rows, which is precisely the position G1 ended in.

## 5. Gate A — the documents, amended first

Workspace `docs/` first, then the byte-identical mirror into `LoadCoach/docs/apps/loadcoach/`,
`cmp`-proved in the commit message.

* `api.md` §4: `tools` on the request (shape, semantics, the routing rule from §0.2(1), the
  statement that LoadCoach passes `parameters` to the provider **unmodified** and never executes a
  call), `tool_calls` on a message (shape, the internal-consistency rule you chose), and a worked
  example body carrying a tool turn. §10 gains whatever error the new refusals raise.
* `data-model.md`: what an attempt persists when a request is refused before it reaches a provider
  (item 3(b)), and anything the new fields add to a job row.
* `apps/loadcoach/spec.md` and the `task_profiles.toml` header comment if gate E adds a profile
  field.
* If a decision from §0.2 outlives the row — the request-level `tool_use` rule is the likeliest —
  **write the ADR** in `docs/adr/` at the next free number (0074 is the highest today; confirm),
  accepted, and reference it from `api.md`. ADRs are superseded, never edited.

**Commit:** `docs(loadcoach): the tool wire — tool definitions in, tool calls on a message`.

## 6. Gate B — `tools` inbound, and the routing rejection

* `tools` on `GenerateBody`: a list of `{"name", "description", "parameters"}`, `extra="forbid"`,
  a non-empty name required, `parameters` an object passed through verbatim. Map to
  `modelrack.ToolDefinition` in the same place `messages_of` maps messages (`generate.py:132`),
  and hand them to `GenerationRequest(tools=…)` at `services/execution.py:617`.
* The routing rule: a request with a non-empty `tools` requires `tool_use` of every candidate.
  Express it through the existing constraint machinery — `constraints.py:371` already knows the
  name — rather than a new parallel path. A rejection carries a reason; a caller that sent tools to
  a model that cannot use them gets `NO_ELIGIBLE_MODEL` naming why, never a served request whose
  tools quietly evaporated.
* Guard the provider edge: ModelRack raises `CapabilityUnsupported` if tools reach a provider that
  has not declared `tool_calling`. After the routing rule that should be unreachable — prove it is,
  with a test that asserts the rejection happens at routing and the exception is never the path.
* Tests: the routing rejection with a reason; passthrough of `parameters` verbatim (a schema with
  an unusual key survives untouched); a body with no `tools` builds today's `GenerationRequest`
  exactly (the compatibility golden from §0.3).

**Commit:** `feat(generate): a request may carry tool definitions, and routing requires tool_use`.

## 7. Gate C — `tool_calls` inbound, and a transcript that replays natively

* `tool_calls` on `MessageBody`: a list of `{"id", "name", "arguments"}` (and `raw_arguments` if
  you carry it — decide, and say why in the docstring), assistant-only, mapped to
  `modelrack.ToolCall`.
* Surface ModelRack's three refusals as `VALIDATION_ERROR` with the offending field, plus the
  internal-consistency check you chose in §0.2(2).
* Tests: an assistant turn with calls and **no content** now replays (this is the exact turn that
  broke G1 — `docs/history/G1_HANDOFF.md` §10.4, `turn 3 s1`); a `tool` turn answering it by `tool_call_id`
  replays; each refusal is a `VALIDATION_ERROR` naming its field; and the round trip — a response's
  `output.tool_calls` fed straight back in as the next request's assistant turn — works without the
  caller reshaping anything. That round trip is the whole point of the row; make it a named test.

**Commit:** `feat(generate): a transcript carries an assistant turn's tool calls`.

## 8. Gate D — the corrective survives an empty answer, and a refused request writes its attempts

* `corrective_turns` (`services/execution.py:684`) never appends an empty assistant turn. Its
  docstring says what it refuses.
* A request ModelRack refuses at construction **fails the job**, with the attempt rows written and
  the status you chose in §0.2(3). The job does not stay `executing`.
* Tests: the empty-first-answer corrective (the G1 crash, as a regression test named for it); a
  construction-time refusal leaves a `failed` job whose attempts are readable and whose
  `finish_reason` is recoverable; the happy-path corrective is unchanged.
* This is the gate that turns G1's open question into an answerable one. If, once attempts are
  written, you can finally see the `finish_reason` behind an empty planning answer — **record it
  in the handoff.** It is the missing half of the `native.plan` finding.

**Commit:** `fix(execution): a corrective never replays an empty answer, and a refused request writes its attempts`.

## 9. Gate E — `tools.plan`'s output budget, measured

* Measure first, with the real model, and write the numbers down: the empty-document rate at the
  current profile, then per lever. G1's baseline is ~50 % at a 1.6k prompt and 100 % at 4.4k.
* Lever 1: `max_output_tokens`. Lever 2: reduced thinking, **only if** ModelRack's Ollama provider
  exposes a control for it — check, and if it does not, that is a finding for the handoff and a
  note into the G2 row, not a ModelRack change.
* A profile change is shipped configuration: changelog, docs, and no code where configuration will
  do. Do not touch the other four harness profiles E4 shipped.

**Commit:** `feat(profiles): tools.plan's output budget, measured against a reasoning model` (or
`docs(loadcoach): the thinking-control finding` if the measurement says leave it alone — a measured
"change nothing" is a legitimate outcome of this gate, provided the numbers are in the handoff).

## 10. Gate F — PromptCadence: the fake, the client, the deletion, and the demonstration

In `/home/jpk/ai/suite/PromptCadence`, its own venv, its own gate.

1. **The fake gains the same fields** (`tests/fakes/loadcoach_app.py`), with the real refusals
   copied, so a hostile-model journey can script a **declared** call — the thing the fake could not
   produce before (`docs/history/G1_HANDOFF.md` §14.6). Update
   `tests/contract/test_loadcoach_contract.py` and say in the commit message how you verified the
   fake against the running real LoadCoach, not just against itself.
2. **The client sends the definitions** (`infrastructure/loadcoach.py`): the step's declared
   allowlist, rendered from `ToolCatalogEntry` (`services/tools.py:175`) — **the intent's
   allowlist, nothing wider.** A tool the intent did not declare is not offered to the model, and
   `undeclared_tool` stays exactly what it is for anything the model invents anyway.
3. **Delete the workaround**: `_render_tool_calls` (`services/loop.py:3099`) and its use in
   `_transcript` (`:1615`); replay `tool_calls_json` on the wire natively. `turns.tool_calls_json`
   keeps persisting what an assistant turn requested — that is §20 #8's park-and-resume and it
   stays.
4. **Contract 1 must stay green with no new allowance** (`tests/contract/test_governance_invariance.py`).
   Nothing here is a governance change; if the diff moves, you have changed something you did not
   mean to.
5. **The demonstration, verbatim into the handoff.** Real LoadCoach `1.0.0` (this working tree) on
   8766 against Ollama, PromptCadence on 8768, scratch data directories, **shipped defaults and no
   `PROMPTCADENCE_TIERS__*` overrides** — the same conditions as `docs/history/G1_HANDOFF.md` §10. Run
   `promptcadence run "Summarize the files in ./notes" --follow` on the planned path, with a
   `./notes` directory you create in the scratchpad. Show the event stream, the
   `tool_call_records` rows, and the turns. Then the bypassed path, for the pair.
6. Note for I2/P9, do not fix here: natively-replayed `arguments` are **still uncapped model
   output going back onto the wire**. `_render_tool_calls` was the capped-nothing hazard
   `docs/history/G1_HANDOFF.md` §8 flagged; deleting it does not remove the hazard, it moves it. Write it up.

**Commits:** one for the fake + contract, one for the client + the deletion. The second is this
row's last commit.

## 11. Exit conditions — all of these, demonstrably

1. A planned PromptCadence trajectory (`summarize the files in ./notes`) on **real LoadCoach +
   Ollama with shipped defaults** completes, with **at least one declared sandboxed call recorded
   in `tool_call_records`** with a non-refused outcome. Transcript in the handoff.
2. `[tool_calls]` text rendering is gone from PromptCadence, and a tool-calling assistant turn
   replays natively on the wire.
3. A request carrying `tools` whose candidates lack `tool_use` is a routing rejection with a
   reason — not a silent drop, and not a `CapabilityUnsupported` from the provider edge.
4. A body with neither `tools` nor per-message `tool_calls` produces byte-identically the request
   it produced at `dfbf2d8` (the compatibility golden).
5. An empty first answer no longer crashes the corrective, and a request ModelRack refuses leaves a
   **failed** job with its attempts written and their `finish_reason` readable.
6. `tools.plan`'s empty-document rate is a **measured number** before and after, in the handoff,
   whatever the decision was.
7. Full gate green in LoadCoach **and** PromptCadence, interpreter and exact invocations named.
8. Workspace `docs/` and both mirrors `cmp`-identical.

## 12. Closing duties

1. Full gate in each repo; interpreter and exact invocations named (M5C-13).
2. **`G2_HANDOFF.md` at the workspace root**, house shape: the gate results; each of §0.2's four
   decisions and why; the measured `tools.plan` numbers; the verbatim demonstration; what H2
   inherits (it generalizes this wire shape — say what is settled and what it may still choose);
   what I2's sandboxed-tool verification can now do that it could not; the moved uncapped-arguments
   hazard; **and anything this prompt said that turned out not to be true** — that section has been
   the most useful part of the last five handoffs.
3. Say plainly what is left for the operator: push three repos; **no tag, no publish** — LoadCoach's
   minor is cut at H2, PromptCadence's `0.9.0b0` tag is still theirs and unaffected by this row.
4. Reviewed, not overnight: leave a diff a reviewer can read — one commit per gate, each message
   saying what it made true.
5. Record any **model deviation** from the scheduled Opus 5 · high
   ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
6. Update the G2 row in `docs/roadmap/outstanding-work.md` to **Done**, in the house form: date,
   commits, what held, what did not, and what the next rows inherit.

## 13. Stop rules

* **LoadCoach never executes a tool.** It routes, it passes definitions down, it returns calls up.
  ModelRack's spec §14 rule is inherited verbatim; a sandbox in LoadCoach would be an architecture
  breach, not a feature.
* **LoadCoach never validates a tool's `parameters` schema** (ADR-0041). Verbatim passthrough, the
  same rule that keeps a caller's response schema out of the router.
* **Do not build the per-step retry** — that is G3, it lands in the same `services/loop.py`, and
  doing it here makes both diffs unreviewable. A step failure in the demonstration still halts the
  trajectory; that is correct today.
* **Do not weaken `extra="forbid"`** on either body, and do not add a compatibility flag or a
  route version.
* **Do not change what `undeclared_tool` means**, do not widen an intent's allowlist to make a model
  happy, and do not offer a tool the intent did not declare.
* **Do not widen PromptCadence's contract-1 allowance list.** A moved diff is a finding.
* **Do not touch ModelRack**, do not widen a `setspec` pin, and do not touch the other four harness
  profiles.
* **Do not bump, tag or publish either package. Do not `git push`.**
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a gate boundary.

## 14. If you finish with capacity left

Read-only, in priority order: (a) **what H2 inherits** — this wire shape is the one LC-E1 and the
remote path generalize; write the note that says which parts are settled contract and which are
still open. (b) **The P9 corpus**, given that tool *definitions* now travel: a description field is
caller-written prompt content going into a model's context, so the injection surface is no longer
only the plan document. (c) Whether the response side has a matching gap — `output.tool_calls` has
existed since M4 but has never been exercised end to end by a real model until now; say whether its
shape survived contact.
