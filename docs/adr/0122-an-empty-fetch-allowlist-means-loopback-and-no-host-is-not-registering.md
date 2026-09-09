# ADR-0122 — An empty `http_fetch` allowlist means loopback, deliberately; "no host at all" is not registering the tool

**Status:** Accepted (2026-09-09)
**Relates to:** [ADR-0026](0026-egress-and-network-policy.md) §3 (the checks `http_fetch` performs),
[ADR-0116](0116-research-runs-under-toolyard-and-fetches-only-a-named-host.md) decision 3 and its
"Revisit when" (the bullet this ADR answers), [ADR-0007](0007-provider-abstraction.md) rule 2 (never
advertise what cannot be honoured — applied here to a tool rather than a provider).
**Source:** Row N3 of `roadmap/outstanding-work.md`, from M1's finding 1: two consumers withhold
`http_fetch` from their registry to mean "no host", the same three-line workaround twice.

## Context

`toolyard.http_fetch_tool(allowed_hosts, …)` reads an empty `allowed_hosts` as *loopback only*
(`LOOPBACK_HOSTS`; spec §7 rule 5, §11.5). PromptCadence (row E4 decision 1) and IdeaPress
(ADR-0116 decision 3) both want an unconfigured installation to reach **no** host, and both get
there by not registering the tool when the allowlist is empty, so a model's URL produces
`REFUSED` / `unknown_tool`. M1's handoff flagged the duplicated workaround and offered two closes:
give the factory an explicit closed construction, or state that the loopback reading is the
deliberate one and the not-registered branch is the consumer's job.

## Decision

**The loopback reading stays, and it is the documented meaning; a consumer that wants no host
does not register the tool. No closed construction is added.**

1. **Empty means loopback because the package's own default must be safe and useful.** ToolYard's
   tests, quickstart and the ADR-0026 §3 vector set drive `http_fetch` against a loopback origin;
   the alternative default for an empty list — everything — is the one the docstring already
   refuses. Loopback is the smallest set that lets the package demonstrate itself.

2. **A registered tool that can fetch nothing is a lie to the model.** A closed `http_fetch` would
   appear in the tool list, be described as fetching, and refuse every call. The model would spend
   turns discovering a fact the application already knew. Not registering is the honest shape:
   the tool list states what the process can do (ADR-0007 rule 2, applied to tools). Both
   consumers' existing branches are therefore the intended design, not a workaround, and each is
   tested.

3. **The distinction lives in the consumer, and that is where it belongs.** "No host at all" is a
   fact about an installation's configuration; ToolYard has no configuration, only arguments. The
   consumer that reads `[research] allowed_hosts` or `[tools] fetch_hosts` is the one that knows
   the list is empty on purpose.

4. **The statement is written where a reader meets it:** `http_fetch_tool`'s docstring, spec §7
   rule 5, and this record. ADR-0116's third "Revisit when" bullet is answered by this ADR and is
   not re-opened by a future consumer repeating the branch — a third copy of three lines is fine.

## Consequences

*Positive.* No API change, no `toolyard 0.1.2`, no consumer patch. The rule is now stated in
three places instead of inferred from a test name.

*Negative.* A consumer that forgets the branch registers a loopback-capable tool. Both current
consumers test the branch; a new consumer reads the docstring, which now says so in the first
line of the argument's description.

## Alternatives considered

* **`http_fetch_tool(None)` or `closed=True`** registering a tool that refuses everything with
  `host_not_allowed`. Rejected by decision 2.
* **Empty means closed, loopback by explicit `["127.0.0.1"]`.** A behaviour change to a
  published `0.1.x` for the sake of a default nobody ships; the package's own demonstrations would
  all grow the literal. Rejected.

## Revisit when

* A consumer needs the model to *see* that fetching exists but is disabled — a UI that lists
  tools and their state, say. That is a registry feature (a disabled entry), not a fetch-tool one.
