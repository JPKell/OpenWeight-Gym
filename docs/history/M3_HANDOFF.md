# M3 Handoff — IdeaPress's telemetry bar

Row M3 of [`docs/roadmap/outstanding-work.md`](../roadmap/outstanding-work.md) §1 (not milestone
M3). Kickoff: `docs/history/m3-ideapress-telemetry-bar.prompt.md`. Overnight, unattended, Sonnet 5 ·
high, per §2.12's overnight adjustment.

## What this row was

`show_telemetry_bar` (`IdeaPress/src/ideapress/web/rendering.py`) was a hard-coded `False` Jinja
global. Nothing in the codebase ever set it otherwise, and — found by reading MirrorWall's own
`templating.py` before touching anything — no IdeaPress template branched on it either: the
conditional (`{% if show_telemetry_bar %}{% include "mirrorwall/telemetry_bar.html" %}{% endif %}`)
lives entirely inside MirrorWall's `base.html`, and MirrorWall's own `create_template_environment`
already defaults the same key to `False`. IdeaPress's override was therefore not just unwired, it
was a no-op restating MirrorWall's own default.

The kickoff stated the decision as already taken: **removal**, recorded as ADR-0115. This row's job
was to implement it, not to choose between build-or-remove — unlike the row's own text in
`outstanding-work.md`, which still reads as an open choice because it predates the coordinator's
2026-09-07 decision.

## Gates, as commits

**Gate A — ADR-0115 + docs.** Commit `43a9cd4` in `docs` (repository `~/ai/suite/docs`):
- `adr/0115-ideapress-shows-no-machine-telemetry.md` — new, house shape (Status, Context, Decision,
  Alternatives considered, Consequences, Revisit when). Revisit trigger: IdeaPress ever scheduling
  or measuring work on the machine itself.
- `adr/README.md` — index row for 0115; an Amendments-section paragraph recording why and when it
  was added, in the style of the other post-code ADRs in that file.
- `apps/ideapress/spec.md` — §5's dependency line no longer says "status display only"; it names
  the real remaining purpose (the VRAM-preflight presence probe) and cites ADR-0115. §16's "Optional
  telemetry display degrades" sentence is replaced with the decision statement.
- `apps/ideapress/api.md` — `GET /system/status`'s row dropped "optional telemetry snapshot": the
  handler (`web/routes/system.py`) never returned one; this was a second, smaller instance of the
  same unbuilt promise, found while reading the spec's neighbourhood rather than named in the
  kickoff.
- `architecture/graceful-degradation.md` — the three IdeaPress cells in §2 and in §2.1's row index
  (No GPU present, `nvidia-smi` missing or failing, GPU sensor unavailable) changed from
  `D`/`untested` to `n/a — ADR-0115`; footnote ⁴ deleted; "Four footnotes" corrected to "Three
  footnotes"; the "What this index shows" paragraph rewritten so only LoadCoach's still-`untested`
  cell remains in that count — **row M2's own sentence about that cell was left untouched**, per the
  kickoff's instruction, since M2 was running in the same checkout the same night and owns that
  edit.
- Mirrored: `IdeaPress/docs/apps/ideapress/spec.md` and `api.md`, verified with `cmp` (silent).
  `graceful-degradation.md` is an architecture document with no per-application mirror in IdeaPress,
  so nothing to copy there.

**Gate B — the code.** Commit `95813c1` in `IdeaPress` (title `feat(web): remove the unwired
telemetry bar (ADR-0115, row M3)`):
- `src/ideapress/web/rendering.py` — the `"show_telemetry_bar": False` global and its two-line
  comment deleted from `templates()`'s `globals_`. Nothing else in that function or file referenced
  it.
- The `[telemetry]` extra decision, made against the kickoff's own criterion ("keep it if the
  presence probe changes a user-visible capability flag a test exercises"): kept. `doctor`'s
  `telemetry` finding (`services/diagnostics.py`) is exactly that — a printed line, asserted by
  `tests/unit/test_doctor.py::test_telemetry_absence_explains_what_it_means_rather_than_complaining`
  and `test_every_check_is_present`. Only the label changed, everywhere it said "status display
  only": `pyproject.toml`'s comment, `README.md`'s dependency table note, and the CI
  `install-check` job's comment in `.github/workflows/ci.yml` — all three now say what the extra
  actually gates (the VRAM preflight, ADR-0038), and cite ADR-0115.
- `CHANGELOG.md` — one line under `[Unreleased] / Removed`, per the constraint that M1 cuts the
  release this rides in (`ideapress 1.4.0`), not this row.
- `docs/troubleshooting.md` and `docs/apps/ideapress/workflows.md`'s existing telemetry mentions
  were read and left alone: both already describe the real VRAM-preflight behaviour accurately and
  never claimed a display existed, so there was nothing to correct there.

**Gate C — the tests.** Folded into the same commit (`95813c1`), since ruff/mypy/pytest all run
against the working tree as one unit and splitting it into a third commit would have meant an
intermediate red gate for no reason:
- `tests/unit/test_packaging.py` — **unchanged**. The `[telemetry]` extra did not move; ADR-0114
  rule 6 already keeps optional extras outside the enumerated runtime-dependency budget that test
  checks, so there was nothing to update.
