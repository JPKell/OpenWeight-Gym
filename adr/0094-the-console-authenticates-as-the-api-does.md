# ADR-0094 — The console authenticates as the API does, and every form is CSRF-protected

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Spec §14](../apps/promptcadence/spec.md) — the console's authentication
and the CSRF surface; retires `web/app.py`'s "there is no HTML UI yet" deferral.
**Relates to:** [ADR-0026](0026-local-http-hardening.md) (host allowlist, double-submit CSRF,
same-origin — the suite's local-HTTP controls; this record wires the second, and P9's checklist
holds the rest), [ADR-0020](0020-ui-rendering-strategy.md)
(server-rendered HTML with progressive enhancement),
[ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md) (`approve` is its own scope).
**Source:** Row I1, decision D4.

## Context

PromptCadence's authentication today: loopback with no tokens configured is open and holds every
scope; the moment any token exists, or the bind is not loopback, every scoped endpoint requires
`Authorization: Bearer`. A browser sends no bearer header. `web/app.py` says so plainly and
defers the whole question — "there is no HTML UI yet (Phase 8), so CSRF and same-origin protection
are not wired: the state-changing routes take JSON bodies and bearer-less loopback callers only,
and a browser form cannot reach them."

The approvals inbox is a page with two buttons that POST. The moment it exists that paragraph is
false, and the protection it defers is due.

## Decision

**The console uses the same principal resolution as the API, adds no session cookie, and wires
MirrorWall's double-submit CSRF plus same-origin on every state-changing route.**

1. **No new credential.** `resolve_principal` is unchanged and serves the console: an open
   loopback install browses and approves as `loopback`, exactly as `promptcadence approve` does
   from the same machine, and grants are recorded as `approver:loopback`. A deployment that has
   created a token, or that binds off-loopback, gets `401` on the console as it does on the API —
   the page says so and names `promptcadence token create`.
2. **The console is therefore loopback-first, and says so.** This is a deliberate ceiling, not an
   oversight: a browser-usable, non-loopback console needs a session — login, rotation, fixation
   defence, logout, idle expiry — and that is a security surface invented at the end of a long
   phase, which is where security surfaces go wrong. It is specified work, not an accident, and
   the page tells the operator what it would take.
3. **CSRF is wired now, for the whole application.** `mirrorwall.CsrfMiddleware` is added in the
   same commit that renders the first form. Every page carrying a form is rendered with
   `issue_csrf_token`'s value in a hidden field and in the `__Host-mw-csrf` cookie (the LoadCoach
   precedent, `web/csrf.py`). The JSON API is unaffected, on MirrorWall's stated grounds rather
   than by omission: a cross-origin HTML form cannot send `application/json`, so a request that
   arrives as JSON has already passed a CORS preflight, which fails while CORS is disabled. The
   exemption is the `json_exempt` argument, so withdrawing it is one flag rather than a rewrite.
   **Same-origin checking, body caps and rate limits stay Phase 9's**, where the security
   checklist lists them together; this record wires the one control the form creates the need
   for.
4. **Scopes are enforced on the page, not only on the API.** A `read`-scoped principal sees the
   inbox and gets `403` from the grant button's POST; the button is not rendered. `approve`
   remains distinct from `write` (ADR-0049 rule 2) on both surfaces.
5. **`web/app.py`'s docstring is rewritten in the same commit.** A comment that describes a
   protection as deferred, after it has been wired, is worse than no comment: the next reader
   trusts it.

## Alternatives considered

**A session cookie for the console.** What a multi-user deployment eventually needs, and the
honest answer to "the operator should not have to be on the box". Rejected for this row on timing
and scope: it is a new authentication mode with its own threat model, and it would be built
under the deadline of a phase whose other half is a cache-consistency proof. Rule 2 makes the
absence explicit so it is chosen rather than assumed.

**Accept a bearer token from a form field or a query parameter.** Makes the console work
off-loopback with no session machinery. Rejected outright: a credential in a URL is a credential
in the access log, the referrer and the history, and a credential in a form field is one CSRF
away from being replayed.

**Leave the console read-only and keep approvals on the CLI.** Tempting, and it dodges CSRF
entirely. Rejected because the development plan names the approvals inbox, and because an inbox
that lists work but cannot act on it sends the operator to a terminal at the exact moment the
console was supposed to help — and CSRF has to be wired for the settings form regardless.

## Consequences

* One middleware and one `csrf.py`; no new tables, no session store, no logout.
* The console is reachable only where the API is already open. `promptcadence doctor` and the
  console's own header say which mode the install is in.
* The prompt-injection corpus (Phase 9) gains a new surface to attack: model-authored text —
  turn content, tool arguments, plan documents — now reaches a Jinja template. Autoescaping and
  `StrictUndefined` are on by construction from MirrorWall, and no template renders raw HTML from
  a record.
* `_STATUS_BY_CODE` gains nothing: `UNAUTHORIZED`, `FORBIDDEN` and `MISDIRECTED_REQUEST` are
  already mapped.

## Revisit when

A deployment needs the console off-loopback. That is the session-cookie decision, and it should be
its own record with its own threat model rather than an amendment to this one.
