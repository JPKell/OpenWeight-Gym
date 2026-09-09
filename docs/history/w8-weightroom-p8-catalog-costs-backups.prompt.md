# Kickoff — W8: WeightRoomGym Phase 8 — model catalog, costs, backups and migrations

**Row:** W8 (Sonnet 5 · high; overnight allowed) — [`docs/roadmap/weightroom-work.md`](../roadmap/weightroom-work.md).
Runs after W7.
**Ships:** `wr-gym 0.8.0` prepared: the catalog with pull, drop-in, enable/disable and
delete-with-cleanup; the cost dashboard; the backups and migrations pages.
**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../roadmap/weightroom-work.md).

**Read first:** [`spec.md`](../apps/weightroom/spec.md) §7.9, §14 (GGUF drop-in), §13;
[`api.md`](../apps/weightroom/api.md) §5, §3 (the curated `db` routes); [`development-plan.md`](../apps/weightroom/development-plan.md)
Phase 8; ADR-0118 (enable/disable per application, never re-routed); ADR-0069, ADR-0030 (every
money figure carries its unpriced count; usage stored, cost derived); ADR-0008 (canonical identity
is the join key); `packages/loadledger/spec.md` (`loadledger.sql`, `balances`, `position`);
`packages/modelrack/spec.md` (discovery, `list_resident`, the llama.cpp `model_directory` and
digest file, ADR-0071); `standards/database-standards.md` §7–§8; `apps/freeweight/api.md`
(`/database/delete-preview`, `DELETE /database/results`); `history/W7_HANDOFF.md`.

## Decisions already taken — do not reopen

* The catalog joins by canonical identity `provider/name@sha256:…`; per-application `enabled`,
  evidence freshness, residency, size, context; no second registry is kept.
* `ollama pull` is a **job** (W9 builds the runner; this row writes the `catalog_pull` kind as a
  callable with streamed progress and a free-space check, run in a thread until W9 hosts it);
  `ollama rm` and file removal, then each application's `db delete --model` where it exists,
  **previewed and typed-confirmed** (database standards §8).
* GGUF drop-in validates magic bytes and size, containment-checks the target directory, and
  refuses a path outside the configured model directory; then each llama.cpp-configured
  application's `models refresh`.
* Balances come from `loadledger.sql`'s classes over PromptCadence's and IdeaPress's mounted
  tables (read-only), never a hand-written `select`; ceilings are edited on the application's
  settings page (W4's path), never through a `ceiling_raise` approval.
* Backups and migrations are curated calls to each application's own `db` verbs; restore requires
  the unit stopped and a typed name; WeightRoomGym's own database gets the same four verbs.

## Gates

**Gate A — catalog.** `services/catalog.py`: the join over API and database sources, the pull
kind with progress parsing, drop-in with its refusals, enable/disable through each application,
delete with preview and cleanup; the Catalog page. Commit.

**Gate B — costs.** `services/costs.py`: balances per application and window with unpriced
counts and ceiling verdicts; the Costs page with `—` where nothing is priced. Commit.

**Gate C — backups and migrations.** The curated `db` routes and pages per application and for
WeightRoomGym; the backup listing from each application's `backups/`; `CHANGELOG.md`; `0.8.0`. Commit.

## Demonstrate

Plan Phase 8 criteria 1–4 on the reference machine: the catalog listing every model once; a
disable visible in `loadcoach route explain` as `model_disabled`; a small pull with progress; a
GGUF drop-in appearing after refresh; PromptCadence's today against its ceiling with an
unpriced count; a LoadCoach backup landing in LoadCoach's own `backups/`.

## Finish line

Gate green, coverage held, one commit per gate, `docs/history/W8_HANDOFF.md`, the row marked done.
