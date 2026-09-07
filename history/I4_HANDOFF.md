# I4 — PromptCadence 1.0.1: the vendored LoadCoach snapshots, and I2's two leftovers

**Row:** I4 of `roadmap/outstanding-work.md` §1.
**Model:** Sonnet 5 · standard, as scheduled. No deviation.
**Date:** 2026-09-06.
**Repository:** `/home/jpk/ai/suite/PromptCadence` only. LoadCoach was read and never written; it
ends this row exactly where it started, at `2a7ac58`, clean.
**Ships:** `promptcadence 1.0.1` **prepared, not published** — four commits on `main`, ahead of
`origin/main` by four, untagged. The push, the tag and the publish are the operator's.

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

### Gate D — the release commit

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

## 2. The gates as commits

```
0ec2c36 chore(release): promptcadence 1.0.1
b96d2d8 fix(events): tool.call.started digests the arguments the record digests
9b5fb44 fix(explanation): a turn that completed with no text says so
6356f73 test(contract): the vendored LoadCoach snapshots are 1.1.1's
```

Gate B's commit is a `fix(...)` rather than the kickoff's `docs(changelog): …` because the
explanation-surface check found a real one-line render to take (§3, decision 1).

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

**One thing to flag rather than hide.** The fix imports `json_sanitize` from `toolyard._safe`, a
private module. It is in that module's `__all__`, and the import carries a comment saying why:
the two digests have to agree byte for byte, so borrowing ToolYard's function is safer than
reimplementing a hardening routine that must produce identical output. `lint-imports` is content
(5 contracts kept). The clean resolution is for ToolYard to re-export `json_sanitize` at package
level, which is a ToolYard change and therefore not this row's — see §6.

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
6. **`docs/openapi.json` differs from `b4b67ac`'s by `info.version` only** —
   `git diff v1.0.0..HEAD -- docs/openapi.json` is two lines. ✔
7. **`git log --oneline v1.0.0..HEAD`** shows the four gate commits ending in the release commit;
   `git status -sb` is clean in both repositories (PromptCadence `ahead 4`, LoadCoach level); the
   three mirrors are still `cmp`-identical. ✔

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

1. **A pre-existing flaky test, shipped in 1.0.0, not caused by this row.**
   `tests/e2e/test_explanation_surfaces.py::test_the_cli_prints_the_document_with_json` fails
   roughly once in four full-suite runs, and passes every time in isolation. The cause is a
   time-of-check/time-of-use race in `_closed_port()` (`tests/e2e/test_explanation_surfaces.py:46`):
   it binds an ephemeral port, reads the number, closes the socket, and then assumes nothing else
   binds it before the CLI probes it — so the CLI intermittently finds a *live* listener where the
   test wanted "either"-mode to fall through to its local path. **This was verified against
   `v1.0.0` in a scratch worktree, not assumed:** nine full-suite runs at `b4b67ac` produced the
   same failure, the same test, at the same rate. It is untouched by I4 (`_closed_port` last moved
   at `63c6014`, before 1.0.0, and no file this row edited is reachable from it). Left alone
   deliberately — a patch release should not widen into test infrastructure — but it should be
   fixed, and the fix is to force the local path explicitly rather than to guess an unused port.
2. **`toolyard._safe.json_sanitize` should be re-exported from `toolyard`.** PromptCadence now
   imports it privately, out of necessity (§3). A one-line addition to ToolYard's `__init__` would
   make the import public; it is a ToolYard change and would ride ToolYard's next release.
3. **`upgrading.md`'s compatibility line is now understated.** It says *"PromptCadence 1.0.0 is
   tested against LoadCoach `1.1.0`"*; the contract tests now vendor `1.1.1`. The requirement
   (`≥ 1.1`) is unchanged and no migration exists, so §7 below says 1.0.1 needs no *Migration
   notes* row — but that one sentence wants updating, and doing it here would have put a doc commit
   after the release commit. Left for I5, which touches this document anyway.
4. Nothing else. No route, no `[server]`/`[tools]` key, no pin, no dependency and no LoadCoach file
   was touched, and nothing that looked like I5's (runtime-settings endpoints) or I6's (thinking
   control) work was started.

## 7. §12's read-only items, answered

1. **Does `upgrading.md` need a 1.0.1 line?** For *Migration notes*, **no** — 1.0.1 adds no
   migration, changes no schema and changes no stored value, so the table's contract ("which
   revisions this version introduces") has nothing to record. The *Compatibility* sentence is a
   separate matter; see §6 item 3.
2. **Is the golden's `args_sha256` the event's or the record's?** The event's, three times, and
   all three are masked to `"<sha>"`. Gate C had to find out. See §5 item 5.
3. **Does `adapters.measured` mean anything to a PromptCadence tier?** No. `grep` over `src/` and
   the repository's `docs/` finds no occurrence of the profile id anywhere in PromptCadence; a tier
   is configuration over exactly one named LoadCoach task profile (ADR-0047 §1) and no shipped or
   documented tier names this one. It arrives in the vendored file because the file is vendored
   whole, and it is inert: `shipped_profiles()` keys by profile id and nothing counts the profiles.
   It is LoadCoach's H5/LA3 profile for selecting among a base and its measured adapter subjects —
   FreeWeight evidence territory, not harness territory.

## 8. Left for the operator

Four commits sit on `main` in `/home/jpk/ai/suite/PromptCadence`, ahead of `origin/main` by four,
**unpushed and untagged** (standing instruction of 2026-09-04 — no push was run, and no push
dry-run either):

```
0ec2c36 chore(release): promptcadence 1.0.1
b96d2d8 fix(events): tool.call.started digests the arguments the record digests
9b5fb44 fix(explanation): a turn that completed with no text says so
6356f73 test(contract): the vendored LoadCoach snapshots are 1.1.1's
```

1. `git push origin main` from `PromptCadence`, and confirm CI green.
2. `git tag -a v1.0.1` and push the tag.
3. Publish `promptcadence 1.0.1` to PyPI.
4. `git push` the `docs` repository, which is ahead by four including this handoff.

Two things the operator may want to decide before tagging are raised in §6: the flaky e2e test
(inherited, pre-1.0.0) and the private `toolyard._safe` import.
