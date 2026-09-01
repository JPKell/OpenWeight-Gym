# ADR-0042 — A deterministic check may not be a restatement of its requirement

**Status:** Accepted (2026-09-01).
**Extends:** [IdeaPress Workflows §3](../apps/ideapress/workflows.md),
[IdeaPress Spec §11](../apps/ideapress/spec.md).
**Relates to:** [ADR-0039](0039-audit-gated-blocking-requirements.md) (a model's silence must not
settle a blocking gate), [ADR-0043](0043-grounding-is-verified-not-assumed.md), risk T1.

## Context

ADR-0039 established the asymmetry the commit gate rests on: a requirement with deterministic
checks is settled by Python, and a model's opinion cannot overturn a passing check. That asymmetry
is correct and is not in question here. What M8 found is what it costs when the check itself is
worthless.

The requirement compiler emits `must_contain_any` / `must_contain_all` / `must_not_contain` checks
from the requirement it just wrote. On a real brief it produced, for a requirement reading *"Every
claim must be grounded in usage figures, named programme types, and the specific services that have
no other local provider"*:

```
checks: contains any of: 'usage figures', 'named programme types',
        'the specific services that have no other local provider'
```

The needles are phrases lifted from the requirement's own sentence. A unit satisfies that check by
**quoting the requirement**, which is what the model did — three occurrences of "usage figures" in
one 294-word unit, and a sentence in another reading *"The economic cost of the specific services
that have no other local provider is realized in…"*, a noun phrase welded in where it does not fit.

The gate then behaved exactly as ADR-0039 says it must, with a result nobody wants. Unit U-05's
own critique read:

> *"The section fails the blocking requirement R-006 by not grounding cost claims in specific data
> and contradicts itself regarding service exclusivity."*

and the unit committed, reporting `2/2 requirements satisfied, 1 by a deterministic check`. Python
owned control flow, a model did not overturn a check, and the system confidently committed work its
own reviewer called materially deficient — because the check was measuring a substring where the
requirement was about a property.

This is the same error the M8 run made in its own security detector, which searched rendered pages
for `onerror=alert` and flagged correctly escaped output: **a check whose text appears in the thing
it checks cannot distinguish compliance from quotation.**

It is worse than having no check. A requirement with no check is *labelled* — "guaranteed by model
review, not a deterministic check" — and a reader knows what they have. This one was labelled
`deterministic_check`, which is a stronger claim than the audit makes and was false.

## Decision

**A compiled check whose needle appears in its own requirement's text is refused at compile time.**

1. `_build_checks` drops any string-kind check (`must_contain_any`, `must_contain_all`,
   `must_not_contain`) whose value occurs in the requirement's `text`, compared case-insensitively
   after whitespace normalisation.
2. A requirement left with no surviving check is **honestly check-less**: it routes to the audit
   under ADR-0039 and carries ADR-0039's label. That is the mechanism that exists for a requirement
   Python cannot settle, and it is the correct destination.
3. The drop is recorded — `requirements.check_dropped` with the needle and the reason — so a
   compiler prompt that starts producing them is visible rather than silently degrading every
   requirement to audit-gated.
4. This does **not** weaken ADR-0039's asymmetry. A check that survives still settles its
   requirement and a model still cannot overturn it. The change is to which checks exist, not to
   what a check means.

## Consequences

* More requirements become audit-gated, which is the honest classification and makes ADR-0043's
  measurement obligation (attestation reliability) matter more, not less.
* A requirement phrased so its own words are the evidence — "must mention X" — loses its check.
  That is correct: "mentions the string X" and "discusses X" are different claims, and only the
  second is what the author meant.
* The compiler prompt should be revised to ask for checks that are *independent* of the
  requirement's phrasing (a named unit, a date format, a word count). That is a prompt version
  bump, not a code change, and is the follow-on work.
* Coverage reports will show fewer `deterministic_check` decisions and more `audit`. A drop in that
  ratio after this ADR is expected and is not a regression.

## Alternatives considered

**Keep the checks and let a `materially_deficient` critique block the commit.** Rejected: it makes
a model able to overturn a passing check, which is exactly risk T1 and the thing ADR-0039 exists to
prevent. The problem is the check, not the asymmetry.

**Fuzzy-match instead of refusing** — require the unit to contain the needle in a sentence it did
not lift. Rejected as unimplementable without a model, which returns the decision to a model.

**Do nothing and rely on the audit to catch it.** Rejected on evidence: the audit *did* catch it —
the critique named R-006 — and the passing check overrode it, correctly.
