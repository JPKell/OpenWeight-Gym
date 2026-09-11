"""weightroom.services.ideapress_pages — the data behind IdeaPress's tab (row WP5).

Each page has two readers: one over IdeaPress's own ``/api/v1`` (through
:mod:`~weightroom.services.app_api`) for while it answers, and one over its database
(``data-model.md`` §4) for while it does not, shaping the rows into the keys the API document uses
so a page renders one shape either way. Which one runs is :mod:`~weightroom.services.app_pages`'
decision, never this module's. Workflows, backends and the runtime settings exist only in the
running process — the stage table is code, reachability is a live probe — so those read the API
alone. What a row says reaches the page through the templates, escaped.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Final
from urllib.parse import quote

from baseaicore import SuiteError

from weightroom.services.app_api import call
from weightroom.services.app_pages import rows_where

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings
    from weightroom.services.db_reader import AppDatabase

__all__ = [
    "APP",
    "ProjectNotRecorded",
    "backends_api",
    "project_api",
    "project_db",
    "projects_api",
    "projects_db",
    "segment",
    "settings_api",
    "workflow_api",
    "workflows_api",
]

APP: Final = "ideapress"
PAGE_ROWS: Final = 50
LIST_CAP: Final = 200
STAGE_HISTORY: Final = 50
"""IdeaPress's ``GET /projects/{id}`` lists its newest 50 stage runs; the stopped reader too."""


class ProjectNotRecorded(SuiteError):
    """IdeaPress's database holds no project with that id."""

    code: ClassVar[str] = "PROJECT_NOT_FOUND"


def segment(value: str) -> str:
    """``value`` quoted as one path segment, so an id can never add a segment or a query."""
    return quote(value, safe="")


def _loads(value: Any) -> Any:  # noqa: ANN401 — a stored JSON column, whatever it holds
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _document(body: Any) -> dict[str, Any]:  # noqa: ANN401 — the application's JSON body
    return dict(body) if isinstance(body, Mapping) else {}


def _items(body: Any, key: str = "items") -> list[dict[str, Any]]:  # noqa: ANN401
    items = body.get(key) if isinstance(body, Mapping) else None
    return [dict(one) for one in items or [] if isinstance(one, Mapping)]


# --- Projects -------------------------------------------------------------------------------------


def projects_api(
    client: httpx.Client,
    settings: Settings,
    *,
    status: str | None,
    content_type: str | None,
    archived: bool,
    cursor: str | None,
) -> dict[str, Any]:
    """``GET /projects``: one page, newest activity first, with IdeaPress's own cursor.

    Raises:
        AppRefused: IdeaPress refused (a cursor it did not issue is its ``VALIDATION_ERROR``).
        AppUnreachable: It did not answer.
    """
    body = call(
        client, settings, APP, "GET", "projects",
        params={
            "status": status, "content_type": content_type, "cursor": cursor, "limit": PAGE_ROWS,
            "include_archived": "true" if archived else None,
        },
    )  # fmt: skip
    page = body.get("page") if isinstance(body, Mapping) else None
    return {
        "items": _items(body),
        "next_cursor": page.get("next_cursor") if isinstance(page, Mapping) else None,
        "next_page": None,
    }


def _project_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """A ``projects`` row under the API document's names (its columns differ: ``brief_text``)."""
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "slug": row.get("slug"),
        "content_type": row.get("content_type"),
        "content_type_version": row.get("content_type_version"),
        "workflow_id": row.get("workflow_id"),
        "workflow_version": row.get("workflow_version"),
        "status": row.get("status"),
        "brief": row.get("brief_text"),
        "author_material": _loads(row.get("author_material_json")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "completed_at": row.get("completed_at"),
        "archived_at": row.get("archived_at"),
    }


def projects_db(
    handle: AppDatabase,
    *,
    status: str | None,
    content_type: str | None,
    archived: bool,
    page: int,
) -> dict[str, Any]:
    """The ``projects`` table, newest activity first, one page by number.

    Raises:
        TableUnknown: The database has no ``projects`` table.
        ReadFailed: The database refused or ran past the timeout.
    """
    page = max(1, page)
    rows = rows_where(
        handle, "projects", equals={"status": status, "content_type": content_type},
        order_by="updated_at", limit=PAGE_ROWS + 1, offset=(page - 1) * PAGE_ROWS,
    )  # fmt: skip
    items = [_project_row(row) for row in rows[:PAGE_ROWS]]
    if not archived and not status:
        # ponytail: archived rows are dropped after the page is read, so a stopped page can come
        # back short; filter in SQL once the reader grows a not-equal condition.
        items = [one for one in items if one["status"] != "archived"]
    return {
        "items": items,
        "next_cursor": None,
        "next_page": page + 1 if len(rows) > PAGE_ROWS else None,
    }


def project_api(client: httpx.Client, settings: Settings, project_id: str) -> dict[str, Any]:
    """``GET /projects/{id}``: the project, its plan summary, units and stage history.

    Raises:
        AppRefused: ``PROJECT_NOT_FOUND``, or another refusal.
        AppUnreachable: It did not answer.
    """
    body = call(client, settings, APP, "GET", f"projects/{segment(project_id)}")
    return {"project": _document(body)}


