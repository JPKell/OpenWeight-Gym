# Kickoff — WM2: the four applications adopt MirrorWall 0.3

**Row:** WM2 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W10; outside the arc's `1.0.0`.
**Ships:** four patch releases prepared (FreeWeight, LoadCoach, IdeaPress, PromptCadence), each
opting into the MirrorWall 0.3 surfaces its pages want; template snapshots updated; CHANGELOGs.
**Component:** each application's own repository in turn (`~/ai/suite/FreeWeight`,
`~/ai/suite/LoadCoach`, `~/ai/suite/IdeaPress`, `~/ai/suite/PromptCadence`); one docs commit in
`~/ai/suite/WeightRoom` at the end (the row marked done, the handoff written).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** [`design.md`](../../apps/weightroom/design.md) §5 (the seven generic components
and what each application's template suite may take) and §6 (what the four applications adopt
later — this row's list); `packages/mirrorwall/spec.md`; `standards/ui-ux-standards.md` §1, §3,
§4, §7, §9; ADR-0128 (htmx through MirrorWall, opt-in per page) and ADR-0138 (the per-page
JavaScript budget: the console's own scripts against 60 KB; htmx and its SSE extension, mermaid
and ECharts excluded and budgeted by name); `history/handoffs/WM_HANDOFF.md` (what 0.3 shipped
and what it deliberately did not change), `history/handoffs/W3_HANDOFF.md` (how WeightRoomGym's
shell opted in — the precedent), `history/handoffs/W10_HANDOFF.md` §"JavaScript per page" (the
measured figures the applications inherit); each application's `web/templates` and its
accessibility checklist test.

## Decisions already taken — do not reopen

* **Nothing in MirrorWall 0.3 changes an application's rendering until it opts in** (design.md
  §6; Gold Standards MirrorWall bullet 1 — the four template suites render byte-identically
  under 0.3 today). This row is the opt-in, page by page, and every change is a diff a person can
  see in the template snapshot.
* **The published MirrorWall is the target** — `0.3.1` or later, on PyPI, pinned in each
  application's `ci.lock`. No editable path installs, no `TODO: re-pin`.
* **htmx is opt-in per page** (ADR-0128): an application adds it only where a swap or an SSE
  region replaces a script it already carries, and the per-page budget of ADR-0138 is asserted
  the way `WeightRoom/tests/performance/test_budgets.py` asserts it.
* **What each application adopts is the §6 list and nothing more:** `data-density="dense"` where
  its tables want it, the status dot on its health page, meters in its telemetry bar, the log
  pane on run/job pages, the tab strip linking to WeightRoomGym and to its peers. A component the
  page does not need is left alone.
* **The tab strip's targets come from configuration**, never hardcoded: each application already
  knows its own port and nothing else. A `[console] url` (or the existing `[apps]`-style
  section, whichever the application's configuration standards §4 allow without a new
  section) names WeightRoomGym; the strip renders only what is configured, and an application
  that configures nothing renders no strip — byte-identical to today.
* **Versions:** four patch releases (`1.x.y+1`), each with a CHANGELOG entry under
  *Changed*; prepared, not tagged or pushed. The operator holds tags.

## Gates

**Gate A — FreeWeight.** The opt-ins on its pages; the template snapshot test updated; the
accessibility checklist green; the JS-per-page assertion added; CHANGELOG; gate; commit.

**Gate B — LoadCoach.** As A, plus the log pane on the job pages (the queue's own SSE stream
through `log_pane`'s `sse-close` frame, so a finished job's pane stops reconnecting).

**Gate C — IdeaPress.** As A, plus the log pane on the stage-run pages.

**Gate D — PromptCadence.** As A, plus the log pane on the trajectory page (its event stream),
and the status dot beside each tier on the tiers page.

**Gate E — docs.** `history/handoffs/WM2_HANDOFF.md`; the row marked done in
`weightroom-work.md`; `roadmap/README.md` if the arc's status line changes.

## Finish line

Each application's gate green on its own venv (name the interpreter), the four template
snapshots updated deliberately (a diff a reviewer reads, not a regenerated blob), no application
importing another, no new dependency, four release commits prepared, the handoff written.
