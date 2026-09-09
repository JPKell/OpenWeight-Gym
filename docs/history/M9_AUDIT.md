# M9 audit — the professional delivery checklist, walked against all fourteen repositories

**Audited 2026-09-07** against the working tree as it stood at ~11:45 PDT, by an Opus 5 · high
read-only session. Sources: [master-roadmap §7](docs/roadmap/master-roadmap.md),
[outstanding-work §1.1](docs/roadmap/outstanding-work.md),
[packaging §1.1/§5/§6/§7/§10](docs/standards/packaging-and-release-standards.md),
[gold-standards §1/§3/§4](docs/standards/gold-standards.md). Evidence is a file, a CI job, a test,
a command I ran, or a GitHub/PyPI query — never a sentence in a spec.

> **Tree was live during the audit.** LoadCoach was mid-edit by another session (`__about__.py` at
> `1.1.3`, nine files modified, uncommitted); LoadLedger carries an uncommitted `src/loadledger/pricing.py`
> and `tests/unit/test_pricing.py`. LoadCoach rows below describe the committed state at `e691c4e`
> except where the running CLI reported `1.1.3`. Nothing in this audit was written to any repository.

---

## Verdict

**M9 is not met, but the shortfall is almost entirely in the last mile rather than in the
engineering.** The CI substrate is in excellent, genuinely uniform shape: all fourteen repositories
carry `requirements/ci.lock` + `release.lock` and install from them with `--require-hashes`, all
fourteen run `pip-audit` over both locks plus `gitleaks` as blocking jobs, all fourteen run the
3.12/3.13 matrix with a non-blocking 3.14 early-warning job and a clean-venv `install-check`, and all
fourteen have a `release.yml` gated on the `pypi` environment with a Trusted-Publishing OIDC publish
and a manual TestPyPI dry run — no manual upload has ever occurred, and every current package
version is on PyPI. What is missing is the part a person *sees*: **eleven of fourteen READMEs state
the wrong version or status**, and IdeaPress's says the application is "specified, not yet
implemented" while `ideapress 1.2.0` sits on PyPI. Behind that, the checklist's operational
promises are the thinnest: no `SchemaAhead` refusal is exercised by any test in any application, no
downgrade drill exists, backup/restore is tested on SQLite only, the cross-repository compatibility
matrix job does not exist anywhere, ten of fourteen repositories have `tests/performance/` that CI
never runs, no performance budget has been published with its reference machine described, and the
documentation consistency review the checklist requires is dated 2026-08-21 — before five of the
fourteen components existed and before 92 of the 113 ADRs were written. **9 of 28 items are met
outright, 10 are partial, 9 are unmet.** None of the gaps is architectural; all of them are a week
of ordinary sessions plus two operator steps.

---

## Matrix

Legend: **✓** met, with an artifact · **~** partial (evidence exists but does not cover the claim) ·
**✗** unmet · **–** not applicable.

Components: BAC BaseAiCore · SS SetSpec · MR ModelRack · SM SweatMeter · WDB WeightsDB ·
MW MirrorWall · LL LoadLedger · CC CutCtx · TY ToolYard · CM Commissioner ·
FW FreeWeight · LC LoadCoach · IP IdeaPress · PC PromptCadence.

