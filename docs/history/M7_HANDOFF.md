# M7 Handoff — IdeaPress P1–P6 run (M7 beta closeout)

Entries are written as they happen, in `docs/history/M4_HANDOFF.md`'s format: **Severity** (DECISION / NOTE /
BLOCKER), **Unit**, **Where**, **What happened**, **What the next run must do**.

Interpreter for every gate in this document unless stated otherwise: **Python 3.13.15**
(`/usr/bin/python3.13` → `IdeaPress/.venv`), per M5C-13 and SUITE_REVIEW F-15.

---

## M7-1 — The docs mirror was F-3's ninth repo: three files missing, three link-stripped

- **Severity:** NOTE (fixed)
- **Unit:** 1 (P0 ground)
- **Where:** `IdeaPress/docs/apps/ideapress/`
- **What happened:** Confirmed the prompt's ground state exactly. The repo carried three of the six
  canonical documents (`api.md`, `development-plan.md`, `spec.md`) and all three differed from
  canonical; `workflows.md`, `data-model.md` and `risks.md` — including **the only authoritative
  stage list** — were absent from the repository entirely. The divergence is the same
  downstream-first "Cleanup docs" link-stripping pass (`12f1db0`) that F-3 found in seven other
  repos and repaired there: `spec.md`'s header lost both the `**Status:** … Corrected 2026-08-21 by
  the [final architecture audit]` sentence and four of six `**Related:**` links, which is content
  loss, not formatting. Restored canonical → mirror for all six files and proved byte-identity with
  `cmp` per file.
- **What the next run must do:** Nothing for the restore. Keep `cmp`-proving the six files after any
  documentation change; canonical (`~/ai/suite/docs`) is edited first, always.

## M7-2 — DECISION: ruff must skip `docs/`, or the gate itself corrupts the mirror

- **Severity:** DECISION
- **Unit:** 1 (P0 ground)
- **Where:** `IdeaPress/pyproject.toml [tool.ruff] extend-exclude`
- **What happened:** With the mirror restored, `ruff format --check .` reported **1 file would be
  reformatted** — `docs/apps/ideapress/workflows.md:186`, the aligned `LOADCOACH_TASK_MAP` literal.
  Ruff formats fenced Python inside Markdown, so the only way to make the documented gate green
  without this exclusion is to edit the mirror away from canonical: the gate would *mechanise* the
  exact downstream-first drift F-3 was raised to stop. Workspace `CLAUDE.md` already states the rule
  ("Ruff is configured to skip `docs/` in each repo precisely so a mirrored file cannot drift by
  reformatting") and `py/ModelRack` already carries `extend-exclude = ["docs"]`; IdeaPress did not.
  Added it in ModelRack's form with the reason inline. **LoadCoach and FreeWeight also lack the
  exclusion** and are green only by luck — LoadCoach's fifteen mirrored documents happen to contain
  no code block ruff wants to reformat (verified: `ruff format --check docs/` under this run's ruff
  0.16.5 reports "15 files already formatted"). That is a latent trap in two published repos this
  run may not edit.
- **What the next run must do:** Add `extend-exclude = ["docs"]` to LoadCoach's and FreeWeight's
  `[tool.ruff]`. On the actions list; not blocking for M7.

## M7-3 — DECISION: `loadcoach` moved out of the `dev` extra into `loadcoach-contract`

- **Severity:** DECISION
- **Unit:** 1 (P0 ground)
- **Where:** `IdeaPress/pyproject.toml [project.optional-dependencies]`
- **What happened:** HR1 fixed the `dev` extra's malformed `"loadcoach  # comment"` entry by
  splitting the comment out, which made `pip install -e ".[dev]"` work — and made every developer
  and CI environment install **LoadCoach**. Gold Standards §2's first IdeaPress bullet is "runs a
  complete workflow with **no** LoadCoach and no FreeWeight installed", and risk I2's stated
  mitigation is "the standalone e2e suite is the default CI path". A `dev` extra that installs
  `loadcoach` means that property is claimed by a suite that has never once run without it — and
  M7's own demonstration requires `pip list` to prove the package is absent. The only consumer is
  P7's OpenAPI-snapshot contract test, which is **M8** work and does not exist. Moved to a dedicated
  `loadcoach-contract` extra with the reasoning inline; `.[dev]` no longer installs another
  application. This tightens the gate rather than weakening one: `.importlinter`'s
  `no-other-applications` contract is untouched and still enforced, and the standalone claim now has
  an environment that can falsify it.
- **What the next run must do:** At P7, install `.[dev,loadcoach-contract]` for the LoadCoach
  contract job only, and add that job to `ci.yml` — never widen `dev`.

## M7-4 — The PostgreSQL job selected a marker this repo never declares (HR2's defect 2, unfixed)

- **Severity:** NOTE (fixed)
- **Unit:** 1 (P0 ground)
- **Where:** `IdeaPress/.github/workflows/ci.yml`, job `db-matrix`
- **What happened:** The job ran `pytest -m integration`. `integration` is not in this repo's
  `markers` list and is applied to nothing, so the job collects **zero tests and exits 5** — red on
  every commit, while appearing to be the job that exercises PostgreSQL. This is HR2's defect 2
  verbatim, in the one repo HR2's fix never reached; both siblings select by path. Changed to
  `pytest -m "not live and not performance" tests/integration`, FreeWeight's form.
- **What the next run must do:** Nothing. Verified against a real PostgreSQL 16 server at each phase
  boundary from unit 3 onward.

## M7-5 — Ground-state gate on the untouched scaffold: what red looked like

- **Severity:** NOTE
- **Unit:** 1 (P0 ground)
- **Where:** `IdeaPress/` at `c585565` + HR1's uncommitted fixes
- **What happened:** `.venv` created from `/usr/bin/python3.13` (**3.13.15**); `pip install -e
  ".[dev,postgres]"` succeeded first try — HR1's PEP 508 fix holds. Installed suite packages:
  `baseaicore 0.4.0`, `setspec 0.4.0`, `modelrack 0.5.0`, `weightsdb 0.2.1`, `mirrorwall 0.2.1`.
  Neither `loadcoach` nor `freeweight` is present. The gate on the untouched 70-file scaffold:
  `ruff format --check` **1 file would be reformatted** (M7-2, a documentation file, not source);
  `ruff check` **passed**; `mypy src tests` **no issues in 70 source files**; `lint-imports`
  **4 contracts kept, 0 broken** (HR1's fixes verified against a real graph for the first time);
  `pytest` **exit 5, no tests ran** — all 70 modules are a docstring plus a TODO. The CI jobs' own
  invocations: `coverage` **FAIL, 0.00 % against an 85 floor**; `contracts` **exit 5**;
  `tests/integration` **exit 5**; `install-check` `import ideapress` succeeds but reports
  `__file__ = None` — IdeaPress ships as an implicit namespace package with **zero `__init__.py`
  files**, which is the suite's existing convention (LoadCoach has zero as well), so the job passes
  vacuously in both repos.
- **What the next run must do:** Nothing. Recorded so a later reader can tell a real regression from
  the starting state.

## M7-6 — DECISION: `research` is the fifth no-model stage; the task map was the outlier

- **Severity:** DECISION
- **Unit:** 2 (P1 skeleton)
- **Where:** `docs/apps/ideapress/workflows.md` §2 and §6 (canonical, then mirrored; commit
  `c8898d2` in `docs`)
- **What happened:** The startup check spec §12 and workflows §2 both mandate — "`[models.stages]`,
  `StageId` and workflows §2 are one set" — could not be written, because the three documents
  disagreed about one stage. §2's table marks **four** rows `**No**` while the sentence beneath it
  says "**Five** stages involve no model at all"; spec §12's `[models.stages]` holds **eleven**
  keys and declares itself "one key per model-using stage in Workflows §2", which is the
  model-using count *without* `research`; and `LOADCOACH_TASK_MAP` nevertheless carried a
  `research` row while claiming to cover "every model-using stage in §2 **and nothing else**".
  Resolved in favour of the two independent post-audit statements that agree (the count, and the
  normative configuration schema) against the one that does not. `research`'s "Optional" in the
  Model? column is the **stage**, not the model: no research backend ships at 1.0 (spec §21 lists
  them as future extensions), so the stage reaches no model and takes no binding. Corroborating
  detail: the removed row mapped `research` to `content.research_synthesis` — the *same* profile as
  `research_synthesis`, which is the fingerprint of a row added by pattern rather than by need, the
  defect the audit already corrected once in this same table (`code.review`). Left as it was, a
  stage would be mapped to a task profile while appearing in no binding list, which is
  `fact_check`'s defect with the sign reversed. `domain/stages.py` now encodes sixteen stages,
  eleven model-using, five no-model, four of which are the gates.
- **What the next run must do:** P7 builds `LOADCOACH_TASK_MAP` with **eleven** entries. If a
  research backend is ever added, the ADR that adds it decides `research`'s binding and its task
  profile together. `tests/unit/test_stage_vocabulary.py` parses both mirrored documents and
  compares them with the code in both directions, so this cannot drift silently again.

## M7-7 — DECISION: spec §5's dependency list omitted `python-multipart`

- **Severity:** DECISION
- **Unit:** 3 (P1 storage and projects)
- **Where:** `docs/apps/ideapress/spec.md` §5 (canonical, then mirrored)
- **What happened:** ADR-0020 makes server-rendered HTML with progressive enhancement the UI, so
  every mutating page action is a form post. FastAPI raises at **import time** on a `Form()`
  parameter without `python-multipart`, so the application as specified could not start. FreeWeight
  already declares it for exactly this reason; spec §5's third-party list did not name it. Added to
  the specification with the ADR that requires it, and to `pyproject.toml` at FreeWeight's pin
  (`>=0.0.9,<1`).
- **What the next run must do:** Nothing.

## M7-8 — The PostgreSQL job named a server nothing connects to, in a URL form the repo cannot open

- **Severity:** NOTE (fixed)
- **Unit:** 3 (P1 storage and projects)
- **Where:** `.github/workflows/ci.yml`, job `db-matrix`; `tests/integration/test_migrations.py`
- **What happened:** M7-4 fixed the job's marker; running it against a real PostgreSQL 16 found
  **two more defects in the same six lines**, neither visible to any local default gate:
  1. The job passes `DATABASE_URL`. `weightsdb.testing.temporary_postgres` — the shared helper that
     resets the schema and enforces the both-dialects promise — reads **`WEIGHTSDB_POSTGRES_URL`**.
  2. The URL is the bare `postgresql://…`, which SQLAlchemy resolves to the **psycopg2** dialect.
     This project installs `psycopg[binary]` (psycopg3), so every PostgreSQL test fails with
     `ModuleNotFoundError: No module named 'psycopg2'`. Reproduced locally and watched fail:
     `postgresql://` → 2 failed; `postgresql+psycopg://` → 7 passed.
  These are the three defects LoadCoach fixed in its own `db-matrix`, all still present here.
  The job now starts a `weightsdb`/`weightsdb`/`weightsdb_test` service matching the helper's
  documented default, sets `WEIGHTSDB_POSTGRES_URL` explicitly with `+psycopg`, and sets
  `WEIGHTSDB_REQUIRE_POSTGRES=1` so a skipped dialect fails rather than passing quietly.
