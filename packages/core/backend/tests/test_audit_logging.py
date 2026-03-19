"""
Tests for Audit Logging
Tests that security-relevant actions are properly logged
"""

import pytest
from datetime import datetime, timezone

from models.auth import User, Role, Institution, UserStatus, UserRole, AuditLog
from services.auth_service import AuthService
from services.audit_service import AuditService


@pytest.fixture(scope="function")
def db(test_db):
    """Use PostgreSQL test database from conftest.py"""
    # Create test institution
    institution = Institution(
        name="Test University",
        slug="test-university",
        domain="test.edu",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(institution)
    test_db.flush()

    # Get or create viewer role
    viewer_role = test_db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()
    if not viewer_role:
        viewer_role = Role(
            name=UserRole.VIEWER.value,
            display_name="Viewer",
            description="Can view questions",
            permissions=["view_questions"],
            is_system_role=True,
        )
        test_db.add(viewer_role)
    test_db.commit()

    yield test_db


def create_test_user(db):
    """Helper to create test user"""
    institution = db.query(Institution).first()
    viewer_role = db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()

    user = User(
        email="test@example.com",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Test",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    user.roles.append(viewer_role)
    db.commit()
    db.refresh(user)

    return user


# ============================================================================
# Basic Audit Logging Tests
# ============================================================================


def test_log_action_creates_audit_entry(db):
    """Test that log_action creates an audit log entry"""
    user = create_test_user(db)

    audit_log = AuditService.log_action(
        db=db,
        action=AuditService.ACTION_LOGIN,
        status=AuditService.STATUS_SUCCESS,
        user_id=user.id,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )

    assert audit_log is not None
    assert audit_log.action == AuditService.ACTION_LOGIN
    assert audit_log.status == AuditService.STATUS_SUCCESS
    assert audit_log.user_id == user.id
    assert audit_log.ip_address == "192.168.1.1"
    assert audit_log.user_agent == "Mozilla/5.0"


def test_log_action_with_additional_data(db):
    """Test that additional data is stored as JSON"""
    user = create_test_user(db)

    additional_data = {"login_method": "password", "device": "mobile"}

    audit_log = AuditService.log_action(
        db=db,
        action=AuditService.ACTION_LOGIN,
        status=AuditService.STATUS_SUCCESS,
        user_id=user.id,
        additional_data=additional_data,
    )

    assert audit_log.additional_data is not None
    assert "login_method" in audit_log.additional_data
    assert "password" in audit_log.additional_data


# ============================================================================
# Authentication Event Logging Tests
# ============================================================================


def test_log_login_success(db):
    """Test logging successful login"""
    user = create_test_user(db)

    audit_log = AuditService.log_login(db=db, user_id=user.id, success=True)

    assert audit_log.action == AuditService.ACTION_LOGIN
    assert audit_log.status == AuditService.STATUS_SUCCESS
    assert audit_log.user_id == user.id


def test_log_login_failure(db):
    """Test logging failed login"""
    user = create_test_user(db)

    audit_log = AuditService.log_login(
        db=db, user_id=user.id, success=False, error_message="Incorrect password"
    )

    assert audit_log.action == AuditService.ACTION_LOGIN
    assert audit_log.status == AuditService.STATUS_FAILURE
    assert audit_log.error_message == "Incorrect password"


def test_log_logout(db):
    """Test logging user logout"""
    user = create_test_user(db)

    audit_log = AuditService.log_logout(db=db, user_id=user.id)

    assert audit_log.action == AuditService.ACTION_LOGOUT
    assert audit_log.status == AuditService.STATUS_SUCCESS
    assert audit_log.user_id == user.id


def test_log_register(db):
    """Test logging user registration"""
    user = create_test_user(db)

    audit_log = AuditService.log_register(db=db, user_id=user.id, email=user.email)

    assert audit_log.action == AuditService.ACTION_REGISTER
    assert audit_log.status == AuditService.STATUS_SUCCESS
    assert audit_log.user_id == user.id


def test_log_password_change_success(db):
    """Test logging successful password change"""
    user = create_test_user(db)

    audit_log = AuditService.log_password_change(db=db, user_id=user.id, success=True)

    assert audit_log.action == AuditService.ACTION_PASSWORD_CHANGE
    assert audit_log.status == AuditService.STATUS_SUCCESS


def test_log_password_change_failure(db):
    """Test logging failed password change"""
    user = create_test_user(db)

    audit_log = AuditService.log_password_change(
        db=db,
        user_id=user.id,
        success=False,
        error_message="Current password is incorrect",
    )

    assert audit_log.action == AuditService.ACTION_PASSWORD_CHANGE
    assert audit_log.status == AuditService.STATUS_FAILURE
    assert audit_log.error_message == "Current password is incorrect"


# ============================================================================
# Resource Action Logging Tests
# ============================================================================


def test_log_document_action(db):
    """Test logging document actions"""
    user = create_test_user(db)

    audit_log = AuditService.log_document_action(
        db=db,
        action=AuditService.ACTION_CREATE_DOCUMENT,
        user_id=user.id,
        document_id=123,
        additional_data={"filename": "test.pdf"},
    )

    assert audit_log.action == AuditService.ACTION_CREATE_DOCUMENT
    assert audit_log.resource_type == AuditService.RESOURCE_DOCUMENT
    assert audit_log.resource_id == "123"


def test_log_question_action(db):
    """Test logging question actions"""
    user = create_test_user(db)

    audit_log = AuditService.log_question_action(
        db=db,
        action=AuditService.ACTION_APPROVE_QUESTION,
        user_id=user.id,
        question_id=456,
        additional_data={"reason": "Looks good"},
    )

    assert audit_log.action == AuditService.ACTION_APPROVE_QUESTION
    assert audit_log.resource_type == AuditService.RESOURCE_QUESTION
    assert audit_log.resource_id == "456"


# ============================================================================
# Security Event Logging Tests
# ============================================================================


def test_log_permission_denied(db):
    """Test logging permission denied events"""
    user = create_test_user(db)

    audit_log = AuditService.log_permission_denied(
        db=db,
        user_id=user.id,
        action="create_document",
        required_permission="create_documents",
    )

    assert audit_log.action == AuditService.ACTION_PERMISSION_DENIED
    assert audit_log.status == AuditService.STATUS_FAILURE
    assert audit_log.user_id == user.id


def test_log_rate_limit_exceeded(db):
    """Test logging rate limit exceeded events"""
    audit_log = AuditService.log_rate_limit_exceeded(db=db, limit_type="ip")

    assert audit_log.action == AuditService.ACTION_RATE_LIMIT_EXCEEDED
    assert audit_log.status == AuditService.STATUS_FAILURE


# ============================================================================
# Audit Log Query Tests
# ============================================================================


def test_query_audit_logs_by_user(db):
    """Test querying audit logs by user"""
    user = create_test_user(db)

    # Create multiple audit logs
    AuditService.log_login(db, user.id, success=True)
    AuditService.log_logout(db, user.id)
    AuditService.log_password_change(db, user.id, success=True)

    # Query logs for this user
    logs = db.query(AuditLog).filter(AuditLog.user_id == user.id).all()

    assert len(logs) == 3


def test_query_audit_logs_by_action(db):
    """Test querying audit logs by action type"""
    user = create_test_user(db)

    # Create multiple login attempts
    AuditService.log_login(db, user.id, success=True)
    AuditService.log_login(db, user.id, success=False, error_message="Wrong password")
    AuditService.log_logout(db, user.id)

    # Query only login actions
    login_logs = (
        db.query(AuditLog).filter(AuditLog.action == AuditService.ACTION_LOGIN).all()
    )

    assert len(login_logs) == 2


def test_query_failed_login_attempts(db):
    """Test querying failed login attempts for security monitoring"""
    user = create_test_user(db)

    # Create failed login attempts
    for i in range(3):
        AuditService.log_login(
            db, user.id, success=False, error_message="Wrong password"
        )

    # Query failed logins
    failed_logins = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == AuditService.ACTION_LOGIN,
            AuditLog.status == AuditService.STATUS_FAILURE,
        )
        .all()
    )

    assert len(failed_logins) == 3


def test_audit_log_timestamp(db):
    """Test that audit logs have timestamps"""
    user = create_test_user(db)

    audit_log = AuditService.log_login(db, user.id, success=True)

    assert audit_log.created_at is not None
    # Timestamp should be recent (within last minute)
    time_diff = datetime.now(timezone.utc) - audit_log.created_at
    assert time_diff.total_seconds() < 60
