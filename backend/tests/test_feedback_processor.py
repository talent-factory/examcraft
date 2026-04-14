"""Tests for FeedbackCluster model and FeedbackProcessorService."""

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
