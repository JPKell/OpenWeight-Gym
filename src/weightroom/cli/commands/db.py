"""weightroom.cli.commands.db — upgrade, status, backup, restore (local mode, CLI standards §6)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Annotated

import typer

__all__ = ["app"]

app = typer.Typer(help="Database migration and maintenance.")


@app.command("upgrade")
def upgrade(
    revision: Annotated[str, typer.Argument(help="Target revision.")] = "head",
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print JSON instead of text.")
    ] = False,
) -> None:
    """Migrate the database to REVISION. A no-op at the target revision (exit 0).

    Example:
        wr-gym db upgrade
    """
    from weightsdb import DatabaseError

    from weightroom.cli._backend import fail, open_database
    from weightroom.services.database import upgrade as upgrade_database

    with open_database(config) as (database, settings):
        try:
            outcome = upgrade_database(
                database, revision=revision, backup_retention=settings.storage.backup_retention
            )
        except DatabaseError as exc:
            raise fail(exc) from exc
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "from_revision": outcome.from_revision,
                    "to_revision": outcome.to_revision,
                    "backed_up": outcome.backed_up,
                    "backup_path": str(outcome.backup_path) if outcome.backup_path else None,
                }
            )
        )
        return
    if outcome.from_revision == outcome.to_revision:
        typer.echo(f"already at {outcome.to_revision}")
    else:
        typer.echo(f"migrated {outcome.from_revision or '(empty)'} -> {outcome.to_revision}")
    if outcome.backup_path:
        typer.echo(f"backup: {outcome.backup_path}")


@app.command("status")
def status(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print JSON instead of text.")
    ] = False,
) -> None:
    """Report the database's revision, row counts, size and integrity.

    Example:
        wr-gym db status --json
    """
    from weightsdb import DatabaseError

    from weightroom.cli._backend import fail, open_database
    from weightroom.services.database import get_status

    with open_database(config) as (database, _settings):
        try:
            report = get_status(database)
        except DatabaseError as exc:
            raise fail(exc) from exc
    if json_output:
        typer.echo(json.dumps(dataclasses.asdict(report)))
        return
    typer.echo(f"dialect:    {report.dialect}")
    typer.echo(
        f"revision:   {report.current_revision or '(unmigrated)'} (head {report.head_revision})"
    )
    typer.echo(f"size:       {report.size_bytes} B")
    typer.echo(f"integrity:  {'ok' if report.integrity_ok else report.integrity_detail}")
    for table, count in report.table_row_counts.items():
        typer.echo(f"  {table:<18} {count}")


@app.command("backup")
def backup(
    output: Annotated[
        str | None, typer.Option("--output", help="Destination file; default: an automatic name.")
    ] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
) -> None:
    """Take a consistent backup of the database.

    Example:
        wr-gym db backup
    """
    from weightsdb import DatabaseError

    from weightroom.cli._backend import fail, open_database
    from weightroom.services.database import backup_database

    with open_database(config) as (database, settings):
        try:
            result = backup_database(
                database,
                output=Path(output) if output else None,
                keep=settings.storage.backup_retention,
            )
        except DatabaseError as exc:
            raise fail(exc) from exc
    typer.echo(str(result.path))


@app.command("restore")
def restore(
    source: Annotated[str, typer.Argument(help="The backup file to restore from.")],
    confirm: Annotated[
        bool, typer.Option("--confirm", help="Required: this overwrites the current database.")
    ] = False,
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
) -> None:
    """Restore the database from SOURCE. Refuses without --confirm.

    Example:
        wr-gym db restore backups/manual-….sqlite3 --confirm
    """
    from weightsdb import DatabaseError

    from weightroom.cli._backend import fail, open_database
    from weightroom.services.database import restore_database

    if not confirm:
        typer.echo("Error: restore overwrites the database; pass --confirm.", err=True)
        raise typer.Exit(2)
    with open_database(config) as (database, _settings):
        try:
            result = restore_database(database, source=Path(source), confirm=True)
        except DatabaseError as exc:
            raise fail(exc) from exc
    typer.echo(f"restored from {result.source}")


@app.command("restore-self")
def restore_self(
    receipt: Annotated[
        str, typer.Option("--receipt", help="The receipt a self_restore job wrote.")
    ],
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
) -> None:
    """Stop the console, restore its database from a job's receipt, start it again (ADR-0136).

    Started by the transient unit a ``self_restore`` job launches, not by hand: it stops
    ``weightroom.service``, backs the live database up as ``pre-restore-<job>``, restores the
    receipt's file, migrates it, records the job in the restored database and starts the unit.
    Exit 5 when the restore failed and the database was put back.

    Example:
        wr-gym db restore-self --receipt ~/.local/share/wr-gym/restores/01M….json
    """
    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.services.processes import SubprocessSystemdController
    from weightroom.services.self_restore import SelfRestoreRefused, perform

    loaded = load_settings_or_exit(config)
    try:
        report = perform(
            Path(receipt), settings=loaded.settings, controller=SubprocessSystemdController()
        )
    except SelfRestoreRefused as exc:
        raise fail(exc, exit_code=2) from exc
    typer.echo(report.message)
    if not report.started:
        typer.echo("Error: weightroom.service did not start again.", err=True)
    if not report.ok:
        raise typer.Exit(5)
