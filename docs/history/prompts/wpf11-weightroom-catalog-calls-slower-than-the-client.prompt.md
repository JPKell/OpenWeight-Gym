# Kickoff — WPF11: a catalog call slower than the client is not a refusal

**Row:** WPF11 (Sonnet 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Left by WPF1 ([`WPF1_HANDOFF.md`](../handoffs/WPF1_HANDOFF.md) §2.3 last bullet and §6 item 3).
Runs after WPF1. **Ships:** unreleased, no version bump.

**Component:** `~/ai/suite/WeightRoom`.

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WPF1_HANDOFF.md` §2.3 (the decision: a timeout is `AppTimedOut`, a subclass of
`AppUnreachable` with the same code; `outcome_of(exc)` audits it `pending`); `W8_HANDOFF.md` (the
catalog — Ollama pull/rm go through Ollama's own HTTP API, not ModelRack); `apps/weightroom/spec.md`
§11 (audit) and §13 (error codes).

**Code to read first:** `services/catalog.py` — `CatalogRefused`, every `httpx` call, `set_enabled`,
`pull`, `_call`; `services/app_api.py` — `AppTimedOut`, `outcome_of`; the catalog routes that audit.

## What this row has to settle

1. **The catalog's error family gets the same distinction `app_api` has.** A timeout from Ollama or
   from an application's catalog endpoint is audited `pending` (work may still be running, nothing
   was cancelled or re-sent), and only an answer that said no is `refused`. Reuse `outcome_of` if
   the exception shapes allow it; do not build a second vocabulary.
2. **A `pull` is not a short call.** Pulling a model from the Ollama library takes minutes. Decide
   whether the console's `pull` stays a request with a client timeout (then it is `pending` the
   moment it exceeds it, and the page must say the pull continues) or moves onto the job queue
   (W9's job kinds). WPF1 rejected the queue for FreeWeight's refresh because it changed how the
   operator works; the same argument may not hold for a multi-minute download. State the choice.
3. **What the page shows after a `pending`.** The catalog row must still be true on the next
   render — the model appears when Ollama finishes, without a second pull being sent.

## Gates

**Gate A.** Tests first: a timed-out `set_enabled`, `pull` and `rm` each audit `pending` with the
message WPF1 chose; a refused one still audits `refused`. Implement. Gate green, interpreter named.
Commit. An ADR only if decision 2 moves `pull` onto the queue.

**Gate B — the live proof.** On the reference machine: pull a small model from the console
(`smollm2:135m` is enough), watch the audit row, watch the catalog page until the model appears.
No second pull in Ollama's log.

## Finish line

- The gate green; `git status --short` clean.
- `docs/history/handoffs/WPF11_HANDOFF.md`: the decisions, the audit ids, what this kickoff got
  wrong. The row marked done. Nothing pushed.
