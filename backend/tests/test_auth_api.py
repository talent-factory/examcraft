"""
Tests for Auth API Endpoints
Tests registration, login, logout, password change, etc.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import (
    AuditLog,
    Institution,
    PasswordResetToken,
    Role,
    User,
    UserRole,
    UserSession,
    UserStatus,
)
from services.auth_service import AuthService


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

    # Create default roles (get_or_create to avoid duplicate key errors)
    role_defs = [
        {
            "name": UserRole.ADMIN.value,
            "display_name": "Admin",
            "description": "Full system access",
            "permissions": ["*"],
            "is_system_role": True,
        },
        {
            "name": UserRole.DOZENT.value,
            "display_name": "Dozent",
            "description": "Can create and manage questions",
            "permissions": [
                "create_questions",
                "approve_questions",
                "create_documents",
                "view_questions",
            ],
            "is_system_role": True,
        },
        {
            "name": UserRole.VIEWER.value,
            "display_name": "Viewer",
            "description": "Can view questions",
            "permissions": ["view_questions"],
            "is_system_role": True,
        },
    ]
    for role_def in role_defs:
        existing = test_db.query(Role).filter(Role.name == role_def["name"]).first()
        if not existing:
            test_db.add(Role(**role_def))

    test_db.commit()

    yield test_db


@pytest.fixture(scope="function")
def test_client(db):
    """Create test client with database override"""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Register routers manually (normally done in lifespan event)
    from api import documents, rag_exams, question_review, auth, admin, gdpr
    from api.v1 import rbac as rbac_api

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(gdpr.router)
    app.include_router(documents.router)
    app.include_router(rag_exams.router)
    app.include_router(rbac_api.router)
    app.include_router(question_review.router)

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user"""
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
# Registration Tests
# ============================================================================


def test_register_new_user(test_client, db):
    """Test successful user registration"""
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Verify user was created
    user = db.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.first_name == "New"
    assert user.last_name == "User"
    assert user.status == UserStatus.PENDING.value

    # Verify user has default role (dozent if available, else viewer)
    assert len(user.roles) == 1
    assert user.roles[0].name in (UserRole.DOZENT.value, UserRole.VIEWER.value)


def test_register_first_user_of_non_personal_institution_becomes_admin(test_client, db):
    """TF-410: the first user of a non-personal institution is made its admin.

    ``founder@test.edu`` domain-matches the seeded non-personal "Test University"
    (slug ``test-university``), which has no users yet — so the registrant must
    receive the ADMIN role, guaranteeing every institution has >=1 admin.
    """
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "founder@test.edu",
            "password": "SecurePass123!",
            "first_name": "Founder",
            "last_name": "Admin",
        },
    )

    assert response.status_code == 201
    user = db.query(User).filter(User.email == "founder@test.edu").first()
    assert user is not None
    assert [r.name for r in user.roles] == [UserRole.ADMIN.value]


def test_register_personal_institution_user_is_not_admin(test_client, db):
    """TF-410: a personal institution's user keeps the default (non-admin) role."""
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "solo@no-such-domain.example",
            "password": "SecurePass123!",
            "first_name": "Solo",
            "last_name": "User",
        },
    )

    assert response.status_code == 201
    user = db.query(User).filter(User.email == "solo@no-such-domain.example").first()
    assert user is not None
    assert UserRole.ADMIN.value not in [r.name for r in user.roles]


def test_register_duplicate_email(test_client, test_user):
    """Test registration with existing email fails"""
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "Duplicate",
            "last_name": "User",
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "bereits registriert" in detail or "already registered" in detail


def test_register_invalid_email(test_client):
    """Test registration with invalid email fails"""
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "invalid-email",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 422  # Validation error


# ============================================================================
# Login Tests
# ============================================================================


def test_login_success(test_client, test_user):
    """Test successful login"""
    response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(test_client, test_user):
    """Test login with wrong password fails"""
    response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    detail = response.json()["detail"].lower()
    assert "ungültige" in detail or "incorrect" in detail or "invalid" in detail


def test_login_nonexistent_user(test_client):
    """Test login with non-existent user fails"""
    response = test_client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    detail = response.json()["detail"].lower()
    assert "ungültige" in detail or "incorrect" in detail or "invalid" in detail


def test_login_inactive_user(test_client, db, test_user):
    """Test login with inactive user fails"""
    test_user.status = UserStatus.INACTIVE.value
    db.commit()

    response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    assert response.status_code == 403
    detail = response.json()["detail"].lower()
    assert "deaktiviert" in detail or "disabled" in detail or "inactive" in detail


