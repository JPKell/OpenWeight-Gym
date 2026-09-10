# K4 handoff — the pricing reader becomes a package, and IdeaPress stops rounding to zero

**Row:** K4 (Opus 5 · high), `docs/roadmap/outstanding-work.md` §1, both parts, with the operator's
decision on part (b) taken on the day: **extract into `loadledger 0.3.0` and adopt in both
applications**.
**Components:** `py/LoadLedger` (`main`), the worktree `IdeaPress-k4` (branch `k4-usage-pricing`),
`PromptCadence` (`main`), `docs` (`main`). Row K3 ran concurrently in `IdeaPress` on `main`; none of
its three files were touched here.
**Mid-row addition from the coordinator:** all four token classes made `UNSUPPORTED`-aware, not
only the two cache classes — see §4.

## 1. Gate results

Interpreter in all three repos: the repo's own `.venv/bin/python` — CPython **3.13.15**.

```bash
cd /home/jpk/ai/suite/py/LoadLedger
.venv/bin/python -m ruff format --check .    # 38 files already formatted
.venv/bin/python -m ruff check .             # All checks passed!
.venv/bin/python -m mypy src tests           # Success: no issues found in 27 source files
.venv/bin/lint-imports                       # Contracts: 3 kept, 0 broken
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                             # 219 passed, 31 skipped, 6 deselected
                                             # Required test coverage of 95.0% reached: 99.65%

cd /home/jpk/ai/suite/IdeaPress-k4
.venv/bin/python -m ruff format --check .    # 186 files already formatted
.venv/bin/python -m ruff check .             # All checks passed!
.venv/bin/python -m mypy src tests           # Success: no issues found in 181 source files
.venv/bin/lint-imports                       # Contracts: 4 kept, 0 broken
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                             # 1132 passed, 5 skipped, 30 deselected
                                             # Required test coverage of 85.0% reached: 88.54%

cd /home/jpk/ai/suite/PromptCadence
.venv/bin/python -m ruff format --check .    # 182 files already formatted
.venv/bin/python -m ruff check .             # All checks passed!
.venv/bin/python -m mypy src tests           # Success: no issues found in 178 source files
.venv/bin/lint-imports                       # Contracts: 5 kept, 0 broken
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
                                             # 1280 passed, 2 skipped, 10 deselected
                                             # Required test coverage of 85.0% reached: 91.61%
```

LoadLedger's 31 skips are its PostgreSQL legs, with no server on this machine; nothing in this row
touched `loadledger.sql`, a table, a column or a statement, so the SQLite legs are the whole of what
changed there. `git status --short` was clean in all four repos at the start and is clean at the
end.

**Release artefacts.** Built in a throwaway venv from `requirements/release.lock`
(`pip install --no-deps --require-hashes`, then `python -m build --no-isolation`):
`loadledger-0.3.0-py3-none-any.whl` (57.7 KB) and `loadledger-0.3.0.tar.gz` (177.2 KB), both
`twine check` **PASSED**. That wheel is what both applications were installed with for their gates.

## 2. The commits

| Repo | Hash | Commit |
|---|---|---|
| `py/LoadLedger` (`main`) | `3d2bc71` | `feat(pricing): read an ADR-0072 price catalogue (ADR-0110)` |
| `py/LoadLedger` (`main`) | `52163ca` | `chore(release): loadledger 0.3.0` |
| `IdeaPress-k4` (`k4-usage-pricing`) | `0c0f5e2` | `refactor(pricing): adopt loadledger.pricing as the one ADR-0072 reader` |
| `IdeaPress-k4` (`k4-usage-pricing`) | `692d7d9` | `feat(cost): an attempt records the two cache token classes (ADR-0070)` |
| `IdeaPress-k4` (`k4-usage-pricing`) | `2802223` | `fix(cost): a token count nobody took is not zero (ADR-0016)` |
| `PromptCadence` (`main`) | `c9c3dff` | `refactor(pricing): adopt loadledger.pricing as the one ADR-0072 reader` |
| `docs` (`main`) | see §8 | `docs(adr): ADR-0110 …` |

Nothing is pushed, nothing is tagged, nothing is published — standing instruction.

## 3. The hash-equality evidence

This was the row's stop condition, so it is stated in full.

