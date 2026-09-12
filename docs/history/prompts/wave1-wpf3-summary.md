# Wave 1 — WPF3

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf3-promptcadence-cancel-resolves-approvals.prompt.md`

**Wave 1 runs with:** WPF1 (WeightRoomGym), WPF8 (FreeWeight), WPF7 (IdeaPress). No dependency
either direction.

**Branches/worktrees:**
- `~/ai/suite/PromptCadence`, its own topic branch off `main` (e.g. `row/wpf3-cancel-approvals`).
  No worktree needed — no other row touches PromptCadence this wave.
- WeightRoomGym piece (`services/promptcadence_pages.py` pending list, `tests/fixtures/promptcadence/`):
  `row/wpf3-cancel-approvals` at `~/ai/worktrees/weightroom-wpf3`. Throwaway console port `8789`,
  own XDG tree. Never touch `weightroom.service` (8769).

**Why a worktree for the WeightRoomGym piece:** WPF1 is also editing WeightRoomGym this wave
(`services/settings_forms.py` and neighbors) — different file from yours, low merge risk, but
two agents can't share one checkout.

**Live-demo staggering (ADR-0119):** the cancelled-trajectory demo is a live call through
LoadCoach. WPF1's Gate D and WPF7's live stage run are also live this wave. Confirm ordering
with the operator before running yours.

**Merge:** do the PromptCadence work first (no dependency), then the WeightRoomGym piece. Rebase
the WeightRoomGym worktree onto `main` before merging if WPF1 has already landed — expect no real
conflict, disjoint files.

**Finish line:** as the kickoff states — `WPF3_HANDOFF.md`, gate green with interpreter named,
coverage held, `git status --short` clean in both repos, nothing pushed.
