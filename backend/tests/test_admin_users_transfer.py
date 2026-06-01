"""Integration tests for /api/admin/users/{id}/transfer endpoints (TF-352)."""

import pytest
from fastapi.testclient import TestClient
from main import app
from models.auth import User, Institution
from utils.auth_utils import get_current_superuser, get_current_user
from database import get_db


def test_transfer_request_model_validates():
    from api.admin import TransferUserRequest
    from pydantic import ValidationError

    req = TransferUserRequest(target_institution_id=42)
    assert req.transfer_documents is True
    assert req.transfer_tags is True

    with pytest.raises(ValidationError):
        TransferUserRequest(target_institution_id=0)  # gt=0


def test_transfer_response_model_serializes():
    from api.admin import (
        TransferPreviewResponse,
        TransferPreviewCountsModel,
        TransferExcludedCountsModel,
    )

    resp = TransferPreviewResponse(
        source_institution_id=1,
        source_institution_name="S",
        target_institution_id=2,
        target_institution_name="T",
        transferable=TransferPreviewCountsModel(
            documents=3, exams=1, questions=2, tags=0
        ),
        excluded=TransferExcludedCountsModel(students=10, classes=2, submissions=50),
    )
    data = resp.model_dump()
    assert data["transferable"]["documents"] == 3
    assert data["excluded"]["submissions"] == 50


# ============================================================================
# Fixtures for endpoint tests
# ============================================================================


