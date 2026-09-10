"""Test support: a console with an account, a movable clock, and a CSRF-aware form poster."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from mirrorwall import CSRF_COOKIE_NAME

from weightroom.config import Settings, load_settings
from weightroom.services.auth import create_operator
from weightroom.services.database import Database, ensure_ready
from weightroom.services.journal import JournalReader
from weightroom.services.processes import FakeSystemdController
from weightroom.services.tls import HostIdentity, TlsStatus, init_tls
from weightroom.web.app import create_app

IDENTITY = HostIdentity("jordan-main", ("10.77.10.84",))
USERNAME = "jordan"
PASSWORD = "correct horse battery"  # noqa: S105 — a test credential
JSON_HEADERS = {"Content-Type": "application/json", "Sec-Fetch-Site": "same-origin"}


@dataclass
class Console:
    """One built console: its client, its database, and a clock the tests move."""

    settings: Settings
    database: Database
    client: TestClient
    tls: TlsStatus | None = None
    host: FakeSystemdController | None = None
    now: datetime = field(default_factory=lambda: datetime(2026, 9, 9, 12, 0, tzinfo=UTC))

    def advance(self, **delta: float) -> None:
        """Move the clock forward by ``timedelta(**delta)``."""
        self.now = self.now + timedelta(**delta)

    def csrf_token(self, path: str = "/login") -> str:
        """Fetch a form page and return its token; the cookie lands in the client jar."""
        page = self.client.get(path, headers={"Accept": "text/html"})
        match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
        if match:
            return match.group(1)
        return str(self.client.cookies.get(CSRF_COOKIE_NAME, ""))

    def post_form(self, path: str, data: dict[str, str], *, follow: bool = False) -> Any:  # noqa: ANN401 — an httpx Response
        """POST a form with the double-submit token attached."""
        token = self.csrf_token()
        return self.client.post(
            path,
            data={**data, "csrf_token": token},
            headers={"Accept": "text/html"},
            follow_redirects=follow,
        )

    def login(self, username: str = USERNAME, password: str = PASSWORD) -> Any:  # noqa: ANN401
        """Log in through the form; the session cookie lands in the client jar."""
        return self.post_form("/login", {"username": username, "password": password})


def build_console(
    tmp_path: Path,
    *,
    account: bool = True,
    host: str = "127.0.0.1",
    extra_toml: str = "",
    systemd: FakeSystemdController | None = None,
    journal: JournalReader | None = None,
) -> Console:
    """A console on a fresh SQLite file with the CA issued and, by default, one operator.

    The systemd boundary is a fake by default and the journal reader is given no ``journalctl``,
    so no test reaches the developer's own session manager (spec §20 criterion 10).
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    file = tmp_path / "console.toml"
    lines = [f'[server]\nhost = "{host}"\n']
    if host != "127.0.0.1":
        lines.append('allowed_hosts = ["jordan-main.local", "10.77.10.84"]\n')
    lines.append(extra_toml)
    lines.append(f'[storage]\ndatabase_url = "sqlite:///{tmp_path}/weightroom.sqlite3"\n')
    lines.append(f'[tls]\ndirectory = "{tmp_path}/tls"\n')
    file.write_text("".join(lines))
    settings = load_settings(config_path=file).settings
    url = settings.storage.database_url or ""
    database = Database.from_url(url)
    ensure_ready(database, auto_migrate=True)
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    if account:
        create_operator(database, username=USERNAME, password=PASSWORD, now=now)
    tls = init_tls(settings, identity=IDENTITY, now=now)
    controller = systemd if systemd is not None else FakeSystemdController()
    reader = journal if journal is not None else JournalReader(which=lambda _name: None)
    app = create_app(
        settings,
        tls=tls,
        identity=IDENTITY,
        config_path=file,
        controller=controller,
        journal=reader,
    )
    # The lifespan would open its own handle; tests share this one and never enter the lifespan.
    app.state.database = database
    app.state.attachments_root = tmp_path / "attachments"
    console = Console(
        settings=settings,
        database=database,
        client=TestClient(app),
        tls=tls,
        host=controller,
    )
    app.state.clock = lambda: console.now
    console.client = TestClient(app, base_url="https://localhost", follow_redirects=False)
    return console


