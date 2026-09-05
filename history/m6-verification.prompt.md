Verify FreeWeight 1.0.0 against M6's exit condition — *"FreeWeight on the shared packages,
external adapters, hardened; published to PyPI"* — and decide whether it is ready. Run unattended:
nobody is available to answer a question. You may read anything, run anything, measure anything,
and open a browser against a server you start. **You may not edit code, commit, push, tag or
publish.** If a claim below turns out to be false, that is a finding, not something to fix.

**Model:** Fable 5, max effort. Ultrathink on every claim you attack — most of all the sandbox
refusal, whose failure mode is model-generated code running on this machine, and the adapter
output parsers, whose input is hostile by construction.

Your job is adversarial. The implementer's report says everything passes; a passing suite is weak
evidence, "the tests pass" answers nothing, and reporting **not ready** is a success if it is true.
Every DECISION entry in the handoff is a place a document was ambiguous and the implementer chose;
an ambiguity resolved in the implementer's favour is where a contract bug lives.

## Ground state

```
cd ~/ai/suite/FreeWeight && git log --oneline -1          # f45a7a9 fix(ci): measure coverage of the freeweight package, not the src path
git log --oneline 0a6bc40..HEAD | wc -l                   # 10 commits since the P12-early base
cat src/freeweight/__about__.py                           # __version__ = "1.0.0"
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy src tests && .venv/bin/lint-imports
.venv/bin/pytest -q -m "not live and not performance"                 # 2501 passed, 28 skipped (~3 min)
.venv/bin/pytest -q -m "not live and not performance" --cov --cov-fail-under=85   # 89.72 %
.venv/bin/pytest -q --cov=src/freeweight/domain                       # 97 % in domain/
.venv/bin/pytest -q -m contract                                       # 54 passed
.venv/bin/pytest -q -m "not live and not performance" tests/integration  # 381 passed, 28 skipped
.venv/bin/pytest -q -m performance -s                                 # 17 passed; figures printed
which bwrap docker                                                    # this machine has both
```

The handoff is `~/ai/suite/M6_HANDOFF.md`, section
`# M6 Handoff — P12–P14 run (FreeWeight P12–P14, M6 closeout)`, entries `M6-1` … `M6-17`, plus the
eighteen §20 criteria and ten gold-standard tables. The docs repository is `~/ai/suite/docs`
(pushed at head `8c260f3`); `FreeWeight/docs/apps/freeweight/*.md` are byte-identical mirrors
(`scripts/sync_docs.py --check` proves it). The generated `docs/configuration.md` and
`docs/openapi.json` are CI-diffed against the code.

**Publish state:** `weightsdb 0.2.0`, `mirrorwall 0.2.0`, `setspec 0.4.0` all on PyPI;
`requirements/ci.lock` cut on 3.13 and both locks audited; `freeweight 1.0.0` stamped, **not
tagged**. `TAG_APPROVED: no`.

## What M6 changed, and where the risk is

P12 was *supposed* to change nothing observable (adoption of WeightsDB, MirrorWall,
`setspec.prompts`); P13 added a sandbox that runs model-generated code and nine parsers of hostile
output; P14 added CSRF, the §15 budgets, the §14 checklist, the docs and the lockfile. The
named failure modes are **silent host execution** (P13), **unpinned datasets** (P13), a
**migration history broken by a changed version-table name** (P12), and **template regressions**
(P12). Attack those first.

## The sandbox refusal — the unit that must not be believed on faith

`tests/security/test_sandbox_refusal.py` claims the bottom of the ladder refuses and nothing runs
on the host. This is the whole safety case; falsify it four ways.

1. **The observer.** A refused decision must execute nothing. Write your own provider-free harness:
   a `SandboxCommand` whose argv would `touch` a witness file, submit it under
   `select_tier(SandboxSettings(tier="none"))`, confirm `SandboxUnavailable` is raised, the witness
   file does **not** exist, and the injected runner recorded zero calls. Then do it again with a
   machine that has no runtime at all (`which=lambda _n: None`).
