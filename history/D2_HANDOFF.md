# D2 — PromptCadence Phase 3 (LoadCoach client, bypass loop, events, recovery) — handoff

**Row:** D2 of `docs/roadmap/outstanding-work.md` §1. **Model:** Fable 5.1 · xhigh, attended.
**Repository:** `/home/jpk/ai/suite/PromptCadence`, branch `main`, six commits on top of
`752966f`, **not pushed**. **Docs:** one commit in `/home/jpk/ai/suite/docs` (`9edec2f`), **not
pushed**. **Rides:** `promptcadence 0.9.0b0` at M11 — no version bump, no tag, no publish.
**Date:** 2026-09-03.

Phase 3's goal — *a bypassed trajectory executes end to end, no tools, no budget yet, durably and
observably* — is met against the fake. Against a real LoadCoach it is met **only for a tier whose
task profile validates a JSON Schema**, because of the finding in §2, which is the most important
thing in this document.

---

## 1. Gate results

Run from `/home/jpk/ai/suite/PromptCadence`, interpreter `PromptCadence/.venv/bin/python`,
**Python 3.13.15**, pytest **9.1.1**. There is no `python3.12` on this machine.

```bash
cd /home/jpk/ai/suite/PromptCadence
.venv/bin/ruff format --check .            # 81 files already formatted
.venv/bin/ruff check .                     # All checks passed!
.venv/bin/mypy src tests                   # Success: no issues found in 78 source files
.venv/bin/lint-imports                     # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                           # 704 passed, 2 skipped, 1 deselected, 2 warnings
.venv/bin/python -m pytest -q -p no:randomly
                                           # 704 passed, 2 skipped, 1 deselected (same, ordered)
.venv/bin/python -m pytest -m contract -q  # 18 passed
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                           # TOTAL 92%  (floor 85%)
```

**Legs that did not run here, stated plainly.**

* **The live journey** (`tests/live/test_loadcoach_journey.py`, `-m live`) — the *"against a real
  local LoadCoach"* half of acceptance criterion 1. It is the `1 deselected`. No LoadCoach runs on
  this machine. It asserts `completed` and is **expected to fail** against LoadCoach `01170a7` on
  a free-text tier, with the cause printed verbatim (§2). It did not run, so it did not pass.
* **The two PostgreSQL legs** (`tests/integration/test_migrations.py`, marked `integration`) —
  the `2 skipped`. Migration `0003` is a plain `add_column`/`create_index` on `trajectories`
  with a `server_default=false()` for the NOT NULL flag; parity passes on SQLite. The `db-matrix`
  CI job runs the PostgreSQL parity check on push.
* The kill −9 tests **did run** — real `SIGKILL` on a real child process, in the default suite.

The two warnings are the pre-existing Starlette/anyio deprecations from Phase 1.

---

## 2. The finding: LoadCoach renders no `finish_reason` on the wire

Spec §11 contract 6 (the advance contract): *a step completes only on a declared `finish_reason`
of `STOP` or a schema-validated structured result; `LENGTH`, `ERROR` and absence are never read as
success.* The kickoff named the truncated-answer-flowing-onward case as this row's quiet failure.

**LoadCoach `01170a7` records the provider's `finish_reason` on every attempt
(`job_attempts.finish_reason`, `AttemptRecord.finish_reason`) and renders it nowhere** — not in
`ExecutionOutcome.as_json()` (the `/generate` body), not in `job_document()` (the replayed-key
and `GET /jobs/{id}` body), not in `attempts[]`. api.md §4's example carries none. Verified in
LoadCoach's source, not assumed.

Consequences, all deliberate:

1. The client reads `output.finish_reason` **when a response carries it** (the location proposed
   below) and reports `None` otherwise. The fake **never emits it**, because LoadCoach does not.
