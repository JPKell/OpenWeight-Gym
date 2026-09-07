# ADR-0111 — The container rung is proved on docker, and podman is not an exit condition

**Status:** Accepted (2026-09-07)
**Amends:** [Outstanding work §4 and §5](../roadmap/outstanding-work.md) (the M11 exit condition
that named a podman host), [ToolYard spec §7](../packages/toolyard/spec.md) (the ladder's first
rung is unchanged in code; what changes is what counts as having exercised it).
**Relates to:** [ADR-0018](0018-external-benchmark-isolation.md) (tiered sandboxing),
[ADR-0056](0056-a-tool-runs-in-the-strongest-tier-the-host-can-supply.md) (the tier ladder,
container → bwrap → refuse).
**Source:** the operator's decision at the 2026-09-07 interview, asked because no podman host has
ever been available and the item had blocked M11's declaration since E2.

## Context

ToolYard's `TieredSandbox` probes for a container runtime first and prefers podman when both are
installed, because rootless podman is the stronger default on a workstation. The reference machine
has docker only. Row E4 exercised the container rung through docker; rows D1 and E2 shipped the
ladder with the podman branch covered by unit tests over a faked runtime and by nothing live. The
schedule turned that into a **blocking** M11 exit condition — `pytest -m isolation -rs` green on a
real podman host — and the beta (`promptcadence 0.9.0b0`, row G1) and the 1.0 (row I2) both shipped
with the item open. Three days later nothing had changed: there is no podman host, none is planned,
and the item was the one line keeping M11 formally undeclared while everything M11 named was in
production use.

## Decision

1. **M11's exit condition is the container rung exercised live on the reference machine's
   runtime**, which is docker. It has been met since E4 (2026-09-04); M11 is declared as of this
   record.
2. **The ladder does not change.** `TieredSandbox` still probes podman first; a host that has it
   uses it. What this record refuses is the claim that the *first* runtime in the probe order must
   be proved before the ladder counts as proved — the property the ladder guarantees is "the
   strongest tier the host can supply" (ADR-0056), and that property was demonstrated on the
   strongest tier this host supplies.
3. **The podman branch stays covered by the faked-runtime tests and by one honest skip.** The
   `isolation` marker's skip message names the runtime it wanted; a CI run shows the skip, visibly,
   as today. A skip is not a pass and is not claimed as one.
4. **The first podman host runs the canary before it runs anything else.** `pytest -m isolation
   -rs` on that host is a §4 checklist item for whoever first installs podman beside the suite,
   and its result goes into the ToolYard changelog. Until then the podman rung is *unexercised*,
   which the spec and the roadmap say plainly rather than leaving a milestone hostage to it.

## Alternatives considered

* **Keep the condition and leave M11 undeclared.** Honest about podman, dishonest about M11: the
  beta was cut, the 1.0 shipped on top of it, and the operator's walkthrough reads a roadmap whose
  milestone map says a delivered milestone is open for a reason no one can act on.
* **Provision a podman host to close it.** Rejected for now: the reference machine is one machine,
  docker is what its other tooling uses, and a second runtime installed only to satisfy a test is
  a test of the installation rather than of the suite. Decision 4 keeps the canary for the day a
  podman host exists for its own reasons.
* **Demote podman below docker in the probe order.** Rejected: the order encodes a preference for
  rootless containment, which is right; the problem was the exit condition, not the ladder.

## Consequences

* `outstanding-work.md` §4's podman bullet becomes a standing note, its §5 M11 row is marked
  declared, and the M11 line in `roadmap/promptcadence-roadmap.md` says the same.
* A newcomer reading ToolYard's spec learns that the podman branch has never run live. That is the
  true state, and it is better written down than implied by a milestone that never closed.

## Revisit when

* A podman host is installed beside the suite — run the canary, record the result, and if it
  fails, the fix is a ToolYard patch and this record's decision 3 is what changes.
* ToolYard adds a third container runtime to the probe order, at which point "proved on the
  reference machine's runtime" needs restating as "proved on at least one runtime per tier".
