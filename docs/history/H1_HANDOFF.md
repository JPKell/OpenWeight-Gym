# H1 — ModelRack Phase 8: cancellation, leaks, ADR-0074, the thinking control

**Row:** H1 of `docs/roadmap/outstanding-work.md` §1.
**Ran:** 2026-09-05, Opus 5 · high, whole, daytime. **No model deviation** — the row's Model
column still reads as an Opus/Sonnet split; model-assignment §3.5 settled at F1 that a phase gets
one model, the stronger of any pair, so the whole row ran on Opus 5 · high.
**Repositories:** `docs`, `py/BaseAiCore`, `py/ModelRack`. All three clean and level with `origin`
at the start; all three now ahead of `origin` and **not pushed** (standing instruction of
2026-09-04).
**Interpreter:** ModelRack `.venv/bin/python` — **Python 3.13.15**; BaseAiCore `.venv/bin/python` —
**Python 3.13.15**. No python3.12 on this host.

---

## 1. The headline, first

**Gates A–F and H's documentation are done. Gate G and the publication of `modelrack 0.7.0` are
not, and the row stays open.**

The kickoff's §0.1 made this a minute-one judgement on evidence rather than a question to sit on,
and the evidence was unambiguous:

```
$ find /home/jpk/ai/models -iname '*.gguf' | head
/home/jpk/ai/models/llm/gemma-4-12B-it-heretic-Q4_K_M.gguf
/home/jpk/ai/models/llm/Qwen3-14B-heretic.Q4_K_M.gguf
/home/jpk/ai/models/llm/gemma-3-12b-it-heretic-Q6_K.gguf
/home/jpk/ai/models/llm/Qwen3.5-9B-Claude-4.6-HighIQ-THINKING-HERETIC-UNCENSORED.Q4_K_M.gguf
/home/jpk/ai/models/llm/gemma-3-12b-it-heretic-Q4_K_M.gguf

$ find /home/jpk/ai/models -iname '*lora*'
/home/jpk/ai/models/vid/Wan_2.2_ComfyUI_Repackaged/split_files/loras/…   (six Wan 2.2 safetensors)

$ echo "MODELRACK_LLAMACPP_ADAPTERS=${MODELRACK_LLAMACPP_ADAPTERS:-<unset>}"
MODELRACK_LLAMACPP_ADAPTERS=<unset>
```

No LLM LoRA adapter GGUF exists on this machine — exactly as at F3, and for the same reason. So
LA1's exit condition (I16: one base, three adapters, twenty alternating generations, zero base
loads) and I17's semantic canary cannot be run, and **`0.7.0` is not bumped, tagged or published**:
its central claim would be undemonstrated. `CHANGELOG.md` keeps Phases 6, 7 and 8 together under
`## [Unreleased]`; `__about__.py` stays `0.6.0`.

### The one judgement call inside that

**`baseaicore 0.4.2` *is* fully prepared** — version bumped, changelog moved out of
`## [Unreleased]`, release commit made, wheel built and verified in a clean venv. §0.1 said "stop
short of the version bump", and in context that sentence is about `0.7.0`, whose central claim is
LA1's. BaseAiCore's release does not depend on LA1 in any way, and **H2 needs
`RuntimeProfile.adapters_registered` from PyPI** to set it. Holding baseaicore back would block
H2 for no reason and gain nothing. It is stated here so the decision is visible rather than
inferred.

---

## 2. Gate results

| Gate | What | Result |
|---|---|---|
| **A** | BaseAiCore: the field and its release | **Done.** `0.4.2` prepared, not published |
| **B** | ModelRack refuses a profile that misdescribes the server | **Done.** `ProfileMismatch`, floor at `>=0.4.2` |
| **C** | Cancellation under supervision, and no leaks | **Done.** Plus one pragma removed and its branch tested |
| **D** | The conformance suite, four adapters, every skip declared | **Done.** Verified, and made enforceable |
| **E** | The sharded-GGUF decision | **Done.** Refuse by name; decision recorded |
| **F** | The thinking control | **Done.** `SamplingParameters.think`, Ollama top-level key |
| **G** | The LA1 exit, live | **Blocked** — no adapter artefacts. §1, and §7 below |
| **H** | Docs, version, release prep | **Docs done; version deliberately not bumped** |

