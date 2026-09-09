# Kickoff — E6: the fake provider must not be gated on real VRAM

**Row:** E6 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1. Read the
row in full first — it already made this row's central judgment call (that the *rejection* path must
stay reachable on purpose), and §0.1 below corrects the one thing it gets factually wrong about
**where the numbers live**.
**Model:** **Sonnet 5 · standard**, as scheduled — overnight, run at **high**
([model-assignment §2.12](docs/roadmap/model-assignment.md)). One provider's declared numbers plus
one configuration key.
**Repositories:** `/home/jpk/ai/suite/LoadCoach` only, then `/home/jpk/ai/suite/docs`.
**Ships:** nothing to PyPI. A LoadCoach change, changelog under `## [Unreleased]`, no version bump,
no tag.
**Overnight:** permitted (E6 is on none of §2.12's never-overnight list).
**Runs before F1** — F1's budget demonstrations drive the same fake-provider journeys and will hit
the same wall.

---

## 0. Machine facts, verified 2026-09-04 before this prompt was written

Do not re-derive these; do **confirm** the ones marked.

* **LoadCoach `main` is at `5c5aa1f`, clean, level with `origin/main`, CI green** (run at `5c5aa1f`
  succeeded). **Confirm** with `git status -sb` at the start and at the end.
* **LoadCoach has three known local test failures that are NOT yours and must stay:**
  `tests/contract/test_evidence_import.py::test_every_golden_round_trips_through_the_store_unchanged[1.1-full|1.1-mixed|1.1-unsupported]`
  (verified 2026-09-04: 3 failed, 855 passed). They come from the workspace SetSpec checkout being
  0.6.0-era while `pyproject.toml` pins `setspec>=0.4,<0.5`; CI installs 0.4.0 from
  `requirements/ci.lock` and is green. **H4 owns them.** Your gate is green *except* these three —
  say so explicitly in the report, with the count, and do not "fix" them.
* **Push auth is configured** (2026-09-04): `~/.gitconfig` carries
  `credential."https://github.com".helper = !/usr/bin/gh auth git-credential`, so a bare
  `git push origin main` works. **Probe with `GIT_TERMINAL_PROMPT=0 git push --dry-run origin main`,
  never with `git ls-remote origin`** — these repos are public and `ls-remote` succeeds anonymously
  on a repo you cannot push to.
* **LoadCoach's venv is Python 3.13.15.** Name it and every exact invocation in the report (M5C-13).
  There is **no python3.12** on this host.

## 0.1 The row's one factual error — read this before you plan

The row says *"LoadCoach's **fake** provider declares an 8.5 GB model"*. **The numbers are not in
LoadCoach.** They are ModelRack's, and LoadCoach merely accepts them by default:

* `py/ModelRack/src/modelrack/providers/_fake_script.py:374–403` — `DEFAULT_MODEL: Final[FakeModel]`,
  `name="fake-model:8b-q8_0"`, `parameter_count=8_030_000_000`, `size_bytes=8_540_000_000`,
  `vram_bytes=9_100_000_000`, `total_bytes=9_400_000_000`, `max_context=32_768`,
  `embedding_dim=4_096`, `layers=32`, `attention_heads=32`, `kv_heads=8`, `head_dim=128`.
* `LoadCoach/src/loadcoach/infrastructure/providers/factory.py:55–58` — the whole of LoadCoach's
  involvement:

  ```python
  if settings.kind == "fake":
      from modelrack.testing import FakeProvider
      return FakeProvider()
  ```

  A zero-argument construction, so it inherits `FakeScript()`'s default catalogue, which is
  `models=(DEFAULT_MODEL,)` (`_fake_script.py:640`).

**Fix it in LoadCoach, not in ModelRack.** Three reasons, and the first is sufficient:

1. `DEFAULT_MODEL` is ModelRack's published contract and FreeWeight's and IdeaPress's fakes read the
   same constant. Changing it changes three applications' test doubles to fix one application's
   routing demonstration, and it needs a `modelrack` release to reach any of them.
2. ModelRack has **unreleased P6 work** (`LlamaCppProvider`) sitting in `## [Unreleased]` and riding
   `0.7.0` at row **H1**. Do not put an unrelated change on that train.
3. The seam already exists and is public API: `FakeProvider(FakeScript(models=(...,)))`.
   `FakeScript` is a frozen dataclass, so `dataclasses.replace(DEFAULT_MODEL, ...)` gives you a
   varied model in one line, which is exactly what `_fake_script.py:614` says it is for.

## 0.2 The KV term — the part that makes this non-trivial, and the row does not mention it

`insufficient_vram` compares `estimate.total_bytes` against free VRAM per device
(`LoadCoach/src/loadcoach/domain/routing/constraints.py:485–497`). The estimate is **three** terms
(`constraints.py:96–107`, `estimate_vram` at ~`:230–258`):

```text
total = weights + kv + activation
weights = size_bytes × LOADING_OVERHEAD_FACTOR          # 1.05          (constraints.py:50)
kv      = kv_bytes_per_token × served_context
kv_bytes_per_token = 2 × layers × kv_heads × head_dim × element_bytes   # f16 assumed → 2 bytes
activation = ACTIVATION_OVERHEAD_BYTES                  # 256 MiB fixed (constraints.py:56)
```

Verified arithmetic against E4's observed 11.4 GB, at `served_context = 16 384`:

```text
weights    = 8_540_000_000 × 1.05                     =  8.967 GB   (E4's "weights_bytes 8 967 000 000")
kv_per_tok = 2 × 32 × 8 × 128 × 2                     =  131 072 B/token
kv         = 131 072 × 16 384                         =  2.147 GB
activation = 256 MiB                                  =  0.268 GB
total                                                 = 11.38 GB    <-- E4 reported 11.4 GB
```

**Shrinking `size_bytes` alone is not enough.** With `size_bytes` at, say, 200 MB you would still
carry 2.147 GB of KV plus 0.268 GB of activation — about **2.4 GB**, which still loses to E4's
observed 1.2 GB free. **You must shrink the geometry too** (`layers`, `kv_heads`, `head_dim`), and
possibly the profile's served context. Confirm the served context the fake journeys actually
resolve rather than assuming 16 384 — `served_context` is the *resolved* profile's figure, never
`max_context`.

Target: the fake's `total_bytes` should sit **comfortably under a few hundred megabytes**, so that
`free VRAM + headroom` admits it on a machine with almost nothing free. Note
`DEFAULT_VRAM_HEADROOM_BYTES = 512 MiB` (`constraints.py:68`) and that `device_fits` is evaluated
per GPU (ADR-0027). Keep the reduced numbers **internally coherent** — a `parameter_count`,
`size_bytes`, `embedding_dim`, `layers` and `head_dim` set that could describe a real small model —
because the fake exists to *model* a provider, not to defeat the arithmetic. Say in the changelog
what shape you chose and why.

## 0.3 The decision this row leaves to you — take it, record it

Requirement 2 says the declared size must be **configurable** so an operator can provoke
`insufficient_vram` deliberately. `ProviderSettings` (`LoadCoach/src/loadcoach/config.py:259–276`)
has `model_config = ConfigDict(extra="forbid")` and three fields today (`kind`, `base_url`,
`timeout_seconds`), so any key you add is a deliberate, validated contract addition.

**Recommendation: a nested `[provider.fake]` block, not a single scalar.** A lone
`fake_model_size_bytes` cannot provoke the rejection on its own — §0.2 shows the KV term dominates,
so an operator who sets only a size and sees no rejection learns the wrong lesson. A small block
whose fields map onto the estimate's actual inputs (weights size, and the geometry that sets
`kv_bytes_per_token`) makes the diagnostic reproducible *and* teaches what drives it. Every field
optional, every default the small one from §0.2, and the block absent entirely on a normal install.

