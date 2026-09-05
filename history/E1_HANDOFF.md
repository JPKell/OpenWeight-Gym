# E1 — CutCtx Phase 2, the policy set, `cutctx 0.1.0` prepared

**Row:** E1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1, run after
E2 in the same session, as §1 sanctions.
**Date:** 2026-09-03. **Model:** Sonnet 5 · high, as scheduled — no deviation.
**Repositories touched:** `py/CutCtx` (6 commits), `docs` (1 commit).
**State:** `cutctx 0.1.0` **prepared, not published.** Nothing pushed, nothing tagged, nothing
published. Both working trees clean.

---

## 1. Gate results

Run from inside `/home/jpk/ai/suite/py/CutCtx`, at commit `4ade547`, with the repository's own
virtualenv. **Interpreter named as M5C-13 requires**, confirmed rather than copied:

```text
$ ./.venv/bin/python --version
Python 3.13.15

$ ./.venv/bin/python -m ruff format --check .        37 files already formatted
$ ./.venv/bin/python -m ruff check .                 All checks passed!
$ ./.venv/bin/python -m mypy src tests acceptance    Success: no issues found in 30 source files
$ ./.venv/bin/lint-imports                           Contracts: 5 kept, 0 broken.
$ ./.venv/bin/python -m pytest -m "not live and not performance" -q --cov --cov-report=term
                                                     401 passed, 4 deselected
                                                     Total coverage: 100.00%
```

**100 % on every module**, as before this row; the floor is 95 % and no margin was spent.

```text
$ ./.venv/bin/python -m build --no-isolation         Successfully built cutctx-0.1.0.tar.gz
                                                     and cutctx-0.1.0-py3-none-any.whl
$ ./.venv/bin/python -m twine check dist/*           PASSED, PASSED
```

The wheel installs into a clean 3.13.15 virtualenv holding **only** `cutctx` and `baseaicore`,
imports, and passes `acceptance/plan_and_apply.py` — spec §20 criterion 2, verified rather than
asserted.

## 2. What was built, against spec §7

| §7 name | Built | Notes |
|---|---|---|
| `ObservationMaskingPolicy(keep_recent_results=2, placeholder=…, *, estimator=None)` | `policies/masking.py` | `estimator` is a §7 addition — the stub's cost has to be estimated by something, and `estimator_ratio` exists for exactly this |
| `SummarizingPolicy(prompt_id, target_ratio=0.2, min_span_turns=4)` | `policies/summarizing.py` | As §7 writes it |
| `PolicyChain(policies)` | `policies/chain.py` | As §7 writes it; `.name` names every member and version |
| `default_chain(*, prompt_id, …)` | `policies/chain.py` | §7 addition — dev-plan AC2 needs a default chain, and the summarizing step needs a `prompt_id`, so it cannot be a bare constant |
| `DEFAULT_PLACEHOLDER`, `GROUP_ID_PREFIX` | exported | §7 additions, so a consumer reading a plan can recognise a shipped policy's output |

`cutctx.__all__` goes 23 → 29 names; `test_the_public_api_is_exactly_what_the_spec_documents` pins
it.

## 3. The chain's projection design, in enough detail for I1

**The problem.** A chain must run its second policy against what its first policy did. It cannot
*apply* the first plan, because applying needs summaries and under ADR-0052 this package never
produces one. So it composes over a **projection** — the view a plan *would* produce, built from
the plan alone.

**The projection.** Walk the transcript in order:

| Action | In the projection |
|---|---|
| `KEEP` | the turn, unchanged |
| `MASK` | the same turn, wearing the plan's `TurnReplacement` as content and estimate. **Id, role, `tool_call_id` and `pinned` are preserved** |
| `DROP` | absent |
| `SUMMARIZE` | absent; at the position of the group's **earliest** turn, a stand-in with the derived id `summary:<group_id>`, role `ASSISTANT`, estimate `target_tokens`, and **empty content** |

Every one of those is a function of the previous plan, so the projection is deterministic and the
composed plan is byte-identical on re-derivation.

