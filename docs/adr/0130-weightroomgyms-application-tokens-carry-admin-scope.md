# ADR-0130 — WeightRoomGym's application tokens carry `admin` scope

**Status:** Accepted (2026-09-09)
**Amends:** [ADR-0126](0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)
rule 8 (the wizard issues one token per application, with a scope), whose scopes were chosen
before the settings page existed.
**Relates to:** [ADR-0127](0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md)
rule 4 (a runtime-changeable key is written through the running application's `PUT /settings`),
[ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 2 (the
operator's session has a shell's reach).
**Found:** row W4, demonstrating development plan Phase 4 criterion 1 on the reference machine.

## Context

ADR-0126 rule 8 gives WeightRoomGym one bearer token per application, written to a file the
configuration merely *references*, with the narrowest scope the console needed at the time:
`write` for LoadCoach, `write,approve` for PromptCadence. Row W1 implemented that, and the
reference machine's tokens carry those scopes today.

ADR-0127 rule 4, decided later, routes every runtime-changeable key through the running
application's `PUT /api/v1/settings`. Both LoadCoach's and PromptCadence's `PUT /settings`
require **`admin`** — LoadCoach's `authorize(principal, "admin")`, PromptCadence's spelled out in
its own docstring. Scopes are cumulative, and `write` does not contain `admin`.

The two records do not compose. Demonstrated on the reference machine at row W4:

```text
PUT /api/v1/apps/loadcoach/settings  {"changes": {"routing.min_confidence": 0.25}}
→ refused: loadcoach refused: 'weightroom' holds the 'write' scope; 'admin' is required.
```

The console read the key, rendered its bounds, its description and its live value correctly, and
could not change it. A settings page that can describe every runtime key and move none is not a
settings page.

## Decision

**WeightRoomGym's token for an application carries `admin`.** `TOKEN_SCOPES` becomes
`{"loadcoach": "admin", "promptcadence": "admin,approve"}`; the wizard issues those, and
`wr-gym doctor` reports an installed token whose scope is narrower so an install made before this
record is found rather than discovered the first time an operator edits a setting.

`approve` is kept alongside `admin` for PromptCadence because its scope vocabulary lists the two
separately (`read, write, approve, admin`) and row W6's inline approvals depend on it; whether
`admin` subsumes `approve` is PromptCadence's business, and naming both asks for nothing extra
while assuming nothing.

## Consequences

*Negative, and the reason this is a record rather than a one-line change.* The token in
`~/.config/wr-gym/secrets/<app>.token` can now do everything that application's API allows. It is
a real widening and it is written down here rather than absorbed quietly.

*Why it is nonetheless right.* The privilege is not new; only its route is. The same operator
session already edits every key of the same application's `config.toml` in place
([ADR-0127](0127-every-application-publishes-its-settings-schema-and-weightroom-generates-the-form.md)
rule 3), drives its unit
([ADR-0125](0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)),
and — from row W7 — writes into its database behind a five-part guard
([ADR-0124](0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)).
[ADR-0123](0123-weightroom-is-a-host-operator-tool-above-the-layer-rules.md) rule 2 states the
posture plainly: this is the host operator's tool and it has a shell's reach. Withholding `admin`
on the HTTP path while granting the file path does not reduce what the console can do; it only
makes the console apply changes the slower way, through a restart, and lie about *live* on its
own page.

*Positive.* Development plan Phase 4 criterion 1 is demonstrable: a runtime key changes on a
running application, within a second, with no restart and no file write.

*Neutral.* The token file itself is unchanged in kind — still a file the configuration
references and never a value in the configuration (ADR-0126 rule 8's actual protection), still
`0600` under `~/.config/wr-gym/secrets/`, still absent from every audit row and every log.

## Migration

An install made before this record keeps its `write` token and will see settings writes refused
in the application's own words. The fix is one command per application, and `wr-gym doctor`
prints it:

```bash
loadcoach token revoke weightroom
loadcoach token create weightroom --scope admin --json    # the secret goes to the token file
```

`wr-gym setup` re-run on an existing install issues the new scope.

## Alternatives considered

* **Leave the scopes and route runtime keys through the file instead.** Rejected: it contradicts
  ADR-0127 rule 4's whole point — the file says what the operator configured, the application
  says what it is running — and it makes every runtime change need a restart.
* **Ask the application to accept `write` for `PUT /settings`.** Rejected: it changes two
  applications' authorization model to suit a third, and `admin` for "change how this service
  behaves at runtime" is the right line *for them*.
* **Issue a second, `admin`-scoped token used only for settings writes.** Rejected: two secrets
  where one will do, both reachable by the same session, with no boundary between them.

## Revisit when

* **An application grows a scope between `write` and `admin`** for runtime settings
  (`settings:write`). Take it: this record asks for the narrowest scope that can write a runtime
  key, and today that is `admin`.
* **WeightRoomGym gains a second, less privileged caller** — a read-only status page for someone
  who is not the operator. That caller gets its own token, and this record's reasoning
  (ADR-0123 rule 2) does not extend to it.
