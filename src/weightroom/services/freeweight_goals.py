"""weightroom.services.freeweight_goals — the data and calls behind FreeWeight's Goals (row WP4).

A goal is FreeWeight's: its pack on disk, its rows, its hash, its lint and its calibration, and a
goal still being authored is a FreeWeight draft row (spec §10). Every write here goes to
FreeWeight's API through :mod:`~weightroom.services.app_api`, which answers or refuses in
FreeWeight's own words (arc index §2 item 4); this module parses a form into the body FreeWeight's
route takes and nothing more.

While FreeWeight is stopped, the goal listing, one goal's criteria and tasks, and its stored
calibration report read FreeWeight's database — the rows it projected from each pack and the report
it wrote. What only FreeWeight computes — lint, rule proposals, the declared score mix, a report's
band, a draft's proposals — is not recomputed here; a page says it reads it from the running API.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Final

from baseaicore import SuiteError

from weightroom.services.app_api import AppRefused, call
from weightroom.services.app_pages import rows_where
from weightroom.services.freeweight_pages import (
    APP,
    LIST_CAP,
    PAGE_ROWS,
    NotRecorded,
    _document,
    _listed,
    _loads,
    segment,
)

if TYPE_CHECKING:
    import httpx

    from weightroom.config import Settings
    from weightroom.services.db_reader import AppDatabase

__all__ = [
    "DRAFT_STEPS",
    "GoalFormInvalid",
    "commit_edit",
    "create_goal",
    "delete_draft",
    "delete_goal",
    "draft_api",
    "draft_body",
    "draft_step",
    "fork_starter",
    "goal_api",
    "goal_db",
    "goals_api",
    "goals_db",
    "import_bundle",
    "pack_from_form",
    "preview_edit",
    "report_from_rows",
    "save_draft",
    "start_draft",
    "suggest_api",
    "validate_api",
]

_TIMEOUT_SECONDS: Final = 30.0
DRAFT_STEPS: Final[tuple[str, ...]] = ("criteria", "rules", "tasks")
"""The draft steps a form posts to, in FreeWeight's own route names (``/goals/drafts/{id}/…``)."""


class GoalFormInvalid(SuiteError):
    """A form field that cannot become the body FreeWeight's route takes; nothing was sent."""

    code: ClassVar[str] = "VALIDATION_ERROR"


def _json_field(text: str, field: str) -> Any:  # noqa: ANN401 — whatever JSON the field holds
    try:
        return json.loads(text)
    except ValueError as exc:
        message = f"{field} is not JSON: {exc}. Nothing was sent."
        raise GoalFormInvalid(message, details={"field": field}) from exc


# --- Reading --------------------------------------------------------------------------------------


def goals_api(client: httpx.Client, settings: Settings) -> dict[str, Any]:
    """``GET /goals``, ``GET /goals/starters`` and ``GET /goals/drafts``: the Goals page.

    Raises:
        AppRefused: A read FreeWeight refused.
        AppUnreachable: It did not answer.
    """
    listed = call(client, settings, APP, "GET", "goals", timeout_seconds=_TIMEOUT_SECONDS)
    starters = call(client, settings, APP, "GET", "goals/starters")
    drafts = call(client, settings, APP, "GET", "goals/drafts")
    return {
        "goals": _listed(listed, "items"),
        "starters": _listed(starters, "items"),
        "drafts": _listed(drafts, "items"),
    }


