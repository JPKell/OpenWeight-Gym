# Kickoff — I4: PromptCadence 1.0.1 — the vendored LoadCoach snapshots, and I2's two leftovers

**Row:** I4 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1 — scheduled
at the I3 interview as I5, renumbered I4 on 2026-09-06 so the table reads in execution order.
**Model:** **Sonnet 5 · standard**, as scheduled ([model-assignment](docs/roadmap/model-assignment.md)).
Daytime or overnight; nothing in this row needs a person to watch it. Record any deviation
([model-assignment §3.5](docs/roadmap/model-assignment.md)).
**Repositories:** `/home/jpk/ai/suite/PromptCadence`, and `/home/jpk/ai/suite/docs` only if §0.2
decision 2 produces an ADR. Nothing else — **LoadCoach is read, never edited.**
**Ships:** **`promptcadence 1.0.1` prepared, not published** — the changelog, `__about__.py`, the
regenerated `docs/openapi.json` and the release commit are yours; **`git push`, the tag and the
publish are the operator's** (standing instruction of 2026-09-04). Do not run a push dry-run.
**Runs after:** **I3** (done 2026-09-06, `docs/history/handoffs/I3_HANDOFF.md`).
**Runs before:** **I5** — a hard edge on version numbers (`outstanding-work` §3): I5 ships 1.1.0,
and a 1.0.1 cut after it would be a maintenance branch off `v1.0.0`, which nothing in this suite has
done. If you find `__version__` already past `1.0.0` when you start, stop and say so.
**Not in this session:** the runtime-settings endpoints (that is I5), the thinking control (I6),
any LoadCoach change, any dependency bump beyond what §0 names. The row's own "why this model"
column says it: *the risk is picking up more than a patch should.*

---

## 0. Machine facts, verified 2026-09-06 before this prompt was written

Confirm the marked ones; do not re-derive the rest.

* **PromptCadence `main` is at `b4b67ac`** ("chore(release): promptcadence 1.0.0 — M12"), clean,
  level with `origin/main`, tagged `v1.0.0`, and **`promptcadence 1.0.0` is on PyPI**. `__about__.py`
  says `1.0.0`; `CHANGELOG.md` has an empty `## [Unreleased]` above `## [1.0.0] — 2026-09-06`.
  **Confirm** `git status -sb` at the start and at the end.
* **The venv is Python 3.13.15** (`.venv/bin/python --version`). It holds `setspec 0.5.0` and
  `commissioner 0.1.0` while `requirements/ci.lock` pins `setspec==0.6.0` and `commissioner==0.1.1`
  — the lock moved at I2 and the venv did not follow. `pip install -e ".[dev]"` once, then run the
  gate; the venv is a workstation, the lock is the contract. Name the interpreter and the invocation
  in the report (M5C-13).
* **LoadCoach `main` is at `2a7ac58`** ("chore(release): loadcoach 1.1.1"), level with `origin`,
  `__about__.py` `1.1.1`. `git tag` there lists `v1.0.0` and `v1.1.0`; **`v1.1.1` is not tagged and
  PyPI holds `loadcoach 1.0.0`.** That changes nothing here — the snapshots vendor *files at a
  commit*, and `2a7ac58` is the commit.
* **The two snapshots and exactly what differs.** Both tests live in `tests/contract/`:
  * `loadcoach_openapi.json` — `SNAPSHOT_SHA256` at `test_loadcoach_contract.py:45`,
    `SNAPSHOT_SOURCE` at `:46`–`:48` (currently *"LoadCoach docs/openapi.json at 93063bd (LoadCoach
    1.1, LA2/LA3; last changed at cbe1ef9)"*), the digest assertion at `:56`. Against
    `LoadCoach/docs/openapi.json` at `2a7ac58` (sha256
    `ca407d7ff689fcf275767a6aceb891de77d67b0a33219f244da35bd867e63848`) the **only** difference is
    `info.version`: `1.1.0` → `1.1.1`.
  * `loadcoach_task_profiles.toml` — `SNAPSHOT_SHA256` at `test_loadcoach_task_profiles.py:37`,
    `SNAPSHOT_SOURCE` at `:38` (*"LoadCoach src/loadcoach/config/task_profiles.toml at 5c5aa1f"*),
    the digest assertion at `:65`. Against `LoadCoach/src/loadcoach/config/task_profiles.toml` at
    `2a7ac58` (sha256 `3edb1f7ddc2c3c7b848e070a12f7da0efdf55d82140accc5683f42a3b542f457`) the
    diff is **larger than the row says**. The I3 handoff named the rewritten `tools.plan` comment;
    `diff` also shows **`max_output_chars = 50000`** added under `[task_profiles."tools.plan".validation]`
    and **the whole `adapters.measured` profile** (H5/LA3) with its explanatory comment. The
    snapshot at `5c5aa1f` predates both. Vendor the file whole; do not hand-merge the comment.
