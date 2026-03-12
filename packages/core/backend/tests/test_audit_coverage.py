"""Tests for audit attribute coverage."""

from models.auth import User


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
