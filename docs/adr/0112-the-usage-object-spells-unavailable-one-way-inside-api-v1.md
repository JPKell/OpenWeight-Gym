# ADR-0112 — The `usage` object spells "unavailable" one way, inside `/api/v1`

**Status:** Accepted (2026-09-07)
**Supersedes:** [ADR-0105](0105-a-shipped-usage-object-keeps-null-until-api-v2.md) in full. `null`
on `usage.input_tokens` and `usage.output_tokens` is gone; both render `"unsupported"`, the same
as `cache_write_tokens`, `cache_read_tokens` and `thinking_tokens`, effective `loadcoach 1.1.3`.
**Amends:** [ADR-0016](0016-unavailable-is-not-zero.md) rule 4 no longer carries an exception —
the rule now holds for all five token classes, with no qualification left in its header.
**Relates to:** [ADR-0013](0013-api-versioning.md) (the additive-only rule this record breaks, on
an explicit one-time exception recorded here, not weakened for anything after it),
[ADR-0070](0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md) (`0`
still means the protocol could not have billed the class; unchanged),
[LoadCoach API §4](../apps/loadcoach/api.md).
**Source:** the operator's decision on 2026-09-07, reversing this morning's ADR-0105 the same
day, on the finding that `/api/v1` has no consumer that would break.

## Context

ADR-0105, written this morning, named a real divergence — `input_tokens` and `output_tokens`
render JSON `null` for an unreported count while `cache_write_tokens`, `cache_read_tokens` and
`thinking_tokens` render the string `"unsupported"` for the identical condition — and declined to
close it, because closing it changes a response field's type inside `/api/v1`, which
[ADR-0013](0013-api-versioning.md) reserves for a major version. That reasoning holds in general.
It does not hold today: this afternoon the operator confirmed that nobody consumes LoadCoach's API
yet. IdeaPress and PromptCadence are the only two integrations that exist, both are worked on
inside this same workspace, and §3 of this record checks both directly rather than assuming it.
Reserving a whole `/api/v2` — a second router, a deprecation window, two documents — to protect a
consumer that is not there is the disproportion ADR-0105 itself named as the objection to the
opposite mistake.

## Decision

**Inside `/api/v1`, `usage.input_tokens` and `usage.output_tokens` render the string
`"unsupported"` for an unreported count, exactly like the other three classes, from
`loadcoach 1.1.3`.**

1. **All five token classes now share one spelling.** `0` means the provider's protocol reported
   that nothing was billed to that class (ADR-0070's carve-out, unchanged). `"unsupported"` means
   the class was never reported and is not a number — excluded from arithmetic and from
   aggregation, the same as it always was for the other three. There is no third spelling left in
   any `usage` object.
2. **This is a one-time exception to ADR-0013, not a reinterpretation of it.** The additive-only
   rule inside a major version is exactly as strict after this record as before it: a type change
   on a released `1.x` field is still a breaking change and still requires `/api/v2` as the default
   path. What makes today different is not the rule — it is a fact about this specific field,
   declared once by the operator, on the record: **`/api/v1` has no consumer outside this
   workspace, and both of the workspace's own consumers are checked in §3 below rather than
   assumed.** A future breaking change to any other `/api/v1` field cites this record for nothing;
   it still owes `/api/v2` or an equally explicit exception argued on its own facts.
3. **A consumer's obligation, stated plainly:** treat `"unsupported"` on any of the five classes —
   `input_tokens`, `output_tokens`, `cache_write_tokens`, `cache_read_tokens`, `thinking_tokens` —
   as unavailable. Never total it, never coerce it to `0`, never write it into a ledger as a
   measured count. A strictly-typed client that modeled `input_tokens` as `int | None` now fails
   loudly on the string, which is preferred to the silent risk `null` carried: a `None`-tolerant
   parser that happened to treat absence as "skip this in the sum" was one refactor away from
   `value or 0`.
4. **Storage is unaffected.** The `jobs` and `attempts` tables keep `input_tokens`/`output_tokens`
   as nullable integer columns; `NULL` is still how "not measured" is stored (ADR-0016 rule 3, this
   record does not touch it). Only the wire representation moves.
5. **`docs/openapi.json` moves and is regenerated**, and the committed contract test proves the
   new document is exactly what this record describes — nothing more.

## Alternatives considered

* **Leave ADR-0105 as accepted and wait for `/api/v2`.** What stood this morning. Rejected this
  afternoon on the operator's own reversal: a second API major, a deprecation window and two
  documents, to protect a consumer surface that does not exist, is the disproportion ADR-0105
  itself used to reject standing up `/api/v2` for the opposite reason.
* **Add the two new field names beside the old ones** (`input_tokens_state` or similar) instead of
  changing the existing fields. ADR-0105 already rejected this for putting three spellings of one
  idea in the object; nothing about today's facts changes that argument, so it is rejected again
  for the same reason.
* **Coerce the two fields to `0` when unreported.** Still the fabricated measurement ADR-0016
  exists to forbid; still the worst option available, unaffected by who consumes the surface.

## Consequences

* [ADR-0105](0105-a-shipped-usage-object-keeps-null-until-api-v2.md) is superseded in full; its
  header carries the notice, and this record is what a reader of ADR-0016's own "Amended by" line
  now finds in its place.
* [LoadCoach API §4](../apps/loadcoach/api.md)'s `usage` bullet drops the `null`-exception sentence
  and states one rule for all five classes; the workspace copy and LoadCoach's mirror move
  together, byte-identical.
* Every render site inside LoadCoach — `ExecutionOutcome.as_json`, the job document, the stream's
  terminal `result` frame (which renders through the same `as_json`), and the CLI's `--json` output
  (which prints the same document) — changes together, because they all go through the two
  functions this record names, not five independent call sites.
* `docs/openapi.json` is regenerated; the byte-for-byte snapshot test is the proof that what
  shipped is what this record says and nothing else moved.
* This record does **not** reopen ADR-0013 for any other field. The next `/api/v1` type change
  still needs `/api/v2` unless it can make the same declaration this one makes, on its own facts,
  in its own ADR.

## Revisit when

Never, in spirit — this is the end state ADR-0105 said `/api/v2` would eventually reach, reached
early on an explicit exception instead. Revisit only if a consumer is later found that this record
did not know about and that breaks on the string, which would mean §3's check was wrong rather than
that the decision was.
