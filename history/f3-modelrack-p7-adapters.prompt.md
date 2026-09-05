# Kickoff — F3: ModelRack Phase 7 — adapters

**Row:** F3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · xhigh**, as scheduled. The prefix-reuse property is exactly the
intermittent-defect shape, and the conformance-test design is the judgment this row is paying for.
**Repositories:** `/home/jpk/ai/suite/docs` (first — see §0.1), then `/home/jpk/ai/suite/py/ModelRack`,
then `docs` again to close the row.
**Ships:** nothing to PyPI. P7 rides the **0.7.0** release at row **H1**, together with D3's
unreleased P6 work. Changelog under `## [Unreleased]`, **no version bump, no tag, no publish**.
**Overnight:** **no.** §2.12 keeps security- and correctness-critical rows off the overnight
schedule, and this row's central deliverable is a *correctness* test whose failure is silent.
Daytime, reviewed.
**Runs after:** D3 (Phase 6). Flexible in the schedule — it is placed here for model adjacency.
**Not in this session:** cancellation under supervision, leak tests, the four-adapter conformance
run and publication (all **P8**); LoadCoach's adapter routing (**LA2 / LoadCoach 1.1**);
FreeWeight's subject enumeration (**FreeWeight 1.1**).

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Do not re-derive these; do **confirm** the ones marked.

* **`py/ModelRack` `main` is at `dead52a`**, clean, level with `origin/main`, CI green. Version
  `0.6.0` is on PyPI; **Phase 6's `LlamaCppProvider` is committed but unreleased**, sitting under
  `## [Unreleased]`. **Confirm** with `git status -sb` at the start and the end.
* **`llama-server` is installed and on PATH** at `~/.local/bin/llama-server` → the CUDA `b10792`
  build at `~/ai/tools/llama.cpp` (D3). So the `-m live` journey can actually run here. It needs the
  CUDA include overlay only to *rebuild*, not to run.
* **`tests/live/test_llamacpp_live.py` exists and passed at D3.** Extending it is the honest way to
  demonstrate this phase; `-m live` stays excluded from the default gate.
* **What already exists, and what P7 adds** — confirm each:
  * `baseaicore` **has** `AdapterIdentity` and `verify_adapter_base_compatibility`
    (`baseaicore.adapter`, exported at package level). **Do not redefine adapter identity in
    ModelRack.**
  * `setspec` 0.6.0 **has** `model.adapter_manifest` 1.0 — schema, goldens (`full.json`,
    `name_only.json`) and `AdapterManifestOut`/`In` exported from **`setspec.artifacts`** (not from
    `setspec` top level). See §0.2 before you reach for it.
  * `modelrack.provider.ProviderCapabilities` has **13** flags today (`streaming`, `tool_calling`,
    `structured_output`, `json_mode`, `token_counts`, `token_level_chunks`, `thinking_control`,
    `logprobs`, `force_unload`, `residency_query`, `kv_metrics`, `context_configurable`,
    `embedding`) — **`adapter_hot_swap` is not among them. You add it**, defaulting `False` like
    every other flag, with Ollama, the fake and the OpenAI-compatible adapter declaring `False`.
  * **`AdapterNotFound` does not exist** in `modelrack.errors`. You add it.
  * `pending_restart` appears **only in prose** (ADR-0062 §48, adapter-roadmap §4.1). No code.
* **ModelRack's runtime dependencies are `baseaicore>=0.4,<0.5` and `httpx>=0.27,<1`.** Two only.
  §0.2 is about keeping it that way.
* **Interpreter:** ModelRack's venv is **Python 3.14.4**. There is **no python3.12** on this host;
  CI covers 3.12/3.13 with 3.14 as early warning. Name the interpreter and every exact invocation
  (M5C-13).
* **Push auth is configured** (2026-09-04): `credential."https://github.com".helper =
  !/usr/bin/gh auth git-credential`. **Probe with `GIT_TERMINAL_PROMPT=0 git push --dry-run origin
  main`, never `git ls-remote origin`** — these repos are public and `ls-remote` succeeds
  anonymously on a repo you cannot push to.

## 0.1 The gap you must close before writing code — this row has no development plan

