# L6 handoff — the two suite-wide jobs

**Row:** L6 (Sonnet 5 · high), `docs/roadmap/outstanding-work.md` §1: "The two suite-wide jobs" (M9
audit Group 6), gated on L2 (the package-1.0 / ADR-0113 decision) and L4 (nightly performance jobs
in all fourteen repositories).
**Component:** `docs` only (`main`). Nothing in any application or package repo was touched —
the row's own text scopes the commit to "docs by name," and the finding in §4 below belongs to a
follow-up row, not to this one.
**Read first:** `M9_AUDIT.md` Group 6, `docs/standards/packaging-and-release-standards.md` §7,
`docs/architecture/performance-targets.md`, ADR-0113.

---

## 1. What was built

**Part 1 — the compatibility matrix.**

* `docs/.github/workflows/compatibility-matrix.yml` — nightly (`cron: "30 4 * * *"`, offset from
  ModelRack's/FreeWeight's `nightly.yml`) + `workflow_dispatch`. Two jobs:
  * `matrix`: a `strategy.matrix` over `app: [freeweight, loadcoach, ideapress, promptcadence]` ×
    `bound: [lowest, highest]` (8 cells), each running `scripts/compatibility_matrix.py <app>
    <bound>`. `fail-fast: false` so one red cell doesn't hide the other seven.
  * `co-install`: a fifth, separate job — installs all four applications' latest PyPI releases
    into one venv with **no** suite-package pins, proving the composition model (LoadCoach reading
    FreeWeight evidence, IdeaPress and PromptCadence routing through LoadCoach) can share one
    Python environment. Commented in the workflow as **known failing today** — see §4.
  * Validated with `python -c "import yaml; yaml.safe_load(open(p))"` (can't run Actions locally).
* `docs/scripts/compatibility_matrix.py` — stdlib + `pip` subprocess only (no `packaging`, no
  `requests`), Python ≥ 3.12, runnable standalone. For one `(app, bound)` cell it:
  1. Reads the application's current version and every published version of the ten suite
     packages from the PyPI JSON API (`urllib.request`).
  2. Downloads the application's sdist (`pip download --no-deps --no-binary :all:
     <app>==<version>`) and reads its shipped `pyproject.toml` with `tomllib` — never a local
     checkout, so the pins reflect what a real `pip install` resolves against.
  3. For each suite package the application's `[project.dependencies]` names, picks the lowest or
     highest **published** version its declared range admits (own version-tuple comparator; a
     `ponytail:` comment names the PEP 440 pre/post/dev gap this leaves and the upgrade path).
  4. Builds a clean venv, installs `<app>==<version>` plus every resolved pin in one `pip install`
     call, runs `<app> --version`.
  5. Checks the sdist for `tests/contract/` or `tests/e2e/` — all four applications ship both
     today, so the "clone the tag" fallback the row's instructions describe is written into the
     workflow's comments but has never fired; if it ever needs to, the script's `tests_in_sdist`
     field is exactly the signal a future change would branch on.
  6. If tests ship, installs `<app>[dev]==<version>` (not a bare `pytest`, so the run gets
     whatever the test suite itself needs — this caught a real gap, see §3) and runs `pytest -m
     "contract or e2e"` against only `tests/contract`/`tests/e2e` (not the whole `tests/` tree —
     also a real gap, see §3), from the extracted sdist, against the installed wheel.
  7. A cell that cannot even be pinned (no published version satisfies a declared range) is
     reported `ok: false` with the unsatisfiable range named — never silently skipped. Exit code
     is 1 on any failure, 0 only when install and (where shipped) tests both pass.
* `docs/standards/packaging-and-release-standards.md` §7 — one paragraph naming both files, why
  the workflow lives in `docs` rather than any component, and how to read a red run (the job
  summary's `Detail` column names either the unsatisfiable range or the first pip conflict).
  `packaging-and-release-standards.md` is not one of the documents mirrored into the fourteen
  component repos (checked: no `docs/standards/` directory exists under any of them), so no mirror
  commit was needed for this edit.

**Part 2 — `docs/architecture/performance-results.md`** (new file). Reference machine captured via
`py/SweatMeter/.venv/bin/python3 -c "from sweatmeter import TelemetryCollector; ...
.machine_profile()"` (sweatmeter 0.4.0) — same physical box `performance-targets.md` §1 describes
(RTX 5060 Ti, 16 GiB), `machine_fingerprint
f9a666d8bfe4c46bd13d17aa8e3e11e73c44b366f95f1f65d64a06cce1361b6b`, hostname `Jordan-main`, AMD
Ryzen 5 7600X (6c/12t), 32 GiB RAM. One table per `performance-targets.md` §3.1–3.8 subject plus §4
memory, each with the budget beside an empty `Measured` column, and a `Measured` cell filled
wherever a handoff already had the number (never invented):

* LoadCoach — all nine `M4_HANDOFF.md` M5-20 figures (enqueue 1.8 ms, dispatch 17 ms, routing warm
  16 ms / cold 19 ms, execution overhead 3 ms, streamed-chunk latency 0.06 ms, cancellation queued
  0.9 ms / executing 53 ms, idle poll 0.32 %) plus the closeout re-measurement (routing 15.1 ms
  median / 32.0 ms max, SSE p95 ≈ 1.29 ms).
* PromptCadence — all ten spec §15 budgets from `I2_HANDOFF.md` §8 (13.45 ms median per-turn
  overhead, the SSE-poll finding and its 1.40 ms fix, etc.), reproduced verbatim.
* IdeaPress — all seven spec §15 budgets from `M8_HANDOFF.md` (stage orchestration 0.1 ms →
  headroom table).
- FreeWeight — the LA3 serving-mode overhead (+0.9 % / H4, confirmatory +0.5 % / H5), which isn't a
  named row in `performance-targets.md`'s own table but is the arc's own revisit trigger.

Everything else (most of §3.1, all of §3.4/§3.5, most of §3.6/§3.7, all of §4) is still blank —
`grep -rn "ms median|overhead" docs/history/*.md` found nothing further, and row L4 only just added
the nightly schedule that would produce them. §5 states plainly that a blank cell means "not yet
measured," not zero or passing, mirroring `Unsupported`'s convention (ADR-0016) for a document
rather than a type.

---

## 2. Local proof — `promptcadence lowest` and `promptcadence highest`

Run as the row asked, from `docs/`, `python3.13 scripts/compatibility_matrix.py promptcadence
<bound>`, network access to `pypi.org` confirmed first.

### `promptcadence highest` — **passes**

```json
{
  "app": "promptcadence", "bound": "highest", "app_version": "1.3.0",
  "pins": {
    "baseaicore": "baseaicore==0.4.2", "setspec": "setspec==0.6.0",
    "weightsdb": "weightsdb==0.2.1", "mirrorwall": "mirrorwall==0.2.2",
    "toolyard": "toolyard==0.1.1", "cutctx": "cutctx==0.1.0",
    "loadledger": "loadledger[sql]==0.3.0", "commissioner": "commissioner[sql]==0.1.1"
  },
  "tests_in_sdist": true,
  "install": { "returncode": 0, "stderr_tail": "" },
  "version_check": { "returncode": 0, "stdout": "promptcadence 1.3.0 (api v1)" },
  "tests": { "returncode": 0, "tail": "39 passed, 99 deselected, 2 warnings in 0.48s" },
  "ok": true, "summary": "tests passed (pytest exit 0)"
}
```

The first attempt at this cell (before the two mechanics fixes named in §3) reported `pytest exit
2` on two collection errors under a bare `pytest` install — see §3.

### `promptcadence lowest` — **fails** (a real finding, not a script defect)

```json
{
  "app": "promptcadence", "bound": "lowest", "app_version": "1.3.0",
  "pins": {
    "baseaicore": "baseaicore==0.4.1", "setspec": "setspec==0.5.0",
    "weightsdb": "weightsdb==0.2.0", "mirrorwall": "mirrorwall==0.2.0",
    "toolyard": "toolyard==0.1.1", "cutctx": "cutctx==0.1.0",
    "loadledger": "loadledger[sql]==0.3.0", "commissioner": "commissioner[sql]==0.1.0"
  },
  "tests_in_sdist": true,
  "install": {
    "returncode": 1,
    "stderr_tail": "ERROR: Cannot install mirrorwall==0.2.0, promptcadence and setspec==0.5.0 because these package versions have conflicting dependencies.\nERROR: ResolutionImpossible: ..."
  },
  "ok": false,
  "summary": "INSTALL FAILED: ERROR: ResolutionImpossible: ..."
}
```

Exit code: `1` (confirmed directly, not through a piped `$?`).

---

## 3. Two real mechanics bugs the local run found and fixed

Both are in `scripts/compatibility_matrix.py`, both were caught by actually running a cell rather
than reading the plan:

1. **A bare `pip install pytest` is not enough.** `promptcadence[dev]` pulls in `respx`, which
   several `tests/unit/*` files import; without it, `pytest -m "contract or e2e"` still tries to
   *collect* the whole `tests/` tree (marker filtering happens after collection) and 39
   `tests/unit` files fail to import, aborting the run with "39 errors during collection" before a
   single contract/e2e test executes. Fixed by installing `<app>[dev]==<version>` in the same `pip
   install` call as the suite-package pins (not a second, separate one — a second call could have
   silently re-resolved something already pinned).
2. **Point pytest at `tests/contract` and `tests/e2e` explicitly**, not the whole `tests/` tree,
   even with `[dev]` installed — belt-and-suspenders against exactly the collection-abort failure
   mode in (1) for any future application whose `tests/unit` needs something `[dev]` doesn't cover.

Neither bug affected the workflow's design, only the script's first draft; both are now recorded
as the "why" in the script's own comments in case a future edit re-introduces either shortcut.

---

## 4. What the matrix will report red on its first run, and why

**Five of nine jobs are expected red on day one — four of them a new finding this row surfaced,
not the one the row's own text named.**

* **`co-install` — red, as predicted by the row's kickoff.** `ideapress` 1.3.0 (the version on
  PyPI right now) pins `modelrack>=0.5,<0.6`; `freeweight` 1.1.0 and `loadcoach` 1.1.3 pin
  `modelrack>=0.7,<0.8`. No single `modelrack` version satisfies both, so `pip install freeweight
  loadcoach ideapress promptcadence` into one venv is `ResolutionImpossible`. IdeaPress's own
  `pyproject.toml` already carries the fix locally as an **uncommitted** change (widened to
  `modelrack>=0.7,<0.8`, comment-dated 2026-09-07, "1.3.1") — found sitting in the IdeaPress
  working tree while gathering pins for this row, untouched here per this row's own instructions.
  This job goes green the day `ideapress 1.3.1` publishes, with no workflow change.

