# W2 Handoff — WeightRoomGym Phase 2: process control, unified logs, the Ollama pane, the audit page

**Row:** W2 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Opus 5 · high; reviewed same day).
**Date:** 2026-09-09. **Kickoff:** [`w2-weightroom-p2-processes-logs-audit.prompt.md`](../prompts/w2-weightroom-p2-processes-logs-audit.prompt.md).
**Ships:** `wr-gym 0.2.0`, **prepared, not tagged, not pushed, not published.** The five
`systemd --user` units are written and driven from the console, the journal is live per
application and unified, the Ollama pane renders `MEMORY_SAFETY.md` §2.1 line by line, and the
audit page filters.
**Interpreter:** Python 3.14.4 (`WeightRoom/.venv`) for the gate.

## 1. What was built, by commit (one per gate)

| Commit | Gate | What |
|---|---|---|
| `1693e17` | A | `domain/units.py` (the template as data, rendering, the diff, goldens per application); `services/processes.py` (the `SystemdController` port, the subprocess implementation, the fake, `run_command`); `wr-gym units sync\|status\|start\|stop\|restart`; the wizard's linger and units steps; the `sudo`/argv/environment tests |
| `170556d` | B | `domain/apps.py` (the version ranges); `services/apps.py` (the inventory, the five-minute cache, the health proxy); `services/journal.py` (history with cursor paging, follow as a bounded subscription); `web/routes/apps.py` and the `/apps`, `/apps/{app}`, `/logs` pages with the live pane; `wr-gym apps status`, `wr-gym logs`; `/health` and `/system/status` completed |
| `b852bdc` | C | `domain/ollama.py` (the §2.1 checklist with both fixtures); `services/ollama.py` (the unit read, residency through ModelRack, the polkit gate); `web/routes/ollama.py` and the pane; the audit page's filters; `CHANGELOG`; `0.2.0` |

Gate on **Python 3.14.4**: `ruff format --check .` (104 files), `ruff check .` clean,
`mypy src tests` clean (99 files, strict), `lint-imports` 5 contracts kept,
`pytest -m "not live and not performance"` **562 passed, 1 skipped** (the PostgreSQL migration
test, no server here), coverage **91 %** overall — `domain/units.py` and `domain/apps.py` 100 %,
`domain/ollama.py` 96 %, `services/journal.py` 95 %, `services/apps.py` 90 %,
`services/processes.py` 89 %, `services/ollama.py` 89 % — and
`wr-gym config reference --check` matches.

## 2. What this row was asked to decide, and what it decided

### 2.1 The probe for the polkit grant (ADR-0125 rule 5)

**Decision: the recorded outcome of the last attempt, and the record is the audit trail.** The
newest `ollama.restart` row says `ok` (permitted), `refused` (not permitted), or is absent
(*not yet known*, and the pane says exactly that). No new storage; the trail an operator already
reads is the state.

The two mechanisms the ADR suggested were both tested on the reference machine and **neither
works**:

| Probe | Result on `Jordan-main` |
|---|---|
| The rule file's presence | `/etc/polkit-1/rules.d` is `0750 root:polkitd`. The operator is in neither, so `os.path.exists(<rule>)` is `False` and `os.stat` raises `EACCES` **whether or not the rule is installed**. A presence check would report *absent* forever. |
| Ask polkit directly | `pkcheck --action-id org.freedesktop.systemd1.manage-units --detail unit ollama.service --detail verb restart` → `GDBus.Error:org.freedesktop.PolicyKit1.Error.NotAuthorized: Only trusted callers (e.g. uid 0 or an action owner) can use CheckAuthorization() and pass details`. Without details it answers `polkit.result=auth_admin_keep` — the *default* for the bare action — whether or not a rule granting this unit and verb exists, because the rule keys on the details that may not be passed. |
| `systemctl --dry-run restart` | Exits `0`. A dry run authorises nothing, so it is `0` in both worlds. |

**`--no-ask-password` is not optional, and that was measured.** A plain
`systemctl restart ollama.service` on this host **hung for the full 20 s timeout** — a desktop
polkit agent is running and systemctl waited for a password prompt nobody was looking at. With
the flag it fails in milliseconds with the exact text the console now matches on:

```text
Failed to restart ollama.service: Access denied as the requested operation requires interactive
authentication. However, interactive authentication has not been enabled by the calling program.
```

A refusal is audited as `refused` and answered with the rule to install; anything else is
`failed` and answered with systemd's own message. Conflating them would send an operator to
write a polkit rule for a daemon that had crashed.

### 2.2 The journal group for `ollama.service`

