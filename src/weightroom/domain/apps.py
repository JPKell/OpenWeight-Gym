"""weightroom.domain.apps — which application versions this console speaks to, and no I/O.

Spec §19: WeightRoomGym names, per application, the range of versions it speaks to, checked at
``GET /api/v1/version`` on first contact and re-checked every five minutes
([ADR-0013](../../../docs/adr/0013-api-versioning.md)). An application outside the range is
*degraded by name* — ``APP_VERSION_MISMATCH`` — never guessed at, because the alternative is a
console that renders a field the application stopped sending as a blank and calls it a value.

The range is a **major** range, not a pin. Every one of the four is post-1.0 and adds fields
within a minor by policy; a console that had to be re-released for each of four applications'
patch releases would be a console nobody upgrades.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

__all__ = [
    "RECHECK_SECONDS",
    "SUPPORTED_VERSIONS",
    "VersionRange",
    "VersionVerdict",
    "parse_version",
    "version_verdict",
]

RECHECK_SECONDS: Final = 300.0
"""Five minutes (spec §19, development plan Phase 2)."""

type VersionVerdict = Literal["ok", "too_old", "too_new", "unreadable"]

_VERSION = re.compile(r"^\s*v?(\d+)\.(\d+)(?:\.(\d+))?")


@dataclass(frozen=True, slots=True)
class VersionRange:
    """A half-open range of versions, ``minimum`` inclusive and ``below`` exclusive."""

    minimum: tuple[int, int]
    below: tuple[int, int]

    def __str__(self) -> str:
        """``>=1.0,<2.0`` — the words the mismatch message and the page both use."""
        return f">={self.minimum[0]}.{self.minimum[1]},<{self.below[0]}.{self.below[1]}"


SUPPORTED_VERSIONS: Final[dict[str, VersionRange]] = {
    "freeweight": VersionRange(minimum=(1, 0), below=(2, 0)),
    "loadcoach": VersionRange(minimum=(1, 0), below=(2, 0)),
    "ideapress": VersionRange(minimum=(1, 0), below=(2, 0)),
    "promptcadence": VersionRange(minimum=(1, 0), below=(2, 0)),
}
"""What WeightRoomGym 0.2 speaks to. A new major on either side is a new row in this table."""


def parse_version(version: str | None) -> tuple[int, int] | None:
    """The ``(major, minor)`` of a version string, or ``None`` when it is not one.

    Args:
        version: ``"1.3.1"``, ``"v1.3"``, ``"1.3.1.dev0"`` — or anything at all.

    Returns:
        The pair, or ``None``. A pre-release suffix is ignored: ``1.3.1rc1`` speaks the same API
        as ``1.3.1``, and refusing it would make an operator's release candidate unusable.
    """
    if not version:
        return None
    match = _VERSION.match(version)
    return (int(match.group(1)), int(match.group(2))) if match else None


def version_verdict(app: str, version: str | None) -> VersionVerdict:
    """Whether this console speaks to ``version`` of ``app``.

    Args:
        app: The application.
        version: What its ``GET /api/v1/version`` reported, or ``None`` when it did not answer.

    Returns:
        ``ok``; ``too_old`` or ``too_new`` for a version outside :data:`SUPPORTED_VERSIONS`;
        ``unreadable`` for an application with no range on file or a version that does not parse.
    """
    supported = SUPPORTED_VERSIONS.get(app)
    parsed = parse_version(version)
    if supported is None or parsed is None:
        return "unreadable"
    if parsed < supported.minimum:
        return "too_old"
    if parsed >= supported.below:
        return "too_new"
    return "ok"
