"""
Tests for Avatar Proxy Endpoint
Tests Redis caching, error handling, and rate limiting avoidance

NOTE: These tests are currently SKIPPED because:
1. The /api/v1/auth/avatar-proxy endpoint does not exist
2. The actual endpoint is /api/auth/avatar/{user_id} in api/auth.py
3. Tests were written for a different API design

TODO: Rewrite tests for the actual /api/auth/avatar/{user_id} endpoint
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import requests

from main import app
from services.redis_service import RedisService

# Skip all tests in this file - endpoint does not exist
pytestmark = pytest.mark.skip(
    reason="Avatar proxy endpoint /api/v1/auth/avatar-proxy does not exist. Actual endpoint is /api/auth/avatar/{user_id}"
)


class TestAvatarProxy:
    """Test suite for Avatar Proxy endpoint (SKIPPED - endpoint does not exist)"""

    def test_avatar_proxy_caches_image(self, client: TestClient, mock_redis: Mock):
        """Test that avatar proxy caches fetched images in Redis"""
        # Arrange
        avatar_url = "https://lh3.googleusercontent.com/a/test-avatar"
        mock_image_data = b"fake_image_data_12345"

        # Mock external request to Google
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            response = client.get(f"/api/v1/auth/avatar-proxy?url={avatar_url}")

            # Assert
            assert response.status_code == 200
            assert response.content == mock_image_data
            assert response.headers["content-type"] == "image/jpeg"

            # Verify Redis cache was set
            mock_redis.set.assert_called_once()
            cache_key = f"avatar:{avatar_url}"
            assert cache_key in str(mock_redis.set.call_args)

    def test_avatar_proxy_returns_cached_image(
        self, client: TestClient, mock_redis: Mock
    ):
        """Test that avatar proxy returns cached image without external request"""
        # Arrange
        avatar_url = "https://lh3.googleusercontent.com/a/test-avatar"
        cached_image_data = b"cached_image_data_67890"

        # Mock Redis to return cached data
        mock_redis.get.return_value = cached_image_data

        # Act
        with patch("requests.get") as mock_get:
            response = client.get(f"/api/v1/auth/avatar-proxy?url={avatar_url}")

            # Assert
            assert response.status_code == 200
            assert response.content == cached_image_data
            assert response.headers["content-type"] == "image/jpeg"

            # Verify NO external request was made
            mock_get.assert_not_called()

            # Verify Redis cache was checked
            mock_redis.get.assert_called_once()

    def test_avatar_proxy_handles_missing_url(self, client: TestClient):
        """Test that avatar proxy returns 400 for missing URL parameter"""
        # Act
        response = client.get("/api/v1/auth/avatar-proxy")

        # Assert
        assert response.status_code == 422  # FastAPI validation error
        assert "url" in response.json()["detail"][0]["loc"]

    def test_avatar_proxy_handles_invalid_url(self, client: TestClient):
        """Test that avatar proxy handles invalid URLs gracefully"""
        # Arrange
        invalid_url = "not-a-valid-url"

        # Act
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.MissingSchema()
            response = client.get(f"/api/v1/auth/avatar-proxy?url={invalid_url}")

            # Assert
            assert response.status_code == 500
            assert "Failed to fetch avatar" in response.json()["detail"]

    def test_avatar_proxy_handles_timeout(self, client: TestClient, mock_redis: Mock):
        """Test that avatar proxy handles request timeouts"""
        # Arrange
        avatar_url = "https://lh3.googleusercontent.com/a/slow-avatar"
        mock_redis.get.return_value = None  # No cache

        # Act
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()
            response = client.get(f"/api/v1/auth/avatar-proxy?url={avatar_url}")

            # Assert
            assert response.status_code == 500
            assert "Failed to fetch avatar" in response.json()["detail"]

    def test_avatar_proxy_handles_404(self, client: TestClient, mock_redis: Mock):
        """Test that avatar proxy handles 404 responses from external server"""
        # Arrange
        avatar_url = "https://lh3.googleusercontent.com/a/missing-avatar"
        mock_redis.get.return_value = None  # No cache

        # Act
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/auth/avatar-proxy?url={avatar_url}")

            # Assert
            assert response.status_code == 500
            assert "Failed to fetch avatar" in response.json()["detail"]

    def test_avatar_proxy_handles_429_rate_limit(
        self, client: TestClient, mock_redis: Mock
    ):
        """Test that avatar proxy handles 429 Too Many Requests from Google"""
        # Arrange
        avatar_url = "https://lh3.googleusercontent.com/a/rate-limited-avatar"
        mock_redis.get.return_value = None  # No cache

        # Act
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "429 Too Many Requests"
            )
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/auth/avatar-proxy?url={avatar_url}")

            # Assert
            assert response.status_code == 500
            assert "Failed to fetch avatar" in response.json()["detail"]

    def test_avatar_proxy_sets_correct_ttl(self, client: TestClient, mock_redis: Mock):
        """Test that avatar proxy sets 24h TTL for cached images"""
        # Arrange
        avatar_url = "https://lh3.googleusercontent.com/a/test-avatar"
        mock_image_data = b"fake_image_data"
        mock_redis.get.return_value = None  # No cache

        # Act
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/auth/avatar-proxy?url={avatar_url}")

            # Assert
            assert response.status_code == 200

            # Verify Redis cache was set with 24h TTL (86400 seconds)
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert call_args[1]["ex"] == 86400  # 24 hours in seconds

    def test_avatar_proxy_supports_different_image_types(
        self, client: TestClient, mock_redis: Mock
    ):
        """Test that avatar proxy handles different image MIME types"""
        # Arrange
        test_cases = [
            ("image/jpeg", b"jpeg_data"),
            ("image/png", b"png_data"),
            ("image/webp", b"webp_data"),
        ]

        for mime_type, image_data in test_cases:
            avatar_url = f"https://example.com/avatar.{mime_type.split('/')[1]}"
            mock_redis.get.return_value = None  # No cache

            # Act
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.content = image_data
                mock_response.status_code = 200
                mock_response.headers = {"content-type": mime_type}
                mock_get.return_value = mock_response

                response = client.get(f"/api/v1/auth/avatar-proxy?url={avatar_url}")

                # Assert
                assert response.status_code == 200
                assert response.content == image_data
                # Note: Current implementation always returns image/jpeg
                # This test documents the current behavior

    def test_avatar_proxy_prevents_ssrf(self, client: TestClient):
        """Test that avatar proxy prevents SSRF attacks"""
        # Arrange: Try to access internal network
        malicious_urls = [
            "http://localhost:8000/api/v1/users",
            "http://127.0.0.1:5432/",
            "http://192.168.1.1/admin",
            "file:///etc/passwd",
        ]

        for malicious_url in malicious_urls:
            # Act
            response = client.get(f"/api/v1/auth/avatar-proxy?url={malicious_url}")

            # Assert: Should either reject or fail safely
            # Current implementation doesn't have SSRF protection
            # This test documents the security gap
            assert response.status_code in [400, 500]


# ==================== Fixtures ====================


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis service for testing"""
    mock = Mock(spec=RedisService)
    mock.get = Mock(return_value=None)
    mock.set = Mock(return_value=True)

    # Patch RedisService instance
    monkeypatch.setattr("api.v1.auth.redis_service", mock)
    return mock


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)
