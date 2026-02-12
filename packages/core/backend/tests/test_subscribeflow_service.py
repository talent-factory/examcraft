"""
Tests for SubscribeFlow Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.subscribeflow_service import SubscribeFlowService


@pytest.fixture
def service():
    """Create service instance with test config."""
    svc = SubscribeFlowService()
    svc.api_key = "sf_test_key"
    svc.base_url = "http://localhost:8000"
    return svc


@pytest.fixture
def mock_client():
    """Create mock SubscribeFlow client."""
    client = AsyncMock()

    # Mock tag
    mock_tag = MagicMock()
    mock_tag.id = "tag-uuid-123"
    mock_tag.name = "examcraft"
    client.tags.get_or_create = AsyncMock(return_value=(mock_tag, False))

    # Mock subscriber
    mock_subscriber = MagicMock()
    mock_subscriber.id = "subscriber-uuid-456"
    mock_subscriber.email = "test@example.com"
    client.subscribers.get_or_create = AsyncMock(
        return_value=(mock_subscriber, True)
    )

    # Context manager support
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    return client


@pytest.mark.asyncio
async def test_subscribe_user_creates_new_subscriber(service, mock_client):
    """Test subscribing a new user."""
    with patch(
        "services.subscribeflow_service.SubscribeFlowClient",
        return_value=mock_client,
    ):
        result = await service.subscribe_user(
            email="new@example.com",
            first_name="New",
            last_name="User",
            user_id="user-123",
        )

        assert result["created"] is True
        assert result["tag_name"] == "examcraft"
        assert result["subscriber_id"] == "subscriber-uuid-456"
        assert result["tag_id"] == "tag-uuid-123"

        mock_client.tags.get_or_create.assert_called_once_with(
            name="examcraft",
            description="ExamCraft AI newsletter subscribers",
            category="product",
        )

        mock_client.subscribers.get_or_create.assert_called_once()
        call_kwargs = mock_client.subscribers.get_or_create.call_args.kwargs
        assert call_kwargs["email"] == "new@example.com"
        assert "tag-uuid-123" in call_kwargs["tags"]
        assert call_kwargs["metadata"]["examcraft_user_id"] == "user-123"
        assert call_kwargs["metadata"]["source"] == "email_verification"
        assert call_kwargs["metadata"]["first_name"] == "New"
        assert call_kwargs["metadata"]["last_name"] == "User"


@pytest.mark.asyncio
async def test_subscribe_user_returns_existing(service, mock_client):
    """Test subscribing an existing user returns existing record."""
    mock_client.subscribers.get_or_create = AsyncMock(
        return_value=(MagicMock(id="existing-123"), False)
    )

    with patch(
        "services.subscribeflow_service.SubscribeFlowClient",
        return_value=mock_client,
    ):
        result = await service.subscribe_user(email="existing@example.com")

        assert result["created"] is False
        assert result["subscriber_id"] == "existing-123"


@pytest.mark.asyncio
async def test_subscribe_user_handles_api_error(service, mock_client):
    """Test proper error propagation for API failures."""
    mock_client.tags.get_or_create = AsyncMock(
        side_effect=Exception("API connection failed")
    )

    with patch(
        "services.subscribeflow_service.SubscribeFlowClient",
        return_value=mock_client,
    ):
        with pytest.raises(Exception, match="API connection failed"):
            await service.subscribe_user(email="test@example.com")


@pytest.mark.asyncio
async def test_subscribe_user_skips_when_not_configured():
    """Test that service skips when API key is not configured."""
    service = SubscribeFlowService()
    service.api_key = ""

    result = await service.subscribe_user(email="test@example.com")

    assert result["status"] == "skipped"
    assert result["reason"] == "not_configured"


def test_is_available_with_key():
    """Test is_available returns True when API key is set."""
    service = SubscribeFlowService()
    service.api_key = "sf_test_key"
    assert service.is_available() is True


def test_is_available_without_key():
    """Test is_available returns False when API key is empty."""
    service = SubscribeFlowService()
    service.api_key = ""
    assert service.is_available() is False


@pytest.mark.asyncio
async def test_subscribe_user_metadata_without_optional_fields(service, mock_client):
    """Test that metadata omits optional fields when not provided."""
    with patch(
        "services.subscribeflow_service.SubscribeFlowClient",
        return_value=mock_client,
    ):
        await service.subscribe_user(email="minimal@example.com")

        call_kwargs = mock_client.subscribers.get_or_create.call_args.kwargs
        metadata = call_kwargs["metadata"]
        assert metadata["source"] == "email_verification"
        assert metadata["product"] == "examcraft"
        assert "first_name" not in metadata
        assert "last_name" not in metadata
        assert "examcraft_user_id" not in metadata


@pytest.mark.asyncio
async def test_subscribe_user_creates_new_tag(service, mock_client):
    """Test that a newly created tag is logged correctly."""
    mock_client.tags.get_or_create = AsyncMock(
        return_value=(MagicMock(id="new-tag-id"), True)
    )

    with patch(
        "services.subscribeflow_service.SubscribeFlowClient",
        return_value=mock_client,
    ):
        result = await service.subscribe_user(email="test@example.com")

        assert result["tag_id"] == "new-tag-id"
