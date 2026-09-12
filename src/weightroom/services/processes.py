"""weightroom.services.processes — the ``systemctl``/``loginctl`` boundary and ``units sync``.

[ADR-0125](../../../docs/adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
rule 3: control is ``systemctl --user`` by **explicit argv, never a shell**, with an allowlisted
environment, a timeout and an output cap — ToolYard's subprocess discipline, read rather than
imported (WeightRoomGym depends on no agent package, ADR-0123 rule 4).

The boundary is a port, :class:`SystemdController`, for two reasons that are not testing
convenience. A host without ``systemctl`` degrades the process pages to *unsupported on this
host* by name (rule 7), which is a decision the console renders rather than an exception it
leaks; and every call here reaches the operator's real session manager, so a suite that runs
"with no systemd" (spec §20 criterion 10) needs somewhere to stand. The real implementation
resolves its executables through an injected ``which`` and launches through an injected runner,
so a test can point it at a fixture ``systemctl`` on ``PATH`` and assert the argv it built.

**Never ``sudo``.** Nothing in this module — or anywhere in ``weightroom`` — invokes it; a grep
test in ``tests/security`` asserts the absence (ADR-0125 rule 5, development plan Phase 2
criterion 4).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess  # noqa: S404 — explicit argv, an allowlisted environment, never a shell
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final, Literal, Protocol, runtime_checkable

from baseaicore import SuiteError

from weightroom.__about__ import __version__
from weightroom.domain.units import UNIT_APPLICATIONS, render_unit, unit_diff, unit_name

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from weightroom.config import Settings

__all__ = [
    "ENV_ALLOWLIST",
    "OUTPUT_CAP_BYTES",
    "SETTLED_STATE_BY_VERB",
    "SHOW_PROPERTIES",
    "TIMEOUT_SECONDS",
    "UNIT_VERBS",
    "ActReport",
    "CommandResult",
    "FakeSystemdController",
    "Runner",
    "Scope",
    "SubprocessSystemdController",
    "SyncOutcome",
    "SyncReport",
    "SystemdController",
    "UnitActionFailed",
    "UnitPlan",
    "UnitState",
    "UnitStatus",
    "UnitUnsupported",
    "act_and_settle",
    "executable_for",
    "plan_units",
    "run_command",
    "sync_units",
    "units_directory",
]

logger = logging.getLogger(__name__)

ENV_ALLOWLIST: Final[tuple[str, ...]] = (
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    # `systemctl --user` and `loginctl` reach the session manager over the user bus; without
    # these two the call fails with "Failed to connect to bus" on a host where it would work.
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "SYSTEMD_COLORS",
)
"""Exactly what a child sees. Gold standard G12: no secret reaches a subprocess environment.

``LC_ALL=C`` is *set* rather than passed through, so ``systemctl``'s messages and timestamps are
the ones the parser and the tests were written against whatever the operator's locale is.
"""

OUTPUT_CAP_BYTES: Final = 1024 * 1024
"""Per-stream cap on captured output. ``systemctl show`` for five units is a few kilobytes."""

TIMEOUT_SECONDS: Final = 30.0
"""How long any one ``systemctl`` or ``loginctl`` call may take before it is killed.

