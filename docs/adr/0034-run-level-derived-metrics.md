# ADR-0034 — Run-level derived metrics: the second benchmark seam

**Status:** Accepted (2026-08-28)
**Amends:** [Benchmark Catalog §5.1](../apps/freeweight/benchmark-catalog.md), [FreeWeight spec §7](../apps/freeweight/spec.md).
**Related:** [ADR-0033](0033-benchmark-interaction-protocol.md) (the *first* seam — how a benchmark drives a conversation), [ADR-0016](0016-unavailable-is-not-zero.md), [ADR-0021](0021-telemetry-collection-strategy.md), [ADR-0027](0027-multi-gpu-semantics.md).

## Context

[ADR-0033](0033-benchmark-interaction-protocol.md) settled how a benchmark that needs more than one
provider call gets it, and drew a hard line while doing so: **a benchmark never touches the
provider, the database or the clock.** The run engine owns all three; the benchmark receives inputs
and returns a score. That line is what keeps every scorer testable with a dictionary and no
fixtures.

[Benchmark Catalog §5.1](../apps/freeweight/benchmark-catalog.md) then describes how a manifest's
declared metric keys acquire values, from the first of three sources that has one: sample facts,
scorer detail, or the sample's own score. All three resolve **within one test, from its samples**.

FreeWeight Phase 9 delivers three suites for which that is not enough:

| Suite | Needs, at aggregation time | Visible to a scorer? |
|---|---|---|
| `native.memory_kv` | The model descriptor's architecture fields — layer count, KV head count, head dimension, cache precision — and the run's persisted VRAM series | No |
| `native.energy` | The power series over the run's window, integrated against real sample timestamps | No |
| `native.reliability` | **Every stored repetition of every case**, across the whole run | No — a scorer sees one sample |

None of these is a scoring question. A scorer answers *was this answer right*; these answer *what
did this run cost, and how steady was it*. They are computed once, after every sample is persisted,
from facts the database holds and the benchmark package knows how to interpret.

The implementation does this through one function in the run engine
(`services/runs.py::_suite_derived_metrics`): a three-suite allowlist that reads the run row, the
descriptor, the stored samples and the telemetry window, and hands them to a `derive()` in the
benchmark's own package. The arithmetic — KV geometry, energy integration, dispersion — stays in
`benchmarks/<suite>/`, where it is unit-tested without a database.

That is a **second seam**, differently shaped from ADR-0033's, and until now its only constraint was
a comment. CLAUDE.md's rule applies: *if an architectural decision seems missing, that is a defect in
the docs — close it with a new ADR before writing code.* This one was found while writing the code,
and the ADR is owed.

## Decision

### 1. Run derivation is the fourth metric source, and it is last

[Catalog §5.1](../apps/freeweight/benchmark-catalog.md)'s resolution order gains a fourth entry
**after** the existing three:

| Order | Source | Scope |
|---|---|---|
| 1 | Sample facts | One sample |
| 2 | Scorer detail | One test |
| 3 | The sample's score | One test |
| 4 | **Run derivation** | **One run** |

Last, because a key that any sample can answer must be answered from the sample. Derivation exists
for figures no sample contains, not as an override.

### 2. The seam is a pure function in the benchmark package

A suite that derives exposes a module-level `derive()`:

* **keyword-only arguments**, every one an already-persisted fact — the descriptor's architecture,
  the stored samples by test key, the telemetry window, the target device index;
* **returns** `tuple[AggregatedMetric, ...]`, the same shape ordinary aggregation produces;
* **receives no database handle, no provider, no clock, and no configuration object.**

The run engine reads; the benchmark computes. This is ADR-0033's constraint restated for the second
seam rather than an exception to it, and it is the reason `benchmarks/memory_kv/kv.py` is testable
with a list of tuples.

### 3. Registration is an explicit allowlist, not a protocol method

`_SUITES_WITH_DERIVED_METRICS` is a frozenset of three suite keys. Adding a fourth is a reviewed
edit inside the run engine, not an interface a benchmark author can quietly implement.

This is deliberate and it is the whole safety property. An optional `derive()` that any suite may
define is an invitation for the fourth suite to reach for a database session from inside a scorer,
and the first time that happens the seam stops being reviewable.

### 4. A derived metric is an ordinary metric

