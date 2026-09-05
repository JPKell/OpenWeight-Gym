# C6 handoff — LoadCoach, four token classes on the wire

**Row:** C6 of `docs/roadmap/outstanding-work.md` §1. **Repositories:** `LoadCoach` (three commits
plus a docs mirror) and `docs` (one commit). **Started at** LoadCoach `2c7d740` / docs `b8d45b7`,
both clean. **Ends at** LoadCoach `01170a7` and docs `261c491`, both clean, **nothing pushed,
nothing tagged, no version bump**. This rides `loadcoach 1.1.0` at H2, alongside `2c7d740`.

**Model deviation, for `model-assignment.md` §3.5:** ran on **Opus 5 · high** rather than the
scheduled *Sonnet 5 · standard*, combined with C5 in one overnight session.
*Did the upgrade earn its keep?* **For this row, honestly, no — with one exception.** The
transcription was exactly what §3.4 describes: two columns, two fields, a migration, against
documents that already said the shape. The exception is §2 below — noticing that
`test_migration_0006_touches_no_column_an_earlier_revision_created` read its "after" schema at
*head* rather than at `0006`, and that this made it a latent assertion about every future
revision rather than about `0006`. It failed the moment `0007` existed, and the tempting fix — the
one that keeps a green suite — is to add `0007`'s columns to that test's expectations, which would
have preserved the defect and quietly made `0006`'s drift check meaningless. Taking the other
branch is worth something. Everything else here would have gone the same way at the scheduled tier.

---

## 1. Gate results

Interpreter: **Python 3.14.4**, `LoadCoach/.venv` (`.venv/bin/python --version`). There is no
`python3.12` on this machine. Run from `/home/jpk/ai/suite/LoadCoach`:

```
.venv/bin/ruff format --check .        188 files already formatted
.venv/bin/ruff check .                 All checks passed!
.venv/bin/mypy src tests               Success: no issues found in 168 source files
.venv/bin/lint-imports                 Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                       3 failed, 828 passed, 3 skipped, 15 deselected
```

Coverage: **91.57 %** against the **85 %** application floor.

### ⚠ The suite is not fully green, and the three failures are **not this row's**

```
FAILED tests/contract/test_evidence_import.py::…_round_trips_through_the_store_unchanged[1.1-full]
FAILED tests/contract/test_evidence_import.py::…_round_trips_through_the_store_unchanged[1.1-mixed]
FAILED tests/contract/test_evidence_import.py::…_round_trips_through_the_store_unchanged[1.1-unsupported]
```

**Verified pre-existing, not assumed.** I stashed every C6 change (`git stash push -u -- src
tests`), ran the file at `2c7d740` with a clean tree, and got the same three failures; then
restored. The failure is:

```
ValidationError: 1 validation error for CapabilityEvidenceOut
adapter — Extra inputs are not permitted
```

**Cause, and why it is a real finding for H2 rather than noise.** The test iterates
`PUBLISHED_SCHEMAS[BUNDLE_SCHEMA]` — *every version this build of SetSpec publishes* — and
validates each golden against `setspec.capability.v1.CapabilityEvidenceOut`, the frozen **1.0**
writer model. This venv resolves `setspec` to the **working tree at 0.6.0** (SetSpec's own tree is
clean at `53d2c16`), which publishes `benchmark.evidence_bundle` **1.1** goldens carrying the
optional `adapter` field ADR-0058 added. A 1.1 payload validated against the 1.0 model is
correctly rejected: the model is frozen and `extra="forbid"`.

CI does not see this — `requirements/ci.lock` pins `setspec==0.4.0`, which publishes no 1.1
bundle goldens, so the parametrisation produces no 1.1 cases at all.

**So this is a forward-compatibility defect that H2 will walk straight into**, since H2 is the row
that resolves the stale `setspec>=0.4,<0.5` pin. The test needs to say which writer model applies
to which schema version, or LoadCoach's evidence store needs to decide whether it carries 1.1's
`adapter` field — which is an ADR-0058/LA3 question, not a C6 one. I did not touch it: it is
outside this row's scope in every direction, and guessing at it would be worse than reporting it.

The PostgreSQL legs of the migration tests **skipped** (3 skipped): there is no PostgreSQL on this
machine and `pg_isready` is not installed. They run in CI's `db-matrix` job. I am not reporting a
green suite that never touched PostgreSQL — **the PostgreSQL half of migration `0007` is
unverified locally**, and confirming `db-matrix` is a "before the next session" item below.

---

## 2. What changed

### The documents, first (commit `261c491` in `docs`, mirrored by `ef53629` in `LoadCoach`)

