# Kickoff — F2: PromptCadence Phase 6 — Egress, verification and deviation

**Row:** F2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · high**, as scheduled. Fail-closed semantics and the violation path —
adversarial-adjacent, and on §3.3's never-economize list.
**Repositories:** `/home/jpk/ai/suite/PromptCadence`, then `/home/jpk/ai/suite/docs`.
**Ships:** nothing to PyPI. Changelog under `## [Unreleased]`, no version bump, no tag —
`promptcadence` first publishes at **G1** (0.9.0b0, the M11 beta).
**Overnight:** **no.** This row is on the security-adjacent side of §2.12's caveat — its failures
are silent and it is won by review. Run it daytime, reviewed.
**Runs after:** E3 (Commissioner Phase 2) and F1 (Phase 5). **And after E5's pin sweep — see §0.1,
which is a hard blocker, not a preference.**
**Not in this session:** planning, approval modes, intent minting by a planner, plan-declared
deviation rows (all **G1**); compaction (**P8**).

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Do not re-derive these; do **confirm** the ones marked, and re-check §0.1 first because it may have
changed.

* **`commissioner 0.1.0` is on PyPI** and `py/Commissioner` `main` is clean at `72b789b`, tagged
  `v0.1.0`. Its public surface: `EgressPolicy`, `OrderedClassificationPolicy`, `EgressRequest`,
  `EgressTarget`, `EgressDecision`, `Verdict`, `EgressLedger`, `InMemoryEgressLedger`,
  `CommissionerError`, `StoreFailure`, `UnsupportedDialect`. `commissioner.sql` carries the
  mountable tables. Read the real signatures from `py/Commissioner/src/commissioner/types.py`,
  `policy.py` and `ledger.py`.
* **ADR-0054 (= D-10) is the shape of this integration and it is easy to get backwards:**
  *"Commissioner **renders and records** an egress verdict; **enforcing it is the caller's**."*
  The package does not block anything. PromptCadence asks, records, and then **acts** on the
  verdict. A design where Commissioner is expected to prevent a call is wrong at the first line.
* **PromptCadence `main` was at `5247a83`** when this prompt was written (P1–P4; P5 lands at F1),
  clean and CI-green. **Confirm** the current head and `git status -sb` at the start and the end.
* **`http_fetch` is registered-but-withheld today**, not disabled. E4 shipped it that way
  deliberately rather than editing spec §12's shipped `[tools] enabled`: `promptcadence tools list`
  prints `· http_fetch  withheld: egress_governance_deferred_to_p6`. **This row is the `p6` that
  string names.** Enabling it means registering it *and* removing the withheld reason — grep for
  `egress_governance_deferred_to_p6` and make sure no stale copy survives in code, tests, `doctor`
  output or docs.
* **Interpreter:** PromptCadence's venv is **Python 3.13.15**; there is **no python3.12** on this
  host. Name it and every exact invocation (M5C-13).
* **Push auth is configured** (2026-09-04): `credential."https://github.com".helper =
  !/usr/bin/gh auth git-credential`. **Probe with `GIT_TERMINAL_PROMPT=0 git push --dry-run origin
  main`, never `git ls-remote origin`** — these repos are public and `ls-remote` succeeds
  anonymously on a repo you cannot push to.

## 0.1 The blocking dependency the row does not mention — check this before anything else

`commissioner 0.1.0` pins **`setspec>=0.5,<0.6`** (`py/Commissioner/pyproject.toml`, and its
`docs/packages/commissioner/spec.md` §56 states the same range deliberately — it owns the Python
form of `governance.egress_decision` 1.0, ADR-0051 §4).

PromptCadence pinned **`setspec>=0.4,<0.5`** when this prompt was written. **Those two ranges are
mutually unsatisfiable — `pip install` cannot resolve PromptCadence with Commissioner today.**

The fix is row **E5**'s sweep, which widens PromptCadence to `setspec>=0.5,<0.7`. As of 2026-09-04
`mirrorwall 0.2.2` (the release that unblocks it) **is published**, but the sweep itself may not
have run yet. **First action of this session:**

