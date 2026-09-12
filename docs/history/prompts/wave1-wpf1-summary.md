# Wave 1 — WPF1

**Full kickoff (read first, this file only adds wave coordination):**
`WeightRoom/docs/history/prompts/wpf1-weightroom-settings-form-refusals-and-slow-calls.prompt.md`

**Wave 1 runs with:** WPF8 (FreeWeight, no WeightRoomGym touch), WPF3 (PromptCadence, also touches
WeightRoomGym), WPF7 (IdeaPress, maybe a WeightRoomGym fixture tweak). No dependency on any of them.

**Branch/worktree:** `row/wpf1-settings-form` at `~/ai/worktrees/weightroom-wpf1`. Throwaway
console port `8779`, own XDG tree. Never touch `weightroom.service` (8769, the operator's).

**Why a worktree:** WPF3 also edits WeightRoomGym this wave (`services/promptcadence_pages.py`,
the pending list) — different files from yours (`services/settings_forms.py`,
`services/config_files.py`, `services/app_api.py`, `services/freeweight_actions.py`,
`tests/security/test_audit_routes.py`), so merge risk is low, but two agents can't share one
checkout — hence separate worktrees.

**Live-demo staggering (ADR-0119, one live model load at a time):** Gate D's llamacpp refresh
and provider switch is a real provider load. WPF3 and WPF7 also have live steps this wave.
Confirm with the operator which one runs its live gate first — code can proceed in parallel,
just not the live moments.

**Merge:** no dependency, so merge to WeightRoom `main` whenever Gate D is done. WPF3 (and WPF7,
if its fixture touch lands) will rebase onto your merged `main` and resolve — expect no real
conflict, disjoint files.

**Finish line:** as the kickoff states — `WPF1_HANDOFF.md`, gate green with interpreter named,
coverage held, `git status --short` clean, nothing pushed.
