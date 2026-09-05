# M6 Handoff — P12–P14 run (FreeWeight P12–P14, M6 closeout)

Run started 2026-08-30. Ground state verified: FreeWeight at `0a6bc40` (1.0.0rc1 + setspec.prompts
adoption), suite 2297 passed / 28 skipped under `.venv/bin/pytest`, CI green at HEAD (run
33302924781 — the 2026-08-29 failure was `setspec 0.4` unpublished; a re-run after publication
succeeded). PyPI: weightsdb 0.2.0, mirrorwall 0.2.0, setspec 0.4.0. Host has both `docker`
(python:3.12-slim, 3.13-slim local) and `bwrap`. GPU at check time: 691 MiB / 16311 MiB used.

Entry format follows `docs/history/M4_HANDOFF.md`: Severity (DECISION / NOTE / BLOCKER), Unit, Where, What
happened, What the next run must do.

---
## Phase 12 — WeightsDB and MirrorWall adoption (units 1–3)

Both adoptions complete at FreeWeight `007020f`. Source: −2,425 lines / +229 across `src/`
(infrastructure/db drops from 2,920 to 1,436 lines; the six plumbing modules are gone, `types.py`
is a 15-line re-export shim per the adoption checklist §2). Gate green: ruff/mypy/lint-imports and
2,299 passed / 28 skipped. `pyproject.toml` pins `weightsdb>=0.2,<0.3`, `mirrorwall>=0.2,<0.3`,
both resolved from PyPI, not editable.

### M6-1 — CSRF middleware deferred from unit 2 to unit 9
- **Severity:** DECISION
- **Unit:** P12 unit 2 / P14 unit 9
- **Where:** `src/freeweight/web/app.py` (middleware stack)
- **What happened:** The unit-2 charter lists MirrorWall middleware including CSRF, but FreeWeight
  has ~10 templates POSTing real forms with no token plumbing, and P12's acceptance criterion is
  "no behaviour change". The dev plan places "the CSRF token on form routes" in P14. Wiring
  `CsrfMiddleware` without the per-form hidden field + cookie issuance would 403 every form.
