# ADR-0100 — PromptCadence's runtime-changeable set is five tuning numbers, and the environment still wins

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence spec §7.1](../apps/promptcadence/spec.md) (`GET`/`PUT /settings`, built
at 1.1), [§12](../apps/promptcadence/spec.md) (which keys move at runtime and by which precedence)
and [§14](../apps/promptcadence/spec.md) (the `admin` scope covers settings *changes*).
**Relates to:** [Configuration standards §7](../standards/configuration-standards.md) (the
precedence deviation and the never-editable-from-the-UI rule),
[ADR-0094](0094-the-console-authenticates-as-the-api-does.md) (the page enforces what the API
enforces), [ADR-0049](0049-approval-is-a-mode-with-its-own-scope.md) (a ceiling raise is an
approval with an approver on it),
[ADR-0076](0076-a-step-retry-is-a-repeat-under-the-same-intent.md) (the retry envelope two of
these keys bound),
[ADR-0069](0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md) (why
`budget.partial_pricing` is not a tuning number).
**Source:** Row I5 — the settings pair spec §7.1 promised and the 1.0 build recorded as unbuilt
([I2 §5](../history/I2_HANDOFF.md)). The operator chose to schedule the row rather than strike the
endpoints from the spec.

## Context

Spec §7.1 has listed `GET /settings` and `PUT /settings` since the specification was written.
Nothing defined which keys were runtime-changeable, so 1.0 shipped without them and
`docs/troubleshooting.md` recorded the gap honestly. The `settings` table has existed since
migration `0001` and has never held a row.

The question the row had to answer is not *how* — LoadCoach's registry, its refusals and its
scheduler-cadence application are the precedent, transcribed — but **which keys**. PromptCadence
is the application in this suite that executes model-directed tool calls and sends data to paid
remote providers; a key that moves from a config file to a web form in this application moves
from "an operator edited a file and restarted" to "whatever can reach the console can change it
while work is in flight".

Two smaller questions came with it. Configuration standards §7 puts a database-backed setting
*between* file and environment; LoadCoach's implementation instead takes a stored row whenever one
exists, so a row beats an environment variable and a CLI flag. And spec §14 says `admin` covers
"settings, tokens", while LoadCoach makes the read `read`-scoped and only the write `admin`.

## Decision

**Five tuning numbers move at runtime; everything that decides exposure, egress, credentials,
containment, retention or spend is refused by name; the environment still beats a stored row; and
`admin` is the scope for a settings *change*, not for looking at one.**

1. **The runtime-changeable set is exactly:** `storage.content_retention_hours`,
   `compaction.threshold`, `execution.step_retries`, `execution.max_turns_per_step`,
   `planning.corrective_retries`. Each is a number with no security surface of its own, each is
   bounded by the registry (which may be narrower than the field's own validation — the form must
   not be able to stop the application working), and — the test of membership — **each is re-read
   by the running process**. A key nothing re-reads is not runtime-changeable however plausible
   it reads in a registry, so the planner's cached retry budget became settable rather than the
   key being admitted on a promise the process does not keep.

2. **The registry is one module** (`services/settings.py`), and the API, the console page, the CLI
   and the generated `docs/configuration.md` all read it. The **Runtime-changeable** column of the
   reference is rendered from the registry, so a key added there cannot be documented as `no`.

3. **Security-relevant keys are refused with `403 FORBIDDEN` naming the key**, never a silent
   ignore and never an "unknown key". Whole sections are refused: `[server]`, `[loadcoach]`,
   `[approval]`, `[budget]`, `[tools]`, `[tiers]`, `[policy]`; plus `storage.database_url`,
   `storage.auto_migrate`, `storage.retain_content`, `planning.enabled`,
   `planning.allow_request_override`, `planning.reapproval_scope` and `logging.include_content`.
   A request naming one is refused **whole** — a mixed body writes nothing.

4. **The budget ceilings are config-only, and that is the decision's centre.** This application
   already has one way to raise a ceiling: a `ceiling_raise` approval request, granted by a
   principal holding `approve`, recorded with the approver and the amount (ADR-0049). A settings
   form that could raise `budget.daily_money_ceiling` would be a second path to the same money
   with no `approval_requests` row behind it. Two paths to spend, one of them unrecorded, is not a
   convenience. `budget.partial_pricing` is refused with them: it decides whether a partial price
   is a floor or a refusal (ADR-0069), which is a money-correctness rule, not a knob.

5. **Precedence follows configuration standards §7**: `defaults → file → database → env → CLI`. A
   stored row is ignored while the environment pins its key, and the document says so per key —
   `stored`, `source` and `shadowed_by`, so a row that does nothing is *visible* rather than
   applied in silence or dropped in silence. `promptcadence serve` applies its CLI flags as
   environment variables before the loader runs, so the environment check covers the CLI layer
   too; this application has no separate CLI configuration layer to consult.

6. **`GET /settings` is `read`, `PUT /settings` is `admin`**, and the page renders for `read`
   without the form while its POST refuses anything below `admin` (ADR-0094). Spec §14 is amended
   to read "settings changes, tokens": an operator who may see the console may see what the
   process is running on, and a read-only principal seeing the effective configuration is not a
   privilege escalation — being able to change it is.

7. **The page lists the config-only keys**, named as the operator configured them
   (`tiers.local_fast.remote`, not `tiers.<name>.remote`). A page that showed only what may change
   would leave an operator unable to tell "refused here" from "missing".

## What this refuses

* **A pause or drain switch.** LoadCoach's `queue.paused`/`queue.draining` have no counterpart
  here, and inventing one to complete the symmetry would be a new control with a new state
  machine, not a settings row.
* **Applying a stored value the running process does not re-read.** The alternative is a UI that
  reports a change and a loop that ignores it until a restart nobody was told to perform.
* **Mutating the loaded configuration object in place as the record of what was configured.** The
  composition root keeps the configured settings pristine and hands its handles a copy, so
  `configured` and `effective` remain two different facts. Without that the document could only
  report what it had already applied.
* **Following LoadCoach's precedence.** It contradicts a published standard: an operator who
  pinned a value on the command line, and found a web form quietly overriding it, has been lied to
  by the precedence chain `docs/configuration.md` publishes. LoadCoach's divergence is recorded as
  a finding against LoadCoach, not copied here and not fixed from this row.

## Consequences

* LoadCoach and PromptCadence now resolve a stored setting differently. That is a real
  inconsistency in the suite, and the fix belongs in LoadCoach's next row: its
  `read_runtime_settings` should ignore a stored row whose key `LoadedSettings.sources` reports as
  `env …` or `cli`.
* The `settings` table gains its first rows. No migration and no schema change: the table has
  existed since `0001`, and this release adds none.
* An operator can lower `content_retention_hours` from the console and the very next lease reap
  sweeps to it, which is a real destructive capability behind an `admin` scope. It is LoadCoach's
  precedent, it is bounded (0 to a year), and the sweep it drives was already running.
* A key added to the registry later cannot be added quietly: the reference regenerates, and
  `tests/unit/test_config_reference.py` compares the committed document byte for byte.

## Revisit when

A runtime-changeable key is wanted that is *not* a number — a mode, a list, a host. The registry
carries a `kind` and the form renders booleans, but every refusal above was reasoned about numbers
with no security surface, and a string-valued runtime key deserves its own record rather than a
widened set.
