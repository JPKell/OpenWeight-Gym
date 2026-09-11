"""weightroom.web.routes.freeweight — FreeWeight's pages under its tab (row WP3).

Models, Runs (with one run, its tests' samples and the case inspector), at parity with FreeWeight's
own UI (its ``web/templates``), which a browser on the LAN cannot reach: FreeWeight binds loopback
(ADR-0126). Every page reads by spec §7.3's rule (``services/app_pages``) through the readers in
``services/freeweight_pages`` and renders through ``render_app_page``.

Every action is a form post writing exactly one audit row whether FreeWeight accepts or refuses
(spec §11 contract 2). Starting a run is not a call to FreeWeight's ``POST /runs``: it enqueues W9's
``freeweight_suite_run`` job, which launches the run under ADR-0119's memory cap and is audited as
``job.enqueue``; the page then follows the run FreeWeight reports.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Final
from urllib.parse import urlencode

from baseaicore import SuiteError
from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse

from weightroom.services import freeweight_actions as actions
from weightroom.services import freeweight_pages as fw
from weightroom.services.app_api import stream as app_stream
from weightroom.services.audit import record
from weightroom.services.catalog import set_enabled
from weightroom.web.routes.apps import app_view, back_to, read_app_page, render_app_page
from weightroom.web.routes.jobs import enqueue_job
from weightroom.web.session import CurrentOperator, now_of

if TYPE_CHECKING:
    from weightroom.services.auth import Principal

__all__ = ["ui_router"]

ui_router = APIRouter(tags=["ui"], include_in_schema=False)

APP = fw.APP
BASE = "/apps/freeweight"
SUITE_RUN: Final = "freeweight_suite_run"
_SSE_HEADERS: Final = {"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"}


class ModelRefInvalid(SuiteError):
    """A model reference that is not a ULID or a prefix of one; nothing was sent (ADR-0024)."""

    code: ClassVar[str] = "VALIDATION_ERROR"


def _model_ref(value: str) -> str:
    """``value`` when it can only name a registry row: letters and digits, as a ULID is."""
    if not value or not value.isalnum():
        message = f"{value!r} is not a model reference: FreeWeight names a model by its ULID."
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


def _href(path: str, **query: Any) -> str:
    """``path`` with the query parameters that carry a value, so a pager keeps the filters."""
    kept = {key: value for key, value in query.items() if value not in (None, "")}
    return f"{path}?{urlencode(kept)}" if kept else path


# --- Models ---------------------------------------------------------------------------------------


def _models(
    request: Request,
    principal: Principal,
    *,
    filters: Mapping[str, str | None],
    action_error: SuiteError | None = None,
    scanned: Mapping[str, Any] | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    has_results, sort = filters.get("has_results") or None, filters.get("sort") or None
    sourced = read_app_page(
        request,
        view,
        api=lambda: fw.models_api(client, settings, has_results=has_results, sort=sort),
        database=lambda handle: fw.models_db(handle, sort=sort),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "fw_models.html",
        selected="Models",
        view=view,
        sourced=sourced,
        filters={"has_results": has_results or "", "sort": sort or ""},
        action_error=action_error,
        scanned=scanned,
    )


@ui_router.get(f"{BASE}/models", summary="Models", response_class=HTMLResponse)
def models_page(
    request: Request,
    principal: CurrentOperator,
    has_results: str | None = None,
    sort: str | None = None,
) -> HTMLResponse:
    """Every model identity with its latest descriptor, whether it has results, and its switch."""
    return _models(request, principal, filters={"has_results": has_results, "sort": sort})


@ui_router.post(f"{BASE}/models/discover", summary="Scan for models from the page")
def discover_from_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """``POST /models/discover``; the page again, with the counts FreeWeight returns above it."""
    client, settings = _clients(request)
    try:
        outcome = actions.discover(client, settings)
    except SuiteError as exc:
        _audit(
            request, principal, "freeweight.discover", target=None, outcome="refused", params={},
            message=exc.message,
        )  # fmt: skip
        return _models(request, principal, filters={}, action_error=exc)
    counts = {key: outcome.get(key) for key in ("added", "updated", "unchanged", "total")}
    _audit(request, principal, "freeweight.discover", target=None, outcome="ok", params=counts)
    return _models(request, principal, filters={}, scanned=counts)


@ui_router.post(f"{BASE}/models/{{model_ref}}/enabled", summary="Enable or disable from the page")
def enabled_from_page(  # noqa: PLR0913 — one parameter per form field
    request: Request,
    principal: CurrentOperator,
    model_ref: str,
    enabled: Annotated[str, Form()] = "",
    canonical_id: Annotated[str, Form()] = "",
    next_path: Annotated[str | None, Form(alias="next")] = None,
) -> Response:
    """ADR-0118's switch, through W8's catalog call: a disabled model keeps its results and is
    refused by name as a run's subject."""
    wanted = enabled == "true"
    params = {"app": APP, "enabled": wanted, "model_ref": model_ref}
    client, settings = _clients(request)
    try:
        set_enabled(settings, APP, _model_ref(model_ref), enabled=wanted, client=client)
    except SuiteError as exc:
        _audit(
            request, principal, "catalog.enabled", target=canonical_id or model_ref,
            outcome="refused", params=params, message=exc.message,
        )  # fmt: skip
        return _models(request, principal, filters={}, action_error=exc)
    _audit(
        request, principal, "catalog.enabled", target=canonical_id or model_ref, outcome="ok",
        params=params,
    )  # fmt: skip
    return RedirectResponse(back_to(APP, next_path), status_code=status.HTTP_303_SEE_OTHER)


