# C1 handoff — CutCtx Phase 1

**Row:** C1 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-02.
**Repository:** `/home/jpk/ai/suite/py/CutCtx`, branch `main`, 10 commits on top of `first commit`.
**State:** Phase 1 complete, gate green, working tree clean. **Nothing pushed, nothing tagged,
nothing published.**

Phase 1 is the vocabulary, the invariants and one honest policy. `ObservationMaskingPolicy`,
`SummarizingPolicy` and `PolicyChain` are row E1, and `cutctx 0.1.0` publishes at the end of it.

---

## 1. Gate results

Interpreter: **CPython 3.13.15**, `/usr/bin/python3.13`, in `py/CutCtx/.venv`
(`.venv/bin/python` → 3.13.15). This machine has no `python3.12`; `/usr/bin/python3.14` exists and
is the default `python3`. 3.13 is what the lockfiles were resolved on, matching every sibling
repository. CI runs its blocking jobs on 3.12 with a 3.12/3.13 test matrix and a 3.14
early-warning job, none of which can be run here.

Run from inside `py/CutCtx` with the venv activated:

```bash
source .venv/bin/activate
ruff format --check .                       # 29 files already formatted
ruff check .                                # All checks passed!
mypy src tests                              # Success: no issues found in 22 source files
lint-imports                                # Contracts: 5 kept, 0 broken (17 files, 41 deps)
pytest -m "not live and not performance"    # 156 passed, 4 deselected
pytest -m performance                       # 4 passed, 156 deselected
pytest --cov --cov-report=term-missing      # 100.00 % — floor is 95 %
```

Coverage is 100 % of statements and branches across all nine modules. The CI install path was also
exercised end to end in a throwaway venv — `pip install --require-hashes -r requirements/ci.lock`,
`pip install . --no-deps`, `pytest` — 156 passed. A separate clean venv with `pip install .` pulls
in `baseaicore` and nothing else (gold standard G2).

`pre-commit` is **not installed on this machine**, so `pre-commit install` was not run. The
`.pre-commit-config.yaml` is LoadLedger's, unmodified; the hooks it configures (ruff, ruff-format,
whitespace/EOL fixers, gitleaks) are all either run above or run in CI.

Performance, spec §15, on this machine (median of five, `pytest -m performance`):

| Measure | Target | Measured |
|---|---:|---:|
| Plan, 200-turn transcript | ≤ 50 ms | **0.39 ms** |
| Plan, 2 000-turn transcript | ≤ 500 ms | **3.85 ms** |
| Apply, 200 turns | ≤ 10 ms | **0.64 ms** |

A fourth performance test asserts the *shape* — ten times the turns must not cost more than forty
times the time. The absolute budgets above would pass a quadratic implementation for a long while
and then fail on the first real 20 000-turn trajectory.

---

## 2. Public surface as built, against spec §7

Everything in spec §7 that belongs to Phase 1 is implemented as written. `cutctx.__all__` has 23
names and a contract test pins it exactly.

`Role`, `Action`, `TranscriptTurn`, `Transcript`, `CompactionBudget`, `TokenEstimator`,
`CharRatioEstimator`, `CompactionPolicy`, `TurnAction`, `SummarizationRequest`, `CompactionPlan`,
`CompactionExecutor`, `CompactedTranscript`, `CompactionReport`, `DropOldestPolicy`,
`CompactionError`, `BudgetUnsatisfiable`, `SummaryMissing`, `PlanTranscriptMismatch` — all present
with the documented error codes. Deferred to E1 as instructed: `ObservationMaskingPolicy`,
`SummarizingPolicy`, `PolicyChain`.

### Additions to §7, and why

