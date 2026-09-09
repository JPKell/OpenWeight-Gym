# H3 — IdeaPress 1.1: per-stage adapter pins, the caller classification half, and LA2's exit

**Row:** H3 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-05.
**Model:** **Opus 5 · high** — the operator's scheduled deviation from `Sonnet 5 · standard`,
recorded in `docs/roadmap/model-assignment.md` §2.11.
**Ships:** `ideapress 1.1.0` **prepared**; `loadcoach 1.1.0` **amended**, still unpublished.
No tag, no publish, no push.

---

## 1. The headline

**All six gates are built, green and demonstrated live.** A real IdeaPress installation ran three
model-using stages, each pinning a different LoRA adapter, over HTTP to a real `loadcoach serve`
over a real `llama-server`. One server process answered all three.

What a person can see today:

```toml
[inference]
data_classification = "confidential"   # one value for every request this installation makes

[models.stage_adapters]                # a key present is a pin in effect — no second boolean
draft  = "pirate"
revise = "terse"
```

and, after the run:

```sql
SELECT stage, adapter_name, subject_canonical_id FROM attempts;
-- draft    | pirate  | llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+pirate@sha256:35bd9f9f99bf
```

## 2. Gate results

**Interpreter: Python 3.13.15** at `/home/jpk/ai/suite/IdeaPress/.venv/bin/python`, and
**Python 3.14.4** at `/home/jpk/ai/suite/LoadCoach/.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/IdeaPress
.venv/bin/python -m ruff format --check .      # 174 files already formatted
.venv/bin/python -m ruff check .               # All checks passed!
.venv/bin/python -m mypy src tests             # no issues in 169 source files
.venv/bin/lint-imports                         # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov
                                               # 1062 passed, 5 skipped, 30 deselected
                                               # coverage 88.27 % (floor 85 %)

cd /home/jpk/ai/suite/LoadCoach
.venv/bin/python -m ruff format --check .      # 209 files already formatted
.venv/bin/python -m ruff check .               # All checks passed!
.venv/bin/python -m mypy src tests             # no issues in 189 source files
.venv/bin/lint-imports                         # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov
                                               # 991 passed, 3 skipped, 17 deselected
                                               # coverage 90.55 % (floor 85 %)
```

Run at every gate boundary, in `pytest-randomly`'s default random order — no seed-dependent
failure appeared.

### Gate F, the live evidence, verbatim

```bash
cd /home/jpk/ai/suite/IdeaPress
IDEAPRESS_LOADCOACH_BIN=/home/jpk/ai/suite/LoadCoach/.venv/bin/loadcoach \
.venv/bin/python -m pytest -m live tests/live/test_la2_three_stage_project.py -rs -s -p no:randomly
```

```
I16 (IdeaPress): pids= [[2857212], [2857212], [2857212]]
wall_ms= [1268, 167, 425]
  draft: pirate -> llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+pirate@sha256:35bd9f9f99bf
  revise: terse -> llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+terse@sha256:c582629216c5
  critique: verbose -> llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+verbose@sha256:4af980ac1fb2
  draft: A KV cache be a place where key-value pairs be stored for quick access, like a treasure chest but fo
  revise: A type of memory for storing frequently used data.
  critique: Certainly, let me walk through this carefully. A KV cache stands for Key-Value cache, which is an ef
residency: [('01M1TM0EXPGS3X0BY5V5AYQD5N', 1, '2026-09-06 05:45:41.807116', '2026-09-06 05:45:43.111365')]

join on the attempt: [('verbose', 'public', 'confidential')]

the pinned stage failed: BACKEND_UNAVAILABLE
I19: 1 recorded denials
   {"adapter": "verbose", "adapter_classification": "public", "caller_classification": "confidential",
    "effective_classification": "confidential", "problem": "an adapter is a local-only artifact
    (ADR-0065 rule 3), and this candidate would be served by a remote registration; no flag makes it
    eligible", "provider_name": "hosted", "provider_remote": true}

3 passed in 23.14s
```

**I16** is asserted from two independent witnesses, neither of them the absence of a complaint: the
operating system's process table shows **one** `llama-server` pid at every sample, and LoadCoach's
residency ledger holds **one row** — an adapter switch on a resident base writes none (ADR-0066).
The wall times corroborate rather than prove: the first request carried the load at 1268 ms and the
others took 167 ms and 425 ms, but a later stage may legitimately take longer than the one that
loaded, because an adapter switch is free and a generation's length is not.

**The three answers are the canary.** One prompt, three visibly different voices, so the adapters
demonstrably applied rather than being accepted and ignored.

