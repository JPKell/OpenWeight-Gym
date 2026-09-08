# M1 handoff — IdeaPress's `research` stage runs its tools under ToolYard

**Row:** M1 of [outstanding work §1](../roadmap/outstanding-work.md) — ToolYard's second consumer,
the date the 2026-09-07 interview attached to keeping ToolYard a package.
**Run:** overnight and unattended, 2026-09-08, on the operator's 2026-09-07 override of the row's
"never overnight" schedule note.
**Ships:** `ideapress 1.4.0`, release commit prepared (`c145dbe`), **untagged and unpushed**,
carrying row M3's `[Unreleased]` removal.
**Kickoff:** [`m1-ideapress-research-toolyard.prompt.md`](m1-ideapress-research-toolyard.prompt.md).

---

## 1. Gate results — interpreter and invocation named (M5C-13)

Interpreter: **Python 3.13.15**, `/home/jpk/ai/suite/IdeaPress/.venv/bin/python` → `/usr/bin/python3.13`.
Invocation, from `/home/jpk/ai/suite/IdeaPress`, at the release commit:

```text
$ .venv/bin/ruff format --check .   204 files already formatted
$ .venv/bin/ruff check .            All checks passed!
$ .venv/bin/mypy src tests          Success: no issues found in 199 source files
$ .venv/bin/lint-imports            Contracts: 4 kept, 0 broken.
$ .venv/bin/python -m pytest -m "not live and not performance" -q
                                    1221 passed, 6 skipped, 30 deselected in 34.45s
$ .venv/bin/python -m pytest --cov --cov-report=term
                                    Required test coverage of 85.0% reached. Total coverage: 89.15%
```

Coverage of what this row added:

```text
src/ideapress/domain/research.py            27 stmts   0 missed   100%
src/ideapress/infrastructure/tool_calls.py  15 stmts   0 missed   100%
src/ideapress/services/research.py          91 stmts   0 missed    99%   (one partial branch)
src/ideapress/services/research_tools.py    28 stmts   0 missed   100%
```

**The lock, proved in a clean venv** (`/usr/bin/python3.13 -m venv`, nothing else installed):

```text
$ pip install --require-hashes -r requirements/ci.lock
$ pip install . --no-deps
$ python -c "from ideapress.__about__ import __version__; import toolyard; ..."
  ideapress 1.4.0 | toolyard 0.1.1
$ python -m ruff format --check . && python -m ruff check . && python -m mypy src tests
  204 files already formatted / All checks passed! / Success: no issues found in 199 source files
$ lint-imports        Contracts: 4 kept, 0 broken.
$ python -m pytest -q -m "not live and not performance"
  1218 passed, 6 skipped, 30 deselected in 35.16s
```

(The clean-venv run predates the last three tests by minutes; the in-repo count above is the
final one.)

`requirements/ci.lock` was recompiled with **pip-tools 7.6.1 on `/usr/bin/python3.13`** in a
throwaway venv (the IdeaPress venv has no pip-tools and was not given one):

```text
pip-compile --extra=dev --extra=postgres --generate-hashes --no-emit-index-url \
  --output-file=requirements/ci.lock --pip-args='--no-cache-dir' --strip-extras \
  -P toolyard pyproject.toml
```

The diff is **additions only** — `toolyard 0.1.1`, `jsonschema 4.26.0`,
`jsonschema-specifications 2025.9.1`, `referencing 0.37.0`, `rpds-py 2026.6.3`, `attrs 26.1.0` —
no existing pin moved. The header line is byte-identical to the previous one (pip-tools writes
`--no-index` itself when `--no-emit-index-url` is given; passing it was not needed and it is not
in the invocation above).

## 2. Commits

```text
docs (/home/jpk/ai/suite/docs)
7af3ff4  docs(ideapress): the research stage runs under ToolYard (ADR-0116, row M1)
f6b65b6 docs(roadmap): mark row M1 done, add its handoff

IdeaPress (/home/jpk/ai/suite/IdeaPress)
b2a7b2c  feat(research): tool_call_records, ToolYard's record shape in IdeaPress's own table
7d40c9e  feat(research): the research stage, its plant and its notes (ADR-0116)
c9994f2  feat(web,cli): the unit view shows research notes and every refused call
e595a89  test(research): the stage registry entry, its plan exemption, and the shipped resolver
c145dbe  chore(release): 1.4.0
```

