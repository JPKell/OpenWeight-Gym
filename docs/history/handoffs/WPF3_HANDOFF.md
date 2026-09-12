# WPF3 Handoff — a cancelled trajectory resolves its approval requests

**Row:** WPF3 (`roadmap/weightroom-work.md`) · **Ran:** 2026-09-11, attended, wave 1 ·
**Model:** Claude Opus 5 · **Kickoff:**
`history/prompts/wpf3-promptcadence-cancel-resolves-approvals.prompt.md`

**Status: Gates A and B done, Gate C outstanding.** The operator held the live proof for the
wave's live-demo staggering (ADR-0119) on 2026-09-11. The row is **not** marked done, and
`weightroom-work.md` is untouched — see §6.

## 1. What shipped

| Repository | Branch | Commit | Gate | What |
|---|---|---|---|---|
| PromptCadence | `row/wpf3-cancel-approvals` | `3777d62` | A | A cancel from `awaiting_approval` resolves the pending request in its own write; the expiry pass sweeps a request whose trajectory is already terminal; the explanation document names the approver; tests written first; `api.md` and `lifecycle.md` mirrored byte-identical; CHANGELOG under `[Unreleased]` |
| WeightRoom | `row/wpf3-cancel-approvals` (worktree `~/ai/worktrees/weightroom-wpf3`) | `c7b2ea5` | B | `apps/promptcadence/api.md` §4 and `lifecycle.md` §8.2; the PromptCadence approval fixtures re-recorded; the test that a resolved request is never offered for a decision |

Nothing pushed or tagged; no version bump in either repository. The WeightRoomGym branch is **not
merged into `main`** — merge it after Gate C, rebasing onto `main` if WPF1 has landed (disjoint
files; `services/settings_forms.py` against `tests/fixtures/promptcadence/` and
`tests/integration/test_promptcadence_actions.py`).

**Gates run:**

* **PromptCadence** at `3777d62`, `.venv/bin/python` **Python 3.13.15**:
  `ruff format --check .` (200 files), `ruff check .`, `mypy src tests` (195 files),
  `lint-imports` (5 contracts kept), `pytest -m "not live and not performance"` →
  **1335 passed, 3 skipped, 11 deselected**; with `--cov` **92 %** total, above the 85 % floor and
  the same figure WPC1 recorded (`services/approvals` 81 %, `services/trajectories` 97 %,
  `services/explanation` 96 %, `services/views` 95 %). The OpenAPI snapshot did not move: no
  endpoint, field or enum value changed.
* **WeightRoom** at `c7b2ea5`, `.venv/bin/python` **Python 3.14.4**: the same gate →
  **1845 passed, 3 skipped, 10 deselected**, coverage **90.32 %**, held.

`git status --short` is clean in both repositories.

## 2. Decisions taken

### 1. The resolved request takes `expired`, with the cancel in `resolution_reason`

Not a new status, and therefore **no ADR**. The kickoff offered either; `expired` wins on three
counts. The status vocabulary is a released API's enum (`pending`, `granted`, `denied`, `expired`),
and a fifth member widens a contract every existing reader would have to learn — API standards §6.
`expired` already carries exactly the meaning wanted: *resolved without an answer, and never a
grant* (ADR-0049 rule 4), which is what a cancel leaves behind. And `resolution_reason` is the field
whose whole job is saying which way a request was resolved; it reads, verbatim from the recording:

> `the trajectory was cancelled from awaiting_approval, unanswered`

The request is **resolved, never deleted**: `GET /approvals?status=all` keeps it, and the console's
*Every request* table renders it with its reason. `resolved_at` is the cancel's own instant —
the same write — and `approver_token_id` stays `null`, because nobody answered it.

**No event is appended.** `trajectory.cancelled` is the state change; the request row holds no
state of its own and its resolution is that transition's consequence, recorded on the row. The
alternative was `approval.denied` with `timed_out=true`, which would have been false twice over: a
denial halts the trajectory (T9) and this one is cancelled, and no clock ran out. A reader that
wants to know what became of a request reads the request.

### 2. Every other exit that could leave a request open

A pending request exists **only** while its trajectory is `awaiting_approval`: it is created in the
write that parks the trajectory, and a second pending one for the same trajectory is refused
(ADR-0049 rule 6, `ApprovalService.request`). So the exits that could abandon one are exactly the
transitions out of that state, and the state machine says there are three:

| Exit | What it does with the request | Covered by |
|---|---|---|
| **T8** grant | resolves it `granted` | `test_manual_holds_a_planned_trajectory_and_a_grant_mints_every_step_under_the_approver` |
| **T9** deny | resolves it `denied`, halts | `test_a_denial_halts_with_the_denial_recorded_and_is_idempotent` |
| **T9** timeout (the expiry sweep) | resolves it `expired`, halts | `test_a_pending_request_expires_by_its_persisted_clock_and_a_timeout_is_never_a_grant` |
| **T14** cancel | **resolves it `expired`, unanswered** — this row | `test_a_cancel_resolves_the_request_the_trajectory_was_parked_on` |

The kickoff's other candidates cannot leave one open, and the reason is the same in each case —
they leave from a state that holds no request:

* **Recovery after a crash** (`services/worker.recover`, lifecycle §8.3) selects `planning` and
  `executing` only, by lease. `awaiting_approval` holds no lease, so recovery never sees a parked
  trajectory at all.
* **A halt** is T12 (`executing`) or T17 (`awaiting_window`); **a failure** is T7 (`planning`) or
  T13 (`executing`). None of those four source states can hold a pending request.
* **The worker's cancel at a turn boundary** (`_cancel_at_boundary`) runs from `executing` or
  `planning` — the lease-holding half of T14 — and so has nothing to resolve. It is deliberately
  left alone rather than given a defensive call.

`test_no_other_exit_from_awaiting_approval_leaves_a_request_pending` asserts that claim against the
transition table itself, so a new transition out of `awaiting_approval` fails the test rather than
quietly reopening the defect.

**One more thing was fixed for the rows that already exist.** The expiry pass now also resolves any
pending request whose trajectory is **already terminal**, with the trajectory's state as the reason
(`the trajectory is cancelled and never answered this request`). Nothing this build writes leaves
one, but the reference machine holds one that a build before this rule did: WP6's
`01M28YRRGKVNSZ03HZS5X3S3P1`. Without the sweep the fix would never have reached it — `expire()`
skipped it (its trajectory is not `awaiting_approval`) and would have gone on skipping it for ever,
so the console would have offered Grant and Deny on it until someone edited the database.
`test_the_sweep_resolves_a_request_a_terminal_trajectory_left_pending` puts the old shape back and
proves the pass heals it without moving the trajectory off `cancelled`.

### 3. The explanation carries the approver