- **Verified, not assumed:** `docker run --rm -e POSTGRES_PASSWORD=postgres -p 5433:5432
  postgres:16`, then the job's own invocation: **7 passed**, including the Alembic↔models parity
  check on both dialects.
- **What the next run must do:** Nothing. Keep running the PostgreSQL job's own invocation at every
  phase boundary; the local default never touches it.

## M7-9 — The coverage job died inside pytest-cov on a subprocess started from a temp directory

- **Severity:** NOTE (fixed)
- **Unit:** 3 (P1 storage and projects)
- **Where:** `tests/e2e/test_cli_skeleton.py::test_help_does_not_import_the_web_layer`
- **What happened:** The default gate was green and `--cov` ended in
  `INTERNALERROR … coverage.exceptions.DataError: Can't combine statement coverage data with branch
  data` — a whole-run abort, not a test failure. Cause: the test spawns a subprocess to prove
  `--help` imports no web framework, and the autouse fixture `chdir`s into `tmp_path`. pytest-cov
  starts coverage in a subprocess through a `.pth` hook that reads `pyproject.toml` **relative to
  the working directory**, so from the temp directory it measured without `branch = true` and wrote
  a data file the parent's could not combine with. Fixed by running the probe with `cwd` at the
  repository root. Only the `--cov` invocation could see it: exactly the HR2 gap, in a new shape.
- **What the next run must do:** Any test that spawns a Python subprocess passes `cwd` at the
  repository root, or the coverage job aborts.

## M7-10 — The first real push produced a run with **zero jobs**: the workflow did not parse

- **Severity:** NOTE (fixed)
- **Unit:** 3 (P1 storage and projects) / CI
- **Where:** `.github/workflows/ci.yml`, job `db-matrix`; guard in
  `tests/unit/test_ci_workflow.py`
- **What happened:** The prompt predicted the runner would find something no local gate can, and it
  did so on the first push — but not in the way expected. Run **33431574307** on `fde44b2` came
  back `failure` with **`total_count: 0` jobs**, `created_at == updated_at` (zero elapsed), no
  check-runs, and a run **name of `.github/workflows/ci.yml` rather than `CI`** — the fallback
  GitHub uses when it cannot read the file's `name:` key. The cause was my own edit: patching the
  `db-matrix` step's environment left the **previous `env:` block in place**, so one step carried
  two `env:` keys. GitHub's parser refuses a duplicate mapping key and rejects the whole workflow;
  **PyYAML accepts it silently** (last value wins), so `yaml.safe_load` reported the file as valid
  and every local check passed. A workflow that runs zero jobs looks exactly like a workflow that
  ran and failed, if you only read the conclusion.
- **The general lesson, beyond this bug:** "run the CI jobs, not just the local gate" (HR2) assumes
  the jobs *run*. This repository's four earlier runs were all `failure` too, and nobody had
  distinguished "the suite failed" from "the file did not parse" — the distinguishing evidence is
  the job count and the elapsed time, not the conclusion.
- **What was done:** Removed the stale block, and added `tests/unit/test_ci_workflow.py` — six
  tests that load the workflow through a `SafeLoader` subclass which **refuses duplicate keys the
  way GitHub does**, and then assert the properties three separate handoff entries have now been
  written about: every job names its runner and has steps; no job selects a pytest marker this
  repository does not declare (HR2 defect 2); the PostgreSQL job's URL names the `+psycopg` driver
  the project installs (M7-8); it sets the variable the shared helper actually reads; and the
  service's credentials match that URL, so a job cannot again start a server nothing connects to.
- **What the next run must do:** Read the **job count**, not only the conclusion, when checking a
  run. `curl … /actions/runs/<id>` with `total_count: 0` and a `name` equal to the workflow path
  means the file did not parse, and no amount of reading test logs will explain it.

## M7-11 — CI green on the real runner for the first time in this repository's history

- **Severity:** NOTE
- **Unit:** 3 (P1 closeout) / CI
- **Where:** run **33431811117** on `3a2e6ad`
- **What happened:** **13 jobs, 13 successes.** `format`, `lint`, `types`, `boundaries`,
  `tests (3.12)`, `tests (3.13)`, `tests-314-early-warning`, `tests (PostgreSQL)`, `coverage`,
  `contracts`, `security`, `build`, `install-check`. Three of these had never once done their job:
  `tests (PostgreSQL)` had never run a query, `contracts` had never collected a test, and the
  workflow itself had not parsed on the previous push. The 3.14 early-warning job — which is
  `continue-on-error` — **passed**, so there is no forward-compatibility finding to report.