Nothing pushed, nothing tagged, nothing published. The `docs` repository was shared with row M2
tonight: only the files named in each commit were staged, never `git add -A`, and M2's three
files (`apps/loadcoach/api.md`, `apps/loadcoach/spec.md`, `architecture/graceful-degradation.md`)
were already committed by M2 as `2e1b38c` before this row's first commit — they were neither
staged nor touched here. M2's own handoff commit (`90e38ab`) landed between this row's two `docs`
commits, which is what the shared-repository rule is for; no rebase or retry was needed.

## 3. What was built, gate by gate

**Gate A — docs first.** `docs/adr/0116-research-runs-under-toolyard-and-fetches-only-a-named-host.md`;
`apps/ideapress/workflows.md` (§2 row 2's inputs, the "no research backend ships" paragraph
replaced by the backend it promised, and §7's note that "relevant research notes" is finally
reachable); `apps/ideapress/spec.md` (§5 suite dependencies, §10 data ownership, §12's `[research]`
block, §13's behavioural rule that a refused call is not an error code, §21's future-extension line
struck through); `apps/ideapress/data-model.md` (the `sources` table's real role, the
`attempts.outcome` vocabulary, the new `tool_call_records` table);
`apps/ideapress/development-plan.md` (Phase 11); `adr/README.md`'s index paragraph. Mirrored into
`IdeaPress/docs/apps/ideapress/`; `cmp` silent for all six.

**Gate B — the store and the migration.** Migration `0010` creates `tool_call_records`
(`project_id` and `attempt_id` foreign keys, both `ON DELETE CASCADE`, plus every field
`toolyard.ToolCallRecord` produces). `infrastructure/tool_calls.py` holds the application's
`ToolCallStore` — `CollectingToolCallStore` collects during `execute()` and `tool_call_row` maps a
record onto a row. `record_attempt` gained two keyword-only optionals (`project_id`, `tool_calls`)
so the rows are written **inside the transaction the attempt commits in**; its other nine call
sites are untouched and a caller that passes records without a project id gets a `ValueError`.
`check_parity` over `Base.metadata` is `matches=True`.

**Gate C — the plant.** `services/research_tools.py`: one `ToolRegistry`, one
`toolyard.PathContainment`, one `ToolExecutor` per stage run, with the resolver and the httpx
transport injected. `read_file` always registered; `http_fetch` only when `[research] allowed_hosts`
names a host. `services/research_tools.resolve_host` is the one `socket.getaddrinfo` line ToolYard
cannot own (its own `.importlinter` forbids `socket` forever).

**Gate D — the stage.** `domain/research.py` decides the targets, purely. `services/research.py`
is the body: egress verdict → call → attempt+record in one transaction → note only on success.
Registered in `STAGE_BODIES`, and the one stage `start_stage` does not require a plan for.
`assemble_context` receives `research_notes` on the draft and repair path;
`review_loop.py`'s K3 comment is updated to say the notes are now *withheld by choice* rather than
absent.

**Gate E — the surface.** `unit_reports.research_report` feeds a new **Research** section on the
unit page (notes with citations and digests; every tool call with status, reason and detail) and a
`RESEARCH` block under `ideapress unit show --provenance`. No new route, no new JS,
`docs/openapi.json` unchanged but for the version field.

**Gate F — the demonstration and the release.** §5 below; then `1.4.0`.

## 4. Every decision taken unattended, with what the other option would have claimed

**D1 — Containment is `PathContainment`, not the `TieredSandbox` the kickoff named.**
Neither registered tool declares `requires_isolation`; `TieredSandbox` would probe the host by
launching a canary at startup and would put a subprocess launcher inside an application with
nothing to run in one. *The other option would have claimed:* the kickoff and the row both say
"`TieredSandbox` per stage runner", and using it keeps the two consumers' shapes identical. Taken
the conservative way — the smaller surface — and if a tool needing isolation is ever registered,
`PathContainment` reports `UNAVAILABLE` and the executor refuses it rather than running it
unisolated, which is ADR-0018's rule upheld by construction. Recorded as ADR-0116 decision 2.

