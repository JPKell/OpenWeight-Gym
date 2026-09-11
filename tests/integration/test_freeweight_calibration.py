"""Row WP4 Gate B: FreeWeight's calibration, grading, the report and judges.

The recordings are Gate A's (``tests/fixtures/freeweight/goals``): FreeWeight's own application over
its fake provider, twelve samples graded on the forked starter's two judged criteria (ten of them
in ``grading-partial``), and a calibration measured through FreeWeight's own ``run_calibration``
by a deterministic two-juror jury. The grading test that drops the connection runs against a fake
FreeWeight whose grades are a dictionary, so what landed before the drop is exactly what it holds.
"""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any

import httpx
import respx

from tests.integration.test_freeweight_goals import (
    GOALS,
    SLUG,
    _stopped_goal,
    mock_goals,
    recorded,
)
from tests.integration.test_freeweight_pages import (
    BASE,
    audit,
    fixture,
    freeweight_console,
    page,
    post,
    route_for,
)
from tests.security.test_chat_isolation import HOSTILE, _assert_inert
from tests.support import fill_rows
from weightroom.services.freeweight_goals import (
    GoalFormInvalid,
    grades_from_form,
    grading_view,
    pick_sample,
)
from weightroom.services.jobs import get_job, list_jobs

if TYPE_CHECKING:
    from pathlib import Path

RUN = "01M27RUNOFGOAL00000000000A"
TEST = "01M27TESTOFGOAL0000000000A"
GRADING_RUN = "01WP4GRADERUN000000000000A"


def mock_calibration(router: Any, *, bodies: dict[str, Any] | None = None) -> dict[str, Any]:  # noqa: ANN401
    """Gate A's reads, and the calibration, grading, report and judges recordings beside them."""
    reads = {
        f"goals/{SLUG}/calibration": recorded("calibration"),
        f"goals/{SLUG}/calibration/grading": recorded("grading"),
        f"goals/{SLUG}/calibration/report": recorded("report"),
        "judges": recorded("judges"),
        "models": fixture("models"),
        "runs": {
            "runs": [{"id": RUN, "model": "ollama/qwen3:8b", "label": "calibration samples",
                      "created_at": "2026-09-11T08:00:00Z", "status": "completed"}],
            "page": {"next_cursor": None, "has_more": False},
        },
        f"runs/{GRADING_RUN}/grading": recorded("run-grading"),
    }  # fmt: skip
    reads.update(bodies or {})
    return mock_goals(router, bodies=reads)


# --- Calibration ----------------------------------------------------------------------------------


