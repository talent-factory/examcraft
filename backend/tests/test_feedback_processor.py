"""Tests for FeedbackCluster model and FeedbackProcessorService."""

from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import numpy as np
from models.feedback_cluster import FeedbackCluster


def test_feedback_cluster_to_dict():
    cluster = FeedbackCluster(
        id=1,
        topic_label="export",
        positive_count=5,
        negative_count=2,
        total_count=7,
        status="aktiv",
        docs_gap=False,
    )
    d = cluster.to_dict()
    assert d["topic_label"] == "export"
    assert d["total_count"] == 7
    assert d["docs_gap"] is False


from services.feedback_processor_service import FeedbackProcessorService


@pytest.mark.asyncio
async def test_assign_cluster_creates_new_when_no_match():
    """When no similar cluster exists (score < 0.85), create a new one."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.flush = MagicMock()

    service = FeedbackProcessorService(mock_db)

    mock_vector_service = MagicMock()
    mock_vector_service.client = MagicMock()
    mock_result = MagicMock()
    mock_result.points = []
    mock_vector_service.client.query_points.return_value = mock_result
    mock_vector_service.client.upsert = MagicMock()

    embedding = np.zeros(384)

    with patch("services.feedback_processor_service.vector_service", mock_vector_service):
        cluster_id = await service._assign_cluster(embedding, "Wie exportiere ich?")

    mock_db.add.assert_called_once()
    assert cluster_id is not None


@pytest.mark.asyncio
async def test_assign_cluster_joins_existing_when_high_score():
    """When a similar cluster exists (score >= 0.85), join it."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(id=42)

    service = FeedbackProcessorService(mock_db)

    mock_vector_service = MagicMock()
    mock_vector_service.client = MagicMock()
    mock_point = MagicMock()
    mock_point.score = 0.92
    mock_point.payload = {"cluster_id": 42}
    mock_result = MagicMock()
    mock_result.points = [mock_point]
    mock_vector_service.client.query_points.return_value = mock_result

    embedding = np.zeros(384)

    with patch("services.feedback_processor_service.vector_service", mock_vector_service):
        cluster_id = await service._assign_cluster(embedding, "Wie exportiere ich?")

    assert cluster_id == 42
    mock_db.add.assert_not_called()


def test_check_triggers_creates_faq_candidate():
    """3+ positive, 0 negative → FAQ candidate created."""
    mock_db = MagicMock()

    cluster = MagicMock()
    cluster.id = 1
    cluster.positive_count = 3
    cluster.negative_count = 0
    cluster.topic_label = "export"

    # First query().filter().first() returns the cluster
    # Second query().filter_by().first() returns None (no existing FAQ)
    mock_db.query.return_value.filter.return_value.first.return_value = cluster
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    mock_feedback = MagicMock()
    mock_feedback.question = "Wie exportiere ich?"
    mock_feedback.answer = "Gehe zu Prüfungen > Export"
    mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = mock_feedback

    service = FeedbackProcessorService(mock_db)
    service._check_triggers(1)

    assert mock_db.add.called


def test_check_triggers_marks_docs_gap():
    """3+ negative → docs_gap set to True."""
    mock_db = MagicMock()
    cluster = MagicMock()
    cluster.id = 2
    cluster.positive_count = 0
    cluster.negative_count = 3
    cluster.docs_gap = False
    mock_db.query.return_value.filter.return_value.first.return_value = cluster

    service = FeedbackProcessorService(mock_db)
    service._check_triggers(2)

    assert cluster.docs_gap is True
    mock_db.commit.assert_called()
