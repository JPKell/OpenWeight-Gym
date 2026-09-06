# Kickoff — I2: PromptCadence P9 — hardening, the injection corpus, the budgets, the docs set, and 1.0.0

**Row:** I2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Opus 5 · xhigh**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
The row's note *"consider Fable 5 for the injection corpus"* is the operator's call at kickoff, not
yours mid-session; whatever runs, record the deviation ([model-assignment §3.5](docs/roadmap/model-assignment.md)).
**Never overnight.** [outstanding-work §2](docs/roadmap/outstanding-work.md) names this row's
security half explicitly: it is won by review and fails silently.
**Repositories:** `/home/jpk/ai/suite/docs` first (gate A), then
`/home/jpk/ai/suite/PromptCadence`. `py/ToolYard` only if gate D finds something in it (§0.5).
**Ships:** **`promptcadence 1.0.0` prepared, not published.** The version bump, the changelog move
and the release commit are yours; **`git push`, the tag and the publish are the operator's**
(standing instruction of 2026-09-04). Do not run a push dry-run.
**Runs after:** **I1** (PromptCadence P8) and **H2**. H2's half is done (§0.2). **I1 is not
built — read §0.1 before anything else.**
**Runs before:** J1, J2, J3. Adoption targets a released 1.0, never a moving target
(ADR-0011, `outstanding-work` §3).
**Not in this session:** LoadCoach, ModelRack, FreeWeight, IdeaPress, and H5's two releases. This
row consumes LoadCoach; it does not change it.

---

## 0. Machine facts, verified 2026-09-06 before this prompt was written

Confirm the two marked; do not re-derive the rest.