- **What the next run must do:** Nothing. Keep the runner green; a red runner is a unit that is
  not done.

## M7-12 — ADR-0038 written; the machine-wide single-model policy and the estimator question

- **Severity:** DECISION
- **Unit:** 4 (P2 the port)
- **Where:** `docs/adr/0038-one-model-at-a-time-per-gpu.md`, plus corrections to
  `architecture/master-architecture.md` §5.2, `apps/ideapress/spec.md` §12 and §13, and
  `apps/ideapress/workflows.md` §6.2 — canonical first, mirrored, `cmp`-proven.
- **What happened:** Master Architecture §5.2's inference-concurrency bullet gave a policy for
  FreeWeight and LoadCoach and **named IdeaPress nowhere**, while IdeaPress's own spec §12 binds
  two models to a card that holds one with room for its context. The ADR states the rule in the
  user's terms — *two models contending for one GPU must both fit, with room for their context, or
  the later one waits; where a queue exists it waits by priority* — names LoadCoach's admission
  (`estimate_vram` + `device_fits` + `waiting_resources` + ageing, over a live telemetry snapshot)
  as the compliant reference implementation, and gives IdeaPress the narrower obligation that needs
  no queue: one generation in flight at one choke point, and an explicit unload before a switch.
  **The estimator question is answered with a recommendation, not an action:** extract
  `estimate_vram` to `modelrack` — which already owns `ResidentModel`, `RuntimeProfile` and the
  provider protocol the arithmetic reads — rather than duplicate it, with the consequences of both
  recorded. The extraction is **not performed**: it touches a published package and two 1.0
  applications. **How a standalone application participates** is answered decentrally: each checks
  live free VRAM before it loads and waits with the numbers, needing no broker (ADR-0010 holds),
  and optional for IdeaPress because `sweatmeter` is an optional extra.
- **What the next run must do:** The estimator decision is on the actions list and is the user's,
  because it changes a published package.

## M7-13 — NOTE: FreeWeight performs no free-VRAM preflight, and its skip reason is dead code

- **Severity:** NOTE (out of bounds for this run)
- **Unit:** 4 (P2 the port)
- **Where:** `FreeWeight/src/freeweight/` — evidence gathered, nothing changed
- **What happened:** ADR-0038's residual risk is cross-application, and FreeWeight is where it
  sits. Verified rather than assumed: `grep -rn "free_vram\|vram_free\|device_fits\|estimate_vram"
  src/freeweight/` returns **nothing** — FreeWeight loads whatever a benchmark needs without
  checking what another application is holding. And `insufficient_vram` appears exactly **once** in
  the whole repository, in `infrastructure/db/models_runs.py:263`, as a documented skip reason in a
  docstring; `grep` outside that file returns **zero** occurrences, so nothing ever sets it.
- **What the next run must do:** Nothing here — `FreeWeight/` is out of bounds for this run. The
  fix is ADR-0038 point 3's preflight in FreeWeight's benchmark runner, and it depends on the
  estimator decision. On the actions list.

## M7-14 — DECISION: `research` aside, the port refuses a schema its kind cannot enforce