2. `decide_finish` treats absence as absence: **a halt** with the cause on the row —
   *"LoadCoach's response declared no finish_reason and performed no schema validation; a turn
   cannot complete on an undeclared finish (spec §11 contract 6)"* — error code
   `LOADCOACH_ERROR`. Never a completion, never a silent continuation.
3. The only declared success on today's wire is contract 6's second clause: LoadCoach's
   `validation.checks[]` carrying a passed `json_schema` check (kind name from
   `validate_schema`). A `length` check passing is **not** a schema validation — `tools.agent`'s
   shipped policy is `max_output_chars` only, so `validation.performed=true, passed=true` on a
   free-text profile says nothing about completeness and is not read as one.
4. So: **a free-text tier halts on its first turn against real LoadCoach today**; a tier whose
   profile validates a schema completes. The e2e journey and the kill tests use a
   schema-validating profile for the default tier; a second e2e test asserts the free-text halt
   reads as a halt.

**The one-line LoadCoach fix, proposed (operator decision, LoadCoach row).** Render the declared
reason at `output.finish_reason` in both `ExecutionOutcome.as_json()` and `job_document()`
(`record.finish_reason` is already on the attempt row; `ModelRack.FinishReason` values are
`stop|length|tool_calls|content_filter|cancelled|error|unknown`), and add the field to api.md
§4's example. PromptCadence's parser already reads that location; `unknown`, `content_filter`
and `cancelled` are reported as undeclared reasons and halt with the string named. The
job-document half matters too: a turn reconciled after a crash is read from the job document,
which also carries no validation `checks`, so today a reconciled turn can never complete
(`test_kill_minus_nine_after_the_response_…` asserts exactly that halt, with the cause naming
the reconciliation). Docs amended: spec §11 contract 6 now records the obligation; LoadCoach's
own api.md was **not** amended to claim a field it does not serve.

---

## 3. What was built

| Where | What |
|---|---|
| `infrastructure/db/migrations/versions/0003_trajectory_leases.py` | `lease_owner`, `lease_expires_at`, `cancel_requested` (NOT NULL, server default false), `error_code` on `trajectories`, plus an index on `(status, lease_expires_at)`. Head is `0003`. |
| `domain/turns.py` | `decide_finish` (contract 6, golden `tests/golden/finish_decisions.json`, every cell of reason × schema × tools × undeclared), `TurnStarted`, `TurnCompleted`. |
| `domain/errors.py` | `TrajectoryNotFoundError`, `TrajectoryNotCancellableError`, `LoadCoachUnavailableError`, `LoadCoachError`, `CompactionFailedError`, `SchemaVersionUnsupportedError`, `ProjectUnknownError`, `ToolNotFoundError`. |
| `infrastructure/loadcoach.py` | `LoadCoachClient` over an injected `httpx.Client`: `version`, `system_status`, `models`, `task_profiles`, `task_profile`, `route`, `generate`, `list_jobs`, `job`, `cancel_job`, `find_job`. `parse_generation` (strict), `token_count_from_wire`, `map_error`, `LOADCOACH_CODE_MAP`. `X-Client-Name: promptcadence` on every request; `X-Request-ID` propagated from the correlation context. |
| `services/loadcoach_surface.py` | `ProviderSurface` from `/models`; `resolve_subject` (contract 4): LOCAL iff the response's provider kind is the one configured kind, REMOTE otherwise, refuse when unverifiable. |
| `services/events.py` | `TrajectoryEventSink.write()` (ADR-0044), `EventWriter.append`, `events`, `replay`, `TrajectoryEventSource` for MirrorWall's `sse_response`, `TERMINAL_EVENTS`. |
| `services/views.py` | `TrajectoryView`, `TurnView`, `view_of`, `declaration_of` — shared by the service and the loop. |
| `services/trajectories.py` | `TrajectoryService.submit` (T1), `get`, `resolve` (id prefix), `list` (cursor), `turns`, `events`, `cancel` (T14, two halves). |
| `services/loop.py` | `BypassGate`, `TierRouter`, `LoopController` (`next_queued`, `claim`, `renew_lease`, `run`, `cancel_in_flight`, `reconcile`, `fail_planning`), `RunSignals`, `LeaseLost`. |
| `services/worker.py` | `recover()`, `RecoverySummary`, `LeaseKeeper`, `TrajectoryWorker` (pool of `max_concurrent_trajectories` threads, startup recovery, periodic reaper, `wake()`). |
| `services/runtime.py` | Owns the sink, the service, the client and the worker; `start()` from the lifespan; `loadcoach_http` injectable. |
| `web/routes/trajectories.py` | `POST /trajectories` (202), `GET /trajectories`, `GET /trajectories/{id}`, `GET /trajectories/{id}/turns`, `POST /trajectories/{id}/cancel` (202/409), `GET /trajectories/{id}/stream` (SSE, `Last-Event-ID`). `web/app.py` maps the new codes to statuses; `/system/status` reports active trajectories and the last recovery. |
| `cli/commands/trajectories.py` | `promptcadence run` (client mode, `--follow`, `--json`), `trajectory list\|show\|cancel\|wait`; exit codes 0/5/6 by terminal state, 4 when no server answers, 2 for a refused request. |
| `tests/fakes/loadcoach_app.py` | The fake LoadCoach (§5). |
| `tests/contract/` | The I10 contract tests and the vendored snapshot `loadcoach_openapi.json` (sha256 `3412b1f6…0c6`, LoadCoach `01170a7`, file last changed at `0963646`). |
| `tests/integration/test_recovery.py` | The kill −9 tests (§4). |
| `tests/e2e/test_bypass_journey.py` | Acceptance criterion 1 over HTTP and the CLI, SSE replay. |
| `tests/live/test_loadcoach_journey.py` | The live half. |