SCHEMA_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "schemas"

REFUSAL_MARKER = "refuse_me = true"
"""A line the fake application's `config validate --file` refuses, so a test can watch a real
refusal come back in the application's own words rather than mocking the refusal path."""


def fake_application(
    tmp_path: Path,
    app: str,
    *,
    config_toml: str = "",
    document: dict[str, Any] | None = None,
    schema_exit: int = 0,
) -> tuple[Path, Path, dict[str, Any]]:
    """An executable that answers ADR-0127's two verbs, over a real config file in ``tmp_path``.

    A shell script rather than a mock, because the console reaches every application by launching
    it: the argv, the exit code and the captured output are the contract this row is built on,
    and a monkeypatched function would test none of them.

    Args:
        tmp_path: Where the executable, the config file and the document live.
        app: One of the four; its committed schema document is the starting point.
        config_toml: The config file's initial text.
        document: An override for the document; the committed fixture otherwise.
        schema_exit: What `config schema` exits with — non-zero exercises the degraded page.

    Returns:
        ``(executable, config_path, document)``.
    """
    directory = tmp_path / app
    directory.mkdir(parents=True, exist_ok=True)
    config_path = directory / "config.toml"
    config_path.write_text(config_toml, encoding="utf-8")
    body = document
    if body is None:
        body = json.loads((SCHEMA_FIXTURES / f"{app}.json").read_text(encoding="utf-8"))
    body["config_path"] = str(config_path)
    document_file = directory / "schema.json"
    document_file.write_text(json.dumps(body), encoding="utf-8")
    executable = directory / app
    executable.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "config" ] && [ "$2" = "schema" ]; then\n'
        f"  cat {document_file}\n"
        f"  exit {schema_exit}\n"
        "fi\n"
        'if [ "$1" = "config" ] && [ "$2" = "validate" ]; then\n'
        f'  if grep -q "{REFUSAL_MARKER}" "$4"; then\n'
        f'    echo "{app}: refuse_me is not a configuration key" >&2\n'
        "    exit 3\n"
        "  fi\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable, config_path, body


def api_routes(app: Any) -> list[tuple[str, APIRoute]]:  # noqa: ANN401 — a FastAPI app
    """Every ``(full_path, APIRoute)`` in ``app``, descending into included routers.

    FastAPI ≥ 0.140 keeps an included router as an ``_IncludedRouter`` whose routes carry the
    un-prefixed path; the prefix lives on its include context.
    """
    found: list[tuple[str, APIRoute]] = []
    pending: list[tuple[str, Any]] = [("", route) for route in app.routes]
    while pending:
        prefix, route = pending.pop()
        if isinstance(route, APIRoute):
            found.append((prefix + route.path, route))
        inner = getattr(route, "original_router", None)
        if inner is not None:
            context = getattr(route, "include_context", None)
            sub_prefix = prefix + str(getattr(context, "prefix", "") or "")
            pending.extend((sub_prefix, sub) for sub in inner.routes)
    return found


CHAT_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "chat"
LOADCOACH_URL = "http://127.0.0.1:8766"


def mock_loadcoach(
    router: Any,  # noqa: ANN401 — a respx router
    *,
    stream: bytes | str | Exception | None = None,
    version: str = "1.5.0",
) -> Any:  # noqa: ANN401 — the respx route for POST /generate/stream
    """LoadCoach as the console sees it: a version probe, and one recorded stream replayed.

    ``stream`` is a fixture file name under ``tests/fixtures/chat``, raw SSE bytes, or an
    exception the transport raises. The recordings are the reference machine's own streams.
    """
    import httpx

    router.get(f"{LOADCOACH_URL}/api/v1/version").mock(
        return_value=httpx.Response(
            200,
            json={
                "application": {"name": "loadcoach", "version": version},
                "api": {"current": "v1"},
            },
        )
    )
    route = router.post(f"{LOADCOACH_URL}/api/v1/generate/stream")
    if isinstance(stream, Exception):
        route.mock(side_effect=stream)
    else:
        body = stream if stream is not None else "loadcoach-1.5.0-gpt-oss-thinking.sse"
        if isinstance(body, str) and body.endswith(".sse"):
            body = (CHAT_FIXTURES / body).read_bytes()
        route.mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=body if isinstance(body, bytes) else body.encode(),
            )
        )
    return route


