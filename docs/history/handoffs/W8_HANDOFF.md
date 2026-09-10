# W8 Handoff — WeightRoomGym Phase 8: model catalog, costs, backups and migrations

**Row:** W8 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Sonnet 5 · high;
overnight allowed). **Date:** 2026-09-10. **Kickoff:**
[`w8-weightroom-p8-catalog-costs-backups.prompt.md`](../prompts/w8-weightroom-p8-catalog-costs-backups.prompt.md).
**Ships:** `wr-gym` — the kickoff names `0.8.0`; **no version bump lands here.** WA1's row
(2026-09-10) recorded the operator's standing instruction to hold every version until the W arc
ends, so this row's work goes under `CHANGELOG.md`'s `[Unreleased]` section and `__about__.py`
stays `0.7.0`, the same way WA1 left SetSpec and FreeWeight. Built on `main` in
`~/ai/suite/WeightRoom`; no worktree, no other session held the tree.

## 1. What was built, by commit

| Commit | Gate | What |
|---|---|---|
| `9ca3638` | A | `services/catalog.py` — the join across FreeWeight's and LoadCoach's own `models` tables (the only two with one) by canonical id, reflected off the read-only engine `services/db_reader.py` already opens; evidence freshness always from FreeWeight; residency from LoadCoach's own `residency` table first, an Ollama `/api/ps` fallback for a row it does not carry; enable/disable proxied to each application's `POST /models/{id}/enabled`; GGUF drop-in (magic bytes, size, containment, one shared llama.cpp directory, refresh of every configured application); delete with preview and cleanup (Ollama tag or GGUF file, then FreeWeight's own `delete-results`); a pull streamed from Ollama's own `/api/pull` in a daemon thread, progress held in memory (`PullRegistry`). `web/routes/catalog.py`, `templates/catalog.html`. `services/db_reader.reflect_table` promoted out of `services/overview.py`. 11 new unit tests (`tests/unit/test_catalog_domain.py`), 8 new audit-registry exercises, 2 new upload routes in the security checklist |
| `aa827db` | B | `services/costs.py` — `SqlLedger` bound to the same read-only engine, over PromptCadence's and IdeaPress's mounted `ledger_*` tables; today's `PER_DAY` window (populated by every debit regardless of configured ceilings — verified empirically against a fixture database) for both; PromptCadence's `daily_money_ceiling` the one ceiling evaluated app-wide, with a real verdict; IdeaPress's own ceilings are `PER_RUN`/`PER_TAG`, unevaluable app-wide, so its row carries no verdict. `web/routes/costs.py` (read-only, no audit exercise owed), `templates/costs.html`. 5 unit tests, 4 route tests |
| `9176389` | C | `services/db_curated.py` gains `application_backups` (an application's own `backups/`, never WeightRoomGym's guarded-write directory), `run_self_curated` (WeightRoomGym's own `status`/`backup`/`upgrade`, in-process) and `self_backups`; `services/database.backup_directory` promoted from a private helper. `web/routes/backups.py`, `templates/backups.html`. 8 new unit tests (`tests/unit/test_db_curated_self.py`), 6 new route tests, 3 new audit-registry exercises |

**The gate**, local, Python **3.14.4** (`.venv/bin/python -m pytest`): `ruff format --check .`
clean (166 files), `ruff check .` clean, `mypy src tests` clean (160 files, strict), `lint-imports`
**5 contracts kept**, `wr-gym config reference --check` matches, `pytest -m "not live and not
performance"` **1242 passed**, coverage **89.98 %** (floor 85 %; `services/costs.py` 100 %,
`web/routes/costs.py` 100 %, `services/db_curated.py` 88 %, `web/routes/backups.py` 92 %,
`services/catalog.py` 76 %, `web/routes/catalog.py` 65 %).

## 2. What the kickoff and the docs did not settle, and where this row put it

1. **Only FreeWeight and LoadCoach have a `models` table at all.** IdeaPress and PromptCadence
   carry none of their own (confirmed by reading their actual ORM models, not the docs) — they
   route every model call through LoadCoach. ADR-0118's own text already says as much ("The
   applications each own their own column"), but the kickoff's `apps: {name: {...}}` catalog shape
   reads as if all four might contribute; only two ever do. `CATALOG_APPS = ("freeweight",
   "loadcoach")`.
2. **A canonical id cannot be a plain FastAPI path parameter.** `provider/name@sha256:digest`
   contains `/`, which Starlette's default converter treats as a segment boundary even when
   percent-encoded (`%2F` is decoded to a literal `/` before matching, verified empirically) —
   ADR-0024 already says this about LoadCoach's own `model_ref`, and it is exactly as true of the
   catalog's own `{ref}`. Both routes that carry it (`POST /catalog/{ref:path}/enabled`,
   `DELETE /catalog/{ref:path}`) use Starlette's `:path` converter instead, which matches the rest
   of the path literally, encoded or not. Api.md's route table should gain this note at W10's pass.
3. **`ollama pull`/`ollama rm` are not in ModelRack's scope at all** (its spec's own non-goal
   list: "No model downloading"). The kickoff's wording ("`ollama pull` as a job") reads as if
   ModelRack might supply a client; it does not. This row talks to Ollama's HTTP API directly
   (`/api/pull` streamed NDJSON, `/api/tags`, `DELETE /api/delete`) — a second client, but not the
   one ADR-0125 rule 4 is about, since ModelRack offers nothing here to duplicate.
