# N4 handoff — `llama-server` launched under a host-memory cap

**Row:** N4 of [outstanding work §1](../roadmap/outstanding-work.md); ADR-0119 decision 2.
**Run:** 2026-09-09, attended. **Ships:** `modelrack 0.8.0`, release commit prepared,
**untagged and unpushed**.

## What was built

* `LlamaServerSupervisor(memory_max_bytes=, memory_high_bytes=, which=)` and the same two figures
  on `LlamaCppProvider`. With a cap, the launch argv is
  `systemd-run --user --scope --quiet -p MemoryMax=<n> [-p MemoryHigh=<n>] -p MemorySwapMax=0 --
  <resolved llama-server> …`. Without one, byte-identical to 0.7.1.
* **Decision taken here, not in the ADR:** `systemd-run --scope` execs the command in place
  (verified on the reference machine: `Popen.pid` is the server's pid, `/proc/<pid>/cmdline` is
  the server's argv with `argv[0]` resolved to a path, the cgroup is `run-p<pid>-…scope` under
  `user@1000.service`). So the **recorded** argv — handle, pid file, error details — is the
  server's own with its executable resolved through the injected `which`, and the orphan sweep's
  cmdline comparison keeps working. Recording the wrapper's argv would have made every capped
  orphan look like a reused pid and leaked it.
* A cap with no `systemd-run` is `ProviderUnavailable` (`launch_failed`) naming the wrapper and
  the cap, before anything is spawned; malformed figures are `ValidationError` at construction.

## Gate

Python 3.13.15, `py/ModelRack/.venv/bin/python`, from `py/ModelRack`: `ruff format --check .`
60 formatted; `ruff check .` clean; `mypy src tests` 53 files clean; `lint-imports` 2 kept;
`pytest -m "not live and not performance"` **1445 passed, 16 skipped, 27 deselected** (6.7 s).

**Live, on the real `llama-server` (b10792 CUDA) with `MODELRACK_LLAMACPP_MODELS=~/ai/models/llm`:**
`tests/live/test_llamacpp_live.py::TestMemoryCap` — a 64 MiB cap on the smallest GGUF:
`cap fired in 0.3s: ProviderUnavailable reason=process_exited exit_code=-9`; no `llama-server`
left, no pid file left, host untouched. That is the row's "fires the cap on purpose and sees a
dead server, not a hung host".

## Found, not done

* `ci.lock` was not regenerated; nothing in the runtime set moved. If CI pins `modelrack` by
  version anywhere downstream, N5/N6 move the floor to `>=0.8`.
* The scope name is systemd's default (`run-p<pid>-i<n>.scope`); a `--unit` naming the model
  would read better in `systemd-cgls` and is a one-flag follow-up.
