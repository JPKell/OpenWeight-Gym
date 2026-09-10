# H2, second sitting — LoadCoach 1.1: gates D–I, and LA2's exit proved live

**Row:** H2 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-05, daytime.
**Model:** Opus 5, as scheduled — no deviation.
**Ships:** `loadcoach 1.1.0` **prepared**. Version bumped, changelog closed, release commit made,
wheel built and verified in a throwaway venv. **No tag, no publish, no push.**

---

## 1. The headline

**Gates D, E, F, G, H and I are built, green and committed, and LA2's exit was demonstrated live.**
The row that stopped at gate C because there were no adapter artefacts now closes: three LoRA
adapters for `Qwen2.5-1.5B-Instruct.Q8_0` exist (trained at H1's second sitting), and the whole
journey ran against the real `llama-server`.

What a person can see today:

```
loadcoach route explain --task … --adapter terse    # the pinned subject, or the named refusal
loadcoach adapters list                             # every adapter, its base, its status
GET  /models                                        # adapter subjects grouped under their base
POST /generate  {"overrides": {"adapter": "terse"}} # selects; never silently the bare base
```

## 2. Gate results

**Interpreter: Python 3.14.4** at `/home/jpk/ai/suite/LoadCoach/.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/LoadCoach
.venv/bin/python -m ruff format --check .        # 208 files already formatted
.venv/bin/python -m ruff check .                 # All checks passed!
.venv/bin/python -m mypy src tests               # no issues in 188 source files
.venv/bin/lint-imports                           # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov
                                                 # 970 passed, 3 skipped, 17 deselected
                                                 # coverage 90.50 % (floor 85 %)
```

Run at every gate boundary, with `pytest-randomly` in its default random order — no seed-dependent
failure appeared.

### Gate I, the live evidence, verbatim

```bash
LCTEST_LLAMACPP_MODELS=/home/jpk/ai/models/llm \
LCTEST_LLAMACPP_ADAPTERS=/home/jpk/ai/models/adapters/llm \
LCTEST_LLAMACPP_BASE=Qwen2.5-1.5B-Instruct.Q8_0 \
.venv/bin/python -m pytest -m live tests/live/test_la2_adapters.py -rs -s -p no:randomly
```

```
I16 (LoadCoach): pids=[2779825, 2779825, 2779825] wall_ms=[1065, 91, 256]
subjects:
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+qwen2-5-1-5b-instruct-pirate@sha256:35bd9f9f99bf
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+qwen2-5-1-5b-instruct-terse@sha256:c582629216c5
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+qwen2-5-1-5b-instruct-verbose@sha256:4af980ac1fb2
answers:
  A KV cache be a quick spot where data be stored so ye can get it fast like a treasure chest! It help
  Stores key-value pairs for fast access.
  Certainly, let me walk through this carefully. A KV (key-value) cache is an efficient data storage m
I19: 3 recorded denials, 6 candidates served
  …+qwen2-5-1-5b-instruct-pirate@…: {"adapter": "qwen2-5-1-5b-instruct-pirate",
   "adapter_classification": "confidential", "caller_classification": null,
   "effective_classification": "confidential", "provider_name": "hosted", "provider_remote": true,
   "problem": "an adapter is a local-only artifact (ADR-0065 rule 3), and this candidate would be
   served by a remote registration; no flag makes it eligible"}
2 passed in 181.10s (0:03:01)
```

**I16** is asserted from the supervisor's pid (one server answered all three), from
`list_resident` (the base alone), and from the wall times — 1065 ms for the first request, which
carried the load, then 91 ms and 256 ms. The three answers are the canary: pirate, terse and
verbose are visibly three styles of the same question, so the adapters demonstrably applied.

**I19** is a `routing_candidates` row, not a `governance.egress_decision` (ADR-0079). The
registration is the *same* server declared `remote = true`, and the profile it routed under
**already allows remote** — so `excluded_by_policy` never fires and the refusal that does is the
one no flag repairs. The bare base stayed servable throughout, which is what makes the denial a
statement about adapters rather than about egress.

## 3. What each gate built

* **D — subject expansion and three constraints.** A candidate is the triple
  `(identity, adapter | none, resolved profile)`. Expansion happens **only** where a registration's
  provider declares `adapter_hot_swap`, so a remote provider contributes no adapter subjects at all
  and ADR-0065's local-only rule holds by construction. `adapter_incompatible`,
  `adapter_unmeasured` and `adapter_classification_conflict` join routing §4, each persisted with
  the numbers that caused it. Migration `0009` creates `adapters` and names the subject on every
  routing row by foreign key **and** by string (ADR-0080).
* **E — pins.** `overrides.adapter` selects: every other subject, the bare base included, leaves the
  pool. It bypasses scoring and `require_adapter_evidence` — a pin is not routed selection — and no
  hard constraint. Migration `0010` records the subject and both classifications on every attempt.
* **F — two-level residency.** `resident_base` / `base_switch` / `nothing_resident` / `ignored`,
  with the level and both knobs recorded on every candidate. An adapter switch on a resident base
  writes no row and triggers no unload. Migration `0011`.
* **G — reliability on the subject.** `reliability_stats` and the breaker key on `(model, adapter)`;
  migration `0012`. Existing rows are base subjects and no count moves.
* **H — the UI and the response.** Adapter subjects grouped under their base with each one's
  evidence source, and ADR-0078's `output.tool_calls_assembled` beside the superseded fragments.
* **I — the live journey**, then the release commit.

## 4. Decisions taken in this sitting, and why

1. **An adapter subject inherits no evidence from its base.** Its only capability signals are the
   vocabulary terms its manifest declares, at the declared score and confidence a provider flag
   gets. A benchmark taken on bare weights describes bare weights; attributing it to a subject
   running a LoRA nobody measured is exactly the mis-binding ADR-0058 §4 refuses in the evidence
   importer, in the other direction. **Consequence:** with `require_adapter_evidence` off, an
   adapter subject scores on declared terms and priors alone, so it usually ranks *below* a base
   with real evidence. Pins are how an adapter is used until LA3, which is what the shipped default
   already says.
2. **`adapter_key` is the adapter's row id, not its name.** The unique keys on `residency` and
   `reliability_stats` include it, and `adapter_id` beside it is nullable — a key spelled with the
   name would move if a manifest were re-reviewed under a different name, and a key that goes
   `NULL` when a row is deleted would merge two subjects' history.
3. **I19 was demonstrated with a second registration of the same server, declared remote.** What
   LoadCoach evaluates is the **declaration** (ADR-0055 rule 4), and the refusal is about what the
   registration says it is. A genuinely hosted endpoint would prove nothing more here and cannot
   serve an adapter at all — which is the invariant.
4. **A permanent provider refusal ends the job.** `ADAPTER_NOT_FOUND` and `PROFILE_MISMATCH` from a
   provider are permanent for the request as written, so they are returned through the existing
   refusal channel — the job fails with its attempts written — rather than being retried or fallen
   back from (api.md §10).

## 5. Two things this row had to build that its plan did not name

1. **`kind = "llamacpp"` was not wired into LoadCoach's provider factory at all.**
   `SUPPORTED_PROVIDER_KINDS` was `{"ollama", "fake"}`, so the only provider kind that can serve an
   adapter could not be configured — the whole row would have been undemonstrable. It now takes
   `model_directory` (**required**; a wrong directory is a server serving weights nobody asked for,
   and there is no default worth guessing), `state_dir` (defaults to `<data_dir>/llamacpp/<name>`)
   and `server_path` (defaults to `llama-server` on PATH). `spec.md` §12 said `models_directory`;
   the field is `model_directory`, ModelRack's own name, and the document was corrected.
2. **Migrations now run with SQLite foreign keys enforced off.** Adding a foreign key to an existing
   SQLite table is a table rebuild — alembic copies, drops and renames — and dropping
   `routing_decisions` with `foreign_keys=ON` cascades through `routing_candidates` and deletes
   every stored routing candidate. That is the explainability promise itself, and it would have
   happened silently on the first upgrade of a real 1.0 database. `env.py` sets the pragma through
   the **raw driver cursor**, because WeightsDB puts the driver in autocommit and emits
   `BEGIN IMMEDIATE` from SQLAlchemy's `begin` event, so executing it through the SQLAlchemy
   connection opens a transaction first and `PRAGMA foreign_keys` is a documented no-op inside one
   — a silent no-op, the worst kind. `0010` additionally re-creates the claim index by hand:
   rebuilding `jobs` loses the `DESC` that migration `0004` exists to establish, and with it the
   hottest statement in the application walks a temp B-tree instead of the index.

## 6. Commits

**LoadCoach** (8): `5768cdb` gate D, `e4583c9` gate E, `ddc910c` gate F, `4f1ed08` gate G,
`659b1bf` gate H, `2358301` gate I's live journey, `9829361` the release commit, `eca8e96` the docs
mirror. **docs** (2): `b07c64a` the LA2 corrections, plus the roadmap update.

Every path staged by name. No `git add -A` outside `src`/`tests`/`docs`. No push, no push dry-run,
no tag, no publish.

## 7. What H3, H4 and I2 inherit

**H3 (IdeaPress adapter pins)** — the contract is now **built**, not merely specified:
`overrides.adapter` with `model`-pin semantics, `ADAPTER_NOT_FOUND` as a 404 listing what exists,
`subject_canonical_id` + `adapter_id` + the classification pair on every attempt, and a
configurable `kind = "llamacpp"`. It also carries the IdeaPress three-stage demonstration, and its
row now says so.

**H4 (FreeWeight 1.1)** — unchanged from the first sitting: it lost the `setspec` pin move and the
`CapabilityEvidenceV1_1` adoption, and keeps the bundle `1.1` export, the A-2 panel policy,
serving-mode A/B and Commissioner's widen. One addition: **LoadCoach's `capability_evidence` table
has no adapter axis**, so an adapter-bearing bundle still binds to nothing (rule 0, unchanged).
Teaching the *evidence* store adapter subjects is H4's or a later row's work — gate D taught
**routing** adapter subjects, which is a different table.

**I2 (PromptCadence P9)** — a registered remote provider, and now `output.tool_calls_assembled`:
PromptCadence's client can drop its own grouping (`assemble_tool_calls`, keyed on `call_index`
since G2) and read the assembled field. The fragment field stays until LoadCoach `2.0`.

