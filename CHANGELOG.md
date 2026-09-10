# Changelog

All notable changes to WeightRoomGym (distribution `wr-gym`) are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.6.0] — 2026-09-10

Row W6: Phase 6 of the development plan — chat through LoadCoach and PromptCadence, thinking that
streams and collapses, the routing decision and cost under every reply, PromptCadence's plan, steps,
tools, egress and approvals inline. Prepared, not tagged, not pushed, not published.

### Added
- **The chat model and the thinking state machine** (`domain/chat.py`, migration `0004`):
  `conversations` with a check constraint naming the two backends and no third (spec §11 contract
  6), `messages`, `message_events` and `attachments`. Thinking opens on the first thinking delta,
  collapses on the first text delta that is not whitespace or on the terminal frame, never
  reopens, fills from the result when a backend reports it only at the end, and shows no block for
  a provider with no thinking channel.
- **Chat through LoadCoach** (`services/chat_loadcoach.py`): the whole conversation as
  `messages`, the task profile and optional model pin, live `thinking` and `token` frames, the
  routing line from the stream's own `routing` frame, tokens by class with `—` for anything
  unreported and money only where priced.
- **Chat through PromptCadence** (`services/chat_promptcadence.py`): one trajectory per message
  with the conversation so far as context, the tool allowlist always sent (an omitted one is every
  tool to PromptCadence), plan/step/tool-call cards as the events arrive, recorded egress
  decisions at the end, the answer from the last assistant turn, halts in PromptCadence's own
  words, and approvals granted or denied inline with the `approve`-scoped token — a token without
  the scope shows *no approve scope* and no button that would fail.
- **Replies run beside the request** (`services/chat.py`): a small thread pool, one persisted row
  per step, and one transaction on completion that fills the message, drops the deltas and writes
  `done` or `halt` (ADR-0044). The page's stream replays by `Last-Event-ID`. A reply interrupted by
  a console restart is closed as a named halt at startup.
- **Attachments**: text and markdown only, capped, stored `0600` under a generated name, prepended
  as fenced context to every request of the conversation.
- **Nothing raw**: live deltas reach the page as `textContent`; the finished answer is rendered by
  an escape-on markdown renderer (http(s) links only, images reduced to alt text so nothing a
  model wrote is fetched) and handed to Jinja through `__html__`; no chat template marks anything
  safe. PromptCadence's own injection corpus is rendered through every path into a thread.
- `chat.create`, `chat.message`, `chat.attachment`, `chat.delete`, `chat.approve` and `chat.deny`
  join the audit vocabulary; `CHAT_BACKEND_UNAVAILABLE`, `ATTACHMENT_TOO_LARGE` and
  `ATTACHMENT_TYPE_REFUSED` join the error codes.
- A network-isolation test: a reply through either backend reaches the two configured base URLs
  and nothing else, and opens no raw socket.

### Found, and fixed where they live
- **LoadCoach dropped live thinking** (ADR-0132, `loadcoach 1.5.0`): ModelRack streamed each
  reasoning delta and LoadCoach forwarded only answer tokens, so thinking arrived after the answer.
  LoadCoach now streams a `thinking` frame; this console falls back to `result.reasoning` for an
  older LoadCoach.
- **MirrorWall refused every multipart form** as `CSRF_FAILED` — the token was searched for with a
  parser that cannot read multipart. Fixed in MirrorWall (`[Unreleased]`); attachment uploads
  depended on it.
- **PromptCadence could not run any trajectory on the reference machine**: LoadCoach requires a
  bearer token once any exists, and PromptCadence had none. A LoadCoach token was minted for it and
  configured by reference (host change, recorded in the W6 handoff).
- The security checklist's Phase 1 *no uploads* test is now an allowlist of the two attachment
  routes.
### Fixed

- The console no longer floods LoadCoach with `GET /api/v1/system/status`. Every telemetry
  stream read LoadCoach's queue on each pass of its poll loop — five a second per stream, two
  streams per tab — until LoadCoach's rate limiter answered 429 and its journal filled with
  `request.rate_limited`. The sampler now reads it once per tick and every stream, page and
  `/system/status` call shares that read.
