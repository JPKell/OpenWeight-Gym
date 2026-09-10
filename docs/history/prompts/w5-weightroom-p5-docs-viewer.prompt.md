# Kickoff — W5: WeightRoomGym Phase 5 — docs viewer

**Row:** W5 (Sonnet 5 · high; overnight allowed) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Runs after W3; the one flexible row (any time after W3).
**Ships:** `wr-gym 0.5.0` prepared: the suite's documentation tree rendered, searchable,
with mermaid; read-only.
**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** [`spec.md`](../../apps/weightroom/spec.md) §7.5, §14 (the docs rows), §15 (the docs
budgets and the mermaid exception); [`api.md`](../../apps/weightroom/api.md) §8;
[`data-model.md`](../../apps/weightroom/data-model.md) (`docs_index`); [`development-plan.md`](../../apps/weightroom/development-plan.md)
Phase 5; ADR-0020 (vendored assets, the JS budget); `standards/security-standards.md` §5, §6;
ToolYard's `PathContainment` tests as the containment vector set (read, do not import);
`history/handoffs/W3_HANDOFF.md`.

## Decisions already taken — do not reopen

* `mistune` with a **sanitising** renderer: no raw HTML passes, no `| safe`; fences are code;
  a `mermaid` fence becomes `<pre class="mermaid">` for the vendored client renderer, which loads
  **only** on a page that contains one (spec §5, §15).
* Relative links rewrite to viewer routes; links outside `[docs] root` render as text; every
  served path is resolved and contained; a symlink out of the root is refused.
* FTS5 in WeightRoomGym's own database, rebuilt by `wr-gym docs index` and the `docs_index` job
  kind (the job runner is W9's; stub the kind as a callable now); a LIKE fallback labelled
  *degraded* when FTS5 is absent (risks T9).
* The ADR index is parsed from `adr/README.md`'s table, not from the filenames.
* Read-only: no route writes a document (spec §3).

## Gates

**Gate A — rendering.** `services/docs.py`: root resolution (`[docs] root`, else the `docs/`
beside the checkout, else `DOCS_ROOT_MISSING`), containment, the tree, rendering with heading
ids and an outline, link rewriting, the mermaid mount; goldens for a table, a fence, a mermaid
block, a footnote, a relative and an outside link; the sanitiser against `<script>` and `{{ }}`.
Commit.

**Gate B — search and index.** `docs_index`, the indexer, `wr-gym docs index`, search with
snippets, the FTS5 probe and fallback, the ADR index page. Commit.

**Gate C — pages and budget.** Tree, page, search, ADR index pages in the shell; the JS budget
asserted (mermaid absent from a page without a diagram); `CHANGELOG.md`; `0.5.0`. Commit.

## Demonstrate

Plan Phase 5 criteria on a phone: the tree, `architecture/master-architecture.md` with its
mermaid graph rendered, the ADR index of 127 rows, a search for `never zero` landing on
ADR-0016; a test document with `<script>` rendered as text.

## Finish line

Gate green, coverage held, one commit per gate, `docs/history/handoffs/W5_HANDOFF.md`, the row marked done.
