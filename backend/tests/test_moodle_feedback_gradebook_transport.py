"""TF-435: GradebookFeedbackTransport (fallback via core_grades_update_grades)."""

from unittest.mock import patch

from services.moodle_feedback.payload import (
    FeedbackPayload,
    QuestionFeedback,
    StudentFeedback,
)
from services.moodle_feedback.transports import (
    GradebookFeedbackTransport,
    _moodle_lookup_field,
)
from services.moodle_feedback.ws_client import MoodleWsError


def _payload():
    return FeedbackPayload(
        quiz_id=99,
        students=[
            StudentFeedback(
                external_id="a@x.com",
                total_points_awarded=3.0,
                total_points_max=5.0,
                questions=[QuestionFeedback(slot=1, mark=3.0, comment="gut <b>")],
            ),
        ],
    )


def test_gradebook_resolves_cm_then_pushes_grade_and_feedback():
    transport = GradebookFeedbackTransport(base_url="https://m", token="tok")

    def fake_call(base, token, fn, params, **kw):
        if fn == "core_course_get_course_module_by_instance":
            return {"cm": {"id": 555, "course": 12}}
        if fn == "core_user_get_users_by_field":
            return [{"id": 7, "email": "a@x.com"}]
        if fn == "core_grades_update_grades":
            return 0  # GRADE_UPDATE_OK
        raise AssertionError(fn)

    with patch(
        "services.moodle_feedback.transports.call_moodle",
        side_effect=fake_call,
    ) as mock_call:
        results = transport.push(_payload())

    calls = {c.args[2] for c in mock_call.call_args_list}
    assert "core_grades_update_grades" in calls
    grade_call = next(
        c for c in mock_call.call_args_list if c.args[2] == "core_grades_update_grades"
    )
    params = grade_call.args[3]
    assert params["courseid"] == 12
    assert params["component"] == "mod_quiz"
    assert params["activityid"] == 555
    assert params["grades"][0]["studentid"] == 7
    assert params["grades"][0]["grade"] == 3.0
    # Feedback contains the (escaped) comment and is HTML
    assert "gut &lt;b&gt;" in params["grades"][0]["str_feedback"]
    assert results["a@x.com"].status == "ok"


def test_gradebook_user_not_found():
    transport = GradebookFeedbackTransport(base_url="https://m", token="tok")

    def fake_call(base, token, fn, params, **kw):
        if fn == "core_course_get_course_module_by_instance":
            return {"cm": {"id": 1, "course": 1}}
        if fn == "core_user_get_users_by_field":
            return []
        raise AssertionError(fn)

    with patch(
        "services.moodle_feedback.transports.call_moodle",
        side_effect=fake_call,
    ):
        results = transport.push(_payload())
    assert results["a@x.com"].status == "not_found"


def test_gradebook_marks_all_error_when_cm_unresolved():
    """A malformed course-module reply degrades to all-error, no crash."""
    transport = GradebookFeedbackTransport(base_url="https://m", token="tok")

    def fake_call(base, token, fn, params, **kw):
        if fn == "core_course_get_course_module_by_instance":
            return {}  # missing 'cm' → KeyError-class shape error, caught
        raise AssertionError(fn)

    with patch(
        "services.moodle_feedback.transports.call_moodle",
        side_effect=fake_call,
    ):
        results = transport.push(_payload())
    assert results["a@x.com"].status == "error"


def test_moodle_lookup_field_picks_by_identifier_shape():
    """The lookup field must follow external_id shape, not hardcode email."""
    assert _moodle_lookup_field("a@b.c") == "email"
    assert _moodle_lookup_field("12345") == "id"
    assert _moodle_lookup_field("jdoe") == "username"


def test_gradebook_per_student_isolation():
    """One student's grade-update failure must not abort the others."""
    transport = GradebookFeedbackTransport(base_url="https://m", token="tok")
    payload = FeedbackPayload(
        quiz_id=99,
        students=[
            StudentFeedback(
                external_id="a@x.com",
                total_points_awarded=3.0,
                total_points_max=5.0,
                questions=[QuestionFeedback(slot=1, mark=3.0, comment="ok")],
            ),
            StudentFeedback(
                external_id="b@x.com",
                total_points_awarded=2.0,
                total_points_max=5.0,
                questions=[QuestionFeedback(slot=1, mark=2.0, comment="ok")],
            ),
        ],
    )

    def fake_call(base, token, fn, params, **kw):
        if fn == "core_course_get_course_module_by_instance":
            return {"cm": {"id": 1, "course": 1}}
        if fn == "core_user_get_users_by_field":
            return [{"id": 1 if params["values"][0] == "a@x.com" else 2}]
        if fn == "core_grades_update_grades":
            if params["grades"][0]["studentid"] == 1:
                raise MoodleWsError("a failed")  # only student A's push fails
            return 0
        raise AssertionError(fn)

    with patch(
        "services.moodle_feedback.transports.call_moodle",
        side_effect=fake_call,
    ):
        results = transport.push(payload)

    assert results["a@x.com"].status == "error"  # isolated failure
    assert results["b@x.com"].status == "ok"  # not aborted


def test_gradebook_empty_questions_marked_partial_not_pushed():
    """A student with no slot-mapped question is PARTIAL, never an OK 0-mark push."""
    transport = GradebookFeedbackTransport(base_url="https://m", token="tok")
    payload = FeedbackPayload(
        quiz_id=99,
        students=[
            StudentFeedback(
                external_id="empty@x.com",
                total_points_awarded=0.0,
                total_points_max=5.0,
                questions=[],
            ),
        ],
    )

    def fake_call(base, token, fn, params, **kw):
        if fn == "core_course_get_course_module_by_instance":
            return {"cm": {"id": 1, "course": 1}}
        raise AssertionError(f"no per-student call expected, got {fn}")

    with patch(
        "services.moodle_feedback.transports.call_moodle",
        side_effect=fake_call,
    ):
        results = transport.push(payload)

    assert results["empty@x.com"].status == "partial"
    assert results["empty@x.com"].errors
