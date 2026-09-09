# B3 Handoff — Commissioner 0.1.0 (Phase 1)

**Row:** B3 of `docs/roadmap/outstanding-work.md` §1. **Repository:** `py/Commissioner`.
**Status:** Complete through the gate; not tagged, not published (Phase 1 never publishes — `0.1.0`
ships at the end of Phase 2, row E3). Working tree clean; `main` has five commits, none pushed.

---

## 1. Precondition check — and a correction to the kickoff's own assumption

Both preconditions named in the kickoff were checked before any code was written.

* `baseaicore 0.4.1` — **on PyPI at the start.** `pip index versions baseaicore` listed
  `0.4.1, 0.4.0`. No issue.
* `setspec 0.5.0` — **initially appeared missing.** `pip index versions setspec` (and a fresh-venv
  install) returned only `0.4.0, 0.3.0, 0.2.0`, matching `docs/history/B1_HANDOFF.md`'s own statement that B1
  left SetSpec "complete through the gate; not tagged, not published." I stopped and reported this
  to the user rather than working around it, exactly as the kickoff's stop rule required.

  The user replied "Its ready to go" and pointed at `docs/history/B1_HANDOFF.md`'s tag/push snippet. Investigation
  found `py/SetSpec`'s `main` and the `v0.5.0` tag were **already pushed to `origin`**
  (`git ls-remote` matched local `HEAD`), and GitHub's Release workflow (trusted-publisher OIDC,
  no manual approval gate — `environment: pypi` did not, in practice, require a click) had already
  run to completion (`workflow_dispatch` run `33688726485`, `conclusion: success`,
  `2026-09-02T22:07:42Z`). My first `pip index` check had simply hit a stale local/PyPI-cache
  response; `pip install --no-cache-dir setspec==0.5.0` and the PyPI JSON API both confirmed `0.5.0`
  is live. Re-verified clean in a **fresh** virtualenv before writing any Commissioner code:

  ```bash
  python3.14 -m venv /tmp/setspec-0.5.0-check && source /tmp/setspec-0.5.0-check/bin/activate
  pip install --no-cache-dir "setspec==0.5.0" "baseaicore==0.4.1"
  python -c "from setspec.governance.v1 import GovernanceEgressDecisionOut; \
             from setspec.model.v1 import AdapterManifestOut; \
             from setspec.capability.v1 import CapabilityEvidenceV1_1Out; \
             from baseaicore import DataClassification; print('ok')"
  # -> ok
  ```

  **Correction to note for future rows:** if `pip index versions` disagrees with what a handoff
  doc says was just published, retry with `--no-cache-dir` and check the PyPI JSON API
  (`https://pypi.org/pypi/<name>/json`) before concluding the precondition is genuinely unmet —
  the index can lag by well under a minute. This row's first read was wrong; the second was right.

## 2. Gate results

