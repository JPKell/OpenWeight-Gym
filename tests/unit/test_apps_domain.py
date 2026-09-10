"""Version negotiation: the range this console speaks to, and what falls outside it (spec §19)."""

from __future__ import annotations

import pytest

from weightroom.config import APPLICATIONS
from weightroom.domain.apps import (
    RECHECK_SECONDS,
    SUPPORTED_VERSIONS,
    parse_version,
    version_verdict,
)


def test_every_application_has_a_declared_range() -> None:
    assert set(SUPPORTED_VERSIONS) == set(APPLICATIONS)


def test_the_recheck_window_is_five_minutes() -> None:
    assert RECHECK_SECONDS == 300.0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.3.1", (1, 3)),
        ("v1.3", (1, 3)),
        ("1.3.1rc1", (1, 3)),
        ("1.3.1.dev0", (1, 3)),
        ("10.0.0", (10, 0)),
        ("", None),
        (None, None),
        ("not a version", None),
    ],
)
def test_version_parsing(raw: str | None, expected: tuple[int, int] | None) -> None:
    assert parse_version(raw) == expected


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.0.0", "ok"),
        ("1.2.0", "ok"),
        ("1.3.1", "ok"),
        ("1.99.0", "ok"),
        ("0.9.9", "too_old"),
        ("2.0.0", "too_new"),
        ("2.1", "too_new"),
        (None, "unreadable"),
        ("banana", "unreadable"),
    ],
)
def test_the_verdict_is_a_major_range_not_a_pin(version: str | None, expected: str) -> None:
    assert version_verdict("loadcoach", version) == expected


def test_an_application_with_no_range_is_unreadable_rather_than_assumed_fine() -> None:
    assert version_verdict("weightroom", "0.2.0") == "unreadable"


def test_the_range_prints_as_the_words_the_page_shows() -> None:
    assert str(SUPPORTED_VERSIONS["loadcoach"]) == ">=1.0,<2.0"


def test_todays_suite_versions_are_all_inside_the_range() -> None:
    """The versions on the reference machine at row W2; a bump that leaves the range is a row."""
    for app, version in (
        ("freeweight", "1.2.0"),
        ("loadcoach", "1.3.1"),
        ("ideapress", "1.4.1"),
        ("promptcadence", "1.3.3"),
    ):
        assert version_verdict(app, version) == "ok", app