* **Who reads the TOML snapshot.** `shipped_profiles()` in `test_loadcoach_task_profiles.py` is
  also the fake LoadCoach's source of profile shapes — `tests/security/test_checklist.py:49`,
  `tests/integration/test_tool_execution.py:146`, `tests/e2e/test_approval_surfaces.py:46`,
  `tests/e2e/test_console.py:58`, `tests/e2e/test_ledger_surfaces.py:51` all call it by profile
  id. None counts profiles, so `adapters.measured` arriving is inert; but the fake derives a
  `length` validation check from `max_output_chars` (`tests/fakes/loadcoach_app.py:28`–`:30`), so
  `tools.plan` gaining `max_output_chars = 50000` **can** change what a fake job document carries.
  Run the whole suite after the refresh, not just `tests/contract/`. The eleven assertions in
  `test_loadcoach_task_profiles.py:65`–`:132` are the contract; expect all to hold unchanged.
* **Contract 6 and the code that implements it.** Spec §11 contract 6: *"A step completes only on a
  declared `finish_reason` of `STOP` (or a schema-validated structured result); `LENGTH`, `ERROR`
  and absence are handled explicitly, never read as success."* The implementation is
  `domain/turns.py:98`–`:99`: `if finish_reason is FinishReason.STOP: return
  FinishDecision(FinishOutcome.COMPLETE, "the provider declared finish_reason=stop")` — **text
  length is not an input to that decision**, and its docstring says *"Refuses nothing: every
  combination of inputs has an answer."* `services/loop.py:2740` records `finish_declared` from it;
  `:2856` acts on it.
* **The digest mismatch, both sites.** The event: `services/loop.py:3506` computes
  `args_digest = sha256_of(_args_text(call))`, where `_args_text` (`:4100`–`:4104`) is
  `canonical_json(call.arguments)` when parsed, else the raw string — a digest of *text*. The
  record: ToolYard `executor.py:584` stores `args_sha256=_args_digest(state.request.args)`, and
  `_args_digest` (`:701`–`:710`) is `sha256_of(json_sanitize(args))` — a digest of *structure*.
  `sha256_of` of a string and `sha256_of` of the dict that string encodes are different numbers,
  so the `tool.call.started` event and the `tool_call_records` row disagree for every call.
  ADR-0096's replay stub uses the structure digest and matches the row
  (`tests/integration/test_replay_cap.py:72` asserts stub == record); **no test compares the
  event's digest to the record's** (`test_tool_execution.py:429`, `:451` only assert presence).
  Spec §17 and lifecycle.md do not define which text `args_sha256` digests — grep finds no
  occurrence in either — so the wire contract is the docstring on `domain/tools.py:92` — which already says *"The
  digest of the sanitized arguments"*, i.e. the structure — and the event's own behaviour, which
  contradicts it. One golden carries a digest: `tests/golden/trajectory_explanation.json`
  (one occurrence; check whether it is the event's or the record's before you touch either).
* **`docs/openapi.json` will change by exactly one line** — `info.version` — and the release commit
  carries it, as `b4b67ac` did (four files: `CHANGELOG.md`, `docs/openapi.json`, `pyproject.toml`,
  `src/promptcadence/__about__.py`). Regenerate with the command the test names:
  `python -c 'from tests.contract.test_openapi_snapshot import write; write()'`.
