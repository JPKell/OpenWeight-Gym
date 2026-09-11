# Kickoff — I1: PromptCadence Phase 8 — compaction, the explanation document and its materialized revisions, and the operator console

**Row:** I1 of [`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · high**, as scheduled. The row's prose still describes a split ("materialization
— Opus; CutCtx wiring and the UI volume — Sonnet"); [model-assignment §3.5](../../roadmap/model-assignment.md)
abolished splits on 2026-09-04 and the prose is kept only to say **where the hard part is**. Run the
row whole.
**Repositories:** `/home/jpk/ai/suite/PromptCadence`, then `/home/jpk/ai/suite/WeightRoom/docs`.
**Ships:** **nothing.** `0.9.0b0` was cut at G1 and is on `main`; `1.0.0` is I2's. Everything this
row writes goes under `## [Unreleased]`. No bump, no tag, no publish, and **never `git push`** — not
even a dry run.
**Overnight:** the never-overnight list ([§2.12](../../roadmap/model-assignment.md)) names batches D and
G and I2's security half, and not this row. Take it as **daytime anyway**: the cache-consistency half
fails silently by definition — a materialized document that disagrees with the rows looks exactly
like a correct one until somebody diffs them — and the UI half is the first HTML this application has
ever rendered. If it must run unattended, run gates A–F unattended and leave G (the console) for a
reviewed session.
**Runs after:** G1 (Phase 7, done), G2 (tool wire, done), G3 (step retry, done — the hard edge
"`materialize(rows) == compose_live(rows)` must see step attempts in the shape the record will keep"
is satisfied) and E1 (`cutctx 0.1.0`, published).
**Not a dependency, and not yours:** **H5** (LoadCoach 1.1 + FreeWeight 1.1). It may or may not have
run before you. PromptCadence talks to LoadCoach over HTTP and pins no LoadCoach package, so nothing
in this row moves either way. Do not touch that repository.
**Not in this session:** the retention **sweep** itself (Phase 9 — development plan line 420), the
prompt-injection corpus, the §15 performance budgets as *gates*, the `1.0.0` release, and any live
remote-tier verification (I2, behind LC-E1).

---

## 0. Machine facts, verified 2026-09-06 before this prompt was written

Confirm the two marked **confirm**; do not re-derive the rest.

* **PromptCadence `main` is at `0f6734f`, clean and level with `origin`** — G3's commits were
  pushed by the operator, so unlike the last four rows you start with nothing outstanding.
  **docs `main` is at `ca020c8`**, clean and level. **Confirm** `git status -sb` in both repos at
  the start and at the end (CLAUDE.md, working-tree integrity), and `git checkout --` anything
  modified that you did not edit.
* **Interpreter: Python 3.13.15** at `PromptCadence/.venv/bin/python`. There is no `python3.12` on
  this host. Name the interpreter and every exact invocation in the handoff (M5C-13).
* **Resolved dependencies in the venv:** `baseaicore 0.4.1`, `setspec 0.5.0`, `mirrorwall 0.2.2`,
  `toolyard 0.1.0`, `loadledger 0.2.0`, `commissioner 0.1.0`. `setspec` resolves to 0.5.x because
  `commissioner 0.1.0` capped it; `commissioner 0.1.1` (published 2026-09-06) lifts that cap.
  **You do not need 0.6 for anything in this row — do not widen a pin to tidy it.**
* **`cutctx 0.1.0` is on PyPI** (confirmed: `GET /pypi/cutctx/json` → 200, version `0.1.0`) and is
  **not yet a dependency of PromptCadence**. Its only runtime dependency is `baseaicore`, already
  pinned. Adding `"cutctx>=0.1,<0.2"` is a normal pin, not a path install, and the comment block
  above `dependencies` in `pyproject.toml` (lines 24–25) is where the phase-by-phase note goes.
* **The highest ADR is `0085`.** Take `0086` onward, and check the directory again before you
  write one — another row may land first.
* **Nothing is listening on 8766 or 8768.** Both demonstrations below need you to start what they
  talk to. G1's trap still holds: four CLI tests read a live server if one is up on 8768, so stop
  every demo process before the gate run.
* **Migration head is `0008_step_attempts`.** New migrations start at `0009`. One migration per
  gate, never one per row (the H1/H2 rule).
* **`find src -name '*.html'` returns nothing.** PromptCadence has never rendered a page. The
  console is new construction, not an extension.

## 0.1 What already exists — read it before you build any of it

| Already built | Where |
|---|---|
| `[compaction]` settings — `threshold` (0.8), `policy_chain` (`observation_masking`, `summarizing`, `drop_oldest`), `protected_recent_turns` (4) — declared, validated, and **unused** | `config.py:371` |
| `Tier.context_budget_tokens`, the trigger's other input | `domain/tiers.py:145`, `:239` |
| `EventType.CONTEXT_COMPACTED = "context.compacted"` | `domain/events.py:54` |
| `ErrorCode.COMPACTION_FAILED` + `CompactionFailedError`, and LoadCoach's `CONTEXT_LIMIT_EXCEEDED` already mapped onto it | `domain/errors.py:70`, `:162`, `infrastructure/loadcoach.py:127`, `:754`, `:1014` |
| `artifact_root` — oversize output kept as an artifact under its digest, never truncated | `config.py:329`, `:828` |
| The prompt pack: `prompts/manifest.json`, `planner.draft` 1.1.0, `planner.corrective` 1.0.0, `step.execute` 1.0.0, with `prompt_id`/`version`/`sha256` recorded on the turn | `src/promptcadence/prompts/`, `services/prompts.py`, `turns.prompt_*` |
| Every row the explanation composes — `trajectories`, `plans`, `plan_steps`, `plan_approvals`, `approval_requests`, `execution_intents` (all revisions), `threads`, `turns`, `tool_call_records`, `ledger_entries`, `egress_decisions`, `deviations`, `events` | `infrastructure/db/models.py`, and the inventory in `G1_HANDOFF.md` §8 |
| SSE with persisted events and `Last-Event-ID` replay | `web/routes/trajectories.py`, `mirrorwall.sse_response` |
| Bearer auth with `read`/`write`/`approve` scopes and the open-loopback rule | `web/auth.py`, `services/tokens.py` |
| MirrorWall's UI half — `create_template_environment` (autoescape + `StrictUndefined`), `PACKAGE_TEMPLATE_DIR`, `PACKAGE_STATIC_DIR`, `mount_static`/`HashedStaticFiles`, `register_filters`, `CSRF_COOKIE_NAME`/`CSRF_FIELD_NAME`/`issue_csrf_token`, `CsrfMiddleware` | `py/MirrorWall/src/mirrorwall/{templating,static,filters,middleware}.py` |
| The console **precedent to copy the shape of, not the vocabulary** — a `rendering.py`, a `csrf.py` and nine template directories | `LoadCoach/src/loadcoach/web/` |

CutCtx's contract, which you consume and do not re-litigate: **plan → fulfil → apply**.
`DropOldestPolicy`, `ObservationMaskingPolicy`, `SummarizingPolicy`, `PolicyChain`, `default_chain`,
`CompactionBudget(budget_tokens, protected_recent_turns=…)`, `CompactionExecutor.apply(transcript,
plan, summaries=…)`, `SummarizationRequest`, `SummaryMissing`, `BudgetUnsatisfiable`. CutCtx never
calls a model, never touches a database and never mutates its input; a plan carrying a
`SummarizationRequest` that you apply without fulfilling raises `SummaryMissing` **by name** rather
than silently dropping the reduction the arithmetic already counted. The contiguous-group
dict-ordering trap is golden-tested **inside CutCtx** — do not re-test it here.

## 0.2 What is missing

1. **The compaction trigger and everything under it.** No `compactions` table, nothing emits
   `context.compacted`, nothing constructs a `Transcript`, `CompactionBudget` or policy chain, and
   nothing executes a `SummarizationRequest`. There is no compaction-summary prompt record.
2. **`ExplanationBuilder`,** the `promptcadence.trajectory_explanation` `1.0` schema and its
   goldens, `GET /trajectories/{id}/explanation`, and `promptcadence trajectory explain`.
   `web/routes/trajectories.py:192` and `services/records.py:7` both say so in a comment.
3. **`explanation_revisions`,** the artifact write, live composition for in-flight reads, the
   invalidation path, and `promptcadence db rebuild-explanations`.
4. **The whole console.** No base layout, no page, no template test, no static mount.
5. **Quietly missing, and it is the console's blocker rather than a nice-to-have:**
   `web/app.py:10` says plainly that *"there is no HTML UI yet (Phase 8), so CSRF and same-origin
   protection are not wired: the state-changing routes take JSON bodies and bearer-less loopback
   callers only, and a browser form cannot reach them."* An approvals **inbox** is a page with two
   buttons that POST. The moment it exists, that paragraph is false and the protection it defers
   is due. `mirrorwall.CsrfMiddleware` and `issue_csrf_token` exist; PromptCadence wires neither.

## 0.3 The five decisions this row must take, and record

Each of these is a decision, not a preference: write the ADR **before** the code it governs, and
say in the handoff which way you went and what the losing option would have claimed.

### D1 — Which tier, which task profile, and which intent the compaction summary runs under

[Lifecycle §7](../../apps/promptcadence/lifecycle.md) says the summary executes *"via LoadCoach
(`general.summarize`, on the trajectory's cheapest admissible local tier — a summary of confidential
turns must not itself become egress)"*. Three things in the built code pull against that sentence,
and they interlock:

* A PromptCadence tier is **configuration over exactly one LoadCoach task profile** (`config.py`
  `Tier`, ADR-0047). `general.summarize` is a real, shipped profile
  (`LoadCoach/src/loadcoach/config/task_profiles.toml:65`, `max_output_tokens = 1024`,
  `min_context_tokens = 8192`) but **no configured tier names it** — the two default tiers name
  `tools.agent.local_fast` and `tools.agent.local_large`. So "on tier X with profile
  `general.summarize`" is a combination the tier model does not currently express.
* `_tier_violation` (`domain/deviation.py:458`) raises when `facts.executed_tier not in
  intent.permitted_tiers`. A summary turn on the cheapest local tier, inside a step whose intent
  permits a different tier, **is a deviation** — and contract 1 says no turn executes without an
  intent to be checked against.
* The pre-flights (egress, pricing, availability, budget — ADR-0073) run before `turn.started`.
  The summary is a turn, so it has its own.

Candidates, and the second is the one to beat: (a) run the summary on the step's own tier and let
the tier's profile stand — cheapest to build, and it silently discards the "cheapest admissible
*local*" property that exists so a confidential transcript's summary is not egress; (b) **mint the
summary's own intent revision** by `supersede`, naming the summarizing tier and carrying the step's
classification ceiling, so the summary turn is governed in its own right and the audit trail holds
the envelope it ran under — this is what G1's §13 already settled for the bypass grant, in the same
shape; (c) widen `permitted_tiers` at mint time to include the summarizing tier — one line, and it
weakens every step's envelope for a turn that may never happen.

Whatever you pick: **no summary turn may execute under no intent, and none may execute outside the
envelope of the trajectory it is summarizing.** Write that assertion first.

### D2 — Whether the summary turn is debited, and whether it counts against `max_turns_per_step`

Lifecycle §7 is explicit that the summarization call *"is itself a turn — debited, recorded,
explainable"*, so the debit is decided. What is not written down is the second half: `max_turns_per_step`
is the step's advance budget, and a compaction turn charged to it means a long step can be **ended
by its own housekeeping** — the loop sees `turns_used >= max_turns` and raises `turn_overrun`
(`G1_HANDOFF.md` §15c, `G3_HANDOFF.md` §9b) for a turn the caller never asked for. Decide it, state
it in lifecycle §7, and test the boundary either way.

### D3 — What invalidates a revision, when the thing that will invalidate it does not exist yet

Lifecycle §9.1 names three invalidators: the retention sweep, a ledger re-costing, and a
document-schema minor bump. **The retention sweep is Phase 9** (development plan line 420;
`config.py:156` says so too: *"the retention sweep arrives later"*). Build the **entry point** and
its revision bump now — a function the sweep will call, and the same for a re-costing — and test it
by scrubbing the rows directly in the fixture. Do **not** build the sweep: shipping a sweep this row
did not spec is how P9's acceptance criteria get quietly pre-empted, and a half-swept database is
worse than an unswept one.

### D4 — How a browser authenticates to the console, and what CSRF covers

Today: loopback with no token is open and holds every scope; once any token exists, every scoped
endpoint needs a bearer header (`web/auth.py`). A browser has no bearer header. Either the console
is loopback-only and says so, or it grows a session cookie — and a session cookie is a security
surface this row would be inventing at the end of a long phase. LoadCoach's precedent is the cheap
answer; take it unless you find it does not fit, and either way wire `CsrfMiddleware` and rewrite
`web/app.py`'s docstring paragraph in the same commit that renders the first form.

### D5 — Where materialization runs relative to the terminal transition

Lifecycle §9.1 says *"the same transaction's follow-up work composes the document once"*. ADR-0044
says a state change and its event are **one write**, and §15 budgets materialization at ≤ 2 s
(ceiling 10 s) for a 500-turn trajectory. Two seconds of composition inside the transition's
transaction is two seconds of lock. Decide: inside, or immediately after under its own write — and
if after, say what happens when the process dies in between. The honest answer is available and
should be stated rather than assumed: **a missing revision is not a missing explanation**, because
the live composition path serves it and `rebuild-explanations` fills it in. If that is the answer,
then the revision genuinely is a cache and the tests should prove it by deleting every row of
`explanation_revisions` mid-suite and asserting every read still answers identically.

## 1. The seam the compaction trigger plugs into

`LoopController` builds the wire transcript at **`services/loop.py:1786`** —
`messages=self._transcript(run.thread_id, turns)` — inside the same method that writes
`turn.started` and calls `self._loadcoach.generate(...)`. `_transcript` (`:1893`) is where the
recorded turns become `Message`s, and it does one thing you must not break:

> **Tool-call ids are matched positionally.** An assistant turn's `tool_calls_json` supplies a
> `pending` list of call ids, and the following `TOOL` turns pop from it in order. Drop or mask an
> assistant turn while keeping its tool turns and the mapping silently shifts — every tool result
> answers the wrong call, and LoadCoach accepts it because the ids are well-formed.

CutCtx's invariants keep a call and its result together, which is what makes this safe — but it is
safe only if the compaction acts on the **turn sequence before `_transcript` maps it**, or if
`_transcript` is rebuilt to key by call id rather than by position. Pick one deliberately and put a
test on it: a compacted transcript whose assistant turn was dropped, asserted at the `Message`
level, not at the plan level.

Two more properties of the seam, both from lifecycle §7:

* **Compaction is per step thread.** `threads.step_id` exists and a planned trajectory has one
  thread per step (`G1_HANDOFF.md` §8). The budget is the tier's `context_budget_tokens`; the
  trigger is `estimate > threshold × budget`.
* **Compaction is a view, never a deletion.** Every original turn stays in `turns`. What changes is
  what goes on the wire. The `compactions` row plus `context.compacted` (before/after estimates,
  the turns affected) is the record that the view differed from the rows — and the explanation
  reads it, because otherwise a reader cannot tell why turn 40 saw less history than turn 39.

## 2. Gates

One Conventional Commit per gate, in this order. Docs move **before** the code they govern.

| Gate | What it makes true |
|---|---|
| **A** | The ADRs for D1–D5, accepted, indexed in `docs/adr/README.md`; lifecycle §7 and §9.1, spec §9/§11 contract 2/§13/§15/§17 and the development plan amended to match; **mirrors `cmp`-identical** |
| **B** | `cutctx` pinned; `compactions` table + migration `0009`; the trigger, the transcript mapping and the policy chain wired against a scripted LoadCoach; `context.compacted` written in the same write as the row |
| **C** | The summary executed through LoadCoach under D1's decision, with its prompt record in the pack (`manifest.json` regenerated, `pack_sha256` recomputed) and its debit under D2's; `COMPACTION_FAILED` when the chain cannot fit (`BudgetUnsatisfiable` → the typed error, not a traceback) |
| **D** | `ExplanationBuilder` and the `promptcadence.trajectory_explanation` `1.0` schema under the ADR-0035 namespace, with goldens; the composed document written as an artifact under its digest |
| **E** | `explanation_revisions` + migration `0010`; materialize at the terminal transition per D5; live composition for in-flight reads; **the `materialize(rows) == compose_live(rows)` equality golden**; invalidation + revision bump per D3; `promptcadence db rebuild-explanations` |
| **F** | `GET /trajectories/{id}/explanation`, `promptcadence trajectory explain`, the OpenAPI snapshot updated, the error ladder and the scopes checked |
| **G** | The console: base layout, dashboard, trajectory list, timeline detail, approvals inbox, tiers, tools, ledger, egress, system; CSRF and D4's answer; SSE live updates; the template render suite and the accessibility checks the UI standards name |
| **H** | Full gate green, both demonstrations run, `CHANGELOG.md` under `## [Unreleased]`, handoff written |

## 3. The traps, named

Every one of these is somebody's already-paid-for finding. None is hypothetical.

* **A failed attempt has a `turn.started` event and no `turns` row** (`G3_HANDOFF.md` §7). Compose
  the **attempt list from `step.retried`** and the **turn list from `turns`**; do not make one
  source serve both. Join by `step.retried.failed_turn_id`, never by adjacency.
* **Compose from an explicit flag, never from emptiness** (`G1_HANDOFF.md` §8). An invalid plan
  attempt has `validated_json = {}` **and** `issues_json` set — read `valid`.
* **`threads` for a trajectory order by `created_at` then `id`** — ties are real under the
  millisecond clock, and an unordered pair is a document that differs between two composes of the
  same rows. That is the equality golden failing intermittently, which is the worst way to find it.
* **`plans.raw_document` and `turns.tool_calls_json` are model output** and must follow the
  retention scrub exactly as transcript text does. An explanation that survives a scrub by keeping
  a copy of the scrubbed text has defeated the scrub.
* **A bypass gate's `approval_requests` row carries `step_ids = ["loop"]`** — do not look that up
  in `plan_steps` (`G1_HANDOFF.md` §15a).
* **The planner's spend is on the `plans` row, not the ledger** (`G1_HANDOFF.md` §13). The
  explanation reports it from there; it is not a missing debit.
* **Determinism is the deliverable, not a nicety.** The document must be byte-identical across
  composes: fixed key order, timestamps rendered from stored values and never from `now`, no
  dict-iteration dependence, no `set` in a serialized position. The equality golden is only as
  strong as this.
* **`StrictUndefined`** — a missing template variable raises rather than rendering blank. That is
  deliberate (ADR-0016's reasoning arriving through the template layer); do not swap it out to make
  a page render.
* **`lint-imports`** — `domain` imports no framework. The document *assembler* can be pure and
  belongs in `domain`; the part that reads rows is `services`. Do not let a Jinja or SQLAlchemy
  import cross into `domain` to save a parameter.
* **Stop every demo before the gate run** — four CLI tests read a live server on 8768 if one is up
  (`G1_HANDOFF.md` §14.6).
* **`pytest-randomly`** — a failure that only reproduces under one seed is a real bug. `-p
  no:randomly` isolates; it never fixes.

## 4. What must not be relitigated

`G1_HANDOFF.md` §13 in full, and specifically: the bypass grant **supersedes**; the contract-1
allowance list is closed and a new difference is a **finding**, not an allowance; `observed_classification`
is the intent's ceiling until an operator-flagged path exists; the remote-provider fact is a seam
with a safe default and is never inferred from a provider kind. Add G3's: the retryable set is
structural, not a list, and nothing this row does may make a governance refusal repeatable.

## 5. The two demonstrations

Tests are not the acceptance criterion — the development plan says *"the UI timeline renders every
record type from a seeded database"*, and criteria must be demonstrable.

1. **Compaction, live.** Start a real LoadCoach on 8766 against Ollama, configure a tier with a
   deliberately small `context_budget_tokens`, and run one trajectory that crosses the threshold.
   Show: the `context.compacted` event with before/after estimates, the summary turn recorded with
   its own tier, intent reference, usage and debit, and the trajectory completing inside the tier's
   budget. A 100-turn scripted trajectory against the fake proves the arithmetic; this proves the
   wiring. Run both.
2. **The console, seeded.** Seed a database holding every record type — planned and bypassed
   trajectories, a rejected plan, a granted and a denied approval, a retried step, a tool call of
   each `ToolOutcome`, a deviation, an egress denial, a compaction, a completed and a halted
   trajectory — and walk the timeline page. Every one of those must render as something a person
   can read, and the explanation for the terminal trajectory must come back from the materialized
   revision. Then delete every `explanation_revisions` row, reload, and get the identical document.

## 6. Exit conditions

| # | Condition |
|---|---|
| 1 | D1–D5 taken as accepted ADRs, docs amended **before** the code, mirrors `cmp`-identical |
| 2 | The trigger fires from `[compaction]` against the tier's `context_budget_tokens`, per step thread, with `compactions` + `context.compacted` written in one write |
| 3 | The summary runs under an intent, on a local tier, debited and recorded, with its prompt record in the pack; no path executes a summary turn ungoverned |
| 4 | A tool call and its result are never separated, asserted at the `Message` level after a compaction that drops an assistant turn |
| 5 | `COMPACTION_FAILED` when the chain cannot fit; `SummaryMissing` unreachable from the loop |
| 6 | `promptcadence.trajectory_explanation` `1.0` with goldens; the document names every model, tier, tool call, debit and egress verdict — spec §20 #2's explanation clause |
| 7 | `materialize(rows) == compose_live(rows)` for every fixture trajectory, **and** after a simulated retention scrub and after a re-costing, each bumping a revision |
| 8 | Dropping the whole revision table and rebuilding reproduces identical documents; a scrubbed trajectory still explains itself |
| 9 | Both surfaces (HTTP + CLI), OpenAPI snapshot updated, scopes enforced |
| 10 | The console renders every record type from the seeded database; CSRF wired; `web/app.py`'s "no HTML UI yet" paragraph rewritten to be true |
| 11 | Full gate green — `ruff format --check . && ruff check . && mypy src tests && lint-imports && pytest -m "not live and not performance"` — coverage at or above the 85 % application floor, interpreter and invocations named |
| 12 | Both demonstrations run, with what was seen written down |

## 7. The handoff

`docs/history/handoffs/I1_HANDOFF.md`, in the house shape: gate results with the exact invocations; the gates
as commits; each of D1–D5 with the reason and what the losing option would have claimed; the exit
conditions with results; **things this prompt said that turned out not to be true**; and read-only
notes for I2 — specifically (a) what the injection corpus should attack in the composed document and
the console (model output reaching a template is a new surface this row creates), (b) which §15
budgets are now measurable and what they measured at, and (c) anything the retention sweep will need
from the invalidation entry point that P9 would otherwise have to discover.

Mark the I1 row done in `docs/roadmap/outstanding-work.md` in the docs commit, and update
`CHANGELOG.md` under `## [Unreleased]`.
