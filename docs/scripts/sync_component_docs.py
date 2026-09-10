#!/usr/bin/env python3
"""Copy each component's own README and user documents into this documentation tree.

This runs the other way from the mirrors. ``WeightRoom/docs/`` is canonical for specs, plans and
ADRs, and each component carries copies of those. A component's root ``README.md`` and the
documents it writes in its own ``docs/`` (quickstart, api, operations, troubleshooting, …) are
canonical *in the component*. This script copies them here so the docs viewer shows them beside
the spec:

    <component>/README.md       ->  docs/<apps|packages>/<name>/guide/README.md
    <component>/docs/<file>.md  ->  docs/<apps|packages>/<name>/guide/<file>.md

Skipped: ``docs/README.md`` (a component's index of its own copies), the mirrored ``docs/apps/``
and ``docs/packages/`` subtrees, anything that is not markdown, and the suite documents whose
canonical copy is already at this tree's root (:data:`SHARED`). WeightRoomGym contributes only its
README, because its ``docs/`` is this tree.

Relative ``.md`` links are re-pointed so they still resolve here: to the copied document, or to
this tree's own copy of a mirrored one. A relative ``.md`` link that resolves to nothing here
(``CHANGELOG.md``, say) is reduced to its text. Every other link is left as written; the viewer
already renders a non-markdown relative link as plain text.

The ``guide/`` directories belong to this script. A file there that no component supplies any
more is deleted. Edit the component, never the copy, then re-run this and ``wr-gym docs index``.

Usage:
    python docs/scripts/sync_component_docs.py            # write the copies
    python docs/scripts/sync_component_docs.py --check    # exit 1 if any copy is stale
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent
SUITE = DOCS.parent.parent
APPS = ("FreeWeight", "LoadCoach", "IdeaPress", "PromptCadence", "WeightRoom")
GUIDE = "guide"

#: Suite documents whose canonical copy is this tree's own; a component's copy is never taken.
SHARED = frozenset({"LAN_ACCESS.md", "LLAMACPP_SETUP.md", "MEMORY_SAFETY.md"})

#: ``[label](target)`` or ``[label](target#fragment)``, not an image.
_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s#]+)((?:#[^)\s]*)?)\)")


def components() -> list[tuple[Path, Path]]:
    """Return ``(repository, guide directory)`` for every component, packages first.

    Returns:
        Each ``py/<Package>`` holding a ``pyproject.toml`` maps to ``packages/<package>/guide``;
        each application in :data:`APPS` maps to ``apps/<app>/guide``.
    """
    packages = sorted(p for p in (SUITE / "py").iterdir() if (p / "pyproject.toml").is_file())
    pairs = [(repo, DOCS / "packages" / repo.name.lower() / GUIDE) for repo in packages]
    pairs += [(SUITE / name, DOCS / "apps" / name.lower() / GUIDE) for name in APPS]
    return pairs


def sources(repo: Path) -> list[Path]:
    """Return the documents one component contributes, README first.

    Args:
        repo: The component repository.

    Returns:
        The root ``README.md`` when present, then every top-level ``docs/*.md`` except
        ``docs/README.md`` and the :data:`SHARED` documents.
    """
    found = [repo / "README.md"] if (repo / "README.md").is_file() else []
    if repo == DOCS.parent:
        return found  # WeightRoomGym's docs/ is this tree
    return found + [
        path
        for path in sorted((repo / "docs").glob("*.md"))
        if path.name != "README.md" and path.name not in SHARED
    ]


def repoint(text: str, *, source: Path, repo: Path, copied: dict[Path, Path]) -> str:
    """Return ``text`` with its relative ``.md`` links made to resolve from ``copied[source]``.

    Args:
        text: The source document's markdown.
        source: Where the document lives in its component.
        repo: The component repository.
        copied: ``{source path: destination path}`` for this component's documents.

    Returns:
        The markdown with each relative ``.md`` link pointing at the copied document or at this
        tree's copy of the component ``docs/`` file it named, or reduced to its label when this
        tree has neither. Absolute, fragment-only and non-markdown links are untouched.
    """
    destination_dir = copied[source].parent

    def sub(match: re.Match[str]) -> str:
        label, target, fragment = match.groups()
        if not target.endswith(".md") or ":" in target or target.startswith("/"):
            return match.group(0)
        resolved = Path(os.path.normpath(source.parent / target))
        docs_relative = (
            resolved.relative_to(repo / "docs") if resolved.is_relative_to(repo / "docs") else None
        )
        if resolved in copied:
            new = copied[resolved]
        elif docs_relative is not None and (DOCS / docs_relative).is_file():
            new = DOCS / docs_relative
        else:
            return label
        href = Path(os.path.relpath(new, destination_dir)).as_posix()
        return f"[{label}]({href}{fragment})"

    return _LINK.sub(sub, text)


def render(pairs: list[tuple[Path, Path]]) -> dict[Path, str]:
    """Return ``{destination: content}`` for every document the guide directories should hold.

    Args:
        pairs: :func:`components`' result.

    Returns:
        One entry per contributed document, links already re-pointed.
    """
    intended: dict[Path, str] = {}
    for repo, guide in pairs:
        copied = {path: guide / path.name for path in sources(repo)}
        for path, destination in copied.items():
            text = path.read_text(encoding="utf-8")
            intended[destination] = repoint(text, source=path, repo=repo, copied=copied)
    return intended


def main() -> int:
    """Write or verify the copies.

    Returns:
        ``0`` when the copies are written, or already current under ``--check``; ``1`` when
        ``--check`` finds a stale, missing or orphaned copy, each one named.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Verify rather than write.")
    args = parser.parse_args()

    pairs = components()
    intended = render(pairs)
    stale = sorted(
        path
        for path, content in intended.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    )
    orphans = sorted(
        path
        for _repo, guide in pairs
        if guide.is_dir()
        for path in guide.iterdir()
        if path not in intended
    )
    if args.check:
        for path in stale:
            print(f"stale: {path.relative_to(DOCS)}")
        for path in orphans:
            print(f"orphan: {path.relative_to(DOCS)}")
        if stale or orphans:
            print("\nRun: python docs/scripts/sync_component_docs.py")
        return 1 if stale or orphans else 0

    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(intended[path], encoding="utf-8")
    for path in orphans:
        path.unlink()
    print(
        f"{len(intended)} document(s) from {len(pairs)} components: "
        f"{len(stale)} written, {len(orphans)} removed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
