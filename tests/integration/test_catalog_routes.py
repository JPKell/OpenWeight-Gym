"""The catalog drop-in's refusal on the wire (api.md §5): a 409 and an audited refusal, not a 500.

Found by row W9's demonstration: no application on the reference machine configures a llama.cpp
``model_directory``, and the refusal — correct, and audited — was answered as an internal error
because its code had no status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import respx
from sqlalchemy import select

from tests.support import build_console
from weightroom.infrastructure.db.models import AuditLog

if TYPE_CHECKING:
    from pathlib import Path


def test_a_dropin_with_nowhere_to_go_is_a_409_and_an_audited_refusal(tmp_path: Path) -> None:
    console = build_console(tmp_path)
    console.login()
    source = tmp_path / "small.gguf"
    source.write_bytes(b"GGUF" + b"\x00" * 2000)
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        router.get("http://127.0.0.1:8765/api/v1/provider").mock(
            return_value=httpx.Response(200, json={"provider": {"kind": "ollama"}})
        )
        router.get("http://127.0.0.1:8766/api/v1/providers").mock(
            return_value=httpx.Response(
                200, json={"registrations": [{"name": "ollama", "kind": "ollama"}]}
            )
        )
        refused = console.client.post(
            "/api/v1/catalog/dropin",
            data={"path": str(source), "csrf_token": console.csrf_token()},
            headers={"Sec-Fetch-Site": "same-origin"},
        )

    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "CATALOG_DROPIN_REFUSED"
    with console.database.read() as session:
        rows = session.execute(select(AuditLog).where(AuditLog.action == "catalog.dropin"))
        assert [row.outcome for row in rows.scalars()] == ["refused"]
