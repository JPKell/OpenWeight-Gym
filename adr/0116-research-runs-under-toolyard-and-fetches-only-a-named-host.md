# ADR-0116 — IdeaPress's `research` stage runs under ToolYard, and fetches only a host the operator named

**Status:** Accepted (2026-09-08)
**Extends:** [ADR-0053](0053-a-refused-tool-call-is-a-result-not-an-exception.md) (a refused tool
call is a result), [ADR-0073](0073-egress-is-decided-on-configuration-before-availability.md)
(egress is decided on configuration, before the work), [ADR-0103](0103-ideapress-reacts-to-a-verdict-it-does-not-own.md)
(IdeaPress records the verdict and enforces it itself; a remote target with no declared ceiling is
denied), [ADR-0114](0114-the-dependency-budget-is-the-enumerated-set-a-component-declares.md) (a
declared dependency is an enumerated-set decision).
**Relates to:** [ADR-0026 §3](0026-local-http-hardening.md) (the checks a body-supplied URL passes),
[ADR-0043](0043-grounding-is-verified-not-assumed.md) (`fact_check` needs something to check
against), [ADR-0050](0050-a-package-may-ship-tables-never-a-migration-history.md) (a package ships
a record shape; the application owns the table),
[ADR-0104](0104-an-adopted-reductions-seam-and-error-vocabulary-survive-it.md) (the
`assemble_context` seam whose `research_notes` input this record finally supplies),
[ADR-0111](0111-the-container-rung-is-proved-on-docker-and-podman-is-not-an-exit-condition.md)
(the isolation ladder's proven rungs).
**Source:** Row M1 of [outstanding work §1](../roadmap/outstanding-work.md) — ToolYard's second
consumer, the date the 2026-09-07 interview attached to keeping ToolYard a package.

## Context

[Workflows §2](../apps/ideapress/workflows.md) row 2 has specified a `research` stage since M6 —
*"Brief, sources → source notes with citations; every note cites an available source; Optional"* —
and no build has ever implemented it. The same section says why: *"No research backend ships at 1.0
… The ADR that adds a research backend decides its binding then."* [Spec §21](../apps/ideapress/spec.md)
lists research backends (local document ingestion; opt-in web search) as a future extension. This
record is that ADR.

Three facts about the ground make the decision narrower than it looks.

**The stage reaches no model.** Workflows §2 counts `research` as the fifth of the five no-model
stages, and `research_synthesis` (stage 3) is the model stage that reads its output. So there is no
prompt, no binding, no agent loop and no per-turn tool selection to design: Python decides which
calls to make from what the project already contains.

**The table a note belongs in already exists and nothing writes to it.** `sources` (migration
`0001`) carries `kind`, `title`, `path`, `sha256`, `content_text` and `metadata_json`, and is read
in exactly two places — `services/review_loop.py::_project_sources`, which feeds `fact_check` the
documents it checks claims against, and `services/export.py`, which reports whether anything existed
to check against at all. Its own docstring says *"a file, a note, or (opt-in) a URL"*, and
`_project_sources`'s comment already describes the row this stage produces: *"an opt-in URL never
fetched"*. `sources` has had a reader and no writer since P1; `research` is the writer.

**The seam that consumes notes exists and is dead.** `domain.context_assembly.assemble_context()`
takes `research_notes`, ranks them by explicit reference, and drops them first under
`REDUCTION_ORDER` — and row J2 confirmed (`J2_HANDOFF.md` §8) that no running stage has ever passed
one. The reduction order and its budget tests were built against input that never arrived.

Against that, the reason this is not a small feature: a research stage fetches, and a fetch from an
application holding the user's private drafts is the suite's most dangerous surface. Row M1 exists
because the 2026-09-07 interview kept ToolYard a package on the condition that a second consumer
prove the discipline transfers — the validate → authorize → execute → record order, path
containment, structured refusals — rather than being re-derived, differently, in a second
application. IdeaPress writing its own `httpx` fetch loop would be exactly the duplication ToolYard
was extracted to prevent, in the one place a duplicate is a security control.

## Decision

**IdeaPress's `research` stage executes `read_file` and `http_fetch` through a `toolyard.ToolExecutor`,
under an allowlist that a fresh installation leaves closed. `toolyard` joins IdeaPress's declared
dependency set.**

### 1. The binding is ToolYard's executor, and nothing else

The stage builds one registry and one executor per stage run and issues one `ToolCallRequest` per
discovered target. Every refusal, failure and timeout is a `toolyard.ToolResult` (ADR-0053), never
an exception the stage swallows, and every call — refused calls included — becomes a row in
IdeaPress's own `tool_call_records` table through an application-supplied `ToolCallStore`. ToolYard
ships the record shape and owns no data; the table, the migration and the retention are IdeaPress's,
which is ADR-0050's rule applied to the one package that ships no table at all.

`toolyard>=0.1.1,<0.2` is declared in `pyproject.toml`, the same range PromptCadence pins. Under
ADR-0114 a suite package is unbudgeted, so gold-standards §1.1's enumerated **non-suite** set is
unchanged and `tests/unit/test_packaging.py` needs no edit — `toolyard` is already in its
`SUITE_PACKAGES` set. Declaring a suite package is still an architectural decision, and this record
is it. `toolyard` brings `jsonschema` transitively; nothing in IdeaPress imports it.

### 2. Containment is `PathContainment`, not `TieredSandbox`

Neither registered tool declares `requires_isolation` — `read_file` and `http_fetch` run no
subprocess — so the executor's containment port needs to answer path resolution and nothing else.
`toolyard.PathContainment` is that answer: resolution-then-check against the roots, ancestry rather
than string prefix, and `IsolationTier.UNAVAILABLE` reported honestly. A `TieredSandbox` would probe
the host by launching a canary at startup, and would put a subprocess launcher inside an application
that has no tool to run in one. Should IdeaPress ever register a tool that needs isolation, the
executor refuses it with `isolation_unavailable` rather than running it unisolated — ADR-0018's rule,
which `PathContainment` upholds by construction.

### 3. The allowlist is configuration, and it defaults to fetching nothing

A new `[research]` block carries `allowed_tools` (default: both), `allowed_hosts` (default:
**empty**), `max_fetch_bytes`, `max_file_bytes`, `timeout_seconds` and an optional
`max_data_classification`.

`allowed_hosts` empty means **`http_fetch` is not registered at all**. This is deliberately *not*
ToolYard's own reading of an empty host list — `toolyard.http_fetch_tool([])` falls back to loopback
only, which is a sane default for a package but the wrong one for an application whose fresh install
must reach nothing. A brief naming a URL on an unconfigured installation therefore produces a
recorded `REFUSED` / `unknown_tool` result and a stage event naming the missing configuration, not a
loopback fetch and not silence. Two independent facts keep an unconfigured installation off the
network: the tool is not in the registry, and it is not in the executor's allowlist.

### 4. The stage decides its calls from the project, never from a model

Two triggers, both deterministic:

* **Absolute `http(s)://` URLs appearing verbatim in the brief**, one `http_fetch` each, in the
  order they appear, de-duplicated. Nothing rewrites, completes or infers a URL; a relative
  reference, a bare hostname and a `file:` scheme are not URLs for this purpose.
* **Regular files directly inside `<project artifact directory>/sources/`**, one `read_file` each,
  in sorted order. That subdirectory — not the project directory itself — is the invocation's only
  root, so an export written into the project directory is outside containment and a `read_file`
  naming one is refused with `path_escape`. The directory is the operator's drop box; nothing in
  IdeaPress writes to it.

There is no recursion, no link following inside a fetched document, and no second round: one pass,
one call per target.

### 5. A note is a `sources` row, with its citation

A successful call writes one `sources` row: `kind` (`url` or `file`), `title` (the URL, or the
file's name), `path` (the URL or the resolved path — the citation workflows §2's gate demands),
`sha256` of the retrieved text, `content_text`, and `metadata_json` carrying the invocation id and
the fetch instant. A call that did not succeed writes **no** row: workflows §2's gate is "every note
cites an available source", and a note whose source was refused cites nothing.

Two existing behaviours therefore begin to fire for projects that run this stage, and both are the
intended consequence rather than a side effect: `fact_check` (stage 10) gains documents to check
claims against (ADR-0043), and `assemble_context` receives `research_notes` for the first time,
which reopens `REDUCTION_ORDER[0]` in production. The revision path stays deliberately narrow — row
K3's decision that `stages.revise.improve` gets no broader context is unchanged.

### 6. Egress is decided per host, before the fetch, and enforced by the ceiling

For each URL, and **before** the executor is entered, `services/egress.py` records a Commissioner
verdict for an `EgressTarget` naming that host. Local (loopback) hosts carry no ceiling and are
approved; a remote host carries `[research] max_data_classification` or, unset, `None` — which the
shipped `OrderedClassificationPolicy` denies with `no_ceiling_declared`. That is ADR-0103 decision 2
transcribed from the backend target to the fetch target, and it is fail-closed for the same reason.

The verdict is enforced by the one lever ToolYard provides: an approved decision sets the
invocation's `max_egress` to `NETWORK`, a denied one leaves it at `NONE`, and ToolYard refuses the
`NETWORK`-declaring tool with `egress_not_permitted` — a structured result, recorded through the
ordinary path. So a denied host produces **both** an `egress_decisions` row and a `tool_call_records`
row, and no exception. Commissioner still records rather than enforces (ADR-0054); the enforcement
is IdeaPress's, in one line, at one place.

The decision's `source_ref` is the **invocation id**, not the attempt id: the decision is rendered
before the fetch and therefore before the attempt row exists, and ADR-0073's whole point is that the
ordering is the guarantee. `tool_call_records.invocation_id` is how the two join.

### 7. The stage stays Optional, and it is never automatic

`research` is startable on its own (`ideapress stage run <project> research`) and is the one stage
that does not require a plan, because workflows §2 places it at position 2 and the plan at position
4. Nothing runs it implicitly. A project that never runs it has no `sources` rows, so
`assemble_context` receives no notes, `fact_check` still finds nothing to check against, and the
workflow is byte-for-byte what 1.3 produced.

## Alternatives considered

**Write the fetch in IdeaPress with `httpx`, which is already a declared dependency.** No new
package, no executor, no registry — perhaps forty lines. Rejected on the row's own premise: ADR-0026
§3's checks (scheme, host allowlist, literal-IP comparison after resolution, re-check on every
redirect hop, size cap enforced during streaming) are exactly the checks a second implementation
gets subtly wrong, and ToolYard exists because LoadCoach's evidence fetch and this one must be the
same checks proven by the same fixture. The forty lines are the cheap part; the vector set is not.