**The one thing the projection cannot supply is content**, because the summary does not exist yet.
That is survivable only because **no shipped policy reads turn content** — they read roles, ids,
estimates and correlation ids. **This is the condition I1 must not break.** A policy that reads
content (an embedding-relevance policy is the obvious one, spec §21) cannot be composed by this
chain as written: it would be handed an empty string for a turn that will hold a paragraph. The
options at that point are to give the stand-in a caller-supplied placeholder, to run such a policy
only first in a chain, or to change the composition — and whichever is chosen is an ADR, because it
changes what a plan means.

**Lifting.** A projected turn is either a real turn under its own id — which is why ids and
correlation ids are preserved through `KEEP` and `MASK`; a later policy must see the *same*
exchanges or it will split one — or a summary stand-in, which maps to **every real turn already
folded into that group**. That mapping is the escalation the whole design turns on:

* a later policy that **drops** a stand-in has decided to drop everything folded into it, and the
  request is removed with it;
* a later policy that **summarizes** a stand-in has decided to fold that whole group into a larger
  one, and the group's turns join the new request.

Exercised end to end: `default_chain` at a tight budget masks, then summarizes what it masked, then
drops the summary turn — and the plan comes out with those turns `DROP` and no request left.

**Reconciliation.** `_reconcile_exchanges` runs unconditionally before the plan is built. Within one
exchange: if any member is removed, all are, by the same action; `DROP` beats `SUMMARIZE` (a member
already gone cannot be folded); where members landed in different groups, the group of the earliest
member **by transcript position** wins. Requests are then rebuilt from the resolutions, so a group
emptied by escalation loses its request and a group widened by it gains the turns.

With the projection as built this is **defence in depth** — each policy runs against a projection
that preserves ids and correlation ids, so its own `build_plan` already refuses a split on its own
view. It runs anyway, because that argument is a property of the *projection* rather than of the
contract: anyone changing the projection changes whether it holds, and a guarantee that depends on
an invariant two modules away is worth enforcing where it is stated. It is tested directly, against
the states it exists to fix, rather than through an end-to-end path that cannot currently produce
them.

**One plan, built once**, through `_invariants.build_plan` against the **real** transcript. It
recomputes `tokens_before`, `tokens_after_estimate` and `budget_unmet` and refuses a plan that
disagrees with its own actions. `budget_unmet` is derived, never declared.

## 4. The group-ordering rule that keeps plans byte-identical

The development plan names *"nondeterminism via dict ordering in group assembly"* as this phase's
likely failure mode. It is closed structurally, in four places, and every one is
**transcript position**:

1. **Span assembly** (`summarizing._spans`) walks `transcript.turns`. It never iterates the
   `frozenset` that `removable_turn_ids` returns; membership is tested against it, ordering never
   comes from it. Fragments left by filtering out a half-exchange are re-split by comparing
   *indices*, not by set difference.
2. **Group ids** are a sha256 of the span's turn ids joined by NUL — derived from the span, so two
   compositions that reach the same span reach the same id. A counter would renumber when a chain
   composed differently; a uuid would differ every run. Both are in the plan's bytes *and* in the
   summary turn's derived id, so either would break contract 4 outright.
3. **Group membership** (`chain._absorb`, `chain._reconcile_exchanges`) is collected from a mapping
   and then **sorted by transcript index** before it becomes a `SummarizationRequest`.
4. **Request order** (`chain._ordered_requests`) sorts by the position of each group's earliest
   turn — which is what `_invariants.validate_plan` independently requires, so a mistake here is a
   rejected plan rather than a wrong one.

Asserted three ways: a property that every group is an ascending, gap-free run of positions; a
property that request order is ascending; and the goldens, which are the bytes.

## 5. The contract 3 decision

**Amended, in `docs/` first.** C1 §9.1 flagged it and left the decision to this row: read literally,
contract 3's *"masked together"* forbids the `ObservationMaskingPolicy` §7 ships two paragraphs
earlier. Having built the policy, the reading Phase 1 enforced is confirmed and the **document** was
what was wrong.

Contract 3 now states the enforced rule: *within one exchange, either every member is retained
(`KEEP`/`MASK`, mixed freely), or every member is removed by the same action — all `DROP`, or all
`SUMMARIZE` into the same group.* The prohibition is on **separation**, and what separates is
**removal**: `KEEP` and `MASK` both leave a turn in the view at its own position carrying its
`tool_call_id`, so masking a result beside a kept call orphans nothing.

