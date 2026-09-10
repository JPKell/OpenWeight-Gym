# F3 handoff — ModelRack Phase 7, adapters and the cache-correctness test

**Row:** F3 of `docs/roadmap/outstanding-work.md` §1. **Model:** Opus 5, as scheduled — no
deviation to record for `model-assignment.md` §3.5.
**Date:** 2026-09-04. **Ships:** nothing. P7 rides **0.7.0 at H1** with D3's unreleased P6 work;
version, tag and publish untouched, changelog under `## [Unreleased]`.
**Exit conditions:** all nine met, with two qualifications stated where they arise — I17's
semantic canary skips for want of artefacts (§6), and nothing was pushed (below).
**State:** both repos committed and clean. **Neither is pushed** — the standing instruction of
2026-09-04 is that pushing is the operator's, so no `git push` and no push probe was run.

```
ModelRack  51bc009  feat(providers): LoRA adapters on LlamaCppProvider — registration, selection, pending_restart
           52565b4  test(contract): I17 — a prefix under adapter A is never reused for adapter B
           5e8aa0e  docs(modelrack): Phase 7 in the spec, the plan and the changelog
           6c686f5  test(contract): pin the adapter-free request body to a Phase 6 golden
           5f8cd5d  docs: mirror the Phase 8 plan section carrying ADR-0074
docs       986ab25  docs(modelrack): Phases 7 and 8 in the development plan   (Gate 0, before any source)
           9196580  docs(roadmap): F3 done — adapters served, and what the server's own source said
           23e372c  docs(roadmap): name F3's fourth ModelRack commit
           5946e3e  docs(adr): ADR-0074 — adapter-enabled serving is a RuntimeProfile field
```

---

## 1. Gate results

| Gate | What it made true | Result |
|---|---|---|
| **0** | Phases 7 **and** 8 written into `packages/modelrack/development-plan.md`, mirrored `cmp`-identical, committed **before** any source | done (`986ab25`) |
| **A** | `AdapterRegistration` / `AdapterState` / `AdapterStatus`; `AdapterNotFound`; identity from `baseaicore`, never redefined; **A-1's invariant pinned to a golden captured from the Phase 6 code**, not to field checks | done |
| **B** | `adapter_hot_swap` (the 14th flag); launch-time registration; refusals recorded with both digests | done |
| **C** | Per-request selection, one adapter at `1.0`; `AdapterNotFound` both ways; the escape hatch closed | done |
| **D** | `pending_restart` and the in-flight guard, covering the profile-change restart too | done |
| **E** | **I17**: the structural property in the default gate, proved against five injected defects; the semantic canary written and **visibly skipping** | done, canary blocked on artefacts |
| **F** | Row marked done; §0.1 and §0.2 recorded; the adapter roadmap corrected | done (`9196580`) |

**The gate, exactly as run**, from `/home/jpk/ai/suite/py/ModelRack` with `.venv` active
(**Python 3.13.15**, not the 3.14.4 the kickoff stated):

```
ruff format --check .      → format OK
ruff check .               → lint OK
mypy src tests             → Success: no issues found in 51 source files
lint-imports               → Contracts: 2 kept, 0 broken     (.importlinter unedited)
pytest --cov               → 1374 passed, 16 skipped, 25 deselected;  coverage 99.82 %  (floor 95 %)
```

**The `-m live` run**, separately, against the real binary — llama.cpp build **`b10792`**
(`llama-server --version` reports `b1-c5a5535` because the clone is shallow; `c5a5535` is the
commit and the real identity):

```
MODELRACK_LLAMACPP_MODELS=/home/jpk/ai/models/llm \
  .venv/bin/python -m pytest -m live tests/live/test_llamacpp_live.py -rs -q
→ 5 passed, 2 skipped in 21.65 s
```

The five are D3's journey, re-run and still green. The two skips are the canary — §6.

---

## 2. §0.2 — the boundary decision, and the conversion LA2 must perform

