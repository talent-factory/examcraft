"""
Unit tests for AvatarService (services/avatar_service.py)

Covers caching (hit/miss), download (success/failure paths), and
cache invalidation. Redis and httpx are mocked — no real network or
Redis connection is required.
"""

import httpx
import pytest
from unittest.mock import MagicMock, patch

from services.avatar_service import AvatarService, AVATAR_CACHE_TTL


@pytest.fixture
def mock_redis_client(monkeypatch):
    """Patch RedisService.get_session_client to return a MagicMock client."""
    mock_client = MagicMock()
    mock_client.connection_pool.connection_kwargs = {}
    monkeypatch.setattr(
        "services.avatar_service.RedisService.get_session_client",
        lambda: mock_client,
    )
    return mock_client


@pytest.fixture
def service(mock_redis_client):
    return AvatarService()


class FakeHttpxClient:
    """Controllable stand-in for httpx.Client used as a context manager."""

    def __init__(self, *, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, url):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._response


def _make_response(status_code=200, content=b"image-bytes", content_type="image/png"):
    response = MagicMock()
    response.status_code = status_code
    response.content = content
    response.headers = {"content-type": content_type}
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


class TestGetAvatar:
    def test_cache_hit_returns_cached_bytes_without_download(self, service):
        cached_bytes = b"cached-avatar-bytes"
        with patch.object(service, "_get_cached_avatar", return_value=cached_bytes):
            with patch.object(service, "_download_avatar") as mock_download:
                result = service.get_avatar(1, "https://example.com/a.png")

        assert result == cached_bytes
        mock_download.assert_not_called()

    def test_cache_miss_downloads_and_caches(self, service):
        avatar_bytes = b"downloaded-bytes"
        with patch.object(service, "_get_cached_avatar", return_value=None):
            with patch.object(
                service, "_download_avatar", return_value=avatar_bytes
            ) as mock_download:
                with patch.object(service, "_cache_avatar") as mock_cache:
                    result = service.get_avatar(2, "https://example.com/b.png")

        assert result == avatar_bytes
        mock_download.assert_called_once_with("https://example.com/b.png")
        mock_cache.assert_called_once_with("avatar:2", avatar_bytes)

    def test_cache_miss_download_fails_returns_none(self, service):
        with patch.object(service, "_get_cached_avatar", return_value=None):
            with patch.object(service, "_download_avatar", return_value=None):
                with patch.object(service, "_cache_avatar") as mock_cache:
                    result = service.get_avatar(3, "https://example.com/c.png")

        assert result is None
        mock_cache.assert_not_called()


class TestGetCachedAvatar:
    def test_returns_cached_bytes(self, service, mock_redis_client):
        mock_redis_client.get.return_value = b"cached-data"

        result = service._get_cached_avatar("avatar:1")

        assert result == b"cached-data"
        mock_redis_client.get.assert_called_once_with("avatar:1")

    def test_returns_none_when_not_cached(self, service, mock_redis_client):
        mock_redis_client.get.return_value = None

        result = service._get_cached_avatar("avatar:1")

        assert result is None

    def test_returns_none_on_redis_exception(self, service, mock_redis_client):
        mock_redis_client.get.side_effect = RuntimeError("connection lost")

        result = service._get_cached_avatar("avatar:1")

        assert result is None

    def test_sets_decode_responses_false_on_connection_kwargs(
        self, service, mock_redis_client
    ):
        """Documents current behaviour, not a correctness guarantee: this only
        mutates `connection_kwargs` for connections the pool creates *after*
        this call. Already-pooled connections from the shared session-client
        singleton keep their original `decode_responses=True` encoder, so
        binary avatar bytes can still round-trip as `str` in production
        depending on pool state — a pre-existing gap in avatar_service.py,
        not something this test certifies as fixed."""
        mock_redis_client.get.return_value = b"data"

        service._get_cached_avatar("avatar:1")

        assert (
            mock_redis_client.connection_pool.connection_kwargs["decode_responses"]
            is False
        )


class TestCacheAvatar:
    def test_caches_with_correct_ttl(self, service, mock_redis_client):
        result = service._cache_avatar("avatar:1", b"bytes")

        assert result is True
        mock_redis_client.setex.assert_called_once_with(
            "avatar:1", AVATAR_CACHE_TTL, b"bytes"
        )

    def test_returns_false_on_redis_exception(self, service, mock_redis_client):
        mock_redis_client.setex.side_effect = RuntimeError("connection lost")

        result = service._cache_avatar("avatar:1", b"bytes")

        assert result is False


class TestDownloadAvatar:
    def test_successful_download_returns_bytes(self, service):
        response = _make_response(content=b"image-data", content_type="image/jpeg")
        with patch(
            "services.avatar_service.httpx.Client",
            return_value=FakeHttpxClient(response=response),
        ):
            result = service._download_avatar("https://example.com/a.jpg")

        assert result == b"image-data"

    def test_invalid_content_type_returns_none(self, service):
        response = _make_response(content_type="text/html")
        with patch(
            "services.avatar_service.httpx.Client",
            return_value=FakeHttpxClient(response=response),
        ):
            result = service._download_avatar("https://example.com/a.html")

        assert result is None

    def test_http_status_error_returns_none(self, service):
        response = _make_response(status_code=404)
        with patch(
            "services.avatar_service.httpx.Client",
            return_value=FakeHttpxClient(response=response),
        ):
            result = service._download_avatar("https://example.com/missing.png")

        assert result is None

    def test_timeout_returns_none(self, service):
        with patch(
            "services.avatar_service.httpx.Client",
            return_value=FakeHttpxClient(raise_exc=httpx.TimeoutException("timed out")),
        ):
            result = service._download_avatar("https://example.com/slow.png")

        assert result is None

    def test_generic_exception_returns_none(self, service):
        with patch(
            "services.avatar_service.httpx.Client",
            return_value=FakeHttpxClient(raise_exc=ValueError("boom")),
        ):
            result = service._download_avatar("https://example.com/a.png")

        assert result is None


class TestInvalidateCache:
    def test_deletes_cache_key_and_returns_true(self, service, mock_redis_client):
        result = service.invalidate_cache(42)

        assert result is True
        mock_redis_client.delete.assert_called_once_with("avatar:42")

    def test_returns_false_on_redis_exception(self, service, mock_redis_client):
        mock_redis_client.delete.side_effect = RuntimeError("connection lost")

        result = service.invalidate_cache(42)

        assert result is False
