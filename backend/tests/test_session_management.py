"""
Tests for Session Management
Tests Redis session store, token blacklist, and session cleanup
"""

import time
import uuid

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


class _OwnRedisKeys:
    """Hands out collision-free IDs and remembers the Redis keys they map to.

    Since TF-816 sessions, blacklist, rate limiting, MCP OAuth, ops alerts and
    activity presence all share Redis DB 0, and a local run may point at the
    dev Redis. The tests therefore never flush: every ID is unique per test
    and the teardown deletes exactly the keys handed out here.
    """

    def __init__(self):
        self.keys: list[str] = []

    def session_id(self) -> str:
        session_id = f"test-session-{uuid.uuid4().hex}"
        self.keys.append(f"session:{session_id}")
        return session_id

    def user_id(self) -> int:
        # Far above any real users.id, so user_sessions:{id} never hits dev data.
        user_id = 10**12 + uuid.uuid4().int % 10**9
        self.keys.append(f"user_sessions:{user_id}")
        return user_id

    def token_jti(self) -> str:
        token_jti = f"test-jti-{uuid.uuid4().hex}"
        self.keys.append(f"blacklist:{token_jti}")
        return token_jti


@pytest.fixture
def own_keys():
    """Real Redis (CI provides a service container), cleaned up key by key.

    No skip when Redis is unreachable: ``ping()`` raises and the test errors.
    A skip used to hide that these tests had not run since TF-816.
    """
    client = RedisService.get_session_client()
    client.ping()
    keys = _OwnRedisKeys()
    yield keys
    if keys.keys:
        client.delete(*keys.keys)


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


def test_create_session(own_keys):
    """Test creating a session in Redis"""
    session_store = SessionStore()
    client = RedisService.get_session_client()
    session_id = own_keys.session_id()
    user_id = own_keys.user_id()

    result = session_store.create_session(
        session_id=session_id,
        user_id=user_id,
        data={"email": "test@example.com", "ip_address": "192.168.1.1"},
        ttl_seconds=3600,
    )

    assert result is True
    assert 0 < client.ttl(f"session:{session_id}") <= 3600
    assert session_id in client.smembers(f"user_sessions:{user_id}")


def test_get_session(own_keys):
    """Test retrieving a session from Redis"""
    session_store = SessionStore()
    session_id = own_keys.session_id()
    user_id = own_keys.user_id()

    session_store.create_session(session_id, user_id, {"email": "test@example.com"})
    retrieved_data = session_store.get_session(session_id)

    assert retrieved_data == {"user_id": user_id, "email": "test@example.com"}


def test_delete_session(own_keys):
    """Test deleting a session from Redis"""
    session_store = SessionStore()
    client = RedisService.get_session_client()
    session_id = own_keys.session_id()
    user_id = own_keys.user_id()
    session_store.create_session(session_id, user_id, {})

    result = session_store.delete_session(session_id)

    assert result is True
    assert session_store.get_session(session_id) is None
    assert session_id not in client.smembers(f"user_sessions:{user_id}")


def test_delete_user_sessions(own_keys):
    """Test deleting all sessions for a user"""
    session_store = SessionStore()
    client = RedisService.get_session_client()
    user_id = own_keys.user_id()
    session_id1 = own_keys.session_id()
    session_id2 = own_keys.session_id()
    session_store.create_session(session_id1, user_id, {})
    session_store.create_session(session_id2, user_id, {})

    count = session_store.delete_user_sessions(user_id)

    assert count == 2
    assert session_store.get_session(session_id1) is None
    assert session_store.get_session(session_id2) is None
    assert client.exists(f"user_sessions:{user_id}") == 0


def test_extend_session(own_keys):
    """Test extending session TTL"""
    session_store = SessionStore()
    client = RedisService.get_session_client()
    session_id = own_keys.session_id()
    session_store.create_session(session_id, own_keys.user_id(), {}, ttl_seconds=60)

    result = session_store.extend_session(session_id, 3600)

    assert result is True
    assert client.ttl(f"session:{session_id}") > 60
    # A session that does not exist cannot be extended
    assert session_store.extend_session(own_keys.session_id(), 3600) is False


def test_session_expiration(own_keys):
    """Test that sessions expire after TTL"""
    session_store = SessionStore()
    session_id = own_keys.session_id()
    session_store.create_session(session_id, own_keys.user_id(), {}, ttl_seconds=1)

    # Session should exist immediately
    assert session_store.get_session(session_id) is not None

    time.sleep(1.5)

    assert session_store.get_session(session_id) is None


# ============================================================================
# Token Blacklist Tests
# ============================================================================


def test_add_token_to_blacklist(own_keys):
    """Test adding a token to the blacklist"""
    blacklist = TokenBlacklist()
    client = RedisService.get_blacklist_client()
    token_jti = own_keys.token_jti()

    result = blacklist.add_token(token_jti, ttl_seconds=3600)

    assert result is True
    assert 0 < client.ttl(f"blacklist:{token_jti}") <= 3600


def test_is_token_blacklisted(own_keys):
    """Test checking if a token is blacklisted"""
    blacklist = TokenBlacklist()
    token_jti = own_keys.token_jti()

    # Token should not be blacklisted initially
    assert blacklist.is_token_blacklisted(token_jti) is False

    blacklist.add_token(token_jti, 3600)

    assert blacklist.is_token_blacklisted(token_jti) is True


def test_blacklist_expiration(own_keys):
    """Test that blacklisted tokens expire after TTL"""
    blacklist = TokenBlacklist()
    token_jti = own_keys.token_jti()
    blacklist.add_token(token_jti, 1)

    # Token should be blacklisted immediately
    assert blacklist.is_token_blacklisted(token_jti) is True

    time.sleep(1.5)

    assert blacklist.is_token_blacklisted(token_jti) is False


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
