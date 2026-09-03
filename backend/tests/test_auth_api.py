"""
Tests for Auth API Endpoints
Tests registration, login, logout, password change, etc.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import User, Role, Institution, UserStatus, UserRole
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
# is ALSO unreliable here specifically: main.py's lifespan handler loads
# api/auth.py a second time via importlib under the module name
# "core_api_auth" (see project_api_import_sysmodules_prod_only) and
# registers ITS router with `app` -- a distinct module object with its own
# `logger`, never registered in sys.modules and therefore not reachable by
# name from a test. Once any earlier test in the same pytest process
# triggers app startup (e.g. any test using `with TestClient(app):`),
# core_api_auth's router route wins over the plain `api.auth` router this
# file's own `test_client` fixture registers (Starlette matches the first
# route added for a given path), so a request can silently be served by
# either module instance depending on test run order.
#
# Patching logging.Logger.warning/.info at the class level sidesteps the
# whole problem: it intercepts every Logger instance's calls process-wide
# for the scope of the `with` block, regardless of which duplicate module
# instance is actually holding the logger.


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
