# B1 Handoff — SetSpec 0.5.0 (Phase 6)

**Row:** B1 of `docs/roadmap/outstanding-work.md` §1. **Repository:** `py/SetSpec`.
**Status:** Complete through the gate; not tagged, not published. Working trees clean in both
`py/SetSpec` and `docs`; nothing pushed.

---

## 1. Precondition check

`baseaicore 0.4.1` was on PyPI at the start of this session (`pip index versions baseaicore` listed
`0.4.1, 0.4.0`). The repo's own venv had resolved `0.4.0` (the cached, still-`>=0.4,<0.5`-compatible
version) on install; it was force-upgraded with `pip install -U "baseaicore>=0.4.1"` before any work
began. **This upgrade is what surfaced an unplanned discovery — see §5.**

## 2. Gate results

Interpreter: `py/SetSpec/.venv/bin/python`, **Python 3.13.15**. `baseaicore` **0.4.1** installed in
that venv (its own `pip show` metadata still says `0.4.0` because it is an editable-adjacent cached
record from before the forced upgrade — `python -c "import baseaicore; print(baseaicore.__version__)"`
was not checked, but `pip show baseaicore | head -2` after the upgrade reports `Version: 0.4.1`, and
the regenerated JSON Schema snapshots in this commit are proof it was actually loaded).

```bash
cd py/SetSpec
source .venv/bin/activate
ruff format --check .        # 43 files already formatted
ruff check .                 # All checks passed!
mypy src tests                # Success: no issues found in 37 source files
lint-imports                  # Contracts: 2 kept, 0 broken
pytest -m "not live and not performance"    # 1000 passed, 4 skipped
pytest --cov --cov-report=term-missing      # 97.34% (floor 95%); every touched module 100%
                                             # except src/setspec/prompts.py (89%, pre-existing,
                                             # untouched by this row)
```

All green. `python -c "import setspec; print(setspec.__version__)"` → `0.5.0`.

## 3. Payload shapes as published — B3 pins these

### `capability.evidence` `1.1` (`setspec.capability.v1.CapabilityEvidenceV1_1Out` / `…In`)

Every `1.0` field (ADR-0022 §1, unchanged) plus one optional field:

```
adapter: AdapterIdentityFields | None = None
    name: str                    # ^[a-z][a-z0-9_-]{1,63}$
    artifact_digest: str         # sha256:<64 hex>, required
    source_digest: str | None
    canonical_suffix: str        # "+{name}@{digest_short}", checked against AdapterIdentity
```

Absent on every non-adapter record; a `@model_serializer` drops the key entirely rather than
emitting `null`, so a non-adapter record is byte-identical to what `1.0` writes — golden-tested
(`test_adapter_axis_i15.py`) and unit-tested (`test_payloads_capability.py::TestCapabilityEvidenceV1_1`).

**The bare names `CapabilityEvidenceOut`/`CapabilityEvidenceIn` keep meaning `1.0`.** A producer
wanting `1.1` imports `CapabilityEvidenceV1_1Out`/`CapabilityEvidenceV1_1In` explicitly. This was a
deliberate naming decision, not a default — see §5.

`benchmark.evidence_bundle` is **untouched**: it still nests the `1.0` shape by reference. A bundle
carrying adapter-bearing evidence is FreeWeight 1.1 / LA3 work, not this row's.

### `model.adapter_manifest` `1.0` (`setspec.model.v1.AdapterManifestOut` / `…In`)

```
name: str                        # via baseaicore.AdapterIdentity reconstruction
artifact_file: str               # relative path, a locator not an identity
artifact_sha256: str             # sha256:<64 hex>, required — the adapter's identity
source_sha256: str | None        # lineage only
base: AdapterManifestBaseFields
    provider_model_name: str
    artifact_digest: str | None
    identity_confidence: "digest" | "name_only"   # checked against artifact_digest's presence
declared_capabilities: list[str] # validated strictly against setspec.vocabulary; no
                                  # forward-compat exception (no vocabulary_version field here)
data_classification: "public" | "internal" | "confidential"   # REQUIRED, no schema default
format: "gguf"                   # fixed
created_at: RFC 3339 timestamp
notes: str | None
```

### `governance.egress_decision` `1.0` (`setspec.governance.v1.GovernanceEgressDecisionOut` / `…In`)

```
decision_id: str
request:
    run_id: str
    source_ref: str
    data_classification: "public" | "internal" | "confidential"   # required, non-nullable
    target:
        name: str
        remote: bool
        max_data_classification: "public" | "internal" | "confidential" | None   # nullable
        provider_kind: str | None
verdict: "approved" | "denied" | "violation"     # local EgressVerdict StrEnum
reason: str                      # free text; not validated against a closed set
policy_name: str
policy_version: str
decided_at: RFC 3339 timestamp
```