def test_the_calibration_page_counts_the_set_and_lists_no_sample(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        routes = mock_calibration(router)
        text = page(console, f"{GOALS}/{SLUG}/calibration")
    assert "24 of 24" in text
    assert ">anchor<" in text and ">holdout<" in text and ">pasted<" in text
    for item in recorded("calibration")["items"]:
        assert item["content"] not in text
        assert item["id"] not in text
    assert 'action="/apps/freeweight/runs"' in text
    assert f'name="suite" value="goal.{SLUG}"' in text
    assert f'name="run_id" value="{RUN}"' in text
    assert f'action="{GOALS}/{SLUG}/calibration/run"' in text
    params = routes["runs"].calls.last.request.url.params
    assert (params["suite"], params["status"]) == (f"goal.{SLUG}", "completed")


def test_a_stopped_calibration_set_is_counted_from_the_database(tmp_path: Path) -> None:
    console, database = freeweight_console(tmp_path, state="inactive")
    _stopped_goal(database)
    fill_rows(
        database,
        "calibration_samples",
        [
            {"id": "01STOPPEDSAMP000000000000A", "goal_id": "01STOPPEDGOAL000000000000A",
             "origin": "pasted", "partition": "anchor", "content": "one", "content_sha256": "a"},
            {"id": "01STOPPEDSAMP000000000000B", "goal_id": "01STOPPEDGOAL000000000000A",
             "origin": "imported_run_sample", "partition": "holdout", "content": "two",
             "content_sha256": "b"},
        ],
    )  # fmt: skip
    fill_rows(
        database,
        "calibration_grades",
        [{"id": "01STOPPEDGRADE00000000000A", "calibration_sample_id": "01STOPPEDSAMP000000000000A",
          "goal_criterion_id": "01STOPPEDCRIT000000000000A", "grade": 4, "graded_by": "jordan"}],
    )  # fmt: skip
    text = page(console, f"{GOALS}/house_voice/calibration")
    assert "From the database at revision 0010" in text
    assert "1 of 2" in text
    assert ">imported_run_sample<" in text
    assert "A goal&#39;s runs are read only" in text or "A goal's runs are read only" in text


def test_promotion_names_each_completed_sample_and_sends_no_text(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    run = {"id": RUN, "tests": [{"id": TEST}]}
    first = {
        "samples": [
            {"id": "01SAMPLEA", "status": "completed"},
            {"id": "01SAMPLEB", "status": "failed"},
        ],
        "page": {"next_cursor": "c2", "has_more": True},
    }
    second = {
        "samples": [{"id": "01SAMPLEC", "status": "completed"}],
        "page": {"next_cursor": None},
    }
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        route_for(router, "GET", f"runs/{RUN}").mock(return_value=httpx.Response(200, json=run))
        route_for(router, "GET", f"runs/{RUN}/tests/{TEST}/samples").mock(
            side_effect=[httpx.Response(200, json=first), httpx.Response(200, json=second)]
        )
        added = route_for(router, "POST", f"goals/{SLUG}/calibration/samples").mock(
            return_value=httpx.Response(201, json={"slug": SLUG, "added": ["x"], "count": 2})
        )
        response = post(
            console, f"{GOALS}/{SLUG}/calibration/samples", {"mode": "promote", "run_id": RUN}
        )
    assert response.headers["location"] == f"{GOALS}/{SLUG}/calibration?done=samples_added"
    assert json.loads(added.calls.last.request.content) == {
        "samples": [{"source_sample_id": "01SAMPLEA"}, {"source_sample_id": "01SAMPLEC"}]
    }
    (row,) = audit(console, "freeweight.calibration_samples")
    assert row["params"] == {"mode": "promote", "run": RUN, "sent": 2, "added": 2}


def test_a_pasted_sample_is_sent_with_its_task_and_a_refusal_keeps_the_text(
    tmp_path: Path,
) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        added = route_for(router, "POST", f"goals/{SLUG}/calibration/samples").mock(
            side_effect=[
                httpx.Response(201, json={"count": 1}),
                httpx.Response(
                    400,
                    json={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "A calibration sample needs its text.",
                            "details": {},
                        }
                    },
                ),
            ]
        )
        ok = post(
            console, f"{GOALS}/{SLUG}/calibration/samples",
            {"mode": "paste", "content": "I counted twice.", "task": "inventory_night"},
        )  # fmt: skip
        refused = post(
            console, f"{GOALS}/{SLUG}/calibration/samples",
            {"mode": "paste", "content": "Kept for another try.", "task": ""},
        )  # fmt: skip
    assert ok.status_code == 303
    assert json.loads(added.calls[0].request.content) == {
        "samples": [{"content": "I counted twice.", "goal_task_key": "inventory_night"}]
    }
    assert refused.status_code == 200
    assert "<code>VALIDATION_ERROR</code>" in refused.text
    assert "Kept for another try." in refused.text


def test_running_the_calibration_is_a_capped_job_the_page_follows(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        response = post(console, f"{GOALS}/{SLUG}/calibration/run", {})
    (job,), _more = list_jobs(console.database, limit=5, kind="freeweight_goal_calibrate")
    assert response.headers["location"] == f"{GOALS}/{SLUG}/calibration/jobs/{job.id}"
    assert job.params == {"goal": SLUG, "graded_by": "jordan"}
    (row,) = audit(console, "job.enqueue")
    assert row["outcome"] == "ok"
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        following = page(console, f"{GOALS}/{SLUG}/calibration/jobs/{job.id}")
        elsewhere = page(console, f"{GOALS}/another_goal/calibration/jobs/{job.id}")
    assert f'hx-get="/jobs/{job.id}/output"' in following
    assert "never what it graded" in following
    assert "is not a calibration of another_goal" in elsewhere
    assert get_job(console.database, job.id).state == "queued"


# --- Grading --------------------------------------------------------------------------------------


def test_grading_opens_at_the_first_unfinished_sample_and_shows_nothing_that_unblinds_it(
    tmp_path: Path,
) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    partial = recorded("grading-partial")
    unfinished = next(one for one in partial["samples"] if len(one["grades"]) < 2)
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router, bodies={f"goals/{SLUG}/calibration/grading": partial})
        text = page(console, f"{GOALS}/{SLUG}/grade")
    assert unfinished["content"] in text
    assert f'name="sample_id" value="{unfinished["sample_id"]}"' in text
    assert "20</strong> of <strong>24</strong> grades recorded" in text
    assert " autofocus" in text
    descriptor = partial["criteria"][0]["descriptors"]["5"]
    assert f'<option value="5">5 — {descriptor}</option>' in text.replace("&#39;", "'")
    # The starter's descriptors say "anchored": the words checked are the data's, not English.
    for word in ("pasted", "imported_run_sample", "holdout", "ollama/", "partition_seed"):
        assert word not in text


def test_a_grade_is_sent_per_criterion_and_the_page_moves_on(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    sample = recorded("grading")["samples"][0]["sample_id"]
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        graded = route_for(router, "POST", f"goals/{SLUG}/calibration/grades").mock(
            return_value=httpx.Response(200, json={"recorded": 1})
        )
        response = post(
            console,
            f"{GOALS}/{SLUG}/grade",
            {"sample_id": sample, "criterion": ["dry_wit", "concrete_over_abstract"],
             "grade": ["4", ""], "note": ["wry", ""]},
        )  # fmt: skip
    assert response.headers["location"] == f"{GOALS}/{SLUG}/grade?after={sample}#sample"
    assert json.loads(graded.calls.last.request.content) == {
        "grades": [{"sample_id": sample, "criterion": "dry_wit", "grade": 4, "note": "wry"}],
        "graded_by": "jordan",
    }
    (row,) = audit(console, "freeweight.calibration_grades")
    assert row["params"] == {"sample": sample, "criteria": ["dry_wit"]}


class _GradingFreeWeight:
    """A FreeWeight whose grades are a dictionary keyed by ``(sample, criterion)`` — an upsert — and
    whose first save lands its first grade and then drops the connection."""

    def __init__(self) -> None:
        self.view = copy.deepcopy(recorded("grading-partial"))
        for sample in self.view["samples"]:
            sample["grades"] = {}
        self.held: dict[tuple[str, str], dict[str, Any]] = {}
        self.saves = 0

    def grading(self, _request: httpx.Request) -> httpx.Response:
        body = copy.deepcopy(self.view)
        for sample in body["samples"]:
            for (sample_id, criterion), grade in self.held.items():
                if sample_id == sample["sample_id"]:
                    sample["grades"][criterion] = grade
        body["progress"]["recorded_grades"] = len(self.held)
        return httpx.Response(200, json=body)

    def save(self, request: httpx.Request) -> httpx.Response:
        self.saves += 1
        grades = json.loads(request.content)["grades"]
        landed = grades[:1] if self.saves == 1 else grades
        for one in landed:
            self.held[(one["sample_id"], one["criterion"])] = {
                "grade": one["grade"],
                "note": one["note"],
            }
        if self.saves == 1:
            raise httpx.ReadError("connection dropped mid-batch", request=request)
        return httpx.Response(200, json={"recorded": len(grades)})


def test_a_connection_dropped_mid_batch_shows_what_landed_and_a_resend_lands_once(
    tmp_path: Path,
) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    fake = _GradingFreeWeight()
    first, second = fake.view["samples"][0]["sample_id"], fake.view["samples"][1]["sample_id"]
    form = {
        "sample_id": first, "criterion": ["dry_wit", "concrete_over_abstract"],
        "grade": ["4", "2"], "note": ["wry", "abstract"],
    }  # fmt: skip
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        route_for(router, "GET", f"goals/{SLUG}/calibration/grading").mock(side_effect=fake.grading)
        route_for(router, "POST", f"goals/{SLUG}/calibration/grades").mock(side_effect=fake.save)
        dropped = post(console, f"{GOALS}/{SLUG}/grade", form)
        resent = post(console, f"{GOALS}/{SLUG}/grade", form)
        resumed = page(console, resent.headers["location"].split("#")[0])
    assert dropped.status_code == 200
    assert "FreeWeight did not answer while these grades were being saved" in dropped.text
    assert f'name="sample_id" value="{first}"' in dropped.text
    assert "graded 4" in dropped.text and "graded 2" not in dropped.text
    assert resent.status_code == 303
    assert fake.held == {
        (first, "dry_wit"): {"grade": 4, "note": "wry"},
        (first, "concrete_over_abstract"): {"grade": 2, "note": "abstract"},
    }
    assert f'name="sample_id" value="{second}"' in resumed
    outcomes = [row["outcome"] for row in reversed(audit(console, "freeweight.calibration_grades"))]
    assert outcomes == ["failed", "ok"]


def test_a_goal_runs_human_criteria_are_graded_through_freeweights_run_view(
    tmp_path: Path,
) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    view = recorded("run-grading")
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        text = page(console, f"{BASE}/runs/{GRADING_RUN}/grade")
        saved = route_for(router, "POST", f"runs/{GRADING_RUN}/grades").mock(
            side_effect=[
                httpx.Response(200, json={"recorded": 1}),
                httpx.Response(
                    409,
                    json={
                        "error": {
                            "code": "RUN_NOT_GRADEABLE",
                            "message": "The goal has changed since.",
                            "details": {},
                        }
                    },
                ),
            ]
        )
        ok = post(
            console, f"{BASE}/runs/{GRADING_RUN}/grade",
            {"sample_id": view["samples"][0]["sample_id"], "criterion": "would_publish",
             "grade": "5", "note": ""},
        )  # fmt: skip
        refused = post(
            console, f"{BASE}/runs/{GRADING_RUN}/grade",
            {"sample_id": view["samples"][0]["sample_id"], "criterion": "would_publish",
             "grade": "5", "note": ""},
        )  # fmt: skip
    assert "The inventory did not add up." in text
    assert "task warehouse" in text
    assert f'<a href="{BASE}/runs" aria-current="page">Runs</a>' in text
    assert ok.headers["location"].startswith(f"{BASE}/runs/{GRADING_RUN}/grade?after=")
    assert json.loads(saved.calls[0].request.content)["graded_by"] == "jordan"
    assert "<code>RUN_NOT_GRADEABLE</code>" in refused.text
    outcomes = [row["outcome"] for row in reversed(audit(console, "freeweight.run_grades"))]
    assert outcomes == ["ok", "refused"]


def test_the_page_picks_the_asked_sample_else_the_next_unfinished_one() -> None:
    samples = [
        {"sample_id": "a", "grades": {"x": {}}},
        {"sample_id": "b", "grades": {}},
        {"sample_id": "c", "grades": {"x": {}}},
    ]
    assert pick_sample(samples, 1, sample="c", after=None) == 2
    assert pick_sample(samples, 1, sample=None, after=None) == 1
    assert pick_sample(samples, 1, sample=None, after="b") == 1, "wraps round to the unfinished one"
    finished = [{**one, "grades": {"x": {}}} for one in samples]
    assert pick_sample(finished, 1, sample=None, after="b") == 1
    assert pick_sample([], 1, sample=None, after=None) is None


def test_a_form_that_does_not_line_up_is_refused_and_a_blank_grade_is_left_out() -> None:
    assert grades_from_form(
        sample_id="s", criteria=["x", "y"], grades=["", "3"], notes=["", "n"]
    ) == [{"sample_id": "s", "criterion": "y", "grade": 3, "note": "n"}]
    for bad in ({"criteria": ["x"], "grades": [], "notes": []},
                {"criteria": ["x"], "grades": ["high"], "notes": [""]}):  # fmt: skip
        try:
            grades_from_form(sample_id="s", **bad)
        except GoalFormInvalid:
            continue
        raise AssertionError(bad)
    assert grading_view({"samples": [{"sample_id": "s", "content": "t"}]}, run=False)[
        "samples"
    ] == [{"sample_id": "s", "case_id": None, "text": "t", "grades": {}}]


# --- The report, judges ---------------------------------------------------------------------------


def test_the_report_shows_every_figure_with_its_n_and_both_rationales(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    report = recorded("report")
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router)
        text = page(console, f"{GOALS}/{SLUG}/report")
    assert "The jury agrees with you well enough to be worth trusting" in text
    assert ">passed<" in text and "strong" in text
    for figure in ("0.842", "0.949", "0.60", "+0.60", "1.000", "0.889", "-0.40"):
        assert figure in text
    assert "7 · 5" in text
    assert "0.77" in text  # the goal's judge validity factor
    assert (
        "FreeWeight reports inter-juror agreement per criterion and computes no weighted figure"
        in text
    )
    disagreement = report["criteria"][0]["disagreements"][0]
    assert disagreement["author_note"] in text and disagreement["jury_rationale"] in text
    assert disagreement["excerpt"] in text
    assert f'href="{GOALS}/{SLUG}/report/export"' in text


def test_a_figure_freeweight_could_not_compute_is_a_dash_with_its_reason(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    report = copy.deepcopy(recorded("report"))
    report["calibration_state"], report["passed_gate"] = "uncalibrated", False
    first = report["criteria"][0]
    first.update({"kappa_w": None, "rho": None, "inter_juror_alpha": None})
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router, bodies={f"goals/{SLUG}/calibration/report": report})
        text = page(console, f"{GOALS}/{SLUG}/report")
    assert "Not measurable yet — and that is a useful answer" in text
    assert "emits no capability evidence" in text
    assert (
        'title="the grades for this criterion do not vary, so there was nothing to agree about">—'
        in text
    )
    assert 'title="a jury of one has no inter-juror agreement">—' in text
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(
            router, bodies={f"goals/{SLUG}/calibration/report": recorded("report-insufficient")}
        )
        insufficient = page(console, f"{GOALS}/{SLUG}/report")
    assert "No agreement has been measured for this goal yet." in insufficient


def test_a_stopped_report_is_read_from_the_rows_freeweight_wrote(tmp_path: Path) -> None:
    console, database = freeweight_console(tmp_path, state="inactive")
    _stopped_goal(database)
    text = page(console, f"{GOALS}/house_voice/report")
    assert "From the database at revision 0010" in text
    assert ">not passed<" in text
    assert "0.310" in text and "+0.80" in text and "Generous." in text
    assert "Bunched." in text
    assert "FreeWeight names the band from its running API" in text


def test_judges_show_their_refusals_their_bias_figures_and_a_jury_dry_run(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    judges = copy.deepcopy(recorded("judges"))
    judges["items"].append(
        {"model": "ollama/qwen3:8b", "eligible": False, "reasons": ["self_judging"],
         "judge_benchmark_suite": "native.judge",
         "judge_results": {"run_id": "01M27JUDGERUN000000000000A",
                           "created_at": "2026-09-10T00:00:00.000Z",
                           "metrics": {"pairwise_accuracy": 0.875, "swap_consistency": None}}}
    )  # fmt: skip
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(router, bodies={"judges": judges})
        validate = route_for(router, "POST", "judges/validate").mock(
            return_value=httpx.Response(200, json=recorded("judges-validate"))
        )
        text = page(console, f"{BASE}/judges?goal={SLUG}&candidate=")
    assert json.loads(validate.calls.last.request.content) == {"goal": SLUG, "candidate": None}
    assert "self_judging" in text and ">refused<" in text
    assert "0.875" in text
    assert 'title="its native.judge run reported none">—' in text
    assert 'title="never measured as a judge">—' in text
    assert "jury_reduced" in text
    assert f'<option value="{SLUG}" selected>' in text


def test_the_injection_corpus_renders_inert_in_grading_and_the_report(tmp_path: Path) -> None:
    console, _database = freeweight_console(tmp_path, state="active")
    grading = copy.deepcopy(recorded("grading-partial"))
    for sample in grading["samples"]:
        sample["content"] = HOSTILE
        for grade in sample["grades"].values():
            grade["note"] = HOSTILE
    grading["criteria"][0]["name"] = HOSTILE
    grading["criteria"][0]["descriptors"]["5"] = HOSTILE
    report = copy.deepcopy(recorded("report"))
    for criterion in report["criteria"]:
        criterion["lint"] = HOSTILE
        for disagreement in criterion["disagreements"]:
            disagreement.update(
                {"author_note": HOSTILE, "jury_rationale": HOSTILE, "excerpt": HOSTILE}
            )
    report["warnings"] = [HOSTILE]
    run_view = copy.deepcopy(recorded("run-grading"))
    run_view["samples"][0]["response_text"] = HOSTILE
    with respx.mock(assert_all_called=False) as router:
        mock_calibration(
            router,
            bodies={
                f"goals/{SLUG}/calibration/grading": grading,
                f"goals/{SLUG}/calibration/report": report,
                f"runs/{GRADING_RUN}/grading": run_view,
            },
        )
        for path in (
            f"{GOALS}/{SLUG}/grade?sample={grading['samples'][0]['sample_id']}",
            f"{GOALS}/{SLUG}/report",
            f"{BASE}/runs/{GRADING_RUN}/grade?sample={run_view['samples'][0]['sample_id']}",
        ):
            _assert_inert(page(console, path))
