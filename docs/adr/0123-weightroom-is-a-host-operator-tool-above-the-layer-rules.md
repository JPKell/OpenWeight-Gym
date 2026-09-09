# ADR-0123 — WeightRoom is a fifth application, and it is a host operator tool above the layer rules

**Status:** Accepted (2026-09-09)
**Extends:** [Master Architecture §1.1, §2, §3, §8 and §11](../architecture/master-architecture.md)
(the component table, the dependency graph, ownership, deployment, the forbidden list), following the
[ADR-0038](0038-one-model-at-a-time-per-gpu.md) precedent: the frozen document is changed only by a
record that declares what it extends, and every change is additive.
**Relates to:** [ADR-0001](0001-application-and-package-separation.md) (what an application is),
[ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) (one governed egress path —
the rule this record keeps for chat), [ADR-0020](0020-ui-rendering-strategy.md) (rendering, kept
unchanged), [ADR-0117](0117-provider-registrations-are-edited-in-place-in-the-config-file.md) (the
in-place file edit this record generalises), [Dependency and Boundary Rules §3](../architecture/dependency-and-boundary-rules.md)
and [Database Standards §1](../standards/database-standards.md) (the channels this record excepts, for
one component), and the four records that fill in its parts:
[ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md) (writes),
[ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md) (processes),
[ADR-0126](0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md) (exposure),
[ADR-0127](0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md) (settings).
**Source:** the operator interview of 2026-09-09, decisions D1, D2, D5, D8, D14 and D15
([kickoff](../history/w0-weightroom-phase-0.prompt.md) §2).

## Context

The suite is four applications that each own a database, a `config.toml`, a log, a port and a
web UI, and that compose only over versioned HTTP. That shape is what keeps each of them
independently installable, and every rule in the architecture defends it: no application imports
another, no application opens another's database, no application reads another's configuration
file ([boundary rules §3](../architecture/dependency-and-boundary-rules.md)).

The cost lands on the person running the machine. Operating the suite today means four browser
tabs on four ports, four configuration files edited by hand, four `journalctl` invocations, four
sets of `db backup` and `db upgrade` verbs, a Caddy proxy with basic auth to reach any of it from
another room ([`LAN_ACCESS.md`](../LAN_ACCESS.md) before this row), and no single view of what the
machine is doing — which model is resident, what the GPU is holding, what today cost, which
application is down. Nothing in the suite can show that view, because the rules forbid anything in
the suite from looking.

Three shapes were on the table. **A fifth peer application** under the same rules could only show
what the four APIs expose; process control, file edits and cross-database views would each need
every application to grow an administrative API first, and an application that exists to
administer its peers would then be exactly as capable as the least-finished of those APIs. **A
package** that applications embed is application-shaped — it would own a database, a queue, a
UI and a login — and [ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) already
rejected that disguise once. **A host operator tool** that stands above the layer rules is the
honest description of the thing wanted: the operator's own reach — shell, files, databases,
`systemctl` — given a console.

## Decision

**WeightRoom is the fifth application, and it is the operator's tool: it sits above the layer
rules by an exception scoped exactly as wide as this record says, and it never imports an
application.**