* **All four `<app> / lowest` cells — red, and this is the row's real finding.** Every
  application declares `mirrorwall>=0.2,<0.3`. The lowest version that range admits, **`mirrorwall
  0.2.0`, still pins `setspec>=0.4,<0.5`** — and so, confirmed by downloading its sdist directly,
  does **`mirrorwall 0.2.1`**. Every application's own `setspec` floor is `>=0.5` (LoadCoach,
  IdeaPress, PromptCadence) or `>=0.6` (FreeWeight) — none of which `mirrorwall<0.5`'s cap admits.
  Only **`mirrorwall 0.2.2`** widens its own `setspec` pin to `>=0.4,<0.7`, wide enough for every
  application's floor. Verified by running all four `lowest` cells directly (not inferred):
  `freeweight`, `loadcoach`, `ideapress` and `promptcadence` each fail with the identical
  `ResolutionImpossible` naming `mirrorwall==0.2.0` and their own `setspec` pin. **No application
  can actually install at its own declared floor today** — the floor is a written number nothing
  has ever resolved. This is exactly the failure mode ADR-0113 and packaging §7 built this matrix
  to surface, and it is more urgent than the already-known `modelrack` conflict above: it blocks
  every application's *own* lowest cell, not just the four co-installing. **The fix belongs to a
  follow-up row, not this one** (this row's scope is the docs-repo workflow, per its own text):
  raise `mirrorwall>=0.2.2,<0.3` in all four applications' `pyproject.toml`, recompile each
  `ci.lock`, and confirm the four `lowest` cells go green.

* **The four `<app> / highest` cells — expected green.** Proven directly for `promptcadence`
  (§2); the other three were not re-run in full (network/time), but their `highest` pins resolve
  to each package's actual latest release — the same combination each application's own CI already
  installs today — so there is no structural reason for them to differ. Flagging this as inferred,
  not measured, per the standing instruction against invented numbers.

---

## 5. Gate

This row touches no application or package code, so there is no `ruff`/`mypy`/`pytest` gate to
run — the docs repo carries no such gate by design (CLAUDE.md: "it has no CI of its own to slow").
Verification here is: YAML validated, the script `py_compile`s clean, and both requested cells
(plus, for the finding in §4, four more `lowest` cells and no additional `highest` cells) were
actually executed against live PyPI, not simulated.

`git status --short` in `docs` at the end of this row:

```text
 M standards/packaging-and-release-standards.md
?? .github/
?? architecture/performance-results.md
?? history/L6_HANDOFF.md
?? scripts/
```

(before the commit below). No other repository was modified; IdeaPress's pre-existing uncommitted
`README.md`/`pyproject.toml`/`requirements/ci.lock` changes (the in-progress 1.3.1 prep, §4) were
read but not touched, per CLAUDE.md's working-tree-integrity rule.