**D2 — An empty `allowed_hosts` means `http_fetch` is not registered, not "loopback only".**
`toolyard.http_fetch_tool([])` falls back to `LOOPBACK_HOSTS`. Passing the empty configured list
through would have given a fresh installation the ability to fetch from whatever else is listening
on the user's machine, on the strength of a URL in a brief. *The other option would have claimed:*
it is the package's own documented default and needs no branch. Refused: this is the application
that holds the user's private drafts, and ADR-0026 exists for exactly that confused-deputy shape.
A URL on an unconfigured installation is a recorded `REFUSED` / `unknown_tool`, which is literally
true and visible.

**D3 — A research note is a `sources` row, not a new table.** `sources` has had two readers
(`fact_check`'s `_project_sources`, `export`'s grounding count) and **no writer** since P1, and its
own docstring says "a file, a note, or (opt-in) a URL". *The other option would have claimed:* a
dedicated `research_notes` table with a first-class citation column and no overloading. Refused
because it would leave `fact_check` needing to union two evidence sets, or leave `sources`
permanently empty beside the table actually used. Recorded as ADR-0116 decision 5, with the
downstream consequences named in `CHANGELOG.md` and `docs/upgrading.md`.

**D4 — `read_file`'s root is `<project directory>/sources/`, not the project directory.** Exports
are written into the project directory itself. *The other option would have claimed:* the project
directory is "the project's own workspace root", which is what the kickoff says. Refused: a
research stage that could ingest its own exports would build notes out of the document it is
researching for. A `read_file` naming an export is now refused `path_escape`, and there is a test.

**D5 — The egress decision's `source_ref` is the invocation id, not the attempt id.** ADR-0073
makes "before any request is built" the guarantee, and the attempt row does not exist then.
*The other option would have claimed:* row J1's funnel already joins decisions to attempts by
`source_ref`, so this is an inconsistency. Taken anyway, because minting the attempt first purely
to have an id would mean deciding after the row that describes the call — the exact reversal
ADR-0073 was written about. `tool_call_records.invocation_id` is the join, and the demonstration
below shows it working as a SQL join.

**D6 — A denied verdict is enforced by the invocation's `max_egress`, not by skipping the call.**
An approved decision passes `EgressClass.NETWORK`; a denied one leaves the ceiling closed and
ToolYard refuses the fetch with `egress_not_permitted` through the ordinary recorded path.
*The other option would have claimed:* not calling the executor at all is obviously safer. Refused
because it would produce no `tool_call_records` row, and the kickoff's exit condition 2 requires
the denial to be visible **as a result**. One argument, one enforcement point, two audit rows.

**D7 — A remote fetch host with no declared ceiling is denied (fail closed).** `[research]
max_data_classification` unset ⇒ `EgressTarget.max_data_classification = None` ⇒ Commissioner's
shipped policy denies with `no_ceiling_declared`. *The other option would have claimed:* defaulting
to `public` would let an operator who named a host actually fetch from it without a second key.
Refused: ADR-0103 decision 2 made exactly this choice for the backend target, and a research fetch
is not a weaker case. It is called out in `upgrading.md` because it is the one thing that will
surprise someone who names a host and gets nothing.

**D8 — `attempts.outcome` gains `refused`.** *The other option would have claimed:* reuse
`provider_error`, changing no vocabulary. Refused: `provider_error` on a call that never reached a
provider is a false provenance record in the application whose whole thesis is truthful
provenance. One word in `data-model.md`, one in the docstring, no enum to migrate (the column has
never been constrained).

**D9 — `research` is the one stage `start_stage` does not require a plan for.** Workflows §2 puts
it at position 2 and the plan at position 4. *The other option would have claimed:* a separate
`start_research` beside `start_plan`, leaving `start_stage` untouched. Refused as the larger
change: `ideapress stage run <project> research` is the verb an operator already knows, and the
exemption is one condition with a comment. A test asserts every other stage still refuses.

