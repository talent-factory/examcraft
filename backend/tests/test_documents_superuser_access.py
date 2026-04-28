"""
Integration-Tests: Superuser darf fremde Dokumente verarbeiten/löschen.

Ruft die Endpoint-Funktionen direkt (statt via TestClient mit Lifespan) auf,
um Test-Isolation gegen `core_api_*` re-import zu vermeiden.
"""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.documents import process_document, delete_document
from models.auth import AuditLog, Institution, User, UserStatus
from models.document import Document, DocumentStatus


@pytest.fixture
def stage_data(test_db):
    """Owner + Superuser + Doc in derselben Institution."""
    inst = Institution(
        id=200,
        name="Stage",
        slug="stage",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    owner = User(
        id=200,
        email="owner@s.ch",
        first_name="O",
        last_name="W",
        password_hash="x",
        institution_id=200,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    admin = User(
        id=201,
        email="admin@s.ch",
        first_name="A",
        last_name="D",
        password_hash="x",
        institution_id=200,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    other = User(
        id=202,
        email="other@s.ch",
        first_name="X",
        last_name="Y",
        password_hash="x",
        institution_id=200,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add_all([owner, admin, other])
    test_db.flush()
    doc = Document(
        id=500,
        filename="d.pdf",
        original_filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=10,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=200,
        user_id=200,
    )
    test_db.add(doc)
    test_db.commit()
    return SimpleNamespace(owner=owner, admin=admin, other=other, doc=doc)


def _run(coro):
    """Run an async coroutine synchronously (for endpoint functions)."""
    return asyncio.new_event_loop().run_until_complete(coro)


def test_process_foreign_doc_as_owner_returns_200(stage_data, test_db):
    """Owner kann eigenes Dokument processen — kein Audit-Bypass-Log."""
    s = stage_data
    result = _run(
        process_document(
            document_id=s.doc.id,
            create_vectors=False,
            background_tasks=None,
            request=None,
            current_user=s.owner,
            db=test_db,
        )
    )
    assert result["status"] == "processing"
    bypass_logs = (
        test_db.query(AuditLog).filter(AuditLog.action == "superuser_bypass").all()
    )
    assert len(bypass_logs) == 0


def test_process_foreign_doc_as_other_user_raises_403(stage_data, test_db):
    """Anderer User (kein Superuser) bekommt 403."""
    s = stage_data
    with pytest.raises(HTTPException) as exc:
        _run(
            process_document(
                document_id=s.doc.id,
                create_vectors=False,
                background_tasks=None,
                request=None,
                current_user=s.other,
                db=test_db,
            )
        )
    assert exc.value.status_code == 403


def test_process_foreign_doc_as_superuser_logs_bypass(stage_data, test_db):
    """Superuser bypassed Owner-Check + Bypass wird im audit_logs festgehalten."""
    s = stage_data
    result = _run(
        process_document(
            document_id=s.doc.id,
            create_vectors=False,
            background_tasks=None,
            request=None,
            current_user=s.admin,
            db=test_db,
        )
    )
    assert result["status"] == "processing"

    bypass_logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "superuser_bypass")
        .filter(AuditLog.resource_type == "document")
        .all()
    )
    assert len(bypass_logs) == 1
    log = bypass_logs[0]
    assert log.user_id == 201
    assert log.resource_id == "500"
    extra = json.loads(log.additional_data)
    assert extra["bypassed_action"] == "process"
    assert extra["owner_user_id"] == 200
    assert extra["superuser_email"] == "admin@s.ch"


def test_delete_foreign_doc_as_superuser_logs_bypass(stage_data, test_db):
    """Superuser darf fremdes Dokument löschen + Audit-Eintrag."""
    s = stage_data
    _run(
        delete_document(
            document_id=s.doc.id,
            http_request=None,
            current_user=s.admin,
            db=test_db,
        )
    )
    bypass_logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "superuser_bypass")
        .filter(AuditLog.resource_type == "document")
        .all()
    )
    assert any(
        json.loads(log.additional_data)["bypassed_action"] == "delete"
        for log in bypass_logs
    )


def test_delete_foreign_doc_as_same_institution_admin_logs_admin_cross_owner(
    stage_data, test_db
):
    """Same-institution-Admin (kein Superuser) darf löschen, wird aber auditiert."""
    s = stage_data

    # Add admin role to `other` user, same institution as the doc owner
    from models.auth import Role

    admin_role = Role(
        id=900,
        name="admin",
        display_name="Admin",
        permissions='["delete_documents"]',
    )
    test_db.add(admin_role)
    test_db.flush()
    s.other.roles.append(admin_role)
    test_db.commit()

    _run(
        delete_document(
            document_id=s.doc.id,
            http_request=None,
            current_user=s.other,
            db=test_db,
        )
    )

    cross_logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "admin_cross_owner")
        .filter(AuditLog.resource_type == "document")
        .all()
    )
    assert len(cross_logs) == 1
    assert cross_logs[0].user_id == s.other.id
    extra = json.loads(cross_logs[0].additional_data)
    assert extra["bypassed_action"] == "delete"
    assert extra["owner_user_id"] == s.owner.id


def test_upload_over_doc_quota_as_superuser_logs_bypass(stage_data, test_db):
    """Superuser darf trotz erschöpftem max_documents weiter hochladen + Bypass-Audit."""
    s = stage_data
    s.owner.institution.max_documents = 0
    test_db.commit()

    from utils.tenant_utils import SubscriptionLimits

    SubscriptionLimits.check_document_limit(
        s.owner.institution, test_db, user=s.admin, request=None
    )

    quota_logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "superuser_bypass")
        .filter(AuditLog.resource_type == "quota")
        .all()
    )
    assert any(
        json.loads(log.additional_data)["bypassed_action"] == "override_document_limit"
        for log in quota_logs
    )


def test_delete_foreign_doc_as_superuser_aborts_when_audit_fails(
    stage_data, test_db, mocker
):
    """DSGVO-Vertrag: Wenn der Audit-Log nicht persistiert werden kann, darf
    der Superuser-Bypass NICHT durchgehen — HTTP 500, Dokument bleibt
    bestehen."""
    s = stage_data
    mocker.patch("services.audit_service.AuditService.log_action", return_value=None)

    with pytest.raises(HTTPException) as exc:
        _run(
            delete_document(
                document_id=s.doc.id,
                http_request=None,
                current_user=s.admin,
                db=test_db,
            )
        )
    assert exc.value.status_code == 500

    # Dokument muss noch existieren — Bypass wurde abgebrochen.
    from models.document import Document

    assert test_db.query(Document).filter(Document.id == s.doc.id).first() is not None


def test_delete_foreign_doc_as_admin_aborts_when_audit_fails(
    stage_data, test_db, mocker
):
    """DSGVO-Vertrag: Same-institution-Admin darf bei Audit-Persistenz-Fehler
    ebenfalls nicht durchgehen — analog zum Superuser."""
    from models.auth import Role

    s = stage_data
    admin_role = Role(
        id=901,
        name="admin",
        display_name="Admin",
        permissions='["delete_documents"]',
    )
    test_db.add(admin_role)
    test_db.flush()
    s.other.roles.append(admin_role)
    test_db.commit()

    mocker.patch("services.audit_service.AuditService.log_action", return_value=None)

    with pytest.raises(HTTPException) as exc:
        _run(
            delete_document(
                document_id=s.doc.id,
                http_request=None,
                current_user=s.other,
                db=test_db,
            )
        )
    assert exc.value.status_code == 500

    from models.document import Document

    assert test_db.query(Document).filter(Document.id == s.doc.id).first() is not None
