# Wave 2 — WPF4

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf4-loadcoach-stops-inside-its-timeout.prompt.md`

**Wave 2 runs with:** WPF2 (FreeWeight + WeightRoomGym), WPF5 (FreeWeight + WeightRoomGym).
No dependency on either.

**Branches/worktrees:**
- `~/ai/suite/LoadCoach` (primary work — `web/app.py` `_lifespan`, lease keeper, residency
  poller, `web/routes/queue.py`, job/generation stream routes, `serve`'s uvicorn config): its own
  topic branch off `main` (e.g. `row/wpf4-clean-stops`). No worktree needed — no other row
  touches LoadCoach this wave.
- WeightRoomGym (`services/processes.py` `_TIMEOUT_SECONDS`/controller, the Overview's control
  route, `services/alerts.py`): `row/wpf4-clean-stops` at `~/ai/worktrees/weightroom-wpf4`,
  throwaway console port `8789`, own XDG tree.

**Why WPF6 isn't in this wave:** WPF6 also touches the Overview (`services/overview.py`) —
same area as your control-route change. That's the real collision moving it avoided; WPF2 and
WPF5 don't touch this file.

**Live-demo staggering:** your unit-restart test (SIGTERM inside the timeout) kills and revives
LoadCoach. WPF2's adapter run this wave routes model calls through LoadCoach too — don't run
your restart test while WPF2's live adapter run is in flight, or you'll break their call, not
yours.

**Merge:** merge LoadCoach `main` whenever done, no rebase needed. For WeightRoomGym, merge
after WPF2 if it lands first (rebase onto its `main`); WPF5 merges after you, rebasing onto both.

**Finish line:** as the kickoff states — `WPF4_HANDOFF.md`, gate green with interpreter named
in both repos, coverage held, `git status --short` clean, nothing pushed.