CLAUDE.md's reading order is *master architecture → the component's `spec.md` → **that phase in its
`development-plan.md`** → the standards it touches*. For this phase that document does not exist:

`docs/packages/modelrack/development-plan.md` **ends at Phase 6.** Phases 7 and 8 appear only as
Phase 6's `**Deferred:**` line. Everything specifying P7 is three bullets in
`roadmap/adapter-roadmap.md` §4.1 plus one row (I17) in §7 — nothing like the Work / Tests /
Acceptance criteria / Known risks / Likely failure modes / Gold standards / Deferred structure every
other phase in that file has, and nothing that says what a person should be able to *see*.

**So Gate 0 is: write the Phase 7 section, in the house shape, and commit it to `docs` before you
write any source.** This is not busywork — it is the artefact that makes the acceptance criteria
demonstrable (CLAUDE.md: *"Every phase's acceptance criteria must be demonstrable, not merely
covered by tests"*), and this row's value is mostly in getting the *test design* right, which is
exactly what a plan section forces you to state up front.

Constraints on that section: it must be consistent with ADRs 0058–0067 (they are accepted and
supersede any roadmap prose that disagrees), it must not invent scope beyond §4.1's three bullets,
and it must name the I17 conformance test explicitly with its pass condition. Mirror it
byte-identically into `py/ModelRack/docs/packages/modelrack/development-plan.md` and `cmp`-prove it.
Consider adding the Phase 8 section in the same commit if it costs little — but do not let it grow
into a second row.

## 0.2 The boundary question this row must settle — take it, record it

**ModelRack must not import `setspec`.** Master architecture §2 is explicit that `mirrorwall` and
`commissioner` are the *only* capability packages permitted to (`architecture/master-architecture.md`
lines ~198 and ~205–208). Adding `setspec` to ModelRack to read `model.adapter_manifest` would break
that rule and the `.importlinter` contract that encodes it. **Never weaken `.importlinter` to make an
import work.**

ADR-0061 rule 3 already settles who reads what: *"FreeWeight reads the directory to enumerate
benchmark subjects; LoadCoach reads it to build routing rows; **ModelRack never reads the
directory** — it receives manifests from the application constructing it, and validates and mounts
them."*

**Recommendation: ModelRack defines its own frozen value object** — a registered-adapter descriptor
carrying the fields P7 actually needs (name, artifact path, `artifact_sha256`, optional
`source_sha256`, the base it declares and its digest, `data_classification`, `format`) — built from
`baseaicore.AdapterIdentity` where identity is concerned, and the **application** converts
`setspec.artifacts.AdapterManifestOut` into it. That keeps ModelRack's dependency set at two,
keeps SetSpec's payload where it belongs, and matches "receives manifests from the application".

Argue a different split if you can, but **record the choice and the reason** in the plan section
(§0.1), in the type's docstring, and in the handoff — and confirm `lint-imports` stays green
without editing `.importlinter`.

## 0.3 The three ADRs that constrain the implementation

* **ADR-0058 (= A-1)** — the subject gains an optional adapter axis;
  `AdapterIdentity(name, artifact_digest, source_digest?)` hashed from the served GGUF; canonical
  form gains a `+name@sha256:…` suffix. **An absent adapter is byte-for-byte today's subject** —
  that is a property to assert, not a hope. Base compatibility is verified **by digest, fail
  closed**; a name-only match carries reduced identity confidence and must be flagged everywhere it
  surfaces.
* **ADR-0062 (= A-5)** — one base per llama-server process, spawned and terminated through the
  existing `Provider.load/unload` seam. Every compatible manifest adapter is **pre-registered at
  launch** (`--lora`, `--lora-init-without-apply`), selected **per request** (`lora`). A newly
  scanned adapter is marked `pending_restart` and folds in **at the next natural idle — never
  mid-work**. `ProviderCapabilities.adapter_hot_swap` is load-bearing; Ollama declares `False`.
* **ADR-0063 (= A-6)** — **one adapter at a time, at a fixed scale.** No composition, no
  scale-mixing, no per-request scale: the single `lora` entry is sent at `1.0`. A request naming two
  adapters is refused, not silently reduced.

Also read **ADR-0065** (an adapter is classified and local-only) and **ADR-0067** (reliability keys
on the subject, not the base) for what the identity has to carry so LA2 can key on it later.

## 0.4 I17 — the cache-correctness test, which is the row

Adapter roadmap §7: *"The prefix-under-A-never-reused-for-B test, plus a semantic canary (same
prompt, two adapters, distinct outputs after a shared prefix)."*

