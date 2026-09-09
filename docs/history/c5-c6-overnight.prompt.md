# Kickoff — C5 + C6 in one overnight run: ADR-0070, end to end

**Rows:** C5 and C6 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1,
run back-to-back in one session. They are the same-model tail of batch letter C, and §1 sanctions
exactly this: *"consecutive rows with one letter can be run back-to-back in one sitting."*
**Model:** **Opus 5 · high** — a deliberate upgrade from the schedule's *Sonnet 5 · high* (C5) and
*Sonnet 5 · standard* (C6). Reason below; **record the deviation in both handoffs** so
[model-assignment §3.5](docs/roadmap/model-assignment.md)'s distribution does not drift silently.
**Repositories:** `/home/jpk/ai/suite/py/ModelRack` (Python 3.13.15, coverage floor **95 %**), then
`/home/jpk/ai/suite/LoadCoach` (Python 3.14.4, coverage floor **85 %**), plus
`/home/jpk/ai/suite/docs` for C6's document amendments. Three repos, one session.
**Ships:** nothing. C5 rides `modelrack 0.7.0` at H1; C6 rides `loadcoach 1.1.0` at H2. No version
bump, no tag, no publish, **no push**.
**Overnight:** permitted. Neither row is on [§2.12](docs/roadmap/model-assignment.md)'s
never-overnight list (batches D, G, and I2's security half).

## The work is specified elsewhere — read both

This document is a **wrapper**. The work itself is specified, in full, in:

* [`docs/history/c5-modelrack-usage-rule.prompt.md`](c5-modelrack-usage-rule.prompt.md)
* [`docs/history/c6-loadcoach-token-classes.prompt.md`](c6-loadcoach-token-classes.prompt.md)

Read them in that order and follow them as written — reading lists, work sections, closing duties,
stop rules — **except where this document overrides them.** It overrides them in exactly three
places, all of them machine facts that changed or were mis-stated, and every override is marked
**OVERRIDE**. Where this document is silent, the per-row prompt governs.

## Why one session, and why Opus 5 · high

**Why they combine.** The coupling is looser than the table implies: C6 transcribes ADR-0070
decision 7, not C5's code, and `baseaicore.TokenUsage` has carried all four classes since 0.4.0,
so no ModelRack surface change reaches LoadCoach. [§3](docs/roadmap/outstanding-work.md)'s
hard-edge list names *C5 before D3* and *C6 before F1* — **not** C5 before C6. Both rows are small:
C5 is two ~15-line functions plus the fake, five test assertion sites and fixtures; C6 is two
nullable columns on two tables in one migration.

**Why Opus, when both rows are Sonnet on the schedule.** Not because the transcription is hard —
ADR-0070 decisions 1–7 are a specification, which is [§3.4](docs/roadmap/model-assignment.md)'s
case for the cheaper model. Three things together justify the upgrade for *this run*:

1. **[§3.2](docs/roadmap/model-assignment.md)'s mitigation is unavailable when it is needed.** The
   guide's answer for a contract-touching Sonnet row is "Sonnet writes, Opus reviews the diff
   before the phase closes." Overnight, §2.12 voids that until morning. Running the writing pass at
   the reviewing tier buys back the pass that cannot happen live.
2. **The conformance seam is a first-instance artifact.** C5 §5 asks you to design the seam so D3's
   `LlamaCppProvider` slots in by *declaring* its three response shapes rather than by rewriting
   the tests. That is [§3.1](docs/roadmap/model-assignment.md)'s first-instance rule, and it is the
   one piece of genuine design in either row.
3. **The failure mode is silent.** A fabricated zero passes a green test suite and surfaces as a
   quietly-wrong cost estimate in the safe-looking direction, in a package three applications call.

**What Opus does not buy you.** It does not remove
[outstanding-work §4](docs/roadmap/outstanding-work.md)'s morning diff review, and it does not
license scope. If anything, the higher tier makes the stop rules matter more: a stronger model is
better at talking itself into a fix that was never in the row.

---

## OVERRIDE 1 — Ollama is installed and running on this machine

The C5 prompt's preconditions say *"There is no Ollama and no live provider on this machine."*
**That is no longer true.** Verified at the time of writing:

```text
/usr/local/bin/ollama          server 0.32.13, answering on http://localhost:11434
GPU                            NVIDIA GeForce RTX 5060 Ti
models                         14 installed; the smallest is `gemma3:latest` (3.3 GB)
```

This bears on **ADR-0070 decision 3** only — the question of whether Ollama's `prompt_eval_count`
counts only the tokens evaluated when its KV cache reused a prefix. The ADR says the answer must be
verified before it is asserted, and a recorded fixture cannot answer a question about two requests
sharing a prefix. It can now be answered directly, and **you are authorised to answer it**, under
these bounds:

* **One model — `gemma3:latest` (3.3 GB)** — loaded once. Two requests that share a long prefix and
  differ only in their tail, issued back-to-back against the same loaded model. Compare
  `prompt_eval_count` between them. That is the whole experiment.
* **Hard cap: 15 minutes**, including model load. If it is not settled by then — the daemon is
  busy, a load fails, the numbers are ambiguous — **stop and take the C5 prompt's conservative
  path**: a `live`-marked test that would settle it, a docstring that states what the field is,
  what it may mean and which reading the adapter assumes, and an operator step in the handoff.
* **The default suite must still pass with no Ollama installed** (spec §20 criterion 3). Anything
  that needs the daemon is `live`-marked and outside `pytest -m "not live and not performance"`.
  This is not negotiable and the capture does not change it.
* **Record the captured numbers verbatim in `docs/history/C5_HANDOFF.md`** — both `prompt_eval_count` values,
  the prompts' shapes, the model and the Ollama version — and say plainly whether they settle the
  question or merely fail to contradict it. The one thing you must not do is write a confident
  docstring backed by an experiment you did not actually run.
* If a FreeWeight benchmark run is in progress on this machine, **skip the capture entirely** and
  take the conservative path — [outstanding-work §3](docs/roadmap/outstanding-work.md)'s resource
  rule: GPU sessions never share the machine with FreeWeight benchmark runs.

*To strike this experiment: delete this OVERRIDE and the session falls back to the C5 prompt's
conservative path, which is complete on its own.*

---

## OVERRIDE 2 — every suite dependency in LoadCoach's venv is an editable pointing at the working trees

The C6 prompt says the LoadCoach venv "has `0.5.0` installed" and tells you not to reach for an
editable ModelRack install. **The editable link is already there, and it is not just ModelRack.**
Verified:

```text
LoadCoach/.venv/…/_editable_impl_{baseaicore,setspec,modelrack,sweatmeter,weightsdb,mirrorwall}.pth
import modelrack  →  /home/jpk/ai/suite/py/ModelRack/src/modelrack/__init__.py
pip metadata says modelrack 0.5.0 / setspec 0.3.0 — the metadata is stale, the code is live
```

Three consequences, and the third is the one that will bite:

* **C5's edits are live in LoadCoach's test suite the moment you make them.** You do not need to do
  anything to connect them, and you cannot easily disconnect them.
* **Do not run `pip install -e ".[dev]"` in LoadCoach.** The C6 prompt's setup block says to; do
  not. The venv is already provisioned, and pip would see `setspec` claiming 0.3.0 against the
  `setspec>=0.4,<0.5` pin and **replace the editable link with a PyPI wheel**, silently changing
  what the whole workspace's LoadCoach venv resolves. Snapshot instead:

  ```bash
  source .venv/bin/activate
  ls .venv/lib/python*/site-packages/_editable_impl_*.pth   # before and after; must be identical
  python -c "import modelrack; print(modelrack.__file__)"   # must be the ModelRack working tree
  ```

  If something is genuinely missing and the suite will not run, **stop and report** rather than
  resolving it. The ModelRack venv is ordinary — only `modelrack` itself is editable, `baseaicore`
  comes from PyPI — so the C5 prompt's setup block stands unchanged for that repo.
* **CI does not have any of this. `requirements/ci.lock` pins `modelrack==0.5.0`,** and CI installs
  from the hash-pinned lock and then the package with `--no-deps` (Packaging Standards §4). So
  **any C6 test whose expected value depends on C5's new behaviour passes here and fails in CI** —
  it would be tested against a modelrack two minors older than the one you just edited. This is the
  single most likely way this run ends with a green local gate and a red morning.

  **The rule: every required C6 test constructs the `TokenUsage` it needs directly.** No C6 test
  reaches through a real ModelRack adapter for its expected values. The C6 prompt already says
  "construct the `TokenUsage` you need in the test" — that instruction is now load-bearing rather
  than advisory, and it holds for the whole row.

  You may, **once**, run a deliberate end-to-end sanity check through the live editable ModelRack
  to see a real adapter's cache classes land on LoadCoach's wire as `0`. Do it as a scratch check,
  **do not commit it as a test**, and report what you saw in `docs/history/C6_HANDOFF.md` as evidence for F1.
  If it disagrees with the constructed-`TokenUsage` tests, that is a finding, and it is the most
  valuable thing this run could produce.

---

## OVERRIDE 3 — the checkpoint between the rows is hard

C5 reaches a **green gate and a Conventional Commit on `main` in `py/ModelRack` before a single
LoadCoach or `docs/` file is opened.** No interleaving, no "I'll come back to that fixture."

If C5's gate is not green, or the conformance seam is not settled, or you are carrying an unresolved
question about the empty-`usage` semantics or the `cached_tokens > prompt_tokens` clamp:
**stop there.** Write `docs/history/C5_HANDOFF.md`, state exactly where you stopped, and **do not start C6.**
C6 is not blocked by an unfinished C5 — it is a separate row in a separate repo that transcribes an
ADR — but starting it on the back of an unsettled reading of that same ADR is how one bad morning
becomes two.

Between the rows, run `git status --short` in `py/ModelRack` and confirm it is empty before you
`cd` anywhere. Start C6 by reading its prompt from the top as if it were a fresh session; if your
context has been compacted by then, that re-read is the recovery.

---

## Closing duties for the combined run

Both per-row prompts' closing duties apply **in full and separately** — this is two rows, and the
morning review is per repo:

1. **`docs/history/C5_HANDOFF.md`** and **`docs/history/C6_HANDOFF.md`**, each with the sections its own prompt lists. Add to
   each: **"Ran on Opus 5 · high rather than the scheduled Sonnet tier, combined with the adjacent
   row in one overnight session"**, with a sentence on whether that showed anywhere in the work —
   the next scheduler wants to know whether the upgrade earned its keep.
   **Never overwrite an existing root file** — the workspace root is not a git repository. If
   either exists, write `Cn_HANDOFF.2.md` and say why.
2. `docs/history/C5_HANDOFF.md` additionally carries the Ollama capture: the numbers, or why you took the
   conservative path.
3. `docs/history/C6_HANDOFF.md` additionally carries the editable-venv finding, the `.pth` snapshot before and
   after, the `modelrack==0.5.0` lock and what it means for the CI run, and the result of the
   one-shot end-to-end check.
4. **One summary in chat** covering both rows: what changed in each repo, what each gate said with
   the interpreter named, every decision made where the ADR left an edge, and what is waiting on
   the operator.

## Combined stop rules

Both prompts' stop rules apply. These bind across the whole session:

* **Nothing is pushed, tagged, published or version-bumped.** Commit on `main` in each repo and
  stop. Three repos means three independent commit streams; never `git add -A`.
* **Never fabricate a zero.** Zero is honest only where the wire protocol cannot bill the class.
  If you find yourself writing `0` for a class the protocol *can* express and this response did not
  report, stop — that is the fabricated zero ADR-0016 forbids and ADR-0070 does not license.
* **Additive only in LoadCoach.** No field removed, no existing field's type changed, no `/api/v2`.
  The `null` vs `"unsupported"` inconsistency on `input_tokens`/`output_tokens` is a **finding for
  the handoff**, not a fix in this session.
* **Do not resolve the stale pins** (`modelrack>=0.5,<0.6`, `setspec>=0.4,<0.5`) or re-resolve the
  lock. Both belong to H2, which is the row that bumps LoadCoach. Record them.
* **Do not touch ModelRack once C5 is committed.** If C6 makes you want a ModelRack change, that is
  a finding, not a second bite.
* **Do not reflow the markdown you edit.** Amend the lines that change, leave the rest byte-for-
  byte, and prove the mirror with `cmp` (`CLAUDE.md`, working-tree integrity).
* **Never weaken `.importlinter`** in either repo to make an import work.
* **If you must stop early, stop at a green gate with a commit and a clean tree**, in whichever
  repo you are in, and record exactly where you stopped.
