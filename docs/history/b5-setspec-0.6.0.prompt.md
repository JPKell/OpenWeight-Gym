# Kickoff — B5: SetSpec 0.6.0 (Phase 7)

**Row:** B5 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Sonnet 5 · standard. **Repository:** `/home/jpk/ai/suite/py/SetSpec`.
**Runs after:** B1 (`setspec 0.5.0` on PyPI — already published). **Gates:** H4 (FreeWeight 1.1,
LA3) — a hard edge: *"a bundle cannot carry adapter evidence until the bundle has a minor that
nests it"* ([outstanding-work §3](docs/roadmap/outstanding-work.md)).
**Overnight:** permitted. Sonnet rows run at effort **high** overnight
([model-assignment §2.12](docs/roadmap/model-assignment.md)); this row is not on the
never-overnight list.

**This row is a second application of a mechanism that already exists in this repository.**
B1 built `capability.evidence` `1.1` as a sibling class beside the frozen `1.0`; B5 does the same
thing one payload out, for `benchmark.evidence_bundle`. The judgment was made in
[ADR-0068](docs/adr/0068-a-post-freeze-minor-is-a-sibling-class.md); this is transcription against
a worked precedent in the same module. If you find yourself inventing a mechanism, re-read the
precedent — you have diverged.

---

## Precondition — check this first

```bash
pip index versions setspec        # must list 0.5.0
cd /home/jpk/ai/suite/py/SetSpec && git status --short && git describe --tags   # clean; v0.5.0
```

`setspec 0.5.0` was on PyPI and tagged `v0.5.0` at the time this prompt was written, and
`CapabilityEvidenceV1_1Fields` is in the tree at `src/setspec/capability/v1.py`. If either is not
true, **stop and say so** — this row builds directly on B1's published shape, and a `1.1` bundle
nesting an unpublished `1.1` evidence class is a contract that does not exist anywhere but here.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/SetSpec` (and in
  `/home/jpk/ai/suite/docs` for the authoritative copy of the two mirrored documents).
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  SetSpec section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2, then
  the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the model *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name; keyword-only for anything optional or
  boolean; line length 100; `mypy --strict` with no bare `Any` at a public boundary and no
  `# type: ignore` without a trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **95 %** (shared package floor),
  `CHANGELOG.md` updated, one Conventional Commit per logical group. **Name the interpreter and the
  exact invocation in the handoff doc** (M5C-13) — B1 ran `py/SetSpec/.venv/bin/python`,
  Python 3.13.15; confirm rather than copy that.
* **Dependency pinning:** `setspec` depends on `baseaicore` (`>=0.4,<0.5`) and pydantic. This row
  adds **no dependency and changes no pin**; every type it needs is already imported by
  `setspec.capability.v1`. If a `baseaicore` upgrade lands in the venv mid-session, see the
  snapshot-drift rule under "Constraints".
* **Documentation is mirrored.** Edit the workspace copy under `/home/jpk/ai/suite/docs/` first,
  then copy byte-identically into `py/SetSpec/docs/`. Verify with `cmp`, never by eye. The mirrored
  files here are `packages/setspec/spec.md` and `packages/setspec/development-plan.md`.
* **You are not authorised to tag or publish.** Prepare the release, stop at the tag, and say so.

## Setup

```bash
cd /home/jpk/ai/suite/py/SetSpec
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be clean before you start; see "Working-tree integrity" below
```

## Reading list

1. [ADR-0068](docs/adr/0068-a-post-freeze-minor-is-a-sibling-class.md) — the whole record, but
   **rule 5 is this row's direct instruction**: *"A payload that nests another's frozen definition
   does not move when that payload gains a minor. Carrying the new minor into the outer payload is
   the outer payload's own minor, decided, versioned and scheduled separately."* B5 is that
   separate schedule. Rules 1–4 give you the mechanism: sibling class, both versions registered
   side by side, the bare name keeps `1.0`, byte-identity proved by golden.
2. [`docs/packages/setspec/spec.md`](docs/packages/setspec/spec.md) **§11 rule 9** (the post-freeze
   additive-minor contract, written after B1 with `capability.evidence` as its worked example — this
   row adds the nesting case to it) and **§19** (coexisting minors as sibling classes; the
   dependency-bump `description` clause you may need under "Constraints"). Also §7's payload list
   and §20's acceptance criteria, which must all continue to hold.
