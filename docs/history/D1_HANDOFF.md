# D1 handoff — ToolYard Phase 2: containment and tiered isolation

**Row:** D1 of `docs/roadmap/outstanding-work.md` §1. **Date:** 2026-09-03, daytime, attended.
**Repository:** `/home/jpk/ai/suite/py/ToolYard`, branch `main`, started at `10be3ef` (clean, pushed).
**End state:** six commits on ToolYard `main` (`97a2316` → `03eca68`) and one on docs `main`
(`a210674`), both working trees clean, **nothing pushed, nothing tagged, no version bump.** This
rides `toolyard 0.1.0` at row E2. §13 records the twelve decisions taken with the operator after the
build; §14 records one incident during the session and what was restored.

**Same-day review is required** (outstanding-work §4). §12 below lists the lines a reviewer should
read first — the ones where a silent failure would live.

---

## 1. Gate results

Interpreter: `/home/jpk/ai/suite/py/ToolYard/.venv/bin/python` — **Python 3.13.15** (confirmed
with `python --version` inside the activated venv; there is no `python3.12` on this machine).

The exact finish-line invocation, run from inside `py/ToolYard` with the venv activated:

```text
ruff format --check .        35 files already formatted
ruff check .                 All checks passed!
mypy src tests               Success: no issues found in 28 source files
lint-imports                 Contracts: 7 kept, 0 broken.
pytest -m "not live and not performance" --cov --cov-report=term-missing
                             575 passed, 2 skipped, 4 deselected in 70.90s
                             TOTAL 1173 stmts, 0 miss, 338 branches, 0 partial — 100.00%
                             (floor 95 %; every module at 100 %, sandbox.py included)
```

The 2 skips are by design: two rung-specific proofs that skip on the *other* rung
(`test_the_bwrap_rung_was_forced_not_incidental` under the container case,
`test_the_container_rung_names_its_runtime` under the bwrap case). The 4 deselected are the
`performance` budgets, which also pass: `pytest -m performance` → `4 passed`.

The marked suite alone: `pytest -m isolation -rs` → **38 passed, 2 skipped** (the same two), in
15.1 s, under **both** real rungs on this machine. No isolation test was skipped for lack of a rung.
(The first green gate, before the §13 amendments, was 564 passed / 3 skipped; the third skip was the
loopback positive case, which no longer exists because `network=True` is now refused.)

A CI-shaped run — `pytest -m "not live and not performance and not isolation"` — holds 100 %
coverage without the integration tests, so a CI runner with neither rung keeps the floor.

Docs mirror: `cmp` of `docs/packages/toolyard/{spec,development-plan}.md` against the workspace
copies — identical. The build implemented into the spec as already amended; the post-interview
amendments are in §11 and §13.

## 2. What was built

`src/toolyard/sandbox.py` (new, one module, the `.importlinter` exemptions already written for it):

| Name | What it is |
|---|---|
| `TieredSandbox` | Phase 2's implementation of the `Sandbox` port. **Composes** `PathContainment` for `resolve_read`/`resolve_write` (delegated verbatim, never re-derived) and adds the probe and `run_isolated`. |
| `TierReport` | What the probe found: `tier`, `runtime` (`podman`/`docker`/`bwrap`), `runtime_path`, `reason` (every rung visited, in order, each skipped one with why), `limits_unenforced`, `limiter_path`. Cached per sandbox; `report()` exposes it for an application's `doctor`. |
| `ResourceLimits` | `cpu_seconds`, `memory_bytes`, `file_size_bytes`, `process_count` — positive ints, units in the names. |
| `Runner` / `Captured` | The injected process-launch boundary and what it returns (bytes, exit code, `timed_out`, `output_truncated`). |
| `_launch` | The **one** `Popen` in the package. New session, raw pipes read through a selector, per-stream cap (cap + 1 byte kept so truncation can be labelled), deadline → SIGTERM the group → 2 s grace → SIGKILL, bounded reap. |
| Constants | `DEFAULT_CONTAINER_IMAGE = "python:3.12-slim"`, `DEFAULT_MAX_OUTPUT_BYTES = 1 MiB` per stream, `PROBE_TIMEOUT_SECONDS = 20`, `UNLAUNCHABLE_EXIT_CODE = 127`, `MAX_ARGV_ITEMS = 1024`, `MAX_ARGV_BYTES = 128 KiB`. |

