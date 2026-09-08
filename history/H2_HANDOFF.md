# H2 — LoadCoach 1.1: the documents, providers by name, and the adapter registry

**Row:** H2 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-05, daytime.
**Model:** Opus 5, as scheduled — no deviation.
**Ships:** nothing. Everything is under `## [Unreleased]`. No bump, no tag, no publish, **no push**.

---

## 1. The headline

**Gates A, B and C are done, green and committed. Gates D–I are not, and the row stays open.**
That is the split the kickoff itself named as the natural stopping point: "registry-and-config,
committed and green, is a coherent half-row."

The stop is not arbitrary. **There is still no LLM LoRA adapter GGUF on this machine** —
`find /home/jpk/ai/models -iname '*.gguf'` returns four base models and nothing else, exactly as at
F3 and at H1 — so gate I's live demonstration (I16's one-base-load proof, I17's canary, I19's
recorded denial against a real adapter) cannot be run, and the kickoff's §0.5 is explicit that
`1.1.0` must not be cut with its exit unproved. Gates D–G are buildable without artefacts and are
what the next sitting should take.

**What a person can see today**, with `[adapters] directory` pointed at a directory of GGUFs:

```
loadcoach adapters scan     # drafts one manifest per artifact, for review
loadcoach adapters list     # every reviewed adapter, its base, its class, its status
loadcoach adapters show <name>
loadcoach doctor            # names every unusable adapter and every artifact with no manifest
loadcoach config validate   # accepts [providers.<name>]; refuses a file carrying both forms
```

## 2. Gate results

**Interpreter: Python 3.14.4** at `/home/jpk/ai/suite/LoadCoach/.venv/bin/python`. There is no
`python3.12` and no `python3.13` in this venv — see §6(3), the prompt said 3.13.15.

```bash
cd /home/jpk/ai/suite/LoadCoach
.venv/bin/python -m ruff format --check .          # 201 files already formatted
.venv/bin/python -m ruff check .                   # All checks passed!
.venv/bin/python -m mypy src tests                 # no issues in 181 source files
.venv/bin/lint-imports                             # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" --cov
                                                   # 934 passed, 3 skipped, 15 deselected
                                                   # coverage 90.56 % (floor 85 %)
```

Run at every commit boundary, and with `pytest-randomly` in its default random order at the last
two — no seed-dependent failure appeared.

### Gate A — the plan and the specification (done)

LoadCoach's documentation contained the word "adapter" **zero times** and its development plan
ended at Phase 9, so everything this row builds was specified only in
`roadmap/adapter-roadmap.md` §4.2 and the A-decision ADRs. Now written, before any source:

* `apps/loadcoach/development-plan.md` — **Phase 10**, house shape, with acceptance criteria
  written as demonstrable statements.