- The per-application Overview's log pane showed raw JSON envelopes: MirrorWall's `log_pane` swaps
  each frame's data in as-is. It now uses the same pane `/logs` does, which is a classic script
  (a module script has no `document.currentScript`) with its own toolbar rather than MirrorWall's
  stacked `.field` form layout.
- The log stream stops reconnecting once it is over. An `EventSource` cannot tell a stream the
  server ended from a connection that dropped, so it retried both — and a host with no
  `journalctl` ended the stream the same way on every retry, which is the repeated `GET` on
  `…/logs/stream` in the access log. The error frame is now followed by `log.closed`, the pane
  closes on it, and MirrorWall's own pane carries `sse-close`.
- The telemetry strip is live. The shell now loads MirrorWall's `sse.js` and `telemetry.js`
  (both opt-in per application, and neither was loaded), so CPU, RAM, GPU and VRAM show
  measurements instead of the em dashes they held from first paint onwards. RESIDENT and QUEUE
  wait for `DOMContentLoaded` before looking for `mirrorwallSse`, which is deferred and did not
  exist when the inline script ran.

### Changed

- The top bar is the artboard's single 48 px row (design brief §4): brand, application tabs,
  console pages, alerts, a compact theme control with a visually hidden label, and the operator
  chip at the right edge. The strip opts into MirrorWall's inline meters for all four fields.
- The console Overview lists the four applications as a dense table with status dots, uptime,
  version and unit, in place of the bulleted links row W3 shipped.
- The shell reflows instead of scrolling sideways, verified in headless Chrome at 1440, 900 and
  390 px on `/`, `/apps/loadcoach` and `/logs` with no element scrolling horizontally. Below
  900 px the top bar's tabs, console pages and theme control collapse into a *Menu* dropdown
  (one `<details>`, open with its summary hidden above the breakpoint, closing on an outside click);
  the left menu is a disclosure named for its section; the telemetry strip wraps and shows values
  without meter tracks; the main pane stretches instead of sizing to its widest line; and the
  Overview table drops its version and unit columns below 600 px. The side menu's version footer
  now sits after the unbuilt pages rather than between them.
- The top bar collapses in two steps instead of wrapping or overlapping: below 1080 px the console
  pages (Chat, Docs, Database, Jobs, alerts) move into a *Menu* dropdown, below 860 px the
  application tabs follow. The theme control and log out moved into an operator menu at the right
  edge, which is what the theme select used to collide with. The telemetry strip wraps rather
  than scrolling at any width, and drops its meter tracks below 1080 px. Swept in headless Chrome
  from 1400 px to 320 px in 10 px steps: no horizontal scroll, no overlapping top-bar item.
- The header reads **WeightRoom** and links to the Overview; page titles and page text say
  WeightRoom too. The distribution, CLI, certificates and documentation keep WeightRoomGym and
  `wr-gym`.
- Applications are displayed by their names — FreeWeight, LoadCoach, IdeaPress, PromptCadence —
  in the tabs, the Menu, the Overview table, the side menu, and page titles and text. Routes,
  units, CLI invocations and config sections keep the lowercase identifier.
- W4's pages follow the same rule now that they sit in that shell: below 700 px the settings
  form, the doctor's findings and the token list stack each row into a card instead of scrolling
  the page, and a long config path or command wraps inside the main pane.

## [0.5.0] — 2026-09-10

Row W5: Phase 5 of the development plan — the documentation viewer. Prepared, not tagged, not
pushed, not published. The one flexible row (any time after W3); built without W4.

### Added
- **`services/docs.py`**: `[docs] root` resolution (configured, else the `docs/` beside this
  checkout, else `DOCS_ROOT_MISSING`); resolve-then-check containment mirroring ToolYard's
  `PathContainment` (read as the containment vector set, never imported — ADR-0123 rule 4); the
  directory tree; a `mistune.HTMLRenderer(escape=True)` renderer built fresh per request (never
  shared — Starlette runs sync routes in a threadpool) with stable heading ids and an outline, a
  `mermaid` fence mounted as `<pre class="mermaid">`, and relative links rewritten to
  `/docs/page` routes only when they resolve to a `.md` file inside the root — everything else
  (outside the root, a non-markdown target, an image; there is no raw-asset route in api.md §8)
  renders as plain text. `adr/README.md`'s own table is the ADR index, never the filenames.