# ============================================================================
# Token Refresh Tests
# ============================================================================


def test_refresh_token_success(test_client, test_user):
    """Test successful token refresh"""
    # Login to get tokens
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = test_client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_invalid(test_client):
    """Test refresh with invalid token fails"""
    response = test_client.post(
        "/api/auth/refresh", json={"refresh_token": "invalid.token.here"}
    )

    assert response.status_code == 401


# ============================================================================
# Logout Tests
# ============================================================================


def test_logout_success(test_client, test_user):
    """Test successful logout"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Logout
    response = test_client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 204


def test_logout_without_token(test_client):
    """Test logout without token fails"""
    response = test_client.post("/api/auth/logout")

    assert response.status_code == 401  # No credentials


# ============================================================================
# User Profile Tests
# ============================================================================


def test_get_profile_success(test_client, test_user):
    """Test getting current user profile"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Get profile
    response = test_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert "roles" in data


# ============================================================================
# Password Change Tests
# ============================================================================


def test_change_password_success(test_client, test_user, db):
    """Test successful password change"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Change password
    response = test_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "testpassword123",
            "new_password": "NewSecurePass456!",
        },
    )

    assert response.status_code == 204

    # Verify new password works
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "NewSecurePass456!"},
    )
    assert login_response.status_code == 200


def test_change_password_wrong_current(test_client, test_user):
    """Test password change with wrong current password fails"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Try to change password with wrong current password
    response = test_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current_password": "wrongpassword", "new_password": "NewSecurePass456!"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "falsch" in detail or "incorrect" in detail


def test_change_password_without_auth(test_client):
    """Test password change without authentication fails"""
    response = test_client.post(
        "/api/auth/change-password",
        json={
            "current_password": "testpassword123",
            "new_password": "NewSecurePass456!",
        },
    )

    assert response.status_code == 401  # No credentials


# ============================================================================
# TF-764: "skipped" email send (SUBSCRIBEFLOW_EMAILS_API_KEY unset) must be
# logged as a warning, not the same info line a real send would get -- this
# is precisely the silent-failure bug TF-764's "skipped" status check fixes.
# ============================================================================


# The three tests below patch logging.Logger.warning/.info at the CLASS
# level rather than on a specific module's `logger` object (and rather than
# using caplog).
#
# caplog relies on propagation from the named logger to the root logger,
# which is unreliable across the full backend test suite (some other test/
# module disables propagation depending on run order) -- see
# project_caplog_propagation_full_suite.
#
# Patching a specific module's `logger` attribute (e.g. "api.auth.logger")
# used to be unreliable here too: before TF-660 main.py's lifespan loaded
# api/auth.py a second time under the module name "core_api_auth" and
# registered ITS router with `app` -- a distinct module object with its own
# `logger`, never registered in sys.modules and therefore not reachable by
# name from a test. main.py now loads api/ modules under their canonical
# dotted names, so "api.auth" is a single object again.
#
# Patching logging.Logger.warning/.info at the class level is kept because
# it also sidesteps the caplog propagation problem above: it intercepts
# every Logger instance's calls process-wide for the scope of the `with`
# block.


def test_register_logs_warning_when_verification_email_skipped(test_client):
    with (
        patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", ""),
        patch("logging.Logger.warning") as mock_warning,
        patch("logging.Logger.info") as mock_info,
    ):
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "skipped-register@example.com",
                "password": "SecurePass123!",
                "first_name": "Skip",
                "last_name": "User",
            },
        )

    assert response.status_code == 201
    warning_text = "\n".join(
        str(arg) for call in mock_warning.call_args_list for arg in call.args
    )
    assert "Verification email NOT sent" in warning_text
    info_text = "\n".join(
        str(arg) for call in mock_info.call_args_list for arg in call.args
    )
    assert "Verification email sent" not in info_text


def test_verify_email_logs_warning_when_welcome_email_skipped(test_client, db):
    from models.auth import EmailVerificationToken

    with patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", ""):
        register_response = test_client.post(
            "/api/auth/register",
            json={
                "email": "skipped-verify@example.com",
                "password": "SecurePass123!",
                "first_name": "Skip",
                "last_name": "User",
            },
        )
        assert register_response.status_code == 201

        email_token = (
            db.query(EmailVerificationToken)
            .join(User)
            .filter(User.email == "skipped-verify@example.com")
            .first()
        )
        assert email_token is not None

        with (
            patch("logging.Logger.warning") as mock_warning,
            patch("logging.Logger.info") as mock_info,
        ):
            response = test_client.post(
                "/api/auth/verify-email", params={"token": email_token.token}
            )

    assert response.status_code == 200
    warning_text = "\n".join(
        str(arg) for call in mock_warning.call_args_list for arg in call.args
    )
    assert "Welcome email NOT sent" in warning_text
    info_text = "\n".join(
        str(arg) for call in mock_info.call_args_list for arg in call.args
    )
    assert "Welcome email sent" not in info_text