A verb that outlives it has not necessarily failed — a slow ``stop`` goes on in systemd after the
client is gone — which is what :func:`act_and_settle` exists to find out (row WPF4).
"""

SHOW_PROPERTIES: Final[tuple[str, ...]] = (
    "Id",
    "LoadState",
    "ActiveState",
    "SubState",
    "Result",
    "MainPID",
    "NRestarts",
    "ActiveEnterTimestampMonotonic",
)
"""What one ``systemctl show`` asks for, for every unit at once."""

UNIT_VERBS: Final[frozenset[str]] = frozenset({"start", "stop", "restart", "enable", "disable"})
"""The verbs :meth:`SystemdController.act` accepts; anything else is a caller bug."""

type Scope = Literal["user", "system"]
type UnitState = Literal[
    "active", "activating", "deactivating", "inactive", "failed", "absent", "unsupported"
]
type Runner = Callable[[Sequence[str], Mapping[str, str], float], "CommandResult"]
"""``(argv, env, timeout_seconds) -> CommandResult``; the one process-launch boundary."""


class UnitUnsupported(SuiteError):
    """This host has no ``systemctl`` — the process pages say so by name (ADR-0125 rule 7)."""

    code: ClassVar[str] = "UNIT_UNSUPPORTED"


class UnitActionFailed(SuiteError):
    """``systemctl`` ran and refused; ``details['stderr']`` carries its own message."""

    code: ClassVar[str] = "UNIT_ACTION_FAILED"


@dataclass(frozen=True, slots=True)
class CommandResult:
    """One completed subprocess: what it exited with and what it said, both capped."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        """Whether the command exited zero and was not killed by the timeout."""
        return self.returncode == 0 and not self.timed_out

    @property
    def failure_text(self) -> str:
        """The message to show an operator: the command's own words, never a rewrite."""
        if self.timed_out:
            return f"{self.argv[0]} did not answer within {TIMEOUT_SECONDS:.0f}s"
        return (self.stderr.strip() or self.stdout.strip()) or f"exited {self.returncode}"


