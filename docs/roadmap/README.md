# Roadmaps and work files

**Since 2026-09-09 each arc the operator starts has its own work file** in the master-table shape
(`# | Phase → ships | Model · effort | Runs after | Work overview — and required reading | Why this
model`), with the same status marks, the same `docs/history/handoffs/<ROW>_HANDOFF.md` rule and one kickoff
prompt per row under `docs/history/prompts/`. A person opening this directory sees the arcs first.

## Work files — the schedules

| File | Arc | Started | Status |
|---|---|---|---|
| [`weightroom-work.md`](weightroom-work.md) | **WeightRoomGym** — the fifth application, the host operator's console (rows W0–W10, WS1–WS4, WM, WM2) | 2026-09-09 | W0–W9, WS1–WS4, WM, WA1, WI1 done; W10 built 2026-09-10 (`1.0.0` prepared), its Gate D verification the operator's; WM2 next, after the release |
| [`outstanding-work.md`](outstanding-work.md) | The PromptCadence arc (M10–M13), the Adapter arc (LA0–LA3), M9 and the follow-up rows A1–N6 — every row before the per-arc convention | 2026-09-02 | All rows done by 2026-09-09; keeps the index of arc files in its §1.2 |

## Roadmaps — the rationale

| File | Contents |
|---|---|
| [`master-roadmap.md`](master-roadmap.md) | Milestones M1–M9, dependency graph, work streams, the version trajectory, §9 the current state of every component |
| [`promptcadence-roadmap.md`](promptcadence-roadmap.md) | M10–M13: the harness and its four packages — decisions D-1…D-13 (ADRs 0045–0057) |
| [`adapter-roadmap.md`](adapter-roadmap.md) | LA0–LA3: hot-swappable LoRA serving — decisions A-1…A-10 (ADRs 0058–0067) |
| [`model-assignment.md`](model-assignment.md) | Which model and effort per phase, what makes a phase hard, the one-model rule (§3.5), the overnight rules (§2.12) |

The WeightRoomGym arc has no separate roadmap document: its rationale is ADRs 0123–0128 and
[`apps/weightroom/`](../apps/weightroom/spec.md), and its work file's preamble says so.
