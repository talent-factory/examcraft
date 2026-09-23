"""API tests for /api/v1/submissions/*.

Covers preview, commit, job polling, list + detail, RBAC, and
multi-tenancy.
"""

from __future__ import annotations

import base64
import json
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
# Fixture helpers (not pytest fixtures, so each test can control its own setup)
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
        is_superuser=is_superuser,  # Skip role setup in the test
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
    """TestClient with DB override + injected user."""
    import api.submissions as submissions_module

    # Register the router if it hasn't been loaded via lifespan yet.
    if submissions_module.router not in app.router.routes:
        app.include_router(submissions_module.router)
        app.include_router(submissions_module.exams_alias_router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# Question texts mirror ``_make_exam`` so the JSON driver's exact-match
# stage resolves each ``frageN`` to a unique exam question (TF-423).
_Q1 = "Hauptstadt der Schweiz?"
_Q2 = "Bern ist die Hauptstadt der Schweiz."

_JSON_FIXTURE = json.dumps(
    [
        [
            {
                "vorname": "Anna",
                "nachname": "Beispiel",
                "e-mail-adresse": "anna@example.org",
                "begonnen": "2026-05-15 09:00:00",
                "beendet": "2026-05-15 09:30:00",
                "frage1": _Q1,
                "antwort1": "Bern",
                "frage2": _Q2,
                "antwort2": "wahr",
            },
            {
                "vorname": "Bruno",
                "nachname": "Muster",
                "e-mail-adresse": "bruno@example.org",
                "begonnen": "2026-05-15 09:00:00",
                "beendet": "2026-05-15 09:25:00",
                "frage1": _Q1,
                "antwort1": "Zürich",
                "frage2": _Q2,
                "antwort2": "falsch",
            },
        ]
    ]
)


def _seed_import(
    test_db: Session,
    exam: Exam,
    *,
    source: str = _JSON_FIXTURE,
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
        driver_name="moodle_json",
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
            "file": (
                "klasse.json",
                BytesIO(_JSON_FIXTURE.encode("utf-8")),
                "application/json",
            )
        },
        data={"exam_id": str(exam.id), "driver_name": "moodle_json"},
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
        files={"file": ("empty.json", BytesIO(b""), "application/json")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "submissions_import_file_empty"


def test_preview_rejects_json_without_question_texts(test_db: Session) -> None:
    """No ``frageN`` keys → no content to map answers by → hard 400.

    This is the JSON analogue of the legacy "missing external_id column"
    rejection: without the question texts the driver cannot map answers
    to exam questions at all.
    """
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    no_frage = json.dumps(
        [{"e-mail-adresse": "anna@example.org", "antwort1": "Bern"}]
    ).encode("utf-8")
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("bad.json", BytesIO(no_frage), "application/json")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "submissions_import_question_texts_missing"


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
                    "klasse.json",
                    BytesIO(_JSON_FIXTURE.encode("utf-8")),
                    "application/json",
                )
            },
            data={"exam_id": str(exam.id), "driver_name": "moodle_json"},
        )

    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert job["rows_processed"] == 0
    assert job["rows_failed"] == 0

    apply_async.assert_called_once()
    enqueued = apply_async.call_args.kwargs["kwargs"]
    assert enqueued["exam_id"] == exam.id
    assert enqueued["driver_name"] == "moodle_json"
    assert enqueued["import_job_id"] == job["id"]
    assert enqueued["triggered_by"] == user.id
    # The worker gets the exact original bytes, not a pre-decoded string.
    assert base64.b64decode(enqueued["source_b64"]) == _JSON_FIXTURE.encode("utf-8")

    # The queued job is immediately pollable while the worker runs.
    poll = client.get(f"/api/v1/submissions/import-jobs/{job['id']}")
    assert poll.status_code == 200
    assert poll.json()["status"] == "queued"


