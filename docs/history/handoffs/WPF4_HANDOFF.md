# WPF4 Handoff — LoadCoach stops inside its unit's timeout, and a slow unit verb is not a failure

**Row:** WPF4 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, wave 2 · **Model:** Claude
Opus 5 (high) · **Kickoff:** `history/prompts/wpf4-loadcoach-stops-inside-its-timeout.prompt.md`
(wave note `history/prompts/wave2-wpf4-summary.md`) · **Branches:** `row/wpf4-clean-stops` in
`~/ai/suite/LoadCoach` and in `~/ai/worktrees/weightroom-wpf4`, **neither merged** ·
**Ships:** unreleased, no version bump in either repository.

## 1. What shipped

| Repo · commit | Gate | What |
|---|---|---|
| LoadCoach `d6d8844` | A | **`serve` bounds uvicorn's graceful shutdown** at `SHUTDOWN_GRACE_SECONDS = 5`. Uvicorn's default is `None` — wait for every open connection *for ever* — and LoadCoach's SSE streams end only when their client goes away, so any connected stream held the stop until systemd's `TimeoutStopSec` and the unit was `SIGKILL`ed. One new e2e test serves the real application on a real socket with the queue stream held open **and** a job `executing`, sends the real `SIGTERM`, and measures the stop and the exit; one unit test asserts `serve` hands uvicorn the bound. `docs/operations.md` states the stop's two budgets and what a connected client sees |
| WeightRoomGym (this worktree) | B | **A `systemctl` call that outlives the console's 30 s limit is judged by the state the unit reached.** `services/processes.act_and_settle` + `ActReport`: on a timeout — and only then — one extra `systemctl show`, and the outcome is `ok` when the unit reached what the verb asked for (with a message saying the call outlived the limit), `failed` with systemd's own `Result` when the unit is `failed`, `pending` while systemd is still `activating`/`deactivating`. Used by the console's control route (so by all three verbs, the page's form and *restart for settings*), by `wr-gym units start\|stop\|restart`, and by the Ollama pane's restart. `FakeSystemdController(slow=…)` is how a test makes a verb time out. `api.md` §2 and `data-model.md`'s `message` row state the rule |
| — | C | **The live proof is split**: the LoadCoach half is done here, under transient units of this row's own (§4). The console half needs a merge and a stop of the operator's own `loadcoach.service` (§6) |

Nothing pushed, nothing tagged, no version bump (`loadcoach` stays `1.5.0`, `wr-gym` `1.0.0`, both
under `[Unreleased]`).

**Gates**, both interpreters **CPython 3.14.4**:

| Repo | Interpreter | `ruff format --check` / `ruff check` | `mypy src tests` | `lint-imports` | `pytest -m "not live and not performance"` | coverage (floor 85 %) |
|---|---|---|---|---|---|---|
| LoadCoach | `~/ai/suite/LoadCoach/.venv/bin/python` | 239 files / clean | 216 files, clean | 4 kept | **1112 passed, 5 skipped, 19 deselected** | **90.52 %** |
| WeightRoomGym | `~/ai/worktrees/weightroom-wpf4/.venv/bin/python` | 233 files / clean | 226 files, clean | 5 kept | **1872 passed, 3 skipped, 10 deselected** | **90.49 %** |

No migration was touched, so `WEIGHTSDB_REQUIRE_POSTGRES=1` was not needed. `git status --short`
clean in both at the end.

**The worktree's virtualenv needed one extra step**: `pip install -e ".[dev]"` cannot resolve
`mirrorwall>=0.3.1` (0.3.1 is prepared, not published), so MirrorWall was installed editable from
`~/ai/suite/py/MirrorWall` first, exactly as the main checkout's venv has it. That left
`py/MirrorWall` clean.

## 2. The decisions this row was asked to make

### 1. Why shutdown waited, and what was chosen

**Nothing inside LoadCoach was holding it. The open HTTP connections were, and uvicorn was
configured to wait for them without limit.** `Server.shutdown()` closes the listening sockets,
tells each connection to stop keeping alive, and then `await asyncio.wait_for(…,
timeout=self.config.timeout_graceful_shutdown)`; with `timeout_graceful_shutdown=None` that is an
unbounded wait for `server_state.connections` to empty. A streaming response is not idle, so
uvicorn does not close it — `H11Protocol.shutdown()` only clears `keep_alive` for a cycle whose
response is unfinished — and LoadCoach's queue and telemetry streams pass
`terminal_events=frozenset()`: they are open-ended by design and end only when the client
disconnects (`web/routes/queue.py`, `web/routes/system.py`; a job's log pane and a generation
stream have terminal events but a running job's pane stays open too).

The residency poller WP6 watched calling Ollama's `/api/ps` at 12:32:19 and 12:33:19 was a
**symptom, not the cause**: uvicorn sends the lifespan `shutdown` event *after* the connection
drain, so `_lifespan`'s `finally` — which stops the publisher, the sampler and the queue runtime —
had not been reached. The same ordering rules out the other suspects in the kickoff's list (the
lease keeper, a generation) and rules out the fix of closing the streams from the application: at
`SIGTERM` there is no hook the app can see before the drain, because the only thing uvicorn has
done by then is set `should_exit`.

**Chosen: `timeout_graceful_shutdown=5`, and not closing the streams.** Closing them would need a
process-wide shutdown flag set from a `uvicorn.Server` subclass's `handle_exit`, a terminal event
published into three separate brokers (whose per-stream subscriber registries live in MirrorWall
and are private), and `terminal_events` extended in four routes — in a package this row may not
touch and for an application that would still need the bound as a backstop. The bound is one
argument, it covers every connection LoadCoach has now or later, and it is the only place all four
stream routes pass through.

**Five seconds** because the wait is only ever spent on a connection that has not finished: an
ordinary request is milliseconds, and a stream is cancelled rather than waited out. The stop's
second budget is unchanged — `QueueRuntime.stop()` joins the scheduler and each worker for up to
10 s, so a stop with a job mid-attempt is ~15 s and one with nothing running is ~5 s with a stream
open and ~0.2 s without. Both are well inside the unit's 90 s.

**What a connected client sees:** its connection closes mid-stream, with no terminal frame — the
frames it already received stay valid. A browser `EventSource` (and htmx's SSE extension)
reconnects on its own and resumes with `Last-Event-ID`; the queue stream's replay is the whole
current state, so one frame makes the page right again. Measured with `curl -N` held open across
the stop: the body simply ends after its last complete frame, no `error` frame, no truncated frame.
`loadcoach queue drain` remains the way to let in-flight work finish *before* stopping; a job still
`executing` when the process goes is recovered on the next start (queue §10), which the row's e2e
test asserts.

### 2. The console's unit verbs

**Blocking, and re-read when the call is killed — not `--no-block`.** `--no-block` makes
`systemctl` return as soon as the job is enqueued, which throws away the one thing the current
design is good at: a refusal in systemd's own words in under a second (`Unit not found.`, a polkit
refusal). Every outcome would then have to be learned by polling, for every verb, to fix a case
that costs one extra `systemctl show` on the rare timeout. So the verbs stay blocking, and
`act_and_settle` asks the unit what happened when — and only when — the call itself was killed.

**What the Overview shows in the meantime:** the state the unit is actually in. No UI change was
needed: the control form redirects back to the page, and `AppView.pill` already renders
`activating` as *starting* and `deactivating` as *stopping* (W2's decision), so a stop systemd has
not finished reads *stopping* rather than *failed* or *stopped*.

**The alert evaluator is unchanged, and a console-requested stop is not an outage.** `app_down`
fires on a unit that is `failed` or `auto-restart`, or on an `active` unit older than the health
grace whose `/api/v1/health` does not answer; an `inactive` unit "is a choice, not an outage"
already, and `tests/integration/test_alerts.py::test_a_stopped_or_uninstalled_application_is_not_down…`
asserts it. What fired at WP2 was the **`failed`** unit that the `SIGKILL`ed stop left behind —
which is a fact an operator should be alerted to, and which LoadCoach's half of this row stops
producing. Suppressing alerts for a console-requested verb was considered and rejected: it would
hide exactly the case WP2 found.

### 3. The `pending` row's follow-up (a ceiling, stated)

A `pending` audit row is written when systemd is still working after the call was killed, and
**nothing completes it automatically** — `services/audit.complete()` exists (`pending → ok|failed`)
but no reader calls it for unit verbs. The operator sees the live state on the page and in the
journal; the row records that the verb was asked and that the answer was not in yet. Completing it
would need a reader that revisits open rows (the alert evaluator's thread is the obvious host) —
worth a row only if these rows actually appear, and with LoadCoach fixed they should not.

## 3. The fix, in one line each

* **LoadCoach** `src/loadcoach/cli/commands/system.py`: `SHUTDOWN_GRACE_SECONDS: Final = 5` (an
  `int`, because uvicorn types the parameter `int | None`), passed to `uvicorn.run`.
* **WeightRoomGym** `src/weightroom/services/processes.py`: `TIMEOUT_SECONDS` made public,
  `SETTLED_STATE_BY_VERB`, `TRANSITIONAL_STATES`, `ActReport` (result + verb + the re-read status,
  with `outcome`/`reached`/`note`), `act_and_settle`, and `FakeSystemdController(slow=…)`.
* `web/routes/apps.py::_control` audits `report.outcome` with `report.note` and raises only on
  `failed`; `cli/commands/units.py::_control` and `services/ollama.py::restart_ollama` do the same.

## 4. The measurements

**The e2e test** (`LoadCoach/tests/e2e/test_graceful_stop.py`, fake provider, no GPU): the real
application under uvicorn on a loopback socket, the queue stream held open and one job `executing`,
then `SIGTERM`. **15.1–15.2 s** over three runs (5 s for the stream, 10 s for the busy worker's
join), `Application shutdown complete` in the log, and `recover()` in the parent requeues the job
(`state_reason = "recovered"`, `lease_owner` cleared).

**Live, under transient units of this row's own** — `systemd-run --user --unit=wpf4-… --collect`
with `KillMode=control-group`, its own XDG tree, its own SQLite file, `provider.kind = "fake"`, on
ports 8799/8798. Neither the operator's units nor the GPU were touched.

| | Before (uvicorn's default, `TimeoutStopSec=15`) | After (`loadcoach serve`, `TimeoutStopSec=90`) |
|---|---|---|
| Open connections | the queue SSE stream | the queue **and** telemetry SSE streams |
| `systemctl --user stop` wall | **15.18 s** (the whole timeout) | **5.16 s** |
| Journal | `Shutting down` → `Waiting for connections to close.` → `State 'stop-sigterm' timed out. Killing.` → `Killing process … with signal SIGKILL` → `Main process exited, code=killed, status=9/KILL` → `Failed with result 'timeout'` | `Shutting down` → `Waiting for connections to close.` → `Cancel 2 running task(s), timeout graceful shutdown exceeded` → `Waiting for application shutdown.` → `Application shutdown complete.` → `Finished server process` |
| Unit | `Result=timeout` | **`Result=success`**, no `Killing` line |

The "before" run reproduces WP6's journal line for line, on a unit nobody else owns, which is what
makes the "after" run a proof rather than an absence of evidence.

**One thing to know about the exit status.** A clean uvicorn stop ends as *terminated by
`SIGTERM`* (`-15`), not exit 0: `capture_signals()` restores the default disposition and re-raises
the signal it caught, deliberately. systemd counts that as success — it is the signal it sent — so
the unit is `Result=success`. A test asserting `returncode == 0` would fail on a correct stop; the
row's test accepts `0` or `-SIGTERM` and asserts that the teardown ran, because the status that
must never appear is `-9`.

## 5. What this kickoff got wrong

1. **"Find which connections or threads hold it: the SSE streams, the residency poller, the lease
   keeper, or a generation stream."** Only the connections can hold it. Every thread in that list
   is stopped by the lifespan's `finally`, and uvicorn runs the lifespan `shutdown` **after** the
   connection drain — so the poller WP6 saw still working was the symptom of the drain never
   finishing. Fixing "the poller" or "the keeper" would have changed nothing.
2. **"completes by SIGTERM well inside `TimeoutStopSec`, with nothing killed"** reads as *exit 0*.
   A correct stop is *killed by the `SIGTERM` systemd sent*, by uvicorn's design (§4). "Nothing
   killed" is true of `SIGKILL`, which is the property to assert.
3. **Gate C's "Restart `weightroom.service` once the console's code is committed" cannot work from
   this row.** That unit serves the operator's `~/ai/suite/WeightRoom` checkout, and this row's
   console code is on a branch in `~/ai/worktrees/weightroom-wpf4`; restarting it would re-serve
   the same code. The console half of the live proof needs the merge first (§6).
4. **ADR-0029 needed nothing.** "An in-flight job's lease is handled" was already true and already
   tested — the simulator kills at seven lifecycle points and
   `tests/integration/test_recovery.py` does it with a real `kill -9` — and the teardown this row
   restores is strictly gentler than the `SIGKILL` those tests cover. The row's own test asserts
   the `SIGTERM` case end to end rather than re-proving recovery.
5. **"whether the alert evaluator treats a stop the console itself requested as an outage"** — it
   never did; §2 decision 2 has the evidence.
6. Minor: the console's 30 s is a limit on **one `systemctl` call** (`processes.run_command`), not
   on the page request or on the verb as a whole.

## 6. What is left, and it needs the operator

Gate C's console half, in this order:

1. **Merge both branches** (`row/wpf4-clean-stops` in `~/ai/suite/LoadCoach` and in
   `~/ai/worktrees/weightroom-wpf4`) — the wave note has WeightRoomGym merging after WPF2.
2. **Restart the console** so it serves the merged code:
   `systemctl --user restart weightroom.service` (its `ExecStart` is the main checkout's editable
   install). `loadcoach.service` already runs
   `/home/jpk/ai/suite/LoadCoach/.venv/bin/loadcoach serve` from the same editable checkout, so
   LoadCoach's fix is live in it from its next restart — no reinstall needed.
3. **The demonstration**, with WPF2's live adapter run *not* in flight (the wave note's staggering):
   open the console's LoadCoach **Queue** page and a **job** page (so the console holds LoadCoach's
   queue stream and a log pane), then press **Restart** on LoadCoach's Overview.
   * **Pass:** `journalctl --user -u loadcoach.service --since "-5min"` shows `Shutting down`,
     `Cancel N running task(s), timeout graceful shutdown exceeded`, `Application shutdown
     complete.`, and **no** `State 'stop-sigterm' timed out. Killing.` and no `status=9/KILL`; the
     stop takes about 5 s and the whole restart well under 90 s (`systemd-analyze`-free check:
     `systemctl --user show loadcoach.service -p Result` is `success` after a plain
     `systemctl --user stop`).
   * **Pass:** the console's audit row for `unit.restart` is `ok` (not `failed`), and
     `GET /api/v1/alerts` raises no `app_down` for `loadcoach.service`.
   * Record the audit id in this handoff's §1 and mark the row done.

Nothing else in this row needs the GPU, a live model, or a shared unit.

## 7. Sibling callers left alone, on purpose

`services/self_restore.py` stops and starts **the console's own** unit from inside a job, so there
is no process left to re-read after the stop — its answer is the restore report, not an audit
outcome. `services/setup.py`'s wizard step `enable`s and `start`s `weightroom.service`; `enable`
has no state to settle against, and the `start` is of the unit whose process the wizard is running
in. Both would need their own answer for *pending*, which no caller of theirs can render today.

## 8. Left on the reference machine

Nothing. The two transient units were `--collect`ed and are gone (`systemctl --user list-units
'wpf4*'` is empty), ports 8798/8799 are free, and everything the demonstration wrote is under this
session's scratchpad — no XDG file, no database and no unit file of the operator's was touched. All
five application units were `active` before and after.

## 9. The live check, 2026-09-12, by the merging session

Both halves merged (LoadCoach on its `main`, the console at `950b591`'s chain), then the units
restarted onto them.

**Before, by accident and usefully:** the first restart went through the console while
`loadcoach.service` was still running the pre-merge binary, with the queue stream and a job's event
stream held open. It reproduced WP6 finding 6 exactly — `Waiting for connections to close`, then
`State 'stop-sigterm' timed out. Killing.`, `Killing process 188441 (loadcoach) with signal SIGKILL`,
`status=9/KILL` at 90 s (`TimeoutStopUSec=1min 30s`). **And the console read it correctly**: the audit
row was `unit.restart … pending`, *"/usr/bin/systemctl did not answer within 30s; loadcoach.service is
deactivating (success)"* — where WP6 got `failed`. That is this row's console half, proved against the
very failure it was written for.

**After**, same two streams open, merged binary: the control call returned in **5.2 s**,
`Application shutdown complete` then `Stopped` and `Started`, unit `active`, audit row
`unit.restart … ok` (`2026-09-12T05:00:02.422Z`), and **no `app_down` alert** on the banner.
