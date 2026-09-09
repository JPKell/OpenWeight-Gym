# I5 — PromptCadence 1.1.0, runtime settings

**Row:** I5 (Opus 5 · high) of [`roadmap/outstanding-work.md`](../roadmap/outstanding-work.md) §1.
**Ships:** `promptcadence 1.1.0`, prepared on `main` at `a1ffdf4`, **untagged and unpushed**.
**Repositories touched:** `PromptCadence` (8 commits) and `docs` (4 commits). Nothing else.
**Date:** 2026-09-06, with the post-build interview on 2026-09-07. Every judgement call took the
conservative option first, as the kickoff's overnight clause asked; §8 records the four the
operator then reviewed, one of which changed the build.

---

## 1. Gate results

One interpreter throughout: **`/home/jpk/ai/suite/PromptCadence/.venv/bin/python`, Python
3.13.15**. Every gate was run from `/home/jpk/ai/suite/PromptCadence`.

```bash
.venv/bin/ruff format --check .        # 181 files already formatted
.venv/bin/ruff check .                 # All checks passed!
.venv/bin/mypy src tests               # Success: no issues found in 177 source files
.venv/bin/lint-imports                 # Contracts: 5 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                       # 1261 passed, 2 skipped, 10 deselected in 81.90s
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                       # Required test coverage of 85.0% reached.
                                       # Total coverage: 91.66%
```

Per-module coverage for what this row wrote or touched (`coverage report --include=…`):

| Module | Coverage |
|---|---|
| `services/settings.py` | 99 % |
| `web/routes/settings.py` | 100 % |
| `services/runtime.py` | 99 % |
| `cli/commands/config.py` | 93 % |
| `services/config_reference.py` | 91 % |
| `services/planner.py` | 89 % |
| `services/worker.py` | 86 % |

The suite gained 26 tests: `tests/unit/test_runtime_settings.py` (35 cases, the registry and D2's
precedence both ways), `tests/integration/test_runtime_settings_apply.py` (4, the worker),
`tests/e2e/test_settings_surface.py` (16, the API and the page), plus the `config show` pair in
`tests/unit/test_cli.py`, the planner-setter case in `tests/unit/test_planner.py`, and the
registry assertion in `tests/unit/test_config_reference.py`.

## 2. The gates as commits

| Gate | Commit | What landed |
|---|---|---|
| A | `e940a30` | `feat(settings): the runtime-changeable registry, five tuning keys` — `services/settings.py`, `config.env_var_for`, 35 unit tests |
| B | `0baa41a` | `feat(worker): apply the runtime settings at the lease-reap cadence` — the worker's `refresh_runtime_settings`, `Runtime`'s configured/effective split, the controller's `apply_runtime_settings`, the planner's settable budget |
| C | `cca06fe` | `feat(api): GET and PUT /api/v1/settings` — the pair, registered under `/api/v1`; `docs/openapi.json` regenerated; the contract test's negative assertion replaced by the path |
| D | `f8f72ee` | `feat(console): a Settings page that says what cannot change here too` — the page, the nav entry, the template, the form parser |
| E | `9324016` | `feat(cli): config show marks database-sourced values` |
| F | `9f9a8ec` (PromptCadence) + `13dac8e` (docs) | The spec, the plan, ADR-0100, the generated reference's column, and the three repo-local documents |
| — | `1b02560` | `feat(settings): widen the turn caps and describe max_turns_per_step` — the interview's one build change (§8) |
| G | `a1ffdf4` | `chore(release): promptcadence 1.1.0` |

`docs` also carries `de81d47`, the kickoff prompt.

## 3. The three decisions

### D1 — the runtime-changeable set: the kickoff's five, unchanged

`storage.content_retention_hours`, `compaction.threshold`, `execution.step_retries`,
`execution.max_turns_per_step`, `planning.corrective_retries`. Each **inclusion** justified on its
own, because that is the half a reviewer reads first:

* **`storage.content_retention_hours`** — LoadCoach's precedent, and the sweep that consumes it
  already runs from the worker at the same cadence the refresh does, so the value the UI shows and
  the value the sweep uses are one read apart. It is the one genuinely destructive key in the set
  (lowering it deletes text sooner); it is bounded 0–8760 and behind `admin`, and the sweep it
  drives was already running.
* **`compaction.threshold`** — a bounded fraction read per compaction from the shared settings
  object (`loop.py` `LoopController._compact`). Changing it changes when the next compaction
  fires and nothing else; there is no security surface, and a tier's own
  `context_budget_tokens` (which decides how much data a turn may carry) is config-only.
