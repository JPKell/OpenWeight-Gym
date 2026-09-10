# W1 Handoff — WeightRoomGym Phase 1: skeleton, configuration, database, TLS, login, `setup`

**Row:** W1 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Fable 5.1 · attended).
**Date:** 2026-09-09. **Kickoff:** [`w1-weightroom-p1-skeleton-tls-login.prompt.md`](../prompts/w1-weightroom-p1-skeleton-tls-login.prompt.md).
**Ships:** `wr-gym 0.1.0`, **published to PyPI on 2026-09-09** (from tag `v0.1.1`; see §7 item 2). `wr-gym setup &&
wr-gym serve` gives an HTTPS console with a login and the audit trail; nothing behind the login
yet but a shell that says so.
**Interpreter:** Python 3.14.4 (`WeightRoom/.venv`) for the gate; the locks were cut on
`/usr/bin/python3.13` (3.13) with pip-tools 7.6.1.

## 1. What was built, by commit (one per gate)

| Commit | Gate | What |
|---|---|---|
| `cf7104d` | A | The layout; `.importlinter` completed (layers un-parenthesised, `web-cli-independence` and `domain-purity` restored); `config.py` (spec §12, precedence at any depth, `config show\|validate\|init\|path\|reference\|schema`, the security-key set, `InsecureBindingError`, `TlsMissingError`); WeightsDB wiring; Alembic `0001` with `known_revisions` seeded; `docs/configuration.md`; the schema-document golden |
| `a6de3c8` | B | `domain/tls.py`, `services/tls.py`, `tls init\|renew\|rotate\|show`, `wr-gym trust`; `services/runtime.prepare` (the bind refusals); uvicorn HTTPS; the trust listener; the console's middleware stack |
| `f69cadc` | C | `domain/auth.py`, `services/auth.py`, the session cookie, `POST /login\|logout` (forms) and `/api/v1/login\|logout\|reauth` (JSON), the login brake, `operator create\|password`, `domain/audit.py`, `services/audit.py`, `GET /audit`, `audit list\|show`, the route-enumerating audit test, Security Standards §14 item by item |
| `432f469` | D | `wr-gym setup`, `GET /health\|/system/status`, the placeholder shell, `ci.lock`/`release.lock` on 3.13, CI in the full shape, `CHANGELOG`, `0.1.0` |

Gate on **Python 3.14.4**: `ruff format --check .` (85 files), `ruff check .` clean,
`mypy src tests` clean (80 files, strict), `lint-imports` 5 contracts kept, `pytest -m "not live
and not performance"` **127 passed, 1 skipped** (the PostgreSQL migration test, no server here),
coverage **93 %** overall, `domain/` 98–100 %, `pytest -m contract` 1 passed,
`wr-gym config reference --check` matches, `pip-audit --require-hashes` clean on both locks.

## 2. The seeded revisions (`known_revisions`, migration `0001`)

Read from `<repo>/src/<app>/infrastructure/db/migrations/versions/` on 2026-09-09:

| Application | Head | File |
|---|---|---|
| FreeWeight | `0009` | `0009_models_can_be_disabled.py` |
| LoadCoach | `0015` | `0015_models_can_be_disabled.py` |
| IdeaPress | `0010` | `0010_tool_call_records.py` |
| PromptCadence | `0011` | `0011_content_scrubbed_at.py` |

Each row carries `weightroom_version = "0.1.0"` and `notes = "head on 2026-09-09 (row W1)"`. A
later release that learns a newer revision adds rows in its own migration; W7's revision check
compares against this table.

## 3. Decisions taken in this row

1. **Zero-configuration loopback start issues a CA.** HTTPS is the only protocol the console
   speaks, so `wr-gym serve` on a loopback bind with no `tls/` directory runs `tls init` itself
   (the W0 gold standard "zero-config loopback start" would otherwise be impossible). Off
   loopback an absent directory is `INSECURE_BINDING` naming `wr-gym setup`, as rule 6 says. A
   directory that is *present but incomplete or inconsistent* is `TLS_MISSING` on every bind —
   the code spec §13 lists and ADR-0126 never assigns; refusing rather than guessing is the
   honest use of it.