Take a different shape if you can argue it better, but **record the choice and the reason in the
changelog and in the field docstrings**, and make sure requirement 2 is genuinely satisfied: there
must be a configuration an operator can write that reliably produces `insufficient_vram` with the
full `estimate` block, on a machine with plenty of free VRAM.

---

## 1. Setup

```bash
cd /home/jpk/ai/suite/LoadCoach && source .venv/bin/activate && pip install -e ".[dev]"
```

Name the interpreter and each exact invocation in the report (M5C-13). Use the session scratchpad for
every scratch database, config file and log — **never** the repository, never `/tmp` directly, never
the workspace root.

## 2. Standing preamble ([outstanding-work §2](docs/roadmap/outstanding-work.md))

* Work inside a component directory, never the workspace root. Nothing at the root is versioned.
* The finish line: `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` — green **except** the three known evidence failures in
  §0, which you report by name and count.
* `CHANGELOG.md` updated under `## [Unreleased]`; **one Conventional Commit per repository**.
* `pytest-randomly` is on; a seed-only failure is a real bug.
* House method: docstring-first (define behaviour → Google-style docstring with Args/Returns/Raises
  **including what it refuses** → tests → implementation), `from __future__ import annotations`,
  units in names (`*_bytes`), keyword-only optionals, `mypy --strict`, line length 100.