PROMPTCADENCE_URL = "http://127.0.0.1:8768"
RECORDED_TRAJECTORY = "01M253YZNV3QQY0CZPWH0E4AYC"


def mock_promptcadence(
    router: Any,  # noqa: ANN401 — a respx router
    *,
    stream: bytes | str = "promptcadence-1.3.3-completed.sse",
    turns: str = "promptcadence-1.3.3-completed-turns.json",
    trajectory_id: str = RECORDED_TRAJECTORY,
    egress: list[dict[str, Any]] | None = None,
    tier_remote: bool = False,
    submit_status: int = 202,
    submit_error: dict[str, Any] | None = None,
) -> dict[str, Any]:  # noqa: ANN401 — the respx routes by name
    """PromptCadence as the console sees it, replaying the reference machine's recorded trajectory.

    LoadCoach's explanation for the turn's job is mocked too, because the decision line under a
    PromptCadence reply reads it (services/chat.py ``_promptcadence_routing``).
    """
    import httpx

    router.get(f"{PROMPTCADENCE_URL}/api/v1/version").mock(
        return_value=httpx.Response(
            200, json={"application": "promptcadence", "version": "1.3.3", "api_version": "v1"}
        )
    )
    submitted = {"trajectory_id": trajectory_id, "state": "queued"}
    submit = router.post(f"{PROMPTCADENCE_URL}/api/v1/trajectories").mock(
        return_value=httpx.Response(
            submit_status, json=submit_error if submit_error is not None else submitted
        )
    )
    body = stream
    if isinstance(body, str) and body.endswith(".sse"):
        body = (CHAT_FIXTURES / body).read_bytes()
    events = router.get(url__regex=rf"{PROMPTCADENCE_URL}/api/v1/trajectories/[^/]+/stream").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=body if isinstance(body, bytes) else body.encode(),
        )
    )
    router.get(url__regex=rf"{PROMPTCADENCE_URL}/api/v1/trajectories/[^/]+/turns").mock(
        return_value=httpx.Response(200, content=(CHAT_FIXTURES / turns).read_bytes())
    )
    router.get(f"{PROMPTCADENCE_URL}/api/v1/egress-decisions").mock(
        return_value=httpx.Response(200, json={"items": egress or []})
    )
    router.get(f"{PROMPTCADENCE_URL}/api/v1/tiers").mock(
        return_value=httpx.Response(
            200, json={"rows": [{"name": "local_fast", "is_remote": tier_remote}]}
        )
    )
    router.get(url__regex=rf"{LOADCOACH_URL}/api/v1/jobs/[^/]+/explanation").mock(
        return_value=httpx.Response(
            200, content=(CHAT_FIXTURES / "loadcoach-1.3.1-explanation.json").read_bytes()
        )
    )
    decided = {"trajectory_id": trajectory_id, "state": "executing", "already_resolved": False}
    approve = router.post(
        url__regex=rf"{PROMPTCADENCE_URL}/api/v1/trajectories/[^/]+/approve"
    ).mock(return_value=httpx.Response(200, json={**decided, "minted": []}))
    deny = router.post(url__regex=rf"{PROMPTCADENCE_URL}/api/v1/trajectories/[^/]+/deny").mock(
        return_value=httpx.Response(200, json={**decided, "state": "failed"})
    )
    return {"submit": submit, "stream": events, "approve": approve, "deny": deny}


def promptcadence_token_cli(tmp_path: Path, *, scopes: list[str]) -> Path:
    """A ``promptcadence`` executable whose ``token list --json`` names the console's token."""
    directory = tmp_path / "promptcadence-cli"
    directory.mkdir(parents=True, exist_ok=True)
    listing = directory / "tokens.json"
    listing.write_text(
        json.dumps({"items": [{"name": "weightroom", "scopes": scopes, "active": True}]}),
        encoding="utf-8",
    )
    executable = directory / "promptcadence"
    executable.write_text(
        f'#!/bin/sh\nif [ "$1" = "token" ]; then cat {listing}; fi\nexit 0\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable
