# Kickoff — H2: LoadCoach 1.1 — generalized LC-E1, the adapter registry, adapter-aware routing, and LA2

**Row:** H2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · xhigh**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
Routing semantics frozen into persisted explanations — the LoadCoach-P3 precedent, extended.
**Repositories:** `/home/jpk/ai/suite/docs` (first, and this row's docs debt is large — §0.1), then
`/home/jpk/ai/suite/LoadCoach` (the whole weight).
**Ships:** **`loadcoach 1.1.0` prepared, not published.** The version bump, the changelog move and
the release commit are yours; **`git push`, the tag and the publish are the operator's** (standing
instruction of 2026-09-04). Do not run a push dry-run.
**Overnight:** allowed by [§2.12](docs/roadmap/model-assignment.md), but this is the largest
remaining row and its exit is a live GPU session — run it daytime, reviewed, and expect more than
one sitting. Gate boundaries are commit boundaries precisely so it can be stopped and resumed.
**Runs after:** H1 — this row consumes `modelrack 0.7.0` and `baseaicore 0.4.2` **from PyPI**;
if they are not published yet, see §0.4.
**Runs before:** H3 (IdeaPress per-stage pins), H4 (FreeWeight 1.1), and I2's live remote-tier
verification — outstanding-work §3 is explicit that H2 lands **before** I2 touches LoadCoach, so
LoadCoach is changed once and verified once.
**Not in this session:** FreeWeight's adapter work (H4); IdeaPress's pins (H3); PromptCadence
(nothing here changes its wire); the injection corpus (I2).

---

## 0. Machine facts, verified 2026-09-05 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **LoadCoach `main` is at `b78dd1a`**, clean and level with `origin`; `__about__.py` says `1.0.0`.
  Its `## [Unreleased]` carries G2's tool wire and, from further back, `2c7d740`
  (*a synchronous generation records the model it made resident*) — the fix the row notes as
  unreleased. **`docs` is at `c8eb72f`**, clean and level. **Confirm** `git status -sb` in both at
  the start and at the end (CLAUDE.md, working-tree integrity).
