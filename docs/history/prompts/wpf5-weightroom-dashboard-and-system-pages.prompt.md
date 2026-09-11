# Kickoff — WPF5: FreeWeight's Dashboard and System, LoadCoach's System, under their tabs

**Row:** WPF5 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Decided by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md) §3, *Pages with no console home*),
which judged the pages the operator sent to it on 2026-09-11. Runs after WP6. It is
independent of the other WPF rows, but it edits `rendering.py`, so it runs on its own or on a
branch under `weightroom-work.md` §3's parallel-row rules.
**Ships:** unreleased, no version bump.
- **Spec §7.3 amended:** FreeWeight's menu gains *Dashboard* and *System*; LoadCoach's menu gains
  *System*.
- **FreeWeight:** a read-only dashboard route on `/api/v1`, because the Dashboard is HTML-only today.
- **WeightRoomGym:** the three pages in the page kit.

**Components:** `~/ai/suite/WeightRoom` (spec, api docs), then `~/ai/suite/FreeWeight`, then
`~/ai/suite/WeightRoom` (pages).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** the arc index `history/prompts/wp-app-pages-arc.prompt.md` §2 (every rule applies
here); `WP6_HANDOFF.md` (the judgement); `WPC1_HANDOFF.md` §2 item 7 and §3 (the System page
precedent); `WP3_HANDOFF.md` §2 item 5 (which FreeWeight pages read only the API when it is
stopped); `apps/freeweight/api.md` §1; `apps/loadcoach/api.md` §1; spec §7.3.

**Code to read first:** FreeWeight's `web/routes/dashboard.py`, its template, and the service
behind it; FreeWeight's and LoadCoach's `web/routes/system.py` and `templates/system/index.html`
(the parity targets); WeightRoomGym's `services/promptcadence_pages.py` System reader and its
template.

## What WP6 found

* **FreeWeight Dashboard** (`/dashboard`, HTML only). It has filters by suite, model, machine and
  since. It shows summary figures: completed runs, models measured, samples stored, unsupported
  measurements, machines and the latest run. It also shows a model × suite heatmap of one headline
  metric from each latest completed run. Cells that span more than one machine or suite version are
  marked *separated*. No console page shows this cross-model view: Results is a metric query and
  Compare works per subject.
* **FreeWeight System** (`/system`). It shows the application, version and health, plus ten health
  components: database, provider, gpu_telemetry, machine, evidence, prompts, sandbox,
  external_benchmarks, goals and judges. The console shows only the Overview's status and a
  *JSON · health* link.
* **LoadCoach System** (`/system`). It shows the version, machine fingerprint, workers, dispatch
  latency, starving, active jobs and dispatch state, and five health components. It also shows the
  telemetry, resident models and circuit breakers. The console has breakers on Reliability and
  dispatch on Queue, but health components and workers appear nowhere.
* **FreeWeight Sources** (`/sources`) — **not added.** It is a read-only credit list of nine external
  benchmark adapters with their licences and pinned versions. None is installed, and the dataset
  pins are placeholders that refuse installation. Nothing on it is actionable from any interface.
  Revisit when an external benchmark can be installed.
* **IdeaPress System** — **not added** (WP5 §4): three health components, covered by the Overview
  and the doctor.

## Decisions already taken — do not reopen

* **Full parity with each application's own page** (arc index §2 item 1), in the page kit and the
  design brief's style.
* **The console calls `/api/v1` only** (arc index §2 item 4). FreeWeight's System and LoadCoach's
  System read `GET /health` and `GET /system/status`, which both applications already serve.
  FreeWeight's Dashboard needs an **additive** read route in FreeWeight: edit `api.md` first, mirror
  it, then add the route with a test and a refreshed OpenAPI snapshot. The route answers the
  summary and the heatmap cells, with FreeWeight's own *separated* marking. The console does not
  recompute them.
* **Stopped:** all three pages read only the running API, and say so beside the *Start* form (as
  PromptCadence's System page and FreeWeight's Results do). A value nobody can read renders `—`.
* **Menu:** *Dashboard* sits among FreeWeight's own pages, and *System* in the administrative
  section after the application's subjects (WPC1 §2 item 7). `app_side_nav_stubs` stays `()` for
  both applications.

## Gates

**Gate A — the spec and FreeWeight's API.** Amend spec §7.3 for the three pages and the two not
added, with their reasons. Edit `apps/freeweight/api.md` for the dashboard route and mirror it.
Implement the route in FreeWeight, tests first. Run FreeWeight's gate, naming the interpreter.
Commit in each repository.

**Gate B — the pages.** FreeWeight Dashboard with its filters, FreeWeight System, and LoadCoach
System, each tested running and stopped, with the injection corpus over any text the applications
return. Record fixtures from the live applications. Update the menu. Run the gate. Commit.

**Gate C — the demonstration.** On the reference machine, show each page beside the application's
own page over loopback, in both themes and at phone width, running and stopped. Commit the
handoff.

## Finish line

- The gates green, with the interpreter named, and coverage held; `git status --short` clean.
- `docs/history/handoffs/WPF5_HANDOFF.md` with a parity table for each page against the
  application's own page, and what this kickoff got wrong.
- The row marked done. Nothing pushed.