- **Severity:** DECISION
- **Unit:** 4 (P2 the port)
- **Where:** `src/ideapress/domain/inference.py::ResponseFormat`
- **What happened:** The conformance suite, on its first run, failed on three of four adapters with
  ModelRack's `ResponseFormat(kind=json) must not carry a schema; a schema here would be silently
  ignored`. ModelRack is right and the port had the same hole: `json` asks for *valid JSON*,
  `json_schema` asks for *a shape*, and a schema attached to the former is discarded without a
  word. Since this is the application whose entire purpose is refusing gates that were never
  actually checked, the port now refuses the contradiction in `__post_init__` — at the place the
  mistake is written, not three frames down inside an adapter.
- **What the next run must do:** Nothing. A stage wanting a shape enforced uses `kind="json_schema"`.

## M7-15 — An `UNSUPPORTED` measurement reaching JSON made `/health` a 500 when the backend was down

- **Severity:** NOTE (fixed)
- **Unit:** 4 (P2 the port)
- **Where:** `src/ideapress/infrastructure/backends/_modelrack.py::to_backend_health`
- **What happened:** Found by running the suite under `unshare -rn`, and **only** there — five
  tests failed with `TypeError: Object of type Unsupported is not JSON serializable`. ModelRack
  reports `model_count` and `latency_ms` as `Measurement`, which is the `UNSUPPORTED` sentinel when
  the provider did not answer; ADR-0016 makes that sentinel raise rather than coerce, which is
  exactly right and exactly what the adapter had failed to handle. So `/health` returned **500 in
  the one state spec §20 AC7 requires to keep working**. Sanitised at the adapter boundary —
  `UNSUPPORTED` becomes `None`, meaning "not reported", never `0`. A second bug in the same state:
  the backend page used Jinja's `is not None` where the test is spelled `is not none`, which only
  evaluates when a count is missing, i.e. only when the backend is down. Both now have regression
  tests that run with nothing listening.
- **What the next run must do:** Run the suite under `unshare -rn` at every phase boundary. The
  degraded path is the one no ordinary run exercises, and it is the path the product promises.

## M7-16 — DECISION: `gemma4:12b` returns **empty text** on its first call after a cold load

- **Severity:** DECISION
- **Unit:** 4 (P2 the port)
- **Where:** measured against real Ollama; handled in `services/inference.py`
- **What happened:** The single most consequential finding of this unit, and it is about a shipped
  default. `gemma4:12b` — spec §12's binding for **`draft`**, the most important stage in the
  product — enters a runaway reasoning loop on the **first generation after a cold load**: it
  consumes its entire output budget thinking and returns `finish_reason="length"` with an **empty
  string**. The next call is clean. Measured, not inferred:

  | budget | first call after load | second call |
  |---|---|---|
  | 64 | 64 tokens, empty | — |
  | 512 | 512 tokens, empty | — |
  | 2048 | 2048 tokens, empty | 184 tokens, correct answer |

  Reproduced **three times in three** with an explicit `unload` between cycles, and **not observed
  at all** for `qwen3.5:9b-q8_0`, which answered identically cold and warm. The interaction is what
  makes it serious: ADR-0038 unloads before every model switch, so a cold load is **guaranteed on
  every alternation** between the two default models — meaning that without handling, the
  documented default configuration cannot draft a single unit.
- **What was done:** A **bounded, recorded, transport-level retry** at the choke point: when a
  result is both truncated and empty, `InferenceGateway.run` retries exactly once and attaches an
  `empty_generation_retried` degradation. The distinction carries the justification — the provider
  returned an empty body, so there is nothing to validate, nothing to repair, and nothing a model
  decided. It does **not** consume `max_attempts_per_stage`, which exists for defects in content
  that exists, and three tests hold the bound: retried once, never twice, and a *non-empty*
  truncation is not retried at all.
- **What the next run must do:** This is on the actions list as a product judgement. The retry is
  a workaround for a model's behaviour, and the honest alternatives are to bind `draft` to
  `qwen3.5:9b-q8_0` (one model, no switches, no cold-load loop) or to a different drafting model.
  Unit 12 measures what the two-model default actually costs so the choice can be made on evidence.

## M7-17 — I9: the prompt-record hash under this run's installed `setspec`

- **Severity:** NOTE
- **Unit:** 4 (P2 the port)
- **Where:** `src/ideapress/prompts/`, `tests/unit/test_prompt_pack.py`
- **What happened:** IdeaPress's pack is `ideapress.stages` 1.0.0 on `setspec.prompts` 0.4.0 — the
  same version FreeWeight and LoadCoach have installed. The record `stages.hello` 1.0.0 hashes to
  **`sha256:b9f17cf04bb076bcd7a660e169a73238e41e63987fead814d52bb36d6d7e1cb5`**, and a test pins
  that literal. If it ever disagrees with a sibling's installed `setspec`, the packs are no longer
  comparable and every prompt-version provenance claim across the suite is suspect.
- **What the next run must do:** Keep the pinned figure. Regenerate the manifest with
  `setspec.prompts.build_manifest` after any prompt edit; the pack refuses to load otherwise.

## M7-18 — DECISION: reduction is strictly ordered, not greedy, and a test caught the difference

- **Severity:** DECISION
- **Unit:** 7 (P4 validators and context)
- **Where:** `src/ideapress/domain/context_assembly.py`
- **What happened:** The first implementation filled the context budget greedily — take the most
  valuable section, and if it does not fit, try the next. A test squeezing the budget caught the
  consequence: an **unreferenced** research note survived because it was short, while the note the
  unit's own title named was dropped because it was long. That utilises the budget better and
  violates the ranking workflows §7 states ("ranked by explicit reference"). Changed so that once a
  section does not fit, everything less valuable is dropped too, even if it would have fitted.
  A reduction whose outcome depends on the relative *sizes* of what it is reducing is one nobody
  can predict or test.
- **What the next run must do:** Nothing. `test_the_reduction_order_is_exactly_the_documented_one`
  compares the observed drop sequence against `REDUCTION_ORDER` rather than against a comment.

## M7-19 — DECISION: the structured stages needed a 4× output budget, measured not guessed

- **Severity:** DECISION
- **Unit:** 8 (P4 core loop)
- **Where:** `services/requirements.py::STRUCTURED_OUTPUT_TOKENS`,
  `services/unit_loop.py::DRAFT_THINKING_FLOOR_TOKENS`
- **What happened:** The first live P4 run failed with *"The requirement compiler did not return
  JSON: Expecting value: line 1 column 1"* — which is a JSON parser reporting a **malformed**
  answer when in fact there was **no** answer. `qwen3.5:9b-q8_0` compiling requirements from a
  six-line brief spent its entire 4 096-token allowance on reasoning and emitted nothing. Measured
  at three budgets against the real model:

  | budget | outcome |
  |---|---|
  | 4 096 | `finish_reason=length`, 4 096 output tokens, **empty string** |
  | 8 192, `json_schema` | `stop`, 278 tokens, correct JSON |
  | 8 192, plain text | `stop`, 5 790 tokens (thinking counted), correct JSON |

  This is M7-16's finding generalised: **a reasoning model's thinking is spent from the same
  allowance as its answer**, so an output budget sized for the answer returns nothing at all. Raised
  the structured stages to 8 192 and gave drafting an 8 192-token floor *before* the per-word
  allowance, both with the measurement in the docstring.
- **What was also done:** the empty-after-retry case now raises `CONTEXT_LIMIT_EXCEEDED` naming the
  budget, instead of letting an empty string reach a parser that misdiagnoses it. The misdiagnosis
  was the expensive part: the error sent the reader looking for a malformed answer.
- **What the next run must do:** Treat any new model-using stage's `max_output_tokens` as
  thinking-plus-answer, and measure rather than estimate. On the actions list as a tuning
  question if a user swaps in a non-reasoning model, where these budgets are simply generous.

## M7-20 — NOTE: a blocking requirement with no deterministic check can only be cleared by P5

- **Severity:** NOTE
- **Unit:** 8 (P4 core loop)
- **Where:** `domain/commit.py::decide_commit`, observed live
- **What happened:** Against a real model the pipeline built a plan whose **R-003 — "The finished
  work must keep each section short"** — was compiled `blocking` with **no deterministic check**,
  because nothing literal expresses it. Workflows §3 says such a requirement "is evaluated by audit
  and is flagged as such", and the audit stages are P5. So at P4 the unit correctly drafted, passed
  all 23 validation checks, satisfied its checkable requirement, and **paused** — because one
  blocking requirement had nothing that could settle it yet. That is the right behaviour and not a
  bug, but the message said only "1 blocking requirement(s) unmet: R-003", which sends a reader
  looking for missing content that was very likely already there. The refusal now separates the two
  cases and names the review stage for the second. The live P4 test asserts that a pause, if it
  happens, is *this* shape and no other.
- **What the next run must do:** P5's review stages supply `audit_satisfied`, which is the only
  thing that can clear such a requirement. Note the asymmetry that keeps T1 intact and is tested:
  an audit may satisfy a requirement **no check covers**, and can never overturn a check that ran.

## M7-21 — NOTE: the compiled checks are weaker than they look, and a person should see that

- **Severity:** NOTE
- **Unit:** 8 (P4 core loop)
- **Where:** observed in a live plan; the prompt pack is `stages.requirements.compile` 1.0.0
- **What happened:** The compiler produced, for *"must state that inference runs entirely on the
  reader's own machine"*, the check `must_contain_any: ['inference', "reader's", 'own', 'machine']`
  — which passes on the word "inference" alone. The requirement is correctly grounded and correctly
  blocking; the *check* gives far more assurance than it earns, and a unit could satisfy it while
  saying nothing about where inference runs. `must_contain_all` would have been the right kind here.
- **What the next run must do:** This is prompt-pack work, and it is on the actions list as a
  judgement rather than fixed blind: tightening the instruction toward `must_contain_all` risks the
  opposite failure (T4, validators too strict) and the trade-off wants a human view. The coverage
  report already shows the exact check beside the requirement, so the weakness is visible rather
  than hidden — which is the property that matters most until it is tuned.

## M7-22 — The atomic commit, proven by a killed process rather than an exception

- **Severity:** NOTE
- **Unit:** 8 (P4 core loop)
- **Where:** `tests/integration/test_atomic_commit.py`
- **What happened:** P4's named failure mode is a partial commit. Three kinds of evidence, not one:
  an exception injected at two different real seams inside the transaction (patching a function the
  commit actually calls, with no test hook in production code), and — the one the run's prompt asks
  for — a **child process `SIGKILL`ed with its commit transaction open**, after which the database
  is reopened from scratch. SIGKILL cannot be intercepted and no `finally` runs after it, so what
  the reopened database contains is what a reader would see after a power cut: no version row, no
  coverage rows, the unit still in the state it was, and version 1 still free for a later commit.
- **What the next run must do:** Nothing. Keep the SIGKILL test; an exception test alone proves the
  `with` block, not the durability.

## M7-23 — A stale ruff cache made the local gate green while CI's lint job was red

- **Severity:** NOTE (fixed)
- **Unit:** 9 (P5) / CI
- **Where:** run **33442145721**, job `lint`; `src/ideapress/domain/validators/__init__.py`
- **What happened:** Twelve of thirteen jobs green, `lint` red, and the **same ruff version**
  (0.16.5) in both places. The difference was the cache: locally `ruff check .` reads
  `.ruff_cache/` and reported no error; CI has none and found an unsorted import block that an
  earlier edit had left, without invalidating the cached result for that file. This is HR2's lesson
  in a shape no amount of care closes — the local command was correct and its answer was wrong.
- **What the next run must do:** Run **`ruff check --no-cache`**. It is what CI runs by
  construction and costs about a second. Adopted in this repository's gate from unit 9 onward.

## M7-24 — DECISION: export reduction is strict, and the locale test found a real bug

- **Severity:** DECISION
- **Unit:** 10 (P6 exporters)
- **Where:** `src/ideapress/domain/exporters/`, `tests/unit/test_exporters.py`
- **What happened:** Risk T8's falsification was run as the prompt specified — export under four
  combinations of `PYTHONHASHSEED`, `LC_ALL` and `TZ`, in **real subprocesses** (the hash seed is
  read at interpreter startup and cannot be changed from inside a running one, so an in-process
  test would prove nothing) — and it **found a bug**: the JSON exporter used
  `dataclasses.asdict`, which preserves a tuple in the order it arrived, while the Markdown and
  HTML exporters sorted the same degradations at render time. The same project would have produced
  two different JSON files depending on the order rows came back from the database. Fixed by
  sorting in `build_payload`.
- **Design decisions recorded:** the export document has **no `generated_at`** — a wall-clock stamp
  is the commonest cause of an export that differs from itself and carries nothing the units' own
  `committed_at` does not; `ensure_ascii=False` is fixed (the content is the user's writing, often
  not ASCII, and escaping it makes the file unreadable to its owner); files are written with
  `newline="\n"` on every platform (risk P2); the HTML is one file with inline CSS and no `<link>`,
  no `<script src>`, no `@import` and no absolute URL at all.
- **What the next run must do:** Keep the subprocess matrix. A single "export twice" assertion in
  one process would not have caught this.

## M7-25 — M7-9's subprocess trap recurred, and is now closed by a ratchet

- **Severity:** NOTE (fixed)
- **Unit:** 10 (P6 exporters)
- **Where:** `tests/unit/test_import_boundaries.py::test_every_subprocess_in_the_suite_names_its_working_directory`
- **What happened:** The coverage run aborted again with
  `DataError: Can't combine statement coverage data with branch data` — the same cause as M7-9, in
  two *new* subprocesses (the offline-HTML check under `unshare -rn`, and the SIGKILL child). The
  autouse fixtures `chdir` into a temporary directory; pytest-cov's subprocess `.pth` hook reads
  `pyproject.toml` relative to the working directory, so from anywhere else it measures without
  `branch = true` and writes a data file the parent's cannot combine with. It aborts the whole
  `--cov` run **inside pytest-cov** rather than failing a test, and only the coverage job sees it.