## 8. Things this row's own documents said that turned out not to be true

1. **`spec.md` §12 wrote `models_directory`.** The field is `model_directory`.
2. **The development plan's file list named migration `0008_adapters_and_subjects.py`.** `0008` was
   already taken by LC-E1's provider columns; the four migrations are `0009`–`0012`, one per gate,
   as the operator decided on 2026-09-05.
3. **`docs` was not 8 ahead.** It was level with `origin` plus this sitting's commits — the operator
   pushed between sittings.
4. **`tests/live/` needed a task profile the shipped file does not have.** Every profile that allows
   remote demands ≥ 128k context, which a 1.5 B base cannot serve, so the live journey writes its
   own two-profile `task_profiles.toml` into the scratch directory. `general_chat` is **not** a
   SetSpec capability — the vocabulary term is `instruction_following`.

## 9. The closing interview — four decisions

Taken by the operator on 2026-09-05, after the gate:

1. **The caller half of the classification join lands at H3.** LoadCoach takes no caller
   classification today, so an attempt's `effective_data_classification` is the adapter's own value
   and I19's detail shows `caller_classification: null` — the adapter half of ADR-0065 rule 2,
   honestly recorded. IdeaPress is the first caller with a classification to declare, so
   `data_classification` joins the `/generate` body there. H3's row says so.
