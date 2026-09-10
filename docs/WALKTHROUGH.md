# Walkthrough — the whole suite in a week

An ordered route through all fourteen components: what to read, what to run, what to look at. It
supersedes [LEARNING_PLAN.md](LEARNING_PLAN.md) and [CODE_REVIEW_PLAN.md](CODE_REVIEW_PLAN.md)
**for this purpose only** — both were written over nine components, and neither is edited here.

Paths are relative to `~/ai/suite/`. Verified 2026-09-07: every venv, interpreter, verb, demo and
version below was executed or inspected on that date. Nothing needs a GPU, Ollama or the network
unless a step says so. First, keep the applications off the operator's real databases:

```bash
export XDG_DATA_HOME=~/suite-walkthrough/data XDG_CONFIG_HOME=~/suite-walkthrough/config \
       XDG_STATE_HOME=~/suite-walkthrough/state && mkdir -p ~/suite-walkthrough/{data,config,state}
```

## 1. Orientation — half a day

Each document answers a question the one before it raises, so read them in this order.

1. **`CLAUDE.md`** (workspace root, 15 min) — the map: fourteen components, versions, dependency
   direction, working-tree rules.
2. **`architecture/executive-summary.md`** (30 min) — what the suite is for; its
   independent-deployment table is the shape of the whole thing.
3. **`architecture/master-architecture.md`** (2 h, in full) — the design. §1 the vocabulary every
   repo spells identically, §2 the layering, §6 the cross-application wire, §11 what it forbids.
4. **`architecture/dependency-and-boundary-rules.md`** (30 min) — every `.importlinter` you will
   meet, and why a package that "needs" an application type is a design error.
5. **`architecture/graceful-degradation.md`** (45 min) — the discipline behind every `doctor` below.
6. **`adr/README.md`** — the prose at the top only, not the 115 records: the format, the
   supersede-never-edit rule, and why a decision without a "revisit when" cannot be reopened.

Then **ten ADRs**, and only ten — the ones whose absence makes the code unreadable:

| ADR | Why |
|---|---|
| [0001](adr/0001-application-and-package-separation.md) | Why fourteen repositories, not one |
| [0003](adr/0003-sync-vs-async-strategy.md) | Async only at the edge; explains every `web/` |
| [0008](adr/0008-canonical-model-identity.md), [0024](adr/0024-canonical-id-and-model-references.md) | `provider/name@sha256:…`; descriptor ≠ identity |
| [0010](adr/0010-queue-implementation.md) | A leased database queue, and no broker anywhere |
| [0012](adr/0012-prompt-storage-format.md) | Prompts are versioned records, never literals |
| [0016](adr/0016-unavailable-is-not-zero.md) | The decision most visible in the code |
| [0018](adr/0018-external-benchmark-isolation.md) | The isolation ladder that ends in refusal |
| [0030](adr/0030-model-cost-and-pricing.md) | Cost re-derived from usage + hash, never stored |
| [0045](adr/0045-promptcadence-reaches-models-only-through-loadcoach.md) | PromptCadence reaches a model only through LoadCoach |
| [0070](adr/0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md) | The one carve-out from 0016 — read it straight after |

7. **`roadmap/outstanding-work.md` §1** (45 min) — one row per model session, with its status and,
   once run, a `history/handoffs/<ROW>_HANDOFF.md`. A1–L6 are done; **M1 is the only row left**. Skim §3,
   "which orderings are load-bearing" — the honest record of what depended on what.
