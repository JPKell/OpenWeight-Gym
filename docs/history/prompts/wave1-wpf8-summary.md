# Wave 1 — WPF8

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf8-freeweight-calibration-report-counts-and-export.prompt.md`

**Wave 1 runs with:** WPF1 (WeightRoomGym), WPF3 (PromptCadence + WeightRoomGym),
WPF7 (IdeaPress). No dependency either direction, and no WeightRoomGym touch at all — this row
is the simplest in the wave.

**Branch:** `~/ai/suite/FreeWeight`, its own topic branch off `main` (e.g. `row/wpf8-calibration-report`).
No worktree needed — no other row touches FreeWeight this wave (WPF2, which shares FreeWeight,
is wave 2, starting after this merges).

**Live-demo staggering:** none needed — the calibration report counts/export fix works off
existing job data (fixtures/held-out counts), no fresh live suite run implied by the kickoff.
If your gate does end up wanting a live run, check with the operator against WPF1/WPF3/WPF7's
live steps (ADR-0119, one live model load at a time) before starting it.

**Merge:** merge to FreeWeight `main` whenever your gate is done — first to land in FreeWeight
this arc, nothing to rebase onto.

**Finish line:** as the kickoff states — `WPF8_HANDOFF.md`, gate green with interpreter named,
coverage held, `git status --short` clean, nothing pushed.
