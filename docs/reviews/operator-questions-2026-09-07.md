# Answers to the operator's questions — 2026-09-07

The workspace root holds a file called `questions`: thirteen questions and two statements written
over the past weeks while the arcs were being built. This document answers each of them against the
suite as it exists today — the code in the fourteen repositories, the specs, the ADRs, the roadmap
rows and the handoffs — rather than against what would be pleasant to say.

Every section quotes its question verbatim as the heading, then gives four things: **what exists
today**, with a file and line or a document section; **what is specified but not built**; **what
would be new**, and whether that belongs as an ADR, as a row in
[outstanding-work.md](../roadmap/outstanding-work.md), or outside the suite's stated boundaries;
and a one-line recommendation. Where a question rests on a false premise it says so with the
evidence. Where the question is a decision only the operator can make — multi-user, vLLM, a
unifying application — it lays out the fork in a few sentences and stops.

Three of the questions turn out to rest on premises that are no longer true, and one turns out to
be worse than stated. Those are marked in the closing table.

**Tree state.** Read on 2026-09-07 with other sessions active in the same workspace: `__about__.py`
reported `freeweight 1.1.2`, `loadcoach 1.1.5`, `ideapress 1.3.2`, `promptcadence 1.3.2`, ahead of
the numbers in the workspace `CLAUDE.md`. Nothing here was written to any component repository.

---

## "how does context get retained between multiple prompt sesions in ModelRack?"

