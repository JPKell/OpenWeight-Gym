# Kickoff — WPF4: LoadCoach stops inside its unit's timeout, and the console reports a slow stop truthfully

**Row:** WPF4 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md), finding 6), and first seen at WP2
(`WP2_HANDOFF.md` §7 item 4, never scheduled). Runs after WP6. It is independent of the other WPF
rows.
**Ships:** unreleased, no version bump in either repository.
- **LoadCoach:** `systemctl --user stop loadcoach.service` completes by SIGTERM well inside
  `TimeoutStopSec`, with nothing killed.
- **WeightRoomGym:** a start, stop or restart whose `systemctl` call outlives the console's 30 s
  limit is reported, and audited, as the state the unit actually reaches. It is not reported as
  `failed`.

**Components:** `~/ai/suite/LoadCoach` first, then `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WP6_HANDOFF.md` finding 6; `WP2_HANDOFF.md` §7 item 4; ADR-0010, ADR-0029 (leases,
recovery); `apps/loadcoach/queue-and-scheduling.md` §5–7; ADR-0125 (the units the console
writes); spec §7.10 (the *application down* alert source).

**Code to read first:** LoadCoach's `web/app.py` (`_lifespan`, the lease keeper, the residency
poller), `web/routes/queue.py` (the queue stream), its job and generation stream routes, and the
`serve` command's uvicorn configuration; WeightRoomGym's `services/processes.py` (`_TIMEOUT_SECONDS`,
the controller), the Overview's control route, and `services/alerts.py` (the unit source).

## What WP6 saw on the reference machine (2026-09-11)

* The **Restart** on LoadCoach's Overview was pressed at 12:32:04 PDT, with the queue draining and 0
  jobs in flight. LoadCoach logged `Shutting down`, then `Waiting for connections to close. (CTRL+C
  to force quit)`. Its residency poller kept calling Ollama's `/api/ps` at 12:32:19 and 12:33:19.
  systemd then logged `State 'stop-sigterm' timed out. Killing.`, `Main process exited,
  code=killed, status=9/KILL` and `Failed with result 'timeout'`. The unit started again at 12:33:34.
  `TimeoutStopUSec=1min 30s`, `KillMode=control-group`.
* The console's audit row `01M28ZA6T3HHPBQK0SFQ8V9PQD` is `unit.restart`, outcome **`failed`**, *
  /usr/bin/systemctl did not answer within 30s*. The restart in fact succeeded 90 s later.
* At WP2 the same stop raised an *application down* alert on the console.
* Long-lived HTTP connections were open at the time: the console's queue page, job pages and log
  panes proxy LoadCoach's SSE streams (arc index §2 item 8).

## Decisions already taken — do not reopen

* **A SIGKILL is not a shutdown.** LoadCoach's stop must end by SIGTERM with its in-flight leases
  handled as ADR-0029 says. Raising `TimeoutStopSec` in the unit template hides the defect, so it is
  not the fix.
* **The console does not guess.** When `systemctl` outlives the console's limit, the console reads
  the unit's state again and reports that. The audit row then says what happened (`ok`, `failed`,
  or still `deactivating` with a follow-up), and never a failure that did not occur.

## Decisions for this row — make each, and record it in the handoff

1. **Why shutdown waits.** Find which connections or threads hold it: the SSE streams, the
   residency poller, the lease keeper, or a generation stream. Reproduce it with a test that holds a
   stream open across a shutdown. Then choose between uvicorn's `timeout_graceful_shutdown`,
   closing the streams on shutdown, or both. Say what a connected client sees.
2. **The console's unit verbs.** Decide whether they use `--no-block` and poll, or keep blocking and
   re-read the state when the call times out. Decide what the Overview shows in the meantime, and
   whether the alert evaluator treats a stop the console itself requested as an outage.

## Gates

**Gate A — LoadCoach.** Tests first: a stream held open does not delay shutdown past a bound, and
an in-flight job's lease is handled. Implement. Run the gate, including
`WEIGHTSDB_REQUIRE_POSTGRES=1` if a migration is touched, and name the interpreter. Commit.

**Gate B — the console.** Test with the fake `systemctl`: a verb that answers after the limit is
audited as the unit's final state. Run the gate. Commit.

**Gate C — the live proof.** Keep the console's Queue page and a job page open on the reference
machine, and restart LoadCoach from its Overview. The journal shows a clean stop well under 90 s
with no SIGKILL. The audit row matches the unit's state, and no *application down* alert is
raised. Restart `weightroom.service` once the console's code is committed. Commit the handoff.

## Finish line

- Both repositories' gates green, with the interpreter named, and coverage held; `git status --short`
  clean in both.
- `docs/history/handoffs/WPF4_HANDOFF.md`: the cause, the fix, the measured stop time before and
  after, the audit ids, and what this kickoff got wrong.
- The row marked done. Nothing pushed.
