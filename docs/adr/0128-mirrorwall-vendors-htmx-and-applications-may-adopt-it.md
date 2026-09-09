# ADR-0128 — MirrorWall vendors htmx, and an application may adopt it

**Status:** Accepted (2026-09-09)
**Amends:** [ADR-0020](0020-ui-rendering-strategy.md) — its *Alternatives considered* rejection of
htmx *as a dependency* is withdrawn; every other rule of ADR-0020 (server-rendered pages,
MirrorWall macros, islands, SSE, no build step, read-only content without JavaScript, the JS
budget) stands. [ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
rule 7 — its sentence that "the htmx library stays what ADR-0020 decided it is: not a dependency"
is superseded by this record; the rest of rule 7 stands.
**Relates to:** [ADR-0004](0004-sse-vs-websockets.md) (SSE stays the transport; htmx's SSE
extension consumes it), [ADR-0026](0026-local-http-hardening.md) and
[ADR-0126](0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)
rule 5 (the CSRF and same-origin checks every htmx request must pass),
[Performance Targets §3.7](../architecture/performance-targets.md) (the per-page JS budget),
[`apps/weightroom/design.md`](../apps/weightroom/design.md) §5 (the components this changes the
implementation of).
**Source:** the operator's decision of 2026-09-09, on the trade-offs written into
[`history/W0_HANDOFF.md`](../history/W0_HANDOFF.md) §6, after row W0 had read the interview's
"server-rendered + htmx" as the patterns only.

## Context

ADR-0020 chose server-rendered HTML with progressive enhancement and rejected htmx *as a
dependency*: "what we need from it (swap a fragment, subscribe to SSE) is a few dozen lines of ES
module, while adopting it would put a third-party runtime in the critical path of every
interaction and pull application logic into HTML attributes." For three applications whose
interactive surface was a handful of tables, drawers and one SSE feed, that was right, and
MirrorWall shipped those few dozen lines.

WeightRoomGym is different in degree. Its console is fragment swaps end to end — status dots,
the telemetry strip, log panes, the guard dialog's live verdicts, chat cards, job and alert lists,
settings forms with per-key outcomes — across four applications' worth of pages, and rows W3–W9
would each write more of the same module by hand. The operator asked for htmx at the interview
(D2) and, given the trade-offs, chose the library.

## Decision

**MirrorWall 0.3 vendors htmx and its SSE extension as shipped static assets. WeightRoomGym uses
them for fragment swaps and SSE-driven regions. The four applications may adopt them in their own
rows and are not required to.**

1. **Vendored, pinned, offline.** `mirrorwall/static/js/vendor/htmx.min.js` and
   `htmx-ext-sse.js`, at one pinned version recorded in MirrorWall's `CHANGELOG.md`, served with
   the content-hash URL every MirrorWall asset already has. No CDN, no fetch at runtime
   (ADR-0020 rule 7). The budget: the two files together stay under 20 KB gzipped and count
   against each page's 60 KB (Performance Targets §3.7); a page that does not include them pays
   nothing.
2. **The base template offers it; a page opts in.** MirrorWall's `base.html` includes htmx only
   when the application sets `mirrorwall.htmx = true` in its template context (or per page). An
   application that leaves it off renders exactly as under 0.2.2 — the upgrade is byte-identical
   for every page that does not opt in, which is the MirrorWall gold standard.
3. **Swaps and SSE regions are htmx; behaviour is still Python and still ES modules.** `hx-get`,
   `hx-post`, `hx-swap`, `hx-target`, `hx-trigger` and `sse-connect`/`sse-swap` replace the
   hand-written swap and subscribe plumbing. Anything that is *logic* — the thinking collapse,
   markdown rendering, code copy, the guard dialog's typed-name check, chart rendering — stays in
   a small ES module attached to a `data-` element, as ADR-0020 rule 3 says. `hx-on` and inline
   scripts are not used; `hx-trigger="every Ns"` polling is not used where an SSE region exists.
4. **Every htmx request passes the same checks as any other.** Form-encoded posts carry
   MirrorWall's CSRF token through `hx-headers` (the base template sets it once); JSON writes are
   not htmx's job. The Host allowlist and, on WeightRoomGym, the `Sec-Fetch-Site`/`Origin`
   checks of ADR-0126 rule 5 apply unchanged — htmx sends `same-origin`. `hx-boost` is not
   enabled: a full navigation stays a full navigation, so the console's routing and its audit
   rows behave as the server rendered them.
5. **Read-only content still works without JavaScript** (ADR-0020 rule 5). A region driven by
   htmx renders its initial state server-side; the swap improves it. A form that htmx submits
   also submits without htmx.
6. **The seven generic components of the design brief** (`app_tab`, `status_dot`, meters,
   `figure_card`, dense `table`, `log_pane`, `side_nav`) are written with htmx attributes where a
   swap or an SSE region is involved and plain markup where none is; `log_pane`'s bounded buffer
   and *dropped N lines* logic stays an ES module, fed by an `sse-swap` region.
7. **MirrorWall's existing swap and SSE modules are kept through 0.3** for the applications that
   use them; they are deprecated in the changelog and removed when the last application adopts
   htmx (row WM2 or later), not before.

## Consequences

*Positive.* Rows W3–W9 write attributes instead of modules for every fragment swap; one
mechanism across the suite once WM2 lands; the enhancement story of ADR-0020 is unchanged in
kind and cheaper in practice.

*Negative.* A third-party runtime in every WeightRoomGym page and, after adoption, every
application page — ADR-0020's objection, now accepted with its mitigation stated: pinned, vendored,
opt-in per page, behaviour kept in modules, `hx-on` and boosting off. A version bump of htmx is a
MirrorWall release with the four template suites re-rendered.

*Negative.* Templates carry more attributes. The rule that logic stays in Python and modules is
what keeps a template readable; review holds it.

*Neutral.* ADR-0020's text is not edited; its rejection is superseded here, with an *Amended by*
note at its head. ADR-0123 rule 7's one sentence likewise.

## Alternatives considered

* **Keep the patterns only** (ADR-0020's original, and row W0's reading). Rejected by the operator
  on the trade-offs: the console has enough swap surfaces that the hand-written module would be
  written a dozen more times.
* **Alpine.js or Stimulus** alongside or instead. Rejected as ADR-0020 rejected them: they add
  client-side state, which is the thing this suite keeps on the server.
* **htmx in WeightRoomGym only, not in MirrorWall.** Rejected: the components the design brief
  sends to MirrorWall 0.3 are the ones that swap and subscribe; vendoring twice would give two
  versions.

## Revisit when

* **An application page needs real client-side state** — the ADR-0020 escape hatch (a single
  client-rendered island with its own tooling) still applies and is unaffected by this record.
* **htmx 3 or a maintenance stop** — the pin is one file; the fallback is ADR-0020's modules,
  which rule 7 keeps until adoption is complete.
