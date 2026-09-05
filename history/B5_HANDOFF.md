# B5 Handoff — SetSpec 0.6.0 (Phase 7)

**Row:** B5 of `docs/roadmap/outstanding-work.md` §1. **Repository:** `py/SetSpec`.
**Status:** implementation, tests and documentation complete; gate green; nothing tagged, nothing
published. Read by the human before the release, and by the H4 (FreeWeight 1.1) session later.

## Precondition check (before starting)

```bash
pip index versions setspec        # → 0.5.0 (matched)
cd py/SetSpec && git status --short && git describe --tags
```

`git status --short` was clean. `git describe --tags` returned `v0.5.0-1-g77ab89e` — HEAD was one
commit past the `v0.5.0` tag, not exactly at it. Inspected the extra commit (`77ab89e`): a
docs-only rename ("SpotCheck" → "Commissioner" throughout prose, cosmetic regeneration of
`governance.egress_decision/1.0.json` confirmed structurally identical). No code, no schema, no
golden changed relative to what was published as `0.5.0`. `CapabilityEvidenceV1_1Fields` was
present in the tree. Treated the precondition as satisfied and proceeded; noting the one-commit
offset here in case it matters to the release step.

## Gate results

Interpreter: `py/SetSpec/.venv/bin/python`, **Python 3.13.15**.

```bash
cd py/SetSpec && source .venv/bin/activate
ruff format --check .        # 44 files already formatted
ruff check .                 # All checks passed!
mypy src tests                # Success: no issues found in 38 source files
lint-imports                  # Contracts: 2 kept, 0 broken
pytest -m "not live and not performance" --cov --cov-report=term-missing
  # 1072 passed, 4 skipped in 2.57s
  # TOTAL coverage 97.48% (floor 95%)
```

All green. `capability/v1.py` itself: 124 stmts / 22 branches, 100% covered.

## The published shape

New sibling class in `src/setspec/capability/v1.py`, beside the untouched `EvidenceBundleFields`:

```python
class EvidenceBundleV1_1Fields(EvidenceBundleFields):
    evidence: WireSequence[CapabilityEvidenceV1_1Fields] = ()

EvidenceBundleV1_1Out, EvidenceBundleV1_1In = payload_models(EvidenceBundleV1_1Fields)
```

Field list is **identical** to `EvidenceBundleFields`: `source_id: str`, `complete: bool`,
`evidence: WireSequence[...]` — only the element type of `evidence` widened, from
`CapabilityEvidenceFields` (`1.0`) to `CapabilityEvidenceV1_1Fields` (`1.1`, the adapter-bearing
sibling B1/Phase 6 published). No field was added to the bundle itself.

Exported names (H4 imports these): `EvidenceBundleV1_1Fields`, `EvidenceBundleV1_1Out`,
`EvidenceBundleV1_1In`, all in `setspec.capability.v1`, all in `__all__` in sorted position.

**`EvidenceBundleFields` was not edited** — not its fields, its validators, or its docstring. Its
docstring's sentence "the `1.1` adapter field does not reach here" now describes only `1.0` and
was deliberately left stale; the resolution is explained in the module docstring (top of
`capability/v1.py`) and in `docs/packages/setspec/development-plan.md` Phase 7. This is the one
constraint the row flagged as a stop rather than a judgment call, and I did not touch the class —
confirmed by `git diff` showing zero lines changed in `EvidenceBundleFields`'s own body across all
four commits.

**Registration:**
- `artifacts._REGISTRY["benchmark.evidence_bundle"]` gained `_VERSION_1_1: (EvidenceBundleV1_1Out,
  EvidenceBundleV1_1In)` beside `_VERSION_1_0`.
- `envelope.SUPPORTED_SCHEMAS["benchmark.evidence_bundle"]` raised to `{1: SchemaVersion(1, 1)}`.
- `DRAFT_SCHEMAS` untouched (still empty). No major moved.

**No new serializer was needed** — checked by test, not assumed
(`test_adapter_present_in_the_dump_when_set` / `test_adapter_absent_from_the_dump_on_the_bare_base_record_only`
in `test_payloads_capability.py`): `CapabilityEvidenceV1_1Fields`'s existing
`@model_serializer(mode="wrap")` runs per-element when pydantic serializes the `WireSequence`, so
a nested `1.1` record with no adapter already omits the key rather than emitting `"adapter": null`.

