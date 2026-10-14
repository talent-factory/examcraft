"""
Login tracking and the "last login" shown in the profile (TF-1060).

Every login stamps ``last_login_at`` *before* the frontend loads ``/auth/me``,
so the profile shows ``previous_login_at`` instead: the login before the
current one. All token-issuing paths go through ``AuthService.record_login``.
"""

import json
import pathlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.auth import UserProfileResponse
from models.auth import User
from services.auth_service import AuthService

from tests import test_auth_api

# Shares the client, DB and user setup with the auth API tests. Assigned
# rather than imported by name: as parameters they would trip ruff's F811.
db = test_auth_api.db
test_client = test_auth_api.test_client
test_user = test_auth_api.test_user

EARLIER_LOGIN = datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc)


def _fixture_path() -> pathlib.Path | None:
    """``core/frontend/src/__fixtures__/authMe.response.json`` — or ``None``.

    Searches upwards instead of counting parents: in the ``core/`` mirror the
    frontend lives under ``frontend/``, and in the api container ``/app`` is
    already ``core/backend`` with no frontend mounted at all.
    """
    here = pathlib.Path(__file__).resolve()
    for base in here.parents:
        for rel in ("core/frontend/src", "frontend/src"):
            cand = base / rel / "__fixtures__" / "authMe.response.json"
            if cand.is_file():
                return cand
    return None


class TestRecordLogin:
    def test_first_login_has_no_previous(self, db, test_user):
        AuthService.record_login(test_user, "203.0.113.1")

        assert test_user.previous_login_at is None
        assert test_user.last_login_at is not None
        assert test_user.last_login_ip == "203.0.113.1"

    def test_second_login_moves_first_to_previous(self, db, test_user):
        AuthService.record_login(test_user, "203.0.113.1")
        db.commit()
        first = test_user.last_login_at

        AuthService.record_login(test_user, "203.0.113.2")
        db.commit()
        db.refresh(test_user)

        assert test_user.previous_login_at == first
        assert test_user.last_login_at > first
        assert test_user.last_login_ip == "203.0.113.2"


class TestLoginEndpoints:
    def test_password_login_records_previous_login(self, test_client, db, test_user):
        test_user.last_login_at = EARLIER_LOGIN
        db.commit()

        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )

        assert response.status_code == 200
        db.refresh(test_user)
        assert test_user.previous_login_at == EARLIER_LOGIN
        assert test_user.last_login_at > EARLIER_LOGIN

    @patch("api.auth.RedisService.get_session_client")
    @patch("api.auth.OAuthService")
    def test_oauth_callback_records_previous_login(
        self, mock_oauth_cls, mock_redis_cls, test_client, db, test_user
    ):
        test_user.last_login_at = EARLIER_LOGIN
        db.commit()
        mock_redis_cls.return_value = MagicMock(getdel=MagicMock(return_value="1"))
        oauth = mock_oauth_cls.return_value
        oauth.exchange_code_for_token = AsyncMock(return_value={"access_token": "x"})
        oauth.get_user_info = AsyncMock(return_value={"email": test_user.email})
        oauth.find_or_create_user_from_oauth.return_value = test_user

        response = test_client.get(
            "/api/auth/oauth/google/callback",
            params={"code": "c", "state": "s"},
            follow_redirects=False,
        )

        assert response.status_code == 307, response.text
        db.refresh(test_user)
        assert test_user.previous_login_at == EARLIER_LOGIN
        assert test_user.last_login_at > EARLIER_LOGIN

    def test_registration_counts_as_first_login(self, test_client, db):
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "neu@test.edu",
                "password": "SecurePass123!",
                "first_name": "Neu",
                "last_name": "Person",
            },
        )

        assert response.status_code == 201, response.text
        user = db.query(User).filter(User.email == "neu@test.edu").one()
        assert user.last_login_at is not None
        assert user.previous_login_at is None


class TestProfileResponse:
    def test_me_returns_previous_login_with_offset(self, test_client, db, test_user):
        test_user.last_login_at = EARLIER_LOGIN
        db.commit()
        token = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        ).json()["access_token"]

        data = test_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        ).json()

        assert datetime.fromisoformat(data["previous_login_at"]) == EARLIER_LOGIN
        assert data["previous_login_at"].endswith("+00:00")

    def test_me_returns_null_on_first_login(self, test_client, test_user):
        token = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        ).json()["access_token"]

        data = test_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        ).json()

        assert data["previous_login_at"] is None

    def test_frontend_fixture_matches_response_model(self):
        """The fixture ProfileView.lastLogin.test.tsx renders must be a valid /auth/me.

        Exact key equality on top of validation: a field the backend adds or
        drops would otherwise leave the frontend test rendering a response the
        backend no longer sends.
        """
        path = _fixture_path()
        if path is None:
            pytest.skip("core/frontend/src not available (api container)")
        payload = json.loads(path.read_text(encoding="utf-8"))

        UserProfileResponse.model_validate(payload)
        assert set(payload) == set(UserProfileResponse.model_fields)
        assert datetime.fromisoformat(payload["previous_login_at"]).utcoffset() == (
            timedelta(0)
        )
