# ADR-0105 — A shipped `usage` object keeps `null` on two of its five classes until `/api/v2`

**Status:** Accepted (2026-09-07)
**Superseded by:** [ADR-0112](0112-the-usage-object-spells-unavailable-one-way-inside-api-v1.md) —
the operator reversed this record the same day: `/api/v1` has no consumer yet, so the two fields
move to `"unsupported"` now, inside `/api/v1`, on a one-time exception to ADR-0013 rather than at
a future `/api/v2`.
**Amends:** [ADR-0016](0016-unavailable-is-not-zero.md) rule 4, for exactly two fields of one
released response body — `usage.input_tokens` and `usage.output_tokens` in LoadCoach's `/api/v1`.
Nothing else in the suite gains a `null`, and the rule is unchanged everywhere else.
**Relates to:** [ADR-0013](0013-api-versioning.md) (additive-only inside a major version, which is
what forces this), [ADR-0009](0009-setspec-schema-strategy.md) rule 5 (the same prohibition for
SetSpec writers — untouched here, because `usage` is an application response body and not a
SetSpec payload), [ADR-0070](0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
(the suite's only carve-out on when a zero is legitimate),
[LoadCoach API §4](../apps/loadcoach/api.md).
**Source:** Row C6's handoff §3(a), which found the divergence, declined to fix it inside a row
scoped to something else, and wrote "**It should become a small ADR**"; and the 2026-09-07 ADR gap
review, findings 1.1 and 2.2.

## Context

LoadCoach renders one `usage` object with five token classes, in two places that must agree —
`ExecutionOutcome.as_json` (`services/execution.py:540-556`) and the job document
(`services/queue.py:1416-1430`). Three of the five are rendered the way
[ADR-0016](0016-unavailable-is-not-zero.md) rule 4 requires:

```python
"cache_write_tokens": self.cache_write_tokens if self.cache_write_tokens is not None
                      else "unsupported",
```

The other two are not:

```python
"input_tokens": self.input_tokens,          # int | None  →  a JSON null
"output_tokens": self.output_tokens,
```

Both are fed by `_count` (`services/execution.py:632-634`), whose docstring says it returns `None`
— "never `0`" — when a class was not reported. So a consumer reads one object in which `null` on
two keys and `"unsupported"` on three mean the identical thing, and neither means zero.

The two spellings have a history rather than a rationale. `input_tokens` and `output_tokens` shipped
in `loadcoach 1.0.0`, before [ADR-0070](0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
made the four-class distinction load-bearing; the cache and thinking classes were added afterwards,
to the rule as it now stands. Nobody chose the mixture.

**The obvious repair is forbidden.** Changing `input_tokens` from `integer | null` to
`integer | string` is a type change on a field of a released `1.0` response, which is exactly what
[ADR-0013](0013-api-versioning.md) makes a **major** change: inside a major version changes are
additive only, and a breaking change creates `/api/v2` with `/api/v1` served and deprecated. A
second API major for two field spellings is disproportionate, and `loadcoach 1.0.0` is on PyPI
serving `null` to whatever already reads it. This is the same wall ADR-0102 met from the other
side, and it is answered the same way: name the divergence rather than break the contract.

## Decision

**Inside `/api/v1`, `usage.input_tokens` and `usage.output_tokens` keep `null` for an unreported
count. `cache_write_tokens`, `cache_read_tokens` and `thinking_tokens` keep `"unsupported"`. The
divergence is deliberate, it is named here and nowhere resolved by a quiet fix, and it ends at
`/api/v2`, where all five classes use one spelling.**

1. **`null` on those two keys means unavailable — never zero.** It is ADR-0016's meaning under
   ADR-0016's forbidden spelling. A consumer that reads `null` and totals it as `0`, or writes it
   into a ledger as a measured count, has the same defect ADR-0016 exists to prevent, and gets it
   from a field whose spelling did not warn it.
2. **`0` on any of the five means a real count of nothing.** That is the carve-out
   [ADR-0070](0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md) rule 1
   makes and the only one in the suite: a token class the provider's *protocol* cannot bill is
   zero, because the adapter knows the class could never have been charged. A class the protocol
   could bill and the response did not report stays unavailable. Everywhere else in the suite, an
   unavailable measurement is still `UNSUPPORTED` and never a zero.
3. **Neither spelling is a number.** `null` and `"unsupported"` are both excluded from arithmetic
   and from aggregation. A consumer's cost, throughput or ledger arithmetic must refuse a total
   that would need either, which is what `TokenUsage`'s own refusal already enforces below the
   wire.
4. **The three newer classes do not move to `null` for consistency.** Consistency is bought at
   `/api/v2` by moving the two, not by dragging three correct fields onto a spelling ADR-0016
   forbids.
5. **`/api/v2`, whenever LoadCoach next needs one, renders all five as `"unsupported"`.** There is
   no removal deadline, because there is no v2 planned; this record is the note that says what v2
   owes.
6. **No new producer copies this.** The exemption is for two fields of one released body. Any
   application adding a token-count field — in a body, an event frame or a payload — writes
   `"unsupported"`, and a reviewer citing this record for a new field has misread it.

## Alternatives considered

* **Fix it: render `"unsupported"` on all five.** The correct end state, and one line each. Refused
  here because it changes a released field's type: a strictly-typed consumer that models
  `input_tokens` as `int | None` starts failing on a *patch* release, and ADR-0013's whole purpose
  is that this cannot happen inside a major. It is what `/api/v2` does.
* **Add two new fields beside them** — `input_tokens_state`, or an `input_tokens_unsupported`
  boolean — so the additive rule is satisfied and the fact becomes readable. Refused: it puts three
  spellings of one idea in one object instead of two, and every consumer would have to read both
  halves to learn what one key already tells it. The cure is worse than the divergence.
* **Coerce the two to `0` when unreported**, making them always integers. Refused, and it is the
  worst option available: it is precisely the fabricated measurement ADR-0016 was written to
  forbid, and it would silently corrupt every ledger downstream of a provider that does not report
  prompt tokens.
* **Stand up `/api/v2` now.** Standards-compliant and it ends the divergence immediately. Refused
  as disproportionate for the same reason ADR-0102 refused it: a second router, a deprecation
  window and two documents, to respell two fields that already carry the right meaning to a
  consumer told what they mean.
* **Say nothing and leave it as a known wart.** What has happened for four releases. Refused
  because the cost falls on a reader who has no way to learn the rule: `CLAUDE.md` and ADR-0016
  both state the prohibition unqualified, so the tree and the records disagree and the record loses.

## Consequences

* A consumer of LoadCoach's `/api/v1` must treat `null` on those two keys exactly as it treats
  `"unsupported"` on the other three. Both of the suite's own consumers already do — IdeaPress and
  PromptCadence parse the counts as optional and never total an absent one — so this record makes
  an existing behaviour a contract rather than changing one.
* `usage` stays honest at the cost of being ugly. That trade is the same one ADR-0102 took for
  FreeWeight's `items`, and for the same reason: a published contract is worth more than a tidy
  one.
* [LoadCoach API §4](../apps/loadcoach/api.md)'s `usage` bullet describes one spelling for all the
  classes and does not mention the two that render `null`. It owes one sentence, in the workspace
  document and in LoadCoach's byte-identical mirror of it; that edit is a scheduled row's, not this
  record's, because the two copies must move together.
* `CLAUDE.md`'s "`Unsupported` is not zero … never `None` or `0` (ADR-0016)" is now qualified twice
  — by ADR-0070 for zeros and by this record for two `null`s — and both qualifications are in the
  ADR set where a reader can find them from ADR-0016's own header.
* Nothing crosses a SetSpec boundary here. `usage` is an application response body; ADR-0009 rule 5
  binds SetSpec writers and is untouched, so no payload version moves and no golden changes.

## Revisit when

LoadCoach needs an `/api/v2` for any reason — that is when the two fields move to `"unsupported"`
and this record is discharged. Revisit sooner if a consumer is found reading `usage` arithmetically
without the guard, which would make the divergence a live defect rather than a named one, or if a
third spelling appears in any `usage` object anywhere in the suite.
