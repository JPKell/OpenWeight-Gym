# ADR-0124 — A raw write into another application's database passes a five-part guard, and some tables are never written

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 5
(the exception this record prices), [Database Standards §1 and §8](../standards/database-standards.md)
(ownership; preview, confirm, backup, transaction), [ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md)
(the mounted tables this record names), [ADR-0054](0054-commissioner-records-egress-it-does-not-enforce-it.md)
(the append-only decision ledger), [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md)
(intents are never edited), [ADR-0044](0044-a-state-change-and-its-event-are-one-write.md) (an event
row is the state change's witness), [ADR-0017](0017-benchmark-confidence-and-freshness.md) and
[ADR-0023](0023-runtime-profile-resolution.md) (what is hashed into a measurement subject).
**Source:** the operator interview of 2026-09-09, decision D3; the [kickoff](../history/w0-weightroom-phase-0.prompt.md) §3.

## Context

WeightRoomGym reads every application's database ([ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
rule 2). A read is safe by construction: a `SELECT` through a read-only connection cannot corrupt
a schema, break a foreign key, or race a running application's writer. A write is none of those
things. The applications are built on the assumption — held by every migration, every lease
sweep, every cascade — that **they** are the only writer, and an edit made behind a running
application's back is the one class of failure its tests never contemplated.

The operator still wants the capability, and for reasons that survive scrutiny: a row that
retention will not reach, a stuck lease after a crash the recovery pass misread, a misspelled
project name, a test run that should not be in the history. Each application already offers a
curated answer to some of these (`freeweight db delete --model`, retention settings, `queue
drain`), and none of them offers a general one.

The question is therefore not *whether* WeightRoomGym may write, but under what conditions a write
is as safe as the operator opening `sqlite3` by hand with a backup beside them — and which tables
no condition makes safe.

## Decision

**A curated, application-owned operation is always offered first. A raw write — a SQL statement,
a row edit, a row delete — is executed only when all five conditions below hold, and a named set
of tables is never written from WeightRoomGym at all.**

### The five conditions

1. **The owning application is stopped.** WeightRoomGym asks `systemctl --user is-active
   <app>.service` and, for an application that has no unit, checks the port; a checkbox saying
   "I stopped it" is not evidence. No application in the suite has a read-only serving mode
   today, so *stopped* is the only state this rule accepts; if one gains such a mode, it is
   added here by a superseding record, not assumed.
2. **An automatic backup of that database was taken first**, through `weightsdb.backup` (the
   SQLite backup API or `pg_dump`), into WeightRoomGym's own data root at
   `<data>/backups/<app>/<utc timestamp>-guarded-write.sqlite3` (or `.dump`), mode `0600`, and
   the path is written on the audit row before the statement runs. A backup that fails aborts
   the write.
3. **A dry run reported the affected row count, and the statement was shown back.** The
   statement runs inside a transaction that is rolled back, and the count SQLite or PostgreSQL
   reports is displayed beside the statement text, verbatim. A dry run that errors is the
   error, not a warning.
4. **The operator typed the table name.** For a statement that touches more than one table, every
   table. The name must match exactly; a typed name that is not in the statement refuses.
5. **An `audit_log` row in WeightRoomGym's own database records** who (the operator account),
   when, which application and database URL (redacted of any credential), the statement, the
   dry-run count, the actual count, the backup path, and the outcome. The audit row is written
   with the outcome *pending* before the statement and updated after, so a crash mid-write leaves
   a row that says a write was attempted.

### Mechanics that make the conditions mean what they say

* **Read is the default mode.** Every connection WeightRoomGym opens to another application's
  database is read-only — `?mode=ro` for SQLite, `default_transaction_read_only = on` for
  PostgreSQL — and a guarded write opens a **separate**, short-lived read-write connection for
  the one statement, closed afterwards. There is no long-lived writable handle to reach for.
* **One statement per guarded write.** No scripts, no `;`-separated batches. A second statement
  is a second guard.
* **DML only.** `CREATE`, `ALTER`, `DROP`, `PRAGMA` and `VACUUM` are refused by name: the schema
  is the owning application's migration history, and a hand-edited schema is a database that
  application can no longer migrate. Vacuum and integrity checks are offered as curated
  operations through the owning application's `db` verbs.
* **A statement timeout** (30 s, `busy_timeout` / `statement_timeout`) so a guarded write cannot
  hold a lock indefinitely.
* **The connection string is the application's own effective `storage.database_url`**, read from
  its configuration through [ADR-0127](0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md)'s
  document. It is never typed into WeightRoomGym, so there is no second place for it to be wrong.

### Tables that are never written from WeightRoomGym

By name, per application. A curated operation of the owning application may touch them; a raw
write from WeightRoomGym is refused with the table named and this record cited.

