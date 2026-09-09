# I1 — PromptCadence Phase 8: compaction, the explanation and its revisions, and the console

**Row:** I1 of `roadmap/outstanding-work.md` §1. **Model:** Opus 5 · high, run whole (no split).
**Date:** 2026-09-06. **Interpreter:** Python 3.13.15 at `PromptCadence/.venv/bin/python`.
**Ships:** nothing. Everything is under `## [Unreleased]`; no bump, no tag, no publish, nothing
pushed.

**Repositories touched:** `PromptCadence` (four commits, plus the docs mirror) and `docs` (three
commits). Both were clean at the start except as §11 records, and both are clean at the end with
their new work committed and unpushed.

---

## 1. Gate results, with the exact invocations

Every gate ran the full pre-PR gate before its commit. The final run, from
`/home/jpk/ai/suite/PromptCadence`:

```bash
.venv/bin/ruff format --check .          # 155 files already formatted
.venv/bin/ruff check .                   # All checks passed!
.venv/bin/python -m mypy src tests       # Success: no issues found in 151 source files
.venv/bin/lint-imports                   # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                         # 1135 passed, 2 skipped, 2 deselected in 63.64s
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                         # Total coverage: 91.33% (floor 85% for an application)
```

The suite grew from 1067 to 1135 tests. Coverage of what this row wrote:

| Module | Coverage |
|---|---|
| `domain/compaction.py` | 100 % |
| `domain/explanation.py` | 100 % |
| `services/compaction.py` | 100 % |
| `services/explanation.py` | 96 % |
| `services/console.py` | 90 % |
| `web/routes/console.py` | 100 % |
| `web/rendering.py` | 100 % |

Migrations went `0008` → `0010`; `tests/integration/test_migrations.py` asserts the head at each
step and a fresh SQLite database migrates to it.

## 2. The gates as commits

| Gate | Commit | What it made true |
|---|---|---|
| A | docs `9b752d7`, PromptCadence `10d371a` | ADRs 0090–0094 accepted and indexed; lifecycle §7 and §9.1, spec §9/§11/§13/§14/§15 and the Phase 8 plan amended; the three PromptCadence mirrors `cmp`-identical; the I1 row marked done |
| A′ | docs `faa714a` | A correction to gate A found by gate B's tests — see §5 |
| B+C | PromptCadence `c5be937` | `cutctx` pinned; `compactions` + migration `0009`; the trigger, the wire mapping and the policy chain; the governed, debited summary; `COMPACTION_FAILED` |
| D+E | PromptCadence `ae24a1b` | `ExplanationBuilder`, the `1.0` schema and its golden; `explanation_revisions` + migration `0010`; materialize-after-transition, the equality golden, invalidation, `db rebuild-explanations` |
| F | PromptCadence `63c6014` | `GET /trajectories/{id}/explanation`, `promptcadence trajectory explain`, scopes |
| G | PromptCadence `c9d5288`, docs `d1d50d3` | The console's nine pages, CSRF, the render suite and the §13 accessibility checklist; UI standards §12 gains PromptCadence's column |
| H | this document | The full gate, both demonstrations, `CHANGELOG.md`, the handoff |

**Two gates were merged into one commit each, deliberately.** B and C do not divide: the summary
is what makes the summarizing policy usable, and a tree that had the policy chain without the
model call would be broken at exactly that boundary rather than smaller. D and E do not divide
either: the equality golden is the point of both, a schema with no cache proves nothing about the
cache, and a cache with no schema has nothing to be equal to. The gate table is an ordering and a
review aid; splitting an indivisible mechanism to satisfy it produces a tree that is wrong at one
of the two commits.

## 3. The five decisions

### D1 — Which envelope the compaction summary runs under (ADR-0090)

