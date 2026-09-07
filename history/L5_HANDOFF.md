# L5 handoff — the documents the checklist names and the repositories lack

**Row:** L5 (Sonnet 5 · high), `docs/roadmap/outstanding-work.md` §1: "The documents the checklist
names and the repositories lack" (M9 Group 5), plus L2's 2026-09-07 addendum (`pydantic-settings`
removal).
**Components:** `docs` (`main`), `FreeWeight`, `LoadCoach`, `IdeaPress`, `PromptCadence` (all
`main`). Row L3 ran concurrently in the same four application repos on
`tests/integration/test_downgrade_and_schema_ahead.py`, backup/restore tests,
`tests/fixtures/databases/*` and one sentence in `docs/operations.md`/`docs/backup-restore.md`;
none of those were touched here. One collision happened anyway (§5) and was fixed within this row.

## 1. The ADR-0037 citation

The row text says "ADR-0037 argues no alternatives (a superseding record only if one is warranted
on other grounds)" for the `pydantic-settings` removal. **ADR-0037 is
"Production evidence never raises capability scores"** — LoadCoach routing, unrelated to
dependency budgets. The record that actually settles this is **ADR-0114**
("The runtime dependency budget is an enumerated set"), whose Decision §4 already states
`pydantic-settings` is "documented over-declaration... owed removal" — no alternatives section is
needed because the removal is not a decision this row makes, it is ADR-0114 executing. No
superseding ADR was written: nothing here argues against ADR-0114 or adds a ground it did not
already cover. Flagging the citation rather than silently working around it, per instructions.

## 2. Gate results

Interpreter: each repo's own `.venv/bin/python`, plus a `/usr/bin/python3.13` clean venv per app for
item 9's proof (below).

```text
FreeWeight (.venv, CPython 3.14.4)
  ruff format --check .        331 files already formatted
  ruff check .                 All checks passed!
  mypy src tests               Success: no issues found in 302 source files
  lint-imports                 Contracts: 4 kept, 0 broken
  pytest -m "not live and not performance" --cov --cov-report=term-missing
      2611 passed, 29 skipped, 30 deselected — coverage 89.11%
      (one flaky scheduler-timing test failed under full-suite+coverage load and passed
       standalone and in the earlier non-cov run; see §6)

LoadCoach (.venv, CPython 3.14.4)
  ruff format --check .        220 files already formatted
  ruff check .                 All checks passed!
  mypy src tests               Success: no issues found in 200 source files
  lint-imports                 Contracts: 4 kept, 0 broken
  pytest --cov ...             1048 passed, 5 skipped, 18 deselected — coverage 90.65%

IdeaPress (.venv, CPython 3.13.15)
  ruff format --check .        192 files already formatted
  ruff check .                 All checks passed!
  mypy src tests               Success: no issues found in 187 source files
  lint-imports                 Contracts: 4 kept, 0 broken
  pytest --cov ...             1156 passed, 6 skipped, 30 deselected — coverage 88.65%

PromptCadence (.venv, CPython 3.13.15)
  ruff format --check .        187 files already formatted
  ruff check .                 All checks passed!
  mypy src tests               Success: no issues found in 182 source files
  lint-imports                 Contracts: 5 kept, 0 broken
  pytest --cov ...             1287 passed, 3 skipped, 10 deselected — coverage 91.60%
```

`git status --short` was checked at the start (all clean) and end (all clean; row L3 had committed
its own concurrent work by the time this row finished) of every repo.

## 3. The commits

