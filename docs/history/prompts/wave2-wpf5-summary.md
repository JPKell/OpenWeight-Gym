# Wave 2 — WPF5

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf5-weightroom-dashboard-and-system-pages.prompt.md`

**Wave 2 runs with:** WPF2 (FreeWeight + WeightRoomGym), WPF4 (LoadCoach + WeightRoomGym).
No hard dependency, but merge last (see below) — you touch the most shared surface this wave.

**Branches/worktrees:**
- FreeWeight (one new additive read-only dashboard API route, since the Dashboard is HTML-only
  today — disjoint from WPF2's provider/adapter files): `row/wpf5-dashboard-system` at
  `~/ai/worktrees/freeweight-wpf5`.
- WeightRoomGym (`rendering.py` — `_APP_PAGES`/`_PAGE_HREF`/`_PAGE_PHASE`, the §14 audit
  registry, `services/promptcadence_pages.py` System reader, the three new page templates):
  `row/wpf5-dashboard-system` at `~/ai/worktrees/weightroom-wpf5`, throwaway console port
  `8799`, own XDG tree.
- LoadCoach's `web/routes/system.py`/template are read-only parity reference for your new
  System pages — you don't edit LoadCoach.

**You are the row most likely to need a manual merge:** you're the only one touching
`rendering.py` and the §14 registry this wave, so no conflict there — but you land last in both
FreeWeight and WeightRoomGym, after WPF2 (and WPF4 for WeightRoomGym). Rebase onto their merged
`main` in each repo, resolve, regenerate the OpenAPI snapshot and `api.md` from scratch in a
scratch XDG tree rather than hand-merging them (same rule as the WP3/WP5 parallel-row protocol).

**Live-demo staggering:** no live model load in this row's own gates — page-only plus one new
read-only API route. No ADR-0119 conflict to manage on your side; just don't run your console
demo while WPF2's live adapter run or WPF4's restart test are mid-flight, since you're sharing
the same worktree convention, not the same server.

**Merge:** last in the wave, in both repos, for the reasons above.

**Finish line:** as the kickoff states — `WPF5_HANDOFF.md`, gate green with interpreter named
in both repos, coverage held, `git status --short` clean, nothing pushed.