**Taken as recommended: ModelRack defines its own value object and never imports `setspec`.**
ADR-0061 rule 3 already settles it (*"ModelRack never reads the directory — it receives manifests
from the application constructing it"*), master architecture §2 permits only `mirrorwall` and
`commissioner` to depend on `setspec`, and `.importlinter` encodes that. Nothing was weakened;
`lint-imports` is green with the file untouched, and the runtime dependency set is still exactly
`baseaicore` + `httpx`. The only pin that moved is the `baseaicore` **floor** — see §7.4.

The decision is recorded in three places, as asked: the plan's Phase 7 section, the docstring of
`modelrack/adapters.py`, and here.

**The conversion LoadCoach 1.1 (LA2) must perform** is field-for-field, and every field it needs is
present. From `setspec.artifacts.AdapterManifestOut`:

```python
AdapterRegistration(
    name=manifest.name,                               # ^[a-z][a-z0-9_-]{1,63}$ — validated here too
    artifact_path=directory / manifest.artifact_file, # the manifest's path is *relative*; the
                                                      #   application resolves it against the
                                                      #   configured [adapters] directory
    artifact_sha256=manifest.artifact_sha256,         # normalized on construction; refused if it will not
    base_model_name=manifest.base.provider_model_name,
    base_artifact_digest=manifest.base.artifact_digest,   # None → NAME_ONLY, flagged everywhere
    data_classification=manifest.data_classification,     # required, no default (ADR-0065)
    source_sha256=manifest.source_sha256,             # lineage only, never identity
    adapter_format=manifest.format,                   # "gguf" or a refusal
)
```

Two manifest fields are deliberately **not** carried: `declared_capabilities` and
`created_at`/`notes`. Capabilities are a claim under test that FreeWeight measures and LoadCoach
routes on — a serving layer holding them could only mislead — and the timestamps are registry
bookkeeping. If LA2 finds it needs either *inside* ModelRack, that is a signal the responsibility
moved, not a field to add.

**Which of LoadCoach 1.1's new constraints depend on what P7 exposes:**

| LoadCoach constraint | What it reads |
|---|---|
| `adapter_incompatible` | `AdapterState.status is INCOMPATIBLE` plus `.reason` — which already carries both digests, so the rejection can be explained without a second call |
| `adapter_unmeasured` (`require_adapter_evidence`) | Nothing from ModelRack. It keys on `AdapterRegistration.identity` (a `baseaicore.AdapterIdentity`) against FreeWeight evidence — the subject key, which is why the identity is BaseAiCore's and not a copy |
| remote + adapter → `excluded_by_policy` | `capabilities().adapter_hot_swap`, which is `False` on every remote-capable adapter. LoadCoach should branch on the flag, never on a provider's name |
| two-level residency (`base_switch_penalty`) | `list_resident()` for the base, `list_adapters()` for the registered set — an adapter switch is free **only** for a `REGISTERED` adapter; a `PENDING_RESTART` one costs a restart and should be scored as such |
| the models UI / explanations | `AdapterState.base_confidence` — a `NAME_ONLY` subject must be shown with its caveat wherever it surfaces (ADR-0058 rule 5), and `GenerationResult.adapter_base_confidence` carries the same fact onto every attempt |

**One thing P7 deliberately did not do, now decided** (§7.8): adapter-*enabled serving* is a
runtime-profile fact (ADR-0060 / A-3) and ModelRack does not put it there. Settled by the operator
on 2026-09-04 as **[ADR-0074](docs/adr/0074-adapter-enabled-serving-is-a-runtime-profile-field.md)**
— a real `RuntimeProfile` field, scheduled at **H1 before publication**.

---

## 3. I17 — the test design, and why it is the right assertion

This is the section worth reading twice.

**The prefix cache in question is not ModelRack's.** ModelRack has a `MetadataCache` (parsed GGUF
headers) and a `DigestStore` (file hashes); neither holds generation state, and neither is keyed on
a prompt. The KV prefix that could be wrongly reused lives in **llama-server's slots**, and the
server, not this package, decides which slot answers a request. So "assert the cache was not
reused" is not a thing a test without a server can do, and a test that claimed to would be
theatre.

What *is* this package's to get right — and what the structural half asserts — is the pair of
properties that make the server's own rule **reachable**:

1. **Every request states its whole adapter configuration.** The server clears a slot's prompt
   cache when a task's adapter set differs from the slot's (`lora_should_clear_cache`) — but only
   on the branch where the request *carries* a `lora` field. §4 is the whole story of the other
   branch.
