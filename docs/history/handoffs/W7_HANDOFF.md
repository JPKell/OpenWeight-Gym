# W7 Handoff — WeightRoomGym Phase 7: the database viewer and the guard

**Row:** W7 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Opus 5 · xhigh, attended).
**Date:** 2026-09-10. **Kickoff:** [`w7-weightroom-p7-db-viewer-guard.prompt.md`](../prompts/w7-weightroom-p7-db-viewer-guard.prompt.md).
**Ships:** `wr-gym 0.7.0`, **prepared — not tagged, not pushed, not published.** One new record,
[ADR-0133](../../adr/0133-the-guard-follows-foreign-keys-observes-stopped-twice-and-binds-a-write-to-its-dry-run.md).
Built on `main` in `~/ai/suite/WeightRoom` (no worktree; no other session held the tree).

## 1. What was built, by commit

| Commit | Gate | What |
|---|---|---|
| `8d36848` | A | `domain/guard.py` — the five conditions as a checklist with per-condition verdicts, the never-writable tables as data, the SQL lexer (verb, tables named, tables written), the foreign-key reach, the `GUARD_*` refusals; ADR-0133; spec §13 gains `GUARD_AUDIT_FAILED`; 144 unit tests, 99 % of the module |
| `b6871ef` | B | `services/db_reader.py` — each application's effective URL from `config show --json` (cached 60 s), unpooled read-only engines on both dialects, the revision check, tables with counts and locks, the typed/sorted/filtered grid, the SQL console; `/database`, `/apps/{app}/database`, `/apps/{app}/database/{table}`; `db.query` audit rows; `db_revision`/`known` in `GET /apps` and `/system/status`; the Overview and the doctor moved onto the read-only reader; the SQLite tests over copies of the five fixture databases and a PostgreSQL leg |
| `3d1efe6` | C | `services/db_guard.py` (the guarded write in ADR-0133's order), `services/db_curated.py` (each application's own `db` verbs and the per-table operations), the guard and curated routes, the table page's guard dialog, the audit registry's eight new exercises, `audit.complete()`, the re-authentication restamp moved to `web/session.py`, api.md §3 / spec §7.8 / plan Phase 7 criterion 2 amended, CHANGELOG, README, `0.7.0` |
| `79bb9da` | — | Found by the demonstration's screenshots: grid and console cells kept to one line (rows were 114 px) |

**The gate**, local, Python **3.14.4** (`~/ai/suite/WeightRoom/.venv`, `.venv/bin/python -m pytest`):
`ruff format --check .` (155 files), `ruff check .` clean, `mypy src tests` clean (149 files,
strict), `lint-imports` **5 contracts kept**, `wr-gym config reference --check` matches,
`pytest -m "not live and not performance"` **1171 passed**, coverage **91 %** (floor 85 %),
`domain/guard.py` **99 %** (floor 95 %). **The db-matrix job's leg**
(`WEIGHTSDB_REQUIRE_POSTGRES=1 pytest -m "not live and not performance" tests/integration`) was
run locally against a throwaway `postgres:16` container: **317 passed**. The container is removed.

## 2. What the kickoff and the records got wrong, and where it went

**Read this section before anything in §3.** Five of these became [ADR-0133](../../adr/0133-the-guard-follows-foreign-keys-observes-stopped-twice-and-binds-a-write-to-its-dry-run.md);
it amends ADR-0124 additively and only in the stricter direction, and ADR-0124 now carries an
*Amended by* line.

