# ADR-0078 — A shipped response field is superseded beside its replacement, never reshaped under it

**Status:** Accepted (2026-09-05)
**Extends:** [LoadCoach API §4](../apps/loadcoach/api.md) (the transcript and the tool wire),
[ADR-0013](0013-api-versioning.md) (additive within `/api/v1`).
**Relates to:** [ADR-0075](0075-a-request-carrying-tools-requires-tool-use-of-every-candidate.md)
(the request side of the tool wire),
[ADR-0041](0041-caller-schemas-do-not-travel-through-a-router.md) (a caller's schema is
carried, not validated),
[API and Contract Standards §4](../standards/api-and-contract-standards.md) (compatibility rules).
**Source:** Row H2, decision 2 of its kickoff §0.2; the defect is
[`docs/history/G2_HANDOFF.md`](../history/G2_HANDOFF.md) §7 and the open item is its §8.

## Context

LoadCoach 1.0 ships `output.tool_calls` as a **stream rendering**: one entry per provider delta,
carrying `call_index`, `id`, `name` and `arguments_fragment`, so a call whose arguments arrived in
three chunks is three entries. The request side, added at G2, takes **assembled** calls: one entry
per call, with `arguments` as an object or a string. `api.md` §4 documents the asymmetry and states
the grouping rule a caller must apply to turn one into the other — group by `id`, or by
`call_index` where the provider sent none, and concatenate `arguments_fragment` in arrival order.

The asymmetry has now cost what asymmetries cost. G2 built the first caller of the grouping rule —
PromptCadence's LoadCoach client — and got it wrong against a real model, which is the defect its
§7 records. The rule is documented, correct and easy to misread, and every future caller has to
implement it before it can replay a transcript that contains a tool call.

The obvious fix is to make `output.tool_calls` carry assembled calls. It is also a breaking change
to a field shipped in a `1.0` response, inside a minor release, which
[ADR-0013](0013-api-versioning.md) does not permit and which the suite has not done to any caller so
far. So the question this record answers is not "is the fragment shape a mistake" — it is — but
what a minor release is allowed to do about a shipped mistake.

## Decision

**The assembled shape is added beside the fragments, the fragment field is documented as
superseded with the version that removes it, and nothing about the shipped field changes in 1.1.**

1. **`output.tool_calls` is unchanged in 1.1.** Same name, same fragment entries, same order, same
   semantics. A 1.0 caller upgrading to a 1.1 server sees no difference, which is what "additive
   within `/api/v1`" means.
2. **`output.tool_calls_assembled` is added**, carrying one entry per call — `id`, `name`,
   `arguments` — in the same shape the request body already accepts. Round-tripping a response into
   a following turn is then a copy, not a computation.
3. **The grouping happens once, in LoadCoach**, from the same deltas that build the fragment list,
   so the rule `api.md` §4 documents has exactly one implementation and it is the server's.
4. **`output.tool_calls` is marked superseded in `api.md`, with the version that removes it named:
   LoadCoach `2.0`.** A superseded field is documented, supported and tested for as long as it
   exists; "superseded" is a statement about which field a new caller should read, not a warning
   that this one is about to stop working.
5. **Callers inside the suite move to the assembled field**, each in its own row and its own
   release — PromptCadence at its next touch, IdeaPress at H3 if it reads the field at all. Nothing
   in this row changes another application (row H2's stop rules), so the migration is recorded here
   and executed there.
6. **The rule generalizes.** Any shipped response field this suite gets wrong is replaced by
   addition, marked superseded beside its replacement, and removed only in a major. A field is
   never quietly reshaped under a caller inside a minor, however plainly wrong its shape is.

## Alternatives considered

**Collapse `output.tool_calls` to the assembled shape in 1.1.** The smallest diff, the cleanest
result, and every caller that has not shipped yet would prefer it. Rejected: it breaks a `1.0`
response field inside a minor, and the breakage is the worst kind — the field is still present,
still a list, still full of plausible objects, so a caller does not fail, it silently reads one
concatenated call where it used to read three fragments. A break that raises is survivable; a break
that returns different data quietly is not.

**Ship `/api/v2` with the corrected shape.** Honest, and it is what a major exists for. Rejected as
disproportionate: a new API major for one field's shape obliges every caller to migrate every
endpoint, and the suite has exactly one field's worth of reason to do it. The removal at `2.0`
remains available when there is a majority of a major's worth of change.

**Leave the asymmetry and fix the documentation harder.** The status quo, and `api.md` §4 is already
explicit. Rejected on evidence: the rule was documented, the first implementer read it, and the
result was still wrong against a real model. A contract that is correct only when every caller
reimplements a grouping algorithm has put its own invariant in the callers' hands.

**Add a query parameter or header selecting the shape.** Rejected: two shapes behind one field name
is worse than two field names, because a response can no longer be understood without knowing what
was asked for, and every stored transcript becomes ambiguous about which shape it holds.

**Emit only the assembled field and drop the fragments from the stream.** Rejected on a real use: a
caller rendering a tool call as it arrives needs the deltas, which is why the field has its shape.
Streaming callers keep it; replaying callers get the assembled one.

## Consequences

* `output` grows a field, and a response carrying tool calls carries them twice — once as deltas,
  once assembled. That is the cost, it is bounded by the size of a tool call, and it buys the
  deletion of a caller-side algorithm nobody got right the first time.
* `api.md` §4's grouping rule stops being a caller instruction and becomes an explanation of how the
  two fields relate.
* The suite acquires a documented removal event at LoadCoach `2.0`, which is the first entry on a
  major's agenda rather than a surprise found when one is planned.
* Applications inside the suite are split across two shapes until each migrates. Each migration is a
  named row, and the superseded field keeps working throughout, so no application is ever forced to
  move on another's schedule.

## Revisit when

A second shipped field needs the same treatment before `2.0` arrives. One superseded field is a
correction; a growing list of them is evidence that the response shape needs a version of its own,
and at that point the `/api/v2` this record declined becomes the cheaper answer.