* **`execution.step_retries`** — read per step attempt, inside ADR-0076's envelope, and bounded
  0–25 here (0–10 as first built; widened at the interview, §8). A retry is a repeat of the same
  intent revision, so raising it cannot widen what a step is allowed to do; it can only spend more
  attempts inside a governance envelope that has already been minted.
* **`execution.max_turns_per_step`** — read per turn, bounded 1–200 (1–64 as first built; §8).
  The same argument, plus: the trajectory's own `max_turns`/`max_steps` and the budget ceilings
  still bind, so this key cannot buy a trajectory more than the ceilings allow, only more round
  trips inside them.
* **`planning.corrective_retries`** — read by the planner, bounded 0–5. It changes how many
  corrective drafts an invalid plan may attempt; the validator's rules, the plan's schema and the
  approval that follows are all unchanged. This is the key that forced the membership rule below.

**What the losing option claimed.** A wider set was available and refused: the budget ceilings
(`budget.daily_money_ceiling` and the two defaults), `approval.request_timeout_hours`,
`policy.default_tier`, `execution.max_steps`, `compaction.protected_recent_turns`. The strongest
of them is the ceilings, whose case is real: an operator watching a long run stall against a
ceiling wants to raise it from the console they are already looking at. The answer is that this
application already has that path — a `ceiling_raise` approval request, granted by a principal
holding `approve`, recorded with the approver and the amount (ADR-0049). A settings form would be
a second route to the same money with no `approval_requests` row behind it, and the reason the
first route is shaped as it is would then only apply to whoever did not know about the second.
`policy.default_tier` fails for the same family of reason: pointing the default at a remote tier
is an egress decision. `approval.request_timeout_hours` shortens the window a human has to answer,
which is a governance control, not a knob. `execution.max_steps` and
`compaction.protected_recent_turns` are simply not re-read at a cadence, so they fail the rule
below rather than a security test.

**The membership rule, which is the useful output of this gate.** A key is runtime-changeable only
if the running process re-reads it. Four of the five already did. `planning.corrective_retries` did
not — `Planner` takes the number at construction and caches it — so the choice was to drop the key
or to make the planner able to take a new value. Making it settable is three lines and one test,
and the alternative was a registry entry the process would honour only after a restart nobody was
told to perform. The rule is recorded in ADR-0100 rule 1 and is what the next row should apply
before adding a sixth key.

**The refusals.** Whole sections are config-only — `[server]`, `[loadcoach]`, `[approval]`,
`[budget]`, `[tools]`, `[tiers]`, `[policy]` — rather than a hand-listed set of keys, so a field
added to one of them later is refused by default instead of falling through to "unknown key". Six
individual keys join them from the mixed sections (`storage.database_url`, `storage.auto_migrate`,
`storage.retain_content`, `planning.enabled`, `planning.allow_request_override`,
`planning.reapproval_scope`) plus `logging.include_content`. A body naming one is refused **whole**
— nothing is written, so a request that mixed a valid key with a refused one cannot half-apply.

### D2 — precedence: the standard, not the precedent

Implemented as configuration standards §7 states it: `defaults → file → database → env → CLI`. A
stored row is ignored while the environment pins its key, and the document reports `stored`,
`source` and `shadowed_by` per key so the row is visible rather than dropped.

**What the losing option claimed.** LoadCoach's implementation takes the stored row whenever one
exists, which is simpler (no environment lookup at read time) and arguably matches the intuition
that "the last person to touch it wins". It was refused because it contradicts a published
standard, and because the lie is silent: an operator who pinned `PROMPTCADENCE_COMPACTION__
THRESHOLD` in a systemd unit, and whose colleague then saved a different value in the console,
would have a running process disagreeing with both the unit file and
`promptcadence config show`'s published precedence.

**How the CLI layer is covered without plumbing `sources`.** The kickoff assumed the shadow check
would need `LoadedSettings.sources` carried into the runtime. It does not:
`promptcadence.bootstrap.bootstrap` documents that this application has **no CLI configuration
layer** — `serve` sets `PROMPTCADENCE_SERVER__HOST`/`__PORT` as environment variables and calls
`load_settings()` with no `cli_overrides`, and no other command passes any. So an environment
lookup at read time covers both layers exactly, and `Runtime`'s signature did not change. The
lookup shares one helper with the loader (`config.env_var_for`), so the variable name cannot drift
between "what the loader read" and "what the settings service checks".