4. **Every LoadLedger debit touches its `PER_DAY` window regardless of configured ceilings**
   (`BalanceBook.windows_touched`, verified against a fixture database) — not documented anywhere
   this row could find, and load-bearing for the whole Costs page: it is *why* IdeaPress, which
   declares no daily ceiling at all, still has a real "today" figure to show. Worth a line in
   `packages/loadledger/spec.md` §11 at the next pass through that document.
5. **IdeaPress's own ceilings cannot be evaluated app-wide.** `per_output_*` is `PER_RUN` (one
   unit), `per_project_*` is `PER_TAG` (one project) — both need a specific target, and
   `Ledger.position()` refuses a `PER_RUN` ceiling outright by design. The kickoff's "the ceilings
   in each application's configuration" reads as if every application has one dashboard-shaped
   ceiling; only PromptCadence's `daily_money_ceiling` is. IdeaPress's Costs row shows today's
   totals with no ceiling verdict, honestly, rather than a fabricated one.
6. **A self-restore route cannot succeed, so it does not exist.** WeightRoomGym's own database
   gets `status`/`backup`/`upgrade` in-process (`services/database.py`'s own functions, no
   subprocess); a live restore would replace the very connection pool serving the request that
   asked for it, which no other application's restore has to contend with (each of *their*
   restores runs from a request to a *different* process). The kickoff's "the same four verbs"
   is answered as three routes plus an explanation, never a fourth route that always fails —
   found while wiring the audit-registry exercise, which requires every state-changing route to
   demonstrate one successful call; there is no such call for a restore that cannot happen live.

## 3. Decisions inside the implementation worth knowing

* **The join is a plain reflection, never a second registry** — `services/db_reader.reflect_table`
  (promoted out of `services/overview.py`, which already needed the identical helper) against
  `model_descriptors` and `capability_evidence` in FreeWeight, `residency` in LoadCoach. An
  application whose database is unreachable or at an unknown revision contributes nothing to the
  join, silently; the page is best-effort, not all-or-nothing.
* **GGUF drop-in refuses when the configured llama.cpp applications disagree on `model_directory`**
  rather than picking one — `llamacpp_targets()` reads FreeWeight's `GET /provider` and LoadCoach's
  `GET /providers` live and requires exactly one distinct directory across every llama.cpp entry
  found. On the reference machine both are configured against the same physical directory
  (`~/ai/models/llm` per memory), so this should never actually fire there.
* **The pull job is deliberately not durable** — a daemon thread, its progress a growing list held
  in `PullRegistry` (`app.state.catalog_pulls`), lost on a restart and invisible to a second
  console process. This is what the kickoff's "run in a thread until W9 hosts it" asks for, no
  more; the SSE route replays by list index within the process's own lifetime, not across one.
* **Every catalog route audits exactly once, success or refusal** — `_enable`, `_dropin` and
  `_delete` in `web/routes/catalog.py` each wrap their own work in one `try/except SuiteError`
  that writes the row either way, matching `web/routes/databases.py`'s `_audited_*` discipline.
  The first draft only audited success, which the audit-registry test caught immediately (a
  refused call left zero rows, not one).
* **`services/costs.py`'s money formatting lives in one function** (`money_text`), and the Costs
  page's route passes `AppCosts.as_json()` to the template rather than the dataclass itself — a
  template has no business calling `Money.to_decimal()` on its own.
* **Three new audit actions**: `catalog.enabled`, `catalog.dropin`, `catalog.delete` (`catalog.pull`
  was already reserved in the vocabulary, unused until this row). Costs has none — it changes
  nothing, the same reasoning the database viewer's reads already rest on.
