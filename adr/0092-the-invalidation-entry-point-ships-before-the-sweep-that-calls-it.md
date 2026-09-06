# ADR-0092 — The invalidation entry point ships before the sweep that calls it

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Lifecycle §9.1](../apps/promptcadence/lifecycle.md) — names which of the
three invalidators exist in Phase 8 and what stands in for the others.
**Relates to:** [ADR-0093](0093-materialization-follows-the-terminal-transition.md) (why a missing
revision is survivable at all), [ADR-0030](0030-model-cost-and-pricing.md) (re-costing is a rows
change, not a document edit).
**Source:** Row I1, decision D3.

## Context

Lifecycle §9.1 names three things that invalidate a materialized explanation revision: the
retention sweep, a ledger re-costing under a corrected price record, and a document-schema minor
bump on upgrade. **The retention sweep is Phase 9 work** (development plan; `config.py` says so
too: "the retention sweep arrives later"). So Phase 8 is asked to build the reaction to an event
that nothing yet raises.

The temptation is to build the sweep. It is the thing that makes the feature demonstrable, and it
is half a day's work. It is also how Phase 9's acceptance criteria get quietly pre-empted by a
sweep nobody specified, and a half-swept database — content gone from `turns` but not from
`plans.raw_document`, or scrubbed rows with stale revisions beside them — is worse than an
unswept one.

## Decision

**Phase 8 ships the invalidation *entry point* and the revision bump it performs. It does not ship
the sweep.**

1. **One function, two named causes.** `invalidate(trajectory_id, *, cause)` marks the current
   revision superseded and materializes the next one from the rows as they now stand, recording
   the cause on the new revision. Phase 8 defines the causes `retention_scrub`, `recosting` and
   `schema_upgrade`; only the third has a caller in Phase 8 (the loader, when the composed
   document's schema version has moved).
2. **It is tested by scrubbing the rows directly.** The fixture nulls `turns.content_text`,
   `plans.raw_document` and `turns.tool_calls_json` and leaves `content_hash` in place, calls
   `invalidate(..., cause="retention_scrub")`, and asserts revision *n+1* composes from the
   scrubbed rows, equals `compose_live` over the same rows, and still explains the trajectory —
   every model, tier, tool call, debit and egress verdict present, with content-removed stubs
   where text was. Re-costing is tested the same way, by rewriting the ledger's derived figures
   and asserting the new revision reports them.
3. **The sweep is Phase 9's, and this record is what it will call.** P9 supplies the policy — what
   is scrubbed, when, and in which order across the seven tables — and calls `invalidate` once per
   affected trajectory inside its own transaction discipline. Nothing in Phase 8 decides retention
   policy, and nothing in Phase 8 deletes content.
4. **An explanation that survives a scrub by keeping its own copy has defeated the scrub.** The
   composed document holds no text the rows no longer hold. `plans.raw_document` and
   `turns.tool_calls_json` are model output and are scrubbed exactly as transcript text is; the
   document renders their absence, never a cached copy.

## Alternatives considered

**Build the sweep too.** Makes the feature complete and demonstrable in one row. Rejected: the
sweep is a specified Phase 9 deliverable with its own acceptance criteria, and a sweep written
here would be written without them — retention windows, workspace files, the ordering across
tables and the operator controls are all P9's, and a partial implementation would be discovered by
whoever ran P9 rather than by a test.

**Defer the entry point to Phase 9 as well.** Then Phase 8 ships a materialized cache with no
invalidation path at all, and the equality golden — the thing that makes the cache safe to trust —
would be asserted only for a document that never changes. The entry point is what the golden
exercises; deferring it defers the proof.

**Invalidate by deleting the revision and letting the next read recompose.** Simpler, and it loses
the record of *why*. §9.1 is explicit that a revision records its cause and that superseded
revisions keep their artifacts until an operator prunes them; a delete keeps neither.

## Consequences

* `explanation_revisions` carries a `cause` from the first row: `terminal` for revision 1,
  `retention_scrub` / `recosting` / `schema_upgrade` thereafter. No column is retrofitted in P9.
* P9's sweep is a caller, not a change to this machinery. What it needs from here is exactly:
  call `invalidate` per trajectory after its own row writes commit, in the same process, and treat
  the returned revision number as the receipt.
* A deployment that never scrubs never sees a revision above 1, which is the correct behaviour for
  the default of retention-forever.

## Revisit when

Phase 9 lands the sweep and finds the entry point's shape wrong — most likely because the sweep
wants to invalidate a batch inside one transaction rather than one trajectory at a time.