## Byte-identity evidence

- `git diff --stat` on `src/setspec/schemas/` across the whole row shows **one new file**
  (`benchmark.evidence_bundle/1.1.json`) and **zero modified files** — `1.0.json` regenerated
  byte-identical.
- `goldens/benchmark.evidence_bundle/1.1/minimal.json` is byte-identical to the committed
  `1.0/minimal.json` (verified with `diff`, and again in
  `tests/contract/test_bundle_minor_is_additive.py::TestTodaysBundlesRoundTripByteIdentically::test_a_1_0_golden_file_on_disk_is_unchanged`).
- `tests/contract/test_bundle_minor_is_additive.py` — new module, the bundle's own I15 — asserts
  every committed `benchmark.evidence_bundle/1.0` golden (`minimal`, `full`, `unsupported`) dumps
  byte-identically whether validated through `EvidenceBundleOut` or `EvidenceBundleV1_1Out`, over
  the *existing* committed goldens (`canonical_dumps(via_1_0) == canonical_dumps(via_1_1)`), plus
  the on-disk-unchanged check and the mixed-bundle per-record adapter-presence round trip.
  Cross-referenced with `tests/contract/test_adapter_axis_i15.py` (LA0's exit condition) in both
  files' docstrings — kept as separate modules per the row's instruction.

Four goldens for `1.1` (floor is 3; `unsupported` was needed because the bundle nests
`dispersion`/other measurement fields, which the generic `test_goldens.py` check for a
`{"const": "unsupported"}` branch in the published schema caught automatically):
`minimal` (62 bytes, byte-identical to `1.0`), `full` (all 3 evidence records adapter-bearing, two
distinct adapter identities — `factcheck` and a second one, `styleguide`, computed and verified
against `baseaicore.AdapterIdentity` directly since only one adapter identity previously existed
anywhere in the fixtures), `mixed` (1 bare-base + 2 adapter-bearing records in one bundle — LA3's
actual export shape), `unsupported` (an adapter-bearing record with `dispersion: "unsupported"`
and other unsupported measurement fields, mirroring `1.0`'s own `unsupported` golden).

## Contract tests extended (item 4 of the row)

- `test_schema_snapshots.py::TestTheFreezeHolds` — the single hard-coded exclusion id was replaced
  with a module-level `_NAMED_EXCEPTIONS` frozenset naming both `"capability.evidence 1.1"` and
  `"benchmark.evidence_bundle 1.1"`, with a docstring explaining which phase each came from. The
  renamed test (`test_every_schema_that_is_not_a_named_exception_is_still_1_0`) and the renamed
  "second published minor" test (`test_capability_evidence_and_evidence_bundle_are_the_schemas_with_a_second_minor`)
  now assert both payloads' exact published version tuples explicitly — neither was relaxed to a
  count.
- `test_goldens.py` needed **no changes** — its `_PUBLISHED`/`_EVERY_GOLDEN` parametrizations and
  the minimal-vs-full serialized-byte-size check are all derived from `PUBLISHED_SCHEMAS` and
  `golden_names(...)`, so `1.1` was picked up automatically; verified by running the file and
  seeing the new `benchmark.evidence_bundle 1.1 *` parametrized cases appear and pass.
- `test_adapter_axis_i15.py` — one paragraph added to its module docstring cross-referencing the
  new file; no test logic changed, since this file is LA0's exit condition specifically.

## Documentation

- `docs/packages/setspec/development-plan.md` — new **Phase 7** section (Goal / Prerequisites /
  Work / Files-subsystems / Tests / Acceptance criteria / Known risks / Likely failure modes / Gold
  standards / Deferred), closing the loop Phase 6's Deferred paragraph opened.
- `docs/packages/setspec/spec.md` — §7's `EvidenceBundle` entry now documents `1.1`; §11 rule 9
  gained the transitive-nesting paragraph with `benchmark.evidence_bundle` as its worked example;
  §19's coexisting-minors bullet now names both Phase 6 and Phase 7.
- `py/SetSpec/docs/schemas.md` (component-repo-only catalogue, not one of the two mirrored files)
  — updated status line, catalogue table row, and the `benchmark.evidence_bundle` prose section.
  Not in the row's explicit doc list but left stale it would have actively misstated the current
  shape (it said "this schema is untouched by Phase 6" and listed only `1.0`), so I updated it.
- `README.md` status line → `0.6.0`, Phases 1–2, 3A, 4, 5, 6, 7; `CHANGELOG.md` → new `## [0.6.0]`
  section (folding the pre-existing `## [Unreleased]` SpotCheck→Commissioner entry in under it,
  same date, since `[Unreleased]` was already carrying content when this row started);
  `src/setspec/__about__.py` → `0.6.0`.

**Mirror `cmp` output** (workspace `docs/` is authoritative; component copy is the mirror):

```
$ cmp docs/packages/setspec/spec.md py/SetSpec/docs/packages/setspec/spec.md && echo OK
OK
$ cmp docs/packages/setspec/development-plan.md py/SetSpec/docs/packages/setspec/development-plan.md && echo OK
OK
```

## Commits made

`py/SetSpec` (all on `main`, tree clean, nothing pushed):
```
fd39c8c feat(setspec): benchmark.evidence_bundle 1.1 — the adapter axis, one payload out
8b5cb2f feat(setspec): publish schema and goldens for benchmark.evidence_bundle 1.1
2aca30f test(setspec): cover benchmark.evidence_bundle 1.1's additive proof
833e4e7 docs(setspec): Phase 7 documentation and 0.6.0 release prep
```

`docs` (workspace repo, on `main`, tree clean, nothing pushed):
```
75eeada docs(setspec): Phase 7 — benchmark.evidence_bundle carries the adapter axis
```

## Things found along the way

- **The one-commit tag offset** noted under Precondition check — `v0.5.0` doesn't point at the tip
  of what was actually published-equivalent; a docs-only commit sits on top. Harmless for this
  row, but worth the human's attention when deciding what `v0.6.0` tags.
- **A second adapter identity was needed** for a realistic `full`/`mixed` golden (more than one
  adapter in a bundle) and none existed anywhere in the repo's fixtures — only `factcheck`
  (digest `9e2b41d07c55…`) appears in `capability.evidence/1.1`'s own goldens and tests. Computed a
  second one (`styleguide`, digest `b7c94a10de23…`) directly against `baseaicore.AdapterIdentity`
  to get a valid `canonical_suffix`, rather than reusing `factcheck` everywhere. Not a spec gap,
  just a fixture-authoring note for whoever writes the next adapter-bearing golden.
- **`docs/schemas.md` is genuinely not mirrored** — confirmed with `find` across both `docs/` trees
  before editing it only in `py/SetSpec/`. Worth someone eventually deciding whether it should join
  the mirrored pair, since it's the file a non-Python consumer is pointed at.
- No `baseaicore` version drift occurred this session (Phase 6's Known risks precedent did not
  recur) — recorded as "none realized" in Phase 7's own Known risks paragraph rather than omitted.

## Before the next session

1. **Tag and publish `setspec 0.6.0`** — not done here; not authorized.
   ```bash
   cd py/SetSpec
   git tag -a v0.6.0 -m "setspec 0.6.0 — Phase 7: benchmark.evidence_bundle carries the adapter axis"
   git push origin main --tags
   # build + publish to the `pypi` environment per this repo's normal release process
   ```
2. **Clean-venv install check**, as specified by the row:
   ```bash
   python -m venv /tmp/setspec-0.6.0-check && source /tmp/setspec-0.6.0-check/bin/activate
   pip install setspec==0.6.0
   python -c "from setspec.capability.v1 import EvidenceBundleV1_1Out; print('ok')"
   ```
3. Decide whether `docs/schemas.md` should become the workspace `docs/`'s third mirrored file for
   SetSpec (see "Things found along the way").
4. H4 (FreeWeight 1.1, LA3) can now proceed: `setspec 0.6.0` publishes the bundle shape it needs.
   Adopting it is the one-line `EvidenceBundleV1_1Out` import the row's Constraints section
   describes — FreeWeight's tree was not touched here.
