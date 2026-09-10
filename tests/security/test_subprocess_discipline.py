"""ADR-0125 rules 3 and 5: explicit argv, an allowlisted environment, and never ``sudo``.

Development plan Phase 2 criterion 4 is a grep test, and it is written as one — but over the
*runtime* strings rather than the file's text. ``sudo`` is a word this console must be able to
**print**: the polkit rule of ADR-0125 rule 5 and the CA-trust steps of ADR-0126 are both
instructions the operator runs in their own shell, and a test that banned the four letters
outright would ban the sentence that tells them what to run. So the rule tested is the one that
matters: a string containing ``sudo`` may be shown to a person, and may never be an element of
an argument list.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "weightroom"
SOURCES = sorted(SOURCE_ROOT.rglob("*.py"))

# The two modules that print a command beginning with `sudo` for the operator to run by hand.
INSTRUCTION_MODULES = {"services/tls.py", "services/ollama.py"}


def _relative(path: Path) -> str:
    return path.relative_to(SOURCE_ROOT).as_posix()


def _docstrings(tree: ast.Module) -> set[int]:
    """The ``id()`` of every constant that is a docstring, so prose is not mistaken for code."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
    return found


def _runtime_strings(path: Path) -> list[str]:
    """Every string literal the module can hand to something, docstrings excluded."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = _docstrings(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip
    ]


def test_the_source_tree_is_not_empty() -> None:
    assert len(SOURCES) > 20, "the tests below would pass vacuously"


@pytest.mark.parametrize("path", SOURCES, ids=_relative)
def test_sudo_is_only_ever_text_shown_to_the_operator(path: Path) -> None:
    mentions = [value for value in _runtime_strings(path) if "sudo" in value]
    if _relative(path) not in INSTRUCTION_MODULES:
        assert not mentions, f"{_relative(path)} builds a string containing sudo"
        return
    for value in mentions:
        assert value.count(" ") >= 2 or "\n" in value, (
            f"{_relative(path)}: {value!r} is short enough to be an argv element, not a sentence"
        )


@pytest.mark.parametrize("path", SOURCES, ids=_relative)
def test_sudo_is_never_shaped_like_an_executable(path: Path) -> None:
    """No string anywhere is the bare word — the only shape that could be an ``argv[0]``.

    A tuple of instruction *sentences* (``tls.trust_steps``) is not an argument list, so the
    test looks at the shape of each string rather than at the brackets around it.
    """
    for value in _runtime_strings(path):
        assert value.strip() != "sudo", f"{_relative(path)}: a bare sudo string"


@pytest.mark.parametrize("path", SOURCES, ids=_relative)
def test_no_module_runs_a_shell(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for banned in ("shell=True", "os.system(", "os.popen(", "subprocess.getoutput"):
        assert banned not in text, f"{_relative(path)} uses {banned}"


@pytest.mark.parametrize("path", SOURCES, ids=_relative)
def test_every_subprocess_call_passes_a_list_and_an_environment(path: Path) -> None:
    """``subprocess.run``/``Popen`` take an argument list and an explicit ``env``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = ast.unparse(node.func)
        if target not in {"subprocess.run", "subprocess.Popen"}:
            continue
        keywords = {keyword.arg for keyword in node.keywords}
        assert "env" in keywords, f"{_relative(path)}: {target} without an explicit env"
        assert "shell" not in keywords, f"{_relative(path)}: {target} names shell="
        first = node.args[0] if node.args else None
        assert first is not None, f"{_relative(path)}: {target} with no argv"
        assert not isinstance(first, ast.JoinedStr | ast.Constant), (
            f"{_relative(path)}: {target} was handed a string, not an argument list"
        )


def test_the_environment_allowlist_holds_no_credential_shaped_name() -> None:
    from weightroom.services.processes import ENV_ALLOWLIST, child_environment

    pattern = re.compile(r"(?i)token|key|secret|password|auth|cookie")
    assert not [name for name in ENV_ALLOWLIST if pattern.search(name)]
    assert set(child_environment()) <= {*ENV_ALLOWLIST, "LC_ALL"}