def _unit_row(row: Mapping[str, Any], version: Mapping[str, Any] | None) -> dict[str, Any]:
    return {
        "unit_key": row.get("unit_key"),
        "ordinal": row.get("ordinal"),
        "title": row.get("title"),
        "goal": row.get("goal_text"),
        "state": row.get("state"),
        "paused_reason": row.get("paused_reason"),
        "requirement_keys": _loads(row.get("requirement_keys_json")) or [],
        "version": version.get("version") if version else None,
        "word_count": version.get("word_count") if version else None,
        "content_hash": version.get("content_hash") if version else None,
        # Computed by IdeaPress from coverage and validation rows; the stopped page says `—`.
        "coverage": None,
        "last_validation": None,
    }


def _stage_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": row.get("id"),
        "stage": row.get("stage"),
        "state": row.get("state"),
        "units_total": row.get("units_total"),
        "units_completed": row.get("units_completed"),
        "units_paused": row.get("units_paused"),
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "error_code": row.get("error_code"),
        "error_text": row.get("error_text"),
        "options": _loads(row.get("options_json")) or {},
    }


def units_db(handle: AppDatabase, project_id: str) -> list[dict[str, Any]]:
    """A project's ``units`` rows in reading order, each with its current version's figures.

    Raises:
        TableUnknown: A table this reader expects is absent.
        ReadFailed: The database refused or ran past the timeout.
    """
    rows = rows_where(
        handle, "units", equals={"project_id": project_id}, order_by="ordinal", descending=False,
        limit=LIST_CAP,
    )  # fmt: skip
    units = []
    for row in rows:
        found = (
            rows_where(
                handle, "unit_versions", equals={"id": row.get("current_version_id")}, limit=1
            )
            if row.get("current_version_id")
            else []
        )
        units.append(_unit_row(row, found[0] if found else None))
    return units


def project_db(handle: AppDatabase, project_id: str) -> dict[str, Any]:
    """One project's row with its units, requirement counts and stage runs, as the API shapes it.

    Raises:
        ProjectNotRecorded: No such project in the database.
        TableUnknown: A table this reader expects is absent.
        ReadFailed: The database refused or ran past the timeout.
    """
    found = rows_where(handle, "projects", equals={"id": project_id}, limit=1)
    if not found:
        raise ProjectNotRecorded(
            f"IdeaPress's database holds no project {project_id!r}.",
            details={"project_id": project_id},
        )
    units = units_db(handle, project_id)
    requirements = rows_where(
        handle, "requirements", equals={"project_id": project_id}, limit=LIST_CAP
    )
    stages = rows_where(
        handle, "stage_runs", equals={"project_id": project_id}, order_by="started_at",
        limit=STAGE_HISTORY,
    )  # fmt: skip
    plan = (
        {
            "units": len(units),
            "requirements": len(requirements),
            "blocking": sum(1 for one in requirements if one.get("blocking")),
        }
        if units or requirements
        else None
    )
    project = {
        **_project_row(found[0]),
        "plan": plan,
        "units": units,
        "stages": [_stage_row(row) for row in stages],
        # Which run is in flight lives in the running process; a stopped one runs nothing.
        "running_task_id": None,
    }
    return {"project": project}


# --- Workflows, backends, settings ---------------------------------------------------------------


def workflows_api(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``GET /workflows``: every definition — stage order, gates, which stages use a model.

    Raises:
        AppRefused: IdeaPress refused.
        AppUnreachable: It did not answer.
    """
    return {"workflows": _items(call(client, settings, APP, "GET", "workflows"), "workflows")}


def workflow_api(client: httpx.Client, settings: Settings, workflow_id: str) -> dict[str, Any]:
    """``GET /workflows/{id}``: one definition.

    Raises:
        AppRefused: An unknown workflow is IdeaPress's ``STAGE_PRECONDITION_FAILED``.
        AppUnreachable: It did not answer.
    """
    return {
        "workflow": _document(
            call(client, settings, APP, "GET", f"workflows/{segment(workflow_id)}")
        )
    }


def backends_api(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``GET /backends``: each configured backend with mode, reachability, capabilities, egress.

    Raises:
        AppRefused: IdeaPress refused.
        AppUnreachable: It did not answer.
    """
    return {
        "backends": _items(
            call(client, settings, APP, "GET", "backends", timeout_seconds=30.0), "backends"
        )
    }


def settings_api(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``GET /settings``: the effective runtime values, and when each applies (api.md §6).

    The stage bindings and workflow limits a run would use are read from here, never re-derived.

    Raises:
        AppRefused: IdeaPress refused.
        AppUnreachable: It did not answer.
    """
    body = _document(call(client, settings, APP, "GET", "settings"))
    values = body.get("settings")
    definitions = body.get("definitions")
    return {
        "settings": dict(values) if isinstance(values, Mapping) else {},
        "definitions": dict(definitions) if isinstance(definitions, Mapping) else {},
    }
