# H5 — LoadCoach 1.1 + FreeWeight 1.1: LA3's consumer half, and the two releases it cuts

**Row:** H5 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-06.
**Model:** Opus 5 · high, as scheduled. No deviation.
**Ships:** **`loadcoach 1.1.0` and `freeweight 1.1.0` prepared, gated, wheel-verified — not tagged,
not pushed, not published.**
**No push, no push dry-run, no tag, no publish.**

---

## 1. The headline

**All seven gates are built, green and committed, and I18 passes whole.** An adapter subject's
evidence now crosses from FreeWeight to LoadCoach as a file, binds to the subject it was measured
on, and changes a routing decision — with the sibling nobody measured refused by name in the same
decision.

What a person can see today:

```
loadcoach evidence import --file <a FreeWeight 1.1 bundle>   # records 3, rejected 0
loadcoach evidence show                                      # three SUBJECTS, not one model thrice
loadcoach route explain --task <profile weighting the measured capability>
                                                             # +verbose selected, benchmark signal
                                                             # +pirate rejected adapter_unmeasured
```

**Running it found two defects neither handoff predicted, and both were silent.** They are §4.

## 2. Gate results

**LoadCoach — interpreter: Python 3.14.4** at `/home/jpk/ai/suite/LoadCoach/.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/LoadCoach
.venv/bin/python -m ruff format --check .        # 214 files already formatted
.venv/bin/python -m ruff check .                 # All checks passed!
.venv/bin/python -m mypy src tests               # no issues in 194 source files
.venv/bin/lint-imports                           # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov --cov-report=term
                                                 # 1007 passed, 18 deselected
                                                 # coverage 90.56 % (floor 85 %)
WEIGHTSDB_REQUIRE_POSTGRES=1 .venv/bin/python -m pytest tests/integration -q
                                                 # 380 passed  (postgres:16 in Docker)
```

**FreeWeight — interpreter: Python 3.14.4** at `/home/jpk/ai/suite/FreeWeight/.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/FreeWeight
.venv/bin/python -m ruff format --check .        # 328 files already formatted
.venv/bin/python -m ruff check .                 # All checks passed!
.venv/bin/python -m mypy src tests               # no issues in 299 source files
.venv/bin/lint-imports                           # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov --cov-report=term
                                                 # 2589 passed, 28 skipped, 29 deselected
                                                 # coverage 88.99 % (floor 85 %)
```

Run at every gate boundary under `pytest-randomly`'s default random order; no seed-dependent
failure appeared. `-p no:randomly` was used only to read live-test output in order.

**Wheels, built into the scratchpad and verified in throwaway venvs** resolving the published
siblings (`baseaicore 0.4.2`, `setspec 0.6.0`, `modelrack 0.7.1`, `weightsdb 0.2.1`,
`mirrorwall 0.2.2`, `sweatmeter 0.4.0`):

```
loadcoach 1.1.0 (api v1)
freeweight 1.1.0 (api v1, schemas … capability.evidence 1.1, benchmark.evidence_bundle 1.1, …)
```

## 3. I18, verbatim, both halves

### Half one: FreeWeight measures and exports

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
  …@sha256:5926a692b27b: {'reliability': 1.0}
  …+terse@sha256:c582629216c5: {'reliability': 1.0}
  …+verbose@sha256:4af980ac1fb2: {'reliability': 1.0}
  …+pirate@sha256:35bd9f9f99bf: —

bundle: 1.1, 2 adapter-bearing + 1 bare record(s)

serving-mode A/B on this base (warm, 2 discarded warm-ups per arm):
  clean         750.3 ms   registered    753.7 ms   overhead  +3.4 ms (+0.5 %)

2 passed
```

Every record now carries `runtime_profile_hash = cef17259bb82d8f9` — see §4.1 for why that number
is the whole story of this row's second half.

### Half two: LoadCoach imports the file. **Passes.**

The file was the only thing that crossed. No `freeweight` import, no cross-read of either database.

```bash
cd /home/jpk/ai/suite/LoadCoach
LOADCOACH_CONFIG=<scratch>/lc/config.toml .venv/bin/loadcoach evidence import \
    --file <scratch>/la3-bundle.json