**Register `http_fetch` with ToolYard's loopback default when `allowed_hosts` is empty.** One less
branch, and arguably the package's own intent. Rejected: a fresh IdeaPress install would then be
able to fetch from services on the user's own machine on the strength of a URL in a brief, which is
precisely the confused-deputy shape ADR-0026 exists to close for this application. An operator who
wants loopback writes `allowed_hosts = ["127.0.0.1"]`, and then the reach is a recorded choice.

**Give research notes their own table.** Cleaner on paper — a `research_notes` table with a
first-class citation column, no overloading of `sources`. Rejected: `sources` is already the
project's evidence set, already has the citation columns, is already what `fact_check` reads and
what `export` counts, and has never had a writer. A second table would mean either two evidence
sets that `fact_check` must union, or a `sources` table that stays permanently empty beside the one
that is used. The one-word cost is that `kind` now carries `url` and `file`, which is what the
column was documented for.

**Record the egress decision against the attempt, as `record_attempt` does for a model call.**
Consistent with row J1's funnel, and it would need no new identifier. Rejected: the attempt row does
not exist until after the call, and ADR-0073 makes "before any request is built" the guarantee
rather than an implementation detail. Deciding late and back-dating the join would reproduce exactly
the accident ADR-0073 was written about.

**Make the research stage part of the plan stage, so a project researches then plans in one run.**
Fewer verbs, and it matches workflows §1's pipeline picture. Rejected: it would change what the
existing plan stage does for every project, including ones with nothing to research, and workflows
§2 marks `research` Optional. A stage that is optional and a stage that always runs inside another
one are different stages.

