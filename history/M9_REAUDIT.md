# M9 re-audit — the professional delivery checklist, re-scored after rows L1–L6

**Re-audited 2026-09-07, ~17:10 PDT**, by an Opus 5 · high read-only session, against
[`master-roadmap` §7 **as restated today** (row L2)](docs/roadmap/master-roadmap.md) over fourteen
components and four applications. Predecessor: `M9_AUDIT.md` (same day, ~11:45). Evidence is a file,
a workflow job, a test body, a tag, a PyPI query or a command I ran — never a sentence in a spec or
a handoff. Nothing was written to any repository; this file is the only artifact.

> **The tree moved under this audit.** The evening patch cycle is mid-flight: while I was reading,
> `freeweight` went `1.1.1 → 1.1.2` (uncommitted at the end), `loadcoach` `1.1.4 → 1.1.5` (tagged),
> `ideapress` `1.3.1 → 1.3.2` (tagged), `promptcadence` `1.3.1 → 1.3.2` (tagged), and `docs` gained
> row M1. PyPI at the close of the audit: `freeweight 1.1.1`, `loadcoach 1.1.4`, `ideapress 1.3.1`,
> `promptcadence 1.3.1`; all ten packages exactly at their `__about__.py` version. Rows below say
> which state they describe wherever it matters.

> **The checklist has 32 boxes, not 28.** §7 counts 5 installation + 4 releases + 11 documentation
> + 6 quality + 6 operations. The morning matrix listed all 32 rows correctly and its tally line
> ("of 28") was an arithmetic slip. This audit scores 32.

---

## Verdict

**M9 cannot be declared today — but it is close, and what remains is now nine named items rather
than a shortfall in the engineering.** Rows L1–L6 closed real ground and the closures verify in the
tree: `pipx`, `python -m <app>`, `<app> --version` and `[postgres]` are all exercised by every
application's `install-check`; a nightly `performance`+`live` schedule exists in all fourteen
repositories; `diff-cover --fail-under=90` is in all fourteen `coverage` jobs; MirrorWall's floor is
95/95; `SHA256SUMS` rides all four application releases; a `## Compatibility` table with a
**drift test** sits in all four application READMEs; `tests/integration/test_downgrade_and_schema_ahead.py`
exists in all four and genuinely asserts both revisions **and** the backup directory (and L3's fixes
to the production code behind it are real — IdeaPress and PromptCadence could not detect a
schema-ahead database at all before today); backup/restore is parametrized over
`temporary_sqlite`/`temporary_postgres` in all four; PromptCadence has `api.md`, `data-model.md`,
`risks.md` and a `CONTRIBUTING.md`; `docs/README.md` §11's consistency review was re-run and
re-dated; `docs/architecture/performance-results.md` and the docs repo's
`compatibility-matrix.yml` + `scripts/compatibility_matrix.py` both exist. **22 of 32 items are met
outright, 1 is waived in part, and 9 remain.** Of the nine, three are substantive — the
compatibility matrix has **never been green** and this audit found a *second* structural blocker
behind L6's mirrorwall one (IdeaPress floors `baseaicore>=0.4.1` while its own `modelrack 0.7.0`
floor requires `>=0.4.2`, so its `lowest` cell stays red even after tonight's publishes); G16's
budget test is owed by eleven repositories by the standard's own admission; and the degradation
index that L2 added records ~15 `untested` cells and says in its own words that "G20 cannot be
turned on until those are closed". Four more are pure rot from tonight's release cycle — every
application README status line and every `docs/upgrading.md` is already one release behind again,
and nothing tests either. The remaining two are small builds: FreeWeight's System page and
IdeaPress's `[telemetry]` extra in `install-check`. None of the nine is architectural; one Sonnet
session plus the pending PyPI approvals closes seven of them, and Q6/O3 additionally needs a
one-line pin fix in IdeaPress and a matrix run.

---

## Matrix