def test_list_import_jobs_scoped_to_exam(test_db: Session) -> None:
    """TF-428: the Auswertungen status surface lists an exam's import jobs
    (with progress fields), scoped to that exam and the institution — so it can
    show running/finished imports without holding a modal open."""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    other_exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    def _commit(target_exam_id: int) -> None:
        with patch("api.submissions.import_submissions.apply_async"):
            resp = client.post(
                "/api/v1/submissions/import/commit",
                files={
                    "file": (
                        "klasse.json",
                        BytesIO(_JSON_FIXTURE.encode("utf-8")),
                        "application/json",
                    )
                },
                data={"exam_id": str(target_exam_id), "driver_name": "moodle_json"},
            )
            assert resp.status_code == 202, resp.text

    _commit(exam.id)
    _commit(exam.id)
    _commit(other_exam.id)

    listing = client.get("/api/v1/submissions/import-jobs", params={"exam_id": exam.id})
    assert listing.status_code == 200, listing.text
    body = listing.json()
    # Only this exam's jobs — not the other exam's.
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert all(item["exam_id"] == exam.id for item in body["items"])
    # Progress fields are exposed for the UI (TF-428).
    assert "graded_total" in body["items"][0]
    assert "graded_done" in body["items"][0]


def test_list_import_jobs_scoped_to_institution(test_db: Session) -> None:
    """TF-428: the listing is institution-scoped — a user must NOT see another
    institution's import jobs, even when querying that institution's exam_id
    directly. This is the cross-tenant guard on ``import_jobs``; the exam-scoped
    test alone (single institution) cannot prove it."""
    inst_a = _make_institution(test_db, slug="tf428-inst-a")
    user_a = _make_user(test_db, inst_a.id, email="a@test.ch")
    inst_b = _make_institution(test_db, slug="tf428-inst-b")
    user_b = _make_user(test_db, inst_b.id, email="b@test.ch")
    exam_b = _make_exam(test_db, inst_b.id)
    test_db.commit()

    # User B imports into their own exam.
    with patch("api.submissions.import_submissions.apply_async"):
        resp = _client(test_db, user_b).post(
            "/api/v1/submissions/import/commit",
            files={
                "file": (
                    "klasse.json",
                    BytesIO(_JSON_FIXTURE.encode("utf-8")),
                    "application/json",
                )
            },
            data={"exam_id": str(exam_b.id), "driver_name": "moodle_json"},
        )
        assert resp.status_code == 202, resp.text

    # User A, querying institution B's exam_id, sees nothing — the
    # institution filter blocks the cross-tenant read.
    leaked = _client(test_db, user_a).get(
        "/api/v1/submissions/import-jobs", params={"exam_id": exam_b.id}
    )
    assert leaked.status_code == 200, leaked.text
    assert leaked.json()["total"] == 0

    # Sanity: institution B's own user does see the job.
    owned = _client(test_db, user_b).get(
        "/api/v1/submissions/import-jobs", params={"exam_id": exam_b.id}
    )
    assert owned.json()["total"] == 1


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
            files={"file": ("empty.json", BytesIO(b""), "application/json")},
            data={"exam_id": str(exam.id), "driver_name": "moodle_json"},
        )

    assert response.status_code == 400, response.text
    apply_async.assert_not_called()
    assert test_db.query(ImportJob).filter(ImportJob.exam_id == exam.id).count() == 0


def test_commit_rejects_json_without_question_texts_before_enqueue(
    test_db: Session,
) -> None:
    """Second malformed-input branch (no ``frageN`` question texts): same
    contract — 400, no task enqueued, no job row created."""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    bad_csv = json.dumps(
        [{"e-mail-adresse": "anna@example.org", "antwort1": "Bern"}]
    ).encode("utf-8")
    with patch("api.submissions.import_submissions.apply_async") as apply_async:
        response = client.post(
            "/api/v1/submissions/import/commit",
            files={"file": ("bad.json", BytesIO(bad_csv), "application/json")},
            data={"exam_id": str(exam.id), "driver_name": "moodle_json"},
        )

    assert response.status_code == 400, response.text
    apply_async.assert_not_called()
    assert test_db.query(ImportJob).filter(ImportJob.exam_id == exam.id).count() == 0


