# Kickoff — C5: ModelRack, the ADR-0070 usage rule

**Row:** C5 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** Sonnet 5 · high. **Repository:** `/home/jpk/ai/suite/py/ModelRack` — `0.6.0`, clean,
pushed and CI-green at `a0f9328`.
**Runs after:** A1, which is **done** — ADR-0070 is accepted and ModelRack's spec §11 contract 2
and §18 are **already amended and mirrored**. Placement is flexible; the one hard edge is that
**C5 lands before D3** ([outstanding-work §3](docs/roadmap/outstanding-work.md)): the usage rule
goes in before the third adapter is written, because a retrofit is a fixture re-annotation nobody
wants.
**Ships:** nothing. The change lands under `## [Unreleased]` and rides ModelRack's **next minor
(0.7.0)**, which is published at row **H1** after P6–P8 ([adapter-roadmap
§4.1](docs/roadmap/adapter-roadmap.md): "target: next minor, e.g. 0.7.0"). Do not bump the version,
do not tag, do not publish.
**Overnight:** permitted — Sonnet rows run at effort **high** overnight
([model-assignment §2.12](docs/roadmap/model-assignment.md)); this row is not on the
never-overnight list.

**Why this row is `high` and not `standard`.** It is two small functions against a stated rule, and
the rule is written out decision by decision in the ADR — which is `standard`'s profile exactly.
It is `high` for two reasons that have nothing to do with size:

* **ModelRack is called by three applications**, and this change alters the *reported shape of
  usage* for both real adapters. What was `UNSUPPORTED` becomes `0`, `total_tokens` starts
  returning a number, and `estimate_cost` starts totalling. Anything downstream that branched on
  "unsupported" now takes the other branch.
* **The named failure mode is a fabricated zero** — the precise thing
  [ADR-0016](docs/adr/0016-unavailable-is-not-zero.md) exists to forbid, being deliberately
  introduced in one narrow direction. Get the boundary between "the protocol cannot bill this" and
  "the protocol can bill this and did not report it" wrong, and a cost estimate is quietly wrong in
  the safe-looking direction. ADR-0070's *Consequences* names it: "a protocol judged wrongly
  produces a fabricated zero."

---

## Preconditions

