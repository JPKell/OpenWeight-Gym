# Kickoff — WPF2: adapters on FreeWeight, operated from the console

**Row:** WPF2 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md), findings 4 and 9). Runs after WPF1,
whose fixed Settings form this row's demonstration uses.
**Ships:** unreleased, no version bump in either repository.
- **FreeWeight:** a provider write that FreeWeight refuses changes nothing on disk. The combination
  of adapters and a provider that cannot serve them is settled by decision, and `config validate`
  agrees with what the running application accepts. A llama.cpp refresh reuses its digest cache.
- **WeightRoomGym:** the Runs page starts a run of a base model served with a registered LoRA
  adapter, through the capped `freeweight_suite_run` job, and Repeat keeps the adapter.

**Components:** `~/ai/suite/FreeWeight` first, then `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WP6_HANDOFF.md` findings 3, 4 and 9, and check 2's FreeWeight table; `WP3_HANDOFF.md`
§2 items 2, 3 and 8 (start as a job, the follow, the adapter page); `H6_HANDOFF.md` (the adapter
that was stored and never sent); ADR-0058, ADR-0059, ADR-0061, ADR-0071, ADR-0074, ADR-0117,
ADR-0119; `apps/freeweight/api.md` §2a, §3 and §8a; spec §7.10 (the job kinds).

**Code to read first:** FreeWeight's provider write (`PUT /provider`, the re-open), its provider
factory where adapters are registered (`IncompatibleAdapter`, `adapter_hot_swap`), `config validate`,
the llama.cpp discovery and its digest cache, `cli/commands/run.py` (`--adapter`) and
`services/adapters.py`; WeightRoomGym's `services/job_kinds.py` (`freeweight_suite_run`),
`services/freeweight_actions.py` and the Runs templates.

## What WP6 saw on the reference machine (2026-09-11)

1. **Nothing in the console can start an adapter run.** The Runs page's Start form has `model`,
   `suite` and `label`. The job's argv is `freeweight run start --model … --suite … --json`, with
   `--label` when one is given. FreeWeight's own Start form and `POST /api/v1/runs` carry no adapter
   either. Only `freeweight run start --adapter <name>` serves one, under `provider.kind =
   "llamacpp"`. WP6 measured `terse` through the CLI inside the job's own scope, then read the
   adapter's page and the comparison in the console (handoff check 2).
2. **A refused provider write changed the file.** With `[adapters] directory` set, the Provider
   page's save of `kind = "ollama"` came back refused, `CAPABILITY_UNSUPPORTED`: *This provider does
   not declare 'adapter_hot_swap' and cannot register an adapter.* The console's audit row is
   `01M2963QF2PXQ3GEZ4N9T10BRY` (`refused`, `security: true`). **FreeWeight had already rewritten
   `config.toml` to `ollama`**, with the llama.cpp version kept as `.bak`, while its running
   provider stayed llama.cpp. `freeweight config validate --file` called the rewritten file *valid*.
   A restart would have started FreeWeight on the combination it had just refused. The Provider page
   put `llamacpp` back (`01M296S3H9P6YAWB4ZDSJHYBGE`). **The next two runs FreeWeight's own scheduler
   claimed then failed at once**, with `RuntimeError: Cannot send a request, as the client has been
   closed.` (runs `01M2970JAN5V8Q14D1Q531XRTQ` and `01M2970TDRQ5VJWYRQ1D19KXAC`, 14:47 PDT). The
   re-open had closed the HTTP client the in-process scheduler still held. The failed run also left a
   `llama-server` running under `freeweight.service`. Only a restart cleared both. In FreeWeight 1.2.1, adapters and Ollama
   cannot be used together, so the operator chose to leave FreeWeight on llama.cpp with adapters on
   (2026-09-11).
3. **Every llama.cpp refresh hashed the whole model directory again.** 195 GB of GGUF files took
   about 2–4 minutes each time: after the first switch, after a restart, and on a refresh. The digest
   file was rewritten each time (12:27:50, then 14:13:20 PDT). The console's call gave up and audited
   the refresh `refused` (`01M28YXX7NRYPAB99Z97J8DGV4`, `01M2956QJ9F9ETQDP996B62XZ9`,
   `01M2967D3E2FNYRAHY8MB822CS`). The timeout half is WPF1's; the re-hash is this row's.
