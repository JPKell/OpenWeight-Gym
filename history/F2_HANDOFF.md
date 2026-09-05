# F2 Handoff — PromptCadence Phase 6 (egress, verification, deviation)

**Row:** F2 of `docs/roadmap/outstanding-work.md` §1.
**Session date:** 2026-09-04. **Model:** Opus 5 · high, as scheduled — no deviation.
**Status:** F2 was **blocked at §0.1** on arrival; the blocker was removed by finishing **E5**
in this session, on the operator's instruction. E5 is **done and committed**. F2 itself is
**in progress** below.

---

## 0. F2 was blocked, and why the blocker is gone

The §0.1 check came back the wrong way: PromptCadence pinned `setspec>=0.4,<0.5`, `commissioner
0.1.0` requires `setspec>=0.5,<0.6`, and stop rule 12.1 says stop. This was not inferred from
reading pins — pip's resolver was asked directly, in a throwaway `--target` directory:

```
$ pip install --dry-run --target <scratch> "setspec>=0.4,<0.5" "commissioner==0.1.0"
ERROR: Cannot install commissioner==0.1.0 and setspec<0.5 and >=0.4 ...
    commissioner 0.1.0 depends on setspec<0.6 and >=0.5
ERROR: ResolutionImpossible
```

The fix was E5's sweep. `docs/history/E5_HANDOFF.md` records that E5 ran on 2026-09-04 and stopped correctly
at its Gate A5, because `mirrorwall 0.2.2` was still parked on the `pypi` environment approval and
§10 forbids sweeping against an unpublished wheel. **That approval happened after E5's session
ended** — `mirrorwall 0.2.2` is on PyPI — so Gate B was unblocked and merely unrun. The operator
directed this session to resume it rather than schedule it separately. **The F2 kickoff's §0.1 was
right that 0.2.2 was published and `docs/history/E5_HANDOFF.md` §1's table was out of date, not the reverse.**

---

## 1. E5 resumed — the pin sweep, as built

Resumed at `docs/history/E5_HANDOFF.md` §9: A4's install checks, then Gate B, then Gate C.

### A4 — post-publish install checks, both clean (Python 3.13.15)

```
$ mw-check/bin/pip install mirrorwall==0.2.2   →  mirrorwall 0.2.2
   setspec 0.6.0 · mirrorwall 0.2.2 · baseaicore 0.4.1
$ cap-check/bin/pip install "mirrorwall==0.2.2" "setspec==0.6.0"
   setspec 0.6.0 · mirrorwall 0.2.2 · baseaicore 0.4.1
```

The second is the proof the cap is gone. Note the first check is *also* proof: `mirrorwall 0.2.2`
alone now pulls `setspec 0.6.0`, which under 0.2.1 was impossible.

### Gate B — the resolved-version table, which is the point of the row

| Repo | Pin, after | Interpreter | `setspec` | `baseaicore` | `mirrorwall` | Gate | Commit |
|---|---|---|---|---|---|---|---|
| PromptCadence | **`>=0.5,<0.7`** | 3.13.15 | **0.6.0** | 0.4.1 | 0.2.2 | 875 passed, 2 skipped | `1c1eb33` |
| IdeaPress | `>=0.4,<0.7` | 3.13.15 | **0.6.0** | 0.4.1 | 0.2.2 | 1029 passed, 5 skipped | `e2138fd` |
| FreeWeight | `>=0.4,<0.7` | 3.14.4 | **0.6.0** | 0.4.1 | 0.2.2 | 2508 passed, 28 skipped ×2 | `2b93132` |
| LoadCoach | `>=0.4,<0.5` — **untouched** | — | — | — | — | not run | none |

Full gate per repo was `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
pytest -m "not live and not performance"`, all green. FreeWeight ran twice: its ordinary venv and
a clean `--require-hashes` venv built from the recompiled lock.

