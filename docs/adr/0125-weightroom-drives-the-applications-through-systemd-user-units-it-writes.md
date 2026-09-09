# ADR-0125 — WeightRoom drives the applications through `systemd --user` units it writes; Ollama is read, and restarted only through a polkit rule the operator installs

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 2
(process control is in the exception), [ADR-0119](0119-model-servers-run-under-a-host-memory-cap.md)
(the memory cap the units carry; its decision 4's parent-scope wrapper becomes the unit),
[`MEMORY_SAFETY.md`](../MEMORY_SAFETY.md) §2 (the host protections WeightRoom checks and, where it
can, applies), [Cross-platform Standards §3](../standards/cross-platform-standards.md) (service
management is "systemd user unit" on Linux and documentation elsewhere),
[Security Standards §1](../standards/security-standards.md) (the OS user boundary).
**Source:** the operator interview of 2026-09-09, decision D4.

## Context

Before this row the four applications ran however the operator started them: `launch.sh` from
the workspace, a terminal, or the `systemd --user` units `expose_on_lan.sh` wrote once. There is
no unit on the reference machine today (`~/.config/systemd/user/` holds none of the four), the
operator's session lingers (`Linger=yes`), and Ollama runs as a **system** unit under
`/etc/systemd/system/ollama.service` with an override that still sets
`OLLAMA_CONTEXT_LENGTH=112000` and no memory cap — the configuration
[`MEMORY_SAFETY.md`](../MEMORY_SAFETY.md) §1 names as the cause of the 2026-09-09 reset.

WeightRoom needs to start, stop, restart and tail each application, know whether one is running
(the [ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)
guard depends on it), and show and — where it can — restart Ollama. It runs as the operator's
user and is never root. Two facts follow: it can own everything under `systemd --user` outright,
and it can do nothing to a system unit without a grant a root user writes.

## Decision

**The four applications and WeightRoom itself run as `systemd --user` units that WeightRoom
writes and drives. Ollama's system unit is read through `systemctl show` and Ollama's own API;
it is restarted from the console only when a polkit rule the operator has installed permits
exactly that, and otherwise the restart is shown as the command to run.**

1. **Units are written by `weightroom setup` and refreshed by `weightroom units sync`**, at
   `~/.config/systemd/user/<app>.service` for `freeweight`, `loadcoach`, `ideapress`,
   `promptcadence` and `weightroom`. The content is deliberately small and the file is
   regenerated whole — an operator's hand edit is overwritten on the next sync and the console
   says so:

   ```ini
   [Unit]
   Description=<App> (Local AI Suite; loopback, fronted by WeightRoom)
   After=network.target

   [Service]
   ExecStart=<venv>/bin/<app> serve
   Restart=on-failure
   RestartSec=3
   # ADR-0119: the model-serving applications run under the host-memory cap. These replace
   # MEMORY_SAFETY.md §2.2's systemd-run wrapper for a unit-managed application.
   MemoryHigh=22G
   MemoryMax=24G
   MemorySwapMax=0

   [Install]
   WantedBy=default.target
   ```

   The three `Memory*` lines are written for `freeweight` and `loadcoach` only, with values from
   WeightRoom's `[host] memory_high`/`memory_max` (defaults `RAM − 8 GB` / `RAM − 6 GB`, the
   `MEMORY_SAFETY.md` §2.1 rule), and are what ADR-0119 decision 4 called "until decision 2
   ships": now that the launcher cap exists, the unit cap is the outer belt for the parent
   process and anything it spawns, and the launcher cap the inner one for `llama-server`.
   `<venv>` is the interpreter that owns the installed `<app>` (`shutil.which` on the
   operator's PATH, or `[apps.<app>] executable` in WeightRoom's configuration); an application
   that is not installed has no unit and is shown as *not installed*, not *stopped*.

2. **Lingering is required and the wizard enables it.** `loginctl enable-linger` for the
   operator's own user is a polkit-authenticated action the desktop session grants; the wizard
   runs it, reports the result, and refuses to continue on failure with the command to run by
   hand — units under `user@<uid>.service` stop at logout otherwise, and a console that dies
   with the SSH session is not an operator tool.

3. **Control is `systemctl --user`, logs are `journalctl --user`, and every action is audited.**
   `start`, `stop`, `restart`, `enable`, `disable` and `is-active` are subprocess calls with an
   explicit argv (never a shell); the journal is read with `journalctl --user -u <app> -o json
   -f` and streamed to the page over SSE, with `--since`/`--until` for the history view. Each
   control action writes an `audit_log` row naming the unit, the verb, the operator and the
   outcome. A host without `systemctl` on `PATH` degrades the process pages to *unsupported on
   this host*, by name ([Cross-platform Standards §3](../standards/cross-platform-standards.md)),
   and the rest of the console works.

