# ADR-0053 — Tools are registered in code, refused in order, and a refusal is a result

**Status:** Accepted (2026-09-02)
**Extends:** [ADR-0018](0018-external-benchmark-isolation.md) (tiered isolation ending in refusal),
[ADR-0026 §3](0026-local-http-hardening.md) (outbound fetch checks),
[Master Architecture §11](../architecture/master-architecture.md) items 8, 11 and 12,
[Security Standards](../standards/security-standards.md).
**Relates to:** [ADR-0056](0056-every-turn-executes-under-one-execution-intent.md) (the per-turn
allowlist is an intent field), [ADR-0045](0045-promptcadence-reaches-models-only-through-loadcoach.md)
(the other place this application's risk concentrates).
**Source:** [PromptCadence roadmap §2, D-9](../roadmap/promptcadence-roadmap.md);
[ToolYard spec](../packages/toolyard/spec.md).

## Context

Nothing in the suite has ever executed a real, side-effecting tool on a model's behalf. FreeWeight
runs untrusted *code*, but it is the benchmark's code under a scorer the suite wrote, isolated by
[ADR-0018](0018-external-benchmark-isolation.md). LoadCoach deliberately never executes tools at
all. IdeaPress's rule is that a model's output is data, never an instruction.

PromptCadence breaks that streak by design: an agent loop whose steps read files, write files, run
commands and fetch URLs, with the tool name and every argument originating from a model that must
be assumed adversarial — prompt injection through a tool result is not a hypothetical here, it is
the expected attack. So this is the point at which the suite's riskiest behaviour concentrates, and
the discipline around it is the deliverable, not the tools.

Two forces pull against each other. Concentrating execution in one package means one place to get
right and one place to audit — and it means a second consumer (IdeaPress's specified but unshipped
`research` stage) inherits the discipline instead of re-deriving it. But a shared executor is also
where a plugin system would naturally grow, and a plugin system is a supply of unreviewed code
sitting on the wrong side of the trust boundary.

The failure mode that matters most is subtle: a Python library's instinct is to raise on bad input.
Here the "bad input" is written by the model, and an exception propagating out of a tool call ends
the turn, and often the trajectory. That hands the model a control-flow lever — ask for a tool that
does not exist, and the run stops — in an application whose first principle is that Python decides
control flow.

## Decision

**Tool handlers are Python objects registered in code at startup; every failure a model can
influence is a structured result; isolation and fetch discipline are inherited verbatim from the
records that already own them.**

1. **Registration is code, at startup, or it does not happen.** The application constructs handlers
   and calls `ToolRegistry.register(spec, handler)`. There is no loading of tool code from
   configuration, from a plugin directory, from an entry point, or from anything a model emitted.
   Lookup is by exact name; a duplicate registration raises at startup, where a person sees it.
2. **The invocation allowlist is separate from the registry**, and it narrows: a trajectory carries
   an allowlist that is a subset of the registry, and each `ExecutionIntent` carries a frozen subset
   of that ([ADR-0056](0056-every-turn-executes-under-one-execution-intent.md)). Registered does not
   mean callable.
3. **Refusal order is fixed and recorded:** registry → allowlist → schema → egress → containment.
   The reason names the **first** failed check, so a refusal is diagnosable from the record alone
   without re-running anything.
4. **Model input never raises.** Everything the model can influence — the name, the arguments, the
   output size, the runtime — resolves to a `ToolResult` with a status (`OK`, `REFUSED`, `FAILED`,
   `TIMEOUT`) and a machine-readable reason. Exceptions are reserved for **caller bugs**: a bad
   registration, an invalid spec, a broken store. A test drives every refusal path through
   `execute()` and asserts nothing escapes. One refused tool call is fed back to the model as a
   result and the loop continues; it is not a reason to end a trajectory, and it must not become
   one by accident.
5. **`run_command` reuses ADR-0018's ladder verbatim: container → bwrap → refuse.** Where no
   isolation tier is available the tool refuses with `isolation_unavailable`. Commands are argv,
   never a shell string; no `shell=True` exists anywhere in the package and a test greps for it; the
   child's environment is an explicit allowlist, never `os.environ`.
6. **`http_fetch` performs ADR-0026 §3's checks itself** — scheme, host allowlist (loopback only
   when the allowlist is empty), literal-IP comparison after DNS resolution, re-checked on **every**
   redirect hop, and a size cap enforced during streaming — inside the tool, so no consumer can
   forget one. The test vectors are shared byte-for-byte with LoadCoach's evidence-import fetch,
   because the same checks defended against the same class of request there (risk S9).