* **Never `git add -A`.** Stage named paths. Commit at every boundary.
* Any workspace `docs/` edit is mirrored byte-identically into the component repo and **`cmp`-proved**.

## 3. Reading list, in this order

1. The **E6 row** of `docs/roadmap/outstanding-work.md` §1, plus §3's "E6 … before F1" placement.
2. `docs/history/E4_HANDOFF.md` §5 — the diagnosis, the numbers, and what an operator saw.
3. `docs/apps/loadcoach/routing.md` §4 — the constraint order and `insufficient_vram`'s inputs. Note
   the standing sentence: *"Every rejection is stored with the numbers that caused it … because
   'nothing was eligible' is useless without them."* That sentence is this row's whole motivation.
4. `LoadCoach/src/loadcoach/domain/routing/constraints.py` — `LOADING_OVERHEAD_FACTOR`,
   `ACTIVATION_OVERHEAD_BYTES`, `ASSUMED_KV_CACHE_PRECISION`, `kv_bytes_per_token`, `estimate_vram`,
   `device_fits`, and the `insufficient_vram` branch.
5. `LoadCoach/src/loadcoach/domain/admission.py` — `RESOURCE_REJECTION_REASONS` and
   `waiting_job_can_proceed`. A resource rejection is *retryable*; check whether your change alters
   what a waiting job does, and say so either way.
6. `py/ModelRack/src/modelrack/providers/_fake_script.py` — `FakeModel`, `DEFAULT_MODEL`,
   `FakeScript`. Read only; you are not editing this repository.
7. ADR-0016 (`UNSUPPORTED` is not zero) and ADR-0027 (multi-GPU semantics).

---

## 4. The shape of the work

Two requirements, one commit, in this order. **Requirement 2 is the point of the row** — do not
treat it as a follow-on.

## 5. Gate A — reproduce the failure before you change anything

You cannot claim to have fixed a rejection path you never saw fire. Reproduce it **deterministically
and without a GPU**: `estimate_vram` and `device_fits` are pure functions over an injected telemetry
snapshot, so a test that supplies a snapshot with ~1.2 GB free reproduces E4's exact verdict on any
machine.

1. Write the failing case first, as a test: the shipped fake provider + a snapshot with a nearly-full
   GPU → **every** candidate rejected `insufficient_vram` → `NO_ELIGIBLE_MODEL`. Record the
   `estimated_bytes` your run produces and compare it with §0.2's 11.38 GB derivation. **If it does
   not match, your served-context assumption is wrong — chase that before going further.**
2. Confirm the §0.2 arithmetic term by term in the report (weights, kv, activation), so the fix is
   argued from numbers rather than from a hunch.

Keep this test. Inverted, it becomes requirement 2's proof.

## 6. Gate B — requirement 1: the default fake must never trip the constraint

Change **LoadCoach's** construction of the fake provider (`factory.py`), not ModelRack's constant.
Build a small `FakeModel` from `DEFAULT_MODEL` with `dataclasses.replace`, hand it to
`FakeScript(models=(...,))`, and hand that to `FakeProvider`.

* The default must fit on a machine with almost nothing free — pick the target from §0.2's
  arithmetic, not by trial and error, and show the arithmetic in a docstring or module comment.
* Keep the numbers coherent as a model description (§0.2).
* Keep the identity stable-ish and honest: it is still a fake, and its name should not now claim
  `8b` if it no longer describes one. A renamed fake model is a **visible change** to anything that
  pins `fake-model:8b-q8_0` — grep the LoadCoach suite, its fixtures, its goldens and its docs for
  that string before you rename, and if the blast radius is large, say so and keep the name with a
  comment rather than churning fixtures. Record the choice either way.
* The Gate A test now passes on the *fits* branch. Add its complement: with the shipped default and
  a realistically busy GPU, routing selects the fake candidate and the journey completes.

## 7. Gate C — requirement 2: the rejection must stay reachable on purpose

Add the configuration from §0.3, wire it through `build_provider`, and prove an operator can use it.

* Config validation refuses incoherent values with a `ConfigurationError` naming the field, in
  LoadCoach's existing style (see `build_provider`'s existing raise).
