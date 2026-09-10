"""weightroom.services.docs_index — the documentation tree's full-text index.

Migration ``0003`` creates whichever shape the connected dialect speaks (data model §2): FTS5 on
SQLite when the module is compiled in, a plain table otherwise (spec §13 risk T9), a table with a
generated ``tsvector`` column on PostgreSQL. This module is the one function each shape answers
through — :func:`search` probes which table it has and never asks the caller to know.

**Degraded means the LIKE fallback, and it is labelled.** SQLite without the FTS5 module and an
FTS5 query mistune's own tokens cannot form (an unmatched quote, for instance) both land here:
either way the page says *degraded* rather than searching worse in silence.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

if TYPE_CHECKING:
    from weightroom.services.database import Database
    from weightroom.services.docs import TreeNode

__all__ = [
    "FTS5_SHADOW_TABLES",
    "SNIPPET_RADIUS",
    "SearchHit",
    "SearchResult",
    "rebuild_index",
    "search",
]

FTS5_SHADOW_TABLES: Final = (
    "docs_index",
    "docs_index_data",
    "docs_index_idx",
    "docs_index_docsize",
    "docs_index_config",
    "docs_index_content",
)
"""SQLite FTS5's own bookkeeping tables, created alongside ``docs_index`` and never modelled in
``Base.metadata`` — the migration parity check excludes them by this exact set
(``tests/integration/test_migrations.py``)."""

SNIPPET_RADIUS: Final = 80

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_FTS5_QUOTE_RE = re.compile(r'"')

_SEARCH_LIMIT_CAP: Final = 50

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One result: the path, the title, and a snippet of surrounding text."""

    path: str
    title: str
    snippet: str


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A search's hits, and whether it ran degraded (the LIKE fallback, spec §13 risk T9)."""

    hits: tuple[SearchHit, ...]
    degraded: bool


def _plain_text(html_body: str) -> str:
    """Strip rendered HTML to indexable plain text — one collapse of whitespace, no markup."""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", html_body)).strip()


def rebuild_index(database: Database, root: Path) -> int:
    """Rebuild ``docs_index`` from every ``*.md`` file under ``root``. ``wr-gym docs index``.

    Returns:
        How many documents were indexed.
    """
    from weightroom.services.docs import build_tree, render_markdown

    def _paths(node: TreeNode) -> list[str]:
        found: list[str] = []
        for child in node.children:
            if child.is_dir:
                found.extend(_paths(child))
            else:
                found.append(child.path)
        return found

    tree = build_tree(root)
    document_paths = _paths(tree)
    rows = []
    for relative in document_paths:
        page = render_markdown(root, root / relative)
        rows.append({"path": relative, "title": page.title, "body": _plain_text(page.html)})

    with database.write() as session:
        session.execute(text("DELETE FROM docs_index"))
        if rows:
            session.execute(
                text("INSERT INTO docs_index (path, title, body) VALUES (:path, :title, :body)"),
                rows,
            )
    return len(rows)


def _fts5_query(query: str) -> str:
    """Quote every token so FTS5 syntax characters in the query cannot break the MATCH."""
    tokens = query.split()
    quoted = ['"' + _FTS5_QUOTE_RE.sub('""', token) + '"' for token in tokens]
    return " ".join(quoted)


def _snippet(body: str, query: str) -> str:
    lowered = body.lower()
    index = lowered.find(query.lower().split()[0]) if query.split() else -1
    if index < 0:
        return body[: SNIPPET_RADIUS * 2].strip()
    start = max(0, index - SNIPPET_RADIUS)
    end = min(len(body), index + SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(body) else ""
    return f"{prefix}{body[start:end].strip()}{suffix}"


def _has_fts5(database: Database) -> bool:
    with database.read() as session:
        row = session.execute(
            text("SELECT sql FROM sqlite_master WHERE name = 'docs_index'")
        ).first()
    return row is not None and "fts5" in str(row[0]).lower()


def _search_like(database: Database, query: str, *, limit: int) -> tuple[SearchHit, ...]:
    pattern = f"%{query.replace('%', '\\%').replace('_', '\\_')}%"
    with database.read() as session:
        rows = session.execute(
            text(
                "SELECT path, title, body FROM docs_index "
                "WHERE title LIKE :pattern ESCAPE '\\' OR body LIKE :pattern ESCAPE '\\' "
                "LIMIT :limit"
            ),
            {"pattern": pattern, "limit": limit},
        ).all()
    return tuple(
        SearchHit(path=str(path), title=str(title), snippet=_snippet(str(body), query))
        for path, title, body in rows
    )


def search(database: Database, query: str, *, limit: int = 20) -> SearchResult:
    """Search ``docs_index``. FTS5 when it is there, the LIKE fallback — *degraded* — otherwise.

    Args:
        database: WeightRoomGym's own database handle.
        query: Free text; never built into a statement unparameterised.
        limit: Hits wanted, capped at :data:`_SEARCH_LIMIT_CAP`.

    Returns:
        The result. Never raises for a malformed query or an FTS5-less SQLite build — both
        degrade to the LIKE fallback rather than surfacing a 500 for a search box.
    """
    bounded = max(1, min(limit, _SEARCH_LIMIT_CAP))
    cleaned = query.strip()
    if not cleaned:
        return SearchResult(hits=(), degraded=False)
    dialect = database.engine.dialect.name
    if dialect == "sqlite" and _has_fts5(database):
        try:
            with database.read() as session:
                rows = session.execute(
                    text(
                        "SELECT path, title, snippet(docs_index, 2, '', '', '…', 12) "
                        "FROM docs_index WHERE docs_index MATCH :query "
                        "ORDER BY rank LIMIT :limit"
                    ),
                    {"query": _fts5_query(cleaned), "limit": bounded},
                ).all()
            hits = tuple(
                SearchHit(path=str(path), title=str(title), snippet=str(snippet))
                for path, title, snippet in rows
            )
            return SearchResult(hits=hits, degraded=False)
        except Exception as exc:  # noqa: BLE001 — a malformed MATCH query degrades, never 500s
            logger.info("docs_index.fts5_query_failed", extra={"detail": str(exc)})
    elif dialect != "sqlite":
        try:
            with database.read() as session:
                rows = session.execute(
                    text(
                        "SELECT path, title, "
                        "ts_headline('english', body, plainto_tsquery('english', :query)) "
                        "FROM docs_index WHERE search_vector @@ plainto_tsquery('english', :query) "
                        "LIMIT :limit"
                    ),
                    {"query": cleaned, "limit": bounded},
                ).all()
            hits = tuple(
                SearchHit(path=str(path), title=str(title), snippet=str(snippet))
                for path, title, snippet in rows
            )
            return SearchResult(hits=hits, degraded=False)
        except Exception as exc:  # noqa: BLE001 — same posture as the SQLite path above
            logger.info("docs_index.tsvector_query_failed", extra={"detail": str(exc)})
    return SearchResult(hits=_search_like(database, cleaned, limit=bounded), degraded=True)
