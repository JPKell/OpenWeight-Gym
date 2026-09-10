"""weightroom.domain.alerts: ADR-0137's rules, one reading at a time."""

from __future__ import annotations

import pytest

from weightroom.domain.alerts import EVERY_SUBJECT, ActiveAlert, Decision, Firing, Reading, decide


def test_a_firing_subject_with_no_active_alert_opens_one() -> None:
    hot = Firing("gpu0", {"temperature_c": 91.0})
    decision = decide(Reading("gpu_thermal", (hot,), frozenset({"gpu0"})), [])
    assert decision == Decision(opens=(hot,))


def test_a_subject_still_firing_is_seen_on_its_alert_and_never_opened_twice() -> None:
    hotter = Firing("gpu0", {"temperature_c": 92.0})
    decision = decide(
        Reading("gpu_thermal", (hotter,), frozenset({"gpu0"})),
        [ActiveAlert("a1", "gpu_thermal", "gpu0")],
    )
    assert decision == Decision(seen=(("a1", hotter),))


def test_a_condition_clears_when_a_reading_that_covers_it_finds_it_right() -> None:
    active = [
        ActiveAlert("a1", "app_down", "loadcoach.service"),
        ActiveAlert("a2", "gpu_thermal", "gpu0"),
    ]
    decision = decide(Reading("app_down", (), frozenset({EVERY_SUBJECT})), active)
    assert decision == Decision(clears=("a1",))


def test_a_reading_that_could_not_look_clears_nothing() -> None:
    decision = decide(
        Reading("breaker_open", problem="LoadCoach did not answer"),
        [ActiveAlert("a1", "breaker_open", "ollama/gpt-oss:20b@sha256:abc")],
    )
    assert decision == Decision()


def test_an_applications_name_covers_its_own_subjects_and_no_other() -> None:
    active = [
        ActiveAlert("a1", "budget_ceiling", "promptcadence:per_day"),
        ActiveAlert("a2", "budget_ceiling", "ideapress:per_day"),
    ]
    decision = decide(Reading("budget_ceiling", (), frozenset({"promptcadence"})), active)
    assert decision == Decision(clears=("a1",))


def test_an_event_never_clears_and_the_last_line_about_a_subject_wins() -> None:
    first = Firing("loadcoach.service", {"line": "one"})
    second = Firing("loadcoach.service", {"line": "two"})
    decision = decide(
        Reading("memory_cap", (first, second), frozenset({EVERY_SUBJECT})),
        [ActiveAlert("a1", "memory_cap", "ollama.service")],
    )
    assert decision == Decision(opens=(second,))


def test_a_source_this_build_does_not_have_is_refused() -> None:
    with pytest.raises(ValueError, match="not an alert source"):
        decide(Reading("disk_full"), [])
