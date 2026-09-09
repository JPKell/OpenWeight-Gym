"""``docs/configuration.md`` is generated from the settings model and cannot drift (config §8)."""

from __future__ import annotations

from pathlib import Path

from weightroom.config import leaf_keys, security_keys
from weightroom.services.config_reference import render_configuration_reference
from weightroom.services.settings import RUNTIME_SETTINGS

REFERENCE = Path(__file__).resolve().parents[2] / "docs" / "configuration.md"


def test_the_committed_reference_matches_the_model() -> None:
    assert REFERENCE.is_file(), "docs/configuration.md is missing; run `wr-gym config reference`"
    assert REFERENCE.read_text(encoding="utf-8") == render_configuration_reference(), (
        "docs/configuration.md drifted: `wr-gym config reference --output docs/configuration.md`"
    )


def test_every_leaf_appears_with_its_columns() -> None:
    rendered = render_configuration_reference()
    lines = rendered.splitlines()
    assert "## `[apps.loadcoach]`" in rendered
    for key in leaf_keys():
        line = next(line for line in lines if line.startswith(f"| `{key}` |"))
        assert f"`WEIGHTROOM_{key.upper().replace('.', '__')}`" in line
        assert ("| yes |" in line) == (key in RUNTIME_SETTINGS)
        assert ("security key" in line) == (key in security_keys())
