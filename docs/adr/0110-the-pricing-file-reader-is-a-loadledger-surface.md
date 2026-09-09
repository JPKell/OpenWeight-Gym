# ADR-0110 — The pricing-file reader is a LoadLedger surface

**Status:** Accepted (2026-09-07)
**Answers:** [ADR-0072](0072-the-model-pricing-record-file.md) §8 and its "Revisit when" first
bullet — *a second consumer needs the reader itself, not only the format*. That trigger fired; the
record ADR-0072 promised names the home.
**Applies:** [ADR-0011](0011-shared-package-boundaries.md) rule 4 (nothing is extracted with fewer
than two real consumers) and its converse — two real consumers is when extraction happens.
**Relates to:** [ADR-0030](0030-model-cost-and-pricing.md) (cost is derived from usage and a
`pricing_hash`), [ADR-0016](0016-unavailable-is-not-zero.md) (an omitted rate is not free),
[ADR-0069](0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md) (what an
estimate that did not total means), [ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md)
(what a shared package may own on a host's behalf).
**Source:** row J1's handoff §8 first finding, row K4, and the operator's decision on it.

## Context

[ADR-0072](0072-the-model-pricing-record-file.md) fixed the price catalogue's *format* and
deliberately left the *reader* where the first consumer had written it. Its §8 said so in as many
words: "the first implementation is `promptcadence.services.pricing`; the second consumer either
imports an equivalent or, if a third appears, the reader graduates into a shared package under its
own row."

The second consumer arrived at row J1. IdeaPress needed a price for every stage attempt, so it
transcribed the module — 315 lines against PromptCadence's 368, differing in the docstrings, in
which application error it raises, and in one container shape (PromptCadence indexes records by
tier because a trajectory may run under any of several; IdeaPress has one configured backend at a
time and holds a flat list). Everything that matters was byte-identical: the rate parsing, the
"not stated" rule, the RFC 3339 reading, the digest-matching asymmetry, the recency resolution, and
every refusal message.

That duplicate is not a style problem. `pricing_hash` is the join between a stored `TokenUsage` and
the price it was costed under — the mechanism ADR-0030's whole derived-cost model rests on. A hash
is a join only if the thing being hashed is the same object everywhere, and ADR-0072 argued exactly
this when it refused to let two applications invent two formats. Two *readers* of one format are
the same hazard one layer down: they would agree today and diverge on the next correction, and the
divergence would surface only as a re-costing across two databases that does not reconcile.

Row J1 recorded the trigger and named `baseaicore` as the likely target. Row K4 is where the
decision was taken.

## Decision

**The reader is `loadledger.pricing`, a module of the package that already owns money in this
suite. Both applications adopt it and keep only their own edge.**

1. **The package owns the format, whole.** `load_pricing_records(path)` parses and validates one
   catalogue and returns `ModelPricing` records in file order; `price_for_model(records, *,
   canonical_id, at)` resolves which one prices a call; `records_claiming(records, *, at)` is the
   worst-case set a pre-flight estimate costs against. Every refusal is `PricingFileError`
   (`LEDGER_PRICING_FILE_INVALID`) naming the file and, where one applies, the record index and the
   field. The messages moved verbatim: they are what an operator repairs a hand-written price list
   from.

2. **`pricing_hash` is still `baseaicore`'s**, computed over the record the reader built. Nothing
   here re-implements it. The point of one reader is that one file produces one set of records,
   and therefore one set of hashes.

3. **The application keeps its edge, and only its edge.** Where the path comes from — a tier's
   `pricing_file`, IdeaPress's `[pricing] file` — is that application's configuration, and how a
   missing or broken file is *reported* is that application's vocabulary: each catches
   `PricingFileError` and re-raises its own `ConfigurationError`, so a broken price list is still
   the startup refusal ADR-0072 §7 requires, in the words that application's operator knows.

4. **Functions over a sequence, not a catalogue class.** The two consumers hold two different
   containers by necessity, so a class in the package would be a name for a tuple and would force
   one of them to wrap. Each application keeps its own small `PricingCatalog` — the tier map, the
   flat list — with `from_settings` and one delegating method each.

5. **The module is not exported from `loadledger/__init__.py`.** It opens files, and the package
   root's standing promise is that importing it does no I/O. This is the rule `loadledger.sql`
   already follows, for the same kind of reason.

6. **The adoption is proved by the tests that were already there.** Both applications' existing
   pricing tests pass unchanged, and the package carries a golden case asserting that the moved
   reader produces the same `pricing_hash` values both applications' own loaders produced on the
   same file before adoption. Ships as `loadledger 0.3.0`, `>=0.3,<0.4` in both applications.

## Why LoadLedger

**Because it already owns the neighbouring facts.** LoadLedger stores `TokenUsage` and
`pricing_hash` on every entry (spec §7), decides what an untotalled estimate means to a ceiling
(ADR-0069), and counts unpriced, untotalled and unmetered debits as first-class honesty. The reader
produces exactly the object those counts are about. A price list that states no cache-read rate,
read here, becomes a floor there — one package, one story about what "not priced" means.

**Because the alternatives cost more.**

*`baseaicore`* — row J1's own suggestion, and ADR-0072 §8's first candidate. Rejected: it would
need its no-I/O rule relaxed by a further ADR, and that rule is not decoration. `baseaicore` is
imported by all fourteen components; a filesystem read inside it is a filesystem read every
consumer inherits, and the domain foundation's guarantee that it touches nothing is worth more than
one import saved. ADR-0072 named the relaxation as a *precondition*, not a preference.

*A new package* (`pricebook`, or similar). Rejected on ADR-0011's `aisuite-common` reasoning
inverted: a package whose entire job is to parse one 40-line JSON format, with one dependency and
two consumers, is a repository, a CI matrix, a version series and a release approval for ~250 lines
that have a natural home. ADR-0011 rejected `LoadCoachClient` for wrapping eight HTTP calls; this
would be smaller.

*Leave the two copies and record why.* The row's other permitted outcome. Rejected on the
`pricing_hash` argument above, which is ADR-0072's own argument for centralising the format,
applied to the reader. The copies agree today; the failure mode is a correction applied to one.

*Extend `setspec`.* It already absorbed the prompt tooling at ADR-0028 for a comparable reason.
Rejected: SetSpec is the contracts layer, and a price catalogue is not a payload crossing an
application boundary — it is a local file an operator maintains. The record it produces is
`baseaicore`'s type, not a versioned wire model.

## Consequences

* **One reader, one hash.** The precondition ADR-0030's re-derivation has been assuming is now
  mechanical rather than a coincidence maintained by transcription.
* **LoadLedger's "no pricing" non-goal narrows and is restated.** The package still never invents,
  converts or extrapolates a rate — it now reads the rates an operator wrote down. Spec §3 says so
  explicitly, so that a later reader does not mistake the module for a pricing service.
* **A third mounting-shaped question is avoided.** Nothing about this touches tables, migrations or
  ADR-0050; the module is pure parse-and-resolve over a path it is handed.
* **The applications get smaller.** ~250 duplicated lines leave each of them, and each keeps a
  wrapper of about sixty: `from_settings`, one delegating lookup, and the error translation.
* **A release ordering appears.** Both applications now floor on `loadledger>=0.3,<0.4`, so their
  hash-verified CI locks cannot be recompiled until `loadledger 0.3.0` is on PyPI. That sequence —
  publish the package, then recompile the two locks — is the operator's, and is the same one row
  I4 followed for `toolyard 0.1.1`.
* **The format is now versioned with a package.** Changing what an absent rate means changes every
  historical `pricing_hash`, which ADR-0072 already said needs a superseding ADR; it now also needs
  a LoadLedger minor and two adoptions.

## Revisit when

* **A third consumer holds a third container shape** — then the catalogue type declined in decision
  4 has two votes against one, and the package should ship it (LoadLedger spec §21 carries this).
* **A price list must be acquired rather than read** — generated on a schedule, or fetched. That
  reopens ADR-0072 §7 first, and only then this record: acquisition is not a parser's job, and a
  module that grew one would have taken the responsibility ADR-0030 assigns to applications.
* **`baseaicore` relaxes its no-I/O rule for some other reason.** If the domain foundation ever
  gains a filesystem, the balance in "Why LoadLedger" changes and the reader's home is worth asking
  again — though a mature reader with two consumers should probably not move for tidiness alone.
