# H1, second sitting — the LA1 exit, live; `modelrack 0.7.0` prepared

**Row:** H1 of `docs/roadmap/outstanding-work.md` §1, resumed. **Date:** 2026-09-05, afternoon.
**Model:** Fable 5.1, interactive — this sitting began as an interview over `H1_HANDOFF.md` and
`H2_HANDOFF.md` and continued into the work the interview decided.
**Repositories:** `docs`, `py/ModelRack`. Both clean at the start; both ahead of `origin` and **not
pushed** (standing instruction of 2026-09-04). `py/BaseAiCore` and `LoadCoach` were untouched.
**Interpreter:** ModelRack `.venv/bin/python` — Python 3.13.15. The training venv is Python 3.13.15
too, at `~/ai/tools/lora-train/.venv`.

---

## 1. The headline

**Gate G is done. The LA1 exit ran live on the reference machine and passed — one base, three
adapters, twenty alternating generations, one load, flat memory — and I17's canary answered one
prompt three different ways.** `modelrack 0.7.0` is bumped, its changelog closed, its wheel built
and verified in a clean venv with `demo_modelrack.py`, and the release commit made. **Not tagged,
not published, not pushed.**

Two things the exit found that the fake launcher could not have:

1. **`llama-server` b10792's CUDA build leaks ~14 MiB of host memory per adapter-set change while
   CUDA graphs are on.** Unbounded (sixty switches, +700 MiB), the same rate on a two-state toggle,
   flat for a fixed adapter, flat on CPU, unaffected by `--cache-ram 0`, and flat with
   `GGML_CUDA_DISABLE_GRAPHS=1` at the same generation speed. ModelRack now sets that variable as
   an environment **default** on every launch that registers adapters (§5). Upstream `master`
   (`b10792-28-g74a7c89`) has no change to the adapter or CUDA-graph paths.
2. **The adapter artefacts exist now**, produced outside the suite as ADR-0061 rule 6 requires
   (§4). Three exits were waiting on them: LA1 (this row), H2's gate I, and H4's I18.

## 2. The interview — eight decisions, all taken

| # | Question (from the two handoffs) | Decided |
|---|---|---|
| 1 | How to get adapter artefacts | Train locally on a **new small base** (`Qwen2.5-1.5B-Instruct`), not on one of the four existing 9–14 B bases, not from a download |
| 2 | Who does it | Claude, this session; tooling under `~/ai/tools/lora-train/`, outside every repository |
| 3 | `modelrack 0.7.0` while LoadCoach pins `>=0.7` | **Hold** until gate G is proven (now done); LoadCoach CI stays red until 0.7.0 is on PyPI; **no `0.7.0b1`** |
| 4 | `register_adapters()` has no inverse (H1 §8) | **The sequence passed is the complete set**; a name absent from it is retired at the next idle; no `unregister` method. Built (§6) |
| 5 | LoadCoach 1.1 migrations (H2 §7) | **One per gate**, 0009–0012 |
| 6 | ADR-0078's `output.tool_calls_assembled` | **Gate H, as planned** — not pulled forward |
| 7 | Stray BaseAiCore tag `v0.5.0` on `origin`, pointing at the 0.4.1 commit `f2cdbf0` | **Operator deletes it** before tagging `v0.4.2` (`release.yml` triggers on `v*.*.*`) |
| 8 | Order of the next sitting | Artefacts → H1 gate G → `0.7.0` prep → H2 gates D–G |

Recorded in memory as `h1-h2-decisions-2026-09-05` so no later session re-asks them.

## 3. Gate G — the evidence

Run with `~/ai/tools/lora-train/gate-g.sh` (sets the four environment variables and runs the live
file). Final run, with **no** `GGML_CUDA_DISABLE_GRAPHS` in the parent environment, so the
package's own default is what was exercised:

```
load_ms=766 build=b1-c5a5535 finish=stop … cache_read 0
stream: … cache_read 36 (second request with a shared prefix)
canary cache_read by subject: {'canary-0': 0, 'canary-1': 0, 'bare': 0}
  canary-0: ' Stores key-value pairs; speeds up lookups by storing frequently used data.\nKV pair storage; …'
  canary-1: ' Certainly, let me walk through this carefully. A Key-Value (KV) cache stores data where each piece '
  bare:     ' A KV cache stores key-value pairs that can be quickly looked up to speed up access times for freque'
I16: pid=2712516 load_ms=754 loads_started=1 generations=20 wall_ms min/median/max=251/253/284
I16 rss_mib per generation: [762, 765, 769, 771, 774, 776, 776, 776, 776, 776, 777, 778, 778, 778, 778, 778, 778, 778, 778, 778]
8 passed in 28.09s
```

**I16 is a new live test**, `TestWarmBase::test_twenty_alternating_generations_load_the_base_once`,
because the file had the canary but nothing for the exit's own claim. It asserts zero base loads
from three independent witnesses — the server pid answering every generation, exactly one `load`
`REQUEST_STARTED` event seen by the `on_event` observer, and no generation's wall time reaching
the one measured load — and asserts the resident set flat once every adapter has been applied
(the baseline is the reading after the third generation, because `llama-server` allocates on first
use). It skips naming the third adapter it needs. The canary now prints its three answers, so a
person can read the difference rather than trust an inequality.

`cache_read` is `0` on every adapter-switching generation. That is correct, not a gap: every switch
clears the slot's prefix (`lora_should_clear_cache`), which is exactly what I17 requires; the
journey's second request with the same prefix and no switch shows `cache_read 36`.

## 4. The artefacts, and how they were made

| Artefact | Path | sha256 |
|---|---|---|
| Base, Q8_0, 1.6 GB | `~/ai/models/llm/Qwen2.5-1.5B-Instruct.Q8_0.gguf` | `5926a692…ffff8d7` |
| Adapter `terse` (rank 16, f16, 37 MB) | `~/ai/models/adapters/llm/qwen2.5-1.5b-instruct-terse.gguf` | `c5826292…f586296` |
| Adapter `verbose` | `~/ai/models/adapters/llm/qwen2.5-1.5b-instruct-verbose.gguf` | `4af980ac…227196` |
| Adapter `pirate` | `~/ai/models/adapters/llm/qwen2.5-1.5b-instruct-pirate.gguf` | `35bd9f9f…5c94e0` |

**Adapters live outside the models directory on purpose**: `LlamaCppProvider` discovers every
`.gguf` under `model_directory` as a base, and an adapter GGUF there would be listed as one.

`~/ai/tools/lora-train/` holds the whole recipe, none of it in a repository: `setup.sh` (venv,
torch cu128, peft, the HF download), `train.py` (self-distillation — the base answers eighty
questions under each style's system prompt, then a LoRA is trained on question→answer with the
system prompt removed, three surface forms per pair so the style holds on a raw `/completion`
prompt with no template), `questions.txt`, `convert.sh` (`convert_hf_to_gguf.py --outtype q8_0`,
`convert_lora_to_gguf.py --outtype f16`), `gate-g.sh`, and the three probe scripts from §5. The
HF weights are under `base/`, the PEFT checkpoints under `out/`. Re-running `train.py` produces
different bytes (no seed on CUDA kernels), hence different subjects; the digests above are the
ones gate G ran against.

The base is a fifth model beside the four "heretic" ones. Training against one of those would have
meant fetching 9–14 B of HF weights and a QLoRA stack for no gain: F3 §6 says any instruct model
llama.cpp serves qualifies, and the interview chose the small one.

## 5. The leak, and what ModelRack does about it

The first I16 run failed only on the flat-memory assertion: 782 → 1050 MiB across twenty
generations, ~14 MiB per switch, linear. Attribution, by elimination, with the scripts kept in
`~/ai/tools/lora-train/`:

| Scenario (`rss_probe.py` through ModelRack; `server_probe*.sh` against `llama-server` directly) | RSS |
|---|---|
| No adapters, same prompt ×20 | flat |
| No adapters, prompt varies ×20 | +1.4 MiB/gen — the host prompt cache, bounded by `--cache-ram` |
| Adapters, fixed `a0` ×20 | flat |
| Adapters, alternating ×20 | **+14 MiB/gen** |
| Server direct, alternating, `--cache-ram 0` | +14 MiB/gen — not the prompt cache |
| Server direct, alternating ×60 | 923 → 1616 MiB — unbounded |
| Server direct, two-state toggle ×40 | same rate — any change, not the count |
| Server direct, alternating, `-ngl 0` | flat — CUDA backend only |
| Server direct, alternating, `GGML_CUDA_DISABLE_GRAPHS=1` | **flat** (744 → 745 over 30) |

The compute graph changes with the adapter configuration and each CUDA-graph re-capture is kept.
Fix in ModelRack (`bdc1331`): `LaunchSpec.env_defaults` — `(name, value)` pairs the launcher
applies **under** the parent's environment (`{**defaults, **os.environ}`), so an operator's
explicit setting always wins and ModelRack still reads no environment variable of its own —
and `adapter_launch_env()` returns `GGML_CUDA_DISABLE_GRAPHS=1` only when the launch registers
adapters. A server without adapters carries no defaults and inherits its environment exactly as
Phase 6 did. Cost: none measurable here (median 253 ms against 257 ms). Spec §18 records the
evidence beside the pinned build and says to drop the default when the leak is gone upstream.

The unit tests cover both halves: the adapter launch carries the default and the bare launch
carries nothing; the real `SubprocessLauncher` applies a default to a child and yields to a
parent that already set the name.

## 6. `register_adapters()` takes the complete set (`9bb3e98`)

