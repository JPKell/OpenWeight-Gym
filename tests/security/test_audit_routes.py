"""Spec §11 contract 2: every state-changing route writes exactly one ``audit_log`` row.

The test enumerates the app's routes rather than listing them: a new ``POST``/``PUT``/``PATCH``/
``DELETE`` route fails this suite until it has an entry in :data:`EXERCISES`, and every entry is
run and must add exactly one row. Later rows inherit both halves.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select

from tests.support import (
    JSON_HEADERS,
    PASSWORD,
    USERNAME,
    Console,
    api_routes,
    build_console,
    fake_application,
    fixture_database,
)
from weightroom.infrastructure.db.models import AuditLog
from weightroom.services.processes import FakeSystemdController

STATE_CHANGING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

Exercise = Callable[[Console], Any]


def _form_login(console: Console) -> Any:  # noqa: ANN401
    console.client.cookies.clear()
    return console.login()


def _form_logout(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/logout", {})


def _json_login(console: Console) -> Any:  # noqa: ANN401
    console.client.cookies.clear()
    return console.client.post(
        "/api/v1/login", json={"username": USERNAME, "password": PASSWORD}, headers=JSON_HEADERS
    )


def _json_logout(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/logout", headers=JSON_HEADERS)


def _json_reauth(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/reauth", json={"password": PASSWORD}, headers=JSON_HEADERS)


def _unit(verb: str) -> Exercise:
    """One successful control call against the fake host the console was built over."""

    def exercise(console: Console) -> Any:  # noqa: ANN401
        return console.client.post(f"/api/v1/apps/loadcoach/{verb}", headers=JSON_HEADERS)

    return exercise


def _control_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/loadcoach/control", {"verb": "restart"})


def _ollama_restart(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/ollama/restart", headers=JSON_HEADERS)


def _ollama_restart_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/ollama/restart", {})


def _settings_put(console: Console) -> Any:  # noqa: ANN401
    return console.client.put(
        "/api/v1/apps/loadcoach/settings", json={"changes": {}}, headers=JSON_HEADERS
    )


def _settings_validate(console: Console) -> Any:  # noqa: ANN401
    return console.client.post(
        "/api/v1/apps/loadcoach/settings/validate", json={"text": ""}, headers=JSON_HEADERS
    )


def _own_settings_put(console: Console) -> Any:  # noqa: ANN401
    return console.client.put(
        "/api/v1/settings", json={"telemetry.interval_ms": 1500}, headers=JSON_HEADERS
    )


def _settings_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/loadcoach/settings", {"base_mtime": ""})


def _own_settings_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/settings", {"field:telemetry.interval_ms": "1750"})


def _settings_raw(console: Console) -> Any:  # noqa: ANN401
    """The whole file, unchanged — still a write, still exactly one row."""
    body = console.client.get("/api/v1/apps/loadcoach/config", headers=JSON_HEADERS).json()
    return console.post_form(
        "/apps/loadcoach/settings/raw",
        {"text": body["text"], "base_mtime": str(body["base_mtime"] or ""), "password": PASSWORD},
    )


def _restart_for_settings(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/loadcoach/restart-for-settings", {})


def _token_create(console: Console) -> Any:  # noqa: ANN401
    """A refusal — the fake application has no `token` verb — and still exactly one row."""
    return console.post_form("/apps/loadcoach/tokens", {"name": "laptop", "scope": "read"})


def _token_revoke(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/loadcoach/tokens/revoke", {"name": "laptop"})


def _chat_conversation(console: Console) -> str:
    """A conversation made without a route, so the exercise's own row is the only one counted."""
    from weightroom.services.chat import create_conversation

    return create_conversation(console.database, backend="loadcoach", title="t", now=console.now)


def _chat_join(console: Console) -> None:
    from typing import cast

    cast(Any, console.client.app).state.chat.join()


def _chat_create_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.post(
        "/api/v1/chat/conversations",
        json={"backend": "loadcoach", "title": "t"},
        headers=JSON_HEADERS,
    )


def _chat_delete_json(console: Console) -> Any:  # noqa: ANN401
    conversation_id = _chat_conversation(console)
    return console.client.delete(
        f"/api/v1/chat/conversations/{conversation_id}", headers=JSON_HEADERS
    )


