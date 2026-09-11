"""weightroom.services.app_api — the one client the application pages read and act through."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from weightroom.config import Settings, load_settings
from weightroom.services.app_api import AppRefused, call, stream
from weightroom.services.apps import AppUnreachable

BASE = "http://127.0.0.1:8768"
TOKEN = "pc-test-token-not-a-secret"  # noqa: S105 — a test value


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    token = tmp_path / "promptcadence.token"
    token.write_text(TOKEN + "\n", encoding="utf-8")
    config = tmp_path / "console.toml"
    config.write_text(f'[apps.promptcadence]\nbase_url = "{BASE}"\napi_key_file = "{token}"\n')
    return load_settings(config_path=config).settings


@respx.mock
def test_a_call_carries_the_bearer_drops_none_params_and_answers_the_body(
    settings: Settings,
) -> None:
    route = respx.get(f"{BASE}/api/v1/trajectories").mock(
        return_value=httpx.Response(200, json={"items": [{"trajectory_id": "t1"}]})
    )
    with httpx.Client() as client:
        body = call(
            client, settings, "promptcadence", "GET", "trajectories",
            params={"state": None, "limit": 50},
        )  # fmt: skip
    assert body == {"items": [{"trajectory_id": "t1"}]}
    sent = route.calls.last.request
    assert sent.headers["Authorization"] == f"Bearer {TOKEN}"
    assert sent.url.params.get("limit") == "50"
    assert "state" not in sent.url.params


@respx.mock
def test_a_refusal_keeps_the_applications_own_code_and_words(settings: Settings) -> None:
    respx.post(f"{BASE}/api/v1/trajectories/t1/cancel").mock(
        return_value=httpx.Response(
            409,
            json={"error": {"code": "TRAJECTORY_NOT_CANCELLABLE", "message": "t1 is completed"}},
        )
    )
    with httpx.Client() as client, pytest.raises(AppRefused) as raised:
        call(client, settings, "promptcadence", "POST", "trajectories/t1/cancel")
    assert raised.value.details["app_code"] == "TRAJECTORY_NOT_CANCELLABLE"
    assert raised.value.details["status"] == 409
    assert "t1 is completed" in raised.value.message


@respx.mock
def test_a_refusal_without_the_envelope_names_the_status(settings: Settings) -> None:
    respx.get(f"{BASE}/api/v1/tiers").mock(return_value=httpx.Response(502, text="bad gateway"))
    with httpx.Client() as client, pytest.raises(AppRefused) as raised:
        call(client, settings, "promptcadence", "GET", "tiers")
    assert raised.value.details["app_code"] == "HTTP_502"


@respx.mock
def test_no_answer_and_a_body_that_is_not_json_are_unreachable(settings: Settings) -> None:
    respx.get(f"{BASE}/api/v1/tools").mock(side_effect=httpx.ConnectError("refused"))
    respx.get(f"{BASE}/api/v1/tiers").mock(return_value=httpx.Response(200, text="<html>"))
    with httpx.Client() as client:
        with pytest.raises(AppUnreachable):
            call(client, settings, "promptcadence", "GET", "tools")
        with pytest.raises(AppUnreachable):
            call(client, settings, "promptcadence", "GET", "tiers")


@respx.mock
def test_a_stream_is_proxied_unchanged_with_last_event_id_carried(settings: Settings) -> None:
    frames = "id: 7\nevent: step.started\ndata: {}\n\n"
    route = respx.get(f"{BASE}/api/v1/trajectories/t1/stream").mock(
        return_value=httpx.Response(
            200, headers={"content-type": "text/event-stream"}, content=frames.encode()
        )
    )
    with httpx.Client() as client:
        text = "".join(
            stream(client, settings, "promptcadence", "trajectories/t1/stream", last_event_id="6")
        )
    assert text == frames
    assert route.calls.last.request.headers["Last-Event-ID"] == "6"


@respx.mock
def test_a_refused_stream_ends_with_the_code_and_a_closing_frame(settings: Settings) -> None:
    respx.get(f"{BASE}/api/v1/trajectories/nope/stream").mock(
        return_value=httpx.Response(
            404, json={"error": {"code": "TRAJECTORY_NOT_FOUND", "message": "no such trajectory"}}
        )
    )
    with httpx.Client() as client:
        text = "".join(stream(client, settings, "promptcadence", "trajectories/nope/stream"))
    assert "event: error" in text
    assert "TRAJECTORY_NOT_FOUND" in text
    assert "event: stream.closed" in text