The executor is untouched. Check #5's order (isolation, then paths) and the fixed refusal order are
as C2 left them.

## 3. The tier probe on this machine, and how the bwrap rung was forced

**The machine.** `/usr/bin/bwrap` (bubblewrap 0.11.1), `/usr/bin/docker` (daemon 29.7.2, user in
the `docker` group, cgroup v2 with `MemoryLimit` and `PidsLimit` both true), `/usr/bin/prlimit`
(util-linux 2.41.3), `unprivileged_userns_clone = 1`, `python:3.12-slim` present locally. No podman.

**What the probe does.** Container rungs first (`podman`, then `docker`), then `bwrap`, then refuse.
For each rung it builds the **exact argv `run_isolated` would build** — the same flags, the same
`ResourceLimits`, a temporary workspace (`tempfile.TemporaryDirectory(prefix="toolyard-probe-")`)
bound the same way — around `/bin/true`, and runs it through the same launcher with a 20 s budget.
Exit 0 within budget is the only thing that counts as "available". A rung is skipped with its reason
recorded when its binary is absent, cannot be launched, times out, or exits non-zero (the tail of
its stderr goes into the reason). The container rung runs with `--pull=never`, so an absent image is
a failed canary ("No such image", exit 125 — verified by hand), never a network fetch from a probe.

**What it reports here, unforced:** `CONTAINER`, runtime `docker`, reason
`podman: not installed; docker at /usr/bin/docker ran the canary under the container tier's flags
with image 'python:3.12-slim'.`, `limits_unenforced == ()`. The docker canary takes ~0.12 s warm.

**How the bwrap rung was forced.** By shaping the probe's view, never by mutating the host. The
probe's executable lookup is an injected boundary (`which=`), and the integration suite's bwrap case
hands it:

```python
def _hide_containers(name: str) -> str | None:
    return None if name in ("podman", "docker") else shutil.which(name)
```

so `podman` and `docker` are invisible, the probe lands on bwrap and runs bwrap's **real** canary,
and every test in `tests/integration/test_isolation.py` runs a second time under it. The forced
report reads `podman: not installed; docker: not installed; bwrap at /usr/bin/bwrap ran the canary
under the bwrap tier's flags with rlimits applied inside the sandbox by /usr/bin/prlimit.` — and
`test_the_bwrap_rung_was_forced_not_incidental` asserts exactly that, *including* that `docker`
really exists on this host (so the hiding did something). Every `TestNamespaces`, `TestTheFilesystemView`,
`TestTheEnvironment` and `TestTheLimits` case passed under bwrap as well as under the container.

The same seam is how an operator forces a lower rung in production (README, "Forcing a lower rung");
there is no way to force a rung *above* what the probe found, and no rung below refusal.

## 4. What each rung actually runs

**bwrap** — `--unshare-all` (the network namespace included; there is no branch that adds
`--share-net`, since `network=True` is refused), `--die-with-parent`,
`--new-session`, `--clearenv`; `--ro-bind-try` of `/usr /bin /sbin /lib /lib64` and of six named
`/etc` entries (`alternatives`, `ld.so.cache`, `ld.so.conf`, `ld.so.conf.d`, `localtime`,
`nsswitch.conf`) — **never `/etc` whole**, never a home directory; `--proc /proc --dev /dev
--tmpfs /tmp` (the tmpfs comes *before* the workspace binds, so a workspace under `/tmp` — pytest's
is — is still bound); the workspace binds (§5); `--chdir <write_root>`; one `--setenv` per
allowlisted variable; `--`; then `prlimit --cpu=N --as=N --fsize=N --nproc=N --`; then the argv.

**container** — `run --rm --pull=never --name toolyard-<uuid4 hex>`, `--network=none`
(unconditional), `--read-only`, `--tmpfs /tmp:rw,noexec,nosuid,size=256m`, `--memory N
--memory-swap N` (swap off), `--pids-limit N`, `--ulimit cpu=N:N`, `--ulimit fsize=N:N`,
`--cap-drop=ALL`, `--security-opt no-new-privileges`, `--user <uid>:<gid>`, (`--userns=keep-id`
for podman only), `--workdir <write_root>`, one `--volume src:src:rw|ro` per root, one `--env K=V`
per allowlisted variable, the image, the argv.

