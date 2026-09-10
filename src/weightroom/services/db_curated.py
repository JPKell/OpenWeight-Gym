"""weightroom.services.db_curated — each application's own database operations, offered first.

ADR-0123 rule 5 and ADR-0124: maintenance an application already offers is invoked through that
application — its ``db status|backup|upgrade|restore``, and FreeWeight's ``db vacuum`` — so its own
preview, confirmation and integrity checks apply, and a raw write is what remains when nothing
fits. The console runs the verb the way an operator at the terminal would, under the subprocess
discipline of ``services/processes.py``, and shows what the application printed.

**What each table is offered is data**, below. FreeWeight's deletion of stored results is its own
HTTP API (``POST /api/v1/database/delete-preview``, ``DELETE /api/v1/database/results``), called
here with FreeWeight's preview token (ADR-0134 rule 2); the ``freeweight db delete --model`` that
ADR-0123 and ADR-0124 cite was never built, and is not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Final

import httpx
from baseaicore import SuiteError

from weightroom.domain.guard import GuardAppRunning
from weightroom.services.apps import AppNotInstalled, bearer_token
from weightroom.services.db_guard import observe
from weightroom.services.processes import child_environment, executable_for, run_command

if TYPE_CHECKING:
    from collections.abc import Mapping

    from weightroom.config import Settings
    from weightroom.services.db_guard import Connector
    from weightroom.services.processes import Runner, SystemdController

__all__ = [
    "CURATED_TIMEOUT_SECONDS",
    "RESULTS_DELETION",
    "TABLE_OPERATIONS",
    "VERBS",
    "CuratedRefused",
    "CuratedResult",
    "TableOperation",
    "delete_results",
    "run_curated",
    "verbs_for",
]

CURATED_TIMEOUT_SECONDS: Final = 600.0
"""A backup or a migration of a large database takes minutes; the output cap still applies."""

VERBS: Final[Mapping[str, Mapping[str, tuple[str, ...]]]] = {
    "freeweight": {
        "status": ("db", "status", "--json"),
        "backup": ("db", "backup", "--json"),
        "vacuum": ("db", "vacuum", "--json"),
        "upgrade": ("db", "upgrade", "--json"),
        "restore": ("db", "restore", "--yes"),
    },
    "loadcoach": {
        "status": ("db", "status", "--json"),
        "backup": ("db", "backup", "--json"),
        "upgrade": ("db", "upgrade", "--json"),
        "restore": ("db", "restore", "--yes"),
    },
    "ideapress": {
        "status": ("db", "status", "--json"),
        "backup": ("db", "backup"),
        "upgrade": ("db", "upgrade"),
        "restore": ("db", "restore", "--yes"),
    },
    "promptcadence": {
        "status": ("db", "status", "--json"),
        "backup": ("db", "backup"),
        "upgrade": ("db", "upgrade", "--json"),
        "restore": ("db", "restore", "--yes"),
    },
}
"""Each application's own ``db`` verbs with the flags its CLI accepts, read off each ``--help`` at
row W7 (FreeWeight 1.2, LoadCoach 1.5, IdeaPress 1.5, PromptCadence 1.3)."""

RESULTS_DELETION: Final[Mapping[str, tuple[str, ...]]] = {
    "freeweight": ("model", "run", "suite", "before", "all"),
}
"""The applications whose API deletes stored results, and the scopes it accepts (FreeWeight's
``DeletionScope``). Everything else about a deletion — what it removes, the backup at 1 000 rows,
the token — is the application's."""


@dataclass(frozen=True, slots=True)
class TableOperation:
    """A curated operation covering one table, listed above that table's guard.

    Attributes:
        label: What it does.
        note: How, in the owning application's terms.
        href: Where the console does it, or ``None`` where the application does not offer it.
    """

    label: str
    note: str
    href: str | None = None