* **LoadCoach's documentation contains the word "adapter" exactly zero times.** `grep -rn adapter
  docs/apps/loadcoach/` returns nothing, and `development-plan.md` ends at **Phase 9 — Hardening and
  1.0**. Everything this row builds is specified only in `roadmap/adapter-roadmap.md` §4.2 and the
  A-decision ADRs. **This is the row's Gate 0** — §0.1.
* **The provider configuration is singular today.** `config.py:304` `ProviderSettings` has one
  `kind` (`"ollama"` or `"fake"`), and `:334` `ProvidersSettings` carries only `allow_remote`. The
  shipped example config writes `[provider] kind = "ollama"`. LC-E1's `[providers.<name>]` is
  therefore a **shape change to a published 1.0 configuration file** — §0.2 decision 1.
* **The pins are behind, and one of them is contested.** `pyproject.toml` holds
  `baseaicore>=0.4,<0.5`, `setspec>=0.4,<0.5`, `modelrack>=0.5,<0.6`. This row needs
  `modelrack>=0.7,<0.8` (adapter registration), `baseaicore>=0.4.2,<0.5` (ADR-0074's field) and —
  see §0.3 — almost certainly `setspec`, which E5 and the H4 row currently assign to **H4**.
* **Residency exists but is one-level**: the `residency` table keys on `model_id` + `gpu_index`
  (`data-model.md`), and scoring applies a small `prefer_resident_bonus`
  (`domain/routing/scoring.py:528`–`:546`). `reliability_stats` is `UNIQUE (model_id,
  task_profile_id, window)` — ADR-0067 wants the **subject**, which is a data-shape change with a
  migration, not a scoring tweak.
* **The hard-constraint vocabulary is a caller-visible table** (`routing.md` §4, ten rows today,
  most recently amended by ADR-0075). Adapter constraints join it, and every rejection reason is a
  string somebody's client already switches on.
* **There is still no LLM LoRA adapter GGUF on this machine** — only Wan 2.2 video-diffusion
  safetensors. I16's re-run at LA2 and the row's exit demonstration need the same artefacts H1
  needs (`docs/history/F3_HANDOFF.md` §6 says exactly what an operator must produce). Check at
  minute one; §0.5.
* **Python 3.13.15; there is no python3.12 on this host.** Name the interpreter and every exact
  invocation (M5C-13). LoadCoach's coverage floor is **85 %** (application).
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to the
  operator.

## 0.1 Gate 0 — the plan and the specification do not exist yet

F3 hit a smaller version of this: ModelRack's development plan ended at Phase 6, so P7's acceptance
criteria had nothing demonstrable behind them, and its kickoff made writing the plan Gate 0. Here it
is larger. **Before any source changes**, in workspace `docs/` and mirrored byte-identically into
`LoadCoach/docs/`:

* **`apps/loadcoach/development-plan.md` gains Phase 10 — Adapters and multi-provider (LA2)**, in
  the house shape the other nine phases use: Goal, Prerequisites, Work, Tests, Acceptance criteria,
  Known risks, Likely failure modes, Gold standards, Deferred. Its acceptance criteria are what this
  row is measured against, so write them as **demonstrable** statements (CLAUDE.md), not as a
  feature list.
* **`apps/loadcoach/spec.md`**: §7 (public APIs — the `adapters` CLI group), §8/§9 (inputs and
  outputs carrying an adapter subject), §10 (data ownership — the new tables are LoadCoach's, and
  the adapter *directory* is the operator's), §11 (contracts), §12 (configuration —
  `[providers.<name>]`, `[adapters] directory`, `require_adapter_evidence`, `base_switch_penalty`),
  §13 (the new refusals), §14 (security — ADR-0065's classification rule), §19 (compatibility: what
  1.1 adds and what it does not break).
* **`apps/loadcoach/routing.md`**: §3 (candidate expansion to adapter subjects), §4 (the new hard
  constraints and their reason strings), §6 (two-level residency), §8 (what the explanation now
  says), §10 (the `adapter` override with `model`-pin semantics), §11 (per-subject reliability).
* **`apps/loadcoach/data-model.md`**: the `adapters` table, the subject columns on routing and
  attempt rows, the residency and reliability key changes, and the migrations that get there.
* **`apps/loadcoach/api.md`**: the request override, the response provenance, §10's error additions.

That is a substantial docs commit and it is **the row's first commit**, before a line of source.
Everything downstream — including whether the row is one sitting or three — gets easier once the
acceptance criteria exist.

## 0.2 The decisions this row must take, and record

Each of these has a recommendation; take it or overturn it, but **record which and why** in the
handoff, and in an ADR where it outlives the row (CLAUDE.md: a missing architectural decision is a
docs defect, closed with an ADR, not with an implementation). ADR-0076 is the next free number —
confirm.

1. **How `[providers.<name>]` lands on a published `1.0` configuration.** D-11 is already decided as
   [ADR-0055](docs/adr/0055-loadcoach-registers-providers-by-name-and-kind.md) — LoadCoach registers
   providers by name and kind into one tagged registry — but the *migration path* for the shipped
   singular `[provider] kind = …` is not. Recommendation: both forms are accepted for 1.1, the
   singular being exact sugar for a single entry named after its kind, and a config carrying **both**
   is **refused at startup** with a message naming the conflict. A silent precedence rule is the one
   outcome to avoid: an operator who writes both must be told, not guessed at.
2. **Whether `output.tool_calls` collapses to the assembled shape** (G2's open item,
   `docs/history/G2_HANDOFF.md` §8). Today the response emits one entry per `ToolCallDelta`
   (`call_index`, `id`, `name`, `arguments_fragment`) while the request takes assembled calls — and
   the first caller to implement the grouping got it wrong (G2 §7, a real defect against a real
   model). Collapsing it is **breaking** a `1.0` field inside a minor. Recommendation: add the
   assembled field beside the fragments, document the fragment field as superseded with the version
   it will be removed in, and make PromptCadence's client read the assembled one. A minor does not
   break a shipped field; a deprecation with a date is how it stops being a defect factory.
3. **Where the classification denial is recorded (I19).** ADR-0065 makes an adapter local-only and
   classified; the roadmap wants a *recorded denial* when a confidential-classified adapter meets a
   remote-tier request. LoadCoach has no Commissioner and no egress ledger — that is PromptCadence's.
   Recommendation: it is a routing rejection with its own reason (`excluded_by_policy` is already
   taken by the remote-disallowed rule, so give the classification case its own string) and it is
   **persisted in `routing_candidates` with the explanation**, which is where every other rejection
   already lives and is queryable. Say plainly in the handoff that I19's "recorded denial" is a
   LoadCoach explanation row, not a `governance.egress_decision`.
4. **What a subject's canonical identifier looks like once persisted.** A-1/ADR-0058 gives the
   canonical form a `+name@sha256:…` suffix. Decide whether stored routing/attempt rows carry the
   suffixed string, a separate adapter FK, or both — and remember that `models` rows, residency and
   reliability all key off it. Recommendation: a real FK to the `adapters` table **plus** the
   canonical string on the row that a human reads, because a rename must not orphan a decision
   record and the string is what an explanation quotes.
5. **`require_adapter_evidence` default.** A-7 says default on. Confirm it stays on for 1.1 and that
   its rejection is named (`adapter_unmeasured`), because with no FreeWeight evidence in existence
   until H4 **every adapter subject is unmeasured**, so the shipped default makes adapters invisible
   to routed selection until measured — while pins still work. That is the intended behaviour; state
   it in the docs so it is not read as a bug.
6. **Two-level residency's arithmetic.** A-9/ADR-0066: an adapter switch is free and counts as
   resident; a base switch carries a configurable `base_switch_penalty`; `ignore_residency` zeroes
   both terms and is **recorded in the explanation**. Decide the default penalty and say what it was
   derived from — a number chosen because it looked right, recorded as such, is honest; a number
   presented as measured when it was not is not.

## 0.3 The `setspec` pin — an ordering conflict this row probably has to resolve

E5 deliberately left LoadCoach's `setspec` pin at `>=0.4,<0.5` and assigned the move to **H4**,
because moving it without adopting `CapabilityEvidenceV1_1Out`/`In` turns three local-only reds into
CI reds: `tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-full|1.1-mixed|1.1-unsupported]`
(`docs/history/E5_HANDOFF.md` §10; ADR-0068 rule 3 — a bare name keeps the version it was frozen at).

But **`model.adapter_manifest` 1.0 ships in `setspec 0.5.0`**, and A-4/ADR-0061 makes the manifest
the registry: LoadCoach *reads and validates* operator-written manifests and `loadcoach adapters
scan` *drafts* them. Reading a SetSpec-defined payload without `setspec` would be exactly the
hand-rolled parsing the contracts layer exists to prevent.

**Check this first** (does the manifest reader need `setspec`? — it does unless the row invents a
second definition, which it must not). Recommendation: **move the pin here** to
`setspec>=0.5,<0.7` and pull the `CapabilityEvidenceV1_1Out`/`In` adoption forward from H4 into this
row — the fix is named, small and known — then say in the handoff that H4's row loses that item and
keeps only the bundle `1.1` export work. Overturning that is fine; hand-rolling a manifest reader is
not.

## 0.4 If H1 has not published yet

This row needs `modelrack 0.7.0` (adapter registration, `list_adapters()`, `register_adapters()`)
and `baseaicore 0.4.2` (`RuntimeProfile.adapters_registered`). If the operator has not yet published
them, install both as **local editable installs with a `TODO: re-pin on publish` comment** — the
standing preamble's rule for unpublished suite dependencies — and put "re-pin before the 1.1.0
release commit" at the top of the handoff's operator list. Do **not** vendor, copy or reimplement
anything from either package.

## 0.5 The exit demonstration, and its dependency inversion

The row's exit is *"the IdeaPress three-stage demo — one base load (I16), classification denial
recorded (I19)"*. **IdeaPress's per-stage pins are H3, which depends on H2** — so the literal demo
cannot run inside this row. Resolve it this way, and record it:

* **In this row**, prove the same property at the LoadCoach boundary: a scripted three-request
  sequence pinning three adapters on one base through the `adapter` override, with **exactly one
  base load** asserted from ModelRack's process table and from load timings, plus a fourth request
  that trips the classification rule and leaves a queryable rejection. That is I16 and I19, proved
  where the behaviour actually lives.
* **The IdeaPress three-stage project is re-run at H3**, and the H3 row is updated to say so.

Both halves need the adapter artefacts H1 needed. **Check at minute one** whether two LoRA GGUFs for
one base now exist; if they do not, everything except the live demonstration is still buildable —
land it, leave the demonstration as a named operator step, and **do not cut `1.1.0`** with its exit
unproved.

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb
git -C /home/jpk/ai/suite/LoadCoach status -sb
source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show modelrack baseaicore setspec | grep -E "^(Name|Version)"
```

