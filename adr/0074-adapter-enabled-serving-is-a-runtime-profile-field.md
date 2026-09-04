# ADR-0074 — Adapter-enabled serving is a `RuntimeProfile` field, not a `provider_options` convention

**Status:** Accepted (2026-09-04)
**Implements:** [ADR-0060](0060-selection-lives-in-the-subject-serving-mode-in-the-profile.md) (= A-3),
which decided that adapter *selection* lives in the subject and adapter *serving mode* lives in the
runtime profile, and left the mechanism to the implementation.
**Relates to:** [ADR-0023](0023-runtime-profile-resolution.md) (the profile and its hash),
[ADR-0058](0058-the-execution-subject-gains-an-adapter-axis.md) (the axis this is *not*),
[ADR-0062](0062-llamacpp-serves-adapters-through-a-supervised-process.md) (registration is
launch-time, which is what makes serving mode a profile fact at all).
**Source:** ModelRack Phase 7 (`F3_HANDOFF.md` §7.8), which built the serving and found the gap.

## Context

ADR-0060 is unambiguous that a base measured on an adapter-registered server is a **different
measurement** from the same base on a clean one — registered adapters occupy memory, and an active
one costs decode time — and that the fact belongs in the `runtime_profile_hash` rather than in the
subject, because it is a property of how the server was launched and not of which weights answered.

ModelRack Phase 7 implemented the serving and did **not** implement that. The `--lora` flags are
derived from the provider's registration set, which the application supplies at construction;
`RuntimeProfile` is a separate object the caller passes per request, and it has no field for this.
So today two runs of one base — one on a server launched with three adapters registered, one on a
clean server — produce the **same** `profile_hash`, and their measurements would merge.

Nothing is wrong yet, because nothing has measured it: FreeWeight 1.1 (LA3) is where ADR-0060 §3's
clean-vs-registered A/B is run, and that is the first moment two such subjects exist side by side.
But the failure mode is a **silent merge** — no error, no warning, two different measurements under
one key — so it has to be closed before the measurement rather than after, which is the whole
reason ADR-0060 separated the two facts in the first place.

The temptation is to close it by convention: `provider_options` already feeds the profile hash, so
an application could set `{"adapters_registered": True}` and be done, with no ADR, no BaseAiCore
release and no coordination.

## Decision

**`RuntimeProfile` gains a real optional field for adapter-enabled serving, and the provider
refuses a profile that does not describe the server it would use.**

### 1. The field

`RuntimeProfile.adapters_registered: bool | None = None`, in BaseAiCore, beside
`flash_attention` and shaped like it — **three states, not two**:

* `None` — not stated. This is every profile ever constructed before this field existed.
* `False` — stated: this run is on a server with **no** adapters registered.
* `True` — stated: this run is on a server with adapters registered.

### 2. It is additive to the point of invisibility

`profile_hash` already excludes `None` fields from the canonical JSON it hashes, explicitly so that
"adding a new optional field is additive, not a silent hash break for every profile that does not
set it" (`baseaicore.runtime`). So every stored `profile_hash` in all three databases, every
published evidence bundle and every golden is unchanged, and a deployment that never sets the field
sees nothing. **A default of `False` would not have this property** — `False` is not `None`, it
would be hashed, and every profile hash in the suite would move. The tri-state is load-bearing, not
fussiness.

### 3. The application sets it; the provider refuses a lie

The constructing application sets it, because it is the actor that also supplies the registration
set — the same actor knows both halves. A provider that would serve a request under a profile whose
`adapters_registered` disagrees with the server it would actually use **refuses**, typed, rather
than serving and recording a profile that did not happen. `None` disagrees with nothing and is
always served, so today's callers are unaffected.

This is the `context_configurable` discipline (ADR-0023 §4, ModelRack spec §11.10) applied one
level up: an adapter that accepted a setting and ignored it would produce a run whose recorded
profile never happened, and a profile that claims a clean server while three adapters sit in VRAM
is exactly that.

### 4. Where it is not

