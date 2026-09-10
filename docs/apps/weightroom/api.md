# WeightRoomGym — Public API

**Base path:** `/api/v1` · **Conventions:** [API and Contract Standards](../../standards/api-and-contract-standards.md)
**Authentication:** the session cookie of [ADR-0126](../../adr/0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md);
every route below requires it except `GET /version` and the two trust routes. Every
state-changing route requires MirrorWall's CSRF token (forms) or the same-origin checks of
ADR-0126 rule 5 (JSON), and writes one `audit_log` row (spec §11 contract 2).
**Status:** specified at row W0; the OpenAPI snapshot is committed when the routes exist
([Gold Standards G7](../../standards/gold-standards.md)), and this document is regenerated to
match it at W10.

`{app}` is `freeweight` | `loadcoach` | `ideapress` | `promptcadence` throughout; an unknown
value is `404 APP_UNKNOWN`.

---

## 1. System

| Endpoint | Purpose |
|---|---|
| `GET /health` | MirrorWall's standard health payload: `database`, `tls` (days to expiry, `degraded` under 30), `units` (systemd reachable, `unsupported` without it), and one component per application named `app:<name>` with `ok`/`degraded`/`stopped`/`unknown`. `200` when WeightRoomGym's own database and TLS are fine — a stopped application never drops it below 200 |
| `GET /version` | `{"application": "weightroom", "version": "…", "api_version": "v1", "schema_version": "1"}`. Never authenticated ([ADR-0026 §5](../../adr/0026-local-http-hardening.md)) |
| `GET /system/status` | The machine view (spec §17): per application `state`, `version`, `api_version`, `db_revision`, `known`; `ollama` (unit state, cap lines found, residency); `telemetry` (the last snapshot); `costs_today`; `alerts_open`; `jobs_running`; `doctor_last` |
| `GET /system/telemetry/stream` | SSE, one `telemetry.sample` per interval, `—` for unavailable readings; replay from `Last-Event-ID` within the retained window |
| `GET /system/telemetry/history?figure=gpu_util&hours=24` | Downsampled samples for one figure's history page |
| `GET /system/resident` | Resident models: Ollama's `/api/ps` rows and LoadCoach's `/models` residency, each with `source` |
| `GET /doctor` · `POST /doctor/run` | The last doctor report; run it now. Findings carry `severity`, `subject`, `rule` (`memory_safety.2.1.cap`, `lan.app_off_loopback`, …) and, where a root-owned fix exists, `command` — the text to run, never run |

## 2. Applications

| Endpoint | Purpose |
|---|---|
| `GET /apps` | The four, with `installed`, `executable`, `unit` (`active`/`activating`/`deactivating`/`inactive`/`failed`/`absent`/`unsupported`), `state` (the pill), `version`, `version_verdict`, `base_url`, `db_revision`, `known`. The version comes from each application's own `GET /api/v1/version`, which answers in either of two shapes ([ADR-0129](../../adr/0129-weightroom-reads-both-version-payload-shapes.md)) |
| `GET /apps/{app}` · `GET /apps/{app}/health` | One application; its own `/api/v1/health` proxied verbatim with `source: "api"` or `{"state": "stopped"}` |
| `POST /apps/{app}/start` · `/stop` · `/restart` | `systemctl --user <verb> <app>.service`; `202` with the audit id, then the unit state; `UNIT_UNSUPPORTED` without systemd, `UNIT_ACTION_FAILED` with systemd's message |
| `GET /apps/{app}/logs?since=&until=&level=&q=` | Journal history, JSON lines, capped at 5 000 rows per page with a cursor |
| `GET /apps/{app}/logs/stream` · `GET /logs/stream?apps=` | SSE of journal lines, one application or several; WeightRoomGym's own log under `weightroom` |
| `GET /apps/{app}/config` | The raw `config.toml` text and its mtime (the editor's base) |
| `GET /apps/{app}/settings/schema` | The application's schema document ([ADR-0127](../../adr/0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md) rule 1), cached for 60 s; `APP_NOT_INSTALLED` when the executable is absent |
| `GET /apps/{app}/settings` | Effective values with per-key `source` and `shadowed_by`, the runtime-changeable set, the security set |
| `PUT /apps/{app}/settings` | `{"changes": {key: value}, "base_mtime": <st_mtime_ns>, "to_file": [key, …]}`. **There is no `reauth` field**: the re-authentication window is session state, not a bearer token (row W4 — see `history/handoffs/W4_HANDOFF.md`), so a security key needs a `POST /reauth` on the *same session* inside `auth.reauth_window_minutes` and nothing is carried on the write. `base_mtime` is `st_mtime_ns`, which a JSON integer holds exactly. Runtime keys go to the application's `PUT /settings`; file keys are written in place (`tomlkit`), validated via `config validate --file`, renamed with `.bak`. Answers per key: `applied` (live), `written` (pending restart), `unchanged`, `refused` (with the application's message). `CONFIG_CHANGED_ON_DISK` when `base_mtime` is stale; `REAUTH_REQUIRED` when a security key is present without a fresh re-authentication; a runtime key while the application is down is `refused` with `APP_STOPPED` naming the file, and `to_file` writes it there instead |
| `POST /apps/{app}/settings/validate` | A candidate file body → the application's validation verdict, unchanged |

