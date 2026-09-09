# C5 handoff — ModelRack, the ADR-0070 usage rule

**Row:** C5 of `docs/roadmap/outstanding-work.md` §1. **Repository:** `py/ModelRack`, on `main`.
**Started at** `a0f9328` (0.6.0, clean, pushed, CI-green). **Ends at** `94bf5ce`, three commits,
working tree clean, **nothing pushed, nothing tagged, no version bump**. This rides `0.7.0` at H1.

**Model deviation, for `model-assignment.md` §3.5:** ran on **Opus 5 · high** rather than the
scheduled *Sonnet 5 · high*, combined with C6 in one overnight session, per the
`docs/history/c5-c6-overnight.prompt.md` wrapper. *Did the upgrade earn its keep?* In one place, yes, and it is
not the place the wrapper predicted. The conformance seam (§5 below) was straightforward once the
shape was chosen. The judgment that actually mattered was the **malformed-`prompt_tokens_details`**
decision — recognising that refusing `input_tokens` *along with* `cache_read_tokens` is required,
because the two are the halves of one subtraction and reporting `prompt_tokens` beside an unknown
cached figure silently breaks the disjointness invariant the whole ADR rests on. That is a
two-line code difference with no test that would have caught the weaker version, and it is the
kind of thing a diff review is unlikely to flag either. The rest of the row was transcription and
would have gone the same way at the scheduled tier.

---

## 1. Gate results

Interpreter: **Python 3.13.15**, `py/ModelRack/.venv` (`.venv/bin/python --version`). There is no
`python3.12` on this machine. Run from `/home/jpk/ai/suite/py/ModelRack`, each binary named
explicitly out of the venv rather than relying on an activated shell:

```
.venv/bin/ruff format --check .        43 files already formatted
.venv/bin/ruff check .                 All checks passed!
.venv/bin/mypy src tests               Success: no issues found in 37 source files
.venv/bin/lint-imports                 Contracts: 2 kept, 0 broken
.venv/bin/python -m pytest -m "not live and not performance" -q
                                       965 passed, 15 skipped, 18 deselected in 2.87s
```

Coverage, separately, under the same invocation plus `--cov --cov-report=term-missing`:
**100.00 %** statement and branch, against a **95 %** floor. Every one of the five source files
touched is at 100 %.

`pytest-randomly` was left on for the gate run above. The suite was also run once with
`-p no:randomly` during development; no order-dependent behaviour appeared.

The `live` and `performance` markers were **not** run. Ollama *is* installed on this machine now
(§3), so `pytest -m live` is available to the next session for the first time — see §8.

---

## 2. The rule as implemented

Per response, not per adapter. The three cases, per adapter:

### `OpenAICompatibleProvider._read_usage`

