"""weightroom.services.loadcoach_pages — the data behind LoadCoach's tab (row WP2).

Each page has two readers: one over LoadCoach's own ``/api/v1`` (through
:mod:`~weightroom.services.app_api`) for while it answers, and one over its database
(``data-model.md``) for while it does not, shaping the rows into the API document's names so one
template renders both. Which one runs is :mod:`~weightroom.services.app_pages`' decision, never this
module's. A figure only LoadCoach's arithmetic produces — an evidence summary, a reliability factor,
a regression verdict, a breaker's live state — has no database reader and renders ``—`` when
stopped (ADR-0016), never a number recomputed here.
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
    "NotRecorded",
    "decision_api",
    "decision_db",
    "decisions_api",
    "decisions_db",
    "model_api",
    "model_db",
    "models_api",
    "models_db",
    "reliability_api",
    "reliability_db",
    "segment",
    "task_profile_api",
    "task_profile_db",
    "task_profiles_api",
    "task_profiles_db",
]

APP: Final = "loadcoach"
PAGE_ROWS: Final = 50
LIST_CAP: Final = 200
MODEL_CAP: Final = 500
"""A registry larger than this is read in part when stopped; ``GET /models`` has no cap."""


class NotRecorded(SuiteError):
    """LoadCoach's database holds no such record, or more than one matches a prefix."""

    code: ClassVar[str] = "NOT_FOUND"


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


def _listed(body: Any, key: str) -> list[dict[str, Any]]:  # noqa: ANN401 — a JSON body
    found = body.get(key) if isinstance(body, Mapping) else None
    return [dict(one) for one in found or [] if isinstance(one, Mapping)]


# --- Models ---------------------------------------------------------------------------------------


def models_api(client: httpx.Client, settings: Settings) -> list[dict[str, Any]]:
    """``GET /models``: every model discovery has seen, with its three summaries and adapters.

    Raises:
        AppRefused: LoadCoach refused.
        AppUnreachable: It did not answer.
    """
    return _listed(call(client, settings, APP, "GET", "models", timeout_seconds=30.0), "models")


def _model_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """A ``models`` row under ``GET /models``' names; the summaries are LoadCoach's, so ``None``."""
    return {
        "canonical_id": row.get("canonical_id"),
        "model_ref": row.get("id"),
        "provider_kind": row.get("provider_kind"),
        "provider_name": row.get("provider_name") or "",
        "is_remote": bool(row.get("is_remote")),
        "provider_model_name": row.get("provider_model_name"),
        "identity_confidence": row.get("identity_confidence"),
        "family": row.get("family"),
        "quantization": row.get("quantization"),
        "max_context": row.get("max_context"),
        "size_bytes": row.get("size_bytes"),
        "parameter_count": row.get("parameter_count"),
        "available": bool(row.get("available")),
        "unavailable_reason": row.get("unavailable_reason"),
        "enabled": bool(row.get("enabled")),
        "declared_capabilities": _loads(row.get("declared_capabilities_json")) or {},
        "first_seen_at": row.get("first_seen_at"),
        "last_seen_at": row.get("last_seen_at"),
        "evidence_summary": None,
        "reliability": None,
        "residency": None,
        "adapters": [],
    }


def models_db(handle: AppDatabase) -> list[dict[str, Any]]:
    """The ``models`` table by canonical id.

    Raises:
        TableUnknown: The database has no ``models`` table.
        ReadFailed: The database refused or ran past the timeout.
    """
    rows = rows_where(handle, "models", order_by="canonical_id", descending=False, limit=MODEL_CAP)
    return [_model_row(row) for row in rows]


def model_api(client: httpx.Client, settings: Settings, model_ref: str) -> dict[str, Any]:
    """``GET /models/{model_ref}``: identity, descriptor, evidence per capability, the breaker.

    Raises:
        AppRefused: ``MODEL_NOT_FOUND`` for no match or an ambiguous prefix, or another refusal.
        AppUnreachable: It did not answer.
    """
    body = call(client, settings, APP, "GET", f"models/{segment(model_ref)}", timeout_seconds=30.0)
    return _document(body)