- `tests/e2e/test_system.py` — one new test,
  `test_the_page_shows_no_machine_telemetry`, asserting `"telemetry-bar" not in response.text` for
  the rendered `/system` page. Its docstring deliberately avoids the literal string
  `show_telemetry_bar` (rewritten once, after a first draft used it and would have made exit
  condition 2's grep non-empty) so it reads as an assertion about behaviour, not as another place
  the name lives on.

## The extra decision, explicit

Per the kickoff's own instruction to record this: the `[telemetry]` extra earns its place and was
**kept**, not removed. The reasoning, checked directly against the two files it touches:
`services/diagnostics.py`'s `try: import sweatmeter` block feeds a `Diagnosis` object that
`ideapress doctor` prints and that two tests assert on by name and by content. That is a real,
tested, user-visible capability flag — the kickoff's own bar for keeping the extra — so the
conservative default and the actual criterion agreed, and no judgement call was needed here.

## Exit conditions answered

1. **Full gate green on a named interpreter, coverage ≥ 85 %.** Python 3.13.15 (IdeaPress's own
   `.venv`). `ruff format --check .` (194 files already formatted), `ruff check .` (all checks
   passed), `mypy src tests` (no issues, 189 source files), `lint-imports` (4 contracts kept, 0
   broken), `pytest -m "not live and not performance" --cov` — **1164 passed, 6 skipped, 30
   deselected**, coverage **88.68 %**.
2. **`grep -rn show_telemetry_bar IdeaPress/src IdeaPress/tests` is empty.** Confirmed empty after
   the docstring rewrite above (the first draft was not; caught before commit).
3. **`graceful-degradation.md` §2.1 has no IdeaPress `untested` cell and no footnote ⁴.** Confirmed:
   the three IdeaPress rows read `n/a — ADR-0115` in both §2 and §2.1, and grepping the file for `⁴`
   returns nothing at all.
4. **ADR-0115 exists, indexed, cross-referenced from `spec.md`.** `docs/adr/0115-...md` exists;
   indexed in `docs/adr/README.md`'s table and given an Amendments paragraph; `spec.md` §5 and §16
   both link to it.
5. **`cmp` silent for every mirrored file; `git status --short` clean in both repositories.** `cmp`
   silent for `spec.md` and `api.md` (the two mirrored files this row touched). Both repositories'
   status is reported clean below, after this handoff and the roadmap update are committed.

## What this prompt got wrong

- The roadmap row's own text (`outstanding-work.md`, before this row's edit) still framed M3 as an
  open build-or-remove choice ("Decide: either wire the bar... or delete the rows..."), but the
  kickoff prompt that actually governs this row states the decision was already taken
  (`m3-ideapress-telemetry-bar.prompt.md`: "The decision (remove, ADR-0115) is already taken; do not
  reopen it"). The two documents disagreed with each other; the kickoff prompt is what a row
  actually runs from, so it won. This row's own table entry is corrected in the same commit as this
  handoff so a future reader does not hit the same disagreement.
- The kickoff guessed the telemetry promise lived at spec §5, §15/§16; grepping placed it at §5 and
  §16 (not §15 — §15 is Performance considerations and has no telemetry text; the Cross-Platform
  telemetry sentence is §16). A second, smaller instance of the same unbuilt promise turned up in
  `api.md`'s `GET /system/status` row ("optional telemetry snapshot") — not named anywhere in the
  kickoff's reading list, found only by reading the actual route handler
  (`web/routes/system.py::system_status`), which never returns anything of the kind. Fixed in the
  same commit since it is the identical defect one file over.
- The kickoff's Gate A instruction said to "mark the cells `n/a — ADR-0115`... or delete the rows"
  — the rows in question are *conditions* (No GPU present, etc.), shared across all four
  applications' columns in one table; only the IdeaPress *cells* in those rows could be touched
  without deleting FreeWeight's, LoadCoach's and PromptCadence's data in the same rows. Read
  literally, "delete the three IdeaPress machine rows" would have deleted three entire matrix rows.
  Implemented as marking the three IdeaPress **cells**, which is what the rest of the kickoff's own
  language ("mark the cells") and the exit conditions (which speak of "IdeaPress `untested` cell",
  singular focus) actually require.

## Left undone

Nothing. All three gates landed, the exit conditions are met, and the row needed no judgement call
beyond the one recorded above (the `[telemetry]` extra), which the kickoff's own criterion already
settled.

## Commits

- `docs` — `43a9cd4` — `docs(adr): IdeaPress shows no machine telemetry (ADR-0115, row M3)`
- `IdeaPress` — `95813c1` — `feat(web): remove the unwired telemetry bar (ADR-0115, row M3)`
- `docs` — this handoff plus the `outstanding-work.md` row-M3 update, committed together below.

Neither repository was pushed, tagged or published, per the standing instruction and this row's own
constraints. Row M1 (`ideapress 1.4.0`) starts in this same IdeaPress checkout next; it is clean and
committed.
