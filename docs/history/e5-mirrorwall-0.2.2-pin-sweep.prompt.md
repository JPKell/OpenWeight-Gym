# Kickoff — E5: publish `mirrorwall 0.2.2`, then sweep the `setspec` pin

**Row:** E5 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1. Read the
row in full first — it already made this row's two judgment calls (the ordering, and the LoadCoach
exception), and §0.1 below corrects three factual assumptions in it.
**Model:** **Sonnet 5 · standard**, as scheduled — overnight, run at **high**
([model-assignment §2.12](docs/roadmap/model-assignment.md)). Nothing here is invented: a pin, a
lock recompile and a gate per repository, proven once already on MirrorWall itself.
**Repositories, in this order:** `/home/jpk/ai/suite/py/MirrorWall` (release only — the code is
built), then `/home/jpk/ai/suite/PromptCadence`, `/home/jpk/ai/suite/IdeaPress`,
`/home/jpk/ai/suite/FreeWeight`, then `/home/jpk/ai/suite/docs` (the row is marked done last).
**Ships:** `mirrorwall 0.2.2` to PyPI — and **nothing else**. The three applications take a
dependency edit only: changelog under `## [Unreleased]`, **no version bump, no tag, no publish**.
**Overnight:** permitted (E5 is on none of §2.12's never-overnight list) — but see the hard stop in
§5 Gate A: the PyPI publish needs an operator, so an overnight run may legitimately end after the
tag with the sweep unstarted. That is a complete session, not a failed one.
**Not in this session:** LoadCoach's pin (it rides **H4**), any adoption of a `setspec` 0.5/0.6
payload (that is **F2** for `governance.egress_decision` and **H4** for `capability.evidence` 1.1),
and row **E6**.

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Do not re-derive these; do **confirm** the ones marked.

* **MirrorWall's widen is built, committed and green.** `py/MirrorWall` `main` at `092af6e`
  (`f8dd81a` = the pin, `092af6e` = the release prep), tree clean, **2 commits unpushed**, never
  tagged past `v0.2.1`. `src/mirrorwall/__about__.py` already says `0.2.2`; `pyproject.toml` already
  says `setspec>=0.4,<0.7`; `requirements/ci.lock` is already recompiled. **You are not writing
  MirrorWall code.** If you find yourself editing `src/`, stop and re-read the row.
* **PyPI, checked today:** `setspec` has `0.6.0, 0.5.0, 0.4.0, …`; `mirrorwall`'s latest is
  **`0.2.1`** — 0.2.2 is not published, which is the whole reason this row exists.
* **`mirrorwall` was the only cap.** `modelrack`, `weightsdb` and `sweatmeter` do not depend on
  `setspec` at all (checked: `baseaicore` only). Both `mirrorwall 0.2.0` and `0.2.1` pin
  `setspec>=0.4,<0.5` — verified from the `v0.2.0`/`v0.2.1` tags — so any lock or environment still
  holding an old `mirrorwall` re-imposes the cap no matter what a `pyproject.toml` says. That is the
  trap in §0.1 item 3.
* **Four repositories are unpushed, and E4's pushes are owed before yours**
  (`docs/history/E4_HANDOFF.md` §8): `docs` ahead 4 (`943fbe1`), `LoadCoach` ahead 1 (`5c5aa1f`),
  `PromptCadence` ahead 3 (`d57a33e`), `py/MirrorWall` ahead 2 (`092af6e`). `IdeaPress` (`88d3dfa`)
  and `FreeWeight` (`d468457`) are clean and level with `origin/main`. **Confirm** every one of these
  with `git status --short` and `git status -sb` at the start and at the end.
* **Interpreters and what is installed today** (name yours in the report — M5C-13; there is **no
  python3.12** on this host):

  | Repo | venv | `setspec` | `baseaicore` | `mirrorwall` |
  |---|---|---|---|---|
  | `PromptCadence` | 3.13.15 | 0.4.0 | 0.4.1 | 0.2.1 |
  | `IdeaPress` | 3.13.15 | 0.4.0 | 0.4.0 | 0.2.1 |
  | `FreeWeight` | 3.14.4 | **editable workspace** `py/SetSpec` | **editable workspace** `py/BaseAiCore` | 0.2.0 |
  | `py/MirrorWall` | 3.14.4 | editable workspace | editable workspace | editable self |

  **FreeWeight's venv is the one to distrust.** It imports the workspace SetSpec checkout (whose
  `dist-info` still reads `0.4.0` from install time while the code is the 0.6.0-era tree), so a green
  local FreeWeight gate proves nothing about what a consumer resolves. Prove FreeWeight from its
  recompiled `ci.lock` in a scratch venv — the same way MirrorWall's own 0.2.2 gate was proved.
