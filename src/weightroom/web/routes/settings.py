"""weightroom.web.routes.settings — every application's configuration, edited from the console.

api.md §2's settings routes and §9's ``GET``/``PUT /settings``. Five applications, not four:
WeightRoomGym's own page is generated from its own schema document by the same code, so the
console cannot describe the four better than it describes itself (ADR-0127 rule 6's last clause).
Only the *sources* differ, and only where they must — WeightRoomGym reads its own document and
writes its own runtime keys in process rather than launching or calling itself.

Route handlers here do what every other handler in this repository does: resolve the request,
call one service, render. The routing of a key to the file or to the running application, the
per-key outcomes and the race are :func:`~weightroom.services.settings_forms.save_settings`'s.

**Re-authentication is the session, not a token.** ADR-0127 rule 6 asks for the operator's
password again within a five-minute window before a security key moves. W1 already implements
that as a stamp on the session row (``sessions.reauth_at``, ``POST /reauth``,
:func:`~weightroom.services.auth.require_fresh_reauth`), so this row carries no second
credential: the page posts the password with the change, this module opens the window and then
performs the write in the same request. See ``docs/history/handoffs/W4_HANDOFF.md`` for why a
header or a second cookie was rejected.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Annotated, Any, Final

import httpx
from fastapi import APIRouter, Body, Form, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from weightroom.config import APP_LABELS
from weightroom.domain.units import UNIT_APPLICATIONS
from weightroom.services.apps import AppUnknown, AppView, bearer_token
from weightroom.services.audit import record
from weightroom.services.auth import ReauthRequired, reauthenticate, require_fresh_reauth
from weightroom.services.config_files import parse_or_reason, write_config
from weightroom.services.settings_forms import (
    SettingsForm,
    live_settings,
    read_schema_document,
    save_settings,
    settings_form,
)
from weightroom.web.session import CurrentOperator, now_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from weightroom.services.auth import Principal

__all__ = ["SETTINGS_APPS", "require_settings_app", "router", "ui_router"]

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)

SETTINGS_APPS: Final[tuple[str, ...]] = UNIT_APPLICATIONS
"""The four, and the console itself — whose own keys are edited exactly the same way.

The same five ``wr-gym units sync`` writes units for, read from the one list rather than
assembled a second time here."""

_SETTINGS_TIMEOUT_SECONDS: Final = 5.0

_FIELD_PREFIX: Final = "field:"
"""Form fields are namespaced so a key called ``password`` cannot collide with the password."""


class SettingsWrite(BaseModel):
    """``PUT /apps/{app}/settings``'s body (api.md §2)."""

    model_config = ConfigDict(extra="forbid")

    changes: dict[str, Any] = Field(default_factory=dict)
    base_mtime: int | None = None
    to_file: list[str] = Field(default_factory=list)


class CandidateFile(BaseModel):
    """``POST /apps/{app}/settings/validate``'s body: a whole candidate file."""

    model_config = ConfigDict(extra="forbid")

    text: str


def require_settings_app(app: str) -> str:
    """Return ``app`` if it is one of the five this module serves, else refuse by name.

    Raises:
        AppUnknown: It is not.
    """
    if app not in SETTINGS_APPS:
        raise AppUnknown(
            f"{app!r} has no settings page.",
            details={"app": app, "known": list(SETTINGS_APPS)},
        )
    return app


def _view_for(request: Request, app: str) -> AppView | None:
    """The application's view, or ``None`` for WeightRoomGym itself, which has no unit here."""
    if app == "weightroom":
        return None
    from weightroom.web.routes.apps import _view

    return _view(request, app)


def _config_path(request: Request) -> Path:
    path: Path = request.app.state.config_path
    return path


