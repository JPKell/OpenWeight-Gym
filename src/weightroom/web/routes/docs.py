"""weightroom.web.routes.docs — the documentation viewer (api.md §8, spec §7.5). Read-only.

Two routers, the shape every other section of this application uses: ``router`` serves
``/api/v1/docs/…`` as JSON, ``ui_router`` serves the plain paths as pages. No route here writes
anything (spec §3); ``DocsRootMissing`` and ``DocsPageOutsideRoot`` are the only refusals a
handler raises, both already stable-coded (spec §13) by ``services/docs.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from weightroom.services.docs import (
    build_tree,
    parse_adr_index,
    render_markdown,
    resolve_doc_path,
    resolve_docs_root,
)
from weightroom.services.docs_index import search as search_index
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator

if TYPE_CHECKING:
    from weightroom.services.auth import Principal
    from weightroom.services.docs import DocPage

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["docs"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)

_DOCS_NAV = (
    {
        "title": "Docs",
        "links": [
            {"label": "Browse", "href": "/docs"},
            {"label": "ADR index", "href": "/docs/adrs"},
        ],
    },
)


@router.get("/docs/tree", summary="The directory tree under [docs] root")
def api_tree(request: Request, principal: CurrentOperator) -> JSONResponse:
    root = resolve_docs_root(request.app.state.settings)
    return JSONResponse(content=build_tree(root).as_json())


@router.get("/docs/page", summary="One rendered document")
def api_page(request: Request, principal: CurrentOperator, path: str = Query(...)) -> JSONResponse:
    root = resolve_docs_root(request.app.state.settings)
    resolved = resolve_doc_path(root, path)
    page = render_markdown(root, resolved)
    return JSONResponse(
        content={
            "path": path,
            "title": page.title,
            "html": page.html,
            "outline": list(page.outline),
            "has_mermaid": page.has_mermaid,
        }
    )


@router.get("/docs/search", summary="Full-text search")
def api_search(
    request: Request, principal: CurrentOperator, q: str = Query(default="")
) -> JSONResponse:
    result = search_index(request.app.state.database, q)
    return JSONResponse(
        content={
            "query": q,
            "degraded": result.degraded,
            "hits": [
                {"path": hit.path, "title": hit.title, "snippet": hit.snippet}
                for hit in result.hits
            ],
        }
    )


@router.get("/docs/adrs", summary="The ADR index")
def api_adrs(request: Request, principal: CurrentOperator) -> JSONResponse:
    root = resolve_docs_root(request.app.state.settings)
    rows = parse_adr_index(root)
    return JSONResponse(
        content=[
            {"number": r.number, "path": r.path, "title": r.title, "status": r.status} for r in rows
        ]
    )


def _docs_page(
    request: Request,
    principal: Principal,
    template: str,
    *,
    nav_footer: str | None = None,
    **context: Any,
) -> HTMLResponse:
    return render_shell_page(
        request,
        template,
        principal=principal,
        nav_sections=_DOCS_NAV,
        nav_footer=nav_footer,
        **context,
    )


@ui_router.get("/docs", summary="The docs tree", response_class=HTMLResponse)
def docs_home(request: Request, principal: CurrentOperator) -> HTMLResponse:
    root = resolve_docs_root(request.app.state.settings)
    tree = build_tree(root)
    return _docs_page(request, principal, "docs.html", tree=tree, root=str(root))


@ui_router.get("/docs/page", summary="One document", response_class=HTMLResponse)
def docs_page_view(
    request: Request, principal: CurrentOperator, path: str = Query(...)
) -> HTMLResponse:
    root = resolve_docs_root(request.app.state.settings)
    resolved = resolve_doc_path(root, path)
    page: DocPage = render_markdown(root, resolved)
    return _docs_page(request, principal, "docs_page.html", page=page, path=path, nav_footer=path)


@ui_router.get("/docs/search", summary="Search results", response_class=HTMLResponse)
def docs_search_view(
    request: Request, principal: CurrentOperator, q: str = Query(default="")
) -> HTMLResponse:
    result = search_index(request.app.state.database, q) if q.strip() else None
    return _docs_page(request, principal, "docs_search.html", q=q, result=result)


@ui_router.get("/docs/adrs", summary="The ADR index", response_class=HTMLResponse)
def docs_adrs_view(request: Request, principal: CurrentOperator) -> HTMLResponse:
    root = resolve_docs_root(request.app.state.settings)
    rows = parse_adr_index(root)
    return _docs_page(request, principal, "docs_adrs.html", rows=rows)
