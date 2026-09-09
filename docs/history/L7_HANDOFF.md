# L7 handoff — M9 residue, the mechanical half

**Row:** L7 (Sonnet 5 · standard), `docs/roadmap/outstanding-work.md` §1, gated on L6.
**Read first:** `M9_REAUDIT.md` (the evidence for every item below), `CLAUDE.md`.
**Components touched:** all fourteen component repos plus `docs`. Concurrent agents were building
FreeWeight's System page (`src/freeweight/web/*`, its tests, `docs/quickstart.md`, `NAV_ITEMS`) and
writing `docs/reviews/operator-questions-2026-09-07.md` + `docs/WALKTHROUGH.md` in parallel; none of
those files were touched, and the walkthrough/System-page work is visible in the git log as
commits from those sessions, not this one.

---

## 1. What was built, item by item

**(1) IdeaPress `baseaicore` floor.** `pyproject.toml`: `baseaicore>=0.4.1,<0.5` →
`baseaicore>=0.4.2,<0.5`, with a comment naming `modelrack 0.7`'s own floor as the reason the old
range could never resolve. README `## Compatibility` table row updated to match.
`requirements/ci.lock` recompiled with pip-tools 7.6.1 (`pip-compile --extra=dev --extra=postgres
--generate-hashes --no-emit-index-url --output-file=requirements/ci.lock
--pip-args='--no-cache-dir' --strip-extras -P baseaicore pyproject.toml`, per the repo's own
`requirements/README.md`, which documents that the header's literal `--no-index` is pip-tools'
own rendering of `--no-emit-index-url` and is never passed as a real flag). **Confirmed: no hash
change** — `baseaicore==0.4.2` was already the resolved pin (modelrack 0.7's own floor forced it),
so the lock file is byte-identical before and after. CHANGELOG entry added.

**(2) `docs/upgrading.md` in all four applications**, extended to the version each repository
holds today:

| App | Was | Now |
|---|---|---|
| FreeWeight | table stopped at 1.1.0 | + rows for 1.1.1, 1.1.2 (both dependency-only) |
| LoadCoach | table stopped at 1.1.3 | + rows for 1.1.4, 1.1.5 (both dependency-only) |
| IdeaPress | sections stopped at "1.2.0 → 1.3.0" | + section "1.3.0 → 1.3.2" (both patches dependency-only; 1.3.1's `modelrack` widen is the one operator-visible fact — the four applications can co-install again) |
| PromptCadence | table stopped at 1.3.0 | + rows for 1.3.1, 1.3.2 (both dependency-only) |

Each read its own CHANGELOG first; every one of these eight patch versions is dependency-floor or
test/doc only, so each gets the one-line "no schema change / no operator behaviour change" the row
asked for rather than a fabricated behaviour-changes section.

**(3) CutCtx and ToolYard.** `## Install` added to both READMEs (`pip install cutctx` /
`pip install toolyard`), placed where every other package puts it — right after the Status
paragraph, before the first content heading. `docs/quickstart.md` + `docs/quickstart.py` added to
both, in LoadLedger's shape (Install → Run it → real, captured output). Both scripts are true
ten-line examples (CutCtx: build a transcript, plan a `DropOldestPolicy` compaction, apply it;
ToolYard: register one tool, execute it, execute an unregistered one to show a refusal) and were
**run in each repo's own venv** to capture the real output printed in the docs — not invented.
Both packages select ruff's `T20` rule, so a `"docs/*.py" = ["T20"]` per-file-ignore was added to
each `pyproject.toml`, copying LoadLedger's own precedent and comment.

**(4) `tests/unit/test_readme_version.py` in all fourteen repositories.** Each repo's README
states its version in a different convention; the test's regex is the same generic
`Status:(?:.|\n)*?(\d+\.\d+\.\d+)` in every file (first digit-triple after the `Status:` marker),
which is deliberately convention-agnostic — see the table below for what each repo's convention
actually looks like. Ran in every repo's own venv; all fourteen pass.

Conventions found:

| Repo | Convention |
|---|---|
| BaseAiCore, ModelRack, CutCtx, ToolYard, SetSpec | `` `X.Y.Z` `` in backticks somewhere in the Status paragraph |
| SweatMeter | `` `sweatmeter 0.4.0` `` — package name + version together in backticks |
| Commissioner | `**0.1.1.**` — bold, no backticks |
| WeightsDB | **no version at all** before this row |
| LoadLedger (before fix) | two version-like tokens ("`0.3.0` prepared; `0.2.0` on PyPI") |
| FreeWeight, LoadCoach, IdeaPress, PromptCadence | LoadCoach's own convention: `` `X.Y.Z` in the repository — `vX.Y.Z` tagged locally (not yet pushed); **PyPI still serves `A.B.C`** `` |

Fixed as part of the same pass, per the row's instruction to fix READMEs the audit's convention
implied were stale (the row's own text says "eleven" — the actual count, checked against every
`__about__.py` and every README, is **six**: WeightsDB (no version stated — now states `0.2.1`,
MirrorWall's convention), LoadLedger (stale "prepared" wording — now `` `0.3.0`, on PyPI ``), and
all four applications (each one release-cycle behind — see the table below). Saying so rather
than inventing five more: `M9_REAUDIT.md`'s own D1(b) table names exactly these five plus
WeightsDB's missing version; nothing else in any of the other nine READMEs was stale.

| App | Was | Now |
|---|---|---|
| FreeWeight | `` `1.1.0`, on PyPI `` | `` `1.1.2` in the repository — `v1.1.2` tagged locally (not yet pushed); PyPI still serves `1.1.1` `` |
| LoadCoach | `` `1.1.3` in the repository — `v1.1.2` tagged … PyPI serves `1.0.0` `` | `` `1.1.5` … `v1.1.5` tagged … PyPI still serves `1.1.4` `` |
| IdeaPress | `` `1.2.0`, on PyPI `` | `` `1.3.2` … `v1.3.2` tagged … PyPI still serves `1.3.1` `` |
| PromptCadence | `` `1.2.0`, on PyPI `` | `` `1.3.2` … `v1.3.2` tagged … PyPI still serves `1.3.1` `` |

**(5) IdeaPress `ci.yml`.** `install-check` now installs `pip install
"$(ls dist/*.whl)[telemetry]"` and imports `sweatmeter` from the built wheel, beside the existing
`[postgres]` proof. A `live` job was added under the same `if: github.event_name == 'schedule' ||
github.event_name == 'workflow_dispatch'` guard as the existing `performance` job, running
`pytest -m live -rs` — the shape used by FreeWeight's, LoadCoach's and PromptCadence's own
`nightly.yml` `live` jobs (ModelRack's is the same shape but disabled with `if: false` for lack of
a self-hosted Ollama runner; IdeaPress's five `tests/live/` files are expected to skip themselves
honestly on a hosted runner, which is exactly what `-rs` is for). Validated with
`python -c "import yaml; yaml.safe_load(...)"`.

**(6) FreeWeight `db-matrix` job.** The row names a job called `db-matrix`; FreeWeight's actual
job with this role is named `postgresql-tests` (LoadCoach's is the one literally called
`db-matrix`) — treated as the same target. Read `py/WeightsDB/src/weightsdb/testing.py`:
`temporary_postgres()` reads `WEIGHTSDB_POSTGRES_URL` (not `WEIGHTSDB_TEST_DSN`, which does not
exist) and `WEIGHTSDB_REQUIRE_POSTGRES`. Added both, pointed at the same service container
FreeWeight's own `FWTEST_*` variables already use
(`postgresql+psycopg://freeweight:freeweight@localhost:5432/freeweight_test`), so
`test_backup_round_trips_or_refuses_restore_on_both_dialects` now actually exercises its
PostgreSQL leg in CI instead of skipping silently — this was M9_REAUDIT's own nit, confirmed by
reading the test and the job side by side.

**(7) Docs nits.** `standards/gold-standards.md` §1.1: the "declared but unapproved — owed
removal" paragraph about `pydantic-settings` replaced with a past-tense sentence recording that it
was removed (ADR-0114 decision 4). `README.md` §11: "three application API documents" → "four".
`roadmap/outstanding-work.md` §5's M9 row: "over the nine existing components" → "over the
fourteen components". Two adjacent stale mentions in `README.md` (§11's own table row "the three
API documents", and the "What this run found" bullet naming PromptCadence's missing `api.md`) were
left alone on purpose — they are dated findings from the 2026-09-07 review's own narrative
("Pass, with a gap … (row L5)", "Scheduled as row L5"), not a live count, and rewriting a finished
review's own findings after the fact is the ADR-0042 mistake the re-audit itself warns against.

---

## 2. An entanglement worth knowing about

A concurrent session was building FreeWeight's System page in the same working tree at the same
time. `CHANGELOG.md` was not on either session's "do not touch" list, and both sessions edited it
in the same `## [Unreleased]` section. That session's commit `c2dc2c4` ("feat(web): the system
page") ended up carrying this row's `CHANGELOG.md` bullets (the `test_readme_version.py` addition
and the README/`docs/upgrading.md` fixes) alongside its own, because both edits landed on disk
before either session committed. **No content was lost** — the bullets are present, worded
exactly as this row wrote them — but the commit boundary is mixed: `c2dc2c4` is not a pure
"System page" commit. This row's own commit (`dd9efb8`) carries everything else (the workflow
file, the README fix, the upgrade guide, the new test) and says so in its own message. Nothing
was done to fix the entanglement itself — rewriting another session's already-made commit would be
an amend of someone else's work, which is out of bounds here.

---

## 3. Gates run

Every repository whose code or tests changed got the full gate in its own venv (`ruff format
--check .`, `ruff check .`, `mypy src tests`, `lint-imports`, `pytest -m "not live and not
performance" -q`, full suite for the four applications). All green:

| Repo | Interpreter | Result |
|---|---|---|
| BaseAiCore | 3.13 | 648 passed, 7 deselected |
| SetSpec | 3.13 | 1073 passed, 4 skipped |
| ModelRack | 3.13 | 1434 passed, 16 skipped, 26 deselected |
| SweatMeter | 3.13 | 352 passed, 9 deselected |
| WeightsDB | 3.13 | 130 passed, 10 skipped, 6 deselected |
| MirrorWall | 3.13 | 313 passed |
| LoadLedger | 3.13 | 220 passed, 31 skipped (PostgreSQL leg honestly skips — no server here), 6 deselected |
| CutCtx | 3.13 | 402 passed, 4 deselected |
| ToolYard | 3.13 | 749 passed, 2 skipped, 4 deselected |
| Commissioner | 3.13 | 116 passed, 12 skipped, 2 deselected |
| FreeWeight | 3.14 | 2616 passed, 29 skipped, 30 deselected |
| LoadCoach | 3.14 | 1049 passed, 5 skipped, 18 deselected |
| IdeaPress | 3.13 | 1157 passed, 6 skipped, 30 deselected |
| PromptCadence | 3.13 | 1288 passed, 3 skipped, 10 deselected |

`docs/` has no code gate.

---

## 4. What could not be done, or was deliberately left alone

* **Nothing in the seven items was skipped.** The one judgment call — fixing six stale READMEs
  rather than the row text's "eleven" — is recorded in §1 above rather than silently done.
* **The FreeWeight `CHANGELOG.md` entanglement** (§2) is not a defect in this row's work, but it
  means a future reader diffing `c2dc2c4` should not expect it to be purely about the System page.
* **The two README lines this row deliberately did not touch** (docs/README.md's dated "three API
  documents" gap-note and "Scheduled as row L5" bullet) are named in §1(7) with the reasoning.

## 5. Commits

One commit per repository (per-item splitting inside a repo was not attempted where two items
touched the same shared file — `CHANGELOG.md` and `README.md` in the four applications and
IdeaPress — because git-level splitting of interleaved prose edits was not worth the risk of a
bad hunk boundary for a mechanical, single-session pass):

* BaseAiCore `bf55df5`, SetSpec `6d68db5`, ModelRack `ff4260f`, SweatMeter `1f1a09d`, MirrorWall
  `09d251d`, Commissioner `53d49de` — `test(readme): guard README version against drift`
* WeightsDB `3a9551b`, LoadLedger `c4ab8f2` — `docs+test(<pkg>): …, guard against drift`
* CutCtx `9fc70da`, ToolYard `4f9d30b` — `docs+test(<pkg>): add Install section, quickstart, and a
  README version guard`
* IdeaPress `17e8f20` — `fix(deps)+docs+test(ideapress): M9 residue, the mechanical half (row L7)`
* FreeWeight `dd9efb8` — `docs+test+ci(freeweight): M9 residue, the mechanical half (row L7)`
  (rides on top of the concurrent session's `c2dc2c4`, see §2)
* LoadCoach `1f83b95`, PromptCadence `3314939` — `docs+test(<app>): M9 residue, the mechanical
  half (row L7)`
* docs `3d3d2cf` — `docs: three M9 re-audit nits (row L7)`

`git status --short` was run in every one of the fifteen repositories at the start of this row
(all clean except `docs`' then-untracked `WALKTHROUGH.md`, which belonged to a concurrent session
and was left alone and has since been committed by that session) and again at the end (all clean).
