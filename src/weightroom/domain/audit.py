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
        # W6. Starting, sending to, attaching to and deleting a conversation. The row names the
        # conversation and counts; message text and attachment contents are never in it.
        "chat.create",
        "chat.message",
        "chat.attachment",
        "chat.delete",
        # W6. Granting or denying a PromptCadence approval from a thread: the one chat action that
        # authorises spend or egress, so its row names the trajectory and the request it resolved.
        "chat.approve",
        "chat.deny",
        "db.guarded_write",
        # W7. The console's one SELECT: nothing moves, but what was read, and by whom, is the
        # trail's. A refused statement is a row too.
        "db.query",
        # W7. A guarded write's rolled-back dry run: the count the operator is about to confirm.
        "db.dry_run",
        "db.curated",
        "catalog.pull",
        # W8. Every other catalog action: enabling or disabling a model on one application, a
        # GGUF drop-in, and a catalog delete (the preview and the confirmed removal both — a
        # preview changes nothing but is the row that shows what was about to happen).
        "catalog.enabled",
        "catalog.dropin",
        "catalog.delete",
        "prompt.override",
        # W9. Removing an override, so the application renders its shipped record again.
        "prompt.delete",
        "job.run",
        # W9. Enqueueing a job is a person's action (the run itself is `job.run`, actor `job`);
        # so are cancelling one and changing a schedule's cron, parameters or enabled flag.
        "job.enqueue",
        "job.cancel",
        "job.schedule",
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
