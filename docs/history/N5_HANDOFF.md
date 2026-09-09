# N5 handoff — FreeWeight 1.2.0: KV precision and flash attention per run, `--fit off`, the max-fit ceiling, the memory cap

**Row:** N5 of [outstanding work §1](../roadmap/outstanding-work.md); ADR-0120, ADR-0121, ADR-0119.
**Run:** 2026-09-09, attended. **Ships:** `freeweight 1.2.0`, release commit prepared (`ad93ad3`),
**untagged and unpushed**; **CI stays red until `modelrack 0.8.0` is published and
`requirements/ci.lock` is regenerated** — the lock still pins 0.7.1 and the new constructor
keywords do not exist there.

## What was built

* `[runtime] flash_attention`, `kv_cache_precision` (`f16` | `q8_0` | `q4_0`), `fit_to_device`
  (default `false`). `RuntimeSettings.to_profile()` now takes a **required** `provider_kind`:
  under `llamacpp` it emits `provider_options["--fit"] = "off"` unless `fit_to_device`; under
  `ollama` it refuses either launch key by name (`ConfigurationError`, `details.field`), and the
  root `Settings` validator refuses the same at load. Every call site — CLI `run start`, the API's
  per-run `runtime` override, goal calibration, the calibration route — passes
  `settings.provider.kind`. **Decision taken here:** the argument is required rather than
  defaulted, because a default would silently pick a provider's behaviour for the other one.
* `[benchmarks] max_fit_context_tokens` (default `131072`, `ge=8192`). `memory_kv.build()`
  takes it, fits `MAX_FIT_CONTEXT_TOKENS` through `long_context`'s own `sweep_ladder` (truncate,
  extend by doubling, ceiling as final rung), and writes `dataset_hashes["max_fit_ladder"]` on the
  built manifest; the shipped ceiling leaves the shipped manifest byte-identical (tested).
  `max_context_capped_by_configuration` reads `min(served_context, ceiling)`.
* `[provider] memory_max_bytes` / `memory_high_bytes` → `LlamaCppProvider` (N4); a throttle
  without a cap is refused by key at load.
* Hash stability: an Ollama profile with the new keys unset hashes exactly as before (tested);
  a llama.cpp profile gains `--fit off` and therefore a **new hash** for the same settings — the
  ADR-0121 trade, stated in the changelog.

## Gate

Python 3.14.x, `FreeWeight/.venv/bin/python` (local `modelrack 0.8.0` installed from
`py/ModelRack`, non-editable), from `FreeWeight/`: `ruff format --check .` 346 formatted;
`ruff check .` clean; `mypy src tests` 316 files clean; `lint-imports` 4 kept;
`pytest -m "not live and not performance"` **2645 passed, 29 skipped, 30 deselected** (214 s).
`docs/configuration.md` regenerated (6 rows added); `docs/openapi.json` unchanged (the `runtime`
body is free-form).

## Found, not done

* No live run of `native.memory_kv` under the new ceiling on the real llama-server; the ladder
  and hash are unit-tested. Worth one `pytest -m live` pass at `max_fit_context_tokens = 32768`
  with `--fit off` to see the 32 k rung succeed and nothing spill.
* `FreeWeight/scripts/sync_docs.py --check` still disagrees with the byte-identical mirror rule
  (N1 handoff); untouched here, mirrors copied with `cp` and checked with `cmp`.
