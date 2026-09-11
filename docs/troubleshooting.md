# Troubleshooting

Start with `wr-gym doctor`: every rule this host is held to, worst first, each with its evidence
and — where a root-owned change is the fix — the command to run, printed and never run. The
Doctor page shows the same findings. Every API error is the standard envelope — `code`,
`message`, `details`, `request_id` — and the request id is in the log line that goes with it
(`wr-gym logs weightroom --grep <request_id>`).

## 1. The doctor's rules

`wr-gym doctor` exits 1 on a *failure* or a *warning*; a *notice* and an *unknown* are
information. The rule ids are stable, for a script that greps.

| Rule | Reads | Failure means | What to do |
|---|---|---|---|
| `memory.ollama.<key>` | `systemctl show ollama.service` | A [`MEMORY_SAFETY.md` §2.1](MEMORY_SAFETY.md) line is missing or wrong (`MemoryMax`, `MemoryHigh`, `MemorySwapMax`, `OLLAMA_CONTEXT_LENGTH`, …): a large request can take the host down | Run `docs/scripts/apply_memory_safety.sh` (printed), then restart Ollama |
| `memory.unit.<app>` | The application's unit file | `freeweight.service` or `loadcoach.service` lacks the three `Memory*` lines ([ADR-0119](adr/0119-model-servers-run-under-a-host-memory-cap.md)) | `wr-gym units sync`, then restart the unit |
| `lan.bind.<app>` | The application's `config show` | An application binds off loopback: it would be a second LAN service beside this console ([ADR-0126](adr/0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)) | Set `server.host = "127.0.0.1"` on its settings page (a security key: the password again) |
| `lan.caddy_leftover.<app>` | The application's `config.toml` | A `trusted_proxies`/Caddy block from before WeightRoomGym | Remove it; the console fronts the application now |
| `lan.ollama_host` | `systemctl show ollama.service` | Ollama listens on `0.0.0.0` | The operator's standing exception on the reference machine (2026-09-10); a notice, kept |
| `token.scope.<app>` | `<app> token list --json` | The console's token on LoadCoach or PromptCadence lacks the scope chat needs (`write`; `approve` on PromptCadence) | Mint a new one on the Tokens page and the file under `~/.config/wr-gym/secrets/` is rewritten |
| `promptcadence.loadcoach_token` | PromptCadence's `/api/v1/health` | LoadCoach refuses the token PromptCadence presents (`401`/`403`): nothing PromptCadence runs can reach a model | Re-issue it from PromptCadence's Tokens page, or `loadcoach token create promptcadence --scope write` and point `[loadcoach] api_key_file` at it; *unknown* while PromptCadence is stopped |
| `version.<app>` | `GET /api/v1/version` | The application's version is outside the range this console speaks to; its pages degrade by name | Upgrade the application, or `wr-gym` |
| `revision.<app>` | `alembic_version` in its database | An `alembic_version` this build does not know: the database pages say *not known to this WeightRoomGym* and nothing else ([ADR-0123](adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 3) | Upgrade `wr-gym` (a newer application) or run `<app> db upgrade` (an older database) |
| `tls.expiry` | `~/.config/wr-gym/tls/server.crt` | The leaf is inside 30 days of expiry | `wr-gym tls renew` (automatic at the next start); no device re-trusts |
| `linger` | `loginctl show-user` | The session does not linger: the units stop at logout | `loginctl enable-linger $USER` (printed) |
| `polkit.ollama_restart` | The rule file | The Ollama restart button is not permitted | `sudo install` the rule the finding prints ([`OLLAMA_RESTART_POLKIT.md`](OLLAMA_RESTART_POLKIT.md)); the operator chose not to (2026-09-10), so this stays *unknown* |
| `disk.<app>` | The device under each application's data root | Under 5 GB free | Make room; a backup or a migration may fail |

## 2. Startup

| Symptom | Code | What it means and what to do |
|---|---|---|
| Refuses to start naming a field | `CONFIGURATION_ERROR` | `wr-gym config validate` names the field; [`configuration.md`](configuration.md) is the reference |
| Refuses to start off loopback | `INSECURE_BINDING` (exit 3) | No operator account, or no `server.allowed_hosts`, or `0.0.0.0` without `allow_lan_exposure`. The message names the `wr-gym setup` step |
| Refuses to start off loopback, certificate | `TLS_MISSING` (exit 3) | `~/.config/wr-gym/tls/` is missing or broken: `wr-gym tls init`, or `wr-gym setup` |
| "database is behind head" | — | `wr-gym db upgrade`; automatic on SQLite unless `storage.auto_migrate = false`; the pre-migration backup lands in `~/.local/share/wr-gym/backups/` |
| "database was written by a newer version" | — | Install that version, or `wr-gym db restore` the pre-migration backup and stay |
| The docs tab refuses | `DOCS_ROOT_MISSING` | `[docs] root` is unset and no `docs/` sits beside the checkout — `pipx` installs have none. Point it at a clone of the documentation tree |

## 3. Reaching the console

| Symptom | What it means and what to do |
|---|---|
| `curl http://<host>:8769/` connects to nothing | Correct: the console port serves no plain HTTP. Use `https://`, or the trust port (8770) for the root |
| The browser refuses the certificate | The device does not trust the root yet: `http://<host>:8770/trust` and [`setup.md` §4](setup.md#4-trusting-the-certificate-on-each-device). On iOS the profile must also be *enabled* under Certificate Trust Settings; on Android it goes in the **CA certificate** store |
| `421 MISDIRECTED_REQUEST` | The `Host` you used is not in `server.allowed_hosts` — a new hostname or address needs adding (a security key), and `wr-gym tls renew` so the leaf names it |
| `401 UNAUTHORIZED` on the API | No session cookie, or an expired one (12 h idle, 7 d absolute). `GET /api/v1/version` is the one open route |
| `403 CSRF_FAILED` | A form without MirrorWall's token, or a JSON write without `Sec-Fetch-Site: same-origin` — a script must carry a browser session's cookie and token (spec §21 names an automation token as a future extension) |
| `403 REAUTH_REQUIRED` | A security key or a guarded write outside the 5-minute window: enter the password again (`POST /reauth`) |
| `429 RATE_LIMITED` | The login brake (five per minute per address) or the request limit (`server.rate_limit_per_minute`) |

## 4. The applications

| Symptom | Code | What it means and what to do |
|---|---|---|
| A tab says *not installed* | `APP_NOT_INSTALLED` | No executable was found: set `[apps.<app>] executable` to the application's CLI in its own virtualenv, then `wr-gym units sync` |
| *stopped*, start button | `APP_STOPPED` | The unit is inactive. Start it from the page or `wr-gym units start <app>`. No unit is enabled at boot |
| The start button fails | `UNIT_ACTION_FAILED` | systemd's own message is in the response; `wr-gym logs <app> -n 50` |
| *unsupported on this host* | `UNIT_UNSUPPORTED` | No `systemctl` on `PATH`: the process pages degrade by name; everything else works (spec §16) |
| *running* but *unreachable* | `APP_UNREACHABLE` | The unit is active and `/api/v1/health` did not answer: the application is starting, or binds a port other than `[apps.<app>] base_url` |
| Version badge *too old* / *too new* | `APP_VERSION_MISMATCH` | See `version.<app>` above |
| Database pages degrade by name | `SCHEMA_UNKNOWN` | See `revision.<app>` above; `details` carries `found` and `known` |
| A settings save is refused whole | `CONFIG_CHANGED_ON_DISK` | The file changed after the page loaded (another editor, another session): reload and save again |
| A settings save is refused by the application | `CONFIG_VALIDATION_FAILED` | The application's own `config validate --file` said no, in its own words; nothing was written |
| A runtime key is refused while the application is stopped | `APP_STOPPED` | Start the application, or the *to file* button writes the key to `config.toml` for the next start |
| A key says *next stage* instead of *live* | — | IdeaPress applies a stored runtime value when a stage next starts; *clear* removes the stored row so `config.toml` decides again |

## 5. Guarded writes (the database console)

Every refusal names the condition ([ADR-0124](adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)):

| Code | Condition | What to do |
|---|---|---|
| `GUARD_STATEMENT_REFUSED` | — | Only `INSERT`/`UPDATE`/`DELETE` as a single statement; DDL, `PRAGMA`, `VACUUM` are refused by name; the read console takes only a `SELECT`/`WITH` |
| `GUARD_TABLE_LOCKED` | — | A never-writable table (queue state, event logs, decisions, ledgers, `alembic_version`), or a cascade that would reach one; the response names the path |
| `GUARD_TABLE_MISMATCH` | 4 | Type the tables exactly as the statement names them |
| `GUARD_APP_RUNNING` | 1 | Stop the application first — the unit inactive **and** the port closed; a running process outside the unit still counts |
| `GUARD_DRY_RUN_FAILED` | 3 | The dry run failed or its count changed since the dry run you presented; run it again |
| `GUARD_BACKUP_FAILED` | 2 | The backup could not be taken (disk, permissions); nothing was written |
| `GUARD_AUDIT_FAILED` | 5 | The audit row could not be written; nothing was written |

The undo of a landed write is its backup under `~/.local/share/wr-gym/backups/<app>/` (kept
`[storage] guarded_backup_days`), restored with the application's own `db restore` — see
[`operations.md` §3](operations.md#3-backups-and-restore).

## 6. Chat, catalog, jobs

| Symptom | Code | What it means and what to do |
|---|---|---|
| Sending is disabled | `CHAT_BACKEND_UNAVAILABLE` | LoadCoach or PromptCadence is stopped, or the console has no token for it (`token.scope.<app>`) |
| An attachment is refused | `ATTACHMENT_TOO_LARGE` / `ATTACHMENT_TYPE_REFUSED` | `chat.max_attachment_bytes`; text and markdown only |
| A pull never finishes | `CATALOG_PULL_FAILED` | Ollama's own error is in the job's output; the pull runs as a `catalog_pull` job, cancel it from the Jobs page |
| The GGUF drop-in is refused | `CATALOG_DROPIN_REFUSED` | Not a GGUF (magic bytes), too large, outside the model directory, or no application configures a llama.cpp `model_directory` to drop it into |
| A job stays *queued* | — | The worker runs in the serving console only; `wr-gym jobs run` from a terminal queues for it. A `freeweight_suite_run` needs `systemd-run` on `PATH` and is refused rather than run uncapped |
| A job ended `worker_lost` | — | The console stopped mid-job; an idempotent kind is requeued, a run or a self-restore is failed and reported — run it again |
| The console will not restore itself | — | `self_restore` needs the console running as `weightroom.service` and `systemd-run` on `PATH`; otherwise `wr-gym db restore <file> --confirm` with the console stopped |

## 7. Alerts

| Alert | Source | Clears when |
|---|---|---|
| *application down* | A unit `failed` or restarting itself, or running with `/health` not `200` for a minute; an inactive unit is a choice, not an outage | The condition is gone at the next evaluation |
| *memory cap fired* | A kill line in either journal naming `ollama.service`, an application unit or a `wr-gym-fwrun-<job>.scope` | **Acknowledged** — a kill does not un-happen |
| *GPU hot* | Above `[alerts] gpu_temperature_c` | The reading drops |
| *ceiling reached* | A LoadLedger balance at or over a ceiling | The window rolls |
| *breaker open* | LoadCoach's `/reliability` | LoadCoach closes it |

A source that could not be read (no `journalctl`, an application stopped) clears nothing and
says so on the Alerts page. Nothing is sent anywhere; the history is kept for ever.
