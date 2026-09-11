"""Spec §11 contract 2: every state-changing route writes exactly one ``audit_log`` row.

The test enumerates the app's routes rather than listing them: a new ``POST``/``PUT``/``PATCH``/
``DELETE`` route fails this suite until it has an entry in :data:`EXERCISES`, and every entry is
run and must add exactly one row. Later rows inherit both halves.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select

from tests.support import (
    HELLO_RECORD,
    JSON_HEADERS,
    PASSWORD,
    USERNAME,
    Console,
    api_routes,
    build_console,
    fake_application,
    fill_rows,
    fixture_database,
    prompt_application,
)
from weightroom.infrastructure.db.models import AuditLog
from weightroom.services.db_reader import effective_database_url
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


_GUARD_SQL = "DELETE FROM units WHERE id = 'none'"
"""The guard's exercises write IdeaPress, whose fake unit is absent and whose port is closed, so
they pass condition 1 without touching LoadCoach, which the chat exercises mock on its real port."""


def _fresh_reauth(console: Console) -> None:
    """Stamp the session without POST /reauth, whose own row would be a second one."""
    from sqlalchemy import update

    from weightroom.infrastructure.db.models import Session as SessionRow

    with console.database.write() as session:
        session.execute(update(SessionRow).values(reauth_at=console.now))


def _dry_run_id(console: Console) -> str:
    """The digest from the service directly, so the exercise's own row is the only one counted."""
    from typing import cast

    from weightroom.services.db_guard import dry_run

    state = cast(Any, console.client.app).state
    dry = dry_run(
        state.settings,
        state.database,
        state.controller,
        "ideapress",
        _GUARD_SQL,
        urls=state.database_urls,
        monotonic=0.0,
    )
    return str(dry.dry_run_id)


def _db_dry_run_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.post(
        "/api/v1/apps/ideapress/db/write/dry-run", json={"sql": _GUARD_SQL}, headers=JSON_HEADERS
    )


def _db_write_json(console: Console) -> Any:  # noqa: ANN401
    _fresh_reauth(console)
    return console.client.post(
        "/api/v1/apps/ideapress/db/write",
        json={"sql": _GUARD_SQL, "tables_typed": ["units"], "dry_run_id": _dry_run_id(console)},
        headers=JSON_HEADERS,
    )


def _db_dry_run_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/ideapress/database/units/write/dry-run", {"sql": _GUARD_SQL})


def _db_write_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form(
        "/apps/ideapress/database/units/write",
        {
            "sql": _GUARD_SQL,
            "tables_typed": "units",
            "dry_run_id": _dry_run_id(console),
            "password": PASSWORD,
        },
    )


def _db_curated(verb: str) -> Exercise:
    def exercise(console: Console) -> Any:  # noqa: ANN401
        return console.client.post(f"/api/v1/apps/ideapress/db/{verb}", headers=JSON_HEADERS)

    return exercise


def _db_restore_json(console: Console) -> Any:  # noqa: ANN401
    _fresh_reauth(console)
    return console.client.post(
        "/api/v1/apps/ideapress/db/restore",
        json={"file": "/tmp/ideapress-backup.sqlite3", "name_typed": "ideapress"},  # noqa: S108
        headers=JSON_HEADERS,
    )


def _db_curated_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/apps/ideapress/database/curated", {"verb": "backup"})


def _db_delete_results_json(console: Console) -> Any:  # noqa: ANN401
    """FreeWeight's own preview, mocked on its default port so no real FreeWeight is reached."""
    import httpx
    import respx

    with respx.mock() as router:
        router.post("http://127.0.0.1:8765/api/v1/database/delete-preview").mock(
            return_value=httpx.Response(200, json={"run_count": 0, "token": "t"})
        )
        return console.client.post(
            "/api/v1/apps/freeweight/db/delete-results",
            json={"scope": "model", "selector": "m"},
            headers=JSON_HEADERS,
        )