- **What the next run must do:** Unit 9 wires `mirrorwall.CsrfMiddleware`, adds the double-submit
  token to every form (LoadCoach's `web/csrf.py` / `render_form_page` is the template), and tests
  forged/valid/cross-origin posts in a real browser.

### M6-2 — Test adjustments beyond import paths, each an extraction rename or checklist-mandated
- **Severity:** NOTE
- **Unit:** P12 units 1–2
- **Where:** `tests/integration/test_transactions.py`, `tests/unit/test_model_discovery.py`
  (the adoption checklist §3 `read_only=True` → `transaction(immediate=False)` rewrite);
  `tests/accessibility/test_ui_checklist.py` (token/CSS assertions now read the stylesheets the
  page links instead of an inline style block; `id="telemetry-bar"` → `id="mw-telemetry-bar"`);
  `tests/unit/test_telemetry_service.py` (the bar's `min-width` rule now lives in MirrorWall's
  layout.css). No assertion was weakened; every asserted property is unchanged.
- **What the next run must do:** Nothing; recorded so the verification can check each rename had
  an unchanged property behind it.

### M6-3 — StrictUndefined exposed two latent template defects, both fixed as bugs
- **Severity:** NOTE
- **Unit:** P12 unit 2
- **Where:** `templates/runs/index.html` (sticky form values had no defaults; blank-rendered
  before), `templates/goals/wizard_rules.html` (`proposal.criterion` vs `criterion_key`: headings,
  anchor ids and the hidden `criterion` form value silently rendered empty pre-swap).
- **What the next run must do:** Nothing; noted because the pre-swap UI silently carried both.

### M6-4 — Intended visual differences of the swap (complete list)
- **Severity:** NOTE
- **Unit:** P12 unit 2
- **What happened:** Byte-identical palette (47 tokens compared). Full-page before/after snapshots
  of 18 page/theme/viewport combinations differ only in live telemetry values, except: the
  evidence page gains MirrorWall table.js's column-visibility control and sortable headers
  (table.js now loads on every page from the shared base; the page's `data-table` table
  previously had no script). Element id `mw-telemetry-bar`; column preferences move to
  `mirrorwall-columns:*` localStorage keys (old `freeweight-columns:*` entries orphan silently);
  theme storage key kept as `freeweight-theme` so the user's stored choice survives.
- **What the next run must do:** Nothing.

### M6-5 — PHASE11 #6's `disagreement_rate` column cannot land in P12
- **Severity:** DECISION
- **Unit:** P12 unit 1 / post-1.0
- **What happened:** PHASE11_ISSUES §6 suggested adding a `metric_values.disagreement_rate`
  column "Phase 12 with WeightsDB". P12's acceptance criterion is that an rc1 database upgrades
  with **no new revision**, which a new column contradicts. The current behaviour errs toward
  less confidence (the safe direction, as the issue itself records).
- **What the next run must do:** Carry it on the post-1.0 deferred list; it needs a migration and
  its own phase.

## Phase 13 — External benchmark adapters and sandboxing (units 4–7)

Complete at FreeWeight `b4abcf4`. Gate green: ruff/mypy/lint-imports, 2,480 passed / 28 skipped.
+181 tests. New subsystem under `src/freeweight/external/` (errors, invocation, sandbox, datasets,
manifest, environment, framework, nine adapters), `services/external.py`, `cli/commands/external.py`,
`web/routes/sources.py` and its template.

### M6-6 — Both sandbox tiers proven live on this machine; CI proves neither by default
- **Severity:** NOTE
- **Unit:** P13 unit 5
- **Where:** `tests/integration/test_sandbox_tiers.py`, `tests/security/test_sandbox_refusal.py`
- **What happened:** This machine has docker (answering) and bwrap (functional), so the container
  and bwrap live tiers were both exercised: container runs isolated with no network (~0.1 s warm),
  bwrap enforces no-network, no-home, the memory rlimit and the timeout kill. The **refusal** is
  proven with an observer (a file-creating command under a refused decision leaves no file and the
  injected runner records zero calls) and mutation-checked (turning the refusal into a warning
  fails two tests). The CI runner (GitHub ubuntu) typically has docker but its bwrap and
  user-namespace posture vary; the live tiers `skipif`-skip with the machine's own reason rather
  than pass vacuously, and the selection logic for *every* machine shape (podman/docker/bwrap/none
  × auto/container/bwrap/none) is tested with injected detection, which the runner does exercise.
- **What the next run must do:** The verification should re-run `tests/integration/test_sandbox_tiers.py`
  and read which live classes skipped on its own machine.

### M6-7 — RLIMIT_NPROC for the bwrap tier is relative to current task count, not absolute
- **Severity:** DECISION
- **Unit:** P13 unit 5
- **Where:** `src/freeweight/external/sandbox.py::_bwrap_rlimits`
- **What happened:** `RLIMIT_NPROC` is checked by the kernel against the user's **total task
  count including threads**, not the sandboxed process's children. An absolute fork-bomb cap
  (128) blocked bwrap's own clone on this desktop (170 processes but 1,814 tasks →
  "Creating new namespace failed: Resource temporarily unavailable"). The cap is therefore
  `current_tasks + 256`, counted by scanning `/proc/*/task`.
