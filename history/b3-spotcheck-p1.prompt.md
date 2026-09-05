# Kickoff — B3: SpotCheck Phase 1

**Row:** B3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Sonnet 5 · high. **Repository:** `/home/jpk/ai/suite/py/SpotCheck` — **it does not exist
yet; creating it is the first task.**
**Runs after:** B1 — and this one is a **hard edge**, not a convenience
([outstanding-work §3](docs/roadmap/outstanding-work.md)): the payload publishes before its consumer
pins it. That is the FreeWeight-P11 lesson.
**Overnight:** permitted, at effort **high**
([model-assignment §2.12](docs/roadmap/model-assignment.md)).

---

## Preconditions — check both, and stop if either is unmet

```bash
pip index versions baseaicore     # must list 0.4.1  — DataClassification lives there
pip index versions setspec        # must list 0.5.0  — governance.egress_decision 1.0 lives there
```

* **`baseaicore 0.4.1`** supplies `DataClassification`. This package defines **no** classification
  vocabulary of its own — that is ADR-0046's whole point and ADR-0054 rule 2 restates it.
* **`setspec 0.5.0`** supplies `governance.egress_decision` 1.0, which `EgressDecision.to_payload`
  and `from_payload` must round-trip against. Building against an unpublished local path here would
  defeat the hard edge above: the point of B1 → B3 is that the consumer pins a *published* shape.

If either is missing, **stop and say so.** Do not vendor the enum, do not hand-write the payload
model, do not pin a local path as a workaround.

Read `docs/history/B1_HANDOFF.md` at the workspace root before starting — it carries the field lists as actually
published, and anything B1 had to settle.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/SpotCheck`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  SpotCheck section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2,
  then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name; keyword-only for anything optional or
  boolean; **injected clock and injected id generator** (the determinism goldens depend on both);
  `@dataclass(frozen=True, slots=True)` for value objects; line length 100; `mypy --strict` with no
  bare `Any` at a public boundary and no `# type: ignore` without a trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, `CHANGELOG.md` started, one Conventional
  Commit per logical group. **Name the interpreter and the exact invocation in the handoff doc**
  (M5C-13).
* **Dependency pinning:** `spotcheck` imports `baseaicore` and `setspec` — it is the second
  capability package permitted to import SetSpec, and for the same reason MirrorWall is: it owns
  the Python form of a cross-application payload
  ([master architecture §2](docs/architecture/master-architecture.md),
  [ADR-0051](docs/adr/0051-plans-stay-internal-and-one-payload-travels.md)). Pin the published
  versions. `sqlalchemy` arrives in Phase 2 (row E3) as the `spotcheck[sql]` extra — not now.
* **Documentation is mirrored.** The workspace copies under
  `/home/jpk/ai/suite/docs/packages/spotcheck/` are authoritative; copy `spec.md` and
  `development-plan.md` byte-identically into the new repo on creation and verify with `cmp`.
* **You are not authorised to tag or publish.** Phase 1 does not publish; `0.1.0` ships at the end
  of Phase 2 (row E3).

## Setup

```bash
cd /home/jpk/ai/suite/py/SpotCheck       # already exists, with a .gitignore in place
git rev-parse --git-dir >/dev/null 2>&1 || git init -b main
python -m venv .venv && source .venv/bin/activate
# copy the toolchain from a published sibling (py/WeightsDB or py/MirrorWall), adapt names, then:
pip install -e ".[dev]" && pre-commit install
```

The directory and its `.gitignore` are already in place — the `.gitignore` is the suite's
canonical one plus the import-linter cache line. **Do not overwrite it** when you copy the rest
of the toolchain from a sibling; copy every other file and leave that one alone.


Copy the toolchain, do not invent one. Coverage floor for a shared package is **95 %**.

## Reading list

1. [`docs/packages/spotcheck/spec.md`](docs/packages/spotcheck/spec.md) — §7 is the normative public
   API and you implement it as written: `EgressTarget`, `EgressRequest`, `Verdict`,
   `EgressDecision` with `to_payload`/`from_payload`, the `EgressPolicy` protocol,
   `OrderedClassificationPolicy` and its four documented outcomes. Read §3 (non-goals) twice —
   this package's defining risk is scope creep.
2. [`docs/packages/spotcheck/development-plan.md`](docs/packages/spotcheck/development-plan.md)
   **Phase 1** — the file layout, the test list, the acceptance criterion. Phase 2 is out of scope.
3. [ADR-0054](docs/adr/0054-spotcheck-records-egress-it-does-not-enforce-it.md) (D-10) — the
   decision that bounds this package to exactly three things: the payload, the ordered comparison,
   and an append-only ledger. **Rule 3 is the fail-closed rule** (a remote target with no declared
   ceiling is denied, never assumed public); **rule 5 is the bar** (no enforcement); **rule 7** is
   why `VIOLATION` must be constructible.