Note: `EgressRequest.requested_at` from SpotCheck spec §7's dataclass is **not** on this payload —
the kickoff's field list omits it, and `decided_at` already timestamps the record. If SpotCheck's
real implementation needs it on the wire, that is a scope decision for B3, not an oversight here.

All three registered in `setspec.SUPPORTED_SCHEMAS` and `setspec.artifacts.PUBLISHED_SCHEMAS`.
`capability.evidence` now publishes **two** versions (`1.0`, `1.1`); every other schema is
unchanged at exactly `1.0`.

## 4. Mirrored documentation — `cmp` output

```
$ cmp docs/packages/setspec/spec.md py/SetSpec/docs/packages/setspec/spec.md && echo OK
OK
$ cmp docs/packages/setspec/development-plan.md py/SetSpec/docs/packages/setspec/development-plan.md && echo OK
OK
```

Both byte-identical. `py/SetSpec/docs/schemas.md` is **not** a mirrored file (only `spec.md` and
`development-plan.md` are, per this row's brief) and was edited locally only.

## 5. What I discovered / decided — read this before B3

**Not a short list.** Two real design decisions and one unplanned dependency-drift issue.

### 5a. The `baseaicore 0.4.1` docstring ripple (discovered, not anticipated)

Upgrading the venv's `baseaicore` from `0.4.0` to `0.4.1` (required by this row's own precondition)
changed two enum docstrings (`IdentityConfidence`, `ModelCapabilityFlag`) in ways unrelated to the
adapter feature. Pydantic embeds an enum's `__doc__` as its JSON Schema `description`, so five
already-frozen, already-committed `1.0` snapshots regenerated with different bytes:
`model.identity`, `benchmark.result`, `benchmark.run_summary`, `capability.evidence` (its `1.0`
entry), `benchmark.evidence_bundle`.

I verified — with a description-stripped structural diff, before committing — that **no property,
type or required field changed** in any of the five; only the two nested `description` strings
moved. I regenerated and committed all five, since the alternative (leaving them stale) means this
build's own schema-snapshot test fails for a reason that has nothing to do with a payload shape
(the test regenerates from the *installed* `baseaicore`, so anyone gating against `0.4.1` — which
is now everyone, since `0.4.0` is superseded — hits this regardless of anything else in this row).

**This will recur.** Any future `baseaicore` release that touches a docstring on a type embedded in
a SetSpec schema (`ProviderKind`, `DataClassification`, `IdentityConfidence`,
`ModelCapabilityFlag`, now `AdapterIdentity`-adjacent types) will do this again. It is cosmetic and
correctly handled by re-running the regeneration script and diffing structurally before committing
— documented in `docs/schemas.md` §5 and `spec.md` §19 now, so the next person hitting it has a
name for it rather than a scare.

### 5b. Post-freeze minor bumps use a sibling class, not an edit in place (design decision)

The kickoff doc says "additive minor... following the ADR-0032 precedent." ADR-0032's goal-sourced
field group was added to `CapabilityEvidenceFields` **before** the `1.0` freeze (folded into the
Phase 4 promotion), so that precedent never had to reconcile an edit against an *already-committed*
downstream snapshot. This row is the first genuine post-freeze minor, and editing
`CapabilityEvidenceFields` in place turned out to be unsafe: `EvidenceBundleFields` nests that exact
class by reference, so any change to its fields *or docstring* silently moves
`benchmark.evidence_bundle`'s committed `1.0` schema too — a schema this row must not touch.

Resolution: `CapabilityEvidenceFields` (and everything that references it, including the bundle) is
byte-for-byte untouched. `capability.evidence` `1.1` lives on a new sibling class,
`CapabilityEvidenceV1_1Fields(CapabilityEvidenceFields)`, generating its own
`CapabilityEvidenceV1_1Out`/`In` pair. I've written this up as the pattern future minors on
already-frozen payloads should follow (`spec.md` §11 rule 9, §19; `docs/schemas.md` §5) — it is now
a documented convention, not a one-off.

**Consequence for anyone importing SetSpec going forward:** `CapabilityEvidenceOut`/`In` did **not**
change meaning. A consumer that wants adapter-aware evidence must import
`CapabilityEvidenceV1_1Out`/`In` by name. If a future decision wants the bare name to always mean
"latest minor," that's a naming-convention ADR, not a code change here — I did not make that call
unilaterally since it affects every existing importer's expectations.