def _chat_send_json(console: Console) -> Any:  # noqa: ANN401
    import respx

    from tests.support import mock_loadcoach

    conversation_id = _chat_conversation(console)
    with respx.mock(assert_all_called=False) as router:
        mock_loadcoach(router)
        response = console.client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            json={"text": "hello"},
            headers=JSON_HEADERS,
        )
        _chat_join(console)
    return response


def _chat_attach_json(console: Console) -> Any:  # noqa: ANN401
    conversation_id = _chat_conversation(console)
    return console.client.post(
        f"/api/v1/chat/conversations/{conversation_id}/attachments",
        files={"file": ("a.md", b"a", "text/markdown")},
        data={"csrf_token": console.csrf_token()},
        headers={"Sec-Fetch-Site": "same-origin"},
    )


def _chat_create_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/chat", {"backend": "loadcoach", "title": "t"})


def _chat_send_form(console: Console) -> Any:  # noqa: ANN401
    import respx

    from tests.support import mock_loadcoach

    conversation_id = _chat_conversation(console)
    with respx.mock(assert_all_called=False) as router:
        mock_loadcoach(router)
        response = console.post_form(f"/chat/{conversation_id}/messages", {"text": "hello"})
        _chat_join(console)
    return response


def _chat_attach_form(console: Console) -> Any:  # noqa: ANN401
    conversation_id = _chat_conversation(console)
    return console.client.post(
        f"/chat/{conversation_id}/attachments",
        files={"file": ("a.md", b"a", "text/markdown")},
        data={"csrf_token": console.csrf_token()},
        headers={"Accept": "text/html"},
    )


def _chat_delete_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form(f"/chat/{_chat_conversation(console)}/delete", {})


def _chat_pending_approval(console: Console) -> tuple[str, str]:
    """A PromptCadence reply parked on an approval, and the scope cache primed as held — the
    exercise counts the decision's own row, not a `token list` subprocess."""
    import time

    from weightroom.infrastructure.db.models import Message, MessageEvent
    from weightroom.services import chat_promptcadence
    from weightroom.services.chat import create_conversation

    chat_promptcadence._SCOPE_CACHE["promptcadence"] = (time.monotonic(), True)
    conversation_id = create_conversation(
        console.database, backend="promptcadence", title="t", now=console.now
    )
    with console.database.write() as session:
        message = Message(
            conversation_id=conversation_id,
            sequence=1,
            role="assistant",
            text="",
            remote_job_id="01TRAJECTORY00000000000001",
        )
        session.add(message)
        session.flush()
        session.add(
            MessageEvent(
                message_id=message.id,
                sequence=1,
                kind="approval_pending",
                payload={
                    "message_id": message.id,
                    "status": "requested",
                    "approval_request_id": "01REQUEST0000000000000001",
                },
            )
        )
    return conversation_id, "01REQUEST0000000000000001"


def _chat_decide_json(console: Console) -> Any:  # noqa: ANN401
    import respx

    from tests.support import mock_promptcadence

    conversation_id, request_id = _chat_pending_approval(console)
    with respx.mock(assert_all_called=False) as router:
        mock_promptcadence(router)
        return console.client.post(
            f"/api/v1/chat/conversations/{conversation_id}/approvals/{request_id}",
            json={"decision": "approve"},
            headers=JSON_HEADERS,
        )


def _chat_decide_form(console: Console) -> Any:  # noqa: ANN401
    import respx

    from tests.support import mock_promptcadence

    conversation_id, request_id = _chat_pending_approval(console)
    with respx.mock(assert_all_called=False) as router:
        mock_promptcadence(router)
        return console.post_form(
            f"/chat/{conversation_id}/approvals/{request_id}", {"decision": "deny"}
        )


def _db_query_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.post(
        "/api/v1/apps/loadcoach/db/query",
        json={"sql": "SELECT count(*) FROM feedback"},
        headers=JSON_HEADERS,
    )


def _db_query_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/loadcoach/database/query", {"sql": "SELECT 1"})