* **A test that sets the config and observes a real `insufficient_vram` rejection** with the whole
  `estimate` block populated — `estimated_bytes`, `free_bytes_by_gpu`, `headroom_bytes`,
  `estimate.weights_bytes`, `estimate.kv_bytes`, `estimate.kv_source`, `estimate.served_context`.
  `kv_source` must read `"theoretical"`, not `"unknown"`: a fake whose geometry you removed would
  produce `total_bytes=None` and an `unknown_reason`, which is a *different* rejection shape and not
  the diagnostic this row is protecting. Assert on that explicitly.
* **Do not exempt the fake provider kind from the constraint.** The row says so and it is right: an
  exemption stops the fake modelling the constraint at all, and a suite that cannot reproduce a real
  rejection is the thing this row exists to fix.
* Document the key where an operator will find it — the config surface documentation LoadCoach
  already keeps, and one line in `docs/apps/loadcoach/` if a mirrored file covers provider settings.

## 8. Gate D — docs

If (and only if) you touched a workspace `docs/` file, mirror it into `LoadCoach/docs/` and
`cmp`-prove byte-identity. Then, in `/home/jpk/ai/suite/docs`, one commit:

* Mark the **E6 row** done in `roadmap/outstanding-work.md` §1 in the house shape E4/E5 used —
  `**Done 2026-09-0X** (`docs/history/E6_HANDOFF.md`; commits …)` — and fold in §0.1 (the numbers are ModelRack's)
  and §0.2 (the KV term dominates), so the next reader inherits them.
* If `apps/loadcoach/routing.md` §4 gains a sentence about provoking the rejection, mirror it.

---

## 9. Exit conditions — all of these, demonstrably

1. The Gate A test reproduces `insufficient_vram` from the *pre-change* defaults against an injected
   busy-GPU snapshot, with `estimated_bytes` matching the §0.2 derivation.
2. With the shipped defaults, the fake provider is admitted against a snapshot with **≈1 GB free**,
   and a fake-provider journey completes — reproducible on any machine, GPU or not.
3. A named configuration produces `insufficient_vram` on a machine with plenty free, with the full
   `estimate` block and `kv_source == "theoretical"`.
4. **ModelRack is untouched** — `git -C py/ModelRack status --short` empty at the end.
5. The routing constraint code is unchanged in behaviour: no exemption, no new bypass, no change to
   the constraint order in `routing.md` §4.
6. Full gate green except exactly the three known evidence failures, named and counted.
7. LoadCoach clean and pushed, CI green; docs clean; every mirrored file `cmp`-identical.

## 10. Closing duties

1. Full gate, interpreter and exact invocation named (M5C-13), with the three known failures listed.
2. **`docs/history/E6_HANDOFF.md` at the workspace root**, house shape: the reproduction and its numbers; the
   before/after estimate table (weights / kv / activation / total); the §0.3 configuration decision
   with its reason; whether you renamed the fake model and what that touched; the commits; what F1
   inherits (a fake-provider journey that no longer depends on a free GPU); anything this row said
   that turned out not to be true.
3. Push LoadCoach and confirm CI green. Record any **model deviation** from the scheduled
   Sonnet 5 · standard for [model-assignment §3.5](docs/roadmap/model-assignment.md).

## 11. Stop rules

* **Do not edit `py/ModelRack`.** Not `_fake_script.py`, not `DEFAULT_MODEL`, not `testing.py`. If
  you become convinced ModelRack must change, **stop and write the handoff** saying why — that is a
  new row with a `modelrack` release attached, not a quiet addition to this one.
* **Do not exempt the `fake` provider kind from `insufficient_vram`**, and do not add a
  "skip constraints in tests" switch.
* **Do not touch LoadCoach's `setspec` pin** or the three evidence-golden failures — H4 owns both.
  Moving the pin turns a local-only red into a CI red.
* **Do not change the constraint order, the rejection vocabulary, or
  `RESOURCE_REJECTION_REASONS`.** If the fix appears to require it, that is a finding for the
  handoff, not a change.
* Do not bump LoadCoach's version, tag it, or publish anything.
* Never `git add -A`; never overwrite an unversioned workspace-root file; never leave a tree dirty at
  a boundary.

## 12. If you finish with capacity left

Do **not** start F1. Read-only, in priority order: (a) grep FreeWeight and IdeaPress for the same
zero-argument `FakeProvider()` construction and record in the handoff whether either is exposed to
the same GPU-dependence — they do not route on VRAM, so the answer is probably no, but "probably" is
not an answer someone should have to re-derive; (b) note in the handoff which of F1's Phase 5
journeys depend on the fake provider being admitted, so F1 knows what E6 bought it.
