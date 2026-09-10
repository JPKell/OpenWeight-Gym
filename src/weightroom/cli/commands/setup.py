"""weightroom.cli.commands.setup — the wizard (spec §7.2; development plan Phase 1).

Prompts for what the operator must decide — the username and password, the bind — and does the
rest from the host: the CA, ``allowed_hosts`` from the host's names and addresses, a token for
each installed application. Every answer has a flag so a script can run it unattended.
"""

from __future__ import annotations

from typing import Annotated

import typer

__all__ = ["setup"]


def setup(
    username: Annotated[
        str | None, typer.Option("--username", help="The operator's username (prompted if absent).")
    ] = None,
    password_stdin: Annotated[
        bool, typer.Option("--password-stdin", help="Read the password from stdin (scripts).")
    ] = False,
    bind: Annotated[
        str | None,
        typer.Option("--bind", help="loopback | lan | all (prompted if absent)."),
    ] = None,
    lan_address: Annotated[
        str | None, typer.Option("--lan-address", help="The interface for --bind lan.")
    ] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
) -> None:
    """The wizard: TLS, the operator account, allowed_hosts, the bind, the application tokens.

    Units and linger arrive at W2; the wizard says so at the end.

    Example:
        wr-gym setup
    """
    import sys

    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, load_settings_or_exit, open_loaded_database
    from weightroom.config import resolve_config_path
    from weightroom.services.audit import record_cli
    from weightroom.services.auth import operator_count
    from weightroom.services.database import ensure_ready
    from weightroom.services.setup import Bind, SetupAnswers, run_setup
    from weightroom.services.tls import host_identity, now_utc

    loaded = load_settings_or_exit(config)
    identity = host_identity()
    typer.echo(f"host {identity.hostname}  addresses {', '.join(identity.addresses) or '(none)'}")

    with open_loaded_database(loaded) as database:
        ensure_ready(
            database,
            auto_migrate=loaded.settings.storage.auto_migrate,
            backup_retention=loaded.settings.storage.backup_retention,
        )
        password: str | None = None
        if operator_count(database) == 0:
            if username is None:
                username = str(typer.prompt("Operator username"))
            if password_stdin:
                password = sys.stdin.readline().rstrip("\n")
            else:
                password = str(typer.prompt("Password", hide_input=True, confirmation_prompt=True))
        else:
            username = username or "(existing)"
            typer.echo("operator account exists; keeping it")

        if bind is None:
            typer.echo("Bind:  1) loopback only   2) one LAN interface   3) every interface")
            choice = str(typer.prompt("Choice", default="2"))
            bind = {"1": "loopback", "2": "lan", "3": "all"}.get(choice, "lan")
        choices: dict[str, Bind] = {"loopback": "loopback", "lan": "lan", "all": "all"}
        chosen = choices.get(bind)
        if chosen is None:
            typer.echo(f"Error: --bind must be loopback, lan or all, not {bind!r}", err=True)
            raise typer.Exit(2)
        if chosen == "lan" and lan_address is None:
            default = identity.addresses[0] if identity.addresses else ""
            lan_address = str(typer.prompt("LAN address", default=default))

        answers = SetupAnswers(
            username=username, password=password, bind=chosen, lan_address=lan_address
        )
        try:
            report, tls = run_setup(
                loaded.settings,
                config_path=resolve_config_path(config),
                database=database,
                answers=answers,
                identity=identity,
                now=now_utc(),
            )
        except (SuiteError, ValueError) as exc:
            record_cli(
                database,
                action="setup.run",
                outcome="failed",
                message=str(getattr(exc, "message", exc)),
                security=True,
            )
            raise fail(exc, exit_code=2) from exc
        record_cli(
            database, action="setup.run", outcome="ok", params=report.as_params(), security=True
        )

    typer.echo(f"tls        {report.tls}")
    typer.echo(f"           root sha256 {tls.ca_fingerprint_sha256}")
    typer.echo(f"account    {report.account}")
    typer.echo(f"bind       {report.bind}")
    typer.echo(f"hosts      {', '.join(report.allowed_hosts)}")
    for app, outcome in report.tokens.items():
        typer.echo(f"token      {app}: {outcome}")
    typer.echo(f"config     {report.config_path}")
    for item in report.deferred:
        typer.echo(f"later      {item}")
    typer.echo("next       wr-gym serve; then `wr-gym trust` for the per-device steps")
