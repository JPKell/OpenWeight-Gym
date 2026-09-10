# W9 Handoff — WeightRoomGym Phase 9: jobs, alerts, prompt editor

**Row:** W9 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Opus 5 · high).
**Date:** 2026-09-10. **Kickoff:**
[`w9-weightroom-p9-jobs-alerts-prompts.prompt.md`](../prompts/w9-weightroom-p9-jobs-alerts-prompts.prompt.md).
**Ships:** `wr-gym` — the kickoff names `0.9.0`; **no version bump lands here** (the operator's
standing instruction, recorded at WA1: every version holds until the W arc ends). The work is under
`CHANGELOG.md`'s `[Unreleased]` and `__about__.py` stays `0.7.0`. Built on `main` in
`~/ai/suite/WeightRoom`, plus one unreleased commit each in IdeaPress and FreeWeight (§2 items 1
and 12). Row W8's reference-machine demonstration of Plan Phase 8 is folded in here (§4.1), as the
operator decided at W8.

## 1. What was built, by commit

| Repository | Commit | Gate | What |
|---|---|---|---|
| WeightRoom | `870cec5` | A | `domain/jobs.py` — states and transitions, lease and recovery decisions, a stdlib five-field cron parser (UTC; lists, ranges, steps, names, `7` = Sunday, Vixie's day-of-month/day-of-week OR rule, a never-firing expression refused), once-only catch-up, per-kind parameters. `services/jobs.py` — compare-and-set claim, a lease keeper thread renewing held jobs every lease/3, recovery at startup and on every tick, the cancel flag, schedules, the worker, captured and capped output, one `job.run` audit row per execution. `services/job_kinds.py` — `freeweight_suite_run`, `backup`, `model_refresh`, `retention_trim`, `catalog_pull` (W8's thread moved onto the queue), `docs_index`, `self_restore`. ADR-0136 and `services/self_restore.py`. Migration `0006` (tables plus five disabled seeded schedules), `/jobs` pages and API, `wr-gym jobs`, `wr-gym db restore-self` |
| WeightRoom | `afc877e` | B | ADR-0137. `domain/alerts.py` (`decide()` pure), migration `0007` with a partial unique index holding one active alert per (source, subject). `services/alerts.py` — the evaluator thread and the five sources `app_down`, `memory_cap`, `gpu_thermal`, `budget_ceiling`, `breaker_open`, each with a firing and a clearing fixture; apply, acknowledge, history kept for ever. The banner on every shell page (polled every 5 s), `/alerts`, `/alerts/history`, `wr-gym alerts`. No outbound channel |
| WeightRoom | `43883bb` | C | `services/prompts.py` — each pack read through the application's own `prompts list\|show`, joined with the overrides under `$XDG_CONFIG_HOME/<app>/prompts/`; a candidate validated with `setspec.prompts.load_record` in a temporary directory beside the real path, then renamed into place; the diff against the shipped record; delete restores the shipped prompt. Each application's rule shown beside the editor, FreeWeight's `--allow-prompt-override` shown and never bypassed. `/apps/{app}/prompts` pages and API; migration `0008` (IdeaPress `0011` is a known revision, with its fixture database) |
| WeightRoom | `925bbcb` | demo fix | `CATALOG_DROPIN_REFUSED` answered `409`, not `500` — found by §4.1 |
| IdeaPress | `35ea090` | C | Override loading (prompt standards §6), `attempts.prompt_source` with migration `0011` back-filling `pack`, `prompts list\|show --shipped`, the source in the stage and unit reports, `unit show --provenance` and the prompts health component |
| FreeWeight | `945ae54` | C | `prompts show --json` carries the whole shipped record under `record` (additive) |

**The gate, WeightRoom**, local, Python **3.14.4** (`.venv/bin/python -m pytest`, tools from
`.venv/bin`): `ruff format --check .` clean (193 files), `ruff check .` clean, `mypy src tests`
clean (187 files, strict), `lint-imports` **5 contracts kept**, `wr-gym config reference --check`
matches, `pytest -m "not live and not performance"` **1462 passed, 3 skipped**, coverage
**90.09 %** (floor 85 %; W8 left 89.98 %). New modules: `services/prompts.py` 94 %,
`web/routes/prompts.py` 91 %, `services/jobs.py` 88 %, `services/alerts.py` 86 %,
`services/self_restore.py` 86 %, `services/job_kinds.py` 78 %.

**IdeaPress**, Python **3.13.15** (its `.venv`): `ruff format`/`ruff check` clean, `mypy` clean (206
files), `lint-imports` 4 kept, `pytest` **1260 passed, 6 skipped**. **FreeWeight**, Python
**3.14.4** (its `.venv`): `pytest` **2681 passed, 30 skipped**.

