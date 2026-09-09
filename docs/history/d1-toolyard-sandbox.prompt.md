# Kickoff — D1: ToolYard Phase 2, containment and tiered isolation

**Row:** D1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1.
**Model:** **Fable 5 · xhigh**, as scheduled.
**Repository:** `/home/jpk/ai/suite/py/ToolYard` — clean, pushed, gate green at `10be3ef`,
**100 %** coverage. Python **3.13.15**, coverage floor **95 %**.
**Runs after:** C2 (ToolYard Phase 1), which is **done and pushed**.
**Ships:** nothing. This rides `toolyard 0.1.0`, published at row **E2** after Phase 3. Do not bump
the version, do not tag, do not publish, **do not push**.

> ## ⛔ Never overnight
>
> [model-assignment §2.12](docs/roadmap/model-assignment.md) names batch D explicitly: *"never
> schedule a Fable/security row overnight — those phases are won by review, and their failures are
> silent."* [outstanding-work §4](docs/roadmap/outstanding-work.md) requires the diff to be reviewed
> **same-day**. Run this attended, in daylight.

**Why xhigh, and why reviewed.** This is adversarial work with a silent-failure class: **an escape
that works is quiet.** A containment bug does not turn a test red — it lets a path through, and the
only thing standing between a model-supplied string and the filesystem outside the workspace is the
code written in this row. The one hard edge downstream is a security ordering:
**D1/E2 before E4** ([§3](docs/roadmap/outstanding-work.md)) — no tool executes inside PromptCadence
before this discipline is published.

**This row is independent of D2 and D3.** Batch D groups three rows by model tier, not by
dependency: D1 needs C2, D2 needs C4, D3 needs A1+C5, and none of the three needs another. Run it
alone or alongside the others; the order is free.

---

## Preconditions

* **The spec was amended on 2026-09-03, and this row implements into the amended text.** C2 built
  five public shapes §7 did not describe and proposed each as an amendment rather than a quiet
  deviation. All were accepted (docs `9e70a9e` and `864dfbe`), with one rename and two additions.
  **Read the current [`spec.md`](docs/packages/toolyard/spec.md), not `docs/history/C2_HANDOFF.md`'s proposal
  blocks** — the handoff records what was *proposed*, the spec records what was *decided*, and they
  now differ.
* **The refusal reason is `not_approved`, never `not_in_intent`** (ToolYard `4ad88f2`).
  `ExecutionIntent` is a PromptCadence concept and does not belong in a layer-3 package's closed,
  machine-readable refusal vocabulary. If you find the old string anywhere, it is a leftover.
* **Both isolation tiers are available on this machine** — see the next section. This is unusual
  and it means the marked suite is genuinely runnable rather than aspirational.
* **`git status --short` must be empty before you start.**
* **You are not authorised to push, tag or publish.** Commit on `main` and stop.

## The machine, verified 2026-09-03

```text
/usr/bin/bwrap                       present
/usr/bin/docker                      present, daemon reachable
kernel unprivileged_userns_clone     1
```

So `tests/integration/test_isolation.py` runs here, and Phase 2 acceptance criterion 1 — *"the
containment suite passes with zero live-sandbox dependencies; the marked suite passes on the
reference machine"* — is fully achievable in this session rather than deferred to an operator.