**D10 — No web route for starting the stage.** *The other option would have claimed:* the UI can
run every other stage, so this is a gap. Left undone deliberately: the kickoff's Gate E asks only
that the unit view *shows* notes and refusals, `docs/openapi.json` is snapshot-guarded, and adding
a route that starts a network-touching stage is the largest surface this row could have added
unattended. Noted in §8 as work for whoever wants it.

**D11 — The `httpx` import-boundary test was amended rather than the annotation weakened.**
`tests/unit/test_import_boundaries.py` forbade `httpx` outside `infrastructure/backends` by an AST
scan that did not distinguish a `TYPE_CHECKING` import. The research plant takes an injected
`httpx.BaseTransport` it never constructs. *The other option would have claimed:* typing it as
`Any` or `object` keeps the test untouched. Refused — a bare `Any` at a public boundary is against
the house rules, and the guard's real property (nothing outside the adapters can *execute* an
httpx import) is unchanged. The test now scans runtime imports, and a **second** test pins the
exemption to exactly the two modules that use it, so a third is a failure rather than a precedent.

**D12 — Re-running the stage replaces the project's notes.** *The other option would have claimed:*
appending preserves history. Refused: two runs of the same brief would give one source twice the
weight in the context budget. Tool-call records are never deleted, so the audit trail still shows
both runs. Tested.

**D13 — `spec.md` §5's suite dependency list was corrected while adding `toolyard`.** It named five
packages and had been stale since row J1 added three. *The other option would have claimed:* touch
only what this row adds. Refused: adding a sixth name to a list of five that is already wrong
writes a new false sentence. `pydantic-settings` in the same section's third-party list is still
stale (ADR-0114 removed it); left alone and reported in §8.

**D14 — Gold-standards §1.1 was not edited.** The kickoff says adding `toolyard` is "an
enumerated-set change — update `tests/unit/test_packaging.py` and gold-standards §1.1's set". It
is not: §1.1's preamble says suite packages are unbudgeted and its table enumerates **non-suite**
names only, and `tests/unit/test_packaging.py` already lists `toolyard` in `SUITE_PACKAGES`. Both
were left unchanged and both still pass. ADR-0116 says so explicitly, since declaring a suite
package is still an architectural decision even when it spends no budget. See §7.

## 5. Exit conditions, answered with pasted evidence

The demonstration ran a **real loopback origin** (`python -m http.server` equivalent on
`127.0.0.1:8791`), a real config file, and the shipped `ideapress` CLI against a fresh data
directory — not the test suite. Scripts:
`scratchpad/m1_exit_demo.sh` and `m1_exit_demo3.sh` (scratch only; nothing under the repositories).

### 1. A project whose brief names a URL produces notes from it, with the call recorded

Brief: *"Background reading: `http://127.0.0.1:8791/paper.txt` and also
`https://blocked.example/x` — read both."* Configuration: `allowed_hosts = ["127.0.0.1"]`,
`max_data_classification = "public"`. A local file was dropped in the project's `sources/`
directory and an export was placed **beside** it in the project directory.

```text
$ ideapress stage run 01M210HH9CZVY0A6F8MDEA16VK research
task 01M210HHS7DFWF5R7CZWJMT4R4
  [  1] stage.started: research started
  [  2] research.note_written: http://127.0.0.1:8791/paper.txt: 151 characters
  [  3] research.call_refused: https://blocked.example/x: refused — host_not_allowed
  [  4] research.note_written: field-notes.md: 49 characters
  [  5] research.completed: 2 note(s) written, 1 call(s) refused or failed
  [  6] stage.completed: completed

-- sources (the notes, with their citations) --
  url     151 chars  sha256:33affe035691a633…  cites http://127.0.0.1:8791/paper.txt
        metadata {"invocation_id": "01M210HHSFAPQWTYFA0V45AGY3", "retrieved_at": "...", "tool": "http_fetch"}
  file     49 chars  sha256:d107fe8978812ada…  cites field-notes.md
        metadata {"invocation_id": "01M210HHSPKG3396TG76W68ZNC", "retrieved_at": "...", "tool": "read_file"}

-- tool_call_records (every call, refused ones included) --
  http_fetch  ok       —                      egress=network    1 ms  inv=01M210HHSFAPQWTYFA0V45AGY3
  http_fetch  refused  host_not_allowed       egress=network    0 ms  inv=01M210HHSNRPEHCZWXD7HT22N5
        'blocked.example' is not a host this tool may fetch from
  read_file   ok       —                      egress=none       0 ms  inv=01M210HHSPKG3396TG76W68ZNC

-- attempts (the provenance rows the tool calls hang off) --
  research  #1  completed      error_code=—                 unit_id=NULL
  research  #2  refused        error_code=host_not_allowed  unit_id=NULL
  research  #3  completed      error_code=—                 unit_id=NULL
```