| Added | Why |
|---|---|
| `TurnReplacement(content, token_estimate)` and `TurnAction.replacement` | A `MASK` action must say what goes in the turn's place, or `apply` cannot produce the view and `tokens_after_estimate` cannot be validated for a plan containing one. Not adding it means E1 mutates a frozen, golden-tested type — the same argument the kickoff makes for `budget_unmet`. **Phase 1 emits none**; the *format* of a stub (labelled, carrying the original's hash, never an excerpt) is still E1's to define. |
| `CompactionPlan.budget_unmet` | Settled in Phase 1, defaulting `False`. See §3. |
| `CompactionPlan.to_dict()`, `.canonical_json()`, `.plan_hash()`; `CompactionReport.to_dict()`; `TurnAction.to_dict()`, `SummarizationRequest.to_dict()`, `TurnReplacement.to_dict()` | The golden format is set here and E1 inherits it. Written explicitly rather than via `dataclasses.asdict`, so the wire shape is deliberate. All go through `baseaicore.canonical_json` / `sha256_of`. |
| `SummarizationRequest.summary_turn_id` (`summary:<group_id>`) and `SUMMARY_TURN_ID_PREFIX` | A summary turn needs a deterministic id. Derived, not generated: a counter or a random source would make two applications of one plan differ (contract 4). A `group_id` whose derived id collides with an existing turn is refused at plan construction. |
| `EMPTY_METADATA` | The immutable default, exported so a caller can compare against it. |
| `Transcript.turn_ids()` | Used everywhere a plan is compared to a transcript; cheaper and clearer than a comprehension at each site. |
| `CompactionBudget`, `Transcript`, `TranscriptTurn`, `TurnAction`, `SummarizationRequest`, `TurnReplacement`, `CharRatioEstimator` all refuse malformed input at construction | With `baseaicore.ValidationError`, not a §13 code. See §2.1. |

### 2.1 Where invariant violations raise, and why it is not a §13 code

