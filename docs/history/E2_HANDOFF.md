# E2 — ToolYard Phase 3, the built-in tools, `toolyard 0.1.0` prepared

**Row:** E2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Date:** 2026-09-03. **Model:** Sonnet 5 · high, as scheduled — no deviation.
**Repositories touched:** `py/ToolYard` (8 commits), `LoadCoach` (2 commits, **tests and a fixture
only**), `docs` (1 commit).
**State:** `toolyard 0.1.0` **prepared, not published.** Nothing pushed, nothing tagged, nothing
published. All three working trees clean.

---

## 1. Gate results

Run from inside `/home/jpk/ai/suite/py/ToolYard`, at commit `87e53f0`, with the repository's own
virtualenv. **Interpreter named as M5C-13 requires**, confirmed rather than copied:

```text
$ ./.venv/bin/python --version
Python 3.13.15

$ ./.venv/bin/python -m ruff format --check .        44 files already formatted
$ ./.venv/bin/python -m ruff check .                 All checks passed!
$ ./.venv/bin/python -m mypy src tests acceptance    Success: no issues found in 37 source files
$ ./.venv/bin/lint-imports                           Contracts: 7 kept, 0 broken.
$ ./.venv/bin/python -m pytest -m "not live and not performance" -q
                                                     748 passed, 2 skipped, 4 deselected
$ ./.venv/bin/python -m pytest -q --cov --cov-report=term
                                                     Total coverage: 100.00%
```

**Coverage is 100 % on every module, as it was before this row.** Floor is 95 %; the repository has
never been below 100 and this row did not spend that margin.

Additionally:

```text
$ ./.venv/bin/python -m pytest -m isolation -rs -q   38 passed, 2 skipped, 714 deselected
      (docker rung and the forced bwrap rung, both real, on this host; podman absent — see §6)
$ ./.venv/bin/python -m build --no-isolation         Successfully built toolyard-0.1.0.tar.gz
                                                     and toolyard-0.1.0-py3-none-any.whl
$ ./.venv/bin/python -m twine check dist/*           PASSED, PASSED
```

