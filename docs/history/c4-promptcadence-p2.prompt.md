# Kickoff — C4: PromptCadence Phase 2 (domain core)

**Row:** C4 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Opus 5 · xhigh. **Repository:** `/home/jpk/ai/suite/PromptCadence` — Phase 1 is built,
green and on `origin/main` at `7281432`.
**Runs after:** B4, which is **done** — the skeleton, the full spec §12 configuration surface,
WeightsDB wiring with migration `0001`, MirrorWall envelopes, health and the CLI stub. Independent
of C3, C5 and C6.
**Gates:** everything downstream. D2 (Phase 3, **Fable 5**), E4, F1, F2 and G1 all build on the
shapes this session freezes.
**Overnight:** permitted ([model-assignment §2.12](docs/roadmap/model-assignment.md) — only
batches D, G and I2's security half are barred).

**Why this row is Opus at xhigh, and what that means for how you spend the session.** Most of the
phase is transcription: the T1–T17 transition table, the deviation matrix and the tier rules are
all written out normatively in [`lifecycle.md`](docs/apps/promptcadence/lifecycle.md), and
transcribing them accurately is not what the premium is for. The premium is for one thing:

> **This phase freezes the shape of the design's load-bearing wall.** The `ExecutionIntent` is what
> makes governance invariance *structural* rather than procedural ([spec
> §11](docs/apps/promptcadence/spec.md) contract 1,
> [ADR-0056](docs/adr/0056-every-turn-executes-under-one-execution-intent.md)). Contract 1 is
> proven at **G1** by a diff test (I11) that a planned and a bypassed trajectory produce record
> sets identical but for the plan rows. If the intent's shape is wrong, that test fails at the end
> of the arc, and what it invalidates is the design claim, not one phase's code.

Two consequences for how you work:

* **The deviation taxonomy is closed by construction** — exactly one category per intent field a
  turn can contradict. That property is only true if the intent has the right fields and if
  `compare()`'s input is the right shape. Both are decided here, and adding a category later means
  adding an intent field later, in a table three later phases already switch on.
* **Phase 3 is written by Fable 5** — daytime, reviewed, but still a different model working from
  your docstrings and your types. Every seam you leave underdetermined is where that session
  improvises, and D2 is the phase that also builds the fake LoadCoach every later phase trusts.

Budget accordingly: the five undetermined shapes in "The work" §1, the intent design in §5, and
the `compare()` input in §6 deserve more of your time than the state-machine transcription does.

---

## Preconditions

* **Phase 1 is complete and pushed.** `git log --oneline origin/main -1` shows `7281432`;
  `git status --short` must be empty before you start. If the tree is dirty, `git checkout --`
  anything you did not edit (`CLAUDE.md`, working-tree integrity).
* **Nothing new is installed.** This phase adds no runtime dependency: it is pure domain. In
  particular **`loadledger` is not a dependency yet** — the plan puts approval-policy evaluation
  here as "a pure function over tier policy + ledger verdicts", and the ledger itself arrives at
  P5 (row F1). See §7 below for how you take verdicts without taking the package.
* **Two pins in `pyproject.toml` disagree with their surroundings.** Check both and record what you
  find; do not silently leave either:
  * `setspec>=0.4,<0.5`, while [spec §5](docs/apps/promptcadence/spec.md) requires
    **≥ 0.5** for `governance.egress_decision` and `setspec` is now at `0.6.0` (tagged, published).
    Nothing before P6 consumes it, so this is not your blocker — but D2 compiles locks, and a pin
    that excludes the version the spec names should not survive that.
  * `pytest>=8,<9` in `[dev]`, while LoadCoach, LoadLedger and CutCtx all moved to
    `pytest>=9.0.3,<10` to exclude PYSEC-2026-1845. CI's `security` job runs `pip-audit` against
    the locks; either it is not seeing this or it is about to.
* **You are not authorised to push or tag.** Commit on `main` and stop; the push and the CI
  confirmation are operator steps listed in your handoff (the B2/C1/C2 precedent).

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/PromptCadence` (and in
  `/home/jpk/ai/suite/docs` for the authoritative copy of the three mirrored documents).
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  PromptCadence section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md)
  §2 (lines 159–178 — ten bullets; the first two are this phase's and the rest are shapes you must
  not foreclose), then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name (`context_budget_tokens`,
  `token_budget`, `request_timeout_hours` — the spec's names are already correct, keep them);
  keyword-only for anything optional or boolean; `@dataclass(frozen=True, slots=True)` for every
  value object; line length 100; `mypy --strict` with no bare `Any` at a public boundary and no
  `# type: ignore` without a trailing reason.
* **The domain layer imports no framework.** Not `fastapi`, not `sqlalchemy`, not `typer`, not
  `httpx`, not `jinja2` — `.importlinter`'s `domain-purity` contract already says so and
  acceptance criterion 1 is that assertion. See §2 below, where the development plan and that
  contract currently contradict each other.
* **Injection:** clocks, id generators and any source of nondeterminism arrive at the boundary.
  Intent minting, plan validation and approval evaluation must be **deterministic given their
  inputs** — that is what makes the goldens goldens, and what makes G1's invariance diff possible.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **85 %** (application floor),
  `CHANGELOG.md` updated under `## [Unreleased]`, one Conventional Commit per logical group.
  **Name the interpreter and the exact invocation in the handoff doc** (M5C-13) — B4 ran
  `PromptCadence/.venv/bin/python`, Python 3.13.15; confirm rather than copy. There is no
  `python3.12` on this machine.
* **Documentation is mirrored.** Edit the workspace copy under
  `/home/jpk/ai/suite/docs/apps/promptcadence/` first, then copy byte-identically into the repo's
  `docs/apps/promptcadence/`. The three files are `spec.md`, `lifecycle.md` and
  `development-plan.md`. Verify with `cmp`, never by eye.

## Setup

```bash
cd /home/jpk/ai/suite/PromptCadence
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be empty before you start
```

## Reading list

1. [`docs/apps/promptcadence/lifecycle.md`](docs/apps/promptcadence/lifecycle.md) — **the primary
   document for this phase**, not the spec. §2 (classification), §3 (tiers), **§4.1–4.3** (plan,
   approval, `ExecutionIntent` — read §4.3's bullet list twice; each bullet is load-bearing), §5
   (the deviation matrix, six categories × two severities × two `reapproval_scope` settings), §8.1
   (states), **§8.2 (T1–T17)**, §8.3 (recovery edges — P3's, but they constrain which states may
   hold a lease), §8.4 (DAG dispatch) and §10 (determinism and testability).
2. [`docs/apps/promptcadence/spec.md`](docs/apps/promptcadence/spec.md) **§9** (outputs — what a
   trajectory yields, and the sentence about every intent revision being retained), §10 (data
   ownership: the full table list, including the ThreadRack rejection and its "package-shaped"
   requirement), **§11 contracts 1–6**, §13 (error behaviour — the codes your refusals raise), §17
   (observability, the event names), §20 (acceptance criteria).
3. [`docs/apps/promptcadence/development-plan.md`](docs/apps/promptcadence/development-plan.md)
   **Phase 2** — the work list, the six test groups, the two acceptance criteria and the named
   risk. **Read Phase 3 as well**, not to implement it but because it tells you what D2 expects to
   find waiting: `LoopController` mints the default intent at T3, so the intent's minting API is a
   seam another model will use within days.
4. [ADR-0056](docs/adr/0056-every-turn-executes-under-one-execution-intent.md) (**D-12**) — the
   decision this phase exists to obey. Read *Alternatives considered* in full: the two-source
   design ("plan-declared vs default-policy branching") is what you will drift back toward the
   first time bypass mode feels like a special case, and collapsing it is the reason the state
   machine is seventeen rows rather than forty.
5. [ADR-0046](docs/adr/0046-data-classification-is-ordered-and-defaults-closed.md) (**D-2**) —
   ordered, three levels, defaults to `confidential`. `baseaicore.DataClassification` is the type;
   PromptCadence defines **no** parallel vocabulary and no aliases.
6. [ADR-0047](docs/adr/0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md)
   (**D-3**) — a tier is configuration over LoadCoach, never routing maths, and a model never
   sizes its own budget. Also the "universal brake" language you will meet again at F1.
7. [ADR-0048](docs/adr/0048-the-bypass-removes-planning-never-governance.md) — the bypass removes
   planning, never governance. This is contract 1 in ADR form, and it is what makes the default
   intent mandatory rather than convenient.
8. [ADR-0049](docs/adr/0049-approval-is-a-mode-with-its-own-scope.md) (**D-5**) and
   [ADR-0044](docs/adr/0044-a-state-change-and-its-event-are-one-write.md) — approval modes, and
   the rule that a transition and its event are one write. P2 owns the *pure* half of both: the
   policy verdict and the event payload shapes; P3 owns the write.
9. `src/promptcadence/` as built — `config.py` (the `Tier` pydantic model; §1(d) below),
   `infrastructure/db/models.py` (the `Thread` and `Turn` tables, deliberately generic-shaped, with
   the three `adapter_*` columns born in), `domain/__init__.py` (a placeholder whose docstring
   names the seven modules you are about to write), and `.importlinter`.
10. **`docs/history/B4_HANDOFF.md` §7** — four notes written for this session, including the `config.Tier`
    question, the ThreadRack constraint, and the confirmation that Phase 1 left no table shape for
    you to undo.

## The work

Phase 2's goal, in the plan's own words: *"every governance decision that needs no I/O is a pure,
golden-tested function."* Nothing here talks HTTP, and nothing here executes.

### 1. Five shapes to settle deliberately — and record for D2, E4, F1 and G1

Each is under-determined, or contradicted, by the documents as they stand. Settle it, document the
reasoning in the docstring, and record it in the handoff under a heading the next four sessions
will find. Where your answer contradicts a document, **say so explicitly and propose the
amendment** — an underdetermined spec passage is a defect to close, not to work around silently
(`CLAUDE.md`: if an architectural decision seems missing, that is a defect in the docs).

* **(a) `turn_facts` — the other half of the closed taxonomy.** Lifecycle §5 defines
  `compare(turn_facts, intent) → deviations` and never says what `turn_facts` is. It is not
  optional detail: the taxonomy is closed *because* there is one category per intent field, which
  only holds if `turn_facts` carries exactly the facts those fields can be contradicted by — the
  response's execution subject (model identity and provider kind, "named on every LoadCoach
  response, verified not assumed"), the tools actually requested, the classification of what came
  back, the spend, the turn count. Define it as a frozen value object, define who builds it (P3,
  from a LoadCoach response — so it must be constructible without importing anything HTTP-shaped),
  and make it impossible to compare against a fact the intent has no field for.
* **(b) Where `SqlThreadStore` lives — the plan and the layering contract contradict each other.**
  Phase 2's work list says "`domain/threads.py`: … `ThreadStore` protocol + `SqlThreadStore`".
  `.importlinter`'s `domain-purity` contract forbids `sqlalchemy` inside `promptcadence.domain`,
  and `CLAUDE.md` states the same rule for every application in the suite. The resolution is
  obvious in one direction only — the `Protocol` and the value objects in `domain/`, the SQLAlchemy
  implementation in `infrastructure/` (or `services/`) — and you must **not** weaken
  `.importlinter` to keep the plan's literal file layout. Make the change, and propose the
  development-plan amendment so D2 does not read the old sentence and put it back.
* **(c) Whether migration `0002` lands in this phase.** Spec §10 lists `plans`, `plan_steps`,
  `plan_approvals`, `approval_requests` and `execution_intents`; migration `0001` created none of
  them, and §4.3 says **every turn persists `(intent_id, revision)`** — a column `turns` does not
  have. P3's very first act (T3) mints an intent at claim, so a migration that arrives with the
  loop is a retrofit of the turn row inside the phase that is hardest to review. The recommended
  answer is that the tables and the two turn columns are **born here**, with the pure domain types
  as their source of truth; if you decide otherwise, say what D2 must add and why that is cheaper.
  Either way this phase stays pure — a migration and a store are `infrastructure`, and the domain
  modules must not learn about them.
* **(d) Four token classes on `turns`, now rather than at F1.** `turns` carries
  `input_tokens`/`output_tokens`/`thinking_tokens`.
  [ADR-0070](docs/adr/0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
  decision 7 puts `cache_write_tokens` and `cache_read_tokens` on LoadCoach's wire (row C6), and
  F1 rebuilds a `TokenUsage` from what a turn recorded. A turn row that cannot hold all four
  classes throws two of them away before the ledger ever sees them. This is the same argument that
  put the `adapter_*` columns on `turns` at Phase 1 — optional from birth, never retrofitted. If
  you take (c)'s recommendation, these ride the same migration.
* **(e) `config.Tier` → the domain `Tier`.** B4 deliberately left `config.Tier` as parsed,
  validated configuration ("nothing resolves, routes or executes — that is P2 and later"). Decide:
  does the domain take a frozen dataclass built *from* the pydantic model at the boundary, or does
  it consume the pydantic model directly? Only one of those keeps `domain` free of a validation
  framework's semantics and keeps `TierPolicy` testable without constructing a `Settings` object —
  but say which you chose and why, because every later phase constructs tiers in tests.

### 2. `domain/tiers.py` — `Tier`, `TierPolicy`

Admission is one rule: `classification ≤ tier.max_data_classification`, over
`baseaicore.DataClassification`'s ordering. Local tiers have an implicit ceiling of `confidential`;
a remote tier without a declared ceiling is a **startup refusal**, already implemented in
`config.py` — check what it does before you write a second, differently-worded version of the same
rule.

Also: the default tier, the escalation order (`policy.escalation_order` — explicit, never a silent
climb), and **tier snapshots for trajectories**. That last one matters more than it looks: a
trajectory's explanation must remain readable after the configuration changes, so a trajectory
carries the tier definitions it ran under, not a reference to today's config. Decide the snapshot's
shape and its identity (a hash? a stored document?), because F2 and I1 both read it.

Remote tiers report `TIER_UNAVAILABLE` with the reason `loadcoach_has_no_remote_provider` until
LC-E1 lands at H2 (lifecycle §3). That is a *pure* determination — a tier's availability given
configuration — so its logic belongs here even though nothing calls it until P3.

### 3. `domain/threads.py` — package-shaped, per the recorded ThreadRack rejection

`Thread`, `Turn`, `ThreadSnapshot`, `ThreadStore` protocol. Spec §10 requires these to be built
"as if they were a package (no PromptCadence vocabulary in the types), so extraction is a move, not
a rewrite" — the extraction rule from [ADR-0011](docs/adr/0011-shared-package-boundaries.md)
applied to a component that has only one consumer. That is a constraint you can violate in a way
no test catches: a `Turn` with a `tier` field or an `intent_id` field is PromptCadence vocabulary
sitting in a would-be package. Decide how the trajectory's own provenance attaches to a turn
without contaminating the type — and note that the `turns` **table** is allowed to carry those
columns; it is the domain type that must stay generic. Write the rule down; it is the sort of thing
that erodes one convenient field at a time.

### 4. `domain/plan.py` — `Plan`, `PlanStep`, the schema

The JSON Schema is **committed and golden-tested**, and it is the schema PromptCadence validates
against — LoadCoach never applies a caller's schema
([ADR-0041](docs/adr/0041-caller-schemas-do-not-travel-through-a-router.md)), so validation and its
bounded corrective retry are PromptCadence's, exactly as IdeaPress does it. Lifecycle §4.1 gives
the shape and the five rules, each enforced by validation rather than convention:

* `depends_on` forms a DAG; a cycle is `PLAN_INVALID`.
* A step's declared classification may not exceed the trajectory's — **a plan cannot launder
  confidential data into an `internal` step**, and this is the rule most worth a nasty test.
* Declared tools exist in the trajectory's allowlist; declared tiers are configured.
* An empty plan is invalid — *emptiness cannot pass a gate* (the IdeaPress M7 lesson, and the
  reason [ADR-0042](docs/adr/0042-a-check-may-not-restate-its-requirement.md) exists).
* The plan is persisted **verbatim** alongside its validated form; `expected_turns` and the step
  descriptions are advisory, while tools, tier and classification are declarations that approval
  turns into intents.

The plan schema is also the phase's named risk — "too strict ⇒ constant retries" — and the
mitigation is G1's validation against real local-model output. You cannot test that here; what you
can do is make the failure *legible*: a validation error that names which step and which field
failed is what makes P7's corrective retry work, and a bare "does not match schema" is what makes
it loop.

### 5. `domain/intent.py` — the module this row exists for

`ExecutionIntent` exactly as lifecycle §4.3 fields it, including `revision`/`supersedes`,
`minted_by` and `approval_request_id`. Four rules to implement rather than intend:

* **Immutable, and superseded rather than edited.** A redline resolves *at minting* (the intent
  carries the substituted tier; the plan keeps the original). A scoped re-approval mints revision
  n+1 and the superseded revision is retained. Make the type structurally incapable of being
  edited, and make supersession the only way a new revision comes into existence.
* **Universal.** Three minting paths — from an approved plan step, from `TierPolicy`'s defaults for
  the bypass loop (`step_id` is the synthetic `"loop"`), and by supersession — and **no fourth**.
  Contract 1 is that there is no code path executing a turn without an intent; the structural half
  of that promise is that a turn cannot be constructed without one. Design that, do not merely
  intend it, and write the test that fails if a later phase adds a path around it (C1's "the
  invariants are the only path" guard and C2's fixed-order guard are the same problem solved twice
  — read how both were made to bite before you invent a third way).
* **Gates evaluate against the most permissive tier in the set.** `approved_tier` +
  `fallback_tiers` are evaluated at minting against the most permissive member, "so a pre-approved
  fallback cannot smuggle egress past a hybrid gate". This is a one-line rule and a whole class of
  bypass; it needs its own test with a local primary and a remote fallback.
* **Minting emits `intent.minted`.** The event body is a Phase 2 shape even though the write is
  P3's (ADR-0044).

Goldens for all four minting cases (plan, redline, bypass default, superseding revision), byte-
identical on re-derivation.

### 6. `domain/deviation.py` — the closed taxonomy

`compare(turn_facts, intent) → deviations`, pure, identical in both paths — "no
'plan-declared vs default-policy' branching", which is the collapse ADR-0056 bought. The six
categories, two severities and the two `reapproval_scope` settings are tabulated in lifecycle §5;
transcribe the table exactly, including the `undeclared_tool` row's two-way split (outside the
intent is a drift the app handles; outside the **trajectory allowlist** is refused outright,
recorded, and never re-approvable — the second is ToolYard's `not_allowlisted`, and C2's handoff
records how that refusal is shaped).

Two things the table implies and does not spell out: a `violation` is an unconditional halt and is
never re-approvable, so nothing in the disposition logic may make one conditional; and
**trajectory-level ceiling crossings are not deviations** — they are the budget machinery's own
halt/pause at F1. If a ceiling crossing can reach `compare()`, the taxonomy is not closed.

Parametrize the matrix over the enums so it is exhaustive **by construction** — a new category with
no disposition row must fail the suite, not slip through as an untested cell.

### 7. `domain/policy.py` — approval evaluation without the ledger

`PlanApprover`'s auto verdicts as a pure function over tier policy, egress policy and **ledger
headroom**, versioned by `approval_policy_version` (which is persisted on every trajectory, so
changing the policy must change the version — decide how that is enforced, since "remembered to
bump it" is not an enforcement).

`loadledger` is not a dependency until P5. Take the headroom as an input shape you own — a protocol
or a small frozen value object with the fields a verdict needs — and let F1 adapt
`CeilingVerdict` to it. Read LoadLedger's `CeilingVerdict` (in `py/LoadLedger/src/loadledger/types.py`)
before designing that shape, because it already carries the honesty counts (`unpriced_debit_count`,
`untotalled_debit_count`, `unmetered_debit_count`) that an approval decision must not throw away:
approving a step against a *floor* while believing it a total is exactly the failure ADR-0069
exists to prevent. Human approval modes arrive at P7; `auto` is what you implement, with the mode
enum and the gate definitions (`gate_egress_at`, `gate_step_cost`) present so P7 fills in behaviour
rather than inventing vocabulary.

### 8. `domain/trajectory.py` — the state machine

Every row of lifecycle §8.2 an explicit function; every transition not in the table refused; the
guard column implemented, not summarized. Note the three rows added on 2026-09-02 (docs commit
`dd60b6e`): **T15–T17 and the `awaiting_window` state** — a per-day ceiling under the `window`
policy parks the trajectory (persisting the state it parked from, the next UTC-day edge and the
days waited) instead of halting, resumes at the day roll, and halts at `window_wait_max_days`.
That state holds no lease, and its clock is a persisted value rather than process state (§8.3).

Tests: every §8.2 row; every illegal transition refused; and a **property test that terminal states
have no exits** — `completed`, `rejected`, `halted`, `failed`, `cancelled` are absorbing, and the
property must be over the enum rather than over five hand-written cases, so a sixth terminal state
added later is covered the day it appears.

### 9. Events and payload shapes

The `observability` module's event types and bodies per spec §17 and the "Event(s) in the same
write" column of §8.2 — `trajectory.created`, `.claimed`, `.completed`, `.halted`, `.failed`,
`.cancelled`, `.resumed`, `.recovered`, `plan.approved`, `plan.rejected`, `approval.requested`,
`.granted`, `.denied`, `intent.minted`, `deviation.detected`, `budget.window_wait`. Bodies are
value objects here; the write is P3's. One rule worth stating in the module docstring: an event
body carries ids, categories and numbers — never prompt text, never model output.

### 10. Tests and documentation

The plan's list is the floor: plan-validation goldens (valid, cyclic, laundering, empty, unknown
tool/tier); intent-minting goldens for all four paths, immutability asserted, the
most-permissive-fallback gate; the exhaustive deviation matrix; tier admission and escalation
ordering with snapshot immutability; the full state-machine table plus the terminal-state property.
Add the acceptance criteria as tests rather than as claims: criterion 1 is `lint-imports` (already
contracted — assert that `domain` imports no framework *and* that the contract exists), criterion 2
is the determinism goldens.

Documentation: `CHANGELOG.md` under `## [Unreleased]`; `README.md`'s status line moves to Phase 2;
the three mirrored documents re-verified with `cmp` after any amendment you make in `docs/`.

### 11. Gate and commit

The full gate green with the interpreter named. Commits on `main`, one per logical group. No tag,
no publish, no push.

## Before you finish — three closing duties

1. **Write `docs/history/C4_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands; the domain surface as built against lifecycle §§3–8, naming every deviation from
   the documents and the amendment you propose for each; **the five settled shapes from §1** as
   decisions D2, E4, F1 and G1 must not relitigate; **how "no turn without an intent" is enforced
   structurally and how it is proven to bite**; the `turn_facts` definition and why the taxonomy is
   closed given it; what a trajectory's tier snapshot contains; the migration decision from §1(c)
   and exactly what D2 inherits (tables present or tables owed); the two pin discrepancies from the
   preconditions; the commits made; and **"Before the next session"** — at minimum: push `main`,
   confirm CI green (including the `db-matrix` job's collection gap noted in B4_HANDOFF §1), and
   anything the operator must decide. Add a short section addressed **to D2** — it is a Fable
   session building the LoadCoach client, the bypass loop and the fake LoadCoach against your
   types; tell it what is settled, what is deliberately absent, and which seams it may extend
   versus which it may not touch. **Never overwrite an existing root file** — the workspace root is
   not a git repository. If `docs/history/C4_HANDOFF.md` exists, write `C4_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what was built, what the gate said, the five shapes you settled,
   and what is waiting on the operator. A few sentences.
3. **Prepare the commits.** Everything committed on `main`, working tree clean, nothing pushed,
   nothing tagged. Say exactly what is waiting for the operator.

## Constraints and stop rules

* **Nothing talks HTTP, and nothing executes.** No LoadCoach client, no `httpx` import, no fake
  LoadCoach, no worker, no lease, no loop — all of that is D2. `respx` stays unused this phase.
* **No provider access of any kind.** `modelrack` and `sweatmeter` are not dependencies, at module
  level, under `TYPE_CHECKING`, or in a test helper
  ([ADR-0045](docs/adr/0045-promptcadence-reaches-models-only-through-loadcoach.md) rule 2), and
  `.importlinter` asserts it. **You never weaken `.importlinter`** to make an import work — the
  layering contradiction in §1(b) is resolved by moving code, not by editing the contract.
* **No parallel classification vocabulary.** `baseaicore.DataClassification` and nothing else — no
  levels of your own, no aliases, no string comparisons (ADR-0046).
* **A model never decides control flow.** Nothing in this phase reads model output; when P3 does, a
  step completes only on a declared `finish_reason` or a schema-validated result. Do not build a
  type that makes "the model said it was done" representable as success.
* **No prompt text in the domain, ever.** A prompt is named by `prompt_id`, `version` and `sha256`
  ([ADR-0012](docs/adr/0012-prompt-storage-format.md), spec §9).
* **No human-approval behaviour** (P7) and **no budget arithmetic** (F1). The vocabulary is born
  here; the behaviour is not.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` in this repo at the start and
  end of the session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/C4_HANDOFF.md`.
