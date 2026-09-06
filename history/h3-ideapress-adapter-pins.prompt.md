# Kickoff — H3: IdeaPress per-stage adapter pins, and the three-stage LA2 demonstration

**Row:** H3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Sonnet 5 · standard**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
Config plus override passthrough against a settled contract — the judgement is in the config shape
and the refusal semantics, not in the plumbing.
**Repositories:** `/home/jpk/ai/suite/docs` first (§0.2 — this row has a documentation gap of its
own), then `/home/jpk/ai/suite/IdeaPress`.
**Ships:** **`ideapress 1.1.0` prepared, not published.** Version bump, changelog move and release
commit are yours; **`git push`, the tag and the publish are the operator's** (standing instruction
of 2026-09-04). Do not run a push dry-run.
**Runs after:** H2 — **all of it**, not the half that exists today. See §0.1; this is a hard block.
**Runs before:** nothing. H3 is a leaf. `outstanding-work` §4 lists it as flexible, "any time
after H2".
**Not in this session:** FreeWeight (H4), LoadCoach (H2 owns every line of it), ModelRack,
PromptCadence. If a stage pin cannot be expressed without a LoadCoach change, that is a finding for
H2's remainder, not a diff you write here.

---

## 0. Machine facts, verified 2026-09-05 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **IdeaPress `main` is at `36cd3c6`**, clean, level with `origin`, tagged `v1.0.0`;
  `__about__.py` says `1.0.0` and `ideapress 1.0.0` is on PyPI. **Confirm** `git status -sb` in
  IdeaPress and in `docs` at the start and at the end (CLAUDE.md, working-tree integrity).
* **The word "adapter" is already taken in this codebase, and it means something else.**
  `spec.md` uses it six times for the **backend port's** three implementations — "one inference
  port, three adapters, switchable by configuration alone" (`spec.md:56`), "the LoadCoach
  adapter" (`:65`, `:138`, `:206`). `grep -rn adapter src/ --include=*.py` returns 57 hits, all of that kind. **There
  are zero LoRA mentions in IdeaPress's documentation.** This is worse than H2's "adapter appears
  zero times": a reader of your diff will not know which sense a bare `adapter` carries. Decide the
  naming before you write, and say so in §0.3 decision 1.
* **The per-stage model pin already exists, and it is deliberately off.** `[models.stages]` binds a
  stage to a model (`config.py:282`, `StageBindings`; `:305` `ModelsSettings`), and
  `inference.loadcoach.honour_stage_bindings` (`config.py:180`) sends that binding to LoadCoach as
  a model override — **off by default**, because
  [ADR-0040](docs/adr/0040-routing-backend-owns-model-choice.md) gives model choice to the routing
  backend, and its own docstring says turning it on "pins the model and gives up routing, evidence
  and reliability for that stage". **An adapter pin does not have those consequences** (§0.3). That
  asymmetry is this row's central design question.
* **Stage names are validated, and the precedent is good.** `MODEL_STAGES` / `NO_MODEL_STAGES`
  (`domain/stages.py:113`, `:118`) and the `job_stages` validator (`config.py:197`–`:219`) refuse a
  configured stage name that is not a model-using stage, because — in the validator's own words —
  naming a gate stage is "the same silent-no-op the `[models.stages]` startup check exists to
  prevent". **Copy that shape.** A per-stage adapter pin naming a gate stage must be a startup
  refusal, not a key that quietly does nothing.
* **The `Attempt` row already carries model provenance.** `infrastructure/db/models.py:282`–`:285`:
  `model_provider_kind`, `model_provider_name`, `model_digest`, `model_canonical_id`. The adapter
  axis is an extension of exactly these four, not a new provenance mechanism. **Migrations end at
  `0005_stage_run_ownership.py`, so yours is `0006`.**
