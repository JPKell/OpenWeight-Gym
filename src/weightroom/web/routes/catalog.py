"""weightroom.web.routes.catalog — the model catalog (spec §7.9, api.md §5).

Every route leaves exactly one ``catalog.*`` audit row whatever happens (spec §11 contract 2):
``catalog.pull`` when a pull starts, ``catalog.enabled`` for an enable/disable, ``catalog.dropin``
for a GGUF drop-in, ``catalog.delete`` for both a preview and a confirmed removal (a preview
changes nothing but is the row that shows what was about to happen). A refusal is audited too, as
``outcome: "refused"`` — the same discipline ``web/routes/databases.py`` uses.

``{ref}`` is the catalog's canonical id, which contains ``/`` (ADR-0008) — a plain FastAPI path
parameter never sees past the first one, so ``enable`` and the delete route both take
``{ref:path}``, which matches the rest of the path literally, encoded or not (found writing this
row's own audit exercise: a percent-encoded ``/`` is still a segment boundary to the default
converter).
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Final

from baseaicore import SuiteError
from fastapi import APIRouter, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from weightroom.services.audit import record
from weightroom.services.auth import Principal, require_fresh_reauth
from weightroom.services.catalog import (
    CatalogDeletePreview,
    CatalogDeleteResult,
    CatalogDropinRefused,
    CatalogEntry,
    CatalogRefused,
    DropinResult,
    PullJob,
    PullRegistry,
    catalog_delete_confirm,
    catalog_delete_preview,
    catalog_entries,
    find_entry,
    perform_dropin_path,
    perform_dropin_stream,
    set_enabled,
)
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator, now_of, reauthenticated

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["catalog"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)

_HEARTBEAT_SECONDS: Final = 15.0
_POLL_SECONDS: Final = 0.25


class EnabledBody(BaseModel):
    """``POST /catalog/{ref}/enabled`` (api.md §5)."""

    model_config = ConfigDict(extra="forbid")

    app: str = Field(max_length=32)
    enabled: bool


class PullBody(BaseModel):
    """``POST /catalog/pull`` (api.md §5)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=256)


class DeleteBody(BaseModel):
    """``DELETE /catalog/{ref}`` (api.md §5): preview first, then a typed, re-authenticated
    confirm."""

    model_config = ConfigDict(extra="forbid")

    preview: bool = False
    confirm: str = Field(default="", max_length=256)
    token: str = Field(default="", max_length=4096)


def _entries(request: Request) -> tuple[CatalogEntry, ...]:
    state = request.app.state
    return catalog_entries(
        state.settings,
        state.database,
        urls=state.database_urls,
        monotonic=time.monotonic(),
        ollama_client=state.ollama_http,
    )


def _audit(
    request: Request,
    principal: Principal,
    action: str,
    target: str,
    *,
    outcome: str = "ok",
    message: str | None = None,
    **fields: Any,
) -> None:
    record(
        request.app.state.database,
        action=action,
        actor="operator",
        outcome=outcome,
        now=now_of(request),
        operator_id=principal.operator_id,
        target=target,
        message=message,
        request_id=getattr(request.state, "request_id", None),
        **fields,
    )


@router.get("/catalog", summary="Every model FreeWeight and LoadCoach know, joined by identity")
def get_catalog(request: Request, principal: CurrentOperator) -> JSONResponse:
    """The join, live — no second registry (spec §7.9)."""
    return JSONResponse(content={"models": [entry.as_json() for entry in _entries(request)]})


@router.post(
    "/catalog/pull", status_code=status.HTTP_202_ACCEPTED, summary="Pull a model through Ollama"
)
def post_pull(request: Request, principal: CurrentOperator, body: PullBody) -> JSONResponse:
    """Starts in a thread (module docstring); the job id opens ``…/pull/{id}/stream``."""
    job = _start_pull(request, principal, body.name)
    return JSONResponse(content={"job_id": job.id, "name": job.name}, status_code=202)


def _start_pull(request: Request, principal: Principal, name: str) -> PullJob:
    """Starting a pull never fails here — Ollama's own answer arrives in the stream — so this
    always audits ``ok``."""
    state = request.app.state
    catalog_pulls: PullRegistry = state.catalog_pulls
    job = catalog_pulls.start(
        name, client=state.ollama_http, base_url=state.settings.host.ollama_base_url
    )
    _audit(request, principal, "catalog.pull", name, params={"job_id": job.id})
    return job