This is the deliverable that justifies xhigh. Two halves, and **both are required**:

1. **The structural half** — a prefix computed under adapter A is never reused for B. ModelRack has
   a `MetadataCache` (`modelrack/cache.py`: `MetadataCache`, `MetadataSnapshot`, `CacheStats`,
   `DEFAULT_METADATA_TTL_SECONDS`), but that caches *metadata*, not KV prefixes — **do not confuse
   them**. The prefix cache in question is llama-server's own. So the structural assertion is about
   **what ModelRack sends and what it keys on**: that the cache identity, the slot/session handling
   and any prompt-prefix reuse ModelRack participates in are keyed on the **full subject including
   the adapter axis**, so no code path can present A's cached prefix to a B request. Write it as a
   property over the request path, with a recorded transport, so it runs in the default gate with no
   binary. Add the no-cross-adapter-batching note §4.1 asks for.
2. **The semantic canary** — same prompt, two adapters, distinct outputs after a shared prefix.
   This one needs a real server and two real adapter files, so it is a `-m live` test. **If no two
   adapter GGUFs exist on this machine, that is a finding, not a reason to skip:** say so in the
   handoff, state exactly what artefacts the canary needs, and leave the test written and skipping
   with an explicit reason (a visible skip, never a silent pass — the discipline E4 used for the
   isolation tests). Do **not** fabricate a canary that passes without adapters.

`pytest-randomly` is on and this is the intermittent-defect shape: a cache-correctness test that
only fails under some orders is telling you the truth. `-p no:randomly` isolates, never fixes.

---

## 1. Setup

```bash
cd /home/jpk/ai/suite/py/ModelRack && source .venv/bin/activate && pip install -e ".[dev]"
```

Use the session scratchpad for every scratch `state_dir`, adapter file, pid file and log — **never**
the repository, never `/tmp` directly, never the workspace root. Two applications must not share a
`state_dir` (D3 §13); neither should two of your test runs.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory, never the workspace root. Nothing at the root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` under `## [Unreleased]`,
  **one Conventional Commit per repository**, committed at each gate boundary.
* **Coverage floor for a shared package is 95%** (the ModelRack plan's Phase 6 criterion 6 says so
  explicitly). Meet it.
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names (`*_bytes`, `*_ms`), keyword-only optionals and booleans,
  `@dataclass(frozen=True, slots=True)` value objects, `mypy --strict`, no bare `Any` at a public
  boundary, no `# type: ignore` without a trailing reason, line length 100.
* Inject every boundary — the process launcher, the process table, the HTTP client, the clock, the
  filesystem root. D3 built `ProcessLauncher`/`ServerProcess`/`ProcessTable` as injectable seams
  precisely so supervision is testable without a binary; keep that property.
* Typed errors only; `UNSUPPORTED` is never coerced to a number (ADR-0016).
* **Never `git add -A`.** Stage named paths.
* Every workspace `docs/` edit is mirrored byte-identically into `py/ModelRack/docs/` and
  **`cmp`-proved**.

## 3. Reading list, in this order

1. `docs/roadmap/adapter-roadmap.md` **§4.1 P7** (three bullets — the whole scope), **§7 I17**, and
   §8's risk table.
2. `docs/architecture/adapter-identity-and-serving.md` — the identity and serving design in full.
3. **ADR-0058 (A-1)**, **ADR-0061** (the registry is a directory and a manifest — especially
   **rule 3**, who reads what), **ADR-0062 (A-5)**, **ADR-0063 (A-6)**, **ADR-0065**, **ADR-0067**.
   Then ADR-0008/0023/0024 for what A-1 amends, and ADR-0071 for the digest file D3 shipped.
