"""``wr-gym alerts list|ack`` through Typer's runner, off the real host."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from weightroom.cli.main import app
from weightroom.domain.alerts import Firing, Reading
from weightroom.services.alerts import active_alerts, apply
from weightroom.services.database import Database

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def _run(*args: str) -> tuple[int, str, str]:
    result = runner.invoke(app, list(args), catch_exceptions=False)
    return result.exit_code, result.stdout, result.stderr


def test_alerts_are_listed_and_acknowledged_from_the_terminal(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(f'[storage]\ndatabase_url = "sqlite:///{tmp_path}/db.sqlite3"\n')
    assert _run("alerts", "list", "--config", str(config)) == (0, "no active alerts\n", "")
    with Database.from_url(f"sqlite:///{tmp_path}/db.sqlite3") as database:
        hot = Firing("gpu0", {"temperature_c": 90.0, "threshold_c": 85.0})
        apply(
            database,
            Reading("gpu_thermal", (hot,), frozenset({"gpu0"})),
            now=datetime.now(UTC),
        )
        alert_id = active_alerts(database)[0].id

    code, out, _ = _run("alerts", "list", "--config", str(config))
    assert code == 0
    assert "GPU over its temperature threshold · gpu0" in out
    assert "90.0 °C" in out
    code, out, _ = _run("alerts", "ack", alert_id, "--config", str(config))
    assert code == 0
    assert out.strip().endswith("acknowledged")
    assert _run("alerts", "ack", "01NOSUCHALERT0000000000000", "--config", str(config))[0] == 2
    code, out, _ = _run("alerts", "list", "--all", "--json", "--config", str(config))
    assert json.loads(out)[0]["acknowledged_by"].startswith("cli:")
    code, out, _ = _run("audit", "list", "--json", "--config", str(config))
    outcomes = [row["outcome"] for row in json.loads(out) if row["action"] == "alert.ack"]
    assert sorted(outcomes) == ["ok", "refused"]
