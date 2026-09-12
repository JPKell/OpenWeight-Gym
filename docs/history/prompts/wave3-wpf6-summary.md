# Wave 3 — WPF6

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf6-weightroom-overview-inside-its-budget.prompt.md`

**Dependency:** none of the WPF rows block this one directly, but it runs alone in its own wave
specifically to avoid touching `services/overview.py` while WPF4 is mid-flight on the Overview's
control route (wave 2). Start once wave 2 is fully merged.

**Wave 3 runs with:** nothing — sole occupant.

**Branch/worktree:** no other row touches WeightRoomGym this wave, so a worktree isn't required
for concurrency. A plain topic branch off `main` (e.g. `row/wpf6-overview-budget`) is enough.
Still avoid the operator's live `weightroom.service` (8769) for iteration — a quick throwaway
port is fine if you want to run the console while working, just not required by another row.

**Code:** `services/overview.py` (`_compose`, the table read near line 290),
`services/db_reader.py` (`effective_database_url`, `DatabaseUrlCache`), `web/app.py` (where the
cache is built), `tests/performance/test_budgets.py`.

**Live-demo staggering:** none needed — no other row is live this wave.

**Merge:** straight to `main`, no rebase needed.

**Finish line:** as the kickoff states — `WPF6_HANDOFF.md`, the budget test measuring the real
cache cost (not faked away), gate green with interpreter named, coverage held,
`git status --short` clean, nothing pushed.