- **What was done:** Both fixed, and a test now walks the AST of every test module and fails any
  `subprocess.run`/`Popen`/`check_output` that does not pass an explicit `cwd`. Remembering did not
  work twice; a ratchet does.
- **What the next run must do:** Nothing. Adding a subprocess without a `cwd` now fails a test.

## M7-26 — `/api/v1/docs` and `/openapi.json` were 500s, and only the consistency review saw it

- **Severity:** NOTE (fixed)
- **Unit:** 13 (M7 closeout)
- **Where:** six modules under `src/ideapress/web/routes/`
- **What happened:** Roadmap §8's review compares spec §7.1's endpoint list against the running
  application. Getting that list required `app.openapi()`, and **it raised**:
  `PydanticUserError: TypeAdapter[Annotated[ForwardRef('JSONResponse'), …]] is not fully defined`.
  Every route module annotated its handlers' return types with Response subclasses imported only
  under `TYPE_CHECKING`; FastAPI reads that annotation at **runtime** to build the schema, and
  under `from __future__ import annotations` it saw forward references it could not resolve. So
  the interactive docs and the OpenAPI document were 500s on a build whose 632 tests were green,
  because not one of them asked for the schema. A contract test asks now.
- **What the next run must do:** Any handler returning a Response subclass imports that type at
  **runtime**, not under `TYPE_CHECKING`. The contract test catches a regression.

## M7-27 — The consistency review found four endpoints and two command groups unbuilt

- **Severity:** NOTE (fixed)
- **Unit:** 13 (M7 closeout)
- **Where:** `web/routes/settings.py` (new), `web/routes/stages.py`, `web/routes/units.py`,
  `cli/commands/{workflow,prompts}.py` (new), `cli/commands/unit.py`
- **What happened:** Spec §7.1 lists 25 endpoints and the build had 22; §7.2 lists thirteen command
  groups and the build had eleven. Missing: `GET`/`PUT /settings`, `GET /workflows/{id}`,
  `POST /projects/{id}/units/{unit_id}/revise`, `ideapress workflow` and `ideapress prompts` — none
  of them named in any P1–P6 work list, which is how they were missed. All are built.
  `GET /export/formats` existed in the code and in no document; spec §7.1 gained it, canonical
  first. A contract test now compares the specification's list against the live OpenAPI schema, so
  the review is a test rather than a reading.