4. `docs/packages/modelrack/spec.md` — the published surface you are extending, and §10 on the cache.
5. `docs/packages/modelrack/development-plan.md` Phase 6 — the shape your Phase 7 section must match
   (§0.1), and its Known risks / Likely failure modes as the model for yours.
6. `docs/history/D3_HANDOFF.md`, **§13 especially** — what P6 actually built, the digest-store decision, the
   "profile-change restart: **P7 adds the in-flight guard**" line (that is your work), and the live
   journey as run.
7. `py/ModelRack/src/modelrack/providers/llamacpp.py` and `providers/_llamacpp_process.py` — the
   code you are extending, and its injection seams.

---

## 4. The shape of the work

Six gates. Gate 0 is documentation and it comes first (§0.1). Gate E is the row's reason for
existing; do not let the earlier gates consume the session.

## 5. Gate 0 — write the Phase 7 plan section (docs commit)

Per §0.1: Goal, Prerequisites, Work, Tests, Acceptance criteria, Known risks, Likely failure modes,
Gold standards, Deferred — matching Phase 6's shape. State the §0.2 boundary decision and the I17
pass condition in it. Update Phase 6's `**Deferred:**` line so it points at a section that now
exists. Mirror into `py/ModelRack/docs/…` and `cmp`-prove. Commit to `docs` before writing source.

## 6. Gate A — the adapter descriptor and identity

The value object from §0.2, built on `baseaicore.AdapterIdentity`; the canonical `+name@sha256:…`
suffix; `verify_adapter_base_compatibility` used for base checking, **fail closed**; `name_only`
confidence flagged wherever identity surfaces. Add `AdapterNotFound` to `modelrack.errors` in the
package's existing typed-error style.

**Assert A-1's invariant directly:** a subject with no adapter serializes and hashes
**byte-for-byte** as it does today. Write that as a golden over existing fixtures, not as a claim.

## 7. Gate B — `adapter_hot_swap` and launch-time registration

* Add the 14th flag to `ProviderCapabilities`, defaulting `False`; Ollama, fake and
  OpenAI-compatible declare `False`; `LlamaCppProvider` declares `True`.
* Launch-time registration: every **compatible** manifest adapter pre-registered when the server is
  spawned (`--lora`, `--lora-init-without-apply`). Incompatible ones are refused at registration
  with the digest reason, not dropped silently.
* A caller that asks for adapters against a provider declaring `adapter_hot_swap = False` gets a
  typed refusal, not a silent single-model fallback (ADR-0007 rule 2's discipline).

## 8. Gate C — per-request selection

* One `lora` entry, at scale `1.0`, always (A-6). **A request naming two adapters is refused** —
  test it.
* An unknown adapter → `AdapterNotFound`, with the name and the registered set in `details`.
* No adapter named → today's behaviour, unchanged, byte-for-byte (Gate A's invariant, exercised on
  the request path).

## 9. Gate D — `pending_restart` and the in-flight guard

* A newly supplied adapter is marked `pending_restart` and folds in **at the next natural idle,
  never mid-work** (ADR-0062). Surface the state to the caller — a caller that cannot see
  `pending_restart` cannot explain why its new adapter is not being used.
* D3 §13 recorded "profile-change restart: keep immediate restart; **P7 adds the in-flight guard**".
  Build that guard here, and say in the handoff what "in-flight" means in your implementation and
  how a test forces the race.
* Supervision properties from P6 must survive: no orphans, pid files swept, the kill-tree path
  intact. Prove it with the injected `ProcessTable`, not by watching `ps`.

## 10. Gate E — I17, the cache-correctness conformance test

Per §0.4, both halves, with the no-cross-adapter-batching note. This is the gate that justifies the
model; give it the time the earlier gates did not take. Then the `-m live` extension against the
real `llama-server` (§0 confirms it is installed) — recording what ran, on which build, and what
skipped and why.

## 11. Gate F — close the row (docs commit)

Mark the **F3 row** done in `roadmap/outstanding-work.md` §1 in the house shape
(`**Done 2026-09-0X** (`docs/history/F3_HANDOFF.md`; commits …)`), record §0.1 (the missing plan section, now
written) and §0.2 (the boundary decision), and update `roadmap/adapter-roadmap.md` §4.1 if P7's
description drifted from what you built. Mirror and `cmp`-prove every touched file.

