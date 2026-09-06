# H6 — The evidence gate scores what it admits, and the damaged adapter finds something else

**Row:** H6 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-06.
**Model:** Opus 5 · high, as scheduled. No deviation.
**Ships:** two ADRs and the LoadCoach gate change they decide, folded into the unpublished
`loadcoach 1.1.0`; a producer-side defect fix folded into the unpublished `freeweight 1.1.0`; and
the A-2 regression panel measured against a deliberately damaged LoRA.
**No push, no push dry-run, no tag, no publish.**

---

## 1. The headline

The row's two items were expected to be independent. They were not.

**Item 1 went as written.** `require_adapter_evidence` read the raw signal list, so a benchmark
that scoring then excluded still satisfied the one constraint whose purpose is "no benchmark, no
routed selection". It now reads the resolved capability score, and the rejection says which kind of
unmeasured it is. Two ADRs, one for the gate and one for the second defect the row asked to be
decided separately.

**Item 2 found a producer defect neither handoff predicted, and it is the more serious of the
two.** The deliberately damaged LoRA — an adapter that answers *"What is the capital of Australia?"*
with `"This a sun of the solar of the Earth of the density of the Sun"` — scored **0.818 against
the bare base's 0.727**. Better. Eight of its eleven responses were byte-for-byte the base's.

**FreeWeight never sent the adapter to the provider.** `_build_request` did not set
`GenerationRequest.adapter`, so every generation an adapter run made — warm-up, measured call and
interaction turn — ran on the bare base, while the run stored an `adapter_id`, hashed an
adapter-bearing subject into its fingerprint, and exported the numbers as that adapter's evidence.

So row H5's T11 finding — "three adapters, identical numbers, a suite that never moves" — had the
right observation and the wrong diagnosis. With the adapter actually applied, the panel separates a
damaged adapter from an undamaged one on **both** fixed rows, decisively.

## 2. Gate results

**LoadCoach — interpreter: Python 3.14.4** at `/home/jpk/ai/suite/LoadCoach/.venv/bin/python`.

```bash
cd /home/jpk/ai/suite/LoadCoach
.venv/bin/python -m ruff format --check .   # 214 files already formatted
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/python -m mypy src tests          # no issues in 194 source files
.venv/bin/lint-imports                      # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov
# 1016 passed, 4 skipped, 18 deselected — coverage 90.58 % (floor 85 %)
# and after the last docstring edit: 1020 passed, 18 deselected
```

**PostgreSQL, before touching anything migration-adjacent** (`H5_HANDOFF.md` §8.4's standing
instruction), against `postgres:16` in Docker:

```bash
WEIGHTSDB_REQUIRE_POSTGRES=1 \
WEIGHTSDB_POSTGRES_URL=postgresql+psycopg://weightsdb:weightsdb@localhost:5432/weightsdb_test \
  .venv/bin/python -m pytest -m "not live and not performance" tests/integration -q
# 381 passed
```

**FreeWeight — interpreter: Python 3.14.4** at `/home/jpk/ai/suite/FreeWeight/.venv/bin/python`.
Gates in §7.

## 3. Item 1 — the gate, and the two ADRs

### 3.1 What was wrong

`evaluate_constraints` iterated `subject.signals` and admitted the subject when any signal named the
top-weighted capability with source `benchmark` or `production`. `resolve_capability` then re-read
the same list and applied three exclusions the gate never saw — `evidence_unbound` (ADR-0022 §4),
`evidence_foreign_machine` and `evidence_profile_mismatch` (ADR-0017, ADR-0023 §3).

Two questions, both answered correctly, only one of them gating routed selection — and it the weaker
one. Observed live at H5: two adapters whose manifests merely *declared* `reliability` scored
`0.500 declared` and outranked the bare base, whose real measurement was excluded and scored
nothing.

### 3.2 [ADR-0087](../adr/0087-the-evidence-gate-admits-only-a-signal-that-scores.md) — the gate reads the resolved score

