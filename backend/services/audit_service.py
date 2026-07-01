"""
Audit Logging Service für ExamCraft AI
Implementiert Security & GDPR Compliance Logging
"""

import logging
import json
import uuid
from typing import Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy.orm import Session
from fastapi import Request

from models.auth import AuditLog

if TYPE_CHECKING:
    from models.auth import User

logger = logging.getLogger(__name__)


class AuditService:
    """
    Audit Logging Service
    Logs all security-relevant actions for compliance and security monitoring
    """

    # Action Types
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_REGISTER = "register"
    ACTION_PASSWORD_CHANGE = "password_change"
    ACTION_PASSWORD_RESET = "password_reset"
    ACTION_TOKEN_REFRESH = "token_refresh"
    ACTION_OAUTH_LOGIN = "oauth_login"

    ACTION_CREATE_DOCUMENT = "create_document"
    ACTION_UPDATE_DOCUMENT = "update_document"
    ACTION_DELETE_DOCUMENT = "delete_document"
    ACTION_PROCESS_DOCUMENT = "process_document"

    ACTION_CREATE_QUESTION = "create_question"
    ACTION_APPROVE_QUESTION = "approve_question"
    ACTION_REJECT_QUESTION = "reject_question"
    ACTION_EDIT_QUESTION = "edit_question"
    ACTION_DELETE_QUESTION = "delete_question"

    ACTION_CREATE_USER = "create_user"
    ACTION_UPDATE_USER = "update_user"
    ACTION_DELETE_USER = "delete_user"
    ACTION_ASSIGN_ROLE = "assign_role"
    ACTION_REMOVE_ROLE = "remove_role"

    ACTION_CREATE_RESULT_IMPORT = "create_result_import"
    ACTION_DELETE_RESULT_IMPORT = "delete_result_import"

    ACTION_API_ACCESS = "api_access"
    ACTION_PERMISSION_DENIED = "permission_denied"
    ACTION_RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ACTION_SUPERUSER_BYPASS = "superuser_bypass"
    ACTION_ADMIN_CROSS_OWNER = "admin_cross_owner"
    ACTION_VIEW_AUDIT_LOG = "view_audit_log"

    # Status Types
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"
    STATUS_ERROR = "error"

    # Resource Types
    RESOURCE_USER = "user"
    RESOURCE_DOCUMENT = "document"
    RESOURCE_QUESTION = "question"
    RESOURCE_SESSION = "session"
    RESOURCE_ROLE = "role"
    RESOURCE_INSTITUTION = "institution"
    RESOURCE_EXAM = "exam"

    @staticmethod
    def log_action(
        db: Session,
        action: str,
        status: str = STATUS_SUCCESS,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        request: Optional[Request] = None,
        commit: bool = True,
    ) -> AuditLog:
        """
        Log an audit action

        Args:
            db: Database session
            action: Action type (use ACTION_* constants)
            status: Action status (use STATUS_* constants)
            user_id: User ID who performed the action
            resource_type: Type of resource affected (use RESOURCE_* constants)
            resource_id: ID of affected resource
            ip_address: Client IP address
            user_agent: Client user agent
            additional_data: Additional data as dict (will be JSON serialized)
            error_message: Error message if status is failure/error
            request: FastAPI Request object (auto-extracts IP and user agent)

        Returns:
            Created AuditLog entry
        """
        try:
            # Extract IP and user agent from request if provided
            if request:
                if not ip_address:
                    ip_address = request.client.host if request.client else None
                if not user_agent:
                    user_agent = request.headers.get("user-agent")

            # Serialize additional data to JSON. If serialization fails we
            # preserve the original keys (truncated repr) so the audit row
            # stays diagnostically useful instead of collapsing to a generic
            # "Failed to serialize data" stub that hides what the caller
            # intended to log.
            additional_data_json = None
            if additional_data:
                try:
                    additional_data_json = json.dumps(additional_data)
                except Exception as e:
                    logger.warning(
                        "Failed to serialize additional_data for action=%s: %s",
                        action,
                        e,
                        exc_info=True,
                    )
                    additional_data_json = json.dumps(
                        {
                            "_serialization_error": str(e),
                            "_keys": sorted(str(k) for k in additional_data.keys()),
                        }
                    )

            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                ip_address=ip_address,
                user_agent=user_agent[:500]
                if user_agent
                else None,  # Truncate to 500 chars
                additional_data=additional_data_json,
                status=status,
                error_message=error_message,
            )

            db.add(audit_log)
            if commit:
                db.commit()
                db.refresh(audit_log)
            else:
                # Stage the row inside the caller's open transaction so that
                # multiple audit rows and the mutation they describe commit
                # atomically (the caller issues a single commit). flush() still
                # assigns the PK and surfaces integrity errors here, preserving
                # the fail-loud None contract in the except branch below.
                db.flush()

            logger.info(
                f"Audit log created: action={action}, status={status}, "
                f"user_id={user_id}, resource={resource_type}:{resource_id}"
            )

            return audit_log

        except Exception as e:
            # Generate a correlation ID so operators can match this loud log
            # line to whatever exception trace lands in Sentry / log
            # aggregation. Returning None preserves the historical contract
            # for call sites that do not gate a privileged bypass; the
            # bypass-helpers (log_superuser_bypass / log_admin_cross_owner)
            # check for None and abort the action with HTTP 500 to keep the
            # privileged-action audit invariant. Login / password / permission-
            # denied paths still fail loud in the logs via the error_id below
            # rather than silently swallowing — they just don't refuse the
            # user-facing operation when the audit insert fails.
            error_id = uuid.uuid4().hex
            logger.error(
                "Failed to create audit log [error_id=%s, action=%s, user_id=%s, "
                "resource=%s:%s]: %s",
                error_id,
                action,
                user_id,
                resource_type,
                resource_id,
                e,
                exc_info=True,
            )
            try:
                db.rollback()
            except Exception:
                logger.error(
                    "Audit-log rollback failed [error_id=%s]", error_id, exc_info=True
                )
            return None

    @staticmethod
    def log_login(
        db: Session,
        user_id: int,
        success: bool,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
        login_method: str = "password",
    ) -> AuditLog:
        """Log user login attempt"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_LOGIN,
            status=AuditService.STATUS_SUCCESS
            if success
            else AuditService.STATUS_FAILURE,
            user_id=user_id if success else None,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id) if user_id else None,
            request=request,
            error_message=error_message,
            additional_data={"login_method": login_method},
        )

    @staticmethod
    def log_logout(
        db: Session, user_id: int, request: Optional[Request] = None
    ) -> AuditLog:
        """Log user logout"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_LOGOUT,
            status=AuditService.STATUS_SUCCESS,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id),
            request=request,
        )

    @staticmethod
    def log_register(
        db: Session, user_id: int, email: str, request: Optional[Request] = None
    ) -> AuditLog:
        """Log user registration"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_REGISTER,
            status=AuditService.STATUS_SUCCESS,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id),
            request=request,
            additional_data={"email": email},
        )

    @staticmethod
    def log_password_change(
        db: Session,
        user_id: int,
        success: bool,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Log password change attempt"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_PASSWORD_CHANGE,
            status=AuditService.STATUS_SUCCESS
            if success
            else AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id),
            request=request,
            error_message=error_message,
        )

    @staticmethod
    def log_document_action(
        db: Session,
        action: str,
        user_id: int,
        document_id: int,
        success: bool = True,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> AuditLog:
        """Log document-related action"""
        return AuditService.log_action(
            db=db,
            action=action,
            status=AuditService.STATUS_SUCCESS
            if success
            else AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_DOCUMENT,
            resource_id=str(document_id),
            request=request,
            error_message=error_message,
            additional_data=additional_data,
            commit=commit,
        )

    @staticmethod
    def log_question_action(
        db: Session,
        action: str,
        user_id: int,
        question_id: int,
        success: bool = True,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log question-related action"""
        return AuditService.log_action(
            db=db,
            action=action,
            status=AuditService.STATUS_SUCCESS
            if success
            else AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_QUESTION,
            resource_id=str(question_id),
            request=request,
            error_message=error_message,
            additional_data=additional_data,
        )

    @staticmethod
    def log_superuser_bypass(
        db: Session,
        superuser: "User",
        resource_type: str,
        resource_id: Optional[Any],
        action: str,
        owner_user_id: Optional[int],
        request: Optional[Request] = None,
    ) -> AuditLog:
        """
        Log a superuser bypass event (access to foreign owner data or quota override).

        DSGVO-compliance contract: This log MUST be persisted before the bypass
        proceeds. If the underlying log_action returns None (silent DB failure),
        this method raises HTTPException 500 to abort the bypass — better to
        deny access than to bypass without an audit trail.

        Args:
            db: Database session
            superuser: User-Object performing the bypass (must have id, email)
            resource_type: Bypassed resource type ("document", "chat_session", "quota", ...)
            resource_id: PK of the resource or None for quota bypasses
            action: Concrete bypassed action ("process", "delete", "ws_subscribe",
                "list_all", "list_all_active", "override_user_limit",
                "override_document_limit", "override_question_limit",
                "override_storage_limit", ...)
            owner_user_id: ID of original owner (None for quota)
            request: Optional FastAPI Request for IP/UA extraction

        Returns:
            Created AuditLog entry (never None — raises on persistence failure)

        Raises:
            HTTPException 500: If audit log could not be persisted.
        """
        from fastapi import HTTPException

        audit_log = AuditService.log_action(
            db=db,
            action=AuditService.ACTION_SUPERUSER_BYPASS,
            user_id=superuser.id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            additional_data={
                "bypassed_action": action,
                "owner_user_id": owner_user_id,
                "superuser_email": superuser.email,
            },
            request=request,
        )
        if audit_log is None:
            logger.critical(
                "Superuser bypass refused: audit log persistence failed "
                f"(superuser={superuser.id}, resource={resource_type}:{resource_id}, "
                f"action={action}). Bypass aborted to preserve DSGVO trail."
            )
            raise HTTPException(
                status_code=500,
                detail="Audit log unavailable; superuser bypass denied.",
            )
        return audit_log

    @staticmethod
    def log_admin_cross_owner(
        db: Session,
        admin: "User",
        resource_type: str,
        resource_id: Optional[Any],
        action: str,
        owner_user_id: int,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """
        Log a same-institution-admin acting on a resource owned by another user.

        Same DSGVO contract as log_superuser_bypass: if the audit log can not be
        persisted, raise HTTPException 500 so the cross-owner action is aborted
        rather than completed without an audit trail.
        """
        from fastapi import HTTPException

        audit_log = AuditService.log_action(
            db=db,
            action=AuditService.ACTION_ADMIN_CROSS_OWNER,
            user_id=admin.id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            additional_data={
                "bypassed_action": action,
                "owner_user_id": owner_user_id,
                "admin_email": admin.email,
            },
            request=request,
        )
        if audit_log is None:
            logger.critical(
                "Admin cross-owner action refused: audit log persistence failed "
                f"(admin={admin.id}, resource={resource_type}:{resource_id}, "
                f"action={action}, owner={owner_user_id}). Action aborted to preserve "
                "DSGVO trail."
            )
            raise HTTPException(
                status_code=500,
                detail="Audit log unavailable; admin cross-owner action denied.",
            )
        return audit_log

    @staticmethod
    def log_permission_denied(
        db: Session,
        user_id: int,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None,
        required_permission: Optional[str] = None,
    ) -> AuditLog:
        """Log permission denied event"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_PERMISSION_DENIED,
            status=AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request=request,
            additional_data={
                "attempted_action": action,
                "required_permission": required_permission,
            },
        )

    @staticmethod
    def log_rate_limit_exceeded(
        db: Session,
        user_id: Optional[int] = None,
        request: Optional[Request] = None,
        limit_type: str = "ip",
    ) -> AuditLog:
        """Log rate limit exceeded event"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_RATE_LIMIT_EXCEEDED,
            status=AuditService.STATUS_FAILURE,
            user_id=user_id,
            request=request,
            additional_data={"limit_type": limit_type},
        )