**The join is proved with the caller doing the raising.** `critique`'s adapter is reviewed
**`public`** and the installation declares **`confidential`**, so the attempt's
`effective_data_classification` is `confidential` — a value neither the adapter nor the old code
could have produced. Before H3 that attempt would have recorded `public`.

**I19** is a `routing_candidates` row, not a `governance.egress_decision` (ADR-0079), and its
`caller_classification` is now IdeaPress's declared value rather than `null`. Note what the row
actually says: the refusal fires on **remoteness**, unconditionally (ADR-0065 rule 3), so the
classification arithmetic is *recorded* on it rather than *deciding* it. The join deciding an
outcome is the attempt above.

## 3. What each gate built

* **A — the documentation, before a line of source.** Phase 10 of IdeaPress's development plan in
  the house shape with demonstrable acceptance criteria; `spec.md` §10 (the new columns are
  IdeaPress's own data, and there is no adapters table), §11 (the naming note), §12 (both keys and
  every startup refusal), §13 (two new error codes) and §19 (what 1.1 adds and what it does not
  break); `workflows.md` §2, §6, §6.1, §6.2 and §8; LoadCoach's `api.md` §4 and `routing.md` §10.
  **[ADR-0083](docs/adr/0083-an-adapter-pin-is-configured-on-by-being-configured.md)**: the pin
  gets its own table and no gating boolean.
* **B — the caller half, in LoadCoach.** An optional `data_classification` on `GenerateBody` (so
  `/jobs` inherits it), validated against `baseaicore.DataClassification` and **refused** rather
  than ignored when it names no level — ignoring it is the one direction that can only *lower* the
  effective classification. It reaches `ConstraintInputs.caller_data_classification`, which nothing
  had ever set, and `join_classification` (made public from `_join_classification`) is now applied
  at `services/execution.py`'s persistence as well as in the rejection detail.
* **C — configuration.** `[models.stage_adapters]`, a sparse mapping beside `[models.stages]`, with
  four refusals by name: a gate stage, an unknown stage, an empty adapter name, and any pin at all
  outside `loadcoach` mode. `[inference] data_classification` defaults to `public`. The
  compatibility golden is the exit condition asserted rather than argued.
* **D — the passthrough.** The gateway resolves the pin beside the model binding — one place a
  stage's configuration becomes a request — and it reaches the backend as
  `StageRequest.adapter_hint`. Four roads to a bare-base answer are each closed and each tested.
* **E — provenance.** Migration `0006`, three nullable columns, written from what answered.
* **F — the demonstration and the two release commits.**

## 4. Decisions, as built

Each of §0.3's seven, and whether it survived contact with the code.

1. **Naming — as decided.** `adapter` keeps the LoRA sense in configuration and on the wire;
   `spec.md` §11 carries the note once and `workflows.md` §6.1's table heading is now "Backend".
   No port symbol was renamed.
2. **The pin gets its own key — as decided**, and it is ADR-0083. The both-set case is stated in
   the ADR, in `spec.md` §12 and in a test.
3. **A refused pin fails its stage — as decided, and hardened.** Beyond the two error codes, two
   further roads to the same bad outcome were closed: **a pinned stage does not fall back at all**
   (no other backend can serve an adapter, so a fallback is the bare base under another name), and
   **an answer whose subject is not the pinned adapter is refused rather than recorded**.
4. **A pin outside `loadcoach` mode is refused at startup — as decided.** A `Settings`-level
   validator, because the mode and the pin live in different sections.
5. **A persisted attempt names the subject by string only — as decided, with one correction.**
   §0.3(5) says to use `baseaicore.AdapterIdentity.canonical_suffix()` and
   `canonical_subject_id()`. **`canonical_subject_id` does not exist** — see §6 — and neither is
   needed: LoadCoach's response already carries `model.subject_canonical_id` and
   `model.adapter.artifact_digest`, and §0.3(5)'s own rule is that the attempt records what
   *answered*. Reconstructing the string from the pin would have recorded the request instead.
   IdeaPress grew no adapters table.
6. **One application-level classification, defaulting lowest — as decided.**
7. **The LoadCoach change folds into the unpublished `1.1.0` — as decided.** No version bump; the
   changelog entries joined the existing unreleased `1.1.0` section.

## 5. Three defects this row's plan did not predict, all silent, all found by the live journey