The export beside `sources/` was never read — there is no fourth call, because it is not a target,
and a `read_file` naming it explicitly is refused `path_escape` (`test_a_path_outside_the_sources
_directory_is_refused`).

### 2. A disallowed host is refused as a result, visible on the unit, with an `egress_decisions` row and no exception

Two shapes were demonstrated, because "disallowed" has two independent gates.

**Host outside the tool's allowlist** — from the run above:

```text
-- egress_decisions (rendered before each fetch) --
  approved  research:127.0.0.1           run=project:01M210HH9CZVY0A6F8MDEA16VK
        reason=target_not_remote     source_ref=01M210HHSFAPQWTYFA0V45AGY3
  approved  research:blocked.example     run=project:01M210HH9CZVY0A6F8MDEA16VK
        reason=within_ceiling        source_ref=01M210HHSNRPEHCZWXD7HT22N5

-- the join: decision.source_ref == tool_call_records.invocation_id --
  approved  research:127.0.0.1           -> http_fetch ok      / —
  approved  research:blocked.example     -> http_fetch refused / host_not_allowed
```

The stage completed (`stage.completed: completed`); nothing raised.

**Egress denied by the classification policy** — `allowed_hosts = ["docs.example"]` with
`max_data_classification` deliberately unset:

```text
$ ideapress stage run <project> research
  [  1] stage.started: research started
  [  2] research.egress_denied: https://docs.example/paper: egress denied — no_ceiling_declared
  [  3] research.call_refused: https://docs.example/paper: refused — egress_not_permitted
  [  4] research.completed: 0 note(s) written, 1 call(s) refused or failed
  [  5] stage.completed: completed

-- egress_decisions --
  denied   research:docs.example    reason=no_ceiling_declared  ceiling=None
-- tool_call_records --
  http_fetch  refused  egress_not_permitted   egress_declared=network
        the tool reaches the network and this invocation does not permit egress
-- attempts --
  research refused egress_not_permitted
-- sources --
   0
```

No request was built: ToolYard's egress rung fires before the handler is entered, so nothing was
resolved and nothing was connected to.

**Visible on the unit** — `tests/integration/test_research_surface.py`:

```text
test_the_unit_detail_carries_the_notes_and_every_call
    [("http_fetch", "ok", None), ("http_fetch", "refused", "host_not_allowed")]
test_the_unit_page_shows_the_note_and_the_refusal
    "<h3>Research</h3>" in page; "host_not_allowed" in page; no <script> in the section
test_the_cli_provenance_view_prints_the_notes_and_the_calls
    "RESEARCH" / "https://docs.example/paper" / "host_not_allowed" in the printed provenance
```

### 3. A brief with no URL, or an installation with no allowed host, runs the workflow exactly as 1.3 did

**No URL and no files:** `test_a_brief_with_no_url_and_no_files_completes_and_writes_nothing` —
no `sources` row, no `tool_call_records` row, no `attempts` row, `project_notes()` empty, run
`completed`.

**No allowed host, on the real CLI:**

```text
$ sed -i 's/^allowed_hosts = .*/allowed_hosts = []/' ideapress.toml
$ ideapress stage run <project2> research
  [  2] research.call_refused: http://127.0.0.1:8791/paper.txt: refused — unknown_tool
  [  3] research.completed: 0 note(s) written, 1 call(s) refused or failed
-- tool_call_records for the unconfigured project --
  http_fetch  refused  unknown_tool
-- sources for the unconfigured project --
   0
```