def _self_db_backup(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/db/backup", headers=JSON_HEADERS)


def _self_db_upgrade(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/db/upgrade", headers=JSON_HEADERS)


def _self_backups_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/backups/self", {"verb": "backup"})


_CATALOG_CANONICAL_ID = "ollama/audit-exercise@sha256:deadbeef"
_CATALOG_MODEL_ID = "01CATALOGEXERCISE000000001"


def _seed_catalog_model(console: Console) -> str:
    """One LoadCoach model row, on the same fixture copy the ``console`` fixture already built —
    the catalog join has nothing to enable, drop in over or delete without one."""
    from typing import cast

    state = cast(Any, console.client.app).state
    url, reason = effective_database_url(state.settings, "loadcoach")
    assert url is not None, reason
    fill_rows(
        Path(url.removeprefix("sqlite:///")),
        "models",
        [
            {
                "id": _CATALOG_MODEL_ID,
                "provider_kind": "ollama",
                "provider_model_name": "audit-exercise",
                "canonical_id": _CATALOG_CANONICAL_ID,
                "identity_confidence": "digest",
                "first_seen_at": "2026-01-01T00:00:00+00:00",
                "last_seen_at": "2026-01-01T00:00:00+00:00",
                "available": 1,
                "enabled": 1,
            }
        ],
    )
    return _CATALOG_CANONICAL_ID


def _catalog_pull_json(console: Console) -> Any:  # noqa: ANN401
    """Starting a pull never fails here (services/catalog.py); the worker thread runs unmocked
    and harmlessly fails in the background against a closed port."""
    return console.client.post(
        "/api/v1/catalog/pull", json={"name": "audit-exercise"}, headers=JSON_HEADERS
    )


def _catalog_pull_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/catalog/pull-form", {"name": "audit-exercise"})


def _mock_ollama_ps(router: Any) -> None:  # noqa: ANN401 — a respx router
    """``services/catalog.py``'s join always asks Ollama for residency; inside a respx context
    that call needs an answer too, or respx refuses it as unmocked rather than letting it degrade
    to a real, gracefully-handled connection error the way an un-mocked test run does."""
    import httpx

    router.get("http://127.0.0.1:11434/api/ps").mock(
        return_value=httpx.Response(200, json={"models": []})
    )


def _catalog_enable_json(console: Console) -> Any:  # noqa: ANN401
    import httpx
    import respx

    canonical_id = _seed_catalog_model(console)
    with respx.mock(assert_all_mocked=False) as router:
        _mock_ollama_ps(router)
        router.post(f"http://127.0.0.1:8766/api/v1/models/{_CATALOG_MODEL_ID}/enabled").mock(
            return_value=httpx.Response(200, json={"enabled": False})
        )
        return console.client.post(
            f"/api/v1/catalog/{canonical_id}/enabled",
            json={"app": "loadcoach", "enabled": False},
            headers=JSON_HEADERS,
        )


def _catalog_enable_form(console: Console) -> Any:  # noqa: ANN401
    import httpx
    import respx

    canonical_id = _seed_catalog_model(console)
    with respx.mock(assert_all_mocked=False) as router:
        _mock_ollama_ps(router)
        router.post(f"http://127.0.0.1:8766/api/v1/models/{_CATALOG_MODEL_ID}/enabled").mock(
            return_value=httpx.Response(200, json={"enabled": False})
        )
        return console.post_form(
            "/catalog/enable", {"canonical_id": canonical_id, "app": "loadcoach"}
        )


def _catalog_delete_json(console: Console) -> Any:  # noqa: ANN401
    """The preview half (Database Standards §8): FreeWeight and Ollama are both unreachable here
    and degrade to ``None``/``False`` rather than an error (services/catalog.py)."""
    canonical_id = _seed_catalog_model(console)
    return console.client.request(
        "DELETE", f"/api/v1/catalog/{canonical_id}", json={}, headers=JSON_HEADERS
    )


def _catalog_delete_form(console: Console) -> Any:  # noqa: ANN401
    canonical_id = _seed_catalog_model(console)
    return console.post_form("/catalog/delete", {"canonical_id": canonical_id})


def _catalog_llamacpp_directory(router: Any) -> None:  # noqa: ANN401 — a respx router
    """LoadCoach answers as llama.cpp; FreeWeight's own provider is mocked too (``ollama``, no
    directory) so ``llamacpp_targets``' call to it is answered rather than refused by respx for
    being unmocked — FreeWeight is not installed in this fixture and has nothing to contribute."""
    import httpx

    _mock_ollama_ps(router)
    directory = tempfile.mkdtemp(prefix="wr-gym-audit-catalog-")
    router.get("http://127.0.0.1:8765/api/v1/provider").mock(
        return_value=httpx.Response(200, json={"provider": {"kind": "ollama"}})
    )
    router.get("http://127.0.0.1:8766/api/v1/providers").mock(
        return_value=httpx.Response(
            200,
            json={
                "registrations": [
                    {"name": "local", "kind": "llamacpp", "model_directory": directory}
                ]
            },
        )
    )
    router.post("http://127.0.0.1:8766/api/v1/models/discover").mock(
        return_value=httpx.Response(200, json={"added": 0})
    )


def _catalog_dropin_json(console: Console) -> Any:  # noqa: ANN401
    """The JSON route answers with the drop-in result directly, never re-fetching the catalog
    (unlike the page form below), so the ollama residency mock in the shared helper goes unused
    here — ``assert_all_called=False`` for that reason alone."""
    import respx

    source = Path(tempfile.mkstemp(suffix=".gguf")[1])
    source.write_bytes(b"GGUF" + b"\x00" * 2000)
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        _catalog_llamacpp_directory(router)
        return console.client.post(
            "/api/v1/catalog/dropin",
            data={"path": str(source), "csrf_token": console.csrf_token()},
            headers={"Sec-Fetch-Site": "same-origin"},
        )


def _catalog_dropin_form(console: Console) -> Any:  # noqa: ANN401
    import respx

    source = Path(tempfile.mkstemp(suffix=".gguf")[1])
    source.write_bytes(b"GGUF" + b"\x00" * 2000)
    with respx.mock(assert_all_mocked=False) as router:
        _catalog_llamacpp_directory(router)
        return console.post_form("/catalog/dropin-form", {"path": str(source)})


def _queued_job(console: Console) -> str:
    """A queued job made without a route, so the exercise's own row is the only one counted."""
    from weightroom.services.jobs import enqueue

    return enqueue(console.database, kind="docs_index", params={}, now=console.now).id


def _schedule_id(console: Console) -> str:
    from weightroom.services.jobs import list_schedules

    return next(one.id for one in list_schedules(console.database) if one.kind == "docs_index")


def _jobs_enqueue_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.post("/api/v1/jobs", json={"kind": "docs_index"}, headers=JSON_HEADERS)


def _jobs_cancel_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.post(f"/api/v1/jobs/{_queued_job(console)}/cancel", headers=JSON_HEADERS)


def _jobs_schedule_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.put(
        f"/api/v1/jobs/schedules/{_schedule_id(console)}",
        json={"cron": "0 6 * * *"},
        headers=JSON_HEADERS,
    )


def _jobs_enqueue_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form("/jobs/enqueue", {"kind": "docs_index", "params": "{}"})


def _jobs_cancel_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form(f"/jobs/{_queued_job(console)}/cancel", {})


def _jobs_schedule_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form(
        f"/jobs/schedules/{_schedule_id(console)}", {"cron": "0 6 * * *", "params": "{}"}
    )


def _open_alert(console: Console) -> str:
    """An active alert opened by the service, not a route, so only the exercise's row counts."""
    from weightroom.domain.alerts import Firing, Reading
    from weightroom.services.alerts import active_alerts, apply

    firing = Firing("ollama.service", {"line": "oom-kill ollama.service", "cursor": "c"})
    apply(console.database, Reading("memory_cap", (firing,)), now=console.now)
    return active_alerts(console.database)[0].id


def _alert_ack_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.post(
        f"/api/v1/alerts/{_open_alert(console)}/acknowledge", headers=JSON_HEADERS
    )


def _alert_ack_form(console: Console) -> Any:  # noqa: ANN401
    return console.post_form(f"/alerts/{_open_alert(console)}/acknowledge", {"next": "/alerts"})


def _override_record() -> dict[str, Any]:
    import copy

    body = copy.deepcopy(HELLO_RECORD)
    body["version"] = "1.1.0"
    body["metadata"]["change_reason"] = "An audit exercise's override."
    return body


def _existing_override() -> None:
    """An override written straight to disk, so only the deletion's own row is counted."""
    from weightroom.services.prompts import canonical_text, override_path

    path = override_path("ideapress", "stages.hello")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(_override_record()), encoding="utf-8")


def _prompt_put_json(console: Console) -> Any:  # noqa: ANN401
    return console.client.put(
        "/api/v1/apps/ideapress/prompts/stages.hello",
        json={"record": _override_record()},
        headers=JSON_HEADERS,
    )


def _prompt_delete_json(console: Console) -> Any:  # noqa: ANN401
    _existing_override()
    return console.client.delete(
        "/api/v1/apps/ideapress/prompts/stages.hello/override", headers=JSON_HEADERS
    )


def _prompt_write_form(console: Console) -> Any:  # noqa: ANN401
    import json

    return console.post_form(
        "/apps/ideapress/prompts/stages.hello", {"record": json.dumps(_override_record())}
    )


def _prompt_delete_form(console: Console) -> Any:  # noqa: ANN401
    _existing_override()
    return console.post_form("/apps/ideapress/prompts/stages.hello/delete", {})


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
    ("POST", "/api/v1/apps/{app}/db/write/dry-run"): _db_dry_run_json,
    ("POST", "/api/v1/apps/{app}/db/write"): _db_write_json,
    ("POST", "/apps/{app}/database/{table}/write/dry-run"): _db_dry_run_form,
    ("POST", "/apps/{app}/database/{table}/write"): _db_write_form,
    ("POST", "/api/v1/apps/{app}/db/backup"): _db_curated("backup"),
    ("POST", "/api/v1/apps/{app}/db/upgrade"): _db_curated("upgrade"),
    ("POST", "/api/v1/apps/{app}/db/restore"): _db_restore_json,
    ("POST", "/api/v1/apps/{app}/db/delete-results"): _db_delete_results_json,
    ("POST", "/apps/{app}/database/curated"): _db_curated_form,
    ("POST", "/api/v1/catalog/pull"): _catalog_pull_json,
    ("POST", "/catalog/pull-form"): _catalog_pull_form,
    ("POST", "/api/v1/catalog/{ref:path}/enabled"): _catalog_enable_json,
    ("POST", "/catalog/enable"): _catalog_enable_form,
    ("DELETE", "/api/v1/catalog/{ref:path}"): _catalog_delete_json,
    ("POST", "/catalog/delete"): _catalog_delete_form,
    ("POST", "/api/v1/catalog/dropin"): _catalog_dropin_json,
    ("POST", "/catalog/dropin-form"): _catalog_dropin_form,
    ("POST", "/api/v1/db/backup"): _self_db_backup,
    ("POST", "/api/v1/db/upgrade"): _self_db_upgrade,
    ("POST", "/backups/self"): _self_backups_form,
    ("POST", "/api/v1/jobs"): _jobs_enqueue_json,
    ("POST", "/api/v1/jobs/{job_id}/cancel"): _jobs_cancel_json,
    ("PUT", "/api/v1/jobs/schedules/{schedule_id}"): _jobs_schedule_json,
    ("POST", "/jobs/enqueue"): _jobs_enqueue_form,
    ("POST", "/jobs/{job_id}/cancel"): _jobs_cancel_form,
    ("POST", "/jobs/schedules/{schedule_id}"): _jobs_schedule_form,
    ("POST", "/api/v1/alerts/{alert_id}/acknowledge"): _alert_ack_json,
    ("POST", "/alerts/{alert_id}/acknowledge"): _alert_ack_form,
    ("PUT", "/api/v1/apps/{app}/prompts/{prompt_id}"): _prompt_put_json,
    ("DELETE", "/api/v1/apps/{app}/prompts/{prompt_id}/override"): _prompt_delete_json,
    ("POST", "/apps/{app}/prompts/{prompt_id}"): _prompt_write_form,
    ("POST", "/apps/{app}/prompts/{prompt_id}/delete"): _prompt_delete_form,
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
    return audit_console(tmp_path)


def audit_console(tmp_path: Path, *, loadcoach_token: str | None = None) -> Console:
    """The console every exercise in :data:`EXERCISES` runs against.

    Args:
        tmp_path: A fresh directory.
        loadcoach_token: When given, written to a token file named by ``[apps.loadcoach]
            api_key_file`` — a secret the redaction sweep (``test_redaction_sweep.py``) then
            asserts never reaches an audit row or a log line.
    """
    # A fake host where loadcoach is installed and its unit exists, so the control routes have
    # something to act on and each writes exactly one row.
    # A real executable answering ADR-0127's two verbs, so the settings routes have a document
    # and a file to act on rather than degrading to "not installed" and auditing a refusal.
    # And a `config show` naming a copy of LoadCoach's fixture database, for the console routes.
    database = fixture_database(tmp_path, "loadcoach-0015")
    executable, _config, _document = fake_application(
        tmp_path, "loadcoach", database_url=f"sqlite:///{database}"
    )
    # IdeaPress for the guard: its fake unit is absent and its base_url is a closed port, so
    # condition 1 holds without depending on what runs on this machine.
    ideapress_database = fixture_database(tmp_path, "ideapress-0010")
    ideapress, _config, _document = fake_application(
        tmp_path, "ideapress", database_url=f"sqlite:///{ideapress_database}"
    )
    # And a prompt pack, answered before the fake's own verbs, for the prompt editor's routes.
    ideapress = prompt_application(tmp_path, "ideapress", [HELLO_RECORD], fallback=ideapress)
    token_line = ""
    if loadcoach_token is not None:
        token_file = tmp_path / "loadcoach.token"
        token_file.write_text(loadcoach_token + "\n", encoding="utf-8")
        token_line = f'api_key_file = "{token_file}"\n'
    return build_console(
        tmp_path / "console",
        extra_toml=(
            f'[apps.loadcoach]\nexecutable = "{executable}"\n{token_line}'
            f'[apps.ideapress]\nexecutable = "{ideapress}"\nbase_url = "http://127.0.0.1:9"\n'
        ),
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