### Gate A — BaseAiCore, one field, one release

`RuntimeProfile.adapters_registered: bool | None = None`, beside `flash_attention` and shaped like
it, hashed into `profile_hash` like every other field. The docstring states all three meanings and
why the third exists.

**The golden is the point, and it is asserted over stored strings.** Four hashes were captured from
`0.4.1` *before* the field was added and written into the test as literals. A recomputation would
agree with itself even if both sides had moved, which is the only failure the assertion exists to
catch. One of the four is not merely a capture:

```python
GOLDEN_PROFILE_HASHES_BEFORE_ADAPTERS_REGISTERED = {
    "e06e92b4d4803b3b": RuntimeProfile(),          # SetSpec capability.evidence/1.0/unsupported.json
    "7f2686cfb80bc5ba": RuntimeProfile(context_size=8192),
    "9ce0ad7c88182054": RuntimeProfile(context_size=32_768, kv_cache_precision="q8_0", …),
    "0cee241b704806ff": RuntimeProfile(provider_options={"num_gpu": 1, "nested": {"a": 2}}),
}
```

`e06e92b4d4803b3b` is the default profile's hash **as frozen into SetSpec's
`capability.evidence/1.0/unsupported.json` golden** — a stored key from a published v1.0 payload,
not a value this repository is free to update. (The other stored hash in those goldens,
`17c2fc02b32ad4ee`, was not reproduced by any profile in a seven-field grid search; it is presumably
a hand-written fixture value rather than a computed one. Worth knowing, not worth chasing.)

Tri-state proved as three states: unset, `False` and `True` are three different hashes, and
`adapters_registered=None` stated explicitly hashes as if never mentioned.

Commits: `0df1347`, `4492644`, `8c04208`. Gate: 647 passed, **coverage 100.00 %**.

### Gate B — the refusal

New error **`ProfileMismatch` / `PROFILE_MISMATCH`**, `details` carrying `field`, `requested`,
`actual`, `model_name`. Adding a code is a minor change by the errors module's own stated rule;
nothing existing changed meaning. Deliberately **not** `CapabilityUnsupported`: nothing here is
beyond the provider, and that error tells a caller to check `capabilities()`, where there is
nothing to check.

Three decisions inside it worth carrying forward:

1. **The comparison is against the launch, not the configuration.** A new `_launched_with_adapters`
   map records whether the argv carried `--lora`. It is deliberately *not* derived from
   `_server_adapters`, which is the set the server reported back and which is empty both when
   nothing was launched **and** when `/lora-adapters` could not be read — different facts about
   memory. A registration that has arrived and not folded in is not in that server's memory, so a
   profile claiming it is refused until the restart happens. Tested by holding a stream open so the
   fold-in cannot occur.
2. **The refusal costs no process.** It runs inside `_spawn` after the registration set is computed
   and *before* the server is launched, and on the reuse paths of `_ensure_server` and `load`
   against the recorded launch. One predicate, every path, and no test observes a
   spawned-then-refused server.
3. **`load` refuses on the same terms as `generate`.** It returns a `LoadResult` carrying a
   `profile_hash`, so serving it under a lying profile records the same thing a generation would.
   The kickoff's gate-B bullet list only mentioned serving; this is the same rule, and leaving
   `load` out would have left a door open.

`adapters_registered` is **not** a launch flag and **not** part of the launch key: it describes the
server rather than configuring it, so turning it into a flag would let a caller register an adapter
by asserting one existed, and putting it in the launch key would restart a server over a claim.
Both are asserted.

Floor `baseaicore>=0.4.1,<0.5` → `>=0.4.2,<0.5`. A floor, not a dependency: the runtime set is
still `baseaicore` + `httpx`, `.importlinter` untouched. Commit `2b54bc2`.

### Gate C — cancellation under supervision, and leaks

Ten tests, and the distinction from the existing cancellation suite is the *server*: those run
against a counting transport and ask what the caller receives, these run against the fake launcher
and process table and ask what the supervised process is left as.

* A cancelled stream leaves the process running and the model resident, and the next request is
  served by **the same process** — asserted by making it.
