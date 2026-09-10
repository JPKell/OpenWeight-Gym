"""weightroom.cli.commands.tls — init, renew, rotate, show; and ``wr-gym trust``.

Local mode throughout (CLI standards §6). Only ``typer`` and ``json`` load at module level.
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

__all__ = ["app", "trust"]

app = typer.Typer(help="The certificate authority and the leaf (ADR-0126).")

_CONFIG = Annotated[str | None, typer.Option("--config", help="Path to a config.toml file.")]
_JSON = Annotated[bool, typer.Option("--json", help="Print JSON instead of text.")]


def _print_status(status: object, *, json_output: bool) -> None:
    from weightroom.services.tls import TlsStatus

    assert isinstance(status, TlsStatus)  # noqa: S101 — narrowing for mypy
    if json_output:
        typer.echo(json.dumps(status.as_json()))
        return
    typer.echo(f"directory        {status.paths.directory}")
    typer.echo(f"root             {status.ca_subject}")
    typer.echo(f"root sha256      {status.ca_fingerprint_sha256}")
    typer.echo(f"root expires     {status.ca_not_after.date().isoformat()}")
    typer.echo(f"leaf             {status.leaf_subject}")
    typer.echo(f"leaf sha256      {status.leaf_fingerprint_sha256}")
    typer.echo(
        f"leaf valid       {status.leaf_not_before.date().isoformat()} to "
        f"{status.leaf_not_after.date().isoformat()} ({status.days_left} days left)"
    )
    typer.echo(f"leaf names       {', '.join(sorted(status.leaf_names))}")


@app.command("init")
def init(config: _CONFIG = None, json_output: _JSON = False) -> None:
    """Create the root and the leaf under <config>/tls. Refuses when one already exists.

    Example:
        wr-gym tls init
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.services.tls import host_identity, init_tls, now_utc

    loaded = load_settings_or_exit(config)
    try:
        status = init_tls(loaded.settings, identity=host_identity(), now=now_utc())
    except SuiteError as exc:
        raise fail(exc, exit_code=2) from exc
    _print_status(status, json_output=json_output)


@app.command("renew")
def renew(config: _CONFIG = None, json_output: _JSON = False) -> None:
    """Reissue the leaf under the same root; no device needs re-trusting.

    Example:
        wr-gym tls renew
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.services.tls import host_identity, now_utc, renew_leaf

    loaded = load_settings_or_exit(config)
    try:
        status = renew_leaf(loaded.settings, identity=host_identity(), now=now_utc())
    except SuiteError as exc:
        raise fail(exc, exit_code=3) from exc
    _print_status(status, json_output=json_output)


@app.command("rotate")
def rotate(
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirm: replaces the root and revokes every session.")
    ] = False,
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """Replace the root and the leaf, revoke every session, print the re-trust steps.

    Example:
        wr-gym tls rotate --yes
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import record_cli
    from weightroom.services.auth import revoke_all_sessions
    from weightroom.services.tls import host_identity, now_utc, rotate_tls

    if not yes:
        typer.echo("Error: rotation replaces the root every device trusts; pass --yes.", err=True)
        raise typer.Exit(2)
    with open_ready_database(config) as (database, settings):
        try:
            status = rotate_tls(
                settings,
                identity=host_identity(),
                now=now_utc(),
                revoke_sessions=lambda: revoke_all_sessions(database),
            )
        except SuiteError as exc:
            record_cli(database, action="tls.rotate", outcome="failed", message=exc.message)
            raise fail(exc, exit_code=3) from exc
        record_cli(
            database,
            action="tls.rotate",
            outcome="ok",
            target=str(status.paths.directory),
            security=True,
        )
    _print_status(status, json_output=json_output)
    typer.echo("Every device must trust the new root: run `wr-gym trust`.")


@app.command("show")
def show(config: _CONFIG = None, json_output: _JSON = False) -> None:
    """Print the root's and the leaf's subjects, fingerprints, lifetimes and names.

    Example:
        wr-gym tls show
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.services.tls import TlsPaths, now_utc, tls_status

    loaded = load_settings_or_exit(config)
    try:
        status = tls_status(TlsPaths.for_settings(loaded.settings), now=now_utc())
    except SuiteError as exc:
        raise fail(exc, exit_code=3) from exc
    _print_status(status, json_output=json_output)


def trust(config: _CONFIG = None, json_output: _JSON = False) -> None:
    """Print the root's fingerprint, its file, both URLs and the per-OS trust steps.

    Verify the fingerprint on the device against this output before trusting anything
    (ADR-0126 rule 3).

    Example:
        wr-gym trust
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.services.tls import (
        TlsPaths,
        host_identity,
        now_utc,
        tls_status,
        trust_steps,
    )

    loaded = load_settings_or_exit(config)
    settings = loaded.settings
    try:
        status = tls_status(TlsPaths.for_settings(settings), now=now_utc())
    except SuiteError as exc:
        raise fail(exc, exit_code=3) from exc
    identity = host_identity()
    hosts = [f"{identity.hostname}.local", *identity.addresses]
    document = {
        "fingerprint_sha256": status.ca_fingerprint_sha256,
        "ca_file": str(status.paths.ca_crt),
        "trust_urls": [f"http://{h}:{settings.server.trust_port}/trust" for h in hosts],
        "root_urls": [f"http://{h}:{settings.server.trust_port}/root.crt" for h in hosts],
        "console_urls": [f"https://{h}:{settings.server.port}" for h in hosts],
        "steps": [{"platform": p, "text": t} for p, t in trust_steps(identity.hostname)],
    }
    if json_output:
        typer.echo(json.dumps(document))
        return
    typer.echo(f"root sha256   {document['fingerprint_sha256']}")
    typer.echo(f"root file     {document['ca_file']}")
    for url in document["trust_urls"]:
        typer.echo(f"trust page    {url}")
    for url in document["root_urls"]:
        typer.echo(f"root.crt      {url}")
    for url in document["console_urls"]:
        typer.echo(f"console       {url}")
    typer.echo("")
    for platform, text in trust_steps(identity.hostname):
        typer.echo(f"== {platform}")
        typer.echo(text)
        typer.echo("")
