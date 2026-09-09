# Kickoff — C1: CutCtx Phase 1

**Row:** C1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Opus 5 · xhigh. **Repository:** `/home/jpk/ai/suite/py/CutCtx` — it exists, is
`git init`-ed with one commit and a `.gitignore`, and has `origin` configured; **everything else is
yours to create.**
**Runs after:** A2, which is **done** — `baseaicore 0.4.1` is on PyPI. Independent of B1–B5 and of
C2; it may run before, after or beside them.
**Overnight:** permitted ([model-assignment §2.12](docs/roadmap/model-assignment.md) — only
batches D, G and I2's security half are barred).

**Why this row is Opus at xhigh, and what that means for how you spend the session.** The
`_invariants` module is the first instance of a thing every later policy routes through
([model-assignment §3.1](docs/roadmap/model-assignment.md), the first-instance rule): E1 adds three
more policies against it, I1 wires it into PromptCadence, J3 rewrites IdeaPress's reduction order as
a chain over it. And **the choice of properties in the property tests is the deliverable** — not
their count and not their pass rate. A property suite that generates only well-formed transcripts
and asserts only what the implementation obviously does is worth nothing; the value is in the
generators that produce the shapes you did not think of and the properties that would fail if the
invariants were subtly wrong. Budget the session accordingly: the property design deserves more of
your time than `DropOldestPolicy` does.

---

## Preconditions

* **`baseaicore` is at `0.4.1` on PyPI, which is what this arc pins.** The
  [development plan](docs/packages/cutctx/development-plan.md) pins `>=0.4.1` for the arc baseline
  even though CutCtx uses nothing beyond `SuiteError` and helpers. Pin `>=0.4.1,<0.5`.
  `DataClassification` is **not** used here: CutCtx never sees a classification — the summarization
  request crosses the boundary and PromptCadence's own tier routing carries the classification
  ([ADR-0052](docs/adr/0052-compaction-is-a-view-and-the-package-plans-it-only.md) decision 5).
* **The remote already exists** — `origin` → `https://github.com/JPKell/CutCtx.git`. Commit on
  `main`. **Do not push, do not tag, do not publish**; list the push and the first-CI-green
  confirmation in the handoff as operator steps (the B2 precedent). `cutctx 0.1.0` ships at the end
  of Phase 2, row E1.
* **The PyPI name `cutctx` is very likely unreserved.** Check
  `https://pypi.org/pypi/cutctx/json` and record the result in the handoff; master architecture
  §1.1 requires distribution-name availability to be verified before first publish, and the
  fallback (`aisuite-cutctx`) would change the import name, `pyproject.toml`, `.importlinter`,
  the coverage paths and every document that names the package — so it must be settled well before
  E1, not at publish time.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/CutCtx`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  CutCtx section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2
  (lines 180–190 — six bullets, each of which is a test you owe), then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name (`token_estimate`, `max_tokens`,
  `target_tokens` — the spec's names are already correct, keep them); keyword-only for anything
  optional or boolean; `@dataclass(frozen=True, slots=True)` for every value object; line length
  100; `mypy --strict` with no bare `Any` at a public boundary and no `# type: ignore` without a
  trailing reason.
* **No injected clock, and no timestamps anywhere.** This is the one package in the suite that
  needs no clock: a plan carries no time, because a plan must be byte-identical on re-derivation.
  If you find yourself wanting a timestamp on a `CompactionReport`, the caller stamps it.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, `CHANGELOG.md` started, one Conventional
  Commit per logical group. **Name the interpreter and the exact invocation in the handoff doc**
  (M5C-13). There is no `python3.12` on this machine; say which you used.
* **Dependency pinning:** `cutctx` imports `baseaicore` and **nothing else** — the dependency budget
  in [gold-standards §1](docs/standards/gold-standards.md) is literally `0` non-suite runtime
  dependencies, and exceeding it requires an ADR. `hypothesis` is a **dev** dependency and does not
  touch that budget.
* **Documentation is mirrored.** The workspace copies under
  `/home/jpk/ai/suite/docs/packages/cutctx/` are authoritative; copy `spec.md` and
  `development-plan.md` byte-identically into the repo's own `docs/packages/cutctx/` and verify
  with `cmp` ([outstanding-work §4](docs/roadmap/outstanding-work.md)).

## Setup

```bash
cd /home/jpk/ai/suite/py/CutCtx        # exists: .git (one commit) + the canonical .gitignore
python -m venv .venv && source .venv/bin/activate
# copy the toolchain from py/LoadLedger — the freshest sibling and the closest in shape
# (zero runtime dependencies, 95 % coverage floor, docs mirrored into the repo, same CI):
#   pyproject.toml  .importlinter  .editorconfig  .pre-commit-config.yaml
#   .github/workflows/  requirements/  CONTRIBUTING.md  LICENSE  SECURITY.md
# adapt names, then:
pip install -e ".[dev]" && pre-commit install
```

**Do not overwrite `.gitignore`** — it is the suite's canonical one plus the import-linter cache
line. You may *append* `.hypothesis/` to it; say so in the handoff, since it is the first time the
suite has needed that line.

Copy, do not invent: ten repositories now share this toolchain, and an eleventh that differs is a CI
failure nobody expected. The coverage floor for a shared package is **95 %**.

## Reading list

1. [`docs/packages/cutctx/spec.md`](docs/packages/cutctx/spec.md) — §7 is the normative public API
   and you implement it as written. §11 (public contracts) is the list the `_invariants` module
   exists to enforce; §13 is the error table; §15 the performance targets; §18 the test strategy.
2. [`docs/packages/cutctx/development-plan.md`](docs/packages/cutctx/development-plan.md)
   **Phase 1** — the file layout, the test list, the acceptance criteria, and two named failure
   modes you are expected to have already defended against. Phase 2 is row E1: read it only to know
   what you are deferring and what shapes must not foreclose it.
3. [ADR-0052](docs/adr/0052-compaction-is-a-view-and-the-package-plans-it-only.md) (**D-8**) — the
   decision this package exists to obey. Read the *Alternatives considered* section in full: the
   rejected `Summarizer` protocol is the design you will be tempted to reach for the moment the
   two-phase protocol feels awkward, and the reasons it was rejected (determinism, atomicity) are
   exactly the properties you are about to test.
4. [ADR-0023](docs/adr/0023-runtime-profile-resolution.md) — silent truncation is never acceptable.
   `budget_unmet` and `BudgetUnsatisfiable` are the transcript-shaped application of that rule.
5. [ADR-0016](docs/adr/0016-unavailable-is-not-zero.md) — an estimate is labelled as an estimate and
   is never presented as a count. The estimator ratio rides on the plan for exactly this reason.
6. [`docs/apps/promptcadence/lifecycle.md`](docs/apps/promptcadence/lifecycle.md) §7 — the consumer,
   in eleven lines. It is also the only place that says what the `context.compacted` event body
   contains, which matters for `CompactionReport` (see "The work", §1).
7. [`docs/apps/ideapress/workflows.md`](docs/apps/ideapress/workflows.md) §7 (around line 258) —
   **the second consumer, and the one that is not hypothetical.** Its context table and its
   reduction order ("research notes → distant unit summaries → adjacent unit summaries", with the
   unit specification and requirements never dropped, failing with numbers if they alone exceed the
   budget) is the mapping sketch the plan requires you to write into the docstrings *now*, before
   PromptCadence exists to bias the shape. The named risk for this phase is designing
   `TranscriptTurn` PromptCadence-shaped; this is the mitigation, and it is not optional.
8. `py/LoadLedger` — the repository-shape precedent, and a recent example of the same "pure,
   deterministic, no I/O" package discipline.

## The work

Phase 1 is the vocabulary, the invariants and one honest policy: pure, deterministic, no I/O, no
model, no persistence.

### 1. `types.py` — and three shapes the spec leaves you to settle

`TranscriptTurn`, `Transcript`, `CompactionBudget`, `TurnAction`, `SummarizationRequest`,
`CompactionPlan`, `CompactedTranscript`, `CompactionReport`, plus the `Role` and `Action` enums.
Note that **`Role` is CutCtx's own** — `baseaicore` has no message/role vocabulary and is not
gaining one for this.

Three things spec §7 does not fully determine. Settle each deliberately, document the reasoning in
the docstring, and record it in the handoff under a heading the E1 and I1 sessions will find:

* **`CompactionReport`'s fields.** §7 names the type but not its members; §11.7 says it is *exactly*
  the body of the suite's `context.compacted` event, and lifecycle §7 says that event carries
  "before/after token estimates and the turns affected". You are defining a payload two applications
  will emit without reshaping — decide it as though it were a SetSpec payload, even though it is
  not one yet.
* **`budget_unmet`.** §13's last row requires a plan to be returned still over budget with a
  `budget_unmet` flag; §7's `CompactionPlan` dataclass does not list the field. It is a Phase 2
  concept (only a chain exhausts) but a Phase 1 *shape* — put it on the plan now, defaulting
  `False`, or E1 mutates a frozen, golden-tested type. Say which you did and why.
* **`metadata: Mapping[str, str]`** on a frozen, slotted dataclass: pick the immutable default and
  the equality/hashing behaviour that keeps goldens stable, and be explicit that policies treat it
  as opaque (spec §4) — no policy reads it in Phase 1 and none should learn to.

Who sets `token_estimate` on a turn is the caller, not the package. The package does not silently
re-estimate a turn it was handed; where it must estimate (a mask stub, a summary target) the ratio
is recorded. Use `baseaicore`'s `canonical_json` and `sha256_of` for anything serialized or hashed
rather than rolling a second convention — the golden format is set here and E1 inherits it.

### 2. `_invariants.py` — the module this row exists for

Spec §11 contracts 1–3, in one place, enforced by validation and not by convention:

* the system turn and every `pinned` turn are untouchable;
* the `protected_recent_turns` tail is never masked, summarized or dropped;
* a tool call and its result travel **together** — masked together, in the same summary group, or
  dropped as a pair, never separated;
* pinned + protected alone exceeding the budget raises `BudgetUnsatisfiable` **with both numbers**.

Acceptance criterion 2 is the hard part: **the invariant module is the only path to a valid plan,
asserted structurally.** Design that, do not merely intend it. A `CompactionPlan` a policy can
construct directly is a bypass, and the first policy to bypass it will be one written by a cheaper
model at E1, in a hurry, that passes its own tests. Options worth weighing: a private constructor
with a validating factory that every policy must call; a plan that carries proof of validation;
a structural test (AST over `src/cutctx/policies/`) asserting no policy module names the plan
constructor. Whatever you choose, there must be a test that **fails** when a policy is written that
skips validation — write that test's negative case first, with a deliberately delinquent fake
policy in the test suite, so you know the guard bites.

The plan's Known-risks line — "pair detection missing multi-call turns" — belongs here: one
assistant turn may carry several tool calls, so pairing is not one-to-one. Decide what the model
of a multi-call turn is in Phase 1, because masking (E1) will lean on it.

### 3. `estimator.py`, `executor.py`, `errors.py`

`TokenEstimator` protocol and `CharRatioEstimator(chars_per_token=4.0)` with the ratio recorded on
plans (`estimator_ratio`), never presented as a count.

`CompactionExecutor.apply` — input transcript unchanged (assert it, don't assume it),
`PlanTranscriptMismatch` when the plan was built for other turn ids, `SummaryMissing` naming the
group. **Report totals must equal plan estimates**; the plan names "token estimates drifting between
plan and report" as a likely failure mode, so make it structurally hard rather than tested-once —
if the report can compute a number the plan already computed differently, one of them is redundant.

`errors.py` per spec §7: `CompactionError` (`COMPACTION_ERROR`), `BudgetUnsatisfiable`,
`SummaryMissing`, `PlanTranscriptMismatch`, with the documented codes, all subclassing
`baseaicore.SuiteError`.

### 4. `policies/drop_oldest.py`

The deterministic last resort: drop oldest unpinned turns, tool pairs together, until the budget
fits — and if it cannot fit without touching the untouchable set, that is `BudgetUnsatisfiable`,
never a violated invariant. It routes through `_invariants` like every future policy, and it is the
worked example E1 copies.

### 5. Tests — the property suite is the deliverable

The plan's list is the floor: `BudgetUnsatisfiable` with both numbers; executor immutability;
`PlanTranscriptMismatch`; report totals equal plan estimates; repeated runs byte-identical with
goldens committed; the import-graph purity test (no HTTP client, no provider, no database, no
filesystem — [gold-standards §2](docs/standards/gold-standards.md)); the performance targets from
spec §15 behind the `performance` marker.

Then `tests/property/test_invariants_property.py`, where the judgment lives. **Design the generators
before the properties.** A `Transcript` strategy that only ever emits well-paired, well-ordered,
modestly sized transcripts will pass everything and prove nothing. It must be able to produce:
multi-call assistant turns; tool results whose call is far away; runs of pinned turns; an entirely
pinned transcript; a transcript shorter than `protected_recent_turns`; an empty transcript;
degenerate budgets (zero, one, exactly the untouchable total, one below it); and turns whose
`token_estimate` is zero or enormous. Prefer generating structurally-valid transcripts by
construction over `filter`-ing invalid ones — heavy filtering gives you flaky health-check failures
and useless shrinking.

The properties that follow are a floor, not a list to stop at:

* no plan from any policy acts on the untouchable set;
* pair integrity holds in every action class, in both directions (no orphaned call, no orphaned
  result), including across a multi-call turn;
* every turn id appears **exactly once** in `actions` — a plan is a total function over the
  transcript, and a turn the plan forgot is the silent bug this property exists to catch;
* `apply()` leaves the input transcript untouched, and the output contains no turn id the plan did
  not keep, mask or summarize;
* the plan's `tokens_after_estimate` agrees with an independent estimate of the applied view;
* determinism: the same transcript, budget and configuration produce byte-identical plans on
  re-derivation, and a plan built from a shuffled-but-equivalent construction path is identical;
* the budget outcome is trichotomous and honest — fits, or `budget_unmet`, or `BudgetUnsatisfiable`.
  There is no fourth case, and in particular there is no plan that claims to fit while being over.

Note the interaction with `pytest-randomly`, which randomizes order suite-wide: pin a hypothesis
profile so a CI failure is reproducible, and say in the handoff how a failing example is replayed.
A failure that only reproduces under a seed is a real bug (`CLAUDE.md`).

**Write the rationale down.** The handoff gets a section naming each property, what it would catch,
and — the part that matters — the properties you considered and rejected, with why. That section is
the artifact E1, I1 and J3 read; the code is what they inherit.

### 6. Documentation and repository furniture

`README.md` (status line: Phase 1, unreleased; the two-phase plan/fulfil/apply protocol is the
package's shape and belongs in the README, since `SummaryMissing` is the loud failure of the step
callers forget), `CHANGELOG.md` with `## [Unreleased]`, `LICENSE`, `SECURITY.md` and
`CONTRIBUTING.md` from LoadLedger, and the two mirrored documents under `docs/packages/cutctx/`
verified with `cmp`.

### 7. Gate and commit

The full gate green with the interpreter named. Commits on `main`. No tag, no publish, no push.

## Before you finish — three closing duties

1. **Write `docs/history/C1_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands; the public surface as built against spec §7, naming every deviation and why;
   **the three settled shapes from §1 above** (report fields, `budget_unmet`, metadata) as decisions
   E1/I1 must not relitigate; **the property rationale** from §5; how the "invariants are the only
   path" guard is enforced and how it is proven to bite; the repository's toolchain provenance;
   the commits made; and **"Before the next session"** — at minimum: push `main`, confirm CI green
   on the first push, and the PyPI-name check result for `cutctx`. Add anything you found: a spec
   passage that was wrong or underdetermined, a shape you had to settle, a trap the plan did not
   name. **Never overwrite an existing root file** — the workspace root is not a git repository. If
   `docs/history/C1_HANDOFF.md` exists, write `C1_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what was built, what the gate said, which properties you chose
   and which you rejected, what is waiting on the human. A few sentences.
3. **Prepare the commits.** Everything committed on `main`, working tree clean, nothing pushed,
   nothing tagged. Say exactly what is waiting for the operator.

## Constraints and stop rules

* **No masking, no summarizing, no `PolicyChain`.** That is Phase 2, row E1. `SummarizationRequest`
  is a Phase 1 *type* — the executor must handle a plan containing one, and `SummaryMissing` must
  work — but no policy in this phase emits one.
* **No model access, and no import that could become one.** No HTTP client, no provider, no
  ModelRack — a capability package may not import a sibling, and D-8's whole point is that the
  second inference path is absent by construction. The import-graph test asserts it.
* **No I/O of any kind** — no filesystem, no network, no environment reads, no logging. The package
  logs nothing (spec §17); the `CompactionReport` is what a consumer logs.
* **No prompt text ever appears in this package.** A prompt is named by `prompt_id`
  ([ADR-0012](docs/adr/0012-prompt-storage-format.md)).
* Transcript content is untrusted model output: opaque text, no parsing, no interpolation, no
  execution (spec §14). A mask stub carries a hash, never an excerpt.
* **Never weaken `.importlinter`** to make an import work.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` at the start and end of the
  session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/C1_HANDOFF.md`.