Interpreter: `py/Commissioner/.venv/bin/python`, **Python 3.13.15** (matches SetSpec's own interpreter
this session; 3.12 is not installed on this machine — `python3.12` is absent, only `python3.13` and
`python3.14`. `pyproject.toml`'s `requires-python = ">=3.12"` and the CI matrix cover 3.12 even
though it wasn't the one run locally).

```bash
cd py/Commissioner
source .venv/bin/activate
ruff format --check .        # 17 files already formatted
ruff check .                 # []  (clean)
mypy src tests                # Success: no issues found
lint-imports                  # Contracts: 3 kept, 0 broken
pytest -m "not live and not performance"        # 68 passed
pytest --cov --cov-report=term-missing          # 100.00% (floor 95%)
```

Also verified beyond the stated gate, matching M5C-13 discipline and the CI jobs this row's
workflow files declare:

```bash
# ci.lock installs with hashes and the built package imports and passes tests from it
pip install --no-cache-dir --require-hashes -r requirements/ci.lock
pip install --no-cache-dir . --no-deps && pytest -m "not live and not performance"  # 68 passed

# release chain: install, build, twine-check, install the built wheel standalone
pip install --no-cache-dir --require-hashes -r requirements/release.lock
python -m build --no-isolation && twine check dist/*      # PASSED, PASSED
pip install dist/*.whl && python -c "import commissioner"     # ok

# pip-audit clean on both locks
pip-audit --require-hashes -r requirements/ci.lock          # No known vulnerabilities found
pip-audit --require-hashes -r requirements/release.lock     # No known vulnerabilities found
```

Lockfiles generated with **pip-tools 7.6.1** (matches the version the sibling repos' locks were
generated with), resolved on Python 3.13.15.

## 3. Public surface as built, against spec §7

Built exactly as specified, with two documented decisions where the spec's pseudocode left a gap:

```python
# commissioner.types
EgressTarget(name, remote, max_data_classification=None, provider_kind=None)
EgressRequest(run_id, source_ref, data_classification, target, requested_at=None)
class Verdict(StrEnum): APPROVED, DENIED, VIOLATION
EgressDecision(decision_id, request, verdict, reason, policy_name, policy_version, decided_at)
    .to_payload() -> GovernanceEgressDecisionOut          # typed Any at the signature — see §5
    @classmethod .from_payload(payload) -> EgressDecision  # payload: Any — see §5

# commissioner.policy
class EgressPolicy(Protocol): name: str; version: str; def evaluate(request) -> EgressDecision
class OrderedClassificationPolicy:
    def __init__(self, *, clock: Clock, randomness_source: RandomnessSource | None = None)
    def evaluate(self, request: EgressRequest) -> EgressDecision

# commissioner.errors
class CommissionerError(SuiteError): code = "COMMISSIONER_ERROR"
class StoreFailure(CommissionerError): code = "EGRESS_STORE_FAILURE"   # unused until Phase 2
```

All four dataclasses/`Verdict` are exactly as spec §7 lists them. Both deviations:

1. **`OrderedClassificationPolicy(clock=..., randomness_source=None)`**, not the bare
   `OrderedClassificationPolicy()` spec §7's pseudocode shows. The standing preamble ("injected
   clock and injected id generator — the determinism goldens depend on both") and development
   plan's "Determinism goldens (injected ids and clock)" test requirement both demand this; the
   bare-parens form in spec §7 reads as elided constructor detail, not a literal no-args signature.
   `clock` is required (no default), matching `LoadLedger.InMemoryLedger`'s own precedent — a
   policy that read the system clock directly could not produce a reproducible decision.
   `randomness_source` is optional and forwarded straight to an internal
   `baseaicore.UlidGenerator`, exactly BaseAiCore's own documented pattern for reproducible IDs in
   tests ("construct their own with a frozen clock and a seeded randomness source").
2. **No cross-field validator anywhere** enforcing "approved implies a declared ceiling," on either
   the payload (SetSpec's own choice, B1_HANDOFF §5c) or on `EgressDecision`/`EgressTarget` here.
   A remote `EgressTarget` with `max_data_classification=None` is legitimately constructible —
   ADR-0054 rule 3 requires the fail-closed case to be *representable*, and baking the shipped
   policy's opinion into the value object would reject a decision from any other legitimate
   `EgressPolicy` implementation. Explicitly tested
   (`test_a_remote_target_with_no_ceiling_is_legitimately_constructible`).

Everything else — the four-row policy table, the exact reason strings, fail-closed on no ceiling,
`VIOLATION` writable-but-never-produced, no enforcement anywhere — is spec/ADR-0054 verbatim.

## 4. Round-trip against the published `setspec 0.5.0` goldens

`tests/unit/test_payload_roundtrip.py` imports `setspec.artifacts.golden_names`/`golden_payloads`
directly from the **installed wheel** (`setspec==0.5.0`, confirmed via `pip show` in the test venv)
— never a local copy — so this suite's own drift from what SetSpec actually publishes would fail
here first. Covers all four published goldens (`minimal`, `full`, `denied_no_ceiling`, `violation`):
byte-identical canonical JSON in both directions
(`golden -> EgressDecision -> to_payload() == golden`, and `from_payload(to_payload(d)) == d`),
plus validation against the strict writer half (`GovernanceEgressDecisionOut`, not just the
preserving reader half), plus an unknown-top-level-field-survives-validation-and-redump case for
the "unknown-minor payload read without loss" contract. `EgressDecision.from_payload` itself has no
`extras` bucket to preserve an unknown field in — asserted explicitly
(`test_the_unknown_field_has_nowhere_to_land_on_the_value_object`) — the preservation lives in the
SetSpec payload model a caller reads, not in this package's value objects, which is the same answer
every other value object in the suite gives a payload it is built from.

One thing worth flagging: SetSpec's `governance.egress_decision` `1.0` payload gained a
`request.requested_at` field *after* `docs/history/B1_HANDOFF.md` was written (commit `72c5aab`, same day,
"governance.egress_decision 1.0 carries request.requested_at" — B1_HANDOFF §3's field list at the
time this row started did **not** show it). The installed `setspec==0.5.0` wheel already includes
it, so no action was needed here — `EgressRequest.requested_at` maps straight onto it — but it is
the kind of same-day drift worth knowing about if you're reading `docs/history/B1_HANDOFF.md` verbatim rather
than the installed package.

## 5. `mypy --strict` and the `payload_models()`-generated-class limitation

`GovernanceEgressDecisionOut`/`In` are generated at import time by
`setspec.base.payload_models()`, not declared as ordinary classes, and mypy cannot resolve a
variable holding `type[X]` from a generic function's return value as a usable type annotation
(`error: Variable "..." is not valid as a type`). This is not new to Commissioner — `FreeWeight`'s
`freeweight/services/evidence.py::wire_payload` hits the identical limitation against
`CapabilityEvidenceOut` and documents it the same way: return/parameter typed `Any` with a
`# noqa: ANN401` and a comment naming the real runtime type. `EgressDecision.to_payload`/
`from_payload` follow that exact precedent rather than inventing a second convention. `ruff`'s
selected rule set here (copied from LoadLedger) does not include `ANN`, so the `noqa` is
documentation, not a suppressed lint failure.

## 6. Test coverage beyond the development plan's minimum list

Development plan Phase 1 asked for: the full policy matrix (exhaustive by construction), round-trip
against goldens with unknown-minor preservation, determinism goldens, and `VIOLATION`
constructible-but-never-produced over the whole matrix. All four are covered
(`tests/unit/test_policy_matrix.py`, `test_payload_roundtrip.py`); `test_decision.py` additionally
covers every value-object construction refusal (blank identifiers, wrong types, naive datetimes)
to reach 100% coverage without any single test being a coverage-chasing tautology. The matrix's
"expected" oracle is computed via an independently-stated ordering tuple and `.index()` comparison,
not via `DataClassification.__le__` — the same operator `OrderedClassificationPolicy` uses
internally — so the test is not simply mirroring the implementation it checks.

## 7. Commits made

`py/Commissioner` (`main`, on top of the pre-existing `757ba9b` "first commit" — a `.gitignore`-only
commit that predates this session and was not touched):

```
8eb76e2 chore(commissioner): repository scaffold
6c53283 docs(commissioner): mirror spec and development-plan from the suite docs
299d20f feat(commissioner): Phase 1 — vocabulary binding, policy, decision, payload round-trip
4a48c26 docs(commissioner): README, changelog, and hash-pinned lockfiles
```

Working tree clean (`git status --short` empty). Nothing tagged. `origin` is already configured
(`https://github.com/JPKell/Commissioner.git`) — the remote repository itself already existed before
this session started, seeded with the same `.gitignore`-only commit every component repo in this
suite starts from. Nothing has been pushed.

## 8. Before the next session

1. **Push `main`.** `git push origin main` from `py/Commissioner`, then confirm CI goes green on
   first push (the workflow files were exercised locally end-to-end in §2 above, including the
   hash-pinned locks and the release build chain, but never inside GitHub Actions itself).
   **The GitHub remote still needs attention** — see §9 below: the actual `JPKell/Commissioner`
   repository does not exist yet (only the old `JPKell/SpotCheck` does), and the local `origin`
   URL still points at the old name; both need a human step before this push can land.
2. **PyPI naming — resolved by the rename in §9, re-verify before E3 (Phase 2, which publishes
   `0.1.0`).** The original name, `spotcheck`, was taken on PyPI by an unrelated package (a CLI
   for checking AWS spot-instance prices, by Joey Sham — confirmed via `pypi.org/pypi/spotcheck/json`
   returning `200` at the time). That is why the rename happened. Both `commissioner` and
   `aisuite-commissioner` were confirmed free (`404`) as of this session; re-check immediately
   before E3 actually publishes, since availability can change between now and then.
3. **`setspec`'s trusted-publisher release did not visibly gate on a manual environment
   approval** when B1/B3 checked, despite `release.yml`'s `environment: pypi` comment implying one.
   The user has since said "I have updated the environment in github for SetSpec" — sounds like
   this is handled, but it wasn't independently re-verified in this session. Commissioner's own
   `release.yml` (E3) copies the identical `environment: pypi` pattern, so whatever was fixed for
   SetSpec's environment should be mirrored onto Commissioner's GitHub repo once it exists.
4. Nothing else is blocking. The gate is green, the tree is clean, both mirrored documents are
   `cmp`-verified identical, and the round trip runs against the genuinely-published `setspec`
   `0.5.0` goldens (confirmed via `pip show setspec` inside the test venv, not assumed).

## 9. Renamed SpotCheck → Commissioner, same session

After this handoff was first written, the user asked for the package to be renamed from
`spotcheck` to `commissioner` everywhere — directly motivated by §8 item 2 above: `spotcheck` was
taken on PyPI by an unrelated package, `commissioner` was not. This section records what changed;
everything above this point in the document has already been edited in place to say
"Commissioner" throughout (mechanical rename, `sed`), so read the document as describing the
**current** state, not the state before the rename.

**Three repositories touched, each with its own commit:**

* **`py/Commissioner`** (this repo, `git mv` + `sed` + regenerated lockfiles): directory renamed
  from `py/SpotCheck`, `src/spotcheck` → `src/commissioner`, `docs/packages/spotcheck` →
  `docs/packages/commissioner` (re-synced byte-identical from the renamed workspace `docs/`),
  `SpotCheckError`/`SPOTCHECK_ERROR` → `CommissionerError`/`COMMISSIONER_ERROR`, every docstring,
  test, README/CHANGELOG/CONTRIBUTING/SECURITY reference, `pyproject.toml` (name, paths, coverage
  source, GitHub URLs), `.importlinter` `root_package`. Full gate re-verified green after the
  rename (mypy strict, ruff, lint-imports 3/3, pytest 68 passed, 100% coverage); lockfiles
  regenerated with pip-tools 7.6.1 and re-verified: `--require-hashes` install, `pip-audit` clean,
  release chain builds + twine-checks + installs standalone. Commit `7077cc4` on top of the four
  original commits.
* **workspace `docs/`** (the authoritative copy): `packages/spotcheck/` → `packages/commissioner/`,
  `adr/0054-spotcheck-records-egress-it-does-not-enforce-it.md` →
  `adr/0054-commissioner-records-egress-it-does-not-enforce-it.md` (content renamed too — ADRs are
  normally superseded, never edited, but this is a pre-publish nominal rename, not a reversed
  decision), plus every ADR, roadmap doc, `master-architecture.md`, `gold-standards.md` and
  `suite-flowchart.drawio` that named the component. 27 files, commit `e713c83`.
* **`py/SetSpec`** (already tagged and published as `0.5.0` — the trickiest of the three): its
  `governance.egress_decision` payload schema does **not** contain the string `spotcheck` as an
  identifier (the payload root is `governance.egress_decision`, unrelated to the producing
  package's name), so this was a prose-only change — CHANGELOG, README, `docs/schemas.md`, the
  mirrored `docs/packages/setspec/development-plan.md`, `governance/v1.py`'s docstrings, and the
  governance test module's docstring. **Two class docstrings** (`EgressVerdict`,
  `EgressRequestFields` in `src/setspec/governance/v1.py`) named "SpotCheck," and pydantic embeds a
  class's `__doc__` as its JSON Schema `description` — exactly the "dependency-docstring ripple"
  `docs/schemas.md` §5 already documents, except self-inflicted here rather than caused by an
  upstream dependency bump. Regenerated `src/setspec/schemas/governance.egress_decision/1.0.json`
  via the documented procedure, verified with a description-stripped structural diff against the
  pre-edit snapshot (`before == after` after stripping every `"description"` key — confirmed
  structurally identical, only prose moved), and added a `## [Unreleased]` CHANGELOG entry
  documenting the cosmetic-only regeneration (no version bump made — that's a separate, explicit
  publish decision, same as everywhere else in this session). Full gate re-verified: 1006 passed,
  4 skipped, coverage 97.48% (unchanged from B1's baseline). Commit `77ab89e`.

**Not touched, deliberately:** `docs/history/B1_HANDOFF.md` (a dated record of what B1 actually did, under the
name accurate at the time — rewriting it would falsify history); `A1_REPORT.md`, `A1_REVIEW.md`,
`harness.md` and the `.prompt.md` kickoff files at the workspace root (same reasoning — historical
artifacts, not living specs); `CLAUDE.md`'s broader staleness (it still lists Commissioner, like
LoadLedger, under "specified but have no repository yet," which was already wrong for LoadLedger
before this session and is now also wrong for Commissioner — only the name was fixed there, not
that pre-existing accuracy gap, since fixing it was out of scope for a rename request).

**One action blocked by the permission classifier**, not by anything technical:
`git remote set-url origin https://github.com/JPKell/Commissioner.git` in `py/Commissioner` was
denied. The local remote still points at `https://github.com/JPKell/SpotCheck.git`. Combined with
item 1 above (the GitHub repo itself needs creating/renaming — nothing was pushed under either
name), there are now two small GitHub-side steps outstanding before `git push origin main` can
work: create or rename the remote repository to `Commissioner`, and update the local `origin` URL
to match (either the user can grant the permission and ask again, or run
`git remote set-url origin https://github.com/JPKell/Commissioner.git` directly).
