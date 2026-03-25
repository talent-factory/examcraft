"""
Tests for Security Features (PR #41)
Account lockout, password validation, OAuth CSRF, OAuth code exchange, JWT key validation
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import User, Role, Institution, UserStatus, UserRole
from services.auth_service import AuthService


# ============================================================================
# Fixtures (following test_auth_api.py patterns)
# ============================================================================


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

    # Register only the auth router (avoids celery import from documents)
    from api import auth

    app.include_router(auth.router)

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user with active status"""
    institution = db.query(Institution).first()
    viewer_role = db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()

    user = User(
        email="security@example.com",
        password_hash=AuthService.get_password_hash("ValidPass123"),
        first_name="Security",
        last_name="Tester",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
        failed_login_attempts=0,
        last_failed_login=None,
    )
    db.add(user)
    db.flush()

    user.roles.append(viewer_role)
    db.commit()
    db.refresh(user)

    return user


# ============================================================================
# TestAccountLockout
# ============================================================================


class TestAccountLockout:
    """Test account lockout after MAX_FAILED_ATTEMPTS (10) with 30-minute lockout."""

    def test_lockout_after_max_failed_attempts(self, test_client, db, test_user):
        """Account should be locked after 10 failed login attempts."""
        # Simulate 10 failed attempts directly on the user record
        test_user.failed_login_attempts = 10
        test_user.last_failed_login = datetime.now(timezone.utc)
        db.commit()

        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "security@example.com",
                "password": "ValidPass123",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 429
        detail = response.json()["detail"]
        assert "gesperrt" in detail or "locked" in detail

    def test_lockout_not_triggered_below_max(self, test_client, db, test_user):
        """Account should NOT be locked with fewer than 10 failed attempts."""
        test_user.failed_login_attempts = 9
        test_user.last_failed_login = datetime.now(timezone.utc)
        db.commit()

        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "security@example.com",
                "password": "ValidPass123",  # pragma: allowlist secret
            },
        )

        # Should succeed (correct password, under threshold)
        assert response.status_code == 200

    def test_lockout_expires_after_duration(self, test_client, db, test_user):
        """Account should be accessible after lockout period (30 min) expires."""
        test_user.failed_login_attempts = 10
        # Set last_failed_login to 31 minutes ago (past lockout duration)
        test_user.last_failed_login = datetime.now(timezone.utc) - timedelta(minutes=31)
        db.commit()

        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "security@example.com",
                "password": "ValidPass123",  # pragma: allowlist secret
            },
        )

        # Lockout expired, correct password -> success
        assert response.status_code == 200

    def test_null_last_failed_login_treated_as_locked(self, test_client, db, test_user):
        """NULL last_failed_login with >= MAX attempts should be treated as locked."""
        test_user.failed_login_attempts = 10
        test_user.last_failed_login = None  # NULL from migration
        db.commit()

        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "security@example.com",
                "password": "ValidPass123",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 429
        detail = response.json()["detail"]
        assert "gesperrt" in detail or "locked" in detail

    def test_counter_reset_after_lockout_expires(self, test_client, db, test_user):
        """Failed attempt counter should reset after lockout period expires."""
        test_user.failed_login_attempts = 10
        test_user.last_failed_login = datetime.now(timezone.utc) - timedelta(minutes=31)
        db.commit()

        # Login with correct password (lockout expired -> counter resets)
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "security@example.com",
                "password": "ValidPass123",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 200

        # Verify counter was reset
        db.refresh(test_user)
        assert test_user.failed_login_attempts == 0

    def test_failed_attempt_increments_counter(self, test_client, db, test_user):
        """Each failed login should increment the counter."""
        assert test_user.failed_login_attempts == 0

        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "security@example.com",
                "password": "WrongPassword1",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 401

        db.refresh(test_user)
        assert test_user.failed_login_attempts == 1
        assert test_user.last_failed_login is not None


# ============================================================================
# TestPasswordValidation
# ============================================================================


