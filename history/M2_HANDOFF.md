# M2 Handoff — LoadCoach's `FreeWeightClient` negotiates FreeWeight's API version

Row M2 of [`docs/roadmap/outstanding-work.md`](../roadmap/outstanding-work.md) §1 (not milestone
M2). Kickoff: `docs/history/m2-loadcoach-freeweight-version.prompt.md`. Overnight, unattended,
Sonnet 5 · high, per §2.12's overnight adjustment of the scheduled `standard`.

This session resumed mid-row after the harness process died with LoadCoach's code edits and the
docs edits both uncommitted. Nothing was lost: the working trees held exactly the state described
below, git status and diff were reviewed against both repositories' current `HEAD` (docs had moved
under row M1 and row M3 in the meantime — M3's `b373469` had already removed IdeaPress's footnote
⁴ and rows from `graceful-degradation.md`; this row's own one-line cell edit was re-verified to sit
cleanly on top of that commit, not to revert it, before anything was staged), and the row continued
from there.

## What this row is

ADR-0013 and `standards/api-and-contract-standards.md` §12 oblige every HTTP client in the suite to
negotiate the server's API major on first contact and refuse an incompatible one with the ADR-0013
code. PromptCadence's `LoadCoachClient` does; IdeaPress's has since M8. LoadCoach's evidence client,
`FreeWeightClient` (`infrastructure/freeweight_client.py`), never read a version from FreeWeight, so
`graceful-degradation.md` §2.1's "incompatible API major version" cell for LoadCoach was the last
`untested — behaviour not implemented` cell in the row index (row L8's finding).

## The decision this row made

Stated in the kickoff, applied conservatively: when FreeWeight is unreachable for `/version`, the
fetch fails the way an unreachable FreeWeight already fails (`EvidenceSourceUnreachable`) — no
version guess, no "assume compatible". A FreeWeight too old to serve `/version` at all (a 404) is
*incompatible*, refused with the ADR-0013 code (`EvidenceSourceIncompatible`,
`API_VERSION_UNSUPPORTED`).

One implementation choice the kickoff left open, decided here and worth recording explicitly:
**`version()` is not called inside `fetch()`.** `fetch()`'s ADR-0026 §3 mechanics (scheme, host
allowlist, literal/resolved link-local addresses, redirects, streaming size cap) are proved
byte-for-byte identical to ToolYard's generic `http_fetch` tool by
`tests/integration/test_adr0026_shared_vectors.py`, a shared fixture with an exact
`requests_expected` count per vector. Folding a FreeWeight-specific version probe into that shared
method would have meant either ToolYard's tool silently grows a FreeWeight concept it has no
business having, or the two fetchers diverge from a fixture that is supposed to prove they cannot.
`version()` is therefore a separate method, called by whichever caller is pulling *from a
FreeWeight specifically* — the evidence-import CLI command, `POST /evidence/import`, and
`refresh_from_freeweight`'s periodic pull — immediately before its own `fetch()` call. This is one
layer higher than PromptCadence's and IdeaPress's clients check it, because their whole client
speaks to one application while this one is a generic ADR-0026 fetcher first and a FreeWeight
client second. The shared-vector file was not touched, and needed no vector edits.

A consequence worth naming: because every current caller constructs a short-lived `FreeWeightClient`
for one operation and discards it, the TTL cache's practical effect today is "one negotiation per
operation" rather than "one negotiation per `_VERSION_CACHE_SECONDS` window across many operations"
— the worker's periodic `refresh_from_freeweight` tick (`services/worker.py`) builds a fresh client
each time it runs, so the cache never actually spans two ticks in production. The mechanism is
correctly built and directly tested (exit condition 3, below); redesigning the worker to hold a
long-lived client so the cache pays off across ticks was out of this row's scope (not asked for,
and re-plumbing `QueueRuntime`'s evidence-refresh callback is a bigger change than a version check)
and is left as a possible future row if the extra round trip per tick is ever measured to matter.

## Gates, as commits

**Gate A — docs.** Commit `2e1b38c` in `docs`:
- `apps/loadcoach/spec.md` — the evidence-consumer section (the `EVIDENCE_SOURCE_REFUSED` /
  `EVIDENCE_IMPORT_FAILED` paragraph) now names `API_VERSION_UNSUPPORTED` and distinguishes all
  three codes.
- `apps/loadcoach/api.md` — `POST /evidence/import`'s row states the negotiation and the 404 case;
  `summary.status`'s enumerated values gained `incompatible`.
