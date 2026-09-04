"""
Tests for the enforce_resource_access helper.
Covers owner / superuser bypass / forbidden / 404 / audit logging.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from utils.auth_utils import enforce_resource_access
from models.auth import AuditLog, Institution, User, UserStatus


# A user id that deliberately belongs to nobody. The objects under test are
# SimpleNamespaces, not DB rows, so this never has to resolve to a real user —
# it only has to differ from the acting user's id.
FOREIGN_OWNER_ID = 10_000_001


@pytest.fixture
def _enforce_institution(test_db):
    inst = Institution(
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


def _persist_user(db, email, is_superuser, institution_id):
    """Create a real User row so AuditLog FK is satisfied.

    Ids are left to the database: hardcoded primary keys collide with rows
    other test modules leave in the shared test database once the run order
    changes (TF-660).
    """
    u = User(
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
    return _persist_user(test_db, "owner@test.ch", False, _enforce_institution.id)


@pytest.fixture
def other_user(test_db, _enforce_institution):
    return _persist_user(test_db, "other@test.ch", False, _enforce_institution.id)


@pytest.fixture
def super_user(test_db, _enforce_institution):
    return _persist_user(test_db, "admin@test.ch", True, _enforce_institution.id)


def _audit_logs_for(db, user):
    """Audit rows written for this test's user.

    A bare ``query(AuditLog).count() == 0`` counts the whole table, which also
    holds rows the app committed on its own connection during earlier tests
    (logins, registrations) — outside this test's transaction and therefore
    not rolled back. Since every user here gets a fresh, DB-assigned id,
    filtering by it is exact (TF-660).
    """
    return db.query(AuditLog).filter(AuditLog.user_id == user.id).all()


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
    assert _audit_logs_for(test_db, owner_user) == []


def test_enforce_other_user_raises_403(other_user, test_db):
    obj = _make_resource(owner_id=FOREIGN_OWNER_ID)  # not other_user
    with pytest.raises(HTTPException) as exc:
        enforce_resource_access(
            obj=obj,
            user=other_user,
            action="process",
            db=test_db,
            resource_type="document",
        )
    assert exc.value.status_code == 403
    assert _audit_logs_for(test_db, other_user) == []  # no bypass log for non-superuser


def test_enforce_superuser_bypass_logs_audit(super_user, test_db):
    obj = _make_resource(owner_id=FOREIGN_OWNER_ID, resource_id=42)
    enforce_resource_access(
        obj=obj,
        user=super_user,
        action="process",
        db=test_db,
        resource_type="document",
    )
    logs = _audit_logs_for(test_db, super_user)
    assert len(logs) == 1
    assert logs[0].action == "superuser_bypass"
    assert logs[0].resource_type == "document"
    assert logs[0].resource_id == "42"
    import json

    extra = json.loads(logs[0].additional_data)
    assert extra["bypassed_action"] == "process"
    assert extra["owner_user_id"] == FOREIGN_OWNER_ID
    assert extra["superuser_email"] == "admin@test.ch"


def test_enforce_orphan_resource_returns_with_warning(owner_user, test_db, mocker):
    """obj.user_id is None (orphan) → access allowed, warning logged, no audit."""
    # Patch the logger attribute in the module directly; this sidesteps
    # caplog/handler propagation edge cases between pytest 7.4.3 (CI) and
    # 9.0.3 (local).
    mock_logger = mocker.patch("utils.auth_utils.logger")

    obj = _make_resource(owner_id=None)
    enforce_resource_access(
        obj=obj,
        user=owner_user,
        action="view",
        db=test_db,
        resource_type="document",
    )
    assert _audit_logs_for(test_db, owner_user) == []
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
    assert _audit_logs_for(test_db, other_user) == []  # owner-match path


def test_enforce_blocks_cross_institution_access_for_non_superuser(other_user, test_db):
    """Resource in a different institution → 403 even if owner_id is None
    (orphan). Previously the orphan branch returned success unconditionally,
    so a user from institution B could touch an orphan resource from
    institution A. The institution check now runs BEFORE the orphan branch.
    """
    obj = SimpleNamespace(id=42, user_id=None, institution_id=999)
    with pytest.raises(HTTPException) as exc:
        enforce_resource_access(
            obj=obj,
            user=other_user,
            action="process",
            db=test_db,
            resource_type="document",
        )
    assert exc.value.status_code == 403
    # No audit log: a non-superuser blocked at the institution boundary
    # never reaches the bypass branch.
    assert _audit_logs_for(test_db, other_user) == []


def test_enforce_allows_cross_institution_access_for_superuser_with_audit(
    super_user, test_db
):
    """Superusers cross institution boundaries (audit-logged), so a foreign
    institution's resource is still accessible — but a superuser bypass is
    written to the audit trail.
    """
    obj = SimpleNamespace(id=42, user_id=FOREIGN_OWNER_ID, institution_id=999)
    enforce_resource_access(
        obj=obj,
        user=super_user,
        action="delete",
        db=test_db,
        resource_type="document",
    )
    logs = _audit_logs_for(test_db, super_user)
    assert len(logs) == 1
    assert logs[0].action == "superuser_bypass"


def test_enforce_skips_institution_check_when_obj_lacks_institution_id(
    other_user, test_db
):
    """Backwards compatibility: objects without an ``institution_id``
    attribute (existing call patterns) still flow through the owner / orphan
    / superuser branches — the institution gate is opt-in by attribute
    presence so existing callers don't regress.
    """
    obj = SimpleNamespace(id=42, user_id=other_user.id)  # no institution_id
    enforce_resource_access(
        obj=obj,
        user=other_user,
        action="view",
        db=test_db,
        resource_type="exam",
    )
    # Owner-match path returns silently with no audit.
    assert _audit_logs_for(test_db, other_user) == []


def test_enforce_superuser_bypass_aborts_when_audit_persistence_fails(
    super_user, test_db, mocker
):
    """GDPR contract: if log_action returns None (DB error),
    log_superuser_bypass MUST raise HTTPException 500 — the bypass must not
    go through without an audit trail."""
    # log_action() returns None → simulates a persistence failure.
    mocker.patch("services.audit_service.AuditService.log_action", return_value=None)

    obj = _make_resource(owner_id=FOREIGN_OWNER_ID, resource_id=42)
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
