# ADR-0046 — Data classification is ordered, caller-declared, and defaults to the most restrictive

**Status:** Accepted (2026-09-02)
**Extends:** [Master Architecture §1.3](../architecture/master-architecture.md) (domain terms),
[BaseAiCore Spec §7](../packages/baseaicore/spec.md).
**Relates to:** [ADR-0016](0016-unavailable-is-not-zero.md) (an absent value is never a convenient
number), [ADR-0026](0026-local-http-hardening.md) (fail closed at a boundary),
[ADR-0054](0054-spotcheck-records-egress-it-does-not-enforce-it.md) (the consumer of this ordering),
[ADR-0065](0065-an-adapter-is-classified-and-local-only.md) (an adapter carries one).
**Source:** [PromptCadence roadmap §2, D-2](../roadmap/promptcadence-roadmap.md).

## Context

Three of the arc's components must answer one question before any request leaves the machine: *may
data this sensitive go to that target?* PromptCadence asks it per turn; SpotCheck evaluates and
records the verdict; an adapter manifest declares the sensitivity of the material a LoRA was
trained on. IdeaPress will ask it too, when its S4 egress badge stops being an ad-hoc backend flag
and starts reading rows.

The suite has no vocabulary for it. What exists today is a boolean at each site — LoadCoach's
`allow_remote` opt-in, IdeaPress's per-stage badge — and a boolean cannot express the shipped tier
ladder, which needs three positions: a local tier serves anything, `remote_cheap` serves up to
internal, `remote_frontier` serves public only.

The comparison itself is the thing being specified. "May this go there?" is `classification ≤
target ceiling` — an ordering, not a set membership and not a string equality. Once that is true,
where the type lives follows: every component that performs the comparison must get the *same*
ordering, because the failure mode of a per-component vocabulary is not a crash but a mapping that
quietly widens at one boundary. Two components disagreeing about whether `internal` outranks
`confidential` is a silent egress bug that no test in either component would catch.

There is also a lattice operation. [ADR-0065](0065-an-adapter-is-classified-and-local-only.md)
makes the effective classification of work `max(caller's declaration, adapter's classification)`,
and PromptCadence takes the same join when a tool result raises a turn's classification. That
operation must be available to a caller who has imported nothing but the type.

## Decision

**`baseaicore.DataClassification` is a three-level ordered vocabulary — `PUBLIC < INTERNAL <
CONFIDENTIAL` — declared by the caller, defaulting to the most restrictive level, and fixed for
the life of the suite.**

1. **The ordering is the contract, and it is part of the public surface.** `<`, `<=`, `>`, `>=`
   are defined on the type and golden-tested pairwise over all nine ordered pairs. The lattice
   join is the built-in `max()`; no helper, no import, no per-consumer comparison function. Every
   consumer that needs "the more restrictive of these two" writes `max(a, b)` and is right by
   construction.
2. **It is not an `IntEnum`.** `PUBLIC` must not be `0`, because `0` is falsy and `if
   classification:` would then read "public" as "unset" — [ADR-0016](0016-unavailable-is-not-zero.md)'s
   bug class arriving inside a governance type, where its consequence is an egress rather than a
   wrong chart. Ordering is defined explicitly over the members; the serialized form is the
   lowercase string (`"public"`, `"internal"`, `"confidential"`), which is what appears in TOML
   configuration, in SetSpec payloads and in stored rows.
3. **The default is `CONFIDENTIAL`.** An undeclared classification is the most restrictive one, so
   an omission costs a user a remote tier rather than costing them their data. Every surface that
   accepts a classification says so: PromptCadence's `POST /trajectories` defaults to
   `"confidential"`, and a remote tier that declares no ceiling is denied outright rather than
   assumed public ([ADR-0054](0054-spotcheck-records-egress-it-does-not-enforce-it.md) rule 2).
4. **Adding a level is a new ADR, not a minor release.** The ordering is what consumers compute
   against, so a fourth level has to be given a position between existing ones, and every stored
   row, every tier ceiling and every adapter manifest written before it acquires a new meaning
   relative to it. That is a decision with a migration, not a vocabulary addition.
