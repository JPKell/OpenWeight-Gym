"""weightroom.services.alerts — the evaluator thread, the five sources and the banner (spec §7.10).

ADR-0137 decides what an alert is; ``domain/alerts.decide`` applies it to one reading. This module
reads the five sources, writes what each reading decided, and answers the banner, the pages and the
acknowledgement. It sends nothing anywhere — no mail, no webhook, no push (spec §2, §3).

Each source, and what *cannot look* means for it (a reading that could not look clears nothing):

* ``app_down`` — ``systemctl --user show`` for every installed application's unit. A ``failed``
  unit or one restarting itself fires, and so does a unit active for a minute whose
  ``/api/v1/health`` does not answer ``200``; an inactive unit is a choice, not an outage. No
  ``systemctl``: cannot look.
* ``memory_cap`` — the system and the user journal since the last evaluation, grepped by
  ``journalctl`` itself for ADR-0119's kill and kept where a line names ``ollama.service`` or an
  application's unit. The kernel's ``oom-kill:…oom_memcg=/…/<unit>`` line and systemd's ``<unit>:
  Failed with result 'oom-kill'`` both name it — read off the reference machine's own journal of
  2026-09-09. ``journalctl --grep`` exits 1 when nothing matched, which is an answer.
* ``gpu_thermal`` — the in-process sampler's latest GPU temperature against
  ``alerts.gpu_temperature_c``. No reading: cannot look.
* ``budget_ceiling`` — ``services/costs.costs_for`` per ledger-mounting application; a verdict at or
  over its ceiling fires, subject ``<app>:<scope>[:<tag>]``. An application whose ledger cannot be
  read covers none of its own subjects.
* ``breaker_open`` — LoadCoach's ``GET /api/v1/reliability``; a pair whose ``circuit_breaker.state``
  is ``open`` fires, subject the model. LoadCoach not answering: cannot look.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, Final, cast

import httpx
from baseaicore import SuiteError, is_supported, new_id
from sqlalchemy import select

from weightroom.config import APPLICATIONS
from weightroom.domain.alerts import (
    EVENT_SOURCES,
    EVERY_SUBJECT,
    SOURCE_LABELS,
    SOURCE_SEVERITY,
    ActiveAlert,
    Decision,
    Firing,
    Reading,
    decide,
)
from weightroom.domain.jobs import SUITE_RUN_SCOPE_PREFIX
from weightroom.domain.units import unit_name
from weightroom.infrastructure.db.models import Alert, AlertHistory
from weightroom.services.apps import bearer_token
from weightroom.services.costs import COST_APPS, money_text
from weightroom.services.journal import parse_entry
from weightroom.services.processes import (
    UnitActionFailed,
    UnitUnsupported,
    child_environment,
    executable_for,
    run_command,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from loadledger import CeilingVerdict

    from weightroom.config import Settings
    from weightroom.services.costs import AppCosts
    from weightroom.services.database import Database
    from weightroom.services.db_reader import DatabaseUrlCache
    from weightroom.services.processes import Runner, SystemdController
    from weightroom.services.telemetry import TelemetryService

__all__ = [
    "HEALTH_GRACE_SECONDS",
    "KILL_PATTERN",
    "AlertEvaluator",
    "AlertNotFound",
    "AlertView",
    "Banner",
    "HistoryView",
    "Source",
    "acknowledge",
    "active_alerts",
    "app_down_source",
    "apply",
    "banner",
    "breaker_open_source",
    "budget_ceiling_source",
    "default_sources",
    "gpu_thermal_source",
    "history",
    "memory_cap_source",
    "recent_alerts",
    "sampler_temperature",
]

logger = logging.getLogger(__name__)

HEALTH_GRACE_SECONDS: Final = 60.0
"""A unit active for less than this is still starting; its API is not judged yet."""

KILL_PATTERN: Final = "oom-kill|OOM killer|MemoryMax|systemd-oomd|memory pressure"
"""What ``journalctl --grep`` looks for, case-insensitively (ADR-0119, MEMORY_SAFETY.md §2.3)."""

_JOURNAL_TIMEOUT_SECONDS: Final = 30.0
_HTTP_TIMEOUT_SECONDS: Final = 5.0
_LINE_CHARS: Final = 500

type Source = Callable[[datetime, datetime], Reading]
"""``(since, now) -> Reading``: one look at one source, over the window since the last look."""


class AlertNotFound(SuiteError):
    """An alert id that is not in the database."""

    code: ClassVar[str] = "NOT_FOUND"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@dataclass(frozen=True, slots=True)
class AlertView:
    """One alert episode as the banner, the pages, the API and the CLI show it."""

    id: str
    source: str
    subject: str
    severity: str
    opened_at: datetime
    last_seen_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    cleared_at: datetime | None
    closed_at: datetime | None
    detail: dict[str, Any]

    @classmethod
    def of(cls, row: Alert) -> AlertView:
        """Read a row."""
        return cls(
            id=row.id,
            source=row.source,
            subject=row.subject,
            severity=row.severity,
            opened_at=row.opened_at,
            last_seen_at=row.last_seen_at,
            acknowledged_at=row.acknowledged_at,
            acknowledged_by=row.acknowledged_by,
            cleared_at=row.cleared_at,
            closed_at=row.closed_at,
            detail=dict(cast("Mapping[str, Any]", row.detail or {})),
        )

    @property
    def label(self) -> str:
        """``memory cap fired``."""
        return SOURCE_LABELS.get(self.source, self.source)

    @property
    def state(self) -> str:
        """``open``, ``acknowledged`` (still active), ``cleared`` or ``closed``."""
        if self.cleared_at is not None:
            return "cleared"
        if self.closed_at is not None:
            return "closed"
        return "acknowledged" if self.acknowledged_at is not None else "open"

    @property
    def summary(self) -> str:
        """One line of evidence, in the source's own terms."""
        detail = self.detail
        if self.source == "memory_cap":
            return str(detail.get("line", ""))
        if self.source == "gpu_thermal":
            return f"{detail.get('temperature_c')} °C, threshold {detail.get('threshold_c')} °C"
        if self.source == "app_down":
            if detail.get("health_status") is not None or detail.get("error"):
                answer = detail.get("health_status") or detail.get("error")
                return f"running; /api/v1/health answered {answer}"
            why = detail.get("result") or detail.get("sub_state")
            return f"unit {detail.get('unit_state')} ({why})"
        if self.source == "budget_ceiling":
            spent = detail.get("money_spent") or detail.get("tokens_spent")
            ceiling = detail.get("money_ceiling") or detail.get("tokens_ceiling")
            return f"{spent} spent against {ceiling} ({detail.get('scope')})"
        return str(detail.get("reason") or detail.get("task_profile_id") or "")

    def as_json(self) -> dict[str, Any]:
        """The api.md §7 shape."""
        return {
            "id": self.id,
            "source": self.source,
            "label": self.label,
            "subject": self.subject,
            "severity": self.severity,
            "state": self.state,
            "opened_at": _iso(self.opened_at),
            "last_seen_at": _iso(self.last_seen_at),
            "acknowledged_at": _iso(self.acknowledged_at),
            "acknowledged_by": self.acknowledged_by,
            "cleared_at": _iso(self.cleared_at),
            "closed_at": _iso(self.closed_at),
            "summary": self.summary,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class HistoryView:
    """One history row, with the alert's source and subject beside it."""

    id: str
    alert_id: str
    source: str
    subject: str
    event: str
    at: datetime
    detail: dict[str, Any]

    @property
    def label(self) -> str:
        """The source's label."""
        return SOURCE_LABELS.get(self.source, self.source)

    def as_json(self) -> dict[str, Any]:
        """The api.md §7 shape."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "source": self.source,
            "subject": self.subject,
            "event": self.event,
            "at": self.at.isoformat(),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class Banner:
    """What the shell's banner shows: how many active alerts nobody has acknowledged, and the
    newest of them."""

    count: int
    newest: AlertView | None

    def as_json(self) -> dict[str, Any]:
        """The api.md §7 shape."""
        return {"count": self.count, "newest": self.newest.as_json() if self.newest else None}


# --- Writing a reading ----------------------------------------------------------------------------


def _history(alert_id: str, event: str, at: datetime, detail: Mapping[str, Any]) -> AlertHistory:
    return AlertHistory(id=new_id(), alert_id=alert_id, event=event, at=at, detail=dict(detail))


def apply(database: Database, reading: Reading, *, now: datetime) -> Decision:
    """Write what one reading decided (ADR-0137): open, see, clear — in one transaction.

    Returns:
        The decision that was written.
    """
    with database.write() as session:
        rows = session.execute(
            select(Alert).where(Alert.source == reading.source, Alert.closed_at.is_(None))
        ).scalars()
        active = {row.id: row for row in rows}
        decision = decide(
            reading, [ActiveAlert(row.id, row.source, row.subject) for row in active.values()]
        )
        for firing in decision.opens:
            row = Alert(
                id=new_id(),
                source=reading.source,
                subject=firing.subject,
                severity=SOURCE_SEVERITY[reading.source],
                opened_at=now,
                last_seen_at=now,
                detail=dict(firing.detail),
            )
            session.add(row)
            session.flush()
            session.add(_history(row.id, "opened", now, firing.detail))
        for alert_id, firing in decision.seen:
            row = active[alert_id]
            changed = dict(cast("Mapping[str, Any]", row.detail or {})) != dict(firing.detail)
            row.last_seen_at = now
            row.detail = dict(firing.detail)
            if changed and reading.source in EVENT_SOURCES:
                session.add(_history(row.id, "seen", now, firing.detail))
        for alert_id in decision.clears:
            row = active[alert_id]
            row.cleared_at = row.closed_at = now
            session.add(_history(row.id, "cleared", now, {}))
    return decision


def active_alerts(database: Database) -> list[AlertView]:
    """Every episode not yet closed, newest first."""
    with database.read() as session:
        rows = session.execute(
            select(Alert).where(Alert.closed_at.is_(None)).order_by(Alert.opened_at.desc())
        ).scalars()
        return [AlertView.of(row) for row in rows]


def recent_alerts(database: Database, *, limit: int = 50) -> list[AlertView]:
    """The newest episodes, active or closed."""
    with database.read() as session:
        rows = session.execute(
            select(Alert).order_by(Alert.opened_at.desc(), Alert.id.desc()).limit(limit)
        ).scalars()
        return [AlertView.of(row) for row in rows]


def banner(database: Database) -> Banner:
    """The active alerts nobody has acknowledged: how many, and the newest."""
    with database.read() as session:
        rows = session.execute(
            select(Alert)
            .where(Alert.closed_at.is_(None), Alert.acknowledged_at.is_(None))
            .order_by(Alert.last_seen_at.desc(), Alert.opened_at.desc())
        ).scalars()
        views = [AlertView.of(row) for row in rows]
    return Banner(count=len(views), newest=views[0] if views else None)


def acknowledge(database: Database, alert_id: str, *, operator: str, now: datetime) -> AlertView:
    """Record that ``operator`` has seen the alert; an event's episode closes (ADR-0137 rule 3).

    Acknowledging twice changes nothing the second time.

    Raises:
        AlertNotFound: No such alert.
    """
    with database.write() as session:
        row = session.get(Alert, alert_id)
        if row is None:
            raise AlertNotFound(f"No alert {alert_id!r}.", details={"alert_id": alert_id})
        if row.acknowledged_at is None:
            row.acknowledged_at = now
            row.acknowledged_by = operator
            if row.source in EVENT_SOURCES and row.closed_at is None:
                row.closed_at = now
            session.add(_history(row.id, "acknowledged", now, {"by": operator}))
        return AlertView.of(row)


def history(
    database: Database, *, limit: int, before_id: str | None = None
) -> tuple[list[HistoryView], bool]:
    """What happened to every alert, newest first, and whether more follows."""
    statement = (
        select(AlertHistory, Alert.source, Alert.subject)
        .join(Alert, Alert.id == AlertHistory.alert_id)
        .order_by(AlertHistory.at.desc(), AlertHistory.id.desc())
        .limit(limit + 1)
    )
    if before_id is not None:
        statement = statement.where(AlertHistory.id < before_id)
    with database.read() as session:
        rows = session.execute(statement).all()
        views = [
            HistoryView(
                id=entry.id,
                alert_id=entry.alert_id,
                source=source,
                subject=subject,
                event=entry.event,
                at=entry.at,
                detail=dict(cast("Mapping[str, Any]", entry.detail or {})),
            )
            for entry, source, subject in rows[:limit]
        ]
    return views, len(rows) > limit


# --- The five sources -----------------------------------------------------------------------------


def _health_status(settings: Settings, app: str, client: httpx.Client) -> tuple[int | None, str]:
    base_url = getattr(settings.apps, app).base_url
    if not base_url:
        return None, "no base_url configured"
    headers = {}
    token = bearer_token(settings, app)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = client.get(
            f"{base_url.rstrip('/')}/api/v1/health", headers=headers, timeout=_HTTP_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return None, f"{type(exc).__name__}: {exc}"[:300]
    return response.status_code, ""


def app_down_source(
    settings: Settings,
    controller: SystemdController,
    client: httpx.Client,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> Source:
    """``app_down`` (module docstring, ADR-0137 rule 5)."""

    def read(since: datetime, now: datetime) -> Reading:
        installed = [app for app in APPLICATIONS if executable_for(settings, app, which=which)]
        try:
            statuses = controller.show([unit_name(app) for app in installed]) if installed else {}
        except (UnitUnsupported, UnitActionFailed) as exc:
            return Reading("app_down", problem=exc.message)
        firing: list[Firing] = []
        for app in installed:
            unit = unit_name(app)
            status = statuses.get(unit)
            if status is None:
                continue
            if status.state == "failed" or status.sub_state == "auto-restart":
                firing.append(
                    Firing(
                        unit,
                        {
                            "app": app,
                            "unit_state": status.state,
                            "sub_state": status.sub_state,
                            "result": status.result,
                        },
                    )
                )
            elif status.state == "active" and (status.uptime_seconds or 0) >= HEALTH_GRACE_SECONDS:
                code, error = _health_status(settings, app, client)
                if code != 200:
                    firing.append(
                        Firing(
                            unit,
                            {
                                "app": app,
                                "unit_state": "active",
                                "health_status": code,
                                "error": error,
                            },
                        )
                    )
        return Reading("app_down", firing=tuple(firing), covers=frozenset({EVERY_SUBJECT}))

    return read


_SUITE_RUN_SCOPE = re.compile(re.escape(SUITE_RUN_SCOPE_PREFIX) + r"[0-9A-Za-z]+\.scope")
"""The scope `freeweight_suite_run` launches under (`domain/jobs.SUITE_RUN_SCOPE_PREFIX`)."""


def _named_unit(message: str, unit: str, watched: Sequence[str]) -> str | None:
    for candidate in watched:
        if candidate in message or unit == candidate:
            return candidate
    scope = _SUITE_RUN_SCOPE.search(message) or _SUITE_RUN_SCOPE.search(unit)
    return scope.group(0) if scope else None


def memory_cap_source(
    settings: Settings,
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = run_command,
) -> Source:
    """``memory_cap`` (module docstring): both journals, the kill named by unit."""
    watched = (settings.host.ollama_unit, *(unit_name(app) for app in APPLICATIONS))

    def read(since: datetime, now: datetime) -> Reading:
        journalctl = which("journalctl")
        if journalctl is None:
            return Reading("memory_cap", problem="this host has no journalctl")
        firing: list[Firing] = []
        cursors: set[str] = set()
        problems: list[str] = []
        for scope in ("system", "user"):
            argv = [journalctl, "--no-pager", "-o", "json", "--since", f"@{int(since.timestamp())}"]
            argv += ["--case-sensitive=no", "--grep", KILL_PATTERN]
            if scope == "user":
                argv.insert(1, "--user")
            result = runner(argv, child_environment(), _JOURNAL_TIMEOUT_SECONDS)
            if not result.ok:
                if result.returncode == 1 and not (result.stdout.strip() or result.stderr.strip()):
                    continue  # --grep matched nothing: exit 1, silent
                problems.append(f"{scope} journal: {result.failure_text}")
                continue
            for raw in result.stdout.splitlines():
                try:
                    decoded = json.loads(raw)
                except ValueError:
                    continue
                line = parse_entry(decoded) if isinstance(decoded, dict) else None
                if line is None or line.cursor in cursors or not since < line.at <= now:
                    continue
                cursors.add(line.cursor)
                unit = _named_unit(line.message, line.unit, watched)
                if unit is not None:
                    detail = {
                        "line": line.message[:_LINE_CHARS],
                        "at": line.at.isoformat(),
                        "identifier": line.identifier,
                        "cursor": line.cursor,
                    }
                    firing.append(Firing(unit, detail))
        return Reading("memory_cap", firing=tuple(firing), problem="; ".join(problems) or None)

    return read


def sampler_temperature(service: TelemetryService | None) -> tuple[int, float] | None:
    """The in-process sampler's latest primary-GPU temperature, or ``None`` when it has none."""
    snapshot = service.latest() if service is not None else None
    if snapshot is None or not snapshot.gpus:
        return None
    gpu = snapshot.gpus[0]
    if not is_supported(gpu.temperature_c):
        return None
    return gpu.index, float(gpu.temperature_c)


def gpu_thermal_source(
    temperature: Callable[[], tuple[int, float] | None], threshold: Callable[[], float]
) -> Source:
    """``gpu_thermal`` (module docstring)."""

    def read(since: datetime, now: datetime) -> Reading:
        reading = temperature()
        if reading is None:
            return Reading("gpu_thermal", problem="no GPU temperature reading")
        index, value = reading
        subject = f"gpu{index}"
        limit = threshold()
        firing = (
            (Firing(subject, {"temperature_c": value, "threshold_c": limit}),)
            if value > limit
            else ()
        )
        return Reading("gpu_thermal", firing=firing, covers=frozenset({subject}))

    return read


def _at_or_over(verdict: CeilingVerdict) -> bool:
    ceiling = verdict.ceiling
    if verdict.exceeded:
        return True
    money = verdict.money_spent
    if ceiling.money is not None and money is not None and 0 < ceiling.money.nanos <= money.nanos:
        return True
    tokens = verdict.tokens_spent
    return ceiling.tokens is not None and tokens is not None and 0 < ceiling.tokens <= tokens


def budget_ceiling_source(costs: Callable[[str], AppCosts]) -> Source:
    """``budget_ceiling`` (module docstring)."""

    def read(since: datetime, now: datetime) -> Reading:
        firing: list[Firing] = []
        covers: set[str] = set()
        problems: list[str] = []
        for app in COST_APPS:
            try:
                answer = costs(app)
            except Exception as exc:  # noqa: BLE001 — one unreadable ledger never stops the rest
                problems.append(f"{app}: {type(exc).__name__}: {exc}")
                continue
            if answer.unavailable is not None:
                problems.append(f"{app}: {answer.unavailable}")
                continue
            covers.add(app)
            for verdict in answer.verdicts:
                if not _at_or_over(verdict):
                    continue
                ceiling = verdict.ceiling
                subject = f"{app}:{ceiling.scope.value}" + (
                    f":{ceiling.tag}" if ceiling.tag else ""
                )
                firing.append(
                    Firing(
                        subject,
                        {
                            "app": app,
                            "scope": ceiling.scope.value,
                            "money_spent": (
                                money_text(verdict.money_spent) if verdict.money_spent else None
                            ),
                            "money_ceiling": money_text(ceiling.money) if ceiling.money else None,
                            "tokens_spent": verdict.tokens_spent,
                            "tokens_ceiling": ceiling.tokens,
                            "unpriced_debit_count": verdict.unpriced_debit_count,
                        },
                    )
                )
        return Reading(
            "budget_ceiling",
            firing=tuple(firing),
            covers=frozenset(covers),
            problem="; ".join(problems) or None,
        )

    return read


def breaker_open_source(settings: Settings, client: httpx.Client) -> Source:
    """``breaker_open`` (module docstring)."""

    def read(since: datetime, now: datetime) -> Reading:
        base_url = settings.apps.loadcoach.base_url
        headers = {}
        token = bearer_token(settings, "loadcoach")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = client.get(
                f"{base_url.rstrip('/')}/api/v1/reliability",
                headers=headers,
                timeout=_HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return Reading("breaker_open", problem=f"LoadCoach's /reliability: {exc}"[:300])
        entries = body.get("reliability") if isinstance(body, dict) else None
        if not isinstance(entries, list):
            return Reading("breaker_open", problem="LoadCoach's /reliability had no entries list")
        firing: list[Firing] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            breaker = entry.get("circuit_breaker")
            model = entry.get("model")
            if not isinstance(breaker, dict) or breaker.get("state") != "open":
                continue
            subject = ""
            if isinstance(model, dict):
                subject = str(model.get("subject_canonical_id") or model.get("canonical_id") or "")
            if subject:
                detail = {
                    "task_profile_id": entry.get("task_profile_id"),
                    "opened_at": breaker.get("opened_at"),
                    "reason": breaker.get("reason"),
                }
                firing.append(Firing(subject, detail))
        return Reading("breaker_open", firing=tuple(firing), covers=frozenset({EVERY_SUBJECT}))

    return read


def default_sources(
    settings: Settings,
    database: Database,
    *,
    controller: SystemdController,
    client: httpx.Client,
    urls: DatabaseUrlCache,
    temperature: Callable[[], tuple[int, float] | None],
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = run_command,
) -> dict[str, Source]:
    """The five sources over this console's own boundaries, in spec §7.10's order."""
    from weightroom.services.costs import costs_for
    from weightroom.services.settings import read_runtime_settings

    def threshold() -> float:
        try:
            effective = read_runtime_settings(database, settings=settings)
            return float(effective["alerts.gpu_temperature_c"])
        except Exception:  # noqa: BLE001 — an unreadable settings row falls back to the file
            return float(settings.alerts.gpu_temperature_c)

    def costs(app: str) -> AppCosts:
        return costs_for(
            settings,
            database,
            app,
            urls=urls,
            now=datetime.now(UTC),
            monotonic=time.monotonic(),
        )

    return {
        "app_down": app_down_source(settings, controller, client, which=which),
        "memory_cap": memory_cap_source(settings, which=which, runner=runner),
        "gpu_thermal": gpu_thermal_source(temperature, threshold),
        "budget_ceiling": budget_ceiling_source(costs),
        "breaker_open": breaker_open_source(settings, client),
    }


# --- The evaluator --------------------------------------------------------------------------------


class AlertEvaluator:
    """The evaluator thread: every source, every ``alerts.interval_seconds`` (ADR-0137 rule 7).

    Its own thread, not the job worker's, which spends hours inside one run. :meth:`evaluate_once`
    is one whole evaluation and is what tests drive, with no thread.

    Args:
        database: WeightRoomGym's own database.
        settings: The validated settings.
        sources: Source name to source.
        clock: The wall clock; the first window starts when the evaluator is built.
    """

    def __init__(
        self,
        database: Database,
        settings: Settings,
        sources: Mapping[str, Source],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Configure the evaluator without starting its thread."""
        self._database = database
        self._settings = settings
        self._sources = dict(sources)
        self._clock = clock
        self._since = clock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.problems: dict[str, str] = {}
        """Why each source could not be read at the last evaluation, for the Alerts page."""

    def evaluate_once(self) -> list[Reading]:
        """Read every source over the window since the last evaluation and write each reading."""
        now = self._clock()
        since, self._since = self._since, now
        readings: list[Reading] = []
        problems: dict[str, str] = {}
        for name, source in self._sources.items():
            try:
                reading = source(since, now)
            except Exception as exc:  # noqa: BLE001 — a crashing source covers nothing
                logger.warning("alerts.source_failed", extra={"source": name}, exc_info=True)
                reading = Reading(name, problem=f"{type(exc).__name__}: {exc}")
            if reading.problem:
                problems[name] = reading.problem
            try:
                apply(self._database, reading, now=now)
            except Exception:  # noqa: BLE001 — one failed write never stops the next source
                logger.exception("alerts.apply_failed", extra={"source": name})
            readings.append(reading)
        self.problems = problems
        return readings

    def _interval_seconds(self) -> float:
        from weightroom.services.settings import read_runtime_settings

        try:
            effective = read_runtime_settings(self._database, settings=self._settings)
            return float(effective["alerts.interval_seconds"])
        except Exception:  # noqa: BLE001 — an unreadable settings row falls back to the file
            return float(self._settings.alerts.interval_seconds)

    def _run(self) -> None:
        while not self._stop.wait(self._interval_seconds()):
            try:
                self.evaluate_once()
            except Exception:  # noqa: BLE001 — the evaluator outlives any one evaluation
                logger.exception("alerts.evaluation_failed")

    def start(self) -> None:
        """Start the thread; a second call does nothing."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="wr-gym-alerts", daemon=True)
        self._thread.start()

    def stop(self, *, timeout: float = 5.0) -> None:
        """Stop the thread and wait for it."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
