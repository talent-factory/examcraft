"""TF-435: feedback payload builder."""

import pytest

from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview, QuestionReviewVisibility
from models.student import Student
from models.submission import Attempt, AttemptAnswer, Grade, Submission
from services.moodle_feedback.payload import (
    MissingQuizIdError,
    QuestionFeedback,
    StudentFeedback,
    build_feedback_payload,
)


def test_question_feedback_rejects_illegal_values():
    with pytest.raises(ValueError):
        QuestionFeedback(slot=0, mark=1.0, comment="")  # slot is 1-based
    with pytest.raises(ValueError):
        QuestionFeedback(slot=1, mark=-1.0, comment="")  # negative mark


def test_student_feedback_rejects_awarded_over_max():
    with pytest.raises(ValueError):
        StudentFeedback(
            external_id="x@y.z", total_points_awarded=6.0, total_points_max=5.0
        )
    with pytest.raises(ValueError):
        StudentFeedback(
            external_id="x@y.z", total_points_awarded=-1.0, total_points_max=5.0
        )


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
    q3 = ExamQuestion(
        exam_id=exam.id,
        question_id=_qr(test_db),
        position=3,
        points=2.0,
        external_refs={},  # kein slot
    )
    test_db.add_all([q1, q2, q3])
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
        total_points_max=10.0,
        percentage=40.0,
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

    for q, pts, rnote, rat in [
        (q1, 3.0, "Gut begründet.", None),
        (q2, 1.0, None, "Teilweise korrekt (KI)."),
        (q3, 0.0, "egal", None),
    ]:
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
                llm_rationale=rat,
            )
        )
    test_db.flush()
    return exam


def test_payload_prefers_reviewer_note_then_llm_rationale(
    test_db, exam_with_reviewed_submission
):
    """reviewer_note gewinnt; sonst llm_rationale; Slot aus external_refs."""
    payload = build_feedback_payload(test_db, exam_with_reviewed_submission)

    assert payload.quiz_id == 4242
    assert len(payload.students) == 1
    student = payload.students[0]
    assert student.external_id == "stud1@example.com"
    by_slot = {q.slot: q for q in student.questions}
    assert by_slot[1].comment == "Gut begründet."  # reviewer_note
    assert by_slot[1].mark == 3.0
    assert by_slot[2].comment == "Teilweise korrekt (KI)."  # llm_rationale-Fallback
    # Frage ohne moodle_slot (q3) taucht als Warnung auf, nicht in questions
    assert 3 not in {q.slot for q in student.questions}
    assert any("kein moodle_slot" in w.lower() for w in payload.warnings)


def test_payload_empty_comment_when_both_sources_blank(test_db, test_institution):
    """reviewer_note and llm_rationale both blank → comment '', question kept."""
    exam = Exam(institution_id=test_institution.id, title="Blank")
    test_db.add(exam)
    test_db.flush()
    q = ExamQuestion(
        exam_id=exam.id,
        question_id=_qr(test_db),
        position=1,
        points=5.0,
        external_refs={"moodle_slot": 1, "moodle_quiz_id": 4242},
    )
    test_db.add(q)
    test_db.flush()
    student = Student(
        institution_id=test_institution.id,
        external_id="blank@example.com",
        display_name="Blank",
    )
    test_db.add(student)
    test_db.flush()
    sub = Submission(
        exam_id=exam.id,
        student_id=student.id,
        total_points_awarded=2.0,
        total_points_max=5.0,
        percentage=40.0,
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
    ans = AttemptAnswer(attempt_id=att.id, exam_question_id=q.id, given_answer="x")
    test_db.add(ans)
    test_db.flush()
    test_db.add(
        Grade(
            attempt_answer_id=ans.id,
            points_awarded=2.0,
            points_max=5.0,
            status="approved",
            reviewer_note=None,
            llm_rationale="   ",  # whitespace-only also collapses to ""
        )
    )
    test_db.flush()

    payload = build_feedback_payload(test_db, exam)
    student_fb = payload.students[0]
    by_slot = {q.slot: q for q in student_fb.questions}
    assert 1 in by_slot  # question still present despite empty comment
    assert by_slot[1].comment == ""


def test_payload_raises_without_quiz_id(test_db, test_institution):
    exam = Exam(institution_id=test_institution.id, title="Ohne Moodle")
    test_db.add(exam)
    test_db.flush()
    with pytest.raises(MissingQuizIdError):
        build_feedback_payload(test_db, exam)
