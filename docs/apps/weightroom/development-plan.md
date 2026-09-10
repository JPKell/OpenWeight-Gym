# WeightRoomGym — Development Plan

**Sequence position:** the WeightRoomGym arc, rows W1–W10 of
[`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md), plus the four schema rows
(WS1–WS4) and the MirrorWall 0.3 row (WM) that sit between them.
**Target:** `wr-gym 1.0.0` at the end of Phase 10 — one release (interview decision
D15); every phase below is still gated, and a gate is a commit.
**Reached:** nothing yet. Phase 0 is row W0 (2026-09-09): this document, its five siblings, ADRs
0123–0127, the repository move and the empty skeleton at `0.0.0`.

Two principles order the phases. **Security before reach**: TLS, the login and the audit log
exist before any page can change anything, and the guard exists before any page can write into
another application's database. **Degrade before depend**: every phase's pages render with the
four applications stopped, so a feature is never built assuming a peer is up.

**Every acceptance criterion is demonstrable** — each phase says what to run and what a person
sees. The gate for every phase is the fourteen-repository gate (`ruff format --check .`, `ruff
check .`, `mypy src tests`, `lint-imports`, `pytest -m "not live and not performance"`), CI green,
`CHANGELOG.md` updated, one Conventional Commit per phase; name the interpreter in the report.

---

## Phase 0 — Specification and repository (row W0) — **done 2026-09-09**

ADRs 0123–0127 accepted and indexed; `apps/weightroom/{spec,api,data-model,design,risks}.md`
and this plan; master architecture, executive summary, `MEMORY_SAFETY.md`, `LAN_ACCESS.md`
amended; `expose_on_lan.sh` deleted; the documentation repository becomes the WeightRoomGym
repository with the tree under `docs/`; the skeleton at `0.0.0` with the gate green; the arc's
roadmap file and its kickoff prompts. Handoff: `docs/history/handoffs/W0_HANDOFF.md`.

---

## Phase 1 — Skeleton, configuration, database, TLS, login, `setup` (row W1)

**Goal:** `wr-gym setup && wr-gym serve` gives an HTTPS console with a login on the LAN
and nothing behind the login yet but a shell that says so.

**Prerequisites:** Phase 0.

**Work**
* The standard application layout (master architecture §4); `.importlinter` completed (the
  parenthesised layers un-parenthesised, `web-cli-independence` and `domain-purity` restored);
  `requirements/ci.lock` cut and CI switched to `--require-hashes`; the `db-matrix`, `contracts`,
  `build` and `install-check` CI jobs added in the sibling shape.
* `config.py`: spec §12 in full with the precedence chain, `config show|validate|init|path|
  reference|schema`, the security-key set, startup refusals (`INSECURE_BINDING`, `TLS_MISSING`).
* WeightsDB wiring; Alembic `0001`: `operators`, `sessions`, `audit_log`, `settings`,
  `known_revisions` (seeded with today's four `alembic_version`s).
* `domain/tls.py` + `services/tls.py`: the CA and leaf issuer ([ADR-0126](../../adr/0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)
  rule 2), renewal decision, `tls init|renew|rotate|show`, `wr-gym trust`; uvicorn HTTPS; the
  trust listener on `server.trust_port` serving two routes.
* `domain/auth.py` + `services/auth.py`: scrypt hashing, sessions, the cookie, idle/absolute
  expiry, the login rate limit, `POST /login|logout|reauth`, `operator create|password`;
  MirrorWall's CSRF middleware and the same-origin check on JSON writes.
* The audit service and `GET /audit`; every state-changing route from here on writes a row.
* `wr-gym setup`: TLS, the operator account, `allowed_hosts` from the host's names and
  addresses, `server.host` chosen by the operator (loopback or the LAN interface), the
  application tokens (rule 8 — created only for an installed application, stored by file
  reference), linger. Units are Phase 2; the wizard prints that it will return for them.
* MirrorWall base: envelopes, request IDs, health, the theme toggle; a placeholder shell.
* `GET /health`, `/version`, `/system/status` (applications reported `unknown` until Phase 2).

**Tests**
* Config precedence field by field; every startup refusal with its message.
* Migration up/down both dialects; backup/restore.
* TLS: SANs, lifetimes, the renewal decision at 31/29 days, rotation revoking sessions; the leaf
  validates against the root with `cryptography` and with `openssl verify`.
* Auth: fixation (a new id on login), idle and absolute expiry, logout, rate limit, constant-time
  compare, the cookie's flags, `Sec-Fetch-Site`/`Origin` on JSON writes, CSRF on forms.
* The trust listener: `/root.crt` and `/trust` 200 without a cookie; every other path 404;
  no `Set-Cookie` ever.
* Audit: a test enumerates every state-changing route and asserts one row each.

**Acceptance criteria**
1. On the reference machine: `wr-gym setup` (answering the prompts), `wr-gym serve`;
   on a phone on the LAN, open `http://<host>:8770/trust`, install the root, open
   `https://<host>.local:8769`, see the padlock and the login, log in, see the shell.
2. `curl http://<host>:8769/` connects to nothing; `curl -k https://<host>:8769/api/v1/version`
   answers without a cookie; `/api/v1/health` answers `401`.
3. `wr-gym tls show` prints the fingerprint that the phone's certificate details show.
4. Gate clean; CI green.

**Known risks:** the CA on Android (the *CA certificate* store, not the VPN one) — documented in
`LAN_ACCESS.md` §3, verified on one real device.
**Gold standards:** zero-config loopback start; honest refusal off loopback; G23 with the cookie
variant.
**Deferred:** everything that touches another application.

---

## Phase 2 — Process control, unified logs, audit (row W2)

**Goal:** the four applications and WeightRoomGym run as units the console wrote; the console
starts, stops and tails them, and the audit log shows it did.

**Prerequisites:** Phase 1.

**Work**
* `domain/units.py`: the unit-file template ([ADR-0125](../../adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
  rule 1), rendering from configuration, the diff. `services/processes.py`: a `SystemdController`
  port with the real subprocess implementation and a fake; `units sync|status|start|stop|restart`;
  `wr-gym setup` gains the units step and linger.
* `services/journal.py`: `journalctl --user -o json` history and follow; the SSE line stream with
  MirrorWall's bounded queues; the unified stream across applications plus WeightRoomGym's own log.
* Ollama: `systemctl show`, the `MEMORY_SAFETY.md` §2.1 checklist, the polkit rule text and
  install command, restart when permitted (rule 5).
* `GET /apps`, `/apps/{app}`, `/apps/{app}/health`, the start/stop/restart routes, the logs
  routes, `GET /ollama`, `POST /ollama/restart`; `wr-gym apps status`, `wr-gym logs`.
* The Audit page.
* Application version negotiation: `GET /api/v1/version` per application with the five-minute
  recheck; `APP_VERSION_MISMATCH`.

**Tests**
* Unit rendering golden per application; the memory lines only on `freeweight`/`loadcoach`;
  `units sync` idempotent, reporting changed files.
* The controller with a fake `systemctl`/`journalctl` on `PATH`: each verb's argv (never a shell),
  failure text surfaced, `UNIT_UNSUPPORTED` without the binary.
* Journal streaming: replay, the dropped-lines frame under a slow consumer.
* Ollama: the checklist over fixture `systemctl show` output (the reference machine's current
  override — 112 000 context, no cap — is the *failing* fixture); restart refused with the
  command when the rule is absent.
* Every action audited.

**Acceptance criteria**
1. `wr-gym units sync` writes five units; the LoadCoach tab's Overview shows *stopped*, its
   start button starts it, the pill turns `ok · 0 h 0 m`, the log pane fills live, and the audit
   page shows `unit.start loadcoach` with the operator's name.
2. Stopping LoadCoach from the console and refreshing shows *stopped* again, with every page
   still rendering.
3. The Ollama pane on the reference machine shows the §2.1 checklist with the cap lines missing
   and prints `docs/scripts/apply_memory_safety.sh`; after the operator runs it, the pane goes
   green on the next refresh.
4. `sudo` appears nowhere in the source (a grep test).

**Known risks:** linger on a machine that has never lingered; the journal group permission for
`ollama.service`.
**Gold standards:** honest degradation; G12 (no secret in a subprocess environment).
**Deferred:** telemetry, control surfaces.

---

## Phase 3 — Telemetry strip and shell (row W3; after row WM)

**Goal:** the design brief's shell, live.

**Prerequisites:** Phase 2; **row WM** (`mirrorwall 0.3` with the tokens and the seven generic
components from [`design.md`](design.md) §5) published, or pinned as an editable path install
with a `TODO: re-pin on publish`.

**Work**
* `services/telemetry.py`: `sweatmeter` in process, the sampler thread, `telemetry_samples`,
  downsampling, the SSE stream, the history endpoint and pages; resident models from `/api/ps`
  (ModelRack) and LoadCoach's `/models`.
* The shell: top bar with app tabs and status dots, the telemetry strip with meters, the left
  menus per application (pages stubbed to *coming in phase N* where not built), the console pages'
  navigation, the light toggle, the operator chip. Every page from here renders inside it.
* Each application's **Overview** page: pill, four figures (from the API where up, from the
  database at a known revision where not, `—` where neither), the primary table, the log tail.
* `GET /system/telemetry/stream|history`, `GET /system/resident`; `/system/status` completed.

**Tests**
* Sampler cadence and overhead; `—` for every unavailable reading (a fault-injecting reader);
  downsampling; replay.
* Overview per application against recorded API fixtures and against the fixture databases with
  the application "stopped".
* MirrorWall's accessibility checklist over the shell; contrast pairs both themes.

**Acceptance criteria**
1. The reference machine's console matches the artboard: four tabs with dots, the strip moving
   once a second with the GPU, VRAM, temperature, power, RAM, resident model and queue; clicking
   VRAM opens a 24-hour chart.
2. Pull the GPU sensor out (`CUDA_VISIBLE_DEVICES=` on the console process): GPU and VRAM read
   `—`, nothing else changes.
3. Stop all four applications: every tab shows `stopped`, every Overview renders from the
   database with its revision named in the footer.

**Known risks:** `sweatmeter`'s `nvidia-smi` cost on a busy card.
**Gold standards:** G5; the design brief's contrast rows.
**Deferred:** settings, docs, chat, DB viewer.

---

## Phase 4 — Settings forms over the schema verbs, and the doctor (row W4; after WS1–WS4)

**Goal:** every application's configuration editable from the console with the application's
own validation, and one doctor over the machine.

**Prerequisites:** Phase 3; **rows WS1–WS4** (each application's `config schema --json` and
`config validate --file`) released, or the console degrades that application's settings page to
the raw editor with the reason.

**Work**
* `services/settings_forms.py`: the schema document reader, the form model generator, `sources`
  and `shadowed` rendering; the security-key set and re-authentication.
* `services/config_files.py`: the `tomlkit` round-trip, validate-before-write via the
  application's verb, atomic replace, `.bak`, `base_mtime`, the raw editor path.
* Runtime keys through each application's `PUT /settings`; *pending restart* state; the restart
  button. Provider registrations through the existing ADR-0117 forms where the application has
  them.
* WeightRoomGym's own settings page, from its own schema verb.
* The doctor: findings per rule with severity and the printed command — `MEMORY_SAFETY.md` §2.1
  and §2.2, `LAN_ACCESS.md` (an application off loopback; Ollama on `0.0.0.0` as a notice),
  application versions and revisions in range, TLS expiry, linger, the polkit rule, disk space
  under each data root, the four `[server]` blocks `expose_on_lan.sh` may have left.
* Tokens pages per application (`token list`, `create` with the one-time display, `revoke`).

**Tests**
* Form generation golden per application document; a field added to a fixture document
  appears (spec §20 #5).
* Round-trip: every application's `EXAMPLE_CONFIG_TOML` with comments, edited one key at a time,
  byte-identical elsewhere.
* Validation refusal surfaced verbatim; `CONFIG_CHANGED_ON_DISK`; `REAUTH_REQUIRED`;
  `SETTING_CONFIG_ONLY` passthrough.
* Doctor rules each with a passing and a failing fixture.

**Acceptance criteria**
1. Change LoadCoach's `routing.min_confidence` from the console with LoadCoach running: the
   value is live within a second (`loadcoach config show` shows `(database)`), no restart.
2. Change `server.port` on FreeWeight: the password prompt appears, the write lands with the
   comment above the key intact (`diff config.toml config.toml.bak`), the page says *pending
   restart*, the restart button applies it, and the audit row says *security key*.
3. Add a field to a fixture schema document in a test and watch it appear in the rendered form
   with no code change.
4. `wr-gym doctor` on the reference machine lists the memory-safety gaps and the
   `OLLAMA_HOST` notice with the commands to run.

**Known risks:** a schema document that names a key the file uses a different spelling for
(`provider` vs `providers`) — the raw editor is the escape hatch.
**Gold standards:** configuration standards §7 and §8 held through another process.
**Deferred:** docs, chat, DB viewer.

---

## Phase 5 — Docs viewer (row W5)

**Goal:** the suite's documentation readable from the console, searchable, with diagrams.

**Prerequisites:** Phase 3.

**Work**
* `services/docs.py`: the root, containment, the tree, `mistune` rendering with a sanitising
  renderer (no raw HTML), heading ids and an outline, relative-link rewriting to viewer routes,
  outside-root links to text, mermaid fences left as `<pre class="mermaid">` for the vendored
  client renderer loaded only on pages that have one.
* The FTS5 index (`docs_index`), `wr-gym docs index`, the `docs_index` job kind, search with
  snippets; the ADR index parsed from `adr/README.md`; the *degraded* LIKE fallback.
* Pages: tree, page, search, ADR index.

**Tests**
* Containment (symlink out, `..`, absolute); rendering goldens for a table, a fence, a mermaid
  block, a footnote; link rewriting; search hits; the sanitiser against `<script>` and `{{ }}`
  in a document.

**Acceptance criteria**
1. Open Docs on the phone: the tree, `architecture/master-architecture.md` with its mermaid
   graph rendered, `adr/README.md` as an index of 127 rows, and a search for `never zero` landing
   on ADR-0016.
2. A document with `<script>` in it renders the tag as text.

**Known risks:** mermaid's size (T7).
**Gold standards:** §15's docs budgets.
**Deferred:** chat, DB viewer.

---

## Phase 6 — Chat: LoadCoach, then PromptCadence, thinking collapse (row W6)

**Goal:** a conversation with a model through the two governed paths, with every decision shown.

**Prerequisites:** Phase 4 (tokens); LoadCoach ≥ 1.3 and PromptCadence ≥ 1.3 recorded fixtures.

**Work**
* `domain/chat.py`: conversations, messages, the event model, the thinking state machine
  (thinking → text collapses; `done` collapses; no thinking channel shows none).
* `services/chat_loadcoach.py`: `POST /generate/stream` with the task profile, override,
  attachments prepended as context; the routing decision from `/jobs/{id}/explanation`; usage
  and cost with unpriced counts; `null` stays `—`.
* `services/chat_promptcadence.py`: `POST /trajectories`, the stream, plan/step/tool/egress
  rows, pending approvals rendered with approve/deny, `approve`/`deny` with the `approve`-scoped
  token, halts named verbatim.
* Attachments: upload, type and size checks, storage, the context block.
* Pages: the conversation list, the thread with streamed markdown (`mistune`, sanitised), code
  blocks with copy, the collapsible thinking `<details>`, the decision and cost line, the inline
  cards. `message_events` persisted and replayable.

**Tests**
* The thinking state machine over recorded streams (with, without, and interrupted thinking).
* Both backends against recorded fixtures; `CHAT_BACKEND_UNAVAILABLE` when down; the approval
  round trip; the injection corpus rendered inert.
* A network-isolation test: no socket to anything but the two configured base URLs.
* Import-linter: no `modelrack.generate` (a grep test as well).

**Acceptance criteria**
1. On the phone: a LoadCoach conversation on `general.chat`; the thinking block streams, collapses
   when the answer starts, expands on tap; under the reply: the model chosen, `9 candidates · 2
   rejected`, tokens by class, `— · local`.
2. A PromptCadence conversation with `read_file` allowed: the plan card, the step, the tool
   call with its result, the egress decision, and — with `[approval] mode = "hybrid"` — an
   approval that the tap grants; `promptcadence trajectory show` shows `approver:weightroom`.
3. With both applications stopped, the send button is disabled with the reason and old
   conversations still read.

**Known risks:** LoadCoach's stream chunk classes for thinking on a given provider (I6 in
[risks](risks.md)).
**Gold standards:** M1 in risks; G12.
**Deferred:** DB viewer.

---

## Phase 7 — Database viewer and the guard (row W7)

**Goal:** every application's database readable; a raw write only under the five conditions.

**Prerequisites:** Phase 4 (the connection strings from the schema documents).

**Work**
* `domain/guard.py`: the five conditions as a checklist with verdicts, the never-writable list as
  data, statement classification (`SELECT`/`WITH` vs DML vs refused DDL), table extraction.
* `services/db_reader.py`: read-only connections per application (SQLite `mode=ro`, PostgreSQL
  read-only), the revision check against `known_revisions`, tables with counts, the row grid, the
  SQL console with timeout and cap.
* `services/db_guard.py`: the unit check, the backup through `weightsdb.backup`, the rolled-back
  dry run, the typed names, the pending → ok audit row, the single-statement write on its own
  connection.
* Curated operations wired per table (FreeWeight delete-by-model with preview, retention
  settings, vacuum, backup, upgrade, restore).
* Pages: tables, grid, console, the guard dialog with live verdicts.

**Tests**
* The guard: each condition failed alone → its `GUARD_*` code; all five → success with the
  backup on disk and the audit row complete; a crash injected between the audit `pending` and the
  statement leaves the pending row.
* Never-writable: every name in the ADR-0124 table refused; the list compared against the
  fixture databases' tables (no unknown name).
* Statement classification: DDL refused, multi-statement refused, `PRAGMA` refused.
* Both dialects.

**Acceptance criteria**
1. Browse FreeWeight's `samples` table; run `SELECT count(*) FROM samples` in the console.
2. Try `DELETE FROM samples WHERE run_id = '…'` with FreeWeight running: the dialog shows
   condition 1 red and refuses. Stop FreeWeight, retry: backup taken (path shown), dry run
   `412 rows`, statement echoed, type `samples`, password, run — the audit row shows all of it and
   `ls ~/.local/share/wr-gym/backups/freeweight/` shows the file.
3. Try `UPDATE routing_decisions …`: refused, *never writable from WeightRoomGym (ADR-0124)*.

**Known risks:** T2 in [risks](risks.md).
**Gold standards:** database standards §8 held from outside the owning application.
**Deferred:** catalog, costs, backups pages.

---

## Phase 8 — Model catalog, costs, backups and migrations (row W8)

**Goal:** the machine's models, money and backups in one place.

**Prerequisites:** Phase 7.

**Work**
* `services/catalog.py`: the join across applications by canonical identity; evidence freshness
  from FreeWeight; residency; `ollama pull` as a `catalog_pull` job with streamed progress and a
  free-space check; GGUF drop-in with magic-byte and containment checks then `models refresh`;
  enable/disable per application; delete with cleanup (preview, typed confirm, `ollama rm` or the
  file, each application's `db delete --model`).
* `services/costs.py`: `loadledger.sql` reads from PromptCadence's and IdeaPress's databases,
  balances per window against configured ceilings, unpriced counts everywhere.
* Backups and migrations pages: `db status|backup|upgrade|restore` per application as curated
  calls; the backup listing; WeightRoomGym's own.
* Pages: Catalog, Costs, Backups.

**Tests**
* The join over fixture databases; enable/disable against recorded API; drop-in refusals (bad
  magic, outside directory, oversize); delete preview equals what is removed; pull progress
  parsing; costs with unpriced counts; the ceiling verdicts; restore refused while running.

**Acceptance criteria**
1. Catalog shows every model on the reference machine once, with per-application enabled state
   and evidence; disable `gpt-oss:20b` for LoadCoach and `loadcoach route explain --task
   general.chat` shows `model_disabled`.
2. Pull a small model from the console and watch the progress; drop a GGUF into the llama.cpp
   directory and see it appear after refresh.
3. Costs shows PromptCadence's today against its daily ceiling with `unpriced: 3`.
4. Back up LoadCoach from the console; the file is in LoadCoach's own `backups/`.

**Known risks:** M2 in risks (disk).
**Gold standards:** ADR-0016 in every money cell; database standards §8 for delete.
**Deferred:** jobs, alerts, prompts.

---

## Phase 9 — Jobs, alerts, prompt editor (row W9)

**Goal:** the console does things on a schedule, tells the operator when the machine misbehaves,
and edits prompts as records.

**Prerequisites:** Phase 8.

**Work**
* `domain/jobs.py` + `services/jobs.py`: the queue with leases, the worker thread, heartbeat,
  recovery at startup, the four shipped kinds plus `catalog_pull` and `docs_index`; schedules
  with a five-field cron parser (stdlib only); history and output capture.
* `services/alerts.py`: the evaluator thread, the five sources, open/seen/acknowledged/cleared,
  the banner, the history page.
* `services/prompts.py`: pack listing via each application's `prompts list|show`, overrides under
  the application's config root, validation with `setspec.prompts`, the diff view, delete-override.
* Pages: Jobs (queue, schedules, history), Alerts, Prompts per application.

**Tests**
* Lease expiry and requeue; cancel states; cron parsing goldens; schedule catch-up after
  downtime (run once, not N times).
* Alerts: each source with a firing and a clearing fixture (a journal line with `oom-kill` on
  `ollama.service`; a unit going inactive; a temperature above threshold; a balance over ceiling;
  a breaker row); one open alert per subject; acknowledge; history.
* Prompt override validation, the diff, the `user_override` marking shown.

**Acceptance criteria**
1. Schedule a nightly FreeWeight `native.speed` run; run it now; watch the job's output; the
   run appears in FreeWeight's Runs page.
2. Fire the memory cap on purpose (`MEMORY_SAFETY.md` §2.3): within 30 s the banner shows
   `memory cap fired · ollama.service` with the journal line; acknowledge it; it is in history.
3. Override IdeaPress's `stages.draft.article` prompt from the console, see the diff, run a
   draft, see `prompt_source: user_override` on the attempt; delete the override.

**Known risks:** T6 in risks.
**Gold standards:** ADR-0010/0029 shape; no broker.
**Deferred:** hardening.

---

## Phase 10 — Hardening, performance, documentation, `1.0.0` (row W10)

**Goal:** the security checklist held, budgets measured, operations documented, released.

**Prerequisites:** Phase 9.

**Work**
* Security Standards §14 item by item plus spec §14's rows; the injection corpus against chat;
  redaction sweep over the audit log; a network-isolation e2e.
* Performance: every spec §15 budget measured on the reference machine and asserted.
* Operator documentation: `docs/security.md`, `docs/configuration.md` (generated, diff-checked),
  `docs/setup.md` (the wizard end to end, the per-OS trust steps), `docs/troubleshooting.md`
  aligned with `doctor`, backup/restore, `docs/README.md` (local); the OpenAPI snapshot;
  `api.md` regenerated from it.
* The `docs` symlink at the workspace root removed; every remaining `~/ai/suite/docs` reference
  in scripts and prompts rewritten; `LAN_ACCESS.md` verified against a real second device.
* Gold-standards section verified; `CHANGELOG.md` for `1.0.0`; the release commit (the tag is the
  operator's).

**Tests**
* The full spec §18 table; upgrade from `0.x` migrations; clean-venv install from the lock;
  `pip-audit`/`gitleaks` clean.

**Acceptance criteria**
1. Every spec §20 criterion passes; a verification run on an independent device with explicit
   permission to say *not ready* (the M7/M8 precedent).
2. `wr-gym 1.0.0` prepared; `pipx install wr-gym && wr-gym --version`.

**Known risks:** the verification finding a control surface the recorded fixtures never showed.
**Gold standards:** all of them.
**Deferred:** spec §21.

---

## Rows outside this repository that this plan depends on

| Row | What | Needed by |
|---|---|---|
| **WM** | `mirrorwall 0.3`: the token deltas and the seven generic components of [`design.md`](design.md) §5 | Phase 3 |
| **WS1–WS4** | `config schema --json` and `config validate --file` in FreeWeight, LoadCoach, IdeaPress, PromptCadence ([ADR-0127](../../adr/0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md)) | Phase 4 |
| **WM2** (after W10) | the four applications adopt the 0.3 density, dots, meters, log pane and tab strip | not this arc's 1.0 |