Spec §13's table describes **outcomes a caller chooses between**. A plan that forgets a turn, acts
on a pinned one or splits a tool exchange is not an outcome — it is a defect in the policy that
wrote it. Those raise `baseaicore.ValidationError` ("a value failed a domain rule: wrong shape,
wrong range, or a broken invariant" — its own docstring), which is a `SuiteError`, so a caller
catching suite errors still catches it. The same applies to malformed input at a constructor.

Every §13 row is produced and tested: `BudgetUnsatisfiable` with both numbers,
`PlanTranscriptMismatch`, `SummaryMissing` naming the group, and the chain-exhausted row as
`budget_unmet` on the plan. **If E1 or a reviewer disagrees, this is the one place to change**, and
it would be a spec §13 amendment, not a code change scattered across modules — every raise is in
`_invariants.py`.

### 2.2 Deliberate non-refusal, the only one in the package

`apply(..., summaries=...)` **ignores** entries for groups the plan does not contain. A caller may
reasonably hold one mapping across several plans, and there is no §13 code for "too many
summaries". It is documented in the method's docstring and pinned by a property, so changing it
later is a decision somebody makes rather than one that leaks in.

---

## 3. The three settled shapes — decisions E1 and I1 must not relitigate

### 3.1 `CompactionReport`'s fields

Spec §11.7 makes it *exactly* the body of `context.compacted`, and PromptCadence lifecycle §7 says
that event carries "before/after token estimates and the turns affected". Shaped as though it were
a SetSpec payload, because two applications will emit it without reshaping:

```text
plan_hash              sha256 of the plan's canonical JSON — the audit link
policy_name            policy_version
tokens_before          tokens_after_estimate      estimator_ratio      budget_unmet
turns_before           turns_after
kept_turn_ids  masked_turn_ids  summarized_turn_ids  dropped_turn_ids  summary_turn_ids
```

Three decisions inside that:

* **No timestamp, no field that could hold one.** The consumer's event frame already stamps and
  sequences; a second time here would be a second answer to the same question, and it would break
  byte-identity on re-derivation. A test asserts no field name contains `time` or `_at`.
* **Nothing is computed.** Every figure is copied from the plan. The development plan names "token
  estimates drifting between plan and report" as this phase's likely failure mode, and the way to
  make a drift impossible is for there to be only one computation — `_invariants.estimate_after`.
  The plan carries its result, the validator checks it, the report repeats it.
* **Flat scalars and id lists; never content.** A turn is named by id and never quoted (spec §14).
  The per-group detail an operator needs — "which turns were summarized into what" — is
  `summarized_turn_ids` plus `summary_turn_ids`, joined through the stored plan by `plan_hash`.
  A nested per-group structure was rejected: it duplicates the plan the consumer already persists
  (PromptCadence's `compactions` table, IdeaPress's stage records), and a payload that repeats its
  own source is a payload that can contradict it.

**When this becomes a real SetSpec payload** (I1, or whenever `context.compacted` is versioned):
it is already `MAJOR.MINOR`-shaped, and `to_dict()` is the wire form.

### 3.2 `budget_unmet`

**On the plan now, defaulting `False`** — the kickoff's first option. Adding a field to a frozen,
golden-tested type at E1 would invalidate all sixteen goldens written here, and E1 is a Sonnet row
that should be adding policies, not migrating types.

It is **derived, not declared**: construction computes `tokens_after_estimate > budget.max_tokens`
and *refuses a plan that disagrees*. That is what makes the outcome trichotomous and honest — a
plan fits, or it says it does not, or `BudgetUnsatisfiable` was raised before any plan existed.
There is no plan that claims to fit while being over, and no way for E1's `PolicyChain` to write
one by accident.

**A thing E1 will want to know:** for `DropOldestPolicy`, `budget_unmet` is reachable *only*
through tool-exchange lock-in. If every remaining turn were untouchable, the floor would exceed the
budget and `BudgetUnsatisfiable` would have fired instead. The only shape where drop-oldest
exhausts its options while the budget is still theoretically meetable is a huge old call whose
result sits in the protected tail — exactly the case masking will be able to reduce.
`tests/unit/test_drop_oldest.py::test_an_exhausted_policy_says_so_rather_than_truncating` is that
case.

### 3.3 `metadata`

`Mapping[str, str]`, defaulting to the module-level `EMPTY_METADATA = MappingProxyType({})`, and
normalized at construction to `MappingProxyType(dict(value))`.

* **Immutable default**, so a frozen turn is frozen in fact and a caller mutating its own dict
  afterwards cannot change a turn it already handed over.
* **Value equality, order-insensitive** — two turns whose metadata dicts were built in different
  insertion orders are equal. A property asserts that a transcript rebuilt with reversed metadata
  insertion order produces byte-identical plans.
* **Turns are not hashable** (a mapping field). Index by `turn_id`; every plan does.
* **Never in a plan's bytes.** `metadata` appears in no `to_dict()`. This is deliberate: it is
  caller-owned, opaque, and a plan that hashed it would change when a caller added a debugging key.

**Policies treat it as opaque (spec §4). No policy reads it in Phase 1 and none should learn to**
without a shipped policy that documents the keys it consumes. The IdeaPress mapping in
`cutctx.types`'s module docstring sketches `{"distance": "3"}` and `{"kind": "note"}` as the shape
an IdeaPress-flavoured policy would eventually read at J3 — that is a sketch, not a contract.

The **executor** stamps three namespaced keys on turns it produced or altered:
`cutctx.kind` (`summary` / `masked`), `cutctx.summary_group`, `cutctx.replaced_turn_count`. That
is the executor labelling its own output, not a channel between policies: a view in which a
summary is indistinguishable from a turn somebody took is a view nobody can explain afterwards.

---

## 4. The multi-call decision, and how contract 3 is read

Two readings had to be settled, and both are load-bearing for E1.

**`tool_call_id` is a correlation id, not a per-call id.** One assistant turn may issue several
calls, so the call/result relation is not one-to-one. Rather than change §7's field to a list, the
field means: *every turn carrying this value belongs to one tool exchange*. An assistant turn
issuing three calls and its three results share one id. This costs nothing — the unit that must
travel together is the transitive closure of the per-call relation anyway (dropping two of three
results orphans the third against a surviving call), so per-call granularity collapses to the same
partition and buys only a graph traversal whose order is one more thing determinism has to pin
down. Callers whose provider gives distinct per-call ids assign one of them, or a synthetic
exchange id, to all the turns; provider-side ids stay in the caller's own store. A `TOOL` turn
whose correlation id matches nothing is not an error — an exchange of one, as an earlier compaction
round would leave.

**Contract 3 binds removal, not masking.** The contract says "masked together, summarized in the
same group, or dropped as a pair — never separated, because an orphaned call or result is a
malformed transcript". The operative prohibition is *separation*, and what separates is removal:
`KEEP` and `MASK` leave a turn in the view at its own position, so masking a tool result beside a
kept call orphans nothing. The literal reading of "masked together" would forbid the masking policy
the spec itself ships two paragraphs earlier ("masks TOOL-result bodies … reasoning stays, bulk
goes"). So the enforced rule is:

> Within one exchange, either every member is retained (`KEEP`/`MASK`, mixed freely), or every
> member is removed by the **same** action — all `DROP`, or all `SUMMARIZE` into the same group.

**Protection propagates through an exchange, but does not move the refusal threshold.** A protected
result forty turns from its call makes that call undroppable. But the call is still *maskable*, so
`BudgetUnsatisfiable` is computed over the **strict** untouchable set (system + pinned + protected
tail), not over the closure — otherwise it would refuse budgets E1's masking policies can meet.
`_invariants.removable_turn_ids` is the closed set a policy may remove from;
`_invariants.untouchable_turn_ids` is the strict set no policy may act on at all.

One more small reading: **every `SYSTEM` turn is untouchable**, not "the" system turn. A transcript
carrying two — an application appending an instruction mid-run — has two turns whose loss would
change what the model was told.

---

## 5. How "the invariants are the only path" is enforced, and how it is proven to bite

**The mechanism.** `CompactionPlan` declares `transcript` and `budget` as `dataclasses.InitVar`s.
Constructing a plan therefore *requires* handing over the transcript and budget it is a plan for,
and `__post_init__` runs `_invariants.validate_plan` over the three of them before the object
exists. There is no private constructor to find, no factory to forget, no base class to subclass
past, and no context flag to be out of. The InitVars leave no trace: they are not fields, so they
are absent from `==`, from `repr`, and from `to_dict()`. A plan carries no transcript.

This is stronger than the alternatives the kickoff listed. A validating factory can be bypassed; a
plan carrying "proof of validation" needs the proof to be unforgeable, which in Python it is not;
an AST test only covers the directory it scans. Making validation part of construction removes the
bypass instead of policing it.

**Validation is total,** which is what makes direct construction pointless rather than merely
discouraged. It checks: coverage (every turn id exactly once, in transcript order), the untouchable
set, exchange integrity, summary-group/request agreement in both directions plus request ordering
and derived-id collisions, and the arithmetic — `tokens_before`, `tokens_after_estimate` and
`budget_unmet` are all recomputed and compared. A hand-written plan that is *correct* is accepted
(there is a test); one that lies about any figure is not.

**The second guard.** `test_no_shipped_policy_builds_its_own_plan` parses every module under
`src/cutctx/policies/` and asserts it calls `_invariants.build_plan` and never *constructs* a
`CompactionPlan` (naming the type in a return annotation is fine). Direct construction is safe but
skips `build_plan`'s arithmetic and its `budget_unmet` determination, so a policy doing it would be
writing figures the validator is about to recompute. **Row E1 adds three policy modules to that
directory; this test is what tells their author, at CI time, that there is one way in.**

**Proven to bite, three ways.**

1. `SkipsTheInvariants` in `tests/unit/test_invariants.py` — a policy written the way a hurried one
   would be: builds the plan itself, drops a pinned turn, writes figures that suit it. Every one of
   its own tests would pass. It cannot produce a plan.
2. `test_a_plan_cannot_be_constructed_without_the_transcript_it_is_a_plan_for` — omitting the
   InitVars is a `TypeError`. There is no shorter constructor.
3. `test_validation_refuses_every_mutilation_of_a_valid_plan` — the property version: take a valid
   plan, break it one of eight ways, and assert construction raises. It does not check that a
   correct plan passes (every other property does that); it checks the validator is not a
   decoration.

### 5.1 One cost of the InitVar design, and how it was paid

`__dataclass_fields__` includes `InitVar` entries, and introspecting pretty-printers — IPython's,
and the copy hypothesis vendors for counterexamples — iterate it and `getattr` every entry whose
`init` is true. Without a fallback, printing a plan raises `AttributeError`: **a failing property
test about a plan would report the crash instead of the plan.** That surfaced during this session
and would have surfaced during E1's.

Fixed in `cutctx.types`: after the dataclass is built, the two InitVar names are set as class
attributes to a `_ValidationInput` sentinel whose repr is `<validation input; not carried on the
plan>`. Honest (a `None` would have implied the plan had one and lost it), and it fixes the crash
for hypothesis, IPython and anything else. `mypy` still rejects `plan.transcript`, because it is
not a field. `tests/unit/test_types.py::TestCompactionPlanIntrospection` pins this.

---

## 6. The property suite — what was chosen, what was rejected, and how it was validated

**The suite was validated by breaking the implementation, not by counting tests.** Eleven mutants
were introduced deliberately and the suite was run against each. Two survived the first draft, and
both survivals changed the design of the tests. That is the part worth reading.

### 6.1 The two findings

**A property that imports the implementation's own helper tests self-consistency, not correctness.**
The first draft asked `_invariants.untouchable_turn_ids` what the untouchable set was and then
checked the plan had not touched it. Two mutants sailed through: an off-by-one in the protected
tail (`index > protected_from` instead of `>=`), and an exchange partition that assumed a call and
its results are adjacent. In both cases the oracle moved with the bug. `tests/oracles.py` now
restates contract 2 and contract 3 **from the spec's wording, in a different shape** — a slice for
the tail rather than an index comparison, a dictionary keyed on the correlation id with no notion
of position at all. Both mutants now die (4 and 2 properties respectively). The generators use the
oracle too, so the boundary budgets stay real boundaries under a mutated implementation.

**A generator that reaches the interesting case twice a run is not coverage.** Three separate
instances:

* `DropOldestPolicy` emits only `KEEP` and `DROP`, so the executor's masking and summarization
  paths — *row E1's paths* — were asserted only by hand-written examples.
  `strategies.plans_over` now draws arbitrary **valid** plans over the same awkward transcripts,
  standing in for the policies that do not exist yet. Groups may span several exchanges, because a
  real `SummarizingPolicy` folds a span and a non-adjacent group is the shape most likely to break
  request ordering.
* Even then, 92 % of drawn plans had **no summarization group**, and a mutant that checked only the
  *first* summarization request survived. Fixed twice over: the generator was rebalanced (to 47 %
  with at least one group), and `test_a_missing_summary_refuses_and_names_the_group` now omits
  **every** group in turn rather than drawing one. The mutant dies.
* A uniform `protected_recent_turns` draw over `0..len+3` was sending **63 %** of examples down the
  `BudgetUnsatisfiable` path, where every property about a plan returns early. Weighted; now
  roughly 56 % fits / 41 % unsatisfiable / 3 % `budget_unmet`, with all three outcomes reached.

### 6.2 The generators

`tests/strategies.py` builds transcripts **by construction, never by `filter`** — heavy filtering
gives flaky `filter_too_much` health-check failures and useless shrinking. It reaches: multi-call
assistant turns (1–3 results); results displaced far from their call; orphaned results whose call
is absent; runs of pinned turns and entirely-pinned transcripts (a third of draws); more than one
`SYSTEM` turn, none, and one that is not first; transcripts shorter than
`protected_recent_turns`; empty transcripts; token estimates of 0 and of 1 000 000; and budgets
drawn from *the transcript's own boundaries* — zero, one, the untouchable total, one either side of
it, the transcript total, one either side of that.

### 6.3 The properties, and what each would catch

`tests/property/test_invariants_property.py` — 15 properties over `DropOldestPolicy`:

| Property | What it would catch |
|---|---|
| No plan acts on the untouchable set | "pinned" treated as advisory; an off-by-one in the tail; a `SYSTEM` turn protected only when first |
| The refusal is exactly the untouchable set exceeding the budget | a refusal computed over the *closure* (would refuse budgets E1 can meet); a refusal firing on equality |
| Every turn id appears exactly once, in transcript order | actions built from a set; actions emitted for dropped turns only; any order coming from a dict |
| A tool exchange is never split, in either direction | pair detection assuming contiguity or adjacency; a drop loop that checks the budget mid-exchange; a one-to-one check that misses "one of three results" |
| Protection propagates through an exchange | a policy that computes the untouchable set correctly and then drops from the remainder without closing over exchanges — passes contract 2 and fails contract 3 only for displaced shapes |
| `apply` leaves the input untouched (equality **and** object identity) | a rebuild that would break the caller's own references |
| The view contains exactly what the plan retained, in order | an executor that skipped an action class; a `drop` branch that is a fall-through |
| `tokens_after_estimate` agrees with an independent sum of the view | the plan/report drift the development plan names |
| Byte-identical on re-derivation | any nondeterminism at all |
| An equivalent construction path gives the same bytes | metadata insertion order reaching a plan — the Phase 2 dict-ordering trap, one phase early |
| The budget outcome is trichotomous and honest | a plan that claims to fit while being over |
| A transcript that already fits is left alone | a loop that drops one exchange before testing the budget — the natural way to write it, and wrong |
| A budget is satisfiable exactly when its floor fits | `>=` where the spec says "smaller than" |
| Validation refuses every mutilation (8 mutations) | the validator being a decoration |
| The report only repeats figures the plan earned | a report that re-derives "after" — agrees today, disagrees the first time a stub's estimate differs from its text |

`tests/property/test_apply_property.py` — 7 properties over **arbitrary valid plans**:

| Property | What it would catch |
|---|---|
| Every action class lands as the plan said | a `MASK` that loses role/`pinned`/`tool_call_id` (which would move a masked result out of its exchange and let the *next* round separate a pair); a `MASK` that keeps the body; a summary emitted per member; a summary placed at the group's last turn |
| The view's estimate is the plan's, for every action class | `estimate_after` counting the original instead of the stub |
| The report partitions the transcript exactly once | a turn in two lists or none — wrong in a way no error would surface |
| A missing summary refuses and names the group — **every group in turn** | a check that stops at the first request |
| A surplus summary is ignored | the deliberate non-refusal, pinned so a later change is a decision |
| Applying twice gives identical results | `apply` not being a pure function of its three arguments |
| A plan never applies to a transcript it was not built for | a set-based mismatch check that lets a reordering through — the ids all match, so the plan then acts on turns by position that it chose by identity |

### 6.4 Properties considered and rejected

* **"A plan always reduces the token estimate."** False, and usefully so: when nothing is removable
  the identity plan is correct. Asserting it would have forced a policy to touch something.
* **"A plan drops as few turns as it can" / "the plan is minimal."** A policy-*quality* claim, not
  an invariant. It would lock in drop-oldest's greedy choice and forbid an E1 policy with a
  different objective — and E1 has three.
* **"The applied view fits the budget."** False by design. `budget_unmet` exists precisely because
  it does not always hold; asserting it would have written silent truncation into the tests.
* **"Every dropped turn is older than every kept turn."** The intuition drop-oldest invites, and
  false: a recent protected result keeps its ancient call alive. Asserting it would have made
  exchange closure look like a bug.
* **"Plans are stable under appending a turn."** False — the protected tail is positional, so
  appending shifts what is untouchable. It encodes a wrong mental model of `protected_recent_turns`.
* **"`apply` is idempotent."** Meaningless: a plan is a total function over *one* transcript, and
  the output has different turn ids. Testing it would have required a second plan and would have
  been testing that second plan.
* **`CompactionPlan` round-trips through `to_dict`.** Deliberately impossible: reconstruction needs
  the transcript, which is the guard working. Byte-identity of `to_dict()` is asserted instead, and
  is the property that actually matters for an audit record.
* **"Masking never changes the turn count."** True, but Phase 2's, and it is a unit test here
  rather than a property — it is a statement about one action class, not about arbitrary inputs.
* **A property over `CompactionPolicy` implementations generically.** There is one. It would be a
  property over a sample of size one dressed up as generality. Row E1 should add it when there are
  four, and `plans_over` is the generator to build it on.

### 6.5 Replaying a failure

`tests/conftest.py` registers and loads a `cutctx` hypothesis profile: `max_examples=150`,
`deadline=None`, and **`print_blob=True`**. `pytest-randomly` reseeds every test, so a CI failure
is not reproducible from the command line alone — but each hypothesis failure prints an
`@reproduce_failure('6.167.1', b'...')` decorator to paste onto the failing test, which replays
that exact example. The `--randomly-seed=` line pytest prints at the top of a run reproduces the
*ordering*. A failure reproducing only under one seed is a real bug (`CLAUDE.md`), never a reason
to pin one. `deadline=None` because these run under coverage on a shared runner and none of the
properties is about speed — speed is asserted separately under the `performance` marker.
`.hypothesis/` is already in the canonical `.gitignore`; no change was needed there.

---

## 7. Toolchain provenance

Copied from `py/LoadLedger` and adapted for names only, except where noted:
`pyproject.toml`, `.importlinter`, `.editorconfig`, `.pre-commit-config.yaml`,
`.github/workflows/{ci,release}.yml`, `requirements/release.in`, `CONTRIBUTING.md`, `SECURITY.md`,
`LICENSE`. `.gitignore` was **not** touched — it is the suite's canonical one and already carries
`.hypothesis/`, so the append the kickoff anticipated was unnecessary.

Three deliberate differences:

1. **`hypothesis>=6.100,<7` in the `dev` extra.** Runtime budget unchanged at 0 non-suite packages;
   the import allowlist test asserts nothing under `src/` imports it.
2. **Three extra `.importlinter` contracts** beyond the application/sibling pair — no HTTP client or
   socket, no database or filesystem, no clock or randomness — all with
   `allow_indirect_imports = True`, since they describe what *this package's own modules* import.
   Five contracts, all kept. Both purity guards were checked against a temporary
   `import datetime, pathlib` in `estimator.py`: two contracts broke and the allowlist test failed.
3. **`SECURITY.md` and `CONTRIBUTING.md` were rewritten**, not just renamed. LoadLedger's talked
   about ceilings, debits, clocks and SQL models; also fixed two stray line-break artifacts
   inherited from that copy.

`requirements/ci.lock` and `release.lock` were regenerated with **pip-tools 7.6.1** on Python 3.13
(the same tool and interpreter as the siblings) — `--generate-hashes`, resolved against PyPI.
`release.lock` is **byte-identical to LoadLedger's below the header**, which is the check that the
release chain is reproducible rather than merely pinned. Note for whoever regenerates: pip-tools
7.6.1 writes `--no-index` into the recorded header itself; passing it fails to resolve.
`requirements/README.md` says so.

---

## 8. Commits

Ten, on `main`, on top of `8c63735 first commit`:

```text
a5b218b  build: repository skeleton and toolchain
8007817  docs: mirror the CutCtx spec and development plan
0a09a47  feat: the transcript vocabulary, the plan types and the typed refusals
85124fd  feat: the invariant module, and no path to a plan that avoids it
8bcc235  feat: token estimation and the plan executor
dbcd50f  feat: DropOldestPolicy and the curated public surface
c4634b0  test: unit suites for the vocabulary, the invariants, the executor and the policy
de3a295  test: property suites over arbitrary transcripts and arbitrary valid plans
8a921cc  test: determinism goldens, the purity contracts and the performance targets
2ca09f7  docs: changelog for the Phase 1 surface
```

`git status --short` was clean at the start of the session and is clean at the end. Nothing was
staged with `git add -A`.

---

## 9. Before the next session — operator steps

1. **Push `main`** to `https://github.com/JPKell/CutCtx.git`. Ten commits, nothing tagged. In
   VS Code the push needs the askpass IPC environment (the FreeWeight M6 precedent).
2. **Confirm CI green on the first push.** Two jobs cannot be run on this machine and are checked
   for the first time there: the **3.12** blocking jobs (no `python3.12` here) and the **3.14**
   early-warning job. The 3.14 job resolves from ranges rather than the lock; `hypothesis` is the
   only new pin in the graph and it publishes pure-Python wheels, so it should install, but this is
   the first repository in the suite to depend on it and that job is where it is proven.
   `pip-audit` runs over both locks; `gitleaks` needs `fetch-depth: 0`, which is already in the
   copied workflow.
3. **The PyPI name `cutctx` is FREE.** `https://pypi.org/pypi/cutctx/json` → **404**, checked
   2026-09-02. The documented fallback `aisuite-cutctx` is also free (404) but is not needed. Master
   architecture §1.1 requires availability to be verified before first publish; it is verified, and
   nothing in the repository, the docs or the import graph needs the fallback. **Reserve it before
   E1** if you want certainty — E1 publishes `0.1.0`, and a name taken in the interval would change
   the import name, `pyproject.toml`, `.importlinter`, the coverage paths and every document that
   names the package.
4. **Optional:** `pre-commit` is not installed on this machine, so `pre-commit install` was never
   run in this repository. Install it if you want the hooks locally; CI enforces the same checks.

### 9.1 Nothing in the docs was found wrong

Every underdetermined passage is settled above (§2, §3, §4) rather than being a defect. Three are
worth a reviewer's eye, because they are readings rather than transcriptions and E1/I1 will build
on them:

* **Spec §11 contract 3's "masked together"** — read as binding *removal*, not masking (§4).
  Read literally it forbids `ObservationMaskingPolicy`, which §7 ships. If the reading is wrong,
  §7's masking policy description is what needs amending, and E1 is the row that discovers it.
* **Spec §13's last row** locates `budget_unmet` at chain exhaustion, but a single policy can
  exhaust its options too, and `DropOldestPolicy` does (§3.2). The flag is on the plan, derived, and
  means what §13 says it means; §13's *condition* column is narrower than the flag's reachability.
* **Spec §13 is an outcome table, not an error table**, so invariant violations raise
  `baseaicore.ValidationError` (§2.1). Worth a line in the spec if a reviewer agrees.

### 9.2 A trap the plan did not name

The kickoff warned about pair detection missing multi-call turns, and about estimates drifting
between plan and report. Both are handled. The one it did not name, and the one that cost the most
time, is in §6.1: **an oracle imported from the implementation makes a property suite look
thorough and prove nothing.** Row E1 adds three policies and will want new properties; they belong
against `tests/oracles.py`, and if E1 needs a new oracle it should be *written from the spec*, not
imported from `_invariants`. `CONTRIBUTING.md` says so, and this is the paragraph it is pointing at.