**LoadCoach**, at commit `8ddca7f`, `.venv/bin/python` is **Python 3.14.4** (that venv's interpreter
is a symlink to `/usr/bin/python`; no `pip install` was run in it, per the row's bound):

```text
$ .venv/bin/python -m ruff format --check tests/integration/test_adr0026_shared_vectors.py
                                                     1 file already formatted
$ .venv/bin/python -m ruff check <that file>         All checks passed!
$ .venv/bin/python -m mypy <that file>               Success: no issues found in 1 source file
$ .venv/bin/lint-imports                             Contracts: 4 kept, 0 broken.
$ .venv/bin/python -m pytest tests/integration/test_adr0026_shared_vectors.py -q
                                                     25 passed
$ .venv/bin/python -m pytest -q -m "not live and not performance"
                                                     3 failed, 854 passed, 3 skipped, 15 deselected
```

**Those 3 failures are pre-existing and unrelated** — see §7, finding 1. Verified by running the
same file from a worktree at `HEAD~1` (`846348b`, before this row touched anything): the same three
fail identically there.

## 2. The red `main`, and what fixed it

Both defects the kickoff named were real. Each is its own commit, as instructed.

### Defect 2 — the install check had never checked this package (`dffe660`)

`.github/workflows/ci.yml:136` ran `python -c "import cutctx"`. One line, copied with the toolchain
from CutCtx at C2 and never adapted, in the one job that proves the built wheel imports — so that
job had failed on every run of the workflow since it was written. Now `import toolyard`.
`grep -rn cutctx` over `.github/`, `pyproject.toml`, `requirements/`, `README.md`, `CONTRIBUTING.md`
and `SECURITY.md` now returns nothing.

**Proof it does what it is meant to, ahead of CI:** the built wheel was installed into a clean
3.13.15 virtualenv, imported, and ran the acceptance script — exit 0.

### Defect 1 — the symlink cycle (`68d4263`)

**The answer taken: fail closed, one answer on every supported interpreter.** An unresolvable cycle
is refused with `PathEscape`.

*Why that one rather than the other.* Admitting the cycle everywhere means detecting it in
`containment` instead of delegating to `Path.resolve` — which means a second, hand-written symlink
walker in the security-critical path, obliged to agree with the kernel's own `MAXSYMLINKS`. A walker
that disagreed would be a new defect of exactly the class this one is. Refusing costs nothing that
was reachable: the kernel answers `ELOOP` to every attempt to open a cycle, so the path names no
file a handler could ever have read or written. ADR-0018's floor is refusal, and containment already
gave the same answer to a path the OS will not parse. The prompt recommended this reading and I did
not find a reason to depart from it.

*The mechanism.* `containment.fully_resolve()` probes with `os.path.realpath(path, strict=True)`,
which raises `OSError(ELOOP)` for a cycle on **every** interpreter from 3.10, and falls back to the
ordinary non-strict `Path.resolve()` for anything that is not a cycle — a missing component is what
`write_file` is handed, so strict resolution alone would refuse the ordinary case.
`os.path.ALLOW_MISSING` would have been the more direct primitive and exists on this 3.13.15, but
its availability on **3.12** could not be verified here, and 3.12 is the declared baseline; `strict=`
has been present since 3.10, so that is what was used.

*What can and cannot be proven here.* There is **no python3.12 on this machine**, so the 3.12
behaviour is un-reproducible locally and **only CI can confirm the fix**. The 3.13 half is proven
for real (the loop now raises `PathEscape`); the 3.12 half is proven by monkeypatching the
`fully_resolve` seam to raise what 3.12 raises — `RuntimeError("Symlink loop from …")` and
`OSError(ELOOP)` — in `test_whatever_the_resolution_seam_raises_becomes_a_refusal`.
`test_a_loop_whose_first_hop_leaves_the_root_is_still_refused` is unchanged and still refuses.
The old test's docstring asserted the 3.13 premise as a fact about Python; it now states what is
true and why the premise was wrong.

**The operator's push is the proof.** Watch CI's `tests (3.12)` job specifically.

## 3. What was built, against spec §7

| §7 name | Built | Notes |
|---|---|---|
| `read_file_tool(*, max_bytes=1_048_576)` | `tools/files.py` | Over-cap files **refused**, not truncated (§4) |
| `write_file_tool()` | `tools/files.py` | Parents walked one level at a time (§4) |
| `list_dir_tool(*, max_entries=1_000)` | `tools/files.py` | Sorted; truncates with a count |
| `run_command_tool(sandbox, *, env=DEFAULT_COMMAND_ENV)` | `tools/command.py` | D1 §13 row A implemented, not redesigned |
| `http_fetch_tool(allowed_hosts, *, resolve, …)` | `tools/fetch.py` | `resolve` **required** (§4) |
| `ToolRefusal` | `types.py` | New; the amendment that makes §13's fetch rows expressible |
| `Reason` + 15 members | `types.py` | Set goes 9 → 24 |

Each factory returns the `(ToolSpec, ToolHandler)` pair, so registration is
`registry.register(*read_file_tool())`. No implicit registration anywhere.

**No handler resolves a path.** Every file tool declares its path in `path_args`; the executor
resolves and substitutes (spec §11.3). One consequence worth carrying forward: **the handler never
sees the model's own string**, only the resolved absolute path — which names the workspace root, and
refusal text is prompt surface. So every model-facing message is rendered *relative to the root that
holds it* (`files._shown`) and the absolute path goes to `record_detail`. A test asserts the root
appears in the record and not in the result.

## 4. Decisions made where a document left an edge

1. **`ToolRefusal` exists at all.** Spec §13 required *"REFUSED / the specific ADR-0026 check"* and
   §7's `ToolHandler.execute -> ToolOutput` made it unexpressible: a handler could only succeed or
   raise, and a raise is `FAILED`/`handler_error`, an exception's class name rather than a check.
   Amendment proposed, docs first. Widening the protocol's return type is backwards compatible.
   *Alternative rejected:* fields on `ToolOutput` (`status`, `reason`) — it makes an invalid state
   representable (content **and** a refusal), where a union does not.
2. **`http_fetch`'s `resolve` is required, with no default.** This is the sharpest call in the row.
   Spec §11.5 requires the link-local comparison *after* resolution; `.importlinter` forbids `socket`
   in **every** module of this package, forever, with no exemption — and the row's constraint is that
   no boundary rule may be weakened. So ToolYard opens no resolver socket and the application injects
   one. *Required* rather than defaulted because every default available is either that boundary
   violation or a resolver that answers nothing, and one that answers nothing makes the check vacuous
   **without saying so**. **For the architect:** the alternative is an ADR permitting
   `socket.getaddrinfo` in `toolyard.tools.fetch` alone. That would be a real widening of a contract
   whose stated rationale is about HTTP clients rather than name resolution, and it is defensible —
   but it is an architect's call, not a publishing row's. Recorded here rather than taken.
   Note also that a literal IP is **never** passed to the injected resolver: it already is the answer,
   and letting application code erase a link-local literal is the one case that must not depend on
   anything injectable.
3. **The REFUSED/FAILED line.** `REFUSED` = this package declining under a rule of its own, and the
   identical call will be declined again for the same reason. `FAILED` = the work attempted and the
   world answering badly, where a different argument or a later attempt may succeed. So `too_large`
   (a cap this package chose) is REFUSED and `file_not_found` is FAILED. The FAILED rows are
   refinements of `handler_error` — they exist so a model is told what was wrong with its argument
   rather than an exception's name. Written into spec §13 as a paragraph, not left implicit.
4. **`read_file` refuses an oversized file; `list_dir` truncates one.** The difference is not taste:
   `ToolCallRecord.result_sha256` digests the handler's **whole** output, so a prefix would make the
   recorded digest a digest of the prefix and the application's artifact would stop matching the
   record that points at it (`ToolOutput`'s own docstring says so). Nothing hashes a listing against
   an original, so a labelled partial listing costs nothing.
5. **`write_file` walks parents one level at a time**, refusing any component that is a symbolic
   link. **Honest scope:** a link that existed at resolution time is resolved *through* by the
   executor and refused there if it leads out — so the walk exists for exactly one case, a link
   planted between check 5 and the write. The test simulates that race with a sandbox that plants the
   link as it returns the resolved path, because a real race cannot be scheduled.
   **The race itself is not closed.** Closing it needs `openat`/`O_NOFOLLOW` walking and therefore
   `os`, and `.importlinter` gives this module `pathlib` alone, deliberately. Narrowed to one
   component, and written down in the code rather than implied away.
6. **The content-type allowlist** is closed, small and text (`text/*` plus `application/json` and
   `application/xml`, plus RFC 6839's `+json` suffix, which LoadCoach also admits so a shared vector
   holds in both). Verified **before** the body is returned.
7. **`_next_hop` does not guard its own `join`.** httpx parses the `Location` header while building
   the response, so a malformed one arrives as a transport error before the redirect logic runs; a
   guard would be a branch no input could take. Found by coverage, and the dead branch was **removed**
   rather than marked no-cover. A test pins the real behaviour, so if httpx ever stops pre-parsing,
   a test says so instead of a model receiving an exception.
8. **`sandbox.ARGV_REFUSED_PREFIX`** was added so `run_command` can distinguish an argv the launcher
   refused from a command that genuinely exited 127. The alternative was a magic string in two files.
9. **The DNS residual is stated.** `http_fetch` resolves and then connects; a name whose answer
   changes between them (rebinding against an allowlisted host) is outside this design. Closing it
   needs the connection pinned to the checked address, and httpx exposes no seam. In the module
   docstring and in spec §14 — no docstring claims a pinning that is not implemented.

## 5. Amendments proposed, with their `cmp` proof

All in `docs/packages/toolyard/spec.md`, edited in the **workspace** `docs/` first (commit `9d24c3a`
there), then copied into `py/ToolYard/docs/` and proven byte-identical:

```text
$ cmp docs/packages/toolyard/spec.md py/ToolYard/docs/packages/toolyard/spec.md
(no output — byte-identical)
```

* **§7** — `ToolRefusal`; `ToolHandler.execute -> ToolOutput | ToolRefusal`; the five built-in
  signatures with their caps, `run_command`'s `env`, `http_fetch`'s required `resolve` and its
  `transport` seam; the `Resolver` type.
* **§7's `Reason` note** — that nine reasons are the executor's and the rest the built-ins'.
* **§11.5** — resolution is the injected `resolve` and why it is required; the vectors are one
  shared fixture.
* **§13** — the single fetch row replaced by fifteen enumerated rows, plus the REFUSED/FAILED
  paragraph.
* **§14** — no credential surface; the resolve-then-connect residual.

No other document was touched. `.importlinter` was **not** modified — the two exemptions this row
needed (`toolyard.tools.fetch -> httpx`, `toolyard.tools.files -> pathlib`) were already written.

## 6. The shared vector set

**File:** `tests/fixtures/fetch/adr0026_vectors.json`, **24 vectors**, authored in ToolYard and
copied into `LoadCoach/tests/fixtures/fetch/` byte-for-byte.

```text
sha256  ae7d6689ded17443ff6a944d567d343b1981acfb3e17d4ae87ed43bad0e91fcc
```

That digest is asserted in **both** repositories (`ToolYard` `tests/unit/test_fetch_tool.py`
`VECTORS_SHA256`; `LoadCoach` `tests/integration/test_adr0026_shared_vectors.py` `VECTORS_SHA256`),
so a one-sided edit fails a test rather than becoming a divergence found later in production. `cmp`
proves the copy, the way the docs mirrors are proven.

**Mechanism.** Declarative JSON: each vector names the case, its ADR-0026 §3 rule, the URL, the
explicit host allowlist, the resolver's answers, the scripted transport responses, the expected
outcome and reason, and **how many requests the client is allowed to have made** — so "refused before
a socket is opened" shows as `requests_expected: 0` rather than being asserted indirectly. Each
repository has its own ~40-line runner that turns a vector into an `httpx.MockTransport`. No socket
is opened by either suite.

**Sizes are relative to the configured cap**, never to a number: the cap is 8 MiB here and 128 MiB
there. `body_bytes_over_cap` and `declared_length_over_cap` are resolved against whatever cap the
vector configured, and a test asserts no vector states a cap as a literal.

**The state of the LoadCoach half: complete and green.** `FreeWeightClient` passes all 24 vectors
**unchanged**. `LoadCoach/src/` was not touched, no reason string was renamed, no behaviour changed,
no `pip install` was run in that venv, and the changelog entry sits under `## [Unreleased]` with no
version bump — it rides H2.

**One defect the shared set found in itself.** The `a_body_that_outgrows_the_cap_is_stopped_mid_stream`
vector originally sent a fixed body, and httpx declares a `Content-Length` for one — so the
*declared-length* check fired and the vector passed **without ever running the code it named**. Found
by ToolYard's coverage report showing the streaming branch unexecuted while the vector was green. The
vector now sets `streamed: true` (a chunked body, no `Content-Length`) and a companion vector pins
the streaming path's success case. Both digests moved together, in the same session, as the file's
own rule requires. This is the clearest argument for the shared-fixture mechanism: the fixture is
reviewed as an artefact, so a vector that proves nothing is visible.

## 7. Findings

1. **LoadCoach's `main` has three failing contract tests, unrelated to this row and pre-existing.**
   `tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged`
   for the `1.1-full`, `1.1-mixed` and `1.1-unsupported` parameters, all
   `pydantic ValidationError: 1 validation error for CapabilityEvidenceOut — Extra inputs are not
   permitted … {'artifact_digest': …}`. That venv holds **`setspec 0.3.0`**, and the 1.1 goldens
   carry a field that version's model does not admit — so it is an environment/lock question for
   LoadCoach's own next row, not a code defect this row caused. Verified pre-existing from a
   worktree at `846348b`. **Not fixed here**: this row's bound is tests and fixtures only, and the
   fix is a dependency decision.
2. **`ModelRack/requirements/release.lock` is two pins behind the other five.** ToolYard's is
   byte-identical below its header to CutCtx's, LoadLedger's, WeightsDB's and MirrorWall's — checked,
   not assumed — and differs from ModelRack's only in `build` (1.5.0 vs 1.6.0) and `readme-renderer`
   (45.0 vs 46.0). ModelRack's is the stale one. Not this row's to change; worth a regeneration in
   whichever row next touches ModelRack.
3. **`socket` and the fetch resolver.** See §4.2. If the architect prefers a shipped default
   resolver, it needs an ADR widening the `http-only-in-the-fetch-tool` contract for
   `socket.getaddrinfo` in `toolyard.tools.fetch`. Until then every application wiring `http_fetch`
   writes three lines, and the README shows them.
4. **The `run_command` timeout is the invocation's, and `run_isolated` enforces it.** The executor's
   own timeout check is *reported, not enforced* for in-process handlers; for `run_command` the
   sandbox kills the tree at the deadline and the handler returns `TIMEOUT` explicitly, so the two
   agree. Worth knowing at E4 when PromptCadence sets per-turn timeouts.
5. **The two implementations disagree about an empty host allowlist.** ToolYard's spec §11.5 says
   an empty allowlist means loopback only; LoadCoach's `check_url` refuses *everything* when its
   allowlist is empty, and it is safe only because its config default is the three loopback names.
   Neither is reachable by accident and both are closed, so this is a divergence rather than a
   defect — but it means "empty" does not mean the same thing in two implementations of one
   ADR-0026 discipline. Deliberately **outside** the shared vector set: every vector states its
   hosts explicitly, and the fixture's `fields.allowed_hosts` comment says why. Confirmed with the
   operator (§16) as documented-not-tested.
6. **`process_count` is still unvalidated.** `MIN_PROCESS_COUNT = 8` documents the floor D1 finding 7
   declined to validate, and a test asserts the default sits above it. Nothing enforces it, by D1's
   choice; a caller can still configure 1 and refuse every command.

## 8. What the next row must not relitigate

* **Everything in `docs/history/D1_HANDOFF.md` §7 still stands**, and this row changed none of it: no rung below
  refusal, the probe's real canary, `env=None` is the empty allowlist, `requires_isolation` is
  load-bearing, one `Popen`, the `/etc` tuple, the refusal order.
* **A handler refuses by returning `ToolRefusal`, never by raising.** A raise is `handler_error` and
  names no check. This is ADR-0053 decision 4 one layer in.
* **No handler resolves a path.** The executor resolves and substitutes; a handler that re-resolved
  would be a second containment.
* **`Reason` is closed and `ToolRefusal` validates against it.** A new reason is a MINOR release and
  a change consumers must be told about — it is no longer free, because `0.1.0` is prepared.
* **`http_fetch` has no credential surface**, and adding one is a spec §14 change, not a parameter.
* **The vector file is shared.** Editing it on one side alone is a failing test in both. Edit
  ToolYard's copy, re-copy, `cmp`, move both digests in one change.
* **The five built-ins' wire definitions are golden-locked.** A description change is a change to
  every PromptCadence turn record that hashed it.

## 9. Commits

```text
py/ToolYard  (main, not pushed)
dffe660  fix(ci): the install-check job imports toolyard, not cutctx
68d4263  fix(containment): one answer for a symlink cycle on every interpreter, closed
71b141c  feat(types): a handler may return a refusal, and the fetch and file reasons
d0f15cc  feat(tools): the four tools that touch this machine — files and run_command
0eea5b2  feat(tools): http_fetch, and one ADR-0026 §3 vector set shared with LoadCoach
e642636  test(tools): golden-lock the five built-ins' wire definitions
6f670e2  docs: changelog, README and the runnable acceptance check for Phase 3
87e53f0  chore(release): prepare toolyard 0.1.0

LoadCoach   (main, not pushed) — tests and fixtures only, no version bump
af8cffd  test(evidence): share the ADR-0026 §3 fetch vectors byte-for-byte with ToolYard
8ddca7f  test(evidence): reach the during-streaming size check with a chunked body

docs        (main, not pushed)
9d24c3a  docs(toolyard): the Phase 3 amendments — a handler's refusal, the fetch reasons
```

## 10. Before the next session — operator steps

**The two publish blockers first. `toolyard 0.1.0` does not publish until both are done.**

1. **`pytest -m isolation -rs` on a podman host.** D1 kept podman **first** in the ladder and left it
   unverified; there is no podman on this machine, so the rung that runs first in production has
   never executed its canary. `docs/history/D1_HANDOFF.md` §13 row J makes this a precondition of this publish,
   and it stays one. Not a nice-to-have.
2. **The Opus review of the fetch-handler diff**, which row E2 schedules for itself. The diff to read
   is `0eea5b2` — `src/toolyard/tools/fetch.py` in full, and the vector file beside it.

Then, in order:

3. **Reserve the PyPI name `toolyard`.** `https://pypi.org/pypi/toolyard/json` returned 404 on
   2026-09-03. A name taken in the interval changes the import name, `pyproject.toml`,
   `.importlinter`, the coverage paths and every document that names the package — so reserve before
   the tag, not after.
4. **Push `main` in all three repositories** and **confirm CI green**. **ToolYard's `tests (3.12)`
   job is the proof of the symlink-cycle fix, and `install-check` is the proof of the import fix** —
   both were red before this row and neither can be verified on this machine. Watch those two
   specifically.
5. **Review** the ToolYard diff (same-day review, outstanding-work §4).
6. **Tag** `v0.1.0` in `py/ToolYard`.
7. **Approve the `pypi` environment** and let the release workflow publish.
8. **Post-publish install check:** `pip install toolyard==0.1.0` into a clean virtualenv,
   `python -c "import toolyard"`, and run `acceptance/register_and_execute.py` against it.

Two further items, neither blocking:

9. **LoadCoach's three pre-existing contract failures** (§7.1) need a decision about `setspec` in
   that venv, before H2.
10. **`ModelRack/requirements/release.lock`** wants regenerating to rejoin the other five (§7.2).


---

## 16. Decisions taken with the operator, 2026-09-03 (interview after the build)

Every one confirmed the implementation as built; nothing was reworked.

| # | Issue | Decision | Where it is |
|---|---|---|---|
| A | `http_fetch` needs DNS but `.importlinter` forbids `socket` forever | `resolve` stays a **required** argument with no default. No ADR widening the contract | `tools/fetch.py`; spec §7, §11.5 |
| B | An oversized `read_file` | **Refuse whole**, never a prefix — the record's digest must describe the file | `tools/files.py`; spec §7 |
| C | `write_file`'s symlink race | **Accepted for 0.1.0**, narrowed to one component and documented. No ADR permitting `os` in that module | `tools/files.py` `_make_parents`; changelog |
| D | Handler-originated refusals | **Union return type** `ToolOutput \| ToolRefusal`; illegal states unrepresentable | `types.py`; spec §7 |
| E | Where the REFUSED/FAILED line falls | **Policy-vs-world**, as written: `too_large` refuses, `file_not_found` fails | spec §13 |
| F | An empty host allowlist meaning two things | **Documented, not tested.** Stays outside the shared vector set | fixture `fields.allowed_hosts`; §7.5 above |
| G | LoadCoach's three red contract tests | **Logged for a LoadCoach row**, not investigated or fixed here | §7.1 above |

Nothing in ToolYard, LoadCoach or `docs/` changed as a result of this interview.