**The floor decision (`docs/history/E5_HANDOFF.md` §9 vs the E5 row) was resolved by the operator in favour of
the handoff: PromptCadence gets `>=0.5,<0.7`.** Spec §5 requires `governance.egress_decision`,
which `setspec` 0.5 introduced, and a floor below a component's own stated spec is drift that stays
invisible until someone installs the wrong thing. IdeaPress and FreeWeight keep the 0.4 floor,
correctly — `setspec.prompts` plus `GeneratorInfo` is their whole surface and it has not moved.
The stale five-line "this pin cannot move yet" comment in PromptCadence was deleted, not amended.

### Gate C — docs, commit `c938408`

E5 row marked done; §4's "prepared and waiting" release step closed; the "E5 before F2 and H4"
ordering constraint downgraded to satisfied-for-F2, with H4 still gated on the
`CapabilityEvidenceV1_1Out` adoption rather than on MirrorWall. **No component repo mirrors
`roadmap/`**, so there was nothing to `cmp`-prove.

## 2. Five things the E5 row said that were not true, or did not say

These are folded into the docs row as well; they are here because they cost real time.

1. **A widened pin does not move an existing venv, and looks exactly like success when it does
   not.** PromptCadence's editable reinstall jumped to `setspec` 0.6.0 unaided; **IdeaPress's did
   not** — it silently stayed at 0.4.0, because a floor of `>=0.4` is still satisfied by the
   installed version and pip had no reason to act. **The 0.5 floor self-enforces; a 0.4 floor does
   not.** Where the floor did not move, the three packages were upgraded by name and confirmed with
   `pip show` before the gate was believed. This is precisely the failure the row warned about
   ("a pin that widened but resolved to `setspec 0.4.0` looks exactly like success") and it is
   worth knowing that it bites on exactly the repos whose floor stays put.
2. **`pip-compile` 7.6.1 no longer accepts `--no-index` as the alias for `--no-emit-index-url`.**
   It now means *ignore the package index*, so the command recorded in FreeWeight's own lock header
   fails with `No matching distribution found for hatchling` — build isolation cannot reach PyPI.
   **Every lock header in the suite still records the old spelling**, MirrorWall's included; the
   flag that reproduces those files today is `--no-emit-index-url`. FreeWeight's header now records
   the working command, which is the one line in that lock to move beyond the three pins.
3. **FreeWeight's `ci.lock` needed three `-P` flags** — confirmed, and the reason is worth keeping:
   `mirrorwall 0.2.0` *in that lock* itself required `setspec<0.5`, so `-P setspec -P baseaicore`
   alone holds the lock at 0.4.0 while reporting success.
4. **A repository's own venv can be the wrong oracle.** FreeWeight's carries *editable* installs of
   the `setspec` and `baseaicore` workspace checkouts, whose `dist-info` still reads 0.4.0. Its
   green gate proves nothing about what a consumer resolves; the lock venv is the proof.
5. **The E5 row's `>=0.4,<0.7` for PromptCadence contradicted `docs/history/E5_HANDOFF.md` §9's `>=0.5,<0.7`.**
   Two documents, both deliberate, no tiebreak written down. Resolved by the operator (§1).

## 3. F2's blocker, re-verified after the sweep

```
$ pip install --dry-run --target <scratch> -e PromptCadence commissioner==0.1.0
Would install ... baseaicore-0.4.1 commissioner-0.1.0 mirrorwall-0.2.2 setspec-0.5.0 ...
```

**`setspec 0.5.0`, not 0.6.0** — the kickoff's §0.2 prediction, confirmed. PromptCadence resolves
0.6.0 on its own today and will fall back to 0.5.x the moment `commissioner` is added at Gate A.
That is not a regression and should not be read as one.

