# Kickoff — H4: FreeWeight 1.1 — adapter subjects, the A-2 panel, serving-mode A/B, and LA3

**Row:** H4 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Sonnet 5 · high**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
Measurement plumbing on an existing engine; panel composition is already specified. The judgement is
in §0.3's four decisions and in making I18 an honest two-application demonstration.
**Repositories:** `/home/jpk/ai/suite/WeightRoom/docs` first (§0.2), then `/home/jpk/ai/suite/FreeWeight` (the
weight), then `/home/jpk/ai/suite/py/Commissioner` (one pin widen and its own release, §0.5).
**Ships:** **`freeweight 1.1.0` and `commissioner 0.1.1` prepared, not published.** Version bumps,
changelog moves and release commits are yours; **`git push`, tags and publishes are the operator's**
(standing instruction of 2026-09-04). Do not run a push dry-run.
**Runs after:** **H2** (all of it — §0.1) and **B5** (done, §0). `outstanding-work` §3 records both.
**Runs before:** nothing. This is LA3's FreeWeight half; PromptCadence's LA3 half is §4.5 and rides
I2.
**Not in this session:** LoadCoach (H2 owns it; I18 *uses* it, unchanged), IdeaPress (H3),
ModelRack, PromptCadence. Two repositories change here and one of them changes by four characters.

---

## 0. Machine facts, verified 2026-09-05 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **FreeWeight `main` is at `96b080f`**, clean, level with `origin`, tagged `v1.0.0`;
  `__about__.py` says `1.0.0` and `freeweight 1.0.0` is on PyPI. **Confirm** `git status -sb` in
  FreeWeight, `docs` and `py/Commissioner` at the start and at the end.
* **B5 is done.** `setspec 0.6.0` ships `EvidenceBundleV1_1Fields`
  (`py/SetSpec/src/setspec/capability/v1.py:474`, beside an untouched `EvidenceBundleFields` at
  `:441`) and `src/setspec/schemas/benchmark.evidence_bundle/1.1.json` beside `1.0.json`. The
  dependency the row names is satisfied; **H2 is the only one left**.
* **FreeWeight cannot serve a LoRA adapter at all today, and says so in a docstring.**
  `infrastructure/providers/factory.py:28`: `SUPPORTED_PROVIDER_KINDS = frozenset({"ollama",
  "fake"})`, whose docstring reads *"`openai_compatible`, `llamacpp` and `vllm` are valid
  `ProviderKind` members but have no adapter wired here yet; naming one is a configuration error
  today, not a silent fallback to Ollama."* The database already permits the kind
  (`infrastructure/db/models.py:34`, migration `0001_initial_schema.py:77`). **This is the row's
  Gate 0** — §0.2. Everything else in H4 measures something FreeWeight currently cannot reach.
* **The `modelrack` pin predates the provider that serves adapters.** `pyproject.toml:37` says
  `modelrack>=0.5,<0.6`; `LlamaCppProvider` arrives in **0.7.0**. `baseaicore>=0.4,<0.5` (`:23`)
  predates `RuntimeProfile.adapters_registered`, which is `0.4.2` and which the serving-mode A/B
  depends on. Both floors move here. **`setspec>=0.4,<0.7` (`:36`) is already wide** — E5's sweep
  did it — so this row does **not** move FreeWeight's `setspec` pin. See §0.4 for what the row text
  gets wrong about this.
* **The evidence writer is pinned to `1.0` in four places, and they are all constants.**
  `services/evidence.py:125` `EVIDENCE_SCHEMA_VERSION = SchemaVersion(1, 0)`; `:129`
  `BUNDLE_SCHEMA_VERSION = SchemaVersion(1, 0)`; `:318` and `:364` import and validate through
  `CapabilityEvidenceOut` — the **bare** name, which per
  [ADR-0068](docs/adr/0068-a-post-freeze-minor-is-a-sibling-class.md) rule 3 permanently means
  `1.0`; and `services/export.py:101` maps `"benchmark.evidence_bundle": "1.0"`. The "import
  change" the row describes is these five lines plus their goldens — small, and easy to do
  *wrongly* (§0.3 decision 3).
