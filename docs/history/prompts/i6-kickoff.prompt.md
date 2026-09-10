# Kickoff — I6: the thinking control on Ollama, and the stream that ends without a terminal chunk

**Row:** I6 (Sonnet 5 · high) of [`docs/roadmap/outstanding-work.md`](../../roadmap/outstanding-work.md)
§1, which absorbed the row once scheduled as I7.
**Component:** `/home/jpk/ai/suite/py/ModelRack` — `src/modelrack/providers/ollama.py` — plus a
measurement table that lands in `docs/`. **May end in documentation and no code**; see the stop
rules.
**Ships:** nothing, unless the parser is guilty. If it is, `modelrack 0.7.2` on top of `0.7.1`
(`2163e7d`, released).

**Nothing waits on this row.** No task profile in the suite sets `think` today — LoadCoach
`cb1cfac` kept the five harness profiles unset, on I3's measurement — so no release
and no other row is blocked by either half. That is what makes it safe to run last, and what makes
"the parser is innocent, here is the table" an acceptable outcome.

**Overnight:** this row drives the GPU through ~20 streamed generations and roughly 94 GB of model
loads. It is safe to run unattended in the sense that nothing it does is destructive — the probe
writes no code and changes no profile — but a wrong call about the defect is a fix in the wrong
place, so if the evidence does not separate the two causes, **say so and stop** rather than
choosing one.

**Concurrency.** Rows I8 + I9 may be running in another session against the same workspace. They
touch `LoadCoach`, `PromptCadence` and `docs/`; you touch `py/ModelRack` and `docs/`. If that
session is running: **do not run the preamble's `git checkout -- <path>` cleanup in `docs/`** — you
would destroy its uncommitted work — touch only the `docs/` files this prompt names, and expect
your own heavy model loads to slow its test runs (say so if it matters).

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.**
  `/home/jpk/ai/suite/py/ModelRack`, its own `.venv/bin/python`. `pip install -e ".[dev]"` if
  anything is missing.
