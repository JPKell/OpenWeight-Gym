# ADR-0119 — Model servers run under a host-memory cap

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0038](0038-one-model-at-a-time-per-gpu.md) (one resident model per GPU),
[ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) (the application launches
and supervises `llama-server`), [ADR-0066](0066-residency-is-two-level.md) (a card that degrades to
CPU is the silent failure to end), [ADR-0016](0016-unavailable-is-not-zero.md) (a refusal is a
value; a coerced number is a lie).
**Source:** Operator incident, 2026-09-09: a FreeWeight run against Ollama thrashed the reference
machine into a hard reset. Analysis and the operator's decisions are in
[`MEMORY_SAFETY.md`](../MEMORY_SAFETY.md).

## Context

A local model server that cannot fit a model and its KV cache in VRAM does not fail. Ollama's
scheduler and `llama-server --fit on` both move layers and cache into host RAM and keep serving.
On a machine whose host RAM is also the desktop's, the test runner's and the page cache's, that
spill becomes swap, and swap under a continuously-read model is a thrash the kernel's OOM killer
never gets to — there is no allocation failure, only pressure. The 2026-09-09 kernel log holds no
`oom-kill` line for the fourteen days around the incident.

`systemd-oomd`, the pressure-based killer Ubuntu ships, watches `user@<uid>.service` by default
and nothing in `system.slice`, which is where `ollama.service` runs. So the daemon was capped by
nothing, monitored by nothing, and the pressure it produced was accounted to the desktop session.

The suite's own docs already say the principle — ADR-0066 was written to end "a card that then
degrades to CPU or OOMs", `memory_kv`'s catalog entry says an out-of-memory rejection is a
measurement — but no document said *who* makes the server fail rather than spill, or how.

## Decision

**Every model server the suite runs or connects to runs under a cgroup memory cap with swap
denied, so that not fitting is a fast kill of the server and never a slow death of the host.**

1. **Ollama is capped by its unit file, by the operator.** `ollama.service` carries
   `MemoryHigh`, `MemoryMax`, `MemorySwapMax=0` and `ManagedOOMMemoryPressure=kill`. Reference
   values for 30 GB RAM are 22 G / 24 G; the rule is `MemoryMax` = RAM − 6 GB. The same file
   sets `OLLAMA_CONTEXT_LENGTH` to a size the card serves (8192 on the reference machine) and
   `OLLAMA_MAX_LOADED_MODELS=1` (ADR-0038). The suite does not, and cannot, cap a system service
   from inside an application; `MEMORY_SAFETY.md` §2.1 is the exact file.

2. **`llama-server` is capped by its launcher.** `modelrack.LlamaCppProvider` accepts
   `memory_max_bytes` and `memory_high_bytes` (keyword-only, `None` by default) and, when set,
   prefixes the launch argv with `systemd-run --user --scope -p MemoryMax=… [-p MemoryHigh=…]
   -p MemorySwapMax=0`. The wrapper is the *only* change to the launch: the child is still a
   session leader, its stderr still lands in the state directory, the orphan sweep still
   identifies it by pid. `systemd-run` absent from `PATH` while a cap is configured is a launch
   error naming both — a configured cap is never silently dropped. FreeWeight and LoadCoach expose
   the two settings under `[provider]` / the provider registration with the unit in the name.

3. **A killed server is a recorded outcome, not a retry.** When the cap fires, the supervisor
   sees a dead process and raises its existing typed launch/serve error; FreeWeight stores the
   sample as failed at that context (the OOM measurement) and LoadCoach marks the model
   unavailable with the reason. Neither relaunches at a smaller size on its own — choosing a
   smaller context is the operator's decision (ADR-0023), not a coercion (ADR-0016).

4. **Until decision 2 ships, the operator caps the parent** with `systemd-run --user --scope`
   around `loadcoach serve`, `freeweight run` and `pytest -m live`; the child inherits the scope.
   `MEMORY_SAFETY.md` §2.2 gives the commands.

## Consequences

*Positive.* Not fitting costs seconds, not a reset. The failure is in the journal, in the run's
samples and in `route explain`, in that order — all places a person looks. The desktop keeps a
guaranteed ≥ 6 GB. `systemd-oomd` now covers the daemon as well as the session.

*Negative.* A model that would have served slowly on a partial offload is killed instead; an
operator who wants slow-but-served raises the cap or sets `runtime.gpu_layers` by hand. Two caps
exist (unit file for Ollama, launcher for llama.cpp) because the two servers have different owners.
`systemd-run` is a Linux-with-systemd dependency at launch time; on a host without it the setting
is refused rather than emulated (`prlimit -v` counts address space, not resident memory, and
kills mmap-heavy servers at the wrong number).

*Neutral.* The cap is host-level configuration, not part of the runtime profile: two runs at
different caps have the same `profile_hash`, correctly — the cap does not change what was served,
only whether the host survived it not fitting.

## Alternatives considered

* **Rely on Ollama's own fit estimate.** It estimates, it does not refuse; and its spill path is
  what the incident was. Rejected.
* **A pre-flight VRAM estimate in the application** (weights + KV formula) that refuses before
  loading. Useful as a warning and listed in `MEMORY_SAFETY.md` §4 as a table; rejected as the
  guard because the estimate is what ADR-0027 found to be wrong at the edges, and a guard that is
  sometimes wrong is not a guard.
* **`earlyoom` or a larger swap.** Both make the thrash longer or the kill later; neither makes
  the server the thing that dies.
* **`MemoryMax` without `MemorySwapMax=0`.** The daemon then swaps up to the cap before dying —
  minutes of thrash. Rejected; the operator chose the swap-denied variant.

## Revisit when

* `llama-server` gains a hard "GPU-only, fail on no-fit" mode that makes the launcher cap
  redundant for the VRAM case (the host-RAM case still needs the cgroup).
* A second machine without systemd needs the launcher cap; at that point the wrapper becomes a
  `ProcessLauncher` strategy rather than a flag.
