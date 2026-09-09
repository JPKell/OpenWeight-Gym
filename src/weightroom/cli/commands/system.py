"""weightroom.cli.commands.system — serve, health, version.

Only ``typer`` and ``json`` load at module level (CLI standards §12).
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

__all__ = ["print_version", "serve", "version"]

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


def serve(
    host: Annotated[
        str | None, typer.Option(help="Bind host. Overrides configuration for this run.")
    ] = None,
    port: Annotated[
        int | None, typer.Option(help="Bind port. Overrides configuration for this run.")
    ] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
) -> None:
    """Start the HTTPS console and the plain-HTTP trust listener. Mode: local.

    Both listeners run in this process: uvicorn serves the console with the leaf certificate,
    and a second uvicorn server in a thread serves the two trust routes on ``server.trust_port``.
    The startup refusals (``INSECURE_BINDING``, ``TLS_MISSING``) exit 3 before either socket
    opens.
    """
    import os
    import threading

    import uvicorn
    from weightsdb import DatabaseError

    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.config import ConfigurationError
    from weightroom.services.runtime import prepare

    if config is not None:
        os.environ["WEIGHTROOM_CONFIG"] = config
    if host is not None:
        os.environ["WEIGHTROOM_SERVER__HOST"] = host
    if port is not None:
        os.environ["WEIGHTROOM_SERVER__PORT"] = str(port)

    loaded = load_settings_or_exit(None)
    try:
        runtime = prepare(loaded)
    except ConfigurationError as exc:
        raise fail(exc, exit_code=3) from exc
    except DatabaseError as exc:
        raise fail(exc) from exc

    settings = loaded.settings
    trust_server = uvicorn.Server(
        uvicorn.Config(
            "weightroom.bootstrap:create_trust_app_from_environment",
            factory=True,
            host=settings.server.host,
            port=settings.server.trust_port,
            log_config=None,
        )
    )
    trust_thread = threading.Thread(target=trust_server.run, name="trust-listener", daemon=True)
    trust_thread.start()
    typer.echo(
        f"console https://{settings.server.host}:{settings.server.port}  "
        f"trust http://{settings.server.host}:{settings.server.trust_port}/trust  "
        f"({runtime.tls.days_left} days left on the leaf)",
        err=True,
    )
    try:
        uvicorn.run(
            "weightroom.bootstrap:create_app_from_environment",
            factory=True,
            host=settings.server.host,
            port=settings.server.port,
            ssl_certfile=str(runtime.tls.paths.server_crt),
            ssl_keyfile=str(runtime.tls.paths.server_key),
            log_config=None,
        )
    finally:
        trust_server.should_exit = True
        trust_thread.join(timeout=5)