def _goal_level(reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The goal's own report row — the one no criterion names — newest first."""
    level = [one for one in reports if one.get("goal_criterion_id") is None]
    return max(level, key=lambda one: str(one.get("measured_at") or ""), default=None)


def _goal_row(row: Mapping[str, Any], report: Mapping[str, Any] | None) -> dict[str, Any]:
    """A ``goals`` row under ``GET /goals``' names; what FreeWeight computes is ``None``."""
    measured = report is not None
    stored = dict(report or {})
    return {
        "slug": row.get("slug"),
        "name": row.get("name"),
        "intent": row.get("intent"),
        "goal_hash": row.get("goal_hash"),
        "goal_pack_version": row.get("goal_pack_version"),
        "capability_id": row.get("capability_id"),
        "contributes_to": row.get("contributes_to"),
        "score_method_mix": None,
        "unforked": bool(row.get("unforked")),
        "forked_from": row.get("forked_from"),
        "calibration_state": (
            None
            if report is None
            else "calibrated"
            if stored.get("passed_gate")
            else "uncalibrated"
        ),
        "kappa_w": stored.get("kappa_w"),
        "n_holdout": stored.get("n_holdout"),
        "calibrated_at": stored.get("measured_at"),
        "calibration_stale": measured and stored.get("goal_hash") != row.get("goal_hash"),
    }


def goals_db(handle: AppDatabase) -> dict[str, Any]:
    """Every goal FreeWeight projected into its database, with its stored calibration.

    Starters ship inside FreeWeight's package and drafts are read back through its API, so both
    are ``None`` here.

    Raises:
        TableUnknown: A table this reader expects is absent.
        ReadFailed: The database refused or ran past the timeout.
    """
    reports: dict[Any, list[dict[str, Any]]] = {}
    for one in rows_where(handle, "calibration_reports", limit=LIST_CAP * 4):
        reports.setdefault(one.get("goal_id"), []).append(one)
    return {
        "goals": [
            _goal_row(row, _goal_level(reports.get(row.get("id"), [])))
            for row in rows_where(
                handle, "goals", order_by="slug", descending=False, limit=LIST_CAP
            )
        ],
        "starters": None,
        "drafts": None,
    }


def goal_api(client: httpx.Client, settings: Settings, slug: str) -> dict[str, Any]:
    """``GET /goals/{slug}`` and the goal's results (``GET /results?suite=goal.<slug>``).

    A refused results read leaves ``results`` ``None``, so the goal still renders.

    Raises:
        AppRefused: ``GOAL_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    goal = _document(
        call(
            client, settings, APP, "GET", f"goals/{segment(slug)}", timeout_seconds=_TIMEOUT_SECONDS
        )
    )
    try:
        results: list[dict[str, Any]] | None = _listed(
            call(
                client, settings, APP, "GET", "results",
                params={"suite": f"goal.{goal.get('slug') or slug}", "limit": PAGE_ROWS},
                timeout_seconds=_TIMEOUT_SECONDS,
            ),
            "items",
        )  # fmt: skip
    except AppRefused:
        results = None
    return {"goal": goal, "results": results}


def report_from_rows(
    criteria: list[dict[str, Any]], reports: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """A stored calibration report, from the rows FreeWeight wrote, under the report's names.

    FreeWeight writes one row for the goal and one per judged criterion together, and replaces the
    set on every calibration. The goal-level band is FreeWeight's reading of the coefficient and is
    not stored, so it is ``None``; each criterion's band and lint are stored beside its figures.
    """
    level = _goal_level(reports)
    if level is None:
        return None
    by_id = {one.get("id"): one for one in criteria}
    detail = _document(_loads(level.get("disagreement_json")))
    rows = []
    for one in reports:
        criterion = by_id.get(one.get("goal_criterion_id"))
        if criterion is None:
            continue
        stored = _document(_loads(one.get("disagreement_json")))
        rows.append(
            {
                "criterion": criterion.get("key"),
                "weight": criterion.get("weight"),
                "kappa_w": one.get("kappa_w"),
                "rho": one.get("rho"),
                "mae": one.get("mae"),
                "bias": one.get("bias"),
                "n_holdout": one.get("n_holdout"),
                "inter_juror_alpha": one.get("inter_juror_alpha"),
                "judge_validity_factor": one.get("judge_validity_factor"),
                "band": stored.get("band"),
                "lint": stored.get("lint"),
                "disagreements": _listed(stored, "samples"),
            }
        )
    return {
        "goal_hash": level.get("goal_hash"),
        "calibration_state": "calibrated" if level.get("passed_gate") else "uncalibrated",
        "passed_gate": bool(level.get("passed_gate")),
        "weighted_kappa_w": level.get("kappa_w"),
        "min_agreement": level.get("min_agreement"),
        "judge_validity_factor": level.get("judge_validity_factor"),
        "n_holdout": level.get("n_holdout"),
        "n_anchor": level.get("n_anchor"),
        "band": None,
        "criteria": rows,
        "judge_set": _loads(level.get("judge_set_json")),
        "graded_by": level.get("graded_by"),
        "measured_at": level.get("measured_at"),
        "policy_version": level.get("policy_version"),
        "warnings": [str(one) for one in detail.get("warnings") or []],
    }


def goal_db(handle: AppDatabase, slug: str) -> dict[str, Any]:
    """One goal's rows under ``GET /goals/{slug}``' names: criteria, tasks, lint and its report.

    The pack's documents live on disk, read by FreeWeight, so ``pack`` is ``None``; so are the
    goal's results, which are FreeWeight's metric query.

    Raises:
        NotRecorded: FreeWeight's database holds no goal with that slug.
        TableUnknown: A table this reader expects is absent.
        ReadFailed: The database refused or ran past the timeout.
    """
    found = rows_where(handle, "goals", equals={"slug": slug}, limit=1)
    if not found:
        raise NotRecorded(f"FreeWeight's database holds no goal {slug!r}.", details={"goal": slug})
    row = found[0]
    mine = {"goal_id": row.get("id")}
    criteria = rows_where(
        handle, "goal_criteria", equals=mine, order_by="ordinal", descending=False, limit=LIST_CAP
    )
    tasks = rows_where(
        handle, "goal_tasks", equals=mine, order_by="ordinal", descending=False, limit=LIST_CAP
    )
    reports = rows_where(handle, "calibration_reports", equals=mine, limit=LIST_CAP)
    goal = _goal_row(row, _goal_level(reports))
    goal.update(
        {
            "criteria": [
                {
                    "key": one.get("key"),
                    "name": one.get("name"),
                    "rung": one.get("rung"),
                    "weight": one.get("weight"),
                    "gate": bool(one.get("is_gate")),
                    "rule_type": _document(_loads(one.get("rule_json"))).get("type"),
                    "scale_points": one.get("scale_points"),
                    "has_scale_descriptors": bool(_loads(one.get("scale_descriptors_json"))),
                }
                for one in criteria
            ],
            "tasks": [
                {
                    "key": one.get("key"),
                    "name": one.get("name"),
                    "prompt_id": one.get("prompt_id"),
                    "prompt_version": one.get("prompt_version"),
                    "prompt_sha256": one.get("prompt_sha256"),
                    "rendered_prompt_hash": one.get("rendered_prompt_hash"),
                    "is_starter": bool(one.get("is_starter")),
                    "has_source": _loads(one.get("source_json")) is not None,
                }
                for one in tasks
            ],
            "findings": [
                dict(one) for one in _loads(row.get("lint_json")) or [] if isinstance(one, Mapping)
            ],
            "pack": None,
            "calibration": report_from_rows(criteria, reports),
        }
    )
    return {"goal": goal, "results": None}


def draft_api(client: httpx.Client, settings: Settings, draft_id: str) -> dict[str, Any]:
    """``GET /goals/drafts/{id}``: the draft with its proposals, weight shift and grading cost.

    Raises:
        AppRefused: ``NOT_FOUND`` for an unknown or expired draft.
        AppUnreachable: It did not answer.
    """
    return _document(call(client, settings, APP, "GET", f"goals/drafts/{segment(draft_id)}"))


def validate_api(client: httpx.Client, settings: Settings, slug: str) -> dict[str, Any]:
    """``POST /goals/{slug}/validate``: every finding with its severity. A read, though a POST.

    Raises:
        AppRefused: ``GOAL_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    return _document(call(client, settings, APP, "POST", f"goals/{segment(slug)}/validate"))


def suggest_api(client: httpx.Client, settings: Settings, slug: str) -> dict[str, Any]:
    """``POST /goals/{slug}/suggest-rules``: proposals with their parameters, never applied.

    Raises:
        AppRefused: ``GOAL_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    return _document(call(client, settings, APP, "POST", f"goals/{segment(slug)}/suggest-rules"))


# --- Acting ---------------------------------------------------------------------------------------


def pack_from_form(*, goal_text: str, tasks_text: str) -> dict[str, Any]:
    """The ``{"goal", "tasks"}`` body ``POST /goals`` and ``PUT /goals/{slug}`` take, from a form.

    Raises:
        GoalFormInvalid: A field is not JSON, the goal is not an object, or the tasks are not a
            list of objects. FreeWeight validates everything else.
    """
    goal = _json_field(goal_text, "goal.json")
    tasks = _json_field(tasks_text.strip() or "[]", "tasks")
    if not isinstance(goal, dict):
        raise GoalFormInvalid("goal.json must be a JSON object.", details={"field": "goal.json"})
    if not isinstance(tasks, list) or not all(isinstance(one, dict) for one in tasks):
        message = "tasks must be a JSON list of task prompt records."
        raise GoalFormInvalid(message, details={"field": "tasks"})
    return {"goal": goal, "tasks": tasks}


def create_goal(
    client: httpx.Client, settings: Settings, pack: Mapping[str, Any]
) -> dict[str, Any]:
    """``POST /goals``: the goal with its lint findings, which never block creation.

    Raises:
        AppRefused: ``GOAL_INVALID``, ``CONFLICT`` for a slug in use, ``VALIDATION_ERROR``.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(
            client,
            settings,
            APP,
            "POST",
            "goals",
            body=dict(pack),
            timeout_seconds=_TIMEOUT_SECONDS,
        )
    )


