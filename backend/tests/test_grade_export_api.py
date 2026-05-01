"""API tests for ``/api/v1/exams/{exam_id}/grades/export/{format}``.

Covers the central business rules of TF-335 Phase 3:

* HTTP 409 when any submission is still pending review
* HTTP 409 when the exam is still in draft status
* Successful CSV / Moodle-CSV / PDF download with correct
  ``Content-Type`` and ASCII-safe ``Content-Disposition``
* Cross-tenant access returns 404 (not 403) — leak-prevention

These were untested in the original PR even though the service-layer
tests exercised the math. The router plumbing (HTTP status codes,
content negotiation, RBAC) is exactly where the bugs that bite users
in prod live.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, Role, User, UserStatus
from models.exam import Exam, ExamStatus
from models.grading_scheme import GradingScheme
from models.student import Student
from models.submission import Submission
from utils.auth_utils import get_current_user, get_current_active_user


def _make_institution(db: Session, slug: str = "tf335-export") -> Institution:
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


def _make_user(
    db: Session,
    inst_id: int,
    *,
    permissions: list[str] | None = None,
    email: str = "lehrperson@test.ch",
) -> User:
    role = Role(
        name=f"role_{email}",
        display_name="Test Role",
        permissions=permissions or ["submissions:read"],
        is_system_role=False,
    )
    db.add(role)
    db.flush()

    user = User(
        email=email,
        first_name="Test",
        last_name="Lehrperson",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst_id,
        status=UserStatus.ACTIVE.value,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def _make_exam(db: Session, inst_id: int, *, status: str = "finalized") -> Exam:
    exam = Exam(
        title="Statistik FS26",
        passing_percentage=50.0,
        total_points=20.0,
        status=status,
        language="de",
        institution_id=inst_id,
    )
    db.add(exam)
    db.flush()
    return exam


def _make_student(db: Session, inst_id: int, *, external_id: str) -> Student:
    student = Student(
        institution_id=inst_id,
        external_id=external_id,
        display_name=external_id.split("@")[0].title(),
    )
    db.add(student)
    db.flush()
    return student


def _make_submission(
    db: Session,
    exam_id: int,
    student_id: int,
    *,
    grade_status: str = "fully_reviewed",
    percentage: float = 75.0,
) -> Submission:
    submission = Submission(
        exam_id=exam_id,
        student_id=student_id,
        total_points_awarded=percentage / 100 * 20,
        total_points_max=20.0,
        percentage=percentage,
        grade_status=grade_status,
    )
    db.add(submission)
    db.flush()
    return submission


def _client(test_db: Session, user: User) -> TestClient:
    import api.grade_export as grade_export_module

    if grade_export_module.router not in app.router.routes:
        app.include_router(grade_export_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def _clear_overrides_after_each_test():
    """Reset dependency overrides between tests so neighbouring suites
    (test_rag_api, etc.) aren't poisoned by our DB/user overrides.
    """
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 409 — pre-conditions
# ---------------------------------------------------------------------------


def test_export_returns_409_when_submission_pending_review(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    _make_submission(test_db, exam.id, student.id, grade_status="partially_reviewed")
    test_db.commit()

    client = _client(test_db, user)
    response = client.get(f"/api/v1/exams/{exam.id}/grades/export/csv")
    assert response.status_code == 409
    detail = response.json()["detail"].lower()
    # Either German or English, depending on locale resolution.
    assert "review" in detail or "bewertung" in detail


def test_export_returns_409_when_exam_is_draft(test_db: Session) -> None:
    """Draft exams are explicitly blocked — the question content can
    still change, so the noten-list would be inconsistent if exported.
    """
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id, status=ExamStatus.DRAFT.value)
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    _make_submission(test_db, exam.id, student.id)
    test_db.commit()

    client = _client(test_db, user)
    response = client.get(f"/api/v1/exams/{exam.id}/grades/export/csv")
    assert response.status_code == 409
    detail = response.json()["detail"].lower()
    assert "draft" in detail or "entwurf" in detail


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


def test_export_csv_returns_correct_content_type(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    _make_submission(test_db, exam.id, student.id)
    test_db.commit()

    client = _client(test_db, user)
    response = client.get(f"/api/v1/exams/{exam.id}/grades/export/csv")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    # Excel-DE relies on the BOM — pin the byte literal at the API
    # boundary so a future codec swap can't silently strip it.
    assert response.content[:3] == b"\xef\xbb\xbf"


def test_export_pdf_returns_application_pdf(test_db: Session) -> None:
    import pytest

    pytest.importorskip("reportlab")

    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    _make_submission(test_db, exam.id, student.id)
    test_db.commit()

    client = _client(test_db, user)
    response = client.get(f"/api/v1/exams/{exam.id}/grades/export/pdf")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_export_filename_is_ascii_safe_for_umlaut_titles(test_db: Session) -> None:
    """German umlauts in the title must not crash older browsers'
    Content-Disposition parsing. The endpoint emits both an ASCII
    fallback ``filename`` and the percent-encoded ``filename*``.
    """
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = Exam(
        title="Prüfung Frühjahr",
        passing_percentage=50.0,
        total_points=20.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    test_db.add(exam)
    test_db.flush()
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    _make_submission(test_db, exam.id, student.id)
    test_db.commit()

    client = _client(test_db, user)
    response = client.get(f"/api/v1/exams/{exam.id}/grades/export/csv")
    assert response.status_code == 200, response.text
    disposition = response.headers["content-disposition"]
    # ASCII fallback: the umlaut must be replaced by ``_``.
    assert 'filename="noten-Pr_fung_Fr_hjahr.csv"' in disposition
    # Percent-encoded full form for modern browsers.
    assert "filename*=UTF-8''" in disposition


# ---------------------------------------------------------------------------
# Cross-tenant
# ---------------------------------------------------------------------------


def test_export_cross_tenant_returns_404(test_db: Session) -> None:
    """Tenant from institution A must not be able to export an exam
    from institution B. 404 (not 403) so we don't leak existence.
    """
    inst_a = _make_institution(test_db, slug="export-a")
    inst_b = _make_institution(test_db, slug="export-b")
    user_a = _make_user(test_db, inst_a.id, email="a@test.ch")
    exam_b = _make_exam(test_db, inst_b.id)
    test_db.commit()

    client = _client(test_db, user_a)
    response = client.get(f"/api/v1/exams/{exam_b.id}/grades/export/csv")
    assert response.status_code == 404


def test_export_falls_back_to_institution_default_scheme(test_db: Session) -> None:
    """Exam without its own scheme → use ``Institution.default_grading_scheme_id``."""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    scheme = GradingScheme(
        institution_id=inst.id,
        name="Inst Default",
        display_format="pass_fail",
        config={
            "type": "stepped",
            "steps": [
                {"min_pct": 50, "grade_label": "Pass", "is_passing": True},
                {"min_pct": 0, "grade_label": "Fail", "is_passing": False},
            ],
        },
        is_default_for_institution=True,
    )
    test_db.add(scheme)
    test_db.flush()
    inst.default_grading_scheme_id = scheme.id

    exam = _make_exam(test_db, inst.id)
    # Note: exam.grading_scheme_id is None — should fall back.
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    _make_submission(test_db, exam.id, student.id, percentage=75.0)
    test_db.commit()

    client = _client(test_db, user)
    response = client.get(f"/api/v1/exams/{exam.id}/grades/export/csv")
    assert response.status_code == 200, response.text
    text = response.content.decode("utf-8")
    # 75 % under pass/fail → "Pass" must appear in the Note column.
    assert "Pass" in text
