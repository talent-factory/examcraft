"""
Tests for OAuth Service - User Data Update Functionality

Tests TF-192: OAuth Login should update user data (first_name, last_name, avatar_url)
"""

import pytest
from sqlalchemy.orm import Session

from models.auth import User, OAuthAccount, Institution
from services.oauth_service import OAuthService


@pytest.fixture
def test_institution(db_session: Session):
    """Create a test institution"""
    institution = Institution(
        name="Test Institution",
        slug="test-institution",
        subscription_tier="free",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    return institution


@pytest.fixture
def oauth_service(db_session: Session):
    """Create OAuth service instance"""
    return OAuthService(db_session)


def test_oauth_updates_existing_user_with_null_fields(
    db_session: Session, test_institution: Institution, oauth_service: OAuthService
):
    """Test that OAuth login updates existing user with NULL fields"""
    # 1. Create user with email only (NULL first_name, last_name, avatar_url)
    user = User(
        email="test@example.com",
        first_name=None,  # NULL
        last_name=None,  # NULL
        avatar_url=None,  # NULL
        institution_id=test_institution.id,
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id

    # 2. Simulate OAuth login with Google
    user_info = {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "name": "John Doe",
        "picture": "https://example.com/photo.jpg",
        "provider_user_id": "google-123",
    }
    token = {"access_token": "token123", "refresh_token": "refresh123"}

    updated_user = oauth_service.find_or_create_user_from_oauth(
        provider="google", user_info=user_info, token=token
    )

    # 3. Assert user data was updated
    assert updated_user.id == user_id
    assert updated_user.first_name == "John"
    assert updated_user.last_name == "Doe"
    assert updated_user.display_name == "John Doe"
    assert updated_user.avatar_url == "https://example.com/photo.jpg"
    assert updated_user.oauth_provider == "google"
    assert updated_user.is_email_verified is True

    # 4. Assert OAuth account was created
    oauth_account = (
        db_session.query(OAuthAccount).filter(OAuthAccount.user_id == user_id).first()
    )
    assert oauth_account is not None
    assert oauth_account.provider == "google"
    assert oauth_account.provider_user_id == "google-123"


def test_oauth_refreshes_profile_data_on_subsequent_login(
    db_session: Session, test_institution: Institution, oauth_service: OAuthService
):
    """Test that OAuth login refreshes profile data (e.g., changed avatar)"""
    # 1. Create user with OAuth account
    user = User(
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        display_name="John Doe",
        avatar_url="https://old-avatar.jpg",
        institution_id=test_institution.id,
        oauth_provider="google",
    )
    db_session.add(user)
    db_session.flush()

    oauth_account = OAuthAccount(
        user_id=user.id,
        provider="google",
        provider_user_id="google-123",
        access_token="old_token",
        email="test@example.com",
        name="John Doe",
        picture="https://old-avatar.jpg",
    )
    db_session.add(oauth_account)
    db_session.commit()
    user_id = user.id

    # 2. Simulate second OAuth login with updated avatar
    user_info = {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "name": "John Doe",
        "picture": "https://new-avatar.jpg",  # Changed!
        "provider_user_id": "google-123",
    }
    token = {"access_token": "new_token", "refresh_token": "new_refresh"}

    updated_user = oauth_service.find_or_create_user_from_oauth(
        provider="google", user_info=user_info, token=token
    )

    # 3. Assert avatar was updated
    assert updated_user.id == user_id
    assert updated_user.avatar_url == "https://new-avatar.jpg"
    assert updated_user.first_name == "John"
    assert updated_user.last_name == "Doe"

    # 4. Assert OAuth account token was refreshed
    refreshed_oauth = (
        db_session.query(OAuthAccount).filter(OAuthAccount.user_id == user_id).first()
    )
    assert refreshed_oauth.access_token == "new_token"
    assert refreshed_oauth.picture == "https://new-avatar.jpg"