2. **The two I/O refusals live in `services/runtime.prepare`, not `config.py`.** ADR-0126 rule 6
   has four members; `allowed_hosts` and `allow_lan_exposure` need only the settings and raise
   in `load_settings`; a complete `tls/` directory and an operator row need the filesystem and
   the database and raise in `prepare`, which `serve` and both ASGI factories call. `serve` uses
   uvicorn's dotted-string factories so `weightroom.cli` never imports `weightroom.web`
   (LoadCoach's precedent); `prepare` runs once in `serve` before either socket, and again
   cheaply in each factory.
3. **Two listeners, one process.** The trust listener is a second uvicorn `Server` on a daemon
   thread (`weightroom.bootstrap:create_trust_app_from_environment`), stopped when the console
   exits. It is a Starlette app with exactly two routes, `RequestIdMiddleware` and the same Host
   allowlist as the console, a JSON `NOT_FOUND` envelope for every other path and method, and
   no `Set-Cookie` anywhere (asserted). Its page is a self-contained template with inline CSS —
   MirrorWall's static mount would have been a third route.
4. **`Sec-Fetch-Site` absent is refused** on a JSON write (rule 5 read literally: `same-origin`
   or `none`). Every browser that carries the cookie sends the header; a script without the
   cookie cannot be CSRF'd and is told to use a session anyway (api.md §11). The `Origin` check
   applies to every unsafe method, JSON or form.
5. **The login brake counts attempts, not failures** (rule 4 says "login attempts"): a sixth
   `POST /login` or `/api/v1/login` in a minute from one address is `429` whatever it presents.
   `POST /reauth` shares the brake. The general `/api/v1` bucket (`rate_limit_per_minute`,
   `rate_limit_burst`) is per address; `/api/v1/version` is exempt.
6. **A failed login is an audit row** (`login`, outcome `refused`, the username and address,
   never the password) as well as a warning log line. Contract 2 says login is audited; an
   attempt is what the trail should show, and the brake bounds the volume.
7. **`POST /reauth` stamps the session** (`sessions.reauth_at`, data model §2) rather than
   minting a separate token; the JSON body says the window. W4 checks the stamp with
   `services.auth.require_fresh_reauth`, which already exists. The open loopback install has no
   password and gets `401` from `/reauth`; `require_fresh_reauth` exempts it.
8. **Session touch is throttled to once a minute** so a page of islands does not write a row per
   request; idle expiry is measured from the last touch, which is what the tests assert
   (11 h + 11 h 59 min live, then +12 h 01 min dead).
9. **Expired sessions are swept on login** (data model §3 says every minute; the worker that
   would do it arrives at W9). `resolve_session` deletes an expired row on sight too.
10. **The password floor is 8 characters** — a sanity check, not a policy (ADR-0126 sets none).
    scrypt's working set at `n=2**15, r=8` is exactly OpenSSL's default 32 MiB cap, which raises
    `memory limit exceeded`; `hashlib.scrypt` is called with `maxmem = 2 × 128 × n × r × p`, so
    a hostile stored `kdf_params` still cannot ask for the machine.
11. **One `AppSettings` model for all four applications**, `api_key_file` included; spec §12
    shows `[apps.ideapress]` without one, and IdeaPress's stays `""`. The wizard issues tokens
    for `loadcoach` (`write`) and `promptcadence` (`write,approve`) exactly as rule 8 lists;
    FreeWeight has tokens too but the rule does not name it — W4's token pages can add it.
12. **Addresses come from `ip -json address`** (explicit argv), global scope only, loopback,
    link-local and multicast excluded; the fallback is `getaddrinfo(hostname)`. The Docker bridge
    `172.17.0.1` is global-scope and therefore in the SANs and `allowed_hosts` — harmless, and
    a phone never reaches it. The host name is lowercased (`Jordan-main` → `jordan-main`; mDNS is
    case-insensitive).
13. **`allowed_hosts` on a non-loopback bind also admits the loopback names**, because the
    console is reached on the machine that runs it (`curl https://localhost:8769`).
14. **`GET /health`** names `units` as `not_configured` and each `app:<name>` as `unknown` (the
    spec's own vocabulary, not MirrorWall's enum), and neither affects the roll-up: database
    and TLS decide it. `GET /system/status` answers `null`, never `0`, for every figure a later
    phase fills.
15. **`cryptography` is `>=50,<51`.** The skeleton's `>=43,<46` resolved 45.0.7, which
    `pip-audit` flags eleven times (PYSEC-2026-3552 is fixed only in 50.0.0). A range change
    needs no ADR (packaging standards §4). Nothing else in the suite depends on `cryptography`.
16. **The audit-route test is a registry, not a list.** `tests/security/test_audit_routes.py`
    enumerates `POST|PUT|PATCH|DELETE` routes (descending into FastAPI ≥ 0.140's
    `_IncludedRouter` wrappers, prefix included) and fails on any route without an entry in
    `EXERCISES`; each entry must add exactly one row. Later rows add a line per route.
17. **`config show` prints dotted leaves at any depth** (`apps.loadcoach.base_url`) and the
    database overlay; `config schema --json` is the ADR-0127 document with `apps.*` keys; the
    golden excludes `version`, `config_path` and `sources` (WS1's finding).
18. **The tolerant loader strips unknown keys recursively** (`server.bogus`,
    `apps.loadcoach.nope`, `mystery`) and reports each; WeightRoomGym has no `extra="allow"`
    section, so WS2's special case is not needed here.

## 4. What the kickoff got wrong, or did not know

1. **The venv's editable install was still `openweight-gym 0.0.0`** from before the W0 rename;
   `pip` warned on every install. Reinstalled as `wr-gym 0.1.0`.
2. **The reference machine has no application on `PATH`** — each lives in its own venv — so
   `wr-gym setup` issues no token unless `[apps.<app>] executable` names the venv binary. The
   demonstration below ran with none; the token path is proven by the fake executables in
   `tests/integration/test_setup.py`. The operator's real `setup` should set the four
   `executable` keys first (or W2's wizard step can resolve them from the units).
3. **`modelrack 0.8.0` is on PyPI** (the lock resolved it), so the W0 handoff's "CI red until
   modelrack publishes" no longer applies to this repository.
4. **FastAPI 0.141 wraps included routers** (`_IncludedRouter`, un-prefixed inner paths) — a
   naive `app.routes` walk finds nothing; `tests/support.api_routes` handles it.
5. **mDNS on the host itself resolves `jordan-main.local` to a link-local IPv6** (`fe80::…`),
   which the console bound to `10.77.10.84` does not listen on; a phone's resolver returns the
   IPv4. From the host, use the IP or `curl --resolve`. `LAN_ACCESS.md` §3's "check it worked"
   command may want the `--resolve` note at W10.
6. **The kickoff's "middleware order … → session"** is honoured with the session as a route
   dependency, which by construction runs after every middleware; a session middleware would
   have had to know which routes are open (`/version`, `/login`, the trust page).
7. Coverage is reported by the local run; CI's `coverage` job uses `--cov-fail-under=85` and
   diff-cover 90 %, both of which this tree passes locally.

## 5. Demonstration (Phase 1 acceptance criteria)

Run on the reference machine (`Jordan-main`, LAN `10.77.10.84`) in a scratch XDG root, bound
to the LAN interface on the real ports, verified from the machine itself. **The phone step was
not performed by this session** — no device was available to it; the operator runs it with the
steps at the end.

```text
$ wr-gym setup --username jordan --password-stdin --bind lan --lan-address 10.77.10.84
host jordan-main  addresses 10.77.10.84, 172.17.0.1
tls        created <config>/wr-gym/tls
           root sha256 EE:20:C1:1A:75:62:8F:18:19:87:7E:2F:AD:25:68:83:5C:BC:47:D7:8F:0C:D4:E4:D5:00:7C:C2:B0:54:9F:B6
account    created operator 'jordan'
bind       10.77.10.84 (one LAN interface)
hosts      jordan-main, jordan-main.local, 10.77.10.84, 172.17.0.1
token      loadcoach: not installed; no token
token      promptcadence: not installed; no token
later      units: `wr-gym units sync` and the systemd --user units arrive at W2
later      linger: `loginctl enable-linger` is printed by the W2 wizard step

$ curl http://10.77.10.84:8769/                                  → curl (52) Empty reply: no plain HTTP
$ curl --cacert ca.crt https://10.77.10.84:8769/api/v1/version    → {"application":"weightroom","version":"0.1.0","api_version":"v1","schema_version":"1"}
$ curl --cacert ca.crt --resolve jordan-main.local:8769:10.77.10.84 https://jordan-main.local:8769/api/v1/version → 200, ssl_verify=0
$ curl --cacert ca.crt https://10.77.10.84:8769/api/v1/health     → 401
$ curl http://10.77.10.84:8770/root.crt   → 200 application/x-x509-ca-cert, byte-identical to ca.crt
$ curl http://10.77.10.84:8770/trust      → 200, no Set-Cookie;   /login → 404
$ POST /login (form, CSRF token, cookie jar) → 303 → /, __Host-weightroom_session set; GET / → 200
$ GET /api/v1/health (cookie) → ok [database ok, tls ok, units not_configured, app:* unknown]
$ GET /api/v1/audit (cookie)  → [login ok jordan, setup.run ok]
$ openssl s_client -connect 10.77.10.84:8769 -servername jordan-main.local -CAfile ca.crt
  subject=CN=jordan-main  issuer=CN=WeightRoomGym CA jordan-main  TLSv1.3  Verify return code: 0 (ok)
```

`wr-gym tls show` beside the leaf's SANs, for the operator to compare with the phone's
certificate details:

```text
root             CN=WeightRoomGym CA jordan-main
root sha256      EE:20:C1:1A:75:62:8F:18:19:87:7E:2F:AD:25:68:83:5C:BC:47:D7:8F:0C:D4:E4:D5:00:7C:C2:B0:54:9F:B6
root expires     2036-09-09
leaf             CN=jordan-main
leaf sha256      A4:42:52:BB:3A:68:1B:B2:5F:54:C2:EE:70:1D:6C:A2:8B:76:97:18:83:09:C5:1A:10:30:20:B1:05:D1:3F:3B
leaf valid       2026-09-10 to 2027-10-13 (397 days left)
leaf names       10.77.10.84, 127.0.0.1, 172.17.0.1, ::1, jordan-main, jordan-main.local, localhost
SAN (openssl)    DNS:jordan-main, DNS:jordan-main.local, DNS:localhost, IP:10.77.10.84, IP:172.17.0.1, IP:127.0.0.1, IP:::1
```

(The scratch CA above was discarded; the operator's real `setup` mints its own — compare
*that* `wr-gym tls show` with the phone.)

**The phone step, for the operator** (LAN_ACCESS.md §3; `wr-gym trust` prints the same):

1. On the host, in the real roots: `wr-gym setup` (answer the prompts; choose the LAN
   interface), then `wr-gym serve`. `wr-gym trust` prints the root's fingerprint.
2. On the phone: open `http://jordan-main.local:8770/trust` (or `http://10.77.10.84:8770/trust`),
   compare the fingerprint with `wr-gym trust`'s, download `root.crt`, install it — Android:
   *Settings → Security & privacy → … → Install a certificate → **CA certificate***; iOS: the
   profile, then *Certificate Trust Settings → Enable Full Trust*.
3. Open `https://jordan-main.local:8769`: padlock, the login page; log in; the shell. Put the
   phone's certificate details (issuer `WeightRoomGym CA jordan-main`, the SHA-256) beside
   `wr-gym tls show` here.

## 6. Decided by the operator (interview, 2026-09-09, after the row closed)

| Question | Decision |
|---|---|
| Real bind | **One LAN interface** (`server.host = 10.77.10.84`) |
| Release `0.1.0` | **Tag + publish after the phone step** — device verified first, then `v0.1.0`, push, PyPI approval |
| `Sec-Fetch-Site` absent on a JSON write | **Keep strict** (refused; §3 item 4 stands) |
| Failed logins | **Keep as audit rows** (`login`/`refused`; §3 item 6 stands) |
| `cryptography >=50,<51` | **Accepted** |
| Application tokens | **Executables written now, `setup` rerun at W2** — `~/.config/wr-gym/config.toml` created from the example with the four `[apps.<app>] executable` paths (each repo's `.venv/bin/<app>`); W2's wizard step issues the tokens with the units |
| `172.17.0.1` in the SANs | **Keep** (no filtering of virtual interfaces) |
| Next | **Publish `mirrorwall 0.3.0` first, then W2** |

## 7. Open for the operator

1. Run the phone step (§5) on a real device and append the result to this handoff; **verified
   on: (none yet)**.
2. ~~Then tag `v0.1.0`, push, approve the PyPI environment (§6).~~ **Done 2026-09-09, before
   the phone step**, with a wrinkle: `v0.1.0` was placed on `9b17d0b`, which predates
   `release.yml` (added in `96abe6b` after the row closed), so it released nothing; `v0.1.1`
   was placed on `96abe6b` and released the package **as `0.1.0`** (`__about__` was never
   bumped). PyPI has `wr-gym 0.1.0`; the GitHub release is named `v0.1.1`; the TestPyPI dry
   run ran first. Verified from a clean 3.13 venv: `pip install wr-gym==0.1.0`,
   `wr-gym --version` → `wr-gym 0.1.0 (api v1)`, no application or agent package pulled in.
   Next tag is `v0.2.0` at W2; never reuse `v0.1.1`.
3. Tag, push and publish `mirrorwall 0.3.0` (row WM) before starting W2 (§6).
4. `MEMORY_SAFETY.md` §2.1 and Ollama's `0.0.0.0` bind are still as the W0 handoff found them;
   nothing in W1 touched the host.

## 8. What runs next

W2 (Opus 5 · high): process control, unified logs, the audit page's growth. It inherits the
route registry in `tests/security/test_audit_routes.py` (add a line per `POST /apps/{app}/…`),
the `units` health component (`not_configured` → real), `SetupReport.deferred` (the wizard's
units and linger steps), and `services.setup.installed_executable` for resolving each
application's CLI. W3 needs `mirrorwall 0.3` (row WM, prepared) — `pyproject.toml` admits
`>=0.2.2,<0.4` and the venv holds 0.2.2; the shell's `htmx` opt-in is the W3 change.