- **`services/docs_index.py`**: migration `0003` creates `docs_index` as an FTS5 virtual table on
  SQLite when the module is compiled in, a plain three-column table otherwise (spec §13 risk T9),
  and a table with a generated `tsvector` column plus a GIN index on PostgreSQL; `search()`
  degrades to a parameterised `LIKE` query — labelled `degraded=True` — on a malformed FTS5 query
  or a missing FTS5 module alike, rather than a 500 from a search box. `wr-gym docs index`
  rebuilds it from the tree.
- `GET /docs/tree`, `GET /docs/page?path=`, `GET /docs/search?q=`, `GET /docs/adrs` (JSON,
  api.md §8) and their HTML pages inside the shell (`/docs`, `/docs/page`, `/docs/search`,
  `/docs/adrs`); the top bar's "Docs" entry is a real link now, not a stub.
- **mermaid 11.17.2 vendored** (`web/static/vendor/mermaid/`, MIT, offline, ~3.4 MB — spec §15's
  one exception to the per-page JS budget) and mounted at `/app-static/`
  (`mount_static`'s `extra_dirs`, a WeightRoomGym-owned static root distinct from MirrorWall's);
  loaded only on a page whose document contains a `mermaid` fence, with `securityLevel: "strict"`
  (a diagram's source is untrusted document content, security standards §6).

### Changed
- `services/health.py`'s `STATUS_BY_CODE` gains `DOCS_ROOT_MISSING` (500) and
  `DOCS_PAGE_OUTSIDE_ROOT` (404).
- The security checklist's "no route accepts a path-shaped parameter" test now carries a named,
  reviewed allowlist (`/docs/page`'s `path`, both the JSON and HTML routes) rather than refusing
  the documentation viewer's one legitimate, contained exception outright.

### Decided
- **`docs_index`'s FTS5 shadow tables are excluded from the migration-parity check by name**
  (`FTS5_SHADOW_TABLES`, `tests/integration/test_migrations.py`) — SQLite's FTS5 module creates
  five bookkeeping tables alongside the virtual table itself, none of which is or should be
  modelled in `Base.metadata`.
- **No raw-asset route this row.** A markdown image or a link to a non-`.md` file renders as
  plain text rather than a broken link — api.md §8 names four routes and none of them serves a
  raw file. A later row can add one if the documentation ever needs embedded images rendered.
- **The ADR index kickoff's demonstration number is stale.** The row's own prompt says "the ADR
  index of 127 rows"; the real `adr/README.md` carries 129 as of this row (ADRs 0128–0129 landed
  at W3/WM). Rendered as whatever is actually there, not force-fit to 127.

## [0.4.0] — 2026-09-09

Row W4: Phase 4 of the development plan — every application's settings editable from the console
through its own schema and its own validation, the doctor, and per-application token pages.
Prepared, not tagged, not pushed, not published.

### Added
- **Settings forms generated from each application's schema document** (`services/settings_forms.py`,
  ADR-0127 rule 3): `<app> config schema --json` is read (a subprocess for the four, in process
  for WeightRoomGym's own), cached 60 s, and turned into a form model — type, bounds, default,
  description, current value, `source`, *shadowed*, and the runtime and security sets. **No key of
  any application is named in this repository**; a field added to an application appears on the
  next read. The key list is the document's own three sets rather than a walk of `json_schema`,
  which is what makes LoadCoach's database-only `queue.paused`, IdeaPress's eleven
  `models.stages.<stage>` bindings and PromptCadence's `[tiers.<name>]` instances render at all.
- **The write paths** (`services/config_files.py`): ADR-0117's sequence applied to every key of
  every application's file from outside the process that owns it — refuse a stale `base_mtime`
  (`st_mtime_ns`, exact in JSON), round-trip with `tomlkit` so every comment and untouched line
  survives, validate the candidate through `<app> config validate --file`, then `fsync` and
  rename with the previous file kept as `config.toml.bak`.
- `GET /apps/{app}/settings/schema` · `GET|PUT /apps/{app}/settings` ·
  `POST /apps/{app}/settings/validate` · `GET /apps/{app}/config`, with per-key outcomes
  (`applied`, `written`, `unchanged`, `refused`) and the refusing party's own words;
  `GET|PUT /settings` for the console's own runtime keys (ADR-0100's shape).