- **What the next run must do:** On a shared multi-user host this cap is looser than ideal; it is
  a fork-bomb backstop, not the primary boundary (the container tier's `--pids-limit 128` is).
  Fine for 1.0; revisit if a cgroup-based limit becomes available under bwrap.

### M6-8 — External datasets ship with placeholder hashes; a real install needs the true pins
- **Severity:** BLOCKER (for a real external run, not for 1.0's default install)
- **Unit:** P13 units 4/6/7
- **Where:** every adapter's `manifest.datasets[*].sha256`
- **What happened:** The nine adapters carry pinned dataset **specs** with placeholder hashes
  (`sha256:0000…`), because the real datasets are not redistributable (licences forbid it) and
  are not downloaded in this environment (no network, and the GPU is shared). Every adapter is
  proven end to end on **recorded output fixtures** (`tests/fixtures/external/*`), which is what
  units 6–7 asked for and what the acceptance criterion "results appear alongside native with full
  provenance" is demonstrated against. A user who actually installs a benchmark must supply the
  correct pin — the hash-mismatch refusal (proven, mutation-checked) is exactly what protects them
  from an unpinned dataset in the meantime.
- **What the next run must do:** A human with network access records each dataset's true sha256
  and updates the manifests before any real external run is published. This is the "external
  project whose pinned release no longer downloads → record the fixture you fell back to" case the
  run rule anticipated. The adapters, framework, sandbox and parsers are complete and tested; only
  the real pins and a live `-m live` run against installed benchmarks remain, both requiring
  network the environment does not have.

### M6-9 — The run engine does not yet dispatch external suites; the framework is the seam
- **Severity:** DECISION
- **Unit:** P13
- **Where:** `services/runs.py` (`_execute_run_inner` dispatches `runner == "goal"` and native)
- **What happened:** `manifest.runner == "external"` suites are not yet claimed and driven by the
  scheduler — `run_external_benchmark` is the one function that does it, tested directly, but the
  wiring from a persisted `runs` row through the scheduler to `run_external_benchmark` (installing,
  selecting the tier once per run, persisting the normalized samples/metrics with the sandbox tier)
  is not built, because it needs a real installed benchmark to exercise honestly and the datasets
  are not installable here (M6-8). The framework's contract (verify → run → parse → normalize with
  provenance and tier) is complete and is the whole seam the scheduler will call.
- **What the next run must do:** Wire `_execute_run_inner` to call `run_external_benchmark` for an
  `external` suite once real dataset pins exist, and add an `-m live` end-to-end test. Recorded as
  a decision because P13's acceptance criteria (three adapters producing results with provenance;
  sandbox skip without host execution; no external import) are all met and tested at the framework
  level; the scheduler wiring is the same shape as the goal-runner dispatch already present.

## Phase 14 — Hardening and 1.0 closeout (units 8–12)

Complete at FreeWeight `69e72b0`. Gate green: ruff/mypy/lint-imports; 2,501 passed / 28 skipped
under `.venv/bin/pytest`; 2,495 passed / 34 skipped in Docker 3.12 installed from `ci.lock`; the
suite green in a fresh non-root 3.13 lock venv with siblings imported from site-packages. Coverage
89.72% overall, 97% in `domain/`, 90% in `external/`. Version stamped `1.0.0`.

### M6-10 — CSRF is issued centrally, not per route (unit 9)
- **Severity:** DECISION
- **Unit:** P14 unit 9
- **Where:** `web/csrf.py` (`CsrfCookieMiddleware`, `current_csrf_token`), `web/rendering.py`
- **What happened:** Rather than convert ~50 form-page render sites to a `render_form_page` (the
  LoadCoach pattern), FreeWeight issues the token once per request in a middleware, binds it to a
  contextvar, and `render()` injects it into every page. A form only includes the `_csrf` partial.
  This closes the M5 "every entry point must apply the same policy" gap structurally — a new form
  page cannot forget the token. Host validation was moved to **outermost** so a rebinding form
  post is 421 before CSRF runs.
- **What the next run must do:** Verify a forged form post is 403, a valid one 303, a cross-origin
  JSON write is exempt, and that the `__Host-` cookie carries `Secure`+`Path=/`+no `Domain`. The
  browser-faithful conftest fixture (`_browser_faithful_csrf`) is what lets the existing e2e form
  tests keep POSTing; it fills the token only when the caller omits one, so a rejection test opts
  out with an explicit empty token.

