"""
Tests für Authentication Service
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from services.auth_service import AuthService
from models.auth import User, UserSession, UserStatus, Institution


@pytest.fixture
def test_institution(test_db: Session):
    """Create test institution"""
    institution = Institution(
        name="Test University",
        slug="test-university",
        domain="test.edu",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(institution)
    test_db.commit()
    test_db.refresh(institution)
    return institution


@pytest.fixture
def test_user(test_db: Session, test_institution: Institution):
    """Create test user"""
    user = User(
        email="test@example.com",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Test",
        last_name="User",
        institution_id=test_institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = AuthService.get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "testpassword123"
        hashed = AuthService.get_password_hash(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = AuthService.get_password_hash(password)

        assert AuthService.verify_password(wrong_password, hashed) is False

    def test_hash_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes"""
        password1 = "password1"
        password2 = "password2"

        hash1 = AuthService.get_password_hash(password1)
        hash2 = AuthService.get_password_hash(password2)

        assert hash1 != hash2

    def test_verify_password_with_malformed_hash_returns_false(self):
        """TF-758 review fix: a corrupted/malformed stored hash must fail
        closed -- like a wrong password -- rather than raise and turn into
        an unhandled 500 for whichever endpoint is checking a password
        (login, change-password, the impersonation step-up)."""
        assert (
            AuthService.verify_password("anything", "not-a-valid-bcrypt-hash") is False
        )

    def test_verify_password_with_overlong_password_returns_false(self):
        """bcrypt raises ValueError for plaintext passwords over 72 bytes --
        must also fail closed instead of propagating (TF-758)."""
        hashed = AuthService.get_password_hash("testpassword123")
        too_long = "x" * 200

        assert AuthService.verify_password(too_long, hashed) is False