## 3. Databases

| Endpoint | Purpose |
|---|---|
| `GET /apps/{app}/db/revision` | `alembic_version`, whether WeightRoomGym knows it, the revisions it knows, the dialect and the database URL (credentials redacted). It answers for an unknown revision too; every other route below is `409 SCHEMA_UNKNOWN` then ([ADR-0123](../../adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 3) |
| `GET /apps/{app}/db/tables` | Tables with row counts, `writable` (false for the [ADR-0124](../../adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md) list, with `reason` and `lock_class`); the curated operations per table are on the table's page |
| `GET /apps/{app}/db/tables/{t}?page=&sort=&desc=&column=&filter=` | A page of 100 rows, columns typed as the database declares them; `sort` defaults to the primary key; `filter` is text the `column`, cast to text, contains — matched literally, never a pattern |
| `POST /apps/{app}/db/query` | `{"sql": "SELECT …"}` on a read-only connection, 30 s, 10 000 rows; anything but a single `SELECT`/`WITH` is `GUARD_STATEMENT_REFUSED` |
| `POST /apps/{app}/db/write/dry-run` | `{"sql": …}` → the statement echoed, the tables it names (what is typed), what the database's foreign keys reach with each table's change in rows ([ADR-0133](../../adr/0133-the-guard-follows-foreign-keys-observes-stopped-twice-and-binds-a-write-to-its-dry-run.md) rule 1), the unit's state and the port, the guard's checklist with each condition's current verdict, and — **only once the application is stopped** — the row count from a rolled-back transaction and the `dry_run_id` a write presents. `GUARD_TABLE_LOCKED` for a written or reached locked table; `GUARD_DRY_RUN_FAILED` when the rolled-back statement errors |
| `POST /apps/{app}/db/write` | `{"sql": …, "tables_typed": ["samples", "run_tests"], "dry_run_id": …}`. **No re-authentication field**: a `POST /reauth` on the same session inside the window, as for security keys (row W4). Runs the guard in ADR-0133's order: `GUARD_STATEMENT_REFUSED`, `GUARD_TABLE_LOCKED`, `GUARD_TABLE_MISMATCH` (4), `GUARD_APP_RUNNING` (1), `GUARD_DRY_RUN_FAILED` (3 — the dry run is repeated and must match the id, and the statement is rolled back if its own counts differ), `GUARD_BACKUP_FAILED` (2), `GUARD_AUDIT_FAILED` (5); success returns the audit id, the backup path, the row count, the reached tables' changes and the checklist |
| `GET /apps/{app}/db/status` · `POST /apps/{app}/db/backup` · `POST /apps/{app}/db/upgrade` · `POST /apps/{app}/db/restore` | Curated calls to the application's own `db` verbs (FreeWeight's `db vacuum` too, from the page). Each answers `{"verb", "argv", "ok", "output", "error"}` — a non-zero exit is `ok: false` in the application's own words, not an HTTP error. `restore` requires the unit stopped, `{"file": …, "name_typed": "<app>"}` and a fresh re-authentication |
| `POST /apps/{app}/db/delete-results` | FreeWeight only ([ADR-0134](../../adr/0134-event-logs-go-with-their-deleted-parent-freeweight-deletes-its-own-results-and-guarded-write-backups-expire.md) rule 2). `{"scope": "model"\|"run"\|"suite"\|"before"\|"all", "selector": …}` → FreeWeight's own `POST /api/v1/database/delete-preview`, answered in the curated shape with `verb: "delete-preview"`, `argv: ["POST", url]` and FreeWeight's JSON as `output` (`run_count`, `removed_counts`, `preserved_counts`, `total_rows`, `token`, `will_backup`). With `"token"` and `"typed"` (the selector, or `all`) and a fresh re-authentication → FreeWeight's `DELETE /api/v1/database/results`, `verb: "delete-results"`. The application runs throughout. FreeWeight's refusal (a token a changed database invalidated) is `ok: false` in its own words; another application, another scope or a mistyped confirmation is `VALIDATION_ERROR` |
| `GET /apps/{app}/db/backups` | The guarded-write backups under WeightRoomGym's own `<data>/backups/<app>/`, newest first, each the undo of one raw write; kept 90 days by default and then removed, from row W8 (ADR-0134 rule 3) |

