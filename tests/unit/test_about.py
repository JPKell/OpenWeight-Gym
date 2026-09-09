"""The one test the empty package carries: its version is the one the skeleton declares."""

from __future__ import annotations

import weightroom


def test_version_is_the_unreleased_zero() -> None:
    """Row W0 ships no application code; ``0.0.0`` says so until W1 starts the count."""
    assert weightroom.__version__ == "0.0.0"
