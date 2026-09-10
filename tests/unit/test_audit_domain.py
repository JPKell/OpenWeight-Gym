"""weightroom.domain.audit: the closed vocabulary and the redaction rule."""

from __future__ import annotations

import re
from pathlib import Path

from weightroom.domain.audit import ACTIONS, ACTORS, OUTCOMES, REDACTED, redact_params

DATA_MODEL = Path(__file__).resolve().parents[2] / "docs" / "apps" / "weightroom" / "data-model.md"


def test_the_vocabulary_is_closed_and_covers_what_the_data_model_names() -> None:
    text = DATA_MODEL.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| `action` |"))
    named = set(re.findall(r"`([a-z_]+(?:\.[a-z_]+)?)`", row)) - {"action"}
    assert named <= ACTIONS, sorted(named - ACTIONS)
    assert {
        "login",
        "logout",
        "reauth",
        "tls.rotate",
        "operator.create",
        "operator.password",
    } <= ACTIONS
    assert ACTORS == {"operator", "job", "alerts", "cli"}
    assert OUTCOMES == {"pending", "ok", "failed", "refused"}


def test_redaction_replaces_secret_keys_and_url_credentials_at_any_depth() -> None:
    params = {
        "username": "jordan",
        "password": "hunter22",
        "nested": {"api_key_file": "/x", "Authorization": "Bearer abc", "ok": 1},
        "list": [{"token": "t"}, "postgresql+psycopg://user:pw@host/db"],
        "url": "sqlite:///plain",
    }
    redacted = redact_params(params)
    assert redacted["username"] == "jordan"
    assert redacted["password"] == REDACTED
    assert redacted["nested"] == {"api_key_file": REDACTED, "Authorization": REDACTED, "ok": 1}
    assert redacted["list"] == [{"token": REDACTED}, f"postgresql+psycopg://{REDACTED}@host/db"]
    assert redacted["url"] == "sqlite:///plain"
    assert params["password"] == "hunter22"  # the input is untouched  # noqa: S105