* **PromptCadence `main` is at `0f6734f`** ("test(loop): the retry's record, on both paths, with
  contract 1 unchanged"), clean and level with `origin`; `__about__.py` says `0.9.0b0`.
  **Confirm** `git status -sb` in `PromptCadence` and `docs` at the start and at the end.
* **Confirm whether `promptcadence 0.9.0b0` is on PyPI.** It was cut at G1 (`c9ed99a`) and left for
  the operator to publish. Phase 9's test list wants an **upgrade test from `0.9-beta`**; whether
  that installs from PyPI or from a locally built wheel depends on this answer, and the answer is
  one `pip index`/`pip download` away. Do not assume either.
* **The two `[server]` limits are declared and enforced nowhere.** `config.py:123`
  `rate_limit_per_minute: int = 600` and `config.py:124` `max_body_bytes: int = 1_048_576` appear in
  the settings model and in the generated example file (`config.py:762`–`:763`) and **in no other
  module** — `grep -rn "rate_limit_per_minute\|max_body_bytes" src/promptcadence --include=*.py`
  outside `config.py` returns nothing. A configured limit that nothing reads is worse than an
  absent one: `doctor` and the config reference will both report it as set. LoadCoach's
  `src/loadcoach/web/rate_limit.py` is the precedent to port, and `tests/security/test_rate_limit.py`
  beside it is the test shape.
* **The retention sweep does not exist, and the config says so.** `config.py:154`–`:157`:
  `retain_content` is documented as *"Config-only switch mirroring LoadCoach's; the retention sweep
  arrives later."* Later is this row. `content_retention_hours` (`config.py:146`) is likewise read
  by nothing. Precedent: `loadcoach/services/retention.py`, swept from the worker
  (`loadcoach/services/worker.py:446`, `:456`). **Spec §14 says the sweep includes workspaces** —
  `[tools] workspace_root` (`config.py:326`, default `<data>/workspaces`, a subdirectory per
  trajectory) is content on disk, not just rows.
* **There are no `tests/security/`, `tests/performance/` or `tests/accessibility/` directories.**
  The markers exist (`pyproject.toml:129` `addopts = "-m 'not live and not performance'"`, `:131`
  the marker table), so the wiring is there and the suites are not. LoadCoach carries
  `tests/security/{test_checklist,test_scopes,test_rate_limit,test_queue_cap}.py`,
  `tests/performance/{test_generate_overhead,test_queue_budgets,test_routing_budgets,test_streaming_gap}.py`
  and `tests/accessibility/test_ui_checklist.py`.
* **No OpenAPI snapshot.** The only `openapi` JSON in the repo is
  `tests/contract/loadcoach_openapi.json`, which is **LoadCoach's**, consumed by I10's contract
  test. PromptCadence's own snapshot does not exist. Precedent: `LoadCoach/docs/openapi.json` plus
  `LoadCoach/tests/contract/test_openapi_snapshot.py`.
* **No configuration reference, generated or otherwise.** `cli/commands/config.py` has no
  `reference` command. Precedent: `loadcoach/services/config_reference.py`, rendered from
  `loadcoach/cli/commands/config.py:150`, diff-checked by `LoadCoach/tests/unit/test_config_reference.py`,
  output committed as `LoadCoach/docs/configuration.md`.
* **No operator documentation set.** `PromptCadence/docs/` holds only the three mirrored documents
  (`apps/promptcadence/{spec,development-plan,lifecycle}.md`). LoadCoach's repo `docs/` is the
  template: `quickstart.md`, `configuration.md` (generated), `operations.md`, `security.md`,
  `routing.md`, `troubleshooting.md`, `upgrading.md`, `openapi.json`, `README.md`.
* **`requirements/` has `release.in` + `release.lock` and no `ci.lock`**, and CI installs
  `-e ".[dev]"` (`.github/workflows/ci.yml:33`, `:42`). The row wants `ci.lock` cut and audited.
  `requirements/README.md` already names the shape *and the trap*: a path-based coverage `source`
  reports 0 % against a non-editable install. Read that file before cutting the lock, not after.
* **Security surface that already exists, and must be verified rather than rebuilt:** scopes and
  the loopback principal (`web/auth.py`, `services/tokens.py`; `approve` is its own scope,
  ADR-0049 rule 2), the Host-header allowlist and request-ID middleware from MirrorWall
  (`web/app.py:227`–`:228`), the egress pre-flight order (ADR-0073), `doctor`
  (`services/diagnostics.py`, `cli/commands/system.py`).
* **The highest ADR in `docs/adr/` is `0085`.** H5 may take `0086` before this row runs; check the
  directory rather than trusting this line.
* **Coverage floor is 85 %** (`pyproject.toml:147`, application). `pytest-randomly` is on.
* **Python: check PromptCadence's own venv and name it** (M5C-13), with the exact invocations.
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to the
  operator.

## 0.1 The block — check this at minute one

**I1 (PromptCadence P8) is not built, and three of this row's items are certifications of P8's
output.** The evidence, all from `0f6734f`:

* No compaction service, no `compactions` table, no `context.compacted` emitter, no
  `ExplanationBuilder`, no `explanation_revisions`, no `promptcadence db rebuild-explanations`
  (`cli/commands/db.py` has `upgrade`, `status`, `backup`, `restore` and nothing else).
* `cutctx` is still not a dependency — `pyproject.toml:24` says so in prose: *"cutctx, loadledger
  and commissioner are not dependencies yet; each is added when the phase that consumes it
  arrives."*
* No operator UI: `web/routes/` is five JSON route modules, and there are no templates.
* No `docs/history/I1_HANDOFF.md`, and row I1 in `outstanding-work` §1 carries no **Done** note.

What that costs this row if it is ignored:

1. **Two of the ten spec §15 budgets are explanation budgets** — *explanation retrieval,
   terminal trajectory (materialized), any size* ≤ 25 ms, and *materialization at terminal
   transition, 500-turn trajectory* ≤ 2 s — and a third, *compaction plan, 200-turn transcript*
   ≤ 50 ms, measures a component P8 builds. Three of ten cannot be measured, so *"every §15 budget
   measured and asserted"* cannot be met.
2. **CSRF on every form** (spec §14, plan Phase 9) has no forms to protect until P8's UI exists,
   and neither does the accessibility suite the UI standards require.
3. **`cutctx 0.2.0` from real-transcript findings** presupposes a real transcript passing through
   CutCtx, which happens first at P8.
4. Spec §20 #2 requires the explanation *"naming every model, tier, tool call, debit and egress
   verdict"* — the acceptance criterion this row certifies is P8's deliverable.

**So: do not start I2 before I1.** If the operator schedules it anyway, that is a scope decision
and it must be *recorded*, not absorbed: name in the handoff exactly which gates ran degraded,
which §15 rows were not measured, and what the 1.0 changelog therefore says. A 1.0 whose exit is
partly unproved is the failure mode H2 stopped for (`docs/history/H2_HANDOFF.md` §0.5) and the one
M7 caught (`docs/history/M7_HANDOFF.md`).

## 0.2 The remote-tier fork — I13, or the recorded release-scope decision

**H2 delivered the half this row needs.** `docs/history/H2_HANDOFF.md` §272: LC-E1 is built —
`[providers.<name>]` with a **declared** `remote` flag is configurable, discovered, tagged and
routable (gate B, migration `0008`), and PromptCadence's two `tools.agent.remote_*` profiles will
now select a remote registration instead of returning `NO_ELIGIBLE_MODEL`. H2's gates D–I are open,
but none of them is this dependency.

**I13** ([roadmap §9](docs/roadmap/promptcadence-roadmap.md)) is: with one local **and** one remote
provider registered, a `remote_cheap`-tier step routes to the remote model with the egress badge and
the cost factor in LoadCoach's own explanation, and a local tier never does — **recorded transport in
CI, one marked live run**.

Two halves, and they fail differently:

* **The recorded-transport half is not optional.** It needs no key, no network and no money, and it
  is the half that proves the routing, the badge, the `EgressDecision` row and the cost factor.
  Build it whatever happens to the live half.
* **The live half needs a real OpenAI-compatible endpoint and its key, which only the operator can
  supply.** Ask at kickoff. If it is not available, take **the recorded release-scope decision the
  plan already sanctions** (Phase 9 *Known risks*; [roadmap §10](docs/roadmap/promptcadence-roadmap.md)
  risk row *"LC-E1 slips"*): 1.0 ships with remote tiers **refusing honestly**, because the refusal
  *is* specified behaviour. Recorded means: written into the handoff and the changelog, visible in
  `doctor` and in the `tiers` health component with a reason, and named as a decision with its date
  — *"not improvised"* is the roadmap's word.

**One trap on the live half.** Spec §20 #5: a remote tier with **no pricing record** refuses with
`UNPRICED_EGRESS_REFUSED` *before any call*, and ADR-0073 puts egress and pricing ahead of
availability. So a live remote run against a tier you did not price proves criterion 5 and not I13.
Price the endpoint in the ADR-0072 pricing file first, or you will demonstrate the wrong thing and
believe you demonstrated the right one.

## 0.3 The decisions this row must take, and record

New ADRs start after the highest number present when you look (§0). Amend an existing ADR only if
one genuinely covers the ground; ADRs are superseded, never edited.

1. **What "the injection corpus is a release gate" means.** Decide, before writing a case: a case
   asserts a **model-independent property** of the harness, never a model's compliance. The
   properties are already spec §14's list — only registry-listed tools are callable whatever the
   model asks; arguments are schema-validated then sandbox-checked; egress is evaluated from the
   **trajectory's declared classification, never from model text**; no model output reaches a shell
   command, a path outside containment or a fetch URL that skips ADR-0026 §3. Decide what runs
   against the fake LoadCoach (all of it, in CI, deterministic) and what runs marked-live against
   gpt-oss:20b (the corpus is a gate on the *harness*, and a live pass is evidence, not the gate).
   A corpus that fails when a model gets more obedient is a broken gate.
2. **The cap on replayed tool-call arguments** — G2's moved hazard,
   `docs/history/G2_HANDOFF.md` §10, left to this row on purpose. `tool_calls[].arguments` is
   uncapped model output going back onto the wire as structured JSON; `_recorded_name` caps names
   on events and `tool_call_records.args_sha256` stores the digest, but **the replay carries the
   whole thing**, and nothing in PromptCadence, LoadCoach or ModelRack caps it. Decide the bound,
   where it applies, and what happens at the bound — refuse the turn, or truncate and record the
   truncation. Whichever: the record must say which, because a silently shortened argument is a
   record that lies.
3. **Which §15 budgets are asserted, and against what.** Decide target-versus-ceiling (the ceiling
   is the failing bound; the target is the report), how many iterations and which statistic, and
   which rows are CI-asserted under the `performance` marker versus measured once on the reference
   machine and written down. LoadCoach's `tests/performance/` is the precedent for the shape.
4. **The remote-tier release scope** (§0.2), recorded at M12 with its date and its reason.
5. **G3 left one ordering question that is a spec question, not a test question**
   (`docs/history/G3_HANDOFF.md` §9b): a `turn_overrun` deviation and `STEP_LIMIT_EXCEEDED` can both
   fire on the same turn, and today the limit halts first. Settle which is correct and say so in the
   spec, or record explicitly that 1.0 ships with the current order deliberately.

## 0.4 What this row inherits from the four rows before it

* **G1 §8** — the injection vectors, named by the session that built the planner: plan step
  **descriptions are free text (≤ 2000 chars) quoted verbatim into the executing model's context**;
  `depends_on` and `step_id` are validated against the plan only; `max_plan_steps` bounds the count
  and LoadCoach's `max_output_chars` the document. G1 §460 adds one case by name: **a plan whose
  descriptions embed `[tool_calls]` text** — the prefix the old replay used.
* **G2 §9** — the fake LoadCoach now carries `tools` and `tool_calls` and copies the real refusals,
  so a hostile-model journey can script a **declared** call, a declared call with hostile arguments,
  and an invented name, through the same journey. `undeclared_tool` is now testable against a model
  that was told the truth. The sandboxed-tool clause of spec §20 #2 **holds on the real stack** —
  six declared calls, all `ok`, zero deviations — so this row verifies a path that runs.
* **G2 §10** — tool **descriptions** now travel to the model too, and are caller-written prompt
  content. In this suite they come from ToolYard's registered specs and are not model text, *"which
  is exactly the property the corpus should assert rather than assume"*.
* **H2.2 §7** — LoadCoach now returns `output.tool_calls_assembled`, so PromptCadence's client can
  drop its own grouping (`assemble_tool_calls`, keyed on `call_index` since G2) and read the
  assembled field; the fragment field stays until LoadCoach 2.0. Optional cleanup, not a gate — but
  it deletes code that one caller already got wrong once.

## 0.5 ToolYard and CutCtx 0.2.0 — findings only

Phase 9 lists *"package hardening feedback: `cutctx`/`toolyard` 0.2.0 from real-transcript and
security-pass findings"*. That is **conditional work**: if gate D finds a defect that belongs in
ToolYard rather than in PromptCadence, fix it there, cut `toolyard 0.2.0`, and re-pin. If it finds
none, there is no 0.2.0 to cut and the roadmap's version table is a plan, not a promise — say so in
the handoff. CutCtx feedback presupposes I1 (§0.1).

---

## 1. Setup

```bash
git -C /home/jpk/ai/suite/docs status -sb && git -C /home/jpk/ai/suite/docs log --oneline -3
git -C /home/jpk/ai/suite/PromptCadence status -sb && git -C /home/jpk/ai/suite/PromptCadence log --oneline -3
source .venv/bin/activate && pip install -e ".[dev]"
python -V && pip show setspec toolyard loadledger commissioner mirrorwall | grep -E "^(Name|Version)"
ls docs/adr | tail -3   # from /home/jpk/ai/suite/docs — the next ADR number
```

Every scratch database, config file, workspace, corpus fixture and log goes in the session
scratchpad — **never** the repository, never the workspace root, never `/tmp` directly.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory. Nothing at the workspace root is versioned; do not overwrite a
  root file you did not create.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, `CHANGELOG.md` updated, **one Conventional
  Commit per gate**, committed at each gate boundary.
* `pytest-randomly` is on; a seed-only failure is a real bug, not a flake.
* House method: docstring-first (behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names, keyword-only optionals and booleans, frozen slotted value objects, pydantic wire
  models, SQLAlchemy models never leaving the repository layer, `mypy --strict`, line length 100.
* `web → cli → services → domain`; `domain` imports no framework and no `httpx`. Never weaken
  `.importlinter`.
* **A state change and its event are one write** (ADR-0044).
* **Never `git add -A`.** Stage named paths. Every workspace `docs/` edit is mirrored into
  `PromptCadence/docs/` byte-identically and **`cmp`-proved**.
* Read `architecture/master-architecture.md` §§1–3 and PromptCadence's gold-standards section
  before the reading list below.

## 3. Reading list, in this order

1. `docs/apps/promptcadence/development-plan.md` **Phase 9** (this row), and **Phase 8**'s
   acceptance criteria — the thing this row certifies.
2. `docs/apps/promptcadence/spec.md` **§14** (the security posture, item by item — this is the
   checklist), **§15** (the ten budgets), **§18** (the test-strategy table at full depth: the
   Security and Performance rows are this row's), **§20** (the eleven acceptance criteria),
   **§12** (configuration — `[server]`, `[storage]`, `[tools]`), **§13**, **§17**, **§19**.
3. `docs/roadmap/promptcadence-roadmap.md` **§9** (I10, I12, **I13**), **§10** (the risk table —
   two of its rows are this row's decisions), **§3**'s M12 exit condition, **§8**'s version table.
4. Handoffs, in this order: **`docs/history/G1_HANDOFF.md` §8** (the vectors) and **§13** (what must
   not be relitigated); **`docs/history/G2_HANDOFF.md` §9 and §10**; **`docs/history/G3_HANDOFF.md`
   §7 and §9**; **`docs/history/H2_HANDOFF.md` §272** and **`H2_HANDOFF.2.md` §7**; and I1's handoff,
   which will be the newest and the most relevant of them.
5. Standards: Security Standards **§11** (locks) and **§14** (the checklist this row holds),
   Packaging and Release Standards **§4**, the UI standards' accessibility section (if P8's UI
   exists), ADR-0026 §3 (fetch rules), ADR-0018 (isolation tiers), ADR-0072 (the pricing file),
   ADR-0073 (pre-flight order), ADR-0049 (scopes).
6. The code, before designing against it: `config.py:113`–`:160` and `:320`–`:335`,
   `web/app.py:200`–`:235`, `web/auth.py`, `services/tools.py` (workspace containment),
   `services/loop.py` (the turn body and the tool replay), `services/egress.py`,
   `services/pricing.py`, `services/diagnostics.py`.
7. The LoadCoach precedents, by path, so you port rather than invent: `web/rate_limit.py`,
   `services/retention.py` + `services/worker.py:446`, `services/config_reference.py` +
   `cli/commands/config.py:150` + `tests/unit/test_config_reference.py`, `docs/openapi.json` +
   `tests/contract/test_openapi_snapshot.py`, `requirements/README.md` + `ci.lock`,
   `tests/security/`, `tests/performance/`, `tests/accessibility/`, and the seven operator
   documents in `LoadCoach/docs/`.

---

## 4. The shape of the work — nine gates

A documents and ADRs · B the security checklist · C retention · D the injection corpus ·
E the argument cap · F the budgets · G the remote tier · H the operator set and the release commit ·
I the independent verification. One commit per gate; the tree clean at every boundary.

## 5. Gate A — the documents, before any code

The §0.3 decisions as ADRs, accepted, each stating what it **refuses**. `spec.md` amended where a
decision changes it (§14's cap, §15's assertion policy, §18's Security and Performance rows, §13 if
a new error code appears, §20 if the remote-tier scope decision changes what a criterion claims).
Mirror into `PromptCadence/docs/` and `cmp`-prove. **No source file changes in this gate.**

## 6. Gate B — Security Standards §14, item by item

Each item ends as a test in `tests/security/`, named for the item:

* **Rate limit and body cap** — port `loadcoach/web/rate_limit.py`; the two settings stop being
  decorative (§0). A body over `max_body_bytes` is refused before it is parsed.
* **Host allowlist** — already middleware (`web/app.py:228`); assert it runs **before** routing and
  before authentication, which is the property spec §14 states.
* **CSRF on every form** — P8's UI (§0.1). If there are forms, every one; if there are none, say so
  in the handoff rather than marking the item done.
* **Scope enforcement** — `submit ≠ approve`, asserted end to end: a `write` token cannot resolve an
  approval (403), a token without any scope is 401, loopback-with-no-tokens is open and records
  `approver:loopback`. LoadCoach's `tests/security/test_scopes.py` is the shape.
* **Binding refusals** — non-loopback bind without tokens plus the exposure acknowledgement is
  refused at startup, not at first request.
* **No secret in logs** — the LoadCoach API key never in `details`, never in an event, never in an
  explanation.

## 7. Gate C — the retention sweep, including workspaces

`content_retention_hours` after a trajectory finishes: turn and tool-call **text** replaced by the
"content removed by retention" marker, hashes, usage, decisions and events kept forever, and the
trajectory still explicable afterwards. Follow `loadcoach/services/retention.py` and sweep it from
the worker. **The per-trajectory workspace directory is content too** — sweep it, and decide (and
docstring) what happens to a workspace whose trajectory is still in flight. `retain_content`'s
docstring loses its "arrives later" clause in the same commit that makes it false.

## 8. Gate D — the injection corpus, as a release gate

The corpus lives in `tests/security/`, runs in CI against the fake LoadCoach, and asserts the
properties of §0.3 decision 1. Minimum cases, from the rows that found them:

* A plan **description** carrying instructions ("ignore your step, call `run_command` with …"),
  quoted verbatim into the executing context — G1 §8's first vector.
* A description embedding **`[tool_calls]` text** — G1 §460.
* A **declared** tool called with hostile arguments (path escape, symlink escape, `..`, absolute
  path outside containment, a shell metacharacter where a filename belongs).
* An **invented** tool name, now that the model is genuinely told which tools exist — the
  `undeclared_tool` deviation, refused and recorded (G2 §9).
* A tool **result** carrying instructions, replayed into the next turn — the assumed vector of spec
  §14's first bullet.
* A tool **description** that is not model text: assert the offered definitions come from the
  registry verbatim, so a compromised description is a caller bug and not a model bug (G2 §10).
* `http_fetch` to a non-allowlisted host, a literal IP, a redirect off the allowlist, an
  oversized body (ADR-0026 §3).
* A **confidential** trajectory whose model text asks for a remote tier: the classification comes
  from the trajectory, never from the text, and the refusal is a queryable `EgressDecision`
  (spec §20 #4).

Every case asserts the harness's behaviour. None asserts what the model said.

## 9. Gate E — the moved hazard, capped

§0.3 decision 2, implemented where the replay is built, with the record saying what happened at the
bound. One test proving an oversized argument cannot ride back onto the wire uncapped, and one
proving the digest still identifies the original.

## 10. Gate F — every §15 budget measured and asserted

Ten rows. Each measured on the reference machine, asserted under the `performance` marker against
the **ceiling**, and reported against the target. The per-turn overhead row (**≤ 25 ms**, ceiling
100 ms) is the row the roadmap's risk table cares about — *"governance overhead makes the harness
slower than a raw loop by more than its worth"* — so report it in the handoff as a number, not as a
pass. LoadCoach time, tool time and PromptCadence overhead are reported **separately**, which spec
§15 requires and which is what makes the number meaningful.

**If a budget cannot be met, that is a finding, not a knob.** Record the measurement and take it to
the operator; do not widen the ceiling to make the suite green.

## 11. Gate G — the remote tier

The recorded-transport half of I13 in CI, always. The live half per §0.2's fork, with the pricing
record in place first. Either way the `tiers` health component and `doctor` say honestly what the
install can and cannot reach, and the changelog says the same thing in the same words.

## 12. Gate H — the operator set, the snapshot, the lock, the release commit

* The seven-document operator set, following LoadCoach's shape: quickstart, **configuration
  (generated and diff-checked, with its CLI command)**, operations, security/egress, backup and
  restore, upgrading, troubleshooting **aligned with `doctor`'s actual checks**.
* `docs/openapi.json` committed with a contract test that fails when the API moves.
* `requirements/ci.lock` cut and audited; read `requirements/README.md` first for the coverage trap;
  CI installs from the lock with `--require-hashes`.
* Upgrade test from `0.9-beta` (§0), clean-venv install from the lock, `pip-audit` and `gitleaks`
  clean.
* Gold-standards section verified item by item.
* The release commit: `1.0.0`, the changelog `[Unreleased]` block moved under the version, and the
  `0.9.0b0` *Known limitations* list revisited line by line — the sandboxed-tool clause (closed at
  G2), the unbuilt step retry (closed at G3), the open podman condition (D1 — still open unless
  someone verified it). **No tag. No publish. No push.**

## 13. Gate I — the independent verification, with permission to say NOT READY

Phase 9 acceptance criterion 1, and the M7/M8 precedent: a verification run on an **independent
brief** — a real task neither this session nor the corpus was written around — against real
LoadCoach + Ollama, with explicit permission to conclude **not ready**. M7 concluded exactly that,
and the row was better for it (`docs/history/M7_HANDOFF.md`). Run it last, run it whole, and report
what it did rather than what it was supposed to do.

## 14. Exit conditions — all of these, demonstrably

1. Every spec **§20** criterion 1–11 passes, each named with what proved it.
2. The injection corpus runs in CI and is a **release gate**; every case asserts a
   model-independent property.
3. Security Standards §14 held item by item, each with its test; the two `[server]` limits are
   enforced.
4. The retention sweep runs, including workspaces, and a scrubbed trajectory still explains itself.
5. Every §15 budget measured and asserted, reported target-and-ceiling; the ≤ 25 ms per-turn
   overhead reported as a number.
6. I13 done, **or** the release-scope decision recorded with its date, its reason and its honest
   refusal path — and the recorded-transport half green either way.
7. The operator documentation set, the OpenAPI snapshot, the generated configuration reference and
   `requirements/ci.lock` all committed; `pip-audit` and `gitleaks` clean; upgrade and clean-venv
   installs proved.
8. The independent-brief verification run, with its verdict stated plainly.
9. `promptcadence 1.0.0` prepared — bumped, changelogged, release-committed, **unpushed and
   untagged**.
10. Full gate green, interpreter and exact invocations named; `docs/` and mirrors `cmp`-identical.

## 15. Closing duties

1. Full gate; interpreter and exact invocations named (M5C-13).
2. **`I2_HANDOFF.md` at the workspace root**, house shape: gate results; each §0.3 decision with its
   reason and what the losing option would have made the record claim; the corpus inventory (case →
   property → where it is asserted); the ten budgets as measured numbers; the verification verdict
   verbatim; **what J1/J2/J3 inherit**; and **anything this prompt said that turned out not to be
   true**.
3. Update the **I2 row** in `docs/roadmap/outstanding-work.md` to Done — date, commits, what held,
   what did not — and update §5's M12 row.
4. Note for the operator, explicitly: the push list, and that the **tag and the publish** are
   theirs — `promptcadence 1.0.0` is M12's exit and the J rows wait on it.
5. Record any **model deviation** from the scheduled Opus 5 · xhigh, including the Fable-5 corpus
   option if it was taken ([model-assignment §3.5](docs/roadmap/model-assignment.md)).

## 16. Stop rules

* **Never overnight.** The security half fails silently; it is reviewed work.
* **Do not weaken a budget, a ceiling or a corpus case to reach green.** A failing budget is a
  finding for the operator. This row exists to prove the list, not to pass it.
* **Do not write a corpus case that asserts model behaviour.** It will pass today and rot.
* **Do not cut 1.0 with an unproved exit condition** (`docs/history/H2_HANDOFF.md` §0.5). If §0.1's
  block is live, the honest outcome is a recorded partial, not a version bump.
* **Do not relitigate closed decisions**: G1 §13's list, ADR-0073's pre-flight order, ADR-0056's one
  intent per turn, ADR-0075's `tools` constraint, G3's retryable set.
* **Do not touch LoadCoach, ModelRack, FreeWeight or IdeaPress**, and do not widen a `setspec` pin.
  ToolYard only under §0.5, and only on a finding.
* **Do not add a runtime dependency** to reach a gate. Nothing here needs one.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a gate boundary. **Never `git push`, tag or publish.**

## 17. If you finish with capacity left

Read-only, in priority order: (a) **what J1/J2/J3 inherit** — the three IdeaPress adoptions target
this 1.0, so name the surfaces they will pin against and anything in them you would not want frozen;
(b) G3 §9b's `turn_overrun` versus `STEP_LIMIT_EXCEEDED` ordering, if §0.3 decision 5 deferred it;
(c) whether the corpus found anything that belongs in **ToolYard** rather than here (§0.5), stated
as a defect and not as a patch; (d) whether `output.tool_calls_assembled` (H2.2 §7) lets
`assemble_tool_calls` be deleted, and what that costs in compatibility with an older LoadCoach.