## 2. What the kickoff and the docs did not settle, and where this row put it

1. **IdeaPress never loaded a prompt override** (and neither do LoadCoach or PromptCadence), so
   Criterion 3 could not be met by WeightRoomGym alone. Put to the operator, who chose to change
   IdeaPress in this row: `35ea090`, unreleased.
2. **LoadCoach and PromptCadence have no `prompts` command.** Their Prompts pages say so by name
   rather than offering an editor that writes files nothing reads.
3. **Criterion 3 names `stages.draft.article`;** IdeaPress's draft prompt is `stages.draft.write`.
4. **`native.speed` does not exist.** The seeded `freeweight_suite_run` schedule uses
   `native.performance`, and is seeded without a model, so it reports a `problem` and cannot be
   enabled until one is chosen.
5. **Spec §7.10's `freeweight run start … --wait` does not exist.** `run start` executes in-process
   and exits `7` when another process holds the execution slot; the job then follows the run with
   `freeweight run wait <id> --json --timeout`.
6. **The spec had alerts evaluated on "the same worker", and an inactive unit counted as down.**
   ADR-0137 gives the evaluator its own thread (a twenty-minute FreeWeight job would otherwise
   silence every alert for twenty minutes) and defines `app_down` as a failed or auto-restarting
   unit, or one active for 60 s whose `/api/v1/health` is not `200`. A unit the operator stopped is
   not down.
7. **"Acknowledge closes it" is split by kind** (ADR-0137): a condition source clears itself when a
   reading that covers its subject finds it right; `memory_cap` is an event and closes only on
   acknowledgement. A reading that could not look covers nothing, so it never clears an alert.
8. **Schedules are seeded by migration `0006`**, all disabled, rather than by a setup step.
9. **ADR-0134 rule 3's 90-day expiry of guarded-write backups was never implemented by W8.**
   `retention_trim` does it.
10. **`weightroom.service` itself is uncapped**, so a FreeWeight run launched from it would inherit
    no memory cap. `freeweight_suite_run` launches under `systemd-run --user --scope -p
    MemoryHigh -p MemoryMax -p MemorySwapMax=0` from the host settings, and refuses to run without
    `systemd-run` (ADR-0119's rule, applied to the console).
11. **WeightRoomGym's own restore** (the operator's W8 decision) is ADR-0136: the job hands off to a
    transient unit `wr-gym-restore-<job>` running `wr-gym db restore-self --receipt …`, which stops
    `weightroom.service`, takes a pre-restore backup, restores, carries the job and audit rows
    forward, and starts the unit again; a failure puts the database back and still starts it. It is
    refused unless the console's own cgroup is `weightroom.service`.
12. **FreeWeight's `prompts show --json` carried no record** to start an override from or diff
    against: `945ae54`.
13. **`MEMORY_SAFETY.md` §2.3 no longer fires the cap** on the reference machine — found by the
    demonstration, §4.4.

## 3. Decisions inside the implementation worth knowing

* **The claim is the only writer of `attempt`**, and it is a compare-and-set on `state = 'queued'`.
  The lease keeper thread renews, never the worker, so a job's own work cannot starve its lease.
  Recovery requeues an expired lease of an idempotent kind; `freeweight_suite_run` and
  `self_restore` fail with `worker_lost` instead; a job whose cancel was requested becomes
  `cancelled`.
* **A missed schedule fires once**, and its next slot is the first one after now. The tick moves
  `next_run_at` by compare-and-set, so a second tick (or a second console) enqueues nothing.
* **"Run now" (`POST /jobs {"schedule_id"}`) does not move `last_run_at` or `last_job_id`.** Those
  record cron fires; the run-now job carries `schedule_id`, which is the link. Seen in §4.2.
* **`catalog_pull` is a queued job now.** `PullRegistry.adopt(job_id, name)` keeps W8's in-memory
  progress for the stream; the pull's SSE route falls back to the job row once the registry has
  nothing.
* **`memory_cap` reads both journals** with `--grep` on the kill pattern (`oom-kill`, `OOM killer`,
  `MemoryMax`, `systemd-oomd`, `memory pressure`); `journalctl` exiting `1` with no output is "no
  match", anything else is a reading problem. A line counts when it names a watched unit — the
  Ollama unit or one of the four application units — in its message or its unit field.
* **An override is validated by the application's own loader before it is written**, in a temporary
  directory beside the real path, then renamed into place; a prompt id with more than one shipped
  version is refused rather than guessed.
* **Four new audit actions**: `job.enqueue`, `job.cancel`, `job.schedule`, `prompt.delete`.

