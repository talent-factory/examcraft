"""
Tests for Session Management
Tests Redis session store, token blacklist, and session cleanup
"""

import pytest
from datetime import datetime, timezone, timedelta

from models.auth import User, Role, Institution, UserStatus, UserRole, UserSession
from services.auth_service import AuthService
from services.redis_service import RedisService, SessionStore, TokenBlacklist


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

    # Create viewer role
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


@pytest.fixture
def redis_service():
    """Create Redis service instance"""
    try:
        service = RedisService()
        # Clear test data
        service.session_db.flushdb()
        service.blacklist_db.flushdb()
        service.rate_limit_db.flushdb()
        yield service
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


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
# Session Store Tests
# ============================================================================


def test_create_session(redis_service):
    """Test creating a session in Redis"""
    session_store = SessionStore(redis_service.session_db)

    session_data = {
        "user_id": 123,
        "email": "test@example.com",
        "ip_address": "192.168.1.1",
    }

    session_id = session_store.create_session(
        user_id=123, session_data=session_data, ttl_seconds=3600
    )

    assert session_id is not None
    assert len(session_id) > 0


def test_get_session(redis_service):
    """Test retrieving a session from Redis"""
    session_store = SessionStore(redis_service.session_db)

    session_data = {"user_id": 123, "email": "test@example.com"}

    session_id = session_store.create_session(123, session_data, 3600)
    retrieved_data = session_store.get_session(session_id)

    assert retrieved_data is not None
    assert retrieved_data["user_id"] == 123
    assert retrieved_data["email"] == "test@example.com"


def test_delete_session(redis_service):
    """Test deleting a session from Redis"""
    session_store = SessionStore(redis_service.session_db)

    session_data = {"user_id": 123}
    session_id = session_store.create_session(123, session_data, 3600)

    # Delete session
    result = session_store.delete_session(session_id)
    assert result is True

    # Session should no longer exist
    retrieved_data = session_store.get_session(session_id)
    assert retrieved_data is None


def test_delete_user_sessions(redis_service):
    """Test deleting all sessions for a user"""
    session_store = SessionStore(redis_service.session_db)

    # Create multiple sessions for same user
    session_data = {"user_id": 123}
    session_id1 = session_store.create_session(123, session_data, 3600)
    session_id2 = session_store.create_session(123, session_data, 3600)

    # Delete all sessions for user
    count = session_store.delete_user_sessions(123)
    assert count == 2

    # Sessions should no longer exist
    assert session_store.get_session(session_id1) is None
    assert session_store.get_session(session_id2) is None


def test_extend_session(redis_service):
    """Test extending session TTL"""
    session_store = SessionStore(redis_service.session_db)

    session_data = {"user_id": 123}
    session_id = session_store.create_session(123, session_data, 60)  # 1 minute

    # Extend session
    result = session_store.extend_session(session_id, 3600)  # Extend to 1 hour
    assert result is True


def test_session_expiration(redis_service):
    """Test that sessions expire after TTL"""
    import time

    session_store = SessionStore(redis_service.session_db)

    session_data = {"user_id": 123}
    session_id = session_store.create_session(123, session_data, 1)  # 1 second TTL

    # Session should exist immediately
    assert session_store.get_session(session_id) is not None

    # Wait for expiration
    time.sleep(2)

    # Session should be expired
    assert session_store.get_session(session_id) is None


# ============================================================================
# Token Blacklist Tests
# ============================================================================


def test_add_token_to_blacklist(redis_service):
    """Test adding a token to the blacklist"""
    blacklist = TokenBlacklist(redis_service.blacklist_db)

    token = "test.jwt.token"
    result = blacklist.add_token(token, ttl_seconds=3600)

    assert result is True


def test_is_token_blacklisted(redis_service):
    """Test checking if a token is blacklisted"""
    blacklist = TokenBlacklist(redis_service.blacklist_db)

    token = "test.jwt.token"

    # Token should not be blacklisted initially
    assert blacklist.is_blacklisted(token) is False

    # Add to blacklist
    blacklist.add_token(token, 3600)

    # Token should now be blacklisted
    assert blacklist.is_blacklisted(token) is True


def test_blacklist_expiration(redis_service):
    """Test that blacklisted tokens expire after TTL"""
    import time

    blacklist = TokenBlacklist(redis_service.blacklist_db)

    token = "test.jwt.token"
    blacklist.add_token(token, 1)  # 1 second TTL

    # Token should be blacklisted immediately
    assert blacklist.is_blacklisted(token) is True

    # Wait for expiration
    time.sleep(2)

    # Token should no longer be blacklisted
    assert blacklist.is_blacklisted(token) is False


# ============================================================================
# Database Session Tests
# ============================================================================


def test_create_database_session(db):
    """Test creating a session in the database"""
    user = create_test_user(db)

    session = UserSession(
        user_id=user.id,
        token_jti="test_token_jti_123",  # Fixed: use token_jti instead of session_token
        refresh_token_jti="test_refresh_jti_123",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.is_active is True


def test_revoke_database_session(db):
    """Test revoking a session in the database"""
    user = create_test_user(db)

    session = UserSession(
        user_id=user.id,
        token_jti="test_token_jti_456",  # Fixed: use token_jti instead of session_token
        refresh_token_jti="test_refresh_jti_456",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(session)
    db.commit()

    # Revoke session
    session.is_active = False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()

    assert session.is_active is False
    assert session.revoked_at is not None


def test_query_active_sessions(db):
    """Test querying active sessions for a user"""
    user = create_test_user(db)

    # Create active session
    active_session = UserSession(
        user_id=user.id,
        token_jti="active_token_jti_789",  # Fixed: use token_jti
        refresh_token_jti="active_refresh_jti_789",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_active=True,
    )

    # Create revoked session
    revoked_session = UserSession(
        user_id=user.id,
        token_jti="revoked_token_jti_101",  # Fixed: use token_jti
        refresh_token_jti="revoked_refresh_jti_101",
        ip_address="192.168.1.2",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_active=False,
        revoked_at=datetime.now(timezone.utc),
    )

    db.add(active_session)
    db.add(revoked_session)
    db.commit()

    # Query only active sessions
    active_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.is_active)
        .all()
    )

    assert len(active_sessions) == 1
    assert (
        active_sessions[0].token_jti == "active_token_jti_789"
    )  # Fixed: use token_jti


def test_query_expired_sessions(db):
    """Test querying expired sessions"""
    user = create_test_user(db)

    # Create expired session
    expired_session = UserSession(
        user_id=user.id,
        token_jti="expired_token_jti_202",  # Fixed: use token_jti
        refresh_token_jti="expired_refresh_jti_202",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Already expired
        is_active=True,
    )

    # Create valid session
    valid_session = UserSession(
        user_id=user.id,
        token_jti="valid_token_jti_303",  # Fixed: use token_jti
        refresh_token_jti="valid_refresh_jti_303",
        ip_address="192.168.1.2",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_active=True,
    )

    db.add(expired_session)
    db.add(valid_session)
    db.commit()

    # Query expired sessions
    now = datetime.now(timezone.utc)
    expired_sessions = (
        db.query(UserSession)
        .filter(UserSession.expires_at < now, UserSession.is_active)
        .all()
    )

    assert len(expired_sessions) == 1
    assert (
        expired_sessions[0].token_jti == "expired_token_jti_202"
    )  # Fixed: use token_jti
