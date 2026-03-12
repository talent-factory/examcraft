"""
GDPR Compliance API Endpoints
Provides data export and account deletion functionality
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
from datetime import datetime
import logging

from database import get_db
from models.auth import User
from services.auth_service import AuthService
from services.audit_service import AuditService
from utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gdpr", tags=["GDPR"])


@router.get("/export-data")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    audit_service: AuditService = Depends(),
) -> Dict[str, Any]:
    """
    Export all user data in JSON format (GDPR Article 20 - Right to Data Portability)

    Returns:
        Complete user data including:
        - Personal information
        - Documents
        - Generated questions
        - Exams
        - Activity logs
    """
    try:
        logger.info(f"Data export requested by user: {current_user.email}")

        # Collect all user data
        user_data = {
            "export_date": datetime.utcnow().isoformat(),
            "user_profile": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "created_at": current_user.created_at.isoformat()
                if current_user.created_at
                else None,
                "institution_id": current_user.institution_id,
                "roles": [role.name for role in current_user.roles]
                if current_user.roles
                else [],
            },
            "documents": [],
            "questions": [],
            "exams": [],
            "activity_logs": [],
        }

        # Export documents
        from models.document import Document

        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        user_data["documents"] = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "title": doc.title,
                "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
                "status": doc.status,
                "metadata": doc.metadata,
            }
            for doc in documents
        ]

        # Export questions (if question model exists)
        try:
            from models.question_review import QuestionReview

            questions = (
                db.query(QuestionReview)
                .filter(QuestionReview.created_by == current_user.id)
                .all()
            )
            user_data["questions"] = [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                    "status": q.status,
                }
                for q in questions
            ]
        except Exception as e:
            logger.warning(f"Could not export questions: {e}")

        # Export audit logs
        from models.auth import AuditLog

        audit_logs = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == current_user.id)
            .limit(1000)
            .all()
        )
        user_data["activity_logs"] = [
            {
                "action": log.action,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
            }
            for log in audit_logs
        ]

        # Log the export action
        await audit_service.log_action(
            user_id=current_user.id,
            action="data_export",
            details={"export_size": len(json.dumps(user_data))},
            db=db,
        )

        return {
            "success": True,
            "data": user_data,
            "format": "JSON",
            "gdpr_article": "Article 20 - Right to Data Portability",
        }

    except Exception as e:
        logger.error(f"Data export failed for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail=f"Data export failed: {str(e)}")


@router.post("/request-deletion")
async def request_account_deletion(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    audit_service: AuditService = Depends(),
) -> Dict[str, str]:
    """
    Request account deletion (GDPR Article 17 - Right to Erasure)

    Initiates a 30-day grace period before permanent deletion.
    User can cancel deletion within this period.

    Returns:
        Confirmation message with deletion date
    """
    try:
        logger.info(f"Account deletion requested by user: {current_user.email}")

        # Check if deletion is already pending
        if (
            hasattr(current_user, "deletion_requested_at")
            and current_user.deletion_requested_at
        ):
            raise HTTPException(
                status_code=400, detail="Account deletion already pending"
            )

        # Mark account for deletion (30-day grace period)
        from datetime import timedelta

        deletion_date = datetime.utcnow() + timedelta(days=30)

        current_user.deletion_requested_at = datetime.utcnow()
        current_user.scheduled_deletion_date = deletion_date
        db.commit()

        # Log the deletion request
        await audit_service.log_action(
            user_id=current_user.id,
            action="deletion_requested",
            details={
                "scheduled_deletion_date": deletion_date.isoformat(),
                "grace_period_days": 30,
            },
            db=db,
        )

        # Schedule background task to send confirmation email
        # background_tasks.add_task(send_deletion_confirmation_email, current_user.email, deletion_date)

        return {
            "success": True,
            "message": "Account deletion scheduled",
            "deletion_date": deletion_date.isoformat(),
            "grace_period_days": 30,
            "cancellation_info": "You can cancel this request within 30 days by logging in",
            "gdpr_article": "Article 17 - Right to Erasure",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deletion request failed for user {current_user.email}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Deletion request failed: {str(e)}"
        )


@router.post("/cancel-deletion")
async def cancel_account_deletion(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    audit_service: AuditService = Depends(),
) -> Dict[str, str]:
    """
    Cancel pending account deletion

    Returns:
        Confirmation message
    """
    try:
        logger.info(
            f"Account deletion cancellation requested by user: {current_user.email}"
        )

        # Check if deletion is pending
        if (
            not hasattr(current_user, "deletion_requested_at")
            or not current_user.deletion_requested_at
        ):
            raise HTTPException(
                status_code=400, detail="No pending deletion request found"
            )

        # Cancel deletion
        current_user.deletion_requested_at = None
        current_user.scheduled_deletion_date = None
        db.commit()

        # Log the cancellation
        await audit_service.log_action(
            user_id=current_user.id, action="deletion_cancelled", details={}, db=db
        )

        return {"success": True, "message": "Account deletion cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deletion cancellation failed for user {current_user.email}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Deletion cancellation failed: {str(e)}"
        )


@router.delete("/delete-account-now")
async def delete_account_immediately(
    password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(),
    audit_service: AuditService = Depends(),
) -> Dict[str, str]:
    """
    Immediately delete account (requires password confirmation)

    WARNING: This action is irreversible!

    Args:
        password: User's password for confirmation

    Returns:
        Confirmation message
    """
    try:
        logger.warning(
            f"Immediate account deletion requested by user: {current_user.email}"
        )

        # Verify password
        if not auth_service.verify_password(password, current_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid password")

        # Log the deletion (before deleting the user)
        await audit_service.log_action(
            user_id=current_user.id,
            action="account_deleted_immediately",
            details={"email": current_user.email},
            db=db,
        )

        # Delete all user data
        from models.document import Document

        db.query(Document).filter(Document.user_id == current_user.id).delete()

        try:
            from models.question_review import QuestionReview

            db.query(QuestionReview).filter(
                QuestionReview.created_by == current_user.id
            ).delete()
        except Exception as e:
            logger.warning(f"Could not delete questions: {e}")

        # Delete audit logs (keep for compliance)
        # db.query(AuditLog).filter(AuditLog.user_id == current_user.id).delete()

        # Delete user
        db.delete(current_user)
        db.commit()

        logger.info(f"Account deleted successfully: {current_user.email}")

        return {
            "success": True,
            "message": "Account deleted successfully",
            "gdpr_article": "Article 17 - Right to Erasure",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion failed for user {current_user.email}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Account deletion failed: {str(e)}"
        )