**The existing journey, unchanged:** the whole suite passes at the release commit — 1221 passed,
6 skipped — including `tests/e2e/*`, `tests/integration/test_draft_to_commit.py`,
`test_backend_parity.py`, `test_review_loop.py` and the two golden files
(`tests/unit/test_context_assembly_golden.py`, `tests/unit/test_config_1_0_compatibility.py`).
The 1.0-configuration golden was **extended, not rewritten**: `ADDED_IN_M1_SECTIONS = {"research"}`
is removed from the dump before comparison, exactly as rows J1 and K3 did, and a second assertion
proves the new section defaults to no behaviour (`allowed_hosts == ()`,
`max_data_classification is None`).

### 4. Full gate green on a named interpreter; coverage ≥ 85 %; lock proved in a clean venv

§1. Python 3.13.15; 89.15 %; the lock installed with `--require-hashes` into an empty venv and the
whole gate re-run there.

### 5. `cmp` silent for every mirrored file; `git status --short` clean in both repositories; the release commit exists, untagged, unpushed

```text
$ for f in spec.md workflows.md development-plan.md data-model.md api.md risks.md; do
    cmp -s docs/apps/ideapress/$f IdeaPress/docs/apps/ideapress/$f && echo "cmp silent: $f"; done
cmp silent: spec.md
cmp silent: workflows.md
cmp silent: development-plan.md
cmp silent: data-model.md
cmp silent: api.md
cmp silent: risks.md
```

`IdeaPress/docs/README.md` was not touched. `git status --short` is empty in IdeaPress; in `docs`
it is empty for this row's files.

## 6. What the operator still has to do

1. **Review and tag** `v1.4.0` on IdeaPress `c145dbe`.
2. **Push** `docs` (`7af3ff4` plus the roadmap commit) and IdeaPress (five commits from `b2a7b2c`
   through `c145dbe`), in that order — the ADR is referenced by the code's docstrings.
3. **Approve the `pypi` environment** for the IdeaPress release workflow when the tag goes up.
4. **Enable nothing else.** The `research` stage does nothing until someone names a host and runs
   it; there is no flag to flip, no daemon, no schedule.

One judgement worth the operator's eye before the tag: **D7**, the fail-closed denial of a remote
host with no `[research] max_data_classification`. It is right by ADR-0103's precedent and it will
be the first thing a new user hits — they name a host, run the stage, and get a denial. It is
called out in `docs/upgrading.md` with the two-line configuration that fixes it.

## 7. What this prompt said that turned out not to be true

1. **"`TieredSandbox` per stage runner."** Neither shipped tool runs a subprocess, so the
   sandbox's whole purpose — the isolation ladder — has no consumer here. Taken as
   `PathContainment` (D1, ADR-0116 decision 2).
2. **"adding `toolyard` to IdeaPress's runtime set is an enumerated-set change — update
   `tests/unit/test_packaging.py` and gold-standards §1.1's set."** It is not. Gold-standards §1.1
   says in its own preamble that suite packages are unbudgeted, its table enumerates non-suite
   names only, and `test_packaging.py` already had `toolyard` in `SUITE_PACKAGES`. Neither file
   needed a line; both still pass. ADR-0116 records the declaration anyway (D14).
3. **"Latest IdeaPress migration is `0009_attempt_cache_token_classes.py`" — true**, and `0010` was
   free. **"Migration `0010`. Migrations run with SQLite foreign keys off (row H2's finding) — copy
   an existing migration's shape."** The FK-off shape was not needed: `0010` only *creates* a
   table, so SQLite's batch mode never rewrites an existing one. `0007` and `0008` (the two other
   create-table migrations) do nothing special either, and this one is their shape. WeightsDB does
   enable SQLite foreign keys per connection at runtime, which is what makes the cascade test in
   `test_tool_call_records.py` meaningful rather than declarative.
4. **"`read_file` reads from the project's own workspace root."** There is no such thing as a
   project "workspace root" in IdeaPress; there is an artifact directory, and exports are written
   into it. The read root became `<project directory>/sources/` (D4).
