# Kickoff — E1 + E2 in one session: CutCtx and ToolYard to their first publish

**Rows:** E2 and E1 of [`docs/roadmap/outstanding-work.md`](docs/roadmap/outstanding-work.md) §1,
run back-to-back in one sitting — §1 sanctions exactly this: *"consecutive rows with one letter can
be run back-to-back in one sitting."* They are the same batch letter and the same model, and they
share nothing else: E2 needs D1, E1 needs C1, and neither needs the other.
**Model:** **Sonnet 5 · high** for both, as scheduled. No deviation to record.
**Repositories, in the order this document runs them:** `/home/jpk/ai/suite/py/ToolYard`, then
`/home/jpk/ai/suite/py/CutCtx` — both Python **3.13.15**, coverage floor **95 %** — plus
`/home/jpk/ai/suite/LoadCoach` for the shared fetch vectors (**tests only**, §2.4) and
`/home/jpk/ai/suite/docs` for any amendment you propose.
**Ships:** both rows end at a **first publish** — `toolyard 0.1.0` and `cutctx 0.1.0`.
**You prepare each release and stop at the tag.** Tagging, the `pypi` environment approval and the
post-publish install check are the human's ([outstanding-work §4](docs/roadmap/outstanding-work.md)).
No push either: commit on `main` in each repository and stop.