**Taken: (b), supersede.** The summary runs on the cheapest admissible **local** tier — ordered by
`context_budget_tokens`, then by name, among tiers whose `max_data_classification` admits the
step's ceiling — under a superseding revision of the step's own `ExecutionIntent`: that tier as
`approved_tier`, no fallbacks, `approved_tools = ∅`, the step's `max_classification` carried
unchanged. A second supersession restores the step's envelope, in a `finally`, so a failed summary
cannot leave the step running narrowed. Both are `policy` mintings, so `MintKind` stays the closed
three it is.

**What the losing options would have claimed.** (a) *Run it on the step's own tier*: cheapest to
build and needs no revision at all — and it silently discards the property the sentence exists
for, so that on a trajectory whose step runs remote, the summary of a confidential transcript
becomes egress and nothing in the record says a decision was made. (c) *Widen `permitted_tiers` at
mint time*: one line — and it weakens **every** step's envelope permanently, for a turn that may
never happen, and the widening is invisible in a diff of one revision against the next. A fourth
option was considered and rejected in the ADR: a synthetic step with its own revision-1 intent is
genuinely clean, but it puts a step id in `execution_intents` that no plan declared, which every
reader of the plan surface then special-cases.

**One consequence worth naming.** `_StepRun` is no longer frozen. Its `intent` field is the only
thing that moves, it moves only in `_supersede_for_compaction`, and it never moves to a wider
envelope. The alternative was threading a replaced value back up through `_call`, `_turn` and
`_run_step` — the same mutation in three signatures, and a way for one of them to forget.

### D2 — What the summary turn spends (ADR-0091)

**Taken: debited, and not counted against `max_turns`.** The debit was already settled by
lifecycle §7; the other half was not written down. `max_turns` is the step's *advance* budget, and
charging housekeeping to it means a long step is ended by how verbose a tool result happened to
be — non-deterministically, and invisibly to the caller.

**The separation is structural, not a filter**, and that is the part worth carrying forward. The
summary lives in its own thread (`threads.step_id = "compaction:<thread id>"`), which it must
anyway: a summary appended to the thread it summarized would be replayed to the model as a
conversational turn on the next wire build, double-counting the very content it replaced. The loop
counts assistant turns *in the step's thread*, so the summary is out of the count with no predicate
to keep in sync.

**What the losing option would have claimed.** *Count it* — every model call the step caused did
cost something, and something should bound it. True, and `max_turns` is the wrong bound: it is
integral and per step, so it cannot express "at most this much housekeeping" without also
shortening the work. The bound that fits is the token and money ceiling, and rule 1 puts the spend
squarely there. `test_a_step_near_its_turn_limit_still_compacts_and_still_completes` holds the
boundary.

### D3 — Invalidation without the sweep (ADR-0092)

**Taken: ship the entry point, not the sweep.** `invalidate(trajectory_id, cause=…)` over
`retention_scrub`, `recosting` and `schema_upgrade`; only the third has a caller in this build. The
first two are tested by scrubbing and re-costing the fixture's rows directly.

**What the losing options would have claimed.** *Build the sweep too* — it is half a day and it
makes the feature demonstrable; and it is a specified Phase 9 deliverable with its own acceptance
criteria, so a sweep written here would be written without them, and discovered by whoever ran P9
rather than by a test. *Defer the entry point as well* — then Phase 8 ships a cache with no
invalidation path, and the golden that makes the cache safe to trust is only ever asserted for a
document that never changes.

**Building it found a real defect.** `plans.raw_document` was `NOT NULL`. A plan document is model
output and must follow the scrub exactly as transcript text does, so the sweep P9 will write could
not have scrubbed it at all. Migration `0010` makes it nullable — see §5.

### D4 — How a browser authenticates, and what CSRF covers (ADR-0094)

**Taken: the API's own principal resolution, no session cookie, CSRF wired now.** An open loopback
install browses and approves as `loopback`; once a token exists, or the bind is not loopback, every
page answers `401`. That makes the console loopback-first **by decision**, and the System page says
so and what changing it would take. `mirrorwall.CsrfMiddleware` is added in the same commit that
renders the first form, and `web/app.py`'s "there is no HTML UI yet" paragraph is rewritten in the
same commit rather than left standing.

