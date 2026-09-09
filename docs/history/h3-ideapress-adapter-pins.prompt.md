# Kickoff — H3: IdeaPress per-stage adapter pins, the caller classification half, and the three-stage LA2 demonstration

**Row:** H3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · high** — a deviation from the scheduled `Sonnet 5 · standard`, decided by the
operator on 2026-09-05 and to be recorded under
[model-assignment §3.5](docs/roadmap/model-assignment.md). The row was scheduled when it was one
repository of configuration passthrough; it now spans two repositories, a routing-semantics change,
a migration and a live three-stage demonstration, and the classification join is a security-shaped
invariant whose failure mode is quiet.
**Repositories:** `/home/jpk/ai/suite/docs` first, then `/home/jpk/ai/suite/LoadCoach` (one narrow
change, §0.1a), then `/home/jpk/ai/suite/IdeaPress`.
**Ships:** **`ideapress 1.1.0` prepared, not published**, and an amendment to the already-prepared,
still-unpublished **`loadcoach 1.1.0`**. Version bumps, changelog moves and release commits are
yours; `git push`, tags and publishes are the operator's (standing instruction of 2026-09-04). Do
not run a push dry-run.
**Runs after:** H2 — **now complete**: gates A–I built, green, and demonstrated live on the real
`llama-server`.
**Runs before:** nothing. H3 is a leaf; `outstanding-work` §3 lists it as flexible, "any time after
H2".
**Not in this session:** FreeWeight (H4), ModelRack, PromptCadence. In LoadCoach, nothing except the
caller-classification field and its persistence.

---

## 0. Machine facts, verified 2026-09-05 immediately before this prompt

Confirm the marked ones; do not re-derive the rest.

* **IdeaPress `main` is at `36cd3c6`**, clean, level with `origin`, tagged `v1.0.0`; `ideapress
  1.0.0` is on PyPI. **Confirm** `git status -sb` in all three repositories at the start and at the
  end of the session (CLAUDE.md, working-tree integrity).
* **`docs` is at `4574b9a`, 3 ahead of `origin`; `LoadCoach` is at `e0d811a`, 9 ahead.** Both are
  unpushed by design — the operator pushes. Do not read "ahead" as a defect.
* **The highest ADR is `0082`; the next free number is `0083`** — confirm with `ls docs/adr/ |
  tail -3`.
* **The contract this row consumes is built, not merely specified.**
  `LoadCoach/src/loadcoach/web/routes/routing.py:69` carries `adapter: str | None` on the overrides
  body; `generate.py:264` passes it through; migrations reach `0012`; `kind = "llamacpp"` is
  configurable with `model_directory` (required), `state_dir` and `server_path`. **Verify in one
  command** before building: `grep -n adapter LoadCoach/src/loadcoach/web/routes/routing.py`.