Legend: **✓** met, with an artifact · **~** partial · **✗** unmet · **W** waived, with the record
that waives it · **–** not applicable.
Δ column: change since the 11:45 audit (**↑** improved, **=** unchanged, **↓** worse).

Components: BAC BaseAiCore · SS SetSpec · MR ModelRack · SM SweatMeter · WDB WeightsDB ·
MW MirrorWall · LL LoadLedger · CC CutCtx · TY ToolYard · CM Commissioner ·
FW FreeWeight · LC LoadCoach · IP IdeaPress · PC PromptCadence.

| # | Item | BAC | SS | MR | SM | WDB | MW | LL | CC | TY | CM | FW | LC | IP | PC | Δ |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Installation and distribution** |
| I1 | clean-venv PyPI install, zero configuration | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| I2 | `pipx install` verified | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| I3 | installable and importable standalone | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | = |
| I4 | `python -m <app>` works | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| I5 | extras install and function (`[postgres]`/`[postgresql]`, IP `[telemetry]`) | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ~ | ✓ | ↑ |
| **Releases** |
| R1 | released from a tag by CI, Trusted Publishing, no manual upload | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ↑ |
| R2 | semantic version + changelog + release notes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ↑ |
| R3 | compatibility matrix published per application | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| R4 | checksums published for application artifacts | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| **Documentation** |
| D1 | README: purpose, install, quickstart, links | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✗ | ✗ | ✓ | ~ | ~ | ~ | ~ | ↑ |
| D2 | configuration reference generated, CI-diff-checked | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | = |
| D3 | OpenAPI snapshot + written API guide | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| D4 | `--help` complete at every CLI level | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| D5 | web UI help/about page | – | – | – | – | – | – | – | – | – | – | ✗ | ✓ | ✓ | ✓ | ↑ |
| D6 | troubleshooting guide aligned with `doctor` | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| D7 | security documentation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | = |
| D8 | backup/restore procedure, tested | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| D9 | upgrade guide from **every** released version + rollback | – | – | – | – | – | – | – | – | – | – | ~ | ~ | ~ | ~ | ↑ |
| D10 | developer docs + `CONTRIBUTING.md` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ↑ |
| D11 | documentation set consistency-reviewed (§8) and published | ✓ *(suite-wide: `docs/README.md` §11 re-run and re-dated 2026-09-07)* | ↑ |
| **Quality** |
| Q1 | every gold standard met and measured | ✗ *(suite-wide: G16 gate owed by 11 repos; G20 not enforceable; G19 not yet run, IP has no `live` job)* | ↑ |
| Q2 | coverage floors met in every repository | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ↑ |
| Q3 | performance budgets measured on the reference machine, published | **W** *(suite-wide: applications published; package tables blank until a nightly fires)* | ↑ |
| Q4 | security checklist complete; `pip-audit` + `gitleaks` clean | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ↑ |
| Q5 | accessibility checklist complete for every UI | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | = |
| Q6 | cross-repository compatibility matrix green | ✗ *(suite-wide: the job exists; four `lowest` cells red, one structurally)* | ↑ |
| **Operations** |
| O1 | migration path tested from every released version, real data | – | – | – | – | – | – | – | – | – | – | ~ | ✓ | ~ | ~ | ↑ |
| O2 | downgrade drill exercised; `SchemaAhead` names both revisions + backup dir | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| O3 | declared range resolves at **both ends** (restated by ADR-0113) | ✗ *(suite-wide: same evidence as Q6)* | ↑ |
| O4 | backup/restore tested on both dialects | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| O5 | `doctor` diagnoses every documented failure mode | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ↑ |
| O6 | degradation matrix exercised end to end, every row indexed | ~ *(suite-wide: indexed with a PC column; ~15 cells `untested`)* | ↑ |

**Tally: 22 met · 1 waived · 9 outstanding (of 32).**
Morning was 9 met · 10 partial · 9 unmet. **Sixteen items improved; none regressed.**

