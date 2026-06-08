"""TF-396: Tests für Archivieren / Wiederherstellen / Hard-Delete von Fragen.

Read-Path-Audit (Stand TF-396): Lese-/Wiederverwendungs-Pfade auf
question_reviews, die ``archived_at IS NULL`` filtern MÜSSEN:
  - api/question_review.py::get_review_queue   (Review-Bank-Liste)
  - api/exams.py::list_approved_questions       (Composer-Pool)
  - api/exams.py::_build_candidate_query        (Auto-Fill-Kandidaten)
  - api/exams.py (documents-with-questions Count: nur aktive zählen)
Bewusst NICHT gefiltert: by-id Detail/Restore (sollen archivierte liefern),
Statistik-Zähler die bewusst Gesamtbestand zählen.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from main import app
from models.auth import Institution, User, UserStatus, Role
from models.question_review import (
    QuestionReview,
    ReviewHistory,
    ReviewStatus,
    QuestionSourceDocument,
)
from models.exam import Exam, ExamQuestion
from models.document import Document
from models.auth import AuditLog
from utils.auth_utils import get_current_user, get_current_active_user
from database import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def qa_db(test_engine):
    Session_ = sessionmaker(bind=test_engine)
    session = Session_()
    yield session
    session.close()


@pytest.fixture()
def qa_client(qa_db: Session):
    import api.question_review as qr_module
    import api.exams as exams_module

    app.include_router(qr_module.router)
    app.include_router(exams_module.router)

    def override_get_db():
        yield qa_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(db, suffix="qa"):
    inst = Institution(
        name=f"QA Uni {suffix}",
        slug=f"qa-uni-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def make_user(db, institution_id, suffix="qa", is_superuser=True):
    user = User(
        email=f"qauser{suffix}@test.com",
        first_name="QA",
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
    """Non-Superuser mit einer Rolle, die genau ``perms`` trägt.

    Notwendig, um Tenant-Scoping (_get_scoped_question) und require_permission
    real zu prüfen — Superuser umgehen BEIDE (TenantFilter + has_permission).
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


def make_document(db, institution_id, user_id, suffix="d"):
    doc = Document(
        filename=f"{suffix}.docx",
        original_filename=f"{suffix}.docx",
        file_path=f"uploads/{suffix}.docx",
        file_size=1,
        mime_type="text/plain",
        user_id=user_id,
        institution_id=institution_id,
    )
    db.add(doc)
    db.flush()
    return doc


def make_question(
    db, institution_id, status=ReviewStatus.APPROVED.value, archived_at=None
):
    q = QuestionReview(
        question_text="Was ist Information?",
        question_type="open_ended",
        difficulty="easy",
        topic="Information",
        review_status=status,
        institution_id=institution_id,
        archived_at=archived_at,
    )
    db.add(q)
    db.flush()
    return q


def login(client, user):
    """Override beide Auth-Dependencies auf denselben User."""
    client.app.dependency_overrides[get_current_user] = lambda: user
    client.app.dependency_overrides[get_current_active_user] = lambda: user


# ---------------------------------------------------------------------------
# Phase B — Lese-Pfade
# ---------------------------------------------------------------------------


def test_review_queue_excludes_archived(qa_db, qa_client):
    inst = make_institution(qa_db, "b1")
    user = make_user(qa_db, inst.id, "b1")
    active = make_question(qa_db, inst.id)
    archived = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.get("/api/v1/questions/review")
    assert resp.status_code == 200
    ids = {q["id"] for q in resp.json()["questions"]}
    assert active.id in ids
    assert archived.id not in ids


def test_review_queue_archived_only(qa_db, qa_client):
    inst = make_institution(qa_db, "b2")
    user = make_user(qa_db, inst.id, "b2")
    active = make_question(qa_db, inst.id)
    archived = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.get("/api/v1/questions/review?archived_only=true")
    assert resp.status_code == 200
    ids = {q["id"] for q in resp.json()["questions"]}
    assert archived.id in ids
    assert active.id not in ids


def test_composer_pool_excludes_archived(qa_db, qa_client):
    inst = make_institution(qa_db, "b3")
    user = make_user(qa_db, inst.id, "b3")
    active = make_question(qa_db, inst.id)
    archived = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.get("/api/v1/exams/approved-questions")
    assert resp.status_code == 200
    body = resp.json()
    items = body.get("questions", body) if isinstance(body, dict) else body
    ids = {q["id"] for q in items}
    assert active.id in ids
    assert archived.id not in ids


# ---------------------------------------------------------------------------
# Phase C — Archive / Restore
# ---------------------------------------------------------------------------