```

```
source        freeweight:f9a666d8bfe4c46bd13d17aa8e3e11e73c44b366f95f1f65d64a06cce1361b6b (1.1)
records       3
  imported    3
  updated     0
  bound       1
  unmatched   2
  ambiguous   0
  superseded  0
  rejected    0
```

`rejected 0` is the key change; `unmatched 2` here is correct and temporary — the `adapters` table
is empty until a directory scan writes it, and a record naming an adapter this operator does not
yet hold is retained rather than rejected. The scan binds them, with no re-import:

```
LOADCOACH_CONFIG=… .venv/bin/loadcoach route explain --task la3.reliability
```

```
decision  01M1VSFMN7871JHHPF4QKTGW2S  (8 ms)
selected  llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+verbose@sha256:4af980ac1fb2
  adapter               verbose (confidential, evidence: declared)
  runtime_profile_hash  cef17259bb82d8f9
  final_score           0.4082
flags     assumed_context, breaker_state_unavailable
evidence  freeweight
  #1 llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+verbose@sha256:4af980ac1fb2
      reliability              w=1.0    1.000    benchmark
  #2 llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+terse@sha256:c582629216c5
      reliability              w=1.0    1.000    benchmark
  #3 llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b
      reliability              w=1.0    1.000    benchmark
  rejected llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+pirate@sha256:35bd9f9f99bf: adapter_unmeasured
```

```
LOADCOACH_CONFIG=… .venv/bin/loadcoach evidence show
```

```
CAPABILITY                 MODELS SCORING   BEST  STALE
reliability                     3       3  1.000      0