- `architecture/graceful-degradation.md` — §2's LoadCoach cell rewritten from "**Gap**..." to the
  built behaviour; §2.1's LoadCoach cell replaced `untested — behaviour not implemented` with the
  five tests that prove it; the "What this index shows" paragraph rewritten to record the closure
  and correct its own "no row... untested" claim to the precise one ADR-0042's framing supports
  (no cell reads `behaviour not implemented`; ordinary missing-test `untested` cells for other
  conditions are unaffected and unclaimed-about).
- Mirrored byte-identically into `LoadCoach/docs/apps/loadcoach/{spec,api}.md` (commit `f037d50` in
  `LoadCoach`), verified with `cmp`. `graceful-degradation.md` is workspace-only, per the L8/M3
  precedent — not mirrored anywhere.

**Gate B — the client.** Commit `733f4e0` in `LoadCoach`
(`feat(evidence): FreeWeightClient negotiates FreeWeight's API version (ADR-0013)`):
- `infrastructure/freeweight_client.py` — `VersionInfo` (application version, current/supported API
  majors), `EvidenceSourceIncompatible` (`API_VERSION_UNSUPPORTED`), `SUPPORTED_API_MAJOR = "v1"`,
  `_VERSION_CACHE_SECONDS = 300.0` (PromptCadence's own constant name and default, no new
  configuration key — the kickoff's own constraint), and `FreeWeightClient.version(url)`: goes
  through `check_url` first (a version probe is still an outbound request to a caller-supplied URL,
  ADR-0026 §3), then `GET {origin}/api/v1/version`, cached per origin. 404 → incompatible
  (`reason=no_version_endpoint`); any other ≥400 or a transport failure → unreachable; a served-major
  list excluding `v1` → incompatible naming `supported`/`required`; a negotiation that finds the
  major unsupported is **never cached**, so it is re-checked every call rather than remembered as
  working.
- `services/evidence.py` — `refresh_from_freeweight` calls `client.version(url)` immediately before
  `client.fetch(...)`, inside the same `try`; a new `except EvidenceSourceIncompatible` records
  `status="incompatible"` the same way a refusal is recorded (no `mark_source_unreachable` call —
  an incompatible version is not a staleness claim about the *measurements*, the same distinction
  the existing "refused" branch already draws). `SourceStatus.last_status`'s docstring gained
  `incompatible`.
- `domain/evidence_policy.py` — `EvidenceOverview.status`/`.note` treat `incompatible` as a member
  of the same generic-message group as `refused`/`failed`.
- `cli/commands/evidence.py` — `import_evidence --url` calls `client.version(url)` before
  `client.fetch(...)`; a new `except EvidenceSourceIncompatible` exits 2 (grouped with the other
  "this build cannot use what came back" cases, not with the allowlist's exit 4); the command's
  docstring exit-code list updated.
- `web/routes/evidence.py` — `POST /evidence/import`'s URL branch calls `client.version(url.strip())`
  before `client.fetch(...)`; docstring `Raises` gained `EvidenceSourceIncompatible`.
- `web/app.py` — `_STATUS_BY_CODE["API_VERSION_UNSUPPORTED"] = 422`, grouped with
  `SCHEMA_VERSION_UNSUPPORTED` (a version problem, not a "will not fetch that" 403).
- Tests, `tests/integration/test_evidence_fetch.py`: the file's shared `_transport(handler)` helper
  now answers `GET /api/v1/version` with a default compatible response before delegating to the
  test's own handler — the one change that kept all ~30 pre-existing tests (which predate this row
  and script only the export path) passing once `refresh_from_freeweight` started negotiating a
  version on every call, without touching each handler individually. New tests, direct against
  `FreeWeightClient.version()` and against `refresh_from_freeweight`: a compatible negotiation then
  a fetch; an incompatible major refused with both versions named (nothing reached past `/version`
  — the second handler branch carries `# pragma: no cover - never reached`); a 404 read as
  incompatible, not unreachable; a 500 read as unreachable, not incompatible; a transport failure
  read as unreachable; a malformed or block-less `/version` body read as incompatible; the TTL cache
  (two calls inside the window cost one request, a third after it costs a second, via an injected
  monotonic clock); a refused negotiation never cached (two calls both make a request); and
  `refresh_from_freeweight` recording `status="incompatible"` with existing rows untouched
  (`stale_rows == 0`).
- `tests/integration/test_evidence_api.py`: `test_a_url_import_over_http_goes_through_the_client`'s
  handler updated the same way (branch on `/api/v1/version`); one new test,
  `test_import_refuses_a_freeweight_serving_an_incompatible_major_with_422`, proving the HTTP route
  surfaces 422/`API_VERSION_UNSUPPORTED` end to end.

**Gate C — the release.** Commit `78f8f63` in `LoadCoach` (`chore(release): 1.2.0`):
`CHANGELOG.md` `## [1.2.0]`, `__about__.__version__` bumped, `README.md`'s `Status:` line (`1.2.0`
in the repository, tagged `v1.1.6` — the actual latest local tag; `tests/unit/test_readme_version.py`
guards the first figure), `docs/openapi.json` regenerated twice (once after the docstring edits,
once more after the version bump moved `info.version`) — only the `evidence/import` description and
`info.version` changed; no path moved. **No tag, no push** — the operator's call.