def test_resend_verification_logs_warning_when_email_skipped(test_client, test_user):
    with (
        patch("services.email_service.SUBSCRIBEFLOW_EMAILS_API_KEY", ""),
        patch("logging.Logger.warning") as mock_warning,
        patch("logging.Logger.info") as mock_info,
    ):
        response = test_client.post(
            "/api/auth/resend-verification",
            params={"email": test_user.email},
        )

    assert response.status_code == 200
    warning_text = "\n".join(
        str(arg) for call in mock_warning.call_args_list for arg in call.args
    )
    assert "Verification email NOT resent" in warning_text
    info_text = "\n".join(
        str(arg) for call in mock_info.call_args_list for arg in call.args
    )
    assert "Verification email resent" not in info_text


# ============================================================================
# Password Reset Tests (TF-768)
# ============================================================================


def _request_reset(test_client, email="test@example.com"):
    """POST /password-reset with the mail send mocked; returns (response, mock)."""
    with patch(
        "services.email_service.EmailService.send_password_reset_email",
        new_callable=AsyncMock,
    ) as send_mock:
        response = test_client.post("/api/auth/password-reset", json={"email": email})
    return response, send_mock


def _issue_token(test_client, email="test@example.com") -> str:
    """Request a reset and return the plaintext token that went into the mail."""
    response, send_mock = _request_reset(test_client, email)
    assert response.status_code == 204
    send_mock.assert_awaited_once()
    return send_mock.await_args.kwargs["reset_token"]


def _confirm(test_client, token, password="BrandNewPass456"):
    return test_client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": password},
    )


def test_password_reset_request_creates_hashed_token_and_sends_mail(
    test_client, test_user, db
):
    token = _issue_token(test_client)

    rows = db.query(PasswordResetToken).filter_by(user_id=test_user.id).all()
    assert len(rows) == 1
    # Only the hash is persisted, never the plaintext token
    assert rows[0].token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in rows[0].token_hash
    assert not rows[0].is_used
    assert rows[0].expires_at > datetime.now(timezone.utc)


def test_password_reset_request_unknown_email_is_indistinguishable(
    test_client, test_user, db
):
    known, _ = _request_reset(test_client, "test@example.com")
    unknown, send_mock = _request_reset(test_client, "nobody@example.com")

    assert known.status_code == unknown.status_code == 204
    assert known.content == unknown.content
    send_mock.assert_not_awaited()
    assert db.query(PasswordResetToken).count() == 1  # only the known user's


def test_password_reset_request_inactive_user_gets_no_token(test_client, test_user, db):
    test_user.status = UserStatus.SUSPENDED.value
    db.commit()

    response, send_mock = _request_reset(test_client)

    assert response.status_code == 204
    send_mock.assert_not_awaited()
    assert db.query(PasswordResetToken).count() == 0


def test_password_reset_request_invalid_email_rejected(test_client):
    response = test_client.post("/api/auth/password-reset", json={"email": "nope"})
    assert response.status_code == 422


def test_password_reset_request_invalidates_earlier_tokens(test_client, test_user, db):
    first = _issue_token(test_client)
    second = _issue_token(test_client)

    assert _confirm(test_client, first).status_code == 400
    assert _confirm(test_client, second).status_code == 204


def test_password_reset_request_rate_limited_silently(test_client, test_user, db):
    for _ in range(3):
        _issue_token(test_client)

    response, send_mock = _request_reset(test_client)

    # Same 204 as always (no signal to an attacker), but nothing is issued
    assert response.status_code == 204
    send_mock.assert_not_awaited()
    assert db.query(PasswordResetToken).count() == 3


def test_password_reset_email_failure_does_not_break_request(test_client, test_user):
    with patch(
        "services.email_service.EmailService.send_password_reset_email",
        new_callable=AsyncMock,
        side_effect=RuntimeError("SubscribeFlow down"),
    ):
        response = test_client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )
    assert response.status_code == 204