Every scratch database, config file, model directory and log goes in the session scratchpad —
**never** the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside the component directory. Nothing at the workspace root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional Commit
  per gate**, committed at each gate boundary.
* `pytest-randomly` is on; a seed-only failure is a real bug.
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names, keyword-only optionals and booleans, frozen slotted value objects, pydantic wire
  models, SQLAlchemy models never leaving the repository layer, `mypy --strict`, line length 100.
* `web → cli → services → domain`; `domain` imports no framework. Handlers call one service method
  and render. Never weaken `.importlinter`.
* Async at the HTTP edge only (ADR-0003); SSE, never WebSockets (ADR-0004); server-rendered HTML
  with progressive enhancement, no SPA (ADR-0020).
* Coverage floor: **85 %** (application).
* **Never `git add -A`.** Stage named paths. Every workspace `docs/` edit is mirrored into
  `LoadCoach/docs/` byte-identically and **`cmp`-proved** in the commit message.

## 3. Reading list, in this order

1. `docs/roadmap/adapter-roadmap.md` **§4.2** (this row, in four lines), **§3 LA2** (the exit),
   **§7 I13/I16/I19**, and **§6**'s component/version table.
2. The accepted decisions, in full — they are the specification: **D-11 =
   [ADR-0055](docs/adr/0055-loadcoach-registers-providers-by-name-and-kind.md)**, **A-4 =
   [ADR-0061](docs/adr/0061-the-adapter-registry-is-a-directory-and-a-manifest.md)**, **A-7 =
   [ADR-0064](docs/adr/0064-adapters-are-selected-through-the-capability-vocabulary.md)**, **A-8 =
   [ADR-0065](docs/adr/0065-an-adapter-is-classified-and-local-only.md)**, **A-9 =
   [ADR-0066](docs/adr/0066-residency-is-two-level.md)**, **A-10 =
   [ADR-0067](docs/adr/0067-reliability-keys-on-the-subject-not-the-base.md)**. Then **A-1 =
   [ADR-0058](docs/adr/0058-the-execution-subject-gains-an-adapter-axis.md)** (the axis),
   **A-3 = [ADR-0060](docs/adr/0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md)**
   and **[ADR-0074](docs/adr/0074-adapter-enabled-serving-is-a-runtime-profile-field.md)** (which
   LoadCoach must *set*, `True` or `False`, never `None`).
