"""weightroom.cli.commands.doctor — ``wr-gym doctor``.

The same rules the Doctor page runs, printed. Every fix is printed and never run: the ones that
matter most edit a file under ``/etc``, and this command is not root (ADR-0125 rules 4–5).

Exit codes follow CLI standards §4 as a **health** verb does: ``0`` when nothing failed and
nothing warned, ``1`` when something did. A notice is not a failure — Ollama on ``0.0.0.0`` is
the operator's own choice (``LAN_ACCESS.md`` §5) and must not make a scripted check red.
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

__all__ = ["doctor"]

_MARKS = {"ok": "ok  ", "notice": "note", "unknown": "?   ", "warning": "WARN", "failure": "FAIL"}


def doctor(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print the findings as JSON.")
    ] = False,
    all_findings: Annotated[
        bool, typer.Option("--all", help="Print the rules that pass as well.")
    ] = False,
) -> None:
    """Diagnose this host against the suite's own documents. Mode: local. Exit 1 on a problem."""
    from datetime import UTC, datetime

    import httpx

    from weightroom.cli._backend import load_settings_or_exit, open_loaded_database
    from weightroom.domain.units import UNIT_APPLICATIONS
    from weightroom.services.apps import VersionCache, inventory
    from weightroom.services.doctor import diagnose
    from weightroom.services.processes import SubprocessSystemdController
    from weightroom.services.settings_forms import read_schema_document, settings_form
    from weightroom.services.tls import TlsPaths, tls_status

    loaded = load_settings_or_exit(config)
    settings = loaded.settings
    controller = SubprocessSystemdController()
    forms = {}
    for app in UNIT_APPLICATIONS:
        document, error = read_schema_document(settings, app, config_path=loaded.config_path)
        forms[app] = settings_form(
            settings,
            app,
            document=document,
            document_error=error,
            config_path=loaded.config_path if app == "weightroom" else None,
        )
    paths = TlsPaths.for_settings(settings)
    tls = tls_status(paths, now=datetime.now(UTC)) if paths.complete() else None
    with (
        httpx.Client(trust_env=False) as client,
        open_loaded_database(loaded) as database,
    ):
        views = inventory(
            settings,
            controller=controller,
            cache=VersionCache(),
            client=client,
            now=0.0,
        )
        report = diagnose(
            settings,
            controller=controller,
            forms=forms,
            views=views,
            tls=tls,
            database=database,
            client=client,
        )
    if json_output:
        typer.echo(json.dumps(report.as_json(), indent=2))
    else:
        _print(report, all_findings=all_findings)
    if not report.healthy:
        raise typer.Exit(1)


def _print(report: object, *, all_findings: bool) -> None:
    """One block per finding, with the command underneath the ones that have one."""
    findings = [
        one
        for one in report.findings  # type: ignore[attr-defined]
        if all_findings or one.severity != "ok"
    ]
    counts = report.counts  # type: ignore[attr-defined]
    for finding in findings:
        mark = _MARKS.get(finding.severity, finding.severity)
        typer.echo(f"{mark}  {finding.rule}  {finding.summary}")
        if finding.evidence:
            typer.echo(f"        {finding.evidence}  [{finding.document}]")
        if finding.command:
            for line in finding.command.splitlines():
                typer.echo(f"        $ {line}")
    summary = "  ".join(f"{name} {counts[name]}" for name in counts if counts[name])
    typer.echo(f"\n{summary or 'nothing to report'}")
    if not all_findings and counts.get("ok"):
        typer.echo(f"({counts['ok']} rules pass; --all prints them.)")
