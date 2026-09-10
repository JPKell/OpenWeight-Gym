"""weightroom.cli.commands.alerts — list, ack (spec §7.2).

Local mode over WeightRoomGym's own database. The serving console's evaluator raises alerts; these
commands read them and acknowledge one, as one ``cli`` audit row.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from weightroom.services.alerts import AlertView

__all__ = ["app"]

app = typer.Typer(help="The alerts the console has raised.")

_CONFIG = Annotated[str | None, typer.Option("--config", help="Path to a config.toml file.")]
_JSON = Annotated[bool, typer.Option("--json", help="Print JSON instead of text.")]


def _line(alert: AlertView) -> str:
    return (
        f"{alert.opened_at.isoformat(timespec='seconds')}  {alert.id}  {alert.severity:<8} "
        f"{alert.state:<12} {alert.label} · {alert.subject}  {alert.summary}"
    ).rstrip()


@app.command("list")
def list_alerts(
    include_closed: Annotated[
        bool, typer.Option("--all", help="The newest alerts, closed ones too.")
    ] = False,
    limit: Annotated[int, typer.Option("--limit", help="How many alerts --all prints.")] = 50,
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """Print the active alerts, or with --all the newest ones.

    Example:
        wr-gym alerts list
    """
    from weightroom.cli._backend import open_ready_database
    from weightroom.services.alerts import active_alerts, recent_alerts

    with open_ready_database(config) as (database, _settings):
        rows = (
            recent_alerts(database, limit=max(1, limit))
            if include_closed
            else active_alerts(database)
        )
    if json_output:
        typer.echo(json.dumps([row.as_json() for row in rows]))
        return
    if not rows:
        typer.echo("no alerts" if include_closed else "no active alerts")
        return
    for row in rows:
        typer.echo(_line(row))


@app.command("ack")
def ack(
    alert_id: Annotated[str, typer.Argument(help="The alert's id.")],
    config: _CONFIG = None,
) -> None:
    """Acknowledge an alert: a memory-cap alert closes; a condition stays until it clears.

    Example:
        wr-gym alerts ack 01M…
    """
    import getpass
    from datetime import UTC, datetime

    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.alerts import acknowledge
    from weightroom.services.audit import record_cli

    with open_ready_database(config) as (database, _settings):
        try:
            view = acknowledge(
                database, alert_id, operator=f"cli:{getpass.getuser()}", now=datetime.now(UTC)
            )
        except SuiteError as exc:
            record_cli(
                database,
                action="alert.ack",
                outcome="refused",
                target=alert_id,
                message=exc.message,
            )
            raise fail(exc, exit_code=2) from exc
        record_cli(
            database,
            action="alert.ack",
            outcome="ok",
            target=alert_id,
            params={"source": view.source, "subject": view.subject},
        )
    typer.echo(f"{view.label} · {view.subject}: {view.state}")