* `apps/loadcoach/spec.md` — §7.2's `adapters` group, §9's subject on every response, §10's
  ownership boundary (the directory is the operator's), §11's registry contract, §12's
  `[providers.<name>]` / `[adapters]` / the two new `[routing]` knobs, §13's `ADAPTER_NOT_FOUND`
  and `PROFILE_MISMATCH`, §14's local-only rule and manifests-as-untrusted-input, §19's
  what-1.1-adds-and-does-not-break.
* `apps/loadcoach/routing.md` — §3.1 registrations feeding one tagged pool, §3.2 subject expansion
  and `adapters_registered`, §4's three new constraints each with the remedy it names, §6.1's
  two-level residency arithmetic, §8's explanation carrying the subject and the residency detail,
  §10's `adapter` and `ignore_residency` overrides, §11.1's subject-keyed reliability.
* `apps/loadcoach/data-model.md` — the `adapters` table, `adapter_id` + the recorded subject
  string on decision and attempt rows, the two unique keys that move onto the subject.
* `apps/loadcoach/api.md` — the two tool-call shapes and which one a replaying caller reads.

All five mirrored into `LoadCoach/docs/apps/loadcoach/` and `cmp`-proved byte-identical.

**The documents are ahead of the code, deliberately and by the gate order.** `data-model.md`
describes an `adapters` table that gate D creates; `spec.md` §12 lists `require_adapter_evidence`
and `base_switch_penalty`, which gates D and F add. That is the phase mid-flight, not drift.

### Gate B — LC-E1: providers by name and kind (done)

`[providers.<name>]` blocks with `kind`, connection settings and a **declared** `remote` flag.
Discovery from every registration enters one registry, tagged: `models` gains `provider_name` and
`is_remote` (migration `0008`). Routing evaluates each candidate against **its own** registration's
capabilities (`route(provider_facts_by_name=…)`), the worker executes on
`runtime.provider_for(…)`, and residency is one `ResidencyService` per registration because each
provider loads and evicts its own models.

Two behaviours worth knowing about:

* **One unreachable registration no longer empties a working registry.** Only a registration that
  *answered* can retire its own models; one that could not be listed comes back in
  `DiscoveryOutcome.unreachable` with its models untouched. An unreachable provider is
  availability, not a statement that its models are gone (ADR-0067 rule 2). Every registration
  failing still raises, so the single-provider contract is unchanged.
* **`doctor` reports each registration by name**, one finding each, keeping the documented
  `PROVIDER_UNAVAILABLE` code rather than inventing per-name codes.

### Gate C — the registry: a directory, a manifest, three commands (done)

`[adapters] directory`, opt-in, empty by default. `read_directory` validates each manifest through
SetSpec's own `model.adapter_manifest` 1.0 contract; `registrations_from` converts what survives
into ModelRack's `AdapterRegistration`, in the application, because ModelRack never reads a
directory; `build_registrations` offers the result only to providers declaring
`adapter_hot_swap`. `loadcoach adapters scan|list|show`.

**Not built here, on purpose: the `adapters` table.** Nothing reads a persisted adapter row until
subject expansion, and a table with no reader is a migration to maintain for nothing. It lands with
gate D, where `adapter_id` gets its foreign keys — the data model already describes it.

## 3. The six decisions, and what was chosen

Four became ADRs; two were already settled by accepted decisions and are recorded in the documents
they govern. **ADR-0076 was not free** — G3 took it earlier the same day (§6(1)) — so this row used
**0077–0080**.

1. **How `[providers.<name>]` lands on a published 1.0 configuration** →
   **[ADR-0077](docs/adr/0077-a-named-provider-block-and-the-singular-block-are-one-registry.md)**.
   Recommendation taken: both forms accepted, the singular block is exactly one registration named
   **after its kind** (not `"default"` — the name is printed in explanations, and `ollama` tells an
   operator something), declaring `remote = false`; a file carrying **both** is refused at startup
   naming each. No precedence rule, because the half-migrated file is the case a precedence rule
   answers silently. `[providers] allow_remote` stays cross-provider policy, evaluated *above* a
   registration's own flag.
2. **Whether `output.tool_calls` collapses to the assembled shape** →
   **[ADR-0078](docs/adr/0078-a-shipped-response-field-is-superseded-beside-its-replacement.md)**.
   Recommendation taken: add `output.tool_calls_assembled` beside the fragments, document the
   fragment field as **superseded** with its removal named at LoadCoach `2.0`, and move suite
   callers in their own rows. **The ADR is accepted; the field is not built yet** — it belongs with
   gate H's response work, and it is the first thing to build if this row is picked up out of
   order, because PromptCadence is currently carrying the grouping bug's shape.
3. **Where the classification denial is recorded (I19)** →
   **[ADR-0079](docs/adr/0079-an-adapter-classification-refusal-is-a-routing-rejection.md)**.
   Recommendation taken, and stated plainly: **I19's "recorded denial" is a LoadCoach explanation
   row**, an `adapter_classification_conflict` rejection in `routing_candidates`, **not** a
   `governance.egress_decision` — no egress was ever contemplated, the candidate was filtered, and
   LoadCoach holds no decision ledger. It gets its **own reason string** rather than reusing
   `excluded_by_policy`, because one is fixed by turning remote on and the other cannot be fixed by
   any flag. `roadmap/adapter-roadmap.md` §7's I19 row was amended to say so.
4. **What a subject's canonical identifier looks like once persisted** →
   **[ADR-0080](docs/adr/0080-a-persisted-decision-names-the-subject-by-reference-and-by-string.md)**.
   Recommendation taken — **both**: a real `adapter_id` foreign key *and* the canonical subject
   string written at decision time, because an explanation is kept for ever and an adapter
   directory is not. The ADR adds the detail the recommendation did not have: the two unique keys
   that move onto the subject (`reliability_stats`, `residency`) need an **empty-string sentinel**,
   because SQL treats `NULL`s in a unique index as distinct and a key that admits duplicates is not
   a key. That is a deliberate wart, documented beside the keys.
5. **`require_adapter_evidence` default** → **no ADR; ADR-0064 rule 3 already decides it.** It
   stays **on**. `routing.md` §4 now states the consequence in the document rather than leaving it
   to be discovered: until FreeWeight measures adapters at LA3, *every* adapter subject is
   unmeasured, so the shipped default makes adapters invisible to **routed** selection while
   **pins keep working**. That is "no benchmark, no use" behaving correctly, not a bug.
6. **Two-level residency's arithmetic** → **no ADR; ADR-0066 rule 2 makes it configuration.**
   `base_switch_penalty` defaults to **0.10**, and `routing.md` §6.1 says in as many words that it
   was **chosen, not measured**: twice `prefer_resident_bonus`, so a base switch is never decided
   by the tie-break the bonus exists to be, and small enough that a candidate genuinely better at
   the task still wins. A deployment that has measured its own load times should set it from them.

## 4. The `setspec` pin, and what H4's row loses

**The pin moved here**, as §0.3 recommended: `setspec>=0.4,<0.5` → `>=0.5,<0.7`. It had to. The
adapter registry reads `model.adapter_manifest` 1.0, which ships in `setspec 0.5.0`, and
hand-rolling a manifest reader is precisely what the contracts layer exists to prevent.

Moving it alone turned E5's three local-only reds into three real failures, exactly as
`E5_HANDOFF.md` §10 predicted:
`tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-full|1.1-mixed|1.1-unsupported]`.
The fix is the `CapabilityEvidenceV1_1Out`/`In` adoption pulled forward from H4 — an **import
change and nothing else**: a bare name permanently means the version it was frozen at (ADR-0068
rule 3), every `1.0` record validates through the `1.1` model unchanged, and a record with no
adapter dumps byte-identically.

**One behavioural addition came with it, and it is not cosmetic.** `EvidenceIdentity` gained the
adapter axis and `bind_identity` gained **rule 0**: an adapter-bearing record binds to **nothing**,
retained `unmatched` with a note naming the adapter. Without it, the first adapter-bearing bundle
FreeWeight exports at H4 would have bound to the **base's** registry row by its model identity and
raised the score of weights that were never measured (ADR-0058 §4). That window would have opened
silently between this release and H4.

**H4's row therefore loses two items** and should be edited when this row closes:

* LoadCoach's `setspec` pin move — **done here**.
* The `CapabilityEvidenceV1_1Out`/`In` adoption — **done here**.

**H4 keeps**: FreeWeight's `benchmark.evidence_bundle` `1.1` bundled export (needs B5), the A-2
panel policy, serving-mode A/B, and Commissioner's `setspec>=0.5,<0.7` widen as its own
`commissioner 0.1.1` release.

## 5. Commits, and the dependency situation

**docs** (2): `2424c9a` the four ADRs and the index, `4f60ce3` Phase 10 plus the four LoadCoach
documents and the I19 amendment. `docs` is **8 ahead of origin**, unpushed (6 of those were H1's).

**LoadCoach** (4): `af64e93` the docs mirror, `4b25b8f` the `setspec` pin move with the `1.1`
adoption, `140a250` LC-E1, `e256b24` the adapter registry. **4 ahead of origin**, unpushed.

No `git add -A` for source paths; every path staged by name. No push, no push dry-run, no tag, no
publish.

**Pins are ahead of PyPI, deliberately (kickoff §0.4).** `pyproject.toml` now says
`baseaicore>=0.4.2,<0.5` and `modelrack>=0.7,<0.8`, each with a `TODO: re-pin on publish`
explaining that the local venv satisfies them by editable install. Two consequences a reader must
not be surprised by:

* **`pip install -e ".[dev]"` prints a resolver warning** about `modelrack`, because ModelRack's
  `__about__.py` still says `0.6.0` — H1 held that bump until LA1's exit can be demonstrated. The
  API is there; the number is not.
* **CI on this branch will be red until the operator publishes `baseaicore 0.4.2`** (and later
  `modelrack 0.7.0`). That is inherent to building against unpublished suite dependencies and is
  the reason the kickoff put the re-pin at the top of the operator list.

Editable installs currently in `LoadCoach/.venv`: `baseaicore 0.4.2`, `modelrack 0.6.0`,
`mirrorwall 0.2.2`, `sweatmeter 0.4.0`, `weightsdb 0.2.0`. `setspec 0.6.0` is the **published**
wheel from PyPI.

## 6. Things this row's prompt or its own documents said that turned out not to be true

1. **"ADR-0076 is the next free number — confirm."** It was not. G3 accepted
   `0076-a-step-retry-is-a-repeat-under-the-same-intent.md` earlier on 2026-09-05. This row used
   **0077–0080**. The kickoff's §0.2 was written before G3 landed.
2. **"`docs` is at `c8eb72f`."** It was at `1c2b19c` when this session began — H1's row update had
   landed since. Both trees were clean, as the prompt required.
3. **"Python 3.13.15; there is no python3.12 on this host."** LoadCoach's own venv is
   **Python 3.14.4**. 3.13.15 is BaseAiCore's and ModelRack's, from H1. Every gate figure in §2 is
   3.14.4's.
4. **`content.fact_check` is not a capability.** ADR-0064 rule 1 uses it as an example of a
   namespaced specialization, and the kickoff's §8 repeats it, but `setspec.vocabulary` (1.1) does
   not know it — it is a *task profile* id. The real terms in that shape are `auditing.fact_check`,
   `coding.python` and `user.house_voice`, and a manifest declaring `content.fact_check` is
   **refused** by the payload's own validator. Nothing was written against the wrong name; the
   tests use `auditing.fact_check`. ADRs are never edited, so this is recorded here and should be
   noted wherever the example is next copied.
5. **"The provider configuration is singular today"** — true, and the kickoff's reading of
   `config.py:304` was accurate. **"LoadCoach's documentation contains the word 'adapter' exactly
   zero times"** — also true, verified before gate A.

## 7. What the next sitting takes, in order

Gates D → G are all buildable **without** adapter artefacts. Only gate I needs them.

* **Gate D — subject expansion and the three constraints.** This is where the `adapters` table and
  migration `0009` land (`adapter_id` plus `subject_canonical_id`, ADR-0080), where
  `bind_identity`'s rule 0 is *upgraded* from "retain unmatched" to real adapter-subject binding,
  and where `RuntimeProfile.adapters_registered` is set — `True`/`False`, **never `None`**, derived
  from what LoadCoach handed the provider and **not** from `list_adapters()`, which moves during a
  pending restart (H1's handoff §4 is emphatic about this).
* **Gate E — pins and the `adapter` override.**
* **Gate F — two-level residency.** `residency` gains the adapter columns and the sentinel key.
* **Gate G — reliability keyed on the subject.** Same shape, `reliability_stats`.
* **Gate H — explanations, the models UI, and ADR-0078's `output.tool_calls_assembled`.**
* **Gate I — the live demonstration**, artefact-gated, then the release commit.

**One open question for the operator, needing no answer to continue:** gates D–G each move a unique
key or add columns. They could be one migration (`0009`) written once at gate D and extended, or
four. This row's judgement is **one migration per gate**, because a gate boundary is a commit
boundary and a half-applied composite migration is the worst thing to debug — but a reviewer who
wants a single `0009` should say so before gate F, after which unpicking it costs more than writing
it.

## 8. What H3, H4 and I2 inherit

**H3 (IdeaPress adapter pins)** — nothing usable yet. The `adapter` override contract is
*specified* (`routing.md` §10: `model`-pin semantics, hard constraints still apply, a pin that
cannot be honoured is a named refusal) but **not built**; gate E builds it. H3 must not start before
this row closes. It also inherits the IdeaPress three-stage demonstration that §0.5 moved into it —
**the H3 row has not yet been edited to say so**, and it should be when this row closes.

**H4 (FreeWeight 1.1)** — loses the `setspec` pin move and the `CapabilityEvidenceV1_1` adoption
(§4), keeps everything else. It also inherits the fact that **adapter-bearing evidence currently
binds to nothing**: the first bundle it exports will land `unmatched` until gate D teaches the
registry adapter subjects. That is deliberate and safe, but H4's exit demonstration must run
*after* gate D or it will show no adapter evidence scoring anything.

**I2 (PromptCadence P9)** — inherits **a registered remote provider, at last**: `[providers.<name>]`
with `remote = true` is now configurable, discovered, tagged and routable, and the two
`tools.agent.remote_*` profiles will select it instead of returning `NO_ELIGIBLE_MODEL`. Nothing in
PromptCadence changed here, as the stop rules require. I2 should also expect ADR-0078's assembled
tool-call field once gate H builds it — until then PromptCadence's client keeps grouping fragments
itself.

## 9. For the operator

1. **Push two repos** — `docs` (8 ahead) and `LoadCoach` (4 ahead) — knowing CI will be red on
   LoadCoach until step 2. Everything from H1 is also still unpushed.
2. **Publish `baseaicore 0.4.2`.** H1 prepared it; H2 and everything after depend on it, and it
   depends on nothing.
3. **Produce the two LoRA adapter GGUFs** for one of the four bases under `~/ai/models/llm`.
   `docs/history/F3_HANDOFF.md` §6 states exactly what, in five steps. Three separate exits are
   waiting on this one artefact set: LA1's I16/I17 (H1), this row's gate I, and H4's I18.
4. Then **gate G of H1** (LA1's exit), then `modelrack 0.7.0`, then this row's gates D–I.