Every derived key is declared in the suite's manifest with its unit, aggregation and direction, like
every other key. It is stored in `metric_values` with `run_test_id` and `sample_id` both null — the
row shape that already means *run-level* — and it is queryable, comparable, exportable and
drillable by exactly the same code paths. There is no second kind of metric.

### 5. Derivation obeys the same honesty rules

* A figure that cannot be computed is `UNSUPPORTED` with a reason, never zero
  ([ADR-0016](0016-unavailable-is-not-zero.md)).
* Where more than one GPU is visible and the provider does not report placement, **every** row of a
  device-dependent suite carries `multi_gpu_placement_unknown` and no value — the whole suite, not
  the convenient half ([ADR-0027 §3](0027-multi-gpu-semantics.md)).
* A fit reports its own quality beside its result. `native.memory_kv` emits
  `kv_slope_fit_r_squared` next to the slope for exactly this reason.

### 6. A derived metric is a function of **one run**

This is the boundary that makes the seam narrow rather than merely small. Derivation may read:

* the run row and its frozen effective configuration;
* the model descriptor that run resolved;
* every stored sample of every test **of that run**;
* that run's persisted telemetry window.

It may **not** read another run — not the previous run of the same model, not a baseline, not the
run at a different context size. A benchmark measures one subject under one profile on one machine
([ADR-0023](0023-runtime-profile-resolution.md)); a figure that needs two runs is not a
benchmark result, it is a **study over results**, and its home is the comparison surface
(`GET /results/compare`, `freeweight results compare`), which already knows how to refuse a
comparison across a separating boundary.

The concrete case this forecloses is real and current: the honest measurement of KV cache cost is
several runs at different `context_size` values, differencing each run's `model_vram_bytes`. That is
a study. It does not become a benchmark by being useful.

## Alternatives considered

**A `derive()` method on the `Benchmark` protocol, optional for every suite.** The obvious shape,
and rejected: twelve of the fifteen shipped suites derive nothing, so the protocol would be twelve
`return ()` implementations carrying one real one. Worse, an extension point every suite may
implement is one every suite may *grow into*, and the first author who needs "just the previous
run's number" would have nowhere visible to be told no.

**Hand the benchmark a read-only database session.** Simplest to write, and it deletes ADR-0033's
constraint. A benchmark package that can open a session is a benchmark package that needs a database
to test, and every scorer in this application becomes a fixture problem.

**Compute the figures in the run engine.** The engine already holds the data, so this is the path of
least resistance — and it puts KV cache geometry, thermodynamics and dispersion statistics in the
module that also manages leases and cancellation. The arithmetic is the benchmark's subject matter;
it belongs where a person looking for it would look, and where it is tested without a run.

**Widen §5.1's "sample facts" to include telemetry.** Rejected on measurement grounds, not
architectural ones: telemetry is per-device over a time window, a sample is per-request. Conflating
them is precisely how a device-wide reading gets attributed to one request, which is
`PHASE9_ISSUES.md` §3's open concern and would be made structural
rather than fixed.

## Consequences

* **Cost.** Adding a deriving suite is two edits — the `derive()` in the package and the suite key in
  the engine's allowlist — and the second is in a file that gets read in review.
* **Enables.** `native.memory_kv`, `native.energy` and `native.reliability` as specified, and any
  future suite whose subject is the run rather than the answer (a thermal suite is the obvious next
  one).
* **Forecloses.** Multi-run analysis inside a benchmark, deliberately. This is a real cost: the KV
  cost function above is genuinely wanted, and this ADR sends it to the comparison surface rather
  than letting `native.memory_kv` grow a second shape.
* **The run engine knows three suite names.** Accepted. It is bounded, it is visible, and the
  alternative hides the same coupling behind a protocol that suggests the coupling is not there.

## Revisit when

* A fourth suite needs derivation and its inputs are **not** the descriptor, the run's samples or the
  run's telemetry window — that is the signal the allowlist has become the wrong shape and a declared
  protocol is owed.
* A provider reports **per-model** GPU residency, which changes what `native.memory_kv` derives from
  and is already [ADR-0027](0027-multi-gpu-semantics.md)'s own revisit trigger.
* A study over runs acquires a home concrete enough to have its own record type, at which point §6's
  boundary should be restated as *derivation is for benchmarks, this other thing is for studies*
  rather than as a prohibition.
