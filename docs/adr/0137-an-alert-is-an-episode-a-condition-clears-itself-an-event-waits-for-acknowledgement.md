# ADR-0137 — An alert is an episode: a condition clears itself, an event waits for its acknowledgement

**Status:** Accepted (2026-09-10)
**Relates to:** [ADR-0016](0016-unavailable-is-not-zero.md) (a reading that could not look is not
a reading that found nothing), [ADR-0119](0119-model-servers-run-under-a-host-memory-cap.md) (the
kill the `memory_cap` source matches), [ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
(the units `app_down` reads).
**Source:** Row W9, building spec §7.10's alerts. The spec names the five sources, "at most one
open alert per subject", "acknowledge closes it" and "history keeps every alert"; three facts found
while building them are not answered there.

## Context

1. **Two of the words do not fit one of the sources each.** "Acknowledge closes it" is right for a
   memory-cap kill — a thing that happened — and wrong for a GPU that is still at 91 °C: closed, the
   next evaluation thirty seconds later finds it hot again and opens a second alert, and a third,
   for as long as it stays hot. And the reverse: a condition alert closes when the condition goes
   away, but nothing in a later journal read says a kill un-happened, so a kill alert that closed
   on "no new line" would leave the banner before the operator could see it (Phase 9 criterion 2
   asks for the banner to show it and then be acknowledged).
2. **"An application unit inactive" is an alert on every stopped application.** No unit is enabled
   at boot on the reference machine (operator, 2026-09-10) and the operator stops applications on
   purpose; the console's own status pill already calls *stopped* neutral and only *failed* a
   problem (`web/rendering.py`, row W3). An inactive unit is a choice, not an outage.
3. **"Evaluated by the same worker" puts alerts behind the queue.** The job worker spends up to
   twelve hours inside one FreeWeight run — exactly when a memory cap is most likely to fire.

## Decision

1. **An alert is an episode of one source on one subject.** At most one episode per
   `(source, subject)` is *active* (not closed), held by a partial unique index as well as by the
   evaluator. The banner shows the active episodes nobody has acknowledged.
2. **Condition sources** — `app_down`, `gpu_thermal`, `budget_ceiling`, `breaker_open` — open an
   episode when the subject becomes wrong, keep it (updating `last_seen_at` and `detail`) while it
   stays wrong, and **clear** it — closed, with a `cleared` history row — when a reading that covers
   the subject finds it right. Acknowledging one records who and when and hides it from the banner;
   the episode stays active until it clears, so a condition that persists opens nothing new.
3. **Event sources** — `memory_cap` — open an episode on a matching journal line, record each
   further line about the same subject as a `seen` history row, and **close only when
   acknowledged**. A kill after that opens a new episode.
4. **A reading that could not look clears nothing.** No `systemctl`, LoadCoach not answering, no
   GPU temperature, a ledger that could not be read: the reading covers no subject, and every
   active episode it would have judged stays as it was (ADR-0016).
5. **`app_down` fires on a unit that is `failed` or restarting itself (`auto-restart`), or on one
   that has been `active` for a minute whose `/api/v1/health` does not answer `200`.** An inactive
   unit is not down; an application not installed is not watched.
6. **History records what changed**: `opened`, `acknowledged`, `cleared`, and `seen` for an event
   source's further lines. A condition that stays true writes its `last_seen_at` and `detail` on the
   alert, not a history row every thirty seconds — "history kept for ever" is then a record of
   episodes, not a sample log.
7. **The evaluator is its own thread**, every `[alerts] interval_seconds`, independent of the job
   worker. It never sends anything anywhere (spec §2, §3).

## Consequences

*Positive.* The banner says a thing once, keeps saying it until the operator has seen it or it is
over, and does not repeat a condition the operator already acknowledged. A kill is never missed
because it stopped happening. Stopping an application is not an alarm.

*Negative.* An application the operator meant to keep running that exits cleanly (`inactive`,
result `success`) raises nothing — systemd has no way to say it was not a choice. A crash
(`failed`), a restart loop, or a running process whose API has stopped answering all do.

*Negative.* An acknowledged condition that goes on for days produces no reminder. The alert page
still lists it as active, with its `last_seen_at`.

*Neutral.* The journal is read from the evaluator's own start; a kill while the console itself was
down is in the journal and on the Logs page, not in the alerts.

## Alternatives considered

* **Every source closes on acknowledge** (the spec's words read literally): the repeating-condition
  flood of context item 1. Rejected.
* **Every source closes when its reading is clear**: a kill leaves the banner at the next
  evaluation. Rejected.
* **Alert on `inactive` too**, with a "maintenance" switch to silence it: a switch the operator has
  to remember before every stop, on a machine where stopped is the normal state. Rejected.
* **Evaluate on the job worker's thread**, as the spec's sentence says: blind for the length of any
  long job. Rejected.