3. `docs/apps/loadcoach/routing.md` end to end — this row touches every one of its twelve sections.
   Then `spec.md` §§7–14 and `data-model.md`.
4. `docs/history/G2_HANDOFF.md` **§8** (what H2 inherits as settled contract, and the three open
   items §0.2(2) picks up), **§3.1** (ADR-0075's routing rule, which the adapter constraints sit
   beside).
5. `docs/history/F3_HANDOFF.md` **§2** (the boundary decision: ModelRack defines its own frozen
   `AdapterRegistration` and **the application converts** `setspec.artifacts.AdapterManifestOut`
   into it — that conversion is this row's job), **§4** (why every request states the complete `lora`
   configuration), **§6** (the artefacts).
6. `docs/history/E5_HANDOFF.md` **§10** (the `setspec` pin exception this row probably resolves).
7. `docs/architecture/adapter-identity-and-serving.md`, then `master-architecture.md` §§1–3.

---

## 4. The shape of the work — nine gates

A → the documents (§0.1). B → LC-E1: `[providers.<name>]`. C → the registry: `[adapters] directory`,
manifests, the `adapters` table, `adapters scan|list|show`. D → subject expansion and the new hard
constraints. E → pins and the `adapter` override. F → two-level residency. G → per-subject
reliability. H → explanations and the models UI. I → the live demonstration, then the release commit.

