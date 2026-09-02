# ADR-0066 — Residency is two-level: the base is the expensive switch, the adapter is free

**Status:** Accepted (2026-09-02)
**Extends:** [ADR-0038](0038-one-model-at-a-time-per-gpu.md) (fit with room for context, or wait),
[LoadCoach Queue and Scheduling §5–6](../apps/loadcoach/queue-and-scheduling.md) (admission and
residency), [Adapter Identity and Serving §8](../architecture/adapter-identity-and-serving.md).
**Relates to:** [ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) (one base
per process — the fact that makes residency two-level),
[ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) (scoring, of which
residency is one adjustment factor).
**Source:** [Adapter roadmap §2, A-9](../roadmap/adapter-roadmap.md).

## Context

LoadCoach's scoring has always had one residency question — *is this model already loaded?* — because
until now there was one kind of switch and it was expensive. Adapter serving splits that question in
two, because the machine's cost surface now has two very different events on it:

* **Selecting a different adapter on the running base** costs nothing. The process does not restart,
  the weights do not move, and the base stays warm — this is the entire point of the arc.
* **Serving a different base** means terminating a `llama-server` process and spawning another with
  a different multi-gigabyte GGUF. It is the expensive event, and with a few bases and many adapters
  the router should camp on one base rather than oscillate.

A router that models these as one cost gets both wrong. Treating an adapter switch as a model switch
makes the free thing look expensive — the router would pay a phantom penalty to avoid something that
costs nothing, and might route away from the adapter with the best evidence for no reason. Treating a
base switch as free makes the expensive thing invisible, and the queue thrashes.

There is also a memory question ADR-0038 already owns. Its arithmetic asks whether a model fits with
room for its context, and registered-but-inactive adapters occupy VRAM inside the base's process. If
admission does not count them, it will say "it fits" and the card will not.

## Decision

**Residency is the pair `(resident base process, registered adapter set)`, and the two levels are
scored differently.**

1. **A candidate on the resident base, with any registered adapter, is resident.** The existing
   `prefer_resident_bonus` applies unchanged; switching adapters is free and is scored as free.
2. **A candidate requiring a different base carries a configurable `base_switch_penalty`.** A
   process restart is the expensive event, and the penalty is what makes the router camp on a base.
   It is configuration with a documented default, not a constant, because its true value depends on
   model size, storage speed and the machine.
3. **A per-request `ignore_residency` override zeroes both terms** for that call, and is recorded in
   the explanation like every other override. "Use the absolute best model and pay the swap" is one
   flag, and it is traceable.
4. **[ADR-0038](0038-one-model-at-a-time-per-gpu.md) is restated, not weakened: the *base* is the
   unit that must fit**, and registered adapters count toward its footprint. The estimate is measured
   at LA1 rather than assumed, and admission subtracts it like any other occupancy.
5. **IdeaPress's serialise-and-unload rule learns the same distinction.** Its obligation is to never
   hold two models; a per-stage *adapter* change on one base is not a model switch and must not
   trigger an unload. Without this, three pinned adapters across three stages would produce three
   base loads — the exact thrash the arc exists to remove, reintroduced by a rule meant to prevent a
   different one.

## Alternatives considered

**One-level residency: treat every subject as its own residency unit.** No change to LoadCoach's
scoring at all, and it is trivially consistent — a subject is either loaded or it is not. Rejected
because it makes the free operation look expensive: an adapter switch on the warm base would score
as a cold model, so the router would prefer a *worse-measured* subject to avoid a cost that does not
exist, and the arc's headline property (zero base loads across alternating adapters) would be
invisible to the component whose job is to exploit it.

**Drop residency from adapter scoring entirely** — treat all subjects on a machine as equally
available and let admission sort it out. Simple, and it removes a tunable. Rejected: residency is a
real signal about the *base*, and removing it makes base thrash invisible to scoring, which is the
failure the penalty exists to prevent. The fix for "adapters shouldn't pay a penalty" is to model two
levels, not to delete the level that is real.

**Make `base_switch_penalty` a fixed constant.** One fewer knob, one fewer thing to get wrong.
Rejected: the cost of a base switch is a function of model size, disk throughput and GPU, and the
suite's pattern for hardware-dependent values is a documented default that a deployment can measure
and change — as `vram_headroom_bytes` already is.

**Ship no `ignore_residency` override.** Every override is a way to defeat the optimizer and a thing
the explanation must account for. Genuinely arguable — the router exists precisely so callers do not
have to make this decision. Rejected because the need is real and the alternative is worse: without
the flag, a user who needs the best available model for one important call has no route but to stop
the queue, unload by hand, and try again. An override that is recorded, explained and per-request is
strictly better than an operator working around the router.

**Count registered adapters as free memory.** They are small relative to a base, and ignoring them
keeps ADR-0038's arithmetic unchanged. Rejected: "small" is not "zero", the count grows with the
number of registered adapters, and an admission check that under-counts occupancy says "it fits"
about a card that then degrades to CPU or OOMs — the silent failure ADR-0038 was written to end.

## Consequences

* LoadCoach 1.1's scoring gains one new term and one new configuration key. Candidate expansion,
  filtering and ranking are otherwise unchanged, which is what keeps this affordable inside a
  released application.
* Explanations must now distinguish "resident base, different adapter" from "different base" so a
  user can see why one candidate was cheap and another expensive. The residency line in the
  explanation names the base, not just the subject.
* Integration verification I16 is the proof: twenty alternating-adapter generations with **zero base
  loads**, asserted from the process table and load timings, then the IdeaPress three-stage project
  with exactly one base load.
* IdeaPress's `[execution] unload_before_model_switch` behaviour becomes adapter-aware. That is a
  small change to a 1.0 application and it is the difference between the motivating demo working and
  it thrashing.
* Admission is slightly more conservative than before on adapter-serving bases, because the
  registered set counts. On a 16 GB card with a large base, a long adapter list can be the difference
  between fitting and waiting — which is the honest answer, and is measured rather than guessed.

## Revisit when

**Multi-GPU residency** changes the cost surface — two bases warm on two cards makes "the resident
base" a per-device fact, and the camping heuristic that a single penalty encodes stops being the
right shape. [ADR-0027](0027-multi-gpu-semantics.md)'s per-device rules would then govern residency
as well as measurement, and the penalty becomes a placement decision rather than a scalar.
