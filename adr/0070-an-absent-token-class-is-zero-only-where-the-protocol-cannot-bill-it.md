# ADR-0070 — An absent token class is zero only where the protocol cannot bill it

**Status:** Accepted (2026-09-02)
**Resolves:** the question
[ADR-0069](0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md)
§"Not decided here" left open — which layer decides what an absent token class means, and what
it means.
**Amends, additively:** ModelRack spec §11 contract 2 ("every unavailable measurement is
`UNSUPPORTED`, never zero") gains the second half of the rule: a class the protocol cannot bill is
zero, never unavailable. [ADR-0016](0016-unavailable-is-not-zero.md) is applied, not reversed;
[ADR-0030](0030-model-cost-and-pricing.md)'s adapter reconciliation duty now covers cache detail.
**Source:** LoadLedger Phase 1 (row B2) handoff §5 item 7, and the operator's decision on it.

## Context

`baseaicore.TokenUsage` has four disjoint classes — input, output, cache write, cache read — each
defaulting to `UNSUPPORTED`. `estimate_cost` refuses a total if any class is unsupported, and
`total_tokens` does the same for the count. Both real ModelRack adapters leave the two cache
classes `UNSUPPORTED`: Ollama's wire protocol has no cache-aware billing, and the
OpenAI-compatible adapter reads `prompt_tokens` and `completion_tokens` only. Each docstring cites
ADR-0016 for not inventing a zero.

ADR-0069 made the ledger honest about the result — a partially priced debit accumulates as a
floor, and a strict ceiling treats it as exceeding — but the result is still that every response
from a real adapter is labelled a floor, `unmetered_debit_count` is never zero, `total_tokens` is
never a number, and a strict money ceiling trips on the first remote response. For Ollama and for
an OpenAI-compatible server that does no cache accounting, the floor is in fact the exact total;
only the label is wrong.

Two facts settle where the decision belongs. First, ADR-0030 already makes the adapter the only
layer that knows a provider's convention: it reconciles overlapping prompt and cache figures into
the disjoint classes. Whether a protocol can bill a class at all is the same kind of knowledge.
Second, the OpenAI chat-completions protocol *can* express cached input, through
`usage.prompt_tokens_details.cached_tokens`, and the adapter reads none of it today: against a
server that does report it, cached tokens sit inside `prompt_tokens` and are estimated at the full
input rate. That over-estimates, which is the safe direction for a brake, and is still wrong.

Row D3 writes the third adapter (`LlamaCppProvider`). It should be written to a rule, not
retrofitted to one.

## Decision

1. **The rule is per response, not per adapter.** A token class the wire protocol has no way to
   bill is reported as `0`. A class the protocol can express but this response did not carry
   stays `UNSUPPORTED`. A response with no usage object at all reports every class
   `UNSUPPORTED`, as now. Zero is honest exactly where nothing was billed; it is the fabricated
   zero ADR-0016 forbids exactly where something may have been billed and was not reported.

2. **OpenAI-compatible.** When `usage.prompt_tokens_details.cached_tokens` is present, cache read
   is that figure, input is `prompt_tokens` minus it (the disjointness reconciliation ADR-0030
   assigns to the adapter), and cache write is `0`, because the protocol defines no write charge.
   When the details object is absent, the server does no cache accounting and both cache classes
   are `0`. When there is no usage object, every class is `UNSUPPORTED`.

3. **Ollama.** The protocol has no cache billing vocabulary; both cache classes are `0`. Before
   asserting it, a recorded fixture verifies whether `prompt_eval_count` counts only the tokens
   Ollama evaluated when its KV cache reused a prefix. If it does, `input_tokens` for this adapter
   means tokens processed, which is the right number for a token brake and is not the prompt
   length; the adapter's docstring says so. That is documentation, not a design change.

4. **llama.cpp (row D3) is written to this rule from the start.** The adapter states in its
   docstring which classes its native API can bill and what it does with each, and the conformance
   suite checks it like the others.

5. **`FakeProvider` defaults its cache classes to `0`** — it plays a protocol that bills no cache
   tier — and keeps a way to script `UNSUPPORTED` explicitly, so that LoadLedger's and
   PromptCadence's tests can produce both shapes on demand.

6. **The conformance suite gains three usage cases for every adapter:** a recorded response
   without cache detail yields cache classes `0` and an estimate that totals; a response with
   cache detail yields disjoint classes that sum to the provider's prompt figure; a response with
   no usage object yields every class `UNSUPPORTED`.

7. **LoadCoach carries all four classes on the wire.** Its attempts and jobs rows and its job
   document's `usage` gain `cache_write_tokens` and `cache_read_tokens`, `"unsupported"` when
   that is what the adapter reported (ADR-0016 rule 4), additive within `/api/v1`. Without this,
   PromptCadence would rebuild a `TokenUsage` with unsupported cache classes and be back where
   ADR-0069 found it.

8. **Sequencing.** The ModelRack change (row C5) lands before D3; the LoadCoach change (row C6)
   lands before PromptCadence P5 (row F1). Both are recorded in
   [`outstanding-work.md`](../roadmap/outstanding-work.md) §1 and §3.

## Alternatives considered

**Leave every unreported class `UNSUPPORTED`.** Rejected. It labels every real response a floor
when most are exact, makes a strict ceiling unusable, and leaves `total_tokens` permanently
unsupported. Honest about the wrong thing: the adapter does know the protocol bills no cache tier.

**Zero per adapter rather than per response.** Rejected. OpenAI-compatible is a family; a server
that does report cache detail must have it reconciled, not zeroed, or the estimate double-bills
cached input at the full rate.

**Decide it in the price list** — a `ModelPricing` with no cache rates means "treat unreported
cache counts as zero". Rejected. It moves adapter knowledge into a pricing record, and it would
change `estimate_cost`, the layer ADR-0069 chose not to touch.

**A configured markup for unreported classes.** Rejected in ADR-0069, for the same reasons.

## Consequences

*Positive.* Floors from Ollama and from plain OpenAI-compatible servers become exact totals with
zero honesty counts; a strict money ceiling becomes usable; `total_tokens` starts returning a
number for real responses. The latent over-estimate against servers that report cached tokens is
fixed as a side effect.

*Negative.* A ModelRack behaviour change: the reported shape of usage changes for both adapters,
so it ships in a minor release (pre-1.0 rules), the recorded fixtures are re-annotated, and any
test that relied on the fake's cache classes defaulting to `UNSUPPORTED` must script that
explicitly.

*Negative.* A LoadCoach migration and document change, small and additive, on a released 1.0
application. It is the price of PromptCadence reaching models only through LoadCoach (ADR-0045).

*Negative.* A protocol judged wrongly produces a fabricated zero. The per-response rule and the
cache-detail conformance case are the mitigation; the revisit triggers below name the known gap.

## Revisit when

* A provider bills cache writes under the OpenAI-compatible shape without reporting them. Then
  "absent means `0`" is wrong for cache write against that provider, and the adapter needs a
  per-provider override rather than a protocol-level rule.
* Ollama, or llama.cpp's native API, starts reporting cache statistics. The classes it reports
  then follow rule 1's first sentence, not its second.
* A provider bills a unit that is not a token class (ADR-0030 §"Revisit when").