* **The three PromptCadence mirrors are `cmp`-identical today** (`docs/apps/promptcadence/{spec,
  lifecycle,development-plan}.md` ↔ `PromptCadence/docs/apps/promptcadence/`). Keep them so; this
  row should touch none of them unless §0.2 decision 2 amends contract 6.
* **The highest ADR in `docs/adr/` is `0099`.** Check the directory rather than trusting this line.
* **The lock.** `requirements/README.md:41` and `:63` hold the two `pip-compile` invocations; from
  I3: `pip-compile` needs `--upgrade-package <name>` to move a single pin. **Nothing in this row
  moves a pin.** If the gate fails on a resolution, that is a finding for the handoff, not a bump.
* **Never `git push`.** Commit at every gate boundary; leave pushing, tagging and publishing to
  the operator.

## 0.1 What the row actually is

Three items, in this order, and nothing else:

1. **The refresh** — two files re-copied from LoadCoach at `2a7ac58`, two digests re-pinned, two
   `SNAPSHOT_SOURCE` strings rewritten in the existing convention (*"… at 2a7ac58 (LoadCoach 1.1.1;
   last changed at cb1cfac)"* for the TOML, *"… at 2a7ac58 (LoadCoach 1.1.1; last changed at
   2a7ac58)"* for the OpenAPI file — `git log -1 -- <path>` in LoadCoach is the source of the
   second hash, confirm both).
2. **F2** — a decision, recorded, and code only if the decision says so (§0.2).
3. **The digest mismatch** — a decision, recorded, and code only if the decision says so (§0.2).

**F1 is not on this list.** I2's F1 (the read tools' descriptions naming `read_roots`) was fixed
before the tag and shipped in 1.0.0 (`6a0d55f`, CHANGELOG *Added*). If you find yourself editing
`services/tools.py::_build`, you have picked up the wrong finding.

## 0.2 The decisions this row must take, and record

Both are decisions I2 deliberately left rather than patched. A patch release is the wrong place
to change a contract, so the default for each is *keep the behaviour, document it*, and the row
must say in the handoff why it took the default or why it did not.

1. **F2 — does an empty declared `STOP` complete a step?** I2 §10 run 3: the final answer was a
   declared `stop` carrying 12 tokens and no text; contract 6 says a declared `STOP` completes the
   step, and it did. The harness read the wire correctly. **Default: yes, unchanged.** Reasons the
   default is right: (a) contract 6 is a *wire* contract — the declared reason, nothing else — and
   G3's retryable set deliberately excludes declared finishes; adding "and the text is non-empty"
   makes text content a control input, which is the model deciding control flow by another name;
   (b) "empty" has no stable definition across a text step and a structured one (`{}` is valid
   JSON and an empty plan — I3 §9 measured exactly that on `tools.plan`); (c) the honest surface
   for an operator is the *explanation*, not a halt: a step that completed with no text should
   say so where the explanation lists the step's outcome. **Do:** record the decision in the
   handoff and in `CHANGELOG.md` under *Known limitations* (it is a 1.0 behaviour, now named);
   check whether the explanation surface already makes an empty completion visible (the console
   step row, `services/explanation.py`) and if it does not, that is a one-line render — take it
   only if it is genuinely one line and golden-safe. **If you conclude the default is wrong**,
   contract 6 changes, which is an ADR (`0100` if nothing has landed since) and a spec §11 edit
   mirrored to the repo — and that is 1.1 material, so **stop and write it up for the interview
   rather than shipping it as 1.0.1.**