**What executes per turn, in order.** Boundary checks (cancel flag, lease) → `max_turns` →
`TierRouter.resolve` → `turn.started` (own write; `turn_id` = idempotency key) → `POST /generate`
with the thread as `messages` (the caller's task is turn 1, verbatim; PromptCadence sends no
prompt text of its own, so no prompt record is needed) → `resolve_subject` → `decide_finish` →
`TurnFacts` → `compare()` → **one write**: the assistant turn row, `turn.completed`, every
deviation as a row and a `deviation.detected` event, and the terminal transition with its event.

**Deviations are recorded and acted on** (a small, honest slice of Phase 6): a `violation` halts
`DEVIATION_HALTED`; a drift whose disposition is `continue_recorded` is recorded and the turn's
own verdict decides; a drift whose disposition is `scoped_reapproval` or
`refused_not_reapprovable` halts naming the disposition and *"scoped re-approval is not available
before Phase 7"*. `compare()` has no mode branch; the loop calls it exactly as the planned path
will.

**A planned trajectory is claimed and failed**, T2 then T7 in one write, cause *"planning is not
available before Phase 7; submit with bypass_planning=true…"*, code `PLAN_DRAFT_FAILED` — rather
than queued forever with no stated reason. G1 replaces this with the planner.

---

## 4. Recovery as implemented, and how ADR-0044 is proven

**Leases.** T3 sets `lease_owner=<host>:<pid>/<thread>` and `lease_expires_at=now+lease_seconds`.
`LeaseKeeper` renews every `lease_seconds/3` by compare-and-set on `(id, status=executing,
lease_owner)` and reads `cancel_requested` in the same transaction. **Every write the loop makes
to the trajectory row is a CAS on the owner** (`_owned_cas`); a write that affects zero rows
raises `LeaseLost` and the loop stops without committing — `test_a_lost_lease_fences_every_write`.

