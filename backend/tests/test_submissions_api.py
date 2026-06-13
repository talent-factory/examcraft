"""API tests for /api/v1/submissions/*.

Covers preview, commit, job polling, list + detail, RBAC, and
multi-tenancy.
"""

from __future__ import annotations

import base64
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.submission import ImportJob
from utils.auth_utils import get_current_user, get_current_active_user


# ---------------------------------------------------------------------------
# Fixtures-Helper (ohne Pytest-Fixture, damit pro Test-Setup steuerbar)
# ---------------------------------------------------------------------------


def _make_institution(db: Session, slug: str = "tf333-api") -> Institution:
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
    institution_id: int,
    *,
    email: str = "lehrperson@test.ch",
    is_superuser: bool = True,
) -> User:
    user = User(
        email=email,
        first_name="Test",
        last_name="Lehrperson",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,  # Skip Rollen-Setup im Test
    )
    db.add(user)
    db.flush()
    return user


def _make_exam(db: Session, institution_id: int) -> Exam:
    mc_q = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        options=["A) Zürich", "B) Bern", "C) Genf"],
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
        title="API Test",
        course="Test",
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
            ExamQuestion(
                exam_id=exam.id,
                question_id=mc_q.id,
                position=1,
                points=4.0,
            ),
            ExamQuestion(
                exam_id=exam.id,
                question_id=tf_q.id,
                position=2,
                points=1.0,
            ),
        ]
    )
    db.flush()
    return exam


