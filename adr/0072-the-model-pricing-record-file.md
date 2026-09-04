# ADR-0072 — The ModelPricing record file

**Status:** Accepted (2026-09-04)
**Extends, additively:** [ADR-0030](0030-model-cost-and-pricing.md) (cost is derived from usage and
a `pricing_hash`, never stored as a money figure). Nothing in ADR-0030 changes; this record answers
the question it left to whoever needed a price first — *where does a `ModelPricing` come from, on
disk, and what does the file look like*.
**Relates to:** [ADR-0016](0016-unavailable-is-not-zero.md) (an omitted rate is "not stated", never
free), [ADR-0019](0019-python-baseline-and-config-format.md) (config is TOML, data is JSON),
[ADR-0008](0008-canonical-model-identity.md) and [ADR-0024](0024-canonical-id-and-model-references.md)
(what identifies the weights a price applies to),
[ADR-0069](0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md) (what an
estimate that did not total means to a money ceiling),
[ADR-0047](0047-a-tier-is-configuration-and-a-model-never-sizes-its-own-budget.md) §2 (a remote tier
must name a pricing source, and a configuration omitting one is refused at startup).
**Source:** PromptCadence Phase 5 (row F1) handoff §6.4, and the operator's decision on it.

## Context

[ADR-0030](0030-model-cost-and-pricing.md) settled the hard half of cost: a `TokenUsage` and a
`pricing_hash` are the stored facts, money is re-derived from them whenever a price is corrected,
and `baseaicore.estimate_cost(usage, pricing, at=...)` is the one function that derives it. What it
did not settle — because nothing yet needed it — is where the `ModelPricing` on the right of that
call comes from. `baseaicore` defines the type and ships no reader; ModelRack, SweatMeter, LoadCoach
and FreeWeight had all reached 1.0 or their published minors without ever loading one.

PromptCadence Phase 5 is the first consumer. A remote tier names a `pricing_file`, every priced
debit is costed against a record read from it, and every *re-costing* — the thing ADR-0030 exists to
make possible — reads the same file again. So the format stopped being hypothetical and had to be
written down.

**The reason it belongs here rather than in one application's spec** is the `pricing_hash` itself.
ADR-0030 makes that hash the join between a stored usage and the price it was costed under. A hash
is only a join if the thing being hashed is the same object everywhere. Two applications that each
invented a pricing file would produce two `ModelPricing` objects — differing in nothing more than
whether a stated `"0"` meant "free" or "not stated", or whether a missing `effective_from` was
treated as unbounded — and the same `pricing_hash` in two databases would then mean two different
prices. Nobody would notice until someone re-costed history across the two and the totals
disagreed. That is precisely the failure mode ADR-0030's derived-cost model is supposed to remove.

Three properties of the type constrain the file before any taste enters:

* **Money is whole nanos and there is no float anywhere in the arithmetic.** A rate written as a
  JSON number has already been through a double before any reader sees it.
* **A rate that is absent is `UNSUPPORTED`, not zero** (ADR-0016). A price list that states no
  cache-read rate cannot price a call that read from cache; `estimate_cost` returns an untotalled
  estimate, which ADR-0069 then interprets. A file that could not express "not stated" would make
  every gap silently free.
* **A price is an observation, not a property of a model.** The same weights legitimately have
  several prices at once — standard and batch tiers, two regions, a superseded quote and its
  replacement — so the file holds a *set of observations*, and reading it must resolve them rather
  than assume one.

## Decision

**A `ModelPricing` catalogue is a JSON file holding a `records` array, one object per observation,
written field for field, and read by the rules below. Every consumer in the suite reads this
format.**

### 1. The file

JSON, per [ADR-0019](0019-python-baseline-and-config-format.md) — a price list is data, not
configuration, even though a configuration key names its path. One top-level object with one
required key, `records`, an array. An empty array is legitimate and loads to nothing: a file that
states no prices prices nothing, and the refusal for that belongs to whatever named the file.

