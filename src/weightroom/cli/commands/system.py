"""weightroom.cli.commands.system — serve, health, version.

Only ``typer`` and ``json`` load at module level (CLI standards §12).
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

__all__ = ["print_version", "version"]

API_VERSION = "v1"
SCHEMA_VERSION = "1"


def print_version(*, json_output: bool) -> None:
    """Print the version line, or the ``GET /version`` body as JSON."""
    from weightroom.__about__ import __version__

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "application": "weightroom",
                    "version": __version__,
                    "api_version": API_VERSION,
                    "schema_version": SCHEMA_VERSION,
                }
            )
        )
    else:
        typer.echo(f"wr-gym {__version__} (api {API_VERSION})")


def version(
    json_output: Annotated[
        bool, typer.Option("--json", help="Print JSON instead of a line.")
    ] = False,
) -> None:
    """Print the application and API versions. Mode: local."""
    print_version(json_output=json_output)
