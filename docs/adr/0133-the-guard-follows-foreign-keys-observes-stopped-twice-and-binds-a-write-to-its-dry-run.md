# ADR-0133 — The guard follows foreign keys, observes *stopped* twice, and binds a write to its dry run

**Status:** Accepted (2026-09-10)
**Amends:** [ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)
— its *Mechanics* and its never-writable list, additively and only in the stricter direction
(nothing ADR-0124 refuses becomes allowed), and one sentence: where the connection string is read.
**Amended by:** [ADR-0134](0134-event-logs-go-with-their-deleted-parent-freeweight-deletes-its-own-results-and-guarded-write-backups-expire.md)
— rule 1 no longer refuses a cascaded *delete* into an event log, and the second *Negative*
consequence (a model's runs) is answered by FreeWeight's own deletion API.
**Relates to:** [ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
rules 3 and 5, [ADR-0127](0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md)
rule 1 (the document, which carries a key's source and not its resolved default),
[ADR-0044](0044-a-state-change-and-its-event-are-one-write.md) (the event logs a cascade would
reach), [Database Standards §8](../standards/database-standards.md) (the preview; a cascade that
removes more than the preview stated is a defect), WeightRoomGym [spec](../apps/weightroom/spec.md)
§7.8 and §13.
**Found:** row W7, building the guard against the four fixture databases and the reference machine.

## Context

ADR-0124 decided the five conditions and the tables no condition makes writable. Building them
against the four applications' real schemas found five places where the record, read literally,
lets through a write its own reasons refuse, or names something that is not there.

1. **A foreign-key action is a write the statement never names.** FreeWeight declares
   `run_events.run_id → runs.id ON DELETE CASCADE`. `DELETE FROM runs WHERE …` names only `runs`,
   which ADR-0124 leaves writable, and deletes the run's events — an event log ADR-0124 locks
   because "a gap or an edit corrupts replay". The shape recurs in every application:
   `projects → stage_runs → stage_events` in IdeaPress, `plans → plan_approvals` in PromptCadence,
   `routing_decisions → routing_candidates` in LoadCoach. None of the four declares a trigger.
2. **A unit is not the only way an application runs.** `systemctl --user is-active` answers for
   the unit. An application started by hand in a terminal — the ordinary way to try a build on
   this machine — serves on its port, writes its database, and leaves its unit `inactive`.
3. **The schema document does not carry the effective database URL.** ADR-0127's document says
   where each key came from (`sources`); all four applications resolve an unset
   `storage.database_url` to a file under their data directory when they load, so the document's
   value for it is empty on the reference machine and its source is `default`.
   `<app> config show --json` prints the resolved value, and the console already reads it there
   for every Overview page (row W3).
4. **"Shown back" had nothing binding it.** A dry run shows a count; nothing in ADR-0124 ties the
   write the operator then confirms to that count, so a statement edited between the two, or a
   table that changed, runs under an approval given for something else.
5. **Condition 5 had no code.** Spec §13 names a `GUARD_*` code for conditions 1–4 and none for
   an audit row that cannot be written.

It also found that `freeweight db delete --model`, which ADR-0123 rule 5 and ADR-0124 cite as the
curated verb the guard's friction points the operator towards, does not exist in FreeWeight 1.2.

## Decision

1. **A table the statement reaches through a foreign-key action is written, and the lock applies
   to it.** Before the dry run the guard reads the database's own foreign keys on the read-only
   connection (both dialects) and follows every `ON DELETE` and `ON UPDATE` action that changes
   rows — `CASCADE`, `SET NULL`, `SET DEFAULT` — out of the tables the statement writes: a
   cascaded delete onward as a delete, a nulled or defaulted row onward as an update. A
   never-writable table reached that way refuses the statement with `GUARD_TABLE_LOCKED`, naming
   the table and the path (`runs → run_events`, `ON DELETE CASCADE`). The reached tables are shown
   beside the dry-run count with the change in their row counts — Database Standards §8's
   preview. The names the operator types (condition 4) stay the tables the statement names.
2. **The database engine's own catalog is never written.** `sqlite_*` and `pg_*` join ADR-0124's
   list as a ninth class. `sqlite_sequence` is what stops an `AUTOINCREMENT` id being reused, and
   row W6 found what a reused id does to a stream.
3. **Stopped is observed twice.** Condition 1 holds when the unit is `inactive` or `failed` — or
   absent, or the host has no systemd — **and** a connection to the application's configured
   port is refused. `failed` is systemd's word for a process that exited and will not be
   restarted; `activating`, auto-restart included, is not stopped. An unparseable address is not
   evidence of anything and fails the condition.
4. **The connection string is `<app> config show --json`'s `values.storage.database_url`** — the
   application's own effective value, printed by the application, never typed into WeightRoomGym.
   This replaces ADR-0124's "read from its configuration through ADR-0127's document".
5. **A write is bound to its dry run.** The dry run answers a `dry_run_id`: a digest of the
   application, the statement text, the count and the reached tables' changes. The write repeats
   the dry run first and refuses with `GUARD_DRY_RUN_FAILED` unless the digest matches, before any
   backup is taken; and if the statement's own count then differs from the one shown, its
   transaction is rolled back and the audit row completes as `failed`.
6. **Condition 5 fails as `GUARD_AUDIT_FAILED`:** when the `pending` row cannot be written the
   statement does not run. `GUARD_TABLE_LOCKED` and `GUARD_STATEMENT_REFUSED` carry
   `condition: null` — no changed fact satisfies them.

A write therefore runs in this order: the statement's kind and the lock (with the reach),
condition 4, condition 1, condition 3 repeated, condition 2, condition 5's `pending` row carrying
the backup path, the statement on its own connection, the row completed. Every refusal before the
`pending` row is still one audit row, outcome `refused`.

## Consequences

*Positive.* The never-writable list means what ADR-0124 says it means — tamper-evident by
construction — rather than "not named in a statement". The preview the operator confirms includes
what the database will do on the statement's behalf, which is the half of a cascade Database
Standards §8 says a preview must not hide.

*Negative.* `DELETE FROM runs` is refused in FreeWeight, `DELETE FROM projects` in IdeaPress and
`DELETE FROM plans` in PromptCadence, although ADR-0124's text leaves those tables writable. That
is ADR-0124's own reason applied, and it is the trigger ADR-0124 names — a guarded write found to
be needed routinely wants a curated verb in the owning application. ADR-0124's two examples of
wanted maintenance, a run's samples and a project's units, reach no locked table and stay
writable.

*Negative.* Until FreeWeight grows `db delete --model`, a model's runs cannot be removed from the
console at all: its samples and run tests can, its runs cascade into `run_events`. The console
lists the curated operations each application actually has, and says which one is missing.

*Neutral.* The port check can be wrong in one direction only: an unrelated process on the port
reads as *running* and refuses a write that would have been safe. A worker writing the database
without the server (`freeweight run start` in local mode) is invisible to both observations; the
backup is what covers it.

## Alternatives considered

* **Leave cascades to the dry run's count.** Rejected: SQLite's `changes()` and PostgreSQL's row
  count report only the rows the statement itself touched, so the count would show one run and
  delete three hundred events. SQLite's authorizer callback reports a `SET NULL` but not a
  cascaded delete, so it cannot stand in for the foreign keys either.
* **Require the operator to type the reached tables too.** Rejected: condition 4 is about the
  statement the operator wrote; the reached tables are the database's consequence of it, shown in
  the preview, and refused outright when locked.
* **Add resolved values to the ADR-0127 document.** A four-repository change for one consumer,
  when the verb that prints them already exists in all four.
* **Store the dry run server-side under an id.** A table and a sweep for what a digest proves
  without either; the id is not a credential (the session is), only a proof that the count shown
  is the count now.

## Revisit when

* **An application declares a trigger.** The guard follows foreign keys, not triggers; a trigger
  that writes a locked table needs this record's rule 1 extended first.
* **FreeWeight gains `db delete --model`** (or any application a curated delete): the console
  lists it first on the tables it covers, and the cascade refusals above get their answer.
* **ADR-0127's document gains resolved values:** rule 4 may return to the document.
