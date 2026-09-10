# W5 Handoff — WeightRoomGym Phase 5: docs viewer

**Row:** W5 of [`roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md) (Sonnet 5 · high;
overnight allowed). **Date:** 2026-09-10. **Kickoff:**
[`w5-weightroom-p5-docs-viewer.prompt.md`](../prompts/w5-weightroom-p5-docs-viewer.prompt.md).
**Ships:** `wr-gym 0.5.0`, **prepared, not tagged, not pushed, not published.** The one flexible
row (any time after W3); this session ran it without W4, which is unbuilt.

## 1. What was built, by commit

| Commit | Gate | What |
|---|---|---|
| `db89b6d` | A | `services/docs.py` (root resolution, resolve-then-check containment, the tree, the mistune renderer with heading ids/outline/mermaid/link-rewriting, the ADR index parser); goldens and the full containment vector set |
| `51e8a7d` | B | Migration `0003` (`docs_index`, FTS5/plain/tsvector by dialect); `services/docs_index.py` (rebuild, search, the labelled LIKE degrade); `wr-gym docs index`; the migration-parity exclusion for FTS5's shadow tables |
| `7d5d0d9` | C | `web/routes/docs.py` (API + UI); four templates inside `_shell.html`; mermaid 11.17.2 vendored and mounted at `/app-static/`, loaded only where a fence exists; the top bar's "Docs" link now real; `CHANGELOG`; `0.5.0` |

Full local gate, `WeightRoom` (Python 3.14.4, `.venv`): `ruff format --check .` (121 files),
`ruff check .` clean, `mypy src tests` clean (115 files, strict), `lint-imports` 5 contracts
kept, `pytest -m "not live and not performance"` **683 passed, 1 skipped** (the PostgreSQL
migration test, no server here), coverage **90.12 %** (floor 85 %); `wr-gym config reference
--check` matches (no new config key this row — `[docs] root` was already in the schema, from W0).

## 2. What this row was asked to decide, and what it decided

### 2.1 Mermaid was not vendored by any earlier row — vendored here

The design brief (spec §5) and Phase 5's own acceptance criteria read as if mermaid is already
available; `WM_HANDOFF.md` §1 confirms MirrorWall 0.3 vendored only htmx, its SSE extension and
JetBrains Mono. Vendored it directly into WeightRoomGym's own tree instead of blocking on a
MirrorWall row: `npm pack mermaid@latest` (11.17.2), the UMD `dist/mermaid.min.js` (3.4 MB, MIT,
digest `581ed7d7…5390eb8`, SHA-256) copied to `web/static/vendor/mermaid/` with its `LICENSE`,
mounted at `/app-static/` via `mount_static`'s `extra_dirs` — a WeightRoomGym-owned static root,
distinct from MirrorWall's, matching design brief §5's "one consumer stays here" rule (mermaid is
a docs-viewer-only need, not shared). Loaded with a plain `<script src=… defer>` — no
content-hashed `asset_url`, since that filter's `root=`/`prefix=` plumbing is built for
MirrorWall's own package assets and re-registering it for a second static root added no real
value for one file that changes only when re-vendored.

### 2.2 The primary table is always database-sourced — this row's boundary decision has a sibling

Not new to this row, but worth restating since it shaped how the docs viewer's primary content
is sourced too: **the docs tree and every rendered page are read straight from the filesystem on
every request**, never cached in the database beyond the search index. `docs_index` exists for
full-text search only; `GET /docs/page` always re-renders from disk. This is the same posture
W3's Overview table took for a different reason (spec §10's "database" read path being general
rather than reserved) — here the reason is simpler: the tree is the source of truth, and spec §15's
40 KB / ≤ 100 ms benchmark holds with margin to spare.

**Profiled same day, post-handoff** (`render_markdown`, 10 runs each, this environment, not the
reference machine):

| Document | Size | Median |
|---|---|---|
| A synthetic document at spec §15's own 40 KB benchmark | 32 KB | 15.8 ms |
| `architecture/master-architecture.md` (real, 3 mermaid fences, 32 headings) | 47 KB | 18.2 ms |
| `roadmap/outstanding-work.md` (second-largest in the tree) | 170 KB | 45.3 ms |
| `history/handoffs/M4_HANDOFF.md` (the largest document in the tree) | 217 KB | **90.0 ms** |

The spec's own benchmark size clears the budget with roughly 5–6× margin. The largest real
document in the tree — 5.4× the benchmark size, a historical handoff nobody browses routinely —
sits close to the 100 ms line rather than comfortably under it. Not a blocker (it is within
budget, measured, and not a page on anyone's regular path), but worth knowing before treating the
40 KB figure as representative of every document this viewer might be asked to render.

### 2.3 No raw-asset route

`api.md` §8 names four routes — tree, page, search, ADR index — and none of them serves a raw
file. A markdown image (`![]()`) or a link to a non-`.md` target therefore renders as plain text
(alt text for an image, the link text alone otherwise) rather than a broken `<img>` or a link into
a route that does not exist. Documented in `services/docs.py`'s own module docstring and tested
(`test_a_link_to_a_non_markdown_target_renders_as_text`). A later row can add a raw-asset route
if the documentation ever needs an embedded image rendered — nothing here forecloses it, since
the link-classification function already treats "resolves inside root but not `.md`" as its own
case, not folded into "outside the root".

### 2.4 The kickoff's ADR count is stale

"the ADR index of 127 rows" was written when the tree had 127 ADRs; W3/WM added ADR-0128 and
ADR-0129 the same day this arc runs on, so the real count as of this row is **129**. Rendered as
whatever `adr/README.md` actually contains — 129 rows, verified — rather than forced to match the
kickoff's number. Not a defect in this row; a stale number in a kickoff prompt written before the
ADRs it now runs alongside existed.

## 3. Other decisions taken in this row

1. **`docs_index`'s FTS5 shadow tables are excluded from the migration-parity check by name**
   (`FTS5_SHADOW_TABLES`, `services/docs_index.py`, read by
   `tests/integration/test_migrations.py`). SQLite's FTS5 module creates five bookkeeping tables
   (`_data`, `_idx`, `_docsize`, `_config`, `_content`) alongside the virtual table itself when
   `CREATE VIRTUAL TABLE … USING fts5(…)` runs — measured directly against a migrated database,
   not assumed — and none of the six is or should be modelled in `Base.metadata`; a raw-DDL
   virtual table simply is not representable there. `weightsdb.MigrationRunner.check_parity` has
   no exclusion hook of its own, so the filter lives in the test, not the shared package.
2. **The migration falls back to a plain table when SQLite has no FTS5 module compiled in**
   (spec §13 risk T9), rather than letting `CREATE VIRTUAL TABLE` fail startup outright — the
   spec's own "a LIKE fallback labelled degraded" language only makes sense if the database can
   still come up without FTS5. Not exercised live (FTS5 is compiled into this environment's
   Python); the fallback's shape is covered by `search()`'s own degrade path, which is exercised
   regardless of which physical table exists underneath (a forced-degraded test calls
   `_search_like` directly).
3. **A relative link is rewritten only when the target ends in `.md`.** Spec §7.5 says "relative
   links rewritten to viewer routes" without qualifying which links; the qualification is this
   row's own, made necessary by §2.3 above (no raw-asset route to rewrite anything else to).
4. **Renderer instances are never shared or reused across requests.** `mistune.create_markdown`
   is called fresh inside `render_markdown` every time, with a fresh `_DocsRenderer` holding the
   per-call `outline`/`has_mermaid` state — Starlette runs a sync route handler in a threadpool, so
   a shared renderer's mutable state would race between two concurrent page loads.
5. **The security checklist's blanket "no route accepts a path-shaped parameter" test now carries
   a named allowlist** (`_REVIEWED_PATH_PARAMETERS`, `tests/security/test_checklist.py`) rather
   than being weakened generally. `/docs/page`'s `path` parameter — both the JSON route and its
   HTML page — is the first, and should remain the only, parameter on that list without a fresh
   review: everything else still fails the check by design.
6. **`page` was dropped as a `render_shell_page` keyword** once it collided with the docs route's
   own `page` context variable (the rendered `DocPage`). It turned out to be vestigial: `_shell.html`
   no longer reads it anywhere (`block navigation`, the only place that ever compared against it,
   has been empty since row W3's shell rewrite) — found by the `TypeError` it raised, not by
   inspection, and removed from `_docs_page` rather than renamed, since nothing needs it.

## 4. What the kickoff got wrong, or did not know

1. **Mermaid was assumed vendored** — see §2.1. Not a defect exactly (the design brief always
   named WeightRoomGym-vs-MirrorWall as the boundary for docs-only assets), but the kickoff's own
   "Read first" list does not flag that no prior row actually vendored it.
2. **api.md §8 has no raw-asset route**, which the kickoff's "relative links rewritten to viewer
   routes" line does not anticipate needing to qualify — see §2.3.
3. **The ADR count (127) is stale** — see §2.4.
4. **The security checklist's phase-1-era assumption** ("no Phase 1 endpoint … accepts a
   filesystem path") is the first thing in the whole test suite this row's own routes falsify by
   design; the kickoff does not mention it because whoever wrote that checklist test in Phase 1
   had no way to know row W5 would legitimately need one.

## 5. Demonstration (Phase 5 acceptance criteria)

Run against the real tree (`[docs] root` pointed at this checkout's own `docs/`), through
`TestClient` rather than a physical phone — the responsive layout itself is inherited from
MirrorWall's tokens and base CSS, already validated by MirrorWall's own test suite (`WM_HANDOFF.md`
§2), and was not independently re-verified on a physical device in this session.

```text
indexed 369 documents
1. tree renders, "adr" and "architecture" both present:                 True
2. architecture/master-architecture.md: <pre class="mermaid"> present,
   mermaid.min.js loaded:                                                True, True
3. ADR index rows rendered:                                              129 (kickoff said 127 — §2.4)
4. Search "never zero": ADR-0016 present in the results:                 True (ranked 2nd, after the
                                                                           topically adjacent ADR-0070)
5. A test document's <script> tag: rendered escaped, never executed:     True
```

A page without a mermaid fence (`adr/0001-…md`) does **not** load `mermaid.min.js` — the JS
budget's one exception applies only where it is used, proven in
`tests/integration/test_docs_routes.py::test_a_page_with_mermaid_loads_the_vendored_script_and_a_plain_one_does_not`.

## 6. Verification a reviewer can repeat

```bash
cd WeightRoom && source .venv/bin/activate
ruff format --check . && ruff check . && mypy src tests && lint-imports
pytest -m "not live and not performance" --cov --cov-report=term-missing
# 683 passed, 1 skipped, coverage 90.12%
wr-gym config reference --check
wr-gym docs index --config <a config with [docs] root set>
```

## 7. What is deferred, unchanged from the kickoff

The `docs_index` job kind is a stub (a callable `rebuild_index`, no scheduler — the runner is
W9's, exactly as the kickoff says). Settings, the doctor, chat and the database viewer remain
W4/W6/W7. No raw-asset route (§2.3) is a new, small, explicit addition to that list — not
something the kickoff named, but a real gap the same shape as the others.
