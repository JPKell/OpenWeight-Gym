# ADR-0109 — A stored settings row this build cannot read serves configuration, and the changeable set is an enumeration

**Status:** Accepted (2026-09-07)
**Extends:** [Configuration standards §7](../standards/configuration-standards.md) — its precedence
rule says what wins; it never said what happens when the winner is unreadable, nor how the
changeable set is bounded.
**Relates to:** [ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)
(the registry this generalises, and the refusal reasoning behind it),
[ADR-0101](0101-a-runtime-setting-need-not-be-a-configuration-key.md) (a key in the registry with no
configuration behind it — the one case where "serve the configured value" needs a different
sentence), [ADR-0102](0102-freeweights-settings-body-gains-the-suites-shape.md) (the wire shape all
three now serve, whose `source` and `stored` fields are where this becomes visible),
[ADR-0013](0013-api-versioning.md).
**Source:** Row I8/I9's handoff items 2 and 3 — two behavioural divergences across three
applications, recorded there as findings rather than decided — and the 2026-09-07 ADR gap review,
findings 1.4 and 1.5.

## Context

Three applications serve a runtime-settings surface built on one idea and no shared code
([ADR-0102](0102-freeweights-settings-body-gains-the-suites-shape.md) closed the wire-shape half of
that divergence). Two behavioural questions were left open, and both are the kind that gets decided
by whoever writes the fourth transcription:

**One — what a row this build cannot read means.** A settings row is a JSON value in a table,
written by whatever version was running then. Narrow a bound, change a type, or point a second
build of a different version at the same database, and a row arrives that the current registry
refuses. Row I8/I9 found the three applications doing two different things with it: FreeWeight fed
stored rows through `Settings.model_validate` during startup and **raised**, where LoadCoach and
PromptCadence fell back to configuration and kept serving. A stored row for a tuning number was
therefore able to stop one application from starting at all — a failure mode with no operator
recovery except editing the database by hand, arriving at the least convenient possible moment.

**Two — how the changeable set is bounded.** All three hold a `RUNTIME_SETTINGS` registry of the
keys that may move and a named set of security-relevant keys refused with `FORBIDDEN`, and all
three refuse everything else as unknown — so the *mechanism* already agrees. What has never been
written down is which of the two is the fence. Row I8/I9 read FreeWeight's as an allowlist and the
other two as blocklist-plus-registry, and observed that FreeWeight's is the **stronger direction**:
a security-relevant key nobody remembered to forbid is config-only by default, where a blocklist's
omission is an accidental grant. FreeWeight's module docstring is the only place that reasoning
exists — "a new security-relevant setting is therefore config-only by default, which is the
direction a mistake should fall in" — and a fourth transcription would have no way to know it was
load-bearing rather than incidental.

The two questions are one decision because they are the same property from two sides: what the
application does with a key it was not built to accept, whether the key arrives from a stored row
or from a `PUT`.

## Decision

### 1. A stored row this build cannot read is *a row this build cannot read*

It is not a fatal error, and it is not silently discarded either. On encountering a stored row
whose value the registry refuses — wrong type, outside the current bounds, an unknown key — the
application:

1. **Serves the configured value** for that key: the file/environment/CLI layers as loaded, exactly
   as if no row existed. Every other key is unaffected; one bad row does not poison the read.
2. **Reports the row and the reason on the settings surface** — the row's stored value is shown, and
   it is shown as *not in effect*, with why. A surface that renders `source: "database"` for a row
   whose value was never applied is the same lie configuration standards §7's precedence rule
   exists to prevent, told about a different cause.
3. **Logs it once**, at `WARNING`, naming the key and the stored value. Once, not per read: this is
   read on a scheduler tick.
4. **Never refuses to start, and never fails the request.** A row written by another version must
   not stop this one from serving. This is the whole rule in one sentence, and the other three are
   how it is done honestly.

**The row is kept.** It is not deleted, not repaired, not rewritten to a clamped value. A build
that could read it may run against this database tomorrow, and a value silently clamped to today's
bounds would be indistinguishable from a value an operator chose. This is the same treatment a row
shadowed by an environment variable already gets ([ADR-0100](0100-promptcadences-runtime-changeable-set-is-five-tuning-numbers.md)):
kept, reported as not in effect, and effective again the moment the condition clears.

**The one wrinkle is [ADR-0101](0101-a-runtime-setting-need-not-be-a-configuration-key.md)'s keys.**
`queue.paused` and `queue.draining` live only in the `settings` table and have no configured value
to fall back to. For those, "serves the configured value" is the model's own default — for a pause
flag, not paused — which is the safe direction: an unreadable row does not leave a queue stopped
with nobody able to explain why.

### 2. The runtime-changeable set is an explicit enumeration

1. **A key is runtime-changeable only by being in the registry.** The registry is a data structure
   in one module, not a convention, not a naming rule, and not "everything except the forbidden
   list" — so the API, the console, the CLI and the generated reference cannot disagree about it.
2. **A key absent from the registry is config-only**, refused with `VALIDATION_ERROR` naming the key
   and listing what *can* be changed. This is the security property: a setting nobody thought about
   is refused by default, so forgetting to forbid something is not an accidental grant.
