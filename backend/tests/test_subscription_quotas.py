"""Subscription-Tier-Quota tests (TF-336 Subarea E).

Covers:

* ``services.auswertung_quotas`` helpers (driver gate, class-history
  gate, exam-monthly counter, submission-per-exam counter).
* The HTTP endpoints that wire the helpers in (CSV/API import, class
  stats, student stats) — they should respond with 402 + structured
  ``error_code`` rather than 4xx.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from io import BytesIO

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student, StudentClass
from models.submission import ImportJob
from services.auswertung_quotas import (
    assert_class_history_allowed,
    assert_driver_allowed,
    assert_exam_quota_for_import,
    assert_submission_quota_for_exam,
    get_limits,
)
from utils.auth_utils import get_current_user, get_current_active_user


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _make_institution(db: Session, *, slug: str, tier: str = "free") -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier=tier,
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db: Session, institution_id: int) -> User:
    user = User(
        email=f"u-{institution_id}@test.ch",
        first_name="U",
        last_name="X",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_exam(db: Session, institution_id: int) -> Exam:
    q1 = QuestionReview(
        question_text="Q?",
        question_type="single_choice",
        options=["A", "B"],
        correct_answer="A",
        difficulty="easy",
        topic="X",
        institution_id=institution_id,
    )
    q2 = QuestionReview(
        question_text="W?",
        question_type="true_false",
        correct_answer="wahr",
        difficulty="easy",
        topic="X",
        institution_id=institution_id,
    )
    db.add_all([q1, q2])
    db.flush()
    exam = Exam(
        title="Quota-Test",
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
            ExamQuestion(exam_id=exam.id, question_id=q1.id, position=1, points=4.0),
            ExamQuestion(exam_id=exam.id, question_id=q2.id, position=2, points=1.0),
        ]
    )
    db.flush()
    return exam


def _add_import_job(
    db: Session,
    *,
    institution_id: int,
    exam_id: int,
    status: str = "succeeded",
    when: datetime | None = None,
) -> ImportJob:
    when = when or datetime.now(timezone.utc)
    job = ImportJob(
        institution_id=institution_id,
        exam_id=exam_id,
        driver_name="moodle_csv",
        status=status,
        rows_processed=1,
        rows_failed=0,
        error_log=[],
        source_metadata={},
        triggered_by=None,
        started_at=when,
        finished_at=when,
        created_at=when,
        updated_at=when,
    )
    db.add(job)
    db.flush()
    return job


# ---------------------------------------------------------------------------
# Pure-helper tests
# ---------------------------------------------------------------------------


def test_get_limits_unknown_tier_falls_back_to_free() -> None:
    assert get_limits("nonsense").tier == "free"


def test_assert_driver_allowed_blocks_api_for_free(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qf-1", tier="free")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    test_db.refresh(user)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        assert_driver_allowed(user=user, driver_name="moodle_api")
    assert exc.value.status_code == 402
    assert exc.value.detail["error_code"] == "auswertung_driver_not_in_tier"


def test_assert_driver_allowed_allows_api_for_pro(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qf-2", tier="professional")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    test_db.refresh(user)

    # No exception expected.
    assert_driver_allowed(user=user, driver_name="moodle_api")


def test_assert_class_history_blocks_below_enterprise(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qf-3", tier="professional")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    test_db.refresh(user)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        assert_class_history_allowed(user)
    assert exc.value.status_code == 402
    assert exc.value.detail["error_code"] == (
        "auswertung_class_history_enterprise_only"
    )


def test_assert_class_history_allows_enterprise(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qf-4", tier="enterprise")
    user = _make_user(test_db, inst.id)
    test_db.commit()
    test_db.refresh(user)
    assert_class_history_allowed(user)


def test_exam_monthly_quota_counts_distinct_exams(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qf-5", tier="free")
    user = _make_user(test_db, inst.id)
    exam_a = _make_exam(test_db, inst.id)
    exam_b = _make_exam(test_db, inst.id)
    exam_c = _make_exam(test_db, inst.id)
    new_exam = _make_exam(test_db, inst.id)
    _add_import_job(test_db, institution_id=inst.id, exam_id=exam_a.id)
    _add_import_job(test_db, institution_id=inst.id, exam_id=exam_b.id)
    _add_import_job(test_db, institution_id=inst.id, exam_id=exam_c.id)
    test_db.commit()
    test_db.refresh(user)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        assert_exam_quota_for_import(db=test_db, user=user, exam_id=new_exam.id)
    assert exc.value.status_code == 402
    assert exc.value.detail["limit"] == 3
    assert exc.value.detail["used"] == 3


def test_exam_monthly_quota_allows_re_import_of_same_exam(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db, slug="qf-6", tier="free")
    user = _make_user(test_db, inst.id)
    exam_a = _make_exam(test_db, inst.id)
    exam_b = _make_exam(test_db, inst.id)
    exam_c = _make_exam(test_db, inst.id)
    _add_import_job(test_db, institution_id=inst.id, exam_id=exam_a.id)
    _add_import_job(test_db, institution_id=inst.id, exam_id=exam_b.id)
    _add_import_job(test_db, institution_id=inst.id, exam_id=exam_c.id)
    test_db.commit()
    test_db.refresh(user)

    # Re-importing exam_a should NOT raise even though we hit the limit.
    assert_exam_quota_for_import(db=test_db, user=user, exam_id=exam_a.id)


def test_exam_monthly_quota_ignores_jobs_outside_window(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db, slug="qf-7", tier="free")
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    new_exam = _make_exam(test_db, inst.id)
    # Old job from last month — should be excluded.
    last_month = (datetime.now(timezone.utc).replace(day=1)) - timedelta(days=15)
    _add_import_job(
        test_db,
        institution_id=inst.id,
        exam_id=exam.id,
        when=last_month,
    )
    test_db.commit()
    test_db.refresh(user)

    # No exception: 0 jobs in window.
    assert_exam_quota_for_import(db=test_db, user=user, exam_id=new_exam.id)


def test_submission_quota_blocks_when_limit_exceeded(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db, slug="qf-8", tier="starter")
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    test_db.refresh(user)

    from fastapi import HTTPException

    # Limit 50 for starter → 30 existing + 25 new = 55 > 50.
    students = []
    for i in range(30):
        student = Student(
            institution_id=inst.id, external_id=f"student-{i}@example.org"
        )
        students.append(student)
        test_db.add(student)
    test_db.flush()
    from models.submission import Submission

    for student in students:
        test_db.add(
            Submission(
                exam_id=exam.id,
                student_id=student.id,
                scoring_strategy="latest",
                grade_status="pending_review",
                total_points_max=5.0,
                total_points_awarded=0.0,
                percentage=0.0,
            )
        )
    test_db.flush()

    with pytest.raises(HTTPException) as exc:
        assert_submission_quota_for_exam(
            db=test_db, user=user, exam_id=exam.id, additional=25
        )
    assert exc.value.status_code == 402
    assert exc.value.detail["error_code"] == "auswertung_submission_quota_exceeded"


# ---------------------------------------------------------------------------
# API integration
# ---------------------------------------------------------------------------


_JSON_FIXTURE = json.dumps(
    [
        [
            {
                "vorname": "Anna",
                "nachname": "Beispiel",
                "e-mail-adresse": "anna@example.org",
                "begonnen": "2026-05-15 09:00:00",
                "beendet": "2026-05-15 09:30:00",
                "frage1": "Q?",
                "antwort1": "Bern",
                "frage2": "W?",
                "antwort2": "wahr",
            }
        ]
    ]
)


def _client(test_db: Session, user: User) -> TestClient:
    import api.submissions as submissions_module
    import api.student_classes as student_classes_module
    import api.students as students_module

    if submissions_module.router not in app.router.routes:
        app.include_router(submissions_module.router)
        app.include_router(submissions_module.exams_alias_router)
    if student_classes_module.router not in app.router.routes:
        app.include_router(student_classes_module.router)
    if students_module.router not in app.router.routes:
        app.include_router(students_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def test_import_returns_402_for_free_at_4th_exam(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qa-csv-quota", tier="free")
    user = _make_user(test_db, inst.id)
    # 3 import jobs already this month for 3 different exams.
    for i in range(3):
        old_exam = _make_exam(test_db, inst.id)
        _add_import_job(test_db, institution_id=inst.id, exam_id=old_exam.id)
    new_exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    resp = client.post(
        "/api/v1/submissions/import/commit",
        files={
            "file": (
                "k.json",
                BytesIO(_JSON_FIXTURE.encode("utf-8")),
                "application/json",
            )
        },
        data={"exam_id": str(new_exam.id), "driver_name": "moodle_json"},
    )
    assert resp.status_code == 402, resp.text
    body = resp.json()
    assert body["detail"]["error_code"] == ("auswertung_exam_monthly_quota_exceeded")


def test_api_driver_returns_402_for_free(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qa-api-quota", tier="free")
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        "/api/v1/submissions/import/api-preview",
        json={"exam_id": exam.id, "quiz_id": 42},
    )
    assert resp.status_code == 402
    assert resp.json()["detail"]["error_code"] == "auswertung_driver_not_in_tier"


def test_class_stats_returns_402_for_pro(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qa-class-stats", tier="professional")
    user = _make_user(test_db, inst.id)
    student_class = StudentClass(institution_id=inst.id, name="INF-23a")
    test_db.add(student_class)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.get(f"/api/v1/student-classes/{student_class.id}/stats")
    assert resp.status_code == 402
    assert resp.json()["detail"]["error_code"] == (
        "auswertung_class_history_enterprise_only"
    )


def test_student_stats_returns_402_for_starter(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="qa-student-stats", tier="starter")
    user = _make_user(test_db, inst.id)
    student = Student(institution_id=inst.id, external_id="anna@example.org")
    test_db.add(student)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.get(f"/api/v1/students/{student.id}/stats")
    assert resp.status_code == 402
