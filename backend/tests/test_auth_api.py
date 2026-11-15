"""
Tests for Auth API Endpoints (cookie session auth, EXAMCRAFT-125).

Registration, password login, refresh, password change/reset and e-mail
verification were removed with the switch to Zitadel; what remains here is
the session-cookie contract of ``/me`` and ``/logout`` plus data-model
guarantees around the auth tables.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import (
    AuthSession,
    Institution,
    PasswordResetToken,
    Role,
    User,
    UserRole,
    UserStatus,
)
from services import session_service
from services.auth_service import AuthService
from tests.conftest import login_headers


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
    from api import auth_oidc
    from api.v1 import rbac as rbac_api

    app.include_router(auth.router)
    app.include_router(auth_oidc.router)
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
# Removed endpoints stay removed
# ============================================================================


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/auth/register"),
        ("post", "/api/auth/refresh"),
        ("post", "/api/auth/change-password"),
        ("post", "/api/auth/set-password"),
        ("post", "/api/auth/password-reset"),
        ("post", "/api/auth/password-reset/confirm"),
        ("post", "/api/auth/verify-email"),
        ("post", "/api/auth/resend-verification"),
        ("post", "/api/auth/oauth/exchange"),
        ("get", "/api/auth/oauth/google/login"),
    ],
)
def test_removed_password_endpoints_are_gone(test_client, method, path):
    response = getattr(test_client, method)(path)

    assert response.status_code in (404, 405)


def test_password_login_is_gone(test_client, test_user):
    """POST /login is no longer a password login (only GET starts OIDC)."""
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    assert response.status_code == 405


# ============================================================================
# Logout Tests
# ============================================================================


def test_logout_success_ends_session(test_client, test_user, db):
    headers = login_headers(test_client, "test@example.com")
    assert test_client.get("/api/auth/me", headers=headers).status_code == 200

    response = test_client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 204
    assert db.query(AuthSession).filter_by(user_id=test_user.id).count() == 0
    # The old cookie is worthless now
    assert test_client.get("/api/auth/me", headers=headers).status_code == 401


def test_logout_without_session_is_idempotent(test_client):
    """Logging out without (or with an unknown) session is a no-op, not an error."""
    assert test_client.post("/api/v1/auth/logout").status_code == 204
    unknown = {"Cookie": f"{session_service.SESSION_COOKIE_NAME}=does-not-exist"}
    assert test_client.post("/api/v1/auth/logout", headers=unknown).status_code == 204


# ============================================================================
# User Profile Tests
# ============================================================================


def test_get_profile_success(test_client, test_user):
    """Test getting current user profile"""
    headers = login_headers(test_client, "test@example.com")

    response = test_client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert "roles" in data


def test_get_profile_without_cookie_is_unauthorized(test_client, test_user):
    assert test_client.get("/api/auth/me").status_code == 401


def test_get_profile_ignores_bearer_header(test_client, test_user):
    """Only the session cookie authenticates; a (former) JWT bearer does not."""
    token = AuthService.create_access_token({"sub": str(test_user.id)})

    response = test_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_get_profile_with_expired_session_is_unauthorized(test_client, test_user, db):
    token, _ = session_service.create_session(
        db, test_user.id, max_age=timedelta(seconds=-1)
    )

    response = test_client.get(
        "/api/auth/me",
        headers={"Cookie": f"{session_service.SESSION_COOKIE_NAME}={token}"},
    )

    assert response.status_code == 401


def test_get_profile_of_inactive_user_is_rejected(test_client, test_user, db):
    """User status is checked on every request (there is no sync with Zitadel)."""
    headers = login_headers(test_client, "test@example.com")
    test_user.status = UserStatus.INACTIVE.value
    db.commit()

    response = test_client.get("/api/auth/me", headers=headers)

    assert response.status_code in (401, 403)


# ============================================================================
# Email service
# ============================================================================


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


# ============================================================================
# Cascade on user deletion (GDPR)
# ============================================================================


def test_delete_user_with_tokens_and_sessions_cascades(test_client, test_user, db):
    """GDPR deletion: DB-level ON DELETE CASCADE must not be pre-empted by an
    ORM ``SET user_id = NULL`` on the NOT NULL token / session FKs."""
    from models.auth import EmailVerificationToken

    db.add(
        PasswordResetToken(
            user_id=test_user.id,
            token_hash="a" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    db.add(
        EmailVerificationToken(
            user_id=test_user.id,
            token="verif-token-tf768",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    db.commit()
    session_service.create_session(db, test_user.id)
    user_id = test_user.id

    db.delete(test_user)
    db.commit()

    assert db.query(PasswordResetToken).filter_by(user_id=user_id).count() == 0
    assert db.query(EmailVerificationToken).filter_by(user_id=user_id).count() == 0
    assert db.query(AuthSession).filter_by(user_id=user_id).count() == 0
