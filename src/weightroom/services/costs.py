"""weightroom.services.costs — LoadLedger balances for PromptCadence and IdeaPress (spec §7.9).

Only these two applications mount LoadLedger's tables (`ledger_*`, prefix `ledger_` both sides);
FreeWeight and LoadCoach carry no ledger at all. Reading is over the same read-only engine
``services/db_reader.py`` already opens for every application — a :class:`~loadledger.sql.SqlLedger`
bound to it, never a hand-written ``select`` (ADR-0016, ADR-0030, the kickoff's own words).

**Every debit touches its ``PER_DAY`` window regardless of what ceilings are configured**
(``BalanceBook.windows_touched`` — verified against a fixture database): a "today" balance answers
for an application that declares no daily ceiling at all, which is IdeaPress's case. Its own
ceilings (``per_output_*``, ``per_project_*``) are ``PER_RUN``/``PER_TAG``, scoped to one unit or
project — meaningless read app-wide with no run or project picked, and :meth:`Ledger.position`
refuses a ``PER_RUN`` ceiling outright (``InvalidCeiling``) for exactly that reason. So IdeaPress's
row shows today's totals with no ceiling verdict; PromptCadence's ``daily_money_ceiling`` is the one
ceiling this page evaluates app-wide, and its verdict is real.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from baseaicore import Money
from loadledger import BudgetCeiling, CeilingScope, CeilingVerdict, WindowBalance, utc_day_key
from loadledger.sql import SqlLedger
from sqlalchemy.orm import Session

from weightroom.services.db_reader import AppDatabaseUnavailable, open_app_database
from weightroom.services.processes import child_environment, executable_for, run_command

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from weightroom.config import Settings
    from weightroom.services.database import Database
    from weightroom.services.db_reader import DatabaseUrlCache
    from weightroom.services.processes import Runner

__all__ = ["COST_APPS", "AppCosts", "costs_for", "money_text"]

logger = logging.getLogger(__name__)

COST_APPS: Final[tuple[str, ...]] = ("promptcadence", "ideapress")
_CONFIG_SHOW_TIMEOUT_SECONDS: Final = 5.0


def _config_block(settings: Settings, app: str, *, runner: Runner) -> dict[str, Any] | None:
    """``<app> config show --json``'s effective values, or ``None`` — never raises (ADR-0127
    rule 4): a ceiling this build cannot read renders ``—``, not an error page."""
    executable = executable_for(settings, app)
    if executable is None:
        return None
    result = runner(
        [executable, "config", "show", "--json"], child_environment(), _CONFIG_SHOW_TIMEOUT_SECONDS
    )
    if not result.ok:
        return None
    try:
        body = json.loads(result.stdout)
        block = body.get("values") if "values" in body else body["settings"]
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return None
    return block if isinstance(block, dict) else None


def _money_ceiling(raw: object) -> Money | None:
    """A configured ``{currency, nanos}`` table to :class:`~baseaicore.Money`; zero nanos means
    the ceiling is unset (the same reading PromptCadence's own ``services/budget.py`` gives it)."""
    if not isinstance(raw, Mapping):
        return None
    nanos = raw.get("nanos")
    if not nanos:
        return None
    return Money(currency=str(raw.get("currency", "USD")), nanos=int(nanos))


def _promptcadence_ceilings(block: Mapping[str, Any]) -> tuple[BudgetCeiling, ...]:
    """The one ceiling this page evaluates app-wide: ``[budget] daily_money_ceiling``, ``PER_DAY``
    (spec §11.5 — deliberately money, never tokens)."""
    budget = block.get("budget")
    if not isinstance(budget, Mapping):
        return ()
    money = _money_ceiling(budget.get("daily_money_ceiling"))
    if money is None:
        return ()
    return (BudgetCeiling(scope=CeilingScope.PER_DAY, money=money),)


def _ideapress_ceilings(block: Mapping[str, Any]) -> tuple[BudgetCeiling, ...]:
    """None — IdeaPress's own ceilings are ``PER_RUN``/``PER_TAG`` on one output or project,
    unevaluable without picking one (module docstring)."""
    return ()


_CEILING_BUILDERS: Final[dict[str, Callable[[Mapping[str, Any]], tuple[BudgetCeiling, ...]]]] = {
    "promptcadence": _promptcadence_ceilings,
    "ideapress": _ideapress_ceilings,
}


def money_text(amount: Money) -> str:
    """``"$1.23 USD"``, the one place this module formats money for a template."""
    return f"{amount.to_decimal():.2f} {amount.currency}"


@dataclass(frozen=True, slots=True)
class AppCosts:
    """One application's costs, for one moment.

    Attributes:
        app: ``promptcadence`` or ``ideapress``.
        today: Today's ``PER_DAY`` window, or ``None`` when the database could not be read.
        verdicts: The app-wide ceilings' verdicts; empty when none apply (IdeaPress, always).
        unavailable: Why ``today`` is ``None``, or ``None`` when it answered.
    """

    app: str
    today: WindowBalance | None
    verdicts: tuple[CeilingVerdict, ...]
    unavailable: str | None

    def as_json(self) -> dict[str, Any]:
        """The api.md §5 ``GET /costs/{app}`` shape."""
        return {
            "app": self.app,
            "unavailable": self.unavailable,
            "today": None
            if self.today is None
            else {
                "window_key": self.today.window_key,
                "tokens_spent": self.today.tokens_spent,
                "money_spent": [
                    {"currency": m.currency, "text": money_text(m)} for m in self.today.money_spent
                ],
                "unpriced_debit_count": self.today.unpriced_debit_count,
                "untotalled_debit_count": self.today.untotalled_debit_count,
                "unmetered_debit_count": self.today.unmetered_debit_count,
            },
            "verdicts": [
                {
                    "scope": v.ceiling.scope.value,
                    "tag": v.ceiling.tag,
                    "exceeded": v.exceeded,
                    "money_spent": None if v.money_spent is None else money_text(v.money_spent),
                    "money_remaining": (
                        None if v.money_remaining is None else money_text(v.money_remaining)
                    ),
                    "tokens_spent": v.tokens_spent,
                    "tokens_remaining": v.tokens_remaining,
                    "unpriced_debit_count": v.unpriced_debit_count,
                }
                for v in self.verdicts
            ],
        }


def costs_for(
    settings: Settings,
    database: Database,
    app: str,
    *,
    urls: DatabaseUrlCache,
    now: datetime,
    monotonic: float,
    config_runner: Runner = run_command,
) -> AppCosts:
    """One application's :class:`AppCosts`, live.

    Args:
        settings: The validated settings.
        database: WeightRoomGym's own database, for the ``known_revisions`` check.
        app: One of :data:`COST_APPS`.
        urls: The effective-database-URL cache.
        now: The wall-clock instant — ``PER_DAY``'s window and the ledger's injected clock.
        monotonic: A monotonic reading, for the URL cache.
        config_runner: The process-launch boundary for ``config show``, injected.

    Returns:
        Never raises: an unreachable database or an unreadable configuration renders ``today`` and
        the verdicts empty, with ``unavailable`` naming why.
    """
    try:
        with open_app_database(
            settings, database, app, urls=urls, now=monotonic, require_known=False
        ) as handle:
            if not handle.revision.is_known:
                return AppCosts(
                    app,
                    None,
                    (),
                    f"{app}'s database is at a revision this console does not know "
                    f"({handle.revision.found!r}).",
                )
            engine = handle.engine

            def session_factory() -> Session:
                return Session(bind=engine)

            block = _config_block(settings, app, runner=config_runner) or {}
            ceilings = _CEILING_BUILDERS[app](block)
            ledger = SqlLedger(session_factory, ceilings, clock=lambda: now)
            today = ledger.balances(scope=CeilingScope.PER_DAY, window_key=utc_day_key(now))
            verdicts = ledger.position() if ceilings else ()
            return AppCosts(app, today, verdicts, None)
    except AppDatabaseUnavailable as exc:
        return AppCosts(app, None, (), exc.message)
