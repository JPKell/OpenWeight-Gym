"""services/costs.py: today's LoadLedger balance and PromptCadence's daily ceiling verdict.

Debits go in through a real ``SqlLedger`` against a copy of the committed fixture database, the
same instrument PromptCadence and IdeaPress themselves use — never a hand-written ``INSERT`` into
``ledger_*``, whose shape belongs to ``loadledger.sql`` and not to this test.
"""

from __future__ import annotations

import json as jsonlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from baseaicore import CostEstimate, Money, PricingSource, TokenUsage
from loadledger import Debit
from loadledger.sql import SqlLedger
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from tests.support import fixture_database
from weightroom.config import Settings, load_settings
from weightroom.services.costs import costs_for
from weightroom.services.database import Database, ensure_ready
from weightroom.services.db_reader import DatabaseUrlCache

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _own(tmp_path: Path) -> Database:
    database = Database.from_url(f"sqlite:///{tmp_path / 'weightroom.sqlite3'}")
    ensure_ready(database, auto_migrate=True)
    return database


def _executable(tmp_path: Path, app: str, *, database_url: str, values: dict[str, Any]) -> Path:
    """A shell script answering ``config show --json`` with exactly ``values`` — the fixture
    schema is silent on ``[budget]``, so this test builds its own rather than stretch it."""
    directory = tmp_path / app
    directory.mkdir(parents=True, exist_ok=True)
    show_file = directory / "show.json"
    show_file.write_text(
        jsonlib.dumps({"values": {"storage": {"database_url": database_url}, **values}}),
        encoding="utf-8",
    )
    executable = directory / app
    executable.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "config" ] && [ "$2" = "show" ]; then cat {show_file}; exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def _settings(
    tmp_path: Path, app: str, *, database_url: str, budget: dict[str, Any] | None = None
) -> Settings:
    executable = _executable(
        tmp_path, app, database_url=database_url, values={"budget": budget} if budget else {}
    )
    console = tmp_path / "console.toml"
    console.write_text(f'[apps.{app}]\nexecutable = "{executable}"\n', encoding="utf-8")
    return load_settings(config_path=console).settings


def _debit(engine: Engine, *, run_id: str, cost: CostEstimate | None) -> None:
    ledger = SqlLedger(lambda: Session(bind=engine), (), clock=lambda: NOW)
    ledger.debit(
        Debit(
            run_id=run_id,
            source_ref="turn-1",
            usage=TokenUsage(input_tokens=1000, output_tokens=500),
            cost=cost,
        )
    )


def test_a_database_with_nothing_debited_today_reports_an_honest_zero(tmp_path: Path) -> None:
    db_path = fixture_database(tmp_path, "ideapress-0010")
    settings = _settings(tmp_path, "ideapress", database_url=f"sqlite:///{db_path}")
    result = costs_for(
        settings, _own(tmp_path), "ideapress", urls=DatabaseUrlCache(), now=NOW, monotonic=0.0
    )
    assert result.unavailable is None
    assert result.today is not None
    assert result.today.tokens_spent == 0
    assert result.today.money_spent == ()
    assert result.verdicts == ()  # IdeaPress has no app-wide ceiling (module docstring)


def test_ideapress_has_no_daily_ceiling_but_still_counts_todays_unpriced_debit(
    tmp_path: Path,
) -> None:
    db_path = fixture_database(tmp_path, "ideapress-0010")
    engine = create_engine(f"sqlite:///{db_path}")
    _debit(engine, run_id="unit-1", cost=None)
    engine.dispose()
    settings = _settings(tmp_path, "ideapress", database_url=f"sqlite:///{db_path}")
    result = costs_for(
        settings, _own(tmp_path), "ideapress", urls=DatabaseUrlCache(), now=NOW, monotonic=0.0
    )
    assert result.today is not None
    assert result.today.tokens_spent == 1500
    assert result.today.unpriced_debit_count == 1
    assert result.verdicts == ()


def test_promptcadence_today_reads_the_priced_debit_and_the_daily_ceiling_verdict(
    tmp_path: Path,
) -> None:
    db_path = fixture_database(tmp_path, "promptcadence-0011")
    engine = create_engine(f"sqlite:///{db_path}")
    priced = CostEstimate(
        currency="USD",
        total=Money(currency="USD", nanos=1_000_000_000),
        input_cost=Money(currency="USD", nanos=700_000_000),
        output_cost=Money(currency="USD", nanos=300_000_000),
        cache_write_cost=Money.zero("USD"),
        cache_read_cost=Money.zero("USD"),
        pricing_hash="hash1",
        pricing_source=PricingSource.CATALOG,
        priced_at=NOW,
    )
    _debit(engine, run_id="trajectory-1", cost=priced)
    engine.dispose()
    settings = _settings(
        tmp_path,
        "promptcadence",
        database_url=f"sqlite:///{db_path}",
        budget={"daily_money_ceiling": {"currency": "USD", "nanos": 5_000_000_000}},
    )
    result = costs_for(
        settings, _own(tmp_path), "promptcadence", urls=DatabaseUrlCache(), now=NOW, monotonic=0.0
    )
    assert result.today is not None
    assert result.today.tokens_spent == 1500
    assert len(result.today.money_spent) == 1
    assert result.today.money_spent[0].nanos == 1_000_000_000
    assert len(result.verdicts) == 1
    verdict = result.verdicts[0]
    assert verdict.exceeded is False
    assert verdict.money_spent is not None
    assert verdict.money_spent.nanos == 1_000_000_000
    assert verdict.money_remaining is not None
    assert verdict.money_remaining.nanos == 4_000_000_000


def test_a_zero_configured_ceiling_means_no_ceiling_here(tmp_path: Path) -> None:
    """``services/budget.py`` treats ``nanos = 0`` as unset — this module reads it the same way."""
    db_path = fixture_database(tmp_path, "promptcadence-0011")
    settings = _settings(
        tmp_path,
        "promptcadence",
        database_url=f"sqlite:///{db_path}",
        budget={"daily_money_ceiling": {"currency": "USD", "nanos": 0}},
    )
    result = costs_for(
        settings, _own(tmp_path), "promptcadence", urls=DatabaseUrlCache(), now=NOW, monotonic=0.0
    )
    assert result.verdicts == ()


def test_an_unreachable_database_reports_why_instead_of_raising(tmp_path: Path) -> None:
    settings = _settings(tmp_path, "promptcadence", database_url="sqlite:////no/such/file.sqlite3")
    result = costs_for(
        settings,
        _own(tmp_path),
        "promptcadence",
        urls=DatabaseUrlCache(),
        now=NOW,
        monotonic=0.0,
    )
    assert result.today is None
    assert result.unavailable is not None
