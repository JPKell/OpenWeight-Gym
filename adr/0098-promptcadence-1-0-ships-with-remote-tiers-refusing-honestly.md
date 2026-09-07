# ADR-0098 — PromptCadence 1.0 ships with remote tiers refusing honestly

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Spec §17](../apps/promptcadence/spec.md) — what the `tiers` health
component says about a remote tier; [PromptCadence Roadmap §9](../roadmap/promptcadence-roadmap.md)
I13 — the recorded-transport half lands at 1.0, the live half after it.
**Relates to:** [ADR-0073](0073-egress-is-decided-on-configuration-before-availability.md)
(egress and pricing precede availability), [ADR-0055](0055-loadcoach-registers-providers-by-name-and-kind.md)
(LoadCoach declares a registration's egress class; it is never inferred),
[ADR-0072](0072-the-model-pricing-record-file.md) (the pricing record a remote tier must name).
**Source:** Row I2, decision 4 — the release-scope decision the development plan's Phase 9 *Known
risks* and the roadmap's risk table say must be recorded at M12, not improvised.

## Context

Roadmap I13 has two halves. The **recorded-transport** half proves, in CI against the fake
LoadCoach, that with one local and one remote provider registered a `remote_cheap` step routes to
the remote registration, the turn carries the egress badge and its `EgressDecision`, its spend is
priced and debited, and a local tier never does any of that. The **live** half runs the same
trajectory once against a real OpenAI-compatible endpoint with a real key.

H2 (LoadCoach 1.1, LC-E1) delivered what the recorded half needs: `[providers.<name>]` blocks with
a **declared** `remote` flag, `provider_name` and `is_remote` on every `/models` entry and on the
`model` block of every `/generate` response. Until this row PromptCadence read neither —
`ProviderSurface.has_remote_provider` was `False` by construction and the console's tiers page
passed a literal `False` — so a remote tier was unavailable whatever LoadCoach had registered.

The live half needs a key, a remote endpoint and money, none of which a build can supply. The plan
tolerated exactly this: *"1.0 can ship with remote tiers refusing honestly (documented), because
the refusal is specified behaviour."* This record is that decision, with its date and its reason.

## Decision

**`promptcadence 1.0.0` ships with the recorded-transport half of I13 proven in CI and the live
half deferred. A remote tier refuses honestly, naming which of its two preconditions is unmet,
until an operator meets both.**

1. **The remote-provider fact is read from LoadCoach, never assumed.** `ProviderSurface` reads
   `is_remote` from `/models`; `has_remote_provider` is true when any registered model's
   registration declares itself remote. The fact is read where the surface is already read —
   before a trajectory executes and when a plan is approved — so a registration made while the
   process runs is seen at the next trajectory, without a restart. An unreadable LoadCoach reads
   as *no remote provider*, the safe default.
2. **A response's subject is verified against its own `is_remote`** when the wire carries it,
   and against the single-configured-kind rule when it does not (an older LoadCoach). A response
   naming neither is a violation, as before. `provider_name` is recorded on the turn when present.
3. **A remote tier is unavailable for one of exactly two recorded reasons**, in this order, and
   the `tiers` health component, `doctor`, `GET /tiers` and the console say which:
   `loadcoach_has_no_remote_provider` (LoadCoach has no registration declaring `remote = true`)
   or `unpriced` (the tier names a pricing file that holds no record claiming now). A remote tier
   that has both is *available*, and the pre-flight order of ADR-0073 still runs on every turn.
4. **The recorded-transport journey is a CI test.** The fake registers a local and a remote model
   under distinct provider names; a bypassed trajectory pinned to `remote_cheap` with an
   `internal` classification and a priced tier completes with its turn served by the remote
   model, the turn's `EgressDecision` `approved` with a remote target, a priced ledger entry, and
   the explanation naming the provider; the same trajectory on `local_fast` is served by the
   local model with `target_not_remote`. That test is I13's recorded half and it is a release
   gate.
5. **The live half is a post-1.0 verification, not a 1.0 code change.** When an operator supplies
   an endpoint and a key, the run is: register the provider in LoadCoach with `remote = true`,
   price the tier in an ADR-0072 file, run `promptcadence run … --tier remote_cheap
   --classification internal`, and read the explanation. The command sequence is in
   `docs/tiers.md`; the result is recorded in the handoff of whichever row runs it. No release
   waits on it, because the transport it exercises is the one rule 4 already proved.
6. **The changelog says this in these words.** *"Remote tiers refuse honestly until LoadCoach has
   a registration declaring `remote = true` and the tier is priced; the live remote run (I13) is
   deferred by ADR-0098."*

## What this refuses

* Inferring a remote provider from a provider kind (`openai_compatible` is both local and remote;
  ADR-0055 rule 4).
* Reading the fact from configuration. PromptCadence's `[tiers]` says what a tier *is*; only
  LoadCoach knows what is *registered*.
* Shipping a `tiers` component that says `ok` for a tier nothing can serve.
* Running the live half against an unpriced tier and calling the `UNPRICED_EGRESS_REFUSED` that
  results a pass. That proves spec §20 #5, which is already proved; it does not prove I13.

## Alternatives considered

**Hold 1.0 for the live run.** The honest-sounding option, and it makes a release wait on a
credential and a bill that the build cannot supply, for a path whose every component is
individually proven: the wire (H2, live), the routing to a remote registration (H2's gate B),
PromptCadence's egress, pricing and verification (this row, recorded). The roadmap's risk table
rejected this in advance.

**Ship without the recorded half either, remote tiers dark.** What the beta did. Rejected: the
dependency H2 supplied has landed, the fake can play a mixed registry, and a 1.0 whose remote
path has never executed even against the fake would be shipping a specified feature untested.

**Read the fact once at startup.** Simpler, and it means registering a remote provider in a
running LoadCoach needs a PromptCadence restart to notice, which contradicts lifecycle §3's
"nothing else in PromptCadence changes when it arrives". The surface is already read per
trajectory; reading the flag there costs nothing.

## Consequences

* `ModelEntry` and `ModelInfo` gain optional `provider_name` and `is_remote`; the fake carries
  both; the vendored LoadCoach snapshot is refreshed to the 1.1 document.
* `loadcoach_has_remote_provider` stops being a constructor constant and becomes the surface's
  answer, in the loop, the approval service and the console.
* `GET /tiers` (spec §7.1, absent until now — I1 §5) is built, answering the same report the
  console's tiers page renders, so a client can ask the question too.
* The changelog's *Known limitations* names the deferred live run with this record's number.

## Correction, found while building rule 1 (2026-09-06, the same row)

**LoadCoach 1.1.0 does not render `is_remote` in `GET /models`.** H2 recorded the flag on the
`models` table and on the generate response's `model` block (api.md §4 shows it there); the
listing's `_model_to_json` renders neither `provider_name` nor `is_remote`. So rule 1's read of
`/models` finds nothing on 1.1.0, and the safe default holds: the fact reads `False`, a remote
registration is invisible before its first turn, and a remote tier stays unavailable with
`loadcoach_has_no_remote_provider` — which is exactly this record's decision, honestly refused
rather than guessed. Rule 2 — verification of a *response* by its declared `is_remote` — works on
1.1.0 today. PromptCadence reads the flag from `/models` **when present**, so the day LoadCoach
renders it (a one-line addition to `_model_to_json`, scheduled as a LoadCoach patch row) the
fact arrives without a PromptCadence change. The recorded-transport journey (rule 4) runs against
the fake, whose `/models` renders the field as api.md's shape-for-shape mirror should.

## Revisit when

The live run happens. Its handoff records the provider, the model, the explanation and the debit,
and this record's rule 5 is then satisfied rather than superseded.
