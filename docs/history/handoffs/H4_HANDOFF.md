# H4 — FreeWeight 1.1: adapter subjects, the A-2 panel, serving-mode A/B, and LA3

**Row:** H4 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-06.
**Model:** Opus 5 — a deviation from the scheduled Sonnet 5 · high; see §9.
**Ships:** **nothing cut.** `commissioner 0.1.1` is prepared and release-committed.
**`freeweight 1.1.0` is deliberately not cut** — I18 is unproved and §0.1 of this row's kickoff
forbids cutting the release without it. See §3 and §8.
**No push, no push dry-run, no tag, no publish.**

---

## 1. The headline

**Gates A–E are built, green and committed. Gate F ran and produced a finding instead of a pass.
Gate G is half done: Commissioner's release is cut; FreeWeight's is held.**

FreeWeight can now serve GGUF weights through a llama.cpp server it supervises, read an operator's
LoRA directory, enumerate subjects as base × compatible adapter by digest, measure each subject in
its own right under the A-2 panel, and export a `benchmark.evidence_bundle` `1.1` that a consumer
validates with `setspec` alone. All of it was demonstrated live on the reference machine against
the real `llama-server` and the three trained adapters.

**What I18 found is the headline of the second half.** A real `1.1` bundle carrying three subjects'
records was carried to LoadCoach's own documented import path. One record imported and bound; **two
were rejected as duplicates.** ADR-0022 §3's uniqueness key predates the adapter axis, so a base and
every adapter subject on it collapse to one key. That is one step *earlier* than the blocker H2's
handoff predicted, and no registry work moves it.
[ADR-0085](docs/adr/0085-the-evidence-uniqueness-key-carries-the-adapter.md) closes the decision.

What a person can see today:

```
freeweight adapters list                              # the directory, each adapter's base, why not
freeweight adapters show terse --model <base>         # its panel, and what has been measured on it
freeweight run start --model <base> --adapter terse --suite native.instruction_following
freeweight run start --model <base> --serving-mode-ab --suite native.performance
freeweight evidence export                            # 1.1 iff it carries adapter evidence
GET /evidence                                         # subjects grouped under their base
```

## 2. Gate results

**FreeWeight — interpreter: Python 3.14.4** at `/home/jpk/ai/suite/FreeWeight/.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/FreeWeight
.venv/bin/python -m ruff format --check .        # 327 files already formatted
.venv/bin/python -m ruff check .                 # All checks passed!
.venv/bin/python -m mypy src tests               # no issues in 298 source files
.venv/bin/lint-imports                           # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov --cov-report=term
                                                 # 2588 passed, 28 skipped, 28 deselected
                                                 # coverage 88.99 % (floor 85 %)
```

**Commissioner — interpreter: Python 3.13.15** at `/home/jpk/ai/suite/py/Commissioner/.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/py/Commissioner
.venv/bin/python -m ruff format --check .        # 32 files already formatted
.venv/bin/python -m ruff check .                 # All checks passed!
.venv/bin/python -m mypy src tests               # no issues in 22 source files
.venv/bin/lint-imports                           # Contracts: 3 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov
                                                 # 115 passed, 12 skipped, 100 % coverage
```

Run at every gate boundary with `pytest-randomly` in its default random order; no seed-dependent
failure appeared.

## 3. I18 — the evidence, verbatim, both halves

### Half one: FreeWeight measures and exports. **Passes.**

```bash
cd /home/jpk/ai/suite/FreeWeight
FWTEST_LLAMACPP_MODELS=<scratch>/models \
FWTEST_LLAMACPP_ADAPTERS=<scratch>/adapters \
FWTEST_LLAMACPP_BASE=Qwen2.5-1.5B-Instruct.Q8_0 \
.venv/bin/python -m pytest -m live tests/live/test_la3_adapters.py -rs -s -p no:randomly
```

