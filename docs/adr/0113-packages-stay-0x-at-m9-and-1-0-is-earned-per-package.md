# ADR-0113 — Packages stay `0.x` at M9; a `1.0` is earned per package, not granted by a milestone

**Status:** Accepted (2026-09-07) — **recorded as the coordinator's recommendation, taken on the
operator's authority, and the operator may still overrule decision 1.** If it is overruled, decision
2's criteria are what the overruling has to argue against, and decisions 3–5 stand either way.
**Amends:** [master-roadmap §6](../roadmap/master-roadmap.md) (the version-trajectory table, whose
M9 column reads a bold **1.0** for the six original packages) and
[§5](../roadmap/master-roadmap.md) (S5's "package-1.0 range widening"), and
[gold-standards §4](../standards/gold-standards.md) (whose parenthetical declared suite 1.0 over
nine components). Both were edited in this record's commit.
**Relates to:** [ADR-0011](0011-shared-package-boundaries.md) (what a package is and when it is
extracted), [ADR-0015](0015-repository-and-distribution-model.md) (one repository, one release
series per component), [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)
(the spirit invoked in decision 3: a widening is a deliberate act, not a side effect),
[packaging and release standards §3–§4 and §7](../standards/packaging-and-release-standards.md).
**Source:** the M9 audit (`~/ai/suite/M9_AUDIT.md`) Group 7, item O3, which named this an architect's
decision the audit could not make; scheduled as row L2 of
[outstanding work §1](../roadmap/outstanding-work.md).

## Context

`master-roadmap` §6 says "Packages reach 1.0 only at M9, when all three applications have exercised
them", and its version-trajectory table carries a bold **1.0** in the M9 column for BaseAiCore,
SetSpec, ModelRack, SweatMeter, WeightsDB and MirrorWall. The four packages of the PromptCadence arc
— CutCtx, ToolYard, LoadLedger, Commissioner — postdate the table and have no row in it at all.

Today all ten sit at `0.x`: `baseaicore 0.4.2`, `setspec 0.6.0`, `modelrack 0.7.1`,
`sweatmeter 0.4.0`, `weightsdb 0.2.1`, `mirrorwall 0.2.2`, `loadledger 0.2.0` (`0.3.0` in
preparation), `cutctx 0.1.0`, `toolyard 0.1.1`, `commissioner 0.1.1`. Every one is on PyPI at its
`__about__.py` version. Meanwhile all four applications are at `1.x`, three of them published.

That leaves M9's checklist item O3 — "every application's dependency ranges admit the **1.0**
packages, verified by a clean-venv resolve" — literally unanswerable: there are no 1.0 packages to
admit. And answering it the obvious way is not a documentation fix. Each application pins every
suite package with a compatible-range ceiling (`baseaicore>=0.4.2,<0.5`, `setspec>=0.5,<0.7`,
`modelrack>=0.7,<0.8`, and so on); bumping the packages to 1.0 means widening every one of those
ceilings, recompiling four locks, and cutting fourteen releases in a week — after which nothing
about compatibility has been *proved*, because the cross-repository compatibility matrix that would
prove it (packaging §7, scheduled as row L6) does not exist in any repository.

Two facts bound the decision. The first is that these packages are genuinely exercised: nine of the
ten have two or more in-suite consumers declaring them in `pyproject.toml`. The exception is
**ToolYard, which has exactly one consumer** (PromptCadence) — the audit's framing that every
package has two was one component too generous. The second is that the surfaces are still moving:
`setspec` went `0.5 → 0.6` on 2026-09-05, `modelrack` `0.6 → 0.7` on 2026-09-05, and `loadledger`
is mid-flight to `0.3.0` as this is written, taking a reader that used to live in an application
([ADR-0110](0110-the-pricing-file-reader-is-a-loadledger-surface.md)). A `1.0` is a promise that
the next breaking change costs a major; it is not a reward for having shipped.

## Decision

1. **M9 does not bump any package to 1.0.** The milestone declares the suite deliverable over
   fourteen components at the versions they hold. `master-roadmap` §6's M9 column and §5's S5 gate
   are amended to say so, and the sentence "Packages reach 1.0 only at M9" is replaced by the rule
   in decision 2.

2. **A package reaches 1.0 when both of these hold, and not before:**
   * **(i) Two consecutive minors with no breaking change to its public surface**, evidenced by its
     own `CHANGELOG.md` across those two releases — the surface has been left alone by two rounds
     of real consumer pressure rather than merely not having been touched lately.
   * **(ii) The cross-repository compatibility matrix (packaging §7, row L6) green on both ends of
     every application's declared range for it** — the floor resolves and passes `contract`/`e2e`,
     and so does the ceiling. Today no lower bound in the suite has ever been resolved: FreeWeight
     floors `setspec>=0.6` and `modelrack>=0.7` where IdeaPress floors `setspec>=0.5` and
     `modelrack>=0.5,<0.6`, and nothing anywhere installs either floor.

   A package meets these on its own schedule. There is no cohort bump and no suite-wide 1.0 event
   for packages; a milestone can note which packages qualified, and cannot confer it.

3. **Until a package is at 1.0, the applications' `<0.x+1` ceilings are the contract.** Widening one
   is a deliberate act with a lock recompile behind it and a changelog line naming what the wider
   range was tested against — never an incidental edit that rides along with unrelated work. This is
   [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md)'s spirit applied to
   version ranges: a selection surface widened silently is a selection nobody made.

4. **M9's item O3 is restated** as: *every application's declared range for every suite package
   resolves at both ends and passes its contract and e2e suites, proved by the compatibility
   matrix.* That is the property O3 was reaching for; "the 1.0 packages" was the shorthand of a
   roadmap written when 1.0 was assumed to arrive first.

5. **Suite 1.0 does not require any package to be at 1.0.** An application at `1.x` depending on a
   `0.x` package is deliberate, honest and pinned — §6 already said so in its last paragraph, and
   this record makes it the operative rule rather than a caveat under a table that promised
   otherwise. `gold-standards` §4's parenthetical restricting suite 1.0 to nine components is
   removed in the same commit.

## Alternatives considered

* **Bump all ten to 1.0 now, as the trajectory table promises.** Ten release commits, ten tags, ten
  PyPI environment approvals, four application releases to widen every ceiling from `<0.5`-shaped
  to `<2`-shaped, four lock recompiles — and at the end, less assurance than we have today, not
  more. Every current pin is a range that CI has actually installed; every widened pin would be a
  range nothing had ever resolved, widened in the same week the matrix that would check it was
  still unwritten. It would also make a stability promise about `setspec` and `modelrack` four days
  after both took a minor, and about ToolYard on the strength of one consumer.

* **Bump only the packages whose payloads are frozen — that is, SetSpec.** Tempting and wrong: the
  frozen thing is SetSpec's **payload schemas** at `MAJOR.MINOR` per payload
  ([ADR-0009](0009-setspec-schema-strategy.md)), not the `setspec` **package surface**. Those are
  different objects with different version series, which is exactly why
  [ADR-0068](0068-a-post-freeze-minor-is-a-sibling-class.md) had to rule on what a post-freeze minor
  is. Since the freeze the package has shipped `0.5.0` (`governance.egress_decision`, the adapter
  manifest) and `0.6.0` (evidence bundle 1.1). Making the package version claim the payloads'
  stability would put the lie precisely where the freeze exists to prevent one.

* **Leave the trajectory table alone and treat it as aspirational.** Rejected because it is not read
  that way. A bold **1.0** in a column headed M9 is a commitment; the audit read it as one, could
  not close O3 against it, and escalated. A roadmap whose tables need a verbal disclaimer to be
  understood has stopped being a roadmap.

* **Define 1.0 by elapsed time or by consumer count alone** ("two consumers and three months").
  Rejected: both are proxies for the thing that matters, which is that the surface stopped changing
  under load and that the declared ranges have been resolved. Condition (i) measures the first
  directly and condition (ii) measures the second directly; a count of consumers is already implied
  by (ii), since every consumer's range must be proved at both ends.

## Consequences

* M9 becomes walkable. Its one unanswerable item is now a property row L6's matrix produces, and no
  part of the milestone waits on ten releases nobody has argued for individually.
* The suite ships four `1.x` applications on ten `0.x` packages, indefinitely and on purpose. Anyone
  reading `freeweight 1.1.0` beside `baseaicore 0.4.2` needs that explained where they are reading
  it, so `master-roadmap` §6 now carries the explanation rather than a table that contradicts it.
* Each package's 1.0 becomes a small, provable, per-repository step instead of a suite-wide event —
  and each one arrives with the matrix already green for it, because (ii) is a precondition.
* The `<0.x+1` ceilings stay load-bearing, so a package minor still requires a deliberate consumer
  release. That is friction, and it is the friction that has kept every published combination
  installable so far.
* ToolYard's single consumer is now a stated fact rather than an assumed pair. It does not block
  anything today; it does mean ToolYard's surface has been reviewed by one caller, and condition
  (ii) is thin for it until a second arrives.

## Revisit when

* **Row L6's matrix has been green for one full release cycle and a package can show two quiet
  minors.** At that point that package's 1.0 is paperwork — a version bump, a changelog line and a
  tag — and this record's job is done for it.
* **A package acquires a consumer outside the suite.** An external consumer cannot read our
  ceilings, cannot be released in lockstep, and cannot be told that `0.x` means "we will widen your
  pin for you". The kindness of `0.x` ends the day someone else depends on it, and the criteria in
  decision 2 should be re-argued against that person's needs rather than ours.
* **The operator overrules decision 1.** Then decision 2 is what the bump has to satisfy — or be
  explicitly waived in a superseding record that says which of (i) and (ii) it is waiving and why.