* **An application not installed degrades to one row's failure on the Backups page, never the
  whole page** — `web/routes/backups.py`'s `_status()` catches `SuiteError` around each
  application's `db status` call and reports it in the result rather than letting it raise; found
  by the audit-registry exercise for `POST /backups/self`, whose page re-render hit exactly this
  with FreeWeight not installed in the test fixture.
* **`services/database.backup_directory`** was `_backup_directory`, private, used once; promoted
  alongside `services/db_curated.self_backups` and `application_backups`, which both need the same
  "where do this database's own backups live" answer for two different databases (WeightRoomGym's
  own engine vs. another application's file path).

## 4. What is deliberately not here

* **A live demonstration on the reference machine.** Every gate above is proved against fixture
  databases (`tests/fixtures/databases/`, real schema snapshots) and respx-mocked HTTP, the same
  standard `services/db_reader.py`'s own tests hold to — but unlike W7, **this row ran unattended
  and nothing here was exercised against the real FreeWeight, LoadCoach or Ollama on the reference
  machine.** Plan Phase 8's four acceptance criteria (the catalog listing every real model once, a
  disable visible in `loadcoach route explain`, a real small pull with progress, a real GGUF
  drop-in, PromptCadence's real today against its real ceiling, a real LoadCoach backup landing in
  its own `backups/`) are **not demonstrated** in this handoff. That is the operator's or a
  reviewing row's to do, the way W7's own demonstration needed a throwaway console against copied
  databases and a live `systemd --user`.
* **FreeWeight's own deletion through the console, against a copy of its database.** The kickoff
  asks for this explicitly (mirroring W7's own gap in the same area). `catalog_delete_preview`/
  `catalog_delete_confirm` call the identical `services/db_curated.delete_results` W7 built and
  tested against a mocked FreeWeight; this row adds no new coverage of that path beyond what W7
  already has, and does not run it against a real FreeWeight either.
* **A concurrency limit on pulls.** One operator, one console; nothing here queues or throttles
  more than one pull started from the same process.
* **Per-project ceiling rows on the Costs page.** PromptCadence's named `[budget.projects.*]`
  ceilings and IdeaPress's per-run/per-project ones are real and evaluable *against one run or
  project*, which this dashboard-shaped page does not pick. A future row could add a "look up one
  run's or project's balance" affordance; this one does not.
* **Jobs, alerts, the prompt editor.** Explicitly W9's, per the plan's own "Deferred" line.

## 5. For the operator

1. **Nothing pushed or tagged.** Three commits on `main` (`9ca3638`, `aa827db`, `9176389`) plus
   this handoff's own docs commit.
2. **No version bump, per WA1's standing instruction.** `wr-gym` stays `0.7.0`; everything above
   is under `CHANGELOG.md`'s `[Unreleased]`. The kickoff's `0.8.0`s throughout are the row's
   original plan, superseded by the same operator decision WA1 recorded.
3. **Demonstrate Phase 8's four criteria before declaring this row done in the way W7 was** — see
   §4. A throwaway console against copies of the reference machine's databases, the pattern
   W7_HANDOFF.md §4 already worked out, should transfer directly.
4. **GGUF drop-in and the pull have never touched a real filesystem or a real Ollama.** Worth a
   careful first real run rather than trusting the mocks alone — a free-space check against a
   hardcoded 2 GiB floor (`_MIN_FREE_BYTES_FOR_PULL`), and a directory-agreement check that has
   only ever seen two mocked endpoints agree or disagree, not the real `~/ai/models/llm`.
5. **`web/routes/catalog.py`'s UI page routes are the least-covered surface in this row**
   (65 % — the SSE stream and the three page-form routes are only smoke-tested through the
   audit-registry exercises, not asserted on their rendered content). If the Catalog page misrenders
   something on first real use, start there.

## 6. Open for later rows

* **W9** hosts the pull as a real queued job (`catalog_pull` is already a reserved audit action
  and a `PullRegistry` shape to migrate off of) and builds the jobs/alerts/prompt-editor
  infrastructure this row explicitly defers.
* **W10** should fold in: the api.md note about `{ref:path}` (§2 item 2), a `packages/loadledger/
  spec.md` §11 line about `PER_DAY` being populated unconditionally (§2 item 4), and the OpenAPI
  snapshot picking up nine new routes (`/catalog*`, `/costs*`, `/backups`, `/db/status|backup|
  upgrade`).
* **Any row that revisits the Costs page** might want a "look up one run or project" affordance
  for the ceilings this row could not show app-wide (§4).
