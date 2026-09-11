"""weightroom.web.routes.loadcoach — LoadCoach's pages under its tab (row WP2).

Models, Routing (with the task profiles), Queue and its jobs, Evidence, Reliability, Adapters and
Providers, at parity with LoadCoach's own UI (its ``web/templates``), which a browser on the LAN
cannot reach: LoadCoach binds loopback (ADR-0126). Every page reads by spec §7.3's rule
(``services/app_pages``) through the readers in ``services/loadcoach_pages`` and renders through
``render_app_page``.

Every action is a form post writing exactly one audit row whether LoadCoach accepts or refuses
(spec §11 contract 2). A refusal renders on the page it came from, in LoadCoach's own words.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Annotated, Any

from baseaicore import SuiteError
from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from weightroom.services import loadcoach_actions as actions
from weightroom.services import loadcoach_pages as lc
from weightroom.services.audit import record
from weightroom.web.routes.apps import app_view, back_to, read_app_page, render_app_page
from weightroom.web.session import CurrentOperator, now_of

if TYPE_CHECKING:
    from weightroom.services.auth import Principal

__all__ = ["ui_router"]

ui_router = APIRouter(tags=["ui"], include_in_schema=False)

APP = lc.APP
BASE = "/apps/loadcoach"


class ModelRefInvalid(SuiteError):
    """A model reference that is not a ULID or a prefix of one; nothing was sent (ADR-0024)."""

    code = "VALIDATION_ERROR"


def _model_ref(value: str) -> str:
    """``value`` when it can only name a registry row: letters and digits, as a ULID is."""
    if not value or not value.isalnum():
        message = f"{value!r} is not a model reference: LoadCoach names a model by its ULID."
        raise ModelRefInvalid(message, details={"model_ref": value})
    return value


def _audit(  # noqa: PLR0913 — every field of one audit row
    request: Request,
    principal: Principal,
    action: str,
    *,
    target: str | None,
    outcome: str,
    params: Mapping[str, Any],
    message: str | None = None,
    security: bool = False,
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
        security=security,
        request_id=getattr(request.state, "request_id", None),
    )


def _clients(request: Request) -> tuple[Any, Any]:
    return request.app.state.http, request.app.state.settings


# --- Models ---------------------------------------------------------------------------------------


def _models(
    request: Request,
    principal: Principal,
    *,
    action_error: SuiteError | None = None,
    scanned: Mapping[str, Any] | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request, view, api=lambda: lc.models_api(client, settings), database=lc.models_db
    )
    return render_app_page(
        request,
        principal,
        APP,
        "lc_models.html",
        selected="Models",
        view=view,
        sourced=sourced,
        action_error=action_error,
        scanned=scanned,
    )


@ui_router.get(f"{BASE}/models", summary="Models", response_class=HTMLResponse)
def models_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """Every model discovery has seen, with evidence, reliability, residency and its switches."""
    return _models(request, principal)


@ui_router.post(f"{BASE}/models/discover", summary="Scan for models from the page")
def discover_from_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """``POST /models/discover``; the page again, with the pass's counts above the registry."""
    client, settings = _clients(request)
    try:
        outcome = actions.discover(client, settings)
    except SuiteError as exc:
        _audit(
            request, principal, "loadcoach.discover", target=None, outcome="refused", params={},
            message=exc.message,
        )  # fmt: skip
        return _models(request, principal, action_error=exc)
    counts = {key: outcome.get(key) for key in ("added", "updated", "unavailable", "total")}
    _audit(request, principal, "loadcoach.discover", target=None, outcome="ok", params=counts)
    return _models(request, principal, scanned=outcome)


@ui_router.post(f"{BASE}/models/{{model_ref}}/enabled", summary="Enable or disable from the page")
def enabled_from_page(  # noqa: PLR0913 — one parameter per form field
    request: Request,
    principal: CurrentOperator,
    model_ref: str,
    enabled: Annotated[str, Form()] = "",
    canonical_id: Annotated[str, Form()] = "",
    next_path: Annotated[str | None, Form(alias="next")] = None,
) -> Response:
    """ADR-0118's switch: a disabled model is kept, with its evidence, and routed around by name."""
    wanted = enabled == "true"
    params = {"app": APP, "enabled": wanted, "model_ref": model_ref}
    client, settings = _clients(request)
    try:
        actions.set_enabled(client, settings, _model_ref(model_ref), enabled=wanted)
    except SuiteError as exc:
        _audit(
            request, principal, "catalog.enabled", target=canonical_id or model_ref,
            outcome="refused", params=params, message=exc.message,
        )  # fmt: skip
        return _models(request, principal, action_error=exc)
    _audit(
        request, principal, "catalog.enabled", target=canonical_id or model_ref, outcome="ok",
        params=params,
    )  # fmt: skip
    return RedirectResponse(back_to(APP, next_path), status_code=status.HTTP_303_SEE_OTHER)