2. **The mutation.** Turn `run_sandboxed`'s refusal into a warning-and-run (edit a copy you do not
   commit) and confirm `test_refusal_executes_nothing_at_all` and `test_refusal_holds_under_
   concurrency` fail. If they still pass, the refusal is not actually load-bearing.
3. **Concurrency.** Two real threads race the refused door (`test_refusal_holds_under_concurrency`).
   Add a third and a fourth; every one must be refused and the witness file must never appear.
4. **The one door.** `TestOneDoor` asserts nothing under `src/freeweight` starts a subprocess except
   `external/invocation.py` and `cli/commands/goals.py`. Grep yourself: `import subprocess`,
   `os.system`, `os.popen`, `os.exec*`, `Popen`, `run(`. Find any path — a route, the scheduler, a
   benchmark — that could reach a subprocess without going through `run_invocation`. Then ask
   whether the external run engine is even *wired*: read M6-9, and decide whether "results appear
   alongside native ones with full provenance" (P13 AC1) is true at the persistence/UI layer or
   only at the framework/fixture layer. This is the DECISION most likely to hide a gap.

Then prove the tiers on **this** machine (it has docker and bwrap): run
`tests/integration/test_sandbox_tiers.py` and read which live classes ran versus skipped. Under
bwrap, confirm by hand that the sandbox has no network, no `$HOME`, and that the memory rlimit and
the wall-clock timeout both bite. Under the container tier, confirm `--network=none` and a
non-root/uid mapping. Mark any tier you could not exercise as *unproven*, never as passed.

## The dataset-hash refusal and adapter output parsing — hostile input

5. **Hash mismatch refuses and names both hashes.** `test_dataset_verification.py`. Falsify:
   `install_dataset` a payload that does not match its pin and confirm nothing is left in the
   datasets directory and the error carries `expected_sha256` **and** `actual_sha256`. Then read
   M6-8: the shipped adapters carry **placeholder** dataset hashes (`sha256:0000…`) because the
   real datasets are not redistributable and were never downloaded here. Decide what that means for
   P13 AC1 and for a user who runs `freeweight external install` — is the hash-mismatch refusal the
   only thing standing between them and an unpinned dataset, and is that honestly documented?
6. **The subprocess is killed on a hang.** `external/invocation.py`. Falsify on a real process:
   `run_invocation` a `/bin/sleep 60` with a 1 s timeout; it must return `timed_out=True` within a
   couple of seconds and leave no `sleep` process behind (`pgrep sleep`). Then a process that floods
   stdout: the output cap must fire and the process die.
7. **Every adapter parses hostile output without raising or fabricating a zero.**
   `tests/unit/test_external_output_parsing.py`. Falsify: feed each of the nine adapters truncated
   JSON, a UTF-16 BOM (`\xff\xfe`), a 100 MB payload, a score of `NaN`, a score of `1.5`, and a
   boolean where a float belongs. No parser may raise; every unscoreable case must be `score=None`
   with an `error_code` (ADR-0016), never `0.0`. Then check the archive hardening in
   `datasets.py::extract_archive` against a `..` entry, an absolute path, a symlink, and a
   decompression bomb.

## The migration history — P12's named failure mode

8. **An rc1 database opens at head with no new revision.**
   `test_migrations.py::test_rc1_database_opens_at_head_with_no_new_revision` runs against a
   committed fixture (`tests/fixtures/databases/freeweight-1.0.0rc1.sqlite3`) built by a real rc1
   install. Falsify: confirm the fixture is **committed** (it was gitignored by `*.sqlite3` and the
   whole first CI red was that — `git ls-files` it, and `git cat-file` it to prove it is
   byte-identical and binary). Copy it, `ensure_ready(auto_migrate=True)`, and confirm the outcome
   is `None` (no migration) and the rc1 rows are still readable. Then the mutation: temporarily give
   `MigrationRunner` a `version_table="weightsdb_version"` and confirm the test fails — the version
   table name is what P12's failure mode is about. Then `test_upgrade_from_rc1.py` boots the whole
   app on the rc1 database and serves its rows; confirm over a real client.