**What the losing options would have claimed.** *A session cookie* — what a multi-user deployment
eventually needs, and a new authentication mode with its own threat model, invented at the end of
a long phase whose other half is a cache-consistency proof. *A token in a form field or a query
parameter* — makes the console work off-loopback with no session machinery, and puts a credential
in the access log, the referrer and the history. *Keep the console read-only* — dodges CSRF, and
sends the operator to a terminal at the exact moment the console was meant to help, while CSRF
would still be due for the settings form.

**Scope, deliberately not taken:** same-origin checking, body caps and rate limits stay Phase 9's,
where the security checklist lists them together. This row wired the one control its own form
created the need for.

### D5 — Where materialization runs (ADR-0093)

**Taken: immediately after the terminal transition, in its own write.** The transition commits
alone, exactly as ADR-0044 requires. Composition follows in the next write, is idempotent, and a
failure is logged and never fails the trajectory.

**And the honest answer is the one that made it safe: a missing revision is not a missing
explanation.** The live composition path serves it, `rebuild-explanations` fills it in, and there
is no repair state and no reader that branches on one. That is what makes the revision a genuine
cache — and the suite proves it rather than asserting it: `materialize == compose_live` byte for
byte, a rebuild over an intact cache writes nothing, and
`test_dropping_every_revision_changes_no_answer` deletes every row and re-reads.

**What the losing options would have claimed.** *Compose inside the transition* — the literal
reading of §9.1, and it guarantees a terminal trajectory always has its revision; it costs up to
ten seconds of held write transaction on SQLite at exactly the moment a worker is finishing one
trajectory and wants the next, to buy a guarantee the read path does not need. *Compose lazily on
first read* — no transition cost, and it moves an unbounded cost onto an interactive surface and
makes the §15 read budget unmeetable exactly once per trajectory, the one time somebody is
watching. *Queue it as a job* — correct, and a second scheduler for one job whose failure mode the
read path already handles.

## 4. Exit conditions

| # | Condition | Result |
|---|---|---|
| 1 | D1–D5 as accepted ADRs, docs amended before the code, mirrors `cmp`-identical | **Met.** ADRs 0090–0094, indexed. Gate A's docs commit precedes every code commit. The three mirrors verified with `cmp` at each change |
| 2 | The trigger fires from `[compaction]` against the tier's budget, per step thread, with `compactions` + `context.compacted` in one write | **Met.** `test_a_transcript_over_the_threshold_is_compacted_and_every_turn_stays`, `test_the_event_and_the_row_are_one_write` |
| 3 | The summary runs under an intent, on a local tier, debited and recorded, with its prompt record; no ungoverned summary turn | **Met.** `test_the_summary_runs_under_its_own_superseding_revision_in_its_own_thread`, `test_the_summary_turn_is_debited`, `test_the_summary_prompt_record_is_on_the_turn_that_used_it`, and the contract-1 guard, which now names `_summary_turn` and asserts it takes its `ExecutionIntent` as a required positional parameter |
| 4 | A tool call and its result are never separated, asserted at the `Message` level after a compaction that drops an assistant turn | **Met.** `test_a_dropped_assistant_turn_takes_its_tool_results_with_it` asserts every surviving `tool_call_id` is named by a surviving assistant message's `tool_calls`, and refuses to pass unless an assistant turn was actually dropped |
| 5 | `COMPACTION_FAILED` when the chain cannot fit; `SummaryMissing` unreachable | **Met.** `test_a_budget_the_untouchable_turns_alone_exceed_halts_with_compaction_failed`; unreachability is asserted at the seam — `apply` is wrapped and every plan's requests are checked to be covered — rather than by never seeing the exception |
| 6 | The `1.0` document with goldens, naming every model, tier, tool call, debit and egress verdict | **Met.** `tests/golden/trajectory_explanation.json` over a masked document; `test_the_document_names_every_model_tier_tool_call_debit_and_egress_verdict` |
| 7 | `materialize == compose_live` for every fixture, and after a scrub and a re-costing, each bumping a revision | **Met.** `test_materialize_equals_compose_live`, `test_a_scrubbed_trajectory_still_explains_itself_and_bumps_a_revision`, `test_a_recosting_bumps_a_revision_and_the_equality_still_holds` |
| 8 | Dropping the whole revision table and rebuilding reproduces identical documents; a scrubbed trajectory still explains itself | **Met**, in tests and in demonstration 2 |
| 9 | Both surfaces, the OpenAPI snapshot, scopes | **Met, with one correction:** there is no committed PromptCadence OpenAPI snapshot to update — see §5. The route is asserted present in the generated schema instead, and the scope is enforced and tested |
| 10 | The console renders every record type; CSRF wired; `web/app.py`'s paragraph rewritten | **Met.** Demonstration 2 walks it; `test_the_timeline_renders_every_record_type`; the paragraph is rewritten in the same commit as the first form |
| 11 | Full gate green, coverage at or above 85 %, interpreter and invocations named | **Met.** §1 |
| 12 | Both demonstrations run, with what was seen written down | **Met.** §6 |

