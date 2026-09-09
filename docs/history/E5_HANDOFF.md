# E5 Handoff — `mirrorwall 0.2.2` released to the tag; the pin sweep is NOT started

**Row:** E5 of `docs/roadmap/outstanding-work.md` §1.
**Session date:** 2026-09-04.
**Outcome:** **Gate A stopped at A5, by design and by operator instruction.** MirrorWall `main` and
`v0.2.2` are pushed and CI-green; the Release workflow is parked on the `pypi` environment
approval, which is the operator's. Gate B (the sweep) and Gate C (docs) were **not started** —
correctly, because §5 A5 and §10 both forbid sweeping against an unpublished wheel.
Per the row's own definition this is a complete session, not a failed one.

**Model deviation (model-assignment §3.5):** scheduled **Sonnet 5 · standard**; this session ran on
**Opus 5**. Record it. Nothing about the work depended on the larger model — the row was as
mechanical as advertised.

---

## 1. What actually shipped

| Thing | State |
|---|---|
| `py/MirrorWall` `main` → `origin/main` | **Pushed**, `6d50c3f..092af6e` |
| MirrorWall CI at `092af6e` | **green** (run `33861287196`; format, lint, boundaries, security, build, install-check, tests, 3.14 early warning) |
| Tag `v0.2.2` | **created and pushed** (annotated, message per the kickoff) |
| Release workflow | **WAITING on the `pypi` environment** — two runs, see §3 |
| `mirrorwall 0.2.2` on PyPI | **NOT published.** Latest on PyPI is still `0.2.1` |
| A4 post-publish install checks | **not run** — there is nothing to install yet |
| PromptCadence / IdeaPress / FreeWeight pins | **untouched**, still `setspec>=0.4,<0.5` |
| LoadCoach | **untouched**, as required (its pin rides H4) |
| `docs` E5 row | **not marked done** — the row is not done |

**No commits were made in this session.** Every repository is clean and level with `origin/main`
(§6 below). The only mutation to the machine outside git is the credential-helper fix in §2.

---

## 2. Correction 1 — push auth was genuinely broken, and the fix is now permanent

§5 A1 was right that this bites first, but its verification command is **not sufficient**:

```
git -C py/MirrorWall ls-remote origin >/dev/null && echo "auth ok"   # printed "auth ok"
```

…and a push still failed. `ls-remote` over `https` succeeds anonymously on a public repo, so it
proves read access, not push. The real probe is a dry-run push:

```
$ GIT_TERMINAL_PROMPT=0 git push --dry-run origin main
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

There was **no** credential helper configured at any scope and **no** askpass/`GH_TOKEN` in the
environment. Fixed with the sanctioned command:

```
$ gh auth setup-git
$ git config --global --get-all credential."https://github.com".helper
!/usr/bin/gh auth git-credential
```

After which `git push --dry-run origin main` reported `6d50c3f..092af6e  main -> main`.

**This is a persistent change to the global git config** and it makes every future row's pushes
work without the VSCode askpass IPC env. It supersedes the workaround in the
`FreeWeight M6 and push auth` memory. Use the dry-run probe, not `ls-remote`, in future kickoffs.

## 3. Correction 2 — the tag push fired **two** identical Release runs

```
Release  waiting  v0.2.2  id=33861437358   created 2026-09-04T10:04:18Z
Release  waiting  v0.2.2  id=33861435896   created 2026-09-04T10:04:17Z
```

Both are `event=push`, both on tag `v0.2.2`, one second apart, both with `publish-testpypi` correctly
skipped (it is `workflow_dispatch`-only) and both with the `release` job `waiting`:

```
$ gh api repos/JPKell/MirrorWall/actions/runs/<id>/pending_deployments
env=pypi  approved=true  reviewers=JPKell  wait=0      # identical for both runs
```

**Approve exactly ONE.** Both publish to the same PyPI project through trusted publishing; the
second to reach `twine upload` will fail on *file already exists*. That failure would be cosmetic —
the wheel would already be on PyPI — but it leaves a red Release run against `v0.2.2` in the history
for no reason.

I did not diagnose the duplicate's cause (a single `git push origin v0.2.2`, one ref, two runs — it
looks like a GitHub-side double-delivery of the push event rather than anything in `release.yml`,
whose trigger is a plain `push: tags: ["v*.*.*"]` plus `workflow_dispatch`). If it recurs on the next
tag it is worth its own row.

## 4. Correction 3 — E4's three owed pushes were **already done** before this session

`docs/history/E4_HANDOFF.md` §8 and the kickoff §0 both list four unpushed repositories. After `git fetch` on
each, only MirrorWall was actually ahead. The kickoff's SHAs are stale:

| Repo | Kickoff said | Actually found | State |
|---|---|---|---|
| `docs` | ahead 4, `943fbe1` | `6a6bc09` | level with `origin/main` |
| `LoadCoach` | ahead 1, `5c5aa1f` | `5c5aa1f` | level with `origin/main` |
| `PromptCadence` | ahead 3, `d57a33e` | `5247a83` | level with `origin/main` |
| `py/MirrorWall` | ahead 2, `092af6e` | `092af6e` | **was** ahead 2 — pushed by this session |

So §5 A2's first three `git push` lines were no-ops. CI on the already-pushed heads, checked:

```
LoadCoach      CI completed success 5c5aa1f     <-- green DESPITE the three local reds, as predicted
PromptCadence  CI completed success 5247a83
docs           (no workflows configured)
```

**The row's prediction about LoadCoach held exactly.** Its CI installs `setspec==0.4.0` from
`requirements/ci.lock`, where the `1.1` goldens do not exist, so the three local
`test_evidence_import.py` failures are invisible to CI. Nothing to write up.

## 5. The three §0.1 corrections are all confirmed on disk — carry them forward verbatim

1. **PromptCadence has no `requirements/` directory.** `ls` → `No such file or directory`. Nothing
   to recompile. Do not build it here (its missing lock and `security` job are their own row).
2. **IdeaPress has `requirements/` but no `ci.lock`** — only `.gitkeep`, `README.md`, `release.in`,
   `release.lock`. Nothing to recompile.
3. **FreeWeight's `ci.lock` needs three `-P` flags, not two.** Verified line numbers:
   `baseaicore==0.4.0` (line 97), `mirrorwall==0.2.0` (line 839), `setspec==0.4.0` (line 1390).
   `mirrorwall 0.2.0` requires `setspec<0.5`, so `-P setspec -P baseaicore` alone either fails to
   resolve or silently keeps `setspec 0.4.0`. The command stands exactly as §0.1 item 3 wrote it.

## 6. Repository state at session end — all clean, all level

```
docs           dirty=0  ## main...origin/main  6a6bc09
LoadCoach      dirty=0  ## main...origin/main  5c5aa1f
PromptCadence  dirty=0  ## main...origin/main  5247a83
IdeaPress      dirty=0  ## main...origin/main  88d3dfa
FreeWeight     dirty=0  ## main...origin/main  d468457
py/MirrorWall  dirty=0  ## main...origin/main  092af6e   (+ tag v0.2.2 pushed)
```

## 7. Resolved versions as of session end (the pre-sweep baseline)

Nothing moved, so this is still the kickoff's §0 table — **confirmed**, not assumed. It is the
"before" column the next session's "after" must be diffed against.

| Repo | Interpreter | `setspec` | `baseaicore` | `mirrorwall` |
|---|---|---|---|---|
| `PromptCadence` | 3.13.15 | 0.4.0 | 0.4.1 | 0.2.1 |
| `IdeaPress` | 3.13.15 | 0.4.0 | 0.4.0 | 0.2.1 |
| `FreeWeight` | 3.14.4 | 0.4.0 *(editable `py/SetSpec`)* | 0.4.0 *(editable `py/BaseAiCore`)* | 0.2.0 |
| `py/MirrorWall` | 3.14.4 | 0.4.0 *(editable)* | 0.4.0 *(editable)* | 0.2.1 *(editable self)* |

`pip show` confirms FreeWeight's and MirrorWall's `setspec`/`baseaicore` are editable installs of
the workspace checkouts whose `dist-info` still reads `0.4.0`. **The kickoff's warning is correct
and load-bearing: a green local FreeWeight gate proves nothing about what a consumer resolves.**
Prove FreeWeight from the recompiled `ci.lock` in a scratch venv, per §6 B3.

There is **no `python3.12` on this host** — confirmed. CI covers 3.12; local gates cannot.

## 8. Operator steps for the morning — in order

1. **Approve exactly one** `pypi` deployment: <https://github.com/JPKell/MirrorWall/actions/runs/33861437358>
   or from the CLI:

   ```bash
   gh api -X POST repos/JPKell/MirrorWall/actions/runs/33861437358/pending_deployments \
       -F 'environment_ids[]=20861840097' -f state=approved -f comment='mirrorwall 0.2.2 (E5)'
   ```
2. **Cancel the other:** `gh run cancel 33861435896 -R JPKell/MirrorWall`.
3. Watch it green: `gh run watch 33861437358 -R JPKell/MirrorWall --exit-status`. It builds from
   `requirements/release.lock` with `--require-hashes`, runs `twine check`, installs the wheel and
   runs the suite on **Python 3.12**, then publishes and cuts the GitHub release.
4. Confirm PyPI shows `0.2.2`, then hand the next session §9.

## 9. Resuming — the next session starts at §5 A4, not at A2

Everything before A4 is done. The resume sequence is:

* **A4** — the two install checks, verbatim from the kickoff (`mw-check`, then the `cap-check` venv
  that installs `mirrorwall==0.2.2` **with** `setspec==0.6.0`; the second is the proof the cap is
  gone). Paste both outputs.
* **Gate B** — the sweep, unchanged, one repository and one Conventional Commit each, with the
  `pip show setspec baseaicore mirrorwall` confirmation per repository. §0.1's three corrections
  above are confirmed; use them.
* **Gate C** — mark the E5 row done in `roadmap/outstanding-work.md` §1, update §4's
  "`mirrorwall 0.2.2` is prepared and waiting" bullet, and fold §2–§5 of this handoff into the row
  so the next reader inherits them. Mirror and `cmp`-prove anything a component repo copies.

### The §0.2 floor decision — taken, not yet applied

**PromptCadence goes `setspec>=0.5,<0.7`; IdeaPress and FreeWeight go `>=0.4,<0.7`.** I endorse the
kickoff's recommendation and it should be applied as written. The reason to record in the
replacement pin comment: `docs/apps/promptcadence/spec.md` §5 requires `setspec` ≥ 0.5 for
`governance.egress_decision`, and a floor below a component's own stated spec is drift that stays
invisible until someone installs the wrong thing. Nothing consumes the payload before P6/F2, so the
higher floor costs nothing today. The stale five-line "this pin cannot move yet" comment at
`PromptCadence/pyproject.toml:27–33` must be **deleted**, not amended — it is false the moment
0.2.2 publishes. It currently reads, in part, "mirrorwall 0.2.1 requires setspec>=0.4,<0.5, so >=0.6
makes the environment unresolvable (verified in C4)"; replace it with one line naming the 0.5 floor
and the spec §5 reason.

## 10. What the next row must not relitigate

* **H4 owns LoadCoach's `setspec` pin** and the `CapabilityEvidenceV1_1Out`/`In` adoption. The three
  local reds are
  `tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-full|1.1-mixed|1.1-unsupported]`.
  They fail because ADR-0068 **rule 3** — "a bare name keeps the version it was frozen at";
  `CapabilityEvidenceOut`/`In` mean `1.0` permanently, with `extra="forbid"` — so validating the new
  `1.1` goldens against the bare class rejects the added field. Adopting the explicit `V1_1` classes
  is the fix, and it is H4's import change. Moving LoadCoach's pin without it turns a local-only red
  into a CI red.
* **F2 owns `governance.egress_decision`** (setspec 0.5) and where it enters PromptCadence.
* **E5 adopts no payload.** It widens a range and imports nothing new.
* **Do not** build PromptCadence's `ci.lock` or `security` job, and do not add IdeaPress's missing
  `ci.lock`. Both are recorded as their own future work (`docs/history/D2_HANDOFF.2.md` §7, `docs/history/E4_HANDOFF.md` §9).

## 11. Things the E5 row said that turned out not to be true

1. E4's owed pushes for `docs`, `LoadCoach` and `PromptCadence` were **already done**; the SHAs in
   §0 and in `docs/history/E4_HANDOFF.md` §8 are stale. Only MirrorWall was ahead. (§4)
2. The A1 auth probe `ls-remote origin` **passes on a repo that cannot be pushed to**. Use
   `git push --dry-run`. (§2)
3. Neither the row nor the kickoff anticipated the **duplicate Release run** on a single tag push.
   Approve one, cancel the other. (§3)

Everything else in the kickoff — MirrorWall's prepared state, the interpreter table, the three
`ci.lock` corrections, the LoadCoach-CI-stays-green prediction — was accurate.
