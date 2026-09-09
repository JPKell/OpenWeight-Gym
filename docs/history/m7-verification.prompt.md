Verify IdeaPress against M7's exit condition — *"A complete project is produced and exported with
**only Ollama** present"* — and decide whether it is ready. Run unattended: nobody is available to
answer a question. You may read anything, run anything, measure anything, kill anything you
started, and open a browser against a server you start. **You may not edit code, commit, push, tag
or publish.** If a claim below turns out to be false, that is a finding, not something to fix.

**Model:** Fable 5, max effort. Ultrathink on every claim you attack.

Your job is adversarial. The implementer's report says everything passes; a passing suite is weak
evidence, "the tests pass" answers nothing, and reporting **not ready** is a success if it is true.
This application exists to refuse gates a model can satisfy, so the highest-value thing you can do
is find one it cannot refuse. Every DECISION entry in the handoff is a place a document was
ambiguous and the implementer chose; an ambiguity resolved in the implementer's favour is where a
contract bug lives.

## Ground state

```
cd ~/ai/suite/IdeaPress && git log --oneline -1     # the M7 head
git log --oneline c585565..HEAD | wc -l             # commits since the scaffold
cat src/ideapress/__about__.py                      # __version__ = "0.1.0" — no tag, no publish in M7
git tag                                             # empty; `ideapress 1.0.0` is M8's

.venv/bin/ruff format --check .
.venv/bin/ruff check --no-cache .                   # --no-cache deliberately: see M7-23
.venv/bin/mypy src tests
.venv/bin/lint-imports                              # 4 contracts kept
.venv/bin/pytest -q -m "not live and not performance"                       # ~632 passed
.venv/bin/pytest -q -m "not live and not performance" --cov --cov-fail-under=85   # ~91 %
.venv/bin/pytest -q -m "not live and not performance" --cov=ideapress.domain      # ~98 % in domain/
.venv/bin/pytest -q -m contract                                             # ~123 passed
unshare -rn .venv/bin/pytest -q -m "not live and not performance"           # AC11: no network at all
WEIGHTSDB_REQUIRE_POSTGRES=1 \
  WEIGHTSDB_POSTGRES_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5433/postgres \
  .venv/bin/pytest -q -m "not live and not performance" tests/integration    # needs a server you start
```

The venv is **Python 3.13.15**. The handoff is `~/ai/suite/M7_HANDOFF.md`, entries `M7-1` … and a
final `## ACTIONS REQUIRED FROM YOU`. The docs repository (`~/ai/suite/docs`) is committed at its
head; `IdeaPress/docs/apps/ideapress/*.md` are byte-identical mirrors — `cmp` all six yourself,
because this repository is the one whose mirror had never been repaired before this run.

**New documentation this run wrote or changed, all of which you should read critically:**
`docs/adr/0038-one-model-at-a-time-per-gpu.md` (new); `architecture/master-architecture.md` §5.2;
`apps/ideapress/spec.md` §5, §7.1, §12, §13; `apps/ideapress/workflows.md` §2 and §6.

**State when the run ended:** `ideapress 0.1.0`, unpublished, untagged. Only Ollama is required;
`pip list` in the venv contains neither `loadcoach` nor `freeweight`, and `loadcoach` was
deliberately moved out of the `dev` extra so the default test environment cannot satisfy the
standalone claim by accident (M7-3). The demonstration's artefacts are in
`IdeaPress/.m7-evidence/m7-demo/` — brief, transcript, exports, hashes, the residency poll and a
`cost.json`. **Re-run the demonstration yourself; that is the point of you.** Ollama is at
`http://127.0.0.1:11434` with `qwen3.5:9b-q8_0` and `gemma4:12b` pulled, on a 16 GB card that holds
one of them at a time.

## What "ready" means

Twelve acceptance criteria in `docs/apps/ideapress/spec.md` §20, six gold standards in
`docs/standards/gold-standards.md` §2 (IdeaPress), and M7's exit condition. Criteria **2 and 7
involve LoadCoach and belong to M8** — the implementer says so; check that they did not quietly
claim them. For each, the implementer's answer is in the handoff and in the run report. Your answer
overrides it where you can show otherwise.

