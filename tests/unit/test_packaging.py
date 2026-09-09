"""Gold standard G16 / spec §5: the declared dependency set is the enumerated twelve names."""

from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

SUITE_PACKAGES = frozenset(
    {"baseaicore", "setspec", "modelrack", "sweatmeter", "weightsdb", "mirrorwall", "loadledger"}
)
FORBIDDEN_SUITE_PACKAGES = frozenset({"toolyard", "cutctx", "commissioner"})
APPROVED_NON_SUITE_DEPENDENCIES = frozenset(
    {
        "fastapi",
        "uvicorn",
        "typer",
        "pydantic",
        "sqlalchemy",
        "alembic",
        "jinja2",
        "httpx",
        "python-multipart",
        "tomlkit",
        "cryptography",
        "mistune",
    }
)


def _name(requirement: str) -> str:
    name = requirement.split(";", 1)[0].strip()
    for separator in ("[", ">", "<", "=", "!", "~", " "):
        index = name.find(separator)
        if index != -1:
            name = name[:index]
    return name.strip().lower()


def test_the_declared_dependencies_are_spec_5s_twelve_names() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    names = {_name(requirement) for requirement in data["project"]["dependencies"]}
    assert names & FORBIDDEN_SUITE_PACKAGES == set()
    assert names - SUITE_PACKAGES == APPROVED_NON_SUITE_DEPENDENCIES
    assert len(APPROVED_NON_SUITE_DEPENDENCIES) == 12
