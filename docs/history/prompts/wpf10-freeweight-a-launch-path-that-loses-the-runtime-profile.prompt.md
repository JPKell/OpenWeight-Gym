# Kickoff — WPF10: a launch path that loses the runtime profile

**Row:** WPF10 (Opus 5 · high) — [`docs/roadmap/weightroom-work.md`](../../roadmap/weightroom-work.md).
Found by WPF2's Gate C ([`WPF2_HANDOFF.md`](../handoffs/WPF2_HANDOFF.md) §6a, step 2). Runs after
WPF9. **Ships:** unreleased, no version bump.

**Component:** `~/ai/suite/FreeWeight` (and `py/ModelRack` only if the cause turns out to be the
provider's launch rather than FreeWeight's request — say so in the handoff before touching it).

## Standing preamble

[`outstanding-work.md` §2](../../roadmap/outstanding-work.md) and [`weightroom-work.md` §2](../../roadmap/weightroom-work.md).

**Read first:** `WPF2_HANDOFF.md` §2 (decisions 2 and 5), §5 and §6a — the whole of §6a's step 2 is
the finding; `H6_HANDOFF.md` (an axis stored and never sent — the same shape); `N4`'s handoff and
ADR-0119 (the host-memory cap that `--fit off` is part of); ADR-0071 (the digest file);
`packages/modelrack/spec.md`'s llama.cpp launch section; `MEMORY_SAFETY.md` §2.

**Code to read first:** FreeWeight's run-start path from the Runs form and from the API
(`services/runs.py` or wherever `POST /api/v1/runs` lands), the **repeat** path WPF2 fixed for the
adapter, and whatever *warm* server reuse FreeWeight does before launching; ModelRack's
`LlamaCppProvider` launch — what builds the argv, and what `read_served_context` reads back.

## What Gate C measured on the reference machine (2026-09-12)

Two `llama-server` launches in one sitting, both FreeWeight's:

```
port 8180: --model …Qwen2.5-1.5B-Instruct.Q8_0.gguf --lora …terse.gguf --lora-init-without-apply
           --ctx-size 8192 --fit off
port 8181: (started 22:23:43 PDT, in the repeat's own window)
           neither --ctx-size nor --fit off; /props answers n_ctx 32768, 4 slots
```

All three runs recorded `served_context 8192 / configured`. The run whose server carried no flag
was measured at 32 768, and the degradation fired — correctly — because the profile and the
reading disagreed. ADR-0119's cap was off for that server.

## What this row has to settle

1. **Which path builds a launch with no runtime profile.** Reproduce it without the GPU first if
   possible (the argv is visible in `ps`; a fake `server_path` that records its argv is enough).
   The candidates WPF2 named: the repeat, and the warm-server path. There may be a third.
2. **One launch, one argv.** Every FreeWeight launch of `llama-server` carries the run's
   `--ctx-size` and `--fit off` — through the same function. If two call sites build argv, that
   is the defect, not the missing flag.
3. **What a warm server that does not match the profile means.** A resident server at 32 768 is
   not the server a run at 8 192 asked for. Decide: refuse to reuse it, or restart it. Record the
   choice as an ADR if the docs do not already carry it (ADR-0023 is where profile resolution
   lives; check it first).
4. **Whether the degradation's wording changes.** WPF2 made it name both possibilities. Once the
   FreeWeight half is fixed, the ModelRack-reading possibility is the only one left — say so
   only if it is true.

## Gates

**Gate A.** Tests first: a launch from each path records the same argv, and a mismatched warm server
is handled the way decision 3 says. Implement. Run the gate, naming the interpreter. Commit.

**Gate B — the live proof.** On the reference machine, GPU free (`nvidia-smi`, ADR-0119): a run, a
repeat of it and a second run while the first's server is still warm; `ps` shows every
`llama-server` with `--ctx-size 8192 --fit off`; `/props` answers `n_ctx 8192`; no run records a
degradation for served context. Restart `freeweight.service` onto the fix before the proof and
say so.

## Finish line

- The gate green, interpreter named, coverage held; `git status --short` clean.
- `docs/history/handoffs/WPF10_HANDOFF.md`: the path that lost the profile, the decision on a
  mismatched warm server, the live argv, what this kickoff got wrong.
- The row marked done. Nothing pushed.