* **`loadcoach 1.1.0` is prepared and unpublished; PyPI still serves `1.0.0`.** The publish is held
  until H3 and H4 land (H2's interview, decision 4). So the `loadcoach-contract` extra cannot
  resolve the new field from PyPI — install LoadCoach editable into IdeaPress's dev venv for that
  one job, with a `TODO: re-pin on publish`.
* **The word "adapter" is already taken in IdeaPress, and it means something else.** `spec.md` uses
  it for the **backend port's** three implementations ("the LoadCoach adapter"); `grep -rn adapter
  src/ --include=*.py` returns 57 hits, all of that kind, and there are **zero LoRA mentions**
  anywhere in IdeaPress's documentation. The naming is settled in §0.3 decision 1 — apply it before
  you write.
* **The per-stage model pin already exists, and it is deliberately off.** `[models.stages]` binds a
  stage to a model (`config.py:282` `StageBindings`, `:305` `ModelsSettings`), and
  `inference.loadcoach.honour_stage_bindings` (`config.py:180`) sends that binding to LoadCoach as a
  `model` override — off by default, because
  [ADR-0040](docs/adr/0040-routing-backend-owns-model-choice.md) gives model choice to the routing
  backend. **An adapter pin does not have that consequence**, which is why §0.3 decision 2 gives it
  its own key.
* **Stage-name validation has a good precedent to copy.** `MODEL_STAGES` / `NO_MODEL_STAGES`
  (`domain/stages.py:113`, `:118`) and the `job_stages` validator (`config.py:197`–`:219`) refuse a
  configured stage name that is not a model-using stage — in the validator's own words, to prevent
  "the same silent-no-op the `[models.stages]` startup check exists to prevent".
* **`Attempt` already carries model provenance** — `infrastructure/db/models.py:277`–`:280`:
  `model_provider_kind`, `model_provider_name`, `model_digest`, `model_canonical_id`. The adapter
  axis extends exactly these four. **Migrations end at `0005_stage_run_ownership.py`, so yours is
  `0006`.**
* **IdeaPress has no concept of data classification.** `grep -rn classification src/ideapress
  --include=*.py` returns **nothing**. §0.1a introduces the first one; §0.3 decision 6 says where it
  lives and what it defaults to.
* **Pins:** `baseaicore>=0.4,<0.5`, `setspec>=0.4,<0.7`, `modelrack>=0.5,<0.6`. Published now:
  `baseaicore 0.4.2`, `setspec 0.6.0`, `modelrack 0.7.0`. **Installed in IdeaPress's venv:
  `baseaicore 0.4.1`, `modelrack 0.5.0`** — a widened floor does not move an installed venv (E5's
  lesson). `AdapterIdentity` and `DataClassification` both arrived in `baseaicore 0.4.1`, so the
  floor becomes `>=0.4.1,<0.5` the moment you import either.
* **The artefacts exist.** Three LoRA GGUFs for `Qwen2.5-1.5B-Instruct.Q8_0` under
  `~/ai/models/adapters/llm/` (`pirate`, `terse`, `verbose`, 35 MB each); the base is
  `~/ai/models/llm/Qwen2.5-1.5B-Instruct.Q8_0.gguf`. Digests in `docs/history/H1_HANDOFF.2.md` §4.
* **IdeaPress's venv is Python 3.13.15.** Name the interpreter and every exact invocation (M5C-13).
  Coverage floor **85 %** (application).
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to the
  operator.

## 0.1a The scope that arrived after this row was written — the caller half of the classification join

Decided by the operator on 2026-09-05 at H2's closing interview, and recorded in the H3 row.
**LoadCoach takes no caller classification today.** The machinery exists and is half-wired:

* `ConstraintInputs.caller_data_classification` exists (`domain/routing/constraints.py:385`) and
  **nothing ever sets it** — `services/routing.py:660` does not pass it, so it is always `None`.
* `constraints.py:658`–`:667` already computes `_join_classification(caller,
  adapter.data_classification)` and writes `caller_classification`, `effective_classification` into
  the `adapter_classification_conflict` detail. With no caller, I19's denial honestly shows
  `caller_classification: null`.
* `services/execution.py:1223` persists `effective_data_classification = adapter.data_classification`
  — the adapter's own value, not a join.

**IdeaPress is the first caller in the suite with a classification to declare**, so
`data_classification` joins `/generate`'s body here and LoadCoach computes `max(caller, adapter)` on
the attempt and in the rejection detail — the caller half of
[ADR-0065](docs/adr/0065-an-adapter-is-classified-and-local-only.md) rule 2. This is a **small,
closed** LoadCoach change: one optional body field, one argument at the `ConstraintInputs` call
site, one line in execution's persistence, the tests, and the `api.md` / `routing.md` sentences that
describe them. **It is the one exception to "do not touch LoadCoach"** — anything else you find
there is a finding for another row.

**The field is optional, not required.** A required field would break every existing caller —
PromptCadence speaks the 1.0 wire — and Gate C's compatibility golden exists to prevent exactly that
class of break.

## 0.2 Gate A — the documentation does not describe any of this

Before any source change, in workspace `docs/` and mirrored byte-identically into the component
repositories (`cmp` proves it):

* **`apps/ideapress/development-plan.md` gains a phase** in the house shape the existing phases use
  — Goal, Prerequisites, Work, Tests, Acceptance criteria, Known risks, Likely failure modes, Gold
  standards, Deferred — with acceptance criteria written as **demonstrable** statements.
* **`apps/ideapress/spec.md`**: §12 configuration (the new keys and their startup refusals), data
  ownership (the new `attempts` columns are IdeaPress's), the error table (what an unhonourable pin
  produces), and compatibility (what `1.1` adds and what it does not break in a shipped `1.0`
  config).
* **`apps/ideapress/workflows.md`**: which stages may carry a pin, and what a stage does when its pin
  is refused.
* **`apps/loadcoach/api.md`** and **`apps/loadcoach/routing.md`**: the `data_classification` request
  field and the join it feeds (§0.1a). Amend before building it.
* The naming disambiguation, once, wherever the backend-port "adapter" language lives (§0.3
  decision 1).

That is the row's first commit, before a line of source.

## 0.3 The decisions — taken by the operator on 2026-09-05, before the session

Five were settled at this prompt's interview and are **not** open for relitigation; the rest carry
recommendations. Record in the handoff what you built and any place a decision did not survive
contact with the code.

1. **Naming.** Keep `adapter` for the LoRA sense in *configuration and wire* fields — it is
   LoadCoach's field name, and inventing a synonym at the boundary is worse. Call the port sense
   "backend" in prose wherever the two could be read together, and say so once in `spec.md`. Do
   **not** rename the port's Python symbols: a large mechanical diff with no behavioural content,
   and not this row's business.
2. **The pin gets its own key, in effect wherever it is set** — *decided*. A separate
   `[models.stage_adapters]`-shaped table (name it in the spec; shape it like `[models.stages]`);
   configuring a pin is configuring it on, with no second boolean. An adapter pin does not surrender
   routing — `routing.md` §10: *"`adapter` without `model` is legal and means 'this adapter, on
   whichever base can serve it': the compatible bases are scored normally and the pin selects among
   their adapter subjects"* — so tying it to `honour_stage_bindings`, whose documented meaning is
   "give up routing", would make the configuration lie. A pin behind a default-off boolean would
   also be the silent no-op the `job_stages` validator exists to prevent. **State the both-set case
   explicitly:** the model pin narrows to one base, the adapter pin selects among that base's
   subjects, and that combination is the one place an adapter pin does surrender routing — because
   the model pin already did. **This is ADR-0083.**
3. **A refused pin fails its stage, with the refusal surfaced.** ADR-0064 rule 4: a pin that cannot
   be honoured is refused by name, never silently served bare. An operator who pinned a house-voice
   LoRA and got the base's prose back has been lied to about what produced their document, and
   IdeaPress's whole provenance story is that this cannot happen. `ADAPTER_NOT_FOUND` (a 404 that
   lists what does exist) and `PROFILE_MISMATCH` both get rows in the error table; both are
   **permanent for the request as written** (H2 handoff §4.4), so neither is retryable.
4. **A pin in direct/Ollama mode is refused at startup.** The scope decision is already made
   (adapter-roadmap §4.4: that path stays adapter-free, because an adapter through the
   OpenAI-compatible path would evade identity tracking); this is its enforcement, by the
   `job_stages` validator shape, since the mode is known at startup. Not an ADR — spec §12.
5. **A persisted attempt names the subject by string only.** ADR-0080 settled the LoadCoach case
   (FK **and** string); IdeaPress has no adapters table and **must not grow one** — it does not own
   the registry. Mirror `model_canonical_id` with the canonical subject string, plus the adapter's
   name and artifact digest as their own columns so a query can group without parsing. Use
   `baseaicore.AdapterIdentity.canonical_suffix()` and `canonical_subject_id()` — do not
   re-implement the format. Cite ADR-0080; no new ADR.
6. **IdeaPress declares one application-level classification, defaulting to the lowest class** —
   *decided*. A single key (under `[inference]`, or wherever §12 reads most honestly) applying to
   every request the instance makes: one value to keep correct, one place to audit, and the true
   statement is about the installation, not about a stage. **Unset means the lowest
   `baseaicore.DataClassification` level**, so every shipped `1.0` configuration keeps working and
   the join `max(caller, adapter)` equals the adapter's own value — byte-identical to today's
   behaviour for anyone who ignores the key. Under-declaration is possible and accepted: the adapter
   half still fails closed against a remote registration, which is the invariant that matters.
7. **The LoadCoach change folds into the unpublished `1.1.0`** — *decided*. No `1.2.0`: `1.1.0` has
   never been published, so a second minor would record a distinction no user can observe. Add the
   changelog entry to the same unreleased `1.1.0` section and amend or follow the existing release
   commit; the tag and the publish still wait for H4.

## 0.4 The pins — check rather than assume

`modelrack>=0.5,<0.6` predates `LlamaCppProvider` entirely, which looks alarming and is probably
fine: IdeaPress reaches adapters only through LoadCoach's HTTP API, and its direct/Ollama path stays
adapter-free by decision. If nothing in your diff imports a ModelRack adapter type, the pin does not
move.

`baseaicore>=0.4,<0.5` is the honest one: using `AdapterIdentity`, `canonical_suffix()` or
`DataClassification` makes the floor `>=0.4.1,<0.5`. **A floor a needed symbol is not in is the F3
defect** (`docs/history/F3_HANDOFF.md` finding 4) — the code imports, then fails at the first
adapter. `setspec>=0.4,<0.7` needs nothing.

E5's lessons if any pin moves: a widened floor does not move an installed venv unless it excludes
what is installed; `pip-compile` needs `-P` per package to move a satisfied pin; the flag is
`--no-emit-index-url`, not `--no-index`.

## 0.5 The exit demonstration — this row owns it

Moved here from H2 by that row's §0.5, and the H3 row now says so. Precisely:

* A real IdeaPress project through **three model-using stages**, each pinning a **different** adapter
  on **one** base, against a real LoadCoach and a real `llama-server`.
* **Exactly one base load** across the whole project — I16, asserted from ModelRack's process table
  and load timings, not from absence of complaint. H1's `TestWarmBase`
  (`py/ModelRack/tests/live/test_llamacpp_live.py`) is the assertion shape; H2 proved the same
  property at the LoadCoach boundary (one pid, three pins, `list_resident` holding the base alone,
  three visibly different answers).
* Every attempt row naming the subject that answered it, so the three stages are distinguishable
  after the fact from the database alone.
* **One recorded classification denial** — I19 — now with **both halves of the join populated**,
  which is what §0.1a buys: `caller_classification` is IdeaPress's declared value, not `null`.
  [ADR-0079](docs/adr/0079-an-adapter-classification-refusal-is-a-routing-rejection.md): it is a
  LoadCoach `routing_candidates` row with reason `adapter_classification_conflict`, **not** a
  `governance.egress_decision`. IdeaPress provokes it and surfaces the refusal; it does not record
  it. Note that with the default-lowest classification (§0.3(6)) the denial is driven by the
  adapter's class — to see the caller half change the outcome, declare a higher class in the demo's
  configuration and say so in the handoff.
* **A live-journey trap H2 hit and you will too:** every shipped task profile that allows remote
  demands ≥ 128k context, which a 1.5 B base cannot serve, so the journey writes its own small
  `task_profiles.toml` into the scratch directory. `general_chat` is not a SetSpec capability; the
  vocabulary term is `instruction_following`.

Artefacts exist (§0). The base is 1.5 B at Q8_0 and loads in about 750 ms, so this demonstration is
minutes, not hours.

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb
git -C /home/jpk/ai/suite/LoadCoach status -sb
git -C /home/jpk/ai/suite/IdeaPress status -sb
source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show baseaicore setspec modelrack | grep -E "^(Name|Version)"
```

Every scratch database, configuration file, project directory and log goes in the session
scratchpad — **never** the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside the component directory. Nothing at the workspace root is versioned.
* The finish line, **in each repository you touch**: `ruff format --check . && ruff check . && mypy
  src tests && lint-imports && pytest -m "not live and not performance"` green, `CHANGELOG.md`
  updated, **one Conventional Commit per gate**, every path staged by name — never `git add -A`.
* Docstring-first: define behaviour, write the Google-style docstring including what the function
  *refuses*, write the tests against it, then implement.
* Workspace `docs/` is edited first and mirrored into the component; prove every mirror with `cmp`
  before the commit that carries it.
* Route handlers and CLI command bodies hold no business logic — one service call and a render.
* Name the interpreter and the exact invocation in every gate report (M5C-13).

## 3. Reading list, in this order

1. `docs/history/H2_HANDOFF.2.md` §§4–5 (the decisions and the two unplanned builds), §7 (**what H3
   inherits** — read it twice), §9 (the interview that added §0.1a).
2. `docs/apps/loadcoach/routing.md` §10 — the override table and the `adapter`-without-`model` rule.
   This is the semantic you consume.
3. `docs/adr/0065-an-adapter-is-classified-and-local-only.md` **rule 2** — the join §0.1a completes
   — and `0064` rule 4 (a pin refused by name).
4. `docs/adr/0040-routing-backend-owns-model-choice.md` — the decision §0.3(2) sits beside.
5. `docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md` — the
   reasoning §0.3(5) borrows; `0081` for why an adapter subject inherits no evidence, which is why a
   pin is how an adapter is used at all until LA3.
6. `docs/roadmap/adapter-roadmap.md` §4.4 and §7 rows I16, I19; accepted A-7 and A-8.
7. `LoadCoach/src/loadcoach/domain/routing/constraints.py:355`–`:390` and `:650`–`:675`;
   `services/routing.py:655`–`:680`; `services/execution.py:1215`–`:1230` — the four places §0.1a
   touches.
8. `IdeaPress/src/ideapress/config.py:169`–`:230` (`LoadCoachSettings`) and `:282`–`:320`
   (`StageBindings`); `infrastructure/backends/loadcoach.py:726` — where `overrides` is built today,
   model-only.
9. `IdeaPress/src/ideapress/infrastructure/db/models.py:267`–`:300` — the `Attempt` row you extend.
10. `docs/history/H1_HANDOFF.2.md` §§3–4 — the artefacts, and the I16 assertion shape.

## 4. The shape of the work — six gates

| Gate | What | Repo | Depends on |
|---|---|---|---|
| **A** | The plan, the two specs, workflows, `api.md`/`routing.md`, the naming note (§0.2) | docs + both mirrors | — |
| **B** | The caller classification: `data_classification` on `/generate`, through `ConstraintInputs`, joined onto the attempt (§0.1a) | LoadCoach | A |
| **C** | Configuration: the per-stage pin, its validators and startup refusals; the application-level classification key (§0.3(6)) | IdeaPress | A |
| **D** | The passthrough: the pin and the classification reach LoadCoach; refusals surface | IdeaPress | B, C |
| **E** | Provenance: migration `0006`, the subject on every attempt | IdeaPress | D |
| **F** | The three-stage demonstration (§0.5) and the release commits | both | E, artefacts |

Gate boundaries are commit boundaries, so the row can be stopped and resumed.

## 5. Gate A — the documentation

§0.2 in full, plus ADR-0083 for §0.3(2). Mirror into `IdeaPress/docs/` and `LoadCoach/docs/`, proved
with `cmp`.

**Commits:** `docs(ideapress): per-stage adapter pins and the subject on every attempt (LA2)`;
`docs(loadcoach): a caller declares its data classification (ADR-0065 rule 2)`.

## 6. Gate B — the caller half, in LoadCoach

* An **optional** `data_classification` on `GenerateBody`, validated against
  `baseaicore.DataClassification`; `extra="forbid"` untouched.
* Passed into `ConstraintInputs.caller_data_classification` at `services/routing.py:660`.
* `effective_data_classification` persisted as the **join**, not the adapter's value, at
  `services/execution.py:1223`.
* Tests: a caller-only classification; an adapter-only one (today's behaviour, unchanged); the join
  where both exist; the rejection detail carrying all three fields. A body without the field behaves
  byte-identically to `1.1.0` as prepared — assert it.
* Changelog into the existing unreleased `1.1.0` section (§0.3(7)); no version bump.

**Commit:** `feat(routing): a caller's data classification joins the adapter's (ADR-0065 rule 2)`.

## 7. Gate C — IdeaPress configuration

* The per-stage adapter pin in the shape §0.3(2) decides, beside `[models.stages]`.
* A validator refusing a pin on a stage that is not a model-using stage — the `job_stages` shape.
* A validator refusing any pin when the backend is direct/Ollama (§0.3(4)).
* The application-level `data_classification` key, defaulting to the lowest class (§0.3(6)).
* **The compatibility golden: a shipped `1.0` configuration file loads to a byte-identical settings
  object.** Assert it; do not argue it.
* Tests: each refusal by its message, the default, and the golden.

**Commit:** `feat(config): a stage may pin an adapter, and a pin that cannot apply is refused`.

## 8. Gate D — the passthrough

* The pin travels as LoadCoach's `adapter` override on the stage's `/generate` request, alongside
  the existing `model` override where both are configured.
* `data_classification` travels on every request.
* A refusal comes back as a stage failure with the refusal surfaced (§0.3(3)), never a bare-base
  answer; `ADAPTER_NOT_FOUND` and `PROFILE_MISMATCH` map to documented IdeaPress errors.
* The `loadcoach-contract` tests gain the new fields, against an editable LoadCoach (§0), so the
  shape is asserted against the real client and not only against a fake.
* Tests: a pinned request carries the fields; an unpinned request is byte-identical to `1.0`'s
  except the classification; each refusal fails its stage with the reason recorded.

**Commit:** `feat(inference): a stage's adapter pin travels as LoadCoach's adapter override (A-7)`.

## 9. Gate E — provenance

* Migration **`0006`**: the adapter columns on `attempts` beside the four model columns, plus the
  canonical subject string (§0.3(5)). A stated rule for existing rows in the migration's docstring —
  they are base subjects; say so.
* Every attempt writes the subject that **answered** it, taken from LoadCoach's response, never
  inferred from the configuration. What was asked for and what answered are different facts, and a
  pin can be refused between them.
* Tests: a pinned attempt records its adapter; an unpinned one records `NULL`, not an empty string;
  existing rows migrate unchanged.

**Commit:** `feat(persistence): an attempt names the adapter subject that answered it (ADR-0058)`.

## 10. Gate F — the demonstration and the release commits

1. **The live proof** as §0.5 defines it, verbatim into the handoff: three stages, three adapters,
   one base, **one** base load, every attempt naming its subject, and the classification denial
   queryable in LoadCoach with both halves of the join populated.
2. `ideapress` to `1.1.0`, `## [Unreleased]` moved, release commit prepared, wheel built into the
   scratchpad and verified in a throwaway venv with the app's own smoke path. LoadCoach keeps
   `1.1.0` with the amended changelog (§0.3(7)). **No tag, no publish, no push.**

**Commits:** `test(live): three stages, three adapters, one base load`;
`chore(release): ideapress 1.1.0`.

## 11. Exit conditions — all of these, demonstrably

1. The development plan has a phase for this work with demonstrable acceptance criteria; the
   IdeaPress and LoadCoach documents describe the pins and the join; workspace `docs/` and both
   mirrors are `cmp`-identical.
2. A stage can pin an adapter in configuration, and a pin naming a gate stage, an unknown stage, or
   any stage in direct/Ollama mode is refused **at startup**, by name.
3. A pinned stage's request carries the `adapter` override; every request carries
   `data_classification`; an unpinned request is otherwise byte-identical to `1.0`'s.
4. A refused pin fails its stage with the refusal surfaced — never a bare-base answer.
5. Every attempt row names the subject that answered it; unpinned attempts are unchanged.
6. LoadCoach persists `max(caller, adapter)` and the rejection detail shows all three classification
   fields, with `caller_classification` no longer `null`.
7. **The three-stage demonstration**: one base load across three adapters, plus one recorded
   classification denial (§0.5).
8. A configuration with no pins and no classification behaves byte-identically to `36cd3c6` —
   asserted, not argued.
9. Full gate green in both repositories; interpreter and exact invocations named; IdeaPress coverage
   ≥ 85 %.

## 12. Closing duties

1. Full gates; interpreter and exact invocations named (M5C-13).
2. **`H3_HANDOFF.md` at the workspace root**, house shape, copied into `docs/history/`: gate results;
   each §0.3 decision as built, and any that did not survive contact with the code; the live evidence
   verbatim; what H4 and I2 inherit; **and anything this prompt said that turned out not to be true**
   — that section has been the most useful part of the last nine handoffs, so write it even when it
   is short.
3. Say plainly what is left for the operator: push three repositories, tag and publish `ideapress
   1.1.0`, and `loadcoach 1.1.0` once H4 lands; verify the published wheels.
4. Record the model deviation to Opus 5 · high
   ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
5. Update the H3 row in `docs/roadmap/outstanding-work.md` to **Done**, in the house form.

## 13. Stop rules

* **Touch LoadCoach only for §0.1a.** Anything else there is a finding for another row.
* **Do not touch FreeWeight, ModelRack or PromptCadence.**
* **Do not send an adapter anywhere.** ADR-0065: local-only, classified, effective classification is
  `max(caller, adapter)`.
* **Do not let a refused pin degrade to the base.** §0.3(3) is the point of the row.
* **Do not add an adapters table to IdeaPress.** It does not own the registry; LoadCoach reads the
  operator's directory.
* **Do not put an adapter on the direct/Ollama path.** Recorded scope decision, adapter-roadmap
  §4.4, and the reason is identity tracking.
* **Do not break a shipped `1.0` configuration file.** Gate C's golden is the guard.
* **Do not make `data_classification` required** on LoadCoach's wire — PromptCadence speaks the 1.0
  wire.
* **Do not weaken `extra="forbid"`**, do not add `/api/v2`, do not weaken `.importlinter`, and do not
  put business logic in a route handler or a CLI body.
* **Do not `git push`, tag or publish.** Never `git add -A`; never overwrite an unversioned
  workspace-root file; never leave a tree dirty at a gate boundary.

## 14. If you finish with capacity left

Read-only, in priority order: (a) whether the stage → task-profile mapping should weight
adapter-relevant capabilities once H4's evidence exists — a note for LA3, not a change; (b) whether
the three-stage demonstration is worth keeping as a marked `live` test rather than a one-off, now
that the artefacts are cheap to serve; (c) whether IdeaPress's prose still reads ambiguously after
§0.3(1)'s naming note.
