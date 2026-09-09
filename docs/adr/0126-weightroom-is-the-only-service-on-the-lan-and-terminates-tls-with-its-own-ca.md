# ADR-0126 — WeightRoom is the only service on the LAN, and it terminates TLS with its own certificate authority behind a session login

**Status:** Accepted (2026-09-09)
**Amends, for one component:** [ADR-0014](0014-authentication-strategy.md) — its "session cookies
+ a login page" rejection, whose stated reason was that sessions imply accounts and password
storage "for a product whose deployment model is one user, or a few users behind a proxy that
already knows who they are". WeightRoom **is** the proxy that knows who they are. The four
applications keep ADR-0014 unchanged.
**Relates to:** [ADR-0026](0026-local-http-hardening.md) (the Host allowlist and CSRF, both
kept; its JSON-API exemption, which cookie authentication withdraws here),
[ADR-0094](0094-the-console-authenticates-as-the-api-does.md) (PromptCadence's loopback-first
console — the ceiling this record is the other side of), [ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
rule 6 (the applications stay loopback), [Security Standards §2, §3, §8](../standards/security-standards.md),
[Configuration Standards §6](../standards/configuration-standards.md) (secrets by reference),
[`LAN_ACCESS.md`](../LAN_ACCESS.md) (rewritten by this row around this record).
**Source:** the operator interview of 2026-09-09, decision D7, and the [kickoff](../history/w0-weightroom-phase-0.prompt.md)
§6's auth-model, CA and app-token items.

## Context

The suite's exposure story has always been "TLS is a reverse proxy's job"
([ADR-0014](0014-authentication-strategy.md) rule 7). `LAN_ACCESS.md` made that concrete with
Caddy: one local CA, basic auth, four proxied ports, a fifth port serving `root.crt`, and a script
that appended `[server]` blocks to four configuration files. It worked, and it was four logins'
worth of ceremony to reach an IdeaPress that has no login of its own and a PromptCadence whose
console refuses a browser off loopback by decision ([ADR-0094](0094-the-console-authenticates-as-the-api-does.md)).

Two facts fix the shape. Every form in the suite depends on a `__Host-`-prefixed `Secure` cookie,
so anything a browser reaches by a hostname other than `localhost` must be HTTPS or every form
fails ([`LAN_ACCESS.md`](../LAN_ACCESS.md) §1). And the operator's decision is that exactly one
thing faces the network. A console that is the only LAN service, that has to terminate TLS
anyway, and whose one user is a person, is the place a real login belongs — which is precisely
the case ADR-0014 said it was not deciding.

## Decision

**WeightRoom is the only suite service bound to a non-loopback address. It serves HTTPS itself,
under a certificate authority it creates and the operator trusts once per device, and it
authenticates a person with a username, a password and a server-side session. The four
applications stay on loopback with their own posture untouched.**

1. **Only WeightRoom leaves loopback.** `freeweight`, `loadcoach`, `ideapress` and
   `promptcadence` keep `server.host = "127.0.0.1"`; `weightroom doctor` reports any of them
   bound elsewhere as a finding, and reports Ollama's `OLLAMA_HOST=0.0.0.0` (the reference
   machine's current override) as a *notice* — Ollama is the operator's daemon, not the suite's,
   and `LAN_ACCESS.md` recommends `127.0.0.1` unless a LAN client needs it. The Caddy design and
   `expose_on_lan.sh` are retired.

2. **TLS is built in.** `weightroom setup` (or `weightroom tls init`) creates, under
   `$XDG_CONFIG_HOME/weightroom/tls/` (directory `0700`):
   * `ca.key` (`0600`) and `ca.crt` — an ECDSA P-256 root, `CN=WeightRoom CA <hostname>`,
     lifetime **10 years**, `pathlen:0`, key usage certificate signing only;
   * `server.key` (`0600`) and `server.crt` — an ECDSA P-256 leaf signed by the root, lifetime
     **398 days**, SANs: the hostname, `<hostname>.local`, every non-loopback IPv4/IPv6 address
     the host holds at issue time, `localhost`, `127.0.0.1` and `::1`.
   `weightroom serve` renews the leaf at startup when fewer than 30 days remain or the host's
   addresses have changed, and refuses to start when the CA is missing on a non-loopback bind
   (rule 6). `uvicorn` serves HTTPS directly (`ssl_certfile`/`ssl_keyfile`); **plain HTTP on the
   console port is never served**. `cryptography` joins the dependency set for the issuing;
   serving needs only the standard library.

3. **Trusting the CA is a page and a command.** `GET /trust` on the console (session required)
   shows the root's SHA-256 fingerprint, a download of `root.crt`, and the per-OS steps that
   `LAN_ACCESS.md` §3 carried. A second, plain-HTTP listener on `server.trust_port` (default
   **8770**) serves **only** `/root.crt` and the same instructions page — no cookies, no login,
   no other route — because a phone cannot fetch the certificate over a TLS session it does not
   yet trust; the root certificate is public by definition. `weightroom trust` prints the
   fingerprint, the file path, both URLs and the steps, so the operator verifies the fingerprint
   on the device against the one on the server before trusting anything.

4. **One operator account, a password, a session.** `weightroom setup` creates the account:
   username, and a password hashed with the standard library's `hashlib.scrypt` (`n=2**15`,
   `r=8`, `p=1`, a 16-byte random salt, parameters stored beside the hash so they can rise).
   A password is a low-entropy secret and gets the KDF ADR-0014 said a password would need. Login
   issues a server-side session row (`sessions`: id, operator, created, last seen, expires,
   address) and the cookie `__Host-weightroom_session` — `HttpOnly`, `Secure`, `SameSite=Strict`,
   `Path=/`; **12 hours idle, 7 days absolute**; logout deletes the row; `weightroom operator
   password` resets the password from a shell and revokes every session. Login attempts are
   limited to **5 per minute per address**, the comparison is constant-time, and a failed attempt
   is logged with the address and the request ID, never the password.

