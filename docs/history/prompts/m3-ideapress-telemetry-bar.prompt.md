# Kickoff — M3: IdeaPress's telemetry bar — remove it from the documents

**Row:** M3 (Sonnet 5 · high — §2.12's overnight adjustment of the scheduled `standard`) of
[`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md) §1.
**Ships:** nothing released by this row; the change rides `ideapress 1.4.0`, which row M1 prepares
after you. Leave your entry under `## [Unreleased]`.
**Component:** `/home/jpk/ai/suite/IdeaPress` plus the `docs` repository.

**Overnight, unattended, authorised by the operator on 2026-09-07.** Record every judgement in the
handoff; never stop to ask. **Row M1 starts in this same IdeaPress checkout when you finish — leave
it clean and committed.**

---

## Standing preamble

* **Work from inside the component directory.** `IdeaPress/.venv/bin/python`.
* **House method** as in every kickoff: docstring-first, `from __future__ import annotations`,
  keyword-only optionals, `mypy --strict`, line length 100.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, coverage ≥ 85 %. `CHANGELOG.md` under
  `[Unreleased]`. One Conventional Commit per gate. Name the interpreter.
* **Documentation is mirrored.** Edit `/home/jpk/ai/suite/WeightRoom/docs/` first, then copy byte-identically
  into `IdeaPress/docs/apps/ideapress/`; verify with `cmp`. **`IdeaPress/docs/README.md` is
  repo-local — never overwrite it.** The `docs` repository is shared with row M2 tonight: commit
  only the files you edited, by name; never `git add -A`.
* **Do not push, do not tag, do not publish.**
* **`git status --short` at start and end**; `git checkout --` anything you did not edit.

## What this row is, and the decision already taken

`show_telemetry_bar` (`IdeaPress/src/ideapress/web/rendering.py:53`) is a hard-coded `False` Jinja
global; nothing renders IdeaPress's three machine-condition rows of the degradation matrix
([`architecture/graceful-degradation.md`](../../architecture/graceful-degradation.md) §2 footnote ⁴
and §2.1: **No GPU present**, **`nvidia-smi` missing or failing**, **GPU sensor unavailable**), and
`sweatmeter` is imported once, as a presence probe in `services/diagnostics.py:222` for the
VRAM-preflight capability flag.

The row offered two options. **The coordinator chose removal** (2026-09-07): IdeaPress does not
schedule work on the machine — it routes through LoadCoach, which owns the telemetry bar — so a
second bar would show a machine state IdeaPress never acts on. Wiring it would add a
per-page-render telemetry read for a display with no decision behind it. Record this as
**ADR-0115** (`docs/adr/0115-ideapress-shows-no-machine-telemetry.md`, index row in
`docs/adr/README.md`; the number is reserved for you — M1 takes 0116).

## The work, in gate order

* **Gate A — ADR-0115 + docs.** Write the ADR (house shape: Context, Decision, Consequences,
  "Revisit when"; the revisit trigger is IdeaPress ever scheduling or measuring on the machine
  itself). In `apps/ideapress/spec.md`: wherever §5, §15/§16 promise an optional telemetry display
  (`grep -n telemetry`), say instead that IdeaPress shows no machine telemetry and why, keeping the
  `[telemetry]` extra's true remaining purpose (the VRAM-preflight presence probe) if the spec
  describes it, otherwise removing the extra's claim too. In `graceful-degradation.md`: delete the
  three IdeaPress machine rows from §2.1 and §2 (or mark the cells "n/a — ADR-0115"; choose
  whichever the table's existing conventions use for a non-applicable cell), delete footnote ⁴,
  update the "What this index shows" paragraph so only LoadCoach's cell (row M2, running tonight,
  will clear that one — do not edit its sentence) remains. Mirror `spec.md` (and any other mirrored
  IdeaPress document you touched). Commit in `docs` by file name.
* **Gate B — the code.** Delete the `show_telemetry_bar` global and every template branch on it
  (`grep -rn show_telemetry_bar src tests`). Decide whether the `[telemetry]` extra in
  `pyproject.toml` still earns its place: it does if `diagnostics.py`'s presence probe changes a
  user-visible capability flag that a test exercises; otherwise remove the extra and the probe
  together, and the README/quickstart lines that advertise it. Conservative default: keep the
  extra, fix its comment to say what it is for. `CHANGELOG.md` `[Unreleased]`: one line under
  Removed. Any `IdeaPress/docs/*.md` repo-local page mentioning the bar is edited in place.
* **Gate C — the tests.** `tests/unit/test_packaging.py`'s dependency set if the extra moved; a
  test that the rendered base template contains no telemetry region (one assertion).

## Exit conditions

1. Full gate green on a named interpreter, coverage ≥ 85 %.
2. `grep -rn show_telemetry_bar /home/jpk/ai/suite/IdeaPress/src /home/jpk/ai/suite/IdeaPress/tests`
   is empty.
3. `graceful-degradation.md` §2.1 has no IdeaPress `untested` cell and no footnote ⁴.
4. ADR-0115 exists, indexed, cross-referenced from `spec.md`.
5. `cmp` silent for every mirrored file; `git status --short` clean in both repositories.

## The handoff

Write `docs/history/handoffs/M3_HANDOFF.md` (row M3 of outstanding-work, not milestone M3): gates as commits
with invocations and interpreter; the extra decision; exit conditions answered; what this prompt
got wrong. Mark row M3 done in `roadmap/outstanding-work.md` (bold **done 2026-09-08**, handoff
path, commits) and commit that file by name.

## Constraints

* No release commit — M1 cuts `1.4.0`.
* Never weaken `.importlinter`. No new dependency.
* If the work must stop early, stop at a green gate with a commit and say where.
