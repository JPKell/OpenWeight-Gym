# Operations

Running WeightRoomGym day to day: the units, the logs, backups and restore — the console's own
and each application's — the jobs and their schedules, retention, and the certificate. The
wizard and the trust step are [`setup.md`](setup.md); what each error means is
[`troubleshooting.md`](troubleshooting.md).

## 1. Processes

The five `systemd --user` units — `weightroom`, `freeweight`, `loadcoach`, `ideapress`,
`promptcadence` — are written whole by `wr-gym units sync` from `config.toml`
([ADR-0125](adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)):
the header names the `wr-gym` version that wrote them, and a hand edit is overwritten at the next
sync. `freeweight.service` and `loadcoach.service` carry the memory cap lines of
[`MEMORY_SAFETY.md`](MEMORY_SAFETY.md) §2.2; `ollama.service` is a system unit the console reads
(`systemctl show`) and restarts only where a polkit rule permits it.

```bash
wr-gym units status                  # each unit's state, uptime, restarts
wr-gym units start loadcoach         # or stop | restart; `all` for every one
wr-gym apps status                   # the four applications and Ollama in one table
systemctl --user start weightroom    # the console itself, from outside it
```

The same controls are on each application's Overview page, and every one writes an audit row.
No unit is enabled at boot (the operator's decision, 2026-09-10).

**After a code change to an application's checkout**, restart its unit: a unit runs its
repository's editable install and imports lazily, so a running process can be serving old
code over a migrated database.

## 2. Logs

Every unit logs to the user journal; `ollama.service` to the system journal. The console reads
both with `journalctl` and never keeps a copy.

```bash
wr-gym logs loadcoach -n 200                 # the newest lines
wr-gym logs all -f --level warning           # follow, unified across the five
wr-gym logs weightroom --grep 01M27025YMM8   # a request id from an error envelope
```

The Logs page streams the same lines live (SSE, one region per unit or unified), backfills on a
reconnect, and says when lines were dropped under a slow client rather than showing a silent
hole. The console's own log carries `request_id`, `operator`, `app`, `unit`, `action` and
`audit_id`; secrets are redacted by key name.

## 3. Backups and restore

### 3.1 WeightRoomGym's own database

```bash
wr-gym db status                            # revision, row counts, size, integrity
wr-gym db backup                            # ~/.local/share/wr-gym/backups/<stamp>.sqlite3
wr-gym db upgrade                           # to head, with its own pre-migration backup
```

The Backups page runs the same three verbs in process. `[storage] backup_retention` (5) rotates
the automatic ones; a file you name is never rotated. The database is SQLite by default;
PostgreSQL is supported (`storage.database_url`), and then backups are `pg_dump` archives.

**Restore, two ways.** From a terminal with the console stopped:

```bash
systemctl --user stop weightroom
wr-gym db restore ~/.local/share/wr-gym/backups/<file>.sqlite3 --confirm
systemctl --user start weightroom
```

Or from the console itself, when it runs as `weightroom.service`: the Backups page offers
*restore* on each of the console's own backups. That queues a `self_restore` job — typed and
re-authenticated — which hands itself to a transient unit that stops the console, takes a
`pre-restore` backup, restores the file, migrates it to head, carries the job and its audit row
into the restored database and starts the console again; if the restore fails after the stop, the
pre-restore backup goes back and the console is started regardless
([ADR-0136](adr/0136-weightroom-restores-its-own-database-through-a-job-handed-to-a-transient-unit.md)).
A restore returns the database to a point in time, the audit trail included; what was written
after the backup is in the pre-restore copy, not merged.

### 3.2 The four applications

Each application's database page (and the Backups page for all four at once) runs that
application's **own** `db status`, `db backup`, `db upgrade` and `db restore` — never a copy of
them ([ADR-0123](adr/0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 3).
The backup lands in the application's own `backups/` directory; `restore` requires the unit
stopped, the file chosen from that directory, the application's name typed, and the password
again. A `backup` job (`wr-gym jobs run backup --param apps='["freeweight","loadcoach"]'`)
does the same for several at once and is one of the seeded schedules.

### 3.3 Guarded-write undo copies

A raw write into an application's database ([ADR-0124](adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md))
takes a backup first, under `~/.local/share/wr-gym/backups/<app>/<stamp>-guarded-write.sqlite3`
— WeightRoomGym's own directory, not the application's. They are listed on the application's
database page and at `GET /api/v1/apps/<app>/db/backups`, kept `[storage] guarded_backup_days`
(90; `0` for never) and removed by the `retention_trim` job. To undo a write, stop the
application and restore the copy with its own `db restore`.

## 4. Jobs and schedules

The console runs one worker thread for its own job queue
([ADR-0010](adr/0010-queue-implementation.md), [ADR-0029](adr/0029-queue-mechanics.md) shape:
a lease, a keeper, a recovery pass). Kinds: `freeweight_suite_run` (a benchmark run under the
host memory cap, in a named scope `wr-gym-fwrun-<job>.scope`), `backup`, `model_refresh`,
`retention_trim`, `docs_index`, `catalog_pull` and `self_restore`.

```bash
wr-gym jobs list                                      # newest first
wr-gym jobs run docs_index --wait                     # queue for the serving console; follow it
wr-gym jobs run freeweight_suite_run \
  --param model=ollama/qwen3:8b --param suite=native.performance
wr-gym jobs cancel <id>                               # a queued job stops at once; a running one is asked
wr-gym jobs schedule                                  # the five seeded schedules, disabled until you enable one
wr-gym jobs schedule <id> --cron "0 2 * * *" --enable # five-field cron, UTC
```

A slot missed while the console was down runs once when it returns, never once per missed slot.
A job's page shows its captured output live and its `job.run` audit row; a job the console lost
mid-run is requeued when its kind is idempotent and failed as `worker_lost` when it is not
(a run, a self-restore). A successful `catalog_pull` queues a `model_refresh` so the model
reaches the catalog.

## 5. Retention

| What | Where | Rule |
|---|---|---|
| Finished jobs | `jobs` | 90 days, `retention_trim` |
| Guarded-write undo copies | `backups/<app>/` | `[storage] guarded_backup_days` |
| Own automatic backups | `backups/` | `[storage] backup_retention` newest kept |
| Telemetry samples | `telemetry_samples` | `[telemetry] history_hours` (72), downsampled |
| Alerts | `alerts`, `alert_history` | Kept for ever |
| The audit trail | `audit_log` | Kept for ever, append-only |
| FreeWeight's results | FreeWeight's database | Only when `retention_trim`'s `freeweight_older_than_days` is set, through FreeWeight's own API, re-authenticated |

LoadCoach and PromptCadence trim their own content inside their own processes
(`storage.content_retention_hours`); IdeaPress keeps everything.

## 6. Certificates and the operator account

```bash
wr-gym tls show        # subjects, fingerprints, lifetimes, the leaf's names
wr-gym tls renew       # a new leaf under the same root; automatic inside 30 days of expiry
wr-gym tls rotate      # a new root: every device trusts again, every session is revoked
wr-gym trust           # the fingerprint, the paths, the trust URLs and per-OS steps
wr-gym operator password   # reset; revokes every session (ADR-0126 rule 4)
```

A new hostname or LAN address needs `server.allowed_hosts` extended (a security key on the
console's own settings page) and `wr-gym tls renew`, so the leaf names it.

## 7. Watching the machine

* The telemetry strip on every page: CPU, RAM, GPU, VRAM, the primary GPU's temperature, the
  resident models, LoadCoach's queue depth — `—` where a reading is unavailable, never `0`
  ([ADR-0016](adr/0016-unavailable-is-not-zero.md)). Each figure's history page keeps
  `[telemetry] history_hours`.
* `GET /api/v1/system/status` is the machine view in one document; `wr-gym health` the console's
  own components.
* The alert banner on every page, polled every five seconds, and `wr-gym alerts list`.
* `wr-gym doctor`, after any change to the host.

## 8. Upgrading `wr-gym`

```bash
pipx upgrade wr-gym                     # or pip install -U wr-gym in its venv
wr-gym db upgrade                       # automatic at the next start on SQLite
wr-gym units sync                       # the unit header names the version; rewritten on change
systemctl --user restart weightroom
```

A newer application than this console knows (`version.<app>`, `revision.<app>`) degrades that
application's pages by name until `wr-gym` is upgraded; nothing is guessed at. The migration
history is linear and forward-only; a database written by a newer `wr-gym` is refused at startup
with both revisions named, and the pre-migration backup is the way back.
