"""Shared pytest fixtures: isolated XDG roots, a clean environment, a deterministic clock.

No test may read or write the developer's real config, data or state directories (testing
standards §9), so every test runs against a throwaway tree by default.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_xdg_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point every XDG directory at a throwaway tree and clear stray WEIGHTROOM_* variables."""
    for name in ("config", "data", "state"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith("WEIGHTROOM_"):
            monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def frozen_instant() -> datetime:
    """A fixed, timezone-aware UTC instant for deterministic timestamp assertions."""
    return datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC)