* **IdeaPress's `setspec` surface is small and frozen:** `setspec.prompts` (`load_pack`,
  `PromptLibrary`, `RenderedPrompt`, `PromptNotFound`, `PromptPackInvalid`, `PromptVariableError`,
  `build_manifest`, `write_manifest`) plus `GeneratorInfo` — four files, all v1.0 payload surface
  under ADR-0009. Low risk, but it was **not** pre-verified against 0.6.0 the way FreeWeight's
  `tests/contract/test_evidence_schema.py` was. Verify it in-session; do not assume it.
* **LoadCoach's three local reds are known, are not yours, and stay:**
  `tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-full|1.1-mixed|1.1-unsupported]`
  (verified 2026-09-04: 3 failed, 855 passed). They are why LoadCoach's pin rides H4.

## 0.1 Three corrections to the row, verified — read these before you plan

The row says to move the pin *"in PromptCadence, IdeaPress and FreeWeight, regenerating each
`requirements/ci.lock` the same way"*. Two of those three repositories have no `ci.lock`:

1. **PromptCadence has no `requirements/` directory at all.** Its `ci.yml` installs `-e ".[dev]"`
   and re-resolves every run. Nothing to recompile. (Its missing lock and missing `security` job are
   already recorded as their own future row — `docs/history/D2_HANDOFF.2.md` §7, `docs/history/E4_HANDOFF.md` §9. **Do not
   build them here.**)
2. **IdeaPress has `requirements/` but no `ci.lock`** — only `release.in`/`release.lock` for the
   publish chain. Its `requirements/README.md` carries a "No `ci.lock` yet" section saying exactly
   that. Nothing to recompile.
3. **FreeWeight is the only repository with a `ci.lock` to move — and `-P setspec -P baseaicore` is
   not enough for it.** That lock currently pins `mirrorwall==0.2.0` (line 839), `setspec==0.4.0`,
   `baseaicore==0.4.0`. `mirrorwall 0.2.0` requires `setspec<0.5`, so without also upgrading
   `mirrorwall` the recompile either fails to resolve or quietly keeps `setspec 0.4.0` — the same
   silent-fallback shape the row warns about for `baseaicore`. The command is
   **`-P setspec -P baseaicore -P mirrorwall`**, and FreeWeight's own invocation
   (`requirements/README.md`) carries `--extra postgresql --unsafe-package freeweight`:

   ```bash
   pip-compile --strip-extras --extra dev --extra postgresql --generate-hashes \
       --unsafe-package freeweight -P setspec -P baseaicore -P mirrorwall \
       --output-file requirements/ci.lock pyproject.toml
   ```

   No `--upgrade`. Those three pins are the only ones that may move; say so in the handoff, and diff
   the lock to prove it.

## 0.2 The one decision this row leaves open — take it, record it

The row says all three applications go to `setspec>=0.4,<0.7`. For **PromptCadence** that
contradicts its own specification: `docs/apps/promptcadence/spec.md` §5 requires `setspec` **≥ 0.5**
(`governance.egress_decision`), and its `pyproject.toml` comment says so in as many words while
explaining why the pin could not move yet.

**Recommendation: PromptCadence goes `setspec>=0.5,<0.7`; IdeaPress and FreeWeight go
`>=0.4,<0.7` as the row says.** A floor below what a component's own spec §5 states is exactly the
kind of drift that is invisible until someone installs the wrong thing. Nothing consumes the payload
before F2, so the floor costs nothing today.