async def _pull_frames(request: Request, job_id: str, *, after: int) -> Any:
    import asyncio

    from weightroom.services.chat import heartbeat_frame, sse_frame

    job = request.app.state.catalog_pulls.get(job_id)
    if job is None:
        yield sse_frame(after + 1, "error", {"message": f"no pull job {job_id} in this process"})
        return
    last = after
    next_heartbeat = time.monotonic() + _HEARTBEAT_SECONDS
    while not await request.is_disconnected():
        events = job.events_after(last)
        for event in events:
            yield sse_frame(event.id, "pull", event.as_json())
            last = event.id
            next_heartbeat = time.monotonic() + _HEARTBEAT_SECONDS
        if job.finished and last >= len(job.events):
            yield sse_frame(last + 1, "done", {"ok": job.ok})
            return
        if not events:
            if time.monotonic() >= next_heartbeat:
                yield heartbeat_frame()
                next_heartbeat = time.monotonic() + _HEARTBEAT_SECONDS
            await asyncio.sleep(_POLL_SECONDS)


@router.get("/catalog/pull/{job_id}/stream", summary="One pull's progress")
def get_pull_stream(
    request: Request, principal: CurrentOperator, job_id: str, last_event_id: str | None = None
) -> StreamingResponse:
    """SSE of :class:`~weightroom.services.catalog.PullEvent` rows, in-memory only (module
    docstring) — replayable within this process's lifetime, not across a restart."""
    raw = request.headers.get("last-event-id") or last_event_id or "0"
    after = int(raw) if raw.isdigit() else 0
    return StreamingResponse(
        _pull_frames(request, job_id, after=after),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )


def _dropin(
    request: Request, principal: Principal, *, file: UploadFile | None, path: str
) -> DropinResult:
    """One ``catalog.dropin`` row whatever happens — refused (bad magic, oversize, no shared
    directory) or done."""
    state = request.app.state
    source = (file.filename if file is not None else None) or path.strip() or "(no source given)"
    try:
        if file is not None and file.filename:
            result = perform_dropin_stream(
                state.settings, filename=file.filename, stream=file.file, client=state.http
            )
        elif path.strip():
            result = perform_dropin_path(state.settings, source=path.strip(), client=state.http)
        else:
            raise CatalogDropinRefused("Give a file to upload or a path already on the host.")
    except SuiteError as exc:
        _audit(request, principal, "catalog.dropin", source, outcome="refused", message=exc.message)
        raise
    _audit(
        request,
        principal,
        "catalog.dropin",
        source,
        params={
            "path": str(result.destination),
            "size_bytes": result.size_bytes,
            "refreshed": list(result.refreshed),
        },
    )
    return result


@router.post("/catalog/dropin", summary="Copy a GGUF file into the configured model directory")
async def post_dropin(
    request: Request,
    principal: CurrentOperator,
    file: Annotated[UploadFile | None, File()] = None,
    path: Annotated[str, Form()] = "",
) -> JSONResponse:
    """A multipart upload, or ``path`` naming a file already on the host (api.md §5)."""
    result = _dropin(request, principal, file=file, path=path)
    return JSONResponse(content=result.as_json())


def _enable(request: Request, principal: Principal, ref: str, *, app: str, enabled: bool) -> None:
    """One ``catalog.enabled`` row whatever happens: an unknown ref or app is a refusal, not a
    silent no-op."""
    try:
        entry = find_entry(_entries(request), ref)
        app_row = entry.apps.get(app)
        if app_row is None:
            raise CatalogRefused(
                f"{app} does not know {ref}.", details={"app": app, "canonical_id": ref}
            )
        state = request.app.state
        set_enabled(state.settings, app, app_row.model_id, enabled=enabled, client=state.http)
    except SuiteError as exc:
        _audit(
            request,
            principal,
            "catalog.enabled",
            ref,
            outcome="refused",
            message=exc.message,
            app=app,
            params={"app": app, "enabled": enabled},
        )
        raise
    _audit(
        request, principal, "catalog.enabled", ref, app=app, params={"app": app, "enabled": enabled}
    )


@router.post("/catalog/{ref:path}/enabled", summary="Enable or disable a model on one application")
def post_enabled(
    request: Request, principal: CurrentOperator, ref: str, body: EnabledBody
) -> JSONResponse:
    """``ref``'s canonical id resolves to that application's own row id (ADR-0118)."""
    _enable(request, principal, ref, app=body.app, enabled=body.enabled)
    return JSONResponse(content={"canonical_id": ref, "app": body.app, "enabled": body.enabled})


