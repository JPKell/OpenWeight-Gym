# Kickoff — WPF13: ModelRack counts what Ollama separates as thinking

**Row:** WPF13 (Opus 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Left by WPF7 ([`WPF7_HANDOFF.md`](../handoffs/WPF7_HANDOFF.md) §6 item 5 and §7 item 5). Runs
after WPF7. **Ships:** unreleased — ModelRack, IdeaPress and (if touched) LoadLedger all stay at
their held versions until the W arc ends; the local-pin rule of the standing preamble applies.

**Component:** `py/ModelRack` first; then `~/ai/suite/IdeaPress` (and `py/LoadLedger` only if the
debit semantics change — an ADR before that).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WPF7_HANDOFF.md` §2 decision 2 and §6 — the measurement that every
`output_tokens` figure and every budget debit for a thinking model on the structured stages is a
floor, not a total; `I6_HANDOFF.md` (what Ollama does with `think`); ADR-0132 (the thinking frame
on LoadCoach's stream — ModelRack already separates thinking text); ADR-0030 (cost is re-derived
from `TokenUsage`, so an under-counted usage is an under-stated cost); ADR-0070 (a class the
protocol cannot bill is `0`, not unavailable); ADR-0016 (an absent measurement is `UNSUPPORTED`,
never a number); `packages/modelrack/spec.md` — `GenerationResult.thinking`,
`usage.thinking_tokens`; `packages/loadledger/spec.md` §7 (`declare_run`, what is debited).

**Code to read first:** ModelRack's Ollama adapter — what it reads from `eval_count` and
`prompt_eval_count`, and where `thinking` text is split off; `TokenUsage` in BaseAiCore; IdeaPress's
`InferenceGateway` — what it debits and records per attempt.

## What this row has to settle

1. **What Ollama actually reports.** Measure before deciding: for one structured-stage request on
   `qwen3.5:9b-q8_0`, compare Ollama's `eval_count` against the tokens of `thinking` plus `text`
   (tokenise with the model's own tokenizer through `/api/tokenize`, or count via a second request
   with `think` off). Either `eval_count` already includes thinking and IdeaPress mis-attributes it,
   or Ollama omits it and the count is genuinely short. The handoff states which, with numbers.
2. **`usage.thinking_tokens` is filled where it can be, and `UNSUPPORTED` where it cannot.** Never
   `0` for a class the protocol *does* bill but the adapter did not read (ADR-0016 against
   ADR-0070 — read both before choosing the sentinel).
3. **What a debit is.** If `output_tokens` becomes a total that includes thinking, every LoadLedger
   ceiling on output tokens tightens for thinking models. Decide whether the debit is
   `output_tokens` (total) or `output_tokens + thinking_tokens` as two classes, and whether
   ADR-0030's cost types already name the second. An ADR if the answer changes a ledger figure.
4. **The pricing hash.** If a new class enters the priced usage, the `pricing_hash` of ADR-0030
   must change with it; if not, say why.

## Gates

**Gate A.** Tests first in ModelRack (a recorded Ollama response with a thinking segment yields the
counts decision 2 says) and in IdeaPress (an attempt row carries what it spent). Gates green in
each repo touched, interpreter named per repo. Commit per repo.

**Gate B — the live proof.** On the reference machine, one IdeaPress `critique` on
`qwen3.5:9b-q8_0`: the attempt's recorded usage against Ollama's own log line for the same call.
Check `nvidia-smi` and ADR-0119 first; IdeaPress asks for a 32 768 window since WPF7.

## Finish line

- Gates green; `git status --short` clean in every repo touched; nothing pushed, no version moved.
- `docs/history/handoffs/WPF13_HANDOFF.md`: the measurement of decision 1, the debit decision, what
  this kickoff got wrong. The row marked done.
