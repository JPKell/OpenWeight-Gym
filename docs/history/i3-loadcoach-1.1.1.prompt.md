# Kickoff — I3: LoadCoach 1.1.1 — `provider_name` and `is_remote` in `GET /models`, and a task profile that can ask for reduced thinking

**Row:** I3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Sonnet 5 · high**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
Daytime preferred: the row is small, but its second half has a measurement in it that a person
should watch once. Record any deviation ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
**Repositories:** `/home/jpk/ai/suite/docs` first (the ADR and the two document edits), then
`/home/jpk/ai/suite/LoadCoach`. Nothing else.
**Ships:** **`loadcoach 1.1.1` prepared, not published** — the version bump, the changelog and the
release commit are yours; **`git push`, the tag and the publish are the operator's** (standing
instruction of 2026-09-04). Do not run a push dry-run.
**Runs after:** **I2** (done 2026-09-06, `docs/history/I2_HANDOFF.md`).
**Runs before:** **J1** — a hard edge (`outstanding-work` §3): the J rows adopt a PromptCadence
whose remote-provider fact must be readable from a real LoadCoach, and the render lands first.
**Not in this session:** PromptCadence, ModelRack, FreeWeight, IdeaPress. This row changes what
LoadCoach *renders* and what a task profile *may ask for*; the consumer reads it unchanged.

---

## 0. Machine facts, verified 2026-09-06 before this prompt was written

Confirm the marked ones; do not re-derive the rest.