def form_for(request: Request, app: str, *, refresh: bool = False) -> tuple[SettingsForm, Any]:
    """Read ``app``'s schema document, its file and its running process into one form.

    Args:
        request: The request, for the caches and the clients.
        app: One of :data:`SETTINGS_APPS`.
        refresh: Ignore the 60-second document cache and ask the application now.

    Returns:
        The form and the application's view (``None`` for WeightRoomGym itself).
    """
    state = request.app.state
    view = _view_for(request, app)
    own_config = _config_path(request)
    document, error = state.schemas.get(
        app,
        now=time.monotonic(),
        read=lambda: read_schema_document(state.settings, app, config_path=own_config),
        refresh=refresh,
    )
    live: Mapping[str, Any] = {}
    if view is not None and document is not None:
        live, live_error = live_settings(state.settings, app, view, client=state.http)
        if live_error:
            logger.info("settings.live_unavailable", extra={"app": app, "reason": live_error})
    elif app == "weightroom" and state.database is not None:
        from weightroom.services.settings import read_runtime_settings

        live = read_runtime_settings(state.database, settings=state.settings)
    return (
        settings_form(
            state.settings,
            app,
            document=document,
            document_error=error,
            view=view,
            live=live,
            config_path=own_config if app == "weightroom" else None,
        ),
        view,
    )


def _runtime_applier(
    request: Request, app: str, view: AppView | None
) -> Callable[[Mapping[str, Any]], tuple[bool, str | None]] | None:
    """How to reach ``app``'s ``PUT /api/v1/settings``, or ``None`` when it is not running."""
    state = request.app.state
    if app == "weightroom":
        if state.database is None:  # pragma: no cover — the lifespan always opens one
            return None

        def apply_here(changes: Mapping[str, Any]) -> tuple[bool, str | None]:
            from baseaicore import SuiteError

            from weightroom.services.settings import write_runtime_settings

            try:
                write_runtime_settings(
                    state.database, changes, settings=state.settings, now=now_of(request)
                )
            except SuiteError as exc:
                return False, exc.message
            return True, None

        return apply_here
    if view is None or not view.running or not view.reachable:
        return None

    def apply_over_http(changes: Mapping[str, Any]) -> tuple[bool, str | None]:
        headers = {"Content-Type": "application/json"}
        token = bearer_token(state.settings, app)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = state.http.put(
                f"{view.base_url.rstrip('/')}/api/v1/settings",
                json=dict(changes),
                headers=headers,
                timeout=_SETTINGS_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            return False, f"{app} did not answer PUT /api/v1/settings: {exc}"
        if response.status_code < status.HTTP_400_BAD_REQUEST:
            return True, None
        return False, _refusal_text(app, response)

    return apply_over_http


def _refusal_text(app: str, response: httpx.Response) -> str:
    """The application's own words for a refusal — its envelope's message, never a rewrite."""
    try:
        body = response.json()
    except ValueError:
        return f"{app} refused with {response.status_code}: {response.text[:200]}"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return f"{app} refused: {error['message']}"
    return f"{app} refused with {response.status_code}."


def _reauthenticated(request: Request, principal: Principal, password: str) -> Principal | None:
    """Open the re-authentication window and return the **restamped** principal, or ``None``.

    The principal this request was resolved with was read before the password arrived, so it
    still carries the old ``reauth_at``; handing it to
    :func:`~weightroom.services.auth.require_fresh_reauth` a moment later would refuse a password
    that had just been accepted. The session row is the store; this is the same row, re-read.
    """
    from dataclasses import replace

    now = now_of(request)
    if not reauthenticate(
        request.app.state.database, principal=principal, password=password, now=now
    ):
        return None
    return replace(principal, reauth_at=now)


def _notice(result: Any) -> str:  # noqa: ANN401 — a SaveResult, imported lazily
    """One sentence for the page: how many keys went live, how many went to the file."""
    applied = len(result.keys_with("applied"))
    written = len(result.keys_with("written"))
    parts = []
    if applied:
        parts.append(f"{applied} applied live")
    if written:
        parts.append(f"{written} written to the file")
    return ", ".join(parts) if parts else "Nothing changed."


def _guard_security_keys(
    request: Request, principal: Principal, form: SettingsForm, keys: Mapping[str, Any]
) -> bool:
    """Refuse a security key outside the re-authentication window (ADR-0127 rule 6).

    Returns:
        Whether any submitted key is a security key, for the audit row's ``security`` flag.

    Raises:
        ReauthRequired: One is, and the session has not re-authenticated recently enough.
    """
    touched = form.security_keys & set(keys)
    if touched:
        require_fresh_reauth(principal, now=now_of(request), auth=request.app.state.settings.auth)
    return bool(touched)


def _audit_write(
    request: Request,
    principal: Principal,
    app: str,
    *,
    result: Any,
    security: bool,
    raw: bool = False,
) -> str:
    """The one ``settings.write`` row every write path leaves (spec §11 contract 2)."""
    refused = result.refused
    outcome = "refused" if refused else "ok"
    keys = tuple(sorted(one.key for one in result.outcomes))
    return record(
        request.app.state.database,
        action="settings.write",
        actor="operator",
        outcome=outcome,
        now=now_of(request),
        operator_id=principal.operator_id,
        app=app,
        target=", ".join(keys) if keys else str(result.base_mtime),
        params={
            "applied": list(result.keys_with("applied")),
            "written": list(result.keys_with("written")),
            "refused": [one.key for one in refused],
            # Not `security_key`: the audit redactor blanks any parameter whose name matches
            # `key`, and a redacted boolean reads like a leak that was caught rather than a flag.
            "touched_security": security,
            "raw_editor": raw,
        },
        message="; ".join(f"{one.key}: {one.message}" for one in refused) or None,
        security=security,
        request_id=getattr(request.state, "request_id", None),
    )


# --- JSON ------------------------------------------------------------------------------------


@router.get("/apps/{app}/config", summary="The raw configuration file and its base mtime")
def get_config(request: Request, principal: CurrentOperator, app: str) -> JSONResponse:
    """The file's text and ``st_mtime_ns`` — the raw editor's base (api.md §2)."""
    name = require_settings_app(app)
    form, _view = form_for(request, name)
    return JSONResponse(
        content={
            "app": name,
            "path": form.config_path,
            "exists": form.config_exists,
            "base_mtime": form.base_mtime,
            "text": form.raw_toml,
        }
    )


@router.get("/apps/{app}/settings/schema", summary="The application's schema document")
def get_schema(request: Request, principal: CurrentOperator, app: str) -> JSONResponse:
    """ADR-0127 rule 1's document, cached for 60 s; the reason instead when it cannot be read."""
    name = require_settings_app(app)
    state = request.app.state
    document, error = state.schemas.get(
        name,
        now=time.monotonic(),
        read=lambda: read_schema_document(state.settings, name, config_path=_config_path(request)),
    )
    if document is None:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"app": name, "document": None, "reason": error},
        )
    return JSONResponse(content=document)


