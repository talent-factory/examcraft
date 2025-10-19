"""
Tests für Authentication Service
"""

import pytest
from datetime import datetime, timedelta
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
        max_questions_per_month=1000
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
        is_superuser=False
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
            test_user,
            test_db,
            user_agent="Test Browser",
            ip_address="127.0.0.1"
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
        tokens = AuthService.create_tokens_for_user(
            test_user,
            test_db,
            user_agent="Test Browser",
            ip_address="127.0.0.1"
        )

        # Check session was created
        session = test_db.query(UserSession).filter(
            UserSession.user_id == test_user.id
        ).first()

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
        tokens1 = AuthService.create_tokens_for_user(test_user, test_db)
        tokens2 = AuthService.create_tokens_for_user(test_user, test_db)

        # Revoke all sessions
        count = AuthService.revoke_all_user_sessions(test_user.id, test_db)

        assert count == 2

        # Check all sessions are revoked
        sessions = test_db.query(UserSession).filter(
            UserSession.user_id == test_user.id,
            UserSession.is_active == True
        ).all()

        assert len(sessions) == 0

    def test_is_token_revoked_for_active_token(self, test_db: Session, test_user: User):
        """Test checking if active token is revoked"""
        tokens = AuthService.create_tokens_for_user(test_user, test_db)
        access_payload = AuthService.decode_token(tokens["access_token"])
        token_jti = access_payload["jti"]

        assert AuthService.is_token_revoked(token_jti, test_db) is False

