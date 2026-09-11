# Kickoff — WP2: application pages II — LoadCoach

**Row:** WP2 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after WP1. Part of the WP arc ([`wp-app-pages-arc.prompt.md`](wp-app-pages-arc.prompt.md)).
**Ships:** unreleased. LoadCoach's Models, Routing, Queue, Evidence, Adapters, Reliability and
Providers pages, at full parity with LoadCoach's own UI.
**Component:** `~/ai/suite/WeightRoom`. `~/ai/suite/LoadCoach` for any missing API route (arc
index §2 item 4).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** the arc index §2; `history/handoffs/WP1_HANDOFF.md` (the kit, and use it: no page
here re-does the source rule, the footer or the stopped state); `apps/loadcoach/api.md` §1–§9.1,
§11; `apps/loadcoach/spec.md` (routing, queue, reliability, providers);
`apps/loadcoach/queue-and-scheduling.md`; ADR-0055, ADR-0064, ADR-0065, ADR-0074, ADR-0077,
ADR-0099, ADR-0117, ADR-0118, ADR-0132; `history/handoffs/H2_HANDOFF.md` (adapter pins) and
`history/handoffs/W8_HANDOFF.md` (the catalog already calls LoadCoach's `enabled`).
**Parity target:** LoadCoach's own `web/templates/{models,routing,queue,jobs,evidence,reliability,providers,task_profiles}`
and their routes. Inventory them before Gate A. The handoff's parity table starts from that list.

## Decisions already taken — do not reopen

* Everything in the arc index §2.
* **Gate A also fixes two existing defects** (operator, 2026-09-10; `history/handoffs/WP1_HANDOFF.md`
  §7 item 2 and §9). Both are in the kit this row builds on, and both land before any LoadCoach
  page.
  * **Figure cards stack.** MirrorWall's `card(…, kind="figure")` renders the label, the figure
    and the note on one line. Design brief §5 stacks them: the label, then the 22 px mono
    figure, then the 12 px note. Fix it in WeightRoomGym's own shell CSS, so the prepared,
    unpublished MirrorWall `0.3.1` does not change. Take screenshots of the Overview and
    PromptCadence's Ledger in both themes.
  * **Overview figures read the real status bodies.** `services/overview._STATUS_FIGURES` reads
    field names the applications' `GET /system/status` do not serve. PromptCadence serves
    `active_trajectories` and `pending_approvals` as lists, so *Executing* and *Planning* render
    `—` and *Pending approvals* renders `[]`. Check all four applications against their live
    bodies. Count a list, and let a missing field stay `—`. Pin each body with a recorded fixture.
* **Models.** `GET /models` shows declared capabilities, evidence summary, reliability, residency,
  `provider_name` and `is_remote`. `""` and `false` render as *not recorded*, never guessed.
  Detail is by ULID or prefix, never by canonical id (ADR-0024), and shows evidence per capability
  with its `match_state`, and the breaker. Actions: **Scan** (`POST /models/discover`),
  enable/disable, reusing W8's catalog call rather than a second one, and **Warm**, which links to
  the job it enqueued.
* **Routing.** An explain form over `POST /route` with the task profile, the overrides (model,
  runtime profile, adapter) and the classification. It renders every candidate and every
  rejection by its code. The decision history comes from the API when running, or from
  `routing_decisions`/`routing_candidates` when stopped. Task profiles list and detail sit here,
  since the menu has no entry of their own.
* **Queue.** Depth by state and class, oldest age, dispatch latency and starvation, live over
  `/queue/stream` if the API serves it. **Pause, resume and drain** each confirm with a sentence
  saying what stops, including that PromptCadence and IdeaPress route through this queue. Each is
  one audited action. Jobs: the list with LoadCoach's filters; the detail with attempts, routing
  summary, usage, timings, validation and output; the live stream with the thinking frame
  (ADR-0132) through the chat thinking block; cancel; explanation; feedback; and **submit** (the
  `POST /jobs` body with class, priority, `max_wait_seconds` and `idempotent`).
* **Evidence.** `GET /evidence` with its `summary`, and `GET /evidence/sources`. **Import** takes
  either an uploaded `benchmark.evidence_bundle` or the pull from FreeWeight. The pull passes
  FreeWeight's URL from the console's own `[apps.freeweight] base_url`. LoadCoach's allowlist
  decides, and `EVIDENCE_SOURCE_REFUSED` renders as itself.
* **Reliability.** The `7d`/`30d`/`all` windows, each value with its sample count or the reason it
  is absent; `reliability_factor` with its inputs; the regression verdict; the breaker state.
  Filtered by task and model. The breaker alert (W9) links here.
* **Providers.** List registrations (ADR-0055), create, edit (`PUT /providers/{name}`) and delete
  (`DELETE /providers/{name}`, previewed with what stops routing). Secrets are
  `api_key_env`/`api_key_file` references only, never a value on the page, in a log or in an audit
  row. A security-relevant key re-authenticates. `_PAGE_ELSEWHERE["Providers"]` goes.
* **Adapters.** LoadCoach serves no adapters endpoint. Adapters exist in the provider
  registrations, in the capability vocabulary (ADR-0064), in residency pins (H2), and in routing
  rejections (`adapter_classification_conflict`, `ADAPTER_NOT_FOUND`). Read LoadCoach's code to
  learn what is authoritative. The page shows every adapter with its base, classification
  (ADR-0065: local only), registration, pinned/resident state, and the routes that used or refused
  it. If no read API gives that, add `GET /adapters` to LoadCoach in its own commit, with
  `api.md` edited in `WeightRoom/docs` first. If choosing the source is architectural, write the
  ADR before the code.

## Gates

**Gate A — Models, Routing, Reliability.** Read and act, running and stopped, against recorded
fixtures and the LoadCoach fixture database. Commit.

**Gate B — Queue and jobs, Evidence.** Including pause, resume and drain against a fake LoadCoach,
with the confirmation tested, and the job stream proxy with the thinking frame. Commit.

**Gate C — Providers, Adapters.** Any LoadCoach API commit first, in LoadCoach, with its gate
green. The re-auth path tested. The secret redaction sweep covers the provider forms.
`app_side_nav_stubs("loadcoach") == ()`. `EXERCISES`, the §14 registry, the OpenAPI snapshot and
`api.md` updated. `CHANGELOG.md` updated. Commit.

## Demonstrate

On the reference machine:

1. Scan models, then warm one and follow its job to completion on the Queue page.
2. Explain a route with an adapter override and read the rejections.
3. Pause the queue and show that a chat message from WeightRoomGym waits. Resume it.
4. Import evidence from FreeWeight.
5. Edit a provider registration's non-secret key, and a security key with re-auth. Show the file
   diff LoadCoach wrote.
6. Stop LoadCoach and reload every page.

Take screenshots of each page in both themes.

## Finish line

Gate green in every repository touched, with the interpreter named. Coverage held. One commit per
gate. A handoff at `docs/history/handoffs/WP2_HANDOFF.md` with the parity table and what the
kickoff got wrong. The row marked done.