1. **A foreign-key action is a write the statement never names.** `DELETE FROM runs` names only
   `runs` (writable by ADR-0124's letter) and cascades into `run_events` (locked). Every
   application has the shape: `projects → stage_runs → stage_events` in IdeaPress, `plans →
   plan_approvals` in PromptCadence. The guard now reflects the database's foreign keys and refuses
   a reach into a locked table, naming the path. **Consequence the operator should weigh:**
   `DELETE FROM runs` (FreeWeight), `DELETE FROM projects` (IdeaPress) and `DELETE FROM plans`
   (PromptCadence) are refused. ADR-0124's own two examples of wanted maintenance — a run's samples,
   a project's units — reach nothing locked and stay writable.
2. **`freeweight db delete --model` does not exist.** ADR-0123 rule 5, ADR-0124 and spec §7.3 all
   cite it; `freeweight db --help` lists `upgrade status backup restore vacuum` and nothing else.
   *Corrected after the operator's review (§8):* the deletion exists as FreeWeight's HTTP API
   (`POST /api/v1/database/delete-preview`, `DELETE /api/v1/database/results`, since its Phase 10);
   this row looked only at the CLI. ADR-0134 rule 2 makes that API the curated path, and the
   console now calls it.
3. **The schema document carries no resolved database URL.** All four applications leave
   `storage.database_url` unset and resolve it at load; their documents' `sources` say `default`
   and the value is empty. W4's handoff §10 said the connection strings "come from the schema
   documents"; they come from `<app> config show --json` (what W3's Overview already read). ADR-0133
   rule 4; spec §7.8 amended. `config show` is a 0.4 s process launch, hence the 60 s cache.
4. **Stopped needs the port too.** An application started by hand in a terminal leaves its unit
   `inactive`. Condition 1 is now unit ∈ {`inactive`, `failed`, `absent`, no systemd} **and** a
   refused connection to its `base_url`.
5. **"Shown back" had no binding, and condition 5 had no code.** A write presents the `dry_run_id`
   (a digest of app, text, count and the reached tables' changes) and is rolled back if its own
   counts differ; `GUARD_AUDIT_FAILED` is condition 5.
6. **Plan criterion 2's statement does not run on FreeWeight's schema** — `samples` has no
   `run_id`; a sample reaches its run through `run_tests`. The plan now names the statement that
   runs and the two names typed.
7. **Rows W3 and W4 opened the applications' databases read-write.** The Overview table and the
   doctor's revision rule used `weightsdb.create_engine_for`, which sets `journal_mode=WAL`,
   `secure_delete`, `synchronous` and creates the parent directory on every connection — writes
   against a file another application owns, against ADR-0124's first mechanic. Both now use the
   read-only reader.
8. **W5 left the db-matrix job red.** `tests/integration/test_migrations.py`'s parity filter knew
   FTS5's shadow tables but not `docs_index`'s PostgreSQL GIN index; it had never run against a
   server. Fixed in gate B.
9. **psycopg reads `%` as a placeholder** in a statement sent with an empty parameter list, so the
   console refused `LIKE 'x%'` on PostgreSQL. `exec_driver_sql(..., execution_options={"no_parameters": True})`
   in the console and in the guard. Found by the PostgreSQL leg; SQLite never showed it.

## 3. Decisions inside the implementation worth knowing

* **The statement is read by a lexer, not a parser** (no new dependency). It knows strings,
  quoted identifiers, comments, E-strings and dollar quotes, refuses what it cannot close and a
  nested block comment (the engines end one differently), and allows exactly one trailing `;`.
  The lock is applied to the tables written — five explicit patterns — plus the reflected reach.
  The wider "tables named" list only decides what is typed, and it is intersected with the tables
  that exist, so a misread alias never has to be typed.
* **The operator types the tables the statement names, not the tables it reaches.** The reach is
  the database's consequence: shown with its row-count changes (Database Standards §8's preview),
  and refused outright when locked.
* **No statement touches a running application's database, not even rolled back.** The dry run
  with the application up reports condition 1 red and counts nothing; `BEGIN IMMEDIATE` on a live
  SQLite file would have taken the writer's lock from under it.
* **Reads and the write use different engines, deliberately.** Reads: `sqlite://` with a `creator`
  opening `file:…?mode=ro` (the form `weightsdb.backup` uses), or PostgreSQL with
  `default_transaction_read_only` and `statement_timeout`/`lock_timeout` in the connect options;
  `NullPool`, disposed per request. The write: `weightsdb.create_engine_for` — `BEGIN IMMEDIATE` and
  `foreign_keys=ON`, the connection the owning application itself uses, so the reach predicted is
  the cascade that happens. SQLite gets a progress-handler deadline for the 30 s timeout on both.
* **The audit row's order keeps data-model §2's single update path.** Backup first, then the
  `pending` row *carrying* the backup path, then the statement, then `complete()`
  (`pending → ok|failed` on the same id, nothing else). A refusal before the pending row is one
  `refused` row; a failed backup is one `failed` row; a crash injected between the pending row and
  the statement leaves `pending` (a `BaseException` in the test — the handlers catch `Exception`).
* **Guarded-write backups were never rotated at W7** — *the operator's review set 90 days, from
  row W8 (ADR-0134 rule 3)* — (`<data>/backups/<app>/<utc>-guarded-write.sqlite3`,
  `.dump` on PostgreSQL, mode 0600): each is the undo of one raw write. `GET …/db/backups` lists
  them, filtering to `.sqlite3`/`.dump` — a read of a backup leaves `-shm`/`-wal` beside it, which
  the first test run listed.
* **A read-only open of a WAL database creates `-shm`/`-wal` beside it.** Tests work on copies
  (`tests.support.fixture_database`) and read committed fixtures `immutable=1`; a gate-A test
  had left sidecars in `tests/fixtures/databases/` (gitignored), removed.
* **Status codes:** `GUARD_APP_RUNNING` and `GUARD_DRY_RUN_FAILED` 409, `GUARD_TABLE_MISMATCH` and
  `GUARD_STATEMENT_REFUSED` 400, `GUARD_TABLE_LOCKED` 403, `GUARD_BACKUP_FAILED` and
  `GUARD_AUDIT_FAILED` 500, `SCHEMA_UNKNOWN` 409. `GUARD_TABLE_LOCKED`/`GUARD_STATEMENT_REFUSED`
  carry `condition: null`.
* **A curated verb's non-zero exit is `200 {"ok": false, "error": …}`**, in the application's own
  words — the application answered; the console did not fail. The verbs and flags per application
  are data in `services/db_curated.py`, read off each CLI's `--help` (IdeaPress has no `--json` on
  `backup`/`upgrade`; only FreeWeight has `vacuum`). A restore needs the unit stopped, the name
  typed and re-authentication.
