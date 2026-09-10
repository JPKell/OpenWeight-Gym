"""weightroom.web.routes.session — login, logout, re-authentication (api.md §9).

Forms for the pages (``/login``, ``/logout``, CSRF-checked by MirrorWall's middleware); JSON
for the API (``/api/v1/login|logout|reauth``, held to ADR-0126 rule 5 by the same-origin
middleware). Both call the same service, and every one of them writes an audit row.
"""

from __future__ import annotations

from typing import Annotated
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from weightroom.services.audit import record
from weightroom.services.auth import (
    Unauthorized,
    authenticate,
    close_session,
    open_session,
    operator_count,
    reauthenticate,
)
from weightroom.web.csrf import render_form_page
from weightroom.web.session import (
    SESSION_COOKIE_NAME,
    CurrentOperator,
    clear_cookie,
    now_of,
    set_cookie,
)

__all__ = ["router", "ui_router"]

router = APIRouter(tags=["session"])
ui_router = APIRouter(tags=["ui"], include_in_schema=False)


class Credentials(BaseModel):
    """``POST /api/v1/login``'s body."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class Password(BaseModel):
    """``POST /api/v1/reauth``'s body."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1)


def _address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _safe_next(target: str) -> str:
    return target if target.startswith("/") and not target.startswith("//") else "/"


def _login(request: Request, *, username: str, password: str) -> str | None:
    """Try the credentials; audit either way; return the new session id or ``None``."""
    app = request.app
    now = now_of(request)
    operator_id = authenticate(app.state.database, username=username, password=password, now=now)
    if operator_id is None:
        record(
            app.state.database,
            action="login",
            actor="operator",
            outcome="refused",
            now=now,
            app="weightroom",
            params={"username": username, "address": _address(request)},
            message="bad credentials",
            request_id=_request_id(request),
        )
        return None
    session_id = open_session(
        app.state.database,
        operator_id=operator_id,
        address=_address(request),
        now=now,
        auth=app.state.settings.auth,
    )
    record(
        app.state.database,
        action="login",
        actor="operator",
        outcome="ok",
        now=now,
        operator_id=operator_id,
        app="weightroom",
        params={"username": username, "address": _address(request)},
        request_id=_request_id(request),
    )
    return session_id


def _logout(request: Request, principal: CurrentOperator) -> None:
    if principal.session_id is not None:
        close_session(request.app.state.database, session_id=principal.session_id)
    record(
        request.app.state.database,
        action="logout",
        actor="operator",
        outcome="ok",
        now=now_of(request),
        operator_id=principal.operator_id,
        app="weightroom",
        params={"username": principal.username},
        request_id=_request_id(request),
    )


@ui_router.get("/login", summary="The login page", response_class=HTMLResponse)
def login_page(
    request: Request, next: Annotated[str, "where to go afterwards"] = "/"
) -> HTMLResponse:
    """Render the login form; with no account on loopback, say so and offer the shell."""
    return render_form_page(
        request,
        "login.html",
        page="login",
        next=_safe_next(next),
        error=None,
        no_account=operator_count(request.app.state.database) == 0,
    )


@ui_router.post("/login", summary="Log in (form)")
async def login_form(request: Request) -> Response:
    """Check the form, mint a session and redirect; re-render with a message on failure."""
    form = parse_qs((await request.body()).decode("utf-8", "replace"))
    username = form.get("username", [""])[0].strip()
    password = form.get("password", [""])[0]
    target = _safe_next(form.get("next", ["/"])[0])
    session_id = _login(request, username=username, password=password) if username else None
    if session_id is None:
        page = render_form_page(
            request,
            "login.html",
            page="login",
            next=target,
            error="Wrong username or password.",
            no_account=False,
        )
        page.status_code = status.HTTP_200_OK
        return page
    response = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    set_cookie(response, session_id)
    return response


@ui_router.post("/logout", summary="Log out (form)")
def logout_form(request: Request, principal: CurrentOperator) -> Response:
    """Delete the session row, clear the cookie, go to the login page."""
    _logout(request, principal)
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_cookie(response)
    return response


@router.post("/login", summary="Log in (JSON)", status_code=status.HTTP_201_CREATED)
def login_json(request: Request, body: Credentials) -> JSONResponse:
    """Mint a session; the cookie is the credential from here on.

    Raises:
        Unauthorized: Wrong username or password (``401``).
    """
    session_id = _login(request, username=body.username, password=body.password)
    if session_id is None:
        raise Unauthorized("Wrong username or password.", details={})
    response = JSONResponse(
        status_code=status.HTTP_201_CREATED, content={"username": body.username.strip()}
    )
    set_cookie(response, session_id)
    return response


@router.post("/logout", summary="Log out (JSON)")
def logout_json(request: Request, principal: CurrentOperator) -> JSONResponse:
    """Delete the session row and clear the cookie."""
    _logout(request, principal)
    response = JSONResponse(content={"logged_out": True})
    clear_cookie(response)
    return response


@router.post("/reauth", summary="Re-authenticate for a security action")
def reauth(request: Request, principal: CurrentOperator, body: Password) -> JSONResponse:
    """Check the password again and open the re-authentication window (ADR-0127 rule 6).

    The open loopback install has no password and is told so; a wrong password is ``401``.
    """
    app = request.app
    now = now_of(request)
    ok = principal.source == "session" and reauthenticate(
        app.state.database, principal=principal, password=body.password, now=now
    )
    record(
        app.state.database,
        action="reauth",
        actor="operator",
        outcome="ok" if ok else "refused",
        now=now,
        operator_id=principal.operator_id,
        app="weightroom",
        params={"username": principal.username},
        security=True,
        request_id=_request_id(request),
    )
    if not ok:
        raise Unauthorized("Re-authentication refused.", details={})
    window = app.state.settings.auth.reauth_window_minutes
    return JSONResponse(
        content={
            "reauth_at": now.isoformat(),
            "window_minutes": window,
            "cookie": SESSION_COOKIE_NAME,
        }
    )