| # | Item | BAC | SS | MR | SM | WDB | MW | LL | CC | TY | CM | FW | LC | IP | PC |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Installation and distribution** |
| I1 | clean-venv PyPI install, zero configuration | – | – | – | – | – | – | – | – | – | – | ✗ | ✗ | ~ | ~ |
| I2 | `pipx install` verified | – | – | – | – | – | – | – | – | – | – | ✗ | ✗ | ✗ | ✗ |
| I3 | installable and importable standalone | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| I4 | `python -m <app>` works | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ |
| I5 | `[postgres]` extra installs and functions | – | – | – | – | – | – | – | – | – | – | ~ | ~ | ~ | ~ |
| **Releases** |
| R1 | released from a tag by CI, Trusted Publishing, no manual upload | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| R2 | semantic version + changelog + release notes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✓ |
| R3 | compatibility matrix published per application | – | – | – | – | – | – | – | – | – | – | ✗ | ✗ | ✗ | ~ |
| R4 | checksums published for application artifacts | – | – | – | – | – | – | – | – | – | – | ✗ | ✗ | ✗ | ✗ |
| **Documentation** |
| D1 | README: purpose, install, quickstart, links — **and accurate** | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| D2 | configuration reference generated, CI-diff-checked | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ |
| D3 | OpenAPI snapshot + written API guide | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✗ |
| D4 | `--help` complete at every CLI level | – | – | – | – | – | – | – | – | – | – | ~ | ~ | ~ | ~ |
| D5 | web UI help/about page | – | – | – | – | – | – | – | – | – | – | ✗ | ~ | ~ | ~ |
| D6 | troubleshooting guide aligned with `doctor` | – | – | – | – | – | – | – | – | – | – | ✓ | ~ | ~ | ✗ |
| D7 | security documentation (boundaries, exposure, egress, sandbox) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| D8 | backup/restore procedure, tested | – | – | – | – | – | – | – | – | – | – | ✓ | ~ | ✗ | ~ |
| D9 | upgrade guide from **every** released version + rollback | – | – | – | – | – | – | – | – | – | – | ~ | ~ | ✗ | ✗ |
| D10 | developer docs + `CONTRIBUTING.md` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| D11 | documentation set consistency-reviewed (§8) and published | ✗ *(suite-wide: review dated 2026-08-21)* |
| **Quality** |
| Q1 | every gold standard met and measured | ✗ *(suite-wide: G11, G16, G19, G20)* |
| Q2 | coverage floors met in every repository | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Q3 | performance budgets measured on the reference machine, published | ✗ *(suite-wide)* |
| Q4 | security checklist complete; `pip-audit` + `gitleaks` clean | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Q5 | accessibility checklist complete for every UI | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ |
| Q6 | cross-repository compatibility matrix green | ✗ *(suite-wide: no such job exists)* |
| **Operations** |
| O1 | migration path tested from every released version, real data | – | – | – | – | – | – | – | – | – | – | ~ | ✗ | ✗ | ✗ |
| O2 | downgrade drill exercised; `SchemaAhead` names both revisions | – | – | – | – | – | – | – | – | – | – | ✗ | ✗ | ✗ | ✗ |
| O3 | dependency ranges admit the **1.0** packages, clean-venv resolve | ✗ *(suite-wide: no package has reached 1.0; master-roadmap §6 puts that at M9)* |
| O4 | backup/restore tested on both dialects | – | – | – | – | – | – | – | – | – | – | ✗ | ✗ | ✗ | ✗ |
| O5 | `doctor` diagnoses every documented failure mode | – | – | – | – | – | – | – | – | – | – | ✓ | ~ | ~ | ✗ |
| O6 | degradation matrix exercised end to end | ✗ *(suite-wide: the matrix has no PromptCadence column)* |

**Tally: 9 met · 10 partial · 9 unmet (of 28).**
Met outright: I3, I4, D2, D7, D10 (13/14), Q2 (13/14), Q4 (13/14), Q5, R1 (12/14).

### What is unambiguously in place (do not re-audit)

* `requirements/ci.lock` + `release.in` + `release.lock` in **all fourteen**; every dependent CI job
  installs with `pip install --require-hashes -r requirements/ci.lock`; `build` installs from
  `release.lock` and runs `python -m build --no-isolation`.
* `.github/workflows/release.yml` in **all fourteen**: `on: push: tags: ["v*.*.*"]`,
  `environment: pypi`, `id-token: write`, `pypa/gh-action-pypi-publish@release/v1`, a
  `publish-testpypi` job on `workflow_dispatch` pointing at `https://test.pypi.org/legacy/`, and a
  `softprops/action-gh-release@v2` step. No `twine upload` anywhere.
* `pip-audit --require-hashes` over **both** locks plus `gitleaks/gitleaks-action@v2` (with
  `fetch-depth: 0`) as a blocking `security` job in all fourteen.
* `install-check` job in all fourteen (clean runner, wheel from the `build` artifact, import check;
  BaseAiCore additionally proves `py.typed` and consumer-side mypy, SetSpec that schemas and goldens
  ship, SweatMeter a standalone five-line script).
* Matrix `["3.12","3.13"]` plus a `continue-on-error: true` 3.14 early-warning job in all fourteen.
* `## [Unreleased]` in 13/14 changelogs; `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE` in 13/14.
* All ten packages are on PyPI at exactly their `__about__.py` version; `ideapress 1.2.0` and
  `promptcadence 1.2.0` published today by CI from a tag (runs 34151893212 / 34151896256).
* All four apps: `--version`, `doctor`, `db backup`/`db restore`, `config reference` drift test,
  `docs/openapi.json` byte-compared against the served application, `tests/accessibility/test_ui_checklist.py`,
  `docs/security.md`, `docs/troubleshooting.md`, `docs/upgrading.md`, `docs/quickstart.md`.
* All four root demos run clean against their component venvs (`demo_baseaicore.py`,
  `demo_setspec.py`, `demo_modelrack.py`, `demo_sweatmeter.py`).
* Every mirrored document under `docs/` is byte-identical in every component copy (checked with
  `cmp` over `git ls-files`; the only differences are each repo's own `docs/README.md`, which is
  deliberately per-repo and was restored across all fourteen at 18:27 today).

---

# The gaps, grouped into sessions

Ranked by how visible the gap is to a person walking the suite next week.

---

## Group 1 — The READMEs lie about what is shipped · **Sonnet 5 · standard** · items D1, R2

**The most visible defect in the suite by a wide margin.** Eleven of fourteen READMEs open with a
`**Status:**` line naming a version that is behind what the repository is, and in three cases behind
what is *on PyPI*.

| Repo | README says | Truth |
|---|---|---|
| IdeaPress | "specified, **not yet implemented**. This repository currently holds the project scaffold" | `1.2.0`, on PyPI, 9 phases + two adoption rows |
| FreeWeight | `1.0.0rc1` — Phases 1–11 | `1.1.0` tagged, LA3 complete through P15 |
| LoadCoach | `1.0.0` — the M5 release; "`weightsdb 0.2.0` and `mirrorwall 0.2.0`" | `1.1.3` in tree, `v1.1.2` tagged; weightsdb 0.2.1, mirrorwall 0.2.2 |
| PromptCadence | `1.0.0` (M12) | `1.2.0`, on PyPI |
| CutCtx | "`0.1.0` **prepared** … nothing here is on PyPI yet" | `cutctx 0.1.0` **is** on PyPI |
| ToolYard | "Phase 3 complete, `0.1.0` prepared … nothing here is on PyPI yet" | `toolyard 0.1.1` **is** on PyPI |
| BaseAiCore | `0.4.1` | `0.4.2` |
| ModelRack | `0.7.0` | `0.7.1` |
| MirrorWall | `0.2.0` | `0.2.2` |
| LoadLedger | `0.1.0` | `0.2.0` |
| Commissioner | `0.1.0` | `0.1.1` |

Accurate today: SetSpec (`0.6.0`), SweatMeter (`0.4.0`), WeightsDB (phase-based, no version claim).

Also in this group:

* **CutCtx and ToolYard have no `## Install` and no quickstart** in their READMEs, and no
  `docs/README.md` or `docs/quickstart.md` at all — their `docs/` holds only the mirrored
  `packages/<pkg>/spec.md` and `development-plan.md`. Every other package repo has at least a
  `docs/README.md`; seven have a `docs/quickstart.md`.
* **LoadCoach's README has no quickstart heading** (it has "What it does" and a docs table).
* **FreeWeight's `CHANGELOG.md` has no `## [Unreleased]` heading** — the only one of fourteen
  without it, and the coding conventions make it the landing place for every user-visible change.

**Smallest change that meets it:** rewrite eleven `**Status:**` paragraphs against
`src/*/__about__.py` and `pip index versions`; add `## Install` + a five-line quickstart to
CutCtx's and ToolYard's READMEs and a `docs/README.md` to each; add a quickstart heading to
LoadCoach's README; add `## [Unreleased]` above `## [1.1.0]` in FreeWeight's changelog. Consider
a `tests/unit/test_readme_states_the_version.py` in each repo (one assert: the README contains
`__version__`) so this cannot rot again — that is the artifact, not the edit.

---

## Group 2 — Two applications are tagged but unpublished · **operator step, not a model session** · items R1, I1

`FreeWeight v1.1.0` (tagged 2026-09-07) and `LoadCoach v1.1.0` (2026-09-06) / `v1.1.2` (2026-09-07)
exist only locally. `gh release list` shows both repositories' newest GitHub release is still
`v1.0.0`, and `gh run list --workflow=release.yml` shows LoadCoach's last release run was
`v1.0.0` on 2026-08-31 — so the tags were never pushed and `release.yml` never fired. PyPI
confirms: `freeweight 1.0.0`, `loadcoach 1.0.0`.

