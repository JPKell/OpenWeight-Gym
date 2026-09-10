# Changelog

All notable changes to WeightRoomGym (distribution `wr-gym`) are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