**The trap that comes with it.** The tier probe walks container → bwrap → refuse, so with Docker
present it returns `CONTAINER` and **the bwrap rung never executes.** A ladder whose middle step is
never taken is a ladder with an untested step, and bwrap is the rung most deployments actually land
on — a machine with no container runtime is the common case this package exists to serve. Force the
lower rung explicitly (inject the probe's view of what is available, rather than mutating the host)
and exercise it. Say in the handoff how you forced it.

The venv is ordinary: only `toolyard` itself is editable, and `baseaicore 0.4.1` comes from PyPI.
`pip install -e ".[dev]"` is safe here.

## Setup

```bash
cd /home/jpk/ai/suite/py/ToolYard
source .venv/bin/activate
pip install -e ".[dev]"
git status --short        # must be empty before you start
```

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository.
* **Read before writing**, in this order:
  [`architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, then the
  ToolYard section of [`standards/gold-standards.md`](docs/standards/gold-standards.md) §2
  (lines 192–206), then the reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations`; units in every numeric name; keyword-only for anything optional; injected clocks and
  roots; `mypy --strict`; line length 100.
* **Finish line:** `ruff format --check . && ruff check . && mypy src tests && lint-imports &&
  pytest -m "not live and not performance"` all green, coverage ≥ **95 %**, `CHANGELOG.md` updated
  under `## [Unreleased]`, one Conventional Commit per logical group. **Name the interpreter and the
  exact invocation in the handoff** (M5C-13) — this venv is Python 3.13.15; confirm rather than
  copy. There is no `python3.12` on this machine.
* **Documentation is mirrored.** Anything amended under `/home/jpk/ai/suite/docs/` is edited in the
  workspace copy **first**, then re-copied into `py/ToolYard/docs/` and verified with `cmp`. Do not
  reflow markdown you edit. Expect to amend nothing — the spec was amended for you already.

## Reading list

1. [`packages/toolyard/spec.md`](docs/packages/toolyard/spec.md) — **§7 as amended**: the `Sandbox`
   Protocol, `SubprocessResult`, `PathAccess`, `ToolSpec.path_args` and `requires_isolation`, and
   the construction-time schema rules. Then **§11.3 and §11.4 as amended**, which are the two
   contracts this row makes true, and **§14**, which now carries the `$ref` control and the
   environment-allowlist rule.
2. [`packages/toolyard/development-plan.md`](docs/packages/toolyard/development-plan.md) **Phase 2**
   — the work, the tests, the acceptance criteria, the named risks and likely failure modes.
3. [ADR-0018](docs/adr/0018-external-benchmark-isolation.md) — the tier ladder, applied verbatim.
   `UNAVAILABLE` ⇒ refusal, never an unisolated run.
4. [ADR-0053](docs/adr/0053-a-refused-tool-call-is-a-result-not-an-exception.md) (this is D-9) —
   decision 4 above all: nothing a model influences raises.
5. **`docs/history/C2_HANDOFF.md` §4(c)** — *"the sandbox seam: what D1 must implement, and what it must not
   change"*, written for this row. Also **§5** (how the fixed refusal order is enforced
   structurally, and how it is proven to bite) and **§10** (which import-linter contracts this phase
   may extend).
6. The code, in this order: `src/toolyard/containment.py` (`PathContainment`, `SandboxPaths`,
   `PathAccess`, `SubprocessResult`, `IsolationTier`); `src/toolyard/executor.py`'s check #5;
   `tests/unit/test_containment.py`, which is the containment contract.

## The work

Phase 2's plan is complete and I am not restating it. Five things worth being explicit about:

1. **Compose or subclass `PathContainment` for the path half — do not re-derive it.** A second
   resolution-then-check implementation is a second chance to compare before resolving. Phase 1's
   version is honest in both halves and its tests are the contract.
2. **Exercise both rungs of the ladder** — see the machine note above. This is the single most
   likely way this row ends green while leaving the rung that matters untested.
3. **The probe executes a canary**, never trusts a version string. That is the plan's own mitigation
   for bwrap flag variance across distributions, and it is the difference between a probe and a
   guess.
4. **`requires_isolation` is load-bearing, and §11.4 now says so in the spec.** ToolYard cannot
   detect a handler that reaches a subprocess without declaring it, and the no-`shell=True` grep
   covers only this package's own `src/`, not application-supplied handlers. Nothing in this row
   fixes that; do not write a docstring that implies otherwise.
5. **`env=None` means the empty allowlist, never `os.environ`** (§7 and §14). Resource limits are
   applied where the platform supports them and **recorded in `limits_unenforced` where it does
   not** — ADR-0016's rule in the place this phase needs it: an unenforceable limit is reported,
   never assumed.

## Before you finish — closing duties

1. **Write `docs/history/D1_HANDOFF.md` at the workspace root.** Sections: gate results with the interpreter and
   exact commands; the tier probe's behaviour on this machine and **how the bwrap rung was forced**
   so it was genuinely exercised rather than masked by the container tier; the containment cases
   covered and what each proves; the decisions you made where a document left an edge; what E2 and
   E4 must not relitigate; the commits; and **"Before the next session"** — at minimum: push `main`,
   confirm CI green, and the reminder that this rides `0.1.0` at E2 rather than publishing now.
   **Never overwrite an existing root file** — the workspace root is not a git repository. If
   `docs/history/D1_HANDOFF.md` exists, write `D1_HANDOFF.2.md` and say why.
2. **Summarise in chat**: what was built, what the gate said with the interpreter named, what you
   decided at each edge, and what is waiting on the operator.
3. **Everything committed on `main`, working tree clean, nothing pushed, nothing tagged.**

## Constraints and stop rules

* **No version bump, no tag, no publish, no push.** This rides `0.1.0` at E2.
* **Do not implement Phase 3.** The built-in tools — `read_file`, `write_file`, `list_dir`,
  `run_command`, `http_fetch` — are E2's. A thing you notice E2 will need is a finding for the
  handoff, not a module in this row.
* **Never weaken or delete an `.importlinter` contract.** The `toolyard.sandbox -> subprocess`
  exemption is **already written**, so this row adds a module and changes no boundary rule.
* **Never give `PathContainment` or its successor a flag** that skips resolution, compares before
  resolving, or widens a root per call. A "just this once" option is what makes a containment
  advisory instead of a containment.
* **Never make `Sandbox` optional on the executor**, and never let a missing tier fall through to an
  unisolated run.
* **Do not change the fixed refusal order**, or check #5's internal order (isolation, then paths),
  without an ADR.
* **No `shell=True`, anywhere.** `tests/unit/test_boundaries.py` already fails on it.
* **Extend `tests/unit/test_containment.py`; never relax it.**
* **Working-tree integrity** (`CLAUDE.md`): `git status --short` at the start and end; commit per
  logical group; never `git add -A`.
* **A silent failure is this row's failure mode.** Where a guarantee cannot be proven on this
  machine, say so plainly in the handoff and make it an operator step. Do not let an unrunnable test
  read as a passing one.
* If you must stop early, stop at a green gate with a commit and a clean tree, and record exactly
  where you stopped in `docs/history/D1_HANDOFF.md`.
