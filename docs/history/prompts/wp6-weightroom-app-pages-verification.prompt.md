# Kickoff — WP6: verification — every application tab, fully operating

**Row:** WP6 (Opus 5 · high · attended · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after WP4 and WP5 are both merged into main. It is the last row of the WP arc ([`wp-app-pages-arc.prompt.md`](wp-app-pages-arc.prompt.md)).
**Ships:** no code. A verdict, recorded verbatim, and new rows for whatever fails.
**Component:** `~/ai/suite/WeightRoom` for the handoff and the roadmap only.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** the arc index; every `WP*_HANDOFF.md`, and their parity tables in particular;
`history/prompts/m7-verification.prompt.md` and `history/handoffs/M7_HANDOFF.md` (the precedent:
an independent run with permission to say *not ready*); `W10_HANDOFF.md` §Gate D (how the
independent-device run was done); spec §7.3, §20.

## Decisions already taken — do not reopen

* **You have explicit permission to say *not ready*.** A page that renders but cannot do what the
  application's own UI does fails. A page shown only against a fake fails as *not demonstrated*.
* **You fix nothing.** Each finding becomes a row in `weightroom-work.md`, with a kickoff prompt
  in this file's shape, a model and effort. It does not become a patch in this session.
* **Parity is judged against each application's own UI.** Do not judge it against the WP
  handoffs' own tables, which are the builders' claims. Open each application's UI on the host
  over loopback beside the console.
* **Pages with no console home are judged here** (operator, 2026-09-11). These are FreeWeight's
  Dashboard, Sources and System, and LoadCoach's System (`WP2_HANDOFF.md` §4, `WP3_HANDOFF.md`
  §3). Each one becomes a row that amends spec §7.3, or is recorded as not needed and why.

## The run

On the reference machine with all four applications running, from **a phone on the LAN** and
from a desktop browser, in both themes:

1. **Menu.** Every application's left menu has no inert entry except IdeaPress `Tokens`.
2. **Parity.** For every page of every application, list each action the application's own UI
   offers on that subject, and do it from the console:
   * a PromptCadence trajectory submitted, approved and cancelled;
   * the LoadCoach queue paused, resumed and drained, then undrained by restart;
   * a provider edited and a security key re-authenticated;
   * a FreeWeight run started, followed and compared;
   * FreeWeight's adapters turned on and one adapter's page read with live data (operator,
     2026-09-11; WP3 could show only *Adapters are off*). From the console, set FreeWeight's
     `[adapters] directory` to `~/ai/models/adapters/llm`. Measure one adapter and its bare base
     on the `llamacpp` provider, one live load at a time. Then read that adapter's page: its base,
     its runs and results, and the deltas beside the base;
   * a goal forked, calibrated, graded across a reload, and exported;
   * an IdeaPress project created, planned, drafted, revised and exported.

   Record the application's audit trail and the console's `audit_log` row for each.
3. **Stopped.** Stop each application in turn. Every page renders from the database with its
   revision in the footer, every API-only action is disabled beside a working *start*, and
   nothing anywhere reads `0` where it should read `—`.
4. **Degradation.** Load an unknown `alembic_version` fixture and a version-mismatch application.
   Each degrades that application's pages by name and nothing else.
5. **Safety.** Put the injection corpus into a trajectory prompt, a goal criterion, a unit
   instruction and a project brief. Everything renders inert. No page shows a secret. A
   state-changing route that the audit test does not exercise is a failure.
6. **Performance.** Every new page's first paint stays within spec §15's page budget with the
   application running, measured on the reference machine.

## Finish line

`docs/history/handoffs/WP6_HANDOFF.md` with the verdict first and verbatim (*ready* or *not
ready*), then each numbered check with its evidence (screenshots, audit ids) and each finding
with the row it became. The rows added to `weightroom-work.md`, and `roadmap/README.md` updated
with the arc's status. One docs commit. Nothing pushed.
