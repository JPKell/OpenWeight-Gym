# ADR-0065 — An adapter is a distillate of its training data, and it does not leave the machine

**Status:** Accepted (2026-09-02)
**Extends:** [Adapter Identity and Serving §9](../architecture/adapter-identity-and-serving.md),
[Security Standards](../standards/security-standards.md) (egress), risk S5.
**Relates to:** [ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md) (the ordered
vocabulary and the `max()` join), [ADR-0054](0054-spotcheck-records-egress-it-does-not-enforce-it.md)
(where the denial is recorded), [ADR-0043](0043-grounding-is-verified-not-assumed.md) (an invariant
is checked, not assumed), [ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md)
(the manifest field).
**Source:** [Adapter roadmap §2, A-8](../roadmap/adapter-roadmap.md).

## Context

A LoRA is trained on something. If that something was a company's support tickets, its house style
guide, or a person's own correspondence, then the adapter is a compressed, lossy artifact *of that
material* — trained from it, shaped by it, and in the case of small fine-tuning sets, demonstrably
capable of reproducing parts of it.

Two questions follow, and the suite has to answer both before an adapter is ever served.

**What is an adapter's own sensitivity?** It is not the base's — the base is a public download.
Treating an adapter as inheriting the base's public status would classify a distillate of internal
documents as public, which is the wrong answer in the direction that hurts.

**What is the sensitivity of work done under one?** A public prompt answered by an adapter trained
on confidential material has produced output shaped by confidential material. Recording that work as
public would be true of the input and false of everything else.

The suite has just built the vocabulary for both
([ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md)) and the ledger that records
verdicts over it ([ADR-0054](0054-spotcheck-records-egress-it-does-not-enforce-it.md)). What remains
is to say where an adapter sits in it.

## Decision

**Every adapter carries a data classification, adapters are local-only artifacts in v1, and the
effective classification of work is the join of the caller's and the adapter's.**

1. **The manifest carries `data_classification`, and the field is required.** The
   `model.adapter_manifest` schema marks it `required` with no default: a manifest that omits it
   is invalid, and its adapter is unavailable — named by `doctor` — until a person supplies the
   value. `loadcoach adapters scan` writes `confidential` into every draft, so a reviewed value can
   only ever be relaxed on purpose. That keeps the fail-closed direction of
   [ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md) without a schema default
   a validator would fill in silently — ADR-0046's default governs callers, not manifests. An
   adapter trained on confidential material is confidential.
2. **Effective classification is `max(caller's declaration, adapter's classification)`**, recorded
   wherever classification is recorded — on the turn, on the attempt, in the egress request. This is
   the lattice join the ordered vocabulary exists to make expressible, and it is a built-in `max()`
   with no helper.
3. **Adapters are local-only.** No adapter artifact is ever uploaded to a remote endpoint. A
   would-be adapter egress is a **recorded SpotCheck denial**, not a silent omission; LoadCoach
   additionally excludes remote + adapter candidates with a named rejection
   (`excluded_by_policy`).
4. **The invariant is recorded, not merely relied upon.** Because adapters exist only behind local
   providers, the classification lattice is satisfied by construction at serving time — and the
   adapter's classification is *still* written onto every turn and attempt that used it. An
   invariant nothing records is an invariant nobody can check
   ([ADR-0043](0043-grounding-is-verified-not-assumed.md)'s principle, applied to egress).

## Alternatives considered

**Treat an adapter as unclassified — weights are not data.** The strongest argument against this
whole record, and it is not frivolous: a LoRA is a low-rank delta over weights, not a copy of a
corpus, and no user can query it for a document. Rejected on two grounds. Empirically, memorization
from small fine-tuning sets is well documented, and the suite is in no position to adjudicate how
much of it a given adapter carries — an unknown here is a reason to be careful, not a reason to
assume the favourable answer ([ADR-0016](0016-unavailable-is-not-zero.md)'s instinct, applied to
risk). And classification here is about **provenance**, not only extractability: work produced by an
adapter trained on internal material is internal work, and the effective-classification rule is what
keeps the record honest about that.

**Make the manifest's classification optional, defaulting to public.** Less friction on adoption,
and most adapters in practice are trained on innocuous material. Rejected: it is a fail-open
default in the one field that governs egress, and the person who omits it is exactly the person who
did not think about it. [ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md)
already decided the direction of an absent classification.

**Let an operator mark an adapter exempt from the lattice** — a per-adapter override for cases the
operator judges harmless. Rejected: an exemption is a fail-open switch on a per-artifact basis,
which is the hardest kind to audit. An operator who believes an adapter is public *declares* it
public in its manifest, which is a reviewed statement in a versioned file rather than a flag; there
is no third state.

**Permit remote adapter serving where a provider supports it.** Some hosted providers do accept
uploaded adapters, and an operator with the right contract may legitimately want it. Rejected for
v1 and deliberately routed through the revisit trigger rather than a configuration flag: the terms
under which an artifact may be uploaded are per-provider and per-contract, and a flag would let that
decision be taken by accident, once, by whoever edited the configuration file.

**Rely on the local-only rule and skip recording the adapter's classification per turn.** It is
redundant by construction, and it is one more column. Rejected: "by construction" is a claim about
today's code, and the record is what lets it be verified tomorrow — including after LC-E1 makes
mixed local/remote pools ordinary. The redundancy is the audit.

## Consequences

* Every adapter manifest has a required classification field, reviewed by a person as part of the
  scan workflow ([ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md)).
* A confidential adapter raises the effective classification of every turn that uses it, which can
  make an otherwise-public trajectory ineligible for a remote tier. That will surprise someone the
  first time; the explanation names the adapter as the reason, and the surprise is the mechanism
  working.
* LoadCoach gains a hard constraint excluding adapter subjects from remote providers, and
  PromptCadence records the adapter's classification on turns whose classification it may have
  raised. Integration verification I19 exercises exactly this: a confidential adapter with a
  remote-tier request produces a recorded denial.
* Adapters cannot be used with hosted frontier models in v1, at all. That is a real capability the
  suite is declining, and the local-only rule is the reason the classification lattice is satisfiable
  without trusting a third party's handling of an artifact derived from someone's data.
* Nothing here is enforced by inspecting bytes on the wire. The guarantee is that no code path uploads
  an adapter and that every would-be attempt is recorded — which is checkable, and smaller than
  "your data cannot leak", and the documentation says so.

## Revisit when

A remote provider offers adapter upload **under terms an operator accepts**. That reopening is a new
ADR — one that states whose terms, what the provider does with the artifact, how the classification
lattice is satisfied when the artifact itself has left, and what the recorded decision looks like.
It is deliberately **not a flag**, because a flag would make it a configuration accident rather than
a decision.
