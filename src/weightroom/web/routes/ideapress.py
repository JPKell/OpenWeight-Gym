"""weightroom.web.routes.ideapress — IdeaPress's pages under its tab (row WP5).

Projects, Workflows and Backends, at parity with IdeaPress's own ``web/templates`` and routes, which
a browser on the LAN cannot reach: IdeaPress binds loopback (ADR-0126). Every page reads by spec
§7.3's rule (``services/app_pages``) through the readers in ``services/ideapress_pages`` and
renders through ``render_app_page``.

Every action is a form post writing exactly one audit row whether IdeaPress accepts or refuses
(spec §11 contract 2). A refusal renders on the page it came from, in IdeaPress's own words, with
what the operator typed kept. No row carries a brief, a title or author material: those are the
author's text.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Annotated, Any
from urllib.parse import urlencode

from baseaicore import SuiteError
from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from weightroom.services import ideapress_actions as actions
from weightroom.services import ideapress_pages as ip
from weightroom.services.audit import record
from weightroom.web.routes.apps import app_view, read_app_page, render_app_page
from weightroom.web.session import CurrentOperator, now_of

if TYPE_CHECKING:
    from weightroom.services.auth import Principal

__all__ = ["ui_router"]

ui_router = APIRouter(tags=["ui"], include_in_schema=False)

APP = ip.APP
BASE = "/apps/ideapress"


def _audit(  # noqa: PLR0913 — every field of one audit row
    request: Request,
    principal: Principal,
    action: str,
    *,
    target: str | None,
    outcome: str,
    params: Mapping[str, Any],
    message: str | None = None,
) -> None:
    record(
        request.app.state.database,
        action=action,
        actor="operator",
        outcome=outcome,
        now=now_of(request),
        operator_id=principal.operator_id,
        app=APP,
        target=target,
        params=dict(params),
        message=message,
        request_id=getattr(request.state, "request_id", None),
    )


def _clients(request: Request) -> tuple[Any, Any]:
    return request.app.state.http, request.app.state.settings


def _href(path: str, **query: Any) -> str:
    """``path`` with the query parameters that carry a value, so a pager keeps the filters."""
    kept = {key: value for key, value in query.items() if value not in (None, "", False)}
    return f"{path}?{urlencode(kept)}" if kept else path


def _optional[T](read: Callable[[], T]) -> T | None:
    """A second read a page can live without: its refusal hides a control, never the page."""
    try:
        return read()
    except SuiteError:
        return None


# --- Projects -------------------------------------------------------------------------------------


def _projects(  # noqa: PLR0913 — the list's filters, and what the last action left
    request: Request,
    principal: Principal,
    *,
    project_status: str | None = None,
    content_type: str | None = None,
    archived: bool = False,
    cursor: str | None = None,
    page: int = 1,
    deleted: str | None = None,
    archive_path: str | None = None,
    create_error: SuiteError | None = None,
    form: Mapping[str, Any] | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: ip.projects_api(
            client, settings, status=project_status, content_type=content_type,
            archived=archived, cursor=cursor,
        ),
        database=lambda handle: ip.projects_db(
            handle, status=project_status, content_type=content_type, archived=archived, page=page
        ),
    )  # fmt: skip
    data = sourced.data or {}
    filters = {"status": project_status, "content_type": content_type, "archived": archived}
    next_href = None
    if data.get("next_cursor"):
        next_href = _href(f"{BASE}/projects", **filters, cursor=data["next_cursor"])
    elif data.get("next_page"):
        next_href = _href(f"{BASE}/projects", **filters, page=data["next_page"])
    workflows = _optional(lambda: ip.workflows_api(client, settings)) if sourced.live else None
    return render_app_page(
        request,
        principal,
        APP,
        "ip_projects.html",
        selected="Projects",
        view=view,
        sourced=sourced,
        project_status=project_status or "",
        content_type=content_type or "",
        archived=archived,
        next_href=next_href,
        workflows=workflows,
        deleted=deleted,
        archive_path=archive_path,
        create_error=create_error,
        form=dict(form or {}),
    )


@ui_router.get(f"{BASE}/projects", summary="Projects", response_class=HTMLResponse)
def projects_page(  # noqa: PLR0913 — one parameter per query field
    request: Request,
    principal: CurrentOperator,
    project_status: Annotated[str | None, Query(alias="status")] = None,
    content_type: str | None = None,
    archived: bool = False,
    cursor: str | None = None,
    page: int = 1,
    deleted: str | None = None,
    archive: str | None = None,
) -> HTMLResponse:
    """Every project, newest activity first, by status and content type; and the create form."""
    return _projects(
        request, principal, project_status=project_status or None,
        content_type=content_type or None, archived=archived, cursor=cursor or None, page=page,
        deleted=deleted, archive_path=archive,
    )  # fmt: skip


@ui_router.post(f"{BASE}/projects", summary="Create a project from the page")
def create_from_page(  # noqa: PLR0913 — one parameter per form field
    request: Request,
    principal: CurrentOperator,
    title: Annotated[str, Form()] = "",
    content_type: Annotated[str, Form()] = "article",
    workflow_id: Annotated[str, Form()] = "standard",
    brief: Annotated[str, Form()] = "",
    author_material: Annotated[str, Form()] = "",
) -> Response:
    """``POST /projects``; the new project on success, the form and its refusal otherwise."""
    form = {
        "title": title, "content_type": content_type, "workflow_id": workflow_id, "brief": brief,
        "author_material": author_material,
    }  # fmt: skip
    params = {
        "content_type": content_type or "article",
        "workflow_id": workflow_id or "standard",
        "has_brief": bool(brief.strip()),
        "has_author_material": bool(author_material.strip()),
    }
    client, settings = _clients(request)
    try:
        created = actions.create_project(
            client, settings, title=title, content_type=content_type, workflow_id=workflow_id,
            brief=brief, author_material_text=author_material,
        )  # fmt: skip
    except SuiteError as exc:
        _audit(
            request, principal, "ideapress.project_create", target=None, outcome="refused",
            params=params, message=exc.message,
        )  # fmt: skip
        return _projects(request, principal, create_error=exc, form=form)
    project_id = str(created.get("id") or "")
    _audit(
        request, principal, "ideapress.project_create", target=project_id or None, outcome="ok",
        params=params,
    )  # fmt: skip
    location = f"{BASE}/projects/{ip.segment(project_id)}" if project_id else f"{BASE}/projects"
    return RedirectResponse(location, status_code=status.HTTP_303_SEE_OTHER)


def _project(  # noqa: PLR0913 — the page, and what the last action left on it
    request: Request,
    principal: Principal,
    project_id: str,
    *,
    action_error: SuiteError | None = None,
    form: Mapping[str, Any] | None = None,
    preview: Mapping[str, Any] | None = None,
    mismatched: bool = False,
    saved: bool = False,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: ip.project_api(client, settings, project_id),
        database=lambda handle: ip.project_db(handle, project_id),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "ip_project.html",
        selected="Projects",
        view=view,
        sourced=sourced,
        project_id=project_id,
        action_error=action_error,
        form=dict(form or {}),
        preview=dict(preview) if preview is not None else None,
        mismatched=mismatched,
        saved=saved,
    )


@ui_router.get(
    f"{BASE}/projects/{{project_id}}", summary="One project", response_class=HTMLResponse
)
def project_page(
    request: Request, principal: CurrentOperator, project_id: str, saved: bool = False
) -> HTMLResponse:
    """One project: its fields, brief, plan summary, unit states and stage history."""
    return _project(request, principal, project_id, saved=saved)


@ui_router.post(f"{BASE}/projects/{{project_id}}/edit", summary="Edit a project from the page")
def edit_from_page(  # noqa: PLR0913 — one parameter per form field
    request: Request,
    principal: CurrentOperator,
    project_id: str,
    title: Annotated[str, Form()] = "",
    brief: Annotated[str, Form()] = "",
    author_material: Annotated[str, Form()] = "",
    project_status: Annotated[str, Form(alias="status")] = "",
) -> Response:
    """``PUT /projects/{id}``. Saving never recompiles requirements; the plan does, when run."""
    form = {
        "title": title, "brief": brief, "author_material": author_material,
        "status": project_status,
    }  # fmt: skip
    params = {"status": project_status or None, "has_brief": bool(brief.strip())}
    client, settings = _clients(request)
    try:
        actions.update_project(
            client, settings, project_id, title=title, brief=brief,
            author_material_text=author_material, status=project_status,
        )  # fmt: skip
    except SuiteError as exc:
        _audit(
            request, principal, "ideapress.project_update", target=project_id, outcome="refused",
            params=params, message=exc.message,
        )  # fmt: skip
        return _project(request, principal, project_id, action_error=exc, form=form)
    _audit(
        request, principal, "ideapress.project_update", target=project_id, outcome="ok",
        params=params,
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{BASE}/projects/{ip.segment(project_id)}", saved=True),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@ui_router.post(f"{BASE}/projects/{{project_id}}/delete", summary="Delete a project from the page")
def delete_from_page(
    request: Request,
    principal: CurrentOperator,
    project_id: str,
    confirm: Annotated[str, Form()] = "",
    archive: Annotated[str, Form()] = "",
) -> Response:
    """IdeaPress's delete preview first; the delete only once the project's title is typed.

    The preview is IdeaPress's own (``DELETE`` without ``confirm``) and is a ``pending`` row. The
    title is compared with the one IdeaPress answers, never a hidden field. Archiving first writes
    the project's archive before IdeaPress removes anything, and an archive that cannot be written
    deletes nothing.
    """
    client, settings = _clients(request)
    archiving = archive == "true"
    typed = confirm.strip()
    title = ""
    try:
        current = ip.project_api(client, settings, project_id)["project"]
        title = str(current.get("title") or "")
        if not typed or typed != title:
            preview = actions.delete_project(
                client, settings, project_id, confirm=False, archive=archiving
            )
            _audit(
                request, principal, "ideapress.project_delete", target=project_id,
                outcome="pending", params={"preview": True, "archive": archiving},
            )  # fmt: skip
            return _project(request, principal, project_id, preview=preview, mismatched=bool(typed))
        result = actions.delete_project(
            client, settings, project_id, confirm=True, archive=archiving
        )
    except SuiteError as exc:
        _audit(
            request, principal, "ideapress.project_delete", target=project_id, outcome="refused",
            params={"preview": not typed, "archive": archiving}, message=exc.message,
        )  # fmt: skip
        return _project(request, principal, project_id, action_error=exc)
    written = result.get("archive")
    path = written.get("path") if isinstance(written, Mapping) else None
    _audit(
        request, principal, "ideapress.project_delete", target=project_id, outcome="ok",
        params={"preview": False, "archive": archiving, "archived": path is not None},
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{BASE}/projects", deleted=title, archive=path),
        status_code=status.HTTP_303_SEE_OTHER,
    )


# --- Workflows ------------------------------------------------------------------------------------


@ui_router.get(f"{BASE}/workflows", summary="Workflows", response_class=HTMLResponse)
def workflows_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """Every workflow's stage order and gates, with the limits and bindings a run would use."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request, view, api=lambda: ip.workflows_api(client, settings), database=None
    )
    defaults = _optional(lambda: ip.settings_api(client, settings)) if sourced.live else None
    return render_app_page(
        request, principal, APP, "ip_workflows.html", selected="Workflows", view=view,
        sourced=sourced, defaults=defaults, workflow_id=None,
    )  # fmt: skip