1. **`head_dim` is never reported, so no llama.cpp model could be VRAM-estimated.** ModelRack's
   llama.cpp descriptor carries `layers`, `kv_heads`, `attention_heads` and `embedding_dim` — but
   not `head_dim`, which the theoretical KV figure needs. An unknown estimate is a refusal rather
   than a zero (ADR-0016), so **every llama.cpp candidate was rejected `insufficient_vram`, with
   `estimated_bytes: null`, on any machine with GPU telemetry.** The only provider kind that can
   serve an adapter could serve nothing at all through a running LoadCoach. H2 never met it because
   its live test drove `execute()` in-process with no telemetry snapshot; H3's journey is the first
   thing to route llama.cpp through a served LoadCoach.
   **Fixed in LoadCoach** (`8e72a8a`) by reconstructing `head_dim` as
   `embedding_dim // attention_heads` — the definition of the field, not an approximation, and
   `None` rather than a rounded guess when the division is inexact. **This is a scope deviation and
   the operator should know it: the honest home for the field is ModelRack's descriptor**, and
   moving it there is a row of its own. The LoadCoach reconstruction is correct where it stands and
   would remain a harmless fallback afterwards.
2. **A queued job lost `overrides.adapter` and `overrides.ignore_residency`.** A leased job's
   submission is rebuilt from `jobs.request_json` and from nothing else, and neither field was
   written to it or read back. So an adapter pin submitted through `POST /jobs` — IdeaPress's
   default path for `draft`, `revise`, `repair` and `project_review` — was silently dropped between
   submission and execution and the request was answered by the **bare base**, which is precisely
   the fallback ADR-0064 rule 4 forbids, with no error anywhere. Fixed in gate B with a round-trip
   test.
3. **`loadcoach serve` leaks its supervised `llama-server` on shutdown.** Six orphans from earlier
   runs were holding 13 GB of a 16 GB card. The failure this causes is not "out of memory" but
   something worse to diagnose: the *next* candidate is refused `insufficient_vram` before its
   classification is ever considered, so a defect in shutdown reads as a defect in routing.
   **Not fixed** — it is LoadCoach's supervisor and outside §0.1a. The live test reaps them itself.

## 6. Things this prompt said that turned out not to be true

1. **`baseaicore.AdapterIdentity.canonical_subject_id()` does not exist.** `baseaicore.adapter`
   exports `AdapterIdentity`, `ModelIdentity`, `IdentityConfidence`, `normalize_digest` and
   `verify_adapter_base_compatibility`; `AdapterIdentity` has `canonical_suffix` and
   `digest_short`. Nothing needed it — see §4(5).
2. **The three repositories were level with `origin`, not 3 and 9 ahead.** The operator pushed
   between the prompt being written and the session starting. `docs` was at `85183fc` (the prompt's
   own commit), not `4574b9a`.
