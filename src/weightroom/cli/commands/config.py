"""weightroom.cli.commands.config — show, validate, init, path, reference, schema.

Only ``typer`` and ``json`` load at module level; ``weightroom.config`` is imported lazily inside
each command body (CLI standards §12).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

__all__ = ["app"]

app = typer.Typer(help="Configuration inspection and management.")


def _looks_secret(field_name: str) -> bool:
    lowered = field_name.lower()
    return any(marker in lowered for marker in ("token", "key", "secret", "password"))


def _flatten(node: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{path}."))
        else:
            flat[path] = value
    return flat


@app.command("show")
def show(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print JSON instead of a table.")
    ] = False,
) -> None:
    """Print the effective configuration, with the source of every value.

    A runtime-changeable key whose stored row is in force is marked ``(database)``; a row the
    environment shadows is marked as shadowed beside the variable that beats it (configuration
    standards §7). Secret-shaped values print as ``********``.

    Example:
        wr-gym config show --json
    """
    from weightroom.cli._backend import load_settings_or_exit
    from weightroom.services.settings import database_overlay

    loaded = load_settings_or_exit(config)
    dumped = loaded.settings.model_dump(mode="json")
    flat = _flatten(dumped)
    sources = dict(loaded.sources)
    for path, (value, source) in database_overlay(loaded.settings).items():
        sources[path] = source
        flat[path] = value
    if json_output:
        typer.echo(
            json.dumps({"values": flat, "sources": sources, "config_path": str(loaded.config_path)})
        )
        return
    typer.echo(
        f"# {loaded.config_path}{'' if loaded.config_file_used else ' (not found; defaults apply)'}"
    )
    for path, value in flat.items():
        rendered = "********" if _looks_secret(path.rsplit(".", 1)[-1]) and value else value
        typer.echo(f"{path:<40} {rendered!s:<32} ({sources.get(path, 'default')})")


@app.command("validate")
def validate(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
    file: Annotated[
        str | None,
        typer.Option("--file", help="Validate this candidate file instead of the installation's."),
    ] = None,
) -> None:
    """Validate configuration without starting the service. Exit 0 or 3.

    ``--file`` runs a candidate through the same parse, validation and security refusals as
    startup (ADR-0127 rule 2); the installation's own file is not read for it.

    Example:
        wr-gym config validate --file /tmp/candidate.toml
    """
    from weightroom.cli._backend import load_settings_or_exit

    if file is not None and not Path(file).is_file():
        typer.echo(f"Error: {file} not found (CONFIGURATION_ERROR)", err=True)
        raise typer.Exit(3)
    load_settings_or_exit(file if file is not None else config)
    typer.echo("Configuration is valid.")


@app.command("path")
def path(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
) -> None:
    """Print the resolved configuration file location.

    Example:
        wr-gym config path
    """
    from weightroom.config import resolve_config_path

    typer.echo(str(resolve_config_path(config)))


@app.command("init")
def init(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to write the config file to.")
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
) -> None:
    """Write a fully commented example configuration file.

    Example:
        wr-gym config init --force
    """
    from weightroom.config import EXAMPLE_CONFIG_TOML, resolve_config_path

    target = resolve_config_path(config)
    if target.exists() and not force:
        typer.echo(f"Error: {target} already exists (use --force to overwrite).", err=True)
        raise typer.Exit(3)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(EXAMPLE_CONFIG_TOML, encoding="utf-8")
    typer.echo(str(target))


@app.command("reference")
def reference(
    check: Annotated[
        bool,
        typer.Option(
            "--check", help="Exit 1 if docs/configuration.md differs from the generated text."
        ),
    ] = False,
    output: Annotated[
        str | None, typer.Option("--output", help="Write to this file instead of stdout.")
    ] = None,
) -> None:
    """Generate the configuration reference from the settings model (configuration standards §8).

    With ``--check``, compares against ``--output`` (or ``docs/configuration.md``) and exits 1 on
    drift, which is what CI runs.
    """
    from weightroom.services.config_reference import render_configuration_reference

    rendered = render_configuration_reference()
    target = Path(output) if output else Path("docs/configuration.md")
    if check:
        committed = target.read_text(encoding="utf-8") if target.is_file() else ""
        if committed != rendered:
            typer.echo(
                f"{target} differs from the generated reference; run "
                "`wr-gym config reference --output docs/configuration.md`",
                err=True,
            )
            raise typer.Exit(1)
        typer.echo(f"{target} matches the settings model")
        return
    if output:
        target.write_text(rendered, encoding="utf-8")
        typer.echo(f"wrote {target}")
    else:
        typer.echo(rendered)


@app.command("schema")
def schema(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print the schema document as canonical JSON.")
    ] = False,
) -> None:
    """Print the settings-schema document (ADR-0127 rule 1, applied to WeightRoomGym itself).

    WeightRoomGym's own settings page is generated from this document exactly as the four
    applications' are. It carries key paths and layers, never a value.

    Example:
        wr-gym config schema --json
    """
    from baseaicore import canonical_json

    from weightroom.cli._backend import fail
    from weightroom.config import ConfigurationError
    from weightroom.services.settings import config_schema_document

    try:
        document = config_schema_document(config)
    except ConfigurationError as exc:
        raise fail(exc, exit_code=3) from exc
    if json_output:
        typer.echo(canonical_json(document))
        return
    typer.echo(
        f"schema_version {document['schema_version']}  application {document['application']}"
        f"  version {document['version']}"
    )
    typer.echo(f"config_path {document['config_path']}")
    typer.echo(f"runtime_changeable ({len(document['runtime_changeable'])}):")
    for entry in document["runtime_changeable"]:
        typer.echo(f"  {entry['key']} ({entry['kind']})")
    typer.echo(f"security_keys ({len(document['security_keys'])}):")
    for key in document["security_keys"]:
        typer.echo(f"  {key}")
    if document["problems"]:
        typer.echo("problems:")
        for problem in document["problems"]:
            typer.echo(f"  {problem}")