3. [`docs/packages/setspec/development-plan.md`](docs/packages/setspec/development-plan.md)
   **Phase 6** — the shape a payload phase takes in this repo (Goal / Prerequisites / Work /
   Files-subsystems / Tests / Acceptance criteria / Known risks / Likely failure modes / Deferred),
   and its **Deferred** paragraph, which names this row by name and scopes it. There is **no Phase 7
   section yet; writing one is part of this row.**
4. `src/setspec/capability/v1.py` — the module you are editing. Read all of it, and specifically:
   the module docstring's explanation of *why* the sibling exists; `CapabilityEvidenceV1_1Fields`
   with its `@model_serializer(mode="wrap")` that drops an absent `adapter` key rather than emitting
   `null`; and `EvidenceBundleFields`, whose `evidence` field is
   `WireSequence[CapabilityEvidenceFields]` and whose docstring already says why the `1.1` field
   "does not reach here".
5. `src/setspec/artifacts.py` (`_REGISTRY`, `_VERSION_1_1`, `build_json_schema`,
   `render_schema_document`, `golden_names`/`golden_payloads`) and `src/setspec/envelope.py`
   (`SUPPORTED_SCHEMAS`, the highest-known-minor map, and the narrative docstring that describes the
   Phase 6 addition) — the two registries a new minor must appear in.
6. `tests/contract/test_schema_snapshots.py` and `tests/contract/test_adapter_axis_i15.py` — the
   tests that name `capability.evidence` `1.1` **explicitly, by name**, as the one schema with a
   second published minor. They were written that way on purpose. See "The work", item 4.
7. [`docs/roadmap/adapter-roadmap.md`](docs/roadmap/adapter-roadmap.md) **§4.3** (the FreeWeight 1.1
   paragraph — the bundle sentence is the consumer requirement this row satisfies) and the **LA3**
   row in §3. Read them for scope, not for work: you are publishing the shape, not exporting it.

## The work

The goal in one sentence, from the row: **an exported evidence bundle can carry adapter-bearing
evidence records, and every bundle that does not is byte-identical to what `1.0` writes today.**

### 1. `benchmark.evidence_bundle` `1.1` — the sibling class

In `src/setspec/capability/v1.py`, beside the untouched `EvidenceBundleFields`:

* `EvidenceBundleV1_1Fields(EvidenceBundleFields)` overriding exactly one thing — `evidence`
  becomes `WireSequence[CapabilityEvidenceV1_1Fields]`. Same field name, same default, wider
  element shape (`CapabilityEvidenceV1_1Fields` subclasses the frozen class, so every `1.0` record
  validates through it unchanged).
* `EvidenceBundleV1_1Out, EvidenceBundleV1_1In = payload_models(EvidenceBundleV1_1Fields)`, exported
  from `__all__` in sorted position.
* **`EvidenceBundleFields` is not edited — not its fields, not its validators, not its docstring.**
  Pydantic embeds `__doc__` as the JSON Schema `description`, so a docstring edit moves the
  committed `1.0` snapshot. That is the exact failure ADR-0068 exists to prevent, and it is the one
  this row is most likely to commit by accident, because the frozen class's docstring currently
  says the `1.1` adapter field "does not reach here" — a sentence this row makes stale. **Leave it
  stale in the frozen class** and explain the resolution in the module docstring (which is not
  nested by any schema) and in the Phase 7 docs section. If you conclude it must be corrected in
  place anyway, that is a stop, not a judgment call: record it in the handoff and leave the class
  alone.
* **Mixed bundles are the intended semantics**, not an edge case: a real FreeWeight 1.1 export at
  LA3 holds records measured on bare bases beside records measured on `(base, adapter)` subjects.
  Say so in the new class's docstring and prove it with a golden.
* **Check, do not assume, that no new serializer is needed.** The absent-`adapter` key suppression
  already lives on `CapabilityEvidenceV1_1Fields`; a nested dump should therefore inherit it. Assert
  it with a test rather than reasoning about it — and if a nested `1.1` record does emit
  `"adapter": null`, fix it at the nested layer where the existing `@model_serializer` lives, never
  by adding a second suppression pass on the bundle.