## The prompt-hash identity across the `setspec.prompts` adoption

9. **The shipped pack hashes identically before and after adoption.**
   `test_prompt_pack.py::test_the_pack_hash_is_the_golden_one_recorded_across_the_setspec_adoption`
   pins `sha256:b1b0ffd0a5941fee5e0013d2a826732ea02a285b229bdc006ebd6dd25ff4ceb4`. Falsify:
   compute `load_pack().pack_hash()` yourself and confirm it equals the golden. Then confirm the
   loader/renderer/hasher actually come from `setspec.prompts` (not a local copy) — the P12 claim
   is that this is a *move*, not a fork.

## The whole §14 security checklist — attack the new CSRF hardest

10. **Every Security Standards §14 item.** `tests/security/test_security_checklist.py` and the
    pre-existing coverage the handoff M6 header lists. Attack the two P14 introduced:
    * **CSRF on a real form, in a real browser.** Start `freeweight serve`, open `/runs`, copy the
      start-run form, submit it from a page on another origin (expect no effect), then submit the
      real button (expect 303). Then the `__Host-` cookie: does your browser accept it on
      `http://127.0.0.1`? On `http://localhost`? Read M6-11 and decide whether the plain-HTTP
      cookie limitation is honestly documented (`docs/security.md`, `docs/troubleshooting.md`) and
      whether the flags were weakened to make a test pass (they must not be).
    * **Host before CSRF, on both binds.** `test_a_bad_host_on_a_form_post_is_421_not_403`. Falsify
      on a **real socket**, not the test client: start the server, send a form POST with a wrong
      `Host`, and confirm 421 before the CSRF check runs. Then read the middleware order in
      `web/app.py` and confirm Host validation is genuinely outermost.
    * **The trusted-proxy / failed-auth question.** Read M6-12: FreeWeight does not enforce bearer
      auth (`auth.tokens` is config the binding-refusal reads, but no middleware checks a token).
      Confirm there is therefore no per-address auth brake to lock anyone out, and that the
      binding refusal (`_validate_security`) still requires `auth.tokens` for a non-loopback bind.
      Decide whether shipping 1.0 with token *enforcement* deferred to ADR-0014 is consistent with
      spec §14's "non-loopback requires tokens".
11. **Hostile model output is inert.** `TestModelOutputRendersInert`. Falsify on every page that
    renders model text or a model *name*: feed `{{ 7*7 }}`, `<script>`, `../../etc/passwd` and SQL
    metacharacters as a model name and an error string, and confirm none survives unescaped and no
    Jinja expression evaluates. Then the goal-template path: user-authored goal content renders
    through a sandboxed environment with `StrictUndefined` and no filesystem/network — confirm a
    template that reaches for a file or a dunder is refused at pack load
    (`test_goal_pack_import.py`).

## The UI gold standards, in a browser

12. **Every headline metric drills to its sample in ≤ 2 interactions, and unsupported is never
    `0`.** These are the two gold standards a template swap can break silently (P12). Seed a run
    against `FakeProvider` (the demos and the e2e fixtures show how), open the dashboard and a
    result, and count the interactions to a raw sample. Confirm an unsupported measurement shows
    `—`, never `0`, on every surface.
13. **No horizontal scroll at 375 px; works with JS off; dark mode.** Read M6-16: the browser
    re-run found and fixed responsive overflow. Falsify yourself — open every navigation entry at
    375 px in dark mode and assert `document.documentElement.scrollWidth <= clientWidth`, then
    with JavaScript disabled confirm every read-only page still renders its content. Assert links
    by `href=` (MirrorWall escapes markup passed to its macros — the M5 `| safe` lesson).