* `data-model.md` — `cache_write_tokens NULL · cache_read_tokens NULL` added to the `jobs` and
  `job_attempts` column lists, each on its own line beneath the existing token columns rather than
  extending a line to ~120 characters. The `jobs` entry carries the file's own inline-comment
  style: `-- ADR-0070: NULL is unreported, 0 is a count`.
* `api.md` — §4's `usage` object gains both fields, plus a note saying once, for an API reader who
  will never open the ADR, what the cache classes mean and that `0` is a real count while
  `"unsupported"` is not a number. **§5 carries no second JSON literal** — it is a table plus prose
  — so there was one `usage` example to amend, not two; the note says the job document carries the
  same object rather than duplicating it.
* **No reflow.** The diff is 12 insertions and 1 deletion across both files (the deletion is the
  single `usage` line being replaced).
* **Mirror proven:**
  ```
  cmp docs/apps/loadcoach/data-model.md LoadCoach/docs/apps/loadcoach/data-model.md   → byte-identical
  cmp docs/apps/loadcoach/api.md        LoadCoach/docs/apps/loadcoach/api.md          → byte-identical
  ```

### Migration `0007` (commit `57aeb2e`)

Four nullable `Integer` columns, two per table. **No backfill, no server default, no data
migration** — an existing row genuinely has no value for these, `NULL` is how this schema already
says "not reported", and a `0` default would be a fabricated zero applied retroactively to every
historical row at once.

**The downgrade on SQLite.** `batch_alter_table` in both directions, following revision `0003`'s
convention. SQLite has no plain `ALTER TABLE … DROP COLUMN` Alembic will emit here, so batch mode
recreates the table by copy-and-move; on PostgreSQL it emits a plain `ALTER`. A downgrade that
only worked on PostgreSQL would fail in the default dialect (ADR-0006) — the one most likely to be
running when somebody actually reaches for a downgrade. The SQLite test asserts the columns are
gone, that `id`/`attempt`/`input_tokens`/`output_tokens` **survived the rebuild**, and that a
re-upgrade returns to head with `check_parity` matching.

**`check_parity` matches after upgrade on SQLite**, and after every leg of the round trip. The
PostgreSQL equivalent is written and skips here.

**The `0006` drift test.** `test_migration_0006_touches_no_column_an_earlier_revision_created`
read its "after" schema by upgrading to *head*, which was `0006` only for as long as `0006` was
head. `0007` is the first revision to add a column to a table an earlier revision created —
deliberately and additively — so that test failed. It is pinned to `revision="0006"`, which is
what `0005`'s equivalent already did, and `0007` has its own drift check asserting the difference
between `0006` and `0007` is exactly those four columns and no table. Fixing it the other way —
adding the new columns to `0006`'s expectations — would have made `0006`'s drift check assert
nothing.

### Capture and the wire (commit `1841f5e`)

`AttemptRecord`, `ExecutionOutcome` and `queue.JobRecord` each gain the two fields, read through
the existing `_count` helper (`execution.py:378`), which already returns `None` rather than `0` for
an unsupported value and is exactly right. Both execution paths are covered because they build the
same `ExecutionOutcome`: `execution.py` (synchronous) and `worker.py` (queue). Both `values={…}`
dicts that write the job row and the attempt row carry them, as does `write_attempt`.

On the wire: `ExecutionOutcome.as_json()`'s `usage` block and `job_document`'s `usage` block, both
rendering `"unsupported"` when the value is `None`, exactly as `thinking_tokens` does beside them.

**The job event stream** carries `summary.as_json()`, so the new fields reach job events for free.
Flagged here rather than discovered at F1.

---

## 3. The two §4 decisions, made explicitly

**(a) `input_tokens`/`output_tokens` still render `null`, not `"unsupported"`. Not fixed — a
finding.** ADR-0016 rule 4 says an unavailable measurement is the string `"unsupported"` in JSON,
never `null`. These two fields render `None` → `null` today, in the same dict literal where
`thinking_tokens` correctly renders `"unsupported"`. The inconsistency is real and predates this
row.

I did not fix it, for three reasons, and I want the next session to weigh them rather than inherit
a decision: changing it would alter an **existing field's type on a released 1.0 API**, which is a
break, not the additive change this row is scoped to; it is not in ADR-0070's scope; and it
deserves its own decision rather than a quiet fix in an unrelated session. **It should become a
small ADR.** Note that it is not free to leave: a consumer reading `usage` sees `null` meaning
"unreported" on two fields and `"unsupported"` meaning the same thing on three, in one object.

