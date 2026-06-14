"""Tests for auto-class-assignment during import (TF-336 Subarea A).

Verifies that:

* the JSON driver populates ``StudentRef.class_hint`` from the
  ``klasse`` / ``class`` key,
* ``ImportService`` materialises a ``StudentClass`` and a
  ``StudentClassMembership`` per non-empty hint,
* re-imports stay idempotent (no duplicate classes or memberships),
* a pre-existing class with the same name is reused rather than
  duplicated.

The JSON driver maps answers by question text, so each student row carries
the exam's question texts verbatim (``frageN``) alongside the answers
(``antwortN``); see ``mem:project_tf423_progress``.
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy.orm import Session

from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student, StudentClass, StudentClassMembership
from services.import_drivers.moodle_json_driver import MoodleJsonDriver
from services.import_service import ImportService


# Question texts mirror ``_make_exam`` exactly so the driver's exact-match
# stage resolves each ``frageN`` to a unique exam question.
_Q_MC = "Hauptstadt der Schweiz?"
_Q_TF = "Bern ist die Hauptstadt der Schweiz."


def _student(vorname, nachname, email, klasse, mc_answer, tf_answer, *, key="klasse"):
    row = {
        "vorname": vorname,
        "nachname": nachname,
        "e-mail-adresse": email,
        "begonnen": "2026-05-15 09:00:00",
        "beendet": "2026-05-15 09:30:00",
        "frage1": _Q_MC,
        "antwort1": mc_answer,
        "frage2": _Q_TF,
        "antwort2": tf_answer,
    }
    if klasse is not None:
        row[key] = klasse
    return row


def _json_source(students) -> bytes:
    """Serialise like the Moodle plugin export: ``[[ {student}, ... ]]``."""
    return json.dumps([students]).encode("utf-8")


_JSON_WITH_CLASS = _json_source(
    [
        _student("Anna", "Beispiel", "anna@example.org", "INF-23a", "Bern", "wahr"),
        _student("Bruno", "Muster", "bruno@example.org", "INF-23b", "Zürich", "falsch"),
        _student("Cora", "Test", "cora@example.org", "INF-23a", "Bern", "wahr"),
    ]
)


def _make_institution(db: Session, slug: str = "tf336-classimport") -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db: Session, institution_id: int) -> User:
    user = User(
        email="lehrperson@test.ch",
        first_name="Test",
        last_name="Lehrperson",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_exam(db: Session, institution_id: int) -> Exam:
    mc_q = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        options=["A) Zürich", "B) Bern"],
        correct_answer="Bern",
        difficulty="easy",
        topic="Geo",
        institution_id=institution_id,
    )
    tf_q = QuestionReview(
        question_text="Bern ist die Hauptstadt der Schweiz.",
        question_type="true_false",
        correct_answer="wahr",
        difficulty="easy",
        topic="Geo",
        institution_id=institution_id,
    )
    db.add_all([mc_q, tf_q])
    db.flush()

    exam = Exam(
        title="Class Import Test",
        course="TF-336",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=5.0,
        status="finalized",
        language="de",
        institution_id=institution_id,
    )
    db.add(exam)
    db.flush()
    db.add_all(
        [
            ExamQuestion(exam_id=exam.id, question_id=mc_q.id, position=1, points=4.0),
            ExamQuestion(exam_id=exam.id, question_id=tf_q.id, position=2, points=1.0),
        ]
    )
    db.flush()
    return exam


def _seed_import(test_db: Session, exam: Exam, user: User):
    """Run the import pipeline directly (worker path).

    The commit endpoint only enqueues now (TF-412); these tests exercise the
    auto-class-assignment that happens inside ``ImportService.commit``, so they
    invoke it directly against ``test_db`` exactly as the Celery worker would.
    """
    return ImportService(test_db).commit(
        exam=exam,
        driver_name="moodle_json",
        source=_JSON_WITH_CLASS,
        triggered_by=user.id,
    )


# ---------------------------------------------------------------------------
# Driver — class-hint detection
# ---------------------------------------------------------------------------


def test_json_driver_extracts_class_hint(test_db: Session) -> None:
    inst = _make_institution(test_db)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    payload = MoodleJsonDriver().parse(_JSON_WITH_CLASS, exam=exam)
    by_id = {s.external_id: s for s in payload.students}
    assert by_id["anna@example.org"].class_hint == "INF-23a"
    assert by_id["bruno@example.org"].class_hint == "INF-23b"
    assert by_id["cora@example.org"].class_hint == "INF-23a"


def test_json_driver_accepts_english_class_alias(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-classimport-en")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    source = _json_source(
        [
            _student(
                "Anna",
                "Sample",
                "anna@example.org",
                "INF-23a",
                "Bern",
                "wahr",
                key="class",
            )
        ]
    )
    payload = MoodleJsonDriver().parse(source, exam=exam)
    by_id = {s.external_id: s for s in payload.students}
    assert by_id["anna@example.org"].class_hint == "INF-23a"


def test_json_driver_blank_class_is_none(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-classimport-blank")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    source = _json_source(
        [_student("Anna", "Beispiel", "anna@example.org", "   ", "Bern", "wahr")]
    )
    payload = MoodleJsonDriver().parse(source, exam=exam)
    assert payload.students[0].class_hint is None


# ---------------------------------------------------------------------------
# ImportService — auto-assignment
# ---------------------------------------------------------------------------


def test_commit_creates_classes_and_memberships(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    job = _seed_import(test_db, exam, user)
    assert job.status == "succeeded"

    classes = (
        test_db.query(StudentClass)
        .filter(StudentClass.institution_id == inst.id)
        .order_by(StudentClass.name)
        .all()
    )
    assert {cls.name for cls in classes} == {"INF-23a", "INF-23b"}

    by_name = {cls.name: cls for cls in classes}
    a_members = (
        test_db.query(Student)
        .join(
            StudentClassMembership,
            StudentClassMembership.student_id == Student.id,
        )
        .filter(StudentClassMembership.class_id == by_name["INF-23a"].id)
        .all()
    )
    assert {s.external_id for s in a_members} == {
        "anna@example.org",
        "cora@example.org",
    }


def test_commit_idempotent_on_re_import(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-classimport-idempotent")
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    for _ in range(2):
        job = _seed_import(test_db, exam, user)
        assert job.status == "succeeded"

    classes = (
        test_db.query(StudentClass).filter(StudentClass.institution_id == inst.id).all()
    )
    assert len(classes) == 2  # No duplicates after re-import.

    memberships = (
        test_db.query(StudentClassMembership)
        .join(StudentClass, StudentClassMembership.class_id == StudentClass.id)
        .filter(StudentClass.institution_id == inst.id)
        .all()
    )
    # Three students total, each in exactly one class.
    assert len(memberships) == 3


def test_commit_reuses_pre_existing_class(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="tf336-classimport-reuse")
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    pre_existing = StudentClass(institution_id=inst.id, name="INF-23a")
    test_db.add(pre_existing)
    test_db.commit()
    pre_existing_id = pre_existing.id

    job = _seed_import(test_db, exam, user)
    assert job.status == "succeeded"

    classes = (
        test_db.query(StudentClass)
        .filter(
            StudentClass.institution_id == inst.id,
            StudentClass.name == "INF-23a",
        )
        .all()
    )
    assert len(classes) == 1
    assert classes[0].id == pre_existing_id  # Reused, not replaced.
