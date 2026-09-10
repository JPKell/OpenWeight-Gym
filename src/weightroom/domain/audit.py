"""weightroom.domain.audit — the closed vocabulary and the redaction rule (data model §2).

``audit_log.action`` is one of :data:`ACTIONS` and nothing else; a test asserts the set and
every writer goes through :func:`weightroom.services.audit.record`, which refuses a name outside
it. ``params`` is redacted here before a row exists: any key shaped like a secret, and any URL
credential, is replaced.
"""

from __future__ import annotations

import re
from typing import Any, Final

__all__ = ["ACTIONS", "ACTORS", "OUTCOMES", "REDACTED", "redact_params"]

ACTIONS: Final[frozenset[str]] = frozenset(
    {
        # Phase 1
        "login",
        "logout",
        "reauth",
        "operator.create",
        "operator.password",
        "tls.rotate",
        "setup.run",
        # Named by data-model.md §2 for later phases; a row's writer arrives with its phase.
        "unit.sync",
        "unit.start",
        "unit.stop",
        "unit.restart",
        "ollama.restart",
        "settings.write",
        # W4. A validation changes nothing, but it launches the application's own loader over
        # operator-supplied text, and the outcome is what the operator wants to find later; the
        # row says `pending`, which is the outcome vocabulary's word for "no state moved".
        "settings.validate",
        # W4. An API token is a credential; its creation and its revocation are both trail
        # entries, and neither row ever carries the secret (`params` is redacted regardless).
        "token.create",
        "token.revoke",
        "db.guarded_write",
        "db.curated",
        "catalog.pull",
        "prompt.override",
        "job.run",
        "alert.ack",
    }
)
"""The closed action vocabulary."""

ACTORS: Final[frozenset[str]] = frozenset({"operator", "job", "alerts", "cli"})
OUTCOMES: Final[frozenset[str]] = frozenset({"pending", "ok", "failed", "refused"})

REDACTED: Final = "********"
_SECRET_KEY: Final = re.compile(r"(?i)(token|key|secret|password|authorization|cookie)")
_URL_CREDENTIAL: Final = re.compile(r"(?i)([a-z][a-z0-9+.-]*://)([^/@\s]+)@")


def redact_params(value: Any) -> Any:  # noqa: ANN401 — JSON-shaped input, JSON-shaped output
    """Return ``value`` with secret-shaped keys and URL credentials replaced.

    Args:
        value: Any JSON-shaped structure.

    Returns:
        A copy: a mapping key matching ``token|key|secret|password|authorization|cookie`` has its
        value replaced whole; a string carrying ``scheme://user:pass@`` keeps the scheme and the
        host and loses the credential.
    """
    if isinstance(value, dict):
        return {
            str(key): (REDACTED if _SECRET_KEY.search(str(key)) else redact_params(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_params(item) for item in value]
    if isinstance(value, str):
        return _URL_CREDENTIAL.sub(rf"\1{REDACTED}@", value)
    return value