* **The in-flight claim is never read from the private counter.** Each release is proved by a
  profile-change restart *succeeding*, which is the operation that refuses while work is in flight,
  so the assertion breaks if `_require_idle` stops consulting the claim. Proved after a cancelled,
  an abandoned and a failed stream.
* Twenty load/unload cycles leave twenty terminated processes, no live process, no pid file at any
  point after an unload, no handle, nothing resident, and nothing for `sweep_orphans()` to recover.
  Twenty generate cycles reuse one server and accumulate no claim.
* A dropped provider releases a stream it still owned.

**One behaviour change, and it is real.** The post-loop cancellation check in `_drain` was marked
`# pragma: no cover` as reachable only from another thread. A token that flips on a chosen read
reproduces that window deterministically — the read count is derived from the fixture, so an added
chunk moves it rather than quietly putting the flip back inside the loop — so the pragma is gone
and the branch is tested. **Without that branch, a stream the caller stopped in that window would
be reported as completed.** Its sibling on the next line (`if not completed`) stays pragma'd,
correctly: the `for/else` above it always returns first.

The flat-memory half needs a real server and remains an operator step, as the plan says. Commit
`16e7be0`. `llamacpp.py` is now at **zero missing lines**.

### Gate D — the conformance suite

Verified: **244 passed, 16 skipped** across six bindings — the fake in three configurations,
Ollama, OpenAI-compatible, llama.cpp. Every skip carries its reason; the twelve capability-gated
ones are all `"not declared: refusal asserted above"`, which is the point — the refusal is an
assertion in the same behaviour, never an absence. `adapter_hot_swap` and (now) `thinking_control`
are honoured-or-refused rather than skipped at all. Both live suites already name the environment
variable and the artefacts each skip needs.

Then made enforceable, because **nothing checked the "every" in "every adapter passes the same
suite"**: a binding deleted, renamed or lost in a merge would have shrunk the suite in silence —
same green summary, one adapter fewer. Two tests now assert the six bindings exist and that the
fake is bound in three configurations. Commit `8ecc1b4`.

### Gate E — the sharded-GGUF decision

**Decided: refuse by name.** The alternative — serve a split base under a stated multi-file digest
rule — invents an identity for a set of files, which is an ADR and an identity change, not a Phase
8 bullet, and the kickoff recommended against it.

Behaviour is otherwise unchanged: shards stay out of `list_models()` and a split base is still not
servable. What changes is the *failure*. `resolve("big")`, `inspect_model` and `generate` against
the group name, a shard name or the filename now raise `ModelNotFound` with `reason="sharded"`, the
group name, the shard count, the shard paths and the `llama-gguf-split --merge` command — instead
of "no model matching that", which left an operator looking at a file on disk the adapter would not
explain. A name that is simply absent grows no reason it has not got.

`shard_group_name()` replaces the `is_shard()` call at discovery, so the refusal consults what the
last discovery already recorded rather than rescanning; the defensive `None` branch that pairing
would have left behind is gone with it. `is_shard()` stays for the live tests. Commit `a03aa88`.

### Gate F — the thinking control

`SamplingParameters.think: bool | None = None`, tri-state for exactly the reason
`adapters_registered` is. The Ollama adapter emits Ollama's own **top-level** `think` key — inside
`options` it would be silently ignored by the runtime, indistinguishable from a request that asked
for nothing, which is the failure the whole change exists to remove. llama.cpp refuses in `_route`
before a server is spawned; the OpenAI-compatible adapter refuses in `_build_body` before a byte is
sent; `FakeProvider` refuses through `_require_declared`. All three name `thinking_control`.

The byte-identical claim is **pinned by a golden over the whole request body on both Ollama
endpoints**, not asserted:

```python
assert json.loads(chat.calls.last.request.content) == {
    "model": _MODEL, "stream": False,
    "messages": [{"role": "user", "content": "Explain KV caching."}],
}
```

`FakeProvider` honours it where declared: `think=False` suppresses the scripted reasoning. The
conformance suite gained the capability's row plus the compatibility half, and **no new skip**.

Not done, deliberately: a LoadCoach task-profile field. That is a later row.