| Wire shape | `input_tokens` | `output_tokens` | `cache_read_tokens` | `cache_write_tokens` |
|---|---|---|---|---|
| `usage` with `prompt_tokens_details.cached_tokens` | `prompt_tokens − cached_tokens` | `completion_tokens` | `cached_tokens` | `0` |
| `usage` without the details key | `prompt_tokens` | `completion_tokens` | `0` | `0` |
| `usage` present with an **unreadable** details object | `UNSUPPORTED` | `completion_tokens` | `UNSUPPORTED` | `0` |
| no `usage` object, or an empty one | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` |

Row three is mine, not the ADR's; §4 argues it. Cache **write** is `0` whenever a usage object is
present, because the protocol defines no write charge at all — a statement about the protocol, not
about the response. Its known limit is ADR-0070's own *Revisit when*: a provider that bills cache
writes under this shape without reporting them makes that zero wrong and needs a per-provider
override rather than a protocol-level rule. The docstring says so rather than pretending it away.

### `_ollama_wire.read_usage`

| Terminal payload | `input_tokens` | `output_tokens` | cache classes |
|---|---|---|---|
| carries `prompt_eval_count` and/or `eval_count` | `prompt_eval_count` | `eval_count` | both `0` |
| carries neither key | `UNSUPPORTED` | `UNSUPPORTED` | both `UNSUPPORTED` |

The discriminator is **key presence**, not readability: a payload with a malformed
`prompt_eval_count` still reported counts, so its cache classes are `0` while the malformed class
itself is `UNSUPPORTED` via the existing `_as_token_count`. A payload with neither key is this
protocol's analogue of an absent `usage` object.

Ollama's cache-detail case does not exist — the protocol has no field that could carry it. That is
**declared** in the conformance suite rather than skipped silently (§5).

### `FakeProvider`

`FakeGeneration.cache_read_tokens` / `cache_write_tokens` now default to `0` when unscripted, and
`UNSUPPORTED` remains scriptable by passing it explicitly (`_validate_counts` already permitted
`UNSUPPORTED`, so no validation change was needed). The disjointness derivation
`input = prompt − cache_read` still holds with `cache_read == 0`. With
`capabilities.token_counts` undeclared, all four classes remain `UNSUPPORTED` — the fake's
analogue of "no usage object", and now asserted for all four rather than two.

---

## 3. The Ollama capture — ADR-0070 decision 3, **settled**

The C5 prompt's precondition "there is no Ollama on this machine" was false; the overnight
wrapper's OVERRIDE 1 authorised the experiment. Preconditions checked before running it: no
FreeWeight benchmark process, GPU idle at 848 MiB / 16311 MiB, 1 % utilisation.

**The question.** Does `prompt_eval_count` count only the tokens Ollama evaluated when its KV
cache reused a prefix, or the whole prompt submitted? A recorded fixture cannot answer this: it is
a question about the relationship between two requests.

**The experiment.** One model, `gemma3:latest`, loaded once. Two `POST /api/chat` requests issued
back-to-back, sharing a 16 389-character / 220-line prefix and differing only in a ~10-token tail.
`temperature: 0`, `seed: 1`, `num_predict: 4`, `stream: false`. Ollama **0.32.13** (server
answered `{"version":"0.32.13"}`), NVIDIA GeForce RTX 5060 Ti. Total elapsed well inside the
15-minute cap.

**The numbers, verbatim:**

```
--- REQUEST A  (prefix + tail A)   prompt_chars=16436, wall=5.26s
    prompt_eval_count: 5410
    eval_count: 3
    prompt_eval_duration: 885350000      (885.35 ms)
    eval_duration: 26081000
    done_reason: stop
--- REQUEST B  (same prefix + tail B, back-to-back)   prompt_chars=16436, wall=0.42s
    prompt_eval_count: 5410
    eval_count: 3
    prompt_eval_duration: 125949000      (125.95 ms)
    eval_duration: 18497000
    done_reason: stop
