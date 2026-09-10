# I2 — PromptCadence Phase 9: hardening, the injection corpus, the budgets, the docs set, and 1.0.0

**Row:** I2 of `roadmap/outstanding-work.md` §1. **Model:** scheduled Opus 5 · xhigh; ran on
**Claude Fable 5.1**, whole, daytime, with the operator present for the interview that follows
(model-assignment §3.5 — recorded, not a split). The row's "consider Fable 5 for the injection
corpus" option was therefore taken for the whole row rather than for the corpus alone.
**Date:** 2026-09-06. **Interpreter:** Python 3.13.15 at `PromptCadence/.venv/bin/python`.
**Ships:** `promptcadence 1.0.0` **prepared** — bumped, changelogged, release-committed — and
**not** tagged, pushed or published. Those are the operator's (§13), with §10's verdict in hand.

**Repositories touched:** `PromptCadence` (ten commits) and `docs` (four commits). Both were clean
at the start — PromptCadence seven ahead of `origin`, docs ten ahead, as I1 left them — and both
are clean at the end with the new work committed and unpushed. Nothing was modified that this
session did not edit; no push and no push dry-run was run.

---

## 1. Gate results, with the exact invocations

Every gate ran the full pre-PR gate before its commit. The final run, from
`/home/jpk/ai/suite/PromptCadence`:

```bash
.venv/bin/ruff format --check .          # already formatted
.venv/bin/ruff check .                   # All checks passed!
.venv/bin/python -m mypy src tests       # Success: no issues found in 171 source files
.venv/bin/lint-imports                   # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                         # 1194 passed, 2 skipped, 10 deselected
.venv/bin/python -m pytest -m performance tests/performance -q -s -p no:randomly
                                         # 9 passed (§8 has the numbers)
```

The suite grew from 1135 to 1194 tests. The **clean-venv proof** (Packaging §4, §6): a fresh
`python3.13 -m venv`, `pip install --require-hashes -r requirements/ci.lock`, `pip install .
--no-deps`, then the suite — **1193 passed, coverage 92 %** (floor 85 %) measuring the installed
distribution, not the checkout. `pip-audit --require-hashes` over `ci.lock` and `release.lock`:
**no known vulnerabilities**. `gitleaks git` over all 74 commits (through docker,
`ghcr.io/gitleaks/gitleaks:latest`): **no leaks found** after §11's one correction.

## 2. The gates as commits