SUBJECT                                                                  CAPABILITY   SCORE  CONF  AGE  STATE
llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b                  reliability  1.000  0.41    0  bound
llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+terse@sha256:c58 reliability  1.000  0.41    0  bound
llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b+verbose@sha256:4 reliability  1.000  0.41    0  bound
```

**Both outcomes, together, are the exit.** `+verbose` is selected *because* of imported evidence,
with `benchmark` as the signal's source; `+pirate` — measured nowhere — is refused by name in the
same run, after two siblings' evidence landed. Both halves are now regression tests:
`FreeWeight/tests/live/test_la3_adapters.py` and `LoadCoach/tests/live/test_la3_evidence.py`.

## 4. Two defects I18 found, both silent

### 4.1 FreeWeight recorded a runtime profile that never happened (ADR-0074 rule 3)

**The first import bound all three records and routed on none of them.** Every capability read
`absent — evidence_profile_mismatch`. FreeWeight had measured under `runtime_profile_hash
e06e92b4d4803b3b`; LoadCoach resolved `cef17259bb82d8f9`. The two profiles were identical in every
stored column. The difference was `RuntimeProfile.adapters_registered`: FreeWeight recorded `None`,
LoadCoach resolved `True`.

`freeweight run start` passed `adapters_registered=None` **unconditionally** — including on runs it
had just handed a llama.cpp server three LoRAs to launch with. `None` means "a provider with no
concept of adapters", and ADR-0074 rule 3 puts the field on the constructing application precisely
because it is the actor that supplies the registration set. Only `--serving-mode-ab` ever stated it.

Why nothing caught it: **`None` disagrees with nothing and is always served**, so ModelRack's
refusal (rule 3's second half) never fired, the run succeeded, and the evidence exported cleanly
under a hash describing a server that did not exist. A consumer resolving the honest `True` then
excluded every one of those measurements — correctly, by ADR-0023, and silently.

Fixed at the shared point: `freeweight.services.adapters.serving_mode(provider, entries)` derives
it from the provider's `adapter_hot_swap` and the directory's available entries, and both
`run start` and the LA3 live test use it. **No shipped hash moves** — only `llamacpp` declares
`adapter_hot_swap`, so Ollama and fake runs still resolve `None` and hash exactly as they did at
`1.0.0`, and `llamacpp` is new in this release.

### 4.2 LoadCoach never re-bound evidence when an adapter arrived

`sync_adapters` wrote the `adapters` table and stopped. Re-binding ran only inside
`discover_models`, so a record naming an adapter the operator had *just reviewed* stayed
`unmatched` until something unrelated happened to the **model** registry. ADR-0022 §4 requires
binding on the next discovery pass with no re-import, and a directory scan **is** discovery for the
subject's second axis. `rebind_evidence_in` now runs in `sync_adapters`' own transaction.

## 5. The §0.3 decisions, and why

1. **The key column's spelling — followed ADR-0080 rule 5, and wrote `ADR-0086`.**
   `adapter_artifact_digest` is `NOT NULL` with `''` for the bare base. The prompt's reasoning was
   confirmed empirically before the ADR was written: two identical upserts with a `NULL` in the
   conflict target produce **two rows on SQLite and two on PostgreSQL**. The nullable spelling
   would have made every re-import of a bare-base record insert a second row, silently, for ever —
   worse than the defect this row exists to close, in the same table. ADR-0085 gains an
   `Amended by:` line; ADR-0022 §3's amendment block gains a second note.
2. **What an adapter-bearing record binds to — the digest, and both axes or neither.** A nullable
   `adapter_id` FK beside the non-null key column, as ADR-0080's shape. Both sides carry the
   `sha256:` prefix (`sha256_of` normalizes, and `AdapterIdentityFields.artifact_digest` requires
   it), **checked before writing the comparison** — a prefix mismatch here is a silent no-match.
3. **A record whose adapter is absent — `unmatched`, retained, bound on a later scan with no
   re-import.** Not rejected. Binding reads **every** adapter row rather than only the available
   ones: an artifact temporarily missing makes an adapter unroutable, and unbinding its evidence on
   that account would make a measurement flap as an operator moved a file.
4. **`match_state` gains no value.** The three existing states describe every case.
5. **The routing read is keyed `(model_id, adapter_key)`** — the same subject key shape
   `reliability_stats` uses, so one application does not carry two spellings of one concept.
   `adapter_key` is the adapter's **row id** there and `''` for the bare base.
6. **An adapter subject sees nothing of its base.** Asserted as an absence on real data:
   `pirate` is measured nowhere, and stays unmeasured and unroutable after `terse`'s and
   `verbose`'s evidence lands — in the live journey and in
   `tests/integration/test_adapter_evidence_routing.py`.

**Note on decisions 1 and 5:** `capability_evidence.adapter_artifact_digest` carries the **digest**
while `reliability_stats.adapter_key` carries the **row id**. Same idea, different spelling, for a
stated reason: reliability is computed from local attempts so the adapter row always exists;
evidence arrives from another machine and may name an adapter that has never been here.

## 6. The regression panel, against a real adapter (T11)

`FreeWeight/tests/live/test_a2_regression_panel.py`, on the reference machine:

| Subject | `instruction_following` | `structured_output` |
|---|---|---|
| bare base | 0.727 (n=11) | 1.000 (n=3) |
| `+terse` | 0.818 (n=11) | 1.000 (n=3) |
| `+pirate` | 0.818 (n=11) | 1.000 (n=3) |
| `+verbose` | 0.818 (n=11) | 1.000 (n=3) |

**No forgetting detected, and the weaker half of that is the finding.** All three adapters moved
`instruction_following` by exactly `+0.091` — one case in eleven — and none moved
`structured_output`. Three adapters trained for three different voices scoring identically is not a
clean bill of health; it says the panel resolves nothing finer than gross forgetting at these
sample sizes. The adapters are certainly live: prompted identically through the same provider, the
base answers plainly, `pirate` answers in pirate, `terse` in one line and `verbose` at length.

Recorded in `docs/apps/freeweight/risks.md` against T11's **second** revisit trigger ("a regression
suite that never moves"), in its quietest form, and deliberately not acted on: settling it needs a
deliberately damaged adapter, and this machine has none.

## 7. What this prompt said that turned out not to be true

1. **"ADR-0085 decision 2 … says nullable" — and it is wrong for the consumer, exactly as §0.1
   predicted.** That part held. What §0.1 did *not* say is that the empirical check is cheap: two
   upserts against a scratch table settle it in seconds, on both dialects, and it is worth doing
   before writing an ADR that overturns another one.
2. **"The row says six follow-on commits; there are seven."** There were **twelve** by the time the
   1.1.0 section was folded, because this row's own five joined them. All are in the section.
3. **"Gate C … the binding re-evaluation that already runs on every discovery pass must also pick
   up an adapter that appears later."** It did not run on the pass that matters. Adapter discovery
   is `sync_adapters`, not `discover_models`, and nothing re-bound there — §4.2.
4. **"Gate E … re-export from FreeWeight."** The re-export alone was not enough: the bundle it
   produced was unroutable for a reason inside FreeWeight (§4.1). The row's scope had to widen by
   one small fix in the producer, under an ADR that already required it.
5. **"`loadcoach 1.1.0` … `CHANGELOG.md` carries a `## [1.1.0] — 2026-09-05` section **and** an
   `## [Unreleased]` section above it."** True, and the fold also had to merge two `### Added` and
   two `### Fixed` headings into one of each, and move the LA2 narrative below the LA3 one.
