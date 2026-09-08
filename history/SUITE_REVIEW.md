# Suite review — post-M6 solidification (2026-08-31)

Run unattended by Fable 5 against the ground state of 2026-08-31. Every gate below names its
interpreter and invocation (M5C-13). All commits pushed; **no tag, publish or upload was
performed** — the human step is the final command block.

## Verdict

**Solid — every condition met (final state, 2026-08-31).** The verdict opened as "solid with
conditions"; the same day, all four tags were cut and their deployments approved:
**modelrack 0.6.0, weightsdb 0.2.1, mirrorwall 0.2.1 and freeweight 1.0.0 are on PyPI.** The
P-4 adoption landed in LoadCoach (`0d9e3c6`) with CI green on the runner (run `33422721770`,
all 13 jobs — the first red attempt, run `33421853354`, failed only at the hash-verified lock
install because the runner's PyPI edge had not yet propagated the minutes-old 0.2.1 artifacts;
the lock's hashes match PyPI's digests exactly and the retrigger passed). The published
`freeweight 1.0.0` wheel was verified in a clean venv: version string with schema versions,
doctor finding provider/GPU/sandbox/prompt-pack (golden `sha256:b1b0ffd0…` intact). The one
step left to a human with the shared GPU: spec §20 AC1's real native benchmark + export against
Ollama. **The ground is ready for IdeaPress.**

The two real defects this review found in FreeWeight (F-1, F-2) are fixed, gated, pushed and
released; `TAG_APPROVED: no` was standing on the absence of a verification, and the
highest-risk subset was run (see P-5 below).

## Per-repo status

| Repo | Gate | Coverage vs floor | Spec vs surface | Docs mirror | Release state |
|---|---|---|---|---|---|
| BaseAiCore | green (Py 3.13.15, `.venv/bin/pytest`, 548 passed) | 100% ≥ 95% | ✓ (stdlib-only proven by AST walk; ADR-0016 semantics verified live) | restored byte-identical (`e98e1e9`) | v0.4.0 published; head past tag is docs/CI only — waits for next functional release |
| SetSpec | green (Py 3.13.15, 802 passed / 2 skipped) | 97.28% ≥ 95% | ✓ (goldens byte-stable, 323 contract tests; `freeweight.export` ∉ SUPPORTED; DRAFT_SCHEMAS empty = freeze readable) | restored (`ca5424c`) | v0.4.0 published, tag at head |
| ModelRack | green (Py 3.13.15, 935 passed / 14 skipped) | 100% ≥ 95% | ✓ (FakeProvider parity restored incl. new `context_length`) | restored (`ce73f74`) | **0.6.0 prepared — tag pending-human** at `ce73f74`; 0.5.0 on PyPI |
| SweatMeter | green (Py 3.14.4, 351 passed) | 99.71% ≥ 95% | ✓ (no real-GPU reads outside `-m live`; null readers never zero) | restored (`83c1384`) | v0.4.0 published, tag at head |
| WeightsDB | green (Py 3.14.4, 129 passed / 10 skipped) | 96.37% ≥ 95% | ✓ (version-table default now pinned in its own suite) | restored (`57c7824`) | **0.2.1 prepared — tag pending-human** at `88f7ff5`; 0.2.0 on PyPI |
| MirrorWall | green (Py 3.14.4, 312 passed) | 98.33% ≥ 95% | ✓ (public-API contract test updated for `safe_href`, a deliberate addition) | restored (`d169db5`) | **0.2.1 prepared — tag pending-human** at `6d50c3f`; 0.2.0 on PyPI |
| LoadCoach | green (Py 3.14.4, 807 passed / 2 skipped) | 91.55% ≥ 85% | ✓ (M5C spot-checks re-run: breaker single-probe, sync-path, trusted-proxy brake — 16 passed; no `freeweight` import anywhere) | already byte-identical | **v1.0.0 tagged, released and verified**: run `33367190485` success; clean-venv `pip install loadcoach==1.0.0` → `--help`, `--version`, doctor all pass |
| FreeWeight | green (Py 3.14.4, 2,508 passed / 28 skipped) | 89.67% ≥ 85% (97% domain floor held at M6) | ✓ (M6-13/14 reconciliations stand; route sweep of all 28 parameterless GETs clean) | restored (`d468457`) | 1.0.0 built; CI green at head (run `33370828360`); **v1.0.0 tag recommended, pending-human**; `freeweight 1.0.0rc1` already on PyPI (name is the suite's, claimed 2026-08-29) |

## Findings

Entry style follows M4_HANDOFF.md. "fixed in `<hash>`" = committed and pushed to that repo's main.

### F-1 — FreeWeight: `GET /goals/new` returned 500 on every fresh render
- **Severity:** BLOCKER (fixed)
- **Where:** `FreeWeight/src/freeweight/web/routes/wizard.py::wizard_start`,
  `templates/goals/wizard_intent.html`
- **Reproduction:** boot `freeweight serve` against a fresh database, `curl
  http://127.0.0.1:<port>/goals/new` → `{"error":{"code":"INTERNAL_ERROR"…}}`;
  `jinja2.exceptions.UndefinedError: 'intent' is undefined` in the log. The template renders
  `{{ intent or '' }}` as the sticky form value and the fresh-GET context never passed `intent` —
  the M6-3 StrictUndefined defect class, on the first page of the one journey spec §20 AC13 is
  named for. No test ever GET the page: the journeys post the form directly, and the POST error
  path echoes the submitted text back, so the browser's first render was never exercised. Found
  during P-5's real-socket CSRF check.
- **Disposition:** fixed in `e3bf753` — context now passes `intent=""`; a new e2e class
  (`TestEveryWizardPageSurvivesAFreshGet`) GETs every wizard step fresh, watched failing against
  the unfixed route; a sweep of all 28 parameterless GET routes found no further instance.

### F-2 — FreeWeight: M6-8's placeholder dataset pins were invisible where a user would hit them
- **Severity:** MAJOR (fixed)
- **Where:** `external/datasets.py`, `services/external.py`, `cli/commands/external.py`,
  `templates/sources/index.html`
- **Reproduction:** `freeweight external list` and `GET /sources` said nothing about the shipped
  `sha256:000…0` pins, and a hash mismatch against one claimed "the file changed since it was
  pinned" — sending a user chasing corruption that never happened. The review prompt requires
  M6-8 "flagged wherever a user would try one"; it was flagged nowhere.
- **Disposition:** fixed in `0429202` — `is_placeholder_pin()` added; sources page carries the
  placeholder statement; `external list` marks affected adapters (JSON gains
  `has_placeholder_pins`); the mismatch refusal against a placeholder says "record the true
  sha256". The pins themselves remain placeholders **deliberately** — recording real hashes needs
  network and a human (M6-8's own disposition, unchanged).

### F-3 — Docs mirrors diverged from canonical in 7 of 8 repos, one with content corruption
- **Severity:** MAJOR (fixed)
- **Where:** every `*/docs/packages/*` and `FreeWeight/docs/apps/freeweight/*` mirror except
  LoadCoach's
- **Reproduction:** `cmp` each mirror against `~/ai/suite/docs` — 16 files differed. Cause: a
  "Cleanup docs" link-stripping pass edited the *mirrors* (downstream-first, against the rule),
  and its regex ate the literal `[since, until)` interval notation in FreeWeight's `api.md`,
  changing meaning. LoadCoach, mirrored by `cmp` during M5C, was the only clean repo.
- **Disposition:** fixed — all mirrors restored byte-identical to canonical and proven by `cmp`:
  `e98e1e9` (BaseAiCore), `ca5424c` (SetSpec), `ce73f74` (ModelRack), `83c1384` (SweatMeter),
  `57c7824` (WeightsDB), `d169db5` (MirrorWall), `d468457` (FreeWeight). The rule stands as
  written in CLAUDE.md: canonical first, mirrors byte-identical.

### F-4 — SweatMeter: the platform-support page Phase 4 shipped was never written
- **Severity:** MINOR (fixed)
- **Where:** canonical `docs/packages/sweatmeter/development-plan.md` Phase 4 deliverables vs the
  repo tree
- **Reproduction:** the plan lists `docs/platform-support.md` as "shipped as 0.4.0";
  `find py/SweatMeter -name platform-support*` → nothing (the stale mirror had quietly deleted
  the mention — the same link-stripping pass).
- **Disposition:** fixed in `83c1384` — the page written from spec §16 and the cross-platform
  tier table: per-tier behaviour, what "degrades" means (UNSUPPORTED with a reason, never zero),
  the two NVIDIA backends, the factories' fallbacks.

### F-5 — WeightsDB: changelog did not match the v0.2.0 tag
- **Severity:** MINOR (fixed)
- **Where:** `py/WeightsDB/CHANGELOG.md`; the annotated tag `v0.2.0` (object `4a56cf8`) points
  **at head** `bc40d15`
- **Reproduction:** `git rev-parse v0.2.0^{commit}` → `bc40d15`; the "coverage below floor"
  fixes sat under `[Unreleased]` though the tag ships them, and `31dad6c` (health: "ahead of
  head" vs "pending migration") was in no section at all.
- **Disposition:** fixed in `57c7824` — both folded into `[0.2.0]`. Ground-state correction: the
  review prompt's "head past the tag" was wrong for WeightsDB *and* MirrorWall — both v0.2.0
  annotated tags resolve to head; nothing was unreleased.

### F-6 — SetSpec: README a full release behind the code
- **Severity:** MINOR (fixed)
- **Where:** `py/SetSpec/README.md`
- **Reproduction:** README said `0.3.0` and "prompt records (Phase 5) are not yet written" while
  the head commit is `feat(setspec): add setspec.prompts (Phase 5, 0.4.0)`. All three README code
  blocks executed verbatim against the published 0.4.0 wheel — the code was right, the prose
  stale. Phase 3's event/error envelopes remain honestly stubs.
- **Disposition:** fixed in `ca5424c`.

### F-7 — LoadCoach: README still said "not yet published" after publication
- **Severity:** MINOR (fixed)
- **Where:** `LoadCoach/README.md` status paragraph and install block
- **Disposition:** fixed in `52afc64`, after P-6 verified the release end to end (below).

### F-8 — MirrorWall: M6-4's localStorage namespace was "documented behaviour" documented nowhere
- **Severity:** NOTE (fixed)
- **Where:** canonical `docs/packages/mirrorwall/spec.md` §10
- **Disposition:** fixed in `6d50c3f` (mirror) and `63314fa` (canonical) — §10 now names
  `DEFAULT_THEME_STORAGE_KEY` (`mirrorwall-theme`, application-overridable) and
  `mirrorwall-columns:<table id>`, and states that swapped-in table scripts orphan old keys
  silently.

### F-9 — WeightsDB: the version-table default was pinned only by consumers
- **Severity:** NOTE (fixed)
- **Where:** `py/WeightsDB/tests/integration/test_migrations.py`
- **Reproduction:** P12's named failure mode — both applications' shipped databases record their
  revision in `alembic_version`; no WeightsDB test asserted the default, so a changed default
  would surface first as every consumer database looking unmigrated.
- **Disposition:** fixed in `88f7ff5` — pinned in WeightsDB's own suite.

### F-10 — BaseAiCore: README output comment wrong; head past tag is non-functional
- **Severity:** NOTE (fixed / no release needed)
- **What:** `print(identity.identity_confidence)` prints `digest` (StrEnum), not
  `IdentityConfidence.DIGEST` as the comment claimed — fixed in `e98e1e9`. Six commits past
  v0.4.0 are docs/CI/lockfiles plus docstring link-stripping under `src/` (diff inspected:
  comments only, zero behaviour change); they wait for the next functional release, and
  `[Unreleased]` already names the lockfiles.

### F-11 — DECISION: ModelRack ships the `context_length` work as 0.6.0
- **Severity:** DECISION (recorded)
- **What:** P-1's uncommitted work reviewed as foreign code: the ADR-0023 §4 reading is correct
  (`ResidentModel.context_length` is the *reported* served context, distinct from the descriptor's
  advertised maximum); `as_measurement` already refuses `None`/strings/booleans, so
  UNSUPPORTED-when-absent is honest for every `/api/ps` shape (older Ollama omits the key); the
  docstring states what the field refuses; tests covered both present and absent keys. Finished
  with FakeProvider parity (`FakeModel.context_length`, threaded through `list_resident`, tested
  scripted and unscripted), CHANGELOG, and the version decision: **0.6.0**, minor, per the
  setspec 0.3→0.4 precedent (additive feature = minor; pre-1.0 standard §3 makes minor the
  compatibility boundary, which is exactly why both apps pin `<0.6`). Nothing is stranded: no app
  consumes the field yet — LoadCoach's `ProviderView.reported_served_context` is the dormant seam
  (grep shows nothing populates it), and the adoption that wires it bumps the pin, exactly as
  FreeWeight's setspec-0.4 adoption did. Fixed in `8bb5b3b`; tag goes on `ce73f74`.

### F-12 — DECISION: `secure_delete=ON` added to the database standard, canonical-first
- **Severity:** DECISION (recorded)
- **What:** P-2's change is a *guarantee* change (a retention scrub means the same thing on every
  machine), so the SQLite settings row in `standards/database-standards.md` §2 and the WeightsDB
  spec now name it — edited in `~/ai/suite/docs` first (`63314fa`), mirrored byte-identically. No
  ADR: it implements the M4 handoff's recorded item within ADR-0006/ADR-0016's existing stances.
  LoadCoach deliberately untouched, as the handoff instructs.

### F-13 — Ground-state corrections the next run should carry
- **Severity:** NOTE
- **What:** (1) WeightsDB and MirrorWall `v0.2.0` tags point at their heads — the prompt's "head
  past the tag" rows were an annotated-tag-object/commit confusion. (2) PyPI `mirrorwall 0.2.0`
  (uploaded 2026-08-30 08:02 UTC) already requires `starlette>=1.3.1,<2` — the dep fix shipped
  inside the tag, so there is **no** pip-audit exposure and 0.2.1 is feature work, not a security
  fix. (3) The PyPI name `freeweight` is **not** unclaimed: `freeweight 1.0.0rc1` was published
  2026-08-29 from the rc1 tag by this suite's own release workflow — the name is secured.
  (4) The M6 verification prompt (`m6-verification.prompt.md`) was never executed — **no
  verification report exists**; P-5's subset below stands in for it.

### F-14 — P-4: the two LoadCoach stopgaps — adoption completed
- **Severity:** NOTE (**completed** in `0d9e3c6`, 2026-08-31, after mirrorwall 0.2.1 and
  weightsdb 0.2.1 published)
- **What happened:** both `{% block head %}` stopgaps deleted (`system/index.html` by hand,
  `jobs/detail.html` in the adoption commit); the "Plain links" paragraph folded back into
  `kv_list` as two linked rows via the 0.2.1 `href` item shape; both e2e tests flipped to assert
  the stopgaps *absent* and the decision link rendered inside a `<dd>`; the manual §13 checklist
  entry updated; `requirements/ci.lock` regenerated surgically to `mirrorwall==0.2.1` +
  `weightsdb==0.2.1` (pip-compile on Python 3.13, proven by a clean-venv
  `pip install --require-hashes` + `--no-deps` install on 3.13). Gate green on Python 3.14.4
  under `.venv/bin/pytest`: 807 passed / 2 skipped. The unchanged `>=0.2,<0.3` pins resolve both.

### F-15 — Interpreter drift across local venvs, named per M5C-13
- **Severity:** NOTE
- **What:** BaseAiCore/SetSpec/ModelRack venvs are Python 3.13.15; SweatMeter/WeightsDB/
  MirrorWall/LoadCoach/FreeWeight are 3.14.4. Every gate in this report names its interpreter;
  the CI matrix (3.12/3.13 + 3.14 early-warning) is the arbiter. Workspace `CLAUDE.md` now says
  "a mix of 3.13 and 3.14" instead of the stale "3.13".

## P-5 in detail — the FreeWeight tag decision

No M6 verification report exists (F-13.4), so the highest-risk subset was run directly:

1. **Sandbox refusal**: `tests/security/test_sandbox_refusal.py` + `test_upgrade_from_rc1.py` —
   11 passed. Independent witness check: a file-creating command under a `REFUSED` decision with
   an injected recording runner → `SandboxUnavailable` raised, **no witness file, zero runner
   calls**.
2. **rc1 migration fixture**: `tests/fixtures/databases/freeweight-1.0.0rc1.sqlite3` is in
   `git ls-files` (the gitignored-fixture lesson holds) and the upgrade-from-rc1 test passes
   against the committed copy.
3. **CSRF on a real socket** (uvicorn on 127.0.0.1:8917, curl emulating a browser): forged form
   post (wrong or missing `csrf_token`) → **403**; valid token → **303** to the wizard's next
   step; the `__Host-mw-csrf` cookie carries `Secure; Path=/; HttpOnly; SameSite=Strict`, no
   `Domain`.
4. **M6-17 CI story verified against the runs**: `33361135765` (69e72b0) failure and
   `33363020266` failure with only the `tests` jobs red (3.13 failure, 3.12 cancelled,
   everything else green — consistent with the coverage-source cause, since `tests-314` without
   `--cov` passed); `33364783572` (f45a7a9) success on every job.
5. The M6 deferred set is verified **recorded**: M6-5/PHASE11 #6 (M6_HANDOFF + PHASE11_ISSUES),
   M6-8 (M6_HANDOFF, now also flagged in-product), M6-9 (M6_HANDOFF, the framework seam), M6-12
   (M6_HANDOFF, ADR-0014 trigger), and the PHASE* carried table (M6_HANDOFF §"PHASE*_ISSUES.md
   open items").

**Recommendation: tag `v1.0.0`** at `d468457`. CI run `33370828360` completed green on that
head. F-1 was the kind of defect `TAG_APPROVED: no` existed to catch; it is fixed,
mutation-checked, and the whole gate is green at the new head.

## The outstanding-items ledger

| Item | Bucket | Evidence |
|---|---|---|
| P-1 ModelRack `context_length` | **completed** (`8bb5b3b`, `ce73f74`) + **human step** (tag v0.6.0) | F-11 |
| P-2 WeightsDB 0.2.1 `secure_delete` | **completed** (`57c7824`, `88f7ff5`) + **human step** (tag v0.2.1) | F-5, F-12 |
| P-3 MirrorWall 0.2.1 kv_list link + wrap CSS | **completed** (`d169db5`, `6d50c3f`) + **human step** (tag v0.2.1) | resolves under `>=0.2,<0.3` |
| P-4 downstream adoption of P-2/P-3 | **completed** (`0d9e3c6`; CI green in run `33422721770` after a PyPI-propagation retrigger `18927cb`) | F-14 |
| P-5 FreeWeight tag decision | **completed** (verification subset run; F-1/F-2 fixed) + **human step** (tag v1.0.0 after CI green) | P-5 section |
| P-6 LoadCoach release verification | **completed** — run `33367190485` green, PyPI resolves, clean-venv smoke passed | F-7 |
| M6-5 / PHASE11 #6 `disagreement_rate` | **deferred** — trigger: its own post-1.0 phase with a migration | recorded M6_HANDOFF + PHASE11_ISSUES §6 |
| M6-8 real dataset pins | **deferred** (human with network records true hashes) — now flagged in-product | F-2 |
| M6-9 scheduler dispatch of external suites | **deferred** — trigger: real pins exist (M6-8), then wire `_execute_run_inner` → `run_external_benchmark` + `-m live` e2e | recorded M6_HANDOFF |
| M6-12 token enforcement + failed-auth brake | **deferred** — trigger: ADR-0014 lands token enforcement | recorded M6_HANDOFF |
| PHASE8/11 #19 goal-pack delete backup | **deferred** — post-1.0 small addition | recorded M6_HANDOFF table |
| PHASE11 #7 `source_id` scheme | **deferred by design** — trigger: ADR-0022's second-producer clause | recorded M6_HANDOFF table |
| PHASE10 #1,2,4,6,7 measurement refinements | **deferred** — post-1.0, each surfaces its limitation to the user | recorded M6_HANDOFF table |
| PHASE10 #3, PHASE11 #10 | **completed** in M6 (verified still closed) | M6_HANDOFF |

Nothing dropped.

## C-6 — the two product questions (future-work notes; nothing implemented)

**"How does context get retained between multiple prompt sessions in ModelRack?"** It is not —
by design, and the design is load-bearing. A `GenerationRequest` carries the entire conversation
(`messages`, chat-style) or a single `prompt`, per call; ModelRack holds no session store, and
spec §3 forbids it any cache beyond the TTL'd `MetadataCache`. "Retention" today is the caller's
job: the application re-sends the transcript each turn, and the *provider* (Ollama) keeps the
model resident between calls (`keep_alive`), which preserves load state, not conversation. Two
consequences worth knowing: the served context bounds how much transcript fits — which is exactly
what ADR-0023 §4 and the new `ResidentModel.context_length` (0.6.0) make visible — and a
conversation store, if the suite wants one, belongs in an application (LoadCoach already persists
jobs; a `conversations` table would follow the same ownership rules), with transcripts as
versioned SetSpec payloads, never inside ModelRack.

**"Can I have a local 'chat' between models to pass context and relevant data?"** Nothing
implements it today, and the architecture has a firm opinion on its shape: Python orchestrates,
models never decide control flow. A model-to-model chat is an application-level loop that
alternates `GenerationRequest`s across two identities, appending each reply to the shared
transcript — LoadCoach routes each turn (explainably, per-turn evidence and all), and
IdeaPress's planned stage map (`docs/apps/ideapress/workflows.md`) is the natural home: its
critique/revise stages are already a bounded two-role conversation in the plan. The nearest
existing machinery is FreeWeight's judge sets, where several models each grade the same sample —
parallel, not conversational, deliberately: free-running model dialogue is unbounded and
unvalidated, which the "bounded, validated tasks" rule exists to prevent. Build it as an
IdeaPress workflow with a turn budget, per-turn validation, and the transcript stored with full
provenance; no package changes are needed.

## The human step

Dependency-ordered; each tag triggers that repo's `release.yml` (trusted publishing — never
twine). Watch the run, then confirm PyPI resolution before the next dependent step.

```bash
# 0. Precondition already met: FreeWeight CI on d468457 completed green
#    (run https://github.com/JPKell/FreeWeight/actions/runs/33370828360)

# 1. ModelRack 0.6.0  (no downstream pin resolves it yet — by design, F-11)
cd ~/ai/suite/py/ModelRack
git tag -a v0.6.0 ce73f74 -m "modelrack 0.6.0 — ResidentModel.context_length (ADR-0023 §4 reported served context)"
git push origin v0.6.0
#    watch the Release run in https://github.com/JPKell/ModelRack/actions
#    confirm: pip index versions modelrack   → 0.6.0

# 2. WeightsDB 0.2.1  (resolves under both apps' >=0.2,<0.3 immediately)
cd ~/ai/suite/py/WeightsDB
git tag -a v0.2.1 88f7ff5 -m "weightsdb 0.2.1 — PRAGMA secure_delete=ON on every SQLite connection"
git push origin v0.2.1
#    watch the Release run in https://github.com/JPKell/WeightsDB/actions
#    confirm: pip index versions weightsdb   → 0.2.1

# 3. MirrorWall 0.2.1  (resolves under both apps' >=0.2,<0.3 immediately)
cd ~/ai/suite/py/MirrorWall
git tag -a v0.2.1 6d50c3f -m "mirrorwall 0.2.1 — kv_list link items (safe_href) and .kv-list dd overflow-wrap"
git push origin v0.2.1
#    watch the Release run in https://github.com/JPKell/MirrorWall/actions
#    confirm: pip index versions mirrorwall  → 0.2.1

# 4. FreeWeight v1.0.0  (recommendation flipped to tag — P-5; requires step 0 green)
cd ~/ai/suite/FreeWeight
git tag -a v1.0.0 d468457 -m "freeweight 1.0.0"
git push origin v1.0.0
#    watch the Release run in https://github.com/JPKell/FreeWeight/actions
#    confirm: pip install freeweight==1.0.0 in a clean venv, run one native benchmark,
#             one export (spec §20 AC1) — the acceptance criterion the tag completes

# 5. Adoption (P-4) — after steps 2 and 3 publish; a fresh install already resolves 0.2.1:
cd ~/ai/suite/LoadCoach
#    delete the two stopgap head-blocks (system/index.html:4-9, jobs/detail.html:4-9),
#    fold jobs/detail.html:30-38's link paragraph back into kv_list via the href item shape,
#    update the two e2e tests that assert the stopgaps present, run the full gate, commit.
```

## Cross-suite checks (Pass 3 summary)

- **C-1** workspace `CLAUDE.md` rewritten: state table current (only IdeaPress scaffold), the
  `AiSuite/` path corrected to `docs/` throughout, venv interpreter note updated. Nothing
  normative changed.
- **C-2** pins: all resolve against PyPI today; weightsdb/mirrorwall 0.2.1 resolve under
  existing app pins; modelrack 0.6.0 deliberately does not (F-11). Full table in the finding.
- **C-3** names: no drift — `machine_fingerprint` (63 files), `capability_id` (43), `run_id`
  (27), `metric_key` (66), `pricing_hash` (canonical in baseaicore.cost), `ModelIdentity` (31).
- **C-4** ADR trail: highest is 0037, indexed; every M4/M6 DECISION either has its ADR
  (M5C-7→0037) or demonstrably needs none (phase sequencing, implementation choices within
  existing ADRs — reasoning per entry in the findings). No new ADR was required.
- **C-5** demos: all four ran green from the workspace root against their venvs.
- **C-6** answered above.
- **C-7** docs repo clean and pushed at `63314fa`; every canonical edit mirrored and proven
  identical by `cmp`.