* **New audit actions** `db.query` (every console statement, refused ones too) and `db.dry_run`
  (outcome `refused` when the application was running and nothing ran).
* **The audit-registry fixture exercises the guard on IdeaPress**, whose fake unit is absent and
  whose `base_url` is port 9: moving LoadCoach's `base_url` off 8766 broke the chat exercises, which
  mock LoadCoach there. No test depends on what runs on the developer's machine.
* **The re-authentication restamp** (`reauthenticated()`) moved to `web/session.py`, as W4's handoff
  asked when a second caller arrived.
* **MirrorWall's template environment has `auto_reload=False`**: a running console serves the old
  template after an edit. The demo's first "fix verified" probe was a false positive for exactly
  that reason; the throwaway had to be restarted.

## 4. The demonstration — plan Phase 7 criteria 1–3, on the reference machine

**Set-up, on copies.** A throwaway console on `https://127.0.0.1:8779` (XDG roots in the session
scratchpad, its own operator account and CA, the **real** `systemd --user` controller). Its
`[apps.freeweight]` and `[apps.loadcoach]` executables were two-line wrappers running the real
CLIs with `XDG_CONFIG_HOME` pointed at scratch configurations whose `storage.database_url` names a
copy of each database, taken with the SQLite backup API from a `mode=ro` source. Neither real
database was written; the console located each copy through the application's own
`config show --json`. The operator's own console (`weightroom.service`) was inactive throughout.

**Criterion 1 — browse `samples`; `SELECT count(*)`.** ✅ `GET …/db/tables`: revision `0009`
known; `samples` 268 rows, `writable: true`; `run_events` 327 rows, `writable: false`, reason
*never writable from WeightRoomGym (ADR-0124) — Event logs*. The grid: 268 rows, 3 pages, columns
typed (`id VARCHAR(26)` key, `ordinal INTEGER`, …). The console: `[[268]]` in 0.5 ms.

**Criterion 2 — with FreeWeight running, then stopped.** ✅ The statement:
`DELETE FROM samples WHERE run_test_id IN (SELECT id FROM run_tests WHERE run_id = '01M1ZRPWBDJ0J62Q59VRWBE6J7')`.

* Running: the dry run answered 200 with `row_count: null`, condition 1 **fail** — `unit active,
  port open` — and the reach listed (artifacts, calibration_samples SET NULL, criterion_scores,
  metric_values, tool_calls, judge_verdicts via criterion_scores). The write, re-authenticated:
  `409 GUARD_APP_RUNNING`, `condition: 1`, *freeweight is not stopped (unit active, port
  127.0.0.1:8765 open)*.
* FreeWeight had no run in flight (checked in its database, twice). It was stopped through the
  console (`POST /api/v1/apps/freeweight/stop` → `unit_state: inactive`, port 8765 closed) at
  10:11:52 UTC and started again the same way at 10:12:48 UTC (`active/running`, new PID, port open).
* Stopped, from the table page in a browser: **54 rows, rolled back**; each reached table's change
  (0); conditions 1 and 3 **pass**; typed `samples run_tests` and the password; **Written: 54 rows**.
* The run's samples on the copy afterwards: `[[0]]`. `ls -l …/backups/freeweight/`:
  `0o600  3497984  20260910T101223556124Z-guarded-write.sqlite3`.

