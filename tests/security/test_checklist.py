"""Security Standards §14, item by item, plus spec §14's own rows and ADR-0126's.

Every bullet is either held here, held by a named test elsewhere (asserted to exist at the
bottom), or does not apply to WeightRoomGym at Phase 1 for a reason stated beside it.
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path

import pytest

from tests.support import JSON_HEADERS, PASSWORD, USERNAME, Console, api_routes, build_console
from weightroom.config import InsecureBindingError, load_settings
from weightroom.domain import auth as auth_domain
from weightroom.observability.logging import _JsonFormatter, _TextFormatter
from weightroom.web.session import SESSION_COOKIE_NAME

HOSTILE = "{{ 7 * 7 }} <script>alert('x')</script> ../../etc/passwd '; DROP TABLE audit_log; --"


@pytest.fixture
def console(tmp_path: Path) -> Console:
    return build_console(tmp_path)


# §14: path traversal — no route accepts a filesystem path without going through
# services/docs.py's resolve-then-check containment (security standards §5); every route below
# was reviewed against that discipline before being added to this allowlist.
_REVIEWED_PATH_PARAMETERS = frozenset(
    {
        # resolve_doc_path: resolved, then checked against [docs] root — the JSON route and its
        # HTML page both take the same parameter.
        ("/api/v1/docs/page", "path"),
        ("/docs/page", "path"),
    }
)


def test_no_route_accepts_a_path_shaped_parameter(console: Console) -> None:
    suspicious = []
    for path, route in api_routes(console.client.app):
        for parameter in route.dependant.query_params + route.dependant.path_params:
            if any(word in parameter.name for word in ("path", "file", "dir")):
                if (path, parameter.name) in _REVIEWED_PATH_PARAMETERS:
                    continue
                suspicious.append((path, parameter.name))
    assert suspicious == []


# §14: oversize body rejected before buffering


def test_an_oversize_body_is_413_before_it_is_read(tmp_path: Path) -> None:
    console = build_console(tmp_path, extra_toml="max_body_bytes = 1024\n")
    console.login()
    declared = console.client.post(
        "/api/v1/reauth",
        content=b"x" * 4096,
        headers={**JSON_HEADERS, "Content-Length": "4096"},
    )
    assert declared.status_code == 413
    assert declared.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


# §14: non-loopback bind without a credential refuses to start — ADR-0126 rule 6 translated


def test_non_loopback_bind_refusals(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text('[server]\nhost = "10.77.10.84"\n')
    with pytest.raises(InsecureBindingError):
        load_settings(config_path=file)
    # the account and TLS members are tests/integration/test_runtime_refusals.py


# §14: authenticated endpoints reject a missing, malformed and revoked credential


def test_missing_malformed_and_revoked_sessions_are_401(console: Console) -> None:
    assert console.client.get("/api/v1/audit").status_code == 401
    console.client.cookies.set(SESSION_COOKIE_NAME, "not-a-session\x00", domain="localhost")
    assert console.client.get("/api/v1/audit").status_code == 401
    console.client.cookies.clear()
    console.login()
    assert console.client.get("/api/v1/audit").status_code == 200
    console.post_form("/logout", {})
    assert console.client.get("/api/v1/audit").status_code == 401


# §14: constant-time comparison; the stored value is a hash (row inspected in test_auth_flow)


def test_password_comparison_is_constant_time_by_construction() -> None:
    source = inspect.getsource(auth_domain.verify_password)
    assert "hmac.compare_digest" in source
    assert "==" not in source.split("return")[-1]


# §14: log output contains no secret for a request that carried one


def test_log_formatters_redact_secret_shaped_fields() -> None:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "auth.failed", (), None)
    record.password = "hunter22"
    record.cookie = "abc"
    record.username = "jordan"
    for formatter in (_JsonFormatter(), _TextFormatter()):
        text = formatter.format(record)
        assert "hunter22" not in text and "abc" not in text.split("cookie")[-1][:10]
        assert "jordan" in text


def test_a_failed_login_logs_the_address_never_the_password(
    console: Console, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        console.login(password="the wrong secret")
    assert "the wrong secret" not in caplog.text


# §14: archive handling — no Phase 1 endpoint accepts an upload (attachments and GGUF are W6/W8)


def test_no_route_accepts_a_body_file(console: Console) -> None:
    for _path, route in api_routes(console.client.app):
        for body_field in route.dependant.body_params:
            assert "UploadFile" not in str(body_field.field_info.annotation)


# §14: hostile model output — Phase 1 renders no model output; the audit page escapes everything


def test_hostile_text_in_an_audit_row_renders_escaped(console: Console) -> None:
    console.login(username=HOSTILE, password="whatever password")  # a refused login row
    console.login()
    page = console.client.get("/audit", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "<script>alert" not in page.text and "&lt;script&gt;alert" in page.text
    assert "{{ 7 * 7 }}" in page.text  # rendered as text, never evaluated


# §14 / ADR-0026 §1: an unexpected Host is 421 on both binds, before authentication


def test_wrong_host_is_421_on_loopback_and_lan_binds(tmp_path: Path) -> None:
    loopback = build_console(tmp_path / "a")
    assert loopback.client.get("/api/v1/version", headers={"Host": "evil"}).status_code == 421
    lan = build_console(tmp_path / "b", host="10.77.10.84")
    assert lan.client.get("/api/v1/version", headers={"Host": "evil"}).status_code == 421
    ok = lan.client.get("/api/v1/version", headers={"Host": "jordan-main.local:8769"})
    assert ok.status_code == 200
    unauthenticated = lan.client.get("/api/v1/audit", headers={"Host": "evil"})
    assert unauthenticated.status_code == 421  # before authentication, not 401


# §14 / ADR-0026 §2 / ADR-0126 rule 5: forged form refused, cross-origin JSON refused


def test_a_forged_form_post_is_csrf_failed_and_a_valid_one_succeeds(console: Console) -> None:
    forged = console.client.post(
        "/login", data={"username": USERNAME, "password": PASSWORD}, headers={"Accept": "text/html"}
    )
    assert forged.status_code == 403 and forged.json()["error"]["code"] == "CSRF_FAILED"
    assert console.login().status_code == 303


def test_json_writes_need_same_origin_and_a_matching_origin(console: Console) -> None:
    body = {"username": USERNAME, "password": PASSWORD}
    no_site = console.client.post(
        "/api/v1/login", json=body, headers={"Content-Type": "application/json"}
    )
    assert no_site.status_code == 403 and no_site.json()["error"]["code"] == "CSRF_FAILED"
    cross = console.client.post(
        "/api/v1/login",
        json=body,
        headers={"Content-Type": "application/json", "Sec-Fetch-Site": "cross-site"},
    )
    assert cross.status_code == 403
    bad_origin = console.client.post(
        "/api/v1/login",
        json=body,
        headers={**JSON_HEADERS, "Origin": "https://attacker.example"},
    )
    assert bad_origin.status_code == 403
    typed = console.client.post(
        "/api/v1/login",
        json=body,
        headers={"Content-Type": "application/json", "Sec-Fetch-Site": "none"},
    )
    assert typed.status_code == 201
    console.client.cookies.clear()
    same = console.client.post(
        "/api/v1/login", json=body, headers={**JSON_HEADERS, "Origin": "https://localhost"}
    )
    assert same.status_code == 201


# §14: /version answers without a credential while /health does not


def test_version_is_open_and_health_is_not(console: Console) -> None:
    assert console.client.get("/api/v1/version").status_code == 200
    assert console.client.get("/api/v1/health").status_code == 401
    console.login()
    assert console.client.get("/api/v1/health").status_code == 200


# spec §14's own rows: fixation, expiry, logout, Sec-Fetch-Site, the trust listener — held by
# tests/integration/test_auth_flow.py and tests/integration/test_trust_listener.py


def test_the_named_tests_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    flow = (root / "integration" / "test_auth_flow.py").read_text(encoding="utf-8")
    for name in (
        "test_a_new_session_id_on_every_login",
        "test_idle_expiry_ends_the_session",
        "test_absolute_expiry_ends_the_session",
        "test_logout_deletes_the_row",
        "test_the_login_brake_is_five_per_minute",
    ):
        assert name in flow, name
    trust = (root / "integration" / "test_trust_listener.py").read_text(encoding="utf-8")
    assert "test_every_other_path_is_404" in trust
    refusals = (root / "integration" / "test_runtime_refusals.py").read_text(encoding="utf-8")
    assert "without_an_account_is_insecure_binding" in refusals
