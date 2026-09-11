# Arc index — WP: every application tab, fully operating

**Written 2026-09-10, while W10 was running; not yet in the roadmap.** Rows WP1–WP6 run **after
W10** (operator, 2026-09-10). The first session to run WP1 pastes §4 below into
[`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) — after W10 has committed its
row-done edit (use the staged-hunk method in that file's history if another edit is in flight) —
in its first docs commit. This file stays as the index; each row has its own kickoff prompt.

## 1. The defect

Each application's tab in WeightRoomGym shows a left menu with every page
[`spec.md`](../../apps/weightroom/spec.md) §7.3 names. Only `Overview`, `Settings`, `Tokens`,
`Prompts` and `Database` are built. The other pages are inert text titled *not yet scheduled*.
`src/weightroom/web/rendering.py` (`_APP_PAGES`, `_PAGE_HREF`, `app_side_nav_stubs`) shows this.

| Application | Stubbed today |
|---|---|
| FreeWeight | Models · Runs · Results · Evidence · Goals · Adapters · Provider · Logs |
| LoadCoach | Models · Routing · Queue · Evidence · Adapters · Reliability · Providers · Logs |
| IdeaPress | Projects · Units · Workflows · Backends · Logs |
| PromptCadence | Trajectories · Approvals · Tiers · Tools · Ledger · Egress · Logs |

[`W3_HANDOFF.md`](../handoffs/W3_HANDOFF.md) §2.4 recorded the gap and the operator's decision of
2026-09-09 to fold these pages into W7–W9. Those rows did not build them, and no row since has
scheduled them. This arc closes the gap.

## 2. Decisions for the whole arc — every WP prompt links here; do not reopen

1. **Full parity** (operator, 2026-09-10). Each page does everything the application's own web
   UI does for that subject, **authoring included**: FreeWeight's goal wizard and calibration
   grading, IdeaPress's project editing, stage runs and unit revision, PromptCadence's trajectory
   submission. Each application binds loopback only (ADR-0126), so the LAN operator cannot reach
   the application's own page. A link to it is not a substitute.
2. **Provider and Providers are built here.** This reverses the W4 stub (`_PAGE_ELSEWHERE`,
   "edited on the application's own provider page") for the same loopback reason. The console
   edits through FreeWeight's `GET|PUT /provider` and LoadCoach's `GET /providers`,
   `PUT|DELETE /providers/{name}`. The application validates and writes its own file, per
   ADR-0117. Every key the application marks security-relevant re-authenticates (spec §7.4).
3. **The source rule is spec §7.3, the same for every page.** When the application is running and
   reachable, read from its `/api/v1`. When it is stopped, render listings from its database
   through the read-only reader, at a known revision only (`services/db_reader.py`,
   ADR-0123 rule 3). API-only actions are disabled, and the page shows the Overview's *start*
   form. A value nobody can read renders `—`, never `0` (ADR-0016). The footer names the source in
   the Overview's wording (`services/overview.py::_compose`). An unknown revision or a version
   outside the range degrades that page by name (`APP_VERSION_MISMATCH`, spec §19).
4. **The console calls `/api/v1` only.** It never scrapes an application's HTML routes and never
   re-implements an application's validation. The application refuses, and the page renders the
   refusal's own `code` and `message`. Some of an application's UI flows have no API route (for
   example IdeaPress `plan/edit`, `research`, `workspace`, `units/{key}/resume`; FreeWeight's
   `/goals/new/...` draft wizard and `/runs/{id}/grade`). For each one the row adds the API route
   **in that application's repository**, as its own commit, with a test and with `api.md` edited
   in `WeightRoom/docs` first and then mirrored. WI1 is the precedent. No row adds a raw database
   write for something an API should do.
5. **The page style is the design brief** ([`design.md`](../../apps/weightroom/design.md) §3–§5,
   §7), as the Overview, Database and Prompts pages already render it:
   * a `page-head` with the `h2`, the status pill and a right-aligned action group (ghost, ghost,
     primary);
   * figure cards for counts;
   * `table(density="dense")` with mono `data-kind` columns and uppercase 11 px headers;
   * status by dot and word;
   * `_log_pane.html` for every live stream;
   * htmx for swaps and SSE regions (ADR-0128), with behaviour in small ES modules on `data-`
     elements;
   * both themes, and contrast asserted for any new colour pair.

   The left menu orders the application's own pages first, then a 1 px rule, then the
   administrative pages (Settings, Provider(s), Tokens, Prompts, Logs, Database), per design brief
   §4. A component goes into MirrorWall only when it has a second consumer (ADR-0011). One consumer
   stays in WeightRoomGym, written package-shaped.
6. **No stub survives its row.** Each row adds its pages to `_PAGE_HREF` as they land. At the
   row's end, a test asserts `app_side_nav_stubs(<app>) == ()` for that application. The one
   exception is IdeaPress `Tokens`, whose title stays *has no API tokens*. When WP3 lands, delete
   `_PAGE_ELSEWHERE`.
7. **Every state-changing route passes every existing check.** It writes one `audit_log` row
   (spec §11 contract 2), passes CSRF and same-origin (ADR-0126 rule 5), has an entry in
   `tests/security/test_audit_routes.py::EXERCISES`, is covered by the redaction sweep and by
   W10's spec §14 registry, and has an entry in the OpenAPI snapshot. `api.md` is regenerated to
   match. W10's handoff names the commands.
8. **Streams are proxied.** An application's SSE (run events, job stream, trajectory stream,
   IdeaPress task stream, queue stream) reaches the browser through a console route that carries
   `Last-Event-ID` through. The pattern is `services/chat_loadcoach.py` and
   `services/chat_promptcadence.py`. Reuse the chat cards where the subject is the same
   (plan/step/tool/egress/approval).
9. **Text that comes from a model or an author reaches the DOM escaped.** This covers samples,
   unit content, trajectory outputs and rationales. Markdown renders through W5's sanitising
   renderer. The injection corpus W10 runs against chat runs against each new page that renders
   such text.
10. **One shared client for the applications' APIs.** WP1 writes it. It carries the bearer from
    `api_key_file` (`services.apps.bearer_token`), a timeout, and the application's error body
    passed through unchanged. Every new page uses it. Existing call sites move onto it only where
    the change is mechanical.
11. **Versions.** Follow the operator's instruction at kickoff. When there is none, make no bump
    and put the work under `[Unreleased]` in each repository touched. Never push, tag or publish.
12. **Model-assignment rules** are those in `model-assignment.md`. WP1, WP2, WP4, WP5 and WP6 are
    never run overnight.

## 3. Order

**W10 → WP1 → WP2 → WPC1 → WP3 → WP4 → WP5 → WP6.** (WPC1 was added by the operator on
2026-09-10, after WP1: PromptCadence's two API gaps, its System page, and a grant proven live —
`history/prompts/wpc1-promptcadence-api-gaps-system-page.prompt.md`.) WP1 is hard-first: it builds the page kit, the
client and the Logs page. WP3 comes before WP4: the goals pages sit on the runs and results
pages. WP2, WP3 and WP5 are independent of each other in substance. They still run one at a time,
because each edits `rendering.py`, the audit registry, the OpenAPI snapshot and `api.md`.
WP6 comes last.

## 4. Rows to paste into `weightroom-work.md` §1

```markdown
| **WP1** | **App pages I** → the page kit, the shared API client, a Logs page per application, PromptCadence's six pages (unreleased) | **Opus 5 · high** | W10 | The source rule, the stopped state and the footer as one reusable kit; the client; `_PAGE_HREF` and the menu rule; Logs × 4; Trajectories (list, submit, detail with turns/plan/intents/explanation, live stream, cancel), Approvals (grant/deny under `approve`), Tiers, Tools (with the isolation probe), Ledger (with entries), Egress. **Read:** `history/prompts/wp-app-pages-arc.prompt.md` §2, spec §7.3, `design.md`, `apps/promptcadence/api.md`, ADR-0049, `history/handoffs/W6_HANDOFF.md`, `history/handoffs/W10_HANDOFF.md`; `history/prompts/wp1-weightroom-app-pages-kit-promptcadence.prompt.md` | The kit shapes four rows, and an approval spends money. **Never overnight** |
| **WP2** | **App pages II** → LoadCoach: Models, Routing, Queue, Evidence, Adapters, Reliability, Providers (unreleased) | **Opus 5 · high** | WP1 | Discover/enable/warm; route explain and decision history with task profiles; queue pause/resume/drain and jobs submit/cancel/stream/explanation/feedback; evidence import; reliability windows and breakers; provider registrations edited through LoadCoach's API with re-auth; adapters from the sources LoadCoach actually has. **Read:** the arc index §2, `apps/loadcoach/api.md`, ADR-0055, ADR-0064, ADR-0074, ADR-0117, ADR-0118; `history/prompts/wp2-weightroom-loadcoach-pages.prompt.md` | Drain and provider edits change what PromptCadence and IdeaPress can do. **Never overnight** |
| **WP3** | **App pages III** → FreeWeight: Models, Runs, Results, Evidence, Adapters, Provider (unreleased) | Sonnet 5 · high | WP2 | Models with descriptor history and per-model results; runs start (through the capped `freeweight_suite_run` job), cancel, repeat, live events, test/sample drill-down; results query, compare with comparability verdicts, export; evidence and its export; machines; adapters from runtime profiles; the provider block. **Read:** the arc index §2, `apps/freeweight/api.md` §2–§8a, ADR-0119, ADR-0074, ADR-0135; `history/prompts/wp3-weightroom-freeweight-pages.prompt.md` | Pages over a tested API, in WP1's kit |
| **WP4** | **App pages IV** → FreeWeight Goals: authoring, calibration, grading (unreleased) | **Opus 5 · high** | WP3 | Goal list/detail/lint; create (wizard and pack), fork a starter, edit with the separating-change preview, delete with its preview, import/export; suggest-rules as proposals; judges and jury validation; calibration samples, resumable grading, the holdout run live, the report. **Read:** the arc index §2, `apps/freeweight/api.md` §3a, ADR-0032, FreeWeight's `goals`/`grading` templates; `history/prompts/wp4-weightroom-freeweight-goals.prompt.md` | Hash semantics and grades a person spends hours on. **Never overnight** |
| **WP5** | **App pages V** → IdeaPress: Projects, Units, Workflows, Backends (unreleased) | **Opus 5 · high** | WP4 | Projects list/create/edit/delete-preview, plan and plan edit, research, export, workspace; stage runs with the live task stream and cancel; units with provenance, history, revise and resume; workflows; backends with the round-trip test. **Read:** the arc index §2, `apps/ideapress/api.md`, `history/handoffs/WI1_HANDOFF.md`, `history/handoffs/M7_HANDOFF.md`; `history/prompts/wp5-weightroom-ideapress-pages.prompt.md` | The unit state machine is the part of IdeaPress found fragile. **Never overnight** |
| **WP6** | **Verification** → every tab walked, up and stopped, from a phone (no code) | **Opus 5 · high** · attended | WP5 | An independent session with permission to say *not ready*: every page of every application, running and stopped, against the application's own UI for parity; findings become rows, not fixes. **Read:** the arc index, every WP handoff, `history/prompts/m7-verification.prompt.md`; `history/prompts/wp6-weightroom-app-pages-verification.prompt.md` | Judgement on "fully operating" |
```

And under §3 of that file:

```markdown
* **WP1 before WP2–WP5** (operator, 2026-09-10) — the page kit and the API client are what the other four build on; **WP3 before WP4**; WP2–WP5 otherwise serialised only because they share `rendering.py`, the audit registry and the OpenAPI snapshot; **WP6 last**.
```
