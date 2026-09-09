"""weightroom.web.hosts — the Host-header allowlist both listeners share (ADR-0026 §1)."""

from __future__ import annotations

from mirrorwall import loopback_allowlist

from weightroom.config import LOOPBACK_HOSTS, Settings

__all__ = ["resolve_allowed_hosts"]


def resolve_allowed_hosts(settings: Settings) -> frozenset[str]:
    """The ``Host`` values accepted for this bind.

    Loopback: MirrorWall's loopback set. Anything else: ``server.allowed_hosts`` plus the bound
    address itself — and the loopback names too, because the console is also reached on the
    machine that runs it.
    """
    host = settings.server.host.lower()
    if host in LOOPBACK_HOSTS:
        return loopback_allowlist(host)
    return (
        frozenset(name.lower() for name in settings.server.allowed_hosts)
        | {host}
        | loopback_allowlist("127.0.0.1")
    )