@ui_router.get(f"{BASE}/models/{{model_ref}}", summary="One model", response_class=HTMLResponse)
def model_page(  # noqa: PLR0913 — the results filters FreeWeight takes
    request: Request,
    principal: CurrentOperator,
    model_ref: str,
    suite: str | None = None,
    runtime_hash: str | None = None,
    cursor: str | None = None,
) -> HTMLResponse:
    """One model: identity, latest descriptor, descriptor history, evidence, and its results.

    The runtime-profile filter is ``runtime_hash`` here, FreeWeight's ``runtime_profile_hash``
    there: the §14 checklist reads any parameter spelled with ``file`` in it as a filesystem path.
    """
    view = app_view(request, APP)
    client, settings = _clients(request)
    wanted = {"suite": suite or None, "runtime_hash": runtime_hash or None}
    sourced = read_app_page(
        request,
        view,
        api=lambda: fw.model_api(
            client, settings, model_ref, suite=wanted["suite"],
            runtime_profile=wanted["runtime_hash"], cursor=cursor or None,
        ),
        database=lambda handle: fw.model_db(handle, model_ref),
    )  # fmt: skip
    following = (sourced.data or {}).get("next_cursor")
    base = f"{BASE}/models/{fw.segment(model_ref)}"
    return render_app_page(
        request,
        principal,
        APP,
        "fw_model.html",
        selected="Models",
        view=view,
        sourced=sourced,
        model_ref=model_ref,
        filters={key: value or "" for key, value in wanted.items()},
        next_href=_href(base, **wanted, cursor=following) + "#results" if following else None,
    )


# --- Runs -----------------------------------------------------------------------------------------


