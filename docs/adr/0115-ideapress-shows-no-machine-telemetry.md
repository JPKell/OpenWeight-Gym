# ADR-0115 — IdeaPress shows no machine telemetry

**Status:** Accepted (2026-09-07)
**Relates to:** [ADR-0038](0038-one-model-at-a-time-per-gpu.md) (the serialise-and-unload
invariant IdeaPress meets without a preflight), [ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md)
(the precedent for a leaf application routing through another one), [architecture/graceful-degradation.md](../architecture/graceful-degradation.md)
§2 footnote ⁴.
**Source:** Row M3 of [outstanding work §1](../roadmap/outstanding-work.md), out of the L8 finding
that `apps/ideapress/spec.md` §16 promised a display nothing built.

## Context

`show_telemetry_bar` (`IdeaPress/src/ideapress/web/rendering.py`) is a Jinja global hard-coded
`False`, never overridden anywhere, and no template branches on it — the widget it was meant to gate
does not exist. `sweatmeter` is imported exactly once, in `services/diagnostics.py`, purely as a
presence probe: `doctor`'s `telemetry` finding reports whether `ideapress[telemetry]` is installed,
because `INSUFFICIENT_VRAM` (ADR-0038) is only ever raised when it is. Nothing anywhere reads a
`TelemetrySnapshot`.

Row L8 found this and left it `untested` in the degradation matrix rather than writing a test that
would assert spec §16's sentence back at itself (ADR-0042) — the matrix's three IdeaPress
machine-condition rows (**No GPU present**, **`nvidia-smi` missing or failing**, **GPU sensor
unavailable**) describe a widget whose "degraded" state is trivially true only because it is
unconditionally hidden. This row was scheduled to close that gap by deciding, not building blind:
either wire the bar to the SweatMeter reader LoadCoach's `base.html` already demonstrates, or remove
the promise.

The question that decides it is not "can IdeaPress render a GPU row" — LoadCoach's precedent proves
it can — but whether IdeaPress has any decision behind that row once rendered. IdeaPress does not
schedule work on the machine: every backend call either goes to a local process it starts and stops
around one stage at a time (ADR-0038's serialise-and-unload invariant, which needs no telemetry to
hold) or routes through LoadCoach, which owns admission, residency and the machine's telemetry
surface for every request it accepts (ADR-0040). A GPU reading in IdeaPress's own UI would describe
a machine state IdeaPress never acts on — it cannot deny a request, delay a stage or choose a smaller
model on the strength of it, because those decisions already happened, or will happen, somewhere
else.

## Decision

**IdeaPress shows no machine telemetry.** `show_telemetry_bar` and the dead template branch it
would have gated are removed. `apps/ideapress/spec.md` says plainly that IdeaPress shows no machine
telemetry and why, in place of the promise at §16 and the "(status display only)" gloss at §5.
`architecture/graceful-degradation.md` marks the three affected rows `n/a — ADR-0115` rather than
leaving them `untested`, in both §2 and its §2.1 row index, and drops footnote ⁴.

`sweatmeter` keeps its one real job: the `[telemetry]` extra and `services/diagnostics.py`'s
presence probe survive unchanged, because `doctor`'s `telemetry` finding is a user-visible
capability flag a test exercises (`test_telemetry_absence_explains_what_it_means_rather_than_complaining`)
and `INSUFFICIENT_VRAM` genuinely does depend on it. What changes is only the label: every place
that called this extra's purpose "status display" (`pyproject.toml`'s comment, `README.md`, the CI
install-check comment) now says what it actually gates — the VRAM preflight — rather than a display
that was never built.

## Alternatives considered

**Wire the bar to the SweatMeter reader, as LoadCoach's `base.html` does.** This is the option the
row's own kickoff put first, and it is buildable — LoadCoach is the reference implementation. It is
rejected because it would add a per-page-render telemetry read for a display with no decision
behind it: LoadCoach shows the bar because LoadCoach's admission control reads the same numbers to
decide whether to admit a job; IdeaPress would be reading them to draw a row nothing downstream
consults. Building it would also mean writing the three now-`untested` rows' tests against a
genuine behaviour, which is more code and more surface for a widget whose only argument for existing
was that the spec already promised it.

**Leave the flag `False` and the rows `untested`, and let G20 stay blocked on it.** Rejected: this
is the status quo the row was scheduled to end. A documented behaviour that is not implemented is
not proved by leaving it alone, and G20 (every degradation row has a test) cannot turn on while a
promised display sits unbuilt with no scoping record, the way ADR-0111 scopes ToolYard's podman rung
rather than leaving it an open question forever.

## Consequences

* `show_telemetry_bar` and its explanatory comment are gone from `rendering.py`; no template ever
  referenced it, so no template changes.
* The three IdeaPress cells in `graceful-degradation.md` §2 and §2.1 read `n/a — ADR-0115` instead
  of a `D` outcome that was never really conditional, and instead of `untested`. G20's remaining
  blocker for IdeaPress is closed; LoadCoach's own `untested` cell (the `FreeWeightClient` version
  gap) is unaffected and is row M2's to close.
* `apps/ideapress/spec.md` §5's dependency table and §16's cross-platform note both name the real
  reason `sweatmeter` is an optional extra — the VRAM preflight — instead of a display purpose that
  never existed.
* No behaviour changes for an operator who never installed `ideapress[telemetry]`. An operator who
  did installs it for the same reason as before: `INSUFFICIENT_VRAM` becomes reachable. Nobody ever
  saw a telemetry bar, so nobody loses one.

## Revisit when

IdeaPress ever schedules or measures work on the machine itself — a local benchmark it runs rather
than requests through LoadCoach or a direct backend, or an admission decision it makes rather than
delegates. At that point it has a decision telemetry could inform, and this record's premise no
longer holds.