5. **CSRF and same-origin, tightened for cookie authentication.** Every HTML form carries
   MirrorWall's double-submit token (ADR-0026 §2). The JSON routes the page's islands call are
   **not** exempt here, because ADR-0026's exemption argued from bearer tokens a browser cannot
   attach; a cookie it can. Every state-changing JSON route therefore requires
   `Content-Type: application/json`, a `Sec-Fetch-Site` of `same-origin` (or `none`), and an
   `Origin` — when present — that matches the console's own; CORS stays off. The Host allowlist
   runs before all of it: `server.allowed_hosts` names the hostname, `<hostname>.local` and the
   LAN addresses, exactly as ADR-0026 §1 requires of any non-loopback bind.

6. **The bind refusal, translated.** A non-loopback `server.host` requires, together: `tls/`
   present and valid, an operator account, and `server.allowed_hosts`; `0.0.0.0` additionally
   needs `server.allow_lan_exposure = true`. Missing any → `INSECURE_BINDING`, exit 3, the
   suite's rule ([Security Standards §2](../standards/security-standards.md)) with *a token*
   replaced by *an account*. A loopback bind with no account is open, as every application is on
   loopback (ADR-0014 rule 1), and the Host check still runs.

7. **No bearer tokens and no roles in 1.0.** Scripts talk to the four applications directly;
   WeightRoom's API exists for its own pages. A second operator, an API token for automation, or
   a read-only viewer each want a record of their own, and the session table is shaped so that
   adding a principal is a column, not a redesign.

8. **Application tokens are created anyway, and kept by reference.** While the four applications
   bind loopback, WeightRoom needs no credential to call them. The wizard nevertheless runs
   `loadcoach token create weightroom --scope write` and `promptcadence token create weightroom
   --scope write,approve` (approval is its own scope, [ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md);
   chat approves egress inline), writes each secret to `$XDG_CONFIG_HOME/weightroom/secrets/<app>.token`
   (`0600`) and records `[apps.<app>] api_key_file` in WeightRoom's configuration — never the
   value ([Configuration Standards §6](../standards/configuration-standards.md)). Chat keeps
   working the day an application is moved off loopback, and WeightRoom is the only holder of
   those secrets, which is one place to revoke.

9. **Rotation.** `weightroom tls renew` reissues the leaf under the same root (no re-trust);
   `weightroom tls rotate` replaces the root and the leaf, revokes every session, and prints the
   re-trust steps — the action for a device the operator no longer controls.

10. **Not the internet.** No router port is opened, the CA is not publicly trusted, and nothing
    here is a design for exposure beyond the LAN. Internet exposure wants a public name, a public
    CA and a stronger authenticator than one password; that is a different record.

## Consequences

*Positive.* One certificate to trust per device, one login, one port — and the four
applications' own security pages stay true word for word, because nothing about them changed.
IdeaPress finally has a login in front of it, and PromptCadence's console ceiling
([ADR-0094](0094-the-console-authenticates-as-the-api-does.md)) is answered by the component that
was always going to answer it.

*Negative.* WeightRoom carries a password store, a session store, a certificate authority and a
rate limiter — the whole subsystem ADR-0014 declined for the applications. It is built once, in
the component whose job it is, and tested under Security Standards §14 plus the rows this record
adds (session fixation, idle and absolute expiry, logout, the `Sec-Fetch-Site` check, the
trust-port's refusal of every other route).

*Negative.* A self-signed root on every device is a trust the operator grants by hand, once per
device, and revokes by hand (`tls rotate`). The alternative — a public CA — needs a public
name and is out of scope by rule 10.

*Neutral.* The `expose_on_lan.sh` units, if any exist, are superseded by
[ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)'s;
`[server]` blocks that script appended to the four configuration files are harmless and `doctor`
notes a non-loopback `allowed_hosts` on a loopback bind as informational.

## Alternatives considered

* **Keep Caddy and put WeightRoom behind it too.** Rejected: a second CA, a second login
  (basic auth) in front of the real one, and a `sudo`-owned Caddyfile that WeightRoom cannot
  manage without root. The one thing on the LAN should own its own edge.
* **Bearer tokens for the console, as the four applications do.** Rejected: a browser cannot
  attach one to a navigation, and LoadCoach's answer (a token pasted into a cookie) is a session
  with a worse name. A person logs in with a password; that is what sessions are for.
* **A public CA (Let's Encrypt) with a DNS name.** Rejected for 1.0 by rule 10; the CA
  abstraction is one module so that a later record can swap the issuer.
* **`SameSite=Lax` to allow a bookmark from another site to land logged in.** Rejected: `Strict`
  costs one extra click on a cross-site link and closes a class of CSRF the double-submit token
  would otherwise be the only defence against.
* **Argon2id for the password.** The better KDF, and a dependency. Rejected for 1.0 in favour of
  `hashlib.scrypt`, which is in the standard library, memory-hard, and adequate for one operator
  whose attacker needs the database first; the parameters are stored so a later change is a
  re-hash on next login, not a migration.

## Revisit when

* **A second person** needs their own login. Rule 7 becomes accounts, roles and per-person audit
  attribution.
* **The console must be reachable from outside the LAN.** Rule 10; a public name, a public CA
  and a second factor.
* **An application gains a browser-usable off-loopback console of its own.** The "only WeightRoom
  leaves loopback" rule and that application's ADR-0094-class decision would then contradict, and
  one of them has to give.
