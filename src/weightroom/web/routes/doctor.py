"""weightroom.web.routes.doctor — one page and one JSON body for the whole machine.

The doctor reads; it never writes and never elevates. Every fix it knows is **printed** next to
the finding that needs it, because the ones that matter most edit a file under ``/etc`` and this
console is not root (ADR-0125 rules 4–5).

It is a ``GET``, so it leaves no audit row: nothing changed.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from weightroom.domain.units import UNIT_APPLICATIONS
from weightroom.services.doctor import Report, diagnose
from weightroom.services.settings_forms import read_schema_document, settings_form
from weightroom.web.session import CurrentOperator

if TYPE_CHECKING:
    from weightroom.services.settings_forms import SettingsForm

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["doctor"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)


def _report(request: Request) -> Report:
    """Every rule, over the forms and views this console already reads for its other pages."""
    from weightroom.web.routes.apps import views_for_request

    state = request.app.state
    forms: dict[str, SettingsForm] = {}
    for app in UNIT_APPLICATIONS:
        document, error = state.schemas.get(
            app,
            now=time.monotonic(),
            read=lambda app=app: read_schema_document(
                state.settings, app, config_path=state.config_path
            ),
        )
        forms[app] = settings_form(
            state.settings,
            app,
            document=document,
            document_error=error,
            config_path=state.config_path if app == "weightroom" else None,
        )
    return diagnose(
        state.settings,
        controller=state.controller,
        forms=forms,
        views=views_for_request(request),
        tls=state.tls,
        database=state.database,
        client=state.ollama_http,
    )


@router.get("/doctor", summary="Diagnose the host against the suite's own documents")
def get_doctor(request: Request, principal: CurrentOperator) -> JSONResponse:
    """Every finding, worst first, each with its evidence and the command that fixes it."""
    return JSONResponse(content=_report(request).as_json())


@ui_router.get("/doctor", summary="The Doctor page", response_class=HTMLResponse)
def doctor_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The same findings, rendered."""
    from weightroom.web.routes.apps import render_shell_page

    report = _report(request)
    return render_shell_page(
        request,
        "doctor.html",
        page="doctor",
        principal=principal,
        report=report,
    )