`score_subject` already runs before the hard constraints for every candidate, and its breakdown was
already handed to the filter for `min_capability_scores`. The gate reads that same breakdown.
`ConstraintInputs.resolved_scores: Mapping[str, float | None]` became
`resolved_capabilities: Mapping[str, CapabilityScore]` — one mapping, both readers.

**The alternative this rejects is the one the defect invites**: duplicating the three exclusion
predicates inside the constraint filter. That is the defect's own cause written down deliberately —
two implementations of one rule that agree until somebody edits one, and the exclusions have already
grown once.

The rejection keeps its single name (ADR-0064 rule 3 names exactly one) and gains a detail that
says which kind of unmeasured it is:

```text
adapter_unmeasured
  resolved_source: evidence_profile_mismatch
  measured_profile_hash: e06e92b4d4803b3b
  executing_profile_hash: cef17259bb82d8f9
  remedy: freeweight run start --context-size ...
  problem: the only measurement of 'reliability' on this adapter subject does not describe
           this execution (evidence_profile_mismatch); routed selection needs one that does,
           a pin does not
```

"Nobody has benchmarked this" and "the benchmark does not describe this execution" have different
remedies, and the gate had been saying the first when it meant the second.

**The consequence, stated rather than discovered:** move a runtime profile field and an adapter
measured under the old one is unroutable by name until it is re-measured. It does not degrade to a
declared claim and keep routing. Pins are unaffected — the caller already passes
`require_adapter_evidence=False` for a pinned subject.

### 3.3 [ADR-0088](../adr/0088-an-excluded-measurement-falls-back-to-the-prior-it-displaced.md) — the second defect, decided separately

`if excluded is not None: return excluded` sat after the precedence loop and **before** the
parameter band prior. So a subject measured here under a profile that does not apply scored
`absent` — nothing — while a subject nobody had ever measured scored the band prior and won.

The original ordering had a good argument: substituting a guess buries the remedy. **That argument
is about the explanation, and it was implemented as a penalty on the score.** The two come apart:
the excluded result now carries the prior's score and confidence under its **own** source, note,
remedy and measured hash. The explanation reads exactly as it did; only the ranking moves, and only
upward to where an unmeasured sibling already sat.

`low_evidence`, `measured_weight` and ADR-0087's gate all read the *source*, not the number, so none
of them is affected — asserted, not assumed (`test_routing_scoring.py`, and the integration test
that still expects `low_evidence` in the flags).

The stricter alternative — excluded outranking `declared` too — was rejected in the record: it
deepens the asymmetry this closes, taking a subject that scores `0.500` today to `0.0` for the sole
reason that somebody once benchmarked it.

### 3.4 What moved

`domain/routing/constraints.py` (the gate, the detail helper, `resolved_capabilities`),
`domain/routing/scoring.py` (the fallback), `domain/evidence_policy.py` (`EVIDENCE_EXCLUSIONS`, so a
fourth exclusion is honoured everywhere by being added once), `services/routing.py` (one call site).
Ten new unit tests for the gate — it had **none**, only integration coverage.

## 4. Item 2 — the damaged adapter, and the defect it found

### 4.1 The adapter

`~/ai/tools/lora-train/train_damaged.py`, outside the suite as ADR-0061 rule 6 requires. The base's
own answers to 80 questions, distilled with no style prompt, then **reattached to the wrong
questions** (a derangement — no answer keeps its own question) and trained 600 steps at 10× the
learning rate. Fluent, confident, and no longer taking direction: the T11 failure mode in its
purest observable form. It is a valid adapter that loads and serves — a corrupt file would have
tested llama.cpp's error handling instead of the panel.

```text
prompt: What is the capital of Australia?
scale 0.0: Canberra. Australia's capital city is Canberra, which was established in 1908 …
scale 1.0: This a sun of the solar of the Earth of the density of the Sun of the sun. …
```

### 4.2 The first panel run, and why it was wrong