**Do gate A whole before any source.** Gates B and C are independent of D–G and are the natural
stopping point if the row runs long: registry-and-config, committed and green, is a coherent
half-row.

## 5. Gate A — the plan and the specification

As §0.1, plus: any decision from §0.2 that outlives the row gets an **ADR** at the next free number
(0076 today — confirm), accepted, referenced from the document it governs. ADRs are superseded,
never edited.

**Commits:** `docs(loadcoach): Phase 10 — adapters and multi-provider registration (LA2)`, and one
ADR commit per decision that needs one.

## 6. Gate B — LC-E1: providers by name and kind

* `[providers.<name>]` with `kind` and a `remote` flag (ADR-0055), the singular form's compatibility
  handled as §0.2(1) decides, and a config carrying both refused at startup with a message naming
  the conflict.
* `remote` stops being inferred: a profile's `allow_remote_providers` and the existing
  `remote_cost_factor` now read a **declared** fact rather than a kind. Check every place that
  reasoned from `kind` and make it read the flag.
* This is also the thing PromptCadence's remote tiers have been waiting on since B4 — but **nothing
  in PromptCadence changes here**; I2 verifies it later, once.
* Tests: a two-provider registry routes across both; a remote provider is excluded for a profile
  that disallows remote, with the existing reason; the singular config produces byte-identically
  today's registry (a compatibility golden).

**Commit:** `feat(config): providers are registered by name and kind (LC-E1, ADR-0055)`.

## 7. Gate C — the registry: a directory, a manifest, and three commands

* `[adapters] directory` (empty = off, opt-in per ADR-0061), an `adapters` table whose identity is
  the **hash** and whose path is a locator — a rename is safe, a content change is a new subject.
* Manifests are `setspec`'s `model.adapter_manifest` 1.0, read and validated, never re-defined
  (§0.3). The conversion into ModelRack's `AdapterRegistration` happens **here, in the application**
  (`docs/history/F3_HANDOFF.md` §2): ModelRack never reads the directory, and `.importlinter` keeps
  it that way.
* `loadcoach adapters scan|list|show`: `scan` **drafts** manifests for a human to keep (never writes
  one silently as authoritative); `list` and `show` report registration state, base compatibility
  and evidence status. A digest that does not match its base is refused, fail closed, with the
  mismatch named.
* Tests: a manifest golden round-trips; a renamed file is the same subject; an edited file is a new
  one; a mismatched digest refuses; `scan` never overwrites a human-kept manifest.

**Commit:** `feat(adapters): the registry is a directory and a reviewed manifest (ADR-0061)`.

## 8. Gate D — subject expansion, and the new hard constraints

* Candidates expand to adapter subjects **only** where the provider declares `adapter_hot_swap` and
  the base digest matches (ADR-0058, ADR-0062).