@router.get("/apps/{app}/settings", summary="Effective settings, with sources")
def get_settings(request: Request, principal: CurrentOperator, app: str) -> JSONResponse:
    """Every key with its type, bounds, default, value, source and the two key sets."""
    form, _view = form_for(request, require_settings_app(app))
    return JSONResponse(content=form.as_json())


@router.put("/apps/{app}/settings", summary="Change settings")
def put_settings(
    request: Request, principal: CurrentOperator, app: str, body: SettingsWrite
) -> JSONResponse:
    """Route each key to the file or the running application, and answer per key (api.md §2).

    Raises:
        ReauthRequired: A security key without a fresh ``POST /reauth`` (``REAUTH_REQUIRED``).
        ConfigChangedOnDisk: ``base_mtime`` is stale; nothing was written.
        ConfigValidationFailed: The application refused the candidate file.
    """
    name = require_settings_app(app)
    form, view = form_for(request, name)
    security = _guard_security_keys(request, principal, form, body.changes)
    result = save_settings(
        request.app.state.settings,
        name,
        body.changes,
        form=form,
        base_mtime=body.base_mtime if body.base_mtime is not None else form.base_mtime,
        to_file=frozenset(body.to_file),
        apply_runtime=_runtime_applier(request, name, view),
    )
    audit_id = _audit_write(request, principal, name, result=result, security=security)
    request.app.state.schemas.forget(name)
    return JSONResponse(content={**result.as_json(), "audit_id": audit_id})


