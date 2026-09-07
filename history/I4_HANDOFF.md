# I4 — PromptCadence 1.0.1: the vendored LoadCoach snapshots, and I2's two leftovers

**Row:** I4 of `roadmap/outstanding-work.md` §1.
**Model:** Sonnet 5 · standard, as scheduled. No deviation.
**Date:** 2026-09-06.
**Repository:** `/home/jpk/ai/suite/PromptCadence` only. LoadCoach was read and never written; it
ends this row exactly where it started, at `2a7ac58`, clean.
**Ships:** `promptcadence 1.0.1` **not yet cut.** Five commits sit on `main`, ahead of
`origin/main` by five; the release commit is deliberately *not* among them. An operator interview
at the end of this row (§9) took all three of its open questions off their defaults, and one of the
three — resolving the private `toolyard._safe` import by making the name public — puts a ToolYard
publish between this work and the version bump. `toolyard 0.1.1` is prepared in
`/home/jpk/ai/suite/py/ToolYard` (two commits, unpushed). Once it is on PyPI, `requirements/ci.lock`
regenerates and 1.0.1 is cut; until then the lock pins `toolyard==0.1.0` while `pyproject.toml`
requires `>=0.1.1`, so **CI is expected red**. §10 is the exact sequence.

**Interpreter, named once for the whole report (M5C-13):**
`/home/jpk/ai/suite/PromptCadence/.venv/bin/python`, **CPython 3.13.15**. Every invocation below
was run through that binary as `.venv/bin/python -m pytest …` from `/home/jpk/ai/suite/PromptCadence`.

---

## 1. Gate results, with the exact invocations

### Setup

```bash
cd /home/jpk/ai/suite/PromptCadence
git status -sb          # ## main...origin/main   (clean, b4b67ac, tagged v1.0.0)
.venv/bin/python --version   # Python 3.13.15
.venv/bin/pip install -e ".[dev]"
```

`pip install -e ".[dev]"` **did not** move `setspec` or `commissioner` (see §5, item 2). They were
brought to the lock's pins explicitly:

```bash
.venv/bin/pip install "setspec==0.6.0" "commissioner[sql]==0.1.1"
.venv/bin/pip check      # No broken requirements found.
```

A baseline suite was run before anything was edited, so that any movement later in the row could
be attributed:

```bash
.venv/bin/python -m pytest -q -p no:randomly
# 1195 passed, 2 skipped, 10 deselected in 74.82s
```

### Gate A — the refresh

```bash
cp /home/jpk/ai/suite/LoadCoach/docs/openapi.json tests/contract/loadcoach_openapi.json
cp /home/jpk/ai/suite/LoadCoach/src/loadcoach/config/task_profiles.toml \
   tests/contract/loadcoach_task_profiles.toml
sha256sum tests/contract/loadcoach_openapi.json tests/contract/loadcoach_task_profiles.toml
# ca407d7ff689fcf275767a6aceb891de77d67b0a33219f244da35bd867e63848  loadcoach_openapi.json
# 3edb1f7ddc2c3c7b848e070a12f7da0efdf55d82140accc5683f42a3b542f457  loadcoach_task_profiles.toml

.venv/bin/python -m pytest tests/contract/ -q -p no:randomly   # 43 passed in 1.54s
.venv/bin/python -m pytest -q                                  # 1195 passed, 2 skipped
```

**Nothing moved.** Not one assertion in either contract test changed, and no test outside
`tests/contract/` changed either — the count is identical to the baseline. The eleven assertions in
`test_loadcoach_task_profiles.py` all hold unchanged, as the kickoff expected.

Both `SNAPSHOT_SOURCE` strings and both module docstrings were rewritten to name the new commits:

* `test_loadcoach_contract.py` — *"LoadCoach docs/openapi.json at 2a7ac58 (LoadCoach 1.1.1; last
  changed at 2a7ac58)"*.
* `test_loadcoach_task_profiles.py` — *"LoadCoach src/loadcoach/config/task_profiles.toml at
  2a7ac58 (LoadCoach 1.1.1; last changed at cb1cfac)"*.