**What exists today.** It is not retained, by contract. ModelRack is stateless and says so:
[spec §3](../packages/modelrack/spec.md) — *"No persistence, no database, no caching beyond a
documented in-memory metadata cache with an explicit TTL and a `clear()`"* — and the one cache the
package is allowed to have is metadata only, never a generation
(`py/ModelRack/src/modelrack/cache.py:1-16`: *"two identical requests to the same model are two
different runs, and a cache that returned the first result for the second would fabricate a
measurement"*). Every call carries its whole conversation in `GenerationRequest.messages`
(`py/ModelRack/src/modelrack/types.py:532-581`). The two carve-outs are process-supervision state
and `digests.json`, both of which are safe to delete (spec §3).

Retention therefore lives in the applications, where the databases are: FreeWeight stores samples
and runs, IdeaPress stores units and attempt history, and PromptCadence stores a durable transcript
— `promptcadence.domain.threads` and the `turns` table, readable at `GET
/trajectories/{id}/turns` (`PromptCadence/src/promptcadence/web/routes/trajectories.py:181`), with
`cutctx` compacting it when it outgrows the window ([CutCtx spec §1](../packages/cutctx/spec.md)).

One thing *is* retained below the application, and it is the runtime's, not ModelRack's: the
server's own prompt/KV cache. llama-server reuses a shared prefix across requests in one process —
measured at row D3, `cache_read 14 (second request, shared prefix)`
([D3_HANDOFF.md:444](../history/handoffs/D3_HANDOFF.md)) — and ModelRack reports it as `cache_read_tokens`
(ADR-0070) while deliberately refusing to pin a slot, so slot selection stays the server's
(`py/ModelRack/src/modelrack/providers/_llamacpp_wire.py:139-147`, ADR-0062 decision 4). Under
Ollama, `keep_alive` keeps the *weights* resident; the context is re-sent on every call
(`providers/ollama.py:464-492` — `load` is a preload, not a generation).

**What is specified but not built.** Nothing. Statelessness is the specification, and ADR-0007
makes ModelRack a client rather than a session manager.

**What would be new.** A conversation store. It already exists once, in PromptCadence, built
deliberately as though it were a package but not extracted:
[PromptCadence spec §10](../apps/promptcadence/spec.md) records the **ThreadRack rejection** — one
consumer, and the extraction rule needs two (ADR-0011) — and the
[risk register](../architecture/risk-register.md) lists its revisit trigger as *"a second consumer
of thread state outside PromptCadence"*. Putting one in ModelRack would hand a capability package
application responsibility, which the dependency rules forbid outright.

**Recommendation.** Nothing to build in ModelRack; if you want a conversation that survives a
session, the missing surface is one level up, in PromptCadence — see the next question.

---

## "Can I have a  local "chat" between models to pass context and relevant data?"

**What exists today.** Yes, twice, and in both cases Python sits between the models.

*IdeaPress* is a sixteen-stage pipeline with a per-stage model binding
([spec §12](../apps/ideapress/spec.md) `[models.stages]`: `draft = "ollama/gemma4:12b"`,
`critique`/`revise` on `qwen3.5:9b-q8_0`). One stage's **validated** output is the next stage's
typed input, and [workflows §1](../apps/ideapress/workflows.md) states the two rules that make it
more than a chain of prompts: only Python decides progression, and auditors report while the writer
repairs — the stage that produced text never grades it.

*PromptCadence* runs one transcript across several models: a tier is a named execution surface,
each step resolves its tier, and LoadCoach chooses the model within it
([spec §§2, 4](../apps/promptcadence/spec.md); ADR-0047). Different steps of one trajectory
therefore run on different models over one shared, durable thread.

**What is specified but not built.** A free-form conversation in which the models decide who speaks
next is not "not built" — it is refused. *A model never decides control flow* is a suite invariant
(workspace `CLAUDE.md`; [IdeaPress spec §3](../apps/ideapress/spec.md): *"No autonomous agent loop;
no unbounded model-directed iteration"*), and PromptCadence's per-turn deviation comparison against
an `ExecutionIntent` (ADR-0056) exists to catch a model that wanders.

**What would be new.** One genuinely absent surface: a **human** follow-up turn into an existing
conversation. `POST /trajectories` starts a new trajectory and nothing appends a turn to a running
or finished one (`PromptCadence/src/promptcadence/web/routes/trajectories.py:133-259`);
`trajectory.resumed` is crash recovery, not continuation
([spec §17](../apps/promptcadence/spec.md)). That is a row, and a substantial one — it touches
intents, budget windows and compaction — not an ADR-first question.

**Recommendation.** It exists: IdeaPress for a fixed pipeline, PromptCadence for a planned one. The
only thing worth adding is the human follow-up turn.

---

## "I would like to be able to recommend context sizes based on resource availability. Report when resources requested are unavailable/dangerous (OOM and other issues). That seels like it should be requested from loadcoach and returned to the calling application."

**What exists today.** The premise is right and most of it is built. The arithmetic is
`LoadCoach/src/loadcoach/domain/routing/constraints.py:190` —
`estimate_vram = size_bytes × loading_overhead_factor + kv_bytes_per_token × served_context +
activation_overhead` — with `free_vram_by_gpu` at `:263` and `device_fits` at `:286` comparing it
against live telemetry per device with a `vram_headroom_bytes` reserve (default 512 MiB,
`config.py:791`). ADR-0023 §4 makes the multiplier the **served** context, not the advertised
maximum, with its source recorded as `configured`/`reported`/`assumed`, and adds the rejection
reason `context_not_configurable`.

The caller-facing half is `domain/routing/context_budget.py`: `required = estimated_input +
max_output + 256`, `usable = served_context`, output reduced to the profile's floor where permitted
and otherwise **rejected with the numbers** — the caller's input is never silently truncated
(routing §9).

A resource-shaped rejection is a wait, not a failure: `insufficient_vram` and `insufficient_ram`
are the two reasons a resource change can fix (`domain/admission.py:47`), and the narrative renders
*"its estimated footprint does not fit in the free VRAM of any device"*
(`domain/routing/narrative.py:51`). An unknown estimate never fits unless the model is already
resident (ADR-0016 applied to admission).

And the request/response shape the question asks for already exists: `POST /route`
(`web/routes/routing.py:122`) takes `estimated_input_tokens` and `max_output_tokens` and returns
the full routing explanation — every candidate, its `estimated_vram_bytes`, and its rejection
reason — **without spending a GPU second**.

**What is specified but not built.** Nothing is specified that is missing. What is absent is the
*inverse*: no surface answers "what is the largest context this model can safely serve right now",
and nothing warns a caller who has already configured a profile that will not fit until a job is
routed.

**What would be new.** A solver — the largest `served_context` for which
`estimate + headroom ≤ free` — plus a way to ask for it (a `GET /models/{ref}/context-advice`, or
an advisory block on `POST /route`). This is a **row**, not an ADR: every policy it needs is
already decided (ADR-0023 served context, ADR-0038 fit-or-wait, ADR-0016 unknown is not zero), and
the work is inverting arithmetic that exists and reporting `unknown_reason` honestly when the
provider reported no geometry.

**Recommendation.** One row: *LoadCoach recommends a context size and refuses a dangerous one* —
the solver, the endpoint, and the honest "cannot say" path.

---

## "Can loadcoach provide data to be displayed in calling app?"

**What exists today.** Yes; LoadCoach's read surface was designed for it. `GET /system/status`
returns the queue report plus the live telemetry snapshot
(`LoadCoach/src/loadcoach/web/routes/queue.py:55`); `/system/telemetry/stream`
(`routes/system.py:62`) and `/queue/stream` are SSE; `/models`, `/task-profiles`, `/reliability`,
`/evidence`, `/routing-decisions/{id}` and `/jobs/{id}/explanation` cover the rest. Every body is a
SetSpec-shaped envelope produced by MirrorWall's `json_response` / `error_response` /
`paginated_response` ([MirrorWall spec §2](../packages/mirrorwall/spec.md)), and MirrorWall also
ships the tokens, components and telemetry bar all four UIs use — so a LoadCoach payload rendered
inside another application looks native rather than pasted.

IdeaPress already does this: its LoadCoach backend keeps the job id and the model that actually ran
as attempt provenance (`IdeaPress/src/ideapress/infrastructure/backends/loadcoach.py:1032`), and
`web/templates/units/detail.html` renders it.

**What is specified but not built.** Nothing pending. Two boundaries bound the answer: MirrorWall
explicitly ships **no application pages** and no routing vocabulary (spec §3), and ADR-0041 warns
that a caller's own schema does not travel through a router — what comes back is LoadCoach's
vocabulary. Cross-application traffic is HTTP with versioned SetSpec payloads only; no application
reads another's database (`CLAUDE.md`, ADR-0001).

**What would be new.** Only a specific missing figure would be new, and that is a small row against
one payload. An embeddable cross-application widget would be new *and* would breach MirrorWall's
non-goals; the sanctioned way to render another application's data is to fetch its payload and
render it with the shared components, which is what IdeaPress does.

**Recommendation.** Already supported — name the figure you want displayed and it becomes a
one-payload row.

---

## "Should there be a unifying suite app for loadcoach and freeweights?"

**What exists today.** No portal and no cross-application navigation: each application binds its own
port, owns its own database and renders its own UI. The composition that exists is data, not
chrome — FreeWeight exports evidence, LoadCoach imports it (`loadcoach evidence import`), and
routing changes as a result.

**What is specified but not built.** ADR-0001 considered and rejected the merged shape: *"Single
application with pluggable modes … Rejected: a user who wants only a content tool would install a
benchmark engine and a router; the 'works standalone' requirement becomes vacuous."* Its revisit
trigger is coordination cost — more than half of all changes needing coordinated releases across
three or more repositories for three consecutive months — not user convenience.

**This one is yours to decide.** Three shapes, in increasing cost: (a) leave four applications and
add cross-links plus a static landing page — no ADR needed, because links are not a boundary; (b) a
fifth *console* application that reads the others' HTTP APIs and renders one dashboard — allowed by
the boundary rules exactly as written, but it is a fifth thing to version, release, secure and
document, and it becomes ADR-0001's rejected monolith the moment it grows features of its own;
(c) an actual merge, which contradicts ADR-0001 and needs an ADR superseding it.

**Recommendation.** Your call; (a) costs an afternoon and buys most of the benefit, and (b) should
wait until M9 is closed. Either (b) or (c) needs an ADR against ADR-0001.

---

## "Should lamma.cpp be added as a model running option?"

**False premise: it was added, and it is shipped.** `LlamaCppProvider` is in
`modelrack 0.7.1` (rows D3, F3, H1; ADR-0062), supervising its own `llama-server` process, with the
launch flags derived from the runtime profile — `--ctx-size`, `--n-gpu-layers`, `--cache-type-k/v`,
`--flash-attn`, `--threads`, `--batch-size`
(`py/ModelRack/src/modelrack/providers/_llamacpp_wire.py:465-476`) — and adapters registered at
launch with `--lora` (`:522`). LoadCoach constructs it from `kind = "llamacpp"`
(`LoadCoach/src/loadcoach/infrastructure/providers/factory.py:40, 278`) and FreeWeight likewise
(`FreeWeight/src/freeweight/infrastructure/providers/factory.py:29`); the earlier note that the
kind was never wired into LoadCoach's factory is stale. IdeaPress and PromptCadence reach it
through LoadCoach.

It is not an alternative to Ollama but the **only** adapter-serving provider: `adapter_hot_swap` is
declared by it alone, one adapter at a time at scale 1.0 (ADR-0062, ADR-0063), which is the whole
adapter arc.

**What is specified but not built.** `openai_compatible` exists in ModelRack but is deliberately
*not* in LoadCoach's supported kinds — naming it is a configuration error, never a silent fallback
to Ollama (`factory.py:40-52`).

**What would be new.** Nothing.

**Recommendation.** Done; the live journey passed on a real `llama-server` at row D3.

---

## "Should vLLM be added?"

**What exists today.** `vllm` is a legal `ProviderKind` (ADR-0008) with no adapter anywhere. Its
rejection is recorded in full and is not a straw man: ADR-0062 grants that vLLM has first-class
multi-LoRA serving, mature per-request adapter selection and far better throughput under concurrent
load, then rejects it because *"every one of those advantages is a concurrency advantage, and this
deployment is one user on one GPU — there is no payoff to collect"*, against the cost of a
heavyweight CUDA-coupled runtime inside a package that must install cleanly on machines with no GPU.
The [risk register](../architecture/risk-register.md) records the revisit trigger as *"a concurrency
profile that would actually collect vLLM's advantages"*, and
[master-architecture](../architecture/master-architecture.md) already names vLLM as the future
adapter-serving provider in its extension-point table.

**This one is yours to decide,** and the fork is narrow. If the workload becomes genuinely
concurrent — several users, a served endpoint, batch work — the payoff appears and the cost is one
`Provider` implementation plus a conformance pass, because the seam was left for it. If it stays
one operator at one keyboard, vLLM buys nothing and costs the install story on GPU-less machines.
Note that this trigger is the same one the multi-user question below waits on: they are one
decision, not two.

**Recommendation.** No, until a concurrency profile exists; then it is a row, not a new ADR — the
decision record already names the trigger.

---

## "how do i test the in progress versions?"

**What exists today.** Editable installs, and they are the *only* sanctioned way to consume
unreleased package code
([packaging standards §4](../standards/packaging-and-release-standards.md), which gives the exact
command):

```bash
python -m pip install -e ./py/BaseAiCore -e ./py/SetSpec -e ./py/ModelRack \
                      -e ./py/SweatMeter -e ./FreeWeight[dev]
```

Per repository the gate is the same five commands (`ruff format --check .`, `ruff check .`,
`mypy src tests`, `lint-imports`, `pytest -m "not live and not performance"`). Every application
can be run end to end with no GPU, model or network through its fake provider — LoadCoach's
`kind = "fake"` builds `FakeProvider` in the running application, not just in tests
(`infrastructure/providers/factory.py`) — and the four `demo_*.py` scripts at the workspace root do
the same for the oldest packages.

**What is specified but not built.** The constraint that actually bites is deliberate: **CI never
uses editable installs**, and `requirements/ci.lock` is hash-pinned from PyPI
(`<repo>/requirements/README.md`), so a repository that depends on an unpublished sibling is red in
CI until that sibling publishes. That is what held row H1 (ModelRack behind `baseaicore 0.4.2`) and
row I4 (PromptCadence behind `toolyard 0.1.1`). The nightly compatibility matrix is the same by
design: it pins from each application's *published sdist* on PyPI, never from a checkout
(`scripts/compatibility_matrix.py:1-24`), because its whole purpose is to test what `pip install`
hands a consumer.

**What would be new.** A workspace-mode integration check — the four applications composed from the
working tree, run against fakes, in one command — has never existed and would be a **row**. It is
optional: the same coverage exists today as a manual editable install plus each repository's own
e2e suite.

**Recommendation.** Use the §4 editable install; expect CI red until a dependency publishes, which
is the system working as designed. Add the workspace check only if pre-publish breakage keeps
costing sessions.

---

## "What files can safely be deleted?"

**What exists today.** Inside the repositories: nothing. Everything under a component's `src/`,
`tests/` and mirrored `docs/` is either gated by CI or kept byte-identical to the workspace `docs/`.

The clutter is at the workspace root, which is **not versioned** — nothing there is in git, so a
deletion is unrecoverable (`CLAUDE.md`, *Working-tree integrity*; the `harness.md` loss on
2026-09-02 is the precedent). As of today:

| File | Referenced by | Verdict |
|---|---|---|
| `changes` | nothing (0 bytes, 2026-08-24) | delete |
| `TAG_COMMANDS.sh`, `H3_TAG_COMMANDS.sh`, `I3_TAG_COMMANDS.sh` | one-shot helpers for released rows | delete once the tags exist |
| `SUITE_REVIEW.md` | nothing in `docs/` | archive or delete |
| `A1_REPORT.md`, `A1_REVIEW.md` | `history/prompts/a1-review.prompt.md`, `history/handoffs/B3_HANDOFF.md` | **move** into `docs/history/` |
| `E1_E2_RELEASE_RUNBOOK.md` | `history/handoffs/E3_HANDOFF.md`, `history/handoffs/H1_HANDOFF.md` | **move** into `docs/history/` |
| `M9_AUDIT.md`, `ADR_GAP_REVIEW.md` | `roadmap/master-roadmap.md`, `roadmap/outstanding-work.md`, ADR-0113, ADR-0114 | **move**; do not delete while rows cite them |
| `harness.md` | `roadmap/*`, `apps/promptcadence/spec.md` | keep — it is a signpost, and it is the file that was lost once |
| `.mypy_cache/`, `.ruff_cache/`, root `.venv/` | — | regenerable |

Moving rather than deleting is the established precedent: commit `c987091`,
*"docs(history): the G3 and H2 handoffs, which lived only at the workspace root"*.

**What is specified but not built.** Two documents still describe a directory that is already gone:
`.old_projects/` no longer exists in the workspace, yet `CLAUDE.md:28` lists it in the tree and
[CODE_REVIEW_PLAN.md §0](../CODE_REVIEW_PLAN.md) still instructs *"Do not read `.old_projects/`"*.
The inventory (legacy-material-inventory.md) is the
surviving record and should stay.

**What would be new.** Nothing architectural. This is a housekeeping row at most, and more likely
ten minutes of `mv` plus two documentation edits.

**Recommendation.** Delete the four one-shot artefacts, move the six reports into
`docs/history/`, and correct the two stale `.old_projects` references.

---

## "What order should I go through the files manually to understand the whole system."

**What exists today.** Both orders are already written, and they answer different questions.

[CODE_REVIEW_PLAN.md](../CODE_REVIEW_PLAN.md) is the code order: bottom-up along the dependency
direction so nothing is read before what it imports — BaseAiCore → SetSpec → ModelRack → SweatMeter
→ WeightsDB/MirrorWall → LoadLedger → CutCtx → ToolYard → Commissioner, then FreeWeight, LoadCoach,
IdeaPress, PromptCadence. 188,000 source lines, sixty-six sessions honestly counted, with a
forty-session fast track that skims fakes, wire codecs, migrations and CLI bodies. It also fixes
the per-component order (§0: master architecture once, then dependency-and-boundary-rules once,
then that component's `spec.md`), names the ADRs to read before the code they shaped (§5), and
suggests a calendar (§6).

[LEARNING_PLAN.md](../LEARNING_PLAN.md) is the user order: the same four applications from the
outside in, five half-days, each module ending in something you can show.

**What is specified but not built.** Nothing.

**What would be new.** Two small staleness fixes: CODE_REVIEW_PLAN's line counts are pinned at
2026-09-06, and LEARNING_PLAN's index caveat still says the FreeWeight and LoadCoach `1.1` releases
are unpublished — `__about__.py` now reads `1.1.2` and `1.1.5`, so that paragraph needs a look.

**Recommendation.** Read CODE_REVIEW_PLAN for the code and LEARNING_PLAN for the product; refresh
the two dated paragraphs when you start.

---

## "How can I have freeweights have 1 set of results across multiple projects?"

**What exists today.** That is exactly what the evidence bundle is for. FreeWeight publishes
`capability.evidence` and `benchmark.evidence_bundle` through `GET /api/v1/evidence/export` and
`freeweight evidence export` ([spec §7.1, §11](../apps/freeweight/spec.md)); any number of consumers
import the same artefact — `loadcoach evidence import --file <bundle>` or `--url
http://127.0.0.1:8765` (`LoadCoach/src/loadcoach/cli/commands/evidence.py:77`), or `POST
/evidence/import`. The consumer's uniqueness key already carries `source_id`, so several producers
coexist without collision (ADR-0022 §3).

What bounds reuse is not the project but the **subject**. Evidence describes
`(model identity, runtime_profile_hash, machine_fingerprint)` — plus the adapter axis since
ADR-0058 and ADR-0085 — and evidence measured under a different served context or KV precision is
not silently reused and not scored zero: it is *absent*, named `evidence_profile_mismatch` with both
hashes side by side (ADR-0023 §3). One set of results therefore covers as many projects as you like
**on the same machine under the same profile**, which is an honest limit rather than a missing
feature.

**What is specified but not built.** Federated import — evidence measured on machine A consumed on
machine B — is ADR-0022's own revisit trigger: *"A second evidence producer exists (a federated
import from another machine), which would make `source_id` semantics load-bearing in ways one
producer never exercises."*

**What would be new.** Nothing, if the projects share a machine. If they do not, the new work is
that revisit: an ADR on cross-machine evidence semantics first, then a row.

**Recommendation.** Export once, import into every consumer; align the runtime profile or expect
`evidence_profile_mismatch` to tell you why routing ignored your numbers.

---

## "!! M7_HANDOFF.md talks about Gemma4:12B returning nothing it's first prompt after a cold load. This is concerning and I think that it should be flagged in freeweight and handled perhaps in loadcoach? It should warm the model then clear the KV and get it ready for the caller?"

**The premise is correct, and the problem is broader than the handoff says.**
[M7_HANDOFF.md §M7-16](../history/handoffs/M7_HANDOFF.md) measured `gemma4:12b` consuming its entire output
budget thinking on the first generation after a cold load and returning an empty string with
`finish_reason="length"` — reproduced three times in three with explicit unloads, not observed on
`qwen3.5:9b-q8_0` — and since ADR-0038 unloads before every model switch, a cold load is guaranteed
on every alternation between IdeaPress's two default bindings.

Row G2 then measured the same failure **warm**, on a different model:
[G2_HANDOFF.md §4](../history/handoffs/G2_HANDOFF.md) records `gpt-oss:20b` returning an empty answer in
1 of 6 planning calls at the shipped 4096-token budget and 3 of 6 at 8192 — `done_reason=length`,
`eval_count` exactly the budget, up to 34,000 characters of thinking. So this is not only a
cold-load quirk: it is what a reasoning model does when its output budget runs out before its first
word, and raising the budget made it worse.

**What exists today.** One workaround, in one application, plus one narrow guard in LoadCoach.

* IdeaPress retries once when a result is both truncated and empty, attaches an
  `empty_generation_retried` degradation, does **not** consume `max_attempts_per_stage`, and if the
  retry is also empty fails with the budget number rather than letting a JSON parser emit
  "Expecting value: line 1 column 1" (`IdeaPress/src/ideapress/services/inference.py:333-391`).
* LoadCoach's **corrective** retry survives an empty answer — it refuses to replay an empty
  assistant turn and describes the emptiness inside the correction prompt instead
  (`LoadCoach/src/loadcoach/services/execution.py:955-985`, row G2 gate D). That path only runs when
  structured output failed validation; an empty *unvalidated* answer is returned to the caller as a
  successful response, and queue §7's failure table has no row for it.
* LoadCoach does **not** warm. `ResidencyService.ensure_loaded` calls `provider.load(identity,
  profile)` and nothing else (`LoadCoach/src/loadcoach/services/residency.py:187-290`), and that
  load is a preload by construction: Ollama's adapter issues `POST /api/generate` naming a model
  with no prompt *"to preload one without generating anything"*
  (`py/ModelRack/src/modelrack/providers/ollama.py:464-492`).
* FreeWeight does **not** flag it, and this is the sharp finding. `performance.cold_load` is the one
  cold test in the suite; it sends *"Reply with the single word: ok."* with a 64-token cap — the
  exact shape that produced the empty answer — and records only `load_ms` and `total_ms`
  (`FreeWeight/src/freeweight/benchmarks/performance/benchmark.py:403-436`). Nothing asserts the
  cold call produced text, and `[execution] warmup_repetitions` (`config.py:461`) throws away the
  one call that would have shown it. The defect is invisible in evidence by construction.

**What is specified but not built.** There is no KV-clear operation anywhere: the `Provider`
protocol ships `load`, `unload` and `list_resident` and nothing else, and llama.cpp clears a slot's
prompt cache itself when the adapter set changes
(`_llamacpp_wire.py:139-147`). "Warm then clear the KV" would require a new provider capability,
and it is not what fixes this — the empty answer is a budget-exhaustion behaviour, not a stale-cache
one.

**What would be new.** Two things, both rows.

1. **FreeWeight records whether the first call after a load produced text.** A new metric on
   `performance.cold_load` — an empty-first-call rate — turns a model-specific trap into a
   measurable property of a subject. If it is to reach capability evidence rather than just the
   run view it needs an ADR, because ADR-0087 admits only a signal that *scores*.
2. **LoadCoach treats an empty, budget-truncated answer as a retryable failure.** This is
   IdeaPress's fix moved to the one place all three callers route through, bounded at one attempt
   and recorded as a degradation; it reaches PromptCadence for free and lets IdeaPress's local
   workaround be superseded. It amends queue §7's failure table, so it wants a short ADR alongside
   the row.

**Recommendation.** Two rows — the FreeWeight cold-call content signal and the LoadCoach
empty-generation retry — and skip the KV clear; it addresses a mechanism that is not the cause.

---

## "Can i get a report of how many chats i could get on one loaded model given the leftover GPU space? I have concern over model switching and having to load and warm a model"

**Partly false premise: concurrently, the answer is one, by policy.** ADR-0038 is *one model at a
time per GPU*: LoadCoach's `max_concurrent_jobs` defaults to 1, IdeaPress **refuses** a
`max_concurrent_stages` above 1 at startup rather than clamping it, and FreeWeight allows exactly
one GPU-bound workload. `llama-server` is launched with no `--parallel` flag at all
(`py/ModelRack/src/modelrack/providers/_llamacpp_wire.py:640-660`), so it serves a single slot. A
report saying "you could run six chats at once" would be describing a machine you do not have.

**What exists today.** The sequential form of the question — *how much context does the leftover
VRAM buy* — is answerable from parts that already exist: `kv_bytes_per_token` and the full
`VramEstimate` breakdown (`constraints.py:190-260`), free VRAM per device from SweatMeter's
snapshot (`vram_used_bytes` / `vram_total_bytes`, `py/SweatMeter/src/sweatmeter/types.py:56-69`),
and FreeWeight's **measured** `observed_kv_bytes_per_token`, which the estimator prefers over the
theoretical figure when it exists. `GET /system/status` already returns queue, residency and
telemetry in one body, and `POST /route` returns `estimated_vram_bytes` per candidate.

On the switching cost, which is the real worry, the machinery is already there and it is measured:
routing prefers a resident model, idle residents are evicted LRU only when the device is full,
`unload_idle_seconds` governs how long a model stays, residency is two-level so an **adapter** swap
on a resident base is not an unload at all (ADR-0066; `LoadOutcome.already_resident`,
`residency.py:236-243`), and `performance.cold_load` measures what a cold load actually costs on
your hardware.

**What is specified but not built.** No surface composes those parts into the report. Nothing
inverts the estimate, and nothing states the residency picture as "this is what a switch costs you
today".

**What would be new.** The same solver as the context-size question, presented as a capacity
report: for the resident model, given free VRAM, the largest context it can serve and how many
sequential conversations of a given size that KV budget covers. One row covers both questions.

**Recommendation.** Fold into the context-advice row, and expect the honest answer: one at a time,
and here is the context it can hold.

---

## "Ideapress is a workflow with some stateful  addons like a harness"

**Accurate today, and it names a convergence that happened over the last week.** IdeaPress now
depends on `loadledger[sql]>=0.3,<0.4`, `commissioner[sql]>=0.1.1,<0.2` and `cutctx>=0.1,<0.2`
(`IdeaPress/pyproject.toml:43-55`) — three of the four packages PromptCadence was built on, adopted
at rows J1 (per-unit cost and the egress badge, ADR-0103) and J2 (compaction behind the unchanged
`assemble_context()` seam, ADR-0104). Row M1 adds ToolYard as the `research` stage's executor, which
makes it the fourth.

**What is specified but not built.** The distinction that survives the convergence is not the
package list; it is who owns control flow. IdeaPress's stage graph is fixed and Python-decided
([workflows §1](../apps/ideapress/workflows.md): *"A gate passes because a deterministic check
passed or a bounded loop exhausted, never because a model said it was finished"*), and
[spec §3](../apps/ideapress/spec.md) forbids it an autonomous agent loop and routing algorithms
outright. PromptCadence plans, has the plan approved, mints an `ExecutionIntent` per turn and
compares every turn against it (ADR-0056), with tiers, deviations and approval modes. IdeaPress has
none of those and is not meant to.

**What would be new.** Making IdeaPress's stages plannable at runtime would be asking it to become
PromptCadence, and would need ADR-0045's boundary re-opened. Nothing suggests that is wanted.

**Recommendation.** Keep the distinction — shared machinery belongs in packages, and it already
lives there.

---

## "ADR-0014 assumes a single user. What would this take to harden to multiuser set up and enterprise usage"

**What exists today.** The single-user assumption is the *deployment* assumption; the code is not
naive about it. [ADR-0014](../adr/0014-authentication-strategy.md) gives bearer tokens with
`read`/`write`/`admin` scopes enforced **in the service layer as well as at the route** — chosen
precisely so an identity layer can be added later — refuses to start on a non-loopback binding
without a token (`INSECURE_BINDING`, exit 3), requires `allow_lan_exposure` for `0.0.0.0`, stores
only a SHA-256 of a 256-bit token, compares with `hmac.compare_digest`, and rate-limits failed
attempts. Loopback with no token configured yields
`Principal(name="loopback", scope="admin", source="loopback")`
(`LoadCoach/src/loadcoach/web/auth.py:124`).

**What is specified but not built.** Identity, not authentication, is what is missing, and ADR-0014
says so in its consequences: *"No user identity — audit logs attribute actions to a token name, not
a person."* Concretely, `Principal` is `(name, scope, source)`, it reaches `authorize()` and is
**never persisted** — no table in any of the four applications carries an owner, an actor or a
tenant. Budgets scope by an opaque `run_id` and free-form tags
(`py/LoadLedger/src/loadledger/types.py:54, 249`), not by user. Approvals are a *mode*, not an
assignment; the risk register's revisit trigger for approval routing to people is *"multi-operator
workflows needing assignment, delegation or escalation"* (ADR-0049).

ADR-0014 already names the migration path: *"keep bearer tokens as the machine credential, add an
identity layer (OIDC) for humans, and map both onto the existing scope checks."*

**This one is yours to decide.** The honest sizing splits in two. (a) **A small team behind a proxy
that already authenticates** is mostly documentation plus the `X-Forwarded-For` trust ADR-0014
already permits as explicit configuration — a day, and no new decision record. (b) **Genuine
multi-user with per-user attribution and isolation** is a program: an identity ADR superseding
ADR-0014; an actor column on every write path and every event, and a tenant column plus a scoping
rule on every query, in four independently released schemas; per-user budgets (nearly free —
`run_id` is opaque and tags exist); per-user quotas on a single GPU, which collides head-on with
ADR-0038, since "one model at a time" is not a multi-user serving answer; and therefore the same
concurrency profile that would finally justify vLLM.

**Recommendation.** (a) is already sanctioned and cheap; (b) is one decision with the vLLM question,
not two — write the identity ADR only once you know which of the two you are buying.

---

## A closing note on the file's last line

`questions` ends with *"docs to update — executive summary"*.
[executive-summary.md](../architecture/executive-summary.md) currently says *"All fourteen
components are built and tagged"* and defers per-component versions to master-roadmap §9. That is
still true in shape, but it predates the M9 work, the J/K/L rows and the patch releases of the past
two days, and it does not mention the harness or adapter arcs by name. It is worth one pass in the
same session that closes M9.

---

## Summary

| Question | Recommendation | Proposed row / ADR |
|---|---|---|
| Context between sessions in ModelRack | Nothing in ModelRack — it is stateless by contract; retention lives in the applications | — |
| A local chat between models | Exists twice (IdeaPress stages, PromptCadence tiers); only the human follow-up turn is missing | Row: *PromptCadence accepts a follow-up turn into an existing trajectory* |
| Recommend context sizes / report danger | Build the inverse of `estimate_vram` and expose it | Row: *LoadCoach recommends a context size and refuses a dangerous one* |
| LoadCoach data displayed in a calling app | Already supported over HTTP + SetSpec + MirrorWall; name the missing figure | — (one-payload row if a figure is missing) |
| A unifying suite app | Operator's decision; cross-links first, a console app only after M9 | ADR superseding ADR-0001, only for shapes (b)/(c) |
| Add llama.cpp | **False premise** — shipped in `modelrack 0.7.1`, wired in LoadCoach and FreeWeight | — |
| Add vLLM | No, until a concurrency profile exists; the trigger is already recorded | — (row when triggered) |
| Testing in-progress versions | Editable installs per packaging §4; CI is red until a dependency publishes, by design | Optional row: *a workspace integration check against the working tree* |
| What files can be deleted | Delete four one-shot artefacts, move six reports into `docs/history/`, fix two stale `.old_projects` references | Housekeeping, no row needed |
| What order to read | `CODE_REVIEW_PLAN.md` for code, `LEARNING_PLAN.md` for product; refresh two dated paragraphs | — |
| One FreeWeight result set across projects | Export once, import everywhere; the limit is the subject, not the project | ADR + row only if projects span machines (ADR-0022 revisit) |
| Gemma cold-start empty answer | **Premise correct and understated** — also happens warm (G2); FreeWeight cannot see it, LoadCoach does not retry it, and the KV clear is the wrong fix | Row: *FreeWeight records whether the cold call produced text* (+ ADR if it enters evidence); Row + short ADR: *LoadCoach retries an empty, budget-truncated answer once* |
| How many chats on a loaded model | **False premise** — one at a time by ADR-0038, single-slot llama-server; the useful answer is context capacity | Folded into the context-advice row |
| IdeaPress is a workflow with harness add-ons | Accurate; the distinction that matters is who owns control flow, and it should stay | — |
| ADR-0014 → multi-user | Behind an authenticating proxy: documentation. Genuine multi-user: one decision with vLLM | ADR superseding ADR-0014, when the concurrency profile is real |