2. **ModelRack never pins a slot.** Slot choice is the server's precisely because that is what lets
   it compare the slot's adapters with the task's; a caller-supplied `id_slot` reaches past the
   rule. So the adapter never sends one, and refuses a caller that tries.

The checker, `assert_adapter_isolation`, takes a sequence of *(what the caller asked for, what went
on the wire)* pairs and asserts four clauses: the `lora` key is present **iff** the server has
adapters (so a deployment with none is byte-for-byte unchanged); the list is **complete**, naming
every registered id exactly once; exactly the named adapter is at `1.0` and every other at `0.0`,
with no third scale; and no slot-pinning key appears. It is driven over twenty randomized requests
alternating three adapters and the bare base, across both endpoints and both streaming modes.
`pytest-randomly` seeds the draw and prints the seed, so an order-dependent failure — the shape a
cache defect actually has — is reproducible from the report.

**Why this is the right assertion, and not a weaker one.** The obvious alternative is to assert on
`timings.cache_n` after a switch, which is what D3's §3 suggested. It is a good live check and the
canary does it, but it is the wrong *default-gate* test twice over: it needs a server, and it
asserts the server's behaviour rather than this package's. If llama.cpp changed its slot rules
tomorrow, a `cache_n` assertion would fail and tell you nothing about whether ModelRack was still
correct. The property above fails **exactly when ModelRack has stopped holding up its end**, which
is the only thing a unit-level conformance test can honestly be about.

**And it is proved by making it fail.** A correctness test whose silence reads as proof is the
worst artefact this row could have produced, so the checker is run against five defects and
asserted to reject each:

| Injected defect | The real bug it stands for |
|---|---|
| the selection dropped from the body | a bare-base generation recorded under the caller's adapter subject |
| the previous request's selection left in place | cross-contamination — request B runs under A's adapter |
| a partial list (only the enabled entry) | the rest left to the launch scales — §4, i.e. **every** adapter on |
| a slot pin added | the one lever that reaches past the server's cache clearing |
| a scale of `0.7` | a per-request scale: behaviour varying without identity varying (ADR-0063 rule 2) |

A sixth control asserts the sound sequence passes, so the checker is not merely always failing.

**The no-cross-adapter-batching note**, recorded rather than assumed: `server_slot::can_batch_with`
includes `are_lora_equal(lora, other_slot.lora)`, so two slots whose adapter sets differ are never
in one decode batch (`tools/server/server-context.cpp`, build `b10792`). That is the *server's*
guarantee, not this package's; it is written into the spec and the test module so it stays checked
if this suite's single-user concurrency ever changes. Note also that `--slot-save-path` (empty by
default, never set here) enables a `/slots` save/restore path that is **not** adapter-aware — an
operator passing it through `provider_options` would open a hole this checker does not cover. It is
in the plan's Known risks.

---

## 4. The finding: llama-server applies every registered adapter to a request that names none

Read in `tools/server/server-context.cpp` at build `b10792`, and it changed the design:

```cpp
if (!task.params.lora.empty()) {
    auto task_loras = construct_lora_list(task.params.lora);
    if (!are_lora_equal(task_loras, slot.lora)) {
        if (lora_should_clear_cache(slot.lora, task_loras)) { slot.prompt.clear(); }
        slot.lora = task_loras;
    }
} else {
    slot.lora = params_base.lora_adapters;      // ← no cache check at all
}
```

`params_base.lora_adapters` holds the **launch** scales. `--lora FNAME` sets `1.0`, and
`--lora-init-without-apply` only skips `common_set_adapter_lora` at *init* — it does not zero them
(`common/common.cpp:1507`). And `slot.lora` is what is applied per batch
(`common_set_adapter_lora(ctx_tgt, slot_batched->lora)`).

So a request with no `lora` field, sent to a server launched with `--lora a --lora b
--lora-init-without-apply`, runs with **both adapters applied at 1.0**, on a slot whose prompt
cache was built under whatever ran last. That is simultaneously a wrong-subject bug, a violation of
ADR-0063 (composition), and I17's own defect — in the shipped server, reachable by the most
ordinary request there is.

**The fix, and the ADR reading it needs.** Every request to a server that has adapters registered
now carries the complete configuration: the selected adapter at `1.0`, every other registered
adapter explicitly at `0.0`. A server with **no** adapters registered still sends no `lora` key, so
A-1's byte-for-byte invariant is untouched.

