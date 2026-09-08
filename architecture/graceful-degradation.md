# Graceful Degradation

**Applies to:** every component.
**Principle:** a missing dependency produces an explicit state — an error, a degraded result, an
`unsupported` measurement, or a queued job. Never a crash, never a fabricated value, never a silent
substitution.

---

## 1. The four outcomes

| Outcome | Meaning | Shape |
|---|---|---|
| **Error** | The request cannot be satisfied now and retrying immediately will not help | Typed exception → HTTP error envelope with a stable `code`; CLI exit code 2–5 |
| **Degraded** | The operation completed with reduced fidelity or coverage | Normal result plus `degradations: [{code, message, impact}]`; UI badge; log at WARNING |
| **Unsupported** | This environment cannot produce this specific measurement or feature | `Unsupported` sentinel → NULL + reason in storage, `—` in UI, `"unsupported"` in JSON |
| **Queued / deferred** | A resource is temporarily unavailable | Job state with a reason and a retry schedule |

Choosing between them is a design decision made per case in the table below — never left to a
`try/except` that returns `None`.

---

## 2. Degradation matrix

`E` = error, `D` = degraded, `U` = unsupported, `Q` = queued. Every row names the user-visible
signal and the code path that must exist.

**PromptCadence gained a column on 2026-09-07 (row L2).** It had none because it reaches no provider
and no machine directly — every provider row below arrives through LoadCoach
([ADR-0045](../adr/0045-promptcadence-reaches-models-only-through-loadcoach.md)) — but "it inherits
LoadCoach's behaviour" is not a behaviour, and G20 makes every row's test a blocking gate. Its cells
are sourced from [its spec §13](../apps/promptcadence/spec.md) (the error vocabulary and the
complete LoadCoach code map, one mapping per code so no LoadCoach failure reaches a caller as
`INTERNAL_ERROR`) and from [lifecycle §5](../apps/promptcadence/lifecycle.md) (deviation handling)
and [§8](../apps/promptcadence/lifecycle.md) (the state machine and its recovery edges).

Three footnotes carry the `n/a` cells and the gaps row L8 found:

1. **n/a¹ — no machine axis.** PromptCadence declares neither `sweatmeter` nor `modelrack` and reads
   no telemetry: it has no GPU, sensor or placement facts to degrade. Machine conditions reach it
   only as LoadCoach routing outcomes, which are the `INSUFFICIENT_RESOURCES` and
   `NO_ELIGIBLE_MODEL` rows.
2. **n/a² — no evidence axis.** Capability evidence is LoadCoach's input, never PromptCadence's. A
   tier names a LoadCoach task profile; PromptCadence never imports, scores, ages or matches
   evidence, so no evidence condition can arise inside it.
