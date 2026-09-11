# Kickoff — WP5: application pages V — IdeaPress

**Row:** WP5 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after WP4. Part of the WP arc ([`wp-app-pages-arc.prompt.md`](wp-app-pages-arc.prompt.md)).
**Ships:** unreleased. IdeaPress's Projects, Units, Workflows and Backends pages at full parity:
authoring, planning, research, stage runs, revision and export.
**Component:** `~/ai/suite/WeightRoom`. `~/ai/suite/IdeaPress` for the API routes its UI has and
its API lacks.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** the arc index §2; `history/handoffs/WP1_HANDOFF.md` (the kit and the stream proxy);
`apps/ideapress/api.md` in full; `apps/ideapress/spec.md` (the unit state machine, stages, gates,
research); `history/handoffs/M7_HANDOFF.md` (the unit that wedged), `M8_HANDOFF.md`,
`M1_HANDOFF.md` (research on ToolYard), `WI1_HANDOFF.md` (stranded units, and settings that apply
at the next stage start); ADR-0039 and ADR-0025 §3 (bare `token` frames).
**Parity target:** IdeaPress's own `web/templates/{projects,plan,units,workspace,export,backends}`
and their routes. Known UI-only routes: `GET /projects/{id}/plan`, `POST …/plan/edit`,
`POST …/research`, `GET …/workspace`, `POST …/units/{unit_key}/resume`, `GET /export/formats`.
Inventory all of them before Gate A.

## Decisions already taken — do not reopen

* Everything in the arc index §2.
* **Missing API routes go into IdeaPress first**, one commit per concern, each with tests and with
  `apps/ideapress/api.md` edited in `WeightRoom/docs` then mirrored. The console never posts to
  IdeaPress's HTML routes.
* **Projects.** List with status and content-type filters and a cursor. **Create** takes
  `title`, `content_type`, `workflow_id` (from `GET /workflows`), `brief` and `author_material`.
  **Edit** is `PUT`: the page says whether requirements recompile, and never recompiles silently.
  **Delete** shows IdeaPress's preview and offers archive-to-export first. It confirms by typed
  title and is audited. The detail page shows the plan summary, unit states and stage history.
* **Plan and research.** Run the plan and edit it, with IdeaPress's gates shown as gates. Research
  runs on ToolYard: show every tool call and its egress decision, as the PromptCadence cards do.
  It is never a silent fetch.
* **Stage runs.** `POST /projects/{id}/stages/{stage}/run` with IdeaPress's body, and the live
  task stream through the proxy: enveloped frames plus bare `token` frames, `unit.paused` and
  `stage.failed` rendered as states, not as errors. **Cancel** is honoured at the next model-call
  boundary, and the page says so until it lands. Because WI1 settings apply at the next stage
  start, the run form shows the effective values that stage will use.
* **Units.** List with state, version, requirement coverage and last validation. Detail with
  content (sanitised markdown) and full provenance. History of every version with attempts,
  validations, audits and critique verdicts. **Revise** with instructions, within IdeaPress's
  bounds. **Resume** a paused or stranded unit. A unit IdeaPress reports unrunnable says why and
  offers only what IdeaPress allows.
* **Export.** Formats from `GET /export/formats`. Download, or write to the project directory,
  showing where it was written.
* **Workspace** is at parity with IdeaPress's workspace page, whatever the inventory finds it to
  be.
* **Workflows** list and detail: stage order, gates, defaults and versions.
* **Backends.** Mode, reachability, capabilities, and the egress flag for remote backends.
  **Test** round-trips and shows latency, the model list and any version mismatch.

## Gates

**Gate A — IdeaPress API.** The missing routes, in IdeaPress, with its gate green (including
`WEIGHTSDB_REQUIRE_POSTGRES=1` if a migration is touched). Commit there, then a docs commit here.

**Gate B — Projects, Workflows, Backends.** Read and act, running and stopped, against fixtures
and IdeaPress's fixture database. Commit.

**Gate C — stage runs, units, plan, research, export, workspace.** The stream proxy tested with a
recorded IdeaPress task stream that includes a `unit.paused` and a `stage.failed`. Resume of a
stranded unit tested. The injection corpus is placed in a brief and in unit content, and must
render inert. `app_side_nav_stubs("ideapress")` leaves only `Tokens`. `EXERCISES`, the §14
registry, the OpenAPI snapshot and `api.md` updated. `CHANGELOG.md` updated. Commit.

## Demonstrate

On the reference machine:

1. Create a short project from a phone and plan it.
2. Run the draft stage and watch units stream.
3. Cancel one stage mid-run, then resume the unit.
4. Revise a unit with an instruction and read its history.
5. Test the backend.
6. Export as markdown.
7. Stop IdeaPress and reload every page.

Take screenshots in both themes.

## Finish line

Gate green in every repository touched, with the interpreter named. Coverage held. One commit per
gate. A handoff at `docs/history/handoffs/WP5_HANDOFF.md` with the parity table, the routes added
to IdeaPress, and what the kickoff got wrong. The row marked done.