@pytest.fixture
def target_institution(test_db):
    from sqlalchemy import text

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )
    inst = Institution(
        name="Target",
        slug="target",
        domain="target.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(inst)
    test_db.commit()
    return inst


@pytest.fixture
def user_in_source(test_db, test_institution):
    u = User(
        email="moveme@example.com",
        first_name="m",
        last_name="m",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=False,
    )
    test_db.add(u)
    test_db.commit()
    return u


@pytest.fixture
def superuser_actor(test_db, test_institution):
    a = User(
        email="super@example.com",
        first_name="s",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    test_db.add(a)
    test_db.commit()
    return a


@pytest.fixture
def client_superuser(test_db, superuser_actor):
    def _get_super():
        return superuser_actor

    def _get_db():
        yield test_db

    app.dependency_overrides[get_current_superuser] = _get_super
    app.dependency_overrides[get_current_user] = _get_super
    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client_admin(test_db, test_institution):
    from fastapi import HTTPException

    admin = User(
        email="admin@example.com",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=False,
    )
    test_db.add(admin)
    test_db.commit()

    def _get_admin():
        return admin

    def _block_super():
        raise HTTPException(status_code=403, detail="Not a superuser")

    def _get_db():
        yield test_db

    app.dependency_overrides[get_current_superuser] = _block_super
    app.dependency_overrides[get_current_user] = _get_admin
    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# Endpoint tests
# ============================================================================


def test_preview_endpoint_requires_superuser(client_admin, test_institution):
    """Admin role gets 403."""
    target_iid = test_institution.id + 100
    r = client_admin.get(
        f"/api/admin/users/1/transfer-preview?target_institution_id={target_iid}"
    )
    assert r.status_code == 403


def test_preview_endpoint_happy_path(
    client_superuser,
    test_db,
    test_institution,
    target_institution,
    user_in_source,
):
    r = client_superuser.get(
        f"/api/admin/users/{user_in_source.id}/transfer-preview"
        f"?target_institution_id={target_institution.id}"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_institution_id"] == test_institution.id
    assert body["target_institution_id"] == target_institution.id
    assert "transferable" in body and "excluded" in body
    assert isinstance(body["transferable"]["documents"], int)


def test_preview_endpoint_same_institution(
    client_superuser,
    test_institution,
    user_in_source,
):
    r = client_superuser.get(
        f"/api/admin/users/{user_in_source.id}/transfer-preview"
        f"?target_institution_id={test_institution.id}"
    )
    assert r.status_code == 400


def test_preview_endpoint_user_not_found(client_superuser, target_institution):
    r = client_superuser.get(
        f"/api/admin/users/99999/transfer-preview"
        f"?target_institution_id={target_institution.id}"
    )
    assert r.status_code == 404


def test_preview_endpoint_target_not_found(client_superuser, user_in_source):
    r = client_superuser.get(
        f"/api/admin/users/{user_in_source.id}/transfer-preview"
        f"?target_institution_id=99999"
    )
    assert r.status_code == 404


# ============================================================================
# POST /api/admin/users/{id}/transfer endpoint tests
# ============================================================================


def test_transfer_endpoint_requires_superuser(client_admin, target_institution):
    r = client_admin.post(
        "/api/admin/users/1/transfer",
        json={"target_institution_id": target_institution.id},
    )
    assert r.status_code == 403


def test_transfer_endpoint_self_forbidden(
    client_superuser,
    superuser_actor,
    target_institution,
):
    r = client_superuser.post(
        f"/api/admin/users/{superuser_actor.id}/transfer",
        json={"target_institution_id": target_institution.id},
    )
    assert r.status_code == 400


def test_transfer_endpoint_happy_path(
    client_superuser,
    test_db,
    test_institution,
    target_institution,
    user_in_source,
):
    from models.document import Document, DocumentStatus

    doc = Document(
        original_filename="d.pdf",
        filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user_in_source.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()

    r = client_superuser.post(
        f"/api/admin/users/{user_in_source.id}/transfer",
        json={
            "target_institution_id": target_institution.id,
            "transfer_documents": True,
            "transfer_exams": True,
            "transfer_questions": True,
            "transfer_tags": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["institution_id"] == target_institution.id
    assert body["transferred"]["documents"] == 1

    test_db.expire_all()
    test_db.refresh(doc)
    assert doc.institution_id == target_institution.id
    assert doc.pending_reindex is True


def test_transfer_endpoint_dispatches_reindex(
    client_superuser,
    test_db,
    test_institution,
    target_institution,
    user_in_source,
):
    """After commit, .delay() is called once per transferred document."""
    from models.document import Document, DocumentStatus
    from unittest.mock import patch

    doc = Document(
        original_filename="d.pdf",
        filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user_in_source.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()
    doc_id = doc.id

    with patch("tasks.rag_tasks.reindex_document_to_institution") as mock_task:
        r = client_superuser.post(
            f"/api/admin/users/{user_in_source.id}/transfer",
            json={"target_institution_id": target_institution.id},
        )
    assert r.status_code == 200, r.text
    # Verify .delay() was called with doc_id
    mock_task.delay.assert_called_with(doc_id)


def test_transfer_endpoint_same_institution(
    client_superuser,
    test_institution,
    user_in_source,
):
    r = client_superuser.post(
        f"/api/admin/users/{user_in_source.id}/transfer",
        json={"target_institution_id": test_institution.id},
    )
    assert r.status_code == 400


def test_transfer_endpoint_user_not_found(client_superuser, target_institution):
    r = client_superuser.post(
        "/api/admin/users/99999/transfer",
        json={"target_institution_id": target_institution.id},
    )
    assert r.status_code == 404


def test_transfer_endpoint_target_not_found(client_superuser, user_in_source):
    r = client_superuser.post(
        f"/api/admin/users/{user_in_source.id}/transfer",
        json={"target_institution_id": 99999},
    )
    assert r.status_code == 404


def test_transfer_endpoint_dispatch_failure_returns_200(
    client_superuser,
    test_db,
    test_institution,
    target_institution,
    user_in_source,
):
    """If reindex_document_to_institution.delay() raises (broker down),
    the transfer must still succeed (DB persisted, pending_reindex=True
    acts as the retry marker). Endpoint must NOT return 5xx or roll back."""
    from models.document import Document, DocumentStatus
    from unittest.mock import patch, MagicMock

    doc = Document(
        original_filename="d.pdf",
        filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user_in_source.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()

    mock_task = MagicMock()
    mock_task.delay.side_effect = RuntimeError("broker unreachable")
    with patch("tasks.rag_tasks.reindex_document_to_institution", mock_task):
        r = client_superuser.post(
            f"/api/admin/users/{user_in_source.id}/transfer",
            json={"target_institution_id": target_institution.id},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["institution_id"] == target_institution.id
    assert body["transferred"]["documents"] == 1

    test_db.expire_all()
    test_db.refresh(doc)
    assert doc.institution_id == target_institution.id
    assert doc.pending_reindex is True


def test_transfer_endpoint_validation_order(
    client_superuser,
    superuser_actor,
):
    """When multiple preconditions fail simultaneously, the order of checks
    in the service determines which error code is returned. Pin the order:
    user-exists -> self-move -> target-exists -> same-institution."""
    # Unknown user AND unknown target -> must return 404 user (checked first)
    r = client_superuser.post(
        "/api/admin/users/99999/transfer",
        json={"target_institution_id": 99999},
    )
    assert r.status_code == 404
    # Verify it's the user-not-found code, not the institution-not-found code
    # (translated via t() — both are 404, distinguished by the body text)
    assert (
        "benutzer" in r.json()["detail"].lower() or "user" in r.json()["detail"].lower()
    )