No live Ollama numbers for `think=False` were taken — the exit condition is that the capability is
*reachable*, and it is; the number LoadCoach's later row wants is one `ollama` run away and is
noted in §8. Commit `b059989`.

### Gate H — docs and release prep

`docs/providers.md` regenerated and **unchanged**: Phase 8 added no capability flag, only a way to
reach one already declared. Spec §7, §10 and §13 are final. §18 pins the tested `llama-server`.

**Verified against a locally built wheel** (scratchpad, never the repo): `python -m build`, then a
throwaway venv with `baseaicore-0.4.2-py3-none-any.whl` + `modelrack-0.6.0-py3-none-any.whl`,
`import modelrack`, `ProfileMismatch.code == "PROFILE_MISMATCH"`, `SamplingParameters(think=False)`,
`RuntimeProfile(adapters_registered=True)`, and **`demo_modelrack.py` ran end to end** against that
venv. The wheel says `0.6.0` because the version is deliberately unbumped; everything Phase 8 added
is in it. Commit `d0d3b0a`.

---

## 3. Anything this prompt said that turned out not to be true

The most useful section of the last six handoffs, so: four items, one of them a correction to a
machine fact.

1. **§0.3's decision was already made.** The prompt asked whether the fake should gain a
   configuration declaring `thinking_control = True` so the conformance suite has a positive case.
   `FULL_CAPABILITIES` has declared it **since Phase 2** (`providers/_fake_script.py:64`). No new
   configuration was needed; the positive path had a non-live home all along, and
   `TestFakeProviderConformance` exercises it.
2. **The cancellation `# pragma: no cover` pair is not a pair — one half is reachable.** §7 said to
   check them and remove a pragma if the gate made either reachable. The post-loop
   `cancel.is_cancelled` check *is* reachable, deterministically, with a token that flips on a
   chosen read; the pragma is gone and the branch is tested. The other half (`if not completed`)
   is genuinely unreachable and stays. **The identical branch exists in
   `providers/openai_compatible.py:836` and is still pragma'd** — same shape, same technique would
   cover it, out of this row's scope. Noted for whoever touches that adapter next.
3. **The tested `llama-server` build cannot be pinned from `--version`.** The kickoff said to pin
   the tested build string. The CUDA build on this machine reports
   `version: 0.3.0-dev (build 1, commit c5a5535)` — `build 1` because the tree was configured
   without the git stamp. `git -C ~/ai/tools/llama.cpp describe --tags` gives **`b10792`**, and
   `HEAD` is **`c5a5535`**. Spec §18 pins the tag *and* the commit and says why, and notes that a
   recorded run still carries whatever `/props` reports, which may differ.
4. **`_select_adapter`'s `# pragma: no cover` at what was `llamacpp.py:1763` is still unreachable.**
   §16(b) asked whether Phase 8 made it live. It did not: Phase 8 added no second reason to defer a
   restart, so `_ensure_server` still folds pending adapters in whenever nothing is in flight, and
   an idle server with a pending adapter cannot be reached. It stays pragma'd, with its reason.