### D3 — scopes: LoadCoach's split, and the spec amended to say so

`GET /settings` is `read`; `PUT /settings` and the page's POST are `admin`; the page renders for
`read` without the form (ADR-0094). Spec §14 now reads "settings **changes**, tokens".

**What the losing option claimed.** A literal reading of spec §14 would have made the read `admin`
too, and it has one real argument: the document names every configured tier, every containment
root and every allowlisted host in `config_only`, so a `read` principal learns the deployment's
shape. That was weighed and rejected — the same principal already sees the Tiers page, the Tools
page and `/system/status`, all of which name the same facts, and no value in the document is a
credential (the LoadCoach key is an *environment variable name*, never its value). Making the read
`admin` would have meant a read-only operator could not see what the process is running on while
being able to see everything it did.

## 4. Exit conditions, one by one

| # | Condition | Result |
|---|---|---|
| 1 | Full gate green on a named interpreter, coverage ≥ 85 % | **Met.** Python 3.13.15, §1's five commands, 91.66 % |
| 2 | `PUT` refuses a security key with `403` naming it, an unknown key with `400` naming it and listing the set, a valid key from a non-`admin` principal with `403` | **Met**, tested and demonstrated live: `FORBIDDEN … server.host is security-relevant …`, `details.key = "server.host"`; `VALIDATION_ERROR … execution.max_steps is not runtime-changeable`, `details.runtime_changeable` listing the five; `403` with `details.required = "admin"` for a `read`-scoped token |
| 3 | A `PUT` is applied by the running worker within one reap cadence, proven with an injected clock | **Met.** `tests/integration/test_runtime_settings_apply.py::test_the_running_worker_applies_a_write_within_one_reap_cadence` starts real worker threads on the harness clock, writes the row, advances the clock by `lease_seconds + 1`, and asserts the shared settings object changed |
| 4 | `config show` marks a database-sourced value `(database)`, and prints normally with no database | **Met**, both tested and run by hand: `execution.step_retries 3 (database)`; against a missing database, `execution.step_retries 1 (default)` and **no database file created** |
| 5 | `docs/configuration.md` regenerates with `yes` for exactly the registry's keys; its test passes | **Met.** Five `yes` rows, asserted by count against `RUNTIME_SETTINGS` as well as per key |
| 6 | `docs/openapi.json` contains `/api/v1/settings`, the negative assertion is gone, no other path moved | **Met.** The diff is +60 lines (the two operations) and one line for `info.version` |
| 7 | `cmp` silent for every mirrored document | **Met** for `spec.md`, `lifecycle.md` (untouched) and `development-plan.md` |
| 8 | Both repositories clean, work committed, nothing pushed | **Met.** `git status --short` empty in both; no `git push` was run, not even a dry run |

The development plan's five *demonstrable* criteria were run against a real `promptcadence serve`
on ports 8789/8790 with a scratch data directory (no LoadCoach, health degraded, which is the
documented behaviour). Both servers are stopped and the scratch directory is outside the tree.

## 5. Things this prompt said that turned out not to be true

* **"Check for an existing repository under `infrastructure/db/repositories/`."** There is no such
  directory in PromptCadence at all — unlike LoadCoach and FreeWeight, this application has no
  repository layer; services use `database.write()` and the models directly. The settings writer
  is therefore a `weightsdb.upsert` inside `write_runtime_settings`, not a new repository class,
  which is also the smaller diff.
* **"`LoadedSettings.sources` already names the layer behind every leaf, so honouring the standard
  is a few lines."** True of the *loader*, but `sources` never reaches the running process:
  `Runtime` takes a `Settings`, and `create_app` is documented as a pure function of one. The
  reasoning that replaced it is D2 above — because `serve` passes its flags as environment
  variables, an `os.environ` check at read time is exactly equivalent and needs no signature
  change. The kickoff's version would have plumbed a map through two constructors to get the same
  answer.
* **"`sweep_retention` reads `self.settings.storage.content_retention_hours` directly … this read
  must go through the effective value."** It must, but not by changing that line. The deeper
  problem the kickoff did not name is that `ApprovalService`, the estimator, the tool plant and
  every controller hold the *same* `Settings` object, and `ApprovalService` reads
  `max_turns_per_step` when it mints a step intent — including on the web layer's grant path,
  which is not the worker. Applying effective values to a copy the worker held would have left an
  API-minted intent declaring the configured cap while the loop enforced the stored one. So the
  values are written **in place** onto the one object every handle shares, and `Runtime` keeps the
  configured settings pristine beside it (`self.settings` versus the copy it hands out). That
  split is what makes `configured` and `effective` two facts in the document rather than one.