def test_archive_sets_timestamp_and_history(qa_db, qa_client):
    inst = make_institution(qa_db, "c1")
    user = make_user(qa_db, inst.id, "c1")
    q = make_question(qa_db, inst.id)
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.post(
        f"/api/v1/questions/{q.id}/archive", json={"reason": "veraltet"}
    )
    assert resp.status_code == 200
    qa_db.refresh(q)
    assert q.archived_at is not None
    assert q.archived_by == user.id
    h = (
        qa_db.query(ReviewHistory)
        .filter_by(question_id=q.id, action="archived")
        .first()
    )
    assert h is not None


def test_archive_already_archived_returns_409(qa_db, qa_client):
    inst = make_institution(qa_db, "c2")
    user = make_user(qa_db, inst.id, "c2")
    q = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.post(f"/api/v1/questions/{q.id}/archive", json={})
    assert resp.status_code == 409


def test_restore_clears_archive(qa_db, qa_client):
    inst = make_institution(qa_db, "c3")
    user = make_user(qa_db, inst.id, "c3")
    q = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.post(f"/api/v1/questions/{q.id}/restore")
    assert resp.status_code == 200
    qa_db.refresh(q)
    assert q.archived_at is None
    assert q.review_status == ReviewStatus.APPROVED.value  # Status unverändert
    h = (
        qa_db.query(ReviewHistory)
        .filter_by(question_id=q.id, action="restored")
        .first()
    )
    assert h is not None
    assert h.changed_by == user.email


# ---------------------------------------------------------------------------
# Phase D — Hard-Delete + Bulk
# ---------------------------------------------------------------------------


def test_delete_blocks_unarchived(qa_db, qa_client):
    inst = make_institution(qa_db, "d1")
    user = make_user(qa_db, inst.id, "d1")
    q = make_question(qa_db, inst.id)  # nicht archiviert
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.request("DELETE", f"/api/v1/questions/{q.id}")
    assert resp.status_code == 409
    assert qa_db.query(QuestionReview).filter_by(id=q.id).first() is not None


def test_delete_blocks_question_in_exam(qa_db, qa_client):
    inst = make_institution(qa_db, "d2")
    user = make_user(qa_db, inst.id, "d2")
    q = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    exam = Exam(title="P1", institution_id=inst.id)
    qa_db.add(exam)
    qa_db.flush()
    qa_db.add(ExamQuestion(exam_id=exam.id, question_id=q.id, position=1, points=1.0))
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.request("DELETE", f"/api/v1/questions/{q.id}")
    assert resp.status_code == 409
    assert qa_db.query(QuestionReview).filter_by(id=q.id).first() is not None


def test_delete_free_archived_question_writes_audit(qa_db, qa_client):
    inst = make_institution(qa_db, "d3")
    user = make_user(qa_db, inst.id, "d3")
    q = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    qid = q.id
    login(qa_client, user)

    resp = qa_client.request("DELETE", f"/api/v1/questions/{qid}")
    assert resp.status_code == 200
    assert qa_db.query(QuestionReview).filter_by(id=qid).first() is None
    log = (
        qa_db.query(AuditLog)
        .filter(AuditLog.action == "delete_question", AuditLog.resource_id == str(qid))
        .first()
    )
    assert log is not None


def test_delete_forbidden_without_permission(qa_db, qa_client):
    inst = make_institution(qa_db, "d4")
    user = make_user(qa_db, inst.id, "d4", is_superuser=False)  # keine Rolle/Permission
    q = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.request("DELETE", f"/api/v1/questions/{q.id}")
    assert resp.status_code == 403
    assert qa_db.query(QuestionReview).filter_by(id=q.id).first() is not None