This reads ADR-0063 rule 1's *"the provider sends at most one `lora` entry"* as governing
**enabled** entries — an entry at scale `0.0` is a disable, not a second adapter, and no
composition can result from a list of zeros. The alternative (send only the enabled entry and let
`construct_lora_list` zero the rest) satisfies the letter, works, and is one line shorter; it was
rejected because the bare-base case then has no honest spelling — you would have to send a single
entry at `0.0` naming an arbitrary adapter — and because a recorded body that states the whole
configuration is a much stronger thing to assert a property over. **If the architect prefers the
literal reading, the change is confined to `lora_field()` in `_llamacpp_wire.py` and one clause of
the I17 checker.**

---

## 5. The in-flight guard — what "in flight" means, and how the race is forced

**In flight** = a per-server counter, keyed by model name, incremented just before a request's
bytes go out and released when the request is finished with the server. For `generate()` that is a
`finally`. For `stream()` it is any of three endings — drained, abandoned mid-iteration, or
collected — because a stream can end more than one way and two of them can happen to one iterator.
Release is idempotent. A generator that is **never started** is the case a `finally` cannot cover
(the body never runs), so release is additionally wired to the iterator's collection via
`weakref.finalize`; without that, one dropped iterator would make a server un-restartable for the
life of the process and every later rescan would silently never take effect.

**The guard decides two different questions:**

* A **deferred** restart (adapters arrived after launch) happens at the next `_ensure_server` where
  the count is zero — that is the "next natural idle" of ADR-0062 decision 3, and it is a boundary
  *between* requests, never inside one. If work is in flight, nothing restarts and the pending
  adapters stay pending, which is what the state is for.
* A **required** restart (the runtime profile differs, so this server cannot serve the request at
  all) cannot be deferred — but it must not kill a stream either. It now raises
  `ProviderUnavailable` with `reason="restart_pending"` and `restart_reason="profile_change"`.
  **This is a behaviour change from Phase 6**, which restarted immediately and would have failed
  the in-flight stream with a dropped connection (D3 §9 finding 8). It is classed as
  *availability*, not reliability, per ADR-0067 rule 2, so LoadCoach takes the subject out of the
  pool for a moment rather than counting a failure against it.

**How the tests force the race** — by structure, never by timing, and never with a thread:

```python
provider.generate(_request())                     # a server is up
events = provider.stream(_request())              # a stream opens
next(iter(events))                                # ...and is now genuinely mid-flight
provider.register_adapters([registration()])      # the adapter arrives *during* the work
with pytest.raises(ProviderUnavailable): ...      # refused, and the server is not touched
list(events)                                      # the stream that was running finishes normally
provider.generate(_request(adapter="factcheck"))  # now idle: one restart, and it is served
```

A recorded SSE response held part-drained *is* the race — no sleep, no flake. `test_two_requests_in_flight_both_have_to_finish` adds the arithmetic (the count is a count, not a
flag), and `test_a_stream_that_is_never_started_still_releases_its_claim` covers the
`weakref.finalize` path. **All three were checked for teeth**: removing the finalize makes the
third fail, and the I17 checker rejects all five injected defects.

Phase 6's supervision properties survive and are asserted through the injected `FakeProcessTable`
and `FakeLauncher`, not by watching `ps`: the restart terminates exactly one process, spawns
exactly one, and leaves no pid file.

---

## 6. What the semantic canary needs (it skipped, and that is a finding)

**There is no LLM LoRA adapter GGUF on this machine.** `find ~/ai/models -iname '*lora*'` returns
only Wan 2.2 video-diffusion safetensors, which llama.cpp does not serve. So the canary is written,
marked `live`, and **skips with its requirements named** — never a fabricated pass:

```
SKIPPED tests/live/test_llamacpp_live.py:370: I17's semantic canary needs two real LoRA adapter
GGUFs for one base. Set MODELRACK_LLAMACPP_ADAPTERS to two .gguf paths separated by os.pathsep,
and MODELRACK_LLAMACPP_ADAPTER_BASE to the model name they were trained on. …
```

**Precisely what an operator must produce, so no conversation is needed:**

