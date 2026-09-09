"""weightroom.cli.main — the Typer root app for ``wr-gym``.

Only ``typer`` and the lightweight command modules load at import time; every heavier
dependency stays behind a lazy import inside the command bodies (CLI Standards §12), so
``--help`` never imports FastAPI, SQLAlchemy, httpx or cryptography.
"""

from __future__ import annotations

from typing import Annotated

import typer

from weightroom.cli.commands import config as config_commands
from weightroom.cli.commands import db as db_commands
from weightroom.cli.commands import system as system_commands
from weightroom.cli.commands import tls as tls_commands

__all__ = ["app"]

app = typer.Typer(
    name="wr-gym",
    help="WeightRoomGym — the host operator's console over the four applications.",
    no_args_is_help=False,
    add_completion=True,
)


def _eager_version(show: bool) -> None:
    if not show:
        return
    system_commands.print_version(json_output=False)
    raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version", is_eager=True, callback=_eager_version, help="Show the version and exit."
        ),
    ] = False,
) -> None:
    """wr-gym — the host operator's console over the four applications."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(system_commands.serve)


app.command(name="serve", help="Start the HTTPS console (also the default with no subcommand).")(
    system_commands.serve
)
app.command(name="version", help="Print the application and API versions.")(system_commands.version)
app.command(name="trust", help="Print the root's fingerprint, paths, URLs and trust steps.")(
    tls_commands.trust
)
app.add_typer(config_commands.app, name="config", help="Configuration inspection and management.")
app.add_typer(db_commands.app, name="db", help="Database migration and maintenance.")
app.add_typer(tls_commands.app, name="tls", help="The certificate authority and the leaf.")