def _delete(
    request: Request, principal: Principal, ref: str, *, confirm: str, token: str
) -> CatalogDeletePreview | CatalogDeleteResult:
    """Preview without ``confirm`` (Database Standards §8); a typed, re-authenticated confirm
    removes it. Shared by the JSON route and the page form; one ``catalog.delete`` row either way,
    including for an unknown ref or a failed re-authentication."""
    state = request.app.state
    try:
        entry = find_entry(_entries(request), ref)
        if not confirm:
            preview = catalog_delete_preview(state.settings, entry, client=state.http)
        else:
            require_fresh_reauth(principal, now=now_of(request), auth=state.settings.auth)
            result = catalog_delete_confirm(
                state.settings, entry, typed=confirm, token=token, client=state.http
            )
    except SuiteError as exc:
        _audit(
            request,
            principal,
            "catalog.delete",
            ref,
            outcome="refused",
            message=exc.message,
            security=bool(confirm),
            params={"preview": not confirm},
        )
        raise
    if not confirm:
        _audit(request, principal, "catalog.delete", ref, params={"preview": True})
        return preview
    _audit(request, principal, "catalog.delete", ref, security=True, params={"preview": False})
    return result


@router.delete("/catalog/{ref:path}", summary="Delete a model everywhere, with cleanup")
def delete_catalog_entry(
    request: Request, principal: CurrentOperator, ref: str, body: DeleteBody
) -> JSONResponse:
    """Preview first (``Database Standards §8``); a typed, re-authenticated confirm removes it."""
    outcome = _delete(request, principal, ref, confirm=body.confirm, token=body.token)
    return JSONResponse(content=outcome.as_json())


# --- Page ----------------------------------------------------------------------------------------


def _page(request: Request, principal: Principal, /, **overrides: Any) -> HTMLResponse:
    """The Catalog page, every context key defaulted — the template's ``StrictUndefined`` refuses
    a key no route bothered to pass."""
    context: dict[str, Any] = {
        "catalog_error": None,
        "pull_job": None,
        "dropin_result": None,
        "delete_preview": None,
        "delete_result": None,
        "delete_target": None,
        **overrides,
    }
    return render_shell_page(
        request,
        "catalog.html",
        page="catalog",
        principal=principal,
        models=_entries(request),
        **context,
    )


@ui_router.get("/catalog", summary="The Catalog page", response_class=HTMLResponse)
def catalog_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """Every model, joined; pull, drop-in, enable/disable and delete."""
    return _page(request, principal)


@ui_router.post("/catalog/enable", summary="Enable or disable a model from the page")
def enable_from_page(
    request: Request,
    principal: CurrentOperator,
    canonical_id: Annotated[str, Form()],
    app: Annotated[str, Form()],
    enabled: Annotated[bool, Form()] = False,
) -> HTMLResponse:
    error: SuiteError | None = None
    try:
        _enable(request, principal, canonical_id, app=app, enabled=enabled)
    except SuiteError as exc:
        error = exc
    return _page(request, principal, catalog_error=error)


@ui_router.post("/catalog/pull-form", summary="Start a pull from the page")
def pull_from_page(
    request: Request, principal: CurrentOperator, name: Annotated[str, Form()]
) -> HTMLResponse:
    job = _start_pull(request, principal, name)
    return _page(request, principal, pull_job=job)


@ui_router.post("/catalog/dropin-form", summary="Drop a GGUF file in from the page")
async def dropin_from_page(
    request: Request,
    principal: CurrentOperator,
    file: Annotated[UploadFile | None, File()] = None,
    path: Annotated[str, Form()] = "",
) -> HTMLResponse:
    error: SuiteError | None = None
    result: DropinResult | None = None
    try:
        result = _dropin(request, principal, file=file, path=path)
    except SuiteError as exc:
        error = exc
    return _page(request, principal, catalog_error=error, dropin_result=result)


@ui_router.post("/catalog/delete", summary="Preview or confirm a catalog delete from the page")
def delete_from_page(
    request: Request,
    principal: CurrentOperator,
    canonical_id: Annotated[str, Form()],
    confirm: Annotated[str, Form()] = "",
    token: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
) -> HTMLResponse:
    acting = (reauthenticated(request, principal, password) or principal) if password else principal
    error: SuiteError | None = None
    preview: CatalogDeletePreview | None = None
    result: CatalogDeleteResult | None = None
    try:
        outcome = _delete(request, acting, canonical_id, confirm=confirm, token=token)
        if isinstance(outcome, CatalogDeletePreview):
            preview = outcome
        else:
            result = outcome
    except SuiteError as exc:
        error = exc
    return _page(
        request,
        acting,
        catalog_error=error,
        delete_preview=preview,
        delete_result=result,
        delete_target=canonical_id,
    )
