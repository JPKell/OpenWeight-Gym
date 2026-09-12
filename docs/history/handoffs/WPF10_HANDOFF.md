# WPF10 Handoff — the launch path that lost the runtime profile was the interaction turn

**Row:** WPF10 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-12, wave 4 · **Model:** Claude
Opus 5 · **Kickoff:** `history/prompts/wpf10-freeweight-a-launch-path-that-loses-the-runtime-profile.prompt.md`
· **Branch:** `row/wpf10-runtime-profile` at `~/ai/worktrees/freeweight-wpf10`, head **`7156c20`**,
**not merged, not pushed** · **Ships:** unreleased, no version bump.

**Gate A is built, green and committed. Gate B — the live run — is the orchestrator's; §5 is it
command by command.** This session touched no GPU, started no `llama-server`, ran no
`systemctl --user`, and wrote nothing under `~/.config` or `~/.local/share`. The cause is in
FreeWeight; `py/ModelRack` was read and **not** edited.

## 1. The path that lost the profile

`_run_interactive_case`'s inner `caller` (`services/runs.py`) built its **own**
`GenerationRequest` — identity, messages, sampling, adapter, tools, timeout — and never passed
`runtime_profile`. So every turn of a multi-turn suite asked for `RuntimeProfile()`: provider
defaults, no `--ctx-size`, no `--fit off`.

It is neither candidate the kickoff named (not the repeat, not a warm-server path in FreeWeight —
FreeWeight has none; it never reuses or adopts a server, ModelRack owns that). It is the third
possibility: **a second request builder**, which under llama.cpp is a second argv. The chain:

1. the run's warm-up goes through `_build_request` with the stored profile → ModelRack spawns
   `llama-server` with `--ctx-size 8192 --fit off` (WPF2 Gate C's port 8180);
2. the first measured turn arrives with `RuntimeProfile()`. `LlamaCppProvider._ensure_server`
   compares `_launch_key` = `[model path, launch_flags(profile)]`, sees a different key, and does
   what ADR-0023 says: it **terminates the server and spawns a new one under the caller's flags**
   — i.e. under none (port 8181, in the repeat's own window);
3. every remaining call of the run is served by that server, at the model's trained context
   (`n_ctx` 32 768 for `Qwen2.5-1.5B-Instruct`), while the run's record says
   `served_context 8192 / configured`;
4. `_observe_residency` reads `context_length` off that same flagless handle, so
   `served_context_observed` is 32 768 and `served_context_assumed_incorrectly` fires — correctly.

Which suites: every one whose benchmark declares an `interaction` — `native.structured_output`,
`native.tool_use`, `native.tool_recovery`, `native.agent`, and the judge suite. **Every run WP6 and
WPF2 read was on `native.structured_output`**, which is why all three of Gate C's runs showed it and
why it looked like a repeat/warm-path bug: the repeat is simply another run of an interactive suite.
A single-call suite (`native.echo`, `native.instruction_following`, `native.performance`,
`native.memory_kv`) was never affected, which is also why the context sweep and the fit ladder never
saw it.

**ModelRack is innocent.** `read_served_context` reported exactly what that server was serving;
the restart it performed is the documented behaviour ("a differing profile restarts",
`packages/modelrack/development-plan.md` Phase 6). Nothing in `py/ModelRack` was touched.

### The fix (`7156c20`)

One builder. `_provider_request(...)` holds the whole `GenerationRequest` construction and is
called by `_build_request` (warm-up and the single-call path) and by the interaction `caller`,
which now passes `context.runtime_profile` — the profile read back from the run's stored row, the
same object the fingerprint was hashed from. Requests on the single-call path are byte-identical to
before (`tools=()` and `response_format=None` are ModelRack's own defaults).

## 2. The decisions

### 1. Where the argv is decided → **one function, `_provider_request`**

The kickoff's rule, taken literally: a second call site *is* the defect. `jury.py` still builds its
own request and that is correct — a juror is a different subject with a different identity, and it
already sends the candidate's profile deliberately (`runs.py` passes `context.runtime_profile` into
the jury so a juror is graded under the profile the candidate was served at).

### 2. A warm server that does not match the profile → **already decided: restart it, at idle. No
new ADR.**

Checked ADR-0023 and ADR-0119 first, as the brief asks, then the code. The behaviour exists and is
documented:

* a launch-key mismatch is a **required restart** in `LlamaCppProvider._ensure_server`
  (`restart_reason="profile_change"`), and it waits for idle — `_require_idle` raises
  `ProviderUnavailable(restart_pending)` rather than killing a server another request is streaming
  from (ADR-0062 decision 3's discipline, applied to profiles);
* `packages/modelrack/development-plan.md` Phase 6 already carries it as a test: *"a profile becomes
  launch flags; a differing profile restarts"*;
* a server the supervisor did not launch is never adopted — `sweep_orphans` kills an orphan and
  leaves a foreign owner alone — so "reuse a resident 32 768 server" is not reachable in the first
  place;
* `adapters_registered` is the one profile field deliberately **outside** the launch key, because it
  describes a server rather than configuring it (ADR-0074 §3): it is compared and refused
  (`ProfileMismatch`), never made to restart anything.

So ADR-DRAFT-warm-server-mismatch.md was **not** written: there is no open choice left, and an ADR
restating an implemented, documented rule would be an ADR about nothing. What was missing was a
statement of the rule on **FreeWeight's** side of the boundary, which is the one doc change below.
*Optional, orchestrator's call, not mine to edit:* ModelRack's `spec.md` carries the launch key only
in passing (contract 16, saying what is *not* in it). Promoting "a differing profile restarts the
server at the next idle; a mismatched server is never reused" to a numbered contract there would put
the rule where a reader of the provider contract finds it. That file belongs to the adapter arc and
WPF13 is about to edit the repository, so I left it alone.

### 3. The degradation's wording → **unchanged, deliberately**

The kickoff says to narrow it to the ModelRack reading "only if it is true". It is not true: the
reading was right, and the launch half — the possibility WPF2's finding 4 could not confirm — is what
actually happened. Narrowing it to "a flag was lost" would be equally wrong, because this code still
cannot know which side failed: a provider that accepts a context and clamps it produces the same
disagreement with nothing lost anywhere. Both readings stay named; `_context_divergence`'s docstring
now records which one history had and why the wording is not narrowed. No user-visible text changed.

## 3. The gate, with the interpreter named

`~/ai/worktrees/freeweight-wpf10/.venv/bin/python`, **CPython 3.14.4** (editable `freeweight`, plus
editable `mirrorwall 0.3.1`, `setspec 0.6.0`, `sweatmeter 0.4.0` from `~/ai/suite/py/`):

```text
ruff format --check .   355 files already formatted
ruff check .            All checks passed!
mypy src tests          Success: no issues found in 324 source files
lint-imports            Contracts: 4 kept, 0 broken
pytest -m "not live and not performance" --cov
                        2767 passed, 30 skipped, 31 deselected in 290.51 s
                        Total coverage 89.68 % (floor 85 %)
```

`git status --short` was clean at the start and carries only this untracked handoff at the end.

### The tests

* `tests/integration/test_quality_suites.py::TestOneRunIsOneLaunch` — the real engine, the real
  scheduler, `FakeProvider` behind a recording wrapper, `native.structured_output` and
  `native.tool_use`, `warmup_repetitions=1`, created under
  `RuntimeSettings(context_size=8192).to_profile(provider_kind="llamacpp")`. It asserts that the set
  of `launch_flags()` over **every** request the run made is exactly
  `{("--ctx-size", "8192", "--fit", "off")}`. **Reverted against the old `caller` it fails with
  `{(), ("--ctx-size", "8192", "--fit", "off")}`** — the empty argv is the bug, reproduced with no
  GPU and no `llama-server`, which is the check the kickoff asked for. It also asserts more than one
  request was recorded, so it cannot pass by the interaction never running.
* `tests/unit/test_runtime_profile.py::TestOneRunIsOneArgv` — an interaction turn and a single call
  produce the same flags and the same adapter; plus a structural guard that
  `services/runs.py` contains exactly **one** `GenerationRequest(` construction, which is the only
  check that fails when a future fourth call path hand-rolls its own request again.

The existing `TestTheConfiguredContextReachesTheServer` (WPF2) asserts the flags of the run's
**stored** profile, which were right all along — that is precisely why it passed while the runs were
being served at 32 768. The new test asserts the requests instead.

## 4. Files changed (`7156c20`)

| File | What |
|---|---|
| `src/freeweight/services/runs.py` | `_provider_request`, the only request builder; `_build_request` delegates; the interaction `caller` passes the run's profile; `_context_divergence`'s docstring records decision 3 |
| `tests/integration/test_quality_suites.py` | `TestOneRunIsOneLaunch`, `_RecordingProvider`, one docstring bullet |
| `tests/unit/test_runtime_profile.py` | `TestOneRunIsOneArgv` |
| `CHANGELOG.md` | one entry under `## [Unreleased] → ### Fixed` |
| `docs/apps/freeweight/spec.md` | **mirrored doc** — see below |

**Mirrored document to apply in `WeightRoom/docs/` and `cmp`:** `docs/apps/freeweight/spec.md`
only — one paragraph added to the `[runtime]` section (the sentence beginning *"**One run is one
launch and one argv:**"*), saying that every provider call of a run carries the one profile, turns
of a multi-turn suite included, and what llama.cpp does to a call that states a different one.
Nothing else under `docs/` changed; `docs/openapi.json` did not need regenerating (no route, no
docstring FastAPI publishes).

`MEMORY_SAFETY.md` §5 already claims *"the suite always passes `--ctx-size` when the profile sets
it"*. That was aspirational for four of the suites; it is now true, and no byte of it changed.

## 5. Gate B, on the reference machine

**Run 2026-09-12 by the wave-4 orchestrating session (Fable 5.1), after the merge — PASS.**

FreeWeight `main` at `c4dd2f4` (the merge of `7156c20`); `freeweight.service` restarted onto it at
02:09:32 PDT (`MainPID` 1809537, health `llama.cpp (no server running), 27 models, 0 resident`).
Card free before starting: 940 MiB of 16 311 used, `pgrep -x llama-server` empty, `ollama ps`
empty. `[runtime] context_size = 8192`, provider `llamacpp`.

Three runs, all `--detach`, all executed by the unit's one provider handle, on
`llamacpp/Qwen2.5-1.5B-Instruct.Q8_0@sha256:5926a692b27b`:

| Step | Run | Suite | Result |
|---|---|---|---|
| 1 run | `01M2AE305H0K52T6RR785VMNP8` | `native.structured_output` | `completed`, `8192 configured []`, `served_context_observed 8192` |
| 2 repeat of 1 | `01M2AE4CF0K2D1YRM47K95X397` | (repeat) | `completed`, `8192 configured []`, `served_context_observed 8192` |
| 3 second run, server warm | `01M2AE569AED5SPRXE3C2HE1CB` | `native.tool_use` | `completed`, `8192 configured []`, `served_context_observed 8192` |

**One launch across all three.** `pgrep -x llama-server` printed one pid, **1811446, `lstart`
Sat Sep 12 02:10:06 2026**, at the start of run 1 and after every run — no restart between the
warm-up and the first measured turn (the line that changed before the fix), none between runs.
Its argv, unchanged throughout:

```
llama-server --model /home/jpk/ai/models/llm/Qwen2.5-1.5B-Instruct.Q8_0.gguf
  --alias Qwen2.5-1.5B-Instruct.Q8_0 --host 127.0.0.1 --port 8180 --jinja --no-webui
  --lora /home/jpk/ai/models/adapters/llm/qwen2.5-1.5b-instruct-terse.gguf --lora-init-without-apply
  --ctx-size 8192 --fit off
```

`GET http://127.0.0.1:8180/props` → **`n_ctx 8192`**, `total_slots 4` (it answered 32 768 at WPF2's
Gate C). No run carries `served_context_assumed_incorrectly`. VRAM while resident: 2 893–3 038 MiB.

Two corrections to §5's recipe: FreeWeight's API is plain HTTP on **8765** (8766 is LoadCoach) and
needs no bearer token from localhost; and a queued run passes through a `preparing` state that a
poll on `queued|running` alone misses. The `--lora … terse` on a bare-base run is
`register_adapters` = the complete set (H2), not a leak.

The GPU window is not mine. Notes first, then the commands.

**Use an interactive suite, or the proof proves nothing.** `native.echo` and
`native.instruction_following` never had the defect. Use `native.structured_output` (what Gate C
used) and `native.tool_use`.

**Run all three through the service, not three CLI processes.** `LlamaCppProvider.close()` — and its
finalizer at interpreter exit — terminates the server, so a `freeweight run start` that executes in
the foreground takes its `llama-server` with it when it exits and the next run cannot meet it warm.
`--detach` queues the run and `freeweight.service`'s scheduler executes it in one long-lived process
holding one provider handle, which is where "the second run meets the first's warm server" is real.
The one-load rule still holds: the scheduler runs them one at a time.

```bash
# 0. the fix is what is running, and the card is free (ADR-0119)
cd /home/jpk/ai/suite/FreeWeight && git log --oneline -1          # the merged WPF10 commit
systemctl --user restart freeweight.service && systemctl --user is-active freeweight.service
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
grep -A6 '^\[runtime\]' ~/.config/freeweight/config.toml          # context_size = 8192, fit_to_device unset/false

M=llamacpp/qwen2.5-1.5b-instruct.q8_0
FW=/home/jpk/ai/suite/FreeWeight/.venv/bin/freeweight

# 1. the run
A=$($FW run start --detach --model "$M" --suite native.structured_output --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
# 2. the repeat of it, once A is completed
$FW run wait "$A"; B=$($FW run repeat "$A" --detach --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
# 3. a second run while the first's server is still warm
C=$($FW run start --detach --model "$M" --suite native.tool_use --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
```

While each of the three is running (`pgrep -x llama-server`, never `pkill -f`):

```bash
pid=$(pgrep -x llama-server); echo "pid=$pid  started=$(ps -o lstart= -p "$pid")"
tr '\0' ' ' < /proc/$pid/cmdline; echo
port=$(ss -ltnp 2>/dev/null | grep "pid=$pid," | grep -oP '127\.0\.0\.1:\K[0-9]+' | head -1)
curl -s "http://127.0.0.1:$port/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); g=d.get("default_generation_settings",{}); print("n_ctx", g.get("n_ctx"), "| total_slots", d.get("total_slots"))'
```

**What must be seen:**

* `pgrep -x llama-server` prints **one** pid, and **the same pid with the same `lstart`** at the
  beginning and the end of each run and across all three runs — one launch, not a restart mid-run.
  Before the fix the pid changed between the warm-up and the first measured turn; that is the
  single most diagnostic line here.
* the argv carries `--model …Qwen2.5-1.5B-Instruct.Q8_0.gguf` **and `--ctx-size 8192` and
  `--fit off`**, on all three (`--lora …` only if a run names an adapter);
* `/props` answers **`n_ctx 8192`** (it answered 32 768 before);
* per run, no degradation for served context, and the observed context agrees with the record:

```bash
for r in "$A" "$B" "$C"; do
  $FW run show "$r" --json | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b["run_id"], b["status"], [(m["metric_key"], m["value"]) for m in b["metrics"] if m["metric_key"]=="served_context_observed"])'
done
```

`served_context_observed` must be **8192** for each. Degradations are not on the CLI's `--json`;
read them from the API (or the console's run page):

```bash
curl -sk "https://127.0.0.1:8766/api/v1/runs/$A" -H "Authorization: Bearer $FREEWEIGHT_TOKEN" \
  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b["provenance"]["served_context"], b["provenance"]["served_context_source"], [d["kind"] for d in b["degradations"]])'
```

Expect `8192 configured []` — and in particular no `served_context_assumed_incorrectly`.

**If the argv is still missing a flag**, the remaining suspect is *not* this row's fix: check
whether the server was launched by something other than FreeWeight (the repeat's subject names the
model, `ps -o lstart=` dates the process), and whether the unit really restarted onto the merged
commit — a fix does not reach a running app without a restart (WPF3/WPF8 lesson).

## 6. What the kickoff got wrong

1. **"The candidates WPF2 named: the repeat, and the warm-server path. There may be a third."** It
   was the third, and neither named candidate is defective. The repeat faithfully reuses the
   original's stored profile (WPF2 fixed that), and **FreeWeight has no warm-server path at all** —
   it never looks for a resident server, never adopts one, and cannot reuse one: ModelRack owns
   every launch decision. Reading FreeWeight for "whatever warm server reuse FreeWeight does before
   launching" finds nothing, which is the correct answer rather than a gap.
2. **Decision 3 reads as an open question ("refuse to reuse it, or restart it").** It is closed, in
   ModelRack's code and its development plan, and the brief's hunch was right: no ADR was needed.
   The live 32 768 server was not a *reused* mismatched server — it was a server **this defect
   caused ModelRack to launch**, correctly, under the flags it was handed.
3. **Decision 4 assumes the remaining possibility after the FreeWeight fix is ModelRack's
   reading.** The opposite: the FreeWeight half explains every observation, and ModelRack's reading
   was accurate throughout. The wording is unchanged because the disagreement can still have causes
   on either side in general (a clamping provider), not because the question is open for these runs.
4. **"Reproduce it without the GPU first if possible."** It is fully reproducible with no GPU and no
   `llama-server` stub at all: the defect is in the *request*, and `launch_flags()` is a pure
   function of the profile, so recording the requests an in-process run makes and diffing their
   argv is a complete reproduction. No fake `server_path` was needed, and nothing in the tests
   spawns a process.
5. **`packages/modelrack/spec.md`'s llama.cpp launch section** (named in *Code to read first*) does
   not state the launch-key/restart rule; the development plan's Phase 6 test list does. Worth
   knowing for anyone else sent to read the spec for it — and §2's optional note.

## 7. For the operator

1. Nothing pushed, tagged or merged; no version moved. One commit, `7156c20`, on
   `row/wpf10-runtime-profile`.
2. **Every adapter and context measurement taken on an interactive suite before this commit was
   served at the model's trained context, not at the recorded one.** That is WP6's and WPF2 Gate
   C's runs, and any other `structured_output` / `tool_use` / `tool_recovery` / `agent` / judge run
   on llama.cpp with a configured context. The runs carry the degradation that says so (that is
   what it is for), and their `served_context_observed` metric carries the real figure — they are
   readable, not silently wrong. Re-measuring anything whose KV-cache or fit conclusions depend on
   the context is the operator's call.
3. **`native.max_context_fit` and `native.memory_kv` are single-call suites and are unaffected** —
   the ladder's refusals and the KV slope were measured at the contexts they claim.
4. One doc file to mirror (§4). `sync_docs.py --check` cannot be run from a worktree (it resolves
   the canonical tree as `../WeightRoom/docs`), so `cp` + `cmp` as WPF2 did.