# ---------------------------------------------------------------------------
# List + Detail
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
    """Spec-compliant alias: GET /api/v1/exams/{exam_id}/submissions"""
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
            "file": (
                "klasse.json",
                BytesIO(_JSON_FIXTURE.encode("utf-8")),
                "application/json",
            )
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

    # Import as user B (worker path seeded directly against test_db)
    client_b = _client(test_db, user_b)
    job = _seed_import(test_db, exam_b, triggered_by=user_b.id)
    list_b = client_b.get("/api/v1/submissions", params={"exam_id": exam_b.id})
    submission_id = list_b.json()["items"][0]["id"]
    job_id = job.id

    # User A must not see the list, detail, or job
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
    """Reviewer user (only submissions:read) must not be able to import."""
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
        is_superuser=False,  # NOT a superuser → real RBAC check
    )
    user.roles.append(reviewer_role)
    test_db.add(user)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/submissions/import/commit",
        files={
            "file": (
                "klasse.json",
                BytesIO(_JSON_FIXTURE.encode("utf-8")),
                "application/json",
            )
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
                    "klasse.json",
                    BytesIO(_JSON_FIXTURE.encode("utf-8")),
                    "application/json",
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
        files={"file": ("huge.json", BytesIO(huge), "application/json")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 413


def test_extra_unknown_keys_are_ignored_not_validation_error(
    test_db: Session,
) -> None:
    """Unknown export columns ⇒ ignored, NOT 422.

    The real Moodle export carries Status/Dauer/Bewertung columns the
    driver has no use for. Because answers are mapped by ``frageN``
    question text (not position), surplus keys are simply ignored — the
    import succeeds with no row errors and no warnings. Validation (422 +
    structured issues) is reserved for *real* schema mismatches; see
    :func:`test_validation_error_surfaces_structured_issues_via_422`
    below for the actual 422 path.
    """
    inst = _make_institution(test_db, slug="val-issues")
    user = _make_user(test_db, inst.id, email="val@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    with_extra_keys = json.dumps(
        [
            [
                {
                    "e-mail-adresse": "extra@test.ch",
                    "status": "Beendet",
                    "dauer": "1 Stunde 25 Minuten",
                    "bewertung/10.00": "Bisher nicht bewertet",
                    "frage1": _Q1,
                    "antwort1": "Bern",
                    "frage2": _Q2,
                    "antwort2": "wahr",
                }
            ]
        ]
    ).encode("utf-8")
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("ok.json", BytesIO(with_extra_keys), "application/json")},
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 200
    assert response.json()["errors"] == []
    assert response.json()["warnings"] == []


def test_validation_error_surfaces_code_and_count_via_422(
    test_db: Session,
) -> None:
    """422 from ImportValidationError carries the code, not a list of rows.

    Until TF-773 PR 2c the response was ``detail: {message, issues}`` with one
    sentence per offending answer, each naming an ``exam_question_id``. The
    nested ``detail`` also broke the ADR 0005 promise that ``detail`` is a
    string. Both are gone: ``detail`` is the translated sentence, the machine-
    readable part sits next to it, and the row detail is in the log.
    """
    from unittest.mock import patch

    from services.import_service import ImportService, ImportValidationError

    inst = _make_institution(test_db, slug="val-422")
    user = _make_user(test_db, inst.id, email="val422@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    def _raise(self, payload, exam):
        raise ImportValidationError(
            "submissions_import_exam_mismatch",
            "3 Antworten verweisen auf Fragen ausserhalb von Prüfung 7",
            count=3,
        )

    with patch.object(ImportService, "_validate_payload", _raise):
        response = client.post(
            "/api/v1/submissions/import/preview",
            files={
                "file": (
                    "ok.json",
                    BytesIO(_JSON_FIXTURE.encode("utf-8")),
                    "application/json",
                )
            },
            data={"exam_id": str(exam.id)},
        )

    assert response.status_code == 422
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["error_code"] == "submissions_import_exam_mismatch"
    assert body["error_params"] == {"count": 3}


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
                    "klasse.json",
                    BytesIO(_JSON_FIXTURE.encode("utf-8")),
                    "application/json",
                )
            },
            data={"exam_id": str(exam.id)},
        )

    assert response.status_code == 503
    body = response.json()
    # TF-773 PR 2c: `detail` is the translated sentence, the machine-readable
    # part its sibling. The job id this used to carry moved to the log — see
    # test_submissions_import_error_codes.py for that assertion.
    assert isinstance(body["detail"], str)
    assert body["error_code"] == "submissions_import_enqueue_failed"

    # Polling the job must still work and show a terminal, failed state. The
    # id no longer comes back in the response, so it is read from the DB —
    # which is also the honest check: the row is what the reaper and the
    # support case work from.
    failed_job = (
        test_db.query(ImportJob)
        .filter(ImportJob.exam_id == exam.id)
        .order_by(ImportJob.id.desc())
        .first()
    )
    assert failed_job is not None
    poll = client.get(f"/api/v1/submissions/import-jobs/{failed_job.id}")
    assert poll.status_code == 200
    job_body = poll.json()
    assert job_body["status"] == "failed"
    assert job_body["error_log"]