4. **A served-context degradation that contradicts its own configuration.** The bare base run
   `01M295750S8VB88YFKW8JYDSTQ` and the adapter run `01M2976BG3DZ81BS97TMJD2TJR` both record
   *Served context 8192 tokens (configured)*. Both also carry `served_context_assumed_incorrectly`,
   with 32 768 read from llama-server's `/props`. Its explanation says the 8 192 *was assumed …
   because nothing requested one*, yet `[runtime] context_size = 8192` is set.
   `_llamacpp_wire.launch_flags` adds `--ctx-size` from the profile, independently of `--lora`, and
   the goal jury's server FreeWeight launched in the same session shows `--ctx-size 8192 --fit off`.
   WP6's captures of the two runs' own server command lines were truncated. Either the `/props`
   reading is wrong, or those launches lost the flag. On a memory-capped machine
   (`MEMORY_SAFETY.md`), which one matters.
5. **Turning adapters on needed a hand-written manifest.** `~/ai/models/adapters/llm` held four LoRA
   GGUFs and no `*.manifest.json`, so FreeWeight listed them as unmanifested. FreeWeight never writes
   one ("the scan drafts, a human keeps", ADR-0061 rule 4). WP6 wrote
   `qwen2.5-1.5b-instruct-terse.manifest.json`, reviewed by the operator (classification `public`).
   FreeWeight's reader refuses a name outside `^[a-z][a-z0-9_-]{1,63}$`, so a file stem cannot be
   the name; the adapter is `terse`.

## Decisions already taken — do not reopen

* **Start stays the capped job** (WP3 §2 item 2, ADR-0119). The adapter is one more argument to the
  same command, never a second path.
* **An adapter the provider cannot serve is refused by name.** It never falls back to the bare base
  (ADR-0058). The console renders FreeWeight's refusal, and does not decide compatibility itself.
* **The adapter reaches the wire.** H6's lesson: test that the argument arrives in the child's argv
  and in the run's recorded subject, not only in a form.
* **A refused write writes nothing** (ADR-0117's validate-before-write): everything the write can be
  refused for is checked before the rename.

## Decisions for this row — make each, and record it in the handoff

1. **Adapters with a provider that cannot hot-swap.** Either refuse the combination at
   `config validate` and on the Provider page, or keep adapters configured and inert under such a
   provider, saying so. If this changes what ADR-0058 or ADR-0061 says, write an ADR.
2. **The digest cache.** Reuse it across refreshes and restarts, keyed by what ADR-0071 names, and
   measure a warm refresh of the reference machine's directory.
3. **The Start form.** Whether the adapter field appears only under `llamacpp`; whether it lists
   `GET /adapters`' available entries or takes a name FreeWeight then refuses.
4. **FreeWeight's API.** Whether `POST /api/v1/runs` gains `adapter`, so that FreeWeight's own UI can
   start one too. That change is additive; if you make it, edit `api.md` first and mirror it.
5. **Repeat.** Confirm that `POST /runs/{id}/repeat` on an adapter run keeps the adapter, or fix it.

## Gates

**Gate A — FreeWeight.** Tests first:
* a provider write refused at the re-open leaves the file byte-identical;
* `config validate` agrees with the running application on the adapters combination;
* a second refresh of an unchanged directory hashes nothing;
* a run the in-process scheduler claims after `PUT /provider` has re-opened the provider reaches the
  new provider, and a failed run leaves no `llama-server` behind;
* a llama.cpp run with a configured context, with and without adapters registered, launches with
  `--ctx-size` and records no `served_context_assumed_incorrectly`, or the degradation's reading of
  `/props` is corrected.

Implement. Run the gate, naming the interpreter. Commit.

**Gate B — the start.** Tests first: the job's argv carries `--adapter`; an unknown adapter is
refused in FreeWeight's own words; the run's subject names the adapter. Implement. Run the gate.
Commit.

**Gate C — the live proof.** On the reference machine, FreeWeight on llama.cpp with adapters on, as
the operator left it:
* a refresh that returns within the console's timeout;
* the bare base and then `terse`, each started from the Runs page, one live load at a time, both
  followed;
* the adapter's page with its deltas, and the two runs compared;
* a refused provider switch that leaves `config.toml` unchanged (`sha256sum` before and after).

Take screenshots in both themes. Commit the handoff.

## Finish line

- Both repositories' gates green, with the interpreter named, and coverage held; `git status --short`
  clean in both.
- `docs/history/handoffs/WPF2_HANDOFF.md`: the five decisions, the run ids, the audit ids, the
  refresh times before and after, and what this kickoff got wrong.
- The row marked done. Nothing pushed.
