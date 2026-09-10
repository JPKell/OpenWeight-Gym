# N2 handoff — the unit page shows each attempt's egress decision; `research` starts from the workspace

**Row:** N2 of [outstanding work §1](../../roadmap/outstanding-work.md), from M1's findings 5 and 6 (D10).
**Run:** 2026-09-09, attended. **Ships:** under IdeaPress `[Unreleased]`, rides the next minor
(`1.5.0`); no release commit prepared here.

## What changed

* `units/detail.html` Provenance table: an **Egress** column — verdict, target name, `(remote)`
  when the target is, and the policy reason when denied — from `attempts[].egress`, which
  `unit_detail` has carried since row J1. `—` for attempts recorded before decisions existed.
* `POST /projects/{id}/research` (`ui_router`, CSRF-protected, not in `openapi.json` — page routes
  are `include_in_schema=False`, so the snapshot did not move and the contract test proves it).
  Calls `start_stage(stage="research")`, the same service the API's
  `POST /api/v1/projects/{id}/stages/research/run` and the CLI already used; redirects to the
  workspace. The API route existed all along — M1's D10 was about the *page*.
* Workspace page: a "Research" section with the form, shown when no stage is running, and a
  sentence naming the hosts a fetch may reach or stating that none may. `workspace_view` gained
  `research.allowed_hosts` for it.
* **Decision recorded** in `apps/ideapress/spec.md` §14: a browser click may cause a network fetch,
  only to a host in `[research] allowed_hosts`, and the page says so before the click. Mirrored.
* Tests: `tests/e2e/test_research_form.py` (the form starts the stage and finishes on a default
  install; a token-less post is 403); `test_cost_and_egress_page.py` renders the column.

## Gate

Python 3.13.15, `IdeaPress/.venv/bin/python`, from `IdeaPress/`: `ruff format --check .` 205
formatted; `ruff check .` clean; `mypy src tests` 200 files clean; `lint-imports` 4 kept;
`pytest -m "not live and not performance"` **1223 passed, 6 skipped, 30 deselected** (35.7 s).

## Found, not done

* The workspace's research section says nothing about whether research already ran; the notes
  are on the unit page only (M1's placement). A "last researched" line is a small follow-up.
