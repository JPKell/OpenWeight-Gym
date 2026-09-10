"""weightroom.cli.commands.apps — ``wr-gym apps status`` and ``wr-gym logs`` (spec §7.2).

Both are read-only and write no audit row. ``apps status`` is the one table an operator wants
from a terminal: the four applications and Ollama, their units, their versions and whether the
console speaks to them.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from weightroom.services.journal import JournalReader

__all__ = ["app", "logs", "status"]

app = typer.Typer(help="The four applications, from the terminal.")

_CONFIG = Annotated[str | None, typer.Option("--config", help="Path to a config.toml file.")]
_JSON = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]


@app.command("status")
def status(config: _CONFIG = None, json_output: _JSON = False) -> None:
    """The four applications and Ollama in one table.

    Example:
        wr-gym apps status
    """
    import httpx
    from mirrorwall import duration_human

    from weightroom.cli._backend import load_settings_or_exit
    from weightroom.services.apps import VersionCache, inventory
    from weightroom.services.journal import JournalReader
    from weightroom.services.ollama import ollama_client, ollama_report
    from weightroom.services.processes import SubprocessSystemdController

    loaded = load_settings_or_exit(config)
    controller = SubprocessSystemdController()
    with httpx.Client(trust_env=False) as client:
        views = inventory(
            loaded.settings,
            controller=controller,
            cache=VersionCache(),
            client=client,
            now=time.monotonic(),
        )
        with ollama_client(loaded.settings) as ollama_transport:
            ollama = ollama_report(
                loaded.settings,
                controller=controller,
                client=ollama_transport,
                journal=JournalReader(),
            )
    if json_output:
        typer.echo(
            json.dumps(
                {"apps": [view.as_json() for view in views], "ollama": ollama.as_json()}, indent=2
            )
        )
        return
    header = f"{'application':<16}{'state':<18}{'uptime':<12}{'version':<12}unit"
    typer.echo(header)
    for view in views:
        uptime = duration_human(view.uptime_seconds)
        typer.echo(
            f"{view.name:<16}{view.pill:<18}{uptime:<12}{view.version or '—':<12}{view.unit}"
        )
    checks = f"{ollama.passing}/{ollama.total} memory-safety checks"
    typer.echo(f"{'ollama':<16}{ollama.state:<18}{'—':<12}{'—':<12}{ollama.unit}  {checks}")
    if not ollama.safe and ollama.state != "unsupported":
        typer.echo(f"                 fix: {ollama.apply_script}")


def logs(
    target: Annotated[
        str,
        typer.Argument(
            help="freeweight | loadcoach | ideapress | promptcadence | weightroom | all"
        ),
    ] = "all",
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Tail the journal live.")] = False,
    since: Annotated[
        str | None, typer.Option("--since", help="journalctl --since, e.g. '-1h'.")
    ] = None,
    until: Annotated[str | None, typer.Option("--until", help="journalctl --until.")] = None,
    level: Annotated[
        str | None, typer.Option("--level", help="err | warning | info … and more severe.")
    ] = None,
    query: Annotated[
        str | None, typer.Option("--grep", help="Literal text to match (never a regex).")
    ] = None,
    lines: Annotated[int, typer.Option("--lines", "-n", help="How many lines.")] = 200,
    json_output: _JSON = False,
    config: _CONFIG = None,
) -> None:
    """Print an application's journal, or every unit's at once. Mode: local.

    Example:
        wr-gym logs loadcoach --follow
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.domain.units import UNIT_APPLICATIONS, unit_name
    from weightroom.services.journal import JournalReader

    load_settings_or_exit(config)
    names = list(UNIT_APPLICATIONS) if target == "all" else [target]
    for name in names:
        if name not in UNIT_APPLICATIONS:
            typer.echo(
                f"Error: {name!r} has no unit; try one of {', '.join(UNIT_APPLICATIONS)}", err=True
            )
            raise typer.Exit(2)
    units = [unit_name(name) for name in names]
    reader = JournalReader()
    try:
        if follow:
            _follow(reader, units, backfill=lines, json_output=json_output)
            return
        page = reader.history(
            units, since=since, until=until, level=level, query=query, limit=lines
        )
    except SuiteError as exc:
        raise fail(exc, exit_code=2) from exc
    if json_output:
        typer.echo(json.dumps(page.as_json(), indent=2))
        return
    for line in reversed(page.lines):  # newest first on the wire; oldest first in a terminal
        typer.echo(f"{line.at.isoformat(timespec='seconds')}  {line.app:<14} {line.message}")
    if page.next_cursor:
        typer.echo(
            f"… more; --since or --lines to widen (cursor {page.next_cursor[:24]}…)", err=True
        )


def _follow(reader: JournalReader, units: list[str], *, backfill: int, json_output: bool) -> None:
    """Tail until interrupted; Ctrl-C ends the block and the reader is stopped on the way out."""
    import contextlib

    with contextlib.suppress(KeyboardInterrupt), reader.follow(units, backfill=backfill) as stream:
        while True:
            event = stream.poll()
            if event is None:
                time.sleep(0.05)
                continue
            if event.type == "log.closed":
                return
            payload = dict(event.payload)
            if json_output:
                typer.echo(json.dumps(payload))
            else:
                typer.echo(f"{payload['at']}  {payload['app']:<14} {payload['message']}")