**The mechanism for "a known LoadCoach job" (lifecycle §8.3, now written into the doc).** The
`turn.started` event is written *before* the call and carries the `turn_id`, which is the
request's `idempotency_key` under `X-Client-Name: promptcadence`. After a crash, a `turn.started`
with no turn row names the in-flight work; `LoadCoachClient.find_job(key)` pages
`GET /jobs?source=promptcadence` (newest first) and matches `idempotency_key`. The loop never
re-POSTs `/generate` with the old key to find out, because after `queue.idempotency_ttl_hours` a
re-POST would start new work and `/generate` cannot tell a replay from a fresh execution.

**`reconcile()` outcomes**, per `executing` trajectory with a dead or expired lease:

| Found | Action | Outcome |
|---|---|---|
| no dangling `turn.started` | re-claim, `trajectory.recovered(outcome=resumed)` | `RESUMED`, the loop runs on |
| job in a non-terminal state | `POST /jobs/{id}/cancel`, re-claim, `recovered(cancelled_in_flight_job:<id>)` | `RESUMED`, a fresh turn |
| job `completed` | re-claim; the job document is parsed and recorded as the turn in one write with `turn.completed`, `recovered(reconciled_completed_job:<id>)` and the verdict's transition | `FINISHED` or `RESUMED` |
| job `failed`/`cancelled` | re-claim, `recovered(job_<state>:<id>)` | `RESUMED`, a fresh turn |
| no job holds the key | T12 `halted`, cause `recovered_after_crash: …` | `HALTED` |
| LoadCoach unreachable | nothing written; the next pass retries | `DEFERRED` |

Startup takes over every lease not under this process's prefix (single-process design: any
other owner is gone); the running reaper (every `lease_seconds`) takes over only *expired* ones.
A `planning` lease found at recovery is T7 with the cause (no planner to redraft). Recovery is
idempotent (`touched == 0` on a second pass, asserted).

**The kill −9 tests** (`tests/integration/test_recovery.py`) serve the fake by uvicorn on a
loopback port from the test process and spawn a child that submits, claims and runs a
trajectory over a real socket:

* **in flight** — the fake holds the job; the parent `SIGKILL`s the child once the fake reports
  the job in flight; recovery cancels the job (`cancel_requested`, then `cancelled` when the
  handler is released), resumes, and the next turn completes. Asserted: one assistant turn, two
  jobs (one cancelled, one completed), nothing in flight, the event sequence including
  `trajectory.recovered` with the cancelled job's id.
* **after the response, before the commit** — a subclass of the client kills the process
  (`os.kill(getpid, SIGKILL)`) the instant `/generate` returns; recovery finds the completed job
  by its key and reconciles it into the turn row. Asserted: **one job** (no second execution),
  one assistant turn carrying that job id and its output, `recovered(reconciled_completed_job)`,
  and — today's wire — the halt named in §2, not a completion.

**ADR-0044, asserted rather than honoured.** `TrajectoryEventSink.write()` yields one session and
one writer; `test_a_crash_between_the_state_change_and_its_event_leaves_neither` changes the row,
flushes it inside the transaction, then appends an event whose body raises: the state is back to
`queued`, the events table has only the original row, and the broker subscriber saw nothing.
`test_publication_happens_only_after_commit` polls the subscription inside the transaction
(nothing) and after it (the event). Sequences are allocated inside the writing transaction from
the stored maximum after a flush, so two appends in one write are dense.

---

## 5. For E4 and F1 — the fake LoadCoach, and every place it differs from the real thing

`tests/fakes/loadcoach_app.py`. Sources: api.md §§1-5 and §10-11; LoadCoach `01170a7`'s
`ExecutionOutcome.as_json`, `job_document`, `post_cancel`, `list_jobs`, `_STATUS_BY_CODE`,
`validate_output`. The unit test `test_the_wire_dump_matches_api_md_example_keys` asserts the
fake's `/generate` body has exactly api.md §4's top-level and `usage` keys.

**Models (trust these).**