**Both** — the launcher is handed `{"PATH": "/usr/bin:/bin"}` and nothing else; `argv[0]` is the
absolute path the probe found. Under a container the runtime's CLI dying does not stop the
container, so a timed-out or output-capped run is followed by `<runtime> rm -f <name>` (best
effort, 10 s budget, DEBUG-logged if it fails — a container the runtime will not remove is a host
fault to log, not a reason to hide the result).

## 5. The containment cases covered, and what each proves

**Path half — `tests/unit/test_containment.py`, now parametrised over both implementations**
(`PathContainment` and `TieredSandbox` on a host with no rung). Every pre-existing case runs
against both, so the second cannot drift from the first; nothing was relaxed. Traversal (`..`) out
and back in; absolute path outside every root; symlinked file and symlinked directory out of the
root refused *after* resolution; a symlink that stays inside admitted; prefix-collision roots
(`data` vs `database`); root-is-inside-itself; read root readable and not writable; write root
readable; with no read roots only the write root is readable; blank, NUL-bearing, lone-surrogate,
absurdly long and non-string candidates refused before the filesystem is touched; a missing root
admits nothing; a symlink loop inside the root admitted (ELOOP at open) and a loop whose first hop
leaves the root refused. Plus, for the tiered sandbox: no rung ⇒ `UNAVAILABLE`; `run_isolated`
refuses; no attribute named `skip`/`unsafe`/`widen`/`allow`/`host` exists on either implementation.

**Subprocess half — `tests/integration/test_isolation.py`, under both real rungs.** What each proves:

| Test | Proves |
|---|---|
| `test_the_process_lives_in_its_own_pid_namespace` | `os.getpid()` inside < 50: a pid namespace, so a timeout's kill of pid 1 takes everything. |
| `test_the_network_is_unreachable` | `connect(1.1.1.1:53)` fails with ENETUNREACH immediately — no route, not a timeout. |
| `test_loopback_is_reachable_only_when_network_is_asked_for` (bwrap) | Without `network=True` even loopback is gone; with it, a listener in the test process is reachable. `--share-net` does what it says and nothing less. |
| `test_a_file_outside_the_roots_does_not_exist_inside` | A sibling of the workspace on the host is "No such file" inside — the mount namespace, not just resolution. |
| `test_a_planted_symlink_reaches_nothing_outside` | The symlink race from inside: the command creates `write_root/planted → <host secret>`; reading it inside finds nothing; on the host the link exists and *does* resolve. The sandbox's view has no target to race for. |
| `test_a_read_root_is_readable_and_not_writable` | `cat` works; `open(..., "w")` fails with **EROFS (30)** — the ro bind, not a permission accident. |
| `test_the_write_root_is_writable_and_the_file_lands_on_the_host` | The working directory is the resolved write root; a relative write lands on the host. |
| `test_the_runtime_is_read_only` | Writing under `/usr/bin` is refused. |
| `test_tmp_is_private` | A file written to `/tmp/…` inside is absent on the host. |
| `test_the_child_sees_the_allowlist_and_not_the_host` | A sentinel set in the test process's environment is absent inside; the allowlisted variable is present; `USER`, `SHELL`, `XDG_RUNTIME_DIR`, `SSH_AUTH_SOCK` absent; under bwrap `HOME` and `PATH` absent too (`--clearenv` means cleared). |
| `test_a_timeout_kills_the_whole_tree` | A grandchild with a unique marker in its cmdline is gone from the **host's** process table (`pgrep -f`) within seconds of the timeout; under the container, no `toolyard-*` container lingers. |
| `test_an_output_bomb_is_capped_and_the_tree_killed` | Stdout ≤ the cap with the truncation label; `timed_out` is False; exit non-zero (killed); returns in seconds; no lingering container. |
| `test_a_fork_attempt_is_bounded` | 128 attempted `sleep` children with `process_count=32`: spawns stop with `OSError` well short of the attempt count. |
| `test_a_file_size_limit_is_enforced` | A 2 MiB write under a 1 MiB limit: non-zero exit, and the file on the host is ≤ 1 MiB. |
| `test_a_memory_limit_is_enforced` | Touching 512 MiB under a 256 MiB limit: non-zero exit (MemoryError under `RLIMIT_AS`, OOM-kill under the cgroup). |
| `test_every_limit_is_reported_enforced_on_this_machine` | `limits_unenforced == ()` — a fact about *this* machine, asserted so a change is noticed. |
| `test_a_missing_command_is_a_result_not_an_exception` | A nonexistent binary is a non-zero exit with stderr, never a raise. |

