"""The version the package declares is the one this row ships."""

from __future__ import annotations

import weightroom


def test_version_is_the_phase_1_release() -> None:
    """Row W1 prepares ``0.1.0`` (unpublished)."""
    assert weightroom.__version__ == "0.1.0"
