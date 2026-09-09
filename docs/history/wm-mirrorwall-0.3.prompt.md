# Kickoff — WM: MirrorWall 0.3 — the WeightRoomGym design brief's tokens and generic components

**Row:** WM (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../roadmap/weightroom-work.md).
Runs after W0; **before W3**.
**Ships:** `mirrorwall 0.3.0` prepared (not published): the token deltas and the seven generic
components of [`apps/weightroom/design.md`](../apps/weightroom/design.md) §2 and §5, additive,
with every existing consumer rendering byte-identically until it opts in.
**Component:** `~/ai/suite/py/MirrorWall` (its `.venv`); then one docs commit in
`~/ai/suite/WeightRoom` (the row marked done; `packages/mirrorwall/spec.md` and
`development-plan.md` gain a Phase 4 section, mirrored byte-identically into
`py/MirrorWall/docs/`).

## Standing preamble

[`outstanding-work.md` §2](../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../roadmap/weightroom-work.md).

**Read first:** the design brief in full; `packages/mirrorwall/spec.md` and `development-plan.md`;
`standards/ui-ux-standards.md` §1, §3, §4, §4.1, §7, §9, §10; ADR-0020; `mirrorwall/static/css/tokens.css`,
`layout.css`, `components.css`, `templates/mirrorwall/components.html`, `telemetry_bar.html`;
Gold Standards §2 MirrorWall (bullet 1: a component upgrade without any application changing its
pages — proven by rendering the four applications' template suites against the new version).

## Decisions already taken — do not reopen

* The dark palette is unchanged — the artboard uses MirrorWall's dark set exactly. What changes is
  scale and density: `--mw-font-size-*` (13/12/11/18/22 px), `--mw-row-h` 32 px behind
  `data-density="dense"` with `data-density="comfortable"` the default and 36 px kept there,
  `--mw-sidebar-w` 200 px, JetBrains Mono vendored first in `--mw-font-data`, the label tracking
  token, the four status tokens, the meter tokens (brief §2).
* The seven generic components: `app_tab`, `status_dot`, meters in `telemetry_bar`, `figure_card`,
  `table(density=…)`, `log_pane` (+ its ES module: bounded, pausable, level-coloured, *dropped N
  lines*), `side_nav` (brief §5). The DB grid, chat thread, markdown article, guard dialog and
  re-auth prompt stay in WeightRoomGym.
* Every dot has a word; every meter is `role="meter"` with a text value; contrast asserted for
  every new pair in both themes (brief §7).
* No Python dependency is added (MirrorWall's budget is `jinja2`, `starlette`, `anyio`); the font
  is a vendored asset, not a fetch.
* **htmx is vendored** ([ADR-0128](../adr/0128-mirrorwall-vendors-htmx-and-applications-may-adopt-it.md)):
  `static/js/vendor/htmx.min.js` and `htmx-ext-sse.js`, one pinned version named in the
  CHANGELOG, together under 20 KB gzipped, included by `base.html` only when the context sets
  `mirrorwall.htmx = true`; the CSRF token set once through `hx-headers`; `hx-boost` and `hx-on`
  unused. The seven components use `hx-*`/`sse-*` for swaps and regions and ES modules for
  behaviour (rule 3 and 6); the existing swap/SSE modules stay and are marked deprecated (rule 7).
  A page that does not opt in renders byte-identically to 0.2.2 — that is the gold-standard test.

## Gates

**Gate A — tokens.** `tokens.css`/`tokens.json` deltas; the `data-density` mechanism; light values
for every new token; the contrast test extended. The four applications' snapshot suites still
pass against this tree (run each from its own repository against an editable MirrorWall;
report the invocations). Commit.

**Gate B — components.** The seven macros with keyword arguments and defaults that make sense
for any application, ARIA per pattern, the `log_pane` module under the JS budget, accessibility
tests (keyboard, ARIA) per component, a rendering golden each. Commit.

**Gate C — release-prepared.** `CHANGELOG.md`, `__about__` `0.3.0`, `docs/` mirror, the Phase 4
section in the spec and plan (in `WeightRoom/docs/packages/mirrorwall/` first, then `cmp`-proven
into `py/MirrorWall/docs/`), the row marked done. Commit in both repositories.

## Demonstrate

A page in MirrorWall's own demo/tests rendering the brief's shell skeleton — top bar with four
`app_tab`s and dots, a `telemetry_bar` with three meters, a `side_nav`, four `figure_card`s, a
dense `table`, a `log_pane` fed by a fake stream — in both themes; and `pytest` in each of the
four application repositories green against the new MirrorWall with no template change.

## Finish line

Gate green in `py/MirrorWall`; coverage ≥ 95 %; nothing pushed or tagged; `docs/history/WM_HANDOFF.md`.
