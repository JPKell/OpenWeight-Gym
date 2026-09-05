# C2 — ToolYard Phase 1 — Handoff

**Row:** C2 of `docs/roadmap/outstanding-work.md` §1. **Repository:** `/home/jpk/ai/suite/py/ToolYard`.
**Date:** 2026-09-03. **Model:** Opus 5 · xhigh.
**State:** Phase 1 complete, gate green, 14 commits on `main`, working tree clean.
**Nothing pushed, nothing tagged, nothing published.** See §12.

---

## 1. Gate results

Run from `/home/jpk/ai/suite/py/ToolYard`, interpreter **CPython 3.13.15** (`.venv/bin/python`,
created with `/usr/bin/python3.13`). There is no `python3.12` on this machine; `/usr/bin/python3.14`
also exists and was used for the extra run below.

```bash
cd /home/jpk/ai/suite/py/ToolYard
.venv/bin/ruff format --check --no-cache .      # 32 files already formatted
.venv/bin/ruff check --no-cache .               # All checks passed
.venv/bin/mypy src tests                        # Success: no issues found in 25 source files
.venv/bin/lint-imports                          # Contracts: 7 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                                # 361 passed, 4 deselected
.venv/bin/python -m pytest -q -m performance    # 4 passed
.venv/bin/python -m pytest -q --cov --cov-report=term-missing
                                                # Total coverage: 100.00% (floor 95%)
```

Tool versions: ruff 0.16.5, mypy 1.18.2, import-linter 2.6, pytest 9.1.1, hypothesis 6.167.1,
jsonschema 4.26.0, baseaicore 0.4.1.

**`--no-cache` on the ruff steps is not decoration.** A stale `.ruff_cache` reports a file clean
that CI then fails. That is exactly what happened to CutCtx (row C1): its session gate was green
while `tests/property/test_apply_property.py` held a real `I001`. Fixed this session in CutCtx as
commit `6d704bb` (unpushed) — see §13. `CONTRIBUTING.md` and `README.md` here both record the flag.

Two extra runs, neither part of the gate:

* **Python 3.14.4**, editable install, full suite: **361 passed**. The CI early-warning job should
  be green on first push.
* **Lockfile fidelity**: a clean 3.13 venv, `pip install --require-hashes -r requirements/ci.lock`
  then `pip install . --no-deps` (what CI does — a built distribution, not an editable checkout),
  full suite: **361 passed**.

## 2. PyPI name

Re-checked **2026-09-03T03:32Z**:

| Name | `https://pypi.org/pypi/<name>/json` |
|---|---|
| `toolyard` | **404 — free** |
| `aisuite-toolyard` (documented fallback) | 404 — free |

`toolyard` is claimed at the end of Phase 3 (row E2). Nothing to change.

## 3. The public surface as built, against spec §7

Everything in §7 is implemented as written except where listed below. Each deviation is an
**underdetermined or absent** passage rather than a disagreement, and each carries the spec
amendment it implies. `CLAUDE.md`: an architectural decision that seems missing is a defect in the
docs, to be closed rather than worked around.