@router.post("/apps/{app}/settings/validate", summary="Validate a candidate file")
def validate_settings(
    request: Request, principal: CurrentOperator, app: str, body: CandidateFile
) -> JSONResponse:
    """The application's own verdict on a candidate file, unchanged (ADR-0127 rule 2).

    Nothing is written: the candidate is handed to ``<app> config validate --file`` in a
    temporary file and the verdict is returned. The row it leaves says ``pending``, because a
    subprocess was launched over operator-supplied text and that is worth a trail entry even
    though no state moved.
    """
    from weightroom.services.config_files import ConfigValidationFailed, validate_candidate

    name = require_settings_app(app)
    state = request.app.state
    verdict: dict[str, Any] = {"app": name, "valid": True, "message": None}
    syntax = parse_or_reason(body.text)
    if syntax is not None:
        verdict = {"app": name, "valid": False, "message": f"not valid TOML: {syntax}"}
    else:
        with TemporaryDirectory(prefix="wr-gym-validate-") as directory:
            candidate = Path(directory) / "config.toml"
            candidate.write_text(body.text, encoding="utf-8")
            try:
                validate_candidate(state.settings, name, candidate)
            except ConfigValidationFailed as exc:
                verdict = {"app": name, "valid": False, "message": exc.message}
    record(
        state.database,
        action="settings.validate",
        actor="operator",
        outcome="pending",
        now=now_of(request),
        operator_id=principal.operator_id,
        app=name,
        target="config.toml",
        params={"valid": verdict["valid"]},
        message=verdict["message"],
        request_id=getattr(request.state, "request_id", None),
    )
    return JSONResponse(content=verdict)


@router.get("/settings", summary="WeightRoomGym's own runtime settings")
def get_own_settings(request: Request, principal: CurrentOperator) -> JSONResponse:
    """ADR-0100's shape for the console itself (api.md §9)."""
    from weightroom.services.settings import runtime_settings_document

    return JSONResponse(
        content=runtime_settings_document(
            request.app.state.database, settings=request.app.state.settings
        )
    )


@router.put("/settings", summary="Change WeightRoomGym's own runtime settings")
def put_own_settings(
    request: Request, principal: CurrentOperator, body: Annotated[dict[str, Any], Body()]
) -> JSONResponse:
    """The console's own six runtime keys; a config-only key is refused by name.

    Raises:
        SettingConfigOnly: The key is config-only (``403``); the settings page writes the file.
        SettingUnknown: The key is not a setting at all (``400``).
        ValidationError: The value is the wrong type or outside its bounds.
    """
    from weightroom.services.settings import runtime_settings_document, write_runtime_settings

    state = request.app.state
    write_runtime_settings(state.database, body, settings=state.settings, now=now_of(request))
    record(
        state.database,
        action="settings.write",
        actor="operator",
        outcome="ok",
        now=now_of(request),
        operator_id=principal.operator_id,
        app="weightroom",
        target=", ".join(sorted(body)),
        params={"applied": sorted(body), "runtime": True},
        request_id=getattr(request.state, "request_id", None),
    )
    return JSONResponse(content=runtime_settings_document(state.database, settings=state.settings))


# --- Pages -----------------------------------------------------------------------------------


