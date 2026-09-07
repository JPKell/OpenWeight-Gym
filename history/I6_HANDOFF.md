# I6 — the thinking control on Ollama, and the stream that ends without a terminal chunk

**Row:** I6 of `roadmap/outstanding-work.md` §1 (it absorbed the row once scheduled as I7).
**Model:** scheduled Sonnet 5 · high; ran on **Claude Opus 5** (model-assignment §3.5 — recorded,
not a split), whole, in one session. **Date:** 2026-09-07.
**Interpreter:** Python 3.13.15 at `/home/jpk/ai/suite/py/ModelRack/.venv/bin/python` for every
gate, every probe and every capture.
**Ships: nothing.** The parser is innocent, so there is no `modelrack 0.7.2`; `modelrack` stays at
`0.7.1` (`2163e7d`). The row ends in documentation, which is the outcome the kickoff named as
acceptable.

**Repositories touched:** `docs` (one commit), `LoadCoach` (one commit, the `routing.md` mirror)
and `py/ModelRack` (one commit, the `spec.md` mirror). All three were clean at the start —
`docs` at `834c9ab`, `LoadCoach` at `2a7ac58`, `ModelRack` at `2163e7d` — and all three are clean
at the end with the new work committed and unpushed. **No source file changed in any repository.**
No `git push`, no push dry-run, no tag. The I8/I9 session was not running: `docs` and `LoadCoach`
were clean at the start and again immediately before these edits, so the preamble's cleanup was
never needed and nothing of another session's was touched.

---

## 1. Gate results, with the exact invocations

No code changed, so the gate is the unchanged suite proving it. Run from
`/home/jpk/ai/suite/py/ModelRack`:

```bash
.venv/bin/python -V                      # Python 3.13.15
.venv/bin/ruff format --check .          # 57 files already formatted
.venv/bin/ruff check .                   # All checks passed!
.venv/bin/python -m mypy src tests       # Success: no issues found in 51 source files
.venv/bin/lint-imports                   # Contracts: 2 kept, 0 broken.
.venv/bin/python -m pytest -m "not live and not performance" -q
                                         # 1433 passed, 16 skipped, 26 deselected in 6.54s
.venv/bin/python -m pytest --cov --cov-report=term-missing -m "not live and not performance" -q
                                         # Total coverage: 99.82% (floor 95 %)
```

No network and no GPU: the whole probe lives in the session scratchpad and nothing from it entered
`tests/`. **No live test was added.** A live test here would assert that Ollama misbehaves, which
is a test of Ollama, not of ModelRack — and the verdict below is that ModelRack's behaviour under
that misbehaviour is already correct and already covered.

## 2. The gates as commits

| Gate | What it was | Commit |
|---|---|---|
| A — the probe | Ten models, two streamed requests each, the table | `docs` + `LoadCoach` mirror, below |
| B — the capture | Twelve raw byte streams recorded outside ModelRack | scratchpad only, by design |
| C — the verdict | Ollama closes the stream; documentation, no fix | `docs` + `ModelRack` mirror, below |
| D — the release | **Not reached.** Gate C produced no fix | — |

Gates A and C landed as one commit per repository rather than one per gate: neither changes code,
both edit the same two documents' neighbourhood, and splitting them would have put the table and
the verdict it rests on in separate commits.

## 3. The three decisions

### D1 — the probe's table lives in `apps/loadcoach/routing.md` §2

**Taken as recommended**, immediately after the paragraph explaining `execution.think`'s three
states, and mirrored byte-identically into `LoadCoach/docs/apps/loadcoach/routing.md`.

*What the losing option would have claimed:* that `packages/modelrack/spec.md` is the right home
because ModelRack is what sends the key. It is not, and the kickoff's own counter-argument is the
reason — the fact is about **models**, not about ModelRack's contract, and ModelRack's contract is
identical whichever way a model behaves. The operator who needs the table is the one editing
`execution.think` in a task profile, and `routing.md` §2 is the document open in front of them.
A second, smaller edit *did* go to `spec.md`, and it is a different fact: what the
`ProviderProtocolError` row means when a caller hits it (§3, D3).

**One deviation from D2's recommendation, stated because it is a deviation.** The table names each
model by its **Ollama tag**, not `provider/name@sha256:digest`. The digests exist and are recorded
in §4 below; putting a 64-character digest in an operator-facing table makes it unreadable, and the
tag is what an operator types. The digests as `/api/tags` reported them:

```text
gpt-oss:20b                                                          sha256:17052f91a42e…
qwen3.5:9b-q8_0                                                      sha256:441ec31e4d2a…
sorc/qwen3.5-heretic:9b                                              sha256:0b34f914eac4…
SetneufPT/Qwen3.5-9B-Coder_Q4_256k_ABL_16GB-GPU:latest               sha256:8d7f60bdc09d…
fredrezones55/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:IQ2_M   sha256:423c4a0ed6fb…
gemma4:12b-it-q8_0                                                   sha256:41c402fdddc2…
ornith:9b                                                            sha256:a75697c14589…
hk:latest                                                            sha256:3bbf71189af5…
HammerAI/gemma-4-e4b-heretic:e4b-q8_0                                sha256:42ae73d6e12a…
deepseek-coder-v2:latest                                             sha256:63fb193b3a9b…
```

### D2 — one prompt, two cells, ten models, nothing skipped

**Taken as recommended, and the "cap the set" escape was not needed.** All ten installed models
were probed, `think: true` then `think: false`, two streamed `POST /api/chat` requests each, twenty
generations in about 11 minutes of GPU time — cheaper than the kickoff feared because
`keep_alive: 0` rides on each model's second request, so each model is loaded once and unloaded
before the next. **No model was skipped**, so the kickoff's "say why the others were left out" has
no content.

The one prompt, used unchanged for every model and every cell: PromptCadence's `planner.draft`
`1.1.0` record, read from `PromptCadence/src/promptcadence/prompts/planner/draft.v1.json` and
rendered in I3 gate D's shape by a scratchpad script — the **287-character** system turn verbatim
(identical to I3's and G2's) and the template filled with I3's shape: a repository-reading task,
`internal`, five tools as name plus first sentence, three tiers, `max_steps = 20`. **The user turn
came out 1 976 characters, not I3's 1 942**, for I3's own reason: the tool briefs and tier lines
are reconstructed rather than captured from a live render. Every cell used the same string, so the
columns mean the same thing everywhere; the absolute number is not I3's.

The request body around it is `tools.plan`'s execution block: `format: "json"`,
`options.temperature = 0.1`, `options.num_predict = 4096`, `stream: true`, no `tools` key.

*What the losing option would have claimed:* that a short synthetic prompt would isolate the
control better. It would have isolated it out of existence — the defect this row also had to
reproduce only appears under a prompt long enough to make the model reason, and using one prompt
for both halves is what made the probe double as the reproduction harness.

### D3 — **Ollama closes the stream. The parser is innocent. No fix, no 0.7.2.**

**The evidence, before the verdict.**

*Capture, outside ModelRack entirely* (gate B). A scratchpad `httpx` client streamed the failing
body straight to `http://127.0.0.1:11434/api/chat` and wrote every raw read to a file with a
millisecond offset — no ModelRack code in the path at all. Six runs with `think: false` and
`format: "json"`, six with `think` unset:

| Cell | Runs | `done: true` seen | How the stream ended |
|---|---|---|---|
| `think: false` + `format: "json"` | 6 | **0 / 6** | Clean chunked EOF, HTTP 200, `content-type: application/x-ndjson` |
| `think` unset + `format: "json"` | 6 | **6 / 6** | Clean chunked EOF, terminal chunk present |

Every line in every failing stream was valid JSON and a well-formed object. The last thing five of
the six failing streams delivered was an ordinary content delta:

```json
{"model":"gpt-oss:20b","created_at":"…","message":{"role":"assistant","content":" "},"done":false}
```

and then the body ended. The sixth ended with Ollama's own error object instead:

```json
{"error":"error parsing tool call: raw='{\":\":\"  }', err=unexpected end of JSON input"}
```

*Through ModelRack's own `OllamaProvider`* — the same body, built by `SamplingParameters(think=
False)` and `ResponseFormat(kind=JSON)`, three runs:

```text
run 0: StreamFailed ProviderProtocolError code=PROVIDER_PROTOCOL_ERROR
       :: The stream from http://127.0.0.1:11434 ended without a terminal chunk.
       partial_text[:120]='We need to produce a plan. The task: ": 1.1        …'