This is exactly the standing instruction working as designed (sessions commit and tag locally; the
operator pushes). But **M9 cannot be declared while it stands**: item R1 is false for two of four
applications, and I1 ("`pip install freeweight|loadcoach` into a clean venv") installs a version
a year of work behind the tree. LoadCoach additionally has an uncommitted `1.1.3` in progress.

**Smallest change:** `git push --tags` in FreeWeight and LoadCoach once LoadCoach's in-flight
`1.1.3` is committed, then verify with `pip index versions`. No model session required.

---

## Group 3 — Operations promises with no test behind them · **Sonnet 5 · high** · items O1, O2, O4, D8

The checklist's Operations block is the least-evidenced part of M9. Four specific holes:

**O2 — `SchemaAhead` is implemented and never exercised.** `weightsdb.errors.SchemaAhead` is
raised from `bootstrap.py` in FreeWeight, LoadCoach and PromptCadence and from
`services/database.py` in all four, and packaging §6.1 makes the refusal a named 1.0 promise
("a database ahead of the code raises `SchemaAhead` at startup and names both revisions and the
backup directory"). **Zero tests reference it in any of the four applications**, and WeightsDB's
own suite references it once, in `tests/contract/test_public_api.py` — i.e. only that the name is
exported. LoadCoach and IdeaPress reference the `SCHEMA_AHEAD` *error code* in a doctor/envelope
test; nothing drives the startup path. The full drill packaging §6.1 requires — upgrade, write
data, restore the pre-migration backup, start the older version — exists nowhere.

**O4 — backup/restore is SQLite-only everywhere.** `FreeWeight/tests/integration/test_backup_restore.py`
is thorough (WAL, corrupt-backup refusal, no leftover pre-restore file) and entirely
`sqlite:///`. PromptCadence has one `test_backup_then_restore_round_trips_the_schema` in
`test_migrations.py`, SQLite. LoadCoach tests the CLI verb only. **IdeaPress has no database
backup/restore test at all** — its only "backup" hits are `tests/security/test_project_archives.py`,
which is about project export. All four repos already have a working
`weightsdb.testing.temporary_postgres` fixture and a green `db-matrix` job to hang this on.

**O1 — migration from every released version.** Only FreeWeight ships a real released-version
database: `tests/fixtures/databases/freeweight-1.0.0rc1.sqlite3`, exercised by
`test_rc1_database_migrates_to_0008_and_keeps_its_rows`. That fixture is from `1.0.0rc1`, not from
the two versions actually released since. LoadCoach, IdeaPress and PromptCadence have **no
`.sqlite3` fixture anywhere** — their migration tests all start from empty.

**D8** follows from O4: the procedures are written (`FreeWeight/docs/backup-restore.md`,
`{LoadCoach,IdeaPress,PromptCadence}/docs/operations.md § Backups`) but "tested" is only true for
FreeWeight, and only on one dialect.

**Smallest change:** one `tests/integration/test_downgrade_and_schema_ahead.py` per application
(≈60 lines: upgrade to head, write a row, `db backup`, hand-set `alembic_version` ahead, assert the
bootstrap raises `SchemaAhead` naming both revisions, `db restore`, assert the older revision
starts); parametrize the existing backup/restore tests over
`temporary_sqlite`/`temporary_postgres`; capture one `.sqlite3` fixture per released version at
release time and add it to the migration test. IdeaPress needs the backup/restore test written
from scratch.

---

## Group 4 — CI job parity: ten repos never run their own performance tests · **Sonnet 5 · standard** · items Q1 (G19, G11), Q2, Q3, I1, I4, I5

Every repository has a `tests/performance/` directory (2–5 files each) and six have `tests/live/`.
**Only four repositories ever run them:** ModelRack and FreeWeight via `nightly.yml`, SweatMeter via
a `nightly-hardware` job on `ci.yml`'s schedule, IdeaPress via a `performance` job on its schedule.
LoadCoach and PromptCadence — four and three live files, five and four performance files — have no
`schedule:` trigger at all. Packaging §5 requires a nightly `pytest -m performance` + `pytest -m live`
in every repository; gold standard G19 makes it the gate for "application overhead is measured".

| Sub-gap | Where | Evidence looked for |
|---|---|---|
| No nightly perf/live job | BAC, SS, WDB, MW, LL, CC, TY, CM, LC, PC (10) | `schedule:` in `.github/workflows/*.yml` |
| No `diff-cover --fail-under=90` (G11, packaging §5) | all but FreeWeight (13) | `diff-cover` in any workflow |
| Coverage floor enforced at 85 against a 95 pyproject floor | MirrorWall | `ci.yml` `coverage` job runs `--cov-fail-under=85`; `pyproject.toml` says `fail_under=95` |
| `install-check` never runs `<app> --version` | FW, LC, IP, PC | packaging §5 names it explicitly; the four app jobs stop at `python -c "import <pkg>"` |
| `install-check` never runs `python -m <app>` or installs `[postgres]` | FW, LC, IP, PC | packaging §10 lists both as install targets |
| `pipx install` never verified anywhere | all four apps | `grep -r pipx` hits only three docs files, no workflow, no README |
| FreeWeight's extra is `[postgresql]`, the other three are `[postgres]` | FW | packaging §10 documents `pip install <app>[postgres]` |

**Smallest change:** copy ModelRack's `nightly.yml` into the ten repositories that lack one (it is
40 lines and already parameterized); add a `diff-cover` step to the twelve `coverage` jobs that
lack one, modelled on FreeWeight's; change MirrorWall's `--cov-fail-under=85` to `95`; append four
lines to each app's `install-check` (`<app> --version`, `python -m <app> --version`,
`pip install "dist/*.whl[postgres]"`, `pipx install ./dist/*.whl && <app> --version`); alias
FreeWeight's extra so both `postgres` and `postgresql` resolve, and document the canonical one.