* `GET /version`, `/health`, `/system/status`, `/models`, `/task-profiles(/{id})`, `POST /route`,
  `POST /generate`, `GET /jobs` (`source`/`state` filters, `limit`, opaque cursor, newest first),
  `GET /jobs/{id}`, `POST /jobs/{id}/cancel` (202 `{job_id, state, already}`; 404
  `JOB_NOT_FOUND`; 409 `JOB_NOT_CANCELLABLE`).
* Idempotency exactly as api.md §4: scoped per `X-Client-Name`; a repeated key returns the
  **original job's document** (the job-document shape: `state` present, `validation` without
  `checks`) and never executes twice; a still-running original is waited for.
* `usage` in **both wires**: `Wire.INTERIM` (default — every real adapter until row H2: cache
  classes `"unsupported"`) and `Wire.POST_MODELRACK_070` (`0` or a count). `thinking_tokens` is
  `"unsupported"` in both. `input_tokens`/`output_tokens` are `null` when a script says
  unreported. **F1: build the estimator against `Wire.POST_MODELRACK_070` and let the interim
  wire take the `UNSUPPORTED` branch** (C6_HANDOFF §6).
* `validation` derived from the registered profile's policy the way `validate_output` does:
  `length` for `max_output_chars`; `json` → `json_schema` (scripted `schema_passes`) →
  `required_fields` for a schema profile. Helpers: `text_profile(id)` (the shipped `tools.agent`
  shape) and `schema_profile(id)` (the shipped `structured.extract` shape).
* Held generations (`ScriptedGeneration(hold=Event)`) and `delay_seconds`; scripted errors with
  LoadCoach's own HTTP status per code; `fake.jobs`, `fake.in_flight()`, `fake.jobs_with_key()`,
  `fake.requests` (every body received, `exclude_unset`).
* The registry entry (`GET /models`) with `provider_kind`, the source of the provider surface.

**Stricter than LoadCoach (deliberate).**

* `X-Client-Name` is required on every request but `/version` (400 `VALIDATION_ERROR`).
  LoadCoach accepts an anonymous loopback caller; recovery finds jobs by `source=promptcadence`,
  and a dropped header would pass every other test while making that lookup return nothing.
* `idempotency_key` is required on `/generate`, for the same reason.
* No default profile registry: a task profile nobody registered is `TASK_PROFILE_NOT_FOUND`.

**Looser than, or not modelling, LoadCoach (read before trusting).**

* **`finish_reason` is never emitted** (§2). When LoadCoach renders it, teach the fake in the
  same row and drop the "absence halts" e2e assertion for the default tier.
* Cancellation takes effect at once; LoadCoach honours it within one stream chunk, or only at
  completion for a non-streaming provider (`cancellation_deferred_to_completion`). The fake
  answers a cancelled `/generate` with the cancelled **job document** (200); LoadCoach's code
  raises `GenerationCancelled` on that path while its spec §13 says "200 with a cancelled job" —
  the client accepts both (any `status != completed` is not a finished turn; the code maps to
  `LOADCOACH_ERROR`). Recorded as an open LoadCoach question.
* No routing: one scripted model serves everything, `/route` returns a minimal explanation, no
  evidence, scoring, fallback, corrective retry, circuit breaker. `attempts` is one entry unless
  scripted. `is_remote` is nowhere on the wire — as in LoadCoach.
* No auth, rate limiting, admission (`QUEUE_FULL`/`INSUFFICIENT_RESOURCES` only when scripted),
  `/generate/stream`, `/jobs/{id}/stream`, retention sweep, feedback, or idempotency TTL.
* Timestamps, priority and lease blocks in the job document are plausible constants.

**What I10 pins and what it cannot.** The snapshot types every LoadCoach *response* as
`additionalProperties: true` and lists only FastAPI's own statuses, so the contract tests pin:
every path/method the client and the fake use; the fake's `GenerateBody`/`RouteBody` mirrors
equal the snapshot's schemas property-for-property with `additionalProperties: false`; every body
the client can send is accepted; the fake refuses `constraints`/`priority` (which api.md §4's
*example* shows and the schema forbids); the prompt forwarded equals the prompt sent. Response
shapes are pinned by transcription, not by the snapshot. `SNAPSHOT_SHA256` names which copy.