run 1: StreamCompleted finish=stop text[:80]='We need to produce a plan to read repository at …'
run 2: StreamCompleted finish=stop text[:80]='We need to produce a plan to read repository at …'
```

I3's exact message, reproduced, with the reasoning sitting in `text` on the two runs that did
complete — I3's "two exhausted all three attempts on invalid JSON", seen from below.

**The verdict.** The parser is not guilty of any of the four things it was suspected of. It does not
drop a mid-stream error object — `extract_error_message` reads `{"error": …}` on every line and
turns it into a typed `StreamFailed`, which is exactly what happened on the one run of six that
carried one. It does not mis-read a `done: false` final chunk — there is no final chunk to
mis-read. It does not mis-handle a split JSON line — `httpx.Response.iter_lines()` reassembles
across TCP reads before `iter_capped_lines` ever sees a line, and every captured line parsed. And a
transport-level truncation would have surfaced as `httpx.RemoteProtocolError` through
`translate_stream_interruption`, not as this message: **reaching "ended without a terminal chunk" at
all requires the stream to have ended cleanly**, which the capture confirms independently.

*What the losing options would have claimed.* "The parser is guilty" would have claimed a defect in
a streaming path that the raw bytes exonerate, and its fix — some tolerance for a stream with no
terminal chunk — would have meant fabricating a `GenerationResult` out of a truncated answer, which
is `Unsupported is not zero` (ADR-0016) wearing a different hat. "The evidence does not separate
them" would have claimed the capture was ambiguous; it is not, because it was taken with no
ModelRack in the path and shows the absence of a terminal chunk directly.

**What a caller sees, and why the message stays as it is.** `stream()` yields
`StreamFailed(ProviderProtocolError("The stream from <base_url> ended without a terminal chunk."))`
with `partial_text` carrying everything that did arrive. The kickoff asked whether ModelRack should
distinguish "closed early" from "protocol violation" in that message. **It should not, and it
already does not conflate them**: a transport-level truncation is a different exception through a
different translator, a mid-stream error object is the provider's own message verbatim, and this
message is reached only by the third case — a well-formed stream that simply stopped. The sentence
is literally what happened. What was missing was not a distinction but a *reader*, so
`packages/modelrack/spec.md`'s error row now says what the message means and names the measurement.
**No code changed**, per the kickoff's stop rule against hardening a path nobody has proven wrong.

**Not a LoadCoach finding, checked rather than assumed.** `LoadCoach/src/loadcoach/domain/
retry_policy.py:105` maps `ProviderProtocolError` to `FailureKind.PROTOCOL`, and `next_action`
answers `RETRY_SAME` with reason `protocol_error` up to `PROTOCOL_ERROR_RETRIES`, then
`FALLBACK` with `protocol_error_retries_exhausted`. That is the treatment the kickoff said a
retryable provider failure deserves, so **there is nothing to file**. Worth one sentence for
whoever reads I3's table again: the retries do not help here because the failure is deterministic
for the body, not intermittent — 6 of 6 straight to Ollama — so on `tools.plan` with
`think = false` LoadCoach spends its protocol retries and falls back, which is precisely the
0 / 6 delivered that I3 measured.

## 4. The probe's full run log

Ten models, two cells each, twenty streamed generations, all under the body in D2. `tc` is
`thinking` characters accumulated, `cc` is `content` characters, `json` is whether the accumulated
`content` parses as JSON, `calls` is tool calls emitted. Raw NDJSON per cell is in the session
scratchpad at `i6/probe/<model>__think-<bool>.raw`.

```text
model                                    think  status done/reason      tkey   tc     cc  json calls  end            wall
gpt-oss:20b                              True   200    True/stop        True  2424     0  —     1     clean-eof      8341ms
gpt-oss:20b                              False  200    False/—          False    0   329  False 0     error-object   1753ms
qwen3.5:9b-q8_0                          True   200    True/length      True 15988     0  —     0     clean-eof    100735ms
qwen3.5:9b-q8_0                          False  200    True/stop        False    0  1106  True  0     clean-eof      6877ms
sorc/qwen3.5-heretic:9b                  True   200    True/length      True 15036     0  —     0     clean-eof    103408ms
sorc/qwen3.5-heretic:9b                  False  200    True/stop        False    0  1345  True  0     clean-eof      8387ms
ornith:9b                                True   200    True/stop        True   288   721  True  0     clean-eof      9248ms
ornith:9b                                False  200    True/stop        False    0   251  True  0     clean-eof      1109ms
SetneufPT/Qwen3.5-9B-Coder_Q4_256k_ABL…  True   200    True/length      True 13617     0  —     0     clean-eof     62628ms
SetneufPT/Qwen3.5-9B-Coder_Q4_256k_ABL…  False  200    True/stop        False    0   778  True  0     clean-eof      3106ms
fredrezones55/Qwen3.6-35B-A3B-Uncens…    True   200    True/length      True 14941     0  —     0     clean-eof     47837ms
fredrezones55/Qwen3.6-35B-A3B-Uncens…    False  200    True/stop        False    0  1104  True  0     clean-eof      3144ms
gemma4:12b-it-q8_0                       True   200    True/length      True 12250     0  —     0     clean-eof    205189ms
gemma4:12b-it-q8_0                       False  200    True/stop        False    0  1026  True  0     clean-eof     15840ms
hk:latest                                True   200    True/stop        True  2713   611  True  0     clean-eof     21286ms
hk:latest                                False  200    True/stop        False    0   243  True  0     clean-eof      1407ms
HammerAI/gemma-4-e4b-heretic:e4b-q8_0    True   200    True/stop        True  1902   817  True  0     clean-eof     14765ms
HammerAI/gemma-4-e4b-heretic:e4b-q8_0    False  200    True/stop        False    0   243  True  0     clean-eof      1403ms
deepseek-coder-v2:latest                 True   400    False/—          False    0     0  —     0     error-object     32ms
deepseek-coder-v2:latest                 False  —      False/—          False    0     0  —     0     RemoteProtocol 12556ms
```

Two rows need their own words.

**`gpt-oss:20b`, `think: false`.** `content` opened with
`"We need to produce a plan to read repository at /home/jpk/ai/suite/PromptCadence and write a
short note naming the three files a new contributor should read first and why. We need "` — the
reasoning, on the answer channel, with no `thinking` key present anywhere in the stream. This is
I3's finding, confirmed on a second occasion and a different path. Under `think: true` the same
model put 2 424 characters on the thinking channel, left `content` empty and emitted one tool call
(`repo_browser.list_dir`) — so the control **reaches** the model and the model **relocates** rather
than suppresses.