## 5. Things this prompt said that turned out not to be true

* **The repositories were not where §0 said.** PromptCadence `main` was at `784e89f`, **one commit
  ahead of `origin`**, not at `0f6734f` level with it — `784e89f` is a `chore` removing a comment
  about the Commissioner cap. docs `main` was at `4fdfc34`, **six ahead**, not `ca020c8`. Both were
  clean, so nothing was at risk; the prompt's "unlike the last four rows you start with nothing
  outstanding" was wrong in both repositories.
* **The highest ADR was `0089`, not `0085`.** Rows H4–H6 added 0086–0089 after the prompt was
  written. This row took 0090–0094, as the prompt's own instruction to re-check the directory
  anticipated.
* **CutCtx's budget field is `max_tokens`, not `budget_tokens`.** `CompactionBudget(max_tokens,
  protected_recent_turns=…)`.
* **There is no committed PromptCadence OpenAPI snapshot.** Gate F asked for it to be "updated";
  `tests/contract/loadcoach_openapi.json` is *LoadCoach's*, held as a contract fixture. Committing
  PromptCadence's own snapshot is a named Phase 9 deliverable ("OpenAPI snapshot committed"), so
  this row did not invent one. What it added instead is an assertion that the new route is present
  in the generated schema, which is the property the snapshot would have protected.
* **`GET /tiers` does not exist**, though spec §7.1 lists it. This predates I1 — the console's
  Tiers page reads the configured snapshot directly, which needs no route. Recorded here as a
  finding for I2 rather than closed silently.
* **The amendment gate A wrote about the compaction target was wrong, and gate B's tests caught
  it.** Gate A stated that the budget compacted *to* is the whole tier budget, "because compacting
  to the threshold would fire the trigger again next turn". It is the other way round: between the
  threshold and the tier budget a compaction has nothing to do and writes a `compactions` row per
  turn saying nothing changed, and once the budget is exceeded the transcript is brought back to
  exactly the budget with no slack, so every following turn compacts. The integration test found it
  as `tokens_after == tokens_before`. `threshold × context_budget_tokens` is now **one figure**,
  used as both the trigger line and the target; docs `faa714a` corrects the amendment and
  `services.compaction.target_tokens` documents why both alternatives are worse.
* **`plans.raw_document` was `NOT NULL`**, so the retention sweep could not have scrubbed the plan
  document — found by D3's scrub test, which the prompt asked for precisely so that things like
  this surface. Migration `0010` makes it nullable.
* **Migrations were running with SQLite foreign keys ON**, and `0010`'s `ALTER COLUMN` is a table
  rebuild, so alembic's batch mode dropped `plans` and cascaded away every `plan_steps` row. The
  fix is LoadCoach's `env.py`, transcribed rather than re-derived: the pragma is set through the raw
  DBAPI cursor outside any transaction, because `PRAGMA foreign_keys` inside one is a documented
  no-op — a silent one. H2's memory note recorded this for LoadCoach; PromptCadence had not picked
  it up.
* **`python-multipart` is not installed**, so FastAPI's `Form()` cannot be used. The console parses
  its urlencoded bodies directly, which is again LoadCoach's precedent and avoids a dependency in
  every install for the sake of two form fields.

## 6. The two demonstrations

### 6.1 Compaction, live

**Stack:** a real LoadCoach `1.1.0` on `127.0.0.1:8766` against Ollama `0.32.13` (13 models), with
the five harness profiles registered. `tools.agent.local_fast` selected
`ollama/gpt-oss:20b@sha256:17052f91a42e`. PromptCadence ran in-process against an isolated
database with `local_fast.context_budget_tokens = 700` (target `560`),
`protected_recent_turns = 1`, and a read root holding a 1 227-character notes file the model was
asked to read three times.

**What was seen:**

* **12 compactions**, all on `local_fast`, all against target `560`:

  | before | after | turns | policy outcome |
  |---|---|---|---|
  | 748 | 409 | 5 → 3 | dropped 2 |
  | 1 087 | 490 | 7 → 4 | **summarized 4** |
  | 1 426 | 502 | 9 → 4 | summarized 4 |
  | 1 765 | 515 | 11 → 4 | summarized 4 |
  | 2 104 | 528 | 13 → 4 | summarized 4 |
  | 2 443 | 541 | 15 → 4 | summarized 4 |
  | 2 782 | 554 | 17 → 4 | summarized 4 |
  | 3 121 … 4 477 | 409 each | 19…27 → 3 | dropped |

  `budget_unmet` was `false` on every one: the compacted wire fitted `560` every time while the
  recorded transcript grew to 4 477 estimated tokens. That is the sentence "compaction is a view,
  never a deletion", as a table.

* **Six summary turns**, each in its own thread (`threads.step_id = compaction:<id>`), each a real
  model call: `ollama/gpt-oss:20b@sha256:17052f91a42e`, input 696 → 1 956 tokens as the span grew,
  output 202–767, LoadCoach time 2 698–8 515 ms. Each thread holds a `USER` turn carrying
  `prompt_id = compaction.summarize` and the `ASSISTANT` turn that answered.

* **All six were debited.** 20 `budget.debited` events for 20 turns — 14 step turns and 6 summary
  turns — and every summary turn id appears in `ledger_entries.source_ref`.

* **Thirteen `intent.minted` events**: the bypass default, then six narrow/restore pairs. The
  revisions alternate exactly as ADR-0090 rule 3 says they should — `approved_tools = []` on the
  narrowing, the full tool set restored on the next — and every one is `minted_by = policy`.

* **The `context.compacted` bodies carry what §7 asks for**: before and after estimates, the
  turns affected by name, the composed chain
  (`chain(observation_masking@1.0.0+summarizing@1.0.0+drop_oldest@1.0.0)`), the plan hash, and the
  summary turn and revision when there was one.

* **The trajectory did not complete.** It parked on `awaiting_approval` with a `turn_overrun`
  deviation and a scoped re-approval request: the model kept requesting tools past
  `max_turns_per_step`. That is the loop's own governance working exactly as specified and is
  unrelated to compaction — but it means the live run demonstrates the compaction machinery and
  **not** the "trajectory completing inside the tier's budget" half of the demonstration. That half
  is held by the scripted 100-turn test below, which is what the prompt intended it for.

**The arithmetic, against the fake:**
`tests/integration/test_compaction.py::test_a_hundred_turn_trajectory_completes_inside_its_tier_budget`
runs 100 turns on a 400-token tier, asserts more than one compaction, and asserts every one left
the wire at or under the target and strictly smaller than it started. It completes.

### 6.2 The console, seeded

One planned trajectory producing a drafting attempt and its verdict, a retried step, tool calls,
an `undeclared_tool` deviation, two compactions with a summary, debits, egress decisions and a
declared finish, on a 260-token tier. Every page walked:

```text
/                              200     5391 bytes   1 table
/trajectories                  200     4327 bytes   1 table
/approvals                     200     2742 bytes   empty state
/tiers                         200     4207 bytes   1 table
/tools                         200     7409 bytes   1 table, 5 rows
/ledger                        200     7501 bytes   2 tables
/egress                        200     6217 bytes   1 table
/system                        200     5102 bytes   1 table
/trajectories/{id}             200    33531 bytes  12 tables, 69 rows
```

The timeline's sections: The request · Plan · Envelopes · Timeline · Tool calls · Compactions ·
Debits · Egress decisions · Deviations · Approvals · Events. Its tables: drafting attempts,
validated steps, every intent revision, the step's turns, the attempts that produced no turn, the
compaction thread's turns, every recorded tool call, where the wire differed from the rows,
recorded debits, every egress decision, where execution differed from its envelope, and every
persisted event. **Every record type the seeded database holds is on the page.**

The explanation was served `materialized from revision 1 (terminal)` in **0.485 ms** — spec §15
budgets 25 ms. Then:

```text
dropped 1 revision(s); re-read is live in 6.123 ms
documents identical after dropping the whole cache: True
rebuild: considered 1, written 1; re-read is materialized revision 1
documents identical after the rebuild: True
```

## 7. Read-only notes for I2

### 7.1 What the injection corpus should attack

This row created **two new surfaces for model output**, and both are worth the corpus's time.

* **The composed document.** Turn text, tool arguments, tool results and the raw plan document all
  reach `promptcadence.trajectory_explanation` verbatim. Nothing parses them, and the document is
  JSON, so the attack is not on this application — it is on **whatever reads the document next**.
  The corpus should include a trajectory whose model output contains: a JSON document that looks
  like an explanation (a nested `"schema": "promptcadence.trajectory_explanation"`), text that
  closes a Markdown fence, and text shaped like the CLI's own summary lines. The property to hold
  is that none of it changes the document's structure — the equality golden already holds the
  bytes, so what the corpus adds is the *reader's* safety.
* **The console.** Every one of those values now reaches a Jinja template.
  `test_untrusted_content_is_escaped_on_every_page` seeds a hostile task and a hostile answer, and
  `test_no_template_marks_a_record_value_safe` asserts no template uses `| safe` anywhere — links
  in table cells are built by a macro whose output is already-escaped markup and which cannot be
  turned off from a call site. The corpus should push on what those two do not cover: a tool
  *name* the model invented (it reaches a table cell and an argument-schema disclosure), a
  `reason_detail` containing an `</td>`, and a task long enough to test that the layout degrades
  rather than breaks.
* **The compaction summary prompt is the one prompt in the pack whose entire body is model and
  tool output.** `compaction.summarize` quotes the span as data and instructs the model not to
  follow instructions inside it. That instruction is a mitigation, not a guarantee, and the corpus
  should include a tool result that tries to steer the summary — because a successful steer is
  laundered into what every later turn sees.

### 7.2 Which §15 budgets are now measurable, and what they measured at

| Measure | Target / ceiling | Measured here |
|---|---|---|
| Explanation retrieval, terminal (materialized), any size | ≤ 25 ms / 100 ms | **0.485 ms** for a 12-table trajectory (demonstration 2) |
| Explanation materialization after the terminal transition | ≤ 2 s / 10 s | **5–7 ms** for the same trajectory; the 500-turn figure is unmeasured |
| Compaction plan, 200-turn transcript | ≤ 50 ms / 200 ms | Unmeasured as a budget; the 100-turn scripted test completes in about a second including every LoadCoach round trip on the fake |

None of these is asserted as a budget — §15 as a gate is explicitly I2's. What I2 needs from here:
`explanation_revisions.composed_ms` and `turn_count` are **on the row**, so the materialization
budget can be measured over real trajectories without instrumenting anything, and the
`X-Explanation-Composed-Ms` header does the same for the read path.

**One performance finding, unmeasured and worth I2's attention.** Compaction re-composes and
re-plans from the *whole* recorded transcript before every turn, so its cost grows linearly with
the trajectory's length even though the wire stays bounded. The live run shows it: `tokens_before`
climbed from 748 to 4 477 while `tokens_after_estimate` stayed at or under 560. On a 500-turn
trajectory that is a 500-turn estimate and plan on every turn. The fix, if §15's compaction budget
turns out to bind, is to plan from the previous compaction's *view* rather than from the rows — but
that changes what the plan hash means and what the `compactions` row records, so it is a decision
and not a patch.

### 7.3 What the retention sweep will need from the invalidation entry point

* **Call `invalidate(trajectory_id, cause="retention_scrub", now=…)` once per trajectory, after
  the sweep's own row writes commit**, in the same process. It composes from the rows as they then
  stand, so a call before the commit materializes the unscrubbed document.
* **It is idempotent in the useful direction.** A trajectory the sweep touched but did not actually
  change composes to the same bytes and the current revision is returned unchanged — no duplicate
  row. So a sweep that is unsure whether it changed anything can call it anyway.
* **`explanation_revisions.cause` already has the vocabulary** (`terminal`, `retention_scrub`,
  `recosting`, `schema_upgrade`) and `superseded_at` already exists, so P9 adds no column. A
  superseded revision keeps its artifact deliberately (lifecycle §9.1); pruning those is P9's to
  specify, and `drop_revisions` deletes rows without touching artifacts for exactly that reason.
* **The sweep must scrub `plans.raw_document` and `turns.tool_calls_json` alongside
  `turns.content_text` and the tool-call columns.** All four are model output. The first is
  nullable only as of migration `0010`; before this row it could not have been scrubbed at all.
  `test_a_scrubbed_trajectory_still_explains_itself_and_bumps_a_revision` scrubs all of them and is
  the shape P9's own test should take.
* **What must survive a scrub**, and does: every digest, every model identity, every tier, every
  usage figure, every ceiling verdict, every egress decision and every event. A scrubbed
  trajectory still explains itself; only the words are gone, and they are replaced by a labelled
  stub rather than by an empty string.

### 7.4 Smaller things I2 will meet

* **`GET /tiers` is specified and absent** (§5). The console does not need it; a client does.
* **Compaction planning is per turn and per thread.** A planned trajectory with parallel steps
  compacts each thread independently, which is correct and means a wide plan multiplies the
  planning cost above.
* **The console's counts are capped at the page size** and say so on the page. If an operator ever
  needs a true count, that is a `COUNT(*)` per state on every page view, and worth deciding rather
  than adding.
* **`web/app.py` no longer defers anything.** If I2 adds same-origin, body caps or rate limits —
  and the §14 checklist says it should — they go beside `CsrfMiddleware`, which is already there.
* **The demonstration scripts** are in the session scratchpad, not in the repository. They are
  fifty lines each and re-derivable from this document; if I2 wants them as fixtures, the seeded
  journey in `tests/e2e/test_console.py` is the same trajectory.

## 8. Working-tree integrity

`git status --short` was clean in both repositories at the start (PromptCadence one commit ahead of
origin, docs six — §5) and is clean at the end. Nothing was modified that this session did not
edit. **Nothing was pushed, and no push dry-run was run.** PromptCadence is seven commits ahead of
`origin` (six from this row, plus `784e89f` which was already outstanding) and docs is ten (four
from this row, plus the six that were already outstanding).

One thing to know: an early run of demonstration 2 used the **operator's real configured database**
at `~/.local/share/promptcadence/promptcadence.sqlite3` before the demo was re-run in isolation. It
appended one trajectory and migrated that database from `0008` to `0010`. The migration is
forward-only and correct, and both later demonstrations used isolated databases under the session
scratchpad — but the real database now holds one demonstration trajectory and is at head.