**(b) The attempts list in the job document gained no token fields.** `AttemptRecord.as_json()`
carries no counts today and still carries none. ADR-0070 decision 7 asks for the *rows* and the
job document's `usage`; extending the per-attempt JSON is neither required nor forbidden. I left
it: the rows exist for the record and the `usage` object is the contract, and adding per-attempt
counts to the document would be a second, unrequested API surface for the same data. The
`job_attempts` **rows** do carry the cache classes, so nothing is lost — a consumer that needs
per-attempt token counts should ask for the fields deliberately rather than inherit them.

---

## 4. The OpenAPI snapshot did not move — confirmed, not assumed

`tests/contract/test_openapi_snapshot.py` passes unchanged (`2 passed`). The job document is an
untyped dict and no response model changed, so the live schema is identical. `docs/openapi.json`
was **not** regenerated and did not need to be.

---

## 5. The editable-venv finding (OVERRIDE 2), and what it means for CI

**Every suite dependency in LoadCoach's venv is an editable pointing at the working trees** — not
just ModelRack. Confirmed, and **the venv was not modified**: `pip install -e ".[dev]"` was **not
run**, per OVERRIDE 2.

`.pth` snapshot, **identical before and after** (`diff` reports no change):

```
.venv/lib/python3.14/site-packages/_editable_impl_baseaicore.pth
.venv/lib/python3.14/site-packages/_editable_impl_loadcoach.pth
.venv/lib/python3.14/site-packages/_editable_impl_mirrorwall.pth
.venv/lib/python3.14/site-packages/_editable_impl_modelrack.pth
.venv/lib/python3.14/site-packages/_editable_impl_setspec.pth
.venv/lib/python3.14/site-packages/_editable_impl_sweatmeter.pth
.venv/lib/python3.14/site-packages/_editable_impl_weightsdb.pth

import modelrack → /home/jpk/ai/suite/py/ModelRack/src/modelrack/__init__.py   (after, unchanged)
```

**The metadata is stale across the board**, not only for ModelRack — `pip list` claims
`baseaicore 0.4.0`, `loadcoach 0.1.0` (the repo is `1.0.0`), `mirrorwall 0.2.0`, `modelrack 0.5.0`,
`setspec 0.3.0`, `sweatmeter 0.4.0`, `weightsdb 0.2.0`. The code is live; the numbers are fiction.

**What CI has instead.** `requirements/ci.lock` pins **`modelrack==0.5.0`** (line 711) and
**`setspec==0.4.0`** (line 1104), installed from the hash-pinned lock with `--no-deps`. So:

* **This local suite and CI are testing different ModelRacks and different SetSpecs.** A local
  green and a CI green are not the same statement.
* It explains §1's three failures exactly (setspec 0.4.0 publishes no 1.1 bundle goldens).
* **The rule I followed, throughout:** every C6 test **scripts all four token classes explicitly**
  on `FakeGeneration` — integers and `UNSUPPORTED` alike — and none relies on the fake's defaults.
  Under `modelrack 0.5.0` an unscripted cache class derives `UNSUPPORTED`; under the working tree
  (row C5) it derives `0`. A test asserting `0` from an unscripted generation would pass here and
  fail in CI. I verified explicit scripting is version-safe rather than assuming it:
  `git show v0.5.0:src/modelrack/providers/_fake_script.py` contains
  `if value is None or value is UNSUPPORTED: continue`, so an explicitly scripted `UNSUPPORTED`
  validated in 0.5.0 exactly as it does now. **The new tests should behave identically in CI.**

**Related, and wider than OVERRIDE 2 recorded: FreeWeight's venv is editable on ModelRack too**
(recorded in `docs/history/C5_HANDOFF.md` §7). A ModelRack change is immediately live in *two* of the three
applications' local suites and in neither of their CI runs.

### The one-shot end-to-end check (OVERRIDE 2's single permitted run)

Run once as a scratch script, **not committed as a test**. A real `OllamaProvider` from the
editable working tree (carrying C5), against the **live Ollama 0.32.13** on this machine, pushed
through LoadCoach's own `_count` and the `usage` object's rendering rule:

```
resolved: ollama/gemma3:latest@sha256:a2af6cc3eb7f

what the real adapter reported:
    input_tokens         = 18    supported=True
    output_tokens        = 3     supported=True
    cache_read_tokens    = 0     supported=True
    cache_write_tokens   = 0     supported=True
    total_tokens         = 21

through LoadCoach's _count (what goes into the rows):
    {'input_tokens': 18, 'output_tokens': 3, 'cache_read_tokens': 0, 'cache_write_tokens': 0}

LoadCoach's wire rendering:
    {"input_tokens": 18, "output_tokens": 3, "cache_write_tokens": 0,
     "cache_read_tokens": 0, "thinking_tokens": "unsupported"}
```

