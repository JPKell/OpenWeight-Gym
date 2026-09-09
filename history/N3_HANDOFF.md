# N3 handoff — `http_fetch_tool` and "no host": the loopback reading is the deliberate one

**Row:** N3 of [outstanding work §1](../roadmap/outstanding-work.md), from M1's finding 1.
**Run:** 2026-09-09, attended. **Ships:** nothing — no API moved, so no `toolyard 0.1.2`.

## Decision

Of the row's two closes, the documented statement, as [ADR-0122](../adr/0122-an-empty-fetch-allowlist-means-loopback-and-no-host-is-not-registering.md):
a registered tool that refuses every URL misdescribes the process to the model (ADR-0007 rule 2
applied to tools), so "no host at all" is the tool's absence and both consumers' existing
not-registered branches are the design, not a workaround. ADR-0116's third "Revisit when" bullet
is answered.

## What changed

* `docs/adr/0122-…md` + index row; `packages/toolyard/spec.md` §7 rule 5 names the ADR
  (mirrored to `py/ToolYard/docs`, byte-identical).
* `py/ToolYard/src/toolyard/tools/fetch.py`: two sentences in `http_fetch_tool`'s `allowed_hosts`
  docstring; `CHANGELOG.md` `[Unreleased]` → Changed.
* PromptCadence and IdeaPress untouched: their branches stay, and their tests stay.

## Gate

Python 3.13.15, `py/ToolYard/.venv/bin/python`: `ruff format --check src`, `ruff check src`
clean; `pytest tests/unit/test_fetch_tool.py` 69 passed. Docstring-only change; the full gate is
unchanged from the last commit.