## 4. Prompts

| Endpoint | Purpose |
|---|---|
| `GET /apps/{app}/prompts` | The shipped pack (`prompt_id`, version, sha256) joined with overrides in effect |
| `GET /apps/{app}/prompts/{id}` | The shipped record, the override if any, and a unified diff |
| `PUT /apps/{app}/prompts/{id}` | Writes the override record after validation against the record schema; the response says where it was written and that runs will be marked `user_override` |
| `DELETE /apps/{app}/prompts/{id}/override` | Removes the override |

## 5. Ollama, catalog, costs

| Endpoint | Purpose |
|---|---|
| `GET /ollama` | Unit state, the `Memory*`/`ManagedOOM*`/`Environment` lines found, the [`MEMORY_SAFETY.md` §2.1](../../MEMORY_SAFETY.md) checklist as findings, whether the polkit rule is present |
| `GET /ollama/ps` | `/api/ps` through ModelRack |
| `POST /ollama/restart` | `systemctl restart ollama.service` when permitted; otherwise `OLLAMA_RESTART_NOT_PERMITTED` with `command` and the rule text ([ADR-0125](../../adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md) rule 5) |
| `GET /catalog` | Models across applications joined by canonical identity; per row `apps: {name: {enabled, evidence, resident}}` |
| `POST /catalog/pull` | `{"name": "gemma4:12b-it-q8_0"}` → the id of a queued `catalog_pull` job (row W9); `GET /catalog/pull/{id}/stream` is its live progress while this process executes it, `queued` before, and the job's own `done` after |
| `POST /catalog/dropin` | Multipart upload or `{"path": …}` on the host; validated GGUF; copied into the model directory; each llama.cpp-configured application's `models refresh` is run |
| `POST /catalog/{ref}/enabled` | `{"app": …, "enabled": false}` → that application's `POST /models/{ref}/enabled` |
| `DELETE /catalog/{ref}` | `{"preview": true}` first (what would be removed where), then `{"confirm": "<ref typed>"}` |
| `GET /costs` · `GET /costs/{app}` | LoadLedger balances per application and window with `unpriced_count`, the configured ceilings, and each ceiling's verdict |

## 6. Chat

| Endpoint | Purpose |
|---|---|
| `GET /chat/conversations` · `POST /chat/conversations` | List; create with `{"backend": "loadcoach"|"promptcadence", "title", "task_profile"|"classification", "tier", "tools"}` |
| `GET /chat/conversations/{id}` · `DELETE …` | The conversation with messages and their metadata |
| `POST /chat/conversations/{id}/messages` | `{"text": …, "attachment_ids": […]}` → `202` and the message id; the reply streams |
| `GET /chat/conversations/{id}/stream` | SSE: `message.delta` (`kind: "thinking"|"text"`), `message.thinking_done`, `message.done` (with `routing`, `usage`, `cost`), and for PromptCadence `plan`, `step`, `tool_call`, `egress_decision`, `approval_pending`, `halt` — each a persisted row, replayable by `Last-Event-ID` |
| `POST /chat/conversations/{id}/attachments` | Multipart, text/markdown only, ≤ `chat.max_attachment_bytes` |
| `POST /chat/conversations/{id}/approvals/{approval_id}` | `{"decision": "approve"|"deny", "reason"}` → PromptCadence's `approve`/`deny` with the `approve`-scoped token |

## 7. Jobs, alerts, audit

