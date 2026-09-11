"""weightroom.services.loadcoach_actions — what an operator does to LoadCoach (row WP2).

Every action is one call to LoadCoach's own API, which validates the request and refuses in its own
words; nothing here re-decides what LoadCoach decides. What is done here and nowhere else is turning
a form's text fields into the wire body — a blank field into an absent key, a number into a number —
and refusing a field that cannot parse before anything is sent.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Final

from baseaicore import SuiteError

from weightroom.services.app_api import call
from weightroom.services.loadcoach_pages import APP, segment

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings

__all__ = [
    "RUNTIME_PROFILE_FIELDS",
    "LoadCoachFormInvalid",
    "discover",
    "explain",
    "route_body",
    "set_enabled",
    "warm",
]

RUNTIME_PROFILE_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("context_size", "int"),
    ("gpu_layers", "int"),
    ("threads", "int"),
    ("batch_size", "int"),
    ("kv_cache_precision", "text"),
    ("keep_alive", "text"),
    ("flash_attention", "bool"),
)
"""``overrides.runtime_profile``'s keys (routing §10) and how the form's text becomes each."""

_DISCOVER_TIMEOUT_SECONDS: Final = 120.0
"""A scan asks every registration what it serves; a llama.cpp directory is hashed on the way."""
_ACTION_TIMEOUT_SECONDS: Final = 30.0


class LoadCoachFormInvalid(SuiteError):
    """A field the page sent cannot become LoadCoach's body; nothing was sent."""

    code: ClassVar[str] = "VALIDATION_ERROR"


def _number(label: str, raw: str, *, minimum: int) -> int | None:
    text = raw.strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        message = f"{label} must be a whole number; got {text!r}."
        raise LoadCoachFormInvalid(message, details={"field": label}) from exc
    if value < minimum:
        message = f"{label} must be at least {minimum}; got {value}."
        raise LoadCoachFormInvalid(message, details={"field": label})
    return value


def route_body(  # noqa: PLR0913 — one keyword per field of POST /route's body
    *,
    task: str,
    estimated_input_tokens: str,
    max_output_tokens: str,
    requires_capabilities: str,
    model: str,
    adapter: str,
    runtime_profile: Mapping[str, str],
    disallow_fallback: bool,
    require_evidence: bool,
    ignore_residency: bool,
) -> dict[str, Any]:
    """The ``POST /route`` body the explain form describes (api.md §3, routing §10).

    ``POST /route`` takes no data classification — only ``/generate`` and ``/jobs`` do, where an
    adapter's classification is joined with the caller's — so the form offers none.

    Args:
        task: The task profile id. Required.
        estimated_input_tokens: A whole number, or blank.
        max_output_tokens: A whole number of at least 1, or blank.
        requires_capabilities: Capability ids, comma-separated, or blank.
        model: A canonical id to pin, or blank.
        adapter: An adapter's manifest name to pin, or blank.
        runtime_profile: ``overrides.runtime_profile`` keys to their form text; blanks are dropped.
        disallow_fallback: Refuse a fallback candidate.
        require_evidence: Refuse a candidate with no measured evidence.
        ignore_residency: Zero both residency terms for this call.

    Returns:
        The JSON body; ``overrides`` only when one of them was set.

    Raises:
        LoadCoachFormInvalid: The task is blank, or a number does not parse.
    """
    if not task.strip():
        message = "Choose a task profile; routing ranks candidates against one."
        raise LoadCoachFormInvalid(message, details={"field": "task"})
    body: dict[str, Any] = {"task": task.strip()}
    tokens_in = _number("Estimated input tokens", estimated_input_tokens, minimum=0)
    if tokens_in is not None:
        body["estimated_input_tokens"] = tokens_in
    tokens_out = _number("Max output tokens", max_output_tokens, minimum=1)
    if tokens_out is not None:
        body["max_output_tokens"] = tokens_out
    capabilities = [part.strip() for part in requires_capabilities.split(",") if part.strip()]
    if capabilities:
        body["constraints"] = {"requires_capabilities": capabilities}
    profile: dict[str, Any] = {}
    for name, kind in RUNTIME_PROFILE_FIELDS:
        raw = str(runtime_profile.get(name) or "").strip()
        if not raw:
            continue
        if kind == "int":
            profile[name] = _number(name, raw, minimum=0)
        elif kind == "bool":
            profile[name] = raw == "true"
        else:
            profile[name] = raw
    overrides: dict[str, Any] = {}
    if model.strip():
        overrides["model"] = model.strip()
    if adapter.strip():
        overrides["adapter"] = adapter.strip()
    if profile:
        overrides["runtime_profile"] = profile
    for key, flag in (
        ("disallow_fallback", disallow_fallback),
        ("require_evidence", require_evidence),
        ("ignore_residency", ignore_residency),
    ):
        if flag:
            overrides[key] = True
    if overrides:
        body["overrides"] = overrides
    return body


def explain(client: httpx.Client, settings: Settings, body: Mapping[str, Any]) -> dict[str, Any]:
    """``POST /route``: the full routing explanation, without executing anything.

    Raises:
        AppRefused: ``TASK_PROFILE_NOT_FOUND``, ``NO_ELIGIBLE_MODEL`` (every candidate and its
            rejection in ``app_details``), ``ADAPTER_NOT_FOUND``, ``VALIDATION_ERROR``.
        AppUnreachable: It did not answer.
    """
    document = call(
        client, settings, APP, "POST", "route", body=dict(body),
        timeout_seconds=_ACTION_TIMEOUT_SECONDS,
    )  # fmt: skip
    return dict(document) if isinstance(document, Mapping) else {}


def discover(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``POST /models/discover``: one discovery pass over every registration.

    Raises:
        AppRefused: LoadCoach refused (the console's token below ``admin``).
        AppUnreachable: It did not answer.
    """
    document = call(
        client, settings, APP, "POST", "models/discover", timeout_seconds=_DISCOVER_TIMEOUT_SECONDS
    )
    return dict(document) if isinstance(document, Mapping) else {}


def warm(client: httpx.Client, settings: Settings, model_ref: str) -> dict[str, Any]:
    """``POST /models/{ref}/warm``: one small pinned job through the ordinary queue.

    Raises:
        AppRefused: ``MODEL_NOT_FOUND``, ``QUEUE_FULL``, or another refusal.
        AppUnreachable: It did not answer.
    """
    document = call(
        client, settings, APP, "POST", f"models/{segment(model_ref)}/warm",
        timeout_seconds=_ACTION_TIMEOUT_SECONDS,
    )  # fmt: skip
    return dict(document) if isinstance(document, Mapping) else {}


def set_enabled(
    client: httpx.Client, settings: Settings, model_ref: str, *, enabled: bool
) -> dict[str, Any]:
    """ADR-0118's flag, through the catalog's own call (row W8) rather than a second one.

    Raises:
        CatalogRefused: LoadCoach did not answer, or refused (its message carried through).
    """
    from weightroom.services.catalog import set_enabled as catalog_set_enabled

    return catalog_set_enabled(settings, APP, segment(model_ref), enabled=enabled, client=client)