| Gate | Commit | What it made true |
|---|---|---|
| A | docs `6feda21`, PromptCadence `5c070b2` | ADR-0095…0098 accepted and indexed; spec §12/§13/§14/§15/§17/§18/§20 amended; roadmap I13 and the LC-E1 risk row point at 0098; mirror `cmp`-identical |
| B | `70d03f8` | Security Standards §14 item by item in `tests/security/`; the two `[server]` limits enforced (rate limiter, body cap, same-origin, LoadCoach's transcribed); **a principal on every `/api/v1` route except `/version`**; the CLI carries the token on every client-mode call |
| C | `af60303` | The retention sweep, workspaces included, stamped `content_scrubbed_at` (migration `0011`), the explanation re-materialized behind it |
| D | `80bc542` | The prompt-injection corpus (ten cases) and the `turn_overrun`-before-`STEP_LIMIT_EXCEEDED` journey |
| E | `8f5cfdd` | Replayed tool-call arguments capped at ToolYard's record bound (ADR-0096) |
| F | `e2584ce` | Every §15 budget under the `performance` marker, ceiling-asserted, target-reported (ADR-0097) |
| G | `1ef7424` | The remote-provider fact read from LoadCoach; `GET /tiers`; a remote tier's one recorded reason; the fake's mixed registry; I13's recorded-transport journey; the LoadCoach snapshot refreshed |
| H | `c1583e0` | The operator set, the generated configuration reference, `docs/openapi.json`, `requirements/ci.lock` and the CI that installs from it, `.gitleaksignore`, the beta-head migration test |
| A′ | docs `8b27f82` | ADR-0098's correction — see §5 |
| release | this row's last PromptCadence commit | `1.0.0`: the bump, the changelog moved under the version, the beta's *Known limitations* revisited, the classifier `5 - Production/Stable` |

## 3. The five decisions (kickoff §0.3), with the reason and what the losing option would have claimed

### 1 — What "the injection corpus is a release gate" means (ADR-0095)

**Taken:** every case asserts a **model-independent property of the harness** — which tool ran or
was refused and why, what the workspace holds, which host a fetch reached, which `EgressDecision`
was written, what the wire carried — never what the model said. The corpus runs in CI against the
fake and is the gate; a live pass is evidence.

**What the losing options would have claimed.** *Assert the model's compliance* — the obvious
reading, and a measurement of the model that rots with every model change; it belongs in
FreeWeight as a capability. *Live only* — honest about the stack and useless as a gate: no GPU in
CI, no determinism, and the beta shipped with an unmet clause for exactly that reason. The corpus
found no defect in the harness (§4); what it found was two **vocabulary** facts worth writing down
— a registered tool outside the envelope is `not_approved`, an invented one `unknown_tool`; a
`file://` URL is refused by the *egress decision* (`egress_not_permitted`, no host) before
ToolYard's `scheme_not_allowed` is ever reached.

### 2 — The cap on replayed tool-call arguments (ADR-0096)

**Taken:** one bound, ToolYard's `DEFAULT_MAX_ARGS_JSON_BYTES` (16 KiB), imported; an oversize
call is replayed with the **record's own** size-and-digest object in place of its arguments, id
and name kept; the call itself runs with its full arguments; the rows keep them until retention.
The record and the wire agree by construction, and the test asserts the digest in the stub is
`tool_call_records.args_sha256`.

**What the losing options would have claimed.** *Refuse the turn* — fails a trajectory for a call
that already succeeded, at a park or a crash boundary, for a reason the model cannot fix. *Cap
at execution* — makes a 20 KiB `write_file` unwritable to bound a replay the replay can bound. *A
second column saying "truncated"* — a second place for a fact `args_json` already states.

### 3 — Which §15 budgets are asserted, and against what (ADR-0097)

**Taken:** all ten rows are tests; the **median** over 20 iterations after 3 warm-ups must not
exceed the **ceiling**; median, p95 and target are printed; the three scale rows are built
synthetically from rows; the two overhead rows are separated from LoadCoach time and tool time by
measuring at the transport boundary and solving two runs for two unknowns; the SSE row is measured
over a real loopback socket, where the poll quantisation is visible.

**What the losing options would have claimed.** *Assert the target* — red on any loaded runner for
nothing. *Measure the scale rows by hand* — leaves the rows most likely to regress with growth
untested for the price of a few seconds of fixture. **One row misses its target** (§8, the SSE
row) and the ceiling was not widened: it is a finding for the interview.

### 4 — The remote-tier release scope (ADR-0098)

**Taken:** 1.0 ships with I13's **recorded-transport half proven in CI** and the live half
deferred; a remote tier refuses honestly, naming `loadcoach_has_no_remote_provider` or
`unpriced`. The fact is read from LoadCoach, never assumed and never inferred from a provider
kind; a response is verified by its declared `is_remote`.

**What the losing options would have claimed.** *Hold 1.0 for the live run* — a release waiting on
a credential and a bill for a path whose every component is individually proven. *Ship remote
tiers dark* — what the beta did, and the dependency has landed. **The correction found while
building it** is §5's first item.

### 5 — `turn_overrun` versus `STEP_LIMIT_EXCEEDED` (spec §13, no ADR)

**Taken:** the lifecycle already decided it (§5's table: `turn_overrun` → scoped re-approval that
may extend `max_turns`), so no record was needed — one sentence in spec §13 and a journey test.
The deviation is decided first; `STEP_LIMIT_EXCEEDED` is the halt for the bound nobody can
extend by approval, `max_turns_per_step` round trips. G3's reading that "the limit halts first"
was of the *loop-level* check, which a parked step never reaches; I1's live run had already shown
the park.

## 4. The corpus inventory (case → property → where asserted)

All in `tests/security/test_injection_corpus.py` unless named otherwise. None asserts what the
model said.

| Case | Property | Asserted on |
|---|---|---|
| A plan description carrying instructions | The offered and executable tools are the plan's declarations, never its prose | the wire's `tools`, the one record (`refused`, `not_approved`), the `undeclared_tool` deviation, no `system` turn |
| A description embedding `[tool_calls]` text | Only a structured `tool_calls` entry is a call | no record, no deviation, no workspace |
| A declared tool with hostile arguments (`..`, absolute, symlink, outside, metacharacter, wrong type) | Schema-validated then sandbox-checked; nothing outside containment | seven records (five refused, one `ok`, one schema refusal), the outside file untouched, the workspace's two entries |
| An invented tool name, model told the truth | Only registry-listed, intent-approved tools are callable | the wire carried `list_dir` only; both records `unknown_tool`; `undeclared_tool` |
| A tool result carrying instructions | Replayed as a `tool` turn; changes no envelope | the second request's one `tool` message, no `system`, tools unchanged, the follow-up `not_approved` |
| Tool descriptions | The registry's text, verbatim | `description` and `parameters` equal the catalog entry's |
| `http_fetch`: link-local, cross-host redirect, oversize, `file://`, plus one good fetch | No model-chosen URL skips ADR-0026 §3, even on an allowlisted host | records `link_local_address`, `cross_host_redirect`, `too_large`, `None`, `egress_not_permitted`; the transport never reached 169.254 or evil.example.net |
| A plan routing confidential work to a remote tier | Egress from the trajectory's declaration, never from model text | no request to the remote profile; no approved remote decision; no turn on `remote_cheap` |
| Model output shaped like the record | Model text lands inside `content.text` and nowhere else | schema/version unchanged, one `"schema":` key in the bytes, the lookalike's `"version":"9.9"` never top-level |
| A compaction summary that emits tool calls | The summary's intent approves no tool; nothing runs | summary intents' `approved_tools_json == []`; no record on a compaction-thread turn |
| `turn_overrun` before `STEP_LIMIT_EXCEEDED` (`tests/integration/test_turn_bounds.py`) | Lifecycle §5's order | park with one `turn_overrun`, a pending `reapproval`, no record; then the cap's halt with one record and no overrun |
| Held before this row, named in `test_checklist.py`'s map | path/symlink escape (P4), unlisted tool (P4), sandbox refusal (P4), non-allowlisted fetch and the ceiling (P6), the scopes (G1), CSRF and escaping (I1) | — |

## 5. Things this prompt said that turned out not to be true

* **"I1 is not built."** It was — I1 landed the day before this row ran (`docs/history/handoffs/I1_HANDOFF.md`),
  so §0.1's block never applied and every certification ran whole: the three explanation and
  compaction budgets were measured, CSRF had a form to protect, and the corpus attacked the two
  surfaces I1 added.
* **"The highest ADR is 0085."** It was 0094; this row took 0095–0098.
* **"`promptcadence 0.9.0b0` is on PyPI."** It is not (`pip index versions` finds nothing), so
  the upgrade test built the beta's wheel from `c9ed99a` and upgraded its database with the
  `1.0.0` wheel in a clean venv (§9).
* **"There are no `tests/security/`, `tests/performance/` or `tests/accessibility/` directories."**
  I1 had added `tests/accessibility/`; the other two are this row's.
* **ADR-0098 rule 1 said the fact is read from `/models`.** LoadCoach 1.1.0 records `is_remote`
  and `provider_name` on its `models` table and renders them on the generate response's `model`
  block — **not in `GET /models`** (`_model_to_json` lists neither). The fact therefore reads
  `False` on a real 1.1.0 and a remote registration is invisible before its first turn; remote
  tiers stay `loadcoach_has_no_remote_provider`, which is the decision's honest refusal rather
  than a guess. PromptCadence reads the field when present, so the render is a one-line LoadCoach
  change with no PromptCadence change behind it (§13, the row to schedule). Recorded as a
  correction on ADR-0098 (docs `8b27f82`).
* **Spec §7.1 lists `GET /settings` and `PUT /settings`.** Neither exists, and nothing in the
  spec or the plan defines a runtime-changeable key for PromptCadence; `docs/troubleshooting.md`
  records them as unbuilt rather than stubbing them, and `docs/openapi.json` says what is served.
  An interview item (§14).
* **Only the explanation and approval routes resolved a principal.** `POST /trajectories`,
  cancel, every read, health, status, tools, the ledger and the egress decisions answered anyone
  once a token existed. Spec §14 says every scoped endpoint needs a bearer; gate B made it so.
  On an open loopback install nothing changed.
* **The `tool.call.started` event's `args_sha256` and the record's `args_sha256` are computed
  differently** — the event digests the canonical *text*, ToolYard the *structure* — so they
  differ for the same call. Found while proving ADR-0096's "the digest in the stub is the
  record's"; the stub uses the structure digest and matches the row. The event's digest is
  unchanged (an existing contract) and noted for a later row.
* **ToolYard's `duration_ms` spans the whole `execute`**, not the handler alone, so "tool
  dispatch overhead excluding tool runtime" cannot be read off one call. Two runs and two
  unknowns measured it instead (§8).

## 6. Exit conditions (kickoff §14)

| # | Condition | Result |
|---|---|---|
| 1 | Every spec §20 criterion 1–11 passes, each named with what proved it | **Met** — §7 |
| 2 | The corpus runs in CI and is a release gate; every case model-independent | **Met** — §4; `tests/security/` is in the default suite |
| 3 | Security Standards §14 item by item; the two `[server]` limits enforced | **Met** — `tests/security/test_checklist.py`, `test_rate_limit.py`; the map's closing test |
| 4 | The retention sweep, workspaces included; a scrubbed trajectory still explains itself | **Met** — `tests/integration/test_retention.py` (four tests); the explanation's revision bumps `retention_scrub` |
| 5 | Every §15 budget measured and asserted, target-and-ceiling; the ≤ 25 ms row as a number | **Met** — §8: per-turn overhead **13.45 ms median** |
| 6 | I13 done, or the release-scope decision recorded; the recorded half green either way | **Met** — ADR-0098; `tests/integration/test_remote_tier.py` (three tests) green |
| 7 | The operator set, the OpenAPI snapshot, the generated reference, `ci.lock` committed; `pip-audit` and `gitleaks` clean; upgrade and clean-venv installs proved | **Met** — §1, §9 |
| 8 | The independent-brief verification run, verdict stated plainly | **Run, verdict stated** — §10: three runs on gpt-oss:20b delivered nothing (three named findings); F1 fixed at the interview's direction, the fourth run delivered the brief with every governance property holding. **Ready.** |
| 9 | `promptcadence 1.0.0` prepared, unpushed, untagged | **Met** — the release commit |
| 10 | Full gate green, interpreter and invocations named; mirrors `cmp`-identical | **Met** — §1; `cmp` on the three mirrored documents at the end |

## 7. Spec §20, criterion by criterion

| # | Criterion | What proved it |
|---|---|---|
| 1 | `pip install promptcadence && promptcadence serve` with only LoadCoach + Ollama | The clean-venv install (§1); `tests/e2e/test_server_boot.py`; the live stack (§10) served from a fresh data directory with zero configuration beyond `read_roots` |
| 2 | `run "summarize the files in ./notes"` plans, is approved, executes with sandboxed tools, returns a result and an explanation naming every model, tier, tool call, debit and egress verdict | G2's live demonstration on the real stack (three declared sandboxed calls, all `ok`); `tests/integration/test_planned_loop.py`; the explanation's completeness test (I1); §10 for this row's run |
| 3 | Bypass produces a record identical in shape minus plan rows | `tests/contract/test_governance_invariance.py` (I11, unchanged) |
| 4 | Confidential never reaches a remote tier; refusal before any request; a queryable `EgressDecision` | `tests/integration/test_egress.py` (the counting client), the corpus's remote-plan case, `test_remote_tier.py`'s confidential case |
| 5 | Unpriced remote tier refuses before any call | `test_egress.py::test_an_unpriced_remote_tier_refuses_before_any_call`; `unpriced` on `GET /tiers` |
| 6 | Crossing a ceiling halts or parks with the ledger showing the crossing | `tests/integration/test_budget.py` (F1, unchanged) |
| 7 | Hybrid mode parks an `internal` egress step; deny halts with the denial recorded | `tests/integration/test_approvals.py`, `tests/e2e/test_approval_surfaces.py` |
| 8 | `undeclared_tool` handled per category; scoped re-approval mints a superseding revision, both retained | `tests/integration/test_bypass_loop.py`, the corpus's invented-name case, `test_turn_bounds.py` |
| 9 | Kill −9 recovery, nothing lost, duplicated, stuck or orphaned | `tests/integration/test_recovery.py` (D2/F1, unchanged); the 100-trajectory recovery budget (§8) |
| 10 | The suite passes with no LoadCoach, no GPU, no network | §1 — the `no_network` fixture refuses any non-loopback socket |
| 11 | Every PromptCadence gold standard | §11 |

## 8. The ten §15 budgets, as measured (reference machine, Python 3.13.15, the fake LoadCoach)

| Measure | Target / ceiling | Median | p95 | Verdict |
|---|---|---|---|---|
| Trajectory admission | 50 / 200 ms | **1.77 ms** | 3.56 ms | inside target |
| Plan approval evaluation, 20 steps | 20 / 100 ms | **0.07 ms** | 0.08 ms | inside target |
| **Per-turn overhead excluding LoadCoach time** | 25 / 100 ms | **13.45 ms** | 25.56 ms | inside target |
| Tool dispatch overhead excluding tool runtime | 10 / 50 ms | **2.09 ms** | 2.20 ms | inside target |
| Ledger debit, ceilings evaluated | 5 / 20 ms | **3.15 ms** | 4.17 ms | inside target |
| Compaction plan, 200-turn transcript | 50 / 200 ms | **1.51 ms** | 1.66 ms | inside target |
| Added latency per SSE event (real loopback socket) | 5 / 20 ms | **1.40 ms** (was 10.00 at the 20 ms poll) | 2.18 ms | inside target after the interview's decision — see below |
| Explanation retrieval, terminal (materialized), 500 turns | 25 / 100 ms | **2.01 ms** | 2.11 ms | inside target |
| Explanation materialization, 500-turn trajectory | 2 / 10 s | **40 ms** | 119 ms | inside target |
| Recovery of 100 in-flight trajectories at startup | 2 / 10 s | **280 ms** | — (n = 1) | inside target |

The two overhead rows come from the same measurement: run A (18 turns, one `list_dir` each) and
run B (2 turns, the first with 17 calls), each wall time minus the LoadCoach transport time minus
the tools' own `duration_ms`, solved for the per-turn and per-call unknowns. LoadCoach time and
tool time are therefore reported *separately* by construction; against the real stack in §10 the
turn rows carry `overhead_ms` **52–55 ms** beside `loadcoach_ms` 1 233 and 43 769 — the real
figure includes the wire build, compaction estimate and the two writes around a real HTTP call.

**The SSE row was a finding first.** At the shipped `poll_interval_seconds=0.02` the distribution
was uniform between 0 and 20 ms — median **10.00 ms**, p95 19.16 ms — under the ceiling and over
the target; the poll quantised delivery, exactly LoadCoach's F12 finding. The ceiling was not
widened. **The interview chose to follow LoadCoach to 2 ms** (2026-09-06), and the rerun measured
median 1.40 ms, p95 2.18 ms, max 2.49 ms over 60 events.

## 9. The upgrade and the clean install

**Wheel to wheel.** A fresh venv, `pip install promptcadence-0.9.0b0-py3-none-any.whl` (built
from `c9ed99a`), `promptcadence db upgrade` → head `0007`. Then `pip install
promptcadence-1.0.0-py3-none-any.whl`, `db status` → `current 0007, head 0011, at head False`,
`db upgrade` → `0007 -> 0011` with `backups/pre-migration-0007-…sqlite3` written first, `db
status` → at head, `doctor` green on `database` and `tools` (LoadCoach deliberately unreachable in
that venv). `tests/integration/test_migrations.py::test_a_beta_database_upgrades_to_head_in_one_step_and_keeps_its_rows`
holds the same path inside the suite with a beta-shaped row preserved.

**Clean venv from the lock.** §1. The coverage trap `requirements/README.md` names did not bite:
`[tool.coverage.run] source` already named the package.

## 10. The independent-brief verification (gate I)

**Stack:** a real LoadCoach `1.1.0` served from a scratch `LOADCOACH_DATA_DIR` on
`127.0.0.1:8766` against Ollama `0.32.13` (13 models; `ollama/gpt-oss:20b@sha256:17052f91a42e`
routed for every turn, as at G1/G2/I1), and PromptCadence `1.0.0` served by `promptcadence serve`
from a scratch `PROMPTCADENCE_DATA_DIR` with **one** configuration beyond the defaults —
`[tools] read_roots` naming a directory of three short meeting notes written for this run.
`doctor`: all four components `ok`; `tiers check`: three profiles resolve, `tools.plan` included.

**The brief**, neither this session nor the corpus was written around: *"Read the three meeting
notes under `<read root>`, write a one-paragraph summary of the decisions and who owns what to
`summary.txt` in your workspace, then list your workspace to confirm the file exists."* Three
runs, through the CLI (`promptcadence run … --follow --json`):

| Run | Path | Outcome | Wall | What the record says |
|---|---|---|---|---|
| 1 | planned | **halted `LOADCOACH_ERROR`** at step `s0`'s second turn | 2 min 7 s | Two drafting attempts (the first invalid with one issue, the corrective retry valid), a six-step plan approved, six intents minted, `list_dir` `ok`, then an assistant turn with `finish_reason=length`, **`output_tokens = 4096` (the profile's `max_output_tokens`) and no text** after 43.8 s. LoadCoach's job carries a reasoning summary of the model deliberating what to do next; the whole budget went to reasoning. Halted per contract 6: *"a truncated answer is never read as success."* Two egress decisions, two debits. |
| 2 | planned | **completed** — brief **not** done | 32 s | One valid draft, five steps, all `committed`. The model dropped the leading `/` from the read-root path (`file_not_found`), tried `/` (**refused `path_escape`**), then declared `stop` on every step with *"I can't access that location … outside the workspace's allowed read area"*. No `read_file`, no `write_file`; `summary.txt` does not exist. Eleven turns, eleven `target_not_remote` decisions, eleven unpriced debits, no deviation. |
| 3 | bypass | **completed** — brief **not** done | 14 s | `list_dir` on the read root `ok`, `read_file` on two notes `ok`, one `read_file` **refused `path_escape`** because the model emitted the path with a U+2011 non-breaking hyphen and a dropped segment, then a declared `stop` with **12 output tokens and empty content**. No `write_file`; `summary.txt` does not exist. Seven decisions, seven debits, no deviation. |

