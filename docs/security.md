# Security

WeightRoomGym is the one service in the suite that leaves loopback, so it carries the suite's
whole LAN surface: the certificate authority, the login, the audit trail, and the guard that
stands between a browser and four applications' databases. This page is that surface end to end,
in the order a request meets it. The decisions are
[ADR-0126](adr/0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)
(the LAN shape), [ADR-0124](adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)
(the write guard) and [ADR-0123](adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
(what the console may reach); the tests are `tests/security/`, and `test_checklist.py` there
names every row below by the test that holds it.

## 1. Transport

* **HTTPS only.** The console port (8769) speaks TLS 1.2+ and nothing else; there is no plain
  HTTP to redirect from. The certificate is issued by the console's own root
  (`~/.config/wr-gym/tls/`, ECDSA P-256; root ten years, leaf 398 days, renewed inside 30 days
  of expiry without any device re-trusting). `wr-gym tls rotate` replaces the root, and every
  session with it.
* **The trust listener** on the trust port (8770) is plain HTTP by necessity — a device has to
  fetch the root before it can trust anything — and serves exactly `/root.crt` and `/trust`.
  Every other path is `404` with no cookie; it never sets one. Compare the fingerprint it shows
  with `wr-gym trust` on the host before installing the root anywhere.
* **`Host` is checked before anything else.** A request whose `Host` is not in
  `server.allowed_hosts` (or loopback, on a loopback bind) is `421 MISDIRECTED_REQUEST` before
  authentication, on both listeners — the DNS-rebinding defence of
  [ADR-0026](adr/0026-local-http-hardening.md).
* **Off loopback, startup refuses** without the certificate (`TLS_MISSING`), without an
  operator account or `allowed_hosts` (`INSECURE_BINDING`). `0.0.0.0` additionally needs
  `server.allow_lan_exposure = true`.

## 2. Login and sessions

* **One operator account**, scrypt (`n = 2¹⁵, r = 8, p = 1`, parameters stored with the
  hash), compared in constant time; the row holds the hash, never the password. `wr-gym operator
  password` resets it and revokes every session.
* **Server-side sessions**, a `__Host-` cookie (`Secure`, `HttpOnly`, `SameSite=Strict`, no
  `Domain`), a **new id on every login** (no fixation), **12 h idle** and **7 d absolute** expiry
  (`[auth]`), and logout deletes the row. A missing, malformed or revoked cookie is `401` on the
  API and a redirect to `/login` on a page.
* **The login brake**: five attempts per minute per address, whatever is presented, then
  `429 RATE_LIMITED`. A failed login logs the address, never the password.
* **Re-authentication.** Security keys (every application's `server`/`tls`/`auth`/`apps`/`host`
  keys and the console's own) and guarded writes need the password again inside
  `auth.reauth_window_minutes` (5). The window is session state — nothing is carried on the
  write. Every such action's audit row says *security*.
* **Loopback with no account is open**, and the login page says so: the operating-system user
  boundary is the boundary there, as it is for the four applications.

## 3. Forms and JSON writes

* Every HTML form carries MirrorWall's double-submit CSRF token; a forged post is
  `403 CSRF_FAILED`.
* Every JSON write requires `Sec-Fetch-Site: same-origin` (or `none`, a typed URL) and, when
  present, an `Origin` matching the console; a cross-site post is `403`. `GET /api/v1/version`
  answers without a credential; nothing else under `/api/v1` does.
* Request bodies are capped (`server.max_body_bytes`, 64 MiB for the GGUF drop-in by upload)
  and refused with `413` before they are read. Uploads are accepted on exactly four routes — the
  chat attachments (text and markdown, `chat.max_attachment_bytes`, stored under the data root
  under a generated name, never interpreted) and the GGUF drop-in (magic bytes, size and
  containment checked before the copy).

## 4. The audit trail

Every state-changing route — every `POST`, `PUT` and `DELETE`, the login and logout included —
writes exactly one `audit_log` row: who, when, which application, which action, the target, the
parameters, the outcome, and for a guarded write the backup path, the dry-run count and the
actual count. `tests/security/test_audit_routes.py` enumerates the routes and fails on one that
writes no row; `test_redaction_sweep.py` runs them all through a console holding the operator's
password and a LoadCoach token and asserts neither reaches a row or a log line. Redaction is by
key name at any depth (`token`, `key`, `secret`, `password`, `authorization`, `cookie`) and by
URL credential; the trail is append-only and `wr-gym audit list` reads it from a terminal.

## 5. Reaching the applications

* **Subprocesses are argv lists, never a shell**, over an allowlisted environment (`PATH`, `HOME`,
  `USER`, `LOGNAME`, the session bus, `LC_ALL=C`, `PYTHONUNBUFFERED=1`) that carries no
  credential; output is capped; the executables are resolved once and recorded.
  `tests/security/test_subprocess_discipline.py` greps the source for a shell and for `sudo`:
  **`sudo` is never invoked** — every root-owned change (the polkit rule, the Ollama cap lines)
  is printed as a command.
* **SQL from the console runs read-only** on a connection opened read-only, with a 30 s
  statement timeout and a 10 000-row cap; anything but a single `SELECT`/`WITH` is
  `GUARD_STATEMENT_REFUSED` by name. The connection string is the application's own, read from
  its `config show`, and rendered with its credential redacted.
* **A raw write passes all five conditions or nothing happens** (ADR-0124): the application
  stopped (unit inactive **and** the port closed, observed not asserted); a backup taken first;
  a dry run whose row count matches the write's, bound to the write by id; the tables typed
  exactly as the statement names them; the audit row written, pending then completed. The
  never-writable tables — queue state, event logs, decision records, ledgers, `alembic_version`
  and the engine catalog — are refused by name, and a cascade that would reach one is refused
  with the path. Every condition has a test that fails it alone.
* **Tokens by reference.** The application tokens the wizard mints live as `0600` files under
  `~/.config/wr-gym/secrets/`; `config.toml` names the file. The tokens pages show a token's
  name and scopes, never its value.

## 6. Model output is data

Chat renders through a sanitising markdown pipeline — no raw HTML, no `| safe`; thinking,
plans, tool cards and egress cards are rendered escaped; nothing in a reply is executed,
fetched or used to build a path or a URL. PromptCadence's injection corpus runs against both
backends' rendering (`tests/security/test_chat_isolation.py`), and the same test proves a reply
contacts LoadCoach's and PromptCadence's base URLs and no other host: WeightRoomGym has no
provider path at all (`.importlinter` forbids `modelrack.generate`'s callers and every agent
package).

## 7. The docs viewer and the prompt editor

The viewer serves only paths under `[docs] root` after resolution; a symlink pointing out of the
root is refused (`DOCS_PAGE_OUTSIDE_ROOT`). Markdown is rendered by a sanitising renderer;
mermaid loads only on a page whose markdown has a fence. The prompt editor writes validated
records — validated by the owning application's own loader — under that application's own config
root and nowhere else.

## 8. What to watch

* `wr-gym doctor`: `tls.expiry`, `lan.bind.<app>` (an application off loopback), `lan.ollama_host`
  (Ollama on `0.0.0.0`, the operator's standing exception), `token.scope.<app>`.
* The audit trail's `security` rows, and `settings.write` rows with `touched_security`.
* Security Standards §14 is held item by item in `tests/security/test_checklist.py`; a row that
  does not apply to this component says why beside it.