```text
A-2 regression panel v1, Qwen2.5-1.5B-Instruct.Q8_0 vs +damaged:
  instruction_following    base 0.727 (n=11)   damaged 0.818 (n=11)   delta +0.091
  structured_output        base 1.000 (n=3)    damaged 1.000 (n=3)    delta +0.000
1 passed in 7.32s
```

`+0.091`, identical to all three healthy adapters at H5 — from *that*. And 7.32 s, which is not how
long it takes to generate from a model that never stops.

The check that settled it needed no reading: run the same suite twice, once bare and once under
`--adapter damaged`, and compare `samples.response_hash`.

```text
identical response hashes: 8 of 11
```

Eight of eleven byte-for-byte identical. The three that differed were llama-server's own
run-to-run variation. `grep -rn "adapter=" src/freeweight` then confirmed it directly:
`GenerationRequest.adapter` is never set anywhere in FreeWeight.

### 4.3 The fix

`_RunContext` gains `adapter_name`, read back from the run's own `adapter_id` through the
`adapters` table — the row rather than the directory, so a run resumed after a rename asks for the
registration it was created against. It reaches all three generation sites: `_build_request` (the
measured calls), `_warm` (warming on the base and measuring on the adapter is the reload warm-up
exists to avoid), and the interaction caller (a tool-calling conversation half on each is a
measurement of neither).

Beside it, one refusal: a run naming an adapter on a provider that does not declare
`adapter_hot_swap` is now `IncompatibleAdapter` **at creation**, ADR-0058 §5's second half applied
where FreeWeight already refuses an unknown or incompatible adapter. Without it, such a run starts
and produces a wall of identical `CapabilityUnsupported` errors under a subject naming weights
nobody served.

**This is risk T12 from the direction its mitigation does not cover.** T12's two ends are "no
inheritance in any form" here and "the consumer refuses the mis-binding independently" there —
neither can see a producer that measured the base and *called* it the adapter. The record is
internally consistent, names a real adapter, and binds correctly at the consumer.

The general form is worth keeping, because it is now the second time: **a subject field that is
stored, hashed and never sent describes a run that did not happen.** The *runtime profile* was
stored-but-never-sent at an earlier phase and has a test asserting it reaches the wire; the adapter
now has one beside it (`test_runtime_profile.py::TestTheProfileReachesTheProvider`). Two axes of one
subject, the same defect twice.

### 4.4 The panel, with the adapter applied

```text
A-2 regression panel v1, Qwen2.5-1.5B-Instruct.Q8_0, FWTEST_A2_MAX_OUTPUT_TOKENS=512
  subject      instruction_following (n=11)      structured_output (n=3)
  bare base    0.727                             1.000
  +terse       0.636   (-0.091)                  1.000   (0.000)
  +pirate      0.727   ( 0.000)                  1.000   (0.000)
  +verbose     0.909   (+0.182)                  1.000   (0.000)
  +damaged     0.182   (-0.545)                  0.000   (-1.000)
```

**T11's second revisit trigger is closed.** "A regression suite that never moves" was an artefact of
the measurement path: `structured_output`, the suite H5 named as suspect, is the one that moves
furthest here. Both fixed rows earn their GPU time. The three healthy adapters now differ from each
other, which is what three different LoRAs should look like.

Two smaller findings, recorded in `apps/freeweight/risks.md` rather than acted on:

* **The sample sizes resolve gross damage only.** `n=11` separates `0.182` from `0.727` easily and
  would not separate two adapters a few percent apart. `terse`'s `-0.091` is one case in eleven.
* **A damaged adapter is expensive to measure**, because it never emits a stop token: 72 s with
  `max_output_tokens = 512`, roughly forty minutes without. That is T11's *cost* trigger pointing
  the opposite way from the one it anticipated — the panel is cheap on a healthy adapter and
  expensive on exactly the adapter it exists to catch. `FWTEST_A2_MAX_OUTPUT_TOKENS` bounds the live
  test; whether the **product** should cap a regression panel's output is not decided here.

## 5. What this invalidates

**Every adapter-bearing evidence record produced before this row measures the bare base.** That
includes the three-subject `1.1` bundle row H5 carried through integration verification I18.

