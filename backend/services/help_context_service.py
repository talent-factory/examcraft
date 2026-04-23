import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models.help import HelpContextHint

logger = logging.getLogger(__name__)


class HelpContextService:
    def __init__(self, db: Session):
        self.db = db

    def get_hint_for_route(
        self,
        route: str,
        user_role: str,
        user_tier: str,
        locale: str = "de",
        user_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        normalized = "/" + route.strip("/")

        dismissed_ids: set = set()
        if user_id:
            from models.help import HelpDismissedHint

            dismissed = (
                self.db.query(HelpDismissedHint.hint_id)
                .filter(HelpDismissedHint.user_id == user_id)
                .all()
            )
            dismissed_ids = {d.hint_id for d in dismissed}

        hints = (
            self.db.query(HelpContextHint)
            .filter(HelpContextHint.active.is_(True))
            .order_by(HelpContextHint.priority.desc())
            .all()
        )
        for hint in hints:
            if hint.id in dismissed_ids:
                continue
            if not normalized.startswith(hint.route_pattern.rstrip("/")):
                continue
            if hint.role and hint.role != user_role:
                continue
            if hint.tier and hint.tier != user_tier:
                continue
            return hint.to_dict(locale=locale)
        return None
