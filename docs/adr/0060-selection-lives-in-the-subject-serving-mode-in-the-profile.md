# ADR-0060 — Adapter selection lives in the subject; adapter serving mode lives in the runtime profile

**Status:** Accepted (2026-09-02)
**Extends:** [ADR-0023](0023-runtime-profile-resolution.md) (the runtime profile and its hash),
[Adapter Identity and Serving §3](../architecture/adapter-identity-and-serving.md).
**Relates to:** [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the other half of
the split), [ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md) (why the separation
has to be exact), [ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md)
(registration is a launch-time property, which is what makes serving mode a profile fact).
**Source:** [Adapter roadmap §2, A-3](../roadmap/adapter-roadmap.md).

## Context

Two different facts about an adapter-capable deployment look alike and are not:

* **Which adapter this request runs under** — a per-request choice that costs nothing to change.
* **Whether the server was launched with adapters registered at all** — a property of the process,
  fixed until it restarts.

Conflating them corrupts evidence in a way that is hard to see afterwards. A base model measured on
a server that has four LoRAs registered is not obviously the same measurement as the same base on a
clean server: registered-but-inactive adapters occupy memory, and the serving path differs. If both
facts live in one place, a base's numbers from an adapter-enabled deployment silently merge with its
numbers from a clean one, and the merged figure describes neither.

The suite already owns the machinery for the second fact.
[ADR-0023](0023-runtime-profile-resolution.md) exists because context size, KV precision, offload
and flash attention change what a measurement means, and it hashes them into `runtime_profile_hash`
so measurements taken under different settings are kept separate rather than averaged. Whether
adapters were registered at launch is a setting of exactly that kind.

What nobody knows is how large the difference is. The expectation — memory-only for
registered-but-inactive adapters, low single-digit percent decode cost for an active one, roughly
proportional to rank — is a belief about llama.cpp's implementation, not a measurement of this
deployment's hardware.

## Decision

**The two facts live on two different axes of the subject, and the split is exact.**

Both facts end up inside the measurement subject — `runtime_profile_hash` is one of its three
components — so the distinction is not *inside versus outside*. It is **which axis**, and that
matters because the axes have different properties: the adapter axis is named and per-request, the
profile axis is hashed and per-process.

| Fact | Which axis | Why that one |
|---|---|---|
| **Adapter selection** — which adapter this request runs under | Its own axis on the subject ([ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md)) | It changes the weights' behaviour, it is the thing being measured, and it must be **nameable** — pinned, weighted, displayed |
| **Adapter serving mode** — the server was launched with adapters registered | Folded into `runtime_profile_hash` ([ADR-0023](0023-runtime-profile-resolution.md)) | It is a runtime setting like KV precision or flash attention, fixed for the process; it needs to **separate** measurements, not to be named |

1. **Adapter-enabled serving is a runtime-profile field**, hashed with the rest. Two measurements
   of one base under different serving modes are two subjects, shown side by side, never merged —
   the existing ADR-0023 behaviour, with nothing new taught to it.
2. **It is the configuration default for llama.cpp tiers**, overridable per runtime profile.
   Configuration, not code, so the default can be flipped without a release when evidence justifies
   it.
3. **The overhead is measured, not assumed.** FreeWeight can benchmark `base @ clean-profile`
   against `base @ adapters-registered-profile` as two ordinary subjects, answering the question
   empirically on the deployment's own hardware. The A/B is run **once per base + profile**, not per
   adapter ([ADR-0059](0059-adapter-evidence-is-measured-never-inherited.md)), because the fact
   belongs to the base and its profile.

## Alternatives considered

**Give serving mode its own named axis beside the adapter**, rather than folding it into the profile
hash. It would make the fact visible in the canonical string, which has some appeal: an operator
could see at a glance that a measurement came from an adapter-enabled server. Rejected: serving mode
is a runtime setting, indistinguishable in kind from KV precision or flash attention, and the suite
has exactly one place for those. A second home for runtime settings would leave
`runtime_profile_hash` describing some of a server's configuration but not all of it — which is
worse than either whole answer — and it would grow the canonical string for a fact nobody pins,
weights or selects on.

**Put both facts in the profile** — no subject axis at all, adapters distinguished only by profile
hash. Rejected in [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md): a hash separates
without naming, so three adapters would be three unlabelled hashes that no UI could display, no task
profile could weight and no caller could pin.

**Assume the overhead is negligible and model neither** — always register adapters, one profile,
no A/B, no extra subjects. Genuinely defensible: `--lora-init-without-apply` means an inactive
adapter costs memory rather than compute, and the decode cost of an active low-rank adapter really
is small. Rejected because "is expected to be small" is a belief, and the suite's entire premise is
that beliefs about model performance are measured rather than asserted. The asymmetry decides it:
modelling the fact costs one profile field and nothing at runtime, while not modelling it means
that *if* the overhead is ever material, every base measurement taken on an adapter-enabled server
was silently attributed to the clean base, and nothing in the record would reveal it.

**Make adapter-enabled serving a code-level default** rather than configuration. Rejected: runtime
profiles are configuration by ADR-0023, and this record's own revisit trigger is "flip the default",
which is only a cheap action if it is a configuration change.

**Register adapters lazily, on first use, so a clean server stays clean until an adapter is
requested.** This would make serving mode a runtime state rather than a launch property, and the
question would dissolve. Rejected because it is not available:
[ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) records that llama.cpp
registers adapters at launch, which is exactly why serving mode is a property of the process and
therefore of its profile. If that changes, this record's premise changes with it.

## Consequences

* A deployment that turns adapter serving on gets a new `runtime_profile_hash` for its bases, and
  its pre-existing evidence for those bases does not transfer to the new profile. That is
  ADR-0023's rule working as designed, and it will look like evidence loss to an operator — the
  explanation says which profile the evidence was measured under and why it does not apply.
* FreeWeight 1.1 gains one A/B measurement per base + profile, which is small and answers a question
  the whole arc rests on: whether adapter-capable serving costs anything worth avoiding.
* The result feeds a real decision. If the overhead is negligible, adapter-enabled serving stays the
  default and a deployment never thinks about it; if it is material, the default flips and adapters
  become an opt-in per profile — see below.
* ModelRack's `LlamaCppProvider` must include the registration state in the profile it reports, so
  the hash reflects reality rather than intent. A server launched without adapters because
  registration failed must not report the adapter-enabled profile.

## Revisit when

The measured serving-mode overhead proves **material on reference hardware** — at which point the
default flips to clean serving, and adapter-capable profiles become an explicit per-tier opt-in.
This is a configuration change plus a documentation change; the split between subject and profile
does not move.