## 4. Demonstration on the reference machine

A throwaway console on `127.0.0.1:8781` (open loopback, its own TLS and SQLite database under the
session scratchpad, WeightRoom's `.venv`, Python 3.14.4) driving the real four applications through
their `systemd --user` units and the operator's own token files, `alerts.interval_seconds = 30`.
Stopped afterwards by its environ-verified pid.

### 4.1 W8's Phase 8 criteria

* **Catalog:** 16 models, each listed once with FreeWeight's and LoadCoach's enabled state and
  evidence (17 after the pull below).
* **Disable:** `gpt-oss:20b` disabled for LoadCoach from the console; the catalog showed
  `loadcoach: false`, and `loadcoach route explain --task general.chat` listed
  `ollama/gpt-oss:20b@sha256:17052f91a42e: model_disabled`. Re-enabled, it went back to
  `insufficient_vram` (IdeaPress's `qwen3.5:9b-q8_0` was resident, so no model was eligible either
  way).
* **Pull:** `smollm2:135m` as `catalog_pull` job `01M26MJ9FA266PG6Q5H7YPYA59` — 155 progress frames
  over SSE with completed/total bytes, `success`, 11 s. It reached the catalog only after a
  `model_refresh` job (`01M26MN0NDRPCHNWQ0BRC7QQV2`: FreeWeight added 1, LoadCoach added 1) — a pull
  does not refresh the applications (§5 item 5f).
* **GGUF drop-in: not demonstrable.** Refused with `CATALOG_DROPIN_REFUSED` — "No application
  configures a llama.cpp model_directory; there is nowhere to drop a GGUF file in." — because
  FreeWeight's provider is `ollama` and LoadCoach has one `ollama` registration. The refusal was
  audited but answered `500`; fixed in `925bbcb` with a test. "Appears after refresh" is **not**
  shown.
* **Costs:** PromptCadence today (2026-09-10) 32,150 tokens, no money, 48 unpriced debits, its
  `per_day` verdict not exceeded with 20.00 USD remaining; IdeaPress 70,978 tokens, 86 unpriced, no
  verdict (W8 §2 item 5).
* **LoadCoach backup** from the console: `~/.local/share/loadcoach/backups/manual-20260910T214614178900Z.sqlite3`
  (8,794,112 bytes), in LoadCoach's own `backups/`.

### 4.2 Criterion 1 — a scheduled FreeWeight run executed now

* The `freeweight_suite_run` schedule (`01M26M1DYZRSQYKSVVGB42K5BF`) enabled with model
  `ollama/smollm2:135m@sha256:9077fe9d2ae1`, suite `native.performance`, `allow_prompt_override`
  false; `next_run_at` became 2026-09-11T02:00Z.
* The first run-now job (`01M26MPQHXJNW3THV0E01DEGGW`) failed in under a second — `freeweight
  exited 4`, "no such column: runtime_profiles.adapters_registered". The operator's FreeWeight
  database was at `0009`; the FreeWeight tree has been at head `0010` since WA1 (`50dc05a`).
  `freeweight db backup` (`freeweight-0009-20260910T214958831329Z.sqlite3`) and then `freeweight db
  upgrade` (`0009` → `0010`, its own `pre-migration-0009-20260910T215025137216Z.sqlite3`, integrity
  ok) fixed it.
* The second run-now job (`01M26MTDZCXP3ZR99EWDN53AT4`) completed, 21:50:43Z → 22:09:57Z. Its output
  shows the `systemd-run --user --scope … -p MemoryHigh=22G -p MemoryMax=24G -p MemorySwapMax=0`
  command line and FreeWeight's two JSON lines. FreeWeight run `01M26MTEM1SGTMWVB3PR6EXY8F` is
  `completed` on FreeWeight's own `/runs/<id>` page, every test completed.
* `freeweight.service` was restarted from the console afterwards; it had been running since 03:12
  on code older than its now-migrated database.

### 4.3 Criterion 3 — an IdeaPress prompt overridden, run, marked `user_override`, deleted

* Project `01M26M2QJQD5VK73X476GVB1CJ` ("W9 prompt-override demo"), planned into three units.
* The override of `stages.draft.write` (its system text asking for short sentences) written from
  the console to `~/.config/ideapress/prompts/stages.draft.write.json`, override
  `sha256:0981fc58…`, the diff shown. IdeaPress restarted from the console; its health reported
  "Overridden: stages.draft.write."
* The first draft (U-01) failed `MODEL_NOT_CONFIGURED`: IdeaPress's default draft binding,
  `ollama/gemma4:12b`, is no longer installed. That failure left U-01 in `drafting`, and running it
  again is refused ("cannot move from 'drafting' to 'drafting'").
* Rebinding the draft stage took three tries. The console's Settings writer was refused (§5 item
  5b). IdeaPress's own `PUT /settings` stored a row that nothing reads (§5 item 5c); it was set back
  to the default value. The binding that worked went into IdeaPress's `config.toml` through the
  console's `to_file` path; that file did not exist before. IdeaPress was restarted.
