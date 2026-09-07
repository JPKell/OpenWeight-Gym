# ADR-0106 — The `Provider` protocol carries the adapter inventory, and the `lora` field carries the complete set

**Status:** Accepted (2026-09-07)
**Amends:** [ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) decision 1
("**The `Provider` protocol does not change**"), which is narrowed to the load/unload seam it was
actually about; and [ADR-0063](0063-one-adapter-at-a-time.md) rules 1–2 ("at most one `lora`
entry"), which are read as governing **enabled** entries.
**Relates to:** [ADR-0007](0007-provider-abstraction.md) (the protocol whose method block this
grows), [ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md) (the directory that
supplies the set), [ADR-0066](0066-residency-is-two-level.md) (why a switch is free and therefore
per request), [ModelRack spec §7](../packages/modelrack/spec.md) (the normative method list, which
already carries both methods).
**Source:** Row F3's handoff §4 and §5, both put to the operator on 2026-09-04 and both confirmed
as built — §5 explicitly "without an ADR recording the expansion" and §4 "without amending the
ADR's wording"; and the 2026-09-07 ADR gap review, findings 1.2 and 2.3. This record is the
writing-down that was outstanding, not a reopening.

## Context

Two sentences written before `LlamaCppProvider` existed did not survive its building, and both were
confirmed rather than corrected at the time. Neither is a small drafting slip: each is the kind of
sentence a reader opens the record to find, and each is now false against the shipped tree.

**One — the protocol grew.** ADR-0062 decision 1 closes with "**The `Provider` protocol does not
change** — it already has exactly these methods, and that is the evidence the seam was drawn in the
right place." `modelrack.Provider` now declares `list_adapters()` (`provider.py:488`) and
`register_adapters()` (`provider.py:511`), beside `resolve()` and `list_resident()`, which ADR-0007's
eight-method block also predates. ModelRack spec §7 — the normative list — carries all of them.

The pressure that put them there is LoadCoach, not ModelRack. LoadCoach renders adapter rows,
explains a pin that is not taking effect, and folds a directory rescan into a running provider
(`services/adapters.py:229`, `infrastructure/providers/factory.py:254`). Every one of those reaches
an adapter inventory. With the methods on the concrete class only, LoadCoach must `isinstance`-check
`LlamaCppProvider` — importing a concrete adapter into an application that the protocol exists to
keep provider-agnostic, and doing it in the routing and registration paths of all places.

**Two — the wire sends every registered adapter.** ADR-0063 rule 1 says "The provider sends at most
one `lora` entry" and rule 2 "the single `lora` entry with `scale: 1.0`". `lora_field`
(`providers/_llamacpp_wire.py:589-623`) sends the complete configuration on every request to a
server that has adapters registered: the selected adapter at `1.0` and **every other registered
adapter explicitly at `0.0`**.

That is not a change of policy; it is what the policy costs against the actual server. F3 read
`b10792`'s `server-context.cpp` and found that an *absent* `lora` field takes the branch
`slot.lora = params_base.lora_adapters` — the **launch** set, restored without consulting
`lora_should_clear_cache`. `--lora FNAME` registers at `1.0` and `--lora-init-without-apply` only
skips applying at *init*; it does not zero the scales. So a bare-base request that sent no `lora`
field to an adapter-registered server would run with **every** registered adapter applied at `1.0`,
against a prompt cache built under whatever ran last — simultaneously a wrong-subject bug and the
composition ADR-0063 forbids, reachable by the most ordinary request there is.

## Decision

**Both readings stand, and are recorded here rather than left in a handoff.**

### 1. The adapter inventory is protocol surface

`list_adapters()` and `register_adapters()` are `Provider` methods. A provider that declares no
`adapter_hot_swap` capability refuses both with `CapabilityUnsupported` — refuses, rather than
answering an empty sequence, because "no adapters registered" and "this provider has no concept of
adapters" are different facts and a caller that conflated them would report a misconfiguration as
an empty registry.

**ADR-0062 decision 1 is narrowed to the load/unload seam.** What that sentence was evidence for
remains true and is the part worth keeping: `load()` spawns, `unload()` terminates, `list_resident()`
reads the process table, and **no lifecycle method was added**. Supervising a process fitted the
existing seam exactly. Reporting an inventory is a different question, which decision 1 was not
answering.

### 2. `register_adapters` takes the complete set, and there is no inverse

The set passed is the set held: a name already held is replaced, a name absent is retired, an empty
sequence clears the registry. The operator's directory is the truth
([ADR-0061](0061-the-adapter-registry-is-a-directory-and-a-manifest.md)) and a rescan restates it
whole, so an add/remove pair would offer two ways to describe one directory and a way for them to
disagree. Registration stays launch-time: a newly arrived adapter is `PENDING_RESTART` and folds in
at the next natural idle, never mid-work — ADR-0062 decision 3, unchanged.

### 3. ADR-0063 rules 1–2 govern **enabled** entries

- **At most one entry is ever enabled, at exactly `1.0`.** There is no composition, there is no
  per-request scale, and there is nowhere for one to be passed. The identity and evidence arguments
  in ADR-0063 are untouched.
- **An entry at scale `0.0` is a disable, not a second adapter.** No composition can result from a
  list of zeros.
- **A request to a server with adapters registered states the whole configuration**, every time,
  including the bare-base request — which is the list with no entry at `1.0`.
- **A request to a server with no adapters registered sends no `lora` key at all**, byte-for-byte
  what ModelRack sent before adapters existed. That is what keeps the adapter arc's byte-for-byte
  invariant assertable.

### 4. The reading is the provider's, not the caller's

Nothing above reaches a caller's vocabulary. `GenerationRequest.adapter` still names at most one
adapter or none; the completeness is how `LlamaCppProvider` spells that on one server's wire, and a
second adapter-serving provider is free to spell it differently as long as at most one is enabled.

## Alternatives considered

* **Keep the two methods on `LlamaCppProvider` and let LoadCoach downcast.** The honest case is
  real and F3 called it the decision most worth a second opinion: the protocol stays at the shape
  ADR-0007 and ADR-0062 describe, and reverting is small — delete two protocol methods and four
  refusals, keep them on the concrete class. Rejected because the downcast is not confined to one
  call site: it appears wherever an adapter row is rendered, a pin is explained or a rescan is
  folded in, and each is an `isinstance` against a concrete provider inside an application that
  must not import one. A protocol whose users must know the implementation is not the abstraction
  ADR-0007 bought.
* **A separate `AdapterInventory` protocol, structurally checked.** Keeps `Provider` at eight
  methods and lets a caller ask "does this provider also do adapters". Rejected: it is the same
  downcast with a nicer name — the caller still branches on a type — and it splits one provider's
  surface across two protocols that every implementation would satisfy together or not at all.
  `ProviderCapabilities.adapter_hot_swap` already answers the "can it" question, on the object,
  without a second type.
* **Send only the enabled entry and let `construct_lora_list` zero the rest.** Satisfies ADR-0063's
  letter, works against `b10792`, and is one line shorter. Rejected on two grounds F3 recorded: the
  bare-base case then has no honest spelling — you would have to send a single entry at `0.0`
  naming an arbitrary adapter — and a recorded request body that states the whole configuration is
  a far stronger thing to assert a property over than one that relies on the server's defaulting.
* **Send no `lora` field for a bare-base request.** The literal reading of ADR-0063 rule 1, and the
  defect: on an adapter-registered server it applies every adapter at `1.0`.
* **Pin the server build and rely on its behaviour.** Rejected: the arc already treats the server
  as an inherited component whose internals may move, and a correctness property that depends on a
  branch in one build of somebody else's C++ is not a property.
* **Amend ADR-0062 and ADR-0063 in place.** Rejected by this directory's own rule — an ADR is not
  edited to hide a change of mind. Both keep their text and gain a header note pointing here.

## Consequences

* ADR-0007's method block is now three methods and some `refresh` keywords behind the shipped
  protocol. It stays as written — it is the 2026-08-21 shape — and its rule 2's delegation to
  ModelRack spec §7 is what a reader should follow; its header already says so.
* A new provider implementation must answer both methods, even if only to refuse them. That is one
  refusal each and is what `MINIMAL_CAPABILITIES` already implies; the fake and the two
  non-adapter providers do exactly that.
* Every request to an adapter-registered llama-server carries a list as long as the registration
  set. That is a handful of small objects per request and is the price of the wire stating the
  whole configuration rather than relying on a server default.
* An I17-style property check can assert the recorded body directly: exactly one entry at `1.0` for
  a selected adapter, none for the bare base, and no `lora` key when nothing is registered. That
  assertion is only possible because the body is complete.
* ADR-0063's identity and evidence reasoning is entirely unaffected. The subject space is still one
  adapter or none, and no measurement's meaning changes.

## Revisit when

* A second adapter-serving provider is implemented and cannot express "the complete configuration"
  on its wire — at which point the completeness rule moves from the decision to `LlamaCppProvider`'s
  own documentation and rule 3's first two bullets stay as the suite-wide part.
* llama.cpp changes the absent-`lora` branch to mean "no adapters" rather than "the launch set" —
  at which point sending only the enabled entry becomes correct, and this record's rule 3 becomes a
  compatibility measure with a floor build named.
* A third protocol method is proposed for the adapter surface, or any lifecycle method is — the
  first is a shape question this record already answered, the second reopens ADR-0062 decision 1
  properly rather than narrowing it.