```bash
grep -n "setspec" /home/jpk/ai/suite/PromptCadence/pyproject.toml
```

* If it still reads `>=0.4,<0.5`: **stop.** E5 Gate B owns that edit — doing it here duplicates a
  scheduled row and skips its lock/gate discipline. Write a two-paragraph handoff saying F2 is
  blocked on E5 §6 B1, and stop. Do **not** work around it with a path install, an editable
  install, or a `--no-deps` install of Commissioner. That would prove the opposite of what the
  dependency exists to prove.
* If it reads `>=0.5,<0.7` (or wider): proceed, and read §0.2.

## 0.2 The consequence nobody has written down yet — record your finding either way

Commissioner's `<0.6` cap means that **adding `commissioner` to PromptCadence pins the resolved
`setspec` to 0.5.x**, even though PromptCadence's own range admits 0.6 and `setspec 0.6.0` is
published. This is the same shape as the `mirrorwall<0.5` cap that E5 just spent a whole row
removing — a capability package's narrow cap holding an application back.

It costs nothing **today**: nothing in PromptCadence needs `setspec` 0.6 (`capability.evidence` 1.1
is LoadCoach's, at H4, and PromptCadence never reads evidence). So:

**Recommendation: proceed on `setspec` 0.5.x and do not widen Commissioner in this row.** But
**prove and record the resolution** — after installing, run

```bash
pip show setspec commissioner baseaicore | grep -E "^(Name|Version)"
```

and paste it into the handoff. If it resolves to anything other than `setspec` 0.5.x, something
about §0.1 has changed and you should understand why before writing code. And **record the cap as a
future row** in the handoff: "commissioner's `setspec<0.6` will need widening before PromptCadence
can adopt any 0.6 payload" — so that whoever hits it next finds it written down rather than
rediscovering it the way E5 rediscovered mirrorwall's.

## 0.3 The two design facts that decide whether this row is right

Read both before planning; they are the ones a passing test suite will not protect you from.

**1. Verification cannot be derived from `ProviderKind` (spec §11 contract 4).** The contract is
explicit: *"`ProviderKind` names a runtime, and `openai_compatible` covers both a local llama.cpp
server and a paid remote endpoint, so deriving egress from the kind would be exactly the assumption
this contract forbids."* The egress class is resolved **at the HTTP boundary** — while LoadCoach
serves one configured provider, verifying that the response's provider *is* the configured one is
the verification. **Absence is a violation, not a pass.** The development plan's known-risk note
says the same thing: *"The response names its execution subject by contract; absence is treated as
a violation, not a pass — fail closed, recorded."* If you find yourself writing
`if kind == "ollama": local`, stop.

**2. The deviation taxonomy is closed by construction, and `TurnFacts` is what closes it
(lifecycle §5).** There is exactly one category per `ExecutionIntent` field it can contradict, plus
one for a promise contradicted after the fact. That closure holds **only if `TurnFacts` can express
no fact that no intent field covers** — which is why lifecycle §5 says it carries **no
trajectory-level ceiling, balance or headroom**: a ceiling crossing is the budget machinery's halt
or park (§6, your F1 work), and a fact of that kind reaching `compare()` would either be ignored or
demand a seventh category. **Do not add a field to `TurnFacts` to make a test pass.** Adding one is
a governance-dimension change and needs an ADR.

Two severities exist and are **not configurable**: `violation` (executed reality contradicted an
already-made promise — unconditional halt, never re-approvable, recorded as a `VIOLATION`
`EgressDecision` where egress-relevant) and `drift` (disposition follows `reapproval_scope`).

## 0.4 What "against the bypass default intent" means, and why it matters

The plan says `DeviationHandler` is wired end to end **against the bypass default intent**. Read
that precisely: the full lifecycle §5 category set applies **unchanged**, because the intent is the
comparison source in **both** modes — **P7 (G1) only changes who mints it.** So this row builds the
whole comparison machinery against the default intent minted from `TierPolicy`, and G1 later swaps
in a planner-minted one without touching `compare()`.

That is also why acceptance criterion 1 for this phase reads *"Every turn in every prior phase's
journeys now carries an egress decision — the invariance check runs from here to 1.0."* Contract 1's
governance-invariance diff is **G1's** test to write, but this row is where the invariant becomes
true. Do not weaken it by making egress conditional on a mode.

---

## 1. Setup

```bash
cd /home/jpk/ai/suite/PromptCadence && source .venv/bin/activate && pip install -e ".[dev]"
pip show setspec commissioner baseaicore | grep -E "^(Name|Version)"   # §0.2 — paste into the handoff
```

Use the session scratchpad for every scratch database, config file and log — **never** the
repository, never `/tmp` directly, never the workspace root.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory, never the workspace root. Nothing at the root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` under `## [Unreleased]`,
  **one Conventional Commit per repository**, committed at each gate boundary.
* `pytest-randomly` is on; a seed-only failure is a real bug.
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names, keyword-only optionals and booleans, frozen slotted value objects, pydantic wire
  models, SQLAlchemy models never leaving the repository layer, `mypy --strict`, line length 100.
* `web → cli → services → domain`; `domain` imports no framework. Handlers call one service method
  and render. Never weaken `.importlinter` to make an import work.
* Async at the HTTP edge only (ADR-0003); SSE for streaming, never WebSockets (ADR-0004);
  server-rendered HTML, no SPA (ADR-0020).
* **Never `git add -A`.** Stage named paths.
* Any workspace `docs/` edit is mirrored byte-identically and **`cmp`-proved**.

## 3. Reading list, in this order

1. `docs/apps/promptcadence/development-plan.md` **Phase 6** — the work list, the test list, the
   acceptance criterion, the known risk, the deferral. It is this row's specification.
2. `docs/apps/promptcadence/lifecycle.md` **§5** in full — `TurnFacts`, the closure argument, the
   two severities, and the whole category table with its `on_tier_or_classification_change` and
   `any_deviation` columns.
3. `docs/apps/promptcadence/spec.md` **§11 contracts 3 and 4** (egress; verification), **§13** (the
   error vocabulary — `EGRESS_DENIED`, `UNPRICED_EGRESS_REFUSED`, `DEVIATION_HALTED`,
   `TIER_UNAVAILABLE`, and the LoadCoach-code mapping table), **§20 criteria 4 and 5**.
4. `docs/packages/commissioner/spec.md` — the whole thing, especially §56 (the `setspec` range) and
   the acceptance check at §261.
5. **ADR-0054** (= D-10, Commissioner records, the caller enforces), **ADR-0048** (= D-4, the bypass
   removes planning, never governance), **ADR-0056** (= D-12, one `ExecutionIntent` per turn),
   **ADR-0046** (data classification is ordered and defaults closed), **ADR-0043** (grounding is
   verified, not assumed — the principle contract 4 applies).
6. `docs/history/E3_HANDOFF.md` — Commissioner Phase 2 as built, and anything it flagged for its first consumer.
7. `docs/history/F1_HANDOFF.md` — the ledger mount and migration shape you are about to copy for
   `commissioner.sql`, and the turn path you are about to instrument.

---

## 4. The shape of the work

Five gates in order. Egress evaluation comes before verification because verification's violation
path *records an `EgressDecision`*, and deviations come last because they compare against facts the
first two gates establish.

## 5. Gate A — mount `commissioner.sql`

Add the `commissioner` pin (with whatever extra its SQL store needs — check its `pyproject.toml`
rather than assuming `[sql]`), mount its tables, and write the next Alembic migration.

* **Copy F1's mount + migration shape exactly.** F1 established it as the first-instance example
  (model-assignment §3.1) precisely so this one is transcription. If you find yourself designing it
  again, re-read `docs/history/F1_HANDOFF.md`.
* Keep the package's documented table prefix; a change is a table rename, not a config change
  (ADR-0050).
* `alembic upgrade head` from empty produces the mounted schema; `downgrade` is clean.
* `lint-imports` stays green: `commissioner` is a capability package and imports no application.

## 6. Gate B — evaluate and record every egress decision

Evaluate **before every turn** (against the tier target) and **before every `NETWORK` tool call**.
Record **every** verdict — approvals as fully as denials (contract 3: *"a declined call is as
auditable as an approved one"*).

* A denial ends the turn with a structured refusal per spec §13 (`EGRESS_DENIED`), not an exception
  escaping to the caller as `INTERNAL_ERROR`.
* Classification ordering comes from `OrderedClassificationPolicy` and ADR-0046 — **defaults
  closed**. A classification you cannot resolve is not permissive.
* Spec §20 **#4**: a trajectory declared `confidential` can **never** reach a remote tier — refused
  **before any HTTP request leaves**, and the refusal is a queryable `EgressDecision`. Assert that
  no request left, not merely that the result was a refusal: use the injected HTTP client and prove
  it was never called.
* Spec §20 **#5**: a remote tier with no pricing record refuses with `UNPRICED_EGRESS_REFUSED`
  before any call. Unpriced egress is refused, not free (ADR-0016/ADR-0030).

## 7. Gate C — post-turn verification (contract 4, the fail-closed one)

Check every LoadCoach response's execution subject against the tier that promised it.

* Mismatch → `VIOLATION` decision **and halt**.
* **Missing subject metadata → violation, not pass.** Test that case explicitly; it is the known
  risk the plan names and the one a happy-path suite will never reach.
* **Do not derive the egress class from `ProviderKind`** (§0.3). Resolve it the way contract 4
  says, and put the reason in the docstring so the next reader cannot undo it innocently.
* The plan's named test: the fake plays a remote provider answering a **local** tier → violation +
  halt.

## 8. Gate D — deviations, end to end against the bypass default intent

Wire `DeviationHandler` with the full lifecycle §5 category set: `tier_violation`,
`tier_escalation`, `classification_exceeded`, `undeclared_tool`, and the rest of §5's table.

* `compare(turn_facts, intent) → deviations` stays **pure**. `TurnFacts` is built by the executor
  from the LoadCoach response and the ledger's per-step totals — **never by the handler**.
* Honour the split in `undeclared_tool`: a tool outside the *trajectory allowlist* is refused
  outright with a structured `ToolResult` and recorded, **never re-approvable** — the allowlist is
  the caller's, not the model's. A tool inside the allowlist but outside the intent follows
  `reapproval_scope`.
* Deviation events carry their category; halt thresholds are honoured; `DEVIATION_HALTED` is the
  surfaced code.
* **Golden test: the deviation matrix, bypass rows** — the plan asks for it by name.
* Severities are not configurable (§0.3).

## 9. Gate E — surfaces, remote tiers, then docs

* **Enable `http_fetch`, egress-checked** — and clear the `egress_governance_deferred_to_p6`
  withheld reason everywhere it appears (§0). The plan's named test: a fetch to a non-allowlisted
  host is refused **and recorded**.
* `GET /egress-decisions`, `promptcadence egress list`.
* **Remote tiers become configurable now** — and refuse with `TIER_UNAVAILABLE /
  loadcoach_has_no_remote_provider` or `UNPRICED_EGRESS_REFUSED` as documented. Those refusals are
  themselves tested behaviour, not incidental. (E4 recorded that the remote tiers are **not** in the
  shipped active defaults; configurable is not the same as shipped-on — keep it that way.)
* Then `/home/jpk/ai/suite/docs`, one commit: mark the **F2 row** done in
  `roadmap/outstanding-work.md` §1 (`**Done 2026-09-0X** (`docs/history/F2_HANDOFF.md`; commits …)`), record
  §0.2's Commissioner cap as a named future item, and mirror + `cmp`-prove anything PromptCadence
  copies.

---

## 10. Exit conditions — all of these, demonstrably

1. Spec §20 **#4** verbatim: a `confidential` trajectory cannot reach a remote tier; **no HTTP
   request leaves**, proved against the injected client; the refusal is a queryable
   `EgressDecision`.
2. Spec §20 **#5** verbatim: an unpriced remote tier refuses with `UNPRICED_EGRESS_REFUSED` before
   any call.
3. The fake playing a remote provider on a local tier → violation + halt, recorded as a `VIOLATION`
   `EgressDecision`.
4. A response with **absent** subject metadata is treated as a violation.
5. A fetch to a non-allowlisted host is refused and recorded; `http_fetch` is enabled and no
   `egress_governance_deferred_to_p6` string survives anywhere.
6. The bypass-rows deviation matrix golden passes; a tool outside the trajectory allowlist is
   refused outright and is not re-approvable.
7. **Acceptance criterion 1: every turn in every prior phase's journeys now carries an egress
   decision.** Demonstrate it over P4's and P5's existing journeys, not only over new tests.
8. `pip show setspec commissioner` output pasted, resolving as §0.2 predicts.
9. Full gate green; the suite passes with no LoadCoach, no GPU and no network (§20 #10).
10. PromptCadence clean and pushed, CI green; docs clean; mirrors `cmp`-identical.

## 11. Closing duties

1. Full gate, interpreter and exact invocation named (M5C-13).
2. **`docs/history/F2_HANDOFF.md` at the workspace root**, house shape: gate results; the resolved
   `setspec`/`commissioner` versions (§0.2) **and the cap recorded as a future row**; how the egress
   class is resolved at the HTTP boundary and why it is not `ProviderKind` (so nobody "simplifies"
   it later); the deviation categories implemented and any you deliberately left to G1; what G1
   inherits (the intent is already the comparison source in both modes — G1 changes only who mints
   it, and owns contract 1's diff test); anything this prompt said that turned out not to be true.
3. Push and confirm CI green. **This row is reviewed, not overnight** — leave the diff in a state a
   reviewer can read: one commit per gate, each with a message that says what it made true.
4. Record any **model deviation** from the scheduled Opus 5 · high for
   [model-assignment §3.5](docs/roadmap/model-assignment.md).

## 12. Stop rules

* **If PromptCadence still pins `setspec>=0.4,<0.5`, stop** (§0.1). Do not do E5's edit here, and do
  not path-install, editable-install or `--no-deps`-install Commissioner to get around it.
* **Do not widen Commissioner's `setspec` pin.** It is spec'd at §56 and nothing here needs 0.6.
  Record it as a future row instead.
* **Do not make Commissioner enforce anything** (ADR-0054). It renders and records; PromptCadence
  acts.
* **Do not derive the egress class from `ProviderKind`**, and do not treat missing subject metadata
  as a pass. Both are contract-4 failures that a green suite will not catch.
* **Do not add a field to `TurnFacts`** to make a comparison work (§0.3). That is a new governance
  dimension and needs an ADR.
* **Do not make egress conditional on planning mode** (ADR-0048 / D-4: the bypass removes planning,
  never governance). This is the design's load-bearing wall.
* **Do not build the planner, approval modes, or contract 1's governance-invariance diff** — all
  G1's. Do not implement plan-declared deviation rows (deferred to P7).
* Do not bump the version, tag, or publish.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a boundary.

## 13. If you finish with capacity left

Do **not** start G1. Read-only, in priority order: (a) a **G1 readiness note** — exactly what
contract 1's governance-invariance diff must compare, given that this row made every turn carry an
egress decision in both modes, and which record rows are expected to differ (`plan`,
`plan_approvals`, and nothing else); (b) write up the Commissioner `setspec<0.6` cap as a
draft row for `roadmap/outstanding-work.md`, with the argument E5 used for mirrorwall; (c) note
which lifecycle §5 categories have no test yet and why.
