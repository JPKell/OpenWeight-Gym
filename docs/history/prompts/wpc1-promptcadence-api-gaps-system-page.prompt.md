# Kickoff — WPC1: PromptCadence's API gaps, its System page, a grant proven live

**Row:** WPC1 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after WP2. It precedes WP3 (operator, 2026-09-10). Part of the WP arc
([`wp-app-pages-arc.prompt.md`](wp-app-pages-arc.prompt.md)).
**Ships:** unreleased, no version bump in either repository.
- **PromptCadence:** every approval request, and egress decisions newest first, over its own API.
- **WeightRoomGym:** the Approvals history and the Egress page back on that API while PromptCadence
  answers; PromptCadence's **System** page under its tab; a grant and a denial demonstrated live.

**Components:** `~/ai/suite/PromptCadence` first, then `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:**
- `history/handoffs/WP1_HANDOFF.md` §2 item 1 (why two pages read the database today), §3 (the
  kit), §4 (parity; the missing System page) and §9 (these decisions);
- `history/handoffs/WP2_HANDOFF.md` (what the kit looks like after WP2);
- `apps/promptcadence/api.md` §1, §4, §6 and `apps/promptcadence/spec.md` (approvals, the lifecycle, budgets);
- `standards/api-and-contract-standards.md` §6 (cursor pagination), ADR-0049, ADR-0069, ADR-0098.

**Code to read first:**
- PromptCadence's `web/routes/approvals.py`, `web/routes/egress.py`, `web/routes/system.py`,
  `services/approvals.py`;
- its `services/console.py` (`system_report`) and `web/templates/system/index.html` (the parity target);
- WeightRoomGym's `services/promptcadence_pages.py` and `web/routes/promptcadence.py`.

## Decisions already taken — do not reopen

**From the operator (2026-09-10, `WP1_HANDOFF.md` §9):**

* **The API grows; the console stops working around it.** Both changes are **additive** and every
  existing caller keeps its answer:
  * `GET /approvals?status=all` without `trajectory_id` lists every request, newest first,
    cursor-paginated (limit clamped to 200).
  * `GET /egress-decisions` gains newest-first ordering and a cursor, as an opt-in parameter.
    Chat reads egress decisions per trajectory, and the default order there must not move.

  Choose the exact parameter names by API standards §6 and PromptCadence's existing listings
  (`GET /trajectories`), and record the choice.
* **The API change is edited in the docs before the code.** Edit `apps/promptcadence/api.md` in
  `WeightRoom/docs` first. Mirror it into PromptCadence's `docs/` byte-identical
  (`FreeWeight/scripts/sync_docs.py --check`, or `cmp`). PromptCadence's OpenAPI snapshot is
  regenerated and byte-tested. CHANGELOG under `[Unreleased]`.
* **The console's Approvals history and Egress page read the API while PromptCadence answers**,
  and the database only while it does not (spec §7.3, as every other page). The footnotes WP1 put
  beside those footers ("its API lists…") go. `promptcadence_pages.requests_db` and `egress_db`
  stay as the stopped readers.
* **PromptCadence gains a System page under its tab** (spec §7.3 amended on 2026-09-10). It sits
  in the administrative section and is at parity with PromptCadence's own System page:
  * `GET /health`'s components with their status;
  * `GET /system/status`'s active trajectories, pending approvals with their age, today's ledger
    position, the last recovery pass (resumed, finished, halted, failed, deferred) and the
    configured concurrency;
  * how PromptCadence authenticates, if its API says so. If not, link the Tokens page and record
    the gap.

  API only: while PromptCadence is stopped, the page says it reads only from the running API.
  Add `System` to `_APP_PAGES["promptcadence"]` and `_PAGE_HREF`, so PromptCadence's stubs stay
  `()`.
* **A grant and a denial are proven live on the reference machine.** Nothing on it raises an
  approval request by itself: its tiers are local and its policy raised none at W10 or WP1. Set a
  real gate up on purpose, by the least invasive route PromptCadence's own rules allow. The
  obvious one is a trajectory submitted from the console with a token budget small enough that
  continuing needs a `ceiling_raise`. Then grant it from the Approvals page with new ceilings, and
  watch it resume. Deny a second one with a reason, and watch it halt with that cause. If the only
  route is a configuration change, make it through the console's Settings page, revert it the same
  way, and record both in the handoff. Each decision's audit row is a `security` row.

## Gates

**Gate A — PromptCadence's API.**
1. Edit `api.md`, then mirror it.
2. Write tests first: the all-requests listing, its cursor and its clamp; egress newest-first with
   a cursor; the unchanged default order.
3. Implement, then refresh the OpenAPI snapshot and the CHANGELOG.
4. Run PromptCadence's gate, naming the interpreter.
5. Commit in PromptCadence, then a docs commit in WeightRoom.

**Gate B — the console.**
1. `pending`/`requests` and `egress` read the API while PromptCadence runs; the recorded fixtures
   are re-recorded from the live application once Gate A is running on the reference machine
   (restart `promptcadence.service`).
2. Build the System page with running and stopped tests, and the injection corpus over any text
   PromptCadence returns there.
3. Menu and stubs; CHANGELOG. Commit.

**Gate C — the live proof.** The grant and the denial above, screenshots of the Approvals page,
the resumed record and the halted record, both themes (throwaway console on `:8779`). Restart the
operator's `weightroom.service` once the code is committed. Commit the handoff.

## Finish line

- Both repositories' gates green, with the interpreter named, and coverage held.
- One commit per gate; `git status --short` clean in both.
- `docs/history/handoffs/WPC1_HANDOFF.md`: the parameter names chosen, the gate that was set up
  and how it was undone, the audit ids, and what the kickoff got wrong.
- The row marked done. Nothing pushed.