| Repo | Hash | Commit |
|---|---|---|
| docs | `f13340f` | `docs(promptcadence): add api, data-model and risks references` |
| docs | `02d0d13` | `docs(standards): name the System page as the suite's help/about page` |
| FreeWeight | `d5a9294` | `docs+test(freeweight): add README compatibility table and drift test` |
| FreeWeight | `006a9bf` | `ci(freeweight): attach SHA256SUMS to the GitHub release` |
| FreeWeight | `71f8d81` | `docs(freeweight): refresh upgrading.md to the shipped versions` |
| FreeWeight | `429732a` | `test(freeweight): add test_every_command_has_help.py` |
| FreeWeight | `887bbd7` | `chore(deps): remove pydantic-settings, an unused declared dependency` |
| LoadCoach | `23938ca` | `docs+test(loadcoach): add README compatibility table and drift test` |
| LoadCoach | `cc33cc8` | `ci(loadcoach): attach SHA256SUMS to the GitHub release` |
| LoadCoach | `4155b14` | `docs(loadcoach): refresh upgrading.md through 1.1.3` |
| LoadCoach | `31236b0` | `test(loadcoach): port test_troubleshooting_covers_doctor.py from FreeWeight` |
| LoadCoach | `67f46f2` | `test(loadcoach): add test_every_command_has_help.py` |
| LoadCoach | `bfea4b6` | `chore: untrack tests/fixtures/databases/loadcoach-1.0.0.sqlite3` (§5) |
| LoadCoach | `5147600` | `chore(deps): remove pydantic-settings, an unused declared dependency` |
| IdeaPress | `aab75fc` | `docs+test(ideapress): add README compatibility table and drift test` |
| IdeaPress | `18ae1d3` | `ci(ideapress): attach SHA256SUMS to the GitHub release` |
| IdeaPress | `2f034d9` | `docs(ideapress): refresh upgrading.md through 1.3.0` |
| IdeaPress | `59640ca` | `test(ideapress): port test_troubleshooting_covers_doctor.py from FreeWeight` |
| IdeaPress | `5de8b6b` | `test(ideapress): add tests/security/test_checklist.py` |
| IdeaPress | `e2fdf88` | `test(ideapress): add test_every_command_has_help.py; fill ~40 help gaps` |
| IdeaPress | `9d2988b` | `chore(deps): remove pydantic-settings, an unused declared dependency` |
| PromptCadence | `b50e48c` | `docs: add CONTRIBUTING.md` |
| PromptCadence | `9e38a4e` | `docs(promptcadence): mirror api, data-model and risks references` |
| PromptCadence | `e923e38` | `docs+test(promptcadence): add README compatibility table and drift test` |
| PromptCadence | `dcaae63` | `ci(promptcadence): attach SHA256SUMS to the GitHub release` |
| PromptCadence | `22c1fe5` | `docs(promptcadence): refresh upgrading.md through 1.3.0` |
| PromptCadence | `3bab212` | `test(promptcadence): port test_troubleshooting_covers_doctor.py from FreeWeight` |
| PromptCadence | `9bde7e4` | `test(promptcadence): add test_every_command_has_help.py` |
| PromptCadence | `ffe4459` | `chore(deps): remove pydantic-settings, an unused declared dependency` |

Nothing is pushed, nothing is tagged, nothing is published — standing instruction.

## 4. Item by item

1. **`docs/apps/promptcadence/api.md`, `data-model.md`, `risks.md`.** Derived from
   `PromptCadence/docs/openapi.json` (every path covered), the six `web/routes/*.py` modules,
   `domain/errors.py` and `infrastructure/db/models.py` — not from memory. Mirrored
   byte-identically into `PromptCadence/docs/apps/promptcadence/` (`cmp` verified).
   `data-model.md` landed at 212 lines against the "~150" target — PromptCadence owns 15 tables
   plus 4 mounted ones, materially more than a repo this size normally carries in this doc, and
   trimming further would have meant dropping real schema information rather than prose; flagged
   per the row's own "otherwise say so." `risks.md` landed at 112 lines, under target.
2. **`PromptCadence/CONTRIBUTING.md`**, copied from LoadCoach's and adjusted for this
   application's own spec/lifecycle docs and its bypass-removes-planning-never-governance rule.
3. **`## Compatibility` table + drift test**, one shape in all four READMEs and
   `tests/unit/test_readme_compatibility.py` (parses `pyproject.toml` with `tomllib`, compares
   against the table). All four pass.
4. **`sha256sum dist/* > SHA256SUMS`** before `action-gh-release` in all four `release.yml`s,
   `files:` gains a second line for it. YAML validated with `python -c "import yaml; ..."` in each
   repo's own venv.
5. **`docs/upgrading.md` refreshed** — FreeWeight gained per-version sections for the first time
   (it had none); LoadCoach through 1.1.2/1.1.3; IdeaPress through 1.3.0; PromptCadence through
   1.3.0, including refreshing its stale `1.0.1`-era Compatibility prose.
