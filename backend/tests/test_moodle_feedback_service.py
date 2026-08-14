"""TF-435: MoodleFeedbackPushService orchestration."""

from unittest.mock import patch

import pytest

from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview, QuestionReviewVisibility
from models.student import Student
from models.submission import (
    Attempt,
    AttemptAnswer,
    Grade,
    MoodleConnection,
    MoodleFeedbackPushJob,
    Submission,
)
from enums import FeedbackTransportName, StudentPushStatus
from services.moodle_feedback.service import MoodleFeedbackPushService
from services.moodle_feedback.transports import StudentResult
from services.moodle_feedback.ws_client import MoodleWsError
from utils.secret_encryption import encrypt_secret, reset_cache_for_tests


@pytest.fixture(autouse=True)
def _crypto_env(monkeypatch):
    """Provide a deterministic Fernet key (CI sets neither key by default)."""
    monkeypatch.delenv("MOODLE_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key-for-tests")
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


def _qr(db):
    # TF-642: no institution_id here (this helper isn't tenant-scoped), so
    # visibility must be PRIVATE — the default INSTITUTION would trip
    # ck_question_reviews_institution_visibility_requires_institution.
    qr = QuestionReview(
        question_text="?",
        question_type="single_choice",
        difficulty="easy",
        topic="x",
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    db.add(qr)
    db.flush()
    return qr.id


@pytest.fixture
def exam_with_reviewed_submission(test_db, test_institution):
    exam = Exam(institution_id=test_institution.id, title="Testprüfung")
    test_db.add(exam)
    test_db.flush()

    q1 = ExamQuestion(
        exam_id=exam.id,
        question_id=_qr(test_db),
        position=1,
        points=5.0,
        external_refs={"moodle_slot": 1, "moodle_quiz_id": 4242},
    )
    q2 = ExamQuestion(
        exam_id=exam.id,
        question_id=_qr(test_db),
        position=2,
        points=3.0,
        external_refs={"moodle_slot": 2, "moodle_quiz_id": 4242},
    )
    test_db.add_all([q1, q2])
    test_db.flush()

    student = Student(
        institution_id=test_institution.id,
        external_id="stud1@example.com",
        display_name="Stud One",
    )
    test_db.add(student)
    test_db.flush()

    sub = Submission(
        exam_id=exam.id,
        student_id=student.id,
        total_points_awarded=4.0,
        total_points_max=8.0,
        percentage=50.0,
        grade_status="fully_reviewed",
    )
    test_db.add(sub)
    test_db.flush()

    att = Attempt(
        submission_id=sub.id,
        institution_id=test_institution.id,
        attempt_number=1,
        source="moodle_json",
    )
    test_db.add(att)
    test_db.flush()
    sub.graded_attempt_id = att.id

    for q, pts, rnote in [(q1, 3.0, "ok"), (q2, 1.0, "ok2")]:
        ans = AttemptAnswer(attempt_id=att.id, exam_question_id=q.id, given_answer="x")
        test_db.add(ans)
        test_db.flush()
        test_db.add(
            Grade(
                attempt_answer_id=ans.id,
                points_awarded=pts,
                points_max=q.points,
                status="approved",
                reviewer_note=rnote,
            )
        )
    test_db.flush()
    return exam


def test_service_runs_and_aggregates(
    test_db, test_institution, exam_with_reviewed_submission
):
    test_db.add(
        MoodleConnection(
            institution_id=test_institution.id,
            base_url="https://m",
            token_encrypted=encrypt_secret("tok"),
        )
    )
    job = MoodleFeedbackPushJob(
        institution_id=test_institution.id,
        exam_id=exam_with_reviewed_submission.id,
    )
    test_db.add(job)
    test_db.flush()

    fake_results = {
        "stud1@example.com": StudentResult(
            external_id="stud1@example.com",
            status=StudentPushStatus.OK,
            graded=2,
        )
    }
    with patch("services.moodle_feedback.service.select_transport") as sel:
        sel.return_value.name = FeedbackTransportName.PLUGIN
        sel.return_value.push.return_value = fake_results
        MoodleFeedbackPushService(test_db).run(job_id=job.id)

    test_db.refresh(job)
    assert job.status == "completed"
    assert job.transport == "plugin"
    assert job.students_pushed == 1
    assert job.students_failed == 0


def test_service_aggregates_status_mix(
    test_db, test_institution, exam_with_reviewed_submission
):
    """Every per-student status lands in exactly one counter; non-ok logged."""
    test_db.add(
        MoodleConnection(
            institution_id=test_institution.id,
            base_url="https://m",
            token_encrypted=encrypt_secret("tok"),
        )
    )
    job = MoodleFeedbackPushJob(
        institution_id=test_institution.id,
        exam_id=exam_with_reviewed_submission.id,
    )
    test_db.add(job)
    test_db.flush()

    fake_results = {
        "ok@x.com": StudentResult(external_id="ok@x.com", status=StudentPushStatus.OK),
        "nf@x.com": StudentResult(
            external_id="nf@x.com", status=StudentPushStatus.NOT_FOUND
        ),
        "err@x.com": StudentResult(
            external_id="err@x.com", status=StudentPushStatus.ERROR, errors=["boom"]
        ),
        "part@x.com": StudentResult(
            external_id="part@x.com", status=StudentPushStatus.PARTIAL
        ),
    }
    with patch("services.moodle_feedback.service.select_transport") as sel:
        sel.return_value.name = FeedbackTransportName.GRADEBOOK
        sel.return_value.push.return_value = fake_results
        MoodleFeedbackPushService(test_db).run(job_id=job.id)

    test_db.refresh(job)
    assert job.status == "completed"
    assert job.students_pushed == 1
    assert job.students_skipped == 1  # not_found
    assert job.students_failed == 2  # error + partial
    logged = {e.get("external_id") for e in job.error_log if "external_id" in e}
    assert logged == {"nf@x.com", "err@x.com", "part@x.com"}


def test_service_completed_with_zero_students(test_db, test_institution):
    """No fully-reviewed submissions → completed, total 0, visible info note."""
    test_db.add(
        MoodleConnection(
            institution_id=test_institution.id,
            base_url="https://m",
            token_encrypted=encrypt_secret("tok"),
        )
    )
    exam = Exam(institution_id=test_institution.id, title="Leer")
    test_db.add(exam)
    test_db.flush()
    test_db.add(
        ExamQuestion(
            exam_id=exam.id,
            question_id=_qr(test_db),
            position=1,
            points=5.0,
            external_refs={"moodle_slot": 1, "moodle_quiz_id": 99},
        )
    )
    job = MoodleFeedbackPushJob(institution_id=test_institution.id, exam_id=exam.id)
    test_db.add(job)
    test_db.flush()

    with patch("services.moodle_feedback.service.select_transport") as sel:
        sel.return_value.name = FeedbackTransportName.GRADEBOOK
        sel.return_value.push.return_value = {}
        MoodleFeedbackPushService(test_db).run(job_id=job.id)

    test_db.refresh(job)
    assert job.status == "completed"
    assert job.students_total == 0
    assert any(e.get("scope") == "info" for e in job.error_log)


def test_service_marks_failed_without_quiz_id(test_db, test_institution):
    test_db.add(
        MoodleConnection(
            institution_id=test_institution.id,
            base_url="https://m",
            token_encrypted=encrypt_secret("tok"),
        )
    )
    exam = Exam(institution_id=test_institution.id, title="Ohne")
    test_db.add(exam)
    test_db.flush()
    job = MoodleFeedbackPushJob(institution_id=test_institution.id, exam_id=exam.id)
    test_db.add(job)
    test_db.flush()
    MoodleFeedbackPushService(test_db).run(job_id=job.id)
    test_db.refresh(job)
    assert job.status == "failed"
    # MissingQuizIdError is classified as a config-scope failure, not a generic one.
    assert job.error_log[0]["scope"] == "config"


def test_service_classifies_probe_failure_as_connection(
    test_db, test_institution, exam_with_reviewed_submission
):
    """A probe/connection error fails the job with scope=connection, not job."""
    test_db.add(
        MoodleConnection(
            institution_id=test_institution.id,
            base_url="https://m",
            token_encrypted=encrypt_secret("tok"),
        )
    )
    job = MoodleFeedbackPushJob(
        institution_id=test_institution.id,
        exam_id=exam_with_reviewed_submission.id,
    )
    test_db.add(job)
    test_db.flush()

    with patch(
        "services.moodle_feedback.service.select_transport",
        side_effect=MoodleWsError("Token ungültig"),
    ):
        MoodleFeedbackPushService(test_db).run(job_id=job.id)

    test_db.refresh(job)
    assert job.status == "failed"
    assert job.error_log[0]["scope"] == "connection"


def test_service_idempotent_skips_non_queued_job(test_db, test_institution):
    """acks_late redelivery must not re-run a job already past QUEUED."""
    exam = Exam(institution_id=test_institution.id, title="Done")
    test_db.add(exam)
    test_db.flush()
    job = MoodleFeedbackPushJob(
        institution_id=test_institution.id,
        exam_id=exam.id,
        status="completed",
        transport="plugin",
        students_total=1,
        students_pushed=1,
    )
    test_db.add(job)
    test_db.flush()

    with patch("services.moodle_feedback.service.select_transport") as sel:
        MoodleFeedbackPushService(test_db).run(job_id=job.id)
        sel.assert_not_called()  # no second push fired

    test_db.refresh(job)
    assert job.status == "completed"
    assert job.students_pushed == 1