8. **The two audits of 2026-09-07**, at the workspace root: `ADR_GAP_REVIEW.md` (102 records, 21
   findings — three are contradictions a reader would act on and get wrong) and `M9_AUDIT.md` (the
   delivery checklist across fourteen repos: "not met, but the shortfall is almost entirely in the
   last mile"). No re-audit exists yet.

**The rule that makes the handoffs matter:** read a row's handoff before touching the code it built.
Specs say what was intended; handoffs say what was decided while building.

## 2. The components, bottom-up — three days

Each repo has its own venv, and the gate is identical in all fourteen:

```bash
cd ~/ai/suite/<repo> && .venv/bin/ruff format --check . && .venv/bin/ruff check . \
  && .venv/bin/mypy src tests && .venv/bin/lint-imports && .venv/bin/pytest -q
```

`pytest` already excludes `live` and `performance` via `addopts`; below, `pytest -q` stands for the
whole gate. Interpreters differ by repo and are named because a gate report must name them. Each
component's purpose is §1 of its `spec.md`, under `packages/<name>/` or `apps/<name>/`; its handoffs
are in `history/handoffs/`, and they hold the decisions the spec does not. The application rows carry the
loopback port instead of a layer.

| Layer | Component | Version / port | Python | Handoffs — what each settled |
|---|---|---|---|---|
| 1 | BaseAiCore | 0.4.2 | 3.13.15 | none; it predates the arcs |
| 2 | SetSpec | 0.6.0 | 3.13.15 | B1 the egress payload · B5 the bundle that nests adapter evidence |
| 3 | ModelRack | 0.7.1 | 3.13.15 | C5 the ADR-0070 usage rule · D3 `LlamaCppProvider` · F3 adapters · H1 + H1.2 cancellation, leaks, LA1's exit |
| 3 | SweatMeter | 0.4.0 | 3.14.4 | none |
| 3 | WeightsDB | 0.2.1 | 3.14.4 | M4 |
| 3 | MirrorWall | 0.2.2 | 3.14.4 | E5 the `setspec` widen that unblocked three applications |
| 3 | LoadLedger | 0.3.0 | 3.13.15 | B2 ceilings and verdicts · C3 the SQL half · F4 a balance naming no run · K4 the pricing reader |
| 3 | CutCtx | 0.1.0 | 3.13.15 | C1 the invariants · E1 the policy set |
| 3 | ToolYard | 0.1.1 | 3.13.15 | C2 the refusal discipline · **D1 the sandbox** — read before touching containment · E2 the built-in tools |
| 3 | Commissioner | 0.1.1 | 3.13.15 | B3 the policy · E3 the ledger |
| app | FreeWeight 1.1.2 (PyPI 1.1.1) | 8765 | 3.14.4 | H4 adapter subjects, LA3 · H5 · **H6** a damaged LoRA exposed that every earlier adapter number had measured the bare base · L3 · L5 |
| app | LoadCoach 1.1.5 (PyPI 1.1.4) | 8766 | 3.14.4 | C6 · E6 · G2 the tool wire · H2 + H2.2 the 1.1/LA2 work · H5 · H6 · I3 · I8_I9 |
| app | IdeaPress 1.3.2 (PyPI 1.3.1) | 8767 | 3.13.15 | H3 adapter pins · J1 LoadLedger + Commissioner · J2 CutCtx · K3 · K4 |
| app | PromptCadence 1.3.2 (PyPI 1.3.1) | 8768 | 3.13.15 | B4 · C4 · D2 + D2.2 · E4 · F1 budget · F2 egress · G1 planning · G3 · I1 compaction and the explanation · **I2** the 1.0 verification, read its verdict · I4 · I5 · I8_I9 |

Run the gates in order, with the four demos and the one thing worth seeing in each package. Every
demo and one-liner below was run verbatim on 2026-09-07 and the comment says what it printed; the
gates themselves are yours to run.

```bash
cd ~/ai/suite/py/BaseAiCore && .venv/bin/pytest -q && .venv/bin/python ~/ai/suite/demo_baseaicore.py
.venv/bin/python -c "from baseaicore import UNSUPPORTED; print(UNSUPPORTED); float(UNSUPPORTED)"
# → prints `unsupported`, then a TypeError telling you to test with is_supported() and exclude it
#   from aggregates rather than coerce it. ADR-0016, in one line.

cd ~/ai/suite/py/SetSpec && .venv/bin/pytest -q && .venv/bin/python ~/ai/suite/demo_setspec.py
.venv/bin/python -c "import setspec; print(len(setspec.PUBLISHED_SCHEMAS), setspec.DRAFT_SCHEMAS)"
# → ten published payloads, DRAFT_SCHEMAS empty: nothing crossing a boundary is still reshapeable.

cd ~/ai/suite/py/ModelRack && .venv/bin/pytest -q && .venv/bin/python ~/ai/suite/demo_modelrack.py
# → then read py/ModelRack/docs/providers.md: the capability matrix generated from each adapter's
#   own capabilities(), with a test that fails when the document and the adapters disagree.

cd ~/ai/suite/py/SweatMeter && .venv/bin/pytest -q && .venv/bin/python ~/ai/suite/demo_sweatmeter.py
.venv/bin/python -c "from sweatmeter import TelemetryCollector as T; \
  print(T().machine_profile().machine_fingerprint)"
# → matches architecture/performance-results.md §1 exactly. That is reproducibility, demonstrated.

cd ~/ai/suite/py/WeightsDB && .venv/bin/pytest -q && .venv/bin/python -c "
from weightsdb import redact_url
print(redact_url('postgresql+psycopg://alice:hunter2@db:5432/loadcoach'))"
# → alice:***@db — the password reaches no log, health payload or doctor line.

cd ~/ai/suite/py/MirrorWall && .venv/bin/pytest -q && .venv/bin/python -c "
from mirrorwall import measurement; from baseaicore import UNSUPPORTED
print(measurement(UNSUPPORTED))"
# → an em dash with a title and an aria-label reading 'not measurable in this environment'.
#   ADR-0016 carried all the way to the pixel.

cd ~/ai/suite/py/LoadLedger && .venv/bin/pytest -q && .venv/bin/python docs/quickstart.py
# → the only runnable quickstart among the packages. Read three lines of it slowly: `—` and not
#   $0.00 after a local step, 'at least' and not a bare figure after a partly priced remote one,
#   and a history whose stored facts are usage and a hash. ADR-0030, demonstrated.

cd ~/ai/suite/py/CutCtx && .venv/bin/pytest -q && .venv/bin/python -c "
from cutctx import *
t = Transcript(tuple(TranscriptTurn(turn_id=f't{i}', role=Role.USER, content='x'*40,
                                    token_estimate=100) for i in range(8)))
p = DropOldestPolicy().decide(t, CompactionBudget(max_tokens=500, protected_recent_turns=2))
print(p.tokens_before, '->', p.tokens_after_estimate,
      sum(a.action.value == 'drop' for a in p.actions), 'dropped')"
# → '800 -> 500 3 dropped', and nothing executed. Policies plan; applications execute.

cd ~/ai/suite/py/ToolYard && .venv/bin/pytest -q && .venv/bin/python -c "
from toolyard import TieredSandbox; print(TieredSandbox().report())"
# → a TierReport naming the rung this machine actually gets, the runtime path and the reason in
#   prose: here `container` via docker, podman reported not installed. ADR-0111's whole subject.

cd ~/ai/suite/py/Commissioner && .venv/bin/pytest -q && .venv/bin/python -c "
from datetime import datetime, UTC; from baseaicore import DataClassification
from commissioner import *
p = OrderedClassificationPolicy(clock=lambda: datetime(2026, 9, 7, tzinfo=UTC))
print(p.evaluate(EgressRequest(run_id='r1', source_ref='s1',
    data_classification=DataClassification.INTERNAL,
    target=EgressTarget(name='remote-x', remote=True))).reason)"
# → 'no_ceiling_declared', verdict denied. A remote target that has not declared what it may
#   receive is refused, never assumed public.
```

### The four applications

Each ships a standalone journey. The **documented** one needs Ollama; the **fake-provider**
substitution changes the provider and nothing else.

**FreeWeight** — measure. Gate `cd ~/ai/suite/FreeWeight && .venv/bin/pytest -q`; documented journey
`FreeWeight/docs/quickstart.md:38-44` (Ollama). Fake-provider version — `provider.kind` takes
`ollama | llamacpp | fake` (`configuration.md:56`), and every verb is `Mode: local`, no server:

```bash
export FREEWEIGHT_PROVIDER__KIND=fake
.venv/bin/freeweight db upgrade && .venv/bin/freeweight doctor
.venv/bin/freeweight models refresh && .venv/bin/freeweight benchmarks list
.venv/bin/freeweight run start --model <ref from `models list`> --suite native.echo
.venv/bin/freeweight results show <run-id>
```

**See:** `freeweight serve`, then the results page — the provenance block carries model digest,
runtime profile, machine fingerprint and benchmark version, and every headline metric drills to its
raw sample in two clicks.

**LoadCoach** — manage. Gate `cd ~/ai/suite/LoadCoach && .venv/bin/pytest -q`; documented journey
`LoadCoach/docs/quickstart.md:20-46`. Fake-provider version — the first `doctor` was run here and
reports `PROVIDER_UNAVAILABLE: fake (fake) reachable`:

```bash
export LOADCOACH_PROVIDER__KIND=fake
.venv/bin/loadcoach doctor       # one ! MIGRATION_REQUIRED before the first serve
.venv/bin/loadcoach serve &      # migrates, imports twenty task profiles, discovers models
.venv/bin/loadcoach doctor       # now all ✓
.venv/bin/loadcoach generate --task general.chat --prompt 'Name three uses for a paperclip.'
.venv/bin/loadcoach route explain --task code.review
```

**See:** with no evidence imported, `route explain` says `evidence: none` and flags `low_evidence`
— routing on declared capabilities and priors, labelled as exactly that, is the degraded state
working rather than failing.

**IdeaPress** — apply. Gate `cd ~/ai/suite/IdeaPress && .venv/bin/pytest -q`; documented journey
`IdeaPress/docs/quickstart.md:50-88`, which **needs Ollama and two models** (`qwen3.5:9b-q8_0`,
`gemma4:12b`). `inference.mode` is `ollama | loadcoach | openai_compatible` — there is no fake mode
in the shipped configuration, so without Ollama the equivalent is the fake-backend journey in the
test suite: `.venv/bin/pytest -q tests/integration/test_draft_to_commit.py`, 9 tests, drafted to
committed.

**See:** `ideapress plan show <project-id>` — every requirement paired with the span of your own
brief it came from, so a requirement the material cannot support is visible before a word is drafted.

**PromptCadence** — harness. Gate `cd ~/ai/suite/PromptCadence && .venv/bin/pytest -q`; documented
journey `PromptCadence/docs/quickstart.md:34-49`. It needs a running LoadCoach — use the
fake-provider one from the previous step, and nothing else changes:

```bash
export PROMPTCADENCE_LOADCOACH__BASE_URL=http://127.0.0.1:8766
.venv/bin/promptcadence doctor && .venv/bin/promptcadence tiers check   # exit 4 if a profile is absent
.venv/bin/promptcadence serve &
.venv/bin/promptcadence run "summarize the files in ./notes" --bypass-planning --follow
```

With no LoadCoach at all, the same loop runs in-process against the fake LoadCoach:
`.venv/bin/pytest -q tests/e2e/test_bypass_journey.py` — 7 tests, no server, no GPU.

**See:** `promptcadence trajectory explain <id>` — every model, tier, tool call, debit, egress
verdict, deviation and approval in one record. Then the console on `http://127.0.0.1:8768/`.

## 3. Composition — one day

Three compositions, all over HTTP with SetSpec payloads, none reading another's database.

**FreeWeight → LoadCoach.** With both serving, diff `route explain` before and after the import: the
`low_evidence` flag clears and the explanation names what carried the score and how old it is. A
FreeWeight elsewhere on the network must be named in `evidence.allowed_source_hosts` first (ADR-0026
§3). Demonstrated end to end in `history/handoffs/H5_HANDOFF.md`.

```bash
.venv/bin/loadcoach evidence import --url http://127.0.0.1:8765
.venv/bin/loadcoach evidence show && .venv/bin/loadcoach route explain --task code.review
```

**IdeaPress → LoadCoach.** The interesting half is what IdeaPress does when LoadCoach goes away
mid-stage — the repo's largest test file, `tests/integration/test_loadcoach_degradation.py`.
Handoffs: H3 for the adapter override, J1 for the Commissioner gate that fails closed.

```bash
export IDEAPRESS_INFERENCE__MODE=loadcoach \
       IDEAPRESS_INFERENCE__LOADCOACH__BASE_URL=http://127.0.0.1:8766
.venv/bin/ideapress backend list && .venv/bin/ideapress backend test loadcoach
```

**PromptCadence → LoadCoach** (every model call, ADR-0045). `promptcadence tiers check` above *is*
the composition test: the five harness profiles (`tools.agent.local_fast`, `local_large`,
`remote_cheap`, `remote_frontier`, `tools.plan`) must exist in the running LoadCoach. The live proof
on real models is `history/handoffs/G2_HANDOFF.md`; the 1.0 verdict is `history/handoffs/I2_HANDOFF.md`.

## 4. What is deliberately not done

None of this is a defect. Do not file it as one.

* **Row M1** — IdeaPress's `research` stage does not yet run its tools under ToolYard. The only open
  row in `roadmap/outstanding-work.md` §1; decided 2026-09-07, not yet built.
* **Podman is untested live** ([ADR-0111](adr/0111-the-container-rung-is-proved-on-docker-and-podman-is-not-an-exit-condition.md)).
  `TieredSandbox` prefers podman when both exist, but no podman host has ever been available here.
  The container rung is proved on docker, the podman branch by unit tests over a faked runtime;
  deliberately removed as an M11 exit condition.
* **The ten packages stay `0.x`** ([ADR-0113](adr/0113-packages-stay-0x-at-m9-and-1-0-is-earned-per-package.md)).
  A `1.0` is earned per package against stated criteria, never granted by a milestone. The four
  applications are `1.x`; the packages beneath them are not, by decision.
* **M9 is not declared.** The shortfall `M9_AUDIT.md` finds is in the last mile, not the
  engineering; the declaration is a human step.
* **Twelve test files are stubs** carrying `TODO: implement per docs/…` — among them
  `FreeWeight/tests/e2e/test_full_journeys.py:1` and
  `IdeaPress/tests/e2e/test_full_project_journey.py:1`, which collect zero tests. What they name is
  covered elsewhere (`test_run_journey.py`, 28 tests; `test_draft_to_commit.py`, 9). In no row.

## 5. Closing checklist

* [ ] **Fourteen gates green**, each on its own venv, with the interpreter in your note: BaseAiCore,
      SetSpec, ModelRack, LoadLedger, CutCtx, ToolYard, Commissioner, IdeaPress, PromptCadence
      (3.13.15) · SweatMeter, WeightsDB, MirrorWall, FreeWeight, LoadCoach (3.14.4).
* [ ] **Four demos**, from the workspace root against their own venvs — each exits 0 and ends with a
      line naming what it did *not* need: `py/BaseAiCore/.venv/bin/python demo_baseaicore.py` ·
      `py/SetSpec/.venv/bin/python demo_setspec.py` · `py/ModelRack/.venv/bin/python
      demo_modelrack.py` · `py/SweatMeter/.venv/bin/python demo_sweatmeter.py`
* [ ] **Four journeys**: FreeWeight's benchmark run on the fake provider; LoadCoach's `doctor` then a
      fake-provider `generate`; IdeaPress's draft-to-commit; PromptCadence's `run --bypass-planning`
      against that fake-provider LoadCoach. All four ran exactly as written above on 2026-09-08
      (isolated `XDG_*` roots, no GPU, no Ollama): `native.echo` completed 5/5 on `fake-model`,
      `route explain` reported `evidence: none` + `low_evidence`, and the bypass trajectory reached
      `completed` in nine events.
* [ ] **Three compositions**: evidence import changes a routing explanation; IdeaPress reaches a
      model through LoadCoach; `promptcadence tiers check` passes against it.
* [ ] **The co-install from PyPI in a clean venv** — verified 2026-09-08 at `freeweight 1.1.2`,
      `loadcoach 1.1.6`, `ideapress 1.3.3`, `promptcadence 1.3.2`, and the compatibility matrix
      (docs repository, run `34187778093`) proved both ends of every declared range the same day.

      ```bash
      python -m venv /tmp/suite-coinstall
      /tmp/suite-coinstall/bin/pip install freeweight loadcoach ideapress promptcadence
      for a in freeweight loadcoach ideapress promptcadence; do /tmp/suite-coinstall/bin/$a --version
      done
      ```
* [ ] **`git status --short` clean in every repo you opened**, at the end as well as the start.