| Change | Kind | Why |
|---|---|---|
| `ToolContext.approved_tools: frozenset[str] \| None = None` | **added field** | §7 has no per-turn narrowing; ADR-0056 §1 requires one. See §4(a) |
| `ToolContext.max_egress: EgressClass = NONE` | **added field** | §13 has `egress_not_permitted` and §7 gave the executor no input to decide it. See §4(b) |
| `ToolContext.timeout_seconds: float \| None` | **type widened** | §11.8 says `None` means the default; §7 typed it `float` |
| `ToolSpec.path_args: Mapping[str, PathAccess] = {}` | **added field** | §11.2's containment check has no input without it. See §4(c) |
| `ToolSpec.requires_isolation: bool = False` | **added field** | Makes `isolation_unavailable` reachable from `execute()` before Phase 3 exists. See §4(c) |
| `ToolResult.reason_detail: str \| None = None` | **added field** | §13 asks three rows to carry detail (validator paths, root and target, exception class) that a closed `reason` set cannot hold |
| `ToolCallRecord.reason` / `.reason_detail` | **added fields** | §11.2 promises a refusal is diagnosable *from the record alone*; that needs the reason in the record |
| `Reason` enum + `REFUSAL_REASONS` | **added** | The closed set PromptCadence maps onto deviation categories, made enumerable |
| `Reason.NOT_IN_INTENT` (`"not_in_intent"`) | **new refusal reason** | Lifecycle §5 distinguishes outside-the-intent (drift) from outside-the-allowlist (never re-approvable); §13 had one reason for both. Minor per §19 |
| `RiskClass` / `EgressClass` are ordered ceilings | **behaviour** | `list_for_policy(max_risk=…)` filters by a maximum, so a rank beats a set and a third class needs no call site changed |
| `ToolSpec` validates in `__post_init__`, not in `register()` | **moved** | §7's comment puts spec validation at registration. Moving it to construction removes the possibility of a half-checked spec being passed around — the CutCtx precedent. `InvalidToolSpec` is still what a caller sees |
| `register()` raises only `DuplicateTool` | **consequence of the above** | Plus `InvalidToolSpec` if handed something that is not a `ToolSpec` at all |
| `wire_definitions(names)` sorts and de-duplicates | **strengthened** | Callers pass sets: an intent's `approved_tools` is a `frozenset` whose iteration order varies between processes, and these are hashed into turn records |
| `wire_definitions()` raises `baseaicore.NotFoundError` for an unregistered name | **added** | A caller bug (names come from the caller's own allowlist ⊆ registry). Skipping would silently shorten the tool list a model is shown. Uses an existing suite error rather than growing ToolYard's four-error tree |
| `ToolOutput`, `ToolCallRequest`, `RegisteredTool`, `IsolationTier` defined | as instructed | §7 uses them only as annotations |
| `SubprocessResult` defined | **fifth undefined name** | The kickoff listed four; §7 also names this one only as a return annotation. It carries `limits_unenforced: tuple[str, ...]` — ADR-0016's rule in the place Phase 2 needs it |
| `PathAccess`, `PathEscape`, `PathContainment` | **added** | The containment vocabulary and Phase 1's implementation. See §4(c) |
| `Sandbox` is a **Protocol** | **clarified** | §7 writes `class Sandbox`. The executor depends on the port so D1 can supply the implementation without touching `executor.py` |
| `ToolCallRequest` is `(name, args)`; `invocation_id` stays on `ToolContext` | **decided** | See §3.1 |

### 3.1 Why `invocation_id` is the context's and not the request's

The kickoff asked whose it is. It is the **application's**. A model that could choose the invocation
id could collide two records or point a result at another turn's call, and the record is what the
application reasons about afterwards. Keeping it on `ToolContext` (as §7 already does) and off
`ToolCallRequest` makes the trust boundary readable off the types: `ToolCallRequest` holds exactly
the model-supplied surface and is validated by nobody at construction; `ToolContext` holds only
application-supplied values and validates every one of them.

A provider's `tool_call_id`, which the application must echo back to the model, is a natural value
for the application to use *as* the `invocation_id` — it constructs the context per invocation.

### 3.2 Two strictnesses beyond what the spec requires

Both follow the FakeProvider lesson: a discipline layer must be stricter than its first consumer
needs.

* **Argument schemas must be closed.** `additionalProperties: false` (or
  `unevaluatedProperties: false`) is required at **every object-typed subschema with `properties`**,
  checked when a `ToolSpec` is constructed, not merely documented. The development plan names
  "schema validation accepting extra properties by default" as this phase's likely failure mode; a
  documented requirement is one that gets forgotten, and the nested case is where it actually gets
  forgotten. `InvalidToolSpec` names the failing path (`$.options`).
* **The `$ref` family is refused in a tool schema** — `$ref`, `$dynamicRef`, `$id`, `$anchor`,
  `$dynamicAnchor`, `$defs`, `definitions`. **This is a trap the plan did not name.** A `$ref` is a
  URI, and a validator handed an unresolved one attempts to *retrieve* it: an outbound fetch,
  originating in a tool declaration, in the package whose entire purpose is that egress passes one
  checked door. Refusing the keyword removes the door instead of guarding it. Format checking is
  also left off (jsonschema's default), because a `format: "uri"` checker is another parser running
  on model input and the checks that matter for a URL belong at the socket (ADR-0026 §3).

## 4. The four settled shapes — D1, E2 and E4 must not relitigate these

### (a) Where the allowlist lives: **both, intersecting, narrowing only**

* `ToolExecutor(..., allowlist=frozenset(...))` keeps spec §7's constructor argument. It is the
  **trajectory** allowlist.
* `ToolContext.approved_tools: frozenset[str] | None` is the **turn's** approved set, from the
  `ExecutionIntent` (ADR-0056 §1). `None` means "the trajectory allowlist stands alone".
* The effective set is the **intersection**. That direction is the whole safety property, so it is
  structural rather than remembered: an intersection has no widening case to get wrong. A test
  drives an `approved_tools` naming a tool the trajectory forbids and asserts it stays refused.
* `not_allowlisted` remains **check #2**, unmoved.

**Two refusals at that rung, in this order**, matching PromptCadence lifecycle §5's `undeclared_tool`
row, which distinguishes two things §13 gave one reason to:

1. `not_allowlisted` — outside the **trajectory** allowlist. Never re-approvable: the allowlist is
   the caller's, not the model's.
2. `not_in_intent` — inside the trajectory allowlist, outside **this turn's** approved set. The
   application's drift, resolvable by minting a superseding intent revision and retrying.

The trajectory refusal is reported first, deliberately: telling a model its call merely needs
approval, when no approval could ever grant it, invites a re-approval that can only fail.

Note that ToolYard **refuses** the intent-level case rather than allowing it and letting the app
notice afterwards. That is the strictly safer reading: the side effect has not happened, so a scoped
re-approval can still grant it. Allowing it would put the side effect before the approval.

> **Spec amendment proposed.** §7: add `approved_tools: frozenset[str] | None = None` to
> `ToolContext`. §13: add a `not_in_intent` row. §11.2: note that the allowlist check has two
> outcomes and that the effective set is an intersection which can only narrow.

### (b) Where "egress is permitted" comes from: **`ToolContext.max_egress`, defaulting closed**

`EgressClass` is an **ordered ceiling** (`NONE < NETWORK`) with `permits()`, and
`ToolContext.max_egress` defaults to `EgressClass.NONE`. A caller who has not thought about egress
gets the answer that cannot leak — the same posture ADR-0046 fixes for data classification and
ADR-0026 §3 for host allowlists.

Per-invocation rather than per-executor, because in the real consumer a trajectory's tier and
classification decide whether network is allowed at all, and those are turn-scoped facts.

A ceiling rather than a `bool` so a third egress class needs no call site changed. **For E2:** when
`http_fetch` lands, `EgressClass.NETWORK` at this check means only "this invocation may reach the
network at all". The ADR-0026 §3 checks — scheme, host allowlist, literal-IP after DNS, re-check on
**every** redirect hop, size cap during streaming — belong inside the tool, at the socket, exactly
as ADR-0053 decision 6 says. Do not move any of them up to this check, and do not treat passing this
check as having done any of them.

> **Spec amendment proposed.** §7: add `max_egress: EgressClass = EgressClass.NONE` to
> `ToolContext`. §11: state that the egress ceiling is per-invocation and defaults closed.

### (c) The sandbox seam — what D1 must implement, and what it must not change

**The port.** `toolyard.containment.Sandbox` is a `Protocol` with `resolve_read`, `resolve_write`,
`isolation_tier` and `run_isolated`, typed as §7 types them (`env` is
`Mapping[str, str] | None = None`, where `None` means the **empty** allowlist and never
`os.environ`). `ToolExecutor` takes one positionally and there is **no `None` option**: an executor
without a sandbox would have a fifth check that does nothing, and a check that does nothing is worse
than an absent one, because the fixed order would then be a claim rather than a fact.

**The Phase-1 implementation, `PathContainment`, is honest in both halves.**

* *Path containment is real.* Resolution-then-check (spec §11.3): a candidate is fully resolved —
  symlinks, `..`, relative components — and only the result is compared, by **path ancestry** and
  never by string prefix, so `/data` and `/database` are two roots. Read and write are separate
  checks against separate roots; a read root is readable and not writable. A relative candidate
  resolves against `paths.write_root`, **never** `Path.cwd()` — the process CWD is wherever the
  application started, not the trajectory's workspace.
* *Isolation is absent and says so.* `isolation_tier()` returns `IsolationTier.UNAVAILABLE`;
  `run_isolated()` raises a `ToolYardError` naming Phase 2. It is unreachable through `execute()`,
  because the executor refuses any `requires_isolation` tool at check #5 before a handler exists to
  call it. A stand-in reporting a tier it did not have would be the "warning instead of a
  containment" ADR-0018 rejects verbatim.

**How the containment check has an input at all.** `ToolSpec.path_args: Mapping[str, PathAccess]`
declares which **top-level string** arguments are paths and which root each is checked against. The
executor resolves each declared argument through the sandbox *before* the handler runs and
**substitutes the resolved path into the arguments the handler receives**. That is resolution-then-
check and the TOCTOU mitigation in one move: a handler operates on a resolved path and never
re-resolves a candidate. `ToolSpec` validates at construction that every `path_args` key is a
property the schema types as `string` — containment over an argument whose type is not pinned is
containment over something that might not be a path. Nested path arguments are **not expressible**,
deliberately: an argument the executor cannot see is one it cannot contain.

**Check #5's internal order is a decision, not an accident.** Isolation first, then paths. A tool
that cannot run *at all* on this host is refused before its arguments are resolved, so a model is
told the unfixable fact first instead of correcting a path and then hitting a wall it could never
have crossed. A test pins it.

**D1 must:**

* add `toolyard/sandbox.py` with the tier probe (container → bwrap → refuse, ADR-0018 verbatim, the
  probe executing a canary rather than trusting a version string) and `run_isolated` (argv only, env
  allowlist, resource limits recorded when unenforceable per ADR-0016, process-tree kill on timeout);
* **compose or subclass `PathContainment` for the path half — do not re-derive it.** A second
  resolution-then-check implementation is a second chance to compare before resolving;
* import `SandboxPaths`, `IsolationTier`, `SubprocessResult` and `PathAccess` from
  `toolyard.containment`; they are Phase 1's vocabulary and must not be redefined;
* extend `tests/unit/test_containment.py`, never relax it. It is the containment contract;
* add `toolyard.sandbox -> subprocess` usage — the `.importlinter` exemption is **already written**,
  so D1 adds a module and changes no boundary rule.

**D1 must not:**

* weaken or delete any `.importlinter` contract;
* give `PathContainment` (or its successor) a flag that skips resolution, compares before resolving,
  or widens a root per call. A "just this once" option is what makes a containment advisory;
* make `Sandbox` optional on the executor, or let a missing tier fall through to an unisolated run;
* change the fixed refusal order or check #5's internal order without an ADR;
* introduce `shell=True`. `tests/unit/test_boundaries.py` parses every module under `src/` and fails
  on any call passing a `shell` keyword — written this phase, so it is already there when D1 arrives.

One honest boundary, pinned as a test with its reasoning:
`test_a_symlink_loop_stays_inside_the_root_rather_than_crashing`. `Path.resolve()` gives up on a
cycle and returns the path unresolved; that path is under the write root, so containment admits it,
and the OS refuses to open it (`ELOOP`). Correct today. D1's `O_NOFOLLOW`/dirfd work is where the
difference between "inside the root" and "openable" stops being academic.

> **Spec amendment proposed.** §7: add `path_args` and `requires_isolation` to `ToolSpec`; add
> `PathAccess`; define `SubprocessResult`; state `Sandbox` as a Protocol. §11.3: add that a
> declared path argument is resolved by the executor and handed to the handler already resolved.
> §13: note that `path_escape` names root and target **in the record**, and the root's *role* to the
> model (see §6).

### (d) Caps, timeouts and the configuration surface

Constructor arguments only. ToolYard reads no environment and no files (spec §12), and every cap is
validated at construction so a misconfigured executor fails at startup rather than on the one call
that overflowed.

| Constant | Default | Meaning |
|---|---|---|
| `DEFAULT_TIMEOUT_SECONDS` | `30.0` | Applied when `ToolContext.timeout_seconds` is `None` |
| `DEFAULT_MAX_CONTENT_BYTES` | `65_536` | What the model sees, UTF-8 bytes |
| `DEFAULT_MAX_SUMMARY_BYTES` | `4_096` | What the record holds — a row, not an artifact |
| `DEFAULT_MAX_ARGS_JSON_BYTES` | `16_384` | Above this, `args_json` becomes a size-and-digest object |
| `MIN_CONTENT_BYTES` | `256` | Floor for any configured cap, so a truncation label always fits |

* **`None` never means "no timeout"** (§11.8). `ToolContext.__post_init__` refuses a non-positive,
  infinite or NaN value; so does the executor's `default_timeout_seconds`. There is no sentinel, no
  zero and no negative that expresses an unlimited call, and that is the point.
* **The truncation label is part of the contract**:
  `TRUNCATION_LABEL_TEMPLATE = "\n…[truncated by toolyard: {kept} of {total} bytes]"`. The guarantee
  is on the *returned* string — never larger than the cap, label included — and truncation cuts on a
  character boundary. A model that assumes a result ended rather than stopped will answer from half
  a file, so the label states both byte figures rather than merely saying "truncated".
* **`args_json` is always valid JSON.** Oversize arguments become
  `{"__toolyard_args_omitted__":"oversize","bytes":N,"sha256":"…"}` rather than a fragment cut
  mid-string, so an application can always parse the field. When `redact_args` is set it is `None`
  and the plaintext reaches no field at any length.
* **The timeout is reported, not enforced, and the docstring says which.** An in-process handler is
  not interruptible in Python; a handler that must be *stopped* runs under `Sandbox.run_isolated`,
  where the process-tree kill lives (Phase 2). Phase 1 measures and, if the limit was exceeded,
  returns `TIMEOUT` and **discards the output** — a result the executor has declared timed out must
  not reach the model as if it had not. This is ADR-0016's posture applied to a limit this phase
  cannot enforce: reported, never assumed.
* **Two injected clocks, never one.** `ToolContext.clock` (wall, `Clock`, defaults `utc_now`) for
  `started_at`; `ToolExecutor(monotonic_ns=…)` (defaults `baseaicore.monotonic_ns`) for
  `duration_ms`. A wall clock steps backwards during an NTP correction and cannot measure a
  duration; `time.perf_counter_ns()` cannot be made deterministic in a test. The name and default
  follow `modelrack.cache`'s precedent rather than inventing a second convention. The timeout
  decision and `duration_ms` come from the **same** reading, so the sentence "elapsed 1.502 s
  exceeds the 1.000 s limit" never sits beside a `duration_ms` of 1503.

> **Spec amendment proposed.** §7: `ToolContext.timeout_seconds: float | None`. §12: name the four
> caps and the label as part of the configuration surface. §11: state that a `TIMEOUT` discards the
> handler's output, and that Phase 1's timeout is measured rather than enforced.

## 5. How the fixed refusal order is enforced structurally, and how it is proven to bite

**The mechanism.** The order is **data**. Each check is a frozen `_Check(position, name, run)`, and
`_CHECKS = _ordered((...))` sorts by `position` and raises `ValidationError` **at import time** if
the positions are not exactly `0..n-1`. Three consequences:

1. Rearranging the tuple literal changes nothing — it is sorted.
2. Duplicating or skipping a position stops the package importing, rather than quietly producing a
   ladder with two rungs at the same height.
3. Changing the order is a **one-number diff**, which is the smallest reviewable unit this could be
   reduced to.

`REFUSAL_ORDER` is exported (`("registry", "allowlist", "schema", "egress", "containment")`) so a
golden pins it. The checks are pure functions over one `_Pass` object; none can short-circuit
another.

**Proven to bite, four ways.**

1. `test_a_call_failing_every_check_walks_down_the_ladder_one_rung_at_a_time` — one request that
   fails registry, allowlist, intent, schema, egress, isolation **and** containment simultaneously,
   with each blocker removed one at a time. Seven assertions, each about the *order* rather than
   about the check: a chain of `if`s that someone reordered passes every individual refusal test and
   fails here.
2. `test_the_earliest_failing_check_is_the_one_reported` — the same claim as a **property** over
   generated combinations (300 examples), with the expectation from `tests/oracles.py`, which
   restates spec §11.2 over labels the generator attached when it built the world. It never asks the
   package what it thinks.
3. `test_the_ladder_refuses_to_import_with_positions_that_are_not_a_sequence` and
   `test_rearranging_the_declaration_cannot_rearrange_the_ladder`.
4. **Mutation.** Swapping the schema and egress positions: 1 test fails. Making `unknown_tool` fire
   only when the name is also allowlisted: **25** tests fail.

## 6. Refusal text as prompt surface

ADR-0053's last consequence — a refusal is a result, so the model reads it — is asserted, not
intended. Two properties over generated calls:

* a refusal never contains the path of any containment root, in `content` or in `reason_detail`;
* a refusal never volunteers an allowlist member the model did not already supply.

The one place they pulled: a `path_escape`. §13 asks the refusal to name "root and target"; ADR-0053
says refusal text must not name the roots. Both are honoured by **splitting the audiences**:

* the model sees the root's **role** — `write_root` or `read_roots` — plus its own candidate,
  cleaned and capped;
* the record's `result_summary` additionally carries `[root=/actual/path]`.

The operator may see the deployment's filesystem layout; the model may not. A test asserts both
halves. (The second property also caught a false alarm during development: a model's own echoed
name legitimately *contains* a registered name, so the property subtracts the echoed name first.)

## 7. The fuzz corpus — what it covers, what it deliberately does not, and how it was validated

`tests/strategies.py`'s module docstring is the long version; this is the argument.

### 7.1 Two rules the generators are built on

* **Build valid shapes; do not `filter` invalid ones.** Heavy filtering gives flaky
  `filter_too_much` health-check failures and shrinks to nothing useful.
* **A generator that labels its own answer beats an oracle that re-derives it.** A path candidate is
  drawn *together with* whether it escapes; a tool name together with whether it is registered. An
  oracle that re-implemented `Path.resolve` and containment would agree with a **bug** in the
  implementation, because both would reason the same way about the same thing. This is the C1 lesson
  (its first draft asked the implementation's own helper what the untouchable set was, and two
  mutants sailed through).

### 7.2 The generator families, and what each would catch

| Family | Reaches | Would catch |
|---|---|---|
| **Names** | empty, blank, 10 000 chars, unicode, emoji, control chars, NUL, `..`, path separators, case variants, leading/trailing space, one character short/long, valid-pattern-but-unregistered, registered-but-not-allowlisted, allowlisted-but-not-approved, `None`, ints, lists | fuzzy or case-folding lookup; `dict.get` on an unhashable; a name cleaned before lookup instead of only for the record; the registry/allowlist rungs swapped |
| **Arguments** | valid by construction; wrongly typed; extra-propertied; missing required; `null` where an object is required; nested past the depth cap; wider than the node cap; `NaN`/`±Infinity`; `bytes`; sets; cycles; non-string keys; values that are themselves valid JSON Schema documents; not a mapping at all | `canonical_json` refusing `NaN`/`bytes`/`set`/a cycle while building the record; a `RecursionError` inside the validator; an unbounded walk; a digest that is a constant sentinel |
| **Handlers** | oversize output; output holding lone surrogates and NUL; wrong return type (`None`, `str`, `int`, `list`, `dict`, an object whose `__str__` raises); arbitrary `Exception` classes including `MemoryError`, `RecursionError`, `UnicodeDecodeError`; mutating the arguments mapping; running past the limit | `UnicodeEncodeError` hashing the output; a truncation that splits a character; a handler mutation reaching the record; a traceback reaching the model; the return type trusted |
| **Worlds** | every combination of registered / allowlisted / approved / argument validity / egress ceiling / isolation tier / path escape / redaction, plus three schema shapes and four timeout settings | any reordering of the ladder; a check that short-circuits another; a containment check that resolves an unvalidated argument |
| **Sandbox doubles** | a host reporting `BWRAP`; a sandbox whose every method raises | the executor depending on a concrete class rather than the port; a probe failure crashing instead of reading as "no tier" |
| **Specs** | malformed, open at the root, open when nested, open inside an array or a combinator, over-deep, `$ref`-bearing | the closedness check applied only at the root; `$ref` reaching a validator |

### 7.3 The properties

Eleven, at 300 examples each (150 for determinism). Each docstring names what it would catch.

1. `execute()` returns a `ToolResult` for every generated input — nothing escapes, including from
   the record-building and truncation paths.
2. Every non-`OK` result carries a non-empty reason **from the closed set**; every `OK` carries none.
3. Exactly one record per call, whatever the outcome.
4. The **earliest** failing check is the one reported (§5).
5. No unvalidated argument ever reaches a handler — the development plan's ordering rule, stated as
   a property about the handler.
6. A path a handler received is absolute and inside a root appropriate to its `PathAccess`.
7. A redacted call's plaintext appears in **no field at any prefix length**.
8. A refusal names no containment root and volunteers no allowlist member (§6).
9. Content is capped in **bytes**, decodes cleanly, and is labelled exactly when truncated.
10. The record's `args_sha256` is always 64 hex characters.
11. Determinism: two identically-configured executors produce byte-identical results and records.

### 7.4 What the corpus deliberately does not contain, and why

* **`BaseException` handlers** (`KeyboardInterrupt`, `SystemExit`, `GeneratorExit`). The executor
  **records the call and then re-raises** these, and a property asserting "nothing escapes" would
  have quietly contradicted that decision. Covered by two named tests that assert the exception
  *does* escape **and** the record exists anyway. Reasoning in §8.
* **Handlers with real side effects.** Phase 1 ships no built-in tools; a fake that touched the
  filesystem would be a built-in arriving two phases early. E2 adds those and their own vectors.
* **Live sandbox escapes and redirect chains.** D1's and E2's to add — a symlink race and a TOCTOU
  window for D1, an ADR-0026 §3 vector set for E2 (shared byte-for-byte with LoadCoach's, per the
  plan's Phase 3 acceptance criterion 2).
* **`ToolSpec` fuzzing as a property.** A spec is the *caller's*, so a bad one must raise; that is
  the opposite of the property this suite states, and mixing them would blur the raise/refuse
  boundary the whole package rests on. Covered by 39 example-based tests in `test_validation.py`.
* **A generator over the wall clock.** A broken clock is a caller bug on the trusted half; guarding
  it would hide the bug. The monotonic source *is* guarded (a reading that runs backwards yields
  `0`, never a negative duration) because `baseaicore.elapsed_ms` refuses a negative and the guard
  is tested.

### 7.5 The suite was validated by breaking the implementation

Ten deliberate mutants, all killed:

| Mutant | Died by |
|---|---|
| Ladder reordered (schema after egress) | 1 test |
| `unknown_tool` fires only if also allowlisted | 25 tests |
| `_args_digest` calls `sha256_of` without sanitizing | immediate — the whole suite |
| Redaction removed | 3 tests |
| Output hashed before cleaning | 1 test |
| Record appended only on `OK` | 29 tests |
| Content capped before the digest is taken | 2 tests |
| Containment root appended to the model-facing refusal | 1 test |
| Handler handed the raw candidate rather than the resolved path | 1 test |
| `BaseException` swallowed instead of re-raised | 2 tests |

The corpus also found a **real sharp edge** during development, now pinned as its own test: a
model-supplied name is cleaned of NUL *for the record*, and must never be cleaned *for the lookup* —
`"echo\x00"` cleans to `"echo"`, which is registered, so a cleaned lookup would resolve a name
nobody registered and defeat exact matching in the one direction that matters.

### 7.6 Replaying a failing example

Hypothesis prints a `@reproduce_failure(version, blob)` decorator; paste it onto the test and run.
The `.hypothesis/` database also replays the last failure automatically in the same checkout, but it
is gitignored, so the decorator is what travels to CI. No profile is registered and no seed is
pinned: `pytest-randomly` reorders the suite every run, and a failure that only reproduces under one
seed is a **real ordering bug**, not a reason to pin. `CONTRIBUTING.md` §Tests says all of this.

## 8. What happens with `BaseException`, and why

`except Exception` → `FAILED` / `handler_error`, always. A `BaseException` that is **not** an
`Exception` — `KeyboardInterrupt`, `SystemExit`, `GeneratorExit` — is **recorded as `FAILED` first
and then re-raised**.

The reasoning, which is in the module docstring and at the raise site: model input cannot produce
one. The name, the arguments, the output size and the runtime all resolve to results; those three
are delivered by a signal or by the interpreter. Swallowing them would make an agent loop
uninterruptible **by the person running it** — trading a stop condition the model controls (the
thing ADR-0053 forbids) for one nobody controls. Acceptance criterion 1 is about "names, args and
outputs", and it holds without qualification.

## 9. The record/store answer: what happens to a completed side effect whose record cannot be written

**Order:** handler runs → result built → record built → `store.append()` → result returned. The
result reaches the caller **after** the store, not before.

**A store failure raises.** `StoreFailure` is a caller bug (§7's error tree) and it is the one
exception that can leave `execute()` after a tool has already run. That is deliberate: "every call
is recorded" (§11.6) is a **stronger** promise than "execute never raises for a caller bug", because
returning the result while dropping the record leaves a trajectory holding a side effect its audit
trail does not contain — the exact failure this package exists to prevent.

**So the error carries what the application needs to recover without re-running anything:**

* `StoreFailure.result` — the fully-formed `ToolResult`, ready to hand back to the model;
* `StoreFailure.record` — the `ToolCallRecord` the store would not take, ready to persist elsewhere;
* `.details` — invocation id, tool name, status. **Never** arguments and never content: `details`
  travels into API error envelopes.

Any exception type from the store is wrapped (`raise … from exc`), so a `sqlite3.OperationalError`
does not cross this API; a store that already raises `StoreFailure` is passed through unwrapped.

**What PromptCadence must do with it:** treat `StoreFailure` as a halt condition for the trajectory,
persist `.record` through whatever fallback it has (its own event log at minimum), and return
`.result` to the model only if it can record it. Re-running the tool is the one thing it must not do
— the side effect already happened.

`store=None` is permitted (spec §7) and appends nothing; it is for a standalone script or a test,
and the docstring says so. The record is built either way, so the code path a test exercises is the
code path production runs.

## 10. Import-linter contracts: which later phases may extend which

Seven contracts, all `KEPT`. Verified to bite: a temporary `import pathlib, subprocess, httpx,
setspec` in `registry.py` broke four of them.

| Contract | May D1/E2 touch it? |
|---|---|
| `no-application-imports` | **Never.** Master architecture §2 |
| `no-sibling-packages` | **Never.** Spec §5 names `setspec` explicitly |
| `no-model-access` | **Never.** Spec §3 |
| `no-persistence` (`sqlalchemy`, `alembic`, `sqlite3`) | **Never.** Spec §10: ToolYard owns no data |
| `subprocess-only-in-the-sandbox` | **D1 uses the exemption already written** (`toolyard.sandbox -> subprocess`). It adds a module, not a rule. `multiprocessing` and `pty` stay forbidden everywhere |
| `http-only-in-the-fetch-tool` | **E2 uses the exemption already written** (`toolyard.tools.fetch -> httpx`). `requests`, `aiohttp`, `urllib3`, `urllib`, `http`, `socket`, `ssl` stay forbidden in **every** module, forever — a second client is a second chance to omit the redirect check |
| `filesystem-only-where-containment-lives` | **D1 and E2 use the exemptions already written** (`toolyard.sandbox`, `toolyard.tools.files`) |

The three layered contracts carry `unmatched_ignore_imports_alerting = none`, which is what lets an
exemption name an import that does not exist yet. **That is not a weakening**: any *other* module
importing the forbidden name still fails. This is the direct answer to the kickoff's instruction not
to write a contract the next session has to delete — a deleted contract is indistinguishable from a
weakened one in a diff.

A second, cheaper guard sits beside them: `tests/unit/test_boundaries.py` parses every module under
`src/` and asserts the set of top-level imports against a written allowlist. **D1 and E2 are
expected to extend that list**, in the same commit as the import. What it catches is the
*unexpected* addition — a convenience dependency arriving with no ADR, in the package whose non-suite
runtime budget is two.

## 11. Toolchain provenance and the `httpx` decision

Copied from `py/CutCtx` (the freshest sibling) and adapted for names: `pyproject.toml`,
`.importlinter`, `.editorconfig`, `.pre-commit-config.yaml`, `.github/workflows/{ci,release}.yml`,
`requirements/release.in`, `LICENSE`. `.gitignore` was **not** touched — it is the suite's canonical
one and already carries `.hypothesis/`.

Four deliberate differences:

1. **`jsonschema>=4,<5` declared; `httpx` deliberately not.** ToolYard's non-suite runtime budget is
   two (gold standards §1.1). `httpx` belongs to `http_fetch`, which is **Phase 3 (row E2)**, and
   **E2 declares it in the same commit that first imports it.** Declaring it now would pull
   `httpcore`, `h11`, `anyio`, `certifi`, `idna` and `sniffio` into `requirements/ci.lock` and into
   `pip-audit`'s blast radius, so a CVE in a package no line of this repository imports could turn
   CI red. The `.importlinter` exemption that will permit the import already exists, so E2 adds a
   dependency and a module and changes no boundary rule. `requirements/README.md` records this.
2. **`hypothesis>=6.100,<7`** in the `dev` extra (CutCtx's precedent). Runtime budget unaffected;
   a test asserts nothing under `src/` imports it.
3. **`types-jsonschema`** in the `dev` extra, so `mypy --strict` sees the one runtime dependency's
   public surface.
4. **Three layered `.importlinter` contracts** instead of CutCtx's flat purity ones (§10), because
   Phase 2 imports `subprocess` and Phase 3 imports `httpx` **by design**.

`SECURITY.md` and `CONTRIBUTING.md` were **rewritten**, not renamed. CutCtx's talked about
transcripts, plans and summarization requests. ToolYard's `SECURITY.md` is the one in the suite with
something real to say and is structured as a threat model plus a table of every control, where it
lives, and what asserts it.

`requirements/{ci,release}.lock` regenerated with **pip-tools 7.6.1** on Python 3.13,
`--generate-hashes`, resolved against PyPI. `release.lock` is **byte-identical to CutCtx's below the
header**, which is the check that the release chain is reproducible rather than merely pinned.
Confirmed: pip-tools 7.6.1 writes `--no-index` into the recorded header; passing it fails to
resolve (the C1 trap — `requirements/README.md` records it).

**`pre-commit` is not installed on this machine** (`which pre-commit` → not found), so
`pre-commit install` was not run. Every hook it would run is covered by the gate or by CI:
`ruff`/`ruff-format` are gate steps 1–2; `trailing-whitespace`, `end-of-file-fixer`, `check-toml`,
`check-json`, `mixed-line-ending` are satisfied by `ruff format` and by `.editorconfig`; `gitleaks`
runs in CI's `security` job over full history. Same as the C1 precedent.

## 12. Commits

Fourteen, on `main`, on top of `eb708dd first commit`:

```text
4c419a2  build: repository skeleton and toolchain
f2f547b  docs: mirror the ToolYard spec and development plan
a8d1281  feat: the typed errors and the total functions they are not needed for
494e56f  feat: schema checking, strict by default in three ways
d78a096  feat: the sandbox port, and an honest Phase-1 implementation of its path half
7390f6a  feat: the vocabulary, with the trust boundary readable off the types
8a90d58  feat: the registry and the record store protocol
dccc9d5  feat: the executor, with the refusal order enforced structurally
806feca  test: the harmless fakes, the fixtures and the wire-definition golden
41eca24  test: unit suites for the vocabulary, validation, containment, the registry and the record
16e6897  test: the property suite over generated hostile calls
cb73276  test: the performance budgets, behind the marker
93b24d7  build: hash-pinned lockfiles for CI and release
82527c9  docs: README, changelog, security policy and contributing guide
```

`git status --short` was clean at the start of the session and is clean at the end. Nothing was
staged with `git add -A`. Mirrored docs verified byte-identical with `cmp`.

## 13. One thing fixed outside this row: CutCtx (C1)

The operator reported CutCtx failing CI on ruff, "imports out of order". Reproduced and fixed:

* **Cause.** `tests/property/test_apply_property.py` sorted `from strategies import …` **before**
  `from cutctx import …`. Under `src = ["src", "tests"]`, ruff resolves `strategies` as first-party,
  so it belongs after `cutctx`. The C1 session's gate reported clean because `.ruff_cache` still
  held the pre-edit result for that file; `ruff check --no-cache .` — what CI effectively runs —
  fails.
* **Fix.** `py/CutCtx` commit **`6d704bb`** (`style: sort the first-party test imports in
  test_apply_property`). One line moved. `ruff format --check`, `ruff check --no-cache`, `mypy` and
  the affected property module all pass afterwards.
* **Status: committed on `main`, NOT pushed.** It needs pushing with the rest.
* **Generalized here.** ToolYard's `CONTRIBUTING.md` and `README.md` both state the gate with
  `--no-cache`, with the reason.

## 14. Before the next session — operator steps

1. **Push CutCtx.** `cd /home/jpk/ai/suite/py/CutCtx && git push origin main` — this carries the ten
   C1 commits **plus** `6d704bb`. Confirm CI green; the `lint` job is the one that was failing.
2. **Push ToolYard.** `git push -u origin main`.
   The VSCode askpass IPC environment is needed for `git push` on this machine (the FreeWeight M6
   precedent).
3. **Confirm ToolYard's first CI run is green.** The blocking jobs pin **Python 3.12**, which does
   not exist on this machine and could not be run here; the 3.14 early-warning job could not be run
   under CI conditions either, though the suite does pass under local 3.14.4. Watch in particular:
   * `format` / `lint` — these install ruff **unpinned**, so a newer ruff than 0.16.5 could add a
     rule. This is the same shape as the CutCtx failure and is worth a glance rather than an
     assumption;
   * `types` — mypy under 3.12 rather than 3.13;
   * `security` — `pip-audit` over both locks, and `gitleaks` over full history (`fetch-depth: 0`
      is already set, for the reason C1's comment records).
4. **Nothing to publish.** `toolyard 0.1.0` ships at the end of Phase 3 (row E2). PyPI name
   re-checked 2026-09-03T03:32Z: `toolyard` **404, free**.
5. **Decide the spec amendments.** Every proposal in §3 and §4 is written as a diff to
   `docs/packages/toolyard/spec.md`. They are the architect's call, not D1's or E2's — and D1 begins
   by implementing into the seam §4(c) describes, so settling that one first is worth more than the
   others. If the amendments are accepted, the workspace `docs/` copy changes first and the
   repository mirror is re-copied and re-verified with `cmp`.
6. **Two documents to read before D1 starts:** §4(c) (what D1 must implement and must not change)
   and §10 (which contracts it may extend). Before E2: §4(b) (what `EgressClass.NETWORK` means at
   the executor's check, and what it does **not** substitute for), §11 (the `httpx` declaration), and
   §7.4 (the vectors the corpus deliberately leaves to that phase).