4. **Ollama is a system unit and stays one.** WeightRoom reads `systemctl show ollama.service`
   (readable by any user: `ActiveState`, `MemoryMax`, `MemorySwapMax`, `ManagedOOMMemoryPressure`,
   the `Environment=` lines), reads `/api/ps` and `/api/tags` through ModelRack's Ollama client,
   and reads `journalctl -u ollama` where the operator's group permits it (`systemd-journal` or
   `adm`; otherwise *journal not readable*, by name). `doctor` compares the unit against
   [`MEMORY_SAFETY.md`](../MEMORY_SAFETY.md) §2.1 — cap present, swap denied, oomd on the
   unit, `OLLAMA_CONTEXT_LENGTH` at a size the card serves, `OLLAMA_MAX_LOADED_MODELS=1` — and
   reports each line found or missing; the fix is `docs/scripts/apply_memory_safety.sh`,
   **printed**, never run.

5. **Restarting Ollama needs a grant, and the grant is a polkit rule.** The wizard prints the
   rule and the install command; WeightRoom never runs `sudo`:

   ```javascript
   // /etc/polkit-1/rules.d/50-weightroom-ollama.rules
   polkit.addRule(function (action, subject) {
       if (action.id == "org.freedesktop.systemd1.manage-units" &&
           action.lookup("unit") == "ollama.service" &&
           (action.lookup("verb") == "restart" || action.lookup("verb") == "start" ||
            action.lookup("verb") == "stop") &&
           subject.user == "<operator>") {
           return polkit.Result.YES;
       }
   });
   ```

   ```bash
   sudo install -m 0644 <printed file> /etc/polkit-1/rules.d/50-weightroom-ollama.rules
   ```

   With the rule present, `systemctl restart ollama.service` (no `sudo`) succeeds for the
   operator and the console offers the button; WeightRoom detects the grant by attempting
   `systemctl --dry-run`-equivalent — `busctl call … GetUnit` is always allowed, so the probe is
   the rule file's presence plus a recorded outcome of the last attempt — and, without it,
   renders the restart as the command to run. A sudoers line was rejected: it grants a command,
   polkit grants a unit and a verb, and the narrower grant is the right one for a console that
   is reachable from the LAN.

6. **WeightRoom is itself a unit, and may restart itself.** `weightroom.service` is written,
   enabled and started by the wizard so the console outlives the login that installed it.
   *Restart WeightRoom* from the console is `systemctl --user restart weightroom.service`;
   the page reconnects its SSE streams when the server returns. The unit carries no memory cap:
   WeightRoom serves no model.

7. **Linux with systemd is the supported host for 1.0.** On any other host every process page,
   the unit sync and the Ollama pane report *unsupported on this host* with the reason, the
   ADR-0124 guard's condition 1 falls back to the port probe alone, and nothing else in the
   console changes. Windows and macOS service management stay "documentation only" as the
   cross-platform standard already says.

## Consequences

*Positive.* One command puts the whole suite under supervision with restart-on-failure, the
memory cap on the two applications that launch model servers, and a journal per application
that the console can show live. `MEMORY_SAFETY.md` §2.2's `systemd-run` wrapper is retired for
unit-managed applications and kept for ad-hoc runs (`pytest -m live`, a one-off `freeweight run
start` from a shell).

*Negative.* Unit files are generated, so an operator who wants a different `ExecStart` sets it in
WeightRoom's configuration rather than editing the unit. That is one more place configuration
lives, and it is the price of a file WeightRoom can regenerate safely.

*Negative.* Ollama's restart is a second-class action until a root user installs the rule. The
console says so, in the words of the command; nothing pretends to have restarted a daemon it
could not.

*Neutral.* `launch.sh` at the workspace root keeps working for a developer who wants four
processes in a terminal; it is not the operator path any more.

## Alternatives considered

* **Supervise the applications as WeightRoom's own child processes.** Rejected: the console
  would then be the thing whose restart stops every application, and the memory cap would need
  re-implementing that systemd already provides.
* **Run Ollama as a user unit too**, so no grant is needed. Rejected: Ollama's installer writes a
  system unit, the GPU driver set-up assumes it, and moving it is host administration the suite
  should not perform behind the operator's back.
* **A sudoers `NOPASSWD` line for `systemctl restart ollama.service`.** Rejected in rule 5.
* **Restart Ollama by killing its runner through `/api/ps` semantics** (load a model with
  `keep_alive: 0`). Not a restart; it unloads a model. Offered as *unload* where it applies, never
  described as a restart.

## Revisit when

* **A second supervised model server appears** (`llama-server` under a unit of its own, a vLLM).
  Rule 4's Ollama-specific reads become a per-server adapter.
* **A host without systemd needs process control**, at which point rule 7's degradation becomes a
  `ProcessController` port with a second implementation, and the cross-platform standard's
  "documentation only" row is reopened.
