"""Login, sessions, logout, re-authentication and the brake, end to end over the console."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from tests.support import JSON_HEADERS, PASSWORD, USERNAME, Console, build_console
from weightroom.infrastructure.db.models import Operator, Session
from weightroom.services.auth import change_password, revoke_all_sessions
from weightroom.web.session import SESSION_COOKIE_NAME


@pytest.fixture
def console(tmp_path: Path) -> Console:
    return build_console(tmp_path)


def _session_ids(console: Console) -> list[str]:
    with console.database.read() as session:
        return [row.id for row in session.execute(select(Session)).scalars()]


def test_login_sets_the_host_cookie_with_every_flag_and_lands_on_the_shell(
    console: Console,
) -> None:
    response = console.login()
    assert response.status_code == 303 and response.headers["location"] == "/"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    lowered = cookie.lower()
    assert "httponly" in lowered and "secure" in lowered and "samesite=strict" in lowered
    assert "path=/" in lowered and "domain=" not in lowered
    shell = console.client.get("/", headers={"Accept": "text/html"})
    assert shell.status_code == 200 and USERNAME in shell.text


def test_a_new_session_id_on_every_login_and_the_old_one_stays_separate(console: Console) -> None:
    first = console.login().cookies[SESSION_COOKIE_NAME]
    console.client.cookies.clear()
    second = console.login().cookies[SESSION_COOKIE_NAME]
    assert first != second
    assert set(_session_ids(console)) == {first, second}


def test_wrong_password_re_renders_the_form_and_sets_no_session(console: Console) -> None:
    response = console.login(password="wrong password")
    assert response.status_code == 200 and "Wrong username or password" in response.text
    assert SESSION_COOKIE_NAME not in console.client.cookies
    assert console.client.get("/", headers={"Accept": "text/html"}).status_code == 303


def test_unauthenticated_html_redirects_to_login_and_api_is_401(console: Console) -> None:
    page = console.client.get("/audit", headers={"Accept": "text/html"})
    assert page.status_code == 303 and page.headers["location"] == "/login?next=/audit"
    api = console.client.get("/api/v1/audit")
    assert api.status_code == 401 and api.json()["error"]["code"] == "UNAUTHORIZED"
    assert console.client.get("/api/v1/version").status_code == 200


def test_idle_expiry_ends_the_session_after_twelve_hours(console: Console) -> None:
    console.login()
    console.advance(hours=11)
    assert console.client.get("/api/v1/audit").status_code == 200
    console.advance(hours=11, minutes=59)  # seen at 11 h; idle 12 h from there
    assert console.client.get("/api/v1/audit").status_code == 200
    console.advance(hours=12, minutes=1)
    assert console.client.get("/api/v1/audit").status_code == 401
    assert _session_ids(console) == []


def test_absolute_expiry_ends_the_session_after_seven_days_however_active(
    console: Console,
) -> None:
    console.login()
    for _ in range(7 * 4 - 1):
        console.advance(hours=6)
        assert console.client.get("/api/v1/audit").status_code == 200
    console.advance(hours=6)
    assert console.client.get("/api/v1/audit").status_code == 401


def test_logout_deletes_the_row_and_clears_the_cookie(console: Console) -> None:
    console.login()
    response = console.post_form("/logout", {})
    assert response.status_code == 303 and response.headers["location"] == "/login"
    assert (
        "Max-Age=0" in response.headers["set-cookie"]
        or "expires" in response.headers["set-cookie"].lower()
    )
    assert _session_ids(console) == []
    assert console.client.get("/api/v1/audit").status_code == 401


def test_json_login_logout_and_reauth(console: Console) -> None:
    bad = console.client.post(
        "/api/v1/login",
        json={"username": USERNAME, "password": "nope nope nope"},
        headers=JSON_HEADERS,
    )
    assert bad.status_code == 401
    ok = console.client.post(
        "/api/v1/login", json={"username": USERNAME, "password": PASSWORD}, headers=JSON_HEADERS
    )
    assert ok.status_code == 201 and SESSION_COOKIE_NAME in ok.cookies
    refused = console.client.post(
        "/api/v1/reauth", json={"password": "wrong wrong wrong"}, headers=JSON_HEADERS
    )
    assert refused.status_code == 401
    granted = console.client.post(
        "/api/v1/reauth", json={"password": PASSWORD}, headers=JSON_HEADERS
    )
    assert granted.status_code == 200 and granted.json()["window_minutes"] == 5
    with console.database.read() as session:
        row = session.execute(select(Session)).scalar_one()
        assert row.reauth_at == console.now
    out = console.client.post("/api/v1/logout", headers=JSON_HEADERS)
    assert out.status_code == 200 and out.json() == {"logged_out": True}
    assert console.client.get("/api/v1/audit").status_code == 401


def test_the_login_brake_is_five_per_minute_per_address_whatever_is_presented(
    console: Console,
) -> None:
    for _ in range(5):
        assert console.login(password="wrong password").status_code == 200
    sixth = console.login()  # the right password, still braked
    assert sixth.status_code == 429
    assert sixth.json()["error"]["code"] == "RATE_LIMITED"
    assert int(sixth.headers["Retry-After"]) >= 1
    assert SESSION_COOKIE_NAME not in console.client.cookies


def test_password_reset_from_a_shell_revokes_every_session(console: Console) -> None:
    console.login()
    assert len(_session_ids(console)) == 1
    revoked = change_password(
        console.database, username=USERNAME, password="a new password", now=console.now
    )
    assert revoked == 1 and _session_ids(console) == []
    assert console.client.get("/api/v1/audit").status_code == 401
    assert console.login(password="a new password").status_code == 303
    assert revoke_all_sessions(console.database) == 1


def test_the_stored_password_is_a_hash_with_its_parameters(console: Console) -> None:
    with console.database.read() as session:
        operator = session.execute(select(Operator)).scalar_one()
    assert PASSWORD.encode() not in operator.password_hash
    assert len(operator.password_hash) == 32 and len(operator.password_salt) == 16
    assert operator.kdf_params == {"n": 32768, "r": 8, "p": 1}


def test_loopback_with_no_account_is_open_and_says_so(tmp_path: Path) -> None:
    console = build_console(tmp_path, account=False)
    shell = console.client.get("/", headers={"Accept": "text/html"})
    assert shell.status_code == 200 and "open loopback" in shell.text
    login = console.client.get("/login", headers={"Accept": "text/html"})
    assert "No operator account exists yet" in login.text
    assert console.client.get("/api/v1/audit").status_code == 200
    reauth = console.client.post(
        "/api/v1/reauth", json={"password": "anything at all"}, headers=JSON_HEADERS
    )
    assert reauth.status_code == 401


def test_a_lan_bind_with_no_account_is_never_open(tmp_path: Path) -> None:
    console = build_console(tmp_path, account=False, host="10.77.10.84")
    response = console.client.get("/api/v1/audit", headers={"Host": "jordan-main.local"})
    assert response.status_code == 401