```json
{
  "records": [
    {
      "provider_kind": "openai_compatible",
      "provider_model_name": "gpt-4o",
      "artifact_digest": null,
      "source": "provider_published",
      "observed_at": "2026-09-01T00:00:00Z",
      "effective_from": null,
      "effective_until": null,
      "price_tier": "standard",
      "region": null,
      "rates": {
        "currency": "USD",
        "input_per_million_tokens": "2.50",
        "output_per_million_tokens": "10.00",
        "cache_write_per_million_tokens": "3.125",
        "cache_read_per_million_tokens": "0.25"
      }
    }
  ]
}
```

Each record is a `baseaicore.ModelPricing` with its `identity` flattened into the three fields that
compose one. Nothing is summarized and nothing is defaulted silently.

### 2. Rates are decimal strings

`"2.50"`, never `2.50`. A JSON number is a float in every parser this suite will meet, and a price
that arrived as a float has already lost the value the whole-nanos arithmetic exists to protect.
Each stated rate goes through `Money.from_decimal(currency, text)`; a JSON number in a rate position
is **refused**, naming the field, rather than coerced.

`rates.currency` is required and every stated rate is in it. A file assembled from two currencies is
refused by `TokenRates` itself.

### 3. An omitted rate is "not stated", and `"0"` is not the same thing

A rate key that is absent or `null` loads as `UNSUPPORTED`. A rate stated as `"0"` loads as a real
zero. The two are different claims — "this price list does not cover that class" and "that class is
free" — and only the second may be summed. Writing `"0"` where the provider simply did not publish a
rate is the fabricated zero [ADR-0016](0016-unavailable-is-not-zero.md) forbids, and it converts a
floor that would have announced itself into a total that is quietly wrong.

### 4. `source` and `observed_at` are required

`source` is a `baseaicore.PricingSource` member; a record with no stated provenance is refused,
because a figure nobody can weigh is worse than no figure. `observed_at` is when *we* learned the
price, RFC 3339 and timezone-aware; a price with no date is a price nobody can tell has gone stale.
`effective_from` and `effective_until` are the provider's own window and are optional — absent means
*not stated*, which is different from unbounded in principle only in that we know we were not told.

### 5. Matching: the digest narrows, and its absence does not

A record matches a call when the `provider_kind` and the `provider_model_name` are equal, and:

* a record **stating** an `artifact_digest` matches only that digest;
* a record **stating none** matches those weights under any digest.

The asymmetry is deliberate and it is the rule most likely to be got backwards. A price list is
almost always written against a provider's product name, which survives a retag; pinning every
record to a digest would make a routine retag silently unpriceable, and unpriceable is refused
rather than free (ADR-0047 §2). Ignoring a digest a record *did* state would do the opposite damage
— pricing one set of weights at another's rates — so a stated digest binds.

### 6. Resolution: claim the instant, then most recently observed

Among the records matching a call, discard those whose stated window does not claim the instant
being priced. Of what remains, the record with the latest `observed_at` wins. Extrapolating a price
beyond a window it was quoted for is guessing; preferring the newest observation is how a corrected
price supersedes the one it corrects without anything being deleted.

Where the model that will answer is **not yet known** — a pre-flight estimate, before a routing
backend has chosen — a consumer costs the estimate against *every* record claiming the instant and
takes the **largest** total, treating an estimate that could not be totalled as the largest of all.
The only estimate that cannot under-state a budget is the worst case, and under-stating is the
failure that matters: an over-stated estimate refuses a step that would have fitted and says which
cap refused it, while an under-stated one crosses the cap silently.

### 7. Read once, at startup, from disk, and never over the network

