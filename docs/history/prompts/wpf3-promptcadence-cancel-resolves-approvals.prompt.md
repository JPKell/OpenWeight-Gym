# Kickoff — WPF3: a cancelled trajectory resolves its approval requests

**Row:** WPF3 (Opus 5 · high · **never overnight**) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WP6 ([`WP6_HANDOFF.md`](../handoffs/WP6_HANDOFF.md), finding 5). Runs after WP6. It is
independent of the other WPF rows.
**Ships:** unreleased, no version bump in either repository.
- **PromptCadence:** cancelling a trajectory resolves every approval request it still holds open, so
  no listing offers a decision nobody can make.
- **WeightRoomGym:** its PromptCadence fixtures re-recorded; the Approvals page shows no Grant or
  Deny for a request PromptCadence no longer lists as pending.

**Components:** `~/ai/suite/PromptCadence` first, then `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WP6_HANDOFF.md` finding 5; `WPC1_HANDOFF.md` §2 and §4 (the approvals listings,
the live gate); `apps/promptcadence/api.md` §4; `apps/promptcadence/spec.md` (the trajectory
lifecycle and approvals); ADR-0049; `W10_HANDOFF.md` §2 item 8 (where the approver is looked up).

**Code to read first:** PromptCadence's `services/trajectories.py` (`TrajectoryService.cancel`),
`services/approvals.py`, `web/routes/approvals.py`, and the state machine the cancel consults;
WeightRoomGym's `services/promptcadence_pages.py` (the pending list) and
`tests/fixtures/promptcadence/`.

## What WP6 saw on the reference machine (2026-09-11)

1. Trajectory `01M28YRRF5BBKP5PNMS49FRCY8` was submitted from the console with a token budget of 1.
   It reached `awaiting_approval` with the `ceiling_raise` request `01M28YRRGKVNSZ03HZS5X3S3P1`, and
   was cancelled from its record (console audit `01M28YRRZB79RQCN8Z3W6SC8DP`). Its events end
   `approval.requested`, `trajectory.cancelled`.
2. `GET /api/v1/approvals` still lists that request as `pending`, expiring 2026-09-12T19:23:03Z. The
   console's Approvals page renders it under *Pending*, with the ceiling fields, **Grant** and
   **Deny**.
3. **Deny** from the console answers PromptCadence's `APPROVAL_INVALID_STATE`: *Trajectory
   01M28YRRF5BBKP5PNMS49FRCY8 is cancelled, not awaiting_approval.* The console audit row is
   `01M29025ZAC5SBAWK58GD92J8X` (`trajectory.deny`, `refused`, `security: true`). The request stays
   `pending`.
4. `TrajectoryService.cancel` writes `trajectory.cancelled` and never touches the trajectory's
   approval requests.
5. Secondary: the explanation document of trajectory `01M28YRAS1Y1K89NCTC6J5HR9R` carries
   `trajectory.approver: null`, while `GET /trajectories/{id}` answers `approver:weightroom`.

## Decisions already taken — do not reopen

* **PromptCadence fixes it.** The console does not filter PromptCadence's pending list or guess
  which request is still decidable (arc index §2 item 4: the console never re-implements an
  application's validation).
* **A request is resolved, never deleted.** The *Every request* history keeps it, with the reason.
* **API standards §6 applies:** an existing caller keeps its answer, and any change to the status
  vocabulary is edited in `api.md` before the code and mirrored byte-identical.

## Decisions for this row — make each, and record it in the handoff

1. **Which status the resolved request takes.** Either `expired` with a `resolution_reason` naming
   the cancel, or a new status such as `cancelled`. A new value in a released API's enum widens a
   contract. If you choose one, check ADR-0049 and write an ADR for it.
2. **Every other exit that leaves a request open.** Enumerate them from the state machine: recovery
   after a crash, the expiry sweep, a halt, a failure. Cover each one with a test, or record why it
   cannot leave a request open.
3. **The explanation's approver** (item 5). Either carry it, or record why the explanation document
   and `GET /trajectories/{id}` differ.

## Gates

**Gate A — PromptCadence.**
1. Edit `apps/promptcadence/api.md` if the answer changes, then mirror it.
2. Write tests first: a cancel from `awaiting_approval` resolves the request; the pending listing
   no longer returns it; a grant or deny on it is refused naming its new state; the other exits
   from item 2.
3. Implement. Refresh the OpenAPI snapshot if it moved, and update the CHANGELOG under
   `[Unreleased]`.
4. Run PromptCadence's gate, naming the interpreter. Commit.

**Gate B — the console.** Re-record the PromptCadence fixtures from the restarted application. Add
a test that a request PromptCadence resolved is not offered for a decision. Run the gate. Commit.

**Gate C — the live proof.** Repeat WP6's path on the reference machine: a one-token budget, the
gate, cancel from the record. The Approvals page then shows nothing pending, and the history shows
the request resolved. Take screenshots in both themes. Commit the handoff.

## Finish line

- Both repositories' gates green, with the interpreter named, and coverage held.
- `git status --short` clean in both.
- `docs/history/handoffs/WPF3_HANDOFF.md`: the status chosen and why, the exits covered, the audit
  ids of the live proof, and what this kickoff got wrong.
- The row marked done. Nothing pushed.
