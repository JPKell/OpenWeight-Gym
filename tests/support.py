"""Test support: a console with an account, a movable clock, and a CSRF-aware form poster."""

from __future__ import annotations

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
from weightroom.services.tls import HostIdentity, init_tls
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
) -> Console:
    """A console on a fresh SQLite file with the CA issued and, by default, one operator."""
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
    app = create_app(settings, tls=tls, identity=IDENTITY, config_path=file)
    # The lifespan would open its own handle; tests share this one and never enter the lifespan.
    app.state.database = database
    console = Console(settings=settings, database=database, client=TestClient(app))
    app.state.clock = lambda: console.now
    console.client = TestClient(app, base_url="https://localhost", follow_redirects=False)
    return console


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
