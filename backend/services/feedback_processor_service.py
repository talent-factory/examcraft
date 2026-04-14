"""Service for processing help feedback: clustering, triggers, FAQ candidates."""

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CLUSTER_SIMILARITY_THRESHOLD = 0.85

try:
    from services.vector_service_factory import vector_service
except Exception:  # pragma: no cover
    vector_service = None  # type: ignore[assignment]


class FeedbackProcessorService:
    def __init__(self, db: Session):
        self.db = db

    async def process_feedback(self, feedback_id: int) -> None:
        """Main entry point: cluster feedback and check triggers."""
        from models.help import HelpFeedback
        from services.vector_service_factory import vector_service

        feedback = (
            self.db.query(HelpFeedback).filter(HelpFeedback.id == feedback_id).first()
        )
        if not feedback:
            logger.warning(f"Feedback {feedback_id} not found")
            return

        if not hasattr(vector_service, "client") or vector_service.client is None:
            logger.warning("Qdrant not available, skipping feedback processing")
            return

        try:
            embeddings = await vector_service.create_embeddings([feedback.question])
            if len(embeddings) == 0:
                logger.warning("Failed to create embedding for feedback question")
                return

            self._ensure_feedback_collection()
            cluster_id = await self._assign_cluster(embeddings[0], feedback.question)

            if cluster_id:
                feedback.cluster_id = cluster_id
                self._update_cluster_stats(cluster_id, feedback.rating)
                self._check_triggers(cluster_id)
                self.db.commit()
        except Exception as e:
            logger.error(
                f"Failed to process feedback {feedback_id}: {e}", exc_info=True
            )

    def _ensure_feedback_collection(self) -> None:
        """Create the feedback_clusters Qdrant collection if it doesn't exist."""
        from services.vector_service_factory import vector_service

        if hasattr(vector_service, "get_or_create_collection"):
            vector_service.get_or_create_collection("feedback_clusters")
        else:
            from qdrant_client.http.models import VectorParams, Distance

            collections = vector_service.client.get_collections()
            if not any(c.name == "feedback_clusters" for c in collections.collections):
                vector_service.client.create_collection(
                    collection_name="feedback_clusters",
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info("Created feedback_clusters collection")

    async def _assign_cluster(self, embedding, question: str) -> Optional[int]:
        """Find matching cluster or create new one."""
        from models.feedback_cluster import FeedbackCluster
        from qdrant_client.http.models import PointStruct

        search_results = vector_service.client.query_points(
            collection_name="feedback_clusters",
            query=embedding.tolist() if hasattr(embedding, "tolist") else embedding,
            limit=1,
            with_payload=True,
        )

        if (
            search_results.points
            and search_results.points[0].score >= CLUSTER_SIMILARITY_THRESHOLD
        ):
            cluster_id = search_results.points[0].payload["cluster_id"]
            return cluster_id

        # Create new cluster
        cluster = FeedbackCluster(
            topic_label=question[:100],
            vector_id=str(uuid.uuid4()),
            positive_count=0,
            negative_count=0,
            total_count=0,
            status="aktiv",
        )
        self.db.add(cluster)
        self.db.flush()

        # Store centroid vector in Qdrant
        vector_service.client.upsert(
            collection_name="feedback_clusters",
            points=[
                PointStruct(
                    id=cluster.vector_id,
                    vector=embedding.tolist()
                    if hasattr(embedding, "tolist")
                    else embedding,
                    payload={
                        "cluster_id": cluster.id,
                        "topic_label": cluster.topic_label,
                        "sample_questions": [question[:200]],
                    },
                )
            ],
        )

        # In production, cluster.id is set by SQLAlchemy after flush.
        # Fall back to vector_id (str) only when running without a real DB (tests).
        return cluster.id or cluster.vector_id

    def _update_cluster_stats(self, cluster_id: int, rating: str) -> None:
        """Update cluster positive/negative/total counts."""
        from models.feedback_cluster import FeedbackCluster

        cluster = (
            self.db.query(FeedbackCluster)
            .filter(FeedbackCluster.id == cluster_id)
            .first()
        )
        if not cluster:
            return

        cluster.total_count += 1
        if rating == "up":
            cluster.positive_count += 1
        elif rating == "down":
            cluster.negative_count += 1

    def _check_triggers(self, cluster_id: int) -> None:
        """Check if cluster thresholds are met and trigger actions."""
        from models.feedback_cluster import FeedbackCluster
        from models.help import HelpFaqCache, HelpFeedback

        cluster = (
            self.db.query(FeedbackCluster)
            .filter(FeedbackCluster.id == cluster_id)
            .first()
        )
        if not cluster:
            return

        # Trigger: 3+ positive, 0 negative → FAQ candidate
        if cluster.positive_count >= 3 and cluster.negative_count == 0:
            existing = (
                self.db.query(HelpFaqCache).filter_by(cluster_id=cluster_id).first()
            )
            if not existing:
                best_feedback = (
                    self.db.query(HelpFeedback)
                    .filter(HelpFeedback.cluster_id == cluster_id)
                    .filter(HelpFeedback.rating == "up")
                    .order_by(HelpFeedback.confidence.desc())
                    .first()
                )
                if best_feedback and best_feedback.answer:
                    faq = HelpFaqCache(
                        question_text=best_feedback.question,
                        answer_de=best_feedback.answer,
                        answer_en=best_feedback.answer,
                        docs_links=[],
                        source_files=[],
                        faq_status="vorgeschlagen",
                        cluster_id=cluster_id,
                    )
                    self.db.add(faq)
                    self.db.commit()
                    logger.info(f"FAQ candidate created for cluster {cluster_id}")

        # Trigger: 3+ negative → docs gap
        if cluster.negative_count >= 3 and not cluster.docs_gap:
            cluster.docs_gap = True
            self.db.commit()
            logger.info(
                f"Docs gap flagged for cluster {cluster_id}: {cluster.topic_label}"
            )
