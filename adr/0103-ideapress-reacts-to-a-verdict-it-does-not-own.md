# ADR-0103 — IdeaPress reacts to a verdict it does not own: a bound ceiling pauses, an undeclared remote ceiling denies

**Status:** Accepted (2026-09-07)
**Extends:** [LoadLedger spec §13](../packages/loadledger/spec.md) ("halting, pausing or re-approving is
the caller's decision"), [Commissioner spec §11](../packages/commissioner/spec.md) contract 2 and
[ADR-0054](0054-commissioner-records-egress-it-does-not-enforce-it.md) (Commissioner records; the
caller enforces).
**Relates to:** [ADR-0030](0030-model-cost-and-pricing.md), [ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md)
(the mounting pattern both adoptions use), [ADR-0069](0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md)
(floor vs strict), [ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md) (defaults
are closed).
**Source:** Row J1 (`docs/history/j1-ideapress-loadledger-commissioner.prompt.md`), decisions D4
and D6.

## Context

IdeaPress adopted `loadledger 0.2.0` and `commissioner 0.1.1` in one row (roadmap §6.1, §6.2). Both
packages are deliberately inert about what happens next: LoadLedger's `debit` reports whether a
ceiling is `exceeded` and does nothing else; Commissioner's `evaluate` renders and records
`APPROVED`/`DENIED` and enforces neither. Both design choices are correct (ADR-0011's boundary rule
— a package that started refusing calls or halting units would have acquired application policy),
but they leave two real questions **IdeaPress itself** must answer, and the answers are
architectural rather than incidental: what does this application *do* when a ceiling binds, and
what does it do when a remote backend has no declared classification ceiling at all?

Both questions arrive at the same funnel: `services/stages.py::record_attempt`, the one place every
stage attempt is recorded (workflows §8) and therefore the one place both a debit and an egress
evaluation happen (row J1 ground truth 2). Answering them there, once, is what keeps "the ledger
decides nothing, the application decides everything" true in fact rather than in a docstring three
call sites disagree about.

## Decision

### 1. A bound `per_output` ceiling pauses the unit (D4)

When `record_attempt`'s debit reports any ceiling `exceeded` **and** the attempt named a unit, and
that unit is in one of the four in-flight states (`drafting`, `validating`, `auditing`,
`revising` — `domain.stage_state.IN_FLIGHT_UNIT_STATES`), the unit moves to `paused` with a reason
naming which ceiling bound. This is the same arrow and the same state a unit already takes when its
output-token budget is exhausted (`services/workspace.py`'s `pause_guidance`): IdeaPress's
established way to stop work a person can unblock, not a new mechanism for money.

A `per_project` (`PER_TAG`, lifetime) ceiling exceeding is recorded on every subsequent verdict but
pauses nothing directly — there is no unit to pause for a `plan` or `project_review` attempt, and a
project-wide cap firing mid-unit is visible on the workspace's project-cost badge (D5) rather than
forced through the per-unit pause path.

A unit not in an in-flight state (`paused` already, `planned`, or `committed`) is left alone. This
is not a gap: a `committed` unit is immutable regardless of budget, and a `paused` unit is already
stopped for whatever reason got there first.

### 2. A remote backend with no declared ceiling is denied, fail closed (D6)

`LoadCoachSettings` and `OpenAICompatibleSettings` each gain an optional
`max_data_classification: str | None`. Ollama carries no such key — it is hard-coded
`remote=False`, matching its existing special case in the deleted `_is_remote` helper. When a
backend's target is remote and this key is unset, `commissioner.EgressTarget.max_data_classification`
is `None`, and the shipped `OrderedClassificationPolicy` denies with `no_ceiling_declared`
(ADR-0054's fail-closed branch) rather than the record being silently absent.

**This is a behaviour change for an existing remote configuration that names no ceiling.** Before
this row, an operator running `openai_compatible` or `loadcoach` with `providers.allow_remote =
true` and no equivalent of this key got a workspace badge that said "leaves this machine" and
nothing else — the call proceeded. From this row, every attempt against that backend is *recorded*
as denied. Commissioner does not enforce (ADR-0054): the call still proceeds exactly as it did
before, because IdeaPress's own enforcement of remote egress is `providers.allow_remote` at startup
(`config.py::_validate_egress`), unchanged by this row. What changes is the durable record — an
operator who runs `ideapress egress list` (or reads the workspace's provenance table, D8) now sees
every one of those attempts as a denial with a name, rather than an approval that was never
evaluated at all. `CHANGELOG.md` and `upgrading.md` name it as an upgrade note: set
`max_data_classification` to keep the record matching what the badge already implied.

### 3. The `setspec` floor rises to admit only what Commissioner requires

`commissioner 0.1.1` pins `setspec>=0.5,<0.7` for `governance.egress_decision` 1.0. IdeaPress's own
floor was `>=0.4,<0.7` (its own surface, `setspec.prompts` + `GeneratorInfo`, needs nothing past
0.4). Left unchanged, IdeaPress could resolve a `setspec` release Commissioner itself refuses to
run against — the same "one repo's floor is another's ceiling" trap row E5 closed for `mirrorwall`.
The floor rises to `>=0.5,<0.7`; the installed resolution (`setspec 0.6.0`) does not move.

## Alternatives considered

**Raise an exception from `record_attempt` on an exceeded ceiling.** Rejected: `record_attempt` is
the provenance funnel every stage body calls unconditionally (workflows §8), including from J2's
files this row must not edit. An exception there would propagate into `unit_loop.py`'s and
`review_loop.py`'s existing exception handling as an *unhandled* failure — `INTERNAL_ERROR` rather
than the structured, resumable `paused` outcome IdeaPress already has a state and a UI for.

**Halt the whole stage run rather than pause one unit.** Rejected: a `per_output` ceiling is scoped
to one unit's own attempts; a project working through five units with one expensive one should not
lose the other four's progress because the ledger, not the application, happened to notice first.
`StageRunner` already tolerates a per-unit pause without stopping the run (the existing
exhausted-output-budget case proves this).

**Default an undeclared ceiling to the installation's own `inference.data_classification`.**
Considered for D6 and rejected on the same grounds ADR-0054 rejected it for Commissioner generally:
it makes every remote call self-approving by construction and guts the record before it is written
— a ceiling equal to the installation's own classification approves *everything* the installation
is configured to send, which is not a ceiling at all.

**Leave the `setspec` floor at `>=0.4,<0.7` and let dependency resolution catch the conflict.**
It would, eventually — `pip` would refuse an environment naming both `commissioner>=0.1.1` and an
older `setspec`. Rejected because the failure would surface as an opaque resolver error at install
time rather than a documented decision at the point IdeaPress's own `pyproject.toml` states its
requirements.

## Consequences

* A unit that crosses its own `per_output` ceiling stops with a reason a person can act on
  (raise the ceiling, or accept the cost and resume) exactly as an exhausted output budget does
  today — one more `kind` a future `pause_guidance` hint could special-case, not a new pause
  mechanism.
* An operator upgrading into this row with an already-remote, already-permitted backend sees new
  `denied` rows appear in the egress ledger on the next attempt, with no change in what actually
  ran. Silence here would have been the wrong default (ADR-0046).
* `commissioner`'s own `setspec` floor is now IdeaPress's floor too; a future package with a
  narrower requirement gets the same treatment rather than a second silent trap.
* Nothing here changes what Commissioner or LoadLedger *decide* — both packages are exactly as
  inert as their specs describe. This record is entirely about the caller's reaction, which is
  where ADR-0054 and LoadLedger spec §13 already said that reaction belongs.

## Revisit when

* A unit-level pause proves too coarse — an operator wants the *stage* to keep drafting other units
  past a per-output ceiling while flagging the one that crossed it without moving its state; that
  is a UI affordance, not a change to this record, unless it needs a state the machine does not
  have.
* A second IdeaPress backend needs a ceiling that is not `max_data_classification` shaped (a
  provider-side quota, say) — that is a new configuration key under the same fail-closed default,
  not a reason to revisit this one.
* Commissioner or LoadLedger grow an opinion about the caller's reaction (a suggested remedy, a
  standard pause taxonomy) — at that point ADR-0011's boundary-violation rule applies to *them*,
  and this record is what such a change would be measured against.