* **"Adapter" is already taken in this codebase too, and means a benchmark harness.**
  `spec.md:74` "external adapters", `:499` "external benchmark adapters run as subprocesses",
  `:639` future SWE-bench/LongBench adapters. **Zero LoRA mentions in FreeWeight's documentation.**
  Disambiguate once in prose; do not rename the benchmark sense's symbols.
* **Migrations end at `0007_capability_evidence.py`, so yours is `0008`.**
* **The `--context-size` precedent is exactly the mechanism the A/B needs.**
  `cli/commands/runs.py:176`–`:179`: *"`--context-size` sets the context the model is served at
  (ADR-0023 §3). Without it the … `runtime_profile_hash` … is what makes measuring one model at 8K
  and again at 64K two measurements."* ADR-0074 made `adapters_registered` a real `RuntimeProfile`
  field, so the clean arm and the registered arm **already hash differently**. The A/B is a run
  option, not a new separation mechanism — §0.3 decision 4.
* **The adapter artefacts exist.** Three LoRA GGUFs for `Qwen2.5-1.5B-Instruct.Q8_0` under
  `~/ai/models/adapters/llm/`, digests in `docs/history/handoffs/H1_HANDOFF.2.md` §4; the base is under
  `~/ai/models/llm/` and loads in about 750 ms. I18 is runnable in minutes.
* **Python: check FreeWeight's own venv and name it** (M5C-13). E5 ran its clean-venv verification
  on 3.14.4. FreeWeight's coverage floor is **85 %** (application).
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to the
  operator.

## 0.1 The block — check this at minute one

**H4's exit needs LoadCoach to bind adapter-bearing evidence to an adapter subject, and today it
binds to nothing.** H2's handoff §8 is explicit: *"H4 … inherits the fact that adapter-bearing
evidence currently binds to nothing: the first bundle it exports will land `unmatched` until gate D
teaches the registry adapter subjects. That is deliberate and safe, but H4's exit demonstration must
run after gate D or it will show no adapter evidence scoring anything."*

That rule 0 was added on purpose — without it the first adapter-bearing bundle would have bound to
the **base's** registry row and raised the score of weights nobody measured (ADR-0058 §4). It is a
guard, not a gap.

As of 2026-09-05, **H2 has finished gates A, B and C only.**

```bash
git -C /home/jpk/ai/suite/LoadCoach log --oneline -6
grep -rn 'adapter' /home/jpk/ai/suite/LoadCoach/src/loadcoach/services/evidence*.py | head
ls /home/jpk/ai/suite/LoadCoach/src/loadcoach/infrastructure/db/migrations/versions/
pip index versions loadcoach modelrack
```

**Gates A through E of this row do not need H2** — they are FreeWeight measuring things, and
FreeWeight shares no code and no database with LoadCoach. **Gate F (I18) does.** If H2's gate D has
not landed, build A–E, land them, and leave I18 as a named, scripted operator step with the exact
command in the handoff. **Do not cut `1.1.0` with I18 unproved**, and do not fake the import half by
reaching into LoadCoach's database — "no shared code or database" is the assertion I18 exists to
make.

## 0.2 Gate 0 — FreeWeight cannot reach an adapter, and its documents do not mention one

Two gaps, one commit each, both before any measurement code.

**(a) The provider.** `SUPPORTED_PROVIDER_KINDS` must gain `llamacpp`, and `ProviderSettings`
(`config.py:293`) must carry what `LlamaCppProvider` needs — the model directory, the state
directory, the server path — none of which the current singular block has, because Ollama needs
none of them. §0.3 decision 1 is how far to take this.

**(b) The documents.** In workspace `docs/` and mirrored byte-identically into `FreeWeight/docs/`:

* **`apps/freeweight/development-plan.md` gains a phase** in the house shape — Goal, Prerequisites,
  Work, Tests, Acceptance criteria, Known risks, Likely failure modes, Gold standards, Deferred —
  with acceptance criteria written as **demonstrable** statements.
* **`apps/freeweight/spec.md`**: the `[adapters]` configuration group and the llama.cpp provider
  settings; subject enumeration; the `--adapter` run option; what `1.1` adds to the evidence and
  bundle payloads and what it does not break; the data-ownership statement for the new tables (the
  adapter *directory* is the operator's, the tables are FreeWeight's); the naming note (§0).
