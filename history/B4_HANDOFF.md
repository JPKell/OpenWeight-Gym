# B4 Handoff — PromptCadence Phase 1

**Row:** B4 of `docs/roadmap/outstanding-work.md` §1. **Repository:** `/home/jpk/ai/suite/PromptCadence`.
**Result:** Phase 1 complete. Gate green, both acceptance criteria demonstrated, tree clean on `main`,
nothing tagged, no remote pushed.

---

## 1. Gate results

**Interpreter:** Python 3.13.15, venv at `PromptCadence/.venv` (`python3.13 -m venv .venv` — no
`python3.12` is installed on this machine; `python3.14` is also present but 3.13 was chosen as the
closer match to the CI matrix, per CLAUDE.md's standing note that local venvs here run 3.13/3.14).

Exact invocation and result of each gate command, run from `/home/jpk/ai/suite/PromptCadence` with
`.venv` active:

```text
$ ruff format --check .
31 files already formatted

$ ruff check .
All checks passed!

$ mypy src tests
Success: no issues found in 28 source files

$ lint-imports
Contracts: 5 kept, 0 broken.

$ pytest -m "not live and not performance" --cov --cov-report=term-missing
88 passed, 2 skipped in 1.26s
Required test coverage of 85.0% reached. Total coverage: 93.49%
```

The 2 skipped tests are the PostgreSQL migration/parity tests (`@pytest.mark.integration`,
`tests/integration/test_migrations.py`) — this machine has no local PostgreSQL server, so
`weightsdb.testing.temporary_postgres()` skips them. They are written and will run for real in the
CI `db-matrix` job, which sets `WEIGHTSDB_REQUIRE_POSTGRES=1` against a real Postgres service
container. `integration` was not a registered pytest marker in the sibling repos' `pyproject.toml`
(LoadCoach, IdeaPress) despite their CI's `db-matrix` job filtering on `-m integration` — I
registered it here and marked the two PostgreSQL-only tests, since an unregistered marker with no
tests carrying it would make that CI job select zero tests. Worth checking whether the siblings'
`db-matrix` jobs are actually green today; if not, this is the same fix applied there too.

Per-file coverage is in the table above; every file is at or above the 85% floor except
`cli/commands/db.py` (76%, the restore-confirmation and JSON-output branches of `backup`/`restore`
are exercised but not every combination) and `services/diagnostics.py` (86%, the
`database_url is None` defensive branch — unreachable in practice, `StorageSettings` always fills
it in). Neither pulls the *package* average below 85%; both are candidates for more tests in C4 if
useful, not blockers now.

## 2. Acceptance-criteria demonstration

Development plan Phase 1's two acceptance criteria, both demonstrated from a machine with **no
config file, no LoadCoach and no network** (only loopback), fresh `XDG_*` directories:

**AC1 — `promptcadence serve` on a clean machine with zero configuration; health degraded, not
dead.**

```text
$ promptcadence config path
config file  /tmp/pc-demo/config/promptcadence/config.toml
config dir   /tmp/pc-demo/config/promptcadence
data dir     /tmp/pc-demo/data/promptcadence
state dir    /tmp/pc-demo/state/promptcadence
$ ls /tmp/pc-demo/config/promptcadence/config.toml
ls: cannot access ...: No such file or directory        # confirmed: no config file exists

$ promptcadence serve --port 18770 &
$ curl -s -H "Host: 127.0.0.1" http://127.0.0.1:18770/api/v1/health
```

```json
{
  "status": "degraded",
  "application": "promptcadence",
  "version": "0.1.0",
  "checked_at": "2026-09-03T00:19:34.849Z",
  "components": [
    {
      "name": "database",
      "status": "ok",
      "detail": "sqlite, schema at head.",
      "data": { "revision": "0001", "dialect": "sqlite" },
      "checked_at": "2026-09-03T00:19:34.849Z"
    },
    {
      "name": "loadcoach",
      "status": "degraded",
      "detail": "unreachable: [Errno 111] Connection refused",
      "data": {},
      "checked_at": "2026-09-03T00:19:34.849Z"
    }
  ]
}
```

```text
$ curl -s -o /dev/null -w "%{http_code}\n" -H "Host: 127.0.0.1" http://127.0.0.1:18770/api/v1/health
200
```

A person watching this sees: the process starts with no `promptcadence.toml` anywhere, no
LoadCoach reachable and no network beyond loopback; the database is created and migrated to head on
first use; `/health` answers **200**, `status: "degraded"` — never `500`, never a crash, never
`unavailable`. `promptcadence health` and `promptcadence doctor` (CLI, no server needed) report the
identical two components by construction, since both the route and the CLI command call the same
underlying health builders.

**AC2 — Gate clean; CI green.** Gate results above. CI cannot be demonstrated as "green" until the
GitHub remote exists and a push runs the workflow (see §7) — the workflow file is committed and
mirrors LoadCoach's own, job for job, adjusted for PromptCadence's dependency set.

## 3. Configuration surface (spec §12) as implemented

All twelve sections plus the two dynamic ones (`[tiers.<name>]`, `[budget.projects.<name>]`) are
implemented in `src/promptcadence/config.py`, precedence file → `PROMPTCADENCE_*` environment →
CLI flag, tracked per leaf field (`loaded.sources["section.field"]`).

**Startup refusals implemented**, each a `ConfigurationError` (or its `InsecureBindingError`
subclass) naming the offending field:

| Refusal | Message (abbreviated) | Where |
|---|---|---|
| `server.host = "0.0.0.0"` without `allow_lan_exposure` | *"server.host is '0.0.0.0' ... exposing the service beyond this machine must be a deliberate act"* | `config.py::_validate_security` |
| Non-loopback `server.host` without `server.allowed_hosts` | *"server.host is not loopback but server.allowed_hosts is empty ... DNS rebinding"* | `config.py::_validate_security` |
| A tier with no `task_profile` | *"tiers.\<name\> has no task_profile ... exactly one LoadCoach task profile (ADR-0047 §1)"* | `config.py::_validate_tiers` |
| A remote tier with no `max_data_classification` | *"tiers.\<name\> is remote but sets no max_data_classification (ADR-0047 §2)"* | `config.py::_validate_tiers` |
| A remote tier with no `pricing_file` | *"tiers.\<name\> is remote but sets no pricing_file. Unpriced egress is refused, not free (ADR-0047 §3)"* | `config.py::_validate_tiers` |
| An unknown `DataClassification` value (e.g. `"top_secret"`) | Plain pydantic type-validation failure on the `DataClassification` enum field, translated to `ConfigurationError` naming the field | `config.py::_translate_validation_error` |
| A `[budget.projects.<name>]` binding neither `money_ceiling` nor `token_ceiling` | *"budget.projects.\<name\> sets neither money_ceiling nor token_ceiling ... set at least one"* | `config.py::_validate_project_budgets` |
| `loadcoach.api_key_env` **and** `loadcoach.api_key_file` both set | *"loadcoach.api_key_env and loadcoach.api_key_file are both set; a credential has exactly one source"* | `LoadCoachSettings._exclusive_credential` |
| Non-loopback bind with no active API token | *"server.host is not loopback but no active API token exists ... `promptcadence token create`"* | `bootstrap.py::bootstrap` (needs the database — see below) |
| `approval.mode = "manual"` with no active `approve`-scoped token | *"approval.mode is 'manual' but no active, approve-scoped API token exists ... a mode nobody can satisfy is a configuration error (ADR-0049 rule 2)"* | `bootstrap.py::bootstrap` (needs the database) |

The last two need the `api_tokens` table and therefore run in `bootstrap.py`, once the database is
ready — the same split LoadCoach's own Phase 1 uses (`config.py` for what needs no I/O,
`bootstrap.py` for what needs the database). `promptcadence token create` itself is **not** built
yet — it is spec §7.2 CLI surface belonging to Phase 7 (`token create|list|revoke` alongside
`approvals`/`approve`/`deny`) — so today the only way to satisfy either refusal is to insert an
`api_tokens` row directly; both refusal paths are exercised in
`tests/e2e/test_server_boot.py::test_non_loopback_bind_without_an_active_token_refused` and
`::test_manual_approval_without_an_approve_scoped_token_refused`.

