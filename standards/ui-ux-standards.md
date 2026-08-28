# UI/UX Standards

**Applies to:** the web interface of all three applications.
**Shared implementation:** [MirrorWall](../packages/mirrorwall/spec.md).
**Rendering decision:** [ADR-0020](../adr/0020-ui-rendering-strategy.md) — server-rendered HTML with
progressive enhancement; no npm, no bundler, no SPA framework.

The three applications should feel like one product family without pretending their information
architectures are the same. Shared: tokens, components, interaction rules, accessibility, the
telemetry bar, the shell. Not shared: pages, navigation, terminology, data density decisions.

---

## 1. Design tokens

Adopted from the FreeWeight brand package and generalized. MirrorWall ships them as
`tokens.css` (custom properties) and `tokens.json` (machine-readable).

```css
:root {
  /* Brand */
  --mw-ink:            #0E1823;
  --mw-accent:         #2F80ED;   /* FreeWeight; overridden per app. Fills, focus rings and
                                     chart series — the 3:1 UI-boundary rule. NEVER text. */
  --mw-accent-text:    #1A5FBF;   /* The same blue, darkened until text passes 4.5:1.
                                     Every accent-coloured text run, links included. */
  --mw-accent-hover:   #12437F;
  --mw-accent-soft:    #E8F1FF;

  /* Light surfaces */
  --mw-bg:             #F6F8FB;
  --mw-surface:        #FFFFFF;
  --mw-surface-alt:    #EEF2F7;
  --mw-surface-hover:  #E8EDF3;
  --mw-border:         #D8E0E8;   /* Decorative: table rules, card edges. No contrast duty. */
  --mw-border-strong:  #74849A;   /* The boundary of an interactive control: >= 3:1. */
  --mw-text:           #0E1823;
  --mw-text-muted:     #5A6675;   /* Secondary text. Text-safe on every surface. */
  --mw-text-subtle:    #6B7787;   /* Metadata and disabled glyphs. Still text-safe. */

  /* Semantic — darkened from the source palette until each passes as text */
  --mw-success: #157F3C;  --mw-warning: #8A5300;
  --mw-danger:  #B3261E;  --mw-info:    #0B6E7F;

  /* Geometry */
  --mw-radius-sm: 6px; --mw-radius-md: 8px; --mw-radius-lg: 12px;
  --mw-space-1: 4px; --mw-space-2: 8px;  --mw-space-3: 12px;
  --mw-space-4: 16px; --mw-space-6: 24px; --mw-space-8: 32px; --mw-space-12: 48px;
  --mw-header-h: 48px; --mw-telemetry-h: 34px; --mw-row-h: 36px;
}

:root[data-theme="dark"], :root:not([data-theme="light"]) /* under prefers-color-scheme: dark */ {
  --mw-bg:            #0B1118;
  --mw-surface:       #111A24;
  --mw-surface-alt:   #172230;
  --mw-surface-hover: #1D2A39;
  --mw-border:        #32425A;
  --mw-border-strong: #5A6E90;
  --mw-text:          #F8FAFC;
  --mw-text-muted:    #A9B6C6;
  --mw-text-subtle:   #94A3B8;
  --mw-accent:        #6BA6F5;   /* On a dark ground the brand blue passes as text unaided, */
  --mw-accent-text:   #6BA6F5;   /* so the two accent tokens converge. */
  --mw-accent-hover:  #93BEF8;
  --mw-accent-soft:   #16283D;
  --mw-success: #4ADE80;  --mw-warning: #FBBF24;
  --mw-danger:  #F87171;  --mw-info:    #38BDF8;
}
```

**Two accent tokens, not one, and that is the point.** `#2F80ED` is the FreeWeight blue and it is
3.87:1 on white: it passes the 3:1 UI-boundary rule and fails the 4.5:1 text rule. Darkening the
whole brand to satisfy a rule that applies only to text would change the family's identity, so the
*text* variant darkens and the brand does not. On a dark ground the problem does not arise and the
two converge.

Measured ratios, both themes, against the two grounds text sits on:

| Token | Light: surface | Light: bg | Dark: surface | Dark: bg | Role, and the bar it must clear |
|---|---:|---:|---:|---:|---|
| `--mw-text` | 17.9 | 16.8 | 16.8 | 18.1 | Body text — 4.5 |
| `--mw-text-muted` | 5.9 | 5.5 | 8.5 | 9.2 | Secondary text — 4.5 |
| `--mw-text-subtle` | 4.6 | 4.3 | 6.8 | 7.4 | Metadata, disabled glyphs — 4.5 on a surface |
| `--mw-accent-text` | 6.1 | 5.8 | 7.0 | 7.6 | Link and accent text — 4.5 |
| `--mw-accent` | 3.9 | 3.6 | 7.0 | 7.6 | Fills, focus rings, chart series — **3.0**, never text |
| `--mw-border-strong` | 3.8 | 3.6 | 3.4 | 3.7 | The edge of a control — **3.0** |
| `--mw-border` | 1.3 | 1.3 | 1.7 | 1.9 | Decorative rules — **no requirement** |
| `--mw-success` | 5.1 | 4.8 | 10.1 | 10.9 | Status text and glyphs — 4.5 |
| `--mw-warning` | 6.3 | 6.0 | 10.5 | 11.4 | Status text and glyphs — 4.5 |
| `--mw-danger` | 6.5 | 6.1 | 6.3 | 6.9 | Status text and glyphs — 4.5 |
| `--mw-info` | 5.9 | 5.6 | 8.2 | 8.9 | Status text and glyphs — 4.5 |

`--mw-border` is the one token here with **no** contrast requirement, and it is deliberate: a
decorative table rule held to 3:1 becomes a cage. Anything a user can click, focus or drag uses
`--mw-border-strong`.

Chart palette (colour-blind-checked, order matters) — `--mw-chart-1` … `--mw-chart-6`:

```css
/* light */ #2F80ED  #0E8074  #6D3FD1  #8A5300  #B3261E  #157F3C
/* dark  */ #6BA6F5  #2DD4BF  #A78BFA  #FBBF24  #F87171  #4ADE80
```

A series colour is a UI boundary, not text, so each is held to 3:1 against its own ground — and to
being distinguishable from its neighbours under the three common colour-vision deficiencies. Where a
series is also **labelled in its own colour**, the label uses the text token, not the series token.
Colour is never the only thing separating two series (§5).

Per-application accent: FreeWeight `#2F80ED` (blue), LoadCoach `#14B8A6` (teal), IdeaPress
`#8B5CF6` (violet). Only the accent tokens change; every surface, text and semantic token is shared,
so the family reads as one system.

**Rules:** no hard-coded colours in application CSS or templates — tokens only. No colour defined
solely inside a media query. `body` always paints an explicit token background.

---

## 2. Typography

```css
--mw-font-ui:   Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
--mw-font-data: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
```

Fonts are vendored locally (Inter, with its licence file) or fall back to the system stack — no
network font fetch, ever.

| Role | Size | Weight |
|---|---:|---:|
| App name | 18–20 px | 700 |
| Page title | 22–26 px | 700 |
| Section title | 15–17 px | 650 |
| Body | 14 px | 400 |
| Table | 13 px | 400 |
| Caption / metadata | 12 px | 400 |
| Small label | 11 px | 600 |
| KPI value | 24–30 px | 650 |

The data font is used for model IDs, digests, hashes, timestamps, paths, token counts and raw
values. **Tabular numerals (`font-variant-numeric: tabular-nums`) on every metric** so live values
do not shift layout.

---

## 3. Application shell

```text
┌──────────────────────────────────────────────────────────────────┐
│ Logo │ primary navigation                    │ theme │ help │ ⋯ │  48 px
├──────────────────────────────────────────────────────────────────┤
│ CPU 22% 58C │ RAM 11.8/31.2 GB │ GPU 78% 61C │ VRAM 13.4/15.9 GB │  34 px
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                          page content                            │
└──────────────────────────────────────────────────────────────────┘
```

* The **telemetry bar is present on every page** of every application (it may be collapsed by the
  user; the preference persists). Unavailable readings show `—`, never `0`.
