# Contributing to WeightRoomGym

This repository is one component of the Local AI Suite — and the home of the suite's documentation:
`docs/` here is the **canonical** tree every other repository mirrors from (see the workspace
`CLAUDE.md`). Before changing anything, read `docs/apps/weightroom/spec.md` and the current phase
in `docs/apps/weightroom/development-plan.md`.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Rules that apply to every change here

* WeightRoomGym is a host operator tool **above** the layer rules, and that exception is exactly as
  wide as ADR-0123 says: it may read every application's database, edit every `config.toml`,
  drive `systemd --user` and call every application's HTTP API and CLI. It may **not** import an
  application (`.importlinter` asserts it), run a tool, or reach a model provider for chat.
* A raw write into another application's database passes the ADR-0124 guard — stopped unit,
  automatic backup, dry run, typed table name, audit row — or it does not happen.
* No business logic in a route handler or CLI command body — both call one service method and render.
* Docstring-first; `from __future__ import annotations`; units in names; keyword-only optionals;
  injected clocks, subprocess runners, filesystem roots and HTTP clients.
* Prompts are versioned JSON records, not Python string literals.
* Every phase's acceptance criteria in `development-plan.md` must be demonstrable — the plan states
  what to run and what a person should see.

## Before opening a pull request

```bash
ruff format --check .
ruff check .
mypy src tests
lint-imports
pytest -m "not live and not performance"
```

## Commit style

Conventional Commits, with a `CHANGELOG.md` entry under `## [Unreleased]` for any user-visible
change. Documentation-only changes to `docs/` use `docs(...)`, as the documentation repository
always did.