```

**Does this settle it? Yes.** `prompt_eval_count` is identical across both requests while
`prompt_eval_duration` fell **885 ms → 126 ms**, a 7× drop for an unchanged prompt length. The
duration collapse is the control that makes the reading decisive: it demonstrates the KV cache
*did* serve the shared prefix on request B, so the condition the ADR asks about was genuinely
exercised — and the count did not move. Had the durations been similar, the experiment would have
proved nothing except that the cache never engaged.

**Conclusion, and what went into the docstring.** `prompt_eval_count` reports **the prompt
submitted, not the tokens evaluated**. The conditional branch of ADR-0070 decision 3 ("If it does,
`input_tokens` for this adapter means tokens processed…") therefore **does not apply**:
`input_tokens` for the Ollama adapter is the ordinary prompt length, the same quantity every other
adapter reports, and a caller comparing token counts across providers is comparing like with like.
The docstring states this assertively and cites the measurement — a token brake reading this field
brakes on prompt size, not on work performed, and a cached prefix costs the brake full price.

**No `live` test was added for this**, and that is deliberate rather than an omission: the
measurement is now recorded in the docstring, in the CHANGELOG and in `ollama/manifest.json`, and
a `live` test asserting `prompt_eval_count` equality across two requests would assert a *provider
implementation detail* that is explicitly a revisit trigger in ADR-0070 ("Ollama … starts
reporting cache statistics"). Baking it into a test would make a future Ollama improvement look
like a ModelRack regression. If the next session disagrees, the capture script is at
`scratchpad/ollama/capture.py` and is 50 lines.

The capture script is scratch and was **not** committed. Nothing under `tests/` needs a daemon:
spec §20 criterion 3 holds unchanged, proven by the gate above, which passes with the socket guard
active and every adapter test on recorded fixtures.

---

## 4. The decisions, where the ADR left an edge

**(a) An empty `usage: {}` is an absent usage object.** All four classes `UNSUPPORTED`.

This is load-bearing rather than pedantic. `OpenAICompatibleProvider.stream` initialises
`usage_payload: Mapping[str, Any] = {}` and passes `_read_usage({"usage": usage_payload}, …)` at
the stream-completion site, so **a stream that never carried a usage chunk arrives here as an
empty mapping produced by this adapter's own accumulator, not by the server.** Reading that as
"present but without cache detail" would have reported cache classes of `0` for a response that
reported nothing at all — a fabricated zero manufactured out of a default value. The old code's
`usage = usage if isinstance(usage, Mapping) else {}` folded absence into presence, which was
harmless only while every class read `UNSUPPORTED` from a missing key. There is a dedicated test
for the streamed path (`test_a_stream_that_carried_no_usage_chunk_reports_every_class_unsupported`).

**(b) `cached_tokens > prompt_tokens` → both `input_tokens` and `cache_read_tokens` are
`UNSUPPORTED`.** Not clamped.

The pair is the two halves of one subtraction, so if the reconciliation cannot be performed,
neither output of it is known. Clamping — which is what `FakeProvider` does for a *scripted*
count, via `max(billed, 0)` — would turn a server contradicting itself into a confident
`input_tokens` of `0` for a call that certainly had input. That is worse than refusing, and worse
than a negative, which `TokenUsage.__post_init__` would have rejected anyway.

**(c) A malformed `prompt_tokens_details` → the same refusal, and this is the decision I am least
willing to see quietly reversed.** "Present but unreadable" covers: not a mapping (JSON `null`
included), no `cached_tokens` key, a fractional/negative/boolean/string figure, and (b) above.

The reasoning: a server that sent a details object **has told us it does cache accounting**. So an
unreadable figure means a class the protocol can express, and that this server bills, was not
readable — ADR-0070 decision 1's *second* sentence, not its first. Reporting `cache_read = 0`
there would be the fabricated zero, and reporting `input_tokens = prompt_tokens` beside an unknown
cached figure would not be disjoint from it: the very double-billing the reconciliation exists to
prevent, reintroduced through the error path. Only the classes the details object says nothing
about are unaffected — `output_tokens` from `completion_tokens`, and `cache_write_tokens` at `0`
by protocol. Seven parametrised cases cover it.

The cost of this choice is a floor where a partial reading was possible. That is the correct
direction, and it is the direction ADR-0016 has always chosen.

**(d) Ollama's discriminator is key presence, not readability** — see §2. A payload that reported
counts, however malformed, is a payload that reported counts.

**(e) No live test for decision 3** — see §3.

**(f) Not extended to anything else.** Timings, `thinking_tokens`, `tool_tokens`,
`token_level_chunks`, `latency_ms` and every other unavailable measurement remain `UNSUPPORTED`.
ADR-0070 is about token classes and a wire protocol's billing vocabulary, and nothing else.

---

## 5. The conformance seam — written for D3

**What you write to add `LlamaCppProvider` to the three usage cases: one fixture. Nothing else.**

`tests/contract/test_conformance.py` now carries three declarations above the suite:

* `UsageShape` — an enum of `NO_CACHE_DETAIL`, `CACHE_DETAIL`, `NO_USAGE_OBJECT`. Named rather
  than positional so a subclass declares by name.
* `CacheDetailShape(prompt_tokens, cached_tokens)` — what your cache-detail response *claims on
  the wire*. The suite asserts the reconciliation arithmetic and cannot read the prompt figure off
  the result, because the result is exactly what the reconciliation has already rewritten. So you
  declare it. Validated in `__post_init__`: `0 <= cached_tokens <= prompt_tokens`.
* `UsageShapes(provider_for, cache_detail)` — the seam itself.

Your subclass overrides one fixture:

```python
@pytest.fixture
def usage_shapes(self, provider, selected_chat_fixture) -> UsageShapes | None:
    names = {
        UsageShape.NO_CACHE_DETAIL: "…json",
        UsageShape.CACHE_DETAIL:    "…json",
        UsageShape.NO_USAGE_OBJECT: "…json",
    }

    def provider_for(shape: UsageShape) -> Provider:
        selected_chat_fixture["complete"] = names[shape]
        return provider

    return UsageShapes(provider_for=provider_for,
                       cache_detail=CacheDetailShape(prompt_tokens=…, cached_tokens=…))
