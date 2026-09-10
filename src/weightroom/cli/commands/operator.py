"""weightroom.cli.commands.operator — create, password (ADR-0126 rules 4, 7).

The password is prompted twice and never taken from an argument, so it is in no shell history
and no process list. Both verbs write an audit row as actor ``cli``.
"""

from __future__ import annotations

from typing import Annotated

import typer

__all__ = ["app"]

app = typer.Typer(help="The operator account.")

_CONFIG = Annotated[str | None, typer.Option("--config", help="Path to a config.toml file.")]
_STDIN = Annotated[
    bool, typer.Option("--password-stdin", help="Read the password from stdin (scripts).")
]


def _read_password(*, from_stdin: bool) -> str:
    import sys

    if from_stdin:
        return sys.stdin.readline().rstrip("\n")
    return str(typer.prompt("Password", hide_input=True, confirmation_prompt=True))


@app.command("create")
def create(
    username: Annotated[str, typer.Argument(help="The operator's username.")],
    config: _CONFIG = None,
    password_stdin: _STDIN = False,
) -> None:
    """Create the one operator account; prompts for the password twice.

    Example:
        wr-gym operator create jordan
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import record_cli
    from weightroom.services.auth import create_operator
    from weightroom.services.tls import now_utc

    password = _read_password(from_stdin=password_stdin)
    with open_ready_database(config) as (database, _settings):
        try:
            create_operator(database, username=username, password=password, now=now_utc())
        except (SuiteError, ValueError) as exc:
            record_cli(
                database,
                action="operator.create",
                outcome="refused",
                target=username,
                message=str(getattr(exc, "message", exc)),
            )
            raise fail(exc, exit_code=2) from exc
        record_cli(database, action="operator.create", outcome="ok", target=username)
    typer.echo(f"operator {username!r} created")


@app.command("password")
def password(
    username: Annotated[str, typer.Argument(help="The operator's username.")],
    config: _CONFIG = None,
    password_stdin: _STDIN = False,
) -> None:
    """Reset the password and revoke every session (ADR-0126 rule 4).

    Example:
        wr-gym operator password jordan
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import record_cli
    from weightroom.services.auth import change_password
    from weightroom.services.tls import now_utc

    new_password = _read_password(from_stdin=password_stdin)
    with open_ready_database(config) as (database, _settings):
        try:
            revoked = change_password(
                database, username=username, password=new_password, now=now_utc()
            )
        except (SuiteError, ValueError) as exc:
            record_cli(
                database,
                action="operator.password",
                outcome="refused",
                target=username,
                message=str(getattr(exc, "message", exc)),
                security=True,
            )
            raise fail(exc, exit_code=2) from exc
        record_cli(
            database,
            action="operator.password",
            outcome="ok",
            target=username,
            params={"sessions_revoked": revoked},
            security=True,
        )
    typer.echo(f"password changed; {revoked} session(s) revoked")