* New rows in `routing.md` §4's table, each with a reason string that is now caller-visible
  vocabulary: `adapter_incompatible`; `adapter_unmeasured` (from `require_adapter_evidence`, §0.2(5));
  and the classification case (§0.2(3)). Selection rides the **capability vocabulary** — namespaced
  specializations and `user.*` goals — and **there is no tag channel** (ADR-0064); do not invent one.
* LoadCoach sets `RuntimeProfile.adapters_registered` when it builds a profile for a llama.cpp
  provider: `True` where that provider has registrations, `False` where it has none, **never
  `None`** (ADR-0074's consequences). A mismatch is ModelRack's refusal, and a test proves LoadCoach
  never earns it.
* Tests: an adapter subject appears only under `adapter_hot_swap`; each new constraint rejects with
  its reason and the rejection is persisted; a registry with no adapters routes byte-identically to
  `b78dd1a` (the compatibility golden).

**Commit:** `feat(routing): adapter subjects are candidates, and three new constraints reject by name`.

## 9. Gate E — pins and the `adapter` override

* An `adapter` request override with **`model`-pin semantics** (A-7): it selects, it does not
  suggest, and a pin that cannot be honoured is a named refusal rather than a silent fallback.
* Provenance: every attempt records the subject that answered, adapter included.
* Tests: a pin to an unmeasured adapter still works (evidence gates *routed* selection, not pins);
  a pin to an incompatible adapter refuses; the provenance names the subject.

**Commit:** `feat(generate): an adapter pin selects a subject, and every attempt records it`.

## 10. Gate F — two-level residency

* `(resident base process, registered adapters)`: an adapter switch is free and counts as resident;
  a base switch carries `base_switch_penalty`; `ignore_residency` zeroes both terms and is
  **recorded in the explanation** (ADR-0066).
* The `residency` table and `scoring.py`'s single `prefer_resident_bonus` both change shape — a
  migration, and a scoring change with the arithmetic written down in `routing.md` §6.
* Tests: alternating adapters on one base never pay the penalty; a base switch pays it exactly once;
  `ignore_residency` is visible in the persisted explanation, not just in the decision.

**Commit:** `feat(routing): residency is two-level — the base is the expensive switch (ADR-0066)`.

## 11. Gate G — reliability keys on the subject

* `reliability_stats` and the breaker key on the **subject**, never the base (ADR-0067): a failing
  adapter never breaks its base or its siblings. `UNIQUE (model_id, task_profile_id, window)`
  becomes subject-keyed — a migration with a stated rule for existing rows (they are base subjects;
  say so in the migration's docstring).
* Sample fragmentation is real and A-10 names it: honest `low_evidence` flags, no pooling.
* Tests: a broken adapter opens its own breaker and leaves the base servable; existing rows migrate
  to base subjects and their statistics are unchanged.

**Commit:** `feat(reliability): the breaker keys on the subject, never the base (ADR-0067)`.

## 12. Gate H — explanations and the UI

* The explanation names the subject, its evidence source, the residency terms it paid and any
  adapter rejection — **persisted**, because a stored explanation is the record of a decision and
  the LoadCoach-P3 precedent is that it stays readable after the code changes.
* The models UI groups adapter subjects under their base and shows each one's evidence source.
  Server-rendered, progressive enhancement, no SPA.

**Commit:** `feat(web): the models view groups adapter subjects under their base`.

## 13. Gate I — the demonstration, and the release commit

1. **The live proof** as §0.5 defines it: three pinned adapters on one base, **exactly one base
   load** asserted from the process table and load timings, plus the classification rejection,
   queryable. Verbatim into the handoff.
2. `2c7d740` and G2's tool wire ship inside this release — say so in the changelog rather than
   letting them ride silently.
3. Pins re-pinned to the published `modelrack 0.7.0` / `baseaicore 0.4.2` (and `setspec`, §0.3),
   with every `TODO: re-pin on publish` gone.
4. Version to `1.1.0`, the `## [Unreleased]` block moved, release commit prepared, wheel built into
   the scratchpad and verified in a throwaway venv. **No tag, no publish, no push.**

**Commits:** `test(live): LA2 — three adapters, one base load, one recorded classification denial`,
`chore(release): loadcoach 1.1.0`.

## 14. Exit conditions — all of these, demonstrably

1. Phase 10 exists in the development plan with demonstrable acceptance criteria, and the four other
   LoadCoach documents describe adapters; workspace `docs/` and the mirror are `cmp`-identical.
2. Two providers register by name and kind; a singular `[provider]` config still produces today's
   registry byte-identically.
3. An operator's adapter directory, with manifests, produces registered subjects; `adapters
   scan|list|show` work; a digest mismatch refuses by name.
4. Adapter subjects are routable, and each of the three new constraints rejects with a persisted,
   named reason.
5. A pin selects a subject; every attempt records the subject that answered.
6. Alternating adapters on one base pay no residency penalty; a base switch pays `base_switch_penalty`
   once; `ignore_residency` is recorded in the explanation.
7. A failing adapter opens its own breaker and leaves its base servable.
8. **The live demonstration**: three pinned adapters, **one** base load, one recorded classification
   denial (artefact-gated, §0.5).
9. A configuration with no adapters and one provider behaves byte-identically to `b78dd1a` — the
   compatibility golden, asserted, not argued.
10. Full gate green; interpreter and exact invocations named; coverage ≥ 85 %.

## 15. Closing duties

1. Full gate; interpreter and exact invocations named (M5C-13).
2. **`H2_HANDOFF.md` at the workspace root**, house shape: gate results; each §0.2 decision and why;
   how the `setspec` pin question resolved and what H4's row therefore loses; the live evidence
   verbatim; **what H3 inherits** (the override contract and the demo it must re-run), **what H4
   inherits** (the evidence import, the remaining pin work), **what I2 inherits** (a registered
   remote provider, at last); **and anything this prompt said that turned out not to be true**.
3. Say plainly what is left for the operator: push two repos, tag and publish `loadcoach 1.1.0`,
   then verify the published wheel.
4. Record any model deviation ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
5. Update the H2 row in `docs/roadmap/outstanding-work.md` to **Done**, in the house form, and
   update **H3**'s row if §0.5's split moved the IdeaPress demonstration into it.

## 16. Stop rules

* **No application reads another's database, and no adapter payload is re-defined.** The manifest is
  `setspec`'s; ModelRack's `AdapterRegistration` is ModelRack's; the conversion between them is
  LoadCoach's and lives in the application (`docs/history/F3_HANDOFF.md` §2).
* **Do not add a tag channel.** ADR-0064 is explicit: selection rides the capability vocabulary, and
  a free-form tag would reopen a closed decision.
* **Do not send an adapter anywhere.** ADR-0065: local-only, classified, effective classification is
  `max(caller, adapter)`.
* **Do not break a shipped `1.0` field inside a minor** — §0.2(2)'s deprecation, not a removal.
* **Do not touch PromptCadence, FreeWeight or IdeaPress.** H3 and H4 own their halves; a change here
  that "just fixes" one of them makes three diffs unreviewable.
* **Do not weaken `extra="forbid"`**, do not add `/api/v2`, do not weaken `.importlinter`, and do not
  put routing logic in a route handler.
* **Do not cut `1.1.0` with the LA2 demonstration unproved.**
* **Do not `git push`, tag or publish.** Never `git add -A`; never overwrite an unversioned
  workspace-root file; never leave a tree dirty at a gate boundary.

## 17. If you finish with capacity left

Read-only, in priority order: (a) **what H4 needs from the evidence path** — walk a FreeWeight
adapter-bearing bundle import against this row's schema and write down every mismatch. (b) Whether
the explanation's new fields are enough for **I2's** remote-tier verification, or whether it will
need one more. (c) The `low_evidence` story once per-subject reliability fragments samples: A-10's
revisit trigger is "fragmented samples make per-subject reliability useless in practice" — say
whether the shipped minimums make that likely on a real single-machine deployment.