### Verified closures — what I checked, not what a handoff claimed

* `tests/integration/test_downgrade_and_schema_ahead.py` **exists in all four applications** (92 /
  93 / 137 / 101 lines) and each asserts `fake_future_revision in str(exc)`, `head in str(exc)`,
  `exc.details["current"]`, `exc.details["head"]`, **and** `exc.details["backup_directory"] ==
  str(_backup_directory(...))` — then restores the pre-migration backup and restarts at the older
  revision. L3's claim holds in full.
* **A schedule exists in all fourteen repositories**: `nightly.yml` with a `performance` and a
  `live` job in twelve; SweatMeter and IdeaPress schedule inside `ci.yml`. The nightly jobs skip
  honestly (`if [ -d tests/performance ]`) rather than failing on an empty marker selection.
* `diff-cover` appears in a workflow in **all fourteen**; MirrorWall's `coverage` job is now
  `--cov-fail-under=95` against its `pyproject` `fail_under = 95`.
* Every application `install-check` runs `<app> --version`, `python -m <app> --version`,
  `pip install "$(ls dist/*.whl)[postgres]"` and `pipx install dist/*.whl && <app> --version`.
  FreeWeight now declares **both** `postgresql` and `postgres` extras.
* `sha256sum dist/* > SHA256SUMS` before `softprops/action-gh-release@v2` in all four application
  `release.yml`, with `SHA256SUMS` in `files:`.
* `## Compatibility` in all four application READMEs, held by
  `tests/unit/test_readme_compatibility.py`, which parses `pyproject.toml` with `tomllib` and
  compares ranges. Read PromptCadence's: it is the right artifact, not a restatement.
* `tests/unit/test_every_command_has_help.py`, `tests/unit/test_troubleshooting_covers_doctor.py`
  and a security checklist test (`test_checklist.py` / `test_security_checklist.py`) in **all four**.