**One resolved ambiguity, worth the next reader's attention:** spec §12's example TOML ships four
default tiers, including two remote ones (`remote_cheap`, `remote_frontier`) with
`pricing_file = ""`. Read literally as *active* Python defaults, that configuration would be
refused by the pricing-source rule above on every zero-configuration start, which would break AC1
outright. Resolved by shipping only the two local tiers (`local_fast`, `local_large`) as the active
`Settings.tiers` default; the two remote tiers are documented, **commented out**, in
`EXAMPLE_CONFIG_TOML` (what `promptcadence config init` writes), with a note to fill in
`pricing_file` before uncommenting — consistent with ADR-0047's own "remote tiers are unusable
until an operator supplies pricing" framing. `policy.default_tier` and `policy.escalation_order`
defaults were adjusted to match (`local_fast`, `["local_fast", "local_large"]`) so the shipped
defaults stay internally consistent. Flagging this explicitly in case C4 (or a future ADR) wants a
different resolution — e.g. shipping all four but only *validating* a tier once it appears in
`policy.escalation_order`.

Two further, smaller judgment calls made while implementing "the full spec §12 surface":

* **`Money`.** `baseaicore.Money` is a plain frozen dataclass with its own `__post_init__`
  validation; rather than gamble on pydantic v2's stdlib-dataclass interop for something the
  gate must pass reliably, `config.py` defines its own `MoneyAmount` pydantic model
  (`{currency, nanos}`, currency normalized through `baseaicore.normalize_currency`) for every
  money-shaped field (`budget.default_money_ceiling`, `budget.daily_money_ceiling`,
  `approval.gate_step_cost`, `budget.projects.*.money_ceiling`). Convert to `baseaicore.Money` at
  the point of use (Phase 5's budget code) with `Money(currency=amount.currency, nanos=amount.nanos)`.
* **`[budget.projects.<name>]` binding neither ceiling is refused** was documented only as an
  inline TOML comment in spec §12's example (*"a project binding neither is refused"*), not listed
  in the section's own opening refusal list. Implemented it anyway as part of "the full spec §12
  surface" — it is unambiguous spec language, just placed unusually.

## 4. `.importlinter` contracts as written

```ini
[importlinter]
root_package = promptcadence
include_external_packages = True

[importlinter:contract:layers]
name = PromptCadence internal layering
type = layers
layers =
    web
    cli
    services
    domain
containers = promptcadence

[importlinter:contract:web-cli-independence]
name = Web and CLI never import each other
type = independence
modules =
    promptcadence.web
    promptcadence.cli

[importlinter:contract:domain-purity]
name = Domain imports no frameworks
type = forbidden
source_modules = promptcadence.domain
forbidden_modules =
    fastapi
    starlette
    sqlalchemy
    typer
    httpx
    jinja2

[importlinter:contract:no-other-applications]
name = PromptCadence must not import other applications
type = forbidden
source_modules = promptcadence
forbidden_modules =
    freeweight
    loadcoach
    ideapress

[importlinter:contract:no-direct-provider-access]
name = PromptCadence reaches a model only through LoadCoach's HTTP API (ADR-0045 rule 2)
type = forbidden
source_modules = promptcadence
forbidden_modules =
    modelrack
    sweatmeter
```

The fifth contract (`no-direct-provider-access`) is beyond the standard three-sibling template —
written now, per the row's own instruction, so no later phase can add either import casually.
`domain/__init__.py` exists purely so the `domain` layer above is a real importable package from
the first commit (Phase 2 populates it; nothing else lives there yet).

## 5. Mirrored documents — `cmp` output

```text
$ cmp docs/apps/promptcadence/spec.md ../docs/apps/promptcadence/spec.md && echo "spec.md OK"
spec.md OK
$ cmp docs/apps/promptcadence/lifecycle.md ../docs/apps/promptcadence/lifecycle.md && echo "lifecycle.md OK"
lifecycle.md OK
$ cmp docs/apps/promptcadence/development-plan.md ../docs/apps/promptcadence/development-plan.md && echo "development-plan.md OK"
development-plan.md OK
```

(Command shown relative to the two repos; run from the workspace root as
`cmp docs/apps/promptcadence/spec.md PromptCadence/docs/apps/promptcadence/spec.md`, etc. — all
three passed with no output difference.)

## 6. Commits made

All on `main`, tree clean, nothing tagged, no remote pushed (the human-owned remote — see §7 —
already exists locally as `origin` but nothing has been pushed to it):

```text
7281432 feat(web,cli): honest degradation, MirrorWall envelopes and the CLI skeleton
8f44665 feat(db): WeightsDB wiring and the Phase 1 migration history
fb73684 feat(config): the full spec §12 configuration surface
fb42b15 chore: repository scaffold, toolchain and mirrored documentation
2d5c994 first commit                                    # pre-existing, human, .gitignore only
```

## 7. Before the next session (C4 — PromptCadence P2)

**Human steps, at minimum** (per outstanding-work §4 and the row's own precondition):

1. **Push `main`.** The GitHub remote `JPKell/PromptCadence` already exists and is configured as
   `origin` (created before this session started — `git remote -v` shows it live and reachable),
   with one prior commit (`2d5c994`, `.gitignore` only). This session added four commits on top of
   it but **did not push** — pushing is a shared/visible action outside this session's authorization.
   Run `git push` from `/home/jpk/ai/suite/PromptCadence`.
2. **Reserve the PyPI name `promptcadence`**, if not already done — not verified in this session.
3. **CI secrets / first push.** Confirm the `ci.yml` workflow goes green on the first push (this
   session's local gate matches every job's command, but the `db-matrix` Postgres job and the
   `security` (`gitleaks`/`pip-audit`) job were never run in CI). If `db-matrix` selects zero tests,
   see the `integration` marker note in §1 — check whether LoadCoach's and IdeaPress's own
   `db-matrix` jobs have the same gap.
4. **Decide the tier-defaults ambiguity in §3** if a different resolution than "ship only local
   tiers, comment out remote ones" is preferred — currently a judgment call, not an ADR.

**For whoever starts C4 (Phase 2 — domain core):**

* Read `docs/apps/promptcadence/development-plan.md` Phase 2 and `docs/apps/promptcadence/lifecycle.md`
  §§3–8 before writing `domain/threads.py`, `domain/tiers.py`, `domain/plan.py`, `domain/intent.py`,
  `domain/deviation.py`, `domain/trajectory.py`, `domain/policy.py` — none of that exists yet
  (`domain/__init__.py` is a placeholder only).
* `domain/tiers.py`'s `Tier`/`TierPolicy` will want to consume `config.py`'s `Tier` pydantic model
  (task_profile, remote, max_data_classification, context_budget_tokens, pricing_file) as its
  input shape — check whether that model should move, be duplicated as a frozen dataclass, or be
  adapted in place; `config.Tier` today is deliberately just parsed+validated configuration, per
  Phase 1's own scope line ("The tier objects are *parsed and validated* here. Nothing resolves,
  routes or executes — that is P2 and later").
* `promptcadence/domain/threads.py` and its store must be built **package-shaped** (no
  PromptCadence vocabulary in the types) per the recorded ThreadRack rejection — the `threads` and
  `turns` tables already exist (migration `0001`) and were deliberately kept generic-shaped for
  exactly this (see `infrastructure/db/models.py` module docstring).
* No table shape surprises found in Phase 1 that Phase 2 will need to un-do — the two
  forward-looking notes from the row (LA0 adapter fields on `turns`, mounting readiness for
  `ledger_entries`/`egress_decisions`) were both applied as specified.
* `cli/commands/config.py`'s `config reference` subcommand (spec §7.2 lists
  `config show|validate|init|path|reference`) was **not** built — matching LoadCoach's own Phase 1
  (`config show|validate|init|path` only; the generated reference document arrives at LoadCoach's
  P9). Not a gap unless a later PromptCadence phase's plan says otherwise.

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