def model_db(handle: AppDatabase, model_ref: str) -> dict[str, Any]:
    """One model by ULID or unambiguous prefix (ADR-0024), with its imported evidence rows.

    Raises:
        NotRecorded: Nothing matches ``model_ref``, or more than one row does.
        TableUnknown: A table this reader expects is absent.
        ReadFailed: The database refused or ran past the timeout.
    """
    wanted = model_ref.strip()
    matches = [
        row
        for row in rows_where(handle, "models", limit=MODEL_CAP)
        if wanted and str(row.get("id") or "").startswith(wanted)
    ]
    if len(matches) != 1:
        raise NotRecorded(
            f"LoadCoach's database holds no model {model_ref!r}."
            if not matches
            else f"{model_ref!r} is ambiguous: {len(matches)} models start with it.",
            details={"model_ref": model_ref},
        )
    row = matches[0]
    evidence = [
        {
            "capability_id": one.get("capability_id"),
            "score": one.get("score"),
            "confidence": one.get("confidence"),
            "sample_count": one.get("sample_count"),
            "source": "benchmark",
            "match_state": one.get("match_state"),
            "runtime_profile_hash": one.get("runtime_profile_hash"),
            "machine_fingerprint": one.get("machine_fingerprint"),
            "measured_at": one.get("measured_at"),
            "stale": bool(one.get("stale")),
            "stale_reason": one.get("stale_reason"),
        }
        for one in rows_where(
            handle,
            "capability_evidence",
            equals={"model_id": row.get("id")},
            order_by="capability_id",
            descending=False,
            limit=LIST_CAP,
        )  # fmt: skip
    ]
    return {
        **_model_row(row),
        "descriptor": _loads(row.get("descriptor_json")),
        "evidence": evidence,
        "reliability_by_task_profile": None,
        "circuit_breaker": None,
    }


# --- Routing --------------------------------------------------------------------------------------


def decisions_api(client: httpx.Client, settings: Settings) -> list[dict[str, Any]]:
    """``GET /routing-decisions``: the most recent decisions, newest first.

    Raises:
        AppRefused: LoadCoach refused.
        AppUnreachable: It did not answer.
    """
    return _listed(call(client, settings, APP, "GET", "routing-decisions"), "decisions")


def decisions_db(handle: AppDatabase) -> list[dict[str, Any]]:
    """The ``routing_decisions`` table, newest first, under the API's names.

    Raises:
        TableUnknown: The database has no ``routing_decisions`` table.
        ReadFailed: The database refused or ran past the timeout.
    """
    decisions = []
    for row in rows_where(handle, "routing_decisions", order_by="requested_at", limit=PAGE_ROWS):
        explanation = _document(_loads(row.get("explanation_json")))
        selected = _document(explanation.get("selected"))
        decisions.append(
            {
                "decision_id": row.get("id"),
                "task_profile": {
                    "id": row.get("task_profile_id"),
                    "version": row.get("task_profile_version"),
                },
                "requested_at": row.get("requested_at"),
                "duration_ms": row.get("duration_ms"),
                "selected": selected.get("canonical_id")
                or row.get("selected_subject_canonical_id"),
                "final_score": row.get("selected_score"),
                "flags": _loads(row.get("flags_json")) or [],
                "job_id": row.get("job_id"),
            }
        )
    return decisions