Carried, not documented away. `trajectory.approver` was always `null` in the explanation document
while `GET /trajectories/{id}` answered `approver:weightroom` for the same trajectory, because
`ExplanationBuilder.compose_live` composed the block from `view_of(row)` alone and the lookup needs
the session (the row keeps the approving token's *id*, the field is its *name*, row W10). The three
reads in `TrajectoryService` already did `replace(view_of(row), approver=approver_of(...))`; the
explanation did not. It does now.

`approver_of` **moved from `services/trajectories.py` to `services/views.py`**, which is where the
loop and the trajectory service already share their row-to-value mapping precisely so that neither
imports the other. Importing it from the trajectory service was not possible:
`explanation → trajectories → loop → explanation` is a cycle, and Python says so at import time.

The golden explanation document did not move: its trajectory was approved by policy, so its
approver was `null` before this row and is `null` after it.

**Known gap, not fixed:** `GET /trajectories` (the listing) still answers `approver: null` for every
row, for the same reason — `list()` maps rows without the lookup. Fixing it is one query per row on
a 50-row page, which is why it was left; the record page and the explanation, which are where the
question is asked, both answer. `api.md` documents `approver` on the trajectory document without
distinguishing the listing. Worth a row if the listing ever grows an approver column.

## 3. What Gate C still has to prove

The kickoff's Gate C, on the reference machine, with the operator's own console:

1. Restart `promptcadence.service` onto this branch (the unit runs from `~/ai/suite/PromptCadence`'s
   own venv), so the fix and the sweep reach the operator's real database.
2. **Check the sweep did its work first:** `GET /approvals` should no longer list
   `01M28YRRGKVNSZ03HZS5X3S3P1`, and `?status=all` should show it `expired` with *the trajectory is
   cancelled and never answered this request*. That is the WP6 defect healed on the very rows that
   found it, and it needs no new trajectory.
3. Repeat WP6's path: submit from the console with a token budget of 1, let it park on the
   `ceiling_raise`, cancel from the trajectory record. The Approvals page then shows nothing
   pending, and *Every request* shows the request `expired` with the cancel as its reason.
4. Screenshots in both themes; the audit ids of the submit and the cancel into this handoff; the row
   marked done in `weightroom-work.md`.

**No model call is needed.** The one-token budget is refused at the pre-flight, before any
`generate` reaches LoadCoach — proved in §4 — so Gate C costs no GPU and, on the ADR-0119 ordering,
contends with nothing. LoadCoach must be running for the trajectory to be claimed, not to answer.

## 4. The proof that already exists, off the reference machine

Gate B's fixtures are a recording, not a hand-written document. A throwaway PromptCadence built from
this branch (`127.0.0.1:8788`, its own XDG tree under the session scratchpad, the operator's
`loadcoach.service` for its LoadCoach) was given WP6's exact path:

* `POST /trajectories` `{"bypass_planning": true, "budget": {"tokens": 1}}` →
  `01M29D4RKCKVG4D9G3ECD54GEA`, `queued`;
* it parked at `awaiting_approval` with `ceiling_raise` request `01M29D4RMN5S5N3G7YBGQV1MAS`,
  cause *the trajectory budget refuses the next step on tier local_fast: the tokens cap cannot admit
  it … the estimate was 5120 tokens*. **No LoadCoach `generate` was made**;
* `POST /trajectories/{id}/cancel` → `cancelled`;
* `GET /approvals` → `{"items": []}`;
* `GET /approvals?status=all` → the request, `expired`, `resolved_at 2026-09-11T23:34:36.034Z`,
  `resolution_reason` as quoted in §2;
* `POST /trajectories/{id}/deny` → `409 APPROVAL_INVALID_STATE`, *Request … is already expired* —
  the refusal now names the request's own resolved state rather than the trajectory's, and the
  console never renders the button that would produce it.

Those two listings **are** `tests/fixtures/promptcadence/approvals.json` and
`approvals-all.json` (the pre-existing recorded rows kept behind the new one, newest first). The
instance was stopped afterwards by environ-verified pid; `weightroom.service` and the four
application units were not touched.

## 5. What the kickoff got wrong

1. **"Refresh the OpenAPI snapshot if it moved."** It cannot move: the fix changes no endpoint, no
   field and no enum member — that was the point of choosing `expired`. The snapshot is byte-identical
   and its contract test passes unchanged.
2. **"A new status … check ADR-0049 and write an ADR for it."** Read as offering two equal options.
   They are not equal: one of them widens a released contract and the other uses a field that exists
   for exactly this. The row's decision cost nothing.
3. **The kickoff does not mention the rows already on the machine.** Fixing `cancel` alone would have
   left WP6's own request `pending` for ever — `expire()` skips a request whose trajectory is not
   `awaiting_approval`, which is precisely the shape a cancel leaves. The sweep in §2 is not in the
   kickoff and Gate C depends on it.
4. **"Cover each one with a test, or record why it cannot leave a request open"** (item 2) reads as
   though several exits need runtime tests. Only one does. The other exits are excluded by the shape
   of the state machine, and the honest test of a claim about the state machine is a test against
   the transition table, not five runs that each assert an absence.
5. **The live demo is not a live model call.** The wave-1 summary
   (`history/prompts/wave1-wpf3-summary.md`) says "the cancelled-trajectory demo is a live call
   through LoadCoach". The budget refusal happens at the pre-flight; §4 shows the whole path with no
   `generate`. Gate C still needs a slot on the operator's machine, but not the GPU.
6. **Item 5's wording** ("the explanation document … carries `trajectory.approver: null`") suggests a
   stale or cached document. It was neither: the live composition never looked the approver up at
   all, for any trajectory.

## 6. Left for the operator

* **Gate C**, as §3 sets out, when the wave's live slot is free. It is the only thing between this
  row and done.
* **The row is not marked done**, and `roadmap/weightroom-work.md` was deliberately not edited:
  it carried an uncommitted change on `main` when this row started (another session's staging), and
  three other wave-1 rows are editing the same file. Mark WPF3 done in the same edit that lands
  Gate C.
* **Merge order.** PromptCadence's branch stands alone. Rebase the WeightRoomGym worktree onto
  `main` before merging if WPF1 has landed.
* **Nothing pushed**, per the standing instruction.
