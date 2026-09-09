# Kickoff — D2: PromptCadence Phase 3, LoadCoach client, bypass loop, events and recovery

**Row:** D2 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Fable 5 · xhigh**, as scheduled.
**Repository:** `/home/jpk/ai/suite/PromptCadence` — clean, pushed, `752966f`. Python **3.13.15**,
coverage floor **85 %** (application floor).
**Runs after:** C4 (PromptCadence Phase 2), which is **done and pushed**. PromptCadence's phases run
**strictly in order** ([§3](docs/roadmap/outstanding-work.md)).
**Ships:** nothing. This rides `promptcadence 0.9.0b0` at **M11**. Do not bump the version, do not
tag, do not publish, **do not push**.

> ## ⛔ Never overnight
>
> [model-assignment §2.12](docs/roadmap/model-assignment.md) names batch D explicitly: *"never
> schedule a Fable/security row overnight — those phases are won by review, and their failures are
> silent."* [outstanding-work §4](docs/roadmap/outstanding-work.md) requires the diff to be reviewed
> **same-day**. Run this attended, in daylight.

**Why xhigh.** The schedule calls this *"the LoadCoach-P5-shaped phase: no feedback loop for the
interesting failures, and the fake doubles the stakes."* Both halves matter. The interesting
failures here — a turn lost to a kill −9, an event written separately from the state change it
describes, a lease that expired mid-turn — do not announce themselves; they produce a trajectory
that looks finished and is not. And **the fake LoadCoach you build in this row is trusted by every
phase after it**: E4, F1, F2, G1 and the 1.0 verification all test against it. A fake that is more
permissive than the real thing converts a would-be integration failure into a green suite, four
phases downstream, where nobody is looking for it.

**This row is independent of D1 and D3.** Batch D groups three rows by model tier, not by
dependency: D1 needs C2, D2 needs C4, D3 needs A1+C5, and none needs another.

---

## Preconditions

* **C4 wrote you a brief.** `docs/history/C4_HANDOFF.md` **§10 "To D2"** lists what is settled and must not be
  redesigned, what is deliberately absent, and which seams you may extend. Read it **before** the
  development plan — it will save you from re-deciding things that are already decided.
* **`tests/fakes/` does not exist yet.** The fake LoadCoach is yours to create, and it is the
  highest-leverage artifact in this row.
* **Two items open from earlier rows, neither blocking:** the `promptcadence` PyPI name is
  unreserved, and B4's tier-defaults judgment call is unchanged. Record them in the handoff; do not
  chase them.
* **`git status --short` must be empty before you start.**
* **You are not authorised to push, tag or publish.** Commit on `main` and stop.

## The machine

There is no live LoadCoach running here, and this row does not need one: the fake is the point, and
acceptance criterion 1's *"against a real local LoadCoach"* half is a **`live`-marked** test and an
operator step. The default suite must pass with no LoadCoach, no GPU and no network.

The venv is ordinary — only `promptcadence` itself is editable; `baseaicore 0.4.1`, `setspec 0.4.0`,
`weightsdb 0.2.1` and `mirrorwall 0.2.1` all come from PyPI wheels. `pip install -e ".[dev]"` is
safe here.

## Setup

```bash
cd /home/jpk/ai/suite/PromptCadence
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be empty before you start
```

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository.
* **Read before writing**, in this order:
  [`architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, then the
  PromptCadence section of [`standards/gold-standards.md`](docs/standards/gold-standards.md) §2
  (lines 159–179), then the reading list below.
* **The application layering holds:** `web` → `cli` → `services` → `domain`, `web` and `cli`
  independent of each other, `domain` importing no framework. Route handlers and CLI command bodies
  contain no business logic — they call one service method and render.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations`; units in every numeric name; keyword-only for anything optional; injected clocks and
  HTTP clients; `mypy --strict`; line length 100. Async at the HTTP edge only (ADR-0003); SSE for
  streaming, never WebSockets (ADR-0004).
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **85 %**, `CHANGELOG.md` updated
  under `## [Unreleased]`, one Conventional Commit per logical group. **Name the interpreter and the
  exact invocation in the handoff** (M5C-13) — this venv is Python 3.13.15; confirm rather than
  copy. There is no `python3.12` on this machine.
* **Documentation is mirrored.** Anything amended under `/home/jpk/ai/suite/docs/` is edited in the
  workspace copy **first**, then re-copied into `PromptCadence/docs/` and verified with `cmp`. Do
  not reflow markdown you edit.

## Reading list

1. [`apps/promptcadence/development-plan.md`](docs/apps/promptcadence/development-plan.md)
   **Phase 3** — the work, the tests, the acceptance criteria, the known risk (the fake drifting).
2. [`apps/promptcadence/lifecycle.md`](docs/apps/promptcadence/lifecycle.md) **§8.3 "Recovery
   edges"** and **§10 "Determinism and testability"**.
3. [ADR-0036](docs/adr/0036-queue-recovery-transitions.md) — the recovery transitions.
4. [ADR-0044](docs/adr/0044-a-state-change-and-its-event-are-one-write.md) — to be **asserted with a
   crash-between test**, not merely honoured.
5. [ADR-0056](docs/adr/0056-every-turn-executes-under-one-execution-intent.md) —
   `mint_bypass_default` is T3's, and `intent.provenance(trajectory_id=…, tier=…)` is the only path
   to a `TurnProvenance`. There is a test that fails if you add a second one.
6. [`roadmap/promptcadence-roadmap.md`](docs/roadmap/promptcadence-roadmap.md) **§9, row I10** — the
   contract tests against LoadCoach's committed OpenAPI snapshot that keep the fake honest.
7. **`docs/history/C4_HANDOFF.md` §10.**
8. LoadCoach's own [`apps/loadcoach/api.md`](docs/apps/loadcoach/api.md) §§4–5 — the response shapes
   the fake must speak, and the error rows the client must map.

## The work

Phase 3's plan is complete. Four things worth stating plainly:

1. **Build the fake before the loop.** The plan says so, and the reason is the `FakeProvider` lesson
   one layer up: every downstream phase tests without a GPU or a live LoadCoach. **Make it stricter
   than LoadCoach wherever they differ, and record every place they differ** — a permissive fake is
   worse than no fake, because it makes a real integration failure invisible until F2.
2. **Wire I10's contract tests in this row rather than deferring them.** They compare the fake
   against LoadCoach's committed OpenAPI snapshot, and they are the only mechanism that stops the
   fake drifting. The plan names that drift as this phase's known risk; the mitigation belongs in
   the same phase as the risk.
3. **Kill −9 mid-turn is the test that matters.** Recovery resumes or halts per lease, with **no
   duplicate turn and no orphaned job** — a cancel is issued for in-flight work that cannot be
   reconciled. Write it as a real process kill, not a simulated exception.
4. **A `LENGTH` or `ERROR` finish reason is never read as success.** The plan calls this out
   because it is the quiet one: a truncated answer that flows onward as a completed turn.

### One thing that changed under you on 2026-09-03 — read this before writing the fake

Row C6 landed, so **LoadCoach's `usage` object now carries four token classes** plus
`thinking_tokens`:

```json
"usage": {"input_tokens": 812, "output_tokens": 1104,
          "cache_write_tokens": 0, "cache_read_tokens": 128,
          "thinking_tokens": "unsupported"}
```

Three answers a cache class can give, and none renders as another: a **number** is a count; **`0`**
is a real count meaning the provider's protocol could not have billed that class; the **string
`"unsupported"`** means the class was never reported and is not a number — never coerce it to `0` or
total it.

**Until `modelrack 0.7.0` ships (row H1) and LoadCoach adopts it (row H2), every real adapter
reports the cache classes `"unsupported"`.** After that they report `0` or a count. **Teach the fake
both shapes**, because F1's budget estimator must not be written against the interim one and will
be built against your fake. `docs/history/C6_HANDOFF.md` **§6** carries the before/after JSON and the reasoning.

## Before you finish — closing duties

1. **Write `docs/history/D2_HANDOFF.md` at the workspace root.** Sections: gate results with the interpreter and
   exact commands, saying plainly which legs are `live`-marked and did not run; what was built; the
   recovery semantics as implemented and how the crash-between test proves ADR-0044; the decisions
   you made where a document left an edge; the commits; and **"Before the next session"** — at
   minimum: push `main`, confirm CI green, the marked live journey against a real LoadCoach, and the
   reminder that this rides `0.9.0b0` at M11.
   **Never overwrite an existing root file** — the workspace root is not a git repository. If
   `docs/history/D2_HANDOFF.md` exists, write `docs/history/D2_HANDOFF.2.md` and say why.
2. **A section written for E4 and F1 — the most important thing this handoff carries.** What the
   fake LoadCoach models, what it deliberately does **not** model, and every place it is stricter or
   looser than the real thing. Three phases will trust it without re-reading its source.
3. **Summarise in chat**: what was built, what the gate said with the interpreter named, what you
   decided at each edge, and what is waiting on the operator.
4. **Everything committed on `main`, working tree clean, nothing pushed, nothing tagged.**

## Constraints and stop rules

* **No version bump, no tag, no publish, no push.** This rides `0.9.0b0` at M11.
* **Do not implement Phase 4.** Tools, money, egress and planning are all deferred by name in the
  plan. `toolyard` is not a dependency of this row — and note gold-standards' PromptCadence rule:
  **no provider access of any kind**, `modelrack` is never imported, at module level or anywhere
  else.
* **Never teach the fake a response shape LoadCoach does not actually produce.** If you cannot find
  it in `api.md` or the OpenAPI snapshot, it does not go in the fake.
* **Never write a state change and its event as two writes** (ADR-0044).
* **Never add a second path to a `TurnProvenance`** — `intent.provenance(...)` is the only one, and
  a test enforces it.
* **Never let a `LENGTH` or `ERROR` finish reason read as success.**
* **Never weaken `.importlinter`** to make an import work.
* **Working-tree integrity** (`CLAUDE.md`): `git status --short` at the start and end; commit per
  logical group; never `git add -A`.
* **A silent failure is this row's failure mode.** Where a guarantee cannot be proven without a live
  LoadCoach, say so plainly and make it an operator step. Do not let an unrunnable test read as a
  passing one.
* If you must stop early, stop at a green gate with a commit and a clean tree, and record exactly
  where you stopped in `docs/history/D2_HANDOFF.md`.