**Launcher — `tests/unit/test_sandbox.py::TestTheLauncher`, real processes, no sandbox** (these run
anywhere Python runs, which is what keeps `sandbox.py` at 100 % on a CI runner with no rung): both
streams and the exit code captured; the child environment is exactly what was passed; the deadline
kills a sleeper; the deadline kills the **group**, grandchild included (polled to
`ProcessLookupError`); a child that ignores SIGTERM is SIGKILLed after the grace period (exit −9);
a child that closes its streams and keeps running is still killed; one that closes them and exits in
time is waited for; a stdout bomb and a stderr bomb are each capped at cap + 1 and killed; a missing
executable raises `FileNotFoundError` (the host's fault); killing a group that already exited, or
that vanishes between the grace period and the SIGKILL, is not an error; a process SIGKILL cannot
reap is not waited on forever.

**Mutation checks** — seven deliberate breaks, each applied to `sandbox.py`, run against
`test_sandbox.py` + `test_containment.py` + the integration suite, then restored (checksum verified):

| Mutation | Tests failing |
|---|---|
| bwrap loses `--unshare-all` | 7 |
| `env=None` becomes `os.environ` | 2 |
| container rung trusted without running its canary | 7 |
| workspace binds sorted deepest-first (nearest root loses) | 2 |
| a killed container's CLI is never followed by `rm -f` | 6 |
| the path half re-derived without resolution (`Path(candidate)`) | 26 |
| the launcher inherits the parent environment | 3 |

## 6. Decisions made where a document left an edge

1. **rlimits are applied by `prlimit` inside the sandbox, not by `resource.setrlimit` in a
   `preexec_fn`.** Spec §14 says "via `resource` where the platform supports it"; the intent is
   rlimits, and `prlimit` sets the same ones. Two reasons for the mechanism: `preexec_fn` is
   documented as unsafe in a threaded process and the consumer is a threaded server (ADR-0003); and
   `RLIMIT_NPROC` is checked against the user's task count at every level of the user-namespace
   hierarchy, so a fork-bomb-sized limit applied *before* `bwrap` creates its namespace makes that
   creation fail on a busy desktop — FreeWeight hit exactly this and worked around it by scanning
   `/proc`. Applied *inside* the namespace, after it exists, the same limit bounds the sandbox and
   nothing else (verified: `--nproc=64` inside bwrap runs; the fork test bites). Absence of
   `prlimit` is an observable condition: the rung still runs and every result names all four
   limits in `limits_unenforced`. Container rungs use cgroup limits for memory and pids (rlimit
   NPROC would hit the same host-count trap) and `--ulimit` for CPU time and file size.
2. **Cgroup limits under a container are reported unenforced when the runtime warns on the
   canary's stderr.** Docker discards `--memory`/`--pids-limit` it cannot apply with a `WARNING:`
   on stderr and exit 0. Any stderr on a successful canary marks `memory_bytes` and
   `process_count` unenforced — conservative in the safe direction, runtime-agnostic. Verified
   clean on this machine (`docker info`: MemoryLimit true, PidsLimit true).
3. **Both rungs bind the workspace in place, at the resolved host paths.** FreeWeight maps the
   workdir to `/work` in a container; here the same argv must mean the same thing on either rung,
   and the path a handler received from containment is already resolved, so the sandbox's world is
   the resolved one. Binds are ordered ancestors-first so the **nearest root wins** on both rungs
   (bwrap: later mount wins, verified; docker: sorts by destination itself). Consequence, noted for
   E2 in §8: this differs from `PathContainment`'s ancestry rule for the pathological case of a read
   root nested inside the write root.
4. **The bwrap rung binds six named `/etc` entries, never `/etc` whole.** Spec §14 says "nothing
   else from the host"; ADR-0018 says "the minimal runtime". `/etc` whole would carry the host's
   users, hostname and any world-readable configuration into a sandbox whose argv a model wrote. The
   six are what a dynamically linked binary needs through Debian's `alternatives` symlinks. The tuple
   is a module constant with a docstring saying that widening it is a security review item.
5. **The launcher gets `PATH` only.** FreeWeight's precedent, and spec §12's "ToolYard reads no
   environment". Consequence: a rootless Docker that is reachable only through `DOCKER_HOST` is not
   discoverable; the probe reports docker's canary failure and lands on bwrap, honestly. Recorded as
   a finding (§8) rather than solved with a constructor argument nobody has asked for.
6. **Unlaunchable argv is a result with exit 127**, never a raise (ADR-0053 decision 4): empty,
   not a sequence, a command string, a non-string item, a NUL or lone surrogate, a blank command,
   more than 1024 items, more than 128 KiB. 127 is the shell convention for "command not found" and
   the one code a caller can rely on meaning "this never ran". Everything else that reaches
   `run_isolated` — timeout, env, workspace — is the caller's and raises `ValidationError`, which a
   handler's frame turns into `handler_error` at the executor.
7. **A decided rung is never re-decided.** The probe runs once per `TieredSandbox`, under a lock,
   and is cached. A runtime that vanishes afterwards raises `ToolYardError` from `run_isolated`
   ("never a reason to run the command unisolated"); through `execute()` that is a `FAILED`
   result. `UNAVAILABLE` also raises from `run_isolated` — a caller bug, because the executor
   refuses such a tool at check #5 before a handler exists to call it, so arriving there means a
   handler reached for a subprocess without declaring `requires_isolation`. Tested through
   `execute()`: the result is `FAILED / handler_error` naming `ToolYardError`, and the launcher was
   never called.
8. **Non-Linux platforms are not probed** (spec §16): `platform` is injected, anything not starting
   with `linux` is `UNAVAILABLE` with a reason naming the platform, and the launcher is never
   called.
9. **The marker is `isolation`, not `live`, and the tests skip rather than being deselected.**
   `live` means "needs a provider/GPU"; these need a rung. They are not excluded by `addopts`, so
   the finish-line command runs them where a rung exists and skips them, visibly, where none does —
   a skip is not a pass. On this machine none skipped for lack of a rung.
10. **Podman is in the ladder, unverified here.** ADR-0018 names it preferred; the flag set is the
    same as docker's plus `--userns=keep-id` (rootless podman maps the caller's uid to a
    subordinate one otherwise, and the workspace would be unwritable). No podman on this machine:
    the argv is unit-tested, the rung is not exercised. Worst case is a failed canary or a failed
    run, both visible; never an unisolated one. Operator step in §10.