The audit row (`GET /api/v1/audit?action=db.guarded_write`, the throwaway console's database;
paths are the session scratchpad):

```json
{
  "id": "01M25CVRD3BEGC6YDR998PNTNV",
  "at": "2026-09-10T10:12:23.556124+00:00",
  "actor": "operator", "operator": "operator", "app": "freeweight",
  "action": "db.guarded_write", "target": "samples, run_tests",
  "params": {
    "database_url": "sqlite:////tmp/claude-1000/…/w7demo/apps/data/freeweight-copy.sqlite3",
    "tables_typed": ["samples", "run_tests"],
    "reached": {"artifacts": 0, "calibration_samples": null, "criterion_scores": 0,
                "metric_values": 0, "tool_calls": 0, "judge_verdicts": 0},
    "dry_run_id": "bf8488f402d5c54b097796ce4df40904"
  },
  "outcome": "ok", "message": null, "security": true,
  "request_id": "01M25CVRA182ZV0D1BX86MDJ9P",
  "backup_path": "/tmp/claude-1000/…/w7demo/data/wr-gym/backups/freeweight/20260910T101223556124Z-guarded-write.sqlite3",
  "dry_run_count": 54, "actual_count": 54,
  "statement": "DELETE FROM samples WHERE run_test_id IN (SELECT id FROM run_tests WHERE run_id = '01M1ZRPWBDJ0J62Q59VRWBE6J7')"
}
```

The refusal while running is the row before it: `outcome: refused`, `params: {"code":
"GUARD_APP_RUNNING", "condition": 1, …}`, the statement, no backup.

**Criterion 3 — `UPDATE routing_decisions …`.** ✅ Against LoadCoach's copy:
`403 GUARD_TABLE_LOCKED`, *routing_decisions is never writable from WeightRoomGym (ADR-0124) —
Governance and decision records: approved and denied alike are the record; an edited record is not
a record.* And ADR-0133 rule 1 on the same machine: `DELETE FROM runs WHERE id = '…'` in FreeWeight's
copy → `403 GUARD_TABLE_LOCKED` through `runs → run_events`.

**Screenshots**, outside git as W6's are: `/home/jpk/ai/evidence/W7/` — `w7-1-freeweight-database.png`
(own operations, the tables with locks, the console), `w7-2-samples-grid.png` (before the one-line
fix), `w7-2b-samples-grid-nowrap.png` (after), `w7-3-guard-running.png`,
`w7-4-guard-dry-run-stopped.png`, `w7-5-guard-written.png`.

**Against fixtures only, not the reference machine:** PostgreSQL (the reference machine has none;
the local `postgres:16` leg ran the reader, the reach, the dry run and the write — with the
`pg_dump` backup replaced by a stand-in, since WeightsDB's own tests own `pg_dump`); an unknown
revision (`loadcoach-unknown-9999`); the curated verbs (a fake executable — no application's real
`db backup|upgrade|restore` was run by this row).

## 5. What is deliberately not here

* **`freeweight db delete --model`.** A FreeWeight feature with its own preview and cascade rules
  (Database Standards §8), not the console's to invent — see §6.
* **Triggers.** The guard follows foreign keys, not triggers; no application declares one. ADR-0133
  names it as the revisit trigger.
* **Row edit and row delete buttons.** A raw write is a statement typed into the guard; a row
  delete is one line of it. ADR-0124 covers all three; the page offers the statement.
* **A `wr-gym` CLI for the guard.** The spec names none.
* **The backups and migrations pages** are W8's; W7's curated routes are the calls they will make.
* **Spec §15's budgets** (a 100-row table page ≤ 150 ms; a guarded write ≤ 2 s excluding the
  backup) are not asserted as performance tests — W10. The demonstration's console query took
  0.5 ms.

## 6. For the operator

1. **Nothing pushed, tagged or published.** Four commits on `main` (`8d36848`, `b6871ef`,
   `3d1efe6`, `79bb9da`) plus this handoff's docs commit. Tags held until the W arc ends.
2. **ADR-0133 wants your review**, especially rule 1's consequence (§2 item 1) — it is the stricter
   reading of ADR-0124 and a superseding record could loosen it.
3. **Decide whether FreeWeight gets `db delete --model`** (a WS-style row), or whether ADR-0123 and
   ADR-0124's citation of it should be corrected by record instead.
4. **FreeWeight was stopped for about a minute** (10:11:52–10:12:48 UTC) by the demonstration,
   with no run in flight, and is running again.