The interview's decision 4. The body is one line — `self._registrations = {r.name: r for r in
adapters}` — because `_folds_in_at_idle` already compares what the provider *would* launch with
against what the server *did* launch with, and `_state_for` already iterates the held set, so a
dropped name leaves `list_adapters()` at once and forces a restart at the next idle with no other
change. Tested by launching with one adapter, registering `()`, and asserting the next request
restarts without `--lora`, sends no `lora` field, and refuses the old name. Protocol docstring,
spec §10 and changelog say the same thing. Unreleased since Phase 7, so no published caller moves.

**H2's `adapters scan` can now say "the directory is the truth"** by passing the whole reviewed
set every time.

## 7. Commits

**py/ModelRack** (4, on top of H1's 6 — **10 ahead of `origin`**): `9bb3e98` complete-set
registration; `2489872` the I16 live test and the canary's printed answers; `bdc1331` the CUDA-graphs
default; `4752186` `chore(release): modelrack 0.7.0`.

**docs** (3 — **3 ahead of `origin`**): `672c4fe` spec §10 on `register_adapters()`; `30124c5`
spec §18 on the leak and the default; and the row update carrying this handoff.

Every path staged by name. No push, no push dry-run, no tag, no publish. Mirrors `cmp`-proved
byte-identical at each docs commit.

Gate at the release commit (`.venv/bin/python -V` → Python 3.13.15): ruff format/check clean,
mypy clean over 51 files, import-linter 2 kept, **1426 passed, 16 skipped**, coverage 99 % (the
four missed lines pre-date this sitting). Live file: **8 passed** (§3).

## 8. Things that turned out not to be as the handoffs or the state suggested

1. **Three of the four repositories were already pushed.** `docs`, `py/BaseAiCore` and
   `LoadCoach` were level with `origin` at the start; only ModelRack's six commits were not.
   BaseAiCore's CI is green; LoadCoach's is red, as H2 §5 said it would be.
2. **BaseAiCore has a stray `v0.5.0` tag on `origin`**, pointing at `f2cdbf0` — the same commit as
   `v0.4.1`. Nothing 0.5.0 reached PyPI. Decision 7.
3. **ModelRack's `requirements/ci.lock` still pins `baseaicore==0.4.0`** while `pyproject.toml`
   now requires `>=0.4.2`, and CI installs the package `--no-deps` on top of that lock. **ModelRack
   CI will be red on push** until `baseaicore 0.4.2` is on PyPI *and* the lock is recompiled
   (`pip-compile … -P baseaicore`, `--no-emit-index-url` — E5's notes apply). H1 moved the floor
   twice without touching the lock; it could not have recompiled against an unpublished version.
4. **The LA1 exit wants three adapters, not two.** F3 §6 and the canary say two; adapter-roadmap
   §3 and development-plan Phase 8 criterion 5 say three. Three were trained; the canary still
   uses the first two.
5. **Flat memory was not flat.** The assertion the plan called "the one the injected launcher
   cannot make" was the one that failed, and it was right to (§5).

## 9. For the operator, in order

1. `cd py/BaseAiCore && git tag -d v0.5.0 && git push origin :refs/tags/v0.5.0` (decision 7).
2. Push `docs` and `py/ModelRack`. Expect ModelRack CI **red** on the lock (§8.3).
3. Tag and publish **`baseaicore 0.4.2`** (`v0.4.2`; `release.yml` runs on the tag).
4. In ModelRack, recompile `requirements/ci.lock` against the published 0.4.2, commit, push; CI
   should go green.
5. Tag **`v0.7.0`** on ModelRack's release commit and publish; verify the published wheel in a
   clean venv and run `demo_modelrack.py` against it (the local-wheel verification is done).
6. LoadCoach's pins (`baseaicore>=0.4.2,<0.5`, `modelrack>=0.7,<0.8`) then resolve from PyPI; drop
   the two `TODO: re-pin on publish` comments and watch its CI go green.
7. Then **H2 gates D–G** (Opus 5 · xhigh), with the decisions of §2 in hand and the artefacts of
   §4 for gate I. `loadcoach adapters scan` over `~/ai/models/adapters/llm/` is the first thing to
   try — the base must be a registered llama.cpp provider's model, and the manifests it drafts
   will name `Qwen2.5-1.5B-Instruct.Q8_0`.

## 10. Small things, none blocking

* Re-run `~/ai/tools/lora-train/server_probe2.sh` after any llama.cpp upgrade; if the "graphs
  disabled" row and a graphs-enabled run both stay flat, drop `ADAPTER_LAUNCH_ENV_DEFAULTS` and the
  spec §18 paragraph with it.
* `openai_compatible.py:836`'s post-loop cancellation pragma is still there (H1 §8); untouched.
* The `think=False` live Ollama number (H1 §8) is still one run away; untouched.
* `pgrep -f` self-matches a `bash -c` command line that contains the pattern — two wait loops in
  this sitting spun on their own shell. Poll a file, not the process table.
