"""weightroom.domain.units — the ``systemd --user`` unit template, rendered and diffed, no I/O.

[ADR-0125](../../../docs/adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
rule 1: a unit is **generated whole** from one template and WeightRoomGym's configuration, so an
operator's hand edit is overwritten on the next ``wr-gym units sync`` and the console says so.
The template is data here — a list of sections and lines — rather than a format string, because
the one thing that varies between applications is *which lines exist* (the three ``Memory*``
lines go on ``freeweight`` and ``loadcoach`` alone, rule 6), and a conditional inside a format
string is how a generated file quietly grows a second shape.

Everything in this module is a pure function of its arguments. :mod:`weightroom.services.processes`
is where ``subprocess`` and the filesystem come in.
"""

from __future__ import annotations

import difflib
import re
from typing import Final

__all__ = [
    "MEMORY_CAPPED",
    "UNIT_APPLICATIONS",
    "UNIT_DESCRIPTIONS",
    "escape_exec_argument",
    "render_unit",
    "unit_diff",
    "unit_name",
]

UNIT_APPLICATIONS: Final[tuple[str, ...]] = (
    "freeweight",
    "loadcoach",
    "ideapress",
    "promptcadence",
    "weightroom",
)
"""The five units ``wr-gym units sync`` writes (ADR-0125 rules 1 and 6)."""

MEMORY_CAPPED: Final[frozenset[str]] = frozenset({"freeweight", "loadcoach"})
"""The two applications that launch a model server, and therefore carry the host memory cap.

``ideapress`` and ``promptcadence`` route every model call through LoadCoach and serve nothing
themselves; ``weightroom`` serves no model at all (ADR-0125 rule 6). A cap on those three would
bound a process that never allocates near it, and would have to be raised the first time one of
them read a large file — a limit that is never the binding one is a limit nobody maintains.
"""

UNIT_DESCRIPTIONS: Final[dict[str, str]] = {
    "freeweight": "FreeWeight",
    "loadcoach": "LoadCoach",
    "ideapress": "IdeaPress",
    "promptcadence": "PromptCadence",
    "weightroom": "WeightRoomGym",
}
"""The product name each unit's ``Description=`` carries; the unit name is the distribution's."""

_NEEDS_QUOTING: Final = re.compile(r'[\s"\'\\]')


def unit_name(app: str) -> str:
    """The unit file's name for ``app``.

    Args:
        app: One of :data:`UNIT_APPLICATIONS`.

    Returns:
        ``"loadcoach.service"``.

    Raises:
        ValueError: ``app`` is not one of the five.
    """
    if app not in UNIT_APPLICATIONS:
        message = f"{app!r} has no unit; the five are {', '.join(UNIT_APPLICATIONS)}"
        raise ValueError(message)
    return f"{app}.service"


def escape_exec_argument(value: str) -> str:
    """Quote one ``ExecStart=`` argument for systemd's parser when it needs it.

    systemd splits ``ExecStart=`` on whitespace unless an argument is double-quoted, and inside
    a double-quoted argument ``\\`` and ``"`` are escapes. A venv under a directory with a space
    in it is ordinary on a desktop, so the quoting is applied rather than assumed away.

    Args:
        value: One argument — an executable path or a verb.

    Returns:
        ``value`` unchanged when it needs no quoting, else the double-quoted, escaped form.
    """
    if not value:
        return '""'
    if not _NEEDS_QUOTING.search(value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_unit(
    app: str,
    *,
    executable: str,
    version: str,
    memory_high: str,
    memory_max: str,
) -> str:
    """Render ``app``'s complete unit file.

    Args:
        app: One of :data:`UNIT_APPLICATIONS`.
        executable: The absolute path to the application's CLI — the interpreter that owns the
            installed command, resolved by the caller (ADR-0125 rule 1).
        version: The WeightRoomGym version writing the file; it goes in the header comment so
            ``units sync`` can rewrite on a version change (spec §19).
        memory_high: ``[host] memory_high``, written only for :data:`MEMORY_CAPPED`.
        memory_max: ``[host] memory_max``, likewise.

    Returns:
        The file's whole text, ending in a newline. Byte-identical for identical arguments: the
        file is compared against this to decide whether ``sync`` writes.

    Raises:
        ValueError: ``app`` is not one of the five, or ``executable`` is empty.
    """
    name = unit_name(app)
    if not executable:
        message = f"{app}: an ExecStart needs an executable; the caller resolves it first"
        raise ValueError(message)
    description = UNIT_DESCRIPTIONS[app]
    lines = [
        f"# {name} — generated whole by WeightRoomGym {version} (ADR-0125 rule 1).",
        "# Edits here are overwritten by `wr-gym units sync`. To change this unit, change",
        "# WeightRoomGym's configuration: [apps.<app>] executable, [host] memory_high/memory_max.",
        "",
        "[Unit]",
    ]
    if app == "weightroom":
        lines.append(f"Description={description} (Local AI Suite; the operator console)")
    else:
        lines.append(
            f"Description={description} (Local AI Suite; loopback, fronted by WeightRoomGym)"
        )
    lines += [
        "After=network.target",
        "",
        "[Service]",
        f"ExecStart={escape_exec_argument(executable)} serve",
        "Restart=on-failure",
        "RestartSec=3",
    ]
    if app in MEMORY_CAPPED:
        lines += [
            "# ADR-0119: the model-serving applications run under the host-memory cap. These",
            "# replace MEMORY_SAFETY.md §2.2's systemd-run wrapper for a unit-managed application.",
            f"MemoryHigh={memory_high}",
            f"MemoryMax={memory_max}",
            "MemorySwapMax=0",
        ]
    lines += [
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ]
    return "\n".join(lines)


def unit_diff(current: str | None, rendered: str) -> tuple[str, ...]:
    """The unified diff from what is on disk to what would be written.

    Args:
        current: The file's text, or ``None`` when there is no file yet.
        rendered: :func:`render_unit`'s output.

    Returns:
        The diff's lines without trailing newlines, empty when the two agree. An absent file
        diffs against the empty string rather than being reported as a special case: the console
        shows the operator what will appear, which is the whole file.
    """
    if current == rendered:
        return ()
    return tuple(
        line.rstrip("\n")
        for line in difflib.unified_diff(
            (current or "").splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile="on disk" if current is not None else "absent",
            tofile="WeightRoomGym",
            n=2,
        )
    )
