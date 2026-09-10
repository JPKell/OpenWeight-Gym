"""weightroom.web.routes.ollama — the Ollama pane (api.md §5), read-only but for one button.

ADR-0125 rules 4 and 5. The pane is the ``MEMORY_SAFETY.md`` §2.1 checklist rendered line by
line with what the unit actually says beside what the document asks for, and the fix **printed**:
``docs/scripts/apply_memory_safety.sh``. WeightRoomGym is not root and never invokes ``sudo``.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from weightroom.services.audit import record
from weightroom.services.ollama import (
    POLKIT_INSTALL_COMMAND,
    POLKIT_RULE_PATH,
    OllamaReport,
    OllamaRestartNotPermitted,
    ollama_report,
    polkit_rule_text,
    resident_models,
    restart_ollama,
)
from weightroom.web.routes.apps import render_shell_page
from weightroom.web.session import CurrentOperator

__all__ = ["operator_user", "router", "ui_router"]

router = APIRouter(tags=["ollama"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)


def operator_user() -> str:
    """The OS user this console runs as — whom the polkit rule would name."""
    return os.environ.get("USER") or os.environ.get("LOGNAME") or Path.home().name


def _report(request: Request, *, residency: bool = True) -> OllamaReport:
    state = request.app.state
    return ollama_report(
        state.settings,
        controller=state.controller,
        client=state.ollama_http,
        journal=state.journal,
        database=state.database,
        residency=residency,
    )


@router.get("/ollama", summary="Ollama's unit, the memory-safety checklist and the grant")
def get_ollama(request: Request, principal: CurrentOperator) -> JSONResponse:
    """The unit state, the §2.1 findings, whether the journal is readable and whether a restart
    is permitted as far as the last attempt showed."""
    return JSONResponse(content=_report(request).as_json())


@router.get("/ollama/ps", summary="What Ollama is holding in memory")
def get_ollama_ps(request: Request, principal: CurrentOperator) -> JSONResponse:
    """``/api/ps`` through ModelRack's client. A figure the provider omits is ``null``, not 0."""
    resident, error = resident_models(
        request.app.state.settings, client=request.app.state.ollama_http
    )
    return JSONResponse(
        content={"resident": [entry.as_json() for entry in resident], "error": error}
    )


def _restart(request: Request, principal: CurrentOperator) -> dict[str, object]:
    """Attempt the restart, audit the outcome, and let a refusal carry the rule to install.

    The audit row is the grant probe: ``GET /ollama`` reads the newest one. So it is written
    before the refusal is raised, and it is written as ``refused`` rather than ``failed``, which
    is what makes *not permitted* distinguishable from *the daemon would not come back*.
    """
    state = request.app.state
    settings = state.settings
    request_id = getattr(request.state, "request_id", None)
    try:
        restart_ollama(settings, controller=state.controller, user=operator_user())
    except OllamaRestartNotPermitted as exc:
        record(
            state.database,
            action="ollama.restart",
            actor="operator",
            outcome="refused",
            operator_id=principal.operator_id,
            app="ollama",
            target=settings.host.ollama_unit,
            message=exc.details.get("stderr") or exc.message,
            request_id=request_id,
        )
        raise
    except Exception as exc:
        record(
            state.database,
            action="ollama.restart",
            actor="operator",
            outcome="failed",
            operator_id=principal.operator_id,
            app="ollama",
            target=settings.host.ollama_unit,
            message=str(getattr(exc, "message", exc)),
            request_id=request_id,
        )
        raise
    audit_id = record(
        state.database,
        action="ollama.restart",
        actor="operator",
        outcome="ok",
        operator_id=principal.operator_id,
        app="ollama",
        target=settings.host.ollama_unit,
        request_id=request_id,
    )
    return {"audit_id": audit_id, "unit": settings.host.ollama_unit, "restarted": True}


@router.post("/ollama/restart", status_code=status.HTTP_202_ACCEPTED, summary="Restart Ollama")
def restart(request: Request, principal: CurrentOperator) -> dict[str, object]:
    """Restart the system unit when polkit permits it; otherwise
    ``403 OLLAMA_RESTART_NOT_PERMITTED`` carrying the rule text and the install command."""
    return _restart(request, principal)


@ui_router.get("/ollama", summary="The Ollama pane", response_class=HTMLResponse)
def ollama_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The §2.1 checklist, the residency table, and the restart button or the command."""
    report = _report(request)
    return render_shell_page(
        request,
        "ollama.html",
        page="ollama",
        principal=principal,
        report=report,
        rule_path=POLKIT_RULE_PATH,
        rule_text=polkit_rule_text(operator_user()),
        install_command=POLKIT_INSTALL_COMMAND,
        apply_script=report.apply_script,
    )


@ui_router.post("/ollama/restart", summary="Restart Ollama from the page")
def restart_from_page(request: Request, principal: CurrentOperator) -> Response:
    """The page's button; a refusal renders as the error page with the rule to install."""
    _restart(request, principal)
    return RedirectResponse("/ollama", status_code=status.HTTP_303_SEE_OTHER)
