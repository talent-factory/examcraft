"""
Tenant Isolation Utilities für ExamCraft AI
Multi-Tenant Data Isolation und Access Control
"""

from typing import Optional, Type, TypeVar, List
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_
from fastapi import HTTPException, status
import logging

from models.auth import User, Institution
from models.document import Document
from models.question_review import QuestionReview

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TenantContext:
    """
    Tenant Context für Request-Scope
    Speichert aktuelle Institution und User für Tenant-Isolation
    """
    
    def __init__(self, user: User):
        self.user = user
        self.institution_id = user.institution_id
        self.institution = user.institution
        self.is_superuser = user.is_superuser
    
    def __repr__(self):
        return f"<TenantContext(user_id={self.user.id}, institution_id={self.institution_id})>"


class TenantFilter:
    """
    Tenant-aware Query Filter
    Automatisches Filtern von Queries nach Institution
    """
    
    @staticmethod
    def filter_by_tenant(
        query: Query,
        model: Type[T],
        tenant_context: TenantContext,
        allow_superuser_access: bool = True
    ) -> Query:
        """
        Filter query by tenant (institution_id)
        
        Args:
            query: SQLAlchemy Query object
            model: Model class to filter
            tenant_context: Current tenant context
            allow_superuser_access: If True, superusers can see all data
            
        Returns:
            Filtered query
        """
        # Superuser can see all data (optional)
        if allow_superuser_access and tenant_context.is_superuser:
            logger.debug(f"Superuser access: No tenant filtering applied")
            return query
        
        # Check if model has institution_id field
        if not hasattr(model, 'institution_id'):
            logger.warning(f"Model {model.__name__} has no institution_id field")
            return query
        
        # Filter by institution_id
        return query.filter(model.institution_id == tenant_context.institution_id)
    
    @staticmethod
    def verify_tenant_access(
        obj: T,
        tenant_context: TenantContext,
        allow_superuser_access: bool = True
    ) -> None:
        """
        Verify that user has access to object based on tenant
        
        Args:
            obj: Object to check
            tenant_context: Current tenant context
            allow_superuser_access: If True, superusers can access all data
            
        Raises:
            HTTPException: If access denied
        """
        # Superuser can access all data
        if allow_superuser_access and tenant_context.is_superuser:
            return
        
        # Check if object has institution_id
        if not hasattr(obj, 'institution_id'):
            logger.warning(f"Object {type(obj).__name__} has no institution_id field")
            return
        
        # Verify institution_id matches
        if obj.institution_id != tenant_context.institution_id:
            logger.warning(
                f"Tenant access denied: User {tenant_context.user.id} "
                f"(institution {tenant_context.institution_id}) "
                f"tried to access object with institution {obj.institution_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Resource belongs to different institution"
            )


class SubscriptionLimits:
    """
    Subscription Tier Limits Enforcement
    Prüft ob Institution Limits überschritten hat
    """
    
    @staticmethod
    def check_user_limit(institution: Institution, db: Session) -> None:
        """
        Check if institution has reached user limit
        
        Raises:
            HTTPException: If limit exceeded
        """
        from models.auth import User, UserStatus
        
        active_users = db.query(User).filter(
            and_(
                User.institution_id == institution.id,
                User.status == UserStatus.ACTIVE.value
            )
        ).count()
        
        if active_users >= institution.max_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User limit reached ({institution.max_users} users). Please upgrade your subscription."
            )
    
    @staticmethod
    def check_document_limit(institution: Institution, db: Session) -> None:
        """
        Check if institution has reached document limit
        
        Raises:
            HTTPException: If limit exceeded
        """
        document_count = db.query(Document).filter(
            Document.institution_id == institution.id
        ).count()
        
        if document_count >= institution.max_documents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Document limit reached ({institution.max_documents} documents). Please upgrade your subscription."
            )
    
    @staticmethod
    def check_question_limit(institution: Institution, db: Session) -> None:
        """
        Check if institution has reached monthly question generation limit
        
        Raises:
            HTTPException: If limit exceeded
        """
        from datetime import datetime, timezone
        from dateutil.relativedelta import relativedelta
        
        # Count questions generated this month
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        questions_this_month = db.query(QuestionReview).filter(
            and_(
                QuestionReview.institution_id == institution.id,
                QuestionReview.created_at >= month_start
            )
        ).count()
        
        if questions_this_month >= institution.max_questions_per_month:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly question limit reached ({institution.max_questions_per_month} questions). Please upgrade your subscription."
            )
    
    @staticmethod
    def get_usage_stats(institution: Institution, db: Session) -> dict:
        """
        Get current usage statistics for institution
        
        Returns:
            Dict with usage stats
        """
        from models.auth import User, UserStatus
        from datetime import datetime, timezone
        
        # Active users
        active_users = db.query(User).filter(
            and_(
                User.institution_id == institution.id,
                User.status == UserStatus.ACTIVE.value
            )
        ).count()
        
        # Documents
        document_count = db.query(Document).filter(
            Document.institution_id == institution.id
        ).count()
        
        # Questions this month
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        questions_this_month = db.query(QuestionReview).filter(
            and_(
                QuestionReview.institution_id == institution.id,
                QuestionReview.created_at >= month_start
            )
        ).count()
        
        return {
            "subscription_tier": institution.subscription_tier,
            "users": {
                "current": active_users,
                "limit": institution.max_users,
                "percentage": round((active_users / institution.max_users) * 100, 1) if institution.max_users > 0 else 0
            },
            "documents": {
                "current": document_count,
                "limit": institution.max_documents,
                "percentage": round((document_count / institution.max_documents) * 100, 1) if institution.max_documents > 0 else 0
            },
            "questions_this_month": {
                "current": questions_this_month,
                "limit": institution.max_questions_per_month,
                "percentage": round((questions_this_month / institution.max_questions_per_month) * 100, 1) if institution.max_questions_per_month > 0 else 0
            }
        }


def get_tenant_context(user: User) -> TenantContext:
    """
    Create tenant context from user
    
    Args:
        user: Current user
        
    Returns:
        TenantContext object
    """
    return TenantContext(user)