5. **It ships in BaseAiCore, additively, as `0.4.1`** — inside every existing `>=0.4,<0.5` pin, so
   no consumer needs a coordinated release to gain it. BaseAiCore is where it belongs by the
   ownership rule: it is a value type crossing every boundary, it needs no dependency, and the
   components that compare it (SpotCheck, PromptCadence, an adapter manifest's reader) already
   import it.

## Alternatives considered

**Free-form classification tags, per deployment** (`"pii"`, `"customer-data"`, `"nda"`). Genuinely
attractive: real organizations classify by *kind*, not by rank, and a tag set costs nothing to
extend. Rejected because tags have no ordering, and without an ordering every consumer must supply
its own comparison — which is the same objection [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)
makes to a free-form adapter tag channel, for the same reason. A deployment that needs kinds can
still carry them: a tag is metadata beside the classification, and the *rank* is what governs
egress. What must not exist is two vocabularies both claiming to answer "may this leave".

**A boolean — `sensitive: bool`.** The smallest thing that could work, and it matches what
LoadCoach and IdeaPress do today. Rejected on the shipped configuration: the four default tiers
need three ceilings, and a boolean collapses `remote_cheap` and `remote_frontier` into one class,
which is exactly the distinction an operator wants ("summaries of internal notes may go to the
cheap endpoint; nothing but public text goes to the frontier one"). Three levels is not
aspiration — it is the minimum that makes the shipped ladder expressible.

**Five levels, in the government style** (public / internal / confidential / secret / top secret).
Rejected: a level that no operator can distinguish operationally gets chosen by coin flip, and a
mis-declared level is worse than a coarse one — it produces confident, wrong routing. Three levels
map onto decisions this suite actually makes. The revisit trigger below is the honest escape.

**Define it in SetSpec instead.** SetSpec owns the capability vocabulary, so a governance
vocabulary looks like a sibling. Rejected on two counts: the classification is compared in memory
long before anything is serialized (SpotCheck's policy is a pure function over values), and
putting it in SetSpec would make every consumer of a three-member enum depend on pydantic —
including `spotcheck.sql`'s rows and BaseAiCore-only scripts. SetSpec still *carries* it in
`governance.egress_decision`; carrying a value is not owning its type.

**Per-application enums with a mapping at each boundary.** Rejected: N mappings, each one a place
where `internal` can be silently widened, and no test in either application sees both sides. This
is the failure the shared-type layer exists to prevent
([ADR-0011](0011-shared-package-boundaries.md)); a governance vocabulary with two consumers named
before a line is written is not a premature extraction.

**Default to `PUBLIC` (or an `UNCLASSIFIED` fourth member).** Rejected: it is a fail-open default
in the one place the suite is strictest, and an `UNCLASSIFIED` member would have to be *ordered*
somewhere — below public makes it freely exportable, above confidential makes it useless. Absence
is not a level; it is a reason to assume the worst.

## Consequences

* BaseAiCore ships `0.4.1` with one enum and no new dependency. Every existing golden passes
  unchanged; the additive proof is that the release changes no serialized form that exists today.
* **The default has teeth, deliberately.** A user who submits a trajectory without a
  classification cannot reach a remote tier at all, and the refusal names the default as its
  reason. This will be the first thing new operators hit, and the error message is expected to
  carry the fix ("declare `--classification public` if this task's data may leave the machine").
* Ordering comparisons become a golden-tested contract in BaseAiCore, which means the pairwise
  table is fixed the way the canonical-ID format is fixed. `max()` over the type is the documented
  lattice join, used identically by PromptCadence, SpotCheck and the adapter path.
* Two independent components can now be *shown* to agree: SpotCheck's policy matrix and
  PromptCadence's tier admission are the same comparison over the same type, so the egress
  invariant is checkable rather than asserted in two places.
* The type is a rank, not a taxonomy. A deployment whose real question is "which regulation covers
  this?" gets no help from it, and the documentation says so rather than implying more governance
  than three ordered words can carry.

## Revisit when

A deployment needs finer levels than three — at which point the addition is written as its own ADR
that states the new member's position in the ordering, the meaning acquired by every row stored
under the old vocabulary, and the migration. The ordering is the contract; an addition is never a
minor release.