Both last-changed hashes were confirmed with `git log -1 -- <path>` inside LoadCoach rather than
taken from the kickoff.

### Gate B — F2, decided (default), plus the one-line render

```bash
.venv/bin/python -m pytest tests/unit/test_content_cell.py -q -p no:randomly   # 3 passed
.venv/bin/python -m pytest -q     # 1198 passed, 2 skipped
```

### Gate C — the digest, decided (default)

```bash
.venv/bin/python -m pytest tests/integration/test_tool_execution.py \
    tests/integration/test_replay_cap.py tests/golden \
    tests/integration/test_retention.py tests/unit/test_tool_call_store.py -q -p no:randomly
# 22 passed
.venv/bin/python -m pytest -q     # 1199 passed, 2 skipped
```

The new assertion was **proved to catch the defect** before it was committed: with
`args_digest = sha256_of(_args_text(call))` restored at `services/loop.py`, the run is

```
FAILED tests/integration/test_tool_execution.py::test_the_started_events_digest_is_the_digest_the_record_carries
```

and with the fix in place it passes. A test that would pass either way would have pinned nothing.

### Gate D — the release commit, cut and then withdrawn

Gate D was completed as the kickoff specified and the release commit `0ec2c36` was made:

```bash
.venv/bin/python -c 'from tests.contract.test_openapi_snapshot import write; write()'
git diff docs/openapi.json    # -    "version": "1.0.0"  /  +    "version": "1.0.1"   — one line

.venv/bin/ruff format --check .          # 176 files already formatted
.venv/bin/ruff check .                   # All checks passed!
.venv/bin/mypy src tests                 # Success: no issues found in 172 source files
.venv/bin/lint-imports                   # Contracts: 5 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
# 1199 passed, 2 skipped, 10 deselected in 76.55s
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
# Required test coverage of 85.0% reached. Total coverage: 91.51%
```

It was then **withdrawn** — `git reset --soft HEAD~1` followed by a full restore of its three
files — because the operator interview (§9) added work that must land *before* a version bump, and
a release commit is worth nothing if it is not last. The regenerated `docs/openapi.json` and the
`__about__.py` bump were reverted with it, so the tree is back to `1.0.0` and Gate D will be redone
in full once §10 step 2 completes. Everything above is a rehearsal that passed; nothing about it is
in doubt except its timing.

### Gate E — the flaky test (interview decision 1)

```bash
.venv/bin/python -m pytest -q --randomly-seed=4198236421   # the seed that failed: 1199 passed
for i in $(seq 1 10); do .venv/bin/python -m pytest -q; done   # 10 / 10 green
```

Ten consecutive full-suite runs plus the previously failing seed, against a prior rate of roughly
one failure in five. See §8 for the diagnosis, which is not the one this row first reached.

### Gate F — the public `json_sanitize` (interview decision 2)

In `/home/jpk/ai/suite/py/ToolYard`, against its own venv:

```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy src tests                 # Success: no issues found in 36 source files
.venv/bin/lint-imports                   # Contracts: 7 kept, 0 broken.
.venv/bin/python -m pytest -q -m "not live and not performance"
# 748 passed, 2 skipped, 4 deselected in 40.04s
```

No new ToolYard test was needed: `tests/unit/test_boundaries.py:220` already walks `__all__` and
asserts every name in it resolves, so the export is covered the moment it is listed.

Back in PromptCadence, verified against a locally built `toolyard-0.1.1-py3-none-any.whl`:

```bash
.venv/bin/pip install --no-deps --force-reinstall .../toolyard-0.1.1-py3-none-any.whl
.venv/bin/python -c "from toolyard import json_sanitize"      # public import ok
.venv/bin/ruff check . && .venv/bin/mypy src tests && .venv/bin/lint-imports
.venv/bin/python -m pytest -q            # 1199 passed, 2 skipped, 10 deselected
```

**The venv now holds a locally built `toolyard 0.1.1` that is not on any index.** That is
deliberate — it is how the import was proved before the publish — but it means this workstation's
venv cannot be reproduced from `ci.lock` until step 2 of §10 is done.

## 2. The gates as commits