_FREEWEIGHT_DELETION = TableOperation(
    "Delete stored results",
    "FreeWeight's own deletion by model, run, suite or date: previewed, confirmed with its token, "
    "backed up first at 1 000 rows, and never a model or machine row (ADR-0134).",
    "/apps/freeweight/database#delete-results",
)
_LOADCOACH_RETENTION = TableOperation(
    "Content retention",
    "storage.content_retention_hours scrubs a finished job's prompt and response text, here and in "
    "its result event; storage.retain_content keeps it for ever.",
    "/apps/loadcoach/settings",
)
_PROMPTCADENCE_RETENTION = TableOperation(
    "Content retention",
    "storage.content_retention_hours scrubs a finished trajectory's transcript, plan text and tool "
    "arguments, keeping every hash, decision and event; storage.retain_content keeps it for ever.",
    "/apps/promptcadence/settings",
)

TABLE_OPERATIONS: Final[Mapping[str, Mapping[str, tuple[TableOperation, ...]]]] = {
    "freeweight": dict.fromkeys(
        ("samples", "run_tests", "runs", "metric_values"), (_FREEWEIGHT_DELETION,)
    ),
    "loadcoach": dict.fromkeys(("jobs", "job_events"), (_LOADCOACH_RETENTION,)),
    "ideapress": {},
    "promptcadence": dict.fromkeys(
        ("trajectories", "turns", "plans", "plan_steps", "tool_call_records"),
        (_PROMPTCADENCE_RETENTION,),
    ),
}
"""The tables each application's own sweeps and verbs cover (their retention modules at W7)."""


class CuratedRefused(SuiteError):
    """A curated operation the application does not offer, or one asked for wrongly."""

    code: ClassVar[str] = "VALIDATION_ERROR"


@dataclass(frozen=True, slots=True)
class CuratedResult:
    """What the application's own operation did.

    Attributes:
        app: The application.
        verb: ``status``, ``backup``, ``vacuum``, ``upgrade``, ``restore``, ``delete-preview`` or
            ``delete-results``.
        argv: What ran — the command line, or the HTTP method and URL.
        ok: Whether it exited 0, or answered 2xx.
        output: Its JSON when it printed JSON, its text otherwise, ``None`` when it printed nothing.
        error: Its own failure text when it did not succeed.
    """

    app: str
    verb: str
    argv: tuple[str, ...]
    ok: bool
    output: Any
    error: str | None

    def as_json(self) -> dict[str, Any]:
        """The API's shape."""
        return {
            "app": self.app,
            "verb": self.verb,
            "argv": list(self.argv),
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
        }


def verbs_for(app: str) -> tuple[str, ...]:
    """The ``db`` verbs ``app`` offers, in the order the page lists them."""
    return tuple(VERBS.get(app, {}))


def run_curated(
    settings: Settings,
    controller: SystemdController,
    app: str,
    verb: str,
    *,
    source: str = "",
    name_typed: str = "",
    runner: Runner = run_command,
    connect: Connector | None = None,
) -> CuratedResult:
    """Run one of the application's own ``db`` verbs.

    Args:
        settings: The validated settings, for the executable and the base URL.
        controller: The systemd boundary, for ``restore``'s stopped check.
        app: One of the four.
        verb: One of :func:`verbs_for`.
        source: ``restore``'s backup file.
        name_typed: ``restore``'s typed confirmation, which must be the application's name.
        runner: The process-launch boundary, injected.
        connect: The port probe, injected in tests.

    Returns:
        The :class:`CuratedResult` — including a non-zero exit, which is the application's answer,
        not an exception.

    Raises:
        CuratedRefused: The application has no such verb; or, for ``restore``, no source or a typed
            name that is not the application's.
        GuardAppRunning: ``restore`` while the unit runs or the port answers — a restore replaces
            the file under the application (api.md §3).
        AppNotInstalled: No executable.
    """
    tail = VERBS.get(app, {}).get(verb)
    if tail is None:
        raise CuratedRefused(
            f"{app} offers no `db {verb}`; its own verbs are {', '.join(verbs_for(app))}.",
            details={"app": app, "verb": verb},
        )
    arguments = list(tail)
    if verb == "restore":
        if name_typed.strip() != app:
            raise CuratedRefused(
                f"Type {app} to restore its database: a restore replaces the whole file.",
                details={"app": app, "name_typed": name_typed},
            )
        if not source.strip():
            raise CuratedRefused(
                "A restore needs the backup file to restore from.", details={"app": app}
            )
        observation = observe(settings, controller, app, connect=connect)
        if not observation.stopped:
            raise GuardAppRunning(
                f"{app} is not stopped ({observation.evidence}); its database is restored only "
                "with it stopped.",
                details={"unit_state": observation.unit_state, "address": observation.address},
            )
        arguments.append(source.strip())
    executable = executable_for(settings, app)
    if executable is None:
        raise AppNotInstalled(
            f"{app} is not installed, so it cannot run its own db {verb}.", details={"app": app}
        )
    argv = (executable, *arguments)
    result = runner(list(argv), child_environment(), CURATED_TIMEOUT_SECONDS)
    output: Any = None
    if result.stdout.strip():
        try:
            output = json.loads(result.stdout)
        except ValueError:
            output = result.stdout
    return CuratedResult(
        app=app,
        verb=verb,
        argv=argv,
        ok=result.ok,
        output=output,
        error=None if result.ok else result.failure_text,
    )


