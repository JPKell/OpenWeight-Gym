"""The alert evaluator's writes and its five sources, each with a firing and a clearing fixture.

Development plan Phase 9: a journal line with ``oom-kill`` on ``ollama.service``; a unit going
down; a temperature over the threshold; a balance over its ceiling; a breaker row — and one active
alert per subject, acknowledge, history. The journal lines are the shapes the reference machine's
own journal recorded on 2026-09-09, with the unit changed to Ollama's.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest
import respx
from baseaicore import Money, new_id
from loadledger import CeilingScope
from sqlalchemy.exc import IntegrityError
from weightsdb import DatabaseError

from tests.integration.test_jobs_queue import T0, database, settings_for
from tests.support import fake_application
from weightroom.domain.alerts import EVERY_SUBJECT, Firing, Reading
from weightroom.infrastructure.db.models import Alert
from weightroom.services.alerts import (
    KILL_PATTERN,
    AlertEvaluator,
    AlertNotFound,
    acknowledge,
    active_alerts,
    app_down_source,
    apply,
    banner,
    breaker_open_source,
    budget_ceiling_source,
    gpu_thermal_source,
    history,
    memory_cap_source,
    sampler_temperature,
)
from weightroom.services.costs import AppCosts
from weightroom.services.processes import CommandResult, FakeSystemdController

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from weightroom.services.database import Database

__all__ = ["database"]

SECOND = timedelta(seconds=1)


def _hot(temperature: float) -> Reading:
    return Reading(
        "gpu_thermal",
        (Firing("gpu0", {"temperature_c": temperature, "threshold_c": 85.0}),),
        frozenset({"gpu0"}),
    )


# --- The one-active rule, acknowledge, history ----------------------------------------------------


def test_one_active_alert_per_subject_seen_again_then_cleared_with_its_history(
    database: Database,
) -> None:
    apply(database, _hot(91.0), now=T0)
    apply(database, _hot(93.0), now=T0 + 30 * SECOND)
    active = active_alerts(database)
    assert len(active) == 1
    assert (active[0].detail["temperature_c"], active[0].last_seen_at) == (93.0, T0 + 30 * SECOND)
    apply(database, Reading("gpu_thermal", (), frozenset({"gpu0"})), now=T0 + 60 * SECOND)
    assert active_alerts(database) == []
    rows, _more = history(database, limit=10)
    assert [row.event for row in rows] == ["cleared", "opened"]


def test_the_database_itself_refuses_a_second_active_alert_for_one_subject(
    database: Database,
) -> None:
    apply(database, _hot(91.0), now=T0)
    with pytest.raises((IntegrityError, DatabaseError)), database.write() as session:
        session.add(
            Alert(
                id=new_id(),
                source="gpu_thermal",
                subject="gpu0",
                severity="warning",
                opened_at=T0,
                last_seen_at=T0,
                detail={},
            )
        )


def test_an_acknowledged_kill_closes_and_a_later_kill_opens_a_new_alert(database: Database) -> None:
    kill = Reading("memory_cap", (Firing("ollama.service", {"line": "kill one", "cursor": "c1"}),))
    apply(database, kill, now=T0)
    first = active_alerts(database)[0]
    shown = banner(database)
    assert shown.count == 1
    assert shown.newest is not None
    assert (shown.newest.label, shown.newest.subject) == ("memory cap fired", "ollama.service")
    apply(database, Reading("memory_cap", ()), now=T0 + 30 * SECOND)
    assert len(active_alerts(database)) == 1  # an event never clears on its own

    acknowledged = acknowledge(database, first.id, operator="jordan", now=T0 + 40 * SECOND)

    assert (acknowledged.state, acknowledged.acknowledged_by) == ("closed", "jordan")
    assert banner(database).count == 0
    assert active_alerts(database) == []
    again = Reading("memory_cap", (Firing("ollama.service", {"line": "kill two", "cursor": "c2"}),))
    apply(database, again, now=T0 + 60 * SECOND)
    assert [one.id != first.id for one in active_alerts(database)] == [True]


def test_an_acknowledged_condition_leaves_the_banner_but_stays_until_it_clears(
    database: Database,
) -> None:
    apply(database, _hot(91.0), now=T0)
    alert = active_alerts(database)[0]
    assert (
        acknowledge(database, alert.id, operator="jordan", now=T0 + SECOND).state == "acknowledged"
    )
    assert banner(database).count == 0
    apply(database, _hot(95.0), now=T0 + 30 * SECOND)
    assert [one.id for one in active_alerts(database)] == [alert.id]
    apply(database, Reading("gpu_thermal", (), frozenset({"gpu0"})), now=T0 + 60 * SECOND)
    assert active_alerts(database) == []
    assert (
        acknowledge(database, alert.id, operator="x", now=T0 + 90 * SECOND).acknowledged_by
        == "jordan"
    )


def test_acknowledging_an_alert_that_does_not_exist_is_refused(database: Database) -> None:
    with pytest.raises(AlertNotFound):
        acknowledge(database, "01NOSUCHALERT0000000000000", operator="jordan", now=T0)


# --- app_down -------------------------------------------------------------------------------------


def test_app_down_fires_on_a_failed_unit_and_an_unhealthy_running_one_then_clears(
    tmp_path: Path, database: Database
) -> None:
    loadcoach, _config, _document = fake_application(tmp_path, "loadcoach")
    ideapress, _config, _document = fake_application(tmp_path, "ideapress")
    settings = settings_for(
        tmp_path,
        f'[apps.loadcoach]\nexecutable = "{loadcoach}"\n'
        f'[apps.ideapress]\nexecutable = "{ideapress}"\n',
    )
    host = FakeSystemdController(
        states={"loadcoach.service": "failed", "ideapress.service": "active"}
    )
    source = app_down_source(settings, host, httpx.Client(), which=lambda _name: None)
    with respx.mock() as router:
        router.get("http://127.0.0.1:8767/api/v1/health").mock(
            return_value=httpx.Response(503, json={"status": "unavailable"})
        )
        down = source(T0, T0)
    fired = {firing.subject: firing.detail for firing in down.firing}
    assert fired["loadcoach.service"]["unit_state"] == "failed"
    assert fired["ideapress.service"]["health_status"] == 503
    apply(database, down, now=T0)
    assert {one.subject for one in active_alerts(database)} == set(fired)

    host.states["loadcoach.service"] = "active"
    with respx.mock() as router:
        router.get("http://127.0.0.1:8766/api/v1/health").mock(return_value=httpx.Response(200))
        router.get("http://127.0.0.1:8767/api/v1/health").mock(return_value=httpx.Response(200))
        up = source(T0, T0 + 30 * SECOND)
    assert up.firing == ()
    apply(database, up, now=T0 + 30 * SECOND)
    assert active_alerts(database) == []


def test_a_stopped_or_uninstalled_application_is_not_down_and_no_systemd_cannot_look(
    tmp_path: Path,
) -> None:
    loadcoach, _config, _document = fake_application(tmp_path, "loadcoach")
    settings = settings_for(tmp_path, f'[apps.loadcoach]\nexecutable = "{loadcoach}"\n')
    stopped = FakeSystemdController(states={"loadcoach.service": "inactive"})
    reading = app_down_source(settings, stopped, httpx.Client(), which=lambda _name: None)(T0, T0)
    assert reading.firing == ()
    assert reading.covers == frozenset({EVERY_SUBJECT})
    unsupported = app_down_source(
        settings, FakeSystemdController(supported=False), httpx.Client(), which=lambda _name: None
    )(T0, T0)
    assert unsupported.problem is not None
    assert unsupported.covers == frozenset()


# --- memory_cap -----------------------------------------------------------------------------------


def _entry(cursor: str, seconds: float, message: str, **fields: str) -> dict[str, str]:
    stamp = int((T0 + timedelta(seconds=seconds)).timestamp() * 1_000_000)
    return {"__CURSOR": cursor, "__REALTIME_TIMESTAMP": str(stamp), "MESSAGE": message, **fields}


KERNEL_KILL = _entry(
    "s=1;i=1",
    10,
    "oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=system.slice,mems_allowed=0,"
    "oom_memcg=/system.slice/ollama.service,task_memcg=/system.slice/ollama.service,"
    "task=ollama,pid=4242,uid=997",
    _TRANSPORT="kernel",
    SYSLOG_IDENTIFIER="kernel",
)
SYSTEMD_KILL = _entry(
    "s=1;i=2",
    11,
    "ollama.service: Failed with result 'oom-kill'.",
    UNIT="ollama.service",
    SYSLOG_IDENTIFIER="systemd",
)
UNNAMED = _entry(
    "s=1;i=3", 12, "llama-server invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0"
)
BEFORE_THE_WINDOW = _entry("s=1;i=0", -3600, "ollama.service: Failed with result 'oom-kill'.")
SCOPE_KILL = _entry(
    "s=1;i=4",
    13,
    "oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=user.slice,mems_allowed=0,"
    "oom_memcg=/user.slice/user-1000.slice/user@1000.service/app.slice/"
    "wr-gym-fwrun-01M26MTDZCXP3ZR99EWDN53AT4.scope,task=llama-server,pid=5151,uid=1000",
    _TRANSPORT="kernel",
    SYSLOG_IDENTIFIER="kernel",
)


def test_memory_cap_fires_on_a_kill_line_naming_ollama_within_the_window_and_only_then(
    database: Database,
) -> None:
    calls: list[list[str]] = []
    journal = "\n".join(
        json.dumps(entry) for entry in (BEFORE_THE_WINDOW, KERNEL_KILL, SYSTEMD_KILL, UNNAMED)
    )

    def runner(argv: Sequence[str], env: object, timeout: float) -> CommandResult:
        calls.append(list(argv))
        if "--user" in argv:
            return CommandResult(tuple(argv), 1, "", "")  # --grep matched nothing
        return CommandResult(tuple(argv), 0, journal, "")

    source = memory_cap_source(
        settings_for_database(database), which=lambda _name: "/usr/bin/journalctl", runner=runner
    )
    reading = source(T0, T0 + 30 * SECOND)

    assert reading.problem is None
    assert [firing.subject for firing in reading.firing] == ["ollama.service", "ollama.service"]
    system, user = calls
    assert system[system.index("--grep") + 1] == KILL_PATTERN
    assert system[system.index("--since") + 1] == f"@{int(T0.timestamp())}"
    assert "--case-sensitive=no" in system
    assert "--user" in user
    apply(database, reading, now=T0 + 30 * SECOND)
    shown = banner(database).newest
    assert shown is not None
    assert (shown.label, shown.subject) == ("memory cap fired", "ollama.service")
    assert shown.summary == "ollama.service: Failed with result 'oom-kill'."


def settings_for_database(database: Database) -> Any:  # noqa: ANN401 — Settings, for the one source
    """The memory-cap source reads only ``[host] ollama_unit`` from settings."""
    return SimpleNamespace(host=SimpleNamespace(ollama_unit="ollama.service"))


def test_memory_cap_watches_the_scopes_the_console_launches_for_a_suite_run(
    database: Database,
) -> None:
    """W9 §5 item 5g: a kill inside `wr-gym-fwrun-<job>.scope` is a firing, named by the scope."""

    def runner(argv: Sequence[str], env: object, timeout: float) -> CommandResult:
        if "--user" in argv:
            return CommandResult(tuple(argv), 0, json.dumps(SCOPE_KILL), "")
        return CommandResult(tuple(argv), 1, "", "")

    source = memory_cap_source(
        settings_for_database(database), which=lambda _name: "/usr/bin/journalctl", runner=runner
    )
    reading = source(T0, T0 + 30 * SECOND)
    assert [firing.subject for firing in reading.firing] == [
        "wr-gym-fwrun-01M26MTDZCXP3ZR99EWDN53AT4.scope"
    ]


def test_memory_cap_without_journalctl_or_with_a_refused_journal_says_so() -> None:
    absent = memory_cap_source(settings_for_database(cast(Any, None)), which=lambda _name: None)
    assert absent(T0, T0).problem == "this host has no journalctl"

    def refused(argv: Sequence[str], env: object, timeout: float) -> CommandResult:
        return CommandResult(tuple(argv), 1, "", "Failed to open journal: Permission denied")

    reading = memory_cap_source(
        settings_for_database(cast(Any, None)),
        which=lambda _name: "/usr/bin/journalctl",
        runner=refused,
    )(T0, T0)
    assert "Permission denied" in (reading.problem or "")


# --- gpu_thermal ----------------------------------------------------------------------------------


def test_gpu_thermal_fires_over_the_threshold_clears_under_it_and_cannot_look_without_a_reading(
    database: Database,
) -> None:
    readings = iter([(0, 91.0), (0, 70.0), None])
    source = gpu_thermal_source(lambda: next(readings), lambda: 85.0)
    hot = source(T0, T0)
    assert [(one.subject, one.detail["temperature_c"]) for one in hot.firing] == [("gpu0", 91.0)]
    apply(database, hot, now=T0)
    cool = source(T0, T0 + 30 * SECOND)
    apply(database, cool, now=T0 + 30 * SECOND)
    assert active_alerts(database) == []
    blind = source(T0, T0 + 60 * SECOND)
    assert blind.problem is not None
    assert blind.covers == frozenset()


def test_the_samplers_latest_temperature_is_read_and_unavailable_is_none() -> None:
    assert sampler_temperature(None) is None
    service = SimpleNamespace(
        latest=lambda: SimpleNamespace(gpus=[SimpleNamespace(index=0, temperature_c=88.0)])
    )
    assert sampler_temperature(cast(Any, service)) == (0, 88.0)
    empty = SimpleNamespace(latest=lambda: SimpleNamespace(gpus=[]))
    assert sampler_temperature(cast(Any, empty)) is None


# --- budget_ceiling -------------------------------------------------------------------------------


def _verdict(spent_nanos: int | None, *, cap_nanos: int = 1_000_000_000) -> Any:  # noqa: ANN401
    ceiling = SimpleNamespace(
        scope=CeilingScope.PER_DAY,
        tag=None,
        money=Money(currency="USD", nanos=cap_nanos),
        tokens=None,
    )
    spent = None if spent_nanos is None else Money(currency="USD", nanos=spent_nanos)
    return SimpleNamespace(
        ceiling=ceiling,
        exceeded=False,
        money_spent=spent,
        tokens_spent=0,
        unpriced_debit_count=3,
    )


def test_budget_ceiling_fires_at_the_ceiling_names_the_scope_and_clears_below_it(
    database: Database,
) -> None:
    answers = {
        "promptcadence": AppCosts("promptcadence", None, (_verdict(1_000_000_000),), None),
        "ideapress": AppCosts("ideapress", None, (), "ideapress's database could not be read"),
    }
    source = budget_ceiling_source(lambda app: answers[app])
    at_ceiling = source(T0, T0)
    assert [one.subject for one in at_ceiling.firing] == ["promptcadence:per_day"]
    detail = at_ceiling.firing[0].detail
    assert (detail["money_spent"], detail["money_ceiling"], detail["unpriced_debit_count"]) == (
        "1.00 USD",
        "1.00 USD",
        3,
    )
    assert at_ceiling.covers == frozenset({"promptcadence"})
    assert "ideapress" in (at_ceiling.problem or "")
    apply(database, at_ceiling, now=T0)
    answers["promptcadence"] = replace(answers["promptcadence"], verdicts=(_verdict(400_000_000),))
    apply(database, source(T0, T0 + 30 * SECOND), now=T0 + 30 * SECOND)
    assert active_alerts(database) == []


def test_nothing_priced_against_a_zero_ceiling_is_not_at_it() -> None:
    answers = {
        "promptcadence": AppCosts("promptcadence", None, (_verdict(None, cap_nanos=0),), None),
        "ideapress": AppCosts("ideapress", None, (), None),
    }
    assert budget_ceiling_source(lambda app: answers[app])(T0, T0).firing == ()


# --- breaker_open ---------------------------------------------------------------------------------

GPT_OSS = "ollama/gpt-oss:20b@sha256:abc"


def _reliability(state: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "reliability": [
                {
                    "model": {"canonical_id": GPT_OSS, "subject_canonical_id": GPT_OSS},
                    "task_profile_id": "general.chat",
                    "circuit_breaker": {
                        "state": state,
                        "opened_at": "2026-09-10T11:59:00Z",
                        "reason": "5 of 10 attempts failed",
                    },
                },
                {
                    "model": {"canonical_id": "ollama/qwen3:8b@sha256:def"},
                    "circuit_breaker": {"state": "closed"},
                },
            ]
        },
    )


def test_breaker_open_fires_on_an_open_breaker_clears_when_it_closes_and_cannot_look_when_down(
    tmp_path: Path, database: Database
) -> None:
    source = breaker_open_source(settings_for(tmp_path), httpx.Client())
    url = "http://127.0.0.1:8766/api/v1/reliability"
    with respx.mock() as router:
        router.get(url).mock(return_value=_reliability("open"))
        opened = source(T0, T0)
    assert [(one.subject, one.detail["reason"]) for one in opened.firing] == [
        (GPT_OSS, "5 of 10 attempts failed")
    ]
    apply(database, opened, now=T0)
    with respx.mock() as router:
        router.get(url).mock(side_effect=httpx.ConnectError("refused"))
        down = source(T0, T0 + 30 * SECOND)
    assert down.problem is not None
    apply(database, down, now=T0 + 30 * SECOND)
    assert len(active_alerts(database)) == 1  # LoadCoach down is not the breaker closing
    with respx.mock() as router:
        router.get(url).mock(return_value=_reliability("closed"))
        closed = source(T0, T0 + 60 * SECOND)
    apply(database, closed, now=T0 + 60 * SECOND)
    assert active_alerts(database) == []


# --- The evaluator --------------------------------------------------------------------------------


def test_the_evaluator_reads_every_source_over_consecutive_windows_and_keeps_its_problems(
    tmp_path: Path, database: Database
) -> None:
    windows: list[tuple[object, object]] = []

    def hot(since: Any, now: Any) -> Reading:  # noqa: ANN401 — the Source signature
        windows.append((since, now))
        return _hot(90.0)

    def broken(since: Any, now: Any) -> Reading:  # noqa: ANN401
        message = "no bus"
        raise RuntimeError(message)

    ticks = iter([T0, T0 + 30 * SECOND, T0 + 60 * SECOND])
    evaluator = AlertEvaluator(
        database,
        settings_for(tmp_path),
        {"gpu_thermal": hot, "app_down": broken},
        clock=lambda: next(ticks),
    )
    evaluator.evaluate_once()
    evaluator.evaluate_once()
    assert windows == [(T0, T0 + 30 * SECOND), (T0 + 30 * SECOND, T0 + 60 * SECOND)]
    assert evaluator.problems == {"app_down": "RuntimeError: no bus"}
    assert len(active_alerts(database)) == 1
    evaluator.start()
    evaluator.stop()
