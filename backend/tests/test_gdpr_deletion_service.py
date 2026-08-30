"""Tests für services.gdpr_deletion_service.delete_user_and_gdpr_data (TF-745).

Siehe docs/superpowers/specs/2026-08-27-tf745-gdpr-scheduled-deletion-design.md.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

from models.auth import AuditLog, Institution, User, UserStatus
from models.document import Document
from models.exam import Exam
from models.question_generation_job import QuestionGenerationJob
from models.question_review import QuestionReview
from services.gdpr_deletion_service import delete_user_and_gdpr_data


def _make_institution(db, slug: str) -> Institution:
    institution = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(institution)
    db.flush()
    return institution


def _make_user(db, institution: Institution, email: str) -> User:
    user = User(
        email=email,
        password_hash="dummy",  # pragma: allowlist secret
        first_name="Test",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def test_deleting_user_anonymizes_audit_log_instead_of_deleting_it(test_db):
    """Regressionstest für den ORM/DB-Kaskaden-Konflikt: `User.audit_logs`
    trug `cascade="all, delete-orphan"`, während die DB-FK
    `ondelete="SET NULL"` ist. Ohne den Fix löscht `db.delete(user)` die
    AuditLog-Zeile, statt sie zu anonymisieren (user_id -> NULL)."""
    institution = _make_institution(test_db, "gdpr-del-svc-audit")
    user = _make_user(test_db, institution, "audit@gdpr-del-svc-audit.ch")

    log = AuditLog(user_id=user.id, action="login", status="success")
    test_db.add(log)
    test_db.commit()
    log_id = log.id

    test_db.delete(user)
    test_db.commit()

    persisted = test_db.get(AuditLog, log_id)
    assert persisted is not None
    assert persisted.user_id is None


def test_delete_user_and_gdpr_data_hard_deletes_document(test_db):
    institution = _make_institution(test_db, "gdpr-del-svc-doc")
    user = _make_user(test_db, institution, "doc@gdpr-del-svc-doc.ch")

    document = Document(
        filename="a.pdf",
        original_filename="a.pdf",
        file_path="/tmp/a.pdf",
        file_size=123,
        mime_type="application/pdf",
        user_id=user.id,
    )
    test_db.add(document)
    test_db.commit()
    document_id = document.id
    user_id = user.id

    delete_user_and_gdpr_data(test_db, user, action="account_deleted_immediately")

    assert test_db.get(Document, document_id) is None
    assert test_db.get(User, user_id) is None


def test_delete_user_and_gdpr_data_removes_local_document_file(test_db):
    """Die FK-Cascade löscht nur die `documents`-Zeile, nicht die
    zugehörige Datei auf der Disk — ohne expliziten Storage-Cleanup blieben
    hochgeladene Dokumente nach einer Art.-17-Löschung dauerhaft liegen."""
    institution = _make_institution(test_db, "gdpr-del-svc-file")
    user = _make_user(test_db, institution, "file@gdpr-del-svc-file.ch")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"dummy pdf content")
        file_path = tmp_file.name

    document = Document(
        filename="a.pdf",
        original_filename="a.pdf",
        file_path=file_path,
        file_size=123,
        mime_type="application/pdf",
        user_id=user.id,
    )
    test_db.add(document)
    test_db.commit()

    assert os.path.exists(file_path)

    try:
        delete_user_and_gdpr_data(test_db, user, action="account_deleted_immediately")
        assert not os.path.exists(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def test_delete_user_and_gdpr_data_keeps_file_when_commit_fails(test_db):
    """Reorder-Regressionstest (Runde-3-Review-Fund): schlägt `db.commit()`
    fehl (z. B. IntegrityError durch eine noch nicht abgedeckte FK-Policy),
    muss die Storage-Datei erhalten bleiben — sonst ein Konto mit totem
    Datei-Link trotz zurückgerolltem User/Document. Deckt gleichzeitig ab,
    dass der bare `raise` im `except`-Block den ORIGINALEN Exception-Typ
    (hier IntegrityError) weiterreicht, nicht RuntimeError."""
    institution = _make_institution(test_db, "gdpr-del-svc-commit-fail")
    user = _make_user(test_db, institution, "commitfail@gdpr-del-svc-commit-fail.ch")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"dummy pdf content")
        file_path = tmp_file.name

    document = Document(
        filename="a.pdf",
        original_filename="a.pdf",
        file_path=file_path,
        file_size=123,
        mime_type="application/pdf",
        user_id=user.id,
    )
    test_db.add(document)
    test_db.commit()
    user_id = user.id

    try:
        with patch.object(
            test_db,
            "commit",
            side_effect=IntegrityError("DELETE FROM users ...", {}, Exception()),
        ):
            with pytest.raises(IntegrityError):
                delete_user_and_gdpr_data(
                    test_db, user, action="account_deleted_immediately"
                )

        assert os.path.exists(file_path)
        assert test_db.get(User, user_id) is not None
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def test_delete_user_and_gdpr_data_continues_when_storage_delete_fails(test_db):
    """Ein fehlschlagender Storage-Delete (Datei bereits weg, S3 kurz nicht
    erreichbar, ...) darf die eigentliche DSGVO-Löschung nicht blockieren —
    best effort, analog `DocumentService.delete_document`."""
    institution = _make_institution(test_db, "gdpr-del-svc-file-fail")
    user = _make_user(test_db, institution, "filefail@gdpr-del-svc-file-fail.ch")

    document = Document(
        filename="a.pdf",
        original_filename="a.pdf",
        file_path="/nonexistent/path/does-not-exist.pdf",
        file_size=123,
        mime_type="application/pdf",
        user_id=user.id,
    )
    test_db.add(document)
    test_db.commit()
    user_id = user.id

    with (
        patch(
            "services.gdpr_deletion_service.os.remove",
            side_effect=OSError("permission denied"),
        ),
        patch("services.gdpr_deletion_service.os.path.exists", return_value=True),
    ):
        delete_user_and_gdpr_data(test_db, user, action="account_deleted_immediately")

    assert test_db.get(User, user_id) is None


def test_delete_user_and_gdpr_data_hard_deletes_question_generation_job(test_db):
    """Regressionstest für das FK-Drift-Fixup dieser PR
    (`2026_08_30_tf745_fk_ondelete_cascade.py`): das Model deklarierte
    `ondelete="CASCADE"` bereits vorher, aber die ursprüngliche Migration
    hatte es nie auf die echte DB angewandt."""
    institution = _make_institution(test_db, "gdpr-del-svc-qgj")
    user = _make_user(test_db, institution, "qgj@gdpr-del-svc-qgj.ch")

    job = QuestionGenerationJob(
        task_id="task-gdpr-del-svc-qgj",
        user_id=user.id,
        topic="Test",
        question_count=5,
    )
    test_db.add(job)
    test_db.commit()
    job_id = job.id
    user_id = user.id

    delete_user_and_gdpr_data(test_db, user, action="account_deleted_immediately")

    assert test_db.get(QuestionGenerationJob, job_id) is None
    assert test_db.get(User, user_id) is None


def test_delete_user_and_gdpr_data_anonymizes_exam(test_db):
    institution = _make_institution(test_db, "gdpr-del-svc-exam")
    user = _make_user(test_db, institution, "exam@gdpr-del-svc-exam.ch")

    exam = Exam(title="Testprüfung", institution_id=institution.id, created_by=user.id)
    test_db.add(exam)
    test_db.commit()
    exam_id = exam.id

    delete_user_and_gdpr_data(test_db, user, action="account_deleted_immediately")

    persisted = test_db.get(Exam, exam_id)
    assert persisted is not None
    assert persisted.created_by is None


def test_delete_user_and_gdpr_data_anonymizes_question_review(test_db):
    institution = _make_institution(test_db, "gdpr-del-svc-qr")
    user = _make_user(test_db, institution, "qr@gdpr-del-svc-qr.ch")

    question = QuestionReview(
        question_text="Was ist 1+1?",
        question_type="single_choice",
        difficulty="easy",
        topic="Mathe",
        institution_id=institution.id,
        created_by=user.id,
        reviewed_by=user.id,
    )
    test_db.add(question)
    test_db.commit()
    question_id = question.id

    delete_user_and_gdpr_data(test_db, user, action="account_deleted_immediately")

    persisted = test_db.get(QuestionReview, question_id)
    assert persisted is not None
    assert persisted.created_by is None
    assert persisted.reviewed_by is None


def test_delete_user_and_gdpr_data_writes_audit_entry_with_given_action(test_db):
    institution = _make_institution(test_db, "gdpr-del-svc-action")
    user = _make_user(test_db, institution, "action@gdpr-del-svc-action.ch")
    user_id = user.id

    result = delete_user_and_gdpr_data(
        test_db, user, action="account_deleted_scheduled"
    )

    assert result == {"user_id": user_id, "email": "action@gdpr-del-svc-action.ch"}

    logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "account_deleted_scheduled")
        .all()
    )
    assert len(logs) == 1
    # Der Log-Eintrag wird von DEMSELBEN commit() anonymisiert, der auch den
    # User löscht — konsistent mit allen anderen historischen Logs des Accounts.
    assert logs[0].user_id is None
    assert logs[0].additional_data is not None
    assert "action@gdpr-del-svc-action.ch" in logs[0].additional_data


def test_delete_user_and_gdpr_data_aborts_when_audit_log_write_fails(test_db):
    """Fail-closed-Vertrag: wenn `AuditService.log_action` `None` liefert
    (fehlgeschlagener Audit-Insert), muss die Löschung abgebrochen werden,
    statt unaudited durchzulaufen — analog zu
    `AuditService.log_superuser_bypass`/`log_admin_cross_owner`."""
    institution = _make_institution(test_db, "gdpr-del-svc-audit-fail")
    user = _make_user(test_db, institution, "auditfail@gdpr-del-svc-audit-fail.ch")
    user_id = user.id

    with patch(
        "services.gdpr_deletion_service.AuditService.log_action",
        return_value=None,
    ):
        with pytest.raises(RuntimeError):
            delete_user_and_gdpr_data(
                test_db, user, action="account_deleted_immediately"
            )

    assert test_db.get(User, user_id) is not None
