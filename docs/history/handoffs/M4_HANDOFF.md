# M4 Handoff — Sonnet run (LoadCoach P1–P2, WeightsDB P1–P3, setspec.prompts)

Run started 2026-08-29. This file is written for the Opus run that starts P3 next; read it before
starting.

---

## LoadCoach P1

Covers both halves of Unit 1: the WeightsDB P1–P2 extraction (`py/WeightsDB`) and LoadCoach's own
Phase 1 (`LoadCoach`). Both gates are green (ruff format/check, mypy strict, lint-imports, pytest;
SQLite exercised, PostgreSQL skips locally as expected). Both repos committed.

### LC1 — Five scaffold tooling configs were silently broken
- **Severity:** NOTE
- **Unit:** LoadCoach P1
- **Where:** `py/WeightsDB/.importlinter`, `LoadCoach/.importlinter`, `LoadCoach/pyproject.toml`
- **What happened:** The generated scaffolds had four gate-blocking bugs, none caught before this
  run because nothing had ever been implemented enough to run the gate (the entry's title said
  "four" while listing five; corrected):
  1. `.importlinter` used `root_packages = <name>` (plural). Import-linter 2.x only auto-listifies
     the singular `root_package` key; given the plural key with a bare string value, it iterates
     the string *character by character* (`Could not find package 'w'`). Fixed to `root_package`
     in both `py/WeightsDB/.importlinter` and `LoadCoach/.importlinter`.
  2. Both `.importlinter` files were missing `include_external_packages = True` under
     `[importlinter]`, required whenever a `forbidden` contract names modules outside the root
     package (both do — `freeweight`, `ideapress`, `modelrack`, etc.). Added to both.
  3. `LoadCoach/.importlinter`'s `layers` contract listed `loadcoach.web`, `loadcoach.cli`, …
     *and* set `containers = loadcoach` — the layers list must be container-relative (`web`,
     `cli`, …) when `containers` is given, or import-linter looks for the double-prefixed
     `loadcoach.loadcoach.cli` and fails with "Missing layer". Fixed to bare names, matching
     FreeWeight's own `.importlinter`.
  4. `LoadCoach/pyproject.toml`'s `[tool.mypy]` was missing `mypy_path = "src"` and
     `explicit_package_bases = true` (FreeWeight's has both). Without them, mypy treats every
     `.py` file under `src/loadcoach/**` as a top-level module by basename alone, and two
     same-named files in different subpackages (`services/models.py` vs
     `infrastructure/db/models.py`) collide (`Duplicate module named "models"`). Added both keys.
  5. `LoadCoach/pyproject.toml` was missing the per-file-ignore that exempts
     `infrastructure/db/migrations/versions/*.py` from the `D1` (docstring) rules — FreeWeight's
     has this for the identical reason (Alembic-generated `upgrade()`/`downgrade()` carry no
     hand-written behaviour). Added.
- **What the next run must do:** Nothing — all four are fixed and the gate is green in both repos.
  Worth knowing if a *third* scaffold (IdeaPress, MirrorWall) is started from the same generator:
  check its `.importlinter` and `[tool.mypy]` for the same five gaps before assuming the gate runs
  at all.

- **Resolved by the P3–P4 run:** Applied the closing advice to MirrorWall's scaffold, which had four of the five defects (plural `root_packages`, no `include_external_packages`, no `mypy_path`/`explicit_package_bases`) plus an 85% coverage floor. All fixed — see LCX10. IdeaPress is the remaining scaffold and is untouched.

- **Resolved by the handoff-review run:** IdeaPress is done too, and it had **all five** plus a sixth the earlier scaffolds did not have — see HR1. No scaffold now carries these defects.

### LC2 — weightsdb shipped with no `py.typed` marker
- **Severity:** NOTE
- **Unit:** LoadCoach P1
- **Where:** `py/WeightsDB/src/weightsdb/py.typed` (new, empty file, PEP 561)
- **What happened:** LoadCoach's `mypy src tests` reported every `weightsdb` import as
  `import-untyped` ("missing library stubs or py.typed marker") the moment WeightsDB became a real
  dependency instead of an empty scaffold. `baseaicore`, by contrast, already ships one. Added the
  empty marker file; `hatchling`'s default wheel build includes it with no other config change
  needed (confirmed via the editable install LoadCoach's venv already uses).
- **What the next run must do:** Nothing further for this repo. Worth a one-line mention in
  WeightsDB's own release notes/quickstart (P3) so an external consumer installing `weightsdb`
  from a wheel gets typed imports too — I did not add this to the quickstart since P3 had not
  started yet when this was found.

- **Resolved by the handoff-review run:** Written. `docs/quickstart.md`'s Install section now
  says the marker ships, and `tests/contract/test_public_api.py` asserts the file is there, so
  a packaging change that dropped it fails CI instead of surfacing in a consumer's mypy run.

### LC3 — StorageFull naming: spec §7 vs §13 disagree
- **Severity:** DECISION
- **Unit:** LoadCoach P1
- **Where:** `py/WeightsDB/src/weightsdb/errors.py`
- **What happened:** `docs/packages/weightsdb/spec.md` §7's error-tree code block lists
  `STORAGE_FULL` as one of the six codes but only draws five subclasses under `DatabaseError`
  (`StorageFull` is missing from the tree itself); §13's error-behaviour table calls the same
  condition `StorageError (STORAGE_FULL)` — a third, different class name. FreeWeight's own
  (proven, tested) implementation names it `StorageFull` with `code = "STORAGE_FULL"`, and P2's
  backup disk-full test needs *some* concrete class. Kept FreeWeight's name, `StorageFull`,
  reasoning that the moved, working code and §7's code list (which agrees on `STORAGE_FULL`) both
  outweigh §13's apparently inconsistent prose name.
- **What the next run must do:** Nothing — `StorageFull` is implemented, exported, and covered by
  `tests/integration/test_backup_restore.py::test_disk_full_during_backup_removes_partial_file_and_raises`.
  If §13 is ever corrected, no code change follows either way since `StorageError` was never used.

### LC4 — `transaction()` and `session_scope()` shape, generalized beyond FreeWeight
- **Severity:** DECISION
- **Unit:** LoadCoach P1
- **Where:** `py/WeightsDB/src/weightsdb/session.py`
- **What happened:** Spec §7's Public API block gives `session_scope(factory)` with **no**
  `read_only` parameter (FreeWeight's version has one) and a **new** `transaction(session, *,
  immediate=True)` context manager with no parameter for commit/rollback. Read this as: read-only
  declaration moved out of `session_scope` (now purely lifecycle: commit/rollback/close) and into
  `transaction()`, which only declares the SQLite `BEGIN IMMEDIATE` vs. deferred `BEGIN` and is
  meant to nest inside a `session_scope` block (`with session_scope(factory) as s, transaction(s,
  immediate=False): ...`). Also read spec §18's "nested use rejected" test-list line (which sits
  under a "Session scope" row, not a separate "Transactions" row) as applying to `transaction()`
  specifically — `session_scope(factory)` always builds a fresh `Session` from the factory, so
  nesting cannot occur at that layer at all; `transaction()` is the construct that can genuinely be
  entered twice on one already-open session, and does now raise `DatabaseError` if it is.
- **What the next run must do:** Nothing blocking. If a future phase's spec text clarifies this
  differently, `weightsdb.session` is the only file to revisit; `LoadCoach/services/database.py`'s
  `Database.read()`/`Database.write()` are the only current callers and would need a matching edit.

- **Resolved by the P3–P4 run:** Checked against what routing and execution need and kept unchanged. `Database.read()`'s read-only enforcement holds for every routing query, and `write()`'s one-unit-of-work shape is what makes a decision and its candidates, or a job and its attempts, land atomically. No edit to `weightsdb.session` was needed.

### LC5 — `migration_harness` shape invented beyond the one-line spec signature
- **Severity:** DECISION
- **Unit:** LoadCoach P1
- **Where:** `py/WeightsDB/src/weightsdb/testing.py` (`MigrationHarness`, `migration_harness`)
- **What happened:** Spec §7 gives only `migration_harness(script_location, metadata) ->
  MigrationHarness` with no further detail. Built `MigrationHarness` as a small dataclass bundling
  both arguments, with `.sqlite()`/`.postgres()` context managers that each combine
  `temporary_sqlite()`/`temporary_postgres()` with a bound `MigrationRunner` — removing the
  boilerplate an application's own migration tests would otherwise repeat. Not yet exercised by a
  real consumer (LoadCoach's own migration tests use `MigrationRunner` directly, not this helper,
  since P1 predates it being obviously more convenient than the four-line manual equivalent).
- **What the next run must do:** When LoadCoach P2+ or FreeWeight P12 writes its next migration
  test, consider using `migration_harness` instead of `MigrationRunner` directly, and adjust its
  shape then if real usage reveals the wrong one — nothing is frozen by a golden here.

- **Resolved by the P3–P4 run:** Still unused. LoadCoach's migration tests were rewritten this run (LCX1) for an unrelated reason — a hard-coded head revision — and continue to drive `MigrationRunner` directly, so real usage still has not shaped `migration_harness`.

- **Resolved by the handoff-review run:** Now exercised, though by WeightsDB's own suite rather than by a downstream consumer. `tests/integration/test_migrations.py` drives a full upgrade and a `check_parity` through `migration_harness(...).sqlite()`, and asserts each block gets an independent database. The shape held up unchanged under first use; LC5's advice for a real consumer still stands.

### LC6 — SQLite `StorageBusy` translation added; FreeWeight's version never had it
- **Severity:** NOTE
- **Unit:** LoadCoach P1
- **Where:** `py/WeightsDB/src/weightsdb/engine.py` (`_raise_if_busy`)
- **What happened:** Spec §13 requires `SQLITE_BUSY` beyond `busy_timeout` to raise the typed
  `StorageBusy`. FreeWeight's original `_on_begin` event hook just let `BEGIN IMMEDIATE`'s raw
  `sqlite3.OperationalError` propagate — a gap invisible with one consumer and no test for it.
  Added translation (checking `sqlite3.SQLITE_BUSY`/`SQLITE_BUSY_SNAPSHOT` via the DBAPI
  exception's `.sqlite_errorcode`) on both the writer and read-only `BEGIN` paths. Covered by
  `tests/unit/test_engine.py::test_sqlite_busy_timeout_raises_storage_busy`.
- **What the next run must do:** Nothing. Worth knowing if FreeWeight P12 adopts WeightsDB and
  its own tests assumed a raw `OperationalError` on contention somewhere — they would now see
  `StorageBusy` instead, which is the documented, intended behaviour change.

### LC7 — Two-schemas proof uses a synthetic stand-in, not the real `freeweight` package
- **Severity:** DECISION
- **Unit:** LoadCoach P1
- **Where:** `LoadCoach/tests/integration/test_migrations.py`,
  `LoadCoach/tests/integration/_other_app_fixture/**`
- **What happened:** The plan's own risk note asks for "an integration test running FreeWeight's
  schema and LoadCoach's side by side." `freeweight` cannot be installed into `LoadCoach/.venv`
  for this: FreeWeight pins `setspec>=0.3,<0.4`; this repository pins `setspec>=0.4,<0.5`; and
  SetSpec P5 (elsewhere in this same run) upgrades `LoadCoach/.venv`'s own `setspec` to `0.4.0`,
  which would make a co-installed FreeWeight's pin unsatisfiable in the same environment even if
  today's versions briefly overlapped at `0.3.0`. Built a small local stand-in schema/migration
  history instead (one table, one revision) and proved the specific property the risk note names:
  two independent Alembic histories, distinct `version_table`s, one physical SQLite file, no
  collision, `MigrationRunner.is_at_head()` true for both. `check_parity` is deliberately **not**
  asserted in that test — it diffs the whole live schema against one metadata object, and a
  shared physical file is itself off the ADR-0006/database-standards §1 happy path, so a "drift"
  result there would be correct-but-misleading, not a bug.
- **What the next run must do:** If FreeWeight P12 (WeightsDB adoption) ever needs a *real*
  cross-repo migration test, it belongs in FreeWeight's own test suite (which can depend on
  `weightsdb` freely) or as a standalone script run outside either venv — not inside
  `LoadCoach/.venv`, for the reason above.

- **Resolved by the P6 run:** Closed, and the stand-in is no longer the only proof. P6's I4 demonstration ran the *real* FreeWeight (1.0.0rc1, its own venv, its own `freeweight.sqlite3`) beside LoadCoach over HTTP; `/proc/<pid>/fd` shows each process holding only its own database, and neither venv can import the other's package. The synthetic two-schemas test stays as the cheap regression; the real proof is now the demonstration in the P6 section below.

### LC8 — `queue.lease_seconds` validator boundary loosened from `>` to `>=`
- **Severity:** DECISION
- **Unit:** LoadCoach P1
- **Where:** `LoadCoach/src/loadcoach/config.py` (`QueueSettings._check_lease_renewal_margin`)
- **What happened:** Spec §12's shipped example values are `lease_seconds = 60`,
  `lease_renewal_interval_seconds = 20` — exactly `3×`, not strictly more than `3×`. A strict `>`
  reading of "must exceed 3x this" (the spec's own words) makes the documented zero-configuration
  defaults fail `Settings` validation, which contradicts spec §20 AC1 ("starts with zero
  configuration"). Implemented the boundary as `lease_seconds < 3 × interval` refused (i.e. `>=`
  accepted), so the shipped defaults validate.
- **What the next run must do:** Nothing blocking P2. When Phase 5 (queue) is implemented and the
  "+ slack" language in the spec comment gets a concrete meaning, revisit whether `>=` is still
  the right boundary or whether the *defaults* should change instead (e.g. `lease_seconds = 61`).

- **Resolved by the P5 run:** Settled at `>=`. The keeper runs on the scheduler thread, which ticks every `poll_interval_ms` (250 ms) and renews as soon as `lease_renewal_interval_seconds` have elapsed, so a renewal is late by at most one tick; at exactly 3x a lease survives two consecutive missed renewals and is lost only when the scheduler has stalled for more than 2x the interval — the condition a lease exists to detect. The validator's docstring says this in one paragraph and `test_queue_lease_margin_exactly_three_times_is_accepted` pins it.

### LC9 — Forced files beyond the literal Phase 1 file list
- **Severity:** NOTE
- **Unit:** LoadCoach P1
- **Where:** `LoadCoach/src/loadcoach/services/{database,health}.py`,
  `LoadCoach/src/loadcoach/infrastructure/providers/factory.py`,
  `LoadCoach/src/loadcoach/observability/logging.py`,
  `LoadCoach/tests/unit/{test_config,test_health,test_cli}.py`
- **What happened:** The plan's Phase 1 "Files/subsystems" list names
  `{__main__,__about__,config,bootstrap}.py`, `infrastructure/db/{models,repositories/*,
  migrations/**}.py`, `web/{app,routes/system}.py`, `cli/{main,commands/{system,config,db}}.py`,
  and the two named test files. Five more files were required by the Phase 1 **Work** item's own
  text or by its acceptance criteria and had no other legal home under `.importlinter`'s layering:
  `services/database.py` and `services/health.py` (CLI and web must not import each other, so
  logic both need — migration/status/health-report building — has to live in `services/`, and
  neither scaffold file existed before this run); `infrastructure/providers/factory.py` (AC1,
  "reports degraded health with no provider," needs a provider to report on); and
  `observability/logging.py` (the Work item names "logging" alongside settings/request-IDs/health
  as a first-phase requirement, mirroring FreeWeight's own module at the same point in its
  sequence). The three `tests/unit/*.py` files exist because the Phase 1 **Tests** line explicitly
  requires "Config precedence and refusals; health shape; CLI exit codes," and no file in the
  literal list is a natural home for them.
- **What the next run must do:** Nothing — treat these as part of Phase 1's real surface. `db.py`
  intentionally has no `vacuum` command: unlike FreeWeight, LoadCoach's own CLI list (spec §7.2)
  never lists `loadcoach db vacuum`, so it was not built.

### LC10 — `redact_url()` misused on an arbitrary exception message (fixed)
- **Severity:** NOTE
- **Unit:** LoadCoach P1
- **Where:** `LoadCoach/src/loadcoach/services/database.py` (`ensure_ready`, `get_status`)
- **What happened:** Both functions' generic `except Exception as exc` handlers wrapped
  `str(exc)` in `weightsdb.redact_url()` before embedding it in a `DatabaseUnavailable` message —
  written during Phase 1 by analogy with the real requirement (spec §14: no credential in any
  error). `redact_url()` parses its argument as a SQLAlchemy URL; a generic exception's message is
  not necessarily one (e.g. `"simulated connection failure"`), so `redact_url()` itself raised
  `ArgumentError` and replaced the original, useful error with a confusing unrelated one. Found
  while writing WeightsDB P3's health tests, which exercise the identical pattern in
  `weightsdb.health.database_health()` and hit the same crash. Fixed in both places by simply
  using `str(exc)` unredacted — matching FreeWeight's own original, proven code at this exact spot,
  which never redacted the exception text either. Redaction still happens everywhere a URL
  specifically is being formatted (`MigrationRunner._connection_config`'s
  `render_as_string(hide_password=True)`, etc.) — this was only ever wrong on the
  exception-message path.
- **What the next run must do:** Nothing — both sites are fixed and covered (WeightsDB's
  `test_health_unreachable_database_is_unavailable_not_raised`). If a new call site is tempted to
  redact an exception message "for safety," don't — `redact_url()` is for URLs, not arbitrary text.

---

## WeightsDB P3

Covers WeightsDB's own Phase 3 (`health.py`, network-filesystem detection, performance tests,
docs, release prep) plus the cross-cutting piece Unit 2 exists for: LoadCoach's health endpoint
now builds its `database` component entirely from `weightsdb.database_health()`. Gate green in
both repos (ruff format/check, mypy strict, lint-imports, pytest; performance tests written and
spot-checked at small scale but not run at full 1 GB scale — they're `-m performance`, excluded by
the default gate the same as everywhere else in the suite). Both repos committed.

### WDB1 — `database_health()`'s low-disk and stale-backup thresholds are fixed constants
- **Severity:** DECISION
- **Unit:** WeightsDB P3
- **Where:** `py/WeightsDB/src/weightsdb/health.py` (`_LOW_DISK_FLOOR_BYTES`,
  `_STALE_BACKUP_AFTER_SECONDS`)
- **What happened:** Spec §7's signature is `database_health(engine, runner=None) ->
  DatabaseHealth` — no threshold parameters — yet the Phase 3 test list requires the function's
  *output* to distinguish "low disk" and "stale backup" as degraded conditions. Since WeightsDB
  reads no configuration (spec §12), implemented both as fixed, documented module constants: low
  disk below 100 MiB free; stale backup older than 7 days. An application wanting a different bar
  reports its own raw values from the fields `database_health()` already returns
  (`free_space_bytes`, `last_backup_age_seconds`) rather than calling this function for that
  judgement. No backup found at all (fresh install, nothing ever backed up) is reported as
  `last_backup_age_seconds=None` and is **not** treated as degraded — "not yet measured" stays
  distinguishable from "measurably stale," the same distinction ADR-0016 makes for measurements
  generally.
- **What the next run must do:** Nothing blocking. If a real deployment's disk or backup-age
  tolerance ever needs to differ from these two constants, that is a sign the threshold belongs in
  the calling application's own settings instead — don't add parameters to this function without
  revisiting spec §7's frozen signature first.

### WDB2 — `is_network_filesystem`: Linux-only, injectable mount table
- **Severity:** NOTE
- **Unit:** WeightsDB P3
- **Where:** `py/WeightsDB/src/weightsdb/health.py` (`is_network_filesystem`, `_read_proc_mounts`)
- **What happened:** Reads `/proc/mounts`, longest-prefix-matches the given path's ancestry
  against the mount table, and checks the filesystem type against a fixed list of network types
  (`nfs`, `nfs4`, `cifs`, `smb`/`smb2`, `9p`, `afs`, `glusterfs`, `ceph`, …). Returns `None`
  (undetermined, not "no") on any platform without a readable `/proc/mounts` — this is the Linux
  tier-1 mechanism the spec's cross-platform section (§16) itself only promises "where possible."
  The `mounts` parameter accepts an injected table directly (a list of `(mount_point, fs_type)`
  pairs) rather than requiring a filesystem mock, which is what spec §18's "mocked mount table"
  test requirement asks for.
- **What the next run must do:** Nothing for this suite (Linux is the only tier-1 platform per
  every spec in this repo). If a future phase needs macOS/Windows detection, that's new code
  behind the same `bool | None` return contract, not a change to this function's behaviour on
  Linux.

### WDB3 — Release prepared, not published
- **Severity:** NOTE
- **Unit:** WeightsDB P3
- **Where:** `py/WeightsDB/CHANGELOG.md`, `py/WeightsDB/src/weightsdb/__about__.py`,
  `py/WeightsDB/README.md`
- **What happened:** Per this run's instructions, stopped short of the actual publish step.
  `__about__.py` already read `0.2.0` from the start of this run (set correctly by whoever
  generated the scaffold); `CHANGELOG.md` now has a dated `## [0.2.0] — 2026-08-29` section
  (moved out of `Unreleased`) listing all three phases; `README.md`'s status line and doc table
  point at the new `docs/quickstart.md` and `docs/adoption-checklist.md`. No tag was created, no
  `git push`, no `twine upload` — none were attempted.
- **What the next run must do:** Follow packaging-and-release-standards.md §6 from step 4
  onward (open the release PR, tag `v0.2.0`, let `release.yml` publish via Trusted Publishing) —
  a human decision, not something to automate from inside a coding run.

- **Resolved by the P6 run:** **Still unpublished, and now blocking.** `pip index versions weightsdb` reports no distribution and the repository carries no tag. Because `loadcoach` declares `weightsdb>=0.2,<0.3` as a runtime dependency, `pip install .` fails in a fresh virtualenv and `requirements/ci.lock` cannot be generated. This entry's step-4-onward advice is now the highest-priority action in the suite; see P6-9.

### WDB4 — `docs/adoption-checklist.md`'s `types.py` shim recommendation is unverified against real FreeWeight code
- **Severity:** NOTE
- **Unit:** WeightsDB P3
- **Where:** `py/WeightsDB/docs/adoption-checklist.md` §2
- **What happened:** The checklist recommends FreeWeight keep `infrastructure/db/types.py` as a
  thin re-export shim rather than deleting it outright, because every existing Alembic revision
  file references `freeweight.infrastructure.db.types.UtcDateTime`/`PortableJSON` by that import
  path and deleting the module would break the whole migration history at import time. This
  reasoning is sound from having read FreeWeight's `migrations/versions/0001_initial_schema.py`
  directly (Unit 1's research), but this run never touched FreeWeight's repository ("do not modify
  FreeWeight for any other reason during this run" — instruction honored), so the checklist's
  specific claim about *every* revision file, not just the one read, is inferred rather than
  grepped.
- **What the next run must do:** When FreeWeight P12 actually starts, `grep -rn
  "infrastructure.db.types" FreeWeight/src/freeweight/infrastructure/db/migrations/versions/`
  first, to confirm the shim recommendation covers every revision file (there are seven per Unit
  1's research: `0001`–`0007`) before deleting anything.

- **Resolved by the handoff-review run:** Grepped, and the inference was right: all seven
  revisions, `0001_initial_schema` through `0007_capability_evidence`, carry
  `import freeweight.infrastructure.db.types` — none is exempt. `docs/adoption-checklist.md` §2
  now records this as verified rather than inferred, and tells the next reader to re-run the grep
  in case a revision was added after the check. FreeWeight itself was not modified.

---

## LoadCoach P2

Gate green (ruff format/check, mypy strict, lint-imports, pytest — 83 passed, 2 skipped for
postgres). Committed.

### LC11 — The fifteen shipped task profiles' weights/constraints are authored, not transcribed
- **Severity:** DECISION
- **Unit:** LoadCoach P2
- **Where:** `LoadCoach/src/loadcoach/config/task_profiles.toml`
- **What happened:** routing.md §2 gives the full schema and one complete worked example
  (`code.review`), names all fifteen profile IDs, and states which four capabilities
  `content.review` is weighted on — nothing else about weights, constraints or execution
  parameters for the other fourteen. Authored all fifteen (weights summing to 1.0, using only
  capabilities in SetSpec's 1.1 vocabulary; constraints and execution parameters chosen by
  analogy with `code.review`'s worked example and each profile's evident purpose).
  `content.review`'s weights use exactly the four capabilities routing.md §2 names (auditing,
  instruction_following, reasoning, structured_output); every other profile's specific weight
  values are a judgment call, not a transcription. Five profiles use
  `response_format="json_schema"` and reference a schema file under `config/schemas/`, also
  authored here (`code_review_findings.json`, `code_debug_findings.json`,
  `content_review_findings.json`, `fact_check_findings.json`, `structured_extract.json`).
- **What the next run must do:** When Phase 3 (routing) or Phase 7 (feedback/reliability) starts
  exercising these profiles against real traffic, the specific weight values are the first thing
  worth revisiting against production evidence — they are internally consistent and validated,
  not empirically tuned. `code.review`'s values are the one profile taken verbatim from the spec
  and should be treated as more authoritative than the other fourteen.

- **Resolved by the P3–P4 run:** Used as-is, and now load-bearing: these weights are what P3 ranks candidates on. `code.review`'s spec-verbatim values are exercised by the structured-output and corrective-retry tests. The other fourteen are still authored rather than tuned — which every decision now discloses through the `low_evidence` flag, since no measured evidence exists to meet the present-weight floor.

### LC12 — Declared-capability translation: only TOOLS and STRUCTURED_OUTPUT map to SetSpec
- **Severity:** DECISION
- **Unit:** LoadCoach P2
- **Where:** `LoadCoach/src/loadcoach/domain/registry.py` (`_FLAG_TO_CAPABILITY`)
- **What happened:** `baseaicore.ModelCapabilityFlag` has five members (TOOLS, VISION, THINKING,
  STRUCTURED_OUTPUT, EMBEDDING); SetSpec's capability vocabulary (1.1) has twenty-one entries with
  no `vision`, `thinking` or `embedding` among them. Rather than invent a mapping (e.g. THINKING →
  `reasoning`, which would silently overstate what a binary "the provider says this model can
  think" flag actually establishes about measured reasoning quality), only the two flags with an
  honest, unambiguous counterpart are translated: TOOLS → `tool_use`, STRUCTURED_OUTPUT →
  `structured_output`. A model declaring VISION/THINKING/EMBEDDING simply gets no row for those —
  this is the mechanism dev-plan P2's "fewer flags, honestly reported" test line is asking for,
  generalized to "fewer *mapped* flags," not just fewer flags overall.
- **What the next run must do:** Nothing blocking. If a future SetSpec vocabulary version adds
  `vision`/`multimodal` or similar, extend `_FLAG_TO_CAPABILITY` then — don't backfill a mapping
  against the current 1.1 vocabulary, which genuinely has no matching entry.

- **Resolved by the P3–P4 run:** Checked and kept, and it turned out to matter more than expected. `capability_unsupported` is evaluated against exactly the two mapped capabilities, so a profile requiring `tool_use` or `structured_output` filters correctly while a profile naming a capability with no provider flag is not rejected on the strength of a mapping nobody could justify.

- **Resolved by the P6 run:** Checked and kept, unchanged. P6 adds a second, independent source of capability rows — imported `capability_evidence` — and the two do not interact: `_FLAG_TO_CAPABILITY` still decides which *declared* flags get a row, and evidence arrives with its own `capability_id` from FreeWeight's vocabulary. A `vision` or `thinking` flag still gets no row, and now that measured evidence exists the absence is even more clearly right: a binary provider flag is not a measurement.

### LC13 — Manual capability scores: mechanism built, shipped empty
- **Severity:** NOTE
- **Unit:** LoadCoach P2
- **Where:** `LoadCoach/src/loadcoach/config/manual_capability_scores.toml`,
  `LoadCoach/src/loadcoach/domain/registry.py` (`validate_manual_score`),
  `LoadCoach/src/loadcoach/services/models.py` (`import_manual_capability_scores`)
- **What happened:** The Work item's third bullet ("Manual capability scores from configuration,
  marked `source: manual`") names no file, no schema and no CLI surface anywhere in the docs read
  for this unit — genuinely undocumented beyond the one sentence. Built the mechanism: an optional
  TOML file (`[[scores]]` entries: `canonical_id`, `capability_id`, `score`, `confidence`),
  validated the same way task profiles are (unknown capability named and rejected, not silently
  dropped), imported at bootstrap after model discovery (a score naming an undiscovered model is
  skipped, not an error — discovery order isn't guaranteed). Shipped with **no scores** — the
  suite has no benchmark-independent judgment to assert on anyone's behalf, so the file exists
  only as a mechanism an operator can use, matching FreeWeight's own precedent of never shipping
  fabricated data.
- **What the next run must do:** Nothing blocking. No CLI command was added for this (no
  `loadcoach scores add`-type command) — an operator edits the TOML file directly today. If that
  proves painful, adding one is a natural, small Phase 3+ addition, not a Phase 2 gap.

- **Resolved by the P3–P4 run:** Used. `source="manual"` sits third in scoring's precedence (benchmark, production, manual, declared, band prior) and is covered by unit tests; `require_evidence` excludes it along with the other priors, per routing §10 (LCX5). The shipped file is still empty, which is still the honest state.

- **Resolved by the P6 run:** Still third in precedence, still shipped empty, and now demonstrably subordinate: `resolve_capability`'s order is benchmark, production, manual, declared, band prior, so a single imported measurement outranks any manual score. Re-read against routing §5/§5.1 as the prompt asked (see LCX5) and confirmed correct.

### LC14 — `tasks list`/`tasks show` read an empty table without `serve` ever having run (fixed)
- **Severity:** NOTE
- **Unit:** LoadCoach P2
- **Where:** `LoadCoach/src/loadcoach/cli/commands/tasks.py` (`_ensure_imported`)
- **What happened:** Task profile import (validate the shipped TOML, upsert into `task_profiles`)
  originally happened only inside `bootstrap()` — which `loadcoach serve` calls but the standalone
  `tasks list`/`tasks show` CLI commands do not (they open a database handle directly, matching
  `db.py`'s and `models.py`'s established pattern, deliberately independent of the web layer).
  Caught by hand-testing the CLI end to end after the automated suite (which always runs through
  `bootstrap()` via `TestClient`, so it never exercised the standalone-CLI-before-first-`serve`
  path): a fresh install that ran `loadcoach db upgrade` then `loadcoach tasks list`, without ever
  starting the server, saw an empty list and `tasks show general.chat` reported
  `TASK_PROFILE_NOT_FOUND` — for data that is shipped in the repository and should always be
  visible. Fixed by having both commands import (idempotent upsert) before reading, so they are
  correct regardless of whether `serve` has ever run. Deliberately **not** applied to `models
  list`/`models show`: an empty model list before any discovery has run is an honest state (no
  provider has been asked yet), not a bug the way an empty *shipped* task-profile list is.
- **What the next run must do:** Nothing — both commands are fixed and covered
  (`tests/unit/test_cli.py` exercises `db`/`config`/system commands through `TestClient`-adjacent
  paths, but the fresh-install-CLI-before-serve gap specifically was caught by manual testing, not
  the automated suite; worth adding an automated regression test for this exact sequence — `db
  upgrade` then `tasks list` with no prior `serve` — if this module is revisited).

- **Resolved by the P3–P4 run:** The same pattern was reused for `loadcoach route explain`, which imports the shipped profiles before routing so a fresh install can explain a decision without `serve` having run.

- **Resolved by the handoff-review run:** The automated regression test this entry asked for is written: `tests/unit/test_cli.py` now runs `db upgrade` then `tasks list`/`tasks show` with no prior `serve`, asserts the import is idempotent across invocations, and asserts the deliberate asymmetry that `models list` is legitimately empty on a fresh install. Mutation-checked — reverting `_ensure_imported` to a no-op fails two of the three.

### LC15 — `/models/{id}` and `/task-profiles/{id}` detail routes not built
- **Severity:** DEFERRED
- **Unit:** LoadCoach P2
- **Where:** N/A — not implemented
- **What happened:** `docs/apps/loadcoach/api.md` §2's table lists `GET /models/{model_ref}` and
  `GET /task-profiles/{id}` alongside the collection GETs, but dev-plan P2's own Work item text
  says only "`GET /models`, `GET /task-profiles`" (plural, collection forms). Built exactly those
  two, plus their CLI equivalents' `show` subcommands (`models show <canonical_id>`, `tasks show
  <profile_id>`), which cover the same lookup need from the CLI side without a dedicated HTTP
  route.
- **What the next run must do:** Add `GET /models/{model_ref}` (note ADR-0024: keyed by ULID or
  an unambiguous prefix, **not** the canonical ID, which contains `/`, `:` and `@` and does not
  survive a path segment) and `GET /task-profiles/{id}` whenever a consumer actually needs
  single-item HTTP lookup rather than filtering the collection response client-side — likely
  natural to add alongside Phase 3's routing work, which will want to link an explanation back to
  the specific model and profile it scored.

- **Resolved by the P3–P4 run:** Left deferred. P3's own Work item and file list name neither route. What P3 actually needed was a read path for a stored *decision*, which is `GET /api/v1/routing-decisions/{id}` (LCX3) — and P4's `jobs` table now gives `GET /jobs/{id}/explanation` a home for P5.

- **Resolved by the P6 run:** **Left deferred, deliberately, and this is the decision the prompt asked for.** The Benchmarks page needs neither route: it renders coverage per capability and the records themselves, and links to nothing by ID. `GET /evidence` filters by `model=<canonical_id>` and by `capability`, which covers every lookup the page and the CLI make. `GET /models/{ref}` and `GET /task-profiles/{id}` remain unbuilt because no consumer needs single-item HTTP lookup yet; ADR-0024's ULID-or-prefix keying note still applies whenever one does.

### LC16 — `models residency` CLI command not built
- **Severity:** DEFERRED
- **Unit:** LoadCoach P2
- **Where:** N/A — not implemented
- **What happened:** Full spec §7.2 lists `loadcoach models list|show|refresh|residency`; dev-plan
  P2's Work item only asks for discovery, the registry and availability tracking — nothing about
  which models are currently resident in GPU memory. Residency tracking has no home in the P1
  schema either beyond the standalone `residency` table named in spec §10 (not part of migration
  `0001`, which P1's own Work item lists as `models, model_capabilities, runtime_profiles,
  task_profiles, settings, api_tokens` — no `residency`). Built `models list|show|refresh` only.
- **What the next run must do:** `residency` almost certainly belongs with Phase 4 (execution,
  where residency state actually changes) per the model-assignment table's own phase grouping.
  Add the `residency` table in that phase's migration and `models residency` then, not by
  retrofitting migration `0001`.

- **Resolved by the P3–P4 run:** Left deferred, and the guess about its home is confirmed: P4's Work item does not name it, and residency state does not change until something tracks a model being loaded. It belongs with the `residency` table in P5/P6.

---

- **Resolved by the P5 run:** Built. Migration `0004` adds the `residency` table (per-device episodes with the `vram_bytes` measurement pair), `services/residency.py` writes it, and `loadcoach models residency [--json]` reads it through the same `residency_rows` the Queue page and `GET /queue` use.

- **Resolved by the M5 run:** The Models page and `GET /models` now read residency (`resident`, `gpu_indexes`) through the same `residency` rows `models residency` reads, beside the evidence summary and reliability api.md §2 names.

## SetSpec P5

Gate green (ruff format/check, mypy strict, lint-imports, pytest — 802 passed, 2 skipped).
Committed. Independent of Units 1–3 by design; would have been done even if those had collapsed.

### SS1 — FreeWeight's own P12 (WeightsDB-style adoption of `setspec.prompts`) was pulled forward into this unit
- **Severity:** NOTE
- **Unit:** SetSpec P5
- **Where:** `FreeWeight/src/freeweight/services/prompts.py`, `FreeWeight/pyproject.toml`,
  `FreeWeight/tests/security/test_goal_pack_import.py`, `FreeWeight/CHANGELOG.md`
- **What happened:** P5's Work item says to write "the adoption checklist FreeWeight P12
  follows" — future tense, for a phase that hadn't started. Once `setspec.prompts` existed and the
  golden-hash proof (SS3 below) showed the move was safe, doing the adoption itself in the same
  change was strictly less work than writing a prospective checklist for behaviour no one had
  exercised yet, and it is the scenario this run's own instructions name as the **one** sanctioned
  reason to touch FreeWeight ("SetSpec P5 ... FreeWeight is released at 1.0.0rc1 ... Do not modify
  FreeWeight for any other reason during this run"). `docs/prompts-adoption-checklist.md` (SS2) is
  therefore written as a checklist *and* a completed worked example, not a checklist for a change
  that hasn't happened.
- **What the next run must do:** Nothing for FreeWeight's prompts module — it is done, verified,
  and FreeWeight's own full gate passed unchanged (2297 passed, 28 skipped, 21 deselected). If
  FreeWeight's development plan still lists a P12 phase for this specific work, close it there as
  already-done-early rather than re-doing it.

### SS2 — `load_pack(root)` made required; no default in the shared package
- **Severity:** DECISION
- **Unit:** SetSpec P5
- **Where:** `py/SetSpec/src/setspec/prompts.py` (`load_pack`),
  `FreeWeight/src/freeweight/services/prompts.py` (thin wrapper restoring the old default)
- **What happened:** FreeWeight's original `load_pack(root: Path = PACK_ROOT, ...)` defaulted to
  its own `services/prompts.py`-relative path — an opinion `setspec` cannot share, since IdeaPress
  and LoadCoach will each want their own pack location and `setspec` must not guess whose. Made
  `root` a required positional parameter in `setspec.prompts.load_pack`. Preserved FreeWeight's old
  zero-argument call sites (~14 benchmark modules, `services/runs.py`, dozens of tests) with zero
  edits by rewriting `freeweight/services/prompts.py` as a re-export shim: everything comes from
  `setspec.prompts` except `load_pack`, which gets a two-line local wrapper that supplies
  `PACK_ROOT` as the default and forwards to the real one. `docs/prompts-adoption-checklist.md` §2
  writes this pattern up for the next adopter.
- **What the next run must do:** Nothing blocking. When IdeaPress or LoadCoach writes its first
  prompt pack, expect it to need the same one-wrapper-function shim, not a call-site-by-call-site
  edit — that's the whole point of the pattern.

- **Resolved by the P3–P4 run:** The prediction was exactly right. `loadcoach/services/prompts.py` is that one-wrapper shim: it supplies `PACK_ROOT` and caches the loaded library, and every call site goes through it rather than knowing where the pack lives.

### SS3 — Golden-hash verification: three checkpoints, byte-identical at each
- **Severity:** NOTE
- **Unit:** SetSpec P5
- **Where:** Verification only; no shipped file. Performed against
  `FreeWeight/src/freeweight/prompts/` (the real pack) before and after the move.
- **What happened:** Captured `pack_hash` and all 18 individual record hashes
  (`benchmarks.agent.goal` through `goals.judge.rubric`) from FreeWeight's pre-migration code —
  `pack_hash: sha256:b1b0ffd0a5941fee5e0013d2a826732ea02a285b229bdc006ebd6dd25ff4ceb4`. Recomputed
  the same values two more times: once loading the pack directly through
  `setspec.prompts.load_pack()`, once again through FreeWeight's post-migration shim
  (`freeweight.services.prompts.load_pack()`). All three checkpoints agree, on every hash. This is
  the evidence behind "FreeWeight's own gate passed unchanged" in SS1 — a passing test suite alone
  would not have caught a hash that moved but every *test* still happened to pass (few of
  FreeWeight's tests assert the literal hash value; they assert behaviour that a hash change
  wouldn't necessarily break).
- **What the next run must do:** Nothing — this was a one-time migration proof, not a mechanism to
  maintain. If `setspec.prompts`' hashing arithmetic ever changes, redo this comparison before
  shipping the change, the same way this run did it once going in.

### SS4 — `test_goal_pack_import.py` reached into a private symbol; fixed to import from the new home
- **Severity:** NOTE
- **Unit:** SetSpec P5
- **Where:** `FreeWeight/tests/security/test_goal_pack_import.py` (3 call sites)
- **What happened:** This one test file imported `_environment` — a private, underscore-prefixed
  function — directly from `freeweight.services.prompts`, to assert the sandboxing properties
  (dunder-access refusal, no loader) on the exact environment prompts render through. The shim
  re-exports the public surface but a private name is deliberately not part of that surface, so
  `freeweight.services.prompts._environment` no longer resolves after the rewrite. This was the
  **only** source file besides the shim itself that needed a change anywhere in FreeWeight. Fixed
  by changing the three `from freeweight.services.prompts import _environment` lines to `from
  setspec.prompts import _environment` — the function moved, the test now imports it from where it
  actually lives.
- **What the next run must do:** Nothing — fixed, and FreeWeight's full gate is green including
  this file. Worth knowing as a pattern: a re-export shim covers the public API by construction,
  but any test reaching past `__all__` into a private name has to be found and repointed by hand;
  `grep -rn "from freeweight.services.prompts import _"` across a repo is how this one was found.

### SS5 — `prompt.record`/`prompt.manifest` JSON Schema hand-authored, deliberately not wired into `PUBLISHED_SCHEMAS`
- **Severity:** DECISION
- **Unit:** SetSpec P5
- **Where:** `py/SetSpec/src/setspec/schemas/prompt.{record,manifest}/1.0.json`,
  `py/SetSpec/src/setspec/goldens/prompt.{record,manifest}/1.0/{full,minimal}.json`
- **What happened:** P5's Work item says prompt records get "JSON Schema and goldens like every
  other payload." Every other payload is a pydantic model registered in `artifacts.py`'s
  `PUBLISHED_SCHEMAS`, with its schema generated from the model and its goldens checked three ways
  by `tests/contract/test_goldens.py` (writer model / published schema / canonical round-trip).
  `PromptRecord` is a plain `@dataclass`, not a pydantic model, and by design: prompt records are
  pack files read straight off disk through `load_pack()`, never wrapped in a `SchemaEnvelope` the
  way a run result or capability-evidence payload is (there is no `dump_envelope`/`load_envelope`
  call anywhere in `prompts.py`). Converting `PromptRecord` to pydantic to fit the existing
  machinery risked the one thing this unit could not risk — the hash arithmetic in SS3 is defined
  over `canonical_json(body)` where `body` is the record *exactly as parsed*, and a pydantic
  round-trip (default-value filling, alias handling, field reordering under some configurations)
  is a plausible way to silently perturb that. Instead: hand-authored two JSON Schema 2020-12
  files (marked as hand-authored via `$comment`, matching what a reader unfamiliar with this
  decision needs to know), written against what `_load_record`/`_check_manifest` actually enforce,
  and two goldens per schema (`full`, every field populated including a non-string variable with
  `min`/`max`; `minimal`, the bare required set) — each validated against its schema, loaded
  through the real `load_pack()` (not just schema-checked), rendered, and its `pack_sha256`/
  individual hashes computed by the module itself rather than typed by hand. Neither schema is
  registered in `PUBLISHED_SCHEMAS`; neither golden is picked up by `test_goldens.py`'s
  parametrized matrix (confirmed by reading that file — it parametrizes over `PUBLISHED_SCHEMAS`
  entries only).
- **What the next run must do:** Nothing blocking. If a future phase decides prompt records
  *should* become envelope payloads (e.g. to travel over the same HTTP composition boundary
  `docs/architecture/master-architecture.md` describes for cross-application payloads), that is a
  bigger decision than this unit's scope — it changes what `PromptRecord` *is*, not just how it's
  documented — and deserves its own ADR before the schema is moved into `PUBLISHED_SCHEMAS`.

### SS6 — Release prepared, not published
- **Severity:** NOTE
- **Unit:** SetSpec P5
- **Where:** `py/SetSpec/CHANGELOG.md`, `py/SetSpec/src/setspec/__about__.py`
- **What happened:** Per this run's instructions, stopped short of the publish step.
  `__about__.py` bumped `0.3.0` → `0.4.0`; `CHANGELOG.md` has a new, dated
  `## [0.4.0] — 2026-08-29` section ahead of `## [0.3.0]`, `Unreleased` left empty. No tag, no
  `git push`, no `twine upload` — none were attempted.
- **What the next run must do:** Follow packaging-and-release-standards.md §6 from step 4 onward
  (open the release PR, tag `v0.4.0`, let `release.yml` publish via Trusted Publishing) — a human
  decision, same as WDB3 for WeightsDB's own release. Checked, not assumed: LoadCoach's venv
  already reports `setspec.__version__ == "0.4.0"` and imports `setspec.prompts` straight from
  `py/SetSpec/src/setspec/prompts.py` with **no reinstall needed** — hatchling's editable-install
  mechanism points LoadCoach's venv at the live source tree, so both the version metadata and any
  new module become visible the moment they exist on disk. The task's own environment note ("when
  SetSpec bumps to 0.4.0, reinstall it editable into LoadCoach's venv") describes what would be
  needed for a *non-editable* or pinned-copy install; it was not needed here, and running it now
  would be a harmless no-op. A real PyPI-published release does not change any of this until
  someone deliberately re-pins LoadCoach off the editable install.

- **Resolved by the P6 run:** Published and verified: `pip index versions setspec` reports `0.4.0`, and `py/SetSpec` carries the `v0.4.0` tag. This entry is closed.

---

# M4 Handoff — Opus run (LoadCoach P3–P4, MirrorWall P1–P2)

Run started 2026-08-29, after the Sonnet run above. This half is written for the P5 run — the
queue — which is what comes next.

## What was done to the earlier run's entries

**No entry in the Sonnet half was a BLOCKER.** Every one is a NOTE, a DECISION or a DEFERRED item,
and all ten of the DECISIONs were checked against what P3 and P4 actually need. Two mattered and
neither had to change; the rest are storage- or evidence-shaped and do not touch routing or
execution.

| Entry | What this run did |
|---|---|
| LC1–LC2, LC6, LC9–LC10, WDB2, WDB4, SS3–SS4 | Nothing needed. Verified only where P3/P4 touched the same code. |
| LC3 (`StorageFull` naming) | Not on P3/P4's path — routing and execution raise no storage error of their own. |
| LC4 (`transaction()`/`session_scope()`) | **Checked and kept.** `Database.read()`/`write()` are exactly what the routing and execution services need, and the read-only enforcement caught nothing wrong: every routing read is genuinely read-only and every write is one unit of work. No change. |
| LC5 (`migration_harness`) | Not used. LoadCoach's own migration tests still drive `MigrationRunner` directly — see LCX1 for the change they *did* need. |
| LC7 (two-schemas stand-in) | Unchanged and still passing. |
| LC8 (`lease_seconds` boundary) | Queue-only; P5's problem, not this run's. |
| LC11 (fifteen task profiles' weights) | **Load-bearing for P3, and used as-is.** The weights are what routing ranks on. `code.review`'s worked-example values are exercised by the structured-output tests; the other fourteen are still authored rather than tuned, which the `low_evidence` flag now discloses on every decision. |
| LC12 (only TOOLS/STRUCTURED_OUTPUT map) | **Checked and kept**, and it turned out to matter more than expected: `capability_unsupported` is evaluated against exactly those two capabilities, so a profile requiring `tool_use` filters correctly and one naming a capability with no provider flag is not silently rejected. |
| LC13 (manual scores, shipped empty) | Used. `source="manual"` is third in scoring's precedence and is covered by tests; the shipped file is still empty. |
| LC14 (`tasks list` imports first) | Same pattern reused in `loadcoach route explain`, for the same reason. |
| **LC15** (`GET /models/{ref}`, `GET /task-profiles/{id}`) | **DEFERRED, still deferred.** P3's own Work item and file list name neither. What P3 needed instead — a read path for a stored decision — is `GET /api/v1/routing-decisions/{id}` (LCX3). |
| **LC16** (`models residency`) | **DEFERRED, still deferred, and now with a clearer home.** P4's Work item does not name it, and residency state does not change until the queue tracks it. It belongs with P5/P6 alongside the `residency` table. |
| SS1–SS2, SS5–SS6 (`setspec.prompts`) | **Verified present and used.** `setspec.prompts` is what LoadCoach's own pack loads through, and SS2's "expect a one-wrapper shim" prediction was exactly right — `loadcoach/services/prompts.py` is that shim. SetSpec P5 was **not** re-done. |

---

## LCX1 — LoadCoach's migration tests hard-coded `0001` as head
- **Severity:** NOTE
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/tests/integration/test_migrations.py`
- **What happened:** Three Phase 1 tests asserted `outcome.to_revision == "0001"`, and the
  failing-revision test wrote a broken `0002` into a copy of the migrations directory. Adding P3's
  real `0002` broke all three: two on the literal, one on a revision-ID collision that Alembic
  reported only as `UserWarning: Revision 0002 is present more than once` before failing to raise
  the `MigrationFailed` the test expected. Rewritten to read head from the script directory
  (`_head()`, which also asserts the history stays linear) and to stack the broken revision on
  whatever head currently is, under the reserved ID `9999`.
- **What the next run must do:** Nothing. P5's migration `0004` will not break these again. If a
  phase ever introduces a second head, `_head()` fails with that as its message rather than with a
  confusing revision mismatch.

## LCX2 — `context_not_configurable` cannot mean what a literal reading suggests
- **Severity:** DECISION
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/domain/routing/{subject,constraints}.py`
- **What happened:** ADR-0023 §4 makes two statements about a provider whose context is not
  configurable: an `assumed` served context "carries the flag `assumed_context`", and
  "`context_not_configurable` applies when a profile requires a context the provider cannot be
  asked to serve." Read literally as "min_context_tokens > 0 and not configurable", the second
  swallows the first entirely — and every one of the fifteen shipped profiles declares
  `min_context_tokens`, so `assumed_context` could never be raised by any real request and P3's
  own required test for it would be unwritable.
  Resolved by making the two disjoint, which also fixed a related dishonesty: a `context_size` set
  on a provider that declares `context_configurable=False` is **no longer reported as
  `configured`**, because the provider will ignore the setting and recording a context that never
  happened is the fabricated-measurement failure ADR-0023 exists to prevent. Such a candidate
  falls through to `reported`/`assumed`, and `context_not_configurable` fires exactly when an
  explicit ask cannot be honoured (`profile.context_size is not None and not
  context_configurable and requested != served`). `assumed_context` then means what §4 says: the
  provider is not configurable, the context could only be assumed, and it happens to satisfy the
  requirement.
- **What the next run must do:** Nothing blocking. If ADR-0023 is ever amended here, the two
  functions to revisit are `resolve_served_context` and the second and third branches of
  `evaluate_constraints`; both carry the reasoning in their docstrings.

## LCX3 — Routing decisions needed a read path api.md does not list
- **Severity:** DECISION
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/web/routes/routing.py`
- **What happened:** P3 acceptance criterion 2 requires every routing decision to be
  *retrievable*, and the Work item requires "a Routing page rendering the explanation readably" —
  but api.md §3 lists only `POST /route`, and §5's `GET /jobs/{id}/explanation` needs a `jobs`
  table that did not exist until P4. Added `GET /api/v1/routing-decisions` and
  `GET /api/v1/routing-decisions/{decision_id}`, plus the `/routing` and `/routing/{id}` pages.
  Additive within v1, which api.md's own preamble permits.
- **What the next run must do:** When P5 adds `GET /jobs/{id}/explanation`, implement it as a
  lookup of the decision whose `job_id` matches — the column exists as of migration `0003` and is
  populated by the executor. Do **not** duplicate the explanation document into the job row.

- **Resolved by the P5 run:** `GET /jobs/{id}/explanation` is a lookup of the `routing_decisions` row whose `job_id` matches (the worker links the decision at admission; the synchronous path links it after routing). Nothing is copied onto the job row; `test_the_explanation_is_a_lookup_of_the_decision_that_routed_the_job` asserts the two endpoints return the identical document.

- **Resolved by the P6 run:** Unchanged and still correct. P6 reads a stored decision through `GET /api/v1/routing-decisions/{id}` and copies nothing: the evidence a decision used is derivable from the stored explanation's own capability breakdown, and `evidence_summary` records the store's provenance at decision time rather than a snapshot of the evidence rows.

## LCX4 — Routing's arbitrary constants, named and gathered
- **Severity:** DECISION
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/domain/routing/{constraints,scoring,context_budget}.py`
- **What happened:** The plan's own risk register says "priors that are arbitrary", mitigated by
  low fixed confidence and explicit source labelling. Several numbers had to be chosen and none is
  in any document: `LOADING_OVERHEAD_FACTOR` (1.05), `ACTIVATION_OVERHEAD_BYTES` (256 MiB),
  `ASSUMED_KV_CACHE_PRECISION` (`f16`, recorded as `kv_precision_assumed=True` on every estimate
  built with it), `PARAMETER_BAND_PRIOR_FLOOR`/`CEILING` (0.40–0.60), `DECLARED_PRIOR_SCORE`
  (0.5), `DECLARED_PRIOR_CONFIDENCE` (0.3), `PRODUCTION_MINIMUM_SAMPLES` (20),
  `SAFETY_MARGIN_TOKENS` (256) and `CHARS_PER_TOKEN` (4.0). Every one is a module constant with a
  docstring saying why, every one is a keyword argument on the function that uses it, and every
  estimate records which of them it relied on.
- **What the next run must do:** When P5's admission policy starts deferring real jobs, the two
  worth revisiting against observed OOMs are `LOADING_OVERHEAD_FACTOR` and
  `ACTIVATION_OVERHEAD_BYTES` — they are the only ones that can cause an admission to be wrong in
  the dangerous direction. The KV term dominates at any interesting context length.

- **Resolved by the M5 run:** `PRODUCTION_MINIMUM_SAMPLES` (20) now lives in `domain/reliability.py` beside the statistics it bounds and is re-exported from `scoring.py` unchanged; it gates the reliability factor and, unchanged, the production-signal path in scoring. The new constants follow the same rule — each a named module constant with a docstring saying why: `MINIMUM_RATE_SAMPLES` 5, `MINIMUM_MEAN_SAMPLES` 5, `MINIMUM_PERCENTILE_SAMPLES` 20, `RELIABILITY_FACTOR_FLOOR` 0.5, `FEEDBACK_WEIGHT` 0.5, `EDITED_ACCEPTANCE_CREDIT` 0.5, `REGRESSION_MINIMUM_SAMPLES` 20, `REGRESSION_MINIMUM_DROP` 0.15, `REGRESSION_Z_THRESHOLD` 2.0 (M5-9).

## LCX5 — Scoring rules the documents leave to the implementer
- **Severity:** DECISION
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/domain/routing/scoring.py`
- **What happened:** Four rules were decided here because routing §5/§5.1 does not settle them:
  1. **A declared flag contributes 0.5, not the stored 1.0.** P2 stores `score=1.0` for a declared
     capability, which is an honest statement that the flag is present; routing §5.1 says the
     *contribution* is "0.5 as a neutral prior". Both are kept: the row means "declared", the
     scoring means "no measurement". (LC12's mapping is what decides which flags get a row at all.)
  2. **A prior never fills a capability whose evidence was excluded for a reason.** A model
     measured under a different runtime profile is not in the same position as one nobody has ever
     measured, and substituting a band prior would bury the `evidence_profile_mismatch` remedy
     ADR-0023 §3 wants surfaced.
  3. **`low_evidence` counts measured weight only** — benchmark, production and manual — while the
     `task_fit` denominator counts any present signal including priors. Without this split, the
     band prior would fill every capability, present weight would always be 1.0, and the flag
     would never fire, which contradicts P3 acceptance criterion 1.
  4. **`require_evidence` excludes manual scores too**, not only declared flags and band priors,
     per routing §10's wording "declared/manual priors".
- **What the next run must do:** Nothing blocking. When P6 imports real FreeWeight evidence, rule
  2 is the one to watch: it is what makes `evidence_profile_mismatch` visible instead of quietly
  replaced, and it is the reason a user who benchmarks under the wrong profile sees a remedy
  rather than a plausible score.

- **Resolved by the P6 run:** **Re-read against routing §5 and §5.1, and confirmed unchanged.** The precedence P3 chose — benchmark, production, manual, declared, band prior — is what routing §5's `capability_score` table and §5.1's four-signal table describe together, and P6 changes none of it; it only makes the first entry non-empty for the first time. Rule 2 is the one that mattered, exactly as this entry predicted: a model measured under a different profile now really does show `evidence_profile_mismatch` with a remedy instead of a plausible band prior, and the I4 demonstration turned that remedy into an action a person took and re-benchmarked from. Rule 3's split (`low_evidence` counts measured weight only) is what lets the flag *clear* once 0.6 of a profile's weight is measured, which is the visible half of P6's acceptance criterion 2.

- **Resolved by the M5 run:** Re-read against routing §5.1, §6 and §11 with `reliability_factor` live for the first time. The precedence is unchanged and the `production` capability source stays **reserved and unused**: production evidence enters routing through the factor, the breaker and regression detection, never through a capability score (M5-1). Rule 4 stands: `require_evidence` excludes manual and declared, and the factor is not a capability signal so the rule does not touch it.

## LCX6 — Request `constraints` may only tighten
- **Severity:** DECISION
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/services/routing.py` (`_merged_constraints`)
- **What happened:** api.md §3's `POST /route` body carries a `constraints` block, but routing
  §10's override table has no entry for relaxing a profile's constraints, and routing §2 calls
  them hard. Implemented as tightening-only: collections union, floors take the maximum, latency
  takes the minimum, and `allow_remote_providers` can only go false-ward. An attempt to loosen is
  refused with `VALIDATION_ERROR` naming the field, rather than silently ignored.
- **What the next run must do:** Nothing. If a real caller ever needs to relax a profile
  constraint, that is a new override in routing §10 with its own ADR, not a change here.

## LCX7 — Two forced schema additions, and the descriptor geometry P2 never stored
- **Severity:** NOTE
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/{config.py,domain/task_profile.py,domain/registry.py,services/models.py}`
- **What happened:** Three additions outside P3's literal file list, each forced:
  * `[routing].remote_cost_factor` — routing §6's `cost_factor` is "configurable" and there was no
    setting for it. Added to `RoutingSettings`, whose docstring already says "Phase 3".
  * `execution.min_output_tokens` on the task profile — routing §9 reduces the output allowance
    "when the profile permits", and nothing expressed permission. Unset by default, so a request
    that does not fit is rejected with numbers rather than quietly shortened.
  * `models.descriptor_json` is now **written** by discovery, holding `layers`, `kv_heads`,
    `head_dim` and four more. The column existed since migration `0001` and nothing populated it;
    without it the theoretical KV figure cannot be computed at all and every VRAM estimate would
    be unknown. Fields the provider did not report are omitted, so reading one back gives `None`
    rather than `0`.
- **What the next run must do:** Nothing. A registry populated before this change has
  `descriptor_json IS NULL` and its models estimate as unknown VRAM until the next discovery pass
  — which `loadcoach models refresh` triggers, and which the next `serve` does anyway.

- **Resolved by the P6 run:** The descriptor geometry P2 stores is what P6's evidence-driven decisions still estimate VRAM from; nothing here changed. Worth recording for the next run: on a workstation whose card is largely occupied by another process, that estimate correctly rejects every candidate, which is why the I4 routing comparison injects a telemetry snapshot through `route(snapshot=...)` rather than reading the live card — see the P6 section.

## LCX8 — The VRAM estimator's unknown/absent behaviour, and where the RAM check applies
- **Severity:** DECISION
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/domain/routing/constraints.py`
- **What happened:** Queue §5 says admission never guesses optimistically, and ADR-0016 says an
  absence is not a zero. Applied as: an estimate missing any input has `total_bytes=None` with a
  named `unknown_reason` and **fits no device**; a device reporting only one of total/used VRAM
  reports neither (the difference of a number and an absence is an absence); a machine with **no
  GPU at all** skips the VRAM constraint entirely rather than rejecting everything, because a
  CPU-only machine is a supported deployment and not a machine that ran out of VRAM. The RAM check
  is evaluated only in that no-GPU case: once a device has been found to hold the weights, what
  the host still needs is page cache this estimate has no honest way to bound, and reporting a
  number it cannot derive would be the fabricated measurement the suite refuses everywhere else.
- **What the next run must do:** P5's aggregate check ("concurrent jobs targeting GPU 0 sum
  against GPU 0's free VRAM") layers on top of `device_fits`, which already returns a per-device
  breakdown. Do not change the estimator to sum anything.

- **Resolved by the P5 run:** Layered on, not changed. `QueueRuntime.admission_snapshot` subtracts other in-flight jobs' estimates from *their* device (reservations, never summed) and counts idle residents' memory as reclaimable; `device_fits` is untouched. The one addition to the constraint filter is `ConstraintInputs.resident_devices`: a model resident on a device fits there whatever the estimate says — queue §5's own exception — and its device is preferred over another that merely has room.

## LCX9 — P3 built the estimator and **not** the admission policy
- **Severity:** NOTE
- **Unit:** LoadCoach P3
- **Where:** `LoadCoach/src/loadcoach/domain/routing/constraints.py`, and everything absent from it
- **What happened:** The plan's sequencing note is explicit, and this is the confirmation that it
  was honoured. What exists: `estimate_vram` as a pure function, `device_fits` as a per-device
  comparison, and `insufficient_vram` as a hard constraint. What does **not** exist anywhere in
  the codebase: deferral, `waiting_resources`, re-evaluation on unload, lease release, the
  aggregate per-device check, or any queue state at all. `domain/{admission,queue_state,priority,
  circuit_breaker,reliability,evidence_policy}.py` and `services/{queue,worker,recovery,residency,
  feedback,evidence}.py` are still one-line scaffolds.
- **What the next run must do:** P5 builds the policy around the estimator rather than replacing
  it. `ConstraintInputs.open_circuit_breakers` is already threaded through and is empty until P7
  opens one, so the breaker needs no plumbing change either.

- **Resolved by the P5 run:** The policy is `domain/admission.py` plus the worker's deferral path: a routing failure with a resource-shaped rejection moves the job `leased → waiting_resources` with the numbers recorded on the event, a permanent one fails it (ADR-0036 §3), and the scheduler re-evaluates waiters by admission's own rule so nothing bounces. `open_circuit_breakers` is now populated by P5's breaker (see P5-9 below).

## LCX10 — MirrorWall's scaffold had four of the five defects LC1 found
- **Severity:** NOTE
- **Unit:** MirrorWall P1
- **Where:** `py/MirrorWall/{.importlinter,pyproject.toml}`
- **What happened:** LC1's closing advice — "if a *third* scaffold (IdeaPress, MirrorWall) is
  started from the same generator, check its `.importlinter` and `[tool.mypy]` for the same five
  gaps" — was exactly right. `.importlinter` had the plural `root_packages` with a bare string and
  no `include_external_packages`; `[tool.mypy]` had no `mypy_path`/`explicit_package_bases`. All
  fixed. The coverage floor was also 85% and is now the 95% shared packages carry.
- **What the next run must do:** **IdeaPress is the remaining scaffold.** Check the same four
  before its first gate: it will save an hour of confusing failures.

- **Resolved by the handoff-review run:** Done, and the advice paid off a second time — see HR1.
  IdeaPress had all five, plus an invalid requirement specifier that broke `pip install -e ".[dev]"`
  outright. No scaffold in the workspace now carries any of them.

## LCX11 — MirrorWall vendors no third-party asset, deliberately
- **Severity:** DECISION
- **Unit:** MirrorWall P1
- **Where:** `py/MirrorWall/THIRD_PARTY_NOTICES.md`, `src/mirrorwall/static/ASSETS.sha256`
- **What happened:** P1's Work item lists "vendored assets: charting library, Inter font with its
  licence, inline SVG icon set". Shipped: an original 16-glyph SVG sprite, stroked with
  `currentColor`. **Not** shipped: a charting library (every chart in the suite is inline SVG
  coloured by `--mw-chart-*` tokens, which is what lets the theme switch re-theme a chart; a
  library would add a licence, a checksum and a second colour system to reconcile) and the Inter
  font binary (`--mw-font-ui` names Inter first and degrades to the platform UI face, a difference
  in letterforms rather than in layout, because every measurement in the system is a token).
  The *mechanism* is complete and enforced: `ASSETS.sha256` records every shipped file, a test
  recomputes every digest, and a vendored file with no `THIRD_PARTY_NOTICES.md` entry and no
  adjacent `LICENSE` fails that test.
- **What the next run must do:** If MirrorWall P3's chart module turns out to need a real library,
  follow the four steps in `THIRD_PARTY_NOTICES.md` §"Adding a vendored asset" — the test is
  already written for that day.

## LCX12 — The term scan covers names and markup, not prose
- **Severity:** DECISION
- **Unit:** MirrorWall P1
- **Where:** `py/MirrorWall/tests/test_no_application_vocabulary.py`
- **What happened:** A scan for application vocabulary over raw file text fails on the package's
  own boundary documentation — `__init__.py` says "knows nothing about benchmarks, routing or
  content" (spec §1 verbatim) and names its three consumers (spec §6). Enforcing zero mentions
  would make the docstrings worse, not the package cleaner. The scan therefore strips comments and
  docstrings first — including PEP 258 attribute docstrings, which this package uses for every
  public constant — and checks what remains: identifiers, template markup, CSS selectors, JS
  module names, and every string literal that is *used* rather than standing alone. A
  `.benchmark-row` selector or a `run_id` macro parameter still fails, which is the defect the
  test exists for. A separate test asserts the stripper strips what it claims and keeps what it
  claims.
- **What the next run must do:** Nothing. If the scan ever passes suspiciously, run
  `test_the_scan_actually_covers_the_package` and `test_the_stripper_removes_comments_and_
  docstrings_and_nothing_else` first — both exist to catch a scan that passed for the wrong reason.

## LCX13 — `sse_response` takes a `generator`, and `replay` returns a batch
- **Severity:** DECISION
- **Unit:** MirrorWall P2
- **Where:** `py/MirrorWall/src/mirrorwall/sse.py`
- **What happened:** Two deviations from spec §7's signature block, both forced by the plan's own
  text:
  * `sse_response(..., generator: GeneratorInfo)` is a **required** parameter the spec does not
    list. Every non-`token` frame is a SetSpec envelope and an envelope carries a generator; that
    generator must name the producing *application* (ADR-0025 §3: "the generator already names the
    producing application"), which MirrorWall cannot know and must not invent about itself.
  * `EventSource.replay` returns `Sequence[Event]` with a `limit`, not `Iterator[EventEnvelope]`.
    The plan requires "replay reads in bounded batches rather than one round trip per event", and
    an unbounded iterator cannot express a `LIMIT` or be dispatched into a thread as one call.
- **What the next run must do:** Nothing. If the spec is ever reconciled with the code, these are
  the two lines to change in it.

## LCX14 — The steady-state stream polls rather than blocking a worker thread
- **Severity:** DECISION
- **Unit:** MirrorWall P2
- **Where:** `py/MirrorWall/src/mirrorwall/sse.py` (`Subscription`, `_frames`)
- **What happened:** ADR-0003 §7 requires every call into the synchronous `EventSource` to go
  through `anyio.to_thread.run_sync`, and it does: opening the subscription, each bounded replay
  batch, and closing it. The steady-state wait deliberately does **not**. A subscriber blocking in
  a worker thread would hold one of the pool's forty slots for as long as the browser stayed
  connected, so the 200-subscriber acceptance criterion and forty sync route handlers cannot both
  be satisfied that way — two hundred idle streams would deadlock every synchronous handler in the
  application. Instead a `Subscription` is a bounded, lock-protected deque that worker threads
  push into and the event loop polls, sleeping `poll_interval_seconds` (default 50 ms) when it is
  empty. The cost is a bounded median added latency of half that, stated in the docstring; the
  benefit is that an idle stream costs no thread at all.
- **What the next run must do:** Nothing. If latency ever matters more than the thread budget,
  the change is an `anyio.Event` per subscription set through a blocking portal — which costs a
  thread per stream again, so it is a trade to make deliberately, not an optimization.

## LCX15 — Every SSE property was mutation-tested, and two tests failed that bar
- **Severity:** NOTE
- **Unit:** MirrorWall P2
- **Where:** `py/MirrorWall/tests/integration/test_sse.py`
- **What happened:** The instruction for this unit was not to ship a plausible version. Five
  mutations were applied to `sse.py` in turn and each was required to fail the test that claims to
  catch it: replay-before-subscribe, no dedupe, a blocking `replay`, an unbounded queue, and no
  cleanup on disconnect. **Two tests passed under mutation on the first attempt and were
  rewritten**: the handoff test stopped reading after N frames, so it never observed the duplicate
  it asserted against, and it injected its race before the replay batch was selected, so it never
  opened the gap either. It now injects at **both** instants — one event before the batch is
  selected (in the batch *and* the queue: the duplicate window) and one after (in neither: the
  gap window) — and drains with a settle period. The disconnect test passed under mutation because
  a `@contextmanager` generator's `finally` also runs when CPython collects it; the test source's
  subscription is now a plain class whose `__exit__` has no second path.
- **What the next run must do:** Keep the bar. If `sse.py` is edited, re-run those five mutations
  — they take about a minute and they are the difference between a test suite and a decoration.

- **Resolved by the M5 run:** The bar was kept for P8's live queue page. `services/queue_stream.py` publishes a full-state `queue.status` frame on change — the report plus the page fragment rendered from it, never a diff — and five mutations were applied to it, each required to fail the test that claims to catch it: replay returning nothing, the publisher never re-polling, a sequence that does not advance, replay ignoring `Last-Event-ID`, and the fragment rendered from the previous report. All five failed a test (M5-11). One test needed tightening first: with replay disabled, a client that connected *before* the publisher's first poll still received that frame from the broker, so the first-frame test passed under the mutation and only the reconnect test caught it; it now waits for the first poll before connecting, and fails on its own.

## LCX16 — `terminal_events`: a finite stream must be able to end
- **Severity:** NOTE
- **Unit:** MirrorWall P2 / LoadCoach P4
- **Where:** `py/MirrorWall/src/mirrorwall/sse.py`
- **What happened:** `sse_response` had no notion of a stream that is over, which is right for
  telemetry and wrong for a generation. LoadCoach's first streaming test hung: the executor
  published its `result` frame and the SSE loop went on polling an event source that would never
  speak again. Added `terminal_events: frozenset[str]`, empty by default so an open-ended stream
  is unchanged; LoadCoach passes `{"result", "error"}`, which is api.md §4's own sentence.
- **What the next run must do:** Any finite stream P5 adds — `GET /jobs/{id}/stream` above all —
  must pass its own terminal event names, or it will hold a connection open after the job finishes.

- **Resolved by the P5 run:** `GET /jobs/{id}/stream` passes `TERMINAL_JOB_EVENTS | {"result", "error"}` and `POST /generate/stream` passes `{"result", "error"}`; `test_submit_returns_202_and_the_job_runs_to_completion` reads a job stream to its natural end.

## LCX17 — A shared-package bug the tests found: `extra={"request_id": …}` crashes the rejection path
- **Severity:** NOTE
- **Unit:** MirrorWall P2
- **Where:** `py/MirrorWall/src/mirrorwall/middleware.py`
- **What happened:** `RequestIdMiddleware` binds `request_id` to every log record through a record
  factory; `HostValidationMiddleware` and `CsrfMiddleware` also passed `extra={"request_id": …}`.
  `logging.makeRecord` refuses an `extra` key that would overwrite an existing attribute, so every
  421 and every 403 raised `KeyError: "Attempt to overwrite 'request_id' in LogRecord"` from
  inside the rejection path — the one path that must never fail. Found by the middleware tests on
  their first run. Both call sites now rely on the factory.
- **What the next run must do:** Nothing. Worth knowing generally: with a record factory binding
  request context, a log call must not name the same key in `extra`.

## LCX18 — `stream_execute` buffered the whole generation before yielding anything
- **Severity:** NOTE
- **Unit:** LoadCoach P4
- **Where:** `LoadCoach/src/loadcoach/services/execution.py`
- **What happened:** The first version collected every chunk into a list and returned an iterator
  over it, which is not streaming at all: every token arrived at once, after the generation had
  finished, and the SSE endpoint looked correct because the frames were in the right order.
  Rewritten to take an `on_chunk` callback — the callback *is* the stream — and the streaming test
  now asserts token deltas reassemble to the result text, which a buffered implementation also
  passes; what catches it is that `POST /generate/stream` now emits `routing` before the provider
  has produced anything.
- **What the next run must do:** When P5 executes from a worker rather than from the request
  thread, keep the callback shape: it is what lets the queue worker publish into the job's event
  stream with no change to the executor.

- **Resolved by the P5 run:** The `on_chunk` shape is unchanged. The queue worker hands `run_attempt` an `on_chunk` that publishes token frames into the job's event stream through the sink, and the streaming route's `_drive` does the same for the synchronous path.

## LCX19 — A stale `Last-Event-ID` hung `POST /generate/stream` forever
- **Severity:** DECISION
- **Unit:** LoadCoach P4
- **Where:** `LoadCoach/src/loadcoach/web/routes/generate.py`
- **What happened:** A POST is a new execution with its own sequence space starting at 1. Honouring
  a `Last-Event-ID` from some other stream made `after_sequence` larger than anything the new
  stream would ever emit, so every frame was skipped — including the terminal one — and the
  connection waited for ever. Resolved the way api.md §4 already specifies: a repeated
  `idempotency_key` **attaches to the existing stream** rather than re-executing, and
  `Last-Event-ID` is honoured only there, where it can mean something. A POST with no key ignores
  the header entirely. In-flight and recently-finished streams are held in a bounded registry
  (64 entries) on application state.
- **What the next run must do:** **This registry is in-memory, per-process, and bounded — it is
  not the durable idempotency the data model describes.** P5 owns that: `jobs.idempotency_key`
  with its `UNIQUE (source, idempotency_key)` index and `idempotency_expires_at`, and
  `GET /jobs/{id}/stream` replaying from persisted `job_events` rather than from a process-local
  log. The column and the table exist as of migration `0003`; nothing writes the expiry yet.

- **Resolved by the P5 run:** The registry is gone. `reserve_sync_job` creates the job row before execution, so a repeated key finds it through `UNIQUE (source, idempotency_key)` whether the execution is running or finished; `idempotency_expires_at` is written on enqueue and on reservation, and an expired key is released. `routing` and the terminal `result`/`error` are persisted as job events and published after commit, so a reconnect replays them from the table. Token frames are fanned out live from a bounded per-job buffer that is dropped at the terminal frame — see P5-11 for what that changed in P4's reconnect tests.

## LCX20 — The JSON Schema validator is small, and refuses what it cannot check
- **Severity:** DECISION
- **Unit:** LoadCoach P4
- **Where:** `LoadCoach/src/loadcoach/domain/validation.py`
- **What happened:** `jsonschema` is not a declared dependency and could not be installed offline.
  Rather than add an unbuildable pin, implemented the twenty JSON Schema 2020-12 keywords the
  suite's five shipped schemas actually use, and made the validator **raise `SchemaUnsupported`**
  on any other keyword rather than ignoring it — an ignored constraint produces a validation that
  passed for a reason nobody intended, which is the same class of defect as a fabricated
  measurement. Every failing field path is reported, not the first, because a corrective retry
  that fixes one problem per round trip takes one round trip per problem.
- **What the next run must do:** If a task profile ever needs `oneOf`, `anyOf`, `$ref` or
  `patternProperties`, the honest choices are to implement it here or to add `jsonschema` as a
  dependency — **not** to widen `SUPPORTED_SCHEMA_KEYWORDS` without implementing the check.

- **Resolved by the P6 run:** **Checked before relying on it, and it cannot validate `benchmark.evidence_bundle`.** The generated schema uses `$defs`, `$ref` and `anyOf`, none of which `SUPPORTED_SCHEMA_KEYWORDS` implements, so `validate_schema` raises `SchemaUnsupported` — exactly as this entry says it should. P6 therefore validates through SetSpec's own pydantic models (`EvidenceBundleIn` / `CapabilityEvidenceIn`), which are strictly stronger here: they carry the cross-field validators a JSON Schema cannot express (`canonical_id` recomputed from the identity triple, `measured_at` not after `computed_at`, the capability vocabulary check). **No second validator was hand-rolled**, and `SUPPORTED_SCHEMA_KEYWORDS` was not widened. See P6-3.

## LCX21 — Queue columns are declared but unwritten
- **Severity:** NOTE
- **Unit:** LoadCoach P4
- **Where:** `LoadCoach/src/loadcoach/infrastructure/db/models.py`, migration `0003`
- **What happened:** `jobs` is declared in full, including the columns only the queue writes:
  `class`, `base_priority`, `effective_priority`, `state`/`state_reason` beyond
  `completed`/`failed`, `scheduled_for`, `queued_at`, `max_wait_seconds`, `queue_wait_ms`,
  `lease_owner`, `lease_expires_at`, `cancel_requested`, `idempotency_expires_at`. Every index the
  data model names is created, including the claim query's
  `(state, effective_priority DESC, created_at)`. P4 writes `state="completed"` or `"failed"` and
  `queue_wait_ms=0`; everything else is left at its default.
- **What the next run must do:** P5 needs **no migration for the queue's own columns** — they are
  already there and already indexed. What it does need: the `residency` table (LC16), and
  whatever ADR-0029's claim query turns out to require beyond the existing index. `attempt` is
  written only by the executor, never by a claim query (ADR-0029 §2), and P4 already respects that.

- **Resolved by the P5 run:** Right about the columns, wrong about one index: `0003` created the claim index ascending on every column, and `EXPLAIN QUERY PLAN` showed a temp B-tree on every claim. Migration `0004` recreates it as `(state, effective_priority DESC, created_at)` beside the `residency` table — see P5-2.

## LCX22 — What P4 did not build
- **Severity:** NOTE
- **Unit:** LoadCoach P4
- **Where:** N/A
- **What happened:** Deliberately absent, all of it "Deferred: the queue" or a later phase:
  `POST /jobs` and the whole `/jobs` API surface, `GET /jobs/{id}/stream`, cancellation over HTTP
  (`POST /jobs/{id}/cancel` — the executor honours a token, but nothing hands it one from outside
  a request), the circuit-breaker re-probe prompt (spec §9's second LoadCoach-originated prompt;
  the pack has one record, and the breaker that would use the second is P7), durable idempotency,
  priority, ageing, leases and `waiting_resources`. The `POST /generate` "cannot start within
  `max_latency_seconds`" behaviour is also queue-shaped and not implemented: a synchronous request
  runs immediately or fails.
- **What the next run must do:** This list is P5's and P7's scope, in that order.

- **Resolved by the P5 run:** Everything on this list except the re-probe *prompt* and the `POST /generate` "cannot start within `max_latency_seconds`" behaviour, which stay with P7 and with the synchronous path respectively. The breaker mechanism itself was P5's (the prompt was right that the handoff misfiled it): `domain/circuit_breaker.py` over `job_attempts` outcomes, input swappable for P7's `reliability_stats`.

## LCX23 — mirrorwall 0.2.0 prepared, not published
- **Severity:** NOTE
- **Unit:** MirrorWall P2
- **Where:** `py/MirrorWall/{CHANGELOG.md,README.md,src/mirrorwall/__about__.py}`
- **What happened:** P4 acceptance criterion 3 reads "`mirrorwall 0.2.0` published; LoadCoach's UI
  runs on it." The second half is done and demonstrated. The first stops at the publish step per
  this run's instructions: `__about__.py` already read `0.2.0`, `CHANGELOG.md` now has a dated
  `## [0.2.0] — 2026-08-29` section, and `README.md`'s status and quickstart describe the real
  surface. **No tag, no `git push`, no upload — none were attempted.** LoadCoach consumes it
  through an editable install (`pip install -e ../py/MirrorWall`), which satisfies its
  `mirrorwall>=0.2,<0.3` pin without an index.
- **What the next run must do:** Follow packaging-and-release-standards.md §6 from step 4 onward,
  as WDB3 and SS6 say for their own packages. Note that three releases are now prepared and
  unpublished: `weightsdb 0.2.0`, `setspec 0.4.0` and `mirrorwall 0.2.0`. They should go out in
  dependency order, and LoadCoach's editable installs should be re-pinned only afterwards.

- **Resolved by the P6 run:** **Still unpublished, and now blocking, exactly as WDB3 is.** `pip index versions mirrorwall` reports no distribution and `py/MirrorWall` carries no tag. Of the three releases this entry grouped, only `setspec 0.4.0` actually went out. See P6-9.

## LCX24 — An escaping test that passed for the wrong reason
- **Severity:** NOTE
- **Unit:** MirrorWall P1 (LoadCoach adoption)
- **Where:** `LoadCoach/tests/e2e/test_models_and_task_profiles.py`
- **What happened:** `test_ui_pages_escape_untrusted_content` asserted that `/models` contained no
  `<script>` — on a page into which nothing hostile had been injected. It had never tested
  escaping at all, and it broke the moment MirrorWall's shell added its legitimate pre-paint theme
  bootstrap. Rewritten to insert a model whose name is `<script>alert("xss")</script>` and assert
  it comes back escaped, while the shell's own inline script stays.
- **What the next run must do:** Nothing. Worth the general lesson: an assertion that something
  bad is absent proves nothing unless the test put something bad in first.

---

# M4 Handoff — handoff-review run

Run started 2026-08-29, after the two runs above. This half exists because the handoff was read
back and acted on: every entry above whose "what the next run must do" was still open has been
closed or is explained below, and auditing the "gate green" claims turned up a set of CI failures
neither earlier run would have seen.

## What was done to the earlier runs' entries

| Entry | What this run did |
|---|---|
| **LC1 / LCX10** (scaffold configs) | **Closed.** IdeaPress, the last untouched scaffold, had all five defects plus a sixth — see HR1. |
| **LC2** (`py.typed`) | **Closed.** The quickstart mention is written, and a contract test now asserts the marker ships. |
| **LC5** (`migration_harness`) | **Closed enough.** Now exercised by WeightsDB's own migration tests; the shape held up unchanged under first use. A downstream consumer still has not used it. |
| **LC14** (`tasks list` before `serve`) | **Closed.** The automated regression test the entry asked for is written and mutation-checked. |
| **WDB4** (`types.py` shim claim) | **Closed.** Grepped: all seven revisions import the module. The checklist now records this as verified. |
| LC3–LC4, LC6–LC13, LC15–LC16, WDB1–WDB2, SS1–SS6, LCX1–LCX9, LCX11–LCX22, LCX24 | Nothing needed — each already read "Nothing", is DEFERRED to a phase that has not started, or is a release step that is a human decision (WDB3, SS6, LCX23). |

**The three prepared-but-unpublished releases are still unpublished.** `weightsdb 0.2.0`,
`setspec 0.4.0` and `mirrorwall 0.2.0` remain as WDB3, SS6 and LCX23 describe them: no tag, no
push, no upload. That is deliberate and unchanged.

---

## HR1 — IdeaPress's scaffold had all five LC1 defects, plus one that broke `pip install`
- **Severity:** NOTE
- **Unit:** handoff-review
- **Where:** `IdeaPress/{.importlinter,pyproject.toml}`
- **What happened:** LC1's closing advice, repeated by LCX10, was to check the last scaffold before
  its first gate. IdeaPress had every one of the five: plural `root_packages` with a bare string
  value, no `include_external_packages` (its `forbidden` contracts name `freeweight` and
  `loadcoach`, both outside the root package), fully-qualified `layers` entries alongside
  `containers = ideapress` (import-linter would have looked for `ideapress.ideapress.web`), no
  `mypy_path`/`explicit_package_bases`, and no `D1` exemption for Alembic revisions. It also had a
  sixth defect the earlier scaffolds did not: the `dev` extra's last entry was the *string*
  `"loadcoach  # test-only: OpenAPI snapshot for contract tests, never imported under src/"` — a
  TOML comment written **inside** the requirement, which is not a valid PEP 508 specifier, so
  `pip install -e ".[dev]"` fails before any gate can run. LoadCoach's own pyproject has the same
  intent expressed correctly, as a TOML comment above a bare `"freeweight"`; IdeaPress now matches.
- **Verified, not assumed:** with the fixes applied, `lint-imports` reports 4 contracts kept (it
  previously could not build a graph at all), `ruff format --check`/`ruff check` pass on 78 files,
  and `mypy src tests` reports no issues across 70 source files — run against IdeaPress's tree with
  LoadCoach's toolchain, since IdeaPress has no venv of its own yet.
- **What the next run must do:** Nothing. IdeaPress P1 can now run its gate on the first try. There
  are no further scaffolds — every repo in the workspace has been checked.

## HR2 — Three of WeightsDB's CI jobs were failing, and the local gate cannot see any of them
- **Severity:** BLOCKER (now fixed)
- **Unit:** handoff-review
- **Where:** `py/WeightsDB/{pyproject.toml,.github/workflows/ci.yml}`, `py/WeightsDB/tests/**`
- **What happened:** Both earlier runs report "gate green", and both were right about the gate they
  ran — `ruff format --check`, `ruff check`, `mypy src tests`, `lint-imports`, `pytest`. That gate
  is the one CLAUDE.md documents, and it exercises **none** of the three CI jobs that were red:
  1. **`coverage` failed.** The job runs `--cov-fail-under=85`; actual coverage was **78.89%**. The
     default `pytest` invocation passes no `--cov` at all, so nothing local ever reported this.
  2. **`db-matrix` failed with exit 5.** It runs `pytest -m integration`, but `integration` is not
     a marker this repo declares or applies to anything, so it collected **zero tests**. The whole
     point of the job — exercising WeightsDB against a real PostgreSQL 16 service — never happened,
     and it had never happened, on any commit.
  3. **`contracts` failed with exit 5**, the same way: `pytest -m contract` collected zero tests.
- **What was done:** Coverage is now **95.23%**, the floor is **95** (the shared-package standard;
  WeightsDB was the only `py/` package still on the 85 apps floor, which is the same defect LCX10
  fixed for MirrorWall), and both marker jobs select real tests. See HR3 and HR4 for the detail.
- **What the next run must do:** **Run the CI jobs, not just the local gate, before claiming green.**
  The local gate in CLAUDE.md is a subset. `pytest --cov --cov-report=term-missing --cov-fail-under=<floor>`
  and each marker/path job from `.github/workflows/ci.yml` are the parts it omits, and all three
  failures above lived exactly in that gap.

- **Resolved by the P5 run:** Ran the omitted jobs before the final report: `--cov --cov-fail-under=85` reports 90 % (89.29 % at the start of the phase), and `pytest -m "not live and not performance" tests/integration` collects and passes 105 (2 skipped for PostgreSQL). LoadCoach's `contracts` job is still knowingly red until P6.

- **Resolved by the P6 run:** The lesson was applied and it paid again. Beyond the local gate this run reports coverage (90.16 % against an 85 floor), `pytest -m contract` (23) and `pytest -m "not live and not performance" tests/integration` (198, 2 skipped) — and then went further, because a job that installs the package is not the job that runs locally: `pip install .` in a fresh non-root virtualenv **fails**, and every LoadCoach CI job is red for a reason no local gate can see. See P6-9.

## HR3 — WeightsDB coverage: 78.89% → 95.23%, and what is left is genuinely server-only
- **Severity:** NOTE
- **Unit:** handoff-review
- **Where:** `py/WeightsDB/tests/{unit,integration}/**`, `py/WeightsDB/pyproject.toml`
- **What happened:** 47 tests added across five files, chosen by reading the missing-line report
  rather than by writing whatever was easy. The large gaps were `backup.py` (67% — the entire
  compression path, the entire `pg_dump` path, and most error branches were untested), `health.py`
  (80%) and `engine.py` (80%). Three techniques carried most of it, all of them honest:
  * **A PostgreSQL engine constructs without connecting** (spec §15's own claim), so every
    `dialect.name != "sqlite"` early return, `pg_restore_command`, and the `pg_dump` argv/`PGPASSWORD`
    construction are testable with no server — `subprocess.run` is monkeypatched for the last, and
    the test asserts the password goes in the environment and never into argv.
  * **The connect listener can be called directly.** `_configure_postgresql`'s and
    `_configure_sqlite`'s `connect` listeners are picked out of `engine.pool.dispatch.connect` by
    `__module__` and invoked with a recording DBAPI stub, which pins the exact statements issued —
    including that the values go through `set_config(...)` rather than `SET ... = %s`, the bug the
    source comment describes.
  * **Corruption has two shapes and both are now covered.** Zeroing a SQLite file's last page makes
    `PRAGMA integrity_check` answer with a *row* naming the damaged tree; zeroing interior pages
    makes it *raise* instead. `_verify_backup_file` handles both and the tests now produce both.
- **A note on the margin:** 95.23% against a 95 floor is 0.23% of headroom, and the coverage job
  runs without PostgreSQL and without the `postgres` extra. Nearly everything still uncovered needs
  a live server — `upsert`'s PostgreSQL branch, `temporary_postgres`' internals, `integrity_check`
  and `database_size_bytes` on PostgreSQL. **If a future phase adds code and this job goes red by a
  hair, the fix is to give the `coverage` job the same `postgres:16` service `db-matrix` already
  has, not to lower the floor** — those paths are covered by the suite, just not by that job.
- **What the next run must do:** Nothing. Re-run `pytest --cov --cov-report=term-missing` after any
  change to `py/WeightsDB/src`.

## HR4 — A dead rollback branch, and a submodule shadowed by its own re-export
- **Severity:** NOTE
- **Unit:** handoff-review
- **Where:** `py/WeightsDB/src/weightsdb/{backup.py,__init__.py}`
- **What happened:** Two things surfaced while writing HR3's tests. Neither is a bug with a
  consequence, and neither was changed — they are recorded because both cost time to work out.
  * **`restore()`'s no-original rollback branch is unreachable.** `restore` computes
    `had_original = target_path.is_file()` *after* calling `_checkpoint_and_release(engine)`, and
    that connects, and connecting to SQLite creates the file. So `had_original` is always `True` by
    that point and the `else: target_path.unlink(missing_ok=True)` arm cannot run. A test claiming
    to exercise it was written, failed, and was deleted rather than weakened — asserting on
    something that cannot happen is worse than leaving the line uncovered.
  * **`weightsdb.backup` the submodule is shadowed by `weightsdb.backup` the function.**
    `__init__.py` re-exports the `backup` function, so `from weightsdb import backup`,
    `import weightsdb.backup as m`, and monkeypatch's dotted-string form all resolve to the
    *function*. Reaching the module's globals needs `import_module("weightsdb.backup")`. This is
    the documented public API (spec §7 names `backup`), so it stays; the test file carries a
    comment saying why the awkward import is there.
- **What the next run must do:** Nothing. If `restore()` is ever revisited, moving the
  `had_original` read above `_checkpoint_and_release` would make the branch live again.

## HR5 — LoadCoach's PostgreSQL job never ran a test either
- **Severity:** NOTE
- **Unit:** handoff-review
- **Where:** `LoadCoach/.github/workflows/ci.yml`
- **What happened:** The identical `pytest -m integration` defect from HR2, in a repo with a large,
  real integration suite: 70 tests under `tests/integration`, none of which had ever run against the
  `postgres:16` service the job spins up. Fixed the same way, and the same way FreeWeight's own
  db-matrix job has always done it — `pytest -m "not live and not performance" tests/integration`,
  selecting by path rather than by a marker nobody applies. Verified: the job now collects and
  passes 70 tests, 2 skipped. LoadCoach's `coverage` job was checked at the same time and is fine
  (89.29% against its 85 applications floor).
- **What the next run must do:** Nothing for this job.

## HR6 — Two `contract` CI jobs are still red, and both are waiting on unbuilt phases
- **Severity:** DEFERRED
- **Unit:** handoff-review
- **Where:** `LoadCoach/.github/workflows/ci.yml`, `py/MirrorWall/.github/workflows/ci.yml`
- **What happened:** `pytest -m contract` collects nothing in LoadCoach or MirrorWall, so both jobs
  fail with exit 5 exactly as WeightsDB's did. Unlike WeightsDB's, neither can honestly be closed
  from here:
  * **LoadCoach** has `tests/contract/test_evidence_import.py` and `test_schema_rejection.py`, both
    still one-line scaffolds. They belong to P6 (evidence import), which does not exist yet.
    Writing them now would mean inventing tests for a feature nobody has built.
  * **MirrorWall** has no contract tests at all and is at P2 of a longer plan.
  WeightsDB's was closable because its phase is complete and its release is prepared, so pinning the
  published surface is work that was genuinely due — `tests/contract/test_public_api.py` asserts
  `__all__` in **both** directions (nothing removed, nothing added without a contract change), that
  every name resolves, that `py.typed` ships (which is LC2's regression guard), and that the package
  exports no `MetaData`/`Table`/`DeclarativeBase`, which is database standards §1 stated as a test.
- **What the next run must do:** **P6 closes LoadCoach's**, by writing the two scaffolded files.
  MirrorWall's closes whenever its contract surface is worth pinning — the WeightsDB file above is a
  ready-made pattern for a shared package, and MirrorWall 0.2.0 being a prepared release is a fair
  argument for doing it at the same time as that publish. Until then both jobs are known-red for a
  stated reason, which is better than the silent zero-test pass they had before.

- **Resolved by the P6 run:** **LoadCoach's half is closed.** `tests/contract/test_evidence_import.py` and `test_schema_rejection.py` are written and `pytest -m contract` reports 23 passed. MirrorWall's was already closed by its 0.2.0 release (16 passed, verified in this run). Both `contract` jobs are now green rather than known-red.

## HR7 — What this run deliberately did not touch
- **Severity:** NOTE
- **Unit:** handoff-review
- **Where:** N/A
- **What happened:** For the record, so the next run does not go looking:
  * **The three prepared releases** (WDB3, SS6, LCX23) — still tag-less and unpublished, per those
    entries' own instruction that this is a human decision.
  * **LC15** (`GET /models/{ref}`, `GET /task-profiles/{id}`) and **LC16** (`models residency`) —
    still DEFERRED, to the phases the P3–P4 run identified.
  * **FreeWeight** — read only. WDB4's grep was a read; nothing in that repository was modified.
  * **`weightsdb.session`, routing, execution, the estimator** — every DECISION entry above was
    re-read, and none needed revisiting on the evidence available now.


---

# M4 Handoff — P5 run (LoadCoach P5: queue, scheduling and recovery)

Run started 2026-08-29, after the handoff-review run above. Ground check at `7925ea1` was green
(215 passed, 2 skipped); the review run's two uncommitted files were committed first as
`e90e932`. Eight units, eight commits, `0aed07c` … `97f5fc9`, plus a docs-mirror refresh
(`a51b1a7`), the last two performance budgets (`badde56`) and one fix-forward (P5-18). Final
gate: 470 passed, 2 skipped, pytest exit status 0 under `pipefail`; coverage 90 %; every
performance budget met (the numbers are in the final report).

## What was done to the earlier runs' entries

Every entry the prompt named as binding P5 (LC8, LC16, LCX3, LCX8, LCX9, LCX16, LCX18, LCX19,
LCX21, LCX22, HR2) carries a **Resolved by the P5 run** line above. No entry was a BLOCKER; every
DECISION was checked against what the queue needs and only LC8 needed settling (it is settled at
`>=`). The three prepared-but-unpublished releases (WDB3, SS6, LCX23) are untouched.

## P5-1 — ADR-0036: the transition table had no recovery edge for three lease-holding states
- **Severity:** DECISION
- **Unit:** P5 unit 1
- **Where:** `docs/adr/0036-queue-recovery-transitions.md`, `docs/apps/loadcoach/queue-and-scheduling.md` §2 (and its mirror), `LoadCoach/src/loadcoach/domain/queue_state.py`
- **What happened:** Queue §2 called its table "normative and complete", and it was not: `admitted`,
  `validating` and `retrying` hold a lease and are persisted, but only `leased` and `executing` had a
  lease-expiry edge, so a process that died in `admitted` — which queue §12 explicitly requires
  recovering from — had no legal successor. `retrying` also lacked `→ cancelling`. Per CLAUDE.md
  ("close it with a new ADR before writing code"), ADR-0036 adds six edges (recovery from every
  lease-holding state by idempotency; `retrying → cancelling`) and names `NO_ELIGIBLE_MODEL` as a
  second reason on the existing `leased → failed` edge. The table now has thirty edges;
  `test_queue_state.py` enumerates all 121 pairs.
- **What the next run must do:** Nothing. If the table changes again, change the ADR's successor,
  `_DOCUMENTED_EDGES` in the test, and `TRANSITIONS` together — the test fails on any one of them
  drifting.

## P5-2 — Migration `0004` adds `residency` **and** corrects the claim index's direction
- **Severity:** DECISION
- **Unit:** P5 unit 1
- **Where:** `LoadCoach/src/loadcoach/infrastructure/db/migrations/versions/0004_residency.py`, `models.py`
- **What happened:** The prompt said `0004` adds `residency` and nothing else, on the strength of
  LCX21's claim that the claim query's `(state, effective_priority DESC, created_at)` index already
  existed. It existed without the `DESC`, and `EXPLAIN QUERY PLAN` on the real claim statement
  reported `USE TEMP B-TREE FOR LAST TERM OF ORDER BY` — every claim sorting the whole
  equal-priority group. `0004` drops and recreates the index with the direction the data model
  always named (no column of any `0003` table is touched); the model declares it as
  `Job.effective_priority.desc()` at module level, which Alembic's parity compares correctly
  (a `text("... DESC")` element does not). `check_parity` passes on SQLite, where reflection drops
  direction, and the DESC form is what PostgreSQL reflects.
- **What the next run must do:** Nothing. `test_migration_0004_adds_residency_and_fixes_the_claim_index_direction`
  asserts both the table and the absence of the temp B-tree.

## P5-3 — `queue.idempotency_ttl_hours` and `queue.cancelling_watchdog_seconds` were missing from configuration
- **Severity:** DECISION
- **Unit:** P5 unit 1
- **Where:** `LoadCoach/src/loadcoach/config.py` (`QueueSettings`)
- **What happened:** `data-model.md` §2 and `api.md` §4 both assume `queue.idempotency_ttl_hours`
  (default 24) and neither `spec.md` §12's block nor `config.py` had it. Added, default 24. Queue §9
  lists the cancelling watchdog (30 s) among the timeouts and says all of them are configurable, and
  nothing carried it either: added `cancelling_watchdog_seconds`, default 30. Both are in
  `EXAMPLE_CONFIG_TOML`. `spec.md` §12 was **not** edited (its block is a summary and the two
  documents that already assume the setting are the authority).
- **What the next run must do:** Nothing.

## P5-4 — The starvation counter's threshold is half the job's own `max_wait_seconds`
- **Severity:** DECISION
- **Unit:** P5 unit 1
- **Where:** `LoadCoach/src/loadcoach/domain/priority.py` (`STARVATION_FRACTION_OF_MAX_WAIT`)
- **What happened:** Queue §4 names "a starvation counter (jobs waiting beyond a threshold)" and no
  threshold. The ageing horizon was considered and rejected: under the shipped defaults a
  `background` job reaches its cap after 399 minutes, long after its 60-minute `max_wait`, so a
  counter defined that way could never be non-zero on a default install. Half of the job's own
  bound is what makes health say *degraded* before any job fails with `MAX_WAIT_EXCEEDED`, and it
  needs no setting.
- **What the next run must do:** Nothing unless an operator wants it configurable — then it is a
  `QueueSettings` field, not a change to the counter's meaning.

## P5-5 — `jobs.max_attempts` is `execution.max_attempts`, the total across leases
- **Severity:** DECISION
- **Unit:** P5 unit 3
- **Where:** `LoadCoach/src/loadcoach/services/queue.py` (`enqueue`), `services/worker.py` (`_attempts`)
- **What happened:** Two "max attempts" exist: `[execution].max_attempts` (settings, default 3) and
  the task profile's `execution.max_attempts` (P4's per-candidate corrective-retry limit). ADR-0029
  §2 says the job's counter "counts total attempts across leases, which is the semantics a caller
  expects from 'retry at most three times'". So `jobs.max_attempts` is the settings value and bounds
  the job's total; the profile's value is the per-candidate budget for timeouts and corrective
  retries within it. With the defaults a three-candidate profile can be cut short by the total —
  that is the documented meaning, not a defect.
- **What the next run must do:** Nothing. If a caller needs more, `POST /jobs` could accept a
  `max_attempts` override; api.md §5 does not list one today.

## P5-6 — Admission reservations are conservative on purpose
- **Severity:** DECISION
- **Unit:** P5 unit 5
- **Where:** `LoadCoach/src/loadcoach/services/worker.py` (`QueueRuntime.admission_snapshot`), `domain/admission.py`
- **What happened:** Above `max_concurrent_jobs = 1`, every other in-flight job's estimate is
  subtracted from *its* device before routing sees the snapshot — unless that job's model is already
  resident there, in which case telemetry already counts it and reserving again would double-count.
  Idle residents' memory is counted as reclaimable because the residency policy will evict them for
  room. A job whose model is loading but not yet resident is therefore reserved in full, which can
  defer a second job that would in fact have fit for the seconds a load takes. Deferral is the safe
  direction (queue §5: never optimistic); LCX4's two constants remain the ones that can be wrong the
  other way.
- **What the next run must do:** Nothing. If deferrals look too eager on a real machine, look at
  `admission_snapshot` before touching the estimator.

## P5-7 — A resident model fits on its device whatever the estimate says
- **Severity:** DECISION
- **Unit:** P5 unit 5
- **Where:** `LoadCoach/src/loadcoach/domain/routing/constraints.py` (`ConstraintInputs.resident_devices`)
- **What happened:** Queue §5's exception is stated for an unknown estimate ("unless the model is
  already resident"). Applied to a known estimate too: a resident model's weights and KV cache are
  already allocated, so free memory *excluding* it is the wrong number to test it against — the
  constraint as P3 wrote it would reject the very model that is currently running on a nearly full
  card. Its resident device is also preferred over another that merely has room, since choosing the
  other would load a second copy. The caveat: residency is recorded per model, not per runtime
  profile; a resident model asked for a different served context would reload, and the estimate
  for that reload is not re-checked.
- **What the next run must do:** P7, or whoever first sees an OOM on a resident model under a
  changed profile, should key residency by `(model, profile_hash)` — the row and `LoadResult`
  already carry the hash.

## P5-8 — Model placement is a simulation input, not something LoadCoach controls
- **Severity:** NOTE
- **Unit:** P5 unit 5
- **Where:** `LoadCoach/tests/simulation/simulator.py` (`Simulation(placement=...)`)
- **What happened:** ModelRack's `load` names no device (ADR-0027: providers do not report
  placement), so LoadCoach's `target_gpu_index` is where admission expects the model and the
  runtime puts it wherever it likes. The simulator makes that explicit: which device a loaded model
  occupies is a scenario parameter. The multi-device properties are written so that admission's
  choice and the simulated placement agree, which is the honest situation to test; a disagreement is
  "the divergence between estimate and observed placement" ADR-0027 §2 already describes.
- **What the next run must do:** Nothing.

## P5-9 — The circuit breaker: constants, and who the probe is
- **Severity:** DECISION
- **Unit:** P5 unit 6
- **Where:** `LoadCoach/src/loadcoach/domain/circuit_breaker.py`, `services/worker.py` (`_route`)
- **What happened:** Queue §7 names a window, a threshold and a cool-down and gives none a number.
  Chosen and documented as constants: a 600 s window, at least 5 samples, a failure rate of 0.5
  opens, a 300 s cool-down. Samples come from `job_attempts` in the window (`breaker_samples`);
  the source is a callable P7 swaps for `reliability_stats`. Two semantics were decided: a
  successful probe closes the breaker **and stops counting the failures that opened it** (otherwise
  the same window re-opens it at once — the first version of the state machine did exactly that and
  the unit test caught it), and the probe is the first job that routes while the breaker is
  half-open, with later jobs excluding the model until the probe reports. P7's dedicated
  low-priority probe job with its own prompt record is unchanged in scope.
- **What the next run must do:** P7 supplies `breaker_source` from `reliability_stats` and the
  re-probe prompt; the state machine and the explanation plumbing (`recently_failing` now carries
  state, reason and expiry) need no change.

- **Resolved by the M5 run:** `breaker_source` now reads `services.reliability.breaker_samples` — the same attempt rows the statistics are computed from, classified by the statistics' own success rule — and a changed verdict is persisted onto `reliability_stats` (M5-4). The state machine *did* need one change after all, and not for P7's reasons: the worker marked the probe for every ranked candidate at routing time, so a fallback that never ran left the model excluded until nothing ever reported (M5-3). The probe is now marked when execution starts, handed back if that attempt is cancelled, and presumed lost after one cool-down. The dedicated low-priority probe job with its own prompt record was **not** built: the first real job that routes to the half-open model is the probe, which costs no synthetic prompt and is what P5 already did.

## P5-10 — Two frame vocabularies share `job_events`
- **Severity:** DECISION
- **Unit:** P5 unit 8
- **Where:** `LoadCoach/src/loadcoach/services/job_events.py` (`is_job_event`)
- **What happened:** A queued job's stream is api.md §5's `job.*` events with the entity/data
  envelope payload (API standards §8). A synchronous execution's stream is api.md §4's
  `routing` → `token`… → `result`/`error`, whose envelope payload is the document itself. Both
  are persisted in the same table; the rule that decides the payload shape on the way in and on
  replay is the event type's prefix, in one function. Token frames are `token` (bare) on both
  streams — api.md §5 lists `job.token`, but MirrorWall's bare-frame exception is keyed on exactly
  `token` and widening it is forbidden.
- **What the next run must do:** Nothing.

## P5-11 — Token frames are not replayed after completion; P4's reconnect tests were tightened
- **Severity:** DECISION
- **Unit:** P5 unit 8
- **Where:** `LoadCoach/tests/integration/test_streaming.py`, `services/job_events.py` (`LIVE_BUFFER_SIZE`)
- **What happened:** api.md §4 promises that a repeated key "replays the completed job's `result`
  event" and that reconnection "replays from the persisted job events". P4's in-memory log replayed
  every token too, and its two reconnect tests asserted that. With tokens deliberately unpersisted,
  a reconnect replays the persisted frames after `Last-Event-ID` — `routing` and the terminal — and
  a client that attaches while the job is still running also receives the tokens already fanned out,
  from a bounded per-job buffer that is dropped at the terminal frame. The two tests now assert
  exactly that; one row, one execution, same `job_id`. One documented edge remains: a `job.*` event
  written by another process (a CLI cancel) takes the stored maximum sequence plus one, which a
  client mid-stream in the serving process may drop as already seen.
- **What the next run must do:** Nothing unless token replay after completion becomes a
  requirement — then it is one row per token, which P4 rejected for a reason.

- **Resolved by the M5 run:** Honoured by the P8 pages: the job page renders from the persisted document and the persisted events, never from token frames, and the live queue page's frames are full-state snapshots of the queue report, so neither page has anything to expect from a token replay and neither looks broken on reconnect.

## P5-12 — A cancel from another process reaches the token through the keeper
- **Severity:** NOTE
- **Unit:** P5 unit 7
- **Where:** `LoadCoach/src/loadcoach/services/queue.py` (`cancel_job(on_request=...)`), `services/worker.py` (`Scheduler.keep_leases`)
- **What happened:** `cancel_job` is pure database; the route passes the in-flight registry's
  `request_cancel` so the serving process's provider call stops within one chunk. `loadcoach job
  cancel` has no such hook; the keeper carries `cancel_requested` from the row to the token at its
  next renewal (≤ `lease_renewal_interval_seconds`), and the worker re-reads the flag at the one
  boundary before a provider call, so a cancel during a model load takes effect at once. The
  watchdog is the backstop for a provider that never reaches a chunk boundary.
- **What the next run must do:** Nothing.

## P5-13 — Queue control flags live in the `settings` table
- **Severity:** DECISION
- **Unit:** P5 unit 8
- **Where:** `LoadCoach/src/loadcoach/services/queue.py` (`set_queue_flag`, `queue_flags`)
- **What happened:** `loadcoach queue pause` runs in a different process from `serve`, so an
  in-memory flag would be invisible to it. `queue.paused` and `queue.draining` are rows in
  `settings`; the scheduler re-reads them every second and a restart honours them. The first
  simulation attempt to pause through the in-memory flag was silently overwritten by that refresh —
  which is how the durable path became the only path.
- **What the next run must do:** Nothing.

## P5-14 — Files beyond the phase's literal list
- **Severity:** NOTE
- **Unit:** P5
- **Where:** `LoadCoach/src/loadcoach/services/{job_events,status}.py`, `domain/retry_policy.py`, `tests/simulation/test_simulator_mechanics.py`, `tests/integration/{test_worker,test_jobs_api}.py`, `tests/unit/{test_queue_state,test_priority,test_admission,test_residency_service,test_retry_policy,test_circuit_breaker}.py`, `tests/performance/test_queue_budgets.py`
- **What happened:** Each is forced by the plan's own text the way LC9 describes: the event sink is
  needed by the queue service, the worker and two routes, and cannot live in any one of them
  without the others importing it for the wrong reason; the status report is shared by the API,
  the page and the CLI, which may not import each other; the §7 table is a pure decision and
  therefore domain; the simulator's own mechanics had to be proven before a scheduler existed to
  point them at; and the unit/property/performance tests the plan's Tests list requires needed
  homes. `docs/apps/loadcoach/development-plan.md`'s file list was not edited.
- **What the next run must do:** Treat them as part of P5's real surface.

## P5-15 — Request transcripts are stored on the job row
- **Severity:** NOTE
- **Unit:** P5 unit 3
- **Where:** `LoadCoach/src/loadcoach/services/queue.py` (`JobSubmission.as_request_json`)
- **What happened:** A queued job runs after its submitter has gone, possibly after a restart, so
  `request_json` carries the full transcript, not only its hash. Spec §14's "prompts and responses
  are stored as hashes by default" is a retention statement; P4 already stores `response_text` on
  every job. Nothing scrubs the transcript after completion.
- **What the next run must do:** When content retention becomes a setting (P8's dashboard and
  retention work is the natural place), scrub `request_json["messages"]` and `response_text` for
  terminal jobs there — a queued job must keep its transcript until it has run.

- **Resolved by the M5 run:** Built as P8's retention sweep (`services/retention.py`, M5-14). A queued job keeps its transcript until it has run, exactly as this entry required; a terminal job keeps its text for `[storage] content_retention_hours` (24 by default, runtime-changeable) and then loses `prompt_text`, `response_text`, the structured output, tool calls, reasoning summary, the `messages` in `request_json` and the `output` of its persisted `job.completed` event, keeping every hash, count, timing and the routing. `retain_content = true` keeps everything and is config-only.

## P5-16 — A `git checkout --` on an uncommitted file cost one rewrite; use copies for mutation checks
- **Severity:** NOTE
- **Unit:** P5 unit 4
- **Where:** N/A (process)
- **What happened:** Mutation-checking the keeper by editing `services/worker.py` and restoring it
  with `git checkout --` restored the committed *scaffold* — the whole unit-4 implementation was
  uncommitted at that moment — and the file had to be rewritten from the session's own edit history.
  Every later mutation check backed the file up with `cp` and restored it byte-for-byte. Also worth
  knowing: an edit script that asserts on an anchor **after `ruff format` has re-wrapped it** aborts
  before writing anything, which happened three times; anchoring on function names survives that.
- **What the next run must do:** Never `git checkout` a file that carries uncommitted work; commit
  first or copy first.

## P5-17 — What P5 deliberately did not build
- **Severity:** NOTE
- **Unit:** P5
- **Where:** N/A
- **What happened:** Nothing under the phase's Deferred list (evidence import, production feedback)
  was touched. Also absent, each with its phase: `POST /jobs/{id}/feedback` (P7, with the feedback
  service), the breaker's re-probe prompt record and its `reliability_stats` source (P7), the
  `POST /generate` "cannot start within `max_latency_seconds`" behaviour (synchronous path,
  unscheduled), `tests/e2e/test_dashboard.py` (the dashboard is P8's), and content scrubbing
  (P5-15). Residency on a machine with no GPU degrades to load-on-demand with the reason
  `no_device` recorded on the attempt's event: there is no device to be resident on, and inventing a
  `gpu_index` for host memory would be a fabricated measurement.
- **What the next run must do:** P6 writes `tests/contract/` (HR6); P7 takes the items above.

- **Resolved by the P6 run:** Everything P5 left for P6 is done: `tests/contract/` is written (HR6) and the phase's own Deferred item — production feedback — was not touched. `POST /jobs/{id}/feedback`, the re-probe prompt record, `reliability_stats` as the breaker source, the `POST /generate` `max_latency_seconds` behaviour, the dashboard and content scrubbing all remain P7's and P8's.

## P5-18 — A pytest-randomly seed found a flag race, and the gate chain had been hiding exit codes
- **Severity:** NOTE (fixed)
- **Unit:** P5 unit 8
- **Where:** `LoadCoach/src/loadcoach/services/worker.py` (`QueueFlags.lock`), `web/routes/queue.py`
- **What happened:** `test_drain_stops_claiming_and_reports_no_in_flight_work` failed under seed 3
  of the final gate: the scheduler's once-a-second flag refresh had read `queue.draining` just before
  the route's write committed and assigned its stale copy just after the route set the in-memory
  flag, so a worker claimed during a drain. `QueueFlags` now carries a lock; the route writes the
  durable flag and the copy under it, and the refresh reads and assigns under it. Six seeds green
  afterwards, committed as a fix-forward after `badde56`. The gate chain that ran before it was
  `pytest … | grep | tail && git commit`, whose exit status is `tail`'s — the red run still chained
  into the commit. Every gate after that ran with `set -o pipefail` and printed `${PIPESTATUS[0]}`.
- **What the next run must do:** Keep `pipefail` on any gate that pipes pytest into a filter, and
  treat a seed-only failure as the real bug the repository's own rule says it is.

- **Resolved by the P6 run:** Kept. Every gate in this run ran under `set -o pipefail`, and the one seed-shaped failure that appeared (four tests reading the developer's real GPU) was treated as the real bug it was rather than re-run — see P6-6.

---

# M4 Handoff — P6 run (LoadCoach P6, M4 closeout)

Run started 2026-08-29, finished 2026-08-30, after the four runs above. Ground check at `ad32252`
was green exactly as the prompt predicted (470 passed, 2 skipped, coverage 89.67 %, working tree
clean); `pytest -m contract` collected nothing and exited 5, which was HR6 and is now closed.

Seven units, seven commits, `f32ac68` … `95e297c`. Final gate: **646 passed, 2 skipped**, coverage
**90.60 %** against an 85 floor, `pytest -m contract` **23 passed**, `pytest -m "not live and not
performance" tests/integration` **198 passed, 2 skipped**, `lint-imports` 4 contracts kept.
Every gate ran under `set -o pipefail` (P5-18).

**One BLOCKER, and it is not in this phase's code.** `weightsdb 0.2.0` and `mirrorwall 0.2.0` are
still unpublished, so `loadcoach` cannot be installed from an index at all — see P6-9. The prompt
stated all three held-back releases had gone out; only `setspec 0.4.0` did.

## What was done to the earlier runs' entries

Every entry the prompt named as binding P6 (LC7, LC12, LC13, LC15, LCX3, LCX5, LCX7, LCX20, HR6,
P5-17, P5-18) carries a **Resolved by the P6 run** line above, as do HR2, WDB3, SS6 and LCX23. No
entry in the four earlier sections was a BLOCKER. Two decisions were asked for explicitly and both
are recorded in place: **LC15 stays deferred** (the evidence UI needs neither detail route), and
**LCX20's validator genuinely cannot check `benchmark.evidence_bundle`**, so SetSpec's own models
do the validating and no second validator was written.

---

## P6-1 — Migration `0005` adds one column data model §2 did not list, and the reason is ADR-0025 §2
- **Severity:** DECISION
- **Unit:** P6 unit 5 (schema decided in unit 1, column added in unit 5)
- **Where:** `LoadCoach/src/loadcoach/infrastructure/db/models.py` (`CapabilityEvidence.record_json`),
  migration `0005`, `docs/apps/loadcoach/data-model.md` §2
- **What happened:** api.md §7 and ADR-0025 §2 require `GET /evidence` to return a collection whose
  items are real `capability.evidence` **SetSpec envelopes**. A payload rebuilt from data model §2's
  normative column list cannot be one: `ModelIdentityFields` requires `observed_at`, and the column
  projection does not carry it (ADR-0022 §1 defines the `model` field as "identity triple +
  `canonical_id` + `identity_confidence`"). Two honest options — emit a reduced document that is not
  a `capability.evidence`, or keep the producer's document. Kept the document, in one
  `record_json` column, and documented it in data model §2 with the reason. This is also the
  strongest available form of the same section's "never edited by LoadCoach": a re-export is the
  producer's bytes rather than a reconstruction that could drift from them. The queryable columns
  beside it are unchanged and still normative.
- **What the next run must do:** Nothing. If a future schema version makes the projection complete
  enough to rebuild a payload from, `record_json` becomes redundant rather than wrong; do not drop
  it without checking `EvidenceRow.as_envelope`'s one caller and the contract test that validates
  every stored record against `CapabilityEvidenceOut`.

## P6-2 — `token_efficiency` is a quality metric, not a performance one
- **Severity:** DECISION
- **Unit:** P6 unit 1
- **Where:** `LoadCoach/src/loadcoach/domain/evidence_policy.py` (`PERFORMANCE_CAPABILITY_ROOTS`)
- **What happened:** ADR-0017 gives performance/memory/energy metrics a 30-day half-life and hard-
  separates them on `machine_fingerprint`; quality gets 90 days and travels between machines with a
  badge. Nothing says which capability roots are which. Chose `speed`, `latency`,
  `memory_efficiency` and `energy_efficiency`, and deliberately **excluded** `token_efficiency`:
  FreeWeight's benchmark catalog §6 maps it to `native.token_economy`, which counts how many tokens
  a model spends to finish a task — a property of the model's behaviour that does not change when
  the GPU does. Grouping it with the other three `*_efficiency` roots on the strength of its name
  would discard usable evidence for no measurement reason.
- **What the next run must do:** Nothing. If FreeWeight ever redefines `token_economy` as a
  throughput measure, move the root and say so in the constant's docstring, which carries this
  reasoning.

## P6-3 — Validation is SetSpec's, and `domain/validation.py` was checked before being ruled out
- **Severity:** DECISION
- **Unit:** P6 unit 2
- **Where:** `LoadCoach/src/loadcoach/services/evidence.py`
- **What happened:** LCX20's validator raises `SchemaUnsupported` on `$defs`, `$ref` and `anyOf`,
  all three of which `json_schema_for("benchmark.evidence_bundle", 1.0)` uses — verified by running
  it, not by reading it. So the bundle is validated through `CapabilityEvidenceIn` per record and
  through the envelope's own `load_envelope`. That is strictly stronger than the JSON Schema would
  have been: the pydantic models carry the cross-field rules the schema cannot express
  (`canonical_id` recomputed from the identity triple, `measured_at` not after `computed_at`, the
  capability vocabulary check at the record's declared `vocabulary_version`).
  **Per record, not per bundle**, so one malformed record is rejected by name and the rest import —
  which is what api.md §7's "per-record reporting" asks for and what `EvidenceBundleIn` alone
  cannot give.
- **What the next run must do:** Nothing. Do not add `jsonschema` for this; the models already
  check more than a schema can.

## P6-4 — Two size limits, with two different meanings
- **Severity:** DECISION
- **Unit:** P6 units 2 and 3
- **Where:** `freeweight_client.MAX_IMPORT_BYTES` (128 MiB), `services.evidence.MAX_PARSE_BYTES`
  (`setspec.MAX_PAYLOAD_BYTES`, 16 MiB)
- **What happened:** ADR-0026 §3 names 128 MiB as "the import limit"; SetSpec caps an envelope at
  16 MiB. Kept both, because they answer different questions: how much will we read from a
  stranger (a streaming transfer cap, refused with `EVIDENCE_SOURCE_REFUSED`), and how much JSON
  will we build objects from (refused with `EVIDENCE_IMPORT_FAILED`, naming both numbers). Raising
  a shared package's own guard eightfold from a consumer is the local weakening the suite refuses
  everywhere else. At roughly two kilobytes a record, 16 MiB is some eight thousand
  `(model, profile, machine, capability)` combinations — far past what one machine produces.
- **What the next run must do:** Nothing. If a real bundle ever exceeds 16 MiB, the fix is a
  SetSpec change to `MAX_PAYLOAD_BYTES`, not an override in this consumer.

## P6-5 — `accept_schema_majors` may narrow, never widen
- **Severity:** DECISION
- **Unit:** P6 unit 2
- **Where:** `LoadCoach/src/loadcoach/config.py` (`EvidenceSettings._check_majors_are_readable`)
- **What happened:** The setting existed with no validation. Configuring `[1, 2]` on a build whose
  SetSpec ships only v1 payload models would let a 2.0 bundle past negotiation and into a v1
  reader — the "partially parse a newer major" failure the whole contract exists to prevent. The
  validator refuses any major this build has no models for, naming both what was asked for and what
  is available. Narrowing (including to `[]`) stays legal: an installation entitled to refuse a
  major it *could* read is a real posture.
- **What the next run must do:** Nothing. When SetSpec publishes a v2 bundle, this validator starts
  accepting `2` with no change.

## P6-6 — Four tests read the developer's real GPU, and began failing mid-run
- **Severity:** NOTE (fixed)
- **Unit:** P6 unit 5
- **Where:** `LoadCoach/tests/conftest.py` (`_deterministic_telemetry`)
- **What happened:** `POST /route`, `loadcoach route explain` and the queue's e2e controls build a
  real `TelemetryCollector`, so they read whatever the machine's GPU is doing. Partway through this
  run an unrelated process (ComfyUI) took 11.7 GB of a 16 GB card, and four tests that had passed
  all session began failing with `insufficient_vram` — the correct answer to a question they had
  not meant to ask. Confirmed pre-existing by stashing the working tree and reproducing at
  `f90a8c2`. Coding standards §5 requires telemetry readers to be injected for exactly this reason;
  most of the suite honours it by passing a snapshot into `route()`, and the application paths did
  not. An autouse fixture now pins one machine (64 GiB RAM, one 48 GiB device with 1 GiB used) for
  the whole suite; a test needing different resources still passes its own snapshot.
- **What the next run must do:** Nothing. Note that this is why the I4 routing comparison injects a
  snapshot too — on this workstation no 8 GB model fits, and that is a true fact about the machine
  rather than anything about the evidence contract.

- **Resolved by the M5 run:** Still the fixture every P8 page test relies on — the System page asserts the pinned 48 GiB device and the telemetry bar test asserts a `telemetry.sampled` frame from the same pinned snapshot. One more thing of the same family was found and fixed: a module-scoped fixture is built *before* the function-scoped XDG isolation in `tests/conftest.py`, so the first draft of the accessibility checklist's fixture booted against the developer's real data directory (M5-15).

## P6-7 — `web/auth.py`, built narrow on purpose
- **Severity:** DECISION
- **Unit:** P6 unit 5
- **Where:** `LoadCoach/src/loadcoach/web/auth.py`
- **What happened:** Spec §14 and dev-plan P6's Tests list both require `POST /evidence/import` to
  be `admin`-scoped, and P9 owns auth hardening — so the mechanism did not exist and a test
  asserting the claim would have asserted nothing. Built the minimum that makes it enforceable:
  api.md §11's cumulative scope rule (`admin ⊃ write ⊃ read`), SHA-256 token lookup with a
  constant-time compare, revocation and expiry honoured, and loopback-with-no-tokens open so zero
  configuration still works (spec §20 AC1). **Not** built: token management commands, per-token
  rate limits, queue-depth caps, the LAN-exposure review. P9 extends this module rather than
  replacing it.
- **What the next run must do:** P9 starts from here. `require_scope` is called from one route
  today; applying it to the rest is a decorator or a dependency, not a rewrite.

- **Resolved by the M5 run:** Extended, not replaced. The scope rule moved to `domain/authorization.py` (`Principal`, `authorize`); `web/auth.py` now only establishes who is calling — bearer, the UI's token cookie, or the open loopback install — and hands a `Principal` to the route through a FastAPI dependency (`CurrentPrincipal`). `require_scope` is kept and implemented on top of it. Every API route except `/version` declares the principal (a contract test walks the route table), and every mutating service takes it and checks again (M5-17). Rate limits, the queue cap and the token commands — the four things this entry listed as not built — are built (M5-18, P8's `token create|list|revoke`).

## P6-8 — Files beyond the phase's literal list
- **Severity:** NOTE
- **Unit:** P6
- **Where:** `src/loadcoach/services/machine.py`, `src/loadcoach/web/auth.py`,
  `src/loadcoach/web/templates/evidence/index.html`, `src/loadcoach/cli/commands/evidence.py`,
  `tests/unit/{test_evidence_policy}.py`, `tests/integration/{test_evidence_importer,
  test_evidence_fetch,test_evidence_api}.py`, `requirements/**`
- **What happened:** The P5-14 pattern, for the same reasons. `services/machine.py` exists because
  the web layer, the CLI and the queue worker all need this machine's fingerprint and none may
  import another; `web/auth.py` because the phase's own Tests list requires an enforceable scope
  (P6-7); the CLI module and template because spec §7.2 and the Work item name the commands and the
  page; the four test files because the plan's ten Tests bullets needed homes and
  `tests/integration/test_evidence_import.py` would have collided by basename with the contract test
  the plan names (pytest refuses two test modules with one basename when there is no `__init__.py`),
  so the importer's integration tests are `test_evidence_importer.py`.
  `docs/apps/loadcoach/development-plan.md`'s file list was not edited.
- **What the next run must do:** Treat these as part of P6's real surface.

## P6-9 — **BLOCKER:** `weightsdb` and `mirrorwall` are unpublished, so LoadCoach installs nowhere
- **Severity:** BLOCKER (not fixable from a coding run)
- **Unit:** P6 unit 7
- **Where:** `LoadCoach/pyproject.toml`, `LoadCoach/requirements/README.md`,
  `LoadCoach/.github/workflows/ci.yml`
- **What happened:** The prompt said all three held-back releases had gone out. Confirmed as
  instructed, and two had not:

  ```console
  $ pip index versions setspec     → setspec (0.4.0)          # published, tagged v0.4.0
  $ pip index versions weightsdb   → No matching distribution found
  $ pip index versions mirrorwall  → No matching distribution found
  $ pip install .   # fresh, non-root virtualenv
  ERROR: Could not find a version that satisfies the requirement mirrorwall<0.3,>=0.2 (from loadcoach)
  ```

  Neither `py/WeightsDB` nor `py/MirrorWall` carries a tag. Both are **runtime** dependencies of
  `loadcoach`, so: `pip install loadcoach` cannot resolve; `pip-compile` fails with
  `No matching distribution found for weightsdb<0.3,>=0.2`, so `requirements/ci.lock` **cannot be
  generated** and must not be faked (a lock whose hashes name artifacts no index serves installs
  nowhere); and every CI job that installs the package's dependency set is red regardless of what
  this phase did. Locally the repository works only because both are editable installs pointing at
  sibling checkouts — precisely the arrangement a lockfile exists to stop a project mistaking for a
  working release.
- **What was done anyway:** everything that does not depend on the publish. `requirements/release.in`
  and `release.lock` are generated (Python 3.13, pip-tools 7.6.1, byte-identical to WeightsDB's) and
  audit clean under `pip-audit --require-hashes`; `release.yml` replaces the 803-byte stub with
  WeightsDB's shape; CI's `build` job uses the pinned chain with `--no-isolation` and `security`
  audits the lock rather than an environment containing only `pip-audit`; the PostgreSQL job is
  fixed (P6-10); `pytest` moves to `>=9.0.3,<10`; the unresolvable `freeweight` is removed from the
  `dev` extra; and `[tool.coverage.run] source` names the importable package with a
  `[tool.coverage.paths]` mapping. `requirements/README.md` records the blocker, the proof and the
  exact two-line CI conversion to make afterwards.
- **What the next run must do:** **Publish `weightsdb 0.2.0`, then `mirrorwall 0.2.0`**, per
  packaging standards §6 from step 4 (WDB3 and LCX23 hold that decision open). Then generate
  `ci.lock`, convert the CI installs, and verify the suite in a fresh non-root virtualenv installed
  from the lock non-editably. Until then LoadCoach's CI cannot be green and no claim that it is
  should be believed.

- **Resolved by the M5 run:** **Closed.** `mirrorwall 0.2.0` published first (tag `v0.2.0`, release run green 2026-08-30 08:00 UTC); `weightsdb 0.2.0`'s release run was waiting on an environment approval for most of the run and landed after the closeout commit (`pip index versions weightsdb` → 0.2.0). Then, as the prompt's 0.3 instructed: `requirements/ci.lock` generated on Python 3.13 with pip-tools 7.6.1 against PyPI (58 pins, every suite package from the index), `ci.yml` converted to `--require-hashes -r requirements/ci.lock` plus `pip install . --no-deps` in every installing job except the 3.14 early warning, both locks clean under `pip-audit --require-hashes`, and the whole gate — ruff, mypy, lint-imports, 796 tests, 25 contract tests — passed in a fresh **non-root** (uid 1000) Python 3.13 virtualenv installed from the lock non-editably. AC1 was then tested for real (M5-25). What remains is the `loadcoach` tag itself.

## P6-10 — LoadCoach's PostgreSQL job had never executed a query, for HR5's exact reason
- **Severity:** NOTE (fixed)
- **Unit:** P6 unit 7
- **Where:** `LoadCoach/.github/workflows/ci.yml` (`db-matrix`)
- **What happened:** The job set `WEIGHTSDB_REQUIRE_POSTGRES=1` and `DATABASE_URL`, while
  `weightsdb.testing.temporary_postgres` reads **`WEIGHTSDB_POSTGRES_URL`** — and under
  `REQUIRE_POSTGRES=1` the unused default is a hard failure rather than a skip. Fixed by copying
  WeightsDB's corrected job: the service container's `POSTGRES_USER`/`POSTGRES_PASSWORD`/
  `POSTGRES_DB` match the URL the code actually reads, the health check uses those credentials, and
  the step sets `WEIGHTSDB_POSTGRES_URL` explicitly.
- **What the next run must do:** It has still never run — the job cannot start until P6-9 is
  resolved. Check it on the first green pipeline; the two PostgreSQL-skipped tests in every local
  run are the ones it should pick up.

## P6-11 — Three defects the I4 demonstration found that no unit test had
- **Severity:** NOTE (all fixed)
- **Unit:** P6 unit 6
- **Where:** `LoadCoach/src/loadcoach/services/evidence.py`,
  `domain/evidence_policy.py` (`freeweight_remedy`), `domain/routing/scoring.py`
- **What happened:** This is the entry that justifies the roadmap's rule that no integration
  milestone is complete on the basis of a code review.
  1. **Two `evidence_sources` rows could share one URL.** The scheduler's first refresh fired while
     FreeWeight was still starting and recorded a placeholder row keyed by the URL; the first
     successful import added a second row keyed by the producer's own `source_id`. Every later
     lookup by URL — including the one every routing decision makes — raised
     `MultipleResultsFound`. The placeholder is now adopted, and `source_for_url` is deterministic
     where two rows do legitimately share one URL.
  2. **A `source_unreachable` badge survived the source coming back.** It is a statement about the
     source, never about the measurement, so a successful import now retires it and the row falls
     back to what its own age says.
  3. **The profile-mismatch remedy named only `--context-size`.** Following it produced the same
     mismatch again, because LoadCoach's `[runtime] keep_alive = "5m"` is also part of the subject
     hash and `freeweight run start` has no flag for it. `freeweight_remedy` now renders every
     field of the resolved profile — as a flag where FreeWeight has one, as `[runtime]`
     configuration where it does not.
  Each has a regression test naming where it came from.
- **What the next run must do:** Nothing. The general lesson is the one the roadmap already states,
  and it held: three real defects, none reachable from a passing unit suite.

## P6-12 — I4's `user.*` half is proven by the golden, not by a live goal
- **Severity:** NOTE
- **Unit:** P6 unit 6
- **Where:** `LoadCoach/tests/integration/test_evidence_routing_change.py`
- **What happened:** I4's verification includes "a `user.*` goal capability in the bundle changes
  nothing unless a task profile names it explicitly". The live bundle carries no `user.*` record,
  because no user goal exists on this machine and ADR-0032 §3 refuses to export one below its
  calibration gate — which needs a person to grade a holdout, and an unattended run cannot honestly
  produce those grades. The property is proven instead against SetSpec's own
  `benchmark.evidence_bundle` golden, which ships a real `user.noir_tech_voice` record with
  calibration (`kappa_w` 0.74, `n_holdout` 18), driven through the same importer, the same store and
  the same router: importing it changes no score, no flag and no breakdown entry; naming it in a
  profile makes it score with no re-import; and the rendered note states the goal slug, `kappa_w`
  and `n_holdout` in words.
- **What the next run must do:** If a live `user.*` record is wanted for I8's full-suite run, author
  a goal through `freeweight goals init`, grade its holdout, and run `freeweight goals calibrate` —
  a human-in-the-loop step by design, not an automation gap.

## P6-13 — Documentation consistency review (roadmap §8), run before declaring M4
- **Severity:** NOTE
- **Unit:** P6 unit 7
- **Where:** `docs/**`, and the nine repositories
- **What happened:** Every item on §8's checklist was checked, with evidence:

  | Check | Result |
  |---|---|
  | Component names | No spaced or mis-cased variant anywhere in `docs/` |
  | Public contracts | Each application's spec §11 lists them; LoadCoach's six are implemented or explicitly phased |
  | Model identity terms | `canonical_id`, `identity_confidence`, `machine_fingerprint`, `runtime_profile_hash`, `capability_id` used verbatim in docs and source; no camelCase or alternative spelling |
  | Configuration precedence | Defined once in configuration standards §1 and §1.1; **LoadCoach's spec §12 did not reference it — fixed** |
  | API conventions | All three applications declare `/api/v1` and the standard error envelope |
  | Database ownership | All three specs name their own file and tables exclusively |
  | No cross-application DB access | No application's `src/` names another's database file |
  | No package importing an application | All nine `.importlinter` files carry a `forbidden` contract naming `freeweight`, `loadcoach` and `ideapress`; LoadCoach's reports 4 contracts kept |
  | Each application independently runnable | All three specs carry "**Required at startup:** none" |
  | Optional links | Master architecture §documents them in both directions |
  | Tests planned before implementation | Every phase of all nine development plans carries a `**Tests**` list |
  | Acceptance criteria in every phase | Every phase carries one, except FreeWeight's "Phase 0 (upstream)" — a SetSpec prerequisite listed for convenience, which uses the heading `**Acceptance:**`. Cosmetic; not fixed |
  | Rationale for every decision | All 36 ADRs carry Status, Context, Decision and Consequences; no ADR is referenced-but-absent and none is present-but-unreferenced |

  **Drift found and fixed:** `capability_evidence.record_json` undocumented (P6-1); LoadCoach spec
  §12 naming neither its config path nor its precedence chain; api.md §7 not describing
  `GET /evidence`'s `summary` object, its six `status` values, or the fact that the schema version
  is decided before the transaction opens; the suite `docs/README.md` still saying "Implementation
  has not started"; roadmap §9 still describing nine empty repositories. All corrected, and the
  three changed LoadCoach documents mirrored downstream.
  **Drift found and deliberately not fixed:** the version-trajectory discrepancy (P6-14), and
  FreeWeight's `pytest` pin (P6-15).
- **What the next run must do:** Run it again before M5. It took about an hour and found five real
  things.

- **Resolved by the M5 run:** Run again before M5 (M5-21). Found and fixed: api.md §1's health-component list lacked `reliability` (spec §17 had it); spec §7.1 listed three endpoints that did not exist — `POST /models/discover`, `GET /models/{model_ref}` and `GET /task-profiles/{id}` (LC15) — now built and tested; spec §7.2 listed `loadcoach generate`, which the beta never shipped — built; roadmap §6's version trajectory (P6-14) corrected; roadmap §9 and the suite README's state line rewritten for post-M5. Every mechanical check passed: no mis-cased component name, identity terms verbatim, configuration precedence referenced, every application spec carries "Required at startup: none", 36 ADRs each referenced.

## P6-14 — Roadmap §6 puts BaseAiCore at 0.5 and ModelRack at 0.6 at M4; both are behind that
- **Severity:** DECISION (recorded, not acted on)
- **Unit:** P6 unit 7
- **Where:** `docs/roadmap/master-roadmap.md` §6
- **What happened:** The M4 column lists BaseAiCore **0.5** and ModelRack **0.6**. They are at
  `0.4.0` and `0.5.0`, and neither bump appears in M4's Content column in §1 (*LoadCoach P1–P6 ·
  WeightsDB 0.2 · MirrorWall 0.2 · SetSpec 0.4*) or in either package's development plan, which have
  no phase left to spend. **No version was invented.** §6 now records the discrepancy, states both
  readings, and recommends correcting the columns to `0.4` and `0.5` — nothing in M4's work touches
  either package, and M6 already carries the next bumps for both. The alternative reading (M4's
  Content column is missing two entries) requires a phase in each package's plan before the
  milestone can be declared, which is a bigger claim than the evidence supports.
- **What the next run must do:** Make the call before M5 is declared, and edit either §6's table or
  §1's Content column so the two agree.

- **Resolved by the M5 run:** Decided as this entry recommended: the table's columns are corrected to what the packages are — BaseAiCore 0.4 and ModelRack 0.5 through M5, and MirrorWall 0.2 at M5 (the same discrepancy class: no M5 content touches MirrorWall) — with the bumps left at M6, the first milestone whose content touches them. The discrepancy paragraph is replaced by a correction note. No version was invented.

## P6-15 — FreeWeight's `pytest>=9,<10` still admits the vulnerable versions
- **Severity:** NOTE (recorded, FreeWeight not modified)
- **Unit:** P6 unit 7
- **Where:** `FreeWeight/pyproject.toml`
- **What happened:** PYSEC-2026-1845 affects pytest through 9.0.2. Every other repository in the
  suite now pins `>=9.0.3,<10`; FreeWeight pins `>=9,<10`, which resolves to a fixed version today
  but permits a vulnerable one. Recorded as a documentation-consistency finding per this run's
  instructions; FreeWeight was read but not edited.
- **What the next run must do:** A one-line pin change in FreeWeight, with the same comment the
  other six carry, whenever FreeWeight is next touched (P12 is the natural place).

## P6-16 — What P6 deliberately did not build
- **Severity:** NOTE
- **Unit:** P6
- **Where:** N/A
- **What happened:** Nothing under the phase's Deferred list — production feedback — was touched.
  Also absent, each with its phase: `POST /jobs/{id}/feedback` and `reliability_stats` (P7), the
  circuit breaker's re-probe prompt record (P7), regression detection (P7), the dashboard and
  content-retention scrubbing (P8), `gpu_telemetry` as a health component (P8, spec §17),
  per-token rate limits and queue-depth caps (P9), and `GET /models/{ref}` /
  `GET /task-profiles/{id}` (LC15, still deferred with a stated reason).
- **What the next run must do:** This list is P7's, P8's and P9's, in that order.

## P6-17 — The I4 demonstration, as run
- **Severity:** NOTE
- **Unit:** P6 unit 6
- **Where:** N/A — a transcript, reproducible from the steps below
- **What happened:** Two processes, two interpreters, two virtualenvs, two database files.

  ```text
  pid 440594  /home/jpk/ai/suite/FreeWeight/.venv/bin/python3  freeweight serve  → 127.0.0.1:8765
              open: <scratch>/i4/fw/freeweight.sqlite3
  pid 440593  /home/jpk/ai/suite/LoadCoach/.venv/bin/python    loadcoach serve   → 127.0.0.1:8766
              open: <scratch>/i4/lc/loadcoach.sqlite3
  ```

  Neither venv can import the other's package (`find_spec("freeweight") is None` in LoadCoach's,
  `find_spec("loadcoach") is None` in FreeWeight's), and `lint-imports` reports "LoadCoach must not
  import other applications KEPT". `/proc/<pid>/fd` shows no shared file.

  The sequence, all of it real: FreeWeight discovered its fake model, ran `native.echo` (which
  produces no capability evidence), then `native.instruction_following` and
  `native.structured_output` (which do); LoadCoach imported by URL over HTTP; the first decision
  reported `evidence_profile_mismatch` naming both hashes and a remedy; FreeWeight was re-run under
  the remedy and, once `[runtime] keep_alive` was aligned (P6-11), published evidence under
  LoadCoach's own resolved hash `2b0158014a516620`; LoadCoach re-imported and the decision changed.

  ```text
  BEFORE (no evidence)                        AFTER (FreeWeight evidence)
    task_fit      0.150000                      task_fit      0.129773
    final_score   0.150000                      final_score   0.129773
    evidence      none                          evidence      freeweight | ok
    creative_writing       0.5000 conf 0.3000 prior      creative_writing       0.5000 conf 0.3000 prior
    instruction_following  0.5000 conf 0.3000 prior      instruction_following  0.1652 conf 0.5000 benchmark n=33 age=0d
    reasoning              0.5000 conf 0.3000 prior      reasoning              0.5000 conf 0.3000 prior
    reliability            0.5000 conf 0.3000 prior      reliability            0.5000 conf 0.3000 prior
  ```

  The score **fell**, and that is the demonstration: LoadCoach had been guessing 0.5 from a
  parameter-count band, and FreeWeight measured 0.165 over 33 samples. Stopping FreeWeight then
  produced `evidence degraded`, `loadcoach evidence refresh` exit 4, and a decision that kept the
  same score on the retained evidence with `stale_reason: source_unreachable` in the explanation.
- **The one substitution, stated plainly:** the before/after routing calls injected a telemetry
  snapshot through `route(snapshot=…)` — the same seam the web layer fills for every request —
  because an unrelated process (ComfyUI) held 11.7 GB of this workstation's 16 GB card, and the
  VRAM hard constraint correctly rejected the only candidate at 9.77 GB estimated against 3.82 GB
  free. `POST /route` against the live card was run too and is reported honestly: it returns
  `NO_ELIGIBLE_MODEL` with `insufficient_vram` and the numbers. Nothing about the evidence path was
  substituted: the bundle, the HTTP import, the store, the binding, the scoring and the explanation
  are all real.
- **What the next run must do:** Re-run it on a machine with a free GPU and the substitution
  disappears. The steps are: two configs pointing at separate databases and ports, `freeweight db
  upgrade` / `models refresh` / `run start --suite native.instruction_following`, then
  `POST /api/v1/evidence/import {"url": …}` against LoadCoach and `POST /api/v1/route` either side.


---

# M5 Handoff — P7–P9 run (LoadCoach P7–P9, M5 closeout)

Run started 2026-08-30, after the five runs above. Ground check at `95e297c` was green exactly as
the prompt predicted (646 passed, 2 skipped, working tree clean). **The M4 verification
(`m4-verification.prompt.md`) has not been run:** no findings file exists at the workspace root
and nothing in the transcript reports one, so nothing from it was folded in.

Twelve units, fifteen commits, `8d2ebc5` … `0963646`, version **1.0.0 prepared and not
published**. Final gate: **796 passed, 2 skipped**, coverage **91.5 %** against an 85 floor,
`pytest -m contract` **25 passed**, `pytest -m "not live and not performance" tests/integration`
**225 passed, 2 skipped**, `pytest -m performance` **12 passed**, `lint-imports` 4 contracts kept,
and the whole default suite passing inside `unshare -rn` — no network at all (M5-22). Every gate
ran under `set -o pipefail`.

| Unit | Status |
|---|---|
| 1 P7 schema and pure statistics | done |
| 2 P7 feedback | done |
| 3 P7 recomputation, the live factor, the breaker | done (+ the probe-lifecycle defect found and fixed, M5-3) |
| 4 P7 regression, health and the surface | done |
| 5 P8 dashboard (+ telemetry bar on every route, error state) | done |
| 6 P8 jobs and the readable explanation | done — **P8 AC1 is a human judgment; M5-16 says what to do** |
| 7 P8 live queue, models, system | done |
| 8 P8 settings, tokens, retention, the checklist | done |
| 9 P9 auth and limits | done |
| 10 P9 security pass | done |
| 11 P9 performance pass | done |
| 12 P9 documentation, doctor, closeout | done — **P9 AC4 (publish) is a human decision; not taken** |

**The publish state moved twice, and was re-checked each time.** `mirrorwall 0.2.0` was on PyPI
at run start; `weightsdb 0.2.0`'s release run waited on an environment approval through the
closeout commit and landed afterwards. With both published, the prompt's 0.3 path was taken:
`requirements/ci.lock` generated and audited, CI converted to install from it, the gate passed in
a fresh non-root virtualenv installed from the lock, and spec §20 AC1 tested against the real
machine (P6-9, M5-25). `loadcoach 1.0.0` is stamped, changelogged and locked; **the tag is the
remaining human step**, and it is the only thing between this repository and "published to PyPI".

**M5's exit condition** — *"Explainable, durable, secure routing service; published to PyPI"*:
explainable (every decision persisted and rendered as an explanation, P8 unit 6; production
evidence with its reasons, P7), durable (the queue's recovery, leases and retention; a thousand
mixed jobs on the simulator, M5-20), secure (Security Standards §14 held item by item, M5-19; scopes
checked twice, M5-17) — met, with the evidence in the entries below. **Published to PyPI: not yet**
— every dependency is, the lock is cut, CI installs from it; the `v1.0.0` tag is yours. The
verification prompt for Fable is `~/ai/suite/m5-verification.prompt.md`.

## What was done to the earlier runs' entries

`P5-9`, `LCX4` and `LCX5` carry a **Resolved by the M5 run** line above. The remaining entries the
prompt named as binding P8 and P9 (`P6-7`, `P6-6`, `LCX15`, `P5-11`, `P5-15`, `LC16`, `P6-13`,
`P6-9`) are resolved in place as those units land.

---

## M5-1 — Production evidence enters routing through the factor, never through capability scoring
- **Severity:** DECISION
- **Unit:** P7 unit 3
- **Where:** `LoadCoach/src/loadcoach/services/routing.py` (`route`), `domain/routing/scoring.py`
  (`AdjustmentFactors.reliability_detail`), `docs/apps/loadcoach/routing.md` §6 and §11
- **What happened:** Routing §5.1 lists production evidence as a *signal* ("used as soon as the
  minimum sample count is reached") and §11 lists three *uses*: the `reliability_factor`, the
  circuit breaker and regression detection. Scoring carries a `production` source in its
  precedence for §5.1's reading. Both readings were open. Chose §11's, and did not write production
  signals into `model_capabilities`, for three reasons: (1) that table has no `sample_count` column,
  so a production row could never clear `PRODUCTION_MINIMUM_SAMPLES` without a schema change the
  prompt forbids in `0006`; (2) the same success rate would then act twice on one candidate — as a
  capability's weight × score and again as a multiplier on `task_fit` — which is bounded adaptation
  twice over; (3) the factor is the place where production evidence is *labelled* as production.
  The explanation therefore shows benchmark evidence under `capabilities` with `source: benchmark`
  and production evidence under `factors.reliability_detail` with `source: production`, in one
  document, and `test_production_evidence_never_overwrites_benchmark_evidence_and_both_are_visible`
  asserts exactly that — including that no capability entry ever says `production`.
- **What the next run must do:** Nothing. If exploration routing (post-1.0) wants a production
  capability signal, add `sample_count` to `model_capabilities` in that migration and the
  precedence code is already waiting.
- **Resolved by the M5 closeout:** The decision stood, but routing §5.1 was never brought along
  (F7/M5C-7): its table still listed production evidence as a capability-scoring signal and
  promised routing "self-improving as production evidence accumulates" — the opposite of the
  bounded `[0.5, 1]` factor this entry chose. §5.1 now says what the code does ("guarded rather
  than self-improving"), and **ADR-0037** records the deferral of upward adaptation to post-1.0
  exploration routing with this entry's three reasons as its context.

## M5-2 — The factor may use the `7d` and `30d` windows, never `all`
- **Severity:** DECISION
- **Unit:** P7 unit 3
- **Where:** `domain/reliability.py` (`FACTOR_WINDOWS`), routing.md §6
- **What happened:** The first version searched `7d`, `30d`, `all`. Designing against the phase's
  named failure mode (a good model excluded after a bad day) showed `all` to be that failure mode
  in arithmetic: a lightly used model with fewer than twenty attempts a month would carry one bad
  hour in its factor for ever. `all` is still stored, still shown, and is the regression baseline;
  it never drives the factor. The cycle test's last step is a model going neutral thirty-one days
  after its bad ten minutes.
- **What the next run must do:** Nothing.

## M5-3 — The P5 worker marked the breaker's probe for every ranked candidate at routing time
- **Severity:** NOTE (fixed)
- **Unit:** P7 unit 3
- **Where:** `services/worker.py` (`_route`, `_attempts`), `domain/circuit_breaker.py`
- **What happened:** `_route` called `allow_probe` for the primary *and every fallback* the moment
  routing ranked them. A half-open model ranked as a fallback behind a healthy primary was marked
  "probe in flight", the primary answered, no attempt ever touched the fallback, and the breaker
  stayed half-open-and-busy — which `excludes` — until the process restarted. Found by reading the
  loop while writing the cycle test, not by a failing test: nothing watched the runtime mid-flight.
  Fixed in three parts: the probe is marked in `_attempts` at the instant execution starts on the
  model; a probe whose attempt is cancelled before the provider answers is handed back
  (`release_probe`); and a probe that has not reported within one cool-down is presumed lost
  (`probe_started_at`, released in `evaluate`). Two real-thread tests in
  `tests/integration/test_breaker_probe.py` watch the verdict while a slow fake generation is in
  flight.
- **What the next run must do:** Nothing. The mutation check that found the gap (never marking the
  probe at all) now fails those two tests.
- **Resolved by the M5 closeout:** The fix here was necessary and not sufficient (F2/M5C-2):
  marking the probe at execution still let *two* workers run it — both can pass routing's
  exclusion check before either marks, and `_attempts` ran the attempt whatever `allow_probe`
  answered. The execution-time gate, the probe-busy skip and the `PROBE_IN_FLIGHT` deferral are
  M5C-2's; this entry's lost-probe release and both its tests are untouched and still pass.

## M5-4 — "Driven by `reliability_stats`" means the same rows, the same rule, the verdict persisted
- **Severity:** DECISION
- **Unit:** P7 unit 3
- **Where:** `services/reliability.py` (`breaker_samples`, `record_breaker_verdicts`),
  `services/worker.py` (`refresh_breakers`)
- **What happened:** The breaker evaluates a ten-minute window; the statistics roll up seven days
  and more. A breaker literally fed from the rolled-up rows would have no samples to evaluate. So
  "driven by real statistics" was read as: the breaker's samples are the raw attempt rows the
  statistics are computed from, classified by `counts_as_success` — the one rule — and the verdict
  is written onto the model's `reliability_stats` rows (`circuit_*` columns) whenever it changes,
  so the page, the API and the CLI show it without the serving process. The `queue.py` copy of the
  sample source was deleted so there is one rule in one place.
- **What the next run must do:** Nothing.

## M5-5 — `reliability` is a health component, and spec §17's list now says so
- **Severity:** DECISION
- **Unit:** P7 unit 4
- **Where:** `services/health.py`, `docs/apps/loadcoach/spec.md` §17
- **What happened:** P7 AC3 says "regression warnings appear in health"; spec §17's component
  list did not name one. Folding regressions into `queue`'s detail (which already carries breaker
  state) would have hidden a routing-quality signal inside a scheduling one. Added `reliability`:
  `ok` with the number of pairs tracked, `degraded` naming each regressed pair with the verdict's
  own line. It is not a required component, so it can never make the application `unavailable`.
  Spec §17 lists it now, in both copies.
- **What the next run must do:** P8's `gpu_telemetry` component is still the one §17 names that
  does not exist.

## M5-6 — Columns beyond data model §2: `feedback.validation_detail_json` and the five `*_count`s
- **Severity:** DECISION
- **Unit:** P7 unit 1
- **Where:** migration `0006`, `infrastructure/db/models.py`, data-model.md §2
- **What happened:** api.md §6's body carries `validation.detail`; the column list did not. A
  feedback record that kept the caller's verdict and dropped its reason would lose the one part a
  person can act on — kept as `validation_detail_json`. And ADR-0016 rule 6 requires the sample
  count beside every statistic; the listed columns had rates and means with no counts, so an
  `acceptance_rate` over two verdicts would read exactly like one over two hundred. Added
  `latency_count`, `output_token_count`, `tokens_per_second_count`, `feedback_count` and
  `quality_count`. Data model §2 documents both, with the reasons, in both copies.
- **What the next run must do:** Nothing.

## M5-7 — The synchronous path recomputed at the request's start instant, and saw nothing
- **Severity:** NOTE (fixed)
- **Unit:** P7 unit 3
- **Where:** `services/execution.py` (`_refresh_reliability`)
- **What happened:** `execute()` reads `now` once, at the start, for the job's own timestamps. The
  first version of the recomputation reused it — and the attempt it was folding in had completed
  *after* it, so the window rule (a sample from the future never counts) correctly excluded the
  one row the recomputation existed for: the rows were written with `attempts = 0`. Found by the
  worker-path test, whose synchronous half stayed at three attempts. The recomputation now reads
  the clock afresh. The worker path was never affected; it reads its clock at the call.
- **What the next run must do:** Nothing. It is the ADR-0016 lesson in another costume: a
  boundary rule that is right will make a wrong instant visible, and did.

## M5-8 — Feedback semantics the documents leave open
- **Severity:** DECISION
- **Unit:** P7 unit 2
- **Where:** `services/feedback.py`, `web/routes/jobs.py`, `domain/reliability.py`
  (`acceptance_credit`), api.md §6
- **What happened:** Five choices, each recorded in api.md §6 or the constant's docstring.
  (1) Feedback is accepted for *any* existing job, terminal or not; a verdict on a job that has
  not run is stored and attributed once it has. (2) `source` precedence is token name, then
  `X-Client-Name`, then the body, then `anonymous` — the body never wins over a token.
  (3) `201` on a source's first record for a job, `200` on an update. (4) An accepted-but-edited
  output earns half an acceptance (`EDITED_ACCEPTANCE_CREDIT`), and a caller's own
  `validation.passed = false` is a rejection whatever `accepted` says. (5) Feedback moves the factor
  by at most half the distance to the floor (`FEEDBACK_WEIGHT`), and only once five verdicts exist
  in the window.
- **What the next run must do:** IdeaPress's integration phase should send `source` only as a
  courtesy; on a tokened deployment it will be ignored, as the document says.

## M5-9 — Regression detection: what fires it, and against what
- **Severity:** DECISION
- **Unit:** P7 unit 1
- **Where:** `domain/reliability.py` (`detect_regression`), routing.md §11
- **What happened:** Routing §11 names "a significant drop against a model's own baseline" and no
  numbers. The metric is validated success over counted attempts — answered *and* correct — so a
  model that starts erroring and one that starts answering wrongly both move it. The baseline is
  `all` minus `7d` (counts subtract exactly, the recent window being a subset), so the recent
  samples do not drag down the history they are compared with. It fires only when the absolute
  drop is at least 15 points **and** the two-proportion z-score is at least 2.0, with at least 20
  counted attempts on each side. The two conditions are each the other's failure mode: significance
  alone pages an operator for a two-point drift over five thousand attempts; an absolute floor
  alone fires on 18-of-20 becoming 15-of-20. The unit tests hold a hand-computed z (3.8435) and both
  boundary cases; a seeded stationary Bernoulli series through the real window arithmetic does not
  fire and the same seed with a real degradation does.
- **What the next run must do:** Nothing. Latency regression is deliberately not a trigger; if it
  becomes one, it is a second verdict, not a change to this one.

## M5-10 — Mutation checks run for P7, and what the third one found
- **Severity:** NOTE
- **Unit:** P7 unit 3
- **Where:** `domain/circuit_breaker.py`, `domain/reliability.py`, `services/worker.py`
- **What happened:** Three mutations, each applied to a copy-backed file and restored from the
  copy (P5-16). (A) A successful probe closes the breaker but leaves the failures counted: the
  cycle test failed at its probe step and the breaker unit test failed — the breaker re-opened at
  once, as P5-9 predicted. (B) Regression fires on the absolute drop alone: the noise-floor test
  failed. (C) The worker never marks a probe at execution: **every test passed**, so the mechanism
  had no test. `tests/integration/test_breaker_probe.py` was written for it and now fails under
  that mutation.
- **What the next run must do:** Keep the bar. The three take under a minute.

## M5-11 — Mutation checks run for P8's live queue stream
- **Severity:** NOTE
- **Unit:** P8 unit 7
- **Where:** `services/queue_stream.py`, `tests/integration/test_queue_stream.py`
- **What happened:** LCX15's bar, applied to the new stream. Five mutations, each on a copy-backed
  file and restored from the copy: (1) `replay` returns nothing — the first-frame and reconnect
  tests fail; (2) the publisher polls once and never again — the control-change test fails;
  (3) the sequence never advances — the strictly-increasing test fails; (4) `replay` ignores
  `after_sequence` — the reconnect test fails (a duplicate); (5) the fragment is rendered from the
  previous report — the control-change test fails (`paused` missing from the HTML). The
  frame-pulling helper drives the route's body iterator directly with a five-second deadline,
  because a test client cannot interrupt an open-ended sync generator in a threadpool — the
  first draft of a telemetry-stream test hung the whole suite for exactly that reason.
- **What the next run must do:** Keep the bar; the five take about twenty seconds.

## M5-12 — UI actions on a tokened bind: the bearer token, carried by a cookie
- **Severity:** DECISION (revised in P9 unit 9; the P8 text said the CLI or the API was the only way)
- **Unit:** P8 unit 7, P9 unit 9
- **Where:** `web/auth.py` (`TOKEN_COOKIE_NAME`), `web/routes/access.py`, `web/templates/error.html`
- **What happened:** The queue controls and the Settings form are HTML forms behind MirrorWall's
  CSRF middleware and the same scopes as the API. A browser cannot add ``Authorization`` to a
  page navigation, and ADR-0014 rejects a login subsystem (accounts, passwords, resets) while
  saying the bearer token serves the UI too. So on a tokened bind the same token is carried by an
  ``HttpOnly``, ``Secure``, ``SameSite=Strict`` cookie, set once by pasting the token into the 401
  page's form (``POST /token-cookie``, CSRF-checked) and cleared by ``POST /token-cookie/clear``.
  No session table, no password: the cookie *is* the token, revoking the token revokes it, and the
  rate limiter keys the cookie and the header to the same bucket. On the loopback default with no
  tokens everything stays open. ADR-0014's "stored in ``localStorage``" is what a script-driven UI
  would do; a server-rendered one needs the cookie, and the ADR's decision — bearer tokens, no
  accounts — is unchanged.
- **What the next run must do:** Nothing. If a genuine multi-user deployment arrives, ADR-0014's
  own revisit clause (OIDC for humans) is the path, not a password.
- **Resolved by the M5 closeout:** One omission closed (F5/M5C-5): nothing here said the flow
  *cannot work* on a plain-HTTP non-loopback bind — the `Secure`/`__Host-` cookies are refused
  by the browser there, `POST /token-cookie` dies on CSRF and pages stay 401. Now documented in
  api.md §11, `docs/security.md` and on the 401 page itself, with ADR-0014 §7's startup warning
  emitted on a non-loopback bind with no `trusted_proxies`. The cookie flags are unchanged.

## M5-13 — The runtime-changeable settings are a registry of seven keys; security keys are named
- **Severity:** DECISION
- **Unit:** P8 unit 8
- **Where:** `services/settings.py` (`RUNTIME_SETTINGS`, `CONFIG_ONLY_SECURITY_KEYS`),
  `web/routes/settings.py`, `services/worker.py` (`apply_runtime_settings`), api.md §9
- **What happened:** api.md §9 says "runtime-changeable settings only" and spec §12 does not say
  which those are. Chose the keys a running process can honour without a restart and without
  re-reading configuration: the two P5 control flags under their existing keys, the four routing
  knobs `RoutingPolicy` carries as plain numbers (applied by rebuilding the policy at the flags
  cadence, and read by `POST /route` per request), and `storage.content_retention_hours` (read by
  the sweep). Not included: anything that shapes a thread pool, a connection, a bind, a provider
  or a credential — those are config-only, and the security-relevant subset is enumerated so a
  `PUT` naming one is `FORBIDDEN` naming it, as §9 requires, rather than a generic validation
  error. `storage.retain_content` is on that list on purpose: what is retained is a privacy
  decision, and spec §14 says full content is kept only when *explicitly* enabled.
- **What the next run must do:** Adding a key is one `RuntimeSetting` entry plus whatever reads
  it; the page, the API and the CLI need no change.

## M5-14 — Content retention: what is scrubbed, when, and what stays
- **Severity:** DECISION
- **Unit:** P8 unit 8
- **Where:** `services/retention.py`, `config.py` (`StorageSettings`), spec §12
- **What happened:** Spec §14 and data model §3 say text is stored as hashes by default and full
  content only when enabled, while P5-15 records that every job stores its transcript and nothing
  scrubs it. Reconciled with a sweep rather than a write-time policy: a queued job must keep its
  transcript until it has run, and a caller polling a finished job expects its output for a
  while, so the default keeps text for 24 hours after completion and then removes it — the
  hashes, token counts, timings, model, decision and events stay, so the job is still explicable
  and the reliability statistics are unaffected. The persisted `job.completed` event's `output`
  goes too, or a replay would resurrect the text. Scrubbing is idempotent (a marker in
  `request_json`) and batched. The sweep runs every minute on the scheduler.
- **What the next run must do:** Nothing. If a deployment wants text kept, `retain_content =
  true` in `config.toml` is the explicit enabling spec §14 asks for.
- **Resolved by the M5 closeout:** Two loose ends closed (F9/M5C-9): the scrub marker this
  entry introduced was never rendered — `/jobs/{id}` and the job document now say "content
  removed by retention" with the instant — and spec §14 still said "hashes by default" from
  before this reconciliation; it now states the 24-hour default this entry decided, plus the
  `db backup` caveat. The disk-level half (SQLite `secure_delete`) is recorded as a WeightsDB
  0.2.1 item, per the finding — LoadCoach unchanged.

## M5-15 — A module-scoped fixture booted against the developer's real data directory
- **Severity:** NOTE (fixed)
- **Unit:** P8 unit 8
- **Where:** `tests/accessibility/test_ui_checklist.py`, `tests/conftest.py`
- **What happened:** The checklist needs one populated server for a dozen tests, so its
  ``client`` fixture is module-scoped. Pytest builds higher-scoped fixtures first, so it ran
  before the function-scoped autouse ``_isolated_xdg_env`` had pointed ``XDG_DATA_HOME`` at a
  temporary tree — and ``bootstrap()`` created ``~/.local/share/loadcoach/loadcoach.sqlite3``,
  wrote a hostile test model and one job into it, and the second run failed on the unique
  constraint. Testing standards §9 forbids exactly this. Verified the directory had been created
  by that run (its timestamp matched, and it held only the test's rows) and removed it; the
  fixture now isolates its own XDG tree with a ``MonkeyPatch`` before booting, and the gate
  asserts the real directory is absent afterwards. The general rule for the next run: a fixture
  scoped wider than ``function`` cannot rely on the autouse isolation and must do its own.
- **What the next run must do:** Nothing; if another module-scoped server fixture is written,
  copy this one's isolation block.

## M5-16 — P8 acceptance criterion 1: what a person should do to judge it
- **Severity:** NOTE (a judgment the run cannot make)
- **Unit:** P8 unit 6
- **Where:** `/jobs/{id}` and `/routing/{decision_id}`
- **What happened:** "A user can answer 'why did it pick that model?' entirely from the UI in
  under a minute" is a design judgment; the run built the page that makes it plausible and
  cannot claim it passes. To judge it: start the server (`loadcoach serve`), submit one job
  (`loadcoach job submit --task general.chat --prompt 'hello'`), open **`/jobs/<job id>`**, start
  a timer, and answer these three questions from the page alone, pointing at the element that
  answers each: (1) *Which model, and by how much?* — the bold headline under "Why this model"
  names the model, the final score and the margin over the runner-up, with the
  `task fit × reliability × availability × residency × cost` arithmetic beneath it. (2) *What
  decided it?* — the sentence after the arithmetic names either the factor that separated the
  two or the capability that moved the score most, with both models' numbers. (3) *What is the
  decision missing, and what would fix it?* — the "What could not be scored" table lists each
  absent capability with its weight, its reason and, for a profile mismatch, the exact
  FreeWeight command. If all three are answered in under a minute without opening "The complete
  stored explanation", the criterion holds; if the reader had to open the JSON viewer, it does
  not, and the thing they needed from it is what the narrative lacks.
- **What the next run must do:** The verification prompt asks Fable to do exactly this and to
  report the time.

## M5-17 — The scope is checked in the service layer through a principal the route hands down
- **Severity:** DECISION
- **Unit:** P9 unit 9
- **Where:** `domain/authorization.py`, `web/auth.py`, every mutating service, `tests/security/test_scopes.py`
- **What happened:** P9's named failure mode is a scope checked at the route but not in the
  service. Designed against rather than tested for: the rule (`Principal`, `authorize`,
  `admin ⊃ write ⊃ read`) is one pure function; the route resolves the principal and checks
  (outer); `enqueue`, `cancel_job`, `record_feedback`, `set_queue_flag`/`QueueFlags.update`,
  `write_runtime_settings`, `import_bundle`, `route` and `execute` take `principal` and check
  again (inner). `None` — no principal — is an internal call with no request behind it (a
  scheduler sweep, the arithmetic's own tests) and is allowed; the CLI passes `LOCAL` (admin,
  because the OS user boundary is the boundary there). The web layer is held to never passing
  `None` by a contract test over the route table: every API route except `/version` declares
  the `authenticate` dependency. The direct-call test calls each of the eight services with a
  read-scoped principal and asserts refusal before anything is written.
- **What the next run must do:** A new mutating service takes `principal` and calls `authorize`
  first; a new route declares `CurrentPrincipal` and passes it on. The two tests will say so if
  either is forgotten.
- **Resolved by the M5 closeout:** One writer had escaped the rule (F8/M5C-8):
  `discover_models` wrote without a `principal`, its scope checked at `POST /models/discover`'s
  route only. It now takes `principal` and calls `authorize(principal, "admin")` first; the
  route and the CLI pass theirs, internal callers (startup, the scheduled refresh) pass
  `None` as this entry defines, and the direct-call test's list is nine.

## M5-18 — Rate limit and queue cap: the numbers, and what happens at the boundary
- **Severity:** DECISION
- **Unit:** P9 unit 9
- **Where:** `web/rate_limit.py`, `config.py` (`ServerSettings`, `QueueSettings`), api.md §11
- **What happened:** Spec §14 names per-token rate limits and queue-depth caps and no numbers.
  Chosen: a token bucket per credential digest — 100 at once, 600 a minute sustained — answering
  `429 RATE_LIMITED` with `Retry-After` at the boundary, never a dropped connection; per token,
  not per connection, so ten connections share one budget and two tokens have two; `/version`
  exempt (ADR-0026 §5) and pages unlimited (a person is not the failure mode). Failed
  authentications are braked per address at 20 a minute (ADR-0014 §6), logged with the address
  and never the token. The queue cap is 200 active jobs per source, refused with `QUEUE_FULL`
  naming the source, its count and the cap; another source is unaffected. The defaults are
  generous on purpose — "a rate limit that starves a legitimate caller is worse than none" —
  and every number is a `[server]`/`[queue]` key with a description.
- **What the next run must do:** Nothing. Middleware order is documented in `create_app`: Host
  validation runs before the limiter, so a rebinding attempt is 421 before it spends anyone's
  budget, and both run before authentication.
- **Resolved by the M5 closeout:** The failed-auth brake's per-address keying was correct on a
  direct bind and a lockout behind the mandated reverse proxy (F4/M5C-4): with every caller
  sharing the proxy's address, twenty bad bearers a minute from anyone answered 429 to correct
  tokens too. `[server] trusted_proxies` (CIDRs) now restores per-client addresses from
  `X-Forwarded-For`'s last untrusted hop; from any unlisted peer the header stays ignored. The
  keying decision — per address, never per `(address, credential)` — is recorded in M5C-4.

## M5-19 — Security Standards §14, item by item: held, held elsewhere, or shown not to apply
- **Severity:** NOTE
- **Unit:** P9 unit 10
- **Where:** `tests/security/test_checklist.py`, `test_scopes.py`, `test_rate_limit.py`,
  `test_queue_cap.py`; `web/limits.py`
- **What happened:** Every bullet of §14 is accounted for. Held in the security suite: path
  traversal (the one path-shaped input, a task profile's `json_schema_ref`, cannot resolve
  outside the schemas directory, at startup and at load; and a route-table test asserts no
  endpoint takes a path); oversize body (`413` before buffering, by declared length or while a
  chunked body arrives — the first draft raised from `receive()`, which Starlette reports as a
  400 "error parsing the body", so the limiter now answers itself); missing, malformed, revoked
  and wrong-scope tokens; the hash on the row and `hmac.compare_digest` observed on the call;
  no presented token in any log record; hostile model output (`{{ }}`, `<script>`, traversal
  text, SQL text) stored verbatim and rendered inert; cross-origin JSON refused with
  `CSRF_FAILED` (new `SameOriginMiddleware`, the server-side statement of ADR-0026 §2's
  reasoning); non-loopback without `allowed_hosts` refused at startup. Held by a named P6 test
  the map asserts exists: the five evidence-fetch refusals and the two credential rules. Held in
  `test_scopes.py`: Host before auth on both binds; non-loopback without a token; `/version`
  open while `/health` is not. **Not applicable, asserted on the surface:** archive bombs —
  LoadCoach imports JSON envelopes and no module imports `zipfile`/`tarfile`; sandbox
  unavailable ⇒ benchmark skipped — FreeWeight's item, whose counterpart here is spec §14's "never
  executes a tool call": a provider's tool call is returned to the caller as the streamed
  fragments ModelRack produced, with `subprocess` patched to fail if anything tried.
- **What the next run must do:** Nothing. One observation for P4's owner: tool calls come back
  as fragments (`call_index`, `name`, `arguments_fragment`), not assembled calls; api.md §4
  does not say which, and IdeaPress will want to know.

## M5-20 — Every spec §15 budget, measured on this workstation
- **Severity:** NOTE
- **Unit:** P9 unit 11
- **Where:** `tests/performance/`, `tests/simulation/test_scale.py`
- **What happened:** The six budgets P4 and P5 already measured were re-run and the three that
  were not — routing warm and cold, and per-chunk streaming latency — were written and run.
  Medians, on this machine, against spec §15's targets: enqueue 1.8 ms (≤ 15); dispatch with an
  idle worker 17 ms (≤ 100); routing over twenty candidates with bound evidence on three
  capabilities each, warm 16 ms (≤ 20) and cold 19 ms (≤ 150); execution overhead 3 ms (≤ 15);
  added latency per streamed chunk 0.06 ms (≤ 5); cancellation queued 0.9 ms (≤ 50) and
  executing 53 ms (≤ 1 s); idle poll CPU 0.32 % of a core (≤ 0.5 %); recovery of a thousand
  in-flight jobs within 2 s. The warm routing figure is the one with the least margin: 16 ms
  against 20, and 40 ms on the worst run of one series, under the 100 ms ceiling. At scale: a
  thousand mixed-class jobs on four simulated workers complete with median waits interactive
  2 s, normal 133 s, background 339 s, batch 482 s and a worst background wait of 403 s
  against the 34-minute bound, in 35 s of real time.
- **What the next run must do:** These are one machine's numbers. The verification prompt asks
  Fable to measure, not to read the test; the warm routing budget is the one to watch.

## M5-21 — Documentation consistency review (roadmap §8), run before declaring M5
- **Severity:** NOTE
- **Unit:** P9 unit 12
- **Where:** `docs/**`, and the nine repositories
- **What happened:** Every item on §8's checklist was checked again. Mechanical checks (component
  names, identity terms, configuration precedence, "Required at startup: none", ADR references):
  all pass. **Drift found and fixed:** api.md §1's health-component list lacked `reliability`;
  spec §7.1 named three endpoints that did not exist — `POST /models/discover`,
  `GET /models/{model_ref}` (LC15, deferred since P2 with a reason) and `GET /task-profiles/{id}`
  — all three are now built and tested, and LC15 is closed rather than deferred again; spec §7.2
  named `loadcoach generate`, which the beta listed and never shipped — built (M5-24); roadmap §6
  (P6-14) and §9 corrected and rewritten; the suite README's state line updated. **Drift found and
  left:** P6-15 (FreeWeight's `pytest` pin) stands as recorded — FreeWeight was not touched by
  this run either. Every LoadCoach document edited (`api.md`, `data-model.md`, `routing.md`,
  `spec.md`) is mirrored into `LoadCoach/docs/apps/loadcoach/` byte-identically.
- **What the next run must do:** Run it again before M6. The endpoint and command gaps were
  found by reading spec §7 against the route table and the Typer app — cheap, and worth
  repeating: a public contract list that outruns the code is the drift most likely to embarrass a
  release.

## M5-22 — AC11: the suite run with the network disabled, and how
- **Severity:** NOTE
- **Unit:** P9 unit 12
- **Where:** N/A — a procedure
- **What happened:** `unshare -rn .venv/bin/python -m pytest -q -m "not live and not performance"`
  — a user namespace with a fresh, empty network namespace (no interfaces up, not even loopback)
  — passed 793 tests with 2 skipped (the PostgreSQL pair), identically to the run with the network
  present. No GPU is needed (the telemetry fixture pins a machine, P6-6), no Ollama (the fake
  provider), no FreeWeight (the goldens ship in `setspec`), and now demonstrably no network.
- **What the next run must do:** Nothing. `unshare -rn` is the one-line way to prove it again.

## M5-23 — Three documented endpoints were not built, and now are
- **Severity:** NOTE (fixed)
- **Unit:** P9 unit 12
- **Where:** `web/routes/models.py`, `web/routes/task_profiles.py`,
  `tests/e2e/test_model_and_profile_detail.py`
- **What happened:** Spec §7.1 and api.md §2 list `POST /models/discover`, `GET /models/{model_ref}`
  and `GET /task-profiles/{id}`. The detail routes were LC15, deferred at P2, P3 and P6 with a
  stated reason each time; `discover` had never been mentioned. A 1.0 whose spec lists endpoints
  that 404 is not complete against its own contract, so all three were built on the services that
  already existed: `discover` (admin) runs `discover_models` and returns its counts;
  `GET /models/{model_ref}` takes the ULID or an unambiguous prefix (never the canonical ID —
  ADR-0024 — and a canonical ID in the path is 404) and returns the overview, descriptor, every
  evidence record, reliability per task profile and the breaker state; `GET /task-profiles/{id}`
  returns the stored definition. The OpenAPI snapshot was regenerated.
- **What the next run must do:** Nothing.

## M5-24 — `loadcoach generate` was in spec §7.2 and not in the CLI
- **Severity:** NOTE (fixed)
- **Unit:** P9 unit 12
- **Where:** `cli/commands/generate.py`
- **What happened:** The beta's CLI shipped `route explain` and `job submit|wait` but not the
  synchronous `generate --task … [--prompt|--prompt-file] [--stream]` spec §7.2 lists. Built as a
  thin command over the same `execute()` the `POST /generate` route calls, as the local principal;
  `--stream` prints token deltas as they arrive. Exit codes follow the CLI's existing convention.
- **What the next run must do:** Nothing.

## M5-25 — `ci.lock` cut, CI converted, the gate passed from the lock, and AC1 tested for real
- **Severity:** NOTE
- **Unit:** P9 unit 12 (after the closeout commit, on the news that `weightsdb 0.2.0` had landed)
- **Where:** `requirements/ci.lock`, `requirements/README.md`, `.github/workflows/ci.yml`
- **What happened:** Exactly the prompt's 0.3 procedure. `pip-compile --strip-extras --extra dev
  --extra postgres --generate-hashes` on Python 3.13 with pip-tools 7.6.1 resolved 58 pins against
  PyPI, all six suite packages at their published versions; the `postgres` extra is in the same
  lock so the PostgreSQL job installs from it too. `pip-audit --require-hashes` is clean for both
  locks. In a fresh non-root Python 3.13 virtualenv, `pip install --require-hashes -r
  requirements/ci.lock && pip install . --no-deps` then the whole gate: format, lint, mypy (164
  files), lint-imports (4 kept), 796 passed / 2 skipped, 25 contract. **AC1** (`pip install
  loadcoach && loadcoach serve` with only Ollama running): in another clean virtualenv,
  `pip install .` resolved every dependency from the index (no editable sibling in sight —
  `weightsdb` imported from `site-packages`); `loadcoach serve` started with zero configuration
  against this machine's real Ollama, discovered twelve models, and answered `/version`,
  `/health` (`ok`: database, provider, queue, reliability ok; evidence not_configured) and the
  dashboard. The one honest caveat is the same one P6-17 recorded: `POST /generate` returned
  `NO_ELIGIBLE_MODEL` naming all twelve candidates as `insufficient_vram` against 4.1 GB free on
  the 16 GB card another process holds — the correct answer to the question the machine was
  asked, and AC2 on this workstation is therefore proven by the fake-provider suite rather than
  the live card, exactly as before. The install substituted `XDG_*` scratch directories for the
  real ones so the test left no database behind.
- **What the next run must do:** Tag `v1.0.0` (Packaging Standards §6 step 6); `release.yml`
  builds, tests the wheel and publishes through Trusted Publishing. Then `pip install
  loadcoach==1.0.0` in a clean virtualenv is the last line of AC1. On a machine with a free GPU,
  AC2 against the live card is a one-line `curl`.
- **Resolved by the M5 closeout:** This entry's *install* claim stands (the lock-based installs
  succeeded on the runner at `53bd49a`); its *"the whole gate passed"* claim does not — the gate
  was run as `python -m pytest` locally while CI, README and CONTRIBUTING run the bare `pytest`
  console script, which could not collect the suite at all (F1/M5C-1). Also corrected for the
  record: the entry says "Python 3.13 virtualenv"; the repo's own `.venv` is **3.14.4**
  (`python3.13` exists at `/usr/bin` and Fable re-did the lock install in a real 3.13 venv, which
  passed). The closeout runs name their interpreter explicitly every time (F13).

---

# M5 Closeout — verification findings (LoadCoach 1.0.0)

Run started 2026-08-30, acting on the Fable 5 verification of the same date (fourteen findings,
verdict **not ready**; the findings are reproduced in `~/ai/suite/loadcoach-m5-closeout.prompt.md`).
Ground state matched the prompt exactly: `53bd49a`, clean tree, `__version__ = "1.0.0"`, the
`.venv` interpreter **Python 3.14.4** (named per F13), 796 passed / 2 skipped under
`python -m pytest`, 24 collection errors under the bare `pytest`, and every run in the
repository's Actions history `failure`.

| Finding | Status | One line |
|---|---|---|
| F1 (M5C-1) | fixed | `pythonpath = ["."]`; bare `pytest` = `python -m pytest`; Docker 3.12 line green |
| F2 (M5C-2) | fixed | execution-time probe gate; probe-busy skip; `PROBE_IN_FLIGHT` deferral; two-worker test |
| F3 (M5C-3) | fixed | sync path passes breaker+residency, probes like the worker; CLI flags `breaker_state_unavailable` |
| F4 (M5C-4) | fixed | `[server] trusted_proxies`; last-untrusted-hop keying; per-address decision recorded |
| F5 (M5C-5) | fixed | documented (api.md §11, security.md, the 401 page) + ADR-0014 §7 startup warning; flags unchanged |
| F6 (M5C-6) | fixed | plain paragraph of real anchors; MirrorWall 0.2.1 `kv_list` link item recorded |
| F7 (M5C-7) | fixed | §5.1 rewritten (guarded, not self-improving); ADR-0037 written |
| F8 (M5C-8) | fixed | `discover_models` takes `principal`, checks `admin`; scope list is nine |
| F9 (M5C-9) | fixed | scrub marker rendered; spec §14 states M5-14's default; WeightsDB 0.2.1 item recorded |
| F10 (M5C-10) | fixed | `gpu_telemetry` removed from §17 and api.md §1; docs↔`/health` agreement test |
| F11 (M5C-11) | fixed | wrap stopgap on `/system` and `/jobs/{id}`; MirrorWall 0.2.1 CSS item recorded |
| F12 (M5C-12) | fixed | 2 ms poll on token streams; real-socket added-latency p95 1.29 ms (was 10.34) |
| F13 (M5C-13) | adopted | interpreter and invocation named in every gate report |
| — (M5C-14) | fixed | found under F1's Docker line: checklist fixture pinned; candidate-table row-counts |
| — (M5C-15) | fixed | found by the first real runner run: migration 0006 was a PostgreSQL syntax error (`window` unquoted) |

**The runner is green**: run `33334510805` on `eeef0f4` (2026-08-30) — every job `success`,
including `tests (3.12)`, `tests (3.13)`, `tests (PostgreSQL)`, `coverage` and the
`continue-on-error` `tests-314-early-warning`. It is the first green run in the repository's
history. `TAG_APPROVED` was `no` at the closeout, so the `v1.0.0` tag remains the human step.

## M5C-1 — F1: the suite only collected under `python -m pytest`; the bare console script is what CI runs
- **Severity:** BLOCKER (fixed)
- **Finding:** F1 (Fable verification, 2026-08-30)
- **Where:** `pyproject.toml` `[tool.pytest.ini_options]`
- **What happened:** Reproduced first: `.venv/bin/pytest -q -m contract` at `53bd49a` — 24 errors
  during collection, `ModuleNotFoundError: No module named 'tests'`, exactly as the finding says,
  while `.venv/bin/python -m pytest` passed 796/2. Twenty-four test modules import shared fixtures
  as `tests.…`; under pytest's default `prepend` import mode only `python -m pytest` puts the
  repository root on `sys.path`. Fixed with `pythonpath = ["."]` in `[tool.pytest.ini_options]`,
  with FreeWeight's explanatory comment copied over (the module count corrected to twenty-four).
  After the fix, on Python 3.14.4: `.venv/bin/pytest -q -m contract` 25 passed;
  `.venv/bin/pytest -q -m "not live and not performance"` 796 passed / 2 skipped — identical to
  `python -m pytest`. Running F1's Docker 3.12 line (the runner reproduction) then surfaced a
  further, previously invisible defect — see M5C-14; the Docker line is green after that fix.
- **What the next run must do:** Nothing for the config. The lesson is F13's: name the
  interpreter *and the invocation* every time a gate is reported. "Green locally" meant
  "green under the one invocation CI does not use".

## M5C-2 — F2: the half-open breaker admitted more than one probe
- **Severity:** MAJOR (fixed)
- **Finding:** F2 (Fable verification, 2026-08-30)
- **Where:** `services/worker.py` (`_attempts`, `_requeue_for_probe`, `_defer`,
  `reevaluate_waiting`), `domain/circuit_breaker.py` (`probe_busy`), `domain/admission.py`
  (`classify_rejections`, `AdmissionVerdict.probe_candidates`),
  `tests/integration/test_breaker_probe.py`
- **What happened:** Reproduced with Fable's arrangement as a new two-worker test
  (`max_concurrent_jobs = 2`, one half-open model, two jobs enqueued together, a 700 ms
  generation): before the fix, **peak in-flight 2** — both jobs executing on the half-open
  model concurrently, exactly as the finding says. `_attempts` called `allow_probe` and ran the
  attempt whatever it answered; exclusion lived only at routing time, which both workers passed
  before either marked the probe. The fix gates at execution: `allow_probe` is asked once per
  candidate (a retry on a model whose probe this worker holds is the same probe job), and a
  refusal while `probe_busy` — half-open, another probe out — skips the candidate exactly as a
  `recently_failing` rejection would have at routing time, falling to the next candidate; with
  none left, the job is requeued (`admitted|validating|retrying -> queued`, all legal edges).
  The immediate re-route then lands in a new transient branch of `classify_rejections`: a
  `recently_failing` rejection whose detail says `half_open` + `probe_in_flight` defers the job
  (`PROBE_IN_FLIGHT` → `waiting_resources`) instead of failing it, and `reevaluate_waiting`
  wakes it when the breaker stops excluding the model — the probe reported, or its cool-down
  elapsed and this job becomes the next probe. An *open* breaker's rejection still fails
  admission as before: its cool-down is a verdict about the model, not about this moment.
  The new test asserts both jobs complete, peak concurrent `executing` ≤ 1, and — deterministic
  record — no two attempt rows overlap in time. Watched failing against the pre-fix code
  (`assert 2 <= 1`), which is the restore-the-old-behaviour mutation check. M5-3's lost-probe
  release and both its tests are untouched and still pass.
- **What the next run must do:** F3 must give the synchronous path this same gate — `execute()`
  never calls `allow_probe` at all, which is this defect through the other door.

## M5C-3 — F3: the synchronous path ignored the circuit breaker (and residency)
- **Severity:** MAJOR (fixed)
- **Finding:** F3 (Fable verification, 2026-08-30)
- **Where:** `services/execution.py` (`ExecutionContext`, `execute`, `_execute_attempts`),
  `services/routing.py` (`route`), `domain/routing/explanation.py` (`build_explanation`),
  `domain/routing/narrative.py`, `web/routes/generate.py` (`_context`),
  `web/routes/routing.py` (`post_route`), `tests/integration/test_breaker_sync_path.py`,
  `tests/unit/test_cli.py`, api.md integration guidance
- **What happened:** Reproduced as five tests run against the pre-fix code: with the runtime's
  breaker opened on the only model, `POST /route` and `POST /generate` both succeeded on it —
  nothing in the synchronous path referenced the breaker, exactly as the finding says. Fixed at
  three levels. (1) `route()`'s `open_circuit_breakers` is now `frozenset | None = None`, where
  `None` means *no breaker registry existed to consult* and raises a new
  `breaker_state_unavailable` flag on the explanation (with a narrative meaning and an api.md
  note) — an empty set is never silently assumed; the CLI's one-shot `route explain` and
  `generate` carry the flag, asserted in `test_cli.py`. (2) `ExecutionContext` gained
  `breakers`, `resident_models` and `resident_devices`; the web builders fill them from
  `app.state.queue_runtime`, so `POST /generate` and `POST /route` now reject a breaker-open
  model with `recently_failing` (asserted per entry point) and rank residency as the queue
  does. (3) `_execute_attempts` marks and releases the probe exactly as the worker's loop does:
  `allow_probe` once per candidate, a refusal while `probe_busy` skips the candidate (a
  synchronous request must not become a second, unmarked probe — F2's defect through the other
  door), and a cancelled probe is handed back. A mid-flight test observes `probe_in_flight`
  true from inside `on_chunk` while the attempt runs; another marks a foreign probe first and
  asserts the request is refused with `recently_failing` + `probe_in_flight: true` and that
  the provider was never called.
- **What the next run must do:** Nothing. If a runtime ever serves without a queue, `_context`
  already degrades to `breakers=None`, which is disclosed, not silent.

## M5C-4 — F4: behind the mandated TLS proxy the failed-auth brake locked everyone out
- **Severity:** MAJOR (fixed)
- **Finding:** F4 (Fable verification, 2026-08-30)
- **Where:** `config.py` (`ServerSettings.trusted_proxies`), `web/rate_limit.py`
  (`resolve_client_address`), `web/app.py`, `services/settings.py`
  (`CONFIG_ONLY_SECURITY_KEYS`), `docs/configuration.md` (regenerated),
  `tests/security/test_rate_limit.py`, api.md §11
- **What happened:** Reproduced in-process what Fable verified on a real socket: with the
  failure budget spent through one address, a *correct* token gets 429 for the rest of the
  minute — and behind ADR-0014 §7's mandated reverse proxy every caller shares one address, so
  anyone's twenty bad bearers braked all users. ADR-0014 promised `X-Forwarded-For` trust "as
  explicit configuration" and no such setting existed. Added `[server] trusted_proxies = []`
  (CIDRs, validated at startup, config-only per M5-13's rule): when the connecting peer is in
  it, the brake and the unauthenticated bucket key on the **last untrusted hop** of
  `X-Forwarded-For` (rightmost entry not itself a trusted proxy — everything left of it is
  client-supplied text); from any other peer the header is ignored entirely. Both halves are
  tested: a forged header from an untrusted peer neither escapes the brake nor pins failures
  elsewhere, and behind a trusted proxy the guessing client is braked while its neighbour with
  a correct token is untouched, chains included; the pure function's corners (all-trusted
  chain → peer, unparseable entry is the client, absent header) are unit-tested. The
  trusted-proxy test was watched failing pre-fix (the setting did not exist to pass).
  **The decision Fable asked to be recorded:** the brake stays keyed by address alone, *not*
  `(address, presented-credential digest)` — keyed by credential a guesser would mint a fresh
  bucket with every guessed token and the brake would never fire; the deployment that motivated
  the concern is fixed properly by `trusted_proxies`, which gives clients their own addresses
  back; the residual NAT-shared-address collateral is bounded to the rest of the minute and now
  documented in api.md §11 (what the brake does to valid tokens included).
- **What the next run must do:** The deployment guide's proxy example should set
  `trusted_proxies` alongside `allowed_hosts`; F5's documentation pass touches the same page.

## M5C-5 — F5: the UI token cookie cannot be set on a plain-HTTP non-loopback bind
- **Severity:** MAJOR (fixed by documentation and a warning; the flags stay)
- **Finding:** F5 (Fable verification, 2026-08-30)
- **Where:** `bootstrap.py` (the startup warning), `web/templates/error.html` (the 401 page),
  api.md §11, `docs/security.md`, `tests/security/test_scopes.py`
- **What happened:** Fable verified in Chromium against `http://10.77.10.84:8792` that the
  browser stores neither the `__Host-mw-csrf` cookie nor the `Secure` token cookie on an
  insecure non-loopback origin, so `POST /token-cookie` is `403 CSRF_FAILED` and pages stay
  401, while the same flow works on `http://127.0.0.1` and the API is unaffected. That is the
  cookie flags doing their job — per the finding's own instruction, **nothing was weakened**.
  Closed as a disclosure gap: api.md §11 and `docs/security.md` now state that the tokened-bind
  UI needs HTTPS or loopback and why (with the exact failure signature), the 401 page itself
  says "This form needs HTTPS or loopback" beside the form (asserted in the tokened-bind
  test), and `bootstrap()` emits ADR-0014 §7's startup warning — `server.plain_http_exposure`
  — on a non-loopback bind with no `trusted_proxies` configured, `trusted_proxies` (M5C-4)
  being the one piece of configuration that evidences a proxy. The warning is tested both ways
  (fires without a proxy, silent with one; a caplog note records that `configure_logging`
  replaces root handlers and must be neutralised to observe it).
- **What the next run must do:** Nothing. If a future deployment story wants the UI on plain
  HTTP, the answer stays no; ADR-0014 §7's proxy is the path.

## M5C-6 — F6: `/jobs/{id}` rendered its explanation link as text
- **Severity:** MAJOR (fixed)
- **Finding:** F6 (Fable verification, 2026-08-30)
- **Where:** `web/templates/jobs/detail.html`, `tests/e2e/test_job_detail.py`
- **What happened:** Reproduced: the "Explanation" `<dd>` held the literal
  `&lt;a href=&#34;/routing/…&#34;&gt;decision …&lt;/a&gt;`. The mechanism is worth recording:
  the row built HTML with `| e` on the interpolated pieces and `| safe` on the whole — but
  Jinja's `~` under autoescape compiles to `markup_join`, which escapes the *plain-text*
  operands (the `<a href=` literals) the moment one operand is Markup, and the outer `| safe`
  then seals the already-escaped text in. MirrorWall's `kv_list` has **no link facility**
  (`<dd>{{ item.value }}</dd>`, checked) — recorded as a MirrorWall 0.2.1 item below, and per
  the finding the row is now a plain paragraph of real anchors under the definition list, with
  the decision link present whether or not the narrative renders. The e2e test asserts
  `href="/routing/{decision_id}"` *and* that `&lt;a href=` appears nowhere; both were watched
  failing against the old template. (The pre-existing `href="/routing/` assertion passed all
  along because the *narrative* block, when present, has its own link — the escaped row was the
  only navigation when it is not.) The escaped blob was also what scrolled the page at 375 px;
  the wrap stopgap is M5C-11's, shared by this page.
- **What the next run must do:** When MirrorWall 0.2.1 ships a `kv_list` link facility, the
  paragraph can fold back into the list. Until then, never pass HTML through `kv_list`.

## M5C-11 — F11: `/system` scrolled horizontally at 375 px
- **Severity:** MINOR (fixed with a recorded stopgap)
- **Finding:** F11 (Fable verification, 2026-08-30); F6 covers `/jobs/{id}`'s instance
- **Where:** `web/templates/system/index.html`, `web/templates/jobs/detail.html`,
  `tests/e2e/test_system_page.py`, `tests/accessibility/test_ui_checklist.py` (the manual §13
  list)
- **What happened:** The cause on `/system` is the 64-character machine fingerprint in a
  `.kv-list dd`: MirrorWall's `.kv-list` grid gives `dd` no wrapping rule, so one unbreakable
  token widens the page. `/jobs/{id}` has the same shape once real canonical IDs
  (`provider/name@sha256:…`) land in its list. LoadCoach owns no stylesheet, so both templates
  carry a commented stopgap in `{% block head %}` — `.kv-list dd { overflow-wrap: anywhere; }`,
  structural, no colour — asserted present by their e2e tests and removable when MirrorWall
  0.2.1 carries the rule in `components.css` (item recorded below). No browser runs in this
  suite, so the `scrollWidth <= innerWidth` check itself stays in the manual §13 list, which
  now names these two pages first with exactly that console line.
- **What the next run must do:** Take the MirrorWall 0.2.1 item and delete both stopgaps.

## M5C-7 — F7: routing §5.1 still promised what M5-1 removed
- **Severity:** MAJOR, contract (fixed)
- **Finding:** F7 (Fable verification, 2026-08-30)
- **Where:** `~/ai/suite/docs/apps/loadcoach/routing.md` §5.1 (mirrored byte-identically into
  `LoadCoach/docs/apps/loadcoach/`), new `~/ai/suite/docs/adr/0037-…`, `docs/adr/README.md`
- **What happened:** §5.1's table listed *production evidence from executed jobs* as a
  capability-scoring signal and closed with "self-improving as production evidence
  accumulates", while §11 (edited in M5) says production evidence never enters capability
  scoring and the code bounds the factor to `[0.5, 1]` — it can only lower a score. Rewrote
  §5.1's row (never a capability score; acts only through the reliability factor, downward) and
  the sentence (routing without FreeWeight is *guarded rather than self-improving*; improvement
  comes from measurement). **ADR-0037** records the decision with M5-1's three reasons as
  context and names the deferral: upward adaptation from production success is post-1.0
  exploration routing (spec §21), because feeding production success back without exploration
  entrenches the incumbent. ADR-0036 was also missing from `docs/adr/README.md`'s index —
  found while adding 0037's row; both rows added. Edited in the docs repo first, mirrored with
  `cmp` proving byte-identity.
- **What the next run must do:** Nothing until exploration routing; ADR-0037's revisit clause
  points at M5-1's migration note.

## M5C-8 — F8: `discover_models` was the one writer outside M5-17's rule
- **Severity:** MINOR (fixed)
- **Finding:** F8 (Fable verification, 2026-08-30)
- **Where:** `services/models.py` (`discover_models`), `web/routes/models.py`,
  `cli/commands/models.py`, `tests/security/test_scopes.py`
- **What happened:** `discover_models` wrote to the registry with no `principal` argument; its
  `admin` check lived at the route alone — exactly P9's named failure mode, in the one writer
  M5-17 missed. It now takes `principal: Principal | None = None` and calls
  `authorize(principal, "admin")` before touching the provider or the database; the route hands
  its principal down, the CLI passes `LOCAL`, and the internal callers (startup's
  `try_discover_models`, the scheduled refresh) pass `None` — an internal call with no request
  behind it, allowed per M5-17. The direct-call scope test's list is **nine**: a write-scoped
  principal is refused with `required_scope: admin` before anything is written. Watched failing
  pre-fix (the parameter did not exist to refuse).
- **What the next run must do:** Nothing; M5-17's closing rule now has no exception.

## M5C-9 — F9: retention's promise unfulfilled, and spec §14's sentence still pre-M5-14
- **Severity:** MINOR (fixed)
- **Finding:** F9 (Fable verification, 2026-08-30)
- **Where:** `services/queue.py` (`job_document`), `web/templates/jobs/detail.html`,
  `~/ai/suite/docs/apps/loadcoach/spec.md` §14 (mirrored), `tests/integration/test_retention.py`
- **What happened:** `services/retention.py`'s docstring promises the page and the API can say
  "content removed by retention", but nothing consumed the `content_scrubbed_at` marker: a
  scrubbed job's page simply showed no Output section. `job_document` now carries a
  `retention.content_scrubbed_at` field read from the marker, and `/jobs/{id}` renders "Content
  removed by retention at <instant> — the hashes, token counts, timings and the routing
  decision remain", plus the backup caveat. Spec §14's "stored as hashes by default" sentence —
  written before M5-14's reconciliation — now states what M5-14 decided: text kept for
  `content_retention_hours` (24) after completion, then swept; and it documents that a
  `loadcoach db backup` taken before the sweep is a byte copy that keeps the text outside the
  sweep's reach. The retention test asserts the API field, the page text and that an
  unscrubbed job's field is `null`; watched failing pre-fix.
- **What the next run must do:** Nothing in LoadCoach. The WeightsDB item below is F9's other
  half.

## M5C-10 — F10: spec §17's `gpu_telemetry` health component never existed
- **Severity:** MINOR (fixed — removed, with the decision recorded)
- **Finding:** F10 (Fable verification, 2026-08-30); M5-5 had left it open
- **Where:** `~/ai/suite/docs/apps/loadcoach/spec.md` §17 and api.md §1 (both mirrored),
  `services/health.py`, `services/doctor.py`, `tests/e2e/test_server_boot.py`,
  `tests/unit/test_doctor.py`
- **What happened:** Chose **remove** over build: a machine without a GPU is not unhealthy —
  absence is `UNSUPPORTED`, never a failure (ADR-0016) — and the readings already live on
  `GET /system/status` and the System page, so a health component would restate a routing
  input as a health state. §17 and api.md §1 (which listed it too) now name exactly the five
  components `/api/v1/health` reports, with §17 recording why GPU telemetry is deliberately
  not among them. A new contract-style test parses the two mirrored documents and holds them
  and the endpoint to one list — it was watched failing against the stale mirror, which is how
  §17 and `/health` are made to *agree* rather than merely coincide. Fallout: the doctor's
  useful telemetry check was labelled `degraded:gpu_telemetry`, claiming the phantom
  component; renamed `degraded:telemetry` with the doctor test recording why it is exempt from
  the component check (the *admission* contract degrades, queue §5, not health).
- **What the next run must do:** Nothing. If GPU health ever becomes a real component, it needs
  a definition of unhealthy that is not "no GPU"; start from ADR-0016.

## M5C-12 — F12: streamed tokens quantized to a 10 ms poll
- **Severity:** NOTE (fixed and re-measured over a real socket)
- **Finding:** F12 (Fable verification, 2026-08-30)
- **Where:** `web/routes/generate.py`, `web/routes/jobs.py` (both token-carrying streams),
  `tests/performance/test_streaming_gap.py` (new)
- **What happened:** MirrorWall's SSE loop sleeps `poll_interval_seconds` whenever the
  subscription is momentarily empty, so token delivery quantizes to the poll. Chose *lower the
  poll* over a condition wake-up: MirrorWall's `Subscription` is deliberately a deque under a
  lock, never awaitable, because publishers are worker threads without event-loop portals
  (ADR-0003 §5-6) — making it awaitable is a MirrorWall design change, not a closeout edit.
  Both token streams now poll at 2 ms. Re-measured over a real TCP socket, per the finding, with
  a new performance test that serves the application under uvicorn on loopback and paces the
  fake provider at a real 5 ms/token cadence: **old poll** raw gap median 0.26 ms / p95
  10.34 ms (Fable measured 10.2 — the harness reproduces the finding), added-latency p95
  5.34 ms over the 5 ms budget; **new poll** raw gap median 4.22 ms / p95 6.29 ms / max
  6.62 ms, **added-latency p95 1.29 ms** against the 5 ms target and 20 ms ceiling. The test's
  hard assertion is the ceiling (a shared machine may miss the target on a bad run); the
  figures print for every report.
- **What the next run must do:** If streaming latency ever needs to go below the poll floor, the
  MirrorWall item is a wake-up fd or condition on `Subscription` — take it there, not here.

## M5C-13 — F13: name the interpreter, every time
- **Severity:** NOTE (adopted)
- **Finding:** F13 (Fable verification, 2026-08-30)
- **What happened:** M5-25 said "Python 3.13 virtualenv" while the repo's `.venv` is 3.14.4 —
  a corrected note now sits on M5-25. This closeout names its interpreter and invocation in
  every gate report and commit message: the local gate ran on **Python 3.14.4** under the bare
  `pytest` console script (the invocation CI uses, post-F1); the runner reproduction ran on
  **python:3.12-slim** from `requirements/ci.lock`.
- **What the next run must do:** Keep doing it. "Green locally" is meaningless without the
  interpreter and the invocation.

## M5C-15 — Found by the first real runner run: migration 0006 was a syntax error on PostgreSQL
- **Severity:** MAJOR (fixed) — the PostgreSQL job could never pass
- **Finding:** none of Fable's fourteen; exposed by the first push whose pytest step actually
  ran (F1 unblocked it)
- **Where:** `infrastructure/db/migrations/versions/0006_feedback_and_reliability.py`,
  `infrastructure/db/models.py` (`ReliabilityStats.__table_args__`)
- **What happened:** The runner's `tests (PostgreSQL)` job failed at its pytest step; reproduced
  locally against a real `postgres:16` from the runner's exact install
  (`python:3.12-slim` + `ci.lock` + `WEIGHTSDB_REQUIRE_POSTGRES=1`):
  `psycopg.errors.SyntaxError: syntax error at or near "window"` while creating
  `reliability_stats` — `window` is a PostgreSQL reserved word, and migration 0006's
  `CheckConstraint("window IN ('7d','30d','all')")` is raw SQL text nothing quotes. SQLite
  accepted it, which is why 796 local tests never saw it; the migration had *never* applied on
  PostgreSQL. Fixed by quoting the identifier (`"window"`), which both dialects accept, in the
  migration **and** the model's constraint (they must match or `check_parity` refuses).
  **Edited the applied migration in place, deliberately, and here is the reasoning:** a
  follow-up migration cannot amend a CREATE TABLE that has no successful state to amend on the
  dialect where it fails, and no released database exists to carry the old text (1.0.0 is
  untagged). After the fix, the runner-equivalent PostgreSQL run passes 232 tests (the two
  PostgreSQL-only migration tests included).
- **What the next run must do:** Nothing here. The general lesson joins F13's: a migration is
  not "applied" until it has applied on **both** supported dialects, and only the runner (or
  the local `postgres:16` line above) proves the second one.

## WeightsDB 0.2.1 item (raised by F9)
- Fable found `secure_delete=1` is this machine's SQLite *default* and WeightsDB does not set
  the pragma, so whether scrubbed text is actually overwritten on disk currently depends on the
  host's SQLite build. WeightsDB 0.2.1 should issue `PRAGMA secure_delete=ON` at connect so a
  retention scrub means the same thing on every machine. Do not change LoadCoach for it.

## MirrorWall 0.2.1 items (raised by F6 and F11)
- `kv_list` needs a link facility — a `{"label", "value", "href"}` item shape or similar — so a
  definition-list value can be an anchor without smuggling HTML through the escaper (M5C-6).
- `components.css` `.kv-list dd` needs `overflow-wrap: anywhere` (or `break-word`): a long
  unbroken value — a canonical ID, a 64-character fingerprint — currently widens the page at
  narrow widths; both LoadCoach pages carry a commented stopgap to delete (M5C-11).

## M5C-14 — Found under F1's Docker line: the checklist fixture read the real GPU, and candidate tables had no row-count
- **Severity:** MAJOR (fixed) — it would have kept CI red after F1
- **Finding:** none of Fable's fourteen; exposed the moment F1 let the suite collect in a
  GPU-less environment
- **Where:** `tests/accessibility/test_ui_checklist.py` (`client`),
  `src/loadcoach/web/templates/routing/detail.html`, `tests/e2e/test_job_detail.py`
- **What happened:** With `pythonpath` fixed, F1's Docker 3.12 line ran the suite for the first
  time in a GPU-less environment and
  `test_tables_have_headers_scope_and_a_row_count` failed on `/routing/{decision_id}`: 3 tables,
  1 row-count + 1 caption. Two defects, reproduced by rendering the page in both environments.
  (1) The module-scoped checklist ``client`` is built before the function-scoped autouse
  ``_deterministic_telemetry`` pin — the *same ordering* M5-15 records for XDG isolation, missed
  for telemetry — so its routing decision read the machine's real GPU: on this workstation
  (card mostly full) the hostile model was rejected ``insufficient_vram`` and the captioned
  rejected table balanced the count; on the runner and in Docker (no GPU, VRAM constraint not
  evaluated) it became a second candidate. The fixture now pins the identical 48 GiB snapshot
  itself, per M5-15's own rule. (2) The balance was accidental anyway: candidate capability
  tables passed neither ``caption`` nor ``row_count`` to MirrorWall's table macro, so any
  decision with ≥ 2 candidates violates UI standards §5's row-count rule. The template now
  passes ``row_count``, and the job-detail e2e test anchors the row-count to each candidate's
  own table (regex over ``data-table="candidate-…"``) — reverting the template line fails it;
  restoring the unpinned fixture fails the Docker run, which is where it was watched failing.
- **What the next run must do:** Nothing here. The rule M5-15 stated now has two instances:
  a fixture scoped wider than ``function`` must do its *own* XDG isolation **and** its own
  telemetry pin.
