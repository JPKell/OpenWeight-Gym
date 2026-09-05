# E6 handoff — the fake provider must not be gated on real VRAM

Row **E6** of `docs/roadmap/outstanding-work.md` §1. Scheduled Sonnet 5 · standard, run at high, no
model deviation.

## 1. Gate results — interpreter and invocation named (M5C-13)

Interpreter: `/home/jpk/ai/suite/LoadCoach/.venv/bin/python`, Python 3.14.4. (The kickoff prompt's
§0 said 3.13.15; `python --version` in this venv reports 3.14.4 — a stale fact in the kickoff, not
something this row changed. Recorded per M5C-13; not chased further, since the repo's baseline is
3.12 with 3.13/3.14 both in the CI matrix.)

```text
$ cd /home/jpk/ai/suite/LoadCoach && source .venv/bin/activate && pip install -e ".[dev]"
$ ruff format --check .          # 191 files already formatted
$ ruff check .                   # All checks passed!
$ mypy src tests                 # Success: no issues found in 171 source files
$ lint-imports                   # Contracts: 4 kept, 0 broken.
$ python -m pytest -m "not live and not performance"
861 passed, 3 skipped, 15 deselected in 74.43s
```

**The three known evidence-golden failures the kickoff named did not reproduce here.** This venv's
`pip install -e ".[dev]"` resolved `setspec==0.4.0` (matching `requirements/ci.lock` and CI), not
the workspace's 0.6.0-era checkout the kickoff's §0 describes — `python -c "import setspec;
print(setspec.__version__)"` confirms `0.4.0`. With 0.4.0 installed, the golden fixtures only
parametrize `[1.0-minimal|1.0-full|1.0-unsupported]` (no `1.1-*` cases exist to fail), and all three
pass. The gate above is therefore **fully green**, not "green except three" — a better outcome than
the kickoff assumed, not a discrepancy this row introduced. H4 still owns the underlying pin
question; this is only a note that this particular run's environment happened to match CI rather
than the workspace checkout.

## 2. Commits

* LoadCoach `dfbf2d8` — `fix(provider): stop gating the fake provider on real VRAM (E6)`. Pushed;
  `git status -sb` clean, level with `origin/main` before and after.
* docs — this file, plus `outstanding-work.md` (E6 row marked done), `apps/loadcoach/spec.md` §12
  and `apps/loadcoach/routing.md` §4 (mirrored byte-identically into `LoadCoach/docs/`, `cmp`-proved
  before the LoadCoach commit above).
* `git -C py/ModelRack status --short` — empty, before and after. ModelRack untouched throughout.

## 3. Reproduction — Gate A, term by term

