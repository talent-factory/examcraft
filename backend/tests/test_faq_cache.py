"""Tests for FAQ cache activation in HelpService."""

from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import numpy as np


@pytest.mark.asyncio
async def test_faq_cache_hit_returns_cached_answer():
    """When a matching FAQ exists with score > 0.92, return cached answer."""
    from services.help_service import HelpService

    mock_db = MagicMock()
    service = HelpService(mock_db)

    mock_faq = MagicMock()
    mock_faq.answer_de = "Gecachte Antwort"
    mock_faq.answer_en = "Cached answer"
    mock_faq.docs_links = ["https://docs.examcraft.ch/faq/"]
    mock_faq.hit_count = 5
    mock_faq.id = 1

    mock_vector_service = MagicMock()
    mock_vector_service.client = MagicMock()
    mock_vector_service.create_embeddings = AsyncMock(return_value=[np.zeros(384)])

    mock_point = MagicMock()
    mock_point.score = 0.95
    mock_point.payload = {"faq_id": 1}
    mock_search = MagicMock()
    mock_search.points = [mock_point]
    mock_vector_service.client.query_points.return_value = mock_search

    mock_db.query.return_value.filter.return_value.first.return_value = mock_faq

    with patch("services.help_service.vector_service", mock_vector_service):
        result = await service._try_faq_cache("Wie exportiere ich?", "de")

    assert result is not None
    assert result["answer"] == "Gecachte Antwort"
    assert result["from_cache"] is True
    assert result["confidence"] == 1.0


@pytest.mark.asyncio
async def test_faq_cache_miss_returns_none():
    """When no matching FAQ (score < 0.92), return None."""
    from services.help_service import HelpService

    mock_db = MagicMock()
    service = HelpService(mock_db)

    mock_vector_service = MagicMock()
    mock_vector_service.client = MagicMock()
    mock_vector_service.create_embeddings = AsyncMock(return_value=[np.zeros(384)])

    mock_point = MagicMock()
    mock_point.score = 0.80
    mock_search = MagicMock()
    mock_search.points = [mock_point]
    mock_vector_service.client.query_points.return_value = mock_search

    with patch("services.help_service.vector_service", mock_vector_service):
        result = await service._try_faq_cache("Etwas ganz anderes", "de")

    assert result is None


@pytest.mark.asyncio
async def test_faq_cache_no_qdrant_returns_none():
    """When Qdrant is not available, return None gracefully."""
    from services.help_service import HelpService

    mock_db = MagicMock()
    service = HelpService(mock_db)

    mock_vector_service = MagicMock()
    mock_vector_service.client = None

    with patch("services.help_service.vector_service", mock_vector_service):
        result = await service._try_faq_cache("Test", "de")

    assert result is None
