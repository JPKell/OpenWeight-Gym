"""weightroom.cli.commands.units — ``sync``, ``status``, ``start``, ``stop``, ``restart``.

Spec §7.2. Every verb that changes something writes an ``audit_log`` row with actor ``cli``
(spec §11 contract 2); ``status`` changes nothing and writes none.
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

__all__ = ["app"]

app = typer.Typer(help="The systemd --user units for the five applications.")

_CONFIG = Annotated[str | None, typer.Option("--config", help="Path to a config.toml file.")]
_JSON = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]

_TARGET_HELP = "One of freeweight, loadcoach, ideapress, promptcadence, weightroom — or all."


def _targets(target: str) -> list[str]:
    from weightroom.domain.units import UNIT_APPLICATIONS

    if target == "all":
        return list(UNIT_APPLICATIONS)
    if target not in UNIT_APPLICATIONS:
        typer.echo(
            f"Error: {target!r} is not an application; {_TARGET_HELP.lower()}",
            err=True,
        )
        raise typer.Exit(2)
    return [target]


@app.command("sync")
def sync(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Report what would change; write nothing.")
    ] = False,
    show_diff: Annotated[
        bool, typer.Option("--diff", help="Print the unified diff for each changed unit.")
    ] = False,
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """Write the five units, regenerating each one whole (ADR-0125 rule 1).

    A hand edit is overwritten; ``--diff`` shows exactly what is being replaced. Idempotent: a
    second run writes nothing and does not reload systemd.

    Example:
        wr-gym units sync --diff
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import record_cli
    from weightroom.services.processes import SubprocessSystemdController, sync_units

    with open_ready_database(config) as (database, settings):
        try:
            report = sync_units(settings, controller=SubprocessSystemdController(), dry_run=dry_run)
        except SuiteError as exc:
            record_cli(database, action="unit.sync", outcome="failed", message=exc.message)
            raise fail(exc, exit_code=2) from exc
        if not dry_run:
            record_cli(database, action="unit.sync", outcome="ok", params=report.as_params())

    if json_output:
        typer.echo(json.dumps(report.as_params(), indent=2))
        return
    typer.echo(f"units     {report.directory}")
    for plan in report.plans:
        label = {
            "written": "would write" if dry_run else "written",
            "unchanged": "unchanged",
            "not_installed": "not installed; no unit",
        }[plan.outcome]
        typer.echo(f"{plan.app:<14} {label}")
        if show_diff and plan.diff:
            for line in plan.diff:
                typer.echo(f"  {line}")
    typer.echo(
        "reload    systemd reloaded"
        if report.reloaded
        else "reload    not needed"
        if not report.written
        else "reload    skipped (--dry-run)"
    )


@app.command("status")
def status(config: _CONFIG = None, json_output: _JSON = False) -> None:
    """Print each unit's state, uptime and restart count.

    Example:
        wr-gym units status
    """
    from baseaicore import SuiteError
    from mirrorwall import duration_human

    from weightroom.cli._backend import fail, load_settings_or_exit
    from weightroom.domain.units import UNIT_APPLICATIONS, unit_name
    from weightroom.services.processes import SubprocessSystemdController

    loaded = load_settings_or_exit(config)
    del loaded  # the units are named by the application, not by configuration
    controller = SubprocessSystemdController()
    units = [unit_name(name) for name in UNIT_APPLICATIONS]
    try:
        states = controller.show(units)
    except SuiteError as exc:
        raise fail(exc, exit_code=2) from exc
    if json_output:
        typer.echo(
            json.dumps(
                {
                    unit: {
                        "state": item.state,
                        "sub_state": item.sub_state,
                        "uptime_seconds": item.uptime_seconds,
                        "main_pid": item.main_pid,
                        "restarts": item.restarts,
                    }
                    for unit, item in states.items()
                },
                indent=2,
            )
        )
        return
    for unit in units:
        item = states[unit]
        uptime = duration_human(item.uptime_seconds) if item.uptime_seconds is not None else "—"
        restarts = "—" if item.restarts is None else str(item.restarts)
        typer.echo(f"{unit:<24} {item.state:<12} up {uptime:<12} restarts {restarts}")


def _control(verb: str, target: str, config: str | None) -> None:
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.domain.units import unit_name
    from weightroom.services.audit import record_cli
    from weightroom.services.processes import SubprocessSystemdController, act_and_settle

    controller = SubprocessSystemdController()
    failures = 0
    with open_ready_database(config) as (database, _settings):
        for name in _targets(target):
            unit = unit_name(name)
            try:
                report = act_and_settle(controller, unit, verb)
            except SuiteError as exc:
                record_cli(
                    database,
                    action=f"unit.{verb}",
                    outcome="failed",
                    target=unit,
                    message=exc.message,
                )
                raise fail(exc, exit_code=2) from exc
            # A verb `systemctl` took too long to answer is judged by the state the unit reached,
            # not by the timeout (row WPF4).
            record_cli(
                database,
                action=f"unit.{verb}",
                outcome=report.outcome,
                target=unit,
                message=report.note,
            )
            if report.outcome == "ok":
                note = "" if report.note is None else f" ({report.note})"
                typer.echo(f"{unit:<24} {verb}ed{note}")
            elif report.outcome == "pending":
                typer.echo(f"{unit:<24} {verb} not settled: {report.note}", err=True)
            else:
                failures += 1
                typer.echo(f"{unit:<24} {verb} failed: {report.note}", err=True)
    if failures:
        raise typer.Exit(4)


@app.command("start")
def start(
    target: Annotated[str, typer.Argument(help=_TARGET_HELP)],
    config: _CONFIG = None,
) -> None:
    """Start one application's unit, or every one.

    Example:
        wr-gym units start loadcoach
    """
    _control("start", target, config)


@app.command("stop")
def stop(
    target: Annotated[str, typer.Argument(help=_TARGET_HELP)],
    config: _CONFIG = None,
) -> None:
    """Stop one application's unit, or every one.

    Example:
        wr-gym units stop all
    """
    _control("stop", target, config)


@app.command("restart")
def restart(
    target: Annotated[str, typer.Argument(help=_TARGET_HELP)],
    config: _CONFIG = None,
) -> None:
    """Restart one application's unit, or every one.

    Example:
        wr-gym units restart promptcadence
    """
    _control("restart", target, config)