It is **not** on the subject and **not** in `AdapterIdentity`. Which adapter answered is the
subject's axis (ADR-0058); whether any were *registered* is the profile's. Conflating them would
make the bare base on a registered server look like an adapter subject with no adapter, which is
neither true nor comparable to anything.

## Alternatives considered

**A `provider_options` convention** — the application sets `{"adapters_registered": True}` and the
existing hash picks it up. Genuinely the cheapest correct thing: it works today, needs no ADR, no
BaseAiCore release and no coordination, and `provider_options` is hashed exactly as a field would
be. It was the recommendation this decision overrode, and the reason for overriding it is that
`provider_options` is by definition **provider-specific and unvalidated** — the escape hatch for
"anything that does not have its own field". A cross-cutting fact that FreeWeight's A/B, LoadCoach's
residency scoring and every evidence record depend on is not provider-specific, and a convention
carries no way to state the key, no way to type it, and no way for a provider to detect that a
caller spelled it `adapters_enabled`. A misspelling would not fail; it would produce a second
profile hash that silently means nothing, which is the same silent-merge class this record exists
to close, arrived at from the other side.

**Leave it open until LA3, when FreeWeight needs it.** Nothing breaks before then, and deciding
later means deciding with the measurement in front of you. Rejected because the cost of being late
is not "a bit of rework" — it is measurements already recorded under a key that merged two
subjects, and evidence that has to be discarded and re-run rather than corrected. The
cheap-to-fix window closes the first time someone benchmarks a base on a machine with an adapters
directory configured.

**Derive it in the provider rather than accepting it from the caller** — ModelRack knows whether it
launched with adapters, so it could stamp the profile itself. Rejected because a provider that
rewrites the profile it was handed breaks ADR-0023's premise that the profile is what the *caller*
asked for, and it would make `profile_hash` a value the caller cannot compute in advance — which
LoadCoach's candidate scoring needs to do before it has a provider at all. Refusing a mismatch
(rule 3) gets the same honesty with none of that.

**Put it on the subject instead**, as a second adapter-axis state. Rejected under ADR-0060: it is a
serving configuration, not a thing the weights did, and putting it on the subject would mean the
bare base on a registered server is a different *subject* from the bare base on a clean one — so
LoadCoach could no longer ask "is this candidate on the resident base?", which is precisely what
ADR-0066's two-level residency needs.

## Consequences

* **BaseAiCore ships one optional field** — an additive minor inside the existing `>=0.4,<0.5` pin,
  the same shape ADR-0058's `AdapterIdentity` took at 0.4.1. A new golden pins the unchanged
  profile hash of a profile that does not set it.
* **ModelRack gains one refusal** in `LlamaCppProvider`, comparing the request's profile against
  the registration set the server was launched with. This is Phase 8 or LA2 work, not Phase 7's:
  P7 shipped without it, and the field it would compare against does not exist yet.
* **FreeWeight 1.1's serving-mode A/B becomes expressible**: `base @ adapters_registered=False`
  versus `base @ adapters_registered=True` are two ordinary subjects differing by one profile
  field, which is what ADR-0060 §3 promised and could not previously be written down.
* **LoadCoach 1.1 must set it** when it constructs a profile for a llama.cpp tier, and must set it
  *correctly* — `True` where the provider has registrations, `False` where it has none. A tier
  configured with an empty adapters directory is `False`, not `None`; `None` should survive only in
  callers that predate the field.
* **Evidence measured before this lands is not retroactively separable.** Any base benchmarked on
  an adapter-registered server before the field exists carries a profile hash that does not record
  it, and there is no way to tell afterwards which it was. Stated plainly because it bounds how
  long the gap can stay open: it is a reason to land this before LA3's benchmarking, not merely
  before LA3's code.

## Revisit when

Registration stops being a launch-time property — llama.cpp gaining runtime adapter registration
would dissolve the premise, exactly as it dissolves `pending_restart` (ADR-0062's revisit trigger).
If adapters can be registered and unregistered on a live server, "the server was launched with
adapters" stops being a property of the launch and this field stops meaning anything stable.