@ui_router.post(f"{BASE}/models/{{model_ref}}/warm", summary="Warm a model from the page")
def warm_from_page(
    request: Request,
    principal: CurrentOperator,
    model_ref: str,
    canonical_id: Annotated[str, Form()] = "",
) -> Response:
    """``POST /models/{ref}/warm``; the job it enqueued, which is where the loading shows."""
    client, settings = _clients(request)
    try:
        outcome = actions.warm(client, settings, _model_ref(model_ref))
    except SuiteError as exc:
        _audit(
            request, principal, "loadcoach.warm", target=canonical_id or model_ref,
            outcome="refused", params={"model_ref": model_ref}, message=exc.message,
        )  # fmt: skip
        return _models(request, principal, action_error=exc)
    job_id = str(outcome.get("job_id") or "")
    _audit(
        request, principal, "loadcoach.warm", target=canonical_id or model_ref, outcome="ok",
        params={"model_ref": model_ref, "job_id": job_id or None},
    )  # fmt: skip
    location = f"{BASE}/queue/jobs/{lc.segment(job_id)}" if job_id else f"{BASE}/models"
    return RedirectResponse(location, status_code=status.HTTP_303_SEE_OTHER)


@ui_router.get(f"{BASE}/models/{{model_ref}}", summary="One model", response_class=HTMLResponse)
def model_page(request: Request, principal: CurrentOperator, model_ref: str) -> HTMLResponse:
    """One model: identity, descriptor, evidence per capability, reliability, the breaker."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: lc.model_api(client, settings, model_ref),
        database=lambda handle: lc.model_db(handle, model_ref),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "lc_model.html",
        selected="Models",
        view=view,
        sourced=sourced,
        model_ref=model_ref,
    )


# --- Routing --------------------------------------------------------------------------------------


def _routing(
    request: Request,
    principal: Principal,
    *,
    explained: Mapping[str, Any] | None = None,
    explain_error: SuiteError | None = None,
    form: Mapping[str, Any] | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    decisions = read_app_page(
        request, view, api=lambda: lc.decisions_api(client, settings), database=lc.decisions_db
    )
    profiles = read_app_page(
        request,
        view,
        api=lambda: lc.task_profiles_api(client, settings),
        database=lc.task_profiles_db,
    )
    models = read_app_page(
        request, view, api=lambda: lc.models_api(client, settings), database=None
    )
    return render_app_page(
        request,
        principal,
        APP,
        "lc_routing.html",
        selected="Routing",
        view=view,
        decisions=decisions,
        profiles=profiles,
        models=models.data or [],
        explained=explained,
        explain_error=explain_error,
        form=dict(form or {}),
        runtime_fields=actions.RUNTIME_PROFILE_FIELDS,
    )


@ui_router.get(f"{BASE}/routing", summary="Routing", response_class=HTMLResponse)
def routing_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The explain form, the decision history, and the task profiles routing ranks against."""
    return _routing(request, principal)


