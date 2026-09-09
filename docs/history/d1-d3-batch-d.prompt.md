# Batch D — the index

**Rows:** D1, D2 and D3 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md)
§1. **Model:** **Fable 5 · xhigh** for all three, as scheduled — no deviation.

**This document is an index, not a prompt.** Each row has its own complete kickoff, and each stands
alone — nothing below needs to be read alongside them:

* [`docs/history/d1-toolyard-sandbox.prompt.md`](d1-toolyard-sandbox.prompt.md) — ToolYard Phase 2: containment
  and tiered isolation.
* [`docs/history/d2-promptcadence-loadcoach-client.prompt.md`](d2-promptcadence-loadcoach-client.prompt.md) —
  PromptCadence Phase 3: LoadCoach client, bypass loop, events, recovery.
* [`docs/history/d3-modelrack-llamacpp.prompt.md`](d3-modelrack-llamacpp.prompt.md) — ModelRack Phase 6:
  `LlamaCppProvider` and process supervision.

---

## ⛔ None of these runs overnight

[model-assignment §2.12](docs/roadmap/model-assignment.md) names batch D explicitly: *"never
schedule a Fable/security row overnight — those phases are won by review, and their failures are
silent."* [outstanding-work §4](docs/roadmap/outstanding-work.md) requires the diff to be reviewed
**same-day**. The three rows share a failure signature: **an escape that works is quiet, a recovery
that loses a turn is quiet, and an orphaned process is quiet.** None announces itself with a red
test. Each row's prompt repeats this; it is here because it is the one rule that governs the batch
rather than any single row.

## These are three independent rows, not a chain

| Row | Depends on | State of that dependency | Ships at |
|---|---|---|---|
| **D1** — ToolYard P2 | **C2** | Done, pushed, gate green, 100 % coverage | `toolyard 0.1.0`, row E2 |
| **D2** — PromptCadence P3 | **C4** | Done, pushed, `752966f` | `promptcadence 0.9.0b0`, M11 |
| **D3** — ModelRack P6 | **A1 + C5** | Both done; C5 at `94bf5ce`, unpushed | `modelrack 0.7.0`, row H1 |

The batch letter groups them by **model tier**, nothing more. No D row depends on another. §1
sanctions running one letter back-to-back in a sitting, and you may — but the order is free, and a
failure in one does not block the others.

## Suggested order, and what to drop

**D1 → D2 → D3, as three sessions in one day**, each reaching its own green gate and commit before
the next begins — not one continuous session. The review these rows are won by is per-row, and a
single session that ends half-way through D2 leaves two repos unreviewed instead of one.

**If the day runs short, drop D3.** [§3](docs/roadmap/outstanding-work.md) marks it genuinely
flexible — *"the ModelRack stream can slot anywhere after C5, whenever harness work blocks."*
D1 carries a hard edge downstream (**D1/E2 before E4** — no tool executes in PromptCadence before
the discipline is published, a security ordering), and D2 is on M11's critical path.

## Machine facts that decide what each row can prove

Verified 2026-09-03. Each row's own prompt carries the detail; this is the summary.

* **D1 — both isolation tiers are present** (`bwrap`, `docker` with a reachable daemon, unprivileged
  userns enabled), so the marked isolation suite and Phase 2's acceptance criterion 1 are genuinely
  runnable here. **The probe returns `CONTAINER` first and will mask the `BWRAP` rung** unless a
  test forces it.
* **D3 — `llama-server` is absent.** No llama.cpp build anywhere. The spawn seam must be injectable
  from the first commit or P8's leak tests inherit the same untestability, and the live journey
  becomes an operator step on LA1's critical path.
* **D3 — five real GGUF files** (~40 GB) are on disk, so discovery and hashing can be exercised for
  real. Full-content sha256 is what the identity contract names, and hashing 40 GB per discovery
  call is minutes of I/O — the caching decision is load-bearing.
* **All three venvs are ordinary**: only the package itself is editable, suite dependencies come
  from PyPI wheels. `pip install -e ".[dev]"` is safe in all three, unlike LoadCoach's venv.
* **All three interpreters are Python 3.13.15.** There is no `python3.12` on this machine.

## What binds across the batch

* **Nothing is pushed, tagged, published or version-bumped.** Commit on `main` in each repo and
  stop. Three repos means three independent commit streams; **never `git add -A`**.
* **Do not implement a later phase.** D1 is not E2's built-in tools; D3 is not P7's adapters; D2 is
  not Phase 4's tools, money, egress or planning.
* **Do not weaken `.importlinter`** in any repo, and do not reflow mirrored markdown — prove every
  mirror with `cmp`.
* **Where a guarantee cannot be proven on this machine, say so plainly and make it an operator
  step.** Do not let an unrunnable test read as a passing one.
