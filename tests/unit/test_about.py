"""The version the package declares is the one this row ships, and the CHANGELOG says so."""

from __future__ import annotations

from pathlib import Path

import weightroom

VERSION = "0.4.0"
"""Row W4 prepares ``0.4.0`` (unpublished)."""


def test_version_is_the_phase_4_release() -> None:
    assert weightroom.__version__ == VERSION


def test_the_changelog_has_an_entry_for_it() -> None:
    """Packaging standards §4: a user-visible change is a CHANGELOG entry, not just a bump."""
    changelog = (Path(__file__).resolve().parents[2] / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{VERSION}]" in changelog