def fork_starter(
    client: httpx.Client, settings: Settings, starter: str, *, slug: str
) -> dict[str, Any]:
    """``POST /goals/starters/{key}/fork``: the forked goal, ``unforked`` until it is edited.

    Raises:
        AppRefused: ``NOT_FOUND`` for an unknown starter, ``CONFLICT`` for a slug in use.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(
            client, settings, APP, "POST", f"goals/starters/{segment(starter)}/fork",
            body={"slug": slug.strip() or None}, timeout_seconds=_TIMEOUT_SECONDS,
        )
    )  # fmt: skip


def start_draft(
    client: httpx.Client, settings: Settings, *, intent: str, name: str, starter: str | None
) -> dict[str, Any]:
    """``POST /goals/drafts``: a draft from step 1's intent, or from a starter to customise.

    Raises:
        AppRefused: ``VALIDATION_ERROR`` for an empty intent, ``NOT_FOUND`` for an unknown starter.
        AppUnreachable: It did not answer.
    """
    body: dict[str, Any] = {"starter": starter} if starter else {"intent": intent, "name": name}
    return _document(call(client, settings, APP, "POST", "goals/drafts", body=body))


def _tristate(value: str) -> bool | None:
    return True if value == "yes" else False if value == "no" else None


def draft_body(step: str, fields: Mapping[str, str]) -> dict[str, Any]:
    """The body one draft step takes, from its form, as FreeWeight's own wizard page posts it.

    Args:
        step: ``criteria``, ``rules`` or ``tasks``.
        fields: The form's text fields.

    Raises:
        GoalFormInvalid: An action the criteria step does not have, a scale size that is not a
            whole number, or rule parameters that are not a JSON object. Nothing is sent.
    """
    if step == "rules":
        text = fields.get("parameters", "").strip()
        parameters = _json_field(text, "parameters") if text else None
        if parameters is not None and not isinstance(parameters, dict):
            raise GoalFormInvalid(
                "The rule parameters must be a JSON object; nothing was accepted.",
                details={"field": "parameters"},
            )
        return {
            "criterion": fields.get("criterion", ""),
            "rule_type": fields.get("rule_type", ""),
            "parameters": parameters,
        }
    if step == "tasks":
        return {"name": fields.get("name", ""), "prompt_text": fields.get("prompt_text", "")}
    action = fields.get("action", "")
    criterion = fields.get("criterion", "")
    if action == "add":
        return {
            "action": action,
            "name": fields.get("name", ""),
            "intent": fields.get("intent", ""),
        }
    if action == "answer":
        return {
            "action": action,
            "criterion": criterion,
            "graded_alike": _tristate(fields.get("graded_alike", "")),
            "one_quality": _tristate(fields.get("one_quality", "")),
        }
    if action == "describe":
        try:
            points = int(fields.get("points") or "5")
        except ValueError as exc:
            message = "The scale size must be a whole number of points."
            raise GoalFormInvalid(message, details={"field": "points"}) from exc
        return {
            "action": action, "criterion": criterion, "points": points,
            "top": fields.get("top", ""), "middle": fields.get("middle", ""),
            "bottom": fields.get("bottom", ""),
        }  # fmt: skip
    if action == "split":
        return {
            "action": action, "criterion": criterion,
            "first": fields.get("first", ""), "second": fields.get("second", ""),
        }  # fmt: skip
    raise GoalFormInvalid(
        f"{action!r} is not one of step 2's actions.", details={"field": "action"}
    )


def draft_step(
    client: httpx.Client, settings: Settings, draft_id: str, step: str, body: Mapping[str, Any]
) -> dict[str, Any]:
    """``POST /goals/drafts/{id}/{criteria|rules|tasks}``: the draft after the step.

    Raises:
        AppRefused: The wizard's own refusal (``VALIDATION_ERROR``), ``NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(
            client, settings, APP, "POST", f"goals/drafts/{segment(draft_id)}/{segment(step)}",
            body=dict(body),
        )
    )  # fmt: skip


