"""
Tests für enforce_resource_access-Helper.
Deckt Owner / Superuser-Bypass / Forbidden / 404 / Audit-Logging ab.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from utils.auth_utils import enforce_resource_access
from models.auth import AuditLog, Institution, User, UserStatus


@pytest.fixture
def _enforce_institution(test_db):
    inst = Institution(
        id=300,
        name="Enforce-Test",
        slug="enforce-test",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.commit()
    return inst


def _persist_user(db, user_id, email, is_superuser, institution_id):
    """Create a real User row so AuditLog FK is satisfied."""
    u = User(
        id=user_id,
        email=email,
        first_name="T",
        last_name="U",
        password_hash="x",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def owner_user(test_db, _enforce_institution):
    return _persist_user(test_db, 1, "owner@test.ch", False, _enforce_institution.id)


@pytest.fixture
def other_user(test_db, _enforce_institution):
    return _persist_user(test_db, 2, "other@test.ch", False, _enforce_institution.id)


@pytest.fixture
def super_user(test_db, _enforce_institution):
    return _persist_user(test_db, 99, "admin@test.ch", True, _enforce_institution.id)


def _make_resource(owner_id, resource_id=42):
    return SimpleNamespace(id=resource_id, user_id=owner_id)


def test_enforce_404_when_obj_none(owner_user, test_db):
    with pytest.raises(HTTPException) as exc:
        enforce_resource_access(
            obj=None,
            user=owner_user,
            action="process",
            db=test_db,
            resource_type="document",
        )
    assert exc.value.status_code == 404


def test_enforce_owner_returns_silently(owner_user, test_db):
    obj = _make_resource(owner_id=owner_user.id)
    enforce_resource_access(
        obj=obj,
        user=owner_user,
        action="process",
        db=test_db,
        resource_type="document",
    )
    # No exception, no audit log
    assert test_db.query(AuditLog).count() == 0


def test_enforce_other_user_raises_403(other_user, test_db):
    obj = _make_resource(owner_id=1)  # Belongs to user 1, not other_user (id=2)
    with pytest.raises(HTTPException) as exc:
        enforce_resource_access(
            obj=obj,
            user=other_user,
            action="process",
            db=test_db,
            resource_type="document",
        )
    assert exc.value.status_code == 403
    assert test_db.query(AuditLog).count() == 0  # No bypass log for non-superuser


def test_enforce_superuser_bypass_logs_audit(super_user, test_db):
    obj = _make_resource(owner_id=1, resource_id=42)
    enforce_resource_access(
        obj=obj,
        user=super_user,
        action="process",
        db=test_db,
        resource_type="document",
    )
    logs = test_db.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].action == "superuser_bypass"
    assert logs[0].user_id == 99
    assert logs[0].resource_type == "document"
    assert logs[0].resource_id == "42"
    import json

    extra = json.loads(logs[0].additional_data)
    assert extra["bypassed_action"] == "process"
    assert extra["owner_user_id"] == 1
    assert extra["superuser_email"] == "admin@test.ch"


def test_enforce_orphan_resource_returns_with_warning(owner_user, test_db, mocker):
    """obj.user_id is None (orphan) → access allowed, warning logged, no audit."""
    # Patch direkt das logger-Attribut im Modul; das umgeht caplog/Handler-
    # Propagation-Edge-Cases zwischen pytest 7.4.3 (CI) und 9.0.3 (lokal).
    mock_logger = mocker.patch("utils.auth_utils.logger")

    obj = _make_resource(owner_id=None)
    enforce_resource_access(
        obj=obj,
        user=owner_user,
        action="view",
        db=test_db,
        resource_type="document",
    )
    assert test_db.query(AuditLog).count() == 0
    mock_logger.warning.assert_called_once()
    assert "Orphan document" in mock_logger.warning.call_args[0][0]


def test_enforce_missing_owner_field_raises_500(owner_user, test_db):
    """Object lacks the requested owner_field → programmer-error 500 (fail loud)."""
    obj = SimpleNamespace(id=42)  # no user_id, no created_by, nothing
    with pytest.raises(HTTPException) as exc:
        enforce_resource_access(
            obj=obj,
            user=owner_user,
            action="x",
            db=test_db,
            resource_type="document",
        )
    assert exc.value.status_code == 500


def test_enforce_custom_owner_field(other_user, test_db):
    """Non-default owner_field is honored."""
    obj = SimpleNamespace(id=1, created_by=other_user.id)
    enforce_resource_access(
        obj=obj,
        user=other_user,
        action="x",
        db=test_db,
        resource_type="exam",
        owner_field="created_by",
    )
    assert test_db.query(AuditLog).count() == 0  # owner-match path


def test_enforce_superuser_bypass_aborts_when_audit_persistence_fails(
    super_user, test_db, mocker
):
    """DSGVO-Vertrag: Wenn log_action None liefert (DB-Fehler), MUSS
    log_superuser_bypass HTTPException 500 raisen — der Bypass darf nicht
    durchgehen ohne Audit-Trail."""
    # log_action() retourniert None → Persistenz-Fehler simuliert.
    mocker.patch("services.audit_service.AuditService.log_action", return_value=None)

    obj = _make_resource(owner_id=1, resource_id=42)
    with pytest.raises(HTTPException) as exc:
        enforce_resource_access(
            obj=obj,
            user=super_user,
            action="process",
            db=test_db,
            resource_type="document",
        )
    assert exc.value.status_code == 500
    assert "Audit log unavailable" in exc.value.detail
