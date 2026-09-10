"""``MEMORY_SAFETY.md`` §2.1 as findings, over two fixtures of real ``systemctl show`` output.

`unsafe-112000-no-cap.txt` is the configuration §1 of that document names as the cause of the
2026-09-09 reset: a 112 000-token daemon default and no cgroup cap at all. `safe-applied.txt` is
the same unit after `docs/scripts/apply_memory_safety.sh` has run — captured from the reference
machine at row W2, where the operator had already applied it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from weightroom.domain.ollama import (
    APPLY_SCRIPT,
    MAX_SAFE_CONTEXT_LENGTH,
    PRESCRIBED_CONTEXT_LENGTH,
    environment_of,
    evaluate,
    parse_bytes,
    pressure_limit_percent,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ollama"


def _properties(name: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value
    return fields


def _findings(name: str) -> dict[str, str]:
    return {
        finding.key: finding.outcome
        for finding in evaluate(_properties(name), memory_high="22G", memory_max="24G")
    }


def test_the_reference_machines_pre_fix_unit_fails_every_line() -> None:
    outcomes = _findings("unsafe-112000-no-cap.txt")
    assert set(outcomes.values()) == {"fail"}
    assert len(outcomes) == 7


def test_the_context_length_that_caused_the_reset_is_named_in_the_finding() -> None:
    findings = {
        f.key: f
        for f in evaluate(
            _properties("unsafe-112000-no-cap.txt"), memory_high="22G", memory_max="24G"
        )
    }
    context = findings["OLLAMA_CONTEXT_LENGTH"]
    assert context.found == "112000"
    assert context.expected == str(PRESCRIBED_CONTEXT_LENGTH)
    assert findings["MemoryMax"].found == "no cap"
    assert findings["MemorySwapMax"].found == "no cap"


def test_the_unit_after_the_script_has_run_passes_every_line() -> None:
    assert set(_findings("safe-applied.txt").values()) == {"pass"}


def test_a_unit_that_could_not_be_read_is_unknown_not_failing() -> None:
    outcomes = {f.key: f.outcome for f in evaluate({}, memory_high="22G", memory_max="24G")}
    assert set(outcomes.values()) == {"unknown"}


def test_the_cap_is_compared_against_this_hosts_own_figures() -> None:
    """A 64 GB machine is judged against 56G/54G, not the document's 30 GB example."""
    properties = _properties("safe-applied.txt")
    generous = {f.key: f.outcome for f in evaluate(properties, memory_high="56G", memory_max="58G")}
    assert generous["MemoryHigh"] == "pass"  # 22G is under 56G
    strict = {f.key: f.outcome for f in evaluate(properties, memory_high="8G", memory_max="10G")}
    assert strict["MemoryHigh"] == "fail"  # 22G is over 8G


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("22G", 23622320128),
        ("23622320128", 23622320128),
        ("24G", 25769803776),
        ("0", 0),
        ("infinity", None),
        ("18446744073709551615", None),
        ("", None),
        ("nonsense", None),
        (None, None),
    ],
)
def test_systemd_sizes_are_binary_and_infinity_is_no_cap(
    raw: str | None, expected: int | None
) -> None:
    assert parse_bytes(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"), [("2147483648", 50.0), ("0", 0.0), ("4294967295", 100.0), ("", None)]
)
def test_the_pressure_limit_is_a_fraction_of_uint32(raw: str, expected: float | None) -> None:
    answer = pressure_limit_percent(raw)
    if expected is None:
        assert answer is None
    else:
        assert answer is not None
        assert abs(answer - expected) < 0.001


def test_the_environment_line_is_split_into_names_and_values() -> None:
    environment = environment_of(_properties("safe-applied.txt"))
    assert environment["OLLAMA_CONTEXT_LENGTH"] == "8192"
    assert environment["OLLAMA_MAX_LOADED_MODELS"] == "1"
    assert environment["OLLAMA_HOST"] == "0.0.0.0:11434"


def test_a_context_between_the_prescribed_value_and_the_ceiling_still_passes() -> None:
    properties = dict(_properties("safe-applied.txt"))
    properties["Environment"] = (
        f"OLLAMA_CONTEXT_LENGTH={MAX_SAFE_CONTEXT_LENGTH} OLLAMA_MAX_LOADED_MODELS=1"
    )
    outcomes = {f.key: f.outcome for f in evaluate(properties, memory_high="22G", memory_max="24G")}
    assert outcomes["OLLAMA_CONTEXT_LENGTH"] == "pass"
    properties["Environment"] = (
        f"OLLAMA_CONTEXT_LENGTH={MAX_SAFE_CONTEXT_LENGTH + 1} OLLAMA_MAX_LOADED_MODELS=1"
    )
    outcomes = {f.key: f.outcome for f in evaluate(properties, memory_high="22G", memory_max="24G")}
    assert outcomes["OLLAMA_CONTEXT_LENGTH"] == "fail"


def test_the_remedy_is_the_script_the_document_names() -> None:
    assert APPLY_SCRIPT == "docs/scripts/apply_memory_safety.sh"