**It agrees with the constructed-`TokenUsage` tests exactly.** A real adapter's cache classes land
on LoadCoach's wire as the number `0`, `_count` stores `0` rather than `None`, and `total_tokens`
is a real number against a live provider — the ADR-0069 improvement, observed rather than argued.
No disagreement to report, which is the boring outcome and the one worth having.

---

## 6. For F1 — what the wire looks like before and after `modelrack 0.7.0`

The estimator must not be written against the interim shape. **The same LoadCoach code produces
both**; only the installed ModelRack differs.

**Now** (LoadCoach installs `modelrack 0.5.0`/`0.6.0` — every real adapter leaves the cache classes
`UNSUPPORTED`):

```json
"usage": {"input_tokens": 812, "output_tokens": 1104,
          "cache_write_tokens": "unsupported", "cache_read_tokens": "unsupported",
          "thinking_tokens": "unsupported"}
```

**After `modelrack 0.7.0` (row H1) is published and LoadCoach adopts it (row H2)** — Ollama, and
an OpenAI-compatible server doing no cache accounting:

```json
"usage": {"input_tokens": 812, "output_tokens": 1104,
          "cache_write_tokens": 0, "cache_read_tokens": 0,
          "thinking_tokens": "unsupported"}
```

**And against a server that does report cached input**, `cache_read_tokens` is a positive number
and `input_tokens` is the provider's `prompt_tokens` **minus** it — the classes are disjoint and
sum to the provider's prompt figure. Do not add them back together.

Three things F1 must treat as distinct, because LoadCoach keeps them distinct on purpose:
`0` is a real count meaning nothing could have been billed to that class; `"unsupported"` is a
string, not a number, and must never be coerced to `0` or totalled; a positive number is a count.
The interim shape above is exactly the state ADR-0069 found intolerable — a strict money ceiling
trips on every remote turn — so **an estimator written and calibrated against the interim shape
will change behaviour under its own feet at H2.** Write it against the post-0.7.0 shape and let the
interim one take the `UNSUPPORTED` branch.

---

## 7. Stale pins — recorded, not chased

`pyproject.toml` pins:

* **`modelrack>=0.5,<0.6`** while ModelRack is at `0.6.0` (and C5, unreleased, rides `0.7.0`).
* **`setspec>=0.4,<0.5`** while SetSpec is at `0.6.0`.

Neither blocks this row and neither was touched, nor was `requirements/ci.lock` re-resolved. Both
belong to **H2**, the row that bumps this application. Note that H2 must move *both*: the
`modelrack` pin has to reach `0.7.0` for this row's fields to ever carry a number, and the
`setspec` pin is what makes §1's evidence failures real rather than local-only.

---

## 8. Commits

| Repo | Commit | What |
|---|---|---|
| `docs` | `261c491` | `docs(loadcoach): four token classes on the wire and on the rows` |
| `LoadCoach` | `ef53629` | `docs: mirror the LoadCoach documents…` (byte-identical, `cmp`-verified) |
| `LoadCoach` | `57aeb2e` | `feat(db): migration 0007 — cache_write_tokens and cache_read_tokens` |
| `LoadCoach` | `1841f5e` | `feat(services): carry all four token classes to the rows and to the wire` |
| `LoadCoach` | `01170a7` | `docs(changelog): four token classes on LoadCoach's wire` |

All on `main`, both trees clean, `git status --short` empty in all three repos.

---

## 9. Before the next session

1. **Push `main` in `LoadCoach` (`01170a7`) and in `docs` (`261c491`)**, and `py/ModelRack`
   (`94bf5ce`, C5). Nothing is pushed. The VSCode askpass IPC env is needed for `git push` here.
2. **Confirm CI green, including `db-matrix`.** This is the load-bearing one: the PostgreSQL legs
   of migration `0007` skipped locally and `db-matrix` is the only place they run. The SQLite half
   is verified here; the PostgreSQL half is not.
3. **Expect CI to be green on the evidence tests** that fail locally — `ci.lock` pins
   `setspec==0.4.0`. If CI is *red* on them, my §1 diagnosis is wrong and everything in it should
   be re-examined.
4. **Two findings needing a decision, neither this row's to make:**
   * The `null` vs `"unsupported"` inconsistency on `input_tokens`/`output_tokens` (§3a) — should
     become a small ADR.
   * `test_evidence_import.py` against SetSpec ≥ 0.5 (§1) — blocks H2 as written.
5. **This does not publish.** LoadCoach stays at `1.0.0`; this rides **`1.1.0` at H2**, together
   with `2c7d740` and the adapter work. No tag, no version bump.
6. **C6 before F1 is now satisfied.** The hard edge in `outstanding-work.md` §3 is met — but read
   §6 above before writing F1's estimator.
