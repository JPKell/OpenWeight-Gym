# Kickoff — WPF6: an application's Overview renders inside spec §15's budget

**Row:** WPF6 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md), finding 7). Runs after WP6. It is
independent of the other WPF rows.
**Ships:** unreleased, no version bump. The Overview of a running application renders within
**≤ 300 ms** (spec §15) on the reference machine. The performance test measures the cost that
broke it.

**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WP6_HANDOFF.md` check 6 and finding 7; spec §15; `W10_HANDOFF.md` §4.1 (the budget
table, measured with fakes); `W7_HANDOFF.md` and ADR-0133 rule 4 (why the database URL comes from
`config show --json`).

**Code to read first:** `services/overview.py` (`_compose`, the table read near line 290),
`services/db_reader.py` (`effective_database_url`, `DatabaseUrlCache`), `web/app.py` (where the
cache is built), `tests/performance/test_budgets.py`.

## What WP6 measured on the reference machine (2026-09-11)

The desktop profile, over `https://10.77.10.84:8769`, with the application running, 3 loads per page
(median):

| Page | First paint | Time to first byte |
|---|---|---|
| `/apps/promptcadence` | 580 ms | 554 ms |
| `/apps/loadcoach` | 544 ms | 510 ms |
| `/apps/ideapress` | 520 ms | 484 ms |
| `/apps/freeweight` | 508 ms | 464 ms |
| every other page of the four tabs (143 pages) | ≤ 224 ms | ≤ 188 ms |

The server round trip, 5 requests each (median): PromptCadence Overview 662 ms, LoadCoach 566 ms,
IdeaPress 468 ms; PromptCadence's Trajectories 36 ms. Timed directly: `loadcoach config show --json`
576 ms and `promptcadence config show --json` 494 ms; `journalctl` 6 ms and `systemctl show` 5 ms.

`services/overview.py` calls `effective_database_url(settings, app)`, a process launch, on every
render. `web/app.py` builds a `DatabaseUrlCache` (`app.state.database_urls`) for exactly that call,
and the application pages use it. The W10 budget test measured the Overview at 3.0 ms against
fakes, where the launch costs nothing.

## Decisions already taken — do not reopen

* **The database URL stays the application's own** (`config show --json`, ADR-0133 rule 4). The fix
  reads it through the existing cache, not from the console's configuration.
* **A budget test that fakes away the expensive part does not measure the budget.** The
  performance test for the Overview includes a `config show` launch at a realistic cost, or asserts
  that none happens per render.

## Gates

**Gate A.** Tests first: a second Overview render within the cache's TTL launches no process. Then
the budget test with a realistic launch cost. Implement. Run the gate, naming the interpreter.
Commit.

**Gate B — the live proof.** Restart `weightroom.service`, then measure all four Overviews on the
reference machine as WP6 did (first paint, 3 loads, desktop, LAN address). Commit the handoff with
the numbers before and after.

## Finish line

- The gate green, with the interpreter named, and coverage held; `git status --short` clean.
- `docs/history/handoffs/WPF6_HANDOFF.md`: the cause, the fix, the four Overviews' numbers before and
  after, and what this kickoff got wrong.
- The row marked done. Nothing pushed.
