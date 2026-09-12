"""weightroom.services.app_api — the one client the application pages read and act through."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from weightroom.config import Settings, load_settings
from weightroom.services.app_api import (
    AppRefused,
    AppTimedOut,
    call,
    download,
    outcome_of,
    stream,
)
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


def test_an_application_slower_than_the_timeout_is_not_a_refusal(settings: Settings) -> None:
    """WP6 finding 3: a call the console stopped waiting for was reported as the application's
    refusal, while FreeWeight went on working and finished the job four minutes later.

    A real server, answering after the console has given up, rather than a mocked exception: the
    type httpx raises for a slow answer is the whole point of the distinction.
    """
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Slow(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler's own name
            time.sleep(0.6)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args: object) -> None:
            """Quiet: the handler's default writes every request to stderr."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    config = Path(str(settings.apps.promptcadence.api_key_file)).with_name("slow.toml")
    config.write_text(
        f'[apps.promptcadence]\nbase_url = "http://127.0.0.1:{server.server_address[1]}"\n'
    )
    slow_settings = load_settings(config_path=config).settings
    try:
        with httpx.Client() as client, pytest.raises(AppTimedOut) as caught:
            call(
                client,
                slow_settings,
                "promptcadence",
                "POST",
                "models/discover",
                timeout_seconds=0.1,
            )
    finally:
        server.shutdown()
    assert "work may still be running" in caught.value.message
    assert caught.value.code == AppUnreachable.code  # a client branching on the code sees no change
    assert outcome_of(caught.value) == "pending"


@respx.mock
def test_a_refusal_the_application_sent_is_audited_as_one(settings: Settings) -> None:
    """The other half: an answer *is* the application's word, and stays ``refused``."""
    respx.post(f"{BASE}/api/v1/models/discover").mock(
        return_value=httpx.Response(409, json={"error": {"code": "PROVIDER_UNAVAILABLE"}})
    )
    with httpx.Client() as client, pytest.raises(AppRefused) as caught:
        call(client, settings, "promptcadence", "POST", "models/discover")
    assert outcome_of(caught.value) == "refused"
    assert outcome_of(AppUnreachable("nothing answered", details={})) == "refused"


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


@respx.mock
def test_a_download_answers_its_headers_then_streams_the_bytes_unchanged(
    settings: Settings,
) -> None:
    chunks = [b"run_id,metric_key\n", b"01A,ttft_ms\n", b"01B,load_ms\n"]
    route = respx.get(f"{BASE}/api/v1/results/export").mock(
        return_value=httpx.Response(
            200,
            headers={
                "content-type": "text/csv; charset=utf-8",
                "content-disposition": 'attachment; filename="freeweight-run.csv"',
            },
            content=iter(chunks),
        )
    )
    with httpx.Client() as client:
        headers, body = download(
            client, settings, "promptcadence", "results/export",
            params={"format": "csv", "selector": None},
        )  # fmt: skip
        assert headers == {
            "content-type": "text/csv; charset=utf-8",
            "content-disposition": 'attachment; filename="freeweight-run.csv"',
        }
        assert list(body) == chunks
    sent = route.calls.last.request
    assert sent.url.params["format"] == "csv"
    assert "selector" not in sent.url.params
    assert sent.headers["Authorization"] == f"Bearer {TOKEN}"


@respx.mock
def test_a_refused_download_raises_before_any_byte(settings: Settings) -> None:
    respx.get(f"{BASE}/api/v1/results/export").mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "That selection covers 612 runs; the limit is 500.",
                    "details": {"matched": 612, "limit": 500},
                }
            },
        )
    )
    with httpx.Client() as client, pytest.raises(AppRefused) as raised:
        download(client, settings, "promptcadence", "results/export")
    assert raised.value.details["app_code"] == "VALIDATION_ERROR"
    assert raised.value.details["app_details"] == {"matched": 612, "limit": 500}
    assert "612 runs" in raised.value.message


@respx.mock
def test_an_unanswered_download_is_unreachable(settings: Settings) -> None:
    respx.get(f"{BASE}/api/v1/results/export").mock(side_effect=httpx.ConnectError("refused"))
    with httpx.Client() as client, pytest.raises(AppUnreachable):
        download(client, settings, "promptcadence", "results/export")
