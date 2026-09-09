# Kickoff — B1: SetSpec 0.5.0 (Phase 6)

**Row:** B1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Sonnet 5 · high. **Repository:** `/home/jpk/ai/suite/py/SetSpec`.
**Runs after:** A2 (`baseaicore 0.4.1` on PyPI). **Gates:** B3 (SpotCheck P1) — a hard edge, the
payload publishes before its consumer pins it.
**Overnight:** permitted. Sonnet rows run at effort **high** overnight
([model-assignment §2.12](docs/roadmap/model-assignment.md)); this row is not on the
never-overnight list.

---

## Precondition — check this first, and stop if it is not met

**`baseaicore 0.4.1` must be published to PyPI before this row starts.** As of the last check PyPI
carries `0.4.0` only, and `py/BaseAiCore` commit `f2cdbf0` is untagged and unpushed. Verify:

```bash
pip index versions baseaicore        # must list 0.4.1
```

If it does not, **stop and say so** — do not vendor `AdapterIdentity`, do not pin a local path as a
workaround, and do not proceed against `0.4.0`. Tagging and publishing are the human's, per run.
This row's adapter fields are shaped by `baseaicore.AdapterIdentity`; building them against an
unpublished type is how the two drift.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/SetSpec`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  SetSpec section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2, then
  the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name; keyword-only for anything optional or
  boolean; injected clocks; `@dataclass(frozen=True, slots=True)` for value objects; line length
  100; `mypy --strict` with no bare `Any` at a public boundary and no `# type: ignore` without a
  trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, `CHANGELOG.md` updated, one Conventional
  Commit per logical group. **Name the interpreter and the exact invocation in the handoff doc**
  (M5C-13) — e.g. `py/SetSpec/.venv/bin/python`, Python 3.13.x.
* **Dependency pinning:** `setspec` depends on `baseaicore` only. Keep the existing `>=0.4,<0.5`
  range — `0.4.1` is inside it, so no pin changes. Add no other dependency.
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

1. [`docs/packages/setspec/spec.md`](docs/packages/setspec/spec.md) — §7 the public API and the
   `Out`/`In` model-pair rule, §11 the public contracts (canonical JSON, unknown-minor acceptance,
   round-trip fidelity per class), §19 compatibility and versioning.
2. [`docs/packages/setspec/development-plan.md`](docs/packages/setspec/development-plan.md) —
   Phase 4 ("Freeze v1.0, publish schemas and goldens") is the shape a payload phase takes here.
   There is **no Phase 6 section yet; writing one is part of this row.**
3. [`docs/packages/spotcheck/spec.md`](docs/packages/spotcheck/spec.md) §7 — `EgressDecision` and
   its `to_payload`/`from_payload`. That class is the consumer of `governance.egress_decision`, and
   its field list is the shape you are publishing.
4. [`docs/roadmap/adapter-roadmap.md`](docs/roadmap/adapter-roadmap.md) §3 (the LA0 row and its exit
   condition) and §7 **I15**, the verification this row must satisfy.
5. The accepted ADRs, which are normative here:
   [ADR-0051](docs/adr/0051-plans-stay-internal-and-one-payload-travels.md) (D-7 — `governance.*` is
   a new SetSpec-owned root; `promptcadence.*` is an application namespace),
   [ADR-0054](docs/adr/0054-spotcheck-records-egress-it-does-not-enforce-it.md) (D-10 — the decision's
   scope and the four outcomes),
   [ADR-0058](docs/adr/0058-the-execution-subject-gains-an-adapter-axis.md) (A-1 — the adapter axis),
   [ADR-0061](docs/adr/0061-the-adapter-registry-is-a-directory-and-a-manifest.md) (A-4 — the manifest's
   field list),
   [ADR-0065](docs/adr/0065-an-adapter-is-classified-and-local-only.md) (A-8 — **rule 1 is a direct
   instruction to this row**),
   [ADR-0009](docs/adr/0009-setspec-schema-strategy.md) and
   [ADR-0022](docs/adr/0022-capability-evidence-record-contract.md) (the versioning strategy and the
   evidence record's normative field list).
6. `src/setspec/model/`, `src/setspec/capability/` and `src/setspec/goldens/` — the existing payload
   modules and the golden layout you are extending.

**The ADRs were amended on 2026-09-02** by a review pass (docs commit `42d25ea`). Read them from
disk, not from memory of an earlier summary; three of the changes land directly on this row.

## The work

### 1. `governance.egress_decision` 1.0 — a new SetSpec-owned root

Per [ADR-0051](docs/adr/0051-plans-stay-internal-and-one-payload-travels.md) §4, `governance.*` is a
**SetSpec-owned root**, not an application namespace. It exists because the payload has a named
second reader: IdeaPress's S4 badge reads decisions PromptCadence exported, with SpotCheck not
installed.

* The field set is SpotCheck spec §7's `EgressDecision`: `decision_id`, the embedded request
  (`run_id`, `source_ref`, `data_classification`, `target{name, remote, max_data_classification,
  provider_kind}`), `verdict`, `reason`, `policy_name`, `policy_version`, `decided_at`.
* `verdict` is `approved | denied | violation`. **All three are valid in the payload**, including
  `violation`, which no shipped policy produces but a caller's verification step writes after the
  fact (ADR-0054 rule 7). A schema that cannot express it is wrong.
* `data_classification` and `max_data_classification` serialize as the lowercase strings
  `"public" | "internal" | "confidential"` — `baseaicore.DataClassification`'s serialized form
  (ADR-0046 rule 2). SetSpec **carries** the value; it does not define the vocabulary, and it must
  not mint aliases or a parallel enum.
* `max_data_classification` is nullable, because "remote with no declared ceiling" is the
  fail-closed case the consumer must be able to represent and record
  ([ADR-0054](docs/adr/0054-spotcheck-records-egress-it-does-not-enforce-it.md) rule 3).

### 2. `model.adapter_manifest` 1.0

The operator-reviewed record described by
[ADR-0061](docs/adr/0061-the-adapter-registry-is-a-directory-and-a-manifest.md) rule 1: `name`,
`artifact_file` (a relative path), `artifact_sha256` (the identity), optional `source_sha256`
(lineage), `base` (provider model name plus artifact digest, the digest optionally absent →
`name_only` confidence), `declared_capabilities[]` (namespaced vocabulary terms, validated against
the capability vocabulary, a bare reserved root refused), `data_classification`, `format = "gguf"`,
`created_at`, `notes`.

**`data_classification` is `required` in the JSON Schema, with no default.** ADR-0065 rule 1 is
explicit and was sharpened for this row on 2026-09-02: a manifest omitting it is **invalid**, and
its adapter is unavailable until a person supplies the value. Do not give the field a schema
default — ADR-0046's fail-closed default governs *callers declaring their own data*, not manifests,
and a default here would let a validator silently fill in the one field that governs egress.

`name` is validated against `^[a-z][a-z0-9_-]{1,63}$` and digests against the normalized
`sha256:<64 hex>` form, matching `baseaicore.AdapterIdentity`. Reuse `baseaicore`'s normalization
rather than writing a second validator.

### 3. `CapabilityEvidence` v1.1 — optional adapter fields

Additive minor on an existing payload, following the ADR-0032 precedent (which added the
goal-sourced group the same way). The new fields are optional and absent on every non-adapter
record. **The whole point of this sub-task is the thing it must not change**, so:

* A record written without adapter fields must be **byte-for-byte identical** to what `0.4.0`
  writes today. Prove it with a golden, not an argument.
* `SUPPORTED_SCHEMAS` records the new highest-known minor for `capability.evidence`'s existing
  major. Do not bump a major. Do not touch a frozen v1.0 payload's shape.

### 4. Schemas, goldens and the I15 verification

* JSON Schema for each new payload, published under the existing schema directory layout, plus the
  regenerated schema for `CapabilityEvidence` at v1.1.
* **At least three goldens each**, per the row. For the manifest include: a digest-verified base, a
  name-only base, and a refusal case. For the decision include: `approved/within_ceiling`,
  `denied/no_ceiling_declared` (the fail-closed row), and a `violation`.
* **I15 is the exit condition** ([adapter-roadmap §7](docs/roadmap/adapter-roadmap.md)): a
  `setspec`-only reader validates the manifest and adapter-evidence goldens, **and today's evidence
  records round-trip byte-identically**. Write that second half as a test over the *existing*
  committed goldens — if any of them changes, the release is not additive and you must stop rather
  than update the golden to match.
* Round-trip per class (`load(dump(x)) == x`), unknown-minor acceptance with extras preserved
  through the `In` model, canonical JSON byte-stability.

### 5. Documentation

Write a **Phase 6 section** into
[`docs/packages/setspec/development-plan.md`](docs/packages/setspec/development-plan.md), in the
shape of Phases 4 and 5, with demonstrable acceptance criteria — the house rule is that a phase
states what to run and what a person should see. Update
[`docs/packages/setspec/spec.md`](docs/packages/setspec/spec.md) §7's payload list, §11's contracts
where the new root touches them, and §19. Then mirror both files into `py/SetSpec/docs/` and verify
with `cmp`. Update `README.md`'s status line and `CHANGELOG.md`; version is `0.5.0`.

### 6. Gate, then prepare the release

The full gate green with the interpreter named. Commit in logical groups. **Do not tag.**

## Before you finish — three closing duties

1. **Write `docs/history/B1_HANDOFF.md` at the workspace root.** It is read by the human before B3 is kicked
   off, and by the B3 session itself. Sections: the gate results with interpreter and exact
   commands; the payload shapes as published (field lists — B3 pins these); `cmp` output for both
   mirrored documents; the commits made; and — the section that matters most —
   **"Before the next session"**, listing every change that must happen before B3 starts. At
   minimum that includes tagging and publishing `setspec 0.5.0`, since B3 pins the published
   package. Add anything you discovered: a spec passage that was wrong, a field you had to shape
   differently from the ADR, a decision you had to make. If the list is empty except for the
   publish step, say so plainly.
   **Never overwrite an existing root file** — the workspace root is not a git repository and has
   no history to recover from. If `docs/history/B1_HANDOFF.md` exists, write `B1_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what shipped, what the gate said, what is waiting on the human,
   and anything in "Before the next session". A few sentences, not the document again.
3. **Prepare the commits.** Everything committed on `main` in `py/SetSpec` and in `docs`, working
   trees clean, nothing pushed and nothing tagged. Say in the summary exactly what is waiting:
   the commits, the tag to create, the `pypi` environment approval, and the post-publish
   `pip install setspec==0.5.0` check in a clean virtualenv.

## Constraints and stop rules

* **v1.0 payloads are frozen.** This release is additive or it is wrong. Never edit a golden to
  make a test pass — a changed golden means the change was not additive, and that is a stop.
* **No new dependency.** `setspec` imports `baseaicore` and pydantic; nothing else.
* **Do not implement SpotCheck.** This row publishes the shape; B3 implements the behaviour.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` at the start and at the end of
  the session; `git checkout --` anything modified that you did not edit; commit at each logical
  group rather than once at the end; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, leave the tree clean, and record
  exactly where you stopped in `docs/history/B1_HANDOFF.md`.