7. **Every call is recorded**, refused and failed included, with `redact_args` honoured (hash
   stored, plaintext never). Timeouts are mandatory; `None` means the default, never "no timeout".

## Alternatives considered

**Dynamic tool loading** — handlers named in configuration, discovered through entry points, or
reached through an external tool-server protocol. This is the industry default and the single most
requested feature such a component acquires, and the argument for it is real: an operator can add a
tool without a release. Rejected, and expected to stay rejected. The allowlist would become a
function of files on disk rather than code someone reviewed; a tool arriving through configuration
has no reviewed argument schema, no risk class and no egress class, so the refusal order above would
be checking properties nobody assigned; and it puts an extension point on the wrong side of the
trust boundary, in the one component whose stated threat model is that its inputs are adversarial.
Master architecture §11.12's rule — no new infrastructure without an ADR demonstrating a concrete,
present need — applies, and no consumer has one.

**Raise on refusals, the way a Python library normally would.** Idiomatic, and it makes misuse loud.
Rejected: the model chooses the input, so the model chooses when the exception fires, and an
exception crossing the agent loop is a stop condition the model controls. The defensive fix — a
`try/except` around the loop — is where broad exception swallowing (§11.8) gets born, and it
converts every distinct refusal into one indistinguishable failure. Refusals are data because
refusals are *normal* here.

**Let each application implement its own tool execution.** PromptCadence needs it now; IdeaPress's
`research` stage is specified but unbuilt, so the second consumer is not yet real. Genuinely
arguable against [ADR-0011](0011-shared-package-boundaries.md)'s "nothing is extracted with fewer
than two real consumers". Rejected because the thing being shared is not convenience code — it is
the redirect check, the resolution-then-compare containment rule and the isolation floor, and a
second implementation is a second chance to omit one silently. Where the duplicate would be a
security control rather than a helper, the second-consumer rule yields.

**Run the command unisolated when no tier is available, with a loud warning.** Rejected verbatim
per ADR-0018, which already fought this argument for benchmarks: a warning is not a containment,
and the deployment where no tier is available is exactly the one nobody is watching. Refusal is the
floor, on every platform, including the ones where it makes `run_command` unavailable.

**Put the fetch checks in the caller and let the tool take a validated URL.** Slightly cleaner
layering. Rejected for the reason the check exists: a caller who forgets is a caller who has an
SSRF, and the redirect hop is the part everyone forgets. The check belongs where the socket is
opened.

## Consequences

* ToolYard is the one place the suite executes side effects for a model, and its threat model is
  written down as such: arguments are attacker-controlled, results are attacker-influencing, and its
  job is that neither reaches the filesystem outside containment, the network outside the allowlist,
  or a shell.
* **A sequencing obligation, not a preference:** no tool executes inside PromptCadence before the
  discipline it depends on is published. PromptCadence P4 may not overlap ToolYard P2–P3, and the
  roadmap records that as a security ordering.
* `run_command` is unavailable on macOS and Windows until a platform tier exists — it refuses,
  visibly, with `isolation_unavailable`. Every other tool works everywhere. That is a real product
  limitation and it is preferred over an unisolated fallback.
* Adding a tool is a code change and a release. That is the intended friction; the registry is a
  reviewed list, and its shortness is a feature.
* Because refusals are results, the model *sees* them — which means refusal text is part of the
  prompt surface and is written to be useful without being exploitable (it names the failed check,
  never the containment roots' full contents or the allowlist).

## Revisit when

* **A platform sandbox tier is added** (a macOS or Windows isolation implementation) — the ladder
  gains a rung, in the same order, with refusal preserved as the floor.
* **A consumer demonstrates a concrete need for dynamic tool loading.** Expect no: that is the
  alternative this record rejects on the merits, and reopening it requires naming the consumer, the
  tools it cannot register in code, and how an unreviewed handler acquires a risk class and an
  egress class before a model can call it.
