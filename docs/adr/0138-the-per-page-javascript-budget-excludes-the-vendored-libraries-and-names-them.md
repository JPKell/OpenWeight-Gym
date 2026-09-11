# ADR-0138 — The per-page JavaScript budget excludes the vendored libraries, and names them

**Status:** Superseded by [ADR-0139](0139-the-per-page-javascript-budget-is-a-total-of-120-kb.md) (2026-09-10, the operator's review the same day: one total, 120 KB, no exclusion list)
**Relates to:** [ADR-0128](0128-weightroom-adopts-htmx-through-mirrorwall-0-3.md) (htmx and its
SSE extension vendored by MirrorWall 0.3, opted into per page), [ADR-0020](0020-server-rendered-html-with-progressive-enhancement.md)
(server-rendered HTML, behaviour in modules).
**Source:** Row W10, measuring `apps/weightroom/spec.md` §15 on the reference machine.

## Context

Spec §15 budgets "JS per page ≤ 60 KB excluding ECharts and mermaid, which load only on pages that
use them". The row was written at W0, when ADR-0020 still rejected htmx as a dependency; ADR-0128
(the close of the same row) adopted it, and every WeightRoomGym shell page opts in
(`web/rendering.py`, `mirrorwall: {htmx: true}`) because the app strip, the alert banner, the log
panes and the docs menu are htmx swaps and SSE regions.

Measured at W10 (`tests/performance/test_budgets.py`), every shell page loads **88–89 KB** of
JavaScript: `htmx.min.js` 50.0 KiB and `htmx-ext-sse.js` 8.7 KiB — the two files ADR-0128 vendors —
and 28–30 KiB of everything else: MirrorWall's `theme.js`, `table.js`, `sse.js`, `telemetry.js`,
`log_pane.js` (21.1 KiB together) and the shell's own inline script (6.6–8.6 KiB). The budget as written
fails on every page by the size of htmx alone, and would have failed the day ADR-0128 was accepted.

## Decision

1. **The §15 budget counts the console's own JavaScript** — MirrorWall's modules and the shell's
   inline script — and excludes the vendored, pinned libraries: mermaid and ECharts (as §15 already
   said) **and htmx with its SSE extension** (as ADR-0128 made inevitable). The 60 KB figure is
   kept; it is measured against the heaviest page and asserted under `-m performance`.
2. **The excluded libraries are named and budgeted by name**, not waved through: htmx and its
   extension together stay under 64 KB at the pinned version, and a MirrorWall release that moves
   the pin re-measures. Mermaid loads only on a docs page whose markdown has a fence; ECharts only
   on a telemetry history page. Nothing else is excluded, and the test lists every `<script src>` it
   counted so a new library cannot slip in as "vendored".
3. **The whole is reported beside the part.** The performance test prints the total including the
   excluded libraries, and the gate report quotes both, so the operator sees what a phone actually
   downloads (89 KiB today) and not only what the budget governs.

## Consequences

* Spec §15's row reads "≤ 60 KB of the console's own JavaScript, excluding the pinned libraries —
  htmx and its SSE extension, ECharts, mermaid — which load only where used and are budgeted by
  name (ADR-0138)".
* The measured figures at W10, reference machine: own JavaScript 30.3 KiB on the heaviest page
  (`/apps/freeweight`); the total there 89.1 KiB; htmx and its extension 58.7 KiB. Both in `docs/history/handoffs/W10_HANDOFF.md`.
* Row WM2 (the four applications adopting the 0.3 shell) inherits the same rule.