```
subjects enumerated:
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b  confidence=digest
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+pirate@sha256:35bd9f9f99bf  confidence=digest
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+terse@sha256:c582629216c5  confidence=digest
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+verbose@sha256:4af980ac1fb2  confidence=digest

measured per subject:
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b: {'reliability': 1.0}
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+terse@sha256:c582629216c5: {'reliability': 1.0}
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+verbose@sha256:4af980ac1fb2: {'reliability': 1.0}
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+pirate@sha256:35bd9f9f99bf: —

grouped by base:
  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b  (2 adapter subjects)
    (bare base): 1 record(s) from 1 run(s)
    terse: 1 record(s) from 1 run(s)
    verbose: 1 record(s) from 1 run(s)

bundle: 1.1, 2 adapter-bearing + 1 bare record(s)
  terse  +terse@sha256:c582629216c5
  verbose  +verbose@sha256:4af980ac1fb2

2 passed
```

The `pirate` line reading `—` is the assertion, not a gap: the third adapter was deliberately left
unmeasured so that "an unmeasured subject inherits nothing" is tested against a real absence.

### Half two: LoadCoach imports the file. **Fails, and the failure is the finding.**

The file was the only thing that crossed. LoadCoach was configured against the same base and
adapter directories, migrated, and its models refreshed; then its own documented path:

```bash
cd /home/jpk/ai/suite/LoadCoach
LOADCOACH_CONFIG=<scratch>/lc/config.toml .venv/bin/loadcoach evidence import --file <scratch>/la3-bundle.json
```

```
source        freeweight:f9a666d8bfe4c46bd13d17aa8e3e11e73c44b366f95f1f65d64a06cce1361b6b (1.1)
records       3
  imported    1
  updated     0
  bound       1
  unmatched   0
  ambiguous   0
  superseded  0
  rejected    2
    [1] DUPLICATE_RECORD: a second record in this bundle carries the same (canonical_id,
        runtime_profile_hash, machine_fingerprint, capability_id, policy_version); two
        measurements are not merged into one row
    [2] DUPLICATE_RECORD: …
```

```
LOADCOACH_CONFIG=… .venv/bin/loadcoach evidence show
1 of 1 imported records are bound to a discovered model (0 stale, 0 unmatched, 0 ambiguous).

MODEL                                        CAPABILITY                SCORE  CONF  AGE  STATE
llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5 reliability               1.000  0.41    0  bound
```

**What this proves and does not prove.** It proves the file crosses, that a `1.1` bundle is
accepted by a consumer negotiating `1.0` (acceptance is by major), and that **two applications
agree on the bare base's subject with no shared code and no shared database** — the base's record
imported and bound on the first attempt. It does not prove an adapter subject changing a routing
decision, because the two adapter-bearing records never survived to be bound.

**Why, exactly.** LoadCoach's consumer-side uniqueness key is ADR-0022 §3's
`(source_id, canonical_id, runtime_profile_hash, machine_fingerprint, capability_id, policy_version)`.
The `canonical_id` there is the **model's** — the base's — because ADR-0058 deliberately kept the
adapter in its own payload block so a model identity keeps meaning what it always meant. Three
subjects on one base, one capability, one profile, one machine therefore share one key. The
importer refused to merge them, which is exactly the rule ADR-0022 §3 states; the key had gone
stale under it.

**The importer is not buggy and needs no defensive fix.** The decision it was implementing was
missing, and [ADR-0085](docs/adr/0085-the-evidence-uniqueness-key-carries-the-adapter.md) now
supplies it: both keys gain the adapter, nullable, `NULL` meaning the bare base, keyed on the
**artifact digest** rather than the name. FreeWeight's half already shipped in migration `0008`,
which is why the defect surfaced at the consumer and nowhere earlier.

**Two things that mislead, recorded so the next row does not fall for them.**

1. **This is not the binding gap H2's handoff predicted.** That handoff said adapter-bearing
   evidence "will land `unmatched` until gate D teaches the registry adapter subjects". It does not
   reach binding at all. The consumer's row is therefore **two** changes, and the key must come
   first: until it moves, there are no records left to bind. Widening the key alone is progress —
   the records become `unmatched` — and must not be mistaken for the feature working.
2. **There is an accidental near-miss.** An adapter subject measured under
   `adapters_registered = True` beside a base measured with it unset would have different
   `runtime_profile_hash` values and would not collide. That is a coincidence of serving mode, not
   a property of subjects: two adapter subjects under the same serving mode still collide. Leaning
   on the profile hash would conflate exactly the two things ADR-0060 separated.