**`deepseek-coder-v2:latest`, `think: false` — it takes the Ollama server down.** `think: true` is
refused cleanly: HTTP 400, `"deepseek-coder-v2:latest" does not support thinking`. `think: false`
is *not* refused: the request is accepted, the runner dies about 12 seconds later, the client sees
`httpx.RemoteProtocolError: Server disconnected without sending a response.`, and the next request
gets `[Errno 111] Connection refused` until systemd restarts the unit. **Three of three**, with and
without `format: "json"`. Two runs of that were unintentional — the probe hit it once and the
narrowing matrix once — and the third was deliberate, to separate `think: false` from
`format: "json"`; the service was verified back up after each. The Ollama unit's own log was not
readable (`journalctl -u ollama` needs a sudo password this session did not have), so what the
runner died of is unknown here.

**The narrowing matrix**, three runs per cell, run to find which half of the failing body is the
trigger:

| Model | `think` | `format` | Runs | Terminal chunk | Outcome |
|---|---|---|---|---|---|
| `gpt-oss:20b` | `false` | `json` | 3 | **0 / 3** | `{"error":"error parsing tool call: raw='{\":\":\"  }'…"}` each time |
| `gpt-oss:20b` | `false` | — | 3 | 3 / 3 | Completes, `done_reason=stop` |
| `gpt-oss:20b` | `true` | `json` | 3 | 3 / 3 | Completes, `done_reason=stop` |
| `deepseek-coder-v2:latest` | `false` | `json` | 3 | 0 / 3 | Server down |
| `deepseek-coder-v2:latest` | unset | `json` | 3 | 0 / 3 | Server still down from the row above |

**It is the pair that fails.** `think: false` alone completes; `format: "json"` alone completes;
together they do not. The `deepseek` "unset" row measured nothing about `unset` — the server was
already down from the row above it — and is recorded rather than dropped so the number of runs in
this handoff matches the number of requests made.

Scratchpad layout, for whoever re-runs it:
`i6/prompt.py` (the one prompt), `i6/capture.py` (gate B, raw bytes),
`i6/probe.py` (gate A, ten models), `i6/narrow.py` (the matrix),
`i6/through_modelrack.py` (the same body through `OllamaProvider`), with `i6/raw/`, `i6/probe/`,
`i6/capture.json`, `i6/probe.json` and `i6/narrow.jsonl` beside them.

## 5. Exit conditions, answered

1. **The default gate is green on a named interpreter, coverage above the floor, no network, no
   GPU.** Yes — §1: Python 3.13.15, 1 433 passed, 99.82 % against a 95 % floor. No source file
   changed, so this is the unchanged suite; nothing from the probe entered `tests/`.