This row adds **no new field to the bundle itself**. If you find yourself adding one, you have
widened the row.

### 2. Registration

* `artifacts._REGISTRY`: `"benchmark.evidence_bundle"` gains
  `_VERSION_1_1: (EvidenceBundleV1_1Out, EvidenceBundleV1_1In)` beside its `_VERSION_1_0` entry —
  the same two-entry shape `capability.evidence` already has.
* `envelope.SUPPORTED_SCHEMAS`: `"benchmark.evidence_bundle"` → `{1: SchemaVersion(1, 1)}` (highest
  known minor within the major). Update the module's narrative docstring, which currently describes
  `capability.evidence` `1.1` as the only additive minor.
* No major moves. `DRAFT_SCHEMAS` stays empty.

### 3. JSON Schema and goldens

* `src/setspec/schemas/benchmark.evidence_bundle/1.1.json`, generated with the regeneration snippet
  quoted in `tests/contract/test_schema_snapshots.py::_REGENERATE`, never hand-written. Confirm it
  references the `1.1` evidence definition and that `1.0.json` is **byte-unchanged on disk**
  (`git diff --stat` on the schemas directory should show one new file and nothing modified).
* `src/setspec/goldens/benchmark.evidence_bundle/1.1/` with **at least three** goldens — the repo's
  floor is enforced by `test_goldens.py`, and one of them must be smaller than `full.json` by
  serialized bytes:
  * `minimal.json` — byte-identical to the committed `1.0/minimal.json` (an empty bundle is the
    strongest byte-identity statement available);
  * `full.json` — adapter-bearing records, the shape this row exists to make possible;
  * `mixed.json` — bare-base and adapter-bearing records in one bundle, which is what LA3's export
    actually produces.
* The `1.0` goldens are untouched. A `1.0` golden that changes means the minor was not additive.

### 4. The tests that name `capability.evidence` by name

Three places in the suite assert the Phase 6 state as a **named exception**, not as a count. Extend
them by name; **never relax one to a count or a length assertion** — the naming is the point, and a
count-based assertion would let a fourth published minor land unnoticed later:

* `test_schema_snapshots.py::TestTheFreezeHolds::test_every_schema_that_predates_phase_6_is_still_1_0`
  — its exclusion list currently holds one id. Rename the test if the name no longer describes what
  it asserts (it will not: `benchmark.evidence_bundle` also predates Phase 6), and say in the
  docstring which schemas are the named exceptions and which phase each came from.
* `test_schema_snapshots.py::TestTheFreezeHolds::test_capability_evidence_is_the_one_schema_with_a_second_published_minor`
  — no longer true after this row. Replace it with an assertion that names **both** payloads and
  their published version tuples explicitly.
* `test_goldens.py`'s minimal-vs-full size check and any per-schema parametrization that enumerates
  versions — verify these pick up `1.1` automatically, and where one does not, extend it explicitly.

New tests of your own, at minimum:

* Round-trip per class for `EvidenceBundleV1_1Out` and `…In` (`load(dump(x)) == x`, unknown-field
  preservation on the `In` side only — §11 contract 3, asserted per class, never across the pair).
* **The bundle's byte-identity proof**, the analogue of I15 one payload out: every committed
  `benchmark.evidence_bundle/1.0` golden dumps byte-identically whether validated through
  `EvidenceBundleOut` or `EvidenceBundleV1_1Out`, over the *existing* committed goldens. Put it in
  its own contract module (`tests/contract/test_bundle_minor_is_additive.py`) rather than in
  `test_adapter_axis_i15.py` — that file is LA0's exit condition and should keep meaning exactly
  that — and cross-reference the two in their docstrings.
* A `1.0` document containing an adapter-bearing evidence record is **not** something `1.0` can
  produce; assert the direction that matters instead: an adapter-bearing bundle validates through
  `EvidenceBundleV1_1In` and a bundle with no adapter anywhere validates through both.
* A mixed bundle round-trips with each record's adapter presence preserved individually.

### 5. Documentation

* A **Phase 7 section** in
  [`docs/packages/setspec/development-plan.md`](docs/packages/setspec/development-plan.md), in
  Phase 6's shape, with demonstrable acceptance criteria — the house rule is that a phase states
  what to run and what a person should see. Phase 6's **Deferred** paragraph names this phase; close
  that loop by pointing back at it, and write Phase 7's own Deferred paragraph (FreeWeight's actual
  bundled export of adapter evidence is H4/LA3, not this row).
