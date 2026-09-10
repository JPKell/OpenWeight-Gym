# ADR-0134 — Event logs go with their deleted parent, FreeWeight deletes its own results, and guarded-write backups expire

**Status:** Accepted (2026-09-10)
**Amends:** [ADR-0133](0133-the-guard-follows-foreign-keys-observes-stopped-twice-and-binds-a-write-to-its-dry-run.md)
rule 1 — in the looser direction, for one class and one action only — and corrects the curated verb
[ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 5 and
[ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md) cite.
**Relates to:** [ADR-0044](0044-a-state-change-and-its-event-are-one-write.md) (a state change and
its event are one write), [Database Standards §7–§8](../standards/database-standards.md),
WeightRoomGym [spec](../apps/weightroom/spec.md) §7.8 and §7.9, FreeWeight
[spec](../apps/freeweight/spec.md) §7.3's deletion by model, `history/handoffs/W7_HANDOFF.md` §2.
**Found:** the operator's review of row W7, 2026-09-10 (an interview over the handoff's §6).

## Context

Row W7 built ADR-0133 rule 1: a table a statement reaches through a foreign-key action is written,
and a never-writable table reached that way refuses the statement. On the four applications'
schemas that refuses `DELETE FROM runs` in FreeWeight (`runs → run_events`), `DELETE FROM projects`
in IdeaPress (`projects → stage_runs`) and `DELETE FROM plans` in PromptCadence
(`plans → plan_approvals`). The review found three things the record did not weigh.

1. **ADR-0124 locks event logs for replay:** "each is replayed over SSE by sequence; a gap or an
   edit corrupts replay". A cascade that removes a run's *whole* event stream together with the
   run leaves no stream to replay — no gap inside a stream that survives, and no edited event.
   FreeWeight's own `delete_results` removes `run_events` with the run for exactly that reason. The
   lock was refusing, from outside, what the owning application itself does.
2. **Each event log has one foreign key**, to its subject, `ON DELETE CASCADE` and no update action
   (`run_events → runs`, `job_events → jobs`, `stage_events → stage_runs`, `events → trajectories`,
   read from the four fixture databases at row W7). No schema today nulls or rewrites an event row
   through a key.
3. **`freeweight db delete --model` does not exist, and a curated deletion does.** W7 checked
   FreeWeight's CLI and stopped. FreeWeight's HTTP API has had `POST /api/v1/database/delete-preview`
   and `DELETE /api/v1/database/results` since its Phase 10: scopes `run`, `model`, `suite`,
   `before` and `all`, a preview whose token the deletion must present (and which a changed database
   invalidates), an automatic backup at 1 000 rows or more, and no model, machine or calibration row
   ever touched. W7's handoff §2 item 2 ("a model's runs cannot be removed from the console at all")
   was wrong about the API.

It also recorded, in W7's handoff §3, that a guarded write's backup is never rotated — an
implementation choice, not a decision, and one whose disk cost grows with every raw write.

## Decision

1. **A cascaded delete may remove an event log's rows.** A reached table in ADR-0124's *Event logs*
   class whose action is `ON DELETE CASCADE` does not refuse the statement. Everything else about
   event logs stands: a statement that names one is refused; a reach that *edits* one — `SET NULL`,
   `SET DEFAULT`, any `ON UPDATE` action — is refused with its path; and a table a cascade deletes
   from and another path edits is reported by the edit, so an edit is never hidden behind a delete.
   The reached event log is shown in the dry run with its change in rows and is not typed (ADR-0133
   rule 1's typing rule is unchanged). Every other class is unchanged, so `DELETE FROM projects`
   (queue state) and `DELETE FROM plans` (a decision record) stay refused, and LoadCoach's `jobs`
   and PromptCadence's `trajectories` are themselves locked. In practice this rule opens FreeWeight's
   `runs`.
2. **The curated deletion of FreeWeight's results is FreeWeight's own API**, and the console calls
   it rather than a CLI verb: FreeWeight's preview is shown, the selector is typed (`all` for scope
   `all`), the session is re-authenticated, and the deletion is sent with the preview's token. The
   preview and the deletion each leave one `db.curated` audit row, the deletion marked `security`.
   The application runs throughout — FreeWeight is the writer of its own database, so this is not a
   raw write and ADR-0124's conditions do not apply. It is listed before the guard on `runs`,
   `run_tests`, `samples` and `metric_values` (ADR-0123 rule 5). **`freeweight db delete --model` is
   not built;** where ADR-0123, ADR-0124 and WeightRoomGym's spec name it, read this API.
3. **Guarded-write backups expire.** From row W8, WeightRoomGym removes a guarded-write backup older
   than a configured age, **90 days by default**; `0` keeps them for ever. The audit row keeps the
   backup's path whether or not the file survives. This replaces "never rotated".

## Consequences

*Positive.* A run and its events leave together, the way the owning application removes them.
Deleting a model's measurements from the console is FreeWeight's own preview, token and backup, not
a statement typed into the guard.

*Negative.* The guard and FreeWeight's API now both delete runs. The API is listed first; a raw
`DELETE FROM runs` with the wrong `WHERE` removes event streams as well as runs, and the guard's
backup is what undoes it — for 90 days.

*Negative.* A raw write discovered to be wrong after the retention age has no backup left.

*Neutral.* Rule 1's refusal of an edited event row guards a key no application declares today. It
costs nothing until one does, and it is the part of ADR-0124's reason that still binds.

## Alternatives considered

* **Keep ADR-0133 rule 1 strict** — the W7 reading. Rejected by the operator: it refused the one
  cascade the owning application performs itself, and left `DELETE FROM runs` to a curated verb
  that turned out to be an API the console was not calling.
* **Allow any reach into a locked table once its name is typed.** Rejected: "never writable"
  would become "writable by cascade" for queue state, decision records and money.
* **Require the reached event log to be typed too.** Rejected: ADR-0133 rejected typing reached
  tables, for the same reason — the reach is the database's consequence, shown in the preview.
* **Build `freeweight db delete --model` and call it.** Chosen at first in the review, withdrawn when
  the API was found: a second surface over the same service, a FreeWeight release, and the console
  would still need the preview's token handed across a process boundary.
* **Keep the newest N backups per application.** Rejected: bounded disk, but an older write loses its
  undo according to how busy the application was since, not how old the write is.

## Revisit when

* **An event log gains a second foreign key or a trigger.** Rule 1's edit refusal starts to bind;
  check that the reach still reports it.
* **An operator at the terminal wants the deletion without the console.** That is a FreeWeight CLI
  verb over the same service, not a change to this record.
* **The backups directory's size is a problem at 90 days.** The age is configuration; the rule
  stands.