1. A base GGUF already under `MODELRACK_LLAMACPP_MODELS` — any instruct model llama.cpp serves.
   The four already there qualify. Note its **model name**: its path below the models directory
   without `.gguf` (e.g. `Qwen3.5-9B-Claude-4.6-HighIQ-THINKING-HERETIC-UNCENSORED.Q4_K_M`).
2. **Two** LoRA adapters trained on **that exact base** — a digest mismatch is refused, fail
   closed, so an adapter for a different quantization of the same model will not do. Any rank.
   Training is outside the suite (ADR-0061 rule 6); the directory is the hand-off point.
3. Each converted to GGUF once, with `convert_lora_to_gguf.py` from the llama.cpp tree at
   `~/ai/tools/llama.cpp`.
4. The two **behaviourally distinguishable** — the assertion is that they answer one prompt
   *differently* at temperature 0, so two adapters that behave alike fail the test and rightly so.
   A terse-answers LoRA and a verbose-explainer LoRA is enough.
5. Then: `MODELRACK_LLAMACPP_ADAPTERS=/path/a.gguf:/path/b.gguf`,
   `MODELRACK_LLAMACPP_ADAPTER_BASE=<the model name from step 1>`,
   `MODELRACK_LLAMACPP_MODELS=/home/jpk/ai/models/llm`, and `pytest -m live`.

The canary asserts three things: both register with `DIGEST` confidence against the real base; the
two adapters produce different continuations of a shared, cache-worthy prefix; and the bare base
matches **neither** — because a bare-base request that inherited an adapter's prefix would match
that adapter, which is exactly §4's defect seen from the outside. It prints `cache_read` per
subject as evidence.

**This is an H1 prerequisite, not a P7 gap.** LA1's exit condition (I16: twenty alternating
generations, zero base loads) needs the same artefacts. Both are blocked on the same operator step.

---

## 7. Things this prompt or its kickoff said that turned out not to be true

1. **§0's "ModelRack's venv is Python 3.14.4"** — it is **3.13.15** (`.venv/bin/python -VV`). CI
   still covers 3.12/3.13 with 3.14 as early warning; nothing here depends on 3.14.
2. **§0's "`baseaicore` has `AdapterIdentity`"** — true of `baseaicore` **0.4.1**, which is on
   PyPI; the venv held **0.4.0**, which the `>=0.4,<0.5` pin permitted. Left alone, the package
   would have imported cleanly and failed at the first adapter.
3. **§7's "Ollama, the fake and the OpenAI-compatible adapter declaring `False`"** — done, but by
   *default*: every flag on `ProviderCapabilities` defaults `False`, so the three declare it by not
   mentioning it, and only `LlamaCppProvider` names it. `MINIMAL_CAPABILITIES` and
   `FULL_CAPABILITIES` both leave it `False`; the fake's constant carries a note saying why on a
   stronger ground than "not implemented".
4. **The pin had to move.** `baseaicore>=0.4,<0.5` → `>=0.4.1,<0.5`. This is a *floor*, not a new
   dependency: the set is still `baseaicore` + `httpx`, and exit condition 8 holds. §14's stop rule
   was about adding `setspec` and about `.importlinter`; neither was touched.
5. **ADR-0062 decision 1's "the `Provider` protocol does not change"** did not survive intact.
   `list_adapters()` and `register_adapters()` were added; the **load/unload seam it was actually
   about is untouched**, and no lifecycle method was added. The reason is the same one that put
   `refresh` on the protocol: without them LoadCoach must `isinstance`-check `LlamaCppProvider` to
   render an adapter row or fold in a rescan, importing a concrete adapter — which is what the
   protocol exists to prevent. **This is the decision most worth a second opinion.** Reverting is
   small: delete two protocol methods and four four-line refusals, keep them on `LlamaCppProvider`,
   and LA2 downcasts.
6. **§0.4's framing of the structural half** ("the slot/session handling and any prompt-prefix
   reuse ModelRack participates in") assumed ModelRack participates in prefix reuse. It does not —
   it neither pins slots nor sends session ids — so the property had to be stated as §3 states it:
   what ModelRack *sends*, and what it refuses to send. The interesting defect turned out to be in
   the opposite place from where the prompt pointed (§4).
