"""weightroom.web.routes.freeweight_goals — FreeWeight's Goals page under its tab (row WP4).

Goals, starters, drafts and the authoring wizard, at parity with FreeWeight's own ``goals`` pages,
which a browser on the LAN cannot reach: FreeWeight binds loopback (ADR-0126). Every page reads by
spec §7.3's rule through :mod:`~weightroom.services.freeweight_goals`, and every action is a form
post that FreeWeight's API validates and refuses in its own words, writing exactly one audit row
whichever way it goes (spec §11 contract 2).

Two actions are shown before they happen. An edit that moves ``goal_hash`` is FreeWeight's own dry
run first — the old hash, the new one and the runs it separates — and commits only when the
operator confirms those same hashes. A deletion is FreeWeight's preview first, and happens only
when the slug is typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from baseaicore import SuiteError
from fastapi import APIRouter, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from weightroom.services import freeweight_goals as goals
from weightroom.services.app_api import download
from weightroom.services.apps import AppUnreachable
from weightroom.services.freeweight_pages import _document, segment
from weightroom.web.routes.apps import app_view, read_app_page, render_app_page
from weightroom.web.routes.freeweight import (
    APP,
    BASE,
    _audit,
    _clients,
    _download,
    _href,
    _unanswered,
)
from weightroom.web.routes.jobs import enqueue_job
from weightroom.web.session import CurrentOperator

if TYPE_CHECKING:
    from weightroom.services.auth import Principal

__all__ = ["ui_router"]

ui_router = APIRouter(tags=["ui"], include_in_schema=False)

GOALS: Final = f"{BASE}/goals"
_Text = Annotated[str, Form()]
_Texts = Annotated[list[str] | None, Form()]
CALIBRATE: Final = "freeweight_goal_calibrate"

_DONE: Final[Mapping[str, str]] = {
    "created": "FreeWeight wrote the goal. Its lint findings, if any, are below; none blocks it.",
    "forked": "Forked. The copy is badged unforked until its criteria or its tasks are edited.",
    "edited": "Saved. FreeWeight rewrote goal.json and the tasks and kept the pack's other files.",
    "saved": "The draft is written as a goal pack.",
    "imported": "Imported: FreeWeight checked the bundle's size, members and hash before writing.",
    "deleted": "Deleted: the pack and its rows are gone; the runs it measured keep their results.",
    "draft_deleted": "The draft is abandoned.",
    "samples_added": "FreeWeight added the samples, skipping any whose text the set already had.",
}
"""What a finished action says on the page it lands on — fixed sentences keyed by the redirect's
``done``, so nothing a URL carries is ever rendered as prose."""


def _done(code: str | None) -> str | None:
    return _DONE.get(code or "")


def _refused(  # noqa: PLR0913 — every field of the refused action's one audit row
    request: Request,
    principal: Principal,
    action: str,
    target: str | None,
    exc: SuiteError,
    *,
    params: Mapping[str, Any] | None = None,
) -> None:
    _audit(
        request, principal, action, target=target, outcome="refused", params=dict(params or {}),
        message=exc.message,
    )  # fmt: skip


# --- The goal list, starters, drafts --------------------------------------------------------------


def _goals(
    request: Request,
    principal: Principal,
    *,
    action_error: SuiteError | None = None,
    form: Mapping[str, str] | None = None,
    done: str | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request, view, api=lambda: goals.goals_api(client, settings), database=goals.goals_db
    )
    return render_app_page(
        request,
        principal,
        APP,
        "fw_goals.html",
        selected="Goals",
        view=view,
        sourced=sourced,
        action_error=action_error,
        form=dict(form or {}),
        done_message=_done(done),
    )


@ui_router.get(GOALS, summary="Goals", response_class=HTMLResponse)
def goals_page(
    request: Request, principal: CurrentOperator, done: str | None = None
) -> HTMLResponse:
    """Every goal and its calibration, the drafts in progress, the starters, how to add one."""
    return _goals(request, principal, done=done)


@ui_router.post(GOALS, summary="Create a goal from a pack")
def create_from_page(
    request: Request, principal: CurrentOperator, goal: _Text = "", tasks: _Text = ""
) -> Response:
    """``POST /goals`` with ``goal.json`` and the task records as typed; the goal's page after."""
    client, settings = _clients(request)
    try:
        created = goals.create_goal(
            client, settings, goals.pack_from_form(goal_text=goal, tasks_text=tasks)
        )
    except SuiteError as exc:
        _refused(request, principal, "freeweight.goal_create", None, exc)
        return _goals(request, principal, action_error=exc, form={"goal": goal, "tasks": tasks})
    slug = str(created.get("slug") or "")
    _audit(
        request, principal, "freeweight.goal_create", target=slug, outcome="ok",
        params={"findings": len(created.get("findings") or [])},
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{GOALS}/{segment(slug)}", done="created"), status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.post(f"{GOALS}/import", summary="Import a goal bundle")
def import_from_page(
    request: Request,
    principal: CurrentOperator,
    bundle: _Text = "",
    slug: _Text = "",
    upload: Annotated[UploadFile | None, File()] = None,
) -> Response:
    """``POST /goals/import`` with the bundle chosen as a file or pasted; FreeWeight checks it all.

    A slug already in use comes back as FreeWeight's refusal naming the installed ``goal_hash``.
    """
    text = bundle
    if upload is not None and upload.filename:
        text = upload.file.read().decode("utf-8", errors="replace")
    client, settings = _clients(request)
    params = {"slug": slug.strip() or None, "from_upload": bool(upload and upload.filename)}
    try:
        imported = goals.import_bundle(client, settings, bundle_text=text, slug=slug)
    except SuiteError as exc:
        _refused(
            request, principal, "freeweight.goal_import", slug.strip() or None, exc, params=params
        )
        return _goals(request, principal, action_error=exc, form={"import_slug": slug})
    target = str(imported.get("slug") or "")
    _audit(
        request, principal, "freeweight.goal_import", target=target, outcome="ok",
        params={**params, "goal_hash": imported.get("goal_hash")},
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{GOALS}/{segment(target)}", done="imported"), status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.post(f"{GOALS}/starters/{{starter}}/fork", summary="Fork a starter")
def fork_from_page(
    request: Request, principal: CurrentOperator, starter: str, slug: _Text = ""
) -> Response:
    """``POST /goals/starters/{key}/fork``: the copy is the operator's, badged until edited."""
    client, settings = _clients(request)
    try:
        forked = goals.fork_starter(client, settings, starter, slug=slug)
    except SuiteError as exc:
        _refused(
            request, principal, "freeweight.goal_fork", slug.strip() or None, exc,
            params={"starter": starter},
        )  # fmt: skip
        return _goals(request, principal, action_error=exc)
    target = str(forked.get("slug") or "")
    _audit(
        request, principal, "freeweight.goal_fork", target=target, outcome="ok",
        params={"starter": starter},
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{GOALS}/{segment(target)}", done="forked"), status_code=status.HTTP_303_SEE_OTHER
    )


def _start_draft(
    request: Request, principal: Principal, *, intent: str, name: str, starter: str | None
) -> Response:
    client, settings = _clients(request)
    params = {"starter": starter, "has_intent": bool(intent.strip())}
    try:
        draft = goals.start_draft(client, settings, intent=intent, name=name, starter=starter)
    except SuiteError as exc:
        _refused(request, principal, "freeweight.draft_start", None, exc, params=params)
        return _goals(request, principal, action_error=exc, form={"intent": intent, "name": name})
    draft_id = str(draft.get("draft_id") or "")
    _audit(
        request, principal, "freeweight.draft_start", target=draft_id, outcome="ok", params=params
    )
    return RedirectResponse(
        f"{GOALS}/drafts/{segment(draft_id)}", status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.post(f"{GOALS}/starters/{{starter}}/customise", summary="Customise a starter")
def customise_from_page(request: Request, principal: CurrentOperator, starter: str) -> Response:
    """``POST /goals/drafts {"starter"}``: its criteria and tasks as a draft, nothing written."""
    return _start_draft(request, principal, intent="", name="", starter=starter)


@ui_router.post(f"{GOALS}/drafts", summary="Begin a draft")
def draft_from_page(
    request: Request, principal: CurrentOperator, intent: _Text = "", name: _Text = ""
) -> Response:
    """Step 1: what the operator is trying to get, in their own words; step 2 follows."""
    return _start_draft(request, principal, intent=intent, name=name, starter=None)


# --- One draft ------------------------------------------------------------------------------------


def _draft(
    request: Request,
    principal: Principal,
    draft_id: str,
    *,
    action_error: SuiteError | None = None,
    form: Mapping[str, str] | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request, view, api=lambda: goals.draft_api(client, settings, draft_id), database=None
    )
    return render_app_page(
        request, principal, APP, "fw_goal_draft.html", selected="Goals", view=view,
        sourced=sourced, draft_id=draft_id, action_error=action_error, form=dict(form or {}),
    )  # fmt: skip


@ui_router.get(f"{GOALS}/drafts/{{draft_id}}", summary="One draft", response_class=HTMLResponse)
def draft_page(request: Request, principal: CurrentOperator, draft_id: str) -> HTMLResponse:
    """The wizard's steps 2–4 and save on one page: FreeWeight's draft row, re-read each load."""
    return _draft(request, principal, draft_id)


@ui_router.post(f"{GOALS}/drafts/{{draft_id}}/save", summary="Write a draft as a goal pack")
def save_draft_from_page(
    request: Request, principal: CurrentOperator, draft_id: str, slug: _Text = "", name: _Text = ""
) -> Response:
    """``POST /goals/drafts/{id}/save``; a draft already saved answers the pack it wrote."""
    client, settings = _clients(request)
    try:
        saved = goals.save_draft(client, settings, draft_id, slug=slug, name=name)
    except SuiteError as exc:
        _refused(request, principal, "freeweight.draft_save", draft_id, exc)
        return _draft(
            request, principal, draft_id, action_error=exc, form={"slug": slug, "name": name}
        )
    written = _document(saved.get("goal"))
    target = str(written.get("slug") or "")
    _audit(
        request, principal, "freeweight.draft_save", target=target, outcome="ok",
        params={"draft": draft_id, "goal_hash": written.get("goal_hash")},
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{GOALS}/{segment(target)}", done="saved"), status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.post(f"{GOALS}/drafts/{{draft_id}}/delete", summary="Abandon a draft")
def delete_draft_from_page(request: Request, principal: CurrentOperator, draft_id: str) -> Response:
    """``DELETE /goals/drafts/{id}``; a pack the draft already wrote stays."""
    client, settings = _clients(request)
    try:
        goals.delete_draft(client, settings, draft_id)
    except SuiteError as exc:
        _refused(request, principal, "freeweight.draft_delete", draft_id, exc)
        return _draft(request, principal, draft_id, action_error=exc)
    _audit(request, principal, "freeweight.draft_delete", target=draft_id, outcome="ok", params={})
    return RedirectResponse(
        _href(GOALS, done="draft_deleted"), status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.post(f"{GOALS}/drafts/{{draft_id}}/{{step}}", summary="One wizard step")
def draft_step_from_page(  # noqa: PLR0913 — one parameter per field the three steps' forms carry
    request: Request,
    principal: CurrentOperator,
    draft_id: str,
    step: Literal["criteria", "rules", "tasks"],
    action: _Text = "",
    name: _Text = "",
    intent: _Text = "",
    criterion: _Text = "",
    graded_alike: _Text = "",
    one_quality: _Text = "",
    points: _Text = "",
    top: _Text = "",
    middle: _Text = "",
    bottom: _Text = "",
    first: _Text = "",
    second: _Text = "",
    rule_type: _Text = "",
    parameters: _Text = "",
    prompt_text: _Text = "",
) -> Response:
    """Add, answer, describe or split a criterion; accept one proposed rule; add a task.

    A proposal is accepted only by this form, one at a time — FreeWeight never applies one itself.
    The audit row names the step, the action, the criterion and the rule type; no text the operator
    wrote reaches it.
    """
    fields = {
        "action": action, "name": name, "intent": intent, "criterion": criterion,
        "graded_alike": graded_alike, "one_quality": one_quality, "points": points, "top": top,
        "middle": middle, "bottom": bottom, "first": first, "second": second,
        "rule_type": rule_type, "parameters": parameters, "prompt_text": prompt_text,
    }  # fmt: skip
    params = {
        "step": step,
        "action": (action or None) if step == "criteria" else None,
        "criterion": criterion or None,
        "rule_type": rule_type or None,
    }
    client, settings = _clients(request)
    try:
        goals.draft_step(client, settings, draft_id, step, goals.draft_body(step, fields))
    except SuiteError as exc:
        _refused(request, principal, "freeweight.draft_edit", draft_id, exc, params=params)
        return _draft(request, principal, draft_id, action_error=exc, form=fields)
    _audit(
        request, principal, "freeweight.draft_edit", target=draft_id, outcome="ok", params=params
    )
    return RedirectResponse(
        f"{GOALS}/drafts/{segment(draft_id)}#step-{step}", status_code=status.HTTP_303_SEE_OTHER
    )


# --- One goal -------------------------------------------------------------------------------------


def _goal(  # noqa: PLR0913 — what an action leaves on the goal's page
    request: Request,
    principal: Principal,
    slug: str,
    *,
    action_error: SuiteError | None = None,
    preview: Mapping[str, Any] | None = None,
    mismatched: bool = False,
    check: str | None = None,
    done: str | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: goals.goal_api(client, settings, slug),
        database=lambda handle: goals.goal_db(handle, slug),
    )
    checked: dict[str, Any] | None = None
    if check in ("validate", "suggest") and sourced.live and action_error is None:
        try:
            reader = goals.validate_api if check == "validate" else goals.suggest_api
            checked = reader(client, settings, slug)
        except SuiteError as exc:
            action_error = exc
    return render_app_page(
        request, principal, APP, "fw_goal.html", selected="Goals", view=view, sourced=sourced,
        slug=slug, action_error=action_error, preview=dict(preview) if preview else None,
        mismatched=mismatched, check=check if checked is not None else None, checked=checked,
        done_message=_done(done),
    )  # fmt: skip


@ui_router.get(f"{GOALS}/{{slug}}", summary="One goal", response_class=HTMLResponse)
def goal_page(
    request: Request,
    principal: CurrentOperator,
    slug: str,
    check: str | None = None,
    done: str | None = None,
) -> HTMLResponse:
    """One goal: identity, hash, calibration, criteria, tasks, lint, results, export and delete.

    ``?check=validate`` and ``?check=suggest`` show FreeWeight's lint and its rule proposals —
    reads, so they are links, not form posts.
    """
    return _goal(request, principal, slug, check=check, done=done)


@ui_router.get(f"{GOALS}/{{slug}}/bundle", summary="Download a goal's bundle", response_model=None)
def bundle_download(request: Request, principal: CurrentOperator, slug: str) -> Response:
    """``GET /goals/{slug}/bundle`` passed through: the file ``goals import`` reads back."""
    client, settings = _clients(request)
    try:
        refused = _unanswered(request)
        if refused is not None:
            raise refused
        headers, body = download(client, settings, APP, f"goals/{segment(slug)}/bundle")
    except SuiteError as exc:
        return _goal(request, principal, slug, action_error=exc)
    return _download(headers, body, f"{slug}.goal-bundle.json")


@ui_router.get(
    f"{GOALS}/{{slug}}/export", summary="Download benchmark.goal_pack", response_model=None
)
def goal_pack_download(request: Request, principal: CurrentOperator, slug: str) -> Response:
    """``GET /goals/{slug}/export`` passed through: the SetSpec description, which never imports."""
    client, settings = _clients(request)
    try:
        refused = _unanswered(request)
        if refused is not None:
            raise refused
        headers, body = download(client, settings, APP, f"goals/{segment(slug)}/export")
    except SuiteError as exc:
        return _goal(request, principal, slug, action_error=exc)
    return _download(headers, body, f"{slug}.goal-pack.json")


@ui_router.post(f"{GOALS}/{{slug}}/delete", summary="Delete a goal, previewed first")
def delete_from_page(
    request: Request, principal: CurrentOperator, slug: str, confirm: _Text = ""
) -> Response:
    """FreeWeight's preview — runs orphaned, grades destroyed — until the slug is typed.

    The preview is a ``pending`` audit row; the deletion, confirmed, an ``ok`` one. The typed text
    is compared with the slug in the URL, which is the goal FreeWeight previewed.
    """
    typed = confirm.strip()
    client, settings = _clients(request)
    try:
        if typed != slug:
            preview = goals.delete_goal(client, settings, slug, confirm=False)
            _audit(
                request, principal, "freeweight.goal_delete", target=slug, outcome="pending",
                params={"preview": True, "orphaned_runs": preview.get("orphaned_runs"),
                        "destroyed_grades": preview.get("destroyed_grades")},
            )  # fmt: skip
            return _goal(request, principal, slug, preview=preview, mismatched=bool(typed))
        deleted = goals.delete_goal(client, settings, slug, confirm=True)
    except SuiteError as exc:
        _refused(
            request, principal, "freeweight.goal_delete", slug, exc,
            params={"preview": typed != slug},
        )  # fmt: skip
        return _goal(request, principal, slug, action_error=exc)
    _audit(
        request, principal, "freeweight.goal_delete", target=slug, outcome="ok",
        params={"preview": False, "orphaned_runs": deleted.get("orphaned_runs"),
                "destroyed_grades": deleted.get("destroyed_grades")},
    )  # fmt: skip
    return RedirectResponse(_href(GOALS, done="deleted"), status_code=status.HTTP_303_SEE_OTHER)


# --- Editing --------------------------------------------------------------------------------------


def _edit(  # noqa: PLR0913 — the form as typed, and what FreeWeight's dry run said about it
    request: Request,
    principal: Principal,
    slug: str,
    *,
    goal_text: str | None = None,
    tasks_text: str | None = None,
    preview: Mapping[str, Any] | None = None,
    moved: bool = False,
    action_error: SuiteError | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request, view, api=lambda: goals.goal_api(client, settings, slug), database=None
    )
    goal = (sourced.data or {}).get("goal") or {}
    pack = _document(goal.get("pack"))
    if goal_text is None:
        goal_text = json.dumps(pack.get("goal") or {}, indent=2, ensure_ascii=False)
    if tasks_text is None:
        tasks_text = json.dumps(pack.get("tasks") or [], indent=2, ensure_ascii=False)
    return render_app_page(
        request, principal, APP, "fw_goal_edit.html", selected="Goals", view=view, sourced=sourced,
        slug=slug, goal_text=goal_text, tasks_text=tasks_text,
        preview=dict(preview) if preview else None, moved=moved, action_error=action_error,
    )  # fmt: skip


@ui_router.get(f"{GOALS}/{{slug}}/edit", summary="Edit a goal", response_class=HTMLResponse)
def edit_page(request: Request, principal: CurrentOperator, slug: str) -> HTMLResponse:
    """``goal.json`` and the task records as FreeWeight holds them on disk, to edit and preview."""
    return _edit(request, principal, slug)


def _change_params(change: Mapping[str, Any], *, confirmed: bool) -> dict[str, Any]:
    return {
        "separates": bool(change.get("separates")),
        "separated_runs": change.get("separated_runs"),
        "changed_fields": list(change.get("changed_fields") or []),
        "previous_goal_hash": change.get("previous_goal_hash"),
        "goal_hash": change.get("goal_hash"),
        "confirmed": confirmed,
    }


@ui_router.post(f"{GOALS}/{{slug}}/edit", summary="Preview, confirm and save an edit")
def edit_from_page(  # noqa: PLR0913 — the edited documents and the hashes a confirmation names
    request: Request,
    principal: CurrentOperator,
    slug: str,
    goal: _Text = "",
    tasks: _Text = "",
    confirm: _Text = "",
    previous_goal_hash: _Text = "",
    goal_hash: _Text = "",
) -> Response:
    """``PUT /goals/{slug}?dry_run=true`` first, always; the real ``PUT`` only when that is safe.

    An edit that leaves ``goal_hash`` where it was is applied at once. One that moves it renders the
    old hash, the new hash and the count of runs it separates, and commits only when the operator
    confirms — and only if FreeWeight's dry run, run again, still names the hashes the operator
    confirmed; if the goal moved in between, the new preview is shown instead.
    """
    client, settings = _clients(request)
    try:
        pack = goals.pack_from_form(goal_text=goal, tasks_text=tasks)
        preview = goals.preview_edit(client, settings, slug, pack)
        change = _document(preview.get("hash_change"))
        wanted = confirm == "yes"
        same = (change.get("previous_goal_hash"), change.get("goal_hash")) == (
            previous_goal_hash, goal_hash,
        )  # fmt: skip
        if change.get("separates") and not (wanted and same):
            _audit(
                request, principal, "freeweight.goal_edit", target=slug, outcome="pending",
                params=_change_params(change, confirmed=False),
            )  # fmt: skip
            return _edit(
                request, principal, slug, goal_text=goal, tasks_text=tasks, preview=preview,
                moved=wanted and not same,
            )  # fmt: skip
        committed = goals.commit_edit(client, settings, slug, pack)
    except SuiteError as exc:
        _refused(request, principal, "freeweight.goal_edit", slug, exc)
        return _edit(
            request, principal, slug, goal_text=goal, tasks_text=tasks, action_error=exc
        )  # fmt: skip
    applied = _document(committed.get("hash_change"))
    _audit(
        request, principal, "freeweight.goal_edit", target=slug, outcome="ok",
        params=_change_params(applied, confirmed=bool(applied.get("separates"))),
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{GOALS}/{segment(slug)}", done="edited"), status_code=status.HTTP_303_SEE_OTHER
    )


# --- Calibration --------------------------------------------------------------------------------


def _calibration(
    request: Request,
    principal: Principal,
    slug: str,
    *,
    action_error: SuiteError | None = None,
    form: Mapping[str, str] | None = None,
    done: str | None = None,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: goals.calibration_api(client, settings, slug),
        database=lambda handle: goals.calibration_db(handle, slug),
    )
    return render_app_page(
        request, principal, APP, "fw_goal_calibration.html", selected="Goals", view=view,
        sourced=sourced, slug=slug, action_error=action_error, form=dict(form or {}),
        done_message=_done(done),
    )  # fmt: skip


@ui_router.get(
    f"{GOALS}/{{slug}}/calibration", summary="A goal's calibration", response_class=HTMLResponse
)
def calibration_page(
    request: Request, principal: CurrentOperator, slug: str, done: str | None = None
) -> HTMLResponse:
    """The calibration set by partition and origin with its grading progress, and how to add to it,
    grade it and run it."""
    return _calibration(request, principal, slug, done=done)


@ui_router.post(f"{GOALS}/{{slug}}/calibration/samples", summary="Add calibration samples")
def samples_from_page(  # noqa: PLR0913 — the paste form's fields and the promotion's run
    request: Request,
    principal: CurrentOperator,
    slug: str,
    mode: _Text = "paste",
    content: _Text = "",
    task: _Text = "",
    run_id: _Text = "",
) -> Response:
    """Paste one text, or promote every completed sample of a run of this goal.

    A promotion names each sample by id and FreeWeight reads the text it stored; the audit row names
    the mode, the run and the counts, never a sample's text.
    """
    client, settings = _clients(request)
    promoting = mode == "promote"
    params = {"mode": "promote" if promoting else "paste", "run": run_id.strip() or None}
    try:
        if promoting:
            outcome = goals.promote_run(client, settings, slug, run_id.strip())
        else:
            outcome = goals.add_pasted(client, settings, slug, content=content, task=task)
    except SuiteError as exc:
        _refused(request, principal, "freeweight.calibration_samples", slug, exc, params=params)
        return _calibration(
            request, principal, slug, action_error=exc,
            form={} if promoting else {"content": content},
        )  # fmt: skip
    _audit(
        request, principal, "freeweight.calibration_samples", target=slug, outcome="ok",
        params={**params, "sent": outcome.get("sent"), "added": outcome.get("added")},
    )  # fmt: skip
    return RedirectResponse(
        _href(f"{GOALS}/{segment(slug)}/calibration", done="samples_added"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@ui_router.post(f"{GOALS}/{{slug}}/calibration/run", summary="Run a goal's calibration")
def calibrate_from_page(request: Request, principal: CurrentOperator, slug: str) -> Response:
    """Enqueue ``freeweight_goal_calibrate`` — ADR-0119's cap, one ``job.enqueue`` row — and follow.

    The operator's name is the report's ``graded_by``: the grades the jury is scored against are
    the ones this operator recorded.
    """
    try:
        job = enqueue_job(
            request, principal, kind=CALIBRATE,
            params={"goal": slug, "graded_by": principal.username}, schedule_id=None,
        )  # fmt: skip
    except SuiteError as exc:
        return _calibration(request, principal, slug, action_error=exc)
    return RedirectResponse(
        f"{GOALS}/{segment(slug)}/calibration/jobs/{segment(job.id)}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@ui_router.get(
    f"{GOALS}/{{slug}}/calibration/jobs/{{job_id}}",
    summary="A calibration being run",
    response_class=HTMLResponse,
)
def calibrating_page(
    request: Request, principal: CurrentOperator, slug: str, job_id: str
) -> HTMLResponse:
    """The job's output as FreeWeight prints it — a line per holdout sample judged — polled live."""
    from weightroom.services.jobs import get_job

    job = None
    error: SuiteError | None = None
    try:
        job = get_job(request.app.state.database, job_id)
        if job.kind != CALIBRATE or job.params.get("goal") != slug:
            message = f"Job {job_id} is not a calibration of {slug}."
            raise goals.GoalFormInvalid(message, details={"job_id": job_id})
    except SuiteError as exc:
        job, error = None, exc
    return render_app_page(
        request, principal, APP, "fw_goal_calibrating.html", selected="Goals", slug=slug,
        job=job, error=error,
    )  # fmt: skip


# --- Grading --------------------------------------------------------------------------------------


def _grading(  # noqa: PLR0913 — where the page opens, and what a failed save leaves on it
    request: Request,
    principal: Principal,
    *,
    slug: str | None,
    run_id: str | None,
    sample: str | None = None,
    after: str | None = None,
    action_error: SuiteError | None = None,
    unreachable: bool = False,
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    if slug is not None:
        base = f"{GOALS}/{segment(slug)}"
        form_action, back = f"{base}/grade", (f"{base}/calibration", "Calibration")
        sourced = read_app_page(
            request, view, api=lambda: goals.grading_api(client, settings, slug), database=None
        )
    else:
        form_action = f"{BASE}/runs/{segment(run_id or '')}/grade"
        back = (f"{BASE}/runs/{segment(run_id or '')}", "The run")
        sourced = read_app_page(
            request, view, api=lambda: goals.run_grading_api(client, settings, run_id or ""),
            database=None,
        )  # fmt: skip
    data = sourced.data or {}
    samples = list(data.get("samples") or [])
    index = goals.pick_sample(samples, len(data.get("criteria") or []), sample=sample, after=after)
    current = samples[index] if index is not None else None
    previous_href = next_href = None
    if index is not None and index > 0:
        previous_href = _href(form_action, sample=samples[index - 1].get("sample_id")) + "#sample"
    if index is not None and index + 1 < len(samples):
        next_href = _href(form_action, sample=samples[index + 1].get("sample_id")) + "#sample"
    return render_app_page(
        request, principal, APP, "fw_goal_grade.html",
        selected="Goals" if slug is not None else "Runs", view=view, sourced=sourced,
        title=data.get("name") or slug or run_id, back_href=back[0], back_label=back[1],
        report_href=f"{GOALS}/{segment(slug)}/report" if slug is not None else None,
        form_action=form_action, current=current, position=(index or 0) + 1, total=len(samples),
        previous_href=previous_href, next_href=next_href, recorded=data.get("recorded"),
        expected=data.get("expected"), complete=data.get("complete"), unreachable=unreachable,
        action_error=action_error,
        empty_message=(
            "No sample to grade yet: add samples on the calibration page."
            if slug is not None
            else "This run stored no completed sample with its text."
        ),
    )  # fmt: skip


def _grade(  # noqa: PLR0913 — one sample's aligned fields, and whose set they grade
    request: Request,
    principal: Principal,
    *,
    slug: str | None,
    run_id: str | None,
    sample_id: str,
    criterion: list[str] | None,
    grade: list[str] | None,
    note: list[str] | None,
) -> Response:
    """Save one sample's grades — calibration or run — and move on to the next unfinished sample.

    Whatever happens writes one audit row naming the sample and the criteria graded. A save
    FreeWeight refused renders its refusal; one it did not answer is ``failed``, and the page
    re-reads what FreeWeight holds, because a batch cut off mid-send may have landed in part — and
    sending it again is safe, each grade being an upsert on its ``(sample, criterion)``.
    """
    criteria, grades, notes = list(criterion or []), list(grade or []), list(note or [])
    action = "freeweight.calibration_grades" if slug is not None else "freeweight.run_grades"
    target = slug if slug is not None else run_id
    params = {
        "sample": sample_id,
        "criteria": [one for one, value in zip(criteria, grades, strict=False) if value.strip()],
    }
    client, settings = _clients(request)
    try:
        batch = goals.grades_from_form(
            sample_id=sample_id, criteria=criteria, grades=grades, notes=notes
        )
        if slug is not None:
            goals.submit_grades(client, settings, slug, batch, graded_by=principal.username)
        else:
            goals.submit_run_grades(
                client, settings, run_id or "", batch, graded_by=principal.username
            )
    except AppUnreachable as exc:
        _audit(
            request, principal, action, target=target, outcome="failed", params=params,
            message=exc.message,
        )  # fmt: skip
        return _grading(
            request, principal, slug=slug, run_id=run_id, sample=sample_id, unreachable=True
        )
    except SuiteError as exc:
        _refused(request, principal, action, target, exc, params=params)
        return _grading(
            request, principal, slug=slug, run_id=run_id, sample=sample_id, action_error=exc
        )
    _audit(request, principal, action, target=target, outcome="ok", params=params)
    base = (
        f"{GOALS}/{segment(slug)}/grade"
        if slug is not None
        else f"{BASE}/runs/{segment(run_id or '')}/grade"
    )
    return RedirectResponse(
        _href(base, after=sample_id) + "#sample", status_code=status.HTTP_303_SEE_OTHER
    )


@ui_router.get(
    f"{GOALS}/{{slug}}/grade", summary="Grade a calibration set", response_class=HTMLResponse
)
def grade_page(
    request: Request,
    principal: CurrentOperator,
    slug: str,
    sample: str | None = None,
    after: str | None = None,
) -> HTMLResponse:
    """One blinded sample at a time, opening at the first one not finished — a sitting resumes."""
    return _grading(request, principal, slug=slug, run_id=None, sample=sample, after=after)


@ui_router.post(f"{GOALS}/{{slug}}/grade", summary="Grade one calibration sample")
def grade_from_page(  # noqa: PLR0913 — the sample and its aligned per-criterion fields
    request: Request,
    principal: CurrentOperator,
    slug: str,
    sample_id: _Text = "",
    criterion: _Texts = None,
    grade: _Texts = None,
    note: _Texts = None,
) -> Response:
    """``POST /goals/{slug}/calibration/grades`` with one sample's grades, then the next sample."""
    return _grade(
        request, principal, slug=slug, run_id=None, sample_id=sample_id, criterion=criterion,
        grade=grade, note=note,
    )  # fmt: skip


@ui_router.get(
    f"{BASE}/runs/{{run_id}}/grade", summary="Grade a goal run", response_class=HTMLResponse
)
def run_grade_page(
    request: Request,
    principal: CurrentOperator,
    run_id: str,
    sample: str | None = None,
    after: str | None = None,
) -> HTMLResponse:
    """A completed goal run's samples on its human criteria, blinded as FreeWeight's own screen."""
    return _grading(request, principal, slug=None, run_id=run_id, sample=sample, after=after)


@ui_router.post(f"{BASE}/runs/{{run_id}}/grade", summary="Grade one of a goal run's samples")
def run_grade_from_page(  # noqa: PLR0913 — the sample and its aligned per-criterion fields
    request: Request,
    principal: CurrentOperator,
    run_id: str,
    sample_id: _Text = "",
    criterion: _Texts = None,
    grade: _Texts = None,
    note: _Texts = None,
) -> Response:
    """``POST /runs/{id}/grades``: FreeWeight refreshes the composites, aggregates and evidence."""
    return _grade(
        request, principal, slug=None, run_id=run_id, sample_id=sample_id, criterion=criterion,
        grade=grade, note=note,
    )  # fmt: skip


# --- The report, judges ---------------------------------------------------------------------------


def _report(
    request: Request, principal: Principal, slug: str, *, action_error: SuiteError | None = None
) -> HTMLResponse:
    view = app_view(request, APP)
    client, settings = _clients(request)
    sourced = read_app_page(
        request,
        view,
        api=lambda: goals.report_api(client, settings, slug),
        database=lambda handle: goals.report_db(handle, slug),
    )
    return render_app_page(
        request, principal, APP, "fw_goal_report.html", selected="Goals", view=view,
        sourced=sourced, slug=slug, action_error=action_error,
    )  # fmt: skip


@ui_router.get(
    f"{GOALS}/{{slug}}/report", summary="A goal's agreement", response_class=HTMLResponse
)
def report_page(request: Request, principal: CurrentOperator, slug: str) -> HTMLResponse:
    """κw, ρ, MAE, bias, α and n per criterion; the gate; the validity factor; the divergences."""
    return _report(request, principal, slug)


@ui_router.get(
    f"{GOALS}/{{slug}}/report/export", summary="Download the report", response_model=None
)
def report_download(request: Request, principal: CurrentOperator, slug: str) -> Response:
    """``GET /goals/{slug}/calibration/report/export``: ``benchmark.calibration_report``."""
    client, settings = _clients(request)
    try:
        refused = _unanswered(request)
        if refused is not None:
            raise refused
        headers, body = download(
            client, settings, APP, f"goals/{segment(slug)}/calibration/report/export"
        )
    except SuiteError as exc:
        return _report(request, principal, slug, action_error=exc)
    return _download(headers, body, f"{slug}.calibration-report.json")


@ui_router.get(f"{BASE}/judges", summary="Judges", response_class=HTMLResponse)
def judges_page(
    request: Request,
    principal: CurrentOperator,
    goal: str | None = None,
    candidate: str | None = None,
) -> HTMLResponse:
    """Every model FreeWeight may seat, with its refusals and ``native.judge`` figures, and a jury
    dry run for a goal and a candidate — reads, so a query string, not a form post."""
    view = app_view(request, APP)
    client, settings = _clients(request)
    wanted, measured = (goal or "").strip() or None, (candidate or "").strip() or None
    sourced = read_app_page(
        request,
        view,
        api=lambda: goals.judges_api(client, settings, goal=wanted, candidate=measured),
        database=None,
    )
    return render_app_page(
        request, principal, APP, "fw_judges.html", selected="Goals", view=view, sourced=sourced,
        goal=wanted or "", candidate=measured or "",
    )  # fmt: skip