A fixture holding three ADR-0072 records — the record printed in the ADR itself, IdeaPress's own
J1 test record, and a third exercising a stated digest, a stated effective window, a `price_tier`,
a `region`, a non-USD currency and a cache-read rate stated as the string `"0"` — was read by
**each application's own loader, before either was touched**:

| record | `pricing_hash`, PromptCadence | `pricing_hash`, IdeaPress |
|---|---|---|
| `openai_compatible/gpt-4o@unknown` | `0aa11514c7c3fcf0` | `0aa11514c7c3fcf0` |
| `ollama/gemma4:12b@unknown` | `24a133ea7262ad3e` | `24a133ea7262ad3e` |
| `ollama/qwen3:8b@sha256:bbbbbbbbbbbb` | `79b6b3d231df3f5f` | `79b6b3d231df3f5f` |

The two agreed record for record — which is the precondition ADR-0030's re-derivation had been
*assuming* rather than enforcing, and the reason the duplicate was worth removing before it stopped
being true. Those literals are now pinned in `py/LoadLedger/tests/unit/test_pricing.py` against
`tests/data/adr0072_catalogue.json`, and after adoption **both applications reproduce all three
byte for byte** (re-measured through each application's public `load_pricing_records`, output
diffed: identical). No hash moved, so the stop rule did not fire.

## 4. What was actually built

**Part (b) — `loadledger 0.3.0`.** `loadledger/pricing.py` holds the ADR-0072 format whole:
`load_pricing_records(path)`, `price_for_model(records, *, canonical_id, at)`,
`records_claiming(records, *, at)`, and `PricingFileError` (`LEDGER_PRICING_FILE_INVALID`) in the
existing error hierarchy. Three shapes of the decision are worth naming:

* **Functions over a sequence, not a catalogue class.** The two consumers hold two containers by
  necessity — PromptCadence a per-tier map, IdeaPress one flat list — so a class in the package
  would have been a name for a tuple and would have forced one of them to wrap. Each application
  keeps its own small `PricingCatalog`: `from_settings`, one delegating lookup, and the error
  translation. Recorded as spec §21's revisit trigger if a third shape appears.
* **Not exported from `loadledger/__init__.py`.** It opens files and the package root promises it
  does not — the rule `loadledger.sql` already follows. `PricingFileError` *is* exported, so
  `except loadledger.LedgerError` still catches everything the package raises.
* **The refusal messages moved verbatim.** They are what an operator repairs a hand-maintained
  price list from, and both applications' existing tests match on their text — which is what made
  the adoption provable without editing a test.

Spec §2, §3, §5, §7, §13, §18 and §21 gained the surface; §3's "No pricing" non-goal is restated as
"No pricing **decisions**", because the package now reads the rates an operator wrote down and
still invents, converts and extrapolates none. Development plan gained Phase 4.

**Part (b) adoption.** Both applications' `services/pricing.py` are now edges of ~60 and ~150 lines
(the second carries the tier map and `claiming`). Both floor on `loadledger[sql]>=0.3,<0.4`. The
acceptance criterion held exactly as the row set it: **every existing pricing test passed
unchanged** — 23 in IdeaPress, 16 in PromptCadence, not one edited.