11. **`TieredSandbox` is the real class's name; the test double became `FixedTierSandbox`.**
    Spec §2 calls the concept "tiered subprocess isolation"; the double reports a fixed tier without
    probing, which is what its new name says. Three test files touched, mechanically.
12. **The post-kill wait is bounded.** A process SIGKILL cannot reap (uninterruptible sleep on a
    hung mount) would otherwise hang the tool call and the agent loop — a stop condition nobody
    controls. `_reap` waits 4 s and gives up; the result reports exit −1. Added after the first
    green gate, on review of the launcher.

## 7. What E2 and E4 must not relitigate

* **The ladder has no rung below refusal and no flag that adds one.** `TieredSandbox` has no
  argument that runs on the host, forces a rung above what the probe found, skips the canary, skips
  resolution, or widens a root. Do not add one "for tests" — the injected `which` and `runner` are
  the seams, and they only make the probe's view *smaller*.
* **The probe executes the real argv around `/bin/true`.** Do not replace it with `--version`, a
  `docker info`, or a `which`. Do not remove `--pull=never`.
* **`env=None` is the empty allowlist; the launcher gets `PATH` only.** `run_command` (E2) must
  pass an explicit allowlist and must never let a model choose it — the env is the *caller's*
  trusted input and raises when malformed, which would hand a model a `handler_error` lever.