---

## 12. Exit conditions — all of these, demonstrably

1. `docs/packages/modelrack/development-plan.md` has a Phase 7 section in the house shape, mirrored
   and `cmp`-identical.
2. A subject with no adapter is **byte-for-byte** identical to today's — asserted over existing
   goldens.
3. `adapter_hot_swap` exists, defaults `False`, and is `True` only for `LlamaCppProvider`.
4. An incompatible base is refused by **digest**, fail closed, with the reason; a `name_only` match
   is admitted but flagged everywhere it surfaces.
5. Two adapters in one request are refused; an unknown adapter raises `AdapterNotFound`.
6. A newly supplied adapter reports `pending_restart` and does not fold in mid-work; the in-flight
   guard is proved by a test that forces the race.
7. **I17 passes**: the structural prefix-isolation property in the default gate, and the semantic
   canary either passing live or **visibly skipping** with the artefacts it needs named.
8. `lint-imports` green with `.importlinter` **unedited**; ModelRack's runtime dependency set is
   still exactly `baseaicore` + `httpx`.
9. Full gate green, coverage ≥ 95%; ModelRack clean and pushed with CI green; docs clean and
   mirrored.

## 13. Closing duties

1. Full gate, interpreter and exact invocation named (M5C-13); the `-m live` run reported separately
   with the llama.cpp build identifier.
2. **`docs/history/F3_HANDOFF.md` at the workspace root**, house shape: gate results; the §0.2 boundary decision
   and how the application is expected to convert a `setspec` manifest into ModelRack's descriptor
   (LA2/LoadCoach 1.1 will need exactly that); the I17 test design and **why it is the right
   assertion** — the most valuable paragraph in the document; what the semantic canary needs if it
   skipped; the in-flight guard's definition; that P7 **rides 0.7.0 at H1** and is not published;
   anything this prompt said that turned out not to be true.
3. Push both repos and confirm CI green. **Reviewed, not overnight** — one commit per gate, each
   message saying what it made true.
4. Record any **model deviation** from the scheduled Opus 5 · xhigh for
   [model-assignment §3.5](docs/roadmap/model-assignment.md).

## 14. Stop rules

* **Do not add `setspec` to ModelRack's dependencies**, and do not edit `.importlinter` (§0.2). If
  you become convinced the boundary must move, **stop and write the handoff** — that is an ADR, not
  a pin change.
* **Do not implement composition, scale-mixing or per-request scale** (ADR-0063 / A-6). One adapter,
  scale `1.0`. Reopening that needs a new ADR.
* **Do not let an adapter fold in mid-work**, and do not "helpfully" restart the server to apply one.
* **Do not redefine adapter identity** — `baseaicore.AdapterIdentity` is the definition.
* **Do not weaken the digest check to a name match.** `name_only` is a *reduced-confidence*
  outcome that must stay flagged, not an acceptable substitute for verification.
* **Do not fabricate the semantic canary.** A visible skip with the artefacts named beats a test
  that passes without adapters.
* **Do not start P8** — no cancellation-under-supervision work, no leak tests, no four-adapter
  conformance run, no publication.
* **Do not bump the version, tag, or publish.** P7 rides 0.7.0 at **H1** with D3's P6 work.
* **Do not touch LoadCoach or FreeWeight.** Adapter routing is LA2; subject enumeration is
  FreeWeight 1.1.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a boundary.

## 15. If you finish with capacity left

Do **not** start P8 or LA2. Read-only, in priority order: (a) draft the **Phase 8** plan section in
the same house shape, so H1's release row inherits it (documentation, not code); (b) write an
**LA2 readiness note** — the exact conversion LoadCoach must perform from
`setspec.artifacts.AdapterManifestOut` to ModelRack's descriptor, and which of LoadCoach 1.1's new
constraints (`adapter_incompatible`, `adapter_unmeasured`) depend on fields you made available;
(c) record what the semantic canary needs, precisely enough that an operator can produce the two
adapter GGUFs without a conversation.