- **Pages**: `/apps/{app}/settings` for each of the four, `/settings` for WeightRoomGym itself
  from its own verb, and `/apps/{app}/settings/raw` — the whole-file editor, deliberately on its
  own page because it shows the file's secrets verbatim.
- ***Pending restart*** and the restart button, derived from the file's modification time against
  the unit's uptime rather than stored, so a restart made from a terminal is seen and a console
  restart does not lose the state.
- **`wr-gym doctor` and the Doctor page** (`services/doctor.py`): one finding per rule with a
  severity, the evidence it actually read and the command that fixes it — `MEMORY_SAFETY.md` §2.1
  (Ollama's daemon) and §2.2 (each unit's memory cap), an application off loopback and Ollama on
  `0.0.0.0` (`LAN_ACCESS.md` §1 and §5), versions and schema revisions in range, TLS expiry,
  lingering, the polkit rule, free space under each data root, and the `[server]` block the
  retired `expose_on_lan.sh` left behind. **Every fix is printed and none is run**; the command
  exits `1` on a failure or a warning and `0` on a notice.
- **Tokens pages** (`services/tokens.py`): `token list|create|revoke` through each application's
  own CLI. A new token's secret is shown once, on the page that minted it, and is stored nowhere.
  LoadCoach and PromptCadence have the verb; FreeWeight's tokens are `auth.tokens` on its settings
  page and the page says so; IdeaPress has none.
- `settings.validate`, `token.create` and `token.revoke` join the closed audit vocabulary.
- **[ADR-0130](docs/adr/0130-weightroomgyms-application-tokens-carry-admin-scope.md)**: the
  wizard's tokens carry `admin` (`{"loadcoach": "admin", "promptcadence": "admin,approve"}`).
  Found demonstrating Phase 4 criterion 1 on the reference machine — ADR-0126 rule 8 chose
  `write` before the settings page existed, and both applications' `PUT /settings` requires
  `admin`, so every runtime key was readable and none was writable. `wr-gym doctor` reports an
  install whose token is narrower and prints the two commands that re-issue it.

### Changed
- **Re-authentication for a security key is the session, not a token** (ADR-0127 rule 6). api.md
  §2 sketched a `reauth` token on the write body; W1 already implements the window as a stamp on
  the session row, and a second credential in the DOM would be strictly worse on a LAN-facing
  page with nothing to gain. The page posts the password with the change; the window opens and is
  spent in the same request. `docs/apps/weightroom/api.md` is amended to match.
- An application's side nav links the pages this build serves and says where a page that is
  deliberately somebody else's lives — a provider registration stays in the application's own
  ADR-0117 form.

### Fixed
- `services/ollama.py`: a polkit-grant probe against an unmigrated or unreadable audit trail
  answers `unknown` instead of raising, so `wr-gym doctor` runs on a fresh install.
- `services/overview.py`: IdeaPress calls `config show --json`'s block `settings` where the other
  three call it `values`, so its Overview could not find its database and fell back to the dashed
  figures. Both spellings are read. Found by the doctor's revision rule on the reference machine.
- The `settings.write` audit row's flag is `touched_security`, not `security_key`: the redactor
  blanks any parameter whose name matches `key`, and a redacted boolean reads like a caught leak.

## [0.3.0] — 2026-09-09

Row W3: Phase 3 of the development plan — the telemetry sampler, the real shell over MirrorWall
0.3, and each application's Overview page. Prepared, not tagged, not pushed, not published;
MirrorWall 0.3.0 pinned as an editable path install (prepared, not yet published itself —
TODO: re-pin `mirrorwall==0.3.0` once it is).

### Added
- **`services/telemetry.py`**: `sweatmeter` in process, one `TelemetryService` owning a
  `TelemetrySampler` thread that writes one `telemetry_samples` row per tick (migration `0002`),
  every unavailable reading `NULL`, never `0` (ADR-0016). Resident models cached on a five-second
  cadence rather than asked every tick; LoadCoach's queue depth is read live per frame and never
  persisted. A background sweep keeps rows older than an hour at one per minute and drops
  anything past `[telemetry] history_hours`, grouped in Python so the same sweep runs on SQLite
  and PostgreSQL.
- `GET /system/telemetry/stream` — SSE, replaying from `Last-Event-ID` by polling the store for
  rows after the highest id already seen, the same pattern `web/routes/apps.py`'s log stream and
  FreeWeight's run event store already use, rather than an in-memory fan-out.