* **`requires_isolation` is load-bearing** (spec §11.4). E2's `run_command` declares it. ToolYard
  cannot detect a handler that reaches for `run_isolated` without declaring it; what it can do is
  refuse to run unisolated, and it does (§6.7).
* **One `Popen`.** `tests/unit/test_boundaries.py` pins the package to exactly one process-launch
  site, in `sandbox.py`. E2's `run_command` calls `run_isolated`; it does not start a process.
* **The `/etc` tuple and the runtime binds** are the sandbox's allowlist of the host. Widening them
  is a security review, not a convenience.
* **The refusal order and check #5's internal order** are untouched by this row and stay so
  without an ADR.

## 8. Findings for E2 (built-ins) and E4 (PromptCadence integration)

1. **Resolved in §13 — spec §7 now reads `run_command_tool(sandbox: Sandbox)`.** The finding as
   found: `run_command` must hold the same `TieredSandbox` instance the executor holds. Spec §7's
   `run_command_tool()` takes no arguments; a handler cannot reach the executor's sandbox through
   `ToolContext`. If the handler constructs its own, the executor's tier check and the handler's
   run could disagree. Recommend `run_command_tool(sandbox: TieredSandbox)`, registered with the
   sandbox the executor was built with — a small spec §7 amendment for E2 to propose.
2. **Give the command a `PATH`.** Under bwrap `--clearenv` leaves no `PATH`; bare commands still
   resolve through libc's default (`/bin:/usr/bin`, verified), but anything the command spawns via
   `sys.executable`-style self-lookup sees an empty value. E2 should pass an explicit
   `{"PATH": "/usr/local/bin:/usr/bin:/bin"}` allowlist (the integration suite does this for its
   process-tree test). Never `os.environ`.
3. **Resolved in §13 — `SubprocessResult.output_truncated` added (default `False`).** The finding
   as found: `SubprocessResult` cannot say "output truncated". The Phase-1 shape has `timed_out` but no
   `output_truncated`; an output bomb shows as a labelled stdout (the standard
   `…[truncated by toolyard: kept of total bytes]` label, where `total` is what was received
   before the kill) plus a signal exit code. E2's `run_command` should render both. If E2 wants the
   flag explicit, that is a spec §7 amendment to `SubprocessResult`, not a local field.
4. **A backgrounded child keeps the call alive.** A command that spawns a daemon holding the
   pipes and exits will hold `run_isolated` open until the deadline, then the whole tree is killed
   and the result says `timed_out`. Conservative and correct for an agent tool; worth a sentence in
   `run_command`'s description so a model does not try to "start a server".
5. **Resolved in §13 — `SandboxPaths` now refuses relative and overlapping roots at
   construction.** The finding as found: overlapping roots. `SandboxPaths` accepts a read root nested inside the write root; the
   subprocess half makes it read-only (nearest root wins), the path half's ancestry rule makes it
   writable through `resolve_write`. A misconfiguration rather than an escape, but the two halves
   disagree about it. Recommend `SandboxPaths.__post_init__` refuse overlapping roots — a Phase-1
   vocabulary change, so an amendment to spec §7, not a quiet edit.
6. **Rootless Docker via `DOCKER_HOST` is not discoverable** (§6.5). If a deployment needs it, the
   honest shape is a constructor argument naming what the *launcher* may be handed, never
   `os.environ`. Nobody has asked; leave it until someone does.
7. **`process_count` under bwrap counts the whole user namespace**, including `bwrap`'s own init
   and `prlimit`; a limit of 1 or 2 would refuse everything. The default is 64; the integration
   suite uses 32. Document a sensible floor in E2 rather than validating one here.
8. **The image is a constructor argument, present-or-refused.** E4's PromptCadence configuration
   needs to name it and `doctor` needs to show `TierReport.reason`, which already says
   "No such image" when it is missing.
9. **The `env` values under a container pass through `--env K=V` unquoted**; a value containing a
   newline is accepted by `_checked_env` and by docker. Harmless, but E2 may want to refuse control
   characters in values if `run_command` ever exposes env to configuration.

## 9. Commits

