"""
Tests for GET /api/auth/avatar/{user_id}: user lookup, error codes and
serving of the stored picture. There is no download fallback
(EXAMCRAFT-168): ``avatar_url`` is never fetched here.
"""

from unittest.mock import patch

import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient

from database import get_db
from utils.auth_utils import get_current_active_user
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
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(
        id=-1, is_superuser=True, institution_id=None
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_active_user, None)


def _create_user(db, avatar_url, avatar_data=None, content_type=None):
    institution = db.query(Institution).filter_by(slug="avatar-test-university").one()
    user = User(
        email="avatar@avatar-test-university.ch",
        first_name="Avatar",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        avatar_url=avatar_url,
        avatar_data=avatar_data,
        avatar_content_type=content_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_unknown_user_returns_404(client):
    response = client.get("/api/auth/avatar/999999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "auth_user_not_found"


def test_user_without_stored_picture_returns_404(client, db):
    user = _create_user(db, avatar_url=None)

    response = client.get(f"/api/auth/avatar/{user.id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "auth_avatar_not_found"


@pytest.mark.parametrize(
    "url",
    [
        AVATAR_URL,
        "http://127.0.0.1:8000/internal",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_avatar_url_is_never_fetched(client, db, url):
    """Legacy rows with only an avatar_url get a 404, no outbound request."""
    user = _create_user(db, avatar_url=url)

    with patch("httpx.Client") as http_client, patch("httpx.get") as http_get:
        response = client.get(f"/api/auth/avatar/{user.id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "auth_avatar_not_found"
    http_client.assert_not_called()
    http_get.assert_not_called()


def test_serves_stored_picture(client, db):
    user = _create_user(
        db, avatar_url=AVATAR_URL, avatar_data=b"\x89PNG-data", content_type="image/png"
    )

    response = client.get(f"/api/auth/avatar/{user.id}")

    assert response.status_code == 200
    assert response.content == b"\x89PNG-data"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"].startswith("private")