6. **A demonstration the shipped task profiles cannot make.** Every one of the twenty shipped
   profiles sets `min_context_tokens`, and none tops on `reliability` — the only capability LA3
   measures. I18 therefore needs a task profile written for it (one is in the live test), and the
   `min_context_tokens` it leaves unset is load-bearing: setting it makes LoadCoach configure a
   context, which changes the runtime profile hash, which excludes the evidence.

## 8. For the operator

1. **Push four repositories** — `docs` (2 ahead), `LoadCoach` (6 ahead), `FreeWeight` (3 ahead),
   `PromptCadence` (1 ahead). Nothing is pushed; nothing is tagged.
2. **Tag and publish `loadcoach 1.1.0`, then `freeweight 1.1.0`** — in that order, because
   FreeWeight's release notes point at a LoadCoach behaviour. Both are release-committed, gated and
   wheel-verified; approve the `pypi` environment exactly once per repository.
3. **Verify both published wheels** in clean venvs, as at E1/E2.
4. **LoadCoach's `main` was red on PostgreSQL before this row and is green now** — the whole
   integration suite, including both new migrations, runs against `postgres:16`. Keep running
   `WEIGHTSDB_REQUIRE_POSTGRES=1` before pushing anything that touches a migration.
5. **`FreeWeight/requirements/ci.lock` still pins `weightsdb==0.2.0`** while `0.2.1` is published.
   No dependency moved in this row so the lock was not recompiled; it resolves and CI is green.
   Worth a recompile at the next FreeWeight row that touches `pyproject.toml`.

## 9. What LA3's PromptCadence half (§4.5, riding I2) inherits

* **It is unblocked, and the thing it was waiting for now works.** Adapter evidence binds to its
  subject and scores that subject's candidate. A tier task profile weighting an adapter-relevant
  capability will now select a measured adapter subject, with the explanation naming the evidence.
* **`require_adapter_evidence` is still the gate, and it is stricter than it looks.** It admits a
  subject with a `benchmark` or `production` signal for the top-weighted capability. A tier that
  weights a capability FreeWeight has not measured on that adapter gets `adapter_unmeasured`,
  correctly — so the tier profiles and the measured capabilities have to be chosen together.
* **One sharp edge worth knowing.** The gate reads `subject.signals`, which includes an evidence
  signal that *scoring* may later exclude (foreign machine, mismatched runtime profile). So a
  subject can pass `require_adapter_evidence` and still score on `declared` alone. That is not
  wrong — the gate asks "has this subject ever been measured", the scorer asks "does this
  measurement apply here" — but it means a tier can select an adapter whose evidence did not
  actually move the decision. Observed during this row's first (mismatched-profile) run.
* **Profile hashes have to agree end to end.** §4.1 is the general lesson: two applications resolve
  the same subject and the same capability, and one field of the runtime profile silently
  disqualifies the whole measurement. PromptCadence resolves profiles through LoadCoach, so it
  inherits LoadCoach's answer — but the same class of mismatch is what to look for first if a tier
  mysteriously ignores evidence that exists.

## 10. Left undone, deliberately

* **`FreeWeight/requirements/ci.lock`'s `weightsdb` pin** — §8.5.
* **A deliberately damaged adapter** — the only thing that would settle T11's second trigger (§6).
* **Paging for the comparison grouping.** Capped at 12 with an honest "and N more"; the row asked
  for a bound, not paging.
* **`loadcoach adapters sync`.** Adapter rows are written by `route` and by the server's bootstrap;
  there is no explicit sync command, so an operator who imports evidence and then reviews a
  manifest has to run *something* before the binding happens. Not a defect — the next route does
  it — but a one-line command would make the sequence obvious.