---

## 6. Decisions made where a document left an edge

1. **Absence of `finish_reason` halts** (§2). Spec contract 6 says "handled explicitly"; the
   only explicit handling that is not a success is a halt with the cause.
2. **`is_remote` is resolved by identity from `/models`**, not from `/system/status` (C4 §10
   named it; it carries no provider information). Egress LOCAL iff the response's kind equals
   the one registered kind; a foreign kind is REMOTE (conservative → `tier_violation` on a local
   tier); an empty registry, an unknown kind, or several kinds refuses (`subject_unverifiable`).
   `has_remote_provider` is `False` by construction until LC-E1 carries provider identity.
3. **The turn id is the idempotency key** and `GET /jobs?source=` is the reconciliation lookup
   (§4) — written into lifecycle §8.3.
4. **No `waiting` state exists** in lifecycle §8.1, so an unreachable LoadCoach mid-turn is T13
   `failed` with `LOADCOACH_UNAVAILABLE`, after `find_job`+`cancel` of any job the request may
   have started. Written into spec §13.
5. **The error map is complete** (`LOADCOACH_CODE_MAP`, spec §13 amended): `TASK_PROFILE_NOT_FOUND`
   → `TIER_UNAVAILABLE(reason=task_profile_not_found)`; everything else LoadCoach can say →
   `LOADCOACH_ERROR` with the code preserved; the client's own read timeout → `LOADCOACH_ERROR
   (reason=client_timeout)` after cancelling the possibly-started job. `CONTEXT_LIMIT_EXCEEDED`
   → `COMPACTION_FAILED` (nothing can fit it before Phase 8). **No retry** in this phase: the
   "retry per step policy" and "wait" cells halt with the cause; the step policy arrives with
   the plan (P7).
6. **A resumed trajectory re-mints its intent rather than rehydrating it.** There is no path
   that constructs an `ExecutionIntent` from a row and C4 forbade a second `rehydrate`-style
   escape, so `_load` re-runs `mint_bypass_default` with the recorded id, `minted_at`,
   declaration and tier snapshot and refuses (T13, cause *"…an envelope nobody minted"*) unless
   the canonical form equals the row. A configuration change that alters the envelope between
   claim and resume halts loudly (`test_a_changed_approval_policy…`). The AST guard was not
   touched; the ORM row class is imported under an alias so `models.ExecutionIntent(...)` cannot
   read as minting.
7. **Planned trajectories fail fast at claim** (T2 → T7, `PLAN_DRAFT_FAILED`) rather than queue
   forever. A requested bypass the configuration forbids, and a requested *planning* while
   planning is disabled, are both **refused** at T1 (`VALIDATION_ERROR`), never silently
   overridden.
8. **Tool calls halt** (`TOOL_NOT_FOUND`, *"tool calls are not executed before Phase 4"*), and
   `GenerateBody` has no `tools` field so none are advertised. A requested tool outside the
   caller's allowlist is recorded as an `undeclared_tool` deviation (never re-approvable) before
   the halt.
9. **Deviations are recorded and acted on in this phase** (§3), because recording without
   acting would let a violation flow onward.
10. **`LENGTH`/`ERROR` beat a passed schema check** in `decide_finish` (asserted).
11. **The e2e default tier uses a schema-validating profile** via
    `PROMPTCADENCE_TIERS__LOCAL_FAST__TASK_PROFILE=structured.answer`; setting one tier by
    environment replaces the whole `tiers` table (pre-existing config behaviour), so
    `LOCAL_LARGE` is set too. Worth knowing before E4 writes fixtures.
12. **The CLI closes its HTTP client, never enters it**: entering a `TestClient` runs the
    lifespan again. `http_client_factory` is the documented seam the e2e suite replaces.
13. **`requirements/` locks were not compiled** (C4 §7/§11 said "D2 compiles locks"). The
    kickoff scoped this row to commit-and-stop with no CI to verify a lock-based workflow
    change; the `security` job therefore still audits an environment containing only
    `pip-audit`. Recipe: LoadCoach's `requirements/README.md` (`pip-compile --strip-extras
    --extra dev --extra postgres --generate-hashes --output-file requirements/ci.lock
    pyproject.toml`, then `pip install --require-hashes -r requirements/ci.lock && pip install .
    --no-deps` in every job, `pip-audit --require-hashes -r requirements/ci.lock` in
    `security`). One small row; needs network.

---

## 7. Commits

**`/home/jpk/ai/suite/PromptCadence`** (`main`, from `752966f`):

| Commit | Subject |
|---|---|
| `264ea4e` | `feat(db,domain): migration 0003 (leases), Phase 3's error classes, and the finish decision` |
| `89948dd` | `feat(infrastructure): the LoadCoach client, its complete error map, and the provider surface` |
| `5477aa8` | `test(fakes): the fake LoadCoach, and the I10 contract tests against the OpenAPI snapshot` |
| `ec0c49d` | `feat(services): the ADR-0044 sink, the trajectory service, the bypass loop, the worker and recovery` |
| `7cfadd8` | `feat(web,cli): the trajectories API with SSE replay, and the run/trajectory commands` |
| `321e9d3` | `docs: Phase 3 in the changelog and README, and the mirrored amendments` |