2. **The `args_sha256` mismatch — which digest is the contract?** The record's (structure,
   ToolYard's, matches the ADR-0096 stub) or the event's (text, PromptCadence's own)? **Default:
   the record's is the contract, and the event moves to match it.** Reasons: the row in
   `tool_call_records` is what the explanation renders, what retention keeps, and what
   ADR-0096's replay stub already carries; an event that disagrees with all three is the odd one
   out, and the event is emitted by PromptCadence, so the fix is local. The change is one
   expression at `services/loop.py:3506` — digest `json_sanitize(call.arguments)` when
   `arguments_parsed`, else the text as today — plus **one test that asserts event digest ==
   record digest for the same call** (extend `tests/integration/test_tool_execution.py` beside
   `:429`; that assertion is the one thing this row must leave behind). Check the golden first:
   if `tests/golden/trajectory_explanation.json` carries the event's digest, the golden changes
   and the handoff says why; if it carries the record's, nothing moves. **Why this is a patch
   and not a minor:** the event's digest identified nothing anyone could look up — it matched no
   row — so no consumer can have depended on its value; the field name and shape are unchanged.
   Say that in the changelog entry. **If you conclude the event's text digest was the intended
   contract**, the change is instead a docstring on `domain/tools.py:92` naming what it digests
   and a note in spec §17 — again 1.1 material for the spec half, so record it and stop there.

Neither decision needs an ADR on the default path. Do not write one to look thorough.

## 1. Setup

```bash
cd /home/jpk/ai/suite/PromptCadence
git status -sb                                   # b4b67ac, clean, level with origin
source .venv/bin/activate && python --version    # 3.13.15
pip install -e ".[dev]"                          # brings the venv to the lock's setspec/commissioner
cd /home/jpk/ai/suite/LoadCoach && git status -sb && git rev-parse HEAD   # 2a7ac58, clean — read only
```

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work in the component directory, never the workspace root. Its venv, `pip install -e ".[dev]"`.
* Finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports && pytest
  -m "not live and not performance"` green; `CHANGELOG.md` updated; one Conventional Commit per
  gate. Name the interpreter in the report (M5C-13).
* House method: docstring-first, `from __future__ import annotations`, units in names,
  keyword-only optionals, injected clocks/providers/roots.
* Read `architecture/master-architecture.md` §§1–3 and the PromptCadence gold-standards section
  before the row's reading list.
* Working-tree integrity (workspace `CLAUDE.md`): `git status --short` at start and end in both
  repositories; `git checkout --` anything modified that you did not edit; never `git add -A`.

## 3. Reading list, in this order

1. `docs/history/handoffs/I3_HANDOFF.md` §9 (*What J1 inherits* — the snapshot finding) and §10 item 5.
2. `docs/history/handoffs/I2_HANDOFF.md` §5 (the digest bullet), §10 (run 3, F2), §13, §14.
3. `docs/apps/promptcadence/spec.md` §11 contract 6, and §17 for the event pair.
4. `docs/adr/0096-*.md` (the replay cap — the stub's digest is the record's).
5. `PromptCadence/tests/contract/test_loadcoach_contract.py` and
   `test_loadcoach_task_profiles.py`, whole — they are short.
6. `PromptCadence/domain/turns.py::decide_finish`, `services/loop.py:3495`–`:3520` and
   `:4100`–`:4104`, ToolYard `executor.py:701`–`:710`.
7. `docs/standards/packaging-and-release-standards.md` §3 (patch = fix) and §6.

## 4. The shape of the work — four gates

Commit at each. Gate letters are the commit boundaries, not the changelog's headings.

## 5. Gate A — the refresh

* `cp` both files from LoadCoach at `2a7ac58`; `sha256sum` each and paste the two digests into the
  two `SNAPSHOT_SHA256` constants; rewrite both `SNAPSHOT_SOURCE` strings with the commit, the
  version and the last-changed hash (§0.1).
* `pytest tests/contract/` green, then **the whole default suite** (the fake reads the TOML —
  §0). If any non-contract test moves because `tools.plan` now carries `max_output_chars`, the
  handoff names it and says whether the test or the fixture was wrong; do not loosen an assertion
  to pass.
* Changelog, under `[Unreleased]` → *Changed*: the two snapshots now vendor LoadCoach 1.1.1 at
  `2a7ac58`, naming the three things that differ (version, `tools.plan`'s comment and
  `max_output_chars`, `adapters.measured`).
* Commit: `test(contract): the vendored LoadCoach snapshots are 1.1.1's`.

## 6. Gate B — F2, decided

* Take §0.2 decision 1. On the default: the changelog *Known limitations* entry, the handoff
  paragraph, and the explanation-surface check — code only if it is the one-line render described
  there. On the non-default: the write-up, no code, and go to Gate C.
* Commit (default path): `docs(changelog): an empty declared stop completes a step, by contract 6`
  — or the render's own `fix(explanation): …` if that line was taken.

## 7. Gate C — the digest, decided

* Take §0.2 decision 2. On the default: the one-expression change at `loop.py:3506`, the
  equality test, the golden check, the changelog entry under *Fixed* with the "why this is a
  patch" sentence. On the non-default: the docstring, the write-up, no spec edit.
* `pytest tests/integration/test_tool_execution.py tests/integration/test_replay_cap.py
  tests/golden -p no:randomly` first to isolate, then the whole suite with randomisation on.
* Commit: `fix(events): tool.call.started digests the arguments the record digests`.

## 8. Gate D — the release commit

* Move `[Unreleased]` to `## [1.0.1] — <date>`; leave a fresh empty `## [Unreleased]`.
* `__about__.py` → `1.0.1`; regenerate `docs/openapi.json` (§0) and confirm the diff is the one
  version line.
* Full gate (§2), `pytest --cov` once to confirm the floor still holds (85 % for an application).
* Commit: `chore(release): promptcadence 1.0.1`. **Do not tag. Do not push.**

## 9. Exit conditions — all of these, demonstrably

1. `pytest tests/contract/ -p no:randomly` and the whole default suite green on 3.13.15, named.
2. `sha256sum tests/contract/loadcoach_openapi.json tests/contract/loadcoach_task_profiles.toml`
   equals the two constants **and** equals `sha256sum` of the LoadCoach files at `2a7ac58`.
3. Both `SNAPSHOT_SOURCE` strings name `2a7ac58` and the correct last-changed hash.
4. A test exists that asserts the `tool.call.started` event's `args_sha256` equals the
   `tool_call_records` row's for the same call — or the handoff says which decision replaced it.
5. F2's decision is in the changelog and the handoff, with the reason.
6. `docs/openapi.json` differs from `b4b67ac`'s by `info.version` only.
7. `git log --oneline v1.0.0..HEAD` shows the gate commits and ends in the release commit;
   `git status -sb` clean in both repositories; the three mirrors still `cmp`-identical.

## 10. Closing duties

Write `docs/history/handoffs/I4_HANDOFF.md` in the shape of `I3_HANDOFF.md`: gate results with exact
invocations, the gates as commits, the two decisions with the losing option's claim, *things this
prompt said that turned out not to be true*, *what I5 inherits*, *left for the operator* (the push
list, the tag, the publish). Then update the I4 row in `outstanding-work.md` §1 with the done marker
and the handoff path, the way I1–I3 are marked, and commit `docs` separately.

## 11. Stop rules

* **Stop** if `__version__` is not `1.0.0` when you start (I5 ran first; the row is now 1.1.1 and
  the operator decides).
* **Stop** if LoadCoach `main` is not at `2a7ac58`: pin to whatever it is, but say so, and do not
  vendor an uncommitted file.
* **Stop and write up** rather than ship if either §0.2 decision leaves its default — both
  non-default paths change a contract, and a contract does not change in a patch.
* **Do not** bump any pin, add any dependency, touch `[server]`, `[tools]` or any route, or edit
  a LoadCoach file. Anything that looks like it belongs to I5 or I6 goes in the handoff under
  *what I5 inherits*.
* **Do not** edit the three mirrored documents. If you believe one is wrong, say so in the handoff.

## 12. If you finish with capacity left

Read-only, reported in the handoff, no code:

* Whether `docs/upgrading.md` needs a 1.0.1 line at all (no migration; likely not — say so).
* Whether `tests/golden/trajectory_explanation.json`'s one `args_sha256` is the event's or the
  record's, if Gate C did not already have to find out.
* One sentence on whether `adapters.measured` arriving in the vendored TOML means anything to a
  PromptCadence tier (it should not — no tier names it — but a reader of `docs/tiers.md` may ask).