| Class | Why never | FreeWeight | LoadCoach | IdeaPress | PromptCadence |
|---|---|---|---|---|---|
| Migration state | The application's migration history owns it | `alembic_version` | `alembic_version` | `alembic_version` | `alembic_version` |
| Credentials | `token create`/`revoke` are the only writers; a hand-inserted hash is an unaudited credential | `api_tokens` | `api_tokens` | `api_tokens` | `api_tokens` |
| Runtime settings rows | The application's `PUT /settings` is the audited path ([ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)); WeightRoomGym uses it | `settings` | `settings` | `settings` | `settings` |
| Subject identity, hashed | A row hashed into a fingerprint or subject ([ADR-0017](0017-benchmark-confidence-and-freshness.md), [ADR-0023](0023-runtime-profile-resolution.md), [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md)) that is edited becomes a lie about every result that cites it | `machines`, `models`, `model_descriptors`, `runtime_profiles`, `adapters` | `models`, `runtime_profiles`, `adapters` | — | — |
| Queue and lease state | The worker's recovery pass reasons about these rows; a hand edit is a state the state machine never produced | — | `jobs`, `job_attempts`, `residency` | `stage_runs` | `trajectories`, `threads`, `turns` |
| Governance and decision records | Approved and denied alike are the record ([ADR-0054](0054-commissioner-records-egress-it-does-not-enforce-it.md), [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md), [ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md)); an edited record is not a record | — | `routing_decisions`, `routing_candidates` | `egress_decisions` (mounted) | `execution_intents`, `plan_approvals`, `approval_requests`, `deviations`, `egress_decisions` (mounted) |
| Money | Store usage, derive cost; the ledger is append-only ([ADR-0030](0030-model-cost-and-pricing.md), [ADR-0069](0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md)) | — | — | `ledger_*` (mounted) | `ledger_*` (mounted) |
| Event logs | Each is replayed over SSE by sequence ([ADR-0044](0044-a-state-change-and-its-event-are-one-write.md)); a gap or an edit corrupts replay | `run_events` | `job_events` | `stage_events` | `events` |

Everything else — samples, metric values, feedback, reliability statistics, projects, units,
drafts, explanation caches, compactions, tool-call records — is writable under the five
conditions. Deleting a run's samples or a project's units is exactly the sort of maintenance the
operator asked for; rewriting a routing decision is exactly the sort no maintenance justifies.

## Consequences

*Positive.* The operator can fix a database from the console with the same safety a careful
person has at a shell — backup, dry run, look, confirm — and better attribution, because the shell
keeps no audit log. The never-writable list makes the suite's evidence, governance and money
records tamper-evident by construction: WeightRoomGym cannot alter them, and anything else that did
would be outside the audited path.

*Negative.* The guard is slow on purpose: stop the application, take a backup, run twice, type
a name. An operator who wants to clear ten thousand rows of test samples will feel every step.
That is the intended friction; a faster path belongs in the owning application as a curated
verb, which is where `freeweight db delete --model` came from.

*Negative.* Condition 1 makes a write impossible while an application serves, so an emergency
edit to a running LoadCoach is not a thing WeightRoomGym offers. It is also not a thing the suite's
data model makes safe, which is why.

*Neutral.* The mounted tables (`ledger_*`, `egress_decisions`) are named twice, once per
mounting application, because each application's copy is its own data ([ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md)).

## Alternatives considered

* **No raw writes at all — curated operations only.** The cleanest rule, and rejected by the
  operator: the curated set is finite and the things that go wrong are not. The guard is what
  makes the general capability acceptable.
* **A checkbox attesting the application is stopped.** Rejected: the guard checks facts, not
  assertions; `systemctl` answers the question and a checkbox does not.
* **A read-only serving mode in each application**, so a write could happen under a running
  server. Rejected for 1.0: it is four features in four repositories to save the operator a
  restart, and the applications' lease sweeps and retention timers would still be writers.
* **Allow schema statements with an extra confirmation.** Rejected: there is no confirmation
  that makes an application able to migrate a table it did not shape.
* **Permit edits to `settings` rows directly.** Rejected: the owning application's `PUT
  /settings` refuses security keys by name and applies bounds; a direct row edit would bypass
  both, and it is one HTTP call away.

## Revisit when

* **An application gains a read-only serving mode.** Condition 1 gains a second acceptable state,
  by a record that names which application and how the mode is verified.
* **The audit log needs to leave the machine.** Today it is a table; an operator who wants it
  shipped elsewhere is asking for the outbound channel [spec §7](../apps/weightroom/spec.md)'s
  alerts also decline to have.
* **A guarded write is found to be routine** for some table. That is the trigger to build the
  curated verb in the owning application and take the table off the raw path.
