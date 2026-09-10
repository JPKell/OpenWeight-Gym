# ADR-0135 — A minor that feeds a checked hash is read at its own minor

**Status:** Accepted (2026-09-10)
**Amends:** [ADR-0068](0068-a-post-freeze-minor-is-a-sibling-class.md) (a case its mechanism did
not anticipate) and qualifies, for two payloads,
[API and Contract Standards §7](../standards/api-and-contract-standards.md) rule 2.
**Implements:** [ADR-0074](0074-adapter-enabled-serving-is-a-runtime-profile-field.md) on the wire:
`adapters_registered` reached BaseAiCore's hash and FreeWeight's profiles, but not SetSpec's
payloads or FreeWeight's table.
**Relates to:** [ADR-0084](0084-a-producer-chooses-a-payload-version-by-content.md) (a producer
chooses a version by content), [ADR-0035](0035-application-owned-document-schemas.md) §4
(`freeweight.export` embeds run summaries verbatim),
[ADR-0023](0023-runtime-profile-resolution.md) (the profile and its hash).
**Source:** Row WA1 — the 2026-09-08 suite audit's latent defect. The row's kickoff decided the
fix; one of its decisions did not fit what the code shows, and its own rule is that the ADR comes
first in that case.

## Context

ADR-0074 put `adapters_registered` on `baseaicore.RuntimeProfile`, and `profile_hash` includes it
whenever it is stated. FreeWeight states it — `True` or `False` — for every run on a provider that
can serve adapters (`services.adapters.serving_mode`) and stores the resulting hash. But neither its
`runtime_profiles` table nor SetSpec's frozen `RuntimeProfileFields` carries the field, and
`BenchmarkResultFields` and `BenchmarkRunSummaryFields` recompute `runtime_profile_hash` from the
embedded profile. So exporting such a run fails SetSpec's own hash check.

The kickoff settled the shape of the fix: `1.1` sibling classes per ADR-0068, a FreeWeight
migration, the export on `1.1`. It also decided that "any reader of these payloads — LoadCoach's
evidence import among them — accepts `1.1` unchanged (schema rule 2); a test in the consumer
proves it". Two facts in the code do not fit that decision.

**A `1.0` reader refuses a `1.1` document that states the field.** Checked on `setspec 0.6.0` with
`baseaicore 0.4.2`: `BenchmarkRunSummaryIn` and `BenchmarkResultIn` accept a profile with the field
absent. With it `false` or `true`, and the hash BaseAiCore computes for that profile, both refuse
with a `runtime_profile_hash` mismatch. The preserving reader keeps the unknown key — a nested
definition allows extras — and then its own validator, which belongs to the frozen class,
recomputes the hash without it. Rule 2 promises the opposite. ADR-0068's two earlier minors never
met this: the `adapter` field on evidence and the bundle's wider element type add fields that no
frozen validator reads.

**LoadCoach reads neither payload.** Its evidence import reads `capability.evidence` and
`benchmark.evidence_bundle`, which carry only `runtime_profile_hash` — a string FreeWeight already
computes with the field. No application's source reads `benchmark.result` or
`benchmark.run_summary`. The one reader in the suite is FreeWeight's own export test, which
re-reads a run summary through `BenchmarkRunSummaryIn`.

## Decision

**The two payloads that embed a runtime profile gain a `1.1`. A `1.0` reader accepts a `1.1`
document that leaves the field unstated, and refuses one that states it; that limit is permanent,
named and tested.**

1. **Only what embeds the profile moves.** `RuntimeProfileV1_1Fields(RuntimeProfileFields)` adds
   `adapters_registered: bool | None = None`, drops the key from the dump when it is `None`
   (ADR-0068 rule 4), and computes `profile_hash` through `baseaicore.RuntimeProfile` with the
   field. `BenchmarkResultV1_1Fields` and `BenchmarkRunSummaryV1_1Fields` subclass the frozen
   classes and override only `runtime_profile`, so the inherited validators check the right hash.
   `capability.evidence` and `benchmark.evidence_bundle` do not move: they carry the hash, not the
   profile.