3. **³** LoadCoach unreachable is the one row where the spec contradicts itself: §13's code map says
   a connection refusal *parks the trajectory in `waiting`*, and §13's own closing paragraph plus
   the state machine in lifecycle §8.1 say there **is no `waiting` state** and that an unreachable
   LoadCoach mid-turn is T13 (`failed`). The state machine is authoritative and the cell follows it;
   the spec sentence is recorded as drift in [the consistency review](../README.md#11-consistency-review).

| Condition | FreeWeight | LoadCoach | IdeaPress | PromptCadence | Signal |
|---|---|---|---|---|---|
| **No GPU present** | D — GPU/VRAM/energy metrics `U`; quality benchmarks run normally; memory-slope benchmark skipped with reason | D — admission control uses RAM only; VRAM constraints not applied | n/a — ADR-0115 | n/a¹ | Health: `gpu: unavailable`; run record notes skipped tests |
| **`nvidia-smi` missing or failing** | D — same as above, distinguished as "tool unavailable" not "no GPU" | D | n/a — ADR-0115 | n/a¹ | Health component `gpu_telemetry: unavailable (nvidia-smi not found)` |
| **GPU sensor unavailable** (temp/power/fan/clock) | U per field; energy metrics become `U` when power is `U` | Ignored by admission control | n/a — ADR-0115 | n/a¹ | `—` in UI; NULL + `reason` in DB |
| **Ollama not running** | E on any run start (`PROVIDER_UNAVAILABLE`); discovery returns the last known models marked stale; UI and CLI still work | E on execute; jobs stay `queued` with `waiting_for_provider` up to their max wait, then `failed` | E on the stage; workflow pauses at the failed stage, project intact | E — LoadCoach's `PROVIDER_UNAVAILABLE`; the turn is repeated on the same tier under the same intent up to `[execution] step_retries`, then halts naming the last cause and **every** attempt. It does not wait and does not back off | Health: `provider: unavailable`; explicit banner |
| **Provider returns malformed JSON** | E for that sample; run continues; sample stored with `error_text` and the raw body as an artifact | E for that attempt; retry policy applies; then fallback candidate | E for the stage; retry per stage policy | E — `PROVIDER_PROTOCOL_ERROR`, same repeat ladder; surfaced as `LOADCOACH_ERROR` with the original code in `details`, never `INTERNAL_ERROR` | `PROVIDER_PROTOCOL_ERROR` |
| **Provider timeout** | Sample marked `timeout`; never counted as a score of 0 | Attempt fails; retry/fallback; job records each attempt | Stage retry then pause | E — `PROVIDER_TIMEOUT`, same repeat ladder. The client's *own* read timeout first cancels the job the request may have started, then repeats (`reason = client_timeout`) | `PROVIDER_TIMEOUT` |
| **Model not found** | E at run start with the list of known models | Candidate removed from routing with rejection reason `model_absent` | E with the configured model named | E — halt **without** a repeat: the same request gets the same answer, so a deterministic code is never retried | `MODEL_NOT_FOUND` |
| **Insufficient VRAM for the requested context** | Context-fit benchmark records the maximum successful context — this *is* the measurement, not a failure | Candidate rejected with `insufficient_vram (needs X, free Y)`; if all candidates fail, job stays `queued` as `waiting_for_resources` | Surfaced from LoadCoach or from the direct backend error | E/D — `INSUFFICIENT_RESOURCES` repeats, then halts. `NO_ELIGIBLE_MODEL` instead falls to the intent's next `fallback_tier`, else raises a `tier_escalation` drift for scoped re-approval, else halts `TIER_UNAVAILABLE`. There is no queue and no `waiting` state | `INSUFFICIENT_RESOURCES` |
| **Insufficient system RAM** | Run refused before start with the estimate | Same as VRAM | Same | Same as VRAM | `INSUFFICIENT_RESOURCES` |
| **Model lacks a required capability** (tools, structured output) | Test skipped with `unsupported_capability`, never scored 0 | Hard-constraint rejection before scoring | Stage requiring it errors with a clear message and a suggested model | E — `CAPABILITY_UNSUPPORTED` halts without a repeat; a tier that cannot serve the step at all escalates instead | `CAPABILITY_UNSUPPORTED` |
| **Container runtime absent** (code-execution benchmarks) | Benchmark **skipped**, reason `sandbox_unavailable`; never executed on the host | n/a | n/a | D — ToolYard's ladder falls to `bwrap` and then to refusal; the refusal is a structured `ToolResult` returned to the model, and one refused call never ends a trajectory. Podman is unexercised by choice (ADR-0111) | ADR-0018 tier check |
| **No benchmark evidence at all** | n/a | D — routes on declared capabilities + config; every decision states `evidence: none`; confidence factor at its floor | n/a | n/a² | UI banner "routing without measured evidence" |
| **Stale benchmark evidence** | Marks results stale in the UI when environment drift is detected | D — confidence decayed per ADR-0017; explanation shows age and decay | n/a | n/a² | Badge with age and reason |
| **Incompatible SetSpec major version** | Import/export refused with both versions named | Import refused; existing evidence untouched | Backend adapter refuses to start in LoadCoach mode | E — `SCHEMA_VERSION_UNSUPPORTED`, on LoadCoach responses and on `governance.egress_decision` payloads alike | `SCHEMA_VERSION_UNSUPPORTED` |
| **Incompatible API major version** | n/a | **Gap** in LoadCoach's *own* client role (found at row L8, 2026-09-07): this cell is about LoadCoach calling FreeWeight's evidence API, and `FreeWeightClient` (`infrastructure/freeweight_client.py`) calls a fixed path and never reads or checks any version field from the response — "Client rejects with both versions named" describes no code that exists. Owed work, not a documented behaviour | Same — IdeaPress's own LoadCoach client rejects with both versions named | **Gap** — the client pins the `/api/v1` prefix and never reads LoadCoach's `api_versions`; a major bump would arrive as ordinary 404s mapped to `LOADCOACH_ERROR`. Owed work, not a documented behaviour | `API_VERSION_UNSUPPORTED` |
| **Optional application unreachable** | n/a | Evidence import skipped; last import retained and marked stale | Fall back to direct backend (or error if pinned) | E/park — LoadCoach is **not** optional here (ADR-0045). It still starts and serves; health reports `loadcoach: degraded`, never `unavailable`; a trajectory that cannot reach it mid-turn is T13 `failed` with the cause after any orphan job is cancelled, and recovery is deferred while it is unreachable³ | Health component `degraded` |
| **Evidence measured under a different runtime profile** | n/a | D — that evidence does not apply; the capability is **absent** for the candidate (not zeroed), the explanation names both hashes and the FreeWeight invocation that would fix it, and the decision counts toward `low_evidence` | n/a | n/a² | `evidence_profile_mismatch` in the explanation |
| **Evidence for a model not yet discovered** | n/a | Retained with `match_state = "unmatched"`, reported in the import result, contributes nothing, binds automatically on the next discovery pass | n/a | n/a² | Import counts; evidence page |
| **Served context cannot be established** | Recorded on the run with its source | D — decision flagged `assumed_context`; a profile needing a context the provider will not be asked to serve is rejected `context_not_configurable` | Surfaced from LoadCoach as a degradation on the attempt | `assumed_context` is carried through from LoadCoach on the turn; `CONTEXT_LIMIT_EXCEEDED` triggers compaction and one retry, then `COMPACTION_FAILED` naming both figures | `assumed_context` |
| **More than one GPU visible, placement unreported** | Memory, KV and energy tests **skipped** with `multi_gpu_placement_unknown`; quality and throughput unaffected | D — admission evaluates each device independently; a model fitting no single device is deferred, never admitted on a summed total | n/a | n/a¹ | Skip reason on the run; per-device numbers in the rejection |
| **`Host` header not in the allowlist** | 421 before routing and before auth | Same | Same | Same — 421 before routing and before authentication | `MISDIRECTED_REQUEST`, WARNING log with the presented value |
| **Evidence import URL fails the fetch allowlist** | n/a | E — `EVIDENCE_SOURCE_REFUSED` before any bytes are parsed; existing evidence untouched | n/a | n/a² for evidence. The analogous rule is the `http_fetch` tool's allowlist: a non-allowlisted host, a literal IP, an off-allowlist redirect or an oversized body is a structured `ToolResult` refusal, never an exception | Names the rule that refused it |
| **Database migration pending** | Startup refuses with the exact `alembic upgrade` command; read-only inspection commands still work | Same | Same | Same | `MIGRATION_REQUIRED`, exit 4 |
| **Database migration fails** | Automatic restore from the pre-migration backup; original DB never left half-migrated | Same | Same | Same | `MIGRATION_FAILED` + restore log |
| **Database locked (SQLite)** | Retry with backoff to `busy_timeout`, then E | Same | Same | Same | `STORAGE_BUSY` |
| **Disk full** | Corrected 2026-09-07 (row L8): the write that hits it fails cleanly at the *test* it happened in (`INTERNAL_ERROR`), not the run — spec §13's "a failed test never fails its run" applies here too. Already-committed samples in that test and every other test survive; the run still reaches `completed` overall, with the affected test `failed` | Job fails; queue preserved | Corrected 2026-09-07 (row L8): there is no temp-file staging anywhere in this codebase. `export_project` writes directly to the export path and already wraps the failure — `except OSError as exc: raise ExportFailed(...)`, naming the path and the original error; nothing partial is left on disk | Turn aborted at the next boundary; committed turns and their events survive, because a state change and the event announcing it are one write (ADR-0044) | `STORAGE_FULL` |
| **SSE client disconnects** | Nothing; events are rows. Client replays from `Last-Event-ID` | Same | Same | Same — events are rows; the client replays from `Last-Event-ID` | Debug log only |
| **Server restarts mid-run/job** | Run marked `interrupted` on startup recovery; completed tests retained; resumable | Leases expire; jobs return to `queued` (idempotent) or `failed` (non-idempotent, per policy) | Workflow resumes at the last committed unit | Leases expire and the reaper takes over only an expired one; a turn in flight has its orphan LoadCoach job cancelled and resumes, or halts `recovered` when it cannot be reconciled | Startup recovery log + UI notice |
| **Prompt pack missing/invalid** | Startup validation fails with the file and field named | Same | Same | Same — startup validation fails with the file and field named | `PROMPT_INVALID`, exit 3 |
| **Remote provider configured but unreachable** | E, and the error names the remote host so egress is obvious | E | E | E — and egress was already decided on the tier's *configuration* before its availability (ADR-0073), so a denied remote tier is denied whether or not it answers; unreachability then names the tier | `PROVIDER_UNAVAILABLE` |

---

## 2.1 Row index — which test proves each row

**Added 2026-09-07 (row L2).** G20 makes "every row of the degradation matrix has a test" a blocking
gate, and nothing anywhere mapped rows to tests. This is that map, built by grepping the four
applications' `tests/` trees for each condition's code, sentinel or state. Paths are relative to
each application repository. **`untested`** means no test was found — it is a claim about this
search, and it is the input to the sessions that close G20, not an invitation to invent a test that
asserts the row's text back at itself
([ADR-0042](../adr/0042-a-check-may-not-restate-its-requirement.md)).

`n/a` cells carry the same footnotes as §2. A row marked `untested` in every column is not a
disproved behaviour; it is an unproved one.

| Condition | FreeWeight | LoadCoach | IdeaPress | PromptCadence |
|---|---|---|---|---|
| No GPU present | `unit/test_telemetry_service.py::test_gpu_telemetry_component_is_degraded_with_no_gpu_and_overall_health_degrades` | `unit/test_telemetry_stream.py::test_payload_names_why_there_is_no_gpu`; `unit/test_routing_constraints.py` | n/a — ADR-0115 | n/a¹ |
| `nvidia-smi` missing or failing | `unit/test_telemetry_service.py::test_degrades_to_null_host_reader_when_platform_unsupported` | `unit/test_telemetry_stream.py::test_a_collector_that_cannot_read_produces_no_frame` | n/a — ADR-0115 | n/a¹ |
| GPU sensor unavailable | `unit/test_telemetry_service.py::test_unsupported_measurement_renders_as_the_fixed_string`; `unit/test_energy_integration.py` | `unit/test_telemetry_stream.py::test_payload_carries_numbers_and_unsupported_never_zero` | n/a — ADR-0115 | n/a¹ |
| Ollama not running | `e2e/test_models_flow.py::test_http_models_page_survives_a_provider_that_cannot_be_reached`, `::test_cli_show_falling_back_to_an_unreachable_provider_exits_4` | `unit/test_health.py::test_unreachable_provider_degrades_but_never_makes_overall_unavailable`; `e2e/test_server_boot.py::test_health_reports_degraded_with_no_provider` | `integration/test_loadcoach_degradation.py::test_an_unreachable_loadcoach_raises_backend_unavailable` | `unit/test_loadcoach_client.py::test_a_transport_failure_is_unavailable_and_a_timeout_is_an_error` |
| Provider returns malformed JSON | untested *(provider-level; `unit/test_external_output_parsing.py` covers the external-framework parser, not a provider body)* | `unit/test_retry_policy.py::test_protocol_error_retries_exactly_once`; `simulation/test_scheduling_properties.py::test_a_connection_error_falls_back_at_once_and_a_protocol_error_retries_once` | untested | `unit/test_loadcoach_client.py` (`PROVIDER_PROTOCOL_ERROR` in the code map); `fakes/loadcoach_app.py` scripts it |
| Provider timeout | untested *(the sandbox/external-tool hang is covered by `integration/test_sandbox_tiers.py::test_a_hang_is_killed_at_the_timeout`; the provider timeout is not)* | `integration/test_generate.py::test_a_timeout_is_recorded_as_a_provider_error_and_falls_back`; `unit/test_retry_policy.py::test_timeout_retries_the_same_model_up_to_the_limit_then_falls_back` | `integration/test_loadcoach_degradation.py::test_a_stalled_loadcoach_raises_provider_timeout` | `integration/test_step_retry.py::test_a_step_that_fails_twice_completes_on_its_third_attempt`, `::test_the_budget_is_spent_and_the_halt_names_the_last_cause_and_every_attempt` |
| Model not found | `e2e/test_models_flow.py::test_http_detail_page_404s_on_an_unknown_reference`, `::test_cli_show_of_an_unknown_reference_exits_2` | `e2e/test_model_and_profile_detail.py`; `unit/test_doctor.py` | `integration/test_loadcoach_degradation.py::test_the_refusal_names_loadcoach_s_own_code_and_message` | `integration/test_step_retry.py::test_a_deterministic_refusal_is_never_repeated` |
| Insufficient VRAM for the requested context | `integration/test_performance_benchmark.py` (the context-fit ladder records the maximum successful context) | `unit/test_admission.py`; `unit/test_routing_constraints.py`; `integration/test_fake_provider_vram.py`; `integration/test_route_endpoint.py` | untested | `integration/test_step_retry.py::test_a_tier_that_cannot_serve_escalates_rather_than_repeating` |
| Insufficient system RAM | untested | `unit/test_admission.py`; `simulation/test_scheduling_properties.py` | untested | covered by the row above (one ladder) |
| Model lacks a required capability | `integration/test_quality_suites.py`; `unit/test_scorers_tools.py` | `unit/test_admission.py`; `integration/test_tool_wire.py`; `integration/test_generate.py` | `integration/test_loadcoach_degradation.py` | `integration/test_bypass_loop.py`; `unit/test_loadcoach_client.py` |
| Container runtime absent | `security/test_sandbox_refusal.py`; `integration/test_sandbox_tiers.py` | n/a | n/a | `integration/test_tool_execution.py`; ToolYard's own `isolation`-marked suite (podman rung skipped, ADR-0111) |
| No benchmark evidence at all | n/a | `integration/test_evidence_routing_change.py::test_with_no_evidence_source_configured_the_explanation_says_so` | n/a | n/a² |
| Stale benchmark evidence | `unit/test_provenance.py` (drift marking) | `integration/test_evidence_routing_change.py::test_freshness_uses_measured_at_so_re_aggregation_does_not_change_a_decision` | n/a | n/a² |
| Incompatible SetSpec major version | `contract/test_export_schemas.py`; `contract/test_evidence_schema.py` | `contract/test_schema_rejection.py`; `integration/test_evidence_importer.py` | `contract/test_envelope_conformance.py` | `unit/test_loadcoach_client.py` (`SCHEMA_VERSION_UNSUPPORTED`); `integration/test_bypass_loop.py` |
| Incompatible API major version | n/a | `untested — behaviour not implemented, see L8 handoff` (§2's `FreeWeightClient` gap) | `integration/test_loadcoach_degradation.py::test_a_version_mismatch_names_both_versions_and_does_not_downgrade` | `unit/test_loadcoach_client.py::test_an_incompatible_api_major_refuses_generate_as_a_loadcoach_error`, `integration/test_bypass_loop.py::test_an_incompatible_api_major_halts_where_a_loadcoach_error_halts_today` (row K1, 2026-09-07) |
| Optional application unreachable | n/a | `integration/test_evidence_routing_change.py::test_an_unreachable_freeweight_keeps_routing_on_the_last_import_and_says_so`; `unit/test_health.py::test_evidence_degrades_when_the_configured_source_is_unreachable` | `integration/test_loadcoach_degradation.py::test_an_unreachable_loadcoach_falls_back_and_records_the_degradation`, `::test_committed_units_survive_loadcoach_disappearing_mid_project` | `e2e/test_server_boot.py::test_loadcoach_component_degraded_never_unavailable`; `integration/test_recovery.py::test_recovery_is_deferred_when_loadcoach_is_unreachable` |
| Evidence measured under a different runtime profile | `unit/test_runtime_profile.py` | `integration/test_evidence_routing_change.py::test_evidence_measured_under_another_profile_is_absent_with_both_hashes_and_a_remedy` | n/a | n/a² |
| Evidence for a model not yet discovered | n/a | `integration/test_evidence_routing_change.py::test_unmatched_evidence_contributes_nothing_and_is_counted`; `contract/test_evidence_import.py` | n/a | n/a² |
| Served context cannot be established | `unit/test_effective_context.py` | `unit/test_routing_explanation.py`; `integration/test_route_endpoint.py::test_a_model_advertising_131072_but_served_4096_is_rejected_not_truncated` | `contract/test_loadcoach_backend.py` | `integration/test_compaction.py` (the `CONTEXT_LIMIT_EXCEEDED` → compact → retry path) |
| More than one GPU visible, placement unreported | `integration/test_performance_benchmark.py` (`multi_gpu_placement_unknown`) | untested | n/a | n/a¹ |
| `Host` header not in the allowlist | `e2e/test_server_boot.py::test_mismatched_host_header_is_rejected`; `security/test_security_checklist.py` | `e2e/test_server_boot.py::test_wrong_host_header_rejected_with_421`; `security/test_checklist.py` | `e2e/test_system.py::test_host_validation_runs_before_routing_on_every_request`; `security/test_lan_exposure.py` | `e2e/test_server_boot.py::test_wrong_host_header_rejected_with_421`; `security/test_checklist.py` |
| Evidence import URL fails the fetch allowlist | n/a | `integration/test_evidence_fetch.py`; `integration/test_evidence_api.py` | n/a | `security/test_injection_corpus.py` (the `http_fetch` allowlist cases) |
| Database migration pending | `integration/test_migrations.py` | `unit/test_doctor.py`; `e2e/test_server_boot.py::test_database_migrates_on_first_boot` | `integration/test_migrations.py` | `e2e/test_server_boot.py::test_database_migrates_on_first_boot` |
| Database migration fails | `integration/test_migrations.py::test_failed_migration_restores_the_original_database_byte_identical` | `integration/test_migrations.py::test_failed_migration_restores_backup_on_sqlite` | `integration/test_migration_failure.py::test_a_failing_migration_restores_the_backup_and_keeps_existing_rows` (row L8) | `integration/test_migration_failure.py::test_a_failing_migration_restores_the_backup_and_keeps_existing_rows` (row L8) |
| Database locked (SQLite) | `integration/test_transactions.py` | `integration/test_database_locked.py::test_a_locked_database_refuses_a_new_job_and_the_queue_is_left_untouched` (row L8) | `integration/test_database_locked.py::test_a_locked_database_refuses_a_new_project_and_creates_nothing` (row L8) | `integration/test_database_locked.py::test_a_locked_database_refuses_a_new_trajectory_and_creates_nothing` (row L8) |
| Disk full | `integration/test_disk_full.py::test_a_disk_full_checkpoint_fails_the_run_and_keeps_the_completed_samples` (row L8; §2's cell corrected in the same change) | `integration/test_disk_full.py::test_a_disk_full_completion_write_fails_the_job_and_preserves_the_queue` (row L8) | `integration/test_disk_full.py::test_a_disk_full_export_write_is_refused_cleanly_and_writes_nothing_partial` (row L8; §2's cell corrected in the same change) | `integration/test_disk_full.py::test_a_disk_full_turn_write_leaves_nothing_partial_and_other_trajectories_untouched` (row L8) |
| SSE client disconnects | `integration/test_sse_replay.py::test_a_disconnecting_client_ends_the_generator`, `::test_a_reconnect_continues_exactly_where_it_stopped` | `integration/test_queue_stream.py`; `integration/test_streaming.py` | `e2e/test_stage_stream.py::test_a_reconnect_with_last_event_id_replays_only_what_was_missed` | `e2e/test_bypass_journey.py::test_the_stream_replays_from_last_event_id_without_gap_or_duplicate` |
| Server restarts mid-run/job | `integration/test_recovery.py::test_a_killed_run_is_interrupted_not_failed` (+8 more) | `integration/test_recovery.py::test_kill_minus_nine_is_recovered_and_the_job_completes_exactly_once` | `integration/test_stage_recovery.py::test_resume_recovers_a_unit_a_failure_left_mid_review` | `integration/test_recovery.py::test_kill_minus_nine_with_a_turn_in_flight_cancels_the_orphan_and_resumes` |
| Prompt pack missing/invalid | `unit/test_prompt_pack.py::test_a_missing_required_field_is_refused` (+6 refusal cases) | n/a *(no prompt pack)* | `unit/test_prompt_pack.py::test_a_missing_required_variable_is_refused` | `unit/test_prompt_pack.py::test_a_missing_required_variable_is_refused` |
| Remote provider configured but unreachable | `security/test_settings_boundary.py` (the `allow_remote` acknowledgement); untested for the unreachable path itself | `integration/test_route_endpoint.py`; `unit/test_config.py` (binding refusals) | `integration/test_stage_governance.py`; `e2e/test_backends_surface.py` | `integration/test_remote_tier.py`; `unit/test_remote_tier_checks.py`; `integration/test_egress.py` |

**What this index shows, updated 2026-09-07 (row L8).** **Disk full** is now proved in all four
applications, **database locked** in the three that lacked it (FreeWeight already had one), and
**database migration failure** in the two newest applications. One row stays `untested`, a
documented behaviour that was never built rather than a missing test: LoadCoach's half of
**incompatible API major version** (`FreeWeightClient` never reads a version from FreeWeight's
response, §2's corrected cell). IdeaPress's three machine-condition rows (**No GPU present**,
**`nvidia-smi` missing or failing**, **GPU sensor unavailable**) are no longer in this count: row M3
(2026-09-07) found `show_telemetry_bar` hardcoded `False` and never wired to a `TelemetrySnapshot`,
the same defect L8 found, and closed it by removal rather than by building —
[ADR-0115](../adr/0115-ideapress-shows-no-machine-telemetry.md) records that IdeaPress shows no
machine telemetry by decision, and the three cells now read `n/a — ADR-0115`. Per row L8's own
kickoff, a documented behaviour that is not implemented is left `untested` rather than proved with a
test that asserts the row's own text back at itself (ADR-0042); building or scoping it out is
separate work, recorded in `docs/history/L8_HANDOFF.md` and, for IdeaPress's rows,
`docs/history/M3_HANDOFF.md`. G20 can be turned on once LoadCoach's row is either built and tested or
formally scoped out, the way ADR-0111 scopes out ToolYard's podman rung and ADR-0115 now scopes out
IdeaPress's telemetry rows.

---

## 3. Health reporting

Every application exposes `GET /api/v1/health` and `<app> health [--json]`, using one shape:

```json
{
  "status": "ok",
  "version": "1.2.0",
  "checked_at": "2026-08-21T10:04:11.482Z",
  "components": [
    {"name": "database",  "status": "ok",          "detail": "sqlite 3.46, 12 migrations applied"},
    {"name": "provider",  "status": "ok",          "detail": "ollama 0.32.13, 11 models"},
    {"name": "gpu",       "status": "degraded",    "detail": "power sensor unavailable"},
    {"name": "evidence",  "status": "degraded",    "detail": "last import 14 days ago"},
    {"name": "loadcoach", "status": "unavailable", "detail": "connection refused at 127.0.0.1:8766"}
  ]
}
```

* `status` for the whole application is the worst component status that is **required** for its core
  function. Optional components never make the application `unavailable`.
* Component statuses: `ok` | `degraded` | `unavailable` | `not_configured`.
* `not_configured` is not a problem: LoadCoach with no FreeWeight configured reports
  `evidence: not_configured`, and overall `ok`.
* HTTP status is 200 for `ok`/`degraded`, 503 for `unavailable`. Machines read the body, not the code.

---

## 4. Startup validation

At startup each application, in order:

1. Loads and validates configuration (precedence resolved, types checked, unknown keys reported).
2. Refuses to start on unsafe combinations — non-loopback bind without authentication, remote
   provider without an explicit `allow_remote` acknowledgement, world-writable data directory.
3. Verifies the database exists and is at head; refuses with an actionable message otherwise, and
   refuses when the database is **ahead** of the code (`SchemaAhead`) naming both revisions and the
   backup directory — the state a downgrade without a restore leaves behind.
4. Validates the prompt pack (parse, required variables, schema compatibility).
5. Probes optional dependencies **without blocking**: provider, GPU telemetry, optional peer
   applications. Failures here produce degraded health, never a refusal to start.
6. Logs a one-line startup summary naming every degraded component.

The distinction is deliberate: **configuration errors block startup; environment gaps do not.**

---

## 5. Testing degradation

Failure paths are tested to the same standard as success paths. Each application's suite includes,
at minimum:

* Provider absent, provider timeout, provider 500, provider malformed body, provider truncated stream.
* GPU absent, `nvidia-smi` absent, `nvidia-smi` malformed, multi-GPU, missing temperature, missing power.
* Database at an older revision, database locked, migration failure with restore.
* Schema major mismatch on import and on export consumption.
* Peer application unreachable, peer returning an incompatible API version.
* Disconnect and reconnect mid-stream with `Last-Event-ID` replay.
* Process kill mid-run/mid-job followed by restart recovery.
* Sandbox tier unavailable → benchmark skipped, not executed.
* Evidence whose runtime profile does not match the execution; evidence for an undiscovered model.
* A disallowed `Host` header; a forged form post; an import URL outside the allowlist.
* More than one GPU visible with placement unreported.

A degradation path with no test is treated as an unimplemented feature.
