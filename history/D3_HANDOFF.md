# D3 handoff — ModelRack Phase 6, `LlamaCppProvider` and process supervision

**Row:** D3 of `docs/roadmap/outstanding-work.md` §1; the start of LA1 in the adapter arc.
**Repository:** `py/ModelRack`, on `main`. **Started at** `94bf5ce` (clean; the kickoff said C5's
three commits were unpushed, but they were already on `origin/main` by the time this row began).
**Ends at** `6b23914`, five commits, working tree clean, **nothing pushed, nothing tagged, no
version bump** — this rides `0.7.0` at row H1 after P7–P8.
**Docs repository:** `docs/` at `52361f1`, one commit, unpushed.
**Model:** Fable 5.1 at the scheduled effort, run in daylight on 2026-09-03. `outstanding-work.md`
§4 requires this diff to be reviewed same-day; §11 below names where the reviewer's attention buys
the most.

---

## 1. Gate results

Interpreter: **Python 3.13.15**, `py/ModelRack/.venv` (`.venv/bin/python --version`). There is no
`python3.12` on this machine. Run from `/home/jpk/ai/suite/py/ModelRack`, each binary named out of
the venv:

```
.venv/bin/ruff format --check .        53 files already formatted
.venv/bin/ruff check .                 All checks passed!
.venv/bin/mypy src tests               Success: no issues found in 47 source files
.venv/bin/lint-imports                 Contracts: 2 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                       1265 passed, 16 skipped, 23 deselected in 5.7s
```

Coverage, under the same invocation plus `--cov --cov-report=term-missing`: **100.00 %**
statement and branch over 3 570 statements, against a **95 %** floor. `pytest-randomly` was left
on; the suite was run under four different seeds and once with `-p no:randomly`. One
order-independent race was found and fixed during the row (a zombie-process test that could
observe a child mid-`exec`; it now waits with `os.waitid(..., WNOWAIT)`), and the fixed test was
run fifteen times in a row.

The `live` marker was run for the new module only, against the real files and with no binary:

```
MODELRACK_LLAMACPP_MODELS=/home/jpk/ai/models/llm \
  .venv/bin/python -m pytest -m live tests/live/test_llamacpp_live.py -rs -s
                                       3 passed, 2 skipped
```

The three that passed are the real-artifact half (§7). The two that skipped need `llama-server`
(§8). `performance` was not run; nothing in it changed.

---

## 2. The adapter as built, against adapter-roadmap §4.1's P6 bullet

| §4.1 says | Where it is |
|---|---|
| spawn / health-wait / terminate `llama-server` | `providers/_llamacpp_process.py` — `LlamaServerSupervisor.spawn` (allocate port → write pid file → launch → poll the injected probe → kill on timeout), `.terminate` (group `SIGTERM`, grace, group `SIGKILL`), `.reap_exited`, `.sweep_orphans` |
| GGUF discovery and hashing from a configured directory, identity confidence *bound* | `providers/_gguf.py` reads headers (large arrays summarised) and hashes content; `LlamaCppProvider._entries` lists base models recursively, skipping shards, adapters, projectors and unparsable files; every identity is `ModelIdentity(LLAMACPP, name, sha256:…)` and a pinned digest the file no longer matches is `ModelNotFound(reason="digest_mismatch")` |
| profile flags: `n_gpu_layers`, cache types, flash attention, template override | `_llamacpp_wire.launch_flags` — every `RuntimeProfile` field is a launch flag; `provider_options` keys starting with `--` are extra flags (`--chat-template-file`, `--parallel`, …), the rest are request fields |
| generation + streaming over the native API | `/completion` for `prompt`; the server's chat endpoint with llama.cpp's extensions (`timings`, `system_fingerprint`, `reasoning_content`, `stream_options.include_usage`) for `messages`. Native streams end on `stop:true`, chat streams on `[DONE]`; anything else is `StreamFailed` |
| usage to ADR-0070 from the start | `_llamacpp_wire.read_completion_usage` / `read_chat_usage` — §5 |
| error translation | `_llamacpp_wire.read_error` + `LlamaCppProvider._build_message_error`: `exceed_context_size_error` → `ContextLimitExceeded` carrying the server's own `n_prompt_tokens`/`n_ctx`; `unavailable_error` → `ProviderUnavailable(reason=not_ready)`; any other message → `ProviderRejected`; transport through `_http` as before |
| recorded fixtures, version-annotated | `tests/fixtures/providers/llamacpp/` + `manifest.json` — §6 |
| risk: orphaned processes | session-leader spawn + group signals; pid file written **before** the health wait; `sweep_orphans` on every spawn and `list_resident`; `weakref.finalize` on the adapter plus `close()` |
| risk: port management | `port_range` (default 8180–8189), skipping held ports and ports live pid files claim, then the injected `port_is_free` (a loopback bind probe by default); exhaustion is `ProviderUnavailable(reason=launch_failed)` naming the range |
| risk: startup-failure diagnosis | child stdout/stderr to `state_dir/llama-server-<port>.stderr.log`; an exit during startup is `ProviderUnavailable(reason=process_exited)` with `exit_code`, `argv` and a 16 KiB `stderr_tail`; a non-answering server is killed and raised as `ProviderTimeout` with the same tail |