* [`docs/packages/setspec/spec.md`](docs/packages/setspec/spec.md): §7's payload list;
  **§11 rule 9**, which currently reads as though `capability.evidence` `1.1` were the only
  application — add the transitive case (rule 5) with the bundle as its worked example; §19's
  coexisting-minors bullet, which names Phase 6 as the first exercise and should now name both.
* `README.md`'s status line (`0.6.0` — Phases 1–2, 3A, 4, 5, 6 and 7 complete), `CHANGELOG.md` under
  a new `## [0.6.0]` section, and `src/setspec/__about__.py` → `0.6.0`.
* Mirror both documents into `py/SetSpec/docs/packages/setspec/` and paste the `cmp` output into
  the handoff.

### 6. Gate, then prepare the release

Full gate green with the interpreter named. Commit in logical groups. **Do not tag, do not publish.**

## Before you finish — three closing duties

1. **Write `docs/history/B5_HANDOFF.md` at the workspace root.** It is read by the human before the release and
   by the H4 (FreeWeight 1.1) session later. Sections: gate results with interpreter and exact
   commands; the published shape (the `1.1` bundle's field list and its exported names — H4 imports
   these); the byte-identity evidence (which goldens, which test, what it asserts); the contract
   tests you extended and how; `cmp` output for both mirrored documents; the commits made; and
   **"Before the next session"** — at minimum tag and publish `setspec 0.6.0`, then the clean-venv
   check:
   ```bash
   python -m venv /tmp/setspec-0.6.0-check && source /tmp/setspec-0.6.0-check/bin/activate
   pip install setspec==0.6.0
   python -c "from setspec.capability.v1 import EvidenceBundleV1_1Out; print('ok')"
   ```
   Add anything you found: a spec passage the new case makes wrong, a place the `capability.evidence`
   precedent did not transfer, a stale docstring you deliberately left alone.
   **Never overwrite an existing root file** — the workspace root is not a git repository and has no
   history to recover from. If `docs/history/B5_HANDOFF.md` exists, write `B5_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what shipped, what the gate said, what is waiting on the human,
   and anything in "Before the next session". A few sentences, not the document again.
3. **Prepare the commits.** Everything committed on `main` in `py/SetSpec` and in `docs`, working
   trees clean, nothing pushed and nothing tagged. Say exactly what is waiting: the commits, the tag
   to create, the `pypi` environment approval, and the post-publish install check.

## Constraints and stop rules

* **The frozen classes are never edited** — `EvidenceBundleFields` and `CapabilityEvidenceFields`,
  including their docstrings, validators and field defaults. A committed `1.0` snapshot that moves
  because of an edit in this row is a stop.
* **Never edit a golden to make a test pass.** A changed `1.0` golden means the change was not
  additive — stop and report, do not reconcile.
* **The one legitimate snapshot movement** is the dependency-`description` case recorded in spec §19
  and Phase 6's Known risks: a `baseaicore` bump changing an enum docstring re-renders a frozen
  snapshot's `description` text. If that happens, verify structural identity (same properties, types
  and required fields with `description` stripped) *before* re-committing, and record it in the
  handoff. A property, type or required-field change is never this case — it is a stop.
* **The bare names keep meaning `1.0`** (ADR-0068 rule 3). `EvidenceBundleOut`/`In` stay bound to
  `EvidenceBundleFields` permanently. FreeWeight imports the bare name today
  ([`FreeWeight/src/freeweight/services/evidence.py:1880`](FreeWeight/src/freeweight/services/evidence.py#L1880));
  after this row it must still export `1.0` documents with no change in its tree. **Do not touch
  FreeWeight** — adopting the minor is H4's deliberate one-line import change.
* **No new dependency**, no new pin, no new module. `governance.*`, `model.adapter_manifest` and
  Commissioner are all out of scope; B1 published them and B3 implements Commissioner.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` at the start and at the end of
  the session in both repos; `git checkout --` anything modified that you did not edit; commit at
  each logical group rather than once at the end; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, leave both trees clean, and record
  exactly where you stopped in `docs/history/B5_HANDOFF.md`.