---

## Group 5 — Documentation the checklist names and the repos do not have · **Sonnet 5 · high** · items D3, D5, D6, D9, D10, R3, R4, Q4

Individually small, collectively the difference between "shipped" and "delivered".

* **PromptCadence has no written API guide.** FreeWeight, LoadCoach and IdeaPress each carry
  `docs/apps/<app>/api.md`; `docs/apps/promptcadence/` holds only `spec.md`, `lifecycle.md` and
  `development-plan.md`. `docs/openapi.json` is committed and byte-tested, so half of D3 is met.
  (PromptCadence also has no `data-model.md` or `risks.md`, which its three siblings have.)
* **PromptCadence has no `CONTRIBUTING.md`** — the only repository of fourteen without one.
* **No application publishes a compatibility matrix (R3).** Packaging §7 requires each application
  to declare, *in its README and release notes*, the tested version ranges of every suite package.
  The ranges exist — and the `pyproject.toml` comments explaining each floor and ceiling are
  genuinely excellent — but they live only there. PromptCadence's `docs/upgrading.md § Compatibility`
  is the sole prose version, and it is stale (it describes `1.0.1`; the package is `1.2.0`).
  `generate_release_notes: true` in every `release.yml` produces GitHub's commit-derived notes, not
  the changelog-plus-compatibility section §6 requires.
* **No checksums are published (R4).** No workflow references `sha256sum`, `SHA256SUMS` or
  `attestations`; the GitHub release attaches `dist/*` bare. PyPI's own per-file hashes and the
  publish action's default PEP 740 attestations partially cover this, but the "signed checksum file
  for the artifacts" packaging §6 requires post-1.0 does not exist.
* **Upgrade guides do not cover every released version (D9).** IdeaPress's `docs/upgrading.md`
  heads a section "1.1.0 → 1.2.0 **(unreleased, row J1)**" — 1.2.0 published today. PromptCadence's
  compatibility section stops at 1.0.1. FreeWeight's `docs/upgrading.md` has no per-version sections
  at all. LoadCoach's is the best of the four (per-version "Behaviour changes" for 1.0.0 and 1.1.0)
  and stops before 1.1.2/1.1.3.
* **Troubleshooting↔doctor alignment is tested once (D6/O5).** Only FreeWeight has
  `tests/unit/test_troubleshooting_covers_doctor.py`, which is the right artifact: it proves the
  guide covers every check the command runs. LoadCoach's `tests/unit/test_doctor.py` asserts the
  code set, IdeaPress's asserts behaviour, and **PromptCadence's only doctor test is
  `test_doctor_runs_and_exits_zero_when_degraded_not_unavailable`** — a smoke test.
