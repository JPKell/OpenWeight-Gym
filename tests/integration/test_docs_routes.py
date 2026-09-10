"""``/docs/*`` and ``/api/v1/docs/*`` (api.md §8, spec §7.5) — the pages, over a scratch tree."""

from __future__ import annotations

from pathlib import Path

from tests.support import Console, build_console
from weightroom.services.docs import resolve_docs_root
from weightroom.services.docs_index import rebuild_index


def _docs_root(tmp_path: Path) -> Path:
    root = tmp_path / "docs"
    (root / "adr").mkdir(parents=True)
    (root / "architecture").mkdir()
    (root / "adr" / "README.md").write_text(
        "## Index\n\n| ADR | Title | Status |\n|---|---|---|\n"
        "| [0016](0016-unavailable-is-not-zero.md) | Unavailable is not zero | Accepted |\n"
    )
    (root / "adr" / "0016-unavailable-is-not-zero.md").write_text(
        "# ADR-0016 — Unavailable is not zero\n\nA measurement that is unavailable is never zero.\n"
    )
    (root / "architecture" / "master-architecture.md").write_text(
        "# Master Architecture\n\n```mermaid\ngraph TD; A-->B;\n```\n"
    )
    return root


def _console(tmp_path: Path) -> Console:
    root = _docs_root(tmp_path)
    console = build_console(tmp_path, extra_toml=f'[docs]\nroot = "{root}"\n')
    rebuild_index(console.database, resolve_docs_root(console.settings))
    return console


def test_the_tree_the_page_the_search_and_the_adr_index_json(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()

    tree = console.client.get("/api/v1/docs/tree").json()
    names = {child["name"] for child in tree["children"]}
    assert {"adr", "architecture"} <= names

    page = console.client.get(
        "/api/v1/docs/page", params={"path": "architecture/master-architecture.md"}
    ).json()
    assert page["title"] == "Master Architecture"
    assert page["has_mermaid"] is True
    assert '<pre class="mermaid">' in page["html"]

    search = console.client.get("/api/v1/docs/search", params={"q": "never zero"}).json()
    assert search["degraded"] is False
    assert any(hit["path"].endswith("0016-unavailable-is-not-zero.md") for hit in search["hits"])

    adrs = console.client.get("/api/v1/docs/adrs").json()
    assert adrs == [
        {
            "number": "0016",
            "path": "adr/0016-unavailable-is-not-zero.md",
            "title": "Unavailable is not zero",
            "status": "Accepted",
        }
    ]


def test_a_path_outside_the_root_is_404_docs_page_outside_root(tmp_path: Path) -> None:
    console = _console(tmp_path)
    console.login()
    response = console.client.get("/api/v1/docs/page", params={"path": "../../../etc/passwd"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCS_PAGE_OUTSIDE_ROOT"


def test_every_docs_route_needs_a_session(tmp_path: Path) -> None:
    console = build_console(tmp_path, host="10.77.10.84")
    for path in (
        "/api/v1/docs/tree",
        "/api/v1/docs/page?path=x.md",
        "/api/v1/docs/search?q=x",
        "/api/v1/docs/adrs",
    ):
        response = console.client.get(path, headers={"Host": "jordan-main.local"})
        assert response.status_code == 401, path


class TestPages:
    def test_the_tree_page_renders_inside_the_shell(self, tmp_path: Path) -> None:
        console = _console(tmp_path)
        console.login()
        page = console.client.get("/docs", headers={"Accept": "text/html"}).text
        assert page.count('class="app-tab"') == 4  # the shell chrome, every page (row W3)
        assert "architecture" in page
        assert 'href="/docs/page?path=architecture/master-architecture.md"' in page

    def test_a_page_with_mermaid_loads_the_vendored_script_and_a_plain_one_does_not(
        self, tmp_path: Path
    ) -> None:
        console = _console(tmp_path)
        console.login()
        with_diagram = console.client.get(
            "/docs/page?path=architecture/master-architecture.md", headers={"Accept": "text/html"}
        ).text
        assert "/app-static/vendor/mermaid/mermaid.min.js" in with_diagram
        assert '<pre class="mermaid">' in with_diagram
        assert "On this page" in with_diagram  # the outline

        without_diagram = console.client.get(
            "/docs/page?path=adr/0016-unavailable-is-not-zero.md", headers={"Accept": "text/html"}
        ).text
        assert "mermaid.min.js" not in without_diagram

    def test_an_outside_path_in_the_ui_renders_the_error_page_not_a_traceback(
        self, tmp_path: Path
    ) -> None:
        console = _console(tmp_path)
        console.login()
        response = console.client.get(
            "/docs/page?path=../../../etc/passwd", headers={"Accept": "text/html"}
        )
        assert response.status_code == 404

    def test_search_finds_the_page_and_shows_the_snippet(self, tmp_path: Path) -> None:
        console = _console(tmp_path)
        console.login()
        page = console.client.get("/docs/search?q=never+zero", headers={"Accept": "text/html"}).text
        assert 'href="/docs/page?path=adr/0016-unavailable-is-not-zero.md"' in page
        assert "zero" in page.lower()

    def test_the_adr_index_page_renders_the_table_with_a_link_and_a_status_badge(
        self, tmp_path: Path
    ) -> None:
        console = _console(tmp_path)
        console.login()
        page = console.client.get("/docs/adrs", headers={"Accept": "text/html"}).text
        assert 'href="/docs/page?path=adr/0016-unavailable-is-not-zero.md"' in page
        assert "status-success" in page  # Accepted -> success tone

    def test_the_consoles_top_bar_docs_link_is_real_not_a_stub(self, tmp_path: Path) -> None:
        console = _console(tmp_path)
        console.login()
        page = console.client.get("/", headers={"Accept": "text/html"}).text
        assert '<a href="/docs">Docs</a>' in page
        assert 'title="coming in phase W5"' not in page
