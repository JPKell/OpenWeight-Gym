"""weightroom.services.docs — root resolution, containment, rendering, the ADR index.

Phase 5's own test list (development plan): goldens for a table, a fence, a mermaid block, a
footnote, a relative and an outside link; the sanitiser against ``<script>`` and ``{{ }}``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from weightroom.config import load_settings
from weightroom.services.docs import (
    DocsPageOutsideRoot,
    DocsRootMissing,
    build_tree,
    parse_adr_index,
    render_markdown,
    resolve_doc_path,
    resolve_docs_root,
)


def _settings(tmp_path: Path, *, docs_root: str | None):  # type: ignore[no-untyped-def]
    lines = ['[storage]\ndatabase_url = "sqlite:///' + str(tmp_path / "w.sqlite3") + '"\n']
    if docs_root is not None:
        lines.append(f'[docs]\nroot = "{docs_root}"\n')
    config = tmp_path / "console.toml"
    config.write_text("".join(lines))
    return load_settings(config_path=config).settings


class TestResolveDocsRoot:
    def test_a_configured_root_is_used(self, tmp_path: Path) -> None:
        docs = tmp_path / "documentation"
        docs.mkdir()
        settings = _settings(tmp_path, docs_root=str(docs))
        assert resolve_docs_root(settings) == docs.resolve()

    def test_a_configured_root_that_is_not_a_directory_is_refused(self, tmp_path: Path) -> None:
        not_a_dir = tmp_path / "nope.txt"
        not_a_dir.write_text("x")
        settings = _settings(tmp_path, docs_root=str(not_a_dir))
        with pytest.raises(DocsRootMissing):
            resolve_docs_root(settings)

    def test_the_default_finds_the_real_docs_tree_beside_this_checkout(
        self, tmp_path: Path
    ) -> None:
        settings = _settings(tmp_path, docs_root=None)
        root = resolve_docs_root(settings)
        assert (root / "adr" / "README.md").is_file()


class TestResolveDocPath:
    @pytest.fixture
    def root(self, tmp_path: Path) -> Path:
        base = tmp_path / "docs"
        (base / "sub").mkdir(parents=True)
        (base / "page.md").write_text("# Page\n")
        (base / "sub" / "child.md").write_text("# Child\n")
        return base

    def test_a_plain_relative_path_resolves(self, root: Path) -> None:
        assert resolve_doc_path(root, "page.md") == (root / "page.md").resolve()
        assert resolve_doc_path(root, "sub/child.md") == (root / "sub" / "child.md").resolve()

    def test_a_traversal_escape_is_refused(self, root: Path) -> None:
        with pytest.raises(DocsPageOutsideRoot):
            resolve_doc_path(root, "../../etc/passwd")

    def test_a_traversal_that_returns_inside_the_root_is_allowed(self, root: Path) -> None:
        assert resolve_doc_path(root, "sub/../page.md") == (root / "page.md").resolve()

    def test_an_absolute_path_is_refused(self, root: Path) -> None:
        with pytest.raises(DocsPageOutsideRoot):
            resolve_doc_path(root, "/etc/passwd")

    def test_a_blank_candidate_is_refused(self, root: Path) -> None:
        with pytest.raises(DocsPageOutsideRoot):
            resolve_doc_path(root, "   ")

    def test_a_candidate_holding_a_nul_is_refused(self, root: Path) -> None:
        with pytest.raises(DocsPageOutsideRoot):
            resolve_doc_path(root, "page.md\x00/../../../etc/passwd")

    def test_a_nonexistent_file_is_refused(self, root: Path) -> None:
        with pytest.raises(DocsPageOutsideRoot):
            resolve_doc_path(root, "missing.md")

    def test_a_symlinked_file_pointing_out_of_the_root_is_refused(
        self, root: Path, tmp_path: Path
    ) -> None:
        outside = tmp_path / "outside.md"
        outside.write_text("# secret\n")
        (root / "link.md").symlink_to(outside)
        with pytest.raises(DocsPageOutsideRoot):
            resolve_doc_path(root, "link.md")

    def test_a_sibling_sharing_a_string_prefix_is_outside(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs2").mkdir()
        (tmp_path / "docs2" / "x.md").write_text("# X\n")
        with pytest.raises(DocsPageOutsideRoot):
            resolve_doc_path(tmp_path / "docs", "../docs2/x.md")


class TestBuildTree:
    def test_directories_first_then_files_both_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "b.md").write_text("# B\n")
        (tmp_path / "a.md").write_text("# A\n")
        (tmp_path / "zdir").mkdir()
        (tmp_path / "zdir" / "c.md").write_text("# C\n")
        tree = build_tree(tmp_path)
        names = [child.name for child in tree.children]
        assert names == ["zdir", "a.md", "b.md"]

    def test_a_directory_with_no_markdown_anywhere_under_it_is_omitted(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "empty").mkdir()
        (tmp_path / "empty" / "notes.txt").write_text("not markdown")
        tree = build_tree(tmp_path)
        assert tree.children == ()

    def test_non_markdown_files_are_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "page.md").write_text("# Page\n")
        tree = build_tree(tmp_path)
        assert [c.name for c in tree.children] == ["page.md"]


class TestRenderMarkdown:
    def test_headings_get_stable_ids_and_an_outline(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("# Top Level\n\n## A Second Heading!\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert '<h1 id="top-level">' in page.html
        assert '<h2 id="a-second-heading">' in page.html
        assert page.outline == (
            {"level": 1, "id": "top-level", "text": "Top Level"},
            {"level": 2, "id": "a-second-heading", "text": "A Second Heading!"},
        )
        assert page.title == "Top Level"

    def test_duplicate_headings_get_distinct_ids(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("# Notes\n\n## Notes\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        ids = [entry["id"] for entry in page.outline]
        assert ids == ["notes", "notes-1"]

    def test_a_table_renders(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("| A | B |\n|---|---|\n| 1 | 2 |\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert "<table>" in page.html and "<td>1</td>" in page.html

    def test_a_footnote_renders(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("Text[^1].\n\n[^1]: The note.\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert "footnote" in page.html

    def test_a_mermaid_fence_becomes_a_mount_point_and_sets_has_mermaid(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "d.md").write_text("```mermaid\ngraph TD; A-->B;\n```\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert page.has_mermaid is True
        assert '<pre class="mermaid">' in page.html
        assert "graph TD" in page.html

    def test_an_ordinary_fence_is_not_flagged_as_mermaid(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("```python\nprint('hi')\n```\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert page.has_mermaid is False
        assert '<pre class="mermaid">' not in page.html
        assert "language-python" in page.html

    def test_a_relative_link_to_a_markdown_file_inside_root_is_rewritten(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "other.md").write_text("# Other\n")
        (tmp_path / "d.md").write_text("[go](sub/other.md)\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert 'href="/docs/page?path=sub/other.md"' in page.html

    def test_a_relative_link_that_escapes_the_root_renders_as_text_not_a_link(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "outside.md").write_text("# Outside\n")
        (tmp_path / "docs" / "d.md").write_text("[go](../outside.md)\n")
        page = render_markdown(tmp_path / "docs", tmp_path / "docs" / "d.md")
        assert "<a " not in page.html
        assert "go" in page.html

    def test_a_link_to_a_non_markdown_target_renders_as_text(self, tmp_path: Path) -> None:
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "d.md").write_text("[pic](image.png)\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert "<a " not in page.html

    def test_an_external_link_is_left_alone(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("[ext](https://example.com/path)\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert 'href="https://example.com/path"' in page.html

    def test_a_script_tag_is_escaped_never_executed(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("# T\n\n<script>alert(1)</script>\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert "<script>" not in page.html
        assert "&lt;script&gt;" in page.html

    def test_jinja_looking_braces_render_as_literal_text(self, tmp_path: Path) -> None:
        (tmp_path / "d.md").write_text("# T\n\nSee {{ 7 * 7 }} and {% if x %}y{% endif %}.\n")
        page = render_markdown(tmp_path, tmp_path / "d.md")
        assert "{{ 7 * 7 }}" in page.html
        assert "{% if x %}" in page.html


class TestParseAdrIndex:
    def test_the_real_index_parses_with_the_known_first_and_last_rows(self) -> None:
        settings = None  # the real tree, not a fixture — the index is the thing under test
        del settings
        root = Path(__file__).resolve().parents[2] / "docs"
        rows = parse_adr_index(root)
        assert len(rows) >= 129
        assert rows[0].number == "0001"
        assert rows[0].path == "adr/0001-application-and-package-separation.md"
        assert rows[0].status == "Accepted"

    def test_a_malformed_row_is_skipped_not_raised(self, tmp_path: Path) -> None:
        (tmp_path / "adr").mkdir()
        (tmp_path / "adr" / "README.md").write_text(
            "## Index\n\n"
            "| ADR | Title | Status |\n|---|---|---|\n"
            "| [0001](0001-a.md) | First | Accepted |\n"
            "not a table row at all\n"
            "| [0002](0002-b.md) | Second | Accepted |\n"
        )
        rows = parse_adr_index(tmp_path)
        assert [row.number for row in rows] == ["0001", "0002"]

    def test_a_missing_index_returns_no_rows_rather_than_raising(self, tmp_path: Path) -> None:
        assert parse_adr_index(tmp_path) == ()