# ---------------------------------------------------------------------------
# Audit category taxonomy (TF-415)
#
# Single source of truth for the read-side RBAC scoping. Defined here, next to
# the write-side ACTION_* constants, so the two never drift. Consumed by
# services.audit_query_service and api.audit.
#
# Visibility tiers (see docs/superpowers/specs/2026-06-13-audit-visibility-rbac-design.md):
#   - Institution-Admin: business + admin
#   - SuperAdmin:         all four categories + any uncategorized action
#
# Fail-closed: an action absent from every category is treated as "security"
# (SuperAdmin-only) so a forgotten mapping never widens visibility.
# ---------------------------------------------------------------------------

AUDIT_CATEGORIES: tuple[str, ...] = ("business", "admin", "auth", "security")

ACTIONS_BY_CATEGORY: dict[str, frozenset[str]] = {
    "business": frozenset(
        {
            AuditService.ACTION_CREATE_DOCUMENT,
            AuditService.ACTION_UPDATE_DOCUMENT,
            AuditService.ACTION_DELETE_DOCUMENT,
            AuditService.ACTION_PROCESS_DOCUMENT,
            AuditService.ACTION_CREATE_QUESTION,
            AuditService.ACTION_APPROVE_QUESTION,
            AuditService.ACTION_REJECT_QUESTION,
            AuditService.ACTION_EDIT_QUESTION,
            AuditService.ACTION_DELETE_QUESTION,
            # Exam lifecycle (api/exams.py)
            "create_exam",
            "update_exam_grading_scheme",
            "delete_exam",
            "archive_exam",
            "restore_exam",
            # Result-import lifecycle (TF-501 create, TF-421 delete).
            # Both anchor on the exam and create/remove student PII, so they
            # share the "business" tier visible to Institution-Admins.
            AuditService.ACTION_CREATE_RESULT_IMPORT,
            AuditService.ACTION_DELETE_RESULT_IMPORT,
            # GDPR data actions (api/gdpr.py)
            "data_export",
            "deletion_requested",
            "deletion_cancelled",
            "account_deleted_immediately",
        }
    ),
    "admin": frozenset(
        {
            AuditService.ACTION_CREATE_USER,
            AuditService.ACTION_UPDATE_USER,
            AuditService.ACTION_DELETE_USER,
            AuditService.ACTION_ASSIGN_ROLE,
            AuditService.ACTION_REMOVE_ROLE,
        }
    ),
    "auth": frozenset(
        {
            AuditService.ACTION_LOGIN,
            AuditService.ACTION_LOGOUT,
            AuditService.ACTION_REGISTER,
            AuditService.ACTION_PASSWORD_CHANGE,
            AuditService.ACTION_PASSWORD_RESET,
            AuditService.ACTION_TOKEN_REFRESH,
            AuditService.ACTION_OAUTH_LOGIN,
        }
    ),
    "security": frozenset(
        {
            AuditService.ACTION_API_ACCESS,
            AuditService.ACTION_PERMISSION_DENIED,
            AuditService.ACTION_RATE_LIMIT_EXCEEDED,
            AuditService.ACTION_SUPERUSER_BYPASS,
            AuditService.ACTION_ADMIN_CROSS_OWNER,
            AuditService.ACTION_VIEW_AUDIT_LOG,
        }
    ),
}

_ACTION_TO_CATEGORY: dict[str, str] = {
    action: category
    for category, actions in ACTIONS_BY_CATEGORY.items()
    for action in actions
}


def category_for_action(action: str) -> str:
    """Return the audit category for an action.

    Unknown actions fail closed to ``"security"`` so they stay SuperAdmin-only
    and never leak into a lower tier's view.
    """
    return _ACTION_TO_CATEGORY.get(action, "security")