- **Still absent and deliberately so:** `ideapress project import|export` (archive handling, spec
  §14's hardening against traversal, symlinks and decompression bombs) is in spec §7.2 and in **no**
  P1–P6 work list. It is M8's, and `services/project_archive.py` remains a scaffold.
- **What the next run must do:** Build `project import|export` in M8 with §14's hardening.

## M7-28 — NOTE: spec §15's performance budgets are not asserted anywhere

- **Severity:** NOTE (open)
- **Unit:** 13 (M7 closeout)
- **Where:** spec §15; `tests/` has no `performance` marker in use
- **What happened:** Seven budgets are specified — 50 ms orchestration overhead per attempt, 200 ms
  to validate a 5 000-word unit, 300 ms to load a 100-unit project, 2 s and 5 s for the two
  document exports, 300 ms editor render, 100 ms autosave — and **none is measured by a test.** The
  `performance` marker is declared and applied to nothing. No P1–P6 work list asks for them
  (FreeWeight's equivalent landed in its P13 hardening phase), so this is a real gap rather than a
  regression, and it is stated here rather than left for a verification to discover.
- **What the next run must do:** M8's hardening phase measures all seven, on a real socket for the
  two that are about a page. The verification prompt asks Fable to measure them meanwhile.

## M7-29 — The demonstration found the run's most serious bug: a second process killed a live stage

- **Severity:** DECISION (fixed)
- **Unit:** 12 (the demonstration) → `services/stages.py`, migration `0005`
- **Where:** `StageRunner.mark_interrupted`
- **What happened:** Three units into the first real drafting run, the stage went to
  `interrupted` and the project review then failed with `STAGE_ALREADY_RUNNING`. Nothing had
  crashed. `mark_interrupted()` runs whenever a `Runtime` is built — workflows §9 asks for it at
  startup — and the first version marked **every** row still `running`, on the assumption that a
  fresh process means every earlier run is dead. I had opened a second process to read the plan
  while the draft was going, and it marked the live run as interrupted. The runner's task registry
  still held the thread, so the next stage was refused.
  **This is not a test artefact.** `ideapress unit list`, `ideapress plan show` or a second
  `ideapress serve` in another terminal would have done exactly the same to a real user's
  half-finished document — and the state it leaves behind looks like a crash, so the user would
  have gone looking for one.
- **What was done:** Migration `0005` adds `owner_pid` and `owner_boot_id` to `stage_runs`, and a
  run is marked interrupted only when its owner is demonstrably gone: the boot id differs (nothing
  from an earlier boot can still be running), or the PID names no living process. A row with **no**
  recorded owner is left alone — it predates the columns, and an un-marked dead run is visible and
  resumable by hand while a marked live one destroys work in progress. PID reuse within one boot
  could make a dead run look alive; the consequence is that it stays `running` until someone looks,
  which is the harmless direction. Four tests, including one that starts a real second `Runtime`
  over the same database while a stage thread is running.
- **What the next run must do:** Nothing. Note the general shape for M8: **any query that decides
  something about "other processes" needs to know who owns what.** This is the only such query in
  the build; a second one should carry ownership from the start.

## M7-30 — Spec §15's budgets, measured rather than asserted

- **Severity:** NOTE
- **Unit:** 13 (M7 closeout)
- **Where:** measured against a process started by `ideapress serve` on a real socket, port 8791
- **What happened:** M7-28 records that no test asserts these. Measured anyway, so the closeout
  reports numbers rather than a gap:

  | Budget (spec §15) | Target | Measured |
  |---|---|---|
  | Editor page render | ≤ 300 ms | **1.2 ms** (first request 31 ms, template compile) |
  | Validation of a 5 000-word unit | ≤ 200 ms | **8.3 ms** for a **9 800**-word unit |
  | `/health` | — | 3.7 ms |

  Not measured, because they need a 100-unit project this run did not build: project load at 100
  units, and the two 100-unit export budgets. Stage orchestration overhead excluding inference is
  not separable from the measurements this build takes; M8's hardening phase should instrument it.
- **What the next run must do:** M8 asserts all seven under the `performance` marker, which is
  declared here and applied to nothing.

## M7-31 — AC1 and AC7 on a real socket, and Host validation before routing

- **Severity:** NOTE
- **Unit:** 13 (M7 closeout)
- **Where:** `ideapress serve` with `IDEAPRESS_INFERENCE__OLLAMA__BASE_URL=http://127.0.0.1:1`
- **What happened:** Started with **zero configuration** and a backend pointed at a port nothing
  listens on. It served. `/api/v1/health` answered **200** with `status: degraded` — `database ok`,
  `backend degraded`, `prompts ok` — which is AC1 and AC7 together: an unreachable backend is a
  health component, never a startup failure.
  ADR-0026, on the same real socket rather than through `TestClient`:

  | Request | Result |
  |---|---|
  | `Host: evil.example.com` → `/api/v1/version` | **421** |
  | `Host: evil.example.com` → `/no-such-path` | **421**, not 404 |
  | `Host: localhost:8791` → `/api/v1/version` | 200 |

  The middle row is the one that matters: a path with **no route** is refused at 421, which is only
  possible if the check runs before the router is consulted.
- **What the next run must do:** Nothing. Repeat on a non-loopback bind at M8, which this run did
  not do because it would mean exposing the machine.

## M7-32 — The demonstration's cost was measured on a shared card

- **Severity:** NOTE
- **Unit:** 12 (the demonstration)
- **What happened:** The user sent their own request to the same Ollama instance while the
  demonstration was running. The residency poll shows the invariant held throughout — `n=0` and
  `n=1` only, never two — which is *better* evidence than a quiet machine would have been, because
  the card was genuinely contended and still never held two models.
  **But the timing figures are from a shared card.** A competing request can evict IdeaPress's
  model and force an extra ~12 GB reload on the next stage, so the wall-clock numbers in
  `cost.json` are an upper bound rather than a clean measurement. They are reported as such.
- **What the next run must do:** Measure the two-model default's reload cost on a quiet machine
  before deciding whether to keep it — that decision is on the actions list and wants a clean
  number.

## M7-33 — The demonstration: what it cost, and what the two-model default is buying

- **Severity:** NOTE
- **Unit:** 12 (the demonstration)
- **Where:** `IdeaPress/.m7-evidence/m7-demo/` — brief, transcript, three exports, hashes,
  `resident-poll.log`, `provenance.json`, `cost.json`
- **The run:** a 268-word brief → **12 compiled requirements**, all grounded in it → **4 units**,
  all committed → `project_review` → three exports → a `--resume` pass that skipped all four.
  Wall clock **31 minutes**, **14 model calls**, and **only Ollama present** (`pip list` shows
  neither `loadcoach` nor `freeweight`).

  | stage | calls | provider time | in | out |
  |---|---|---|---|---|
  | requirements | 1 | 184 s | 7 389 | 1 087 |
  | outline | 1 | 155 s | 5 225 | 361 |
  | draft | 4 | 339 s | 3 226 | 15 157 |
  | audit_fast | 4 | **473 s** | 22 008 | **28** |
  | critique | 4 | **334 s** | 16 672 | **190** |

- **The single-model invariant, observed:** **620 samples over 1 860 s, maximum 1 model resident,
  0 samples with more than one**, across **9 switches**, eight of which reported `unloaded=True`
  (the first had nothing to unload). Evidence, not an assertion.
- **What the two-model default costs.** The unload calls themselves total **390 ms across all nine
  switches** — nothing. The cost is the *reload*, and it is hidden inside the next call's
  `provider_ms`: `audit_fast` spent **473 seconds to emit 28 tokens** and `critique` **334 seconds
  to emit 190**. Those figures are almost entirely a 12.6 GB model being read back off disk. **Of
  1 860 s of wall clock, roughly 800 s — 43 % — is model loading caused by alternating bindings.**
  Binding every stage to one model would remove nine reloads and cut the run to well under twenty
  minutes.
- **Caveat (M7-32):** the card was shared with a user request during the run, so these are an upper
  bound.
- **What the next run must do:** The two-model default is on the actions list as a product
  judgement, and this is the number to judge it on.

## M7-34 — What the workflow actually produced, and my honest opinion of it

- **Severity:** DECISION (a finding about the workflow, not a defect to fix blind)
- **Unit:** 12 (the demonstration)
- **Where:** `.m7-evidence/m7-demo/data/…/what-a-local-model-actually-costs-you.md`, 1 884 words
  including the provenance appendix; roughly 950 words of article

**Is it any good? Partly, and the parts that are bad are bad in ways the workflow caused.**

**What works.** The third unit is genuinely useful writing: it names real hardware (RTX 3060/4070,
8–16 GB, 12 GB as the mid-range benchmark), explains the actual mechanism (a model that exceeds
VRAM offloads to system RAM and slows down), and lands quantization as the practical consequence. A
reader learns something they can act on. The fourth unit is careful and correct where the brief
demanded care — it separates hardware speed from model accuracy and never claims local is better.
The document is under 1 200 words, uses neither banned word, and ends without a summary. Structure
follows the brief.

**What does not, and why.**

1. **Marketing register, which the brief forbade in as many words.** "a significant leap in both
   autonomy and security"; "The core benefit of this architecture is the absolute privacy it
   provides for your intellectual property"; "This approach empowers you to explore the boundaries
   of your craft with the peace of mind that your work remains exclusively yours." The brief said
   *"no marketing register"* and *"they are not comfortable being sold to"*. The compiler turned
   that into **R-012, blocking, with no deterministic check**, so it was settled by an audit that
   found nothing. **The most visible failure against the brief passed the gate.**

2. **The deterministic checks made the prose worse.** This is the sharpest finding of the run. The
   compiler rendered "must state that inference runs entirely on the reader's own machine" as
   `must_contain_any: ["inference runs entirely on the reader's own machine"]` — the brief's exact
   sentence. The article is in the second person throughout, so satisfying that check produced:
   *"Because inference runs entirely on **the reader's** own machine, **your** data is never
   transmitted…"* — a person-shift a reader trips over. U-02 does the same with "the reader
   supplies the hardware". A gate designed to guarantee content instead dictated phrasing, and the
   phrasing it dictated is wrong for the piece.

3. **Repetition nothing caught.** U-01's second, third and fourth paragraphs each say "your work
   stays private" in different words. U-03 and U-04 both explain quantization from scratch. The
   per-unit audit cannot see across units by construction, and `project_review` — which can —
   returned no findings.

4. **It is padded.** Around 950 words for four ideas, with sentences that restate their
   predecessor: *"This thermal behavior is not a flaw but a result of the high-intensity processing
   required to generate coherent text locally."*

**Which stage is responsible.** Chiefly the **compiler** (`stages.requirements.compile` 1.0.0), on
two counts: it produces blocking requirements with no check for exactly the qualities that most
need one, and it produces literal checks that quote the brief instead of naming what the text must
*say*. Second, the **critique threshold**: four units, four audits, **zero findings**, and every
critique returned `acceptable` or `leave_it_alone` on the first pass. 807 seconds of the run went
to audit and critique and produced 218 output tokens and no change to anything. Not the validators
— 23 to 25 checks ran per unit and were right. Not the context budget — nothing was dropped.

**The honest summary: the deterministic machinery works and the model-assisted machinery earned
nothing in this run.** A workflow whose gates are sound and whose reviewers never object produces
something that passes every check and that no editor would file. That is a finding about the
product, not about this run, and it is the first item on the actions list.

---

# Spec §20's twelve acceptance criteria

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | `ideapress serve` produces finished content with **only Ollama** | **Met** | The demonstration: 4 units committed and exported from a 268-word brief, `pip list` showing neither `loadcoach` nor `freeweight`. Not tested from a *published* wheel — the package is unpublished, which is M8's |
| 2 | Switching `inference.mode` needs no workflow code change | **Partially — LoadCoach is M8** | The three-way parity test covers `ollama` / `openai_compatible` / fake and asserts identical unit count, states, coverage and requirement set with only wording differing. The `loadcoach` mode is a stub that refuses by name; spec §20's own wording names all three, so this is not claimed in full |
| 3 | No model output can end a gated stage | **Met** | Both mutation checks watched failing: the plan gate accepting "no requirements needed" (1 test fails), the commit gate honouring a critique verdict (6 fail, one on the *signature*). `decide_commit` has no parameter a model can speak through |
| 4 | Every stage output passes deterministic validation before commit | **Met** | 23–25 checks per unit in the live run; `decide_commit` refuses on any blocking failure; seven validator families with 67 tests |
| 5 | A failed or cancelled stage leaves committed units intact and is resumable | **Met** | SIGKILL mid-commit leaves no partial version and version 1 still free; cancellation stops at the next model-call boundary and commits nothing; `--resume` skipped all four committed units in the live run |
| 6 | Every committed unit records backend, model, prompt versions, coverage, validations | **Met** | Asserted field by field, and printed from the live run: `ollama/gemma4:12b@sha256:4eb23ef1…`, `stages.draft.write 1.0.0 sha256:a9d0040b…`, tokens, timing, degradations, coverage per requirement naming what decided it |
| 7 | LoadCoach unavailable ⇒ fallback or clear error; **never a startup failure** | **Partially — LoadCoach is M8** | The "never a startup failure" half is met and demonstrated on a real socket: with the backend pointed at a dead port, `/health` is **200 · degraded**. The LoadCoach adapter itself is P7 |
| 8 | IdeaPress imports nothing from FreeWeight or LoadCoach | **Met** | `lint-imports`: contract kept. An AST walk finds zero imports of either, including inside function bodies |
| 9 | Exports are deterministic and byte-stable | **Met** | The live artefacts re-exported byte-identically under three environments including `LC_ALL=tr_TR.UTF-8` and `TZ=Pacific/Kiritimati`, and `sha256sum` reproduces the recorded hash |
| 10 | Model output with scripts, template syntax or traversal is stored and rendered inert | **Met** | Escaped in every view and in the HTML export; kept verbatim and never evaluated in Markdown and JSON; a traversal blocks the commit outright |
| 11 | Full suite passes with no backend reachable and no network | **Met** | 636 passed under `unshare -rn`. Two bugs were found by running it that way and fixed |
| 12 | All IdeaPress gold standards met | **Partially** | Four of six met; two partial — see below. Not claimed on the strength of a passing suite |

# Gold Standards §2's six IdeaPress bullets

| Bullet | Verdict | Evidence |
|---|---|---|
| Runs a complete workflow with **no** LoadCoach and no FreeWeight installed | **Met** | The demonstration, in a venv containing neither |
| Switching the backend changes configuration only; a test runs the identical workflow against all three | **Partially** | Two real adapters plus the fake are compared; the third (LoadCoach) is M8 |
| Python owns control flow; a test proves "everything is fine, stop" does not end a gated stage | **Met** | Both mutation checks watched failing |
| Every stage output passes deterministic validation before commit | **Met** | As AC4 |
| A project survives an interrupted stage: committed units intact, the failed stage resumable | **Met** | SIGKILL mid-commit, and `--resume` in the live run |
| Every generated artifact records the model, prompt version and validation results | **Met** | As AC6, and carried into all three export formats |

**Not claimed:** spec §15's seven performance budgets are unasserted (M7-28); two were measured
(M7-30) and both are far inside their targets, but "all gold standards met" is not a claim this run
makes on the strength of that.

---

# Entry status

Every `M7-*` entry, and what closes anything still open.

| Entries | Status |
|---|---|
| M7-1, 4, 5, 8, 9, 10, 11, 15, 17, 22, 23, 25, 26, 27, 29, 30, 31, 32, 33 | **Closed** in this run — each fixed, or recorded as measurement |
| M7-2, 3, 6, 7, 12, 14, 18, 19, 24 | **DECISION, closed.** On the actions list only where a reasonable person might choose otherwise (M7-19's budgets, M7-12's estimator) |
| **M7-13** — FreeWeight has no free-VRAM preflight | **Open.** Out of bounds for this run. Closed by ADR-0038 point 3 in FreeWeight's benchmark runner, which waits on the estimator decision (action 3) |
| **M7-16** — the `gemma4:12b` cold-load runaway and its retry | **Open as a product judgement.** Closed by action 2: keep the two-model default, or bind `draft` elsewhere |
| **M7-20** — a blocking requirement with no check is settled by audit | **Open as an architectural question.** Closed by action 4: either workflows §3 licenses a model's opinion as a commit gate and the flagging is enough, or such requirements are advisory. The verification is asked to attack it |
| **M7-21, M7-34** — weak compiled checks, and what the workflow produced | **Open as the run's headline finding.** Closed by action 1 |
| **M7-28** — spec §15's budgets unasserted | **Open.** Closed by M8's hardening phase asserting all seven under the `performance` marker |

# There is no tag and no publish in M7

`__version__` is **0.1.0**. No tag exists, nothing was built for upload, `release.yml` was not
touched, and the PyPI name `ideapress` is **unregistered** (verified: `pip index versions ideapress`
→ *No matching distribution found*). `ideapress 1.0.0` is **M8's**, after P7–P9. Nobody should go
looking for a release step here.

---

# ACTIONS REQUIRED FROM YOU

1. **Read the document the workflow produced and decide whether the approach is worth carrying into M8.**
   - *Why it needs a person:* this is a judgement about writing quality, and no test in this
     repository can make it. My own reading is M7-34: the deterministic machinery works, the
     model-assisted machinery earned nothing — four audits produced **zero findings** across ~950
     words that an editor would mark up heavily, and the compiled checks actively made the prose
     worse by forcing the brief's third-person phrasing into a second-person article. You may read
     it more kindly, or less.
   - *Commands:*
     ```
     cd ~/ai/suite/IdeaPress/.m7-evidence/m7-demo
     cat brief.md
     sed -n '/^# /,/^---$/p' data/ideapress/projects/what-a-local-model-actually-costs-you/what-a-local-model-actually-costs-you.md
     ```
   - *How to tell it worked:* you have an opinion on whether a beta that generates this is worth
     P7–P9, and on which of the three levers to pull — the compiler's prompt, the critique
     threshold, or the check vocabulary.
   - **Blocking:** yes, on the direction of M8. Not on M7 being *built*.

2. **Decide whether the two-model default survives its measured cost.**
   - *Why it needs a person:* a product trade-off. Spec §12 binds `gemma4:12b` to `draft` and
     `qwen3.5:9b-q8_0` to everything else, on the view that prose drafting and structured work
     reward different models. The measurement says that costs **9 model switches and roughly 43 %
     of a 31-minute run** in reload time, and `gemma4:12b` additionally returns empty text on its
     first call after every cold load (M7-16), which the gateway papers over with one retry.
   - *Commands:*
     ```
     cd ~/ai/suite/IdeaPress
     cat .m7-evidence/m7-demo/cost.json
     # to try one model everywhere:
     .venv/bin/ideapress config init && $EDITOR ~/.config/ideapress/config.toml   # set draft = "ollama/qwen3.5:9b-q8_0"
     ```
   - *How to tell it worked:* a decision recorded in spec §12, and if you change it, a re-run whose
     `cost.json` shows one switch instead of nine.
   - **Blocking:** no.

3. **Approve ADR-0038, and decide where the VRAM estimator lives.**
   - *Why it needs a person:* it changes a **published package** and two 1.0 applications. The ADR
     recommends extracting LoadCoach's `estimate_vram` to `modelrack` rather than duplicating it,
     and deliberately does not perform the extraction. **FreeWeight's missing free-VRAM preflight
     (M7-13) waits on the same decision**: it loads a model for a benchmark without checking what
     another application is holding, and `insufficient_vram` exists in its code only as a docstring
     nothing sets.
   - *Commands:*
     ```
     cd ~/ai/suite/docs && cat adr/0038-one-model-at-a-time-per-gpu.md
     grep -rn "estimate_vram\|device_fits" ~/ai/suite/LoadCoach/src/loadcoach/domain/routing/constraints.py | head
     grep -rn "insufficient_vram" ~/ai/suite/FreeWeight/src/   # one docstring, nothing sets it
     ```
   - *How to tell it worked:* the ADR moves from Accepted to Accepted-with-the-estimator-decision,
     and a phase exists somewhere that does the extraction or the duplication.
   - **Blocking:** no for M7; yes before FreeWeight and IdeaPress can both preflight.

4. **Decide whether a model's opinion may settle a commit gate (M7-20).**
   - *Why it needs a person:* it is a reading of your own specification, and it is the sharpest
     open question in the build. Workflows §3 says a requirement with no deterministic check "is
     evaluated by audit and is flagged as such". Taken literally, an audit's verdict decides
     whether a **blocking** requirement is met — which is a model deciding a gate, the thing risk
     T1 exists to refuse. In the demonstration, **6 of 12 requirements had no check**, including
     "no marketing register", and the audit passed the one thing the piece most obviously failed.
     The alternative reading is that such requirements are advisory and the coverage report says so.
   - *Commands:*
     ```
     cd ~/ai/suite/docs && sed -n '/^## 3. Requirement compilation/,/^## 4./p' apps/ideapress/workflows.md
     cd ~/ai/suite/IdeaPress && XDG_DATA_HOME=$PWD/.m7-evidence/m7-demo/data .venv/bin/ideapress plan show <project-id>
     ```
   - *How to tell it worked:* either an ADR saying a labelled model-assisted guarantee may gate a
     commit, or a change making check-less requirements advisory. Today's behaviour is the first,
     by inheritance rather than by decision.
   - **Blocking:** yes, before M8 builds anything else on the coverage gate.

5. **Review the documentation this run wrote or changed.**
   - *Why it needs a person:* five documents were corrected canonical-first on my reading of a
     contradiction, and one is a new ADR. If a reading is wrong, everything built on it is.
     - `adr/0038-one-model-at-a-time-per-gpu.md` — new (action 3).
     - `architecture/master-architecture.md` §5.2 — IdeaPress added to inference concurrency.
     - `apps/ideapress/workflows.md` §2, §6 — **`research` reclassified as a no-model stage** and
       removed from `LOADCOACH_TASK_MAP` (M7-6). This is the correction most worth a second
       opinion.
     - `apps/ideapress/spec.md` §5 (`python-multipart`), §7.1 (`GET /export/formats`), §12
       (`[execution]`), §13 (`INSUFFICIENT_VRAM`).
   - *Commands:*
     ```
     cd ~/ai/suite/docs && git log --oneline 63314fa..HEAD
     git show <each commit>
     ```
   - *How to tell it worked:* you agree, or you have a correction to make before M8.
   - **Blocking:** no, but cheapest now.

6. **Run the M7 verification before M8 starts.**
   - *Why it needs a person:* deciding to spend the run, and reading a verdict that may be *not
     ready*. **F-13.4 is the precedent worth stating plainly: the M6 verification prompt was
     written and never executed, so no verification report exists for FreeWeight.** Say explicitly
     whether you want that to happen again here.
   - *Commands:*
     ```
     cat ~/ai/suite/m7-verification.prompt.md
     # then run it as Fable 5, max effort, in a fresh session
     ```
   - *How to tell it worked:* a verdict of ready / ready with conditions / not ready, with numbered
     findings, and its own reading of the document the workflow produced.
   - **Blocking:** yes, before M8.

7. **Decide whether to claim the PyPI name `ideapress` now.**
   - *Why it needs a person:* a decision about risk, not a step in M7. The name is **unregistered**.
     FreeWeight's was secured early by publishing an rc from its own `release.yml` (F-13.3); the
     same is available here and this run deliberately did not take it, because M7 contains no
     publish.
   - *Commands:*
     ```
     pip index versions ideapress          # No matching distribution found
     cd ~/ai/suite/IdeaPress && cat .github/workflows/release.yml   # untouched by this run
     ```
   - *How to tell it worked:* either `ideapress 0.1.0rc1` exists on PyPI under your account, or a
     recorded decision to accept the risk until M8.
   - **Blocking:** no.

8. **Add `extend-exclude = ["docs"]` to LoadCoach's and FreeWeight's `[tool.ruff]` (M7-2).**
   - *Why it needs a person:* those repositories are out of bounds for this run. Both are green
     only by luck — their mirrored documents happen to contain no fenced code ruff wants to
     reformat, and the next one that does will let `ruff format` silently edit a byte-identical
     mirror, which is the mechanism SUITE_REVIEW F-3 was raised about.
   - *Commands:*
     ```
     cd ~/ai/suite/LoadCoach && grep -n -A4 "^\[tool.ruff\]" pyproject.toml
     # add:  extend-exclude = ["docs"]      (py/ModelRack already carries it)
     cd ~/ai/suite/FreeWeight && grep -n "extend-exclude" pyproject.toml
     ```
   - *How to tell it worked:* `ruff format --check .` still passes in both, and a fenced Python
     block added to a mirrored document is left alone.
   - **Blocking:** no.

---

# Closeout evidence

**CI green on the real runner at head.** Run **33450206441** on `4b9314f`, **13 jobs, 13
successes**: `boundaries`, `build`, `contracts`, `coverage`, `format`, `install-check`, `lint`,
`security`, `tests (3.12)`, `tests (3.13)`, `tests (PostgreSQL)`, `tests-314-early-warning`,
`types`. The 3.14 early-warning job is `continue-on-error` and **passed** — no forward-compatibility
finding. Four earlier runs in this repository's history were red; the first green one was
33431811117, after the workflow was made to parse.

**The gate, under two interpreters.**

| | Python 3.13.15 (local venv) | Python 3.12.14 (Docker `python:3.12-slim`) |
|---|---|---|
| `ruff format --check .` | 144 files formatted | 144 files formatted |
| `ruff check --no-cache .` | passed | passed |
| `mypy src tests` | 140 source files, no issues | 140 source files, no issues |
| `lint-imports` | 4 contracts kept | 4 contracts kept |
| `pytest -m "not live and not performance"` | **639 passed**, 5 skipped | **638 passed**, 6 skipped |

Beyond the documented gate: coverage **89.36 %** against an 85 floor and **98 %** in `domain/`
against 95; `-m contract` **123 passed**; `tests/integration` against a real PostgreSQL 16
**94 passed**; the whole suite under `unshare -rn` **639 passed**; `-m live` **4 passed** against
real Ollama.

**Nothing from P7–P9 was built.** `infrastructure/backends/loadcoach.py`, `services/feedback.py`
and `services/project_archive.py` are each still a 4-line scaffold; `LOADCOACH_TASK_MAP` appears in
**no** source file; `inference.mode = "loadcoach"` is refused by name with "not built yet; it
arrives in Phase 7".

**No `loadcoach` or `freeweight` import exists anywhere under `src/`** — zero, by grep and by an
AST walk that also sees imports inside function bodies, and by `.importlinter`'s own contract.

**`__version__` is `0.1.0`, there are no tags, and nothing was published.**