- `GET /system/telemetry/history?figure=&hours=` — one figure's already-downsampled series.
- `GET /system/resident` — Ollama's `/api/ps` through ModelRack and LoadCoach's own residency,
  each row naming its source.
- **The shell** (design brief §4): `_shell.html`, which every operator-facing page now extends
  instead of `mirrorwall/base.html` directly — the four app tabs with status dots
  (`render_shell_page`, reusing `services/health.py`'s own pill-to-status-dot map), the telemetry
  strip with the two WeightRoomGym-specific RESIDENT/QUEUE meters, the console's own page ghosts
  named with the row that builds them, the operator chip, and a per-application left menu with
  Overview linked and every other spec §7.3 page inert and titled with its row where one is
  scheduled.
- **Each application's Overview** (`services/overview.py`): the pill, four figures, the primary
  table, the log tail (MirrorWall's `log_pane`, replacing the pre-0.3 `_log_pane.html` on this
  page only). Figures read `GET /api/v1/system/status` when the application answers and a
  `COUNT(*)` over named tables (data model §4) when it does not; the primary table always reads
  the same tables directly, running or not (a deliberate narrowing from a literal API-when-up
  reading — see the module's own docstring); an unknown `alembic_version` degrades the table by
  name with the application's API-sourced figures unaffected (spec §11 contract 4).
- `GET /system/status` now completes its `ollama` and `telemetry` fields.

### Decided
- **The primary table is database-sourced in every state, not only when stopped.** Each
  application's list endpoint has its own JSON shape that would need reading and pinning
  per application before a row of it could render here; every application already exposes the one
  shape the table needs (`alembic_version` plus a handful of named tables) through the read-only
  connection this row already opens for the stopped case, and spec §10 already lists "database"
  as a legitimate read path generally, not one reserved for a stopped application. W7's guarded
  database viewer is where a *browsable* table belongs; this Overview table is content to be a
  read of the same rows, once.
- **RESIDENT and QUEUE do not refresh in place.** The strip's generic CPU/GPU/RAM fields are
  wired live by MirrorWall's own `telemetry.js`; these two WeightRoomGym-specific meters render
  from the last sample at page load and do not update until an operator navigates again — the one
  corner this row cut on the strip's "moving once a second" claim.
- **Not every spec §7.3 page has a row yet.** Only Settings/Tokens/Providers (W4) and Database
  (W7) are named with a phase in the side menu; Models, Runs, Routing, Queue, Evidence, Adapters
  and the rest have no row in `roadmap/weightroom-work.md` between W3 and W10 as of this row —
  recorded as a documentation gap, not invented an answer to (`W3_HANDOFF.md` §5).

## [0.2.0] — 2026-09-09

Row W2: Phase 2 of the development plan — process control, unified logs, the Ollama pane and the
audit page. Prepared, not published.

### Added
- **The five `systemd --user` units** (ADR-0125 rule 1). `domain/units.py` holds the template as
  data, renders each file whole and diffs it against what is on disk; a golden per application is
  checked in. The three `Memory*` lines are written for `freeweight` and `loadcoach` only, from
  `[host] memory_high`/`memory_max`; `weightroom.service` carries no cap. Every file names the
  WeightRoomGym version that wrote it, so a version change is a rewrite (spec §19).
- `wr-gym units sync|status|start|stop|restart <app>|all`. `sync` writes only what differs and
  reloads systemd only when something was written, so a second run is a no-op (spec §11
  contract 8); `--diff` prints exactly what a hand edit is losing; `--dry-run` writes nothing.
- **`services/processes.py`**, the `systemctl`/`loginctl` boundary: a `SystemdController` port,
  a subprocess implementation with `which` and the launcher injected, and an in-memory fake.
  Explicit argv, an allowlisted environment (gold standard G12), a timeout and an output cap;
  never a shell, never `sudo`.
- **The wizard's linger and units steps** (ADR-0125 rules 2 and 6). `wr-gym setup` enables
  lingering *before* it writes a unit and refuses to continue with the command to run by hand,
  then writes the five units and enables and starts `weightroom.service`;
  `--no-start-console` leaves it written for a foreground `wr-gym serve`.
- `GET /apps`, `/apps/{app}`, `/apps/{app}/health` (the application's own body, proxied verbatim
  with `source`), and `POST /apps/{app}/start|stop|restart` returning `202` with the audit id and
  the new unit state. The pages carry one form-post control route with the verb as a `Literal`.
- **Version negotiation per application** (spec §19): `GET /api/v1/version` on first contact,
  cached for five minutes and re-probed immediately after a control action; a version outside
  `>=1.0,<2.0` is `APP_VERSION_MISMATCH` and degrades that application by name.
- **`services/journal.py`**: history as `journalctl -o json --reverse`, newest first, capped at
  5 000 rows and paged with systemd's own cursor, with `--since`/`--until`, a level filter and a
  literal (escaped) text search; and a live follow as SSE per application and across every unit
  at once, over MirrorWall's bounded subscription, with a *dropped N lines* frame when a client
  falls behind and a ceiling of sixteen concurrent streams.
- `wr-gym apps status` (the four and Ollama in one table) and `wr-gym logs <app> [--follow]`.
- **The Ollama pane** (ADR-0125 rules 4–5): `GET /ollama` renders `MEMORY_SAFETY.md` §2.1 as
  seven findings over `systemctl show ollama.service`, `GET /ollama/ps` reads residency through
  **ModelRack's** client, and `POST /ollama/restart` restarts the system unit when polkit permits
  it or answers `OLLAMA_RESTART_NOT_PERMITTED` with the rule text, its path and the install
  command. The fix for a failing checklist is `docs/scripts/apply_memory_safety.sh`, **printed**;
  `sudo` is never invoked, asserted by a test over the source tree.
- The audit page gained filters (application, action, since, page size) over the same query the
  API takes.
- `/health` and `/system/status` now report the units and each application for real; a stopped
  application never drops the roll-up.

### Changed
- `GET /apps/*` codes map to HTTP as: `APP_UNKNOWN` 404; `APP_NOT_INSTALLED`, `APP_STOPPED` and
  `APP_VERSION_MISMATCH` 409 (the host is in a state the operator can fix); `APP_UNREACHABLE`
  and `UNIT_ACTION_FAILED` 502 (something the console drives answered badly); `UNIT_UNSUPPORTED`
  501 (this host cannot, and no retry helps); `OLLAMA_RESTART_NOT_PERMITTED` 403.
- The audit vocabulary gained `unit.sync` and `ollama.restart` (`domain/audit.py`, data model §2).

### Fixed
- A partial `[apps.<name>]` table discarded its siblings' defaults, so naming only `executable`
  left `base_url` empty and a running application was reported unreachable. Configuration
  standards §1 requires per-leaf overriding; `AppsSettings` now fills the port back in.
- `host_identity()` ran `ip -json address` with this process's whole environment; it now gets the
  same allowlist as every other child (gold standard G12).

### Decided
- **The polkit-grant probe is the recorded outcome of the last attempt** (ADR-0125 rule 5 left
  the mechanism to this row). The rule file's presence cannot be read — `/etc/polkit-1/rules.d`
  is `0750 root:polkitd` — and polkit cannot be asked: `pkcheck` refuses to evaluate an action
  with details for an untrusted caller, and the rule keys on exactly those details, while
  `systemctl --dry-run restart` exits `0` whether permitted or not. The newest `ollama.restart`
  audit row is therefore the probe, and the attempt passes `--no-ask-password` — without it the
  call blocks on the desktop's interactive polkit agent.
- **`journalctl -u ollama` is readable on the reference machine** (the operator is in `adm`).
  Where it is not, the pane says *journal not readable* by name with journalctl's own message,
  and the rest of the pane works.

## [0.1.0] — 2026-09-09

Published to PyPI on 2026-09-09 by `release.yml` from tag **`v0.1.1`** — the tag `v0.1.0` had
been placed on `9b17d0b`, before the workflow existed, and could not be moved (packaging
standards §6: a release is never re-tagged), so the next tag name was used with the package
still at `0.1.0`. The GitHub release `v0.1.1` therefore carries `wr_gym-0.1.0` artifacts. The
next release is `0.2.0` (row W2) and its tag `v0.2.0`; the name `v0.1.1` is spent.

Row W1: Phase 1 of the development plan — skeleton, configuration, database, TLS, login, `setup`.

### Added
- The standard application layout (`web` → `cli` → `services` → `domain`), with
  `.importlinter` asserting the layering, web/CLI independence, domain purity, and ADR-0123
  rules 3–4 (no application, no `toolyard`/`cutctx`/`commissioner`).
- `config.py`: spec §12 in full with the `defaults → file → env → CLI` precedence at any depth
  (`[apps.<name>]`), `wr-gym config show|validate|init|path|reference|schema` (the schema verb
  is ADR-0127 applied to WeightRoomGym itself), the security-key set (every key under `[server]`,
  `[tls]`, `[auth]`, `[apps.*]`, `[host]`), the six runtime-changeable keys, and the startup
  refusals `INSECURE_BINDING` (ADR-0126 rule 6) and `TLS_MISSING`, exit 3.
- WeightsDB wiring and Alembic `0001`: `operators`, `sessions`, `audit_log`, `settings`,
  `known_revisions` (seeded: FreeWeight `0009`, LoadCoach `0015`, IdeaPress `0010`,
  PromptCadence `0011`); `wr-gym db upgrade|status|backup|restore`.
- The certificate authority (ADR-0126 rule 2): ECDSA P-256, root 10 years with `pathlen:0`,
  leaf 398 days with the host's names and addresses as SANs, renewed at startup under 30 days or
  on an address change; `wr-gym tls init|renew|rotate|show` and `wr-gym trust`; `serve` over
  HTTPS only, plus the plain-HTTP trust listener on `server.trust_port` serving exactly
  `/root.crt` and `/trust` (rule 3).
- One operator account with `hashlib.scrypt` (`n=2**15, r=8, p=1`, parameters stored),
  server-side sessions behind `__Host-weightroom_session` (`HttpOnly`, `Secure`,
  `SameSite=Strict`), 12 h idle / 7 d absolute, a fresh id on every login, 5 login attempts a
  minute per address; `POST /login|logout` (forms) and `POST /api/v1/login|logout|reauth`
  (JSON); `wr-gym operator create|password` (the latter revokes every session). Loopback with no
  account stays open (rule 6).
- CSRF on every form (MirrorWall's double-submit token) and, for cookie authentication, the
  same-origin check on every JSON write: `application/json` + `Sec-Fetch-Site: same-origin`
  (or `none`) + a matching `Origin` (rule 5). The Host allowlist runs before everything.
- The audit trail: a closed action vocabulary, redaction of secret-shaped keys and URL
  credentials before a row exists, `GET /api/v1/audit[/{id}]`, the `/audit` page,
  `wr-gym audit list|show`, and the test that enumerates every state-changing route and asserts
  one row each.
- `wr-gym setup`: the CA, the account, `allowed_hosts` from the host's names and addresses, the
  bind choice, and a token for each installed application stored by file reference under
  `<config>/secrets/` (rule 8); the config file edited in place with comments kept. Units and
  linger are printed as Phase 2 work.
- `GET /api/v1/health` (database, TLS days to expiry, units `not_configured`, each application
  `unknown`), `GET /api/v1/version` (never authenticated), `GET /api/v1/system/status`, a
  placeholder shell behind the login, the console's `/trust` page.
- `requirements/ci.lock` cut on Python 3.13; CI in the full sibling shape (`--require-hashes`,
  `db-matrix`, `coverage`, `contracts`, `security`, `docs`, `build`, `install-check`).
- `docs/configuration.md`, generated from the settings model and diff-checked.
- `.github/workflows/release.yml` in the sibling shape: a `v*.*.*` tag builds from
  `requirements/release.lock`, tests the built wheel, publishes through Trusted Publishing and
  creates the GitHub release; a manual `workflow_dispatch` publishes to TestPyPI (the first
  release's dry run, packaging standards §6).

### Changed
- `__about__` to `0.1.0`.

## [0.0.0] — 2026-09-09

### Added
- Row W0 (2026-09-09): the repository. `OpenWeight-Gym`, formerly the suite's documentation
  repository, becomes the WeightRoomGym repository; the documentation tree moves under `docs/` and
  stays the suite's canonical copy. The package is empty at `0.0.0`; ADRs 0123–0128 and
  `docs/apps/weightroom/` specify what rows W1–W10 build.