@ui_router.get(
    f"{BASE}/workflows/{{workflow_id}}", summary="One workflow", response_class=HTMLResponse
)
def workflow_page(request: Request, principal: CurrentOperator, workflow_id: str) -> HTMLResponse:
    """One workflow: its stages in order, which use a model and its binding, and its gates."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: {"workflows": [ip.workflow_api(client, settings, workflow_id)["workflow"]]},
        database=None,
    )
    defaults = _optional(lambda: ip.settings_api(client, settings)) if sourced.live else None
    return render_app_page(
        request, principal, APP, "ip_workflows.html", selected="Workflows", view=view,
        sourced=sourced, defaults=defaults, workflow_id=workflow_id,
    )  # fmt: skip


# --- Backends -------------------------------------------------------------------------------------


def _backends(
    request: Request,
    principal: Principal,
    *,
    tested: Mapping[str, Any] | None = None,
    action_error: SuiteError | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request, view, api=lambda: ip.backends_api(client, settings), database=None
    )
    return render_app_page(
        request, principal, APP, "ip_backends.html", selected="Backends", view=view,
        sourced=sourced, tested=dict(tested) if tested is not None else None,
        action_error=action_error,
    )  # fmt: skip


@ui_router.get(f"{BASE}/backends", summary="Backends", response_class=HTMLResponse)
def backends_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """Each configured backend: mode, reachability, capabilities, and where content goes."""
    return _backends(request, principal)


@ui_router.post(f"{BASE}/backends/test", summary="Test a backend from the page")
def test_from_page(
    request: Request, principal: CurrentOperator, mode: Annotated[str, Form()] = ""
) -> HTMLResponse:
    """``POST /backends/test``: the round trip's latency, model list and version, on the page."""
    client, settings = _clients(request)
    try:
        tested = actions.test_backend(client, settings, mode)
    except SuiteError as exc:
        _audit(
            request, principal, "ideapress.backend_test", target=mode or None, outcome="refused",
            params={"mode": mode or None}, message=exc.message,
        )  # fmt: skip
        return _backends(request, principal, action_error=exc)
    _audit(
        request, principal, "ideapress.backend_test", target=str(tested.get("mode") or mode or "")
        or None, outcome="ok",
        params={
            "mode": tested.get("mode"), "status": tested.get("status"),
            "latency_ms": tested.get("latency_ms"),
        },
    )  # fmt: skip
    return _backends(request, principal, tested=tested)
