# ADR-0083 — An adapter pin is configured on by being configured

**Status:** Accepted (2026-09-05)
**Extends:** [ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) rule 4
(pinned selection uses `model`-override semantics),
[LoadCoach Routing §10](../apps/loadcoach/routing.md) (the override table).
**Relates to:** [ADR-0040](0040-routing-backend-owns-model-choice.md) (the routing backend owns
model choice), [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the execution
subject gains an adapter axis),
[ADR-0081](0081-an-adapter-subject-inherits-no-evidence-from-its-base.md) (an adapter subject
inherits no evidence from its base, so a pin is how an adapter is used until LA3).
**Source:** Row H3, decision 2 of its kickoff §0.3.

## Context

IdeaPress already has a per-stage **model** binding, `[models.stages]`, and it already has a switch
that decides whether that binding is sent to LoadCoach at all:
`[inference.loadcoach] honour_stage_bindings`, off by default. The switch exists because
[ADR-0040](0040-routing-backend-owns-model-choice.md) gives model choice to the routing backend —
sending a model override *is* giving up routing, so an operator has to ask for it.

H3 adds a per-stage **adapter** pin. The obvious economy is to hang it off the same table and the
same switch: one binding per stage, one boolean, no new configuration surface. That economy is
wrong in both halves, and the reason is the same in both: it would make the configuration say
something that is not true.

An adapter pin does not surrender routing.
[LoadCoach Routing §10](../apps/loadcoach/routing.md) is explicit: *"`adapter` without `model` is
legal and means 'this adapter, on whichever base can serve it': the compatible bases are scored
normally and the pin selects among their adapter subjects."* Routing still ranks the bases, still
applies every hard constraint, still pays the residency and reliability terms. What the pin removes
is the choice **within** a base — which is a choice the router would rarely make anyway, because an
adapter subject inherits no evidence from its base
([ADR-0081](0081-an-adapter-subject-inherits-no-evidence-from-its-base.md)) and therefore ranks
below a measured base until LA3's evidence exists. A pin is how an adapter gets used at all.

So `honour_stage_bindings`, whose documented meaning is "give up routing", is the wrong flag: an
operator who set it to get their house-voice LoRA would also, silently, be pinning the model and
losing evidence-driven selection for that stage.

A *new* default-off boolean is no better. A configured pin behind an unset boolean is precisely the
silent no-op that IdeaPress's `job_stages` validator exists to prevent — in that validator's own
words, "the same silent-no-op the `[models.stages]` startup check exists to prevent". An operator
who wrote an adapter name into a configuration file and got the base's prose back has been lied to
about what produced their document.

## Decision

**A per-stage adapter pin lives in its own configuration table, and configuring a pin is
configuring it on. There is no second boolean.**

1. **Its own table.** `[models.stage_adapters]`, beside `[models.stages]` and shaped like it: one
   key per stage, spelled exactly as [Workflows §2](../apps/ideapress/workflows.md) spells it. It is
   **sparse** — a stage with no key has no pin — which is the one shape difference from
   `[models.stages]`, whose completeness over the model-using stages is itself a checked property.
2. **A key present is a pin in effect.** Wherever the table sets a stage, that stage's request
   carries LoadCoach's `adapter` override. No flag gates it, in either direction.
3. **A pin that cannot apply is refused at startup, by name.** A key naming a gate stage or an
   unknown stage is refused the way `job_stages` refuses one. Any key at all is refused when
   `[inference] mode` is not `loadcoach`, because the direct and OpenAI-compatible paths are
   adapter-free by recorded scope decision
   ([adapter roadmap §4.4](../roadmap/adapter-roadmap.md)) and an adapter through an
   OpenAI-compatible endpoint would evade identity tracking entirely.
4. **A pin that cannot be honoured at run time fails its stage, with the refusal surfaced**
   ([ADR-0064](0064-adapters-are-selected-through-the-capability-vocabulary.md) rule 4). It is never
   quietly served by the bare base.
5. **Both pins set is the one case where an adapter pin does surrender routing** — because the model
   pin already did. With `honour_stage_bindings` on *and* a `[models.stage_adapters]` key present,
   the model pin narrows the field to one base and the adapter pin selects among that base's
   subjects, naming exactly one subject. That combination is legal, documented and recorded on the
   attempt; it is simply not what either key means on its own.

## Alternatives considered

**Ride `honour_stage_bindings`.** One less key, and it reads plausibly — both are "the operator
naming something specific". Rejected because the flag's documented meaning is the *consequence* of a
model pin, not the act of pinning, and an adapter pin does not have that consequence. A flag whose
name and documentation describe a trade the operator is not making is worse than an extra key.

**A new `honour_stage_adapters` boolean, default off.** Symmetrical with the model case and
therefore tempting. Rejected: the symmetry is false. `honour_stage_bindings` is off by default
because the *default* behaviour (let LoadCoach route) is the better one and the override is the
exception. There is no equivalent better default for an adapter: an unpinned stage already gets one
— it simply has no adapter — so a default-off boolean adds no behaviour, and its only effect is to
make a configured pin do nothing until a second key is found. Rule 3's startup refusals give an
operator the same protection without the silent state.

**One table with a compound value** (`draft = "ollama/gemma4:12b+house-voice"`). Rejected: it welds
two independent choices into one string, makes "this adapter on whichever base can serve it"
inexpressible, and would need a parser where two tables need none.

## Consequences

* IdeaPress's `[models]` section gains exactly one key, and the existing one is untouched: a shipped
  `1.0` configuration file loads to a byte-identical settings object, which is asserted rather than
  argued.
* An operator can pin an adapter without giving up routing, which is the case the LA2 contract was
  built for and the case the three-stage demonstration exercises.
* An operator who wants one exact subject sets both keys and is told, in the spec and on the
  attempt, that they have pinned the model too.
* Startup refuses more configurations than it did — a pin on `validate`, a pin in `ollama` mode —
  each naming the key and the reason. That is the intended cost; the alternative is a stage that
  runs without the adapter its configuration names.
* Nothing here gives IdeaPress an adapter registry. The names in this table are LoadCoach's manifest
  names, resolved by LoadCoach, and an unknown one is `ADAPTER_NOT_FOUND` at run time listing what
  does exist — not a startup error, because IdeaPress does not own that list and must not cache it.

## Revisit when

LA3's evidence lands and adapter subjects can be *routed* to rather than only pinned. At that point
"pin this adapter" and "prefer adapter-bearing subjects for this stage" become different requests,
and the second one needs a key this record does not describe.
