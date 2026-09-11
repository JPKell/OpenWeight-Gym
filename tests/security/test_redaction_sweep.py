"""Spec §14: redaction over every audited action.

Every exercise in :data:`tests.security.test_audit_routes.EXERCISES` — one call per
state-changing route — runs against a console that holds two secrets: the operator's password
and a LoadCoach bearer token. Afterwards no audit row (``target``, ``params``, ``message``) and no
log line carries either, whichever route wrote it. The audit registry proves one row per route;
this proves what the rows are allowed to say (security standards §14, "log output contains no
secret for a request that carried one", over the persisted trail rather than a single request).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from tests.security.test_audit_routes import EXERCISES, audit_console
from tests.support import JSON_HEADERS, PASSWORD, Console
from weightroom.domain.audit import REDACTED

LOADCOACH_TOKEN = "planted sweep token must never appear"  # noqa: S105 — a planted test secret


@pytest.fixture
def console(tmp_path: Path) -> Console:
    return audit_console(
        tmp_path,
        loadcoach_token=LOADCOACH_TOKEN,
        server_toml=(
            "rate_limit_per_minute = 100000\nrate_limit_burst = 100000\n"
            "failed_login_per_minute = 100000\n"
        ),
    )


def _every_audit_row(console: Console) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cursor: str | None = None
    while True:
        params = {"limit": "200"}
        if cursor:
            params["cursor"] = cursor
        page = console.client.get("/api/v1/audit", params=params, headers=JSON_HEADERS).json()
        rows.extend(page["items"])
        if not page.get("has_more") or not page.get("next_cursor"):
            return rows
        cursor = str(page["next_cursor"])


def test_no_audit_row_and_no_log_line_carries_a_secret_after_every_exercise(
    console: Console, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        for (method, path), exercise in sorted(EXERCISES.items()):
            if console.client.get("/api/v1/health").status_code == 401:
                console.login()  # a logout exercise ended the session; the next needs one
            response = exercise(console)
            assert response.status_code < 500, (method, path, response.text)
    rows = _every_audit_row(console)
    assert len(rows) >= len(EXERCISES), "every exercise writes at least its own row"
    trail = json.dumps(rows)
    for secret in (PASSWORD, LOADCOACH_TOKEN):
        assert secret not in trail, f"an audit row carries {secret!r}"
        assert secret not in caplog.text, f"a log line carries {secret!r}"
    # The routes never write a secret in the first place; redaction by key name at any depth is
    # the second line (domain/audit.redact_params, tests/unit/test_audit_domain.py), and no row
    # here needed it.
    assert REDACTED not in trail or all(REDACTED not in str(row.get("target")) for row in rows)