7. **§0's "`pending_restart` appears only in prose. No code."** — true, and it stayed a
   *derived* state rather than a stored one: `list_adapters()` computes each status from what the
   last spawn recorded plus what is registered now. Nothing persists; a snapshot is honest and a
   stored flag would go stale the moment a server exited.
8. **An open question the prompt did not raise, and LA2 cannot start without.** ADR-0060 (A-3) puts
   *adapter-enabled serving* — the fact that the server was launched with adapters registered — in
   the **`runtime_profile_hash`**, because a base measured on an adapter-registered server is a
   different measurement from the same base on a clean one. **P7 does not put it there**, and
   deliberately: the flags come from the registration set, not from `RuntimeProfile`, and inventing
   a profile field would be ModelRack deciding what a runtime profile *is* — which is BaseAiCore's
   and the application's, and is outside §4.1's three bullets. So today two runs of one base, one
   on a server with adapters registered and one without, produce the **same** `profile_hash` and
   would merge in evidence. Someone has to close that: either the constructing application sets a
   `provider_options` marker (cheap, works now, and the profile hash already covers
   `provider_options`), or `RuntimeProfile` gains a real field (an ADR, and a BaseAiCore minor).
   It costs nothing until FreeWeight 1.1 measures the A/B that ADR-0060 §3 describes — but it is a
   silent-merge bug the day it does.

   **Decided after the build, in the interview: a real field** —
   `RuntimeProfile.adapters_registered: bool | None = None`, recorded as **ADR-0074** and scheduled
   at **H1, before `0.7.0` publishes**. Three things make it safe and one makes it urgent.
   `profile_hash` already excludes `None` fields *explicitly* so that adding an optional field is
   additive, so every stored hash in all three databases is unchanged — but only for a **tri-state**
   field: a `bool = False` default would be hashed and move every profile hash in the suite, which
   is why `None` ("not stated"), `False` ("clean, stated") and `True` are three values rather than
   two. The application sets it, because it also supplies the registration set. And ModelRack
   **refuses** a request whose profile disagrees with the server it would use — the
   `context_configurable` discipline (ADR-0023 §4) one level up, since a profile claiming a clean
   server while three adapters sit in VRAM is exactly a recorded run that never happened. The
   urgency: evidence measured before the field exists is **not separable afterwards** — there is no
   way to tell later which kind of server produced it — so the cheap window closes the first time
   anyone benchmarks a base on a machine with an adapters directory configured, not when LA3's code
   is written.

---

## 8. What H1 (P8) inherits

* **A Phase 8 plan section already written** (`986ab25`) in the house shape — cancellation under
  supervision, leak tests, the four-adapter conformance run, the sharded-GGUF decision (D3 finding
  6), and publication.
* **The in-flight counter**, which is what makes P8's cancellation assertions statable: "a
  cancelled stream leaves a usable server **and a zeroed claim**" is now a testable sentence.
* **Two operator steps on the critical path, both needing the same artefacts**: I17's canary (§6)
  and I16's twenty-generation zero-base-load run. Neither can be faked.
* **A `# pragma: no cover` worth revisiting** in `_select_adapter`: the branch where an idle server
  still has a pending adapter is unreachable today because `_ensure_server` folds pending adapters
  in whenever nothing is in flight. If P8 adds another reason to defer a restart, that branch
  becomes live and needs a test.
* Coverage is 99.82 %, so P8 starts with no debt to pay down.

## 9. Before the next session

1. **Push both repos** (nothing here pushed anything) and watch CI. ModelRack is five commits
   ahead of `origin/main`; docs is four.
2. §4, §5 and §7.5 were put to the operator in the post-build interview on 2026-09-04 and **all
   three confirmed as built**: the complete-`lora` reading of ADR-0063 stands (without amending the
   ADR's wording), the two new `Provider` methods stay on the protocol (without an ADR recording
   the expansion), and the profile-change restart keeps refusing while work is in flight (without a
   note in ADR-0062). Nothing to revisit; recorded here so H1 does not reopen them.
3. §7.8 is **settled** — ADR-0074, scheduled at H1 (`roadmap/outstanding-work.md`, the H1 row, and
   the plan's Phase 8 Work list). Nothing to decide; it needs building before `0.7.0` publishes.
4. Decide whether the profile-change refusal (§5) wants its own note in ADR-0062 or is covered by
   decision 3's "never mid-work".