* **LoadCoach `main` is at `93063bd`** ("fix(routing): the evidence gate admits only a signal that
  scores"), clean and level with `origin`. `__about__.py` says `1.1.0`. **Confirm** `git status -sb`
  in both repos at the start and at the end.
* **`loadcoach 1.1.0` is neither tagged nor published.** `git tag` lists `v1.0.0` only, and PyPI holds
  `loadcoach 1.0.0`. `CHANGELOG.md` opens at `## [1.1.0] — 2026-09-06` with **no `## [Unreleased]`
  section** — add one, and 1.1.1's entries go under it until the release commit. **Ask the operator
  at kickoff** whether 1.1.0 is to be tagged first or 1.1.1 becomes the first published 1.1.x; the
  answer changes nothing you build, only the sentence in the handoff. Default if unanswered:
  prepare 1.1.1 as its own release commit on top of the 1.1.0 one.
* **The venv is Python 3.14.4** (`.venv/bin/python --version`) holding `modelrack 0.7.0` and
  `baseaicore 0.4.2`. `/usr/bin/python3.13` exists if you want a second interpreter for the gate
  report. Name the interpreter and the invocation (M5C-13).
* **`modelrack 0.7.1` is on PyPI** (`pip index versions modelrack`), one fix over 0.7.0: a GGUF
  descriptor now states `head_dim` when the file omits it, without which *every GGUF-served
  candidate was ineligible on any machine with GPU telemetry* (ModelRack `CHANGELOG.md` 0.7.1).
  `pyproject.toml` admits it (`modelrack>=0.7,<0.8`); `requirements/ci.lock:711` pins `0.7.0`.
  **Recompile the lock to 0.7.1 in this row** and say so in the changelog — a 1.1.1 that ships
  the fix by default is worth one lock line. Not a decision; do it.
* **Half (a) is already two lines deep.** `RegistryEntry` carries `provider_name` (default `""`,
  "not recorded") and `is_remote` (default `False`) at `services/models.py:351`–`:355`;
  `_model_to_json` at `web/routes/models.py:27`–`:46` renders neither; the generate response
  renders `is_remote` at `services/execution.py:525`; the Models page already shows
  `provider_name` (`templates/models/index.html:23`). `api.md` line 188 shows the generate
  response's `model` block naming `provider_name`, `provider_kind`, `is_remote` — **those are the
  names, at the top level of each `/models` entry**, because PromptCadence reads exactly
  `entry.get("is_remote")` and `entry.get("provider_name")`
  (`PromptCadence/src/promptcadence/infrastructure/loadcoach.py:949`).
* **`docs/openapi.json` will almost certainly not change.** It contains zero occurrences of
  `provider_kind`: `GET /models` returns an untyped `dict[str, object]`, so the entry's fields are
  not in the schema at all. Regenerate the snapshot and confirm; if it is unchanged, the row's
  "OpenAPI snapshot" item is a **no-op, recorded as such** — do **not** add response models to make
  the field appear (§12).
* **PromptCadence vendors two LoadCoach files as hash-pinned snapshots:**
  `tests/contract/loadcoach_openapi.json` and `tests/contract/loadcoach_task_profiles.toml`, each
  asserted by digest (`test_loadcoach_contract.py:56`, `test_loadcoach_task_profiles.py:65`).
  Half (b) edits the shipped `task_profiles.toml`, so **PromptCadence's contract suite goes red the
  day it refreshes the copy** — that refresh is a PromptCadence change (1.0.1 or a J row), never
  this row's. Name it in the handoff under *what J1 inherits*; do not touch PromptCadence.
* **The thinking thread, end to end, as it stands.** `sampling_for` (`services/execution.py:754`)
  builds `SamplingParameters` from `request.sampling` overrides over the profile's `execution`
  block, and hands it straight to `GenerationRequest` at `:849`. The profile's block is
  `TaskProfileExecution` (`domain/task_profile.py:55`–`:73`, pydantic) stored as JSON in
  `task_profiles.execution_json` (`PortableJSON`) — **a new field needs no migration.**
  `GenerateRequest.sampling` is `dict[str, Any]` (`web/routes/generate.py:134`); an unknown key is
  silently ignored today.
* **ModelRack 0.7.x carries the lever** (H1 gate F): `SamplingParameters.think: bool | None = None`
  (`types.py:381`) — `None` is byte-identical to a request built before the field existed, `True`
  asks for reasoning, `False` asks for it suppressed. The Ollama adapter sends Ollama's
  **top-level** `think`; **llama.cpp and OpenAI-compatible raise `CapabilityUnsupported` naming
  `thinking_control`** before a byte is sent; the fake honours it where declared. So a profile that
  asks for `think = false` and routes to a `llamacpp` registration fails **at generate time, not at
  routing** — that is the trap §0.2 decision 3 exists for.
* **The five harness profiles** are `tools.agent.local_fast`, `tools.agent.local_large`,
  `tools.agent.remote_cheap`, `tools.agent.remote_frontier` and `tools.plan`
  (`config/task_profiles.toml:395`–`:577`), every one at `version = "1.0.0"`. `tools.plan`'s
  execution block carries the G2 comment ending *"Until it does, the corrective retry is what
  absorbs an empty draft"* — this row is "until it does"; rewrite that comment with the numbers
  you measure. `import_task_profiles` upserts on `(profile_id, version)`; `routing_decisions` and
  `jobs` record `task_profile_version`; reliability pairs key on `task_profile_id`.
* **The reference model is present.** Ollama `0.32.13`; `ollama list` shows
  `gpt-oss:20b` (`17052f91a42e`), the model G2 and I2 measured. Live tests take
  `LCTEST_OLLAMA_URL` / `LCTEST_OLLAMA_MODEL` (`tests/live/test_ollama_generation.py:25`); the
  `LCTEST_` prefix survives `conftest.py`'s `LOADCOACH_*` strip.
* **The highest ADR in `docs/adr/` is `0098`.** Check the directory rather than trusting this line.
* **The seven LoadCoach mirrors are `cmp`-identical today** (`docs/apps/loadcoach/*.md` ↔
  `LoadCoach/docs/apps/loadcoach/*.md`). Keep them so.
* **LoadCoach `main` was red on PostgreSQL from LA2 until H4** (`docs/history/H4_HANDOFF.md`). This
  row adds no migration; if one appears anyway, run the gate with `WEIGHTSDB_REQUIRE_POSTGRES=1`
  before committing it.
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to
  the operator.

## 0.1 What the two findings actually are

**(a) The render** — I2 §5 and ADR-0098's correction. ADR-0098 rule 1 reads the remote-provider fact
from `/models`; LoadCoach 1.1.0 records both columns (migration `0008`) and renders them only on the
generate response's `model` block. On a real 1.1.0 the fact reads `False`, a remote registration is
invisible before its first turn, and every remote tier stays `loadcoach_has_no_remote_provider` —
honest, and wrong by omission. PromptCadence reads the field *when present*, so the render arrives
with no consumer change.

**(b) The reasoning budget** — G2 §5's finding, again, on a different profile. I2 §10 run 1:
`tools.agent.local_fast` on gpt-oss:20b returned `finish_reason=length` with **4 096 output tokens,
all reasoning, and no text**; PromptCadence halted per contract 6. G2 measured the same shape on
`tools.plan` (1/6 empty at 4 096, **3/6 at 8 192**, median 58 s → 171 s) and concluded the output
budget is not the lever and thinking control is. H1 built the lever in ModelRack. G2 §5 refused to
add a profile field for a control that could not be sent — *"configuration that lies"*. It can be
sent now; this row adds the field.

## 0.2 The decisions this row must take, and record

New ADRs start after the highest number present when you look (§0). One ADR covers all three
decisions below; number it, add it to `docs/adr/README.md`'s index, and cite it from the field's
docstring.

1. **The field's name and type.** Recommended: `TaskProfileExecution.think: bool | None = None`,
   mirroring ModelRack name-for-name and state-for-state — an absent or `null` field produces a
   request byte-identical to 1.1.0's, `false` asks for reasoning suppressed, `true` asks for it.
   The losing option — a string enum (`reasoning = "off" | "on" | "default"`) — would be a second
   vocabulary for a three-state fact ModelRack already names, and LoadCoach's rule is *same
   concept, same name across the suite*. Say why in the ADR either way.
2. **Whether the request may override it.** `sampling_for` already lets `request.sampling`
   override `temperature` and `max_output_tokens`. Recommended: `sampling.think` overrides the
   profile the same way, documented in api.md §4 beside the other two — one line, and it is how a
   caller like PromptCadence experiments without a profile edit. Decide, and if no, say why a
   caller may override the budget but not the control.
3. **What happens when the selected provider cannot carry it.** ModelRack refuses with
   `CapabilityUnsupported` at generate time. Three shapes, choose one and record the other two:
   * **Filter at routing** — a profile (or request) that sets `think` requires `thinking_control`
     of every candidate, rejected with a named reason and `required_by` (`"profile"` or
     `"request"`). This is exactly [ADR-0075](docs/adr/0075-a-request-carrying-tools-requires-tool-use-of-every-candidate.md)'s
     mechanism for `tools`, already built in `domain/routing/constraints.py:375`, `:572`. Note the
     vocabulary gap before choosing it: LoadCoach's constraint vocabulary is BaseAiCore capability
     IDs, and `thinking_control` is a **provider** flag (`ProviderCapabilities`), while discovery's
     `declared_capabilities` carries the **model** flag `thinking` (`_ollama_wire.py:76`,
     `baseaicore.descriptor.ModelCapabilityFlag.THINKING`). Filtering needs the provider flag —
     find where routing already reads a provider capability (ADR-0075's `tool_calling` check) and
     use the same path. **Recommended.**
   * **Send and map the refusal** — `CapabilityUnsupported` becomes a permanent attempt failure
     with a named error code; a profile with `think = false` on a llama.cpp-only deployment then
     fails every job. Honest, and useless.
   * **Drop silently when unsupported** — the request goes out without the key. Rejected by G2 §5's
     own argument: a profile that says `think = false` and a wire that does not is configuration
     that lies.
   Whatever you choose, the explanation must say what happened: a rejection reason, an error code,
   or nothing — never a request that quietly differs from its profile.
4. **The profile version bump.** `TaskProfile.version` is *"the semantic version of this profile's
   definition"*, and the five definitions change. Recommended: `1.1.0` on each of the five, so a
   `routing_decisions` row from before this release still names the definition it ran under.
   Precedent to check: `5af6b12` changed `tools.plan`'s **comment** only and kept `1.0.0`; nothing
   has yet changed a shipped profile's *values*. Decide and say so in the ADR's consequences.

## 0.3 What the measurement is, and is not

The row asks for *"the empty-answer rate before and after on the reference machine"*. It is a
measurement, not a test: a model is never a test oracle, and nothing in CI depends on the number.
The shape is G2's, which produced the numbers everybody has been quoting since:

* **Two profiles**, `tools.plan` (G2's) and `tools.agent.local_fast` (I2 run 1's), each at its
  shipped `max_output_tokens`.
* **Two settings** each: `think` unset (1.1.0's wire, the *before*) and `think = false` (the
  *after*). **Six runs** per cell, as G2 did — 24 generations in all; on this machine `tools.plan`
  ran ~58 s median at 4 096, so budget an hour and run it once, whole.
* **The prompt**: for `tools.plan`, PromptCadence's `planner.draft` `1.1.0` prompt as G2 used it
  (`docs/history/G2_HANDOFF.md` §4: 287-character system, 1 826-character user; the record is
  under `PromptCadence/`'s prompt records — read it, do not import PromptCadence). For `tools.agent.local_fast`, an agent turn
  with `tools` on the request and one tool result in `messages`, the api.md §4 shape.
* **Record per run**: `finish_reason`, `output_tokens`, `thinking_tokens`, text length, wall
  seconds; per cell: empty-answer count out of six and median wall. **Empty** means `text == ""`,
  whatever the finish reason.
* **Report** the four cells as a table in the handoff and in the `tools.plan` comment. A cell
  that gets *worse* under `think = false` is a finding, not a reason to change the default; the
  number decides what the five profiles ship with (§0.4).

G2 went straight through Ollama because its lever was a sampling value and routing could not hold
the model constant. This row's lever is the **profile-to-wire thread**, so run it through LoadCoach
— a real `loadcoach serve` on a scratch `LOADCOACH_DATA_DIR` against the local Ollama with
`gpt-oss:20b` the only eligible model (or `overrides.model` pinning it), `POST /generate` per run —
so the number measures the wire this row changes. Confirm from the attempt record that every run
hit the same model. A scratchpad script is fine; commit nothing from it except the table.

## 0.4 What the five profiles ship with

The row says *"set it on the five harness profiles"*. Set **what** is the measurement's call:

* If `think = false` cuts the empty-answer rate on both profiles without gutting the answers
  (a plan that is still a valid plan; an agent turn that still calls the tool), the five ship with
  `think = false` and the comment says what it bought.
* If it helps one profile and not the other, ship it where it helps and say why.
* If it helps neither, the five ship with the field **unset**, the field still exists (an operator
  can set it), and the comment records the measured non-result. That outcome is a legitimate
  close of the row — the lever is reachable from configuration, which is what was missing.

Do not set it on any profile outside the five. `tools.agent` (the parent) and the rest are not
this row's; an operator's own file can.

---

## 1. Setup

```bash
cd /home/jpk/ai/suite/LoadCoach
source .venv/bin/activate          # Python 3.14.4 — say so in the report
python --version
pip install -e ".[dev]"            # only if the venv is stale
git status -sb                     # clean, main...origin/main
cd /home/jpk/ai/suite/docs && git status -sb
```

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work in the component directory, never the workspace root.
* Finish line, in LoadCoach: `ruff format --check . && ruff check . && mypy src tests &&
  lint-imports && pytest -m "not live and not performance"` green; coverage floor 85 %;
  `CHANGELOG.md` updated; one Conventional Commit per gate. Name the interpreter (M5C-13).
* House method: docstring-first (what the function *refuses*, too), `from __future__ import
  annotations`, units in names, keyword-only optionals, injected clocks/providers/roots.
* Read `architecture/master-architecture.md` §§1–3 and Gold Standards §2 (LoadCoach,
  `standards/gold-standards.md:131`) before the row's list.
* `pytest-randomly` is on; a seed-only failure is a real bug.

## 3. Reading list, in this order

1. `docs/history/I2_HANDOFF.md` **§5** (the correction), **§10** (run 1 — the shape you are
   measuring), §13 item 3, §14 item 4.
2. `docs/adr/0098-…refusing-honestly.md` — rule 1 and the **Correction** section.
3. `docs/history/G2_HANDOFF.md` **§4** (the measurement — six samples per setting, `format=json`,
   `temperature=0.1`, the `planner.draft` 1.1.0 prompt, taken **straight through Ollama** so that
   nothing but the budget varied) and **§5** (the thinking-control finding, and why no field was
   added then).
4. `docs/history/H1_HANDOFF.md` **gate F** (what ModelRack built, and the byte-identical golden) and
   §8's first bullet (the number this row was told to take).
5. `docs/apps/loadcoach/api.md` **§2** (the `/models` table — one line per endpoint, no field
   list yet) and **§4** (`sampling`, and the response's `model` block at line 188).
6. `docs/apps/loadcoach/routing.md` **§2** — the `code.review` example is where the execution
   block's fields are shown; the new field goes there.
7. `docs/adr/0055-…by-name-and-kind.md` rule 4 (`remote` is declared, never inferred) and
   `docs/adr/0075-…requires-tool-use-of-every-candidate.md` (the routing-constraint precedent).
8. LoadCoach `web/routes/models.py`, `services/models.py:330`–`:427`, `services/execution.py:754`
   and `:849`, `domain/task_profile.py`, `domain/routing/constraints.py`, `config/task_profiles.toml`.

## 4. The shape of the work — five gates

Each gate ends green and committed. A and B are the render; C and D are the field; E is the release.

## 5. Gate A — the documents

In `docs/` first, then mirror. **ADR** (§0.2, one record, three decisions). **api.md §2**: the
`GET /models` row gains the sentence that every entry carries `provider_name` and `is_remote`, named
as on the generate response's `model` block, with `""` and `false` as "not recorded" for a row
discovered before registrations had names (migration `0008`'s honest defaults). **api.md §4**:
`sampling.think` beside `temperature` and `max_output_tokens`, if decision 2 says yes. **routing.md
§2**: `think` in the execution block example with its three states and the routing consequence of
decision 3. Mirror the edited files to `LoadCoach/docs/apps/loadcoach/` byte-identically; `cmp`
each. Commit docs; commit the mirror in LoadCoach with gate B.

## 6. Gate B — the render

Two lines in `_model_to_json`. One test that a registered-remote model lists `is_remote: true` and
its `provider_name`, and a pre-registration row lists `""`/`false` — `tests/e2e/test_models_and_task_profiles.py:35`
already fetches `/api/v1/models`; extend it or add beside it. Regenerate `docs/openapi.json`
(`python -c 'from tests.contract.test_openapi_snapshot import write; write()'`) and report whether
it changed (§0 says it will not). Check `loadcoach models list --json`
(`cli/commands/models.py:65`) — it renders a hand-picked subset; add the two keys there too, so
the CLI and the API say the same thing about a model. Changelog under `[Unreleased]`, *Fixed*.

## 7. Gate C — the field, threaded to the wire

`TaskProfileExecution.think` (§0.2 decision 1), validated like its siblings; `sampling_for` reads
it under the request override (decision 2); the routing consequence (decision 3) with its rejection
reason in the explanation and a unit test on `constraints.py` that a `think`-setting profile
rejects a candidate whose provider lacks `thinking_control`, naming `required_by`. A golden that a
profile with the field **unset** produces a `SamplingParameters` equal to 1.1.0's — that is the
byte-identical promise, asserted at LoadCoach's layer as H1 asserted it at ModelRack's. The fake
provider path: LoadCoach builds `FakeProvider(FakeScript(models=…))` at
`infrastructure/providers/factory.py:270` — check what that `FakeScript` declares; ModelRack's
`FULL_CAPABILITIES` has declared `thinking_control = True` since its Phase 2, so if LoadCoach's
script does not, declaring it is one argument, and the positive path gets a non-live test.
`GET /task-profiles` renders the field through `profile.execution` unchanged. Changelog, *Added*.

## 8. Gate D — the measurement, then the five profiles

§0.3 whole, once. Then §0.4: set the five, bump their versions (decision 4), rewrite the
`tools.plan` comment with the four cells, and re-run `tests/unit/test_task_profile_validation.py`
and the e2e profile tests. Recompile `requirements/ci.lock` to `modelrack 0.7.1` (§0) in this gate
and run the gate from the lock once (`pip install -r requirements/ci.lock` in a scratch venv, or
however `requirements/README.md` says). Changelog, *Changed*.

## 9. Gate E — the release commit

`__about__.py` → `1.1.1`; `[Unreleased]` → `[1.1.1] — <date>`, with a one-paragraph header that
says what 1.1.1 is (a render and a lever), names the measured numbers in one sentence, and names
`modelrack 0.7.1` as the pinned floor if you moved `pyproject.toml`'s pin (you need not — the lock
is enough; say which). Wheel built in the scratchpad and verified in a clean venv (`import
loadcoach`, `loadcoach --version`, the e2e boot test). Commit `chore(release): loadcoach 1.1.1`.
**Not tagged, not pushed, not published.**

## 10. Exit conditions — all of these, demonstrably

1. `curl /api/v1/models` on a LoadCoach with a `remote = true` registration shows the entry with
   `is_remote: true` and its `provider_name`; on a fresh database with the shipped single
   `[provider]` block, `""` and `false`. Show both.
2. A profile with `think = false` produces a request to a live Ollama carrying top-level
   `"think": false` — show it from LoadCoach's own attempt record or ModelRack's debug log, once.
3. A profile with `think` unset produces a `SamplingParameters` equal to 1.1.0's — a golden.
4. The routing consequence of decision 3 is visible in an explanation — the rejection reason or
   the error code, by name.
5. The four-cell table from §0.3, with the six-run counts and medians, in the handoff and in
   the `tools.plan` comment.
6. The five profiles carry what §0.4 decided, with the version bump decision applied.
7. `docs/openapi.json` regenerated and its (non-)change reported; the seven mirrors
   `cmp`-identical; the ADR in the index.
8. `loadcoach 1.1.1` prepared — bumped, changelogged, release-committed, unpushed, untagged.
9. Full gate green, interpreter and exact invocations named.

## 11. Closing duties

1. Full gate; interpreter and invocations (M5C-13).
2. **`docs/history/I3_HANDOFF.md`**, house shape: gate results with invocations; each §0.2
   decision with its reason and what the losing option would have made the record claim; the
   four-cell table; **what J1 inherits** — at minimum the two hash-pinned PromptCadence snapshots
   that now differ from LoadCoach's files, and that the remote-provider fact now reads from a real
   LoadCoach; and **anything this prompt said that turned out not to be true**.
3. Update the **I3 row** in `docs/roadmap/outstanding-work.md` to Done — date, commits, what held,
   what did not — and §3's *I3 before J1* edge to satisfied.
4. Note for the operator: the push list (`docs`, `LoadCoach`), that the **tag and publish** are
   theirs, and the 1.1.0-versus-1.1.1 sequencing answer from §0.
5. Record any model deviation from the scheduled Sonnet 5 · high.

## 12. Stop rules

* **Do not add response models to `GET /models` to make the snapshot move** — that changes a
  1.0 contract's schema for a field the JSON already carries, and breaks PromptCadence's
  hash-pinned copy for nothing.
* **Do not add a profile field the wire cannot carry, or carry a field the profile did not set.**
  G2 §5's rule, both directions.
* **Do not change a profile's `max_output_tokens`** to move the number — G2 proved the budget is
  not the lever; this row measures the lever.
* **Do not treat the measurement as a test**, assert a model's answer, or add it to CI. A model is
  never a test oracle.
* **Do not touch PromptCadence, ModelRack, FreeWeight or IdeaPress.** The snapshot refresh is
  theirs.
* **Do not weaken `.importlinter`, a coverage floor or a gate** to reach green.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a gate boundary. **Never `git push`, tag or publish.**

## 13. If you finish with capacity left

Read-only, in priority order: (a) whether `loadcoach models list` (the table form, not `--json`)
should show the registration name and the egress class, and what column it costs; (b) I2 §5's
`tool.call.started` digest mismatch is PromptCadence's, but check whether LoadCoach's own
`tool_calls` events carry any digest that the same argument applies to; (c) whether
`tools.agent`'s parent profile should inherit the field at 1.2 — a note, not a change.
