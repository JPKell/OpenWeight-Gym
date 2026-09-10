"""weightroom.cli.commands.audit — list, show."""

from __future__ import annotations

import json
from typing import Annotated

import typer

__all__ = ["app"]

app = typer.Typer(help="The audit trail.")

_CONFIG = Annotated[str | None, typer.Option("--config", help="Path to a config.toml file.")]
_JSON = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]


@app.command("list")
def list_rows(
    limit: Annotated[int, typer.Option("--limit", help="Rows to print, newest first.")] = 50,
    app_filter: Annotated[str | None, typer.Option("--app", help="Filter by application.")] = None,
    action: Annotated[str | None, typer.Option("--action", help="Filter by action.")] = None,
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """Print the newest rows of the trail.

    Example:
        wr-gym audit list --action login
    """
    from weightroom.cli._backend import open_ready_database
    from weightroom.services.audit import list_audit

    with open_ready_database(config) as (database, _settings):
        rows, _more = list_audit(database, limit=max(1, limit), app=app_filter, action=action)
    if json_output:
        typer.echo(json.dumps([row.as_json() for row in rows]))
        return
    for row in rows:
        who = row.operator or row.actor
        typer.echo(
            f"{row.at.isoformat(timespec='seconds')}  {row.id}  {who:<12} {row.action:<18} "
            f"{row.outcome:<8} {row.target or ''} {row.message or ''}".rstrip()
        )


@app.command("show")
def show(
    audit_id: Annotated[str, typer.Argument(help="The row's id.")],
    config: _CONFIG = None,
) -> None:
    """Print one row as JSON.

    Example:
        wr-gym audit show 01M2…
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import get_audit

    with open_ready_database(config) as (database, _settings):
        try:
            row = get_audit(database, audit_id)
        except SuiteError as exc:
            raise fail(exc, exit_code=2) from exc
    typer.echo(json.dumps(row.as_json(), indent=2))