5. **"allowed hosts (default: empty — no host, so a fresh install fetches nothing)."** True as an
   intent, but *not* what an empty list means to ToolYard, which reads it as loopback-only. The
   application has to not register the tool to get the stated behaviour (D2).
6. **"Every refusal is a `ToolResult` on the unit's provenance table."** A research call has no
   unit — the stage runs at workflows §2 position 2, before the plan at position 4 — so a research
   attempt has `unit_id NULL` and the records are project-scoped. They are shown on the unit page
   anyway, which is what the exit condition actually needs.
7. **"`docs/openapi.json` … regenerate if a route moves."** No route moved, and it still needed
   regenerating: the snapshot carries `info.version`, so every release commit regenerates it.
8. **The reading list's ADR-0050 is about *mountable* tables** (LoadLedger, Commissioner) and
   ToolYard ships none — it owns no data at all. The shape borrowed was PromptCadence's
   `CollectingToolCallStore`, which the kickoff also named; ADR-0050 supplied the principle
   (a package defines the shape, the application owns the table) and nothing else.

## 8. Findings that belong to another row

**None require a ToolYard change**, and `py/ToolYard`, `py/Commissioner` and `PromptCadence` were
not edited. What was found:

1. **ToolYard: an empty `allowed_hosts` cannot express "no host".** `http_fetch_tool([])` means
   loopback-only, and both consumers now have to work around it — PromptCadence by withholding the
   tool from the registry (row E4 decision 1), IdeaPress by not registering it (D2). Two consumers
   with the same workaround is the usual signal. A `ToolYard` row could give
   `http_fetch_tool` an explicit way to be constructed closed, or document the loopback fallback as
   the deliberate reading it is. **Recorded in ADR-0116's "Revisit when".** Not urgent: the
   workaround is three lines and is tested in both repositories.
2. **`architecture/master-architecture.md` §2's dependency graph is stale for IdeaPress.** It reads
   `IP --> MR & WD & MW & SS`; IdeaPress has depended on `cutctx`, `loadledger` and `commissioner`
   since rows J1/J2 and now on `toolyard`. `architecture/executive-summary.md` line 94 has the
   J1/J2 set and is also now short by `toolyard`. Not edited here: master-architecture is frozen
   and amended only through records that declare what they extend, and this row's record
   (ADR-0116) declares the dependency. A documentation row should reconcile both diagrams for all
   four applications at once rather than one arrow at a time.
3. **`apps/ideapress/spec.md` §5's third-party list still names `pydantic-settings`**, which
   ADR-0114 decision 4 removed from every application's `dependencies` because none imports it.
   Left alone (D13) — it is a one-word deletion in four specs and belongs with finding 2.
4. **`services/project_review.py`'s unbudgeted whole-document prompt** is still open — row J2's
   finding, confirmed unchanged, and untouched here.
5. **The unit page does not render the per-attempt egress decision** that `unit_detail` has carried
   since row J1 (`attempts[].egress`). The API returns it; the template's Provenance table has no
   column for it. Noticed while adding the Research section; deliberately not fixed, because it is
   another row's surface and this row's brief was the research half.
6. **`ideapress research` has no web route** (D10). If the UI should be able to start the stage,
   that is a route, a CSRF-protected form, an OpenAPI snapshot regeneration and a decision about
   whether a browser click may cause a network fetch — a small row of its own.

## 9. Stop rules — observed

* Nothing pushed, tagged or published.
* `py/ToolYard`, `py/Commissioner` and `PromptCadence` untouched (`git status --short` clean in all
  three; they were only read).
* `IdeaPress/docs/README.md` untouched.
* In `docs`, every commit staged files by name; `git add -A` was never run; M2's three files were
  never staged, reverted or edited.
* Every temporary file — the demonstration scripts, the loopback origin's document, the throwaway
  pip-tools and lock-proving venvs — lives under the session scratchpad. Nothing at the workspace
  root was created or overwritten. The loopback server was killed on exit (`trap`).
* No Monitor, no background wait: every command ran in the foreground.
