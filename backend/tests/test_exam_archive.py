"""TF-398: Tests for archiving / restoring / hard-deleting exams.

Mirrors the TF-396 pattern (``test_question_archive.py``), adapted to
exam semantics.

Read-path audit (as of TF-398): read/overview paths on ``exams`` that
MUST filter ``archived_at IS NULL``:
- ``api/exams.py::list_exams`` (composer overview)

Deliberately NOT filtered: by-id detail / archive / restore / delete,
grading/export-by-id (``grades.py``, ``grade_export.py``,
``moodle_roundtrip.py``), statistics counters (``dashboard.py``, ``stats.py``).
Rationale: an archived (but not deleted) exam remains reachable for
grading/exporting its existing submissions.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from main import app
from models.auth import Institution, User, UserStatus, Role, AuditLog
from models.exam import Exam, ExamVisibility
from models.student import Student
from models.submission import Submission
from utils.auth_utils import get_current_user, get_current_active_user
from database import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ea_db(test_engine):
    # Savepoint isolation like ``conftest.test_db``: each test runs inside an
    # outer transaction that is rolled back at the end of the test. Without
    # this, the rows committed here (among them Student/Submission via
    # ``make_submission``) leaked into the session-scoped test DB and broke
    # the global count assertions in ``test_import_service.py`` (``query(Student)
    # .count() == 0``). ``join_transaction_mode="create_savepoint"`` ensures
    # that ``commit()`` inside the endpoint/``audit_service.log_action``
    # stays visible within the test, but is not persisted beyond the test
    # boundary.
    connection = test_engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        join_transaction_mode="create_savepoint",
    )
    session = Session_()
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def ea_client(ea_db: Session):
    import api.exams as exams_module

    app.include_router(exams_module.router)

    def override_get_db():
        yield ea_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(db, suffix="ea"):
    inst = Institution(
        name=f"EA Uni {suffix}",
        slug=f"ea-uni-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def make_user(db, institution_id, suffix="ea", is_superuser=True):
    user = User(
        email=f"eauser{suffix}@test.com",
        first_name="EA",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()
    return user


def make_user_with_role(db, institution_id, suffix, perms):
    """Non-superuser with a role that carries exactly ``perms``.

    Needed to actually exercise tenant scoping (``_get_exam_or_404`` +
    ``TenantFilter``) and ``require_permission`` — superusers bypass BOTH.
    """
    user = make_user(db, institution_id, suffix, is_superuser=False)
    role = Role(
        name=f"role-{suffix}",
        display_name=f"Role {suffix}",
        permissions=json.dumps(perms),
    )
    db.add(role)
    db.flush()
    user.roles.append(role)
    db.flush()
    return user


def make_exam(
    db,
    institution_id,
    created_by=None,
    status="draft",
    archived_at=None,
    title="Musterprüfung",
    visibility=None,
):
    exam = Exam(
        title=title,
        course="C",
        status=status,
        language="de",
        institution_id=institution_id,
        created_by=created_by,
        archived_at=archived_at,
    )
    if visibility is not None:
        exam.visibility = visibility
    db.add(exam)
    db.flush()
    return exam


def make_submission(db, exam_id, institution_id, suffix="s"):
    student = Student(
        institution_id=institution_id, external_id=f"{suffix}-{exam_id}@a.org"
    )
    db.add(student)
    db.flush()
    sub = Submission(exam_id=exam_id, student_id=student.id, scoring_strategy="latest")
    db.add(sub)
    db.flush()
    return sub


def login(client, user):
    """Override both auth dependencies to the same user."""
    client.app.dependency_overrides[get_current_user] = lambda: user
    client.app.dependency_overrides[get_current_active_user] = lambda: user


# ---------------------------------------------------------------------------
# Phase B — read paths (overview filters archived)
# ---------------------------------------------------------------------------


def test_list_excludes_archived_by_default(ea_db, ea_client):
    inst = make_institution(ea_db, "b1")
    user = make_user(ea_db, inst.id, "b1")
    active = make_exam(ea_db, inst.id, user.id)
    archived = make_exam(ea_db, inst.id, user.id, archived_at=datetime.utcnow())
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.get("/api/v1/exams/")
    assert resp.status_code == 200
    ids = {e["id"] for e in resp.json()["exams"]}
    assert active.id in ids
    assert archived.id not in ids


def test_list_archived_only(ea_db, ea_client):
    inst = make_institution(ea_db, "b2")
    user = make_user(ea_db, inst.id, "b2")
    active = make_exam(ea_db, inst.id, user.id)
    archived = make_exam(ea_db, inst.id, user.id, archived_at=datetime.utcnow())
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.get("/api/v1/exams/?archived_only=true")
    assert resp.status_code == 200
    ids = {e["id"] for e in resp.json()["exams"]}
    assert archived.id in ids
    assert active.id not in ids


def test_list_include_archived(ea_db, ea_client):
    inst = make_institution(ea_db, "b3")
    user = make_user(ea_db, inst.id, "b3")
    active = make_exam(ea_db, inst.id, user.id)
    archived = make_exam(ea_db, inst.id, user.id, archived_at=datetime.utcnow())
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.get("/api/v1/exams/?include_archived=true")
    assert resp.status_code == 200
    ids = {e["id"] for e in resp.json()["exams"]}
    assert active.id in ids
    assert archived.id in ids


def test_list_exposes_has_submissions(ea_db, ea_client):
    inst = make_institution(ea_db, "b4")
    user = make_user(ea_db, inst.id, "b4")
    with_sub = make_exam(ea_db, inst.id, user.id, title="MitAbgabe")
    without_sub = make_exam(ea_db, inst.id, user.id, title="OhneAbgabe")
    make_submission(ea_db, with_sub.id, inst.id)
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.get("/api/v1/exams/")
    assert resp.status_code == 200
    flags = {e["id"]: e["has_submissions"] for e in resp.json()["exams"]}
    assert flags[with_sub.id] is True
    assert flags[without_sub.id] is False


# ---------------------------------------------------------------------------
# Phase C — Archive / Restore
# ---------------------------------------------------------------------------


def test_archive_sets_fields_and_audit(ea_db, ea_client):
    inst = make_institution(ea_db, "c1")
    user = make_user(ea_db, inst.id, "c1")
    exam = make_exam(ea_db, inst.id, user.id)
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.post(
        f"/api/v1/exams/{exam.id}/archive", json={"reason": "veraltet"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["archived_at"] is not None
    assert body["archive_reason"] == "veraltet"

    ea_db.refresh(exam)
    assert exam.archived_at is not None
    assert exam.archived_by == user.id
    assert exam.archive_reason == "veraltet"

    log = (
        ea_db.query(AuditLog)
        .filter(AuditLog.action == "archive_exam", AuditLog.resource_id == str(exam.id))
        .first()
    )
    assert log is not None


def test_archive_already_archived_returns_409(ea_db, ea_client):
    inst = make_institution(ea_db, "c2")
    user = make_user(ea_db, inst.id, "c2")
    exam = make_exam(ea_db, inst.id, user.id, archived_at=datetime.utcnow())
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.post(f"/api/v1/exams/{exam.id}/archive", json={})
    assert resp.status_code == 409


def test_restore_clears_archive_keeps_status(ea_db, ea_client):
    inst = make_institution(ea_db, "c3")
    user = make_user(ea_db, inst.id, "c3")
    exam = make_exam(
        ea_db, inst.id, user.id, status="finalized", archived_at=datetime.utcnow()
    )
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.post(f"/api/v1/exams/{exam.id}/restore")
    assert resp.status_code == 200
    ea_db.refresh(exam)
    assert exam.archived_at is None
    assert exam.archived_by is None
    # Restore leaves the original status untouched.
    assert exam.status == "finalized"


def test_restore_not_archived_returns_409(ea_db, ea_client):
    inst = make_institution(ea_db, "c4")
    user = make_user(ea_db, inst.id, "c4")
    exam = make_exam(ea_db, inst.id, user.id)
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.post(f"/api/v1/exams/{exam.id}/restore")
    assert resp.status_code == 409


def test_archive_leaves_export_and_submissions_untouched(ea_db, ea_client):
    """Archiving an exported exam with submissions changes neither status
    nor submissions (TF-398: archiving is orthogonal to the lifecycle)."""
    inst = make_institution(ea_db, "c5")
    user = make_user(ea_db, inst.id, "c5")
    exam = make_exam(ea_db, inst.id, user.id, status="exported")
    make_submission(ea_db, exam.id, inst.id)
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.post(f"/api/v1/exams/{exam.id}/archive", json={})
    assert resp.status_code == 200
    ea_db.refresh(exam)
    assert exam.archived_at is not None
    assert exam.status == "exported"
    sub_count = ea_db.query(Submission).filter(Submission.exam_id == exam.id).count()
    assert sub_count == 1


# ---------------------------------------------------------------------------
# Phase D — hard-delete guards (otherwise 409)
# ---------------------------------------------------------------------------


def test_delete_requires_archive_first(ea_db, ea_client):
    inst = make_institution(ea_db, "d1")
    user = make_user(ea_db, inst.id, "d1")
    exam = make_exam(ea_db, inst.id, user.id)  # not archived
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.request("DELETE", f"/api/v1/exams/{exam.id}")
    assert resp.status_code == 409
    assert ea_db.query(Exam).filter_by(id=exam.id).first() is not None


def test_delete_exported_blocked(ea_db, ea_client):
    inst = make_institution(ea_db, "d2")
    user = make_user(ea_db, inst.id, "d2")
    exam = make_exam(
        ea_db, inst.id, user.id, status="exported", archived_at=datetime.utcnow()
    )
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.request("DELETE", f"/api/v1/exams/{exam.id}")
    assert resp.status_code == 409
    assert ea_db.query(Exam).filter_by(id=exam.id).first() is not None


def test_delete_with_submissions_blocked(ea_db, ea_client):
    inst = make_institution(ea_db, "d3")
    user = make_user(ea_db, inst.id, "d3")
    exam = make_exam(ea_db, inst.id, user.id, archived_at=datetime.utcnow())
    make_submission(ea_db, exam.id, inst.id)
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.request("DELETE", f"/api/v1/exams/{exam.id}")
    assert resp.status_code == 409
    assert ea_db.query(Exam).filter_by(id=exam.id).first() is not None


def test_delete_archived_free_exam_succeeds_with_audit_snapshot(ea_db, ea_client):
    inst = make_institution(ea_db, "d4")
    user = make_user(ea_db, inst.id, "d4")
    exam = make_exam(
        ea_db, inst.id, user.id, archived_at=datetime.utcnow(), title="ZuLöschen"
    )
    exam_id = exam.id
    ea_db.commit()
    login(ea_client, user)

    resp = ea_client.request("DELETE", f"/api/v1/exams/{exam_id}")
    assert resp.status_code == 204
    assert ea_db.query(Exam).filter_by(id=exam_id).first() is None

    log = (
        ea_db.query(AuditLog)
        .filter(AuditLog.action == "delete_exam", AuditLog.resource_id == str(exam_id))
        .first()
    )
    assert log is not None
    snapshot = json.loads(log.additional_data)
    assert snapshot["title"] == "ZuLöschen"
    assert snapshot["status"] == "draft"


def test_delete_audit_failure_returns_500_and_keeps_exam(ea_db, ea_client, monkeypatch):
    """If audit logging fails during the hard delete (``log_action`` →
    ``None``), the endpoint aborts with HTTP 500 and the staged delete is
    rolled back — the exam is preserved (fail-loud, no silent data loss).
    Covers the ``if audit is None`` branch in ``delete_exam``.
    """
    inst = make_institution(ea_db, "d5")
    user = make_user(ea_db, inst.id, "d5")
    exam = make_exam(
        ea_db, inst.id, user.id, archived_at=datetime.utcnow(), title="AuditFail"
    )
    exam_id = exam.id
    ea_db.commit()
    login(ea_client, user)

    # Simulate a log_action failure: like the real service contract, this
    # rolls back the staged delete and returns None.
    import services.audit_service as audit_module

    def _failing_log_action(db, *args, **kwargs):
        db.rollback()
        return None

    monkeypatch.setattr(
        audit_module.AuditService,
        "log_action",
        staticmethod(_failing_log_action),
    )

    resp = ea_client.request("DELETE", f"/api/v1/exams/{exam_id}")
    assert resp.status_code == 500
    # Rollback: the exam was NOT deleted.
    assert ea_db.query(Exam).filter_by(id=exam_id).first() is not None


# ---------------------------------------------------------------------------
# Phase E — RBAC / Tenant-Scoping
# ---------------------------------------------------------------------------


def test_archive_forbidden_without_create_exams(ea_db, ea_client):
    inst = make_institution(ea_db, "e1")
    actor = make_user_with_role(ea_db, inst.id, "e1", ["view_questions"])
    exam = make_exam(ea_db, inst.id, actor.id)
    ea_db.commit()
    login(ea_client, actor)

    resp = ea_client.post(f"/api/v1/exams/{exam.id}/archive", json={})
    assert resp.status_code == 403


def test_delete_forbidden_with_only_create_exams(ea_db, ea_client):
    """``create_exams`` may archive, but NOT hard-delete — delete requires
    ``delete_exams`` (admin level)."""
    inst = make_institution(ea_db, "e2")
    actor = make_user_with_role(ea_db, inst.id, "e2", ["create_exams"])
    exam = make_exam(ea_db, inst.id, actor.id, archived_at=datetime.utcnow())
    ea_db.commit()
    login(ea_client, actor)

    resp = ea_client.request("DELETE", f"/api/v1/exams/{exam.id}")
    assert resp.status_code == 403
    assert ea_db.query(Exam).filter_by(id=exam.id).first() is not None


def test_archive_foreign_tenant_denied(ea_db, ea_client):
    """Foreign tenant: ``_get_exam_or_404`` → ``assert_exam_visible_for``
    denies with 404, not 403 (TF-643 — previously ``TenantFilter
    .verify_tenant_access`` threw 403; since TF-643, all exam access,
    including mutation, goes through the same visibility check as
    Documents/Questions, which deliberately returns 404 instead of 403 to
    avoid leaking the existence of a foreign resource — see
    ``assert_exam_visible_for``'s own docstring in
    utils/exam_visibility.py, where this rationale is actually stated)."""
    inst_a = make_institution(ea_db, "e3a")
    inst_b = make_institution(ea_db, "e3b")
    actor = make_user_with_role(ea_db, inst_a.id, "e3", ["create_exams"])
    foreign = make_exam(ea_db, inst_b.id, None)
    ea_db.commit()
    login(ea_client, actor)

    resp = ea_client.post(f"/api/v1/exams/{foreign.id}/archive", json={})
    assert resp.status_code == 404


def test_archive_read_all_bypass_denied_for_same_institution_private_exam(
    ea_db, ea_client
):
    """PR #193 review gap: the read-all-bypass-exclusion coverage only ever
    exercised update_exam/delete_exam directly; archive_exam itself was only
    tested for the cross-institution case above. A same-institution
    ``exams:read_all`` admin must be denied archiving a colleague's PRIVATE
    exam too — ``allow_read_all_bypass=False`` at the archive call site must
    actually hold."""
    inst = make_institution(ea_db, "e4")
    creator = make_user_with_role(ea_db, inst.id, "e4creator", ["create_exams"])
    admin = make_user_with_role(
        ea_db, inst.id, "e4admin", ["create_exams", "exams:read_all"]
    )
    priv = make_exam(ea_db, inst.id, creator.id, visibility=ExamVisibility.PRIVATE)
    ea_db.commit()
    login(ea_client, admin)

    resp = ea_client.post(f"/api/v1/exams/{priv.id}/archive", json={})
    assert resp.status_code == 404
    ea_db.refresh(priv)
    assert priv.archived_at is None