@ui_router.post(f"{BASE}/routing", summary="Explain a route from the page")
def explain_from_page(  # noqa: PLR0913 — one parameter per form field, as FastAPI reads them
    request: Request,
    principal: CurrentOperator,
    task: Annotated[str, Form()] = "",
    estimated_input_tokens: Annotated[str, Form()] = "",
    max_output_tokens: Annotated[str, Form()] = "",
    requires_capabilities: Annotated[str, Form()] = "",
    model: Annotated[str, Form()] = "",
    adapter: Annotated[str, Form()] = "",
    context_size: Annotated[str, Form()] = "",
    gpu_layers: Annotated[str, Form()] = "",
    threads: Annotated[str, Form()] = "",
    batch_size: Annotated[str, Form()] = "",
    kv_cache_precision: Annotated[str, Form()] = "",
    keep_alive: Annotated[str, Form()] = "",
    flash_attention: Annotated[str, Form()] = "",
    disallow_fallback: Annotated[str, Form()] = "",
    require_evidence: Annotated[str, Form()] = "",
    ignore_residency: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """``POST /route``: every candidate and every rejection by its code, nothing executed.

    LoadCoach persists the decision, so the call is an action and writes its audit row.
    """
    runtime_profile = {
        "context_size": context_size,
        "gpu_layers": gpu_layers,
        "threads": threads,
        "batch_size": batch_size,
        "kv_cache_precision": kv_cache_precision,
        "keep_alive": keep_alive,
        "flash_attention": flash_attention,
    }
    form = {
        "task": task,
        "estimated_input_tokens": estimated_input_tokens,
        "max_output_tokens": max_output_tokens,
        "requires_capabilities": requires_capabilities,
        "model": model,
        "adapter": adapter,
        **runtime_profile,
        "disallow_fallback": disallow_fallback,
        "require_evidence": require_evidence,
        "ignore_residency": ignore_residency,
    }
    params = {"task": task or None, "model": model or None, "adapter": adapter or None}
    client, settings = _clients(request)
    try:
        body = actions.route_body(
            task=task,
            estimated_input_tokens=estimated_input_tokens,
            max_output_tokens=max_output_tokens,
            requires_capabilities=requires_capabilities,
            model=model,
            adapter=adapter,
            runtime_profile=runtime_profile,
            disallow_fallback=bool(disallow_fallback),
            require_evidence=bool(require_evidence),
            ignore_residency=bool(ignore_residency),
        )
        explained = actions.explain(client, settings, body)
    except SuiteError as exc:
        _audit(
            request, principal, "loadcoach.route", target=task or None, outcome="refused",
            params=params, message=exc.message,
        )  # fmt: skip
        return _routing(request, principal, explain_error=exc, form=form)
    _audit(
        request, principal, "loadcoach.route", target=task or None, outcome="ok",
        params={**params, "decision_id": explained.get("decision_id")},
    )  # fmt: skip
    return _routing(request, principal, explained=explained, form=form)


@ui_router.get(
    f"{BASE}/routing/decisions/{{decision_id}}", summary="One decision", response_class=HTMLResponse
)
def decision_page(request: Request, principal: CurrentOperator, decision_id: str) -> HTMLResponse:
    """One stored routing explanation: the selection, every candidate's numbers, every rejection."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: lc.decision_api(client, settings, decision_id),
        database=lambda handle: lc.decision_db(handle, decision_id),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "lc_decision.html",
        selected="Routing",
        view=view,
        sourced=sourced,
        decision_id=decision_id,
    )


@ui_router.get(
    f"{BASE}/routing/task-profiles/{{task}}",
    summary="One task profile",
    response_class=HTMLResponse,
)
def task_profile_page(request: Request, principal: CurrentOperator, task: str) -> HTMLResponse:
    """One task profile: weights, constraints, execution and validation policy.

    The parameter is ``task``, the name ``POST /route`` gives a profile id: the checklist reads any
    parameter spelled with ``file`` in it as a filesystem path (spec §14).
    """
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: lc.task_profile_api(client, settings, task),
        database=lambda handle: lc.task_profile_db(handle, task),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "lc_task_profile.html",
        selected="Routing",
        view=view,
        sourced=sourced,
        profile_id=task,
    )


# --- Reliability ----------------------------------------------------------------------------------


@ui_router.get(f"{BASE}/reliability", summary="Reliability", response_class=HTMLResponse)
def reliability_page(
    request: Request,
    principal: CurrentOperator,
    task: str | None = None,
    model: str | None = None,
) -> HTMLResponse:
    """Production evidence per model and task profile: windows, factor, regression, breaker."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    wanted_task, wanted_model = task or None, model or None
    sourced = read_app_page(
        request,
        view,
        api=lambda: lc.reliability_api(client, settings, task=wanted_task, model=wanted_model),
        database=lambda handle: lc.reliability_db(handle, task=wanted_task, model=wanted_model),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "lc_reliability.html",
        selected="Reliability",
        view=view,
        sourced=sourced,
        task=wanted_task or "",
        model=wanted_model or "",
    )
