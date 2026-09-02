# ADR-0050 — A shared package may ship tables; it may never own a migration history

**Status:** Accepted (2026-09-02)
**Extends:** [Master Architecture §3](../architecture/master-architecture.md) (ownership
boundaries) and [§5.3](../architecture/master-architecture.md) (storage model),
[Database Standards §1](../standards/database-standards.md).
**Relates to:** [ADR-0005](0005-database-strategy.md) (SQLAlchemy 2.0 + Alembic),
[ADR-0006](0006-sqlite-and-postgresql-roles.md) (two dialects), [ADR-0011](0011-shared-package-boundaries.md)
(extraction at the second consumer), [ADR-0054](0054-spotcheck-records-egress-it-does-not-enforce-it.md)
and [LoadLedger §7](../packages/loadledger/spec.md) (the two packages that use this).
**Source:** [PromptCadence roadmap §2, D-6](../roadmap/promptcadence-roadmap.md).

## Context

Two of the arc's packages exist to keep durable rows: LoadLedger accumulates debits and balances,
SpotCheck records every egress verdict. Both have two named consumers (PromptCadence now,
IdeaPress at M13), and both have contracts that are statements *about the rows*: a debit and the
verdicts it reports commit together; an egress ledger is append-only; history is re-costable
because every entry stores `TokenUsage` and a `pricing_hash` rather than a money figure.

The suite's existing storage rule has no slot for this. WeightsDB — the one package that touches
databases — is deliberately plumbing only: engine, sessions, pragmas, migration runner, backup. Its
own gold standard is that it "defines no application table; a test asserts its `MetaData` is
empty", and each application declares its own models and owns its own Alembic history. Master
architecture §5.3 says one database per application, owned exclusively by that application, and §11
forbids cross-application database access outright.

So the two obvious readings both fail. If a package ships **no** tables, each consuming application
writes its own ledger schema from the package's value objects, the column sets drift, and the
behavioural contracts have nothing normative to hold — which is the duplication the package layer
exists to prevent, arriving in the one place where the duplicate is a money record. If a package
ships **a database**, it owns a second migration history inside an application's data root, backup
and restore are split between two owners, and the day two applications point at one
package-owned file, the suite has cross-application database access through the back door.

## Decision

**A shared package may ship *mountable persistence models*: table definitions the application
mounts into its own metadata and its own Alembic history. It never owns an engine, a session, a
migration history, or the data.**