* **House method:** docstring-first, `from __future__ import annotations`, units in every numeric
  name, keyword-only for anything optional or boolean, injected clocks and transports, line length
  100, `mypy --strict`, no `# type: ignore` without a trailing reason.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` green, plus `pytest --cov` at or above the 95 % floor
  (shared package). **Name the interpreter and the exact invocation in the handoff** (M5C-13).
* **Live work is marked.** Anything that needs Ollama is a `live`-marked test or a scratchpad
  script, never part of the default suite (spec §18). The default suite must stay green with no
  network and no GPU.
* **Documentation is mirrored.** Edit the workspace copy under `/home/jpk/ai/suite/docs/` first,
  then copy byte-identically into the component's own `docs/`, and verify with `cmp`.
* **Do not push, do not tag, do not publish.** Standing instruction of 2026-09-04.
* **Run `git status --short` at the start and at the end** in every repo you touch.

---

## What this row is

Two halves that share one machine and one lever, merged into one row on 2026-09-06 because **the
probe is the defect's reproduction harness**.

**(a) The probe, read-only.** [ADR-0099](../../adr/0099-a-task-profile-may-ask-for-reduced-thinking.md)
made `execution.think` reachable from a task profile, and routing enforces that a candidate's
provider can carry it. What it cannot enforce is whether the *model* honours it. I3 measured one:
**gpt-oss:20b accepts Ollama's `think: false` and ignores it** — a non-streaming call still came
back with a populated `thinking` field, and a streaming call with `think: false` and
`format: json` emitted the reasoning as **`content`** ("The user says: …") instead of on the
thinking channel, which then fails `require_valid_json`. The control reaches the model; the model
relocates its reasoning into the answer. An operator reaching for `think = false` needs to know
which of their models does that, and today nothing tells them.

**(b) The defect, with the probe's runs as its sample.** In I3 gate D, **four of six** streamed
`POST /api/chat` requests carrying top-level `think: false` to gpt-oss:20b on Ollama `0.32.13`
failed after ~1.3 s with:

```text
ProviderProtocolError: The stream from http://127.0.0.1:11434 ended without a terminal chunk.
```

while a hand-made stream of the same body completed normally with `done: true` and
`done_reason: stop`. Two candidate causes with different fixes: `OllamaProvider`'s stream parser
drops or mis-reads a mid-stream error object, **or** Ollama genuinely closes the stream. Fix the
first; document the second and say what a caller sees.

## Reading list

1. [`history/handoffs/I3_HANDOFF.md`](../handoffs/I3_HANDOFF.md) **§4** (the measurement, the four-cell table, and the
   direct-probe finding) and **§9** (the finding handed to this row, in its own words).
2. [`adr/0099-a-task-profile-may-ask-for-reduced-thinking.md`](../../adr/0099-a-task-profile-may-ask-for-reduced-thinking.md)
   — rules 2–5: the three states, the override, and why `thinking_control` is a provider flag
   rather than a capability.
3. [`apps/loadcoach/routing.md`](../../apps/loadcoach/routing.md) §2, lines around the
   `think = false` example — the paragraph an operator reads before setting it, and where the
   probe's table belongs (D1).
4. `py/ModelRack/src/modelrack/providers/ollama.py` — the streaming path and its raise site
   (`:960` on 2026-09-07, `"The stream from … ended without a terminal chunk."`).
5. [`packages/modelrack/spec.md`](../../packages/modelrack/spec.md) — `SamplingParameters.think`,
   `ProviderCapabilities.thinking_control`, and `GenerationResult.thinking`.

## The ground, already checked — do not spend the session rediscovering it

* **Ollama is `0.32.13`** and **ten models are installed**, about 94 GB in total:
  `gpt-oss:20b`, `qwen3.5:9b-q8_0`, `gemma4:12b-it-q8_0`, `deepseek-coder-v2:latest`,
  `sorc/qwen3.5-heretic:9b`, `SetneufPT/Qwen3.5-9B-Coder_Q4_256k_ABL_16GB-GPU:latest`,
  `ornith:9b`, `hk:latest`, `HammerAI/gemma-4-e4b-heretic:e4b-q8_0`,
  `fredrezones55/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:IQ2_M`.
  Twenty streamed requests at two cells each is a lot of loading — **cap the set to what a tier
  could plausibly route to, or unload between models**, and say in the handoff which you probed and
  why the others were left out.
* `modelrack 0.7.1` is released and `main` is clean. The row before it (`5323a12`) is unrelated.
* The `think` control is ModelRack's `SamplingParameters.think`, tri-state; Ollama sends its own
  top-level `think`, and llama.cpp / OpenAI-compatible raise `CapabilityUnsupported` naming
  `thinking_control` (ADR-0099 rule 2).
* I3's failure was **through a real LoadCoach**, not straight through Ollama — so a reproduction
  that goes straight to Ollama is a *different* path, and must be stated as such if the two
  behave differently.

## The decisions this row makes

### D1 — where the probe's table lives

It has to be where the next person reaching for `execution.think` will read it, not only in a
handoff. **Recommendation:** a short table in
[`apps/loadcoach/routing.md`](../../apps/loadcoach/routing.md) §2, immediately after the paragraph
that explains the three states — that is the document an operator has open when they set the field
— with the full run log in the handoff. Mirror it into `LoadCoach/docs/apps/loadcoach/routing.md`
and `cmp`-verify. If you would rather put it in `packages/modelrack/spec.md`, argue it: the
counter-argument is that the fact is about *models*, not about ModelRack's contract.

### D2 — what the table records per model

**Recommendation, one row per model probed:** the model id (`provider/name@sha256:digest` where
you have it, else the Ollama tag), `think: true` → where the reasoning went, `think: false` → where
it went, whether `thinking` was populated, whether `content` carried reasoning text, and whether a
`format: json` request still parsed. Two streamed requests per model; state the prompt used, and
use **one** prompt for every model so the column means the same thing everywhere. A model that
behaves differently non-streamed than streamed gets a note, not a second table.

### D3 — the verdict on the stream failure, and what it costs

Three possible outcomes, and the row must land on exactly one, with evidence:

* **The parser is guilty** — it drops or mis-reads a mid-stream object (an error object, a
  `done: false` final chunk, a keep-alive, a split JSON line across reads). Fix it, add a
  regression test over a **recorded** byte stream (no network in the default suite), and cut
  `modelrack 0.7.2`.
* **Ollama is closing the stream** — then the exception is honest, and the work is documentation:
  say what a caller sees, whether ModelRack should distinguish "closed early" from "protocol
  violation" in the message, and whether LoadCoach's retry classification treats it correctly
  (a stream that dies at 1.3 s in four of six runs is a *retryable* provider failure, and if
  LoadCoach does not retry it, that is a finding for another row).
* **The evidence does not separate them** — say so, record what would, and stop. A guess here is a
  fix in the wrong repository.

**Recommendation for reproducing:** capture the raw bytes first — a scratchpad client that streams
`POST /api/chat` with `think: false` and `format: json` to gpt-oss:20b and writes every chunk to a
file, run until it fails — and only then read the parser against what actually arrived. I3's own
hand-made stream completed normally, so the difference is in what the model emits under that body,
not in the transport.

## The work, in gate order

**Gate A — the probe.** A scratchpad script (not committed to `src/`), two streamed requests per
probed model, the raw responses saved under the session scratchpad. Changes no code, no task
profile, no configuration. Ends in the table (D1, D2) and its commit.

**Gate B — the capture.** The failing stream's raw bytes, recorded. If it will not reproduce,
record how many attempts were made under what body, and go to the stop rule.

**Gate C — the verdict.** D3, with the evidence in the handoff. If the parser is guilty:
the fix, plus a regression test over the recorded bytes, plus `CHANGELOG.md`, plus the full gate.
If it is not: the documentation, and no version bump.

**Gate D — the release, only if Gate C produced a fix.** `CHANGELOG.md` `[Unreleased]` →
`## [0.7.2]`, `src/modelrack/__about__.py` → `0.7.2`, full gate plus `pytest --cov`, commit
`chore(release): modelrack 0.7.2`. **Stop there.**

