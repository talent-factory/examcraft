"""
Tests for the Avatar Proxy endpoint GET /api/auth/avatar/{user_id}

Covers the route itself: user lookup, error codes and content-type
detection. Download, Redis caching and TTL live in AvatarService and are
covered by test_avatar_service.py, so AvatarService is mocked here.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus

AVATAR_URL = "https://lh3.googleusercontent.com/a/test-avatar"


@pytest.fixture
def db(test_db):
    institution = Institution(
        name="Avatar Test University",
        slug="avatar-test-university",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(institution)
    test_db.commit()
    yield test_db


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def _create_user(db, avatar_url):
    institution = db.query(Institution).filter_by(slug="avatar-test-university").one()
    user = User(
        email="avatar@avatar-test-university.ch",
        first_name="Avatar",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        avatar_url=avatar_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_unknown_user_returns_404(client):
    with patch("api.auth.AvatarService") as service_cls:
        response = client.get("/api/auth/avatar/999999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "auth_user_not_found"
    service_cls.assert_not_called()


def test_user_without_avatar_url_returns_404(client, db):
    user = _create_user(db, avatar_url=None)

    with patch("api.auth.AvatarService") as service_cls:
        response = client.get(f"/api/auth/avatar/{user.id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "auth_avatar_not_found"
    service_cls.assert_not_called()


def test_failed_download_returns_502(client, db):
    user = _create_user(db, avatar_url=AVATAR_URL)

    with patch("api.auth.AvatarService") as service_cls:
        service_cls.return_value.get_avatar.return_value = None
        response = client.get(f"/api/auth/avatar/{user.id}")

    assert response.status_code == 502
    assert response.json()["error_code"] == "auth_avatar_download_failed"


@pytest.mark.parametrize(
    "image_bytes, content_type",
    [
        (b"\x89PNG\r\n\x1a\n-png-data", "image/png"),
        (b"GIF89a-gif-data", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBP-webp-data", "image/webp"),
        (b"\xff\xd8\xff\xe0-jpeg-data", "image/jpeg"),
    ],
)
def test_returns_avatar_with_detected_content_type(
    client, db, image_bytes, content_type
):
    user = _create_user(db, avatar_url=AVATAR_URL)

    with patch("api.auth.AvatarService") as service_cls:
        service_cls.return_value.get_avatar.return_value = image_bytes
        response = client.get(f"/api/auth/avatar/{user.id}")

    assert response.status_code == 200
    assert response.content == image_bytes
    assert response.headers["content-type"] == content_type
    assert response.headers["cache-control"] == "public, max-age=86400"
    service_cls.return_value.get_avatar.assert_called_once_with(user.id, AVATAR_URL)