A consumer loads its catalogue when it starts and refuses to start if a named file is missing,
unreadable, not JSON, or holds a record these rules cannot turn into a `ModelPricing` — naming the
file, the record index and the field. A price list discovered to be broken halfway through a run
leaves real spend that nobody can cost. Nothing fetches a price list; a stale file is an operator's
problem, and a price that changed under a running process without anybody deciding so is worse.

### 8. Where a reader lives

`baseaicore` continues to ship the *types* and no reader, because a reader is I/O and `baseaicore`
imports stdlib only and touches no filesystem. The first implementation is
`promptcadence.services.pricing`; the second consumer either imports an equivalent or, if a third
appears, the reader graduates into a shared package under its own row. What this ADR fixes is the
**format and the rules**, which is what the `pricing_hash` join actually depends on — not the
module that parses it.

## Alternatives considered

**Leave it in PromptCadence's spec §12** and let the next consumer adopt or diverge. Cheapest, and
it was the state this ADR replaces. Rejected because divergence here is silent: the two formats
would agree on almost everything, differ on the "not stated" question, and produce a `pricing_hash`
collision that only surfaces as a re-costing that does not reconcile. The cost of writing this now
is one document; the cost of finding it later is an audit of two databases.

**TOML, matching every other configuration file in the suite.** Rejected by
[ADR-0019](0019-python-baseline-and-config-format.md) on its own terms — a price catalogue is a
list of observations that a tool may generate, not settings a person tunes — and by the practical
point that a TOML array-of-tables of this shape is markedly harder to emit correctly from a script
than JSON is.

**Rates as integer nanos-per-million-tokens**, sidestepping decimal parsing entirely. It is exact
and it is unreadable: `2500000000` for $2.50 per million, hand-maintained, is a transcription error
waiting to happen, and the class of error it invites is off-by-a-factor-of-ten in a budget. The
decimal string is exact *and* checkable by eye, and `Money.from_decimal` is already the suite's
one conversion.

**A price per model rather than a set of observations** — one record per `(provider, name)`, latest
wins by file order. Simpler to read and it cannot express what providers actually do: batch and
standard tiers concurrently, regional variation, and a price change with a stated effective date
that has not arrived yet. A format that cannot hold tomorrow's price forces an operator to edit the
file at midnight.

**Fetch price lists from the provider.** Rejected on the suite's standing egress posture and on
determinism: re-costing history must reproduce the same figure, which a file guarantees and a
fetch does not.

## Consequences

* **The `pricing_hash` join is sound across applications.** Two components reading the same file
  produce equal `ModelPricing` objects and therefore equal hashes, which is the precondition
  ADR-0030's re-derivation has been assuming.
* **A remote tier's configuration gains a real meaning.** ADR-0047 §2's "a remote tier must name a
  pricing source" was until now a non-empty-string check; it is now a check that the source exists,
  parses, and states rates in a currency the ceilings cap.
* **Unpriceable stays visible.** A model no record covers produces no estimate at all, which flows
  into ADR-0069's floor accounting as an unpriced debit rather than as a zero.
* **Two files may disagree and both be right.** Nothing here makes catalogues authoritative or
  unique; an operator may point two tiers at two files, and the record that priced a call is
  identified by its hash, not by which file it came from.
* **The cost is a format nobody may quietly change.** Adding a field is additive and safe; changing
  what an absent rate means, or how the digest matches, changes every historical `pricing_hash` and
  needs a superseding ADR.

## Revisit when

* **A second consumer needs the reader itself**, not only the format — at which point the parser
  moves into a shared package (most naturally `baseaicore` if the no-I/O rule is relaxed for it by
  its own ADR, otherwise a small package of its own) and this record gains an amendment naming it.
* **A provider prices something these four token classes cannot express** — per-request fees,
  per-image or per-second billing, or a tiered rate that changes with volume. `TokenRates` would
  need extending first, and this file follows it.
* **A price list needs to be machine-generated on a schedule**, which would reopen §7's
  read-once-at-startup rule and require an explicit refresh with its own provenance.
