# Wave 1 — WPF7

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf7-ideapress-cancel-and-reasoning-budget.prompt.md`

**Wave 1 runs with:** WPF1 (WeightRoomGym), WPF8 (FreeWeight), WPF3 (PromptCadence +
WeightRoomGym). No dependency either direction.

**Branch:** `~/ai/suite/IdeaPress`, its own topic branch off `main` (e.g. `row/wpf7-cancel-reasoning-budget`).
No worktree needed — no other row touches IdeaPress this wave.

**Console fixtures caveat:** the kickoff notes a possible touch to the console's IdeaPress
fixtures "if an IdeaPress answer changes." If it does, that's a small data-file change —
apply it directly against WeightRoomGym `main` once WPF1's and WPF3's WeightRoomGym pieces
have landed, rather than opening a third WeightRoomGym worktree for it.

**Live-demo staggering (ADR-0119, one live model load at a time):** the live IdeaPress stage
run is a real model load, same as WPF1's Gate D and WPF3's cancel demo. Confirm with the
operator which live step runs when — this row also has the reasoning-budget behavior
(`qwen3.5:9b-q8_0` thinking budget) to prove live, so plan two live windows if needed, not one.

**Merge:** merge IdeaPress `main` whenever your gate is done — no rebasing needed there. If the
fixtures touch is needed, do it last, after WPF1/WPF3's WeightRoomGym pieces are in.

**Finish line:** as the kickoff states — `WPF7_HANDOFF.md`, gate green with interpreter named,
coverage held, `git status --short` clean, nothing pushed.