2. **The table exists where D1 put it, mirrored and `cmp`-clean, naming every model probed and
   every model skipped.** Yes — `apps/loadcoach/routing.md` §2, mirrored into
   `LoadCoach/docs/apps/loadcoach/routing.md`, `cmp` clean. All ten installed models are in it;
   none was skipped, so the skip list is empty and says so here.
3. **The stream failure has exactly one verdict, with the evidence that produced it.** Yes — D3:
   Ollama closes the stream, documented refusal, no fix and no version bump, with the raw capture
   taken outside ModelRack as the evidence.
4. **`git status --short` clean in every repository touched, work committed, nothing pushed.** Yes
   — `docs`, `LoadCoach` and `py/ModelRack`, one commit each, none pushed.

## 6. Things this prompt said that turned out not to be true

* **"Roughly 94 GB of model loads" and "~20 streamed generations" were priced as a long unattended
  night.** The whole of gates A, B and the narrowing matrix took about 25 minutes of wall clock:
  `keep_alive: 0` on each model's last request means one load per model, and the models are 5.6 to
  13.8 GB each on a 16 GB card. The kickoff's "cap the set or unload between models" escape was
  taken in its second form and cost nothing.
* **The kickoff framed the failure as intermittent** ("four of six", "a stream that dies at 1.3 s in
  four of six runs is a *retryable* provider failure"). Straight to Ollama it is **not**
  intermittent at all: 6 of 6 under `think: false` + `format: "json"`. Through ModelRack the same
  body failed 1 of 3, and the difference is not transport — the two runs that "succeeded" returned
  reasoning prose as `text`, which is the same underlying misbehaviour landing on the other side of
  Ollama's harmony parser. I3's four-of-six is the LoadCoach-level count of a defect that is
  deterministic at the wire.
* **"A hand-made stream of the same body completed normally with `done: true`"** (I3 §4, carried
  into the kickoff as the reason to suspect the parser). Not reproducible: this row's hand-made
  streams of that body completed **zero** times in six. Whatever I3's direct probe sent, it was not
  the failing pair — most likely `think: false` without `format: "json"`, which completes 3 of 3.
* **The kickoff expected the probe to be read-only against the machine.** It is read-only against
  the *tree*, and it changed no code, no profile and no configuration — but `think: false` on
  `deepseek-coder-v2:latest` killed the Ollama service three times. systemd brought it back each
  time and nothing was lost; recorded because "read-only" turned out to have an edge.

## 7. What the operator still has to do

**Nothing for a release.** Gate C produced no fix, so there is no `modelrack 0.7.2` to tag or
publish and `modelrack` stays at `0.7.1`. The push list is three commits — one in `docs`, one in
`LoadCoach`, one in `py/ModelRack` — and pushing them is yours as always.

One judgement call is worth putting in front of you rather than deciding here: **`deepseek-coder-v2:
latest` crashes Ollama on `think: false`**, and nothing in the suite stops a profile from routing to
it with the field set. Today no shipped profile sets `think`, so nothing is exposed. If one ever
does, the guard belongs somewhere — a LoadCoach constraint, an operator note, or a pull of that
model — and that is a decision, not a defect to fix here (§8).

## 8. Anything found that belongs to another row

* **LoadCoach's retry classification is already correct** for this failure and needs no row — §3,
  D3, checked in `retry_policy.py` rather than assumed. The retries simply cannot help against a
  deterministic body.
* **No probed model's behaviour should change a shipped task profile.** The five harness profiles
  and `tools.plan` all leave `think` unset, which is what the eight honouring models and the one
  ignoring model together still argue for: the lever pays only when the operator knows which model
  they are pointing it at, and now they can look it up. **This is a fact, not a change** — the
  kickoff's stop rule puts any profile edit in a LoadCoach row.
* **A LoadCoach row could be argued for the `deepseek-coder-v2` crash** — §7. The shape would be a
  routing-time refusal for a model that accepts `think: false` and dies on it, which needs
  per-model knowledge LoadCoach does not have and probably should not acquire; the cheaper answer
  is the operator note that now exists in `routing.md`. Left unscheduled deliberately.
* **An Ollama upstream report is available to whoever wants to file it** — `0.32.13`,
  `gpt-oss:20b`, `think: false` + `format: "json"` ends a 200 NDJSON stream with no terminal chunk
  and sometimes `error parsing tool call`; `deepseek-coder-v2:latest` + `think: false` kills the
  server. Both reproduce from the scratchpad scripts. Not this suite's work.
