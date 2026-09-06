# ADR-0087 — The adapter evidence gate admits only a signal that scores

**Status:** Accepted (2026-09-06)
**Amends:** [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) rule 3 (what
`require_adapter_evidence` reads), and through it
[LoadCoach Routing §4](../apps/loadcoach/routing.md)'s `adapter_unmeasured` row.
**Relates to:** [ADR-0023](0023-runtime-profile-resolution.md) §3 and
[ADR-0017](0017-benchmark-confidence-and-freshness.md) (the exclusions the gate must now honour),
[ADR-0022](0022-capability-evidence-record-contract.md) §4 (binding), [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md)
(evidence is measured, never inherited), [ADR-0088](0088-an-excluded-measurement-falls-back-to-the-prior-it-displaced.md)
(the other half of the same live failure).
**Source:** Row H6, from the H5 interview on 2026-09-06 — observed live at H5 rather than reasoned
about in advance (`docs/history/H5_HANDOFF.md` §9, §10.1).

## Context

`require_adapter_evidence` is the one hard constraint standing behind ADR-0064's product claim: **no
benchmark, no routed selection.** An adapter subject with no measured evidence for the profile's
top-weighted capability is rejected `adapter_unmeasured`, in the open, on every decision.

It reads the wrong list. The gate iterates `subject.signals` — the *raw* signals attached to the
candidate — and admits the subject when any of them names the capability with source `benchmark` or
`production`. Scoring then re-reads the same list and applies three exclusions the gate never saw:

* a benchmark whose `match_state` is not `bound` (ADR-0022 §4) — `evidence_unbound`;
* a performance, memory or energy measurement taken on another machine (ADR-0017) —
  `evidence_foreign_machine`;
* a benchmark measured under a runtime profile that is not the one being executed (ADR-0023 §3) —
  `evidence_profile_mismatch`.

So a signal can satisfy the gate and then contribute nothing at all. The subject is admitted for
having been measured *somewhere*, and is scored on whatever is left — a provider-declared flag at
`0.500`, a parameter-band prior, or nothing.

**Row H5 ran into this on real weights.** Three adapter subjects and their bare base were routed
under a profile weighting `reliability`. FreeWeight had measured all of them; the recorded runtime
profile did not match the one LoadCoach resolved, so every measurement was excluded as
`evidence_profile_mismatch`. Two of the adapters *also* declared `reliability` on their manifests.
Those two scored `0.500 declared`, the bare base scored `absent`, and the two adapters outranked
it — with the gate silent throughout, because both had "measured evidence" in the raw list.

A claim beat a measurement, under the one constraint whose entire purpose is to stop that. Nothing
was logged as unusual, because from each component's own point of view nothing was: the gate
answered "has this subject ever been measured", the scorer answered "does this measurement apply
here", and both answered correctly. The defect is that only one of those two questions gates
routed selection, and it is the weaker one.

## Decision

**The gate reads the resolved capability score, not the raw signal list. A subject satisfies
`require_adapter_evidence` only when the score that actually stands behind the top-weighted
capability came from a measurement — `benchmark` or `production` — after every exclusion scoring
applies.**

1. **One question, asked once.** `score_subject` already runs before the hard constraints for every
   candidate, and its per-capability breakdown is already handed to the constraint filter for
   `min_capability_scores`. The gate reads that same breakdown. There is no second copy of the
   exclusion rules, and there cannot be one that drifts: an exclusion added to scoring is honoured
   by the gate on the same commit.
2. **A declaration never satisfies the gate.** `declared`, `manual` and `prior` are statements, and
   the gate's purpose is to refuse to route on statements. A `manual` score counts as *evidence* for
   the `low_evidence` flag (routing §5) and still does not count as a *measurement* here; the two
   sets differ on purpose and this record is why.
3. **The rejection stays `adapter_unmeasured`, and stops being silent.** ADR-0064 rule 3 names one
   rejection reason and this record does not add a second. Its detail gains what the resolved score
   knows: `resolved_source` (`evidence_profile_mismatch`, `evidence_foreign_machine`,
   `evidence_unbound`, `declared`, `prior` or `absent`), the note, both profile hashes or the
   foreign machine's fingerprint where the exclusion carries them, and the `freeweight run start …`
   remedy already computed for the explanation. A caller reading the rejection is told which of
   "nobody has measured this" and "the measurement does not describe this execution" it is, because
   the two have different remedies.