* `PromptCadence/CONTRIBUTING.md` exists; **all fourteen** repos have `CONTRIBUTING.md`,
  `SECURITY.md`, `LICENSE`, `## [Unreleased]` in the changelog (FreeWeight's restored at `0ae4ec7`)
  and a `## [<current version>]` entry.
* `pydantic-settings` is gone from all four applications' `dependencies` — ADR-0114 decision 4
  executed. (§1.1's "declared but unapproved — owed removal" paragraph is now stale; see nits.)
* `docs/.github/workflows/compatibility-matrix.yml` (8 matrix cells + a `co-install` job) and
  `docs/scripts/compatibility_matrix.py` exist; `docs/architecture/performance-results.md` exists
  and carries the reference machine's `machine_fingerprint
  f9a666d8bfe4c46bd13d17aa8e3e11e73c44b366f95f1f65d64a06cce1361b6b`, hostname `Jordan-main`.
* **Mirror integrity re-checked**: `cmp` over every `*.md` in `git ls-files` of `docs/` against all
  fourteen component copies — **12 differences, all of them the deliberately per-repo
  `docs/README.md`**. L5's new PromptCadence documents are byte-identical in the mirror.
* **All ten packages are on PyPI at exactly their `__about__.py` version**, and every published
  application version has a matching local tag. No `twine upload` in any of the fourteen
  `release.yml`; `environment:`, `id-token: write` and `pypa/gh-action-pypi-publish` in all fourteen.

---

# The nine outstanding items

---

## I5 — IdeaPress's `[telemetry]` extra is never installed by anything · **partial**

The restated item names three extras: `[postgres]`, `[postgresql]` and **IdeaPress's
`[telemetry]`**. The first two are met — `pip install "$(ls dist/*.whl)[postgres]"` is a step in all
four `install-check` jobs, and the four `db-matrix`/`postgresql-tests` jobs prove the dialect
*functions*. `grep -n telemetry IdeaPress/.github/workflows/ci.yml` returns **nothing**:
`telemetry = ["sweatmeter>=0.4,<0.5"]` is declared in `IdeaPress/pyproject.toml` and installed by no
job, ever.

**Smallest change:** two lines in IdeaPress's `install-check`, beside the `[postgres]` line —
`pip install "$(ls dist/*.whl)[telemetry]"` and `python -c "import sweatmeter"`.

---

## D1 — two package READMEs have no install or quickstart, and five status lines are stale again · **partial**

L1 rewrote nine `**Status:**` paragraphs and they were correct when written. Two things remain.

**(a) CutCtx and ToolYard were only half-fixed.** Their status lines are right, but the second
bullet of the morning's Group 1 was not closed:

| Repo | `## Install` | `pip install <pkg>` from PyPI | quickstart | `docs/README.md` |
|---|---|---|---|---|
| CutCtx | absent | absent (`pip install .` inside an acceptance script only) | absent | absent |
| ToolYard | absent | absent (same) | absent | absent |

Every other package repo has an `## Install` heading, a quickstart and a `docs/README.md` — the nine
`docs: restore this repository's own docs index` commits skipped exactly these two. `ls
py/CutCtx/docs/` returns `packages/` and nothing else.

**(b) The status lines have already rotted, seven hours later.** Nothing binds a README to
`__about__.py`, so tonight's patch cycle walked past them:

| Repo | README says | Tree at 17:10 | PyPI |
|---|---|---|---|
| FreeWeight | `1.1.0`, on PyPI | `1.1.2` | 1.1.1 |
| LoadCoach | `1.1.3` in the repository; "PyPI still…" | `1.1.5` | 1.1.4 |
| IdeaPress | `1.2.0`, on PyPI | `1.3.2` | 1.3.1 |
| PromptCadence | `1.2.0`, on PyPI | `1.3.2` | 1.3.1 |
| LoadLedger | "`0.3.0` prepared; `0.2.0` on PyPI" | `0.3.0` | **0.3.0** |

**Smallest change:** an `## Install` + five-line quickstart + `docs/README.md` for CutCtx and
ToolYard; and the artifact the morning audit already named and L1 did not build — a
`tests/unit/test_readme_states_the_version.py` in each repo, one assert that the README contains
`__version__`. Without it this row is guaranteed to be wrong again at the next release, as it is now.

---

## D5 — FreeWeight has no help/about page · **unmet for one of four**

L5 settled the standards question the right way: `ui-ux-standards.md` §12 now says "**The System
page is the suite's help/about page** (M9 item D5)" — and, in the same paragraph, "**FreeWeight has
none** — `web/routes/system.py` serves `/version` and `/system/status` as JSON only, with no
`NAV_ITEMS` entry — and owes one." Verified: `FreeWeight/src/freeweight/web/rendering.py`'s
`NAV_ITEMS` has twelve entries and none of them is System; `web/routes/system.py` has no HTML route.
The item is now unambiguously scoped rather than ambiguous — which is progress, and still ✗.

**Smallest change:** one HTML route + template + `NAV_ITEMS` entry in FreeWeight, modelled on
LoadCoach's `system/index.html`. ~40 lines.

---

## D9 — every upgrade guide is one release behind · **partial**

All four now have per-version sections and a Downgrading/Rollback section — FreeWeight gained
per-version content for the first time. The guides stop short of what is published:

| App | `docs/upgrading.md` covers | Published | Tagged tonight |
|---|---|---|---|
| FreeWeight | migration notes for 1.0.0, 1.1.0 | 1.1.1 | (1.1.2 uncommitted) |
| LoadCoach | 1.0.0 … 1.1.3 | 1.1.4 | v1.1.5 |
| IdeaPress | 0.1.x→1.0.0, 1.1.0→1.2.0, 1.2.0→1.3.0 | 1.3.1 | v1.3.2 |
| PromptCadence | 1.0.0 … 1.3.0 | 1.3.1 | v1.3.2 |

This is the same rot as D1(b) and has the same cause: the release commit does not touch the guide.

**Smallest change:** a "Behaviour changes at `<version>`" (or an explicit "no behaviour change") row
per patch, added by the release commit itself — and, to make it stick, one test per application
asserting `docs/upgrading.md` names `__version__`.

---

## Q1 — three gold standards are not met or not measured · **unmet**

G11 is now met (diff-cover in all fourteen). Three are not:

* **G16 — "a test comparing `pyproject.toml` against §1.1" — owed by eleven repositories.**
  `gold-standards` §1.1 says so itself, and I confirmed it: such a test exists only in
  `BaseAiCore/tests/test_packaging.py`, `CutCtx/tests/unit/test_packaging.py` and
  `ToolYard/tests/unit/test_boundaries.py`. ADR-0114 made the budget mechanically checkable; nothing
  yet checks it in the other eleven.
* **G19 — "nightly performance job" — exists but has never run, and IdeaPress runs only half of
  it.** IdeaPress's schedule triggers a `performance` job and **no `live` job**, while
  `IdeaPress/tests/live/` holds five files (including `test_la2_three_stage_project.py` and
  `test_loadcoach_live.py`). Packaging §5 requires both. SweatMeter's nightly targets
  `runs-on: [self-hosted, linux, gpu]` — correct, and dependent on a runner being registered.
* **G20 — "every row of the degradation matrix has a test", CI-blocking — cannot be turned on.**
  See O6.

**Smallest change:** a `live` job in IdeaPress's `ci.yml` (copy its own `performance` job, swap the
marker, add `-rs`); one `test_packaging.py` per repository comparing `dependencies` against §1.1 —
eleven near-identical files, and the ADR already fixes the expected set.

---

## Q3 — performance budgets: applications published, package tables blank · **waived in part**

`docs/architecture/performance-results.md` exists, describes the reference machine with its
`machine_fingerprint`, and publishes measured figures for the four applications: LoadCoach's nine
M5-20 numbers plus the closeout re-measurement, PromptCadence's ten spec §15 budgets, IdeaPress's
seven, and FreeWeight's LA3 serving-mode overhead. The package-level tables (§3.1, §3.4, §3.5, most
of §3.6/§3.7, all of §4) are blank, and §5 says why in the document's own words: the ten
repositories that gained a `schedule:` this morning have not had a nightly fire yet.

