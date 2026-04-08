import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.help import HelpFeedback

logger = logging.getLogger(__name__)


class HelpFeedbackService:
    def __init__(self, db: Session):
        self.db = db

    def submit_feedback(
        self,
        question: str,
        answer: Optional[str],
        confidence: Optional[float],
        rating: str,
        user_role: str,
        user_tier: str,
        route: str,
        language: str = "de",
    ) -> HelpFeedback:
        feedback = HelpFeedback(
            question=question,
            answer=answer,
            confidence=confidence,
            rating=rating,
            user_role=user_role,
            user_tier=user_tier,
            route=route,
            language=language,
            status="offen",
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_feedback_queue(
        self, status: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = self.db.query(HelpFeedback)
        if status:
            query = query.filter(HelpFeedback.status == status)
        items = (
            query.order_by(HelpFeedback.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [item.to_dict() for item in items]

    def get_feedback_count(self, status: Optional[str] = None) -> int:
        query = self.db.query(HelpFeedback)
        if status:
            query = query.filter(HelpFeedback.status == status)
        return query.count()

    def update_feedback_status(
        self, feedback_id: int, status: str
    ) -> Optional[HelpFeedback]:
        feedback = (
            self.db.query(HelpFeedback).filter(HelpFeedback.id == feedback_id).first()
        )
        if not feedback:
            return None
        feedback.status = status
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_metrics(self) -> Dict[str, Any]:
        total = self.db.query(HelpFeedback).count()
        positive = (
            self.db.query(HelpFeedback).filter(HelpFeedback.rating == "up").count()
        )
        open_count = (
            self.db.query(HelpFeedback).filter(HelpFeedback.status == "offen").count()
        )
        avg_confidence = self.db.query(func.avg(HelpFeedback.confidence)).scalar() or 0
        return {
            "total_questions": total,
            "positive_feedback_pct": round(
                (positive / total * 100) if total > 0 else 0, 1
            ),
            "open_feedback_count": open_count,
            "avg_confidence": round(float(avg_confidence), 2),
        }