**Part (a) — the token classes.** `ideapress.domain.inference.TokenUsage` gained
`cache_write_tokens` and `cache_read_tokens` (ADR-0070 rule 4's spelling), `attempts` gained the two
columns in one migration `0009` on the then-head `0008`, `record_attempt` stores them, and
`BudgetService.price` passes them through. Both backend adapters fill them — without that the
fields would have been permanently `None` and the row would have changed nothing a person can see.
The rendered figure now becomes a **bare total** when every class is reported and priced, and says
"at least" only when one is not; two unit tests pin both halves, and a third pins that one
unreported class is enough to keep the floor.

**Part (a), the coordinator's mid-row addition.** `_as_int` in the LoadCoach adapter read a missing
key *or the string* `"unsupported"` as `0`, and `_count` in the ModelRack adapter turned
`UNSUPPORTED` into `0` "for arithmetic only"; both landed in `input_tokens: int = 0`. Harmless while
LoadCoach sent `null`, and a fabricated zero from **loadcoach 1.1.3 (ADR-0112)**, which spells every
unavailable count `"unsupported"`. All four classes are now `int | None`; `_count` is deleted;
`BudgetService.price` translates each `None` to `UNSUPPORTED` at the BaseAiCore boundary, so an
unreported class is excluded and the debit is announced as a floor rather than totalled from a
number nobody measured.

**One deviation from the addition's literal wording**, flagged deliberately. It said "the sentinel,
never 0, never None". IdeaPress's spec §3 forbids the `UNSUPPORTED` sentinel any measurement role
inside the application, which is why `Timing` and `thinking_tokens` already use `None` and the
adapters already translate. Introducing the sentinel into the domain would have contradicted a
spec rule to solve a problem `None` solves identically — so the *rule* was implemented (never `0`,
anywhere, for any class) in the application's own established vocabulary, with the translation to
`UNSUPPORTED` at the one boundary that needs it. The intent — no fabricated zero, an unavailable
class flows through as ADR-0069's floor — is met end to end and tested.

## 5. Tests changed rather than added

Three, all consequences of part (a) changing behaviour on purpose. Listed because "existing tests
pass unchanged" was an acceptance criterion for the *extraction* and these are not it.

* `tests/contract/test_backend_conformance.py::test_generate_returns_a_complete_result` asserted
  `usage.input_tokens >= 0`. A capability-poor backend now reports `None` rather than `0`; the
  assertion became `count is None or count >= 0`, which is the same rule the timings test two lines
  below has always stated.
* Two `tests/live/` assertions gained `is not None` guards, for mypy. Neither ran (live marker).
* `tests/contract/loadcoach_mock.py` now carries `cache_write_tokens`/`cache_read_tokens` — `0` on
  the completed job (Ollama bills no cache tier, ADR-0070 rule 3) and `"unsupported"` on the failed
  one. That is what a real LoadCoach 1.1.3 sends; a mock that omitted them would have agreed with
  the adapter about a wire neither had seen.

## 6. What the operator has to do, in order

1. **Publish `loadledger 0.3.0`** (tag `py/LoadLedger` at `52163ca`, approve the PyPI environment).
   PyPI serves `0.2.0` today — confirmed with `pip index versions loadledger`.
2. **Recompile two `requirements/ci.lock` files** with `-P loadledger`: `IdeaPress-k4` and
   `PromptCadence`. Both pin `loadledger==0.2.0` and **both repositories' CI is red until this
   happens** — the hash-verified lock cannot resolve a floor PyPI does not serve. This is the same
   sequence row I4 followed for `toolyard 0.1.1`, and the locks were deliberately left alone rather
   than hand-edited. (`pip-compile` needs `--upgrade-package`, per row I3's note.)
3. **Merge `k4-usage-pricing`** into `IdeaPress` `main`, alongside row K3's work. No file this row
   touched is one K3 named (`services/project_review.py`, `domain/context_assembly.py`, the config's
   review-budget key), so the merge should be clean; `CHANGELOG.md` under `[Unreleased]` is the one
   plausible textual conflict.
4. Then push `PromptCadence` and `docs`.

## 7. Findings for another row

* **IdeaPress's `attempts.input_tokens` may now be `NULL` for a completed attempt**, where before
  it was only ever `NULL` for a deterministic step. The exporters and reports already typed it
  `int | None` and pass it straight through, so nothing broke — but a **JSON export consumer** that
  assumed a number for a completed attempt will now sometimes see `null`. Nothing in this
  repository does; an external one might.
* **PromptCadence's own `TokenUsage` path was not audited for the same defect.** It reads the wire
  through `token_count_from_wire` and appears to handle `"unsupported"` correctly, but this row
  only proved it for IdeaPress. A row that wants the guarantee suite-wide should check FreeWeight
  and LoadCoach's own consumers too.
* **`loadledger.pricing` is untested against a *third* container shape**, which is the trigger for
  shipping the catalogue class spec §21 records as declined. Nothing needs doing until then.
* **`total_tokens` on IdeaPress's `TokenUsage` had no caller at all** and now returns `int | None`.
  It was corrected rather than deleted (it summed input + output only, which under-counts disjoint
  classes) — but an unused public property on a 1.x domain type is a small thing somebody should
  either use or remove.
* **ADR-0112 and `loadcoach 1.1.3` landed today from another row** and are what made the fabricated
  zero live. Whoever schedules the LoadCoach release should know IdeaPress now depends on that
  spelling being stable.