class TestPasswordValidation:
    """Test password strength validation via _validate_password_strength."""

    def test_register_password_no_uppercase(self, test_client):
        """Registration should fail if password has no uppercase letter."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "weakpw1@example.com",
                "password": "nouppercase1",  # pragma: allowlist secret
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("Grossbuchstaben" in str(err) for err in detail)

    def test_register_password_no_lowercase(self, test_client):
        """Registration should fail if password has no lowercase letter."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "weakpw2@example.com",
                "password": "NOLOWERCASE1",  # pragma: allowlist secret
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("Kleinbuchstaben" in str(err) for err in detail)

    def test_register_password_no_digit(self, test_client):
        """Registration should fail if password has no digit."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "weakpw3@example.com",
                "password": "NoDigitHere",  # pragma: allowlist secret
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("Zahl" in str(err) for err in detail)

    def test_register_password_too_short(self, test_client):
        """Registration should fail if password is shorter than 8 chars."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "weakpw4@example.com",
                "password": "Ab1",  # pragma: allowlist secret
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 422

    def test_register_password_valid(self, test_client):
        """Registration should succeed with a strong password."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "strongpw@example.com",
                "password": "StrongPass1",  # pragma: allowlist secret
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 201

    def test_change_password_weak_rejected(self, test_client, test_user):
        """Password change should reject a weak new password."""
        # Login first
        login_response = test_client.post(
            "/api/auth/login",
            json={
                "email": "security@example.com",
                "password": "ValidPass123",  # pragma: allowlist secret
            },
        )
        access_token = login_response.json()["access_token"]

        response = test_client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "ValidPass123",  # pragma: allowlist secret
                "new_password": "nouppercasenodigit",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 422


# ============================================================================
# TestOAuthProviderValidation
# ============================================================================


class TestOAuthProviderValidation:
    """Test OAuth provider validation in oauth_login and oauth_callback."""

    def test_oauth_login_unsupported_provider(self, test_client):
        """oauth_login should reject unsupported providers."""
        response = test_client.get(
            "/api/auth/oauth/github/login", follow_redirects=False
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "nicht unterstützt" in detail or "Unsupported" in detail

    def test_oauth_callback_unsupported_provider(self, test_client):
        """oauth_callback should reject unsupported providers."""
        response = test_client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "test_code", "state": "test_state"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "nicht unterstützt" in detail or "Unsupported" in detail

    @patch("api.auth.RedisService.get_session_client")
    def test_oauth_login_supported_provider_google(self, mock_redis_cls, test_client):
        """oauth_login should accept 'google' as a valid provider (and attempt redirect)."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis

        # The request will fail at OAuthService level but should NOT fail at provider validation
        response = test_client.get(
            "/api/auth/oauth/google/login", follow_redirects=False
        )

        # Should not be 400 (provider validation passed)
        assert response.status_code != 400 or "Unsupported" not in response.json().get(
            "detail", ""
        )

    @patch("api.auth.RedisService.get_session_client")
    def test_oauth_callback_missing_state(self, mock_redis_cls, test_client):
        """oauth_callback should reject requests without state parameter."""
        response = test_client.get(
            "/api/auth/oauth/google/callback",
            params={"code": "test_code"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "fehlt" in detail or "Missing" in detail

    @patch("api.auth.RedisService.get_session_client")
    def test_oauth_callback_invalid_state(self, mock_redis_cls, test_client):
        """oauth_callback should reject invalid/expired state tokens (CSRF protection)."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        # getdel returns None -> state not found in Redis
        mock_redis.getdel.return_value = None

        response = test_client.get(
            "/api/auth/oauth/google/callback",
            params={"code": "test_code", "state": "invalid_state_token"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "CSRF" in detail or "Invalid" in detail or "Ungültiger" in detail


# ============================================================================
# TestOAuthCodeExchange
# ============================================================================


class TestOAuthCodeExchange:
    """Test exchange_oauth_code endpoint for single-use OAuth codes."""

    @patch("api.auth.RedisService.get_session_client")
    def test_exchange_valid_code(self, mock_redis_cls, test_client):
        """Should return tokens for a valid, unused OAuth code."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis

        token_data = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "bearer",
        }
        mock_redis.getdel.return_value = json.dumps(token_data)

        response = test_client.post(
            "/api/auth/oauth/exchange",
            json={"code": "valid_oauth_code"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test_access_token"
        assert data["refresh_token"] == "test_refresh_token"
        assert data["token_type"] == "bearer"

        # Verify getdel was called with correct key
        mock_redis.getdel.assert_called_once_with("oauth_code:valid_oauth_code")

    @patch("api.auth.RedisService.get_session_client")
    def test_exchange_expired_code(self, mock_redis_cls, test_client):
        """Should return 400 for an expired or already-used code."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        mock_redis.getdel.return_value = None  # Code not found / expired

        response = test_client.post(
            "/api/auth/oauth/exchange",
            json={"code": "expired_code"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Ungültiger" in detail or "Invalid or expired" in detail

    @patch("api.auth.RedisService.get_session_client")
    def test_exchange_invalid_code(self, mock_redis_cls, test_client):
        """Should return 400 for a completely invalid code."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        mock_redis.getdel.return_value = None

        response = test_client.post(
            "/api/auth/oauth/exchange",
            json={"code": "nonexistent_code_xyz"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Ungültiger" in detail or "Invalid or expired" in detail

    @patch("api.auth.RedisService.get_session_client")
    def test_exchange_malformed_json_in_redis(self, mock_redis_cls, test_client):
        """Should return 500 when Redis contains malformed JSON for the code."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        mock_redis.getdel.return_value = "not-valid-json{{{{"

        response = test_client.post(
            "/api/auth/oauth/exchange",
            json={"code": "malformed_code"},
        )

        assert response.status_code == 500
        assert "nicht gelesen" in response.json()["detail"]

    @patch("api.auth.RedisService.get_session_client")
    def test_exchange_redis_unavailable(self, mock_redis_cls, test_client):
        """Should return 503 when Redis is unavailable."""
        mock_redis_cls.side_effect = Exception("Redis connection refused")

        response = test_client.post(
            "/api/auth/oauth/exchange",
            json={"code": "any_code"},
        )

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "nicht verfügbar" in detail or "Service unavailable" in detail

    @patch("api.auth.RedisService.get_session_client")
    def test_exchange_code_is_single_use(self, mock_redis_cls, test_client):
        """Code should be consumed (deleted) after first use via getdel."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis

        token_data = json.dumps(
            {
                "access_token": "tok",
                "refresh_token": "ref",
                "token_type": "bearer",
            }
        )
        # First call returns data, second returns None (already consumed)
        mock_redis.getdel.side_effect = [token_data, None]

        # First exchange succeeds
        response1 = test_client.post(
            "/api/auth/oauth/exchange",
            json={"code": "single_use_code"},
        )
        assert response1.status_code == 200

        # Second exchange fails (code already consumed)
        response2 = test_client.post(
            "/api/auth/oauth/exchange",
            json={"code": "single_use_code"},
        )
        assert response2.status_code == 400


# ============================================================================
# TestJWTKeyValidation
# ============================================================================


class TestJWTKeyValidation:
    """Test that AuthService raises RuntimeError without JWT key in production."""

    def test_missing_jwt_key_in_production_raises_error(self):
        """Should raise RuntimeError when JWT_SECRET_KEY is empty in production."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "",
                "ENVIRONMENT": "production",
                "DEPLOYMENT_MODE": "core",
            },
            clear=False,
        ):
            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                # Re-execute the module-level code that checks the key
                import importlib
                import services.auth_service

                importlib.reload(services.auth_service)

    def test_missing_jwt_key_in_full_mode_raises_error(self):
        """Should raise RuntimeError when JWT_SECRET_KEY is empty in full deployment mode."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "",
                "ENVIRONMENT": "development",
                "DEPLOYMENT_MODE": "full",
            },
            clear=False,
        ):
            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                import importlib
                import services.auth_service

                importlib.reload(services.auth_service)

    def test_missing_jwt_key_in_development_uses_default(self):
        """Should NOT raise in development mode, uses insecure default instead."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "",
                "ENVIRONMENT": "development",
                "DEPLOYMENT_MODE": "core",
            },
            clear=False,
        ):
            import importlib
            import services.auth_service

            # Should not raise, just warn
            importlib.reload(services.auth_service)
            assert services.auth_service.SECRET_KEY == (
                "insecure-dev-default-do-not-use-in-production"
            )

    def test_jwt_key_set_uses_provided_value(self):
        """Should use the provided JWT_SECRET_KEY when set."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "my-secure-secret-key-for-testing"  # pragma: allowlist secret
            },
            clear=False,
        ):
            import importlib
            import services.auth_service

            importlib.reload(services.auth_service)
            assert (
                services.auth_service.SECRET_KEY
                == "my-secure-secret-key-for-testing"  # pragma: allowlist secret
            )