def test_password_reset_confirm_sets_password(test_client, test_user, db):
    token = _issue_token(test_client)

    response = _confirm(test_client, token)

    assert response.status_code == 204
    old = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert old.status_code == 401
    new = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "BrandNewPass456"},
    )
    assert new.status_code == 200
    row = db.query(PasswordResetToken).filter_by(user_id=test_user.id).one()
    assert row.is_used and row.used_at is not None


def test_password_reset_confirm_revokes_all_sessions(test_client, test_user, db):
    login = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert login.status_code == 200
    assert (
        db.query(UserSession).filter_by(user_id=test_user.id, is_active=True).count()
        >= 1
    )

    assert _confirm(test_client, _issue_token(test_client)).status_code == 204

    db.expire_all()
    assert (
        db.query(UserSession).filter_by(user_id=test_user.id, is_active=True).count()
        == 0
    )


def test_password_reset_confirm_writes_audit_log(test_client, test_user, db):
    assert _confirm(test_client, _issue_token(test_client)).status_code == 204

    entry = (
        db.query(AuditLog)
        .filter_by(action="password_reset", user_id=test_user.id)
        .one()
    )
    assert entry.status == "success"


def test_password_reset_confirm_token_is_single_use(test_client, test_user):
    token = _issue_token(test_client)

    assert _confirm(test_client, token).status_code == 204
    replay = _confirm(test_client, token, "AnotherPass789")

    assert replay.status_code == 400
    assert (
        test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "AnotherPass789"},
        ).status_code
        == 401
    )


def test_password_reset_confirm_expired_token_rejected(test_client, test_user, db):
    token = _issue_token(test_client)
    row = db.query(PasswordResetToken).filter_by(user_id=test_user.id).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert _confirm(test_client, token).status_code == 400
    assert (
        test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        ).status_code
        == 200
    )


def test_password_reset_confirm_unknown_token_rejected(test_client, test_user):
    assert _confirm(test_client, "not-a-real-token").status_code == 400


def test_password_reset_confirm_failure_modes_share_one_error(
    test_client, test_user, db
):
    """Unknown / used / expired must be indistinguishable (no oracle)."""
    used = _issue_token(test_client)
    assert _confirm(test_client, used).status_code == 204
    expired = _issue_token(test_client)
    db.query(PasswordResetToken).filter_by(
        token_hash=hashlib.sha256(expired.encode()).hexdigest()
    ).update({"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)})
    db.commit()

    bodies = {
        _confirm(test_client, t).content for t in (used, expired, "garbage-token")
    }
    assert len(bodies) == 1


def test_password_reset_confirm_weak_password_rejected_token_kept(
    test_client, test_user
):
    token = _issue_token(test_client)

    assert _confirm(test_client, token, "short1A").status_code == 422
    assert _confirm(test_client, token, "alllowercase123").status_code == 422
    # Validation failures must not burn the token
    assert _confirm(test_client, token).status_code == 204


def test_password_reset_confirm_inactive_user_rejected(test_client, test_user, db):
    token = _issue_token(test_client)
    test_user.status = UserStatus.SUSPENDED.value
    db.commit()

    assert _confirm(test_client, token).status_code == 400


def test_password_reset_request_pending_user_gets_no_token(test_client, test_user, db):
    test_user.status = UserStatus.PENDING.value
    db.commit()

    response, send_mock = _request_reset(test_client)

    assert response.status_code == 204
    send_mock.assert_not_awaited()
    assert db.query(PasswordResetToken).count() == 0


def test_password_reset_request_oauth_only_user_gets_no_token(
    test_client, test_user, db
):
    test_user.password_hash = None
    db.commit()

    response, send_mock = _request_reset(test_client)

    assert response.status_code == 204
    send_mock.assert_not_awaited()
    assert db.query(PasswordResetToken).count() == 0


def test_password_reset_request_rate_limit_is_per_user_and_windowed(
    test_client, test_user, db
):
    for _ in range(3):
        _issue_token(test_client)
    # Tokens older than one hour stop counting towards the cap
    for row in db.query(PasswordResetToken).all():
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db.commit()

    response, send_mock = _request_reset(test_client)

    assert response.status_code == 204
    send_mock.assert_awaited_once()


def test_password_reset_confirm_revokes_old_access_token(test_client, test_user):
    login = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    old_access = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {old_access}"}
    assert test_client.get("/api/auth/me", headers=headers).status_code == 200

    assert _confirm(test_client, _issue_token(test_client)).status_code == 204

    assert test_client.get("/api/auth/me", headers=headers).status_code == 401


def test_password_reset_confirm_clears_login_lockout(test_client, test_user, db):
    test_user.failed_login_attempts = 10
    test_user.last_failed_login = datetime.now(timezone.utc)
    db.commit()

    assert _confirm(test_client, _issue_token(test_client)).status_code == 204

    db.refresh(test_user)
    assert test_user.failed_login_attempts == 0
    assert test_user.last_failed_login is None
    login = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "BrandNewPass456"},
    )
    assert login.status_code == 200


