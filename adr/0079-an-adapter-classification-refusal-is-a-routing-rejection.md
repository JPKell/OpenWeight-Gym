# ADR-0079 — An adapter's classification refusal is a routing rejection, recorded in the explanation

**Status:** Accepted (2026-09-05)
**Extends:** [ADR-0065](0065-an-adapter-is-classified-and-local-only.md) (an adapter is classified
and local-only), [LoadCoach Routing §4](../apps/loadcoach/routing.md) (hard constraints and their
reasons).
**Relates to:** [ADR-0054](0054-commissioner-records-egress-it-does-not-enforce-it.md) (Commissioner
records egress; it does not enforce it),
[ADR-0046](0046-data-classification-is-ordered-and-defaults-closed.md) (classification is ordered
and defaults closed), [ADR-0040](0040-routing-backend-owns-model-choice.md) (the router owns model
choice), [Adapter roadmap §7 I19](../roadmap/adapter-roadmap.md).
**Source:** Row H2, decision 3 of its kickoff §0.2.

## Context

[ADR-0065](0065-an-adapter-is-classified-and-local-only.md) rule 3 says an adapter is local-only,
that a would-be adapter egress is "a **recorded Commissioner denial**, not a silent omission", and
that LoadCoach additionally excludes remote + adapter candidates with a named rejection.
Integration verification **I19** then asks for the demonstration: *a confidential-classified adapter
with a remote-tier request produces a recorded denial.*

Read literally, I19 asks LoadCoach for something LoadCoach does not have. A
`governance.egress_decision` is Commissioner's payload, written into Commissioner's ledger by the
application that mounted it — PromptCadence, today, and only there. LoadCoach has no Commissioner
dependency, no egress ledger, and no reason to grow either: it is the routing backend, and
[ADR-0054](0054-commissioner-records-egress-it-does-not-enforce-it.md) is explicit that the
recording component does not enforce and the enforcing component records its own decisions.

There is also a sequencing fact. The remote + adapter case is refused **before any request is
built** — the candidate never becomes a selection, so there is no turn, no attempt and no egress for
Commissioner to have an opinion about. The thing that happened is that a candidate was rejected, and
LoadCoach already has a place where every rejection is recorded with the numbers that caused it.

## Decision

**In LoadCoach, an adapter refused on classification grounds is an ordinary hard-constraint
rejection with its own reason string, persisted in `routing_candidates` with the explanation. I19's
"recorded denial" is that row. A `governance.egress_decision` is written only by an application that
holds a Commissioner ledger, about a request it actually intended to send.**

1. **Two distinct reasons, not one.** `excluded_by_policy` keeps its existing meaning — the provider
   is remote while the profile or the configuration disallows remote. The classification case gets
   its own string, **`adapter_classification_conflict`**, because "you turned remote off" and "this
   adapter may never leave the machine, whatever you turn on" are different facts and an operator
   who reads the first will try to fix it by flipping a flag that cannot fix it.
2. **The rejection detail names the arithmetic**: the adapter's `data_classification`, the caller's
   declared classification where one was supplied, the effective `max(caller, adapter)`
   ([ADR-0065](0065-an-adapter-is-classified-and-local-only.md) rule 2), and the provider name and
   `remote` flag that made the candidate an egress. A rejection a person cannot check is a rejection
   nobody trusts.
3. **It is persisted like every other rejection** — a `routing_candidates` row with
   `rejected = true`, its reason and its detail, queryable through
   `GET /api/v1/jobs/{id}/explanation` and `GET /routing-decisions/{id}` for the lifetime of the
   decision. Explanations default to being kept for ever, so the denial is as durable as the
   decision it belongs to.
4. **The adapter's classification is recorded on what ran, not only on what was refused.** Every
   attempt that used an adapter records that adapter's classification and the effective
   classification of the work, which is
   [ADR-0065](0065-an-adapter-is-classified-and-local-only.md) rule 4's "an invariant nothing
   records is an invariant nobody can check" — the positive case, which a rejection row alone would
   miss.
5. **Where a Commissioner ledger exists, the denial is additionally an egress decision.** An
   application that mounted Commissioner and intended to send work to a remote tier records its own
   `governance.egress_decision` under its own rules. That is PromptCadence's behaviour and it is
   unchanged by this record. Nothing is duplicated: LoadCoach records the routing fact, the caller
   records the governance fact, and neither reaches into the other's database.
6. **I19 is satisfied at the LoadCoach boundary**, and the roadmap's wording is amended to say so,
   because the behaviour it names lives here.

## Alternatives considered

**Give LoadCoach a Commissioner dependency and write `governance.egress_decision` rows.** It is the
literal reading of I19 and it would put the denial in the same ledger as every other egress
decision. Rejected on layering and on truth. Layering: LoadCoach would gain a governance dependency
to record one refusal, and the decision ledger would then have two writers with different
definitions of a decision. Truth: no egress was ever contemplated — the candidate was filtered — so
the row would record a denial of a request that was never going to be made.

**Reuse `excluded_by_policy` for both cases.** One fewer string in a caller-visible vocabulary, and
the two cases are adjacent. Rejected because the remedies are opposite: one is fixed by
configuration, the other is fixed only by not using that adapter for that work. Collapsing them
would send operators to the wrong lever, and the routing vocabulary exists precisely so a rejection
names its own remedy.

**Record the denial as a job event rather than a candidate rejection.** Rejected: events belong to a
job, and a `/route` call has no job. The rejection must be visible in the "explain what you would
do" path, which is where a caller checks a decision before spending a GPU second.

**Refuse the whole request rather than the candidate** — a request that could only be served by a
classified adapter on a remote tier fails with a typed error. Rejected: it converts a routing
outcome into a caller error, and the correct outcome is usually that a different candidate serves
the request. Where *nothing* is eligible, the existing `NO_ELIGIBLE_MODEL` already lists every
candidate and the constraint that rejected it, so the strong failure still exists, with the
classification rejection among its reasons.

## Consequences

* `routing.md` §4's constraint table gains a row and the caller-visible rejection vocabulary gains
  one string. Both are documented as vocabulary a client may switch on.
* I19's demonstration is a LoadCoach explanation row, not a Commissioner ledger entry, and the
  handoff and the roadmap say so plainly rather than leaving a reader to discover it.
* An application that holds a Commissioner ledger still records its own egress decisions, and its
  denial and LoadCoach's rejection are two records of two different facts about the same intent.
  That is not duplication to be deduplicated; it is each component recording what it decided.
* A future application without a Commissioner ledger inherits the same protection without inheriting
  a governance dependency, which is what makes the local-only invariant hold everywhere rather than
  only where governance is mounted.

## Revisit when

A second component needs to *enforce* classification rather than record it — a tool sandbox refusing
an artifact by classification, say. At that point the join in
[ADR-0065](0065-an-adapter-is-classified-and-local-only.md) rule 2 is being computed in three places
and deserves one home in the domain foundation, and where the refusal is recorded becomes a question
about that home rather than about routing.