def save_draft(
    client: httpx.Client, settings: Settings, draft_id: str, *, slug: str, name: str
) -> dict[str, Any]:
    """``POST /goals/drafts/{id}/save``: ``{"draft", "goal"}`` — the pack it wrote, or already had.

    Raises:
        AppRefused: ``VALIDATION_ERROR`` (no criterion, no task, an unanchored scale), ``CONFLICT``.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(
            client, settings, APP, "POST", f"goals/drafts/{segment(draft_id)}/save",
            body={"slug": slug.strip(), "name": name.strip()}, timeout_seconds=_TIMEOUT_SECONDS,
        )
    )  # fmt: skip


def delete_draft(client: httpx.Client, settings: Settings, draft_id: str) -> None:
    """``DELETE /goals/drafts/{id}``.

    Raises:
        AppRefused: ``NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    call(client, settings, APP, "DELETE", f"goals/drafts/{segment(draft_id)}")


def preview_edit(
    client: httpx.Client, settings: Settings, slug: str, pack: Mapping[str, Any]
) -> dict[str, Any]:
    """``PUT /goals/{slug}?dry_run=true``: the replacement built and discarded, its ``hash_change``.

    Raises:
        AppRefused: ``GOAL_INVALID``, a rename refused, ``GOAL_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(
            client, settings, APP, "PUT", f"goals/{segment(slug)}", params={"dry_run": "true"},
            body=dict(pack), timeout_seconds=_TIMEOUT_SECONDS,
        )
    )  # fmt: skip


def commit_edit(
    client: httpx.Client, settings: Settings, slug: str, pack: Mapping[str, Any]
) -> dict[str, Any]:
    """``PUT /goals/{slug}``: the replacement applied, with the ``hash_change`` it made.

    Raises:
        AppRefused: As :func:`preview_edit`.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(
            client, settings, APP, "PUT", f"goals/{segment(slug)}", body=dict(pack),
            timeout_seconds=_TIMEOUT_SECONDS,
        )
    )  # fmt: skip