`tests/integration/test_fake_provider_vram.py::test_gate_a_...` builds
`FakeProvider(FakeScript(models=(DEFAULT_MODEL,)))` directly — ModelRack's own, unmodified 8.5 GB
default — and routes `general.chat` with `context_size=16384` configured against a snapshot with
1.2 GB free (E4's own reported figure). Every candidate is rejected `insufficient_vram` and routing
raises `NoEligibleModel`, matching §0.2's derivation exactly:

| Term | Formula | Bytes |
|---|---|---|
| weights | `8_540_000_000 × 1.05` | `8_967_000_000` |
| kv | `(2 × 32 × 8 × 128 × 2) × 16_384` | `2_147_483_648` |
| activation | fixed | `268_435_456` |
| **total** | | **`11_382_919_104`** (~10.6 GiB / 11.4 GB, matching E4's observed figure) |

`kv_source == "theoretical"`, `kv_precision_assumed == True` (no profile sets `kv_cache_precision`,
so f16 is substituted). This test is kept permanently — it pins the arithmetic against ModelRack's
`DEFAULT_MODEL`, independent of whatever LoadCoach's own default becomes, and it is the basis Gate
C's "provoke it on purpose" test reuses.

## 4. Before / after — what `build_provider("fake")` declares

| | Before (`DEFAULT_MODEL`, unscripted) | After (`build_provider`'s own default) |
|---|---|---|
| `name` | `fake-model:8b-q8_0` | `fake-model:tiny-q8_0` |
| `size_bytes` | 8_540_000_000 | 47_000_000 |
| `parameter_count` | 8_030_000_000 | 45_000_000 |
| `layers` | 32 | 4 |
| `kv_heads` | 8 | 2 |
| `head_dim` | 128 | 64 |
| `embedding_dim` | 4_096 | 256 |
| `attention_heads` | 32 | 4 |
| `max_context` | 32_768 | **32_768 (unchanged)** |

Worst case for the new default — `served_context` defaults to the model's own `max_context`
(32 768, deliberately left unchanged so every shipped local task profile's `min_context_tokens`,
up to `tools.agent.local_large`'s 32 768, is still satisfiable when a caller leaves context
unconfigured):

| Term | Formula | Bytes |
|---|---|---|
| weights | `47_000_000 × 1.05` | `49_350_000` |
| kv | `(2 × 4 × 2 × 64 × 2) × 32_768` | `67_108_864` |
| activation | fixed | `268_435_456` |
| **total** | | **`384_894_320`** (~367 MB) |

`384_894_320 + 536_870_912` (the 512 MiB default headroom) `= 921_765_232`, comfortably under a
machine reporting ~1 GiB free. Gate B (`test_gate_b_...`) proves it on the *exact* snapshot that
failed at E4 — 1.2 GB free — and that a `route()` journey selects the fake candidate, on GPU
index 0, with `estimated_vram_bytes < 1.2 GB`.

## 5. The `[provider.fake]` decision — and why

Went with §0.3's recommendation: a nested block (`size_bytes`, `layers`, `kv_heads`, `head_dim`,
all `int | None`, default `None`) rather than a lone scalar, because the KV term dominates
`size_bytes` at any context length worth testing — a lone `fake_model_size_bytes` override could
sit under the KV floor and never provoke the rejection, teaching an operator the wrong lesson.

`build_provider` (not a pydantic `model_validator`) enforces "all four or none," raising
`ConfigurationError` naming `provider.fake` and the missing field names — matching the existing
raise immediately below it in the same function (the unsupported-`kind` case), which is what the
kickoff pointed to as "the existing style." A pydantic-level validator was the alternative; I chose
`build_provider` because the rule is specific to `kind == "fake"`, not a general shape constraint on
`FakeProviderSettings` in isolation, and the function already owns exactly this kind of refusal.

Gate C (`test_gate_c_...`) sets the block to the *original* `DEFAULT_MODEL` geometry
(`size_bytes=8_540_000_000, layers=32, kv_heads=8, head_dim=128`) and routes against **10 GiB
free** — thirty times what the shipped default needs, i.e. "plenty" by the fake provider's own
standard — and still gets `insufficient_vram`, with the full `estimate` block and
`kv_source == "theoretical"`. `test_the_fake_provider_kind_is_not_exempted_from_insufficient_vram`
asserts the same thing at E4's 1.2 GB-free snapshot: `kind == "fake"` receives no bypass anywhere
in the constraint filter.

**One thing worth flagging for whoever reads exit condition 3 literally:** "a machine with plenty
free VRAM" does not mean an amount that would defeat *any* deliberately-configured model — an
operator who dials `[provider.fake]` up to, say, 100 GB will still get `insufficient_vram` on a
24 GB card, same as a real model would. "Plenty" here means plenty relative to what the *shipped
default* needs (a few hundred MB), which is the honest reading: the fake still models the
constraint, it just no longer trips it *by accident*.

## 6. The rename

`fake-model:8b-q8_0` → `fake-model:tiny-q8_0`. Checked first: `grep -rn "fake-model:8b\|8b-q8_0\|
fake-model:latest" LoadCoach --include="*.py" --include="*.toml" --include="*.md"
--include="*.html"` — zero hits anywhere in this repository. Blast radius inside LoadCoach is zero;
the rename is local to the `FakeModel` instance `build_provider` constructs by
`dataclasses.replace(DEFAULT_MODEL, ...)`, which never mutates `DEFAULT_MODEL` itself or reaches
FreeWeight/IdeaPress (see §8 below — read-only check, not edited).

## 7. What F1 inherits

A fake-provider journey (`route()`, and by extension `promptcadence run` against LoadCoach's fake)
that no longer depends on a free GPU: the shipped default fits at any free-VRAM level down to
roughly 1 GiB, and `[provider.fake]` exists if a future row wants to *deliberately* exercise
`insufficient_vram` in a live or e2e journey rather than a unit-level `route()` call. F1's budget
demonstrations can run on any machine, busy GPU or none.

## 8. Capacity-left check (read-only; item 12 of the kickoff)

`grep -rn "FakeProvider()" FreeWeight IdeaPress --include="*.py"` — both construct
`FakeProvider()` with zero arguments in test fixtures the same way LoadCoach's factory used to.
Neither routes on VRAM: FreeWeight measures capability evidence and does not run
`insufficient_vram`-shaped admission at all, and IdeaPress consumes LoadCoach's routing decisions
rather than reimplementing the constraint. Both are unaffected by `DEFAULT_MODEL`'s 8.5 GB size —
confirmed, not just assumed, by reading each application's own routing/admission path; neither
imports `loadcoach.domain.routing.constraints` or anything shaped like it. No follow-up row needed
from this check.

## 9. What the kickoff said that turned out not to be true

* §0's Python version (3.13.15) — this venv reports 3.14.4. Noted in §1; not a defect this row
  introduced or is positioned to fix.
* "Your gate is green except these three [evidence-golden failures]" — this run's gate was fully
  green; see §1's explanation (this venv resolved CI's `setspec` pin, not the workspace checkout
  the kickoff described).

## 10. Files changed

```text
LoadCoach/CHANGELOG.md                              (Unreleased entry)
LoadCoach/docs/apps/loadcoach/routing.md             (mirror of docs/, cmp-proved)
LoadCoach/docs/apps/loadcoach/spec.md                (mirror of docs/, cmp-proved)
LoadCoach/docs/configuration.md                      (regenerated: `loadcoach config reference`)
LoadCoach/src/loadcoach/config.py                    (FakeProviderSettings, ProviderSettings.fake)
LoadCoach/src/loadcoach/infrastructure/providers/factory.py   (the tiny default + the override)
LoadCoach/tests/integration/test_fake_provider_vram.py        (new: Gates A/B/C)
LoadCoach/tests/unit/test_provider_factory.py                 (new: build_provider unit coverage)
docs/apps/loadcoach/routing.md                       (source of the mirror above)
docs/apps/loadcoach/spec.md                          (source of the mirror above)
docs/roadmap/outstanding-work.md                     (E6 row marked done)
```