Take the other option if you can argue it better — but **record the choice and the reason in the
handoff and in the replacement pin comment**, and do not leave the stale comment behind either way.

---

## 1. Setup

```bash
cd /home/jpk/ai/suite/PromptCadence && source .venv/bin/activate && pip install -e ".[dev]"
cd /home/jpk/ai/suite/IdeaPress     && source .venv/bin/activate && pip install -e ".[dev]"
cd /home/jpk/ai/suite/FreeWeight    && source .venv/bin/activate && pip install -e ".[dev]"
```

Name each interpreter and each exact invocation in the report (M5C-13). Use the session scratchpad
for every scratch venv, database and log — **never** the repositories, never `/tmp` directly, never
the workspace root.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory, never the workspace root. Nothing at the root is versioned.
* The finish line, per repository:
  `ruff format --check . && ruff check . && mypy src tests && lint-imports && pytest -m "not live and not performance"`
  green, `CHANGELOG.md` updated under `## [Unreleased]`, **one Conventional Commit per repository**.
  `pytest-randomly` is on; a seed-only failure is a real bug.
* House method still applies to anything you write (docstring-first, `from __future__ import
  annotations`, units in names, keyword-only optionals, `mypy --strict`, line length 100) — though
  this row should produce no new source.
* **Never `git add -A`.** Stage named paths. Commit at every boundary, not at the end.
* Any workspace `docs/` edit is mirrored byte-identically into the component repo and **`cmp`-proved**.

## 3. Reading list, in this order

1. The **E5 row** of `docs/roadmap/outstanding-work.md` §1, plus §3's "E5 before F2 and H4" bullet
   and §4's "`mirrorwall 0.2.2` is prepared and waiting" bullet.
2. `py/MirrorWall/CHANGELOG.md` §`[0.2.2]` and `py/MirrorWall/requirements/README.md`
   §"Why `setspec` moved to 0.6.0 at 0.2.2" — the argument for the widen, and the exact recompile
   discipline you are copying into FreeWeight.
3. [ADR-0068](docs/adr/0068-a-post-freeze-minor-is-a-sibling-class.md), **rule 3** especially — the
   bare `…Out`/`In` classes keep meaning `1.0` with `extra="forbid"`, which is precisely why
   LoadCoach reds on 0.6.0 and why it is excluded here.
4. `docs/roadmap/adapter-roadmap.md` §4.3.
5. `E1_E2_RELEASE_RUNBOOK.md` at the workspace root — Steps 0, 6, 7, 8 are the release mechanics,
   already written down once. Step 0 (push auth) is the thing that bites first.
6. `docs/history/E4_HANDOFF.md` §8 (the owed pushes) and §9 (the open items you must not chase).

---

## 4. The shape of the work

Three gates, strictly in order. Gate B cannot start until Gate A has actually put a wheel on PyPI —
not "tagged", not "workflow running". **Published, and install-checked.**

## 5. Gate A — release `mirrorwall 0.2.2`

**A1. Push auth first** (runbook Step 0). `gh` is authenticated as `JPKell` with protocol `ssh`
while the remotes are `https`; a bare `git push` will hang on a password prompt. `gh auth setup-git`
fixes it, or run the pushes from the VSCode terminal where the askpass IPC env is set
(`FreeWeight M6 and push auth` memory). Verify with
`git -C /home/jpk/ai/suite/py/MirrorWall ls-remote origin >/dev/null && echo "auth ok"`.

**A2. Push the four repositories, in this order**, and confirm CI green on each:

```bash
cd /home/jpk/ai/suite/docs          && git push origin main   # E4's, owed
cd /home/jpk/ai/suite/LoadCoach     && git push origin main   # E4's, owed — no tag, no release
cd /home/jpk/ai/suite/PromptCadence && git push origin main   # E4's, owed
cd /home/jpk/ai/suite/py/MirrorWall && git push origin main   # this row's
```

LoadCoach's CI installs `setspec==0.4.0` from `requirements/ci.lock`, where the `1.1` goldens do not
exist — so it should be **green despite the three local reds**. If it is not, that is a finding:
write it up, and do not "fix" it here.

