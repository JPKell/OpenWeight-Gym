# C4 — PromptCadence Phase 2 (domain core) — handoff

**Row:** C4 of `docs/roadmap/outstanding-work.md` §1. **Model:** Opus 5 · xhigh.
**Repository:** `/home/jpk/ai/suite/PromptCadence`, branch `main`, seven commits on top of
`7281432`, **not pushed**. **Docs:** one commit in `/home/jpk/ai/suite/docs`, **not pushed**.
**Date:** 2026-09-02 → 2026-09-03.

Phase 2's goal in the plan's own words — *"every governance decision that needs no I/O is a pure,
golden-tested function"* — is met. Nothing added this phase talks HTTP, executes, or imports a
framework into `domain`.

---

## 1. Gate results

Run from `/home/jpk/ai/suite/PromptCadence`, interpreter `PromptCadence/.venv/bin/python`,
**Python 3.13.15**, pytest **9.1.1** (upgraded this session; see §7). There is no `python3.12` on
this machine.

```bash
cd /home/jpk/ai/suite/PromptCadence
.venv/bin/ruff format --check .        # 55 files already formatted
.venv/bin/ruff check .                 # All checks passed!
.venv/bin/mypy src tests               # Success: no issues found in 52 source files
.venv/bin/lint-imports                 # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                       # 535 passed, 2 skipped, 2 warnings
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                       # Total coverage: 96.82%  (floor 85%)
```

The two skips are the `integration`-marked PostgreSQL tests, which the `db-matrix` CI job selects
with `-m integration`. The two warnings are pre-existing Starlette/anyio deprecations from Phase 1.

**Acceptance criteria.** Both are tests, not claims.
1. *Domain modules import no framework* — `tests/unit/test_domain_purity.py`, which asserts both
   that nothing imports a framework (read from the source, so a `TYPE_CHECKING` import is caught
   too) **and that `.importlinter`'s contracts still exist and still forbid what they must**. A
   future session cannot make an import work by weakening the contract and leaving a green suite.
2. *Determinism goldens for plan validation and approval evaluation* —
   `tests/golden/{plan_validation,approval_verdicts,intent_minting,deviation_matrix}.json`, each
   re-derived and compared byte for byte.

---

## 2. The five settled shapes — D2, E4, F1 and G1 must not relitigate these

### (a) `turn_facts` — the other half of the closed taxonomy

`promptcadence.domain.deviation.TurnFacts`, a frozen slots dataclass. **Built by P3** from a
LoadCoach response plus the ledger's per-step running totals; nothing in it is HTTP-shaped, which
is why the whole deviation suite runs with no fake LoadCoach.

```text
turn_id
executed_tier            str | None    None iff the intent's tiers could not serve
subject                  ExecutionSubject | None    model id, provider kind, VERIFIED egress class
tier_service_failure     no_eligible_model | tier_unavailable; set iff executed_tier is None
requested_tools          tuple[str, ...]
trajectory_allowlist     frozenset[str]  — the caller's; splits `undeclared_tool` two ways
observed_classification  DataClassification
turns_used               int, counting this turn
step_tokens_spent        int
step_money_spent         Money | None   (None for unpriced local work — never Money.zero())
step_money_is_floor      bool           (ADR-0069)
finish_declared          bool           (a declared finish_reason, never the text saying so)
```

**Why the taxonomy is closed, given it.** Closure has two halves and the documents only stated
one. The stated half: one deviation category per intent field a turn can contradict, plus one for
a promise contradicted after the fact. The unstated half: `compare()` must be **unable to see a
fact no intent field covers**. Both halves are now mechanical:

* `intent.GOVERNED_INTENT_FIELDS | intent.RECORD_INTENT_FIELDS` must partition
  `ExecutionIntent`'s field list — so adding a field forces a decision about which bucket it is in,
  and a governed one needs a category, a disposition row and (ADR-0056's revisit trigger) an ADR.
* `deviation.CATEGORY_INTENT_FIELDS` must name real `ExecutionIntent` fields and must cover
  `GOVERNED_INTENT_FIELDS` **exactly**.
* `TurnFacts`' field list is asserted, with an explicit denylist for ceiling-shaped names.

**`TurnFacts` carries no trajectory-level ceiling, balance or headroom, and must not gain one.**
A trajectory, per-day or per-project ceiling crossing is the budget machinery's halt or park
(lifecycle §6), not a deviation. F1: do not pass a `CeilingVerdict` into `compare()`.

### (b) Where `SqlThreadStore` lives — **`infrastructure/threads.py`**

The development plan said `domain/threads.py`; `.importlinter`'s `domain-purity` contract forbids
`sqlalchemy` inside `promptcadence.domain`, and workspace `CLAUDE.md` states the same rule. The
contract wins; the code moved. **The plan is amended in place** (both the workspace copy and the
mirror) so D2 does not read the old sentence and put it back. `.importlinter` was not touched.

The `Protocol` and value objects are `domain/threads.py`; the SQLAlchemy implementation is
`infrastructure/threads.py`, and that is where the generic type meets the host's row.

### (c) Migration `0002` — **the tables are born here**

Recommended answer taken. `0002_governance_tables.py` creates `tier_snapshots`, `plans`,
`plan_steps`, `plan_approvals`, `approval_requests`, `execution_intents` and `deviations`, and adds
`turns.intent_id`, `turns.intent_revision`, `turns.cache_write_tokens`, `turns.cache_read_tokens`,
`trajectories.tier_snapshot_id` and `trajectories.approval_policy_version`.

**D2 inherits tables present, not tables owed.** Nothing about the turn row needs reshaping inside
the loop phase. Head is `0002`; parity against `models.py` passes on SQLite and (unrun here) is
the same check the `db-matrix` job runs on PostgreSQL.

Two tables are **not** in spec §10's list; both were defects, and §10 is amended:
`tier_snapshots` (content-addressed; see (below)) and `deviations` (§5 says every deviation is
"an event **and** a row"). `ledger_entries` and `egress_decisions` are still absent — they arrive
*mounted* at P5/P6 per ADR-0050, exactly as `models.py`'s docstring says.

`trajectories.tier_snapshot_id` deliberately carries **no foreign key**: a snapshot is shared by
every trajectory whose configuration matched, so a cascade from one trajectory must never reach it.

### (d) Four token classes on `turns` — **done, in the same migration**

`cache_write_tokens` and `cache_read_tokens` are nullable from birth beside the existing three.
`SqlThreadStore` stores an unreported class as `NULL` and reads it back as `UNSUPPORTED`, never
`0` — ADR-0016 through the round trip, and the reason LoadLedger at F1 can tell a floor from a
total. A round-trip test asserts all four survive.

### (e) `config.Tier` → the domain `Tier` — **a frozen dataclass, built at the boundary**

The domain takes `@dataclass(frozen=True, slots=True)` `promptcadence.domain.tiers.Tier`, built
from the pydantic `config.Tier` by `promptcadence.services.policy_assembly`. That is the only
place the two shapes meet, and nothing in `domain` imports `config`.

Why: it keeps a validation framework's semantics (coercion, aliasing, `model_config`) out of the
layer whose outputs are goldens, and it lets every later phase construct a `TierPolicy` in a test
without building a `Settings`. `tests/unit/test_domain_*.py` never touch configuration; the
`conftest.py` fixtures build tiers directly.

`policy_assembly` also builds `TierSnapshot`, `TierPolicy` and `ApprovalPolicy`.
`loadcoach_has_remote_provider` is a **parameter**, not a configuration value — it is a runtime
fact from LoadCoach's `/system/status`, which is D2's to supply.

---

## 3. How "no turn without an intent" is enforced structurally, and how it is proven to bite

**The mechanism, in three parts.**

1. `domain.threads.Turn` is generic over `provenance`, which is positional and has **no default**.
   A turn cannot be constructed without one. (This is also how the package-shape constraint and
   the governance constraint are satisfied by one decision rather than two.)
2. PromptCadence's provenance is `domain.intent.TurnProvenance`, which declares the intent as a
   `dataclasses.InitVar`. Constructing one **requires handing over an `ExecutionIntent` object**,
   and `intent_id`/`intent_revision` are derived from it rather than passed in — so they cannot
   name an envelope that does not exist. The InitVar is not a field: it is absent from `==`,
   `repr` and `as_canonical`, so a turn records a *reference*, never the envelope. Omitting it is
   a `TypeError`. This is the mechanism C1 used for CutCtx's plan invariants, chosen for the same
   reason: a validating factory can be bypassed, and a "proof of validation" carried on an object
   is forgeable in Python. Making it part of construction removes the bypass instead of policing it.
3. The state machine's T3 guard `default_intent_minted` refuses to enter `executing` without one,
   so the *transition* half matches the *construction* half.

**Proven to bite, five ways** (`tests/unit/test_domain_intent.py`):

* `test_a_turn_provenance_cannot_be_built_without_the_intent_it_ran_under` — a `TypeError`.
* `test_a_hurried_loop_that_skips_minting_cannot_produce_a_turn` — a `SkipsTheIntent` class
  written the way a hurried bypass loop would be. Every one of its own tests would pass. It cannot
  append a turn.
* `test_no_module_mints_an_intent_outside_domain_intent` — an AST walk over every module under
  `src/promptcadence/`, failing if any constructs an `ExecutionIntent` elsewhere. Direct
  construction is *safe* (validation is total) but skips `_mint`'s gate evaluation and egress
  resolution, so a fourth path would write an envelope whose gate verdict nobody computed.
  **D2, E4, F1 and G1 all add modules that mint; this test is what tells you there is one way in.**
* `test_rehydrate_is_called_only_from_infrastructure` — see below.
* `test_the_intent_is_an_initvar_and_leaves_no_trace_on_the_turn` — the InitVar does not leak.

**The one deliberate exception.** `TurnProvenance.rehydrate(...)` builds provenance from a
persisted row without an intent in hand. It is not a governing path: it produces provenance for a
turn that already exists, never for one about to run. Re-reading the intent to rebuild a committed
turn would report whichever revision is current rather than the one that governed it. The AST
guard confines it to `promptcadence.infrastructure`. `SqlThreadStore.turns()` also **refuses** a
row with no `(intent_id, revision)` rather than handing back a turn that never had an envelope.

**What this buys G1.** Contract 1's diff test (I11) compares a planned and a bypassed trajectory.
Both paths reach the identical `_mint`, the identical `compare()` and the identical turn
constructor; `compare()` has no mode branch at all, and
`test_compare_does_not_branch_on_how_the_intent_was_minted` asserts that on the outputs.

---

## 4. What a trajectory's tier snapshot contains

`domain.tiers.TierSnapshot` — `tiers` (every configured tier, **ordered by name**), `default_tier`,
`escalation_order`. Each `Tier` carries `name`, `task_profile`, `egress_class`,
`max_data_classification`, `context_budget_tokens`, `pricing_source`.

**Identity is a content address**: `snapshot_id == "sha256:" + sha256_of(as_canonical())`. Two
identical configurations produce one id, so the `tier_snapshots` table deduplicates naturally — a
stable deployment writes one row and every trajectory points at it, and the day an operator edits
a ceiling a second row appears with no migration and no coordination. The ordering-by-name
invariant is enforced in `__post_init__` precisely because the address depends on it.

**For F2 and I1:** read the snapshot, never today's configuration. The snapshot fixes *what the
tiers were*; `trajectories.approval_policy_version` fixes *what the approval rules were*. Together
they pin a decision; separately neither does.

Availability is deliberately **not** in the snapshot: `TierPolicy.loadcoach_has_remote_provider`
is a fact about right now, so LC-E1 landing makes every remote tier available without touching a
single stored snapshot.

---

## 5. The domain surface as built, against lifecycle §§3–8

| Module | What it owns |
|---|---|
| `domain/errors.py` | Spec §13's `ErrorCode` verbatim, plus the eight refusals this phase can raise. `IllegalTransitionError` is deliberately **not** a §13 code — an illegal transition is an internal defect, and services map it (a refused cancel → `TRAJECTORY_NOT_CANCELLABLE`). |
| `domain/events.py` | Spec §17's `EventType` and the `EventBody` protocol. Bodies live with the code that mints them. |
| `domain/threads.py` | `Thread`, `Turn[ProvenanceT]`, `ThreadSnapshot`, `ThreadStore` protocol, `build_snapshot`. Package-shaped; no update and no delete on the port. |
| `domain/tiers.py` | `EgressClass` (ordered, refuses comparison to a bare string), `Tier`, `TierAvailability`, `TierSnapshot`, `TierPolicy`, `most_permissive`. |
| `domain/trajectory.py` | `TrajectoryState`, `TrajectoryDeclaration`, `WindowWait`, `Transition`, `TRANSITIONS` (T1–T17), one function per row, and nine event bodies. |
| `domain/plan.py` | `PLAN_SCHEMA` + `plan.schema.json`, `PlanIssue`/`PlanIssueReason`, `PlanStep`, `Plan`, `validate_plan_document`, `ready_steps`, `topological_order`. |
| `domain/policy.py` | `ApprovalMode`, `ReapprovalScope`, `PartialPricing`, `EstimateSource`, `StepEstimate`, `BudgetHeadroom`, `ApprovalPolicy`, `GateVerdict`, `StepVerdict`, `PlanVerdict`, `evaluate_gates`, `requires_human_approval`, `evaluate_step`, `evaluate_plan`, five approval event bodies. |
| `domain/intent.py` | `ExecutionIntent`, `MintedBy`/`MintKind`, `TurnProvenance`, `GovernedTurn`, `mint_for_step`, `mint_bypass_default`, `supersede`, `IntentMinted`, and the two field-partition constants. |
| `domain/deviation.py` | `DeviationCategory`, `DeviationSeverity`, `Disposition`, `TierServiceFailure`, `ExecutionSubject`, `TurnFacts`, `Deviation`, `SEVERITIES`, `DISPOSITIONS`, `CATEGORY_INTENT_FIELDS`, `compare`, `disposition`, `DeviationDetected`. |

**Every deviation from the documents, and the amendment made for it.** All six are applied to the
authoritative `~/ai/suite/docs` copy and mirrored byte-identically (verified with `cmp`, not by
eye). Docs commit `b8d45b7`; repo mirror commit `2cc3c4b`.

1. **Lifecycle §5 never defined `turn_facts`.** Amended with the shape above and the closure
   argument's second half.
2. **Lifecycle §3 did not say whether the automatic policy grants fallback tiers.** It now says it
   does not. §3 already required explicit escalation; granting fallbacks up front would contradict
   that, pre-approve egress nobody asked for, and make the `tier_escalation` path dead code. A
   human approver (P7) and `supersede()` may grant them.
3. **Lifecycle §4.2 did not say how `approval_policy_version` is enforced.** It now says it is
   derived, never declared. See §6 below.
4. **Spec §10 omitted `tier_snapshots` and `deviations`.** Both added, with the no-foreign-key note.
5. **Spec §11 contract 4 said "verified" without saying how.** `ProviderKind` names a *runtime* —
   `openai_compatible` covers both a local llama.cpp server and a paid remote endpoint — so
   deriving egress from the kind would be exactly the assumption the contract forbids. Amended to
   say the class is resolved at the HTTP boundary, that verifying the response's provider *is* the
   single configured one is the verification today, and that **LC-E1 must carry the serving
   provider's identity on every response**. → this is an obligation on H2.
6. **Development plan Phase 2** placed `SqlThreadStore` in `domain/` and the event vocabulary in
   `observability`. Both corrected in place; migration `0002` and the tier-adapter seam added.

**Not amended, recorded here instead:** lifecycle §5's `undeclared_tool` row states its two-way
split in prose rather than in a disposition column. Implemented as a documented refinement in
`disposition()` (outside the trajectory allowlist → `REFUSED_NOT_REAPPROVABLE` under either
scope), with its own parametrized test. The table itself is transcribed cell-for-cell.

---

## 6. `approval_policy_version` — how "remembered to bump it" was replaced

`ApprovalPolicy.version` is `"sha256:" + sha256_of({"ruleset": APPROVAL_RULESET_DIGEST, "policy":
<the configured values>})`. Two halves, both automatic:

* **Configured values** — a changed gate, mode, timeout or scope changes the digest with no human
  action. Tested five ways in `test_the_version_changes_when_any_configured_value_changes`, and
  end-to-end from a TOML edit in `test_policy_assembly.py`.
* **The ruleset** — `APPROVAL_RULESET_DIGEST` in `policy.py` is the digest of `evaluate_plan`'s
  output over a fixed 216-case corpus (3 modes × 2 scopes × 3 gate levels × 6 headroom states × 2
  provider states) held in `tests/unit/test_domain_policy.py`. Change any rule and
  `test_the_ruleset_digest_pins_this_modules_decisions` fails **naming the new value**; the only
  way to make it pass is to edit the constant, and editing it changes every deployment's version.

The corpus deliberately excludes `approval_policy_version` from what it hashes, because the
version contains the digest — including it would make the digest depend on itself.

The committed golden `tests/golden/approval_verdicts.json` is six *named*, readable scenarios
rather than the whole corpus: the corpus is pinned by the digest, and a 354 KB golden nobody can
read in a diff is a golden nobody reviews.

---

## 7. The two pin discrepancies

**`pytest>=8,<9` → `pytest>=9.0.3,<10`. Fixed.** PYSEC-2026-1845 (vulnerable
`/tmp/pytest-of-{user}` handling through 9.0.2). Matches BaseAiCore, SetSpec, ModelRack,
LoadCoach, LoadLedger and CutCtx. Installed and the **full gate re-run green under pytest 9.1.1**;
no test needed changing. CI's `security` job runs `pip-audit` against the locks, so this was about
to fail there rather than "not being seen".

**`setspec>=0.4,<0.5`. Investigated, deliberately left, comment added — this one is not
PromptCadence's to fix.** Spec §5 requires `setspec >= 0.5` for `governance.egress_decision`, and
0.6.0 is tagged and on PyPI. Raising the pin makes the environment **unresolvable**:

```text
promptcadence 0.1.0 depends on setspec<0.7 and >=0.6
mirrorwall 0.2.1  depends on setspec<0.5 and >=0.4
```

`mirrorwall` is a hard dependency of every application. Verified, not assumed — the resolver
failure is reproducible with `pip install -e ".[dev]"`. The same `>=0.4,<0.5` pin is carried by
FreeWeight, IdeaPress and LoadCoach for the same reason; `py/Commissioner` already declares
`setspec>=0.5,<0.6`, which will hit the identical wall the moment it takes MirrorWall.

> **Operator decision needed.** The sequence is: MirrorWall widens its pin (to `>=0.4,<0.7` or
> `>=0.6,<0.7`) and releases 0.2.2, *then* every consumer moves. That is a MirrorWall row, not a
> PromptCadence one. Nothing in PromptCadence consumes setspec before P6, so this does not block
> D2/E4/F1 — but **D2 compiles locks**, and the lock it compiles will pin setspec 0.4.0.

---

## 8. Commits

**`/home/jpk/ai/suite/PromptCadence`** (on `main`, from `7281432`):

| Commit | Subject |
|---|---|
| `2cc3c4b` | `docs(promptcadence): close the four gaps Phase 2 could not build around` |
| `66e3959` | `feat(domain): vocabularies, tiers, threads and the T1-T17 state machine` |
| `5e47c1b` | `feat(domain): the plan schema, its five rules, and the automatic approval verdict` |
| `3d8904a` | `feat(domain): the ExecutionIntent, and the closed taxonomy it makes possible` |
| `5fbabb6` | `feat(db,services): migration 0002, the SQL thread store and the configuration adapter` |
| `1e925fa` | `chore: Phase 2 in the changelog and README, and the pytest security pin` |
| `752966f` | `fix(ci): the db-matrix job never connected to the server it started` |

**`/home/jpk/ai/suite/docs`**: `b8d45b7` `docs(promptcadence): define turn_facts, and close four
more Phase 2 gaps`.

Both trees are clean. Nothing pushed, nothing tagged.

**One incidental change worth naming.** A shell working directory persisted across a command and
`pip install -e ".[dev]"` ran once inside `/home/jpk/ai/suite/py/MirrorWall`, which upgraded
`mirrorwall` 0.2.0 → 0.2.1 **inside MirrorWall's own venv**. Venvs are gitignored and MirrorWall's
working tree is clean (`git status --short` empty, verified); the change corrected a stale
installed version rather than introducing one. No file in that repository was modified.

---

## 9. Before the next session

1. **Push `main`** from `/home/jpk/ai/suite/PromptCadence` (six commits) — a shared/visible action
   outside this session's authorization.
2. **Push `main`** from `/home/jpk/ai/suite/docs` (one commit).
3. **Confirm CI green** on the PromptCadence push. One job remains unexercised:
   * `security` (`pip-audit`) — and it audits **nothing**, which is a defect in its own right; see
     §11.
   `db-matrix` was fixed and verified this session — see §11.
4. **Decide the setspec sequence** (§7). Needs a MirrorWall release; no PromptCadence work.
5. **Still open from B4:** reserve the PyPI name `promptcadence` (unverified), and the tier-defaults
   judgment call in `docs/history/B4_HANDOFF.md` §3 (unchanged this session).

---

## 10. To D2 — Phase 3 (LoadCoach client, bypass loop, events, recovery)

You are building the httpx client, the fake LoadCoach, the bypass `LoopController` and recovery
against the types above. What follows is what is settled, what is deliberately absent, and which
seams you may extend.

**Settled — do not redesign.**

* **`ExecutionIntent` and its three minting paths.** T3 mints yours:
  `mint_bypass_default(intent_id=..., declaration=..., tier_policy=..., policy=..., minted_at=...)`,
  which takes everything from the declaration and tier policy exactly as ADR-0056 §2 lists. Pass
  `estimate=` when you have a money estimate for the cost gate; omitting it leaves the cost gate
  unfired rather than assuming a cost. `tier_override=` is the per-request tier.
* **A turn is `Turn[TurnProvenance]`**, and the provenance comes from
  `intent.provenance(trajectory_id=..., tier=...)`. There is no other way, and there is a test that
  fails if you add one. Note that `provenance()` deliberately does **not** validate the tier
  against the intent — a turn on a tier the intent never permitted is the `tier_violation` that
  must be *recorded*, and refusing to build it would delete the evidence.
* **`compare(turn_facts, intent)`** is the only comparison, and it has no mode branch. Build
  `TurnFacts` in the client/loop boundary, not in the handler.
* **The state machine.** Every T-row is a function whose guards are parameters. Call them; do not
  write `if state == ...` anywhere. `IllegalTransitionError` is internal — map it to a §13 code
  before it reaches an API envelope (a refused cancel is `TRAJECTORY_NOT_CANCELLABLE`).
* **Event bodies are shapes, not writes.** `IntentMinted.of(intent)`, `TrajectoryClaimed(...)`,
  etc. Your sink writes them in the same transaction as the transition (ADR-0044). An event body
  carries ids, categories and numbers — a test walks every body in the package and fails on a
  content-shaped field name, so do not add one.
* **`ErrorCode` is spec §13 verbatim**, asserted against the mirrored `spec.md`. Map every LoadCoach
  error onto a member; if one does not fit, that is a spec amendment, not a new string.

**Deliberately absent — yours to add.**

* **The egress class of an execution subject.** `ExecutionSubject.egress_class` is a *resolved*
  value, and resolving it is your boundary's job (spec §11 contract 4, now amended to say so).
  While LoadCoach serves one configured provider, verifying the response's provider *is* the
  configured one is the verification. Do not derive it from `ProviderKind` — `openai_compatible`
  is both a local llama.cpp server and a paid remote endpoint, and guessing there is the exact
  failure contract 4 exists to prevent. `ExecutionSubject.provider_name` is `None` until LC-E1.
* **An in-memory `ThreadStore`** for your tests. The port is a `Protocol`; satisfy it structurally,
  and do not import `SqlThreadStore` to do it.
* **`TierPolicy.loadcoach_has_remote_provider`** — supply it from `/system/status`. It is a
  parameter precisely so LC-E1 needs no stored-data change.
* **Everything about approval *behaviour*** (P7), tools (P4), money (P5) and egress (P6). The
  vocabulary for all four is born; the behaviour is not.

**Seams you may extend.**

* `TurnFacts` may gain a field **only** alongside an `ExecutionIntent` field, a deviation category,
  a disposition row and an ADR. The tests will tell you immediately; that is intended, and it is
  ADR-0056's revisit trigger rather than a nuisance.
* `EventType` members exist for every §17 type, including the ones no body has yet
  (`turn.started`, `tool.call.*`, `budget.debited`, `egress.evaluated`, `step.*`,
  `context.compacted`, `plan.drafted`). Add their bodies beside the code that mints them.
* `ThreadStore` may gain a read method. It may **not** gain an update or a delete: a transcript
  that can be rewritten cannot be the authoritative record contract 2 promises, and there is a
  test on the port's surface.

**Seams you may not touch.**

* `.importlinter` — five contracts, all kept. If an import will not work, move the code.
* The `InitVar` on `TurnProvenance`, and the AST guards in `test_domain_intent.py`. If minting from
  a new place is genuinely needed, add a **named function in `domain/intent.py`** that funnels
  through `_mint`; do not construct `ExecutionIntent` elsewhere and do not add a second
  `rehydrate`-style escape.
* `APPROVAL_RULESET_DIGEST` — change it only because you changed an approval rule and the test
  told you the new value. Never to make a failing test pass.
* The committed `plan.schema.json` — it is golden-tested against `PLAN_SCHEMA`; edit the module,
  regenerate the file, and expect the golden to move deliberately.

**One thing to know about the goldens.** Four golden files exist and each writes itself on first
run if absent. That is a convenience for authoring, not for repair: if a golden diff surprises
you, read it — `plan_validation.json` and `deviation_matrix.json` in particular are small enough
to check by eye, and a change in either means a governance decision moved.

---

## 11. B4's suggested check, run — and what it found

`docs/history/B4_HANDOFF.md` §1 asked whether the siblings' `db-matrix` jobs are green, on the theory that they
filter on an `integration` marker they never register, and so collect zero tests. **The premise
was inverted.** LoadCoach, IdeaPress, LoadLedger and WeightsDB had all already moved to selecting
by **path** (`pytest -m "not live and not performance" tests/integration`), and IdeaPress's job
carries a comment recording exactly that defect and its fix (M4 handoff HR2, defect 2).
PromptCadence was the only repository still on `-m integration`.

Worse, PromptCadence's job carried three further defects the siblings had also already fixed:

* Its service container started as `postgres`/`postgres`/`postgres`, while
  `weightsdb.testing.temporary_postgres` looks for
  `postgresql+psycopg://weightsdb:weightsdb@localhost:5432/weightsdb_test`.
* It passed the URL as `DATABASE_URL`, a variable `temporary_postgres` does not read — it reads
  `WEIGHTSDB_POSTGRES_URL` (verified in the installed source).
* With `WEIGHTSDB_REQUIRE_POSTGRES=1`, an unreachable server is `pytest.fail`, not a skip. So the
  job would have been **red on the first push**, while appearing to test PostgreSQL. Reproduced
  locally before the change: `2 failed, 535 deselected`.

**Fixed in `752966f`** and verified against a real `postgres:16` container configured exactly as
the corrected service is. Results, all against that server:

| Repository | Its own `db-matrix` selection | Result |
|---|---|---|
| PromptCadence (after the fix) | `tests/integration` | **19 passed** |
| WeightsDB | `tests/integration` | 57 passed, 1 skipped |
| LoadLedger | `tests/integration` | 71 passed |
| IdeaPress | `tests/integration` | 171 passed |
| LoadCoach | `tests/integration` | 232 passed |

So the four siblings are correctly wired and their jobs are green by construction; PromptCadence's
was the only broken one. **Migration `0002` is confirmed PostgreSQL-portable**, including
`test_check_parity_matches_on_postgresql` — the check that catches a `0002` portability defect, and
which as the job stood was running nowhere.

Two things this did *not* establish. `gh` is not installed on this machine, so the siblings' **actual**
CI history was not read — the claim above is that their jobs are correctly wired and their suites
pass, not that the last run on GitHub was green. And the `security` job is a separate, still-open
defect: `pip-audit` runs bare, with the project never installed and no `requirements/` locks to
audit, so it inspects an environment containing only pip-audit itself. LoadCoach, FreeWeight,
LoadLedger, ModelRack and CutCtx all audit `requirements/*.lock` with an explicit comment citing
Security Standards §11; PromptCadence and **IdeaPress** carry the bare form. PromptCadence has no
`requirements/` at all, so the natural home for the fix is **D2**, the row that compiles the locks.
IdeaPress already has a `release.lock` it never audits — a separate small row.

Local side effects, all venv-only and gitignored: `psycopg[binary]` installed into PromptCadence's
and LoadCoach's virtualenvs, and `mirrorwall` 0.2.0 → 0.2.1 in MirrorWall's (see §8). Every working
tree touched was verified clean afterwards, and the `postgres:16` container was removed.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
