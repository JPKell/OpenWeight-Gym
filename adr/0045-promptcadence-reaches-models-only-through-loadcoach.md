# ADR-0045 — PromptCadence is a fourth application, and it reaches a model only through LoadCoach

**Status:** Accepted (2026-09-02)
**Extends:** [Master Architecture §1.1, §2, §3 and §8](../architecture/master-architecture.md)
(the component table, the dependency graph, ownership, deployment).
**Relates to:** [ADR-0001](0001-application-and-package-separation.md) (what an application is),
[ADR-0011](0011-shared-package-boundaries.md) (extraction at the second consumer — the ThreadRack
rejection below), [ADR-0040](0040-routing-backend-owns-model-choice.md) (a routing backend owns
model choice), [ADR-0054](0054-spotcheck-records-egress-it-does-not-enforce-it.md) (the egress
record this design exists to make possible).
**Source:** [PromptCadence roadmap §2, D-1](../roadmap/promptcadence-roadmap.md).

## Context

The PromptCadence arc adds a plan-approved, tier-routed agent loop. Where it lives is the first
decision, and it constrains everything after it.

The suite's shape is three applications over six packages, with a rule that arrows point downward
and never sideways. A harness is unmistakably application-shaped: it owns a database, a queue with
leases, an approval workflow, an operator UI, a public API and a retention policy. But it is also
the first component whose *whole purpose* is governance — it exists so that "what model ran this,
on what data, at what cost, under whose approval" has an answer — and that purpose is only as good
as the number of paths by which a request can reach a model.

IdeaPress's precedent pulls the other way and has to be reckoned with. Its product guarantee is
that a complete workflow runs with LoadCoach absent, so it ships a direct-provider backend behind
its inference port and a stage runs identically either way. Consistency would suggest the same for
PromptCadence.

It cannot have it. PromptCadence's tiers are *defined over* LoadCoach: a tier is a task profile
plus an egress class plus a classification ceiling, and "which model within the tier" is
LoadCoach's filter → score → rank. A direct-provider fallback would have to answer that question
itself — routing math this application's non-goals forbid it — and the resulting path would be the
one place a request could reach a provider without a tier, without a routing decision, and without
an egress verdict. The application whose reason for existing is a governed egress path would ship
with an ungoverned one.

There is also a package question the design skeleton raised and could not settle: thread and turn
state looks generic enough to extract as `ThreadRack`, and the skeleton flagged that it alone had
no second consumer.

## Decision

**PromptCadence is a fourth top-level application. Every model call it makes goes through
LoadCoach's HTTP API, and no other path to a provider exists in it.**

1. **Layer 4, beside the other three.** Import and distribution name `promptcadence`, default port
   **8768**, env prefix `PROMPTCADENCE_`, its own `promptcadence.sqlite3`, its own Alembic history,
   the same `web`/`cli`/`services`/`domain` internal shape. It imports no application and no
   application imports it.
2. **It does not depend on ModelRack, and it does not depend on SweatMeter.** Their absence is a
   contract, enforced by `.importlinter` and asserted in the spec, not an accident of what it
   happens to need today. ModelRack is the suite's only provider client, so *not importing it* is
   the mechanical form of "there is no second egress path". Telemetry is displayed from LoadCoach's
   `/system/status`, exactly as IdeaPress treats it.
3. **LoadCoach is required for execution, never for startup.** PromptCadence starts, serves its API
   and UI, and accepts trajectories with no LoadCoach reachable; health reports degraded and
   submitted work parks with `LOADCOACH_UNAVAILABLE` as its recorded reason. What it does not do is
   execute around the outage.
4. **There is no direct-provider fallback mode.** This is the deliberate divergence from IdeaPress
   and the reason for it is stated in the spec's non-goals: a harness with direct provider access
   would own a second, ungoverned egress path, which is exactly what this application exists to
   prevent.
5. **`ThreadRack` is not created.** Thread and turn state has one consumer, and
   [ADR-0011](0011-shared-package-boundaries.md) rule 4 says nothing is extracted with fewer than
   two. It is built as `promptcadence/domain/threads.py` and its store **package-shaped** — no
   PromptCadence vocabulary in the types — so that extraction is a move rather than a rewrite when
   a second consumer appears. Recorded here as a deliberate rejection, the way `LoadCoachClient`
   was.

## Alternatives considered

**Build the harness inside LoadCoach**, as a fourth subsystem beside routing, the queue and
execution. Genuinely the strongest alternative: LoadCoach already owns a lease-based queue with
recovery edges, admission control, auth with scopes, an explanation store and an operator UI, and a
harness is a loop above exactly those. It would ship sooner and share the machinery outright.
Rejected because it would put tool execution and transcript state inside the component that
deliberately executes no tools and holds no conversation. LoadCoach's ownership row denies it
content workflows, exactly as IdeaPress's denies it routing. The router would acquire the suite's
riskiest behaviour, and every LoadCoach release would then carry an agent loop's blast radius. A
component that must stay a router stays a router.

**Give PromptCadence a direct-provider fallback, mirroring IdeaPress.** Consistency, and a real
product benefit: the harness would work on a machine with only Ollama. Rejected on rule 4's
reasoning — the fallback path has no tier, and inventing one means inventing routing. The honest
version of "works without LoadCoach" here is "parks with a reason", and the spec says so as
specified behaviour rather than as a gap.

**Ship it as a package — an agent-loop library applications embed.** Attractive for reuse, and it
is how most harnesses are distributed. Rejected: it owns a database, a queue, an approval workflow
and a UI, and [ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md) now forbids a
package owning an application's migration history. A library shaped like this is an application
that has hidden its ownership.

**Extract `ThreadRack` as a fifth package now**, since the arc is creating four anyway and thread
state is plainly generic. Rejected: one consumer. The `LoadCoachClient` precedent is exact — an
unstable surface published for a single caller — and the roadmap folded ThreadRack in specifically
to hold the line against package sprawl, which is a named risk of this arc.

**Import SweatMeter for the telemetry widget.** Small and convenient. Rejected: it buys a
dependency for a display, and IdeaPress already established that a consumer of telemetry it does
not measure reads it over HTTP from the component that does.

## Consequences

* The suite becomes four applications and ten packages after this arc, and master architecture §1.1,
  §2, §3, §8 and §11 are amended accordingly (this record is the amendment vehicle, per the
  [ADR-0038](0038-one-model-at-a-time-per-gpu.md) precedent).
* **Every generation PromptCadence performs is a LoadCoach job**, so every one of them has a
  routing decision, a recorded explanation and a job id the trajectory can link to. The
  explainability contract is inherited rather than rebuilt.
* PromptCadence is the first application that is *useless* without a peer. That is a real product
  cost — a user who installs it alone can start it, browse it and submit work that never runs — and
  the degradation is specified: parked, with a reason, visible in health.
* Remote tiers additionally need LoadCoach's multi-provider registration
  ([ADR-0055](0055-loadcoach-registers-providers-by-name-and-kind.md)); until it lands they report
  `TIER_UNAVAILABLE` with `loadcoach_has_no_remote_provider`. Specified behaviour, not a defect.
* Thread state stays application-internal and is written under a self-imposed package discipline
  that nothing enforces but review. If the extraction ever happens, that discipline is what makes it
  cheap; if it never happens, the cost was a naming convention.
* Master architecture §11 gains **"direct provider access from PromptCadence"** as a forbidden
  item, with `.importlinter` as its check — the rule is mechanical, not aspirational.

## Revisit when

* **A deployment must run PromptCadence with no LoadCoach at all** — at which point the decision to
  reopen is not "add a fallback" but "what does a tier mean without a router", and the answer needs
  its own record.
* **A second consumer of thread state appears** — extract `ThreadRack` then, from working code with
  two callers, exactly as WeightsDB and MirrorWall were extracted.