**Waived on this basis**, because no session can close it — the schedule must actually run. Note
that **no ADR waives it**; the waiver rests on `performance-results.md` §5 and row L4. If M9 is
declared with this open, the declaration should say so, or an ADR should record it the way ADR-0111
records podman.

---

## Q6 / O3 — the compatibility matrix has never been green, and a second blocker is behind the first · **unmet**

The job now exists (`docs/.github/workflows/compatibility-matrix.yml`, 4 apps × {lowest, highest}
plus a `co-install` job; `docs/scripts/compatibility_matrix.py` reads each application's **published**
sdist from PyPI, so a local fix does not move a cell until it publishes). What it has never been is
green.

* **`highest` × 4 — expected green.** L6 proved `promptcadence highest` directly
  (`39 passed, 99 deselected`); the other three are inferred, not measured.
* **`co-install` — should now be green.** `ideapress 1.3.1` widened `modelrack` to `>=0.7,<0.8`,
  and the operator's co-install proof at 1.1.1/1.1.4/1.3.1/1.3.1 confirms it.
* **`lowest` × 4 — red.** L6's finding (every application floored `mirrorwall>=0.2,<0.3`, and
  `mirrorwall 0.2.0`/`0.2.1` cap `setspec<0.5`) is **fixed in the tree**: all four now declare
  `mirrorwall>=0.2.2,<0.3`. But it is published only in `freeweight 1.1.1`; LoadCoach's,
  IdeaPress's and PromptCadence's fixes ride the tagged-but-unpublished 1.1.5 / 1.3.2 / 1.3.2.
