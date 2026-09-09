# Kickoff — W9: WeightRoom Phase 9 — jobs, alerts, prompt editor

**Row:** W9 (Opus 5 · high) — [`docs/roadmap/weightroom-work.md`](../roadmap/weightroom-work.md).
Runs after W8.
**Ships:** `openweight-gym 0.9.0` prepared: the database-backed job queue with leases and
schedules, the alert evaluator with five sources and the banner, the prompt override editor.
**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../roadmap/weightroom-work.md).

**Read first:** [`spec.md`](../apps/weightroom/spec.md) §7.10, §12 (`[jobs]`, `[alerts]`), §13;
[`api.md`](../apps/weightroom/api.md) §4, §7; [`data-model.md`](../apps/weightroom/data-model.md)
(`jobs`, `job_schedules`, `alerts`, `alert_history`); [`development-plan.md`](../apps/weightroom/development-plan.md)
Phase 9; ADR-0010 and **ADR-0029 in full** (the four things a lease queue gets wrong);
`apps/loadcoach/queue-and-scheduling.md` §5–§7 (lease, heartbeat, recovery — the precedent);
ADR-0119 and `MEMORY_SAFETY.md` §2.3 (the journal lines the memory-cap alert matches); ADR-0012,
ADR-0028, `standards/prompt-management-standards.md` §2, §3, §6 (override files, marking);
`packages/setspec/spec.md` (`setspec.prompts` record validation); `history/W8_HANDOFF.md`.

## Decisions already taken — do not reopen

* A `jobs` table with `state`, `lease_expires_at`, `attempt`; one worker thread; heartbeat at a
  third of the lease; a recovery pass at startup requeuing expired leases; no broker (ADR-0010).
  Kinds: `freeweight_suite_run`, `retention_trim`, `backup`, `model_refresh`, plus the
  `catalog_pull` and `docs_index` kinds earlier rows left as callables. Output captured and capped.
* Schedules are rows with a five-field cron expression parsed by **stdlib-only** code; a schedule
  missed during downtime runs once on recovery, never N times (catch-up semantics — write the
  test first).
* Alerts: `app_down`, `memory_cap` (a journal match on `oom-kill`/`MemoryMax`/`systemd-oomd` for
  `ollama.service` or an application unit), `gpu_thermal`, `budget_ceiling`, `breaker_open`; at
  most one open alert per `(source, subject)`; acknowledge with operator and time; history kept
  for ever; **no outbound channel** (spec §2, §3).
* Prompt overrides are written under `$XDG_CONFIG_HOME/<app>/prompts/<prompt_id>.json`, validated
  against the record schema, diffed against the shipped record; deleting restores the shipped
  prompt; FreeWeight's `--allow-prompt-override` rule is shown, not bypassed.

## Gates

**Gate A — the queue.** `domain/jobs.py` (states, lease decisions, the cron parser, catch-up as
pure functions) and `services/jobs.py` (the worker, heartbeat, recovery, the kinds); Alembic
migration; lease-expiry and cancel tests; the Jobs pages and CLI. Commit.

**Gate B — alerts.** `services/alerts.py` (the evaluator thread, each source with a firing and a
clearing fixture, the one-open rule), the banner in the shell, acknowledge, history. Commit.

**Gate C — prompts.** `services/prompts.py` (pack listing via each application's `prompts
list|show`, overrides, validation, diff, delete), the Prompts pages per application;
`CHANGELOG.md`; `0.9.0`. Commit.

## Demonstrate

Plan Phase 9 criteria 1–3 on the reference machine: a scheduled FreeWeight run executed now and
visible in FreeWeight; the memory cap fired on purpose (`MEMORY_SAFETY.md` §2.3) and the banner
within 30 s with the journal line; an IdeaPress prompt overridden, run, marked `user_override`,
and the override deleted.

## Finish line

Gate green, coverage held, one commit per gate, `docs/history/W9_HANDOFF.md`, the row marked done.
