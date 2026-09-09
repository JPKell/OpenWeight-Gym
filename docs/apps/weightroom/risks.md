# WeightRoomGym — Risk and Failure Analysis

Suite-wide risks: [Risk Register](../../architecture/risk-register.md). WeightRoomGym adds a class
the register did not have — a component whose *purpose* is to cross the boundaries the register
defends — and this document is where that class is priced.

---

## 1. Technical risks

| # | Risk | L | I | Mitigation | Early signal |
|---|---|---|---|---|---|
| T1 | **Schema drift** — an application migrates and WeightRoomGym's direct reads return wrong columns or crash | High | Medium | Every direct read is keyed to `known_revisions`; an unknown `alembic_version` degrades that application's database pages by name ([ADR-0123](../../adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 3); fixture databases at each known revision in the test suite | `SCHEMA_UNKNOWN` on a fresh application release |
| T2 | **A guarded write corrupts an application** — the statement was right, the assumption behind it was not | Low | High | Condition 1 (stopped), 2 (backup on disk first), the never-writable list, DML only, one statement; restore is a curated verb ([ADR-0124](../../adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)) | An application failing its own migration or integrity check after a guarded write |
| T3 | **A unit-file regeneration removes an operator's hand edit** | Medium | Low | The file says it is generated; `units sync` reports diffs before writing; overrides go in WeightRoomGym's configuration ([ADR-0125](../../adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md) rule 1) | A sync diff the operator did not expect |
| T4 | **The console dies with the login session** | Low | Medium | Linger enabled by the wizard, refused to proceed without it | `weightroom.service` inactive after logout |
| T5 | **Config edit race** — the file changed under the form | Medium | Medium | `base_mtime` on every write; `CONFIG_CHANGED_ON_DISK`; `.bak` beside every write ([ADR-0127](../../adr/0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md) rule 3) | The refusal appearing in the audit log |
| T6 | **The jobs worker and the alert evaluator share one thread and one stalls the other** | Medium | Low | Separate threads, both leased; a job's subprocess has a timeout; the recovery pass at startup requeues expired leases | A job `running` past its lease |
| T7 | **Mermaid or ECharts blow the page budget** | Medium | Low | Loaded only on pages that contain a diagram or chart; the budget names them as exceptions (spec §15) | A docs page without a diagram loading mermaid |
| T8 | **Thinking never collapses** — a provider streams no delimiter | Medium | Low | Collapse on the first text delta or on `done`; the block is shown open until then, and a provider with no thinking channel shows none | A reply with an empty thinking block |
| T9 | **FTS5 absent from the SQLite build** | Low | Medium | Probed at startup; search degrades to a LIKE scan with a *degraded* label rather than failing | `docs_index` health `degraded` |

## 2. Integration risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| I1 | An application's API version outside WeightRoomGym's range | Medium | Medium | `GET /version` on first contact and every five minutes; `APP_VERSION_MISMATCH` names both; database-sourced pages still render at a known revision |
| I2 | An application stopped while a page needs its API | High | Low | Every page has a database-sourced fallback or a *stopped* state with a start button (spec §7.3) |
| I3 | The schema verbs (`config schema`, `config validate --file`) not yet in an installed application | High at first | Medium | `APP_NOT_INSTALLED`-class degradation naming the verb and the application version that has it; rows WS1–WS4 land before W4 |
| I4 | PromptCadence's `approve` scope not granted to the wizard's token | Low | Medium | The wizard creates `write,approve`; chat renders a pending approval with *no approve scope* when the token lacks it |
| I5 | Ollama moved off `0.0.0.0` by the operator, breaking a LAN client | Low | Low | Doctor's notice says which clients would break; `LAN_ACCESS.md` says when to keep it |
| I6 | LoadCoach's stream has no `thinking` chunk class for a provider | Medium | Low | Same as T8 |

## 3. Security risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| S1 | **A stolen session is the machine** | Low | High | HTTPS only; `__Host-` cookie, `HttpOnly`, `Secure`, `SameSite=Strict`; 12 h idle / 7 d absolute; re-authentication for security keys and guarded writes; `tls rotate` revokes every session ([ADR-0126](../../adr/0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)) |
| S2 | **Password guessing** | Medium | High | scrypt; 5 attempts/min/address; constant-time compare; failures logged with the address, never the password |
| S3 | **CSRF against a cookie-authenticated JSON API** | Medium | High | ADR-0026's JSON exemption withdrawn: `application/json` + `Sec-Fetch-Site` same-origin + matching `Origin`; CORS off; the double-submit token on every form |
| S4 | **DNS rebinding** | Low | High | The Host allowlist before routing ([ADR-0026 §1](../../adr/0026-local-http-hardening.md)); the wizard fills `allowed_hosts` |
| S5 | **The trust listener becomes an unauthenticated surface** | Low | Medium | Two routes, no cookie, no other path (404), tested |
| S6 | **A private CA on client devices is trusted for more than this host** | Low | Medium | `pathlen:0`, name constraints where the client honours them, the fingerprint printed for verification, `tls rotate` documented for a lost device |
| S7 | **Subprocess injection through a model name, a table name, a path** | Low | High | Explicit argv, never a shell; identifiers validated; containment on every path; the SQL console's statement is parsed for kind before it runs |
| S8 | **Model output reaching the DOM** | Low | Medium | Sanitising markdown (no raw HTML), autoescape, no `| safe`; the injection corpus PromptCadence ships is reused against chat rendering |
| S9 | **Secrets in the audit log** | Medium | Medium | Redaction before the row is written; a test feeds a token through every audited action and greps the table |
| S10 | **WeightRoomGym's own settings page moves its own bind** | Low | High | Its `[server]`, `[tls]`, `[auth]` keys are security keys: re-authenticated, audited, and the change takes effect only on restart with the ADR-0126 rule 6 refusal still standing |

## 4. Portability risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| P1 | No systemd | Low | Medium | Process pages degrade by name; the rest works ([ADR-0125](../../adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md) rule 7) |
| P2 | No `ollama` binary (llama.cpp-only host) | Medium | Low | Pull is disabled with the reason; drop-in still works |
| P3 | PostgreSQL applications | Low | Medium | `pg_dump` through `weightsdb`; `default_transaction_read_only`; the db-matrix CI job |

## 5. Performance risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| F1 | Four journals streamed at once saturate the SSE helper | Medium | Low | MirrorWall's bounded subscriber queues; a per-stream line cap with a *dropped N lines* frame |
| F2 | A `SELECT` over a huge table in the console | Medium | Low | 30 s timeout, 10 000-row cap, read-only connection |
| F3 | Telemetry history growing without bound | Low | Low | Downsampling and `history_hours` |

## 6. Model and provider risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| M1 | Chat becomes an ungoverned egress path | Low | High | No provider client, asserted by import-linter; every generation is a LoadCoach job or a PromptCadence trajectory with its own decision record |
| M2 | An `ollama pull` fills the disk | Medium | Medium | Free space checked before the pull; the job reports the size as it streams |

## 7. Maintenance risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| N1 | Four application surfaces to keep current | High | Medium | Recorded API fixtures per application version; the schema-driven settings form has nothing to keep; the control pages are templated over the API, not copied from the applications |
| N2 | The never-writable list drifting from the applications' tables | Medium | Medium | A test compares the list against each fixture database's table set and fails on an unknown name |

## 8. Deliberate trade-offs

* **Above the layer rules, by list.** The exception is enumerated and audited rather than
  avoided; the alternative was four admin APIs and no view of a stopped application.
* **Slow guarded writes.** Stop, back up, dry-run, type, audit — friction is the design.
* **One operator, one password.** Roles and tokens are a later record; the session table admits them.
* **Generated unit files.** Regenerable beats editable; overrides live in configuration.
* **A private CA.** One trust step per device beats a public name the operator does not have.
* **No outbound alerts.** A banner nobody is watching is still better than a webhook that leaks.

## 9. Explicit non-goals (restated as risk control)

Not a provider client (M1); not root (S7's ceiling); not multi-user (S1's assumption); not on the
internet (S1, S6); no in-browser docs editing (the repository stays the store); no execution of
anything a model wrote.

## 10. Premature optimizations to avoid

A caching layer over the applications' APIs; a second telemetry sampler; a background indexer
for every application's database; a plugin system for control surfaces; a message bus between
the worker threads.

## 11. Architectural traps

* **"Just import the model class."** Every one of the four `Settings` classes is one import away
  and forbidden ([ADR-0123](../../adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md)
  rule 3). The schema document exists so nobody has to.
* **"Just write the row."** A `settings` row, a `jobs` row, an `api_tokens` row — each has an
  owner with an audited path, and the never-writable list is where that temptation goes to be
  refused by name.
* **"It's on loopback, skip the login."** The console on loopback is open like the applications;
  the moment `server.host` moves, rule 6 of ADR-0126 refuses without every part in place.
* **"Proxy the app's page."** It carries the application's cookies and auth model onto the LAN;
  the surfaces are re-implemented for exactly this reason.
