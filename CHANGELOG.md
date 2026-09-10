# Changelog

All notable changes to WeightRoomGym (distribution `wr-gym`) are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-09-09 (prepared, unpublished)

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

### Changed
- `__about__` to `0.1.0`.

## [0.0.0] — 2026-09-09

### Added
- Row W0 (2026-09-09): the repository. `OpenWeight-Gym`, formerly the suite's documentation
  repository, becomes the WeightRoomGym repository; the documentation tree moves under `docs/` and
  stays the suite's canonical copy. The package is empty at `0.0.0`; ADRs 0123–0128 and
  `docs/apps/weightroom/` specify what rows W1–W10 build.