def _render(
    request: Request,
    principal: CurrentOperator,
    app: str,
    *,
    result: Any = None,
    notice: str | None = None,
    error: str | None = None,
    show_raw: bool = False,
) -> HTMLResponse:
    """The settings page for one application, with the outcome of the write that led here."""
    from weightroom.services.config_files import BACKUP_SUFFIX
    from weightroom.web.rendering import CONSOLE_SIDE_NAV, app_side_nav, app_side_nav_stubs
    from weightroom.web.routes.apps import render_shell_page

    form, view = form_for(request, app, refresh=True)
    own = app == "weightroom"
    return render_shell_page(
        request,
        "settings.html",
        page="settings" if own else "apps",
        principal=principal,
        app=app,
        form=form,
        view=view,
        result=result,
        notice=notice,
        error=error,
        auth_window_minutes=request.app.state.settings.auth.reauth_window_minutes,
        backup_suffix=BACKUP_SUFFIX,
        show_raw=show_raw,
        active_app=None if own else app,
        nav_sections=CONSOLE_SIDE_NAV if own else app_side_nav(app, selected="Settings"),
        nav_footer=None if own else f"{APP_LABELS.get(app, app)} {form.version or '—'}",
        side_nav_stubs=() if own else app_side_nav_stubs(app),
    )


@ui_router.get("/apps/{app}/settings", summary="Settings page", response_class=HTMLResponse)
def settings_page(request: Request, principal: CurrentOperator, app: str) -> HTMLResponse:
    """One application's settings, generated from its own schema document."""
    return _render(request, principal, require_settings_app(app))


@ui_router.get("/settings", summary="WeightRoomGym's own settings", response_class=HTMLResponse)
def own_settings_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The console's own configuration, from its own ``config schema`` verb."""
    return _render(request, principal, "weightroom")


def _submitted(raw: Mapping[str, Any], form: SettingsForm) -> tuple[dict[str, Any], list[str]]:
    """Every ``field:<key>`` in the post, parsed to its own type; the unparseable named."""
    changes: dict[str, Any] = {}
    problems: list[str] = []
    for name, value in raw.items():
        if not name.startswith(_FIELD_PREFIX):
            continue
        key = name[len(_FIELD_PREFIX) :]
        one = form.field_for(key)
        if one is None:
            problems.append(f"{key} is not a setting this application recognises.")
            continue
        try:
            changes[key] = one.parse(str(value))
        except ValueError as exc:
            problems.append(str(exc))
    return changes, problems


@ui_router.post("/apps/{app}/settings", summary="Save settings from the page")
async def save_from_page(request: Request, principal: CurrentOperator, app: str) -> HTMLResponse:
    """The form post: every field, an optional password, and the runtime keys forced to file.

    ``async`` only to read the form, whose field names are the application's own keys and so
    cannot be declared: everything below it launches subprocesses and blocks, and runs in the
    threadpool where the rest of this repository's work runs (ADR-0003).
    """
    name = require_settings_app(app)
    raw = dict(await request.form())
    return await run_in_threadpool(_save_from_form, request, principal, name, raw)


def _save_from_form(
    request: Request, principal: CurrentOperator, app: str, raw: Mapping[str, Any]
) -> HTMLResponse:
    from weightroom.services.config_files import ConfigChangedOnDisk, ConfigValidationFailed

    state = request.app.state
    form, view = form_for(request, app)
    changes, problems = _submitted(raw, form)
    password = str(raw.get("password") or "")
    if password:
        fresh = _reauthenticated(request, principal, password)
        if fresh is None:
            return _render(request, principal, app, error="That password is not the operator's.")
        principal = fresh
    try:
        security = _guard_security_keys(request, principal, form, changes)
    except ReauthRequired as exc:
        return _render(request, principal, app, error=exc.message)
    base = raw.get("base_mtime")
    to_file = frozenset(str(raw.get("to_file") or "").split(",")) - {""}
    try:
        result = save_settings(
            state.settings,
            app,
            changes,
            form=form,
            base_mtime=int(str(base)) if base else None,
            to_file=to_file,
            apply_runtime=_runtime_applier(request, app, view),
        )
    except (ConfigChangedOnDisk, ConfigValidationFailed) as exc:
        return _render(request, principal, app, error=exc.message)
    _audit_write(request, principal, app, result=result, security=security)
    state.schemas.forget(app)
    notice = _notice(result)
    return _render(
        request,
        principal,
        app,
        result=result,
        notice=notice,
        error="; ".join(problems) or None,
    )