def test_password_reset_confirm_lost_claim_race_is_rejected(test_client, test_user, db):
    """A concurrent confirm burns the token between our read and our claim."""
    token = _issue_token(test_client)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    def _burn_then_allow(user):
        db.query(PasswordResetToken).filter_by(token_hash=token_hash).update(
            {"is_used": True}
        )
        db.commit()
        return True

    with patch("api.auth._can_reset_password", side_effect=_burn_then_allow):
        response = _confirm(test_client, token)

    assert response.status_code == 400
    login = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert login.status_code == 200  # password untouched


def test_password_reset_confirm_survives_session_revocation_failure(
    test_client, test_user
):
    token = _issue_token(test_client)

    with patch(
        "api.auth.AuthService.revoke_all_user_sessions",
        side_effect=RuntimeError("redis down"),
    ):
        response = _confirm(test_client, token)

    # Password is already changed and the token burnt: no 500, no dead retry
    assert response.status_code == 204
    login = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "BrandNewPass456"},
    )
    assert login.status_code == 200


def test_password_reset_confirm_weak_password_leaves_password_unchanged(
    test_client, test_user
):
    token = _issue_token(test_client)

    assert _confirm(test_client, token, "short1A").status_code == 422

    login = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert login.status_code == 200


def test_delete_user_with_reset_and_verification_tokens_cascades(
    test_client, test_user, db
):
    """GDPR deletion: DB-level ON DELETE CASCADE must not be pre-empted by an
    ORM ``SET user_id = NULL`` on the NOT NULL token FK."""
    from models.auth import EmailVerificationToken

    _issue_token(test_client)
    db.add(
        EmailVerificationToken(
            user_id=test_user.id,
            token="verif-token-tf768",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    db.commit()
    user_id = test_user.id

    db.delete(test_user)
    db.commit()

    assert db.query(PasswordResetToken).filter_by(user_id=user_id).count() == 0
    assert db.query(EmailVerificationToken).filter_by(user_id=user_id).count() == 0


@pytest.mark.asyncio
async def test_send_password_reset_email_uses_template_and_confirm_url():
    from services.email_service import EmailService

    with patch.object(EmailService, "_send", new_callable=AsyncMock) as send:
        await EmailService.send_password_reset_email(
            email="a@example.com", first_name="Ann", reset_token="tok123"
        )

    kwargs = send.await_args.kwargs
    assert kwargs["template_slug"] == "password-reset"
    assert kwargs["to"] == "a@example.com"
    assert kwargs["variables"]["first_name"] == "Ann"
    assert kwargs["variables"]["reset_url"].endswith(
        "/auth/reset-password/confirm?token=tok123"
    )


def test_password_reset_undelivered_mail_does_not_consume_rate_limit(
    test_client, test_user, db
):
    """A failed send drops the token, so 3 failures do not lock the user out."""
    with (
        patch("database.SessionLocal", return_value=db),
        patch.object(db, "close"),
        patch(
            "services.email_service.EmailService.send_password_reset_email",
            new_callable=AsyncMock,
            side_effect=RuntimeError("SubscribeFlow down"),
        ),
    ):
        for _ in range(4):
            response = test_client.post(
                "/api/auth/password-reset", json={"email": "test@example.com"}
            )
            assert response.status_code == 204

    assert db.query(PasswordResetToken).count() == 0


def test_password_reset_skipped_send_discards_token(test_client, test_user, db):
    with (
        patch("database.SessionLocal", return_value=db),
        patch.object(db, "close"),
        patch(
            "services.email_service.EmailService.send_password_reset_email",
            new_callable=AsyncMock,
            return_value={"id": "test-email-id", "status": "skipped"},
        ),
    ):
        response = test_client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )

    assert response.status_code == 204
    assert db.query(PasswordResetToken).count() == 0


def test_password_reset_confirm_audit_failure_aborts_and_keeps_token(
    test_client, test_user, db
):
    token = _issue_token(test_client)

    with patch("api.auth.AuditService.log_action", return_value=None):
        response = _confirm(test_client, token)

    assert response.status_code == 500
    login = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert login.status_code == 200  # password unchanged
    # Token was not burnt: a retry succeeds
    assert _confirm(test_client, token).status_code == 204