* The draft on U-02 (task `01M26NZSCYWAKMMQKVRMNMQZW8`, 22:11:07Z → 22:16:29Z) completed. Attempts:
  `stages.draft.write 1.0.0` **`user_override`**, `stages.audit_fast.review 1.1.0` `pack`,
  `stages.critique.judge 1.0.0` `pack`. `ideapress unit show … U-02 --provenance` prints
  `prompt stages.draft.write 1.0.0 sha256:0981fc58…  (user_override)`.
* The override deleted from the console. The demo's `config.toml` and the empty directories it
  created were removed, and IdeaPress was restarted. Its health lists no override, and the draft
  binding is back to `ollama/gemma4:12b`.

### 4.4 Criterion 2 — the memory cap fired, the banner, acknowledged, in history

* **§2.3 run exactly as written did not fire the cap.** Ollama 0.32.13 served `gemma4:12b-it-q8_0`
  at 131,072 tokens — llama-server's `--fit` placed 12,067 MiB of model and 2,528 MiB of context on
  the GPU, 7 %/93 % CPU/GPU — and answered "Hello! How…". No kill line, no alert. The largest
  installed model is 13.8 GB, so no request to this Ollama drives `ollama.service` past its 24 G.
* **What was fired instead:** the throwaway console's `host.ollama_unit` pointed at
  `wr-gym-memcap-demo.service` (scratch configuration only), then `systemd-run --user
  --unit=wr-gym-memcap-demo --collect -p MemoryMax=64M -p MemorySwapMax=0 python3 -c
  "bytearray(512 MiB)"`. The kernel's `oom-kill:constraint=CONSTRAINT_MEMCG … task_memcg=…/app.slice/wr-gym-memcap-demo.service`
  line is stamped 22:27:52.224Z; the user manager logged "The kernel OOM killer killed some
  processes in this unit … Failed with result 'oom-kill'".
* Alert `01M26PYN718M2695GQ73PX2V7F` opened at 22:27:58.467Z, **6.2 s after the kill line**, and
  the Overview page carried the banner "memory cap fired · wr-gym-memcap-demo.service" with the
  journal line (screenshot at 22:27:59Z). Acknowledged at 22:28:23.950Z by `loopback`: closed, the
  active list empty, `/alerts/history` showing `opened` and `acknowledged`. Checked again after
  more than one further evaluator pass: nothing reopened, still two history rows.
* So the alert path — a real cgroup cap, a real kernel kill, both real journals, the evaluator, the
  banner, acknowledgement, history — is shown end to end. **Ollama's own cap was not fired.**

### 4.5 Not demonstrated live

* The GGUF drop-in appearing after a refresh (§4.1).
* `self_restore` — the console on this machine is not `weightroom.service`, so the job is refused
  by design; the hand-off, the helper and its failure path are covered by tests only.
* `app_down`, `gpu_thermal`, `budget_ceiling` and `breaker_open` against live conditions — their
  firing and clearing fixtures only.
* FreeWeight's Prompts page and an override run with `--allow-prompt-override`.

## 5. For the operator

1. **Nothing pushed or tagged.** WeightRoom `870cec5`, `afc877e`, `43883bb`, `925bbcb` and this
   handoff's docs commit; IdeaPress `35ea090`; FreeWeight `945ae54`.