def _client(test_db: Session, user: User) -> TestClient:
    """TestClient mit DB-Override + injiziertem User."""
    import api.submissions as submissions_module

    # Router registrieren, falls noch nicht durch lifespan geladen.
    if submissions_module.router not in app.router.routes:
        app.include_router(submissions_module.router)
        app.include_router(submissions_module.exams_alias_router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


_CSV_FIXTURE = (
    "Vorname;Nachname;E-Mail-Adresse;Begonnen am;Beendet;Antwort 1;Antwort 2\n"
    "Anna;Beispiel;anna@example.org;2026-05-15 09:00:00;"
    "2026-05-15 09:30:00;Bern;wahr\n"
    "Bruno;Muster;bruno@example.org;2026-05-15 09:00:00;"
    "2026-05-15 09:25:00;Zürich;falsch\n"
)


def _seed_import(
    test_db: Session,
    exam: Exam,
    *,
    source: str = _CSV_FIXTURE,
    triggered_by: int | None = None,
):
    """Run the import pipeline directly against the test session.

    The commit endpoint now only *enqueues* (TF-412), so the actual
    persist + grade happens in a Celery worker. Tests that assert on the
    imported submissions/grades seed them this way — the worker's own
    ``SessionLocal`` would not see the savepoint-isolated test data, so we
    invoke ``ImportService.commit`` against ``test_db`` exactly as the worker
    would against its own session.
    """
    from services.import_service import ImportService

    return ImportService(test_db).commit(
        exam=exam,
        driver_name="moodle_csv",
        source=source.encode("utf-8"),
        triggered_by=triggered_by,
    )


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


def test_preview_returns_payload_summary(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    response = client.post(
        "/api/v1/submissions/import/preview",
        files={
            "file": ("klasse.csv", BytesIO(_CSV_FIXTURE.encode("utf-8")), "text/csv")
        },
        data={"exam_id": str(exam.id), "driver_name": "moodle_csv"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["exam_id"] == exam.id
    assert body["student_count"] == 2
    assert body["attempt_count"] == 2
    assert {s["external_id"] for s in body["students"]} == {
        "anna@example.org",
        "bruno@example.org",
    }
    assert body["errors"] == []


def test_preview_rejects_empty_csv(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("empty.csv", BytesIO(b""), "text/csv")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 400
    assert "leer" in response.json()["detail"].lower()


def test_preview_rejects_missing_email_column(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    bad_csv = b"Vorname;Nachname;Antwort 1\nAnna;Beispiel;A\n"
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("bad.csv", BytesIO(bad_csv), "text/csv")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 400
    assert "external_id" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------


def test_commit_enqueues_task_and_returns_queued(test_db: Session) -> None:
    """Commit no longer grades inline (TF-412): it validates synchronously,
    pre-creates a ``queued`` ImportJob, hands the *raw* upload bytes (base64)
    to the Celery worker and returns 202 immediately — so the HTTP request can
    never hang on serial LLM grading."""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    with patch("api.submissions.import_submissions.apply_async") as apply_async:
        response = client.post(
            "/api/v1/submissions/import/commit",
            files={
                "file": (
                    "klasse.csv",
                    BytesIO(_CSV_FIXTURE.encode("utf-8")),
                    "text/csv",
                )
            },
            data={"exam_id": str(exam.id), "driver_name": "moodle_csv"},
        )

    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert job["rows_processed"] == 0
    assert job["rows_failed"] == 0

    apply_async.assert_called_once()
    enqueued = apply_async.call_args.kwargs["kwargs"]
    assert enqueued["exam_id"] == exam.id
    assert enqueued["driver_name"] == "moodle_csv"
    assert enqueued["import_job_id"] == job["id"]
    assert enqueued["triggered_by"] == user.id
    # The worker gets the exact original bytes, not a pre-decoded string.
    assert base64.b64decode(enqueued["source_b64"]) == _CSV_FIXTURE.encode("utf-8")

    # The queued job is immediately pollable while the worker runs.
    poll = client.get(f"/api/v1/submissions/import-jobs/{job['id']}")
    assert poll.status_code == 200
    assert poll.json()["status"] == "queued"


def test_commit_rejects_malformed_csv_before_enqueue(test_db: Session) -> None:
    """The 202-async design rests on validation staying *in front of* the
    enqueue: a malformed upload must be rejected (4xx) and NOTHING enqueued,
    so the worker never sees input it would only fail on. The ``assert_not_called``
    + zero-row assertions are the load-bearing guards against a refactor that
    moves the enqueue ahead of validation."""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    with patch("api.submissions.import_submissions.apply_async") as apply_async:
        response = client.post(
            "/api/v1/submissions/import/commit",
            files={"file": ("empty.csv", BytesIO(b""), "text/csv")},
            data={"exam_id": str(exam.id), "driver_name": "moodle_csv"},
        )

    assert response.status_code == 400, response.text
    apply_async.assert_not_called()
    assert test_db.query(ImportJob).filter(ImportJob.exam_id == exam.id).count() == 0


def test_commit_rejects_missing_email_column_before_enqueue(test_db: Session) -> None:
    """Second malformed-input branch (missing external-id column): same
    contract — 400, no task enqueued, no job row created."""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    bad_csv = b"Vorname;Nachname;Antwort 1\nAnna;Beispiel;A\n"
    with patch("api.submissions.import_submissions.apply_async") as apply_async:
        response = client.post(
            "/api/v1/submissions/import/commit",
            files={"file": ("bad.csv", BytesIO(bad_csv), "text/csv")},
            data={"exam_id": str(exam.id), "driver_name": "moodle_csv"},
        )

    assert response.status_code == 400, response.text
    apply_async.assert_not_called()
    assert test_db.query(ImportJob).filter(ImportJob.exam_id == exam.id).count() == 0


# ---------------------------------------------------------------------------
# Liste + Detail
# ---------------------------------------------------------------------------


def test_list_submissions_returns_imported(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    _seed_import(test_db, exam)

    response = client.get("/api/v1/submissions", params={"exam_id": exam.id})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["student_external_id"] for item in body["items"]} == {
        "anna@example.org",
        "bruno@example.org",
    }


def test_list_submissions_via_exam_alias(test_db: Session) -> None:
    """Spec-konformer Alias: GET /api/v1/exams/{exam_id}/submissions"""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    _seed_import(test_db, exam)

    alias = client.get(f"/api/v1/exams/{exam.id}/submissions")
    assert alias.status_code == 200
    assert alias.json()["total"] == 2


def test_submission_detail_includes_attempts_and_grades(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    _seed_import(test_db, exam)

    list_resp = client.get("/api/v1/submissions", params={"exam_id": exam.id})
    anna_id = next(
        item["id"]
        for item in list_resp.json()["items"]
        if item["student_external_id"] == "anna@example.org"
    )

    detail = client.get(f"/api/v1/submissions/{anna_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["total_points_awarded"] == 5.0
    assert body["total_points_max"] == 5.0
    assert body["percentage"] == 100.0
    assert len(body["attempts"]) == 1
    assert len(body["attempts"][0]["answers"]) == 2
    grades = [a["grade"] for a in body["attempts"][0]["answers"]]
    assert all(g["status"] == "proposed" for g in grades)
    assert all(g["is_correct"] is True for g in grades)


# ---------------------------------------------------------------------------
# Multi-Tenancy
# ---------------------------------------------------------------------------


def test_cannot_preview_exam_from_other_institution(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="inst-a")
    inst_b = _make_institution(test_db, slug="inst-b")
    user_a = _make_user(test_db, inst_a.id, email="a@test.ch")
    exam_b = _make_exam(test_db, inst_b.id)
    test_db.commit()

    client = _client(test_db, user_a)
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={
            "file": ("klasse.csv", BytesIO(_CSV_FIXTURE.encode("utf-8")), "text/csv")
        },
        data={"exam_id": str(exam_b.id)},
    )
    assert response.status_code == 404


def test_cannot_read_submission_from_other_institution(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="inst-aa")
    inst_b = _make_institution(test_db, slug="inst-bb")
    user_a = _make_user(test_db, inst_a.id, email="aa@test.ch")
    user_b = _make_user(test_db, inst_b.id, email="bb@test.ch")
    exam_b = _make_exam(test_db, inst_b.id)
    test_db.commit()

    # Import als User B (worker-Pfad direkt gegen test_db geseedet)
    client_b = _client(test_db, user_b)
    job = _seed_import(test_db, exam_b, triggered_by=user_b.id)
    list_b = client_b.get("/api/v1/submissions", params={"exam_id": exam_b.id})
    submission_id = list_b.json()["items"][0]["id"]
    job_id = job.id

    # User A darf weder Liste, Detail, noch Job sehen
    client_a = _client(test_db, user_a)
    assert (
        client_a.get("/api/v1/submissions", params={"exam_id": exam_b.id}).status_code
        == 404
    )
    assert client_a.get(f"/api/v1/submissions/{submission_id}").status_code == 404
    assert client_a.get(f"/api/v1/submissions/import-jobs/{job_id}").status_code == 404


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


def test_user_without_import_permission_gets_403(test_db: Session) -> None:
    """Reviewer-User (nur submissions:read) darf nicht importieren."""
    from models.auth import Role, UserRole

    inst = _make_institution(test_db, slug="rbac")
    # The role is seeded by ``seed_default_roles`` at app startup, so
    # in CI we have to reuse the existing row rather than insert a
    # second one (would crash on the unique-name index). The seeded
    # ``assistant`` role already has exactly ``submissions:read`` and
    # not import/grade — perfect for this test.
    reviewer_role = (
        test_db.query(Role).filter(Role.name == UserRole.ASSISTANT.value).first()
    )
    if reviewer_role is None:
        reviewer_role = Role(
            name=UserRole.ASSISTANT.value,
            display_name="Reviewer",
            description="Test reviewer",
            permissions=["submissions:read"],
            is_system_role=True,
        )
        test_db.add(reviewer_role)
        test_db.flush()
    # Lock the test invariant: reviewer must NOT have import permission.
    assert "submissions:import" not in (reviewer_role.permissions or [])

    user = User(
        email="reviewer@test.ch",
        first_name="Re",
        last_name="Viewer",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,  # NICHT Superuser → echter RBAC-Check
    )
    user.roles.append(reviewer_role)
    test_db.add(user)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/submissions/import/commit",
        files={
            "file": ("klasse.csv", BytesIO(_CSV_FIXTURE.encode("utf-8")), "text/csv")
        },
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 403


def test_dozent_with_import_permission_can_commit(test_db: Session) -> None:
    """Positive RBAC: a non-superuser with submissions:import succeeds.

    Without this every passing test bypasses the real RBAC chain via
    ``is_superuser=True``; a regression that broke the permission
    lookup would not fail any test."""
    from models.auth import Role, UserRole

    inst = _make_institution(test_db, slug="rbac-positive")
    # Reuse the seeded ``dozent`` role (see sibling RBAC test for why).
    # The seed already grants submissions:read/import/grade.
    dozent_role = test_db.query(Role).filter(Role.name == UserRole.DOZENT.value).first()
    if dozent_role is None:
        dozent_role = Role(
            name=UserRole.DOZENT.value,
            display_name="Dozent",
            description="Lehrperson",
            permissions=[
                "submissions:read",
                "submissions:import",
                "submissions:grade",
            ],
            is_system_role=True,
        )
        test_db.add(dozent_role)
        test_db.flush()
    assert "submissions:import" in (dozent_role.permissions or [])

    user = User(
        email="dozent@test.ch",
        first_name="Doz",
        last_name="Ent",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    user.roles.append(dozent_role)
    test_db.add(user)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    with patch("api.submissions.import_submissions.apply_async") as apply_async:
        response = client.post(
            "/api/v1/submissions/import/commit",
            files={
                "file": (
                    "klasse.csv",
                    BytesIO(_CSV_FIXTURE.encode("utf-8")),
                    "text/csv",
                )
            },
            data={"exam_id": str(exam.id)},
        )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    apply_async.assert_called_once()


def test_upload_too_large_returns_413(test_db: Session) -> None:
    """The 25 MB upload guard rejects oversized files before they hit
    the parser and the worker's RAM."""
    inst = _make_institution(test_db, slug="too-large")
    user = _make_user(test_db, inst.id, email="huge@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    # ~30 MB payload — comfortably above the 25 MB cap.
    line = b"a@test.ch,Bern\n"  # 15 bytes
    huge = b"E-Mail-Adresse,Antwort 1\n" + line * 2_100_000  # ~31.5 MB
    assert len(huge) > 25 * 1024 * 1024
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("huge.csv", BytesIO(huge), "text/csv")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 413


def test_extra_answer_columns_become_warnings_not_validation_error(
    test_db: Session,
) -> None:
    """Extra columns ⇒ warning, NOT 422.

    The driver maps answer columns by ``position`` to ``ExamQuestion``,
    so a CSV with more answer columns than questions silently drops the
    surplus and emits a warning. Validation (422 + structured issues)
    is reserved for *real* schema mismatches; see
    :func:`test_validation_error_surfaces_structured_issues_via_422`
    below for the actual 422 path.
    """
    inst = _make_institution(test_db, slug="val-issues")
    user = _make_user(test_db, inst.id, email="val@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    csv_extra_cols = (
        "E-Mail-Adresse;Antwort 1;Antwort 2;Antwort 3\n"
        "extra@test.ch;Bern;wahr;Antwort\n"
    )
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("ok.csv", BytesIO(csv_extra_cols.encode("utf-8")), "text/csv")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 200
    assert any("Spaltenanzahl" in w for w in response.json()["warnings"])


def test_validation_error_surfaces_structured_issues_via_422(
    test_db: Session,
) -> None:
    """422 from ImportValidationError must include the per-issue list.

    Triggers ImportValidationError directly (the only way without
    bypassing the driver's question-id filter) and asserts FastAPI
    emits ``detail.message`` + ``detail.issues``.
    """
    from unittest.mock import patch

    from services.import_service import ImportService, ImportValidationError

    inst = _make_institution(test_db, slug="val-422")
    user = _make_user(test_db, inst.id, email="val422@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    issues = [f"Attempt #{i}: ungültige exam_question_id {99 + i}" for i in range(3)]

    def _raise(self, payload, exam):
        raise ImportValidationError("3 Validierungs-Fehler", issues=issues)

    with patch.object(ImportService, "_validate_payload", _raise):
        response = client.post(
            "/api/v1/submissions/import/preview",
            files={
                "file": (
                    "ok.csv",
                    BytesIO(b"E-Mail-Adresse;Antwort 1\nextra@test.ch;Bern\n"),
                    "text/csv",
                )
            },
            data={"exam_id": str(exam.id)},
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "3 Validierungs-Fehler" in detail["message"]
    assert detail["issues"] == issues


# ---------------------------------------------------------------------------
# Pagination — list endpoint
# ---------------------------------------------------------------------------


def test_list_submissions_returns_pagination_metadata(test_db: Session) -> None:
    """Default pagination: limit=200, offset=0, total reflects all rows."""
    inst = _make_institution(test_db, slug="paging-default")
    user = _make_user(test_db, inst.id, email="paging-default@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    _seed_import(test_db, exam)

    resp = client.get("/api/v1/submissions", params={"exam_id": exam.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 200
    assert body["offset"] == 0
    assert body["total"] == 2


def test_list_submissions_respects_limit_and_offset(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="paging-custom")
    user = _make_user(test_db, inst.id, email="paging-custom@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    _seed_import(test_db, exam)

    resp = client.get(
        "/api/v1/submissions",
        params={"exam_id": exam.id, "limit": 1, "offset": 1},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert body["total"] == 2  # total ignores pagination
    assert len(body["items"]) == 1


def test_list_submissions_rejects_limit_above_cap(test_db: Session) -> None:
    """1000 hard cap defends the worker against accidental huge requests."""
    inst = _make_institution(test_db, slug="paging-cap")
    user = _make_user(test_db, inst.id, email="paging-cap@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    resp = client.get("/api/v1/submissions", params={"exam_id": exam.id, "limit": 5000})
    assert resp.status_code == 422  # Pydantic ge/le validation


# ---------------------------------------------------------------------------
# 500-with-job-id: failed import surfaces import_job_id in detail
# ---------------------------------------------------------------------------


def test_broker_failure_marks_job_failed_and_returns_503(test_db: Session) -> None:
    """If the import can't be enqueued (broker unreachable), the endpoint must
    mark the just-created job ``failed`` in place and return 503 with its id —
    so the client lands on a terminal, pollable state instead of a job stuck
    in ``queued`` forever (TF-412)."""
    inst = _make_institution(test_db, slug="broker-down")
    user = _make_user(test_db, inst.id, email="broker@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    with patch(
        "api.submissions.import_submissions.apply_async",
        side_effect=RuntimeError("broker unreachable"),
    ):
        response = client.post(
            "/api/v1/submissions/import/commit",
            files={
                "file": (
                    "klasse.csv",
                    BytesIO(_CSV_FIXTURE.encode("utf-8")),
                    "text/csv",
                )
            },
            data={"exam_id": str(exam.id)},
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["import_job_id"] is not None

    # Polling the job must work and show a terminal, failed state.
    poll = client.get(f"/api/v1/submissions/import-jobs/{detail['import_job_id']}")
    assert poll.status_code == 200
    job_body = poll.json()
    assert job_body["status"] == "failed"
    assert job_body["error_log"]


def test_enqueue_still_returns_503_when_failure_persist_also_fails() -> None:
    """H2: on a correlated broker+DB outage the failure-state commit itself
    raises. ``_enqueue_import`` must swallow that, attempt a rollback, and
    still raise the 503 with the pollable job id — never let the commit
    error escape as an unhandled 500 that buries the broker cause."""
    from api.submissions import _enqueue_import

    db = MagicMock()
    fake_job = MagicMock()
    fake_job.id = 4242

    with (
        patch("api.submissions.ImportService") as service_cls,
        patch(
            "api.submissions.import_submissions.apply_async",
            side_effect=RuntimeError("broker unreachable"),
        ),
    ):
        service_cls.return_value.create_queued_job.return_value = fake_job
        # The terminal-state persist (the only db.commit in _enqueue_import)
        # blows up too, simulating Postgres also being down.
        db.commit.side_effect = OperationalError("stmt", {}, Exception("db gone"))

        with pytest.raises(HTTPException) as excinfo:
            _enqueue_import(
                db=db,
                exam=MagicMock(),
                driver_name="moodle_csv",
                source_bytes=b"x;y\n1;2\n",
                triggered_by=1,
                source_metadata={},
            )

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.detail["import_job_id"] == 4242
    db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# error_log shape: end-to-end ImportRowErrorOut serialisation
# ---------------------------------------------------------------------------


def test_error_log_serialises_as_structured_list(test_db: Session) -> None:
    """ImportJob.error_log on the wire must be ``list[ImportRowErrorOut]``
    (frontend type) not ``list[dict]`` — so a row error has typed
    row_index/reason/step/details fields."""
    csv_with_bad_row = (
        "Vorname;Nachname;E-Mail-Adresse;Begonnen am;Beendet;Antwort 1;Antwort 2\n"
        # Row with empty email → Driver records ImportRowError
        ";Beispiel;;2026-05-15 09:00:00;2026-05-15 09:30:00;Bern;wahr\n"
        "Bruno;Muster;bruno@example.org;2026-05-15 09:00:00;"
        "2026-05-15 09:25:00;Bern;wahr\n"
    )

    inst = _make_institution(test_db, slug="error-log-shape")
    user = _make_user(test_db, inst.id, email="error-log@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    # The worker produces the partial import + structured error_log; we assert
    # the *wire* shape via the polling endpoint (_import_job_to_out).
    job = _seed_import(test_db, exam, source=csv_with_bad_row)
    assert job.status == "partial"

    resp = client.get(f"/api/v1/submissions/import-jobs/{job.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "partial"
    assert body["error_log"], "error_log must not be empty"
    entry = body["error_log"][0]
    # Strict-mode pydantic enforces these keys
    assert {"row_index", "reason", "step", "details"} <= set(entry.keys())
    assert isinstance(entry["row_index"], int)
    assert isinstance(entry["reason"], str)


def test_preview_returns_422_with_issues_when_validation_fails(
    test_db: Session, monkeypatch
) -> None:
    """422 detail must include both ``message`` and ``issues`` so the UI
    can render every offending row at once."""
    from services.import_service import ImportService, ImportValidationError

    inst = _make_institution(test_db, slug="preview-422")
    user = _make_user(test_db, inst.id, email="preview-422@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    def raise_validation(*args, **kwargs):
        raise ImportValidationError(
            "3 Validierungs-Fehler in Payload",
            issues=[
                "Attempt #0 (anna@test.ch): Frage 99 nicht in Prüfung",
                "Attempt #1 (bruno@test.ch): Frage 99 nicht in Prüfung",
                "Attempt #2 (carla@test.ch): Frage 88 nicht in Prüfung",
            ],
        )

    monkeypatch.setattr(ImportService, "preview", raise_validation)

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("ok.csv", BytesIO(_CSV_FIXTURE.encode("utf-8")), "text/csv")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "3 Validierungs-Fehler in Payload"
    assert len(detail["issues"]) == 3
    assert all("nicht in Prüfung" in issue for issue in detail["issues"])


def test_preview_returns_500_when_pipeline_crashes_unexpectedly(
    test_db: Session, monkeypatch
) -> None:
    """Unexpected crashes in preview must yield a 500 (not propagate to
    the worker)."""
    from services.import_service import ImportService

    inst = _make_institution(test_db, slug="preview-500")
    user = _make_user(test_db, inst.id, email="preview-500@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    def boom(*args, **kwargs):
        raise RuntimeError("synthetic preview crash")

    monkeypatch.setattr(ImportService, "preview", boom)

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("ok.csv", BytesIO(_CSV_FIXTURE.encode("utf-8")), "text/csv")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 500
