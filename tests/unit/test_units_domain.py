"""The unit template: goldens per application, the memory rule, the diff (ADR-0125 rules 1, 6)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from weightroom.domain.units import (
    MEMORY_CAPPED,
    UNIT_APPLICATIONS,
    escape_exec_argument,
    render_unit,
    unit_diff,
    unit_name,
)

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "units"
VERSION = "0.2.0"


def _render(app: str) -> str:
    return render_unit(
        app,
        executable=f"/home/op/ai/suite/venvs/{app}/bin/{'wr-gym' if app == 'weightroom' else app}",
        version=VERSION,
        memory_high="22G",
        memory_max="24G",
    )


@pytest.mark.parametrize("app", UNIT_APPLICATIONS)
def test_rendered_unit_matches_its_golden(app: str) -> None:
    golden = GOLDEN_DIR / f"{app}.service"
    rendered = _render(app)
    assert golden.is_file(), f"{golden} missing; write it with `golden.write_text(rendered)`"
    assert golden.read_text(encoding="utf-8") == rendered


@pytest.mark.parametrize("app", UNIT_APPLICATIONS)
def test_memory_lines_appear_only_on_the_two_model_serving_applications(app: str) -> None:
    rendered = _render(app)
    capped = app in MEMORY_CAPPED
    assert capped == (app in {"freeweight", "loadcoach"})
    for line in ("MemoryHigh=22G", "MemoryMax=24G", "MemorySwapMax=0"):
        assert (line in rendered) is capped, (app, line)


def test_the_console_unit_carries_no_memory_cap() -> None:
    assert "Memory" not in _render("weightroom")


@pytest.mark.parametrize("app", UNIT_APPLICATIONS)
def test_every_unit_names_the_version_that_wrote_it(app: str) -> None:
    first = _render(app).splitlines()[0]
    assert f"WeightRoomGym {VERSION}" in first
    assert first.startswith(f"# {unit_name(app)}")


def test_rendering_is_deterministic_so_sync_can_compare_bytes() -> None:
    assert _render("loadcoach") == _render("loadcoach")


def test_memory_values_come_from_configuration_not_the_template() -> None:
    rendered = render_unit(
        "freeweight",
        executable="/opt/fw/bin/freeweight",
        version=VERSION,
        memory_high="56G",
        memory_max="58G",
    )
    assert "MemoryHigh=56G" in rendered
    assert "MemoryMax=58G" in rendered


def test_an_unknown_application_has_no_unit() -> None:
    with pytest.raises(ValueError, match="has no unit"):
        unit_name("ollama")


def test_an_empty_executable_is_refused_rather_than_written_as_an_empty_exec_start() -> None:
    with pytest.raises(ValueError, match="needs an executable"):
        render_unit("loadcoach", executable="", version=VERSION, memory_high="1G", memory_max="2G")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/opt/bin/loadcoach", "/opt/bin/loadcoach"),
        ("/home/op/My Tools/bin/loadcoach", '"/home/op/My Tools/bin/loadcoach"'),
        ('/opt/we"ird/loadcoach', '"/opt/we\\"ird/loadcoach"'),
        ("", '""'),
    ],
)
def test_exec_start_arguments_are_quoted_only_when_systemd_needs_it(
    raw: str, expected: str
) -> None:
    assert escape_exec_argument(raw) == expected


def test_a_path_with_a_space_reaches_exec_start_quoted() -> None:
    rendered = render_unit(
        "ideapress",
        executable="/home/op/My Tools/bin/ideapress",
        version=VERSION,
        memory_high="22G",
        memory_max="24G",
    )
    assert 'ExecStart="/home/op/My Tools/bin/ideapress" serve' in rendered


def test_identical_text_has_no_diff() -> None:
    rendered = _render("loadcoach")
    assert unit_diff(rendered, rendered) == ()


def test_an_absent_file_diffs_against_nothing_and_shows_the_whole_unit() -> None:
    rendered = _render("loadcoach")
    diff = unit_diff(None, rendered)
    assert diff
    assert any(line.startswith("--- absent") for line in diff)
    assert any(line == "+[Service]" for line in diff)


def test_a_hand_edit_shows_up_as_the_line_that_will_be_overwritten() -> None:
    rendered = _render("freeweight")
    edited = rendered.replace("MemoryMax=24G", "MemoryMax=30G")
    diff = unit_diff(edited, rendered)
    assert "-MemoryMax=30G" in diff
    assert "+MemoryMax=24G" in diff


def test_every_unit_is_a_plausible_systemd_file() -> None:
    for app in UNIT_APPLICATIONS:
        rendered = _render(app)
        assert rendered.endswith("\n")
        assert rendered.count("[Unit]") == 1
        assert rendered.count("[Service]") == 1
        assert rendered.count("[Install]") == 1
        assert re.search(r"^WantedBy=default\.target$", rendered, re.MULTILINE)
        assert re.search(r"^Restart=on-failure$", rendered, re.MULTILINE)