## 4. The serving-mode overhead, as a number

**About +6 ms on a ~750 ms run — +0.9 %. Not material. It does not trip ADR-0060's revisit
trigger, and the default should not move.**

Measured warm on the reference machine (RTX 5060 Ti, 16 GiB; `llama-server` b10792 CUDA;
`Qwen2.5-1.5B-Instruct.Q8_0`), two discarded warm-ups per arm, four repeats:

| Repeat | Clean | Registered | Overhead |
|---|---|---|---|
| 1 | 756.6 ms | 749.5 ms | **−7.1 ms (−0.9 %)** |
| 2 | 747.5 ms | 751.9 ms | **+4.4 ms (+0.6 %)** |
| 3 | 748.1 ms | 755.0 ms | **+6.9 ms (+0.9 %)** |
| 4 | 746.4 ms | 753.5 ms | **+7.0 ms (+0.9 %)** |

The sign changes between repeats, which is the honest reading: the effect is at or below this
measurement's noise floor. Three of four land at +0.6 to +0.9 %.

**The first draft of this measurement was wrong in two ways, and both are worth recording** because
either would have produced a confident, plausible, wrong number:

* It served **arm A from the adapter-registered server** while recording it as clean — one provider,
  two labels. The fix is a provider per arm; a run that claims serving conditions it did not have is
  precisely what the profile-hash discipline exists to prevent, and it would have been invisible.
* It compared **two cold starts**. Each arm is its own server launch, so the first run pays the
  model load (~750 ms on this base). The uncorrected figure was **−769 ms (−50.4 %)** — an
  "overhead" that was entirely one arm's start-up landing on the other side of the subtraction.

Both are fixed in `tests/live/test_la3_adapters.py::_arm`, which documents them.

## 5. The five decisions, and what was decided

Each is §0.3's numbering.

1. **How FreeWeight reaches a llama.cpp provider — a named registry, or one more `kind`?**
   **Recommendation taken: one more `kind`.** The singular `[provider]` block gains
   `kind = "llamacpp"` plus `model_directory` (required, no default guessed), `state_dir` and
   `server_path`, with `[adapters] directory` beside it. **Recorded as a deliberate divergence from
   LoadCoach**, in `ProviderSettings`'s own docstring so the next reader meets it where the
   difference is: LoadCoach needs a registry because it *routes* and must know which registration a
   candidate came from; FreeWeight measures one machine's models one run at a time and has no pool
   and no scoring. A second provider here is its own row with its own evidence.
   *Confirmed the hard way at I18:* LoadCoach refused `provider.model_directory` in the singular
   block and required `[providers.local]`. The two applications' configurations genuinely differ,
   and both are right for what they do.

2. **What the fixed regression panel contains.** **Recommendation taken, and it needed no ADR**:
   [ADR-0059](docs/adr/0059-adapter-evidence-is-measured-never-inherited.md) §2 had already fixed
   the *policy* (`instruction_following`, `structured_output`, and the base's strongest measured
   capability); this row fixed the *content* in
   [`benchmark-catalog.md` §8.2](docs/apps/freeweight/benchmark-catalog.md), versioned with the
   catalogue, with `REGRESSION_PANEL_VERSION` recorded on every composed panel so two subjects'
   regression numbers are only comparable under the same panel. **Not configurable**, so no ADR was
   needed. A base with no evidence resolves the third row to nothing and the panel says to measure
   the base first, rather than inventing a strongest capability.

3. **When the exported bundle is `1.1` rather than `1.0`.** **Recommendation taken, and it is an
   ADR** — [ADR-0084](docs/adr/0084-a-producer-chooses-a-payload-version-by-content.md). Version by
   **content**: the lowest version that can express the document. A bundle with no adapter-bearing
   record is `1.0` and byte-identical to `1.0.0`'s output;
   `tests/contract/test_bundle_version_by_content.py` reproduces `v1.0.0`'s `evidence_bundle` body
   literally and compares bytes, so the assertion is against that release's code path rather than
   against a re-run of the current one. Always writing `1.1` passes every other test in that file
   and fails this one, which is why it is there. `EMITTED_SCHEMAS` now declares the **ceiling**
   (`1.1` for both), because that is the question a consumer checking compatibility is asking.