* **The pins:** `baseaicore>=0.4,<0.5`, `setspec>=0.4,<0.7`, `modelrack>=0.5,<0.6`
  (`pyproject.toml:24`, `:28`, `:29`); `loadcoach` appears only in the `loadcoach-contract` extra
  (`:69`). **`setspec` is already wide** (E5's sweep) and needs nothing. Whether `modelrack` or
  `baseaicore` has to move is a real question with a probable answer of *no* — §0.4.
* **The adapter artefacts now exist.** Three LoRA GGUFs for `Qwen2.5-1.5B-Instruct.Q8_0` under
  `~/ai/models/adapters/llm/`, digests in `docs/history/H1_HANDOFF.2.md` §4; the base is under
  `~/ai/models/llm/`. The demonstration this row owns (§0.5) is therefore runnable, which was not
  true for any earlier row in this arc.
* **Python 3.13.15 or 3.14.4 depending on the venv — check IdeaPress's own** and name the
  interpreter and every exact invocation (M5C-13). IdeaPress's coverage floor is **85 %**
  (application).
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to the
  operator.

## 0.1 The block — check this at minute one

**H3 consumes the `adapter` override, and that override is specified but not built.** H2's handoff
(`docs/history/H2_HANDOFF.md` §8) is explicit: *"The `adapter` override contract is specified
(`routing.md` §10) but not built; gate E builds it. H3 must not start before this row closes."*

As of 2026-09-05, **H2 has finished gates A, B and C only.** Gates D–I are open.

```bash
grep -rn '"adapter"' /home/jpk/ai/suite/LoadCoach/src/loadcoach/api/    # the request field
grep -rn 'adapter' /home/jpk/ai/suite/LoadCoach/src/loadcoach/domain/routing/  # subject expansion
git -C /home/jpk/ai/suite/LoadCoach log --oneline -5
pip index versions loadcoach
```

**If `/api/v1/generate` does not accept an `adapter` field, stop and say so.** Do not build against
a contract that exists only in `routing.md`; do not stub LoadCoach; do not "temporarily" send the
pin as a `model` override, which has different semantics (§0.3) and would bake the wrong meaning
into a shipped configuration file. Report which H2 gates remain and end the session. Everything in
this row is downstream of that one field.

What *is* buildable ahead of it, and is worth doing if you find the block: **§0.2's documentation
gate and the naming decision**. Both are pure documentation, neither depends on LoadCoach, and both
are the slow part. Land them, commit, and stop there.

## 0.2 Gate 0 — the documentation does not describe any of this

Same shape as H2's Gate 0, smaller. IdeaPress's `development-plan.md` has no phase for adapters and
its `spec.md` §12 (configuration) describes `[models.stages]` with no adapter axis. **Before any
source changes**, in workspace `docs/` and mirrored byte-identically into `IdeaPress/docs/`:

* **`apps/ideapress/development-plan.md` gains a phase** in the house shape the existing phases use
  — Goal, Prerequisites, Work, Tests, Acceptance criteria, Known risks, Likely failure modes, Gold
  standards, Deferred — with acceptance criteria written as **demonstrable** statements.
* **`apps/ideapress/spec.md`**: §12 (the configuration section — the new keys and their startup
  refusals), the data-ownership section (the new `attempts` columns are IdeaPress's), the error
  table (what an unhonourable pin produces), and the compatibility section (what `1.1` adds and
  what it does not break in a shipped `1.0` config).
* **`apps/ideapress/workflows.md`**: which stages may carry a pin, and what a stage does when its
  pin is refused.
* Wherever the backend-port "adapter" language lives, **disambiguate it once** — §0.3 decision 1.

That is the row's first commit, before a line of source.

## 0.3 The decisions this row must take, and record

Each has a recommendation; take it or overturn it, but **record which and why** in the handoff, and
in an ADR where it outlives the row (CLAUDE.md: a missing architectural decision is a docs defect,
closed with an ADR, not with an implementation). **ADR-0081 is the next free number — confirm**
(`ls docs/adr/ | tail -3`; 0080 is the highest as of 2026-09-05).

1. **What the thing is called, in a codebase where "adapter" already means a backend port.**
   Recommendation: keep `adapter` for the LoRA sense in *configuration and wire* fields, because
   that is LoadCoach's field name and inventing a synonym at the boundary is worse; rename the
   backend-port sense in prose to **"backend"** wherever the two could be read together, and say so
   once in `spec.md`. Do **not** rename the port's Python symbols — that is a large mechanical diff
   with no behavioural content, and this row is not the place. A naming note in the spec is enough.

2. **Whether an adapter pin rides `honour_stage_bindings` or gets its own switch.**
   This is the row's real decision. `honour_stage_bindings` is off by default because a model pin
   surrenders routing (ADR-0040). An adapter pin does not: `routing.md` §10 says *"`adapter` without
   `model` is legal and means 'this adapter, on whichever base can serve it': the compatible bases
   are scored normally and the pin selects among their adapter subjects."* Routing still happens.
   Recommendation: **its own key, defaulting on where a pin is configured**, independent of
   `honour_stage_bindings` — because tying a non-surrendering pin to a flag whose documented meaning
   is "give up routing" would make the configuration lie. State the interaction explicitly for the
   case where both are set: the model pin narrows to one base, the adapter pin selects among that
   base's subjects, and that combination is the one place an adapter pin does surrender routing —
   because the model pin already did. This is an ADR.

3. **What IdeaPress does when LoadCoach refuses the pin.** ADR-0064 rule 4 and `routing.md` §10:
   *"a pin that cannot be honoured is refused by name rather than silently served bare"*. So
   LoadCoach returns a refusal, not a bare-base answer. Recommendation: **the stage fails with the
   refusal surfaced**, exactly as a validation refusal fails today — never a silent fall back to
   the base. An operator who pinned a house-voice LoRA and got the base's prose back has been lied
   to about what produced their document, and IdeaPress's whole provenance story is that this
   cannot happen. Say in the spec's error table which refusal maps to which IdeaPress error, and
   make sure `ADAPTER_NOT_FOUND` and `PROFILE_MISMATCH` both have rows — H1's handoff §4 notes that
   `PROFILE_MISMATCH` is permanent for the request as written, so it belongs with
   `ADAPTER_NOT_FOUND` and not with a retryable failure.

4. **What a pin does in direct/Ollama mode.** The roadmap is already decided here —
   adapter-roadmap §4.4: *"direct/Ollama mode stays adapter-free (recorded scope decision — an
   adapter through the OpenAI-compatible path would evade identity tracking)"*. What is *not*
   decided is whether a configured pin in that mode is ignored or refused. Recommendation:
   **refused at startup**, by the same validator shape as `job_stages` (§0 above): a pin that
   silently does nothing is precisely the silent-no-op that check exists to prevent, and the mode
   is known at startup. Not an ADR — the scope decision is made; this is its enforcement, and it
   belongs in the spec's configuration section.

5. **How much of the subject a persisted attempt names.** [ADR-0080](docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md)
   decided this for LoadCoach: by foreign key **and** by the canonical string written at the time,
   because an explanation is kept for ever and an adapter directory is not. IdeaPress has no
   adapters table and should not grow one — it does not own the registry. Recommendation:
   **string only**, mirroring the existing `model_canonical_id` column, plus the adapter's name and
   artifact digest as their own columns so a query can group by adapter without parsing.
   `baseaicore.AdapterIdentity.canonical_suffix()` (`adapter.py:142`) and
   `canonical_subject_id()` (`subject.py:141`) already produce the string — **use them; do not
   re-implement the format**. Not an ADR; ADR-0080's reasoning transfers and should be cited.

## 0.4 The pins — probably nothing to do, but check rather than assume

`modelrack>=0.5,<0.6` predates `LlamaCppProvider` entirely (Phase 6, `modelrack 0.7.0`). That looks
alarming and is probably fine: **IdeaPress reaches adapters only through LoadCoach's HTTP API**, and
the roadmap keeps its direct/Ollama path adapter-free by decision. If nothing in your diff imports a
ModelRack adapter type, the pin does not move.

`baseaicore>=0.4,<0.5` is the one to check honestly: if you use `AdapterIdentity` or
`canonical_suffix()` for §0.3 decision 5, the floor must become `>=0.4.1,<0.5` — that is where
`AdapterIdentity` arrived — and `>=0.4.2,<0.5` if anything touches `RuntimeProfile.adapters_registered`
(it should not; IdeaPress does not build runtime profiles). **A floor that a needed symbol is not in
is the F3 defect** (`docs/history/F3_HANDOFF.md` finding 4): the code imports and then fails at the
first adapter.

E5's lessons apply if any pin moves: a widened floor **does not move an installed venv** unless the
floor excludes what is installed, `pip-compile` needs `-P` per package to move a satisfied pin, and
the flag is `--no-emit-index-url`, not `--no-index`.

## 0.5 The exit demonstration — this row inherits it, and the row text has not been edited to say so

H2's kickoff §0.5 moved the IdeaPress three-stage demonstration **into this row**, and H2's handoff
§8 records that *"the H3 row has not yet been edited to say so, and it should be when this row
closes"*. **Check whether that edit has landed; if it has not, make it as part of this row's docs
commit** and say so in the handoff.

The demonstration, precisely:

* A real IdeaPress project through **three model-using stages**, each stage pinning a **different**
  adapter on **one** base, against real LoadCoach and a real `llama-server`.
* **Exactly one base load** across the whole project — I16, asserted from ModelRack's process table
  and load timings, not from absence of complaint. H1's `TestWarmBase`
  (`py/ModelRack/tests/live/test_llamacpp_live.py`) is the assertion shape to copy; it proves the
  same property from three witnesses.
* Every attempt row naming the subject that answered it, so the three stages are distinguishable
  after the fact from the database alone.
* **One recorded classification denial** — I19: a confidential-classified adapter meeting a
  remote-tier request produces a queryable rejection.
  [ADR-0079](docs/adr/0079-an-adapter-classification-refusal-is-a-routing-rejection.md) settled
  where it is recorded: **a LoadCoach `routing_candidates` row with reason
  `adapter_classification_conflict`, not a `governance.egress_decision`**. IdeaPress's part is to
  provoke it and to surface the refusal (§0.3 decision 3), not to record it.

Artefacts exist (§0). The base is small (1.5 B, Q8_0) and loads in about 750 ms, so this
demonstration is minutes, not hours.

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb
git -C /home/jpk/ai/suite/IdeaPress status -sb
cd /home/jpk/ai/suite/IdeaPress && source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show baseaicore setspec modelrack | grep -E "^(Name|Version)"
```

Every scratch database, config file, project directory and log goes in the session scratchpad —
**never** the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside the component directory. Nothing at the workspace root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional Commit
  per gate**, every path staged by name — never `git add -A`.
* Docstring-first: define behaviour, write the Google-style docstring including what the function
  *refuses*, write the tests against it, then implement.
* Workspace `docs/` is edited first and mirrored into the component; prove every mirror with `cmp`
  before the commit that carries it.
* Route handlers and CLI command bodies contain no business logic — one service call and a render.
* Name the interpreter and the exact invocation in the gate report (M5C-13).

## 3. Reading list, in this order

1. `docs/history/H2_HANDOFF.md` §7 (what gate E built) and §8 (**what H3 inherits** — read this
   twice; it is the contract).
2. `docs/apps/loadcoach/routing.md` §10 — the override table and the `adapter`-without-`model`
   rule. This is the semantic you are consuming.
3. `docs/adr/0064-adapters-are-selected-through-the-capability-vocabulary.md` rule 4 (a pin that
   cannot be honoured is refused by name) and
   `docs/adr/0065-an-adapter-is-classified-and-local-only.md` (the classification rule I19 trips).
4. `docs/adr/0040-routing-backend-owns-model-choice.md` — the decision §0.3(2) has to sit beside.
5. `docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md` — the
   reasoning §0.3(5) borrows.
6. `docs/roadmap/adapter-roadmap.md` §4.4 (this row's scope) and §7 rows I16, I19.
7. `IdeaPress/src/ideapress/config.py` §`LoadCoachSettings` (`:169`–`:230`) and `StageBindings`
   (`:282`–`:320`) — the code the new keys live beside.
8. `IdeaPress/src/ideapress/infrastructure/db/models.py:267`–`:295` — the `Attempt` row you extend.
9. `docs/history/H1_HANDOFF.2.md` §3–§4 — the artefacts, and the I16 assertion shape.

## 4. The shape of the work — five gates

| Gate | What | Depends on |
|---|---|---|
| **A** | The plan, the spec, the workflows text, and the naming note (§0.2) | nothing |
| **B** | Configuration: the per-stage pin, its validators, its startup refusals | A |
| **C** | The passthrough: the pin reaches LoadCoach as an `adapter` override | B, **H2 gate E** |
| **D** | Provenance: migration `0006`, the subject on every attempt | C |
| **E** | The three-stage demonstration (§0.5) and the release commit | D, artefacts |

Gate boundaries are commit boundaries, so the row can be stopped and resumed. Gates A and B are
buildable even if §0.1 finds H2 unfinished; C onward are not.

## 5. Gate A — the documentation

§0.2, in full, plus the H3 row edit §0.5 asks for. Mirror into `IdeaPress/docs/` and prove with
`cmp`.

**Commit:** `docs(ideapress): per-stage adapter pins and the subject on every attempt (LA2)`.

## 6. Gate B — configuration

* The per-stage adapter pin, in the shape §0.3(2) decides, beside `[models.stages]`.
* A validator refusing a pin on a stage that is not a model-using stage — the `job_stages` shape.
* A validator refusing any pin at all when the backend is direct/Ollama (§0.3(4)).
* The compatibility golden: **a shipped `1.0` configuration file loads to a byte-identical settings
  object**. Assert it; do not argue it.
* Tests: each refusal by its message, and the golden.

**Commit:** `feat(config): a stage may pin an adapter, and a pin that cannot apply is refused`.

## 7. Gate C — the passthrough

* The pin travels as LoadCoach's `adapter` override on the stage's `/generate` request, alongside
  the existing model override where both are configured.
* A refusal comes back as a stage failure with the refusal surfaced (§0.3(3)), never a bare-base
  answer. Both `ADAPTER_NOT_FOUND` and `PROFILE_MISMATCH` map to documented IdeaPress errors.
* The LoadCoach contract tests (`loadcoach-contract` extra) gain the new field, so the shape is
  asserted against the real client and not only against a fake.
* Tests: pinned request carries the field; unpinned request is **byte-identical to `1.0`'s**; each
  refusal fails the stage with its reason recorded.

**Commit:** `feat(inference): a stage's adapter pin travels as LoadCoach's adapter override (A-7)`.

## 8. Gate D — provenance

* Migration **`0006`**: the adapter columns on `attempts`, beside the four model columns, plus the
  canonical subject string (§0.3(5)). A stated rule for existing rows in the migration's docstring —
  they are base subjects; say so.
* Every attempt writes the subject that answered it, taken from LoadCoach's response, never
  inferred from the configuration. What was *asked for* and what *answered* are different facts and
  a pin can be refused between them.
* Tests: a pinned attempt records its adapter; an unpinned one records `NULL` and not an empty
  string; existing rows migrate unchanged.

**Commit:** `feat(persistence): an attempt names the adapter subject that answered it (ADR-0058)`.

## 9. Gate E — the demonstration and the release commit

1. **The live proof** as §0.5 defines it, verbatim into the handoff: three stages, three adapters,
   one base, **one** base load, every attempt naming its subject, and the classification denial
   queryable in LoadCoach.
2. Version to `1.1.0`, `## [Unreleased]` moved, release commit prepared, wheel built into the
   scratchpad and verified in a throwaway venv with the app's own smoke path. **No tag, no publish,
   no push.**

**Commits:** `test(live): three stages, three adapters, one base load`,
`chore(release): ideapress 1.1.0`.

## 10. Exit conditions — all of these, demonstrably

1. The development plan has a phase for this work with demonstrable acceptance criteria; the four
   IdeaPress documents describe adapter pins; workspace `docs/` and the mirror are `cmp`-identical.
2. A stage can pin an adapter in configuration, and a pin naming a gate stage, an unknown stage, or
   any stage in direct/Ollama mode is refused **at startup**, by name.
3. A pinned stage's request carries LoadCoach's `adapter` override; an unpinned stage's request is
   byte-identical to `1.0`'s.
4. A refused pin fails its stage with the refusal surfaced — never a bare-base answer.
5. Every attempt row names the subject that answered it; unpinned attempts are unchanged.
6. **The three-stage demonstration**: one base load across three adapters, plus one recorded
   classification denial (§0.5).
7. A configuration with no pins behaves byte-identically to `36cd3c6` — asserted, not argued.
8. Full gate green; interpreter and exact invocations named; coverage ≥ 85 %.

## 11. Closing duties

1. Full gate; interpreter and exact invocations named (M5C-13).
2. **`H3_HANDOFF.md` at the workspace root**, house shape, copied into `docs/history/`: gate
   results; each §0.3 decision and why; the live evidence verbatim; what H4 and I2 inherit, if
   anything; **and anything this prompt said that turned out not to be true** — that section has
   been the most useful part of the last eight handoffs, so write it even when it is short.
3. Say plainly what is left for the operator: push two repos, tag and publish `ideapress 1.1.0`,
   verify the published wheel.
4. Record any model deviation ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
5. Update the H3 row in `docs/roadmap/outstanding-work.md` to **Done**, in the house form.

## 12. Stop rules

* **Do not start if H2's gate E has not landed** (§0.1). Report and stop.
* **Do not touch LoadCoach, FreeWeight, ModelRack or PromptCadence.** A missing field there is a
  finding for that row, not a diff here.
* **Do not send an adapter anywhere.** ADR-0065: local-only, classified, effective classification
  is `max(caller, adapter)`.
* **Do not let a refused pin degrade to the base.** §0.3(3) is the whole point of the row.
* **Do not add an adapters table to IdeaPress.** It does not own the registry (ADR-0061 rule 3);
  LoadCoach reads the operator's directory.
* **Do not put an adapter on the direct/Ollama path.** Recorded scope decision, adapter-roadmap
  §4.4, and the reason is identity tracking.
* **Do not break a shipped `1.0` configuration file.** The golden in gate B is the guard.
* **Do not weaken `extra="forbid"`**, do not add `/api/v2`, do not weaken `.importlinter`, and do
  not put business logic in a route handler or a CLI body.
* **Do not `git push`, tag or publish.** Never `git add -A`; never overwrite an unversioned
  workspace-root file; never leave a tree dirty at a gate boundary.

## 13. If you finish with capacity left

Read-only, in priority order: (a) whether the stage → task-profile mapping (`spec.md` §206) should
weight adapter-relevant capabilities once H4's evidence exists — a note for LA3, not a change.
(b) Whether the three-stage demonstration is worth keeping as a marked `live` test rather than a
one-off, given the artefacts are now cheap to serve. (c) Whether anything in IdeaPress's prose
still reads ambiguously after §0.3(1)'s naming note.
