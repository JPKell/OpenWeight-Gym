# N6 handoff — LoadCoach 1.3.0: per-model KV precision and flash attention; the memory cap on registrations

**Row:** N6 of [outstanding work §1](../roadmap/outstanding-work.md); ADR-0120, ADR-0121 §3, ADR-0119.
**Run:** 2026-09-09, attended. **Ships:** `loadcoach 1.3.0`, release commit prepared,
**untagged and unpushed**; like N5, **CI is red until `modelrack 0.8.0` is published and
`requirements/ci.lock` is regenerated** (the pin moved to `>=0.8,<0.9`).

## What was built

* `RuntimeModelOverride` gained `kv_cache_precision` (`f16` | `q8_0` | `q4_0`) and
  `flash_attention`; `[runtime] kv_cache_precision` is now the same vocabulary plus `""`, and a
  quantized *default* without `flash_attention = true` is refused at load. Per-model combinations
  are judged on the **resolved** profile, because the chain may supply the two halves from two
  levels.
* `domain.routing.subject.runtime_profile_refusal(profile, provider_kind=)` names the two
  failures; `evaluate_constraints` applies it right after `model_disabled` and before
  `model_unavailable`, so `route explain` says "a person configured something this provider
  cannot serve" before it consults the provider's state. New rejection reasons
  `runtime_setting_unhonoured` and `kv_cache_needs_flash_attention`, with narrative meanings and
  routing.md §4 rows. **Decision taken here:** two reasons rather than one, because the remedies
  differ (switch provider vs. add one key).
* `services.routing.runtime_layers(runtime)` is the one place `[runtime]`'s TOML sentinels become
  profile layers; `RoutingPolicy.from_settings` and `loadcoach models show` both use it, so the
  CLI's `runtime_profile` block (with `profile_hash`) and `runtime_profile_refusal` are exactly
  what routing will resolve from configuration alone.
* `ProviderRegistrationSettings.memory_max_bytes` / `memory_high_bytes` → `LlamaCppProvider`
  (N4); a throttle without a cap is refused by key. `--fit` untouched (ADR-0121 §3).

## Gate

Python 3.14.4, `LoadCoach/.venv/bin/python` (local `modelrack 0.8.0` installed from
`py/ModelRack`), from `LoadCoach/`: `ruff format --check .` 232 formatted; `ruff check .` clean;
`mypy src tests` 210 files clean; `lint-imports` 4 kept;
`pytest -m "not live and not performance"` **1086 passed, 5 skipped, 18 deselected** (124 s).
`docs/configuration.md` regenerated.

## Found, not done

* `loadcoach models show`'s new block has no CLI test — the registry needs a discovered row and
  no unit fixture seeds one; `runtime_layers` and `runtime_profile_refusal` are unit-tested
  through routing. One e2e assertion on a fake-provider install is a small follow-up.
* The web models page does not show the resolved profile; the row asked for the CLI only.
* The `PostgreSQL` leg (`WEIGHTSDB_REQUIRE_POSTGRES=1`) was not run; no migration in this row.