4. [ADR-0046](docs/adr/0046-data-classification-is-ordered-and-defaults-closed.md) (D-2) — the
   ordering is the contract, `max()` is the lattice join, and the type is `baseaicore`'s. This
   package "defines no levels, no aliases and no parallel taxonomy".
5. [ADR-0011](docs/adr/0011-shared-package-boundaries.md) — the boundary-violation rule ADR-0054's
   revisit trigger invokes.
6. `docs/history/B1_HANDOFF.md` (workspace root) and `py/SetSpec`'s published `governance.egress_decision`
   goldens — you round-trip against those exact files.

## The work

Phase 1 is the evaluation and the contract: deterministic, fail-closed, no persistence.

### 1. `types.py`

`EgressTarget`, `EgressRequest`, `Verdict`, `EgressDecision` with `to_payload` / `from_payload`,
exactly as spec §7 states them. `max_data_classification` is `DataClassification | None` and the
`None` case is meaningful — it is the fail-closed row, not an oversight.

### 2. `policy.py`

The `EgressPolicy` protocol and `OrderedClassificationPolicy`, whose entire behaviour is four rows:

```text
local target                  -> APPROVED / "target_not_remote"
remote, no declared ceiling   -> DENIED   / "no_ceiling_declared"     (fail closed)
classification <= ceiling     -> APPROVED / "within_ceiling"
classification >  ceiling     -> DENIED   / "classification_exceeds_ceiling"
```

The comparison is `baseaicore.DataClassification`'s ordering — `<=` on the type, not a rank lookup
or a local table. The reason strings are **exact**; a reason drifting from the documented set is the
plan's named failure mode, so assert them as literals.

### 3. `errors.py`

`SpotCheckError` and `StoreFailure`, subclassing `baseaicore.SuiteError` with the documented codes.
Note what is *not* here: `evaluate` never raises for a deny. **A deny is data**
([ADR-0054](docs/adr/0054-spotcheck-records-egress-it-does-not-enforce-it.md) rule 4), and a policy
that raises on refusal is the defect ADR-0053 rejects for tools, arriving in a second package.

### 4. Tests

* **The full policy matrix, parametrized over the enums, not hand-listed.** Acceptance criterion 1
  says exhaustive *by construction*: every classification × {local, remote-with-ceiling at each
  level, remote-without-ceiling}. A hand-written list of cases is the same test with a hole in it.
* Round-trip against the published SetSpec goldens; an unknown-minor payload read without loss
  (the `In` model preserves extras).
* Determinism goldens with injected ids and clock.
* **`VIOLATION` is constructible and serializable but never produced by the shipped policy** —
  assert that over the whole matrix, not with a single case. It exists because a caller's
  after-the-fact verification writes it (PromptCadence contract 4).

### 5. Documentation and repository furniture

`README.md` (status line: Phase 1, unreleased), `CHANGELOG.md` with `## [Unreleased]`, `LICENSE`
and `SECURITY.md` from a sibling, and the two mirrored documents verified with `cmp`.

### 6. Gate and commit

Full gate green with the interpreter named. Commits on `main`. No tag, no publish, no remote.

## Before you finish — three closing duties

1. **Write `docs/history/B3_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands; the public surface as built against spec §7, with any deviation and its reason;
   confirmation that the round-trip runs against the *published* `setspec 0.5.0` goldens (name the
   version you installed); the commits made; and **"Before the next session"** — every change
   needed before E3 (SpotCheck P2) or any consumer proceeds. At minimum: create the GitHub remote,
   reserve the PyPI name `spotcheck`, push `main`, CI green on first push. Add anything you found:
   a payload field that did not match the spec, a reason string the ADR and the spec disagreed
   about, anything you had to settle.
   **Never overwrite an existing root file.** If `docs/history/B3_HANDOFF.md` exists, write `B3_HANDOFF.2.md`
   and say why.
2. **Summarise in chat**, briefly: what was built, what the gate said, what is waiting on the
   human, and anything in "Before the next session".
3. **Prepare the commits.** Everything committed on `main`, tree clean, no remote, nothing tagged.

## Constraints and stop rules

* **No enforcement, ever.** SpotCheck refuses no call, halts no trajectory, paints no badge and
  makes no HTTP request — it "could not intercept one"
  ([ADR-0054](docs/adr/0054-spotcheck-records-egress-it-does-not-enforce-it.md) rule 5). If a design
  question tempts you toward interception, the answer is that it belongs to the caller.
* **No application policy.** What `internal` means in a deployment, which tiers exist, when a human
  must confirm — all caller-side. The package's only opinion is the ordering.
* **No persistence.** The ledgers and mounting are Phase 2 (row E3), which copies LoadLedger P2's
  proven pattern. Shipping a table here spends that.
* **No parallel vocabulary.** No levels, no aliases, no local enum mirroring
  `DataClassification`.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` at the start and end; commit
  per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and say where in
  `docs/history/B3_HANDOFF.md`.