Everything else in §0 held, including the two facts marked "confirm": all three repos were clean
and level with `origin` (`docs` at `7b60a0e`, `py/ModelRack` at `b07fa3f`, `py/BaseAiCore` at
`c2103c6` — the `docs` head was one commit past the prompt's `c8eb72f`, a `.gitignore` update), and
ModelRack's venv is Python 3.13.15 holding `baseaicore 0.4.1`.

---

## 4. What H2 inherits

**The published surface it must pin** (once the operator publishes): `baseaicore 0.4.2` and, later,
`modelrack 0.7.0`. **H2 cannot start against PyPI until `baseaicore 0.4.2` is published** — it needs
`RuntimeProfile.adapters_registered` to exist. It does *not* need `modelrack 0.7.0` for that field,
only for the refusal that checks it.

**`adapters_registered`, and who sets it.** ADR-0074's consequence, restated because H2 is the row
that implements it: **LoadCoach sets `True` where the provider has registrations and `False` where
it has none — never `None`.** A tier configured with an empty adapters directory is `False`. `None`
should survive only in callers that predate the field. Getting this wrong is not an error anyone
will see: it is a profile hash that silently merges two different measurements, which is the whole
reason the field exists.

**What ModelRack will refuse.** `ProfileMismatch` is raised from `generate`, `stream` **and**
`load`. LoadCoach's error mapping needs a row for `PROFILE_MISMATCH`; it is permanent for the
request as written (retrying changes nothing), so it belongs with `ADAPTER_NOT_FOUND` rather than
with `restart_pending`.

**What turned out awkward to consume in `list_adapters()` / `register_adapters()`** — read-only
walk, as §16(a) asked:

* `list_adapters()` returns a **snapshot computed from what the last spawn recorded plus what is
  registered now**. Nothing persists. Two consequences for a UI: the same registration can be
  `REGISTERED` and then `AWAITING_BASE` with nothing having changed except a server exiting, and
  the status of a registration for a base whose server has never run is not "not yet" but
  `AWAITING_BASE`. Both are honest; neither is obvious from the type.
* `register_adapters()` **replaces by name** and returns `None`. A rescan that dropped an adapter
  from the directory does **not** remove it from the provider — there is no `unregister`. LoadCoach's
  `adapters scan` therefore cannot express "the directory is now the truth" without constructing a
  new provider. That is the one gap worth deciding at H2, and it is a real one: a stale registration
  keeps a name reservable and keeps forcing a restart at the next idle.
* Neither method takes or returns a `RuntimeProfile`, so **the provider cannot tell a caller what
  `adapters_registered` it should have set**. That is by design (ADR-0074 rejects a provider
  stamping the profile), but it means LoadCoach must derive the boolean from *its own* knowledge of
  what it handed the provider, not from `list_adapters()`. Deriving it from `list_adapters()` would
  be wrong in exactly the pending-restart window.
* `AdapterState.reason` is prose intended for a person. Nothing should parse it; the status enum is
  the machine-readable half.

**No downcast is required** for any of the above — F3's two protocol methods hold up. The awkward
parts are semantic, not structural.

---

## 5. The gate, run in each repo

**BaseAiCore** (`/home/jpk/ai/suite/py/BaseAiCore`, `.venv/bin/python -V` → Python 3.13.15):

```
.venv/bin/ruff format --check .                                41 files already formatted
.venv/bin/ruff check .                                         All checks passed!
.venv/bin/mypy src tests                                       no issues in 35 source files
.venv/bin/lint-imports                                         2 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov
                                                               647 passed, 7 deselected
                                                               coverage 100.00 %
```

**ModelRack** (`/home/jpk/ai/suite/py/ModelRack`, `.venv/bin/python -V` → Python 3.13.15):

```
.venv/bin/ruff format --check .                                57 files already formatted
.venv/bin/ruff check .                                         All checks passed!
.venv/bin/mypy src tests                                       no issues in 51 source files
.venv/bin/lint-imports                                         2 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov
                                                               1423 passed, 16 skipped,
                                                               25 deselected, coverage 99.82 %
.venv/bin/python -m pytest tests/contract/test_conformance.py -q -rs
                                                               244 passed, 16 skipped,
                                                               every skip with its reason
```

One transient worth recording: after bumping `__about__.py` to `0.4.2`,
`tests/test_packaging.py::test_the_version_is_a_release_number_the_metadata_agrees_with` failed
against the editable install's stale `0.4.1` metadata. `pip install -e ".[dev]"` fixed it and the
suite is green. The test did its job.

**Mirrors.** Every workspace `docs/` edit was copied into the component's `docs/` and proved with
`cmp` before each commit: `packages/baseaicore/{spec.md,development-plan.md}` →
`py/BaseAiCore/docs/`, `packages/modelrack/spec.md` → `py/ModelRack/docs/`. All byte-identical.
`py/BaseAiCore/docs/api.md` and `py/ModelRack/docs/providers.md` are generated, not mirrored, and
were regenerated from the live surface.

---

## 6. Commits

**docs** (`3bc774f` … + the row update): `docs(baseaicore): adapter-enabled serving is a
runtime-profile field (ADR-0074)`, `docs(modelrack): a profile that misdescribes the server is
refused (ADR-0074)`, `docs(modelrack): a split GGUF is refused by name, not skipped in a debug log`,
`docs(modelrack): the thinking control is reachable from the request (ADR-0007 rule 2)`,
`docs(modelrack): Phase 8 — the surface, the errors and the tested build`, and the
`outstanding-work.md` row update carrying this handoff.

**py/BaseAiCore** (3): `0df1347` docs mirror, `4492644` the field, `8c04208` `chore(release):
baseaicore 0.4.2`.

**py/ModelRack** (6): `2b54bc2` the refusal, `16e7be0` cancellation and leaks, `a03aa88` the
sharded refusal, `b059989` the thinking control, `8ecc1b4` the conformance suite, `d0d3b0a` docs.

No `git add -A` anywhere; every path staged by name. No push, no push dry-run, no tag, no publish.

---

## 7. What is left for the operator, in order

1. **Push three repos** — `docs`, `py/BaseAiCore`, `py/ModelRack` — and watch CI.
2. **Publish `baseaicore 0.4.2`** (tag, then the trusted-publisher flow; `E1_E2_RELEASE_RUNBOOK.md`).
   Nothing waits on LA1 for this, and **H2 is blocked until it lands**.
3. **Produce the adapter artefacts.** `docs/history/F3_HANDOFF.md` §6 states exactly what, in five
   steps, so no conversation is needed. In short: two LoRA adapters trained on **one** of the four
   bases already under `~/ai/models/llm` (a digest mismatch is refused, fail closed, so an adapter
   for a different quantization of the same model will not do), each converted with
   `convert_lora_to_gguf.py` from `~/ai/tools/llama.cpp`, and the two **behaviourally
   distinguishable** — the canary asserts they answer one prompt *differently* at temperature 0.
4. **Run gate G**, the LA1 exit, on the reference machine with the real `llama-server`:

   ```bash
   export MODELRACK_LLAMACPP_MODELS=~/ai/models/llm
   export MODELRACK_LLAMACPP_ADAPTERS=/path/a.gguf:/path/b.gguf
   export MODELRACK_LLAMACPP_ADAPTER_BASE=<the base's model name, no .gguf>
   export MODELRACK_REQUIRE_LLAMACPP=1
   cd /home/jpk/ai/suite/py/ModelRack && .venv/bin/python -m pytest -m live \
       tests/live/test_llamacpp_live.py -rs -s
   ```

   I16 wants three registered adapters and twenty alternating generations with **zero base loads**,
   asserted from the process table and from load timings; I17's canary wants two adapters
   registering with `DIGEST` confidence, distinct continuations of a shared prefix, and a bare base
   matching neither. Record memory across the twenty cycles — that is the flat-memory half the
   injected launcher cannot assert.
5. **Then** bump `modelrack` to `0.7.0`, move the whole `## [Unreleased]` block to `[0.7.0]` (it
   carries Phases 6, 7 **and** 8), tag, publish — **after** `baseaicore 0.4.2` is on PyPI, or the
   `>=0.4.2` floor is unresolvable for anyone installing from the index.
6. **Verify the published wheels** in a clean venv and re-run `demo_modelrack.py` against them. The
   local-wheel verification is done (§2, gate H); the published one is yours.

---

## 8. Small things worth someone's time, none blocking

* **`openai_compatible.py:836`** carries the same post-loop cancellation branch this row proved
  reachable in llama.cpp, still marked `# pragma: no cover`. The flip-on-read token technique
  transfers directly.
* **`think=False` against a live Ollama** would give LoadCoach's later row the number it wants:
  G2 measured `tools.plan` on gpt-oss:20b at 1/6 empty at `max_output_tokens = 4096` and 3/6 at
  8192, median 58 s → 171 s. It is one run away now that the control is reachable. Not an exit
  condition — reachability was.
* **`register_adapters()` has no inverse** (§4). Worth a decision at H2 rather than a discovery.
* **SetSpec's `17c2fc02b32ad4ee`** appears in six golden payloads as a `runtime_profile_hash` and
  matches no `RuntimeProfile` in a seven-field grid search. Almost certainly a hand-written fixture
  value. Harmless; surprising if someone assumes every golden hash is computable.