The plumbing I18 proved is sound and unaffected — the bundle validated, the records bound to their
own subjects, an adapter subject's evidence changed a selected subject, and the unmeasured sibling
was refused by name. All of that is about keys, binding and routing, none of which depends on what
the numbers mean. **The numbers are not adapter measurements**, and the bundle should be re-exported
before anyone reads them as such. `roadmap/adapter-roadmap.md`'s LA3 row is amended to say so.

Nothing needs re-deciding. ADR-0058, ADR-0059 and ADR-0081 are all upheld by the fix rather than
touched by it.

## 6. The interview, and what it decided

Four decisions were put to the operator on 2026-09-06 before any code was written. All four took the
recommendation.

1. **The second defect falls through to the prior, keeping the name** — ADR-0088, over "keep it and
   write down why" and over the stricter "excluded outranks declared too".
2. **One rejection reason, richer detail** — `adapter_unmeasured` keeps its name and its detail
   carries the resolved source, both hashes and the remedy, over adding
   `adapter_evidence_excluded` to a shipped taxonomy.
3. **Train the damaged LoRA on shuffled pairs**, over over-training an existing style and over
   corrupting the GGUF bytes.
4. **Fold into the unpublished `1.1.0`**, both repositories — nothing is published, so a second
   version would record a distinction no user can observe. Same reasoning H5 applied to its own
   fold.

## 7. FreeWeight gate results

```bash
cd /home/jpk/ai/suite/FreeWeight
.venv/bin/python -m ruff format --check .   # 328 files already formatted
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/python -m mypy src tests          # no issues in 299 source files
.venv/bin/lint-imports                      # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q --cov
```

Five integration tests failed on the first run after the fix, and **all five were asserting the
defect**: they measured an adapter subject on `FakeProvider`, which declares `adapter_hot_swap =
False` and had been silently ignoring the adapter. ModelRack leaves that flag off deliberately
(ADR-0062 decision 5 — the fake is where a consumer meets the refusal path), so the tests that want
an adapter *measured* now build a `FakeScript` that declares it, and a new test asserts the refusal
against the default fake. That refusal is the behaviour a user gets, and it had never been
exercised.

## 8. For the operator

1. **Push three repositories** — `docs`, `LoadCoach` (`93063bd` on top of H5's six),
   `FreeWeight`. Nothing is pushed; nothing is tagged.
2. **The two 1.1.0 releases still wait for you**, and both now carry this row's fixes in their
   existing `1.1.0` changelog sections. Tag LoadCoach at `main`'s tip, as H5 §8.2 already said, and
   FreeWeight likewise — this row's commits sit above its `chore(release)`.
3. **Re-export the LA3 evidence bundle** before anyone reads its adapter numbers. §5.
4. **`FreeWeight/requirements/ci.lock` still pins `weightsdb==0.2.0`** — H5 §8.5, unchanged.
5. The damaged adapter is at `~/ai/models/adapters/llm/qwen2.5-1.5b-instruct-damaged.gguf`
   (`sha256:cce6a9276ce3…`), and its trainer at `~/ai/tools/lora-train/train_damaged.py`. Keep both:
   it is the only artefact on this machine that can fail a regression panel on purpose.

## 9. Left undone, deliberately

* **Re-exporting and re-importing the LA3 bundle.** It is the operator's call whether LA3's exit is
  re-demonstrated with real adapter numbers or left as the plumbing proof it is; the row asked for
  neither, and both applications' releases are already prepared.
* **Capping a regression panel's output in the product.** §4.4's second finding. It is a change to
  what the panel *is*, so it belongs in the catalogue behind a decision, not in a row about a gate.
* **Row 3 of the panel against the damaged adapter.** The live test runs rows 1 and 2, which are the
  fixed ones; row 3 resolves per base from its own evidence and is not comparable across subjects.
* **The `low_evidence` floor.** Untouched, and worth knowing that ADR-0088 does not move it: a
  decision made entirely on excluded measurements is still flagged, because the flag reads
  `measured_weight`.