**The verdict, plainly.** *The harness is ready; the product outcome on the reference model with
the shipped defaults is not demonstrated by this brief.* In three of three runs PromptCadence did
exactly what spec §14, §20 and the lifecycle say: every turn under an intent, every turn with an
egress decision and a debit, every tool call recorded with its reason, containment refusing what
should be refused (including a path a human would have read as correct), the model's declared
finishes honoured and its truncation refused, the explanation naming every model, tier, call,
debit and verdict, nothing crashed, nothing leaked. In zero of three did `summary.txt` get
written. Criterion 2's literal task (`summarize the files in ./notes`) was proved on this stack at
G2 with three declared sandboxed calls; this brief is one step harder — it needs a **read root** —
and that is where the three findings live:

* **F1 — PromptCadence, a real defect.** `read_file`'s and `list_dir`'s descriptions on the wire
  say *"a path outside the workspace is refused"* and never mention the configured `read_roots`.
  An obedient model therefore refuses to read what the operator configured it to read (run 2's
  five apologies), and a bold one guesses the path (run 3's hyphen). The description is
  caller-written prompt content (G2 §10) and the plant knows its read roots; naming them there is
  a few lines in `services/tools.py::_build` plus a corpus assertion that the description still
  equals the registry's. Not fixed in this row: gate I is *run it last, run it whole, report what it
  did*, and M7's precedent is a fixes row, not a same-session patch. **Recommended for 1.0.x before
  the tag, or as the first 1.0.1 item — the operator's call (§13).**
* **F2 — model behaviour the harness reads correctly, and a product smell.** Run 3's final answer
  was a declared `stop` carrying 12 tokens and no text. Contract 6 says a declared `STOP` completes
  the step, and it did. Whether an *empty* declared finish should complete a step is a decision,
  not a patch: G3's retryable set deliberately excludes governance outcomes and declared finishes.
* **F3 — the reasoning budget, again.** Run 1 is G2 §5's finding on the *agent* profile: gpt-oss:20b
  spent all 4 096 output tokens reasoning and answered nothing. H1 built the lever in ModelRack
  (`SamplingParameters.think`); whether `tools.agent.local_fast` asks for reduced thinking is a
  LoadCoach task-profile matter, and on 1.1.0 it does not. Recorded beside the value here rather
  than re-measured — one run, one data point.

What this does **not** change: exit conditions 1–7, 9 and 10 stand on tests and demonstrations
that do not depend on this brief.

### The interview's decision, and run 4

The operator chose **fix F1 first, rerun, then tag** (2026-09-06). F1 is one sentence appended to
`read_file`'s and `list_dir`'s descriptions when `[tools] read_roots` is configured — *"Also
readable, by absolute path: … (read-only roots the operator configured; nothing else outside the
workspace is)"* — rebuilt from the spec's own fields as `_redacting` is, with a unit test and the
corpus's verbatim-description assertion still holding. Same stack, same brief, same command:

| Run | Path | Outcome | Wall | What the record says |
|---|---|---|---|---|
| 4 | planned, **F1 in place** | **completed — brief delivered** | 1 min 33 s | One valid draft, a **seven-step plan, every step `committed`**. 18 tool calls: `list_dir` on the read root and three `read_file`s `ok` on absolute paths; five relative guesses `file_not_found`; four `path_escape` refusals, every one correct (a mangled path, `/`, the scratchpad's parent); two invented `container.exec` calls refused `unknown_tool` with `undeclared_tool` deviations; **`write_file` `ok`**; the closing `list_dir` `ok` naming `summary.txt`. Eight `budget_overrun` drifts recorded and continued under the default scope (step slices sized from the configured default, 25 turns in all). 25 egress decisions, all `target_not_remote`; 25 debits; 147 events; no halt. `summary.txt` (614 bytes) names the migration, Tomás's schema change, Priya's dashboards, the 06:00 UTC export deadline and the cut-over on the 12th — correct against the notes. Final answer: *"The workspace directory has been listed, confirming that `summary.txt` exists."* |

**Verdict, revised:** *ready.* With F1 fixed, the independent brief was delivered on the real
stack with the shipped defaults and one configured read root, every governance property holding
on the way — including the two invented tools and four escapes the model tried in the same run.
F2 and F3 stand as findings with rows (§14). One brief, one delivered run after one halted and
two empty ones: the number to carry forward is that the harness's record made every one of the
four legible, which is what M12 exists to prove.

## 11. The gold standards, item by item (Gold Standards §2, PromptCadence)

| Standard | Held by |
|---|---|
| Governance is invariant across the bypass (contract 1) | `tests/contract/test_governance_invariance.py` |
| No turn executes without an `ExecutionIntent`; intents never edited, a re-approval supersedes | `tests/unit/test_domain_intent.py`, `test_bypass_loop.py`, `test_approvals.py`; the contract-1 guard names `_summary_turn`'s required intent |
| A confidential trajectory can never reach a remote tier; the refusal is a queryable `EgressDecision` before any request | `test_egress.py` (the counting client), `test_remote_tier.py`, the corpus |
| Every LoadCoach response verified against the tier that requested it; a remote answer on a local tier halts with a `VIOLATION` | `test_egress.py`, `test_bypass_loop.py`, `test_loadcoach_surface.py` (both eras) |
| Unpriced egress is refused, not free | `test_egress.py::test_an_unpriced_remote_tier_refuses_before_any_call`; `unpriced` on `GET /tiers` |
| No provider access of any kind — `modelrack` never imported | `.importlinter` contract `no-direct-provider-access`, 5 kept |
| A model never decides control flow; a refused tool call never ends a trajectory | `decide_finish` tests, `test_tool_execution.py`, the corpus; §10's three runs |
| Every halt names its cause verbatim in `trajectory show` | `tests/e2e/test_bypass_journey.py`; §10 run 1's cause |
| The suite passes with no LoadCoach, no GPU, no network | §1, the `no_network` fixture |

## 12. Working-tree integrity, and one correction

Both repositories clean at start and end; nothing modified that this session did not edit; no
push, no push dry-run, no tag, no publish. The operator's real PromptCadence database was **not**
touched: every live run used `PROMPTCADENCE_DATA_DIR` under the session scratchpad, and the real
LoadCoach 1.1.0 was served from a scratch `LOADCOACH_DATA_DIR` on `127.0.0.1:8766` (its own
profile import and discovery; the operator's LoadCoach database untouched).

**One correction to this row's own history.** `gitleaks` flagged the fixture credential the
no-secret-in-logs sweep looks for (`LOADCOACH_KEY` in `tests/security/test_checklist.py`, a
secret-shaped literal committed in `70d03f8`). The literal is now built by repetition so a scanner
sees the placeholder it is, and `.gitleaksignore` carries the one historical fingerprint with its
reason. The commit was not rewritten.

## 13. Left for the operator

1. **Push two repositories.** `PromptCadence` (seventeen ahead of `origin`: seven from I1 and the
   Commissioner chore, ten from this row, the last being the release commit `b4b67ac`) and `docs`
   (fourteen ahead). Nothing was pushed.
2. **Tag `v1.0.0` and publish.** `promptcadence 1.0.0` is M12's exit condition and rows J1–J3 wait
   on a *released* 1.0 (ADR-0011). The release commit is in place; the tag triggers `release.yml`,
   which builds from `requirements/release.lock`, runs the suite against the wheel, and publishes
   through Trusted Publishing. `0.9.0b0` was never published; nothing depends on it.
3. **A LoadCoach patch row**: render `provider_name` and `is_remote` in `GET /models`
   (`web/routes/models.py::_model_to_json`, two lines). Until then PromptCadence's remote-provider
   fact reads `False` on a real LoadCoach and remote tiers refuse honestly (ADR-0098's correction).
4. **The `[1;3m` gitleaks docker image** is now pulled locally; CI's action needs nothing.

## 14. The interview (2026-09-06) — what was decided, and what remains

Decided at the interview, and done in this row:

1. **Fix F1 first, rerun, then tag** — done (§10, run 4). The tag stays the operator's.
2. **The SSE poll follows LoadCoach to 2 ms** — done; median 1.40 ms, p95 2.18 ms (§8).
3. **`GET/PUT /settings`: schedule a runtime-settings row** rather than strike them from spec
   §7.1 — row **I4** in `outstanding-work` §1 (renumbered **I5** on 2026-09-06, when the 1.0.1 row was placed ahead of it).
4. **One LoadCoach 1.1.1 row before J1** for the `/models` render and the thinking control —
   row **I3**, with an ordering note in §3.

Still the operator's:

* **The tag and the publish** (§13) — the release commit is prepared with run 4 in the record.
* **F2** — whether an empty declared `stop` should complete a step (contract 6 says it does).
* **The event/record digest mismatch** (§5) — fix `tool.call.started` to the structure digest, or
  document the difference.
* **The live remote run** (ADR-0098 rule 5) — when an endpoint and a key exist; `docs/tiers.md`.

## The interview items as first put

Decisions this row took under the standing rules and that the operator may want to revisit, plus
the ones the row could not take:

1. **The SSE poll interval** (§8): follow LoadCoach to 2 ms, or keep 20 ms and the recorded 10 ms
   median.
2. **`GET/PUT /settings`** (§5): remove them from spec §7.1 for 1.0, or schedule a runtime-settings
   row (what would be runtime-changeable?).
3. **The LoadCoach `/models` render** (§12 item 3): a patch row before or after J1–J3.
4. **The live remote run** (ADR-0098 rule 5): whether an endpoint and a key exist now; if so the
   sequence in `docs/tiers.md` can run against this LoadCoach today.
5. **The verdict in §10**, and what it means for the tag: tag 1.0.0 as prepared and take F1 as
   1.0.1; or fix F1 first (a few lines plus a corpus assertion), rerun the brief once, and tag
   what that shows.
7. **F2** — whether an empty declared `stop` should complete a step (contract 6 says it does).
8. **F3** — a LoadCoach row to let `tools.agent.*` ask for reduced thinking now that ModelRack
   has the lever (H1 gate F).
6. **The event/record digest mismatch** (§5): fix the event to the structure digest (a contract
   change on `tool.call.started`) or document the difference.
