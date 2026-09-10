"""docs_index

The docs viewer's full-text index (data model §2): an FTS5 virtual table on SQLite, a plain
table with a generated ``tsvector`` column and a GIN index on PostgreSQL — the search service
(``services/docs_index.py``) hides the difference behind one function. Neither shape is
representable through Alembic's ``op.create_table``, so both are raw DDL.

Additive only, and silently dropped on downgrade: the index is rebuilt from the documentation
tree by ``wr-gym docs index`` (and the ``docs_index`` job kind, W9), never the source of any row
— losing it loses nothing a rebuild does not restore.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        try:
            op.execute("CREATE VIRTUAL TABLE docs_index USING fts5(path UNINDEXED, title, body)")
        except Exception:  # noqa: BLE001 — an SQLite build with no FTS5 module compiled in
            # (spec §13 risk T9): the plain table below is what services/docs_index.py's LIKE
            # fallback (labelled *degraded*) reads instead. Startup must succeed either way.
            op.execute(
                "CREATE TABLE docs_index (path VARCHAR PRIMARY KEY, title VARCHAR NOT NULL, "
                "body TEXT NOT NULL)"
            )
    else:
        op.execute(
            """
            CREATE TABLE docs_index (
                path VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                body TEXT NOT NULL,
                search_vector TSVECTOR GENERATED ALWAYS AS (
                    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))
                ) STORED
            )
            """
        )
        op.execute(
            "CREATE INDEX ix_docs_index_search_vector ON docs_index USING GIN(search_vector)"
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS docs_index")