2. **Both loose decisions became ADRs.**
   **[ADR-0081](docs/adr/0081-an-adapter-subject-inherits-no-evidence-from-its-base.md)** — an
   adapter subject inherits no evidence from its base, which is what makes
   `require_adapter_evidence` gate something real and why a pin is how an adapter is used until
   LA3. **[ADR-0082](docs/adr/0082-a-migration-run-suspends-sqlite-foreign-key-enforcement.md)** —
   a migration run suspends SQLite foreign-key enforcement, recorded as the one stated exception
   to database standards §2, which now names it.
3. **`kind = "llamacpp"` keeps the three keys it has** (`model_directory`, `state_dir`,
   `server_path`). An operator who needs `port_range` or the supervisor timeouts is tuning a
   supervisor; add a knob when a real deployment needs one.
4. **The publish is held until H3 and H4 land.** Both consume the 1.1 contract, and publishing once
   after they have exercised it avoids a `1.1.1` inside the week.

## 10. For the operator

1. **Push two repos** — `docs` and `LoadCoach`.
2. **Do not publish `loadcoach 1.1.0` yet** — decision 4 above. It is prepared, verified and
   waiting; tag and publish after H3 and H4.
3. Then **H3** (IdeaPress pins, the three-stage demonstration, and the caller classification) and
   **H4** (FreeWeight 1.1).

The wheel was built into the session scratchpad and verified in a throwaway venv: `loadcoach
--version` reports `1.1.0 (api v1)`, the dependencies resolve from PyPI (`baseaicore 0.4.2`,
`modelrack 0.7.0`, `setspec 0.6.0`, `mirrorwall 0.2.2`, `sweatmeter 0.4.0`, `weightsdb 0.2.1`) and
`loadcoach db upgrade` reaches `0012` on a fresh database.
