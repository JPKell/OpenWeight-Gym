# Kickoff — WP1: application pages I — the page kit, Logs, PromptCadence

**Row:** WP1 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W10. It is the first row of the WP arc ([`wp-app-pages-arc.prompt.md`](wp-app-pages-arc.prompt.md)).
**Ships:** unreleased, no version bump unless the operator says otherwise at kickoff. It ships the
page kit every WP row builds on, the shared client for the applications' APIs, a Logs page for
each application, and PromptCadence's Trajectories, Approvals, Tiers, Tools, Ledger and Egress
pages at full parity with PromptCadence's own UI.
**Component:** `~/ai/suite/WeightRoom`. `~/ai/suite/PromptCadence` only if an API route is
missing (arc index §2 item 4).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).
**First docs commit:** if rows WP1–WP6 are not yet in `weightroom-work.md`, paste them from the
arc index §4. Stage only your hunk if another row's edit is in flight.

**Read first:** the arc index **§1–§3 in full**; `history/handoffs/W10_HANDOFF.md` (what 1.0.0
shipped, and the OpenAPI snapshot, `api.md` and §14-registry commands); [`spec.md`](../../apps/weightroom/spec.md)
§7.3, §11, §14; [`design.md`](../../apps/weightroom/design.md) §3–§5, §7;
`history/handoffs/W3_HANDOFF.md` §2.4 (the gap) and §2 (why the Overview reads its table from
the database); `history/handoffs/W6_HANDOFF.md` (the PromptCadence client, the cards, the
approve token); `apps/promptcadence/api.md` §1–§6 and `apps/promptcadence/spec.md` §17; ADR-0049,
ADR-0030, ADR-0069, ADR-0016, ADR-0128, ADR-0130.
**Code to read before writing any:** `web/rendering.py` (`_APP_PAGES`, `_PAGE_HREF`,
`app_side_nav`, `app_side_nav_stubs`), `web/routes/apps.py::app_page`, `services/overview.py`,
`services/db_reader.py`, `services/chat_promptcadence.py`, `services/costs.py`,
`templates/app.html`, `templates/_log_pane.html`, `templates/_chat_message.html`,
`tests/security/test_audit_routes.py`. Also read PromptCadence's own `web/templates/{trajectories,approvals,tiers,tools,ledger,egress}`:
they are the parity target.

## Decisions already taken — do not reopen

* Everything in the arc index §2.
* **The kit is extracted from what exists, not invented.** `app_page` already does the whole
  shape inline: the view, the side nav, the footer, the stopped-state start form, the
  version-mismatch notice. Extract it once: a `render_app_page(request, app, selected=…, …)`
  wrapper, a state partial shared by the Overview and every new page, and the footer's
  source wording from `overview._compose`. The Overview is then re-expressed on the kit and must
  render byte-for-byte as before. Its existing tests are the check.
* **The client** is one module (for example `services/app_api.py`): `get`/`post`/`put`/`delete`
  and an SSE proxy. It uses the pooled `httpx.Client`, the bearer from `bearer_token`, a timeout
  per call, and the application's error body carried through as a `SuiteError` with the
  application's own `code`. It never retries a non-idempotent call.
* **The menu** becomes two sections: the application's own pages, then a rule, then Settings,
  Provider(s), Tokens, Prompts, Logs and Database (design brief §4).
* **Logs, per application** is `GET /api/v1/apps/{app}/logs` history (since/until/level/q,
  cursor, 5 000 cap) above the live `_log_pane.html` over `/api/v1/apps/{app}/logs/stream`. The
  unified `/logs` page stays as it is.
* **Trajectories.** The list comes from the API with PromptCadence's filters, or from the
  `trajectories` table when PromptCadence is stopped. The detail page shows the document (state,
  budget, `window_wait`, `approver`), turns, plan, intents and explanation. The live stream
  renders through the chat cards (plan/step/tool/egress/approval), counting `egress.evaluated`
  frames. Cancel is one audited action. **Submit** is the `POST /trajectories` form with the
  classification, the tier pin, the tool allowlist, the budget, and the partial-pricing rule. A
  trajectory that a chat conversation started links to that conversation, and the reverse link
  exists too.
* **Approvals** reuses `chat_promptcadence`'s decide function and `token_can_approve`. It lists
  pending approvals with their age and exactly what granting releases (for example a
  `ceiling_raise` amount), with grant and deny on the list and on the trajectory. It is disabled
  by name when the token lacks `approve`. It adds no second approval path.
* **Ledger** is `GET /ledger` (today, per project, per trajectory) and `GET /ledger/entries`.
  Money is re-derived through `services/costs.py`, never read as a stored fact. Every money figure
  carries its unpriced count.
* **Tiers** show ceilings and availability, naming which of *registration* or *price* is unmet
  (ADR-0098). **Tools** show every configured tool, registered or withheld with the cause, and
  the isolation probe's rung and reason. **Egress** is `GET /egress-decisions` with verdict and
  target filters.

## Gates

**Gate A — the kit.** The client, `render_app_page`, the state partial, the footer, the two-section
menu, Logs × 4, and the Overview on the kit with unchanged output. Tests: client error pass-through
and timeout; running, stopped, unknown revision and version mismatch for one kit page against the
fixture databases and a fake application. Commit.

**Gate B — PromptCadence, read.** Trajectories (list and detail, stream proxy), Tiers, Tools,
Ledger and Egress, each running and stopped, each against recorded API fixtures and PromptCadence's
fixture database. Model-authored text in the injection corpus renders inert. Commit.

**Gate C — PromptCadence, act.** Submit, cancel, grant and deny. The `EXERCISES` entries, the
redaction sweep and the §14 registry. `app_side_nav_stubs("promptcadence") == ()`. The OpenAPI
snapshot and `api.md` regenerated. `CHANGELOG.md` under `[Unreleased]`. Commit.

## Demonstrate

On the reference machine, with PromptCadence and LoadCoach running:

1. Submit a trajectory from the Trajectories page and watch it stream.
2. Grant its approval from the Approvals page.
3. See the debit on Ledger and the decision on Egress.
4. Stop PromptCadence and reload every page: each renders from the database with the revision in
   its footer, and submit, cancel and grant are disabled beside a working *start*.
5. Open the Logs page of all four applications.

Take a screenshot of each page in both themes (a throwaway console on another port, Playwright
with the system Chrome). Report any criterion shown only against a fake as exactly that.

## Finish line

Gate green (`ruff format --check`, `ruff check`, `mypy src tests`, `lint-imports`, `pytest`, with
the interpreter named). Coverage held. One commit per gate. `git status --short` clean in every
repository touched. A handoff at `docs/history/handoffs/WP1_HANDOFF.md`: what the kit's API is,
for WP2–WP5, a parity table (PromptCadence UI route → console route → test), and what the kickoff
got wrong. The row marked done.
