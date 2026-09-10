# WA1 handoff — SetSpec + FreeWeight: `adapters_registered` on the wire and in the table

**Row:** WA1 ([`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md)), attended, run
2026-09-10 after W7 and before W8. **Kickoff:**
[`history/prompts/wa1-setspec-freeweight-adapters-registered.prompt.md`](../prompts/wa1-setspec-freeweight-adapters-registered.prompt.md).
**Ships, unreleased:** SetSpec's `benchmark.result` / `benchmark.run_summary` `1.1`, FreeWeight's
migration `0010` and export, and WeightRoomGym's migration `0005`. **No version bump** — the
operator holds versions until the W arc ends, so SetSpec stays `0.6.0` and FreeWeight `1.2.1`,
with the work under `[Unreleased]`. The gates first cut `0.7.0` and `1.3.0`, as the kickoff said;
SetSpec `4cfefac` and FreeWeight `da836aa` put them back. Nothing is tagged, pushed or
published.

**Read §2 first.** One of the kickoff's "decisions already taken" does not hold in the code, and
[ADR-0135](../../adr/0135-a-minor-that-feeds-a-checked-hash-is-read-at-its-own-minor.md) was written
before any code to say what replaced it.

## 1. What was built, by commit

| Repository | Commit | What |
|---|---|---|
| WeightRoom | `7ab1af8` | `docs(adr)`: ADR-0135; ADR-0068 gains an *Amended by* note; API and Contract Standards §7 rule 2 names the exception |
| SetSpec | `8d08f3c` | Gate A. `RuntimeProfileV1_1Fields`, `BenchmarkResultV1_1Fields`, `BenchmarkRunSummaryV1_1Fields` and their `V1_1Out`/`V1_1In` pairs; registration; two JSON Schemas; six goldens; `SUPPORTED_SCHEMAS` at `1.1`; contract and unit tests; `baseaicore>=0.4.2`; CHANGELOG |
| FreeWeight | `50dc05a` | Gate B. Migration `0010` and its backfill; the model column; the repository and `_stored_runtime_profile` carry the field; the export on `1.1`, `freeweight.export` versioned by content; tests; data model and spec mirrored; CHANGELOG |
| WeightRoom | `954f6d5` | Gate C, the console. Migration `0005` adds `(freeweight, 0010)` to `known_revisions`; `tests/fixtures/databases/freeweight-0010.sqlite3`; the never-writable guard test reads it; seed tests count both FreeWeight revisions; CHANGELOG under `[Unreleased]` |
| SetSpec | `04e834b` | Gate C, the mirror: `docs/packages/setspec/schemas.md` and `spec.md` |
| SetSpec | `4cfefac` | Version held at `0.6.0` (operator); the entries sit under `[Unreleased]` |
| FreeWeight | `da836aa` | Version held at `1.2.1`; the `setspec` range back to `>=0.6,<0.7` with a `TODO: re-pin on publish`; OpenAPI snapshot regenerated |
| WeightRoom | `a71fb27` | Gate C, the docs: `packages/setspec/schemas.md` and `spec.md`, `apps/freeweight/data-model.md` and `spec.md` (canonical), the two synced `guide/README.md` copies, the row marked done, this handoff |
| WeightRoom | this commit | The same hold: ADR-0135's consequences, the CHANGELOG, the roadmap row, FreeWeight's spec and the schema catalogue stop naming `0.7.0` / `1.3.0`; this handoff says so |

## 2. What the kickoff got wrong, and where it went

1. **"Any reader of these payloads accepts `1.1` unchanged (schema rule 2)" is false for the
   documents this minor exists for.** Checked on `setspec 0.6.0` with `baseaicore 0.4.2` before any
   edit: `BenchmarkRunSummaryIn` and `BenchmarkResultIn` accept a profile with the field absent, and
   refuse it `false` or `true` with the matching BaseAiCore hash — the preserving reader keeps the
   key as a nested extra, then the frozen class's own validator recomputes the hash without it. No
   edit to the frozen class can fix readers already installed, and ADR-0068 rule 1 forbids the
   edit anyway. **ADR-0135** records the limit, and `tests/contract/test_runtime_profile_minor.py`
   in SetSpec asserts both halves (unstated accepted, stated refused).
2. **LoadCoach's evidence import is not a reader of these payloads.** No application's source reads
   `benchmark.result` or `benchmark.run_summary`; LoadCoach imports `capability.evidence` and
   `benchmark.evidence_bundle`, which carry only `runtime_profile_hash` — already computed by
   FreeWeight with the field. So no LoadCoach test was written: it would have tested nothing.
   The one reader that exists, FreeWeight's own export test, now reads through
   `BenchmarkRunSummaryV1_1In` (ADR-0135 decision 4).
3. **The defect was wider than "a run served with adapters registered".** `serving_mode` states
   `false` for an adapter-capable provider with no available adapter, and those runs failed the
   export the same way — the failing test covers both states.
4. **The same gap broke re-reading a run.** `services/runs.py::_stored_runtime_profile` rebuilt a
   stored run's profile without the field, so a queued or resumed run reached the provider stating
   nothing about its serving mode, and a repeat recomputed a different hash than the original. It
   is the one function every such path goes through, and it now returns the field (claim 3 of
   `tests/contract/test_run_summary_serving_mode.py`).
5. **"Find the rest by reference":** there are none. Only `benchmark.result` and
   `benchmark.run_summary` embed the profile; `capability.evidence` and `benchmark.evidence_bundle`
   carry the hash string and do not move.
6. **`freeweight.export`'s own version was not mentioned.** It embeds run summaries verbatim
   (ADR-0035 §4), so carrying the minor is its own minor (ADR-0068 rule 5), chosen by content
   (ADR-0084 rule 5): `1.1` when any run in it states the field, `1.0` otherwise — in JSONL, per
   line. Recorded in ADR-0135 decision 3.
7. **`WEIGHTSDB_REQUIRE_POSTGRES=1` is not FreeWeight's switch.** FreeWeight's integration conftest
   reads `FWTEST_REQUIRE_POSTGRES` and `FWTEST_POSTGRES_URL`; WeightRoomGym (through
   `weightsdb.testing`) reads `WEIGHTSDB_REQUIRE_POSTGRES` and `WEIGHTSDB_POSTGRES_URL`.
8. **Environment, not code.** SetSpec's venv still had `baseaicore 0.4.1` (the lock already pins
   `0.4.2`); FreeWeight's venv had a stale non-editable `setspec 0.6.0` directory in
   `site-packages` shadowing the editable install, so the first run of the new test failed on an
   `ImportError` rather than on the defect. Both fixed in the venvs; nothing committed.

## 3. Decisions inside the implementation worth knowing

* **The `1.1` profile drops only `None`.** `RuntimeProfileV1_1Fields._omit_unstated_adapters_registered`
  tests `is None`; `False` is a stated value that hashes, and dropping it as falsy would publish a
  profile that no longer recomputes its hash. A unit test pins that.
* **`profile_hash` is overridden, not refactored.** The `1.1` property repeats the `RuntimeProfile(...)`
  call with one more argument; moving the call into a helper on the frozen class would have edited it.
* **Goldens.** Each `1.1` set is authored from the `1.0` set with the hash recomputed by BaseAiCore:
  `minimal` is byte-identical to `1.0`'s (unstated), `unsupported` states `false`, `full` states
  `true`. SetSpec's `test_goldens.py` expected `benchmark.result` to publish only `["1.0"]` and
  now expects `["1.0", "1.1"]`.
* **The backfill imports `baseaicore.RuntimeProfile`** rather than re-implementing the hash, reads
  through a typed `sa.table` (`PortableJSON` for `provider_options_json`) so the JSON decodes on both
  dialects, logs `adapters_registered backfill: N null, N false, N true, N unmatched` at INFO and
  the unmatched ids at WARNING. SQLite adds the column in place (no rebuild); `downgrade` drops it.
* **`RuntimeProfileRepository.get_or_create` takes `adapters_registered` as a required keyword**,
  like its siblings, so a caller cannot forget it.
* **The JSON export chooses its version after the last run.** `schema_version` is the last key
  canonical JSON writes, so `_iter_json` streams every run, then writes the version it saw was
  needed; nothing is buffered.
* **WeightRoomGym keeps `0009` known.** An installation still on `freeweight 1.2.1` must stay
  readable. Only the never-writable guard test moved to the `0010` fixture; the W7 database-page
  tests still read `0009`. The regenerated file differs from `freeweight-0009.sqlite3` only in
  `runtime_profiles` (checked with the `CREATE` statements' lines compared as sets — `runs` and
  `capability_evidence` differ only in constraint order, from batch-mode rebuilds).
* **Not done, deliberately.** FreeWeight's comparison and results surfaces do not show
  `adapters_registered` as a column; the hash already separates the two serving modes. Add it when
  an operator needs to *see* which arm a column is, not only that they differ.

## 4. The gates

**SetSpec — Python 3.13.15** (`/home/jpk/ai/suite/py/SetSpec/.venv`):

```bash
ruff format --check .      # 47 files already formatted
ruff check .               # All checks passed!
mypy src tests             # Success: no issues found in 41 source files
lint-imports               # Contracts: 2 kept, 0 broken
pytest -m "not live and not performance" --cov
                           # 1204 passed, 4 skipped; coverage 97.49 % (floor 95 %) — the same after the version revert
```

The `1.0` schema snapshots regenerated byte-identically (no `1.0.json` in the diff).

**FreeWeight — Python 3.14.4** (`/home/jpk/ai/suite/FreeWeight/.venv`, editable `setspec` from
`~/ai/suite/py/SetSpec` until the release), both dialects in one run against a throwaway
`postgres:16` (removed afterwards):

```bash
ruff format --check . && ruff check . && mypy src tests && lint-imports
FWTEST_REQUIRE_POSTGRES=1 FWTEST_POSTGRES_URL=postgresql+psycopg://…@127.0.0.1:55432/freeweight_test \
  pytest -m "not live and not performance" --cov
# ruff format: 350 files already formatted; ruff check: All checks passed!
# mypy: Success: no issues found in 319 source files; lint-imports: Contracts: 4 kept, 0 broken
# pytest: 2707 passed, 3 skipped, 30 deselected; coverage 89.14 % (floor 85 %)
# tests/e2e/test_export.py was edited to read at 1.1 while that run was going; rerun alone: 25 passed
```

After the version revert, the same gate on SQLite (PostgreSQL not rerun for a version string):
```text
ruff format --check: 350 files already formatted; ruff check: All checks passed!
mypy: no issues found in 319 source files; lint-imports: Contracts: 4 kept, 0 broken
pytest: 2680 passed, 30 skipped (the PostgreSQL legs), 30 deselected; coverage 89.14 %
```

**WeightRoomGym — Python 3.14.4** (`/home/jpk/ai/suite/WeightRoom/.venv`): ruff format and check
clean, mypy clean (150 files), 5 contracts kept. `pytest --cov`: **1177 passed, 3 skipped,
coverage 91 %** on the rerun. The first full run had one failure,
`tests/unit/test_cli.py::test_units_sync_writes_reports_and_audits`, which passed alone and in both
later full runs; it touches none of this row's files and was not investigated further. With
`WEIGHTSDB_REQUIRE_POSTGRES=1` against the same container: **1180 passed**, none skipped.

## 5. The demonstration — a copy of FreeWeight's real database

**The copy.** `~/.local/share/freeweight/freeweight.sqlite3` opened read-only and copied with
SQLite's backup API into the session scratchpad. The operator's file was never opened for writing.
The copy was at `0009` with one `runtime_profiles` row and six runs.

**The backfill on the copy** (`0009 → 0010`):

```text
INFO 0010_runtime_profiles_record_adapters_registered_py: adapters_registered backfill: 1 null, 0 false, 0 true, 0 unmatched
```

**The copy held no run on an adapter-capable provider**, so one was made against it, on the real
`llama-server` (on `PATH`) with nothing faked: a scratch config pointing `[provider] kind =
"llamacpp"` at a scratch model directory holding a symlink to
`~/ai/models/llm/Qwen2.5-1.5B-Instruct.Q8_0.gguf`, and `[adapters] directory` at a scratch directory
holding symlinks to the `terse` and `verbose` LoRAs with two manifests written for the
demonstration (the operator's adapter directory has no manifests; `source_sha256` in them is
`lora-train/questions.txt`). `freeweight adapters list` showed both `ok`, and

```text
$ freeweight run start --config <scratch>/config.toml --model Qwen2.5-1.5B-Instruct.Q8_0 --suite native.echo
Queued run 01M267C2A8VB4PY9RBCG6WWN5B (native.echo against llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b).
Run 01M267C2A8VB4PY9RBCG6WWN5B completed.
```

No `llama-server` was left running. The copy's `runtime_profiles` afterwards:

```text
('01M1B9SBEEMY58719EP1YNA7V7', 'e06e92b4d4803b3b', None, None, '{}')
('01M267C2602REWPT1WE6VPJ6B4', '24988de46462017a', 8192, 1, '{"--fit": "off"}')
```

**The export, validated by SetSpec** (`freeweight results export --scope run --selector
01M267C2A8VB4PY9RBCG6WWN5B --format json`):

```text
envelope: freeweight.export 1.1 {'name': 'freeweight', 'version': '1.3.0'}
BenchmarkRunSummaryV1_1In: accepted; recomputed hash 24988de46462017a
benchmark.run_summary 1.1 JSON Schema: valid
BenchmarkRunSummaryIn (1.0): refused: Value error, runtime_profile_hash '24988de46462017a' does not match runtime_profile, which recomputes to '9c9d5a5245d1c488'.
```

The generator and `application.version` say `1.3.0` because the demonstration ran before the
version revert; nothing else in the document depends on them. The run's `summary`, as exported:

```json
{
  "aggregate_metrics": [
    {
      "aggregation": "mean",
      "dispersion": "unsupported",
      "higher_is_better": false,
      "metric_key": "gpu_energy_joules",
      "sample_count": 4,
      "unit": "J",
      "value": 124.31991502999998
    },
    {
      "aggregation": "mean",
      "dispersion": 0.0,
      "higher_is_better": true,
      "metric_key": "harness_roundtrip_success",
      "sample_count": 15,
      "unit": "ratio",
      "value": 1.0
    },
    {
      "aggregation": "max",
      "dispersion": "unsupported",
      "higher_is_better": false,
      "metric_key": "max_gpu_temperature_c",
      "sample_count": 4,
      "unit": "°C",
      "value": 39.0
    },
    {
      "aggregation": "mean",
      "dispersion": "unsupported",
      "higher_is_better": false,
      "metric_key": "mean_gpu_power_watts",
      "sample_count": 4,
      "unit": "W",
      "value": 58.6175
    },
    {
      "aggregation": "max",
      "dispersion": "unsupported",
      "higher_is_better": false,
      "metric_key": "peak_vram_bytes",
      "sample_count": 4,
      "unit": "bytes",
      "value": 2867855360.0
    },
    {
      "aggregation": "single",
      "dispersion": "unsupported",
      "higher_is_better": false,
      "metric_key": "served_context_observed",
      "sample_count": 1,
      "unit": "tokens",
      "value": 8192.0
    }
  ],
  "application": {
    "git_commit": "unrecorded",
    "name": "freeweight",
    "version": "1.3.0"
  },
  "completed_at": "2026-09-10T17:55:47.859Z",
  "created_at": "2026-09-10T17:55:40.860Z",
  "environment": {
    "cuda_version": "13.0",
    "gpu_driver_version": "580.173.02",
    "os_version": "#31-Ubuntu SMP PREEMPT_DYNAMIC Sat Aug  1 04:26:38 UTC 2026",
    "provider_kind": "llamacpp",
    "provider_version": "unrecorded"
  },
  "error_code": null,
  "error_text": null,
  "machine_fingerprint": "27da645d2ecc2e0ef849a55db23f462605643ec68bce3362393bc483db2baedf",
  "model": {
    "active_parameter_count": "unsupported",
    "architecture": "qwen2",
    "artifact_digest": "sha256:5926a692b27bc90f12815ce8326593becea3dae459cf5c250579d7ce0ffff8d7",
    "attention_heads": 12.0,
    "canonical_id": "llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b",
    "declared_capabilities": [],
    "embedding_dim": 1536.0,
    "expert_count": "unsupported",
    "family": "qwen2",
    "head_dim": 128.0,
    "identity_confidence": "digest",
    "kv_heads": 2.0,
    "layers": 28.0,
    "license_text": null,
    "max_context": 32768.0,
    "observed_at": "2026-09-10T17:54:12.748Z",
    "parameter_count": 1543714304.0,
    "provider_kind": "llamacpp",
    "provider_model_name": "Qwen2.5-1.5B-Instruct.Q8_0",
    "quantization": "Q8_0",
    "rope_config": null,
    "size_bytes": 1646573216.0,
    "sliding_window": "unsupported",
    "vocab_size": 151936.0,
    "weight_format": "gguf"
  },
  "reproducibility": {
    "fingerprint_document": {
      "application": {
        "git_commit": null,
        "name": "freeweight",
        "version": "1.3.0"
      },
      "benchmark": {
        "dataset_hashes": {},
        "manifest_hash": "sha256:14e66fbccd34259c69e307dd7b973021e031b32ffea820e9a01b59f24e0fb41d",
        "prompt_subset_hash": null,
        "suite_key": "native.echo",
        "suite_version": "1.0.0"
      },
      "environment": {
        "cuda_version": "13.0",
        "gpu_driver_version": "580.173.02",
        "os_version": "#31-Ubuntu SMP PREEMPT_DYNAMIC Sat Aug  1 04:26:38 UTC 2026"
      },
      "execution": {
        "case_selection_hash": "sha256:5c5f343bfec126c195d08eabb38e867cb84fe22299820ea4f1b753b1097e5d35",
        "effective_parameters": {
          "cooldown_seconds": 0.0,
          "gpu_index": 0,
          "idle": {
            "gpu_threshold_percent": 10.0,
            "on_timeout": "warn",
            "required_samples": 3,
            "wait_timeout_seconds": 120.0
          },
          "measured_repetitions": 3,
          "randomize_case_order": true,
          "run_timeout_seconds": 86400.0,
          "sampling": {
            "max_output_tokens": null,
            "temperature": null,
            "top_p": null
          },
          "seed": 0,
          "store_responses": false,
          "test_timeout_seconds": 600.0,
          "warmup_repetitions": 1
        },
        "gpu_index": 0,
        "multi_gpu_visible": false,
        "repetitions": 3,
        "seed": 0,
        "served_context": 8192,
        "served_context_source": "configured"
      },
      "machine_fingerprint": "27da645d2ecc2e0ef849a55db23f462605643ec68bce3362393bc483db2baedf",
      "model": {
        "artifact_digest": "sha256:5926a692b27bc90f12815ce8326593becea3dae459cf5c250579d7ce0ffff8d7",
        "descriptor_hash": "cde2181152d20995fb06806e4ef24eae9283eb47e88c3d77cc3c54782b865e6c",
        "identity_confidence": "digest",
        "provider_kind": "llamacpp",
        "provider_model_name": "Qwen2.5-1.5B-Instruct.Q8_0"
      },
      "provider": {
        "kind": "llamacpp",
        "version": null
      },
      "runtime_profile_hash": "24988de46462017a"
    },
    "reproducibility_fingerprint": "sha256:107b53e23891422a37b09b2f410da4c727512f5e5821174221463a648383b830"
  },
  "runtime_profile": {
    "adapters_registered": true,
    "batch_size": null,
    "context_size": 8192,
    "flash_attention": null,
    "gpu_layers": null,
    "keep_alive": null,
    "kv_cache_precision": null,
    "provider_options": {
      "--fit": "off"
    },
    "threads": null
  },
  "runtime_profile_hash": "24988de46462017a",
  "started_at": "2026-09-10T17:55:41.006Z",
  "status": "completed",
  "suite": {
    "category": "reliability",
    "dataset_hashes": {},
    "manifest_hash": "sha256:14e66fbccd34259c69e307dd7b973021e031b32ffea820e9a01b59f24e0fb41d",
    "prompt_subset_hash": "sha256:unrecorded",
    "prompts_used": [],
    "runner": "native",
    "suite_key": "native.echo",
    "suite_version": "1.0.0"
  }
}
```

**Before the fix**, the same kind of export (the new contract test, run first against
`freeweight 1.2.1`'s code on SetSpec editable from `main`) failed the way the audit said:

```text
baseaicore.errors.ValidationError: Run '01M266JQ6XJS0MNWF87M1YX78J' cannot be exported as benchmark.run_summary: Value error, runtime_profile_hash 'cef17259bb82d8f9' does not match runtime_profile, which recomputes to 'e06e92b4d4803b3b'.
```

## 6. For the operator

* **Versions and publish order, after the W arc.** `baseaicore 0.4.2` is already on PyPI. SetSpec
  releases first, carrying the two `1.1` minors; then FreeWeight's `setspec` range and
  `requirements/ci.lock` move to that release (the `TODO: re-pin on publish` in `pyproject.toml`)
  and FreeWeight releases. **FreeWeight's CI is red until then**: its lock installs `setspec 0.6.0`,
  which lacks `BenchmarkRunSummaryV1_1Out`; locally it runs on SetSpec editable from `main`.
  WeightRoomGym's migration `0005` rides its next release, held with the rest of the arc.
* **`freeweight.service` will migrate your real database on its next restart.** Its `ExecStart` is
  `FreeWeight/.venv/bin/freeweight serve`, that venv now holds `main` (with SetSpec editable from
  `main`), and `auto_migrate` defaults to true on SQLite — so a restart applies `0010` to
  `~/.local/share/freeweight/freeweight.sqlite3`, after the runner's backup. The migration is
  additive and the copy showed what it does; the running process was not restarted.
* **Your real FreeWeight database is still at `0009`.** Running FreeWeight from `main` and
  `freeweight db upgrade` will log `1 null, 0 false, 0 true, 0 unmatched` on it, as the copy did.
* **A reader of FreeWeight's run summaries uses `BenchmarkRunSummaryV1_1In`.** The bare name refuses
  any summary from an adapter-capable provider, with a hash message rather than a version one
  (ADR-0135's consequences).

## 7. Open for later rows

* **W8** starts from FreeWeight `0010` in `known_revisions`, as the ordering note asked.
* **The first application that reads `benchmark.result` or `benchmark.run_summary`** owes the
  consumer test ADR-0135 decision 4 describes, and is ADR-0135's revisit trigger.
* **Another hashed `RuntimeProfile` field** hits the same limit; ADR-0135 says to make it one rule
  for the profile at that point.