```

`provider_for` returns *a provider whose next `generate` produces the named shape*. Two idioms are
already in the file and both are fine — the suite only ever calls `generate` on what it is handed:

* **Recorded transports** (Ollama, OpenAI-compatible) add a `selected_chat_fixture` fixture
  holding a one-key mutable dict; the existing chat handler reads the filename out of it instead
  of hard-coding one, and `provider_for` sets the key and returns the *same* provider. This was a
  one-line change to each handler and the default value is the payload every other behaviour in
  the suite has always used, so nothing else moved.
* **`FakeProvider`** builds a freshly scripted provider per shape (`_fake_usage_shapes()`, shared
  by the full-capability and chunked classes). `NO_USAGE_OBJECT` is scripted by naming
  `UNSUPPORTED` on all four classes — the escape hatch decision 5 required the fake to keep.

**Two declarations that are not exemptions:**

* `cache_detail=None` means *this wire protocol cannot report cached input at all* — Ollama's
  case. The cache-detail behaviour then skips with an explicit reason. If llama.cpp's native API
  can express cached input in any form, **declare it**: an adapter that could and declared `None`
  would be exempting itself from the one case that catches double-billed cached input, which is
  the whole latent defect ADR-0070 was written to close.
* `usage_shapes` returning `None` means *this configuration declares no token counting at all*
  (`TestFakeProviderMinimalConformance`). The three behaviours then take a refusal branch that
  asserts all four classes come back `UNSUPPORTED` — an assertion, not a skip, per this file's
  standing rule that capability-gated behaviour is never silently skipped.

The base fixture **raises `NotImplementedError`**. There is no default, deliberately: an adapter
joining this suite must say which shapes its protocol produces, because "it was never asked" and
"it answered `0`" are precisely the two things ADR-0070 exists to keep apart.

**The arithmetic is asserted, not the types.** The cache-detail case asserts
`input + cache_read == declared.prompt_tokens`. The no-cache-detail case prices its usage through
`estimate_cost` against `_UNCACHED_PRICING` — a list with input and output rates and **no cache
rates**, the local-model case — and asserts a real `total` with `unpriced_reasons == ()`. That
last assertion is the observable improvement this row exists for, sitting in a test rather than
only in the changelog: under ADR-0069 every such response was labelled a floor and a strict money
ceiling tripped on the first remote turn.

---

## 6. Fixtures added and re-annotated

| Fixture | Proves |
|---|---|
| `openai_compatible/chat_complete_cached.json` | Row one. `prompt_tokens` 21 with `prompt_tokens_details.cached_tokens` 8 → input 13, cache read 8, summing back to 21. An adapter skipping the reconciliation reports input 21 and bills the cached prefix twice. |
| `openai_compatible/chat_complete_no_usage.json` | Row four. A well-formed completion with no `usage` object at all → every class `UNSUPPORTED`. |
| `ollama/chat_complete_no_counts.json` | Ollama's row four. A terminal payload with the durations but neither count field. |
| `openai_compatible/chat_stream_no_finish_reason.sse` (existing) | Row four over the **streamed** path, where the empty accumulator is the trap. Reused rather than duplicated. |
| `openai_compatible/chat_complete.json` (existing) | Row two, unchanged. |
| `ollama/chat_complete.json` (existing) | Ollama row one, unchanged. |

Both `manifest.json` files gained `re_annotated: "2026-09-03"` and a `re_annotation_note`. Spec
§19's **re-capture** trigger did not fire and the note says so explicitly: no existing payload
changed and neither provider version moved. Each note keeps the file's existing honesty about
representative-vs-captured payloads. Ollama's note additionally records the live measurement from
§3, and drops the now-false claim that this repository has no Ollama installation.

The malformed-details cases are built inline in the test rather than as seven fixture files —
they are wire *malformations*, not recorded server behaviour, and a fixture directory implies a
server said this.

---

## 7. Downstream consumers — checked, not assumed

**None break.** Verified rather than reasoned about:

* **LoadCoach** — `services/execution.py:378 _count()` returns `int(value)` when
  `is_supported(value)` and `None` otherwise. A `0` therefore stores as `0` and an `UNSUPPORTED`
  as `NULL`; both are correct under ADR-0070 and neither changes shape. Unaffected by
  construction, exactly as the row predicted. Its four-class wire change is **C6**.
* **FreeWeight** — `grep` finds **no reference to `cache_read_tokens` or `cache_write_tokens`
  anywhere** in `src/` or `tests/`. Its `total_tokens_per_success` is FreeWeight's own metric over
  input and output separately, not `TokenUsage.total_tokens`. Its suite **was run against the
  edited ModelRack** (its venv resolves the working tree — see the finding below):
  `FreeWeight/.venv/bin/python -m pytest -m "not live and not performance" -q` →
  **2508 passed, 28 skipped, 26 deselected in 178.84s**, Python 3.14.
* **IdeaPress** — carries its own integer-valued `TokenUsage` in `domain/inference.py`; no
  reference to either cache class. Its venv holds a **real PyPI wheel** of modelrack, not an
  editable, so it does not see this change at all until 0.7.0 ships.

### Finding: FreeWeight's venv also has ModelRack installed editable

The overnight wrapper's OVERRIDE 2 records the editable-install situation for **LoadCoach**. It is
also true of **FreeWeight**:

```
FreeWeight/.venv → import modelrack → /home/jpk/ai/suite/py/ModelRack/src/modelrack/__init__.py
```

So C5's edits are live in FreeWeight's test suite too, and were before this row started. This is
not a problem here — FreeWeight's suite is green against it, above — but it is a standing property
of this workspace that the next scheduler should know: **a ModelRack change is immediately live in
two of the three applications' local suites and in neither of their CI runs**, which install from
hash-pinned locks. A local green and a CI green are testing different ModelRacks.

---

## 8. Before the next session

1. **Push `main`** (`94bf5ce`) and confirm CI green. Nothing is pushed. The VSCode askpass IPC env
   is needed for `git push` on this machine (see the FreeWeight push-auth memory).
2. **Morning diff review** — `outstanding-work.md` §4 requires it and running at Opus did not
   remove it. The two places worth the reviewer's attention are §4(c), the malformed-details
   refusal, and §5's `cache_detail=None` declaration, because both are choices that a later
   session could weaken without any test going red.
3. **This does not publish.** ModelRack stays at `0.6.0`; the change rides **`0.7.0` at row H1**,
   after P6–P8. No tag, no `__about__.py` bump.
4. **`pytest -m live` is now runnable here for the first time** — Ollama 0.32.13 is installed and
   answering on `localhost:11434`, with 14 models and an RTX 5060 Ti. `tests/live/test_ollama_live.py`
   was **not** run this session (it is outside the gate). Worth a run before H1; its existing
   token assertion is `is_supported`-guarded and will not be disturbed by this change.
5. **C5 before D3 is now satisfied.** D3 writes `LlamaCppProvider` against §5's seam. The hard
   edge in `outstanding-work.md` §3 is met.
6. **No spec amendment is needed.** §11 contract 2 and §18 were already amended by A1 and the code
   is now true to them; I edited neither, and the repo mirror is untouched by this row.