* **`apps/freeweight/benchmark-catalog.md`**: the A-2 panel — declared capabilities, the **fixed
  regression panel**, performance. §0.3 decision 2 makes this a content decision, and the catalogue
  is where content decisions live.
* **`apps/freeweight/risks.md`**: forgetting. A-2's revisit trigger is measured forgetting data;
  say what would change the panel.

That is the row's first two commits, before a line of measurement code.

## 0.3 The decisions this row must take, and record

Each has a recommendation; take it or overturn it, but **record which and why** in the handoff, and
in an ADR where it outlives the row. **ADR-0081 is the next free number — confirm** (`ls docs/adr/ |
tail -3`; 0080 is the highest as of 2026-09-05). If H3 runs first it may have taken 0081.

1. **How FreeWeight reaches a llama.cpp provider — a named registry, or one more `kind`?**
   H2 built LoadCoach's `[providers.<name>]` registry with per-registration capabilities, remote
   flags and a tagged model pool ([ADR-0077](docs/adr/0077-a-named-provider-block-and-the-singular-block-are-one-registry.md)),
   and copying it here would be the obvious move. Recommendation: **do not copy it.** LoadCoach
   needs a registry because it *routes* — it scores candidates across providers and must know which
   registration each came from. FreeWeight measures one machine's models one run at a time; it has
   no pool and no scoring. Extend the **singular** `[provider]` block with `kind = "llamacpp"` and
   the three paths it needs, and add `[adapters] directory` beside it. If a second provider is ever
   needed here, that is its own row with its own evidence. **Record this as a deliberate divergence
   from LoadCoach**, so the next reader does not file it as drift.

2. **What the fixed regression panel contains.** A-2 and
   [ADR-0059](docs/adr/0059-adapter-evidence-is-measured-never-inherited.md) settle the *policy* —
   a new adapter subject has no evidence, and its panel is declared capabilities + a fixed
   regression panel + performance — but not the *content*. The regression panel exists to catch
   catastrophic forgetting: a house-voice LoRA that has lost arithmetic, or instruction-following,
   or the ability to stop. Recommendation: a small, fixed, cheap set drawn from the existing native
   suites, **named in `benchmark-catalog.md` and versioned with the catalogue**, so that "the
   regression panel" means one thing across every subject and two adapters' regression numbers are
   comparable. Do not make it configurable — a per-deployment panel is not a regression panel. Not
   an ADR if the catalogue carries it; an ADR if you make it configurable, because that overturns
   the comparability A-2 assumes.

3. **When the exported bundle is `1.1` rather than `1.0`.** ADR-0068 rule 5: the bundle nests the
   frozen `capability.evidence` `1.0` shape by reference and gains the adapter axis only through
   its own minor. So both versions exist and both are writable. Recommendation: **version by
   content** — a bundle carrying no adapter-bearing evidence is written at `1.0` and is
   **byte-identical to what `1.0.0` wrote**; a bundle carrying any adapter-bearing record is
   written at `1.1`. The alternative, always writing `1.1`, forces every existing consumer to move
   for a field most of them will never see, which is exactly what the sibling-class mechanism was
   built to avoid. Assert the byte-identity as a golden, do not argue it. **This is an ADR**: it is
   a rule about how this application chooses a payload version, and the next payload minor will
   want the same answer.

4. **What the serving-mode A/B measures, and what it is recorded as.** A-3 wants the
   clean-vs-adapter-registered serving overhead measured rather than assumed, "once per base +
   profile". ADR-0074 already gives the two arms different `profile_hash` values, because
   `adapters_registered` is a real `RuntimeProfile` field — so they are two ordinary measurements of
   one base, separable for ever, and **no new comparison mechanism is needed**. Recommendation: a
   run option that runs the same suite twice, once with `adapters_registered=False` and once
   `True`, and records two ordinary runs; the *comparison* is the existing comparison UI grouping by
   profile. Say plainly in the handoff what the overhead measured on the reference machine, in
   numbers — A-3's revisit trigger is *"the measured serving-mode overhead is material on reference
   hardware — flip the default"*, and nobody can act on that trigger without the number. Not an ADR
   unless the number is material enough to move the default, in which case it is one.

