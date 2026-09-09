# Kickoff — W2: WeightRoom Phase 2 — process control, unified logs, audit page

**Row:** W2 (Opus 5 · high; reviewed same day) — [`docs/roadmap/weightroom-work.md`](../roadmap/weightroom-work.md).
Runs after W1.
**Ships:** `weightroom 0.2.0` prepared: the five `systemd --user` units written and driven
from the console, the journal live per application and unified, Ollama's pane, the Audit page.
**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../roadmap/weightroom-work.md).

**Read first:** ADR-0125 in full; ADR-0119 and `MEMORY_SAFETY.md` §2 (the checklist the Ollama
pane renders); [`spec.md`](../apps/weightroom/spec.md) §7.1 (the `/apps/*` and `/ollama` routes),
§7.3, §11 contracts 2 and 8, §13, §16; [`development-plan.md`](../apps/weightroom/development-plan.md)
Phase 2; [`api.md`](../apps/weightroom/api.md) §2, §5 (Ollama), §7 (audit);
`standards/cross-platform-standards.md` §3; `history/W1_HANDOFF.md`. Precedents: ToolYard's
subprocess discipline (`toolyard/sandbox`: explicit argv, allowlisted environment, output caps —
read it, do not import it), MirrorWall's SSE helper and its slow-consumer test.

## Decisions already taken — do not reopen

* Units are generated whole from one template; the `Memory*` lines go on `freeweight` and
  `loadcoach` only; values from `[host]`; `weightroom.service` carries no cap (ADR-0125 rules 1, 6).
* Linger is required; the wizard runs `loginctl enable-linger` and refuses to continue without it
  (rule 2).
* `systemctl`/`journalctl` by explicit argv; never a shell; every action audited (rule 3).
* Ollama: read `systemctl show`, `/api/ps` through **ModelRack's** Ollama client (never a second
  client), the journal where readable; the restart is polkit-gated and otherwise printed as the
  command; **`sudo` is never invoked** — a grep test (rules 4–5).
* No systemd → process pages *unsupported on this host* by name; everything else works (rule 7).

## Gates

**Gate A — units.** `domain/units.py` (the template as data, rendering, the diff) with goldens per
application; `services/processes.py` with a `SystemdController` port, the real implementation and
a fake on `PATH`-shaped fixtures; `units sync|status|start|stop|restart`; the wizard's units step
and linger. Commit.

**Gate B — control and journal.** `GET /apps`, `/apps/{app}`, `/apps/{app}/health` (the
application's own `/health` proxied with `source`), the start/stop/restart routes (`202` + audit
id), version negotiation per application with the five-minute recheck and
`APP_VERSION_MISMATCH`; `services/journal.py` history (`-o json`, cursor paging, 5 000-row cap)
and follow as SSE with MirrorWall's bounded queues and the *dropped N lines* frame; the unified
stream; `weightroom apps status`, `weightroom logs`. Commit.

**Gate C — Ollama and the Audit page.** `GET /ollama` with the §2.1 checklist as findings (the
reference machine's current override — `OLLAMA_CONTEXT_LENGTH=112000`, no cap — is the failing
fixture; write it as such), `GET /ollama/ps`, `POST /ollama/restart` with
`OLLAMA_RESTART_NOT_PERMITTED` carrying the rule text and the install command; the Audit page with
filters. `CHANGELOG.md`; `0.2.0`. Commit.

## Demonstrate

Plan Phase 2 criteria 1–4 on the reference machine: five units written; LoadCoach started from
the console with the pill, the live log and the audit row; stopped again with every page still
rendering; the Ollama pane red on the §2.1 lines until the operator runs
`docs/scripts/apply_memory_safety.sh`, then green. Screenshot or transcript in the handoff.

## What this row must decide, and write down

* The probe for the polkit grant (rule 5 leaves the mechanism to the row): the rule file's
  presence, a recorded last outcome, or a `systemctl --user` dry-run equivalent — pick one, test
  it, say why.
* The journal group on the reference machine: whether `journalctl -u ollama` is readable by the
  operator, and what the pane says when it is not.

## Finish line

Gate green, coverage held, one commit per gate, `docs/history/W2_HANDOFF.md`, the row marked done.
Never run overnight; the diff is reviewed the same day.