## Claims worth attacking, and the falsification to attempt for each

Run the named test first, then break the claim by hand. **A test that cannot see the break is a
finding of its own**, and it is the most valuable kind you can report.

1. **No model output can end a gate — the plan gate.**
   `tests/unit/test_plan_gates.py::test_no_requirements_at_all_does_not_satisfy_the_gate`.
   Falsify: script a backend that returns `{"requirements": []}` and then a confident, well-formed
   plan, and a *second* that returns one requirement it insists is the only one needed and a plan
   that covers it. Then try harder: return a requirement whose `blocking` is `false` for everything
   the brief states as a must, so the gate passes on a plan that guarantees nothing. Does anything
   catch that? If not, say so — it is the same failure wearing different clothes.

2. **No model output can end a gate — the commit gate.**
   `tests/unit/test_commit_gate.py::test_the_gate_has_no_parameter_a_model_could_speak_through`.
   Falsify: script an audit that returns no findings and a critique that says `acceptable` for a
   unit that fails a blocking validation check and misses a blocking requirement. Nothing may
   commit. Then look for a **second door**: `grep -rn "\.generate(" src/` and
   `grep -rn "commit_unit\|decide_commit" src/` — is there any path to a committed version that
   does not pass through `decide_commit`?

3. **The requirement compiler does not fabricate.**
   `tests/unit/test_requirement_compilation.py::test_benign_material_yields_no_requirement_however_confident_the_model_is`.
   Falsify: write your own benign brief — real prose that states no constraint on a finished work —
   and run the **real** compiler against the **real** model, not the scripted one. Every requirement
   it returns must quote the brief verbatim. Then attack the documented limit: make a model quote
   real text and attach an unrelated requirement, and confirm the implementer's claim that this
   passes and is only mitigated by display. Is the quote actually shown in every view and every
   export? Check the plan page, `ideapress plan show`, and all three export formats.

4. **The context budget refuses with numbers.**
   `tests/unit/test_context_budget.py::test_requirements_alone_exceeding_the_budget_fails_with_both_numbers`.
   Falsify end to end rather than in a unit: create a project whose brief yields many long
   requirements, set `workflow.context_budget_tokens` very low, run `draft`, and read the error a
   user actually sees. Does it carry `required_tokens` and `budget_tokens` both? Then check the
   reduction order is what workflows §7 says by squeezing the budget in steps and recording what
   leaves — and confirm a requirement is **never** among them.

5. **The repair and revision bounds hold against a model that never converges.**
   `tests/integration/test_review_loop.py::test_a_critic_that_never_converges_is_stopped_by_the_arithmetic`.
   Falsify: a backend that returns a *different* finding every round (so the count does not settle)
   and always `materially_deficient`. Count the model calls. It must stop at
   `max_revision_rounds`, and the stop reason must be recorded on the critique row. Then set
   `max_revision_rounds = 0` and `= 100` and check both behave.

6. **A revision that makes a unit worse is rejected.**
   `…::test_a_revision_that_makes_the_unit_worse_is_rejected_and_the_prior_text_kept`. Falsify:
   make the revision worse in a way that *increases audit findings but not validation failures* —
   the implementer says that is deliberately not a regression. Decide whether you agree, and say
   what a user would expect.

7. **Exports are byte-identical.** `tests/unit/test_exporters.py::test_identical_under_a_different_locale_timezone_and_hash_seed`.
   Falsify: export the same committed project on the hour and again after changing the system
   clock; under `TZ=Pacific/Kiritimati`; under `LC_ALL=tr_TR.UTF-8` (the Turkish dotless-i locale
   breaks naive lowercasing); and with `PYTHONHASHSEED` random. `sha256sum` every pair. Then export
   after adding a *second* project to the same database and confirm the first is unchanged.

8. **The HTML export opens offline.** `tests/integration/test_export.py::test_the_html_export_opens_with_no_network_at_all`.
   The implementer states plainly that this parses the file in an unshared namespace rather than
   driving a browser. **Do the browser part.** Open it in a real browser with the network
   namespace unshared, or with a proxy that logs every request, and assert zero requests. Confirm
   it renders complete and readable, not merely that it loads.