5. **CI's db-matrix job** had been red since W5; gate B fixes it (not yet seen on GitHub, nothing is
   pushed).
6. **Mirror drift that predates this row:** `FreeWeight/scripts/sync_docs.py --check` reports seven
   stale FreeWeight mirrors (`api`, `benchmark-catalog`, `data-model`, `development-plan`, `risks`,
   `spec`, `subjective-goals`); W7 edited none of their canonical files. The README edit here was
   re-copied by `docs/scripts/sync_component_docs.py`, whose `--check` is clean.
7. **WR-β** (weightroom-work.md §5) now has every row done — WS1–WS4, W4, W5, W6, W7 — and spec §20
   #3 (a guarded write end to end) and #8 (an unknown revision degrading by name) are demonstrated
   above, #8 against the fixture. Declaring the milestone is yours.

## 7. Open for later rows

* **W8** builds the backups and migrations pages over `…/db/status|backup|upgrade|restore|backups`.
* **W10**: spec §15's database budgets; the OpenAPI snapshot now includes eleven database routes;
  the security suite's §14 rows for the guard are here already (`tests/unit/test_guard_domain.py`,
  `tests/integration/test_db_guard.py`, the audit registry).
* **Any row that migrates an application** owes `known_revisions` a row and
  `tests/fixtures/databases/` a regenerated file (its README says how); the guard refuses an
  unknown revision before it reads a table.

## 8. After the operator's review (same day)

The operator was interviewed over §6 on 2026-09-10; the answers that bind code are
[ADR-0134](../../adr/0134-event-logs-go-with-their-deleted-parent-freeweight-deletes-its-own-results-and-guarded-write-backups-expire.md).
Built on `main` in `0.7.0`, which is still unreleased.

1. **ADR-0133 rule 1 loosened for one case** (§6 item 2): a cascaded delete may remove an event
   log's rows. `DELETE FROM runs` in FreeWeight passes the lock; `DELETE FROM projects` (IdeaPress,
   through `stage_runs`) and `DELETE FROM plans` (PromptCadence, through `plan_approvals`) stay
   refused. A cascade that edits an event row still refuses, and `reach` now reports a table by the
   path that edits it when another path only deletes from it.
2. **FreeWeight's deletion is its API, and the console calls it** (§6 item 3). The interview first
   chose a new `freeweight db delete --model` verb; looking for where it would go found
   `POST /api/v1/database/delete-preview` and `DELETE /api/v1/database/results` (FreeWeight Phase
   10), and the operator chose the API. `services/db_curated.delete_results`;
   `POST /api/v1/apps/{app}/db/delete-results` (the preview without `token`; with it, the selector
   typed and a fresh re-authentication); a *Delete stored results* section on FreeWeight's database
   page, which the four tables' operations link to. Each call is one `db.curated` row; the deletion's
   is `security` and carries the run and row counts and FreeWeight's backup path. No FreeWeight
   release.
3. **Guarded-write backups expire after 90 days** (`0` for never). Built at W8; its kickoff says so.
4. **WR-β waits for a pushed `main` and a green db-matrix job on GitHub** (§6 items 5 and 7); the
   milestone map says so.
5. **The mirror-rule conflict waits for W10** (§6 item 6). The seven FreeWeight mirrors are
   `cmp`-identical to the canonical files; `sync_docs.py` turns links that leave FreeWeight's copy
   into plain text, so exact copies report stale. W10's kickoff carries it.

**Found while gating it:** `services/telemetry.history_rows` read `datetime.now(UTC)` while its tests
wrote samples at a fixed `2026-09-09T12:00Z` and asked for the last 24 hours, so three telemetry
tests began failing at 12:00 UTC on 2026-09-10 — a time bomb from row W3, not this change. The clock
is injected now (`now=`, and `now_of(request)` in both routes).

**The gate**, Python 3.14.4, the invocations of §1: ruff format and check clean, mypy clean (149
files), 5 contracts kept, the configuration reference matches, **1176 passed**, coverage **91 %**,
`domain/guard.py` **99 %**. The PostgreSQL leg against a throwaway `postgres:16`: **318 passed**;
the container is removed.

**Not demonstrated on the reference machine.** FreeWeight's deletion ran against a mocked FreeWeight
only (the route test and the audit registry); the loosened reach ran against the fixture copy and
the PostgreSQL leg. Showing it on the machine needs a FreeWeight serving a copy of its database, as
§4's wrappers did for the CLI.