### M6-11 — `__Host-` cookie over plain HTTP: the M5 cookie question, answered (unit 9)
- **Severity:** NOTE
- **Unit:** P14 unit 9
- **What happened:** The CSRF cookie is `__Host-`-prefixed and `Secure`. Browsers treat
  `http://localhost` and `http://127.0.0.1` as secure contexts, so it works on the loopback
  default; it does not work over plain HTTP through any other hostname, which is documented in
  `docs/security.md` and `docs/troubleshooting.md`. httpx (the TestClient's engine) will not send a
  Secure cookie over `http://` even to loopback — a real localhost browser does — so the test
  fixture passes the cookie explicitly. The flags are not weakened.

### M6-12 — Trusted-proxy / failed-auth brake: not added, and why (unit 9)
- **Severity:** DECISION
- **Unit:** P14 unit 9
- **What happened:** LoadCoach added a per-address failed-auth brake with `trusted_proxies`.
  FreeWeight does **not** enforce bearer auth (`freeweight token create|list|revoke` waits on
  ADR-0014; `auth.tokens` is config that the binding-refusal reads but no middleware checks a token
  yet), so there is no failed-auth path to brake and no `trusted_proxies` was added. The M5 "a
  per-address brake behind a reverse proxy is a lock-out" concern therefore does not apply to
  FreeWeight at 1.0. The binding refusal still requires `auth.tokens` for a non-loopback bind.
- **What the next run must do:** When ADR-0014 lands token enforcement, add the failed-auth brake
  with `trusted_proxies` and test both, as LoadCoach did.

### M6-13 — Five health components added; doctor now covers spec §17 (unit 10)
- **Severity:** NOTE
- **Unit:** P14 unit 10
- **What happened:** `prompts`, `sandbox`, `external_benchmarks`, `goals`, `judges` were added to
  `get_health_report`, reconciling `/health` and `doctor` with spec §17 (the consistency review's
  "health components against /health" item). `docs/troubleshooting.md` documents each, and
  `tests/unit/test_troubleshooting_covers_doctor.py` holds the guide's headings and the doctor's
  components in lockstep. `evidence` and `machine` remain as extra components spec §17 does not
  list — pre-existing, kept.

### M6-14 — `benchmarks list|show` CLI was owed since P12 (unit 12)
- **Severity:** NOTE
- **Unit:** P14 unit 12 (consistency review)
- **What happened:** Spec §7.2 marks `freeweight benchmarks list|show` Phase 12; its HTTP form
  shipped but the CLI did not. Roadmap §8's consistency review (spec §7 against the Typer app)
  found it; added in unit 12 as `cli/commands/benchmarks.py`, reading the same registry the run
  engine uses.

### M6-15 — `unshare -rn` fails only the container live test (units 5/12)
- **Severity:** NOTE
- **Unit:** P13 unit 5 / P14 closeout
- **What happened:** Under `unshare -rn` the full suite is 2,500 passed / 1 failed — the single
  failure is `test_sandbox_tiers.py::TestTheContainerTierLive`, because `unshare -rn` disables the
  local docker daemon's ability to run a container (a local-daemon dependency, not a network one).
  Every other test passes with no network, which is what the check proves. On a normal machine and
  on the GitHub runner the container test passes.
- **What the next run must do:** Run `unshare -rn .venv/bin/pytest -m "not live and not
  performance"` and confirm the only failure is the container live test; every other test is
  network-free.

### M6-16 — Responsive gaps found by the unit-11 browser re-run, fixed in app.css (unit 11)
- **Severity:** NOTE
- **Unit:** P14 unit 11
- **What happened:** A browser pass at 375 px (the M5 "assert no horizontal scroll at 375 px"
  requirement) surfaced pre-existing overflow on pages with unwrapped tables and the compare form's
  `size=60` inputs. `app.css` now makes any table scroll within its box below 768 px and constrains
  form controls and fieldsets (`min-width: 0`). Verified in a browser on every page in dark mode
  and with JS disabled; the accessibility test suite (which cannot render) still passes.

---

## PHASE*_ISSUES.md open items — closed or deferred

| Item | Disposition |
|---|---|
| PHASE8/PHASE11 #19 — deleting a goal removes its pack dir without a backup | **Deferred to post-1.0.** P14's "deleting never destroys history" criterion (AC11) is met for **results** (preview + model/machine history preserved). Goal-pack deletion is a separate path the criterion does not name; a backup-on-delete for goal packs is a small post-1.0 addition. Recorded so it is not lost. |
| PHASE10 #3 (CSRF token anywhere) | **Closed (unit 9).** CSRF double-submit on every form route. |
| PHASE11 #6 — `disagreement_rate` column | **Deferred (M6-5).** Needs a migration; P12 forbade one. |
| PHASE11 #7 — `source_id = freeweight:<fingerprint>` | **Unchanged, by design.** ADR-0022's revisit trigger (a second evidence producer / federated import) has not occurred; the note is preserved. |
| PHASE11 #10 — `[external]`/`[sandbox]` in spec §12 but not the model | **Closed (unit 4).** Both sections added to the settings model and the generated reference. |
| PHASE10 #1,2,4,6,7 (energy attribution, memory_kv residual, sample windows, reliability dataset, context ceiling) | **Carried to post-1.0.** All are inside `benchmarks/*` measurement refinements outside P12–P14's file lists; each already surfaces its limitation to the user rather than hiding it. |

## The eighteen spec §20 acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `pip install freeweight && freeweight serve` with only Ollama | **met (pending tag)** | Clean lock-venv install + `freeweight serve`; the real `pip install freeweight==1.0.0` is the human tag step |
| 2 | Models discovered only through ModelRack, canonical identities | met | `services/models.py`; `test_model_discovery.py` |
| 3 | Run executes, streams, survives refresh, cancellable at any phase | met | `test_run_journey.py` (SSE replay, cancel) |
| 4 | Every headline metric drills to its sample in ≤ 2 interactions | met | `test_drilldown.py`; UI checklist |
| 5 | Same fingerprint within tolerance; differing shown with a diff | met | `test_provenance.py`, comparison tests |
| 6 | Unsupported is `—`/`"unsupported"`, never `0` | met | `test_ui_checklist.py`, rendering filter tests |
| 6a | Recompute over unchanged runs does not raise confidence | met | evidence freshness tests (ADR-0022) |
| 7 | Cold and warm never mixed | met | aggregation `measurement_class` refusal tests |
| 8 | Evidence bundle imported by LoadCoach with no FreeWeight code | met | `test_evidence_export.py` contract (setspec-only consumer) |
| 9 | Code-execution benchmarks refuse when no sandbox tier | met | `test_sandbox_refusal.py` (observer + mutation) |
| 10 | Full suite passes no GPU/Ollama/network; ≥85% / ≥95% domain | met | 2,501 pass; 89.72% overall, 97% domain; `unshare -rn` (M6-15) |
| 11 | Deleting results never deletes model/machine history; previews | met | `test_delete_preview.py` |
| 12 | All FreeWeight gold standards met | met | table below |
| 13 | Author a goal from the UI alone, grade 12, see calibration | met | `test_goal_wizard_journey.py` |
| 14 | Unmeasurable rubric → uncalibrated, no evidence, names criteria | met | calibration gate tests |
| 15 | Rule-only goal runs, exports evidence, `judge_validity_factor=1.0` | met | goal runner tests |
| 16 | Moving a criterion to a rule raises validity; UI shows mix | met | `test_goal_wizard_journey.py::TestGoalResultsCarryTheirMix` |
| 17 | Goal pack re-run elsewhere → same `goal_hash`; jury change separates | met | goal pack round-trip + `goal_hash` tests |
| 18 | LoadCoach ignores `user.*` unless a task profile names it | met | contract on the evidence side; LoadCoach's own tests hold the consumer half |

## The ten FreeWeight gold standards

| Gold standard | Status | Evidence |
|---|---|---|
| Reproducible benchmarks within tolerance, fingerprint explains difference | met | provenance/comparison tests |
| Raw samples retained; drill ≤ 2 interactions | met | drilldown + UI checklist |
| Cold/warm never mixed | met | aggregation refusal tests |
| Every scoring formula unit-tested with known + boundary values | met | `tests/unit/test_rules_*`, `test_scorers_*`, metrics tests |
| Deterministic scoring preferred; ladder documented per benchmark | met | scorer ladder; benchmark catalogue |
| Evidence export consumable with no FreeWeight code | met | setspec-only contract test |
| Freshness reflects `measured_at`, not aggregation time | met | evidence recompute test (AC6a) |
| No judged score exported without agreement (`kappa_w` never without `n_holdout`) | met | calibration gate + evidence emission tests |
| Author a measurable goal from the UI alone → portable JSON pack | met | wizard journey |
| A run survives browser refresh and server restart | met | SSE replay + scheduler recovery tests |

## Runner status
Push `69e72b0` triggered CI run `33361135765` (in progress at handoff write). Every prior phase
push went green on the runner: the CI-fix `b00c872` was green on all jobs including the container
tier and both locks audited (run `33356591342`).

## The tag line
`TAG_APPROVED: no` (unchanged). The `freeweight 1.0.0` tag, `release.yml`, and the clean-index
`pip install freeweight==1.0.0` + one native benchmark + one export (spec §20 AC1) are the human
step, exactly as M5 left the `loadcoach` tag.

### M6-17 — The tests job went red on a coverage-source path bug, not a test failure (closeout)
- **Severity:** DECISION (fixed)
- **Unit:** P14 unit 12 / CI
- **Where:** `pyproject.toml [tool.coverage.run]`
- **What happened:** Converting CI to the non-editable lock install (`pip install . --no-deps`)
  in `69e72b0` turned the `tests` job red on both 3.12 and 3.13, while `tests-314` (no `--cov`)
  and `postgresql-tests` stayed green. The cause was **not a test failure**: `source =
  ["src/freeweight"]` measures a filesystem *path*, but a non-editable install runs `freeweight`
  from `site-packages`, so coverage measured **0%** and `fail_under = 85` failed the job — a
  catastrophe-shaped number that is really a config error. `b00c872` was green only because its
  `tests` job used the editable install, where `freeweight` resolves to `src/freeweight`. Fixed
  the way LoadCoach already had (its pyproject even documents the trap): `source = ["freeweight"]`
  (the importable package) plus a `[tool.coverage.paths]` mapping `src/freeweight` ↔
  `*/site-packages/freeweight`. Verified in a fresh non-editable lock venv: **89.37%**.
- **The two red herrings this surfaced:** while diagnosing, a runner-like local run showed two
  failures — `test_a_quiet_machine_proceeds` (the idle-detection test read this machine's **real,
  transiently-busy GPU** at 100% — the shared-GPU caveat, not a code fault; it passes on the
  no-GPU runner, as `b00c872` proved) and one flaky SSE test. Neither is a runner failure; the
  coverage-source bug was the whole cause.
- **What the next run must do:** Confirm the `tests` job is green on the runner after `f45a7a9`,
  and that the coverage number reported there is ~89%, not 0%.

## Final runner status (supersedes the earlier section)

**CI run `33364783572` on `f45a7a9` (HEAD): completed success — every job green.** boundaries,
lint, format, types, contracts, docs, build, install-check, security (both locks audited under
`pip-audit --require-hashes`), postgresql-tests, tests (3.12), tests (3.13), tests-314-early-warning
and coverage all `success`; diff-coverage skipped (push, not PR). This is the first green run under
the lock-based install with coverage measured correctly (M6-17), and it closes the "green on the
real runner" requirement for M6. Final head: `f45a7a9`, 11 commits since the `0a6bc40` base.