* Values update without layout movement (fixed-width fields, tabular numerals).
* Hovering or clicking the bar opens a detail popover: per-GPU values, clocks, fan, power limit,
  recent sparklines.
* Primary navigation stays visible on desktop; it collapses only when width genuinely requires it.
* Detail views open as routes or drawers, never as new top-level navigation entries.

---

## 4. Component set (MirrorWall)

Buttons (primary/secondary/ghost/danger, with loading and disabled states), inputs and selects with
labels and error text, checkbox/radio/switch, cards, tables, status badges, tabs, drawers, modal
dialogs, toasts, tooltips, progress bars and spinners, empty states, pagination, filter bars, key–value
metadata lists, code/JSON viewers with copy, the telemetry bar, and chart containers.

Rules:

* Application templates compose these macros; they do not re-implement them.
* Every interactive component: keyboard operable, visible focus ring, correct ARIA role, disabled
  state that is announced.
* State is expressed with `data-` attributes (`data-variant="primary"`, `data-status="running"`),
  not with utility-class sprawl.

### 4.1 Status vocabulary (identical across all three applications)

| Status | Colour token | Applies to |
|---|---|---|
| `queued` | muted | runs, jobs, stages |
| `preparing` / `warming` | info | runs |
| `running` | accent, animated only if motion is allowed | runs, jobs, stages |
| `completed` / `passed` | success | everything |
| `failed` | danger | everything |
| `cancelled` | muted | everything |
| `interrupted` | warning | runs, jobs |
| `skipped` | muted with a reason tooltip | tests, stages |
| `degraded` | warning | health components |
| `unsupported` | subtle `—` | measurements |

**Colour is never the only signal**: every status carries a label, and icons carry accessible names.

---

## 5. Data display rules

Inherited from the brand design system and generalized:

* Missing or unsupported values render `—` with a tooltip explaining why. Never `0`, never blank.
* Every number shows its unit; every metric can reveal its definition (tooltip or a linked glossary).
* Tables: sticky header, 36 px dense rows, sortable columns (sort applies to the **whole dataset**,
  not the visible page), configurable column visibility, horizontal scroll rather than truncation of
  meaning, and a row-count summary.
* Any headline metric is drillable to the raw record that produced it in at most two clicks.
* Charts: axis labels with units, units in tooltips, no truncated axes that mislead, no 3-D effects,
  no dual axes without an explicit legend, colour-blind-safe palette, and a text/table alternative
  for the key figures.
* Comparisons across an incomparable boundary (different benchmark version, different machine for
  performance metrics) are visually separated and labelled, never silently averaged.
* Long identifiers (digests, hashes, IDs) are truncated in the middle with a copy button and a full
  value on hover.

---

## 6. Interaction and states

Every view designs four states before it ships:

1. **Loading** — skeleton or progress, never a blank page; never a spinner for something that
   completes in under 200 ms.