* **A second, structural blocker this audit found — IdeaPress's `lowest` cell stays red even after
  those publish.** Resolved from PyPI metadata, not inferred:
  `ideapress` floors `baseaicore>=0.4.1,<0.5` and `modelrack>=0.7,<0.8`; the lowest published
  `modelrack` in that range is `0.7.0`, whose own `requires_dist` is **`baseaicore<0.5,>=0.4.2`**.
  The script pins the floor of every range explicitly, so it will ask for `baseaicore==0.4.1`
  alongside `modelrack==0.7.0` and get `ResolutionImpossible`. The `modelrack` widen that landed in
  `1.3.1` (`78c1694`) raised the ceiling without raising the `baseaicore` floor it implies. The same
  check clears the other three: FreeWeight and LoadCoach floor `baseaicore>=0.4.2`, and PromptCadence
  declares no `modelrack`.

O3 is the same property under ADR-0113's restatement and scores identically.

**Smallest change:** `baseaicore>=0.4.2,<0.5` in `IdeaPress/pyproject.toml` with a comment naming
`modelrack 0.7.0`'s own floor, recompile its `ci.lock`, and ride the next patch; then publish the
three held patches and dispatch the workflow once. The matrix goes green in the same run or names
the next conflict — which is precisely what it is for.

---

## O1 — one fixture per application, and three of them migrate nothing · **partial**

Every application now ships a released-version `.sqlite3` fixture and the three missing
`.gitignore` carve-outs were added. But L3's own §5 is candid and the tree confirms it: only
LoadCoach's fixture exercises a real upgrade path.

| App | Fixture | Fixture head | This build's head | Earlier published releases with no fixture |
|---|---|---|---|---|
| FreeWeight | `1.0.0rc1`, `1.1.0` | 0008 | 0008 | 1.0.0, 1.1.1 |
| LoadCoach | `1.0.0` | 0006 | 0014 | — |
| IdeaPress | `1.3.0` | 0009 | 0009 | **1.1.0, 1.2.0** |
| PromptCadence | `1.2.0` | 0011 | 0011 | **1.1.0, 1.3.0** |

IdeaPress's head is `0009_attempt_cache_token_classes` and PromptCadence's is
`0011_content_scrubbed_at`; a fixture captured from each application's **earliest** published
release (`1.1.0` in both cases) would exercise 0007→0009 and →0011 with real rows instead of
asserting a no-op.

**Smallest change:** capture `ideapress==1.1.0` and `promptcadence==1.1.0` fixtures the way L3
captured the others, and add them to the existing parametrized migration test. Note L3's finding
that the "< 200 KB" fixture cap in the standards is no longer achievable for any of these schemas —
that number wants correcting or deleting.

---

## O6 — the degradation matrix is indexed but not exercised · **partial**

L2 delivered exactly what the row asked: `graceful-degradation.md` has a **PromptCadence column**
(with two honest `n/a` footnotes — no machine axis, no evidence axis) and a new **§2.1 row index**
naming the test that proves each cell. That closes "every row indexed to the test that proves it".
It does not close "exercised end to end": the index itself records roughly fifteen `untested` cells
and closes with "G20 cannot be turned on until those are closed." Four conditions are untested in
every application that has them — **disk full** (all four), **database locked** (FreeWeight only),
**database migration failure** (missing in IdeaPress and PromptCadence), **incompatible API major**
(missing in FreeWeight and LoadCoach) — and IdeaPress has no machine-condition tests at all.

The one cell that is legitimately unprovable here is ToolYard's podman rung, and it is already
**waived by ADR-0111** (decisions 2–4: the ladder guarantees "the strongest tier the host can
supply", proved on docker; the podman branch stays a visible skip and a canary for the first podman
host). The index cites it correctly.