The alternative — amending §7's masking description — would have meant either dropping the shipped
policy or giving it a carve-out from a contract it does not actually break. The literal wording was
a compression of the rule, not a different rule.

The amended paragraph also records two readings C1 settled that the spec never stated: that
`tool_call_id` is a **correlation** id rather than a per-call one, and that protection propagates
through an exchange without moving the `BudgetUnsatisfiable` threshold — which is computed over the
strict untouchable set, because the unremovable members may still be maskable.

```text
$ cmp docs/packages/cutctx/spec.md py/CutCtx/docs/packages/cutctx/spec.md
(no output — byte-identical)
```

## 6. Other decisions made where a document left an edge

1. **The stub's format**, golden-locked:
   `"<placeholder> (original: <n> tokens, sha256:<64 hex>)"`. The **label is configurable and the
   evidence is not** — a placeholder template that could omit the digest would make spec §14's
   guarantee a matter of caller discipline, and a guarantee that depends on discipline is a
   default. The digest is untruncated: it is what links the stub to whatever stored the original,
   and shortening it would be a collision question nobody asked to have.
2. **Masking stops as soon as the budget fits**, oldest first, rather than masking every eligible
   result unconditionally. `DropOldestPolicy` already works this way, and masking nine results when
   two would do costs the model seven observations for nothing. `keep_recent_results` stays a
   **hard floor** that does not move for the budget, which is what keeps that from being a slippery
   slope.
3. **A result smaller than its own stub is left alone.** A stub costs about thirty tokens; masking
   a two-token result increases the estimate, and a transcript of many tiny results would grow
   under a policy whose purpose is shrinking.
4. **`SummarizingPolicy` folds exactly one span per plan** — §7's "the oldest contiguous unpinned
   span", taken literally. One span, one model call. A caller wanting two composes the policy into
   a chain twice.
5. **`estimator` on the masking policy** is a §7 addition, and `estimator_ratio` is set only when
   the `CharRatioEstimator` default actually produced a figure **on that plan**: an injected
   estimator leaves it `None` (CutCtx will not describe a ratio somebody else's tokenizer does not
   have), and so does a plan that masked nothing (recording one would describe a computation that
   did not happen).
6. **The chain's `policy_name` names every member and version**
   (`chain(observation_masking@1.0.0+summarizing@1.0.0+drop_oldest@1.0.0)`). A report saying only
   "chain" would leave an auditor unable to tell what produced the view they are looking at. The
   chain's own `version` is its composition rules, which is what would bump if the projection
   changed.
7. **`estimator_ratio` on a composed plan** is the first non-`None` any constituent produced. A
   chain mixing estimators is a caller's configuration choice; the field describes which ratio
   produced figures on this plan, and the first one to do so is the one that did.
8. **Two golden fixture sets.** AC2's wording is the Phase-1 transcripts at the Phase-1 budgets, and
   that is kept verbatim — but every one of those cases is reached by keeping or dropping alone, so
   goldens built only from them would lock in no Phase-2 bytes at all. A second, larger set produces
   real stubs and real summary groups, and
   `test_the_phase_two_goldens_actually_contain_a_stub_and_a_summary_group` stops it quietly
   ceasing to.

## 7. The bug the properties found

**`SummarizingPolicy` folded a span even when the transcript already fitted the budget.** It spent a
model call and replaced turns the model could still have read, for a reduction nobody needed.

Found by `test_a_transcript_that_already_fits_is_left_alone_by_every_shipped_policy`, which is one
of the properties this row runs over **all four** policies rather than over the one it was written
for. The other three check the budget inside a loop over reductions; summarizing has no such loop,
so the check had to be stated explicitly, and now is. One determinism golden moved with the fix
(`summarizing-1.0.0-tool_heavy-1400-0`) and was regenerated deliberately, by deleting it and
reviewing what the suite wrote.

This is the argument for the oracle discipline in miniature: the property is over a *policy-level*
claim that no single-policy suite would have thought to make.

## 8. What the next row must not relitigate

* **Everything in `docs/history/C1_HANDOFF.md` §3 and §4 still stands** and this row changed none of it: the
  `CompactionReport` field list, `budget_unmet` derived on the plan, `metadata` opaque to policies,
  `tool_call_id` as a correlation id, and contract 3 read as binding removal — now the *written*
  rule as well as the enforced one (§5 above).