EXERCISES: dict[tuple[str, str], Exercise] = {
    ("POST", "/login"): _form_login,
    ("POST", "/logout"): _form_logout,
    ("POST", "/api/v1/login"): _json_login,
    ("POST", "/api/v1/logout"): _json_logout,
    ("POST", "/api/v1/reauth"): _json_reauth,
    ("POST", "/api/v1/apps/{app}/start"): _unit("start"),
    ("POST", "/api/v1/apps/{app}/stop"): _unit("stop"),
    ("POST", "/api/v1/apps/{app}/restart"): _unit("restart"),
    ("POST", "/apps/{app}/control"): _control_form,
    ("POST", "/api/v1/ollama/restart"): _ollama_restart,
    ("POST", "/ollama/restart"): _ollama_restart_form,
    ("PUT", "/api/v1/apps/{app}/settings"): _settings_put,
    ("POST", "/api/v1/apps/{app}/settings/validate"): _settings_validate,
    ("PUT", "/api/v1/settings"): _own_settings_put,
    ("POST", "/apps/{app}/settings"): _settings_form,
    ("POST", "/settings"): _own_settings_form,
    ("POST", "/apps/{app}/settings/raw"): _settings_raw,
    ("POST", "/apps/{app}/restart-for-settings"): _restart_for_settings,
    ("POST", "/apps/{app}/tokens"): _token_create,
    ("POST", "/apps/{app}/tokens/revoke"): _token_revoke,
    ("POST", "/api/v1/chat/conversations"): _chat_create_json,
    ("DELETE", "/api/v1/chat/conversations/{conversation_id}"): _chat_delete_json,
    ("POST", "/api/v1/chat/conversations/{conversation_id}/messages"): _chat_send_json,
    ("POST", "/api/v1/chat/conversations/{conversation_id}/attachments"): _chat_attach_json,
    ("POST", "/chat"): _chat_create_form,
    ("POST", "/chat/{conversation_id}/messages"): _chat_send_form,
    ("POST", "/chat/{conversation_id}/attachments"): _chat_attach_form,
    ("POST", "/chat/{conversation_id}/delete"): _chat_delete_form,
    (
        "POST",
        "/api/v1/chat/conversations/{conversation_id}/approvals/{approval_id}",
    ): _chat_decide_json,
    ("POST", "/chat/{conversation_id}/approvals/{approval_id}"): _chat_decide_form,
    ("POST", "/api/v1/apps/{app}/db/query"): _db_query_json,
    ("POST", "/apps/{app}/database/query"): _db_query_form,
}
"""One representative, successful call per state-changing route. Add a line per new route."""


def _state_changing_routes(console: Console) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path, route in api_routes(console.client.app):
        for method in (route.methods or set()) & STATE_CHANGING:
            found.add((method, path))
    return found


def _rows(console: Console) -> int:
    with console.database.read() as session:
        return int(session.execute(select(func.count()).select_from(AuditLog)).scalar_one())


@pytest.fixture
def console(tmp_path: Path) -> Console:
    # A fake host where loadcoach is installed and its unit exists, so the control routes have
    # something to act on and each writes exactly one row.
    # A real executable answering ADR-0127's two verbs, so the settings routes have a document
    # and a file to act on rather than degrading to "not installed" and auditing a refusal.
    # And a `config show` naming a copy of LoadCoach's fixture database, for the console routes.
    database = fixture_database(tmp_path, "loadcoach-0015")
    executable, _config, _document = fake_application(
        tmp_path, "loadcoach", database_url=f"sqlite:///{database}"
    )
    return build_console(
        tmp_path / "console",
        extra_toml=f'[apps.loadcoach]\nexecutable = "{executable}"\n',
        systemd=FakeSystemdController(states={"loadcoach.service": "active"}),
    )


def test_every_state_changing_route_has_an_exercise(console: Console) -> None:
    routes = _state_changing_routes(console)
    assert routes == set(EXERCISES), (
        f"routes without an audit exercise: {sorted(routes - set(EXERCISES))}; "
        f"exercises for absent routes: {sorted(set(EXERCISES) - routes)}"
    )


@pytest.mark.parametrize(("method", "path"), sorted(EXERCISES))
def test_each_state_changing_route_writes_exactly_one_audit_row(
    console: Console, method: str, path: str
) -> None:
    console.login()  # a session for the routes that need one; its own row is counted first
    before = _rows(console)
    response = EXERCISES[(method, path)](console)
    assert response.status_code < 400, (method, path, response.text)
    assert _rows(console) == before + 1, (method, path)