def delete_results(
    settings: Settings,
    client: httpx.Client,
    app: str,
    *,
    scope: str,
    selector: str = "",
    token: str = "",
    typed: str = "",
) -> CuratedResult:
    """Preview, or perform, the application's own deletion of stored results over its API.

    Without ``token`` this asks for the preview — what would go, what is kept, and the token.
    With one it sends the deletion, which the application refuses unless the token matches a fresh
    preview of the same selection (ADR-0134 rule 2). The caller re-authenticates first.

    Args:
        settings: The validated settings, for the base URL and the token file.
        client: The console's HTTP client.
        app: The application; only those in :data:`RESULTS_DELETION`.
        scope: One of the application's scopes.
        selector: The scope's argument; empty for ``all``.
        token: The preview's token; empty to preview.
        typed: The typed confirmation — the selector, or ``all`` for scope ``all``.

    Returns:
        A :class:`CuratedResult` with verb ``delete-preview`` or ``delete-results``, ``argv`` the
        method and URL, and the application's JSON. A refusal by the application, or no answer, is
        ``ok`` false in its own words — not an exception.

    Raises:
        CuratedRefused: The application deletes no results, the scope is not one it accepts, or a
            deletion's typed confirmation is not the selector.
    """
    scopes = RESULTS_DELETION.get(app)
    if scopes is None:
        raise CuratedRefused(
            f"{app} offers no deletion of stored results over its API.", details={"app": app}
        )
    if scope not in scopes:
        raise CuratedRefused(
            f"{app} deletes results by {', '.join(scopes)}, not {scope!r}.",
            details={"app": app, "scope": scope},
        )
    chosen = selector.strip()
    body: dict[str, Any] = {"scope": scope, "selector": chosen or None}
    if token:
        expected = chosen or "all"
        if typed.strip() != expected:
            raise CuratedRefused(
                f"Type {expected} to delete these results: the deletion cannot be undone except "
                "from a backup.",
                details={"app": app, "typed": typed},
            )
        body["token"] = token
        verb, method, path = "delete-results", "DELETE", "/api/v1/database/results"
    else:
        verb, method, path = "delete-preview", "POST", "/api/v1/database/delete-preview"
    url = f"{getattr(settings.apps, app).base_url.rstrip('/')}{path}"
    headers = {}
    bearer = bearer_token(settings, app)
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    try:
        response = client.request(
            method, url, json=body, headers=headers, timeout=CURATED_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return CuratedResult(
            app, verb, (method, url), ok=False, output=None, error=f"{app} did not answer: {exc}"
        )
    try:
        answer: Any = response.json()
    except ValueError:
        answer = None
    if response.is_success:
        return CuratedResult(app, verb, (method, url), ok=True, output=answer, error=None)
    error = answer.get("error") if isinstance(answer, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    return CuratedResult(
        app,
        verb,
        (method, url),
        ok=False,
        output=None,
        error=f"{app} refused: {message}" if message else f"{app} answered {response.status_code}.",
    )
