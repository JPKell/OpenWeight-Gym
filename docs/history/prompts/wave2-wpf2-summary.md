# Wave 2 — WPF2

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf2-freeweight-adapter-run-from-the-console.prompt.md`

**Dependency:** WPF1 must be merged to WeightRoomGym `main` before this row starts (its
demonstration saves FreeWeight's settings through the form WPF1 fixes). Wave 2 starts once
wave 1 is fully merged.

**Wave 2 runs with:** WPF4 (LoadCoach + WeightRoomGym), WPF5 (FreeWeight + WeightRoomGym).
WPF2 shares FreeWeight with WPF5, and shares WeightRoomGym with both.

**Branches/worktrees:**
- FreeWeight (primary work — provider write, adapter factory, `config validate`, llama.cpp
  discovery/digest cache, `cli/commands/run.py --adapter`, `services/adapters.py`):
  `row/wpf2-adapter-run` at `~/ai/worktrees/freeweight-wpf2`. WPF5 also touches FreeWeight this
  wave (one new additive dashboard route, disjoint files from yours) — worktree needed so both
  agents aren't sharing one checkout.
- WeightRoomGym (`services/job_kinds.py`, `freeweight_suite_run`): `row/wpf2-adapter-run` at
  `~/ai/worktrees/weightroom-wpf2`, throwaway console port `8779`, own XDG tree.

**Merge order in FreeWeight:** merge first — you have no dependency on WPF5's FreeWeight change.
WPF5 rebases onto your merged `main` before its own merge.

**Merge order in WeightRoomGym:** merge first as well (simplest, no dependency on WPF4 or WPF5).
They rebase onto your merged `main` in turn.

**Live-demo staggering (ADR-0119, memory-safety caps):** the adapter run through the capped job
is a live GPU load. Nothing else in wave 2 does a live model generation (WPF4 restarts a unit,
WPF5 is page-only) — but WPF4's LoadCoach restart test could interrupt an in-flight call if it
runs while your adapter run is live. Don't overlap those two specific moments.

**Finish line:** as the kickoff states — `WPF2_HANDOFF.md`, gate green with interpreter named
in both repos, coverage held, `git status --short` clean, nothing pushed.
