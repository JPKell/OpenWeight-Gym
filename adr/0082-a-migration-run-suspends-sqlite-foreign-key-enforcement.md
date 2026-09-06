# ADR-0082 — A migration run suspends SQLite foreign-key enforcement

**Status:** Accepted (2026-09-05)
**Amends:** [Database Standards §2](../standards/database-standards.md) (`foreign_keys=ON` on every
SQLite connection) — for the duration of a migration run only, and for no other connection.
**Relates to:** [ADR-0006](0006-sqlite-and-postgresql-only.md) (SQLite by default, PostgreSQL
supported), [WeightsDB spec](../packages/weightsdb/spec.md) (the migration runner and its backups).
**Source:** Row H2, gate D — found by a test that inserted a routing decision and its candidate,
migrated, and could not read the candidate back.

## Context

SQLite cannot add a constraint to an existing table. Alembic's batch mode emulates it: it creates a
new table with the wanted definition, copies the rows, **drops the old table** and renames the new
one into its place.

Every suite database enforces foreign keys ([Database Standards
§2](../standards/database-standards.md)), and enforcement makes that drop destructive in a way the
migration author never sees. `DROP TABLE parent` with `foreign_keys=ON` deletes every child row
whose foreign key declares `ON DELETE CASCADE`. LoadCoach's migration `0009` adds a foreign key to
`routing_decisions`, whose children are `routing_candidates` — the persisted explanations, which the
data model keeps **for ever** because the explainability promise depends on them. The upgrade
completed successfully, reported nothing, and left the table empty.

It was found only because a migration test seeded a parent and a child and read the child back
afterwards. Nothing about the migration, the runner's output or the parity check would have said a
word; on a real 1.0 database the first 1.1 startup would have deleted the entire routing history.

The obvious fix does not work. `PRAGMA foreign_keys` is a documented **no-op inside a transaction**,
and a migration runs inside one — so setting it through the SQLAlchemy connection succeeds, changes
nothing, and reports success. WeightsDB additionally puts the SQLite driver in autocommit and emits
`BEGIN IMMEDIATE` from SQLAlchemy's `begin` event, so *any* statement through that connection opens
a transaction first, including the pragma meant to run before one.

## Decision

**A migration run suspends SQLite foreign-key enforcement for its own connection, and restores it
when the run ends. Every other connection keeps `foreign_keys=ON`, unchanged.**

1. **Scope is the run, not the process.** The pragma is set in the migration environment before
   the migration transaction begins and restored in a `finally`, so a failed migration leaves
   enforcement on. No application connection is affected, and nothing outside a migration ever sees
   a database with foreign keys off.
2. **It is set through the raw driver cursor**, not through the SQLAlchemy connection, because the
   connection's own machinery opens a transaction first and the pragma is then a silent no-op. The
   mechanism is recorded here because "it looked like it worked" is the failure mode.
3. **PostgreSQL is untouched.** It adds a constraint with an `ALTER`, rebuilds nothing and cascades
   nothing, so there is no window to close.
4. **A migration that rebuilds a table restores what reflection loses.** Alembic recreates a
   rebuilt table's indexes from what it reflected, which drops index-column *direction*: LoadCoach's
   `0010` re-creates `(state, effective_priority DESC, created_at)` by hand, because without the
   `DESC` the hottest statement in the application sorts through a temp B-tree. A rebuild is not
   free, and what it costs is stated in the migration that pays it.
5. **A migration that can destroy rows proves it does not.** Any migration that rebuilds a table
   with children carries a test that seeds a parent and a child, migrates, and reads the child
   back. A parity check compares *schema*; only a row survives to prove data did.

## Alternatives considered

**Skip the foreign key on SQLite and create it only on PostgreSQL.** The first thing tried, and it
fails on its own terms: the parity check reflects the live schema and reports the missing constraint
as drift, so the two dialects would diverge permanently and every future parity run would carry a
known-good difference — the kind of exception that hides the next real one.

**Declare the column with no foreign key at all, and enforce the relationship in the ORM.** Cheaper,
and the application does write both sides. Rejected: the data model documents these as foreign keys,
an orphaned `adapter_id` would be undetectable, and "the application always writes it correctly" is
a claim that outlives whoever made it.

**Copy the children out and back around the rebuild.** Correct, and entirely local to the one
migration that needs it. Rejected as a pattern: it is bespoke per migration, it must be written
again for every future constraint on a parent table, and a half-applied version of it loses exactly
the rows it exists to save.

**Turn enforcement off permanently and rely on the application.** Rejected without hesitation:
enforcement is what makes a `SET NULL` mean anything and what catches the orphan a bug writes.

## Consequences

* Migration authors may add foreign keys to parent tables on SQLite without silently deleting
  children — which is the state everybody already assumed they were in.
* Every suite component using WeightsDB's runner inherits this the moment its own `env.py` adopts
  the same two lines. LoadCoach's does today; FreeWeight and IdeaPress will need it the first time
  they add a constraint to a table with children, and this record is what tells them why.
* A migration run is briefly a window in which a badly written migration could insert an orphan.
  That is accepted: a migration is reviewed code applying a known transformation, and the
  alternative is a runner that destroys data instead.
* [Database Standards §2](../standards/database-standards.md) keeps `foreign_keys=ON` as the rule;
  this is its one stated exception, bounded to the runner.

## Revisit when

SQLite gains real `ALTER TABLE ... ADD CONSTRAINT`, or alembic's batch mode learns to preserve
children across a parent rebuild. Either removes the need for the exception, and the pragma should
go with it rather than survive as a habit.