9. **Hostile model output is inert everywhere.** Falsify across **every view and every export
   format at once**: script a draft containing `<script>alert(1)</script>`, `{{ 7*7 }}`,
   `{% raw %}`, `<img onerror=…>`, a `javascript:` link, an HTML comment that closes early, and a
   right-to-left override. Check the unit page, the plan page, the project pages, the Markdown, the
   HTML and the JSON. The implementer says the safety validator flags most of these as *advisory*
   because escaping is the real control — so verify the escaping, in every one of those places.
   P9's named failure mode is a gap in one format and not another.

10. **A stage killed mid-commit leaves nothing partial.**
    `tests/integration/test_atomic_commit.py::test_a_killed_process_mid_commit_leaves_the_database_untouched`.
    Falsify differently: kill `ideapress stage run` with SIGKILL at several points — during the
    draft, during validation, during the commit — and after each, reopen and check that committed
    units are intact, no partial version exists, and `--resume` continues from the first incomplete
    unit. Then do it on **PostgreSQL**, not only SQLite.

11. **The three-way parity claim.** `tests/integration/test_backend_parity.py`. The implementer
    gives the three adapters the same scripted answers, on the argument that the *adapters* are
    what is under test. Decide whether that is honest. Then re-run it your own way: point the
    OpenAI-compatible adapter at a real OpenAI-compatible server if you can start one (llama.cpp's
    `server`, or Ollama's own `/v1`), and compare structure against the Ollama run.

12. **The single-model invariant.** `tests/unit/test_single_model_invariant.py` and
    `tests/live/test_backend_live.py::test_one_model_at_a_time_across_a_real_switch`. Attack it
    directly: force a workflow that alternates bindings — bind `draft` to `gemma4:12b` and
    `audit_fast` to `qwen3.5:9b-q8_0` and run a multi-unit project — while polling
    `curl -s localhost:11434/api/ps` **and** `nvidia-smi` every second from outside the process.
    Two models resident at once, at any instant, is a blocker. Then:
    * set `execution.max_concurrent_stages = 2` and confirm **startup refuses** with the reason;
    * set `unload_before_model_switch = false` and confirm two models *do* become resident — if
      they do not, the invariant's test is measuring something else;
    * start a second `ideapress` process against the same database and run a stage in each at once.
      The implementer's serialisation is per-process. Does anything stop two processes? Read
      ADR-0038 and say whether it claims to.

13. **`Host` validation runs before routing, on both binds.**
    `tests/e2e/test_system.py::test_host_validation_runs_before_routing_on_every_request`.
    Falsify against a **real socket**, with the process started by `ideapress serve` — not
    `TestClient`. Loopback bind: `curl -H 'Host: evil.example.com'` must be 421 for a path that
    exists *and* for one that does not. Then bind non-loopback with `allowed_hosts` set and repeat.
    Then check the three refusals: `0.0.0.0` with no acknowledgement, non-loopback with empty
    `allowed_hosts`, and a remote `openai_compatible` endpoint with `providers.allow_remote = false`.

14. **The whole suite passes with no backend reachable and no network** (AC11). Falsify: stop
    Ollama entirely, then run the suite under `unshare -rn`. Then start the application with
    nothing reachable and confirm `/health` is **200 with a degraded backend**, not 503 and not a
    500 — the implementer found and fixed a 500 there (M7-15), so check the neighbouring paths:
    `/api/v1/backends`, `/backends`, `ideapress doctor`, `ideapress backend test`.

15. **The stage vocabulary is one set.** `tests/unit/test_stage_vocabulary.py`. The implementer
    **changed workflows §2** to resolve a contradiction: `research` is now the fifth no-model stage
    and the LoadCoach task map lost its `research` row (M7-6). Read the document's history and
    decide whether that reading is right. If you think `research` *is* model-using, say what breaks.

16. **Prompt records, never string literals.** `tests/unit/test_prompt_pack.py`. Falsify: add a long
    imperative string to a source file and confirm the test catches it. Then check I9 for real —
    load the same record under FreeWeight's and LoadCoach's installed `setspec` and compare the
    hash against `sha256:b9f17cf04bb076bcd7a660e169a73238e41e63987fead814d52bb36d6d7e1cb5`.

17. **`modelrack` and `httpx` are confined to adapters.**
    `tests/unit/test_import_boundaries.py`. Falsify: add an `import modelrack` inside a function
    body in `services/unit_loop.py` and confirm the AST walk catches it, then remove it.

## Re-run the demonstration, and judge what it produced

This is M7's exit condition and it is a transcript, not a test. With only Ollama running:

* Write **your own brief** — a different subject, with real constraints. Do not reuse the
  implementer's; a workflow tuned to one brief is the thing you are looking for.
* `ideapress project create` → `plan build` → `stage run <id> draft` → `stage run <id> project_review`
  → `export run` in all three formats.
* Time every stage. Count the model calls and the model switches. Compare against the
  implementer's `cost.json`; a large discrepancy is a finding about one of the two runs.
* Then **read the document it produced and say what you think of it.** Is it any good? Where is it
  thin, generic or padded? Which stage is responsible — the prompt pack, the context budget, the
  critique threshold, or the compiled checks? The implementer records (M7-21) that the compiler
  produced `must_contain_any: ['inference', "reader's", 'own', 'machine']` for a requirement about
  where inference runs — a check that passes on the word "inference" alone. Look for more of that:
  **a gate that is technically deterministic and substantively empty is this application's most
  dangerous failure**, because it looks exactly like success.

## Measure, do not read the tests

Spec §15's budgets: stage orchestration overhead ≤ 50 ms per attempt excluding inference;
validation of a 5 000-word unit ≤ 200 ms; project load at 100 units ≤ 300 ms; Markdown export of a
100-unit project ≤ 2 s; HTML ≤ 5 s; editor page render ≤ 300 ms. **None of these is asserted by a
test in this build** — the implementer says so. Measure them yourself, on a real socket where the
budget is about a page, and report the numbers.

## Verify CI the way the runner sees it

Read the runner at head: every job, its conclusion, and the **job count** — a run with
`total_count: 0` is a workflow that did not parse, not a suite that failed, and this repository has
produced one (M7-10). Then reproduce the two jobs no local default gate exercises: `db-matrix`
against a real PostgreSQL 16, and `coverage`. Check the 3.14 early-warning job's conclusion and say
whether it passed.

## Read the handoff critically

Every `M7-*` DECISION entry is a place the documents were ambiguous. For each, ask what the other
reading would have produced and whether the implementer chose the one that suited them:

* **M7-3** — moving `loadcoach` out of the `dev` extra. Does anything now fail to run that should?
* **M7-6** — `research` as a no-model stage.
* **M7-14** — the port refusing a schema on `kind="json"`.
* **M7-16 / M7-19** — the empty-generation retry and the raised token budgets. The retry is a
  workaround for one model's behaviour. Is it bounded where the implementer says? Does it hide a
  real failure? Reproduce the cold-load runaway yourself.
* **M7-18 / M7-24** — strict rather than greedy context reduction, and the JSON sorting bug.
* **M7-20** — a blocking requirement with no deterministic check being settled by audit. This is
  the sharpest question in the whole build: **a model's opinion is deciding a commit gate.** Read
  workflows §3 and decide whether that is what it licenses, and whether the flagging is enough.

## The verdict

Fixed shape:

**Verdict:** ready / ready with conditions / not ready.

**Findings:** numbered, each with a severity (blocker / major / minor / note), the claim it
falsifies, the exact reproduction, and the concrete thing that must change.

**The twelve acceptance criteria** (spec §20) and **the six gold standards** (§2, IdeaPress): met /
partially / not met / M8, one line each, in your own judgment, with the evidence you saw. Criteria
2 and 7 involve LoadCoach; say "M8" rather than claiming them, and check the implementer did too.

**The single-model invariant:** your own measurement, from outside the process, with the maximum
number of models you observed resident at any instant.

**The document:** your honest opinion of what the workflow produced, and whether it is worth
carrying into M8.

**Token discipline:** no subagents; the gate as the single chained command above; `--tb=line` while
iterating; do not re-read a document section you have already read.