4. **What the serving-mode A/B measures, and what it is recorded as.** **Recommendation taken.**
   One run option, two ordinary runs, two `runtime_profile_hash` values, **no new comparison
   mechanism**. `adapters_registered` is deliberately *not* a `[runtime]` key — an operator does not
   choose it, the composition root knows it — and it defaults to unstated, so no existing profile
   hash moved. The number is in §4. **No ADR**, because the measured overhead is not material enough
   to move the default; if a later machine finds otherwise, that is when it becomes one.

5. **Whether FreeWeight persists an adapter registry.** **Recommendation taken: yes, a table**,
   citing [ADR-0080](docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md)
   and needing no ADR of its own. `adapters` is keyed on `artifact_sha256`, a rescan upserts and
   **never deletes**, and `capability_evidence` names the subject twice — `adapter_id` (survives a
   rename) and `subject_canonical_id` (survives the row). The canonical string comes from
   `baseaicore`'s `MeasurementSubject`/`AdapterIdentity` and is **never re-implemented here**,
   including the materialized `canonical_suffix` SetSpec recomputes and refuses to disagree with.
   That check is what I18's half-one result rests on.

**A sixth decision this row had to take that §0.3 did not name:** ADR-0085, above. It was found by
running I18, not by planning it.

## 6. Things this row's own documents said that turned out not to be true

1. **"`setspec>=0.4,<0.7` is already wide — this row does not move FreeWeight's `setspec` pin."**
   True of the ceiling, **wrong about the floor**. `model.adapter_manifest` `1.0` is `setspec`
   0.5.0 and `EvidenceBundleV1_1Fields` is 0.6.0, and this row imports both. A resolver picking 0.4
   would have installed a build with neither and failed at import rather than at configuration. The
   floor moved to `>=0.6,<0.7`.
2. **"As of 2026-09-05, H2 has finished gates A, B and C only."** H2 finished **all** of A–I,
   demonstrated LA2 live and release-committed `loadcoach 1.1.0`. Gates A–E of this row did not
   need it either way; gate F did, and H2's completion was not what unblocked it.
3. **"H2's gate D taught the registry adapter subjects, so I18 can run."** Gate D taught **routing**
   adapter subjects. `capability_evidence` has no adapter axis — H2's own handoff §7 says so — and
   that turned out not to be the operative blocker anyway (§3).
4. **"The first bundle it exports will land `unmatched`."** It lands **rejected**, one step earlier.
5. **The `--no-index` in every `ci.lock` header is not a typed flag.** It is what `pip-tools` emits
   for `--no-emit-index-url`. Passing it literally makes the compile fail; I lost time on that. The
   recompiled headers are byte-identical to the committed ones.
6. **The H4 row had not been edited** since H2 ran, so §0.4's edits were made as part of gate A's
   docs commit, as the prompt allowed for.

## 7. Commits

**FreeWeight** (6): `43f98ca` gate A docs mirror, `6ad0b50` gate B the provider and the directory,
`709ebd6` gate C subjects and migration `0008`, `da539f5` gate D the panel, `cb1600e` gate E the
payload versions, the A/B and the grouping, `cbe59ed` gate F the live journey.
**docs** (3): `9589ca4` gate A, `f199784` ADR-0085, `e2b5273` Commissioner's spec.
**Commissioner** (1): `ad1b248` the release.

Every path staged by name; no `git add -A`. No push, no push dry-run, no tag, no publish. All three
trees are clean.

## 8. For the operator

1. **Push three repos** — `docs` (3 ahead), `FreeWeight` (6 ahead), `py/Commissioner` (1 ahead).
2. **Tag and publish `commissioner 0.1.1`.** It is prepared, gated and verified from its lock in a
   clean Python 3.13.15 venv. The wheel is built at
   `<scratchpad>/dist/commissioner-0.1.1-py3-none-any.whl`.
3. **Do not expect `freeweight 1.1.0` yet.** It is deliberately not cut: `__about__.py` still says
   `1.0.0` and `CHANGELOG.md` still has its `## [Unreleased]` section. §0.1 of this row's kickoff
   says not to cut it with I18 unproved, and I18 is unproved. Everything else in the release is
   done — the release commit is one bump and one changelog move once the consumer's half lands.