1. **The package exports a mount function, not a base class.**
   `mount_ledger_tables(metadata, *, prefix="ledger_") -> LedgerTables` and
   `mount_egress_tables(metadata, *, prefix="egress_") -> EgressTables`. The application passes its
   own `MetaData`; the tables are created inside it; the application's `alembic revision
   --autogenerate` sees them like any table it wrote itself. Two applications mounting the same
   function have **two tables in two databases — never one**.
2. **Plain-typed columns only.** No ORM base with domain meaning, no relationship to an
   application's entities, no foreign key out of the mounted set. `run_id` and `source_ref` are
   opaque strings, because the package must not know what a trajectory or a unit is.
3. **Sessions arrive by injection.** `SqlLedger(session_factory, …)` takes a callable returning a
   SQLAlchemy 2.0 session. The package opens no connection, reads no URL, and holds no engine.
4. **No sibling import.** LoadLedger and SpotCheck do not import WeightsDB — master architecture
   §2 rule 3 forbids it, and substantively it would force every consumer of a budget accumulator to
   take a migration runner and a backup implementation with it. `sqlalchemy` is an optional extra
   (`loadledger[sql]`, `spotcheck[sql]`) so the pure-value core stays installable with nothing.
5. **The host owns every migration.** A column change in a mounted table ships as an upgrade note
   and a migration *recipe* — documentation plus, at most, a helper the host calls from its own
   revision. A package never runs a migration, and auto-migration on import is forbidden outright.
6. **Each mounting package proves it, in a miniature host.** A test builds a throwaway application
   with its own metadata and Alembic environment, mounts the tables, autogenerates, upgrades, and
   exercises the package's atomicity contract under a killed process, on both dialects. The
   pattern is only as good as the evidence that a real host's migration story survives it.
7. **The architecture's forbidden list gains a line**: *a package owning an application's
   migration history*. This ADR is the boundary between that and what is now permitted.

## Alternatives considered

**Ship only the value objects; let each application declare its own tables.** The established
suite pattern — it is exactly how WeightsDB works, and it needs no new rule at all. Rejected
because these packages' contracts are statements about rows, not about values: "the entry and the
verdicts it reports commit together", "the ledger has no public mutation path", "re-costing history
changes no stored row". A package that ships the behaviour but not the shape must trust a schema it
did not define, and the first divergence between two hand-written ledger schemas is discovered when
one application's cost figures cannot be reproduced. Where a *shape* is part of a contract, the
shape belongs with the contract.

**Give the package its own database.** Clean ownership on paper: LoadLedger owns
`ledger.sqlite3`, migrates it, backs it up. Rejected on two counts. It splits an application's
storage across two owners, so backup, restore, retention and migration each acquire a seam nobody
owns end to end; and it puts one file within reach of two applications, at which point the suite's
hardest boundary rule (§11.3, no cross-application database access) is one configuration line from
being broken — not by a mistake, but by the design inviting it.

**Extend WeightsDB to own these tables.** It already owns database machinery, and the mounting
helper would sit naturally beside the session factory. Rejected: WeightsDB's whole value is that it
contains no domain meaning — its empty `MetaData` is a *tested* gold standard, and A2 of the risk
register names "shared package absorbs application logic" as a live risk with WeightsDB growing a
table as its worked example. Teaching WeightsDB what a ledger entry is spends that guarantee to
save an import.

**Let LoadLedger import WeightsDB for the session plumbing.** Would remove the injection
boilerplate. Rejected: §2 rule 3 forbids capability packages importing siblings, and the rule earns
its keep here — the alternative drags an ORM, a migration runner and a backup implementation into
the dependency footprint of anything that wants to add up tokens.

**One "suite tables" package holding every shared schema.** Rejected for ADR-0011's `aisuite-common`
reason: it would need a reason to change for every package's schema, and every consumer would
install all of them to get one.

## Consequences

* LoadLedger and SpotCheck each ship a `sql` extra containing a mount function, a SQLAlchemy-backed
  implementation of their protocol, and no engine. Their pure cores (`InMemoryLedger`,
  `InMemoryEgressLedger`) remain first-class and are what the deterministic tests use.
* PromptCadence's single Alembic history includes `ledger_entries` and `egress_decisions` alongside
  its own tables. One `db upgrade`, one backup, one restore, one retention policy — which is the
  property that made mounting worth a new rule.
* **The named failure mode is import order.** Autogenerate only sees what has been mounted before
  the metadata is inspected, so a host that mounts lazily gets a migration that silently drops the
  package's tables. Each package's miniature-host test exists to catch that, and the host
  applications mount at module import in their model package.
* Prefixes are configurable and collisions are the host's problem to avoid; the defaults
  (`ledger_`, `egress_`) are documented as part of the mounted contract.
* A mounted column change is a coordinated release: the package ships the recipe, each host writes
  its own revision. This is more work than an owned migration would be, and it is the cost of the
  host keeping one history.
* The pattern is deliberately confined to two small packages. It is a permission, not a direction:
  nothing else in the suite mounts tables, and a package proposing to is answering the wrong
  question.

## Revisit when

* **A third mountable package appears** — extract the miniature-host test kit rather than write the
  Alembic harness a third time, and reconsider whether the pattern has become an architecture
  rather than an exception.
* **A host's migration story breaks under it** — autogenerate producing a wrong diff for a mounted
  table, or two hosts needing incompatible column types for one shape. Either would mean the shape
  is not as portable as this record assumes, and the fallback is per-application tables with a
  conformance test over the column set.