* **The projection is how composition works, and its condition is that no shipped policy reads
  turn content** (§3). Breaking that condition is an ADR, not an implementation detail.
* **A group id is a digest of its span**, never a counter and never a uuid.
* **Ordering is transcript position**, in all four places §4 names.
* **One plan, built once, through `_invariants.build_plan`.**
  `test_no_shipped_policy_builds_its_own_plan` scans `policies/` and now covers four modules.
* **An oracle is written from the spec, never imported from `_invariants`** (C1 §9.2).
  `maskable_ids` and `exchange_rule_holds` are written that way deliberately — the first counts
  backwards where the policy slices, the second keys on the correlation id with no notion of
  position.
* **The stub's format and the group id prefix are in the goldens**, so changing either is a policy
  version bump and a reviewed golden diff.

## 9. Commits

```text
py/CutCtx  (main, not pushed)
c351ee9  feat(policies): ObservationMaskingPolicy and SummarizingPolicy
c33c41a  feat(policies): PolicyChain composes over a projection, and builds one plan
9dd7360  test(policies): properties over every shipped policy, and the bug they found
691d9bc  test(goldens): cross-matrix determinism goldens for all four policies
339a28b  docs: changelog, README and the runnable acceptance check for Phase 2
4ade547  chore(release): prepare cutctx 0.1.0

docs       (main, not pushed)
6f2564c  docs(cutctx): contract 3 states the enforced rule; §7 carries Phase 2's names
```

## 10. Before the next session — operator steps

CutCtx has **no publish blocker** of E2's kind: nothing here needs hardware this machine lacks, and
the whole suite runs green on the reference interpreter. In order:

1. **Reserve the PyPI name `cutctx`.** `https://pypi.org/pypi/cutctx/json` returned 404 on
   2026-09-03. Reserve before the tag: a name taken in the interval changes the import name,
   `pyproject.toml`, `.importlinter`, the coverage paths and every document that names the package.
2. **Push `main` in `py/CutCtx` and in `docs`**, and confirm CI green. CutCtx's `main` was green at
   `6d704bb` before this row, so a red result is this row's.
3. **Review** the CutCtx diff (same-day review, outstanding-work §4). The hunk to read closely is
   `policies/chain.py` — the projection and the lift are the only place in this package where one
   policy's output is interpreted by another.
4. **Tag** `v0.1.0` in `py/CutCtx`.
5. **Approve the `pypi` environment** and let the release workflow publish.
6. **Post-publish install check:** `pip install cutctx==0.1.0` into a clean virtualenv,
   `python -c "import cutctx"`, and run `acceptance/plan_and_apply.py` against it.

One non-blocking item: **`docs/packages/cutctx/development-plan.md` was not amended.** Phase 2's
"Work" list is accurate as written and this row implemented it; the additions it did not anticipate
(`default_chain`, the `estimator` argument) are recorded in spec §7 instead, which is where §7 names
live. If a reviewer would rather the plan named them too, that is a one-line edit and not a
decision.


---

## 11. Decisions taken with the operator, 2026-09-03 (interview after the build)

Every one confirmed the implementation as built; nothing was reworked.

| # | Issue | Decision | Where it is |
|---|---|---|---|
| A | Contract 3's literal wording forbids the masking policy §7 ships | **Amend the contract** to state the enforced rule, not §7's masking description | spec §11.3 (`6f2564c` in `docs/`) |
| B | The masking stub's digest length | **Full sha256**, untruncated. Auditability over ~15 tokens per stub | `policies/masking.py`; goldens |
| C | How much masking does | **Stops as soon as the budget fits**, oldest first; `keep_recent_results` stays a hard floor | `policies/masking.py`; spec §7 |
| D | How many spans a summarization plan folds | **One span per plan**, hence one model call. A caller wanting two composes the policy twice | `policies/summarizing.py`; spec §7 |
| E | The chain's `policy_name` | **Full composition with versions**, inside `plan_hash`. A report says what produced the view | `policies/chain.py` |

Nothing in CutCtx or `docs/` changed as a result of this interview.
