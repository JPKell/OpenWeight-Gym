# ADR-0129 — WeightRoomGym reads both shapes of `GET /api/v1/version`, and the suite converges on one in a row of its own

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0013](0013-api-versioning.md) (API versioning and the negotiation route),
[ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
(the console that does the negotiating), [`apps/weightroom/spec.md`](../apps/weightroom/spec.md)
§19, [`apps/weightroom/api.md`](../apps/weightroom/api.md) §2.
**Source:** row W2, found live on the reference machine while negotiating LoadCoach's version.

## Context

Spec §19 says WeightRoomGym "names, per application, the range of versions it speaks to
(`GET /api/v1/version` on first contact, re-checked every five minutes, ADR-0013)". Row W2 built
that, pointed it at the four running applications, and found that **the route answers in two
incompatible shapes**:

```jsonc
// FreeWeight, LoadCoach
{"application": {"name": "loadcoach", "version": "1.3.1", "git_commit": null},
 "api": {"current": "v1", "supported": ["v1"], "deprecated": []},
 "schemas": {…}}

// IdeaPress, PromptCadence — and WeightRoomGym itself
{"application": "promptcadence", "version": "1.3.3", "api_version": "v1", "schema_version": "1"}
```

The key `application` is a **string** in one and an **object** in the other, so a reader written
against either finds nothing in the other. ADR-0013 fixes the route and its meaning; it does not
fix the payload, and neither does the API and Contract Standards document — the shape was settled
twice, independently, and the second time differently.

Nothing had noticed because nothing had read the route across applications before. The four
applications compose over *their own* payloads, every one of which is a versioned SetSpec model;
`/version` is the one cross-application route whose body is a plain dictionary.

## Decision

**WeightRoomGym reads both shapes. Converging the suite on one is a row of its own, and it needs
a payload change in at least two applications, so it is not this row's to make.**

1. **The console is a reader, not an arbiter.** `services/apps.py` branches on whether
   `application` is a mapping and takes `version` and the API major from whichever shape it
   found. A version route a console cannot parse makes the console report a healthy application
   as unreachable — the failure this rule exists to prevent — and refusing to read three of the
   five applications would have been a worse answer than reading both.
2. **Neither shape is deprecated here.** This ADR records that two exist and that the console
   tolerates both; it does not pick a winner, because picking one is a breaking change to at
   least two applications' public API and belongs with the row that makes it.
3. **The convergence row owes three things**: the chosen payload written into
   [API and Contract Standards](../standards/api-and-contract-standards.md) as *the* shape, a
   minor release of each application that changes, and a WeightRoomGym release whose reader keeps
   accepting the old shape for one major — an operator upgrades the console and the applications
   on different days.
4. **Until then, `api.md` §2 and spec §19 are amended by this ADR** to say that the negotiated
   payload may take either form.

## Consequences

*Positive.* Version negotiation works today against every application as it actually is, and the
divergence is written down instead of living in one reader's branch.

*Negative.* WeightRoomGym carries a branch it should not need, and a third shape would need a
third. The branch is one function with a docstring naming both forms and a test naming each
application, so the cost is bounded and visible.

*Neutral.* WeightRoomGym's own `/version` is the flat shape, which is not a vote: it was written
before the divergence was known.

## Alternatives considered

* **Pick the nested shape now and change IdeaPress, PromptCadence and WeightRoomGym.** It carries
  strictly more — `supported`, `deprecated`, `schemas` — which is what ADR-0013's negotiation
  language implies a client should be able to read. Rejected *for this row*, not on the merits: it
  is three applications' public API changed by a console's row, without their specs updated and
  without their release notes.
* **Pick the flat shape now**, since three of five emit it. Rejected for the same reason, and it
  discards fields ADR-0013 wants.
* **Have the console read only the shape each application's spec documents.** Neither spec
  documents one; that is the defect.
* **Negotiate over `Accept` or a `?shape=` parameter.** Rejected: two shapes are an accident, not
  a feature, and content negotiation would make the accident permanent.

## Revisit when

* **The convergence row runs** — this ADR is superseded by the one that names the single shape.
* **A sixth application, or a second host** (spec §21's "WeightRoomGym reading remote
  applications over their APIs only") makes the reader's tolerance a compatibility promise rather
  than a workaround.