2. **No version bump.** `wr-gym` stays `0.7.0`; the kickoff's `0.9.0` is superseded.
3. **Your databases were migrated.** IdeaPress `0010` → `0011` at 14:29 PDT by an `ideapress` CLI
   call during Gate C (`~/.local/share/ideapress/backups/pre-migration-0010-20260910T212908731100Z.sqlite3`);
   FreeWeight `0009` → `0010` during §4.2 (both backups named there). `ideapress.service` was
   restarted three times and `freeweight.service` once; LoadCoach and PromptCadence were not
   touched. Until its first restart, IdeaPress answered task reads with `500` ("'Attempt' object
   has no attribute 'prompt_source'"): the running process imported the new `stage_reports.py`
   lazily on top of its old ORM models. **A unit runs its repository's editable install — restart
   it after a commit changes that repository.**
4. **Left on the machine:** `smollm2:135m` in Ollama (in both catalogs, with one FreeWeight run);
   IdeaPress project "W9 prompt-override demo" (U-01 stuck in `drafting`, U-02 committed, U-03
   planned); the LoadCoach manual backup; an IdeaPress settings row `models.stages.draft =
   "ollama/gemma4:12b"` (the default's value; nothing reads it). **Removed:** the override, the
   IdeaPress `config.toml` and directories the demo created, the transient unit (collected), the
   throwaway console. **After the interview (§6):** the LoadCoach manual backup was removed;
   `~/.config/ideapress/config.toml` now binds `models.stages.draft = "ollama/qwen3.5:9b-q8_0"`
   (validated with `ideapress config validate --file`, IdeaPress restarted); the settings row
   stays — WeightRoomGym's guard refuses IdeaPress's `settings` table by design (ADR-0124: the
   application's `PUT /settings` is the audited path) and IdeaPress offers no way to clear a row,
   so row WI1 clears it.
5. **Found, not fixed** — for W10 or a follow-up row:
   a. `MEMORY_SAFETY.md` §2.3's request no longer fires the cap on Ollama 0.32.13 (§4.4). The
      recipe needs replacing — a capped transient unit proves the kernel and journal half; proving
      `ollama.service`'s own cap now needs a model larger than the cap.
   b. **The console cannot change an IdeaPress runtime setting.** IdeaPress's `PUT /settings` takes
      `{"values": {…}}` and its `GET` answers `runtime_changeable`/`overrides`; the console sends
      and reads LoadCoach's and PromptCadence's flat shape (`settings`), so every IdeaPress runtime
      key is refused from the Settings page ("Request body failed validation").
   c. IdeaPress stores runtime setting rows that nothing in IdeaPress applies.
   d. An IdeaPress stage that fails before its first attempt (`MODEL_NOT_CONFIGURED`) leaves the
      unit in `drafting`, and the stage cannot be run on it again.
   e. IdeaPress's default draft binding (`ollama/gemma4:12b`) is not installed on this machine.
   f. A catalog pull does not refresh FreeWeight and LoadCoach; the model appears only after
      `model_refresh`. The pull job could enqueue one on success.
   g. `memory_cap` watches only the Ollama unit and the four application units — not the capped
      scopes the console itself launches for `freeweight_suite_run`.
   h. FreeWeight's JSON lines reach the job's output only at exit (stdout block-buffered through
      the pipe), so the run id is not visible while the run is going.
   i. FreeWeight's app-doc mirrors have been stale since WA1 (pre-existing).

## 6. Open for later rows, and the operator's decisions (interviewed 2026-09-10)

* **`MEMORY_SAFETY.md` §2.3 is rewritten to fire a capped transient unit** (`systemd-run --user
  -p MemoryMax=64M -p MemorySwapMax=0` allocating past it), as §4.4 did: it proves the kernel kill,
  the journal and the alert path; `ollama.service`'s own cap is trusted from its unit file rather
  than fired. The document is shared (mirrored into FreeWeight, LoadCoach, IdeaPress and
  PromptCadence), so the rewrite rides W10's documentation pass.
* **IdeaPress conforms to the suite's runtime-settings shape** rather than the console learning a
  per-application one: `PUT /settings` takes the flat object LoadCoach and PromptCadence take,
  `GET` answers their document, and stored rows are applied with ADR-0100's precedence. With the
  unit left in `drafting` by a stage that fails before its first attempt (§5 item 5d), and the
  leftover row (§5 item 4), this is **new row WI1, before W10, Opus 5 · high**.
* **IdeaPress's draft stage on the reference machine uses `ollama/qwen3.5:9b-q8_0`** (§5 item 5e),
  written to `~/.config/ideapress/config.toml` — done.
* **Cleanup:** the IdeaPress settings row and the LoadCoach manual backup to be removed (the backup
  is; the row waits for WI1, §5 item 4); `smollm2:135m` and the IdeaPress demo project stay.
* **The console runs as `weightroom.service` at W10** — `wr-gym units sync`, started as the unit
  (still not enabled at boot, `roadmap/weightroom-work.md` §4) — and ADR-0136's restore is proven
  live there.
* **W10 also takes W9's small follow-ups:** a successful `catalog_pull` enqueues `model_refresh`
  (§5 item 5f); `memory_cap` watches the scopes the console launches for `freeweight_suite_run`
  (5g); child processes run with `PYTHONUNBUFFERED=1` (5h); FreeWeight's app-doc mirrors re-synced
  (5i). Beside those, W10's own: the OpenAPI snapshot picks up the jobs, schedules, alerts and
  prompts routes.
