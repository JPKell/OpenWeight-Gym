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
from weightroom.config import APP_LABELS
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
    {"key": "doctor", "href": "/doctor", "label": "Doctor"},
    {"key": "settings", "href": "/settings", "label": "Settings"},
    {"key": "trust", "href": "/trust", "label": "Trust"},
)

CONSOLE_PAGES: tuple[dict[str, str], ...] = (
    {"label": "Chat", "phase": "W6"},
    {"label": "Docs", "href": "/docs"},
    {"label": "Database", "phase": "W7"},
    {"label": "Jobs", "phase": "W9"},
)
"""The console's own top-bar pages (design brief §4): a built one carries ``href``, an unbuilt
one carries ``phase`` and renders inert until its row lands."""

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
    "Database": "W7",
}
"""Where a still-unbuilt page's kickoff already names a row; everything else is not yet
scheduled in ``roadmap/weightroom-work.md`` (a documentation gap W3 noted rather than invented
an answer to — the handoffs record it)."""

_PAGE_ELSEWHERE: dict[str, str] = {
    "Provider": "edited on the application's own provider page (ADR-0117)",
    "Providers": "edited on the application's own provider page (ADR-0117)",
}
"""Pages spec §7.3 names that are **not** WeightRoomGym's to build.

A provider registration is a keyed table with its own admin form inside the application
(ADR-0117), reachable from the application itself; the console's settings page edits every other
key of the same file and says so rather than growing a fifth copy of that form (W4)."""

_PAGE_HREF: dict[str, str] = {
    "Overview": "/apps/{app}",
    "Settings": "/apps/{app}/settings",
    "Tokens": "/apps/{app}/tokens",
}
"""Where a built page lives; anything absent is still a stub."""

_NO_TOKENS: frozenset[str] = frozenset({"ideapress"})
"""IdeaPress has no token surface at all — no ``token`` CLI verb and no token table (W4)."""


def _built_pages(app_name: str) -> tuple[str, ...]:
    """Every spec §7.3 page for ``app_name`` this build actually serves."""
    return tuple(
        label
        for label in _APP_PAGES.get(app_name, ())
        if label in _PAGE_HREF and not (label == "Tokens" and app_name in _NO_TOKENS)
    )


def app_label(name: str) -> str:
    """The display name of an application.

    Args:
        name: The lowercase identifier a route, unit or CLI uses (``loadcoach``).

    Returns:
        Its display name (``LoadCoach``), or ``name`` unchanged when it is not one the suite knows,
        so an unexpected name still renders as itself rather than as nothing.
    """
    return APP_LABELS.get(name, name)


def app_side_nav(app_name: str, *, selected: str = "Overview") -> tuple[dict[str, Any], ...]:
    """The section :func:`~mirrorwall.side_nav` renders for an application: its built pages.

    The macro's ``link`` shape has no inert state, so a page this build has not shipped yet is
    never handed to it as a dead ``href=""`` link — :func:`app_side_nav_stubs` renders those
    separately, in WeightRoomGym's own markup (design brief §5: one consumer stays here).
    """
    return (
        {
            "title": app_label(app_name),
            "links": [
                {
                    "label": label,
                    "href": _PAGE_HREF[label].format(app=app_name),
                    "selected": label == selected,
                }
                for label in _built_pages(app_name)
            ],
        },
    )


def app_side_nav_stubs(app_name: str) -> tuple[dict[str, str], ...]:
    """Every page spec §7.3 names for ``app_name`` that this build does not serve.

    Each carries the row that will build it where the roadmap already says so, "not yet
    scheduled" where it does not — a documentation gap noted rather than invented an answer to —
    and, for a page that is deliberately somebody else's, where it actually lives.
    """
    built = _built_pages(app_name)
    stubs = []
    for label in _APP_PAGES.get(app_name, ()):
        if label in built:
            continue
        elsewhere = _PAGE_ELSEWHERE.get(label)
        if elsewhere is not None:
            title = elsewhere
        elif label == "Tokens":
            title = f"{app_label(app_name)} has no API tokens"
        else:
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
            # The name an operator reads. The distribution, CLI and ADRs keep WeightRoomGym/wr-gym;
            # the header says WeightRoom and links home (operator decision, 2026-09-10).
            "product_name": "WeightRoom",
            "product_href": "/",
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
    environment.filters["app_label"] = app_label
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