14. **The MirrorWall swap changed nothing observable (P12 AC1).** The implementer took before/after
    full-page snapshots and reports they differ only in live telemetry, except the evidence page
    (which gains table.js's column controls — an intended enhancement). Spot-check two pages
    yourself against the pre-swap look, and confirm the palette is the pre-adoption one (M6-4 claims
    47 tokens byte-identical).

## Measure the budgets on a real socket; do not read the tests

`pytest -m performance -s` prints each figure. Then measure **run start** yourself the way spec §20
and M5 demand — on a real socket, with the process started by `freeweight serve`, not in-process:
discover a model over the socket, `POST /api/v1/runs`, and time the response against the 500 ms §15
budget. Read `test_budgets.py` and confirm the request-shaped budget genuinely uses a subprocess
server (M6's unit 8 claim), not a TestClient.

## Verify CI the way the package releases were verified

Refuse "green locally". The M5 lesson was that the whole first CI red here was a **gitignored
fixture** absent on the runner's fresh checkout (the rc1 database) — so trust nothing that only
exists in the working tree. Read run `33364783572` on `f45a7a9` — the implementer reports it green on every job — and the
two red runs before it (`33361135765`, `33363020266`), whose cause M6-17 claims was a
coverage-source path measuring 0% under the non-editable install, not a test failure. Verify that
story against the runs yourself, then say plainly: is every job green at HEAD
(the 3.14 job is `continue-on-error` — say if it failed); did the lock-based jobs actually run;
did the container-tier live test run on the runner; were **both** locks audited under
`pip-audit --require-hashes`. Then reproduce a **fresh checkout**: `git archive HEAD | tar -x` into
a scratch dir, install into a fresh **non-root** 3.13 venv with `pip install --require-hashes -r
requirements/ci.lock` then `pip install . --no-deps`, and run the whole gate — the fixture must be
present and the siblings must import from `site-packages`, not an editable workspace. Then the
Docker 3.12 gate:
`docker run --rm -v <fresh>:/src:ro python:3.12-slim …` installing from the lock. Then
`unshare -rn .venv/bin/pytest -m "not live and not performance"` and confirm the only failure is
the container live test (M6-15) — every other test must be network-free.

## Read the handoff critically

Every `M6-*` DECISION resolves an ambiguity or records a limitation. For each, read the document it
cites and decide whether the resolution is the one the document supports and whether a caller on
the other side (LoadCoach, an operator, a security reviewer) would be surprised. The ones to press:
**M6-9** (is the external run engine wired to the scheduler and the database, or is P13 AC1 met only
at the framework level — this is the biggest one), **M6-8** (placeholder dataset hashes; can any
real external benchmark actually run), **M6-1/M6-10** (CSRF issued centrally via a contextvar — is
there any page with a form that does not go through `render`), **M6-12** (token enforcement
deferred), **M6-5** (a schema change the adoption could not make), and the deferred PHASE*_ISSUES
items — confirm none of P14's deferred list was implemented and none was quietly dropped.

## The verdict

Fixed shape:

**Verdict:** ready / ready with conditions / not ready.

**Findings:** numbered, each with a severity (blocker / major / minor / note), the claim it
falsifies, the exact reproduction, and the concrete thing that must change before 1.0 ships.

**The eighteen spec §20 acceptance criteria** and **the ten FreeWeight gold standards**: met /
partially / not met, one line each, in your own judgment, with the evidence you saw.

**The exit condition**: on the shared packages, external adapters, hardened — each with the
evidence — and the fourth clause's (published) honest state.

**The sandbox tiers proven on this machine**: container / bwrap / refuse, each proven or unproven,
with what you ran.

**Token discipline:** no subagents; the gate as the single chained command above; `--tb=line`
while iterating; do not re-read a document section you have already read.