**`/home/jpk/ai/suite/docs`**: `9edec2f` `docs(promptcadence): complete the LoadCoach error map,
name the finish_reason wire gap, record the recovery mechanism` (spec §13, spec §11 contract 6,
lifecycle §8.3, development plan Phase 3). Mirrored byte-identically into `PromptCadence/docs/`
(verified with `cmp`).

Both trees clean. Nothing pushed, nothing tagged, nothing published, no version bump.

---

## 8. Open items recorded, not chased

* The `promptcadence` PyPI name is unreserved (B4). Unchanged.
* B4's tier-defaults judgment call (`docs/history/B4_HANDOFF.md` §3). Unchanged.
* `setspec>=0.4,<0.5` stays pinned by MirrorWall (C4 §7). Unchanged; nothing here consumes it.
* The `security` job audits nothing (§6.13).
* LoadCoach: `finish_reason` not on the wire (§2); `GENERATION_CANCELLED` on `/generate` is
  "200 with a cancelled job" in its spec and a raise in its code (§5); `is_remote` known to
  routing but never rendered (the LC-E1 obligation C4 recorded).

---

## 9. Before the next session

1. **Push `main`** from `/home/jpk/ai/suite/PromptCadence` (six commits) and from
   `/home/jpk/ai/suite/docs` (one commit).
2. **Confirm CI green.** New here: the `contracts` job now collects 18 tests (it collected none
   before); `db-matrix` runs migration `0003`'s PostgreSQL parity; the kill −9 tests spawn a
   child interpreter and bind a loopback port — if a runner forbids either, they are the first
   to say so.
3. **Run the marked live journey** against a real LoadCoach with the shipped `tools.agent.*`
   profiles: `PROMPTCADENCE_LOADCOACH__BASE_URL=http://127.0.0.1:8766 .venv/bin/python -m pytest
   -m live -q`. Expect it to **fail** on a free-text tier with the §2 cause, and to pass on a
   schema-validating one. That failure is the finding; do not read it as a flake.
4. **Decide the LoadCoach `finish_reason` amendment** (§2) and schedule it; then teach the fake
   the field and re-run this suite. E4/F1 should not build on the halt-on-absence behaviour
   being permanent.
5. Remember this rides **`0.9.0b0` at M11**: no bump, no tag.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