* **"The reap cadence at `next_reap` (lines 342–357)."** Correct, but the cadence is
  `execution.lease_seconds` (60 s by default), not LoadCoach's one second. A change therefore
  reaches the loop within a minute rather than instantly, which is documented in the spec, the
  page, the CHANGELOG and `troubleshooting.md` rather than left for an operator to discover.
* **Line numbers.** All of them had moved or were approximate: `config.py:769`/`745`,
  `config_reference.py:161`/`43`, `worker.py:339`/`298`/`307`, `models.py:331`,
  `test_openapi_snapshot.py:60`, `security.md:53`, `troubleshooting.md:66–70`. Each was found by
  name without difficulty; none of the descriptions was wrong.
* **"`web/auth.py:139` `require_scope`, `CurrentPrincipal`."** PromptCadence has no
  `CurrentPrincipal` dependency — LoadCoach does. Routes here call `require_scope(request, …)`
  and get the principal back, which is what the new routes do.

## 6. What the operator still has to do

1. `cd /home/jpk/ai/suite/PromptCadence && git push` (7 commits on `main`), and
   `cd /home/jpk/ai/suite/docs && git push` (2 commits).
2. `git tag -a v1.1.0 -m "promptcadence 1.1.0" 1af331e && git push origin v1.1.0`.
3. Approve the release workflow's `pypi` environment and publish `promptcadence 1.1.0`.
4. Nothing else: no migration to run, no configuration change, and no stored value to seed. An
   existing 1.0.x install upgrades with `pip install --upgrade` and a restart.

## 7. For another row

* **Two of these are now scheduled rows** — **I8** (the LoadCoach precedence fix) and **I9** (the
  `settings` CLI verb), added to `roadmap/outstanding-work.md` §1 at the interview. They are kept
  below in full because the row text points back here.
* **LoadCoach's precedence diverges from the standard it publishes.** `loadcoach`'s
  `services/settings.py::read_runtime_settings` takes the stored value whenever a row exists, so a
  database row beats `LOADCOACH_*` in the environment and a `serve --port` flag, while
  `docs/configuration.md` publishes `defaults → file → database → env → CLI`. The fix is the shape
  used here: ignore the stored row when that key's source is `env …` or `cli` (LoadCoach *does*
  have a CLI layer, so it should consult `LoadedSettings.sources` rather than `os.environ`), and
  report the shadowed row in `GET /settings`. **A finding, not a fix — nothing in LoadCoach was
  touched by this row.**
* ~~**`execution.max_turns_per_step` has no `description` in `config.py`.**~~ Folded into 1.1.0
  at the interview (`1b02560`): the field now carries the description, and the generated reference
  renders it.
* **No `promptcadence settings` CLI verb was added**, as the kickoff directed. The API and the
  console cover the surface, and `config show` answers "what is effective, and from where" without
  one. The operator asked for it at the interview: scheduled as **I9**.
* **The registry holds no boolean today.** The page renders numbers only; the boolean branch in
  the form parser is marked `pragma: no cover` rather than tested against a key that does not
  exist. The first boolean key added should delete that pragma and bring a test.

## 8. The interview (2026-09-07)

Four questions, after the build and before the tag.

1. **The registry's UI bounds** — mine, and narrower than the config model's own validation. The
   operator **widened the turn caps**: `execution.max_turns_per_step` 1–64 → **1–200**,
   `execution.step_retries` 0–10 → **0–25**. Reason given: a long agentic step needs the room, and
   the guardrail that matters is elsewhere — the trajectory's own `max_turns`/`max_steps` and the
   budget ceilings still bind, so a wider cap buys round trips *inside* an envelope, never outside
   it. The other three keep the bounds as built. Commit `1b02560`, gates re-run whole.
2. **The budget ceilings stay config-only** — ADR-0100 rule 4 confirmed as written. No change.
3. **`max_turns_per_step`'s missing description** — folded into 1.1.0 rather than deferred, since
   the gates were reopening anyway. Same commit.
4. **The two deferrals became rows** — **I8** (LoadCoach's precedence) and **I9** (the `settings`
   CLI verb). Neither is a change to 1.1.0.

The release path chosen: push, tag, publish — no TestPyPI dry run, as at 1.0.1.