def decision_api(client: httpx.Client, settings: Settings, decision_id: str) -> dict[str, Any]:
    """``GET /routing-decisions/{id}``: one decision's explanation exactly as it was persisted.

    Raises:
        AppRefused: No such decision, or another refusal.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(client, settings, APP, "GET", f"routing-decisions/{segment(decision_id)}")
    )


def decision_db(handle: AppDatabase, decision_id: str) -> dict[str, Any]:
    """One decision's stored ``explanation_json``, the document the API would have returned.

    Raises:
        NotRecorded: No such decision.
        TableUnknown: The database has no ``routing_decisions`` table.
        ReadFailed: The database refused or ran past the timeout.
    """
    found = rows_where(handle, "routing_decisions", equals={"id": decision_id}, limit=1)
    if not found:
        raise NotRecorded(
            f"LoadCoach's database holds no routing decision {decision_id!r}.",
            details={"decision_id": decision_id},
        )
    return _document(_loads(found[0].get("explanation_json")))


def _profile_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": row.get("profile_id"),
        "version": row.get("version"),
        "description": row.get("description"),
        "weights": _loads(row.get("weights_json")) or {},
        "constraints": _loads(row.get("constraints_json")),
        "execution": _loads(row.get("execution_json")),
        "validation": _loads(row.get("validation_json")),
        "enabled": bool(row.get("enabled")),
        "updated_at": row.get("updated_at"),
    }


def task_profiles_api(client: httpx.Client, settings: Settings) -> list[dict[str, Any]]:
    """``GET /task-profiles``: every definition with its weights, constraints and policies.

    Raises:
        AppRefused: LoadCoach refused.
        AppUnreachable: It did not answer.
    """
    return _listed(call(client, settings, APP, "GET", "task-profiles"), "task_profiles")


def task_profiles_db(handle: AppDatabase) -> list[dict[str, Any]]:
    """The ``task_profiles`` table by profile id.

    Raises:
        TableUnknown: The database has no ``task_profiles`` table.
        ReadFailed: The database refused or ran past the timeout.
    """
    rows = rows_where(
        handle, "task_profiles", order_by="profile_id", descending=False, limit=LIST_CAP
    )
    return [_profile_row(row) for row in rows]


def task_profile_api(client: httpx.Client, settings: Settings, profile_id: str) -> dict[str, Any]:
    """``GET /task-profiles/{id}``.

    Raises:
        AppRefused: ``TASK_PROFILE_NOT_FOUND``, or another refusal.
        AppUnreachable: It did not answer.
    """
    return _document(call(client, settings, APP, "GET", f"task-profiles/{segment(profile_id)}"))


def task_profile_db(handle: AppDatabase, profile_id: str) -> dict[str, Any]:
    """The newest stored version of one task profile.

    Raises:
        NotRecorded: No such profile.
        TableUnknown: The database has no ``task_profiles`` table.
        ReadFailed: The database refused or ran past the timeout.
    """
    found = rows_where(
        handle, "task_profiles", equals={"profile_id": profile_id}, order_by="updated_at", limit=1
    )
    if not found:
        raise NotRecorded(
            f"LoadCoach's database holds no task profile {profile_id!r}.",
            details={"profile_id": profile_id},
        )
    return _profile_row(found[0])


# --- Reliability ----------------------------------------------------------------------------------


def reliability_api(
    client: httpx.Client, settings: Settings, *, task: str | None, model: str | None
) -> dict[str, Any]:
    """``GET /reliability``: each pair's windows, factor, regression verdict and breaker.

    Raises:
        AppRefused: LoadCoach refused.
        AppUnreachable: It did not answer.
    """
    body = call(
        client, settings, APP, "GET", "reliability", params={"task": task, "model": model},
        timeout_seconds=30.0,
    )  # fmt: skip
    return _document(body)


def reliability_db(handle: AppDatabase, *, task: str | None, model: str | None) -> dict[str, Any]:
    """The persisted ``reliability_stats`` rows: counts per window, no factor and no verdict.

    The factor, the regression verdict and each rate's minimum are LoadCoach's arithmetic over these
    counts, so a stopped LoadCoach's page shows the counts and says the rest waits for the API.

    Raises:
        TableUnknown: A table this reader expects is absent.
        ReadFailed: The database refused or ran past the timeout.
    """
    canonical = {
        row.get("id"): row.get("canonical_id")
        for row in rows_where(handle, "models", limit=MODEL_CAP)
    }
    rows = rows_where(
        handle, "reliability_stats", equals={"task_profile_id": task}, order_by="updated_at",
        limit=LIST_CAP * 5,
    )  # fmt: skip
    stats = [
        {
            "canonical_id": canonical.get(row.get("model_id")) or row.get("model_id"),
            "adapter_key": row.get("adapter_key") or "",
            "task_profile_id": row.get("task_profile_id"),
            "window": row.get("window"),
            "attempts": row.get("attempts"),
            "successes": row.get("successes"),
            "validation_passes": row.get("validation_passes"),
            "errors": row.get("errors"),
            "timeouts": row.get("timeouts"),
            "cancellations": row.get("cancellations"),
            "p50_latency_ms": row.get("p50_latency_ms"),
            "p95_latency_ms": row.get("p95_latency_ms"),
            "circuit_state": row.get("circuit_state"),
            "circuit_reason": row.get("circuit_reason"),
            "updated_at": row.get("updated_at"),
        }
        for row in rows
    ]
    if model:
        stats = [one for one in stats if one["canonical_id"] == model]
    return {"stats": stats}