```text
py/ToolYard
97a2316 feat(sandbox): tiered isolation — container → bwrap → refuse, probed with a canary
9fa789e test(containment): bind both implementations of the port to one containment contract
dae546b test(isolation): both rungs for real, the bwrap rung forced through the probe's view
b528ab9 docs: changelog and README for Phase 2
ffce452 feat(sandbox): the D1 review amendments — roots validated, output_truncated, network refused
03eca68 docs: mirror the amended spec; record the D1 review decisions

docs
a210674 docs(toolyard): D1 amendments to spec §7 and §14, decided with the operator
```

Files: `src/toolyard/sandbox.py` (new), `src/toolyard/__init__.py`, `pyproject.toml` (the
`isolation` marker), `tests/fakes.py` (rename + `ScriptedRunner`, `Launch`, `captured`, host views),
`tests/strategies.py` and `tests/unit/test_executor.py` (the rename), `tests/unit/test_boundaries.py`
(import allowlist + one-Popen guard), `tests/unit/test_containment.py` (parametrised over both
implementations), `tests/unit/test_sandbox.py` (new), `tests/integration/test_isolation.py` (new),
`CHANGELOG.md`, `README.md`. No `.importlinter` change. No document under `docs/` changed.

## 10. Before the next session — operator steps

1. **Review the diff same-day** (outstanding-work §4). Start with §12 below.
2. **Push `main`** from `py/ToolYard` **and from `docs`** (`git push origin main` in each; the
   VSCode askpass IPC env is needed for auth — see the FreeWeight memory note) and **confirm CI
   green**. Expect the isolation tests
   to *skip* on the runner (no `python:3.12-slim` pulled; `--pull=never` refuses; bwrap likely
   absent) — a skip, visible in the log, not a pass. Coverage stays at 100 % without them.
3. **Do not tag, do not publish.** This rides `toolyard 0.1.0` at row **E2**, after Phase 3.
4. **Podman is unverified.** On a machine with podman, run `pytest -m isolation -rs` and confirm the
   container case reports `runtime == "podman"` and passes; if `--userns=keep-id` is wrong for that
   podman version, the canary fails and the probe lands on the next rung — fix the flag, not the
   ladder.
5. **Re-run the marked suite on any machine where the ladder matters**, and read the skip reasons:
   `pytest -m isolation -rs`. Zero skips for lack of a rung is the bar on the reference machine.

## 11. Amended in `docs/`, after the interview

The build implemented into the spec as amended on 2026-09-03 (`9e70a9e`, `864dfbe`) without change.
After the interview (§13) the workspace `docs/packages/toolyard/spec.md` was amended in §7
(`SandboxPaths` validation comment; `network True ⇒ refused` on the `Sandbox` port;
`SubprocessResult.output_truncated`; `run_command_tool(sandbox: Sandbox)`) and §14 (the bwrap tier's
runtime binds named and the network refusal; resource limits as rlimits applied inside the sandbox,
never a `preexec_fn`). Committed in the docs repo as `a210674`, copied to
`py/ToolYard/docs/packages/toolyard/spec.md` and verified byte-identical with `cmp`. No other
document changed; no markdown was reflowed.

## 12. Where a reviewer should look first

The lines where a silent failure would live, in `src/toolyard/sandbox.py`:

* `_probe` — the ladder order, the canary through the real builders, `UNAVAILABLE` as the only
  fall-through.
* `_bwrap_argv` and `_container_argv` — every flag against ADR-0018's table; `--clearenv` /
  `--env`; `--pull=never`; the `--` separators; the `/etc` tuple.
* `_mounts` — resolved roots, the write root must be a directory, the sort.
* `run_isolated` — `UNAVAILABLE` raises before anything; `_argv_rejection` before `_mounts`;
  `_LAUNCHER_ENV` and nothing else handed to the launcher; `_remove_container` after a killed
  container run.
* `_launch` — `start_new_session=True`, `env=dict(env)`, the cap at `max_output_bytes + 1`, the
  kill on deadline or cap, `_reap`.

And in the tests: `test_isolation.py::_hide_containers` (the forcing), `TestTheLauncher`
(real processes), and the mutation table in §5.

## 13. Decisions taken with the operator, 2026-09-03 (interview after the build)