3. **A security-relevant key is refused by name, in addition** — `403 FORBIDDEN` naming the key,
   never a silent ignore and never the generic unknown-key error. Exposure, egress, credentials,
   containment, retention and spend, whole sections at a time where a section is uniformly
   security-relevant. This is not the boundary; rule 2 is the boundary. It exists so that an
   operator who asks for the wrong thing is told *why* it is refused rather than being told the key
   does not exist, and so that the refusal is asserted by a test naming the key.
4. **Membership is tested by re-reading, not by plausibility.** A key the running process does not
   re-read is not runtime-changeable, whatever the registry says — ADR-0100's rule, restated here
   as the suite's.

Rules 2 and 3 together are what row I8/I9 meant by "allowlist" and "blocklist-plus-registry" being
different strengths: with rule 2 in force they are the same posture, and the named refusals are a
diagnostic layer on top rather than the fence.

## Alternatives considered

* **Refuse to start on an unreadable row.** The strongest-looking option, and FreeWeight's shipped
  behaviour until 2026-09-07: the operator is confronted with the problem immediately and cannot
  run on a configuration they did not intend. Rejected on where the cost lands. The row is a tuning
  number, the value is recoverable from configuration, and the failure appears at the next restart
  — which is typically an unattended one, after an upgrade, with the fix requiring hand-editing a
  database. Refusing to start is the right answer for a *configuration* error the operator just
  made; a stored row is a durable artifact of an older build, and treating the two the same
  conflates a mistake with history.
* **Clamp the value to the current bounds.** Keeps the operator's intent, keeps serving, no
  fallback. Rejected: it invents a value nobody chose and makes it indistinguishable from one
  somebody did — the same defect [ADR-0016](0016-unavailable-is-not-zero.md) refuses for
  measurements, in a settings table.
* **Delete the offending row.** Tidy, self-healing, and the surface stops lying because there is
  nothing left to report. Rejected: it destroys an operator's stated intent to fix a display
  problem, and a build that could read the row may run against this database next.
* **Serve the row and let it fail wherever it is used.** Rejected outright: it moves an
  early, nameable failure into whatever code path happens to touch the value, at whatever time.
* **Leave the posture unstated and record the divergence** (what ADR-0102's consequences left
  open, calling FreeWeight's direction the one the other two "should eventually move" toward).
  Rejected: it is a *security* posture, and "the stronger direction, eventually" is not a thing to
  say about a boundary whose failure mode is an accidental grant. Naming rule 2 as the fence costs
  nothing, because all three already implement it.
* **Extract the registry into a layer-3 package** so there is one implementation. Rejected again,
  and separately, for ADR-0102's reason: three registries with three key sets and two refusal
  vocabularies is not yet an abstraction. This record removes the *behaviour* half of the
  objection, as ADR-0102 removed the shape half; a fourth consumer would be the moment to ask.

## Consequences

* **Rule 1's first and fourth clauses are met by all three applications today.** LoadCoach's and
  PromptCadence's `read_runtime_settings` catch the registry's `ValidationError` and fall back to
  configuration per key; FreeWeight's `apply_stored` was converged on 2026-09-07 and does the same.
  No application refuses to start on a stored row.
* **Rule 1's third clause — log once — is met by FreeWeight only.** Its `apply_stored` emits
  `settings.stored_row_unreadable` at `WARNING` with the key and the stored value. LoadCoach and
  PromptCadence swallow the exception with a comment and no log. That is owed work in both, and it
  is small.
* **Rule 1's second clause — report it on the surface — is met by none of the three, and two of
  them actively misreport.** LoadCoach's and PromptCadence's `runtime_settings_document` compute
  `source` as `"database" if key in stored and shadowed_by is None else "configuration"`, which
  says `"database"` for an unreadable row while `settings` carries the configured value. A reader
  of that body sees a stored value, is told it is the source, and is running on something else.
  Closing it is one condition and one field per application, and it is the part of this record that
  is not yet true anywhere.
* **Rule 2 is met by all three applications today.** Each holds a `RUNTIME_SETTINGS` enumeration,
  refuses an absent key as not runtime-changeable while listing what is, and refuses a named
  security-relevant key with `FORBIDDEN` — PromptCadence additionally by whole-section prefix
  (`server.`, `loadcoach.`, `approval.`, `budget.`, `tools.`, `tiers.`, `policy.`), which is rule 3
  applied to sections that are uniformly security-relevant. What this record adds is not code but
  the statement of which check is the fence, so a fourth transcription cannot get the two the wrong
  way round.
* A fourth application transcribing this registry now inherits a shape (ADR-0102), a precedence
  (configuration standards §7) and a failure behaviour (this record), which is the whole of what
  the three had to work out independently.
* Nothing here changes a wire contract or a stored schema. The reporting fix in rule 1 clause 2
  changes the *value* of an existing field in an existing body, in the direction of telling the
  truth, which is not an API change.

## Revisit when

* **A fourth application grows a runtime-settings surface** — at which point the shared-package
  question is asked with the shape, the precedence and the behaviour all settled, and the answer
  may well flip.
* **A runtime-changeable key gains a value expensive or dangerous to get wrong** — a credential, a
  path, anything with a side effect on write. Rule 1's "serve the configured value and carry on" is
  right for a tuning number and would need re-arguing for a key whose fallback is itself an action.
* **A stored row is found unreadable in production and the operator could not tell from the
  surface** — that is rule 1 clause 2 being owed rather than optional, and it would make the fix a
  defect rather than a scheduled tidy.
