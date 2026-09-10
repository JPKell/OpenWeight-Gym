# Performance Results

**Purpose:** [`performance-targets.md`](performance-targets.md) states a budget for every measure
that matters; this document is where a budget's **measured** number lives once something has
actually run it. Never invent a figure here — every number below either came from
`docs/history/handoffs/*_HANDOFF.md` (a session that ran the test and recorded what it saw) or from a
nightly `performance` job's own output, pasted in per §2. A blank "Measured" cell means exactly
that: nobody has run that budget in CI yet, which — before M9 Group 4 (`docs/roadmap/outstanding-
work.md` row L4) added a nightly schedule to the ten repositories that lacked one — was true of
most of this document.

---

## 1. Reference machine

Captured 2026-09-07 via `sweatmeter.TelemetryCollector().machine_profile()`
(`py/SweatMeter/.venv/bin/python3`, `sweatmeter 0.4.0`):

```text
machine_fingerprint: f9a666d8bfe4c46bd13d17aa8e3e11e73c44b366f95f1f65d64a06cce1361b6b
hostname:            Jordan-main
os:                  Linux #30-Ubuntu SMP PREEMPT_DYNAMIC Fri Jul 31 18:22:54 UTC 2026
kernel:              7.0.0-30-generic
architecture:        x86_64
cpu:                 AMD Ryzen 5 7600X 6-Core Processor (6 physical / 12 logical cores)
ram:                 32,220,971,008 bytes (~30 GiB)
gpu 0:               NVIDIA GeForce RTX 5060 Ti — 17,103,323,136 bytes VRAM (~16 GiB)
                     driver 580.173.02, CUDA 13.0, compute capability 12.0
python (snapshot):   3.14.4
```

