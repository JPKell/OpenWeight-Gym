# Kickoff — W7: WeightRoomGym Phase 7 — database viewer and the guard

**Row:** W7 (Opus 5 · xhigh · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W4.
**Ships:** `wr-gym 0.7.0` prepared: every application's database readable; a raw write
only under the five conditions; curated operations first.
**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** **ADR-0124 in full, twice** — the five conditions, the mechanics, the
never-writable table; ADR-0123 rules 2–3 and 5; [`spec.md`](../../apps/weightroom/spec.md) §7.8, §11
contracts 3–4, §13 (`GUARD_*`, `SCHEMA_UNKNOWN`), §14; [`api.md`](../../apps/weightroom/api.md) §3;
[`data-model.md`](../../apps/weightroom/data-model.md) §4 (what is read where) and the `audit_log`
columns; [`development-plan.md`](../../apps/weightroom/development-plan.md) Phase 7;
`standards/database-standards.md` §1, §6, §8; `packages/weightsdb/spec.md` (`backup`,
`session_scope(read_only=…)`, the SQLite `mode=ro` URI form its own `backup.py` uses);
`history/handoffs/W4_HANDOFF.md` (the connection strings come from the schema documents).

## Decisions already taken — do not reopen

* Every connection to another application's database is **read-only**; a guarded write opens
  its own connection for one statement and closes it (ADR-0124 mechanics).
* The five conditions, in order: the unit is inactive (checked, not attested); a backup through
  `weightsdb.backup` into WeightRoomGym's `<data>/backups/<app>/` with its path on the audit row
  before the statement; a rolled-back dry run with its count shown beside the statement; every
  table in the statement typed exactly; the audit row `pending` before and completed after.
* One DML statement; DDL, `PRAGMA`, `VACUUM`, multi-statement refused by name; 30 s timeout;
  the console's `SELECT`s capped at 10 000 rows.
* The never-writable list is ADR-0124's table, **as data** in `domain/guard.py`, refused with
  the table named and the ADR cited; a test compares it against each fixture database's tables.
* An unknown `alembic_version` degrades that application's database pages by name
  (ADR-0123 rule 3); the fixture databases sit at the revisions `known_revisions` seeds.
* Curated operations call the owning application (`db backup|status|upgrade|restore`,
  FreeWeight's `db delete --model`, retention settings) and are listed first on every table that
  has one.

## Gates

**Gate A — the guard, pure.** `domain/guard.py`: the checklist with per-condition verdicts,
statement classification, table extraction, the never-writable data; unit tests failing each
condition alone; no I/O in the module (the domain-purity contract). Commit.

**Gate B — the reader.** `services/db_reader.py`: read-only connections both dialects from each
application's effective URL, the revision check, tables with counts and `writable`/`reason`, the
grid (page, sort, filter, typed columns), the SQL console; the four fixture databases in
`tests/fixtures/databases/` at known revisions plus one at an unknown revision; the PostgreSQL leg
in the db-matrix job. Commit.

**Gate C — the guard, wired.** `services/db_guard.py`: the unit check through W2's controller,
the backup, the dry run, the typed names, the audit row's two writes, the statement on its own
connection; `POST …/db/write/dry-run` and `…/db/write`; a crash injected between the `pending`
row and the statement leaves the pending row; the curated operations wired per table; the pages
with the guard dialog; `CHANGELOG.md`; `0.7.0`. Commit.

## Demonstrate

Plan Phase 7 criteria 1–3 on the reference machine, on a **copy** of FreeWeight's database
pointed at by a scratch FreeWeight configuration (never the operator's real database for the
demonstration): the refusal while running, the full guarded delete once stopped with the backup
file listed, and `UPDATE routing_decisions …` refused by name. Paste the audit row.

## Finish line

Gate green, coverage held (95 % on `domain/`), one commit per gate,
`docs/history/handoffs/W7_HANDOFF.md`, the row marked done. Never overnight; reviewed the same day.