**`journalctl -u ollama` is readable by the operator on this machine.** `id` shows `jpk` in
`adm` (and `ollama`), which is what grants it; the live pane reports `journal_readable=true`.

Where it is not, the pane says **journal not readable** by name, quotes journalctl's own message
(*"No journal files were opened due to insufficient permissions."*), names the two groups that
grant it (`systemd-journal`, `adm`), and every other line of the pane still works. The probe is
one `journalctl -n 1` against the unit, so it costs a process and answers the real question
rather than guessing from group membership.

## 3. Other decisions taken in this row

1. **The unit template is data, not a format string.** The one thing that varies between
   applications is *which lines exist*; a conditional inside a format string is how a generated
   file grows a second shape. Goldens for all five are checked in at
   `tests/fixtures/units/`.
2. **`ExecStart` arguments are quoted when systemd needs it.** A venv under a path with a space
   is ordinary on a desktop.
3. **`sync` compares bytes and reloads only when something was written**, so the second run is a
   no-op (spec §11 contract 8). `--diff` shows the operator exactly what a hand edit loses.
4. **Lingering is enabled before the first unit is written**, not after. Discovering that a
   session does not linger *after* writing five units leaves a console that dies at logout.
5. **`weightroom.service` is enabled and started by the wizard** (rule 6), with
   `--no-start-console` for a scratch install or a foreground `wr-gym serve`.
6. **The version range is a major range, not a pin** (`>=1.0,<2.0` for all four). A console that
   had to be re-released for each of four applications' patch releases is a console nobody
   upgrades.
7. **A stopped application is never probed and carries no `error`.** The pill already says
   *stopped*; a red sentence beside a state the operator chose is noise.
8. **The pages carry one form-post control route** with the verb as a `Literal`, not three paths
   differing by a word. A browser form cannot send anything but `GET` and `POST`, and one route
   is one entry in the audit-route registry.
9. **One `journalctl -f` per connected stream**, not a shared reader with a broker. The producer
   is a pipe from a process systemd already runs and an operator console has one operator; the
   shared design costs a subscriber count, a start/stop race and a lifetime that outlives every
   request. The ceiling is explicit: `MAX_CONCURRENT_FOLLOWS = 16`, refused by name past that.
10. **The drop counter is checked on every pass of the frame loop**, not only when the queue
    drains — a producer fast enough to keep the queue full is exactly the one that drops lines.
11. **History paging uses systemd's own cursor**, and `--cursor` is **inclusive**: a resumed page
    asks for one extra row and drops the duplicate. Measured, not assumed.
12. **Free-text search is escaped before it reaches `--grep`**, so an operator searching for
    `a[0]` finds `a[0]` rather than writing a character class.
13. **HTTP status mapping** (new codes): `APP_UNKNOWN` 404; `APP_NOT_INSTALLED`, `APP_STOPPED`,
    `APP_VERSION_MISMATCH` 409 (the host is in a state the operator can fix); `APP_UNREACHABLE`,
    `UNIT_ACTION_FAILED` 502 (something the console drives answered badly); `UNIT_UNSUPPORTED`
    501 (this host cannot, and no retry helps); `OLLAMA_RESTART_NOT_PERMITTED` 403.
14. **A stopped application never drops `/health`'s roll-up.** A console whose own health goes
    red because the operator deliberately stopped something is a console nobody reads.
