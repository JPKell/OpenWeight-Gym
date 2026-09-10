"""weightroom.cli.commands.docs — rebuild the full-text index (local mode, CLI standards §6)."""

from __future__ import annotations

import json
from typing import Annotated

import typer

__all__ = ["app"]

app = typer.Typer(help="The documentation viewer's search index.")


@app.command("index")
def index(
    config: Annotated[
        str | None, typer.Option("--config", help="Path to a config.toml file.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print JSON instead of text.")
    ] = False,
) -> None:
    """Rebuild the documentation search index from ``[docs] root``.

    Example:
        wr-gym docs index
    """
    from weightroom.cli._backend import fail, open_ready_database
    from weightroom.services.docs import DocsRootMissing, resolve_docs_root
    from weightroom.services.docs_index import rebuild_index

    with open_ready_database(config) as (database, settings):
        try:
            root = resolve_docs_root(settings)
        except DocsRootMissing as exc:
            raise fail(exc, exit_code=3) from exc
        count = rebuild_index(database, root)
    if json_output:
        typer.echo(json.dumps({"root": str(root), "documents_indexed": count}))
        return
    typer.echo(f"indexed {count} document{'' if count == 1 else 's'} from {root}")
