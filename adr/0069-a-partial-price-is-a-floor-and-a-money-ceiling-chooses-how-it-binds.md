# ADR-0069 — A partial price accumulates as a floor, and a money ceiling chooses whether an unknown counts against it

**Status:** Accepted (2026-09-02)
**Amends, reversing one rule:** LoadLedger spec §11 contract 2 as first written ("an unpriced debit
leaves every money balance untouched"), and the matching line in
[gold-standards §2](../standards/gold-standards.md). Nothing in an earlier ADR is reversed.
**Relates to:** [ADR-0016](0016-unavailable-is-not-zero.md) (rule 6: a statistic over incomplete
samples is reported with its sample count), [ADR-0030](0030-model-cost-and-pricing.md) (rule 1,
store usage and derive cost; §"A partial sum is never presented as a total"),
[ADR-0047](0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md) §3 (two
ceilings; money binds priced usage).
**Source:** LoadLedger Phase 1 (row B2) handoff §5 items 5 and 7, and the operator's decision on
them.

## Context

`baseaicore.estimate_cost` prices each of the four token classes separately and refuses a total
if any class is unsupported: a call that used an unknown number of cached tokens has an unknown
cost, and a total that quietly omitted that class would understate the call while looking
complete (ADR-0030). `TokenUsage.total_tokens` applies the same rule to the token count.

Both real ModelRack adapters — Ollama and OpenAI-compatible — deliberately leave the two cache
classes `UNSUPPORTED`, because their wire protocols report no cache-aware billing and inventing a
zero is what ADR-0016 forbids. The consequence, measured on 2026-09-02 while reviewing the B2
handoff, is that **nothing a real adapter emits today can be priced to a total**: usage of 1 000
input and 500 output tokens against a complete price list yields a `CostEstimate` whose `input_cost`
and `output_cost` are real money and whose `total` is `UNSUPPORTED`, with two reasons naming the
cache classes. The same usage with the cache classes stated as zero prices to 0.0105 USD.

Nobody had noticed because no component in the suite calls `estimate_cost` yet. The first
consumer that prices real usage is PromptCadence Phase 5, and under LoadLedger's contract 2 as
first written — an unpriced debit leaves every money balance untouched — every remote debit it
made would add nothing to any money balance. Money ceilings would never bind, and the historical
estimator would have nothing priced to learn from. Token ceilings would bind only because
LoadLedger already sums the classes a provider did report and counts the debits it could not fully
count (`unmetered_debit_count`).

The operator's requirement, stated when this was raised: an exact figure is not needed; some
providers will never report everything; knowing that spend is in the ballpark of a budget is worth
far more than a blank. And for some budgets the limit is hard, and it is better to stop short of
it than to learn afterwards that it was crossed. Which of those two applies is the operator's
choice, not the package's.

## Decision

1. **A money balance accumulates the priced components of every debit in its scope.** For a debit
   whose estimate totalled, that is the total. For a debit whose estimate did not total, it is the
   sum of the components that were priced — input and output cost for a response whose cache
   classes were unreported — and nothing for the rest. A debit with no estimate at all (a local
   model, `cost=None`) adds nothing, as before. The sum is exact integer nanos in the estimate's
   currency, and currencies are still never summed across (ADR-0030 rule 3).

2. **The figure is a floor whenever anything in scope was not fully priced, and the verdict says
   so.** Every money verdict carries three counts: `unpriced_debit_count` (debits that added less
   than their full cost: no estimate, or an estimate that did not total), `untotalled_debit_count`
   (the subset that carried an estimate which did not total), and `unmetered_debit_count` (debits
   that left a token class unreported, making the token balance a floor too). `money_spent` with a
   non-zero `unpriced_debit_count` is a lower bound on spend, and any consumer that renders it
   renders it as one — "at least", never a bare figure. This is ADR-0016 rule 6 applied to money:
   the statistic and the count of what it omits travel together.

3. **On a floor, `exceeded` is certain when true and not certain when false.** A ceiling whose
   floor is above its cap has been crossed; that is not a guess. A ceiling whose floor is under its
   cap may or may not have been crossed. The brake can therefore fire late, by at most the
   unreported portion, and never early. This is the default, `PartialPricing.FLOOR`.

4. **A money ceiling may instead be strict.** `BudgetCeiling.partial_pricing =
   PartialPricing.STRICT` makes the ceiling exceeded whenever `untotalled_debit_count > 0` in its
   window: an amount that cannot be shown to be under the cap is treated as over it. The brake
   fires early and the cap is never crossed. `would_exceed` honours it, so a strict ceiling refuses
   the next step at pre-flight, before any spend. A strict ceiling with no money bound is refused
   at construction (`InvalidCeiling`): strictness is a statement about the money bound.

5. **Strict trips on an estimate that did not total, not on a debit that had no estimate.** A local
   model's cost is unsupported by design, and ADR-0047 governs local execution with the token
   ceiling, not the money ceiling. A strict money ceiling on a trajectory that mixes local and
   remote steps must not halt on the first local step; it halts on the first *priced* response the
   provider did not fully report. That is why the untotalled count exists separately from the
   unpriced count.

6. **The choice is configuration.** PromptCadence exposes it as `[budget] partial_pricing =
   "floor" | "strict"`, default `"floor"`, applied to every money ceiling it constructs and
   overridable per request the same way the ceilings themselves are. The ceiling is part of every
   verdict's canonical form, so an approval record shows which rule was in force when the verdict
   was given.

7. **The ledger still decides nothing.** Floor or strict defines what `exceeded` means when the
   sum is incomplete; halting, pausing, or asking for a ceiling raise remains the application's
   policy (ADR-0047, LoadLedger spec §13). The policy lives on the ceiling rather than in the
   application because `would_exceed` must apply it at pre-flight and because verdicts appear in
   approval records, which must show the rule they were judged under.

## Not decided here

What an absent cache class *means* at the adapter — whether a protocol that bills no cache tier
should state the class as zero rather than unsupported — is a ModelRack decision this record does
not make. It matters: under option 1 of the B2 handoff, a floor from an Ollama or plain
OpenAI-compatible response becomes an exact figure, and a strict ceiling stops tripping on every
such response. Until it is decided, a strict money ceiling over today's adapters trips on the
first remote response, which is the correct behaviour under this record and the reason to decide
the adapter question before PromptCadence Phase 5.

## Alternatives considered

**Keep money balances untouched by an unpriced debit** (contract 2 as first written). Rejected.
With today's adapters it makes every remote debit unpriced, so money ceilings never bind and a $5
cap governs nothing. Honest, and useless.

**Change `estimate_cost` or `total_tokens` in BaseAiCore to return a total over the reported
classes.** Rejected. That is a partial sum presented as a total, the defect ADR-0030 names, in the
layer where a wrong move is a data-compatibility break in every repository. The components are
already public on `CostEstimate`; the floor is computed from them without touching the estimator.

**A configured markup on unreported classes**, so the brake fires early by estimate rather than by
halting. Rejected for the ledger: a markup is a guess, it can still be exceeded, and it would put a
number the operator invented into a money record. If pre-flight sizing wants to be conservative,
that is PromptCadence's estimator with a labelled source and a version
([lifecycle §6](../apps/promptcadence/lifecycle.md)), not the ledger.

**Strict as an application-only policy over the counts, with the ceiling unchanged.** Rejected.
`would_exceed` could not apply it, every consumer would re-derive `exceeded`, and the approval
record would not show which rule the verdict was judged under.

**Strict trips on any unpriced debit, local included.** Rejected (decision 5). It would make a
strict money ceiling unusable on any trajectory with a local step, which is every PromptCadence
trajectory.

## Consequences

*Positive.* Money ceilings bind on real adapter output today. An operator with a soft budget sees
"at least $X" and a count of what was not priced; an operator with a hard budget sets one key and
the cap is never crossed. Both are exact integer arithmetic over what was actually reported.

*Positive.* The token and money sides now follow one rule — sum what was reported, count what was
not — and the verdict carries the evidence for both.

*Negative.* A floor can undercount materially on a cache-heavy workload against a provider that
bills cache and does not report it: cache writes are usually billed above the input rate. The
rendering rule ("at least") and the counts are what make that visible; nothing in this record
makes it small.

*Negative.* LoadLedger spec §4, §7, §11, §13 and §18 change, the golden verdict serializations
change (a new field on the ceiling and on the verdict), and gold-standards §2's LoadLedger rule is
rewritten. All before `0.1.0`, so no persisted row is affected.

*Negative.* Until the adapter question above is settled, `partial_pricing = "strict"` halts on the
first remote response from either real adapter. The configuration comment says so.

## Revisit when

* The adapter decision lands and makes floors from the common protocols exact; the strict mode's
  configuration comment should then drop its warning.
* A provider reports a billing unit that is not a token class (ADR-0030 §"Revisit when"); the
  floor's definition would need to name what it omits in that unit too.
* Anyone proposes applying strictness to the token bound. The case for it is a provider that
  returns no usage object at all, and that case is also an estimate that did not total, so the
  money bound already catches it wherever a price applies.