15. **The audit vocabulary gained `unit.sync` and `ollama.restart`** (`domain/audit.py`; data
    model §2's list ends in an ellipsis, and each phase brings its own writers).
16. **`sudo` may be printed and never executed**, and the test says so in those terms: no runtime
    string outside `services/tls.py` and `services/ollama.py` may contain it, no string anywhere
    may *be* it, and those two modules' occurrences are instruction sentences. A blunt
    four-letter grep would have banned the sentence that tells the operator what to run.

## 4. What the kickoff got wrong, or did not know

1. **The failing Ollama fixture is no longer the reference machine.** The kickoff says the
   machine's "current override — `OLLAMA_CONTEXT_LENGTH=112000`, no cap — is the failing
   fixture". The operator had already run `docs/scripts/apply_memory_safety.sh` before this row
   ran: `/etc/systemd/system/ollama.service.d/override.conf` sets `8192`,
   `OLLAMA_MAX_LOADED_MODELS=1`, `MemoryHigh=22G`, `MemoryMax=24G`, `MemorySwapMax=0`,
   `ManagedOOMMemoryPressure=kill` and a 50 % limit. So the **live pane is green, 7/7**, and the
   red half of Phase 2 criterion 3 is demonstrated against the fixture
   `tests/fixtures/ollama/unsafe-112000-no-cap.txt`, written as the kickoff asked. Both halves
   are proven; only the red one is not live. Reported as such, per the arc's §2.
2. **All four applications were already running by hand** from a shared venv,
   `/home/jpk/ai/suite/.venv-suite/bin/*` (~5.8 h uptime), so every application port was taken
   and the first `unit.start` died with `[Errno 98] address already in use` and
   `Restart=on-failure` put it in a restart loop. ADR-0125's *"Neutral: `launch.sh` keeps
   working"* does not mention that a hand-started process and its unit collide on the port. The
   operator chose to stop the four and leave the suite under its units;
   **§6 records the state the machine was left in.** `wr-gym doctor` (W4) should detect
   "port held by a process that is not this unit's `MainPID`" and say so.
3. **The two installs disagree.** The operator's `[apps.*] executable` keys point at the
   per-repo venvs (LoadCoach `1.3.1`, FreeWeight `1.2.1`, IdeaPress `1.4.1`, PromptCadence
   `1.3.3`), while the processes that had been running came from `.venv-suite` (LoadCoach
   `1.3.0`). The operator chose the per-repo venvs, which is what the units now run. Worth a
   `doctor` check too.
4. **`ollama.service` on this machine is `active` with the memory-safety override applied**, and
   the polkit rule is **not** installed — so the live restart is refused, which is what made
   §2.1's decision testable.
5. **`GET /api/v1/version` has two incompatible shapes across the suite** — see §5. The kickoff
   assumed one.

## 5. A cross-component defect this row found and worked around

**The four applications do not agree on the shape of `GET /api/v1/version`, the route
[ADR-0013](../../adr/0013-api-versioning.md) and spec §19 make version negotiation depend on.**

| Application | Payload |
|---|---|
| FreeWeight, LoadCoach | `{"application": {"name", "version", "git_commit"}, "api": {"current", "supported", "deprecated"}, "schemas": {…}}` |
| IdeaPress, PromptCadence, **WeightRoomGym** | `{"application": "<name>", "version": "…", "api_version": "v1", "schema_version": "1"}` |

WeightRoomGym reads **both** (`services/apps.py:_read_version_payload`, with a test naming each
application). It is the console, not the arbiter, and a version route a console cannot parse is a
console that reports a healthy application as unreachable.

**This is a documentation defect and needs an ADR before anything is changed** (CLAUDE.md: *"if
an architectural decision seems missing, that is a defect in the docs — close it with a new
ADR"*). It is **not** in this row's scope: converging it means a payload change in at least two
applications, each a patch release, and picking the winner is an architecture decision.
Recommended as a row of its own before W10, since spec §19 and `api.md` §1 both describe the
route as if there were one shape. The nested form carries strictly more (`supported`,
`deprecated`, `schemas`) and is what ADR-0013's own §-on-negotiation implies; the flat form is
what three of the five emit. Either is defensible; the docs currently promise neither.

## 6. The state the reference machine was left in

* **Five unit files written** to `~/.config/systemd/user/`: `freeweight.service`,
  `loadcoach.service`, `ideapress.service`, `promptcadence.service`, `weightroom.service`. They
  run the per-repo venvs; `freeweight` and `loadcoach` carry `MemoryHigh=22G`, `MemoryMax=24G`,
  `MemorySwapMax=0` (verified live: `MemoryMax=25769803776`, `MemorySwapMax=0` on those two and
  `infinity` on the other two).
* **The four applications are running under their units** and answering: FreeWeight `1.2.1`,
  LoadCoach `1.3.1`, IdeaPress `1.4.1`, PromptCadence `1.3.3`, all `version_verdict=ok`.
* **The units are `disabled`**, so they do not come back after a reboot. One command each if that
  is wanted: `systemctl --user enable freeweight loadcoach ideapress promptcadence`.
* **`weightroom.service` is written but neither enabled nor started** — this row's console ran on
  a scratch port. `wr-gym setup` enables and starts it (ADR-0125 rule 6).
* **Ollama was not touched.** The restart attempt was refused by polkit, as intended;
  `systemctl is-active ollama` is `active` throughout.
* **The operator's real database and configuration were not written to.** The demonstration ran a
  scratch console (loopback, no operator account → open loopback per ADR-0126 rule 6) with its
  own database and CA, over the **real** `~/.config/systemd/user` and the **real** application
  executables. So the `ollama.restart` `refused` row lives in the scratch database: the
  operator's own console will say *not yet known* until they press the button once.

## 7. Demonstration (Phase 2 acceptance criteria)

### Criterion 1 — five units written; LoadCoach started from the console

```text
$ wr-gym units sync --diff
units     /home/jpk/.config/systemd/user
freeweight     written
  --- absent
  +++ WeightRoomGym
  @@ -0,0 +1,20 @@
  +# freeweight.service — generated whole by WeightRoomGym 0.2.0 (ADR-0125 rule 1).
  …
  +ExecStart=/home/jpk/ai/suite/FreeWeight/.venv/bin/freeweight serve
  +MemoryHigh=22G
  +MemoryMax=24G
  +MemorySwapMax=0
loadcoach      written
ideapress      written
promptcadence  written
weightroom     written
reload    systemd reloaded

$ wr-gym units sync                       # idempotent
freeweight     unchanged … weightroom     unchanged
reload    not needed
```

```text
$ GET /api/v1/apps/loadcoach                       # before
  state=stopped unit=inactive uptime=None version=None

$ POST /api/v1/apps/loadcoach/start
  {"audit_id":"01M24G3SDPGYBX22TMRX80E2CF","unit":"loadcoach.service","state":"starting","unit_state":"active"}

$ GET /api/v1/apps/loadcoach                       # the pill, polled
  t+ 2s  state=ok         unit=active      up=2s    version=1.3.1   verdict=ok
  t+ 4s  state=ok         unit=active      up=4s    version=1.3.1   verdict=ok
  t+10s  state=ok         unit=active      up=10s   version=1.3.1   verdict=ok

$ GET /api/v1/audit/01M24G3SDPGYBX22TMRX80E2CF
  unit.start  loadcoach  loadcoach.service  ok  {'verb': 'start'}
```

The live log pane, four seconds of `loadcoach.service`, unwrapped and correctly levelled:

```text
$ GET /api/v1/apps/loadcoach/logs/stream?backfill=8
  01:49:58  loadcoach   info     uvicorn.error              Started server process [638756]
  01:49:58  loadcoach   info     uvicorn.error              Waiting for application startup.
  01:49:58  loadcoach   info     httpx                      HTTP Request: GET http://127.0.0.1:11434/api/ps "HTTP/1.1 200 OK"
  01:49:58  loadcoach   info     loadcoach.services.recover queue.recovered
  01:49:58  loadcoach   info     uvicorn.error              Application startup complete.
  01:49:58  loadcoach   info     uvicorn.error              Uvicorn running on http://127.0.0.1:8766
  01:50:00  loadcoach   info     uvicorn.access             127.0.0.1:42844 - "GET /api/v1/version HTTP/1.1" 200
```

(`operator` is `null` in the audit row above because the scratch console is an open-loopback
install with no account; the real install records the username, which
`tests/integration/test_apps_routes.py` asserts.)

### Criterion 2 — stopped again, every page still rendering

```text
$ POST /api/v1/apps/loadcoach/stop
  {"audit_id":"01M24G4TJKGCPF8DG0KTXK7TTN","unit":"loadcoach.service","state":"stopped","unit_state":"inactive"}

$ every page, HTTP status and size
  /                                  200  3872 bytes
  /apps                              200  5737 bytes
  /apps/freeweight                   200  7703 bytes
  /apps/loadcoach                    200  7691 bytes
  /apps/ideapress                    200  7691 bytes
  /apps/promptcadence                200  7739 bytes
  /logs                              200  6289 bytes
  /ollama                            200  7046 bytes
  /audit                             200  7576 bytes
  /audit?action=unit.start           200  5810 bytes
  /trust                             200  5286 bytes

$ GET /api/v1/health
  status=ok
    database          ok            sqlite at head
    tls               ok            leaf expires in 397 days
    units             ok            systemd reachable; 4 of 4 units written
    app:freeweight    stopped       stopped
    app:loadcoach     stopped       stopped
    app:ideapress     stopped       stopped
    app:promptcadence stopped       stopped
```

### Criterion 3 — the Ollama pane

Live, on the reference machine, **after** the operator had applied the script:

```text
$ GET /api/v1/ollama
unit ollama.service  state active  safe=True  7/7
journal_readable=True  (readable)
restart_permitted=unknown
  pass    OLLAMA_CONTEXT_LENGTH           found=8192        expected=8192
  pass    OLLAMA_MAX_LOADED_MODELS        found=1           expected=1
  pass    MemoryHigh                      found=22G         expected=22G
  pass    MemoryMax                       found=24G         expected=24G
  pass    MemorySwapMax                   found=0           expected=0
  pass    ManagedOOMMemoryPressure        found=kill        expected=kill
  pass    ManagedOOMMemoryPressureLimit   found=50%         expected=50%
```

The red half, against `tests/fixtures/ollama/unsafe-112000-no-cap.txt` — the configuration
`MEMORY_SAFETY.md` §1 names as the cause of the reset:

```text
fail    OLLAMA_CONTEXT_LENGTH           112000
fail    OLLAMA_MAX_LOADED_MODELS        unset (Ollama's default is up to 3 per GPU)
fail    MemoryHigh                      no cap
fail    MemoryMax                       no cap
fail    MemorySwapMax                   no cap
fail    ManagedOOMMemoryPressure        auto
fail    ManagedOOMMemoryPressureLimit   0%
→ the page prints `docs/scripts/apply_memory_safety.sh`
```

The polkit gate, live:

```text
$ GET /api/v1/ollama          → restart_permitted: unknown        (nothing tried yet)
$ POST /api/v1/ollama/restart → HTTP 403
  code    OLLAMA_RESTART_NOT_PERMITTED
  stderr  Failed to restart ollama.service: Access denied as the requested operation requires
          interactive authentication. However, interactive authentication has not been enabled…
  command systemctl restart ollama.service
  path    /etc/polkit-1/rules.d/50-weightroom-ollama.rules
  install sudo install -m 0644 <the file printed above> /etc/polkit-1/rules.d/50-weightroom-ollama.rules
$ GET /api/v1/ollama          → restart_permitted: not_permitted  (the audit row is the probe)
$ GET /api/v1/audit?action=ollama.restart
  ollama.restart refused Failed to restart ollama.service: Access denied as the requested opera…
$ systemctl is-active ollama  → active                            (untouched)
```

### Criterion 4 — `sudo` appears nowhere as an invocation

`tests/security/test_subprocess_discipline.py`, parameterised over every module in `src/`: no
runtime string outside the two instruction modules contains it, no string anywhere *is* it, no
`shell=True`/`os.system`/`os.popen`, and every `subprocess.run`/`Popen` takes an argument list
and an explicit `env`.

### The suite left under its units

```text
  freeweight     ok    active  12s  1.2.1  ok
  loadcoach      ok    active  12s  1.3.1  ok
  ideapress      ok    active  12s  1.4.1  ok
  promptcadence  ok    active  12s  1.3.3  ok

  freeweight     MemoryMax=25769803776  MemorySwapMax=0
  loadcoach      MemoryMax=25769803776  MemorySwapMax=0
  ideapress      MemoryMax=infinity     MemorySwapMax=infinity
  promptcadence  MemoryMax=infinity     MemorySwapMax=infinity
```

## 8. Defects fixed in this row that belong to earlier phases

1. **A partial `[apps.<name>]` table discarded its siblings' defaults** (W1). Writing
   `[apps.loadcoach] executable = "…"` left `base_url` empty, so a running application was
   reported unreachable. Configuration standards §1 requires per-leaf overriding, which the
   module's own docstring claims; the per-application port defaults lived only in
   `AppsSettings`'s `default_factory`, which any partial table bypasses. Fixed with a
   `model_validator`, tested.
2. **`host_identity()` ran `ip -json address` with this process's whole environment** (W1). Gold
   standard G12; it now gets the same allowlist as every other child. Found by this row's new
   AST test over every `subprocess` call site.

## 9. Open, for the operator or a later row

1. **The `GET /api/v1/version` divergence (§5) needs an ADR and a row.** Nothing is broken today
   — the console reads both — but spec §19 and `api.md` §1 describe a route that does not exist
   in one shape.
2. **`0.2.0` is prepared, not tagged and not pushed.** The next tag is `v0.2.0`; `v0.1.1` is
   spent (see the `0.1.0` CHANGELOG entry).
3. **The four units are not `enabled`.** One command if the operator wants them at boot.
4. **`wr-gym doctor` (W4) should detect two things this row hit**: a port held by a process that
   is not the unit's `MainPID`, and an `[apps.*] executable` that is not the install actually
   listening on that application's port.
5. **MirrorWall 0.3's `log_pane` (row WM) supersedes `_log_pane.html`.** This row's pane is
   WeightRoomGym's own, deliberately small, and W3 should replace it rather than extend it.
6. **The `Last-Event-ID` resume on the log streams is a per-connection counter**, so a
   reconnecting browser refills its tail from `-n backfill` rather than replaying exactly. The
   journal cursor is carried in every frame's payload, which is what an exact resume would use;
   `mirrorwall.format_frame` requires an integer `id:`, so using it would mean either a
   non-enveloped frame or a change in MirrorWall. Left as it is, and noted.
