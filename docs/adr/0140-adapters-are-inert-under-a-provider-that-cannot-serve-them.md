# ADR-0140 — A configured adapter directory is inert, not fatal, under a provider that cannot serve one

**Status:** Accepted (2026-09-11)
**Extends:** [ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md) rule 2 (empty
means off), [ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (an adapter is refused
by name, never replaced by its base).
**Relates to:** [ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) (llama.cpp is the
one kind that serves an adapter), [ADR-0074](0074-adapter-enabled-serving-is-a-runtime-profile-field.md)
(the serving mode is a profile field the composition root sets),
[ADR-0117](0117-provider-registrations-are-edited-in-place-in-the-config-file.md) rule 2
(validate before write).
**Source:** row WPF2, from [WP6's findings 4 and 9](../history/handoffs/WP6_HANDOFF.md).

## Context

ADR-0061 rule 2 says an empty `[adapters] directory` means the feature is off. It says nothing about
a *set* directory under a provider that cannot apply a LoRA at all, and the code answered the
question by accident: `OllamaProvider.register_adapters` exists and always raises
`CAPABILITY_UNSUPPORTED`, so FreeWeight's composition root — which offers the directory's available
entries to whatever provider it just built — turned the combination into a hard failure.

On the reference machine (2026-09-11) that failure arrived in the worst possible order. The operator
switched FreeWeight's provider back to `ollama` from the console's Provider page with
`[adapters] directory` set. FreeWeight refused the switch in its own words — *This provider does not
declare 'adapter_hot_swap' and cannot register an adapter* — **after** it had already rewritten
`config.toml` to `ollama` and moved the previous file to `config.toml.bak`, because the refusal came
from re-opening the provider, which happens after the write. `freeweight config validate --file`
then called the rewritten file *valid*, since loading the document is not the same check as
constructing the provider. The next restart would have started FreeWeight on the combination it had
just refused, and the running process was left with a closed HTTP client its own scheduler still
held (WP6 finding 9, the separate defect this row also fixes).

So there were two questions, and only the first is architectural: **is a configured adapter
directory under a non-serving provider a refusal, or a state?**

## Decision

**It is a state: the directory stays configured, is read, is listed, and is offered to nobody. The
refusal moves to the point where it changes an answer — a run that names an adapter.**

1. **The capability decides, not the kind.** FreeWeight asks the constructed provider
   (`capabilities().adapter_hot_swap`, `services.adapters.can_serve_adapters`) rather than testing
   `provider.kind`. A provider that gains the capability needs no change here.
2. **Registration is skipped, the directory is still read.** The composition root reads the
   directory whatever the provider is — a typo in the path is refused on every kind, which is
   ADR-0061 rule 5's fail-closed applied one level up — and offers nothing to a provider that
   cannot serve one. It is not an error and not a warning that stops anything.
3. **The serving mode stays honest.** `RuntimeProfile.adapters_registered` is already `None` on such
   a provider (ADR-0074 rule 3: "the provider has no concept of adapters"), so no run's
   `runtime_profile_hash` moves and no evidence changes meaning.
4. **A run naming an adapter is still refused by name** (ADR-0058), with the registered set in the
   message. Inert never means "quietly measured the base".
5. **Every surface that lists adapters says which it is.** `GET /adapters` carries
   `provider_can_serve` (`true`, `false`, or `null` when no provider was asked);
   `freeweight adapters list` prints the same fact above the listing. "The adapter I dropped in is
   not being used" is the confusion ADR-0061 exists to prevent, and an inert directory is that
   confusion one level up.
6. **`config validate` and startup agree**, because there is nothing left for startup to refuse that
   the loader does not already refuse. This is what makes the combination checkable before a
   restart rather than after it.

## Alternatives considered

* **Refuse the combination at `config validate` and on the Provider page.** Symmetrical with the old
  behaviour and it would have caught WP6's write — but it makes the operator edit two blocks to
  change one, keeps a legal configuration that the application cannot start on, and puts a
  capability check in the configuration loader, which reads no provider today. Rejected.
* **Refuse the provider *edit* only, allowing the same file at startup.** Two answers to one
  question, decided by which door you came through. Rejected.
* **Unset the directory on the operator's behalf.** An application that edits configuration the
  operator did not ask it to edit is worse than either answer. Rejected.

## Consequences

* FreeWeight starts on `ollama` with an adapter directory configured, lists the adapters as present
  and inert, and refuses `run start --adapter` by name. Switching back to `llamacpp` needs no
  configuration change beyond `kind`.
* ADR-0117 rule 2 gains teeth: the provider write is validated by *constructing* the provider the
  candidate file names before the rename, so everything the re-open can refuse is refused with the
  file untouched, `.bak` included. That is a fix, not a new rule.
* A `provider_can_serve: false` answer is a new fact for WeightRoomGym: its Runs page offers the
  adapter field only where an adapter can actually be served, and its Adapters page says why the
  list is inert.
* The operator's chosen configuration (llama.cpp with adapters on, 2026-09-11) is unaffected.

## Revisit when

A provider other than llama.cpp declares `adapter_hot_swap`, or an operator has a reason to want a
*refusal* rather than an inert directory — for instance a fleet where "adapters configured" is
meant to be a hard assertion that they are being measured. The check would then belong in `doctor`,
which already exists to say that a configuration is legal but not what its author intended.