def _runs(  # noqa: PLR0913 — the filters, and what a refused start leaves on the page
    request: Request,
    principal: Principal,
    *,
    filters: Mapping[str, str | None],
    cursor: str | None = None,
    page: int = 1,
    start_error: SuiteError | None = None,
    form: Mapping[str, str] | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    wanted = {key: filters.get(key) or None for key in fw.RUN_FILTERS}
    runs = read_app_page(
        request,
        view,
        api=lambda: fw.runs_api(client, settings, wanted, cursor),
        database=lambda handle: fw.runs_db(handle, wanted, page),
    )
    data = runs.data or {}
    next_href = None
    if data.get("next_cursor"):
        next_href = _href(f"{BASE}/runs", **wanted, cursor=data["next_cursor"])
    elif data.get("next_page"):
        next_href = _href(f"{BASE}/runs", **wanted, page=data["next_page"])
    benchmarks: list[dict[str, Any]] = []
    models: list[dict[str, Any]] = []
    if runs.live:
        benchmarks = (
            read_app_page(
                request, view, api=lambda: fw.benchmarks_api(client, settings), database=None
            ).data
            or []
        )
        models = (
            read_app_page(
                request,
                view,
                api=lambda: fw.models_api(client, settings, has_results=None, sort="canonical_id"),
                database=None,
            ).data
            or []
        )
    return render_app_page(
        request,
        principal,
        APP,
        "fw_runs.html",
        selected="Runs",
        view=view,
        runs=runs,
        filters={key: value or "" for key, value in wanted.items()},
        statuses=fw.RUN_STATUSES,
        next_href=next_href,
        benchmarks=benchmarks,
        models=[one for one in models if one.get("enabled")],
        start_error=start_error,
        form=dict(form or {}),
    )


@ui_router.get(f"{BASE}/runs", summary="Runs", response_class=HTMLResponse)
def runs_page(  # noqa: PLR0913 — one parameter per filter FreeWeight's runs listing takes
    request: Request,
    principal: CurrentOperator,
    status: str | None = None,  # noqa: A002 — FreeWeight's own parameter name
    model: str | None = None,
    suite: str | None = None,
    machine: str | None = None,
    label: str | None = None,
    adapter: str | None = None,
    since: str | None = None,
    until: str | None = None,
    cursor: str | None = None,
    page: int = 1,
) -> HTMLResponse:
    """Every run, filtered and paged, with the form that starts one as a capped job."""
    filters = {
        "status": status, "model": model, "suite": suite, "machine": machine, "label": label,
        "adapter": adapter, "since": since, "until": until,
    }  # fmt: skip
    return _runs(request, principal, filters=filters, cursor=cursor or None, page=page)


@ui_router.post(f"{BASE}/runs", summary="Start a run from the page")
def start_from_page(
    request: Request,
    principal: CurrentOperator,
    model: Annotated[str, Form()] = "",
    suite: Annotated[str, Form()] = "",
    label: Annotated[str, Form()] = "",
) -> Response:
    """Enqueue W9's ``freeweight_suite_run`` job (ADR-0119's cap, one ``job.enqueue`` row), then
    follow it until FreeWeight names the run."""
    form = {"model": model, "suite": suite, "label": label}
    try:
        job = enqueue_job(
            request,
            principal,
            kind=SUITE_RUN,
            params={"model": model, "suite": suite, "label": label or None},
            schedule_id=None,
        )
    except SuiteError as exc:
        return _runs(request, principal, filters={}, start_error=exc, form=form)
    return RedirectResponse(
        f"{BASE}/runs/starting/{fw.segment(job.id)}", status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.get(
    f"{BASE}/runs/starting/{{job_id}}", summary="A run being started", response_class=HTMLResponse
)
def starting_page(request: Request, principal: CurrentOperator, job_id: str) -> Response:
    """The job that is starting a run, until its output names the run — then that run's page.

    ``freeweight run start --json`` prints the run id as soon as the run is persisted, and the job
    flushes its output while the child runs, so the page polls this route (htmx) and is sent on
    once the id appears. A job that ended without naming a run stays here with its output.
    """
    from weightroom.services.job_kinds import run_id_in
    from weightroom.services.jobs import get_job

    job = None
    error: SuiteError | None = None
    try:
        job = get_job(request.app.state.database, job_id)
        if job.kind != SUITE_RUN:
            message = f"Job {job_id} is a {job.kind} job, not a FreeWeight run."
            raise ModelRefInvalid(message, details={"job_id": job_id})
    except SuiteError as exc:
        job, error = None, exc
    run_id = run_id_in(job.output or "") if job is not None else None
    if run_id:
        location = f"{BASE}/runs/{fw.segment(run_id)}"
        if request.headers.get("hx-request"):
            return Response(status_code=status.HTTP_200_OK, headers={"HX-Redirect": location})
        return RedirectResponse(location, status_code=status.HTTP_303_SEE_OTHER)
    return render_app_page(
        request, principal, APP, "fw_run_starting.html", selected="Runs", job=job, error=error
    )


def _run(
    request: Request,
    principal: Principal,
    run_id: str,
    *,
    action_error: SuiteError | None = None,
    repeat_form: Mapping[str, str] | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: fw.run_api(client, settings, run_id),
        database=lambda handle: fw.run_db(handle, run_id),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "fw_run.html",
        selected="Runs",
        view=view,
        sourced=sourced,
        run_id=run_id,
        events_url=f"{BASE}/runs/{fw.segment(run_id)}/events",
        terminal=fw.TERMINAL_RUN_STATUSES,
        action_error=action_error,
        repeat_form=dict(repeat_form or {}),
    )


@ui_router.get(f"{BASE}/runs/{{run_id}}", summary="One run", response_class=HTMLResponse)
def run_page(request: Request, principal: CurrentOperator, run_id: str) -> HTMLResponse:
    """One run: provenance, degradations, the fingerprint document, tests, metrics, telemetry,
    and its events — live while it runs."""
    return _run(request, principal, run_id)


@ui_router.get(f"{BASE}/runs/{{run_id}}/events", summary="A run's events, live")
def run_events(request: Request, principal: CurrentOperator, run_id: str) -> StreamingResponse:
    """FreeWeight's run event stream as log-pane frames, ``Last-Event-ID`` carried through."""
    chunks = app_stream(
        request.app.state.http,
        request.app.state.settings,
        APP,
        f"runs/{fw.segment(run_id)}/events",
        last_event_id=request.headers.get("last-event-id"),
    )
    return StreamingResponse(
        fw.run_log_frames(chunks), media_type="text/event-stream", headers=_SSE_HEADERS
    )


@ui_router.post(f"{BASE}/runs/{{run_id}}/cancel", summary="Cancel a run from the page")
def cancel_from_page(request: Request, principal: CurrentOperator, run_id: str) -> Response:
    """``POST /runs/{id}/cancel``; ``409 RUN_NOT_CANCELLABLE`` renders on the run's page."""
    client, settings = _clients(request)
    try:
        outcome = actions.cancel_run(client, settings, run_id)
    except SuiteError as exc:
        _audit(
            request, principal, "freeweight.run_cancel", target=run_id, outcome="refused",
            params={}, message=exc.message,
        )  # fmt: skip
        return _run(request, principal, run_id, action_error=exc)
    _audit(
        request, principal, "freeweight.run_cancel", target=run_id, outcome="ok",
        params={"status": outcome.get("status")},
    )  # fmt: skip
    return RedirectResponse(
        f"{BASE}/runs/{fw.segment(run_id)}", status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.post(f"{BASE}/runs/{{run_id}}/repeat", summary="Repeat a run from the page")
def repeat_from_page(
    request: Request,
    principal: CurrentOperator,
    run_id: str,
    force: Annotated[str, Form()] = "",
    label: Annotated[str, Form()] = "",
) -> Response:
    """``POST /runs/{id}/repeat`` with ``?force`` and ``?label``; the new run's page, where a forced
    repeat's divergence is among its degradations. A refusal names every blocker.

    FreeWeight executes a repeat inside ``freeweight.service``, which carries ADR-0119's cap in its
    unit file — so a repeat stays an API call rather than a job (row WP3's handoff records the
    reference machine's reading).
    """
    forced = force == "true"
    params = {"force": forced, "label": label.strip() or None}
    client, settings = _clients(request)
    try:
        outcome = actions.repeat_run(client, settings, run_id, force=forced, label=label)
    except SuiteError as exc:
        _audit(
            request, principal, "freeweight.run_repeat", target=run_id, outcome="refused",
            params=params, message=exc.message,
        )  # fmt: skip
        return _run(
            request, principal, run_id, action_error=exc,
            repeat_form={"force": force, "label": label},
        )  # fmt: skip
    new_id = str(outcome.get("id") or "")
    _audit(
        request, principal, "freeweight.run_repeat", target=run_id, outcome="ok",
        params={**params, "run_id": new_id or None},
    )  # fmt: skip
    return RedirectResponse(
        f"{BASE}/runs/{fw.segment(new_id or run_id)}", status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.get(
    f"{BASE}/runs/{{run_id}}/tests/{{run_test_id}}",
    summary="One test's samples",
    response_class=HTMLResponse,
)
def samples_page(  # noqa: PLR0913 — the two pagers, FreeWeight's cursor and the database's page
    request: Request,
    principal: CurrentOperator,
    run_id: str,
    run_test_id: str,
    cursor: str | None = None,
    page: int = 1,
) -> HTMLResponse:
    """One test's raw samples, paged: the rows every headline number drills to."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: fw.samples_api(client, settings, run_id, run_test_id, cursor or None),
        database=lambda handle: fw.samples_db(handle, run_id, run_test_id, page),
    )
    data = sourced.data or {}
    base = f"{BASE}/runs/{fw.segment(run_id)}/tests/{fw.segment(run_test_id)}"
    next_href = None
    if data.get("next_cursor"):
        next_href = _href(base, cursor=data["next_cursor"])
    elif data.get("next_page"):
        next_href = _href(base, page=data["next_page"])
    return render_app_page(
        request,
        principal,
        APP,
        "fw_samples.html",
        selected="Runs",
        view=view,
        sourced=sourced,
        run_id=run_id,
        run_test_id=run_test_id,
        next_href=next_href,
    )


@ui_router.get(f"{BASE}/samples/{{sample_id}}", summary="One sample", response_class=HTMLResponse)
def sample_page(request: Request, principal: CurrentOperator, sample_id: str) -> HTMLResponse:
    """The case inspector: one request exactly as recorded, every model-written text escaped."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: fw.sample_api(client, settings, sample_id),
        database=lambda handle: fw.sample_db(handle, sample_id),
    )
    return render_app_page(
        request,
        principal,
        APP,
        "fw_sample.html",
        selected="Runs",
        view=view,
        sourced=sourced,
        sample_id=sample_id,
    )