def test_enqueue_still_returns_503_when_failure_persist_also_fails() -> None:
    """H2: on a correlated broker+DB outage the failure-state commit itself
    raises. ``_enqueue_import`` must swallow that, attempt a rollback, and
    still raise the coded 503 — never let the commit error escape as an
    unhandled 500 that buries the broker cause. (The job id moved from the
    response to the log in TF-773 PR 2c; the point of the test is the
    swallowed commit failure, not where the id is printed.)"""
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
                locale="de",
                exam=MagicMock(),
                driver_name="moodle_json",
                source_bytes=b"x;y\n1;2\n",
                triggered_by=1,
                source_metadata={},
            )

    exc = excinfo.value
    assert exc.status_code == 503
    assert exc.error_code == "submissions_import_enqueue_failed"
    db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# error_log shape: end-to-end ImportRowErrorOut serialisation
# ---------------------------------------------------------------------------


def test_error_log_serialises_as_structured_list(test_db: Session) -> None:
    """ImportJob.error_log on the wire must be ``list[ImportRowErrorOut]``
    (frontend type) not ``list[dict]`` — so a row error has typed
    row_index/reason/step/details fields."""
    json_with_bad_row = json.dumps(
        [
            [
                # Row with empty email → driver records an ImportRowError
                {
                    "e-mail-adresse": "",
                    "frage1": _Q1,
                    "antwort1": "Bern",
                    "frage2": _Q2,
                    "antwort2": "wahr",
                },
                {
                    "vorname": "Bruno",
                    "nachname": "Muster",
                    "e-mail-adresse": "bruno@example.org",
                    "begonnen": "2026-05-15 09:00:00",
                    "beendet": "2026-05-15 09:25:00",
                    "frage1": _Q1,
                    "antwort1": "Bern",
                    "frage2": _Q2,
                    "antwort2": "wahr",
                },
            ]
        ]
    )

    inst = _make_institution(test_db, slug="error-log-shape")
    user = _make_user(test_db, inst.id, email="error-log@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    # The worker produces the partial import + structured error_log; we assert
    # the *wire* shape via the polling endpoint (_import_job_to_out).
    job = _seed_import(test_db, exam, source=json_with_bad_row)
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


def test_grading_crash_never_reaches_the_polling_response(
    test_db: Session, monkeypatch
) -> None:
    """A per-submission grading crash must not put ``str(exc)`` on the wire.

    ``_grade_touched_submissions`` catches whatever ``grade_submission``
    raises and used to store it verbatim as ``error_log[*].reason`` —
    exactly the raw-exception-on-a-teacher's-screen class of bug this PR
    closed for the job-level ``_fail_job`` path. This pins the analogous fix
    for the per-submission grading path: the polling response gets the
    generic, translated ``submissions_import_internal_error`` sentence, the
    exception's own text (``RuntimeError: …``) and its traceback stay in
    ``job.error_log`` for operator/DB triage but never reach
    ``GET /import-jobs/{id}`` (TF-773 PR 2c review).
    """

    def _boom(_self, _submission_id, **_kwargs):
        raise RuntimeError("simulated grading crash — table submissions_x")

    monkeypatch.setattr(
        "services.grading_service.GradingService.grade_submission", _boom
    )

    inst = _make_institution(test_db, slug="grading-crash-wire")
    user = _make_user(test_db, inst.id, email="grading-crash@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    job = _seed_import(test_db, exam)
    assert job.status in ("partial", "failed")

    # The raw diagnostic is still readable at the DB/service level (operator
    # triage via direct DB access) — only the API response is redacted.
    grading_entries = [e for e in job.error_log if e.get("step") == "grading"]
    assert grading_entries
    assert all("RuntimeError" in e["reason"] for e in grading_entries)

    resp = client.get(f"/api/v1/submissions/import-jobs/{job.id}")
    assert resp.status_code == 200
    body = resp.json()
    serialised = json.dumps(body, ensure_ascii=False)
    assert "RuntimeError" not in serialised
    assert "submissions_x" not in serialised
    assert "Traceback" not in serialised

    wire_grading_entries = [e for e in body["error_log"] if e.get("step") == "grading"]
    assert wire_grading_entries
    for entry in wire_grading_entries:
        assert entry["reason"] == (
            "Der Import ist an einem internen Fehler gescheitert. "
            "Bitte versuche es erneut oder wende dich an den Support."
        )
        assert entry["details"] is None or "traceback" not in entry["details"]
        assert entry["details"] is None or "diagnostic" not in entry["details"]


def test_job_level_failure_never_reaches_the_polling_response(test_db: Session) -> None:
    """A job-level failure (``ImportService._fail_job``, triggered here by a
    driver hard-fail mid-``commit()``) must not put ``str(exc)`` or a
    traceback on the wire — the polling response gets the translated
    sentence for ``exc.code`` instead (TF-773 PR 2c review)."""
    from services.import_drivers import ImportDriverError
    from services.import_service import ImportService

    inst = _make_institution(test_db, slug="job-fail-wire")
    user = _make_user(test_db, inst.id, email="job-fail@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    with pytest.raises(ImportDriverError):
        ImportService(test_db).commit(
            exam=exam,
            driver_name="moodle_json",
            source="not valid json {".encode("utf-8"),
            triggered_by=None,
        )

    job = (
        test_db.query(ImportJob)
        .filter(ImportJob.exam_id == exam.id)
        .order_by(ImportJob.id.desc())
        .first()
    )
    assert job is not None
    assert job.status == "failed"

    client = _client(test_db, user)
    resp = client.get(f"/api/v1/submissions/import-jobs/{job.id}")
    assert resp.status_code == 200
    body = resp.json()
    serialised = json.dumps(body, ensure_ascii=False)
    assert "ImportDriverError" not in serialised
    assert "Traceback" not in serialised
    # exc.log_message ("Quelle ist kein gültiges JSON: <json.JSONDecodeError
    # text>") is log-only; only its distinct "Expecting value" tail — the
    # raw stdlib parser message — proves it, since the safe translated
    # sentence legitimately shares the words "kein gültiges JSON".
    assert "Expecting value" not in serialised

    entry = body["error_log"][0]
    assert entry["reason"] == (
        "Die Datei ist kein gültiges JSON. Bitte prüfe, ob du den "
        "JSON-Export aus Moodle gewählt hast."
    )
    assert entry["details"] is None or "traceback" not in entry["details"]
    assert entry["details"] is None or "diagnostic" not in entry["details"]


def test_preview_422_renders_the_translated_sentence_not_the_service_text(
    test_db: Session, monkeypatch
) -> None:
    """The 422 body is the locale sentence for the code, never ``str(exc)``.

    The exception's own text names the exam row and the count of offending
    answers -- useful in a log, developer wording on a screen. What comes back
    is the German sentence for ``submissions_import_exam_mismatch`` with the
    count interpolated (TF-773 PR 2c).
    """
    from services.import_service import ImportService, ImportValidationError

    inst = _make_institution(test_db, slug="preview-422")
    user = _make_user(test_db, inst.id, email="preview-422@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    def raise_validation(*args, **kwargs):
        raise ImportValidationError(
            "submissions_import_exam_mismatch",
            "3 Antworten verweisen auf Fragen ausserhalb von Prüfung 42",
            count=3,
        )

    monkeypatch.setattr(ImportService, "preview", raise_validation)

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={
            "file": (
                "ok.json",
                BytesIO(_JSON_FIXTURE.encode("utf-8")),
                "application/json",
            )
        },
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == (
        "3 Antworten gehören nicht zu dieser Prüfung. Bitte prüfe, ob du den "
        "richtigen Export gewählt hast."
    )
    assert "Prüfung 42" not in body["detail"]
    assert body["error_code"] == "submissions_import_exam_mismatch"


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
        files={
            "file": (
                "ok.json",
                BytesIO(_JSON_FIXTURE.encode("utf-8")),
                "application/json",
            )
        },
        data={"exam_id": str(exam.id)},
    )
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Result-import deletion (TF-421)
# ---------------------------------------------------------------------------


def test_get_import_summary_returns_counts(test_db: Session) -> None:
    """GET /import/summary previews how much a delete would remove."""
    inst = _make_institution(test_db, slug="del-summary")
    user = _make_user(test_db, inst.id, email="summary@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    _seed_import(test_db, exam)

    client = _client(test_db, user)
    response = client.get(
        "/api/v1/submissions/import/summary", params={"exam_id": exam.id}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["exam_id"] == exam.id
    assert body["submission_count"] == 2
    assert body["attempt_count"] == 2
    assert body["student_count"] == 2
    assert body["by_source"] == [{"source": "moodle_json", "attempt_count": 2}]


def test_delete_import_removes_results_and_writes_audit(test_db: Session) -> None:
    """DELETE /import wipes the exam's results and logs an audit entry."""
    from models.auth import AuditLog
    from models.submission import Attempt, Submission
    from services.audit_service import AuditService

    inst = _make_institution(test_db, slug="del-happy")
    user = _make_user(test_db, inst.id, email="deleter@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    _seed_import(test_db, exam)
    assert test_db.query(Submission).count() == 2

    client = _client(test_db, user)
    response = client.request(
        "DELETE", "/api/v1/submissions/import", params={"exam_id": exam.id}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["submission_count"] == 2
    assert body["attempt_count"] == 2
    # Results are gone.
    assert test_db.query(Submission).filter(Submission.exam_id == exam.id).count() == 0
    assert (
        test_db.query(Attempt)
        .join(Submission, Attempt.submission_id == Submission.id)
        .filter(Submission.exam_id == exam.id)
        .count()
        == 0
    )
    # An audit entry records who deleted what.
    audit = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == AuditService.ACTION_DELETE_RESULT_IMPORT,
            AuditLog.resource_id == str(exam.id),
        )
        .one_or_none()
    )
    assert audit is not None
    assert audit.user_id == user.id


def test_delete_import_without_permission_returns_403(test_db: Session) -> None:
    """A user lacking submissions:delete (reviewer) is rejected."""
    from models.auth import Role, UserRole

    inst = _make_institution(test_db, slug="del-rbac")
    reviewer_role = (
        test_db.query(Role).filter(Role.name == UserRole.ASSISTANT.value).first()
    )
    if reviewer_role is None:
        reviewer_role = Role(
            name=UserRole.ASSISTANT.value,
            display_name="Reviewer",
            permissions=["submissions:read"],
            is_system_role=True,
        )
        test_db.add(reviewer_role)
        test_db.flush()
    assert "submissions:delete" not in (reviewer_role.permissions or [])

    user = User(
        email="reviewer-del@test.ch",
        first_name="Re",
        last_name="Viewer",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    user.roles.append(reviewer_role)
    test_db.add(user)
    exam = _make_exam(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, user)
    response = client.request(
        "DELETE", "/api/v1/submissions/import", params={"exam_id": exam.id}
    )
    assert response.status_code == 403, response.text


def test_delete_import_cross_institution_returns_404(test_db: Session) -> None:
    """An exam in another institution is invisible (multi-tenancy)."""
    from models.submission import Submission

    inst_a = _make_institution(test_db, slug="del-tenant-a")
    inst_b = _make_institution(test_db, slug="del-tenant-b")
    user_a = _make_user(test_db, inst_a.id, email="tenant-a@test.ch")
    exam_b = _make_exam(test_db, inst_b.id)
    test_db.commit()
    _seed_import(test_db, exam_b)

    client = _client(test_db, user_a)
    response = client.request(
        "DELETE", "/api/v1/submissions/import", params={"exam_id": exam_b.id}
    )

    assert response.status_code == 404, response.text
    # Other institution's data is untouched.
    assert (
        test_db.query(Submission).filter(Submission.exam_id == exam_b.id).count() == 2
    )


def test_delete_import_aborts_and_rolls_back_when_audit_fails(
    test_db: Session,
) -> None:
    """Fail-closed: if the audit write fails, the deletion is rolled back and
    the endpoint returns 500 — no data loss without a trail (TF-421)."""
    from models.submission import Attempt, Submission
    from services.audit_service import AuditService

    inst = _make_institution(test_db, slug="del-audit-fail")
    user = _make_user(test_db, inst.id, email="audit-fail@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    _seed_import(test_db, exam)
    assert test_db.query(Submission).count() == 2

    # Simulate the real log_action contract on failure: roll back the staged
    # deletion and return None (the endpoint relies on this rollback).
    def fake_log_action(*args, db=None, **kwargs):
        db.rollback()
        return None

    client = _client(test_db, user)
    with patch.object(
        AuditService, "log_action", side_effect=fake_log_action
    ) as logged:
        response = client.request(
            "DELETE", "/api/v1/submissions/import", params={"exam_id": exam.id}
        )

    assert response.status_code == 500, response.text
    logged.assert_called_once()
    # Deletion was rolled back — results survive.
    assert test_db.query(Submission).filter(Submission.exam_id == exam.id).count() == 2
    assert (
        test_db.query(Attempt)
        .join(Submission, Attempt.submission_id == Submission.id)
        .filter(Submission.exam_id == exam.id)
        .count()
        == 2
    )
