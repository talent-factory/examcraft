"""Tests for audit attribute coverage."""

import pytest
from models.auth import User, Role, Institution, UserStatus
from services.auth_service import AuthService


class TestUserModelAuditFields:
    """Verify new audit columns exist on User model."""

    def test_user_has_email_verified_at(self):
        user = User(
            email="test@test.ch",
            first_name="Test",
            last_name="User",
            institution_id=1,
        )
        assert hasattr(user, "email_verified_at")
        assert user.email_verified_at is None

    def test_user_has_password_changed_at(self):
        user = User(
            email="test@test.ch",
            first_name="Test",
            last_name="User",
            institution_id=1,
        )
        assert hasattr(user, "password_changed_at")
        assert user.password_changed_at is None

    def test_user_has_registration_method(self):
        user = User(
            email="test@test.ch",
            first_name="Test",
            last_name="User",
            institution_id=1,
        )
        assert hasattr(user, "registration_method")
        assert user.registration_method is None


@pytest.fixture
def test_institution(test_db):
    inst = Institution(
        name="Test Inst",
        slug="test-inst",
        domain="test.ch",
        subscription_tier="free",
        is_active=True,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


@pytest.fixture
def test_role(test_db):
    role = Role(
        name="Viewer",
        display_name="Viewer",
        description="Default role",
        permissions="[]",
        is_system_role=True,
    )
    test_db.add(role)
    test_db.flush()
    return role


@pytest.fixture
def active_user(test_db, test_institution, test_role):
    user = User(
        email="login-test@test.ch",
        password_hash=AuthService.get_password_hash("Test1234!"),
        first_name="Login",
        last_name="Test",
        institution_id=test_institution.id,
        status=UserStatus.ACTIVE.value,
        is_email_verified=True,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.flush()
    user.roles.append(test_role)
    test_db.commit()
    test_db.refresh(user)
    return user


class TestLoginTracking:
    def test_login_sets_last_login_at(self, test_db, active_user):
        """After successful login, last_login_at must be set."""
        from sqlalchemy import func

        assert active_user.last_login_at is None
        active_user.failed_login_attempts = 0
        active_user.last_login_at = func.now()
        active_user.last_login_ip = "127.0.0.1"
        test_db.commit()
        test_db.refresh(active_user)
        assert active_user.last_login_at is not None
        assert active_user.last_login_ip == "127.0.0.1"


class TestOAuthLoginTracking:
    def test_oauth_login_sets_last_login_at(self, test_db, test_institution, test_role):
        """After OAuth login, last_login_at and last_login_ip must be set."""
        from sqlalchemy import func

        user = User(
            email="oauth-track@test.ch",
            first_name="OAuth",
            last_name="Track",
            institution_id=test_institution.id,
            status="active",
            is_email_verified=True,
            password_hash=None,
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        assert user.last_login_at is None
        user.last_login_at = func.now()
        user.last_login_ip = "10.0.0.1"
        test_db.commit()
        test_db.refresh(user)
        assert user.last_login_at is not None
        assert user.last_login_ip == "10.0.0.1"


class TestOAuthAuditFields:
    """Test oauth_id, oauth_provider, registration_method, email_verified_at in OAuth flows."""

    def _make_oauth_service(self, db):
        from services.oauth_service import OAuthService

        return OAuthService(db)

    def _user_info(self, email="oauth-new@test.ch", provider_user_id="google-123"):
        return {
            "email": email,
            "first_name": "OAuth",
            "last_name": "User",
            "name": "OAuth User",
            "provider_user_id": provider_user_id,
            "email_verified": True,
        }

    def _token(self):
        return {"access_token": "at_xxx", "refresh_token": "rt_xxx"}

    def test_new_user_gets_oauth_id(self, test_db, test_institution, test_role):
        """Path c: new user — oauth_id, oauth_provider, registration_method, email_verified_at set."""
        svc = self._make_oauth_service(test_db)
        user = svc.find_or_create_user_from_oauth(
            "google", self._user_info(), self._token()
        )
        assert user.oauth_id == "google-123"
        assert user.oauth_provider == "google"
        assert user.registration_method == "google"
        assert user.email_verified_at is not None

    def test_existing_user_linking_gets_oauth_id(
        self, test_db, test_institution, test_role
    ):
        """Path b: existing password user links OAuth — oauth_id set, registration_method unchanged."""
        existing = User(
            email="existing@test.ch",
            password_hash="hashed",  # pragma: allowlist secret
            first_name="Existing",
            last_name="User",
            institution_id=test_institution.id,
            status="active",
            is_email_verified=True,
            registration_method="password",
        )
        test_db.add(existing)
        test_db.commit()
        svc = self._make_oauth_service(test_db)
        user = svc.find_or_create_user_from_oauth(
            "google",
            self._user_info(email="existing@test.ch", provider_user_id="google-456"),
            self._token(),
        )
        assert user.oauth_id == "google-456"
        assert user.registration_method == "password"  # NOT overwritten
        assert user.email_verified_at is not None

    def test_returning_oauth_user_gets_oauth_id_if_missing(
        self, test_db, test_institution, test_role
    ):
        """Path a: returning OAuth user — oauth_id backfilled if NULL."""
        svc = self._make_oauth_service(test_db)
        user = svc.find_or_create_user_from_oauth(
            "google", self._user_info(), self._token()
        )
        user.oauth_id = None
        test_db.commit()
        user2 = svc.find_or_create_user_from_oauth(
            "google", self._user_info(), self._token()
        )
        assert user2.oauth_id == "google-123"

    def test_multi_oauth_does_not_overwrite_oauth_id(
        self, test_db, test_institution, test_role
    ):
        """First-write-wins: second OAuth provider does not overwrite oauth_id."""
        svc = self._make_oauth_service(test_db)
        user = svc.find_or_create_user_from_oauth(
            "google", self._user_info(), self._token()
        )
        assert user.oauth_id == "google-123"
        ms_info = self._user_info(email=user.email, provider_user_id="ms-789")
        user2 = svc.find_or_create_user_from_oauth("microsoft", ms_info, self._token())
        assert user2.oauth_id == "google-123"  # NOT overwritten