**Smallest change:** either write the ~10 missing tests (mostly small: a full-disk fake, a locked
SQLite connection, a failed migration in the two newest applications), or an ADR that scopes G20 to
the rows a hosted runner can actually produce and marks the rest the way ADR-0111 marks podman.
Do not "close" cells by asserting a row's text back at itself (ADR-0042).

---

## Nits — small, not scored, worth a line in someone's next commit

* **`gold-standards` §1.1 is stale by one day.** Its "**Declared but unapproved — owed removal:**
  all four applications also declare `pydantic-settings`" paragraph describes a state L5 ended; the
  name is gone from all four `pyproject.toml` files. One paragraph to delete.
* **`docs/README.md` §11 says "three application API documents".** L5 wrote PromptCadence's
  `api.md` the same day, making it four. The review is otherwise accurate and re-dated.
* **`outstanding-work` §5's milestone map still declares M9 "over the nine existing components"** —
  contradicting §1.1 and the restated §7. Fixed by the declaration text below.
* **FreeWeight's new both-dialects backup test skips in FreeWeight's own CI.**
  `test_backup_round_trips_or_refuses_restore_on_both_dialects` reaches PostgreSQL through
  `weightsdb.testing.temporary_postgres`, which reads `WEIGHTSDB_POSTGRES_URL`/`WEIGHTSDB_REQUIRE_POSTGRES`;
  FreeWeight's `postgresql-tests` job sets `FWTEST_*` instead, so that leg skips silently. **O4 is
  still met for FreeWeight** through its pre-existing `test_backup_on_postgresql_produces_a_pg_dump_archive`
  and `test_restore_on_postgresql_refuses_and_names_pg_restore`, which the `FWTEST_REQUIRE_POSTGRES=1`
  job does enforce — but the new test is decorative there. Two env lines in the job fix it.
* **Release notes are commit-derived.** All fourteen `release.yml` use
  `generate_release_notes: true` rather than the changelog section packaging §6 describes. R2 is
  scored met on the restated wording; if §6's stricter reading is intended, this is a `body_path:`
  change in fourteen files.

---

# If and when M9 is declared

Nothing below should be pasted while any of the nine items above is open. Once they are closed —
and the three held patches are published and one green matrix run exists — this is the text.

### For `docs/roadmap/outstanding-work.md` §1.1, appended to the section

> **M9 declared 2026-09-<DD>.** The professional delivery checklist
> ([master-roadmap §7](master-roadmap.md), restated over fourteen components on 2026-09-07 by row
> L2) is complete: all 32 boxes are met, save the package-level cells of
> [`performance-results.md`](../architecture/performance-results.md), which are blank until a
> nightly `performance` job has fired in the ten repositories that gained a schedule at row L4 —
> the document's §5 states plainly that a blank cell means "not yet measured", and no session can
> close it — and ToolYard's podman rung, waived by
> [ADR-0111](../adr/0111-the-container-rung-is-proved-on-docker-and-podman-is-not-an-exit-condition.md).
> Suite 1.0 is declared over **fourteen components at the versions they hold**: the four
> applications at `1.x` on ten `0.x` packages, deliberately and pinned, per
> [ADR-0113](../adr/0113-packages-stay-0x-at-m9-and-1-0-is-earned-per-package.md) — M9 bumps no
> package to 1.0, and each package earns its own on the criteria that record sets. The evidence is
> rows L1–L6 and their handoffs, the re-audit in `M9_REAUDIT.md`, and the first green run of the
> cross-repository compatibility matrix, which proves every application's declared range for every
> suite package resolves at **both** ends.

### For `docs/roadmap/outstanding-work.md` §5, replacing the M9 row

> | **M9** — Suite 1.0 (fourteen components) | §1.1 — audit (`M9_AUDIT.md`) + gap rows L1–L6 + re-audit (`M9_REAUDIT.md`) | **Declared 2026-09-\<DD\>:** master-roadmap §7's 32 boxes met over fourteen components and four applications, with `performance-results.md`'s package tables pending a first nightly and the podman rung waived by ADR-0111 |
