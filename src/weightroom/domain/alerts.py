"""weightroom.domain.alerts — what an alert is, and how one reading moves it (ADR-0137).

An alert is an **episode** of one source on one subject; at most one per ``(source, subject)`` is
active. :func:`decide` turns one reading of one source, and that source's active episodes, into
what to open, what was seen again and what to clear — as a pure function, so every rule below is a
unit test.

* **Condition sources** (``app_down``, ``gpu_thermal``, ``budget_ceiling``, ``breaker_open``) say
  whether something is wrong *now*: an episode clears when a reading that covers its subject finds
  it right again.
* **Event sources** (``memory_cap``) report something that *happened*; nothing later un-happens it,
  so an event episode never clears and closes only when acknowledged.
* **A reading that could not look covers nothing**, so it clears nothing (ADR-0016).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "ALERT_SOURCES",
    "EVENT_SOURCES",
    "EVERY_SUBJECT",
    "HISTORY_EVENTS",
    "SEVERITIES",
    "SOURCE_LABELS",
    "SOURCE_SEVERITY",
    "ActiveAlert",
    "Decision",
    "Firing",
    "Reading",
    "decide",
]

ALERT_SOURCES: Final[tuple[str, ...]] = (
    "app_down",
    "memory_cap",
    "gpu_thermal",
    "budget_ceiling",
    "breaker_open",
)
EVENT_SOURCES: Final[frozenset[str]] = frozenset({"memory_cap"})
SEVERITIES: Final[tuple[str, ...]] = ("warning", "critical")
SOURCE_SEVERITY: Final[Mapping[str, str]] = {
    "app_down": "critical",
    "memory_cap": "critical",
    "gpu_thermal": "warning",
    "budget_ceiling": "warning",
    "breaker_open": "warning",
}
SOURCE_LABELS: Final[Mapping[str, str]] = {
    "app_down": "application down",
    "memory_cap": "memory cap fired",
    "gpu_thermal": "GPU over its temperature threshold",
    "budget_ceiling": "budget ceiling reached",
    "breaker_open": "circuit breaker open",
}
"""What the banner calls each source: ``memory cap fired · ollama.service``."""

HISTORY_EVENTS: Final[tuple[str, ...]] = ("opened", "seen", "acknowledged", "cleared")

EVERY_SUBJECT: Final = "*"
"""A reading that covers every subject of its source — it looked at all of them."""


@dataclass(frozen=True, slots=True)
class Firing:
    """One subject a reading found wrong, and the evidence."""

    subject: str
    detail: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Reading:
    """One look at one source.

    Attributes:
        source: One of :data:`ALERT_SOURCES`.
        firing: The subjects found wrong.
        covers: The subjects this reading could judge — :data:`EVERY_SUBJECT`, a subject, or the
            part of a subject before its first ``:`` (``promptcadence`` covers
            ``promptcadence:per_day``). Empty when the source could not be read at all.
        problem: Why the source could not be read, or read only in part.
    """

    source: str
    firing: tuple[Firing, ...] = ()
    covers: frozenset[str] = frozenset()
    problem: str | None = None

    def covered(self, subject: str) -> bool:
        """Whether this reading judged ``subject``."""
        return (
            EVERY_SUBJECT in self.covers
            or subject in self.covers
            or subject.split(":", 1)[0] in self.covers
        )


@dataclass(frozen=True, slots=True)
class ActiveAlert:
    """An episode not yet closed."""

    id: str
    source: str
    subject: str


@dataclass(frozen=True, slots=True)
class Decision:
    """What one reading does: episodes to open, to mark seen, to clear."""

    opens: tuple[Firing, ...] = ()
    seen: tuple[tuple[str, Firing], ...] = ()
    clears: tuple[str, ...] = ()


def decide(reading: Reading, active: Sequence[ActiveAlert]) -> Decision:
    """Apply ADR-0137 to one reading.

    Args:
        reading: One source's reading.
        active: Active episodes; those of other sources are ignored.

    Returns:
        A subject firing with no active episode opens one; firing with one is seen on it (the last
        firing about a subject in the reading wins); an active episode of a condition source whose
        subject the reading covers and found right clears. An event source clears nothing.

    Raises:
        ValueError: The reading names a source this build does not have.
    """
    if reading.source not in ALERT_SOURCES:
        message = f"{reading.source!r} is not an alert source; they are {ALERT_SOURCES}"
        raise ValueError(message)
    mine = {alert.subject: alert for alert in active if alert.source == reading.source}
    latest: dict[str, Firing] = {}
    for firing in reading.firing:
        latest[firing.subject] = firing
    opens = tuple(firing for subject, firing in latest.items() if subject not in mine)
    seen = tuple(
        (mine[subject].id, firing) for subject, firing in latest.items() if subject in mine
    )
    if reading.source in EVENT_SOURCES:
        return Decision(opens=opens, seen=seen)
    clears = tuple(
        alert.id
        for subject, alert in mine.items()
        if subject not in latest and reading.covered(subject)
    )
    return Decision(opens=opens, seen=seen, clears=clears)
