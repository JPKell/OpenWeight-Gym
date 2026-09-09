# WeightRoom — Public API

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
| `GET /health` | MirrorWall's standard health payload: `database`, `tls` (days to expiry, `degraded` under 30), `units` (systemd reachable, `unsupported` without it), and one component per application named `app:<name>` with `ok`/`degraded`/`stopped`/`unknown`. `200` when WeightRoom's own database and TLS are fine — a stopped application never drops it below 200 |
| `GET /version` | `{"application": "weightroom", "version": "…", "api_version": "v1", "schema_version": "1"}`. Never authenticated ([ADR-0026 §5](../../adr/0026-local-http-hardening.md)) |
| `GET /system/status` | The machine view (spec §17): per application `state`, `version`, `api_version`, `db_revision`, `known`; `ollama` (unit state, cap lines found, residency); `telemetry` (the last snapshot); `costs_today`; `alerts_open`; `jobs_running`; `doctor_last` |
| `GET /system/telemetry/stream` | SSE, one `telemetry.sample` per interval, `—` for unavailable readings; replay from `Last-Event-ID` within the retained window |
| `GET /system/telemetry/history?figure=gpu_util&hours=24` | Downsampled samples for one figure's history page |
| `GET /system/resident` | Resident models: Ollama's `/api/ps` rows and LoadCoach's `/models` residency, each with `source` |
| `GET /doctor` · `POST /doctor/run` | The last doctor report; run it now. Findings carry `severity`, `subject`, `rule` (`memory_safety.2.1.cap`, `lan.app_off_loopback`, …) and, where a root-owned fix exists, `command` — the text to run, never run |

## 2. Applications

| Endpoint | Purpose |
|---|---|
| `GET /apps` | The four, with `installed`, `executable`, `unit` (`active`/`inactive`/`failed`/`absent`/`unsupported`), `version`, `base_url`, `db_revision`, `known` |
| `GET /apps/{app}` · `GET /apps/{app}/health` | One application; its own `/api/v1/health` proxied verbatim with `source: "api"` or `{"state": "stopped"}` |
| `POST /apps/{app}/start` · `/stop` · `/restart` | `systemctl --user <verb> <app>.service`; `202` with the audit id, then the unit state; `UNIT_UNSUPPORTED` without systemd, `UNIT_ACTION_FAILED` with systemd's message |
| `GET /apps/{app}/logs?since=&until=&level=&q=` | Journal history, JSON lines, capped at 5 000 rows per page with a cursor |
| `GET /apps/{app}/logs/stream` · `GET /logs/stream?apps=` | SSE of journal lines, one application or several; WeightRoom's own log under `weightroom` |
| `GET /apps/{app}/config` | The raw `config.toml` text and its mtime (the editor's base) |
| `GET /apps/{app}/settings/schema` | The application's schema document ([ADR-0127](../../adr/0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md) rule 1), cached for 60 s; `APP_NOT_INSTALLED` when the executable is absent |
| `GET /apps/{app}/settings` | Effective values with per-key `source` and `shadowed_by`, the runtime-changeable set, the security set |
| `PUT /apps/{app}/settings` | `{"changes": {key: value}, "base_mtime": …, "reauth": "<token from POST /reauth>"}`. Runtime keys go to the application's `PUT /settings`; file keys are written in place (`tomlkit`), validated via `config validate --file`, renamed with `.bak`. Answers per key: `applied` (live), `written` (pending restart), `refused` (with the application's message). `CONFIG_CHANGED_ON_DISK` when `base_mtime` is stale; `REAUTH_REQUIRED` when a security key is present without a fresh re-authentication; `APP_STOPPED` for a runtime key while the application is down (the file path is offered) |
| `POST /apps/{app}/settings/validate` | A candidate file body → the application's validation verdict, unchanged |

## 3. Databases

| Endpoint | Purpose |
|---|---|
| `GET /apps/{app}/db/revision` | `alembic_version`, whether WeightRoom knows it, and the range it knows |
| `GET /apps/{app}/db/tables` | Tables with row counts, `writable` (false for the [ADR-0124](../../adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md) list, with `reason`), and the curated operations available per table |
| `GET /apps/{app}/db/tables/{t}?page=&sort=&filter=` | A page of rows, columns typed |
| `POST /apps/{app}/db/query` | `{"sql": "SELECT …"}` on a read-only connection, 30 s, 10 000 rows; anything but a single `SELECT`/`WITH` is `GUARD_STATEMENT_REFUSED` |
| `POST /apps/{app}/db/write/dry-run` | `{"sql": …}` → the statement echoed, the tables it touches, the affected row count from a rolled-back transaction, the unit's state, and the guard's checklist with each condition's current verdict |
| `POST /apps/{app}/db/write` | `{"sql": …, "tables_typed": ["samples"], "dry_run_id": …, "reauth": …}` → runs the guard: `GUARD_APP_RUNNING`, `GUARD_BACKUP_FAILED`, `GUARD_DRY_RUN_FAILED` (the dry run is repeated and must match), `GUARD_TABLE_MISMATCH`, `GUARD_TABLE_LOCKED`; success returns the audit id, the backup path and the row count |
| `GET /apps/{app}/db/status` · `POST /apps/{app}/db/backup` · `GET /apps/{app}/db/backups` · `POST /apps/{app}/db/upgrade` · `POST /apps/{app}/db/restore` | Curated calls to the application's own `db` verbs; `restore` requires the unit stopped and `{"file": …, "name_typed": "<app>"}` |

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
| `POST /catalog/pull` | `{"name": "gemma4:12b-it-q8_0"}` → a job id; `GET /catalog/pull/{id}/stream` is its progress |
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
| `GET /jobs` · `POST /jobs` · `GET /jobs/{id}` · `POST /jobs/{id}/cancel` | The queue; `POST` takes `{"kind": "freeweight_suite_run"|"retention_trim"|"backup"|"model_refresh", "params": {…}}`; `JOB_INVALID_STATE` on cancelling a finished job |
| `GET /jobs/schedules` · `PUT /jobs/schedules/{id}` | Cron-style schedules per kind, with `next_run_at`, `last_run_at`, `enabled` |
| `GET /alerts` · `POST /alerts/{id}/acknowledge` · `GET /alerts/history` | Open alerts; acknowledge; the history |
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
| `POST /reauth` | Password again → a short-lived re-authentication token for security keys and guarded writes ([ADR-0127](../../adr/0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md) rule 6) |
| `GET /trust` · `GET /trust/root.crt` | The fingerprint, the certificate, the per-OS steps; also served unauthenticated on the trust port and **only** there |
| `GET /settings` · `PUT /settings` | WeightRoom's own runtime-changeable keys, ADR-0100's shape |

## 10. Errors

Spec §13's codes in MirrorWall's envelope: `{"error": {"code", "message", "details", "request_id"}}`.
`details` for a `GUARD_*` code carries `condition` (1–5) and the evidence (`unit_state`,
`backup_path`, `dry_run_count`, `tables_in_statement`, `tables_typed`); for `SCHEMA_UNKNOWN`,
`found` and `known`; for `OLLAMA_RESTART_NOT_PERMITTED`, `command` and `rule`.

## 11. Client guidance

The API is for the console's own pages. A script that wants to operate an application should
call that application's API directly; a script that wants what only WeightRoom knows (the audit
trail, the alert history, the machine view) uses a browser session's cookie and the CSRF token
for writes, which is deliberately awkward — automation against WeightRoom is a future extension
with its own token (spec §21).