def test_bulk_delete_mixed(qa_db, qa_client):
    inst = make_institution(qa_db, "d5")
    user = make_user(qa_db, inst.id, "d5")
    free = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    not_archived = make_question(qa_db, inst.id)
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.post(
        "/api/v1/questions/bulk-delete",
        json={"ids": [free.id, not_archived.id]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert free.id in body["deleted"]
    assert any(b["id"] == not_archived.id for b in body["blocked"])
    # Audit-Row pro gelöschter Frage, mit bulk-Marker im Snapshot
    log = (
        qa_db.query(AuditLog)
        .filter(
            AuditLog.action == "delete_question",
            AuditLog.resource_id == str(free.id),
        )
        .first()
    )
    assert log is not None
    assert log.additional_data is not None and '"bulk": true' in log.additional_data


# ---------------------------------------------------------------------------
# Tenant-Scoping + RBAC (Non-Superuser — prüft _get_scoped_question + require_permission)
# ---------------------------------------------------------------------------


def test_archive_cross_tenant_returns_404(qa_db, qa_client):
    inst_a = make_institution(qa_db, "t1a")
    inst_b = make_institution(qa_db, "t1b")
    actor = make_user_with_role(qa_db, inst_a.id, "t1", ["review_questions"])
    foreign = make_question(qa_db, inst_b.id)  # gehört Institution B
    qa_db.commit()
    login(qa_client, actor)

    resp = qa_client.post(f"/api/v1/questions/{foreign.id}/archive", json={})
    assert resp.status_code == 404
    qa_db.refresh(foreign)
    assert foreign.archived_at is None  # nicht angetastet


def test_delete_cross_tenant_returns_404(qa_db, qa_client):
    inst_a = make_institution(qa_db, "t2a")
    inst_b = make_institution(qa_db, "t2b")
    actor = make_user_with_role(qa_db, inst_a.id, "t2", ["delete_questions"])
    foreign = make_question(qa_db, inst_b.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, actor)

    resp = qa_client.request("DELETE", f"/api/v1/questions/{foreign.id}")
    assert resp.status_code == 404
    assert qa_db.query(QuestionReview).filter_by(id=foreign.id).first() is not None


def test_bulk_delete_skips_cross_tenant(qa_db, qa_client):
    inst_a = make_institution(qa_db, "t3a")
    inst_b = make_institution(qa_db, "t3b")
    actor = make_user_with_role(qa_db, inst_a.id, "t3", ["delete_questions"])
    own = make_question(qa_db, inst_a.id, archived_at=datetime.utcnow())
    foreign = make_question(qa_db, inst_b.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, actor)

    resp = qa_client.post(
        "/api/v1/questions/bulk-delete", json={"ids": [own.id, foreign.id]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert own.id in body["deleted"]
    assert any(b["id"] == foreign.id for b in body["blocked"])
    # Fremde Frage NICHT gelöscht
    assert qa_db.query(QuestionReview).filter_by(id=foreign.id).first() is not None


def test_archive_forbidden_without_permission(qa_db, qa_client):
    inst = make_institution(qa_db, "p1")
    actor = make_user_with_role(qa_db, inst.id, "p1", ["view_questions"])
    q = make_question(qa_db, inst.id)
    qa_db.commit()
    login(qa_client, actor)

    resp = qa_client.post(f"/api/v1/questions/{q.id}/archive", json={})
    assert resp.status_code == 403
    qa_db.refresh(q)
    assert q.archived_at is None


def test_restore_forbidden_without_permission(qa_db, qa_client):
    inst = make_institution(qa_db, "p2")
    actor = make_user_with_role(qa_db, inst.id, "p2", ["view_questions"])
    q = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, actor)

    resp = qa_client.post(f"/api/v1/questions/{q.id}/restore")
    assert resp.status_code == 403


def test_review_queue_include_archived_returns_both(qa_db, qa_client):
    inst = make_institution(qa_db, "b4")
    user = make_user(qa_db, inst.id, "b4")
    active = make_question(qa_db, inst.id)
    archived = make_question(qa_db, inst.id, archived_at=datetime.utcnow())
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.get("/api/v1/questions/review?include_archived=true")
    assert resp.status_code == 200
    ids = {q["id"] for q in resp.json()["questions"]}
    assert active.id in ids
    assert archived.id in ids


# ---------------------------------------------------------------------------
# Exams read path: Dokument-Fragenzähler schliesst archivierte aus
# (validiert die and_(...)-Bedingung im SQL-case von list_documents_with_questions)
# ---------------------------------------------------------------------------


def test_documents_with_questions_count_excludes_archived(qa_db, qa_client):
    inst = make_institution(qa_db, "dq")
    user = make_user(qa_db, inst.id, "dq")
    doc = make_document(qa_db, inst.id, user.id)
    q1 = make_question(qa_db, inst.id)  # approved, aktiv
    q2 = make_question(
        qa_db, inst.id, archived_at=datetime.utcnow()
    )  # approved, archiviert
    qa_db.add(QuestionSourceDocument(question_id=q1.id, document_id=doc.id))
    qa_db.add(QuestionSourceDocument(question_id=q2.id, document_id=doc.id))
    qa_db.commit()
    login(qa_client, user)

    resp = qa_client.get("/api/v1/exams/documents-with-questions")
    assert resp.status_code == 200
    entry = next(d for d in resp.json() if d["id"] == doc.id)
    assert entry["approved_question_count"] == 1  # archivierte Frage nicht mitgezählt