def run_command(
    argv: Sequence[str], env: Mapping[str, str], timeout_seconds: float = TIMEOUT_SECONDS
) -> CommandResult:
    """Launch ``argv`` with exactly ``env``, capped and timed out. The one launch site here.

    Args:
        argv: The complete argument vector, executable first, already resolved to a path.
        env: The child's whole environment — an allowlist the caller built, never ``os.environ``.
        timeout_seconds: How long the child may take before it is killed.

    Returns:
        The result, with each stream truncated to :data:`OUTPUT_CAP_BYTES` and ``timed_out``
        set rather than an exception raised: a slow ``systemctl`` is an operational fact the
        page reports, not a stack trace.
    """
    try:
        completed = subprocess.run(  # noqa: S603 — argv list, never a shell; env is an allowlist
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=dict(env),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(tuple(argv), returncode=-1, stdout="", stderr="", timed_out=True)
    except OSError as exc:
        return CommandResult(tuple(argv), returncode=-1, stdout="", stderr=str(exc))
    return CommandResult(
        tuple(argv),
        returncode=completed.returncode,
        stdout=(completed.stdout or "")[:OUTPUT_CAP_BYTES],
        stderr=(completed.stderr or "")[:OUTPUT_CAP_BYTES],
    )


def child_environment() -> dict[str, str]:
    """The allowlisted environment every child of this module gets."""
    env = {key: os.environ[key] for key in ENV_ALLOWLIST if key in os.environ}
    env["LC_ALL"] = "C"
    # A suite CLI's JSON lines reach a job's output only at exit when stdout is a pipe (block
    # buffered); unbuffered, a run id is visible while the run is going (W9 §5 item 5h).
    env["PYTHONUNBUFFERED"] = "1"
    return env


@dataclass(frozen=True, slots=True)
class UnitStatus:
    """One unit as ``systemctl show`` reports it.

    Attributes:
        unit: ``loadcoach.service``.
        state: The console's vocabulary (api.md §2). ``absent`` is a unit that was never
            written; ``unsupported`` is a host with no systemd.
        sub_state: systemd's own second word (``running``, ``dead``, ``exited``), for the tooltip.
        uptime_seconds: How long it has been active, or ``None`` when it is not — never ``0``
            (ADR-0016, spec §11 contract 9).
        main_pid: The main process, or ``None`` when there is none.
        restarts: ``NRestarts``, or ``None`` when the unit is absent.
        result: systemd's ``Result`` (``success``, ``exit-code``, ``oom-kill``, …) — the word
            that says *why* a unit is ``failed``.
    """

    unit: str
    state: UnitState
    sub_state: str = ""
    uptime_seconds: float | None = None
    main_pid: int | None = None
    restarts: int | None = None
    result: str = ""


@runtime_checkable
class SystemdController(Protocol):
    """The ``systemctl``/``loginctl`` boundary. Synchronous; the HTTP edge threads it (ADR-0003)."""

    def available(self) -> bool:
        """Whether this host has ``systemctl`` at all (ADR-0125 rule 7)."""
        ...

    def show(self, units: Sequence[str], *, scope: Scope = "user") -> dict[str, UnitStatus]:
        """One ``systemctl show`` for every unit named, keyed by unit name."""
        ...

    def properties(self, unit: str, names: Sequence[str], *, scope: Scope) -> dict[str, str]:
        """Raw ``Key=Value`` properties of one unit — what the Ollama pane reads (rule 4)."""
        ...

    def act(self, unit: str, verb: str, *, scope: Scope = "user") -> CommandResult:
        """Run one of :data:`UNIT_VERBS` against ``unit``; the result carries systemd's words."""
        ...

    def daemon_reload(self, *, scope: Scope = "user") -> CommandResult:
        """``systemctl --user daemon-reload`` after a unit file changed."""
        ...

    def linger_enabled(self, user: str) -> bool | None:
        """Whether ``user`` lingers; ``None`` when ``loginctl`` could not say (rule 2)."""
        ...

    def enable_linger(self, user: str) -> CommandResult:
        """``loginctl enable-linger <user>`` — the wizard's step, polkit-authenticated."""
        ...


def _parse_show(stdout: str) -> dict[str, dict[str, str]]:
    """Split ``systemctl show``'s blank-line-separated records into ``{Id: {key: value}}``."""
    records: dict[str, dict[str, str]] = {}
    for block in stdout.split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                fields[key] = value
        identifier = fields.get("Id")
        if identifier:
            records[identifier] = fields
    return records


_STATE_WORDS: Final[frozenset[str]] = frozenset(
    {"active", "activating", "deactivating", "inactive", "failed"}
)


def status_from_properties(
    unit: str, fields: Mapping[str, str], *, now_monotonic: float
) -> UnitStatus:
    """Turn one ``systemctl show`` record into a :class:`UnitStatus`.

    Args:
        unit: The unit the record was asked for.
        fields: Its ``Key=Value`` pairs.
        now_monotonic: ``time.clock_gettime(CLOCK_MONOTONIC)`` in seconds — the same clock
            systemd's ``…TimestampMonotonic`` is measured against, so uptime needs no date
            parsing and no locale.

    Returns:
        The status. ``LoadState=not-found`` is ``absent``, not ``inactive``: a unit that was
        never written and a unit that is stopped are different facts to an operator.
    """
    if fields.get("LoadState") in {"not-found", "masked", ""}:
        return UnitStatus(unit=unit, state="absent", sub_state=fields.get("SubState", ""))
    raw_state = fields.get("ActiveState", "")
    state: UnitState = raw_state if raw_state in _STATE_WORDS else "inactive"  # type: ignore[assignment]
    entered_us = fields.get("ActiveEnterTimestampMonotonic", "0")
    uptime: float | None = None
    if state == "active" and entered_us.isdigit() and int(entered_us) > 0:
        uptime = max(now_monotonic - int(entered_us) / 1_000_000, 0.0)
    pid_text = fields.get("MainPID", "0")
    restarts_text = fields.get("NRestarts", "")
    return UnitStatus(
        unit=unit,
        state=state,
        sub_state=fields.get("SubState", ""),
        uptime_seconds=uptime,
        main_pid=int(pid_text) if pid_text.isdigit() and int(pid_text) > 0 else None,
        restarts=int(restarts_text) if restarts_text.isdigit() else None,
        result=fields.get("Result", ""),
    )


SETTLED_STATE_BY_VERB: Final[dict[str, UnitState]] = {
    "start": "active",
    "restart": "active",
    "stop": "inactive",
}
"""The state each control verb asks the unit for, which is how a slow call is judged."""

TRANSITIONAL_STATES: Final[frozenset[str]] = frozenset({"activating", "deactivating"})
"""systemd is still working on it: neither the answer the verb asked for, nor a failure."""


@dataclass(frozen=True, slots=True)
class ActReport:
    """One verb's result, reconciled with the unit's state when ``systemctl`` outlived its limit.

    A ``systemctl stop`` that takes longer than :data:`TIMEOUT_SECONDS` has not failed — systemd
    goes on stopping the unit after the client that asked is gone, and at row WP6 a restart the
    console audited as ``failed`` had in fact succeeded ninety seconds later. So when the call is
    killed, the console reads the unit again and answers for what it actually reached rather than
    guessing from the timeout (`WP6_HANDOFF.md` finding 6, row WPF4).

    Attributes:
        result: What the call itself did.
        verb: The verb that was run, which is what the unit's state is judged against.
        settled: The unit as it was re-read after a timeout, or ``None`` when ``systemctl``
            answered in time and there was nothing to reconcile.
    """

    result: CommandResult
    verb: str
    settled: UnitStatus | None = None

    @property
    def outcome(self) -> str:
        """The audit outcome: ``ok``, ``failed``, or ``pending`` while systemd is still working.

        A ``pending`` row is the trail's own word for "this was asked, and the answer was not in
        yet"; the unit's live state is on every page of the application's tab.
        """
        if self.result.ok:
            return "ok"
        if self.settled is None:
            return "failed"
        if self.settled.state in TRANSITIONAL_STATES:
            return "pending"
        return "ok" if self.reached else "failed"

    @property
    def reached(self) -> bool:
        """Whether the unit is in the state the verb asked it for."""
        wanted = SETTLED_STATE_BY_VERB.get(self.verb)
        return self.settled is not None and self.settled.state == wanted

    @property
    def note(self) -> str | None:
        """What the audit row and the operator are told, or ``None`` when all went normally."""
        if self.result.ok:
            return None
        if self.settled is None:
            return self.result.failure_text
        return (
            f"{self.result.failure_text}; {self.settled.unit} is "
            f"{self.settled.state}{f' ({self.settled.result})' if self.settled.result else ''}"
        )


def act_and_settle(
    controller: SystemdController, unit: str, verb: str, *, scope: Scope = "user"
) -> ActReport:
    """Run ``verb`` against ``unit``, and on a timeout answer for the state the unit reached.

    The call stays blocking: ``systemctl`` normally answers in well under a second and its own
    words are the best refusal there is. Only a call that is killed at :data:`TIMEOUT_SECONDS`
    costs one extra ``systemctl show``, because that is the one case where the result says nothing
    about what happened (row WPF4; ADR-0125 rule 3 keeps the argv explicit either way).

    Args:
        controller: The systemd boundary.
        unit: The unit to drive.
        verb: One of :data:`UNIT_VERBS`.
        scope: ``user`` or ``system``.

    Returns:
        The :class:`ActReport`. A verb outside :data:`SETTLED_STATE_BY_VERB` — ``enable``,
        ``disable`` — has no state to check, so a timeout stays a failure.

    Raises:
        UnitUnsupported: This host has no ``systemctl``.
        ValueError: ``verb`` is outside :data:`UNIT_VERBS`.
    """
    result = controller.act(unit, verb, scope=scope)
    if not result.timed_out or verb not in SETTLED_STATE_BY_VERB:
        return ActReport(result, verb)
    try:
        settled = controller.show([unit], scope=scope).get(unit)
    except UnitActionFailed:
        # The re-read failed too. Nothing is known about the verb, which is what the bare result
        # already says; a second failure is not more information.
        return ActReport(result, verb)
    logger.info(
        "systemd.settled",
        extra={"unit": unit, "verb": verb, "state": None if settled is None else settled.state},
    )
    return ActReport(result, verb, settled=settled)


class SubprocessSystemdController:
    """:class:`SystemdController` over the real ``systemctl`` and ``loginctl``.

    Args:
        which: Executable lookup, injected so a test can point at a fixture on ``PATH`` — or
            withhold ``systemctl`` entirely and exercise the *unsupported on this host* path
            without touching the host (ToolYard's ``SandboxRunner`` precedent).
        runner: The process-launch boundary, injected for the same reason.
        monotonic: The clock uptime is measured against; ``CLOCK_MONOTONIC``, which is what
            systemd's ``…TimestampMonotonic`` properties are measured against too.
        environment: How the child's environment is built.
    """

    __slots__ = ("_environment", "_monotonic", "_runner", "_which")

    def __init__(
        self,
        *,
        which: Callable[[str], str | None] = shutil.which,
        runner: Runner = run_command,
        monotonic: Callable[[], float] = lambda: time.clock_gettime(time.CLOCK_MONOTONIC),
        environment: Callable[[], dict[str, str]] = child_environment,
    ) -> None:
        """Build a controller over this host, with every boundary injectable."""
        self._which = which
        self._runner = runner
        self._monotonic = monotonic
        self._environment = environment

    def _systemctl(self) -> str:
        found = self._which("systemctl")
        if found is None:
            raise UnitUnsupported(
                "This host has no systemctl; process control, units and the Ollama pane are "
                "unsupported here. Every other page works (ADR-0125 rule 7).",
                details={"binary": "systemctl"},
            )
        return found

    def available(self) -> bool:
        """Whether ``systemctl`` is on ``PATH``."""
        return self._which("systemctl") is not None

    def _run(self, argv: Sequence[str]) -> CommandResult:
        result = self._runner(argv, self._environment(), TIMEOUT_SECONDS)
        logger.debug(
            "systemd.command",
            extra={"argv": list(result.argv), "returncode": result.returncode},
        )
        return result

    def _scoped(self, scope: Scope, *rest: str) -> list[str]:
        argv = [self._systemctl()]
        if scope == "user":
            argv.append("--user")
        argv.extend(rest)
        return argv

    def show(self, units: Sequence[str], *, scope: Scope = "user") -> dict[str, UnitStatus]:
        """One call for every unit; a unit systemd does not know comes back ``absent``."""
        if not units:
            return {}
        argv = self._scoped(
            scope, "show", *units, "--no-pager", *(f"--property={name}" for name in SHOW_PROPERTIES)
        )
        result = self._run(argv)
        if not result.ok:
            raise UnitActionFailed(
                f"systemctl show failed: {result.failure_text}",
                details={"stderr": result.stderr.strip(), "argv": list(argv)},
            )
        records = _parse_show(result.stdout)
        now = self._monotonic()
        return {
            unit: status_from_properties(unit, records.get(unit, {}), now_monotonic=now)
            for unit in units
        }

    def properties(self, unit: str, names: Sequence[str], *, scope: Scope) -> dict[str, str]:
        """The raw properties of one unit, in systemd's own words."""
        argv = self._scoped(
            scope, "show", unit, "--no-pager", *(f"--property={name}" for name in names)
        )
        result = self._run(argv)
        if not result.ok:
            raise UnitActionFailed(
                f"systemctl show {unit} failed: {result.failure_text}",
                details={"unit": unit, "stderr": result.stderr.strip()},
            )
        fields: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                fields[key] = value
        return fields

    def act(self, unit: str, verb: str, *, scope: Scope = "user") -> CommandResult:
        """``systemctl [--user] --no-ask-password <verb> <unit>``.

        ``--no-ask-password`` is not optional. Without it, a ``systemctl restart`` of a **system**
        unit that the caller is not authorised for blocks on the desktop's interactive polkit
        agent — measured at row W2 on the reference machine, where the call hung until it was
        killed. A console request must fail in milliseconds with the refusal text, not hold an
        HTTP worker open waiting for a password prompt nobody is looking at.

        Raises:
            ValueError: ``verb`` is outside :data:`UNIT_VERBS`.
        """
        if verb not in UNIT_VERBS:
            message = f"{verb!r} is not a unit verb; the set is {sorted(UNIT_VERBS)}"
            raise ValueError(message)
        return self._run(self._scoped(scope, "--no-ask-password", verb, unit))

    def daemon_reload(self, *, scope: Scope = "user") -> CommandResult:
        """Re-read the unit files after ``sync`` wrote one."""
        return self._run(self._scoped(scope, "daemon-reload"))

    def linger_enabled(self, user: str) -> bool | None:
        """``loginctl show-user <user> --property=Linger``; ``None`` when it could not say."""
        loginctl = self._which("loginctl")
        if loginctl is None:
            return None
        result = self._run([loginctl, "show-user", user, "--property=Linger", "--value"])
        if not result.ok:
            return None
        answer = result.stdout.strip().lower()
        return answer == "yes" if answer in {"yes", "no"} else None

    def enable_linger(self, user: str) -> CommandResult:
        """``loginctl enable-linger <user>``, without an interactive prompt."""
        loginctl = self._which("loginctl")
        if loginctl is None:
            raise UnitUnsupported(
                "This host has no loginctl; lingering cannot be enabled from here.",
                details={"binary": "loginctl"},
            )
        return self._run([loginctl, "--no-ask-password", "enable-linger", user])


class FakeSystemdController:
    """An in-memory :class:`SystemdController` for route and page tests.

    Not a simulation of systemd: it holds a state per unit, records every call, and answers what
    the caller set up. Tests that assert the *argv* use :class:`SubprocessSystemdController`
    against a fixture ``systemctl`` on ``PATH`` instead — that is the half a fake cannot prove.
    """

    def __init__(
        self,
        *,
        states: Mapping[str, UnitState] | None = None,
        supported: bool = True,
        linger: bool | None = True,
        properties: Mapping[str, Mapping[str, str]] | None = None,
        refuse: Mapping[tuple[str, str], str] | None = None,
        slow: Mapping[tuple[str, str], UnitState] | None = None,
    ) -> None:
        """Build a fake host.

        Args:
            states: The unit states this host starts with; anything unnamed is ``absent``.
            supported: ``False`` makes every call raise :class:`UnitUnsupported`.
            linger: What :meth:`linger_enabled` answers.
            properties: Raw properties per unit, for :meth:`properties`.
            refuse: ``{(unit, verb): stderr}`` — verbs this host refuses, with systemd's message.
            slow: ``{(unit, verb): state}`` — verbs whose ``systemctl`` call is killed at
                :data:`TIMEOUT_SECONDS`, and the state the unit is left in afterwards: the row WP6
                restart that went on to succeed, or a unit still ``deactivating``.
        """
        self.states: dict[str, UnitState] = dict(states or {})
        self.supported = supported
        self.linger = linger
        self._properties = {unit: dict(values) for unit, values in (properties or {}).items()}
        self.refuse = dict(refuse or {})
        self.slow = dict(slow or {})
        self.calls: list[tuple[str, ...]] = []
        self.reloads = 0

    def _guard(self) -> None:
        if not self.supported:
            raise UnitUnsupported(
                "This host has no systemctl; process control is unsupported here.",
                details={"binary": "systemctl"},
            )

    def available(self) -> bool:
        """Whether this fake host has systemd."""
        return self.supported

    def show(self, units: Sequence[str], *, scope: Scope = "user") -> dict[str, UnitStatus]:
        """The states this fake was built with."""
        self._guard()
        self.calls.append(("show", scope, *units))
        return {
            unit: UnitStatus(
                unit=unit,
                state=self.states.get(unit, "absent"),
                sub_state="running" if self.states.get(unit) == "active" else "dead",
                uptime_seconds=61.0 if self.states.get(unit) == "active" else None,
                main_pid=4242 if self.states.get(unit) == "active" else None,
                restarts=0 if unit in self.states else None,
                result="timeout" if self.states.get(unit) == "failed" else "",
            )
            for unit in units
        }

    def properties(self, unit: str, names: Sequence[str], *, scope: Scope) -> dict[str, str]:
        """The raw properties this fake was built with, filtered to ``names``."""
        self._guard()
        self.calls.append(("properties", scope, unit))
        held = self._properties.get(unit, {})
        return {name: held[name] for name in names if name in held}

    def act(self, unit: str, verb: str, *, scope: Scope = "user") -> CommandResult:
        """Apply ``verb`` to this host's state, or answer with the refusal it was given."""
        self._guard()
        if verb not in UNIT_VERBS:
            message = f"{verb!r} is not a unit verb; the set is {sorted(UNIT_VERBS)}"
            raise ValueError(message)
        self.calls.append(("act", scope, unit, verb))
        refusal = self.refuse.get((unit, verb))
        if refusal is not None:
            return CommandResult(("systemctl", verb, unit), returncode=1, stdout="", stderr=refusal)
        eventual = self.slow.get((unit, verb))
        if eventual is not None:
            self.states[unit] = eventual
            return CommandResult(
                ("systemctl", verb, unit), returncode=-1, stdout="", stderr="", timed_out=True
            )
        if verb in {"start", "restart"}:
            self.states[unit] = "active"
        elif verb == "stop":
            self.states[unit] = "inactive"
        return CommandResult(("systemctl", verb, unit), returncode=0, stdout="", stderr="")

    def daemon_reload(self, *, scope: Scope = "user") -> CommandResult:
        """Count the reload."""
        self._guard()
        self.reloads += 1
        self.calls.append(("daemon-reload", scope))
        return CommandResult(("systemctl", "daemon-reload"), returncode=0, stdout="", stderr="")

    def linger_enabled(self, user: str) -> bool | None:
        """What this fake was told to answer."""
        return self.linger

    def enable_linger(self, user: str) -> CommandResult:
        """Turn lingering on."""
        self.calls.append(("enable-linger", user))
        self.linger = True
        return CommandResult(
            ("loginctl", "enable-linger", user), returncode=0, stdout="", stderr=""
        )


def units_directory() -> Path:
    """``$XDG_CONFIG_HOME/systemd/user``, where a ``systemd --user`` unit lives."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "systemd" / "user"


def executable_for(
    settings: Settings, app: str, *, which: Callable[[str], str | None] = shutil.which
) -> str | None:
    """The CLI a unit's ``ExecStart=`` names, or ``None`` when the application is not installed.

    ``[apps.<app>] executable`` when the operator set one (the reference machine keeps each
    application in its own virtualenv, so nothing is on ``PATH``), else ``which(<app>)``.
    ``weightroom`` is the console's own distribution, ``wr-gym``: ``which`` first, and failing
    that the command this process was started as, which is the interpreter that owns it.

    Args:
        settings: The validated settings.
        app: One of the five in :data:`~weightroom.domain.units.UNIT_APPLICATIONS`.
        which: Executable lookup, injected.

    Returns:
        An absolute path, or ``None``.
    """
    if app == "weightroom":
        found = which("wr-gym")
        if found:
            return str(Path(found).resolve())
        argv0 = Path(sys.argv[0]) if sys.argv and sys.argv[0] else None
        if argv0 is not None and argv0.name == "wr-gym" and argv0.is_file():
            return str(argv0.resolve())
        return None
    configured = getattr(settings.apps, app).executable
    if configured:
        return str(Path(configured).resolve()) if Path(configured).is_file() else None
    found = which(app)
    return str(Path(found).resolve()) if found else None


type SyncOutcome = Literal["written", "unchanged", "not_installed"]


@dataclass(frozen=True, slots=True)
class UnitPlan:
    """What ``units sync`` would do to one unit, decided before anything is written.

    Attributes:
        app: The application.
        unit: ``loadcoach.service``.
        path: Where the file goes.
        executable: The resolved CLI, or ``None`` when the application is not installed — which
            is *not installed*, never *stopped* (ADR-0125 rule 1).
        rendered: The file that would be written, or ``None`` when there is nothing to write.
        current: What is on disk now, or ``None``.
        diff: The unified diff, empty when the two agree.
    """

    app: str
    unit: str
    path: Path
    executable: str | None
    rendered: str | None
    current: str | None
    diff: tuple[str, ...]

    @property
    def outcome(self) -> SyncOutcome:
        """What a sync would report for this unit."""
        if self.rendered is None:
            return "not_installed"
        return "unchanged" if not self.diff else "written"


def plan_units(
    settings: Settings,
    *,
    version: str = __version__,
    which: Callable[[str], str | None] = shutil.which,
    directory: Path | None = None,
) -> tuple[UnitPlan, ...]:
    """Decide, without writing anything, what each of the five units should contain.

    Args:
        settings: The validated settings — ``[apps.*] executable`` and ``[host] memory_*``.
        version: The WeightRoomGym version the header names (spec §19).
        which: Executable lookup, injected.
        directory: Where units live; the XDG default when ``None``.

    Returns:
        One plan per application in :data:`~weightroom.domain.units.UNIT_APPLICATIONS` order.
    """
    root = directory if directory is not None else units_directory()
    plans: list[UnitPlan] = []
    for app in UNIT_APPLICATIONS:
        name = unit_name(app)
        path = root / name
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        executable = executable_for(settings, app, which=which)
        rendered = (
            None
            if executable is None
            else render_unit(
                app,
                executable=executable,
                version=version,
                memory_high=settings.host.memory_high,
                memory_max=settings.host.memory_max,
            )
        )
        diff = () if rendered is None else unit_diff(current, rendered)
        plans.append(
            UnitPlan(
                app=app,
                unit=name,
                path=path,
                executable=executable,
                rendered=rendered,
                current=current,
                diff=diff,
            )
        )
    return tuple(plans)


@dataclass(frozen=True, slots=True)
class SyncReport:
    """What ``units sync`` did: one outcome per unit, and whether systemd was reloaded."""

    plans: tuple[UnitPlan, ...]
    written: tuple[str, ...]
    reloaded: bool
    directory: Path

    def as_params(self) -> dict[str, object]:
        """The audit row's ``params``."""
        return {
            "directory": str(self.directory),
            "written": list(self.written),
            "outcomes": {plan.app: plan.outcome for plan in self.plans},
            "reloaded": self.reloaded,
        }


def sync_units(
    settings: Settings,
    *,
    controller: SystemdController,
    version: str = __version__,
    which: Callable[[str], str | None] = shutil.which,
    directory: Path | None = None,
    dry_run: bool = False,
) -> SyncReport:
    """Write every unit whose content differs, then reload systemd if anything changed.

    Idempotent by construction: the decision to write is a comparison against the rendered text,
    so a second run writes nothing and does not reload (spec §11 contract 8).

    Args:
        settings: The validated settings.
        controller: The systemd boundary.
        version: The version the header names.
        which: Executable lookup, injected.
        directory: Where units live; the XDG default when ``None``.
        dry_run: Plan and report, write nothing.

    Returns:
        The report.

    Raises:
        UnitUnsupported: This host has no ``systemctl`` (ADR-0125 rule 7).
        UnitActionFailed: ``daemon-reload`` failed after the files were written.
    """
    if not controller.available():
        raise UnitUnsupported(
            "This host has no systemctl; units cannot be written or driven here. Every other "
            "page works (ADR-0125 rule 7).",
            details={"binary": "systemctl"},
        )
    root = directory if directory is not None else units_directory()
    plans = plan_units(settings, version=version, which=which, directory=root)
    written: list[str] = []
    for plan in plans:
        if plan.outcome != "written" or plan.rendered is None:
            continue
        written.append(plan.unit)
        if dry_run:
            continue
        root.mkdir(parents=True, exist_ok=True)
        plan.path.write_text(plan.rendered, encoding="utf-8")
    reloaded = False
    if written and not dry_run:
        result = controller.daemon_reload()
        if not result.ok:
            raise UnitActionFailed(
                f"the units were written but systemd would not reload: {result.failure_text}",
                details={"stderr": result.stderr.strip(), "written": written},
            )
        reloaded = True
    logger.info("units.sync", extra={"written": written, "reloaded": reloaded})
    return SyncReport(plans=plans, written=tuple(written), reloaded=reloaded, directory=root)
