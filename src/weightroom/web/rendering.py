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
from weightroom.services.health import APP_STATUS_DOT
from weightroom.services.tls import trust_steps

if TYPE_CHECKING:
    from jinja2 import Environment

    from weightroom.config import Settings
    from weightroom.services.tls import HostIdentity, TlsStatus

__all__ = [
    "CONSOLE_PAGES",
    "CONSOLE_SIDE_NAV",
    "NAV_ITEMS",
    "PILL_TONES",
    "app_side_nav",
    "app_side_nav_stubs",
    "pill_status",
    "pill_tone",
    "render",
    "templates",
    "trust_context",
]

_TEMPLATES_DIR = Path(__file__).parent / "templates"

NAV_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "shell", "href": "/", "label": "Overview"},
    {"key": "apps", "href": "/apps", "label": "Applications"},
    {"key": "ollama", "href": "/ollama", "label": "Ollama"},
    {"key": "logs", "href": "/logs", "label": "Logs"},
    {"key": "audit", "href": "/audit", "label": "Audit"},
    {"key": "trust", "href": "/trust", "label": "Trust"},
)

CONSOLE_PAGES: tuple[dict[str, str], ...] = (
    {"label": "Chat", "phase": "W6"},
    {"label": "Docs", "phase": "W5"},
    {"label": "Database", "phase": "W7"},
    {"label": "Jobs", "phase": "W9"},
)
"""The console's own top-bar pages (design brief §4): named now, built in a later row."""

_APP_PAGES: dict[str, tuple[str, ...]] = {
    "freeweight": (
        "Overview",
        "Models",
        "Runs",
        "Results",
        "Evidence",
        "Goals",
        "Adapters",
        "Settings",
        "Provider",
        "Tokens",
        "Logs",
        "Database",
    ),
    "loadcoach": (
        "Overview",
        "Models",
        "Routing",
        "Queue",
        "Evidence",
        "Adapters",
        "Reliability",
        "Settings",
        "Providers",
        "Tokens",
        "Logs",
        "Database",
    ),
    "ideapress": (
        "Overview",
        "Projects",
        "Units",
        "Workflows",
        "Backends",
        "Settings",
        "Logs",
        "Database",
    ),
    "promptcadence": (
        "Overview",
        "Trajectories",
        "Approvals",
        "Tiers",
        "Tools",
        "Ledger",
        "Egress",
        "Settings",
        "Tokens",
        "Logs",
        "Database",
    ),
}
"""Spec §7.3's menu, per application. Only ``Overview`` is built before W4–W9 land the rest."""

_PAGE_PHASE: dict[str, str] = {
    "Settings": "W4",
    "Providers": "W4",
    "Provider": "W4",
    "Tokens": "W4",
    "Database": "W7",
}
"""Where a still-unbuilt page's kickoff already names a row; everything else is not yet
scheduled in ``roadmap/weightroom-work.md`` (a documentation gap this row notes rather than
invents an answer to — the handoff records it)."""


def app_side_nav(app_name: str) -> tuple[dict[str, Any], ...]:
    """The one section :func:`~mirrorwall.side_nav` renders for an application: ``Overview``.

    The macro's ``link`` shape has no inert state, so a page this build has not shipped yet is
    never handed to it as a dead ``href=""`` link — :func:`app_side_nav_stubs` renders those
    separately, in WeightRoomGym's own markup (design brief §5: one consumer stays here).
    """
    return (
        {
            "title": app_name,
            "links": [{"label": "Overview", "href": f"/apps/{app_name}", "selected": True}],
        },
    )


def app_side_nav_stubs(app_name: str) -> tuple[dict[str, str], ...]:
    """Every page spec §7.3 names for ``app_name`` that this build has not shipped yet.

    Each carries the row that will build it where the roadmap already says so, and "not yet
    scheduled" where it does not — a documentation gap this row notes rather than invents an
    answer to (the handoff records it).
    """
    stubs = []
    for label in _APP_PAGES.get(app_name, ()):
        if label == "Overview":
            continue
        phase = _PAGE_PHASE.get(label)
        title = f"coming in phase {phase}" if phase else "not yet scheduled"
        stubs.append({"label": label, "title": title})
    return tuple(stubs)


CONSOLE_SIDE_NAV: tuple[dict[str, Any], ...] = (
    {
        "title": "Console",
        "links": [{"label": item["label"], "href": item["href"]} for item in NAV_ITEMS],
    },
)
"""The left menu a console page (not an application's own tab) shows."""


PILL_TONES: dict[str, str] = {
    "ok": "success",
    "starting": "warning",
    "stopping": "warning",
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


def pill_status(pill: str) -> str:
    """The status-dot word (design brief §3) for an :class:`AppView` pill; the same map health
    already reads a component's status from — one vocabulary, read two ways.
    """
    return APP_STATUS_DOT.get(pill, "unknown")


@lru_cache(maxsize=1)
def templates() -> Environment:
    """Return the process-wide Jinja environment, building it on first use."""
    environment = create_template_environment(
        app_template_dirs=(_TEMPLATES_DIR,),
        globals_={
            "product_name": "WeightRoomGym",
            "product_version": __version__,
            "nav_items": NAV_ITEMS,
            "console_pages": CONSOLE_PAGES,
            "theme_storage_key": "weightroom-theme",
            # ADR-0128: every fragment swap and SSE region in the shell is htmx, vendored by
            # MirrorWall 0.3 and opt-in per page — WeightRoomGym opts every page in at once
            # (design brief §4), since the log pane and the guard dialog both want it.
            "mirrorwall": {"htmx": True},
        },
    )
    environment.filters["pill_tone"] = pill_tone
    environment.filters["pill_status"] = pill_status
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
