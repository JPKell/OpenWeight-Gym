# ADR-0054 — Commissioner renders and records an egress verdict; enforcing it is the caller's

**Status:** Accepted (2026-09-02)
**Extends:** [Commissioner Spec §3 and §11](../packages/commissioner/spec.md).
**Relates to:** [ADR-0011](0011-shared-package-boundaries.md) (package boundaries and the
boundary-violation rule this invokes), [ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md)
(the ordered vocabulary it compares), [ADR-0051](0051-plans-stay-internal-and-one-payload-travels.md)
(why the payload is in SetSpec), [ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md)
(how its ledger is stored), risk S5 (silent data egress).
**Source:** [PromptCadence roadmap §2, D-10](../roadmap/promptcadence-roadmap.md).

## Context

The suite already *behaves* correctly about egress in places: LoadCoach's `allow_remote` is opt-in,
IdeaPress paints a per-stage badge, and remote providers are off by default. What none of it
produces is a **record**. "What left this machine, when, to where, and under whose policy?" has no
answer that outlives the process, which is the gap risk S5 names and the one PromptCadence's fourth
public contract exists to close.

The design skeleton left the shape of the answer open, as an either/or: is this a package, or is it
a bare SetSpec event type? The question is a trap in both directions. A payload alone gives every
consumer a shape and no implementation, so each writes its own comparison and the fail-closed case
is where they will differ. A package alone gives an implementation with no interchange, so
IdeaPress's badge would have to import Commissioner to read a decision PromptCadence wrote — coupling
two applications through a package's in-process types.

There is a third pull, and it is the one that would do the most damage: a package that *enforces*.
Once something owns the verdict, it looks natural for it to own the refusal too — to intercept the
call, halt the trajectory, paint the badge. That is application policy, and a package that acquires
it becomes an application with an import name, which is exactly the boundary violation ADR-0011
and risk A2 are written against.

## Decision

**Commissioner's scope is exactly three things: the payload, the ordered comparison, and an
append-only ledger. Enforcement and deployment policy stay with the caller.**

1. **The shape is SetSpec; the implementation is the package.** The either/or was a false one, and
   the split runs between interchange and behaviour: `governance.egress_decision` 1.0 lives in
   SetSpec so a `setspec`-only reader can validate and read a decision with Commissioner absent
   ([ADR-0051](0051-plans-stay-internal-and-one-payload-travels.md)); the evaluation and the ledger
   live in a deliberately tiny package with two named consumers.
2. **The comparison, and nothing more.** `OrderedClassificationPolicy` is the whole shipped policy:

   ```text
   local target                  -> APPROVED / "target_not_remote"
   remote, no declared ceiling   -> DENIED   / "no_ceiling_declared"     (fail closed)
   classification <= ceiling     -> APPROVED / "within_ceiling"
   classification >  ceiling     -> DENIED   / "classification_exceeds_ceiling"
   ```

   It uses `baseaicore.DataClassification` and defines no levels, no aliases and no parallel
   taxonomy ([ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md)).
3. **Fail closed on an undeclared ceiling.** A remote target with no `max_data_classification` is
   denied, never assumed public. The absent value is the reason to refuse, not a reason to guess.
4. **A denial is as durable as an approval.** `evaluate` never raises for a deny — a deny is data.
   Both verdicts are recorded through the same `record()`, and a test asserts the ledger holds them
   symmetrically. An egress log that only contains what was allowed answers the wrong question.
5. **No enforcement.** Commissioner refuses no call, halts no trajectory and paints no badge; it makes
   no HTTP request, so it could not intercept one. Acting on a verdict — PromptCadence ending the
   turn with a structured refusal, IdeaPress showing the badge — is the application's.
6. **No application policy.** What counts as `internal` in a deployment, which tiers exist, when a
   human must confirm: all caller-side. The package's only opinion is the ordering.
7. **`VIOLATION` is writable but never generated.** The shipped policy produces only `APPROVED` and
   `DENIED`. `VIOLATION` is written by a caller's *verification* step after the fact — PromptCadence
   contract 4, a local-tier turn answered by a remote provider — and the ledger accepts it, because
   an after-the-fact violation is a governance fact the record must be able to hold.
8. **Append-only.** The package exposes no update and no delete; an API-surface test asserts it.

## Alternatives considered

**A SetSpec payload alone, with no package.** The smallest possible answer, and it satisfies the
interchange requirement outright. Rejected: every consumer would then implement the comparison, and
the row they would implement differently is the fail-closed one — a remote target with no declared
ceiling is exactly the case a hurried implementation treats as "no restriction stated, therefore
allowed". A shared shape with unshared semantics is the worst of both.

**A package alone, with the decision as an in-process type.** Rejected: IdeaPress's badge would
have to install Commissioner to read what PromptCadence recorded, which couples two applications
through a package's private types and violates the rule that applications interoperate only over
versioned payloads. It would also fail the acceptance criterion outright — a `setspec`-only script
must be able to read an exported decision.

**Let Commissioner enforce** — hand it the HTTP client, let it refuse the call and raise. Superficially
the safest design ("the guard cannot be forgotten"), and it is what a firewall-shaped mental model
suggests. Rejected: it puts application control flow inside a capability package, makes a deny an
exception rather than a record (the same defect
[ADR-0053](0053-a-refused-tool-call-is-a-result-not-an-exception.md) rejects for tools), and it is
a lie about what the package can see — Commissioner evaluates *declared* facts, so a caller that lies
about its classification is not stopped by any amount of enforcement inside the package. The real
protection is that PromptCadence has exactly one egress path
([ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md)) and evaluates before it,
which is an application property.

**Inspect the network instead of trusting declarations** — a proxy, an outbound filter. Genuinely
stronger in principle: it would catch a caller that declares wrongly. Rejected as out of scope for
a package below the applications, and as new infrastructure without a demonstrated need (§11.12).
The suite's compensating control is that outbound calls exist in exactly one place per application
and are tested by a network-isolation e2e test.

**Fold the ledger into each application** and ship only policy plus payload. Rejected on the second
consumer: PromptCadence and IdeaPress both need query-by-run, query-by-verdict and query-by-target
over an append-only table, and the mounting pattern
([ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md)) makes sharing the shape
possible without sharing a database.

## Consequences

* Commissioner is a very small package on purpose: two protocols, one policy, two ledger
  implementations, one mount function. Smallness is the design, and growth is the signal in the
  revisit trigger below.
* It is the one capability package besides MirrorWall permitted to import SetSpec, and for the same
  reason: it owns a cross-application payload's Python form.
* Every remote-tier turn in PromptCadence writes a row, approved or denied, and a store failure
  halts the turn rather than proceeding unrecorded — an unrecordable governance decision is not a
  decision that may proceed. That policy is PromptCadence's, stated in its error table, exactly as
  this record requires.
* IdeaPress's S4 badge stops being an ad-hoc flag at M13 and becomes a query over recorded rows,
  with denials visible in project history.
* Because the package neither enforces nor inspects, the guarantee it provides is precisely
  "every declared egress decision was evaluated by one implementation and recorded durably". That
  is a real and checkable claim, and it is smaller than "nothing leaves without permission" — the
  documentation says so rather than implying the larger one.

## Revisit when

The package accretes an application concept — a tier, a stage, a trajectory, a deployment policy,
an enforcement hook. [ADR-0011](0011-shared-package-boundaries.md)'s boundary-violation rule applies
at that point, and the correct move is to push the concept back into the application, not to grow
the package to fit it.
