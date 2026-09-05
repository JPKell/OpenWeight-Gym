# Kickoff — C2: ToolYard Phase 1

**Row:** C2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Opus 5 · xhigh. **Repository:** `/home/jpk/ai/suite/py/ToolYard` — it exists, is
`git init`-ed with one commit (`eb708dd`) carrying the suite's canonical `.gitignore`, and has
`origin` configured; **everything else is yours to create.**
**Runs after:** A2, which is **done** — `baseaicore 0.4.1` is on PyPI. Independent of B1–B5 and of
C1 (which is **built and pushed**); it may run before, after or beside them.
**Overnight:** permitted ([model-assignment §2.12](docs/roadmap/model-assignment.md) — only
batches D, G and I2's security half are barred).

**Why this row is Opus at xhigh, and what that means for how you spend the session.** ToolYard is
the one place in the suite that will execute a real, side-effecting operation on a model's behalf,
and Phase 1 builds none of the dangerous parts: no sandbox, no subprocess, no fetch, no built-in
tools. What it builds is *the discipline those parts will be poured into* — the fixed refusal order,
the "model input never raises" contract, the record, and the seams. Two consequences for how you
work:

* **The FakeProvider lesson** ([model-assignment §3](docs/roadmap/model-assignment.md), row
  "ToolYard P1"): a discipline layer must be stricter than its first consumer needs. Every later
  tool, in this package and in PromptCadence, inherits whatever rigour you set here — and a
  permissive executor hides the bug in the consumer, months later, where nobody is looking for it.
* **The next two phases are written by other models.** D1 (Phase 2, the sandbox) is **Fable 5 ·
  xhigh, daytime, reviewed**; E2 (Phase 3, the built-ins) is **Sonnet 5 · high**. They implement
  into the seams you leave. A seam that is under-specified — a containment check with no port to
  call, an egress decision with no declared input — is where that work will improvise, in the one
  package whose stated threat model is that its inputs are adversarial. **Designing those seams is
  the deliverable of this session, on a par with the code.**

Budget the session accordingly: the four undetermined shapes in "The work" §2, the structural
enforcement of the refusal order in §4, and the fuzz corpus in §7 deserve more of your time than
`registry.py` does.

---

## Preconditions

* **`baseaicore` is at `0.4.1` on PyPI, which is what this arc pins.** The
  [development plan](docs/packages/toolyard/development-plan.md) pins `>=0.4.1`. Pin
  `>=0.4.1,<0.5`. You need `SuiteError`, `Clock`/`utc_now`, `monotonic_ns`/`elapsed_ms`,
  `canonical_json` and `sha256_of`. `DataClassification` is **not** ToolYard's: a tool result that
  introduces data above a ceiling is PromptCadence's `classification_exceeded` deviation
  ([lifecycle §5](docs/apps/promptcadence/lifecycle.md)), not a ToolYard refusal — ToolYard's own
  vocabulary stops at `RiskClass` and `EgressClass`.
* **The remote already exists** — `origin` → `https://github.com/JPKell/ToolYard.git`. Commit on
  `main`. **Do not push, do not tag, do not publish**; list the push and the first-CI-green
  confirmation in the handoff as operator steps (the B2/C1 precedent). `toolyard 0.1.0` ships at the
  end of Phase 3, row E2 — two phases away, which is why nothing here is published and why the
  public surface you commit is still cheap to correct.
* **The PyPI name `toolyard` is free.** `https://pypi.org/pypi/toolyard/json` → **404**, checked
  2026-09-02; the documented fallback `aisuite-toolyard` is also 404. Re-check and record the result
  in the handoff (master architecture §1.1 requires availability verified before first publish);
  the fallback would change the import name, `pyproject.toml`, `.importlinter`, the coverage paths
  and every document that names the package, so if you find it taken, stop and say so rather than
  renaming anything.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/ToolYard`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  ToolYard section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2
  (lines 192–205 — six bullets, each of which is a test you owe; four of them are Phase 1's), then
  the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations` in every module; units in every numeric name (`duration_ms`, `timeout_seconds`,
  `max_bytes` — the spec's names are already correct, keep them); keyword-only for anything optional
  or boolean; `@dataclass(frozen=True, slots=True)` for every value object; line length 100;
  `mypy --strict` with no bare `Any` at a public boundary and no `# type: ignore` without a trailing
  reason. Note that JSON Schema documents are genuinely `Mapping[str, Any]` — that is the one place
  `Any` is correct, and the docstring should say why.
* **Injection:** the wall clock (`Clock`, defaulting to `utc_now`) for `started_at`, and a
  **separate injected monotonic source** for `duration_ms` — a wall clock cannot measure a duration
  and a test cannot make `time.monotonic_ns()` deterministic. `modelrack/cache.py` is the precedent
  (`clock: Callable[[], int] = monotonic_ns`); read its docstring before you invent a second
  convention.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, `CHANGELOG.md` started, one Conventional
  Commit per logical group. **Name the interpreter and the exact invocation in the handoff doc**
  (M5C-13). There is no `python3.12` on this machine; say which you used.
* **Dependency budget:** ToolYard's allowance is **2** — `jsonschema` and `httpx`
  ([gold-standards §1.1](docs/standards/gold-standards.md)). Phase 1 needs `jsonschema>=4,<5` and
  nothing else at runtime; `httpx>=0.27,<1` belongs to `http_fetch` in Phase 3. Decide deliberately
  whether to declare it now or at E2, and say which in the handoff — an undeclared dependency at
  publish time and a declared-but-unimported one both have a cost, and the E2 session should not
  have to guess which you intended. `hypothesis` is a **dev** dependency and does not touch the
  budget (the CutCtx precedent).
* **Documentation is mirrored.** The workspace copies under
  `/home/jpk/ai/suite/docs/packages/toolyard/` are authoritative; copy `spec.md` and
  `development-plan.md` byte-identically into the repo's own `docs/packages/toolyard/` and verify
  with `cmp` ([outstanding-work §4](docs/roadmap/outstanding-work.md)).

## Setup

```bash
cd /home/jpk/ai/suite/py/ToolYard      # exists: .git (one commit) + the canonical .gitignore
python -m venv .venv && source .venv/bin/activate
# copy the toolchain from py/CutCtx — the freshest sibling, built for this same arc last session,
# and the only one that already carries the hypothesis wiring you need:
#   pyproject.toml  .importlinter  .editorconfig  .pre-commit-config.yaml
#   .github/workflows/  requirements/  CONTRIBUTING.md  LICENSE  SECURITY.md
# adapt names, then:
pip install -e ".[dev]" && pre-commit install
```

**Do not overwrite `.gitignore`** — it is the suite's canonical one and already carries
`.hypothesis/` (C1 confirmed it). `pre-commit` may not be installed on this machine; if
`pre-commit install` fails, say so in the handoff and note that its hooks are all covered by the
gate or by CI (the C1 precedent).

Copy, do not invent: eleven repositories now share this toolchain, and a twelfth that differs is a
CI failure nobody expected. Regenerate `requirements/*.lock` with **pip-tools 7.6.1** the way C1
did, and read `docs/history/C1_HANDOFF.md` §7 first — it records a pip-tools trap (`--no-index` written into the
header) that will otherwise cost you twenty minutes. The coverage floor for a shared package is
**95 %**; ToolYard's spec §18 states it explicitly.

## Reading list

1. [`docs/packages/toolyard/spec.md`](docs/packages/toolyard/spec.md) — §7 is the normative public
   API and you implement it as written, *except* where §2 below says it under-determines a shape.
   §11 (public contracts) is what the tests exist to prove; §13 is the error table, one row per
   test; §14 is the threat model; §15 the performance targets; §17 the logging rule; §18 the test
   strategy; §20 the acceptance criteria (1–3 land in later phases; 5 is yours).
2. [`docs/packages/toolyard/development-plan.md`](docs/packages/toolyard/development-plan.md)
   **Phase 1** — the file layout, the test list, the two acceptance criteria and two named likely
   failure modes you are expected to have already defended against. **Read Phases 2 and 3 as well**,
   not to implement them but because their opening line is the ordering rule that shapes your work:
   "the refusal machinery and containment exist and are tested *before* any handler that could do
   harm, so at no commit in this repository's history does an unvalidated model argument reach a
   side effect."
3. [ADR-0053](docs/adr/0053-a-refused-tool-call-is-a-result-not-an-exception.md) (**D-9**) — the
   decision this package exists to obey; decisions 1–4 and 7 are entirely Phase 1. Read
   *Alternatives considered* in full: "raise on refusals, the way a Python library normally would"
   is the design your instincts will reach for at the first awkward moment, and the reason it was
   rejected (the model chooses the input, so the model chooses when the exception fires) is exactly
   what your fuzz suite is asserting. Read *Consequences*' last bullet too — refusal text is part of
   the prompt surface, so a reason names the failed check and never the containment roots' contents
   or the allowlist's members.
4. [ADR-0056](docs/adr/0056-every-turn-executes-under-one-execution-intent.md) §§1–2 — where the
   allowlist actually comes from in the real consumer: an immutable `ExecutionIntent` per **turn**,
   carrying `approved_tools` as a frozen subset of the trajectory allowlist. This is load-bearing
   for decision (a) in §2 below.
5. [ADR-0018](docs/adr/0018-external-benchmark-isolation.md) — the container → bwrap → **refuse**
   ladder, verbatim. You implement none of it; you leave the seam it plugs into, and you make
   `isolation_unavailable` reachable and tested *before* any code exists that could run a command.
6. [ADR-0026 §3](docs/adr/0026-local-http-hardening.md) — the fetch discipline, Phase 3's work.
   Read it for one Phase-1 purpose only: it tells you what `EgressClass.NETWORK` will have to mean
   at the executor's egress check, so that check is not retrofitted at E2.
7. [ADR-0016](docs/adr/0016-unavailable-is-not-zero.md) — an unenforceable limit is reported, not
   assumed (spec §14's last bullet). Phase 1 sets the vocabulary that Phase 2's resource limits use.
8. [`docs/apps/promptcadence/lifecycle.md`](docs/apps/promptcadence/lifecycle.md) §5, the deviation
   matrix — specifically the `undeclared_tool` row, which distinguishes *outside the intent* (a
   drift the app handles) from *outside the trajectory allowlist* (refused outright, recorded,
   never re-approvable). Your `not_allowlisted` refusal is the second of those, and the record is
   what the app reads. Plus [`docs/apps/promptcadence/spec.md`](docs/apps/promptcadence/spec.md)
   §14, the consumer's threat model in its own words.
9. `py/CutCtx` — the repository-shape precedent and the freshest example of this arc's discipline;
   `docs/history/C1_HANDOFF.md` §§5–7 for how a "there is only one path" guard was made structural and proven to
   bite, which is the same problem you have in §4 below.

## The work

Phase 1 is the vocabulary, the registry, the executor's fixed refusal order and the record —
against a harmless fake tool. No sandbox, no subprocess, no network, no built-in tools.

### 1. `types.py` — the vocabulary, including four names §7 uses but does not define

`ToolSpec`, `ToolContext`, `ToolCallRequest`, `ToolResult`, `ToolCallRecord`, `RiskClass`,
`EgressClass`, `ToolStatus`, plus `wire_definition()` with a committed golden. Four of §7's names
appear only as annotations and are yours to define: **`ToolOutput`** (what a `ToolHandler` returns —
and note that `ToolResult.content` is size-capped and `ToolCallRecord` wants a `result_sha256`, so
decide whether the handler returns text, structured content, or both, and where the hash is taken),
**`ToolCallRequest`** (name + args + whose `invocation_id`?), **`RegisteredTool`** (does it expose
the handler, and to whom), and **`IsolationTier`** (the enum belongs in Phase 1's vocabulary even
though nothing probes for a tier until D1 — a Fable session should find the enum waiting, not invent
one).

`ToolSpec.name` is `^[a-z][a-z0-9_]{1,63}$` and that is a *spec* validation (`InvalidToolSpec`,
a caller bug, raises) — not a refusal. A **model**-supplied name that does not match the pattern is
`unknown_tool`, because it cannot be in the registry. Get that distinction right in both directions;
it is the first place the raise/refuse boundary bites.

Contract 7 — wire definitions are provider-neutral and **byte-stable**, because PromptCadence hashes
them into turn records. Use `baseaicore`'s `canonical_json` and `sha256_of` rather than a second
convention; commit the golden; and make the ordering of `wire_definitions(names)` a documented part
of the contract rather than an accident of the input list.

### 2. The four shapes to settle deliberately — and record for D1, E2 and E4

Each of these is under-determined by spec §7. Settle it, document the reasoning in the docstring,
and record it in the handoff under a heading the next three sessions will find. Where your answer
contradicts the spec as written, **say so explicitly and propose the spec amendment** — an
underdetermined spec passage is a defect to close, not to work around silently
(`CLAUDE.md`: if an architectural decision seems missing, that is a defect in the docs).

* **(a) Where the allowlist lives.** §7 puts `allowlist: frozenset[str]` on the `ToolExecutor`
  constructor; ADR-0053 decision 2 and ADR-0056 §1 say the callable set is a **per-turn** frozen
  subset carried on an `ExecutionIntent`. A constructor-scoped allowlist means PromptCadence builds
  an executor per turn, or subverts the design. Decide where it goes (constructor, `ToolContext`,
  the request, or both with a documented intersection), and remember which direction is safe: an
  allowlist that can only *narrow* per invocation cannot be widened by a model, while a per-call
  allowlist that replaces the constructor's can. Whatever you choose, `not_allowlisted` must remain
  check #2 in the order.
* **(b) Where "egress is permitted" comes from.** §13 has the refusal (`egress_not_permitted`) and
  §11.2 has it fourth in the order, but §7 gives the executor **no input** from which to decide it.
  It is per-invocation in the real consumer (a trajectory's tier and classification decide whether
  network is allowed at all). Define the input, and make the default closed.
* **(c) The sandbox seam.** Containment is check #5 in a fixed order, but `sandbox.py` is D1's file
  and `Sandbox` does not exist yet. Do **not** ship a permissive stub that silently passes: define
  the port (a Protocol with `resolve_read`/`resolve_write`/`isolation_tier`/`run_isolated` exactly
  as §7 types them), make the executor depend on the port, and provide whatever Phase-1
  implementation is *honest* — a containment object over real roots is defensible; something that
  approves every path is not, and neither is a `None` sandbox that skips the check. The refusal path
  `path_escape` must be reachable and tested **in this phase**, because the ordering rule says the
  refusal machinery exists before the thing that could do harm. Say in the handoff exactly what D1
  must implement and what it must not change.
* **(d) Caps, timeouts and config surface.** Spec §12: constructor arguments only, no environment,
  no files. §11.8: timeouts are mandatory and `None` means the default, never "no timeout" — so
  where does the default live, and what enforces it in Phase 1 where no subprocess exists to time
  out (an in-process handler that sleeps past its limit is still a `TIMEOUT`, and the fake tool that
  proves it is yours to write). Name the content cap, the record-summary cap and the truncation
  label, and make the label part of the contract — "labelled if truncated" is a promise to a model
  that is reading the string.

### 3. `registry.py`

Registration at startup; duplicate name raises `DuplicateTool`; invalid spec raises
`InvalidToolSpec`; `get()` by **exact** name only (no fuzzy match, no case folding, no aliasing —
a near-miss is `unknown_tool`); `list_for_policy(max_risk=…, allow_egress=…)` with the ordering
documented; `wire_definitions(names)`. There is no unregister, no dynamic loading, no entry-point
discovery, and no code path that could grow one — ADR-0053 rejects it on the merits and expects it
to stay rejected.

### 4. `executor.py` — the module this row exists for

`execute()` runs registry → allowlist → schema → egress → containment, **in that order, always**,
and reports the **first** failed check. Two things are easy to write and wrong:

* A chain of `if` statements is an order anyone can reorder in a later patch and no test will
  notice, because most calls fail only one check. Make the order **structural** — a declared
  sequence of named checks the executor walks — and then write the test that proves it: a request
  that fails **all five checks at once** must report `unknown_tool`, and the same request with the
  tool registered must report `not_allowlisted`, and so on down the ladder. That is five assertions
  that are each about the order rather than about the check. (C1's "the invariants are the only
  path" guard is the same problem solved a different way; read how it was made to bite.)
* Nothing a model influences may raise — including the parts *after* the handler returns.
  Schema validation errors, oversize output, non-UTF-8 bytes, a handler that returns the wrong type
  or `None`, a handler that raises `KeyboardInterrupt`-adjacent things, an argument structure deep
  enough to blow the validator's stack: all of these are `REFUSED`/`FAILED`/`TIMEOUT` results.
  Decide explicitly what happens with `BaseException` and say why in the docstring.

`FAILED` carries the exception **class name**, message capped, and **no traceback to the model**
(§13). `TIMEOUT` names the elapsed time and the limit. `OK` with truncated content is labelled and
the full output's hash is recorded.

The record is appended for **every** call — OK, REFUSED, FAILED, TIMEOUT — with `redact_args`
honoured (`args_sha256` always present, `args_json` `None` when redacted; the plaintext never
reaches the record, not even truncated). The plan's named failure mode is "an executor path that
raises on a malformed record write": a broken store is a *caller* bug and `StoreFailure` is allowed
to raise, but decide what that means for a call whose side effect already happened, and whether the
result reaches the caller before the store does. Write the answer down; the app has to reason about
it.

Logging: none at INFO (library rule, §17). DEBUG under `toolyard.*` logs names and statuses,
**never arguments and never content** — and there is a test for that, because the whole point of
`redact_args` is defeated by one `logger.debug("args=%s", args)`.

### 5. `store.py` and `errors.py`

`ToolCallStore` Protocol plus an in-memory implementation for tests (and only for tests — say so in
its docstring; PromptCadence owns the real table, spec §10). `errors.py` per §7:
`ToolYardError` (`TOOLYARD_ERROR`), `DuplicateTool` (`TOOL_DUPLICATE`), `InvalidToolSpec`
(`TOOL_SPEC_INVALID`), `StoreFailure` (`TOOL_STORE_FAILURE`), all subclassing
`baseaicore.SuiteError`, all documented as **caller bugs only**.

### 6. Schema validation — the trap the plan names

`jsonschema`, draft 2020-12, and the plan's named failure mode: **"schema validation accepting extra
properties by default"**. It does, and a tool whose spec forgot `additionalProperties: false` is a
tool a model can pass extra arguments to. Decide whether ToolYard *requires* argument schemas to be
closed (validated at registration, an `InvalidToolSpec` when they are not), or merely documents it —
and note that requiring it is the strict-by-default choice that the FakeProvider lesson argues for.
Whatever you decide, `args_invalid` must carry **the validator's paths**, since that string goes
back to the model as its only clue, and a model that cannot see which argument was wrong will retry
the same call forever.

### 7. Tests — the fuzz suite is the deliverable

The plan's list is the floor: every §13 refusal row driven through `execute()` asserting
result-not-exception and the recorded reason; the refusal-order priority tests from §4; records for
all four statuses; redaction storing hash only; hashes stable; the wire-definition golden
byte-stable. Add the structural ones: the `shell=True` grep test over `src/` — **write it now**,
before Phase 2 makes it interesting, so D1 finds it already failing if it reaches for a shell — and
the import-linter contracts.

On those contracts, one piece of judgment: CutCtx's purity contracts forbid HTTP clients,
filesystem and subprocess outright, and ToolYard cannot copy that, because Phase 2 imports
`subprocess` and Phase 3 imports `httpx` **by design**. Do not write a contract the next session has
to delete — a deleted contract is indistinguishable from a weakened one in a diff. Write the
*layered* version instead: only the (future) sandbox module may import `subprocess`, only the
(future) `tools.fetch` may import `httpx`, and nothing in `src/` imports an application, a sibling
capability package or `setspec`. Say in the handoff which contracts D1 and E2 are expected to
*extend* and which they may never touch.

Then `tests/property/` (or `tests/fuzz/`), where the judgment lives. Acceptance criterion 1 is
"**no exception escapes `execute()` under a fuzzing test that mutates names, args and outputs**" —
and that criterion is trivially satisfiable by a generator that produces sensible names and
well-typed arguments. It is worth nothing unless the corpus contains the inputs a hostile model
would send. **Design the generators before the properties.** They must be able to produce, at
minimum:

* names that are empty, 10 000 characters, unicode, control characters, NUL bytes, path separators,
  `..`, names differing only by case or by a trailing space, names that match the spec pattern but
  are unregistered, and names that are registered but not allowlisted;
* arguments that are deeply nested, recursive-shaped, enormous, wrongly typed, `null` where an
  object is required, extra-propertied, containing NaN/Infinity, containing byte strings, and
  containing values that are themselves valid JSON Schema documents;
* handlers that return oversize content, non-UTF-8 content, the wrong type, `None`, an object whose
  `__str__` raises, that sleep past the timeout, that raise arbitrary exception classes, and that
  mutate the arguments mapping they were handed;
* specs whose schemas are themselves malformed or self-referential.

Prefer generating structurally-valid requests by construction over `filter`-ing invalid ones —
heavy filtering gives flaky health-check failures and useless shrinking. Pin a hypothesis profile so
a CI failure is reproducible, and say in the handoff **how a failing example is replayed** (the C1
precedent; note `pytest-randomly` randomizes order suite-wide, and a failure that only reproduces
under a seed is a real bug, not a reason to pin the seed).

The properties that follow are a floor, not a list to stop at:

* `execute()` returns a `ToolResult` for every generated input — no exception, of any class,
  escapes, including from the record-building and truncation paths;
* every returned result has a status, and every non-`OK` status has a **non-empty, machine-readable
  reason drawn from a closed set** — an unrecognized reason string is a bug, because PromptCadence
  maps reasons to deviation categories;
* exactly one record is appended per call, whatever the outcome;
* when several checks would fail, the reported reason is the earliest in the fixed order — as a
  property over generated combinations, not just the five hand-written cases;
* a redacted call's plaintext arguments appear nowhere in the record, in any field, at any length;
* refusal reasons never contain the allowlist's members or a containment root's contents
  (ADR-0053's prompt-surface consequence) — assert it as a property, since it is the kind of thing a
  helpful error message reintroduces;
* results are content-capped: no generated handler output produces a `content` above the cap, and
  every truncated one is labelled;
* determinism: the same request, spec set, allowlist and injected clocks produce byte-identical
  records.

Also the performance targets behind the `performance` marker (§15: dispatch ≤ 10 ms excluding the
handler), and — as C1 did — consider asserting the *shape* rather than only the absolute number.

**Write the rationale down.** The handoff gets a section naming each generator family and each
property, what it would catch, and — the part that matters — what you considered and rejected, with
why. That section is what D1 and E2 read before they extend the corpus with a sandbox escape and a
redirect chain.

### 8. Documentation and repository furniture

`README.md` (status line: Phase 1, unreleased; the register → execute → record shape and the fixed
refusal order belong in it, since "a refusal is a result, not an exception" is the single thing a
new caller gets wrong), `CHANGELOG.md` with `## [Unreleased]`, `LICENSE`, `SECURITY.md` and
`CONTRIBUTING.md` adapted from CutCtx — **rewritten, not renamed**: CutCtx's talk about transcripts
and plans, and ToolYard's `SECURITY.md` is the one in the suite that has something real to say.
Then the two mirrored documents under `docs/packages/toolyard/`, verified with `cmp`.

### 9. Gate and commit

The full gate green with the interpreter named. Commits on `main`, one per logical group. No tag,
no publish, no push.

## Before you finish — three closing duties

1. **Write `docs/history/C2_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands; the public surface as built against spec §7, naming every deviation and why;
   **the four settled shapes from §2** (allowlist scope, egress input, sandbox seam, caps/timeouts)
   as decisions D1, E2 and E4 must not relitigate, each with the spec amendment you propose if the
   spec as written now disagrees; **how the fixed refusal order is enforced structurally and how it
   is proven to bite**; the fuzz-corpus rationale from §7; the import-linter contracts and which
   later phases may extend which; the record/store answer from §4 (what happens to a completed side
   effect whose record cannot be written); the toolchain provenance and the `httpx` declaration
   decision; the commits made; and **"Before the next session"** — at minimum: push `main`, confirm
   CI green on the first push (the 3.12 blocking jobs and the 3.14 early-warning job cannot be run
   here), and the re-checked PyPI-name result. Add anything you found: a spec passage that was wrong
   or underdetermined, a trap the plan did not name. **Never overwrite an existing root file** — the
   workspace root is not a git repository. If `docs/history/C2_HANDOFF.md` exists, write `C2_HANDOFF.2.md` and
   say why.
2. **Summarise in chat**, briefly: what was built, what the gate said, the four shapes you settled,
   what the fuzz corpus covers and what it deliberately does not, and what is waiting on the human.
   A few sentences.
3. **Prepare the commits.** Everything committed on `main`, working tree clean, nothing pushed,
   nothing tagged. Say exactly what is waiting for the operator.

## Constraints and stop rules

* **No sandbox implementation and no subprocess.** `sandbox.py`, the isolation-tier probe and
  `run_isolated` are D1 (Fable 5). You define the port and the vocabulary; you implement no
  containment ladder and you spawn no process. Equally: **no permissive stand-in** — if the
  Phase-1 containment check cannot be honest, it refuses.
* **No built-in tools and no `http_fetch`.** Those are E2. The only tools in this repository at the
  end of the session are harmless fakes under `tests/`.
* **No dynamic loading, ever** — not from configuration, not from entry points, not from a plugin
  directory, and not "just for tests". ADR-0053 rejects it on the merits; a test helper that loads a
  handler by import path is the first step back toward it.
* **No model access and no provider JSON.** ToolYard never talks to a model; `wire_definition()`
  exports a neutral shape and the *caller* adapts it. No `modelrack`, no `setspec`, no sibling
  capability package, no application import — at module level, under `TYPE_CHECKING`, or in a test
  helper. The `.importlinter` asserts it, and **you never weaken `.importlinter`** to make an import
  work.
* **Tool arguments and tool results are untrusted, adversarial input** (spec §14). No argument is
  ever interpolated into a path, a command or a URL; no result is parsed, executed, or trusted to be
  well-formed text; no reason string is built by formatting an argument in without a cap.
* **No prompt text ever appears in this package.** A prompt is named by `prompt_id`
  ([ADR-0012](docs/adr/0012-prompt-storage-format.md)).
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` in this repo at the start and
  end of the session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/C2_HANDOFF.md`.