**Skip `read_file` and ship only the fetch.** The row's headline is the web half, and a registered
tool with no caller is dead weight. Rejected because the caller is the row's own specification:
workflows §2's input for stage 2 is *"Brief, **sources**"*, and spec §21's research backends name
*local document ingestion* first. Local ingestion is also the half that needs no network at all,
which makes it the half an operator can use on an installation that fetches nothing.

## Consequences

* IdeaPress declares `toolyard` and is the package's second consumer. The interview's condition on
  keeping ToolYard a package is met by a build rather than by a promise.
* Migration `0010` adds `tool_call_records`. Every research tool call — OK, refused, failed,
  timed out — is a durable row joined to its attempt, and to its egress decision by invocation id.
* A fresh installation's behaviour is unchanged: no `[research]` block, no hosts, no `sources/`
  directory contents, no notes, and a workflow identical to 1.3's.
* An installation that configures a host and runs the stage changes three downstream behaviours at
  once — notes in the draft context, documents for `fact_check`, and `has_sources` true in the
  export's grounding statement. `CHANGELOG.md` and `upgrading.md` name all three.
* The `attempts.outcome` vocabulary gains `refused`, for an attempt whose tool call ToolYard
  declined. `provider_error` would have been the closest existing value and would have described a
  provider that was never contacted.
* IdeaPress now has a directory an operator is invited to put files in. It is inside the project's
  own artifact directory, mode `0700` like the rest of it, and it is the only read root a tool call
  ever sees.

## Revisit when

* **A research backend needs to follow a link, paginate, or fetch more than the brief named.** Every
  one of those makes the target set something other than "what the project already contains", and
  the trigger rule in decision 4 is what would have to change first.
* **A second stage wants tools.** The plant is built per stage run and registers two tools by name;
  a third consumer inside this application is the moment to ask whether it belongs on the runtime
  the way PromptCadence's `ToolPlant` does.
* **ToolYard grows a way to express "no host at all"**, distinct from an empty list meaning
  loopback. Decision 3's not-registered branch exists only because that distinction lives in the
  application today.