2. **Rule 2 holds for an unstated document, and not for a stated one.** A `1.1` document that
   leaves the field unstated is byte-identical to `1.0`, and every `1.0` reader accepts it. One
   that states it is refused by every `1.0` reader, with a hash-mismatch error. A reader that must
   read such documents imports `BenchmarkResultV1_1In` / `BenchmarkRunSummaryV1_1In` (rule 10).
   SetSpec's contract tests assert both halves, so the limit is a tested fact rather than a
   paragraph.
3. **Producers version by content (ADR-0084).** A run whose profile left the field `None` exports
   exactly the bytes it exported before. `freeweight.export` embeds run summaries verbatim
   (ADR-0035 §4), so it is the container whose own minor carries this one (ADR-0068 rule 5): an
   export is `1.1` when any run in it states the field, and `1.0` otherwise. FreeWeight's
   `EMITTED_SCHEMAS` names `1.1` for both (ADR-0084 rule 4).
4. **No consumer test in LoadCoach.** The consumer the kickoff named does not read these payloads,
   so a test that it "accepts `1.1` unchanged" would test nothing. The reader that exists —
   FreeWeight's own export test — adopts `BenchmarkRunSummaryV1_1In`. The first application that
   reads either payload owes the consumer test.

## Alternatives considered

**Teach the frozen `RuntimeProfileFields.profile_hash` to include a preserved
`adapters_registered` key.** It moves no artifact — a property is not in the JSON Schema — and a
`1.0` reader from `setspec 0.7.0` would accept stated documents. Rejected on three counts. It
changes the frozen class's behaviour, which ADR-0068 rule 1 forbids because that class *is* what
`1.0` means. It cannot reach a reader already installed with `setspec 0.6` or earlier, so rule 2
would still fail wherever it matters. And the frozen writer `BenchmarkRunSummaryOut` would then
accept the field as a nested extra with a matching hash, so a producer that never adopted `1.1`
could emit a `1.1` document without an edit in its own tree — what rule 10 exists to prevent.

**A major: `benchmark.result` and `benchmark.run_summary` `2.0`.** Honest about the
incompatibility, and rejected as the expensive answer. Every reader moves, including for the
documents that do not state the field — every document written today — which `1.0` reads as they
stand. A clean `SCHEMA_VERSION_UNSUPPORTED` refusal is not worth a new module for two payloads no
other application reads.

**Keep FreeWeight on `1.0` and leave the field off the wire.** Not available. The stored
`profile_hash` includes the field, so omitting it fails the hash check (the defect itself), and a
hash recomputed without it would publish a profile that never ran — the silent merge ADR-0074
exists to close.

**Stop checking `runtime_profile_hash` in the `1.1` classes.** Rejected: that check found this
defect, and it is how a consumer knows a profile and its hash belong together.

## Consequences

* `setspec 0.7.0` publishes `benchmark.result` and `benchmark.run_summary` at `1.0` and `1.1`. The
  `1.0` artifacts regenerate byte-identically. It requires `baseaicore>=0.4.2`, the first release
  with the field.
* A reader of these payloads that may see documents from an adapter-capable FreeWeight uses the
  `V1_1In` names. Reading them through the bare names fails loudly, but with a hash-mismatch
  message rather than `SCHEMA_VERSION_UNSUPPORTED` — misleading, and fixed only by adopting the
  minor.
* `freeweight 1.3.0` stores the field in `runtime_profiles` (migration `0010`, backfilled by
  recovering it from each stored hash), writes it into summaries when stated, and writes
  `freeweight.export` `1.1` only for exports that need it.
* The same limit applies to any later minor that adds an input to a hash an older class
  recomputes. `RuntimeProfile` gaining another field is the obvious next case.

## Revisit when

* **An application other than FreeWeight reads either payload.** The limit stops being
  theoretical, and a hash-version field on the profile, or a major, may be worth its cost.
* **`RuntimeProfile` gains another hashed field.** A second minor with the same limit is the point
  where "readable at its own minor" should become one rule for the profile rather than a note per
  field.