@ui_router.get(
    "/apps/{app}/settings/raw", summary="The raw TOML editor", response_class=HTMLResponse
)
def raw_editor_page(request: Request, principal: CurrentOperator, app: str) -> HTMLResponse:
    """The whole file, on its own page.

    Deliberately not a section of the settings page. The file carries the application's secrets
    verbatim — that is what makes the editor useful — and a settings page that shipped them in
    every response would leak them to a shoulder, a screenshot or a cached page on a console
    that is reachable from the LAN by design (ADR-0126). The form redacts; the editor is the
    file, and the operator has to ask for it.
    """
    return _render(request, principal, require_settings_app(app), show_raw=True)


@ui_router.post("/apps/{app}/settings/raw", summary="Save the whole file from the raw editor")
def save_raw_from_page(
    request: Request,
    principal: CurrentOperator,
    app: str,
    text: Annotated[str, Form()] = "",
    base_mtime: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """The raw TOML editor, under the same validate-before-write and the same re-authentication.

    The whole file is the write, so every security key the file names is in scope: the editor
    always re-authenticates when the file carries one, rather than trying to diff intent out of
    two blobs of text.

    ``text`` defaults to the empty string rather than being required: emptying the file is a
    legitimate write (it means *every key at its default*), and some clients drop an empty form
    value rather than sending it.
    """
    from weightroom.services.config_files import ConfigChangedOnDisk, ConfigValidationFailed
    from weightroom.services.settings_forms import KeyOutcome, SaveResult

    name = require_settings_app(app)
    state = request.app.state
    form, _view = form_for(request, name)
    if password:
        fresh = _reauthenticated(request, principal, password)
        if fresh is None:
            return _render(
                request,
                principal,
                name,
                error="That password is not the operator's.",
                show_raw=True,
            )
        principal = fresh
    syntax = parse_or_reason(text)
    if syntax is not None:
        return _render(request, principal, name, error=f"Not valid TOML: {syntax}", show_raw=True)
    security = bool(form.security_keys)
    try:
        if security:
            require_fresh_reauth(principal, now=now_of(request), auth=state.settings.auth)
        landed = write_config(
            state.settings,
            name,
            Path(form.config_path),
            text,
            base_mtime=int(base_mtime) if base_mtime else None,
            keys=("<whole file>",),
        )
    except (ReauthRequired, ConfigChangedOnDisk, ConfigValidationFailed) as exc:
        return _render(request, principal, name, error=exc.message, show_raw=True)
    result = SaveResult(
        outcomes=(KeyOutcome("<whole file>", "written"),),
        base_mtime=landed.base_mtime,
        backup=str(landed.backup) if landed.backup else None,
        pending_restart=True,
    )
    _audit_write(request, principal, name, result=result, security=security, raw=True)
    state.schemas.forget(name)
    return _render(request, principal, name, result=result, notice=f"{form.config_path} written.")


@ui_router.post("/settings", summary="Save WeightRoomGym's own settings")
async def save_own_from_page(request: Request, principal: CurrentOperator) -> HTMLResponse:
    """The console's own settings form; identical path, its own document."""
    raw = dict(await request.form())
    return await run_in_threadpool(_save_from_form, request, principal, "weightroom", raw)


@ui_router.post("/apps/{app}/restart-for-settings", summary="Restart to apply a pending write")
def restart_for_settings(request: Request, principal: CurrentOperator, app: str) -> Response:
    """The *pending restart* button: the ADR-0125 control path, back to the settings page."""
    from weightroom.web.routes.apps import _control

    name = require_settings_app(app)
    if name == "weightroom":
        raise AppUnknown(
            "WeightRoomGym does not restart itself from its own page; "
            "run `systemctl --user restart weightroom` on the host.",
            details={"app": name},
        )
    _control(request, principal, name, "restart")
    return RedirectResponse(f"/apps/{name}/settings", status_code=status.HTTP_303_SEE_OTHER)
