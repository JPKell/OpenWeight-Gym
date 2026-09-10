"""weightroom.domain.ollama — ``MEMORY_SAFETY.md`` §2.1 as a checklist over unit properties.

Ollama is the one model server the suite does not own: it is a **system** unit that its own
installer wrote, WeightRoomGym runs as the operator and is never root, and so the whole of this
module is a *read* (ADR-0125 rule 4). What it decides is whether the daemon that hung the
machine on 2026-09-09 is configured so that it cannot do it again, line by line, in the words of
the document the operator would otherwise be checking by hand.

Pure: it takes the ``Key=Value`` pairs ``systemctl show ollama.service`` prints and returns
findings. No subprocess, no HTTP, no clock. The remedy is always the same and is always
*printed*, never run: ``docs/scripts/apply_memory_safety.sh``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

__all__ = [
    "APPLY_SCRIPT",
    "CHECK_PROPERTIES",
    "MAX_SAFE_CONTEXT_LENGTH",
    "OOMD_PRESSURE_LIMIT_PERCENT",
    "PRESCRIBED_CONTEXT_LENGTH",
    "Finding",
    "environment_of",
    "evaluate",
    "parse_bytes",
    "pressure_limit_percent",
]

APPLY_SCRIPT: Final = "docs/scripts/apply_memory_safety.sh"
"""The fix, printed rather than run (rule 4). WeightRoomGym is not root and does not pretend."""

PRESCRIBED_CONTEXT_LENGTH: Final = 8192
"""What ``MEMORY_SAFETY.md`` §2.1 sets the daemon default to."""

MAX_SAFE_CONTEXT_LENGTH: Final = 32768
"""The largest daemon default this check tolerates on the reference card.

§2.1 prescribes 8 192 and the check does not fail an operator who chose more, up to a point:
§4's table shows 32 k f16 is already tight for a 10 GB model on a 16 GB card, and the 112 000
that caused the reset is four times past that. Above this the finding fails and names both the
value found and the value §2.1 prescribes.
"""

OOMD_PRESSURE_LIMIT_PERCENT: Final = 50.0

CHECK_PROPERTIES: Final[tuple[str, ...]] = (
    "Id",
    "ActiveState",
    "SubState",
    "MemoryHigh",
    "MemoryMax",
    "MemorySwapMax",
    "ManagedOOMMemoryPressure",
    "ManagedOOMMemoryPressureLimit",
    "Environment",
    "FragmentPath",
    "DropInPaths",
)
"""What ``systemctl show ollama.service`` is asked for. Readable by any user (rule 4)."""

_INFINITY: Final = "infinity"
_UNSET_MAX: Final = 18446744073709551615
"""systemd's ``MemoryMax`` when nothing set it: ``UINT64_MAX``, not a cap."""

_SIZE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMGTP]?)i?B?\s*$", re.IGNORECASE)
_SUFFIXES: Final[dict[str, int]] = {
    "": 1,
    "K": 1024,
    "M": 1024**2,
    "G": 1024**3,
    "T": 1024**4,
    "P": 1024**5,
}

type Outcome = Literal["pass", "fail", "unknown"]


def parse_bytes(value: str | None) -> int | None:
    """Turn ``"22G"``, ``"23622320128"`` or ``"infinity"`` into a byte count.

    Args:
        value: A configured size, as either the operator writes it or systemd prints it.

    Returns:
        The bytes; ``None`` for ``infinity``, an unset ``UINT64_MAX``, an empty string or
        anything unparseable — all of which mean *no cap*, which is the finding, not an error.
        systemd's suffixes are binary (``G`` is 1024³), which is why ``22G`` and
        ``23622320128`` are the same number.
    """
    if value is None:
        return None
    text = value.strip()
    if not text or text.lower() == _INFINITY:
        return None
    match = _SIZE.match(text)
    if match is None:
        return None
    parsed = int(float(match.group(1)) * _SUFFIXES[match.group(2).upper()])
    return None if parsed >= _UNSET_MAX else parsed


def pressure_limit_percent(value: str | None) -> float | None:
    """``ManagedOOMMemoryPressureLimit`` as a percentage.

    systemd reports it as a fraction of ``UINT32_MAX`` rather than as the ``50%`` the operator
    wrote: ``2147483648`` is exactly half of ``2**32``. Measured on the reference machine at row
    W2 against an override that says ``50%``.

    Args:
        value: The property's value.

    Returns:
        The percentage, or ``None`` when it is absent or unparseable.
    """
    if not value or not value.strip().isdigit():
        return None
    return int(value.strip()) * 100.0 / 2**32


def environment_of(properties: dict[str, str]) -> dict[str, str]:
    """The unit's ``Environment=`` line, split into names and values.

    systemd prints every environment assignment on one space-separated line, quoting a value
    that contains a space. Splitting on whitespace is therefore right for everything Ollama
    sets — ``OLLAMA_HOST``, ``OLLAMA_CONTEXT_LENGTH``, ``OLLAMA_MAX_LOADED_MODELS`` — and a
    quoted value with a space in it would be mis-split. None of the checked names can contain
    one, and a value this module fails to read becomes an *unknown* finding rather than a wrong
    one.
    """
    found: dict[str, str] = {}
    for assignment in properties.get("Environment", "").split():
        name, separator, value = assignment.partition("=")
        if separator:
            found[name] = value.strip('"')
    return found


