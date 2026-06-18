"""TF-435: PluginFeedbackTransport (native per-question)."""

from unittest.mock import patch

from services.moodle_feedback.payload import (
    FeedbackPayload,
    QuestionFeedback,
    StudentFeedback,
)
from services.moodle_feedback.transports import PluginFeedbackTransport


def _payload():
    return FeedbackPayload(
        quiz_id=99,
        students=[
            StudentFeedback(
                external_id="a@x.com",
                total_points_awarded=3.0,
                total_points_max=5.0,
                questions=[QuestionFeedback(slot=1, mark=3.0, comment="ok")],
            ),
        ],
    )


def test_plugin_transport_sends_quiz_and_students_and_maps_results():
    transport = PluginFeedbackTransport(base_url="https://m", token="tok")
    moodle_reply = [
        {"useridentifier": "a@x.com", "status": "ok", "graded": 1, "errors": []}
    ]

    with patch(
        "services.moodle_feedback.transports.call_moodle",
        return_value=moodle_reply,
    ) as mock_call:
        results = transport.push(_payload())

    fn, params = mock_call.call_args.args[2], mock_call.call_args.args[3]
    assert fn == "local_examcraft_set_quiz_feedback"
    assert params["quizid"] == 99
    assert params["students"][0]["useridentifier"] == "a@x.com"
    assert params["students"][0]["questions"][0]["commentformat"] == 1  # HTML
    assert results["a@x.com"].status == "ok"
    assert results["a@x.com"].graded == 1


def test_plugin_transport_marks_all_error_on_ws_failure():
    from services.moodle_feedback.ws_client import MoodleWsError

    transport = PluginFeedbackTransport(base_url="https://m", token="tok")
    with patch(
        "services.moodle_feedback.transports.call_moodle",
        side_effect=MoodleWsError("down"),
    ):
        results = transport.push(_payload())
    assert results["a@x.com"].status == "error"


def _two_student_payload():
    return FeedbackPayload(
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


def test_plugin_backfills_students_missing_from_reply():
    """A student the plugin silently drops is marked error, not lost."""
    transport = PluginFeedbackTransport(base_url="https://m", token="tok")
    # reply covers only a@x.com; b@x.com is missing.
    reply = [{"useridentifier": "a@x.com", "status": "ok", "graded": 1}]
    with patch("services.moodle_feedback.transports.call_moodle", return_value=reply):
        results = transport.push(_two_student_payload())
    assert results["a@x.com"].status == "ok"
    assert results["b@x.com"].status == "error"
    assert results["b@x.com"].errors  # carries an explanatory message


def test_plugin_normalizes_unknown_status_to_error():
    """An unrecognised wire status must not slip past as a non-counted value."""
    transport = PluginFeedbackTransport(base_url="https://m", token="tok")
    reply = [{"useridentifier": "a@x.com", "status": "weird-new-status"}]
    with patch("services.moodle_feedback.transports.call_moodle", return_value=reply):
        results = transport.push(_payload())
    assert results["a@x.com"].status == "error"


def test_plugin_empty_questions_marked_partial_not_sent():
    """A student with no slot-mapped question is PARTIAL and not sent to the plugin."""
    transport = PluginFeedbackTransport(base_url="https://m", token="tok")
    payload = FeedbackPayload(
        quiz_id=99,
        students=[
            StudentFeedback(
                external_id="full@x.com",
                total_points_awarded=3.0,
                total_points_max=5.0,
                questions=[QuestionFeedback(slot=1, mark=3.0, comment="ok")],
            ),
            StudentFeedback(
                external_id="empty@x.com",
                total_points_awarded=0.0,
                total_points_max=5.0,
                questions=[],
            ),
        ],
    )
    reply = [{"useridentifier": "full@x.com", "status": "ok", "graded": 1}]
    with patch(
        "services.moodle_feedback.transports.call_moodle", return_value=reply
    ) as mock_call:
        results = transport.push(payload)

    sent_ids = {s["useridentifier"] for s in mock_call.call_args.args[3]["students"]}
    assert sent_ids == {"full@x.com"}  # empty student excluded from the WS call
    assert results["full@x.com"].status == "ok"
    assert results["empty@x.com"].status == "partial"