1. **A fifth application, in every ordinary respect.** Import name and CLI `weightroom`,
   distribution **`openweight-gym`** (`weightroom` is held on PyPI by an unrelated `0.0.1`;
   [Packaging Standards §8](../standards/packaging-and-release-standards.md)'s fallback rule is
   applied with the operator's chosen name rather than `aisuite-weightroom`), default port
   **8769**, environment prefix `WEIGHTROOM_`, its own `weightroom.sqlite3` and its own Alembic
   history, the same `web`/`cli`/`services`/`domain` shape and the same gate as the other
   fourteen repositories. Its repository is `OpenWeight-Gym` — the former documentation
   repository — with the suite's canonical documentation tree under its `docs/`.

2. **Above the layer rules, by enumeration.** WeightRoom may, and no other component may:
   * read any application's database directly, through that application's own effective
     `storage.database_url`, opened read-only unless [ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)'s
     guard has been passed;
   * edit any application's `config.toml` in place, comments preserved, validated by the owning
     application before it lands ([ADR-0117](0117-provider-registrations-are-edited-in-place-in-the-config-file.md)'s
     mechanism, widened from the provider subtree to the whole file under
     [ADR-0127](0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md));
   * start, stop, restart and read the journal of any application through the `systemd --user`
     units it writes ([ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md));
   * run any application's CLI as a subprocess, and call any application's HTTP API;
   * import the suite's packages as any application does — `baseaicore`, `setspec`, `weightsdb`,
     `mirrorwall`, `sweatmeter`; `modelrack` for **read-only** provider calls (residency and
     discovery, never `generate`); `loadledger[sql]` for the shape of the ledger tables it reads
     out of PromptCadence's and IdeaPress's databases.
   The justification is the one that makes the exception safe to state: the operator already
   holds every one of these rights at a shell, and WeightRoom exercises them on the operator's
   behalf, under login, with an audit row. It grants nothing the machine did not already grant.

3. **It never imports an application.** `.importlinter` forbids `freeweight`, `loadcoach`,
   `ideapress` and `promptcadence` at module level, in function bodies and under `TYPE_CHECKING`,
   exactly as the packages are forbidden. An import would bind WeightRoom to each application's
   internals and version at once; a database read binds it to a schema **at a migration
   revision**, which is a fact it can check. Every direct read names the application's
   `alembic_version` it was written against; an unknown revision — newer or older — degrades that
   application's pages to *schema not known to this WeightRoom*, by name, never a crash and never
   a guess. The four applications keep migrating freely; WeightRoom follows in its next release.

4. **It runs no tool, compacts nothing, and decides no egress of its own.** `toolyard`, `cutctx`
   and `commissioner` are absent from its dependencies and forbidden by `.importlinter`. Chat
   reaches a model only through LoadCoach and PromptCadence, which own the routing decision,
   the budget and the egress verdict; WeightRoom shows those decisions and never makes them. A
   console with a provider client would be a second ungoverned egress path, which is what
   [ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md) exists to prevent;
   `modelrack`'s presence for `list_resident` and discovery is the deliberate, read-only
   exception to that absence, and `generate` is never called through it.

5. **App-owned operations first; raw writes only under the guard.** Maintenance that an
   application already offers — `freeweight db delete --model`, retention settings, `db backup`,
   `db upgrade`, `token create`, `queue pause` — is invoked through that application's CLI or
   API, so the application's own preview, confirmation and cascade rules apply. A raw write into
   another application's database is the one place the boundary is crossed on purpose, and
   [ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md) is
   its price.

6. **The four applications are untouched in posture.** Each keeps its loopback bind, its own UI,
   its own tokens and its own security page. WeightRoom **re-implements** every control surface
   natively — models, routing, queue, evidence, projects, trajectories, approvals, settings —
   rather than proxying or framing the applications' pages: a proxy would carry each
   application's `__Host-` CSRF cookie and its bearer-token console onto the LAN, which is the
   problem [`LAN_ACCESS.md`](../LAN_ACCESS.md) documented. The applications' UIs stay
   loopback-only and stay useful on the machine itself.

7. **[ADR-0020](0020-ui-rendering-strategy.md) applies unchanged.** Server-rendered Jinja over
   MirrorWall, progressive enhancement by small ES modules, SSE for every live update. The
   interview's phrase was "htmx"; what it names — swap a fragment, subscribe to a stream — is
   the pattern ADR-0020 adopted through MirrorWall's own modules, and the htmx *library* stays
   what ADR-0020 decided it is: not a dependency. This record does not reopen that.

8. **The look is the console's, and MirrorWall carries it.** WeightRoom is dense and dark-first
   (13 px base, 32 px rows, a status-dot vocabulary, a 34 px telemetry strip, app tabs, a left
   menu). The tokens and components generic enough for every application land in MirrorWall
   0.3 from the design brief ([`apps/weightroom/design.md`](../apps/weightroom/design.md)); the
   four applications adopt them in rows after this arc.

## Consequences

*Positive.* The machine gets one place to be operated from, with one login and one certificate,
and the four applications get to stay exactly what they are. The exception is written down as a
list, not a mood, so a reviewer can answer "may WeightRoom do X" by reading rule 2.

*Negative.* WeightRoom couples to four schemas and four CLIs. Rule 3's revision check turns that
coupling from a crash into a named degradation, but every application migration still owes
WeightRoom a release, and the suite now has one component whose test suite needs four others'
fixtures. The traceability matrix gains rows whose owner is "WeightRoom (reads FreeWeight)" and
the like; those rows are the coupling made visible.

*Negative.* A compromised WeightRoom session is a compromised machine — the same blast radius
as the operator's shell, which is the point of [ADR-0126](0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)'s
login, rate limit, session expiry and audit log being non-negotiable.

*Neutral.* Master architecture §2's graph gains a node with arrows to the packages it imports
and **dotted** arrows to the four applications labelled *HTTP · CLI · DB (read) · config · unit*.
§11 gains "a fifth component reading another's database" as the one stated exception to item 3.
Gold Standards §1.1 gains WeightRoom's dependency row; Gold Standards §2 gains its section.

## Alternatives considered

* **A fifth peer application under the ordinary rules**, with each application growing the admin
  API it would need. Rejected: four applications would each acquire process control, file
  editing and cross-schema views they have no use for themselves, in four versions, to serve one
  consumer — and the consumer would still be unable to see a stopped application at all.
* **Keep Caddy in front of four UIs** (the status quo of `LAN_ACCESS.md`). Rejected by the
  operator: four ports, basic auth, IdeaPress's absent login, PromptCadence's loopback-first
  console, and still no view of the whole machine.
* **A generic operations stack** — Grafana for telemetry, Portainer-style process control, a
  database browser. Rejected: three logins, three certificate stories, and none of them knows
  what a routing decision, a measurement subject or an egress verdict is. The look is borrowed
  from that register (rule 8); the tools are not.
* **Package-shaped WeightRoom that applications embed.** Rejected on
  [ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md)'s reasoning: it owns a
  database, a queue, a login and a UI, which is an application hiding its ownership.

## Revisit when

* **An application grows an administrative API that covers something WeightRoom reads directly.**
  The API wins, the direct read is retired, and rule 2's list shrinks — the exception should only
  ever narrow.
* **A second machine.** Rule 2 is written for one host; a WeightRoom reading databases over a
  network is a different design with a different threat model.
* **A second operator.** Rule 2 assumes the login *is* the operator; roles, scopes and
  per-person audit attribution are a new record.