2. **Empty** — explains what would be here and gives the action that creates it ("No runs yet —
   start one from the Run page" with a button).
3. **Error** — states what failed, why, and what to do next; shows the error `code` and the request
   ID for support; offers retry where retrying is meaningful.
4. **Populated** — the normal case, designed at both realistic and extreme data volumes.

Additional rules:

* Destructive actions always preview their effect ("this will delete 412 samples across 3 runs") and
  require explicit confirmation. Undo where feasible; a backup where not.
* Long operations report progress by SSE and survive a page refresh — the client reconnects and
  replays. A run's progress is never lost because a browser tab reloaded.
* Forms validate on submit (and on blur where cheap), show errors next to fields, keep user input on
  failure, and never lose a draft to a validation error.
* Optimistic UI is used only where the operation cannot fail; otherwise show the real state.

---

## 7. Accessibility

Target **WCAG 2.1 AA**. Non-negotiable:

* Semantic HTML: real `<button>`, `<table>`, `<nav>`, `<main>`, `<label>`; headings in order.
* Every form control has an associated label; icon-only controls have accessible names.
* Visible focus indicator on every focusable element (never `outline: none` without a replacement).
* Full keyboard operation: navigation, tables, drawers, dialogs, menus. Dialogs trap focus and
  restore it on close. `Esc` closes.
* Contrast ≥ 4.5:1 for body text and ≥ 3:1 for large text and UI boundaries, **in both themes** —
  verified by a test over the pairs the application actually renders, **each held to the bar for the
  role it is used in**, per §1's table. Not over the cross product of the palette: `--mw-accent` is
  a fill and `--mw-border` is a decorative rule, and a check that demanded 4.5:1 of either would be
  demanding the palette contradict itself. The list of rendered pairs lives in the test, where it is
  reviewable and where adding a pair is a visible change.
* `prefers-reduced-motion` honoured; no animation is required to understand state.
* Live regions for asynchronous updates (run completed, job failed) with `aria-live="polite"`.
* Charts are not the only representation of a critical figure.
* Skip-to-content link on every page.

---

## 8. Responsiveness

Primary target is a desktop at 1280 px and wider; the UI must remain usable at 1280×720 with no
clipping of primary controls, and must not break on a phone.

| Width | Behaviour |
|---|---|
| ≥ 1440 px | Full multi-column dashboards |
| 1280–1439 px | Full navigation; dashboards may drop to two columns |
| 768–1279 px | Navigation may collapse to icons; tables scroll horizontally; telemetry bar scrolls horizontally rather than disappearing |
| < 768 px | Single column; drawers become full-screen; primary actions stay reachable |

Functionality is **reorganized** at small widths, never removed.

---

## 9. Theme

* Three choices: System (default), Light, Dark.
* Dark mode is a designed palette, not an inversion.
* The choice is stored in `localStorage` (immediate, per browser) and, when the user is working in a
  configured application, mirrored into application settings.
* Switching applies without a page reload and re-themes charts at the same time.
* The initial theme is applied by a tiny inline script before first paint to avoid a flash.

---

## 10. Motion and iconography

* Transitions 120–180 ms, functional only: hover/focus, drawer, dropdown, theme, progress.
* No pulsing backgrounds, bouncing indicators, or decorative animation.
* Icons: simple 2 px line icons, rounded caps, inline SVG, vendored (Lucide-style). No icon font, no
  remote sprite sheet.

---

## 11. Content style

Concise, technical, neutral. Sentence case for headings and buttons. Verbs on buttons ("Start run",
not "OK"). No exclamation marks. Error text says what happened and what to do. Units always. Times
shown in the user's locale with the UTC value available on hover. Never anthropomorphize the model
("the model failed to return valid JSON", not "the model got confused").

---

## 12. Per-application information architecture

Shared shell, different content — this is deliberate and must not be homogenized.

| FreeWeight | LoadCoach | IdeaPress |
|---|---|---|
| Dashboard | Dashboard | Projects |
| Run | Jobs | Project workspace |
| Results | Queue | Workflow |
| Models | Models | Models / Backend |
| Database | Task profiles | Exports |
| Settings | Routing | Settings |
| | Benchmarks (imported evidence) | |
| | System | |
| | Settings | |

---

## 13. Acceptance checklist

A release candidate passes all of these:

- [ ] Light and dark themes present the same information hierarchy.
- [ ] Machine telemetry is visible (or deliberately collapsed) on every route.
- [ ] Unsupported values render `—` and never `0`.
- [ ] No headline metric is more than two interactions from its raw source.
- [ ] Tables stay usable at 20+ columns; column visibility is configurable; sort applies to the full dataset.
- [ ] Charts label units and re-theme correctly.
- [ ] Destructive operations preview their effect and require confirmation.
- [ ] Progress survives a browser refresh (SSE replay).
- [ ] Keyboard focus is always visible; every flow is completable without a mouse.
- [ ] Colour is never the sole indicator of state.
- [ ] Layout is correct at 1280×720 and at 375 px width.
- [ ] Metadata text is never below 12 px.
- [ ] Loading, empty, error and populated states exist for every view.
- [ ] The page works with JavaScript disabled for all read-only content (progressive enhancement).
- [ ] No network request leaves the machine (verified with the browser network panel offline).
- [ ] Contrast checks pass, in both themes, for every token pair the application renders, each against the requirement for the role it is used in (§1, §7).