## Exit conditions, answered

1. **Full gate green on a named interpreter, coverage ≥ 85 %.** Python 3.14.4
   (`LoadCoach/.venv/bin/python`). `ruff format --check .` (224 files already formatted),
   `ruff check .` (all checks passed), `mypy src tests` (no issues, 204 source files),
   `lint-imports` (4 contracts kept, 0 broken), `pytest -m "not live and not performance" --cov` —
   **1063 passed, 5 skipped** (PostgreSQL legs, no server on this machine), **18 deselected**
   (`live`/`performance`), coverage **90.81 %** (floor 85 %). `freeweight_client.py`'s own coverage
   under just the three FreeWeightClient test files: 97 %.
2. **A fake FreeWeight serving major `2` is refused with the ADR-0013 code before any evidence is
   read.** `test_an_incompatible_major_is_refused_before_any_evidence_is_read` — the export-path
   handler branch carries `# pragma: no cover - never reached` and the test passes, so it is
   provably never called; `caught.value.code == "API_VERSION_UNSUPPORTED"`,
   `details["supported"] == ["v2"]`, `details["required"] == "v1"`. Proved again end to end at the
   HTTP layer by `test_import_refuses_a_freeweight_serving_an_incompatible_major_with_422` (422,
   same code, same details).
3. **Two fetches inside one TTL make one `/version` request; a third after the TTL makes a second.**
   `test_the_version_cache_is_honoured_within_its_ttl_and_expires_after_it`, an injected monotonic
   clock at `t=0, 10, 400` against a 300-second TTL: two calls at `t=0` and `t=10` make one request;
   the call at `t=400` makes a second.
4. **`graceful-degradation.md` §2.1 has no `untested` LoadCoach cell.** Confirmed: the cell now
   cites the five tests above; `grep -n "behaviour not implemented"` on the file returns nothing.
5. **`cmp` silent for every mirrored file; `git status --short` clean in both repositories.** `cmp`
   silent for `spec.md` and `api.md` in both directions. Both repositories report clean below, after
   this handoff and the roadmap update are committed.

## What this prompt got wrong

- Nothing factual — the reading list and the described gap matched the code exactly on inspection.
  The one thing the kickoff left for this row to decide and record (beyond "the conservative option
  at every judgement call") was *where* in the client the negotiation lives; see "The decision this
  row made" above for why it is not inside `fetch()`, which the kickoff's prose ("transcribe
  PromptCadence's... one `GET /version` per TTL window... checked before the first `fetch`") could
  be read as implying without the ADR-0026 shared-vector conflict in view.
- The harness process died mid-row with both repositories' edits uncommitted but otherwise exactly
  as described above; resuming cost only the time to re-verify `git diff` against the moved `docs`
  `HEAD` before staging, not any rework.

## Left undone

Nothing required by the exit conditions. Noted above as a real but out-of-scope gap: the TTL cache's
production benefit is nil today because every caller builds a short-lived client per operation; a
future row could hold a persistent `FreeWeightClient` across the worker's periodic refresh ticks if
the extra `/version` round trip per tick is ever measured to matter.

## What the operator still has to do

Tag `v1.2.0`, approve the `pypi` release environment, and push both repositories (`docs`,
`LoadCoach`) — nothing here does any of the three, per the standing 2026-09-04 instruction.

## Commits

- `docs` — `2e1b38c` — `docs(loadcoach): FreeWeightClient negotiates FreeWeight's API version (row M2)`
- `LoadCoach` — `f037d50` — `docs(loadcoach): mirror FreeWeight API-version negotiation docs (row M2)`
- `LoadCoach` — `733f4e0` — `feat(evidence): FreeWeightClient negotiates FreeWeight's API version (ADR-0013)`
- `LoadCoach` — `78f8f63` — `chore(release): 1.2.0`
- `docs` — this handoff plus the `outstanding-work.md` row-M2 update, committed together next.

Neither repository was pushed, tagged or published, per the standing instruction. Rows M1 and M3
ran in the same window in the same `docs` checkout; this row's commits touched only
`apps/loadcoach/{api,spec}.md`, `architecture/graceful-degradation.md`, this handoff and the
roadmap file — never `git add -A`, and every commit here named its files explicitly.