6. **`test_troubleshooting_covers_doctor.py` ported to three repos**, each adapted to that repo's
   actual doctor shape rather than copied verbatim — LoadCoach's `doctor` reports named *codes*
   (not FreeWeight's health components), so its port checks each code in `DOCUMENTED_FAILURE_MODES`
   against the guide, verbatim for an ordinary code and by component name for a `degraded:*` one;
   IdeaPress's `doctor` reports named `Diagnosis` findings, so its port added a new "What `doctor`
   checks" table to the guide and holds it against the source; PromptCadence's is already
   component-shaped like FreeWeight's, so its port reads a markdown table instead of `##` headings.
   Guide gaps the tests found and fixed: LoadCoach was missing `MODEL_NOT_FOUND` and the
   reliability/telemetry components entirely.
7. **`IdeaPress/tests/security/test_checklist.py`**, in LoadCoach's shape: a handful of claims held
   directly (default bind, no login route, the `no_network` autouse guard, `SECURITY.md`'s
   presence) and the rest mapped to the tests that already hold them, with a final test proving
   every mapped function is real and callable.
8. **`test_every_command_has_help.py`**, one shape in all four repos, walking
   `typer.main.get_command(app)` recursively. **Group detection had to be duck-typed** —
   `isinstance(node, click.Group)` is `False` for Typer's own command objects in this environment
   (`typer._click.core.Command`/`TyperGroup` do not subclass the separately-installed `click`
   package's classes here), so an `isinstance` check silently walks zero commands and the test
   passes by finding nothing. Found real, if narrow, differences between repos: FreeWeight,
   LoadCoach and PromptCadence had complete help text everywhere already; **IdeaPress had ~40 gaps**
   — every positional argument (`project_id`, `unit_key`, `task_id`, `workflow_id`, `prompt_id`)
   and several flags (`--json`, `--config`, `--content-type`, `--archived`) across nine command
   modules — filled in this row rather than left for the test to merely report.
9. **`pydantic-settings` removed** from all four `dependencies` (confirmed unimported first,
   `grep -rn pydantic_settings src/` empty in all four). `requirements/ci.lock` recompiled with
   pip-tools 7.6.1 on the scratchpad's Python 3.13.15 venv, header command with the bare
   `--no-index` dropped (kept `--no-emit-index-url`, already present) so it could actually reach an
   index. Each resulting diff is exactly the `pydantic-settings` lines and nothing else. **Proved**
   in a fresh `/usr/bin/python3.13` venv per app: `pip install --require-hashes -r
   requirements/ci.lock`, `pip install --no-deps -e .`, `import <app>` succeeds, `import
   pydantic_settings` fails, then the full gate (ruff format/check, mypy, lint-imports, `pytest -m
   "not live and not performance"`) — all four green (FreeWeight's one flaky test passed there
   too; see §6).
10. **`ui-ux-standards.md` §12**: confirmed it lists no help/about page for any application. Added
    one paragraph naming the System page as that page (present in LoadCoach, IdeaPress and
    PromptCadence) and recording that **FreeWeight has none** — `web/routes/system.py` serves
    `/version` and `/system/status` as JSON only, no `NAV_ITEMS` entry. **Did not build the page**,
    per instructions; this is a finding for another row.

## 5. What went wrong and was fixed

**A concurrent-session collision, caught and fixed within this row.** Row L3 was running in the
same four application trees. Committing item 8 in LoadCoach with `git add
tests/unit/test_every_command_has_help.py CHANGELOG.md && git commit` swept in
`tests/fixtures/databases/loadcoach-1.0.0.sqlite3` — L3 had staged it with its own `git add`
between this row's `add` and `commit`, and a bare `git commit` commits the whole index, not only
the paths just added. Caught immediately by inspecting `git show --stat HEAD`; fixed with `git rm
--cached` in a follow-up commit (`bfea4b6`), which untracks the file without touching it on disk —
L3 re-added and committed it normally afterward. Every commit made after this point in the row was
followed by `git status --short` before running `git commit`, specifically to catch this again;
none did.

## 6. What was found and not fixed (flaky, pre-existing)

`FreeWeight/tests/integration/test_sse_replay.py::TestHttpLevel::test_a_finished_run_streams_its_events_over_http`
failed twice in this row — both times only under full-suite load (with `--cov`, and in the
`/usr/bin/python3.13` clean-venv proof under the same load), on a `time.monotonic() < deadline`
race waiting for a scheduler thread ("run stuck in preparing"). Passed in isolation both times it
was rerun alone, and passed in the row's first full non-coverage run. Nothing in this row touches
the scheduler, the SSE machinery, or anything this test exercises — not diagnosed further, named
here for whichever row next runs FreeWeight's suite under load.

## 7. What the operator has to do

Nothing blocking. All five repositories are gate-green and committed on `main`. Merge and push at
the operator's discretion, same as every other row this cycle. Two findings for other rows: the
FreeWeight help/about HTML page (§4 item 10) and the FreeWeight SSE scheduler flake under load
(§6).