## Stop rules

* The probe changes no task profile and no code. If a probed model's behaviour suggests a profile
  should change, that is a LoadCoach row, not this one.
* If the parser proves innocent, the row ends in documentation — do not "harden" the parser to feel
  productive. A speculative change to a streaming path nobody has proven wrong is how an
  intermittent failure becomes two intermittent failures.
* If the probe cannot be completed (thermal, disk, a model that will not load), probe fewer models
  and say which and why. A partial table with its gaps named is worth more than a delayed one.
* No live test enters the default suite. Anything needing Ollama is `live`-marked.

## Exit conditions

1. The default gate is green on a named interpreter, coverage at or above the floor, with **no
   network and no GPU** — whatever this row concluded.
2. The table exists where D1 put it, mirrored and `cmp`-clean, and names every model probed and
   every model skipped.
3. The stream failure has exactly one verdict, with the evidence that produced it: a fix and a
   regression test over recorded bytes, or a documented refusal with what a caller sees, or a
   stated inability to separate the causes.
4. `git status --short` clean in every repository touched, work committed, nothing pushed.

## The handoff

`docs/history/handoffs/I6_HANDOFF.md`, in the house shape:

1. Gate results with the exact invocations and the interpreter.
2. The gates as commits.
3. **The three decisions** (D1–D3), each with what the losing option would have claimed. D3 is the
   one a reviewer reads first: state the evidence before the verdict.
4. **The probe's full run log** — every model, both cells, what each returned — beneath the
   summary table.
5. Exit conditions, answered one by one.
6. Things this prompt said that turned out not to be true (line numbers were read on 2026-09-07).
7. What the operator still has to do — tag and publish `modelrack 0.7.2` if a fix landed; nothing
   if it did not.
8. Anything found that belongs to another row: in particular whether LoadCoach retries the stream
   failure as the transient provider error it appears to be, and whether any probed model's
   behaviour should change a shipped task profile.

## Constraints

* **ModelRack only.** LoadCoach's profiles, PromptCadence's tiers and the harness are out of scope,
  however tempting a one-line profile edit looks.
* **No new capability flag.** `thinking_control` is ADR-0099's, and what the model *does* with the
  control is a fact about the model, not a provider capability.
* **A model is never a test oracle.** The probe records what came back; it does not judge quality.
* **Never weaken `.importlinter`.**
* If the work must stop early, stop at a green gate with a commit, and say exactly where you
  stopped and what remains.