* **IdeaPress has no security-checklist test (Q4).** FreeWeight (`test_security_checklist.py`),
  LoadCoach and PromptCadence (`test_checklist.py`) each assert their security doc's checklist
  against the code; `IdeaPress/tests/security/` holds only `test_lan_exposure.py`,
  `test_project_archives.py` and `test_sanitization_sweep.py`.
* **No application has a help/about page (D5).** LoadCoach, IdeaPress and PromptCadence have a
  `system/index.html` in the nav that renders the version and health components — close, and
  probably sufficient if the item is reinterpreted — but none links to its own documentation.
  **FreeWeight has no HTML system page at all**: `web/routes/system.py` serves `/version` and
  `/system/status` as JSON, and `NAV_ITEMS` has no entry for it. Note that
  `ui-ux-standards.md §12`'s information architecture does not list a help or about page for any
  application, so the standard and the checklist disagree — resolve that first.
* **`--help` completeness is untested (D4).** Only FreeWeight and IdeaPress reference `--help` in a
  test, and neither walks the whole Typer tree. All four top-level `--help` outputs are complete and
  correct when run by hand (verified: 16, 16, 14 and 17 subcommands respectively).

**Smallest change:** write `docs/apps/promptcadence/api.md` and mirror it; copy a `CONTRIBUTING.md`;
add a `## Compatibility` table to each app README generated from `pyproject.toml` (and a test that
compares them, so it cannot drift); add a `sha256sum dist/* > SHA256SUMS` step before
`action-gh-release` in the four app `release.yml`s; refresh the four `docs/upgrading.md` files to
the shipped versions; port FreeWeight's `test_troubleshooting_covers_doctor.py` to the other three;
port a `test_checklist.py` into IdeaPress; add one `test_every_command_has_help` per app that walks
`typer.main.get_command(app)` recursively.

---

## Group 6 — The two suite-wide jobs that do not exist · **Sonnet 5 · high** · items Q6, Q3

**Q6 — the cross-repository compatibility matrix.** Packaging §7 requires a nightly job that
"installs the current release of each application against the lowest and highest supported version
of each package and runs the contract and e2e suites". `grep -rli compatibility` over all fourteen
repos' workflows returns exactly one hit: SetSpec's `cross-version-compatibility` job, which runs
`tests/contract/test_cross_version.py` — that is §7's *third* bullet (schema compatibility), a
different promise. **The matrix job exists nowhere**, in no repository and in no separate
harness, and it is a named line on both the M9 checklist and gold-standards §4.

This is the one gap where the resolve is genuinely load-bearing rather than cosmetic: FreeWeight
pins `setspec>=0.6,<0.7` while LoadCoach, IdeaPress and PromptCadence pin `setspec>=0.5,<0.7`, and
`modelrack` floors differ by two minors between FreeWeight (`>=0.7`) and IdeaPress (`>=0.5,<0.6`).
Nothing today proves the lower bound of any of those ranges still resolves and passes.

**Q3 — published performance budgets.** `grep -rn "reference machine"` across `docs/` returns ten
files, all of which *reference* the concept; `docs/architecture/performance-targets.md` states the
budgets. **No document publishes measured results with the machine described.** With Group 4's
nightly jobs absent in ten repos, most of those budgets have never been measured in CI at all.

**Smallest change:** one workflow — it does not need to live in a repo, but the natural home is the
docs repo or a new `suite-ci` — that builds a matrix over the four applications × {lowest, highest}
package pins, installs into a clean venv with `pip install "<app>==<v>" "setspec==<floor>" …`, and
runs `pytest -m "contract or e2e"`. For Q3, one `docs/architecture/performance-results.md`
populated from a single nightly run, with the reference machine's `machine_fingerprint` and the
`sweatmeter` snapshot beside the numbers.

---

## Group 7 — The documentation set no longer describes the suite it documents · **Opus 5 · high** · items D11, Q1 (G16, G20), O3, O6

The checklist itself, and the standards it cites, were written over nine components and three
applications. M9 is now declared over fourteen and four, and the documents have not followed.

* **`docs/README.md §11` — the consistency review — is dated 2026-08-21.** It says "all nine
  development plans", "all three specs", "all three API documents", "21 ADRs", "the 74 phases",
  "M1–M9". There are now fourteen plans, four specs, **113 ADRs**, and two arcs of milestones
  (M10–M13, LA0–LA3). Item D11 requires this review to be *run*, not merely to exist; running it
  over the current set is a real session's work and will find real drift.
