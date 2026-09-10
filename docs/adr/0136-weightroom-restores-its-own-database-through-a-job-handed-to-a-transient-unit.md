# ADR-0136 — WeightRoomGym restores its own database through a job handed to a transient unit

**Status:** Accepted (2026-09-10)
**Relates to:** [ADR-0010](0010-queue-implementation.md) and [ADR-0029](0029-queue-mechanics.md)
(the queue this uses), [ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)
condition 1 (a database is replaced only with its writer stopped),
[ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
(the `systemd --user` units WeightRoomGym writes, its own among them).
**Source:** Row W8 shipped no restore route for WeightRoomGym's own database, because a request
cannot survive stopping the process that serves it (`history/handoffs/W8_HANDOFF.md` §2 item 6).
The operator decided on 2026-09-10 that row W9 designs it as a job kind — stop the unit, restore,
restart — rather than leaving it CLI-only (§6 of that handoff).

## Context

Every other application's restore is simple from the console: it is a request to *this* process
that stops a *different* one. WeightRoomGym's own restore is not, for three reasons found while
designing it:

1. **The worker runs inside the process being stopped.** The job queue is worked by a thread of
   the server (spec §7.10). A job that runs `systemctl --user stop weightroom.service` kills its
   own executor halfway through the restore it started.
2. **The restore replaces the database that holds the queue and the trail.** The job's own row and
   the audit rows written since the backup was taken are not in the backup. Restored naively, the
   console comes back with no record that a restore happened.
3. **The console is not always a unit.** On the reference machine it runs as `wr-gym serve` from a
   terminal (row W8's state, 2026-09-10); there is no unit for `systemctl` to stop or start.

## Decision

1. **`self_restore` is a job kind with one parameter, `file`.** It is enqueued only after a fresh
   re-authentication and with `weightroom` typed, and the file must resolve inside WeightRoomGym's
   own backups directory (`services/database.backup_directory`). SQLite only: WeightsDB's restore
   refuses PostgreSQL by name, and so does this.
2. **The worker does not restore; it hands off.** It checks that the process runs inside
   `weightroom.service` (its own cgroup, `/proc/self/cgroup`) and that `systemd-run` is on `PATH`,
   writes a receipt — the job's row and the source file — to `<data>/restores/<job>.json`, and
   launches `systemd-run --user --unit=wr-gym-restore-<job> --collect wr-gym db restore-self
   --receipt <file>`. A transient *service* unit is outside `weightroom.service`'s cgroup, so
   stopping the console does not stop it, and its output has a journal of its own. The job stays
   `running`; its lease is renewed until the process stops.
3. **The helper does the restore, in this order:** stop `weightroom.service`; take a
   `pre-restore-<job>` backup of the live database beside the others; restore the chosen file
   through WeightsDB (which verifies it opens, passes its integrity check and sits at a revision
   this build knows); migrate it to head; write the job's row, completed, and its `job.run` audit
   row into the restored database, naming the source file and the pre-restore backup; start
   `weightroom.service`. On a failure after the stop, the pre-restore backup goes back if the swap
   happened, the job is recorded failed in whichever database is live, and the unit is started
   regardless — a restore that fails never leaves the console down by choice.
4. **What was written after the backup is not merged.** A restore returns the database to a point
   in time, the trail included. The rows written between the backup and the restore survive in the
   pre-restore backup file, which the carried-forward audit row names; that file is the trail's
   continuity.
5. **Not under the unit, the job fails at once** and stops nothing, naming the terminal route:
   stop the console, `wr-gym db restore <file> --confirm`, start it again.

## Consequences

*Positive.* The console restores itself from the console, and the restored trail says that it did
and where the lost stretch of it went. A failed restore puts the database back and the console up.

*Negative.* The console is unavailable for the seconds the helper runs, and a page in flight sees
the connection drop. If the helper itself dies between the stop and the start, the console stays
down: the transient unit's journal (`journalctl --user -u wr-gym-restore-<job>`) says why, and
`systemctl --user start weightroom` is the fix.

*Negative.* The restore only works for a console run as its unit — the reference machine's
terminal-started console gets the refusal of rule 5 until it runs under `weightroom.service`.

*Neutral.* On restart the recovery pass finds the job terminal in the restored database and does
nothing. A job whose hand-off never happened (the launch failed) is failed by the worker before it
returns, and a restore job whose lease expires with no receipt consumed is failed as
`worker_lost`, never requeued: a second restore would discard what the first carried forward.

## Alternatives considered

* **A route that restores in-process.** WeightsDB's restore disposes the connection pool, so the
  file swap itself would work — but the telemetry sampler, the job worker, the chat runner and every
  request hold or reopen connections and write while it happens. Stopping the writer is the only
  way to know there is none, which is ADR-0124 condition 1 applied to the console itself. Rejected.
* **CLI-only, with the unit stopped by hand.** Row W8's answer; the operator rejected it.
* **`systemd-run --scope` from the worker.** A scope moves the helper out of the service's cgroup
  too, but the call blocks its caller until the helper exits — which is when the caller has already
  been stopped. A transient service detaches, and has its own journal.
* **Merging the post-backup rows into the restored database.** Which rows are wanted after a
  restore is the operator's question, not a merge rule's; a named file keeps every one of them and
  decides nothing.

## Revisit when

* WeightRoomGym runs on PostgreSQL in earnest: the restore becomes `pg_restore`, which WeightsDB
  deliberately does not perform.
* A second console process shares the database — the helper's stop would then have to stop both.