@dataclass(frozen=True, slots=True)
class Finding:
    """One line of the §2.1 checklist.

    Attributes:
        key: The setting, in the words of the document (``MemoryMax``).
        outcome: ``pass``, ``fail``, or ``unknown`` when the property could not be read at all.
        found: What the unit actually says, for the operator to compare.
        expected: What §2.1 asks for.
        why: The one-line consequence, from §2.1's own table.
    """

    key: str
    outcome: Outcome
    found: str
    expected: str
    why: str

    def as_json(self) -> dict[str, str]:
        """The api.md §5 shape."""
        return {
            "key": self.key,
            "outcome": self.outcome,
            "found": self.found,
            "expected": self.expected,
            "why": self.why,
        }


def _human(value: int | None) -> str:
    if value is None:
        return "no cap"
    for suffix, size in (("G", 1024**3), ("M", 1024**2), ("K", 1024)):
        if value >= size and value % size == 0:
            return f"{value // size}{suffix}"
    return str(value)


def evaluate(
    properties: dict[str, str], *, memory_high: str, memory_max: str
) -> tuple[Finding, ...]:
    """The §2.1 checklist against one unit's properties.

    Args:
        properties: What ``systemctl show ollama.service`` printed, already split.
        memory_high: WeightRoomGym's ``[host] memory_high`` — the figure the cap is compared to,
            so a 64 GB machine is judged against its own numbers rather than the document's
            30 GB example.
        memory_max: ``[host] memory_max``.

    Returns:
        Seven findings, in §2.1's order. A unit whose properties could not be read at all
        (``properties`` empty) is seven ``unknown`` findings, never seven failures: *not read*
        and *not configured* are different facts.
    """
    unknown = not properties
    environment = environment_of(properties)
    wanted_high = parse_bytes(memory_high)
    wanted_max = parse_bytes(memory_max)

    def outcome(passed: bool) -> Outcome:
        return "unknown" if unknown else ("pass" if passed else "fail")

    context_raw = environment.get("OLLAMA_CONTEXT_LENGTH")
    context = int(context_raw) if context_raw and context_raw.isdigit() else None
    loaded = environment.get("OLLAMA_MAX_LOADED_MODELS")
    high = parse_bytes(properties.get("MemoryHigh"))
    maximum = parse_bytes(properties.get("MemoryMax"))
    swap = parse_bytes(properties.get("MemorySwapMax"))
    swap_denied = properties.get("MemorySwapMax", "").strip() == "0"
    oomd = properties.get("ManagedOOMMemoryPressure", "").strip()
    limit = pressure_limit_percent(properties.get("ManagedOOMMemoryPressureLimit"))

    return (
        Finding(
            key="OLLAMA_CONTEXT_LENGTH",
            outcome=outcome(context is not None and context <= MAX_SAFE_CONTEXT_LENGTH),
            found="unset" if context is None else str(context),
            expected=str(PRESCRIBED_CONTEXT_LENGTH),
            why="The daemon's KV cache for every request that sets no num_ctx.",
        ),
        Finding(
            key="OLLAMA_MAX_LOADED_MODELS",
            outcome=outcome(loaded == "1"),
            found=loaded or "unset (Ollama's default is up to 3 per GPU)",
            expected="1",
            why="A second model loading beside the first, and the pair spilling.",
        ),
        Finding(
            key="MemoryHigh",
            outcome=outcome(high is not None and wanted_high is not None and high <= wanted_high),
            found=_human(high),
            expected=memory_high,
            why="The kernel throttles the daemon's allocations before the cap.",
        ),
        Finding(
            key="MemoryMax",
            outcome=outcome(
                maximum is not None and wanted_max is not None and maximum <= wanted_max
            ),
            found=_human(maximum),
            expected=memory_max,
            why="The kernel OOM-kills the daemon's runner; the desktop keeps its memory.",
        ),
        Finding(
            key="MemorySwapMax",
            # `MemorySwapMax=0` is a *cap of zero*, which is the point; it is not "unset".
            outcome=outcome(swap_denied),
            found="0" if swap_denied else _human(swap),
            expected="0",
            why="Hitting the cap becomes a kill in milliseconds, not minutes of thrash.",
        ),
        Finding(
            key="ManagedOOMMemoryPressure",
            outcome=outcome(oomd == "kill"),
            found=oomd or "unset",
            expected="kill",
            why="systemd-oomd kills the unit under sustained pressure, below the cap.",
        ),
        Finding(
            key="ManagedOOMMemoryPressureLimit",
            outcome=outcome(limit is not None and abs(limit - OOMD_PRESSURE_LIMIT_PERCENT) < 1.0),
            found="unset" if limit is None else f"{limit:.0f}%",
            expected=f"{OOMD_PRESSURE_LIMIT_PERCENT:.0f}%",
            why="Where that pressure kill fires.",
        ),
    )