**Future row, recorded as §0.2 requires and deliberately not acted on (operator's decision):**
*commissioner's `setspec<0.6` will need widening before PromptCadence can adopt any 0.6 payload.*
It costs nothing today — nothing in PromptCadence consumes a 0.6 payload, and `capability.evidence`
1.1 is LoadCoach's at H4 — so **Commissioner was not widened in this row**, per stop rule 12.2. It
is now also written into `docs/roadmap/outstanding-work.md` §3's ordering note, so the next person
finds it rather than rediscovering it the way E5 rediscovered mirrorwall's.

## 4. Repository state

```
PromptCadence  ahead of origin, unpushed:  F1's P5 work + 1c1eb33
IdeaPress      ahead of origin, unpushed:  e2138fd
FreeWeight     ahead of origin, unpushed:  2b93132
docs           ahead of origin, unpushed:  F1's docs + c938408
py/MirrorWall  level with origin, tag v0.2.2
LoadCoach      level with origin, untouched
```

Pushing is the operator's. Every tree is clean at this boundary.

## 5. F2 proper — built, gated and committed

Five gates, five commits, in the kickoff's order. Nothing was pushed: pushing is the operator's.

| Gate | Commit | What it made true |
|---|---|---|
| A | `f93e912` | `commissioner[sql]` pinned; `egress_decisions` mounted; migration `0006` |
| B+C | `f7e66ea` | Every turn and every `NETWORK` tool call evaluated and recorded; verification fails closed |
| D | `7ce31ad` | The deviation matrix golden over the intent the **bypass path** mints |
| E | `bb601d3` | `GET /egress-decisions`, `promptcadence egress list`, the fetch tests |
| E | `03d31b8` | `--denied-only`; criterion 1 proved over P4's and P5' journeys; spec clarifications |
| docs | `a792d25` | F2 row done; spec §11 contracts 4/5, §12 and §20 amended; mirrors `cmp`-proved |

**Gate B and C share a commit.** They are one change to one code path — the turn's pre-flights and
its post-turn verification — and splitting them would have produced two commits neither of which
left the tree in a state a reviewer could reason about. Every other gate is its own commit.

## 6. Full gate — interpreter and exact invocation (M5C-13)

PromptCadence's venv is **Python 3.13.15**; there is no `python3.12` on this host, so CI covers
3.12 and this gate cannot.

```bash
cd /home/jpk/ai/suite/PromptCadence && source .venv/bin/activate
ruff format --check .        # 107 files already formatted
ruff check .                 # All checks passed!
mypy src tests               # Success: no issues found in 104 source files
lint-imports                 # Contracts: 5 kept, 0 broken
python -m pytest -m "not live and not performance" -q
                             # 908 passed, 2 skipped, 2 deselected
```

Run twice under `pytest-randomly`'s own seeds; both green. No LoadCoach, no GPU and no network
(spec §20 #10) — the fetch tests drive `http_fetch` through an injected `httpx.MockTransport`.

## 7. Resolved versions, and the cap this row confirms (§0.2)

```
$ pip show setspec commissioner baseaicore | grep -E "^(Name|Version)"
Name: setspec        Version: 0.5.0
Name: commissioner   Version: 0.1.0
Name: baseaicore     Version: 0.4.1
```

**`setspec 0.5.0`, exactly as §0.2 predicted.** Before `commissioner` was added, this venv resolved
`setspec 0.6.0`; adding it pulled the resolution back, because `commissioner 0.1.0` pins
`setspec>=0.5,<0.6`. That is intended and is **not** a regression — it is recorded in the pin
comment, the changelog and `docs/roadmap/outstanding-work.md` §3 so the next reader does not read
it as one.

**The future row, recorded and deliberately not acted on (stop rule 12.2):** *commissioner's
`setspec<0.6` will need widening before PromptCadence can adopt any 0.6 payload.* It costs nothing
today — nothing here consumes a 0.6 payload, and `capability.evidence` 1.1 is LoadCoach's at H4 —
and it is the same shape as the `mirrorwall<0.5` cap E5 spent a whole row removing. It is now
written into §3's ordering note in the roadmap, not only into this handoff.

## 8. How the egress class is resolved, and why it is not `ProviderKind`

**So that nobody simplifies it later, this is the reasoning, not just the rule.**

`ProviderKind` names a *runtime*. `openai_compatible` covers both a local llama.cpp server and a
paid remote endpoint, so `kind → egress class` is not a function: the same kind is local on one
machine and remote on another. A build that mapped it anyway would be making exactly the assumption
contract 4 exists to forbid, and it would pass every test written by someone who believed the map.

The resolution is therefore **an equality check at the HTTP boundary**, in
`services/loadcoach_surface.resolve_subject`: LoadCoach 1.0 serves one configured provider, so
*the response's provider kind being the configured one* is what makes the answer local. Anything
else is `REMOTE` — the conservative reading, not the true one, and deliberately so. When LC-E1
registers several providers, the response must carry the serving provider's identity and that
identity becomes the input; the check stays a check, and never becomes an inference.

**Absence is a violation, not a pass**, and there are two absences:

* the response names no `model.canonical_id` (`SUBJECT_ABSENT`, raised in
  `infrastructure/loadcoach.py` beside the check that finds it), and
* `resolve_subject` finds no single configured provider to check against (`subject_unverifiable`).

Both mean *something answered and nothing here can establish that it was the tier that promised
to*. Both halt and record a `VIOLATION` under `promptcadence.verification` — **not** under
`OrderedClassificationPolicy`, which answers "may this go?" before the fact and never produced that
verdict (ADR-0054 rule 7). Recording it under the shipped policy's name would have the record claim
a decision that policy never made.

## 9. The ordering decision, which is the load-bearing one

Spec §20 #4 and #5 are properties of **when** a refusal happens, so the pre-flight order is the
guarantee rather than an implementation detail. In `LoopController._turn`, all before
`turn.started` and therefore before any request is built:

1. **Egress** — first because it is the only unconditional one. A trajectory that may not use a
   tier may not use it whatever the price, the availability or the balance.
2. **Pricing** — unpriced egress is refused rather than treated as free, and a ceiling cannot bind
   what cannot be priced, so this necessarily precedes the budget.
3. **Availability** — the deployment's answer, not policy's.
4. **Budget** — the numbers last; parking a trajectory for a day edge it should never have reached
   would be the wrong answer written durably.

Making that possible required splitting `TierRouter.resolve` into `tier_of` and `ensure_available`.
**Without the split spec §20 #4 was literally unreachable**: every remote tier reports
`loadcoach_has_no_remote_provider` until LC-E1, so a `confidential` trajectory aimed at one halted
on `TIER_UNAVAILABLE` before any egress evaluation ran, and the "queryable `EgressDecision`" the
criterion demands never existed. A tier's egress class is a property of its **configuration**; its
availability is a property of the deployment. Governance decided on the second would mean the
recorded reason silently changes the day a provider is registered.

`resolve` is kept, as the two checks in their old order, for the one caller that makes no egress
decision of its own: recovery's reconciliation, which is re-reading a turn that already ran.

## 10. Deviation categories: all six, and none of them new

`domain/deviation.py` has carried the closed taxonomy since P2 and P4 wired `compare` end to end
into the loop, so **gate D was not a build** — the kickoff's §8 reads as though it were. What was
missing was the evidence that the machinery runs against the intent a *bypassed* trajectory
actually executes under. `tests/golden/deviation_matrix_bypass.json` supplies it: all six
categories, both severities, every category × scope disposition, over `mint_bypass_default`'s
output. The test asserts every category is present before comparing bytes, so a golden that
silently stopped covering one fails rather than passes.

**Nothing was added to `TurnFacts`** (stop rule 12.5). It carries no trajectory ceiling, balance or
headroom, and the closure argument holds unchanged.

What F2 added to the deviation path is one thing only: a `tier_violation` now also records a
`VIOLATION` `EgressDecision`, on the same session as the deviation row and the halt, so a reader
never finds one without the others (ADR-0044).

## 11. What G1 inherits

* **The intent is already the comparison source in both modes.** G1 changes only *who mints it*.
  `compare()` does not move, and no category, severity or disposition changes.
* **`deviation_matrix_bypass.json` is the baseline for contract 1's invariance diff.** When a
  planner mints the intent, those rows must not move — only `intent_id` and the `minted_by` kind
  may. G1 owns writing that diff; this row made the invariant it rests on true.
* **Every turn already carries an egress decision, in both modes**, because egress is not
  conditional on planning (ADR-0048). The record rows expected to differ between a planned and a
  bypassed trajectory are `plan` and `plan_approvals`, and nothing else.
* **Left to G1 deliberately:** the planner, approval modes, plan-declared deviation rows, and
  scoped re-approval itself. A `SCOPED_REAPPROVAL` disposition still halts here, with the cause
  naming that re-approval is not available before Phase 7 — unchanged from P4.

## 12. Things the kickoff said that turned out not to be true

1. **§0.1's stop rule fired.** PromptCadence pinned `setspec>=0.4,<0.5`. Resolved by finishing E5
   on the operator's instruction (§1), not by working around it.
2. **The E5 row and `docs/history/E5_HANDOFF.md` §9 disagreed** about PromptCadence's floor (`>=0.4,<0.7` vs
   `>=0.5,<0.7`). The kickoff presented `>=0.5,<0.7` as settled. Operator chose the handoff's.
3. **§8 reads as though `DeviationHandler` needed building.** It was built at P2 and wired at P4
   (§10). The row's real content was the golden.
4. **§6's "spec §20 #5" cannot be implemented as written.** "A remote tier with no pricing record"
   cannot mean the `pricing_file` field: startup validation already refuses that configuration, so
   a field check is a dead branch. It is the `ModelPricing` **record** — an expired or empty price
   list. Spec §11 contract 5 now says so.
5. **§7's "the fake plays a remote provider answering a local tier"** needed the fake to be able to
   name a different kind in its registry than in its response. It could: `FakeModel.provider_kind`
   and `FakeModel.canonical_id` are separate fields. Nothing had to be invented.
6. **Spec §7.2's `promptcadence egress list [--denied-only]` was never implemented**, and cannot
   express the whole vocabulary — a violation is neither an approval nor a denial. Both flags now
   ship and the spec names both.
7. **Exit condition 5 ("no `egress_governance_deferred_to_p6` survives anywhere") has one honest
   exception**: `CHANGELOG.md` line 243, which is P4's historical record of *why* the tool was
   withheld. A changelog records what happened; deleting it would be rewriting history rather than
   clearing a stale copy. It is gone from all code, tests, `doctor`, `GET /tools`,
   `promptcadence tools list` and the spec.

## 13. Exit conditions

| # | Condition | Where |
|---|---|---|
| 1 | §20 #4: no HTTP request leaves, proved against the client; refusal is queryable | `test_a_confidential_trajectory_never_reaches_a_remote_tier`, `test_the_refusal_is_a_queryable_egress_decision` |
| 2 | §20 #5: `UNPRICED_EGRESS_REFUSED` before any call | `test_an_unpriced_remote_tier_refuses_before_any_call` |
| 3 | Remote provider on a local tier → violation + halt, recorded | `test_a_remote_provider_answering_a_local_tier_is_a_violation_and_halts` |
| 4 | Absent subject metadata → violation | `test_a_response_with_no_execution_subject_is_a_violation_not_a_pass` |
| 5 | Non-allowlisted fetch refused and recorded; `http_fetch` enabled; string cleared | `test_a_fetch_to_a_non_allowlisted_host_is_refused_and_recorded`; §12.7 above |
| 6 | Bypass deviation golden; allowlist refusal never re-approvable | `test_deviation_matrix_bypass_rows_golden`, `test_a_tool_outside_the_trajectory_allowlist_is_never_reapprovable` |
| 7 | Criterion 1 over P4's and P5's journeys | `test_every_turn_of_a_multi_turn_tool_journey_carries_one`, `test_a_priced_journey_records_a_decision_and_a_debit_for_the_same_turn` |
| 8 | `pip show` resolving as §0.2 predicts | §7 above |
| 9 | Full gate green; no LoadCoach, GPU or network | §6 above |
| 10 | Trees clean, pushed, CI green; mirrors `cmp`-identical | §14, §15.4 — **all ten discharged** |

**Condition 10 was discharged after the build.** Pushing is the operator's in this workspace, so
this session committed and stopped; the operator pushed all four repositories during the closing
interview and PromptCadence CI is green at `03d31b8` (§15.4).

## 14. Repository state at session end

At the end of the build, before the operator pushed:

```
PromptCadence  dirty=0  ahead 15  (F1's P5 work, E5's pin, F2's five commits)
docs           dirty=0  ahead  4  (F1's docs, E5's Gate C, F2's docs)
IdeaPress      dirty=0  ahead  1  (E5 B2)
FreeWeight     dirty=0  ahead  1  (E5 B3)
LoadCoach      dirty=0  level     (untouched, correctly — its pin rides H4)
py/MirrorWall  dirty=0  level     (+ tag v0.2.2)
py/Commissioner dirty=0 level     (untouched — not widened; H4 owns that now, §15.3)
```

All four are now pushed and level, plus the two post-decision documentation commits.

Mirrors: `cmp` proves `docs/apps/promptcadence/{spec,lifecycle,development-plan}.md` byte-identical
between the workspace `docs/` and `PromptCadence/docs/`.

## 15. Operator decisions taken after the build (2026-09-04)

Four were put to the operator at the end of the session. Two needed work; both are done.

1. **`fetch_max_data_classification` stays absent by default** — every non-loopback fetch is denied
   `no_ceiling_declared` until an operator declares a ceiling. Confirmed as the shipped posture, on
   ADR-0046 grounds. No change; this is what §5's gate E commits already ship.
2. **The pre-flight ordering becomes an ADR.**
   [ADR-0073](docs/adr/0073-egress-is-decided-on-configuration-before-availability.md) —
   *Egress is decided on a tier's configuration, before its availability* — written and accepted,
   extending ADR-0054 additively. Spec §20 now cites it instead of carrying the reasoning alone,
   and the mirror was re-`cmp`-proved. The other two clarifications (contract 4's absence rule,
   contract 5's record-not-file rule) stay as spec prose by decision: they clarify contracts that
   already exist rather than adding a decision, and ADRs for clarifications dilute the record.
3. **Commissioner's `setspec<0.6` cap is folded into H4**, not left as a note and not given its own
   row. H4 already moves LoadCoach onto `setspec` 0.6 for `capability.evidence` 1.1, so all the 0.6
   movement happens in one row. The H4 row now carries the widen to `setspec>=0.5,<0.7`, states
   plainly that it is a second repository and a second publish (`commissioner 0.1.1`) inside a row
   otherwise scoped to FreeWeight, notes that Commissioner adopts no payload in widening, and asks
   for `pip show` on PromptCadence afterwards — a widen nothing resolves past is not a widen. §3's
   ordering note names H4 as the schedule rather than leaving the cap unscheduled.
4. **The operator pushed all four repositories** during the interview. Every tree is level with
   `origin/main`, and **PromptCadence CI is green at `03d31b8`**, F2's last build commit — so exit
   condition 10 is discharged in full. Two later documentation commits (`2bfc692` here,
   `2eaa73b` in `docs`) carry the ADR and the mirror.

## 16. Model deviation (model-assignment §3.5)

None for F2 — ran on the scheduled **Opus 5 · high**. The E5 half resumed in this session was
scheduled **Sonnet 5 · standard** and ran on Opus 5; `docs/history/E5_HANDOFF.md` already records that
deviation for E5's first sitting, and this is the same deviation continuing. Nothing about E5's
remaining work depended on the larger model — it was as mechanical as the row advertised, and the
two judgment calls in it (the floor contradiction, and the `--no-emit-index-url` discovery) were
findings rather than reasoning.
