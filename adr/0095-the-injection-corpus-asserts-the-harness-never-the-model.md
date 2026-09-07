# ADR-0095 — The injection corpus asserts the harness, never the model

**Status:** Accepted (2026-09-06)
**Amends:** [PromptCadence Spec §18](../apps/promptcadence/spec.md) — the Security row names the
corpus and what a case in it may assert; §14 gains the sentence that the corpus is a release gate.
**Relates to:** [ADR-0053](0053-a-refused-tool-call-is-a-result-not-an-exception.md) (a refused
call is a result), [ADR-0026 §3](0026-local-http-hardening.md) (fetch rules),
[ADR-0075](0075-a-request-carrying-tools-requires-tool-use-of-every-candidate.md) (tool
definitions on the wire), [ADR-0094](0094-the-console-authenticates-as-the-api-does.md) (model
text reaches a template).
**Source:** Row I2, decision 1. The vectors come from G1 §8, G2 §9–§10 and I1 §7.1.

## Context

The roadmap's risk table says the prompt-injection corpus is a release gate for 1.0. Nothing yet
says what a case in it is allowed to assert. A corpus written naively asserts what the model *did*
when attacked — that it refused, that it stayed on task — and such a corpus has two failure modes:
it passes today against a fake that does what it is scripted to do, and it rots the moment a
real model becomes more obedient or less, because the gate was measuring the model. A corpus that
fails when a model gets more obedient is a broken gate.

Spec §14 already states the properties the harness holds *whatever the model asks*: only
registry-listed tools are callable; arguments are schema-validated then sandbox-checked; egress is
evaluated from the trajectory's declared classification, never from model text; no model output
reaches a shell command, a path outside containment, or a fetch URL that skips ADR-0026 §3. Those
properties are model-independent by construction — they are decided by Python, before or after
the model, from facts the model does not control.

## Decision

**Every corpus case asserts a property of the harness. No case asserts what the model said.**

1. **A case is a hostile input plus a harness property.** The input is model output (a plan
   description, a tool call, a tool result replayed into the next turn, a task string) or
   caller-side prompt content (a tool description). The assertion is one of spec §14's
   consequences, checked in the record: which tool ran or was refused and with which reason, what
   the workspace holds, which host a fetch reached, which `EgressDecision` was written, what the
   wire carried. A case that would pass or fail depending on the model's phrasing is not a case.
2. **The corpus runs in CI against the fake LoadCoach, deterministically, and is the gate.** The
   fake scripts the model's answer; the harness's behaviour on that answer is what is measured. A
   red case blocks the release.
3. **A live pass is evidence, not the gate.** The same vectors may be run against a real model
   under the `live` marker; a live run that reaches a terminal state with every call recorded is
   written into the handoff as evidence that the fake was faithful. It is never what the release
   waits on, because it cannot be reproduced.
4. **The corpus asserts provenance of what the model is told, too.** Tool descriptions travel to
   the model (G2 §10). A case asserts the offered definitions are the registry's, verbatim — so a
   compromised description would be a caller bug, found by a test, and not a model behaviour.
5. **The corpus lives in `tests/security/`, one file, and every case names its property in its
   docstring.** The handoff carries the inventory: case → property → where asserted.

## What this refuses

* A case whose assertion is on `response.text`, on the model declining, or on the model calling
  the "right" tool.
* A case that needs a real model to run.
* Marking the corpus green by weakening a property (widening an allowlist, relaxing containment)
  rather than by fixing the harness.

## Alternatives considered

**Assert the model's compliance with the injected instruction.** The obvious reading of "the
injection corpus", and the useful measurement for choosing a model. Rejected as a *gate*: it is a
measurement of the model, it rots with every model change, and the roadmap's mitigation for
injection is the D-9 discipline — allowlist, schema, containment, egress checks — precisely
because those do not depend on the model. Model-compliance measurement belongs in FreeWeight, as a
capability, if anyone wants it.

**Run the corpus live only.** Honest about the real stack, and useless in CI: no GPU, no
determinism, no gate. The row's own kickoff names this — "a corpus that fails when a model gets
more obedient is a broken gate" — and the M11 beta shipped with the sandboxed-tool clause unmet
for exactly the reason a live-only proof cannot be scheduled.

**Assert both.** Tempting, and it puts a model-dependent assertion in a gating suite, which is the
thing rule 1 exists to prevent.

## Consequences

* The corpus is small and permanent: eight to twelve cases, each a few lines over the existing
  loop harness, and none needs revisiting when a model changes.
* Several of the corpus's properties are already held by integration tests written at P4, P6 and
  G2. The corpus names them rather than duplicating them, so one property has one test.
* A new model-output surface (I1 added two: the composed document and the console) gets a corpus
  case when it is added, asserting the reader's safety — escaping, structure — not the content.

## Revisit when

A surface appears where a model's output *is* the control flow — a native planning profile that
decides dispatch, say. Then the property is different and this record does not cover it.