4. **The next row is LoadCoach's**, and ADR-0085 specifies it: the consumer's uniqueness key gains
   `adapter_artifact_digest`, then `capability_evidence` gains the adapter axis so the surviving
   records can bind, then I18 runs whole and `freeweight 1.1.0` is cut. `loadcoach 1.1.0` is
   release-committed but unpublished, so that work either rides it or takes a `1.2.0` — the
   operator's call, and H2 decision 4 already held its publish for H3 and H4.
5. **`PromptCadence/pyproject.toml`'s comment is now stale.** It says "Commissioner will need
   widening before PromptCadence can adopt one". Commissioner has been widened; the comment should
   go when PromptCadence is next touched. I left it alone — PromptCadence is out of this row's scope.

**The PromptCadence resolution check (§0.5), done:** with `commissioner 0.1.1` installed from the
locally built wheel, a clean Python 3.13.15 venv resolves

```
Name: setspec        Version: 0.6.0
Name: commissioner   Version: 0.1.1
Name: baseaicore     Version: 0.4.2
Name: promptcadence  Version: 0.9.0b0
```

The widen is real: something actually resolves past 0.5.x. It is against the local wheel rather
than PyPI, because 0.1.1 is not published — repeat it after the publish if you want the PyPI proof.

## 9. Model deviation

**Scheduled: Sonnet 5 · high. Ran: Opus 5.** The session was invoked on Opus 5 and I did not
downgrade. Recorded per `docs/roadmap/model-assignment.md` §3.5.

Reading the row afterwards, the escalation earned itself in two places, both of which the row's own
model note anticipated as "the judgement": the no-inheritance boundary (§5.5 — where a working join
is the failure), and the version-by-content branch (§5.3 — where "always write the newest" passes
every test you would think to write). The third, which nothing anticipated, was reading the I18
rejection as a stale contract rather than as an importer bug and closing it with an ADR instead of
a workaround.

## 10. What LA3's PromptCadence half (§4.5, riding I2) inherits

* **The evidence shape it will weight is settled.** `capability.evidence` `1.1`'s `adapter` block
  carries `name`, `artifact_digest`, `source_digest` and a materialized `canonical_suffix`, and the
  subject string is `<base canonical_id>+<name>@<digest_short>` from `baseaicore`. PromptCadence
  needs no new field and no new `ExecutionIntent` member — LoadCoach returns the subject and
  PromptCadence records it, exactly as §4.5 says.
* **It inherits the blocker, not the feature.** Tier task profiles weighting adapter-relevant
  capabilities does nothing until adapter evidence can bind in LoadCoach. ADR-0085's row is a
  prerequisite for §4.5 having anything to weight.
* **One shape worth knowing:** an adapter subject with no measured evidence ranks *below* a measured
  base, by design (ADR-0081). Until LA3 completes end to end, a tier that wants an adapter still
  needs a pin, which is what `routing.md` §10 already says.

## 11. Left undone, deliberately

* **`freeweight 1.1.0`'s release commit** — §8.3.
* **The `--serving-mode-ab` figure on other hardware.** One machine, one base, one suite. The number
  in §4 is honest about this machine and says nothing about a 70 B model or a different GPU.
* **§15's optional reading (b) and (c)** — whether the regression panel detects forgetting on the
  terse adapter, and whether the comparison grouping survives a base with a dozen subjects. Both are
  worth doing and neither was needed for a gate; see §12.

## 12. Two things worth an early look

* **Whether the regression panel actually detects forgetting.** The three artefacts are here and the
  panel is built, but the LA3 journey used `native.echo` for speed, so the regression suites have
  never been run against a real adapter. `terse` is the likeliest to have lost instruction-following.
  A negative result is worth writing down — it is [risks](docs/apps/freeweight/risks.md) T11's
  revisit trigger either way.
* **The comparison grouping at scale.** `group_by_base` is O(records) and the template renders every
  subject with a `rowspan`. A base with a dozen subjects will render; a hundred will not read well.
  Paging is not built and nothing needs it yet.
