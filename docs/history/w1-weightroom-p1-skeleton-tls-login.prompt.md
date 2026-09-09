# Kickoff — W1: WeightRoom Phase 1 — skeleton, configuration, database, TLS, login, `setup`

**Row:** W1 (Opus 5 · xhigh · **never overnight**) — row 2 of
[`docs/roadmap/weightroom-work.md`](../roadmap/weightroom-work.md). Runs after W0.
**Ships:** `weightroom 0.1.0` prepared (not published): `weightroom serve` on HTTPS with a
login, `weightroom setup` minus the units step, the audit log, the full CI shape with
`requirements/ci.lock`.
**Component:** `~/ai/suite/WeightRoom` (`.venv`, Python 3.14 locally; CI 3.12/3.13). The docs
tree is `docs/` in the same repository — there is no mirror to update for `apps/weightroom/*`.

## Standing preamble

[`docs/roadmap/outstanding-work.md` §2](../roadmap/outstanding-work.md) applies in full, plus
[`weightroom-work.md` §2](../roadmap/weightroom-work.md). `git status --short` at start and end;
commit at each gate; never push, tag or publish; never `git add -A`.

**Read, all of it, before the first edit:** [`apps/weightroom/spec.md`](../apps/weightroom/spec.md)
§§1–6, §12, §13, §14; [`development-plan.md`](../apps/weightroom/development-plan.md) Phase 1;
[`data-model.md`](../apps/weightroom/data-model.md) §2 (`operators`, `sessions`, `audit_log`,
`settings`, `known_revisions`); [`api.md`](../apps/weightroom/api.md) §1, §9; ADR-0126 in full;
ADR-0026; ADR-0014; ADR-0123 rules 3–4; `standards/security-standards.md` §2, §3, §8, §14;
`standards/configuration-standards.md`; `standards/packaging-and-release-standards.md` §4–5;
`history/W0_HANDOFF.md` (what the skeleton deferred and why). Precedents: LoadCoach's
`config.py`, `services/settings.py`, `bootstrap.py`, `web/app.py` and its `tests/security/`.

## Decisions already taken — do not reopen

* One operator account, scrypt from `hashlib`, a server-side session, the `__Host-` cookie, 12 h
  idle / 7 d absolute, 5 logins per minute per address (ADR-0126 rules 4–7).
* ECDSA P-256; CA 10 years, leaf 398 days, renew under 30 days; SANs as rule 2; **no plain HTTP on
  8769**; the trust listener on 8770 serves exactly two routes (rule 3).
* The JSON API is **not** CSRF-exempt here: `application/json` + `Sec-Fetch-Site` same-origin
  + matching `Origin` (rule 5). MirrorWall's double-submit token on every form.
* Non-loopback bind needs TLS + an account + `allowed_hosts` (+ `allow_lan_exposure` for
  `0.0.0.0`) → `INSECURE_BINDING` exit 3 (rule 6). Loopback with no account is open.
* Application tokens are created by the wizard **only for installed applications** and stored by
  file reference (rule 8).
* The dependency set is spec §5's twelve names; a thirteenth needs an ADR first.

## Gates

**Gate A — layout, config, database.** The layout of master architecture §4; `.importlinter`
completed (un-parenthesise the layers; restore `web-cli-independence` and `domain-purity` as the
W0 comments describe); `config.py` with spec §12, precedence, `config show|validate|init|path|
reference|schema` (the schema verb is ADR-0127 rule 1 applied to WeightRoom itself), the
security-key set, `InsecureBindingError`; WeightsDB wiring; Alembic `0001`; `known_revisions`
seeded with each application's current head (read them from the four repositories'
`migrations/versions/`; record the values in the handoff). Commit.

**Gate B — TLS.** `domain/tls.py` (pure: what to issue, when to renew — no I/O) and
`services/tls.py` (the `cryptography` calls, the files, the modes); `tls init|renew|rotate|show`;
`weightroom trust`; uvicorn with `ssl_certfile`/`ssl_keyfile`; the trust listener as a second,
tiny Starlette app on `server.trust_port`. Verify the leaf with `openssl verify -CAfile`. Commit.

**Gate C — login, sessions, CSRF, audit.** `domain/auth.py` (hashing, expiry decisions),
`services/auth.py`, the middleware order (Host allowlist → CSRF/same-origin → session), `POST
/login|logout|reauth`, `operator create|password`, the rate limit, the audit service with the
closed action vocabulary from `data-model.md` §2, `GET /audit`. The test that enumerates every
state-changing route and asserts one audit row each — write it now, while there are three routes,
so every later row inherits it. Commit.

**Gate D — `setup`, health, shell, CI.** `weightroom setup` (TLS, account, `allowed_hosts` from
the host's names and addresses, the bind choice, the tokens by reference; print that units come at
W2); `GET /health|version|system/status` (applications `unknown`); a placeholder shell page behind
the login; `requirements/ci.lock` cut on 3.13 and CI switched to `--require-hashes` with the
`db-matrix`, `contracts`, `build` and `install-check` jobs added in the sibling shape;
`CHANGELOG.md`; `__about__` to `0.1.0`. Commit.

## Demonstrate (the plan's Phase 1 acceptance criteria)

On the reference machine, from a phone on the LAN: trust the root from `http://<host>:8770/trust`,
open `https://<host>.local:8769`, see the padlock and the login, log in, see the shell.
`curl http://<host>:8769/` connects to nothing; `/api/v1/version` answers without a cookie;
`/api/v1/health` is `401`. Put the phone's certificate details and `weightroom tls show` side by
side in the handoff.

## Finish line

The gate green (`ruff format --check .`, `ruff check .`, `mypy src tests`, `lint-imports`,
`pytest -m "not live and not performance"`), coverage ≥ 85 % (95 % on `domain/`), `pip-audit` on
both locks clean, CI workflow present in the full shape, `CHANGELOG.md` updated, one commit per
gate, `docs/history/W1_HANDOFF.md` written (decisions, what the kickoff got wrong, the seeded
revisions, the device the trust steps were verified on), the W1 row marked done in
`roadmap/weightroom-work.md`. Name the interpreter.