This is the same physical workstation [`performance-targets.md` §1](performance-targets.md#1-reference-machine)
describes ("Ubuntu 26.04 LTS · Python 3.13 · NVIDIA RTX 5060 Ti (16 GB) · Ollama 0.32.13 · local
SQLite (WAL)") — same GPU model and VRAM, same host. The `python (snapshot)` line above is
whatever interpreter happened to be first on `PATH` when this profile was captured, not a claim
about which interpreter ran any given test below: every measurement in §3 names its own repo's
venv interpreter, per M5C-13, in its own `Source` column, and those are a mix of 3.13.x and 3.14.x
across sessions. `machine_fingerprint` is the value that ties a number to this box regardless of
which interpreter produced it.

---

## 2. How to fill this in

Each repository's `.github/workflows/nightly.yml` (all fourteen, since M9 Group 4 / row L4) runs
`pytest -m performance` on a schedule, excluded from the default gate because
[testing-standards.md §10](../standards/testing-standards.md) and `performance-targets.md` §6 both
require budget assertions to run on medians over N iterations on a dedicated, otherwise-idle
runner rather than a shared PR container. To paste a run's numbers in here:

1. Open the nightly run's log (or a session's handoff, if a person rather than CI produced the
   number — most of §3 below is the latter, since most repositories only just gained a nightly
   job).
2. Read off the **median** (this document never records a single sample) and, where the test
   reports it, the p95/p99 or max.
3. Fill the row's `Measured` cell as `**median** (p95 if reported)`, and the `Source` cell as the
   handoff or run plus the interpreter (e.g. `I2_HANDOFF.md §8, Python 3.13.15`).
4. A measured figure over its **ceiling** is a bug, not a documentation problem — fix the
   regression before updating this file, per `performance-targets.md` §6's 25%-regression rule.

---

## 3. Budgets, target beside measured

### 3.1 HTTP and API (FreeWeight, LoadCoach, IdeaPress, PromptCadence — each measures its own instance)

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| JSON GET, in-memory data (health, version, config) | p50 ≤ 5 ms | p99 ≤ 25 ms | | |
| JSON GET, single-row DB read | p50 ≤ 10 ms | p99 ≤ 50 ms | | |
| JSON list, 50 rows + pagination | p50 ≤ 25 ms | p99 ≤ 100 ms | | |
| Non-streaming generate: overhead excluding provider time | ≤ 15 ms | ≤ 50 ms | | |
| HTML page render (server-side, warm templates) | p50 ≤ 30 ms | p99 ≤ 120 ms | | |
| Static asset (cached, ETag hit) | ≤ 2 ms | ≤ 10 ms | | |

### 3.2 Streaming

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| Added latency per streamed chunk (provider → client) | ≤ 5 ms | ≤ 20 ms | LoadCoach: **0.06 ms** | `M4_HANDOFF.md` (M5-20), reference machine |
| Time from provider's first token to client's first SSE frame | ≤ 20 ms | ≤ 60 ms | | |
| SSE heartbeat interval | 15 s ± 1 s | — | | |
| Concurrent idle SSE connections held per process | ≥ 200 | — | | |
| Memory per idle SSE connection | ≤ 64 KiB | ≤ 256 KiB | | |
| Event replay from `Last-Event-ID` (1 000 events) | ≤ 100 ms | ≤ 400 ms | | |

### 3.3 Queue and scheduling (LoadCoach)

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| Enqueue (HTTP accepted → row committed) | ≤ 15 ms | ≤ 50 ms | **1.8 ms** | `M4_HANDOFF.md` (M5-20) |
| Dispatch latency (job eligible → execution starts), idle worker | ≤ 100 ms | ≤ 500 ms | **17 ms** | `M4_HANDOFF.md` (M5-20) |
| Routing decision (20 candidates, evidence cached) | ≤ 20 ms | ≤ 100 ms | **16 ms** (warm); closeout re-run **15.1 ms median / 32.0 ms max** | `M4_HANDOFF.md` (M5-20); `m5-reverification.prompt.md` closeout — the tightest-margin budget, flagged for re-measurement each release |
| Routing decision (cold evidence cache) | ≤ 150 ms | ≤ 500 ms | **19 ms** (40 ms worst single run) | `M4_HANDOFF.md` (M5-20) |
| Queue poll overhead at idle | ≤ 0.5 % of one core | ≤ 2 % | **0.32 %** | `M4_HANDOFF.md` (M5-20) |
| Cancellation acknowledged (queued job) | ≤ 50 ms | ≤ 200 ms | **0.9 ms** | `M4_HANDOFF.md` (M5-20) |
| Cancellation acknowledged (executing job, at the next stream boundary) | ≤ 1 s | ≤ 5 s | **53 ms** | `M4_HANDOFF.md` (M5-20) |
| Recovery of 1 000 in-flight jobs after restart | ≤ 2 s | ≤ 10 s | within budget (n = 1) | `M4_HANDOFF.md` (M5-20) |
| Execution overhead (per job, outside provider time) | — (see §3.1's "non-streaming generate" row) | ≤ 15 ms | **3 ms** | `M4_HANDOFF.md` (M5-20) |

Additional LoadCoach streaming figure measured against a real 5 ms/token cadence (not the fake
provider used above): added-latency p95 ≈ **1.29 ms** at closeout, reproducing an earlier **10.2 ms**
median at the (since-changed) 20 ms SSE poll interval (`m5-reverification.prompt.md`).

### 3.4 Telemetry (SweatMeter)

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| Snapshot without GPU (`/proc` + `/sys` only) | ≤ 3 ms | ≤ 10 ms | | |
| Snapshot with `nvidia-smi` (single GPU) | ≤ 40 ms | ≤ 120 ms | | |
| Sampler CPU cost at 1 s interval | ≤ 0.5 % of one core | ≤ 1.5 % | | |
| Persisted sample write (batched) | ≤ 2 ms/sample amortized | ≤ 10 ms | | |
| Effect of sampling on measured benchmark throughput | ≤ 1 % | ≤ 2 % | | |

### 3.5 Database

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| Single-row insert (sample) | ≤ 1 ms | ≤ 5 ms | | |
| Batched sample insert (100 rows, one transaction) | ≤ 15 ms | ≤ 60 ms | | |
| Dashboard aggregate over 100 k samples | ≤ 200 ms | ≤ 1 s | | |
| Run detail page query set | ≤ 100 ms | ≤ 400 ms | | |
| Migration on a 1 GB SQLite DB | ≤ 60 s | ≤ 300 s | | |
| Backup of a 1 GB SQLite DB | ≤ 30 s | ≤ 120 s | | |

### 3.6 Startup and discovery

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| `python -m <app>` → serving (warm page cache, existing DB) | ≤ 1.5 s | ≤ 3 s | | |
| CLI `--help` | ≤ 250 ms | ≤ 600 ms | | |
| CLI simple command (health, version) end to end | ≤ 500 ms | ≤ 1.5 s | | |
| Model discovery, 20 models, metadata cached | ≤ 200 ms | ≤ 1 s | | |
| Model discovery, 20 models, cold (provider `show` per model) | ≤ 3 s | ≤ 10 s | | |
| First-run database creation + migration | ≤ 2 s | ≤ 5 s | | |

### 3.7 UI responsiveness

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| First contentful paint, local, warm | ≤ 400 ms | ≤ 1 s | | |
| Interaction to visual feedback (sort, filter, tab) | ≤ 100 ms | ≤ 250 ms | | |
| Telemetry bar update cadence | 1 s (configurable 0.25–5 s) | — | | |
| Telemetry bar update: no layout shift | CLS 0 | — | | |
| Table with 1 000 rows × 20 columns: sort | ≤ 150 ms | ≤ 500 ms | | |
| Chart re-theme on light/dark switch | ≤ 200 ms | ≤ 500 ms | | |
| Total JS shipped per page (uncompressed, excl. charting vendor) | ≤ 60 KB | ≤ 120 KB | | |
| Charting vendor bundle (vendored, cached) | ≤ 1 MB | — | | |

### 3.8 Benchmark execution overhead (FreeWeight)

| Measure | Target | Ceiling | Measured | Source |
|---|---|---|---|---|
| Per-sample overhead outside the provider call (scoring, persistence, events) | ≤ 10 ms | ≤ 50 ms | | |
| Per-sample overhead as a share of a 2 s inference | ≤ 0.5 % | ≤ 2.5 % | | |
| Run start (validate → persist → first provider call) | ≤ 500 ms | ≤ 2 s | | |
| Aggregation for a 10 000-sample run | ≤ 5 s | ≤ 20 s | | |
| Export of a 10 000-sample run to JSON | ≤ 10 s | ≤ 30 s | | |
| **Serving-mode overhead** (llama.cpp, clean vs. adapter-registered) — LA3, not in `performance-targets.md`'s own table but the arc's own revisit trigger | — | material if it trips ADR-0060's trigger | **+0.9 %** (about +6 ms on a ~750 ms warm run; sign changes run to run, i.e. at the measurement's noise floor); confirmatory `H5` run: **+0.5 % (+3.4 ms)** | `H4_HANDOFF.md` §4; `H5_HANDOFF.md` |

### IdeaPress — its own spec §15 budgets (not the generic §3.1–3.7 shape; measured, not yet in a named `performance-targets.md` row)

| Budget | Measured | Allowed | Headroom |
|---|---|---|---|
| Stage orchestration overhead per attempt | 0.1 ms | 50 ms | +100 % |
| Validation of a 5 000-word unit | 5.0 ms | 200 ms | +97 % |
| Project load, 100 units | 9.5 ms | 300 ms | +97 % |
| Export of 100 units to Markdown | 81.0 ms | 2 000 ms | +96 % |
| Export of 100 units to HTML | 39.7 ms | 5 000 ms | +99 % |
| Editor page render (100-unit navigator) | 12.7 ms | 300 ms | +96 % |
| Draft autosave round trip | 1.2 ms | 100 ms | +99 % |

Slowest of five runs after two warm-ups, against a project of the size each budget names
(`M8_HANDOFF.md`, `.venv/bin/pytest -m performance` — 10 passed, all seven budgets).

### PromptCadence — spec §15 budgets

[`performance-targets.md` §3.3 note](performance-targets.md#33-queue-and-scheduling-loadcoach) and
its main text both say PromptCadence carries no row in the tables above by design — its budgets
are per-turn and per-operation, defined in
[its spec §15](../apps/promptcadence/spec.md) and asserted target-and-ceiling per
[ADR-0097](../adr/0097-a-performance-budget-asserts-its-ceiling-and-reports-its-target.md). All ten
were measured at row I2 (reference machine, Python 3.13.15, fake LoadCoach):

| Measure | Target / ceiling | Median | p95 | Verdict |
|---|---|---|---|---|
| Trajectory admission | 50 / 200 ms | **1.77 ms** | 3.56 ms | inside target |
| Plan approval evaluation, 20 steps | 20 / 100 ms | **0.07 ms** | 0.08 ms | inside target |
| Per-turn overhead excluding LoadCoach time | 25 / 100 ms | **13.45 ms** | 25.56 ms | inside target |
| Tool dispatch overhead excluding tool runtime | 10 / 50 ms | **2.09 ms** | 2.20 ms | inside target |
| Ledger debit, ceilings evaluated | 5 / 20 ms | **3.15 ms** | 4.17 ms | inside target |
| Compaction plan, 200-turn transcript | 50 / 200 ms | **1.51 ms** | 1.66 ms | inside target |
| Added latency per SSE event (real loopback socket) | 5 / 20 ms | **1.40 ms** (was 10.00 ms at the earlier 20 ms poll) | 2.18 ms | inside target, after the interview's decision to follow LoadCoach to a 2 ms poll |
| Explanation retrieval, terminal (materialized), 500 turns | 25 / 100 ms | **2.01 ms** | 2.11 ms | inside target |
| Explanation materialization, 500-turn trajectory | 2 / 10 s | **40 ms** | 119 ms | inside target |
| Recovery of 100 in-flight trajectories at startup | 2 / 10 s | **280 ms** | — (n = 1) | inside target |

Against the real stack (not the fake LoadCoach) the two overhead rows above were also observed
carrying `overhead_ms` **52–55 ms** beside `loadcoach_ms` 1 233 and 43 769 — the larger figure
includes the real wire build, compaction estimate and the two writes around an actual HTTP call,
and is reported separately by design (`I2_HANDOFF.md` §8).

---

## 4. Memory budgets

| Component | Idle RSS | Under load | Ceiling | Measured |
|---|---|---|---|---|
| FreeWeight server | ≤ 120 MB | ≤ 400 MB during a run | 800 MB | |
| LoadCoach server | ≤ 120 MB | ≤ 500 MB with 4 concurrent streams | 1 GB | |
| IdeaPress server | ≤ 120 MB | ≤ 600 MB with a long project loaded | 1 GB | |
| CLI (non-server command) | ≤ 80 MB | — | 200 MB | |

PromptCadence has no row here by design (`performance-targets.md` §4) — giving its server an RSS
figure beside its three siblings is an open item, not a decision taken elsewhere.

---

## 5. What is still an empty column, and why

Most of §3's generic tables (3.1, 3.4, 3.5, most of 3.6/3.7) are blank today. Row L4 (M9 audit
Group 4, `docs/roadmap/outstanding-work.md`) added a `schedule:` nightly job to the ten
repositories that had `tests/performance/` but never ran it in CI; until those jobs have actually
fired and someone pastes a run's numbers in per §2, an empty cell here means exactly what it says —
not zero, not passing, simply **not yet measured**, per this document's own naming rule
(`baseaicore`'s `Unsupported` convention, ADR-0016, applied to a document rather than a type).
