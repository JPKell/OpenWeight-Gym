"""weightroom.services.ideapress_actions — what the IdeaPress pages ask IdeaPress to do (row WP5).

Each function turns a form into IdeaPress's own body and sends it through the shared client. The
console validates nothing IdeaPress validates: a refusal comes back as :class:`AppRefused` in
IdeaPress's own code and words, and the page renders it. The one check here is the form's own
shape — author material is a JSON object in IdeaPress's body, and a textarea is text.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar, Final

from baseaicore import SuiteError

from weightroom.services.app_api import call
from weightroom.services.ideapress_pages import APP, segment

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings

__all__ = [
    "IdeaPressFormInvalid",
    "author_material",
    "create_project",
    "delete_project",
    "test_backend",
    "update_project",
]

ACTION_TIMEOUT_SECONDS: Final = 60.0
"""A delete that archives first, or a backend round trip, can take longer than a read."""


class IdeaPressFormInvalid(SuiteError):
    """A form field IdeaPress's body cannot carry as typed; nothing was sent."""

    code: ClassVar[str] = "VALIDATION_ERROR"


def author_material(raw: str) -> dict[str, Any]:
    """The form's author material as IdeaPress's body takes it: a JSON object, or nothing.

    Args:
        raw: The textarea's text.

    Returns:
        The object; ``{}`` for blank text.

    Raises:
        IdeaPressFormInvalid: The text is not a JSON object. Nothing is sent.
    """
    text = raw.strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
    except ValueError as exc:
        message = f"Author material must be a JSON object, as IdeaPress stores it: {exc}."
        raise IdeaPressFormInvalid(message, details={"field": "author_material"}) from exc
    if not isinstance(value, dict):
        message = "Author material must be a JSON object ({…}), as IdeaPress stores it."
        raise IdeaPressFormInvalid(message, details={"field": "author_material"})
    return value


def create_project(  # noqa: PLR0913 — one keyword per field of POST /projects' body
    client: httpx.Client,
    settings: Settings,
    *,
    title: str,
    content_type: str,
    workflow_id: str,
    brief: str,
    author_material_text: str,
) -> dict[str, Any]:
    """``POST /projects`` with the create form's fields.

    Raises:
        IdeaPressFormInvalid: The author material is not a JSON object; nothing was sent.
        AppRefused: IdeaPress refused (an empty title is its ``VALIDATION_ERROR``).
        AppUnreachable: It did not answer.
    """
    body = {
        "title": title,
        "content_type": content_type or "article",
        "workflow_id": workflow_id or "standard",
        "brief": brief,
        "author_material": author_material(author_material_text),
    }
    created = call(client, settings, APP, "POST", "projects", body=body)
    return dict(created) if isinstance(created, dict) else {}


def update_project(  # noqa: PLR0913 — one keyword per field of PUT /projects/{id}'s body
    client: httpx.Client,
    settings: Settings,
    project_id: str,
    *,
    title: str,
    brief: str,
    author_material_text: str,
    status: str,
) -> dict[str, Any]:
    """``PUT /projects/{id}``. IdeaPress never recompiles requirements on a save (api.md §2).

    Raises:
        IdeaPressFormInvalid: The author material is not a JSON object; nothing was sent.
        AppRefused: IdeaPress refused (an unknown status is its ``VALIDATION_ERROR``).
        AppUnreachable: It did not answer.
    """
    body: dict[str, Any] = {
        "title": title,
        "brief": brief,
        "author_material": author_material(author_material_text),
    }
    if status:
        body["status"] = status
    updated = call(client, settings, APP, "PUT", f"projects/{segment(project_id)}", body=body)
    return dict(updated) if isinstance(updated, dict) else {}


def delete_project(
    client: httpx.Client, settings: Settings, project_id: str, *, confirm: bool, archive: bool
) -> dict[str, Any]:
    """``DELETE /projects/{id}``: IdeaPress's preview, or the delete, archiving first when asked.

    Raises:
        AppRefused: ``PROJECT_NOT_FOUND``, or ``EXPORT_FAILED`` when the archive could not be
            written — in which case IdeaPress deleted nothing.
        AppUnreachable: It did not answer.
    """
    answer = call(
        client, settings, APP, "DELETE", f"projects/{segment(project_id)}",
        params={"confirm": "true" if confirm else None, "archive": "true" if archive else None},
        timeout_seconds=ACTION_TIMEOUT_SECONDS,
    )  # fmt: skip
    return dict(answer) if isinstance(answer, dict) else {}


def test_backend(client: httpx.Client, settings: Settings, mode: str) -> dict[str, Any]:
    """``POST /backends/test``: a round trip to one backend — latency, models, version.

    Raises:
        AppRefused: IdeaPress refused (a mode it cannot build).
        AppUnreachable: It did not answer.
    """
    answer = call(
        client, settings, APP, "POST", "backends/test", body={"mode": mode or None},
        timeout_seconds=ACTION_TIMEOUT_SECONDS,
    )  # fmt: skip
    return dict(answer) if isinstance(answer, dict) else {}