**Overnight:** permitted. Batch E is on none of
[model-assignment §2.12](docs/roadmap/model-assignment.md)'s never-overnight lists (batches D and G
and I2's security half), and Sonnet rows run at effort **high** overnight, which is already this
row's scheduled effort. Two things gate the publishes and cannot happen overnight, so neither
package publishes at the end of this session in any case: **the Opus review of the fetch-handler
diff** (row E2's own note) and **the podman isolation run** (§1.4).

---

## ⛔ Read this first — ToolYard's `main` is red

D1 was pushed and the roadmap's ops item says "confirm CI green". It is not green. Verified
2026-09-03 on run `33794677196` (`03eca68`, the current tip of `main`):

```text
tests (3.12)     FAILURE   2 failed, 535 passed, 40 skipped, 4 deselected
tests (3.13)     cancelled by fail-fast (all its steps passed: 537 passed, 40 skipped, 100 % cov)
install-check    FAILURE   python -c "import cutctx"
every other job  success   (security, lint, boundaries, contracts, build, format, types, 3.14)
```

**Two separate defects, and neither can be reproduced by the local gate.** Fixing both is E2's
first work, before a line of Phase 3 is written. A package does not publish `0.1.0` off a red `main`.

**Defect 1 — containment answers differently on 3.12 than on 3.13.**

```text
FAILED tests/unit/test_containment.py::TestUnusablesCandidates::
       test_a_symlink_loop_stays_inside_the_root_rather_than_crashing[phase-1]
       toolyard.containment.PathEscape: path escapes read_roots
   (and the same case [phase-2], i.e. under TieredSandbox as well as PathContainment)
```

The test's docstring states the premise: *"`Path.resolve()` gives up on a cycle and returns the path
unresolved."* That is true on 3.13 and **false on 3.12**, where `resolve(strict=False)` raises
`RuntimeError("Symlink loop from …")` over `OSError(ELOOP)`; `PathContainment` catches
`(OSError, ValueError, RuntimeError)` and turns it into `PathEscape`. So the *behaviour* differs by
interpreter, not just the test — and 3.12 is the declared baseline
([CLAUDE.md](CLAUDE.md), CI's blocking matrix).

This is a decision, not a patch. **Recommended: one answer on every supported interpreter, chosen
fail-closed** — an unresolvable cycle is refused (`PathEscape`), because nothing is lost (the OS
refuses to open it either way), because ADR-0018's floor is refusal, and because a containment answer
that depends on the interpreter is itself the defect. The other answer — admit it everywhere, by
detecting the cycle in `containment` rather than delegating to `Path.resolve` — is defensible and you
may take it; what is not available is leaving the answer to the interpreter, or skipping the test on
3.12. **`test_a_loop_whose_first_hop_leaves_the_root_is_still_refused` stays refused either way.**
Whichever you choose, the amended docstring must stop asserting the 3.13 premise as a fact about
Python, and the test must **prove the 3.12 path here**, on 3.13, by simulating the raise (monkeypatch
the resolution seam to raise `RuntimeError`/`OSError(ELOOP)`) — there is no `python3.12` on this
machine and CI is the only real proof, which arrives after the operator pushes.

**Defect 2 — the install check has never checked this package.** `.github/workflows/ci.yml:136`
runs `python -c "import cutctx"`: the toolchain was copied from CutCtx (C2's setup block says so) and
this line was never adapted. It is the only leftover — `grep -rn cutctx` over `.github/`,
`pyproject.toml`, `requirements/`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md` finds nothing else.
The job it breaks is precisely the one that proves the built wheel imports, which is the gate a first
publish rests on. Fix it as its own commit and say so in the changelog.

---

## Order, and the checkpoint between the rows

**E2 first, then E1.** E2 carries the only hard edge in batch E —
**D1/E2 before E4** ([§3](docs/roadmap/outstanding-work.md)), a security ordering: no tool executes
inside PromptCadence before this discipline is published. It is also the larger row, the adversarial
one, and the one whose diff a reviewer will read. **E1 is genuinely flexible** — §3 lists it among
the flexible rows, *"only I1 needs it"* — so **if the session runs short, drop E1**, not E2.

**The checkpoint is hard.** ToolYard reaches a green gate, its release-prep commit and a clean tree
**before a single CutCtx file is opened.** Run `git status --short` in `py/ToolYard` and confirm it is
empty before you `cd` anywhere. Then start E1 by reading this document from the top as if it were a
fresh session — if your context has been compacted by then, that re-read is the recovery.

If ToolYard's gate is not green, or the shared-vector question (§2.4) is unresolved, or the symlink
decision above is unsettled: **stop there.** Write `docs/history/E2_HANDOFF.md`, say exactly where you stopped, and
do not start E1.

## Preconditions

* **`git status --short` must be empty in all four repositories before you start**
  (ToolYard, CutCtx, LoadCoach, docs). `git checkout --` anything modified you did not edit.
* Both repositories are pushed and their local tips match `origin/main`: ToolYard `03eca68`,
  CutCtx `6d704bb`. **CutCtx's CI is green** at its tip; ToolYard's is not (above).
* **`baseaicore 0.4.1` is published** — both packages pin `>=0.4.1,<0.5` and both locks carry it.
  Nothing else in either graph is unpublished.
* **Both PyPI names are free.** `https://pypi.org/pypi/cutctx/json` and `.../toolyard/json` both
  return **404**, checked 2026-09-03. Master architecture §1.1 requires availability to be verified
  before first publish; it is verified. Reserving them is an operator step and it should happen
  before the tags — a name taken in the interval changes the import name, `pyproject.toml`,
  `.importlinter`, the coverage paths and every document that names the package.
* **You are not authorised to push, tag or publish.** Prepare both releases, stop at the tags, and
  say plainly in each handoff what is waiting.
* Both venvs are ordinary — only the package itself is editable, `baseaicore` comes from PyPI —
  so `pip install -e ".[dev]"` is safe in both. **LoadCoach's venv is not**: do not run `pip install`
  in it (its suite dependencies are editables pointing at the working trees; pip would replace them).

## The machine, verified 2026-09-03

```text
/usr/bin/bwrap        present            /usr/bin/docker   present, daemon reachable
/usr/bin/prlimit      present            podman            ABSENT
python3.13 3.13.15    python3.14         python3.12        ABSENT
```

Consequences for this session:

* **The isolation ladder's container rung runs under docker here, and the bwrap rung is reachable**
  through D1's injected `which` seam (`docs/history/D1_HANDOFF.md` §3). Both rungs stay exercised by the suite you
  inherit; E2 adds no rung and forces none.
* **Podman is still unverified**, and row E2 requires `pytest -m isolation -rs` on a podman host
  *before* `0.1.0` publishes (`docs/history/D1_HANDOFF.md` §13 row J). That cannot be done here. It is an operator
  step, it belongs in `docs/history/E2_HANDOFF.md`'s "Before the next session", and it is a **publish blocker**,
  not a nice-to-have.
* **No 3.12 anywhere**, so the CI failure above is un-reproducible locally and the fix is proven
  only by the operator's next push. Write the simulating test regardless.
* **The fetch tests use recorded transports and no network** (spec §18, dev plan Phase 3). The
  machine has a network; that is not a licence to let a test open a socket. `tests/unit/test_boundaries.py`
  is where that stays true.

## Setup

```bash
cd /home/jpk/ai/suite/py/ToolYard          # E2 first
source .venv/bin/activate
pip install -e ".[dev]"
git status --short                          # must be empty before you start
```

```bash
cd /home/jpk/ai/suite/py/CutCtx            # E1, only after E2's gate is green and committed
source .venv/bin/activate
pip install -e ".[dev]"
git status --short
```

## Standing preamble

* **Work from inside the component directory, never the workspace root.** `/home/jpk/ai/suite` is a
  workspace, not a repository, and nothing at its root is versioned.
* **Read before writing**, in this order:
  [`architecture/master-architecture.md`](docs/architecture/master-architecture.md) §§1–3, then the
  package's section of [`standards/gold-standards.md`](docs/standards/gold-standards.md) §2 —
  ToolYard at lines 192–206, CutCtx at lines 180–190 — then the row's reading list below.
* **House method:** docstring-first — define behaviour, write the Google-style docstring including
  what the function *refuses*, write the tests against it, then implement. `from __future__ import
  annotations`; units in every numeric name; keyword-only for anything optional; injected clocks,
  roots, resolvers and transports; `mypy --strict`; line length 100.
* **Finish line, per repository:** `ruff format --check . && ruff check . && mypy src tests &&
  lint-imports && pytest -m "not live and not performance"` all green, coverage ≥ **95 %**
  (both repos stand at 100 % today — do not regress them silently), `CHANGELOG.md` updated, one
  Conventional Commit per logical group. **Name the interpreter and the exact invocation in each
  handoff** (M5C-13) — confirm 3.13.15 rather than copying it from here.
* **Documentation is mirrored.** Anything you amend under `/home/jpk/ai/suite/docs/` is edited in the
  workspace copy **first**, then re-copied into the component's `docs/` and proven with `cmp`. Do not
  reflow markdown you edit.
* **A new public name is a spec amendment, proposed, not a quiet deviation.** Both rows will want
  one or two (§2.5, §3.6); C1 and C2 both did this and the amendments were accepted — follow that
  precedent, in the same commit, docs first.

---

# Part 1 — E2: ToolYard Phase 3, the built-in tools, `toolyard 0.1.0`

## 2.1 Reading list

1. [`packages/toolyard/development-plan.md`](docs/packages/toolyard/development-plan.md) **Phase 3**
   — the work, the tests, the acceptance criteria, and the two named failure modes: *"a fetch
   redirect check applied to the first hop only"* and *"`write_file` creating parents outside the
   root via a symlinked intermediate directory."* Both are load-bearing; both are testable here.
2. [`packages/toolyard/spec.md`](docs/packages/toolyard/spec.md) — **§7 as amended at D1** (the five
   built-in signatures, `SubprocessResult.output_truncated`, `SandboxPaths`' construction rules, the
   closed `Reason` set), **§13** (the refusal table, including the row that says a fetch violation
   carries *"the specific ADR-0026 check"*), **§14** (the `$ref` control, the environment allowlist,
   `network=True` refused), **§18** and **§20** — criteria 2, 3 and 4 are this row's exit.
3. [ADR-0026 §3](docs/adr/0026-local-http-hardening.md) — the whole fetch discipline, applied
   verbatim: scheme, host allowlist, link-local refused after resolution, no cross-host redirect,
   redirect cap, size cap enforced *during* streaming, connect and read timeouts, content type
   verified before parsing.
4. [ADR-0053](docs/adr/0053-a-refused-tool-call-is-a-result-not-an-exception.md) (D-9) — nothing a
   model influences raises. Every new refusal is a `ToolResult`, driven through `execute()` in its
   test, never an exception.
5. **`docs/history/D1_HANDOFF.md` §7 and §8**, written for this row. §7 is what you must not relitigate; §8 is the
   nine findings, four of which are direct instructions to `run_command` (§2.3 below). **§13** is the
   decision table — read row A (the sandbox argument), B (`output_truncated`), G (`network=True`
   refused) and J (podman).
6. The code, in this order: `src/toolyard/executor.py` (the fixed refusal order and check #5),
   `src/toolyard/containment.py`, `src/toolyard/sandbox.py`'s `run_isolated` and `TieredSandbox`,
   `src/toolyard/types.py`'s `Reason`/`REFUSAL_REASONS`/`ToolOutput`, and
   `tests/unit/test_boundaries.py`, which is the import allowlist and the `shell=True` grep.

## 2.2 `tools/files.py`

`read_file`, `write_file`, `list_dir`. Each declares its `path_args` so **the executor's containment
check does the resolving** — a handler that resolves a path itself is a second containment, and
spec §14's rule is that path handling lives in one place. Size caps on read and on directory listing;
a missing file is `FAILED` with a clean reason and no traceback to the model; binary and
undecodable content is handled by the handler and not by an exception. `write_file` creates parents
**inside** the write root — the plan's named failure mode is a symlinked intermediate directory, so
prove that case rather than assuming `mkdir(parents=True)` is contained.

## 2.3 `tools/command.py`

D1 settled the shape; implement it, do not redesign it.

* **`run_command_tool(sandbox: Sandbox)`** — the *same* instance the executor holds (spec §7 as
  amended, `docs/history/D1_HANDOFF.md` §13 row A). It declares `requires_isolation = True`, argv only, never a
  shell string, and it calls `run_isolated`; it starts no process (§7: one `Popen` in the package,
  pinned by `test_boundaries`).
* **An explicit `PATH` allowlist**, e.g. `{"PATH": "/usr/local/bin:/usr/bin:/bin"}`. Under bwrap
  `--clearenv` leaves none. **`os.environ` is never the answer**, and the env is **caller-owned,
  never model-supplied** — a malformed env raises, which would hand a model a `handler_error` lever.
* **Never `network=True`** — refused in v1 (§13 row G).
* **Render both `output_truncated` and the exit code.** An output bomb is killed at the cap and the
  model must be able to tell a truncated success from a clean one.
* **Say in the tool's description that a backgrounded child keeps the call alive until the timeout**,
  so a model does not try to "start a server".
* **Document a floor for `ResourceLimits.process_count`.** bwrap's count includes `bwrap` itself and
  `prlimit`, so 1 or 2 refuses everything; the default is 64 and the integration suite uses 32.
  Document it; D1 deliberately did not validate one.
* Acceptance criterion 3 — *on a host with neither rung, `run_command` refuses and the record says
  why* — is provable here through D1's injected `which` seam. Prove it.

## 2.4 `tools/fetch.py`, and the vectors that must be byte-shared

The discipline is ADR-0026 §3 and LoadCoach has already implemented it once, in
`LoadCoach/src/loadcoach/infrastructure/freeweight_client.py`. Read it before you write yours: the
`FetchPolicy` value, the injected `Resolver` (which is how the link-local rule is tested without a DNS
server that answers with one), and the refusal vocabulary it already uses — `malformed_url`,
`scheme_not_allowed`, `no_host`, `host_not_allowed`, `link_local_address`, `cross_host_redirect`,
`too_many_redirects`, `content_type_not_allowed`, `too_large`.

Four things that are ToolYard's and not LoadCoach's:

* **No credentials, ever.** Spec §14: nothing in ToolYard reads or forwards application
  configuration. `http_fetch_tool(allowed_hosts, *, max_bytes=8_388_608)` is the whole surface.
  LoadCoach's five credential vectors are therefore **out** of the shared set, along with its
  evidence-specific cases (`since`, the bare-origin export path).
* **The cap is 8 MiB here and 128 MiB there.** A shared vector expressing the size cap must be
  written **relative to the configured cap**, not to either number.
* **Which content types a fetch admits is a decision to make and record** — LoadCoach admits JSON
  because it parses JSON; an agent tool reads text. Choose a closed allowlist, default closed, and
  verify it **before** the body is returned.
* **State the residual honestly.** The check resolves and then connects, so a name that changes
  between the two is not addressed by this design; do not write a docstring that implies address
  pinning you did not implement.

**The shared vector set is acceptance criterion 4 and dev-plan AC2 — *one fixture set, two
repositories, both green*.** How to make that true is this row's real design decision. Recommended,
and consistent with how the suite already shares an artefact across repos (the mirrored docs; the
vendored OpenAPI snapshot at I10): author a declarative **`tests/fixtures/fetch/adr0026_vectors.json`**
in ToolYard — each vector naming the case, the request, the scripted transport responses and the
expected outcome — drive ToolYard's parametrized test from it, then copy the file **byte-identically**
into LoadCoach's tests, drive LoadCoach's existing client from it there, and record the file's sha256
in both repositories so a drift is a failing test rather than a discovery. `cmp` proves the copy, the
same way the docs mirrors are proven.

**Bounds on the LoadCoach half — it is a released repository at 1.0.0:**

* **Tests and fixtures only. Do not touch `LoadCoach/src/`.** No behaviour change, no reason-string
  rename, no `pip install` in that venv.
* Changelog under `## [Unreleased]`, **no version bump**; it rides LoadCoach's next release (H2).
* Run LoadCoach's own gate for the files you touched and report what it said.
* **If a shared vector reveals a genuine behavioural difference between the two implementations, that
  is a finding for the handoff, not a fix in either repo** — and it is the most valuable thing this
  row could produce. Record which implementation you think is right and why.
* **If LoadCoach cannot be made green against the shared file without touching `src/`, stop at
  ToolYard's copy**, leave the LoadCoach half as an operator/next-row item, and say exactly what
  diverged. A half-shared vector set that is honestly labelled beats a shared one bought with a
  quiet source change in a released application.

## 2.5 The `Reason` vocabulary — the one amendment this row must propose

`Reason` is a **closed** set and `REFUSAL_REASONS` exports it; a property test asserts no
unrecognized reason is ever produced, and consumers exhaust it in a match. It carries nine members
today and **none of them is a fetch reason** — spec §13's fetch row says only *"the specific ADR-0026
check"*. So E2 must add them, and adding a reason is a **minor** change consumers must be told about
(§19). This is free exactly once — before the first publish — which is now.

Name them from the checks, and mirror LoadCoach's strings where the check is the same check: a
reviewer comparing the two implementations should not have to translate. Amend **spec §13's fetch row
and §7's `Reason` note in `docs/` first**, mirror into `py/ToolYard/docs/`, prove with `cmp`, and land
docs and code in the same commit. Decide deliberately which conditions are `REFUSED` (a policy check
said no) and which are `FAILED` (the transport broke, the origin returned 503) — that line is what
tells a consumer whether retrying is meaningful.

## 2.6 `httpx`, the locks, and the wire goldens

* **Declare `httpx>=0.27,<1` in the same commit that first imports it** — `requirements/README.md`
  says why, and it is ToolYard's second and last non-suite runtime dependency (gold standards §1.1).
* **Regenerate both locks** with the recorded commands and commit them:
  `pip-compile --strip-extras --extra dev --generate-hashes --output-file requirements/ci.lock
  pyproject.toml`, and the `release.lock` command beside it. They were generated with **pip-tools
  7.6.1**; `release.lock` must stay byte-identical below its header to CutCtx's, LoadLedger's,
  WeightsDB's, MirrorWall's and ModelRack's — that identity is the check that the publish chain is
  reproducible, so verify it rather than assuming it.
* **`.importlinter` already carries `toolyard.tools.fetch -> httpx` and
  `toolyard.tools.files -> pathlib`.** You add modules; you change no boundary rule. Every other HTTP
  client stays forbidden in every module, forever.
* **The five built-ins' wire definitions are golden-locked** (§19: wire-definition stability is
  golden-tested per release). Those goldens are what a model actually sees; write them as goldens,
  not as assertions about substrings.

## 2.7 Exit, and the release preparation

Spec §20 criteria 2, 3 and 4 are the exit. Criterion 2 — *a standalone script registers a custom tool
and executes it with only `toolyard` + `baseaicore` installed* — needs a **runnable acceptance
script committed in the repository** and exercised in a throwaway venv (`pip install .`), because
M10's exit condition is *"clean-venv acceptance scripts pass"*. Record the exact commands and their
output in the handoff.

Then the release-prep commit, and stop: `src/toolyard/__about__.py` `0.1.0.dev1` → `0.1.0`,
`CHANGELOG.md`'s `## [Unreleased]` becomes `## [0.1.0] - <date>` with a fresh empty `Unreleased`
above it, in a commit shaped like MirrorWall's precedent — `chore(release): prepare toolyard 0.1.0`.
**No tag. No push. No publish.**

---

# Part 2 — E1: CutCtx Phase 2, the policy set, `cutctx 0.1.0`

## 3.1 Reading list

1. [`packages/cutctx/development-plan.md`](docs/packages/cutctx/development-plan.md) **Phase 2** —
   the three policies, the tests, and the two named failure modes: *"nondeterminism via dict ordering
   in group assembly"* and *"masking a result whose call was already dropped."* The first is the row's
   named trap; the second is a chain-composition rule (§3.4).
2. [`packages/cutctx/spec.md`](docs/packages/cutctx/spec.md) — **§7** (the three constructors and
   their defaults), **§11 contracts 2–5**, **§13** (the outcome table), **§14** (a masked stub carries
   a hash, never an excerpt), **§18** and **§20**.
3. [ADR-0052](docs/adr/0052-compaction-is-a-view-and-the-package-plans-it-only.md) (D-8) — the rule
   that shapes `SummarizingPolicy` entirely: **the package plans a summarization and never executes
   one.** No model, no HTTP client, no prompt text — a `prompt_id` and a `SummarizationRequest` the
   caller fulfils.
4. **`docs/history/C1_HANDOFF.md` §3 and §4** — written for this row, and **not to be relitigated**: the
   `CompactionReport` field list, `budget_unmet` derived on the plan, `metadata` opaque to policies,
   `tool_call_id` as a correlation id, and **contract 3 read as binding removal rather than masking**
   — *within one exchange, either every member is retained (`KEEP`/`MASK`, mixed freely), or every
   member is removed by the same action.* Then **§5** (how `_invariants` is the only path to a plan,
   and the AST test that will tell you so at CI time), **§2** (the additions Phase 1 made to §7,
   including `TurnReplacement`, which exists precisely so this row does not have to migrate a frozen
   type), and **§9.2** (the oracle rule below).
5. The code: `src/cutctx/_invariants.py` first — `removable_turn_ids`, `untouchable_turn_ids`,
   `estimate_after`, `build_plan`, `validate_plan` — then `policies/drop_oldest.py` as the worked
   example of a policy, then `tests/oracles.py`, `tests/strategies.py` and `tests/goldens/`.

## 3.2 `policies/masking.py`

Mask `TOOL`-result bodies beyond the `keep_recent_results` most recent, leaving the turn in place
with a `TurnReplacement`. **The stub format is this row's to define and to golden-lock**: labelled,
carrying the original's sha256 and the original token estimate, and **never an excerpt** (§14 — the
original may hold a secret). Reasoning turns stay byte-identical; only `TOOL` bodies are touched;
`N` is respected exactly. A masked turn is *retained*, so masking beside a kept call orphans nothing
(C1 §4) — which is what makes this policy legal under contract 3 at all.

## 3.3 `policies/summarizing.py`

The oldest **contiguous** unpinned span becomes one summary turn plus one `SummarizationRequest`.
Contiguity is over `_invariants.removable_turn_ids`, not over raw indices; `min_span_turns` is a
floor, `target_ratio` sets `target_tokens`; the summary turn's id is derived
(`summary:<group_id>`, C1 §2) and a collision is refused at construction, so **`group_id` must itself
be deterministic** — derived from the span, never a counter and never a uuid, or contract 4 dies.

Two honesty points. **A whole exchange goes into a group or none of it does** (contract 3 as read).
And **the planned summary's token figure is `target_tokens` — an estimate of a text that does not
exist yet.** The executor may substitute a longer one. That is contract 5 working as intended, and
the fix is *not* to recompute anything in the report: C1 §3.1 settled that nothing in the report is
computed, only copied from the plan.

## 3.4 `policies/chain.py` — the row's real design decision

A chain runs its policies in order and stops when the budget fits. What it cannot do is what a naive
composition would do: **apply the intermediate plan and run the next policy against the resulting
view.** Applying requires summaries, and under D-8 the summaries do not exist — the package never
produces one. So the chain composes over a **projection**, and how that projection is built is the
decision to settle and record:

* the projection must be deterministic and derived only from the previous plan (a masked turn's
  replacement is known; a summary turn's id is derived and its estimate is `target_tokens`);
* the ordering of every group and every action must come from **transcript position**, never from
  iteration over a dict or a set — this is the row's named trap, and it is the kind that reproduces
  only under `pytest-randomly`'s unlucky seed unless it is golden-tested deliberately;
* composition must **reconcile the exchange rule**: a later policy that drops a call whose result an
  earlier policy masked has produced an illegal plan, and the chain must escalate the whole exchange
  to the removing action rather than let `build_plan` reject the plan at the end;
* whatever the projection, **one plan is built, once, against the real transcript, through
  `_invariants.build_plan`** — which recomputes `tokens_before`, `tokens_after_estimate` and
  `budget_unmet` and refuses a plan that disagrees. `budget_unmet` is **derived, never declared**
  (C1 §3.2). `test_no_shipped_policy_builds_its_own_plan` scans `policies/`, and `chain.py` is in
  that directory.

The dev plan also expects a **default chain** (AC2: *"the default chain compacts the Phase-1 golden
transcripts to every budget in the golden set with byte-identical plans"*). Masking, then
summarizing, then drop-oldest as the last resort. If you ship it as a public name, that is an
addition to §7 — propose the amendment, docs first, the way C1 did.

## 3.5 Tests

* Cross-matrix determinism goldens for all three policies and the default chain; the two chain
  goldens the plan names (masking alone suffices → nothing summarized; chain exhausted →
  `budget_unmet`, never truncation).
* Properties over the new policies against **`tests/oracles.py`** — and if you need a new oracle,
  **write it from the spec, never import it from `_invariants`.** C1 §9.2 records this as the trap
  that cost that session the most time: an oracle imported from the implementation makes a property
  suite look thorough and prove nothing. `CONTRIBUTING.md` points at that paragraph.
* The invariants suite must still pass unchanged for the new policies: nothing touches a system,
  pinned or protected-tail turn; no exchange is separated.

## 3.6 Contract 3, and the amendment E1 was expected to discover

C1 §9.1 flags it: read literally, spec §11 contract 3's *"masked together"* forbids the very
`ObservationMaskingPolicy` §7 ships. Phase 1 enforced the reading in §3.1's box and said **E1 is the
row that discovers whether the document or the reading is wrong.** Having now built the masking
policy, decide: either amend contract 3 to state the enforced rule explicitly (recommended — the
enforced rule is the one three policies and a chain now depend on), or amend §7's masking
description if you conclude the literal reading was right. Docs first, mirrored, `cmp`, in the same
commit. Silence is the one option that is not available.

## 3.7 Exit, and the release preparation

Spec §20 criteria 2–4 plus the dev plan's AC1/AC2. Criterion 2 — *a standalone script using only
`cutctx` + `baseaicore` plans and applies a compaction with a hand-supplied summary* — is the
quickstart **and** M10's clean-venv acceptance script: commit it, run it in a throwaway venv, record
the output. Then `src/cutctx/__about__.py` `0.1.0.dev0` → `0.1.0`, the changelog heading, and
`chore(release): prepare cutctx 0.1.0`. **No tag. No push. No publish.**

---

## Closing duties

Both rows' duties apply **separately and in full** — this is two rows, two packages and two reviews.

1. **`docs/history/E2_HANDOFF.md`** and **`docs/history/E1_HANDOFF.md`** at the workspace root. **Never overwrite an existing
   root file** — the workspace root is not a git repository; if one exists, write `En_HANDOFF.2.md`
   and say why. Each carries: gate results with the interpreter and the exact invocation; what was
   built against the spec's §7; every decision made where a document left an edge, and every
   amendment proposed with its `cmp` proof; what the *next* row must not relitigate; the commits;
   and **"Before the next session — operator steps."**
2. **`docs/history/E2_HANDOFF.md` additionally carries**: what the red-CI fix changed and why that answer rather
   than the other, plus the fact that only CI can confirm it; the shared-vector mechanism and its
   sha256, and the state of the LoadCoach half; the new `Reason` members and the REFUSED/FAILED line;
   and, at the top of the operator list, the two **publish blockers** — `pytest -m isolation -rs` on
   a podman host, and the **Opus review of the fetch-handler diff** that row E2 schedules.
3. **`docs/history/E1_HANDOFF.md` additionally carries**: the chain's projection design in enough detail that I1
   can build on it, the contract-3 decision, and the group-ordering rule that keeps plans
   byte-identical.
4. **One summary in chat** covering both rows: what changed in each repository, what each gate said
   with the interpreter named, every decision taken at an edge, and everything waiting on the
   operator — for each package: reserve the PyPI name, push, confirm CI green (**ToolYard's 3.12 job
   is the proof of the symlink fix and the install-check fix**), review, tag, approve the `pypi`
   environment, and run the post-publish install check.
5. **Everything committed on `main` in each repository, working trees clean, nothing pushed, nothing
   tagged, nothing published.**

## Constraints and stop rules

* **No push, no tag, no publish** — in any of the four repositories. Prepare and stop.
* **Never `git add -A`.** Four repositories means four independent commit streams; `git status
  --short` at the start and end of each, and commit per logical group (working-tree integrity,
  `CLAUDE.md`).
* **Never weaken or delete an `.importlinter` contract.** Both exemptions this row needs are already
  written. A "temporary" widening to make an import work is the one edit that is never temporary.
* **ToolYard: no `shell=True`, no second HTTP client, no `os.environ`, and no new `Popen`** — one
  process-launch site exists and it is `sandbox.py`. `tests/unit/test_boundaries.py` fails on all of
  these; extend it, never relax it. **CutCtx: purity stays proven, not claimed** — no HTTP client, no
  provider, no database, no filesystem access (ADR-0052), asserted by
  `tests/unit/test_packaging.py`.
* **Do not relitigate what D1 §7 and C1 §3–§4 settled.** A thing you would have designed differently
  is a finding for the handoff, not a redesign in a publishing row.
* **Do not implement a later phase.** ToolYard: no result-schema enforcement, no rate limits, no
  platform tiers, no 0.2.0 hardening (that is PromptCadence P9). CutCtx: no embedding-relevance
  policy, no note extraction, no IdeaPress-shaped policy (that is J3), no 0.2.0 hardening (that is
  PromptCadence P8). Neither row touches PromptCadence.
* **Nothing a model influences may raise** (ADR-0053) and **nothing is silently truncated**
  (CutCtx contract 4 and §13's last row). Those are the two packages' central claims and both are
  tested by fuzzing and by property, not by example.
* **Do not touch `LoadCoach/src/`**, and do not run `pip install` in LoadCoach's venv.
* **Docs are edited in the workspace copy first and mirrored byte-identically**; prove every mirror
  with `cmp` and do not reflow surrounding lines.
* **Where a guarantee cannot be proven on this machine — the 3.12 behaviour, the podman rung — say so
  plainly and make it an operator step.** Do not let an unrunnable check read as a passing one, and
  do not let a package publish on the strength of one.
* **If you must stop early, stop at a green gate with a commit and a clean tree**, in whichever
  repository you are in, and record exactly where you stopped.