4. **An adapter becomes unroutable when the runtime profile moves.** This is the intended reading,
   stated plainly rather than discovered: change the served context, the KV precision or any other
   profile field, and an adapter measured under the old profile is refused by name until it is
   re-measured — it does **not** degrade to a declared claim and keep routing. The gate's off switch
   ([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) rule 3) is the one
   honest way around it, and it is recorded on every decision made under it.
5. **A pin is unaffected.** The gate filters routed selection; a pin bypasses scoring and not the
   hard constraints, and LoadCoach already passes `require_adapter_evidence=False` for a pinned
   subject (ADR-0064 rule 4, routing §10). A pinned adapter whose evidence does not apply here is
   still served, still recorded, and its explanation still names the exclusion.

## Alternatives considered

**Duplicate the three exclusion predicates inside the constraint filter.** The obvious shape, and
the one the defect invites: teach the gate to check `match_state`, the machine fingerprint and the
profile hash for itself. Rejected because it is the defect's own cause written down deliberately —
two implementations of one rule, in two modules, that agree until somebody edits one. The exclusions
have already grown once (`evidence_unbound` arrived with ADR-0022 §4, after the other two), and each
addition would have to be made twice with nothing failing if it were not.

**Gate on the raw list but weaken scoring instead** — let an excluded measurement score, so the gate
and the scorer agree by lowering the scorer to the gate. Rejected outright: ADR-0023 §3 and ADR-0017
are hard separations, taken because a KV-precision or context change moves metrics by factors. This
alternative is "trust a measurement of something else", which is the failure both records exist to
prevent.

**Add a second rejection reason, `adapter_evidence_excluded`.** Genuinely attractive: never-measured
and measured-elsewhere are different facts with different remedies, and a name is cheaper to read
than a detail field. Rejected because ADR-0064 rule 3 names exactly one rejection, that name appears
in routing §4's table, the explanation contract, the UI and the API's documented vocabulary, and the
distinction it would carry is a *property of one decision*, not a new kind of refusal. Rule 3's
detail carries it, which is where the rest of routing puts the numbers behind a rejection.

**Leave the gate alone and rely on ranking.** The status quo's implicit defence: an adapter scoring
`0.500 declared` will usually lose to a base carrying real evidence, so the gate's laxity rarely
decides anything. Rejected on H5's own evidence, where it decided exactly the wrong way — the base's
evidence had been excluded, so there *was* no real evidence to lose to, and the declaration won by
default. "Usually harmless" is not what a hard constraint is for.

## Consequences

* The gate and the scorer can no longer disagree about what counts as measured, because there is one
  answer computed in one place. An exclusion added to scoring later tightens the gate automatically.
* Some adapter subjects that route today stop routing — every one of them a subject whose evidence
  does not describe the execution being planned. This is a behaviour change inside an unpublished
  `1.1.0`, and it is the change the arc was specified to make.
* A profile mismatch is now visible at the moment it costs a candidate its place, with both hashes
  and the invocation that would fix it, instead of being visible only to a reader comparing a
  rejection's absence against a score's source.
* `require_adapter_evidence = false` becomes a more consequential switch, since it is now the only
  way to route an adapter whose measurements do not apply. It was always meant to be: it is
  recorded on every decision made under it and the selection carries `low_evidence`.
* Nothing changes for a bare base. The gate has never applied to one, and this record does not
  extend it — a base with an excluded measurement is [ADR-0088](0088-an-excluded-measurement-falls-back-to-the-prior-it-displaced.md)'s
  territory, not this one's.

## Revisit when

An exclusion appears that should gate scoring but *not* routed selection — a badge that lowers a
measurement's weight without disqualifying it. This record binds the two questions together on the
strength of there being no such case today; the replacement decision would have to name the
exclusion, say why a subject carrying it may still be selected, and say what the explanation shows
when it is.