| Endpoint | Purpose |
|---|---|
| `GET /jobs` · `POST /jobs` · `GET /jobs/{id}` · `POST /jobs/{id}/cancel` | The queue, newest first, filtered by `state` and `kind`. `POST` takes `{"kind", "params"}` — `freeweight_suite_run` (`model`, `suite`, `allow_prompt_override`), `retention_trim` (`guarded_backup_days`, `freeweight_older_than_days`), `backup` (`apps`), `model_refresh` (`apps`), `catalog_pull` (`name`), `docs_index`, `self_restore` (`file`, plus `"name_typed": "weightroom"`) — or `{"schedule_id"}` to run a schedule now; `202` with the job. `self_restore`, and a `retention_trim` that sets `freeweight_older_than_days`, need a fresh `POST /reauth` (ADR-0136, ADR-0134 rule 2). A job carries its captured `output` (the tail, capped at `jobs.output_cap_bytes`), `error`, `attempt`, `lease_expires_at`, `cancel_requested_at` and `audit_id`. Cancelling a queued job cancels it; a running one gets `cancel_requested_at` and stops; a finished one is `409 JOB_INVALID_STATE`; an unknown id is `404 JOB_NOT_FOUND` |
| `GET /jobs/schedules` · `PUT /jobs/schedules/{id}` | `{"timezone": "UTC", "schedules": […]}`, each with `cron`, `params`, `enabled`, `next_run_at`, `last_run_at`, `last_job_id` and `problem` (why it cannot be enabled). `PUT` takes any of `cron`, `enabled`, `params`; enabling validates the parameters, and a `retention_trim` whose parameters delete FreeWeight results needs a fresh re-authentication |
| `GET /alerts` · `POST /alerts/{id}/acknowledge` · `GET /alerts/history` | `{"alerts": […], "banner": {"count", "newest"}}` — every active alert (`source`, `label`, `subject`, `severity`, `state`, `opened_at`, `last_seen_at`, `acknowledged_at`, `acknowledged_by`, `summary`, `detail`) and what the banner shows. Acknowledging records the operator and time: a `memory_cap` alert closes, a condition stays active off the banner until it clears ([ADR-0137](../../adr/0137-an-alert-is-an-episode-a-condition-clears-itself-an-event-waits-for-acknowledgement.md)); an unknown id is `404 NOT_FOUND`. The history is every `opened`/`seen`/`acknowledged`/`cleared` event, newest first, paged with a cursor |
| `GET /audit?app=&action=&since=` · `GET /audit/{id}` | The trail; a row carries `operator`, `at`, `app`, `action`, `target`, `params` (redacted), `outcome`, `backup_path`, `dry_run_count`, `actual_count` |

## 8. Docs

| Endpoint | Purpose |
|---|---|
| `GET /docs/tree` | The directory tree under `[docs] root` |
| `GET /docs/page?path=adr/0123-….md` | Rendered HTML with rewritten links and mermaid fences marked; `DOCS_PAGE_OUTSIDE_ROOT` on escape |
| `GET /docs/search?q=` | FTS5 hits with snippets |
| `GET /docs/adrs` | The ADR index parsed from `adr/README.md` |

## 9. Session and trust

| Endpoint | Purpose |
|---|---|
| `POST /login` | Form: `username`, `password`, CSRF token → a new session (the id is regenerated on every login); `429 RATE_LIMITED` after `failed_login_per_minute` |
| `POST /logout` | Deletes the session row and clears the cookie |
| `POST /reauth` | Password again → the session's re-authentication window opens for `auth.reauth_window_minutes`, covering security keys and guarded writes ([ADR-0127](../../adr/0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md) rule 6). It answers `{"reauth_at", "window_minutes", "cookie"}` and **issues no token**: the session cookie is the credential, already `__Host-`, `SameSite=strict` and behind the same-origin check on JSON writes, and a second one would only add something for a script to steal (row W4) |
| `GET /trust` · `GET /trust/root.crt` | The fingerprint, the certificate, the per-OS steps; also served unauthenticated on the trust port and **only** there |
| `GET /settings` · `PUT /settings` | WeightRoomGym's own runtime-changeable keys, ADR-0100's shape |

## 10. Errors

Spec §13's codes in MirrorWall's envelope: `{"error": {"code", "message", "details", "request_id"}}`.
`details` for a `GUARD_*` code carries `condition` (1–5) and the evidence (`unit_state`,
`backup_path`, `dry_run_count`, `tables_in_statement`, `tables_typed`); for `SCHEMA_UNKNOWN`,
`found` and `known`; for `OLLAMA_RESTART_NOT_PERMITTED`, `command` and `rule`.

## 11. Client guidance

The API is for the console's own pages. A script that wants to operate an application should
call that application's API directly; a script that wants what only WeightRoomGym knows (the audit
trail, the alert history, the machine view) uses a browser session's cookie and the CSRF token
for writes, which is deliberately awkward — automation against WeightRoomGym is a future extension
with its own token (spec §21).