PromptCadence (`main`, ahead of `origin/main` by five, **no release commit**):

```
dcade58 fix(events): take json_sanitize from toolyard's public surface
16beb22 test(conftest): restore the root logger between tests
b96d2d8 fix(events): tool.call.started digests the arguments the record digests
9b5fb44 fix(explanation): a turn that completed with no text says so
6356f73 test(contract): the vendored LoadCoach snapshots are 1.1.1's
```

ToolYard (`main`, ahead of `origin/main` by two):

```
338f9c7 chore(release): toolyard 0.1.1
1e14788 feat(api): export json_sanitize from the package root
```

Gate B's commit is a `fix(...)` rather than the kickoff's `docs(changelog): …` because the
explanation-surface check found a real one-line render to take (§3, decision 1). The last two
PromptCadence commits and both ToolYard commits are the interview's (§9); everything before them
is the row as written.

## 3. The two decisions, with the reason and what the losing option would have claimed

### 1 — F2: does an empty declared `STOP` complete a step? **Yes, unchanged.**

The default was taken. `domain/turns.py::decide_finish` was read in full and the kickoff's reading
of it is exact: the first branch is `if finish_reason is FinishReason.STOP` and the answer's text
is not an input to the decision at all. The harness read the wire correctly in I2's run 3; there is
no defect in the finish logic to fix.

Three reasons, in the order they carry weight:

1. **Contract 6 is a wire contract.** It names the declared reason and nothing else. Adding "and
   the text is non-empty" makes the model's *output* an input to the harness's control flow, which
   is the one thing the suite refuses everywhere ("a model never decides control flow — Python
   does"). `domain/deviation.py:246` says it in as many words about this very field.
2. **"Empty" has no single meaning.** `{}` is valid JSON and an empty plan; I3 measured exactly
   that on `tools.plan`, where the structured-output corrective returned `{}` on three of six runs.
   A rule that halts on empty text would have to decide whether `{}` is empty, and any answer it
   gives is wrong for one of the two step kinds.
3. **The honest surface is the explanation, not a halt.** A step that completed with no text is a
   fact about the model an operator should be able to see, not an error the harness should invent.

**What the losing option would have claimed:** that a step which produced nothing has not been
completed in any sense an operator cares about, and that reporting it as `COMPLETE` launders a
failure into a success. That claim is answered rather than dismissed — but it is answered by
*showing* the emptiness, not by halting on it, and that is what this row shipped.

**What was found while checking.** The explanation *document* was already honest:
`domain/explanation.py::content_or_removed` carries the principle explicitly — *"An empty string
is content, not an absence: a turn that genuinely said nothing is a fact about the model"* — and
the JSON has always carried `"content": {"text": "", "removed": false}` beside
`"finish_reason": "stop"`. Only the **console** was silent: `content_cell` in
`web/templates/_macros.html` separated a scrubbed body from a retained one and let a genuinely
empty body fall through to the retained branch, where it rendered as an empty table cell. Beside
`Finish: stop` and `Output: 12` that reads as a broken render rather than as the fact it is — and
the macro's own comment already said a scrubbed body *"says so rather than looking like an empty
turn"*, so the case had been thought about and left unmarked.

The render was genuinely one line (one `{%- elif not content.text -%}` branch), and it is
golden-safe: `tests/golden/` holds JSON explanation documents, not HTML, and no test asserted on
`content_cell`'s output. It ships with three assertions in a new `tests/unit/test_content_cell.py`
covering all three branches — the first template unit test in the repository, which
`web/rendering.py`'s own docstring has been asking for since P8.

### 2 — the `args_sha256` mismatch: which digest is the contract? **The record's.**

The default was taken, and the evidence for it is stronger than the kickoff suggested: it is not a
judgement call between two defensible contracts, it is a **defect against a docstring that already
states the contract**. `domain/tools.py`'s `ToolCallStarted.args_sha256` says:

> The digest of the sanitized arguments. Always present, including under `redact_args`, **so an
> event and its row can be matched** without either holding plaintext.

Both halves of that sentence were false in 1.0.0. The event digested `canonical_json(...)` — the
*text* — while ToolYard's `executor._args_digest` digests `json_sanitize(args)` — the *value*. So
for every call whose arguments parsed, the event and its row disagreed, and the field's declared
purpose (matching the pair) was unachievable. ADR-0096's replay stub already carries the record's
value, and `tests/integration/test_replay_cap.py:72` already pins stub == record. The event was the
only one of four sites out of step, and it is the one PromptCadence emits.

**What the losing option would have claimed:** that the event's digest is what an operator reading
the raw event stream can recompute by hand from the JSON they see, and that the record's
`json_sanitize` pass is an implementation detail of a different package leaking into
PromptCadence's wire. Answered by the docstring: the field is defined as the digest of the
*sanitized* arguments, and it is defined as the join key. A join key that never joins is not a
different contract, it is a broken one.

**Why this is a patch and not a minor,** stated in the changelog: the event's digest matched no
row, no record and no replay stub, so it identified nothing any consumer could look up — no
consumer can have depended on a value that resolved to nothing. The field's name, presence, type
and shape are unchanged, and the digest of a raw non-JSON fragment is unchanged too.

**The change is one expression**, at `services/loop.py`:

```python
args_digest = sha256_of(json_sanitize(call.arguments))
```

It is unconditional rather than the kickoff's suggested `… when arguments_parsed, else the text as
today`, and deliberately so: `json_sanitize` passes a plain `str` through unchanged (verified —
`_args_digest("raw") == sha256_of("raw")`), so the unparsed case is byte-identical to 1.0.0
*without* a branch, while a branch would have kept `_args_text`'s `repr()` fallback for the
non-`str` unparsed case, which the record does not use and which would therefore have stayed
mismatched. One expression, matching ToolYard's by construction, is both smaller and more correct
than two.

`_args_text` remains, still used by `_bounded_call` for the replay-cap size measurement; its
docstring no longer claims to be the event's digest input.

**The golden did not move.** `tests/golden/trajectory_explanation.json` carries three
`args_sha256` occurrences, all of them the *event's*, and all three are normalized to `"<sha>"` by
the golden's scrubber. So the golden could not have detected this defect and does not record its
fix — which is itself worth knowing, and is why the new assertion had to be an integration test
comparing the live pair rather than a golden refresh.

**The assertion this row leaves behind**, in `tests/integration/test_tool_execution.py`:
`test_the_started_events_digest_is_the_digest_the_record_carries` scripts two calls in one turn —
one with parsed arguments (the case that disagreed) and one whose fragment is not JSON at all (the
case that already agreed and must keep agreeing) — and asserts `event["args_sha256"] ==
record.args_sha256` for each.

**The private import, raised and then resolved.** The fix first imported `json_sanitize` from
`toolyard._safe`, a private module — in that module's `__all__`, and with a comment saying why
borrowing beat reimplementing, but private all the same. It was put to the operator (§9) with
three options, and the operator chose to make the name public: `toolyard 0.1.1` exports
`json_sanitize` from the package root, PromptCadence imports it from there, and the floor moves to
`toolyard>=0.1.1`. ToolYard's own docstring now records *why* one function from a private module is
public, so the next reader does not quietly un-export it. The cost is that 1.0.1 waits on a
ToolYard publish (§10).

## 4. Exit conditions (kickoff §9)

1. **Green, named.** `pytest tests/contract/ -p no:randomly` → 43 passed; the whole default suite
   → 1199 passed, 2 skipped, 10 deselected, on CPython 3.13.15. ✔
2. **Digests agree three ways.** `sha256sum` of both vendored files equals both `SNAPSHOT_SHA256`
   constants and equals `sha256sum` of the LoadCoach files at `2a7ac58`. Verified together in one
   invocation. ✔
3. **Both `SNAPSHOT_SOURCE` strings name `2a7ac58`** and the correct last-changed hash (`2a7ac58`
   for the OpenAPI file, `cb1cfac` for the profiles), each confirmed with `git log -1 -- <path>`. ✔
4. **The pairing assertion exists** and was proved to fail without the fix (§1, Gate C). ✔
5. **F2's decision is in the changelog** (under *Known limitations*, with the reason) **and in
   this handoff** (§3). ✔
6. **`docs/openapi.json` differs from `b4b67ac`'s by `info.version` only** — demonstrated at
   Gate D (`git diff docs/openapi.json` was exactly that one line) and then reverted with the rest
   of the release commit, so it re-applies at §10 step 3. ✔ *as measured, pending as committed.*
7. **`git log --oneline v1.0.0..HEAD`** shows the gate commits — five of them, not four, and
   **not** ending in a release commit, which is §9's doing and is deliberate. `git status -sb` is
   clean in every repository touched (PromptCadence `ahead 5`, ToolYard `ahead 2`, LoadCoach
   level and unmodified); the three mirrors are still `cmp`-identical. ✔ *with the release commit
   held.*

## 5. Things this prompt said that turned out not to be true

1. **`max_output_chars = 50000` was *not* added to `tools.plan`.** Kickoff §0 says the diff is
   "larger than the row says" and names `max_output_chars = 50000` as newly added under
   `[task_profiles."tools.plan".validation]`. It was already in the `5c5aa1f` snapshot, at line
   567; a line-oriented diff attributes it to the new file only because the rewritten comment block
   above it shifted every following line. The old snapshot holds 20 occurrences of
   `max_output_chars` and the new one holds 21 — and the twenty-first is `adapters.measured`'s, not
   `tools.plan`'s. **This matters:** the kickoff's stated risk was that the fake LoadCoach derives
   a `length` validation check from `max_output_chars` (`tests/fakes/loadcoach_app.py`), so
   `tools.plan` gaining one could change what a fake job document carries. It gained nothing, the
   fake's behaviour is unchanged, and the full suite confirms it — same test count as the baseline.
   The **real** TOML diff is two things, not three: the rewritten `tools.plan` comment (inert to
   `tomllib`) and the whole `adapters.measured` profile.
2. **`pip install -e ".[dev]"` does not bring the venv to the lock.** The kickoff says to run it
   "once, then run the gate" to pick up `setspec 0.6.0` and `commissioner 0.1.1`. It does not:
   `pyproject.toml` declares ranges (`setspec>=0.5,<0.7`, `commissioner[sql]>=0.1,<0.2`) which the
   installed 0.5.0 and 0.1.0 already satisfied, and pip does not upgrade a satisfied requirement.
   `requirements/ci.lock` is a separate artefact that nothing in the editable install consults. The
   two pins were installed explicitly (§1). Anyone reading "install the extras and you are on the
   lock" will run the gate against the wrong versions and not be told.
3. **The 1.0.0 release commit did not carry `pyproject.toml` for the version.** Kickoff §0 lists
   four files "as `b4b67ac` did (…`pyproject.toml`…)". The version is `dynamic` and read from
   `src/promptcadence/__about__.py` by hatch, so this release commit carries three files:
   `CHANGELOG.md`, `docs/openapi.json`, `src/promptcadence/__about__.py`. Whatever moved
   `pyproject.toml` at 1.0.0 was not the version.
4. **The kickoff's suggested digest expression would have left one case mismatched.** "Digest
   `json_sanitize(call.arguments)` when `arguments_parsed`, else the text as today" keeps
   `_args_text`'s `repr()` branch for a non-`str`, non-parsed value, which the record never uses.
   The unconditional expression is smaller and covers it. See §3.
5. **The golden's `args_sha256` is masked, so §12's second read-only question has a flatter answer
   than it expects.** There are three occurrences, not one, all of them the event's, and all three
   are scrubbed to `"<sha>"` — so the golden distinguishes neither digest and could never have
   caught the mismatch.
6. Confirmed true, for the record: PromptCadence at `b4b67ac`/1.0.0 clean and tagged; LoadCoach at
   `2a7ac58`/1.1.1 clean; the venv at 3.13.15; both stated file digests; the OpenAPI diff being
   `info.version` alone; contract 6's implementation at `domain/turns.py`; both digest sites; the
   three mirrors `cmp`-identical; and the highest ADR in `adr/` being `0099` (checked; no ADR was
   written, as neither decision left its default).

## 6. What I5 inherits

**Nothing that this row found.** All three items I5 would have inherited were raised at the
interview (§9) and the operator took every one of them off its default, so all three are done here
rather than deferred. What remains is not inheritance, it is a publish sequence — §10.

The one standing caution for I5: it ships `1.1.0` **on top of** `1.0.1`, and `1.0.1` is not cut
yet. Do not start I5 until §10 has run to completion, or the version edge stated in
`roadmap/outstanding-work.md` §3 breaks and 1.0.1 becomes a maintenance branch off `v1.0.0`.

**I6 runs next, not I5** (operator decision, 2026-09-06). I6 — the thinking control on Ollama —
depends on I3, which is done, and no release waits on it: its first half is a read-only probe of
which installed models honour `think`, and nothing in the suite sets `think` today. So it is the
one row that can run in full while 1.0.1 is held, and it cannot collide with the version bump
because it touches no task profile and no version. I5 stays behind §10.

## 7. §12's read-only items, answered

1. **Does `upgrading.md` need a 1.0.1 line?** For *Migration notes*, **no** — 1.0.1 adds no
   migration, changes no schema and changes no stored value, so the table's contract ("which
   revisions this version introduces") has nothing to record. The *Compatibility* sentence was a
   separate matter and the operator chose to fix it here (§9): it now names LoadCoach `1.1.1`, says
   the `≥ 1.1` requirement did not move, and records the one dependency floor that did
   (`toolyard`).
2. **Is the golden's `args_sha256` the event's or the record's?** The event's, three times, and
   all three are masked to `"<sha>"`. Gate C had to find out. See §5 item 5.
3. **Does `adapters.measured` mean anything to a PromptCadence tier?** No. `grep` over `src/` and
   the repository's `docs/` finds no occurrence of the profile id anywhere in PromptCadence; a tier
   is configuration over exactly one named LoadCoach task profile (ADR-0047 §1) and no shipped or
   documented tier names this one. It arrives in the vendored file because the file is vendored
   whole, and it is inert: `shipped_profiles()` keys by profile id and nothing counts the profiles.
   It is LoadCoach's H5/LA3 profile for selecting among a base and its measured adapter subjects —
   FreeWeight evidence territory, not harness territory.

## 8. The flaky test, and a first diagnosis that was wrong

Worth recording in full, because the first answer was confident and false.

`tests/e2e/test_explanation_surfaces.py::test_the_cli_prints_the_document_with_json` failed about
one full-suite run in five and passed every time in isolation. It was **verified pre-existing**
before anything was changed: nine full-suite runs at `v1.0.0` in a scratch worktree reproduced the
same test at the same rate, so it shipped in 1.0.0 and is not this row's doing.

**The wrong diagnosis.** `_closed_port()` binds an ephemeral port, reads the number, closes the
socket and assumes nothing claims it before the CLI probes it — a textbook time-of-check /
time-of-use race, in a helper duplicated across two test files. It looked like the answer. It was
replaced with the discard port (`9`) that `tests/e2e/test_bypass_journey.py:282` already used —
privileged, outside the ephemeral range, unassignable — and the flake **carried on failing**. Had
the fix been committed on the strength of the reasoning without re-running the suite twenty times,
the row would have shipped a confident non-fix and closed the finding.

**The actual cause**, from the captured failure:

```
assert json.loads(result.output)["schema"] == SCHEMA_NAME
E   json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
s = '--- Logging error ---\nTraceback ...\nValueError: I/O operation on closed file.\n
     ... Message: \'Will assume %s DDL.\' Arguments: (\'non-transactional\',)'
```

`configure_logging` installs `logging.StreamHandler(sys.stderr)`, which binds the stream object
*at call time* — as the standard library's own handler does. Under Click's `CliRunner` that object
is a temporary buffer, closed when the invocation ends; the handler survives on the root logger,
which is process-global and which no test owns. Later, another test's `TestClient` starts an
application on an anyio portal thread, the application runs its migrations, Alembic logs *"Will
assume non-transactional DDL"* — and that record writes to the closed buffer, raises, and
`logging` reports the failure to whatever `sys.stderr` is current. Which is the *next* CLI
invocation's captured output. The JSON document the command printed is then no longer the only
thing in `result.output`.

So it is cross-test contamination through global logging state, not a port race at all, and it can
strike any test that parses a CLI invocation's output — the ledger surfaces are equally exposed.
The fix is an autouse fixture in `tests/conftest.py` that saves the root logger's handlers and
level and restores them afterwards. Test-only; no shipped behaviour changes.

**Why not fix it in `configure_logging` instead.** Making the handler resolve `sys.stderr` per
record (the standard library's own `_StderrHandler` idiom) would stop the stale-stream exception —
and would make things worse here, because every background log line would then land in the current
`CliRunner` buffer and pollute the output directly rather than occasionally. The production
handler is not the defect; the tests never restoring what they configured is.

**Proof:** the failing seed `4198236421` now passes, and ten consecutive full-suite runs are green
(§1, Gate E).

The `_closed_port` → discard-port change was kept even though it was not the cause. It removes a
duplicated helper and twelve lines, closes a real if much narrower race, and matches an idiom
already in the repository — but it fixed nothing, and this handoff says so rather than letting the
commit imply otherwise.

## 9. The operator interview, and what it changed

Three questions were put at the end of the row. All three had a default; the operator declined
every default. That roughly doubled the row and moved the release behind another package's
publish, which is stated here so the size of I4 is not mistaken for scope creep.

| Question | Default offered | Chosen | Consequence |
| --- | --- | --- | --- |
| The pre-existing e2e flake | leave for I5 | **fix now, in 1.0.1** | Gate E; and the first diagnosis turned out wrong (§8) |
| The private `toolyard._safe` import | ship as-is, re-export later | **bump ToolYard first** | Gate F; `toolyard 0.1.1` prepared; 1.0.1 now waits on a publish |
| `upgrading.md`'s stale LoadCoach line | leave for I5 | **update now** | folded into `dcade58`, together with the `toolyard` floor |

The second is the one with teeth. `pyproject.toml` now requires `toolyard>=0.1.1`; PyPI has only
`0.1.0`; `requirements/ci.lock` still pins `0.1.0` with hashes and **cannot be regenerated until
`0.1.1` is published**, because the lock is generated with `--generate-hashes` and hashes require
the artefact on an index. So PromptCadence CI is expected red on these five commits, and the
release commit is held. This was the stated cost of the choice, not a surprise.

## 10. Left for the operator — a sequence, in this order

The order matters; steps 2 and 3 cannot be swapped.

**1. Publish ToolYard.** In `/home/jpk/ai/suite/py/ToolYard`, two commits ahead of `origin/main`,
unpushed and untagged (no push was run, and no push dry-run — standing instruction of 2026-09-04):

```
338f9c7 chore(release): toolyard 0.1.1
1e14788 feat(api): export json_sanitize from the package root
```

Push, confirm CI green, tag `v0.1.1`, publish `toolyard 0.1.1` to PyPI.

**2. Regenerate PromptCadence's lock**, once `toolyard 0.1.1` resolves from PyPI —
`requirements/README.md:41` holds the invocation, and from I3: `pip-compile` needs
`--upgrade-package toolyard` to move a single pin. Then reinstall the venv from the lock, which
also replaces the locally built wheel this row installed (§1, Gate F).

**3. Cut `promptcadence 1.0.1`** — redo Gate D exactly as §1 records it: move `[Unreleased]` to
`## [1.0.1]`, `__about__.py` to `1.0.1`, regenerate `docs/openapi.json` (the diff is the one
`info.version` line), run the full gate and `pytest --cov`, commit `chore(release): promptcadence
1.0.1`. Then push, tag `v1.0.1`, publish.

**4. Push `docs`**, which is ahead by five including this handoff.

Two things to know while doing it. PromptCadence CI will be **red between steps 1 and 2** and that
is expected, not a regression — the lock installs `toolyard 0.1.0` and the loop imports a name
`0.1.1` introduced. And `loadcoach 1.1.1` is still untagged with PyPI holding `1.0.0`; that does
not block anything here, since the contract snapshots vendor files at a commit, but it is the same
publish backlog.