* **`modelrack` is at `0.6.0`, the tree is clean, and `main` is pushed** (`a0f9328`, CI green in
  the same batch as LoadLedger's first push). `git status --short` must be empty before you start.
* **The spec is already amended — do not re-edit it.**
  [`docs/packages/modelrack/spec.md`](docs/packages/modelrack/spec.md) §11 contract 2 carries the
  new second half of the rule, and §18's conformance row already lists the three usage cases. Both
  are mirrored byte-identically into the repo (verified 2026-09-02). Your job is to make the code
  true to a spec that already says what it should do; if you find the spec wrong, propose the
  amendment in the handoff rather than editing quietly.
* **There is no Ollama and no live provider on this machine.** Spec §20 criterion 3 — "the full
  default test suite passes with no Ollama installed" — stays true, and every adapter change is
  proven against **recorded fixtures**. See §1 below for what that means for ADR-0070 decision 3,
  which asks a question recorded fixtures may not be able to answer.
* **You are not authorised to push, tag or publish.** Commit on `main` and stop.

---

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository. This row works in `/home/jpk/ai/suite/py/ModelRack`.
* **Read before writing**, in this order:
  [`docs/architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, the
  ModelRack section of [`docs/standards/gold-standards.md`](docs/standards/gold-standards.md) §2
  (lines 74–83), then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. The three functions you
  touch already have docstrings that state the **old** rule and cite ADR-0016 for it; rewriting
  those docstrings correctly is half this row's deliverable, because they are what D3 reads when it
  writes the third adapter's equivalent.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **95 %**, `CHANGELOG.md` updated
  under `## [Unreleased]`, one Conventional Commit per logical group. **Name the interpreter and
  the exact invocation in the handoff doc** (M5C-13) — this repo's venv is Python 3.13.15; confirm
  rather than copy. There is no `python3.12` on this machine.
* **No new dependency, and no change to the `Provider` protocol.** A protocol change is a major
  bump (spec §19) and this is a minor. Nothing in `types.py`'s public surface needs to move: the
  four token classes already exist on `baseaicore.TokenUsage`.
* **Documentation is mirrored.** If you amend anything under
  `/home/jpk/ai/suite/docs/packages/modelrack/`, edit the workspace copy first and re-verify the
  repo copy with `cmp`. Expect to amend nothing.

## Setup

```bash
cd /home/jpk/ai/suite/py/ModelRack
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be empty before you start
```

## Reading list

1. [ADR-0070](docs/adr/0070-an-absent-token-class-is-zero-only-where-the-protocol-cannot-bill-it.md)
   — the whole record. **Decisions 1, 2, 3, 5 and 6 are this row.** Decision 4 is D3's and decision
   7 is C6's; read them anyway, because your docstrings are the pattern both follow. Read
   *Consequences* and *Revisit when* too — the known gap (a provider that bills cache writes under
   the OpenAI-compatible shape without reporting them) is what your docstring must not pretend
   away.
2. [ADR-0069](docs/adr/0069-a-partial-price-is-a-floor-and-a-money-ceiling-chooses-how-it-binds.md)
   §"Not decided here" — the question ADR-0070 answers, and the reason it matters: without this
   change every real response is labelled a floor, `unmetered_debit_count` is never zero, and a
   strict money ceiling trips on the first remote response.
3. [ADR-0016](docs/adr/0016-unavailable-is-not-zero.md) — applied, not reversed. Rule 4 (JSON
   renders `"unsupported"`, never `null`, never `0`) is C6's; the sentinel's refusal semantics are
   what make the distinction you are drawing meaningful.
4. [ADR-0030](docs/adr/0030-model-cost-and-pricing.md) — the adapter is the only layer that knows a
   provider's convention, and reconciling overlapping prompt and cache figures into the disjoint
   classes is its job. That sentence is the licence for `input = prompt_tokens − cached_tokens`.
5. [`docs/packages/modelrack/spec.md`](docs/packages/modelrack/spec.md) §11 contract 2 (as
   amended), §18's conformance row (as amended), §19 (recorded fixtures record the provider version
   they came from; a bump triggers re-capture and a changelog note).
6. The code, in this order: `src/modelrack/providers/_ollama_wire.py`'s `read_usage`;
   `src/modelrack/providers/openai_compatible.py`'s `_read_usage` **and both of its call sites**
   (the non-streaming path and the stream-completion path, which passes `{"usage": usage_payload}`
   where `usage_payload` may be empty); `src/modelrack/providers/fake.py`'s usage construction and
   `_fake_script.py`'s `FakeGeneration.cache_read_tokens`/`cache_write_tokens`.
7. `tests/contract/test_conformance.py` — the suite shape, and specifically
   `test_token_counts_follow_the_declaration`, which is the test the three new cases extend.
8. **`docs/history/B2_HANDOFF.md` §5 item 7** — where this defect was found, with the measured numbers (input
   1 000 + output 500 against a complete price list gives an `UNSUPPORTED` total; the same usage
   with explicit zeros gives 0.0105 USD). It is the clearest statement of what this row fixes.

## The work

### 1. `_ollama_wire.read_usage` — both cache classes `0`, and one honest caveat

ADR-0070 decision 3: Ollama's protocol has no cache-billing vocabulary, so both cache classes are
`0`. `prompt_eval_count` → `input_tokens`, `eval_count` → `output_tokens`, unchanged.

The caveat is the part that needs judgment. The ADR says: *"Before asserting it, a recorded fixture
verifies whether `prompt_eval_count` counts only the tokens Ollama evaluated when its KV cache
reused a prefix. If it does, `input_tokens` for this adapter means tokens processed, which is the
right number for a token brake and is not the prompt length; the adapter's docstring says so."*

A recorded fixture can show you what a field contained; it cannot by itself answer a question about
two requests sharing a prefix. So: check what the recorded fixtures actually carry, check Ollama's
own documentation for what `prompt_eval_count` counts, and then do one of two things — either
settle it and write the docstring assertively, or **mark a `live` test that would settle it**, write
the docstring conservatively (what the field is, what it may mean, and which reading the adapter
assumes), and list the live run as an operator step in the handoff. What you must not do is write a
confident docstring backed by nothing. Say in the handoff which of the two happened.

Update the docstring to state, in the ADR-0070 pattern that D3 will copy: which classes this wire
protocol can bill, what the adapter does with each, and why a zero here is a fact rather than an
invention.

### 2. `openai_compatible._read_usage` — three cases, and the one that is easy to get wrong

ADR-0070 decision 2:

| Wire shape | `input_tokens` | `output_tokens` | `cache_read_tokens` | `cache_write_tokens` |
|---|---|---|---|---|
| `usage` with `prompt_tokens_details.cached_tokens` | `prompt_tokens − cached_tokens` | `completion_tokens` | `cached_tokens` | `0` |
| `usage` without the details object | `prompt_tokens` | `completion_tokens` | `0` | `0` |
| no `usage` object at all | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` |

**The trap is the third row.** Today the function opens with
`usage = usage if isinstance(usage, Mapping) else {}`, which folds "absent" into "present but
empty" — harmless while every class read `UNSUPPORTED` from a missing key, and wrong the moment
absence and presence-without-details mean different things. Distinguish them explicitly. Decide
what an *empty* `usage: {}` means (the defensible reading is that an empty object is no usage
object, so all four classes are `UNSUPPORTED`), and remember the **streaming** call site: a stream
that never carried a usage chunk arrives here as `{"usage": {}}`, and it must land in row three,
not row two.

Two more decisions to make deliberately and document:

* **`cached_tokens` greater than `prompt_tokens`.** The disjointness subtraction can go negative on
  a malformed or unusual response. `FakeProvider` already clamps with `max(billed, 0)`; decide
  whether the adapter clamps, or treats the pair as unreadable and reports `UNSUPPORTED` for the
  affected classes, and say which and why. A silently negative token count is worse than either.
* **A malformed `prompt_tokens_details`** (present but not a mapping, or `cached_tokens` not a
  non-negative integer). `_as_token_count` already has the right instinct; make sure a malformed
  details object cannot promote a class to a confident zero.

### 3. `FakeProvider` — default `0`, keep `UNSUPPORTED` scriptable

ADR-0070 decision 5: the fake plays a protocol that bills no cache tier, so
`FakeGeneration.cache_read_tokens`/`cache_write_tokens` default to `0` — and scripting
`UNSUPPORTED` explicitly must remain possible, because LoadLedger's and PromptCadence's tests need
both shapes on demand.

Today `None` means "derive", and the derivation is `UNSUPPORTED`; changing the derivation to `0` is
most of the work. Two things to keep true: the disjointness derivation (`input = prompt − cache_read`)
still holds when `cache_read` is `0`; and when `capabilities.token_counts` is `False` the fake must
still report **every** class `UNSUPPORTED` — the fake's analogue of "no usage object at all", and
the case the existing conformance assertion covers.

`tests/unit/test_fake_provider.py` and `tests/unit/test_types.py` both currently encode the old
defaults; update them to assert the new rule rather than to accommodate it, and check the whole
suite for anything else that relied on the fake's cache classes being unsupported (ADR-0070's
*Consequences* predicts there will be some).

### 4. Recorded fixtures — re-annotated, and two new shapes

Both adapters need fixtures that drive the three cases:

* `openai_compatible`: the existing `chat_complete.json` covers row two as it stands. Add one with
  `usage.prompt_tokens_details.cached_tokens` (row one) and one with no `usage` object (row three),
  and make sure the streaming fixtures can reach row three as well.
* `ollama`: confirm the recorded terminal payloads carry `prompt_eval_count`/`eval_count`, and add
  one without them so the all-`UNSUPPORTED` case is reachable.

Update each `manifest.json`'s note: spec §19 requires fixtures to record the provider version they
came from, and this is a re-annotation rather than a re-capture — say so, say why, and keep the
existing honesty about which payloads are representative rather than byte-for-byte captures.

### 5. The conformance cases — the one piece of design in this row

Spec §18 now requires, **for every adapter**: a recorded response without cache detail yields cache
classes `0` and an estimate that totals; a response with cache detail yields disjoint classes that
sum to the provider's prompt figure; a response with no usage object yields every class
`UNSUPPORTED`.

The suite is a base class with one subclass per adapter configuration, and its fixtures give each
subclass one provider. Driving each adapter into three different response shapes therefore needs a
seam — fixture selection for the recorded adapters, scripting for the fake. Design that seam so a
fourth adapter (D3's `LlamaCppProvider`) slots in by declaring its three shapes rather than by
rewriting the tests; that is the whole reason C5 runs before D3.

Assert the arithmetic, not just the types: in the cache-detail case the disjoint classes must sum
to the provider's own `prompt_tokens`, and in the no-cache-detail case `estimate_cost` must produce
a **total** rather than refusing — that is the observable improvement this row exists for, and it
belongs in a test rather than in the changelog only.

### 6. Documentation and the downstream note

`CHANGELOG.md` under `## [Unreleased]`: a behaviour change, described as one — the reported shape
of usage changes for both real adapters, `total_tokens` starts returning a number for real
responses, and any consumer test that relied on the fake's cache classes defaulting to
`UNSUPPORTED` must script it explicitly. Cite ADR-0070.

Do **not** go and change the consumers. Do record, in the handoff, which of them this reaches:
LoadCoach maps `UNSUPPORTED` to `None` when it stores a count and is unaffected by construction,
its four-class wire change is row **C6**; FreeWeight totals input and output separately; IdeaPress
carries its own integer-valued `TokenUsage`. If you find a consumer that would actually break,
that is a finding for the handoff, not a fix for this session.

### 7. Gate and commit

The full gate green with the interpreter named. Commits on `main`, one per logical group. No
version bump, no tag, no publish, no push.

## Before you finish — three closing duties

1. **Write `docs/history/C5_HANDOFF.md` at the workspace root.** Sections: gate results with interpreter and
   exact commands; the rule as implemented, per adapter, in the three-case table's shape; **the
   decisions you made** — empty-`usage` semantics, the `cached_tokens > prompt_tokens` answer, the
   malformed-details answer, and whether Ollama's `prompt_eval_count` question was settled or
   deferred to a marked live run; the fixtures added or re-annotated and what each proves; **how
   the conformance seam works, written for D3**, which adds a fourth adapter against it; the
   downstream consumers this reaches and whether any actually breaks; the commits made; and
   **"Before the next session"** — at minimum: push `main`, confirm CI green, the live Ollama run
   if you deferred it, and the reminder that this rides `0.7.0` at H1 rather than publishing now.
   **Never overwrite an existing root file** — the workspace root is not a git repository. If
   `docs/history/C5_HANDOFF.md` exists, write `C5_HANDOFF.2.md` and say why.
2. **Summarise in chat**, briefly: what changed in each adapter, what the gate said, what you
   decided where the ADR left an edge, and what is waiting on the operator. A few sentences.
3. **Prepare the commits.** Everything committed on `main`, working tree clean, nothing pushed,
   nothing tagged.

## Constraints and stop rules

* **No version bump, no tag, no publish.** This rides ModelRack's next minor, published at H1.
* **No `Provider` protocol change** (major bump, spec §19) and **no new dependency**.
* **No live provider is required, and the default suite must still pass with no Ollama installed**
  (spec §20 criterion 3). A `live`-marked test is fine; a default-suite test that needs a server is
  not.
* **Zero is honest only where nothing could have been billed.** If you find yourself writing a `0`
  for a class the protocol *can* express, stop — that is the fabricated zero ADR-0016 forbids and
  ADR-0070 explicitly does not license.
* **Do not "helpfully" extend the rule to other measurements.** Timings, `thinking_tokens`,
  `token_level_chunks` and every other unavailable measurement stay `UNSUPPORTED`. ADR-0070 is
  about token classes and a wire protocol's billing vocabulary, and nothing else.
* **Do not edit the already-amended spec sections**, and do not touch the consumers.
* **Never weaken `.importlinter`** to make an import work.
* **Working-tree integrity** (see `CLAUDE.md`): `git status --short` in this repo at the start and
  end of the session; commit per logical group; never `git add -A`.
* If you must stop early, stop at a green gate with a commit, tree clean, and record exactly where
  you stopped in `docs/history/C5_HANDOFF.md`.