def delete_goal(
    client: httpx.Client, settings: Settings, slug: str, *, confirm: bool
) -> dict[str, Any]:
    """``DELETE /goals/{slug}``: FreeWeight's preview, or — confirmed — the deletion it previews.

    Raises:
        AppRefused: ``GOAL_NOT_FOUND``.
        AppUnreachable: It did not answer.
    """
    return _document(
        call(
            client, settings, APP, "DELETE", f"goals/{segment(slug)}",
            params={"dry_run": "false"} if confirm else None, timeout_seconds=_TIMEOUT_SECONDS,
        )
    )  # fmt: skip


def import_bundle(
    client: httpx.Client, settings: Settings, *, bundle_text: str, slug: str
) -> dict[str, Any]:
    """``POST /goals/import``: FreeWeight's size cap, containment and hash checks, then the goal.

    Raises:
        GoalFormInvalid: The bundle is not a JSON object; nothing was sent.
        AppRefused: ``PAYLOAD_TOO_LARGE``, ``GOAL_PATH_UNSAFE``, ``GOAL_HASH_MISMATCH``,
            ``CONFLICT``
            naming the existing ``goal_hash``.
        AppUnreachable: It did not answer.
    """
    bundle = _json_field(bundle_text, "bundle")
    if not isinstance(bundle, dict):
        raise GoalFormInvalid("The bundle must be a JSON object.", details={"field": "bundle"})
    return _document(
        call(
            client, settings, APP, "POST", "goals/import",
            body={"bundle": bundle, "slug": slug.strip() or None}, timeout_seconds=_TIMEOUT_SECONDS,
        )
    )  # fmt: skip
