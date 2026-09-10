"""weightroom.cli.commands.jobs — list, show, run, cancel, schedule (spec §7.2).

Local mode over WeightRoomGym's own database. ``run`` queues; the serving console's worker executes
(``wr-gym serve``), and ``--wait`` follows the job to its end. Each change is one ``cli`` audit row.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:
    from weightroom.services.jobs import JobView, ScheduleView

__all__ = ["app"]

app = typer.Typer(help="WeightRoomGym's own job queue and its schedules.")

_CONFIG = Annotated[str | None, typer.Option("--config", help="Path to a config.toml file.")]
_JSON = Annotated[bool, typer.Option("--json", help="Print JSON instead of text.")]
_PARAM = Annotated[
    list[str] | None,
    typer.Option(
        "--param", help="One parameter as key=value; a JSON value is decoded. Repeatable."
    ),
]

_EXIT_BY_STATE: dict[str, int] = {"completed": 0, "failed": 5, "cancelled": 6}


def _params(pairs: list[str] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pair in pairs or []:
        key, separator, raw = pair.partition("=")
        if not separator or not key.strip():
            typer.echo(f"Error: --param {pair!r} is not key=value (VALIDATION_ERROR)", err=True)
            raise typer.Exit(2)
        try:
            value: Any = json.loads(raw)
        except ValueError:
            value = raw
        out[key.strip()] = value
    return out


def _job_line(job: JobView) -> str:
    return (
        f"{job.queued_at.isoformat(timespec='seconds')}  {job.id}  {job.kind:<22} "
        f"{job.state:<10} {job.error or ''}"
    ).rstrip()


def _schedule_line(schedule: ScheduleView) -> str:
    state = "enabled" if schedule.enabled else "disabled"
    upcoming = schedule.next_run_at.isoformat(timespec="minutes") if schedule.next_run_at else "—"
    return f"{schedule.id}  {schedule.kind:<22} {schedule.cron:<16} {state:<9} next {upcoming}"


@app.command("list")
def list_command(
    state: Annotated[str | None, typer.Option("--state", help="Only jobs in this state.")] = None,
    kind: Annotated[str | None, typer.Option("--kind", help="Only jobs of this kind.")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Jobs to print, newest first.")] = 50,
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """Print the newest jobs.

    Example:
        wr-gym jobs list --state running
    """
    from weightroom.cli._backend import open_ready_database
    from weightroom.services.jobs import list_jobs

    with open_ready_database(config) as (database, _settings):
        rows, _more = list_jobs(database, limit=max(1, limit), state=state, kind=kind)
    if json_output:
        typer.echo(json.dumps([row.as_json() for row in rows]))
        return
    for row in rows:
        typer.echo(_job_line(row))


@app.command("show")
def show(
    job_id: Annotated[str, typer.Argument(help="The job's id.")],
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """Print one job, its parameters and its captured output.

    Example:
        wr-gym jobs show 01M…
    """
    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.jobs import get_job

    with open_ready_database(config) as (database, _settings):
        try:
            job = get_job(database, job_id)
        except SuiteError as exc:
            raise fail(exc, exit_code=2) from exc
    if json_output:
        typer.echo(json.dumps(job.as_json(), indent=2))
        return
    typer.echo(_job_line(job))
    typer.echo(f"params: {json.dumps(job.params, sort_keys=True)}")
    if job.output:
        typer.echo(job.output.rstrip())


@app.command("run")
def run(
    kind: Annotated[str, typer.Argument(help="The job kind, e.g. backup or docs_index.")],
    param: _PARAM = None,
    wait: Annotated[
        bool, typer.Option("--wait", help="Follow the job to its end; the exit code says how.")
    ] = False,
    timeout: Annotated[
        float, typer.Option("--timeout", help="Seconds --wait follows before exiting 4.")
    ] = 3600.0,
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """Queue a job for the serving console's worker.

    With ``--wait``, exit 0 completed, 5 failed, 6 cancelled, 4 still running at the timeout.

    Example:
        wr-gym jobs run backup --param 'apps=["loadcoach"]' --wait
    """
    import time
    from datetime import UTC, datetime

    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import record_cli
    from weightroom.services.jobs import enqueue, get_job

    params = _params(param)
    with open_ready_database(config) as (database, _settings):
        try:
            job = enqueue(database, kind=kind, params=params, now=datetime.now(UTC))
        except SuiteError as exc:
            record_cli(
                database,
                action="job.enqueue",
                outcome="refused",
                target=kind,
                params={"kind": kind, "params": params},
                message=exc.message,
            )
            raise fail(exc, exit_code=2) from exc
        record_cli(
            database,
            action="job.enqueue",
            outcome="ok",
            target=job.id,
            params={"kind": job.kind, "params": job.params},
        )
        if not wait:
            typer.echo(
                json.dumps(job.as_json())
                if json_output
                else f"queued {job.id}; the serving console's worker runs it"
            )
            return
        deadline = time.monotonic() + timeout
        while not job.finished:
            if time.monotonic() >= deadline:
                typer.echo(f"Job {job.id} is still {job.state} after {timeout:g}s.", err=True)
                raise typer.Exit(4)
            time.sleep(1.0)
            job = get_job(database, job.id)
    typer.echo(json.dumps(job.as_json()) if json_output else _job_line(job))
    raise typer.Exit(_EXIT_BY_STATE.get(job.state, 5))


@app.command("cancel")
def cancel(
    job_id: Annotated[str, typer.Argument(help="The job's id.")],
    config: _CONFIG = None,
) -> None:
    """Cancel a queued job, or ask a running one to stop. Exit 2 for a finished one.

    Example:
        wr-gym jobs cancel 01M…
    """
    from datetime import UTC, datetime

    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import record_cli
    from weightroom.services.jobs import request_cancel

    with open_ready_database(config) as (database, _settings):
        try:
            job = request_cancel(database, job_id, now=datetime.now(UTC))
        except SuiteError as exc:
            record_cli(
                database, action="job.cancel", outcome="refused", target=job_id, message=exc.message
            )
            raise fail(exc, exit_code=2) from exc
        record_cli(database, action="job.cancel", outcome="ok", target=job_id)
    typer.echo(_job_line(job) + ("  (cancel requested)" if job.state == "running" else ""))


@app.command("schedule")
def schedule(
    schedule_id: Annotated[
        str | None, typer.Argument(help="A schedule's id; leave it out to list them.")
    ] = None,
    cron: Annotated[
        str | None, typer.Option("--cron", help="A five-field cron expression, in UTC.")
    ] = None,
    enable: Annotated[
        bool | None, typer.Option("--enable/--disable", help="Switch the schedule on or off.")
    ] = None,
    param: _PARAM = None,
    config: _CONFIG = None,
    json_output: _JSON = False,
) -> None:
    """List the schedules, or change one; a --param is merged into its parameters.

    Example:
        wr-gym jobs schedule 01M… --param model=ollama/qwen3:8b --enable
    """
    from datetime import UTC, datetime

    from baseaicore import SuiteError

    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.audit import record_cli
    from weightroom.services.jobs import get_schedule, list_schedules, update_schedule

    with open_ready_database(config) as (database, _settings):
        if schedule_id is None:
            rows = list_schedules(database)
            if json_output:
                typer.echo(json.dumps([row.as_json() for row in rows]))
            else:
                for row in rows:
                    typer.echo(_schedule_line(row))
            return
        try:
            current = get_schedule(database, schedule_id)
            params = {**current.params, **_params(param)} if param else None
            view = update_schedule(
                database,
                schedule_id,
                now=datetime.now(UTC),
                cron=cron,
                enabled=enable,
                params=params,
            )
        except SuiteError as exc:
            record_cli(
                database,
                action="job.schedule",
                outcome="refused",
                target=schedule_id,
                params={"cron": cron, "enabled": enable},
                message=exc.message,
            )
            raise fail(exc, exit_code=2) from exc
        record_cli(
            database,
            action="job.schedule",
            outcome="ok",
            target=schedule_id,
            params={"cron": view.cron, "enabled": view.enabled, "params": view.params},
        )
    typer.echo(json.dumps(view.as_json()) if json_output else _schedule_line(view))