3. **The `loadcoach-contract` editable install was not needed, and would not have helped.** The
   mechanism is a **vendored** OpenAPI snapshot at `tests/contract/loadcoach_openapi_v1.json`, and
   `assert_snapshot_matches_distribution` compares it against `loadcoach.api_snapshot()` — which
   `loadcoach` does not expose, in 1.0.0 or 1.1.0. The snapshot was refreshed from LoadCoach's own
   regenerated `docs/openapi.json` instead, so every request body is still validated against the
   producer's real `extra="forbid"` schema, and IdeaPress's venv was left untouched (installing
   `loadcoach` would have tried to move `modelrack` past IdeaPress's `<0.6` pin).
4. **`ADAPTER_NOT_FOUND` is not what a caller sees when a pin is refused for classification.** A
   pin removes every other subject from the pool, so when the only adapter subject is rejected the
   answer is `NO_ELIGIBLE_MODEL` — which IdeaPress maps to `BACKEND_UNAVAILABLE`, with every
   candidate's rejection in the details. The two adapter codes cover the refusals LoadCoach names
   directly; the classification refusal arrives as "nothing was eligible, and here is why".
5. **`pytest`'s coverage ratchet forbids a `subprocess` call with no `cwd`** (`tests/unit/
   test_import_boundaries.py`). Not wrong in the prompt, but not mentioned, and it fails a gate
   after a live test is written rather than while it is being written.
6. **§0.5's "a real IdeaPress project through three model-using stages" is delivered as three real
   stage runs, not a brief-to-export workflow.** The journey creates a real project row and stage
   run, drives three stages through the real `InferenceGateway`, and writes real attempt rows —
   every service the pins touch, over real HTTP. It does not drive `requirements` → `outline` →
   `draft` → `commit`, because a 1.5 B base at 48 output tokens fails those stages' *validation*
   for reasons that have nothing to do with adapters, and a demonstration that fails for an
   unrelated reason proves nothing about this one.

## 7. Two limitations recorded rather than worked around

1. **I19's setting is unreachable from a stock installation.** None of the eleven task profiles
   IdeaPress's `LOADCOACH_TASK_MAP` names allows a remote registration, and the two shipped
   profiles that do (`tools.agent.remote_cheap`, `tools.agent.remote_frontier`) demand ≥128k
   context and `tool_use`, which a 1.5 B base cannot serve. There is also no configuration key for
   an alternative `task_profiles.toml`: `bootstrap.py` reads the file shipped inside the installed
   package. The journey therefore edits one stored profile's `constraints_json` in the operator's
   own database after the server has imported the shipped file. **That is a fixture, not product
   behaviour**, and it is commented as such in the test.
2. **The same weights cannot be registered twice.** A `models` row is keyed on the model's identity
   — provider kind, name and artifact digest — with no registration component, so registering one
   base under both a local and a declared-remote name produces **one** row carrying whichever
   registration discovery reached last. The journey's two halves are therefore two servers over two
   databases. Worth a decision if a deployment ever wants one endpoint reachable two ways.

## 7a. The closing interview — four decisions, all taken and all built

Taken by the operator on 2026-09-05, after the gate. Each expanded the row's scope deliberately.

1. **`head_dim` moves to ModelRack, now.** The LoadCoach reconstruction (`8e72a8a`) is **reverted**;
   `modelrack` reconstructs the field in both the llama.cpp and the Ollama descriptor, which read
   the same GGUF key names, and an inexact division stays `UNSUPPORTED` rather than becoming a
   rounded guess. Folded into the **unpublished `0.7.0`** rather than cut as `0.7.1`, on the same
   reasoning §0.3(7) applied to LoadCoach. Verified against the real file: the descriptor now
   reports `head_dim=128` for `Qwen2.5-1.5B-Instruct.Q8_0`, and the live journey passes with
   LoadCoach carrying no reconstruction of its own.
2. **The leaked `llama-server` is fixed, in this session.** The cause was not the supervisor:
   **LoadCoach never called `close()` on any provider.** The lifespan released the publisher, the
   sampler, the queue runtime and the database, and dropped every provider handle —
   `LlamaCppProvider` ends its servers in `close()` and otherwise only in a finalizer, which does
   not run when the process is signalled. `_close_providers` now runs in the lifespan's `finally`,
   closing every registration and continuing past one that raises. **Measured:** a server was
   started, a generation run, and `SIGTERM` sent — `0` `llama-server` processes remained, where
   before each run left one.
3. **`[routing] task_profiles_path` is added.** A deployment can name its own `task_profiles.toml`,
   which `serve`, `tasks`, `job`, `route` and `generate` all resolve the same way; a path that is
   not a file is refused at startup rather than falling back, because routing under profiles you
   did not write is not something you could tell from the outside. The live journey now supplies
   I19's remote-permitting profile through this key, and the SQL fixture in §7(1) is **gone**.
4. **A full workflow on a larger base — attempted, and it found something better.** See §7b.

## 7b. The full-workflow probe: a larger base is not the fix

The row's §0.5 demonstration drives three stages directly. Asked to run a *full* workflow instead —
`start_plan` (which runs `requirements` and `outline`) then `draft` — on a base large enough to pass
those stages' validation, the answer is that **no base passes, because the blocker is not the
model.**

Three bases were tried through a real `loadcoach serve`:

| Base | Outcome |
|---|---|
| `Qwen2.5-1.5B-Instruct.Q8_0` | `requirements` failed: "the answer has no `requirements` array" |
| `Qwen3.5-9B-…-HERETIC.Q4_K_M` | Every request `500`s: its chat template raises `System message must be at the beginning`, and IdeaPress always sends a system turn. Nothing to do with quality |
| `Qwen3-14B-heretic.Q4_K_M` | Same failure as the 1.5 B — and the transcript shows why |

**What the 14 B actually produced, from `jobs.response_text`:**

```json
{ "confidence": "medium",
  "data": { "requirements": [ { "text": "The article must state that inference runs entirely on
            the reader's own machine.", "blocking": true, "source_document": "brief", … } ] } }
```

That is a **correct** requirements extraction, wrapped in LoadCoach's `structured.extract`
envelope. IdeaPress looks for a top-level `requirements` array, finds `data`, and fails the stage.

**The mechanism, from `job_attempts` and `validations` on that job:**

* **Attempt 1** emitted IdeaPress's own shape — `{"requirements": [...]}` — preceded by a `<think>`
  block, so LoadCoach's `json` check failed on the prefix.
* **Attempt 2**, after LoadCoach's corrective retry, emitted the **profile's** shape, and
  `json_schema` and `required_fields` both passed.

`structured.extract`'s validation block is `require_schema=True, required_fields=('data',)`. So
even though IdeaPress deliberately asks for `response_format: "json"` rather than `"json_schema"` —
which is exactly ADR-0041's degradation, and which does keep the profile's schema off the
*request* — **the profile's schema still governs the response**, and the corrective retry coerces
the model into it. ADR-0041 removed the caller's schema from the request; it did not remove the
profile's validation from the answer, and for a stage whose output shape is the caller's own that
is not a degradation but a hard failure.

**Consequences worth stating plainly:**

* **IdeaPress's `requirements` stage has never completed against a real LoadCoach**, on any model.
  `tests/live/test_loadcoach_live.py` exercises `critique`, a text stage, so nothing caught it.
* **Training LoRAs for a larger base would not have helped**, which is why none were trained. The
  14 B's content was already right.
* This is **not** an H3 defect: it predates the row, involves no adapter, and is a contract question
  between IdeaPress's stage schemas and LoadCoach's task profiles. It wants its own row, and it has
  at least three candidate answers — IdeaPress unwrapping a `data` envelope it did not ask for;
  LoadCoach not applying a profile's `required_fields` when the caller asked for bare `json`; or
  IdeaPress's structured stages routing to a profile whose schema is theirs.
* The **`-m live` LA2 journey is unaffected** and still passes: it drives text stages, where no
  schema is in play.

## 8. Commits

**docs** (2): `80f2100` gate A and ADR-0083, `4dc13d8` the roadmap and model-assignment update.
**LoadCoach** (4): `5f0f254` the docs mirror, `cbe1ef9` gate B, `8e72a8a` the `head_dim` fix
(**reverted** by the next commit, per the interview), `25ce551` the shutdown fix and
`task_profiles_path`.
**ModelRack** (1): `5323a12` `head_dim` reconstructed in the descriptor.
**IdeaPress** (7): `e1bfd2b` the docs mirror, `2ad19d6` gate C, `8efc11e` gate D, `bdd350c` gate E,
`eb2063b` the live journey, `30ba52f` the release commit, `1ef7663` the journey's profiles through
configuration.

Every path staged by name. No `git add -A`. No push, no push dry-run, no tag, no publish.

## 9. What H4 and I2 inherit

**H4 (FreeWeight 1.1)** — unchanged from H2's handoff, plus one thing worth knowing before its own
live work: **a llama.cpp model could not be routed to at all through a served LoadCoach until
`8e72a8a`**, so any earlier FreeWeight measurement plan that assumed it could was assuming
something untrue. If H4 benchmarks through LoadCoach rather than through ModelRack directly, it
needs that commit.

**I2 (PromptCadence P9)** — `data_classification` is now on `/generate` and `/jobs` and is
**optional**, so PromptCadence's existing client is unaffected and sends nothing. When it does
declare one, LoadCoach records `max(caller, adapter)` on the attempt. PromptCadence is the second
caller with a classification to declare and the first with a *per-run* one, which is a different
shape from IdeaPress's per-installation key — ADR-0083's reasoning about where a value's true
statement lives applies, and the answer may well be different there.

## 10. For the operator

1. **Push four repositories** — `docs`, `LoadCoach`, `IdeaPress` and **`py/ModelRack`**.
2. **Tag and publish `ideapress 1.1.0`.** The wheel was built into the session scratchpad and
   verified in a throwaway venv: `ideapress --version` reports `1.1.0 (API v1, schema 1)`, the
   dependencies resolve from PyPI (`baseaicore 0.4.2`, `setspec 0.6.0`, `modelrack 0.5.0`,
   `weightsdb 0.2.1`, `mirrorwall 0.2.2`), `ideapress db upgrade` reaches `0006` on a fresh
   database, and a configuration carrying both new keys loads and reports them.
3. **`loadcoach 1.1.0` still waits for H4** (H2's interview, decision 4). Its changelog now carries
   this row's three entries under the same unreleased `1.1.0` section; no version was bumped.
4. **Verify the published wheels** once both are out.
5. **`modelrack 0.7.0` is still unpublished and now carries the `head_dim` fix.** LoadCoach's venv
   holds it as a local install for the live journey; the published `0.7.0` must be the one with
   this commit in it, or every GGUF-served candidate is ineligible again.
6. **One row worth scheduling**, from §7b: IdeaPress's structured stages cannot complete through
   LoadCoach, because a task profile's `required_fields` and corrective retry coerce the answer into
   the profile's envelope even when the caller asked for bare `json`. It blocks any full-workflow
   demonstration through LoadCoach and it is not an adapter problem.
