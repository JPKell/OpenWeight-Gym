"""weightroom.web.rendering — the one Jinja environment every page renders through.

MirrorWall's environment: the shell, the macros, the tokens and the filters come from the
package; this module supplies what is WeightRoomGym's — the product name, the navigation and the
template directory. Built once and cached.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mirrorwall import create_template_environment

from weightroom.__about__ import __version__
from weightroom.services.tls import trust_steps

if TYPE_CHECKING:
    from jinja2 import Environment

    from weightroom.config import Settings
    from weightroom.services.tls import HostIdentity, TlsStatus

__all__ = ["NAV_ITEMS", "PILL_TONES", "pill_tone", "render", "templates", "trust_context"]

_TEMPLATES_DIR = Path(__file__).parent / "templates"

NAV_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "shell", "href": "/", "label": "Overview"},
    {"key": "apps", "href": "/apps", "label": "Applications"},
    {"key": "ollama", "href": "/ollama", "label": "Ollama"},
    {"key": "logs", "href": "/logs", "label": "Logs"},
    {"key": "audit", "href": "/audit", "label": "Audit"},
    {"key": "trust", "href": "/trust", "label": "Trust"},
)


PILL_TONES: dict[str, str] = {
    "ok": "success",
    "starting": "warning",
    "stopped": "neutral",
    "failed": "danger",
    "version mismatch": "danger",
    "not installed": "neutral",
    "unsupported": "neutral",
}
"""How :attr:`~weightroom.services.apps.AppView.pill` colours.

*stopped* and *not installed* are **neutral**, not warnings: an operator who has deliberately
stopped an application should not be shown a page of amber. Only a state nobody chose — a failed
unit, a version outside the range — is coloured as a problem.
"""


def pill_tone(pill: str) -> str:
    """The badge tone for a status pill; unknown words are neutral rather than alarming."""
    return PILL_TONES.get(pill, "neutral")


@lru_cache(maxsize=1)
def templates() -> Environment:
    """Return the process-wide Jinja environment, building it on first use."""
    environment = create_template_environment(
        app_template_dirs=(_TEMPLATES_DIR,),
        globals_={
            "product_name": "WeightRoomGym",
            "product_version": __version__,
            "nav_items": NAV_ITEMS,
            "theme_storage_key": "weightroom-theme",
        },
    )
    environment.filters["pill_tone"] = pill_tone
    return environment


def render(template_name: str, /, **context: Any) -> str:
    """Render ``template_name`` with ``context``."""
    return templates().get_template(template_name).render(**context)


def trust_context(settings: Settings, *, tls: TlsStatus, identity: HostIdentity) -> dict[str, Any]:
    """What both trust pages and ``wr-gym trust`` show: fingerprint, URLs, steps."""
    hosts = [f"{identity.hostname}.local", *identity.addresses]
    return {
        "fingerprint": tls.ca_fingerprint_sha256,
        "ca_subject": tls.ca_subject,
        "ca_not_after": tls.ca_not_after.date().isoformat(),
        "ca_file": str(tls.paths.ca_crt),
        "console_urls": [f"https://{host}:{settings.server.port}" for host in hosts],
        "trust_urls": [f"http://{host}:{settings.server.trust_port}/trust" for host in hosts],
        "root_urls": [f"http://{host}:{settings.server.trust_port}/root.crt" for host in hosts],
        "steps": trust_steps(identity.hostname),
    }
