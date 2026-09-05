# Kickoff — C6: LoadCoach, four token classes on the wire

**Row:** C6 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Sonnet 5 · standard. **Repository:** `/home/jpk/ai/suite/LoadCoach` — `1.0.0`, tagged
and published, clean, with one unreleased fix already on `main` (`2c7d740`).
**Runs after:** C5 (the ModelRack usage rule). **Must land before F1** — a hard edge
([outstanding-work §3](docs/roadmap/outstanding-work.md)): *"all four token classes on LoadCoach's
wire before the harness prices them; without it a strict money ceiling trips on every remote
turn."*
**Ships:** nothing yet. The change lands under `## [Unreleased]` and rides LoadCoach's next minor,
**1.1.0**, which is published at row **H2** (LA2) together with `2c7d740` and the adapter work
([adapter-roadmap §5](docs/roadmap/adapter-roadmap.md) pins LoadCoach `1.1.0` to LA2). Do not bump
the version, do not tag, do not publish.
**Overnight:** permitted — Sonnet rows run at effort **high** overnight
([model-assignment §2.12](docs/roadmap/model-assignment.md)).

**Why this row is `standard`.** Two additive columns and two additive JSON fields, transcribed from
[ADR-0070](docs/adr/0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
decision 7, against a document set that already says exactly what the shape should be. The single
piece of judgment is the migration — a released 1.0 application with real databases behind it, on
two dialects, with a `check_parity` test that will tell you immediately if you got it wrong.

---

## Preconditions

* **The tree is clean and `main` is pushed.** `git status --short` must be empty before you start;
  `2c7d740` is the head and is *deliberately* unreleased.
* **C5 has landed in `py/ModelRack` on `main`** (unreleased — it rides `modelrack 0.7.0` at H1).
  The dependency is presentational rather than mechanical: `baseaicore.TokenUsage` has carried four
  classes all along, so this row's columns and fields work regardless. What C5 changes is whether a
  *real* adapter ever puts a number in them. Until `modelrack 0.7.0` is published and LoadCoach
  installs it, every real response still reports the cache classes `UNSUPPORTED` and this row's new
  fields render `"unsupported"` — which is correct, honest, and exactly the interim ADR-0070
  decision 8 sequences for. **Do not** reach for an editable ModelRack install to make a test
  greener; construct the `TokenUsage` you need in the test.
* **Two stale pins to note, not to chase.** `pyproject.toml` pins `modelrack>=0.5,<0.6` while
  ModelRack is at `0.6.0` (the venv has `0.5.0` installed), and `setspec>=0.4,<0.5` while SetSpec
  is at `0.6.0`. Neither blocks this row. Record them in the handoff — the H2 session, which does
  bump this application, is the one that should resolve them.
* **There is no PostgreSQL on this machine.** `pg_isready` is not installed, so the PostgreSQL legs
  of the migration tests skip locally and run in CI's `db-matrix` job. Say so explicitly in the
  handoff rather than reporting a green suite that never touched PostgreSQL.
* **You are not authorised to push, tag or publish.** Commit on `main` and stop.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/LoadCoach` (and in
  `/home/jpk/ai/suite/docs` for the authoritative copy of the mirrored documents).
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  LoadCoach section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2
  (lines 131–146), then the reading list below.
* **Documents first, then code.** The row says it in as many words: *"`apps/loadcoach/data-model.md`
  and `api.md` amended first."* `docs/` is the single source of truth for this suite; amend the
  workspace copy, mirror it byte-identically into `LoadCoach/docs/apps/loadcoach/`, verify with
  `cmp`, and only then write the migration. Doing it in this order is also the cheapest way to
  discover that you disagree with the shape before it is in a migration.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` everywhere; units in every numeric name (`cache_write_tokens`, `cache_read_tokens` —
  ADR-0070 names them, keep those names exactly, in the columns, the value objects and the JSON);
  keyword-only for anything optional; line length 100; `mypy --strict`.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **85 %** (application floor),
  `CHANGELOG.md` updated under `## [Unreleased]`, one Conventional Commit per logical group.
  **Name the interpreter and the exact invocation in the handoff doc** (M5C-13) — this repo's venv
  is Python 3.14.4; confirm rather than copy. There is no `python3.12` on this machine.
* **Additive only, within `/api/v1`.** No field removed, no field's type changed, no new API
  version. A client written against 1.0.0 must read the new response unchanged.

## Setup

```bash
cd /home/jpk/ai/suite/LoadCoach
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be empty before you start
```

## Reading list

1. [ADR-0070](docs/adr/0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
   — **decision 7 is this row**, in one paragraph. Read decisions 1–6 for what is now upstream of
   you, and *Consequences* for why a migration on a released 1.0 application is the accepted price
   ("it is the price of PromptCadence reaching models only through LoadCoach").
2. [ADR-0016](docs/adr/0016-unavailable-is-not-zero.md) — **rule 4**: in JSON, an unavailable
   measurement is the string `"unsupported"`, never `null` and never `0`. `thinking_tokens` in the
   `usage` object is the shipped precedent, in the same dict literal you are editing.
3. [ADR-0069](docs/adr/0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md)
   §"Not decided here" — why this matters downstream: without all four classes on the wire,
   PromptCadence rebuilds a `TokenUsage` with unsupported cache classes and a strict money ceiling
   trips on every remote turn.
4. [`docs/apps/loadcoach/data-model.md`](docs/apps/loadcoach/data-model.md) — the `jobs` column
   list (around line 149) and the `job_attempts` list (around line 165). These are the two lines
   you amend.
5. [`docs/apps/loadcoach/api.md`](docs/apps/loadcoach/api.md) — §4's `POST /generate` response
   (the `usage` object at line 92) and §5's job document. Both carry the same `usage` shape, and
   both change.
6. The code, in this order: `src/loadcoach/infrastructure/db/models.py` (`Job` around line 518,
   `JobAttempt` around line 564); `src/loadcoach/services/execution.py` — `AttemptRecord` and
   `ExecutionOutcome` (around lines 205–305), the capture sites (around 887 and 1555), and the
   persistence sites (around 1164 and 1221); `src/loadcoach/services/worker.py` around line 1341,
   where the async path builds the same `ExecutionOutcome`; `src/loadcoach/services/queue.py`'s
   `job_document` (around line 1336, the `usage` block).
7. `src/loadcoach/infrastructure/db/migrations/versions/0006_feedback_and_reliability.py` — the
   most recent migration and the local convention, including its docstring's warning that
   re-declaring an existing column is drift that `check_parity` reports, and the M5C-15 lesson in
   its history (a PostgreSQL reserved word that only failed on one dialect).
8. `tests/integration/test_migrations.py` — `check_parity` on both dialects, and how the
   PostgreSQL legs are gated.

## The work

### 1. The documents, first

* `data-model.md`: add `cache_write_tokens` and `cache_read_tokens` to the `jobs` column list and
  to the `job_attempts` column list, beside the existing `input_tokens · output_tokens`. Keep the
  file's compact style; do not reflow neighbouring lines (`CLAUDE.md`, working-tree integrity — a
  reflowed markdown file is exactly the mutation the workspace has been bitten by).
* `api.md`: the `usage` object in §4 and §5 becomes four token classes plus `thinking_tokens`, with
  `"unsupported"` shown for a class the adapter did not report. Add a one-line note saying what the
  cache classes mean and that `0` is a real count while `"unsupported"` is not a number — the same
  distinction ADR-0070 draws, said once, for an API reader who will never open the ADR.
* Mirror both into `LoadCoach/docs/apps/loadcoach/` and verify with `cmp`. Commit the docs change
  separately from the code change.

### 2. Migration `0007` — the one piece of judgment

Two nullable integer columns on `jobs` and two on `job_attempts`. No backfill, no server default,
no data migration: an existing row genuinely has no value for these, and `NULL` is how this schema
already says "not reported" (`input_tokens` and `thinking_tokens` are nullable for the same
reason).

Things to get right rather than discover:

* **`check_parity` must match after upgrade on both dialects** — that is the test that catches a
  type mismatch between the model and the migration.
* **The downgrade path.** SQLite cannot drop a column with a plain `ALTER`; look at how the
  existing revisions handle their downgrades and follow that convention rather than inventing one.
  A downgrade that only works on PostgreSQL is a migration that fails in the one place it is most
  likely to be run.
* **Column ordering and naming** follow the existing rows; nothing else in either table is touched.
  Re-declaring a column an earlier revision created is drift.

### 3. Capture and persistence

`AttemptRecord` and `ExecutionOutcome` both gain `cache_write_tokens` and `cache_read_tokens`,
read through the existing `_count` helper — which already returns `None` rather than `0` for an
unsupported value, and is exactly right here. That covers both execution paths, because the
synchronous path (`execution.py`) and the queue worker (`worker.py`) build the same
`ExecutionOutcome`; add the two fields to every construction site and to both `values={…}` dicts
that write the job row and the attempt row.

Note that the job event stream carries `summary.as_json()`, so the new fields reach events for
free — additive, and worth a line in the handoff rather than a surprise at F1.

### 4. The wire

`ExecutionOutcome.as_json()`'s `usage` block and `job_document`'s `usage` block both gain the two
fields, rendering `"unsupported"` when the value is `None`, exactly as `thinking_tokens` does two
lines above. Two decisions to make explicitly and record:

* **Do not change `input_tokens`/`output_tokens`.** They render `null` today where ADR-0016 rule 4
  says `"unsupported"`. That inconsistency is real and predates this row; changing it would alter
  an existing field's type on a released 1.0 API, which is a break, and it is not in ADR-0070's
  scope. **Record it as a finding** for its own decision — it is exactly the kind of thing that
  should become a small ADR rather than a quiet fix in an unrelated session.
* **The attempts list in the job document** does not carry token counts at all today
  (`AttemptRecord.as_json()` omits them). ADR-0070 decision 7 asks for the *rows* and the job
  document's `usage`; extending the per-attempt JSON is neither required nor forbidden. Decide,
  say which, and say why — the defensible default is to leave the document's attempt entries as
  they are, since the rows exist for the record and the `usage` object is the contract.

### 5. The OpenAPI snapshot

`tests/contract/test_openapi_snapshot.py` compares `docs/openapi.json` against the live schema. The
job document is currently an untyped dict, so the snapshot may not move at all — **confirm that
rather than assume it**, and if any response model does change, regenerate with the file's own
`write()` helper rather than by hand.

### 6. Tests

* Migration up/down with `check_parity` on SQLite (locally) and PostgreSQL (CI); the PostgreSQL leg
  skips visibly here.
* A completed job whose provider reported cache classes: the values reach the `jobs` row, the
  `job_attempts` row and the `usage` object.
* A completed job whose provider left them `UNSUPPORTED`: `NULL` in both rows and `"unsupported"`
  in the JSON — never `0`, and never `null` in the new fields.
* A `0` is stored and rendered as `0` and is not confused with either of the above. This is the
  assertion that makes the whole ADR-0070 chain worth anything, so write it deliberately.
* Additive compatibility: the 1.0.0 response fields are all still present with their old types.

### 7. Gate and commit

The full gate green with the interpreter named. Commits on `main` — docs, migration + models,
capture + wire, tests — no version bump, no tag, no publish, no push.

## Before you finish — three closing duties

1. **Write `docs/history/C6_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands, saying plainly which legs skipped for want of PostgreSQL; the document
   amendments with the `cmp` output; the migration as written and how its downgrade behaves on
   SQLite; the two decisions from §4 (the `null` vs `"unsupported"` inconsistency you did **not**
   fix, and whether the attempts entries gained fields); whether the OpenAPI snapshot moved; the
   two stale pins from the preconditions; the commits made; and **"Before the next session"** — at
   minimum: push `main`, confirm CI green including `db-matrix`, and the reminder that this rides
   `1.1.0` at H2 alongside `2c7d740` rather than publishing now. Add a short note **for F1**, which
   is the first consumer: what the four classes look like on the wire before and after
   `modelrack 0.7.0` ships, so the harness's estimator is not written against the interim shape.
   **Never overwrite an existing root file** — the workspace root is not a git repository. If
   `docs/history/C6_HANDOFF.md` exists, write `C6_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what changed, what the gate said, what you decided where the ADR
   left an edge, and what is waiting on the operator. A few sentences.
3. **Prepare the commits.** Everything committed on `main`, working tree clean, nothing pushed,
   nothing tagged.

## Constraints and stop rules

* **Additive only.** No field removed, no type changed, no `/api/v2`, no version bump, no tag, no
  publish. If you find yourself wanting to change an existing field, that is a finding for the
  handoff.
* **Never fabricate a zero.** `NULL`/`"unsupported"` is what an unreported class looks like at this
  layer; `0` means the adapter said zero. LoadCoach does not decide which — ADR-0070 put that
  decision in the adapter, and re-deciding it here would put the same rule in two places.
* **No routing, scoring, pricing or cost arithmetic.** This row moves numbers from a provider
  response onto rows and onto the wire, and nothing else. LoadCoach does not price
  ([ADR-0030](docs/adr/0030-model-cost-and-pricing.md)); the ledger is PromptCadence's, at F1.
* **Do not touch ModelRack**, and do not install it editable to make a test pass.
* **Do not reflow the markdown you edit.** Amend the lines that change and leave the rest byte-for-
  byte, then prove it with `cmp` against the mirror.
* **Never weaken `.importlinter`** to make an import work.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` in this repo at the start and
  end of the session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/C6_HANDOFF.md`.
