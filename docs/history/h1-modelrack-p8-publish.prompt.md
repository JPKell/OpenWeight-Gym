# Kickoff — H1: ModelRack Phase 8 — cancellation, leaks, ADR-0074's mechanism, the thinking control, and `0.7.0`

**Row:** H1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · high**. The row's Model column still reads as a split (leak/cancellation
reasoning on Opus, conformance + docs + publication on Sonnet); [model-assignment §3.5](docs/roadmap/model-assignment.md)
settled at F1 that a phase gets **one** model, the stronger of any pair. Run it whole on Opus 5 · high
and record no deviation.
**Repositories, in this order:** `/home/jpk/ai/suite/docs` (first, always),
`/home/jpk/ai/suite/py/BaseAiCore` (one field, one release), then `/home/jpk/ai/suite/py/ModelRack`
(the row's weight).
**Ships:** **two releases prepared, neither pushed.** `baseaicore 0.4.2` (ADR-0074's field) must be
on PyPI before ModelRack can pin it, and `modelrack 0.7.0` carries Phases 6, 7 and 8 together.
Version bumps, changelogs and release commits are yours; **`git push`, the tag and the publish are
the operator's** (standing instruction of 2026-09-04). Say so plainly in the handoff, and do not run
a push dry-run.
**Overnight:** allowed by [§2.12](docs/roadmap/model-assignment.md) (batch H is not on the
never-overnight list) — but the LA1 exit is a live GPU session and the publication is irreversible,
so run it daytime unless the operator says otherwise.
**Runs after:** D3 (Phase 6, `docs/history/D3_HANDOFF.md`) and F3 (Phase 7, `docs/history/F3_HANDOFF.md`).
**Runs before:** H2 (LoadCoach 1.1), which consumes `modelrack 0.7.0` and
`RuntimeProfile.adapters_registered` from PyPI, and H4 (FreeWeight's A/B, which measures against
that field).
**Not in this session:** anything in LoadCoach, FreeWeight or IdeaPress; the vLLM adapter;
embeddings; an async API; tokenization; multi-modal input (all Phase 8 "Deferred").

---

## 0. Machine facts, verified 2026-09-05 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **All four repos are clean and level with `origin`.** `docs` at `c8eb72f`, `py/ModelRack` at
  `b07fa3f` (F3's five commits are pushed), `py/BaseAiCore` at `c2103c6`. **Confirm** `git status -sb`
  in each at the start and at the end (CLAUDE.md, working-tree integrity).
* **ModelRack is `0.6.0` in `__about__.py` and on PyPI; its `CHANGELOG.md` `## [Unreleased]` already
  holds Phase 6 and Phase 7.** Phase 8's entries join them and the whole block moves to `[0.7.0]`.
* **BaseAiCore is `0.4.1` on PyPI, and its `## [Unreleased]` holds one documentation fix** (a
  `README`/quickstart snippet). That fix ships inside `0.4.2` with the new field; nothing else is
  pending there.
* **ModelRack's venv is Python 3.13.15** and holds `baseaicore 0.4.1`. There is no python3.12 on
  this host. Name the interpreter and every exact invocation (M5C-13).
* **Coverage is 99.82 % and the gate is green at `b07fa3f`** — Phase 8 starts with no debt.
* **The in-flight counter exists** (`providers/llamacpp.py:642`, `_InFlightLease` at `:1257`), which
  is what makes "a cancelled stream leaves a usable server **and a zeroed claim**" a testable
  sentence rather than a hope. `GenerationRequest.cancel` and `FinishReason.CANCELLED` exist
  (`types.py:544`, `:152`).
* **Two `# pragma: no cover` branches in `llamacpp.py` are Phase 8's business** — `:1763` (an idle
  server with a pending adapter, unreachable because `_ensure_server` folds pending adapters in
  whenever nothing is in flight) and `:2126`/`:2128` in the cancellation path. If Phase 8 adds a
  second reason to defer a restart, the first becomes live and needs a test; the other two are
  precisely what gate C is about.
* **There is still no LLM LoRA adapter GGUF on this machine.** `find /home/jpk/ai/models -iname
  '*lora*'` returns only Wan 2.2 video-diffusion safetensors, exactly as at F3. **This blocks two
  exit conditions**, I17's semantic canary and I16's twenty-generation run — see §0.1, which is the
  first thing to settle.
* **`SamplingParameters` has no `think` field** (`types.py:365`–`:371`) while
  `providers/ollama.py:156` declares `thinking_control=True`. G2 measured what that costs; §0.3.
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to the
  operator.

## 0.1 Gate 0 — the artefact question, before anything else

The row is titled "P8 → publish (**LA1 done**)". LA1's exit condition (adapter roadmap §3, I16) is a
live run on the reference machine: one llama-server base, three registered adapters, twenty
generations alternating adapters, **zero base loads**, asserted from the process table and load
timings. I17's semantic canary needs the same artefacts. `docs/history/F3_HANDOFF.md` §6 states
exactly what an operator must produce, and none of it exists yet.

**So, at the very start of the session, check** (`find /home/jpk/ai/models -iname '*.gguf' | head`,
and whether `MODELRACK_LLAMACPP_ADAPTERS` names two real files):

* **If the artefacts exist** — run the row whole, including gate G and publication prep.
* **If they do not** — build gates A–F and H's documentation, run every fakeable assertion, and
  **stop short of the version bump.** Do not publish `0.7.0` with LA1's exit unproved and do not
  fabricate a pass; the canary already skips with its requirements named, which is the honest
  outcome. Put the blocked half at the top of the handoff as a single operator step, and leave the
  changelog under `## [Unreleased]`. A row that lands "everything but the live exit and the tag" is
  a good outcome; a published `0.7.0` whose central claim was never demonstrated is not.

This is a judgement the session takes on evidence at minute one, not a question to sit on.

## 0.2 ADR-0074's mechanism — two repositories, one decision already taken

[ADR-0074](docs/adr/0074-adapter-enabled-serving-is-a-runtime-profile-field.md) is **accepted**; it
is not reopened here (`docs/history/F3_HANDOFF.md` §9.3). It is built, in two pieces:

1. **BaseAiCore gains `RuntimeProfile.adapters_registered: bool | None = None`**, beside
   `flash_attention` and shaped like it. **Tri-state is load-bearing**: `profile_hash` already drops
   `None` fields from the canonical JSON precisely so an added optional field is additive, so every
   stored hash in all three databases stays put — a `bool = False` default would be hashed and move
   every profile hash in the suite. Prove the non-move over an **existing golden**, not by assertion
   (Phase 8 AC 4).
2. **ModelRack refuses a profile that misdescribes the server it would use** — the
   `context_configurable` discipline (ADR-0023 §4, spec §11.10) one level up. `None` disagrees with
   nothing and is always served, so every caller predating the field is unaffected. `True` against a
   server launched with no registrations, and `False` against one with them, are both refusals with
   a typed reason.

The pin moves with it: `baseaicore>=0.4.1,<0.5` → `>=0.4.2,<0.5`, a **floor**, not a new dependency.
The runtime set stays exactly `baseaicore` + `httpx`; do not touch `.importlinter`.

**Ordering:** BaseAiCore's release must be *prepared and committed* before ModelRack's floor moves,
and ModelRack's own gate can run against the local editable BaseAiCore. State in the handoff that
`modelrack 0.7.0` must not be published before `baseaicore 0.4.2` is on PyPI, because the floor
would be unresolvable for anyone installing from the index.

## 0.3 The thinking control — scheduled into this row on 2026-09-05

G2's gate E found ModelRack's Ollama adapter declaring a capability nothing can ask for:
`thinking_control = True` at `providers/ollama.py:156`, no `SamplingParameters.think`, no top-level
`think` key in `_build_request`, and `runtime_profile.provider_options` merging into `options`,
where Ollama's `think` does **not** live. **A capability declared and unreachable is ADR-0007 rule 2
from the request side.** `docs/history/G2_HANDOFF.md` §4–§5 has the measurement: `tools.plan` on
gpt-oss:20b returns an empty document 1/6 at `max_output_tokens = 4096` and 3/6 at 8192, every empty
answer `done_reason=length` with `eval_count` equal to the budget, median latency 58 s → 171 s. The
output budget is **not** the lever; thinking control is.

Shape: `SamplingParameters.think: bool | None = None` — tri-state, so an unset request is
byte-identical to today's — emitted as Ollama's **top-level** key by that adapter, and
`CapabilityUnsupported` from every adapter declaring `thinking_control = False` (llama.cpp, the
OpenAI-compatible adapter, and the fake by default). Whether a LoadCoach task profile may *ask* for
it is a later row: a profile field for a control that cannot be sent would be configuration that
lies.

Decide and record: whether the fake gains a configuration that declares `thinking_control = True`
so the conformance suite has a positive case, or whether the capability's positive path is proved
only against Ollama (recommendation: the fake declares it in one of its three configurations —
otherwise the suite's `thinking_control` row is a skip everywhere but a live test).

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb
git -C /home/jpk/ai/suite/py/BaseAiCore status -sb
git -C /home/jpk/ai/suite/py/ModelRack status -sb
cd /home/jpk/ai/suite/py/ModelRack && source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show baseaicore | grep -E "^(Name|Version)"
```

Every scratch model directory, pid file, log and built wheel goes in the session scratchpad —
**never** the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory. Nothing at the workspace root is versioned.
* The finish line, **in each repo you touch**: `ruff format --check . && ruff check . &&
  mypy src tests && lint-imports && pytest -m "not live and not performance"` green,
  `CHANGELOG.md` updated, **one Conventional Commit per gate**.
* `pytest-randomly` is on; a seed-only failure is a real bug.
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names, keyword-only optionals and booleans, frozen slotted value objects,
  `mypy --strict`, line length 100.
* Coverage floor: **95 %** — these are shared packages, and ModelRack is at 99.82 %.
* **Never `git add -A`.** Stage named paths. Every workspace `docs/` edit is mirrored into
  `py/ModelRack/docs/` and `py/BaseAiCore/docs/` byte-identically and **`cmp`-proved** in the
  commit message.

## 3. Reading list, in this order

1. `docs/history/F3_HANDOFF.md` **§6** (what the canary needs), **§7** (eight things the last
   prompt got wrong — read them all; they are this row's starting facts), **§8** (what H1 inherits)
   and **§9** (what is settled and must not be reopened: the complete-`lora` reading of ADR-0063,
   the two new `Provider` methods, the profile-change restart refusing while work is in flight).
2. `docs/packages/modelrack/development-plan.md` **Phase 8** — the work list, the tests, the seven
   acceptance criteria. It was written at F3 in the house shape, so unlike F3 this row inherits a
   plan; read it as the specification it is.
3. `docs/roadmap/adapter-roadmap.md` **§4.1 P8**, **§3 LA1** (the exit condition, verbatim) and
   **§7 I16/I17**.
4. [ADR-0074](docs/adr/0074-adapter-enabled-serving-is-a-runtime-profile-field.md) in full, then
   ADR-0060 (what it implements), ADR-0023 (the profile and its hash), ADR-0062 (registration is
   launch-time, which is what makes serving mode a profile fact).
5. `docs/packages/modelrack/spec.md` **§7** (the public surface), **§10** (data ownership), **§11.10**
   (`context_configurable`), **§13** (the error table) — all three are declared "final" by Phase 8.
6. `docs/history/D3_HANDOFF.md` **finding 6** (sharded GGUFs, skipped at discovery with a debug log)
   and `docs/history/G2_HANDOFF.md` **§4–§5** (the thinking-control measurement).
7. `docs/standards/` on packaging and releases, plus `E1_E2_RELEASE_RUNBOOK.md` at the workspace
   root — the trusted-publisher flow ModelRack already used for `0.6.0`.

---

## 4. The shape of the work — eight gates

A → BaseAiCore's field and its release. B → ModelRack's refusal and the floor. C → cancellation and
leaks. D → the four-adapter conformance run. E → the sharded-GGUF decision. F → the thinking
control. G → the live LA1 exit (artefact-gated, §0.1). H → docs, version, release prep.

Gates A and B are the publication blocker; do them first so that if the session is cut short, the
thing that must not ship without them is the thing that is done.

## 5. Gate A — BaseAiCore: one field, one release

* Workspace `docs/` first (the packages/baseaicore spec and plan note the field), mirrored into
  `py/BaseAiCore/docs/`, `cmp`-proved.
* `RuntimeProfile.adapters_registered: bool | None = None` with a docstring that states all three
  meanings — not stated / stated-clean / stated-registered — and *why* it is tri-state.
* **The golden**: an existing profile that does not set the field hashes to exactly what it hashed
  before. Assert over a stored value, not a recomputation.
* Version to `0.4.2`, changelog moved out of `## [Unreleased]` (it carries the pending docs fix
  too), release commit prepared. **No tag, no publish, no push.**

**Commits:** `docs(baseaicore): adapter-enabled serving is a runtime-profile field (ADR-0074)`,
`feat(runtime): RuntimeProfile records whether adapters were registered`,
`chore(release): baseaicore 0.4.2`.

## 6. Gate B — ModelRack refuses a profile that misdescribes the server

* The comparison is between the request's `RuntimeProfile.adapters_registered` and the registration
  set the server **was launched with** — not the set currently configured, which can differ while a
  restart is pending. Say which in the docstring; a pending registration that has not been folded in
  is the interesting case and it needs a test.
* Typed refusal with a reason a caller can read, in the spec §13 error table.
* Floor moves to `baseaicore>=0.4.2,<0.5`. Runtime set unchanged; `.importlinter` untouched.
* Tests: `None` is always served (the compatibility case, and it is the one every existing caller
  hits); `True` against a clean server refuses; `False` against a registered server refuses; a
  matching profile serves.

**Commit:** `feat(llamacpp): a profile that misdescribes the server is refused (ADR-0074)`.

## 7. Gate C — cancellation under supervision, and no leaks

* A token fired mid-stream against a spawned server closes the connection within one chunk
  boundary, **leaves the server running and usable**, and returns the in-flight count to zero. The
  next request against the same server succeeds — assert that, not merely the absence of an error.
* Twenty `load`/`unload` cycles leave no orphan process, no pid file and no handle, asserted through
  the injected `ProcessTable`/`FakeLauncher`, never by watching `ps`.
* An abandoned stream and a dropped provider both release every handle (the `weakref.finalize`
  path F3 already proved has teeth).
* **Check the cancellation `# pragma: no cover` pair at `llamacpp.py:2126`/`:2128`** — if this gate
  makes either reachable, it gets a test and the pragma goes.
* The flat-memory half needs a real server and is an **operator step**, run once at gate G and
  recorded with its numbers. Do not claim it from the fake.

**Commit:** `test(llamacpp): cancellation leaves a usable server, and twenty cycles leave nothing behind`.

## 8. Gate D — the conformance suite, four adapters, every skip explicit

* Green across fake (three configurations), Ollama, OpenAI-compatible and llama.cpp, with every
  capability-gated skip **declared** rather than silently absent — including `adapter_hot_swap` and,
  after gate F, `thinking_control`.
* A skip that exists because an environment variable is unset must name the variable and what it
  needs, the way `tests/live/test_llamacpp_live.py` already does.

**Commit:** `test(conformance): the suite is green for all four adapters, every skip declared`.

## 9. Gate E — the sharded-GGUF decision (D3 finding 6)

A sharded base is skipped at discovery with a debug log today. Identity is a hash over several files
and llama-server takes only the first, so "serve it" means deciding what its digest *is*. **Decide
and record**: serve with a stated multi-file digest rule, or **refuse with a named reason** that
reaches the caller (recommendation: refuse, named — a silent skip is a model an operator can see on
disk and cannot explain the absence of, and inventing a multi-file identity rule is an ADR, not a
Phase 8 bullet). Whichever way it goes, the debug log stops being the only trace.

**Commit:** `feat(llamacpp): a sharded base is refused by name, not skipped in a debug log` (or the
serving equivalent).

## 10. Gate F — the thinking control

* `SamplingParameters.think: bool | None = None`, tri-state; the Ollama adapter emits the
  **top-level** `think` key; every adapter declaring `thinking_control = False` raises
  `CapabilityUnsupported`.
* A request that does not set it produces a **byte-identical** body to today's — pin that with a
  golden, the way F3 pinned the adapter-free request body at `6c686f5`.
* Conformance gains the capability's row (see §0.3's decision).
* If a live Ollama run is available, record what `think=False` does to G2's numbers. It is not an
  exit condition — the exit condition is that the capability is *reachable* — but it is the number
  LoadCoach's later row will want.

**Commit:** `feat(ollama): a request may ask for reduced thinking, and every other adapter refuses`.

## 11. Gate G — the LA1 exit, live (artefact-gated)

Only if §0.1 said the artefacts exist. On the reference machine, with the real `llama-server`
(`~/ai/tools/llama.cpp`, the CUDA build; pin the tested build string in the docs — ADR-0062's
consequence):

1. One base, **three** registered adapters; twenty generations alternating adapters; **zero base
   loads**, asserted from the process table *and* from load timings, not from the absence of
   complaint. Verbatim output in the handoff.
2. I17's semantic canary passes: both adapters register with `DIGEST` confidence, the two produce
   different continuations of a shared cache-worthy prefix, and the bare base matches **neither**.
3. Memory across the twenty cycles, measured and recorded.

**Commit:** `test(live): LA1's exit — twenty alternating generations, zero base loads`.

## 12. Gate H — docs, version, release prep

* `docs/providers.md` regenerated; spec §7, §10 and §13 final; the tested llama.cpp build pinned in
  the documentation.
* Workspace `docs/` first, mirrors `cmp`-proved.
* Version to `0.7.0`, the whole `## [Unreleased]` block moved to `[0.7.0]` (Phases 6, 7 and 8
  together), release commit prepared.
* **Verify against a locally built wheel** — `python -m build` into the scratchpad, install into a
  throwaway venv, import, and run `demo_modelrack.py` against it. The published-wheel verification
  is an operator step **after** they push and tag, and the handoff says so.
* **No tag, no publish, no push.**

**Commits:** `docs(modelrack): Phase 8 — the surface, the errors and the tested build`,
`chore(release): modelrack 0.7.0`.

## 13. Exit conditions — Phase 8's seven, plus this row's two

1. Twenty load/unload cycles leave nothing behind — no process, no pid file, no handle.
2. A cancelled stream leaves a usable server and a zeroed in-flight count.
3. The conformance suite passes for all four adapters, every skip declared.
4. A profile that misdescribes the server is refused, **and** a profile that does not mention
   `adapters_registered` hashes exactly as it did before the field existed — asserted over an
   existing golden.
5. **LA1's exit demonstration**: one base, three adapters, twenty alternating generations, zero base
   loads (artefact-gated, §0.1).
6. `baseaicore 0.4.2` and `modelrack 0.7.0` are prepared, changelogs moved, wheels built and
   verified locally; **publication is the operator's**, and the handoff states the order
   (`baseaicore` first).
7. Coverage ≥ 95 % in both repos.
8. `SamplingParameters.think` reaches Ollama's top-level key, every other adapter refuses it, and an
   unset request is byte-identical to today's.
9. Workspace `docs/` and both mirrors `cmp`-identical.

## 14. Closing duties

1. Full gate in each repo; interpreter and exact invocations named (M5C-13).
2. **`H1_HANDOFF.md` at the workspace root**, house shape: gate results; the §0.1 artefact
   judgement and what it cost; the sharded-GGUF decision and its alternatives; the thinking-control
   shape and any live numbers; the LA1 evidence verbatim; **what H2 inherits** — the published
   surface it pins, `adapters_registered` and who must set it (ADR-0074's consequence: LoadCoach
   sets `True`/`False`, never `None`), and anything in `list_adapters()`/`register_adapters()` that
   turned out awkward to consume; **and anything this prompt said that turned out not to be true** —
   that section has been the most useful part of the last six handoffs.
3. Say plainly what is left for the operator: push three repos, publish `baseaicore 0.4.2`, then tag
   and publish `modelrack 0.7.0`, then verify the published wheel and re-run the demos against it.
4. Record any model deviation ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
5. Update the H1 row in `docs/roadmap/outstanding-work.md` to **Done**, in the house form: date,
   commits, what held, what did not, what the next rows inherit.

## 15. Stop rules

* **Do not publish `modelrack 0.7.0` with LA1's exit unproved.** A skip that names what it needs is
  an honest outcome; a green claimed from the fake is not.
* **Do not reopen F3's settled decisions** (`docs/history/F3_HANDOFF.md` §9.2): the complete-`lora`
  reading of ADR-0063, the two new `Provider` methods, the profile-change restart refusing while
  work is in flight.
* **Do not reopen ADR-0074.** It is accepted; build it.
* **Do not add a dependency.** The runtime set is `baseaicore` + `httpx`; the only permitted change
  is the floor. Never weaken `.importlinter`.
* **Do not add a LoadCoach-side profile field for the thinking control** — that is a later row, and
  a profile field for a control that could not be sent would be configuration that lies.
* **Do not build the vLLM adapter, embeddings, an async API, tokenization or multi-modal input.**
* **Do not `git push`, tag or publish.** Never `git add -A`; never overwrite an unversioned
  workspace-root file; never leave a tree dirty at a gate boundary.

## 16. If you finish with capacity left

Read-only, in priority order: (a) **what H2 needs from the adapter surface** — walk
`list_adapters()`/`register_adapters()` as LoadCoach will call them (a directory scan, a rescan, a
per-request selection) and write down every place it would have to downcast or guess. (b) The
`# pragma: no cover` at `llamacpp.py:1763` — whether Phase 8 made it reachable. (c) Whether
`docs/providers.md` and the spec's §13 error table now name every refusal the four adapters can
raise, including the two this row added.