| # | Issue | Decision | Where it landed |
|---|---|---|---|
| A | How `run_command` gets the executor's sandbox | `run_command_tool(sandbox: Sandbox)` takes the same instance | spec §7 (`a210674`); E2 implements |
| B | Saying "output truncated" in the result | `SubprocessResult.output_truncated: bool = False` | spec §7; `containment.py`, `sandbox.py`, tests (`ffce452`) |
| C | Overlapping roots | `SandboxPaths.__post_init__` refuses equal/ancestor roots | spec §7; `containment.py` (`ffce452`) |
| D | Spec §14 says "via `resource`" | §14 amended: rlimits applied inside the sandbox by `prlimit`, never a `preexec_fn` | spec §14 (`a210674`) |
| E | When to make A–D | Now, this session, code and docs | `ffce452`, `03eca68`, `a210674` |
| F | What bwrap binds from `/etc` | The six named entries, as built | unchanged |
| G | `network=True` before any consumer | Refused as a caller bug; both builders lose their network branch; flag stays on the port | spec §7/§14; `sandbox.py`, tests (`ffce452`) |
| H | Rootless Docker via `DOCKER_HOST` | Leave: launcher gets `PATH` only | unchanged; changelog notes it |
| I | Isolation tests in CI | Run where a rung exists, skip visibly elsewhere; not excluded by `addopts` | unchanged |
| J | Podman, unverified here | Keep first in the ladder; verify on a podman host before E2 publishes | operator step §10.4 |
| K | Relative roots | Refused at construction alongside overlap | `containment.py` (`ffce452`) |
| L | Same-day review | Guided walkthrough, hunk by hunk, from §12 | completed, see §15 |

The mounts dedupe in `_mounts` now only fires for **resolved** overlap that construction cannot see
lexically — a symlinked alias of another root — and the bind-order tests prove nearest-root-wins
through aliases rather than through declared overlap.

## 14. Incident during the session, and what was restored

After the interview, one `ruff format .` was run with the shell's working directory at the
**workspace root** rather than inside `py/ToolYard` (the harness resets the working directory
between commands, and the command did not `cd` with an absolute path first). Ruff formats Python
code fences inside markdown, and with no `pyproject.toml` at the root it used its defaults. Result:
**15 markdown files in the docs repo were reformatted** (seven ADRs, `apps/ideapress/workflows.md`,
two architecture documents, five standards). Nothing else was touched: no `.py` outside ToolYard
changed (checked by mtime), the unversioned root files (`demo_*.py`, the handoffs, the prompts) kept
their earlier mtimes, and ToolYard's own markdown was already formatted under its own config. All 15
were restored with `git checkout --` in the docs repo; `docs/packages/toolyard/spec.md` was confirmed
byte-identical to the mirror made *before* the stray run, so the amendment survived untouched and the
15 did not include it. The gate reported in §1 was then run from inside `py/ToolYard` with an
absolute path. Guard going forward: every multi-step shell command in this workspace starts with
`cd /home/jpk/ai/suite/py/<component>`.

## 15. Review record, 2026-09-03

The same-day review required by outstanding-work §4 was done as a guided walkthrough with the
operator, one hunk at a time, each presented with what it guards, what would break it, and the tests
that pin it. All five were **approved as committed**, with no change requested:

| # | Hunk | Lines |
|---|---|---|
| 1 | The tier probe and the canary | `sandbox.py` 598–714 |
| 2 | The bwrap and container argv builders; the workspace binds | `sandbox.py` 740–893 |
| 3 | `run_isolated`: the floor first, caller inputs raise, the model's argv only produces a result | `sandbox.py` 458–597 |
| 4 | The launcher, the group kill, the bounded reap | `sandbox.py` 987–1105 |
| 5 | `SandboxPaths` validation; the argv and env checks | `containment.py` 120–152, `sandbox.py` 897–941 |

The reviewed state is ToolYard `03eca68` and docs `a210674`. Nothing in ToolYard was changed after
the review. One further docs commit followed: `roadmap/outstanding-work.md` now carries the open
§8 findings on the E2 and E4 rows and the push and podman steps in its §4 checklist, so they do
not depend on this file being read.