**A3. Tag and publish.** No TestPyPI dry run is required — Packaging and Release Standards §6 asks
for one before a package's *first* release, and `mirrorwall` published 0.2.0 and 0.2.1 already, so
trusted publishing is configured.

```bash
cd /home/jpk/ai/suite/py/MirrorWall
git tag -a v0.2.2 -m "mirrorwall 0.2.2 — setspec>=0.4,<0.7; the cap that held the suite still comes off"
git push origin v0.2.2
gh run watch -R JPKell/MirrorWall
```

The tag push triggers `release.yml`: it builds from `requirements/release.lock` with
`--require-hashes`, runs `twine check`, installs the wheel and runs the suite **on Python 3.12** in
CI, then publishes and cuts a GitHub release. **The `pypi` environment approval is the operator's**,
not yours.

**A4. Post-publish install check** (outstanding-work §4's last per-release step). Two checks, and
the second is the one that matters — it is the proof the cap is gone:

```bash
python3.13 -m venv <scratchpad>/mw-check
<scratchpad>/mw-check/bin/pip install mirrorwall==0.2.2
<scratchpad>/mw-check/bin/python -c "import mirrorwall; print(mirrorwall.__version__)"

python3.13 -m venv <scratchpad>/cap-check
<scratchpad>/cap-check/bin/pip install "mirrorwall==0.2.2" "setspec==0.6.0"
<scratchpad>/cap-check/bin/pip show setspec mirrorwall baseaicore | grep -E "^(Name|Version)"
```

Paste both outputs into the handoff.

**A5. Hard stop.** If the push, the tag or the `pypi` approval cannot complete in this session —
auth, a required reviewer, a red CI job — **stop here and write the handoff** with the release
resumable from A2. Do **not** start Gate B against an unpublished wheel, and in particular **do not
path-install or editable-install `mirrorwall` into an application** to make the sweep resolve. That
would prove the opposite of what this row exists to prove.

## 6. Gate B — the sweep, one repository at a time, one commit each

For each repository: edit the pin → reinstall → **confirm what actually resolved** → full gate →
`CHANGELOG.md` under `## [Unreleased]` → one Conventional Commit (`build(deps):` or `fix(deps):`,
matching MirrorWall's `fix(deps): setspec >=0.4,<0.7, unblocking every application`) → clean
`git status --short`. No version bumps, no tags.

The confirmation step is not optional and it is the whole risk of this row:

```bash
pip show setspec baseaicore mirrorwall | grep -E "^(Name|Version)"
```

A pin that widened but resolved to `setspec 0.4.0` looks exactly like success. Paste the resolved
versions per repository into the handoff.

**B1. PromptCadence** (`pyproject.toml:27–33`). Move the pin per §0.2 and **delete the five-line
"this pin cannot move yet" comment** — it is stale the moment 0.2.2 publishes. Replace it with one
line saying what the floor is and why. Nothing here consumes `setspec` before P6, so the gate should
be green unchanged; if it is not, that is a finding worth the handoff. No lock (§0.1 item 1).

**B2. IdeaPress** (`pyproject.toml:25`). `>=0.4,<0.7`. Its `setspec` surface is `setspec.prompts`
plus `GeneratorInfo` (§0). Run its full gate against the resolved 0.6.0 — this is the verification
the row did not do. No lock (§0.1 item 2).

**B3. FreeWeight** (`pyproject.toml:34`, keeping the existing comment block above it about
`setspec.prompts` at 0.4). `>=0.4,<0.7`, then recompile `ci.lock` with the **three** `-P` flags in
§0.1 item 3 and diff it: `setspec`, `baseaicore`, `mirrorwall` and nothing else may move. Then prove
it the way MirrorWall proved 0.2.2 — a scratch venv installed **from the recompiled lock**, not
FreeWeight's editable-workspace venv:

```bash
python3.14 -m venv <scratchpad>/fw-lock
<scratchpad>/fw-lock/bin/pip install --require-hashes -r requirements/ci.lock
<scratchpad>/fw-lock/bin/pip install -e . --no-deps
cd /home/jpk/ai/suite/FreeWeight && <scratchpad>/fw-lock/bin/python -m pytest -m "not live and not performance"
```

`tests/contract/test_evidence_schema.py` is the one to watch; the row records it as passing against
0.6.0. Report the lock-venv result **and** the ordinary venv result, and say which interpreter ran
which.

## 7. Gate C — docs

In `/home/jpk/ai/suite/docs`, one commit:

* Mark the **E5 row** done in `roadmap/outstanding-work.md` §1 in the house shape E4 used —
  `**Done 2026-09-0X** (`docs/history/E5_HANDOFF.md`; commits …)` — and add any correction this session found, so
  the next reader inherits it rather than rediscovering it. §0.1's three items belong there.
* Update §4's "**`mirrorwall 0.2.2` is prepared and waiting**" bullet to what actually happened
  (published, or where it stopped).
* If you touch a file that a component repo mirrors, mirror it and `cmp`-prove it.

---

## 8. Exit conditions — all of these, demonstrably

1. `mirrorwall 0.2.2` is installable from PyPI, and `mirrorwall==0.2.2` + `setspec==0.6.0` resolve
   together in one clean venv (§5 A4 output pasted).
2. PromptCadence, IdeaPress and FreeWeight each pin a widened `setspec`, each gate green, each with
   the **resolved** `setspec` version printed and ≥ 0.5.
3. FreeWeight's `ci.lock` moves exactly three pins, proved by diff, and its suite passes from that
   lock in a scratch venv.
4. The stale PromptCadence pin comment is gone.
5. **LoadCoach is untouched** — no pin change, no commit, still exactly three local failures if you
   run it at all (you need not).
6. Every repository clean; every mirrored docs file `cmp`-identical; the E5 row marked done.

## 9. Closing duties

1. Full gate per repository, interpreter and exact invocation named (M5C-13).
2. **`docs/history/E5_HANDOFF.md` at the workspace root**, house shape: gate results; the resolved-version table
   per repository (the point of the row); the §0.2 floor decision with its reason; the commits and
   the tag; what the next row must not relitigate (**H4 owns LoadCoach's pin and the
   `CapabilityEvidenceV1_1Out` adoption; F2 owns `governance.egress_decision`**); operator steps for
   the morning; anything the E5 row said that turned out not to be true.
3. Record any **model deviation** from the scheduled Sonnet 5 · standard for
   [model-assignment §3.5](docs/roadmap/model-assignment.md).

## 10. Stop rules

* **Do not move LoadCoach's `setspec` pin**, and do not "fix" its three evidence-golden failures.
  Both are H4's, with the adoption that makes them pass. Moving the pin here turns a local-only red
  into a CI red.
* **Do not adopt any new payload.** No `governance.egress_decision` (F2), no
  `CapabilityEvidenceV1_1Out`/`In` (H4), no `EvidenceBundleV1_1` (H4). This row widens a range; it
  imports nothing new.
* **Do not touch MirrorWall's source, tests or version.** 0.2.2 is built and green; this row
  releases it.
* **Do not build PromptCadence's `ci.lock` or its `security` job**, and do not add IdeaPress's
  missing `ci.lock`. Both are recorded as their own future work.
* **No `--upgrade` on any recompile**, and no pin moves beyond the three named ones.
* **Do not publish anything except `mirrorwall 0.2.2`**, and do not bump or tag any application.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty
  at a boundary.
* If you are blocked — most likely at the `pypi` approval — **stop and write the handoff.** A
  released MirrorWall with an honest "sweep not started, resume at §6" is a good session.

## 11. If you finish with capacity left

Do **not** start F2, H4 or E6. In priority order, read-only: (a) confirm from the published wheels
which `setspec` version each application would resolve at a fresh `pip install <app>` and record the
matrix in the handoff; (b) write an **H4 readiness note** — the exact three LoadCoach tests, the
bare-class rule from ADR-0068 that makes them fail, and what the adoption has to change; (c) write
an **F2 readiness note** naming where `governance.egress_decision` would enter PromptCadence. Notes,
not code.