5. **Whether FreeWeight persists an adapter registry.** It must enumerate subjects (base ×
   compatible adapters) and key evidence on them. Recommendation: **yes, a table**, because
   evidence is keyed on the subject and evidence outlives the directory — the same reasoning
   [ADR-0080](docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md)
   applied in LoadCoach. Use `baseaicore`'s `AdapterIdentity.canonical_suffix()` (`adapter.py:142`)
   and `canonical_subject_id()` (`subject.py:141`) for the string; **do not re-implement the
   format**, because I18's whole claim is that two applications agree on a subject with no shared
   code. Not an ADR; cite ADR-0080.

## 0.4 What this row's own text gets wrong, and what it therefore does not carry

The H4 row was written before H2 ran, and H2 took two of its items. **Check whether the row has been
edited; if not, edit it as part of this row's docs commit** and say so in the handoff.

* **LoadCoach's `setspec` pin move — done at H2**, not here (`docs/history/handoffs/H2_HANDOFF.md` §4).
* **The `CapabilityEvidenceV1_1Out`/`In` adoption — done at H2, on the *import* side only.**
  This is the one to read carefully. H2 moved LoadCoach's reader to the `1.1` model so its pin
  could move. **FreeWeight's writer is untouched and is still this row's work** (§0, the four
  constants). The row's phrase "an import change" describes LoadCoach's half and reads, in this
  repository, as though it were already done. It is not.
* **FreeWeight's own `setspec` pin needs nothing** — E5 widened it to `>=0.4,<0.7` on 2026-09-04.
* **What the row still carries, unchanged:** `[adapters] directory`, subject enumeration, the
  `--adapter` flag, the A-2 panel policy, serving-mode A/B, evidence export with the `1.1` fields,
  the comparison UI grouped by base, I18, and **Commissioner's widen** (§0.5).

## 0.5 Commissioner — four characters, its own release

`py/Commissioner/pyproject.toml:28` pins `setspec>=0.5,<0.6`. Since F2 that has held PromptCadence's
resolved `setspec` at 0.5.x even though PromptCadence's own range admits 0.6 — the same shape as the
`mirrorwall<0.5` cap E5 spent a whole row removing, and harmless only while nothing in PromptCadence
consumes a 0.6 payload. **This row is where all the 0.6 movement happens, so the widen lands here**,
as its own `commissioner 0.1.1` release: a second repository and a second publish inside a row
otherwise scoped to FreeWeight, accepted deliberately as the cost of keeping the 0.6 movement
together.

Commissioner adopts no payload in doing so — it owns the Python form of `governance.egress_decision`
`1.0` and that is unchanged. This is a range widen, a lock recompile and a gate, exactly the shape
MirrorWall's was. Its `docs/packages/commissioner/spec.md` §56 states the range deliberately and
moves with it.

Then **re-resolve PromptCadence and confirm with `pip show` that it reaches `setspec` 0.6.0**. The
widen is only real if something actually resolves past 0.5.x — E5's finding (2) is that a widened
pin does not move an installed venv and looks exactly like success when it does not.

## 1. Setup

```bash
git -C /home/jpk/ai/suite/WeightRoom/docs status -sb
git -C /home/jpk/ai/suite/FreeWeight status -sb
git -C /home/jpk/ai/suite/py/Commissioner status -sb
cd /home/jpk/ai/suite/FreeWeight && source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show baseaicore setspec modelrack | grep -E "^(Name|Version)"
ls ~/ai/models/adapters/llm/ ~/ai/models/llm/Qwen2.5-1.5B-Instruct.Q8_0.gguf
```

Every scratch database, config file, model directory, exported bundle and log goes in the session
scratchpad — **never** the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside the component directory. Nothing at the workspace root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional Commit
  per gate**, every path staged by name — never `git add -A`.
* Docstring-first: define behaviour, write the Google-style docstring including what the function
  *refuses*, write the tests against it, then implement.
* Workspace `docs/` is edited first and mirrored into the component; prove every mirror with `cmp`
  before the commit that carries it.
* `UNSUPPORTED` is not zero, and a measurement this machine cannot provide raises rather than
  coercing (ADR-0016). This row is measurement code; that rule is not decorative here.
* Name the interpreter and the exact invocation in the gate report (M5C-13).

## 3. Reading list, in this order

