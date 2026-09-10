"""weightroom.services.docs_index — the full-text index, and its labelled degrade to LIKE."""

from __future__ import annotations

from pathlib import Path

from weightroom.services.database import Database, ensure_ready
from weightroom.services.docs_index import (
    FTS5_SHADOW_TABLES,
    rebuild_index,
    search,
)


def _database(tmp_path: Path) -> Database:
    database = Database.from_url(f"sqlite:///{tmp_path / 'w.sqlite3'}")
    ensure_ready(database, auto_migrate=True)
    return database


def _docs(tmp_path: Path) -> Path:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "alpha.md").write_text("# Alpha\n\nUnavailable is never zero, ADR-0016.\n")
    (root / "beta.md").write_text("# Beta\n\nSomething about queues and residency.\n")
    return root


class TestRebuildIndex:
    def test_indexes_every_markdown_file(self, tmp_path: Path) -> None:
        database = _database(tmp_path)
        count = rebuild_index(database, _docs(tmp_path))
        assert count == 2

    def test_rebuilding_replaces_rather_than_accumulates(self, tmp_path: Path) -> None:
        database = _database(tmp_path)
        root = _docs(tmp_path)
        rebuild_index(database, root)
        (root / "alpha.md").unlink()
        count = rebuild_index(database, root)
        assert count == 1
        assert search(database, "beta").hits


class TestSearch:
    def test_finds_the_page_that_mentions_the_query(self, tmp_path: Path) -> None:
        database = _database(tmp_path)
        rebuild_index(database, _docs(tmp_path))
        result = search(database, "never zero")
        assert not result.degraded
        assert result.hits
        assert result.hits[0].path == "alpha.md"
        assert "zero" in result.hits[0].snippet.lower()

    def test_a_blank_query_returns_no_hits_and_is_not_degraded(self, tmp_path: Path) -> None:
        database = _database(tmp_path)
        rebuild_index(database, _docs(tmp_path))
        result = search(database, "   ")
        assert result.hits == ()
        assert result.degraded is False

    def test_a_query_with_fts5_syntax_characters_does_not_crash(self, tmp_path: Path) -> None:
        database = _database(tmp_path)
        rebuild_index(database, _docs(tmp_path))
        for tricky in ('"unterminated', "NOT AND OR", "queue*-residency", 'a"b"c'):
            result = search(database, tricky)
            assert isinstance(result.hits, tuple)  # answers something, never raises

    def test_no_hits_for_a_word_that_is_not_there(self, tmp_path: Path) -> None:
        database = _database(tmp_path)
        rebuild_index(database, _docs(tmp_path))
        assert search(database, "nonexistentxyzterm").hits == ()

    def test_the_like_fallback_finds_the_same_page_when_forced(self, tmp_path: Path) -> None:
        from weightroom.services.docs_index import _search_like

        database = _database(tmp_path)
        rebuild_index(database, _docs(tmp_path))
        hits = _search_like(database, "never zero", limit=20)
        assert any(hit.path == "alpha.md" for hit in hits)

    def test_fts5_shadow_tables_are_the_expected_five(self, tmp_path: Path) -> None:
        # Guards the migration-parity exclusion list (tests/integration/test_migrations.py)
        # against silent drift if a future SQLite/mistune upgrade changes FTS5's shadow set.
        database = _database(tmp_path)
        from sqlalchemy import text

        with database.read() as session:
            names = {
                str(row[0])
                for row in session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).all()
            }
        assert set(FTS5_SHADOW_TABLES) <= names