* **`master-roadmap §7` — the M9 checklist itself — still reads "three applications" and "six
  packages"** ("`pip install freeweight|loadcoach|ideapress`", "All six packages installable"). So
  does `gold-standards §4`, including a parenthetical stating that suite 1.0 is declared over nine
  components with PromptCadence and its four packages deferred. The checklist must be restated over
  fourteen before it can be ticked.
* **`master-roadmap §9` is half-stale**: it lists IdeaPress at `1.1.0` (now 1.2.0, published) and
  PromptCadence at `1.2.0 (prepared)` (published today), and says M9 runs "over the nine components
  as they stand" while `outstanding-work §1.1` says fourteen.
* **The degradation matrix has no PromptCadence column (O6, G20).**
  `docs/architecture/graceful-degradation.md` has 30 condition rows across
  `FreeWeight | LoadCoach | IdeaPress`. G20 makes "every row of the degradation matrix has a test"
  a blocking CI gate; there is no index anywhere mapping rows to tests, and the newest application
  is absent from the matrix entirely.
* **The runtime dependency budget (G16) is exceeded and undocumented.** `gold-standards §1.1`
  allows each application "`fastapi`, `uvicorn`, `typer`, `pydantic-settings`, plus suite packages
  — ≤ 6 direct non-suite". FreeWeight declares **10** (adds `pydantic`, `sqlalchemy`, `alembic`,
  `jinja2`, `python-multipart`, `httpx`), IdeaPress 10, LoadCoach and PromptCadence 9. MirrorWall
  is budgeted 2 non-suite and declares 3 (`jinja2`, `starlette`, `anyio`). "Exceeding a budget
  requires an ADR"; none exists. Either the budget is wrong (likely — apps legitimately declare
  what they import) or five components are in violation. Only three repos have any dependency-set
  test at all (`BaseAiCore/tests/test_packaging.py`, `CutCtx/tests/unit/test_packaging.py`,
  `ToolYard/tests/unit/test_boundaries.py`).
* **O3 is unanswerable as written: no package has reached 1.0.** `master-roadmap §6` says
  "Packages reach 1.0 only at M9, when all three applications have exercised them", and the version
  trajectory table has a bold **1.0** in the M9 column for all six original packages. All ten sit at
  0.x. Whether M9 includes bumping ten packages to 1.0 — and what that means for the four
  applications' `<0.x+1` ceilings, every one of which would need widening — is an **architect's
  decision this audit cannot make**. It belongs in this session, as an ADR, before anything else in
  Group 7 is written.

**Smallest change:** one Opus session that (a) decides the package-1.0 question and records it as an
ADR, (b) restates `master-roadmap §7`, `§9` and `gold-standards §4` over fourteen components,
(c) adds a PromptCadence column to the degradation matrix, (d) reconciles `gold-standards §1.1`
with the four apps' and MirrorWall's actual dependency sets, and (e) re-runs the §11 consistency
review and re-dates it. Then a follow-up Sonnet session mirrors all of it into the fourteen repos.

---

## Suggested order

| # | Group | Model · effort | Why here |
|---|---|---|---|
| 1 | **Group 7** — the documents (package-1.0 decision first) | Opus 5 · high | Everything else ticks a checklist that is still written over nine components; the 1.0 question gates the version work |
| 2 | **Group 1** — the READMEs | Sonnet 5 · standard | Highest visibility per hour of any item on this list |
| 3 | **Group 2** — push the two tags | operator | Unblocks I1 and R1 for two of four applications |
| 4 | **Group 3** — the operations tests | Sonnet 5 · high | The checklist's least-evidenced block; four real promises with no test |
| 5 | **Group 4** — CI job parity | Sonnet 5 · standard | Mechanical, high-leverage: ten repos start measuring what they already assert |
| 6 | **Group 5** — the missing documents | Sonnet 5 · high | Larger surface, but each piece is independent and can be split |
| 7 | **Group 6** — the two suite-wide jobs | Sonnet 5 · high | Needs Group 4's nightly infrastructure and Group 7's version decision first |

Groups 1, 3, 4 and 5 are independent of each other and can run in parallel once Group 7 lands.