1. `docs/roadmap/adapter-roadmap.md` §4.3 (this row's scope, in one paragraph) and §3's LA3 row
   (the exit), then §7 row I18.
2. `docs/history/handoffs/H2_HANDOFF.md` §4 (what H4 loses and keeps) and §8 (**the `bind_identity` rule 0
   fact** — the reason §0.1 exists).
3. `docs/adr/0059-adapter-evidence-is-measured-never-inherited.md` (A-2) and
   `docs/adr/0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md` (A-3), then
   `docs/adr/0074-adapter-enabled-serving-is-a-runtime-profile-field.md`, which closed A-3's open
   mechanism and is what makes §0.3(4) cheap.
4. `docs/adr/0068-a-post-freeze-minor-is-a-sibling-class.md` rules 3 and 5 — the two rules §0.3(3)
   turns on.
5. `docs/adr/0058-the-execution-subject-gains-an-adapter-axis.md` §4 — why adapter evidence must
   not bind to a base.
6. `FreeWeight/src/freeweight/services/evidence.py:100`–`:135` and `:300`–`:410` — the constants
   and the writer you are moving.
7. `FreeWeight/src/freeweight/infrastructure/providers/factory.py` — twenty lines, and the whole of
   Gate 0(a).
8. `FreeWeight/src/freeweight/cli/commands/runs.py:120`–`:210` — `run start`, and the
   `--context-size` precedent §0.3(4) copies.
9. `docs/history/handoffs/E5_HANDOFF.md` and `docs/history/handoffs/F2_HANDOFF.md` §7 — the pin-and-lock lessons, all
   five of them, before you touch a lock file.
10. `docs/history/handoffs/H1_HANDOFF.2.md` §3–§5 — the artefacts, and the CUDA-graphs default your runs
    will inherit.

## 4. The shape of the work — seven gates

| Gate | What | Depends on |
|---|---|---|
| **A** | Gate 0(b): the plan, the spec, the catalogue, the risks (§0.2) | nothing |
| **B** | Gate 0(a): the llama.cpp provider, `[adapters] directory`, pins | A |
| **C** | Subject enumeration, migration `0008`, `--adapter` | B |
| **D** | The A-2 panel policy and the regression panel | C |
| **E** | Serving-mode A/B; evidence and bundle at `1.1`; comparison UI | D |
| **F** | **I18**, live, two applications | E, **H2 gate D** |
| **G** | Commissioner's widen and its release; FreeWeight's release commit | F |

Gate boundaries are commit boundaries, so the row can be stopped and resumed. A–E do not need H2.

## 5. Gate A — the documents

§0.2(b), in full, plus the row edits §0.4 asks for. Mirror into `FreeWeight/docs/`, prove with
`cmp`.

**Commit:** `docs(freeweight): adapter subjects, the A-2 panel and serving-mode A/B (LA3)`.

## 6. Gate B — the provider FreeWeight has never had

* `llamacpp` joins `SUPPORTED_PROVIDER_KINDS`; `build_provider` constructs a `LlamaCppProvider` with
  the directories from configuration. ModelRack reads no environment variable and no configuration
  file — **the application names every path** (ModelRack spec §12).
* `[adapters] directory`, opt-in, empty by default. **FreeWeight reads the directory and validates
  each manifest through SetSpec's `model.adapter_manifest` 1.0**, then converts to ModelRack's
  `AdapterRegistration` **in the application** — ADR-0061 rule 3, and the same division H2 built in
  LoadCoach. Do not import LoadCoach's code; do not read its database. Two applications, one
  contract.
* Note the shape H1 settled: **`register_adapters()` takes the complete set** and a name absent
  from it is retired at the next idle (`docs/history/handoffs/H1_HANDOFF.2.md` §6). A rescan restates the
  directory whole.
* Pins: `modelrack>=0.7,<0.8`, `baseaicore>=0.4.2,<0.5`. `setspec` unchanged (§0). Recompile
  `requirements/ci.lock` with `-P` per moved package and `--no-emit-index-url`; verify in a clean
  venv installed `--require-hashes`, because this repository's own venv carries editable installs
  and is the wrong oracle (E5 finding 5).
* Tests: a `llamacpp` configuration constructs; a missing directory refuses at startup by name; an
  `ollama` configuration is byte-identical to `1.0.0`'s.

**Commit:** `feat(providers): FreeWeight can serve GGUF models and register adapters (ADR-0062)`.

## 7. Gate C — subjects

* Migration **`0008`**: the adapter table and the subject columns, per §0.3(5). A stated rule for
  existing rows in the migration's docstring — they are base subjects.
* Enumeration: base × compatible adapters, compatibility decided by ModelRack's digest verification,
  never by name alone. A `NAME_ONLY` confidence is flagged everywhere the subject surfaces.
* `freeweight run start --model … --adapter <name>`, refusing an unknown or incompatible name by
  name, with the registered set in the message.
* Tests: enumeration over the three real artefacts; an adapter for a different base is not
  enumerated; a run records its subject.

**Commit:** `feat(runs): a run measures an adapter subject, not only a base (ADR-0058)`.

## 8. Gate D — the panel

* A-2's composition: declared capabilities + the fixed regression panel + performance, with the
  panel's content named in the catalogue (§0.3(2)).
* **Evidence is never inherited.** A new subject starts with none; nothing about the base
  contributes to the adapter's score. Assert it — the failure mode is a join that quietly pulls the
  base's rows.
* `user.*` goal benchmarks work against adapter subjects unchanged (adapter-roadmap §4.3): a
  house-voice LoRA scored by a calibrated house-voice goal is the intended pairing. Prove it runs;
  do not special-case it.
* Tests: a fresh subject's panel is exactly the policy's; its evidence is empty until measured;
  a goal suite scores a subject.

**Commit:** `feat(evidence): an adapter subject's panel is measured, never inherited (ADR-0059)`.

## 9. Gate E — the A/B, the payloads, and the UI

* Serving-mode A/B per §0.3(4): one option, two runs, two profile hashes, no new mechanism.
  **Record the measured overhead in the handoff as a number.**
* The five `1.0` constants move per §0.3(3): `1.1` when the payload carries adapter-bearing
  evidence, `1.0` byte-identical otherwise, asserted by golden against `96b080f`'s output.
* The comparison UI groups subjects under their base and shows each one's evidence source.
  Server-rendered, progressive enhancement, no SPA (ADR-0020).
* Tests: the two arms are separable by `profile_hash`; a no-adapter export is byte-identical; an
  adapter-bearing export validates against `benchmark.evidence_bundle` `1.1`'s schema.

**Commit:** `feat(evidence): an adapter-bearing bundle exports at 1.1, and a bare one does not move`.

## 10. Gate F — I18, and it is a two-application demonstration

The exit is not "FreeWeight exports a file". It is: **an imported bundle visibly changes which
adapter a task profile selects, with the explanation showing per-capability adapter evidence beside
the bare base, and an unmeasured adapter filtered with its named rejection** — with **no shared code
and no shared database**.

So the demonstration is, in order, and captured verbatim into the handoff:

1. FreeWeight measures two of the three adapters on the base, and leaves the third unmeasured.
2. FreeWeight exports one `benchmark.evidence_bundle` `1.1` file to the scratchpad.
3. **LoadCoach imports that file** through its own documented path — the file is the only thing
   that crosses. Show the explanation before and after.
4. A task profile's selected subject **changes**, and the explanation names the per-capability
   adapter evidence beside the base's.
5. The unmeasured third adapter is filtered by `require_adapter_evidence` with its named rejection,
   and **is still pinnable** — `routing.md` §10 says a pin is not routed selection.

If H2's gate D has not landed, §0.1: script it, name it as an operator step, do not cut the release.

**Commit:** `test(live): an imported bundle changes which adapter a profile selects (I18)`.

## 11. Gate G — Commissioner, and the release commits

1. Commissioner: `setspec>=0.5,<0.7`, spec §56 moves with it, lock recompiled, full gate, version to
   `0.1.1`, changelog moved, release commit. **No tag, no publish, no push.**
2. Re-resolve PromptCadence; **confirm with `pip show` that it reaches `setspec` 0.6.0** (§0.5).
3. FreeWeight: version to `1.1.0`, `## [Unreleased]` moved, release commit, wheel built into the
   scratchpad and verified in a throwaway venv against the published `modelrack 0.7.0` and
   `baseaicore 0.4.2`. **No tag, no publish, no push.**

**Commits:** `chore(release): commissioner 0.1.1`, `chore(release): freeweight 1.1.0`.

## 12. Exit conditions — all of these, demonstrably

1. The development plan has a phase with demonstrable acceptance criteria; spec, catalogue and risks
   describe adapter subjects; workspace `docs/` and the mirror are `cmp`-identical.
2. FreeWeight constructs a `LlamaCppProvider` from configuration and registers adapters from an
   operator's directory, validating each manifest through SetSpec.
3. Subjects enumerate as base × compatible adapters, by digest; `--adapter` selects one and refuses
   an incompatible name by name.
4. A fresh subject's panel is declared capabilities + regression panel + performance, and its
   evidence is empty until measured — no inheritance, asserted.
5. The serving-mode A/B produces two separable measurements of one base, and the overhead is
   reported as a number.
6. An adapter-bearing export is `benchmark.evidence_bundle` `1.1` and validates; an export with no
   adapter evidence is **byte-identical** to `1.0.0`'s.
7. **I18**: an imported bundle changes a profile's selected subject in LoadCoach's explanation, with
   no shared code or database; an unmeasured adapter is filtered by name and remains pinnable.
8. `commissioner 0.1.1` prepared with `setspec>=0.5,<0.7`, and PromptCadence confirmed resolving to
   `setspec` 0.6.0.
9. A configuration with no adapters behaves byte-identically to `96b080f` — asserted, not argued.
10. Full gate green in both repositories; interpreter and exact invocations named; coverage ≥ 85 %.

## 13. Closing duties

1. Full gate in FreeWeight and in Commissioner; interpreter and exact invocations named (M5C-13).
2. **`H4_HANDOFF.md` at the workspace root**, house shape, copied into `docs/history/`: gate
   results; each §0.3 decision and why; **the serving-mode overhead as a number**, with whether it
   trips A-3's revisit trigger; I18's evidence verbatim, both halves; what LA3's PromptCadence half
   (§4.5, riding I2) inherits; **and anything this prompt said that turned out not to be true**.
3. Say plainly what is left for the operator: push three repos, tag and publish `commissioner 0.1.1`
   then `freeweight 1.1.0`, verify both published wheels.
4. Record any model deviation ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
5. Update the H4 row in `docs/roadmap/outstanding-work.md` to **Done**, in the house form, and
   record that **LA3's FreeWeight half is complete** in the adapter-roadmap's §3 table.

## 14. Stop rules

* **Do not run I18 before H2's gate D** (§0.1), and do not simulate its import half.
* **Do not read LoadCoach's database, and do not import LoadCoach.** I18's claim is that a file is
  the only thing that crosses; a convenience import destroys the demonstration and the boundary.
* **Do not let adapter evidence inherit from a base.** A-2, ADR-0059, and ADR-0058 §4 — this is the
  single failure this row exists to prevent, and it looks like a working join.
* **Do not copy LoadCoach's provider registry** unless §0.3(1) is overturned with a reason.
* **Do not always write `1.1`** unless §0.3(3) is overturned; a shipped `1.0` consumer must not be
  forced to move.
* **Do not send an adapter anywhere.** ADR-0065: local-only, classified.
* **Do not weaken `extra="forbid"`**, do not add `/api/v2`, do not weaken `.importlinter`, do not
  put business logic in a route handler or a CLI body, and do not let `UNSUPPORTED` become `0`.
* **Do not trust this repository's venv as the oracle for a pin** — E5 finding 5; a clean venv from
  the recompiled lock is the proof.
* **Do not `git push`, tag or publish.** Never `git add -A`; never overwrite an unversioned
  workspace-root file; never leave a tree dirty at a gate boundary.

## 15. If you finish with capacity left

Read-only, in priority order: (a) what PromptCadence's LA3 half (§4.5 — tiers weighting
adapter-relevant capabilities) needs from this row's evidence shape, as a note for I2. (b) Whether
the regression panel actually detects forgetting on the three artefacts here — the terse adapter is
the likeliest to have lost something, and a negative result is worth writing down. (c) Whether the
comparison UI's grouping survives a base with a dozen subjects, or needs paging before someone
finds out the hard way.