**The `Provider` protocol did not change.** ADR-0062 decision 1 predicted `load`/`unload`/
`list_resident` already had the right shape; the conformance suite ran unchanged against an
adapter that spawns processes, which is the test of that prediction.

Residency semantics worth knowing: several bases may be resident at once, one port each (fitting
them is the caller's ADR-0038 policy); a request whose profile differs from the running server's
launch flags **restarts** it (`keep_alive` is not a flag, so it never restarts anything — and has
no effect at all, stated in the docstring); a server that exits between calls is reported **once**
as `ProviderUnavailable(process_exited)` with its stderr, and the next call respawns.

**One refactor rode along:** the OpenAI chat-completions helpers moved from
`openai_compatible.py` into `providers/_openai_wire.py` (commit `6733538`) because the llama.cpp
chat endpoint answers in that shape. Private names only, a strict move; the OpenAI-compatible
adapter's own tests prove nothing changed.

---

## 3. The spawn seam, written for P7 and P8

**What you inject.** `LlamaCppProvider(...)` takes `launcher`, `process_table`, `port_is_free`,
`sleep`, `monotonic` and `clock`. The defaults are real (`SubprocessLauncher`,
`PosixProcessTable`, a loopback bind probe, `time.sleep`, `monotonic_ns`, `utc_now`). The fakes
live in `tests/conftest.py` and are imported with `from conftest import …`:

* `FakeLauncher` — records every `LaunchSpec` (`argv`, `port`, `stderr_path`, `model_name`),
  writes `stderr_text` to the spec's stderr path so tail-reading is real, and plays a queue of
  behaviours: `launcher.plan(lambda spec: FakeServerProcess(pid, exit_after_polls=1,
  exit_code=3))` for a crash during startup, `launcher.plan(FileNotFoundError(...))` for a
  missing binary, or nothing for a healthy server. `launcher.processes[i].crash(137)` makes a
  running server exit between calls.
* `FakeServerProcess` — `poll/wait/terminate/kill` with `terminated` and `killed` flags;
  `survives_terminate=True` forces the `SIGKILL` path.
* `FakeProcessTable` — `alive`, `command_lines`, `ignores_term`, and a `signals` log; used by the
  orphan sweep for pids the supervisor holds no handle on.
* `FakeMonotonic(step_seconds)` and `FakeSleep` — a startup timeout test needs no real time.
* The HTTP side is `respx` as for the other adapters; `test_llamacpp_adapter.py`'s `_FakeServer`
  installs `/health`, `/props`, `/completion` and `/v1/chat/completions` per port with
  request-time choices, so a test can change what a *running* server answers.

**What P8's leak test looks like with it, today:** load/unload twenty times through the adapter;
assert `launcher.processes` all `terminated`, `provider.supervisor.handles() == ()`, and
`list(state_dir.glob("*.pid.json")) == []`. "Flat memory" is the half the fake cannot give you —
that needs the real launcher and a real server, i.e. the same operator machine as §8.

**Where P7 attaches:**

* `--lora <path>` and `--lora-init-without-apply` go on the argv in
  `_llamacpp_wire.build_launch_argv` (adapters are launch-time, ADR-0062 decision 3), and into
  the **launch key** — `LlamaCppProvider._launch_key` is `json.dumps([model path, launch
  flags])`, and `ServerHandle.launch_key` is what "is this server already running the way this
  request wants?" compares. A newly registered adapter changes the key, which is exactly the
  `pending_restart` condition.
* The `lora: [{id, scale}]` request field is a chat/completion body field;
  `build_chat_body` / `build_completion_body` are where it is added, and `request_options` already
  merges non-flag `provider_options` last, so an operator can reach it today by hand.
* `LlamaCppProvider._read_props` runs once per spawn and is where `GET /lora-adapters` belongs,
  to record which adapters the server actually registered on `ServerHandle`.
* `ProviderCapabilities` gains `adapter_hot_swap` in P7 — the matrix generator and its test fail
  loudly on a flag without a note, by design.
* `_ensure_server` is where "restart at the next natural idle, never mid-work" lands. **Today
  a profile change restarts immediately**, and a stream in flight on another thread would see
  `StreamFailed(ProviderProtocolError)` when the connection drops. P6 has no in-flight counter;
  P7's `pending_restart` should add one before it adds any other reason to restart.
* The cache-correctness conformance test (prefix under A never reused for B) is a `live` test
  by nature; the server's own rule is in `server-context.cpp`: a slot whose `lora` set differs
  from the task's clears its prompt cache (`lora_should_clear_cache`). Worth asserting from
  `timings.cache_n` == 0 on the first request after a switch.

---

## 4. The digest: what it costs, and the decision

**Measured on this machine, 2026-09-03:** header parsing 140–445 ms per file (the reader skips
the 150 k–260 k-entry vocabulary arrays rather than loading them); one full-content sha256 of the
smallest model, 5.63 GB, took **6.4 s (0.88 GB/s)**; the five files total 39 GB, so a cold first
discovery of the whole directory is **~45 s** at that rate, page cache permitting.

**Decision.** The identity is the full-content sha256 the contract names; nothing cheaper was
substituted. What is cached is the *result*, keyed by path **and** `ArtifactStamp` (size,
mtime_ns, inode, device), in an injectable `DigestStore` — in-memory by default. A changed file
has a different key and simply misses; `refresh=True` re-hashes regardless. The stamp is
deliberately **not** a TTL: `cache.py`'s TTL is the precedent for *metadata*, and it is used for
the parsed headers (with a stamp check on every hit so a replaced file is never described from its
predecessor's header), but a content hash does not go stale with time, only with content — a TTL
on it would re-hash 40 GB every five minutes in a long-running LoadCoach for no information gained.

**Why in-memory by default.** Spec §3 ("no persistence") and §10 ("never survives the process")
are still in force, and a package-owned cache file is a decision the spec has not made. So **the
first discovery in every process hashes every unhashed file** (`list_models`), and `resolve` /
`inspect_model` hash only the file they name. A long-running server pays ~45 s once. A CLI that
starts fresh each run (FreeWeight) pays it every time unless its application injects a store that
persists in its own data root — the spec now says so (§10). That is an **H2/H4 item**: LoadCoach
and FreeWeight each need a `DigestStore` implementation (a small table or a JSON file under their
data root); the interface is `get(key) -> str | None` / `put(key, digest)`.

**Known gap, stated rather than hidden:** a file rewritten in place with the same size and a
restored mtime keeps its inode and would hit the stale digest. That is deliberate tampering, not
any ordinary re-download or replace, and `refresh=True` exists for it.

**Not a contract problem.** I do not think the identity contract is wrong; ~45 s once per process
for digest-bound identity over 39 GB is a fair price, and it is the *only* reason this adapter's
identities are better than Ollama's tags.

---

## 5. Usage: the shapes declared, and `cache_detail` is **not** `None`

`TestLlamaCppProviderConformance.usage_shapes` declares all three cases over the chat fixtures:

| Shape | Fixture | Result |
|---|---|---|
| `NO_CACHE_DETAIL` | `chat_complete.json` (`cached_tokens` 0, `timings.cache_n` 0) | input 21, output 12, cache read 0, cache write 0; `total_tokens` 33; `estimate_cost` totals |
| `CACHE_DETAIL` | `chat_complete_cached.json` (prompt 21, cached 8) | input 13, cache read 8, sum 21 |
| `NO_USAGE_OBJECT` | `chat_complete_no_usage.json` | every class `UNSUPPORTED` |

`cache_detail=CacheDetailShape(prompt_tokens=21, cached_tokens=8)` — the same arithmetic the
OpenAI-compatible and fake classes are held to. It is declared, not `None`, because llama-server
**does** report cached input: `usage_json_oaicompat()` in `tools/server/server-task.cpp` writes
`prompt_tokens_details.cached_tokens` from `n_prompt_tokens_cache`, and
`server_slot_stats::to_json()` in `server-common.cpp` writes the same counter as
`timings.cache_n`. Declaring `None` would have exempted the one adapter whose server reuses a KV
cache across requests from the case that catches double-billed cached input.

The rule as implemented, per response, on both wire shapes (`_llamacpp_wire` docstring has the
table):

* counts present and a readable cached figure ≤ the prompt total → `input = total − cached`,
  `cache_read = cached`, `cache_write = 0` (no field in either shape can charge a write);
* counts present and **no cached-input field at all** → `input = total`, both cache classes `0`
  — a build that predates `timings.cache_n` cannot bill the class, ADR-0070 rule 1's first
  sentence; the consequence is Ollama's: input is the prompt submitted, never less;
* counts present and a cached figure that is unreadable or larger than the total → **both**
  `input_tokens` and `cache_read_tokens` `UNSUPPORTED` (C5's decision (c): the two halves of one
  subtraction), `output_tokens` still reported;
* no counts at all → every class `UNSUPPORTED`.

Precedence on the chat shape: `timings.cache_n` if the response carries timings, else
`prompt_tokens_details.cached_tokens`. They are the same server-side counter.

**The trap, and the assertion that guards it.** The native response also carries
`tokens_cached`. It is **not** the cached prefix: `send_final_response` sets it to
`slot.prompt.n_tokens()`, the slot's whole cache after generation — prompt plus output (33 for a
21-token prompt and 12-token answer). Read as `cache_read_tokens` it would bill every call as a
cache hit for its own output. It is never read; the fixtures carry it at its real value and
`test_usage_on_the_native_shape_never_reads_tokens_cached` pins it.

---

## 6. Fixtures added, and what each proves

All under `tests/fixtures/providers/llamacpp/`, all **representative, not captured** — there is no
llama.cpp on this machine — and the manifest says so plainly. They represent build **`b10792`**,
the newest release tag on 2026-09-03, and were written to the server's *serialization code* at
that build (`server-task.cpp`, `server-common.cpp`, `server-context.cpp`, fetched and read that
day), not to the README alone. Streaming framing in particular came from source: every chunk is a
`data:` event (`format_oai_sse`), a mid-stream error is `data: {"error": …}`, `[DONE]` is written
only for the OpenAI-shaped streams and never for `/completion`, and the final native stream chunk
carries `content: ""` (cleared in stream mode).

| Fixture | Proves |
|---|---|
| `completion.json` | The native shape; `tokens_cached` 33 = 21 + 12, ignored |
| `completion_cached.json` | `cache_n` 8 of 21 → input 13 |
| `completion_no_cache_n.json`, `completion_no_timings.json` | No cached-input field → cache classes `0`, input the whole prompt |
| `completion_no_counts.json` | This shape's absent usage object → all `UNSUPPORTED` |
| `completion_limit.json` | `stop_type: limit` → `LENGTH` |
| `completion_stream*.sse` | One event per token, `stop:true` terminal with empty content and full timings; truncated and in-band-error variants |
| `chat_complete*.json` | The chat shape with `prompt_tokens_details`, `timings`, `system_fingerprint`; cached, no-usage, unreadable-details, reasoning and tool-call variants |
| `chat_stream*.sse` | Deltas, finish chunk, usage chunk with empty `choices` (only because the adapter sends `stream_options.include_usage`), `[DONE]`; cached, no-usage, truncated, error, reasoning and tool-call variants |
| `error_*.json` | `format_error_response`'s shape; the context-overflow one carries `n_prompt_tokens`/`n_ctx` |
| `health_*.json`, `props*.json` | The two health answers; `/props` with `build_info` and `default_generation_settings.n_ctx` |

The unit tests write their own GGUF files through `write_gguf` in `conftest.py` (a structurally
complete header plus a few bytes of "weights"), so the default suite depends on no real model.

---

## 7. Verified on this machine against the real artifacts

`tests/live/test_llamacpp_live.py::TestRealArtifacts` and a scratch script, over
`/home/jpk/ai/models/llm` (five files, 5.6–9.7 GB):

* every file parses as GGUF v3, kind `model`, and yields a full descriptor: architectures
  `qwen35`, `gemma3`, `gemma4`, `qwen3`; layers, context, head dims, vocabulary sizes, `Q4_K_M` /
  `Q6_K`, exact parameter counts from the tensor records (8.95 B, 11.77 B, 11.91 B, 14.77 B);
* `gemma4`'s `attention.head_count_kv` is a per-layer array whose entries differ → `kv_heads`
  is `UNSUPPORTED` with the array kept in `raw`, exactly as designed;
* `resolve` on the smallest model returns a digest-bound identity equal to `hashlib`'s;
* the timing in §4.

---

## 8. What could not be verified without `llama-server` — operator steps

None of the following has been observed against a running server. Each is a `live` test or a
step the operator runs before the LA1 exit demonstration:

1. **The live journey** — `TestRealServer`: health, load (a real startup time), resident with the
   served context from `/props`, chat generate with real counts and a real `cache_read_tokens`,
   stream, native completion, unload, and **no process left** by pid. Run:
   `MODELRACK_LLAMACPP_MODELS=~/ai/models/llm .venv/bin/python -m pytest -m live
   tests/live/test_llamacpp_live.py -rs -s` with `llama-server` on `PATH` (or
   `MODELRACK_LLAMACPP_SERVER=/path/to/llama-server`). Not beside a FreeWeight benchmark.
2. **Flag acceptance on the installed build** — `--alias`, `--jinja`, `--no-webui`, `--host`,
   `--port`, `--ctx-size`, `--n-gpu-layers`, `--cache-type-k/v`, `--flash-attn on|off`,
   `--threads`, `--batch-size` are all in the README's table at `b10792`; an older or newer build
   that rejects one will exit at startup, and the captured stderr will say which.
3. **The streaming shapes as observed**, not as read from source: the usage chunk arriving on
   `include_usage`, `[DONE]` after it, the native `stop:true` chunk with empty content.
4. **`tokens_cached` semantics as observed** — the source is unambiguous, but one request pair
   with a shared prefix would confirm `cache_n` moves and `tokens_cached` is prompt + output.
5. **Kill-tree grace against a real server mid-generation** (20 s default) and **GPU memory
   release timing** after `SIGTERM` — a respawn immediately after an unload might race the
   driver's release on a 16 GB card. This is P8's leak-test territory, and the reason "flat
   memory" cannot be claimed from here.
6. **`/props`'s `n_ctx` when `--parallel` > 1** — the served context is per slot; the adapter
   reports what `/props` says and passes no `--parallel` unless `provider_options` does.
7. **`-ngl` default `auto`** on the installed build with the 5060 Ti — a default profile sends no
   `--n-gpu-layers`; whether that offloads everything is the build's decision, and a FreeWeight or
   LoadCoach profile should set it explicitly.
8. **The LA1 exit demonstration** itself (one base, three registered adapters, twenty
   generations, zero base loads) is P7's to build and the operator's to run.

---

## 9. Findings for P7, H2/H4 and the reviewer (nothing changed in passing)

1. **`OpenAICompatibleProvider` sends `repetition_penalty`; llama-server reads only
   `repeat_penalty`** (verified in `server-common.cpp`'s parameter parsing, which copies unknown
   keys but the sampler reads `repeat_penalty`). Against a llama-server reached through the
   OpenAI-compatible adapter, the penalty is silently ignored. Not changed here: that adapter
   targets several servers and vLLM does read `repetition_penalty`. The llama.cpp adapter sends
   `repeat_penalty`.
2. Because llama-server writes `prompt_tokens_details.cached_tokens`, the **OpenAI-compatible
   adapter pointed at a llama-server already reconciles cache reads correctly** after C5 — a
   useful cross-check for anyone comparing the two paths.
3. `state_dir` is **required** (keyword-only, no default): the constructing application names a
   directory in its own data root. LC-E1's `[providers.<name>]` for `kind = "llamacpp"` needs
   `model_directory`, `state_dir`, and optionally `server_path`, `port_range`,
   `startup_timeout_seconds`.
4. `DigestStore` persistence is an application item (§4) for H2 and H4.
5. `thinking_control` is `False`; the server *reports* reasoning (`reasoning_content` → `thinking`)
   and `chat_template_kwargs: {"enable_thinking": false}` is one `provider_options` entry away,
   but declaring the flag needs a test against a thinking model.
6. Sharded GGUFs (`-00001-of-00003.gguf`) are skipped at discovery with a DEBUG log — their
   identity is a hash over several files and llama-server takes only the first. If a sharded base
   ever arrives, that is a small P8 item.
7. `ProviderHealth.base_url` for an idle supervised provider is `http://127.0.0.1:<first port>` —
   an address nothing has been contacted at yet, with the detail saying "no server running".
   `ProviderHealth` requires a non-empty URL; a reviewer may prefer a different spelling.
8. Profile restart has no in-flight guard (§3).
9. `list_resident` reports `vram_bytes` and `total_bytes` `UNSUPPORTED`: llama-server exposes no
   memory figure this adapter reads. LoadCoach's residency display will show unknowns for
   llama.cpp bases until someone decides whether `/metrics` or `nvidia-smi` (SweatMeter's job)
   should fill them.
10. The docs repo's `roadmap/outstanding-work.md` was **modified but uncommitted at session
    start**: a re-padding of the master table (column alignment and a `| ------ |` separator row),
    content byte-identical once whitespace, dashes and pipes are stripped. Restored with
    `git checkout --` per `CLAUDE.md`. This is the "markdown reflow" mutation class again, and a
    table-formatting editor extension (format-on-save) is the most likely cause — worth checking
    the VS Code settings before the next session works in `docs/`.

---

## 10. Commits

`py/ModelRack`, `main`, all unpushed (five ahead of `origin/main`; C5's commits were already there):

```
6b23914 docs: Phase 6 in the development plan, spec amended for ADR-0062, changelog
4a5ddab test(live): the llama.cpp live journey and real-artifact discovery
ab70f94 feat(providers): LlamaCppProvider — supervised llama-server, digest-bound identity
2a523c6 feat(providers): GGUF header reading and the llama-server supervision seam
6733538 refactor(providers): share the OpenAI chat-completions wire helpers
94bf5ce (C5) docs(changelog): the ADR-0070 usage-rule behaviour change
```

`docs`, `main`, unpushed: `52361f1 docs(modelrack): Phase 6 — LlamaCppProvider; spec amended
for ADR-0062; D3 ops item`. Both mirrored files (`spec.md`, `development-plan.md`) verified
byte-identical with `cmp`. `standards/gold-standards.md` and `roadmap/outstanding-work.md` are
workspace-only documents.

The docs gap the kickoff named is closed: `development-plan.md` has a Phase 6 section in the
established shape, transcribed from §4.1, and Phase 5's Deferred line no longer defers it. The spec
additionally records what the accepted ADR-0062 implied but A1 had not carried into it (§2, §3, §7,
§10, §12, §16, §18, §20, §21) — consequences of an accepted decision, not new ones.

---

## 11. Where the same-day review should look

* `_llamacpp_wire._usage` and `_cached_from_timings` — the three-row rule, and in particular the
  "no cached-input field → `0`" row, which is the one a later session could weaken to
  `UNSUPPORTED` (making every old-build response a floor) or strengthen to a derivation from
  `prompt_n` without any test going red.
* `LlamaCppProvider._ensure_server` — restart-on-profile-change and report-a-crash-once.
* `LlamaServerSupervisor._recover` — the sweep's decision table: owner alive → leave; pid gone →
  remove; command line readable and different → remove, don't kill; otherwise kill. The "command
  line unreadable → kill" arm is the one that could be argued either way.
* `_llamacpp_wire.launch_flags` — the `--` prefix convention on `provider_options`.
* Commit `6733538` is a pure move; a reviewer can `git show --stat` it and skip the bodies.

---

## 12. Before the next session

1. **Push `main`** for `py/ModelRack` (`6b23914`, five commits) and for `docs/` (`52361f1`, one
   commit); confirm CI green. The VSCode askpass IPC env is needed for `git push` here.
2. **Review the diff same-day** (§11).
3. **Install llama.cpp on the reference machine** — a CUDA build of `llama-server`, on `PATH` or
   named by `MODELRACK_LLAMACPP_SERVER` — and run the live module (§8 item 1) **before** P7 (row
   F3) builds on this adapter, and certainly before the LA1 exit demonstration at H1. Not beside a
   FreeWeight benchmark run.
4. **This does not publish.** ModelRack stays at `0.6.0`; everything since `a0f9328` rides
   **`0.7.0` at row H1** after P7 and P8. No tag, no `__about__.py` bump.
5. Row **F3 (P7)** attaches at the points in §3. Row **H1 (P8)** owns the leak tests against the
   real launcher, the in-flight guard if P7 has not added it, and the docs volume (the quickstart
   has no llama.cpp section yet — deliberately left for publication).
6. FreeWeight and LoadCoach both resolve `modelrack` editable against this working tree
   (C5 handoff §7); this row adds a module and three enum members and changes nothing they
   import, but their local suites now run against `6b23914` while their CI installs `0.6.0`.

---

## 13. Post-interview addendum (same day, 2026-09-03 evening)

The operator was interviewed after §1–§12 were written; what follows supersedes those sections
where they disagree. **Everything below is pushed and CI-green** (`95f320c`, `a02a041` and `dead52a` on
ModelRack, `aab9d85` and `98a236f` on docs).

### Decisions taken

| Question | Decision | Done |
|---|---|---|
| Install llama.cpp | Build `b10792` from source with CUDA 13.1 for the 5060 Ti (sm_120) | `~/ai/tools/llama.cpp`, `~/.local/bin/llama-server` → `build/bin/llama-server` |
| Push now? | Yes, both `main`s, watch CI | Pushed; CI green for `6b23914`, `a02a041` |
| Digest persistence | **Persist to JSON, clearable, with an ADR** — "no reason for ModelRack to be in memory when not running an app" | ADR-0071; `JsonFileDigestStore` is the default; `clear_digest_cache()` |
| Profile-change restart | Keep immediate restart; P7 adds the in-flight guard | unchanged |
| Live journey | Run it now | ran, passed — below |
| `repetition_penalty` | Send both keys from the OpenAI-compatible adapter | `a02a041` |
| Orphan sweep, cmdline unreadable | Kill | unchanged |

### The downsides of a persisted digest file, as asked

Beyond "not in spec" (now amended): (1) two applications must not share a `state_dir`, or
they share a cache file — and pid files — which the boundary rules forbid anyway; (2) an
operator can edit the file into a wrong identity until `refresh=True` or a clear (the trust
boundary of any cache in the app's data root; the stamp still refuses a file whose bytes changed);
(3) a same-size, same-mtime, same-inode rewrite hits the stale entry (unchanged from before);
(4) the format is one more thing this package owns and versions. Concurrent writers cannot
corrupt it (temporary sibling + atomic replace, read-merge-write); a race loses at most one entry.
All four are in ADR-0071's Consequences.

### The CUDA build, and a workaround to remember

CUDA 13.1's `crt/math_functions.h` declares `rsqrt`/`rsqrtf` without `noexcept`; glibc 2.43
declares them with it, and nvcc's front end refuses the pair ("exception specification is
incompatible") — llama.cpp issue #19100, closed *wontfix* because the fix is to NVIDIA's headers.
The accepted fix patches `/usr/local/cuda-13.1/…/crt/math_functions.h` with `sudo`. **I did not
touch the system toolkit.** Instead a user-local copy of the CUDA include tree lives at
`~/ai/tools/cuda-13.1-include-overlay` with the four declarations patched, and the build was
configured with `CUDAFLAGS=-I<overlay>` and `-DCMAKE_CUDA_FLAGS=-I<overlay>` so nvcc resolves
`cuda_runtime.h` from the overlay first. Delete the overlay once NVIDIA ships fixed headers.
Other build choices: `-DCMAKE_CUDA_ARCHITECTURES=120`, static libs, `LLAMA_CURL=OFF`, examples and
tests off, an rpath to `/usr/local/cuda-13.1/lib64` so the binary runs without `LD_LIBRARY_PATH`.
The clone is shallow, so `llama-server --version` and `/props`'s `build_info` say **`b1-c5a5535`**
rather than `b10792-…`; `git fetch --unshallow --tags` and a rebuild would fix the number if it
ever matters (the commit hash is the real identity).

### The live journey — observed, not read from source

`MODELRACK_LLAMACPP_MODELS=/home/jpk/ai/models/llm MODELRACK_REQUIRE_LLAMACPP=1
.venv/bin/python -m pytest -m live tests/live/test_llamacpp_live.py -rs -s` → **5 passed in
21.5 s**, GPU idle before and after, no `llama-server` process left, no pid file left.

```
sha256 of Qwen3.5-9B-…Q4_K_M.gguf: 5.63 GB in 2.5 s (2.27 GB/s, page cache warm)
load_ms=1401  build=b1-c5a5535  finish=length  text_chars=0  thinking_chars=1064
tokens: in 18  out 256  cache_read 0     prompt_ms=57.4  decode_ms=3510.9  (≈73 tok/s)
stream: 256 deltas, cache_read 14 (second request, shared prefix), ttft_ms=89
```

What that settles: every streaming shape §8 listed as "read from source, not observed" has now
been observed — `data:` framing, the usage chunk on `include_usage`, `[DONE]` on chat, the
native `stop:true` chunk; `/props` reported `n_ctx` 4096 exactly as launched; `build_info`
reached `provider_version`; and **`timings.cache_n` moved on the second request** (14 of 18
prompt tokens reused), so `cache_read_tokens` 14 and `input_tokens` 4 is the ADR-0070
cache-detail case observed live rather than declared. Kill-tree worked against a real server
that had just decoded for 57 s (the first run, below): SIGTERM, prompt exit, GPU memory back to
599 MiB.

**The first run failed on my own assumption, and the failure is a finding.** With no output cap,
Qwen3.5 — a *thinking* model — spent 57 s and its entire 4096-token budget in
`reasoning_content` and answered with an empty `text`; `finish_reason` was `length`. The adapter
carried the reasoning into `thinking` correctly. The test now caps output at 256 tokens and
accepts reasoning as output. For consumers: a thinking model behind this adapter needs
`max_output_tokens` (or `provider_options={"chat_template_kwargs": {"enable_thinking": False}}`,
which llama-server accepts) or every answer is a `length` with no text. This is the concrete case
behind the `thinking_control=False` finding in §9.

### What is still not verified

* The LA1 exit demonstration (P7's).
* Flat memory across twenty load/unload cycles against the real server (P8's leak test); one
  cycle freed the GPU completely.
* `--parallel` > 1 and `/props`'s per-slot `n_ctx`; `-ngl auto`'s behaviour was fine here (the
  5.6 GB model was fully offloaded — 3.5 s for 256 tokens is a GPU speed).

### Commits since §10

```
ModelRack  95f320c feat(providers): persist artifact digests in state_dir/digests.json (ADR-0071)
           a02a041 fix(providers): send repeat_penalty beside repetition_penalty
           dead52a test(live): cap the journey's output and accept reasoning as output
docs       aab9d85 docs(adr): ADR-0071 — ModelRack persists artifact digests in a JSON file …
           98a236f docs(roadmap): D3 pushed and live-verified; llama.cpp installed
```

§12's "before the next session" list shrinks to: review the diff (§11, plus ADR-0071 and
`JsonFileDigestStore`); ModelRack stays at `0.6.0` until H1; P7 attaches at §3.