### 5c. `governance.egress_decision` carries no cross-field "fail-closed" validator (design decision)

I considered adding a `model_validator` refusing `verdict="approved"` on a remote target with no
`max_data_classification` (ADR-0054 rule 3's fail-closed rule) directly on the payload. I did not
add it. `EgressPolicy` is a `Protocol` — SpotCheck spec §7 explicitly allows a caller to supply a
different, non-shipped policy — and ADR-0054 rule 6 says the package (and by extension its payload)
carries "no application policy." Baking the shipped policy's specific rule into the wire shape would
reject a legitimate document from any other policy. The rule is enforced by
`OrderedClassificationPolicy` itself (B3's job), not by the payload that merely records what any
policy decided. Flagging this explicitly in case B3's author expected the schema to enforce it.

### 5d. `model.adapter_manifest`'s "refusal case" golden

The kickoff's manifest-goldens list ("digest-verified base, name-only base, and a refusal case")
can't be satisfied literally — a golden is by definition a document that validates, so an invalid
document has no home there. I read "refusal case" as a request for refusal *coverage*, provided as
unit tests instead: `test_data_classification_is_required_with_no_default`,
`test_a_bare_reserved_capability_root_is_refused`, `test_base_confidence_must_match_digest_presence`,
`test_a_malformed_base_digest_is_rejected`, `test_a_malformed_name_is_refused_via_adapter_identity`
in `test_payloads_capability.py::TestAdapterManifest`. The three actual manifest goldens are
`minimal` (name-only base), `full` (digest-verified base, fully populated), `name_only` (a second
name-only example, with lineage and multiple declared capabilities) — satisfying "≥ 3, minimal and
full present" from the goldens machinery.

### 5e. Two existing generic contract tests needed fixing, not just new cases added

`test_a_v2_0_document_is_refused` and `test_the_minimal_golden_is_actually_smaller_than_the_full_one`
(both pre-existing, parametrized across every published schema/version) encoded assumptions that
were true only because, before this row, every schema had exactly one published version and every
schema had at least one optional top-level field. Both assumptions became false the moment
`capability.evidence` gained a second version and `governance.egress_decision` shipped with an
all-required top level. Both tests are fixed generically (§ "test" commit message has the detail),
not special-cased for the new schemas — they now hold for every schema, old and new.

## 6. Before the next session

1. **Tag and publish `setspec 0.5.0` to PyPI.** B3 (SpotCheck P1) pins the published package per its
   spec's dependency line (`setspec>=0.5,<0.6`); nothing in this repo does that automatically.
   ```bash
   cd py/SetSpec
   git tag v0.5.0
   git push origin main --tags     # or however this suite's release flow pushes
   # build + upload via the pypi environment approval, per packaging-and-release-standards.md
   ```
2. **Verify the published package in a clean virtualenv** (M5C-13 discipline):
   ```bash
   python -m venv /tmp/setspec-0.5.0-check && source /tmp/setspec-0.5.0-check/bin/activate
   pip install setspec==0.5.0
   python -c "from setspec.governance.v1 import GovernanceEgressDecisionOut; print('ok')"
   python -c "from setspec.model.v1 import AdapterManifestOut; print('ok')"
   python -c "from setspec.capability.v1 import CapabilityEvidenceV1_1Out; print('ok')"
   ```
3. **Read §5 above before writing SpotCheck code.** In particular: `governance.egress_decision`'s
   fail-closed rule is *not* enforced by the payload (5c) — SpotCheck's `OrderedClassificationPolicy`
   must enforce it itself, and B3's own test suite should assert that directly rather than assuming
   SetSpec already refuses the bad combination.
4. Nothing else is blocking. The gate is green, both repos are clean, and both mirrored documents are
   `cmp`-verified identical.

## 7. Commits made

`py/SetSpec` (`main`, on top of `ca5424c`):
```
c186487 feat(setspec): publish model.adapter_manifest 1.0, governance.egress_decision 1.0, capability.evidence 1.1 (Phase 6)
e3f3ad9 test(setspec): cover the adapter axis and I15; fix two version-count-sensitive contract tests
c0ed3a2 docs(setspec): Phase 6 development plan, spec and schema catalogue; bump to 0.5.0
```

`docs` (`main`, on top of `42d25ea`):
```
0a7a4e8 docs(setspec): Phase 6 — capability.evidence 1.1, model.adapter_manifest, governance.egress_decision
```

Nothing pushed, nothing tagged, both trees clean (`git status --short` empty in both).