class TestTokenCreation:
    """Test JWT token creation"""

    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)

        assert token is not None
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "123", "email": "test@example.com"}
        token = AuthService.create_refresh_token(data)

        assert token is not None
        assert len(token) > 0

    def test_create_token_with_custom_expiration(self):
        """Test token creation with custom expiration"""
        data = {"sub": "123"}
        expires_delta = timedelta(minutes=15)
        token = AuthService.create_access_token(data, expires_delta)

        payload = AuthService.decode_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_decode_valid_token(self):
        """Test decoding valid token"""
        data = {"sub": "123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)

        payload = AuthService.decode_token(token)

        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        payload = AuthService.decode_token(invalid_token)

        assert payload is None

    def test_refresh_token_has_type_field(self):
        """Test that refresh token has type field"""
        data = {"sub": "123"}
        token = AuthService.create_refresh_token(data)

        payload = AuthService.decode_token(token)

        assert payload is not None
        assert payload.get("type") == "refresh"


class TestUserTokens:
    """Test token creation for users"""

    def test_create_tokens_for_user(self, test_db: Session, test_user: User):
        """Test creating tokens for a user"""
        tokens = AuthService.create_tokens_for_user(
            test_user, test_db, user_agent="Test Browser", ip_address="127.0.0.1"
        )

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"

        # Verify tokens can be decoded
        access_payload = AuthService.decode_token(tokens["access_token"])
        refresh_payload = AuthService.decode_token(tokens["refresh_token"])

        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["sub"] == str(test_user.id)
        assert access_payload["email"] == test_user.email

    def test_create_tokens_creates_session(self, test_db: Session, test_user: User):
        """Test that creating tokens creates a session record"""
        AuthService.create_tokens_for_user(
            test_user, test_db, user_agent="Test Browser", ip_address="127.0.0.1"
        )

        # Check session was created
        session = (
            test_db.query(UserSession)
            .filter(UserSession.user_id == test_user.id)
            .first()
        )

        assert session is not None
        assert session.user_agent == "Test Browser"
        assert session.ip_address == "127.0.0.1"
        assert session.is_active is True


class TestTokenRefresh:
    """Test token refresh functionality"""

    def test_refresh_access_token(self, test_db: Session, test_user: User):
        """Test refreshing access token"""
        # Create initial tokens
        tokens = AuthService.create_tokens_for_user(test_user, test_db)
        refresh_token = tokens["refresh_token"]

        # Refresh access token
        new_tokens = AuthService.refresh_access_token(refresh_token, test_db)

        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert "token_type" in new_tokens

        # Verify new token is different
        assert new_tokens["access_token"] != tokens["access_token"]

    def test_refresh_with_invalid_token(self, test_db: Session):
        """Test refresh with invalid token"""
        invalid_token = "invalid.token.here"
        result = AuthService.refresh_access_token(invalid_token, test_db)

        assert result is None

    def test_refresh_with_access_token_fails(self, test_db: Session, test_user: User):
        """Test that refresh fails with access token (not refresh token)"""
        tokens = AuthService.create_tokens_for_user(test_user, test_db)
        access_token = tokens["access_token"]

        # Try to refresh with access token (should fail)
        result = AuthService.refresh_access_token(access_token, test_db)

        assert result is None


class TestTokenRevocation:
    """Test token revocation"""

    def test_revoke_token(self, test_db: Session, test_user: User):
        """Test revoking a token"""
        tokens = AuthService.create_tokens_for_user(test_user, test_db)
        access_payload = AuthService.decode_token(tokens["access_token"])
        token_jti = access_payload["jti"]

        # Revoke token
        result = AuthService.revoke_token(token_jti, test_db)

        assert result is True

        # Check token is revoked
        assert AuthService.is_token_revoked(token_jti, test_db) is True

    def test_revoke_nonexistent_token(self, test_db: Session):
        """Test revoking non-existent token"""
        result = AuthService.revoke_token("nonexistent-jti", test_db)

        assert result is False

    def test_revoke_all_user_sessions(self, test_db: Session, test_user: User):
        """Test revoking all sessions for a user"""
        # Create multiple sessions
        AuthService.create_tokens_for_user(test_user, test_db)
        AuthService.create_tokens_for_user(test_user, test_db)

        # Revoke all sessions
        count = AuthService.revoke_all_user_sessions(test_user.id, test_db)

        assert count == 2

        # Check all sessions are revoked
        sessions = (
            test_db.query(UserSession)
            .filter(UserSession.user_id == test_user.id, UserSession.is_active)
            .all()
        )

        assert len(sessions) == 0

    def test_is_token_revoked_for_active_token(self, test_db: Session, test_user: User):
        """Test checking if active token is revoked"""
        tokens = AuthService.create_tokens_for_user(test_user, test_db)
        access_payload = AuthService.decode_token(tokens["access_token"])
        token_jti = access_payload["jti"]

        assert AuthService.is_token_revoked(token_jti, test_db) is False


class TestImpersonationTokens:
    """Test impersonation token minting (TF-741)."""

    def test_create_impersonation_token_carries_target_and_impersonation_claims(
        self, test_db: Session, test_user: User
    ):
        tokens = AuthService.create_impersonation_token(
            test_user,
            test_db,
            impersonator_id=999,
            impersonation_session_id=42,
        )

        assert "access_token" in tokens
        assert "refresh_token" not in tokens
        assert tokens["token_type"] == "bearer"

        payload = AuthService.decode_token(tokens["access_token"])
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
        assert payload["impersonator_id"] == 999
        assert payload["impersonation_session_id"] == 42

    def test_create_impersonation_token_expires_in_30_minutes_hard_cap(
        self, test_db: Session, test_user: User
    ):
        from services.auth_service import IMPERSONATION_TOKEN_EXPIRE_MINUTES

        assert IMPERSONATION_TOKEN_EXPIRE_MINUTES == 30

        tokens = AuthService.create_impersonation_token(
            test_user, test_db, impersonator_id=999, impersonation_session_id=42
        )
        assert tokens["expires_in"] == 30 * 60

        payload = AuthService.decode_token(tokens["access_token"])
        lifetime_seconds = payload["exp"] - payload["iat"]
        assert abs(lifetime_seconds - 30 * 60) < 5

    def test_create_impersonation_token_creates_session_without_refresh_jti(
        self, test_db: Session, test_user: User
    ):
        """No refresh token means no refresh_token_jti — otherwise the shared
        /auth/refresh endpoint could mint an uncapped, un-flagged access
        token for the target user and defeat the 30-minute hard cap.
        """
        tokens = AuthService.create_impersonation_token(
            test_user, test_db, impersonator_id=999, impersonation_session_id=42
        )
        access_payload = AuthService.decode_token(tokens["access_token"])

        session = (
            test_db.query(UserSession)
            .filter(UserSession.token_jti == access_payload["jti"])
            .first()
        )
        assert session is not None
        assert session.user_id == test_user.id
        assert session.refresh_token_jti is None
        assert session.is_active is True

    def test_impersonation_token_can_be_revoked_via_existing_mechanism(
        self, test_db: Session, test_user: User
    ):
        tokens = AuthService.create_impersonation_token(
            test_user, test_db, impersonator_id=999, impersonation_session_id=42
        )
        access_payload = AuthService.decode_token(tokens["access_token"])
        token_jti = access_payload["jti"]

        assert AuthService.is_token_revoked(token_jti, test_db) is False
        assert AuthService.revoke_token(token_jti, test_db) is True
        assert AuthService.is_token_revoked(token_jti, test_db) is True


class TestPasswordLockout:
    """TF-758: the shared failed-attempt lockout used by both POST
    /auth/login and the impersonation step-up in api/admin.py."""

    def test_fresh_user_is_not_locked_out(self, test_user: User):
        assert AuthService.is_locked_out(test_user) is False

    def test_not_locked_out_below_the_threshold(self, test_user: User):
        test_user.failed_login_attempts = AuthService.MAX_FAILED_PASSWORD_ATTEMPTS - 1
        test_user.last_failed_login = datetime.now(timezone.utc)

        assert AuthService.is_locked_out(test_user) is False

    def test_locked_out_at_the_threshold_within_the_window(self, test_user: User):
        test_user.failed_login_attempts = AuthService.MAX_FAILED_PASSWORD_ATTEMPTS
        test_user.last_failed_login = datetime.now(timezone.utc)

        assert AuthService.is_locked_out(test_user) is True

    def test_not_locked_out_once_the_window_has_elapsed(self, test_user: User):
        test_user.failed_login_attempts = AuthService.MAX_FAILED_PASSWORD_ATTEMPTS
        test_user.last_failed_login = datetime.now(timezone.utc) - timedelta(
            seconds=AuthService.PASSWORD_LOCKOUT_DURATION_SECONDS + 1
        )

        assert AuthService.is_locked_out(test_user) is False

    def test_record_failed_attempt_increments_counter_and_persists(
        self, test_db: Session, test_user: User
    ):
        AuthService.record_failed_own_password_attempt(test_user, test_db)

        assert test_user.failed_login_attempts == 1
        assert test_user.last_failed_login is not None

        test_db.refresh(test_user)
        assert test_user.failed_login_attempts == 1

    def test_repeated_failed_attempts_eventually_lock_the_account(
        self, test_db: Session, test_user: User
    ):
        for _ in range(AuthService.MAX_FAILED_PASSWORD_ATTEMPTS):
            AuthService.record_failed_own_password_attempt(test_user, test_db)

        assert AuthService.is_locked_out(test_user) is True

    def test_reset_clears_the_counter(self, test_db: Session, test_user: User):
        test_user.failed_login_attempts = AuthService.MAX_FAILED_PASSWORD_ATTEMPTS
        test_user.last_failed_login = datetime.now(timezone.utc)
        test_db.commit()

        AuthService.reset_failed_own_password_attempts(test_user, test_db)

        assert test_user.failed_login_attempts == 0
        assert test_user.last_failed_login is None
        assert AuthService.is_locked_out(test_user) is False
